#!/usr/bin/env bash
# Bounded EMR smoke: submit one HadoopPrepMain run with --once over sample layout on S3.
# Does not create infrastructure, mutate IAM, or delete output paths.
# Dry-run prints the EMR command only. It does not invoke hadoop or aws.
# A local regular prep config is ceiling-checked before the EMR step is built.
# The cluster bash body repeats that check after copyToLocal and before hadoop jar.
set -euo pipefail

readonly MAIN_CLASS="edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
readonly STEP_NAME="ScholarChain-Phase4-HadoopPrep-smoke-once"

# Inclusive smoke ceilings. Keep usage() and scripts/README.md in sync.
readonly SMOKE_MAX_LOCAL_SAMPLE_RECORDS=1000
readonly SMOKE_MAX_REDUCER_COUNT=8
readonly SMOKE_MAX_CANDIDATE_BLOCK_SIZE=256
readonly SMOKE_MAX_CANDIDATE_PAIRS_PER_BLOCK=4096
readonly SMOKE_MAX_AUTHOR_TEAM_SIZE=64
readonly SMOKE_MAX_RECORD_BYTES=8388608
readonly SMOKE_MAX_XML_ENTITY_EXPANSION=8388608

usage() {
  cat <<'EOF'
Usage: phase4-emr-smoke.sh [OPTIONS]

Submit (or dry-run) a single EMR step that runs HadoopPrepMain with --once on sample inputs
under an S3 input prefix. Default mode is dry-run (no AWS calls, and no hadoop invocation).

The step keeps command-runner.jar and runs bash -c on the cluster master. That script localizes
the job JAR, dependency bundle, and prep config into a fresh work directory under
${TMPDIR:-/tmp} before hadoop jar:
  s3://, s3a://, s3n://, and hdfs:// sources use hadoop fs -copyToLocal
  any other path is copied with cp when it is already a regular file
Dataset inputs stay remote s3:// URIs and are not copied onto the master.

The required job JAR is hadoop-submit_*.jar (module classes plus lib/<dependency-bundle>.jar
for RunJar). Do not submit the thin JAR alone. The driver also exports HADOOP_CLASSPATH to the
localized bundle. -libjars passes that same localized bundle on the application args for tasks.
--config is the localized local file. Hadoop stays Provided on the cluster.
Cluster execution uses --execution-mode cluster; the job must not run LocalJobRunner.

maxLocalSampleRecords in the caller-supplied prep config is a launch-level bound for the whole
step (total accepted records for the run), not a per-mapper cap and not a per-split cap.

Smoke ceilings are inclusive maximums. When --config is a local regular file, the script
rejects a value above the ceiling, or a missing or non-numeric ceiling field, before it
builds the EMR step. That failure does not print an aws emr add-steps command. The cluster
bash -c body runs the same check after copyToLocal and before hadoop jar. Ceiling fields
must be JSON numbers.

  maxLocalSampleRecords      <= 1000
  reducerCount               <= 8
  maxCandidateBlockSize      <= 256
  maxCandidatePairsPerBlock  <= 4096
  maxAuthorTeamSize          <= 64
  maxRecordBytes             <= 8388608
  maxXmlEntityExpansion      <= 8388608

Required (environment variables and/or long options; no defaults):

  EMR cluster id     SCHOLARCHAIN_EMR_CLUSTER_ID  or  --cluster-id
  AWS region         SCHOLARCHAIN_AWS_REGION      or  --region
  S3 input prefix    SCHOLARCHAIN_S3_INPUT_PREFIX or  --input-prefix
                     Must contain datasets/samples/{dblp,openalex,crossref,orcid}/...
  S3 output prefix   SCHOLARCHAIN_S3_OUTPUT_PREFIX or --output-prefix
                     Form: s3://bucket/non-empty-key-prefix
  Submit JAR         SCHOLARCHAIN_HADOOP_SUBMIT_JAR or --jar
                     hadoop-submit_*.jar. Cluster-visible URI or master-local path.
                     The step localizes it before hadoop jar.
                     SCHOLARCHAIN_HADOOP_THIN_JAR is accepted only as a deprecated alias.
  Dependency bundle  SCHOLARCHAIN_HADOOP_DEPENDENCY_BUNDLE or --libjars
                     Non-Hadoop runtime JAR. Cluster-visible URI or master-local path;
                     the step localizes it before hadoop jar.
  Prep config path   SCHOLARCHAIN_HADOOP_PREP_CONFIG or --config
                     Cluster-visible URI or master-local path. The step localizes it and
                     passes the local file to --config, plus --output-root from --output-prefix.
                     A local regular file is ceiling-checked before the step is built.

Modes:
  (default)          Print exact "aws emr add-steps" command and exit 0.
  --dry-run          Same as default.
  --execute          Run "aws emr add-steps" (requires AWS CLI credentials; human gate).

Trace output always prints: cluster id, region, submitJar, dependency bundle, input paths,
output prefix, step name.
EOF
}

die() {
  echo "phase4-emr-smoke.sh: $*" >&2
  exit 1
}

# Same checker locally (stdin) and inside the cluster bash body (quoted heredoc).
# argv: config-path, then inclusive ceilings in FIELDS order.
SMOKE_CEILING_PY="$(
  cat <<'PY'
import json
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
    sys.stderr.write("phase4-emr-smoke: %s\n" % (message,))
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
    fail("smoke ceiling check expected a config path and %d ceilings" % (len(FIELDS),))

limits = []
for field, raw in zip(FIELDS, sys.argv[2:]):
    if not raw.isdigit():
        fail("smoke ceiling for %s is not an integer" % (field,))
    limits.append(int(raw))

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
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
        fail("%s %s exceeds smoke ceiling %s" % (field, number, limit))
PY
)"
readonly SMOKE_CEILING_PY

enforce_smoke_ceiling() {
  local config_file="$1"
  python3 - \
    "${config_file}" \
    "${SMOKE_MAX_LOCAL_SAMPLE_RECORDS}" \
    "${SMOKE_MAX_REDUCER_COUNT}" \
    "${SMOKE_MAX_CANDIDATE_BLOCK_SIZE}" \
    "${SMOKE_MAX_CANDIDATE_PAIRS_PER_BLOCK}" \
    "${SMOKE_MAX_AUTHOR_TEAM_SIZE}" \
    "${SMOKE_MAX_RECORD_BYTES}" \
    "${SMOKE_MAX_XML_ENTITY_EXPANSION}" \
    <<<"${SMOKE_CEILING_PY}"
}

CLUSTER_ID="${SCHOLARCHAIN_EMR_CLUSTER_ID:-}"
AWS_REGION="${SCHOLARCHAIN_AWS_REGION:-}"
INPUT_PREFIX="${SCHOLARCHAIN_S3_INPUT_PREFIX:-}"
OUTPUT_PREFIX="${SCHOLARCHAIN_S3_OUTPUT_PREFIX:-}"
SUBMIT_JAR="${SCHOLARCHAIN_HADOOP_SUBMIT_JAR:-${SCHOLARCHAIN_HADOOP_THIN_JAR:-}}"
LIB_JARS="${SCHOLARCHAIN_HADOOP_DEPENDENCY_BUNDLE:-}"
CONFIG_PATH="${SCHOLARCHAIN_HADOOP_PREP_CONFIG:-}"
EXECUTE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cluster-id)
      CLUSTER_ID="${2:-}"
      shift 2
      ;;
    --region)
      AWS_REGION="${2:-}"
      shift 2
      ;;
    --input-prefix)
      INPUT_PREFIX="${2:-}"
      shift 2
      ;;
    --output-prefix)
      OUTPUT_PREFIX="${2:-}"
      shift 2
      ;;
    --jar)
      SUBMIT_JAR="${2:-}"
      shift 2
      ;;
    --libjars)
      LIB_JARS="${2:-}"
      shift 2
      ;;
    --config)
      CONFIG_PATH="${2:-}"
      shift 2
      ;;
    --dry-run)
      EXECUTE=0
      shift
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1 (see --help)"
      ;;
  esac
done

require_non_empty() {
  local name="$1"
  local value="$2"
  if [[ -z "${value}" ]]; then
    die "missing required value: ${name}"
  fi
}

require_non_empty "EMR cluster id (SCHOLARCHAIN_EMR_CLUSTER_ID or --cluster-id)" "${CLUSTER_ID}"
require_non_empty "AWS region (SCHOLARCHAIN_AWS_REGION or --region)" "${AWS_REGION}"
require_non_empty "S3 input prefix (SCHOLARCHAIN_S3_INPUT_PREFIX or --input-prefix)" "${INPUT_PREFIX}"
require_non_empty "S3 output prefix (SCHOLARCHAIN_S3_OUTPUT_PREFIX or --output-prefix)" "${OUTPUT_PREFIX}"
require_non_empty "submit JAR path (SCHOLARCHAIN_HADOOP_SUBMIT_JAR or --jar; hadoop-submit_*.jar)" "${SUBMIT_JAR}"
require_non_empty "Hadoop dependency bundle (SCHOLARCHAIN_HADOOP_DEPENDENCY_BUNDLE or --libjars)" "${LIB_JARS}"
require_non_empty "Hadoop prep config path (SCHOLARCHAIN_HADOOP_PREP_CONFIG or --config)" "${CONFIG_PATH}"

validate_s3_uri_with_prefix() {
  local label="$1"
  local uri="$2"
  if [[ "${uri}" != s3://* ]]; then
    die "${label} must be an s3:// URI (got: ${uri})"
  fi
  local rest="${uri#s3://}"
  local bucket="${rest%%/*}"
  local key=""
  if [[ "${rest}" == */* ]]; then
    key="${rest#*/}"
  fi
  if [[ -z "${bucket}" ]]; then
    die "${label} must include a bucket name (got: ${uri})"
  fi
  if [[ -z "${key}" ]]; then
    die "${label} must include a non-empty key prefix after the bucket (got: ${uri})"
  fi
}

validate_s3_uri_with_prefix "S3 output prefix" "${OUTPUT_PREFIX}"

if [[ "${INPUT_PREFIX}" != s3://* ]]; then
  die "S3 input prefix must be an s3:// URI (got: ${INPUT_PREFIX})"
fi

input_base="${INPUT_PREFIX%/}"
DBLP_URI="${input_base}/datasets/samples/dblp/linked-records.xml"
OPENALEX_URI="${input_base}/datasets/samples/openalex/works.jsonl"
CROSSREF_URI="${input_base}/datasets/samples/crossref/works.jsonl"
ORCID_URI="${input_base}/datasets/samples/orcid/records.jsonl"

if ! command -v python3 >/dev/null 2>&1; then
  die "python3 is required to validate the smoke ceiling and build EMR --steps JSON"
fi

# A local regular file is rejected before the step JSON or aws command is built.
if [[ -f "${CONFIG_PATH}" ]]; then
  enforce_smoke_ceiling "${CONFIG_PATH}" || die "smoke ceiling rejected local config: ${CONFIG_PATH}"
fi

CONFIG_OUTPUT_ROOT=""
if [[ "${CONFIG_PATH}" != s3://* && "${CONFIG_PATH}" != hdfs://* ]]; then
  if [[ -f "${CONFIG_PATH}" ]]; then
    CONFIG_OUTPUT_ROOT="$(
      python3 - "${CONFIG_PATH}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
value = data.get("outputRoot")
if value is None:
    sys.exit(0)
if not isinstance(value, str):
    sys.exit(0)
print(value)
PY
    )"
  fi
fi

build_steps_json() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$@" <<'PY'
import json
import shlex
import sys

(
    step_name,
    submit_jar,
    main_class,
    lib_jars,
    config_path,
    output_root,
    dblp,
    openalex,
    crossref,
    orcid,
    max_local_sample_records,
    max_reducer_count,
    max_candidate_block_size,
    max_candidate_pairs_per_block,
    max_author_team_size,
    max_record_bytes,
    max_xml_entity_expansion,
    ceiling_py,
) = sys.argv[1:]


def q(value: str) -> str:
    return shlex.quote(value)


def shell_ceiling(value: str) -> str:
    if not value.isdigit():
        raise SystemExit(f"internal smoke ceiling is not an integer: {value}")
    return value


ceiling_numbers = [
    shell_ceiling(max_local_sample_records),
    shell_ceiling(max_reducer_count),
    shell_ceiling(max_candidate_block_size),
    shell_ceiling(max_candidate_pairs_per_block),
    shell_ceiling(max_author_team_size),
    shell_ceiling(max_record_bytes),
    shell_ceiling(max_xml_entity_expansion),
]
ceiling_lines = ceiling_py.splitlines()
if not ceiling_lines:
    raise SystemExit("smoke ceiling checker is empty")
for field in (
    "maxLocalSampleRecords",
    "reducerCount",
    "maxCandidateBlockSize",
    "maxCandidatePairsPerBlock",
    "maxAuthorTeamSize",
    "maxRecordBytes",
    "maxXmlEntityExpansion",
):
    if field not in ceiling_py:
        raise SystemExit(f"smoke ceiling checker is missing {field}")

# This body runs on the cluster master. Dry-run only embeds it; it does not execute it.
# The ceiling check is the same Python program used for a local regular config.
bash_lines = [
    "set -euo pipefail",
    'work="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-phase4.XXXXXX")"',
    "localize() {",
    '  local src="$1"',
    '  local dest="$2"',
    '  case "${src}" in',
    "    s3://*|s3a://*|s3n://*|hdfs://*)",
    '      hadoop fs -copyToLocal "${src}" "${dest}"',
    "      ;;",
    "    *)",
    '      if [[ -f "${src}" ]]; then',
    '        cp -- "${src}" "${dest}"',
    "      else",
    '        echo "phase4-emr-smoke: source is not a regular file: ${src}" >&2',
    "        exit 1",
    "      fi",
    "      ;;",
    "  esac",
    "}",
    f"src_jar={q(submit_jar)}",
    f"src_bundle={q(lib_jars)}",
    f"src_config={q(config_path)}",
    'local_jar="${work}/job.jar"',
    'local_bundle="${work}/bundle.jar"',
    'local_config="${work}/prep-config.json"',
    'localize "${src_jar}" "${local_jar}"',
    'localize "${src_bundle}" "${local_bundle}"',
    'localize "${src_config}" "${local_config}"',
    'command -v python3 >/dev/null 2>&1 || { echo "phase4-emr-smoke: python3 is required to enforce the smoke ceiling" >&2; exit 1; }',
    "python3 - \"${local_config}\" "
    + " ".join(ceiling_numbers)
    + " <<'SCHOLARCHAIN_SMOKE_CEILING_PY'",
]
bash_lines.extend(ceiling_lines)
bash_lines.extend(
    [
    "SCHOLARCHAIN_SMOKE_CEILING_PY",
    'export HADOOP_CLASSPATH="${local_bundle}${HADOOP_CLASSPATH:+:$HADOOP_CLASSPATH}"',
    " ".join(
        [
            "exec",
            "hadoop",
            "jar",
            '"${local_jar}"',
            q(main_class),
            "-libjars",
            '"${local_bundle}"',
            "--once",
            "--execution-mode",
            "cluster",
            "--output-root",
            q(output_root),
            "--config",
            '"${local_config}"',
            "--dblp",
            q(dblp),
            "--dblp-snapshot",
            "dblp-2026-10-03",
            "--dblp-retrieval",
            "2026-10-05",
            "--openalex",
            q(openalex),
            "--openalex-snapshot",
            "openalex-rest-2026-10-05",
            "--openalex-retrieval",
            "2026-10-05",
            "--crossref",
            q(crossref),
            "--crossref-snapshot",
            "crossref-rest-2026-10-05",
            "--crossref-retrieval",
            "2026-10-05",
            "--orcid",
            q(orcid),
            "--orcid-snapshot",
            "orcid-public-api-2026-10-05",
            "--orcid-retrieval",
            "2026-10-05",
        ]
    ),
    ]
)
bash_body = "\n".join(bash_lines) + "\n"
copy_at = bash_body.find("copyToLocal")
reducer_at = bash_body.find('"reducerCount"')
jar_at = bash_body.find("hadoop jar")
if copy_at < 0 or reducer_at < 0 or jar_at < 0 or not (copy_at < reducer_at < jar_at):
    raise SystemExit("smoke ceiling check must follow copyToLocal and precede hadoop jar")
expected_invoke = 'python3 - "${local_config}" ' + " ".join(ceiling_numbers)
if expected_invoke not in bash_body:
    raise SystemExit("smoke ceiling invocation was not embedded")

step = {
    "Name": step_name,
    "ActionOnFailure": "CONTINUE",
    "HadoopJarStep": {
        "Jar": "command-runner.jar",
        "Args": ["bash", "-c", bash_body],
    },
}
print(json.dumps([step], separators=(",", ":")))
PY
  else
    die "python3 is required to build EMR --steps JSON safely"
  fi
}

STEPS_JSON="$(
  build_steps_json \
    "${STEP_NAME}" \
    "${SUBMIT_JAR}" \
    "${MAIN_CLASS}" \
    "${LIB_JARS}" \
    "${CONFIG_PATH}" \
    "${OUTPUT_PREFIX}" \
    "${DBLP_URI}" \
    "${OPENALEX_URI}" \
    "${CROSSREF_URI}" \
    "${ORCID_URI}" \
    "${SMOKE_MAX_LOCAL_SAMPLE_RECORDS}" \
    "${SMOKE_MAX_REDUCER_COUNT}" \
    "${SMOKE_MAX_CANDIDATE_BLOCK_SIZE}" \
    "${SMOKE_MAX_CANDIDATE_PAIRS_PER_BLOCK}" \
    "${SMOKE_MAX_AUTHOR_TEAM_SIZE}" \
    "${SMOKE_MAX_RECORD_BYTES}" \
    "${SMOKE_MAX_XML_ENTITY_EXPANSION}" \
    "${SMOKE_CEILING_PY}"
)"

echo "=== ScholarChain Phase 4 EMR smoke (trace) ==="
echo "stepName=${STEP_NAME}"
echo "clusterId=${CLUSTER_ID}"
echo "region=${AWS_REGION}"
echo "submitJar=${SUBMIT_JAR}"
echo "dependencyBundle=${LIB_JARS}"
echo "configPath=${CONFIG_PATH}"
echo "driverBootstrap=HADOOP_CLASSPATH"
echo "taskClasspath=libjars"
echo "configScope=local-file"
echo "localization=step localizes submitJar, dependencyBundle, and configPath on the cluster master before hadoop jar"
echo "inputPrefix=${INPUT_PREFIX}"
echo "sampleDblp=${DBLP_URI}"
echo "sampleOpenalex=${OPENALEX_URI}"
echo "sampleCrossref=${CROSSREF_URI}"
echo "sampleOrcid=${ORCID_URI}"
echo "outputPrefix=${OUTPUT_PREFIX}"
echo "stepOutputRoot=${OUTPUT_PREFIX}"
echo "executionMode=cluster"
echo "smokeCeiling=maxLocalSampleRecords<=${SMOKE_MAX_LOCAL_SAMPLE_RECORDS} reducerCount<=${SMOKE_MAX_REDUCER_COUNT} maxCandidateBlockSize<=${SMOKE_MAX_CANDIDATE_BLOCK_SIZE} maxCandidatePairsPerBlock<=${SMOKE_MAX_CANDIDATE_PAIRS_PER_BLOCK} maxAuthorTeamSize<=${SMOKE_MAX_AUTHOR_TEAM_SIZE} maxRecordBytes<=${SMOKE_MAX_RECORD_BYTES} maxXmlEntityExpansion<=${SMOKE_MAX_XML_ENTITY_EXPANSION}"
if [[ -n "${CONFIG_OUTPUT_ROOT}" ]]; then
  echo "configOutputRoot=${CONFIG_OUTPUT_ROOT}"
  if [[ "${CONFIG_OUTPUT_ROOT}" != "${OUTPUT_PREFIX}" ]]; then
    echo "outputRootNote=config outputRoot differs; step passes --output-root to override"
  fi
fi
echo "mode=$([[ ${EXECUTE} -eq 1 ]] && echo execute || echo dry-run)"
echo "=============================================="

# shellcheck disable=SC2086
AWS_CMD=(aws emr add-steps --region "${AWS_REGION}" --cluster-id "${CLUSTER_ID}" --steps "${STEPS_JSON}")

printf 'Exact command (replay):\n'
printf ' %q' "${AWS_CMD[@]}"
printf '\n'

if [[ "${EXECUTE}" -eq 0 ]]; then
  echo "Dry-run complete; no EMR step submitted. hadoop and aws were not invoked."
  exit 0
fi

echo "Executing aws emr add-steps (human gate required)."
"${AWS_CMD[@]}"
