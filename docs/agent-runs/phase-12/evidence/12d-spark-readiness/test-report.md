# Observed offline checks

STATUS: COMPLETE for local deterministic/runtime validation; independent review pending.
OWNER: Build owner runs JDK17/sbt; coordinator runs bounded packaged local CLIs; Spark owner authors feature tests.
WORK ORDER: work-order.md. All listed counts are observed output, not planned acceptance numbers.
FILES CREATED: Exact commands/environments/results/logs, source freeze, classpath/artifact inventories, actual output archives and probe/comparison receipts in this directory.
FILES MODIFIED: Only owned source and appended coordinator records; no independent test or human decision changes.
COMMANDS RUN: Command JSON and runner copies retain full Java classpaths, JDK opens, configs, process bounds and minimal environments. Correct sbt offline setting is SBT_OPTS=-Dsbt.offline=true plus set ThisBuild / offline := true; the unsupported -offline launcher attempt is disclosed. Final alias check runs formatting, owner/independent tests, build contracts and markTestRun. No separate Python billing or A1 rerun is claimed.
TEST RESULTS:

| Stage | Observed result |
|---|---|
| Initial launcher | exit1, unsupported -offline, no tests |
| Initial targeted readiness | exit0,11 tests |
| First fullcheck | exit1,1253 tests with1 failure, unchanged independent source fence |
| Repaired targeted readiness + independent safety | exit0,12+7 tests |
| Fresh verified packaging | exit0, current assembled JAR |
| Final sbt check | exit0,1267 tests,0 failures;723.885s |
| Actual local Hadoop preparation | exit0,10.623s |
| Actual disabled-LLM ER resolve | exit0,0.502s |
| Packaged baseline first attempt | exit1, local socket denied; partial retained |
| First escalated retry | refused existing partial output before Java launch |
| Packaged baseline A new output | exit0,29.247s,28 datasets |
| Packaged baseline B relocated input/shuffle2 | exit0,31.397s,28 datasets |
| Actual exact comparator | exit0,13.277s,28 schemas/counts/hashes/full row multisets match |
| Separate-JVM probe attempt1 | exit2,121.035s, missing standalone XML dependency |
| Separate-JVM probe attempt2 | exit2,1.047s, missing explicit launcher Scala binary version |
| Separate-JVM probe attempt3 | exit0,2.248s, actual external task JVM and file exchange |
| Local threaded positive | exit0,1.339s, externalExecutorVerified=false |
| Local threaded distributed-required negative | expected exit2,1.268s, no success output |

Final fullcheck counts are207 core +64 Hadoop +39 ER +50 Spark +80 storage +107 RAG +40 services +667 independent +13 build contracts. Their sum is1267. The first attempt's stale XML included old build reports that had not run in that failed invocation; its log-count1253 is authoritative. No duplicate count from old XML is used. Generated marker timestamp1793738960408 was written only after final success.

VALIDATION RESULTS: Final source/JAR stability, marker binding and packaging checks are in build report/results. Root verifies all six final source hashes against working files and before/after snapshots. All4912 pre-existing non-Spark tracked blobs and six initial record bases matched before append; later preservation checks allow only five exact new suffixes and preserve the human record. Compressed logs retain raw-byte hashes; archive members are read back and hashed. Same-JAR runtime reports bind actual observations, not a Spark master label alone.
ASSUMPTIONS: Process logs are accepted as observed evidence pending independent review; no reviewer rerun is represented.
RISKS: Local execution and synthetic DBLP-only data are narrower than full multi-source/EMR deployment. A default sandbox denial and standalone runtime bootstrap failures were corrected without deleting or substituting failed evidence. Raw event logs and the generated JAR remain ignored local artifacts, with public provenance retained. Local sockets required sandbox escalation; no cloud/network service was used.
MANUAL ACTION REQUIRED: Independent read-only review only; no user Terminal work is needed for the completed checks.
BLOCKED-ON OWNER: Human/reviewer for acceptance and later infra/deploy roles for separately gated live work.
BLOCKED-ON EVIDENCE: Independent readiness verdict and later remote/shared-filesystem/EMR/lifetime/teardown evidence.
NEXT GATE: Fresh independent review. No automatic source-control or live action.
