<!-- Course-named copy of owner-report.md in this folder, added in Phase 17 (package 17D, docs/agent-runs/phase-17/prompt.md). The text below this note is identical to owner-report.md, which is unchanged. -->

# Subphase 10A

STATUS: COMPLETE (implementation and observed gates; pending independent review and human acceptance)
OWNER: /root coordinator; build-engineer, service-engineer, test-engineer own implementation classes per evidence/10a/delegation.md
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
OWNER: /root coordinator; /root/service_engineer sole implementation owner in modules/services/**
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

STATUS: COMPLETE (implementation and deterministic gates; independent review pending)
OWNER: orchestrator /root assembling service-engineer, test-engineer and build-engineer evidence
WORK ORDER: Subphase10B only; user instruction to start10B with prior defaults. Branch phase-10; base and current HEAD c85da7365927a1f7d8ee5ab1f67c5c1a128391b3. Follow AGENTS.md, CLAUDE.md, docs/agents.md and the Drive phase10.md Sections3–10. No reviewer invoked and no later phase started.
FILES CREATED: 17 source/test/example files plus the evidence/10b subtree; exhaustive paths and owners in evidence/10b/source-files.json and files.json.
FILES MODIFIED: 13 source/build/docs files plus owner-report.md, test-report.md and repairs.md. No human-owned gate, commit or approval record changed. Exact final Git lists are retained in evidence/10b/final-validation.json.
COMMANDS RUN: Exact JDK17 gate commands, exits, elapsed times and failed attempts are in evidence/10b/commands.md and *-result.json. Read-only git status/branch/HEAD, diff checks, hashes, YAML/JSON/ref validation and Docker cleanup were also observed.
TEST RESULTS: services26/26 across4suites; existing independent10A20 and final10B17 passed; buildVerification13/13 across8suites. Full sbt -batch check exit0:1199passed/0failed,145suites; sbt708s,wall709.995s,JDK17.0.20.1. Full-log SHA-256 376355f9d008d6aa3e8cb9159fbd3166fde575e0f34372c16bca7af5c5c815a1. All4Dockerimages rebuilt;8role/mode startupsmokespassed; packagedverifiedcount3 lifecycle/replay409/evidence/explainpassed; actual3-main HTTPcomposition/breakergauges/correlationpassed; stoppinggraph produced queryhealth200/ready503. Allcontainers/networkcleaned.
VALIDATION RESULTS: Evidence/explain, bounded graph directions/depth/cursor/path/timeout, semantic retrieval, actual downstream clients, worker idempotency/poisonDLQ, complete16-pathOpenAPI/fiveJSONexamples, thinroutes and packagingassets are implemented and tested. Final30sourcehashes match; only README observedcounts changed after the full-check source snapshot. Prior findings: F1 CLOSED by the prior user-supplied independent review and retained regression tests pass. F2 terminal retryable:false; F3 persisted202state; F4 invalidstartup exit2 inall4images; F5 half-open-failure/429/RESULT_TOO_LARGE tests added. O1 staleimages replaced by4hash-verified rebuiltimages; O2 pre-gate source hashes retained including failed attempts. These10B changes await independent review; no approval is claimed.
ASSUMPTIONS: Use all approved defaults: address F2–F5; graph direction both, default depth1/max3, default limit50/max200, course edge allowlist, snapshot/filter-bound opaque signed cursor, configurable5000ms timeout; evidence/explain from stored provenance/audit with links.evidence; poison threshold3 with DLQ-before-ack and failed-DLQ leave-unacked; rebuild/smoke all4local Docker images, no push. Earlier answers persisted; user explicitly restarted10B after the stop. No questions remained.
RISKS: Explicit offline-synthetic composition uses declared Phase9G1 fixtures; live backend/provider execution and deployment remain unverified human-gated work. The frozen GraphReader lacks direction/snapshot semantics, so live graph deployment needs the stronger GraphSnapshot adapter. Query execution is local and nondurable; worker PROCESSING reservations require crash recovery and DLQ publication/terminal recording are not transactional. Missing cache/retry measurements are null; unknown score weights are absent; internal runtime trace uses query ID linked to HTTP context. New/internal routes currently log safe template label unmatched. Full OpenAPI semantic validation was unavailable; YAML/local refs, committed examples and wire assertions passed. Optional OpenSearch/indexes/CI and cloud deployment were omitted.
MANUAL ACTION REQUIRED: User launches the supplied read-only10B reviewer; after approval the user owns commit and human-gate. No10Bcommit/push was made.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for required local gates. Live deployment/provider gates remain unrun and outofscope.
NEXT GATE: User-launched independent10Breview. Stop; do not startPhase11 or any later work automatically.


## Subphase 10B repair round 1

STATUS: COMPLETE (implementation and local gates; independent recheck pending)
OWNER: orchestrator /root assembling service-engineer, test-engineer and build-engineer reports
WORK ORDER: User-approved F6 plus F9 only. Branch phase-10; base/current HEAD c85da7365927a1f7d8ee5ab1f67c5c1a128391b3; prior uncommitted10B preserved. External review recorded verbatim under Subphase10B in review.md.
FILES CREATED: GraphRequestDeadlineSpec.scala and IndependentServices10BDeadlineSpec.scala, plus evidence/10b-repair-1/. Exact paths in repair-files.json and files.json.
FILES MODIFIED: Seven existing service files for F6/F9; root review/repair/owner/test reports. No build file changed. Repair delta is9 source artifacts; aggregate uncommitted10B source manifest is33 artifacts.
COMMANDS RUN: Exact commands, environment, exits, elapsed times and log hashes in evidence/10b-repair-1/commands.md and *-result.json. Every sbt command used the prescribed JDK17 environment. Pre-gate source hashes, red source text, failed and cancelled attempts retained.
TEST RESULTS: Final services31/31 in5suites; independent10A/B41/41 in7suites; packageServices passed. Final full sbt -batch check exit0:1208passed/0failed,147suites; sbt709s,wall710.548s,JDK17.0.20.1. LogSHA256 39aaf21ff6902af2bcde194c7e45622f207aa9338adebaaf5b04dc8b2bc6f4d3. Full modules: core207,hadoop64,entityResolution39,sparkAnalytics38,storage80,rag107,services31,independent629,buildVerification13. Four images rebuilt, eight boot cases and three-main HTTP/stop-graph checks passed; all11containers/network cleaned.
VALIDATION RESULTS: Independent pre-fix regression failed4run/3pass/1fail. Final burst sends4deadline requests without readiness resets: one backend call each, caller-traced nonretryable504, CLOSED gauge before probes, readiness200 and later normal success. True refusal, no-response timeout and unready503 still trip circuit and fail readiness. Safe typed marker parsing is restricted to graph GET operations; unknown/malformed/wrong-scope errors retain dependency classification. General422/F12 behavior unchanged. F9 prior counts corrected to observed36/36six-suite and17/17four-suite gates; prior37 together occurred only inside full625. New41-test repair gate was actually observed. All33 final hashes match; only README final counts changed after full-check snapshot.
ASSUMPTIONS: User selected “F6 + F9 count corrections (Recommended)”; all other findings carried. Tests use authenticated loopback stubs and declared synthetic offline fixtures; no live claim.
RISKS: F7 and F8 worker behaviors, F10 stage/index/template detail, F11 route labels, F12 general graph422 code preservation, F13 response examples/schema, F14 environment/path configuration, and F15 internal-surface/local-fixture wiring remain carried and unchanged. Live adapters/deployment, stable multi-replica cursor key injection, SQS redrive, durable dispatch/PROCESSING recovery and full third-party OpenAPI validation remain later human-gated work.
MANUAL ACTION REQUIRED: User launches the complete read-only recheck prompt in evidence/10b-repair-1/reviewer-prompt.md. User owns acceptance, commit and human gate. No agent commit/push/reviewer/cloud/provider/human-gate action occurred.
BLOCKED-ON OWNER: None for required local repair work.
BLOCKED-ON EVIDENCE: None for required local gates.
NEXT GATE: User-launched read-only Subphase10B repair round1 recheck; stop before Phase11.


## Subphase 10B repair round 2

STATUS: COMPLETE (implementation/local gates; independent recheck pending)
OWNER: orchestrator /root assembling service-engineer,test-engineer,build-engineer evidence
WORK ORDER: F6 residual only, explicitly confirmed by user “yes fix f6 for me, since it is the blocking bug”. Branch phase-10; base/currentHEAD c85da7365927a1f7d8ee5ab1f67c5c1a128391b3; all uncommitted10B and repair1 preserved. Repair1 external verdict recorded verbatim in review.md; F9 CLOSED by that recheck.
FILES CREATED: GraphTransportBudgetSpec.scala,IndependentServices10BEqualBudgetSpec.scala and evidence/10b-repair-2/.
FILES MODIFIED: Seven service artifacts and two independent test-double wrappers; phase review/repair/owner/test reports by orchestrator. Repair delta11sourcefiles(8service,3test),aggregate35sourceartifacts. No build file changed. Exact paths/owners/hashes in repair-files.json,source-files.json,files.json.
COMMANDS RUN: evidence/10b-repair-2/commands.md and named *-result.json bind every exact JDK17 command,exit,time,loghash and pre-run source snapshot. Red sources retained verbatim. No buildVerification-only rerun required(no build changes); fullcheck included13/13.
TEST RESULTS: Independent red3run/1pass/2fail; module red4run/0pass/4fail. Green services36/36 in6suites,independent10A/B44/44 in8suites,packageServicespassed,exit0,20.061s. Final fullcheck1216passed/0failed,149suites,exit0,JDK17.0.20.1,sbt721s/wall723.581s. Full-logSHA256 8930aa7a4c872e6412011fc362a2e00b5cb5a18640b059bc9e8b8dfffe26c526. Fourimages rebuilt/eightstartupcases passed; actual3-mainremotecomposition explicitlyequal500mscaps andstopgraphoutage readinesspassed. All11containers/network cleaned.
VALIDATION RESULTS: Omitted and explicit cap budget tests use actualGraphApi300ms behindproxy300ms,burst4 before readiness,one snapshotexecutioneach,tracednonretryableGRAPH_DEADLINE_EXCEEDED,CLOSEDbeforeprobes,ready200 andnormalrecovery. Proxy now always forwards min(validrequested/defaultcap,T-ceil(T*reservePercent/100)) fornode/neighbors/metrics/paths; default25percent yields3750msworkatT5000. Budgets deterministic for cursorbinding,invalidcaller400,tinyimpossiblegraphconfigrefused; safe narrowmarker andtrueoutagebehavior preserved. Existing wrappers forwardnewparameters whileoriginalassertionsremain. All35sourcehashes match; onlyREADMEfinalcounts changed afterfullsnapshot. No F16backendreadinesschange.
ASSUMPTIONS: F6onlyscope;percent25defaultresponse reserve/configuredgraphcap;declaredsynthetic/localHTTPfixtures. No liveproviderclaim.
RISKS: F7,F8,F10–F16 remain carried and unchanged; F9 is CLOSED by the external recheck. A live GraphSnapshot adapter still needs backend readiness (F16). Live adapters/deployment,stable cursor-key injection,SQS redrive,durable dispatch/PROCESSING recovery and a full third-party OpenAPI validator remain later human-gated work. The configured response reserve provides explicit headroom, not immunity to arbitrary network delay; genuine transport failures remain dependency failures.
MANUAL ACTION REQUIRED: User launches complete read-only recheck prompt in evidence/10b-repair-2/reviewer-prompt.md;user owns acceptance,commit,human gate. No agentcommit/push/reviewer/cloud/provider/Phase11/human-decision action occurred.
BLOCKED-ON OWNER: None for requiredlocalrepair.
BLOCKED-ON EVIDENCE: None for requiredlocalgates.
NEXT GATE: User-launched Subphase10B repair2read-onlyrecheck;stop.
