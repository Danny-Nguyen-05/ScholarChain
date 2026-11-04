#!/usr/bin/env bash
# Phase 12D spike - after-destroy inventory. Read-only AWS describes; the
# judgement is made by inventory_eval.py (stdlib) and printed as JSON.
#
# Usage: inventory.sh --account <12 digits> [--region us-east-2] [--out file.json]
# Exit: 0 nothing billable remains (a KMS key in PendingDeletion is expected),
#       2 billable resource remains, 3 inconclusive (a describe failed), 64 usage.
set -uo pipefail

ACCOUNT="" REGION="us-east-2" OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="${2:-}"; shift 2 ;;
    --region) REGION="${2:-}"; shift 2 ;;
    --out) OUT="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
case "$ACCOUNT" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) echo "--account must be 12 digits" >&2; exit 64 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STACK="spike-emr"
BUCKET="scholarchain-spike-emr-${ACCOUNT}-${REGION}"
: > "$TMP/errors.txt"

run() { # name -- aws args...
  local name="$1"; shift
  if ! "$@" > "$TMP/${name}.json" 2> "$TMP/${name}.err"; then
    echo "${name}" >> "$TMP/errors.txt"
  fi
}

TAGF="Name=tag:scholarchain:stack,Values=${STACK}"
run tagging aws resourcegroupstaggingapi get-resources --tag-filters "Key=scholarchain:stack,Values=${STACK}" --region "$REGION" --output json
run emr aws emr list-clusters --active --region "$REGION" --output json
run nat aws ec2 describe-nat-gateways --filter "$TAGF" --region "$REGION" --output json
run eip aws ec2 describe-addresses --filters "$TAGF" --region "$REGION" --output json
run eni aws ec2 describe-network-interfaces --filters "$TAGF" --region "$REGION" --output json
run instances aws ec2 describe-instances --filters "$TAGF" --region "$REGION" --output json
run volumes aws ec2 describe-volumes --filters "$TAGF" --region "$REGION" --output json
run efs aws efs describe-file-systems --region "$REGION" --output json
run aliases aws kms list-aliases --region "$REGION" --output json

# KMS: describe every key seen through the tagging API or an alias (at most 10).
n=0
for kid in $(python3 -I "$HERE/inventory_eval.py" key-ids --dir "$TMP" 2>/dev/null | head -n 10); do
  n=$((n + 1))
  run "kms-describe-${n}" aws kms describe-key --key-id "$kid" --region "$REGION" --output json
done

# S3: existence of the one expected bucket.
if aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" > "$TMP/head-bucket.out" 2> "$TMP/head-bucket.err"; then
  echo 0 > "$TMP/head-bucket.rc"
else
  echo $? > "$TMP/head-bucket.rc"
fi

python3 -I "$HERE/inventory_eval.py" evaluate --dir "$TMP" --account "$ACCOUNT" --region "$REGION" --bucket "$BUCKET" > "$TMP/result.json"
rc=$?
cat "$TMP/result.json"
[ -z "$OUT" ] || cp "$TMP/result.json" "$OUT"
exit "$rc"
