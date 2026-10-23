STATUS: COMPLETE for independent F3/F4 regressions and affected targets.
OWNER: test-engineer /root/test_engineer — test author, not reviewer.
WORK ORDER: Subphase 7B repair round 1, tests/** only, F3/F4 only.
FILES CREATED: None this repair.
FILES MODIFIED: IndependentStorageGraphLoaderSpec.scala and IndependentStorageGraphReaderSpec.scala under tests/src/test/scala/edu/uic/cs441/scholarchain/independent/.
COMMANDS RUN: No personal sbt invocation. Coordinator executed exact JDK17 formatting/storage/independentStorage/CSV targets in commands.md. Owner read source, complete external review and retained log.
TEST RESULTS: Exit0, real19.40 seconds: storage23/23, independent54/54, SparkCSV4/4. Six new independent regressions increased48to54. Raw output /tmp/phase7b-repair1-targeted-1.txt; complete retained targeted-1.txt with hash metadata.
VALIDATION RESULTS: LOAD_FAILED stops after one poll; new adapter on shared durable ports submits exactly one new job (AUTO then NEW), completes and preserves failure/retry history. Write conflicts stop immediately and recover on rerun. Deadlock and unknown states become immediate failures. Timeout reuses the pending ID with no submission. Completed fingerprint produces no new upload/submission. SDK Documents constructed structurally preserve actual CRLF, tabs, quotes, backslashes, Greek/CJK and emoji exactly in node/neighbor properties, including UTF-8 bytes. Existing Spark-shaped exports reused; no new export producer or fixture contract change.
ASSUMPTIONS: Synthetic offline fixtures establish local behavior, not live Neptune correctness.
RISKS: N4–N14 deferred. Full gate remains coordinator responsibility.
MANUAL ACTION REQUIRED: Coordinator completes full check and recheck packet.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for affected tests; full check pending at owner return.
NEXT GATE: Full deterministic gate then user-launched read-only review. Files frozen, no owner jobs.
