# ScholarChain Phase 8 — Embeddings and S3 Vectors population: implementation and handoff plan

Prepared: 2026-10-22. Intended reader: a fresh manager/orchestrator agent in Codex, Cursor or Claude Code, and the independent reviewer agents the user launches between subphases.

**Schedule slot:** 8A–8B Nov 4 – Nov 7, 2026; 8C Nov 15 – Nov 17, 2026 (after Phase 14).

> **⛔ WORK ONE SUBPHASE AT A TIME, THEN STOP.** Do exactly one subphase per prompt. When it is done or blocked, return the reviewer prompt and **end your turn**. Do not start, prepare or "get ahead on" the next subphase, even if you have time or the next step looks obvious. The user reviews every subphase before the next begins. Doing several subphases in one run is a failure of this work order, even when the code is correct.

## 1. Your assignment

Implement Phase 8, **Embeddings and S3 Vectors population**, in `/Users/danny/Documents/UIC/CS441/ScholarChain`.

You are the coordinator. Launch specialist subagents with your tool's native delegation, give each a bounded work order, route dependencies and repairs, collect observed evidence, and produce the review handoff prompt for the user. Do not write specialist production code yourself. Subagents must not launch more subagents.

Four rules apply to every subphase:

1. **Ask before implementing.** At the start of every subphase you may ask the user any question, and the user wants you to. Ask everything at once, give a recommended default for each question, and wait for answers before editing files. If you have no questions, say so explicitly, then proceed.
2. **One subphase at a time, then stop for the user's review.** Implement only the subphase named in the prompt you were given. When it is done or blocked, stop and end your turn. Do not begin the next subphase in the same run and do not draft its code ahead of time. The next subphase starts only when the user pastes a new prompt, normally the one the reviewer wrote. This also applies to repair rounds: fix only the listed findings, then stop.
3. **Do not trigger a code reviewer.** Never launch, invoke or auto-select the `code-reviewer` agent or any other reviewer. The user handles review outside your session.
4. **End every subphase with a copyable reviewer prompt.** Your final message for a subphase must contain the complete reviewer prompt in one fenced code block (Section 10). The user pastes it into a separate reviewer agent. That reviewer reviews read-only, then writes the next prompt for you: either the next subphase or a repair round. Then stop and wait.

This document is an implementation work order. It is not proof of human acceptance, instructor approval, a completed run, or permission to spend money on AWS.

## 2. Project context and verified starting point

- **Inputs:** Phase 6's four semantic summary types (researcher-profile, community, collaboration-path, paper) with their source references, plus topic and institution nodes and counts. Phase 7 provides the ports and fakes: `VectorStore`, `ObjectStore`, `ArtifactRegistry`, `RunLedger`. Read `modules/storage/README.md` for the captured S3 Vectors limits.
- **What this phase builds:** deterministic document rendering, a versioned embedding client, a manifest-driven ingestion pipeline (text to S3, embedding, batched vector writes, hash-based dedup), and retrieval smoke tests. Exact counts, paths, components and bridge scores stay in Neptune/DynamoDB/Spark outputs and are **never** answered from vector similarity.
- **AWS split.** 8A and 8B run entirely on fakes and a deterministic local embedder. **8C is the live bounded ingestion into real S3 Vectors** and runs only after Phase 14 has deployed the infrastructure and the user records approval. It is part of this phase's gate; if Phase 14 is not reached, disclose it as an open gate.
- **Corpus size.** The course asks for at least 10,000 vectors, or an instructor-approved smaller corpus when the selected subset does not yield 10,000 meaningful units. The Phase 6 real-data slice (about 20,000 DBLP publication records) should yield enough researcher-profile and paper vectors, but confirm the count from the Phase 6 export before promising it.
- **Schedule slot:** 8A–8B Nov 4 – Nov 7, 2026. 8C Nov 15 – Nov 17, 2026 (inside Phase 14).

Environment for every sbt command (copy exactly):

```bash
cd /Users/danny/Documents/UIC/CS441/ScholarChain
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch check        # about 7+ minutes; the "checkProbeInjectFailure ... injected format-stage failure" line is an expected self-test
```

## 3. Source of authority and required reading

1. `AGENTS.md`, `CLAUDE.md`, `docs/agents.md`, `.claude/agents/storage-engineer.md`, `.claude/agents/rag-engineer.md`, `docs/agent-runs/README.md`.
2. The course Phase 8 section and "S3 Vectors design": https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-8-create-embeddings-and-populate-s3-vectors
3. `modules/storage/README.md` (ports, limits, vector-key rules) and the Phase 7 owner report.
4. Phase 6 summary and export contracts: `SparkAnalyticsContracts.scala` (semantic summary and source-reference records), `modules/spark/README.md`.
5. Current AWS documentation (aws-knowledge MCP, read-only): the chosen embedding model's input limits, output dimensions and region availability; S3 Vectors index immutability (dimension and metric are fixed at creation).

## 4. Decisions and open questions that apply to the whole phase

- **Open questions for the phase (ask in Step 0 of 8A):**
  - **8-1. Embedding provider and model.** Recommended: Amazon Bedrock Titan Text Embeddings (current version available in the course account's region), invoked through the AWS SDK so authentication is an IAM role and no API key is stored. Alternative: an OpenAI embedding model through the existing provider pattern, which needs an API key in Secrets Manager. The model ID is configuration, never a constant.
  - **8-2. Vector dimension and distance metric.** Recommended: cosine, and the smallest dimension the chosen model supports that still separates the smoke-test neighbors (a smaller dimension lowers storage and latency). The index is immutable after creation, so this is decided once.
  - **8-3. The fifth index.** The course lists five indexes. Phase 6 produces four summary types; `topic-institution-summary-v1` needs a deterministic template over topic and institution nodes plus their aggregate counts. Recommended: implement all five.
  - **8-4. Paper abstracts.** Abstracts may be missing for DBLP records. Recommended: embed the permitted abstract when present, otherwise a compact deterministic paper summary (title, venue, year, topics, team size), and record which one was used.
  - **8-5. Queue.** SQS or a manifest-driven batch? Recommended: define the `EmbeddingWorkQueue` port with an SQS adapter **and** a manifest-driven batch runner; the manifest runner executes the 8C ingestion, the SQS path exists because Phase 15 experiment C needs a queue backlog.
- **Model version is part of identity.** The embedding model ID and version are stored with every vector and part of the vector key tag.
- **Deterministic fake embedder for tests.** A hashed bag-of-words embedder so the smoke tests have real, predictable neighbors without any model call.

## 5. Delegation and ownership

Follow `docs/agents.md`. One writer per artifact class. Record each launched agent's native ID, role, model, assigned paths and handoffs. You alone assemble `docs/agent-runs/phase-08/**` from agent reports.

| Agent | Owns | Subphases |
|---|---|---|
| `rag-engineer` | `modules/rag/**` and `prompts/**` for this phase: rendering templates, chunking policy, `EmbeddingClient` port and Bedrock adapter, model versioning, semantic-context format, retrieval smoke tests | 8A–8B |
| `storage-engineer` | `modules/storage/**`: `EmbeddingWorkQueue` port, SQS adapter, manifest runner, S3 text-store writes, hash dedup via `ArtifactRegistry`, `RunLedger` failure records, vector write batches | 8A–8C |
| `domain-engineer` | `modules/core/**`: embedding-document, embedding-work-item, vector-metadata and semantic-context contracts, if not already present | 8A, on demand |
| `build-engineer` | `build.sbt`, `project/**`: `sqs` and `bedrockruntime` SDK entries | 8A, on demand |
| `test-engineer` | `tests/**`: independent retrieval and dedup tests | 8B |
| `deploy-engineer` | Executes the approved live ingestion command only | 8C, only after the human approval record |

The two engineers receive **separate** work orders, as the course requires. Their shared interface is the `EmbeddingDocument` and vector-metadata contract in `core`.

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
11. **Evidence stays lean.** Put exact commands, exit codes, test counts and meaningful log excerpts under `docs/agent-runs/phase-08/evidence/<subphase>/`; summarize in `owner-report.md` and `test-report.md`. Do not commit full datasets, run outputs or large inventories. Human decisions (`human-gate.md`, `commit.txt`, any approval record) are written only by the user; never write or rewrite them.
12. **Reports** use exactly these fields: `STATUS`, `OWNER`, `WORK ORDER`, `FILES CREATED`, `FILES MODIFIED`, `COMMANDS RUN`, `TEST RESULTS`, `VALIDATION RESULTS`, `ASSUMPTIONS`, `RISKS`, `MANUAL ACTION REQUIRED`, `BLOCKED-ON OWNER`, `BLOCKED-ON EVIDENCE`, `NEXT GATE`. Never report an unobserved pass; list unrun commands as unverified.
13. **No commits or pushes by agents.** The user commits, normally once per approved subphase on a `phase-8` branch.
14. **Lean scope (about 30 days remain before the 2026-11-25 deadline).** Implement what the baseline and rubric require. Do not add optional components (OpenSearch, CI workflows, extra indexes or services) unless the user asks. Record each omission in the owner report so the final report can disclose it.
15. **Stop at the boundary.** When the subphase is done or blocked: ensure no subagents, builds or jobs are still running; return the handoff packet and the reviewer prompt (Section 10); end the turn with **"Subphase 8X is ready for review. I have stopped and will not start the next subphase until I receive the next prompt."**

## 7. Design (binding unless a subphase question changes it)

### 7.1 Documents and rendering (rag-engineer)

- **Document types:** researcher-profile, community, collaboration-path, paper, topic-institution-summary.
- **Rendering is deterministic:** the same input rows and template version give byte-identical text. Templates use only fields from computed tables and source records (the Phase 6 rule). Each document carries its source references and a `templateVersion`.
- **Chunking:** a chunk policy (maximum characters or tokens, boundary rule, overlap) for permitted abstracts or longer text; chunk IDs are stable (`StableIds.chunkOrProfileId`).
- **Text store:** the authoritative text or generated profile is written to ordinary S3 (graph/RAG prefix) as JSON with its content hash; the vector metadata holds only the pointer.

### 7.2 Embedding client and model versioning

- `EmbeddingClient.embed(texts: Seq[String]): Seq[Vector]` with a bounded concurrency setting (from `operations.maxConcurrentLlmCalls`-style config), retries with backoff, and a typed failure result per item.
- The result carries `embeddingModel` (ID plus version) and `dimension`. A dimension that does not match the index is a hard error.
- Adapters: Bedrock (default, question 8-1), the deterministic fake, and optionally the OpenAI-style provider if the user chooses it.

### 7.3 Ingestion path (storage-engineer)

1. Read the work manifest (documents to embed: key, type, text pointer, text hash, window, IDs).
2. **Skip unchanged items:** if `ArtifactRegistry` already has the same vector key with the same `textHash` and `embeddingModel`, count `unchanged` and do nothing.
3. If the same key exists with a **different** `textHash` and the same model, count `vectorKeyTextConflict` and reject (Phase 7 rule).
4. Otherwise embed, build the compact metadata (Section 7.4 of Phase 7), write in batches through `VectorStore.putBatch`, register the key and hash, and record failures and retry counts in `RunLedger`.
5. Emit counters: written, unchanged, conflicts, rejected (with reason), retried, per-index counts, throughput (vectors per second) and total embedding calls.

### 7.4 Retrieval smoke tests and the semantic-context format

- Smoke tests, offline with the fake embedder: for at least five known queries (for example a researcher profile query, a topic query, a community query, a path query, an institution query), the expected neighbor appears in the top K. The expected neighbors are fixed in committed test fixtures.
- **Semantic-context format** for the synthesis agent (Phase 9): a compact list of items with `vectorKey`, `score`, `documentType`, the S3 pointer, and a short excerpt. It is labeled as descriptive context, never as proof of an edge or a metric.
- A test proves each vector result can be followed to its ordinary S3 text through the pointer and that the stored hash matches.

### 7.5 Live ingestion (8C)

- Runs the same manifest runner against real S3 Vectors and Bedrock, bounded by an explicit vector-count cap, a concurrency cap, and a dollar cap, all from the approval record.
- Reports throughput, rejected records, duplicate handling, query latency samples (for example 50 queries per index, p50/p95), index counts, the metadata schema, the embedding model version, and cost and object counts.

## 8. Subphases

Execute the subphases in order: 8A → 8B → 8C. Each subphase starts only from a prompt produced by the reviewer of the previous one, or from the user. **One subphase per run:** after a subphase's handoff you stop, and the user reviews it before anything else happens. Never chain subphases together. Every subphase has the same frame:

> **Step 0 — Questions.** You may ask the user any question before implementing. Ask the open questions below that are still open, plus any of your own, each with a recommended default. Wait for answers.
> **Step N — Handoff and stop.** Do not trigger any code reviewer. Return the handoff packet and the copyable reviewer prompt (Section 10), then end your turn. Do not start the next subphase.

### Subphase 8A — Templates, embedding client, queue/manifest runner, contracts

**Owners:** `domain-engineer` (contracts), `build-engineer` (SDK entries), `rag-engineer` and `storage-engineer` in **separate** work orders, `test-engineer` (interface-first).

**Open questions:** 8-1, 8-2, 8-3, 8-4, 8-5.

**Tasks:**

1. `domain-engineer`: embedding-document, work-item, vector-metadata and semantic-context contracts with wire examples and tests (additive; no existing field changes).
2. `build-engineer`: add `sqs` and `bedrockruntime` SDK entries.
3. `rag-engineer`: rendering templates for all five document types; chunking policy; `EmbeddingClient` port, deterministic fake and Bedrock adapter (not called in tests); model-version handling; semantic-context format.
4. `storage-engineer`: `EmbeddingWorkQueue` port with a fake, an SQS adapter (request-shape tested against a stubbed client) and the manifest runner; S3 text-store writes; hash dedup and conflict handling; `RunLedger` failure and retry records.
5. Tests per Section 9, written against fakes.

**Done when:** all contracts, templates, ports and adapters exist; rendering is byte-deterministic; dedup and conflict behavior is tested; `sbt check` passes.

> **⛔ STOP after 8A.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 8B until the user sends a new prompt.

### Subphase 8B — Ingestion pipeline, retrieval smoke tests, independent tests

**Owners:** `storage-engineer`, `rag-engineer`, `test-engineer`.

**Tasks:**

1. A CLI entry point (`EmbeddingIngestMain` or equivalent) that reads the Phase 6 export plus work manifest and runs the pipeline against the **fakes**, with an end-to-end local run on the Phase 6 G1 fixture and on a small slice of the real-data export. No network.
2. Retrieval smoke tests with known expected neighbors (Section 7.4), the S3-pointer round trip, and the "exact metrics are not answered from vectors" rule documented in the semantic-context format.
3. `test-engineer` independent tests: same key / different text, unchanged skip, stale model version, dimension mismatch, missing abstract fallback, throttling retry and permanent failure to the rejected report, replay idempotency.
4. Author the 8C live command, its approval-record template (vector cap, concurrency cap, dollar cap, region, bucket and index names from config) and cleanup steps. **Do not run it.**
5. Run the full `sbt check`.

**Done when:** the local end-to-end ingestion is reproducible with identical counters on rerun; smoke tests pass; `sbt check` passes; the 8C command and template exist and are unexecuted.

> **⛔ STOP after 8B.** Return the handoff packet and reviewer prompt, then end your turn. Do not start 8C until the user sends a new prompt.

### Subphase 8C — Live bounded ingestion (after Phase 14 deploys)

**Start condition:** Phase 14 deployed the vector bucket, indexes, text bucket and IAM roles, and the user wrote an approval record containing the caps and budget. If these do not exist, do not start; tell the user.

**Owners:** `deploy-engineer` (executes the approved command and returns evidence). `storage-engineer` only for routed repairs.

**Tasks:**

1. Run the approved manifest ingestion against the real S3 Vectors indexes and Bedrock within the caps.
2. Collect the report listed in Section 7.5 and run the five retrieval smoke queries against the real indexes.
3. Record object counts, estimated cost, and the cleanup/teardown state.

**Done when:** at least 10,000 vectors (or the approved smaller corpus) are stored and queryable, the same key cannot refer to different text, every vector result resolves to its S3 text, and the report is complete. Repairs, if any, use a normal repair round.

> **⛔ STOP after 8C.** Return the handoff packet and reviewer prompt, then end your turn. The phase closes only after the user's own review and `human-gate.md`.

## 9. Required test matrix

| Area | Minimum meaningful cases |
|---|---|
| Rendering | Byte-identical output for identical input; every number in a document equals its source field; template version recorded |
| Chunking | Boundary and overlap rules; stable chunk IDs; empty and oversized text |
| Embedding client | Dimension mismatch is an error; retry then success; retries exhausted → typed failure; model version attached |
| Dedup | Unchanged text and model → skipped; same key, different text → conflict rejected; new model version → new key tag |
| Pipeline | Counters (written/unchanged/conflicts/rejected/retried); `RunLedger` failure and retry records; local rerun gives identical counters |
| Retrieval | Five known queries return the expected neighbor in top K on the fake embedder; every result follows its S3 pointer to text with a matching hash |
| Boundaries | No long text in metadata; exact metrics never sourced from vector results (documented and asserted in the context format tests) |
| Live (8C) | Count ≥ 10,000 or approved smaller corpus; sampled queries; rejected records reported |

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

When you receive a prompt that came from the reviewer, first append the reviewer's verdict verbatim to `docs/agent-runs/phase-08/review.md` under the subphase heading, marked "user-supplied external review". On REQUEST-CHANGES, log the routed findings in `repairs.md`. Then do what the prompt asks.

**Template you must complete and give to the user:**

Reviewer instructions removed at the user’s request; review prompts are provided in chat.

## 11. Final checklist (Phase 8 complete)

- [ ] Each subphase was reviewed by a user-launched reviewer; verdicts are retained in `review.md`.
- [ ] The same vector key cannot silently refer to different text.
- [ ] The embedding model ID and version are stored with every vector.
- [ ] Source text or profile content is fetchable from a vector result through its ordinary S3 pointer.
- [ ] Retrieval smoke tests pass offline and (8C) against real indexes.
- [ ] Exact counts, paths, components and bridge metrics come from graph/metric stores, not vector similarity.
- [ ] Throughput, rejected records, duplicate handling, latency samples, index counts, metadata schema, model version, cost and object counts are reported (8C).
- [ ] If 8C was not run, the live-ingestion gate is disclosed as open in `human-gate.md`.
- [ ] A fresh `sbt check` on JDK 17 passes; the reviewer returned APPROVE; the human wrote `human-gate.md` and `commit.txt`.
