STATUS: COMPLETE for F3/F4 implementation and affected targets; coordinator full gate pending.
OWNER: storage-engineer /root/storage_engineer.
WORK ORDER: Subphase 7B repair round 1, F3/F4 only; modules/storage/**. No nonblocking fixes or 7C.
FILES CREATED: Main sources AwsDocumentJson.scala and NeptuneJobAttempts.scala; module test NeptuneRepairSpec.scala.
FILES MODIFIED: NeptuneGraphLoader.scala, NeptuneGraphReader.scala and modules/storage/README.md.
COMMANDS RUN: Owned read/search/edit commands; explicit JDK17 javap for pinned Document/SdkNumber API inspection. No owner sbt process. Coordinator exact JDK17 formatting and affected targets recorded in commands.md.
TEST RESULTS: Exit0, real19.40 seconds: storage23/23, independent54/54, SparkCSV4/4. No failed repair invocation. Full check pending when this owner returned.
VALIDATION RESULTS: F3 pending allowlist is LOAD_NOT_STARTED/LOAD_IN_QUEUE/LOAD_IN_PROGRESS; completion succeeds and all other states terminate with a sanitized status-specific ledger failure. Immutable terminal markers cause a new numbered attempt with NEW mode on rerun; timeout retains the pending job, completion remains Unchanged without new uploads/submissions. Legacy job rows are preserved and recover through append-only markers/attempts. Tests cover failed jobs, write conflicts, deadlock, unknown statuses, timeout reuse, completion reuse, retry history and legacy recovery. F4 uses structural SDK Document conversion for reader results and loader status. Internal JSON preserves maps, lists, raw strings, exact BigDecimal numbers, booleans and null. Node labels/neighbor properties preserve CRLF, tab, quotes, backslash, Greek/CJK and emoji; large integers beyond 2^53 and precise decimals remain unquoted numbers. No Document.toString JSON parsing remains.
ASSUMPTIONS: Existing IDs, hashes, producer outputs and public storage contracts remain authoritative. Recovery is append-only and requires no deletion.
RISKS: Live AWS behavior is unverified. Existing N4–N14 remain deferred, including concurrency/cross-service limitations.
MANUAL ACTION REQUIRED: Coordinator completes full check/evidence; user launches recheck.
BLOCKED-ON OWNER: None for implementation.
BLOCKED-ON EVIDENCE: Full check pending at owner return.
NEXT GATE: Successful full check then independent recheck. Owned source/tests/README frozen; no owner jobs.
