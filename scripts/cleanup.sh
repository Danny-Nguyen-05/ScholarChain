#!/usr/bin/env bash
# Phase 13 cleanup: classify by policy, require deletion protection to be released first (a separately
# approved preparation step), list the actual destructive actions of a saved plan, and remove only after a
# human confirmation token bound to that exact plan. Dry run by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/cleanup.sh --env NAME [--region REGION] [--profile PROFILE] [--evidence-dir DIR]
                          [--prepare [--image-revision SHA]] [--confirm TOKEN --plan FILE] [--execute] [--help]

Purpose
  Tear down the Terraform-managed RUNTIME safely under a preservation policy. The saved plan is built
  with -target for teardown addresses only, its ACTUAL destructive actions are listed, and the human
  confirmation token is bound to that exact saved plan. Dry run is the default and is the only mode
  used in Phase 13.

Preservation policy (pinned in scripts/config/release.conf; not overridable from the environment)
  PRESERVED (never removed): Terraform state/backend (module.foundation: state bucket, lock table,
    budget); all S3 buckets and objects and their bucket-level configuration (datalake, evidence,
    artifacts); S3 Vectors; the KMS keys, aliases and key policies that keep preserved data readable;
    CloudWatch log groups needed for grading.
  TEARDOWN: ECS/ECR runtime, EMR, Neptune, DynamoDB, SQS, Step Functions and the network (NAT/EIP,
    endpoints, VPC and children), plus the runtime IAM roles/policies and alarms/dashboard that a
    targeted run pulls in as dependents.
  Anything else is UNLISTED. The saved plan is REFUSED when any delete or replace touches a preserved
  class, or when any delete is not in the teardown set.

Source and state
  Every Terraform command for the destroy root runs in a read-only copy of the committed HEAD source (git
  archive into a private run directory; an ignored override.tf can never load) that is bound to the LIVE
  local state file (TERRAFORM_STATE_FILE) by a generated backend "local" override.

Dry run (default): prints the read-only inventory commands (terraform state list for every root, and a
  tag-based "aws resourcegroupstaggingapi get-resources" inventory), the preserve list, the protection
  check, the preparation plan and the commands --execute would run; runs none of them (no aws, no
  terraform beyond the local version probe; no file is written).

Human approval point (plan Section 7.3): 3. --execute is an explicit human invocation after the
  listing; the confirmation token is the documented human confirmation.

Deletion protection and the preparation step (R5)
  Neptune (deletion_protection), the query load balancer (enable_deletion_protection), the DynamoDB tables
  (deletion_protection_enabled) and the ECR repositories (force_delete=false) block a teardown while
  protected. Before the destroy listing and before the confirmed run cleanup.sh reads the current state
  (terraform show -json, values never printed) and REFUSES the destructive sequence with a PREPARE-REQUIRED
  message while any teardown resource still has such a protection active (rules: CLEANUP_PROTECTION_RULES).
  The separately approved preparation step is:
    1. cleanup.sh --prepare [--image-revision SHA] --execute
       plans (normal plan, not destroy) with -var=cleanup_mode=true and -target for exactly the protected
       teardown resources, saves it with a receipt (purpose cleanup-prepare) and REFUSES it when it deletes or
       creates anything, updates anything outside the teardown set, or changes any attribute other than the
       protection and force flags (CLEANUP_PREPARE_ALLOWED_ATTRS). Pass the image revision that is currently
       deployed so no task definition changes. Nothing is applied.
    2. the human writes a NEW approval record (APPROVED_STAGE=cleanup-prepare) and a pre-spend receipt;
       scripts/deploy.sh --stage cleanup-prepare applies exactly that plan (re-checking the policy), then
    3. the listing below runs and now proceeds to the confirmation token.
  Dry run of --prepare prints these commands. cleanup_mode also switches S3 / S3 Vectors force_destroy, but
  those preserved resources are never targeted and the S3 prevent_destroy guards stay.

--execute (two invocations)
  1. LISTING (no --confirm): live STS account hash; inventories (before-inventory.txt); classify the
     destroy root's state; PROTECTION CHECK; terraform plan -destroy -target=<teardown addresses> -out=<run
     dir>/destroy-<env>.tfplan; terraform show -json and show -no-color of that saved plan (private files);
     check the policy; print every action as "DESTROY-ACTION: <verb> <address>" (never truncated),
     "DESTROY-PLAN-SHA256: ...", "DESTROY-PLAN-FILE: <path>" and "CONFIRM-TOKEN: <sha256>". It then REFUSES
     (exit 3): nothing is destroyed. A policy violation also refuses (step destroy-policy) and prints no
     usable token. CONFIRM-TOKEN = sha256 over: plan sha256, account sha256, region, environment and the
     sorted destructive action list (format in scripts/README.md).
  2. CONFIRMED (--confirm TOKEN --plan FILE): does NOT re-plan. The saved plan named by --plan (the
     DESTROY-PLAN-FILE of step 1) is copied once into a private temp directory, hashed, re-inspected with
     terraform show -json, re-checked against the policy and the protection check, and the token is
     recomputed from that copy plus the LIVE STS account hash. A changed plan, a changed action list,
     another account, region or environment all refuse (exit 3). Only then is that verified copy applied
     (its sha256 re-verified immediately before apply), then after-inventory.txt is written.

Private outputs (R2)
  Each run creates a FRESH run directory <PLAN_DIR>/<run-id> (0700) for the materialized source and every
  private plan output, and a fresh evidence directory <CLEANUP_EVIDENCE_DIR>/<run-id> (or --evidence-dir, which
  must lie inside <CLEANUP_EVIDENCE_DIR> and not exist). Every output must be absent beforehand (a leftover file
  or a symlink at a derived name is refused, never followed), inside its directory, git-ignored (plan outputs),
  and distinct from every other output; files are opened O_CREAT|O_EXCL|O_NOFOLLOW (never truncated), 0600.

Two passes: on the current stack the first destroy pass is expected to fail at aws_eip.nat
  DisassociateAddress (HTTP 403, carried item 24). Run the procedure again (a fresh listing and a
  new token) for the second pass. Do NOT widen IAM to make pass 1 succeed. S3 buckets and the S3
  Vectors resources carry literal prevent_destroy and are preserved by policy; bucket destruction
  needs a human-reviewed source change plus the phase gate and is never done by this script.

Options
  --env NAME           environment tfvars (infra/terraform/environments/NAME.tfvars at HEAD); required
  --region REGION      region (or SCHOLARCHAIN_AWS_REGION); required
  --profile PROFILE    profile (or AWS_PROFILE); required with --execute
  --evidence-dir DIR   evidence directory inside <CLEANUP_EVIDENCE_DIR> (default <CLEANUP_EVIDENCE_DIR>/<run-id>)
  --prepare            plan the deletion-protection preparation (see above) instead of the destroy listing
  --image-revision SHA with --prepare: the currently deployed image revision (40-hex), passed as -var image_revision
  --confirm TOKEN      token printed by the listing run
  --plan FILE          with --confirm: the DESTROY-PLAN-FILE printed by the listing run
  --execute            run the listing (no --confirm), the preparation plan (--prepare) or the confirmed removal

Inputs (environment variable NAMES): SCHOLARCHAIN_AWS_REGION, AWS_PROFILE,
  SCHOLARCHAIN_TF_PRIVATE_VARS (destroy plan; redacted everywhere), TERRAFORM_BIN, SCHOLARCHAIN_REPO_ROOT.

Exit codes
  0    dry run printed; or destroy pass completed; or the preparation plan was recorded (or none is needed)
  2    usage error
  3    refused: missing or wrong --confirm, policy violation, PREPARE-REQUIRED (protection active), missing input or
       state, wrong Terraform version, an output path that exists, escapes its directory or collides
  4    gate failure (before/after inventory could not be produced; the preparation plan targets the wrong stack)
  5    a terraform or aws command failed (RESULT: PARTIAL for an incomplete destroy pass)
  124  a command timed out

Evidence produced (deliverable D20)
  <evidence dir>/before-inventory.txt, after-inventory.txt (sorted target lists with the account ID
  redacted to <acct>), destroy-plan.sha256 and destroy-actions.txt (the sorted action list: addresses
  only). The saved plan, its JSON and its full text stay private in <PLAN_DIR>/<run-id> (git-ignored); raw
  command output is never written to the evidence directory.
EOF
}

ENV_NAME=""
REGION="${SCHOLARCHAIN_AWS_REGION:-}"
PROFILE="${AWS_PROFILE:-}"
EVIDENCE_DIR=""
CONFIRM=""
CONFIRM_PLAN=""
IMAGE_REVISION=""
PREPARE=0
EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env | --region | --profile | --evidence-dir | --confirm | --plan | --image-revision)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "cleanup.sh" "$1 needs a value"
      fi
      case "$1" in
        --env) ENV_NAME="$2" ;;
        --region) REGION="$2" ;;
        --profile) PROFILE="$2" ;;
        --evidence-dir) EVIDENCE_DIR="$2" ;;
        --confirm) CONFIRM="$2" ;;
        --plan) CONFIRM_PLAN="$2" ;;
        --image-revision) IMAGE_REVISION="$2" ;;
      esac
      shift 2
      ;;
    --prepare)
      PREPARE=1
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
      sc_usage_exit "cleanup.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "cleanup.sh"
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
if [[ "${PREPARE}" -eq 1 && ( -n "${CONFIRM}" || -n "${CONFIRM_PLAN}" ) ]]; then
  sc_usage_error "--prepare cannot be combined with --confirm or --plan"
fi
if [[ -n "${IMAGE_REVISION}" ]]; then
  [[ "${PREPARE}" -eq 1 ]] || sc_usage_error "--image-revision is only valid with --prepare"
  [[ "${IMAGE_REVISION}" =~ ^[0-9a-f]{40}$ ]] || sc_usage_error "--image-revision must be a 40-hex commit SHA"
fi
if [[ -n "${CONFIRM_PLAN}" && -z "${CONFIRM}" ]]; then
  sc_usage_error "--plan is only valid together with --confirm"
fi
if [[ "${EXECUTE}" -eq 1 && -n "${CONFIRM}" && -z "${CONFIRM_PLAN}" ]]; then
  sc_usage_error "--confirm needs --plan FILE (the DESTROY-PLAN-FILE printed by the listing run)"
fi
HEAD_COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
if ! sc_git -C "${REPO_ROOT}" cat-file -e "${HEAD_COMMIT}:${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars" 2>/dev/null; then
  sc_refuse "${EX_REFUSED}" "environment file not found: ${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars does not exist at HEAD"
fi
PRIVATE_VARS="${!TF_PRIVATE_VARS_ENV:-}"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the approved AWS profile (--profile or AWS_PROFILE)"
  [[ -n "${PRIVATE_VARS}" && -f "${PRIVATE_VARS}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the private variable file named by ${TF_PRIVATE_VARS_ENV}"
  sc_require_tool aws
else
  [[ -n "${PROFILE}" ]] || PROFILE="<profile>"
  [[ -n "${PRIVATE_VARS}" ]] || PRIVATE_VARS="<private-vars-file>"
fi
sc_require_tool python3
if [[ "${CLEANUP_DESTROY_ROOTS}" != "${TERRAFORM_ROOT}" ]]; then
  sc_refuse "${EX_REFUSED}" "CLEANUP_DESTROY_ROOTS must be exactly ${TERRAFORM_ROOT}: the destroy root runs from the materialized, state-bound source"
fi
DESTROY_ROOT="${TERRAFORM_ROOT}"
EVIDENCE_ABS="${REPO_ROOT}/${CLEANUP_EVIDENCE_DIR}"
EVIDENCE_DIR="${EVIDENCE_DIR:-${EVIDENCE_ABS}/${RUN_ID}}"
case "${EVIDENCE_DIR}" in
  /*) ;;
  *) EVIDENCE_DIR="${REPO_ROOT}/${EVIDENCE_DIR}" ;;
esac

sc_step "terraform-version"
sc_require_terraform

TF_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" AWS_PAGER= TF_IN_AUTOMATION=1 TF_INPUT=0 CHECKPOINT_DISABLE=1)
AWS_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" AWS_PAGER=)
RULE_ARGS=(--preserve-types "${CLEANUP_PRESERVE_TYPE_RULES}" --preserve-addresses "${CLEANUP_PRESERVE_ADDRESS_RULES}"
  --teardown-addresses "${CLEANUP_TEARDOWN_ADDRESS_RULES}")

# Inventory roots: every Terraform root outside modules/. Only the destroy root runs from the materialized source.
ROOTS=()
while IFS= read -r f; do
  ROOTS+=("$(dirname "${f}")")
done < <(find "${TERRAFORM_ROOT}" -name versions.tf -not -path '*/modules/*' -not -path '*/.terraform/*' | sort)
if [[ ${#ROOTS[@]} -eq 0 ]]; then
  sc_refuse "${EX_REFUSED}" "no Terraform roots found under ${TERRAFORM_ROOT}"
fi

sc_step "preserve-list"
for item in ${CLEANUP_PRESERVE//,/ }; do
  echo "PRESERVE: ${item}"
done
echo "PRESERVE-RULES types: ${CLEANUP_PRESERVE_TYPE_RULES}"
echo "PRESERVE-RULES addresses: ${CLEANUP_PRESERVE_ADDRESS_RULES}"
echo "TEARDOWN-RULES addresses: ${CLEANUP_TEARDOWN_ADDRESS_RULES}"
echo "PROTECTION-RULES: ${CLEANUP_PROTECTION_RULES}"

# ---- output locations: absent, confined, distinct, private -----------------------------------------
sc_step "output-paths"
RUN_DIR_PLANNED="${PLAN_DIR_ABS}/${RUN_ID}"
if [[ "${PREPARE}" -eq 1 ]]; then
  PLAN_FILE="${RUN_DIR_PLANNED}/prepare-${ENV_NAME}.tfplan"
else
  PLAN_FILE="${RUN_DIR_PLANNED}/destroy-${ENV_NAME}.tfplan"
fi
PLAN_JSON="${PLAN_FILE}.json"
PLAN_TXT="${PLAN_FILE}.txt"
PLAN_LOG="${PLAN_FILE}.log"
PLAN_RECEIPT="${PLAN_FILE}.receipt.json"
OUTPUT_ENTRIES=(
  --entry "evidence before-inventory" "${CLEANUP_EVIDENCE_DIR}" "${EVIDENCE_ABS}" "${EVIDENCE_DIR}/before-inventory.txt"
  --entry "evidence after-inventory" "${CLEANUP_EVIDENCE_DIR}" "${EVIDENCE_ABS}" "${EVIDENCE_DIR}/after-inventory.txt"
  --entry "evidence destroy-plan.sha256" "${CLEANUP_EVIDENCE_DIR}" "${EVIDENCE_ABS}" "${EVIDENCE_DIR}/destroy-plan.sha256"
  --entry "evidence destroy-actions.txt" "${CLEANUP_EVIDENCE_DIR}" "${EVIDENCE_ABS}" "${EVIDENCE_DIR}/destroy-actions.txt"
  --entry "plan file" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_FILE}"
  --entry "plan json export" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_JSON}"
  --entry "plan text export" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_TXT}"
  --entry "plan log" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_LOG}"
  --entry "plan receipt" "${PLAN_DIR}" "${PLAN_DIR_ABS}" "${PLAN_RECEIPT}"
)
# Evidence is shareable, plan outputs are private: the two pinned directories must not alias or nest.
case "${EVIDENCE_ABS}/" in
  "${PLAN_DIR_ABS}/"*) sc_refuse "${EX_REFUSED}" "the evidence directory ${CLEANUP_EVIDENCE_DIR} must be separate from the private plan directory ${PLAN_DIR} (it aliases or nests inside it)" ;;
esac
case "${PLAN_DIR_ABS}/" in
  "${EVIDENCE_ABS}/"*) sc_refuse "${EX_REFUSED}" "the evidence directory ${CLEANUP_EVIDENCE_DIR} must be separate from the private plan directory ${PLAN_DIR} (the plan directory nests inside it)" ;;
esac
sc_check_outputs "${OUTPUT_ENTRIES[@]}"
EVIDENCE_DIR="$(dirname "${SC_CHECKED[0]}")"
PLAN_FILE="${SC_CHECKED[4]}"
PLAN_JSON="${SC_CHECKED[5]}"
PLAN_TXT="${SC_CHECKED[6]}"
PLAN_LOG="${SC_CHECKED[7]}"
PLAN_RECEIPT="${SC_CHECKED[8]}"
for out_path in "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}" "${PLAN_LOG}" "${PLAN_RECEIPT}" "${RUN_DIR_PLANNED}"; do
  sc_require_ignored "${out_path}"
done
sc_info "plan outputs go to the fresh ${PLAN_DIR}/${RUN_ID} (ignored); evidence goes to ${EVIDENCE_DIR#"${REPO_ROOT}"/} (absent beforehand)"

# ---- Terraform source for the destroy root: materialized HEAD, bound to the live state ----------
DESTROY_ROOT_DIR="${RUN_DIR_PLANNED}/source/${HEAD_COMMIT}/${DESTROY_ROOT}"
TF_DATA="${RUN_DIR_PLANNED}/tfdata"
_env_tfvars() {
  printf '%s' "${DESTROY_ROOT_DIR%"/${DESTROY_ROOT}"}/${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars"
}
_root_dir() {
  if [[ "$1" == "${DESTROY_ROOT}" ]]; then
    printf '%s' "${DESTROY_ROOT_DIR}"
  else
    printf '%s' "${REPO_ROOT}/$1"
  fi
}
STATE_IDENT=""
# _source_ready: execute only. Fresh run directory, materialized HEAD, state identity, terraform init.
_source_ready() {
  local rc=0
  sc_step "source"
  sc_ensure_plan_dir
  sc_run_dir
  sc_materialize_source "${HEAD_COMMIT}" "${SC_RUN_DIR}"
  DESTROY_ROOT_DIR="${SC_TF_ROOT_DIR}"
  TF_DATA="${SC_TF_DATA_DIR}"
  sc_mktemp STATE_IDENT
  sc_record_state "${STATE_IDENT}" exists
  sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --show always -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" init -input=false -lockfile=readonly || rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${rc}")" "terraform init of the materialized source failed (exit ${rc}); nothing was changed"
  fi
}

# _evidence_dir_ready: creates the evidence directory (0700) inside CLEANUP_EVIDENCE_DIR once; call it from the
# main shell, never from a pipeline.
EVIDENCE_READY=0
_evidence_dir_ready() {
  if [[ "${EVIDENCE_READY}" -eq 0 ]]; then
    sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${CLEANUP_EVIDENCE_DIR}" --within "${EVIDENCE_ABS}" --path "${EVIDENCE_DIR}"
    EVIDENCE_READY=1
  fi
}

# _write_evidence NAME: stdin to a NEW file in the evidence directory (O_EXCL|O_NOFOLLOW, never overwritten).
# Safe in a pipeline: it only returns a status.
_write_evidence() {
  python3 -I "${SC_LIB_DIR}/safeio.py" write-new --root "${REPO_ROOT}" "${EVIDENCE_DIR}/$1" >/dev/null
}

# _inventory LABEL: writes the redacted <evidence>/<label>-inventory.txt (execute only) and keeps the
# raw state list of the destroy root in DESTROY_STATE_FILE. Called directly, never in a subshell.
INVENTORY_FILE=""
DESTROY_STATE_FILE=""
_inventory() {
  local label="$1" root state_out raw_state raw_tags rc line env_args=()
  INVENTORY_FILE="${EVIDENCE_DIR}/${label}-inventory.txt"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    _evidence_dir_ready
  fi
  # Raw command output goes to temp files; only redacted lists reach the evidence directory.
  sc_mktemp state_out
  sc_mktemp raw_state
  sc_mktemp raw_tags
  : >"${state_out}"
  for root in "${ROOTS[@]}"; do
    rc=0
    : >"${raw_state}"
    env_args=("${TF_ENV[@]}")
    if [[ "${root}" == "${DESTROY_ROOT}" ]]; then
      env_args+=("TF_DATA_DIR=${TF_DATA}")
    fi
    sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture "${raw_state}" -- \
      "${env_args[@]}" "${TF}" "-chdir=$(_root_dir "${root}")" state list || rc=$?
    if [[ "${EXECUTE}" -eq 1 ]]; then
      if [[ "${rc}" -ne 0 ]]; then
        if [[ "${root}" == "${DESTROY_ROOT}" ]]; then
          sc_fail "$(sc_rc_to_exit "${rc}")" "terraform state list failed for the destroy root ${root}"
        fi
        sc_warn "terraform state list failed for ${root}; treated as empty"
        : >"${raw_state}"
      fi
      if [[ "${root}" == "${DESTROY_ROOT}" ]]; then
        DESTROY_STATE_FILE="${state_out}.destroy-root"
        cp "${raw_state}" "${DESTROY_STATE_FILE}"
        SC_TMP_FILES+=("${DESTROY_STATE_FILE}")
      fi
      while IFS= read -r line; do
        if [[ -n "${line}" ]]; then
          printf 'tf:%s:%s\n' "${root}" "${line}" >>"${state_out}"
        fi
      done <"${raw_state}"
    fi
  done
  rc=0
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${raw_tags}" -- \
    "${AWS_ENV[@]}" aws resourcegroupstaggingapi get-resources --region "${REGION}" \
    --tag-filters "Key=${CLEANUP_TAG_KEY_PROJECT},Values=${NAME_PREFIX_PROJECT}" \
    "Key=${CLEANUP_TAG_KEY_ENVIRONMENT},Values=${NAME_PREFIX_ENVIRONMENT}" --output json || rc=$?
  if [[ "${EXECUTE}" -eq 1 ]]; then
    if [[ "${rc}" -ne 0 ]]; then
      sc_fail "$(sc_rc_to_exit "${rc}")" "tag-based inventory failed (exit ${rc})"
    fi
    python3 -I -c 'import json,sys
for item in json.load(open(sys.argv[1])).get("ResourceTagMappingList", []):
    print(item["ResourceARN"])' "${raw_tags}" >>"${state_out}" || sc_fail "${EX_GATE}" "cannot parse the tag-based inventory output"
    # The account ID never reaches evidence: redact, then sort the redacted list.
    sc_redact "$(cat "${state_out}")" | LC_ALL=C sort -u | _write_evidence "${label}-inventory.txt" ||
      sc_fail "${EX_GATE}" "cannot create the evidence file ${label}-inventory.txt (it must not exist)"
    sc_info "${label} inventory: $(wc -l <"${INVENTORY_FILE}" | tr -d ' ') entries"
  fi
}

# _show_saved_plan PLANFILE JSONOUT [TEXTOUT]: terraform show of the saved plan (JSON, and text when given);
# the outputs are created exclusively (never overwritten).
_show_saved_plan() {
  local planfile="$1" jsonout="$2" textout="${3:-}" rc=0
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture-new "${jsonout}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" show -json "${planfile}" || rc=$?
  if [[ "${EXECUTE}" -eq 1 && "${rc}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${rc}")" "terraform show -json of the saved plan failed (exit ${rc})"
  fi
  if [[ -n "${textout}" ]]; then
    rc=0
    sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture-new "${textout}" -- \
      "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" show -no-color "${planfile}" || rc=$?
    if [[ "${EXECUTE}" -eq 1 && "${rc}" -ne 0 ]]; then
      sc_fail "$(sc_rc_to_exit "${rc}")" "terraform show -no-color of the saved plan failed (exit ${rc})"
    fi
  fi
}

# _protection_check [TARGETS_OUT]: reads the CURRENT state (terraform show -json into a private temp file that
# is removed at exit; no value is printed) and finds teardown resources whose deletion protection is still
# active. Returns 0 when none is active, 1 when some are (the PROTECTION-ACTIVE lines are printed).
_protection_check() {
  local targets_out="${1:-}" state_json rc=0 out_rc=0 extra=()
  sc_mktemp state_json
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture "${state_json}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" show -json || rc=$?
  if [[ "${EXECUTE}" -eq 0 ]]; then
    return 0
  fi
  if [[ "${rc}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${rc}")" "terraform show -json of the current state failed (exit ${rc}); nothing was changed"
  fi
  if [[ -n "${targets_out}" ]]; then
    extra=(--targets-out "${targets_out}")
  fi
  sc_mktemp POLICY_OUT
  python3 -I "${SC_LIB_DIR}/verify.py" protection-state --state-json "${state_json}" --rules "${CLEANUP_PROTECTION_RULES}" \
    ${extra[@]+"${extra[@]}"} "${RULE_ARGS[@]}" >"${POLICY_OUT}" || out_rc=$?
  while IFS= read -r line; do
    printf '%s\n' "$(sc_redact "${line}")"
  done <"${POLICY_OUT}"
  if [[ "${out_rc}" -ge 2 ]]; then
    sc_fail "${EX_GATE}" "cannot read the protection state of the current stack"
  fi
  return "${out_rc}"
}

# _prepare_required: the destructive sequence is refused while any teardown resource is still protected.
_prepare_required() {
  sc_refuse "${EX_REFUSED}" "PREPARE-REQUIRED: deletion protection is still active on the teardown resources listed above; nothing was destroyed and no destroy plan or confirmation token is produced. Run 'scripts/cleanup.sh --prepare --execute' (add --image-revision <the deployed revision>), have the preparation plan approved through scripts/deploy.sh --stage cleanup-prepare, then run this listing again"
}

# ---- dry run -----------------------------------------------------------------------------------
if [[ "${EXECUTE}" -eq 0 && "${PREPARE}" -eq 0 ]]; then
  sc_step "source"
  sc_info "execute would extract ${TERRAFORM_ROOT} as committed at ${HEAD_COMMIT} into ${PLAN_DIR}/${RUN_ID}/source (read-only, bound to the live state ${TERRAFORM_STATE_FILE}) and run terraform init there; nothing is read or written in a dry run"
  sc_step "before-inventory"
  _inventory before
  sc_step "protection-check"
  sc_info "execute (1: listing) refuses with PREPARE-REQUIRED while a teardown resource still has deletion protection (CLEANUP_PROTECTION_RULES); the check reads the current state:"
  _protection_check
  sc_step "destroy-commands"
  sc_info "execute (1: listing, no --confirm) would classify the destroy root's state, then for the destroy root (${DESTROY_ROOT}):"
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_PLAN_SECONDS}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" plan -destroy -input=false -lock-timeout=60s \
    "-var-file=$(_env_tfvars)" "-var-file=${PRIVATE_VARS}" "-var=aws_region=${REGION}" "-var=aws_profile=${PROFILE}" \
    -var=cleanup_mode=true "-target=<each-teardown-address-from-the-classified-state-list>" "-out=${PLAN_FILE}"
  _show_saved_plan "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}"
  sc_info "dry run: would check the saved plan against the preservation policy, print every DESTROY-ACTION, DESTROY-PLAN-SHA256 and DESTROY-PLAN-FILE, then CONFIRM-TOKEN (binds plan sha256, account sha256, region, environment, sorted actions)"
  sc_info "execute (2: --confirm TOKEN --plan <DESTROY-PLAN-FILE>) would NOT re-plan: it verifies a private copy of that saved plan against the token and the live account, then applies the verified copy:"
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_APPLY_SECONDS}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" apply -input=false -lock-timeout=60s "<verified-private-copy-of-${PLAN_FILE##*/}>"
  sc_step "after-inventory"
  _inventory after
  sc_info "dry run: evidence would go to ${EVIDENCE_DIR#"${REPO_ROOT}"/} (before-inventory.txt, after-inventory.txt, destroy-plan.sha256, destroy-actions.txt)"
  sc_result DRY-RUN "no aws or terraform command was run and no file was written; --execute lists the destructive actions first, then needs --confirm <token> --plan <file>" "${EX_OK}"
fi

if [[ "${EXECUTE}" -eq 0 && "${PREPARE}" -eq 1 ]]; then
  sc_step "source"
  sc_info "execute would extract ${TERRAFORM_ROOT} as committed at ${HEAD_COMMIT} into ${PLAN_DIR}/${RUN_ID}/source (read-only, bound to the live state ${TERRAFORM_STATE_FILE}) and run terraform init there"
  sc_step "protection-check"
  sc_info "dry run: the preparation targets exactly the teardown resources whose protection is active in the current state:"
  _protection_check
  sc_step "prepare-plan"
  PREPARE_VARS=("-var-file=$(_env_tfvars)" "-var-file=${PRIVATE_VARS}" "-var=aws_region=${REGION}" "-var=aws_profile=${PROFILE}")
  if [[ -n "${IMAGE_REVISION}" ]]; then
    PREPARE_VARS+=("-var=image_revision=${IMAGE_REVISION}")
  fi
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_PLAN_SECONDS}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" plan -input=false -lock-timeout=60s \
    "${PREPARE_VARS[@]}" -var=cleanup_mode=true "-target=<each-protected-teardown-resource-found-by-the-protection-check>" "-out=${PLAN_FILE}"
  _show_saved_plan "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}"
  sc_info "dry run: would REFUSE the plan unless it only updates teardown resources in place and changes only the protection/force flags (${CLEANUP_PREPARE_ALLOWED_ATTRS}); it would then write the receipt ${PLAN_RECEIPT#"${REPO_ROOT}"/} and print the approval-record lines (APPROVED_STAGE=cleanup-prepare)"
  sc_info "then: scripts/deploy.sh --stage cleanup-prepare --plan <PLAN-FILE> --execute (approval record + pre-spend receipt), then the cleanup.sh listing"
  sc_result DRY-RUN "no aws or terraform command was run and no file was written; --prepare --execute plans the deletion-protection release (nothing is applied)" "${EX_OK}"
fi

# ---- execute: live identity first ----------------------------------------------------------------
sc_step "account-identity"
sc_mktemp ID_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- \
  "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Account --output text || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "aws sts get-caller-identity failed (exit ${RC}); nothing was destroyed"
fi
ACCOUNT_ID="$(tr -d '[:space:]' <"${ID_FILE}")"
if [[ ! "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]]; then
  sc_fail "${EX_GATE}" "unexpected account identity output (not a 12-digit account ID); nothing was destroyed"
fi
sc_register_account "${ACCOUNT_ID}"
ACCOUNT_HASH="$(sc_sha256_string "${ACCOUNT_ID}")"
sc_info "account sha256=${ACCOUNT_HASH}"

_source_ready

# ---- preparation plan (R5) -----------------------------------------------------------------------
if [[ "${PREPARE}" -eq 1 ]]; then
  sc_step "protection-check"
  sc_mktemp PREPARE_TARGETS
  PROTECTED=0
  _protection_check "${PREPARE_TARGETS}" || PROTECTED=$?
  if [[ "${PROTECTED}" -eq 0 ]]; then
    sc_result PASS "no teardown resource has active deletion protection; no preparation is needed; the listing can run" "${EX_OK}"
  fi
  PREPARE_TARGET_ARGS=()
  while IFS= read -r line; do
    if [[ -n "${line}" ]]; then
      PREPARE_TARGET_ARGS+=("-target=${line}")
      echo "PREPARE-TARGET: $(sc_redact "${line}")"
    fi
  done <"${PREPARE_TARGETS}"
  if [[ ${#PREPARE_TARGET_ARGS[@]} -eq 0 ]]; then
    sc_fail "${EX_GATE}" "protection is active but no target address was produced"
  fi

  sc_step "prepare-plan"
  sc_safeio create-new --root "${REPO_ROOT}" "${PLAN_LOG}"
  PREPARE_VARS=("-var-file=$(_env_tfvars)" "-var-file=${PRIVATE_VARS}" "-var=aws_region=${REGION}" "-var=aws_profile=${PROFILE}")
  if [[ -n "${IMAGE_REVISION}" ]]; then
    PREPARE_VARS+=("-var=image_revision=${IMAGE_REVISION}")
  fi
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_PLAN_SECONDS}" --log-existing "${PLAN_LOG}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" plan -input=false -lock-timeout=60s \
    "${PREPARE_VARS[@]}" -var=cleanup_mode=true "${PREPARE_TARGET_ARGS[@]}" "-out=${PLAN_FILE}" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${RC}")" "terraform plan failed for the preparation; nothing was changed (redacted log: ${PLAN_LOG})"
  fi
  sc_private_file "${PLAN_FILE}"
  _show_saved_plan "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}"
  sc_private_file "${PLAN_JSON}" "${PLAN_TXT}" "${PLAN_LOG}"

  sc_step "prepare-policy"
  sc_mktemp POLICY_OUT
  RC=0
  python3 -I "${SC_LIB_DIR}/verify.py" prepare-policy --show-json "${PLAN_JSON}" --allowed-attrs "${CLEANUP_PREPARE_ALLOWED_ATTRS}" \
    "${RULE_ARGS[@]}" >"${POLICY_OUT}" || RC=$?
  while IFS= read -r line; do
    printf '%s\n' "$(sc_redact "${line}")"
  done <"${POLICY_OUT}"
  if [[ "${RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "the preparation plan changes more than the protection flags of teardown resources (see POLICY-VIOLATION lines); it is not offered for approval and nothing was applied"
  fi

  sc_step "plan-receipt"
  PLAN_ARGS=(--no-image-revision)
  if [[ -n "${IMAGE_REVISION}" ]]; then
    PLAN_ARGS=(--image-revision "${IMAGE_REVISION}")
  fi
  RC=0
  python3 -I "${SC_LIB_DIR}/verify.py" plan-target --show-json "${PLAN_JSON}" --region "${REGION}" --account-sha256 "${ACCOUNT_HASH}" \
    --environment "${ENV_NAME}" --project "${NAME_PREFIX_PROJECT}" "${PLAN_ARGS[@]}" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "${EX_GATE}" "the preparation plan does not target the expected region, account, environment, project and image revision"
  fi
  sc_tree_state
  CLEAN=true
  if [[ "${SC_TREE_STATE}" != "clean" ]]; then
    CLEAN=false
    sc_warn "work tree is not clean (${SC_TREE_STATE}); the receipt records clean=false and deploy.sh will refuse it"
  fi
  RC=0
  python3 -I "${SC_LIB_DIR}/plan_summary.py" --show-json "${PLAN_JSON}" --plan-file "${PLAN_FILE}" --out "${PLAN_RECEIPT}" \
    --commit "${HEAD_COMMIT}" --scripts-commit "${HEAD_COMMIT}" --clean "${CLEAN}" --region "${REGION}" --account-sha256 "${ACCOUNT_HASH}" \
    --env "${ENV_NAME}" --terraform-version "${TF_VERSION}" --created-utc "$(sc_now)" --run-id "${RUN_ID}" --profile "${PROFILE}" \
    --image-revision "${IMAGE_REVISION}" --env-tfvars "${TERRAFORM_ENV_DIR}/${ENV_NAME}.tfvars" --text-file "${PLAN_TXT}" \
    --private-vars-supplied --stateful-prefixes "${STATEFUL_TYPE_PREFIXES}" --iam-prefixes "${IAM_TYPE_PREFIXES}" \
    --root "${REPO_ROOT}" --source-tree-sha256 "${SC_SRC_TREE_SHA256}" --state-json "${STATE_IDENT}" --purpose cleanup-prepare || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$([[ "${RC}" -eq 4 ]] && echo "${EX_GATE}" || echo "${EX_CMDFAIL}")" "preparation receipt failed (exit ${RC})"
  fi
  sc_private_file "${PLAN_RECEIPT}"
  PLAN_SHA="$(sc_sha256 "${PLAN_FILE}")"
  RECEIPT_SHA="$(sc_sha256 "${PLAN_RECEIPT}")"
  echo "PLAN-FILE: ${PLAN_FILE}"
  echo "PLAN-RECEIPT: ${PLAN_RECEIPT} sha256=${RECEIPT_SHA}"
  echo "PLAN-TEXT: ${PLAN_TXT} sha256=$(sc_sha256 "${PLAN_TXT}") (complete plan text; private, never share or commit it)"
  echo "APPROVAL-RECORD-CANDIDATE (review, then the human writes a NEW record; cleanup.sh never writes it):"
  echo "APPROVED_PLAN_SHA256=${PLAN_SHA}"
  echo "APPROVED_RECEIPT_SHA256=${RECEIPT_SHA}"
  echo "APPROVED_COMMIT=${HEAD_COMMIT}"
  echo "APPROVED_ACCOUNT_SHA256=${ACCOUNT_HASH}"
  echo "APPROVED_REGION=${REGION}"
  echo "APPROVED_ENVIRONMENT=${ENV_NAME}"
  echo "APPROVED_PRESPEND_SHA256=<sha256 of the human-written pre-spend receipt: shasum -a 256 <file>>"
  echo "APPROVED_STAGE=cleanup-prepare"
  sc_result PASS "preparation plan recorded, NOT applied; apply it with scripts/deploy.sh --stage cleanup-prepare after the approval record, then re-run the cleanup listing" "${EX_OK}"
fi

sc_step "before-inventory"
_inventory before

sc_mktemp ACTIONS_FILE
sc_mktemp POLICY_OUT

# _policy_check JSONFILE: prints every DESTROY-ACTION and enforces the preservation policy.
_policy_check() {
  local rc=0
  python3 -I "${SC_LIB_DIR}/verify.py" destroy-policy --show-json "$1" --actions-out "${ACTIONS_FILE}" "${RULE_ARGS[@]}" >"${POLICY_OUT}" || rc=$?
  while IFS= read -r line; do
    printf '%s\n' "$(sc_redact "${line}")"
  done <"${POLICY_OUT}"
  return "${rc}"
}

# _token PLANSHA: the confirmation token for the plan hash, the LIVE account, region, environment and actions.
_token() {
  python3 -I "${SC_LIB_DIR}/verify.py" destroy-token --plan-sha256 "$1" --account-sha256 "${ACCOUNT_HASH}" \
    --region "${REGION}" --environment "${ENV_NAME}" --actions-file "${ACTIONS_FILE}"
}

if [[ -z "${CONFIRM}" ]]; then
  # ---- listing: classify, protection check, plan with -target for teardown addresses only, list, refuse ---
  sc_step "classify-state"
  sc_mktemp TARGETS_FILE
  if [[ -z "${DESTROY_STATE_FILE}" || ! -f "${DESTROY_STATE_FILE}" ]]; then
    sc_fail "${EX_GATE}" "no state list for the destroy root"
  fi
  python3 -I "${SC_LIB_DIR}/verify.py" classify-state --state-file "${DESTROY_STATE_FILE}" --targets-out "${TARGETS_FILE}" "${RULE_ARGS[@]}" ||
    sc_fail "${EX_GATE}" "cannot classify the state list"
  TARGET_ARGS=()
  while IFS= read -r line; do
    if [[ -n "${line}" ]]; then
      TARGET_ARGS+=("-target=${line}")
      echo "TEARDOWN-TARGET: $(sc_redact "${line}")"
    fi
  done <"${TARGETS_FILE}"
  if [[ ${#TARGET_ARGS[@]} -eq 0 ]]; then
    _inventory after
    sc_result PASS "no teardown-class resource is in state; nothing to destroy; preserved resources were left untouched" "${EX_OK}"
  fi

  sc_step "protection-check"
  PROTECTED=0
  _protection_check || PROTECTED=$?
  if [[ "${PROTECTED}" -ne 0 ]]; then
    _prepare_required
  fi

  sc_step "destroy-plan"
  sc_safeio create-new --root "${REPO_ROOT}" "${PLAN_LOG}"
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_PLAN_SECONDS}" --log-existing "${PLAN_LOG}" -- \
    "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" plan -destroy -input=false -lock-timeout=60s \
    "-var-file=$(_env_tfvars)" "-var-file=${PRIVATE_VARS}" "-var=aws_region=${REGION}" "-var=aws_profile=${PROFILE}" \
    -var=cleanup_mode=true "${TARGET_ARGS[@]}" "-out=${PLAN_FILE}" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${RC}")" "terraform plan -destroy failed for ${DESTROY_ROOT}; nothing was destroyed (redacted log: ${PLAN_LOG})"
  fi
  sc_private_file "${PLAN_FILE}"
  _show_saved_plan "${PLAN_FILE}" "${PLAN_JSON}" "${PLAN_TXT}"
  sc_private_file "${PLAN_JSON}" "${PLAN_TXT}" "${PLAN_LOG}"
  DESTROY_SHA="$(sc_sha256 "${PLAN_FILE}")"
  printf '%s  %s\n' "${DESTROY_SHA}" "$(basename "${PLAN_FILE}")" | _write_evidence destroy-plan.sha256 ||
    sc_fail "${EX_GATE}" "cannot create the evidence file destroy-plan.sha256 (it must not exist)"
  printf 'DESTROY-PLAN-SHA256: %s\n' "${DESTROY_SHA}"
  echo "DESTROY-PLAN-FILE: ${PLAN_FILE}"
  echo "DESTROY-PLAN-TEXT: ${PLAN_TXT} sha256=$(sc_sha256 "${PLAN_TXT}") (complete plan text; private, never share or commit it)"

  sc_step "destroy-policy"
  RC=0
  _policy_check "${PLAN_JSON}" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "the saved destroy plan violates the preservation policy (see POLICY-VIOLATION lines); nothing was destroyed and no confirmation token is offered"
  fi
  _write_evidence destroy-actions.txt <"${ACTIONS_FILE}" || sc_fail "${EX_GATE}" "cannot create the evidence file destroy-actions.txt (it must not exist)"
  TOKEN="$(_token "${DESTROY_SHA}")"
  printf 'CONFIRM-BINDING: plan_sha256=%s account_sha256=%s region=%s environment=%s actions=%s\n' \
    "${DESTROY_SHA}" "${ACCOUNT_HASH}" "${REGION}" "${ENV_NAME}" "$(wc -l <"${ACTIONS_FILE}" | tr -d ' ')"
  printf 'CONFIRM-TOKEN: %s\n' "${TOKEN}"

  sc_step "confirm"
  sc_refuse "${EX_REFUSED}" "human confirmation required: review every DESTROY-ACTION above, then re-run with --confirm ${TOKEN} --plan ${PLAN_FILE}; nothing was destroyed"
fi

# ---- confirmed: verify the EXACT saved plan, the live account and the token, then apply that copy -
sc_step "verify-saved-plan"
case "${CONFIRM_PLAN}" in
  /*) ;;
  *) CONFIRM_PLAN="${REPO_ROOT}/${CONFIRM_PLAN}" ;;
esac
if ! python3 -I "${SC_LIB_DIR}/safeio.py" check-file --root "${REPO_ROOT}" --within-name "${PLAN_DIR}" --within "${PLAN_DIR_ABS}" "${CONFIRM_PLAN}" >"${ID_FILE}" 2>&1; then
  sc_refuse "${EX_REFUSED}" "no saved destroy plan at the given --plan path: $(cat "${ID_FILE}"); run the listing (without --confirm) first; nothing was destroyed"
fi
SAVED_PLAN="$(cat "${ID_FILE}")"
sc_verified_copy "${SAVED_PLAN}" VERIFIED_PLAN
DESTROY_SHA="$(sc_sha256 "${VERIFIED_PLAN}")"
VERIFIED_JSON="${SC_VERIFIED_DIR}/destroy.show.json"
_show_saved_plan "${VERIFIED_PLAN}" "${VERIFIED_JSON}"
RC=0
_policy_check "${VERIFIED_JSON}" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "the saved destroy plan violates the preservation policy; nothing was destroyed"
fi
TOKEN="$(_token "${DESTROY_SHA}")"
printf 'DESTROY-PLAN-SHA256: %s\n' "${DESTROY_SHA}"
if [[ "${CONFIRM}" != "${TOKEN}" ]]; then
  sc_refuse "${EX_REFUSED}" "--confirm token does not match the exact saved plan, the live account, region, environment and action list (the plan changed, the account differs, or the token was mistyped); nothing was destroyed"
fi
sc_info "confirmation token matches the exact saved plan, the live account hash, region, environment and action list"
sc_step "protection-check"
PROTECTED=0
_protection_check || PROTECTED=$?
if [[ "${PROTECTED}" -ne 0 ]]; then
  _prepare_required
fi
printf '%s  %s\n' "${DESTROY_SHA}" "$(basename "${SAVED_PLAN}")" | _write_evidence destroy-plan.sha256 ||
  sc_fail "${EX_GATE}" "cannot create the evidence file destroy-plan.sha256 (it must not exist)"
_write_evidence destroy-actions.txt <"${ACTIONS_FILE}" || sc_fail "${EX_GATE}" "cannot create the evidence file destroy-actions.txt (it must not exist)"
BEFORE_COUNT="$(wc -l <"${EVIDENCE_DIR}/before-inventory.txt" | tr -d ' ')"

sc_step "destroy-apply"
APPLY_FAILED=0
now_sha="$(sc_sha256 "${VERIFIED_PLAN}")"
if [[ "${now_sha}" != "${DESTROY_SHA}" ]]; then
  sc_refuse "${EX_REFUSED}" "the verified plan copy changed after verification; nothing was destroyed"
fi
rc=0
sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_APPLY_SECONDS}" --show always -- \
  "${TF_ENV[@]}" "TF_DATA_DIR=${TF_DATA}" "${TF}" "-chdir=${DESTROY_ROOT_DIR}" apply -input=false -lock-timeout=60s "${VERIFIED_PLAN}" || rc=$?
if [[ "${rc}" -ne 0 ]]; then
  APPLY_FAILED="${rc}"
  sc_warn "destroy apply failed for ${DESTROY_ROOT} (exit ${rc}); on pass 1 aws_eip.nat DisassociateAddress 403 is the expected carried item 24; do not widen IAM"
fi

sc_step "after-inventory"
_inventory after
AFTER_COUNT="$(wc -l <"${INVENTORY_FILE}" | tr -d ' ')"
sc_info "before=${BEFORE_COUNT} entries, after=${AFTER_COUNT} entries; files in ${EVIDENCE_DIR}"
if [[ "${APPLY_FAILED}" -ne 0 ]]; then
  sc_result PARTIAL "destroy pass incomplete (apply exit ${APPLY_FAILED}); run the listing again for the second pass; before=${BEFORE_COUNT} after=${AFTER_COUNT}" "${EX_CMDFAIL}"
fi
sc_result PASS "destroy pass complete; before=${BEFORE_COUNT} after=${AFTER_COUNT}; evidence=${EVIDENCE_DIR}" "${EX_OK}"
