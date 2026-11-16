# Phase 15 work order

Plan: `<Google Drive>/My Drive/plan/phase15.md` (Data pipeline run and elasticity experiments).
Session plan: `docs/runbooks/session-2-plan.md` (Session 2, DRAFT revision 3; approved by the human as a plan document on 2026-11-15, not a Procedure R approval record).
Tool: Claude Code orchestrator (main session). Subagents are launched with model `opus` (Opus 5.5) at effort `high`, as the user asked on 2026-11-14.

## Opening (2026-11-15)

- Phase 14 closed: human gate ACCEPTED WITH DEFERRALS (`docs/agent-runs/phase-14/human-gate.md`), accepted commit `ee50bf3` (`docs/agent-runs/phase-14/commit.txt`), merged to `main` by PR #10 at the user's request ("can you open the pr merge phase 14 into main and then open phase 15 for me", chat, 2026-11-15); merge commit `a576878`.
- Branch `phase-15` created from `main` at `a576878`. Untracked drafts carried in the working tree, not committed: `docs/runbooks/session-2-plan.md`, `docs/demo-script.md`.
- No AWS, Anthropic or Voyage call is made in Phase 15 until a Session 2 Procedure R approval record written by the human exists.

## How Session 2 maps onto Phase 15

| Session 2 piece (session-2-plan.md) | Phase 15 subphase |
|---|---|
| Offline prerequisites P0-P43 (budget guard, EMR fixes, manifests, load generator, dashboard, request-count scaling, semantic route) | 15A (manifests, load generator, derivation scripts) and the setup for 15B |
| Stage a (R0): EMR Hadoop then Spark at about 10.5k and 50k real DBLP works; about 10k vectors and a retrieval smoke | 15A experiments A and B (EMR) |
| R-b: small elasticity experiment, failure and recovery | 15B experiments C-F, reduced as the instructor allowed |
| R-c (optional, gate total <= USD 22): coauthor and path reruns | recorded under Phase 16B |

## Human decisions already recorded (sources)

- Instructor reply to ScholarChain's own request (human-supplied, class channel, 12:10 PM CST 2026-11-15): reduced scales approved (about 10.5k and 50k works; up to 10,000 real voyage-4-lite vectors; ER gold set 200 reviewed / 194 definitive, resolve the 6 if practical and explain AI-assisted validation); budget raise declined, USD 25 stays; a smaller, carefully designed elasticity experiment is acceptable. Summary in `session-2-plan.md` §1b; the human keeps the original.
- Session 2 plan answers (2026-11-15): Q1 keep the USD 3 margin; Q3 cap Neptune at 1 NCU (P32 done: all Neptune cost was serverless capacity); Q4 the human reviews the 6 ER pairs; Q9 narrow `ecs:StopTask` in an IAM window; Q11 alerts USD 18 / 20 / 22; other questions at their defaults (`session-2-plan.md` §9.1).
- §9.2 answers (2026-11-15): public `/v1/semantic/retrieve` with the same API key, bounded top-k and query length, rate limiting, typed errors, tests and no data beyond the internal route; R-c optional behind the <= 22 gate; ledger transfer `15b->16b:28`; deployer role removed in final cleanup. P40 cutoff: reviewed and committed by Wed 2026-11-18 12:00 CST, else the health-check fallback, no last-minute changes.
- Cost to date: USD 15.83 of 25 (provisional C11, `docs/agent-runs/phase-14/evidence/14b/session-1/section-c/c11-cost-report.md`).

## Work order 1: P0 budget guard (Step 0)

P0 performs the Phase 14 runbook step A3 that the user skipped on 2026-11-11: move the live budget (USD 200, alerts 50/80/100%) to USD 25 with actual-spend alerts at USD 18 / 20 / 22. Offline: `infra-engineer` changes `infra/terraform/billing-bootstrap` (notification set, tests, README) and the `scripts/billing` pins as needed; then the user's reviewer and commit. Live: the human runs the reviewed `budget_execution.py modify` procedure in a billing-role window.

Step 0 questions asked 2026-11-15 (answered 2026-11-15, below):
1. Alert type: actual spend only at USD 18 / 20 / 22, no forecast alerts (default yes).
2. Keep the USD 25 limit and the custom period 2026-10-01 to 2027-01-01 (default yes).
3. Keep the same private verified recipient (default yes).
4. Live modify on Tue 2026-11-17 (default).
5. Before then, a read-only Switch-role check that `scholarchain-billing-deployer` still works (default yes).

Step 0 answers (user, chat, 2026-11-15): "Accept all five, with one condition: the budget must exclude credits and refunds (spend before credits, matching Cost Explorer's 15.75). With USD 140 of credits, a budget that counts credits stays at 0 and the alerts would never fire. Confirm in the Terraform/script and say how the current Phase 12 budget is set. Also note in the plan that the budget covers AWS only; Anthropic and Voyage stay in the ledger total."

Coordinator check of that condition (read-only, 2026-11-15):
- `infra/terraform/billing-bootstrap/main.tf` `cost_types`: `include_credit = false`, `include_refund = false`, `include_tax = true` (unchanged by P0).
- `scripts/billing/budget_execution.py` `COST_TYPES` starts `{"IncludeCredit": False, "IncludeRefund": False, ...}` and the modify readback refuses a budget whose `CostTypes` differ (lines 38 and 427-431).
- Live Phase 12 budget: no recorded API readback of its `CostTypes` (the Phase 12D readback stage ended BLOCKED-ON). Observed behaviour supports credit exclusion: the Budgets page shows USD 15.75 spent (7.87% of 200), equal to Cost Explorer with credits excluded, while the Bills page shows USD 0.00 net after credits. P0's modify readback is the first recorded API confirmation.
- The AWS budget covers AWS charges only; Anthropic and Voyage spend is tracked in the LLM ledger and the C11 combined total.

Phase 15 plan questions 15-1 to 15-6 are largely answered through `session-2-plan.md` (caps in §6; load levels and the failure scenario in the R-b stage; OpenSearch omitted); the remaining ones are confirmed in Step 0 of 15A.

## Work order 1: P0 outcome (2026-11-15)

User-launched review 1 returned REQUEST-CHANGES (records only); repair round 1 followed; recheck review 2 returned APPROVE (`review.md`, `repairs.md`). The user said "Yes commit and push it for me" (chat, 2026-11-15): commit `d5e74aa` on `phase-15`, pushed to `origin/phase-15`. The live modify is the human's, on Tue 2026-11-17, from a step-by-step checklist (git-ignored `target/phase15/p0/nov17-budget-modify-checklist.md`, no agent AWS call).

Open decision for the live modify: `budget_execution.py` accepts the modify gate record only under `docs/agent-runs/phase-14/` and its packet only under `docs/agent-runs/phase-14/evidence/14b/` (`MODIFY_RECORD_PREFIX`, `MODIFY_PACKET_PREFIX`, lines 58-59); `budget_verification.py` requires `docs/agent-runs/phase-14/evidence/14b/budget-modify-verify-<name>` (line 431). Asked of the user 2026-11-15 (default: keep those paths, with no code change, and cross-reference them from Phase 15).

## Work order 2: P40 public semantic route and query-embedding cache (Step 0)

Scope (`session-2-plan.md` row P40, §9.2 answer 1): `POST /v1/semantic/retrieve` on query-api with the same API key as the other `/v1` routes, forwarding to semantic-service; a bounded LRU query-embedding cache around the Voyage client in semantic-service, with hit and miss counters on `/metrics`; served in offline-synthetic mode for the P35 rehearsal. Acceptance checks (1)-(9) as in the plan row. Owners: `service-engineer` (route, rate limiter, composition, OpenAPI, config, service tests), `rag-engineer` (cache decorator and its tests), `test-engineer` (independent API test under `tests/**`). Cutoff: reviewed and committed by Wed 2026-11-18 12:00 CST, else the health-check fallback; no last-minute changes.

Coordinator read-only facts (2026-11-15): `SemanticApiConfig` defaults are `maxTopK` 50, `maxQuestionChars` 8192, `maxBodyBytes` 65536, `maxFilters` 16, `timeoutMs` 5000; no rate limiter exists in `modules/services`.

Step 0 answers (user, chat, 2026-11-15): "Accept all defaults (A: keep the phase-14 folders and point to them from the Phase 15 records). Two additions to P40 and R-b: 1. Add the S3 Vectors query cost (per query plus data processed) of the elasticity load to R-b's planned and worst-case budget. 2. The load generator uses a fixed question set (about 100–200 distinct questions), so Voyage calls are bounded by cache misses. Report 429s separately from successful responses, and exclude them from latency and throughput figures."

Recorded consequences:
- Decision A (live modify): the modify gate record goes under `docs/agent-runs/phase-14/` and its packet under `docs/agent-runs/phase-14/evidence/14b/`, as the wrapper requires; the Phase 15 records cross-reference them. No code change.
- Addition 1 goes to `session-2-plan.md` (documentation-engineer): S3 Vectors query pricing (US East (N. Virginia) figures on the public S3 pricing page, read 2026-11-15; Ohio not listed): USD 2.50 per million query requests, plus query data processed at USD 0.004 per TB for the first 100K vectors, where data processed per query = average vector size (vector, key and filterable metadata) x vectors in the index. Worst case bounded by the P40 rate limit (requests above it get 429 and never reach S3 Vectors).
- Addition 2 goes to P42 (experiment-engineer, load generator) and P40's `/metrics`: a fixed question set of about 100-200 distinct questions; 429s reported separately and excluded from latency and throughput.

Follow-up questions Q16 and Q17 (raised by the documentation-engineer's S3 Vectors cost amendment, `session-2-plan.md` §9.3). User's answers (chat, 2026-11-15): "Q17: accept. Keep R-b as designed and expect R-c to be dropped (document why in the report). Q16: accept the existing per-level limits only if the worst case (198,600 queries: S3 Vectors query and data-processed charges plus Voyage cache misses) is already in R-b's worst case and keeps the project ≤ USD 22. Show the numbers. If it doesn't fit, lower the per-level limits to the minimum that still shows scale-out to 2 tasks and scale-in. Also confirm the rate-limit setting from P35 won't throttle the heaviest load level, so scaling is driven by served requests, not 429s."

Coordinator check of the Q16 condition (2026-11-15, from the plan's figures): S3 Vectors at 198,600 queries = 198,600 x (USD 2.50 per million + 40,960,000 B x USD 0.004 per TB) = 0.4965 + 0.0326 = USD 0.53; Voyage misses are bounded by distinct questions x semantic-service task starts (at most about 800 embeds, about 0.8M tokens, at most USD 0.016, USD 0 inside the free tokens), independent of the query count. R0 + R-b cap = 6.18 - 0.80 + 0.53 = 5.91, plus 0.02 Voyage = 5.93; project at caps = 15.83 + 5.93 = USD 21.76 <= 22 (margin 0.24). The condition holds, so the existing per-level limits (600 / 3,000 / 15,000 / 30,000 / 150,000) are kept. Rate-limit rule (for P35 and P42): because the per-level limits bound the query count and cost, the Session 2 rate `r_S2` is set from P35 at no less than twice the measured peak served rate per query-api task at level 50; P35 acceptance requires zero 429s at every level, and any 429 in R-b is reported per level. Not yet verified: P35 has not run.

Step 0 questions asked 2026-11-15, each with the coordinator's default (all accepted):
1. Public limits: topK at most 20, question at most 1,000 characters, body at most 8 KiB, filters at most 16 (same filter shape as the internal route); the internal route keeps its limits.
2. Rate limit: an in-memory token bucket per API key in each query-api task; code default 50 requests/s with a burst of 100, overridable by environment variable; a typed 429 `RATE_LIMITED` reply that is marked retryable; 429s counted on `/metrics`. The Session 2 value is set from P35 so that load level 50 is not throttled.
3. Cache: in-memory LRU per semantic-service task, 1,024 entries by default (environment override), keyed by (model, input type, exact question text), no TTL; only successful embeddings are cached; the key and logs never contain question text in clear (hash only).
4. No Terraform change in P40: the code defaults apply, and any environment override rides with P41's infra change.
5. Schedule: rag-engineer and service-engineer in parallel now; then the test-engineer's independent test; full `sbt check`; one review of the whole P40 bundle targeted for Mon 2026-11-16; commit after your "Yes, commit" by Tue 2026-11-17, which leaves Wed morning as buffer.
