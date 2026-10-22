# Subphase 6I commands and execution scope

Working directory: `/Users/danny/Documents/UIC/CS441/ScholarChain`.
Branch `phase-6`; base/unchanged HEAD `d1afc7f6698965ddbe010621b277b10e655d25ff`.
Whole-Phase-6 review baseline `03493882399e9020e6892c9f97e0ec8919365215`.

## Fresh definition-of-done gate

Actual environment and subprocess command:

```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
/usr/bin/time -p sbt -batch check
```

An inline Python `subprocess.run` wrapper redirected Java/time/sbt stdout and
stderr to `final-check.txt`, recorded UTC start/completion, and appended the
observed `exit=<returncode>`. `gate-execution.json` records the actual subprocess
exit code; `final-gate-metadata.json` extracts module counts, timing, log byte size
and SHA-256 after completion. The retained log is complete and unfiltered.
The expected injected `checkProbeInjectFailure` error trace is part of the build
verification self-test, not a failed repository gate.

## Read-only preflight and final inventory commands

```sh
git status --short
git branch --show-current
git rev-parse HEAD
git log -3 --format='%H %s'
git diff --stat 03493882399e9020e6892c9f97e0ec8919365215
git diff --name-only 03493882399e9020e6892c9f97e0ec8919365215
git diff --name-only d1afc7f6698965ddbe010621b277b10e655d25ff
git ls-files --others --exclude-standard
shasum -a 256 /Users/danny/Documents/plan/phase6.md
git diff --check
git diff --check 03493882399e9020e6892c9f97e0ec8919365215
```

`preflight.json` records the initially clean tree and committed previous subphase.
`implementation-snapshot.json` hashes the 68 implementation/config/build/dataset
files introduced or modified by Phase 6, not a full repository inventory. Final
metadata compares those hashes and mtimes and checks unchanged HEAD/plan and
human-owned file existence/content. It does not read secret directories.
`changed-files.txt` records current tracked/untracked changes;
`whole-phase-files.txt` records tracked changes against the Phase 6 baseline plus
untracked files so the external reviewer can include the complete scope.

## Retained evidence consistency audit

An inline Python JSON/SHA audit produced `retained-evidence-check.json`:

- Read both stored run metadata objects and the 28-table replay comparison;
  compare run IDs, compiled code fingerprint, logical config fingerprint,
  each recorded table hash and the complete counter arrays.
- Recursively diff `analytics-report.json` versus `replay-analytics-report.json`;
  compare the 12 difference paths and both raw file hashes against the repair
  comparison. Confirm the comparison explicitly distinguishes logical table
  equality from nonidentical reports.
- For each recorded successful root, compute
  `sha256(run-manifest bytes + b"\n" + run-metadata bytes)` and compare with
  the completion marker. Compare retained manifest/metadata bytes to each
  published sidecar.

This validates metadata/sidecar consistency only. It is not a Parquet reread,
rerun of Spark, or new event-log DAG recomputation. Historical dataset Python 12/12
and the real pipeline runs are not rerun in 6I; current Scala integration tests
run as part of `sbt check`.

## Course source

Read the official raw course README using the web tool, then Python
`urllib.request.urlopen` to read the complete Phase 6 and Detailed Spark sections
without summary truncation. `course-source.json` records source URL, bytes,
SHA-256, UTC retrieval and section ranges. No dataset downloaded or network
budget consumed for data acquisition in 6I.

## Boundaries

Coordinator edits only `docs/agent-runs/phase-06/**`, excluding human decisions.
No implementation, formatter-by-hand, packaging run, AWS call, live model call,
store load, dataset cleanup, reviewer launch, commit or push. Build-generated
ignored marker updates are the normal result of a successful check. Final output
is a comprehensive read-only reviewer prompt; human acceptance remains pending.

## Final cumulative whitespace result

```sh
git diff --check 03493882399e9020e6892c9f97e0ec8919365215 -- . ':(exclude)docs/agent-runs/phase-06/evidence/**'
```

Observed current tracked diff: exit 0. Cumulative non-evidence diff: exit 0.
The unfiltered cumulative check: exit 2 for trailing whitespace in historical
raw evidence logs. Originals were preserved. `diff-check.txt` has all output.
An initial metadata assembly assertion assumed every cumulative check returned0;
the assertion was corrected to report this result. No source/log fix, extra test
run or passing cumulative-all-files claim was substituted.
