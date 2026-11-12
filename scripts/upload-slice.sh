#!/usr/bin/env bash
# Phase 14C slice upload: put a COMPLETED local Phase 6 export (its Parquet tables and manifests) into the curated bucket under
# <run_prefix>/ with the operator-loader role, with checksums verified and recorded. Dry run by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/upload-slice.sh --export-dir DIR --run-prefix run-YYYYMMDD --bucket CURATED-BUCKET --region REGION
                               [--profile PROFILE] [--manifest-out PATH] [--execute] [--help]

Purpose
  Upload the Parquet tables and the manifests of a completed local Phase 6 export to the curated S3 bucket, under the key
  prefix <run-prefix>/ (the only prefix the operator-loader role may write in that bucket: deployer/operator_roles.tf).
  What is uploaded, relative to the export directory (the key is <run-prefix>/<relative path>):
    * every *.parquet file below nodes/, edges/, metrics/, path-evidence/ and semantic-summaries/;
    * run-manifest.json, run-metadata.json, counters.json and _SCHOLARCHAIN_SPARK_COMPLETE;
    * load-manifests/*.json.
  Not uploaded (counted as EXPORT-SKIPPED): Spark and Hadoop sidecars (_SUCCESS, *.crc, dot files), neptune-opencypher-csv/ (the
  graph loader reads it from the graph bucket), plans/, integrity/, event logs. Any other file inside the table directories refuses.

Usage errors (exit 2, nothing is read, nothing is uploaded)
  * a missing or invalid run prefix (^run-[a-z0-9][a-z0-9-]{1,27}$, the same rule as the deployer's operator_run_prefix);
  * a missing bucket, or a bucket name that is not scholarchain-<env>-<account>-curated; a missing or invalid region; --execute
    without --profile; an unknown option or an option without its value.

Refusals (exit 3, nothing is uploaded; the checks run before the first PutObject)
  * a bucket whose account is not the one the profile belongs to;
  * a caller that is not the operator-loader role (assumed-role/scholarchain-<env>-operator-loader/...);
  * a non-completed export: missing run manifest, run metadata, counters, load manifests or completion marker, a marker that
    does not equal sha256(run-manifest + LF + run-metadata) + LF, no Parquet file, or manifests that name different runs;
  * a key outside <run-prefix>/ (an empty or dot segment, or characters outside A-Za-z0-9._=:+@/-; the one exception is the exact
    escape %3A that Spark writes for ':' in run_id=run%3A<uuid>, kept as that literal text; any other '%' such as %20, %2F, %3a
    or a bare '%' is refused), a symbolic link anywhere;
  * a file over 5 GiB, more than 5000 files, or more than 20 GiB in total (this tool uses single PutObject calls);
  * an object that ALREADY exists under a planned key with different content (size or SHA-256), or with no SHA-256 checksum:
    nothing is overwritten, ever. An existing object with the same SHA-256 and size is UNCHANGED and skipped, so a re-run after
    a failure is safe;
  * an existing --manifest-out (it is evidence and is never overwritten).

Dry run (default): scans and hashes the local files and prints the plan, one line per file
  (UPLOAD-FILE: <n> path=<relative path> key=<s3 key> bytes=<bytes> sha256=<hex>) with the totals (EXPORT-RUN:), and prints the
  aws commands --execute would run (DRY-RUN CMD:). It makes no aws call and writes no file.

--execute: sts get-caller-identity (role and account check); s3api list-objects-v2 under the prefix and get-object-attributes of
  every key that already exists (the refusals above); then for each new file
    aws s3api put-object --checksum-algorithm SHA256 --checksum-sha256 <base64 of the local sha256> --if-none-match '*'
  (S3 itself rejects a body that does not match the declared SHA-256 and a key that appeared in the meantime; --if-none-match needs
  AWS CLI v2.17 or newer); then s3api head-object --checksum-mode ENABLED of every key, which must report the local size and
  SHA-256; then the manifest is written (key, bytes, sha256, version id, status uploaded|unchanged per file).

Inputs
  --export-dir DIR      a completed Phase 6 export directory (local)           --run-prefix P   the run folder, for example run-20261115
  --bucket NAME         the curated bucket (or SCHOLARCHAIN_CURATED_BUCKET)    --region R       (or SCHOLARCHAIN_AWS_REGION)
  --profile P           the operator-loader profile (or AWS_PROFILE); required with --execute. Credentials are never read,
                        printed or logged: only the profile NAME reaches the aws command.
  --manifest-out PATH   default target/phase14/evidence/14c/upload-manifest.json; must lie below target/ (git-ignored) and not exist
  --execute             upload (see above); without it nothing happens
  Environment variable names: SCHOLARCHAIN_AWS_REGION, SCHOLARCHAIN_CURATED_BUCKET, AWS_PROFILE, SCHOLARCHAIN_REPO_ROOT.

Human approval points
  Uploading is a live cloud mutation of the data lake: --execute follows the recorded Phase 14C gate and the operator-loader MFA
  session (deployer/README.md, "Replan W5a"). The dry run needs no approval.

Exit codes
  0    dry run printed; or upload completed and verified, manifest written
  2    usage error
  3    refused (see above); nothing was uploaded
  4    verification failed (stored size or SHA-256 differs from the local file); the manifest is NOT written
  5    an aws command failed (a re-run skips the objects that were already stored with the same content)
  124  a command timed out

Evidence produced
  STEP: markers, EXPORT-RUN, EXPORT-SKIPPED, UPLOAD-FILE, UNCHANGED, UPLOADED, VERIFIED lines and one RESULT: line on stdout;
  with --execute the manifest scholarchain.upload-manifest.v1 (bucket name with the account shown as <acct>, no credential).
EOF2
}

EXPORT_DIR="" RUN_PREFIX="" BUCKET="${SCHOLARCHAIN_CURATED_BUCKET:-}" REGION="${SCHOLARCHAIN_AWS_REGION:-}" PROFILE="${AWS_PROFILE:-}"
MANIFEST_OUT="" EXECUTE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --export-dir | --run-prefix | --bucket | --region | --profile | --manifest-out)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "upload-slice.sh" "$1 needs a value"
      fi
      case "$1" in
        --export-dir) EXPORT_DIR="$2" ;;
        --run-prefix) RUN_PREFIX="$2" ;;
        --bucket) BUCKET="$2" ;;
        --region) REGION="$2" ;;
        --profile) PROFILE="$2" ;;
        --manifest-out) MANIFEST_OUT="$2" ;;
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
      sc_usage_exit "upload-slice.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "upload-slice.sh"
if [[ "${EXECUTE}" -eq 1 ]]; then
  DRY_RUN=0
  sc_banner "execute"
else
  DRY_RUN=1
  sc_banner "dry-run"
fi

sc_step "inputs"
sc_require_tool python3
[[ -n "${EXPORT_DIR}" ]] || sc_usage_error "--export-dir is required"
[[ -n "${RUN_PREFIX}" ]] || sc_usage_error "--run-prefix is required (for example run-20261115)"
[[ "${RUN_PREFIX}" =~ ^run-[a-z0-9][a-z0-9-]{1,27}$ ]] || sc_usage_error "--run-prefix must match ^run-[a-z0-9][a-z0-9-]{1,27}$ (for example run-20261115)"
[[ -n "${BUCKET}" ]] || sc_usage_error "--bucket (or SCHOLARCHAIN_CURATED_BUCKET) is required: the curated bucket"
[[ "${BUCKET}" =~ ^scholarchain-[a-z0-9-]+-([0-9]{12})-curated$ ]] || sc_usage_error "--bucket must be scholarchain-<env>-<account>-curated"
BUCKET_ACCOUNT="${BASH_REMATCH[1]}"
sc_register_account "${BUCKET_ACCOUNT}"
[[ -n "${REGION}" ]] || sc_usage_error "region required: --region or SCHOLARCHAIN_AWS_REGION"
sc_region_valid "${REGION}" || sc_usage_error "region '${REGION}' is not a valid AWS region name"
if [[ "${EXECUTE}" -eq 1 ]]; then
  [[ -n "${PROFILE}" ]] || sc_usage_error "--execute needs --profile (or AWS_PROFILE): the operator-loader profile"
  [[ "${PROFILE}" =~ ^[A-Za-z0-9_.@-]+$ ]] || sc_usage_error "--profile must be a profile NAME (letters, digits, '_', '.', '@', '-')"
  sc_require_tool aws "install the AWS CLI v2"
fi
[[ -d "${EXPORT_DIR}" ]] || sc_refuse "${EX_REFUSED}" "the export directory does not exist: $(basename "${EXPORT_DIR}")"
EXPORT_ABS="$(cd "${EXPORT_DIR}" && pwd -P)"

EVIDENCE_DIR_REL="target/phase14/evidence/14c"
MANIFEST_OUT="${MANIFEST_OUT:-${REPO_ROOT}/${EVIDENCE_DIR_REL}/upload-manifest.json}"
case "${MANIFEST_OUT}" in
  /*) ;;
  *) MANIFEST_OUT="${REPO_ROOT}/${MANIFEST_OUT}" ;;
esac
MANIFEST_OUT="$(sc_realpath "${MANIFEST_OUT}")" # an alias of the repository root (for example /var versus /private/var) is accepted
sc_require_ignored "${MANIFEST_OUT}"
sc_check_outputs --entry "upload manifest" target "${REPO_ROOT}/target" "${MANIFEST_OUT}"
MANIFEST_OUT="${SC_CHECKED[0]}"

sc_step "export-scan"
sc_mktemp PLAN_FILE
sc_mktemp SCAN_OUT
RC=0
python3 -I "${SC_LIB_DIR}/upload_slice.py" scan --export "${EXPORT_ABS}" --prefix "${RUN_PREFIX}" --out "${PLAN_FILE}" >"${SCAN_OUT}" || RC=$?
while IFS= read -r line; do
  printf '%s\n' "$(sc_redact "${line}")"
done <"${SCAN_OUT}"
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "the export cannot be uploaded (see UPLOAD-REFUSED above); nothing was uploaded"
fi
FILE_COUNT="$(grep -c '^UPLOAD-FILE: ' "${SCAN_OUT}" || true)"
EXPORT_LINE="$(grep '^EXPORT-RUN: ' "${SCAN_OUT}" | head -n 1)"

AWS_ENV=(env "AWS_PROFILE=${PROFILE:-<operator-loader-profile>}" "AWS_REGION=${REGION}" AWS_PAGER=)

if [[ "${EXECUTE}" -eq 0 ]]; then
  sc_step "upload-plan"
  sc_info "dry run: ${FILE_COUNT} file(s) would be uploaded to s3://${BUCKET}/${RUN_PREFIX}/ (${EXPORT_LINE#EXPORT-RUN: }); no aws command is run and no file is written"
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws sts get-caller-identity --region "${REGION}" --query Arn --output text
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api list-objects-v2 --region "${REGION}" --bucket "${BUCKET}" --prefix "${RUN_PREFIX}/" --output json
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api get-object-attributes --region "${REGION}" --bucket "${BUCKET}" --key "<key-that-already-exists>" --object-attributes Checksum ObjectSize --output json
  sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" -- "${AWS_ENV[@]}" aws s3api put-object --region "${REGION}" --bucket "${BUCKET}" --key "<key-from-the-plan>" --body "<local-file>" --checksum-algorithm SHA256 --checksum-sha256 "<base64-sha256>" --if-none-match '*' --output json
  sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" -- "${AWS_ENV[@]}" aws s3api head-object --region "${REGION}" --bucket "${BUCKET}" --key "<key-from-the-plan>" --checksum-mode ENABLED --output json
  sc_info "dry run: the manifest would be written to ${MANIFEST_OUT#"${REPO_ROOT}"/}"
  sc_result PASS "dry run: ${FILE_COUNT} file(s) planned under ${RUN_PREFIX}/; nothing was uploaded" "${EX_OK}"
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
if [[ ! "${CALLER_ARN}" =~ ^arn:aws:sts::[0-9]{12}:assumed-role/scholarchain-[a-z0-9-]+-operator-loader/[A-Za-z0-9_=,.@-]+$ ]]; then
  sc_refuse "${EX_REFUSED}" "the profile is not an operator-loader session (assumed-role/scholarchain-<env>-operator-loader/...); nothing was uploaded"
fi
sc_info "caller is an operator-loader session of the bucket's account"

sc_step "preflight"
sc_mktemp LIST_FILE
sc_mktemp WORK_FILE
sc_mktemp EXISTING_OUT
sc_mktemp UNCHANGED_FILE
sc_mktemp RESULTS_FILE
RC=0
sc_exec --cloud --timeout "${TIMEOUT_AWS_SECONDS}" --capture "${LIST_FILE}" -- "${AWS_ENV[@]}" aws s3api list-objects-v2 --region "${REGION}" --bucket "${BUCKET}" --prefix "${RUN_PREFIX}/" --output json || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "$(sc_rc_to_exit "${RC}")" "listing s3://${BUCKET}/${RUN_PREFIX}/ failed (exit ${RC}); nothing was uploaded"
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
while IFS=$'\t' read -r index rel key b64; do
  [[ -n "${index}" ]] || continue
  RC=0
  sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" --capture "${WORK_FILE}" -- "${AWS_ENV[@]}" aws s3api put-object --region "${REGION}" --bucket "${BUCKET}" --key "${key}" --body "${EXPORT_ABS}/${rel}" \
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
done < <(python3 -I "${SC_LIB_DIR}/upload_slice.py" list --plan "${PLAN_FILE}" --skip-file "${UNCHANGED_FILE}")

sc_step "verify"
_verify_rows() {
  local state="$1" index key
  while IFS=$'\t' read -r index _rel key _b64; do
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
_verify_rows unchanged < <(python3 -I "${SC_LIB_DIR}/upload_slice.py" list --plan "${PLAN_FILE}" --only-file "${UNCHANGED_FILE}")
_verify_rows uploaded < <(python3 -I "${SC_LIB_DIR}/upload_slice.py" list --plan "${PLAN_FILE}" --skip-file "${UNCHANGED_FILE}")

sc_step "manifest"
sc_mktemp MANIFEST_TMP
COMMIT="$(sc_git_head || true)"
BUCKET_LABEL="$(sc_redact "${BUCKET}")"
python3 -I "${SC_LIB_DIR}/upload_slice.py" manifest --plan "${PLAN_FILE}" --results "${RESULTS_FILE}" --bucket-label "${BUCKET_LABEL}" --region "${REGION}" \
  --created-utc "$(sc_now)" --commit "${COMMIT:-unknown}" >"${MANIFEST_TMP}" || sc_fail "${EX_GATE}" "the manifest could not be built"
sc_safeio ensure-dir --root "${REPO_ROOT}" --within-name target --within "${REPO_ROOT}/target" --path "$(dirname "${MANIFEST_OUT}")"
sc_safeio write-new --root "${REPO_ROOT}" "${MANIFEST_OUT}" <"${MANIFEST_TMP}"
printf 'UPLOAD-MANIFEST: %s\n' "${MANIFEST_OUT#"${REPO_ROOT}"/}"
printf 'UPLOAD-MANIFEST-SHA256: %s\n' "$(sc_sha256 "${MANIFEST_OUT}")"

sc_result PASS "${FILE_COUNT} file(s) verified under ${RUN_PREFIX}/ (${UPLOADED} uploaded, $(grep -c . "${UNCHANGED_FILE}" || true) unchanged); manifest ${MANIFEST_OUT#"${REPO_ROOT}"/}" "${EX_OK}"
