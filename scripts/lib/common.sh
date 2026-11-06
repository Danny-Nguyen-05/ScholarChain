#!/usr/bin/env bash
# Shared library for the Phase 13 scripts. Source it; do not execute it.
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
# Compatible with bash 3.2 (macOS /bin/bash): no associative arrays, no mapfile.
# shellcheck shell=bash

SC_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SC_SCRIPTS_DIR="$(dirname "${SC_LIB_DIR}")"

# Documented exit codes shared by every Phase 13 script.
readonly EX_OK=0
readonly EX_USAGE=2
readonly EX_REFUSED=3 # precondition not met or approval check failed; nothing mutating ran
readonly EX_GATE=4    # a verification gate failed
readonly EX_CMDFAIL=5 # an underlying tool command failed
readonly EX_PARTIAL=5 # check.sh only: selected gates passed but others were skipped
readonly EX_TIMEOUT=124
export EX_OK EX_USAGE EX_REFUSED EX_GATE EX_CMDFAIL EX_PARTIAL EX_TIMEOUT

SC_SCRIPT="${SC_SCRIPT:-unknown}"
SC_STATE_ABS=""
SC_STEP="init"
SC_RESULT_DONE=0
SC_SECRETS=()
SC_ACCOUNTS=()
SC_TMP_FILES=()
SC_RM_TREES=()
SC_CFG_OVERRIDES=""
SC_CLOCK_FILE=""
DRY_RUN="${DRY_RUN:-1}"

# ---------------------------------------------------------------------------------------------
# Redaction and logging
# ---------------------------------------------------------------------------------------------

# sc_register_secret VALUE: later output replaces VALUE (for example the raw account ID).
sc_register_secret() {
  if [[ -n "${1:-}" ]]; then
    SC_SECRETS+=("$1")
  fi
}

# sc_register_account VALUE: later output shows the account ID as <acct>.
sc_register_account() {
  if [[ -n "${1:-}" ]]; then
    SC_ACCOUNTS+=("$1")
  fi
}

# sc_register_private_vars FILE: registers the file's path and every quoted string value in it as a
# secret, so later stdout, stderr, retained logs and the timeout trace show <redacted> for them. The
# values are extracted by redact.py and never printed.
sc_register_private_vars() {
  local file="$1" value
  if [[ -z "${file}" || ! -f "${file}" ]]; then
    return 0
  fi
  sc_register_secret "${file}"
  while IFS= read -r value; do
    sc_register_secret "${value}"
  done < <(python3 -I "${SC_LIB_DIR}/redact.py" --extract-private-vars "${file}" 2>/dev/null || true)
}

# _sc_refresh_redact_file: rewrites the 0600 values file (S<TAB>secret, A<TAB>account) that redact.py
# and timeout.py read; exports its PATH (never the values) as SC_REDACT_FILE.
SC_REDACT_FILE="${SC_REDACT_FILE:-}"
_sc_refresh_redact_file() {
  local s
  if [[ -z "${SC_REDACT_FILE}" || ! -f "${SC_REDACT_FILE}" ]]; then
    sc_mktemp SC_REDACT_FILE
    export SC_REDACT_FILE
  fi
  : >"${SC_REDACT_FILE}"
  if [[ ${#SC_SECRETS[@]} -gt 0 ]]; then
    for s in "${SC_SECRETS[@]}"; do
      case "${s}" in *$'\n'*) continue ;; esac
      printf 'S\t%s\n' "${s}" >>"${SC_REDACT_FILE}"
    done
  fi
  if [[ ${#SC_ACCOUNTS[@]} -gt 0 ]]; then
    for s in "${SC_ACCOUNTS[@]}"; do
      case "${s}" in *$'\n'*) continue ;; esac
      printf 'A\t%s\n' "${s}" >>"${SC_REDACT_FILE}"
    done
  fi
}

# sc_redact_stream: stdin to stdout through redact.py with the registered values.
sc_redact_stream() {
  _sc_refresh_redact_file
  python3 -I "${SC_LIB_DIR}/redact.py" --values-file "${SC_REDACT_FILE}"
}

# sc_redact TEXT: replaces registered secrets, secret-named environment values and any
# standalone 12-digit run (an AWS account ID) before text reaches stdout or stderr.
sc_redact() {
  local text="$1" name val s
  while IFS= read -r name; do
    case "${name}" in
      *SECRET* | *TOKEN* | *PASSWORD* | *ACCESS_KEY* | *API_KEY* | *_KEY | *CREDENTIAL* | *PRIVATE_VARS)
        val="${!name:-}"
        if [[ ${#val} -ge 4 ]]; then
          text="${text//"${val}"/<redacted>}"
        fi
        ;;
    esac
  done < <(compgen -e)
  if [[ ${#SC_SECRETS[@]} -gt 0 ]]; then
    for s in "${SC_SECRETS[@]}"; do
      text="${text//"${s}"/<redacted>}"
    done
  fi
  if [[ ${#SC_ACCOUNTS[@]} -gt 0 ]]; then
    for s in "${SC_ACCOUNTS[@]}"; do
      text="${text//"${s}"/<acct>}"
    done
  fi
  # Boundaries exclude letters so 64-hex checksums are never mangled.
  printf '%s' "${text}" | sed -E -e ':a' -e 's/(^|[^0-9A-Za-z])[0-9]{12}([^0-9A-Za-z]|$)/\1<acct>\2/' -e 'ta'
}

sc_now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

sc_info() { printf '[%s] [%s] INFO %s\n' "$(sc_now)" "${RUN_ID}" "$(sc_redact "$*")"; }
sc_warn() { printf '[%s] [%s] WARN %s\n' "$(sc_now)" "${RUN_ID}" "$(sc_redact "$*")" >&2; }
sc_err() { printf '[%s] [%s] ERROR %s\n' "$(sc_now)" "${RUN_ID}" "$(sc_redact "$*")" >&2; }

# sc_step NAME: greppable step marker on stdout.
sc_step() {
  SC_STEP="$1"
  printf 'STEP: %s\n' "$1"
}

# sc_result STATUS DETAIL EXIT_CODE: prints the final RESULT line and exits.
sc_result() {
  local status="$1" detail="$2" code="$3"
  SC_RESULT_DONE=1
  printf 'RESULT: %s %s\n' "${status}" "$(sc_redact "${detail}")"
  exit "${code}"
}

# sc_refuse CODE REASON: precondition/approval refusal naming the failing step.
sc_refuse() {
  local code="$1"
  shift
  sc_err "refused at step ${SC_STEP}: $*"
  sc_result REFUSED "step=${SC_STEP} reason=$*" "${code}"
}

# sc_fail CODE REASON: a gate or command failure naming the failing step.
sc_fail() {
  local code="$1"
  shift
  sc_err "failed at step ${SC_STEP}: $*"
  sc_result FAIL "step=${SC_STEP} reason=$*" "${code}"
}

# sc_usage_exit SCRIPT MESSAGE: an option-parsing error BEFORE sc_init (unknown flag, flag without a value). Prints the
# greppable markers and exactly one RESULT line, then exits 2, so every script ends with one RESULT line even on bad usage.
sc_usage_exit() {
  printf 'STEP: start\nSTEP: usage\n'
  printf '%s: %s\n' "$1" "$(sc_redact "$2")" >&2
  printf 'RESULT: REFUSED step=usage reason=%s\n' "$(sc_redact "$2")"
  exit "${EX_USAGE}"
}

sc_usage_error() {
  sc_err "usage: $*"
  sc_result REFUSED "step=usage reason=$*" "${EX_USAGE}"
}

# sc_mktemp VARNAME [dir]: creates a temp file (or directory with "dir") and removes it at exit.
sc_mktemp() {
  local f
  if [[ "${2:-}" == "dir" ]]; then
    f="$(mktemp -d "${TMPDIR:-/tmp}/sc-tmp.XXXXXX")"
  else
    f="$(mktemp "${TMPDIR:-/tmp}/sc-tmp.XXXXXX")"
  fi
  SC_TMP_FILES+=("${f}")
  printf -v "$1" '%s' "${f}"
}

_sc_on_exit() {
  local rc=$?
  if [[ "${SC_RESULT_DONE}" -eq 0 && "${rc}" -ne 0 ]]; then
    SC_RESULT_DONE=1
    printf 'RESULT: FAIL step=%s reason=unexpected-exit code=%s\n' "${SC_STEP}" "${rc}"
  fi
  if [[ ${#SC_TMP_FILES[@]} -gt 0 ]]; then
    rm -rf "${SC_TMP_FILES[@]}"
  fi
  if [[ ${#SC_RM_TREES[@]} -gt 0 ]]; then
    # Materialized sources are read-only trees: restore write permission before removing them.
    chmod -R u+w "${SC_RM_TREES[@]}" 2>/dev/null || true
    rm -rf "${SC_RM_TREES[@]}"
  fi
}

# ---------------------------------------------------------------------------------------------
# Initialization, repository root and configuration
# ---------------------------------------------------------------------------------------------

# sc_init SCRIPT_NAME: run id, repo root, configuration, EXIT trap. Changes into the repo root.
sc_init() {
  SC_SCRIPT="$1"
  RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  trap _sc_on_exit EXIT
  if [[ -n "${SCHOLARCHAIN_REPO_ROOT:-}" ]]; then
    REPO_ROOT="${SCHOLARCHAIN_REPO_ROOT}"
  else
    REPO_ROOT="$(git -C "${SC_SCRIPTS_DIR}" rev-parse --show-toplevel 2>/dev/null || true)"
  fi
  if [[ -z "${REPO_ROOT}" || ! -d "${REPO_ROOT}" ]]; then
    sc_step "repo-root"
    sc_refuse "${EX_REFUSED}" "cannot find the repository root (run inside the checkout or set SCHOLARCHAIN_REPO_ROOT)"
  fi
  REPO_ROOT="$(cd "${REPO_ROOT}" && pwd -P)"
  cd "${REPO_ROOT}" || exit "${EX_REFUSED}"
  sc_load_config
  case "${PLAN_DIR}" in
    /* | *..*)
      sc_step "config"
      sc_refuse "${EX_REFUSED}" "PLAN_DIR must be a relative path inside the repository without '..'"
      ;;
  esac
  PLAN_DIR_ABS="${REPO_ROOT}/${PLAN_DIR}"
  SC_STATE_ABS="${REPO_ROOT}/${TERRAFORM_STATE_FILE}"
  # Whenever a private variable file is named, its path and string values are redacted from every
  # script's output, retained logs and timeout trace (the file is only read, never printed).
  if [[ -n "${!TF_PRIVATE_VARS_ENV:-}" ]]; then
    sc_register_private_vars "${!TF_PRIVATE_VARS_ENV}"
  fi
  export REPO_ROOT RUN_ID
}

# Integrity and safety pins: always taken from the config file; a same-named environment variable
# is ignored (and announced). Tests point at a fixture file with SCHOLARCHAIN_CONFIG_FILE instead.
SC_PINNED_KEYS=" TERRAFORM_STATE_FILE CLEANUP_PROTECTION_RULES CLEANUP_PREPARE_ALLOWED_ATTRS REQUIRED_TERRAFORM_VERSION RUNTIME_ARCHIVE_EXPECTED_SHA256 RUNTIME_ARCHIVE_EXPECTED_SIZE IMAGE_PLATFORM ECS_ARCH_SOURCE APPROVAL_RECORD_PATH SERVICE_ARTIFACTS PLAN_DIR PRESPEND_MAX_AGE_HOURS PRESPEND_MIN_HEADROOM_USD CLEANUP_PRESERVE_TYPE_RULES CLEANUP_PRESERVE_ADDRESS_RULES CLEANUP_TEARDOWN_ADDRESS_RULES RUNTIME_LIVE_MODULE RUNTIME_LIVE_INDICATOR_TYPES RUNTIME_LIVE_PROTECTED_TYPES EMR_MAX_RUN_USD EMR_MAX_LIVE_RUNS EMR_CUMULATIVE_CAP_USD EMR_LEDGER_PATH PIPELINE_PRICING_FILE RUN_APPROVAL_RECORD_PATH PIPELINE_SPARK_CONF_FILE PIPELINE_RUNS_DIR EXPERIMENT_RUNS_DIR PIPELINE_EFS_MOUNT PIPELINE_RUNTIME_DIR PIPELINE_JOB_JAR_PATH PIPELINE_JAVA_HOME_FILE PIPELINE_STEP_BIN_DIR PIPELINE_STEP_ARG_MAX_CHARS PIPELINE_EXPECTED_SPARK_VERSION PIPELINE_EXPECTED_SCALA_VERSION PIPELINE_MAX_CAPACITY PIPELINE_MAX_RUNTIME_MINUTES PIPELINE_MAX_IDLE_TIMEOUT_SECONDS PIPELINE_STEP_WEIGHTS PIPELINE_MIN_STEP_SECONDS PIPELINE_MAX_INPUT_BYTES PIPELINE_MAX_COPYOUT_BYTES PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS PIPELINE_CEILING_REDUCER_COUNT PIPELINE_CEILING_MAX_CANDIDATE_BLOCK_SIZE PIPELINE_CEILING_MAX_CANDIDATE_PAIRS_PER_BLOCK PIPELINE_CEILING_MAX_AUTHOR_TEAM_SIZE PIPELINE_CEILING_MAX_RECORD_BYTES PIPELINE_CEILING_MAX_XML_ENTITY_EXPANSION PIPELINE_ER_XMX PIPELINE_MAX_EXECUTORS_PER_NODE ARCHIVE_MAX_COPY_BYTES "

# sc_load_config: read the config file without executing it. Pinned keys ignore the environment;
# every other key may be overridden by a same-named environment variable (announced).
# SCHOLARCHAIN_CONFIG_FILE replaces the whole file (test-only mechanism, announced on stdout).
sc_load_config() {
  local file="${SC_SCRIPTS_DIR}/config/release.conf" line key val ignored=""
  if [[ -n "${SCHOLARCHAIN_CONFIG_FILE:-}" ]]; then
    file="${SCHOLARCHAIN_CONFIG_FILE}"
    printf 'CONFIG-FILE: using %s instead of the repository config (test-only SCHOLARCHAIN_CONFIG_FILE)\n' "${file}"
  fi
  if [[ ! -f "${file}" ]]; then
    printf 'RESULT: REFUSED step=config reason=missing config file %s\n' "${file}"
    SC_RESULT_DONE=1
    exit "${EX_REFUSED}"
  fi
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^([A-Z][A-Z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      if [[ "${SC_PINNED_KEYS}" == *" ${key} "* ]]; then
        if [[ -n "${!key:-}" && "${!key}" != "${val}" ]]; then
          ignored="${ignored} ${key}"
        fi
        printf -v "${key}" '%s' "${val}"
      elif [[ -n "${!key:-}" ]]; then
        SC_CFG_OVERRIDES="${SC_CFG_OVERRIDES} ${key}"
      else
        printf -v "${key}" '%s' "${val}"
      fi
    fi
  done <"${file}"
  if [[ -n "${ignored}" ]]; then
    printf 'CONFIG-IGNORED: pinned settings cannot be overridden by the environment:%s\n' "${ignored}"
  fi
  # The controllable pre-spend clock is a TEST-ONLY mechanism: honoured only together with the announced
  # SCHOLARCHAIN_CONFIG_FILE; with the real repository config it is ignored (and that is announced too).
  if [[ -n "${SCHOLARCHAIN_TEST_CLOCK_FILE:-}" ]]; then
    if [[ -n "${SCHOLARCHAIN_CONFIG_FILE:-}" ]]; then
      SC_CLOCK_FILE="${SCHOLARCHAIN_TEST_CLOCK_FILE}"
      printf 'CLOCK-OVERRIDE: using %s as the pre-spend clock (test-only; honoured because SCHOLARCHAIN_CONFIG_FILE is set)\n' "${SC_CLOCK_FILE}"
    else
      printf 'CLOCK-IGNORED: SCHOLARCHAIN_TEST_CLOCK_FILE is honoured only together with the test-only SCHOLARCHAIN_CONFIG_FILE\n'
    fi
  fi
  if [[ -n "${SC_CFG_OVERRIDES}" ]]; then
    printf 'CONFIG-OVERRIDE: environment overrides config for:%s\n' "${SC_CFG_OVERRIDES}"
  fi
}

# sc_load_pricing: reads the pinned EMR pricing file (PIPELINE_PRICING_FILE) without executing it. Every key is
# pinned: a same-named environment variable is ignored (announced). SCHOLARCHAIN_PRICING_FILE replaces the
# file ONLY together with the announced test-only SCHOLARCHAIN_CONFIG_FILE (otherwise ignored, announced).
sc_load_pricing() {
  local file="${REPO_ROOT}/${PIPELINE_PRICING_FILE}" line key val ignored="" name
  # An inherited rate or pricing variable can never stand in for a missing line of the pinned file.
  while IFS= read -r name; do
    case "${name}" in
      EMR_RATE_* | EMR_PRICING_*)
        ignored="${ignored} ${name}"
        unset "${name}"
        ;;
    esac
  done < <(compgen -e)
  if [[ -n "${SCHOLARCHAIN_PRICING_FILE:-}" ]]; then
    if [[ -n "${SCHOLARCHAIN_CONFIG_FILE:-}" ]]; then
      file="${SCHOLARCHAIN_PRICING_FILE}"
      printf 'PRICING-FILE: using %s instead of the repository pricing file (test-only SCHOLARCHAIN_PRICING_FILE)\n' "${file}"
    else
      printf 'PRICING-FILE-IGNORED: SCHOLARCHAIN_PRICING_FILE is honoured only together with the test-only SCHOLARCHAIN_CONFIG_FILE\n'
    fi
  fi
  if [[ ! -f "${file}" ]]; then
    printf 'RESULT: REFUSED step=pricing reason=missing pricing file %s\n' "${file}"
    SC_RESULT_DONE=1
    exit "${EX_REFUSED}"
  fi
  while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^(EMR_[A-Z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      printf -v "${key}" '%s' "${val}"
    fi
  done <"${file}"
  if [[ -n "${ignored}" ]]; then
    printf 'CONFIG-IGNORED: pinned pricing settings cannot be overridden by the environment:%s\n' "${ignored}"
  fi
}

# sc_banner MODE: first line of every run.
sc_banner() {
  sc_step "start"
  sc_info "script=${SC_SCRIPT} mode=$1 run_id=${RUN_ID} repo_root=${REPO_ROOT}"
}

# ---------------------------------------------------------------------------------------------
# Command execution (every external command can go through scripts/lib/timeout.py)
# ---------------------------------------------------------------------------------------------

# sc_quote ARG...: shell-quotes each argument for replay; "<" and ">" stay literal so placeholders
# such as <acct> and <profile> read clearly (a placeholder is not replayable on purpose).
sc_quote() {
  local a
  for a in "$@"; do
    if [[ "${a}" =~ ^[A-Za-z0-9_@%+=:,./\<\>-]+$ ]]; then
      printf '%s ' "${a}"
    else
      printf '%q ' "${a}"
    fi
  done
}

# sc_exec [--cloud] [--timeout S] [--log FILE|--log-existing FILE] [--capture FILE|--capture-new FILE]
#         [--stdin FILE] [--show always|fail] -- CMD...
#   --cloud    the command touches the cloud or mutates state: in dry-run mode it is printed, not run
#   --capture  stdout goes to FILE (0600, truncated; a private temp file); stderr goes to the captured output
#   --capture-new  stdout goes to a NEW file: it must not exist; created O_CREAT|O_EXCL|O_NOFOLLOW below the
#              repository root (never truncated, never through a symlink); used for every plan and evidence output
#   --log-existing  append the redacted output to an EXISTING log (created earlier with safeio create-new),
#              opened without O_CREAT and with O_NOFOLLOW below the repository root
# Prints "CMD: timeout=<S>s <redacted command>" (or "DRY-RUN CMD: ...") then runs the command
# through timeout.py. Output is captured; what is appended to --log and what is shown (last 40 lines,
# after failures or always with --show always) is REDACTED first through redact.py (account IDs, secret
# environment values, registered secrets and private variable values); raw subprocess output is never
# persisted. Returns the command's exit code (124 on timeout).
sc_exec() {
  local cloud=0 timeout="${TIMEOUT_QUICK_SECONDS:-120}" log="" log_existing="" capture="" capture_new="" stdin_file="/dev/null" show="fail"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --cloud) cloud=1 ;;
      --timeout)
        timeout="$2"
        shift
        ;;
      --log)
        log="$2"
        shift
        ;;
      --log-existing)
        log_existing="$2"
        shift
        ;;
      --capture)
        capture="$2"
        shift
        ;;
      --capture-new)
        capture_new="$2"
        shift
        ;;
      --stdin)
        stdin_file="$2"
        shift
        ;;
      --show)
        show="$2"
        shift
        ;;
      --)
        shift
        break
        ;;
      *)
        sc_err "sc_exec: unknown option $1"
        return "${EX_USAGE}"
        ;;
    esac
    shift
  done
  _sc_refresh_redact_file
  local printable
  printable="$(sc_redact "$(sc_quote "$@")")"
  if [[ "${cloud}" -eq 1 && "${DRY_RUN}" -eq 1 ]]; then
    printf 'DRY-RUN CMD: timeout=%ss %s\n' "${timeout}" "${printable}"
    return 0
  fi
  printf 'CMD: timeout=%ss %s\n' "${timeout}" "${printable}"
  local out rc=0
  out="$(mktemp "${TMPDIR:-/tmp}/sc-exec.XXXXXX")"
  local helper=(python3 -I "${SC_LIB_DIR}/timeout.py" --seconds "${timeout}" --grace "${TIMEOUT_GRACE_SECONDS:-10}" --output "${out}")
  if [[ -n "${capture}" ]]; then
    helper+=(--stdout "${capture}")
  fi
  if [[ -n "${capture_new}" ]]; then
    helper+=(--stdout-new "${capture_new}" --root "${REPO_ROOT}")
  fi
  if [[ -n "${stdin_file}" ]]; then
    helper+=(--stdin "${stdin_file}")
  fi
  "${helper[@]}" -- "$@" || rc=$?
  if [[ -n "${log}" ]]; then
    if ! (umask 077 && python3 -I "${SC_LIB_DIR}/redact.py" --values-file "${SC_REDACT_FILE}" --append-to "${log}" <"${out}") 2>/dev/null; then
      sc_warn "output not retained in the log: redaction or the symlink-safe append failed"
    fi
  fi
  if [[ -n "${log_existing}" ]]; then
    if ! (umask 077 && python3 -I "${SC_LIB_DIR}/redact.py" --values-file "${SC_REDACT_FILE}" --append-to "${log_existing}" --root "${REPO_ROOT}" <"${out}") 2>/dev/null; then
      sc_warn "output not retained in the log: redaction or the symlink-safe append failed"
    fi
  fi
  if [[ "${rc}" -ne 0 || "${show}" == "always" ]]; then
    if [[ -s "${out}" ]]; then
      local line
      while IFS= read -r line; do
        printf '  | %s\n' "${line}"
      done < <(tail -n 40 "${out}" | python3 -I "${SC_LIB_DIR}/redact.py" --values-file "${SC_REDACT_FILE}")
    fi
  fi
  rm -f "${out}"
  if [[ "${rc}" -eq "${EX_TIMEOUT}" ]]; then
    sc_warn "command timed out after ${timeout}s"
  fi
  return "${rc}"
}

# sc_rc_to_exit RC: 124 stays 124 (timeout); any other command failure maps to EX_CMDFAIL.
sc_rc_to_exit() {
  if [[ "$1" -eq "${EX_TIMEOUT}" ]]; then
    printf '%s' "${EX_TIMEOUT}"
  else
    printf '%s' "${EX_CMDFAIL}"
  fi
}

# ---------------------------------------------------------------------------------------------
# Tool, JDK and Terraform checks
# ---------------------------------------------------------------------------------------------

sc_require_tool() {
  local tool="$1" hint="${2:-}"
  if ! command -v "${tool}" >/dev/null 2>&1; then
    sc_refuse "${EX_REFUSED}" "required tool not found on PATH: ${tool}${hint:+ (${hint})}"
  fi
}

# sc_sha256 FILE: lowercase hex sha256.
sc_sha256() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

# sc_sha256_string STRING: sha256 of the exact string, no trailing newline (account-hash formula).
sc_sha256_string() {
  if command -v shasum >/dev/null 2>&1; then
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}'
  else
    printf '%s' "$1" | sha256sum | awk '{print $1}'
  fi
}

# sc_git ARGS...: git with every inherited GIT_* variable removed (a stray GIT_DIR, GIT_WORK_TREE or
# GIT_INDEX_FILE must not redirect a gate to another repository).
sc_git() {
  local gitenv=() name
  while IFS= read -r name; do
    case "${name}" in GIT_*) gitenv+=(-u "${name}") ;; esac
  done < <(compgen -e)
  if [[ ${#gitenv[@]} -gt 0 ]]; then
    env "${gitenv[@]}" git "$@"
  else
    git "$@"
  fi
}

sc_git_head() { sc_git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null; }

# sc_tree_state: sets SC_TREE_STATE (clean | dirty | error) and SC_TREE_DETAIL. The parsed
# `git status --porcelain=v1 -z --untracked-files=all` output is compared against ONE literal path,
# APPROVAL_RECORD_PATH (exact string comparison, never a git pathspec): the human writes the approval
# record after the plan, and committing it would move HEAD away from APPROVED_COMMIT. Nothing else is
# exempt: --approval does not add an exemption and no environment variable can. A failing or
# unparsable `git status` is state "error", never "clean".
SC_TREE_STATE="error"
SC_TREE_DETAIL=""
export SC_TREE_STATE SC_TREE_DETAIL
sc_tree_state() {
  local rc=0
  SC_TREE_DETAIL="$(python3 -I "${SC_LIB_DIR}/verify.py" git-tree --repo "${REPO_ROOT}" --exempt "${APPROVAL_RECORD_PATH}")" || rc=$?
  case "${rc}" in
    0) SC_TREE_STATE="clean" ;;
    1) SC_TREE_STATE="dirty" ;;
    *) SC_TREE_STATE="error" ;;
  esac
}

# sc_git_dirty: exit 0 unless the tree is verifiably clean (a git failure counts as not clean).
sc_git_dirty() {
  sc_tree_state
  [[ "${SC_TREE_STATE}" != "clean" ]]
}

_sc_is_java17() {
  local home="$1" banner
  [[ -x "${home}/bin/java" ]] || return 1
  banner="$("${home}/bin/java" -version 2>&1 | head -n 1 || true)"
  [[ "${banner}" == *'version "17.'* || "${banner}" == *'version "17"'* ]]
}

# sc_try_jdk17: exports JAVA_HOME/PATH/SBT_OPTS for sbt; returns 1 with SC_ERR_MSG when JDK 17 is unusable.
sc_try_jdk17() {
  local candidates=() c found="" tried=""
  if [[ -n "${JAVA_HOME:-}" ]]; then
    candidates+=("${JAVA_HOME}")
  fi
  local java_home_tool="${JAVA_HOME_TOOL:-/usr/libexec/java_home}"
  if [[ -x "${java_home_tool}" ]]; then
    c="$("${java_home_tool}" -v 17 2>/dev/null || true)"
    if [[ -n "${c}" ]]; then
      candidates+=("${c}")
    fi
  fi
  if [[ -n "${JDK17_FALLBACK_HOME:-}" ]]; then
    candidates+=("${JDK17_FALLBACK_HOME}")
  fi
  if [[ ${#candidates[@]} -gt 0 ]]; then
    for c in "${candidates[@]}"; do
      tried="${tried} ${c}"
      if _sc_is_java17 "${c}"; then
        found="${c}"
        break
      fi
    done
  fi
  if [[ -z "${found}" ]]; then
    SC_ERR_MSG="JDK 17 not found (tried:${tried:- none}); install JDK 17 or set JAVA_HOME to it"
    return 1
  fi
  local logback="${REPO_ROOT}/${SBT_LOGBACK_FILE}"
  if [[ ! -f "${logback}" ]]; then
    SC_ERR_MSG="sbt logback configuration missing: ${SBT_LOGBACK_FILE}"
    return 1
  fi
  export JAVA_HOME="${found}"
  export PATH="${JAVA_HOME}/bin:${PATH}"
  export SBT_OPTS="-Dlogback.configurationFile=${logback}"
  SC_JAVA_VERSION="$("${JAVA_HOME}/bin/java" -version 2>&1 | head -n 1)"
  sc_info "JDK 17 ready: ${SC_JAVA_VERSION} JAVA_HOME=${JAVA_HOME}"
}

sc_setup_jdk17() {
  if ! sc_try_jdk17; then
    sc_refuse "${EX_REFUSED}" "${SC_ERR_MSG}"
  fi
}

# sc_try_terraform: sets TF and TF_VERSION; returns 1 with SC_ERR_MSG unless the CLI is exactly the pinned version.
sc_try_terraform() {
  TF="${TERRAFORM_BIN:-terraform}"
  if ! command -v "${TF}" >/dev/null 2>&1; then
    SC_ERR_MSG="terraform not found (${TF}); install ${REQUIRED_TERRAFORM_VERSION} or set TERRAFORM_BIN"
    return 1
  fi
  local json found probe rc=0
  sc_mktemp probe
  # The version probe is bounded like every other command: it runs through scripts/lib/timeout.py.
  python3 -I "${SC_LIB_DIR}/timeout.py" --seconds "${TIMEOUT_QUICK_SECONDS:-120}" --grace "${TIMEOUT_GRACE_SECONDS:-10}" \
    --stdout "${probe}" --stdin /dev/null -- env CHECKPOINT_DISABLE=1 "${TF}" version -json 2>/dev/null || rc=$?
  json=""
  if [[ "${rc}" -eq 0 ]]; then
    json="$(cat "${probe}")"
  fi
  found="$(printf '%s' "${json}" | python3 -I -c 'import json,sys
try:
    print(json.load(sys.stdin).get("terraform_version",""))
except Exception:
    print("")' 2>/dev/null || true)"
  if [[ -z "${found}" ]]; then
    SC_ERR_MSG="could not read terraform version from '${TF} version -json'"
    return 1
  fi
  if [[ "${found}" != "${REQUIRED_TERRAFORM_VERSION}" ]]; then
    SC_ERR_MSG="terraform version ${found} found; exactly ${REQUIRED_TERRAFORM_VERSION} is required"
    return 1
  fi
  export TF_VERSION="${found}"
  sc_info "terraform ${found} accepted (binary: ${TF})"
}

sc_require_terraform() {
  if ! sc_try_terraform; then
    sc_refuse "${EX_REFUSED}" "${SC_ERR_MSG}"
  fi
}

# sc_service_list: prints "name main" lines from SERVICE_ARTIFACTS.
sc_service_list() {
  local pair
  for pair in ${SERVICE_ARTIFACTS}; do
    printf '%s %s\n' "${pair%%=*}" "${pair#*=}"
  done
}

# sc_ecs_arch: prints linux/amd64 or linux/arm64 from the ECS cpu_architecture, or fails (status 1).
sc_ecs_arch() {
  python3 -I "${SC_LIB_DIR}/tools.py" ecs-arch "${REPO_ROOT}/${ECS_ARCH_SOURCE}"
}

# sc_realpath PATH: canonical absolute path (symlinks resolved even when the leaf does not exist yet).
sc_realpath() {
  python3 -I -c 'import os,sys
print(os.path.realpath(sys.argv[1]))' "$1"
}

# sc_region_valid REGION
sc_region_valid() {
  [[ "$1" =~ ^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$ ]]
}

# sc_name_prefix: <project>-<environment>, the ECR/ECS naming prefix of modules/runtime.
sc_name_prefix() {
  printf '%s-%s' "${NAME_PREFIX_PROJECT}" "${NAME_PREFIX_ENVIRONMENT}"
}

# ---------------------------------------------------------------------------------------------
# Private output locations (plan outputs), verified-copy and source-materialization helpers
# ---------------------------------------------------------------------------------------------

# sc_require_ignored PATH: refuse unless PATH (inside the repo) is ignored by git. Called for EVERY
# derived plan output path before anything is written there.
sc_require_ignored() {
  local path="$1" rel
  case "${path}" in
    "${REPO_ROOT}"/*) rel="${path#"${REPO_ROOT}"/}" ;;
    *) sc_refuse "${EX_REFUSED}" "output path is outside the repository: refused" ;;
  esac
  if ! sc_git -C "${REPO_ROOT}" check-ignore -q -- "${rel}"; then
    sc_refuse "${EX_REFUSED}" "output path ${rel} is not git-ignored (plan outputs may be private); refused before anything was written"
  fi
}

# sc_safeio ARGS...: scripts/lib/safeio.py; a refusal becomes a script refusal carrying its reason. The
# command's stdout is left in SC_SAFEIO_OUT.
SC_SAFEIO_OUT=""
sc_safeio() {
  local out
  if ! out="$(python3 -I "${SC_LIB_DIR}/safeio.py" "$@" 2>&1)"; then
    sc_refuse "${EX_REFUSED}" "${out}"
  fi
  SC_SAFEIO_OUT="${out}"
}

# sc_check_outputs --entry LABEL WITHIN-NAME WITHIN-ABS PATH ...: validates a set of NEW output paths (inside their
# directory, no symlink component, not existing, pairwise distinct and not nested) without creating anything. The
# confined (alias-resolved) path of each entry is left in SC_CHECKED, in order; callers use THOSE paths from then on.
SC_CHECKED=()
sc_check_outputs() {
  local line
  sc_safeio check-new --root "${REPO_ROOT}" "$@"
  SC_CHECKED=()
  while IFS= read -r line; do
    SC_CHECKED+=("${line}")
  done <<<"${SC_SAFEIO_OUT}"
}

# sc_ensure_plan_dir: PLAN_DIR exists with mode 0700 (every component below the repository is a real directory).
sc_ensure_plan_dir() {
  sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${PLAN_DIR}" --within "${PLAN_DIR_ABS}" --path "${PLAN_DIR_ABS}"
  chmod 700 "${PLAN_DIR_ABS}"
}

# sc_run_dir: creates the FRESH private run directory <PLAN_DIR>/<RUN_ID> (mkdir 0700; it must not exist) and sets
# SC_RUN_DIR. Materialized sources, the Terraform data directory and (for plan.sh and cleanup.sh) every private
# output live below it.
SC_RUN_DIR=""
sc_run_dir() {
  local candidate="${PLAN_DIR_ABS}/${RUN_ID}"
  sc_require_ignored "${candidate}"
  sc_safeio fresh-dir --root "${REPO_ROOT}" --within-name "${PLAN_DIR}" --within "${PLAN_DIR_ABS}" --path "${candidate}"
  SC_RUN_DIR="${SC_SAFEIO_OUT}"
}

# sc_private_file PATH...: mode 0600.
sc_private_file() {
  local f
  for f in "$@"; do
    if [[ -e "${f}" ]]; then
      chmod 600 "${f}"
    fi
  done
}

# sc_verified_copy SRC DESTVAR: copies SRC once into a private (0700) temp directory, sets DESTVAR to
# the copy's path (mode 0400). Callers hash and use ONLY the copy, so a later change to SRC is
# irrelevant. When a run directory exists the copy lives inside it (the 322 MB runtime archive must not
# land in a shared temp directory).
SC_VERIFIED_DIR=""
sc_verified_copy() {
  local src="$1" name
  if [[ -z "${SC_VERIFIED_DIR}" ]]; then
    if [[ -n "${SC_RUN_DIR}" ]]; then
      SC_VERIFIED_DIR="${SC_RUN_DIR}/verified"
      mkdir "${SC_VERIFIED_DIR}"
      chmod 700 "${SC_VERIFIED_DIR}"
    else
      sc_mktemp SC_VERIFIED_DIR dir
      chmod 700 "${SC_VERIFIED_DIR}"
    fi
  fi
  name="copy-$(basename "${src}")-$$-${#SC_TMP_FILES[@]}-${SECONDS}-${RANDOM}"
  cp "${src}" "${SC_VERIFIED_DIR}/${name}"
  chmod 400 "${SC_VERIFIED_DIR}/${name}"
  printf -v "$2" '%s' "${SC_VERIFIED_DIR}/${name}"
}

# sc_record_state OUTFILE MODE: reads the identity (present, lineage, serial, sha256) of the LIVE local state file
# named by TERRAFORM_STATE_FILE into OUTFILE (JSON). Only those four facts are read; nothing else leaves the state
# file. MODE exists (the default for every use): a missing state is refused, because a plan against a missing state
# would propose to create resources that already exist. MODE absent (plan.sh --expect-new-state, a very first
# deployment): an existing state is refused instead.
sc_record_state() {
  local outfile="$1" mode="$2" identity
  if ! identity="$(python3 -I "${SC_LIB_DIR}/state_bind.py" inspect --state "${SC_STATE_ABS}")"; then
    sc_refuse "${EX_REFUSED}" "${identity}"
  fi
  printf '%s\n' "${identity}" >"${outfile}"
  if [[ "${mode}" == "exists" && "${identity}" == *'"present": false'* ]]; then
    sc_refuse "${EX_REFUSED}" "the live state file ${TERRAFORM_STATE_FILE} does not exist: a plan against a missing state would propose to create resources that already exist (use plan.sh --expect-new-state only for a very first deployment)"
  fi
  if [[ "${mode}" == "absent" && "${identity}" != *'"present": false'* ]]; then
    sc_refuse "${EX_REFUSED}" "--expect-new-state was given but the live state file ${TERRAFORM_STATE_FILE} already exists: plan against it (without the flag)"
  fi
  sc_info "live state ${TERRAFORM_STATE_FILE}: ${identity}"
}

# sc_materialize_source COMMIT RUNDIR: extracts TERRAFORM_ROOT exactly as committed at COMMIT (git archive, so no
# ignored or untracked file such as override.tf can come along) into RUNDIR/source/COMMIT, writes the local-backend
# binding to the LIVE state file (state_bind.py), hashes the resulting tree and makes it read-only. The current
# scripts run against that source, so a rollback does not need the previous tree to contain the release scripts.
# Sets SC_SRC_BASE, SC_TF_ROOT_DIR, SC_TF_DATA_DIR and SC_SRC_TREE_SHA256.
SC_SRC_BASE=""
SC_TF_ROOT_DIR=""
SC_TF_DATA_DIR=""
SC_SRC_TREE_SHA256=""
export SC_SRC_BASE SC_TF_ROOT_DIR SC_TF_DATA_DIR SC_SRC_TREE_SHA256
sc_materialize_source() {
  local commit="$1" rundir="$2" base out
  if [[ ! "${commit}" =~ ^[0-9a-f]{40}$ ]] || ! sc_git -C "${REPO_ROOT}" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    sc_refuse "${EX_REFUSED}" "source commit ${commit} is not a commit in this repository"
  fi
  base="${rundir}/source/${commit}"
  sc_require_ignored "${base}"
  mkdir -p "${rundir}/source"
  if ! mkdir "${base}"; then
    sc_refuse "${EX_REFUSED}" "the source directory already exists in this run directory"
  fi
  chmod 700 "${base}"
  printf 'CMD: git archive --format=tar %s %s | tar -x -C <run-dir>/source/%s\n' "${commit}" "${TERRAFORM_ROOT}" "${commit}"
  if ! sc_git -C "${REPO_ROOT}" archive --format=tar "${commit}" "${TERRAFORM_ROOT}" | tar -x -C "${base}"; then
    sc_refuse "${EX_REFUSED}" "could not materialize ${TERRAFORM_ROOT} from commit ${commit}"
  fi
  if [[ ! -d "${base}/${TERRAFORM_ROOT}" ]]; then
    sc_refuse "${EX_REFUSED}" "commit ${commit} has no ${TERRAFORM_ROOT}"
  fi
  if ! out="$(python3 -I "${SC_LIB_DIR}/state_bind.py" write-binding --root "${base}/${TERRAFORM_ROOT}" --state "${SC_STATE_ABS}")"; then
    sc_refuse "${EX_REFUSED}" "${out}"
  fi
  if ! SC_SRC_TREE_SHA256="$(python3 -I "${SC_LIB_DIR}/state_bind.py" tree-hash --root "${base}/${TERRAFORM_ROOT}")"; then
    sc_refuse "${EX_REFUSED}" "cannot hash the materialized source tree"
  fi
  mkdir -p "${rundir}/tfdata"
  chmod 700 "${rundir}/tfdata"
  chmod -R a-w "${base}"
  SC_SRC_BASE="${base}"
  SC_TF_ROOT_DIR="${base}/${TERRAFORM_ROOT}"
  SC_TF_DATA_DIR="${rundir}/tfdata"
  sc_info "materialized ${TERRAFORM_ROOT} at ${commit} (read-only, bound to the live state ${TERRAFORM_STATE_FILE}): source_tree_sha256=${SC_SRC_TREE_SHA256}"
}
