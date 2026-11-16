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

## Work order 3: P41 request-count scaling and rate-limit env wiring (Step 0)

Scope (`session-2-plan.md` rows F26 and P41, section 5.3 step 2): a second target-tracking policy for query-api on `ALBRequestCountPerTarget`, with the CPU policy kept, plus the Terraform env wiring of the P40 rate-limit override. Terraform authoring only, offline; nothing is run against AWS. P40 was committed as `cceb1f5`.

Coordinator read-only facts (2026-11-16):
- `aws_appautoscaling_policy.http_cpu` (`modules/runtime/compute.tf` about line 303) covers the three HTTP services, with `cpu_target` 60 and cooldowns 300 / 60 s.
- `aws_lb.query` and `aws_lb_target_group.query` have `count = var.enabled && var.image_revision != null ? 1 : 0`.
- The query-api environment comes from the aws-mode map `aws_role_env["query-api"]`.
- The deployer already allows `PutScalingPolicy`, `DeleteScalingPolicy` and `DescribeScalingPolicies` (`deployer/phase14_main.tf` 585, 596), and F26 records the `TargetTracking-*` alarms.
- `tests/infra/test_runtime_shape_14b.py:64-71` pins the exact list of planned scaling policies.

Proposed defaults (coordinator, 2026-11-16):
1. A second policy for query-api only, `ALBRequestCountPerTarget`, with `resource_label` "<alb arn_suffix>/<target group arn_suffix>". It exists only when the runtime is deployed and the target is set. Cooldowns 300 / 60 s, and scale-in stays on. The CPU policy and target 60 are unchanged for all three services.
2. `query_requests_per_target_target`: number, default null (no policy), a whole number from 1 to 100,000 requests per target per minute. The value comes from P35.
3. `query_semantic_rate_limit_per_second` (1-100,000) and `query_semantic_rate_limit_burst` (1-1,000,000), both nullable with default null, which leaves them unset so the code defaults 50 / 100 apply. They are set on query-api only, in aws mode.
4. No cache-size variable (the code default 1,024 is well above 100-200 questions).
5. One dashboard panel for ALB `RequestCountPerTarget` and `HTTPCode_Target_4XX_Count`. It appears only when the ALB exists and stays within P9's 50-metric limit.
6. Owners:
   - infra-engineer: `infra/terraform/**` and its `terraform test` files;
   - test-engineer: `tests/infra/**`, only where the shape checks list policies or env names;
   - documentation-engineer: the plan draft line, which also fixes review finding R3 at `session-2-plan.md:581`.
7. Schedule: build Mon 2026-11-16, one review Tue 2026-11-17, commit by Wed 2026-11-18 12:00 CST after the user's "Yes, commit" (before the P15 pins refresh and the P35 values that day).

Step 0 answer (user, chat, 2026-11-16): "Accept defaults"

Coordinator rule slip (2026-11-16, disclosed): a read-only `grep -rn 'service_capacity\b' infra/terraform/environments` matched one line of the private `course.local.tfvars` (line 18, the text `service_capacity = {`, with no value shown). Nothing from it was used. Later greps exclude `*.local.tfvars`.

## P41-D follow-up answers (user, chat, 2026-11-16)

Verbatim: "1: (a). I'll read the Voyage usage page after the session and note the read time. Report it as the total for the session window, not per task, and compare it with the size of the fixed question set (misses ≤ distinct questions). If the page doesn't separate the window, mark it "unverified". 2: Yes, reword the P35 row. 3: Yes, keep the history entry."

Second follow-up (user, chat, 2026-11-16), verbatim: "1(a) and 2(a): accept. … From here, please don't open new questions on the Voyage-calls figure. It's a footnote. Put the time into the pipeline bundle." Meaning:
- 1(a): add the section 6.3a caveats. A total up to 4 × distinct questions is explained by task starts, and the uncoalesced duplicate misses on a cold task are noted.
- 2(a): "session window" means the R-b load window only. If the usage page cannot isolate that window, the figure is "unverified".

## Priority decision after P41 Step 0 (user, chat, 2026-11-16)

Verbatim: "Agreed on finishing P41 first. For the rest, change the priority: the R0 pipeline comes first, because Hadoop/Spark on EMR carries far more grade weight than elasticity and we have only one EMR retry. Before choosing the order, classify every open prerequisite as: (1) must exist before Session 2 (the live run can't work without it), (2) can be done offline after Session 2 (e.g. ER confidence intervals, P30/P31, docs), (3) can be dropped and stated as a limitation. Show the list with owner and estimated time for each. Then build group 1 in this order: the pipeline/EMR fixes with a local dry run of the full step chain (both sizes), then P42, P35, P15, P20, and my approval record. Review in bundles (one pipeline bundle, one elasticity bundle), not per item. Go/no-go Wednesday 18:00 CST: if the pipeline bundle isn't reviewed, committed and dry-run locally, Session 2 moves to the Sat/Sun fallback."

Working rule (user, chat, 2026-11-16), verbatim: "Time is the main risk. From now on: 1. Classify the open prerequisites (must-before-Session-2 / after / drop) and show me the must list with owners and time estimates today. 2. Run independent owners in parallel where files don't overlap (pipeline owners can start now while P41 finishes). 3. Only ask me questions that affect money, security, or the pipeline's correctness. For everything else, apply your recommended default and list it in the next status. 4. Reviews in bundles: pipeline, then elasticity. Go/no-go Wednesday 18:00 CST; fallback Sat Nov 21."

Coordinator defaults applied under rule 3 (2026-11-16):
- P18: the infra-engineer proves the base plan against the leftover state offline; the human decides at the pipeline review.
- If the pipeline is ready at go/no-go but the elasticity bundle is not, the whole session moves to Sat 2026-11-21 (one base-apply).
- R-c is dropped (Q17).
- P34 is deferred until P41 is committed (both edit `infra/terraform/phase12b.tf`).
- The optional P41 test-engineer coverage is not done.
- `storage-engineer` works in an isolated git worktree so that no two sbt runs share this tree.

Questions kept for the user because they affect money or the pipeline: the P25 EMR caps, and the P21 network download.

P25 and P21 decisions (user, chat, 2026-11-16), verbatim: "P25: approved. Cap 4 runs and USD 3.36 cumulative, including Session 1's EMR spend. Confirm the project worst case stays ≤ USD 22. Rule: S first; if S succeeds the next run is L; if S fails, retry S once and drop L as a stated limitation. If L fails, no retry: report it with logs. P21: approved. Download the pinned DBLP archive once from the public mirror and verify the sha256. Keep the archive out of git; commit only the manifest, checksum and slice script."

Coordinator check of the P25 cost condition, from `session-2-plan.md` §6.3, §6.3a and §6.4:
- The ledger holds 2 Session 1 runs at an estimate of USD 1.68. With a cap of 4 runs and USD 3.36 cumulative, it allows exactly 2 more runs at the USD 0.84 ledger estimate each.
- R0's EMR cost block is already capped for S + L: 3.83 cluster-hours at USD 0.50, which is USD 1.92.
- Under the rule, Session 2 has at most 2 EMR runs: S then L, or S then an S retry. An S retry is no longer than L, so the EMR cap does not grow.
- R0 + R-b cap stays at 5.93, and the project at caps stays at 15.83 + 5.93 = **USD 21.76 ≤ 22.00**.
- Condition: L must fit the 90-minute run. If the P6 local L time shows it does not, the cap must be recomputed (P25 note), and that is a new money decision for the user.

Rubric priority (user, chat, 2026-11-16), verbatim: "Prioritize by rubric points. Order: (1) R0 pipeline (Hadoop+Spark on EMR, real data); (2) the coauthor/path fixes stay on the after-list but are mandatory, as core collaboration queries; (3) elasticity after R0; (4) in Phase 17: README commands verified on a clean checkout, agent replay instructions, and all agents submitted. Low-value polish (wording, history entries, footnote figures): apply defaults, don't ask me."

What changes:
- P3 (direct-coauthor context budget) and P4 (path abstentions) move from "drop" to "after Session 2, mandatory". They are fixed and tested offline after the session, and do not depend on R-c.
- The rest of the R-c set (P10, P12, P14, P16, P36) stays dropped.
- Phase 17 must include: README commands replayed on a clean checkout, agent replay instructions, and all agent definitions submitted.

Q12 decision (user, chat, 2026-11-16), verbatim: "Q12 can't be dropped: the course README requires at least 30 benchmark questions covering coauthor breadth, max team size, direct collaboration, shortest paths, components, communities, bridge researchers, temporal change, topics, institutions and evidence, and the instructor didn't approve reducing it. Move it to the after-Session-2 list. Show which of these types Session 1's 40 questions already cover, and propose how to cover the rest offline against the local stack (no paid calls unless within the ledger)."

Consequence: Q12, the 30+ question benchmark covering all 11 types, moves from "drop" to "after Session 2, mandatory". Coverage of `experiments/inputs/14c/questions.txt` (40 questions, read 2026-11-16) is shown to the user in chat. The proposal is pending the user's choice of evaluation mode.

Q12 evaluation mode (user, chat, 2026-11-16), verbatim: "(b), but run all 33 questions with real answers, not 11. At about USD 0.0014 per answer (Session 1: 55 answers ≈ USD 0.075) that's about USD 0.05. Run it after P3/P4 are fixed, and score retrieval, claims and the answer text against the computed answer key. Key handling: propose how the run gets an Anthropic key consistent with our rules (key only in Secrets Manager, never in files, logs or shell history, deleted and revoked afterwards). If there's no safe way, fall back to (a) and state it in the report. Confirm the exact cost from the ledger before running."

The coordinator's key-handling proposal is in chat, pending the user's security approval. The exact ledger cost is confirmed before the run.

Key-handling approval (user, chat, 2026-11-16), verbatim: "Approved, with three additions: 1. The run command passes the key only as an environment variable of that one process, never as a CLI argument (visible in ps). 2. The runbook step says to run with shell tracing off (set +x). 3. USD 1 spend limit on the new key. Scope it to its own workspace if the console allows. Size the "local graph + real Anthropic writer" mode before committing to (b), as you said. Fallback (a) if it's too big."

Approved procedure:
- The user creates the key, with a USD 1 limit and its own workspace if the console allows.
- It is stored with `read -rs` and `put-secret-value` from stdin, then `unset KEY`.
- The run starts with shell tracing off (`set +x`). The key is passed only as an environment variable of the one run process, never as a CLI argument.
- The user closes the shell afterwards.
- The secret is deleted with no recovery window, and the key is revoked.
- An agent checks before the run that nothing logs the environment or the key.

Sizing of the mixed mode (local graph + real Anthropic writer) comes before committing to (b). If it is too large, the fallback is (a).

Review routing (user, chat, 2026-11-16), verbatim: "When the sbt check is done. From now on trigger the review agent using opus 5.5 high on your own. Clear. No more separate reviewer"

Consequence: from now on, after the bundle's gates pass (`sbt check` and the clean-copy `check.sh`), the coordinator launches the independent read-only `code-reviewer` agent itself (Opus 5.5, high) with the reviewer prompt. The user no longer runs a separate external reviewer. The reviewer's verdict is recorded verbatim in `review.md`. Every commit still needs the user's explicit "Yes, commit".

Standing commit consent (user, chat, 2026-11-16), verbatim: "Alright after the reviewer approved i give you permission to commit it and continue for me. Clear?" From now on, a bundle is committed by the coordinator right after the code-reviewer agent's APPROVE, and work continues to the next item. Limits: no commit on REQUEST-CHANGES; push to `origin/phase-15` after every approved commit (user, chat, 2026-11-16: "Yes a"), no force-push; human-owned records (approval and gate records, pin refreshes) stay the user's.

Recorded consequences: P41 is finished first. The pipeline bundle comes next, then the elasticity bundle (P42, P35), then P15, P20 and the human's approval record. There is one review per bundle. Go/no-go is Wed 2026-11-18 18:00 CST; if it fails, Session 2 moves to Sat 2026-11-21 / Sun 2026-11-22.
