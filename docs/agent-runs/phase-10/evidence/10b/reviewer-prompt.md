You are the independent, read-only code reviewer for ScholarChain Phase 10,
Subphase 10B, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read, in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase10.md,
   Sections 3–7, Subphase 10B in Section 8, and Sections 9–10.
3. The course Phase 10 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-10-expose-the-runtime-through-restful-microservices
4. docs/agent-runs/phase-10/prompt.md, owner-report.md, test-report.md and
   repairs.md (Subphase 10B sections), then evidence/10b/work-order.md,
   handoff.md, commands.md, source-files.json, check-summary.json,
   final-validation.json, prior-findings.md and the retained owner/Docker reports.
   All evidence paths above are under docs/agent-runs/phase-10/.

Checkpoint facts:
- Branch: phase-10.
- Subphase base SHA and current HEAD:
  c85da7365927a1f7d8ee5ab1f67c5c1a128391b3.
- 10A including its approved repair was committed before 10B. 10B is uncommitted.
- Changed tracked files:
- Dockerfile
- docs/agent-runs/phase-10/owner-report.md
- docs/agent-runs/phase-10/repairs.md
- docs/agent-runs/phase-10/test-report.md
- modules/services/README.md
- modules/services/src/main/resources/openapi/scholarchain.v1.yaml
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiApplication.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiServer.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/DownstreamClient.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/QueryService.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RuntimeWorkflowAdapter.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ServiceMains.scala
- project/ScholarChainBuild.scala
- project/ServiceDistribution.scala
- project/ServicesPackaging.md
- project/verification/src/test/scala/scholarchain/build/ServiceDistributionSpec.scala
- New source/test/example files:
- modules/services/src/main/resources/openapi/examples/error.json
- modules/services/src/main/resources/openapi/examples/graph-page.json
- modules/services/src/main/resources/openapi/examples/job-reference.json
- modules/services/src/main/resources/openapi/examples/query-request.json
- modules/services/src/main/resources/openapi/examples/semantic-request.json
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/EmbeddingWorker.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/EvidenceApi.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/GraphApi.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/OfflineComposition.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RemoteServices.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/SemanticApi.scala
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/Services10BSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BFixture.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BGraphSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BLifecycleSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BStructureSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BWorkerSpec.scala
- The other untracked files are the evidence artifacts under
  docs/agent-runs/phase-10/evidence/10b/. Their exhaustive exact paths are in
  evidence/10b/files.json. No human-gate, commit or approval record was written.
- Source ownership: 20 service files, five build files and five independent-test
  files; all 30 final hashes match. Full-check source comparison differs only
  in README's later update of observed test/Docker counts.

Step 0 answers:
The user authorized defaults and explicitly restarted 10B after the prior stop.
Include F2–F5; graph direction both, default depth 1/max 3, default limit 50/max
200, course edge allowlist, opaque signed cursor bound to node/snapshot/filters,
configurable 5000 ms hard timeout. Evidence/explain project stored provenance and
observable audits, and query responses link evidence. Worker poison threshold is
3 configurable attempts; enqueue to DLQ before acknowledging, and leave the source
unacknowledged when DLQ publication fails. Rebuild/smoke all four local Docker
images; no push. No unanswered Step 0 questions remained.

Exact central commands (each sbt command used the environment below):
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
java -version
Observed Homebrew 17.0.20.1, exit 0.

1. sbt -batch 'services / Test / compile'
   Exit 1: metadata JSON type mismatch; 7.844 s; no tests ran.
2. sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10B*'
   Attempt targeted-1: exit 1, same compile error, 6.012 s, no tests ran.
   Attempt targeted-2: exit 1, 11.996 s; services 25/25, independent 13/16.
   The three failures exposed unfinished OpenAPI routes and Cask's graph-query
   parameter rejection; service fixes retained the independent expectations.
3. sbt -batch scalafmtSbt 'buildVerification / Compile / scalafmt' 'buildVerification / Test / scalafmt' 'buildVerification / test'
   Exit 0, 13/13 tests, eight suites, 15.620 s.
4. sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A* edu.uic.cs441.scholarchain.independent.IndependentServices10B*'
   Exit 0, services 26/26 in four suites and independent 36/36 in six suites,
   11.579 s. A final example-contract test was added afterward.
5. sbt -batch 'independentTests / Test / scalafmt' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10B*' packageServices
   Exit 0, final 10B independent 17/17 in four suites; four-artifact packaging
   passed; 8.119 s.
6. sbt -batch check
   Exit 0, 1199 passed/0 failed, 145 suites; sbt 708 s (11:48), wall 709.995 s.
   Module counts: core207, hadoop64, entityResolution39, sparkAnalytics38,
   storage80, rag107, services26, independentTests625, buildVerification13.
   /tmp/phase10b-check.log SHA-256:
   376355f9d008d6aa3e8cb9159fbd3166fde575e0f34372c16bca7af5c5c815a1.
   CheckFailurePathSpec intentionally emits a nested injected-format failure;
   its parent test and the outer check passed.
7. git diff --check: exit 0. Final source hashes and package hashes match.
   Ruby YAML/local-reference validation: 16 paths, 97 resolved references;
   five JSON examples parsed and exercised by wire-contract tests. This is not
   a full third-party OpenAPI semantic-validator claim.

Docker evidence:
- Docker 29.5.3; all four images rebuilt, eight role/mode startup smokes passed,
  non-root UID999, correct main, missing configuration exit2, authenticated
  metrics. Unconfigured health200/ready503; explicit offline health200/ready200.
- Packaged query: verified fixture publication count3, same-key replay200,
  different-body409, evidence collection/item/explain200.
- Three packaged mains on an isolated internal Docker network made actual graph
  and semantic HTTP calls with propagated correlation and registered breaker
  gauges. Stopping graph left query health200 and produced traced ready503.
- Successful commands used temporary empty Docker authentication configuration:
  DOCKER_CONFIG=/tmp/phase10b-docker-config DOCKER_HOST=unix:///Users/danny/.docker/run/docker.sock python3 /tmp/phase10b-docker.py
  Exit0,13.530s. Same environment python3 /tmp/phase10b-docker-remote.py,
  exit0,2.805s. Exact argv/results/image IDs/hashes are in the copied Docker JSON.
- First build was cancelled after a credential-helper stall (build130,
  harness1,165.960s). Three integration harness failures were retained: internal
  network host-port lookup, startup curl parsing, overly specific log-template
  expectation. No production change bypassed required behavior.
- Application JAR SHA-256:
  e3a8103743f00bd36e64919256b31d9084a903783d9f100288a0787d73783878.
  It and four prompt assets match inside all four images. All task containers
  and the temporary network were removed; no builds/subagents remain running.

Prior findings and handling:
- F1: CLOSED by prior user-launched review; Retried Written/Unchanged/Rejected
  regression tests remain and pass. Verify no regression to creator ownership.
- F2 Medium, service-engineer: terminal failures now persist retryable:false;
  replay remains terminal, new key required for a deliberate new workflow.
- F3 Low, service-engineer: 202 reference reports persisted QUEUED/RUNNING state.
- F4 Low, service-engineer: invalid startup exits2, observed for all four images.
- F5 Low, service/test-engineer: failed half-open probe, queue-full429 and
  RESULT_TOO_LARGE cases added and passing.
- O1 build-engineer: stale images replaced with hash-verified rebuilt artifacts.
- O2 orchestrator: source hashes retained before every gate, including failures.
These 10B treatments await your review; no agent has approved its own changes.

Known limitations:
- Offline-synthetic mode explicitly uses declared fixtures. No live cloud/model
  call, provider/deployment claim, optional OpenSearch/index or CI was added.
  Live backend composition remains later human-gated work.
- Frozen GraphReader lacks direction/snapshot guarantees; live deployment needs
  a proper GraphSnapshot adapter or a typed unsupported response.
- Query dispatcher is local/nondurable; unbound or pending rows can require
  recovery after a crash. Worker PROCESSING has no guessed lease takeover;
  DLQ publication and terminal recording are not transactional.
- Unknown retry/cache measurements are null; unavailable score weights absent.
  Internal runtime trace uses query ID, linked to HTTP context. New/internal
  request logs use the safe label unmatched. No hidden model reasoning is exposed.
- Full OpenAPI semantic validator unavailable; source scanning is heuristic.
  Bounded actual HTTP examples and contract/behavior tests provide the stated evidence.

Review rules:
- Read-only. Do not edit files, run builds/tests/Docker, call AWS or any provider,
  change data, commit or push. Do not read secrets or rewrite human decisions.
- Inspect git diff c85da7365927a1f7d8ee5ab1f67c5c1a128391b3 plus untracked files.
  Report all confirmed findings in one pass.
- Check one-writer ownership, configuration/provenance, no secrets, honest logs
  and hashes, meaningful independent assertions, required task coverage and
  respected cloud/spend gates. Verify F2–F5 treatments and F1 regression safety.
- Check thin routes, conditional idempotency, auth on all non-health routes,
  traced errors, safe logs, readiness, retries/timeouts/breakers, worker poison
  behavior, all four artifacts and OpenAPI consistency. Verify required end-to-end
  evidence-backed answer and actual downstream wiring/breaker registration.
- Distinguish blocking defects, nonblocking observations and unverified live gates;
  do not demand later deployment work as this subphase's implementation scope.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 10B.
2. Every finding: severity, path:line, evidence/reasoning, impact, owning agent,
   acceptance check, blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. A complete NEXT PROMPT in one fenced block for the main orchestrator:
   If APPROVE, tell it to append your verdict verbatim as user-supplied external
   review under Subphase 10B, confirm the user's commit, and tell the user Phase10
   is ready for their human-gate and Phase11 is next. Do not start Phase11 automatically.
   If REQUEST-CHANGES, tell it to append your verdict/findings verbatim to review.md
   and repairs.md, route blocking findings to their listed owners, repair only the
   authorized scope, rerun affected tests and full JDK17 check, return a recheck
   prompt, and stop. Do not launch another reviewer or write human decisions.
