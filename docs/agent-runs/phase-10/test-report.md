# Subphase 10A

STATUS: COMPLETE (implementation and observed gates; pending independent review and human acceptance)
OWNER: /root evidence coordinator; observed results from service-engineer, test-engineer and build-engineer
WORK ORDER: Phase10A only. Branch phase-10; base and current HEAD 3c0a817305d783bbb6a4cb6fe9bb654d06d8632a. Exact plan/user messages in prompt.md; user default answers in evidence/10a/step0-answers.md. No10B work or reviewer invocation.
FILES CREATED:
- Dockerfile.dockerignore
- modules/services/README.md
- modules/services/src/main/resources/openapi/scholarchain.v1.yaml
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiApplication.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiContracts.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiServer.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/DownstreamClient.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RuntimeWorkflowAdapter.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ServiceMains.scala
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/RuntimeWorkflowAdapterSpec.scala
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/ServiceFoundationSpec.scala
- project/ServiceDistribution.scala
- project/ServicesPackaging.md
- project/verification/src/test/scala/scholarchain/build/ServiceDistributionSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10AResilienceSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10ASpec.scala
- docs/agent-runs/phase-10/** (coordinator reports and evidence; exact inventory evidence/10a/files.json)
FILES MODIFIED:
- Dockerfile
- build.sbt
- project/Dependencies.scala
- project/ScholarChainBuild.scala
- project/Versions.scala
COMMANDS RUN:
All exact command blocks, env, failures and outputs: evidence/10a/commands.md and the three owner reports. Principal gates:
- sbt -batch check: exit0, JDK17.0.20.1,756s.
- sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'services / test': final exit0,16/16.
- sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A*': exit0,20/20.
- sbt -batch 'services/update' 'buildVerification / Compile / scalafmt' 'buildVerification / Test / scalafmt' scalafmtSbt 'buildVerification/testOnly scholarchain.build.ServiceDistributionSpec': exit0,3/3.
- sbt -batch packageServices dockerLocal: exit0,4images built.
- python3 /tmp/phase10a-container-smoke-2.py: exit0,4image checks passed/created containers removed (replay evidence/10a/container-smoke.py).
- git diff --check: exit0. Distribution ZIP verification exit0,199dependency JARs,0Spark JARs,4mains/OpenAPI present.
TEST RESULTS:
Full gate1170 passed,0failed,139completed suites. Counts: core207,hadoop64,entityResolution39,sparkAnalytics38,storage80,rag107,services16,independentTests608,buildVerification11. Targeted39 new tests are included within full gate; do not add them again. Nested injected format-stage failure is expected CheckFailurePathSpec; outer check passed and markTestRun executed. Retained check-result.json/check-excerpts.txt bind original /tmp log hash.
VALIDATION RESULTS:
Cask0.10.2 compiled Scala3.3.4; pinned dependency matches existing uPickle4.0.2. Thin routes delegate to query service/workflow ports; conditional session reservation plus CAS updates; sync/async/jobs; separate bearer auth; IDs and typed errors; safe logs; readiness/liveness; metrics; timeout/read retry/breakers; initial OpenAPI. Four independent local images run selected entrypoints as nonroot. All22source/build/test artifacts unchanged during final gate, source hashes retained. Full implementation details and module docs are linked in owner reports.
ASSUMPTIONS:
User confirmed defaults including Docker available; no cloud or paid-provider execution authorized/performed. Fakes and synthetic fixtures are not corpus findings. Existing core/storage/rag contracts sufficed; no domain or other owner edits needed. No commits/pushes, resets or human gate edits. Exact backend agent model IDs are not exposed by native collaboration API and are not invented.
RISKS:
Foundation mains have no configured backend (health200/readiness503/query503). Successful API tests inject fakes; real runtime adapter test verifies audited abstention. Local async executor does not resume jobs after process death; a crash between reservation/body binding leaves an uncertain session returning503, and persistent store failure can prevent terminal publication. Real adapter leaves researchers empty and explicitly rejects includeScores=true422. Phase9 internal audit trace uses queryId rather than independently injected HTTP traceId. HTTP parser failures before application dispatch are outside the application trace envelope. Full OpenAPI semantic validation unavailable (Ruby syntax/surface check passed). Storage retains Hadoop/Parquet runtime dependencies. These are disclosed limitations for review, not acceptance or production-readiness claims.
MANUAL ACTION REQUIRED:
User launches read-only review using reviewer-prompt.md. On approval user commits10A; only a new prompt starts10B. Human owns acceptance/commit records. Optional OpenSearch,Cognito,extra indexes/services and CI workflows omitted per lean scope.
BLOCKED-ON OWNER: None; independent review/human acceptance remain next gates.
BLOCKED-ON EVIDENCE: None for observed10A gates. Limitations remain explicitly unverified.
NEXT GATE: User-launched10A read-only review, then human commit and separately prompted10B. All delegated agents completed; all foreground builds/tests exited; smoke-created containers removed.

# Subphase 10A repair round 1

STATUS: COMPLETE (F1 implementation and required gates passed; independent recheck/human acceptance pending)
OWNER: /root test-evidence coordinator; /root/service_engineer owns module regression tests
WORK ORDER: Subphase10A repair round1, F1 only. User-supplied external verdict appended verbatim to review.md; F1–F5 routed/listed in repairs.md. Base/HEAD 3c0a817305d783bbb6a4cb6fe9bb654d06d8632a,branch phase-10. Prior uncommitted10A changes preserved by explicit user instruction. No questions for this repair round.
FILES CREATED:
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/RetriedSessionCreationSpec.scala
- docs/agent-runs/phase-10/evidence/10a-repair-1/** (exact inventory files.json)
- docs/agent-runs/phase-10/review.md
- docs/agent-runs/phase-10/repairs.md
FILES MODIFIED:
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala
- modules/services/README.md (idempotency paragraph only)
- docs/agent-runs/phase-10/owner-report.md and test-report.md (append repair sections)
Other source/build/test files unchanged from original10A checkpoint. Repair-source.diff verified against pre-repair SHA256 values.
COMMANDS RUN:
Every sbt invocation used exact plan JAVA_HOME/JDK17,PATH,SBT_OPTS. Complete commands/results in evidence/10a-repair-1/commands.md and service-owner-report.md.
- Initial child /usr/bin/time -p sbt -batch 'services / Test / testOnly edu.uic.cs441.scholarchain.services.RetriedSessionCreationSpec': exit1 before tests,cache lock refused,elapsed0.26s. Inherited child escalation wait was interrupted by root; no process/test result. Root checked no sbt process existed and ran gates centrally using its current unrestricted tool. This was an interrupted stale wait, not a user refusal of the repair.
- Root pre-fix sbt -batch 'services / Test / testOnly edu.uic.cs441.scholarchain.services.RetriedSessionCreationSpec': exit1,3run/2pass/1fail,3s. RetriedWritten first response503 reproduced F1; RetriedUnchanged/Rejected passed.
- Root sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A*': exit0; format1s/0s,services19/19 in4s,independent20/20 in3s. Required scopes ran sequentially in one invocation.
- Root sbt -batch check: exit0,1173passed/0failed,140suites/0aborted,713s.
- git diff --check: exit0. Source freeze/hash validation:23/23 match,20original source artifacts unchanged; only3expected repair paths differ. Branch/HEAD unchanged.
TEST RESULTS:
New3-case regression failed on old code and passed after F1. Successful retried creator returns200or202validjob,persists terminal response,runs workflow exactly once,same-body replay returns stored response,different-body409. RetriedUnchanged/Rejected reconcile existing record with zero new workflow calls and preserve409conflicts. Full module19passed,independent10A20passed. Full repository1173passed includes those tests; do not add targeted counts again. Per-module full counts core207,hadoop64,entityResolution39,sparkAnalytics38,storage80,rag107,services19,independentTests608,buildVerification11. Expected nested injected format-stage failure remains a passing build self-test; outer check exited0 and markTestRun executed.
VALIDATION RESULTS:
Exactly Retried(_,Written(session)) normalizes to Written(session), then follows the existing creator branch unchanged. Other Retried results preserve primary-session reconciliation without scheduling. No storage edits required. Minimal3-file diff and acceptance matrix retained. Full log /tmp/phase10a-r1-check.log SHA256 964d6d8041b97fe6f6ca7c3b1e9ab8ef96ca5e58ff130bf1a3eb32b02b7b223f; lean excerpts and hashes retained. Original10A evidence remains historical; refreshed repair source hashes are evidence/10a-repair-1/source-files.json.
ASSUMPTIONS:
User authorized F1 only and proceeding with uncommitted10A. Successful fixed-token storage retry Written means this caller created reservation. Synthetic fakes/tests are not live datastore evidence. Original defaults unchanged.
RISKS:
F2–F5 remain nonblocking and untouched: stored terminal retryability,202QUEUED label,configuration failure exit0,and additional half-open/429/result-too-large tests. Original10A runtime/durable-dispatcher/trace/projection limitations remain. Docker packaging unchanged; images were NOT rebuilt and existing local images predate F1,so they do not contain this repair. No new claim of production durability/readiness.
MANUAL ACTION REQUIRED:
User launches read-only recheck from evidence/10a-repair-1/reviewer-prompt.md. No commit until recheck approves. User owns acceptance/commit records. No10B until separately prompted after review.
BLOCKED-ON OWNER: None for this implementation/gate; independent reviewer and human acceptance are next gates.
BLOCKED-ON EVIDENCE: None for F1 repair gates. Prior nonblocking findings remain listed rather than silently repaired.
NEXT GATE: User-launched independent F1 recheck for10A repair round1; no reviewer invoked. Service agent completed; all regression,targeted,fullcheck processes exited. No Docker jobs/containers started. No cloud/provider,push/commit/reset/discard,human-gate edits or10B work.


## Subphase 10B

STATUS: COMPLETE
OWNER: orchestrator assembling independently owned tests and observed central gates
WORK ORDER: Phase10B required matrix and full JDK17 check.
FILES CREATED: Five independent10Bfiles and Services10BSpec.scala; two packaging cases added to existing ServiceDistributionSpec. Source/owner manifest: evidence/10b/source-files.json.
FILES MODIFIED: Source tests only by their respective owners; this report and evidence by orchestrator.
COMMANDS RUN: evidence/10b/commands.md records exact commands; each named *-result.json binds exit/time/log hash and its pre-command source hashes.
TEST RESULTS: Full check1199passed/0failed/145suites,exit0,708s(sbt)/709.995s(wall),JDK17.0.20.1. Module totals: core207,hadoop64,entityResolution39,sparkAnalytics38,storage80,rag107,services26,independentTests625,buildVerification13. Focused final10B17/17; services26/26; prior10A20/20 preserved. Fourimages/eightbootcases plus packaged3-service HTTP and fail-dependency readiness passed. Exact summaries in check-summary.json and Docker result JSON.
VALIDATION RESULTS: Real bounded HTTP query→verifiedcount3→stored evidence→explain lifecycle; auth/malformed/timeouttraces; graphdirectedfilters/caps/signedstablecursors; workerduplicate/poison/failedDLQ; actualreadretries/writeonce/correlation/breakers; fivecommittedJSONexamples; thinroutesourceheuristic. F1regressionspreserved; F2–F5featurechecks pass. Rootretains every failedattempt: two compilegates sameJSONmetadata typeerror; targeted-2 services25pass and independent13pass/3fail due unfinishedOpenAPI and Caskqueryparams; one cancelledcredentialhelper build; three integrationharnessissues. Fixedwithout weakening required behavior. Nested CheckFailurePathSpec error is intentional and outercheckpassed. Full-logSHA256 376355f9d008d6aa3e8cb9159fbd3166fde575e0f34372c16bca7af5c5c815a1.
ASSUMPTIONS: Approved offlinefixture/defaultscope; no liveproviderorcloudcalls.
RISKS: Explicit offline-synthetic composition uses declared Phase9G1 fixtures; live backend/provider execution and deployment remain unverified human-gated work. The frozen GraphReader lacks direction/snapshot semantics, so live graph deployment needs the stronger GraphSnapshot adapter. Query execution is local and nondurable; worker PROCESSING reservations require crash recovery and DLQ publication/terminal recording are not transactional. Missing cache/retry measurements are null; unknown score weights are absent; internal runtime trace uses query ID linked to HTTP context. New/internal routes currently log safe template label unmatched. Full OpenAPI semantic validation was unavailable; YAML/local refs, committed examples and wire assertions passed. Optional OpenSearch/indexes/CI and cloud deployment were omitted.
MANUAL ACTION REQUIRED: User-launched independentreview, then human acceptance/commit.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for localrequiredgates.
NEXT GATE: Subphase10Bread-onlyreview; stop.


## Subphase 10B repair round 1

STATUS: COMPLETE
OWNER: orchestrator assembling independent and module-owner tests
WORK ORDER: F6 acceptance/outage regression and F9 evidence correction; user-authorized scope only.
FILES CREATED: One module suite (5tests) and one independent suite (4tests); paths in repair-files.json.
FILES MODIFIED: No existing tests; new module503 metric assertion corrected to existing contract after red. New independent positive ordering strengthened after first green.
COMMANDS RUN: commands.md and *-result.json retain exact JDK17 commands/exits/times/hashes. No standalone buildVerification/test needed because no build file changed; fullcheck included13/13.
TEST RESULTS: Final targeted31/31 services5suites and41/41 independent7suites; full1208/1208 in147suites,exit0,sbt709s/wall710.548s,JDK17.0.20.1. Four rebuilt images/eight startup cases and three-main remote/outage smoke passed. Full-logSHA256 39aaf21ff6902af2bcde194c7e45622f207aa9338adebaaf5b04dc8b2bc6f4d3.
VALIDATION RESULTS: Independent red4run/3pass/1fail exactly reproduced F6; three true-outage guards passed before fix. Module red5run/2pass/3fail included two intended missing-marker failures and one corrected503 metric expectation. First green31/41+package passed. Original red source retained. Independent test then strengthened to burst4 without successful readiness calls resetting failures; first full attempt intentionally SIGTERM-cancelled at230.240s(exit143), retained separately. Final targeted gate passed stronger test; final full gate used that exact test source. Intentional nested CheckFailurePathSpec failure is expected; parent and outer check passed. See regression-notes.md and acceptance.md.
ASSUMPTIONS: F6/F9 only; local authenticated HTTP/fakes and synthetic packaged runtime.
RISKS: Local results are not live deployment guarantees; nonblocking F7,F8,F10–F15 remain carried.
MANUAL ACTION REQUIRED: User-launched read-only recheck.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for required gates.
NEXT GATE: Subphase10B repair round1 recheck, then stop.


## Subphase 10B repair round 2

STATUS: COMPLETE
OWNER: orchestrator assembling module/independent/build owner reports
WORK ORDER: F6residual equal-budget behavioral red/green and fullgate.
FILES CREATED: Module GraphTransportBudgetSpec final5tests;independentEqualBudgetSpec3tests.
FILES MODIFIED: Two independent fakeGraphEndpoints wrappers receive budget-aware overloads;original retry/status/trace assertions intact.
COMMANDS RUN: Exactcommands/exits/durations/hash/source evidence in evidence/10b-repair-2/commands.md and *-result.json, allJDK17environment.
TEST RESULTS: Redindependent3run/1pass/2fail,redmodule4run/0pass/4fail. Green36/36services6suites,44/44independent8suites,packagepassed. Finalfull1216/1216,149suites,exit0,sbt721s/wall723.581s,JDK17.0.20.1. Fullmodulescore207,hadoop64,entityResolution39,sparkAnalytics38,storage80,rag107,services36,independent632,buildVerification13. Fourcurrentimages/eightstartupcases plusremoteequal500/500composition/stopgraphpassed. Full-logSHA256 8930aa7a4c872e6412011fc362a2e00b5cb5a18640b059bc9e8b8dfffe26c526.
VALIDATION RESULTS: Exactformattedredtexts/pre-gatehashes retained. Both actualequal300budgets omitted/caller300 reproduced3executionsfor4requests beforefix. Newindependenttesttextunchangedredtogreen;modulegreengained5thconfigcase/expandedrealnode-metric-path guards explicitlyreported. Cursorreplayandprioroutageguards pass. NestedCheckFailurePathSpec injectederrorintentional,parent/outergatepassed. No cancelled repair2 gate orfailedDockerattempt. OnlyREADMEcountdocchangedpost-fullsnapshot.
ASSUMPTIONS: User-authorizedF6only;noF16backendreadychange.
RISKS: Localtests do notestablishlivebackend/network guarantees;carriedfindingsunchanged.
MANUAL ACTION REQUIRED: User-launched independentrecheck.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None forrequiredlocalgates.
NEXT GATE: Repair2read-onlyrecheck,thenstop.
