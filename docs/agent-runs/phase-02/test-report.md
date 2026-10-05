# Phase 2 test report

STATUS: observed from retained build-engineer output and reviewer inspection of target logs. The coordinator did not re-run the suite.

OWNER: `build-engineer` for the tests under `project/verification/`. `code-reviewer` inspected logs and did not edit them.

WORK ORDER: AWS-free marker and check-failure tests. No module application tests. `tests/**` contains only `tests/.gitkeep`.

FILES CREATED: `project/verification/src/test/scala/scholarchain/build/TestRunMarkerSpec.scala`, `project/verification/src/test/scala/scholarchain/build/CheckFailurePathSpec.scala`.

FILES MODIFIED: `TestRunMarkerSpec.scala` no longer contains the simulated-guard test or the hard-coded task-name list. One test remains: `write creates gitignored marker path with success and timestamp`.

COMMANDS RUN: See the command table and independent double-check in `owner-report.md` under "Coordinator validation supplement."

TEST RESULTS:

- `TestRunMarkerSpec`: one test, reported passed inside the 22:13:44 check. Retained `succeeded_tests` lists `TestRunMarkerSpec=1791170024047`.
- `CheckFailurePathSpec`: one test. `testOnly` XML at `2026-10-04T22:13:52` has `failures="0"` and `errors="0"`. The test runs a real `checkTask` with the probe property and requires a non-zero exit plus an unchanged marker. The independent Java 17 run of `sbt -batch 'Test/compile' check packageJobs` also passed both specs (2 tests, 0 failures) and wrote the marker only after the tests.
- Module `definedTestNames` for `core` was empty on review. No application tests exist.

VALIDATION RESULTS: Normal `contractTest` is `buildVerification / Test / test` unless the probe property is set. The property is set only by `CheckFailurePathSpec`. A flagged `checkTask` fails at `checkProbeInjectFailure` before `markTestRun`.

ASSUMPTIONS: `Def.sequential` does not run later tasks after `sys.error`.

RISKS: Any non-zero subprocess status satisfies the spec, including `sbt` missing from `PATH`. An sbt server already started with `-Dscholarchain.checkProbe.fail=true` keeps that property for later commands on the same server.

MANUAL ACTION REQUIRED: none for these two tests. `dockerLocal` was outside the build-engineer's test report and was unverified at handoff; the later independent image build succeeded, as recorded in `owner-report.md`.

BLOCKED-ON OWNER: none

BLOCKED-ON EVIDENCE: The build-engineer's single retained `sbt check` transcript showing both tests and then `TestRunMarker` was absent at handoff. The later independent run observed that sequence; see `owner-report.md`.

NEXT GATE: human acceptance. This file does not accept Phase 2.
