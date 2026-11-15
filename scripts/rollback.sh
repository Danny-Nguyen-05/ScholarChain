#!/usr/bin/env bash
# Phase 13 rollback (policy 13-5), expressed through the Terraform-only path. Dry run by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF'
Usage: scripts/rollback.sh --env NAME [--region REGION] [--profile PROFILE]
                           (--previous-manifest FILE |
                            --mode infra --previous-commit SHA
                              [--deployed-manifest FILE | --deployed-push-record FILE])
                           [--stage plan|deploy] [--plan FILE] [--approval FILE] [--prespend FILE]
                           [--execute] [--help]

Purpose
  Roll back WITHOUT any console or CLI mutation outside Terraform, and without data repair
  (policy 13-5). Every mutation is delegated to scripts/plan.sh and scripts/deploy.sh, so each
  rollback needs the same human approval record, pre-spend receipt and plan provenance as a
  deployment.

  Application rollback (default, --mode app): redeploy the previous image digests recorded in the
  previous deploy-manifest.json (written by deploy.sh --execute --stage push or runtime-apply).
    1. verify the previous manifest holds sha256 digests for all four services
    2. verify the registry tag still resolves to the recorded digest:
         aws ecr describe-images --repository-name <repo> --image-ids imageTag=<previous commit>
       (printed in dry run; compared in --execute; a mismatch refuses)
    3. re-plan with image_revision=<previous commit SHA> through plan.sh (--stage plan)
    4. the human writes a NEW approval record for that plan (APPROVED_STAGE=runtime-apply, with
       APPROVED_PLAN_SHA256, APPROVED_RECEIPT_SHA256, APPROVED_COMMIT, APPROVED_ACCOUNT_SHA256, APPROVED_REGION,
       APPROVED_ENVIRONMENT and APPROVED_PRESPEND_SHA256) and a fresh pre-spend receipt, then
    5. deploy.sh --stage runtime-apply --reuse-images <previous manifest> --execute (--stage deploy):
       applies exactly the approved plan copy; pushes nothing; account/region/commit/plan/receipt
       checks all apply and the four ECS task definitions are verified afterwards
  Infrastructure rollback (--mode infra --previous-commit SHA): the CURRENT scripts run against the
  previous commit's Terraform source, which plan.sh and deploy.sh materialize read-only (git archive
  of infra/terraform at SHA into a PRIVATE run directory <PLAN_DIR>/<run-id>/source/SHA). The previous tree
  does NOT need to contain these scripts, and nothing is checked out: this script never changes the work
  tree. The materialized copy is bound to the LIVE local state file (TERRAFORM_STATE_FILE) by a generated
  backend "local" override, so the rollback plans AND applies against the existing state of the live stack,
  never a fresh one: the plan receipt records the state's lineage, serial and sha256, and deploy.sh refuses
  to apply when the state file is missing, has a different lineage or changed after the plan.
  No data repair of any kind is performed; S3 versioning and the DynamoDB, Neptune and load balancer protections stay.

  Two kinds, chosen by what the LIVE state shows (step runtime-state reads the state file locally: module path,
  type and instance count only). "Runtime live" means the runtime is DEPLOYED, and is decided only from the pinned
  RUNTIME_LIVE_INDICATOR_TYPES of RUNTIME_LIVE_MODULE: resources that exist solely while the runtime is deployed (the
  four ECS services, the query load balancer and its target group; the HTTPS listener when a certificate is set).
  The ECS cluster, the service-discovery namespace and the four ECR repositories are NOT indicators: a runtime-disabled
  base apply already creates them, so a state after the first base apply is "runtime NOT live". A state with some but
  not all indicators (for example a load balancer without services, or only some services) is an ambiguous PARTIAL
  runtime: it is REFUSED at STEP runtime-state before any registry, plan or apply call (route it to the human).
    runtime NOT live (runtime disabled, the default): steps 3-5 are the same with
       plan.sh --source-commit SHA and deploy.sh --stage base-apply --source-commit SHA (APPROVED_COMMIT = SHA,
       APPROVED_STAGE=base-apply; the plan receipt records SHA as the planned commit; no image revision).
    runtime LIVE (S1, keeps the running runtime): the rollback MUST carry the CURRENTLY DEPLOYED image revision,
       bound to exactly one of
         --deployed-manifest FILE      the deploy-manifest.json written by the runtime-apply that put the revision
                                       live (it must be a runtime-apply manifest: this region, the four
                                       repositories, all four ECS services recorded; deploy.sh also compares
                                       the account)
         --deployed-push-record FILE   the push record of that revision (the revision is the record's commit)
       Before anything else the registry digests of <repo>:<revision> are compared with that manifest or record
       (aws ecr describe-images, as in an application rollback; a mismatch refuses before any plan or apply). Then
         3. plan.sh --source-commit SHA --image-revision <revision> (--stage plan); the receipt's action list is
            checked at once (STEP runtime-preservation): a plan that would delete or replace a protected type
            (RUNTIME_LIVE_PROTECTED_TYPES: the indicator types plus the ECS cluster) while the state shows the
            deployed runtime is REFUSED and must not be approved;
         4. the human writes a NEW approval record: APPROVED_STAGE=runtime-apply, APPROVED_COMMIT=SHA (the Terraform
            source), plus the plan and receipt hashes, account hash, region, environment and pre-spend receipt;
         5. deploy.sh --stage runtime-apply --source-commit SHA (--reuse-images <manifest> | --image-revision <rev>
            --push-record <record>) (--stage deploy): it re-verifies manifest or record, registry digests (before
            apply), receipt, approval, plan target (the plan's image_revision must equal the bound revision),
            state binding and runtime preservation, applies exactly the approved plan, then checks that all four ECS
            services reference the bound revision (or its verified digest) before anything is recorded as success.
    A live runtime without --deployed-* is refused (a plan without an image revision would delete it); --deployed-*
    while the state shows no deployed runtime is refused too (the rollback would CREATE the runtime), also when the
    state holds the ECS cluster and ECR repositories of a base apply; a PARTIAL runtime is refused either way.

Dry run (default): verifies local inputs, prints the delegated plan.sh dry-run output, the registry
digest verification commands and the exact deploy.sh invocation (with --profile). It runs no aws, docker
or terraform command beyond the local Terraform version probe: the inspection of a plan (terraform show) is
deferred to --execute.

Options
  --env NAME               environment (infra/terraform/environments/NAME.tfvars); required
  --region REGION          region (or SCHOLARCHAIN_AWS_REGION); required
  --profile PROFILE        profile (or AWS_PROFILE); required with --execute; printed in the delegated commands
  --previous-manifest FILE previous deploy-manifest.json (app mode)
  --mode app|infra         default app
  --previous-commit SHA    previous commit (infra mode)
  --deployed-manifest FILE   infra mode, runtime live: deploy-manifest.json of the runtime-apply that deployed the
                           revision to keep
  --deployed-push-record FILE  infra mode, runtime live: push record of the revision to keep (alternative to the manifest)
  --stage plan|deploy      required with --execute: the two-step flow in 3 and 5 above
  --plan FILE              rollback plan file printed by --stage plan as "PLAN-FILE: <path>" (the --stage deploy input;
                           also run as a dry-run deploy check when given)
  --approval FILE          approval record passed to deploy.sh
  --prespend FILE          pre-spend receipt passed to deploy.sh
  --execute                delegate with --execute (human approval points 4 and 1)

Inputs (environment variable NAMES): SCHOLARCHAIN_AWS_REGION, AWS_PROFILE,
  SCHOLARCHAIN_TF_PRIVATE_VARS, TERRAFORM_BIN, SCHOLARCHAIN_RUNTIME_ARCHIVE(_S3_URI) (via deploy.sh).

Human approval points (plan Section 7.3)
  4. the re-plan (plan.sh --execute) needs the user's approved profile;
  1. the redeploy (deploy.sh --execute) needs a NEW Phase 14 approval record naming the rollback
     plan's sha256, the commit, the account hash, the region, the pre-spend receipt and the stage. A
     reviewed plan is not approval.

Exit codes
  0    dry run printed, or the requested stage succeeded
  2    usage error
  3    refused: bad manifest or push record, registry digest mismatch, unknown previous commit, a live runtime
       that would not be kept, a binding without a deployed runtime, a partial runtime or an unreadable state
       (STEP runtime-state / runtime-preservation), or a delegated refusal
  4/5/124  propagated from the delegated plan.sh or deploy.sh

Evidence produced
  The delegated receipts: <PLAN_DIR>/<run-id>/<env>-<revision>.tfplan(.receipt.json) from plan.sh (path printed as
  PLAN-FILE) and deploy-manifest-<stage>-<run-id>.json from deploy.sh, plus this script's STEP/RESULT lines.
EOF
}

ENV_NAME=""
REGION="${SCHOLARCHAIN_AWS_REGION:-}"
PROFILE="${AWS_PROFILE:-}"
PREV_MANIFEST=""
MODE="app"
PREV_COMMIT=""
DEPLOYED_MANIFEST=""
DEPLOYED_PUSH_RECORD=""
STAGE=""
PLAN=""
APPROVAL=""
PRESPEND=""
EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env | --region | --profile | --previous-manifest | --mode | --previous-commit | --deployed-manifest | --deployed-push-record | --stage | --plan | --approval | --prespend)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "rollback.sh" "$1 needs a value"
      fi
      case "$1" in
        --env) ENV_NAME="$2" ;;
        --region) REGION="$2" ;;
        --profile) PROFILE="$2" ;;
        --previous-manifest) PREV_MANIFEST="$2" ;;
        --mode) MODE="$2" ;;
        --previous-commit) PREV_COMMIT="$2" ;;
        --deployed-manifest) DEPLOYED_MANIFEST="$2" ;;
        --deployed-push-record) DEPLOYED_PUSH_RECORD="$2" ;;
        --stage) STAGE="$2" ;;
        --plan) PLAN="$2" ;;
        --approval) APPROVAL="$2" ;;
        --prespend) PRESPEND="$2" ;;
      esac
      shift 2
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
      sc_usage_exit "rollback.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "rollback.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
[[ -n "${ENV_NAME}" ]] || sc_usage_error "--env NAME is required"
[[ -n "${REGION}" ]] || sc_usage_error "region required: --region or SCHOLARCHAIN_AWS_REGION"
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
case "${MODE}" in
  app)
    [[ -n "${PREV_MANIFEST}" ]] || sc_usage_error "--mode app needs --previous-manifest FILE"
    [[ -z "${DEPLOYED_MANIFEST}${DEPLOYED_PUSH_RECORD}" ]] || sc_usage_error "--deployed-manifest and --deployed-push-record belong to --mode infra (an application rollback uses --previous-manifest)"
    ;;
  infra)
    [[ "${PREV_COMMIT}" =~ ^[0-9a-f]{40}$ ]] || sc_usage_error "--mode infra needs --previous-commit <40-hex SHA>"
    [[ -z "${DEPLOYED_MANIFEST}" || -z "${DEPLOYED_PUSH_RECORD}" ]] || sc_usage_error "give --deployed-manifest OR --deployed-push-record, not both"
    ;;
  *) sc_usage_error "--mode must be app or infra" ;;
esac
if [[ "${EXECUTE}" -eq 1 ]]; then
  case "${STAGE}" in
    plan | deploy) ;;
    *) sc_usage_error "--execute needs --stage plan or --stage deploy (the human writes the approval record between them)" ;;
  esac
  [[ -n "${PROFILE}" ]] || sc_refuse "${EX_REFUSED}" "--execute needs the approved AWS profile (--profile or AWS_PROFILE)"
  if [[ "${STAGE}" == "deploy" && -z "${PLAN}" ]]; then
    sc_usage_error "--stage deploy needs --plan FILE (the rollback plan the new approval record names)"
  fi
else
  [[ -n "${PROFILE}" ]] || PROFILE="<profile>"
fi
sc_require_tool python3
sc_require_tool git

sc_step "terraform-version"
sc_require_terraform

SERVICES=""
while read -r svc _main; do
  SERVICES="${SERVICES} ${svc}"
done < <(sc_service_list)
SERVICES="${SERVICES# }"
NAME_PREFIX="$(sc_name_prefix)"
REPOSITORIES=""
for svc in ${SERVICES}; do
  REPOSITORIES="${REPOSITORIES} ${NAME_PREFIX}/${svc}"
done
REPOSITORIES="${REPOSITORIES# }"
HEAD_COMMIT="$(sc_git_head)" || sc_refuse "${EX_REFUSED}" "not a git work tree with a commit"
IMAGE_REVISION=""

AWS_ENV=(env "AWS_PROFILE=${PROFILE}" "AWS_REGION=${REGION}" AWS_PAGER=)
sc_mktemp WORK_FILE

# _verify_registry_digests: every <repo>:<IMAGE_REVISION> must resolve to the digest recorded in PREV_DIGESTS
# ("<service> <repository> <tag> <digest>" lines). Printed in a dry run; compared with --execute (a mismatch refuses).
_verify_registry_digests() {
  local svc repo recorded rc current
  for svc in ${SERVICES}; do
    repo="${NAME_PREFIX}/${svc}"
    recorded="$(printf '%s\n' "${PREV_DIGESTS}" | awk -v s="${svc}" '$1==s {print $4}')"
    rc=0
    sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- \
      "${AWS_ENV[@]}" aws ecr describe-images --region "${REGION}" --repository-name "${repo}" \
      --image-ids "imageTag=${IMAGE_REVISION}" --query 'imageDetails[0].imageDigest' --output text || rc=$?
    if [[ "${EXECUTE}" -eq 1 ]]; then
      current="$(tr -d '[:space:]' <"${WORK_FILE}")"
      if [[ "${rc}" -ne 0 || "${current}" != "${recorded}" ]]; then
        sc_refuse "${EX_REFUSED}" "registry tag ${repo}:${IMAGE_REVISION} does not resolve to the recorded digest ${recorded}"
      fi
      sc_info "registry tag ${repo}:${IMAGE_REVISION} resolves to the recorded digest"
    else
      sc_info "dry run: would require ${repo}:${IMAGE_REVISION} to resolve to ${recorded}"
    fi
  done
}

# _list_recorded: print the recorded image lines of PREV_DIGESTS.
_list_recorded() {
  printf '%s\n' "${PREV_DIGESTS}" | grep -v '^IMAGE_REVISION' | while read -r svc repo tag digest; do
    sc_info "recorded: ${svc} ${repo}:${tag} ${digest}"
  done
}

RUNTIME_BOUND=0
if [[ "${MODE}" == "app" ]]; then
  sc_step "previous-manifest"
  [[ -f "${PREV_MANIFEST}" ]] || sc_refuse "${EX_REFUSED}" "previous deploy manifest not found: ${PREV_MANIFEST}"
  RC=0
  python3 -I "${SC_LIB_DIR}/tools.py" verify-deploy-manifest --manifest "${PREV_MANIFEST}" --services "${SERVICES}" || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "previous deploy manifest failed verification"
  PREV_DIGESTS="$(python3 -I "${SC_LIB_DIR}/tools.py" digests --manifest "${PREV_MANIFEST}")"
  IMAGE_REVISION="$(printf '%s\n' "${PREV_DIGESTS}" | sed -n 's/^IMAGE_REVISION //p')"
  sc_info "rolling back to image revision ${IMAGE_REVISION}"
  _list_recorded

  sc_step "verify-registry-digests"
  _verify_registry_digests
else
  sc_step "previous-commit"
  if ! sc_git -C "${REPO_ROOT}" cat-file -e "${PREV_COMMIT}^{commit}" 2>/dev/null; then
    sc_refuse "${EX_REFUSED}" "--previous-commit ${PREV_COMMIT} is not a commit in this repository"
  fi
  if ! sc_git -C "${REPO_ROOT}" cat-file -e "${PREV_COMMIT}:${TERRAFORM_ROOT}" 2>/dev/null; then
    sc_refuse "${EX_REFUSED}" "commit ${PREV_COMMIT} has no ${TERRAFORM_ROOT}"
  fi
  sc_info "infrastructure rollback: the CURRENT scripts (HEAD ${HEAD_COMMIT}) run against ${TERRAFORM_ROOT} as committed at ${PREV_COMMIT}, materialized read-only; no checkout is needed and the previous tree need not contain scripts/"

  # S1/T1: is the runtime DEPLOYED in the LIVE state? Decided only from the pinned indicator types (resources that exist
  # solely while the runtime is deployed), never from the ECS cluster or ECR repositories a runtime-disabled base apply
  # creates. Deployed: the rollback must carry its image revision. Not deployed: it must not (that would CREATE it).
  # Partial (some indicators, not all): ambiguous, refused here before any registry, plan or apply call.
  sc_step "runtime-state"
  RC=0
  LIVE_OUT="$(python3 -I "${SC_LIB_DIR}/verify.py" runtime-live --state "${SC_STATE_ABS}" --module "${RUNTIME_LIVE_MODULE:-}" \
    --indicators "${RUNTIME_LIVE_INDICATOR_TYPES:-}" --types "${RUNTIME_LIVE_PROTECTED_TYPES:-}")" || RC=$?
  while IFS= read -r line; do
    [[ -z "${line}" ]] || sc_info "${line}"
  done <<<"${LIVE_OUT}"
  [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "$(printf '%s\n' "${LIVE_OUT}" | tail -n 1)"
  BOUND_GIVEN=0
  if [[ -n "${DEPLOYED_MANIFEST}${DEPLOYED_PUSH_RECORD}" ]]; then
    BOUND_GIVEN=1
  fi
  case "${LIVE_OUT}" in
    "RUNTIME-LIVE: yes"*)
      if [[ "${BOUND_GIVEN}" -eq 0 ]]; then
        sc_refuse "${EX_REFUSED}" "the live state shows a RUNNING runtime: an infrastructure rollback must carry the deployed image revision (--deployed-manifest FILE or --deployed-push-record FILE); a plan without one would delete the runtime"
      fi
      RUNTIME_BOUND=1
      ;;
    "RUNTIME-LIVE: no"*)
      if [[ "${BOUND_GIVEN}" -eq 1 ]]; then
        sc_refuse "${EX_REFUSED}" "--deployed-manifest/--deployed-push-record was given but the live state shows no deployed runtime (no ECS service, load balancer or target group; the ECS cluster and ECR repositories of a runtime-disabled base apply do not count): this rollback would CREATE the runtime; use the runtime-disabled infrastructure rollback (no image revision)"
      fi
      ;;
    *)
      sc_refuse "${EX_REFUSED}" "the runtime-state verdict is not recognized; refusing (fail closed)"
      ;;
  esac

  if [[ "${RUNTIME_BOUND}" -eq 1 ]]; then
    sc_step "deployed-revision"
    if [[ -n "${DEPLOYED_MANIFEST}" ]]; then
      [[ -f "${DEPLOYED_MANIFEST}" ]] || sc_refuse "${EX_REFUSED}" "deployed-image manifest not found: ${DEPLOYED_MANIFEST}"
      RC=0
      python3 -I "${SC_LIB_DIR}/tools.py" verify-deploy-manifest --manifest "${DEPLOYED_MANIFEST}" --services "${SERVICES}" \
        --require-stage runtime-apply --region "${REGION}" --repositories "${REPOSITORIES}" --require-ecs-services || RC=$?
      [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "the deployed-image manifest is not a verified runtime-apply manifest for these four repositories; refusing before any plan"
      PREV_DIGESTS="$(python3 -I "${SC_LIB_DIR}/tools.py" digests --manifest "${DEPLOYED_MANIFEST}")"
      IMAGE_REVISION="$(printf '%s\n' "${PREV_DIGESTS}" | sed -n 's/^IMAGE_REVISION //p')"
    else
      [[ -f "${DEPLOYED_PUSH_RECORD}" ]] || sc_refuse "${EX_REFUSED}" "deployed-image push record not found: ${DEPLOYED_PUSH_RECORD}"
      RC=0
      IMAGE_REVISION="$(python3 -I "${SC_LIB_DIR}/records.py" revision --file "${DEPLOYED_PUSH_RECORD}")" || RC=$?
      [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "${IMAGE_REVISION}"
      RC=0
      PUSHED_LINES="$(python3 -I "${SC_LIB_DIR}/records.py" check-push-record --file "${DEPLOYED_PUSH_RECORD}" --commit "${IMAGE_REVISION}" \
        --region "${REGION}" --environment "${NAME_PREFIX_ENVIRONMENT}" --repositories "${REPOSITORIES}" --services "${SERVICES}")" || RC=$?
      [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "${PUSHED_LINES}"
      PREV_DIGESTS=""
      while read -r svc digest; do
        PREV_DIGESTS="${PREV_DIGESTS}${svc} ${NAME_PREFIX}/${svc} ${IMAGE_REVISION} ${digest}"$'\n'
      done <<<"${PUSHED_LINES}"
    fi
    sc_info "keeping the running runtime at image revision ${IMAGE_REVISION} (the deployed manifest or push record binds it; deploy.sh also compares the account)"
    _list_recorded

    sc_step "verify-registry-digests"
    _verify_registry_digests
  fi
fi

# _delegate NAME ARGS...: run a sibling script; its output is shown prefixed so STEP markers stay unambiguous.
# The captured output file stays readable in DELEGATE_OUT until the next call.
DELEGATE_OUT=""
_delegate() {
  local name="$1" rc=0
  shift
  sc_mktemp DELEGATE_OUT
  printf 'CMD: %s\n' "$(sc_redact "$(sc_quote bash "${SC_SCRIPTS_DIR}/${name}" "$@")")"
  bash "${SC_SCRIPTS_DIR}/${name}" "$@" >"${DELEGATE_OUT}" 2>&1 || rc=$?
  sed 's/^/  | /' "${DELEGATE_OUT}"
  return "${rc}"
}

# plan.sh creates a fresh private run directory per run and prints the plan path as PLAN-FILE.
PLAN_ARGS=(--env "${ENV_NAME}" --region "${REGION}" --profile "${PROFILE}")
DEPLOY_ARGS=(--region "${REGION}" --plan "${PLAN:-<rollback-plan-file-printed-by-plan.sh-as-PLAN-FILE>}" --profile "${PROFILE}")
if [[ "${MODE}" == "app" ]]; then
  PLAN_ARGS+=(--image-revision "${IMAGE_REVISION}")
  DEPLOY_ARGS+=(--stage runtime-apply --reuse-images "${PREV_MANIFEST}")
elif [[ "${RUNTIME_BOUND}" -eq 1 ]]; then
  # S1: the rollback keeps the running runtime: the plan and the apply carry the bound image revision.
  PLAN_ARGS+=(--source-commit "${PREV_COMMIT}" --image-revision "${IMAGE_REVISION}")
  DEPLOY_ARGS+=(--stage runtime-apply --source-commit "${PREV_COMMIT}")
  if [[ -n "${DEPLOYED_MANIFEST}" ]]; then
    DEPLOY_ARGS+=(--reuse-images "${DEPLOYED_MANIFEST}")
  else
    DEPLOY_ARGS+=(--image-revision "${IMAGE_REVISION}" --push-record "${DEPLOYED_PUSH_RECORD}")
  fi
else
  PLAN_ARGS+=(--source-commit "${PREV_COMMIT}")
  # An infrastructure rollback re-applies the Terraform source only: the 322 MB runtime archive is not re-uploaded.
  DEPLOY_ARGS+=(--stage base-apply --source-commit "${PREV_COMMIT}" --skip-runtime-archive)
fi
if [[ -n "${APPROVAL}" ]]; then
  DEPLOY_ARGS+=(--approval "${APPROVAL}")
fi
if [[ -n "${PRESPEND}" ]]; then
  DEPLOY_ARGS+=(--prespend "${PRESPEND}")
fi

if [[ "${EXECUTE}" -eq 0 ]]; then
  sc_step "delegate-plan"
  sc_info "re-plan through plan.sh (dry run shown below; it performs no aws or terraform command)"
  if [[ "${MODE}" == "infra" ]]; then
    sc_info "after the real re-plan the receipt's action list is checked (STEP runtime-preservation): a plan that deletes or replaces a live runtime-class resource is refused"
  fi
  RC=0
  _delegate plan.sh "${PLAN_ARGS[@]}" || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_fail "${RC}" "delegated plan.sh dry run failed"
  sc_step "delegate-deploy"
  sc_info "then, after the human writes a NEW approval record (and a fresh pre-spend receipt) for the rollback plan:"
  printf 'DRY-RUN CMD: %s\n' "$(sc_redact "$(sc_quote scripts/deploy.sh "${DEPLOY_ARGS[@]}" --execute)")"
  if [[ -n "${PLAN}" ]]; then
    sc_info "--plan was given: delegated deploy.sh dry run (local checks only)"
    RC=0
    _delegate deploy.sh "${DEPLOY_ARGS[@]}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_fail "${RC}" "delegated deploy.sh dry run refused (see output above)"
  fi
  sc_result DRY-RUN "rollback verified locally; nothing was run; approval point 1 (a new Phase 14 record and pre-spend receipt) is required before deploy" "${EX_OK}"
fi

RC=0
if [[ "${STAGE}" == "plan" ]]; then
  sc_step "delegate-plan"
  _delegate plan.sh "${PLAN_ARGS[@]}" --execute || RC=$?
  [[ "${RC}" -eq 0 ]] || sc_fail "${RC}" "delegated plan.sh failed"
  ROLLBACK_PLAN="$(sed -n 's/^PLAN-FILE: //p' "${DELEGATE_OUT}" | head -n 1)"
  if [[ "${MODE}" == "infra" ]]; then
    # S1 safety net, at once and before the human reviews: while the state shows the runtime, the plan must delete
    # or replace none of its runtime-class resources (deploy.sh checks the receipt and the verified plan again).
    sc_step "runtime-preservation"
    EXPECT_RUNTIME=not-live
    if [[ "${RUNTIME_BOUND}" -eq 1 ]]; then
      EXPECT_RUNTIME=live
    fi
    [[ -n "${ROLLBACK_PLAN}" && -f "${ROLLBACK_PLAN}.receipt.json" ]] || sc_refuse "${EX_REFUSED}" "the plan receipt was not found next to the rollback plan; cannot check that the live runtime is kept"
    RC=0
    python3 -I "${SC_LIB_DIR}/verify.py" runtime-preservation --state "${SC_STATE_ABS}" --module "${RUNTIME_LIVE_MODULE:-}" \
      --indicators "${RUNTIME_LIVE_INDICATOR_TYPES:-}" --types "${RUNTIME_LIVE_PROTECTED_TYPES:-}" \
      --receipt "${ROLLBACK_PLAN}.receipt.json" --expect "${EXPECT_RUNTIME}" || RC=$?
    [[ "${RC}" -eq 0 ]] || sc_refuse "${EX_REFUSED}" "this rollback plan would not keep the live runtime (see RUNTIME-PRESERVATION-FAILED above); do NOT approve or apply it"
  fi
  sc_info "NEXT (human): review the plan, write a NEW approval record with the APPROVED_* lines above, then run --stage deploy --plan <the PLAN-FILE above>"
  sc_result PASS "rollback plan recorded at ${ROLLBACK_PLAN:-<see PLAN-FILE above>}; run --stage deploy after writing the approval record" "${EX_OK}"
fi
sc_step "delegate-deploy"
_delegate deploy.sh "${DEPLOY_ARGS[@]}" --execute || RC=$?
[[ "${RC}" -eq 0 ]] || sc_fail "${RC}" "delegated deploy.sh failed or refused"
sc_result PASS "rollback deployed through deploy.sh" "${EX_OK}"
