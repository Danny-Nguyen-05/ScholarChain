# ScholarChain Phase 7 — Storage adapters and loading: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** Oct 29 – Nov 3, 2026 (can run in parallel with Phase 12).

> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 7, **Storage adapters and loading**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **Phase 6 supplies the data products.** Spark writes partitioned Parquet node, edge, metric, community, component, path-evidence and semantic-summary tables plus four load manifests (Neptune, DynamoDB, S3 Vectors, ordinary S3) and a run manifest under `export/`. Read `modules/spark/README.md`, the Phase 6 owner report and the manifest contracts in `modules/core` first. Storage identifiers must equal Spark identifiers exactly.
- **Modules.** `modules/storage` is an empty module (`.gitkeep` only) that depends on `core`. `rag` and `services` depend on `storage`, so the ports and fakes defined here are the contract those modules code against. The build has **no AWS SDK dependency yet**.
- **AWS is not available to this phase.** Unit, contract and adapter tests use in-memory fakes and stubbed SDK clients. Live AWS tests are authored behind an explicit profile but **not run**: they run in Phase 14 (subphase 14C) after Terraform has created the resources. Disclose this in the owner report.
- **Spark exports Parquet, but Neptune's bulk loader historically ingests CSV (openCypher or Gremlin format) or RDF.** The agent must confirm the accepted formats from current AWS documentation (aws-knowledge MCP is available; read-only). If Parquet is not accepted, a small additional export is needed (see 7A task 6).
- **Schedule slot:** Oct 29 – Nov 3, 2026 (about 6 days). Phase 12 (Terraform) can run in a second session at the same time because its paths (`infra/terraform/**`) do not overlap `modules/storage/**`.

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/storage-engineer.md`, `docs/agent-runs/README.md`.
2. The course Phase 7 section, "S3 Vectors design", "Required technology stack" and "Configuration" in the course README: https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-7-implement-storage-adapters-and-loading
3. `modules/spark/README.md` and `docs/agent-runs/phase-06/owner-report.md`, `test-report.md`, `evidence/` (the real output layout, schema versions and manifest fields).
4. `modules/core/src/main/scala/.../core/` contracts: `SparkAnalyticsContracts.scala`, `SparkAnalyticsConfig.scala`, `StableIds.scala`, `Records.scala`, `RunManifest`/`Provenance`.
5. Current AWS documentation (use the aws-knowledge MCP, read-only) for: Neptune bulk loader formats and the `neptunedata` API, openCypher parameterized queries, S3 Vectors API limits (vectors per PutVectors call, metadata size, filterable metadata, top-K, dimensions), DynamoDB conditional writes. Record exact URLs and the limits you rely on.

## 4. Decisions and open questions that apply to the whole phase

- **Fakes first.** Every port has an in-memory fake in `modules/storage` main code (package `...storage.fakes`) so `rag`, `services` and `tests` can use them without AWS. (Open question 7-1.)
- **AWS SDK for Java v2** is the client library (pure Java; works from Scala 3). Versions are pinned by `build-engineer` in the dependency ledger (`project/Versions.scala` / `Dependencies.scala`). Services needed: `s3`, `dynamodb`, `neptunedata`, `s3vectors`, and later `sqs` and `bedrockruntime` (those two are added in Phase 8).
- **Read-only runtime credentials for the graph.** The code has two separate Neptune ports: `GraphLoader` (write) and `GraphReader` (read-only, allowlisted parameterized openCypher templates). Runtime services only ever receive a `GraphReader`.
- **No long text in vector metadata.** Long text lives in ordinary S3; metadata holds only filter fields and pointers.
- **Idempotency everywhere.** Reloading the same manifest produces the same final state and no duplicates.
- **Open questions for the phase (ask in Step 0 of the subphase that needs them):**
  - **7-1.** Put fakes in main code so other modules can use them? Recommended: yes.
  - **7-2.** Is Docker available for container-based fakes (LocalStack, DynamoDB Local)? Recommended: do not depend on Docker; use in-memory fakes and stubbed SDK clients that assert request shape (condition expressions, batch sizes, retry behavior).
  - **7-3.** Include the optional `ResearcherMetricCache` DynamoDB table? Recommended: yes. Runtime needs point reads of per-window metrics by `researcherId` + `windowId`, and storing every window's metrics as Neptune node properties would bloat the nodes.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-07/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `build-engineer` | `build.sbt`, `project/**`: AWS SDK v2 dependency entries, an `awsIntegration` test configuration or tag that is **off by default** | 7A (on demand later) |
| `storage-engineer` | `modules/storage/**`: ports, fakes, adapters, loaders, module tests, `modules/storage/README.md` (keys, indexes, limits, retry policy, cleanup) | 7A–7C |
| `domain-engineer` | `modules/core/**`: any new shared record or config contract the storage layer needs (table-key records, load results, rejected-vector record, storage config) | 7A, only if `storage-engineer` returns `BLOCKED-ON domain-engineer` |
| `spark-engineer` | `modules/spark/**`: only the optional Neptune openCSV export in 7A task 6 | 7A, only if the format check requires it |
| `test-engineer` | `tests/**`: independent contract and adversarial tests against the ports and fakes | 7C primary; interface-first in 7A–7B |
| `infra-engineer` | Not used here. The Terraform that creates the tables, buckets, Neptune and vector indexes is Phase 12 | — |

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
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-07/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-7` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 7X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Ports (in `modules/storage`)

| Port | Methods (minimum) | Notes |
|---|---|---|
| `ObjectStore` | `put(key, bytes, contentType, metadata)`, `get`, `exists`, `head` returning content hash | Versioned keys, SHA-256 content hash stored as object metadata and checked on read; run manifests written last |
| `RunLedger` | `startRun`, `recordStage`, `recordFailure(retryCount)`, `completeRun`, `getRun` | DynamoDB, conditional writes |
| `EntityLinkCache` | `putLink`, `lookupByNormalizedName`, `lookupByExternalId` | Backs the runtime researcher-name resolver (Phase 9) |
| `QuerySessionStore` | `createIfAbsent(queryId, idempotencyKey)`, `get`, `update` | Idempotency for POST /v1/query |
| `EvidenceBundleStore` | `put(bundle)`, `get(evidenceId)` | Large bundles go to S3 with a pointer row |
| `ArtifactRegistry` | `register(artifactId, version, uri, hash)`, `latest`, `get` | Also records vector key → text hash |
| `ResearcherMetricStore` | `put(record)`, `get(researcherId, windowId)`, `batchGet` | Optional table (question 7-3) |
| `GraphLoader` | `submitBulkLoad(manifest)`, `status(loadId)` | Write path, loader role only |
| `GraphReader` | `node(id)`, `neighbors(id, window, edgeTypes, limit, cursor)`, `directCoauthors`, `shortestPaths(a, b, maxDepth, window, limit)`, `communityMembers`, `crossCommunityEdges` | Read-only, allowlisted parameterized openCypher, bounded depth/limit/timeout |
| `VectorStore` | `ensureIndex(name, dimension, metric)`, `putBatch`, `query(index, vector, topK, filter)`, `get(keys)` | Batching, retries, rejected-vector report |

### 7.2 DynamoDB tables and keys (state the access pattern for each)

| Table | Partition key | Sort key | Access pattern | Notes |
|---|---|---|---|---|
| `RunLedger` | `runId` | `stageKey` | One run's stages and failures | Conditional put for stage start; no TTL |
| `EntityLinkCache` | `entityType#normalizedKey` | `policyVersion#sourceId` | Name or external ID → candidate researcher IDs with affiliations and confidence | Loaded from Spark researcher nodes and accepted Phase 5 links; no TTL |
| `QuerySession` | `queryId` | `itemType` | Query state; second access path by idempotency key through a GSI | Conditional create; TTL only for disposable sessions, documented |
| `EvidenceBundle` | `evidenceId` | `part` | Evidence lookup for GET /v1/evidence | Pointer to S3 for large content; content hash stored |
| `ArtifactRegistry` | `artifactId` | `version` | Latest artifact and vector-key → text-hash registry | Conditional put prevents silent text change |
| `ResearcherMetricCache` (optional) | `researcherId` | `windowId` | Exact stored metrics with metric version and run ID | Written by the loader from Spark metric tables |

On-demand capacity unless the agent justifies otherwise. Every write that must not be overwritten uses a condition expression; the tests assert the expression text and the conflict behavior.

### 7.3 Neptune

- **Nodes:** Researcher, Work, Venue, Institution, Topic, plus selected context nodes. **Edges:** AUTHORED, COAUTHORED_WITH, PUBLISHED_IN, AFFILIATED_WITH, HAS_TOPIC, RESOLVES_TO, DERIVED_FROM, SUPPORTED_BY, as implemented by the Phase 6 graph model.
- **IDs:** node and edge IDs equal the Spark stable IDs byte for byte. A test loads a Spark-shaped fixture and asserts every Neptune ID is present in the Spark output set and vice versa.
- **COAUTHORED_WITH properties:** `jointPublicationCount`, `firstCollaborationYear`, `lastCollaborationYear`, window start/end, evidence pointer (the support-table key). Every edge must trace to supporting works (SUPPORTED_BY or the support table), and the loader validates endpoints and evidence before submitting.
- **Loader:** build the loader input from the Phase 6 export manifest, upload to the graph S3 prefix, call the bulk loader through the `neptunedata` API with an IAM role, poll status with a bounded timeout, and record the result in `RunLedger`. Format question: see context and 7A task 6.
- **Reader:** parameterized openCypher only. No string concatenation of user text. Each template has a depth cap, result cap and timeout from config.

### 7.4 S3 Vectors

- Five index abstractions with the exact names `researcher-profile-v1`, `collaboration-community-v1`, `paper-abstract-v1`, `collaboration-path-v1`, `topic-institution-summary-v1`. Dimension and distance metric come from config (decided in Phase 8; the adapter takes them as parameters).
- **Vector key:** deterministic, stable, built from `docType`, entity ID, window ID and a model-version tag. A second write with the same key and a different `textHash` is **rejected and counted**, not silently overwritten (ArtifactRegistry holds the registry).
- **Metadata (compact, filterable):** `researcherId` or `communityId`, `documentType`, `windowStartYear`, `windowEndYear`, `topicId`, `institutionId`, `sourceDataset`, `textS3Uri`, `textHash`, `embeddingModel`, `runId`. The adapter validates that every metadata value fits the service limits captured from the docs and rejects (to a reject record) anything that does not.
- **Batching and retry:** batch size from the documented per-call limit; bounded exponential backoff with jitter for throttling and transient failures; permanent failures go to a rejected-vector report with a reason code.

### 7.5 Idempotency and failure policy

- Loaders are safe to rerun: S3 keys are content-addressed or versioned; DynamoDB writes are conditional; Neptune loads use stable IDs; vector writes check the registry.
- A reload of an unchanged manifest reports `unchanged` counts and writes nothing new.
- Every adapter returns a typed result (written, unchanged, rejected with reason, retried) instead of throwing for expected failures.

## 8. Subphases

Execute the subphases in order: 7A → 7B → 7C. Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 7A — Build wiring, ports, fakes, S3 and DynamoDB adapters

**Owners:** `build-engineer`, `storage-engineer`, `domain-engineer` (only if blocked), `spark-engineer` (only task 6), `test-engineer` (parallel, interface-first).

**Open questions:** 7-1, 7-2, 7-3.

**Tasks:**

1. `build-engineer`: add the AWS SDK v2 entries (`s3`, `dynamodb`, `neptunedata`, `s3vectors`) to the ledger and `storage` module dependencies; add an off-by-default `awsIntegration` test mechanism (a ScalaTest tag excluded from `sbt check`, run only with `SCHOLARCHAIN_AWS_ITEST=1` and an explicit profile); keep `sbt check` green and fast.
2. `domain-engineer` (only if needed): shared storage records, for example table-key records, load-result records and a `StorageConfig` contract that follows the course "Configuration" shape (buckets, Neptune endpoint/port/timeouts, vector bucket and index names).
3. `storage-engineer`: define all ports in Section 7.1 and their in-memory fakes.
4. `storage-engineer`: S3 `ObjectStore` adapter (versioned keys, content hash, run manifest written last) and the six DynamoDB adapters (Section 7.2) using conditional writes, with a documented table/key/access-pattern table in `modules/storage/README.md`.
5. `storage-engineer`: loaders from the Phase 6 manifests into `EntityLinkCache` (researcher names, external IDs, accepted links) and `ResearcherMetricCache`.
6. **Format check.** Confirm the Neptune bulk-loader formats from current documentation. If Parquet is not accepted, return `BLOCKED-ON spark-engineer` / user with the doc URL and request a small Spark work order: write an `neptune-opencypher-csv` export, derived from the existing node and edge tables, with the same IDs, in Phase 6's export layout. Do not change existing tables or ID formulas.
7. Tests: fake behavior, request-shape tests with stubbed SDK clients (condition expressions, batch sizes), idempotent reload, content-hash mismatch on read, missing/malformed metadata.

**Done when:** ports and fakes exist and are used by tests; S3 and DynamoDB adapters pass their tests; the format question is answered with citations; `sbt check` passes.

> **⛔ STOP after 7A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 7B until the user sends a new prompt.

### Subphase 7B — Neptune loader and reader, S3 Vectors adapter

**Owners:** `storage-engineer`, `test-engineer` (parallel).

**Open questions:** none new; ask any the 7A review raised.

**Tasks:**

1. `GraphLoader`: manifest → loader input → upload → `neptunedata` bulk-load call → bounded status polling → `RunLedger` record. Endpoint and role ARN come from config.
2. Pre-load validation: every coauthor edge has both endpoints in the node set and at least one supporting work ID; reject and count violations without loading them.
3. `GraphReader`: the allowlisted templates in Section 7.3 with parameters, depth/limit/timeout caps. A test proves user text never appears in the query string.
4. `VectorStore` S3 Vectors adapter: `ensureIndex`, batched `putBatch`, `query` with metadata filters, `get`; retry/backoff; rejected-vector report; vector-key and `textHash` conflict check through `ArtifactRegistry`.
5. Capture the **current service limits** from documentation (with URLs and the date) in `modules/storage/README.md`.
6. A CLI entry point (`StorageLoadMain` or equivalent) that, given a Phase 6 export manifest and a config file, runs the S3 upload, DynamoDB loaders and Neptune bulk load through the ports. It defaults to **dry run** (prints what it would do and the counts it expects), runs fully against the fakes locally, and refuses a real AWS target unless an explicit flag and the config's approved-environment name are present. Phase 14C will execute it live.
7. Tests: Neptune ID parity with a Spark-shaped fixture, invalid edge rejection, query parameterization, vector metadata too large, duplicate vector key with same text (unchanged) and with different text (rejected), throttling retry then success, retry exhaustion goes to the rejected report, and the CLI's dry-run and refusal behavior.

**Done when:** all Section 9 rows for Neptune and S3 Vectors pass on fakes/stubs; limits are documented with citations; `sbt check` passes.

> **⛔ STOP after 7B.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 7C until the user sends a new prompt.

### Subphase 7C — Independent hardening, gated live suite, cleanup notes

**Owners:** `test-engineer` (primary), `storage-engineer` (repairs and the live-suite code), `build-engineer` (on demand).

**Tasks:**

1. `test-engineer` independent suites under `tests/**` against the ports: serialization round trips, duplicate keys, missing/malformed metadata, DynamoDB conditional-write conflict, idempotent reload, reader refuses over-depth/over-limit requests, a source scan proving runtime-facing code takes `GraphReader` and not `GraphLoader`.
2. `storage-engineer`: author the **live** `awsIntegration` suite (S3 round trip, DynamoDB conditional conflict, tiny Neptune load and query, tiny vector write and query) behind the explicit profile. **Do not run it.** Document the exact command, required environment variable names, expected cleanup, and cost bound for Phase 14C.
3. Document in `modules/storage/README.md`: schemas, keys, indexes, metadata fields, batch sizes, retry policy, idempotency strategy, limits with citations, and cleanup procedure for the live suite.
4. Run the full `sbt check`.

**Done when:** `sbt check` passes; the live suite compiles but is excluded from `check`; the README contains every item the course lists for the Phase 7 report.

> **⛔ STOP after 7C.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Serialization | Round trip for each stored record; unknown schema version fails; corrupt row rejected |
| S3 | Versioned key; content-hash mismatch on read; manifest written last; missing object |
| DynamoDB | Conditional create succeeds once and conflicts on repeat; condition expression text asserted; idempotency-key GSI lookup; TTL only where documented |
| Idempotent reload | Second load of the same manifest writes nothing new for every store |
| Neptune | Spark ID parity both directions; edge with missing endpoint rejected; edge without supporting work rejected; reader templates parameterized; depth/limit caps enforced; loader timeout |
| S3 Vectors | Metadata too large rejected; duplicate key same text unchanged; duplicate key different text rejected; batch splitting at the documented limit; throttle retry then success; retries exhausted → rejected report |
| Safety | Runtime-facing code cannot obtain a `GraphLoader`; no secrets in logs or exceptions; live suite excluded from `check` |

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

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-07/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

## 11. Final checklist (Phase 7 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] Ports and fakes exist for S3, DynamoDB tables, Neptune loader/reader and S3 Vectors; other modules can use them.
- [ ] Neptune IDs match Spark IDs; coauthor edges trace to supporting works; the reader is read-only and parameterized.
- [ ] DynamoDB keys match the stated access patterns; conditional writes are tested.
- [ ] Vector writes cannot silently change text for an existing key; long text stays in S3.
- [ ] Loaders are idempotent and tested.
- [ ] Service limits are captured with documentation URLs.
- [ ] The live AWS suite is authored, excluded from `sbt check`, and **not run**; the Phase 14C run is disclosed as an open gate.
- [ ] A fresh `sbt check` on JDK 17 passes.
- [ ] The reviewer returned APPROVE; the human wrote `human-gate.md` and `commit.txt`.
