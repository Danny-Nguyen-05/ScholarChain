# Phase 10 human acceptance

Recorded: 2026-10-30 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 10 local implementation (Subphases 10A and
10B), with the carried findings and unverified live gates below.**

This file transcribes the user's decision; it is not an agent approving its
own work. On 2026-10-30 the user stated that they had asked their
implementation agent to write the missing human gates and it had not, and
asked: **“Can you create them for me? … Can you do that for me?”** That
instruction expressly authorizes writing this closeout record on the user's
behalf. It does not authorize a commit; the user commits it. No earlier human
decision or review record is changed.

Acceptance covers, on `phase-10` (not yet merged to `main`):

- 10A: `c85da7365927a1f7d8ee5ab1f67c5c1a128391b3` — service foundation and retried reservation repair
- 10B: `0c5ee89994b5b738a3490ef5e8f032fdc67327b2` — services and graph deadline repairs

## Accepted implementation and validation

- `query-api`, `graph-service`, `semantic-service` and `embedding-worker`;
  authenticated, bounded routes with idempotency, cursor pagination, trace
  IDs, timeouts, retries and circuit breakers; evidence and explain routes;
  health/readiness; four container images.
- User-supplied independent reviews, retained verbatim in [review.md](review.md):
  **APPROVE for 10A repair round 1** (F1 closed) and **APPROVE for 10B repair
  round 2** (F6 closed; F9 closed in round 1; no F1–F5 regression).
- Latest retained JDK 17 full check: **1,216 passed / 0 failed** in 149
  suites, exit **0**, sbt 721 s, JDK 17.0.20.1. Evidence:
  [evidence/10b-repair-2/](evidence/10b-repair-2/) (`check-result.json`,
  `final-validation.json`). Raw logs were kept in `/tmp` only (O3). Tests were
  not rerun for this closeout.

## Accepted deferrals and remaining gates

The human accepts Phase 10 with these items **OPEN/nonblocking**, owners in
[repairs.md](repairs.md). Acceptance is not repair closure.

- F7, F8, F10–F16 carried to Phase 11 or later (DLQ publication at the attempt
  limit, worker-loop exception containment, stage audit fields, route labels,
  422 code preservation, response examples, semantic limits, proxy surface,
  live GraphSnapshot readiness).
- **F17:** `SCHOLARCHAIN_GRAPH_TIMEOUT_MS` must be set once per environment for
  both `query-api` and `graph-service` in the Phase 12–14 deployment config.
- O3: full raw logs live only in `/tmp`; hashes and excerpts are retained.
- Live adapters and deployment, snapshot-backend readiness, stable cursor-key
  injection, SQS redrive, a durable dispatcher with PROCESSING recovery and a
  full OpenAPI semantic validator remain later human-gated work. Offline
  synthetic composition is not evidence of live behavior.

## Closeout boundary

This decision accepts the local Phase 10 scope and the disclosed deferrals. It
does not authorize merging, live AWS/provider calls, deployment or
expenditure; those keep their separate gates.
