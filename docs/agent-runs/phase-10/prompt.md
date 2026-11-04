# Phase 10 work order — Subphase 10A

## User instructions

> implement the plan for me

> I have checked to phase-10 branch
> implement phase 10 for me, use defaults docker available.

Only 10A is authorized for this run under the plan’s one-subphase boundary. User confirmed the defaults asked in Step 0: Cask subject to Scala 3.3.4 verification; hashed external bearer API key and separate internal service token; configurable 15000 ms synchronous deadline; course routes and OpenAPI path; four-artifact service split; graph ingress through query-api proxy; phase-10 branch; local Docker builds available, no push.

## Exact supplied plan

# ScholarChain Phase 10 — RESTful microservices: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** Nov 9 – Nov 13, 2026.

> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 10, **RESTful microservices**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **What exists:** `modules/services` (depends on `core`, `rag`, `storage` and, today, `sparkAnalytics`) is empty. The `Dockerfile` at the repository root builds one image that runs `services.jar`. Phase 9 provides the `WorkflowRunner` and all runtime stages behind ports; Phase 7 provides fakes for every store. Everything in this phase runs offline against fakes.
- **Build issue to settle in 10A:** `services` should not need the Spark module at runtime. Spark is `Provided`, so it is not shipped, but the dependency is misleading. `build-engineer` decides whether to remove `sparkAnalytics` from `services`' `dependsOn` (recommended: remove unless a class is actually used).
- **Deployable artifacts.** The course baseline needs at least three independently deployable runtime services. This plan uses **four artifacts from one codebase**: `query-api`, `graph-service`, `semantic-service` and `embedding-worker`. The worker exists because Phase 15 experiment C scales workers on SQS backlog. Each artifact has its own main class and its own container image.
- **Schedule slot:** Nov 9 – Nov 13, 2026 (about 5 days). Phase 13 (scripts) can overlap the end of this phase.

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/service-engineer.md`, `docs/agent-runs/README.md`.
2. The course Phase 10 section, "Runtime microservice graph", **"REST API contract"** (every route, request and response example, error model), "Observability requirements" and "Security requirements": https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-10-expose-the-runtime-through-restful-microservices
3. `modules/rag/README.md` (workflow, abstention and audit behavior) and `modules/storage/README.md`.
4. The existing `Dockerfile` and `project/ScholarChainBuild.scala`.

## 4. Decisions and open questions that apply to the whole phase

- **Open questions for the phase (ask in Step 0 of 10A):**
  - **10-1. HTTP library.** Recommended: Cask (Scala 3, small, uses upickle which the project already uses) with in-house timeout, retry and circuit-breaker helpers. Alternatives: Pekko HTTP or http4s (heavier). The service-engineer must confirm the choice compiles on Scala 3.3.4 and that `build-engineer` adds it to the dependency ledger.
  - **10-2. Authentication.** Recommended: a bearer API key for external clients (hash stored, constant-time comparison, the key supplied through Secrets Manager at deploy time) and a separate internal service token between services. No Cognito (lean scope). Document it as the course deployment's authentication method.
  - **10-3. Sync vs async threshold.** Recommended: respond synchronously when the workflow completes within `operations.synchronousDeadlineMs` (default 15,000 ms), otherwise return `202` with a job reference and continue in the worker path.
  - **10-4. OpenAPI file.** The course says endpoint names may change if the OpenAPI contract is consistent. Recommended: keep the course routes exactly and commit `modules/services/src/main/resources/openapi/scholarchain.v1.yaml` (owned by `service-engineer`) for Phase 17 to link.
  - **10-5. Service split.** Recommended: `query-api` hosts query, jobs, explain, evidence, the orchestrator, synthesis, verification and audit; `graph-service` hosts graph exploration, metrics and path retrieval; `semantic-service` hosts embedding plus vector retrieval; `embedding-worker` drains the SQS queue. Confirm or change.
- **Thin routes.** Routes only parse, validate, call a service-layer function and map the result. No retrieval algorithm lives in a route handler.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-10/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `service-engineer` | `modules/services/**`: routes, services, middleware, clients, main classes, OpenAPI file, module tests, `modules/services/README.md` | 10A–10B |
| `build-engineer` | `build.sbt`, `project/**`, `Dockerfile`: HTTP library entry, the `services` dependency cleanup, one image per artifact (build-arg for the main class) | 10A, 10B |
| `domain-engineer` | `modules/core/**`: error model, request/response and job-record contracts if missing | on demand |
| `rag-engineer`, `storage-engineer` | Only if a port or stage is missing (return `BLOCKED-ON`) | on demand |
| `test-engineer` | `tests/**`: independent API tests and the query-to-evidence lifecycle test | 10B |

## 6. Global rules for every subphase

1. **Ask first.** Step 0 of every subphase: list your questions, including the subphase's "Open questions" that are still open, each with a recommended default. Wait for the user's answers. If none, write "No questions for this subphase" and proceed.
2. **Preflight.** Record `git status --short`, the branch and HEAD as this subphase's **base SHA**. If the previous subphase's changes are still uncommitted, ask the user whether to proceed or wait for their commit. Never reset or discard changes you did not make.
3. **JDK 17 for every sbt command** (Section 2). Report `java -version` in the first gate of each subphase.
4. **One writer per artifact.** Route every edit to the owner in Section 5 and `docs/agents.md`. An unlisted path is an orphan: stop and ask the user. Out-of-scope work is returned as `BLOCKED-ON <owner>` with evidence.
5. **Secrets.** Never read or print `.env`, private keys, tokens, generated credentials or secret directories. Secrets live in AWS Secrets Manager or approved local placeholders, never in tracked files, logs, prompts, Terraform source or plans.
6. **Cloud and money gates.** All AWS infrastructure is authored in Terraform. Live apply, deployment, costly scale changes, data destruction, security changes and rollback require the human gate recorded in the phase evidence. Do not run any command that creates, changes or deletes a cloud resource, or that calls a paid model provider, unless this subphase's text and the user's recorded approval allow it. Unit and contract tests use fakes.
7. **Configuration, not constants.** No hardcoded bucket names, endpoints, account IDs, regions, thresholds or model IDs without a configuration entry and a short rationale (the course deducts for this).
8. **Observability.** Structured logs with trace/run IDs; no secrets or full sensitive payloads in logs.
9. **Every behavior change has tests**, written from the stated requirement, not by re-running the implementation's own logic. Module owners add tests under their module's `src/test/**`; `test-engineer` adds independent tests under `tests/**`.
10. **Provenance.** Data transformations and runtime claims keep source and run provenance. An LLM may never invent a researcher identity, path, score or evidence.
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-10/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-10` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 10X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Routes (course contract)

| Service | Routes |
|---|---|
| `query-api` | `POST /v1/query`; `GET /v1/jobs/{jobId}`; `GET /v1/jobs/{jobId}/result`; `GET /v1/evidence/{evidenceId}`; `GET /v1/explain/{queryId}`; `GET /healthz`; `GET /readyz`; `GET /metrics` |
| `graph-service` | `GET /v1/graph/nodes/{nodeId}`; `GET /v1/graph/nodes/{nodeId}/neighbors` (bounded depth, edge types, result count, timeout, cursor pagination); internal metric and path routes under `/internal/v1/**`; health and readiness |
| `semantic-service` | Internal vector retrieval under `/internal/v1/semantic/**`; health and readiness |
| `embedding-worker` | No public routes; SQS consumer loop; health endpoint |

The external graph routes may be exposed through `query-api` as a thin proxy, or directly. Decide in 10A and document it; the ingress design is Phase 12's input.

### 7.2 Required HTTP behavior

- JSON request/response contracts that match the committed examples; path-based versioning (`/v1`).
- `X-Request-Id` and trace ID on every request, propagated to downstream calls and logs; every error response includes the trace ID.
- `Idempotency-Key` on POST: the first request creates a `QuerySession` row with a conditional write; a repeat returns the stored answer or job reference and does not rerun the workflow; a repeat with a different body returns a typed conflict.
- Typed error model with the status-code mapping documented: 400 invalid JSON/constraint, 401/403 auth, 404 missing evidence/node, 409 idempotency conflict, 422 unsupported query, 429 throttled, 502/504 downstream failure or timeout, 500 internal.
- Timeouts per downstream call, bounded retries on idempotent reads only, and a circuit breaker per downstream dependency with tests of open, half-open and closed states.
- Authentication on every non-health route; no secrets or raw credentials in responses or logs; log redaction tested.
- `/healthz` (process alive) and `/readyz` (dependencies reachable) are different checks; neither exposes secrets or internal addresses.
- Metrics (`/metrics`): request count, status-code counts, latency histogram (p50/p95/p99 derivable), timeouts, downstream errors, circuit-breaker state, workflow verification-status counts and abstention count.

### 7.3 Async path

`POST /v1/query` that exceeds the synchronous deadline returns `202` with `jobId`; the job record lives in `QuerySession`; the worker path runs the workflow, writes the result pointer, and `GET /v1/jobs/{jobId}` reports state, timestamps, stage, errors and the result link. A job that fails is retried within a bounded policy, then marked failed with its error.

### 7.4 Packaging

One shaded or thin-with-lib jar per artifact (or one jar with multiple main classes), and a `Dockerfile` that takes the main class as a build argument. Images are tagged by Git SHA in Phase 13; here only the build works locally (`docker` is optional, ask in Step 0 whether Docker is available; if not, `package` produces the jar and the Dockerfile is reviewed but not built).

## 8. Subphases

Execute the subphases in order: 10A → 10B. Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 10A — Foundation: server, errors, auth, idempotency, query and jobs

**Owners:** `build-engineer`, `service-engineer`, `domain-engineer` (on demand), `test-engineer` (interface-first).

**Open questions:** 10-1, 10-2, 10-3, 10-4, 10-5, and whether Docker is available.

**Tasks:**

1. `build-engineer`: HTTP library entry, `services` dependency cleanup, multi-artifact packaging (jars and Dockerfile build arg).
2. `service-engineer`: server skeleton, request-ID and trace-ID middleware, typed error model, authentication, `/healthz` and `/readyz`, `/metrics`, log redaction, configuration loading from environment (no hardcoded values).
3. `POST /v1/query` (sync and async paths), `GET /v1/jobs/{jobId}` and `/result`, idempotency through `QuerySessionStore`.
4. Downstream client helpers: timeout, bounded retry, circuit breaker, with tests.
5. Initial OpenAPI file for these routes.
6. Tests: successful sync query (fake workflow), async path, invalid JSON, unsupported query constraint, unauthorized, repeated idempotent request, different-body conflict, timeout and downstream failure, health vs readiness.

**Done when:** the listed routes behave per Section 7.2 against fakes; `sbt check` passes.

> **⛔ STOP after 10A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 10B until the user sends a new prompt.

### Subphase 10B — Evidence, graph, semantic, explain, worker, end-to-end test, packaging

**Owners:** `service-engineer`, `build-engineer`, `test-engineer` (parallel).

**Tasks:**

1. `GET /v1/evidence/{evidenceId}` with provenance, source record, source URI, graph path or text pointer and compact supporting content; missing evidence returns the typed 404.
2. `graph-service` routes with cursor pagination and hard caps; `semantic-service` internal routes; `query-api` calls them through the downstream client helpers.
3. `GET /v1/explain/{queryId}`: QueryPlan, stages executed, prompt and model versions, evidence IDs, score components, counters and verification status. No hidden chain-of-thought.
4. `embedding-worker` loop over the `EmbeddingWorkQueue` port with idempotent processing and a poison-message path to the DLQ port; local fake queue test.
5. Finish the OpenAPI file; add `modules/services/README.md` with the route table, status-code mapping, timeout policy, dependency graph, authentication method and exact test counts.
6. Test-engineer: a full query-to-evidence lifecycle with fakes that ends in an evidence-backed answer; independent auth, malformed-body and timeout tests; a source scan proving route handlers contain no retrieval logic (they call services only).
7. `build-engineer`: verify all four artifacts build; if Docker is available, build the images locally (no push).
8. Full `sbt check`.

**Done when:** at least one end-to-end API test reaches an evidence-backed answer from bounded fixtures; error responses carry trace IDs; request/response examples match the contract tests; `sbt check` passes.

> **⛔ STOP after 10B.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Query | Successful sync query; async `202` then job result; invalid JSON; unsupported constraint → 422; missing evidence → 404 |
| Idempotency | Repeat with same key returns the same answer and does not rerun the workflow; different body with same key → 409 |
| Auth | Missing key → 401; invalid key → 401/403; internal route without service token rejected; health routes open |
| Resilience | Downstream timeout → typed 504 with trace ID; retry only idempotent reads; circuit breaker open/half-open/closed |
| Errors | Every error response has `traceId`, a stable error code, and no stack trace or secret |
| Health | `/healthz` independent of dependencies; `/readyz` fails when a dependency is down; neither leaks configuration |
| Graph | Pagination cursor stable; depth/edge-type/result-count/timeout caps enforced |
| Explain | Returns plan, stages, versions, evidence IDs, counters; never chain-of-thought |
| Worker | Duplicate message processed once; poison message goes to DLQ port |
| Lifecycle | Query → answer → evidence fetch → explain, all with fakes |
| Structure | Route handlers contain no retrieval logic (source scan); log redaction test |

Tests assert required behavior from hand-derived expectations, not by re-running the implementation's own logic.

## 10. Handoff protocol and reviewer prompt

At the end of **every subphase and every repair round**, return a handoff packet to the user containing:

- Status (complete or blocked).
- Base SHA, branch and HEAD.
- Changed and untracked files.
- Exact commands with exit codes and test counts.
- Evidence paths.
- Answers the user gave in Step 0.
- Limitations and manual actions.
- **The complete reviewer prompt in one fenced code block**, with every placeholder filled with real values.

Then stop. **Never launch a reviewer.** The user pastes the prompt into a separate reviewer agent. That reviewer returns its verdict **and** the next prompt for you.

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-10/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

## 11. Final checklist (Phase 10 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] Routes do not embed retrieval algorithms.
- [ ] Error responses include trace IDs; health checks expose no secrets.
- [ ] Request and response examples match contract tests; the OpenAPI file is consistent with the routes.
- [ ] At least one end-to-end API test reaches an evidence-backed answer using bounded fixtures.
- [ ] Four deployable artifacts build; the route table, status-code mapping, timeout policy, dependency graph, authentication method and test counts are documented.
- [ ] A fresh `sbt check` on JDK 17 passes; the reviewer returned APPROVE; the human wrote `human-gate.md` and `commit.txt`.
