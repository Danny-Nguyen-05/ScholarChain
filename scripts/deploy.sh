#!/usr/bin/env bash
# Phase 13 deployment gate: verifies the human approval record, the pre-spend receipt and the saved
# plan, then (only with --execute) performs ONE separately approved stage. Dry run only in Phase 13.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/deploy.sh --stage base-apply|push|runtime-apply|cleanup-prepare [--plan FILE] [--region REGION]
                         [--approval FILE] [--prespend FILE] [--manifest FILE] [--push-record FILE]
                         [--reuse-images DEPLOY_MANIFEST] [--image-revision SHA] [--source-commit SHA]
                         [--profile PROFILE] [--skip-runtime-archive] [--execute] [--help]

Purpose
  Verify the human approval record, the pre-spend receipt and (for the stages that apply a plan) the saved
  plan and its provenance, then (only with --execute) perform exactly ONE stage. Each Phase 14 step is a
  separate stage with its own approval record (APPROVED_STAGE) so none of them rides along with another. The
  recorded first-deployment order is: base apply, push, runtime plan, new approval, runtime apply.
    base-apply     apply ONLY: Terraform applies the verified plan with the runtime disabled (this is
                   what creates the ECR repositories), then the G5 runtime archive upload. No push.
    push           push ONLY: needs NO plan. Verify each local image tag against the release manifest (image ID
                   and OS/arch), push by commit SHA, verify the registry digest equals the pushed digest, then
                   write the private PUSH RECORD that runtime-apply requires. Refuses while an ECR
                   repository is missing (run base-apply first). No apply.
    runtime-apply  apply after push verification: the push record must name this commit, account, region,
                   environment and the four repositories, and every <repository>:<commit> must still resolve
                   to the recorded pushed digest BEFORE apply; then Terraform applies the verified runtime
                   plan, then all four ECS services and their ACTIVE task definitions are checked against the
                   expected image references; the deploy manifest is written only after that passes.
                   With --source-commit SHA (SHA != HEAD) it is the INFRASTRUCTURE ROLLBACK THAT KEEPS THE
                   RUNNING RUNTIME (S1): Terraform source SHA is applied while carrying the CURRENTLY DEPLOYED
                   image revision, which is bound to a verified previous deploy manifest (--reuse-images; it must
                   be the manifest of a runtime-apply, for this account, region and the four repositories) or to
                   a push record of that revision (--image-revision REV with --push-record), and whose registry
                   digests must equal the recorded ones BEFORE apply. The approval record is still
                   APPROVED_STAGE=runtime-apply, with APPROVED_COMMIT=SHA (the Terraform source) and the plan
                   and receipt hashes: the receipt's commit (SHA), scripts_commit (HEAD) and image_revision
                   (REV) bind it, so a record for a plain runtime-apply (commit HEAD) can never be used for it.
                   The bound state must show the DEPLOYED runtime (RUNTIME_LIVE_INDICATOR_TYPES: the four ECS
                   services, the query load balancer and target group; the ECS cluster and ECR repositories of a
                   base apply do not count, so on a post-base-apply state the carry would CREATE the runtime and
                   is refused), and a plan that deletes or replaces a protected resource is refused (STEP
                   runtime-preservation).
    cleanup-prepare apply ONLY the cleanup-preparation plan made by cleanup.sh --prepare (a plan with
                   -var=cleanup_mode=true): it is re-checked against the preparation policy (updates of
                   teardown resources, protection and force flags only) before anything is applied.
  Dry run is the default and the only mode used in Phase 13: it performs every LOCAL check, prints every
  command it would run, and runs none of them: no aws, no terraform init, show or apply, no docker, no registry
  login. The inspection of the verified plan (terraform show -json) is DEFERRED to --execute and printed.

Checks, in order (each prints "STEP: <name>"; the first failure refuses with a distinct exit code)
  terraform-version exactly 1.13.5
  clean-tree        refuse a dirty work tree. `git status --porcelain=v1 -z --untracked-files=all` is
                    parsed and compared: ONLY the literal configured approval-record path
                    (docs/agent-runs/phase-14/human-gate.md) is exempt, by exact string comparison. The
                    human writes the record after the plan; committing it would move HEAD away from
                    APPROVED_COMMIT. --approval adds no exemption (an alternate in-repo record path makes
                    the tree dirty unless it is git-ignored) and no environment variable can. A git
                    failure or unparsable output refuses
  approval-record   read the record (default: docs/agent-runs/phase-14/human-gate.md, or --approval).
                    Required lines, each EXACTLY once, KEY=value, no quotes:
                      APPROVED_STAGE=<base-apply|push|runtime-apply|cleanup-prepare>
                      APPROVED_COMMIT=<40 lowercase hex>   (the Terraform source commit being applied; HEAD for push)
                      APPROVED_ACCOUNT_SHA256=<64 lowercase hex>
                      APPROVED_REGION=<aws region>
                      APPROVED_ENVIRONMENT=<environment name, e.g. course>
                      APPROVED_PRESPEND_SHA256=<64 lowercase hex: sha256 of the pre-spend receipt>
                    and, for the stages that apply a plan (base-apply, runtime-apply, cleanup-prepare) only:
                      APPROVED_PLAN_SHA256=<64 lowercase hex>
                      APPROVED_RECEIPT_SHA256=<64 lowercase hex: sha256 of the plan receipt the human reviewed>
                    A push record names NO plan: a plan or receipt line in a push record is refused
  stage-match       --stage == APPROVED_STAGE
  commit-match      source commit (HEAD, or --source-commit) == APPROVED_COMMIT
  region-match      --region (or SCHOLARCHAIN_AWS_REGION) == APPROVED_REGION
  environment-match APPROVED_ENVIRONMENT == the environment the scripts operate on (NAME_PREFIX_ENVIRONMENT)
  prespend-receipt  the human-written pre-spend receipt (--prespend, default target/phase14/
                    prespend-receipt.json): sha256 == APPROVED_PRESPEND_SHA256; monitoring confirmed
                    active; cost snapshot at most PRESPEND_MAX_AGE_HOURS (24) old; reported spend,
                    unreported-usage allowance, reserves and remaining headroom all present and
                    numeric (missing is never zero); headroom at least PRESPEND_MIN_HEADROOM_USD (20).
                    Runs before ANY push, apply or upload and is RE-VERIFIED (hash, freshness, headroom,
                    monitoring) immediately before EACH paid operation: ECR login, every image push, every
                    terraform apply and the archive upload. A receipt that expired meanwhile stops the
                    stage at that operation (no further paid call)
  plan-checksum     (plan stages) the plan file is copied ONCE into a private (0700) directory; the copy's
                    sha256 must equal APPROVED_PLAN_SHA256; the copy is what is inspected and applied
  plan-provenance   (plan stages) the plan receipt (<plan>.receipt.json, REQUIRED) is copied once; its sha256
                    must equal APPROVED_RECEIPT_SHA256; it must tie the plan sha256 to a clean tree, the
                    approved source commit, HEAD (scripts commit), the approved account hash, region,
                    environment, planned environment and project, terraform version and image revision
  state-binding     (plan stages) the LIVE local state file (TERRAFORM_STATE_FILE) must exist, carry the receipt's
                    lineage, and still have the receipt's serial and sha256 (or still be absent when the plan
                    was made with --expect-new-state). Checked again immediately before every apply
  plan-inspect      (plan stages) deferred to --execute: the source commit is re-materialized from git
                    (git archive, bound to the live state) and its tree hash must equal the receipt's
                    source_tree_sha256; terraform init; terraform show -json <verified copy>: the plan's own
                    provider region, aws_account_id, environment, project and image_revision variables must
                    match the record. Mandatory before any execute-path mutation
  image-revision-binding  (runtime-apply with --reuse-images, --image-revision or --source-commit) the carried
                    revision: the previous deploy manifest must hold sha256 digests for all four services; for
                    an infrastructure rollback (--source-commit SHA) it must also be the manifest of a
                    runtime-apply, name this account and region and the four repositories, and record all four
                    ECS services; --image-revision REV must equal the manifest's revision
  runtime-preservation  (base-apply, and the infrastructure rollback that keeps the runtime) the live state
                    file is read locally (module path, type and instance count only). The runtime is LIVE only
                    when every RUNTIME_LIVE_INDICATOR_TYPES count is complete (four ECS services, the query load
                    balancer and target group, 0 or 1 listener); none of them is "not live" (the ECS cluster and
                    ECR repositories of a runtime-disabled base apply do not count); anything in between is a
                    PARTIAL runtime and is refused. While it is live, the receipt's action list (dry run included)
                    and, with --execute, the verified plan's own terraform show -json must delete or replace no
                    resource of a protected type (RUNTIME_LIVE_PROTECTED_TYPES: the indicator types plus the ECS
                    cluster); an infrastructure rollback that keeps the runtime also needs the state to show
                    it. Fail closed
  release-manifest  (push and runtime-apply) manifest commit == HEAD, not dirty, status complete, all
                    four images present with the configured architecture; with --reuse-images or an
                    --image-revision other than HEAD no image is built or pushed, so it is not used
  runtime-archive   (base-apply) G5 archive size and sha256 verified against the config pins on a private COPY
                    made once; that copy (not the original path) is what is uploaded
  push-record       (runtime-apply without --reuse-images) the push record for the deployed revision (HEAD, or
                    --image-revision), account, region, environment and the four repositories (default
                    <RELEASE_DIR>/<revision>/push-record.json)
  account-check     --execute only, BEFORE any mutating command: lowercase hex sha256 of the 12-digit
                    account ID (printf '%s' "$id" | shasum -a 256, no trailing newline) from
                    "aws sts get-caller-identity --query Account --output text" must equal
                    APPROVED_ACCOUNT_SHA256. The raw ID is never printed

Stage sequences (printed in dry run; run only with --execute, each through timeout.py)
  base-apply:     terraform-apply (pre-spend re-check, plan and state re-verified immediately before apply),
                  runtime-archive-upload (pre-spend re-check, the private copy re-hashed, aws s3 cp of THAT
                  copy with the copy's own sha256 as metadata, then size and sha256 verified against the copy),
                  write-deploy-manifest
  push:           ecr-repositories-exist, verify-local-images, ecr-login (pre-spend re-check), push-images
                  (pre-spend re-check before each push), record-digests, write-push-record, write-deploy-manifest
  runtime-apply:  ecr-repositories-exist, verify-registry-images (digest == the recorded pushed digest),
                  terraform-apply, record-ecs (aws ecs describe-services + describe-task-definition: all four
                  services must reference the bound revision, or its verified digest), write-deploy-manifest
  cleanup-prepare: terraform-apply, write-deploy-manifest
  The ECR repositories are created by Terraform, so push and runtime-apply refuse
  (ecr-repositories-exist) until a base-apply has created them.

Private run directory (R2)
  An execute run creates a FRESH directory <PLAN_DIR>/<run-id> (0700; never reused), holds the materialized
  source, the Terraform data directory, the verified copies and the archive copy there, and removes it at exit.
  The deploy manifest and the push record are created exclusively (O_EXCL | O_NOFOLLOW; never overwritten).

Options
  --stage STAGE         required: base-apply | push | runtime-apply | cleanup-prepare
  --plan FILE           the saved plan file approved by the record (required for the plan stages; refused with
                        --stage push, which has no plan; relative paths resolve from the repository root)
  --region REGION       region (or SCHOLARCHAIN_AWS_REGION); required
  --approval FILE       approval record override (read from here; adds NO dirty-tree exemption)
  --prespend FILE       pre-spend receipt override (see the schema in scripts/README.md)
  --manifest FILE       release manifest (default <RELEASE_DIR>/<HEAD>/release-manifest.json)
  --push-record FILE    push record to read (runtime-apply; default <RELEASE_DIR>/<HEAD>/push-record.json)
  --reuse-images FILE   previous deploy-manifest.json: redeploy its recorded image digests (rollback;
                        runtime-apply only; the digests come from that manifest, not from a push record)
  --image-revision SHA  runtime-apply only: the image revision the plan deploys when it is not HEAD, bound to the
                        push record (--push-record, default <RELEASE_DIR>/SHA/push-record.json). With
                        --reuse-images it must equal the manifest's revision
  --source-commit SHA   apply the Terraform source as committed at SHA (infrastructure rollback): with base-apply
                        (runtime disabled) or with runtime-apply plus --reuse-images or --image-revision (keeps
                        the running runtime); the same scripts run against it
  --profile PROFILE     AWS profile (or AWS_PROFILE); required with --execute (the human's approved profile)
  --skip-runtime-archive  base-apply: do not upload the G5 archive
  --execute             perform the stage (human approval point 1: the Phase 14 record)

Inputs (environment variable NAMES; values are never echoed)
  SCHOLARCHAIN_AWS_REGION, AWS_PROFILE, TERRAFORM_BIN, SCHOLARCHAIN_RUNTIME_ARCHIVE (local path),
  SCHOLARCHAIN_RUNTIME_ARCHIVE_S3_URI (destination; no default bucket), SCHOLARCHAIN_REPO_ROOT.

Human approval points (plan Section 7.3)
  1. --execute requires the Phase 14 approval record written by the human for exactly this stage,
     plan, commit, account and region, plus the pre-spend receipt it names. A reviewed plan is not
     approval to apply.
  4. The plan was made with the user's approved profile (plan.sh --execute).

Exit codes
  0    dry run completed with every local check passing (RESULT: DRY-RUN), or the stage completed (RESULT: PASS)
  2    usage error
  3    refused: dirty tree, approval record missing or malformed, any mismatch, stale, expired or missing
       pre-spend receipt, missing or edited plan receipt, plan target or source mismatch, missing, replaced or changed
       state, wrong account, missing manifest, push record or image, ECR repository missing, wrong Terraform version
  4    gate failure after approval (digest mismatch, upload verification failed, ECS verification failed)
  5    a command failed during the stage (RESULT: PARTIAL or FAIL names the step)
  124  a command timed out

Evidence produced
  STEP lines and the printed command list; with --execute,
  <RELEASE_DIR>/<HEAD>/deploy-manifest-<stage>-<run-id>.json (stage, commit, revision, plan sha256, region,
  account sha256, registry digests, task-definition ARNs) and, for --stage push,
  <RELEASE_DIR>/<HEAD>/push-record.json.
EOF
}

PLAN=""
REGION="${SCHOLARCHAIN_AWS_REGION:-}"
APPROVAL=""
PRESPEND=""
MANIFEST=""
PUSH_RECORD=""
REUSE=""
IMAGE_REVISION_OPT=""
SOURCE_COMMIT=""
STAGE=""
PROFILE="${AWS_PROFILE:-}"
SKIP_ARCHIVE=0
EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --plan | --region | --approval | --prespend | --manifest | --push-record | --reuse-images | --image-revision | --source-commit | --stage | --profile)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "deploy.sh" "$1 needs a value"
      fi
      case "$1" in
        --plan) PLAN="$2" ;;
        --region) REGION="$2" ;;
        --approval) APPROVAL="$2" ;;
        --prespend) PRESPEND="$2" ;;
        --manifest) MANIFEST="$2" ;;
        --push-record) PUSH_RECORD="$2" ;;
        --reuse-images) REUSE="$2" ;;
        --image-revision) IMAGE_REVISION_OPT="$2" ;;
        --source-commit) SOURCE_COMMIT="$2" ;;
        --stage) STAGE="$2" ;;
        --profile) PROFILE="$2" ;;
      esac
      shift 2
      ;;
    --skip-runtime-archive)
      SKIP_ARCHIVE=1
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
      sc_usage_exit "deploy.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "deploy.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
[[ -n "${REGION}" ]] || sc_usage_error "region required: --region or SCHOLARCHAIN_AWS_REGION"
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
case "${STAGE}" in
  base-apply | runtime-apply | cleanup-prepare)
    [[ -n "${PLAN}" ]] || sc_usage_error "--plan FILE is required for --stage ${STAGE}"
    ;;
  push)
    [[ -z "${PLAN}" ]] || sc_usage_error "--stage push has no plan: its approval record names no plan, so --plan is refused"
    ;;
  *) sc_usage_error "--stage must be base-apply, push, runtime-apply or cleanup-prepare (each Phase 14 step is separately approved)" ;;
esac
APPLIES_PLAN=1
[[ "${STAGE}" == "push" ]] && APPLIES_PLAN=0
if [[ -n "${REUSE}" && "${STAGE}" != "runtime-apply" ]]; then
  sc_usage_error "--reuse-images is only valid with --stage runtime-apply"
fi
if [[ -n "${PUSH_RECORD}" && "${STAGE}" != "runtime-apply" ]]; then
  sc_usage_error "--push-record is only valid with --stage runtime-apply"
fi
if [[ -n "${IMAGE_REVISION_OPT}" ]]; then
  [[ "${STAGE}" == "runtime-apply" ]] || sc_usage_error "--image-revision is only valid with --stage runtime-apply"
  [[ "${IMAGE_REVISION_OPT}" =~ ^[0-9a-f]{40}$ ]] || sc_usage_error "--image-revision must be a 40-hex commit SHA"
fi
if [[ -n "${SOURCE_COMMIT}" ]]; then
  [[ "${SOURCE_COMMIT}" =~ ^[0-9a-f]{40}$ ]] || sc_usage_error "--source-commit must be a 40-hex commit SHA"
fi
if [[ ! "${PRESPEND_MAX_AGE_HOURS}" =~ ^[0-9]+(\.[0-9]+)?$ || ! "${PRESPEND_MIN_HEADROOM_USD}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  sc_refuse "${EX_REFUSED}" "PRESPEND_MAX_AGE_HOURS and PRESPEND_MIN_HEADROOM_USD must be numeric in the config"
fi
APPROVAL="${APPROVAL:-${REPO_ROOT}/${APPROVAL_RECORD_PATH}}"
PRESPEND="${PRESPEND:-${REPO_ROOT}/${PRESPEND_RECEIPT_DEFAULT_PATH}}"
RELEASE_PREFIX="${REPO_ROOT}/${RELEASE_DIR}"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the approved AWS profile (--profile or AWS_PROFILE)"
  sc_require_tool aws
  if [[ "${STAGE}" == "push" ]]; then
    sc_require_tool docker
  fi
else
  [[ -n "${PROFILE}" ]] || PROFILE="<profile>"
fi
sc_require_tool git
sc_require_tool python3

sc_step "terraform-version"
sc_require_terraform

sc_step "clean-tree"
sc_tree_state
if [[ "${SC_TREE_STATE}" == "error" ]]; then
  sc_refuse "${EX_REFUSED}" "cannot determine whether the work tree is clean (${SC_TREE_DETAIL}); refusing"
fi
if [[ "${SC_TREE_STATE}" != "clean" ]]; then
  sc_refuse "${EX_REFUSED}" "work tree is dirty (${SC_TREE_DETAIL}); commit or stash everything (including untracked files) before deploying; only the literal ${APPROVAL_RECORD_PATH} is exempt"
fi
COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
SOURCE_COMMIT="${SOURCE_COMMIT:-${COMMIT}}"
# CARRY=1: an infrastructure rollback that keeps the running runtime (runtime-apply from another source commit).
CARRY=0
if [[ "${SOURCE_COMMIT}" != "${COMMIT}" ]]; then
  case "${STAGE}" in
    base-apply) ;;
    runtime-apply)
      if [[ -z "${REUSE}" && -z "${IMAGE_REVISION_OPT}" ]]; then
        sc_refuse "${EX_REFUSED}" "--source-commit with --stage runtime-apply needs the deployed image revision bound to a verified previous deploy manifest (--reuse-images) or to a push record (--image-revision with --push-record)"
      fi
      CARRY=1
      ;;
    *) sc_refuse "${EX_REFUSED}" "--source-commit is only valid with --stage base-apply (runtime disabled) or --stage runtime-apply (infrastructure rollback that keeps the runtime)" ;;
  esac
fi
sc_info "clean tree at ${COMMIT}"

# An execute run owns a FRESH private run directory (removed at exit); a dry run writes nothing there.
if [[ "${EXECUTE}" -eq 1 ]]; then
  sc_ensure_plan_dir
  sc_run_dir
  SC_RM_TREES+=("${SC_RUN_DIR}")
fi

sc_step "approval-record"
if [[ ! -f "${APPROVAL}" ]]; then
  sc_refuse "${EX_REFUSED}" "approval record not found: ${APPROVAL#"${REPO_ROOT}"/}"
fi
# _approval_value KEY PATTERN: sets APPROVAL_VALUE (called directly so refusals reach stdout).
APPROVAL_VALUE=""
_approval_value() {
  local key="$1" pattern="$2" count line
  count="$(grep -Ec "^[[:space:]]*${key}[[:space:]]*=" "${APPROVAL}" || true)"
  if [[ "${count}" -eq 0 ]]; then
    sc_refuse "${EX_REFUSED}" "approval record has no ${key} line"
  fi
  if [[ "${count}" -gt 1 ]]; then
    sc_refuse "${EX_REFUSED}" "approval record has ${count} ${key} lines; exactly one is required"
  fi
  line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "${APPROVAL}")"
  if [[ ! "${line}" =~ ^${key}=(.*)$ ]]; then
    sc_refuse "${EX_REFUSED}" "approval record line for ${key} must be exactly KEY=value with no spaces or quotes"
  fi
  APPROVAL_VALUE="${BASH_REMATCH[1]}"
  if [[ ! "${APPROVAL_VALUE}" =~ ${pattern} ]]; then
    sc_refuse "${EX_REFUSED}" "approval record value for ${key} is malformed"
  fi
}
# _approval_absent KEY: a push record names no plan.
_approval_absent() {
  if grep -Eq "^[[:space:]]*$1[[:space:]]*=" "${APPROVAL}"; then
    sc_refuse "${EX_REFUSED}" "the approval record for --stage push must not contain a $1 line: a push names no plan and no plan receipt"
  fi
}
_approval_value APPROVED_STAGE '^(base-apply|push|runtime-apply|cleanup-prepare)$'
APPROVED_STAGE="${APPROVAL_VALUE}"
# The stage decides which other lines are required, so it is compared first.
# An unknown APPROVED_* key (a misspelt or foreign key) refuses: other text in the record is ignored, extra keys are not.
UNKNOWN_KEY="$(grep -E '^[[:space:]]*APPROVED_[A-Za-z0-9_]*[[:space:]]*=' "${APPROVAL}" | sed -E 's/^[[:space:]]*(APPROVED_[A-Za-z0-9_]*).*/\1/' |
  grep -Ev '^(APPROVED_STAGE|APPROVED_COMMIT|APPROVED_ACCOUNT_SHA256|APPROVED_REGION|APPROVED_ENVIRONMENT|APPROVED_PRESPEND_SHA256|APPROVED_PLAN_SHA256|APPROVED_RECEIPT_SHA256)$' | head -n 1 || true)"
if [[ -n "${UNKNOWN_KEY}" ]]; then
  sc_refuse "${EX_REFUSED}" "approval record has an unknown key ${UNKNOWN_KEY}: any extra APPROVED_* key refuses"
fi
sc_step "stage-match"
if [[ "${STAGE}" != "${APPROVED_STAGE}" ]]; then
  sc_refuse "${EX_REFUSED}" "--stage ${STAGE} != APPROVED_STAGE ${APPROVED_STAGE}; each Phase 14 step needs its own approval record"
fi
sc_step "approval-record"
_approval_value APPROVED_COMMIT '^[0-9a-f]{40}$'
APPROVED_COMMIT="${APPROVAL_VALUE}"
_approval_value APPROVED_ACCOUNT_SHA256 '^[0-9a-f]{64}$'
APPROVED_ACCOUNT_SHA256="${APPROVAL_VALUE}"
_approval_value APPROVED_REGION '^[a-z]{2}(-[a-z0-9]+)+-[0-9]+$'
APPROVED_REGION="${APPROVAL_VALUE}"
_approval_value APPROVED_ENVIRONMENT '^[a-z0-9][a-z0-9_-]*$'
APPROVED_ENVIRONMENT="${APPROVAL_VALUE}"
_approval_value APPROVED_PRESPEND_SHA256 '^[0-9a-f]{64}$'
APPROVED_PRESPEND_SHA256="${APPROVAL_VALUE}"
APPROVED_PLAN_SHA256=""
APPROVED_RECEIPT_SHA256=""
if [[ "${APPLIES_PLAN}" -eq 1 ]]; then
  _approval_value APPROVED_PLAN_SHA256 '^[0-9a-f]{64}$'
  APPROVED_PLAN_SHA256="${APPROVAL_VALUE}"
  _approval_value APPROVED_RECEIPT_SHA256 '^[0-9a-f]{64}$'
  APPROVED_RECEIPT_SHA256="${APPROVAL_VALUE}"
  sc_info "approval record parsed (8 required lines, each exactly once)"
else
  _approval_absent APPROVED_PLAN_SHA256
  _approval_absent APPROVED_RECEIPT_SHA256
  sc_info "approval record parsed (6 required lines, each exactly once; no plan lines, as required for a push)"
fi

sc_step "commit-match"
if [[ "${SOURCE_COMMIT}" != "${APPROVED_COMMIT}" ]]; then
  sc_refuse "${EX_REFUSED}" "source commit ${SOURCE_COMMIT} != APPROVED_COMMIT ${APPROVED_COMMIT}"
fi

sc_step "region-match"
if [[ "${REGION}" != "${APPROVED_REGION}" ]]; then
  sc_refuse "${EX_REFUSED}" "region ${REGION} != APPROVED_REGION ${APPROVED_REGION}"
fi

sc_step "environment-match"
if [[ "${APPROVED_ENVIRONMENT}" != "${NAME_PREFIX_ENVIRONMENT}" ]]; then
  sc_refuse "${EX_REFUSED}" "APPROVED_ENVIRONMENT ${APPROVED_ENVIRONMENT} != the environment these scripts operate on (${NAME_PREFIX_ENVIRONMENT})"
fi

# ---- pre-spend gate: local, runs before any push, apply or upload, and again before EACH paid operation ---
sc_step "prespend-receipt"
if [[ ! -f "${PRESPEND}" ]]; then
  sc_refuse "${EX_REFUSED}" "pre-spend receipt not found: ${PRESPEND#"${REPO_ROOT}"/} (the human writes it; see scripts/README.md)"
fi
sc_verified_copy "${PRESPEND}" VERIFIED_PRESPEND
PRESPEND_SHA="$(sc_sha256 "${VERIFIED_PRESPEND}")"
if [[ "${PRESPEND_SHA}" != "${APPROVED_PRESPEND_SHA256}" ]]; then
  sc_refuse "${EX_REFUSED}" "pre-spend receipt sha256 ${PRESPEND_SHA} != APPROVED_PRESPEND_SHA256 ${APPROVED_PRESPEND_SHA256}"
fi

# _prespend_check LABEL: verifies the private copy (hash, monitoring, freshness, headroom, numeric fields) now.
# With the announced test-only SCHOLARCHAIN_CONFIG_FILE a controllable clock may supply the time for LABEL.
_prespend_check() {
  local label="$1" now rc=0 clock=()
  now="$(sc_sha256 "${VERIFIED_PRESPEND}")"
  if [[ "${now}" != "${APPROVED_PRESPEND_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "pre-spend receipt copy changed (sha256 ${now}) before ${label}; no further paid operation will run"
  fi
  if [[ -n "${SC_CLOCK_FILE}" ]]; then
    clock=(--clock-file "${SC_CLOCK_FILE}" --label "${label}")
  fi
  python3 -I "${SC_LIB_DIR}/verify.py" prespend --file "${VERIFIED_PRESPEND}" \
    --max-age-hours "${PRESPEND_MAX_AGE_HOURS}" --min-headroom "${PRESPEND_MIN_HEADROOM_USD}" ${clock[@]+"${clock[@]}"} || rc=$?
  [[ "${rc}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "pre-spend receipt rejected before ${label}: that paid operation and every later one is not run"
}
# _prespend_gate LABEL: the immediate pre-operation re-verification (execute only; a dry run prints it).
_prespend_gate() {
  if [[ "${EXECUTE}" -eq 0 ]]; then
    sc_info "dry run: the pre-spend receipt would be re-verified immediately before ${1}"
    return 0
  fi
  _prespend_check "$1"
  sc_info "pre-spend receipt re-verified before ${1}"
}
_prespend_check "initial"

NAME_PREFIX="$(sc_name_prefix)"
SERVICES=""
while read -r svc _main; do
  SERVICES="${SERVICES} ${svc}"
done < <(sc_service_list)
SERVICES="${SERVICES# }"
REPOSITORIES=""
for svc in ${SERVICES}; do
  REPOSITORIES="${REPOSITORIES} ${NAME_PREFIX}/${svc}"
done
REPOSITORIES="${REPOSITORIES# }"
IMAGE_REVISION="${COMMIT}"
PREV_DIGESTS=""
IMAGE_ARGS=(--image-revision "${COMMIT}")
if [[ "${STAGE}" == "base-apply" ]]; then
  IMAGE_ARGS=(--no-image-revision)
  IMAGE_REVISION=""
fi

# The carried revision (a rollback, or a revision other than HEAD) is bound BEFORE the receipt check: to the previous
# deploy manifest (--reuse-images) or, with --image-revision, to the push record of that revision (checked later at
# push-record, then every registry digest is compared with it before apply).
if [[ -n "${REUSE}" || -n "${IMAGE_REVISION_OPT}" ]]; then
  sc_step "image-revision-binding"
fi
if [[ -n "${IMAGE_REVISION_OPT}" ]]; then
  IMAGE_REVISION="${IMAGE_REVISION_OPT}"
  IMAGE_ARGS=(--image-revision "${IMAGE_REVISION}")
fi
if [[ -n "${REUSE}" ]]; then
  [[ -f "${REUSE}" ]] || sc_refuse "${EX_REFUSED}" "previous deploy manifest not found: ${REUSE}"
  BIND_ARGS=()
  if [[ "${CARRY}" -eq 1 ]]; then
    # The infrastructure rollback keeps a RUNNING runtime: the manifest must be bound to this deployment.
    BIND_ARGS=(--require-stage runtime-apply --account-sha256 "${APPROVED_ACCOUNT_SHA256}" --region "${REGION}" --repositories "${REPOSITORIES}" --require-ecs-services)
  fi
  RC=0
  python3 -I "${SC_LIB_DIR}/tools.py" verify-deploy-manifest --manifest "${REUSE}" --services "${SERVICES}" ${BIND_ARGS[@]+"${BIND_ARGS[@]}"} || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "previous deploy manifest failed verification"
  PREV_DIGESTS="$(python3 -I "${SC_LIB_DIR}/tools.py" digests --manifest "${REUSE}")"
  MANIFEST_REVISION="$(printf '%s\n' "${PREV_DIGESTS}" | sed -n 's/^IMAGE_REVISION //p')"
  if [[ -n "${IMAGE_REVISION_OPT}" && "${IMAGE_REVISION_OPT}" != "${MANIFEST_REVISION}" ]]; then
    sc_refuse "${EX_REFUSED}" "--image-revision ${IMAGE_REVISION_OPT} != the previous deploy manifest's image revision ${MANIFEST_REVISION}"
  fi
  IMAGE_REVISION="${MANIFEST_REVISION}"
  IMAGE_ARGS=(--image-revision "${IMAGE_REVISION}")
fi
if [[ "${CARRY}" -eq 1 ]]; then
  CARRY_BOUND="the push record of that revision (checked at push-record)"
  if [[ -n "${REUSE}" ]]; then
    CARRY_BOUND="the verified previous deploy manifest of a runtime-apply"
  fi
  sc_info "infrastructure rollback that KEEPS the runtime: Terraform source ${SOURCE_COMMIT} (scripts at ${COMMIT}) carries the deployed image revision ${IMAGE_REVISION}, bound to ${CARRY_BOUND}"
fi

VERIFIED_PLAN=""
PLAN_SHA="none"
TF_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" TF_IN_AUTOMATION=1 TF_INPUT=0 CHECKPOINT_DISABLE=1)
TF_ROOT_DIR=""
if [[ "${APPLIES_PLAN}" -eq 1 ]]; then
  # ---- saved plan: one private verified copy, receipt bound to the approval, state and source bindings ----
  sc_step "plan-checksum"
  if [[ ! -f "${PLAN}" ]]; then
    sc_refuse "${EX_REFUSED}" "plan file not found: ${PLAN}"
  fi
  PLAN="$(cd "$(dirname "${PLAN}")" && pwd -P)/$(basename "${PLAN}")"
  sc_verified_copy "${PLAN}" VERIFIED_PLAN
  PLAN_SHA="$(sc_sha256 "${VERIFIED_PLAN}")"
  if [[ "${PLAN_SHA}" != "${APPROVED_PLAN_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "plan sha256 ${PLAN_SHA} != APPROVED_PLAN_SHA256 ${APPROVED_PLAN_SHA256}"
  fi
  sc_info "plan sha256 matches the approval record (verified private copy; the copy is what is applied)"

  sc_step "plan-provenance"
  RECEIPT_FILE="${PLAN}.receipt.json"
  if [[ ! -f "${RECEIPT_FILE}" ]]; then
    sc_refuse "${EX_REFUSED}" "plan receipt not found next to the plan (${RECEIPT_FILE##*/}); it is REQUIRED: re-run plan.sh"
  fi
  sc_verified_copy "${RECEIPT_FILE}" VERIFIED_RECEIPT
  RECEIPT_SHA="$(sc_sha256 "${VERIFIED_RECEIPT}")"
  if [[ "${RECEIPT_SHA}" != "${APPROVED_RECEIPT_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "plan receipt sha256 ${RECEIPT_SHA} != APPROVED_RECEIPT_SHA256 ${APPROVED_RECEIPT_SHA256}; the receipt was changed after the human reviewed it, or it is another run's receipt"
  fi
  PURPOSE="deploy-plan"
  if [[ "${STAGE}" == "cleanup-prepare" ]]; then
    PURPOSE="cleanup-prepare"
    # The preparation plan keeps the revision currently deployed (so no task definition changes): it is the
    # receipt's own, and the saved plan's variable is compared with it below.
    RECEIPT_REVISION="$(python3 -I "${SC_LIB_DIR}/state_bind.py" receipt-field --receipt "${VERIFIED_RECEIPT}" --key image_revision || true)"
    IMAGE_REVISION="${RECEIPT_REVISION}"
    if [[ -n "${RECEIPT_REVISION}" ]]; then
      IMAGE_ARGS=(--image-revision "${RECEIPT_REVISION}")
    else
      IMAGE_ARGS=(--no-image-revision)
    fi
  fi
  RC=0
  python3 -I "${SC_LIB_DIR}/verify.py" plan-provenance --receipt "${VERIFIED_RECEIPT}" --plan-sha256 "${PLAN_SHA}" \
    --source-commit "${SOURCE_COMMIT}" --scripts-commit "${COMMIT}" --account-sha256 "${APPROVED_ACCOUNT_SHA256}" \
    --region "${REGION}" --environment "${NAME_PREFIX_ENVIRONMENT}" --project "${NAME_PREFIX_PROJECT}" --purpose "${PURPOSE}" \
    --terraform-version "${TF_VERSION}" "${IMAGE_ARGS[@]}" || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "plan receipt does not bind this plan to clean, approved provenance"

  # _check_state_binding: the live state file must still be the one the plan was made against.
  _check_state_binding() {
    local out rc=0
    out="$(python3 -I "${SC_LIB_DIR}/state_bind.py" check --state "${SC_STATE_ABS}" --receipt "${VERIFIED_RECEIPT}")" || rc=$?
    if [[ "${rc}" -ne 0 ]]; then
      sc_refuse "${EX_REFUSED}" "${out}"
    fi
    sc_info "${out}"
  }
  sc_step "state-binding"
  _check_state_binding

  sc_step "plan-inspect"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    sc_materialize_source "${SOURCE_COMMIT}" "${SC_RUN_DIR}"
    RC=0
    python3 -I "${SC_LIB_DIR}/state_bind.py" check-tree --receipt "${VERIFIED_RECEIPT}" --tree-sha256 "${SC_SRC_TREE_SHA256}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the source Terraform would load differs from the source the reviewed plan was made from"
    TF_ROOT_DIR="${SC_TF_ROOT_DIR}"
    TF_ENV+=("TF_DATA_DIR=${SC_TF_DATA_DIR}")
    RC=0
    sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --show always -- \
      "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" init -input=false -lockfile=readonly || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "terraform init of the materialized source failed (exit ${RC}); nothing was applied"
    SHOW_JSON="${SC_VERIFIED_DIR}/plan.show.json"
    RC=0
    sc_exec --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" --capture-new "${SHOW_JSON}" -- \
      "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" show -json "${VERIFIED_PLAN}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "terraform show -json of the verified plan copy failed (exit ${RC}); nothing was applied"
    RC=0
    python3 -I "${SC_LIB_DIR}/verify.py" plan-target --show-json "${SHOW_JSON}" --region "${REGION}" \
      --account-sha256 "${APPROVED_ACCOUNT_SHA256}" --environment "${NAME_PREFIX_ENVIRONMENT}" --project "${NAME_PREFIX_PROJECT}" "${IMAGE_ARGS[@]}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the saved plan targets a different region, account, environment, project or image revision than the approval record"
    if [[ "${STAGE}" == "cleanup-prepare" ]]; then
      RC=0
      python3 -I "${SC_LIB_DIR}/verify.py" prepare-policy --show-json "${SHOW_JSON}" --allowed-attrs "${CLEANUP_PREPARE_ALLOWED_ATTRS}" \
        --preserve-types "${CLEANUP_PRESERVE_TYPE_RULES}" --preserve-addresses "${CLEANUP_PRESERVE_ADDRESS_RULES}" \
        --teardown-addresses "${CLEANUP_TEARDOWN_ADDRESS_RULES}" || RC=$?
      [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the cleanup-preparation plan changes more than teardown resources' protection flags; nothing was applied"
    fi
  else
    TF_ROOT_DIR="${PLAN_DIR_ABS}/${RUN_ID}/source/${SOURCE_COMMIT}/${TERRAFORM_ROOT}"
    TF_ENV+=("TF_DATA_DIR=${PLAN_DIR_ABS}/${RUN_ID}/tfdata")
    sc_info "dry run: the inspection of the verified plan is DEFERRED to --execute (nothing beyond the version probe runs now); it will materialize ${SOURCE_COMMIT}, compare its tree hash with the receipt, then run:"
    sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" -- \
      "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" init -input=false -lockfile=readonly
    sc_exec --cloud --timeout "${TIMEOUT_TERRAFORM_LOCAL_SECONDS}" -- \
      "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" show -json "<verified-private-copy-of-${PLAN##*/}>"
    sc_info "dry run: its planned region, account hash, environment, project and image_revision must then match the approval record"
  fi
fi

# ---- S1 runtime preservation: an infrastructure rollback must keep a running runtime -------------------------
# base-apply (a plan with NO image revision) and the infrastructure rollback that keeps the runtime (CARRY) are the
# stages that could delete the live runtime. The live state file is read locally (module path, type, instance count).
# T1: "live" means DEPLOYED (the pinned indicator types: ECS services, query load balancer, target group, listener);
# the ECS cluster and ECR repositories of a runtime-disabled base apply do not make it live. A PARTIAL runtime refuses.
if [[ "${APPLIES_PLAN}" -eq 1 && ( "${STAGE}" == "base-apply" || "${CARRY}" -eq 1 ) ]]; then
  sc_step "runtime-preservation"
  EXPECT_RUNTIME=any
  if [[ "${CARRY}" -eq 1 ]]; then
    EXPECT_RUNTIME=live
  fi
  RC=0
  python3 -I "${SC_LIB_DIR}/verify.py" runtime-preservation --state "${SC_STATE_ABS}" --module "${RUNTIME_LIVE_MODULE:-}" \
    --indicators "${RUNTIME_LIVE_INDICATOR_TYPES:-}" --types "${RUNTIME_LIVE_PROTECTED_TYPES:-}" \
    --receipt "${VERIFIED_RECEIPT}" --expect "${EXPECT_RUNTIME}" || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the plan receipt shows this stage would not keep the live runtime (see RUNTIME-PRESERVATION-FAILED above); nothing was applied"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    RC=0
    python3 -I "${SC_LIB_DIR}/verify.py" runtime-preservation --state "${SC_STATE_ABS}" --module "${RUNTIME_LIVE_MODULE:-}" \
      --indicators "${RUNTIME_LIVE_INDICATOR_TYPES:-}" --types "${RUNTIME_LIVE_PROTECTED_TYPES:-}" \
      --show-json "${SHOW_JSON}" --expect "${EXPECT_RUNTIME}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the verified plan itself would not keep the live runtime (see RUNTIME-PRESERVATION-FAILED above); nothing was applied"
  else
    sc_info "dry run: the verified plan's own terraform show -json is checked the same way at --execute (deferred with the other inspection)"
  fi
fi

# _reverify_plan: the verified copy must still hash to the approved value immediately before apply.
_reverify_plan() {
  local now
  now="$(sc_sha256 "${VERIFIED_PLAN}")"
  if [[ "${now}" != "${APPROVED_PLAN_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "the verified plan copy changed after verification (sha256 ${now}); nothing was applied"
  fi
}

sc_step "release-manifest"
ECS_ARCH="$(sc_ecs_arch)" || sc_refuse "${EX_REFUSED}" "cannot read the ECS cpu_architecture from ${ECS_ARCH_SOURCE}"
if [[ "${ECS_ARCH}" != "${IMAGE_PLATFORM}" ]]; then
  sc_refuse "${EX_REFUSED}" "configured image platform ${IMAGE_PLATFORM} != ECS task architecture ${ECS_ARCH}"
fi
RELEASE_IMAGES=""
if [[ "${STAGE}" == "base-apply" || "${STAGE}" == "cleanup-prepare" ]]; then
  sc_info "${STAGE} pushes no image: the release manifest is not used"
elif [[ -n "${REUSE}" ]]; then
  sc_info "rollback mode: reusing images already in the registry for revision ${IMAGE_REVISION}; nothing will be pushed"
elif [[ "${IMAGE_REVISION}" != "${COMMIT}" ]]; then
  sc_info "carrying the already pushed revision ${IMAGE_REVISION} (not HEAD): nothing is built or pushed, so the release manifest is not used; the push record binds the revision"
else
  MANIFEST="${MANIFEST:-${RELEASE_PREFIX}/${COMMIT}/release-manifest.json}"
  [[ -f "${MANIFEST}" ]] || sc_refuse "${EX_REFUSED}" "release manifest not found: ${MANIFEST#"${REPO_ROOT}"/} (run scripts/package.sh first)"
  RC=0
  python3 -I "${SC_LIB_DIR}/tools.py" verify-release-manifest --manifest "${MANIFEST}" --head "${COMMIT}" \
    --platform "${IMAGE_PLATFORM}" --services "${SERVICES}" --ecs-arch "${ECS_ARCH}" || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "release manifest failed verification"
  RELEASE_IMAGES="$(python3 -I "${SC_LIB_DIR}/tools.py" release-images --manifest "${MANIFEST}")"
fi

sc_step "runtime-archive"
ARCHIVE_PATH=""
ARCHIVE_COPY=""
ARCHIVE_URI="${!RUNTIME_ARCHIVE_S3_URI_ENV:-}"
ARCHIVE_SIZE=""
ARCHIVE_SHA=""
if [[ "${STAGE}" != "base-apply" ]]; then
  sc_info "the runtime archive upload belongs to --stage base-apply only"
  SKIP_ARCHIVE=1
elif [[ "${SKIP_ARCHIVE}" -eq 1 ]]; then
  sc_info "runtime archive upload skipped by --skip-runtime-archive"
else
  if [[ -n "${SCHOLARCHAIN_RUNTIME_ARCHIVE:-}" ]]; then
    ARCHIVE_PATH="${SCHOLARCHAIN_RUNTIME_ARCHIVE}"
  elif [[ -f "${REPO_ROOT}/${RUNTIME_ARCHIVE_DEFAULT_PATH}" ]]; then
    ARCHIVE_PATH="${REPO_ROOT}/${RUNTIME_ARCHIVE_DEFAULT_PATH}"
  fi
  if [[ -z "${ARCHIVE_PATH}" || ! -f "${ARCHIVE_PATH}" ]]; then
    if [[ "${EXECUTE}" -eq 1 ]]; then
      sc_refuse "${EX_REFUSED}" "runtime archive not found (set SCHOLARCHAIN_RUNTIME_ARCHIVE or use --skip-runtime-archive)"
    fi
    sc_warn "runtime archive not found locally; --execute would be refused unless --skip-runtime-archive"
    ARCHIVE_COPY="<private-copy-of-the-runtime-archive>"
  else
    if [[ "${EXECUTE}" -eq 1 ]]; then
      # The archive is copied ONCE; size and sha256 are verified on the COPY, and only the copy is uploaded.
      sc_verified_copy "${ARCHIVE_PATH}" ARCHIVE_COPY
    else
      ARCHIVE_COPY="<private-copy-of-the-runtime-archive>"
    fi
    VERIFY_TARGET="${ARCHIVE_PATH}"
    VERIFIED_WHAT="in place (dry run: no copy is made)"
    if [[ "${EXECUTE}" -eq 1 ]]; then
      VERIFY_TARGET="${ARCHIVE_COPY}"
      VERIFIED_WHAT="on its private copy"
    fi
    ARCHIVE_SIZE="$(wc -c <"${VERIFY_TARGET}" | tr -d ' ')"
    ARCHIVE_SHA="$(sc_sha256 "${VERIFY_TARGET}")"
    if [[ "${ARCHIVE_SIZE}" != "${RUNTIME_ARCHIVE_EXPECTED_SIZE}" || "${ARCHIVE_SHA}" != "${RUNTIME_ARCHIVE_EXPECTED_SHA256}" ]]; then
      sc_refuse "${EX_REFUSED}" "runtime archive size/sha256 does not match the config pins (size ${ARCHIVE_SIZE}, sha256 ${ARCHIVE_SHA})"
    fi
    sc_info "runtime archive verified ${VERIFIED_WHAT}: size=${ARCHIVE_SIZE} sha256=${ARCHIVE_SHA}"
  fi
  if [[ -z "${ARCHIVE_URI}" ]]; then
    if [[ "${EXECUTE}" -eq 1 ]]; then
      sc_refuse "${EX_REFUSED}" "set ${RUNTIME_ARCHIVE_S3_URI_ENV} (s3://bucket/key) or use --skip-runtime-archive"
    fi
    sc_warn "${RUNTIME_ARCHIVE_S3_URI_ENV} is unset; --execute would be refused unless --skip-runtime-archive"
    ARCHIVE_URI="s3://<bucket>/<key>"
  elif [[ ! "${ARCHIVE_URI}" =~ ^s3://[^/]+/.+ ]]; then
    sc_refuse "${EX_REFUSED}" "${RUNTIME_ARCHIVE_S3_URI_ENV} must look like s3://bucket/key"
  fi
fi

# ---- push record: written by --stage push, required by runtime-apply ------------------------------------
PUSH_RECORD_DEFAULT="${RELEASE_PREFIX}/${IMAGE_REVISION:-${COMMIT}}/push-record.json"
PUSHED_DIGESTS=""
if [[ "${STAGE}" == "push" ]]; then
  sc_step "push-record-path"
  sc_check_outputs --entry "push record" "${RELEASE_DIR}" "${RELEASE_PREFIX}" "${PUSH_RECORD_DEFAULT}"
  PUSH_RECORD_DEFAULT="${SC_CHECKED[0]}"
  sc_info "the push record ${PUSH_RECORD_DEFAULT#"${REPO_ROOT}"/} does not exist yet and will be created exclusively after every digest is verified"
elif [[ "${STAGE}" == "runtime-apply" && -z "${REUSE}" ]]; then
  sc_step "push-record"
  PUSH_RECORD="${PUSH_RECORD:-${PUSH_RECORD_DEFAULT}}"
  if [[ ! -f "${PUSH_RECORD}" ]]; then
    sc_refuse "${EX_REFUSED}" "no push record for this commit (${PUSH_RECORD#"${REPO_ROOT}"/}; revision ${IMAGE_REVISION}): run the separately approved --stage push first; a registry tag that was not pushed and verified by this procedure is not accepted"
  fi
  sc_verified_copy "${PUSH_RECORD}" VERIFIED_PUSH_RECORD
  RC=0
  PUSHED_DIGESTS="$(python3 -I "${SC_LIB_DIR}/records.py" check-push-record --file "${VERIFIED_PUSH_RECORD}" --commit "${IMAGE_REVISION}" \
    --account-sha256 "${APPROVED_ACCOUNT_SHA256}" --region "${REGION}" --environment "${NAME_PREFIX_ENVIRONMENT}" \
    --repositories "${REPOSITORIES}" --services "${SERVICES}")" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "${PUSHED_DIGESTS}"
  fi
  sc_info "push record names revision ${IMAGE_REVISION}, this account, region, environment and the four repositories"
fi

# ---- account check: execute only, before any mutating command ---------------------------------
sc_step "account-check"
AWS_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" AWS_PAGER=)
sc_mktemp ID_FILE
sc_mktemp WORK_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- \
  "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Account --output text || RC=$?
ACCOUNT_ID="<acct>"
if [[ "${EXECUTE}" -eq 1 ]]; then
  if [[ "${RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "aws sts get-caller-identity failed (exit ${RC}); no mutating command was run"
  fi
  ACCOUNT_ID="$(tr -d '[:space:]' <"${ID_FILE}")"
  sc_register_account "${ACCOUNT_ID}"
  if [[ ! "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]]; then
    sc_refuse "${EX_REFUSED}" "unexpected account identity output; no mutating command was run"
  fi
  ACCOUNT_HASH="$(sc_sha256_string "${ACCOUNT_ID}")"
  if [[ "${ACCOUNT_HASH}" != "${APPROVED_ACCOUNT_SHA256}" ]]; then
    sc_refuse "${EX_REFUSED}" "account sha256 ${ACCOUNT_HASH} != APPROVED_ACCOUNT_SHA256 ${APPROVED_ACCOUNT_SHA256}; no mutating command was run"
  fi
  sc_info "account sha256 matches the approval record"
else
  ACCOUNT_HASH="${APPROVED_ACCOUNT_SHA256}"
  sc_info "dry run: the account comparison runs only with --execute, before any mutating command"
fi

ECR_HOST="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# _cloud [sc_exec options] -- CMD...: runs one mutating cloud command; in execute mode a failure
# stops the run with RESULT: FAIL naming the current step.
_cloud() {
  local rc=0
  sc_exec --cloud --show always "$@" || rc=$?
  if [[ "${EXECUTE}" -eq 1 && "${rc}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${rc}")" "command failed (exit ${rc}) during the mutating sequence"
  fi
}

sc_mktemp FACTS
: >"${FACTS}"
REG_DIGESTS=""
sc_mktemp REG_DIGESTS
: >"${REG_DIGESTS}"

# _registry_digest SVC: runs the describe-images query; in execute mode sets REG_DIGEST (sha256:...) and
# fails the run when the tag is missing or the digest is malformed.
REG_DIGEST=""
_registry_digest() {
  local svc="$1" repo="${NAME_PREFIX}/$1" rc=0
  REG_DIGEST="sha256:<resolved-at-execute>"
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
    "${AWS_ENV[@]}" aws ecr describe-images --region "${REGION}" --repository-name "${repo}" \
    --image-ids "imageTag=${IMAGE_REVISION}" --query 'imageDetails[0].imageDigest' --output text || rc=$?
  if [[ "${EXECUTE}" -eq 1 ]]; then
    REG_DIGEST="$(tr -d '[:space:]' <"${WORK_FILE}")"
    if [[ "${rc}" -ne 0 || ! "${REG_DIGEST}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
      sc_refuse "${EX_REFUSED}" "registry tag ${repo}:${IMAGE_REVISION} does not resolve to a sha256 digest"
    fi
  fi
}

# _ecr_repositories_exist: every repository must exist; the first deployment needs a base-apply first.
_ecr_repositories_exist() {
  local svc repo rc
  for svc in ${SERVICES}; do
    repo="${NAME_PREFIX}/${svc}"
    rc=0
    sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
      "${AWS_ENV[@]}" aws ecr describe-repositories --region "${REGION}" --repository-names "${repo}" \
      --query 'repositories[0].repositoryName' --output text || rc=$?
    if [[ "${EXECUTE}" -eq 1 && "${rc}" -ne 0 ]]; then
      sc_refuse "${EX_REFUSED}" "ECR repository ${repo} does not exist; apply the approved infrastructure first (no image was pushed)"
    fi
  done
}

# _terraform_apply: applies the verified private copy (never the original path). Immediately before apply: the
# pre-spend receipt, the plan copy's hash and the live state binding are verified again.
_terraform_apply() {
  _prespend_gate "terraform-apply"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    _reverify_plan
    _check_state_binding
  else
    sc_info "dry run: the plan copy's hash and the state binding would be re-verified immediately before apply"
  fi
  _cloud --timeout "${TIMEOUT_TERRAFORM_APPLY_SECONDS}" -- \
    "${TF_ENV[@]}" "${TF}" "-chdir=${TF_ROOT_DIR}" apply -input=false -lock-timeout=60s "${VERIFIED_PLAN:-<verified-private-copy-of-the-plan>}"
}

# ---- stage: base-apply ---------------------------------------------------------------------------
if [[ "${STAGE}" == "base-apply" ]]; then
  sc_step "terraform-apply"
  _terraform_apply

  sc_step "runtime-archive-upload"
  ARCHIVE_FACT_STATUS="skipped"
  if [[ "${SKIP_ARCHIVE}" -eq 1 ]]; then
    sc_info "skipped by --skip-runtime-archive"
  else
    bucket="${ARCHIVE_URI#s3://}"
    key="${bucket#*/}"
    bucket="${bucket%%/*}"
    _prespend_gate "archive-upload"
    if [[ "${EXECUTE}" -eq 1 ]]; then
      # Apply ran for a long time: the copy must still be the bytes that passed the pinned checks.
      now_size="$(wc -c <"${ARCHIVE_COPY}" | tr -d ' ')"
      now_sha="$(sc_sha256 "${ARCHIVE_COPY}")"
      if [[ "${now_size}" != "${ARCHIVE_SIZE}" || "${now_sha}" != "${ARCHIVE_SHA}" ]]; then
        sc_refuse "${EX_REFUSED}" "the private archive copy changed after verification; it is not uploaded"
      fi
    fi
    _cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" -- \
      "${AWS_ENV[@]}" aws s3 cp "${ARCHIVE_COPY}" "${ARCHIVE_URI}" --region "${REGION}" --only-show-errors \
      --checksum-algorithm SHA256 --metadata "sha256=${ARCHIVE_SHA:-<sha256-of-the-private-copy>}"
    _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
      "${AWS_ENV[@]}" aws s3api head-object --region "${REGION}" --bucket "${bucket}" --key "${key}" \
      --checksum-mode ENABLED --query '[ContentLength,Metadata.sha256,ChecksumSHA256]' --output text
    if [[ "${EXECUTE}" -eq 1 ]]; then
      read -r remote_size remote_sha remote_checksum <"${WORK_FILE}" || true
      if [[ "${remote_size:-}" != "${ARCHIVE_SIZE}" || "${remote_sha:-}" != "${ARCHIVE_SHA}" ]]; then
        sc_fail "${EX_GATE}" "uploaded runtime archive verification failed (remote size/sha256 metadata differ from the verified private copy)"
      fi
      # N5: the metadata above is what this script set itself; the S3-COMPUTED ChecksumSHA256 (base64 of the raw sha256;
      # for a multipart upload a composite of the part checksums) must also match the verified private copy.
      CHECKSUM_PARTS=()
      if [[ "${remote_checksum:-}" =~ -[0-9]+$ ]]; then
        sc_mktemp PARTS_FILE
        _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${PARTS_FILE}" -- \
          "${AWS_ENV[@]}" aws s3api get-object-attributes --region "${REGION}" --bucket "${bucket}" --key "${key}" \
          --object-attributes ObjectParts --max-parts 1000 --query 'ObjectParts.Parts[].[PartNumber,Size,ChecksumSHA256]' --output text
        CHECKSUM_PARTS=(--parts-file "${PARTS_FILE}")
      fi
      CHECKSUM_OUT="$(python3 -I "${SC_LIB_DIR}/verify.py" s3-checksum --file "${ARCHIVE_COPY}" --checksum "${remote_checksum:-}" ${CHECKSUM_PARTS[@]+"${CHECKSUM_PARTS[@]}"})" || CHECKSUM_OUT="${CHECKSUM_OUT:-S3-CHECKSUM-FAILED: checksum comparison could not run}"
      if [[ ! "${CHECKSUM_OUT}" =~ ^S3-computed ]]; then
        sc_fail "${EX_GATE}" "uploaded runtime archive verification failed (${CHECKSUM_OUT})"
      fi
      sc_info "runtime archive upload verified (size, sha256 metadata and the ${CHECKSUM_OUT})"
    else
      sc_info "dry run: after the upload the object's S3-computed ChecksumSHA256 is compared with the private copy (a multipart object also reads its part list: aws s3api get-object-attributes --object-attributes ObjectParts)"
    fi
    ARCHIVE_FACT_STATUS="uploaded"
  fi
  printf 'archive\t%s\t%s\t%s\t%s\n' "${RUNTIME_ARCHIVE_S3_URI_ENV}" "${ARCHIVE_FACT_STATUS}" "${ARCHIVE_SHA:-${RUNTIME_ARCHIVE_EXPECTED_SHA256}}" "${ARCHIVE_SIZE:-${RUNTIME_ARCHIVE_EXPECTED_SIZE}}" >>"${FACTS}"
fi

# ---- stage: cleanup-prepare ----------------------------------------------------------------------
if [[ "${STAGE}" == "cleanup-prepare" ]]; then
  sc_step "terraform-apply"
  _terraform_apply
  sc_info "NEXT: re-run scripts/cleanup.sh (listing); the protection check must now pass"
fi

# ---- stage: push ---------------------------------------------------------------------------------
if [[ "${STAGE}" == "push" ]]; then
  sc_step "ecr-repositories-exist"
  _ecr_repositories_exist

  sc_step "verify-local-images"
  sc_mktemp INSPECT_JSON
  IMAGE_IDS_FILE="${FACTS}.ids"
  : >"${IMAGE_IDS_FILE}"
  for svc in ${SERVICES}; do
    local_image="${LOCAL_IMAGE_PREFIX}-${svc}:${IMAGE_REVISION}"
    recorded_line="$(printf '%s\n' "${RELEASE_IMAGES}" | awk -v s="${svc}" '$1==s {print}')"
    recorded_image="$(printf '%s' "${recorded_line}" | awk '{print $2}')"
    recorded_id="$(printf '%s' "${recorded_line}" | awk '{print $3}')"
    if [[ "${recorded_image}" != "${local_image}" || ! "${recorded_id}" =~ ^sha256:[0-9a-f]{64}$ ]]; then
      sc_refuse "${EX_REFUSED}" "release manifest does not record ${local_image} with an image ID; no image was pushed"
    fi
    RC=0
    sc_exec --cloud --timeout 60 --capture "${INSPECT_JSON}" -- docker image inspect "${local_image}" || RC=$?
    if [[ "${EXECUTE}" -eq 1 ]]; then
      INSPECTED=""
      if [[ "${RC}" -eq 0 ]]; then
        INSPECTED="$(python3 -I "${SC_LIB_DIR}/tools.py" image-inspect "${INSPECT_JSON}")" || INSPECTED=""
      fi
      if [[ -z "${INSPECTED}" ]]; then
        sc_refuse "${EX_REFUSED}" "cannot inspect the local image ${local_image}; no image was pushed"
      fi
      if [[ "${INSPECTED%% *}" != "${IMAGE_PLATFORM}" ]]; then
        sc_refuse "${EX_REFUSED}" "local image ${local_image} is ${INSPECTED%% *}, expected ${IMAGE_PLATFORM}; no image was pushed"
      fi
      if [[ "${INSPECTED#* }" != "${recorded_id}" ]]; then
        sc_refuse "${EX_REFUSED}" "local tag ${local_image} no longer resolves to the image ID recorded in the release manifest (the tag was replaced); no image was pushed"
      fi
      sc_info "local image ${local_image} matches the release manifest (${IMAGE_PLATFORM}, recorded image ID)"
    else
      sc_info "dry run: would require ${local_image} to be ${IMAGE_PLATFORM} with image ID ${recorded_id}"
    fi
    printf '%s\t%s\n' "${svc}" "${recorded_id}" >>"${IMAGE_IDS_FILE}"
  done

  sc_step "ecr-login"
  sc_mktemp PASSWORD_FILE
  _prespend_gate "ecr-login"
  _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${PASSWORD_FILE}" -- \
    "${AWS_ENV[@]}" aws ecr get-login-password --region "${REGION}"
  _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --stdin "${PASSWORD_FILE}" -- \
    docker login --username AWS --password-stdin "${ECR_HOST}"

  sc_step "push-images"
  PUSHED_FILE="${FACTS}.pushed"
  : >"${PUSHED_FILE}"
  for svc in ${SERVICES}; do
    remote="${ECR_HOST}/${NAME_PREFIX}/${svc}:${IMAGE_REVISION}"
    image_id="$(awk -F'\t' -v s="${svc}" '$1==s {print $2}' "${IMAGE_IDS_FILE}")"
    _prespend_gate "push-${svc}"
    # Tag by the VERIFIED image ID, never by the mutable local tag.
    _cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- docker tag "${image_id}" "${remote}"
    _cloud --timeout "${TIMEOUT_DOCKER_PUSH_SECONDS}" --capture "${WORK_FILE}" -- docker push "${remote}"
    if [[ "${EXECUTE}" -eq 1 ]]; then
      pushed="$(python3 -I "${SC_LIB_DIR}/verify.py" push-digest --file "${WORK_FILE}")" || sc_fail "${EX_GATE}" "docker push of ${svc} printed no sha256 digest"
      printf '%s\t%s\n' "${svc}" "${pushed}" >>"${PUSHED_FILE}"
    fi
  done

  sc_step "record-digests"
  RECORD_LINES="${FACTS}.record"
  : >"${RECORD_LINES}"
  for svc in ${SERVICES}; do
    repo="${NAME_PREFIX}/${svc}"
    _registry_digest "${svc}"
    if [[ "${EXECUTE}" -eq 1 ]]; then
      pushed="$(awk -F'\t' -v s="${svc}" '$1==s {print $2}' "${PUSHED_FILE}")"
      if [[ "${REG_DIGEST}" != "${pushed}" ]]; then
        sc_fail "${EX_GATE}" "registry digest ${REG_DIGEST} for ${repo}:${IMAGE_REVISION} != the digest pushed (${pushed}); nothing was recorded"
      fi
      sc_info "registry digest for ${repo}:${IMAGE_REVISION} equals the pushed digest"
      image_id="$(awk -F'\t' -v s="${svc}" '$1==s {print $2}' "${IMAGE_IDS_FILE}")"
      printf '%s\t%s\t%s\t%s\n' "${svc}" "${repo}" "${pushed}" "${image_id}" >>"${RECORD_LINES}"
    fi
    printf 'image\t%s\t%s\t%s\t%s\n' "${svc}" "${repo}" "${IMAGE_REVISION}" "${REG_DIGEST}" >>"${FACTS}"
  done

  sc_step "write-push-record"
  if [[ "${EXECUTE}" -eq 1 ]]; then
    sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${RELEASE_DIR}" --within "${RELEASE_PREFIX}" --path "${RELEASE_PREFIX}/${COMMIT}"
    RC=0
    OUT_RECORD="$(python3 -I "${SC_LIB_DIR}/records.py" write-push-record --root "${REPO_ROOT}" --out "${PUSH_RECORD_DEFAULT}" --commit "${COMMIT}" \
      --account-sha256 "${ACCOUNT_HASH}" --region "${REGION}" --environment "${NAME_PREFIX_ENVIRONMENT}" --run-id "${RUN_ID}" \
      --pushed-utc "$(sc_now)" --pushed "${RECORD_LINES}")" || RC=$?
    if [[ "${RC}" -ne 0 ]]; then
      sc_fail "${EX_GATE}" "${OUT_RECORD}"
    fi
    sc_info "${OUT_RECORD}: commit, account hash, region, environment, the four repositories and the pushed digests"
  else
    sc_info "dry run: would create ${PUSH_RECORD_DEFAULT#"${REPO_ROOT}"/} exclusively (commit, account hash, region, environment, repositories, pushed digests)"
  fi
fi

# ---- stage: runtime-apply ------------------------------------------------------------------------
if [[ "${STAGE}" == "runtime-apply" ]]; then
  sc_step "ecr-repositories-exist"
  _ecr_repositories_exist

  sc_step "verify-registry-images"
  for svc in ${SERVICES}; do
    repo="${NAME_PREFIX}/${svc}"
    _registry_digest "${svc}"
    if [[ -n "${REUSE}" ]]; then
      recorded="$(printf '%s\n' "${PREV_DIGESTS}" | awk -v s="${svc}" '$1==s {print $4}')"
      if [[ "${EXECUTE}" -eq 1 ]]; then
        if [[ "${REG_DIGEST}" != "${recorded}" ]]; then
          sc_refuse "${EX_REFUSED}" "registry tag ${repo}:${IMAGE_REVISION} does not resolve to the recorded digest ${recorded}"
        fi
      else
        sc_info "dry run: would require ${repo}:${IMAGE_REVISION} to resolve to recorded digest ${recorded}"
      fi
      REG_DIGEST="${recorded}"
    else
      recorded="$(printf '%s\n' "${PUSHED_DIGESTS}" | awk -v s="${svc}" '$1==s {print $2}')"
      if [[ "${EXECUTE}" -eq 1 ]]; then
        if [[ "${REG_DIGEST}" != "${recorded}" ]]; then
          sc_refuse "${EX_REFUSED}" "registry tag ${repo}:${IMAGE_REVISION} resolves to ${REG_DIGEST}, not the digest ${recorded} recorded by the verified push; nothing was applied"
        fi
      else
        sc_info "dry run: would require ${repo}:${IMAGE_REVISION} to resolve to the digest ${recorded} recorded by the verified push"
      fi
      REG_DIGEST="${recorded}"
    fi
    printf '%s\t%s\n' "${svc}" "${REG_DIGEST}" >>"${REG_DIGESTS}"
    printf 'image\t%s\t%s\t%s\t%s\n' "${svc}" "${repo}" "${IMAGE_REVISION}" "${REG_DIGEST}" >>"${FACTS}"
  done

  sc_step "terraform-apply"
  _terraform_apply

  sc_step "record-ecs"
  # shellcheck disable=SC2086 # SERVICES is a space-separated list of simple names
  _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
    "${AWS_ENV[@]}" aws ecs describe-services --region "${REGION}" --cluster "${NAME_PREFIX}" --services ${SERVICES} \
    --query 'services[].[serviceName,taskDefinition]' --output text
  if [[ "${EXECUTE}" -eq 1 ]]; then
    SERVICE_MAP="${FACTS}.services"
    if ! python3 -I "${SC_LIB_DIR}/verify.py" ecs-services --file "${WORK_FILE}" --services "${SERVICES}" >"${SERVICE_MAP}"; then
      cat "${SERVICE_MAP}"
      sc_fail "${EX_GATE}" "not all four ECS services exist with an active task definition; the deployment is NOT recorded as successful"
    fi
    sc_mktemp TD_FILE
    while read -r svc arn; do
      repo="${NAME_PREFIX}/${svc}"
      _cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${TD_FILE}" -- \
        "${AWS_ENV[@]}" aws ecs describe-task-definition --region "${REGION}" --task-definition "${arn}" \
        --query 'taskDefinition.containerDefinitions[].image' --output text
      digest="$(awk -F'\t' -v s="${svc}" '$1==s {print $2}' "${REG_DIGESTS}")"
      python3 -I "${SC_LIB_DIR}/verify.py" image-ref --file "${TD_FILE}" --expected "${ECR_HOST}/${repo}:${IMAGE_REVISION}" \
        --expected-digest-ref "${ECR_HOST}/${repo}@${digest}" ||
        sc_fail "${EX_GATE}" "the active task definition of ${svc} does not reference ${repo}:${IMAGE_REVISION}; the deployment is NOT recorded as successful"
      printf 'ecs\t%s\t%s\n' "${svc}" "$(sc_redact "${arn}")" >>"${FACTS}"
    done <"${SERVICE_MAP}"
    sc_info "all four ECS services run task definitions that reference ${NAME_PREFIX}/<service>:${IMAGE_REVISION} (the digest verified before apply)"
  else
    for svc in ${SERVICES}; do
      sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
        "${AWS_ENV[@]}" aws ecs describe-task-definition --region "${REGION}" --task-definition "<${svc}-task-definition-arn>" \
        --query 'taskDefinition.containerDefinitions[].image' --output text
    done
    sc_info "dry run: each task definition image must equal <acct>.dkr.ecr.${REGION}.amazonaws.com/${NAME_PREFIX}/<service>:${IMAGE_REVISION} (or the verified digest)"
  fi
fi

sc_step "write-deploy-manifest"
OUT="${RELEASE_PREFIX}/${COMMIT}/deploy-manifest-${STAGE}-${RUN_ID}.json"
if [[ "${EXECUTE}" -eq 0 ]]; then
  sc_info "dry run: would write ${OUT#"${REPO_ROOT}"/} (stage, digests, task-definition ARNs, plan sha256, commit, region, account sha256)"
  sc_result DRY-RUN "all local checks passed (stage ${STAGE}: approval record, pre-spend receipt${PLAN:+, plan, receipt, state binding}); no mutating command was run" "${EX_OK}"
fi
{
  printf 'meta\tstage\t%s\n' "${STAGE}"
  printf 'meta\tcommit\t%s\n' "${SOURCE_COMMIT}"
  printf 'meta\timage_revision\t%s\n' "${IMAGE_REVISION}"
  printf 'meta\tregion\t%s\n' "${REGION}"
  printf 'meta\taccount_sha256\t%s\n' "${ACCOUNT_HASH}"
  printf 'meta\tplan_sha256\t%s\n' "${PLAN_SHA}"
  printf 'meta\tdeployed_utc\t%s\n' "$(sc_now)"
  printf 'meta\trun_id\t%s\n' "${RUN_ID}"
  cat "${FACTS}"
} >"${FACTS}.all"
sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name "${RELEASE_DIR}" --within "${RELEASE_PREFIX}" --path "${RELEASE_PREFIX}/${COMMIT}"
RC=0
MANIFEST_OUT="$(python3 -I "${SC_LIB_DIR}/tools.py" deploy-manifest --facts "${FACTS}.all" --out "${OUT}" --root "${REPO_ROOT}")" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "${EX_GATE}" "${MANIFEST_OUT}"
fi
echo "${MANIFEST_OUT}"
rm -f "${FACTS}.all"
sc_result PASS "stage ${STAGE} complete${IMAGE_REVISION:+ for ${IMAGE_REVISION}}; manifest=${OUT}" "${EX_OK}"
