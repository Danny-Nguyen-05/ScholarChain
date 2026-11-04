#!/usr/bin/env bash
# Primary-node collect step: tar results + outputs (probe JSON lives in
# results/) from the EFS mount, write a sha256 manifest, and upload both to
# s3://<bucket>/results/. Refuses to upload more than --max-bytes (default
# 64 MiB) so the S3 request bound in scripts/phase12d-spike stays valid.
#
# Injectable: SC_MNT (default /mnt/scholarchain), SC_WORK.
set -euo pipefail
MNT="${SC_MNT:-/mnt/scholarchain}"
BUCKET="" REGION="" MAX_BYTES=67108864
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket) BUCKET="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    --max-bytes) MAX_BYTES="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
[ -n "$BUCKET" ] && [ -n "$REGION" ] || { echo "--bucket and --region are required" >&2; exit 64; }
case "$MAX_BYTES" in ''|*[!0-9]*) echo "--max-bytes must be an integer" >&2; exit 64 ;; esac

WORK="${SC_WORK:-$(mktemp -d)}"
mkdir -p "$WORK"
TAR_NAME="scholarchain-spike-results.tar.gz"

[ -d "$MNT/results" ] || { echo "no $MNT/results; nothing to collect" >&2; exit 2; }
mkdir -p "$MNT/outputs"

# per-file manifest (paths relative to the tar root), carried inside the tar
( cd "$MNT" && find results outputs -type f -print | LC_ALL=C sort | while IFS= read -r f; do
    printf '%s  %s\n' "$(sha256sum "$f" | cut -d' ' -f1)" "$f"
  done ) > "$WORK/files-manifest.sha256"

tar -czf "$WORK/$TAR_NAME" -C "$MNT" results outputs -C "$WORK" files-manifest.sha256
size="$(wc -c < "$WORK/$TAR_NAME" | tr -d ' ')"
if [ "$size" -gt "$MAX_BYTES" ]; then
  echo "results tarball is $size bytes, over the $MAX_BYTES cap; not uploading" >&2
  exit 5
fi
printf '%s  %s\n' "$(sha256sum "$WORK/$TAR_NAME" | cut -d' ' -f1)" "$TAR_NAME" > "$WORK/results-manifest.sha256"

aws s3 cp "$WORK/$TAR_NAME" "s3://${BUCKET}/results/${TAR_NAME}" --region "$REGION" --only-show-errors
aws s3 cp "$WORK/results-manifest.sha256" "s3://${BUCKET}/results/results-manifest.sha256" --region "$REGION" --only-show-errors
echo "collected $size bytes to s3://${BUCKET}/results/"
