# Subphase 10B repair round 2 handoff

STATUS: COMPLETE — implementation and local gates; independent recheck pending.
OWNER: Orchestrator assembling service, independent-test and build owners.
WORK ORDER: F6 residual only, explicitly authorized by the user.
FILES CREATED: Two regression suites and this evidence subtree.
FILES MODIFIED: Seven service artifacts, two independent test doubles and phase reports.
Repair-only 11 source files; aggregate 35. Exact paths/owners/hashes: repair-files.json,
source-files.json, files.json and final-validation.json.
COMMANDS RUN: Exact commands/exits/times/hashes in commands.md and named gate result JSON.
TEST RESULTS: Targeted36/36 service tests,44/44 independent tests; full1216/1216 in149 suites,
exit0, JDK17.0.20.1, sbt721s/wall723.581s. Four images/eight startup cases and the three-main
remote/stop-graph checks passed. Genuine pre-fix red failures are retained.
VALIDATION RESULTS: Both omitted and explicit equal300ms budgets now produce one typed,
traced graph deadline per request, preserve CLOSED before readiness probes, then readiness200
and normal success. All four operation types consume deterministic forwarded work budgets.
Default transport5000ms forwards at most3750ms with the configured25percent response reserve.
All35 hashes match; only README final counts changed after the full-check snapshot.
ASSUMPTIONS: User confirmed F6 only. Branch phase-10; base/currentHEAD
c85da7365927a1f7d8ee5ab1f67c5c1a128391b3. All prior uncommitted work preserved.
RISKS: F7,F8,F10–F16 remain carried. Live backend/deployment/recovery work remains later scope.
MANUAL ACTION REQUIRED: User launches the complete read-only prompt below; user owns commit/human-gate.
BLOCKED-ON OWNER: None.
BLOCKED-ON EVIDENCE: None for required local gates.
NEXT GATE: User-launched independent recheck; stop before Phase11.

No commit, push, provider/cloud call, reviewer invocation or human-decision edit occurred.
All specialist agents, builds, task containers and the temporary network have stopped.

```text
You are the independent, read-only code reviewer for ScholarChain Phase 10,
Subphase 10B repair round 2, in:
/Users/danny/Documents/UIC/CS441/ScholarChain

Read in order:
1. AGENTS.md, CLAUDE.md, docs/agents.md, .claude/agents/code-reviewer.md,
   docs/agent-runs/README.md.
2. /Users/danny/Library/CloudStorage/GoogleDrive-cpnguyen0630@gmail.com/My Drive/plan/phase10.md
   Sections 3–7, Subphase 10B in Section 8, and Sections 9–10.
3. The course Phase 10 specification:
   https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-10-expose-the-runtime-through-restful-microservices
4. docs/agent-runs/phase-10/review.md, repairs.md, owner-report.md and test-report.md
   (repair round 2 sections), then evidence/10b-repair-2/external-review.txt,
   work-order.md, acceptance.md, regression-notes.md, repair-source.diff,
   repair-files.json, source-files.json, commands.md, check-summary.json,
   final-validation.json, files.json and the owner/Docker reports.
All short evidence paths below refer to docs/agent-runs/phase-10/evidence/10b-repair-2/.

Checkpoint facts:
- Branch: phase-10.
- Base SHA and current HEAD: c85da7365927a1f7d8ee5ab1f67c5c1a128391b3.
- All 10B and repair changes remain uncommitted. Nothing was reset, discarded or pushed.
- Exact aggregate changed/untracked lists: files.json and final-validation.json.
- Aggregate current source: 35 hashed artifacts. Repair-only delta: 11 files,
  eight service-owned and three independent-test-owned. No build file changed:
- modules/services/README.md
- modules/services/src/main/resources/openapi/scholarchain.v1.yaml
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiApplication.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/ApiContracts.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/GraphApi.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/RemoteServices.scala
- modules/services/src/main/scala/edu/uic/cs441/scholarchain/services/SemanticApi.scala
- modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/GraphTransportBudgetSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BDeadlineSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BEqualBudgetSpec.scala
- tests/src/test/scala/edu/uic/cs441/scholarchain/independent/IndependentServices10BLifecycleSpec.scala
- Other changes are orchestrator-owned phase reports and the repair evidence subtree.
  source-before.json binds the prior source hashes; repair-source.diff isolates this round.
  No human decision file changed.

Step 0 answer:
The user explicitly confirmed: “yes fix f6 for me, since it is the blocking bug”.
Only F6 residual was authorized. F9 is CLOSED by the previous external recheck.
F7, F8 and F10–F16 remain carried and unchanged. No questions remain.

Implementation to verify:
Every allowlisted graph GET (node, neighbors, metrics, paths) forwards an explicit
work budget min(valid caller budget or configured graph cap, T - ceil(T*P/100)).
T is the per-attempt transport deadline; P defaults to 25 percent and is configurable
from 1 to 99. Default equal 5000 ms caps forward 3750 ms, leaving 1250 ms for response
delivery. Equal 300 ms caps forward 225 ms. An explicitly requested 1 ms stays 1 ms.
Invalid caller budgets return 400 before a backend call. Overflow-safe arithmetic
and refusal of impossible nonpositive work budgets are tested.

Graph-service consumes the forwarded budget on all four operations, including
blocking node/metric reads and path expansion. Cursor binding remains deterministic:
forwarding depends on configuration and requested budget, not elapsed time or network
state. README and OpenAPI document the rule. Narrow marker parsing, fixed safe error
message, caller trace, no retry/breaker failure for a recognized graph deadline, and
true-outage behavior remain intact. F16 snapshot-backend readiness was not changed.

Required acceptance evidence:
IndependentServices10BEqualBudgetSpec uses actual GraphApi with a blocking interruptible
snapshot, graph cap 300 ms and proxy transport 300 ms. Both omitted timeout and explicit
timeoutMs=300 send four requests before any readiness/successful downstream probe.
Each returns 504 GRAPH_DEADLINE_EXCEEDED, retryable:false and the caller's trace; exactly
four snapshot executions occur. The test asserts CLOSED before readiness, then readiness
200 and later normal node/neighbor success. Real cursor replay remains stable.
Prior refusal, silent/no-response timeout and unready-503 cases still pass.

Regression provenance:
- Independent red: three tests, one passed and two failed. Both equal-budget cases
  caused three snapshot executions for four public requests; cursor replay passed.
  Exact formatted red source is retained and is byte-identical to the final new test.
- Module red: four tests, all failed behaviorally before production edits. Missing
  forwarded budgets, config validation, caller-budget rejection and equal-budget
  transport classification were observed. The final module suite has five tests,
  adding nondefault environment/configuration cases and expanded real all-operation guards.
- Two existing independent test doubles gained budget-aware overload forwarding.
  Existing retry/status/correlation assertions remain. No expectation was weakened.

Exact gates:
Working directory: /Users/danny/Documents/UIC/CS441/ScholarChain.
Every sbt command used exactly:
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
Observed Java 17.0.20.1. Source hashes were recorded before every gate.
- `java -version`: exit 0, 0.019 seconds. Metadata: java-version-result.json.
- `sbt -batch 'services / Test / scalafmt' 'independentTests / Test / scalafmt'`: exit 0, 2.820 seconds. Metadata: format-red-result.json.
- `sbt -batch 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10BEqualBudgetSpec'`: exit 1, 7.895 seconds. Metadata: independent-red-result.json.
- `sbt -batch 'services / Test / testOnly edu.uic.cs441.scholarchain.services.GraphTransportBudgetSpec'`: exit 1, 6.032 seconds. Metadata: module-red-result.json.
- `sbt -batch 'services / Compile / scalafmt' 'services / Test / scalafmt' 'independentTests / Test / scalafmt' 'services / test' 'independentTests / Test / testOnly edu.uic.cs441.scholarchain.independent.IndependentServices10A* edu.uic.cs441.scholarchain.independent.IndependentServices10B*' packageServices`: exit 0, 20.061 seconds. Metadata: targeted-green-result.json.
- `sbt -batch check`: exit 0, 723.581 seconds. Metadata: check-result.json.

Targeted green: services 36/36 in six suites; independent 10A/B 44/44 in eight suites;
packageServices passed. Final full check: 1216 passed, zero failed, 149 suites,
sbt 721 seconds (12:01), wall 723.581 seconds.
Module counts: core207, hadoop64, entityResolution39, sparkAnalytics38, storage80,
rag107, services36, independentTests632, buildVerification13.
No standalone buildVerification rerun was required because no build files changed;
the full check passed all 13 build tests.
Full log: /tmp/phase10b-r2-check.log
SHA-256: 8930aa7a4c872e6412011fc362a2e00b5cb5a18640b059bc9e8b8dfffe26c526.
The nested injected-format error is intentional CheckFailurePathSpec behavior;
its parent test and the outer gate passed. No cancelled repair-2 gate occurred.

Docker evidence:
DOCKER_CONFIG=/tmp/phase10b-docker-config DOCKER_HOST=unix:///Users/danny/.docker/run/docker.sock python3 /tmp/phase10b-r2-docker.py
Exit 0, 14.451 seconds. Four rebuilt images/eight startup cases passed: expected mains,
UID999, invalid-config exit2, health/readiness distinction, authenticated metrics,
verified fixture count3, replay200, conflict409, evidence/explain200.
Same environment, python3 /tmp/phase10b-r2-docker-remote.py:
exit0, 2.749 seconds. Three actual mains used explicitly equal graph/proxy 500 ms caps,
returned verified3, exposed CLOSED gauges and propagated correlation. Stopping graph
preserved query health200 and produced traced readiness503 NOT_READY in 0.581 seconds.
JAR SHA-256: 5a02a92e12306cc84d5e0bfd45a8bdf8c8d98a7ed8a53a6d4a02bebc90d16eb3.
The JAR and four prompt assets match inside every image. Image IDs, exact argv, hashes
and cleanup are in the copied Docker result JSON. Both first attempts passed; all 11
containers and the isolated network were removed.
Raw Docker log SHA-256: 07fe2d932e77d9eede95926284aa22279e37345a6f7161e2d7e2fc5361611e82.
Raw remote log SHA-256: c9d4553930390d2a73e260f100a2b54543816fdc985082d241a5c579a718474a.

Final checks:
35/35 source hashes and 11/11 repair hashes match. Only README's observed-count summary
changed after the full-check source snapshot; no Scala/test/build/resource changed.
git diff --check exited0. OpenAPI YAML/local-reference checks passed:16 paths and103 refs.
Existing wire examples passed. A full third-party semantic validator was not available.
All specialist agents and task jobs stopped. No reviewer was invoked.

Carried findings and limitations:
F1–F5 and O1–O2 had no regression in the prior recheck; F9 is externally CLOSED.
F7 processor calls after DLQ failure; F8 worker exception health; F10 stage/index/template
visibility; F11 unmatched route labels; F12 general422 code preservation; F13 response
examples/schema; F14 semantic environment/prompt path; F15 internal semantic/local fixture
path wiring; F16 live GraphSnapshot backend readiness remain unchanged.
Live adapters/deployment, stable cursor-key injection, SQS redrive, durable dispatcher and
PROCESSING recovery, and full OpenAPI validation remain later human-gated work. Configured
response headroom does not claim immunity to arbitrary network delay; genuine transport
failures remain dependency faults. No Phase11, cloud/provider call, commit, push or human-gate edit.

Review rules:
Read-only. Do not edit, run builds/tests/Docker, call AWS/providers, change data, read secrets,
commit or push. Inspect git diff against the base plus untracked files and the repair-only diff.
Report all confirmed findings in one pass. Check ownership/scope, configuration/provenance,
no secrets, honest hashes/logs, meaningful independent tests, thin routes, conditional
idempotency, auth, traced errors, safe logs, readiness, retries/breakers, packaging and OpenAPI.
Verify F6 residual closure for omitted and near-cap budgets on all four operation types;
check strict-marker and genuine-outage regression safety. Distinguish blocking defects,
nonblocking observations and later live gates. Do not require later deployment work here.

Return:
1. VERDICT: APPROVE or REQUEST-CHANGES for Subphase 10B repair round2.
2. Findings: severity, path:line, evidence/impact, owner, acceptance check, blocking yes/no.
3. Report fields from docs/agent-runs/README.md.
4. Complete NEXT PROMPT in one fenced block:
   If APPROVE, append your verdict verbatim as user-supplied external review under repair2,
   confirm the user's commit, and state Phase10 is ready for their human-gate. Phase11 is
   next but must not start automatically. Do not write human decisions.
   If REQUEST-CHANGES, append verdict/findings, route blockers to their owners, rerun affected
   and full JDK17 gates, return another recheck prompt and stop. Do not invoke a reviewer.
```

Subphase 10B repair round 2 is ready for review. I have stopped and will not start the next subphase until I receive the next prompt.
