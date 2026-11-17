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

Relaunch, Neptune and P34 decisions (user, chat, 2026-11-16 about 08:40 CST), verbatim:
"1. Relaunch: Yes, now, with the original briefs updated for current HEAD. Keep lane D's files and lane A's tftest file, but treat them as unreviewed drafts: re-run their tests. Each lane writes its work to disk as it goes, not only at the end. Tell me what interrupted the run at 23:17. If it was the machine sleeping, I'll run caffeinate.
2. Neptune: (a), lower the hold from 150,000 to 90,000. Condition: use the P35 measured rate (or the planning rate until P35 runs) and state how many minutes the level-50 hold lasts. It must cover scale-out plus at least 3 minutes of steady state at the scaled-out task count. If it doesn't, come back to me before choosing (c).
3. P34 as planned is impossible. Set min 1 / max 2.5 NCU. Correct the plan text (P34, F23, 5.3, 6.4 and every 0.1608/h ceiling claim). If a max=1 Terraform change or test exists, revert it. Recompute the gate thresholds at the real rate. List every number that changed."

Coordinator actions and findings:
- The interruption at 23:17:01 CST on 2026-11-15 (05:17:01Z) was a user interrupt in the main session. All six lane transcripts end with "[Request interrupted by user]" at that second, during the Stop-hook loop. It was not machine sleep. The six lanes were relaunched at about 08:40 CST, with progress files under `target/phase15/lanes/` (git-ignored). The surviving draft `infra/terraform/tests/phase15_stagea.tftest.hcl` belongs to lane B (the original brief), not lane A, so lane B re-checks it.
- No max=1 Neptune change exists. `phase12b.tf:22` still requires min >= 1 and max exactly 2.5, and `tests/phase15_elasticity.tftest.hcl` pins that max 1 is refused. Nothing to revert.
- Coordinator error corrected: the earlier figure "+0.37, worst case 22.13" used R-c's 3.5 h Neptune cap. R-b's Neptune window is about 5 h planned and 7 h at cap (back-solved from the 6.4 rows), so the correct cap increase at 0.402/h is +1.69, and the project worst case is 23.45. Decision 2(a) was taken on the wrong figure, and its hold condition is not met at the planning rate (90,000 at 250 requests/s = 6.0 min, against an estimated 9.5 min for scale-out plus 3 min). Per the user's rule, (a) is NOT applied and the choice goes back to the user.

R-b option decision (user, chat, 2026-11-16), verbatim:
"(i), with conditions:
1. Tax: Session 1's Bills page showed tax 0.00. Confirm whether tax applies to this account. If not, drop the ×1.11 row; if it does, come back to me, since 25.44 is over the hard ceiling.
2. The 5.8 h Neptune window is a hard stop: run the R-b load early in the window. At 5.8 h, destroy Neptune whether R-b has finished or not, and keep whatever elasticity data was captured. Put the clock times in the runbook.
3. Pre-R-b check: before applying R-b, spend to date (with its read time) + R-b cap must be ≤ 25.00; otherwise skip R-b.
4. Update the plan to floor 2 / project ≤ 23.00, list every changed number, and give me the exact wording for the P19 approval record.
Noted on the interrupt: I'll queue messages instead of stopping the session."

Coordinator notes:
- Tax cannot be confirmed from the repository. The Bills page showed "Taxes by service" USD 0.00 with net USD 0.00 after credits, which shows that no tax was charged on a zero net, not that the account is untaxed. The x1.11 column stays, marked pending the human's read of the Billing tax settings.
- R-c is dropped: the 5.8 h Neptune hard stop cannot hold R-c's Neptune window.
- The P21 partial file `target/phase6-inputs/6fg-dblp/dblp-2026-10-03.xml.gz.partial` (882,900,992 bytes) was written by the first lane-D run from 05:15:29Z, after the human's P21 approval at 05:13:55Z. That run read the approval in prompt.md, although its brief predated the approval. The interrupt at 05:17:01Z cut it off. The relaunched lane D made the one complete download (1,107,081,001 bytes, sha256 matches the pin). So the archive was fetched one and a fraction times, not once.

Tax-settings read (user, screenshot in chat, 2026-11-16): Billing → Tax settings → Tax registrations shows one entry, seller Amazon Web Services, Inc., with no TRN and no TRN status. The business address is in a US city that levies a local tax on cloud services. The account ID and address are deliberately not recorded here. Coordinator assessment: tax applying is NOT ruled out.
- AWS promotional-credit terms say credits are not applied against transaction taxes.
- The Bills page notes that its estimates exclude taxes unless listed.
- The local cloud-tax rate was 11% in 2025, and secondary sources report 15% from 2026-01-01 (unverified).
Per the user's condition 1 ("if it does, come back to me"), the decision goes back to the user, and the x1.11 column is not dropped.

Tax decision (user, chat, 2026-11-16), verbatim: "the portion of your bill deducted/covered by AWS credits is not taxed. Since they are credits so tax is 0"

Consequence: condition 1 of option (i) is answered by the human. The x1.11 column is dropped, and option (i) stands at floor 2 (project <= 23.00, worst case 22.97). Recorded limit: this holds while AWS credits cover the spend. Spend beyond the credit balance would be taxable, so the pre-R-b check (spend to date + R-b cap <= 25.00) stays.

P19 section 4a fixes (user, chat, 2026-11-16), verbatim:
"Good work. Fixes to section 4a before I sign:
1. Item 5: update to the corrected clock (destroy target T_N0 + 5 h 15 min, absolute stop + 5 h 30 min, so deletion ends inside 5.8 h) and the recomputed latest load start. The current draft's + 5 h 48 min ends past 5.8 h.
2. Item 2: add a line for my read of the remaining AWS credit balance (with its UTC time), which must be ≥ the Session 2 AWS cap; otherwise this approval is void.
3. Item 4: the pre-R-b check is spend to date + 3.57 ≤ 23.00 (floor 2), not 25.00. Above 23.00, R-b is skipped unless I record a new decision.
4. S fails twice: don't drop R-b. Use the P6 local S export for chunks and vectors (same Voyage cap), load them, and run R-b. The report states that the vectors came from the local run. Check that this path is in the runbook and that the P6 output is kept for it. If it's not feasible, tell me why.
5. Keep item 8: it covers the Session 2 Voyage key."

Hadoop team-size option and P18 (user, chat, 2026-11-16), verbatim:
"Hadoop: before I accept "keep 16", size one middle option. Keep the 16-author / 128-pair cap on coauthor-PAIR records only (so the pairs limit and ER blocking stay unchanged), but still emit the team/authorship records for every work, up to 80 authors (linear, not quadratic). Then large works stay in the graph and max team size is correct.
Tell me: which files and owners change, whether the 64 infra ceiling applies to team records or only pairs, whether ER or Spark contracts change, and how long it takes including tests and the P6 re-run.
If it touches ER/Spark contracts or costs more than ~2 h, fall back to keep 16 and disclose. In that case:
- the report and benchmark state the cap and its effects (works dropped, 12.9% of L pairs, components and bridges);
- the max-team-size benchmark questions show the system's 16 next to the true 71/79 from the Hadoop statistics, marked as a known limitation, not a pass.
P6: the reject-file check for "0 dropped by the limit" is fine; also record the count of works dropped (63 S / 210 L) as evidence.
P18: agreed. Plan stage a against the leftover state after `terraform state list` (addresses only, no state file reads) shows exactly the two guards. Anything else: stop and report."

Outcome of the user's team-size rule (coordinator, 2026-11-16): the hadoop-engineer's read-only sizing found that the middle option breaks two hard Spark invariants:
- the pair-count check (Phase6CJobs.scala:451-460 and 635-642);
- the unconditional W_r = T_r check (Phase6DEJobs.scala:541-554).
It also changes the core prep-config contract and the infra ceilings, at about 12-16 h of effort. By the user's rule ("If it touches ER/Spark contracts or costs more than ~2 h, fall back to keep 16 and disclose"), maxAuthorTeamSize stays 16. The disclosure is required in the report and the benchmark:
- the cap and its effects (works dropped: 63 S / 210 L; 12.9% of L's pairs; components and bridges);
- the max-team-size questions show the system's 16 next to the true 71 / 79 from Hadoop's largestTeam, marked as a known limitation, not a pass.
P6 records the dropped-work counts (OVERSIZE_TEAM 63 S / 210 L) as evidence, alongside the reject-file check for zero maxLocalSampleRecords drops.

L, second size, D1-D3 and budget (user, chat, 2026-11-16), verbatim:
"L: drop on EMR (P25 rule). Report the measured local evidence: L Hadoop passes in 132 s, 210 works dropped by the team limit, max team 79; ER runs out of memory at 22g after 16 min. Both EMR runs go to S and its retry.
Second size: if Spark can run on L locally with ER bypassed (identity pass-through, disclosed as such) with a small change, run it and record Spark time and graph size at L next to S. If the bypass isn't small, stop at Hadoop-only L evidence. Don't touch the EMR path for this.
D1/D2: add a test that feeds the exact arguments sc-step.sh builds into the Hadoop job's parser, plus the S run without workarounds as proof.
D3: tell me which node ER runs on, the instance type, what else runs there (YARN containers, daemons), and the free memory at 10g. My rule: 10g minimum, since it's the measured pass; go higher only if ER runs alone on that node with ≥2 GB headroom. Otherwise come back to me.
Budget: recompute the worst case with L dropped. Tell me whether floor 3 is back within reach.
Also: what came of the Hadoop team-record middle option (pairs capped at 16, team/authorship records kept up to 80)?"

S run cap (user, chat, 2026-11-16), verbatim: "Agreed on all items. Floor 2 stays. One change: cap each S run at 60 min if the per-step timeouts (Hadoop, ER 18 min, Spark, copy-out) plus cluster start-up fit inside 60 with margin. Show the sum. If they don't fit, keep 90. Update the worst case (expect ~22.47) and the P19 draft numbers to match."

Outcome (coordinator, from scripts/config/release.conf:297-307):
- The per-step timeouts are fixed shares of the run cap (PIPELINE_STEP_WEIGHTS stage-in 5, hadoop-prep 20, entity-resolution 20, spark-class-origin 5, spark-job 40, copy-out 10, which sums to 100%).
- At the 90-min cap the timeouts are 4.5 + 18 + 18 + 4.5 + 36 + 9 = 90 min. The four named steps alone are 81 min. Cluster start-up (the plan's 20-min cold start) comes on top, for about 110 min. That does not fit inside 60.
- At a 60-min cap the timeouts would shrink to 3 + 12 + 12 + 3 + 24 + 6. That leaves the Spark step 24 min against the spark-engineer's S estimate on EMR of 14-20 min (a 4-min margin at the high end) on a path never run on EMR.
- Per the user's rule, the cap stays at 90 min. The worst case stays USD 22.97 and the P19 draft numbers are unchanged.

P0 pre-checks (user, chat, 2026-11-16, before the Tuesday modify):
- Cost Explorer screenshot, Nov 13-16 by service, credits excluded: total USD 15.39; Nov 13 2.31, Nov 14 12.16, Nov 15 0.92 (Neptune 0.63), Nov 16 0.00.
- Read-only Switch Role check: `aws sts get-caller-identity --profile scholarchain-billing-deployer` returned an Arn ending `assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator`. The coordinator checked the account hash against the A3 pin `32c67ff8…bf3e`: it MATCHES. The account ID is not recorded here.

P26(c) Voyage tier (user, chat, 2026-11-16), verbatim: "Voyage Usage tier 1, payment method is already set, don't know how to check requests per minutes and tokens per minutes"
Coordinator: the configured model is voyage-4-lite (modules/rag, scripts/config). Voyage docs, Rate Limits page (docs.voyageai.com/docs/rate-limits, read 2026-11-16): Tier 1 voyage-4-lite / voyage-3.5-lite = 16M TPM, 2000 RPM. The Embeddings API reference gives the voyage-4-lite per-request cap: at most 1,000 texts and 1M tokens. The batched ingest (batchSize 100, about 12K tokens per request, about 100 requests for 10,000 items) is far inside these limits. P26(c) passes, provided the human's dashboard shows no project-level limit below the organization's.

Cost Explorer, 2026-10-01 to 2026-11-16, credits excluded (user screenshot, chat, 2026-11-16): total USD 15.75, average daily 0.34, 20 services. Spend sits on Nov 4 (small), Nov 13-15, and 0 on Nov 16. This matches the plan's C11 AWS figure of 15.75, so no new spend has appeared since the Nov 15 read.

D3 decision (user, chat, 2026-11-16), verbatim: "D3: none of the three. Use r5.xlarge for the primary node only (32 GiB, same 4 vCPU as m5.xlarge), with the ER heap at 10g, or 12g if the headroom stays ≥2 GB. Rationale: an OOM kill at 0.5–1 GiB free would likely repeat on the retry and burn both EMR runs. Confirm the r5.xlarge EC2 + EMR hourly rate for us-east-2 from the pricing page, and confirm EMR supports it on our release. Then recompute the worst case with the 60-min S cap. It must stay ≤ 23.00. If it doesn't, come back to me before changing anything. The Terraform/script change goes through the infra-engineer with terraform test and review as usual. Make the P19 draft numbers match."

Coordinator checks (2026-11-16):
- Rates (public AWS price lists, read 2026-11-16 about 11:49 CST): EMR offer file us-east-2 (publicationDate 2026-11-13T18:02:09Z) gives r5.xlarge 0.063 and m5.xlarge 0.048. The EC2 on-demand Linux us-east-2 file gives r5.xlarge 0.252 (32 GiB, 4 vCPU) and m5.xlarge 0.192. So the primary r5.xlarge costs 0.315/h and the core m5.xlarge 0.240/h, for a cluster rate of 0.555/h (was 0.48).
- EMR support: "Supported instance types with Amazon EMR", US East (Ohio): r5.xlarge minimum emr-5.13.0 / emr-6.0.0 / emr-7.0.0, so it is supported on the pinned emr-7.8.0.
- ER heap: on a 32 GiB primary, 12g (P6 RSS 13.9 GB) plus about 2.5-4 GiB of daemons leaves about 14 GiB free, at least 2 GB, so the user's rule gives 12g.
- The 60-min cap was rejected earlier by the user's rule (prompt.md "S run cap"). Worst case by run cap (EMR block = 2 runs x (cap + 15 min idle) + 20 min cold start, at 0.555/h exact, or 0.58/h with the plan's rounding margin):
  - 90 min: 3.83 h, block 2.13-2.22 (was 1.92), project at caps 23.18-23.27, ABOVE 23.00;
  - 75 min: 3.33 h, block 1.85-1.93, project 22.90-22.98;
  - 60 min: 2.83 h, block 1.57-1.64, project 22.62-22.69.
  The script ledger per run (budget.py method, x(cap + 15 min)) is 0.971 at 90, 0.833 at 75 and 0.694 at 60. The cumulative total with Session 1's 1.68 is 3.62, 3.35 and 3.07 against the 3.36 cap.
- At the user's 90-min cap the worst case exceeds 23.00, so nothing is changed: the decision goes back to the user.

S run cap and D3 go-ahead (user, chat, 2026-11-16), verbatim: "75 min. Go ahead: r5.xlarge primary, ER heap 12g, S run cap 75 min with the step timeouts you listed, budget.py and the pricing file updated, terraform test and review as usual. Then update the P19 numbers. The margins are thin (22.98 / 23.00; ledger 3.35 / 3.36). Record the EMR actuals right after each S run so the pre-R-b check uses real numbers, not the cap."

## EMR ledger cap after the pipeline-bundle review (2026-11-16)

Coordinator question (finding 1 of the pipeline-bundle review 1, `review.md` work order 4): `--record-actual` measures S from cluster creation (boot included) and adds a 900 s idle tail of 0.14, while the retry still reserves 0.84. At the 3.36 cap the retry is admitted only if S's recorded cost is at most 0.70 (about 75 min from cluster creation), so a late S failure would refuse the approved retry. Options: raise the cap 3.36 → 3.53 (Session 1's 1.68 plus the 3.33 h EMR block at 0.555/h; the 1.93 block is already inside the 22.98 project cap, so no project figure changes), or keep 3.36 and disclose.

User answer, verbatim: "Raise cap to 3.53 (Recommended)"

Coordinator defaults applied (not asked; outside the money, security and pipeline-correctness rule): review findings 7 (Phase 12C DynamoDB dashboard panels removed under P9) accepted, test run renamed and disclosed; finding 8, both r5 rates restated in the P19 draft for the user's approval record; finding 6, the 8 GiB copy-out ceiling kept with the reason recorded.

## EMR retry rounding budget after review 2 (2026-11-16)

Coordinator question (finding 1 of review 2, `review.md` work order 4): every ledger term rounds up to the cent, so with the 3.53 cap and a full 75-min S, the retry is admitted only if cluster creation to S submission plus the wait before recording is about 19 min or less (a 20-min cold start gives 0.88 and 3.54). Options: accept with operator steps (no money change), or add a 0.02 allowance (cap 3.55, project margin 0).

User answer, verbatim: "Accept, add steps (Recommended)"

Coordinator defaults applied (not asked): review 2 finding 6, `/readyz` stays in the semantic mix (weight 1 of 44, about 4,500 calls; bounded and small whatever the probe pricing), disclosed in the plan; finding 2, `--observe-seconds` is refused for a non-loopback target (experiment-engineer, after the P35 rehearsal ends, because P35 uses loadgen.py).

## P35 scaling target after the local rehearsal (2026-11-16)

Coordinator question: the P35 local rehearsal (run p35-local-1, evidence under `docs/agent-runs/phase-15/evidence/p35/`) was CPU-bound at 0.25 vCPU with no network latency, so its served rates (level 1 about 5,285/min, level 25 about 27,034/min per task) give T = 10,000 under the P35 rule (allowed 5,285 < T <= 13,517). The plan's live estimate (200 ms per request) puts level 25 at about 7,500/min and level 50 at about 15,000/min, so T = 10,000 would probably not scale out at level 25 live. Options: T = 3,000 from the live estimate (level 1 about 300 and level 5 about 1,500 below T; level 25 about 2.5x and level 50 about 5x; robust for about 50-400 ms latency; the Terraform max task count still caps scale-out), recorded as a deviation from the local rule; or T = 10,000 by the local rule.

User answer, verbatim: "T = 3,000 (Recommended)"

Coordinator defaults applied (not asked; the user's Q16 formula fixes them): `r_S2` = 3,500 (at least 2 x the local level-50 peak of 1,737 served requests per second per task, rounded up) and `b_S2` = 7,000 (2 x `r_S2`), both user-set tfvars (`query_semantic_rate_limit_per_second`, `query_semantic_rate_limit_burst`). The per-run request caps (198,600) bind the R-b cost, so these values do not change it. `query_requests_per_target_target` = 3000 is also a user-set tfvar.

## P0 budget modify moved to 2026-11-16 and the modify incident (2026-11-16)

User request, verbatim: "Can we do the p0 budget change now instead of waiting for tomorrow?"

Coordinator check before answering: no `scripts/billing/**` or `infra/terraform/billing-bootstrap/**` change since d5e74aa, template hash 946352f3…af28 unchanged, main checkout clean at a975775, P0 kit tests 18 OK. Only the date changed (D=20261116). The user ran every AWS step.

User request on the gate record, verbatim: "I want you to fill those for me". Coordinator action: filled only the factual blanks of `docs/agent-runs/phase-14/budget-modify-gate-20261116.md` (plan and input hashes, commits C and C2, operation, window 19:50-20:50, packet and backup paths); the user had already filled the date and author, then removed the DRAFT line, signed and committed it (C3 2611cc6).

Coordinator kit fix during the window (not tracked; `target/phase15/p0/p0_gate.py`): the hidden and visible prompts opened `/dev/tty` in text mode "r+", which raises `io.UnsupportedOperation` on a terminal (`P0_GATE_REFUSED: UNEXPECTED_UnsupportedOperation`, nothing written). Replaced with an unbuffered binary reader and a separate writer; tested in a real pty (hidden input not echoed, 5-line STS paste parsed) and the kit's 18 tests OK.

Outcome: the modify apply printed `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`, then the wrapper stopped with `MODIFY_APPLY_OR_BACKUP_FAILED_INCIDENT_REQUIRED` (exit 2). The user's read-only console check showed USD 25, custom 2026-10-01 to 2027-01-01, three actual-cost alerts at > $18, > $20 and > $22, one verified recipient, spend $15.75, excluded charge types Credit and Refund.

User decision, verbatim: "yes you can start the incident write-up and the wrapper fix tonight"

## Frozen session commit moved to tonight (2026-11-16)

Coordinator question: make tonight's reviewed billing-fix commit (the P0 incident fix touches only `scripts/billing/**`, the incident record and records) the frozen session commit, so P20 (the post-review sbt check) and P6 S on the frozen commit run tonight and the user can set the final private tfvars; P15 rebuild, the credit-balance read, the approval record and the go/no-go stay on Wednesday. Any later code change voids the freeze and repeats the frozen steps.

User answer, verbatim: "Yes"

## P15 moved to tonight (2026-11-16)

User request, verbatim: "The p15 parts on wednesday. Can you do it also tonight? Just ask"

Coordinator plan (no account ID needed): after the billing-bundle review, run A1.4 (`sbt packageEmr`, the upload script's dry run with a syntactically valid placeholder bucket and run prefix, first proving on two different placeholders that the printed `EMR-RENDER` hashes do not depend on them, then `render_manifests.py` and `check_manifests.py --final`), the A2 drift check (read-only; any drift goes to the user, who owns `reviewed-pins.json`), and A1.7 (full `scripts/check.sh`, `RESULT: PASS gates=7`, which is also P20), then commit: that commit is the frozen code commit. A12 (images, built on the final HEAD) stays after the P0 verification records are committed, because B0 requires HEAD to equal the A12 HEAD; any record commit after the images would require a rebuild.
