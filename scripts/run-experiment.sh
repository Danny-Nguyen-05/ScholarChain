#!/usr/bin/env bash
# Phase 13B experiment runner: executes ONLY a committed experiment manifest, through run-bounded-pipeline.sh.
# Dry run by default. Creates no infrastructure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/run-experiment.sh --manifest FILE --cluster-id J-ID [--approval FILE] [--prespend FILE] [--profile P]
                                 [--execute] [--help]

Purpose
  Run ONE experiment described by a manifest that is committed to git, on an EXISTING Terraform-created EMR
  cluster. The script validates the manifest, records the commit and limits, and delegates the whole pipeline
  (the six steps, the ceilings, the G6 guard, the approval and pre-spend gates, the YARN kill by tag) to
  scripts/run-bounded-pipeline.sh; it does not duplicate any step logic.

Manifest rules (refused before anything else, exit 3)
  * The file must be TRACKED by git and UNCHANGED against HEAD: an untracked, ignored, modified or staged-but-
    different file is refused, as is a path outside the repository.
  * It must be JSON of schema scholarchain.experiment-manifest.v1 with REQUIRED "budget" (max_usd,
    max_runtime_minutes, max_capacity, region) and "teardown" (mode auto-termination, max_idle_timeout_seconds)
    sections, a "pipeline" section and "metrics.locations". A missing, empty or invalid section is rejected;
    unknown keys are rejected. The schema is documented in scripts/lib/experiment.py and scripts/README.md.
  * budget.max_usd may not exceed EMR_MAX_RUN_USD (3), runtime and capacity may not exceed the pinned pipeline caps.
  * Bucket names embed the AWS account id, so a COMMITTED manifest holds only run-time tokens, never an account id:
      ${SCHOLARCHAIN_ARTIFACTS_BUCKET}  ${SCHOLARCHAIN_LOGS_BUCKET}  ${SCHOLARCHAIN_RAW_BUCKET}  ${SCHOLARCHAIN_REPORTS_BUCKET}
      (environment variables of the same names, each scholarchain-<env>-<12 digits>-<artifacts|logs|raw|reports>, all of one stack)
      ${SCHOLARCHAIN_RUN_PREFIX}  (environment variable of that name, ^run-[a-z0-9][a-z0-9-]{1,27}$)
    The script replaces the tokens in the string values BEFORE the schema check and hands the resolved values to the pipeline. An
    unknown token, an empty or unset variable for a token in use, a value of another shape, buckets of different stacks, or a raw
    12-digit account id in a committed string is refused (exit 3). The approval record still binds the COMMITTED file
    (APPROVED_MANIFEST_SHA256, the git-tracked bytes); the resolved values are bound by APPROVED_RUN_CONFIG_SHA256 of the pipeline.
    The sha256 of the resolved manifest and the substituted values (account shown as <acct>) go to experiment-record.json.

Inputs
  --manifest FILE     the committed manifest (real manifests live under experiments/, written in Phase 15)
  --cluster-id J-ID or SCHOLARCHAIN_EMR_CLUSTER_ID   the existing cluster (it is NOT in the manifest)
  --approval FILE     approval record (default RUN_APPROVAL_RECORD_PATH); --prespend FILE pre-spend receipt
  --profile P or AWS_PROFILE   for --execute
  Environment variable names: SCHOLARCHAIN_EMR_CLUSTER_ID, AWS_PROFILE, SCHOLARCHAIN_REPO_ROOT, the token variables above, and the test-only
  SCHOLARCHAIN_CONFIG_FILE / SCHOLARCHAIN_PRICING_FILE. Pinned settings come from scripts/config/*.conf.

Modes
  (default)   DRY RUN: validates the manifest, prints the private run record it would write and the complete
              dry run of run-bounded-pipeline.sh (every command; no aws, hadoop or spark command runs; nothing is written).
  --execute   human approval point 2 (plan Section 7.3): the SAME approval-record, pre-spend and G6 gates as
              run-bounded-pipeline.sh --execute. The record uses APPROVED_ACTION=run-experiment and adds
              APPROVED_MANIFEST_SHA256=<sha256 of the committed manifest> (sha256 of the file bytes) to the
              run-bounded-pipeline keys; the dry run prints every line to paste.

Human approval points (plan Section 7.3)
  2. --execute: an approval record naming the manifest, budget, region, capacity, maximum runtime and teardown,
     plus a pre-spend receipt. A reviewed dry run is not approval to execute.

Exit codes
  0    success, or the dry run completed
  2    usage error
  3    refused: manifest not committed or unchanged, invalid or incomplete, or any gate of run-bounded-pipeline.sh refused
  4    a verification gate failed (the pipeline's cluster check or a failed step)
  5    an underlying aws command failed
  124  timed out (the hard runtime cap fired)

Evidence produced
  STEP: markers, the pipeline output (each line prefixed "pipeline| ") and one RESULT: line. --execute writes,
  exclusively and git-ignored, EXPERIMENT_RUNS_DIR/<experiment>-<run>/: experiment-record.json (commit SHA,
  manifest sha256, resource limits, region, start time, metric locations) and experiment-result.json (end time,
  exit code). The pipeline's own run manifest lists the output locations.
EOF2
}

MANIFEST="" CLUSTER_ID="${SCHOLARCHAIN_EMR_CLUSTER_ID:-}" APPROVAL="" PRESPEND="" PROFILE="${AWS_PROFILE:-}" EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest | --cluster-id | --approval | --prespend | --profile)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "run-experiment.sh" "$1 needs a value"
      fi
      case "$1" in
        --manifest) MANIFEST="$2" ;;
        --cluster-id) CLUSTER_ID="$2" ;;
        --approval) APPROVAL="$2" ;;
        --prespend) PRESPEND="$2" ;;
        --profile) PROFILE="$2" ;;
      esac
      shift 2
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --dry-run)
      EXECUTE=0
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "run-experiment.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "run-experiment.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
sc_require_tool python3
sc_require_tool git
[[ -n "${MANIFEST}" ]] || sc_usage_error "missing required value: --manifest"
[[ -n "${CLUSTER_ID}" ]] || sc_usage_error "missing required value: --cluster-id (or SCHOLARCHAIN_EMR_CLUSTER_ID)"

# ---- the manifest must be committed: tracked, inside the repository and unchanged against HEAD -------------------
sc_step "manifest-committed"
[[ -f "${MANIFEST}" ]] || sc_refuse "${EX_REFUSED}" "manifest not found: ${MANIFEST}"
MANIFEST_ABS="$(sc_realpath "${MANIFEST}")"
case "${MANIFEST_ABS}" in
  "${REPO_ROOT}"/*) ;;
  *) sc_refuse "${EX_REFUSED}" "the manifest is outside the repository: only a committed manifest may be run" ;;
esac
MANIFEST_REL="${MANIFEST_ABS#"${REPO_ROOT}"/}"
if ! sc_git -C "${REPO_ROOT}" ls-files --error-unmatch -- "${MANIFEST_REL}" >/dev/null 2>&1; then
  sc_refuse "${EX_REFUSED}" "${MANIFEST_REL} is not tracked by git (untracked or ignored): commit it first"
fi
if ! sc_git -C "${REPO_ROOT}" diff --quiet HEAD -- "${MANIFEST_REL}" 2>/dev/null; then
  sc_refuse "${EX_REFUSED}" "${MANIFEST_REL} differs from HEAD (modified or staged): only a committed, unchanged manifest may be run"
fi
HEAD_BLOB_SHA="$(sc_git -C "${REPO_ROOT}" cat-file blob "HEAD:${MANIFEST_REL}" | { shasum -a 256 2>/dev/null || sha256sum; } | awk '{print $1}')"
MANIFEST_SHA="$(sc_sha256 "${MANIFEST_ABS}")"
[[ "${HEAD_BLOB_SHA}" == "${MANIFEST_SHA}" ]] || sc_refuse "${EX_REFUSED}" "${MANIFEST_REL} bytes differ from HEAD"
COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
sc_info "manifest ${MANIFEST_REL} is tracked and identical to HEAD ${COMMIT} (sha256 ${MANIFEST_SHA})"

# ---- run-time tokens: bucket names and the run prefix are resolved from the environment, never committed ----------
sc_step "manifest-tokens"
sc_mktemp RENDERED_FILE
RENDER_RC=0
RENDER_OUT="$(python3 -I "${SC_LIB_DIR}/experiment.py" render --manifest "${MANIFEST_ABS}" --out "${RENDERED_FILE}")" || RENDER_RC=$?
if [[ "${RENDER_RC}" -eq 4 ]]; then
  cp "${MANIFEST_ABS}" "${RENDERED_FILE}" # not valid JSON: the schema check below refuses it with its usual message
  RENDER_OUT="RENDERED-SHA256 ${MANIFEST_SHA}"
  RENDER_RC=0
fi
if [[ "${RENDER_RC}" -ne 0 ]]; then
  while IFS= read -r line; do sc_err "${line}"; done <<<"${RENDER_OUT}"
  sc_refuse "${EX_REFUSED}" "the manifest tokens cannot be resolved: $(printf '%s' "${RENDER_OUT}" | head -n 1)"
fi
RENDERED_SHA=""
SUBST_JSON="{}"
SUBST_ARGS=()
while IFS= read -r line; do
  case "${line}" in
    "ACCOUNT "*) sc_register_account "${line#ACCOUNT }" ;; # capture only: from here on the account is redacted everywhere
    "SUBST "*) SUBST_ARGS+=("${line#SUBST }") ;;
    "RENDERED-SHA256 "*) RENDERED_SHA="${line#RENDERED-SHA256 }" ;;
  esac
done <<<"${RENDER_OUT}"
if [[ "${#SUBST_ARGS[@]}" -gt 0 ]]; then
  SUBST_JSON="$(printf '%s\n' "${SUBST_ARGS[@]}" | python3 -I -c 'import json,sys; print(json.dumps(dict(l.rstrip("\n").split(" ", 1) for l in sys.stdin if l.strip()), sort_keys=True))')"
fi
for entry in "${SUBST_ARGS[@]+"${SUBST_ARGS[@]}"}"; do
  printf 'EXPERIMENT-TOKEN: %s\n' "$(sc_redact "${entry}")"
done
printf 'EXPERIMENT-MANIFEST-SHA256: committed=%s rendered=%s\n' "${MANIFEST_SHA}" "${RENDERED_SHA}"

# ---- schema, budget and teardown sections (of the RESOLVED manifest) -------------------------------------------------
sc_step "manifest-schema"
VALID_RC=0
VALID_OUT="$(python3 -I "${SC_LIB_DIR}/experiment.py" validate --manifest "${RENDERED_FILE}" --max-run-usd "${EMR_MAX_RUN_USD}" \
  --max-runtime-cap "${PIPELINE_MAX_RUNTIME_MINUTES}" --max-capacity-cap "${PIPELINE_MAX_CAPACITY}" \
  --max-idle-cap "${PIPELINE_MAX_IDLE_TIMEOUT_SECONDS}")" || VALID_RC=$?
if [[ "${VALID_RC}" -ne 0 ]]; then
  while IFS= read -r line; do sc_err "${line}"; done <<<"${VALID_OUT}"
  sc_refuse "${EX_REFUSED}" "the manifest is invalid or lacks a required budget or teardown section: $(printf '%s' "${VALID_OUT}" | head -n 1)"
fi
EXP_ID="$(python3 -I "${SC_LIB_DIR}/experiment.py" show --manifest "${RENDERED_FILE}" --what id)"
EXP_REGION="$(python3 -I "${SC_LIB_DIR}/experiment.py" show --manifest "${RENDERED_FILE}" --what region)"
sc_info "manifest ${EXP_ID} is valid: $(python3 -I "${SC_LIB_DIR}/experiment.py" show --manifest "${RENDERED_FILE}" --what limits)"
PIPE_RUN="${EXP_ID}-${RUN_ID}"
START_UTC="$(sc_now)"

sc_step "run-record"
printf 'EXPERIMENT-RECORD: experiment=%s commit=%s manifest=%s manifest_sha256=%s region=%s start_utc=%s\n' \
  "${EXP_ID}" "${COMMIT}" "${MANIFEST_REL}" "${MANIFEST_SHA}" "${EXP_REGION}" "${START_UTC}"
printf 'EXPERIMENT-LIMITS: %s\n' "$(python3 -I "${SC_LIB_DIR}/experiment.py" show --manifest "${RENDERED_FILE}" --what limits)"
while IFS= read -r loc; do
  printf 'EXPERIMENT-METRIC-LOCATION: %s\n' "$(sc_redact "${loc}")"
done < <(python3 -I "${SC_LIB_DIR}/experiment.py" show --manifest "${RENDERED_FILE}" --what metrics)
printf 'EXPERIMENT-APPROVAL-LINE: APPROVED_ACTION=run-experiment\n'
printf 'EXPERIMENT-APPROVAL-LINE: APPROVED_MANIFEST_SHA256=%s\n' "${MANIFEST_SHA}"
printf 'EXPERIMENT-APPROVAL-NOTE: Rendered manifest sha256: %s (a comment line, ignored by the parser; the resolved values are bound by APPROVED_RUN_CONFIG_SHA256)\n' "${RENDERED_SHA}"

REC_DIR="" REC_FILE=""
if [[ "${EXECUTE}" -eq 1 ]]; then
  RUNS_ABS="${REPO_ROOT}/${EXPERIMENT_RUNS_DIR}"
  sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${EXPERIMENT_RUNS_DIR}" --within "${RUNS_ABS}" --path "${RUNS_ABS}"
  REC_DIR="${RUNS_ABS}/${PIPE_RUN}"
  sc_require_ignored "${REC_DIR}"
  sc_safeio fresh-dir --root "${REPO_ROOT}" --within-name "${EXPERIMENT_RUNS_DIR}" --within "${RUNS_ABS}" --path "${REC_DIR}"
  REC_DIR="${SC_SAFEIO_OUT}"
  REC_FILE="${REC_DIR}/experiment-record.json"
  REC_OUT="$(python3 -I "${SC_LIB_DIR}/experiment.py" write-record --root "${REPO_ROOT}" --out "${REC_FILE}" --manifest "${MANIFEST_ABS}" \
    --manifest-sha256 "${MANIFEST_SHA}" --kind planned --commit "${COMMIT}" --at "${START_UTC}" --pipeline-run-id "${PIPE_RUN}" \
    --rendered-sha256 "${RENDERED_SHA}" --substitutions-json "${SUBST_JSON}")" ||
    sc_refuse "${EX_REFUSED}" "${REC_OUT}"
  sc_info "experiment record: ${REC_FILE#"${REPO_ROOT}"/}"
fi

# ---- delegate the pipeline (no step logic here) ---------------------------------------------------------------------
sc_step "delegate-pipeline"
PIPE_ARGS=()
while IFS= read -r flag && IFS= read -r value; do
  PIPE_ARGS+=("${flag}" "${value}")
done < <(python3 -I "${SC_LIB_DIR}/experiment.py" args --manifest "${RENDERED_FILE}")
PIPE_ARGS+=(--cluster-id "${CLUSTER_ID}" --run-id "${PIPE_RUN}" --delegated-from-experiment "${MANIFEST_SHA}")
[[ -z "${APPROVAL}" ]] || PIPE_ARGS+=(--approval "${APPROVAL}")
[[ -z "${PRESPEND}" ]] || PIPE_ARGS+=(--prespend "${PRESPEND}")
[[ -z "${PROFILE}" ]] || PIPE_ARGS+=(--profile "${PROFILE}")
[[ "${EXECUTE}" -eq 0 ]] || PIPE_ARGS+=(--execute)
sc_info "delegating to run-bounded-pipeline.sh (run id ${PIPE_RUN})"
PIPE_OUT=""
sc_mktemp PIPE_OUT
PIPE_RC=0
# The child gets its own redaction values file (it registers its own secrets and removes the file at exit).
env -u SC_REDACT_FILE bash "${SC_SCRIPTS_DIR}/run-bounded-pipeline.sh" "${PIPE_ARGS[@]}" >"${PIPE_OUT}" 2>&1 || PIPE_RC=$?
while IFS= read -r line; do
  printf 'pipeline| %s\n' "$(sc_redact "${line}")"
done <"${PIPE_OUT}"

if [[ "${EXECUTE}" -eq 1 ]]; then
  STATUS="PASS"
  [[ "${PIPE_RC}" -eq 0 ]] || STATUS="FAIL"
  python3 -I "${SC_LIB_DIR}/experiment.py" write-record --root "${REPO_ROOT}" --out "${REC_DIR}/experiment-result.json" --manifest "${MANIFEST_ABS}" \
    --manifest-sha256 "${MANIFEST_SHA}" --kind result --commit "${COMMIT}" --at "$(sc_now)" --started "${START_UTC}" --pipeline-run-id "${PIPE_RUN}" \
    --exit-code "${PIPE_RC}" --status "${STATUS}" --rendered-sha256 "${RENDERED_SHA}" --substitutions-json "${SUBST_JSON}" >/dev/null || sc_warn "the experiment result record could not be written"
fi
if [[ "${PIPE_RC}" -ne 0 ]]; then
  sc_step "pipeline-failed"
  if [[ "${PIPE_RC}" -eq "${EX_REFUSED}" || "${PIPE_RC}" -eq "${EX_USAGE}" ]]; then
    sc_result REFUSED "step=delegate-pipeline reason=run-bounded-pipeline.sh refused (exit ${PIPE_RC}; see the pipeline| lines)" "${PIPE_RC}"
  fi
  sc_result FAIL "step=delegate-pipeline reason=run-bounded-pipeline.sh exited ${PIPE_RC} (see the pipeline| lines)" "${PIPE_RC}"
fi
if [[ "${EXECUTE}" -eq 1 ]]; then
  sc_result PASS "experiment=${EXP_ID} run=${PIPE_RUN} commit=${COMMIT} record=${REC_FILE#"${REPO_ROOT}"/}" "${EX_OK}"
fi
sc_result DRY-RUN "experiment=${EXP_ID} manifest_sha256=${MANIFEST_SHA}; the delegated pipeline dry run ran no aws, hadoop or spark command and nothing was written" "${EX_OK}"
