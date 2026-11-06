#!/usr/bin/env python3
"""Plan builder for run-bounded-pipeline.sh (stdlib; python3 -I). Creates no cloud resource and calls no cloud API.

  plan --out FILE [options]     validate every input and ceiling, hash the local inputs, render the six EMR steps
                                (stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out)
                                and the canonical run configuration. Writes one JSON document (mode 0600) to FILE and
                                prints nothing else. Refusals print "PIPELINE-REFUSED: <reason>" and exit 1.
  show --plan FILE --what W     print one field of a plan: run-config-sha256 | summary | step-count |
                                step-name:N | step-seconds:N | step-json:N | step-body:N | step-args:N |
                                step-arglens:N | field:KEY
  step-manifest [--write|--check]  the sha256 pin of the installed step programs (infra/terraform/emr-step-programs.json)
  verify-class-origin ...       the driver and executor class-origin verifier, exactly the program the cluster
                                step runs (argv: probe-json spark-version scala-version jar-dir job-jar job-sha256)
  write-manifest --root R --out FILE --plan FILE --kind planned|result [...]
                                create the private run manifest (planned) or the result record, exclusively (safeio)
  check-hadoop-config FILE      the Phase 4 ceiling check on a local prep config (argv ceilings via --ceiling K=V)
  check-cluster ...             --execute only: describe-cluster, get-auto-termination-policy and list-instance-groups
                                outputs must show a WAITING or RUNNING cluster WITH an auto-termination idle timeout
                                (60..max) and only the approved instance type and counts

Design notes
  * The run configuration is canonical JSON (sorted keys, no spaces). Its sha256 is what the human approves
    (APPROVED_RUN_CONFIG_SHA256). It holds everything that decides what the run does and costs, and nothing volatile
    (no run id, no clock, no commit).
  * Every cluster-side step is `bash -c <short launcher> sc-step <sha256> <STEP> KEY=VALUE...` on the primary node
    (command-runner.jar). The launcher verifies the bootstrap-installed runner scripts/emr/sc-step.sh against the sha256
    computed here and execs it (finding C1: EMR allows at most 10,280 characters per step argument, so the static program
    text is installed, not embedded). The plan builder refuses any argument over the pinned limit.
  * Item 1 (carried 12D finding): `timeout` kills only the client. Every YARN-submitting body therefore tags the YARN
    application with the run id and, when the runtime cap fires or the step is interrupted, lists the applications by
    that tag and kills each one (yarn application -list -appTags <run-id>; yarn application -kill <id>).
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import sys

SCHEMA_CONFIG = "scholarchain.bounded-run-config.v1"
SCHEMA_MANIFEST = "scholarchain.bounded-run-manifest.v1"
SCHEMA_RESULT = "scholarchain.bounded-run-result.v1"
STEP_ORDER = ("stage-in", "hadoop-prep", "entity-resolution", "spark-class-origin", "spark-job", "copy-out")
SOURCES = ("dblp", "openalex", "crossref", "orcid")
# Same field list and order as scripts/phase4-emr-smoke.sh (a test compares them).
CEILING_FIELDS = (
    "maxLocalSampleRecords",
    "reducerCount",
    "maxCandidateBlockSize",
    "maxCandidatePairsPerBlock",
    "maxAuthorTeamSize",
    "maxRecordBytes",
    "maxXmlEntityExpansion",
)
ARTIFACTS = ("hadoop-submit-jar", "hadoop-libjars", "er-jar", "job-jar")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{5,63}$")
REGION = re.compile(r"^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CLUSTER = re.compile(r"^j-[A-Z0-9]{3,32}$")
INSTANCE_TYPE = re.compile(r"^[a-z][a-z0-9]{1,8}\.[a-z0-9]{3,12}$")
S3_URI = re.compile(r"^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/.+")
SPARK_REQUIRED = {
    "spark.yarn.jars": "local:/opt/scholarchain-runtime/jars/*",
    "spark.yarn.populateHadoopClasspath": "false",
    "spark.authenticate": "true",
    "spark.network.crypto.enabled": "true",
    "spark.network.crypto.authEngineVersion": "1",
    "spark.network.crypto.saslFallback": "false",
    "spark.io.encryption.enabled": "true",
    "spark.dynamicAllocation.enabled": "true",
    "spark.dynamicAllocation.shuffleTracking.enabled": "true",
}


class Refused(Exception):
    pass


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(document):
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def q(value):
    return shlex.quote(str(value))


# ---------------------------------------------------------------------------------------------------------------------
# The installed step programs (finding C1). The step runner, the Phase 4 ceiling program, the class-origin verifier and the
# spark-config renderer are FILES under scripts/emr/. Each is ONE program run locally (tests, dry run) and on the cluster
# primary node as a bootstrap-installed, sha256-verified copy, so what is tested is what runs. Their sha256 values are part of
# the approved run configuration and of infra/terraform/emr-step-programs.json (the Terraform guard compares the tfvars
# artifact hashes with that manifest).
# ---------------------------------------------------------------------------------------------------------------------
EMR_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "emr"))
STEP_MANIFEST = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "infra", "terraform", "emr-step-programs.json"))
STEP_SCRIPT = "sc-step.sh"
CEILING_PROGRAM = "sc-ceiling-check.py"
CLASS_ORIGIN_PROGRAM = "sc-class-origin-verify.py"
RENDER_PROGRAM = "sc-render-spark-config.py"
STEP_PROGRAMS = (STEP_SCRIPT, CEILING_PROGRAM, CLASS_ORIGIN_PROGRAM, RENDER_PROGRAM)
# AWS API reference, HadoopJarStepConfig.Args: every string may be at most 10,280 characters. The pinned release.conf key
# PIPELINE_STEP_ARG_MAX_CHARS may lower the limit; it may never raise it above what EMR accepts.
EMR_API_ARG_LIMIT = 10280
SAFE_NODE_DIR = re.compile(r"^/[A-Za-z0-9_.+/-]+$")


def program_path(name):
    return os.path.join(EMR_DIR, name)


def program_text(name):
    with open(program_path(name), encoding="utf-8") as handle:
        return handle.read()


def program_shas():
    """sha256 of every installed step program, computed from the repository files."""
    try:
        return {name: sha256_file(program_path(name)) for name in STEP_PROGRAMS}
    except OSError as error:
        raise Refused("a step program under scripts/emr/ cannot be read (%s)" % type(error).__name__)


def step_manifest(bin_dir, shas):
    return {"bin_dir": bin_dir, "programs": shas}


def check_step_manifest(shas):
    """The reviewed Terraform-side pin (infra/terraform/emr-step-programs.json) must name exactly the repository files' hashes,
    so a Terraform plan and this run configuration can never disagree about the installed programs. (The node directory is
    compared with PIPELINE_STEP_BIN_DIR by the tests and by tests/phase13c.tftest.hcl, not here: the offline tests point the
    pinned directory at a fake node.)"""
    try:
        with open(STEP_MANIFEST, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except (OSError, ValueError):
        raise Refused("STEP-PROGRAM-DRIFT: infra/terraform/emr-step-programs.json is missing or not valid JSON")
    if not isinstance(manifest, dict) or manifest.get("programs") != shas:
        raise Refused(
            "STEP-PROGRAM-DRIFT: infra/terraform/emr-step-programs.json differs from the files under scripts/emr/; "
            "regenerate it with `python3 -I scripts/lib/pipeline.py step-manifest --write` and update the tfvars artifact hashes"
        )


# ---------------------------------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------------------------------
def read_spark_conf(path):
    """Spark properties as an ordered list of (key, value); validates the decision 12-10 requirements."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        raise Refused("the Spark property file %s cannot be read" % path)
    pairs = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition(" ")
        value = value.strip()
        if not key.startswith("spark.") or not value:
            raise Refused("malformed Spark property line: %s" % stripped[:60])
        pairs.append((key, value))
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise Refused("the Spark property file repeats a key")
    table = dict(pairs)
    for key, wanted in SPARK_REQUIRED.items():
        if table.get(key) != wanted:
            raise Refused("decision 12-10 requires %s=%s (found %s)" % (key, wanted, table.get(key, "nothing")))
    codecs = table.get("spark.hadoop.io.compression.codecs", "")
    if not codecs or "lzo" in codecs.lower():
        raise Refused("spark.hadoop.io.compression.codecs must be set and must not list an LZO codec")
    if table.get("spark.hadoop.fs.defaultFS") != "file:///":
        raise Refused("spark.hadoop.fs.defaultFS must be file:/// (G1 option ii: EFS staging)")
    for forbidden in ("spark.yarn.tags", "spark.yarn.appMasterEnv.JAVA_HOME", "spark.executorEnv.JAVA_HOME", "spark.dynamicAllocation.maxExecutors", "spark.yarn.stagingDir"):
        if forbidden in table:
            raise Refused("%s is set by the step itself (run id, resolved Java 17, capacity, EFS staging) and must not be in the file" % forbidden)
    return pairs


def check_hadoop_config(path, ceilings):
    """Runs the Phase 4 ceiling program on a local prep config. Returns a problem string or None."""
    import subprocess

    completed = subprocess.run(
        [sys.executable, "-I", program_path(CEILING_PROGRAM), path] + [str(ceilings[field]) for field in CEILING_FIELDS],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return completed.stderr.strip().replace("bounded-pipeline: ", "")
    return None


def read_datasets(path):
    try:
        with open(path, encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, ValueError):
        raise Refused("the datasets manifest %s is missing or not valid JSON" % path)
    if not isinstance(document, dict) or sorted(document) != sorted(SOURCES):
        raise Refused("the datasets manifest must name exactly %s" % ", ".join(SOURCES))
    out = {}
    for source in SOURCES:
        entry = document[source]
        if not isinstance(entry, dict) or sorted(entry) != ["retrieval", "snapshot"]:
            raise Refused("datasets manifest entry %s needs exactly snapshot and retrieval" % source)
        for field in ("snapshot", "retrieval"):
            if not isinstance(entry[field], str) or not SAFE_TOKEN.match(entry[field]):
                raise Refused("datasets manifest %s.%s is not a safe token" % (source, field))
        out[source] = {"snapshot": entry["snapshot"], "retrieval": entry["retrieval"]}
    return out


def is_remote(ref):
    return ref.startswith(("s3://", "s3a://", "s3n://", "hdfs://"))


def hash_artifacts(refs, supplied):
    """sha256 for each artifact: computed from a local regular file, or supplied for a remote or node-local path."""
    hashes = {}
    for name in ARTIFACTS:
        ref = refs.get(name)
        computed = None
        if ref and not is_remote(ref) and os.path.isfile(ref):
            computed = sha256_file(ref)
        given = supplied.get(name)
        if given is not None and not HEX64.match(given):
            raise Refused("--artifact-sha256 %s is not 64 lowercase hex" % name)
        if computed and given and computed != given:
            raise Refused("the local file for %s has sha256 %s but --artifact-sha256 says %s" % (name, computed, given))
        value = given or computed
        if not value:
            raise Refused("no sha256 for %s: pass --artifact-sha256 %s=<64 hex> (a remote or node-local reference cannot be hashed here)" % (name, name))
        hashes[name] = value
    return hashes


# ---------------------------------------------------------------------------------------------------------------------
# Step commands (finding C1). Each EMR step is `bash -c <launcher> sc-step <sha256> <STEP> KEY=VALUE...`: a short static
# launcher, the sha256 of the installed step runner (computed here from scripts/emr/sc-step.sh) and the per-run parameters
# as separate arguments. The launcher verifies the installed runner against that sha256 on the node (fail closed) and then
# execs it; the runner (scripts/emr/sc-step.sh) is the B1 wrapper (on-node `timeout --kill-after`, own process group, TERM
# then KILL, STEP-WARN) plus the six step bodies, and verifies each installed Python program against its own sha256 before
# running it. No step argument comes near EMR's 10,280 character limit; build_plan still refuses any that would.
# ---------------------------------------------------------------------------------------------------------------------
LAUNCHER = (
    "set -euo pipefail; f=%s; want=\"$1\"; shift; "
    "printf '%%s  %%s\\n' \"${want}\" \"${f}\" | sha256sum -c --status - || "
    "{ printf 'STEP-FAIL sc-step: sha256 mismatch for %%s: the installed step runner is not the approved one\\n' \"${f}\" >&2; exit 1; }; "
    "exec bash \"${f}\" \"$@\""
)


def launcher(step_bin_dir):
    return LAUNCHER % q(step_bin_dir.rstrip("/") + "/" + STEP_SCRIPT)


def kv(key, value):
    return "%s=%s" % (key, value)


def step_params(name, cfg):
    """The KEY=VALUE parameters of one step, in a stable order. The allow-list per step is in scripts/emr/sc-step.sh."""
    sha = cfg["artifact_sha256"]
    refs = cfg["refs"]
    programs = cfg["step_programs_sha256"]
    params = [
        kv("STEP_SECONDS", cfg["step_seconds"][name]),
        kv("KILL_AFTER", cfg["kill_after_seconds"]),
        kv("RUN_ID", cfg["run_id"]),
        kv("TAG", cfg["yarn_tag"]),
        kv("MNT", cfg["efs_mount"]),
    ]
    if name == "stage-in":
        params += [kv("INPUT_PREFIX", cfg["input_prefix"].rstrip("/") + "/"), kv("REGION", cfg["region"]), kv("MAX_INPUT_BYTES", cfg["max_input_bytes"])]
    elif name == "hadoop-prep":
        params += [
            kv("SUBMIT_JAR_REF", refs["hadoop-submit-jar"]),
            kv("SUBMIT_JAR_SHA", sha["hadoop-submit-jar"]),
            kv("LIBJARS_REF", refs["hadoop-libjars"]),
            kv("LIBJARS_SHA", sha["hadoop-libjars"]),
            kv("CONFIG_REF", refs["hadoop-config"]),
            kv("CONFIG_SHA", sha["hadoop-config"]),
            kv("CEILINGS", " ".join(str(cfg["ceilings"][field]) for field in CEILING_FIELDS)),
            kv("CEILING_PY_SHA", programs[CEILING_PROGRAM]),
        ]
        for source in SOURCES:
            params += [kv(source.upper() + "_SNAPSHOT", cfg["datasets"][source]["snapshot"]), kv(source.upper() + "_RETRIEVAL", cfg["datasets"][source]["retrieval"])]
    elif name == "entity-resolution":
        params += [
            kv("JAVA_HOME_FILE", cfg["java_home_file"]),
            kv("ER_XMX", cfg["er_xmx"]),
            kv("ER_JAR_REF", refs["er-jar"]),
            kv("ER_JAR_SHA", sha["er-jar"]),
            kv("ER_POLICY_REF", refs["er-policy"]),
            kv("ER_POLICY_SHA", sha["er-policy"]),
            kv("ER_CONFIG_REF", refs["er-config"]),
            kv("ER_CONFIG_SHA", sha["er-config"]),
        ]
    elif name in ("spark-class-origin", "spark-job"):
        params += [
            kv("JAVA_HOME_FILE", cfg["java_home_file"]),
            kv("RUNTIME_DIR", cfg["runtime_dir"]),
            kv("JOB_JAR", cfg["job_jar_path"]),
            kv("JOB_JAR_SHA", sha["job-jar"]),
            kv("MAX_EXECUTORS", cfg["max_executors"]),
            kv("EXPECTED_SPARK_VERSION", cfg["expected_spark_version"]),
            kv("EXPECTED_SCALA_VERSION", cfg["expected_scala_version"]),
            kv("CLASS_ORIGIN_PY_SHA", programs[CLASS_ORIGIN_PROGRAM]),
        ]
        if name == "spark-job":
            params += [kv("RENDER_PY_SHA", programs[RENDER_PROGRAM]), kv("TEMPLATE_REF", refs["spark-config-template"]), kv("TEMPLATE_SHA", sha["spark-config-template"])]
        params += [kv("SPARK_CONF", "%s=%s" % (key, value)) for key, value in cfg["spark_conf"]]
    elif name == "copy-out":
        params += [kv("OUTPUT_PREFIX", cfg["output_prefix"].rstrip("/") + "/" + cfg["run_id"]), kv("REGION", cfg["region"]), kv("MAX_COPYOUT_BYTES", cfg["max_copyout_bytes"])]
    return params


def step_args(name, cfg):
    """The EMR step's HadoopJarStepConfig.Args list for one step."""
    return ["bash", "-c", launcher(cfg["step_bin_dir"]), "sc-step", cfg["step_programs_sha256"][STEP_SCRIPT], name] + step_params(name, cfg)


def render_command(args):
    """The step as a readable shell command (printed in the dry run); `bash -c <this text>` runs exactly what EMR would."""
    return " \\\n  ".join(q(arg) for arg in args) + "\n"


def arg_lengths(args):
    return [len(arg) for arg in args]


def arg_name(arg):
    match = re.match(r"^([A-Z][A-Z0-9_]*)=", arg)
    if match:
        return match.group(1)
    return "launcher" if arg.startswith("set -euo pipefail") else "argument"


def check_arg_lengths(name, args, limit):
    """Finding C1: refuse before any cloud call when a step argument exceeds the pinned EMR limit."""
    for index, arg in enumerate(args):
        if len(arg) > limit:
            raise Refused(
                "STEP-ARG-TOO-LONG: step %s argument %d (%s) has %d characters, over the limit of %d (EMR HadoopJarStepConfig.Args allows at most %d per string); nothing was submitted"
                % (name, index, arg_name(arg), len(arg), limit, EMR_API_ARG_LIMIT)
            )


def length_line(name, args, limit):
    lengths = arg_lengths(args)
    return "%s limit=%d count=%d max=%d total=%d lengths=%s" % (name, limit, len(lengths), max(lengths), sum(lengths), ",".join(str(n) for n in lengths))


def step_json(name, run_id, args):
    step = {
        "Name": ("ScholarChain-%s-%s" % (run_id, name))[:256],
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {"Jar": "command-runner.jar", "Args": args},
    }
    return json.dumps([step], separators=(",", ":"))


# ---------------------------------------------------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------------------------------------------------
def parse_weights(text):
    weights = {}
    for item in text.split():
        name, _, value = item.partition("=")
        if name not in STEP_ORDER or not value.isdigit() or int(value) < 1:
            raise Refused("PIPELINE_STEP_WEIGHTS entry %r is invalid" % item)
        weights[name] = int(value)
    if sorted(weights) != sorted(STEP_ORDER):
        raise Refused("PIPELINE_STEP_WEIGHTS must name exactly the six steps")
    if sum(weights.values()) > 100:
        raise Refused("PIPELINE_STEP_WEIGHTS sum to more than 100")
    return weights


def need(args, name, label):
    value = getattr(args, name)
    if value is None or value == "":
        raise Refused("missing required value: %s" % label)
    return value


def build_plan(args):
    run_id = need(args, "run_id", "--run-id")
    if not SAFE_RUN_ID.match(run_id):
        raise Refused("the run id must be 6-64 characters of letters, digits, '.', '_' or '-'")
    region = need(args, "region", "--region")
    if not REGION.match(region):
        raise Refused("the region %r is not an AWS region name" % region)
    cluster_id = need(args, "cluster_id", "--cluster-id")
    if not CLUSTER.match(cluster_id):
        raise Refused("the cluster id must look like j-XXXXXXXXXXXXX")
    if not INSTANCE_TYPE.match(args.instance_type or ""):
        raise Refused("--instance-type must look like m5.xlarge")
    if args.core_count < 1 or args.core_count > 10 or args.max_task_count < 0 or args.max_task_count > 10:
        raise Refused("core count must be 1-10 and task count 0-10")
    capacity = 1 + args.core_count + args.max_task_count
    if capacity > args.max_capacity_cap:
        raise Refused("capacity %d (1 primary + %d core + %d task) exceeds the cap %d (PIPELINE_MAX_CAPACITY)" % (capacity, args.core_count, args.max_task_count, args.max_capacity_cap))
    if args.max_runtime_minutes < 10 or args.max_runtime_minutes > args.max_runtime_cap:
        raise Refused("--max-runtime-minutes must be between 10 and the cap %d (PIPELINE_MAX_RUNTIME_MINUTES)" % args.max_runtime_cap)
    input_prefix = need(args, "input_prefix", "--input-prefix")
    output_prefix = need(args, "output_prefix", "--output-prefix")
    if not S3_URI.match(input_prefix):
        raise Refused("--input-prefix must be s3://bucket/non-empty-prefix")
    if not S3_URI.match(output_prefix):
        raise Refused("--output-prefix must be s3://bucket/non-empty-prefix")
    refs = {}
    for name, flag in (
        ("hadoop-submit-jar", "--hadoop-submit-jar"),
        ("hadoop-libjars", "--hadoop-libjars"),
        ("hadoop-config", "--hadoop-config"),
        ("er-jar", "--er-jar"),
        ("er-policy", "--er-policy"),
        ("er-config", "--er-config"),
        ("spark-config-template", "--spark-config-template"),
    ):
        refs[name] = need(args, name.replace("-", "_"), flag)
    supplied = {}
    for item in args.artifact_sha256 or []:
        name, _, value = item.partition("=")
        if name not in ARTIFACTS + ("hadoop-config", "er-policy", "er-config", "spark-config-template"):
            raise Refused("--artifact-sha256 names an unknown artifact: %s" % name)
        supplied[name] = value
    artifact_sha = hash_artifacts(refs, {k: v for k, v in supplied.items() if k in ARTIFACTS})
    # Configuration and template files: hashed when they are local files, else the human supplies the sha256.
    for name in ("hadoop-config", "er-policy", "er-config", "spark-config-template"):
        ref = refs[name]
        computed = sha256_file(ref) if (not is_remote(ref) and os.path.isfile(ref)) else None
        given = supplied.get(name)
        if given is not None and not HEX64.match(given):
            raise Refused("--artifact-sha256 %s is not 64 lowercase hex" % name)
        if computed and given and computed != given:
            raise Refused("the local file for %s has sha256 %s but --artifact-sha256 says %s" % (name, computed, given))
        if not (computed or given):
            raise Refused("no sha256 for %s: pass --artifact-sha256 %s=<64 hex>" % (name, name))
        artifact_sha[name] = computed or given
    ceilings = {field: int(getattr(args, "ceiling_%d" % index)) for index, field in enumerate(CEILING_FIELDS)}
    if os.path.isfile(refs["hadoop-config"]):
        problem = check_hadoop_config(refs["hadoop-config"], ceilings)
        if problem:
            raise Refused("ceiling rejected the prep config %s: %s" % (os.path.basename(refs["hadoop-config"]), problem))
    spark_conf = read_spark_conf(args.spark_conf_file)
    # Finding C1: the installed step programs. Their sha256 values come from the repository files, are cross-checked with the
    # Terraform-side manifest, and become part of the approved run configuration.
    step_bin_dir = args.step_bin_dir or ""
    if not SAFE_NODE_DIR.match(step_bin_dir) or ".." in step_bin_dir.split("/") or "//" in step_bin_dir or step_bin_dir.endswith("/"):
        raise Refused("PIPELINE_STEP_BIN_DIR must be a plain absolute node directory without '..' or a trailing slash")
    arg_limit = args.step_arg_max_chars
    if arg_limit < 1000 or arg_limit > EMR_API_ARG_LIMIT:
        raise Refused("PIPELINE_STEP_ARG_MAX_CHARS %d must be from 1000 to %d (the EMR HadoopJarStepConfig.Args limit)" % (arg_limit, EMR_API_ARG_LIMIT))
    step_programs = program_shas()
    check_step_manifest(step_programs)
    datasets = read_datasets(need(args, "datasets_manifest", "--datasets-manifest"))
    weights = parse_weights(args.step_weights)
    total_seconds = args.max_runtime_minutes * 60
    step_seconds = {name: max(args.min_step_seconds, total_seconds * weights[name] // 100) for name in STEP_ORDER}
    if sum(step_seconds.values()) > total_seconds:
        raise Refused("the step timeouts (each at least %d s) exceed the maximum runtime of %d s; lengthen --max-runtime-minutes" % (args.min_step_seconds, total_seconds))
    max_executors = max(1, (args.core_count + args.max_task_count) * args.max_executors_per_node)
    estimate = json.loads(args.estimate_json)
    teardown = {"mode": "auto-termination", "max_idle_timeout_seconds": args.max_idle_timeout_seconds}
    config = {
        "schema": SCHEMA_CONFIG,
        "action": args.action,
        "region": region,
        "cluster_id": cluster_id,
        "instance_type": args.instance_type,
        "primary_count": 1,
        "core_count": args.core_count,
        "max_task_count": args.max_task_count,
        "max_capacity": capacity,
        "max_runtime_minutes": args.max_runtime_minutes,
        "budget_usd": args.budget_usd,
        "estimate": estimate,
        "teardown": teardown,
        "input_prefix": input_prefix,
        "output_prefix": output_prefix,
        "refs": refs,
        "artifact_sha256": artifact_sha,
        "runtime_archive_sha256": args.runtime_archive_sha256,
        "spark_conf": [list(pair) for pair in spark_conf],
        "spark_conf_sha256": sha256_file(args.spark_conf_file),
        "datasets": datasets,
        "datasets_manifest_sha256": sha256_file(args.datasets_manifest),
        "ceilings": ceilings,
        "max_input_bytes": args.max_input_bytes,
        "max_copyout_bytes": args.max_copyout_bytes,
        "efs_mount": args.efs_mount,
        "runtime_dir": args.runtime_dir,
        "job_jar_path": args.job_jar_path,
        "java_home_file": args.java_home_file,
        "er_xmx": args.er_xmx,
        "expected_spark_version": args.expected_spark_version,
        "expected_scala_version": args.expected_scala_version,
        "max_executors": max_executors,
        "step_bin_dir": step_bin_dir,
        "step_programs_sha256": step_programs,
        "kill_after_seconds": args.kill_after_seconds,
        "step_seconds": step_seconds,
        "steps": list(STEP_ORDER),
    }
    if config["job_jar_path"].startswith("local:") or ".." in config["job_jar_path"].split("/"):
        raise Refused("the job jar path must be a plain absolute node path")
    run_config_sha = hashlib.sha256(canonical(config).encode("utf-8")).hexdigest()
    # Run-specific values are added after hashing: the run id is also the YARN tag.
    runtime_cfg = dict(config)
    runtime_cfg["run_id"] = run_id
    runtime_cfg["yarn_tag"] = run_id
    steps = []
    for name in STEP_ORDER:
        argv = step_args(name, runtime_cfg)
        check_arg_lengths(name, argv, arg_limit)
        steps.append(
            {
                "name": name,
                "timeout_seconds": step_seconds[name],
                "args": argv,
                "arg_lengths": arg_lengths(argv),
                "arg_limit": arg_limit,
                "body": render_command(argv),
                "add_steps_json": step_json(name, run_id, argv),
            }
        )
    return {
        "schema": "scholarchain.bounded-run-plan.v1",
        "run_id": run_id,
        "yarn_tag": run_id,
        "run_config": config,
        "run_config_sha256": run_config_sha,
        "steps": steps,
        "output_locations": {part: "%s/%s/%s/" % (output_prefix.rstrip("/"), run_id, part) for part in ("hadoop", "er", "spark", "results", "config")},
    }


def write_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def cmd_plan(args):
    try:
        plan = build_plan(args)
    except Refused as error:
        print("PIPELINE-REFUSED: %s" % error)
        return 1
    except (ValueError, OSError) as error:
        print("PIPELINE-REFUSED: invalid input (%s)" % type(error).__name__)
        return 1
    write_private(args.out, json.dumps(plan, indent=1, sort_keys=True))
    return 0


def load_plan(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def cmd_show(args):
    plan = load_plan(args.plan)
    what = args.what
    if what == "run-config-sha256":
        print(plan["run_config_sha256"])
    elif what == "step-count":
        print(len(plan["steps"]))
    elif what.startswith("step-name:"):
        print(plan["steps"][int(what.split(":")[1])]["name"])
    elif what.startswith("step-seconds:"):
        print(plan["steps"][int(what.split(":")[1])]["timeout_seconds"])
    elif what.startswith("step-json:"):
        print(plan["steps"][int(what.split(":")[1])]["add_steps_json"])
    elif what.startswith("step-args:"):
        print(json.dumps(plan["steps"][int(what.split(":")[1])]["args"], separators=(",", ":")))
    elif what.startswith("step-arglens:"):
        step = plan["steps"][int(what.split(":")[1])]
        print(length_line(step["name"], step["args"], step["arg_limit"]))
    elif what.startswith("step-body:"):
        sys.stdout.write(plan["steps"][int(what.split(":")[1])]["body"])
    elif what.startswith("field:"):
        value = plan["run_config"]
        for part in what.split(":", 1)[1].split("."):
            value = value[part]
        print(value if isinstance(value, str) else json.dumps(value, sort_keys=True))
    elif what == "summary":
        config = plan["run_config"]
        print("run-id: %s" % plan["run_id"])
        print("yarn-tag: %s" % plan["yarn_tag"])
        print("cluster-id: %s" % config["cluster_id"])
        print("region: %s" % config["region"])
        print("instance-type: %s primary=1 core=%d max-task=%d max-capacity=%d" % (config["instance_type"], config["core_count"], config["max_task_count"], config["max_capacity"]))
        print("max-runtime-minutes: %d" % config["max_runtime_minutes"])
        print("budget-usd: %s" % config["budget_usd"])
        print("estimate-usd: %s (%s)" % (config["estimate"]["estimate_usd"], config["estimate"]["formula"]))
        print("teardown: %s (the cluster must have an auto-termination idle timeout of at most %d s)" % (config["teardown"]["mode"], config["teardown"]["max_idle_timeout_seconds"]))
        print("input-prefix: %s" % config["input_prefix"])
        print("output-prefix: %s/%s/" % (config["output_prefix"].rstrip("/"), plan["run_id"]))
        for name, value in sorted(config["artifact_sha256"].items()):
            print("artifact-sha256 %s: %s" % (name, value))
        print("step-bin-dir: %s" % config["step_bin_dir"])
        for name, value in sorted(config["step_programs_sha256"].items()):
            print("step-program-sha256 %s: %s" % (name, value))
        print("spark-conf-sha256: %s" % config["spark_conf_sha256"])
        print("datasets-manifest-sha256: %s" % config["datasets_manifest_sha256"])
        for source in SOURCES:
            print("dataset %s: snapshot=%s retrieval=%s" % (source, config["datasets"][source]["snapshot"], config["datasets"][source]["retrieval"]))
        print("ceilings: " + " ".join("%s<=%s" % (field, config["ceilings"][field]) for field in CEILING_FIELDS))
        print("data-ceilings: input<=%s bytes copy-out<=%s bytes" % (config["max_input_bytes"], config["max_copyout_bytes"]))
        for step in plan["steps"]:
            print("step %s: timeout=%ds" % (step["name"], step["timeout_seconds"]))
    else:
        print("unknown --what", file=sys.stderr)
        return 2
    return 0


def cmd_verify_class_origin(args):
    sys.argv = ["class-origin"] + list(args.argv)
    exec(compile(program_text(CLASS_ORIGIN_PROGRAM), CLASS_ORIGIN_PROGRAM, "exec"), {"__name__": "__main__"})
    return 0


def cmd_step_manifest(args):
    text = json.dumps(step_manifest(args.step_bin_dir, program_shas()), indent=2, sort_keys=True) + "\n"
    if args.check:
        try:
            with open(STEP_MANIFEST, encoding="utf-8") as handle:
                current = handle.read()
        except OSError:
            current = None
        if current != text:
            print("STEP-PROGRAM-DRIFT: infra/terraform/emr-step-programs.json differs from scripts/emr/ (run with --write)")
            return 1
        print("step manifest ok")
        return 0
    if args.write:
        with open(STEP_MANIFEST, "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote infra/terraform/emr-step-programs.json")
        return 0
    sys.stdout.write(text)
    return 0


def cmd_check_cluster(args):
    problems = []

    def load(path, label):
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            problems.append("%s output is unreadable or not JSON" % label)
            return None

    described = load(args.describe, "describe-cluster")
    policy = load(args.policy, "get-auto-termination-policy")
    groups = load(args.groups, "list-instance-groups")
    state = idle = None
    if isinstance(described, dict):
        cluster = described.get("Cluster") or {}
        if cluster.get("Id") != args.cluster_id:
            problems.append("describe-cluster returned another cluster id")
        state = (cluster.get("Status") or {}).get("State")
        if state not in ("WAITING", "RUNNING"):
            problems.append("the cluster state is %s: steps are submitted only to a WAITING or RUNNING cluster" % state)
    if isinstance(policy, dict):
        idle = (policy.get("AutoTerminationPolicy") or {}).get("IdleTimeout")
        if isinstance(idle, bool) or not isinstance(idle, int):
            problems.append("the cluster has NO auto-termination policy: forced auto-termination is required")
        elif idle < 60 or idle > args.max_idle_seconds:
            problems.append("the auto-termination idle timeout %s s is outside 60..%d s" % (idle, args.max_idle_seconds))
    total = 0
    limits = {"MASTER": 1, "CORE": args.core_count, "TASK": args.max_task_count}
    if isinstance(groups, dict):
        found = groups.get("InstanceGroups")
        if not isinstance(found, list) or not found:
            problems.append("the cluster reports no instance groups")
            found = []
        for group in found:
            kind = group.get("InstanceGroupType")
            if kind not in limits:
                problems.append("unknown instance group type %s" % kind)
                continue
            if group.get("InstanceType") != args.instance_type:
                problems.append("%s group uses %s, not the approved %s" % (kind, group.get("InstanceType"), args.instance_type))
            requested = group.get("RequestedInstanceCount")
            running = group.get("RunningInstanceCount")
            if not isinstance(requested, int) or not isinstance(running, int):
                problems.append("%s group has no integer instance counts" % kind)
                continue
            if max(requested, running) > limits[kind]:
                problems.append("%s group has %d instances, above the approved %d" % (kind, max(requested, running), limits[kind]))
            total += max(requested, running)
        if total > args.max_capacity:
            problems.append("the cluster holds %d instances, above the approved maximum capacity %d" % (total, args.max_capacity))
    for problem in problems:
        print("CLUSTER-CHECK-FAILED: %s" % problem)
    if problems:
        return 1
    print("CLUSTER-CHECK: ok state=%s auto_termination_idle_timeout_seconds=%s instances=%d type=%s" % (state, idle, total, args.instance_type))
    return 0


def cmd_check_hadoop_config(args):
    ceilings = {}
    for item in args.ceiling:
        key, _, value = item.partition("=")
        ceilings[key] = value
    missing = [f for f in CEILING_FIELDS if f not in ceilings]
    if missing:
        print("PIPELINE-REFUSED: missing ceiling %s" % ",".join(missing))
        return 2
    problem = check_hadoop_config(args.file, ceilings)
    if problem:
        print("PIPELINE-REFUSED: %s" % problem)
        return 1
    return 0


def cmd_write_manifest(args):
    safeio = _load("sc_safeio", "safeio.py")
    plan = load_plan(args.plan)
    config = plan["run_config"]
    if args.kind == "planned":
        document = {
            "schema": SCHEMA_MANIFEST,
            "run_id": plan["run_id"],
            "yarn_tag": plan["yarn_tag"],
            "action": config["action"],
            "commit": args.commit,
            "clean_tree": True,
            "started_utc": args.at,
            "region": config["region"],
            "account_sha256": args.account_sha256,
            "cluster_id": config["cluster_id"],
            "run_config_sha256": plan["run_config_sha256"],
            "approval_record_sha256": args.approval_sha256,
            "prespend_receipt_sha256": args.prespend_sha256,
            "dataset_snapshots": config["datasets"],
            "datasets_manifest_sha256": config["datasets_manifest_sha256"],
            "artifact_sha256": config["artifact_sha256"],
            "runtime_archive_sha256": config["runtime_archive_sha256"],
            "spark_conf_sha256": config["spark_conf_sha256"],
            "estimate": config["estimate"],
            "budget_usd": config["budget_usd"],
            "limits": {
                "max_capacity": config["max_capacity"],
                "max_runtime_minutes": config["max_runtime_minutes"],
                "ceilings": config["ceilings"],
                "max_input_bytes": config["max_input_bytes"],
                "max_copyout_bytes": config["max_copyout_bytes"],
            },
            "teardown": config["teardown"],
            "output_locations": plan["output_locations"],
            "steps": [{"name": s["name"], "timeout_seconds": s["timeout_seconds"]} for s in plan["steps"]],
        }
    else:
        outcomes = []
        for item in args.outcome or []:
            name, _, state = item.partition("=")
            outcomes.append({"step": name, "state": state})
        document = {
            "schema": SCHEMA_RESULT,
            "run_id": plan["run_id"],
            "run_config_sha256": plan["run_config_sha256"],
            "ended_utc": args.at,
            "status": args.status,
            "step_outcomes": outcomes,
        }
    try:
        handle = safeio.open_new(args.root, args.out)
    except safeio.Refused as error:
        print("PIPELINE-REFUSED: %s" % error)
        return 1
    with handle:
        handle.write((json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print("wrote %s %s" % (args.kind, os.path.basename(args.out)))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--out", required=True)
    for name in (
        "run-id", "action", "region", "cluster-id", "instance-type", "budget-usd", "input-prefix", "output-prefix", "hadoop-submit-jar",
        "hadoop-libjars", "hadoop-config", "er-jar", "er-policy", "er-config", "spark-config-template", "datasets-manifest",
        "spark-conf-file", "efs-mount", "runtime-dir", "job-jar-path", "java-home-file", "er-xmx", "expected-spark-version",
        "expected-scala-version", "step-weights", "runtime-archive-sha256", "estimate-json", "step-bin-dir",
    ):
        p.add_argument("--" + name)
    for name in ("core-count", "max-task-count", "max-runtime-minutes", "max-capacity-cap", "max-runtime-cap", "max-input-bytes", "max-copyout-bytes", "max-idle-timeout-seconds", "max-executors-per-node", "kill-after-seconds", "min-step-seconds", "step-arg-max-chars"):
        p.add_argument("--" + name, type=int, required=True)
    for index in range(len(CEILING_FIELDS)):
        p.add_argument("--ceiling-%d" % index, required=True)
    p.add_argument("--artifact-sha256", action="append")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("show")
    p.add_argument("--plan", required=True)
    p.add_argument("--what", required=True)
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("verify-class-origin")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_verify_class_origin)
    p = sub.add_parser("step-manifest")
    p.add_argument("--step-bin-dir", default="/opt/scholarchain-spike/bin")
    p.add_argument("--write", action="store_true", help="write infra/terraform/emr-step-programs.json instead of printing it")
    p.add_argument("--check", action="store_true", help="exit 1 when the committed manifest differs from scripts/emr/")
    p.set_defaults(fn=cmd_step_manifest)
    p = sub.add_parser("check-hadoop-config")
    p.add_argument("file")
    p.add_argument("--ceiling", action="append", required=True)
    p.set_defaults(fn=cmd_check_hadoop_config)
    p = sub.add_parser("check-cluster")
    for name in ("describe", "policy", "groups", "cluster-id", "instance-type"):
        p.add_argument("--" + name, required=True)
    for name in ("core-count", "max-task-count", "max-capacity", "max-idle-seconds"):
        p.add_argument("--" + name, type=int, required=True)
    p.set_defaults(fn=cmd_check_cluster)
    p = sub.add_parser("write-manifest")
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--kind", choices=["planned", "result"], required=True)
    p.add_argument("--at", required=True)
    p.add_argument("--commit", default="")
    p.add_argument("--account-sha256", default="")
    p.add_argument("--approval-sha256", default="")
    p.add_argument("--prespend-sha256", default="")
    p.add_argument("--status", default="")
    p.add_argument("--outcome", action="append")
    p.set_defaults(fn=cmd_write_manifest)
    return parser


if __name__ == "__main__":
    namespace = build_parser().parse_args(sys.argv[1:])
    sys.exit(namespace.fn(namespace))
