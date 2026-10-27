
# Subphase 10A

user-supplied external review

VERDICT: REQUEST-CHANGES for Subphase 10A.
F1 (High, BLOCKING) — QueryService.scala:182-195 with StorageRows.scala:208 and
DynamoStorage.scala:161-171. DynamoRows.transact retries with a fixed ClientRequestToken; a
successful retry makes RowSessions.createIfAbsent return Retried(n, Written(session)), meaning
this caller created the reservation. QueryService.submit treats every Retried as a lost reply,
never binds the fingerprint or schedules the workflow, polls an unbound "{}" row and returns
503; all replays and GET /v1/jobs/{jobId} for that key then return 503 permanently. No test
covers Retried. Owner: service-engineer. Acceptance: a module test whose store returns
Retried(1, Written(s)) from createIfAbsent gives exactly one workflow run, a 200 (or 202 with
a valid jobId) first response, a same-body replay of the stored result without rerun, and 409
for a different body; Retried(n, Rejected(..)) and Retried(n, Unchanged(..)) still reconcile
without starting work; services/test, the 10A independent tests and full sbt -batch check on
JDK 17 pass.
F2 (Medium, nonblocking) — QueryService.scala:147-151,105-110: a queue-full 429 and exhausted
retryable 502/503/504 failures are persisted with retryable:true, so same-key retries can never
succeed. Replay stored terminal failures as retryable:false, or document/test that a new
Idempotency-Key is required. Owner: service-engineer.
F3 (Low, nonblocking) — QueryService.scala:118: the 202 job reference always reports status
QUEUED, even while RUNNING. Owner: service-engineer.
F4 (Low, nonblocking) — ServiceMains.scala:10: configuration failure exits the JVM with code 0;
it should exit nonzero. Owner: service-engineer.
F5 (Low, nonblocking) — no tests for a failed half-open probe reopening the breaker, the 429
queue-full path or RESULT_TOO_LARGE. Owners: test-engineer / service-engineer.
Future scope (10B): links.evidence in the sync response; DownstreamClient production wiring and
breaker gauges in the mains; graph/semantic/worker/explain/evidence routes; lifecycle test;
final OpenAPI.

# Subphase 10A repair round 1

user-supplied external review

VERDICT: APPROVE for Subphase 10A repair round 1.
F1 CLOSED: QueryService.scala:127-133 rewrites only Retried(_, Written(s)) to Written(s), which
then uses the same body-binding, revision CAS and scheduling path as a normal creation; all other
Retried outcomes still reconcile without execution. RetriedSessionCreationSpec failed before the
fix (3 tests/2 passed/1 failed, retried creator returned 503) and covers every acceptance
assertion: 200 or 202 with a valid jobId, stored same-body replay, 409 for a different body,
exactly one workflow run, persisted SUCCEEDED row, and zero runs for Retried Unchanged/Rejected.
Evidence verified: 23/23 source hashes match; only QueryService.scala and the services README
changed; full sbt check log SHA-256 964d6d80…b223f, 1173 passed/0 failed, 140 suites, exit 0,
JDK 17.0.20.1.
Nonblocking, carried: F2 (Medium) stored terminal failures keep retryable:true although a
same-key replay never reruns; F3 (Low) 202 reference always says QUEUED; F4 (Low) invalid
startup configuration exits 0; F5 (Low) missing tests for a failed half-open probe, the queue-full
429 path and RESULT_TOO_LARGE; O1 local Docker images predate F1 (rebuild in 10B task 7); O2 the
spec text from the failing pre-fix run was not hash-retained (line 63 vs current line 75 after
formatting).


# Subphase 10B

user-supplied external review

```text
VERDICT: REQUEST-CHANGES for Subphase 10B. One defect blocks approval (F6). Everything else is nonblocking or belongs to later live-deployment gates.

I re-checked the evidence without editing anything or running builds, tests or Docker:
- All 30 source hashes match source-files.json. Compared with the full-check snapshot, only modules/services/README.md changed.
- The full-check log and both Docker log hashes match the recorded values.
- The per-module counts add up to 1199, with 0 failures.
- git diff --check passes, and HEAD is c85da73.
- Every file was written by its listed owner, no human-gate file was touched, and no secrets were found (the Docker arguments contain only the synthetic placeholder hashes).

Prior findings

┌───────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  ID   │                                                                Result                                                                 │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ F1    │ No regression. Retried(_, Written) still takes the creator path (QueryService.scala:132-135), and the other retried outcomes still    │
│       │ reconcile without running the workflow.                                                                                               │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ F2    │ Fixed. Terminal failures are now saved with retryable:false (QueryService.scala:209-220). The first response and every same-key       │
│       │ replay are identical, and Services10BSpec:39-78 tests this.                                                                           │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ F3    │ Fixed. The 202 reference reports the stored state (QueryService.scala:114-123). There is a test that a replay shows RUNNING.          │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ F4    │ Fixed. A bad configuration exits with code 2 (ServiceMains.scala:38-130), and this was seen in all four images.                       │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ F5    │ Fixed. There are now tests for a failed half-open probe, the queue-full 429 and RESULT_TOO_LARGE.                                     │
├───────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ O1 /  │ Closed. The images were rebuilt and match the JAR and prompt hashes, and source hashes were recorded before every gate.               │
│ O2    │                                                                                                                                       │
└───────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Findings

F6 — Medium — BLOCKING. Owners: service-engineer (fix), test-engineer (independent test), build-engineer (rebuild images).

A normal graph request can open the graph circuit breaker and make query-api report itself not ready.
- Where:
  - GraphApi.scala:131,137,168,217: the caller can lower timeoutMs down to 1. When graph-service's own deadline runs out, it returns a typed 504.
  - RemoteServices.scala:90,95: query-api turns that 504 into ApiError.timeout, which is marked retryable (ApiContracts.scala:22).
  - DownstreamClient.scala:92-98: query-api counts it as a breaker failure and retries it, because it is a GET.
  - RemoteServices.scala:108-109: the readiness check goes through that same breaker.
  - OfflineComposition.scala:261-264: query-api readiness depends on it.
- How it fails: take a public request to /v1/graph/nodes/X/neighbors on a non-trivial snapshot, with either ?timeoutMs=1 or a heavy depth-3 expansion that hits the 5000 ms cap.
  a. graph-service returns 504.
  b. query-api sends the same request 3 times, so the 3 failures reach breakerFailureThreshold (3) and the breaker opens.
  c. For the next 30 s (breakerResetMs), query-api /readyz returns 503 while graph-service is healthy.
  d. The remote metric reads inside /v1/query also fail during that window, and all graph proxy traffic is refused.

  One authenticated request every 30 s keeps query-api out of rotation, and the deterministic timeout is also sent three times.
- How I confirmed it: by tracing the code. I could not run it under the read-only rules.
- Acceptance check: an independent test runs query-api in front of a real or stub graph-service and sends at least threshold + 1 neighbor requests that end in graph-service's own deadline 504. It must show all of the following:
  - each request returns a typed 504 carrying the caller's trace ID;
  - graph-service receives exactly one call per request;
  - the gauge still reads downstream_circuit_state{dependency="graph",state="CLOSED"} 1;
  - query-api /readyz stays 200;
  - a later normal request succeeds.

  Real outages must still open the breaker: connection refused, a client timeout with no response, or a 5xx from an unready service. The existing breaker tests and the stop-graph Docker check must still pass.
- Suggested fix: graph-service sends a distinct code for its own deadline that is not retryable. RemoteService reads the typed error body instead of the status alone, passes the safe code through, and does not count errors the downstream marks non-retryable and request-specific as dependency failures.

F7 — Low — nonblocking. Owner: service-engineer.
EmbeddingWorker.scala:55-66,77,89-95: if publishing to the DLQ fails at the attempt limit, the row goes back to RETRY. Every later redelivery runs the processor again before trying the DLQ. With a live embedding provider, each of those is a paid call beyond maxAttempts.
Acceptance: when the stored attempt count is already at the limit, the worker goes straight to the DLQ without calling the processor.

F8 — Low — nonblocking. Owner: service-engineer.
EmbeddingWorker.scala:110-114: run() has no guard against unexpected exceptions, so one error from an adapter ends the loop thread for good. /healthz and /readyz keep returning 200 (ServiceMains.scala:94,119-120).
Acceptance: an exception from the adapter is contained, or health reflects that the loop has died.

F9 — Low — nonblocking. Owner: service-engineer (README), orchestrator (repairs.md).
modules/services/README.md:223-224 says "Observed targeted gate … 37/37 independent 10A/10B tests … six suites." No single gate observed 37 tests in six suites:
- targeted-3 ran 36/36 in 6 suites, before the last test was added;
- the final targeted run was 17/17 in 4 suites;
- the 37 only ran together inside the full check's 625.

repairs.md:26 has the same wording. Acceptance: restate the counts as observed.

F10 — Low — nonblocking. Owner: service-engineer; rag-engineer if runPlan needs stage hooks.
The adapter only reports the stages PLANNING, RETRIEVAL and AUDIT (RuntimeWorkflowAdapter.scala:20,24,27). So a job never shows SYNTHESIS or CLAIM_VERIFICATION (the stage allowlist is at QueryService.scala:236), and explain's stagesExecuted leaves out two stages that did run. Explain also does not list the course's "indexes queried" or "query-template IDs" as their own fields (EvidenceApi.scala:51-105).

F11 — Low — nonblocking (already disclosed). Owner: service-engineer.
ApiApplication.scala:97-101: every new 10B route is logged with the route label unmatched.

F12 — Low — nonblocking. Owner: service-engineer.
RemoteServices.scala:78-92: specific graph-service error codes are lost through the proxy. GRAPH_SCAN_CAP, GRAPH_NODE_CAP and PATH_EXPANSION_TRUNCATED all become UNSUPPORTED_QUERY. This could be fixed together with F6.

F13 — Low — nonblocking. Owner: service-engineer.
scholarchain.v1.yaml:396-410: there are no committed response examples for the synchronous QueryResponse, Evidence, Explain or JobStatus. answer has no declared shape, so researchers, scores and numbers sent as strings are not in the contract, which differs from the course example.

F14 — Low — nonblocking. Owner: service-engineer.
SemanticApiConfig cannot be set from the environment (SemanticApi.scala:22-32, OfflineComposition.scala:72). The prompts folder is found by walking up from the working directory rather than being configured (OfflineComposition.scala:28-32). Both go against plan rule 7 (configuration, not constants).

F15 — Observation / future scope. Owner: service-engineer.
- query-api also serves /internal/v1/semantic/retrieve (ApiApplication.scala:212). That widens its internal surface beyond the planned service split, though the README documents it.
- In remote composition, the path and community agents still read the local fixture graph (OfflineComposition.scala:213-219), so query-api never calls /internal/v1/graph/paths.

Not verified here (later human-gated work):
- live adapters and deployment;
- injecting a stable cursor key across replicas;
- the SQS redrive policy in Terraform;
- a durable job dispatcher and recovery of PROCESSING rows;
- a full third-party OpenAPI validator.

Report fields

STATUS: COMPLETE (review) — verdict REQUEST-CHANGES
OWNER: code-reviewer (read-only)
WORK ORDER: docs/agent-runs/phase-10/evidence/10b/reviewer-prompt.md
FILES CREATED: None in repository (course README fetched to session scratchpad only)
FILES MODIFIED: None
COMMANDS RUN: git rev-parse HEAD; git status --short; git diff --stat/--check c85da73; git diff c85da73 -- <modified files>; cat/sed/grep of all 30 sources, OpenAPI, examples, README, phase reports and evidence; python3 -I SHA-256 rehash vs source-files.json and check-sources.json; shasum -a 256 of /tmp/phase10b-check.log, -docker.log, -docker-remote.log; curl GET of the public course README
TEST RESULTS: None executed by reviewer. Retained evidence matches: services 26/26, independent 10B 17/17, 10A 20 (targeted-3 36/36), buildVerification 13/13, full check 1199/0 in 145 suites, exit 0, JDK 17.0.20.1
VALIDATION RESULTS: 30/30 hashes match; only README differs from the check snapshot; three log hashes match; module totals sum to 1199; git diff --check exit 0; HEAD c85da73; ownership consistent
ASSUMPTIONS: Live deployment, provider and durability work is later scope; F6 confirmed by static trace
RISKS: F6 lets one authenticated caller open the graph breaker and fail query-api readiness; F7–F15 nonblocking
MANUAL ACTION REQUIRED: User pastes NEXT PROMPT to orchestrator; user owns any commit and human-gate
BLOCKED-ON OWNER: service-engineer (F6 fix), test-engineer (F6 independent test), build-engineer (rebuild images after fix)
BLOCKED-ON EVIDENCE: F6 acceptance test, rerun targeted gates, full JDK 17 sbt check, rebuilt images plus three-main remote smoke
NEXT GATE: Repair round 1 for F6, then user-launched read-only recheck
```


# Subphase 10B repair round 1

user-supplied external review

```text
VERDICT: REQUEST-CHANGES for Subphase 10B repair round 1.

F9 is closed. F6 is only partly closed. The timeoutMs=1 path is fixed and well tested. But the other half of F6's failure scenario, a heavy expansion that runs to the default 5000 ms graph cap, still opens the breaker under the shipped default configuration.

What I verified

- Hashes: all 33 source files match source-files.json, and all 9 repair files match repair-files.json.
- Change scope: since the full-check snapshot, only modules/services/README.md changed. Every 10B file outside the repair list is unchanged since round 0, including QueryService and the worker.
- Logs and counts: the full-check log and both Docker log hashes match. Module counts add up to 1208 with 0 failures. git diff --check passes, and HEAD is still c85da73.
- Scope and ownership: the work stayed inside the authorized F6 + F9 scope, and F12 is unchanged. Each file was written by its listed owner, and no human decision file was touched. review.md and repairs.md carry the prior verdict as user-supplied external review.
- F1–F5, O1–O2: no regressions.
- F9: CLOSED. README.md:230-236 now reports the 36/36 six-suite and 17/17 four-suite gates separately, plus the observed 41/41 seven-suite repair gate.
- Marker parsing: the parser in RemoteServices.scala:107-129 is narrow, as claimed:
  - it requires the graph dependency, a GET to an allowlisted path, status 504, an exact four-field body and retryable:false;
  - it discards the downstream message and trace;
  - malformed, wrong-scope and retryable markers keep normal failure handling.
- Tests: the red runs genuinely failed before the fix, which is good evidence. The independent burst test asserts CLOSED before any readiness probe runs.

Findings

F6 — Medium — BLOCKING (still open in one scenario). Owners: service-engineer (fix and module test), test-engineer (independent test), build-engineer (rebuild and smokes).

- Where:
  - graph-service's default budget is 5000 ms: ServiceMains.scala:18 and GraphApi.scala:135,141;
  - query-api's attempt deadline is also 5000 ms (ApiContracts default): DownstreamClient.scala:63,86 and RemoteServices.scala:49,101.
- What happens: take a /v1/graph/nodes/X/neighbors request with no timeoutMs, or timeoutMs=5000, that takes longer than the budget (a hub node at depth 3, or a slow snapshot adapter).
  a. query-api's clock starts before it sends the request. graph-service's clock starts after it receives and parses it, and its 504 marker still has to travel back.
  b. So query-api's own timer always fires first. It produces the retryable DOWNSTREAM_TIMEOUT, not the marker.
  c. That timeout is retried 3 times and counts 3 breaker failures. The breaker opens, and query-api /readyz returns 503 for 30 s. This is the original F6 outcome.
  d. Any caller timeoutMs close to 5000 ms races the same way.

  The repair's Docker harness also sets query-api's SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS=500 while the graph budget stays 5000 (phase10b-r1-docker-remote.py:6). Nothing checks that these two settings fit together.
- How I confirmed it: by tracing the code. I did not run it.
- Why the tests missed it: both new suites only use timeoutMs=1, or a module-level budget far below the transport deadline.
- Acceptance check:
  a. query-api must not let a graph request's budget reach its own per-attempt transport deadline. One option is to always forward a timeoutMs clamped to the transport deadline minus a configured margin, deterministically so cursor binding stays stable. Another is to refuse to start (exit 2) when the configured budgets overlap. Document the chosen rule in the README and OpenAPI.
  b. An independent HTTP test puts query-api in front of a real GraphApi whose snapshot read blocks, with equal default-style budgets (for example both 300 ms) and no timeoutMs on the request. Four requests must each return 504 GRAPH_DEADLINE_EXCEEDED with the caller's trace, cause exactly one backend call each, and leave the breaker CLOSED and /readyz at 200.
  c. The existing outage tests (refusal, no response, unready 503) still pass.

F16 — Low — nonblocking, future live-adapter gate. Owner: service-engineer.

Because of the repair, a graph-service whose snapshot backend hangs now only ever returns GRAPH_DEADLINE_EXCEEDED. That never trips query-api's breaker, and graph-service's own readiness never checks the snapshot: GraphEndpoints.ready defaults to true at SemanticApi.scala:8 and GraphApi doesn't override it. A live GraphSnapshot adapter must report backend readiness.

Carried and unchanged (nonblocking): F7, F8, F10, F11, F12, F13, F14, F15.

Later human-gated work, not verified here: live adapters and deployment, stable cursor-key injection, SQS redrive, a durable dispatcher and PROCESSING recovery, and a full OpenAPI validator.

Report fields

STATUS: COMPLETE (recheck) — verdict REQUEST-CHANGES
OWNER: code-reviewer (read-only)
WORK ORDER: docs/agent-runs/phase-10/evidence/10b-repair-1/reviewer-prompt.md
FILES CREATED: None
FILES MODIFIED: None
COMMANDS RUN: git rev-parse HEAD; git branch --show-current; git status --short; git diff --check c85da73; git diff c85da73 -- review.md; cat/grep of repair evidence, repair-source.diff and current sources; python3 -I SHA-256 rehash vs 10b-repair-1 source-files.json, check-sources.json, repair-files.json and 10b/source-files.json; shasum -a 256 of /tmp/phase10b-r1-check.log, -docker.log, -docker-remote.log
TEST RESULTS: None executed by reviewer. Retained evidence: services 31/31 (5 suites), independent 10A/B 41/41 (7 suites), full check 1208/0 in 147 suites, exit 0, JDK 17.0.20.1; red gates independent 3/4 and module 2/5 as described
VALIDATION RESULTS: 33/33 and 9/9 hashes match; only README differs from the check snapshot; three log hashes match; module totals sum to 1208; diff --check exit 0; scope limited to F6+F9; F9 closed; F6 timeoutMs=1 path closed, default-budget path open
ASSUMPTIONS: Default ServiceConfig and SCHOLARCHAIN_GRAPH_TIMEOUT_MS values describe the shipped configuration; residual confirmed by static trace
RISKS: A heavy or slow graph expansion at the default cap still opens the graph breaker and fails query-api readiness for 30 s
MANUAL ACTION REQUIRED: User pastes NEXT PROMPT; user owns commit and human gate
BLOCKED-ON OWNER: service-engineer, test-engineer, build-engineer (F6 residual)
BLOCKED-ON EVIDENCE: Equal-budget independent HTTP test, targeted and full JDK 17 gates, rebuilt images and smokes
NEXT GATE: Repair round 2 for F6 residual, then user-launched read-only recheck
```


# Subphase 10B repair round 2

user-supplied external review

```text
VERDICT: APPROVE for Subphase 10B (repair round 2). F6 is now closed. I found no blocking defects and no regressions, and the repair stayed inside the authorized scope (F6 residual only).

What I verified

- The fix closes the gap I flagged last round. query-api now always sends graph-service an explicit work budget smaller than its own transport timeout:
  - The budget is min(requested or graph cap, T − ceil(T·P/100)), where T is query-api's per-attempt transport timeout and P is the reserve percentage (RemoteServices.scala, graphWorkBudgetMs and graphParameters).
  - It applies to all four graph operations: node, neighbors, metrics and paths.
  - With the defaults (T = 5000 ms, P = 25%) it forwards 3750 ms, leaving 1250 ms for the response to get back.
  - Invalid caller budgets get a 400 before any backend call, and the breaker is never touched.
  - A configuration that leaves no positive work budget refuses to start (exit 2).
- graph-service enforces the forwarded budget on every operation. This covers node and metrics reads (operationTimeout) and path expansion, including the breadth-first search after the neighbor read.
- The independent equal-budget test is real and was red first. IndependentServices10BEqualBudgetSpec runs a real GraphApi behind real HTTP with 300 ms graph and 300 ms proxy budgets. It covers both an omitted and an explicit 300 ms caller budget:
  - four requests produce exactly four snapshot executions;
  - each returns 504 GRAPH_DEADLINE_EXCEEDED, non-retryable, with the caller's trace;
  - CLOSED is asserted before any readiness probe, then /readyz returns 200 and normal traffic succeeds;
  - cursor replay stays stable.

  The final file is byte-identical to its retained red version, and that red run reproduced the defect (3 backend executions for 4 requests).
- The real-outage behavior is unchanged. The marker parser, the refusal, no-response and unready-503 tests, and the stop-graph Docker check all still hold. The changes to existing test doubles only forward the new parameters, and every prior assertion is still there.
- Evidence integrity:
  - 35/35 source hashes and 11/11 repair hashes match, and only the README changed after the check snapshot. Changes since repair 1 are exactly the 11 declared files.
  - The full-check log hash matches, with 9 module totals summing to 1208 and no failures. git diff --check passes, and HEAD is c85da73.
- Scope and earlier findings: QueryService and the worker are unchanged, so there is no F1–F5 regression. F7, F8 and F10–F16 are untouched.

Findings

ID: F17
Severity: Low
Where: ApiContracts.scala (graphRequestTimeoutMs) and ServiceMains.scala:18
Note: query-api and graph-service each read SCHOLARCHAIN_GRAPH_TIMEOUT_MS separately. If an environment sets it higher on query-api than on
graph-service, budgets above graph-service's cap get a 400. The defaults match. Phase 12 deployment config should set it once per environment.
Owner: service-engineer / infra-engineer (Phase 12)
Blocking: No
────────────────────────────────────────
ID: O3
Severity: Observation
Where: evidence log-index.json
Note: The full raw logs live only in /tmp. The repository keeps their hashes and excerpts, which is enough under the lean-evidence rule, but the raw
logs won't survive a reboot.
Owner: orchestrator
Blocking: No

Carried as nonblocking, for Phase 11 or later: F7, F8, F10–F16, F17.

Later human-gated work, not verified here: live adapters and deployment, snapshot-backend readiness (F16), stable cursor-key injection, SQS redrive, a durable dispatcher and PROCESSING recovery, and a full OpenAPI semantic validator.

Report fields

STATUS: COMPLETE (recheck) — verdict APPROVE
OWNER: code-reviewer (read-only)
WORK ORDER: docs/agent-runs/phase-10/evidence/10b-repair-2/reviewer-prompt.md
FILES CREATED: None
FILES MODIFIED: None
COMMANDS RUN: git rev-parse HEAD; git status --short; git diff --check c85da73; cat/grep/awk of repair-2 evidence, repair-source.diff and current sources; diff of the final vs red equal-budget spec (identical); python3 -I SHA-256 rehash vs repair-2 source-files.json, repair-files.json, check-sources.json and repair-1 source-files.json; shasum -a 256 /tmp/phase10b-r2-check.log; grep of test totals in that log
TEST RESULTS: None executed by reviewer. Retained evidence: independent red 1/3, module red 0/4; green services 36/36 (6 suites), independent 10A/B 44/44 (8 suites), packageServices; full check 1216/0 in 149 suites, exit 0, JDK 17.0.20.1, sbt 721 s, wall 723.581 s
VALIDATION RESULTS: 35/35 and 11/11 hashes match; only README differs from the check snapshot; log hash matches; totals sum to 1216; diff --check exit 0; F6 CLOSED; F9 CLOSED (round 1); no F1–F5 regression; scope respected
ASSUMPTIONS: Live deployment, provider and durability gates remain later scope
RISKS: Nonblocking items carried to Phase 11; graph timeout must be configured consistently across services (F17)
MANUAL ACTION REQUIRED: User reviews the diff, commits Subphase 10B, and writes human-gate.md and commit.txt
BLOCKED-ON OWNER: None
BLOCKED-ON EVIDENCE: None for Subphase 10B
NEXT GATE: User commit and Phase 10 human gate; then Phase 11 by explicit user prompt only
```
