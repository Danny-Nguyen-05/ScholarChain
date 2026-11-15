#!/usr/bin/env bash
# Phase 14B/15A EMR artifact upload: put the EMR bootstrap script, the four step programs, the four job JARs (from the local artifact
# manifest), optional config files and up to three input datasets into the project ARTIFACTS bucket under emr/<run-prefix>/, with
# checksums verified and recorded. Dry run by default; --execute needs the recorded human approval record.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/upload-emr-artifacts.sh --artifacts-bucket BUCKET --run-prefix run-YYYYMMDD --region REGION
                                       --input-dataset LABEL=DIR [--input-dataset LABEL=DIR ...]
                                       [--bootstrap FILE] [--artifact-manifest FILE] [--er-policy FILE] [--er-config FILE]
                                       [--spark-config-template FILE]
                                       --profile scholarchain-pipeline --principal-role operator-pipeline --approval FILE
                                       [--manifest-out PATH] [--execute] [--help]

Purpose
  Upload everything the EMR runs need, from the local machine, to the project artifacts bucket scholarchain-<env>-<account>-artifacts
  (the only bucket the EMR module accepts for its artifact URIs and the EMR instance role reads). The key is emr/<run-prefix>/<kind>/...
  (the final grant of the operator-pipeline role: create-only below exactly that prefix):
    bin/bootstrap.sh                         scripts/emr/bootstrap.sh (or --bootstrap)               -> emr_config.bootstrap_uri
    jars/hadoop-submit.jar, hadoop-bundle.jar, entity-resolution.jar, spark-job.jar
                                             the four job JARs listed by --artifact-manifest (default target/emr-artifacts/
                                             emr-artifact-manifest.json, written by `sbt packageEmr`; roles hadoop-submit-jar,
                                             hadoop-dependency-bundle, entity-resolution-job-jar, spark-job-jar); each file's sha256 and
                                             size must equal the manifest    -> emr_config.job_jar_uri (spark-job.jar), pipeline flags
    steps/<name>                             the four step programs of scripts/emr/, each sha256 equal to the Terraform pin
                                             infra/terraform/emr-step-programs.json                   -> emr_config.extra_artifacts
    config/er-policy.json, er-config.json, spark-config-template.json
                                             from --er-policy, --er-config, --spark-config-template (each optional)
    input/<label>/datasets/samples/...       one input dataset per --input-dataset LABEL=DIR (1 to 3; size-25, size-50 and size-100 in
                                             Phase 15A); DIR must hold the Phase 4 layout run-bounded-pipeline.sh stages in
                                             (datasets/samples/dblp/linked-records.xml, openalex/works.jsonl, crossref/works.jsonl,
                                             orcid/records.jsonl) and at most PIPELINE_MAX_INPUT_BYTES in total.
                                                                       -> --input-prefix s3://<bucket>/emr/<run-prefix>/input/<label>
  The G5 runtime archive is NOT uploaded here: deploy.sh --stage base-apply uploads it. Pipeline output (--output-prefix
  s3://<bucket>/pipeline/<run-prefix>/15a/size-N) is written by the EMR instance role and is not uploaded here.

Usage errors (exit 2, nothing is read, nothing is uploaded)
  * a missing or invalid run prefix (^run-[a-z0-9][a-z0-9-]{1,27}$, the same rule as the deployer's operator_run_prefix); a missing region,
    or a bucket name that is not scholarchain-<env>-<account>-artifacts; no --input-dataset;
  * --execute without --profile, --principal-role or --approval; an unknown option or an option without its value.

Refusals (exit 3, nothing is uploaded; every check runs before the first PutObject)
  * --execute with an approval record that does not exist, is a link, or does not match this plan (see "Approval record");
  * a step program that differs from the Terraform pin (STEP-PROGRAM-DRIFT), a job JAR that differs from the artifact manifest or is
    missing, a manifest that does not hold exactly the four roles, an input dataset without the four sample files or above the input ceiling;
  * a key outside emr/<run-prefix>/, a symbolic link anywhere, a file over 5 GiB, more than 5000 files or 4 GiB in total;
  * a bucket of another account than the profile, or a caller that is not an assumed-role session of scholarchain-<env>-<principal-role>;
  * an object that ALREADY exists under a planned key with different content (size or SHA-256), or with no SHA-256 checksum: nothing is
    overwritten, ever. An existing object with the same SHA-256 and size is UNCHANGED and skipped, so a re-run after a failure is safe;
  * an existing --manifest-out (it is evidence and is never overwritten).

Dry run (default): scans and hashes the local files, prints the plan (UPLOAD-FILE: lines), PLAN-SHA256, the values to copy next
  (EMR-CONFIG: / EMR-RENDER: / EMR-PIPELINE: lines: the URIs and sha256 values for emr_config, for experiments/scripts/render_manifests.py --sha, and the run-bounded-pipeline.sh input prefixes), the APPROVAL-LINE: lines the
  human pastes into the approval record, and the aws commands --execute would run (DRY-RUN CMD:). It makes no aws call and writes no file.

Approval record (--approval FILE; written by the human, never by an agent; the file must exist or --execute is refused)
  APPROVED_ACTION=upload-emr-artifacts          APPROVED_PLAN_SHA256=<the dry run's PLAN-SHA256>
  APPROVED_ACCOUNT_SHA256=<sha256 of the 12-digit account id of the bucket, no newline>     APPROVED_REGION=<region>
  Each line exactly once as KEY=value (no quotes, spaces, indent or CR); other text is ignored; an unknown APPROVED_* key refuses.
  The plan hash covers every key, size and sha256, so a changed file needs a new approval.

--execute: sts get-caller-identity (account and role check); s3api list-objects-v2 under emr/<run-prefix>/ and get-object-attributes of every
  key that already exists (the refusals above); then for each new file
    aws s3api put-object --checksum-algorithm SHA256 --checksum-sha256 <base64 of the local sha256> --if-none-match '*'
  (S3 itself rejects a body that does not match the declared SHA-256 and a key that appeared in the meantime; --if-none-match needs AWS CLI
  v2.17 or newer); then s3api head-object --checksum-mode ENABLED of every key, which must report the local size and SHA-256; then the
  manifest is written (key, class, bytes, sha256, version id, status uploaded|unchanged per file).

Inputs
  --artifacts-bucket NAME  the artifacts bucket (or SCHOLARCHAIN_ARTIFACTS_BUCKET)      --run-prefix P    for example run-20261115
  --region R               (or SCHOLARCHAIN_AWS_REGION)                                 --input-dataset LABEL=DIR   LABEL ^[a-z0-9][a-z0-9-]{1,19}$
  --profile P              required with --execute (or AWS_PROFILE): scholarchain-pipeline, the `aws login` profile of the operator-pipeline
                           role, which may only CREATE below emr/<run-prefix>/ in the artifacts bucket (PutObject with If-None-Match '*'; multipart
                           allowed), read it back, and read pipeline/<run>/ and the EMR logs; it cannot write raw, curated or reports. Credentials are never read, printed or logged: only the profile NAME reaches aws.
  --principal-role NAME    required with --execute: the role name suffix of that principal; the caller must be
                           assumed-role/scholarchain-<env>-<NAME>/... (operator-pipeline, the role infra/terraform/deployer/operator_pipeline.tf creates; the
                           name is an argument, not a constant, so a change of principal needs no script change).
  --approval FILE          the approval record (required with --execute)
  --manifest-out PATH      default target/phase14/evidence/15a/emr-upload-manifest.json; must lie below target/ (git-ignored) and not exist
  --execute                upload (see above); without it nothing happens
  Environment variable names: SCHOLARCHAIN_AWS_REGION, SCHOLARCHAIN_ARTIFACTS_BUCKET, AWS_PROFILE, SCHOLARCHAIN_REPO_ROOT.

Human approval points
  Uploading is a live cloud mutation: --execute follows the recorded Phase 14B/15A gate and the principal's session. The dry run needs no
  approval. Nothing is uploaded before the approval record exists.

Exit codes
  0    dry run printed; or upload completed and verified, manifest written
  2    usage error
  3    refused (see above); nothing was uploaded
  4    verification failed (stored size or SHA-256 differs from the local file); the manifest is NOT written
  5    an aws command failed (a re-run skips the objects that were already stored with the same content)
  124  a command timed out

Evidence produced
  STEP: markers, UPLOAD-FILE, UNCHANGED, UPLOADED, VERIFIED lines and one RESULT: line on stdout; with --execute the manifest
  scholarchain.emr-upload-manifest.v1 (bucket name with the account shown as <acct>, no credential).
EOF2
}

BUCKET="${SCHOLARCHAIN_ARTIFACTS_BUCKET:-}" REGION="${SCHOLARCHAIN_AWS_REGION:-}" PROFILE="${AWS_PROFILE:-}"
RUN_PREFIX="" BOOTSTRAP="" ARTIFACT_MANIFEST="" PRINCIPAL_ROLE="" APPROVAL="" MANIFEST_OUT="" EXECUTE=0
ER_POLICY="" ER_CONFIG="" SPARK_TEMPLATE="" DATASETS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --artifacts-bucket | --run-prefix | --region | --profile | --principal-role | --approval | --manifest-out | --bootstrap | --artifact-manifest | --er-policy | --er-config | --spark-config-template | --input-dataset)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "upload-emr-artifacts.sh" "$1 needs a value"
      fi
      case "$1" in
        --artifacts-bucket) BUCKET="$2" ;;
        --run-prefix) RUN_PREFIX="$2" ;;
        --region) REGION="$2" ;;
        --profile) PROFILE="$2" ;;
        --principal-role) PRINCIPAL_ROLE="$2" ;;
        --approval) APPROVAL="$2" ;;
        --manifest-out) MANIFEST_OUT="$2" ;;
        --bootstrap) BOOTSTRAP="$2" ;;
        --artifact-manifest) ARTIFACT_MANIFEST="$2" ;;
        --er-policy) ER_POLICY="$2" ;;
        --er-config) ER_CONFIG="$2" ;;
        --spark-config-template) SPARK_TEMPLATE="$2" ;;
        --input-dataset) DATASETS+=("$2") ;;
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
      sc_usage_exit "upload-emr-artifacts.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "upload-emr-artifacts.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
sc_require_tool python3
[[ -n "${RUN_PREFIX}" ]] || sc_usage_error "--run-prefix is required (for example run-20261115)"
[[ "${RUN_PREFIX}" =~ ^run-[a-z0-9][a-z0-9-]{1,27}$ ]] || sc_usage_error "--run-prefix must match ^run-[a-z0-9][a-z0-9-]{1,27}$ (for example run-20261115)"
[[ -n "${BUCKET}" ]] || sc_usage_error "--artifacts-bucket (or SCHOLARCHAIN_ARTIFACTS_BUCKET) is required: the artifacts bucket"
[[ "${BUCKET}" =~ ^scholarchain-([a-z0-9-]+)-([0-9]{12})-artifacts$ ]] || sc_usage_error "--artifacts-bucket must be scholarchain-<env>-<account>-artifacts"
BUCKET_ENV="${BASH_REMATCH[1]}"
BUCKET_ACCOUNT="${BASH_REMATCH[2]}"
sc_register_account "${BUCKET_ACCOUNT}"
[[ -n "${REGION}" ]] || sc_usage_error "region required: --region or SCHOLARCHAIN_AWS_REGION"
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
[[ "${#DATASETS[@]}" -ge 1 ]] || sc_usage_error "at least one --input-dataset LABEL=DIR is required"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_usage_error "--execute needs --profile (or AWS_PROFILE): the profile of the principal the deployer grants"
  [[ "${PROFILE}" =~ ^[A-Za-z0-9_.@-]+$ ]] || sc_usage_error "--profile must be a profile NAME (letters, digits, '_', '.', '@', '-')"
  [[ -n "${PRINCIPAL_ROLE}" ]] || sc_usage_error "--execute needs --principal-role NAME (the role of the profile, for example operator-pipeline)"
  [[ "${PRINCIPAL_ROLE}" =~ ^[a-z][a-z0-9-]{1,40}$ ]] || sc_usage_error "--principal-role must match ^[a-z][a-z0-9-]{1,40}$"
  [[ -n "${APPROVAL}" ]] || sc_usage_error "--execute needs --approval FILE: the human approval record"
  sc_require_tool aws "install the AWS CLI v2"
fi

if [[ "${EXECUTE}" -eq 1 ]]; then
  # The cheapest refusal first: no record, no upload, and not even a local scan.
  sc_step "approval-record"
  if [[ -L "${APPROVAL}" || ! -f "${APPROVAL}" ]]; then
    sc_refuse "${EX_REFUSED}" "the approval record does not exist (or is a link): write it after reviewing the dry run; nothing was uploaded"
  fi
fi

BOOTSTRAP="${BOOTSTRAP:-${REPO_ROOT}/scripts/emr/bootstrap.sh}"
ARTIFACT_MANIFEST="${ARTIFACT_MANIFEST:-${REPO_ROOT}/target/emr-artifacts/emr-artifact-manifest.json}"
STEP_MANIFEST="${REPO_ROOT}/infra/terraform/emr-step-programs.json"

EVIDENCE_DIR_REL="target/phase14/evidence/15a"
MANIFEST_OUT="${MANIFEST_OUT:-${REPO_ROOT}/${EVIDENCE_DIR_REL}/emr-upload-manifest.json}"
case "${MANIFEST_OUT}" in
  /*) ;;
  *) MANIFEST_OUT="${REPO_ROOT}/${MANIFEST_OUT}" ;;
esac
MANIFEST_OUT="$(sc_realpath "${MANIFEST_OUT}")"
sc_require_ignored "${MANIFEST_OUT}"
sc_check_outputs --entry "emr upload manifest" target "${REPO_ROOT}/target" "${MANIFEST_OUT}"
MANIFEST_OUT="${SC_CHECKED[0]}"

sc_step "artifact-scan"
sc_mktemp PLAN_FILE
sc_mktemp SCAN_OUT
SCAN_ARGS=(scan --repo-root "${REPO_ROOT}" --run-prefix "${RUN_PREFIX}" --out "${PLAN_FILE}" --bootstrap "${BOOTSTRAP}" --steps-dir "${REPO_ROOT}/scripts/emr"
  --step-manifest "${STEP_MANIFEST}" --artifact-manifest "${ARTIFACT_MANIFEST}" --max-input-bytes "${PIPELINE_MAX_INPUT_BYTES}")
[[ -z "${ER_POLICY}" ]] || SCAN_ARGS+=(--er-policy "${ER_POLICY}")
[[ -z "${ER_CONFIG}" ]] || SCAN_ARGS+=(--er-config "${ER_CONFIG}")
[[ -z "${SPARK_TEMPLATE}" ]] || SCAN_ARGS+=(--spark-config-template "${SPARK_TEMPLATE}")
for d in "${DATASETS[@]}"; do
  SCAN_ARGS+=(--input-dataset "${d}")
done
RC=0
python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" "${SCAN_ARGS[@]}" >"${SCAN_OUT}" || RC=$?
while IFS= read -r line; do
  printf '%s\n' "$(sc_redact "${line}")"
done <"${SCAN_OUT}"
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "the artifacts cannot be uploaded (see UPLOAD-REFUSED above); nothing was uploaded"
fi
FILE_COUNT="$(grep -c '^UPLOAD-FILE: ' "${SCAN_OUT}" || true)"
PLAN_SHA="$(sed -n 's/^PLAN-SHA256: //p' "${SCAN_OUT}" | head -n 1)"
ACCOUNT_SHA="$(printf '%s' "${BUCKET_ACCOUNT}" | python3 -I -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())')"

sc_step "next-values"
python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" hints --plan "${PLAN_FILE}" --bucket "${BUCKET}" --step-manifest "${STEP_MANIFEST}" | while IFS= read -r line; do
  printf '%s\n' "$(sc_redact "${line}")"
done
printf 'APPROVAL-LINE: APPROVED_ACTION=upload-emr-artifacts\n'
printf 'APPROVAL-LINE: APPROVED_PLAN_SHA256=%s\n' "${PLAN_SHA}"
printf 'APPROVAL-LINE: APPROVED_ACCOUNT_SHA256=%s\n' "${ACCOUNT_SHA}"
printf 'APPROVAL-LINE: APPROVED_REGION=%s\n' "${REGION}"

if [[ -n "${APPROVAL}" ]]; then
  sc_step "approval-record"
  RC=0
  OUT="$(python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" approval --file "${APPROVAL}" --plan-sha "${PLAN_SHA}" --account-id "${BUCKET_ACCOUNT}" --region "${REGION}")" || RC=$?
  printf '%s\n' "$(sc_redact "${OUT}")"
  if [[ "${RC}" -ne 0 ]]; then
    sc_refuse "${EX_REFUSED}" "the approval record does not match this plan; nothing was uploaded"
  fi
fi

AWS_ENV=(env "AWS_PROFILE=${PROFILE:-<profile-of-the-granted-principal>}" "AWS_REGION=${REGION}" AWS_PAGER=)
KEY_PREFIX="emr/${RUN_PREFIX}/"

if [[ "${EXECUTE}" -eq 0 ]]; then
  sc_step "upload-plan"
  sc_info "dry run: ${FILE_COUNT} file(s) would be uploaded to s3://${BUCKET}/${KEY_PREFIX}; no aws command is run and no file is written"
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Arn --output text
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api list-objects-v2 --region "${REGION}" --bucket "${BUCKET}" --prefix "${KEY_PREFIX}" --output json
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api get-object-attributes --region "${REGION}" --bucket "${BUCKET}" --key "<key-that-already-exists>" --object-attributes Checksum ObjectSize --output json
  sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" -- "${AWS_ENV[@]}" aws s3api put-object --region "${REGION}" --bucket "${BUCKET}" --key "<key-from-the-plan>" --body "<local-file>" --checksum-algorithm SHA256 --checksum-sha256 "<base64-sha256>" --if-none-match '*' --output json
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api head-object --region "${REGION}" --bucket "${BUCKET}" --key "<key-from-the-plan>" --checksum-mode ENABLED --output json
  sc_info "dry run: the manifest would be written to ${MANIFEST_OUT#"${REPO_ROOT}"/}"
  sc_result PASS "dry run: ${FILE_COUNT} file(s) planned under ${KEY_PREFIX}; nothing was uploaded" "${EX_OK}"
fi

# ---- execute -------------------------------------------------------------------------------------------------------------------
sc_step "identity"
sc_mktemp ID_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Account --output text || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "aws sts get-caller-identity failed (exit ${RC}); nothing was uploaded"
fi
ACCOUNT_ID="$(tr -d '[:space:]' <"${ID_FILE}")"
sc_register_account "${ACCOUNT_ID}"
[[ "${ACCOUNT_ID}" =~ ^[0-9]{12}$ ]] || sc_refuse "${EX_REFUSED}" "unexpected account identity output; nothing was uploaded"
[[ "${ACCOUNT_ID}" == "${BUCKET_ACCOUNT}" ]] || sc_refuse "${EX_REFUSED}" "the bucket belongs to another account than the profile; nothing was uploaded"
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${ID_FILE}" -- "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Arn --output text || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "aws sts get-caller-identity (Arn) failed (exit ${RC}); nothing was uploaded"
fi
CALLER_ARN="$(tr -d '[:space:]' <"${ID_FILE}")"
EXPECTED_ROLE="scholarchain-${BUCKET_ENV}-${PRINCIPAL_ROLE}"
if [[ ! "${CALLER_ARN}" =~ ^arn:aws:sts::[0-9]{12}:assumed-role/${EXPECTED_ROLE}/[A-Za-z0-9_=,.@-]+$ ]]; then
  sc_refuse "${EX_REFUSED}" "the profile is not an assumed-role session of ${EXPECTED_ROLE}; nothing was uploaded"
fi
sc_info "caller is a ${EXPECTED_ROLE} session of the bucket's account"

sc_step "preflight"
sc_mktemp LIST_FILE
sc_mktemp WORK_FILE
sc_mktemp EXISTING_OUT
sc_mktemp UNCHANGED_FILE
sc_mktemp RESULTS_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${LIST_FILE}" -- "${AWS_ENV[@]}" aws s3api list-objects-v2 --region "${REGION}" --bucket "${BUCKET}" --prefix "${KEY_PREFIX}" --output json || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "listing s3://${BUCKET}/${KEY_PREFIX} failed (exit ${RC}); nothing was uploaded"
fi
python3 -I "${SC_LIB_DIR}/upload_slice.py" existing --plan "${PLAN_FILE}" --listing "${LIST_FILE}" >"${EXISTING_OUT}" || sc_refuse "${EX_REFUSED}" "the bucket listing could not be read; nothing was uploaded"
grep -v '^EXISTING ' "${EXISTING_OUT}" || true
: >"${UNCHANGED_FILE}"
while read -r tag index key _rest; do
  [[ "${tag}" == "EXISTING" ]] || continue
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- "${AWS_ENV[@]}" aws s3api get-object-attributes --region "${REGION}" --bucket "${BUCKET}" --key "${key}" --object-attributes Checksum ObjectSize --output json || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${RC}")" "reading the attributes of an existing object failed (exit ${RC}); nothing was uploaded"
  fi
  if ! OUT="$(python3 -I "${SC_LIB_DIR}/upload_slice.py" compare --plan "${PLAN_FILE}" --index "${index}" --attributes "${WORK_FILE}")"; then
    printf '%s\n' "$(sc_redact "${OUT}")"
    sc_refuse "${EX_REFUSED}" "an object already exists with different content; nothing was uploaded"
  fi
  printf '%s\n' "$(sc_redact "${OUT}")"
  printf '%s\n' "${index}" >>"${UNCHANGED_FILE}"
done <"${EXISTING_OUT}"

sc_step "upload"
UPLOADED=0
while IFS=$'\t' read -r index path key b64; do
  [[ -n "${index}" ]] || continue
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" --capture "${WORK_FILE}" -- "${AWS_ENV[@]}" aws s3api put-object --region "${REGION}" --bucket "${BUCKET}" --key "${key}" --body "${path}" \
    --checksum-algorithm SHA256 --checksum-sha256 "${b64}" --if-none-match '*' --output json || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    sc_fail "$(sc_rc_to_exit "${RC}")" "put-object failed for ${key} (exit ${RC}) after ${UPLOADED} upload(s); a re-run skips the objects already stored with the same content"
  fi
  if ! OUT="$(python3 -I "${SC_LIB_DIR}/upload_slice.py" put --plan "${PLAN_FILE}" --index "${index}" --response "${WORK_FILE}" --results "${RESULTS_FILE}")"; then
    printf '%s\n' "$(sc_redact "${OUT}")"
    sc_fail "${EX_GATE}" "S3 reported a different SHA-256 than the local file for ${key}"
  fi
  printf '%s\n' "$(sc_redact "${OUT}")"
  UPLOADED=$((UPLOADED + 1))
done < <(python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" list --plan "${PLAN_FILE}" --skip-file "${UNCHANGED_FILE}")

sc_step "verify"
_verify_rows() {
  local state="$1" index key
  while IFS=$'\t' read -r index _path key _b64; do
    [[ -n "${index}" ]] || continue
    RC=0
    sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${WORK_FILE}" -- "${AWS_ENV[@]}" aws s3api head-object --region "${REGION}" --bucket "${BUCKET}" --key "${key}" --checksum-mode ENABLED --output json || RC=$?
    if [[ "${RC}" -ne 0 ]]; then
      sc_fail "$(sc_rc_to_exit "${RC}")" "head-object failed for ${key} (exit ${RC})"
    fi
    if ! OUT="$(python3 -I "${SC_LIB_DIR}/upload_slice.py" verify --plan "${PLAN_FILE}" --index "${index}" --head "${WORK_FILE}" --state "${state}" --results "${RESULTS_FILE}")"; then
      printf '%s\n' "$(sc_redact "${OUT}")"
      sc_fail "${EX_GATE}" "the stored object differs from the local file; the manifest is not written"
    fi
    printf '%s\n' "$(sc_redact "${OUT}")"
  done
}
_verify_rows unchanged < <(python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" list --plan "${PLAN_FILE}" --only-file "${UNCHANGED_FILE}")
_verify_rows uploaded < <(python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" list --plan "${PLAN_FILE}" --skip-file "${UNCHANGED_FILE}")

sc_step "manifest"
sc_mktemp MANIFEST_TMP
COMMIT="$(sc_git_head || true)"
BUCKET_LABEL="$(sc_redact "${BUCKET}")"
python3 -I "${SC_LIB_DIR}/upload_emr_artifacts.py" manifest --plan "${PLAN_FILE}" --results "${RESULTS_FILE}" --bucket-label "${BUCKET_LABEL}" --region "${REGION}" \
  --created-utc "$(sc_now)" --commit "${COMMIT:-unknown}" >"${MANIFEST_TMP}" || sc_fail "${EX_GATE}" "the manifest could not be built"
sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name target --within "${REPO_ROOT}/target" --path "$(dirname "${MANIFEST_OUT}")"
sc_safeio write-new --root "${REPO_ROOT}" "${MANIFEST_OUT}" <"${MANIFEST_TMP}"
printf 'UPLOAD-MANIFEST: %s\n' "${MANIFEST_OUT#"${REPO_ROOT}"/}"
printf 'UPLOAD-MANIFEST-SHA256: %s\n' "$(sc_sha256 "${MANIFEST_OUT}")"

sc_result PASS "${FILE_COUNT} file(s) verified under ${KEY_PREFIX} (${UPLOADED} uploaded, $(grep -c . "${UNCHANGED_FILE}" || true) unchanged); manifest ${MANIFEST_OUT#"${REPO_ROOT}"/}" "${EX_OK}"
