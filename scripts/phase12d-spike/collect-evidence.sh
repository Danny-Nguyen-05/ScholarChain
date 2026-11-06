#!/usr/bin/env bash
# Phase 12D spike - evidence collection BEFORE destroy.
# Downloads s3://<bucket>/results/ and s3://<bucket>/emr-logs/ into a local
# evidence directory, verifies the step-3 results manifest (tar sha256, then
# every file inside the tar), and writes a sha256 manifest of everything
# downloaded. Bounded: each download is tried at most 3 times; no polling.
#
# Usage: collect-evidence.sh --bucket <name> --dest <dir> [--region us-east-2]
# Exit: 0 ok, 3 manifest mismatch or unsafe tarball, 4 download failed, 64 usage.
set -euo pipefail

BUCKET="" DEST="" REGION="us-east-2"
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket) BUCKET="${2:-}"; shift 2 ;;
    --dest) DEST="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
[ -n "$BUCKET" ] && [ -n "$DEST" ] || { echo "--bucket and --dest are required" >&2; exit 64; }
case "$BUCKET" in scholarchain-spike-emr-*) ;; *) echo "bucket must start with scholarchain-spike-emr-" >&2; exit 64 ;; esac

if command -v sha256sum >/dev/null 2>&1; then
  SHA=(sha256sum)
else
  SHA=(shasum -a 256)
fi
hash_of() { "${SHA[@]}" "$1" | awk '{print $1}'; }

mkdir -p "$DEST/results" "$DEST/emr-logs"

download() { # prefix localdir
  local n=1
  while [ "$n" -le 3 ]; do
    if aws s3 cp "s3://${BUCKET}/$1" "$2" --recursive --region "$REGION" --only-show-errors; then
      return 0
    fi
    n=$((n + 1))
  done
  return 1
}

download "results/" "$DEST/results" || { echo "results download failed after 3 attempts" >&2; exit 4; }
download "emr-logs/" "$DEST/emr-logs" || { echo "emr-logs download failed after 3 attempts" >&2; exit 4; }

TAR="$DEST/results/scholarchain-spike-results.tar.gz"
MAN="$DEST/results/results-manifest.sha256"
[ -f "$TAR" ] && [ -f "$MAN" ] || { echo "results tarball or manifest missing" >&2; exit 3; }

expected="$(awk '$2=="scholarchain-spike-results.tar.gz"{print $1}' "$MAN")"
actual="$(hash_of "$TAR")"
if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
  echo "RESULTS MANIFEST MISMATCH: expected '${expected}' got '${actual}'" >&2
  exit 3
fi
echo "results tarball sha256 verified: ${actual}"

EXTRACT="$DEST/results-extracted"
rm -rf "$EXTRACT"; mkdir -p "$EXTRACT"
# Item 31 (carried 12D finding): macOS bsdtar treats Hadoop's real ._SUCCESS.crc checksum files as AppleDouble
# metadata ("Failed to restore metadata", exit 1, the file is not extracted), so `tar -xzf` cannot be used here.
# Python tarfile extracts every member verbatim, refusing absolute paths, "..", links and special files.
# COPYFILE_DISABLE=1 also stops any tar this script or its callers start from adding "._" members to NEW archives.
export COPYFILE_DISABLE=1
python3 -I - "$TAR" "$EXTRACT" <<'PY' || { echo "results tarball could not be extracted safely" >&2; exit 3; }
import os
import sys
import tarfile

archive_path, dest = sys.argv[1], os.path.realpath(sys.argv[2])
with tarfile.open(archive_path, "r:gz") as archive:
    members = archive.getmembers()
    for member in members:
        target = os.path.realpath(os.path.join(dest, member.name))
        if os.path.isabs(member.name) or ".." in member.name.split("/") or not (target == dest or target.startswith(dest + os.sep)):
            raise SystemExit("unsafe member path: %s" % member.name)
        if not (member.isreg() or member.isdir()):
            raise SystemExit("unsupported member type: %s" % member.name)
    for member in members:
        target = os.path.join(dest, member.name)
        if member.isdir():
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with archive.extractfile(member) as source, open(target, "xb") as out:
            out.write(source.read())
PY
if [ ! -f "$EXTRACT/files-manifest.sha256" ]; then echo "files-manifest.sha256 missing inside the tarball" >&2; exit 3; fi
count=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  want="${line%%  *}"; rel="${line#*  }"
  [ -f "$EXTRACT/$rel" ] || { echo "listed file missing: $rel" >&2; exit 3; }
  got="$(hash_of "$EXTRACT/$rel")"
  [ "$got" = "$want" ] || { echo "FILE MISMATCH: $rel" >&2; exit 3; }
  count=$((count + 1))
done < "$EXTRACT/files-manifest.sha256"
echo "verified ${count} extracted file(s)"

# manifest of everything downloaded or extracted (excluding the manifest itself)
OUT="$DEST/evidence-manifest.sha256"
rm -f "$OUT"
( cd "$DEST" && find results emr-logs results-extracted -type f -print | LC_ALL=C sort | while IFS= read -r f; do
    printf '%s  %s\n' "$("${SHA[@]}" "$f" | awk '{print $1}')" "$f"
  done ) > "$OUT"
echo "wrote $OUT ($(wc -l < "$OUT" | tr -d ' ') files)"
