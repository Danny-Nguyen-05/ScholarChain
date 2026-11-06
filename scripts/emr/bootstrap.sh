#!/usr/bin/env bash
# ScholarChain Phase 13C - main EMR bootstrap action (runs on every node of the Terraform-created cluster).
#
# Ported from the live-proven Phase 12D spike bootstrap (scripts/phase12d-spike/emr/bootstrap.sh) to decision 12-10:
# EMR emr-7.8.0 with applications ["Hadoop"] only and a portable Spark 3.5.4 / Scala 2.13.14 runtime on Java 17.
# A human uploads the runtime archive, the job JAR and this script in Phase 14; Terraform (modules/emr) passes their
# S3 URIs and sha256 values from tfvars. Nothing is uploaded before then.
#
# Order matters:
#   1. parse and validate every argument (no network)
#   2. arm the hard node deadline (`shutdown -h +N`) BEFORE any download
#   3. verify this script against --self-sha256 (drift detection; see the note below)
#   4. download the runtime archive from the S3 URI, verify its sha256, check every member path, extract it
#   5. download the job JAR, verify its sha256, install it at the pinned path
#   6. resolve Java 17 at run time (never hard-coded), validate the path, write the Java-home file
#   7. decode the Terraform-rendered spark-defaults, verify its sha256, make JAVA_HOME appear exactly once per key
#   8. every --artifact (step scripts, config): download, verify sha256, install under an allowed directory. Finding C1: the
#      four EMR step programs (sc-step.sh, sc-ceiling-check.py, sc-class-origin-verify.py, sc-render-spark-config.py, all in
#      scripts/emr/) are installed this way into STEP_BIN; every EMR step runs sc-step.sh from there after verifying it
#      against the sha256 the pipeline computed from the repository file (EMR allows only 10,280 characters per step argument)
#   9. install the EFS mount helper and mount the access point (G1 option ii: EFS staging plus S3 copy steps)
#  10. primary only: prepare the run directories on EFS and install the --artifact files that live on EFS
# ANY mismatch or failure exits nonzero, which makes EMR fail the bootstrap and terminate the cluster (fail closed).
#
# Installed paths are the ones scripts/config/release.conf pins and scripts/lib/pipeline.py expects:
#   PIPELINE_RUNTIME_DIR=/opt/scholarchain-runtime
#   PIPELINE_JOB_JAR_PATH=/opt/scholarchain-runtime/application/scholarchain-job.jar
#   PIPELINE_JAVA_HOME_FILE=/opt/scholarchain-spike/java-home
#   PIPELINE_EFS_MOUNT=/mnt/scholarchain
# A test (scripts/tests/test_emr_bootstrap.py) compares the defaults below with release.conf.
#
# Note on --self-sha256: EMR downloads this script itself, so a check inside it is drift detection (the script that
# runs is the script whose hash Terraform recorded), not tamper protection against someone who can replace both the
# script and the arguments. The artifact checks (runtime, JAR, spark-defaults, --artifact) have the same trust root:
# the sha256 values come from Terraform, which comes from the reviewed tfvars.
#
# Everything environment-specific is injectable for local PATH-shim tests:
#   SC_RUNTIME_DEST  SC_JOB_JAR_PATH  SC_STEP_BIN  SC_MNT  SC_PROC_UPTIME  SC_PROC_MOUNTS  SC_INSTANCE_JSON  SC_WORK
#   SC_FALLBACK_DEADLINE_MINUTES  SC_JVM_DIR  SC_ALT_JRE  SC_JAVA_HOME_FILE
# Commands are looked up on PATH: sudo aws sha256sum tar shutdown mount dnf base64.
set -euo pipefail

RUNTIME_DEST="${SC_RUNTIME_DEST:-/opt/scholarchain-runtime}"
JOB_JAR_DEST="${SC_JOB_JAR_PATH:-/opt/scholarchain-runtime/application/scholarchain-job.jar}"
STEP_BIN="${SC_STEP_BIN:-/opt/scholarchain-spike/bin}"
MNT="${SC_MNT:-/mnt/scholarchain}"
PROC_UPTIME="${SC_PROC_UPTIME:-/proc/uptime}"
PROC_MOUNTS="${SC_PROC_MOUNTS:-/proc/mounts}"
INSTANCE_JSON="${SC_INSTANCE_JSON:-/mnt/var/lib/info/instance.json}"
FALLBACK_MIN="${SC_FALLBACK_DEADLINE_MINUTES:-60}"
JVM_DIR="${SC_JVM_DIR:-/usr/lib/jvm}"
ALT_JRE="${SC_ALT_JRE:-/etc/alternatives/jre}"
JAVA_HOME_FILE="${SC_JAVA_HOME_FILE:-/opt/scholarchain-spike/java-home}"

REGION="" MAX_MIN="" ALLOW_MIN="5" SELF_SHA=""
RUNTIME_URI="" RUNTIME_SHA="" JOB_JAR_URI="" JOB_JAR_SHA="" DEFAULTS_B64="" DEFAULTS_SHA=""
EFS_ID="" AP_ID="" JAVA_HOME_ARG=""
ARTIFACTS=()
UNKNOWN_ARG=0

log() { printf '[bootstrap] %s\n' "$*" >&2; }
die() {
  local code="$1"
  shift
  log "FATAL: $*"
  exit "${code}"
}

# 1. arguments ---------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --region) REGION="${2:-}"; shift 2 || break ;;
    --max-minutes) MAX_MIN="${2:-}"; shift 2 || break ;;
    --startup-allowance-minutes) ALLOW_MIN="${2:-}"; shift 2 || break ;;
    --self-sha256) SELF_SHA="${2:-}"; shift 2 || break ;;
    --runtime-uri) RUNTIME_URI="${2:-}"; shift 2 || break ;;
    --runtime-sha256) RUNTIME_SHA="${2:-}"; shift 2 || break ;;
    --job-jar-uri) JOB_JAR_URI="${2:-}"; shift 2 || break ;;
    --job-jar-sha256) JOB_JAR_SHA="${2:-}"; shift 2 || break ;;
    --spark-defaults-b64) DEFAULTS_B64="${2:-}"; shift 2 || break ;;
    --spark-defaults-sha256) DEFAULTS_SHA="${2:-}"; shift 2 || break ;;
    --artifact) ARTIFACTS+=("${2:-}"); shift 2 || break ;;
    --efs-id) EFS_ID="${2:-}"; shift 2 || break ;;
    --access-point-id) AP_ID="${2:-}"; shift 2 || break ;;
    --java-home) JAVA_HOME_ARG="${2:-}"; shift 2 || break ;;
    *)
      log "unknown argument: $1"
      UNKNOWN_ARG=1
      shift
      ;;
  esac
done

# 2. hard deadline FIRST ------------------------------------------------------
# minutes = max_cluster_minutes - minutes already up since boot - startup allowance
arm_deadline() {
  local max="$1" up_s up_min minutes
  up_s="$(cut -d' ' -f1 "${PROC_UPTIME}" 2>/dev/null | cut -d. -f1 || true)"
  case "${up_s}" in '' | *[!0-9]*) up_s=0 ;; esac
  up_min=$(((up_s + 59) / 60))
  minutes=$((max - up_min - ALLOW_MIN))
  if [[ "${minutes}" -lt 1 ]]; then minutes=1; fi
  log "arming node shutdown in ${minutes} minute(s) (max=${max}, uptime=${up_min}m, allowance=${ALLOW_MIN}m)"
  sudo shutdown -h "+${minutes}" "scholarchain hard deadline" ||
    die 10 "could not arm the shutdown deadline; failing closed"
}

case "${ALLOW_MIN}" in '' | *[!0-9]*) ALLOW_MIN=5 ;; esac
case "${MAX_MIN}" in
  '' | *[!0-9]*)
    arm_deadline "${FALLBACK_MIN}"
    die 64 "--max-minutes missing or not an integer (fallback deadline armed)"
    ;;
esac
arm_deadline "${MAX_MIN}"

[[ "${UNKNOWN_ARG}" -eq 0 ]] || die 64 "unknown argument(s)"
for v in REGION SELF_SHA RUNTIME_URI RUNTIME_SHA JOB_JAR_URI JOB_JAR_SHA DEFAULTS_B64 DEFAULTS_SHA EFS_ID AP_ID; do
  [[ -n "${!v}" ]] || die 64 "missing required argument for ${v}"
done
HEX64='^[0-9a-f]{64}$'
S3URI='^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/[A-Za-z0-9._/=+@-]+$'
for v in SELF_SHA RUNTIME_SHA JOB_JAR_SHA DEFAULTS_SHA; do
  [[ "${!v}" =~ ${HEX64} ]] || die 64 "${v} is not 64 lowercase hex characters"
done
for v in RUNTIME_URI JOB_JAR_URI; do
  [[ "${!v}" =~ ${S3URI} ]] || die 64 "${v} is not a plain s3://bucket/key URI"
done
[[ "${REGION}" =~ ^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$ ]] || die 64 "--region is not an AWS region name"
[[ "${EFS_ID}" =~ ^fs-[0-9a-f]+$ ]] || die 64 "--efs-id is not an EFS file system id"
[[ "${AP_ID}" =~ ^fsap-[0-9a-f]+$ ]] || die 64 "--access-point-id is not an EFS access point id"

# Allowed install directories for --artifact DEST: the runtime tree, the step-script directory and the EFS config
# directory. Anything else (or any ".." or unsafe character) refuses before a download.
safe_path() { # path: absolute, plain characters only, no ".." component, no "//"
  [[ "$1" =~ ^/[A-Za-z0-9_.+/-]+$ ]] && [[ "$1" != *..* ]] && [[ "$1" != *//* ]]
}
ART_URI=() ART_SHA=() ART_DEST=() ART_ON_EFS=()
for spec in ${ARTIFACTS[@]+"${ARTIFACTS[@]}"}; do
  IFS=, read -r a_uri a_sha a_dest a_extra <<<"${spec}"
  [[ -z "${a_extra:-}" && -n "${a_uri}" && -n "${a_sha}" && -n "${a_dest}" ]] || die 64 "--artifact must be URI,SHA256,DEST"
  [[ "${a_uri}" =~ ${S3URI} ]] || die 64 "--artifact URI is not a plain s3://bucket/key URI"
  [[ "${a_sha}" =~ ${HEX64} ]] || die 64 "--artifact sha256 is not 64 lowercase hex characters"
  safe_path "${a_dest}" || die 64 "--artifact DEST is not a safe absolute path"
  on_efs=0
  case "${a_dest}" in
    "${RUNTIME_DEST}"/* | "${STEP_BIN}"/*) ;;
    "${MNT}"/config/*) on_efs=1 ;;
    *) die 64 "--artifact DEST must be under ${RUNTIME_DEST}/, ${STEP_BIN}/ or ${MNT}/config/" ;;
  esac
  ART_URI+=("${a_uri}")
  ART_SHA+=("${a_sha}")
  ART_DEST+=("${a_dest}")
  ART_ON_EFS+=("${on_efs}")
done

WORK="${SC_WORK:-$(mktemp -d)}"
mkdir -p "${WORK}"

sha_of() { sha256sum "$1" | cut -d' ' -f1; }
check_sha() { # file expected label: returns nonzero on a mismatch; never touches the file
  local got
  got="$(sha_of "$1")"
  if [[ "${got}" != "$2" ]]; then
    log "sha256 mismatch for $3: expected $2 got ${got}"
    return 1
  fi
  log "sha256 ok: $3"
}
verify() { # file expected label: a mismatch removes the DOWNLOADED file and fails closed (never used for this script)
  check_sha "$@" || {
    rm -f "$1"
    die 3 "sha256 mismatch for $3"
  }
}
fetch() { # uri dest
  log "download $1"
  aws s3 cp "$1" "$2" --region "${REGION}" --only-show-errors || die 6 "download failed: $1"
}

# 3. this script ---------------------------------------------------------------
check_sha "${BASH_SOURCE[0]}" "${SELF_SHA}" "bootstrap script (drift check)" || die 3 "sha256 mismatch for the bootstrap script (drift check)"

# 4. runtime -----------------------------------------------------------------
fetch "${RUNTIME_URI}" "${WORK}/runtime.tgz"
verify "${WORK}/runtime.tgz" "${RUNTIME_SHA}" "runtime archive"
# Every member must stay inside scholarchain-runtime/: no absolute path, no ".." component.
members_ok=1
while IFS= read -r member; do
  case "${member}" in
    scholarchain-runtime | scholarchain-runtime/*) ;;
    *) members_ok=0 ;;
  esac
  case "/${member}/" in */../*) members_ok=0 ;; esac
done < <(tar -tzf "${WORK}/runtime.tgz")
[[ "${members_ok}" -eq 1 ]] || die 3 "the runtime archive holds a member outside scholarchain-runtime/ (or a '..' path); refusing to extract"
parent="$(dirname "${RUNTIME_DEST}")"
sudo mkdir -p "${parent}"
sudo rm -rf "${RUNTIME_DEST}"
sudo tar -xzf "${WORK}/runtime.tgz" -C "${parent}" --no-same-owner
[[ -d "${parent}/scholarchain-runtime" ]] || die 3 "runtime archive did not contain scholarchain-runtime/"
if [[ "${parent}/scholarchain-runtime" != "${RUNTIME_DEST}" ]]; then
  sudo mv "${parent}/scholarchain-runtime" "${RUNTIME_DEST}"
fi
sudo chmod -R a+rX "${RUNTIME_DEST}"
rm -f "${WORK}/runtime.tgz"

# 5. job JAR ------------------------------------------------------------------
fetch "${JOB_JAR_URI}" "${WORK}/job.jar"
verify "${WORK}/job.jar" "${JOB_JAR_SHA}" "job jar"
sudo mkdir -p "$(dirname "${JOB_JAR_DEST}")"
sudo cp "${WORK}/job.jar" "${JOB_JAR_DEST}"
sudo chmod 644 "${JOB_JAR_DEST}"
check_sha "${JOB_JAR_DEST}" "${JOB_JAR_SHA}" "installed job jar" || die 3 "sha256 mismatch for the installed job jar"

# 6. Java 17 ------------------------------------------------------------------
# Resolved at run time (EMR 7.8.0 does not have the documented /usr/lib/jvm/java-17-amazon-corretto: its controller
# runs /usr/lib/jvm/jre-17, JAVA_HOME=/etc/alternatives/jre). The first SAFE candidate whose bin/java reports major 17
# wins. Item 28: the path is written into a properties-format file, so only plain path characters are accepted; a
# newline, space, '#', '=', ':' or backslash could inject another spark-defaults line.
is_java17() { # home
  [[ -x "$1/bin/java" ]] && "$1/bin/java" -version 2>&1 | grep -Eq 'version "17(\.|")'
}
safe_java_home() { # home: absolute, [A-Za-z0-9_.+/-] only (this also rejects a newline), no ".." component
  [[ "$1" == /* ]] && [[ "$1" =~ ^/[A-Za-z0-9_.+/-]+$ ]] && [[ "$1" != *..* ]]
}
resolve_java() {
  local cands=() c real tried="" rejected=0
  if [[ -n "${JAVA_HOME_ARG}" ]]; then cands+=("${JAVA_HOME_ARG}"); fi
  cands+=("${JVM_DIR}/jre-17" "${JVM_DIR}/java-17-amazon-corretto" "${JVM_DIR}/java-17-amazon-corretto.x86_64")
  if real="$(readlink -f "${ALT_JRE}" 2>/dev/null)" && [[ -n "${real}" ]]; then cands+=("${real}"); fi
  if c="$(command -v java 2>/dev/null)" && real="$(readlink -f "${c}" 2>/dev/null)" && [[ -n "${real}" ]]; then
    cands+=("$(dirname "$(dirname "${real}")")")
  fi
  for c in "${cands[@]}"; do
    tried="${tried} ${c//[^A-Za-z0-9_.+\/-]/?}"
    if ! safe_java_home "${c}"; then
      rejected=1
      continue
    fi
    if is_java17 "${c}"; then
      RESOLVED_JAVA_HOME="${c}"
      return 0
    fi
  done
  if [[ "${rejected}" -eq 1 ]]; then
    die 4 "no Java 17 found at a safe path (a candidate had unsafe characters and was rejected); candidates tried:${tried}"
  fi
  die 4 "no Java 17 found; candidates tried:${tried}"
}
resolve_java
log "resolved JAVA_HOME=${RESOLVED_JAVA_HOME}"
sudo mkdir -p "$(dirname "${JAVA_HOME_FILE}")"
printf '%s\n' "${RESOLVED_JAVA_HOME}" | sudo tee "${JAVA_HOME_FILE}" >/dev/null
sudo chmod a+r "${JAVA_HOME_FILE}"

# 7. spark-defaults ------------------------------------------------------------
# Terraform renders the file from the reviewed decision 12-10 settings and passes it base64-encoded with its sha256.
printf '%s' "${DEFAULTS_B64}" | base64 -d >"${WORK}/spark-defaults.conf" 2>/dev/null ||
  printf '%s' "${DEFAULTS_B64}" | base64 -D >"${WORK}/spark-defaults.conf" 2>/dev/null ||
  die 3 "spark-defaults is not valid base64"
verify "${WORK}/spark-defaults.conf" "${DEFAULTS_SHA}" "spark-defaults"
# A trailing backslash is a properties line continuation that could swallow the lines appended below.
if grep -Eq '\\$' "${WORK}/spark-defaults.conf"; then
  die 3 "spark-defaults has a line continuation (trailing backslash); refusing"
fi
# Item 29: remove JAVA_HOME entries whatever the separator (properties allow space, tab, '=' and ':', and leading
# whitespace), then append this node's resolved Java exactly once per key.
JAVA_KEY_RE='^[[:space:]]*spark\.(yarn\.appMasterEnv|executorEnv)\.JAVA_HOME([[:space:]=:]|$)'
{
  grep -Ev "${JAVA_KEY_RE}" "${WORK}/spark-defaults.conf" || true
  printf 'spark.yarn.appMasterEnv.JAVA_HOME %s\nspark.executorEnv.JAVA_HOME %s\n' "${RESOLVED_JAVA_HOME}" "${RESOLVED_JAVA_HOME}"
} >"${WORK}/spark-defaults.final"
for key in 'spark\.yarn\.appMasterEnv\.JAVA_HOME' 'spark\.executorEnv\.JAVA_HOME'; do
  count="$(grep -Ec "^[[:space:]]*${key}([[:space:]=:]|\$)" "${WORK}/spark-defaults.final" || true)"
  [[ "${count}" == "1" ]] || die 3 "spark-defaults must hold ${key//\\/} exactly once (found ${count})"
done
sudo mkdir -p "${RUNTIME_DEST}/conf"
sudo cp "${WORK}/spark-defaults.final" "${RUNTIME_DEST}/conf/spark-defaults.conf"
sudo chmod a+r "${RUNTIME_DEST}/conf/spark-defaults.conf"

# 8. extra artifacts (step scripts, config) not on EFS ---------------------------
install_artifact() { # index
  local i="$1" tmp="${WORK}/artifact.$1"
  fetch "${ART_URI[$i]}" "${tmp}"
  verify "${tmp}" "${ART_SHA[$i]}" "artifact ${ART_DEST[$i]}"
  sudo mkdir -p "$(dirname "${ART_DEST[$i]}")"
  sudo cp "${tmp}" "${ART_DEST[$i]}"
  case "${ART_DEST[$i]}" in
    "${STEP_BIN}"/*) sudo chmod 755 "${ART_DEST[$i]}" ;;
    *) sudo chmod 644 "${ART_DEST[$i]}" ;;
  esac
}
for i in ${ART_URI[@]+"${!ART_URI[@]}"}; do
  if [[ "${ART_ON_EFS[$i]}" -eq 0 ]]; then install_artifact "${i}"; fi
done

# 9. EFS ---------------------------------------------------------------------
sudo dnf install -y amazon-efs-utils || die 5 "could not install amazon-efs-utils"
sudo mkdir -p "${MNT}"
sudo mount -t efs -o "tls,iam,accesspoint=${AP_ID}" "${EFS_ID}:/" "${MNT}" ||
  die 5 "EFS mount failed"
grep -q " ${MNT} " "${PROC_MOUNTS}" || die 5 "${MNT} is not a mount point after mount; refusing to use a local directory"
log "EFS mounted at ${MNT}"

# 10. primary only -------------------------------------------------------------
if [[ -r "${INSTANCE_JSON}" ]] && grep -Eq '"isMaster"[[:space:]]*:[[:space:]]*true' "${INSTANCE_JSON}"; then
  log "primary node: preparing ${MNT}"
  mkdir -p "${MNT}/runs" "${MNT}/staging" "${MNT}/config"
  for i in ${ART_URI[@]+"${!ART_URI[@]}"}; do
    if [[ "${ART_ON_EFS[$i]}" -eq 1 ]]; then install_artifact "${i}"; fi
  done
else
  log "core or task node: nothing further to prepare"
fi
log "bootstrap complete"
