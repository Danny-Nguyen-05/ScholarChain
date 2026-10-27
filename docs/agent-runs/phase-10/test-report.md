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
