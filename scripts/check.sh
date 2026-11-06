#!/usr/bin/env bash
# Phase 13 validation gates. Real run, no cloud mutation. See usage() or --help.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

ALL_GATES="constitution hooks shell python terraform script-tests sbt"

usage() {
  cat <<'EOF'
Usage: scripts/check.sh [--only GATE[,GATE...]] [--skip GATE[,GATE...]] [--list-gates] [--help]

Purpose
  Run every non-cloud validation gate and exit nonzero if any gate fails. Each gate prints
  "STEP: gate-<name>", a PASS/FAIL line, and the run ends with a summary table and a
  "RESULT:" line. Full per-gate logs go to <CHECK_LOG_DIR>/<run-id>/ (git-ignored target/).

Gates (default: all, in this order)
  constitution   required constitution files exist; every tracked or new *.json parses
                 (fixture prefixes in JSON_FIXTURE_EXCLUDES are skipped)
  hooks          bash -n and shellcheck on the hook scripts under the Claude hooks directory
  shell          bash -n and shellcheck on every tracked and new *.sh (any finding fails)
  python         python3 -I -m py_compile on every scripts/**/*.py
  terraform      exact version check, fmt -check -recursive, then for each root with a
                 versions.tf outside modules/ (root, billing-bootstrap, billing-execution,
                 deployer, spikes/*): init -backend=false -lockfile=readonly (tracked lock files are
                 never rewritten), validate, and test where tests/ exists. It runs BEFORE script-tests
                 on purpose: its init installs the providers the real-Terraform script tests need, so a
                 clean checkout runs them instead of skipping them
  script-tests   scripts/tests (through scripts/lib/suite_run.py), scripts/phase12d-spike/tests and
                 scripts/billing/tests/test_*.py (one process per file) and tests/scripts (the test-engineer's
                 independent script tests). The list is PINNED in this
                 script: an omitted suite fails, and a suite that EXECUTES zero tests fails. Executed =
                 unittest "Ran N" minus the METHOD-level skips (a class-level skip adds one skip but no
                 test to "Ran"); skipped classes are listed separately. In a DEFAULT FULL RUN (no
                 --only/--skip) the real-Terraform classes test_terraform_state_binding.RealStateBindingTests
                 and test_terraform_r1.RouteOwnershipTest must EXECUTE: a skip or a missing class fails the
                 gate (a skip is not a pass). A partial run only warns about them (it is never a pass anyway).
                 tests/scripts is REQUIRED in a default full run: a missing directory, or one that executes
                 no test, fails the gate. Until the test-engineer populates it, a PARTIAL run only warns
                 (SUITE-PENDING) and still ends RESULT: PARTIAL, never a pass
  sbt            sbt -batch check under JDK 17 (scalafmt, Test/compile, tests, contract tests,
                 markTestRun)

Options
  --only LIST    run only these gates; the run ends RESULT: PARTIAL (exit 5) and lists the skipped gates
  --skip LIST    run all except these gates; also ends RESULT: PARTIAL (exit 5)
  --list-gates   print the gate names and exit 0

Inputs (environment variable NAMES; none are secrets)
  JAVA_HOME           optional JDK 17 override (otherwise /usr/libexec/java_home -v 17, then the
                      configured Homebrew path); the run applies the JDK 17 environment itself
  SBT_BIN             sbt executable (default: sbt)
  TERRAFORM_BIN       terraform executable (default: terraform); must report exactly 1.13.5
  SCHOLARCHAIN_REPO_ROOT  repository root override (used by tests)
  SC_TEST_ONLY_SCRIPT_TEST_SUITES  TEST-ONLY: replaces the pinned script-test suite list; announced as
                      SUITES-OVERRIDE and the run can then never end RESULT: PASS (always PARTIAL)
  Non-pinned keys in scripts/config/release.conf may be overridden by an environment variable.

Mode
  Real run only: the gates are local. The terraform gate runs "terraform init", which downloads
  the pinned provider over the network (no AWS API call; AWS credential environment variables
  are unset for it). No terraform plan/apply, docker push or aws command is ever run.

Human approval points (plan Section 7.3)
  None: this script mutates no cloud resource. The four approval points apply to
  scripts/plan.sh --execute, deploy.sh --execute and cleanup.sh --execute.

Exit codes
  0    every gate ran and passed (RESULT: PASS); only a default run can exit 0
  2    usage error
  3    precondition failure before any gate (repository root, python3)
  4    one or more gates failed (RESULT: FAIL lists them)
  5    all selected gates passed but some were skipped by --only/--skip (RESULT: PARTIAL): never
       a pass, so a partial run cannot be mistaken for one

Evidence produced
  STEP/PASS/FAIL lines and the summary table on stdout; per-gate logs under <CHECK_LOG_DIR>/<run-id>/.
EOF
}

SELECT_ONLY=""
SKIP_LIST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)
      SELECT_ONLY="${2:-}"
      [[ $# -ge 2 ]] || { sc_usage_exit "check.sh" "--only needs a value"; }
      shift 2
      ;;
    --skip)
      SKIP_LIST="${2:-}"
      [[ $# -ge 2 ]] || { sc_usage_exit "check.sh" "--skip needs a value"; }
      shift 2
      ;;
    --list-gates)
      echo "${ALL_GATES}"
      exit 0
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "check.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "check.sh"

_validate_gate_list() {
  local list="$1" g
  for g in ${list//,/ }; do
    case " ${ALL_GATES} " in
      *" ${g} "*) ;;
      *) sc_usage_error "unknown gate '${g}' (known: ${ALL_GATES})" ;;
    esac
  done
}
_validate_gate_list "${SELECT_ONLY}"
_validate_gate_list "${SKIP_LIST}"

if ! command -v python3 >/dev/null 2>&1; then
  sc_step "preflight"
  sc_refuse "${EX_REFUSED}" "python3 is required"
fi

LOG_DIR="${REPO_ROOT}/${CHECK_LOG_DIR}/${RUN_ID}"
mkdir -p "${LOG_DIR}"
sc_mktemp PYCACHE_DIR dir

sc_banner "real-run"
sc_info "logs: ${LOG_DIR}"

# ---------------------------------------------------------------------------------------------
# Gates. Each returns 0 on pass and 1 on fail; none exits the script.
# ---------------------------------------------------------------------------------------------

# _list_tracked_and_new GLOB...: NUL-separated existing files from git ls-files -co.
_list_tracked_and_new() {
  local f
  while IFS= read -r -d '' f; do
    if [[ -f "${f}" ]]; then
      printf '%s\0' "${f}"
    fi
  done < <(git -C "${REPO_ROOT}" ls-files -co --exclude-standard -z -- "$@")
}

gate_constitution() {
  local rc=0 f listing excludes ex skip
  for f in AGENTS.md CLAUDE.md docs/agents.md docs/agent-runs/README.md .claude/settings.json \
    .claude/ownership-audit.json .mcp.json; do
    if [[ -f "${f}" ]]; then
      sc_info "present: ${f}"
    else
      sc_err "constitution file missing: ${f}"
      rc=1
    fi
  done
  if compgen -G ".claude/agents/*.md" >/dev/null; then
    sc_info "present: .claude/agents/*.md"
  else
    sc_err "constitution file missing: .claude/agents/*.md"
    rc=1
  fi
  listing="${LOG_DIR}/json-files.nul"
  : >"${listing}"
  excludes="${JSON_FIXTURE_EXCLUDES:-}"
  while IFS= read -r -d '' f; do
    skip=0
    for ex in ${excludes}; do
      if [[ "${f}" == "${ex}"* ]]; then
        skip=1
      fi
    done
    if [[ "${skip}" -eq 0 ]]; then
      printf '%s\0' "${f}" >>"${listing}"
    fi
  done < <(_list_tracked_and_new '*.json')
  local count
  count="$(tr -cd '\0' <"${listing}" | wc -c | tr -d ' ')"
  if [[ "${count}" -gt 0 ]]; then
    if xargs -0 python3 -I "${SC_LIB_DIR}/tools.py" json-parse <"${listing}" >"${LOG_DIR}/json-parse.log" 2>&1; then
      sc_info "${count} JSON files parse"
    else
      sc_err "JSON parse failures:"
      head -n 20 "${LOG_DIR}/json-parse.log" | while IFS= read -r f; do sc_err "${f}"; done
      rc=1
    fi
  else
    sc_info "no JSON files to parse"
  fi
  return "${rc}"
}

# _syntax_and_lint LOGNAME FILE...: bash -n each file, then one shellcheck over all of them.
_syntax_and_lint() {
  local name="$1" rc=0 f
  shift
  if [[ $# -eq 0 ]]; then
    sc_err "no shell scripts found for ${name}"
    return 1
  fi
  for f in "$@"; do
    if ! sc_exec --timeout "${TIMEOUT_QUICK_SECONDS}" --log "${LOG_DIR}/${name}.log" -- bash -n "${f}"; then
      sc_err "bash -n failed: ${f}"
      rc=1
    fi
  done
  if ! command -v shellcheck >/dev/null 2>&1; then
    sc_err "shellcheck is not installed; it is required (no silent skip)"
    return 1
  fi
  if ! sc_exec --timeout "${TIMEOUT_SHELLCHECK_SECONDS}" --log "${LOG_DIR}/${name}.log" -- shellcheck -x -P SCRIPTDIR "$@"; then
    sc_err "shellcheck reported findings (see ${LOG_DIR}/${name}.log)"
    rc=1
  fi
  sc_info "${name}: $# scripts checked (bash -n + shellcheck)"
  return "${rc}"
}

gate_hooks() {
  local files=() f
  for f in .claude/hooks/*.sh; do
    if [[ -f "${f}" ]]; then
      files+=("${f}")
    fi
  done
  if [[ ${#files[@]} -eq 0 ]]; then
    sc_err "no hook scripts found in the Claude hooks directory"
    return 1
  fi
  _syntax_and_lint hooks "${files[@]}"
}

gate_shell() {
  local files=() f
  while IFS= read -r -d '' f; do
    files+=("${f}")
  done < <(_list_tracked_and_new '*.sh')
  if [[ ${#files[@]} -eq 0 ]]; then
    sc_err "no tracked or new *.sh files found"
    return 1
  fi
  _syntax_and_lint shell "${files[@]}"
}

gate_python() {
  local files=() f
  while IFS= read -r -d '' f; do
    files+=("${f}")
  done < <(_list_tracked_and_new 'scripts/*.py')
  if [[ ${#files[@]} -eq 0 ]]; then
    sc_warn "no scripts/**/*.py files found"
    return 0
  fi
  if ! sc_exec --timeout "${TIMEOUT_QUICK_SECONDS}" --log "${LOG_DIR}/python.log" -- \
    python3 -I -X "pycache_prefix=${PYCACHE_DIR}" -m py_compile "${files[@]}"; then
    sc_err "py_compile failed (see ${LOG_DIR}/python.log)"
    return 1
  fi
  sc_info "python: ${#files[@]} files compile"
}

# The real-Terraform proofs (R1 state binding, R1 route ownership) are pinned too: in a default full run these classes
# must EXECUTE (not be skipped for a missing provider directory). Dotted module.Class names, space separated.
REQUIRED_REAL_TERRAFORM_CLASSES="test_terraform_state_binding.RealStateBindingTests test_terraform_r1.RouteOwnershipTest"
FULL_RUN=0
if [[ -z "${SELECT_ONLY}" && -z "${SKIP_LIST}" ]]; then
  FULL_RUN=1
fi

# The REQUIRED script test suites are pinned here (not in the config file, not overridable from the
# environment): a default run always runs all four, an omitted suite fails the gate, and a suite that
# executes zero tests fails the gate. discover:<dir> = unittest discover; files:<dir> = one python3 -I
# process per test_*.py (the billing suites interfere with each other when loaded by one discover
# process; terraform_state_binding.py is excluded because it applies scratch Terraform state).
# tests/scripts holds the test-engineer's independent script tests (Subphase 13B); it is REQUIRED in a default full
# run (a missing directory, or one that executes no test, fails the gate). Until the test-engineer populates it, a
# PARTIAL run (--only/--skip, never a pass anyway) only warns about it: SUITE-PENDING.
REQUIRED_SUITES="discover:scripts/tests discover:scripts/phase12d-spike/tests files:scripts/billing/tests discover:tests/scripts"
PENDING_UNTIL_POPULATED="tests/scripts"
SUITE_OVERRIDE=0

# _suite_executed LOG: prints the number of tests EXECUTED from plain `python3 file.py` unittest output ("Ran N" minus
# the skips it reports), or 0. Used for the one-process-per-file suites; scripts/tests and the spike suite go through
# suite_run.py, which separates method-level skips from class-level skips exactly.
_suite_executed() {
  local log="$1" ran skipped
  ran="$(grep -E '^Ran [0-9]+ tests? in' "${log}" | tail -n 1 | sed -E 's/^Ran ([0-9]+) .*/\1/')"
  skipped="$(grep -E '^(OK|FAILED) \(.*skipped=[0-9]+' "${log}" | tail -n 1 | sed -E 's/.*skipped=([0-9]+).*/\1/')"
  printf '%s' "$((${ran:-0} - ${skipped:-0}))"
}

# _suite_field LOG KEY: value of KEY=<n> on the last SUITE-SUMMARY line suite_run.py printed (0 when absent).
_suite_field() {
  local value
  value="$(grep -E '^SUITE-SUMMARY ' "$1" | tail -n 1 | tr ' ' '\n' | sed -n "s/^$2=//p" | head -n 1)"
  printf '%s' "${value:-0}"
}

gate_script_tests() {
  local rc=0 suites="${REQUIRED_SUITES}" suite kind dir log ran f count suite_files require
  if [[ -n "${SC_TEST_ONLY_SCRIPT_TEST_SUITES:-}" ]]; then
    suites="${SC_TEST_ONLY_SCRIPT_TEST_SUITES}"
    SUITE_OVERRIDE=1
    echo "SUITES-OVERRIDE: test-only suite list in use (${suites}); this run can never end RESULT: PASS"
  fi
  for suite in ${suites}; do
    kind="${suite%%:*}"
    dir="${suite#*:}"
    if [[ ! -d "${REPO_ROOT}/${dir}" ]]; then
      if [[ "${dir}" == "${PENDING_UNTIL_POPULATED}" && "${FULL_RUN}" -eq 0 && "${SUITE_OVERRIDE}" -eq 0 ]]; then
        sc_warn "SUITE-PENDING: required suite ${dir} does not exist yet (the test-engineer populates it); a default full run FAILS until it does"
        continue
      fi
      sc_err "required test suite directory missing: ${dir}"
      rc=1
      continue
    fi
    case "${kind}" in
      discover)
        log="${LOG_DIR}/script-tests-${dir//\//_}.log"
        require=()
        if [[ "${dir}" == "scripts/tests" && "${SUITE_OVERRIDE}" -eq 0 ]]; then
          require=(--require-class "${REQUIRED_REAL_TERRAFORM_CLASSES// /,}")
          if [[ "${FULL_RUN}" -eq 1 ]]; then
            require+=(--enforce-required)
          fi
        fi
        if sc_exec --timeout "${TIMEOUT_SBT_CHECK_SECONDS}" --log "${log}" -- \
          python3 -I -X "pycache_prefix=${PYCACHE_DIR}" "${SC_LIB_DIR}/suite_run.py" --start-dir "${dir}" --pattern 'test_*.py' \
          ${require[@]+"${require[@]}"}; then
          count="$(_suite_field "${log}" executed)"
          if [[ "${count}" -gt 0 ]]; then
            ran="$(grep -E '^Ran [0-9]+ tests?' "${log}" | tail -n 1 || true)"
            sc_info "suite ${dir}: ${ran:-ran} (${count} executed, $(_suite_field "${log}" skipped_tests) skipped tests, $(_suite_field "${log}" skipped_classes) skipped classes) OK"
            grep -E '^SUITE-SKIPPED-CLASS ' "${log}" | while IFS= read -r f; do sc_warn "${f}"; done || true
            grep -E '^SUITE-REQUIRED .* status=' "${log}" | while IFS= read -r f; do
              case "${f}" in
                *"status=ok") sc_info "${f}" ;;
                *) sc_warn "required real-Terraform class did not run (not enforced in a partial run): ${f}" ;;
              esac
            done || true
          elif [[ "${dir}" == "${PENDING_UNTIL_POPULATED}" && "${FULL_RUN}" -eq 0 && "${SUITE_OVERRIDE}" -eq 0 ]]; then
            sc_warn "SUITE-PENDING: suite ${dir} executed no test yet (the test-engineer populates it); a default full run FAILS until it does"
          else
            sc_err "suite ${dir} executed zero tests: an empty suite is a failure"
            rc=1
          fi
        else
          if grep -q '^SUITE-REQUIRED-FAILED' "${log}"; then
            grep -E '^SUITE-REQUIRED' "${log}" | while IFS= read -r f; do sc_err "${f}"; done || true
            sc_err "suite ${dir}: a required real-Terraform test class was skipped or missing in a default full run (see ${log}); run the terraform gate first so the providers exist"
          else
            sc_err "suite failed: ${dir} (see ${log})"
          fi
          rc=1
        fi
        ;;
      files)
        suite_files=0
        for f in "${REPO_ROOT}/${dir}"/test_*.py; do
          [[ -f "${f}" ]] || continue
          suite_files=$((suite_files + 1))
          log="${LOG_DIR}/script-tests-${dir//\//_}-$(basename "${f}").log"
          if sc_exec --timeout "${TIMEOUT_SBT_CHECK_SECONDS}" --log "${log}" -- \
            python3 -I -X "pycache_prefix=${PYCACHE_DIR}" "${f}"; then
            count="$(_suite_executed "${log}")"
            if [[ "${count}" -gt 0 ]]; then
              sc_info "suite file ${dir}/$(basename "${f}"): ${count} executed OK"
            else
              sc_err "suite file ${dir}/$(basename "${f}") executed zero tests: an empty suite is a failure"
              rc=1
            fi
          else
            sc_err "suite file failed: ${dir}/$(basename "${f}") (see ${log})"
            rc=1
          fi
        done
        if [[ "${suite_files}" -eq 0 ]]; then
          sc_err "suite ${dir} holds no test_*.py file: an empty suite is a failure"
          rc=1
        fi
        ;;
      *)
        sc_err "unknown suite kind: ${suite}"
        rc=1
        ;;
    esac
  done
  return "${rc}"
}

gate_sbt() {
  local sbt="${SBT_BIN:-sbt}" log="${LOG_DIR}/sbt-check.log"
  if ! sc_try_jdk17; then
    sc_err "${SC_ERR_MSG}"
    return 1
  fi
  if ! command -v "${sbt}" >/dev/null 2>&1; then
    sc_err "sbt not found (${sbt}); install sbt or set SBT_BIN"
    return 1
  fi
  if ! sc_exec --timeout "${TIMEOUT_SBT_CHECK_SECONDS}" --log "${log}" -- "${sbt}" -batch check; then
    sc_err "sbt -batch check failed (see ${log})"
    return 1
  fi
  grep -E 'Passed: Total|Tests: succeeded|\[success\]' "${log}" | tail -n 4 | while IFS= read -r f; do sc_info "sbt: ${f}"; done || true
  return 0
}

gate_terraform() {
  local rc=0 root roots=() log="${LOG_DIR}/terraform.log"
  if ! sc_try_terraform; then
    sc_err "${SC_ERR_MSG}"
    return 1
  fi
  # Neutralize every ambient AWS credential source: validate and mock tests need none.
  local tfenv=(env -u AWS_PROFILE -u AWS_DEFAULT_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY
    -u AWS_SESSION_TOKEN AWS_EC2_METADATA_DISABLED=true AWS_CONFIG_FILE=/dev/null
    AWS_SHARED_CREDENTIALS_FILE=/dev/null TF_IN_AUTOMATION=1 TF_INPUT=0 CHECKPOINT_DISABLE=1)
  if ! sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --log "${log}" -- \
    "${tfenv[@]}" "${TF}" "-chdir=${TERRAFORM_ROOT}" fmt -check -recursive; then
    sc_err "terraform fmt -check -recursive failed"
    rc=1
  fi
  while IFS= read -r root; do
    roots+=("$(dirname "${root}")")
  done < <(find "${TERRAFORM_ROOT}" -name versions.tf -not -path '*/modules/*' -not -path '*/.terraform/*' | sort)
  if [[ ${#roots[@]} -eq 0 ]]; then
    sc_err "no Terraform roots found under ${TERRAFORM_ROOT}"
    return 1
  fi
  for root in "${roots[@]}"; do
    sc_info "terraform root: ${root}"
    if ! sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --log "${log}" -- \
      "${tfenv[@]}" "${TF}" "-chdir=${root}" init -backend=false -input=false -lockfile=readonly; then
      sc_err "init failed: ${root}"
      rc=1
      continue
    fi
    if ! sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --log "${log}" -- \
      "${tfenv[@]}" "${TF}" "-chdir=${root}" validate; then
      sc_err "validate failed: ${root}"
      rc=1
    fi
    if [[ -d "${root}/tests" ]]; then
      if ! sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --log "${log}" -- \
        "${tfenv[@]}" "${TF}" "-chdir=${root}" test; then
        sc_err "terraform test failed: ${root}"
        rc=1
      fi
    fi
  done
  grep -E '^Success!|[0-9]+ passed, [0-9]+ failed' "${log}" | while IFS= read -r f; do sc_info "terraform: ${f}"; done || true
  # -lockfile=readonly keeps init from rewriting tracked provider lock files; fail if one changed anyway.
  if ! git -C "${REPO_ROOT}" diff --quiet -- '*.terraform.lock.hcl'; then
    sc_err "a tracked .terraform.lock.hcl was modified during the terraform gate; review and restore it"
    rc=1
  fi
  sc_info "note: terraform init downloaded providers over the network (no AWS API call)"
  return "${rc}"
}

# ---------------------------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------------------------

_selected() {
  local g="$1"
  if [[ -n "${SELECT_ONLY}" ]]; then
    case ",${SELECT_ONLY}," in
      *",${g},"*) ;;
      *) return 1 ;;
    esac
  fi
  case ",${SKIP_LIST}," in
    *",${g},"*) return 1 ;;
  esac
  return 0
}

# Explicit dispatch (not "gate_${name}") so shellcheck can see every gate function is used.
_run_gate() {
  case "$1" in
    constitution) gate_constitution ;;
    hooks) gate_hooks ;;
    shell) gate_shell ;;
    python) gate_python ;;
    script-tests) gate_script_tests ;;
    sbt) gate_sbt ;;
    terraform) gate_terraform ;;
    *) return 1 ;;
  esac
}

SUMMARY=""
FAILED=""
SKIPPED=""
PASSED_COUNT=0
for gate in ${ALL_GATES}; do
  if ! _selected "${gate}"; then
    SKIPPED="${SKIPPED} ${gate}"
    SUMMARY="${SUMMARY}$(printf '  %-14s %-5s %s' "${gate}" SKIP -)"$'\n'
    continue
  fi
  sc_step "gate-${gate}"
  started="${SECONDS}"
  if _run_gate "${gate}"; then
    status=PASS
    PASSED_COUNT=$((PASSED_COUNT + 1))
  else
    status=FAIL
    FAILED="${FAILED} ${gate}"
  fi
  elapsed=$((SECONDS - started))
  printf 'GATE: %s %s (%ss)\n' "${gate}" "${status}" "${elapsed}"
  SUMMARY="${SUMMARY}$(printf '  %-14s %-5s %ss' "${gate}" "${status}" "${elapsed}")"$'\n'
done

if [[ "${SUITE_OVERRIDE}" -eq 1 ]]; then
  SKIPPED="${SKIPPED} custom-script-test-suites"
fi

sc_step "summary"
printf 'GATE SUMMARY\n  %-14s %-5s %s\n%s' "gate" "state" "time" "${SUMMARY}"
if [[ -n "${FAILED}" ]]; then
  sc_result FAIL "failed:${FAILED}${SKIPPED:+ skipped:${SKIPPED}}" "${EX_GATE}"
fi
if [[ -n "${SKIPPED}" ]]; then
  sc_warn "not a full pass: gates skipped:${SKIPPED}"
  sc_result PARTIAL "passed=${PASSED_COUNT} skipped:${SKIPPED}" "${EX_PARTIAL}"
fi
sc_result PASS "gates=${PASSED_COUNT}" "${EX_OK}"
