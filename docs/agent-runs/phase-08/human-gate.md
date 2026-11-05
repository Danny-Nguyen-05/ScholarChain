# Phase 8 human acceptance

Recorded: 2026-10-30 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 8 local scope (Subphases 8A and 8B), with the
deferred findings below. Subphase 8C (live ingestion and retrieval smoke)
remains OPEN and deferred to Phase 14C.**

This file transcribes the user's decision; it is not an agent approving its
own work. On 2026-10-30 the user stated that they had asked their
implementation agent to write the missing human gates and it had not, and
asked: **“Can you create them for me? … Can you do that for me?”** That
instruction expressly authorizes writing this closeout record on the user's
behalf. It does not authorize a commit; the user commits it. No earlier human
decision or review record is changed.

Acceptance covers, on `phase-8` (merged to `main` by PR #4, merge commit
`0f0eeb1dfd451d9caf86d926d1ec5b7f4a6a97ce`):

- 8A: `3c45de74ec5900b8ac5c0273b5bf80bef8f84b1e` — Implement Phase 8A embeddings and stable-slot ingestion
- 8B: `5fee9ffc607cf802e4aaddf4a261c21f1f232fec` — Implement Phase 8B local ingestion and retrieval validation

## Accepted implementation and validation

- Embedding client port and fake, stable-slot vector keys, the manifest-driven
  ingestion runner, the five document renderers and local retrieval
  validation on the G1 fixture; render-only real-model manifest producer and
  an authored (unexecuted) live query-smoke command.
- User-supplied independent reviews, retained verbatim in [review.md](review.md):
  **APPROVE for 8A repair round 1** (F1, N1 fixed) and **APPROVE for 8B repair
  round 1** (B1, N9 fixed; R1 fixed in 8B).
- Latest retained JDK 17 full gate: **766 passed / 0 failed**, exit **0**
  (core 157, Hadoop 64, entity resolution 39, Spark 38, storage 51, RAG 33,
  independent 376, build verification 8); Java 17.0.20.1, sbt 1.10.7, 695.67 s.
  Metadata: [final-check.json](evidence/8b-r1/final-check.json). Raw log SHA-256
  `3b5abff12a025530e445a79ccddfe438a0f1df29f25c240078ebe4b81b46876f` (raw log
  was kept in `/tmp` only). Tests were not rerun for this closeout.

## Accepted deferrals and remaining gates

The human accepts 8A/8B with these findings **OPEN/nonblocking**, owners and
details in [repairs.md](repairs.md). Acceptance is not repair closure.

- N2–N8, R2, R3, N10–N14, N16–N19 remain open and deferred.
- **Must be resolved or explicitly disclosed before any 8C live run:**
  N15 (query-smoke approval requires ingest-sized caps), R3 (filterable
  metadata budget checked only after embedding) and N11 (mixed summaries omit
  `sourceDataset`, to be disclosed in the 8C metadata report).
- **8C is not run.** No live S3 Vectors or Bedrock call has been made. 8C
  returns in Phase 14C after deployment, with its own human-written ingest
  and query-smoke approvals, and its caps drawn from the shared USD 200
  project budget (plan of record: phase8.md shared-budget note and phase12.md
  “Shared AWS budget and deployment window”).
- Real embedding quality, live latency, cost, IAM and cleanup remain
  unverified. Fake-embedder retrieval results are not live-quality evidence.

## Closeout boundary

This decision accepts the local Phase 8 scope and the disclosed deferrals. It
does not authorize live AWS/provider calls, 8C execution, deployment,
expenditure or cleanup; those keep their separate gates. Phase 8 is fully
closed only after 8C runs or its omission is accepted in a later record.
