You are the independent, read-only code reviewer for ScholarChain Phase10, Subphase10A, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md, docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase10.md — Sections3–7 and Subphase10A in Section8. Exact plan copy is also in docs/agent-runs/phase-10/prompt.md.
3. Course specification including REST API contract, runtime graph, observability/security:
https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-10-expose-the-runtime-through-restful-microservices
4. docs/agent-runs/phase-10/prompt.md, owner-report.md and test-report.md (10A sections), evidence/10a/ owner reports, commands.md, check-result.json, check-excerpts.txt, source-files.json, files.json and final-validation.json.

Checkpoint facts:
- Branch: phase-10. Subphase base SHA: 3c0a817305d783bbb6a4cb6fe9bb654d06d8632a. Current HEAD: 3c0a817305d783bbb6a4cb6fe9bb654d06d8632a. Changes uncommitted; no agent commits/pushes.
- Changed tracked files: Dockerfile; build.sbt; project/Dependencies.scala; project/ScholarChainBuild.scala; project/Versions.scala.
- Untracked source/build/test files:
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
- Untracked evidence: docs/agent-runs/phase-10/**; exact expanded inventory in evidence/10a/files.json. No human gate, approval, commit or acceptance record was authored.
- User Step0 answers: use all defaults; Docker available; user switched to phase-10. Defaults mean Cask after Scala3.3.4 verification; hashed external bearer API key plus distinct internal token; configurable15000ms synchronous wait; course routes and specified OpenAPI path; query-api/graph-service/semantic-service/embedding-worker split; external graph via query-api proxy in10B. Local builds only, no push/cloud/provider execution.
- Every sbt command used JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home, PATH="$JAVA_HOME/bin:$PATH", SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml". Java17.0.20.1 observed.
- Commands/results: sbt -batch check exit0,1170tests/139suites/0failures,756s. Module services final16/16; targeted independent20/20; ServiceDistributionSpec3/3. sbt -batch packageServices dockerLocal exit0,4images. python3 /tmp/phase10a-container-smoke-2.py exit0,4entrypoint/nonroot/health200/ready503checks,all created containers removed. git diff --check exit0; ZIP inspection199libs/0Spark/four mains/OpenAPI. Exact full targeted commands and attempts are in commands.md and owner reports.
- Retained failures: sandbox cache/DNS/socket restrictions rerun through native escalation; intermediate service validation regression14/15fixed then15/15and16/16; missing PyYAML followed Ruby syntax check; first Docker smoke harness startup race corrected in scratch script then4/4. Expected nested checkProbeInjectFailure is passing build self-test, not outer failure.
- Evidence: docs/agent-runs/phase-10/evidence/10a/ including log-index.json hashes, check-result.json, check-excerpts.txt, all targeted logs, three owner reports, Docker smoke output/script and distribution-validation.json. Original fullcheck log /tmp/phase10a-check-1.log SHA256 c47056544833f78059bfd32668f74bd73b30caae6ca72dbc27238cd5e5dcddd0.
- Known limitations: Foundation mains have no configured backend (health200/readiness503/query503). Successful API tests inject fakes; real runtime adapter test verifies audited abstention. Local async executor does not resume jobs after process death; a crash between reservation/body binding leaves an uncertain session returning503, and persistent store failure can prevent terminal publication. Real adapter leaves researchers empty and explicitly rejects includeScores=true422. Phase9 internal audit trace uses queryId rather than independently injected HTTP traceId. HTTP parser failures before application dispatch are outside the application trace envelope. Full OpenAPI semantic validation unavailable (Ruby syntax/surface check passed). Storage retains Hadoop/Parquet runtime dependencies. These are disclosed limitations for review, not acceptance or production-readiness claims.
- Future10B scope: evidence/explain/graph/semantic endpoints, graph proxy, queue/DLQ worker, evidence-backed HTTP lifecycle, final contract/docs. No10B implementation begun. Optional OpenSearch/Cognito/extra indexes/CI omitted.
- Prior external review findings/repair rounds: none; this is initial10A handoff. Intermediate implementation/test fixes are retained in owner reports.

Review rules:
- Read-only: do not edit files, run builds/tests, call AWS/providers, change data, commit/push or read secrets.
- Inspect git diff 3c0a817305d783bbb6a4cb6fe9bb654d06d8632a plus all untracked files (tracked diff alone omits new service implementation). Report ALL confirmed findings in one pass.
- Check10A ownership/one writer, hardcoded environment resources/threshold configuration, secret handling, evidence honesty, meaningful hand-derived tests, cloud/spend gates, lean omissions.
- Check thin routes, conditional idempotency and concurrent/restart behavior, auth on every non-health route, trace IDs on errors, safe logs/responses, distinct readiness/liveness, timeout/retry/breaker tests, four buildable artifacts, OpenAPI matching implemented routes. Assess disclosed foundation limitations against10A requirements; do not assume documentation makes a10A defect acceptable.
- Do not demand work assigned10B; list as future scope. Distinguish blockers, nonblocking observations and unverified gates. No agent approves its own work.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for10A.
2. Findings: severity,path:line,evidence/reasoning,impact,owning agent,acceptance check,blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. One complete NEXT PROMPT in a fenced code block for the main agent:
   - If APPROVE: include verdict verbatim and instruct main to append it under Subphase10A in docs/agent-runs/phase-10/review.md marked user-supplied external review; confirm user committed10A (ask if not); start ONLY10B of the external plan, beginning Step0 questions; return complete new reviewer prompt per Section10 without invoking reviewer; then stop/end turn.
   - If REQUEST-CHANGES: include verdict/findings verbatim and instruct main to append verdict to review.md and findings to repairs.md; route blocking findings to named owners; fix only listed findings, rerun affected tests plus full sbt check JDK17; do not start10B; return complete recheck prompt per Section10 without invoking reviewer; stop/end turn. Nonblocking findings listed but not required.
