#!/usr/bin/env bash
# ScholarChain Phase 13C repair 1 (finding C1) - the installed EMR step runner.
#
# Why this file exists: EMR accepts at most 10,280 characters per string in a step's HadoopJarStepConfig.Args. The 13C
# wrapper plus the six step bodies, embedded in ONE `bash -c <body>` argument, were about 11.8 KB (spark-job) and 10.2 KB
# (class-origin). The static program text now lives HERE and in three small Python programs, installed on the primary node by
# the bootstrap action as sha256-pinned --artifact files in the pinned directory PIPELINE_STEP_BIN_DIR
# (/opt/scholarchain-spike/bin); each EMR step passes only a short launcher plus per-run KEY=VALUE parameters.
#
#   EMR step Args:  bash -c <launcher> sc-step <sha256-of-this-file> <STEP> KEY=VALUE...
#   launcher     :  verify this file against the sha256 the pipeline computed from the repository file (fail closed), then
#                   exec bash THIS_FILE <STEP> KEY=VALUE...
#   wrapper mode :  sc-step.sh STEP KEY=VALUE...       (below: run_wrapper)  finding B1, unchanged in behaviour
#   body mode    :  sc-step.sh __body STEP KEY=VALUE...                       run by the wrapper under `timeout --kill-after`
#
# B1 (kept): the WHOLE step body, every localize copy included, runs under `timeout --kill-after=KILL_AFTER STEP_SECONDS`
# as a job-control process group; on timeout, failure or cancel (TERM/INT) the wrapper sends TERM to the whole group, waits
# up to the grace, then KILLs what is left (STEP-WARN). Item 1 (kept): the YARN-submitting bodies tag the application with the
# run id and kill every application carrying that tag when the cap fires or on TERM/INT/EXIT.
#
# Parameters are plain KEY=VALUE words. Each key must be on the allow-list of the step, may be given once (SPARK_CONF is
# repeated on purpose), and is NEVER evaluated: a value is only ever expanded inside double quotes. The three Python programs
# (ceiling check, class-origin verifier, spark-config renderer) are run only after their sha256 matches a *_PY_SHA parameter.
#
# Portable bash (3.2 and later: no associative arrays), because the offline tests run it on a laptop with fake binaries.
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SELF="${SELF_DIR}/$(basename "${BASH_SOURCE[0]}")"
CEILING_PY="${SELF_DIR}/sc-ceiling-check.py"
CLASS_ORIGIN_PY="${SELF_DIR}/sc-class-origin-verify.py"
RENDER_PY="${SELF_DIR}/sc-render-spark-config.py"

# Main classes and sample layout: fixed program text, part of the sha256-pinned file (not run parameters).
HADOOP_MAIN="edu.uic.cs441.scholarchain.hadoop.HadoopPrepMain"
ER_MAIN="edu.uic.cs441.scholarchain.entityresolution.Phase5Main"
SPARK_MAIN="edu.uic.cs441.scholarchain.spark.Phase6Main"
PROBE_MAIN="edu.uic.cs441.scholarchain.spark.Phase12Readiness"
SAMPLE_DBLP="datasets/samples/dblp/linked-records.xml"
SAMPLE_OPENALEX="datasets/samples/openalex/works.jsonl"
SAMPLE_CROSSREF="datasets/samples/crossref/works.jsonl"
SAMPLE_ORCID="datasets/samples/orcid/records.jsonl"

STEP_NAME="sc-step"
die() {
  printf 'STEP-FAIL %s: %s\n' "${STEP_NAME}" "$*" >&2
  exit 1
}
log() { printf 'STEP-LOG %s: %s\n' "${STEP_NAME}" "$*"; }

# ---- arguments -------------------------------------------------------------------------------------------------
MODE="wrap"
if [[ "${1:-}" == "__body" ]]; then
  MODE="body"
  shift
fi
[[ $# -ge 1 ]] || die "usage: sc-step.sh [__body] STEP KEY=VALUE..."
STEP_NAME="$1"
shift
PARAMS=("$@")

COMMON_KEYS="STEP_SECONDS KILL_AFTER RUN_ID TAG MNT"
case "${STEP_NAME}" in
  stage-in) STEP_KEYS="INPUT_PREFIX REGION MAX_INPUT_BYTES" ;;
  hadoop-prep) STEP_KEYS="SUBMIT_JAR_REF SUBMIT_JAR_SHA LIBJARS_REF LIBJARS_SHA CONFIG_REF CONFIG_SHA CEILINGS CEILING_PY_SHA DBLP_SNAPSHOT DBLP_RETRIEVAL OPENALEX_SNAPSHOT OPENALEX_RETRIEVAL CROSSREF_SNAPSHOT CROSSREF_RETRIEVAL ORCID_SNAPSHOT ORCID_RETRIEVAL" ;;
  entity-resolution) STEP_KEYS="JAVA_HOME_FILE ER_XMX ER_JAR_REF ER_JAR_SHA ER_POLICY_REF ER_POLICY_SHA ER_CONFIG_REF ER_CONFIG_SHA" ;;
  spark-class-origin) STEP_KEYS="JAVA_HOME_FILE RUNTIME_DIR JOB_JAR JOB_JAR_SHA MAX_EXECUTORS EXPECTED_SPARK_VERSION EXPECTED_SCALA_VERSION CLASS_ORIGIN_PY_SHA SPARK_CONF" ;;
  spark-job) STEP_KEYS="JAVA_HOME_FILE RUNTIME_DIR JOB_JAR JOB_JAR_SHA MAX_EXECUTORS EXPECTED_SPARK_VERSION EXPECTED_SCALA_VERSION CLASS_ORIGIN_PY_SHA RENDER_PY_SHA TEMPLATE_REF TEMPLATE_SHA SPARK_CONF" ;;
  copy-out) STEP_KEYS="OUTPUT_PREFIX REGION MAX_COPYOUT_BYTES" ;;
  *) die "unknown step name (expected stage-in, hadoop-prep, entity-resolution, spark-class-origin, spark-job or copy-out)" ;;
esac

SPARK_CONFS=()
parse_params() {
  local kv key value allowed
  allowed=" ${COMMON_KEYS} ${STEP_KEYS} "
  # An inherited environment variable of the same name must never stand in for a missing or duplicated parameter.
  for key in ${COMMON_KEYS} ${STEP_KEYS}; do
    unset "${key}"
  done
  for kv in "$@"; do
    case "${kv}" in
      [A-Z]*=*) ;;
      *) die "a parameter is not KEY=VALUE with an upper-case key" ;;
    esac
    key="${kv%%=*}"
    value="${kv#*=}"
    [[ "${key}" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "parameter name ${key} has unsafe characters"
    case "${allowed}" in *" ${key} "*) ;; *) die "parameter ${key} is not accepted by this step" ;; esac
    if [[ "${key}" == "SPARK_CONF" ]]; then
      SPARK_CONFS+=("${value}")
      continue
    fi
    [[ -z "${!key+x}" ]] || die "parameter ${key} was given twice"
    printf -v "${key}" '%s' "${value}"
  done
  for key in ${COMMON_KEYS} ${STEP_KEYS}; do
    if [[ "${key}" == "SPARK_CONF" ]]; then
      [[ ${#SPARK_CONFS[@]} -ge 1 ]] || die "no SPARK_CONF parameter: the decision 12-10 Spark settings are required"
      continue
    fi
    [[ -n "${!key:-}" ]] || die "missing parameter ${key}"
  done
}
parse_params ${PARAMS[@]+"${PARAMS[@]}"}

is_uint() { [[ "$1" =~ ^[0-9]+$ ]]; }
if ! is_uint "${STEP_SECONDS}" || ! is_uint "${KILL_AFTER}"; then
  die "STEP_SECONDS and KILL_AFTER must be whole numbers"
fi
RUN_ROOT="${MNT}/runs/${RUN_ID}"

# ---- wrapper mode (finding B1) ----------------------------------------------------------------------------------
run_wrapper() {
  local rc=0 waited=0
  TERMED=0
  # job control makes the background job its own process group (leader pid = group id), which is signalled as a whole
  set -m
  timeout --kill-after="${KILL_AFTER}" "${STEP_SECONDS}" bash "${SELF}" __body "${STEP_NAME}" ${PARAMS[@]+"${PARAMS[@]}"} &
  CHILD=$!
  set +m
  GROUP="${CHILD}"
  kill_group() { kill "-$1" -- "-${GROUP}" 2>/dev/null || kill "-$1" "${CHILD}" 2>/dev/null || true; }
  # an EMR cancel (SEND_INTERRUPT) reaches this wrapper only: forward it to the whole timed group
  trap 'TERMED=1; kill_group TERM' TERM INT
  while true; do
    wait "${CHILD}" && rc=0 || rc=$?
    kill -0 "${CHILD}" 2>/dev/null || break
  done
  if [[ "${rc}" -ne 0 || "${TERMED}" -eq 1 ]]; then
    kill_group TERM
    while kill -0 -- "-${GROUP}" 2>/dev/null && [[ "${waited}" -lt "${KILL_AFTER}" ]]; do
      sleep 1
      waited=$((waited + 1))
    done
  fi
  if kill -0 -- "-${GROUP}" 2>/dev/null; then
    printf 'STEP-WARN %s: processes of the step process group %s were still running after the step; killed with SIGKILL\n' "${STEP_NAME}" "${GROUP}" >&2
    kill_group KILL
  fi
  if [[ "${rc}" -eq 124 || "${rc}" -eq 137 ]]; then
    printf 'STEP-FAIL %s: exceeded the %ss step timeout (exit %s)\n' "${STEP_NAME}" "${STEP_SECONDS}" "${rc}" >&2
  fi
  exit "${rc}"
}

if [[ "${MODE}" == "wrap" ]]; then
  run_wrapper
fi

# ---- body mode: shared helpers -----------------------------------------------------------------------------------
require_mount() { grep -q " ${MNT} " "${SC_PROC_MOUNTS:-/proc/mounts}" || die "${MNT} is not a mount point: refusing to use a local directory"; }

localize() { # src dest expected-sha256
  local src="$1" dest="$2" want="$3"
  case "${src}" in
    s3://* | s3a://* | s3n://* | hdfs://*) hadoop fs -copyToLocal "${src}" "${dest}" ;;
    *) if [[ -f "${src}" ]]; then cp -- "${src}" "${dest}"; else die "source is not a regular file: ${src}"; fi ;;
  esac
  printf '%s  %s\n' "${want}" "${dest}" | sha256sum -c --status - || die "sha256 mismatch for ${src}"
}

verify_program() { # installed Python program, expected sha256 (computed by the pipeline from the repository file)
  [[ -f "$1" ]] || die "the installed step program ${1##*/} is missing"
  printf '%s  %s\n' "$2" "$1" | sha256sum -c --status - || die "sha256 mismatch for the installed step program ${1##*/}"
}

# Item 1: timeout kills only the client, not the YARN application. List the applications that carry the run id as their tag
# and kill each one; run on EXIT, on TERM/INT and when run_bounded sees the cap fire.
kill_tagged() {
  local apps app
  apps="$(yarn application -list -appStates NEW,NEW_SAVING,SUBMITTED,ACCEPTED,RUNNING -appTags "${TAG}" 2>/dev/null | awk '/^application_/{print $1}' || true)"
  for app in ${apps}; do
    log "killing YARN application ${app} (tag ${TAG})"
    yarn application -kill "${app}" || true
  done
}
yarn_traps() {
  trap 'kill_tagged' EXIT
  trap 'kill_tagged; exit 143' TERM INT
}
run_bounded() { # seconds command...
  local secs="$1" rc=0
  shift
  timeout --kill-after="${KILL_AFTER}" "${secs}" "$@" || rc=$?
  if [[ "${rc}" -eq 124 || "${rc}" -eq 137 || "${rc}" -eq 143 ]]; then
    log "runtime cap reached (exit ${rc}): killing the YARN application tagged ${TAG}"
    kill_tagged
  fi
  return "${rc}"
}

resolve_java() {
  [[ -r "${JAVA_HOME_FILE}" ]] || die "no resolved Java 17 home (${JAVA_HOME_FILE} missing): the bootstrap did not complete"
  JAVA_HOME="$(head -n 1 "${JAVA_HOME_FILE}")"
  [[ -n "${JAVA_HOME}" && -x "${JAVA_HOME}/bin/java" ]] || die "the resolved Java home is not usable"
  "${JAVA_HOME}/bin/java" -version 2>&1 | grep -Eq 'version "17(\.|")' || die "the resolved Java is not 17"
  export JAVA_HOME
}

discover_run() { # sub-directory of the run root: the one completed run below it
  local markers
  markers="$(find "${RUN_ROOT}/$1" -maxdepth 4 -name _SCHOLARCHAIN_COMPLETE -print)"
  [[ "$(printf '%s\n' "${markers}" | grep -c .)" -eq 1 ]] || die "expected exactly one completed run under ${RUN_ROOT}/$1"
  dirname "${markers}"
}

spark_env() {
  require_mount
  resolve_java
  # The portable runtime only: never the stock EMR Spark or Hadoop classpath.
  export SPARK_HOME="${RUNTIME_DIR}" SPARK_CONF_DIR="${RUNTIME_DIR}/conf" SPARK_SCALA_VERSION=2.13
  export HADOOP_CONF_DIR="${HADOOP_CONF_DIR:-/etc/hadoop/conf}"
  export YARN_CONF_DIR="${HADOOP_CONF_DIR}"
  export PATH="${JAVA_HOME}/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"
  unset CLASSPATH SPARK_DIST_CLASSPATH HADOOP_CLASSPATH SPARK_CLASSPATH || true
  printf '%s  %s\n' "${JOB_JAR_SHA}" "${JOB_JAR}" | sha256sum -c --status - || die "the packaged job jar on this node does not have the approved sha256"
}

build_spark_cmd() { # main-class then the application arguments; sets the SPARK_CMD array
  local main="$1" kv
  shift
  SPARK_CMD=("${SPARK_HOME}/bin/spark-submit" --master yarn --deploy-mode cluster --name "scholarchain-${SPARK_STEP}-${RUN_ID}"
    --class "${main}"
    --conf "spark.yarn.tags=${TAG}"
    --conf "spark.yarn.stagingDir=file://${MNT}/staging"
    --conf "spark.yarn.appMasterEnv.JAVA_HOME=${JAVA_HOME}"
    --conf "spark.executorEnv.JAVA_HOME=${JAVA_HOME}"
    --conf "spark.dynamicAllocation.maxExecutors=${MAX_EXECUTORS}")
  for kv in "${SPARK_CONFS[@]}"; do
    SPARK_CMD+=(--conf "${kv}")
  done
  SPARK_CMD+=("local:${JOB_JAR}" "$@")
}

verify_class_origin() {
  verify_program "${CLASS_ORIGIN_PY}" "${CLASS_ORIGIN_PY_SHA}"
  python3 "${CLASS_ORIGIN_PY}" "${RUN_ROOT}/results/class-origin.json" "${EXPECTED_SPARK_VERSION}" "${EXPECTED_SCALA_VERSION}" "${RUNTIME_DIR%/}/jars" "${JOB_JAR}" "${JOB_JAR_SHA}"
}

# ---- the six step bodies ------------------------------------------------------------------------------------------
body_stage_in() {
  require_mount
  local dest="${RUN_ROOT}/inputs" total
  [[ ! -e "${RUN_ROOT}" ]] || die "${RUN_ROOT} already exists: a run directory is never reused"
  total="$(aws s3 ls "${INPUT_PREFIX}" --recursive --summarize --region "${REGION}" | awk '/Total Size:/{print $3}')"
  [[ "${total}" =~ ^[0-9]+$ ]] || die "could not read the staged input size"
  [[ "${total}" -le "${MAX_INPUT_BYTES}" ]] || die "input ${total} bytes exceeds the ${MAX_INPUT_BYTES} byte ceiling"
  mkdir -p "${dest}"
  aws s3 cp "${INPUT_PREFIX}" "${dest}/" --recursive --region "${REGION}" --only-show-errors
  log "staged ${total} bytes from ${INPUT_PREFIX} to ${dest}"
}

# Phase 15 P6 defect D1: HadoopPrepPipeline accepts only `run:<uuid version 4>` (StableIds runPattern), while the pipeline run id may not
# contain ':'. The Hadoop run id is therefore derived DETERMINISTICALLY from RUN_ID: the first 32 hex digits of sha256(RUN_ID) with the
# version nibble set to 4 and the variant nibble to 8, 9, a or b (the same construction as StableIds' deterministic Spark run id). The
# directory under hadoop/ is found later by its completion marker (discover_run), so nothing downstream needs the two ids to be equal.
hadoop_run_id() { # pipeline run id -> run:<uuid v4 form>
  local f h variant
  # hashed from a file (sha256sum FILE), the form every sha256sum and the offline test shims support
  f="$(mktemp "${TMPDIR:-/tmp}/scholarchain-run-id.XXXXXX")"
  printf '%s' "$1" >"${f}"
  h="$(sha256sum "${f}" | cut -c1-32)"
  rm -f "${f}"
  [[ "${h}" =~ ^[0-9a-f]{32}$ ]] || die "could not derive the Hadoop run id"
  variant="$(printf '%x' $(((16#${h:16:1} & 3) | 8)))"
  printf 'run:%s-%s-4%s-%s%s-%s\n' "${h:0:8}" "${h:8:4}" "${h:13:3}" "${variant}" "${h:17:3}" "${h:20:12}"
}

body_hadoop_prep() {
  yarn_traps
  require_mount
  local work in_dir out_dir ceil hadoop_id
  work="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"
  localize "${SUBMIT_JAR_REF}" "${work}/job.jar" "${SUBMIT_JAR_SHA}"
  localize "${LIBJARS_REF}" "${work}/bundle.jar" "${LIBJARS_SHA}"
  localize "${CONFIG_REF}" "${work}/prep-config.json" "${CONFIG_SHA}"
  command -v python3 >/dev/null 2>&1 || die "python3 is required to enforce the ceilings"
  verify_program "${CEILING_PY}" "${CEILING_PY_SHA}"
  read -r -a ceil <<<"${CEILINGS}"
  [[ ${#ceil[@]} -eq 7 ]] || die "CEILINGS must hold exactly seven integers"
  python3 "${CEILING_PY}" "${work}/prep-config.json" "${ceil[@]}"
  export HADOOP_CLASSPATH="${work}/bundle.jar${HADOOP_CLASSPATH:+:$HADOOP_CLASSPATH}"
  in_dir="${RUN_ROOT}/inputs"
  out_dir="${RUN_ROOT}/hadoop"
  [[ ! -e "${out_dir}" ]] || die "${out_dir} already exists"
  hadoop_id="$(hadoop_run_id "${RUN_ID}")"
  log "Hadoop run id ${hadoop_id} (derived from pipeline run id ${RUN_ID})"
  # Phase 15 P6 defect D2: --output-root is a plain absolute path. FsPaths.runPath treats every non-remote root as a local path, so a
  # file:// URI would become a relative path named "file:" under the step's working directory.
  run_bounded "${STEP_SECONDS}" hadoop jar "${work}/job.jar" "${HADOOP_MAIN}" \
    "-Dmapreduce.job.tags=${TAG}" -libjars "${work}/bundle.jar" \
    --once --execution-mode cluster --run-id "${hadoop_id}" \
    --output-root "${out_dir}" --config "${work}/prep-config.json" \
    --dblp "file://${in_dir}/${SAMPLE_DBLP}" --dblp-snapshot "${DBLP_SNAPSHOT}" --dblp-retrieval "${DBLP_RETRIEVAL}" \
    --openalex "file://${in_dir}/${SAMPLE_OPENALEX}" --openalex-snapshot "${OPENALEX_SNAPSHOT}" --openalex-retrieval "${OPENALEX_RETRIEVAL}" \
    --crossref "file://${in_dir}/${SAMPLE_CROSSREF}" --crossref-snapshot "${CROSSREF_SNAPSHOT}" --crossref-retrieval "${CROSSREF_RETRIEVAL}" \
    --orcid "file://${in_dir}/${SAMPLE_ORCID}" --orcid-snapshot "${ORCID_SNAPSHOT}" --orcid-retrieval "${ORCID_RETRIEVAL}"
}

body_entity_resolution() {
  require_mount
  resolve_java
  local work hadoop_run er_out
  work="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"
  localize "${ER_JAR_REF}" "${work}/er.jar" "${ER_JAR_SHA}"
  localize "${ER_POLICY_REF}" "${work}/policy.json" "${ER_POLICY_SHA}"
  localize "${ER_CONFIG_REF}" "${work}/config.json" "${ER_CONFIG_SHA}"
  hadoop_run="$(discover_run hadoop)"
  er_out="${RUN_ROOT}/er/run"
  [[ ! -e "${er_out}" ]] || die "${er_out} already exists"
  mkdir -p "${RUN_ROOT}/er"
  # Single-JVM step on the primary node (Phase5Main has no distributed mode); Java 17 was resolved at bootstrap.
  timeout --kill-after="${KILL_AFTER}" "${STEP_SECONDS}" "${JAVA_HOME}/bin/java" -Xmx"${ER_XMX}" -cp "${work}/er.jar" "${ER_MAIN}" resolve \
    --input "${hadoop_run}" --policy "${work}/policy.json" --config "${work}/config.json" \
    --llm-mode disabled --output "${er_out}"
}

body_spark_class_origin() {
  yarn_traps
  spark_env
  SPARK_STEP="class-origin"
  local probe_shared="${RUN_ROOT}/probe" probe_out="${RUN_ROOT}/results/class-origin.json"
  mkdir -p "${probe_shared}" "${RUN_ROOT}/results" "${MNT}/staging"
  # Driver AND executor class-origin probe (Phase12Readiness distributed): fails closed on any version difference.
  build_spark_cmd "${PROBE_MAIN}" probe "${probe_shared}" "${probe_out}" distributed
  run_bounded "${STEP_SECONDS}" "${SPARK_CMD[@]}"
  verify_class_origin
}

body_spark_job() {
  yarn_traps
  spark_env
  SPARK_STEP="bounded"
  local work hadoop_run er_run spark_out
  # Fail closed again here: the Spark job never starts without a passing class-origin result for this run.
  [[ -f "${RUN_ROOT}/results/class-origin.json" ]] || die "no class-origin result for this run: refusing to start the Spark job"
  verify_class_origin
  hadoop_run="$(discover_run hadoop)"
  er_run="${RUN_ROOT}/er/run"
  [[ -d "${er_run}" ]] || die "no entity-resolution output at ${er_run}"
  spark_out="${RUN_ROOT}/spark"
  [[ ! -e "${spark_out}" ]] || die "${spark_out} already exists"
  mkdir -p "${spark_out}" "${RUN_ROOT}/spark-checkpoint" "${RUN_ROOT}/config" "${MNT}/staging"
  work="$(mktemp -d "${TMPDIR:-/tmp}/scholarchain-bounded.XXXXXX")"
  localize "${TEMPLATE_REF}" "${work}/spark-template.json" "${TEMPLATE_SHA}"
  verify_program "${RENDER_PY}" "${RENDER_PY_SHA}"
  python3 "${RENDER_PY}" "${work}/spark-template.json" "${RUN_ROOT}/config/spark-config.json" "${hadoop_run}" "${er_run}" "${spark_out}" "${RUN_ROOT}/spark-checkpoint"
  build_spark_cmd "${SPARK_MAIN}" "${RUN_ROOT}/config/spark-config.json"
  run_bounded "${STEP_SECONDS}" "${SPARK_CMD[@]}"
}

# Phase 15 P23: copy out only what the report and the loaders need. Per part, an ordered filter table in the `aws s3 cp` filter
# language (relative to the part directory; `*` also matches `/`; every file is included unless a filter matches; the LAST matching
# filter wins). The SAME table drives both the size, manifest selection below (copyout_keep, bash glob matching with identical
# semantics) and the --exclude/--include arguments of the upload, so what is sized, hashed and copied is one set.
#   hadoop : counters, run manifest, completion marker and stats; rejects (export/.../reject/); NOT intermediate/ and NOT the
#            record export (Spark already consumed it; about 0.46 GB of the 1.0 GB local output at 10,577 works was export,
#            0.61 GB intermediate)
#   er     : the small top-level files of the ER run (manifest, diagnostics, effective config and policy, marker); NOT the work/ and
#            researcher/ trees and NOT evidence.jsonl or audit-details.jsonl (about 0.66 GB of the 0.76 GB local output)
#   spark, results, config : everything (the Spark export the loaders read, with load-manifests/, the neptune-opencypher-csv/ sidecar
#            and the event logs under .event-logs/)
copyout_rules() { # part -> COPYOUT_RULES: action pattern action pattern ...
  COPYOUT_RULES=()
  case "$1" in
    hadoop) COPYOUT_RULES=(exclude 'intermediate/*' exclude '*/intermediate/*' exclude 'export/*' exclude '*/export/*'
      include 'export/*/reject/*' include '*/export/*/reject/*') ;;
    er) COPYOUT_RULES=(exclude '*/*/*' exclude 'evidence.jsonl' exclude '*/evidence.jsonl' exclude 'audit-details.jsonl'
      exclude '*/audit-details.jsonl') ;;
  esac
}

copyout_keep() { # relative-path (uses COPYOUT_RULES) -> 0 when the file is copied out
  local i=0 keep=0
  while [[ "${i}" -lt "${#COPYOUT_RULES[@]}" ]]; do
    # shellcheck disable=SC2053 # the right side is a glob on purpose
    if [[ "$1" == ${COPYOUT_RULES[i + 1]} ]]; then
      if [[ "${COPYOUT_RULES[i]}" == "exclude" ]]; then keep=1; else keep=0; fi
    fi
    i=$((i + 2))
  done
  return "${keep}"
}

body_copy_out() {
  require_mount
  local total=0 parts="" part rel size manifest="${RUN_ROOT}/copyout-manifest.sha256" f list i
  local -a filters
  [[ ! -e "${manifest}" ]] || die "${manifest} already exists"
  list="$(mktemp "${TMPDIR:-/tmp}/scholarchain-copyout.XXXXXX")"
  # Only the parts that exist are selected, sized, listed in the manifest and copied (a salvaged partial run may lack some).
  # Symbolic links are never followed or copied (find -type f; --no-follow-symlinks), so the ceiling bounds every copied byte.
  for part in hadoop er spark results config; do
    [[ -d "${RUN_ROOT}/${part}" ]] || continue
    parts="${parts} ${part}"
    copyout_rules "${part}"
    ( cd "${RUN_ROOT}/${part}" && find . -type f -print ) >"${list}.${part}" || die "could not list ${RUN_ROOT}/${part}"
    while IFS= read -r rel; do
      rel="${rel#./}"
      copyout_keep "${rel}" || continue
      size="$(wc -c <"${RUN_ROOT}/${part}/${rel}")" || die "could not size ${part}/${rel}"
      size="${size//[[:space:]]/}"
      is_uint "${size}" || die "could not size ${part}/${rel}"
      total=$((total + size))
      printf '%s/%s\n' "${part}" "${rel}" >>"${list}"
    done <"${list}.${part}"
    rm -f "${list}.${part}"
  done
  [[ -n "${parts}" ]] || die "nothing to copy out: none of hadoop, er, spark, results, config exists under ${RUN_ROOT}"
  [[ "${total}" -le "${MAX_COPYOUT_BYTES}" ]] || die "copy-out ${total} bytes exceeds the ${MAX_COPYOUT_BYTES} byte ceiling"
  ( cd "${RUN_ROOT}" && LC_ALL=C sort "${list}" | while IFS= read -r f; do
    printf '%s  %s\n' "$(sha256sum "${f}" | cut -d' ' -f1)" "${f}"
  done ) >"${manifest}" || die "could not build the copy-out manifest (sort or sha256sum failed)"
  rm -f "${list}"
  for part in ${parts}; do
    copyout_rules "${part}"
    filters=()
    i=0
    while [[ "${i}" -lt "${#COPYOUT_RULES[@]}" ]]; do
      filters+=("--${COPYOUT_RULES[i]}" "${COPYOUT_RULES[i + 1]}")
      i=$((i + 2))
    done
    aws s3 cp "${RUN_ROOT}/${part}/" "${OUTPUT_PREFIX}/${part}/" --recursive ${filters[@]+"${filters[@]}"} --no-follow-symlinks --region "${REGION}" --only-show-errors
  done
  aws s3 cp "${manifest}" "${OUTPUT_PREFIX}/copyout-manifest.sha256" --region "${REGION}" --only-show-errors
  log "copied ${total} bytes (selected files of${parts}) to ${OUTPUT_PREFIX}"
}

case "${STEP_NAME}" in
  stage-in) body_stage_in ;;
  hadoop-prep) body_hadoop_prep ;;
  entity-resolution) body_entity_resolution ;;
  spark-class-origin) body_spark_class_origin ;;
  spark-job) body_spark_job ;;
  copy-out) body_copy_out ;;
esac
