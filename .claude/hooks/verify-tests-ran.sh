#!/usr/bin/env bash
set -euo pipefail

root=${CLAUDE_PROJECT_DIR:-$(pwd)}
marker="$root/.claude/.last-test-run"
dirs=()
[[ -d "$root/modules" ]] && dirs+=("$root/modules")
[[ -d "$root/tests" ]] && dirs+=("$root/tests")
[[ -d "$root/scripts" ]] && dirs+=("$root/scripts")
[[ -d "$root/datasets/scripts" ]] && dirs+=("$root/datasets/scripts")
[[ -d "$root/experiments/scripts" ]] && dirs+=("$root/experiments/scripts")
[[ -d "$root/load-tests" ]] && dirs+=("$root/load-tests")
(( ${#dirs[@]} > 0 )) || exit 0

source_find() {
  if [[ ${1:-} == newer ]]; then
    find "${dirs[@]}" -type f \( -name '*.scala' -o -name '*.java' -o -name '*.sh' -o -name '*.py' \) -newer "$marker" -print -quit 2>/dev/null
  else
    find "${dirs[@]}" -type f \( -name '*.scala' -o -name '*.java' -o -name '*.sh' -o -name '*.py' \) -print -quit 2>/dev/null
  fi
}

if [[ ! -e "$marker" ]]; then
  if source_find | grep -q .; then
    echo "Tests are required: no .claude/.last-test-run marker exists. Run sbt check; only a successful check may update the marker." >&2
    exit 2
  fi
  exit 0
fi
if source_find newer | grep -q .; then
  echo "Tests are stale: source changed after .claude/.last-test-run. Run sbt check and verify the marker updates after success." >&2
  exit 2
fi
exit 0
