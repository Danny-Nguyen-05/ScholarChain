#!/usr/bin/env bash
# Phase 13 Terraform planning with a provenance receipt. Dry run by default; never applies.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/plan.sh --env NAME [--region REGION] [--profile PROFILE] [--image-revision SHA]
                       [--source-commit SHA] [--plan-out FILE] [--receipt FILE] [--expect-new-state]
                       [--execute] [--help]

Purpose
  Plan the Terraform root for one environment and record a provenance receipt. NEVER applies.
  Dry run (default) prints the exact commands and runs none of them: no aws, no terraform
  init/plan/show, no file is written. With --execute it runs, each through scripts/lib/timeout.py:
    git archive <commit> infra/terraform | tar -x   into the PRIVATE run directory (see below)
    aws sts get-caller-identity --query Account --output text   (account hash; raw ID never printed)
    terraform -chdir=<materialized root> init -input=false -lockfile=readonly
    terraform -chdir=<materialized root> plan -input=false -var-file=<environments/NAME.tfvars>
        -var-file=<private vars> -var aws_region=<region> -var aws_profile=<profile>
        [-var image_revision=<sha>] -out=<plan file>
    terraform -chdir=<materialized root> show -json <plan file>      (raw JSON, private)
    terraform -chdir=<materialized root> show -no-color <plan file>  (COMPLETE plan text, private)

  Source (R3): the plan ALWAYS runs from a `git archive` of the commit (HEAD, or --source-commit), never from
  the work tree, so a Git-ignored override.tf or *_override.tf can never be loaded. The materialized tree is
  read-only; its sha256 (source_tree_sha256) is recorded in the receipt and deploy.sh re-materializes and
  compares it.

  State (R1): the root uses the LOCAL backend. The materialized copy is bound to the LIVE state file
  (TERRAFORM_STATE_FILE, default infra/terraform/terraform.tfstate) by a generated backend "local" override,
  so a plan never starts from a fresh, empty state. The state's lineage, serial and sha256 (nothing else) are
  recorded in the receipt; a missing state is refused unless --expect-new-state is given (a very first
  deployment); deploy.sh refuses to apply when the state is missing, has another lineage or has changed.

  It then checks the saved plan's own provider region, aws_account_id, environment, project and image_revision
  variables against the inputs (a mismatch exits 4) and writes the receipt (schema
  scholarchain.plan-receipt.v2): plan sha256, commit of the planned source, scripts commit, clean-tree flag,
  account sha256 (never the raw ID), region, environment, planned environment and project, image_revision,
  source_tree_sha256, state identity, terraform version, UTC time, add/change/destroy/replace counts, IAM and
  stateful-resource changes, and the COMPLETE list of resource actions. deploy.sh REQUIRES this receipt next to
  the plan and its sha256 in the approval record (APPROVED_RECEIPT_SHA256).

  Review path (nothing is truncated): the full plan text file path and its sha256 are printed as
  "PLAN-TEXT: <path> sha256=<hash>" (review it locally; it is private); every resource address and action is printed as PLAN-ACTION lines
  (address and action only: no attribute values, no variable values) and kept in the receipt.
  Finally it prints the approval-record lines for the human to review and paste into the Phase 14
  record; this script never writes that record.

Private outputs (R2)
  Every run creates a FRESH run directory <PLAN_DIR>/<run-id> (mkdir 0700; it must not exist) that holds the
  materialized source, the Terraform data directory and, by default, the outputs. An explicit --plan-out or
  --receipt may name another path inside <PLAN_DIR>, but every output (plan, .json, .txt, .log, receipt) must be:
  inside <PLAN_DIR>; reported ignored by `git check-ignore`; absent beforehand (a leftover file or a symlink at a
  derived name is refused, never followed or overwritten); distinct from the other outputs (aliases and nesting
  are refused). Files are opened with O_CREAT|O_EXCL|O_NOFOLLOW (never truncated) and are 0600 in 0700 directories.
  Set TF_PLUGIN_CACHE_DIR to avoid downloading the providers for every fresh run directory.

Options
  --env NAME            required; uses infra/terraform/environments/NAME.tfvars as committed at the source commit
  --region REGION       AWS region (or SCHOLARCHAIN_AWS_REGION); required; nothing is hardcoded
  --profile PROFILE     AWS profile (or AWS_PROFILE); required with --execute. The user's approved
                        profile is scholarchain-deployer-tf (human-owned; no default here)
  --image-revision SHA  optional 40-hex commit SHA passed as -var image_revision (runtime plan, rollback)
  --source-commit SHA   plan the Terraform source exactly as committed at SHA while running THESE scripts;
                        used by rollback.sh so an older tree need not contain the scripts. The receipt
                        records SHA as the commit. Default: HEAD. Together with --image-revision this is the
                        plan of an infrastructure rollback that KEEPS the running runtime (rollback.sh, S1)
  --plan-out FILE       plan file path; must lie inside <PLAN_DIR> (target/plans) and must not exist.
                        Default <PLAN_DIR>/<run-id>/<env>-<commit>.tfplan
  --receipt FILE        receipt path; same rules (default <plan file>.receipt.json)
  --expect-new-state    the live state file does not exist yet (the very first deployment): require that, record
                        it, and require the state to still be absent at apply. Without the flag a missing state
                        is refused (and with it an existing state is refused)
  --execute             run the commands above (human approval point 4)

Inputs (environment variable NAMES; values are never echoed)
  SCHOLARCHAIN_AWS_REGION    region (or --region)
  AWS_PROFILE                profile (or --profile)
  SCHOLARCHAIN_TF_PRIVATE_VARS  path of the ignored private tfvars file (account ID, AZs, trusted
                             principal, budget, notification address); required with --execute. Its
                             path and string values are redacted from all output, logs and traces
  TERRAFORM_BIN              terraform executable (default: terraform); must report exactly 1.13.5

Human approval points (plan Section 7.3)
  4. Any real plan: run --execute only with the user's approved profile and private variable file.
  The plan is a proposal: applying it needs approval point 1 (deploy.sh --execute) and the
  Phase 14 approval record. A reviewed plan is not approval to apply.

Exit codes
  0    dry run printed, or receipt written
  2    usage error
  3    refused: missing input or state, wrong Terraform version, output path outside, not ignored, existing or colliding
  4    gate failure: the saved plan's region, account, environment, project or image_revision does not match the inputs,
       or the state changed while planning
  5    a terraform or aws command failed
  124  a command timed out

Evidence produced
  <plan file>, <plan file>.json, <plan file>.txt, <plan file>.log (all private, git-ignored: never
  copy them into evidence) and the receipt JSON (checksums, counts, state identity and the action list only).
EOF
}

ENV_NAME=""
REGION="${SCHOLARCHAIN_AWS_REGION:-}"
PROFILE="${AWS_PROFILE:-}"
IMAGE_REVISION=""
SOURCE_COMMIT=""
PLAN_OUT=""
RECEIPT=""
EXPECT_NEW_STATE=0
EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env | --region | --profile | --image-revision | --source-commit | --plan-out | --receipt)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "plan.sh" "$1 needs a value"
      fi
      case "$1" in
        --env) ENV_NAME="$2" ;;
        --region) REGION="$2" ;;
        --profile) PROFILE="$2" ;;
        --image-revision) IMAGE_REVISION="$2" ;;
        --source-commit) SOURCE_COMMIT="$2" ;;
        --plan-out) PLAN_OUT="$2" ;;
        --receipt) RECEIPT="$2" ;;
      esac
      shift 2
      ;;
    --expect-new-state)
      EXPECT_NEW_STATE=1
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
      sc_usage_exit "plan.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "plan.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
[[ -n "${ENV_NAME}" ]] || sc_usage_error "--env NAME is required"
[[ "${ENV_NAME}" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || sc_usage_error "--env must match [a-z0-9][a-z0-9_-]*"
[[ -n "${REGION}" ]] || sc_usage_error "region required: --region or SCHOLARCHAIN_AWS_REGION"
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
if [[ -n "${IMAGE_REVISION}" && ! "${IMAGE_REVISION}" =~ ^[0-9a-f]{40}$ ]]; then
  sc_usage_error "--image-revision must be a 40-hex commit SHA"
fi
if [[ -n "${SOURCE_COMMIT}" && ! "${SOURCE_COMMIT}" =~ ^[0-9a-f]{40}$ ]]; then
  sc_usage_error "--source-commit must be a 40-hex commit SHA"
fi
PRIVATE_VARS="${!TF_PRIVATE_VARS_ENV:-}"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the approved AWS profile (--profile or AWS_PROFILE)"
  [[ -n "${PRIVATE_VARS}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the private variable file named by ${TF_PRIVATE_VARS_ENV}"
  [[ -f "${PRIVATE_VARS}" ]] || sc_refuse "${EX_REFUSED}" "the file named by ${TF_PRIVATE_VARS_ENV} does not exist"
else
  [[ -n "${PROFILE}" ]] || PROFILE="<profile>"
  [[ -n "${PRIVATE_VARS}" ]] || PRIVATE_VARS="<private-vars-file>"
fi

COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
SRC_COMMIT="${SOURCE_COMMIT:-${COMMIT}}"
if ! sc_git -C "${REPO_ROOT}" cat-file -e "${SRC_COMMIT}^{commit}" 2>/dev/null; then
  sc_refuse "${EX_REFUSED}" "source commit ${SRC_COMMIT} is not a commit in this repository"
fi
if ! sc_git -C "${REPO_ROOT}" cat-file -e "${SRC_COMMIT}:${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars" 2>/dev/null; then
  sc_refuse "${EX_REFUSED}" "environment file not found: ${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars does not exist at commit ${SRC_COMMIT}"
fi
sc_tree_state
CLEAN=true
if [[ "${SC_TREE_STATE}" != "clean" ]]; then
  CLEAN=false
  sc_warn "work tree is not clean (${SC_TREE_STATE}: ${SC_TREE_DETAIL}); the receipt records clean=false and deploy.sh will refuse it (the plan itself comes from the committed source, never the work tree)"
fi

# ---- output locations: inside PLAN_DIR, ignored, absent, distinct, private -----------------------
sc_step "output-paths"
RUN_DIR_PLANNED="${PLAN_DIR_ABS}/${RUN_ID}"
PLAN_FILE="${PLAN_OUT:-${RUN_DIR_PLANNED}/${ENV_NAME}-${SRC_COMMIT}.tfplan}"
case "${PLAN_FILE}" in
  /*) ;;
  *) PLAN_FILE="${REPO_ROOT}/${PLAN_FILE}" ;;
esac
RECEIPT="${RECEIPT:-${PLAN_FILE}.receipt.json}"
case "${RECEIPT}" in
  /*) ;;
  *) RECEIPT="${REPO_ROOT}/${RECEIPT}" ;;
esac
OUTPUT_ENTRIES=(
  --entry "--plan-out" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_FILE}"
  --entry "plan json export" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_FILE}.json"
  --entry "plan text export" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_FILE}.txt"
  --entry "plan log" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_FILE}.log"
  --entry "--receipt" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${RECEIPT}"
)
sc_check_outputs "${OUTPUT_ENTRIES[@]}"
PLAN_FILE="${SC_CHECKED[0]}"
PLAN_JSON="${SC_CHECKED[1]}"
PLAN_TXT="${SC_CHECKED[2]}"
PLAN_LOG="${SC_CHECKED[3]}"
RECEIPT="${SC_CHECKED[4]}"
for out_path in "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}" "${PLAN_LOG}" "${RECEIPT}" "${RUN_DIR_PLANNED}"; do
  sc_require_ignored "${out_path}"
done
sc_info "outputs stay inside ${PLAN_DIR} (ignored, absent beforehand, distinct, private): plan, .json, .txt, .log, receipt; run directory ${PLAN_DIR}/${RUN_ID}"

sc_step "terraform-version"
sc_require_terraform

# ---- Terraform source: ALWAYS a git archive of the commit, never the work tree -------------------
TF_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" TF_IN_AUTOMATION=1 TF_INPUT=0 CHECKPOINT_DISABLE=1)
STATE_BEFORE=""
STATE_MODE="exists"
if [[ "${EXPECT_NEW_STATE}" -eq 1 ]]; then
  STATE_MODE="absent"
fi
sc_step "materialize-source"
if [[ "${EXECUTE}" -eq 1 ]]; then
  sc_ensure_plan_dir
  sc_run_dir
  sc_materialize_source "${SRC_COMMIT}" "${SC_RUN_DIR}"
  TF_ROOT_DIR="${SC_TF_ROOT_DIR}"
  TF_DATA="${SC_TF_DATA_DIR}"
  sc_mktemp STATE_BEFORE
  sc_record_state "${STATE_BEFORE}" "${STATE_MODE}"
  # An explicit --plan-out below the plan directory gets its parent directories (0700) created here.
  sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${PLAN_DIR}" --within "${PLAN_DIR_ABS}" --path "$(dirname "${PLAN_FILE}")"
  sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${PLAN_DIR}" --within "${PLAN_DIR_ABS}" --path "$(dirname "${RECEIPT}")"
  sc_safeio create-new --root "${REPO_ROOT}" "${PLAN_LOG}"
  SOURCE_TREE_SHA="${SC_SRC_TREE_SHA256}"
else
  TF_ROOT_DIR="${RUN_DIR_PLANNED}/source/${SRC_COMMIT}/${TERRAFORM_ROOT}"
  TF_DATA="${RUN_DIR_PLANNED}/tfdata"
  SOURCE_TREE_SHA="<computed-at-execute>"
  sc_info "dry run: would extract ${TERRAFORM_ROOT} as committed at ${SRC_COMMIT} into ${PLAN_DIR}/${RUN_ID}/source/${SRC_COMMIT} (read-only), bind it to the live state ${TERRAFORM_STATE_FILE} and record the state's lineage, serial and sha256; nothing is read or written in a dry run"
fi
ENV_TFVARS="${TF_ROOT_DIR%"/${TERRAFORM_ROOT}"}/${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars"
TF_ENV+=("TF_DATA_DIR=${TF_DATA}")
INIT_ARGS=(init -input=false -lockfile=readonly)
VAR_ARGS=("-var-file=${ENV_TFVARS}" "-var-file=${PRIVATE_VARS}" "-var=aws_region=${REGION}" "-var=aws_profile=${PROFILE}")
if [[ -n "${IMAGE_REVISION}" ]]; then
  VAR_ARGS+=("-var=image_revision=${IMAGE_REVISION}")
fi
sc_info "env=${ENV_NAME} region=${REGION} source_commit=${SRC_COMMIT} scripts_commit=${COMMIT} clean=${CLEAN} plan=${PLAN_FILE}"
sc_mktemp ID_FILE

sc_step "account-identity"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- \
  "${TF_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Account --output text || RC=$?
ACCOUNT_HASH="<computed-at-execute>"
if [[ "${EXECUTE}" -eq 1 ]]; then
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${RC}")" "aws sts get-caller-identity failed (exit ${RC})"
  fi
  ACCOUNT_ID="$(tr -d '[:space:]' <"${ID_FILE}")"
  if [[ ! "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]]; then
    sc_fail "${EX_GATE}" "unexpected account identity output (not a 12-digit account ID)"
  fi
  sc_register_account "${ACCOUNT_ID}"
  ACCOUNT_HASH="$(sc_sha256_string "${ACCOUNT_ID}")"
  sc_info "account sha256=${ACCOUNT_HASH}"
fi

sc_step "terraform-init"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --log-existing "${PLAN_LOG}" --show always -- \
  "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" "${INIT_ARGS[@]}" || RC=$?
if [[ "${EXECUTE}" -eq 1 && "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "terraform init failed (exit ${RC})"
fi

sc_step "terraform-plan"
RC=0
# The plan text is NOT echoed: it is saved (see terraform-show-text) and reviewed from the file.
sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_PLAN_SECONDS}" --log-existing "${PLAN_LOG}" -- \
  "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" plan -input=false -lock-timeout=60s \
  "${VAR_ARGS[@]}" "-out=${PLAN_FILE}" || RC=$?
if [[ "${EXECUTE}" -eq 1 && "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "terraform plan failed (exit ${RC}); redacted log: ${PLAN_LOG}"
fi
if [[ "${EXECUTE}" -eq 1 ]]; then
  sc_private_file "${PLAN_FILE}"
  STATE_AFTER=""
  sc_mktemp STATE_AFTER
  sc_record_state "${STATE_AFTER}" "${STATE_MODE}"
  if ! cmp -s "${STATE_BEFORE}" "${STATE_AFTER}"; then
    sc_fail "${EX_GATE}" "the live state changed while planning (identity before and after differ); plan again"
  fi
fi

sc_step "terraform-show"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture-new "${PLAN_JSON}" -- \
  "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" show -json "${PLAN_FILE}" || RC=$?
if [[ "${EXECUTE}" -eq 1 && "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "terraform show -json failed (exit ${RC})"
fi

sc_step "terraform-show-text"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture-new "${PLAN_TXT}" -- \
  "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" show -no-color "${PLAN_FILE}" || RC=$?
if [[ "${EXECUTE}" -eq 1 && "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "terraform show -no-color failed (exit ${RC})"
fi

sc_step "plan-receipt"
if [[ "${EXECUTE}" -eq 0 ]]; then
  sc_info "dry run: would check the saved plan's region, account, environment, project and image_revision, print PLAN-TEXT (path and sha256 of ${PLAN_TXT#"${REPO_ROOT}"/}), print every PLAN-ACTION, and write the receipt ${RECEIPT#"${REPO_ROOT}"/}"
  sc_result DRY-RUN "no aws or terraform command was run and no file was written; re-run with --execute (approval point 4) to plan" "${EX_OK}"
fi
sc_private_file "${PLAN_JSON}" "${PLAN_TXT}" "${PLAN_LOG}"
TARGET_IMAGE_ARGS=(--no-image-revision)
if [[ -n "${IMAGE_REVISION}" ]]; then
  TARGET_IMAGE_ARGS=(--image-revision "${IMAGE_REVISION}")
fi
RC=0
python3 -I "${SC_LIB_DIR}/verify.py" plan-target --show-json "${PLAN_JSON}" --region "${REGION}" \
  --account-sha256 "${ACCOUNT_HASH}" --environment "${ENV_NAME}" --project "${NAME_PREFIX_PROJECT}" "${TARGET_IMAGE_ARGS[@]}" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "${EX_GATE}" "the saved plan does not target the expected region, account, environment, project and image revision"
fi
SUMMARY_ARGS=(--show-json "${PLAN_JSON}" --plan-file "${PLAN_FILE}" --out "${RECEIPT}" --commit "${SRC_COMMIT}"
  --scripts-commit "${COMMIT}" --clean "${CLEAN}" --region "${REGION}" --account-sha256 "${ACCOUNT_HASH}" --env "${ENV_NAME}"
  --terraform-version "${TF_VERSION}" --created-utc "$(sc_now)" --run-id "${RUN_ID}" --profile "${PROFILE}"
  --image-revision "${IMAGE_REVISION}" --env-tfvars "${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars" --text-file "${PLAN_TXT}"
  --private-vars-supplied --stateful-prefixes "${STATEFUL_TYPE_PREFIXES}" --iam-prefixes "${IAM_TYPE_PREFIXES}"
  --root "${REPO_ROOT}" --source-tree-sha256 "${SOURCE_TREE_SHA}" --state-json "${STATE_BEFORE}" --purpose deploy-plan)
RC=0
python3 -I "${SC_LIB_DIR}/plan_summary.py" "${SUMMARY_ARGS[@]}" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "$([[ "${RC}" -eq 4 ]] && echo "${EX_GATE}" || echo "${EX_CMDFAIL}")" "plan receipt failed (exit ${RC})"
fi
sc_private_file "${RECEIPT}"
PLAN_SHA="$(sc_sha256 "${PLAN_FILE}")"
TEXT_SHA="$(sc_sha256 "${PLAN_TXT}")"
RECEIPT_SHA="$(sc_sha256 "${RECEIPT}")"
sc_info "receipt: ${RECEIPT}"
echo "PLAN-FILE: ${PLAN_FILE}"
echo "PLAN-RECEIPT: ${RECEIPT} sha256=${RECEIPT_SHA}"
echo "PLAN-TEXT: ${PLAN_TXT} sha256=${TEXT_SHA} (the COMPLETE plan text for the exact saved plan; private, never share or commit it)"
echo "APPROVAL-RECORD-CANDIDATE (review, then the human writes the Phase 14 record; plan.sh never writes it):"
echo "APPROVED_PLAN_SHA256=${PLAN_SHA}"
echo "APPROVED_RECEIPT_SHA256=${RECEIPT_SHA}"
echo "APPROVED_COMMIT=${SRC_COMMIT}"
echo "APPROVED_ACCOUNT_SHA256=${ACCOUNT_HASH}"
echo "APPROVED_REGION=${REGION}"
echo "APPROVED_ENVIRONMENT=${ENV_NAME}"
echo "APPROVED_PRESPEND_SHA256=<sha256 of the human-written pre-spend receipt: shasum -a 256 <file>>"
echo "APPROVED_STAGE=<one of base-apply | runtime-apply (a push approval record names no plan: see scripts/README.md)>"
sc_result PASS "plan recorded, not applied; receipt=${RECEIPT} plan_sha256=${PLAN_SHA}" "${EX_OK}"
