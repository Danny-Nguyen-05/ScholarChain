STATUS: COMPLETE for7C-M1 implementation and affected validation; full coordinator gate pending.
OWNER: storage-engineer /root/storage_engineer; final owner report returned this repair, assembled by coordinator.
WORK ORDER: Subphase7C repair round1,7C-M1 only. Sole writing territory modules/storage/** test tree and README.
FILES CREATED: AwsLiveGraphCleanup.scala and AwsLiveGraphCleanupSpec.scala under modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/.
FILES MODIFIED: AwsLiveRun.scala in same test package; modules/storage/README.md.
COMMANDS RUN: Owner source/review reads and owned edits, no owner sbt invocation. Coordinator exactJDK17 formatting, storage/AwsIntegration/compile ONLY, normalstorage and IndependentStorage*Spec tests; commands.md contains exact invocation.
TEST RESULTS: Exit0 real14.30s; normalstorage32/32, independentStorage73/73, live configuration compiled. No live test body or actual cleanup executed. Five new offline cases cover zero-match edge/node DELETE, invalid/nonintegral counts, remaining data, read failure and successful verification order. No failed repair invocation.
VALIDATION RESULTS: Both DELETEs return exact numeric counts checked against journaled ID cardinality; undirected edge matches deduplicated. Separate read-side edge point query and production GraphReader.node calls must prove every ID absent. All graph entries stay created until the entire graph batch passes count and absence checks, then transition to cleaned. Mismatch/malformed response/remaining data/read error fails closed and preserves created journal state. Exact IDs/run ownership predicates and noDETACH remain intact. README clarifies verification and partial-cleanup reconciliation.
ASSUMPTIONS: Future live cleanup requires existing opt-in and approvedPhase14C guards. Offline stubs verify local behavior, not Neptune execution.
RISKS: Live query/cleanup behavior unverified; partial deletion followed by failed verification deliberately leaves graph batch created.7C-L1/L2/L3 and other deferred findings unchanged.
MANUAL ACTION REQUIRED: Coordinator fullgate/evidence, user externalrecheck thenhumancommit/Phase7acceptance.
BLOCKED-ON OWNER:None forimplementation.
BLOCKED-ON EVIDENCE:Fullcheck pending at owner return.
NEXT GATE:FullJDK17check thenuser-launchedrecheck; all source/README frozen, no owner jobs.
