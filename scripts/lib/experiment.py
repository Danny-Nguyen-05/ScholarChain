#!/usr/bin/env python3
"""Experiment manifest validation and run records for run-experiment.sh (stdlib; python3 -I).

  validate --manifest FILE --max-run-usd C --max-runtime-cap M --max-capacity-cap N --max-idle-cap S
        Validates the manifest against the schema below. Prints "EXPERIMENT-REFUSED: <reason>" lines and exits 1 for
        any violation; otherwise prints nothing and exits 0.
  render --manifest FILE --out FILE
        Resolves the run-time tokens of a committed manifest (below) into FILE (private, mode 0600) and prints, for the shell:
        "ACCOUNT <12 digits>" (capture only, never display), "SUBST <token> <value with the account as <acct>>" per token used,
        "TOKENIZED yes|no" and "RENDERED-SHA256 <hex>". Exit 1 with "EXPERIMENT-REFUSED: <reason>" lines on any problem; exit 4 when the file is not valid JSON (the schema check then reports it).
  args --manifest FILE
        Prints the run-bounded-pipeline.sh arguments the manifest implies, one per line (flag, then value on its own
        line), so the shell can build an argument array without word splitting.
  show --manifest FILE --what W      id | region | metrics (one URI per line) | limits
  write-record --root R --out FILE --manifest FILE --manifest-sha256 H --kind planned|result --commit C --at T
               [--started T] [--pipeline-run-id ID] [--exit-code N] [--status S]
               [--rendered-sha256 H] [--substitutions-json J]
        Create the private experiment run record (or result), exclusively (safeio).

Run-time tokens (the bucket names embed the AWS account id, so a committed manifest holds only tokens, never an account id):
  ${SCHOLARCHAIN_ARTIFACTS_BUCKET}  ${SCHOLARCHAIN_LOGS_BUCKET}  ${SCHOLARCHAIN_RAW_BUCKET}  ${SCHOLARCHAIN_REPORTS_BUCKET}
        the value comes from the environment variable of the same name and must match scholarchain-<env>-<12 digits>-<suffix> with the
        suffix artifacts, logs, raw or reports respectively; every bucket used must share one environment and one account;
  ${SCHOLARCHAIN_RUN_PREFIX}        ^run-[a-z0-9][a-z0-9-]{1,27}$ (the deployer's operator_run_prefix).
  Any other ${...}, an empty or unset value, or a value of another shape is refused; a raw 12-digit account id inside a committed string is
  refused too. Tokens are replaced in every string VALUE (not in keys) BEFORE the schema check, so the S3 URI rules apply to the real
  names. The committed file (and its sha256) is what git and the approval record bind; the rendered sha256 and the substituted values
  (account shown as <acct>) are recorded in experiment-record.json.

Manifest schema (JSON, "scholarchain.experiment-manifest.v1"). Unknown keys are rejected at every level.
  schema        "scholarchain.experiment-manifest.v1"                                                   required
  id            ^[a-z0-9][a-z0-9-]{2,29}$                                                                required
  description   non-empty string                                                                         required
  budget        REQUIRED object, all four members required
      max_usd              number > 0, at most the per-run cap EMR_MAX_RUN_USD (becomes --budget-usd)
      max_runtime_minutes  integer 10..PIPELINE_MAX_RUNTIME_MINUTES (becomes --max-runtime-minutes)
      max_capacity         integer, must equal 1 + core_count + max_task_count, at most PIPELINE_MAX_CAPACITY
      region               AWS region name (becomes --region)
  teardown      REQUIRED object
      mode                      "auto-termination" (the only value: the cluster tears itself down when idle)
      max_idle_timeout_seconds  integer 60..PIPELINE_MAX_IDLE_TIMEOUT_SECONDS (becomes --max-idle-seconds)
  pipeline      REQUIRED object: instance_type, core_count, max_task_count (optional, default 0), input_prefix,
                output_prefix, hadoop_submit_jar, hadoop_libjars, hadoop_config, er_jar, er_policy, er_config,
                spark_config_template, datasets_manifest (each becomes the matching run-bounded-pipeline.sh flag), and
                artifact_sha256 {name: 64 hex} (becomes --artifact-sha256 name=hex; "job-jar" is required)
  metrics       REQUIRED object: locations, a non-empty list of s3:// URIs where the metric exports will be
                (the cluster id is NOT in the manifest: it is created by Terraform and passed with --cluster-id)
"""
import argparse
import decimal
import hashlib
import importlib.util
import json
import os
import re
import sys

SCHEMA = "scholarchain.experiment-manifest.v1"
TOP_KEYS = {"schema", "id", "description", "budget", "teardown", "pipeline", "metrics"}
BUDGET_KEYS = {"max_usd", "max_runtime_minutes", "max_capacity", "region"}
TEARDOWN_KEYS = {"mode", "max_idle_timeout_seconds"}
PIPELINE_STRINGS = (
    "instance_type", "input_prefix", "output_prefix", "hadoop_submit_jar", "hadoop_libjars", "hadoop_config", "er_jar",
    "er_policy", "er_config", "spark_config_template", "datasets_manifest",
)
PIPELINE_KEYS = set(PIPELINE_STRINGS) | {"core_count", "max_task_count", "artifact_sha256"}
ARTIFACT_NAMES = {"hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar", "hadoop-config", "er-policy", "er-config", "spark-config-template"}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,29}$")
REGION = re.compile(r"^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
S3_URI = re.compile(r"^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/.+")
SAFE_VALUE = re.compile(r"^[^\x00-\x1f\x7f]{1,1024}$")


BUCKET_TOKENS = {
    "SCHOLARCHAIN_ARTIFACTS_BUCKET": "artifacts",
    "SCHOLARCHAIN_LOGS_BUCKET": "logs",
    "SCHOLARCHAIN_RAW_BUCKET": "raw",
    "SCHOLARCHAIN_REPORTS_BUCKET": "reports",
}
RUN_PREFIX_TOKEN = "SCHOLARCHAIN_RUN_PREFIX"
RUN_PREFIX_RE = re.compile(r"^run-[a-z0-9][a-z0-9-]{1,27}$")
PROJECT_BUCKET_RE = re.compile(r"^scholarchain-([a-z0-9-]+)-([0-9]{12})-([a-z]+)$")
TOKEN_RE = re.compile(r"\$\{([^}]*)\}")
ACCOUNT_LITERAL_RE = re.compile(r"(?<![0-9A-Za-z])[0-9]{12}(?![0-9A-Za-z])")


def _strings(value, out):
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, list):
        for item in value:
            _strings(item, out)
    elif isinstance(value, dict):
        for item in value.values():
            _strings(item, out)
    return out


def _substitute(value, values):
    if isinstance(value, str):
        return TOKEN_RE.sub(lambda m: values[m.group(1)], value)
    if isinstance(value, list):
        return [_substitute(item, values) for item in value]
    if isinstance(value, dict):
        return {key: _substitute(item, values) for key, item in value.items()}
    return value


def resolve_tokens(document, environ):
    """Returns (resolved document, {token: value}, problems). The committed document is not modified."""
    problems, used = [], {}
    strings = _strings(document, [])
    for text in strings:
        if ACCOUNT_LITERAL_RE.search(text):
            problems.append("a committed string holds a raw 12-digit account id; use the ${SCHOLARCHAIN_*_BUCKET} tokens (the bucket names embed the account id)")
        if re.search(r"\$[A-Za-z_]", text):
            problems.append("a string holds a $NAME without braces; write ${NAME} (only the documented tokens are resolved)")
        if text.count("${") != len(TOKEN_RE.findall(text)):
            problems.append("a string holds a malformed token (an unclosed ${...})")
        for name in TOKEN_RE.findall(text):
            if name not in BUCKET_TOKENS and name != RUN_PREFIX_TOKEN:
                problems.append("unknown token ${%s} (allowed: %s)" % (name, ", ".join(sorted(list(BUCKET_TOKENS) + [RUN_PREFIX_TOKEN]))))
            else:
                used[name] = None
    envs, accounts = set(), set()
    for name in sorted(used):
        value = environ.get(name, "")
        if not value:
            problems.append("${%s} is used but the environment variable %s is empty or unset" % (name, name))
            continue
        if name == RUN_PREFIX_TOKEN:
            if not RUN_PREFIX_RE.match(value):
                problems.append("%s must match %s" % (name, RUN_PREFIX_RE.pattern))
                continue
        else:
            match = PROJECT_BUCKET_RE.match(value)
            if not match or match.group(3) != BUCKET_TOKENS[name]:
                problems.append("%s must be a project bucket name scholarchain-<env>-<12 digits>-%s" % (name, BUCKET_TOKENS[name]))
                continue
            envs.add(match.group(1))
            accounts.add(match.group(2))
        used[name] = value
    if len(envs) > 1 or len(accounts) > 1:
        problems.append("the bucket tokens name different environments or accounts; they must all belong to one stack")
    if problems:
        return None, used, problems
    return _substitute(document, used), used, []


def redact_value(value):
    match = PROJECT_BUCKET_RE.match(value)
    return "scholarchain-%s-<acct>-%s" % (match.group(1), match.group(3)) if match else value


def cmd_render(args):
    try:
        document = load(args.manifest)
    except (OSError, ValueError) as error:
        print("EXPERIMENT-REFUSED: the manifest is missing or not valid JSON (%s)" % type(error).__name__)
        return 4  # the shell lets the schema check report this one (same step and wording as before tokens existed)
    resolved, used, problems = resolve_tokens(document, os.environ)
    if problems:
        for problem in sorted(set(problems)):
            print("EXPERIMENT-REFUSED: %s" % problem)
        return 1
    if used:
        data = (json.dumps(resolved, indent=2, sort_keys=True) + "\n").encode("utf-8")
    else:
        with open(args.manifest, "rb") as handle:
            data = handle.read()
    fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    accounts = sorted({PROJECT_BUCKET_RE.match(v).group(2) for n, v in used.items() if n in BUCKET_TOKENS})
    for account in accounts:
        print("ACCOUNT %s" % account)
    for name in sorted(used):
        print("SUBST %s %s" % (name, redact_value(used[name])))
    print("TOKENIZED %s" % ("yes" if used else "no"))
    print("RENDERED-SHA256 %s" % hashlib.sha256(data).hexdigest())
    return 0


def _safeio():
    spec = importlib.util.spec_from_file_location("sc_safeio", os.path.join(os.path.dirname(os.path.abspath(__file__)), "safeio.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reject_constant(name):
    raise ValueError("non-finite JSON constant %s" % name)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_constant)


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value not in (float("inf"), float("-inf"))


def problems_for(document, limits):
    problems = []
    if not isinstance(document, dict):
        return ["the manifest must be a JSON object"]
    for key in sorted(set(document) - TOP_KEYS):
        problems.append("unknown top-level key: %s" % key)
    if document.get("schema") != SCHEMA:
        problems.append("schema must be %s" % SCHEMA)
    if not isinstance(document.get("id"), str) or not ID.match(document.get("id", "")):
        problems.append("id must match %s" % ID.pattern)
    if not isinstance(document.get("description"), str) or not document.get("description", "").strip():
        problems.append("description must be a non-empty string")
    budget = document.get("budget")
    if not isinstance(budget, dict):
        problems.append("the budget section is required (max_usd, max_runtime_minutes, max_capacity, region)")
        budget = {}
    else:
        for key in sorted(set(budget) - BUDGET_KEYS):
            problems.append("unknown budget key: %s" % key)
        for key in sorted(BUDGET_KEYS - set(budget)):
            problems.append("budget.%s is required" % key)
        if "max_usd" in budget:
            value = budget["max_usd"]
            if not is_number(value) or value <= 0:
                problems.append("budget.max_usd must be a number greater than 0")
            elif value > limits["max_run_usd"]:
                problems.append("budget.max_usd %s exceeds the per-run cap %s USD" % (value, limits["max_run_usd"]))
        if "max_runtime_minutes" in budget:
            value = budget["max_runtime_minutes"]
            if not is_int(value) or value < 10 or value > limits["max_runtime_cap"]:
                problems.append("budget.max_runtime_minutes must be an integer from 10 to %d" % limits["max_runtime_cap"])
        if "max_capacity" in budget:
            value = budget["max_capacity"]
            if not is_int(value) or value < 1 or value > limits["max_capacity_cap"]:
                problems.append("budget.max_capacity must be an integer from 1 to %d" % limits["max_capacity_cap"])
        if "region" in budget and (not isinstance(budget["region"], str) or not REGION.match(budget["region"])):
            problems.append("budget.region must be an AWS region name")
    teardown = document.get("teardown")
    if not isinstance(teardown, dict):
        problems.append("the teardown section is required (mode, max_idle_timeout_seconds)")
        teardown = {}
    else:
        for key in sorted(set(teardown) - TEARDOWN_KEYS):
            problems.append("unknown teardown key: %s" % key)
        for key in sorted(TEARDOWN_KEYS - set(teardown)):
            problems.append("teardown.%s is required" % key)
        if "mode" in teardown and teardown["mode"] != "auto-termination":
            problems.append("teardown.mode must be auto-termination")
        if "max_idle_timeout_seconds" in teardown:
            value = teardown["max_idle_timeout_seconds"]
            if not is_int(value) or value < 60 or value > limits["max_idle_cap"]:
                problems.append("teardown.max_idle_timeout_seconds must be an integer from 60 to %d" % limits["max_idle_cap"])
    pipeline = document.get("pipeline")
    if not isinstance(pipeline, dict):
        problems.append("the pipeline section is required")
        pipeline = {}
    else:
        for key in sorted(set(pipeline) - PIPELINE_KEYS):
            problems.append("unknown pipeline key: %s" % key)
        for key in PIPELINE_STRINGS:
            if key not in pipeline:
                problems.append("pipeline.%s is required" % key)
            elif not isinstance(pipeline[key], str) or not SAFE_VALUE.match(pipeline[key]):
                problems.append("pipeline.%s must be a plain string" % key)
        for key in ("input_prefix", "output_prefix"):
            if isinstance(pipeline.get(key), str) and not S3_URI.match(pipeline[key]):
                problems.append("pipeline.%s must be s3://bucket/non-empty-prefix" % key)
        if not is_int(pipeline.get("core_count")) or not 1 <= pipeline.get("core_count", 0) <= 10:
            problems.append("pipeline.core_count must be an integer from 1 to 10")
        tasks = pipeline.get("max_task_count", 0)
        if not is_int(tasks) or not 0 <= tasks <= 10:
            problems.append("pipeline.max_task_count must be an integer from 0 to 10")
        shas = pipeline.get("artifact_sha256")
        if not isinstance(shas, dict) or "job-jar" not in shas:
            problems.append("pipeline.artifact_sha256 must be an object that includes job-jar")
        else:
            for name, value in shas.items():
                if name not in ARTIFACT_NAMES:
                    problems.append("pipeline.artifact_sha256 names an unknown artifact: %s" % name)
                elif not isinstance(value, str) or not HEX64.match(value):
                    problems.append("pipeline.artifact_sha256.%s must be 64 lowercase hex" % name)
        if is_int(pipeline.get("core_count")) and is_int(tasks) and is_int(budget.get("max_capacity")):
            if 1 + pipeline["core_count"] + tasks != budget["max_capacity"]:
                problems.append("budget.max_capacity %s must equal 1 + core_count + max_task_count = %d" % (budget["max_capacity"], 1 + pipeline["core_count"] + tasks))
    metrics = document.get("metrics")
    if not isinstance(metrics, dict) or set(metrics) != {"locations"}:
        problems.append("the metrics section is required and holds exactly: locations")
    else:
        locations = metrics["locations"]
        if not isinstance(locations, list) or not locations or not all(isinstance(x, str) and S3_URI.match(x) for x in locations):
            problems.append("metrics.locations must be a non-empty list of s3:// URIs")
    return problems


def _limits(args):
    return {
        "max_run_usd": float(args.max_run_usd),
        "max_runtime_cap": args.max_runtime_cap,
        "max_capacity_cap": args.max_capacity_cap,
        "max_idle_cap": args.max_idle_cap,
    }


def cmd_validate(args):
    try:
        document = load(args.manifest)
    except (OSError, ValueError) as error:
        print("EXPERIMENT-REFUSED: the manifest is missing or not valid JSON (%s)" % type(error).__name__)
        return 1
    problems = problems_for(document, _limits(args))
    for problem in problems:
        print("EXPERIMENT-REFUSED: %s" % problem)
    return 1 if problems else 0


def cmd_args(args):
    document = load(args.manifest)
    pipeline = document["pipeline"]
    budget = document["budget"]
    out = [
        ("--region", budget["region"]),
        ("--budget-usd", format(decimal.Decimal(str(budget["max_usd"])), "f")),
        ("--max-runtime-minutes", str(budget["max_runtime_minutes"])),
        ("--max-idle-seconds", str(document["teardown"]["max_idle_timeout_seconds"])),
        ("--instance-type", pipeline["instance_type"]),
        ("--core-count", str(pipeline["core_count"])),
        ("--max-task-count", str(pipeline.get("max_task_count", 0))),
    ]
    for key in PIPELINE_STRINGS:
        if key == "instance_type":
            continue
        out.append(("--" + key.replace("_", "-"), pipeline[key]))
    for name in sorted(pipeline["artifact_sha256"]):
        out.append(("--artifact-sha256", "%s=%s" % (name, pipeline["artifact_sha256"][name])))
    for flag, value in out:
        print(flag)
        print(value)
    return 0


def cmd_show(args):
    document = load(args.manifest)
    if args.what == "id":
        print(document["id"])
    elif args.what == "region":
        print(document["budget"]["region"])
    elif args.what == "metrics":
        for location in document["metrics"]["locations"]:
            print(location)
    elif args.what == "limits":
        budget = document["budget"]
        print("max_usd=%s max_runtime_minutes=%s max_capacity=%s region=%s idle_timeout_seconds<=%s" % (budget["max_usd"], budget["max_runtime_minutes"], budget["max_capacity"], budget["region"], document["teardown"]["max_idle_timeout_seconds"]))
    else:
        return 2
    return 0


def cmd_write_record(args):
    safeio = _safeio()
    document = load(args.manifest)
    base = {
        "experiment_id": document["id"],
        "manifest_sha256": args.manifest_sha256,
        "commit": args.commit,
        "region": document["budget"]["region"],
        "resource_limits": {
            "max_usd": document["budget"]["max_usd"],
            "max_runtime_minutes": document["budget"]["max_runtime_minutes"],
            "max_capacity": document["budget"]["max_capacity"],
            "teardown": document["teardown"],
            "instance_type": document["pipeline"]["instance_type"],
        },
        "metric_locations": document["metrics"]["locations"],
    }
    if args.rendered_sha256:
        base["rendered_manifest_sha256"] = args.rendered_sha256
        base["token_substitutions"] = json.loads(args.substitutions_json or "{}")
    if args.kind == "planned":
        base.update({"schema": "scholarchain.experiment-run-record.v1", "start_time_utc": args.at, "pipeline_run_id": args.pipeline_run_id})
    else:
        base.update(
            {
                "schema": "scholarchain.experiment-run-result.v1",
                "start_time_utc": args.started,
                "end_time_utc": args.at,
                "pipeline_run_id": args.pipeline_run_id,
                "exit_code": args.exit_code,
                "status": args.status,
            }
        )
    try:
        handle = safeio.open_new(args.root, args.out)
    except safeio.Refused as error:
        print("EXPERIMENT-REFUSED: %s" % error)
        return 1
    with handle:
        handle.write((json.dumps(base, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("wrote %s %s" % (args.kind, os.path.basename(args.out)))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate")
    p.add_argument("--manifest", required=True)
    p.add_argument("--max-run-usd", required=True)
    p.add_argument("--max-runtime-cap", type=int, required=True)
    p.add_argument("--max-capacity-cap", type=int, required=True)
    p.add_argument("--max-idle-cap", type=int, required=True)
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("render")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("args")
    p.add_argument("--manifest", required=True)
    p.set_defaults(fn=cmd_args)
    p = sub.add_parser("show")
    p.add_argument("--manifest", required=True)
    p.add_argument("--what", required=True)
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("write-record")
    for name in ("root", "out", "manifest", "manifest-sha256", "commit", "at"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--kind", choices=["planned", "result"], required=True)
    p.add_argument("--started", default="")
    p.add_argument("--pipeline-run-id", default="")
    p.add_argument("--exit-code", type=int, default=0)
    p.add_argument("--status", default="")
    p.add_argument("--rendered-sha256", default="")
    p.add_argument("--substitutions-json", default="")
    p.set_defaults(fn=cmd_write_record)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
