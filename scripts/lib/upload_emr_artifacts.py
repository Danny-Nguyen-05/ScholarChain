#!/usr/bin/env python3
"""Planning, approval and manifest helper of scripts/upload-emr-artifacts.sh (stdlib only; run as python3 -I).

The shell script owns every AWS call; this module owns the pure decisions so they are testable without AWS: which local files
are uploaded, under which keys of the artifacts bucket, with which sha256, whether the human approval record matches the plan,
and the evidence manifest. The remaining steps (existing / compare / put / verify) reuse scripts/lib/upload_slice.py, which only
reads the plan's "files" list (key, bytes, checksum_sha256_b64). This module never calls a cloud API and never prints a credential.

Key layout (all in the project ARTIFACTS bucket, the only bucket the EMR module accepts for its artifact URIs and the instance role
reads; the final contract of the deployer's operator-pipeline grant: create-only below emr/<run_prefix>/), below emr/<run_prefix>/:
  bin/bootstrap.sh                        the EMR bootstrap action (emr_config.bootstrap_uri)
  jars/hadoop-submit.jar                  role hadoop-submit-jar of target/emr-artifacts/emr-artifact-manifest.json
  jars/hadoop-bundle.jar                  role hadoop-dependency-bundle
  jars/entity-resolution.jar              role entity-resolution-job-jar
  jars/spark-job.jar                      role spark-job-jar (emr_config.job_jar_uri); every file's sha256 and size must equal the manifest
  steps/<name>                            the four step programs (emr_config.extra_artifacts), sha256 = infra/terraform/emr-step-programs.json
  config/er-policy.json                   --er-policy FILE
  config/er-config.json                   --er-config FILE
  config/spark-config-template.json       --spark-config-template FILE
  config/hadoop-config.json               --hadoop-config FILE (Phase 15 P1: the Hadoop prep config; manifest pipeline.hadoop_config
                                          s3://<artifacts>/emr/<run_prefix>/config/hadoop-config.json, sha pin name hadoop-config)
  input/<label>/datasets/samples/...      one Phase 4 layout input dataset per --input-dataset LABEL=DIR (labels size-25, size-50, size-100 in
                                          Phase 15A); run-bounded-pipeline.sh --input-prefix s3://<artifacts>/emr/<run>/input/<label>
Pipeline output is NOT uploaded here: --output-prefix s3://<artifacts>/pipeline/<run>/15a/size-N is written by the EMR instance role.

Subcommands (exit 0 ok, 1 refused with an "UPLOAD-REFUSED: <reason>" line on stdout, 2 usage)
  scan      --repo-root R --run-prefix P --out PLAN.json --bootstrap F --steps-dir D --step-manifest F --artifact-manifest F
            [--er-policy F] [--er-config F] [--spark-config-template F] [--hadoop-config F] --input-dataset LABEL=DIR...
            --max-input-bytes N
  list      --plan PLAN.json [--only-file F | --skip-file F]   rows "<index>TAB<local path>TAB<key>TAB<base64 sha256>"
  approval  --file F --plan-sha X --account-id ID --region R   check the human approval record
  hints     --plan PLAN.json --bucket B --step-manifest F   print the s3 URIs and sha256 values to copy into emr_config and the pipeline flags
  manifest  --plan PLAN.json --results R.jsonl --bucket-label L --region R --created-utc T --commit C   JSON on stdout
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("upload_slice", os.path.join(HERE, "upload_slice.py"))
slice_lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(slice_lib)
Refused = slice_lib.Refused
refuse = slice_lib.refuse

SCHEMA = "scholarchain.emr-upload-manifest.v1"
ACTION = "upload-emr-artifacts"
MANIFEST_SCHEMA = "scholarchain.emr-artifact-manifest.v1"
ROLES = ("hadoop-dependency-bundle", "hadoop-submit-jar", "entity-resolution-job-jar", "spark-job-jar")
# The fixed object names the experiment manifests and the tfvars example refer to (flat, one per role).
JAR_NAMES = {
    "hadoop-submit-jar": "hadoop-submit.jar",
    "hadoop-dependency-bundle": "hadoop-bundle.jar",
    "entity-resolution-job-jar": "entity-resolution.jar",
    "spark-job-jar": "spark-job.jar",
}
CONFIG_OPTIONS = (("er_policy", "er-policy.json"), ("er_config", "er-config.json"), ("spark_config_template", "spark-config-template.json"),
                  ("hadoop_config", "hadoop-config.json"))
LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,19}$")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._=+@-]{0,199}$")
SAMPLE_FILES = (
    "datasets/samples/dblp/linked-records.xml",
    "datasets/samples/openalex/works.jsonl",
    "datasets/samples/crossref/works.jsonl",
    "datasets/samples/orcid/records.jsonl",
)
MAX_DATASETS = 3
MAX_FILES = 5000
MAX_TOTAL_BYTES = 4 * 1024 ** 3
MAX_CONFIG_BYTES = 8 * 1024 * 1024


def check_run_prefix(prefix):
    return slice_lib.check_prefix(prefix)


def entry(path, key, klass, root_prefix):
    """One planned upload: the local file (regular, not a link), its key (inside emr/<run_prefix>/) and its sha256."""
    size = slice_lib.lstat_regular(path, os.path.basename(path))
    if size > slice_lib.MAX_FILE_BYTES:
        refuse("%s is %d bytes; one PutObject request is limited to 5 GiB" % (os.path.basename(path), size))
    slice_lib.check_key(key, root_prefix)
    raw = slice_lib.sha256_file(path)
    return {
        "path": os.path.abspath(path), "key": key, "bytes": size, "sha256": raw.hex(),
        "checksum_sha256_b64": base64.b64encode(raw).decode("ascii"), "class": klass,
    }


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        refuse("%s is missing or not valid JSON" % what)


def step_entries(args, root_prefix):
    manifest = load_json(args.step_manifest, "the step program manifest")
    programs = manifest.get("programs") if isinstance(manifest, dict) else None
    if not isinstance(programs, dict) or len(programs) != 4:
        refuse("the step program manifest must list exactly four programs")
    out = []
    for name in sorted(programs):
        if not NAME_RE.match(name):
            refuse("step program name %s is not accepted" % name)
        path = os.path.join(args.steps_dir, name)
        if not os.path.lexists(path):
            refuse("step program %s is missing from %s" % (name, os.path.basename(args.steps_dir.rstrip("/"))))
        item = entry(path, "%s/steps/%s" % (root_prefix, name), "step-program", root_prefix)
        if item["sha256"] != programs[name]:
            refuse("STEP-PROGRAM-DRIFT: %s has sha256 %s but the Terraform pin (emr-step-programs.json) says %s; regenerate the pin or restore the file" % (name, item["sha256"], programs[name]))
        out.append(item)
    return out


def jar_entries(args, root_prefix):
    manifest = load_json(args.artifact_manifest, "the EMR artifact manifest")
    if not isinstance(manifest, dict) or manifest.get("schema") != MANIFEST_SCHEMA:
        refuse("the EMR artifact manifest does not carry the schema %s" % MANIFEST_SCHEMA)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        refuse("the EMR artifact manifest has no artifacts list")
    roles = [a.get("role") for a in artifacts if isinstance(a, dict)]
    if sorted(roles) != sorted(ROLES):
        refuse("the EMR artifact manifest must hold exactly the roles %s (found %s)" % (", ".join(ROLES), ", ".join(sorted(str(r) for r in roles))))
    repo = os.path.realpath(args.repo_root)
    out = []
    for artifact in sorted(artifacts, key=lambda a: a["role"]):
        rel = artifact.get("path")
        if not isinstance(rel, str) or rel.startswith("/") or ".." in rel.split("/") or not rel:
            refuse("artifact %s has an unsafe path in the manifest" % artifact["role"])
        path = os.path.join(repo, rel)
        if not os.path.lexists(path):
            refuse("artifact %s is missing locally (%s); build it first (sbt packageEmr)" % (artifact["role"], rel))
        if not os.path.realpath(path).startswith(repo + os.sep):
            refuse("artifact %s resolves outside the repository" % artifact["role"])
        item = entry(path, "%s/jars/%s" % (root_prefix, JAR_NAMES[artifact["role"]]), "jar:" + artifact["role"], root_prefix)
        if item["sha256"] != artifact.get("sha256") or item["bytes"] != artifact.get("bytes"):
            refuse("artifact %s differs from the manifest (sha256 or size): rebuild it or regenerate the manifest; nothing is uploaded" % artifact["role"])
        out.append(item)
    return out


def config_entries(args, root_prefix):
    out = []
    for option, name in CONFIG_OPTIONS:
        path = getattr(args, option)
        if not path:
            continue
        if not os.path.lexists(path):
            refuse("--%s file %s does not exist" % (option.replace("_", "-"), os.path.basename(path)))
        if slice_lib.lstat_regular(path, os.path.basename(path)) > MAX_CONFIG_BYTES:
            refuse("config file %s is larger than %d bytes" % (os.path.basename(path), MAX_CONFIG_BYTES))
        out.append(entry(path, "%s/config/%s" % (root_prefix, name), "config:" + name, root_prefix))
    return out


def dataset_entries(args, root_prefix):
    datasets = args.input_dataset or []
    if not datasets:
        refuse("at least one --input-dataset LABEL=DIR is required")
    if len(datasets) > MAX_DATASETS:
        refuse("at most %d input datasets (one per Phase 15 run) are accepted" % MAX_DATASETS)
    seen, out, summary = set(), [], []
    for spec in datasets:
        label, sep, directory = spec.partition("=")
        if not sep or not LABEL_RE.match(label):
            refuse("--input-dataset must be LABEL=DIR with LABEL matching ^[a-z0-9][a-z0-9-]{1,19}$")
        if label in seen:
            refuse("input dataset label %s is used twice" % label)
        seen.add(label)
        if not os.path.isdir(directory) or os.path.islink(directory):
            refuse("input dataset %s: the directory does not exist or is a link" % label)
        base = os.path.realpath(directory)
        for rel in SAMPLE_FILES:
            candidate = os.path.join(base, rel)
            if not os.path.lexists(candidate):
                refuse("input dataset %s lacks %s (the Phase 4 layout run-bounded-pipeline.sh stages in)" % (label, rel))
        top = os.path.join(base, "datasets", "samples")
        for part in (os.path.join(base, "datasets"), top):
            if os.path.islink(part) or not os.path.isdir(part):
                refuse("input dataset %s: %s is not a real directory" % (label, os.path.relpath(part, base)))
        files, total, skipped = [], 0, 0
        for current, dirs, names in os.walk(top, followlinks=False):
            dirs.sort()
            for d in dirs:
                if os.path.islink(os.path.join(current, d)):
                    refuse("input dataset %s holds a symbolic link; links are never uploaded" % label)
            for name in sorted(names):
                full = os.path.join(current, name)
                if name.startswith(".") or name.startswith("_"):
                    skipped += 1
                    continue
                rel = os.path.relpath(full, base).replace(os.sep, "/")
                item = entry(full, "%s/input/%s/%s" % (root_prefix, label, rel), "input:" + label, root_prefix)
                total += item["bytes"]
                files.append(item)
        if total > args.max_input_bytes:
            refuse("input dataset %s has %d bytes; the pipeline refuses an input prefix above %d bytes (PIPELINE_MAX_INPUT_BYTES)" % (label, total, args.max_input_bytes))
        out.extend(files)
        summary.append((label, len(files), total, skipped))
    return out, summary


def cmd_scan(args):
    prefix = check_run_prefix(args.run_prefix)
    root_prefix = "emr/" + prefix
    if not os.path.lexists(args.bootstrap):
        refuse("the bootstrap script is missing")
    files = [entry(args.bootstrap, root_prefix + "/bin/bootstrap.sh", "bootstrap", root_prefix)]
    files += step_entries(args, root_prefix)
    files += jar_entries(args, root_prefix)
    files += config_entries(args, root_prefix)
    datasets, summary = dataset_entries(args, root_prefix)
    files += datasets
    if len(files) > MAX_FILES:
        refuse("%d files planned; the limit is %d" % (len(files), MAX_FILES))
    keys = [f["key"] for f in files]
    if len(set(keys)) != len(keys):
        refuse("two planned files share a key (a duplicate config file name?)")
    files.sort(key=lambda f: f["key"])
    total = sum(f["bytes"] for f in files)
    if total > MAX_TOTAL_BYTES:
        refuse("%d bytes planned; the limit of this tool is %d" % (total, MAX_TOTAL_BYTES))
    plan_sha = plan_hash(files)
    plan = {
        "kind": "emr-artifacts", "run_prefix": prefix, "root_prefix": root_prefix, "plan_sha256": plan_sha,
        "files": files, "total_bytes": total, "datasets": [{"label": s[0], "files": s[1], "bytes": s[2]} for s in summary],
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(plan, handle, sort_keys=True)
    print("EMR-UPLOAD: run=%s files=%d bytes=%d datasets=%d" % (prefix, len(files), total, len(summary)))
    print("PLAN-SHA256: %s" % plan_sha)
    for label, count, size, skipped in summary:
        print("EMR-INPUT-DATASET: label=%s files=%d bytes=%d skipped_hidden=%d" % (label, count, size, skipped))
    for index, item in enumerate(files):
        print("UPLOAD-FILE: %d class=%s key=%s bytes=%d sha256=%s" % (index, item["class"], item["key"], item["bytes"], item["sha256"]))
    return 0


def plan_hash(files):
    """sha256 over the sorted lines '<key> TAB <bytes> TAB <sha256> LF': what the human approves."""
    text = "".join("%s\t%d\t%s\n" % (f["key"], f["bytes"], f["sha256"]) for f in sorted(files, key=lambda f: f["key"]))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_plan(path):
    return slice_lib.load_plan(path)


def cmd_list(args):
    plan = load_plan(args.plan)
    only = slice_lib.read_indices(args.only_file) if args.only_file else None
    skip = slice_lib.read_indices(args.skip_file) if args.skip_file else set()
    for index, item in enumerate(plan["files"]):
        if (only is not None and index not in only) or index in skip:
            continue
        print("%d\t%s\t%s\t%s" % (index, item["path"], item["key"], item["checksum_sha256_b64"]))
    return 0


APPROVAL_PATTERNS = {
    "APPROVED_ACTION": re.escape(ACTION),
    "APPROVED_PLAN_SHA256": r"[0-9a-f]{64}",
    "APPROVED_ACCOUNT_SHA256": r"[0-9a-f]{64}",
    "APPROVED_REGION": r"[a-z]{2}(-[a-z0-9]+)+-[0-9]+",
}
KEY_LINE = re.compile(r"^\s*(APPROVED_[A-Za-z0-9_]*)\s*=")


def cmd_approval(args):
    """The human writes KEY=value lines, each exactly once; other text is ignored; an unknown APPROVED_* key refuses."""
    path = args.file
    if os.path.islink(path) or not os.path.isfile(path):
        refuse("the approval record does not exist or is not a regular file")
    try:
        with open(path, "rb") as handle:
            raw = handle.read(1024 * 1024 + 1)
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        refuse("the approval record cannot be read as UTF-8 text")
    if len(raw) > 1024 * 1024:
        refuse("the approval record is larger than 1 MiB")
    values, problems = {}, []
    for line in text.split("\n"):
        match = KEY_LINE.match(line)
        if not match:
            continue
        key = match.group(1)
        if key not in APPROVAL_PATTERNS:
            problems.append("unknown key %s" % key)
            continue
        strict = re.match(r"^(%s)=(.*)$" % re.escape(key), line)
        if not strict or not re.fullmatch(APPROVAL_PATTERNS[key], strict.group(2)):
            problems.append("malformed line for %s (exactly KEY=value, no spaces, quotes, indent or CR)" % key)
            continue
        if key in values:
            problems.append("duplicate %s" % key)
            continue
        values[key] = strict.group(2)
    for key in APPROVAL_PATTERNS:
        if key not in values and not any(key in p for p in problems):
            problems.append("missing %s" % key)
    if problems:
        refuse("approval record: " + "; ".join(problems))
    account_sha = hashlib.sha256(args.account_id.encode("utf-8")).hexdigest()
    expected = {"APPROVED_PLAN_SHA256": args.plan_sha, "APPROVED_ACCOUNT_SHA256": account_sha, "APPROVED_REGION": args.region}
    for key, want in expected.items():
        if values[key] != want:
            refuse("approval record: %s does not match this run (the plan, account or region differs from what was approved)" % key)
    print("APPROVAL-OK: action=%s plan_sha256=%s region=%s" % (ACTION, values["APPROVED_PLAN_SHA256"], values["APPROVED_REGION"]))
    return 0


PIPELINE_NAMES = {
    "hadoop-submit-jar": "hadoop-submit-jar", "hadoop-dependency-bundle": "hadoop-libjars", "entity-resolution-job-jar": "er-jar", "spark-job-jar": "job-jar",
}
CONFIG_PIPELINE = {"er-policy.json": "er-policy", "er-config.json": "er-config", "spark-config-template.json": "spark-config-template",
                   "hadoop-config.json": "hadoop-config"}


def cmd_hints(args):
    """What the human copies next: the emr_config values (bootstrap, job JAR, the four extra_artifacts with their dest), the sha256 values
    for experiments/scripts/render_manifests.py (--sha NAME=HEX) and the run-bounded-pipeline.sh flags. Pure text from the plan; the bucket
    is the argument (the caller shows it redacted)."""
    plan = load_plan(args.plan)
    manifest = load_json(args.step_manifest, "the step program manifest")
    bin_dir = manifest.get("bin_dir")
    if not isinstance(bin_dir, str) or not bin_dir.startswith("/"):
        refuse("the step program manifest has no bin_dir")
    uri = lambda key: "s3://%s/%s" % (args.bucket, key)
    for item in plan["files"]:
        klass = item["class"]
        if klass == "bootstrap":
            print("EMR-CONFIG: bootstrap_uri=%s bootstrap_sha256=%s" % (uri(item["key"]), item["sha256"]))
        elif klass == "jar:spark-job-jar":
            print("EMR-CONFIG: job_jar_uri=%s job_jar_sha256=%s" % (uri(item["key"]), item["sha256"]))
        elif klass == "step-program":
            name = item["key"].rsplit("/", 1)[1]
            print("EMR-CONFIG: extra_artifact uri=%s sha256=%s dest=%s/%s" % (uri(item["key"]), item["sha256"], bin_dir, name))
        if klass.startswith("jar:"):
            print("EMR-RENDER: --sha %s=%s    # ref %s" % (PIPELINE_NAMES[klass[4:]], item["sha256"], uri(item["key"])))
        elif klass.startswith("config:"):
            print("EMR-RENDER: --sha %s=%s    # ref %s" % (CONFIG_PIPELINE[klass[7:]], item["sha256"], uri(item["key"])))
    for dataset in plan["datasets"]:
        print("EMR-PIPELINE: input-prefix label=%s uri=%s files=%d bytes=%d" % (dataset["label"], uri("%s/input/%s" % (plan["root_prefix"], dataset["label"])), dataset["files"], dataset["bytes"]))
    print("EMR-PIPELINE: output prefix (written by the EMR instance role, not uploaded here): s3://%s/pipeline/%s/15a/size-N" % (args.bucket, plan["run_prefix"]))
    print("EMR-PIPELINE: the G5 runtime archive is uploaded by deploy.sh base-apply, not by this script")
    return 0


def cmd_manifest(args):
    plan = load_plan(args.plan)
    status, version = {}, {}
    with open(args.results, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("verified"):
                status[record["index"]] = record["status"]
                version[record["index"]] = record.get("version_id")
    files = []
    for index, item in enumerate(plan["files"]):
        if index not in status:
            refuse("%s was not verified; no manifest is written" % item["key"])
        files.append({
            "key": item["key"], "class": item["class"], "bytes": item["bytes"], "sha256": item["sha256"],
            "checksum_sha256_b64": item["checksum_sha256_b64"], "version_id": version.get(index), "status": status[index],
        })
    document = {
        "schema": SCHEMA, "created_utc": args.created_utc, "commit": args.commit, "bucket": args.bucket_label, "region": args.region,
        "run_prefix": plan["run_prefix"], "root_prefix": plan["root_prefix"], "plan_sha256": plan["plan_sha256"],
        "datasets": plan["datasets"],
        "totals": {"files": len(files), "bytes": plan["total_bytes"], "uploaded": sum(1 for f in files if f["status"] == "uploaded"),
                   "unchanged": sum(1 for f in files if f["status"] == "unchanged")},
        "files": files,
    }
    sys.stdout.write(json.dumps(document, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="upload_emr_artifacts.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("scan")
    p.add_argument("--repo-root", required=True)
    p.add_argument("--run-prefix", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--bootstrap", required=True)
    p.add_argument("--steps-dir", required=True)
    p.add_argument("--step-manifest", required=True)
    p.add_argument("--artifact-manifest", required=True)
    p.add_argument("--er-policy")
    p.add_argument("--er-config")
    p.add_argument("--spark-config-template")
    p.add_argument("--hadoop-config")
    p.add_argument("--input-dataset", action="append")
    p.add_argument("--max-input-bytes", type=int, required=True)
    p.set_defaults(fn=cmd_scan)
    p = sub.add_parser("list")
    p.add_argument("--plan", required=True)
    p.add_argument("--only-file")
    p.add_argument("--skip-file")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("approval")
    p.add_argument("--file", required=True)
    p.add_argument("--plan-sha", required=True)
    p.add_argument("--account-id", required=True)
    p.add_argument("--region", required=True)
    p.set_defaults(fn=cmd_approval)
    p = sub.add_parser("hints")
    p.add_argument("--plan", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--step-manifest", required=True)
    p.set_defaults(fn=cmd_hints)
    p = sub.add_parser("manifest")
    p.add_argument("--plan", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--bucket-label", required=True)
    p.add_argument("--region", required=True)
    p.add_argument("--created-utc", required=True)
    p.add_argument("--commit", required=True)
    p.set_defaults(fn=cmd_manifest)
    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except Refused as error:
        print("UPLOAD-REFUSED: %s" % error)
        return 1
    except OSError as error:
        print("UPLOAD-REFUSED: %s" % (error.strerror or error))
        return 1


if __name__ == "__main__":
    sys.exit(main())
