#!/usr/bin/env bash
# ScholarChain Phase 12D spike - EMR bootstrap action (runs on every node).
#
# Order matters:
#   1. parse arguments (no network)
#   2. arm the hard node deadline (`shutdown -h +N`) BEFORE any download
#   3. download + sha256-verify the runtime, extract it
#   4. install the EFS mount helper and mount the access point (TLS + IAM)
#   5. primary only: prepare directories on EFS, extract the G1 inputs
# Any failure exits nonzero, which makes EMR fail the bootstrap and terminate
# the cluster.
#
# Everything environment-specific is injectable for local PATH-shim tests:
#   SC_RUNTIME_DEST  (default /opt/scholarchain-runtime)
#   SC_SPIKE_BIN     (default /opt/scholarchain-spike/bin)
#   SC_MNT           (default /mnt/scholarchain)
#   SC_PROC_UPTIME   (default /proc/uptime)
#   SC_PROC_MOUNTS   (default /proc/mounts)
#   SC_INSTANCE_JSON (default /mnt/var/lib/info/instance.json)
#   SC_WORK          (default: mktemp -d)
#   SC_FALLBACK_DEADLINE_MINUTES (default 60; used if --max-minutes is missing)
# Commands are looked up on PATH: sudo aws sha256sum tar shutdown mount dnf.
set -euo pipefail

RUNTIME_DEST="${SC_RUNTIME_DEST:-/opt/scholarchain-runtime}"
SPIKE_BIN="${SC_SPIKE_BIN:-/opt/scholarchain-spike/bin}"
MNT="${SC_MNT:-/mnt/scholarchain}"
PROC_UPTIME="${SC_PROC_UPTIME:-/proc/uptime}"
PROC_MOUNTS="${SC_PROC_MOUNTS:-/proc/mounts}"
INSTANCE_JSON="${SC_INSTANCE_JSON:-/mnt/var/lib/info/instance.json}"
FALLBACK_MIN="${SC_FALLBACK_DEADLINE_MINUTES:-60}"

BUCKET="" REGION="" MAX_MIN="" ALLOW_MIN="5"
RUNTIME_KEY="" RUNTIME_SHA="" JOB_JAR_SHA="" INPUTS_KEY="" INPUTS_SHA=""
G1_KEY="" DEFAULTS_KEY="" RUN_STEP_KEY="" COLLECT_KEY="" EFS_ID="" AP_ID=""
JAVA_HOME_DIR="/usr/lib/jvm/java-17-amazon-corretto"

log() { printf '[bootstrap] %s\n' "$*" >&2; }
die() { local code="$1"; shift; log "FATAL: $*"; exit "$code"; }

# 1. arguments ---------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket) BUCKET="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    --max-minutes) MAX_MIN="${2:-}"; shift 2 ;;
    --startup-allowance-minutes) ALLOW_MIN="${2:-}"; shift 2 ;;
    --runtime-key) RUNTIME_KEY="${2:-}"; shift 2 ;;
    --runtime-sha256) RUNTIME_SHA="${2:-}"; shift 2 ;;
    --job-jar-sha256) JOB_JAR_SHA="${2:-}"; shift 2 ;;
    --inputs-key) INPUTS_KEY="${2:-}"; shift 2 ;;
    --inputs-sha256) INPUTS_SHA="${2:-}"; shift 2 ;;
    --g1-config-key) G1_KEY="${2:-}"; shift 2 ;;
    --spark-defaults-key) DEFAULTS_KEY="${2:-}"; shift 2 ;;
    --run-step-key) RUN_STEP_KEY="${2:-}"; shift 2 ;;
    --collect-key) COLLECT_KEY="${2:-}"; shift 2 ;;
    --efs-id) EFS_ID="${2:-}"; shift 2 ;;
    --access-point-id) AP_ID="${2:-}"; shift 2 ;;
    --java-home) JAVA_HOME_DIR="${2:-}"; shift 2 ;;
    *) log "unknown argument: $1"; UNKNOWN_ARG=1; shift ;;
  esac
done

# 2. hard deadline FIRST ------------------------------------------------------
# minutes = max_cluster_minutes - minutes already up since boot - startup allowance
arm_deadline() {
  local max="$1" up_s up_min minutes
  up_s="$(cut -d' ' -f1 "$PROC_UPTIME" 2>/dev/null | cut -d. -f1 || true)"
  case "$up_s" in ''|*[!0-9]*) up_s=0 ;; esac
  up_min=$(( (up_s + 59) / 60 ))
  minutes=$(( max - up_min - ALLOW_MIN ))
  if [ "$minutes" -lt 1 ]; then minutes=1; fi
  log "arming node shutdown in ${minutes} minute(s) (max=${max}, uptime=${up_min}m, allowance=${ALLOW_MIN}m)"
  sudo shutdown -h "+${minutes}" "scholarchain spike hard deadline" \
    || die 10 "could not arm the shutdown deadline; failing closed"
}

case "$MAX_MIN" in
  ''|*[!0-9]*) arm_deadline "$FALLBACK_MIN"; die 64 "--max-minutes missing or not an integer (fallback deadline armed)" ;;
esac
case "$ALLOW_MIN" in
  ''|*[!0-9]*) ALLOW_MIN=5 ;;
esac
arm_deadline "$MAX_MIN"

[ "${UNKNOWN_ARG:-0}" = "0" ] || die 64 "unknown argument(s)"
for v in BUCKET REGION RUNTIME_KEY RUNTIME_SHA JOB_JAR_SHA INPUTS_KEY INPUTS_SHA G1_KEY DEFAULTS_KEY RUN_STEP_KEY COLLECT_KEY EFS_ID AP_ID; do
  [ -n "${!v}" ] || die 64 "missing required argument for $v"
done

WORK="${SC_WORK:-$(mktemp -d)}"
mkdir -p "$WORK"

fetch() { # key dest
  log "download s3://${BUCKET}/$1"
  aws s3 cp "s3://${BUCKET}/$1" "$2" --region "$REGION" --only-show-errors
}
sha_of() { sha256sum "$1" | cut -d' ' -f1; }
verify() { # file expected label
  local got
  got="$(sha_of "$1")"
  if [ "$got" != "$2" ]; then
    rm -f "$1"
    die 3 "sha256 mismatch for $3: expected $2 got $got"
  fi
  log "sha256 ok: $3"
}

# 3. runtime -----------------------------------------------------------------
fetch "$RUNTIME_KEY" "$WORK/runtime.tgz"
verify "$WORK/runtime.tgz" "$RUNTIME_SHA" "runtime tarball"

parent="$(dirname "$RUNTIME_DEST")"
sudo mkdir -p "$parent"
sudo rm -rf "$RUNTIME_DEST"
sudo tar -xzf "$WORK/runtime.tgz" -C "$parent" --no-same-owner
[ -d "$parent/scholarchain-runtime" ] || die 3 "runtime tarball did not contain scholarchain-runtime/"
if [ "$parent/scholarchain-runtime" != "$RUNTIME_DEST" ]; then
  sudo mv "$parent/scholarchain-runtime" "$RUNTIME_DEST"
fi
sudo chmod -R a+rX "$RUNTIME_DEST"
rm -f "$WORK/runtime.tgz"
verify "$RUNTIME_DEST/application/scholarchain-job.jar" "$JOB_JAR_SHA" "job jar"

# Java check: the runtime needs the documented Corretto 17.
[ -x "$JAVA_HOME_DIR/bin/java" ] || die 4 "no java at $JAVA_HOME_DIR/bin/java"
"$JAVA_HOME_DIR/bin/java" -version 2>&1 | grep -q 'version "17' || die 4 "$JAVA_HOME_DIR is not Java 17"

# spark defaults and step scripts (every node)
fetch "$DEFAULTS_KEY" "$WORK/spark-defaults.conf"
sudo mkdir -p "$RUNTIME_DEST/conf" "$SPIKE_BIN"
sudo cp "$WORK/spark-defaults.conf" "$RUNTIME_DEST/conf/spark-defaults.conf"
sudo chmod a+r "$RUNTIME_DEST/conf/spark-defaults.conf"
fetch "$RUN_STEP_KEY" "$WORK/run-step.sh"
fetch "$COLLECT_KEY" "$WORK/collect-results.sh"
sudo cp "$WORK/run-step.sh" "$SPIKE_BIN/run-step.sh"
sudo cp "$WORK/collect-results.sh" "$SPIKE_BIN/collect-results.sh"
sudo chmod 755 "$SPIKE_BIN/run-step.sh" "$SPIKE_BIN/collect-results.sh"

# 4. EFS ---------------------------------------------------------------------
sudo dnf install -y amazon-efs-utils || die 5 "could not install amazon-efs-utils"
sudo mkdir -p "$MNT"
sudo mount -t efs -o "tls,iam,accesspoint=${AP_ID}" "${EFS_ID}:/" "$MNT" \
  || die 5 "EFS mount failed"
grep -q " ${MNT} " "$PROC_MOUNTS" || die 5 "$MNT is not a mount point after mount; refusing to use a local directory"
log "EFS mounted at $MNT"

# 5. primary only ------------------------------------------------------------
if [ -r "$INSTANCE_JSON" ] && grep -Eq '"isMaster"[[:space:]]*:[[:space:]]*true' "$INSTANCE_JSON"; then
  log "primary node: preparing $MNT"
  mkdir -p "$MNT/inputs" "$MNT/config" "$MNT/results" "$MNT/outputs" "$MNT/checkpoints" "$MNT/staging" "$MNT/probe-shared"
  fetch "$INPUTS_KEY" "$WORK/inputs.tgz"
  verify "$WORK/inputs.tgz" "$INPUTS_SHA" "G1 inputs tarball"
  tar -xzf "$WORK/inputs.tgz" -C "$MNT/inputs"
  fetch "$G1_KEY" "$MNT/config/spark-g1-portable.json"
else
  log "core node: nothing further to prepare"
fi
log "bootstrap complete"
