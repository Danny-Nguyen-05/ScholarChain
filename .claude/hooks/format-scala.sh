#!/usr/bin/env bash
set -euo pipefail

input=$(cat)
path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""')
[[ "$path" == *.scala ]] || exit 0
root=${CLAUDE_PROJECT_DIR:-$(pwd)}
if [[ ! -f "$root/build.sbt" ]]; then
  echo "Scala formatter deferred: build.sbt is not present yet." >&2
  exit 0
fi
# The official sbt-scalafmt task scalafmtOnly formats only the listed file.
# Require a simple path inside the project before passing it to sbt's command parser.
if [[ "$path" == "$root/"* ]]; then
  relative=${path#"$root/"}
else
  echo "Scala formatter refused a path outside the project: $path" >&2
  exit 2
fi
if [[ ! "$relative" =~ ^[A-Za-z0-9_./-]+[.]scala$ ]] || [[ "$relative" == *".."* ]]; then
  echo "Scala formatter refused an unsafe file path. Rename the file or format it through an approved owner command." >&2
  exit 2
fi
cd "$root"
if ! sbt "scalafmtOnly $relative" >&2; then
  echo "Scala formatting failed for $relative. Fix the build or formatter and rerun scalafmtOnly for this file." >&2
  exit 2
fi
