#!/usr/bin/env bash
# Phase 13B smoke test of a running query-api: health, readiness, one bounded query, evidence, idempotency, 401.
# Talks only to the URL it is given. Never prints the API key.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/smoke-test.sh --url URL [--api-key-env NAME] [--query-body FILE] [--checks LIST] [--request-timeout S] [--job-timeout S] [--help]

Purpose
  Check a running query-api through its public contract (modules/services/README.md and the OpenAPI file). Six
  checks run in order; the first failure stops the run and names its STEP marker:
    STEP: smoke-healthz      GET /healthz is 200 with status alive (no authentication)
    STEP: smoke-readyz       GET /readyz is 200 with status ready (no authentication)
    STEP: smoke-query        one bounded researcher query: POST /v1/query with an Idempotency-Key; a 200 answer, or a
                             202 job reference followed to SUCCEEDED and its result; the answer must hold claims
    STEP: smoke-evidence     GET /v1/evidence/{id} for the first evidence id a returned claim cites
    STEP: smoke-idempotency  the same body with the same Idempotency-Key returns the same queryId (and job id) and
                             leaves the stored evidence list unchanged (no duplicate)
    STEP: smoke-error-path   POST /v1/query without a key and with an invalid key are both 401 UNAUTHORIZED, and the
                             error bodies do not echo the key
  Every request has a timeout. This script is read-mostly: the only writes are the idempotent query POSTs.

Inputs
  --url URL              target base URL (or SCHOLARCHAIN_SMOKE_URL): http(s)://host[:port]. Plain http is accepted only
                         for a loopback host, so the bearer key never travels in clear text to a remote host.
  --api-key-env NAME     NAME of the environment variable holding the API key (default SCHOLARCHAIN_SMOKE_API_KEY).
                         The value is never printed, logged or written; it is registered for redaction.
  --query-body FILE      JSON request body (default: the one supported offline-synthetic fixture question
                         {"question":"Synthetic fixture: publication count for A","output":{"includeScores":false}})
  --checks LIST          comma-separated subset of the six checks to run, always in the order above (default: all six). Use
                         healthz,readyz for the unauthenticated health check, healthz,readyz,error-path for health plus the 401
                         path. evidence and idempotency read the state of query, so naming either without query is a usage
                         error (exit 2). No API key is needed (and none is read) when only healthz and/or readyz are selected.
                         The RESULT line names the number of checks that ran, so a partial run is never mistaken for the full six.
  --request-timeout S    seconds per HTTP request (default TIMEOUT_SMOKE_REQUEST_SECONDS)
  --job-timeout S        seconds for an asynchronous job to finish (default TIMEOUT_SMOKE_JOB_SECONDS)
  Environment variable names: SCHOLARCHAIN_SMOKE_URL, SCHOLARCHAIN_SMOKE_API_KEY (or the name given), SCHOLARCHAIN_REPO_ROOT.

Modes
  Real run only. It sends HTTP requests to the target and nothing else (no AWS call). Against the local service use
  scripts/smoke-local.sh, which starts query-api in offline-synthetic mode with a throwaway key and runs this script.
  Phase 14 runs it against the deployed endpoint with the real key supplied through the environment.

Human approval points (plan Section 7.3)
  None for a local or stub target. Pointing it at a deployed endpoint belongs to the Phase 14 gate: the key comes
  from the environment, never from a file in the repository.

Exit codes
  0    every check passed
  2    usage error
  3    refused: no key in the environment variable, or an unsafe target URL
  4    a check failed (the last STEP: marker names it)
  124  a request or job timed out

Evidence produced
  STEP: markers, one CHECK-OK or CHECK-FAILED line per check and one RESULT: line on stdout. Nothing is written.
EOF2
}

URL="${SCHOLARCHAIN_SMOKE_URL:-}" KEY_ENV="SCHOLARCHAIN_SMOKE_API_KEY" BODY_FILE=""
REQUEST_TIMEOUT="" JOB_TIMEOUT="" CHECKS_OPT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --url | --api-key-env | --query-body | --checks | --request-timeout | --job-timeout)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "smoke-test.sh" "$1 needs a value"
      fi
      case "$1" in
        --url) URL="$2" ;;
        --api-key-env) KEY_ENV="$2" ;;
        --query-body) BODY_FILE="$2" ;;
        --checks) CHECKS_OPT="$2" ;;
        --request-timeout) REQUEST_TIMEOUT="$2" ;;
        --job-timeout) JOB_TIMEOUT="$2" ;;
      esac
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "smoke-test.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "smoke-test.sh"
sc_banner "smoke"

sc_step "inputs"
sc_require_tool python3
[[ -n "${URL}" ]] || sc_usage_error "missing required value: --url (or SCHOLARCHAIN_SMOKE_URL)"
[[ "${KEY_ENV}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || sc_usage_error "--api-key-env must be an environment variable NAME"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-${TIMEOUT_SMOKE_REQUEST_SECONDS}}"
JOB_TIMEOUT="${JOB_TIMEOUT:-${TIMEOUT_SMOKE_JOB_SECONDS}}"
[[ "${REQUEST_TIMEOUT}" =~ ^[0-9]+(\.[0-9]+)?$ && "${JOB_TIMEOUT}" =~ ^[0-9]+(\.[0-9]+)?$ ]] || sc_usage_error "timeouts must be positive numbers of seconds"
if [[ -n "${BODY_FILE}" && ! -f "${BODY_FILE}" ]]; then
  sc_usage_error "--query-body file not found"
fi
ALL_CHECKS=(healthz readyz query evidence idempotency error-path)
SELECTED=()
if [[ -z "${CHECKS_OPT}" ]]; then
  SELECTED=("${ALL_CHECKS[@]}")
else
  [[ "${CHECKS_OPT}" =~ ^[a-z-]+(,[a-z-]+)*$ ]] || sc_usage_error "--checks must be a comma-separated list of: ${ALL_CHECKS[*]}"
  IFS=',' read -r -a REQUESTED <<<"${CHECKS_OPT}"
  for want in "${REQUESTED[@]}"; do
    [[ " ${ALL_CHECKS[*]} " == *" ${want} "* ]] || sc_usage_error "--checks: unknown check '${want}' (valid: ${ALL_CHECKS[*]})"
  done
  for name in "${ALL_CHECKS[@]}"; do # the canonical order, whatever order was typed
    [[ ",${CHECKS_OPT}," == *",${name},"* ]] && SELECTED+=("${name}")
  done
  [[ "${#SELECTED[@]}" -eq "${#REQUESTED[@]}" ]] || sc_usage_error "--checks names a check twice"
  if [[ " ${SELECTED[*]} " =~ " evidence " || " ${SELECTED[*]} " =~ " idempotency " ]] && [[ ! " ${SELECTED[*]} " =~ " query " ]]; then
    sc_usage_error "--checks: evidence and idempotency need the query check (add query)"
  fi
fi
NEEDS_KEY=0
for name in "${SELECTED[@]}"; do
  [[ "${name}" == "healthz" || "${name}" == "readyz" ]] || NEEDS_KEY=1
done
KEY_VALUE=""
if [[ "${NEEDS_KEY}" -eq 1 ]]; then
  KEY_VALUE="${!KEY_ENV:-}"
  [[ -n "${KEY_VALUE}" ]] || sc_refuse "${EX_REFUSED}" "the environment variable ${KEY_ENV} holds no API key (export it; the script never prints it)"
  sc_register_secret "${KEY_VALUE}"
fi
URL_OUT="$(python3 -I "${SC_LIB_DIR}/smoke_client.py" validate-url "${URL}")" || sc_refuse "${EX_REFUSED}" "${URL_OUT}"
URL="${URL%/}"
sc_info "target ${URL}; the API key is read from ${KEY_ENV} and is never printed"

sc_mktemp STATE_FILE
: >"${STATE_FILE}"
chmod 600 "${STATE_FILE}"
IDEM_KEY="smoke-${RUN_ID}"
EXTRA=()
[[ -z "${BODY_FILE}" ]] || EXTRA+=(--body-file "${BODY_FILE}")

_check() { # name step
  local name="$1" out rc=0
  sc_step "$2"
  out="$(python3 -I "${SC_LIB_DIR}/smoke_client.py" check "${name}" --url "${URL}" --state "${STATE_FILE}" --key-env "${KEY_ENV}" \
    --request-timeout "${REQUEST_TIMEOUT}" --job-timeout "${JOB_TIMEOUT}" --idem-key "${IDEM_KEY}" ${EXTRA[@]+"${EXTRA[@]}"} 2>&1)" || rc=$?
  printf '%s\n' "$(sc_redact "${out}")"
  if [[ "${rc}" -ne 0 ]]; then
    if [[ "${rc}" -eq 124 ]]; then
      sc_fail "${EX_TIMEOUT}" "${name} check timed out"
    fi
    sc_fail "${EX_GATE}" "${name} check failed"
  fi
}

for name in "${SELECTED[@]}"; do
  _check "${name}" "smoke-${name}"
done

sc_step "smoke-complete"
if [[ "${#SELECTED[@]}" -eq "${#ALL_CHECKS[@]}" ]]; then
  sc_result PASS "all 6 checks passed against ${URL}" "${EX_OK}"
fi
sc_result PASS "only ${#SELECTED[@]} of 6 checks ran (${SELECTED[*]}) and passed against ${URL}; this is not the full smoke test" "${EX_OK}"
