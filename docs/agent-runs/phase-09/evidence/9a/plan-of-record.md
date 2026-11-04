# ScholarChain Phase 9 — Runtime collaboration-analysis agents: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** Nov 5 – Nov 11, 2026.

> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 9, **Runtime collaboration-analysis agents**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **What exists after Phases 6–8:** deterministic graph/metric data and the storage ports with fakes (`GraphReader`, `ResearcherMetricStore`, `EntityLinkCache`, `VectorStore`, `EvidenceBundleStore`, `QuerySessionStore`, `ObjectStore`), plus the semantic-context format and `EmbeddingClient`. Runtime stages talk to **ports only**, so everything in this phase is testable offline with fakes loaded from the Phase 6 known-graph fixtures.
- **Module:** `modules/rag` (depends on `core` and `storage`). Prompts and JSON schemas live under `prompts/runtime/**` and `prompts/schemas/**` (owned by `rag-engineer`).
- **Existing LLM code:** Phase 5 has an OpenAI Responses adapter inside `modules/entity-resolution`. `rag` cannot import it (module direction). Write a new `LlmClient` port with its own adapters here.
- **No live LLM calls in tests.** Tests use a scripted fake `LlmClient`. A small, explicitly approved live smoke (9C task 6) is optional and spend-gated.
- **Phase 6 accepted limits the runtime must respect:** community, cross-community, bridge and continuity outputs are iteration-limited (`Converged: false` on all observed real windows); the distance P90 is approximate. Both are carried in the stored rows (Phase 7) and must appear in evidence and answers.
- **Schedule slot:** about 5–7 days after Phase 8's 8B is approved; target finish Nov 11, 2026.

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/rag-engineer.md`, `docs/agent-runs/README.md`.
2. The course Phase 9 section, "Runtime microservice graph", "Example evidence-backed workflow", "Security requirements" and the research questions at the top of the course README: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-9-implement-the-runtime-collaboration-analysis-agents
3. `modules/storage/README.md`, `modules/spark/README.md` (metric definitions and window names), and the Phase 6–8 owner reports.
4. Phase 5 evidence on researcher resolution (accepted/unresolved links, confidence) so the resolver's abstention matches the ER policy.

## 4. Decisions and open questions that apply to the whole phase

- **Open questions for the phase (ask in Step 0 of 9A):**
  - **9-1. LLM provider for planning and synthesis.** Recommended: Amazon Bedrock Converse API with a model available in the course region (authentication by IAM role, no key to store). Alternative: the OpenAI Responses pattern from Phase 5, which needs an API key in Secrets Manager. Behind one `LlmClient` port either way; model IDs are configuration.
  - **9-2. Planner design.** Recommended: LLM structured output validated against the QueryPlan JSON schema, with a deterministic rule-based fallback for the benchmark question patterns, so a malformed model response never blocks a known question.
  - **9-3. Claim verification design.** Recommended: synthesis returns **typed** `AnswerClaim` records plus a narrative that references claim IDs only. Verification is deterministic for typed fields (IDs, counts, hop lists, years, windows, scores) and checks that every number in the narrative appears in a claim. An LLM verifier is optional and only for free-text paraphrase. The deterministic verifier is the one that decides VERIFIED/UNSUPPORTED.
  - **9-4. Retrieval modes for evaluation.** Phase 15 experiment E compares graph-only, vector-only and fused retrieval. Recommended: a `retrievalMode` option (`graph`, `vector`, `fused`) in the workflow, defaulting to `fused`, enabled for evaluation by configuration.
  - **9-5. Benchmark set.** Recommended: at least 12 benchmark questions covering ranking by distinct coauthors, maximum team size, direct coauthors, shortest path, component lookup, community comparison, bridge ranking, temporal comparison, topic filter, an ambiguous name, an unsupported question, and a prompt-injection case.
- **Deterministic facts never come from the LLM.** Counts, paths, components, communities and bridge scores come from stored data through ports. The LLM plans and interprets.
- **There is no universal ranking formula.** Rank by the metric the question names: distinct coauthors by `C_r`, repeated collaboration by the documented weighted measure, bridge researchers by the selected bridge measure. A composite score is allowed only with explicit components, normalization, weights, missing-data behavior and rationale.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-09/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `domain-engineer` | `modules/core/**`: QueryPlan, ResearcherCandidate, EvidenceItem/EvidenceBundle, AnswerClaim, VerificationResult, AuditRecord and runtime-config contracts with wire examples | 9A |
| `rag-engineer` | `modules/rag/**`, `prompts/runtime/**`, `prompts/schemas/**`: all agents/stages, orchestrator, prompts and schemas, benchmark suite, local CLI | 9A–9C |
| `storage-engineer` | `modules/storage/**`: only if a runtime need is missing from a port (return `BLOCKED-ON storage-engineer`) | on demand |
| `test-engineer` | `tests/**`: independent runtime tests, prompt-injection and abstention tests | 9B–9C |
| `build-engineer` | `build.sbt`, `project/**`: SDK entry for the chosen LLM adapter | 9A, on demand |

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
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-09/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-9` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 9X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Workflow (typed stages)

`QueryPlannerAgent → ResearcherResolverAgent → {CollaborationMetricsAgent, PathFinderAgent, CommunityAnalystAgent, SemanticContextAgent} (parallel, each with a deadline) → EvidenceBuilderAgent → AnswerSynthesisAgent → ClaimVerificationAgent → Audit`. A `WorkflowRunner` composes the stages. Each stage has an input type, an output type and a typed failure.

### 7.2 Stage requirements

1. **QueryPlanner:** produces a `QueryPlan` with operations from an **allowlist** (researcher ranking, maximum team size, direct coauthors, shortest path, component lookup, community comparison, bridge ranking, temporal comparison, topic filter, institution filter, semantic explanation), extracted researcher names, window, topic, venue, institution, ranking metric. Never emits Cypher, SQL or AWS operations. Unknown requests produce an `UnsupportedQuery` plan, not a guess.
2. **ResearcherResolver:** uses `EntityLinkCache`. Returns all candidates with source IDs, affiliations, coauthor context and confidence; if more than one plausible candidate remains or none, it returns `Ambiguous` or `NotFound`, and the workflow **abstains with the candidate list** instead of choosing. It exposes the DBLP homonym-suffix rule from Phase 6 identity (`Name 0001` is distinct from `Name 0002`).
3. **CollaborationMetrics:** reads `ResearcherMetricStore` and returns exact stored values: publication count, distinct coauthors, total coauthor occurrences, average and maximum team size, weighted degree, component, community, bridge measures, coreness, with window, metric version and run ID. It rejects a requested window that is not stored.
4. **PathFinder:** uses `GraphReader` templates only. Returns researcher IDs, edge weights, supporting work IDs, years and provenance for each hop; enforces depth, result and timeout limits from config; reports `NoPath` and `ExceededMaxHops` as typed results.
5. **CommunityAnalyst:** membership, size, cross-community edges, selected neighboring communities and bridge measures. Explains the difference between high direct degree and high bridge importance using stored values. Every community or bridge result carries the stored `converged` flag and iteration count; when `converged` is false the claim and the final answer must say the result is iteration-limited and must not describe it as a converged community structure. Approximate values (distance P90) are labeled approximate.
6. **SemanticContext:** `VectorStore` queries with metadata filters; returns the Phase 8 semantic-context items. Retrieved text is **untrusted data**: it is placed in a clearly delimited data block, truncated by the token budget, and never inserted into instruction positions.
7. **EvidenceBuilder:** builds a bounded `EvidenceBundle` that keeps deterministic evidence (IDs, metrics, paths, supporting works, resolution confidence, provenance) separate from descriptive semantic context; assigns each item a stable `evidenceId`; enforces the context token budget; persists through `EvidenceBundleStore`.
8. **AnswerSynthesis:** one prompt-versioned LLM call that returns JSON validated against the schema: `claims[]` (claimId, claimType, subject IDs, value fields, evidenceIds, windows) and a narrative that references claim IDs. Must state uncertainty and missing evidence, and explain breadth vs intensity vs team size vs connectivity vs bridge importance when relevant. No hidden reasoning is returned.
9. **ClaimVerification:** for every claim, checks that each cited evidence ID exists in the bundle and that every researcher identity, publication title, coauthor count, team-size claim, path hop, community claim, bridge score, window and number equals the bundle value. Returns `VERIFIED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED` or `CONFLICTING` per claim and overall. Unsupported claims are removed or labeled in the final answer, never silently kept.
10. **Audit:** persists QueryPlan, resolved researcher IDs, evidence IDs, metric versions, graph run ID, prompt and model versions, token counts when available, latency, verification result and an answer hash.

### 7.3 Required controls

- Every prompt and JSON schema is versioned (`promptVersion`, `schemaVersion`) and stored under `prompts/**`.
- Every model output is validated before use. Malformed structured output is retried only within a bounded policy (default 1 retry), then falls back (planner) or fails closed (synthesis → abstain).
- Context and token budgets from config (`retrieval.contextTokenBudget`, `operations.maxConcurrentLlmCalls`); abstain with a typed reason when identity or evidence is insufficient.
- Retrieved text is data, not instructions. Titles, abstracts and generated profiles are scanned in tests for injection strings.
- Never expose chain-of-thought.
- All model, bucket, endpoint and threshold values come from configuration.

### 7.4 Retrieval modes

`retrievalMode` = `graph` (stores only), `vector` (semantic context only; deterministic claims abstain) or `fused`. Used by Phase 15 experiment E. A test proves the `vector` mode cannot emit a deterministic numeric claim.

## 8. Subphases

Execute the subphases in order: 9A → 9B → 9C. Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 9A — Contracts, prompts/schemas, planner and resolver

**Owners:** `domain-engineer`, `build-engineer` (on demand), `rag-engineer`, `test-engineer` (interface-first).

**Open questions:** 9-1, 9-2, 9-3, 9-4, 9-5.

**Tasks:**

1. `domain-engineer`: the runtime contracts listed in Section 5 and the runtime-config contract (retrieval limits, token budget, deadlines, model IDs, fusion policy version) with wire examples and tests.
2. `rag-engineer`: `LlmClient` port, scripted fake, and the chosen adapter (not called in tests); prompt files and JSON schemas for planner and synthesis under `prompts/**` with versions.
3. `rag-engineer`: QueryPlanner (LLM + validation + rule fallback) and ResearcherResolver (with abstention on ambiguity).
4. Tests: planner allowlist (arbitrary Cypher request rejected), malformed JSON retry then fallback, fabricated operation rejected, resolver ambiguity (`Wei Wang`-style common name, DBLP suffix cases), not-found, confidence reporting.

**Done when:** contracts and schemas validate; planner and resolver pass tests on fakes; `sbt check` passes.

> **⛔ STOP after 9A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 9B until the user sends a new prompt.

### Subphase 9B — Metrics, path, community, semantic agents, evidence builder, workflow runner

**Owners:** `rag-engineer`, `test-engineer` (parallel).

**Tasks:**

1. CollaborationMetrics, PathFinder, CommunityAnalyst and SemanticContext stages against the storage ports.
2. EvidenceBuilder with the token budget, stable evidence IDs and persistence.
3. `WorkflowRunner` with parallel fan-out, per-stage deadlines and typed failures; `retrievalMode` support.
4. A fake-store fixture loaded from the Phase 6 G1 expected values so the stages return known results (A→G is 4 hops; A→H has no path; and so on).
5. Tests: exact metric values, missing window, hop evidence with supporting works, no-path and max-depth cases, community and bridge explanation inputs, untrusted-text delimiting and truncation, vector-mode cannot produce numeric claims, evidence bundle size bound.

**Done when:** the retrieval and evidence stages produce correct, bounded, deterministic evidence on the fixture; `sbt check` passes.

> **⛔ STOP after 9B.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 9C until the user sends a new prompt.

### Subphase 9C — Synthesis, verification, abstention, audit and benchmark suite

**Owners:** `rag-engineer`, `test-engineer` (parallel; independent injection and abstention tests).

**Tasks:**

1. AnswerSynthesis with typed claims, narrative-by-claim-ID, schema validation and bounded retry; fail closed to an abstaining answer.
2. ClaimVerification (deterministic checker per Section 7.2 item 9), overall status, and answer rewriting that removes or labels unsupported claims.
3. Audit persistence through the ports; answer hash.
4. A local CLI (`RuntimeWorkflowMain` or similar) that runs the workflow with fakes for a question given on the command line.
5. The benchmark suite from question 9-5 with expected results derived by hand from the fixture, run against the scripted fake LLM.
6. Optional, only with explicit user approval and a stated dollar cap: one live LLM smoke run of three benchmark questions. Retain request/response metadata but no secrets.
7. Document in `modules/rag/README.md`: prompt versions, schemas, allowed plan operations, identity-resolution behavior, query templates used, verification rules, abstention behavior, benchmark results, known failure modes.
8. Full `sbt check`.

**Done when:** every benchmark case behaves as specified; prompt-injection, fabricated-ID and unsupported-claim tests pass; deterministic and semantic retrieval are tested separately; `sbt check` passes.

> **⛔ STOP after 9C.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Planner | Allowlisted operation only; request for arbitrary Cypher/AWS call → `UnsupportedQuery`; malformed JSON → bounded retry → rule fallback; unknown metric → unsupported |
| Resolver | Unique name resolves; common name returns multiple candidates and the workflow abstains; DBLP homonym suffix distinct; not found; confidence and source IDs present |
| Metrics | Exact values for each metric with window, metric version and run ID; unknown window rejected |
| Path | G1 A→G 4 hops with per-hop supporting works; A→H no path; depth and result caps; timeout becomes typed failure |
| Community | Membership, size, cross-community edges; high-degree vs bridge distinction uses stored values; a row with `converged=false` is reported as iteration-limited and the verifier rejects any claim that calls it converged |
| Semantic | Filters applied; items labeled descriptive; vector mode cannot emit deterministic numeric claims |
| Evidence | Bounded size; stable IDs; deterministic and semantic evidence separated |
| Synthesis | Schema-invalid output rejected; every claim has evidence IDs; abstains on insufficient evidence |
| Verification | Wrong count → UNSUPPORTED or CONFLICTING; missing evidence ID → UNSUPPORTED; fabricated researcher ID rejected; unsupported claim removed or labeled |
| Injection | Instruction text in a title, abstract and generated profile does not alter the plan, the query, or the answer |
| Audit | Record contains plan, resolved IDs, evidence IDs, metric versions, run ID, prompt/model versions, verification result, answer hash |
| Benchmark | At least 12 questions with expected outcomes (Section 4, question 9-5) |

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

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-09/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

## 11. Final checklist (Phase 9 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] User text cannot become arbitrary database code (allowlisted operations, parameterized templates).
- [ ] Ambiguous researcher names do not silently resolve to one identity.
- [ ] Every numerical and path claim has evidence IDs; unsupported claims are removed, weakened or labeled.
- [ ] Prompt-injection tests pass.
- [ ] Deterministic graph retrieval and semantic retrieval are tested and reported separately.
- [ ] Prompts and schemas are versioned; model outputs are validated; no chain-of-thought is exposed.
- [ ] The benchmark-query suite passes; known failure modes are documented.
- [ ] Any live LLM smoke is within the approved cap, or was not run and is disclosed.
- [ ] A fresh `sbt check` on JDK 17 passes; the reviewer returned APPROVE; the human wrote `human-gate.md` and `commit.txt`.
