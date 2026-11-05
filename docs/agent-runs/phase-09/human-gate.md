# Phase 9 human acceptance

Recorded: 2026-10-30 (America/Chicago).

## Decision and authority

**ACCEPTED BY THE HUMAN: Phase 9 local implementation (Subphases 9A, 9B and
9C), with the deferred findings and unverified live gates below.**

This file transcribes the user's decision; it is not an agent approving its
own work. On 2026-10-30 the user stated that they had asked their
implementation agent to write the missing human gates and it had not, and
asked: **“Can you create them for me? … Can you do that for me?”** That
instruction expressly authorizes writing this closeout record on the user's
behalf. It does not authorize a commit; the user commits it. No earlier human
decision or review record is changed.

Acceptance covers, on `phase-9` (merged to `main` by PR #5, merge commit
`3c0a817305d783bbb6a4cb6fe9bb654d06d8632a`):

- 9A: `f139f9c925b4925864a2c9a33734d869a1929cd2` — runtime contracts, planning and resolution
- 9B: `2527de01252286080e6db776b9cc0199a9353e1e` — retrieval and evidence workflow
- 9C: `5c9d320923d47560c1d1c48afe18aca3adce72b5` — synthesis, verification and audit

## Accepted implementation and validation

- `LlmClient` port with a scripted fake; QueryPlanner, ResearcherResolver,
  parallel metric/path/community/semantic stages, EvidenceBuilder,
  AnswerSynthesis, deterministic ClaimVerification and Audit; `retrievalMode`
  graph/vector/fused; abstention and fail-closed audit; offline benchmark.
- User-supplied independent reviews, retained verbatim in [review.md](review.md):
  **APPROVE for 9A repair round 1** (B1–B4 fixed), **APPROVE for 9B repair
  round 1** (B1 fixed; N1 confirmed fixed) and **APPROVE for 9C** with no
  blocking findings.
- Final 9C gates: targeted **299 passed / 0 failed**; actual CLI benchmark
  **15/15**; JDK 17 full check **1,131 passed / 0 failed**, exit **0**
  (core 207, Hadoop 64, entity resolution 39, Spark 38, storage 80, RAG 107,
  independent 588, build 8), 780.69 s. Metadata:
  [check-2-result.json](evidence/9c/check-2-result.json). Raw log SHA-256
  `830bb94d47e4d122f44013f5a42f82fc45fed696df4020afba395511cbd0bc37` (raw log
  was kept in `/tmp` only). Tests were not rerun for this closeout.

## Accepted deferrals and remaining gates

The human accepts Phase 9 with these items **OPEN/nonblocking**, owners and
details in [repairs.md](repairs.md) and
[coverage-and-limitations.md](evidence/9c/coverage-and-limitations.md).
Acceptance is not repair closure.

- 9C review NB1–NB10 are logged and not implemented. NB1 (unrelated
  citations on non-semantic claims), NB3 and NB8 were later confirmed
  nonblocking in Phase 11.
- N2, N4–N7, O5–O7, O10 and R1 keep their disclosed limits; R2 is cosmetic.
- All results are **offline correctness** with scripted LLMs and fake stores.
  They are not evidence of live-model quality, injection resistance,
  production latency or real-enrichment coverage. Live SDK
  region/model/tool/temperature compatibility (N4) remains a live gate.
- **The optional 9C live LLM smoke was not authorized or run.** If run later,
  it needs its own human-written approval with a cap drawn from the shared
  USD 200 project budget (phase9.md shared-budget note; phase12.md
  “Shared AWS budget and deployment window”).

## Closeout boundary

This decision accepts the local Phase 9 scope and the disclosed deferrals. It
does not authorize live model or AWS calls, deployment or expenditure; those
keep their separate gates.
