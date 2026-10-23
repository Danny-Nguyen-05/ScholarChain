# Phase 7 test report

## Subphase 7A

STATUS: COMPLETE for observed local 7A test gates. Full check passed 594/594, exit 0; detailed results follow below.

OWNER: Coordinator `/root` executes owner-requested checks and retains observed evidence. Module and independent test owners wrote their respective tests. No reviewer role was invoked.

WORK ORDER: Run affected 7A tests and a fresh stable-tree `sbt check` using Section 2's JDK 17 environment. Preserve exact failures and distinguish targeted results from the complete gate.

FILES CREATED: Command registers, bounded build logs and policy proofs, targeted run logs/metadata, source snapshot, final gate evidence and audits under `evidence/7a/`.

FILES MODIFIED: Coordinator reports only. Exact specialist file paths are in `evidence/7a/files.json`.

COMMANDS RUN: Exact commands, exits and environment are in `evidence/7a/commands.md` and `build/commands.md`. Observed Java 17.0.20.1 and sbt 1.10.7. No command supplied both live-test opt-in and a valid profile. `/usr/bin/time -p sbt -batch check` completed under the default exclusion policy with exit 0.

TEST RESULTS: Final targeted command exited 0: storage 9/9, independent storage 26/26, Spark CSV 4/4; zero failures or aborted suites; real 15.22 seconds. Independent breakdown: ports 9, SDK stubs 11, synthetic manifest 5, actual Spark Parquet 1. Build policy test passed and tagged failure sentinel stayed excluded. Missing-opt-in test/testOnly/testQuick/executeTests probes and missing-profile probe each returned expected exit 1. Lowercase-configuration parser failures are retained separately and are not guard evidence. Earlier compile/test failures were repaired; full gate is separate below.

VALIDATION RESULTS: Tests assert known SHA-256, conditional expressions and concrete keys, configured GSI, atomic reservation, session-only TTL, 100+1 batch splitting, unprocessed retries, bounded S3 streams, manifest-last publication, unchanged reload, schema/count/hash rejection and iterator closure. Literal expected metrics and IDs verify provenance/qualification preservation. Actual Spark partitioned Parquet exercises integral doubles, nested context, Longs and nulls. CSV tests retain exact Unicode, quotes and embedded CRLF, both-direction ID parity, blank unknown years, empty headers and endpoint/support validation. Original failing byte assertions remain intact.

ASSUMPTIONS: Fixtures are explicitly synthetic. Independent fixture hashes were precomputed with Python hashlib. The actual Parquet integration uses the producer hash only to bind the handoff and asserts literal stored expectations. Historical Phase 6 results do not substitute for this fresh gate; no dataset Python test counts are added.

RISKS: Fakes/stubs establish local behavior and request shape, not live AWS compatibility. Broader hardening and the live suite remain 7C; real graph/vector adapters and CLI remain 7B. Raw full gate log stays under `/tmp`, with a bounded retained excerpt, raw byte count and hash for lean evidence. Storage application bounds and nonlocal-return warnings are disclosed.

MANUAL ACTION REQUIRED: User independently reviews 7A and commits only after acceptance. No automatic reviewer.

BLOCKED-ON OWNER: None for completed local test gates.

BLOCKED-ON EVIDENCE: None for completed local tests; live-service gates remain unverified.

NEXT GATE: Read-only user-launched 7A review after the full gate. Do not start 7B.

## Final local gate and stopping boundary

STATUS: COMPLETE for Subphase 7A local implementation and deterministic gates; independent review and human acceptance remain pending.

Fresh Section 2 JDK 17 `sbt -batch check` exited **0**, **594 passed / 0 failed**: core144, Hadoop64, ER39, Spark38, storage9, independent292, build8. Java17.0.20.1, sbt1.10.7. Sbt679s, real680.62s; completed2026-10-22 17:20:28 America/Chicago. The injected `checkProbeInjectFailure` error is the expected passing build self-test. No live integration tests ran.

Evidence: `evidence/7a/final-check.json`, `final-check-excerpt.txt`, `final-audit.json`. Raw log `/tmp/phase7a-final-check-2.log`, 1,363,026 bytes, SHA-256 `a1ce196af9385e3340b648ba5340f0449299b0bbe2330767a671a6c5896d179b`. Retained excerpts include original line numbers; the raw full log remains outside tracked evidence to keep it lean.

All109 scoped implementation/build/test/documentation hashes and mtimes were unchanged during the final gate. Protected Phase6 human-gate/repairs/commit and root control files match preflight; original plan hash matches. Tracked `git diff --check` exits0; all new implementation files are whitespace-clean. The generated test marker exists. Branch `phase-7`, base/current HEAD `98dd2a4458e3128d019af1c1d1dbd2bf1dfcbbd2`; no commit/push/staging or human gate was written. The first full-gate failure and its repair remain retained separately.

BLOCKED-ON OWNER: None for local7A completion. External reviewer and human own acceptance.
BLOCKED-ON EVIDENCE: None for the7A local gate. LiveAWS and later-subphase gates remain explicitly unverified.
NEXT GATE: User-launched read-only7A review using `evidence/7a/reviewer-prompt.md`, then human commit if approved. All specialist agents and launched builds have finished. No reviewer was triggered; no7B work started. Stop after handoff.


## Subphase 7A — repair round 1 test evidence

STATUS: Affected tests passed; fresh fullgate running. Final observed disposition follows after completion.
OWNER: Coordinator execution/evidence; storage/test owners authored only assigned source/tests. No reviewer invoked.
WORK ORDER: F1/F2 only, affected storage/independent/NeptuneCSV targets and fresh full JDK17check; preserve external review and earlier results.
FILES CREATED: repair-1/targeted-tests.txt; real-manifest-smoke.txt; real-manifest-smoke-relative-failure.txt; targeted-results.json; commands.md; evidence-migration.json; source-snapshot.json; audits/reports.
FILES MODIFIED: Coordinator report and reference metadata only; source ownership in owner-reports.md.
COMMANDS RUN: Section2 env,java-version and exact task/exit history in repair-1/commands.md. gitignore unchanged. No cloud/provider tests.
TEST RESULTS: storage10/10, independent27/27, SparkCSV4/4, exit0,real16.52s. Tests increased by one module and one independent regression. Real-source forked smoke clean exit0; counts are source metadata, not remeasured table counts. Fullcheck running.
VALIDATION RESULTS: Valid Str rowCount fixtures, malformed/nonstring/overflow counts rejected under valid completion markers, exact Long parsing. Actual retained source probe reads <=1row/table without writes.23 log renames hash-identical,14 raw build hashes reverified; new.txt paths appear in Git status/nonignored inventory. Old raw/tmp command history and verbatim review retain.log spelling. Provider classpath excerpt has separate raw/retained hashes.
ASSUMPTIONS: Synthetic metadata fixtures accurately match producer encoding; actual-source binding evidence is separately limited. Do not substitute earlier594/0 for this repair gate.
RISKS: First un-forked smoke shutdownclasspath exception and forked relative-path error retained; corrected forked absolute-path smoke passes. N1–N8 unchanged. This is local testing, not AWS/whole-dataset validation.
MANUAL ACTION REQUIRED: User recheck after fullgate, then human commit if approved.
BLOCKED-ON OWNER: None for affected targets.
BLOCKED-ON EVIDENCE: Fullgate running, final result follows.
NEXT GATE: User-launched read-only7A repair1 recheck after observedfullgate; no7B.


### Repair round 1 — final observed gate and disposition

STATUS: COMPLETE for the blocking F1/F2 local repairs and required checks. Independent recheck and human acceptance remain pending.

The fresh JDK 17 `sbt -batch check` exited **0**: **596 passed / 0 failed**, core144 / Hadoop64 / ER39 / Spark38 / storage10 / independent293 / build8. Java17.0.20.1, sbt1.10.7; sbt679s, real681.20s; completed2026-10-22 18:02:48 America/Chicago. The injected format-stage probe error is a passing build self-test. No live integration suite ran.

F1 is repaired and locally validated: exact nonnegative decimal-string Long parsing, corrected module/independent metadata fixtures, malformed-count regressions and a clean forked read-only smoke against three real retained manifests. Earlier tests used actual Parquet with synthetic metadata; they did not prove the producer metadata encoding. The repair evidence makes that distinction explicit. The smoke sampled one row each from researcher/collaboration/kcore and did not load caches or recompute complete table counts/hashes.

F2 is repaired and locally validated: all23 retained logs renamed to Git-visible.txt without byte changes; references updated;23 renamed hashes,14 original build hashes and all live retained index/target references verified. The classpath excerpt has an explicit retained hash separate from its full raw-log hash. Raw/tmp execution history and verbatim review retain their historical.log spelling. .gitignore is unchanged. No files were staged or committed.

All110 scoped source/build/test/documentation hashes and mtimes stayed unchanged during the final gate. Only the four authorized F1 source/test files differ from the reviewed source snapshot. Protected Phase6/control files, real-source metadata hashes and verbatim review match. Tracked diff check exits0; repair source files have no trailing whitespace. All launched jobs and specialist turns ended.

Evidence: `evidence/7a/repair-1/final-check.json`, `final-check-excerpt.txt`, `final-audit.json`, `targeted-results.json`, `evidence-migration.json`, `git-visible-files.txt` and `commands.md`. Raw full gate `/tmp/phase7a-repair1-final-check.log`:1,362,175bytes, SHA256 `26f7ad074aa1db1028558326d8826e30fd6e07937ed8ad511a2d5870f12e2497`.

N1–N8 remain OPEN/nonblocking with their recorded owners. No nonblocking fix, Spark producer/ID/hash change, .gitignore/build change, reviewer launch, cloud/provider call, commit/push, human-gate edit or7B work occurred.

BLOCKED-ON OWNER: None for local repair completion; reviewer and human own acceptance.
BLOCKED-ON EVIDENCE: None for the required local repair gate. Live-service and broader real-data gates remain unverified.
NEXT GATE: User-launched read-only7A repair1 recheck using `evidence/7a/repair-1/rechecker-prompt.md`; no commit until recheck APPROVE. Stop before the next subphase.
