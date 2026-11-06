#!/usr/bin/env python3
"""Plan builder for run-bounded-pipeline.sh (stdlib; python3 -I). Creates no cloud resource and calls no cloud API.

  plan --out FILE [options]     validate every input and ceiling, hash the local inputs, render the six EMR steps
                                (stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job, copy-out)
                                and the canonical run configuration. Writes one JSON document (mode 0600) to FILE and
                                prints nothing else. Refusals print "PIPELINE-REFUSED: <reason>" and exit 1.
  show --plan FILE --what W     print one field of a plan: run-config-sha256 | summary | step-count |
                                step-name:N | step-seconds:N | step-json:N | step-body:N | field:KEY
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
  * Every cluster-side body runs through `bash -c` on the primary node (command-runner.jar), like phase4-emr-smoke.sh.
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
HADOOP_MAIN = "edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
ER_MAIN = "edu.uic.cs441.scholarchain.entityresolution.Phase5Main"
SPARK_MAIN = "edu.uic.cs441.scholarchain.spark.Phase6Main"
PROBE_MAIN = "edu.uic.cs441.scholarchain.spark.Phase12Readiness"
SOURCES = ("dblp", "openalex", "crossref", "orcid")
SAMPLE_FILES = {
    "dblp": "datasets/samples/dblp/linked-records.xml",
    "openalex": "datasets/samples/openalex/works.jsonl",
    "crossref": "datasets/samples/crossref/works.jsonl",
    "orcid": "datasets/samples/orcid/records.jsonl",
}
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
# The Phase 4 ceiling program and the class-origin verifier. Each is ONE program run locally (tests, dry run) and on the
# cluster master (embedded in the step body as a quoted heredoc), so what is tested is what runs.
# ---------------------------------------------------------------------------------------------------------------------
CEILING_PY = '''import json
import sys

FIELDS = (
    "maxLocalSampleRecords",
    "reducerCount",
    "maxCandidateBlockSize",
    "maxCandidatePairsPerBlock",
    "maxAuthorTeamSize",
    "maxRecordBytes",
    "maxXmlEntityExpansion",
)


def fail(message):
    sys.stderr.write("bounded-pipeline: %s\\n" % (message,))
    raise SystemExit(1)


def reject_non_finite(token):
    raise ValueError("non-finite JSON number: %s" % (token,))


def json_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != value or value == float("inf") or value == float("-inf"):
            return None
        return value
    return None


if len(sys.argv) != 2 + len(FIELDS):
    fail("ceiling check expected a config path and %d ceilings" % (len(FIELDS),))
limits = []
for field, raw in zip(FIELDS, sys.argv[2:]):
    if not raw.isdigit():
        fail("ceiling for %s is not an integer" % (field,))
    limits.append(int(raw))
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle, parse_constant=reject_non_finite)
except Exception as error:
    fail("prep config is not valid JSON: %s" % (error,))
if not isinstance(data, dict):
    fail("prep config root must be a JSON object")
for field, limit in zip(FIELDS, limits):
    if field not in data:
        fail("missing numeric field: %s" % (field,))
    number = json_number(data[field])
    if number is None:
        fail("%s must be a JSON number" % (field,))
    if number > limit:
        fail("%s %s exceeds ceiling %s" % (field, number, limit))
'''

CLASS_ORIGIN_PY = '''import json
import os
import sys


def fail(message):
    sys.stderr.write("CLASS-ORIGIN-FAILED: %s\\n" % (message,))
    raise SystemExit(1)


if len(sys.argv) != 7:
    fail("expected: probe-json spark-version scala-version jar-dir job-jar job-sha256")
probe, spark_v, scala_v, jar_dir, job_jar, job_sha = sys.argv[1:7]
try:
    with open(probe, encoding="utf-8") as handle:
        doc = json.load(handle)
except Exception as error:
    fail("probe result unreadable: %s" % type(error).__name__)
if not isinstance(doc, dict) or doc.get("schemaVersion") != "scholarchain.phase12-readiness.v1" or doc.get("stage") != "probe":
    fail("not a Phase 12 readiness probe result")
if doc.get("externalExecutorVerified") is not True or doc.get("distributedRequired") is not True:
    fail("the executor was not verified outside the driver process")
driver = doc.get("driver")
tasks = doc.get("taskProcesses")
if not isinstance(driver, dict) or not isinstance(tasks, list) or not tasks:
    fail("the driver or executor report is missing")
need = ("spark", "scala-library", "scala-reflect", "scala3-library")
reports = [("driver", driver)] + [("executor-%s" % t.get("executorId"), t) for t in tasks if isinstance(t, dict)]
parsed = {}
prefix = jar_dir.rstrip("/") + "/"
for role, report in reports:
    if not str(report.get("javaVersion", "")).startswith("17."):
        fail("%s runs Java %s, not 17" % (role, report.get("javaVersion")))
    if role != "driver" and report.get("executorId") in (None, "driver", "unavailable"):
        fail("%s is not an executor process" % role)
    libs = {}
    for lib in report.get("libraries") or []:
        if isinstance(lib, dict):
            libs[lib.get("component")] = lib
    for component in need:
        if component not in libs:
            fail("%s report lacks %s" % (role, component))
    if libs["spark"].get("runtimeVersion") != spark_v:
        fail("%s Spark version %s differs from the required %s" % (role, libs["spark"].get("runtimeVersion"), spark_v))
    if libs["scala-library"].get("runtimeVersion") != scala_v:
        fail("%s Scala library version %s differs from the packaged job's %s" % (role, libs["scala-library"].get("runtimeVersion"), scala_v))
    for component in ("spark", "scala-library", "scala-reflect"):
        origin = str(libs[component].get("origin"))
        if not origin.startswith(prefix):
            fail("%s loaded %s from %s, outside the runtime jar directory %s" % (role, component, origin, jar_dir))
    if not os.path.basename(str(libs["spark"]["origin"])).endswith("-%s.jar" % spark_v):
        fail("%s Spark origin %s is not a %s jar" % (role, libs["spark"]["origin"], spark_v))
    if os.path.basename(str(libs["scala-library"]["origin"])) != "scala-library-%s.jar" % scala_v:
        fail("%s Scala library origin %s is not scala-library-%s.jar" % (role, libs["scala-library"]["origin"], scala_v))
    s3 = libs["scala3-library"]
    if s3.get("origin") != job_jar or s3.get("codeSourceSha256") != job_sha:
        fail("%s scala3-library is not loaded from the packaged job jar with the approved sha256" % role)
    parsed[role] = libs
base = parsed["driver"]
for role, libs in parsed.items():
    for component in need:
        for field in ("origin", "classSha256", "codeSourceSha256"):
            if libs[component].get(field) != base[component].get(field):
                fail("%s differs between the driver and %s for %s" % (field, role, component))
print("CLASS-ORIGIN-OK: the driver and %d executor report(s) agree on Spark %s, Scala %s and the packaged job jar" % (len(tasks), spark_v, scala_v))
'''

RENDER_PY = '''import json
import sys

template, out, hadoop_run, er_run, output_root, checkpoint = sys.argv[1:7]
with open(template, encoding="utf-8") as handle:
    document = json.load(handle)
if not isinstance(document, dict):
    raise SystemExit("spark config template must be a JSON object")
overrides = {
    "hadoopRunRoot": hadoop_run,
    "entityResolutionRunRoot": er_run,
    "outputRoot": output_root,
    "checkpointDirectory": checkpoint,
}
for key in overrides:
    if key not in document:
        raise SystemExit("spark config template lacks the key %s" % key)
document.update(overrides)
with open(out, "x", encoding="utf-8") as handle:
    json.dump(document, handle, indent=2, sort_keys=True)
    handle.write("\\n")
'''


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
        [sys.executable, "-I", "-c", CEILING_PY, path] + [str(ceilings[field]) for field in CEILING_FIELDS],
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
# Step bodies (run on the primary node under `bash -c`)
# ---------------------------------------------------------------------------------------------------------------------
def prelude(name, cfg, yarn):
    kill = cfg["kill_after_seconds"]
    lines = [
        "set -euo pipefail",
        "STEP_NAME=%s" % q(name),
        "RUN_ID=%s" % q(cfg["run_id"]),
        "TAG=%s" % q(cfg["yarn_tag"]),
        "MNT=%s" % q(cfg["efs_mount"]),
        'RUN_ROOT="${MNT}/runs/${RUN_ID}"',
        "KILL_AFTER=%s" % q(kill),
        "log() { printf 'STEP-LOG %s: %s\\n' \"${STEP_NAME}\" \"$*\"; }",
        "die() { printf 'STEP-FAIL %s: %s\\n' \"${STEP_NAME}\" \"$*\" >&2; exit 1; }",
        'require_mount() { grep -q " ${MNT} " "${SC_PROC_MOUNTS:-/proc/mounts}" || die "${MNT} is not a mount point: refusing to use a local directory"; }',
        "localize() {",
        '  local src="$1" dest="$2" want="$3"',
        '  case "${src}" in',
        '    s3://*|s3a://*|s3n://*|hdfs://*) hadoop fs -copyToLocal "${src}" "${dest}" ;;',
        '    *) if [[ -f "${src}" ]]; then cp -- "${src}" "${dest}"; else die "source is not a regular file: ${src}"; fi ;;',
        "  esac",
        '  printf \'%s  %s\\n\' "${want}" "${dest}" | sha256sum -c --status - || die "sha256 mismatch for ${src}"',
        "}",
    ]
    if yarn:
        lines += [
            "# Item 1: timeout kills only the client, not the YARN application. List the applications that carry",
            "# the run id as their tag and kill each one.",
            "kill_tagged() {",
            "  local apps app",
            '  apps="$(yarn application -list -appStates NEW,NEW_SAVING,SUBMITTED,ACCEPTED,RUNNING -appTags "${TAG}" 2>/dev/null | awk \'/^application_/{print $1}\' || true)"',
            "  for app in ${apps}; do",
            '    log "killing YARN application ${app} (tag ${TAG})"',
            '    yarn application -kill "${app}" || true',
            "  done",
            "}",
            "trap 'kill_tagged' EXIT",
            "trap 'kill_tagged; exit 143' TERM INT",
            "run_bounded() {",
            '  local secs="$1" rc=0',
            "  shift",
            '  timeout --kill-after="${KILL_AFTER}" "${secs}" "$@" || rc=$?',
            '  if [[ "${rc}" -eq 124 || "${rc}" -eq 137 || "${rc}" -eq 143 ]]; then',
            '    log "runtime cap reached (exit ${rc}): killing the YARN application tagged ${TAG}"',
            "    kill_tagged",
            "  fi",
            '  return "${rc}"',
            "}",
        ]
    return lines


def java_lines(cfg):
    return [
        "JAVA_HOME_FILE=%s" % q(cfg["java_home_file"]),
        '[[ -r "${JAVA_HOME_FILE}" ]] || die "no resolved Java 17 home (${JAVA_HOME_FILE} missing): the bootstrap did not complete"',
        'JAVA_HOME="$(head -n 1 "${JAVA_HOME_FILE}")"',
        '[[ -n "${JAVA_HOME}" && -x "${JAVA_HOME}/bin/java" ]] || die "the resolved Java home is not usable"',
        '"${JAVA_HOME}/bin/java" -version 2>&1 | grep -Eq \'version "17(\\.|")\' || die "the resolved Java is not 17"',
        "export JAVA_HOME",
    ]


def body_stage_in(cfg):
    lines = prelude("stage-in", cfg, False)
    lines += [
        "require_mount",
        'DEST="${RUN_ROOT}/inputs"',
        '[[ ! -e "${RUN_ROOT}" ]] || die "${RUN_ROOT} already exists: a run directory is never reused"',
        "PREFIX=%s" % q(cfg["input_prefix"].rstrip("/") + "/"),
        "REGION=%s" % q(cfg["region"]),
        "MAX_BYTES=%s" % q(cfg["max_input_bytes"]),
        'TOTAL="$(aws s3 ls "${PREFIX}" --recursive --summarize --region "${REGION}" | awk \'/Total Size:/{print $3}\')"',
        '[[ "${TOTAL}" =~ ^[0-9]+$ ]] || die "could not read the staged input size"',
        '[[ "${TOTAL}" -le "${MAX_BYTES}" ]] || die "input ${TOTAL} bytes exceeds the ${MAX_BYTES} byte ceiling"',
        'mkdir -p "${DEST}"',
        'aws s3 cp "${PREFIX}" "${DEST}/" --recursive --region "${REGION}" --only-show-errors',
        'log "staged ${TOTAL} bytes from ${PREFIX} to ${DEST}"',
    ]
    return "\n".join(lines) + "\n"


def body_hadoop_prep(cfg):
    ceilings = cfg["ceilings"]
    inputs = cfg["datasets"]
    lines = prelude("hadoop-prep", cfg, True)
    lines += [
        "require_mount",
        'WORK="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"',
        'localize %s "${WORK}/job.jar" %s' % (q(cfg["refs"]["hadoop-submit-jar"]), q(cfg["artifact_sha256"]["hadoop-submit-jar"])),
        'localize %s "${WORK}/bundle.jar" %s' % (q(cfg["refs"]["hadoop-libjars"]), q(cfg["artifact_sha256"]["hadoop-libjars"])),
        'localize %s "${WORK}/prep-config.json" %s' % (q(cfg["refs"]["hadoop-config"]), q(cfg["artifact_sha256"]["hadoop-config"])),
        'command -v python3 >/dev/null 2>&1 || die "python3 is required to enforce the ceilings"',
        'python3 - "${WORK}/prep-config.json" ' + " ".join(str(ceilings[f]) for f in CEILING_FIELDS) + " <<'SCHOLARCHAIN_CEILING_PY'",
    ]
    lines += CEILING_PY.rstrip("\n").split("\n")
    lines += [
        "SCHOLARCHAIN_CEILING_PY",
        'export HADOOP_CLASSPATH="${WORK}/bundle.jar${HADOOP_CLASSPATH:+:$HADOOP_CLASSPATH}"',
        'IN="${RUN_ROOT}/inputs"',
        'OUT="${RUN_ROOT}/hadoop"',
        '[[ ! -e "${OUT}" ]] || die "${OUT} already exists"',
        "run_bounded %s hadoop jar \"${WORK}/job.jar\" %s \\" % (q(cfg["step_seconds"]["hadoop-prep"]), q(HADOOP_MAIN)),
        '  "-Dmapreduce.job.tags=${TAG}" -libjars "${WORK}/bundle.jar" \\',
        '  --once --execution-mode cluster --run-id "${RUN_ID}" \\',
        '  --output-root "file://${OUT}" --config "${WORK}/prep-config.json" \\',
    ]
    last = len(SOURCES) - 1
    for index, source in enumerate(SOURCES):
        tail = " \\" if index < last else ""
        lines.append(
            '  --%s "file://${IN}/%s" --%s-snapshot %s --%s-retrieval %s%s'
            % (source, SAMPLE_FILES[source], source, q(inputs[source]["snapshot"]), source, q(inputs[source]["retrieval"]), tail)
        )
    return "\n".join(lines) + "\n"


def discover_lines(tag_dir, var):
    return [
        '%s_MARKERS="$(find "${RUN_ROOT}/%s" -maxdepth 4 -name _SCHOLARCHAIN_COMPLETE -print)"' % (var, tag_dir),
        '[[ "$(printf \'%%s\\n\' "${%s_MARKERS}" | grep -c .)" -eq 1 ]] || die "expected exactly one completed run under ${RUN_ROOT}/%s"' % (var, tag_dir),
        '%s_RUN="$(dirname "${%s_MARKERS}")"' % (var, var),
    ]


def body_er(cfg):
    lines = prelude("entity-resolution", cfg, False)
    lines += ["require_mount"]
    lines += java_lines(cfg)
    lines += [
        'WORK="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"',
        'localize %s "${WORK}/er.jar" %s' % (q(cfg["refs"]["er-jar"]), q(cfg["artifact_sha256"]["er-jar"])),
        'localize %s "${WORK}/policy.json" %s' % (q(cfg["refs"]["er-policy"]), q(cfg["artifact_sha256"]["er-policy"])),
        'localize %s "${WORK}/config.json" %s' % (q(cfg["refs"]["er-config"]), q(cfg["artifact_sha256"]["er-config"])),
    ]
    lines += discover_lines("hadoop", "HADOOP")
    lines += [
        'ER_OUT="${RUN_ROOT}/er/run"',
        '[[ ! -e "${ER_OUT}" ]] || die "${ER_OUT} already exists"',
        'mkdir -p "${RUN_ROOT}/er"',
        "# Single-JVM step on the primary node (Phase5Main has no distributed mode); Java 17 was resolved at bootstrap.",
        'timeout --kill-after="${KILL_AFTER}" %s "${JAVA_HOME}/bin/java" -Xmx%s -cp "${WORK}/er.jar" %s resolve \\'
        % (q(cfg["step_seconds"]["entity-resolution"]), cfg["er_xmx"], q(ER_MAIN)),
        '  --input "${HADOOP_RUN}" --policy "${WORK}/policy.json" --config "${WORK}/config.json" \\',
        '  --llm-mode disabled --output "${ER_OUT}"',
    ]
    return "\n".join(lines) + "\n"


def spark_env_lines(cfg, name):
    lines = prelude(name, cfg, True)
    lines += ["require_mount"]
    lines += java_lines(cfg)
    lines += [
        "RUNTIME=%s" % q(cfg["runtime_dir"]),
        "JOB_JAR=%s" % q(cfg["job_jar_path"]),
        "# The portable runtime only: never the stock EMR Spark or Hadoop classpath.",
        'export SPARK_HOME="${RUNTIME}" SPARK_CONF_DIR="${RUNTIME}/conf" SPARK_SCALA_VERSION=2.13',
        'export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/etc/hadoop/conf}" YARN_CONF_DIR="${HADOOP_CONF_DIR:-/etc/hadoop/conf}"',
        'export PATH="${JAVA_HOME}/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"',
        "unset CLASSPATH SPARK_DIST_CLASSPATH HADOOP_CLASSPATH SPARK_CLASSPATH || true",
        "printf '%s  %s\\n' " + q(cfg["artifact_sha256"]["job-jar"]) + ' "${JOB_JAR}" | sha256sum -c --status - || die "the packaged job jar on this node does not have the approved sha256"',
    ]
    return lines


def spark_submit_lines(cfg, name, main, args_lines):
    confs = []
    for key, value in cfg["spark_conf"]:
        confs.append("  --conf %s \\" % q("%s=%s" % (key, value)))
    lines = [
        '"${SPARK_HOME}/bin/spark-submit" --master yarn --deploy-mode cluster --name %s \\' % q("scholarchain-%s-%s" % (name, cfg["run_id"])),
        "  --class %s \\" % q(main),
        '  --conf "spark.yarn.tags=${TAG}" \\',
        '  --conf "spark.yarn.stagingDir=file://${MNT}/staging" \\',
        '  --conf "spark.yarn.appMasterEnv.JAVA_HOME=${JAVA_HOME}" \\',
        '  --conf "spark.executorEnv.JAVA_HOME=${JAVA_HOME}" \\',
        "  --conf %s \\" % q("spark.dynamicAllocation.maxExecutors=%s" % cfg["max_executors"]),
    ]
    lines += confs
    lines += ['  "local:${JOB_JAR}" \\'] + args_lines
    return lines


def body_class_origin(cfg):
    lines = spark_env_lines(cfg, "spark-class-origin")
    lines += [
        'PROBE_SHARED="${RUN_ROOT}/probe"',
        'PROBE_OUT="${RUN_ROOT}/results/class-origin.json"',
        'mkdir -p "${PROBE_SHARED}" "${RUN_ROOT}/results" "${MNT}/staging"',
        "# Driver AND executor class-origin probe (Phase12Readiness distributed): fails closed on any version difference.",
        "run_bounded %s \\" % q(cfg["step_seconds"]["spark-class-origin"]),
    ]
    lines += spark_submit_lines(cfg, "class-origin", PROBE_MAIN, ['  probe "${PROBE_SHARED}" "${PROBE_OUT}" distributed'])
    lines += verify_lines(cfg)
    return "\n".join(lines) + "\n"


def verify_lines(cfg):
    return [
        'python3 - "${RUN_ROOT}/results/class-origin.json" %s %s %s "${JOB_JAR}" %s <<\'SCHOLARCHAIN_CLASS_ORIGIN_PY\''
        % (q(cfg["expected_spark_version"]), q(cfg["expected_scala_version"]), q(cfg["runtime_dir"].rstrip("/") + "/jars"), q(cfg["artifact_sha256"]["job-jar"]))
    ] + CLASS_ORIGIN_PY.rstrip("\n").split("\n") + ["SCHOLARCHAIN_CLASS_ORIGIN_PY"]


def body_spark_job(cfg):
    lines = spark_env_lines(cfg, "spark-job")
    lines += [
        "# Fail closed again here: the Spark job never starts without a passing class-origin result for this run.",
        '[[ -f "${RUN_ROOT}/results/class-origin.json" ]] || die "no class-origin result for this run: refusing to start the Spark job"',
    ]
    lines += verify_lines(cfg)
    lines += discover_lines("hadoop", "HADOOP")
    lines += [
        'ER_RUN="${RUN_ROOT}/er/run"',
        '[[ -d "${ER_RUN}" ]] || die "no entity-resolution output at ${ER_RUN}"',
        'SPARK_OUT="${RUN_ROOT}/spark"',
        '[[ ! -e "${SPARK_OUT}" ]] || die "${SPARK_OUT} already exists"',
        'mkdir -p "${SPARK_OUT}" "${RUN_ROOT}/spark-checkpoint" "${RUN_ROOT}/config" "${MNT}/staging"',
        'WORK="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"',
        'localize %s "${WORK}/spark-template.json" %s' % (q(cfg["refs"]["spark-config-template"]), q(cfg["artifact_sha256"]["spark-config-template"])),
        'python3 - "${WORK}/spark-template.json" "${RUN_ROOT}/config/spark-config.json" "${HADOOP_RUN}" "${ER_RUN}" "${SPARK_OUT}" "${RUN_ROOT}/spark-checkpoint" <<\'SCHOLARCHAIN_RENDER_PY\'',
    ]
    lines += RENDER_PY.rstrip("\n").split("\n")
    lines += ["SCHOLARCHAIN_RENDER_PY", "run_bounded %s \\" % q(cfg["step_seconds"]["spark-job"])]
    lines += spark_submit_lines(cfg, "bounded", SPARK_MAIN, ['  "${RUN_ROOT}/config/spark-config.json"'])
    return "\n".join(lines) + "\n"


def body_copy_out(cfg):
    lines = prelude("copy-out", cfg, False)
    lines += [
        "require_mount",
        "PREFIX=%s" % q(cfg["output_prefix"].rstrip("/") + "/" + cfg["run_id"]),
        "REGION=%s" % q(cfg["region"]),
        "MAX_BYTES=%s" % q(cfg["max_copyout_bytes"]),
        'TOTAL=0',
        'for part in hadoop er spark results config; do',
        '  [[ -d "${RUN_ROOT}/${part}" ]] || continue',
        '  SIZE="$(du -sk "${RUN_ROOT}/${part}" | awk \'{print $1 * 1024}\')"',
        '  TOTAL=$((TOTAL + SIZE))',
        "done",
        '[[ "${TOTAL}" -le "${MAX_BYTES}" ]] || die "copy-out ${TOTAL} bytes exceeds the ${MAX_BYTES} byte ceiling"',
        'MANIFEST="${RUN_ROOT}/copyout-manifest.sha256"',
        '[[ ! -e "${MANIFEST}" ]] || die "${MANIFEST} already exists"',
        '( cd "${RUN_ROOT}" && find hadoop er spark results config -type f -print 2>/dev/null | LC_ALL=C sort | while IFS= read -r f; do',
        "    printf '%s  %s\\n' \"$(sha256sum \"${f}\" | cut -d' ' -f1)\" \"${f}\"",
        '  done ) > "${MANIFEST}"',
        'for part in hadoop er spark results config; do',
        '  [[ -d "${RUN_ROOT}/${part}" ]] || continue',
        '  aws s3 cp "${RUN_ROOT}/${part}/" "${PREFIX}/${part}/" --recursive --region "${REGION}" --only-show-errors',
        "done",
        'aws s3 cp "${MANIFEST}" "${PREFIX}/copyout-manifest.sha256" --region "${REGION}" --only-show-errors',
        'log "copied ${TOTAL} bytes (hadoop, er, spark, results, config) to ${PREFIX}"',
    ]
    return "\n".join(lines) + "\n"


BODIES = {
    "stage-in": body_stage_in,
    "hadoop-prep": body_hadoop_prep,
    "entity-resolution": body_er,
    "spark-class-origin": body_class_origin,
    "spark-job": body_spark_job,
    "copy-out": body_copy_out,
}


def step_json(name, run_id, body):
    step = {
        "Name": ("ScholarChain-%s-%s" % (run_id, name))[:256],
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {"Jar": "command-runner.jar", "Args": ["bash", "-c", body]},
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
        body = BODIES[name](runtime_cfg)
        steps.append({"name": name, "timeout_seconds": step_seconds[name], "body": body, "add_steps_json": step_json(name, run_id, body)})
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
    exec(compile(CLASS_ORIGIN_PY, "class-origin-verifier", "exec"), {"__name__": "__main__"})
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
        "expected-scala-version", "step-weights", "runtime-archive-sha256", "estimate-json",
    ):
        p.add_argument("--" + name)
    for name in ("core-count", "max-task-count", "max-runtime-minutes", "max-capacity-cap", "max-runtime-cap", "max-input-bytes", "max-copyout-bytes", "max-idle-timeout-seconds", "max-executors-per-node", "kill-after-seconds", "min-step-seconds"):
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
