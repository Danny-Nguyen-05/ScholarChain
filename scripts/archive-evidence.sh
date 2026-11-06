#!/usr/bin/env bash
# Phase 13B evidence archive: gather local evidence into a NEW versioned directory, redacted, with an index.
# Real run on local files; the optional S3 upload is printed, never run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

usage() {
  cat <<'EOF2'
Usage: scripts/archive-evidence.sh --phase NN --label LABEL --include CATEGORY=PATH [--include ...]
         [--external-location NAME=LOCATION ...] [--dest-root DIR] [--tar] [--s3-prefix s3://bucket/key] [--region R] [--help]

Purpose
  Gather evidence into a new, versioned evidence directory: <dest-root>/phase-NN/evidence/<LABEL>/ (default
  dest-root docs/agent-runs). Categories: test-reports, plan-receipts (receipt and checksum sidecars only),
  image-digests, run-manifests, metric-exports, experiment-outputs, release-metadata. It writes INDEX.json (schema
  scholarchain.evidence-index.v1: commit, creation time, one entry per file with category, size, sha256 and status).

Rules
  * Never overwritten: the label directory must not exist (refused otherwise) and every file is created exclusively
    below a symlink-free directory chain (scripts/lib/safeio.py). Use a new label per run, for example 13b-v2.
  * Files of at most ARCHIVE_MAX_COPY_BYTES (1 MiB) that are UTF-8 text are COPIED after redaction: account IDs
    (12-digit runs), the values of secret-named environment variables, registered private values, private-key blocks,
    access key IDs, any generic secret, token, password, api-key or credential assignment (api_token = ..., client_secret: ...,
    password=..., api_key: ..., JSON "secret": "..."; numbers, booleans and checksums are left intact) and Bearer or
    Authorization values. The index records both the
    original sha256 and the archived (redacted) sha256.
  * Files larger than that, and binary files (they cannot be redacted), are NOT copied: the index records their sha256,
    size and the REQUIRED external location (an s3:// URI, drive:<text> or a Drive URL) given with
    --external-location NAME=LOCATION (NAME is the file name, its path below the source, or category/path). A
    file without one refuses the whole run before anything is written.
  * Private material is refused outright, never archived: Terraform state, plan binaries (*.tfplan), raw plan JSON and
    plan text, variable files (*.tfvars and *.tfvars.json), dotenv files, private keys (*.pem, *.key, id_*) and any file
    whose name contains the word for login material. Only plan receipts (*.tfplan.receipt.json) and checksum
    sidecars (*.tfplan.sha256) are accepted from the plan family.
  * Symlinks in a source are refused. macOS metadata files (names starting "._", and .DS_Store) are skipped and listed
    in the index; they never enter the directory or a tar. (Hadoop's own ._SUCCESS.crc files are skipped the same way.)
  * --tar also builds <dest>.tar.gz next to the directory, with Python tarfile (no owner names, fixed mtime, no
    "._" member), and verifies the listing with python tarfile and with `tar -tzf` under COPYFILE_DISABLE=1.
  * After writing, the directory is re-read: every copied file matches its recorded sha256 and no text holds an
    account id, a registered secret or a credential shape (exit 4 otherwise).

Inputs
  --phase NN        two digits         --label LABEL    letters, digits, '.', '_' and '-' (required)
  --include CATEGORY=PATH   a file or a directory (repeatable)       --dest-root DIR   an existing directory
  --external-location NAME=LOCATION   for each file that is not copied
  --s3-prefix s3://bucket/key   DRY RUN ONLY: prints the `aws s3 cp ... --checksum-algorithm SHA256` command that a
                    human could run later; nothing is ever uploaded by this script. --region R is printed in it.
  Environment variable names: SCHOLARCHAIN_REPO_ROOT, SCHOLARCHAIN_TF_PRIVATE_VARS (its values are redacted).

Modes
  Real run on local files (no cloud call). There is no --execute: the S3 part is a printed command only.

Human approval points (plan Section 7.3)
  None for the local archive. Uploading to S3 or Drive is a separate human action after reviewing the index; large
  originals stay in Drive or S3 with their recorded sha256.

Exit codes
  0    archive written and verified
  2    usage error
  3    refused: existing label directory, private material, symlink, missing source, missing external location
  4    verification failed (tar listing with metadata members, redaction check, sha256 mismatch)
  5    an underlying command failed
  124  a command timed out

Evidence produced
  STEP: markers, ARCHIVE-* lines and one RESULT: line on stdout; the evidence directory with INDEX.json (and the tar).
EOF2
}

PHASE="" LABEL="" DEST_ROOT="" MAKE_TAR=0 S3_PREFIX="" REGION=""
INCLUDES=() EXTERNALS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase | --label | --include | --external-location | --dest-root | --s3-prefix | --region)
      if [[ $# -lt 2 ]]; then
        sc_usage_exit "archive-evidence.sh" "$1 needs a value"
      fi
      case "$1" in
        --phase) PHASE="$2" ;;
        --label) LABEL="$2" ;;
        --include) INCLUDES+=("$2") ;;
        --external-location) EXTERNALS+=("$2") ;;
        --dest-root) DEST_ROOT="$2" ;;
        --s3-prefix) S3_PREFIX="$2" ;;
        --region) REGION="$2" ;;
      esac
      shift 2
      ;;
    --tar)
      MAKE_TAR=1
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      sc_usage_exit "archive-evidence.sh" "unknown argument: $1 (see --help)"
      ;;
  esac
done

sc_init "archive-evidence.sh"
# The S3 command is only ever printed: the whole script runs in dry-run mode for cloud commands.
DRY_RUN=1
sc_banner "local-archive"

sc_step "archive-inputs"
sc_require_tool python3
[[ "${PHASE}" =~ ^[0-9]{2}$ ]] || sc_usage_error "--phase must be two digits (for example 13)"
[[ "${LABEL}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$ ]] || sc_usage_error "--label is required: letters, digits, '.', '_' and '-' (for example 13b-v1)"
[[ ${#INCLUDES[@]} -gt 0 ]] || sc_usage_error "at least one --include CATEGORY=PATH is required"
if [[ -n "${S3_PREFIX}" ]]; then
  [[ "${S3_PREFIX}" =~ ^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9](/.*)?$ ]] || sc_usage_error "--s3-prefix must be s3://bucket[/key]"
fi
if [[ -n "${REGION}" ]]; then
  sc_region_valid "${REGION}" || sc_usage_error "--region is not a valid AWS region name"
fi
DEST_ROOT="${DEST_ROOT:-${REPO_ROOT}/docs/agent-runs}"
[[ -d "${DEST_ROOT}" ]] || sc_refuse "${EX_REFUSED}" "the destination root does not exist: ${DEST_ROOT}"
DEST_ROOT="$(cd "${DEST_ROOT}" && pwd -P)"
DEST="${DEST_ROOT}/phase-${PHASE}/evidence/${LABEL}"
COMMIT="$(sc_git_head || true)"
_sc_refresh_redact_file

sc_step "archive-scan"
PLAN_FILE=""
sc_mktemp PLAN_FILE
scan_args=()
for item in "${INCLUDES[@]}"; do scan_args+=(--include "${item}"); done
if [[ ${#EXTERNALS[@]} -gt 0 ]]; then
  for item in "${EXTERNALS[@]}"; do scan_args+=(--external-location "${item}"); done
fi
RC=0
OUT="$(python3 -I "${SC_LIB_DIR}/archive.py" scan --out "${PLAN_FILE}" --max-copy-bytes "${ARCHIVE_MAX_COPY_BYTES}" "${scan_args[@]}")" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  while IFS= read -r line; do sc_err "${line}"; done <<<"${OUT}"
  sc_refuse "${EX_REFUSED}" "the archive was refused before anything was written (see ARCHIVE-REFUSED above)"
fi
printf '%s\n' "${OUT}"

sc_step "archive-write"
RC=0
OUT="$(python3 -I "${SC_LIB_DIR}/archive.py" write --plan "${PLAN_FILE}" --dest-root "${DEST_ROOT}" --dest "${DEST}" --phase "${PHASE}" \
  --label "${LABEL}" --commit "${COMMIT:-unknown}" --created-utc "$(sc_now)" --redact-file "${SC_REDACT_FILE}")" || RC=$?
if [[ "${RC}" -ne 0 ]]; then
  sc_refuse "${EX_REFUSED}" "${OUT}"
fi
printf '%s\n' "${OUT}"
printf 'ARCHIVE-INDEX: %s/INDEX.json\n' "${DEST}"

TAR_FILE=""
if [[ "${MAKE_TAR}" -eq 1 ]]; then
  sc_step "archive-tar"
  TAR_FILE="${DEST}.tar.gz"
  RC=0
  OUT="$(COPYFILE_DISABLE=1 python3 -I "${SC_LIB_DIR}/archive.py" tar --dest "${DEST}" --out "${TAR_FILE}")" || RC=$?
  if [[ "${RC}" -ne 0 ]]; then
    printf '%s\n' "${OUT}"
    sc_fail "${EX_GATE}" "the tar archive could not be built cleanly: ${OUT}"
  fi
  printf '%s\n' "${OUT}"
fi

sc_step "archive-verify"
RC=0
OUT="$(python3 -I "${SC_LIB_DIR}/archive.py" verify --dest "${DEST}" --redact-file "${SC_REDACT_FILE}")" || RC=$?
printf '%s\n' "${OUT}"
if [[ "${RC}" -ne 0 ]]; then
  sc_fail "${EX_GATE}" "the written evidence directory failed verification"
fi

if [[ -n "${S3_PREFIX}" ]]; then
  sc_step "archive-s3-plan"
  S3_BASE="${S3_PREFIX%/}/phase-${PHASE}/evidence"
  REGION_ARGS=()
  [[ -z "${REGION}" ]] || REGION_ARGS=(--region "${REGION}")
  sc_info "DRY RUN ONLY: nothing is uploaded; a human may run these commands after reviewing the index"
  sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" -- aws s3 cp "${DEST}" "${S3_BASE}/${LABEL}/" --recursive --checksum-algorithm SHA256 ${REGION_ARGS[@]+"${REGION_ARGS[@]}"}
  if [[ -n "${TAR_FILE}" ]]; then
    printf 'ARCHIVE-TAR-SHA256: %s %s\n' "$(sc_sha256 "${TAR_FILE}")" "$(basename "${TAR_FILE}")"
    sc_exec --cloud --timeout "${TIMEOUT_S3_UPLOAD_SECONDS}" -- aws s3 cp "${TAR_FILE}" "${S3_BASE}/$(basename "${TAR_FILE}")" --checksum-algorithm SHA256 ${REGION_ARGS[@]+"${REGION_ARGS[@]}"}
  fi
fi

sc_step "archive-complete"
sc_result PASS "evidence directory ${DEST} written and verified${TAR_FILE:+; tar ${TAR_FILE}}" "${EX_OK}"
