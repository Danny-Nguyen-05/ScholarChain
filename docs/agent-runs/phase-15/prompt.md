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
