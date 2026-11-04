#!/usr/bin/env bash
# Phase 12D spike - identity preflight. Read-only: one sts:GetCallerIdentity.
# Prints ONLY the caller Arn, Account and the region in effect (never keys),
# and refuses to continue unless all three match the expected values.
#
# Usage: preflight.sh --account <12 digits> --role <role name> [--region us-east-2]
# Exit: 0 ok, 1 identity mismatch or call failure, 64 usage.
set -euo pipefail

ACCOUNT="" ROLE="scholarchain-deployer" REGION_EXPECTED="us-east-2"
while [ $# -gt 0 ]; do
  case "$1" in
    --account) ACCOUNT="${2:-}"; shift 2 ;;
    --role) ROLE="${2:-}"; shift 2 ;;
    --region) REGION_EXPECTED="${2:-}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done
case "$ACCOUNT" in
  [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]) ;;
  *) echo "--account must be 12 digits" >&2; exit 64 ;;
esac
[ -n "$ROLE" ] || { echo "--role must not be empty" >&2; exit 64; }

region="${AWS_REGION:-${AWS_DEFAULT_REGION:-}}"
if [ -z "$region" ]; then
  region="$(aws configure get region 2>/dev/null || true)"
fi

if ! ident="$(aws sts get-caller-identity --query '[Arn,Account]' --output text 2>/dev/null)"; then
  echo "PREFLIGHT FAIL: sts get-caller-identity failed" >&2
  exit 1
fi
arn="$(printf '%s' "$ident" | awk '{print $1}')"
acct="$(printf '%s' "$ident" | awk '{print $2}')"

echo "Arn=${arn}"
echo "Account=${acct}"
echo "Region=${region:-<unset>}"

fail=0
if [ "$acct" != "$ACCOUNT" ]; then echo "PREFLIGHT FAIL: account is not the expected ${ACCOUNT}" >&2; fail=1; fi
case "$arn" in
  "arn:aws:sts::${ACCOUNT}:assumed-role/${ROLE}/"*) : ;;
  *) echo "PREFLIGHT FAIL: caller is not an assumed-role session of ${ROLE}" >&2; fail=1 ;;
esac
# no extra path segments after the session name
rest="${arn#"arn:aws:sts::${ACCOUNT}:assumed-role/${ROLE}/"}"
case "$rest" in */*) echo "PREFLIGHT FAIL: unexpected ARN shape" >&2; fail=1 ;; esac
if [ "$region" != "$REGION_EXPECTED" ]; then echo "PREFLIGHT FAIL: region is not ${REGION_EXPECTED}" >&2; fail=1; fi

[ "$fail" -eq 0 ] || exit 1
echo "PREFLIGHT OK"
