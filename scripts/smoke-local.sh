#!/usr/bin/env bash
# Phase 13B local smoke: start query-api (offline-synthetic, throwaway key), run smoke-test.sh against it, stop it.
# No AWS and no cloud call: the offline-synthetic mode creates only fake stores and a scripted model.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/smoke-local.sh [--build] [--port N] [--startup-seconds S] [--run-seconds S] [--help]

Purpose
  Reproduce the 13B smoke verification locally: start the real query-api from the service distribution
  (modules/services/target/distribution) in SCHOLARCHAIN_SERVICE_MODE=offline-synthetic, with a freshly generated
  throwaway API key whose sha256 alone is passed to the service (SCHOLARCHAIN_API_KEY_SHA256) and a separate random
  internal-token hash, run scripts/smoke-test.sh against it with the key in SCHOLARCHAIN_SMOKE_API_KEY, and stop the
  service. The supported fixture question is asked: "Synthetic fixture: publication count for A". Nothing is
  deployed and no cloud service is contacted.

Inputs
  --build              when the distribution is missing, run `sbt -batch packageServices` under JDK 17 first
                       (without it a missing distribution is refused with that hint)
  --port N             listen port on 127.0.0.1 (default: a free port chosen at run time)
  --startup-seconds S  wait this long for /healthz (default 60)
  --run-seconds S      hard cap on the service process lifetime (default 300; it is killed with its process group)
  JDK 17: the script applies the JDK 17 environment itself (JAVA_HOME, /usr/libexec/java_home -v 17, then the
  configured fallback). Environment variable names: JAVA_HOME, SBT_BIN, SCHOLARCHAIN_REPO_ROOT.

Modes
  Real run only, local only (loopback). The key is generated per run, never printed, never written to a file.

Human approval points (plan Section 7.3)
  None: nothing leaves this machine.

Exit codes
  0    the service started and every smoke check passed
  2    usage error
  3    refused: JDK 17 or the distribution is missing, or the service did not become healthy
  4    a smoke check failed (the smoke-test.sh STEP marker is in the output)
  5    the sbt build or the service process failed
  124  a command timed out

Evidence produced
  STEP: markers, the smoke-test.sh output, a redacted excerpt of the service log and one RESULT: line on stdout.
EOF2
}

BUILD=0 PORT="" STARTUP_SECONDS=60 RUN_SECONDS=300
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build)
      BUILD=1
      shift
      ;;
    --port | --startup-seconds | --run-seconds)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "smoke-local.sh" "$1 needs a value"
      fi
      case "$1" in
        --port) PORT="$2" ;;
        --startup-seconds) STARTUP_SECONDS="$2" ;;
        --run-seconds) RUN_SECONDS="$2" ;;
      esac
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "smoke-local.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "smoke-local.sh"
sc_banner "local"

SERVICE_PID=""
SERVICE_LOG=""
# shellcheck disable=SC2329 # invoked through the EXIT trap below
_local_cleanup() {
  if [[ -n "${SERVICE_PID}" ]]; then
    kill "${SERVICE_PID}" 2>/dev/null || true
    wait "${SERVICE_PID}" 2>/dev/null || true
  fi
  _sc_on_exit
}
trap '_local_cleanup' EXIT

sc_step "inputs"
sc_require_tool python3
[[ "${STARTUP_SECONDS}" =~ ^[0-9]+$ && "${RUN_SECONDS}" =~ ^[0-9]+$ ]] || sc_usage_error "--startup-seconds and --run-seconds must be integers"
[[ -z "${PORT}" || "${PORT}" =~ ^[0-9]+$ ]] || sc_usage_error "--port must be an integer"

sc_step "jdk17"
sc_setup_jdk17

DIST="${REPO_ROOT}/${ARTIFACT_SERVICE_DIST_DIR}"
sc_step "distribution"
if [[ ! -f "${DIST}/services.jar" || ! -d "${DIST}/lib" || ! -d "${DIST}/prompts" ]]; then
  if [[ "${BUILD}" -eq 0 ]]; then
    sc_refuse "${EX_REFUSED}" "the service distribution is missing under ${ARTIFACT_SERVICE_DIST_DIR}: run 'sbt -batch packageServices' on JDK 17 or pass --build"
  fi
  sc_require_tool "${SBT_BIN:-sbt}"
  RC=0
  sc_exec --timeout "${TIMEOUT_SBT_PACKAGE_SECONDS}" -- "${SBT_BIN:-sbt}" -batch packageServices || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_fail "$(sc_rc_to_exit "${RC}")" "sbt -batch packageServices failed (exit ${RC})"
  [[ -f "${DIST}/services.jar" ]] || sc_refuse "${EX_REFUSED}" "packageServices did not produce ${ARTIFACT_SERVICE_DIST_DIR}/services.jar"
fi
sc_info "distribution: ${ARTIFACT_SERVICE_DIST_DIR} (services.jar sha256 $(sc_sha256 "${DIST}/services.jar"))"

sc_step "throwaway-credentials"
# The key and the two hashes exist only in this process and in the environment of the two children below.
API_KEY="$(python3 -I -c 'import secrets; print("smoke-" + secrets.token_urlsafe(32))')"
INTERNAL_TOKEN="$(python3 -I -c 'import secrets; print("internal-" + secrets.token_urlsafe(32))')"
sc_register_secret "${API_KEY}"
sc_register_secret "${INTERNAL_TOKEN}"
API_KEY_SHA256="$(sc_sha256_string "${API_KEY}")"
INTERNAL_SHA256="$(sc_sha256_string "${INTERNAL_TOKEN}")"
if [[ -z "${PORT}" ]]; then
  PORT="$(python3 -I -c 'import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()')"
fi
sc_info "generated a throwaway API key (not printed); only its sha256 reaches the service; port ${PORT}"

sc_step "start-service"
sc_mktemp SERVICE_LOG
(
  cd "${DIST}"
  exec env SCHOLARCHAIN_SERVICE_MODE=offline-synthetic "SCHOLARCHAIN_API_KEY_SHA256=${API_KEY_SHA256}" \
    "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256=${INTERNAL_SHA256}" SCHOLARCHAIN_HTTP_HOST=127.0.0.1 "SCHOLARCHAIN_HTTP_PORT=${PORT}" \
    python3 -I "${SC_LIB_DIR}/timeout.py" --seconds "${RUN_SECONDS}" --grace 5 --output "${SERVICE_LOG}" -- \
    "${JAVA_HOME}/bin/java" -cp 'services.jar:lib/*' edu.uic.cs441.scholarchain.services.QueryApiMain
) </dev/null >/dev/null 2>&1 &
SERVICE_PID=$!
sc_info "query-api started (offline-synthetic, pid ${SERVICE_PID}, hard cap ${RUN_SECONDS}s)"

_service_log_excerpt() {
  if [[ -s "${SERVICE_LOG}" ]]; then
    printf 'SERVICE-LOG-EXCERPT (redacted, last 15 lines):\n'
    tail -n 15 "${SERVICE_LOG}" | sc_redact_stream | while IFS= read -r line; do printf '  | %s\n' "${line}"; done
  fi
}

sc_step "wait-healthy"
URL="http://127.0.0.1:${PORT}"
STATE="$(mktemp "${TMPDIR:-/tmp}/sc-smoke-wait.XXXXXX")"
SC_TMP_FILES+=("${STATE}")
HEALTHY=0
waited=0
while [[ "${waited}" -lt "${STARTUP_SECONDS}" ]]; do
  if ! kill -0 "${SERVICE_PID}" 2>/dev/null; then
    break
  fi
  if python3 -I "${SC_LIB_DIR}/smoke_client.py" check healthz --url "${URL}" --state "${STATE}" --request-timeout 2 >/dev/null 2>&1; then
    HEALTHY=1
    break
  fi
  sleep 1
  waited=$((waited + 1))
done
if [[ "${HEALTHY}" -ne 1 ]]; then
  _service_log_excerpt
  sc_refuse "${EX_REFUSED}" "the service did not become healthy within ${STARTUP_SECONDS}s"
fi
sc_info "healthy after ~${waited}s"

sc_step "run-smoke-test"
SMOKE_RC=0
SMOKE_OUT="$(env "SCHOLARCHAIN_SMOKE_API_KEY=${API_KEY}" bash "${SC_SCRIPTS_DIR}/smoke-test.sh" --url "${URL}" 2>&1)" || SMOKE_RC=$?
printf '%s\n' "${SMOKE_OUT}" | sc_redact_stream | while IFS= read -r line; do printf 'smoke| %s\n' "${line}"; done
_service_log_excerpt

sc_step "stop-service"
kill "${SERVICE_PID}" 2>/dev/null || true
wait "${SERVICE_PID}" 2>/dev/null || true
SERVICE_PID=""
sc_info "service stopped"

if [[ "${SMOKE_RC}" -ne 0 ]]; then
  sc_fail "${SMOKE_RC}" "smoke-test.sh exited ${SMOKE_RC} against the local offline-synthetic query-api"
fi
sc_result PASS "local offline-synthetic query-api passed all smoke checks on 127.0.0.1:${PORT}" "${EX_OK}"
