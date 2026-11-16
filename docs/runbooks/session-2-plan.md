# ScholarChain Session 2 live-session plan

**Status: DRAFT, not approved.** Drafted 2026-11-15 by the documentation-engineer for the human architect's review.

- Revision 1 (same day) added two EMR sizes and the class-wide reduced-scale guidance.
- Revision 2 (same day) added the instructor's reply to **ScholarChain's own** request (section 1b: reduced scales approved, budget raise declined) and a re-plan under a firm USD 25.
- Revision 3 (same day) adds:
  - your answers (section 9.1; this approves the plan document, **not** the Procedure R approval record);
  - a real-work elasticity load with load-driven scaling;
  - the optional R-c rerun;
  - the external-review items N1, N4, N5 and N9.
- Amendment of 2026-11-15 (work order P40-D, from your Phase 15 Work order 2 answers):
  - the S3 Vectors query cost of the R-b load (section 6.3a), with every affected total and gate recomputed;
  - the fixed question set (about 100-200 distinct questions) and the Voyage bound from cache misses;
  - 429s reported apart from successful responses;
  - the accepted P40 defaults;
  - decision A for the P0 live modify;
  - two new open questions (section 9.3), **answered the same day**: Q16 keeps the 15B per-level request limits as the required cost bound (the condition holds: project at caps 21.76; superseded 2026-11-16, see the P34 amendment below), and Q17 keeps R-b as designed and expects R-c to be dropped.
- Amendment of 2026-11-16 (work order P41-D, from your Phase 15 Work order 3 answer "Accept defaults" and the P40 review 1 findings R2 and R3):
  - row P41: the accepted defaults (second target-tracking policy for query-api, the three root variables, no cache-size variable, one dashboard panel, owners, schedule); the implementation is not yet reviewed;
  - section 5.3 step 2: the rate-limit override is expressed through the root variables `query_semantic_rate_limit_per_second` and `query_semantic_rate_limit_burst`, with the environment names kept in parentheses;
  - R3: section 6.3a now cites `SemanticApi.scala` line 100 (`vectors.query`) for the `QueryVectors` call; line 98 is the embed call;
  - R2: an open item in section 5.3 step 4 and rows P35 and P42: the `embedding_cache_*` counters cannot be read through the ALB in aws mode, so Session 2 needs another source for the Voyage-calls figure or reports it as unverified. Nothing was measured.
  - Follow-up the same day (your P41-D follow-up answers, 2026-11-16):
    - **R2 decided (answer (a))**: the Voyage usage page, read by you after the session with its read time; session-window total, not per task, compared with the fixed question-set size; "unverified" if the page does not separate the window. This replaces the either/or wording in section 5.3 step 4 and rows P35 and P42;
    - row P35 item (5) now names the root variables, with the environment names in parentheses (answer 2);
    - the provenance entry in section 10 is kept and extended (answer 3);
    - second follow-up (your answers 1(a) and 2(a), 2026-11-16): the R2 rule uses the R-b load window only and the section 6.3a caveats (up to about 4 × distinct questions from task starts, plus a few duplicate calls from a cold task) in place of the 2× note.
- Amended 2026-11-16 (P34 impossible; your decision 2026-11-16: "P34 as planned is impossible. Set min 1 / max 2.5 NCU."; phase 15 repairs E1 and E5):
  - AWS sets the smallest maximum capacity of Neptune Serverless at 2.5 NCU, so the 1-NCU cap (P34) cannot be set. Capacity stays **min 1 / max 2.5 NCU**, the Session 1 configuration. No Terraform change (none existed to revert). P34 is closed as not possible;
  - Neptune is now planned at the observed 0.297/h (about 1.85 NCU, P32) and capped at the 2.5-NCU ceiling, 2.5 x 0.1608 per NCU-hour = 0.402/h. Before this amendment the plan used 0.1608/h for both;
  - old values, for the record: R0 + R-b 3.50 / 5.93 (project 19.33 / 21.76; column B 21.45 / 24.10); R0 + R-b + R-c 4.57 / 8.19 (project 20.40 / 24.02; B 22.63 / 26.59); R-b worst case `E_b` 2.36; gate 1 threshold 3.06; gate 2 limit `X_spent <= 2.73` with planned `X_spent` 3.02 (margin -0.29); R-c cap 2.26 (planned 1.07); AWS-only alert totals 19.25 / 21.26 and 20.28 / 23.42. New values: sections 6.2-6.4 and the summary table below;
  - **R0 + R-b at caps (23.45) no longer fits floor 3 (22.00).** The 90,000-hold option (your decision 2(a)) fails its condition, so it is not applied. A decision was pending; it was taken the same day (next entry).
- Amended 2026-11-16 (option (i) decided; your R-b option decision, recorded verbatim in `docs/agent-runs/phase-15/prompt.md` and in section 6.4):
  - **floor 2** for the whole plan: `S` = 7.17, project total at most **23.00** (was floor 3, `S` = 6.17, at most 22.00);
  - the 150,000 hold and the per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 are kept;
  - **R-b's Neptune window is a hard stop at 5.8 h** (planned 5.0 h; was 7.0 h at cap), with clock times in sections 5.3, 5.5 and 6.7: R-b Neptune cap 5.8 x 0.402 = 2.33 (was 2.81); `E_b` 3.57 (was 4.05); R0 + R-b cap 7.14 (was 7.62); project at caps 22.97 (was 23.45);
  - gate 1 threshold 2.85 (was 1.37) and a new pre-R-b check (spend to date + 3.57 <= 25.00);
  - **R-c dropped** (the 5.8 h stop cannot hold R-c's Neptune window, and gate 2 fails anyway); its figures stay as a record. The R-c DynamoDB cache load is not run, so planned `X_a` is about 1.35 (was 1.57);
  - column B (x 1.11) was kept, pending your read of the tax settings (condition 1): its cap was 25.44, above the USD 25 limit. **Answered the same day** (your words: "the portion of your bill deducted/covered by AWS credits is not taxed. Since they are credits so tax is 0"): tax 0 on credit-covered spend, valid while credits cover the spend; column B dropped;
  - draft wording for the P19 approval record: section 4a.
  - follow-ups the same day: the Neptune clock was made conservative (destroy target `T_N0` + 5 h 15 min, absolute `T_N0` + 5 h 30 min; was 5 h 30 min and 5 h 48 min, with no new load start after 4 h 50 min), the pre-destroy steps were sized at about 50 min from Session 1 (section 5.5), giving a latest full-variant load start of 14:25 CST and a latest load start of 14:38 CST; a failed S retry then meant stop, report with logs and no R-b (a consequence of your P25 rule; superseded by your 4a review, next bullet).
  - **L dropped on EMR, D3 cluster and EMR actuals (your decisions 2026-11-16, recorded verbatim in `docs/agent-runs/phase-15/prompt.md` from "L, second size"):** both EMR runs go to S and its retry (P25 rule), and L is reported from local evidence only. Cluster: r5.xlarge primary (EC2 0.252 + EMR 0.063 = 0.315/h) and m5.xlarge core (0.240/h), 0.555/h; ER heap 12g; S run cap 75 min. Plan rate 0.50 → 0.58 per cluster-hour; EMR cap block 3.83 h = 1.92 → 3.33 h = 1.93; planned EMR 2.05 h = 1.03 → 0.96 h = 0.56. R0 1.64 / 3.57 → 1.17 / 3.58; R0 + R-b 4.18 / 7.14 → 3.71 / 7.15; project 20.01 / 22.97 → 19.54 / 22.98 (margin 0.02 to 23.00); AWS cap for the credit check 6.72 → 6.73; planned `X_a` 1.35 → 0.88. The EMR actuals are recorded after each S run, and gate 1 and the pre-R-b check use them (section 5.2).
  - your 4a review (2026-11-16, answers 1-5): item 5 already had the corrected clock; the AWS credit balance read must be at least the Session 2 AWS cap of 6.72 (sections 4a and 5.1); the pre-R-b check uses 23.00 (floor 2) instead of 25.00; if S fails twice, R-b runs on vectors from the local P6 S run (section 5.2 step 7b; replaces "stop, no R-b"); item 8 is kept for the Session 2 Voyage key.
  - **P35 local rehearsal result and your scaling-target decision (2026-11-16; user answer "T = 3,000 (Recommended)", recorded verbatim in `docs/agent-runs/phase-15/prompt.md`, "P35 scaling target after the local rehearsal"):** the results paragraph under section 4 (after the prerequisites table) records run p35-local-1 (completed, 198,750 requests, 0 errors, 0 x 429). `query_requests_per_target_target` = **3000**, a recorded deviation from the local rule (which gave 5,285 < T <= 13,517); `query_semantic_rate_limit_per_second` = **3500** and `query_semantic_rate_limit_burst` = **7000** (Q16 formula). Rows P35 and P41, sections 5.3 step 2, 6.3a, the checklist, the risk table and section 9.3 carry the values. All three are set by you in the private tfvars; none is set by this document.

Nothing in this file approves spending, an apply, a deployment or a cleanup, and nothing in it has been run against AWS, Anthropic or Voyage AI. Every live step still needs the human gates of the [Phase 14 runbook](phase-14-live-session.md): an approval record and pre-spend receipt (Procedure R) before each apply, and IAM windows recorded with their open and close times.

**Who this is for:** you, the human who types every live command. The coordinator routes the offline fixes to their owners. Reviewers check each fix before any live step.

**In one paragraph (approved plan, section 6):** Session 2 is **one day** that ends within 12 hours of the first apply. In priority order:

1. **Stage a (S3 + EMR, no Neptune or ECS).** EMR runs the real Hadoop → entity resolution → Spark chain at **S = 10,577** DBLP works (the approved smaller scale; the S retry is the second EMR run), recording step times, counters and EMR/YARN/EC2 utilization. **L (about 50,000) is dropped on EMR (P25 rule, 2026-11-16)** and is reported from local evidence (section 8). Then about **10,000 real voyage-4-lite vectors** are built from S's output, ingested, and checked with a live retrieval smoke.
2. **R-b (gate 1):** a small elasticity experiment on the production runtime.
   - Neptune runs at min 1 / max 2.5 NCU, the Session 1 configuration (a 1-NCU cap, P34, is not possible), and the graph is **empty**. **The Neptune window is a hard stop at 5.8 h** (option (i); clock in section 5.3); the load runs early in the window.
   - Before R-b: gate 1 (threshold 2.85) **and** the pre-R-b check (spend to date + R-b cap 3.57 <= 23.00).
   - The load is **semantic retrieval**, real work against S3 Vectors, through a new API-key route with a query-embedding cache (P40, P42).
   - Scaling is **ALB request count per target**, kept alongside CPU (P41).
   - Includes one stop-a-task failure-and-recovery example.
3. **R-c: dropped (option (i), 2026-11-16).** The 5.8 h Neptune hard stop cannot hold R-c's Neptune window (about 7.5 h), and gate 2 fails anyway. The report uses the Session 1 results plus the offline P3 and P4 proofs. Former text, kept as a record: **R-c (optional, gate 2 at most 22.00 project total):** load the 10.5k graph (DynamoDB caches are loaded during stage a) and rerun only the 14 direct-coauthor and 10 path questions after P3, P4 and N1 pass. This is dropped if its gate fails. **Since the 2026-11-15 amendment it fails gate 2 on planned figures** (planned `X_spent` about 3.47 against 2.36 since the 2026-11-16 Neptune correction, because of the S3 Vectors query cost of R-b and the real Neptune rate; 3.02 against 2.73 before it). **Your Q17 answer (2026-11-15): keep R-b as designed and expect R-c to be dropped; the report states why.**

**Budget (section 6; firm USD 25; `C11_TOTAL_USD` = 15.83 provisional, tax 0 per the Bills page; tax 0 on credit-covered spend (your decision 2026-11-16; the x 1.11 column B was dropped); **floor 2 since 2026-11-16 (option (i)), so the project total must stay at or below 23.00**; floor 3 and 22.00 before):**

| Plan | Planned (A) | Cap (A) | Project total A, planned / cap |
|---|---:|---:|---|
| R0 | 1.17 | 3.58 | 17.00 / 19.41 |
| R0 + R-b | **3.71** | **7.15** | **19.54 / 22.98** (fits floor 2 even at caps, margin 0.02; Neptune hard stop 5.8 h; S only on EMR, D3 cluster) |
| R0 + R-b + R-c | 5.59 | 10.25 | 21.42 / 26.08 (**dropped**, option (i); record only, computed with the former 7.0 h R-b Neptune cap; gate 2 `X_spent <= 2.36` against planned 3.47 failed) |

Amended 2026-11-15: R-b now carries the S3 Vectors query cost of its load (section 6.3a): 0.53 planned and 0.53 cap, bounded by the required per-level request limits (198,600 queries), plus 0.02 for Voyage cache misses in the cap. This replaces the earlier allowance of 0.10 / 0.30. Under the 1.11 check, R-c does not fit and R-b fits only on planned figures.

Amended 2026-11-16 (P34 impossible): Neptune is planned at 0.297/h and capped at 0.402/h (min 1 / max 2.5 NCU) instead of 0.1608/h, which adds 0.68 planned and 1.69 at cap to R-b. Previous summary values: R0 + R-b 3.50 / 5.93, project 19.33 / 21.76; R0 + R-b + R-c 4.57 / 8.19, project 20.40 / 24.02, gate 2 `X_spent <= 2.73` against planned 3.02. Under the 1.11 check, R-b now does not fit even on planned figures (column B 22.20 / 25.97).

Amended 2026-11-16 (option (i)): floor 2 (project at most 23.00) and a 5.8 h Neptune hard stop for R-b (cap 7.62 → 7.14, project 23.45 → 22.97); R-c dropped. Column B: 22.20 / 25.44, which fits floor 2 on planned figures but is above the USD 25 limit at caps; it stayed pending your read of the tax settings until your tax decision the same day, which dropped column B.

Amended 2026-11-16 (L dropped on EMR; D3 cluster r5.xlarge primary at 0.58 per cluster-hour; S run cap 75 min): R0 1.64 / 3.57 → 1.17 / 3.58 (project 17.47 / 19.40 → 17.00 / 19.41); R0 + R-b 4.18 / 7.14 → 3.71 / 7.15 (project 20.01 / 22.97 → 19.54 / 22.98).

---

## 1. Purpose and scope

- **Priority order** (from the instructor's guidance, section 1b):
  1. Strongest evidence of correctness and scalability: EMR at two approved scales with times, counters and utilization. **Since 2026-11-16: S on EMR only (L dropped on EMR, P25 rule); L is shown from measured local evidence, with the ER bypass disclosed (section 8).**
  2. About 10,000 real vectors with ingestion and retrieval shown.
  3. A small, carefully designed elasticity experiment with scale-out and scale-in.
- Close what Session 1 left open: B9 EMR PARTIAL, 15B elasticity dropped, the failure-and-recovery example, and the live demonstration items (the Session 1 video ran only 63 s). These are closed as far as a firm USD 25 allows.
- Document everything not evaluated because of resource limits (the instructor's request): live API answers, the Neptune load, and the coauthor and path reruns in Session 2.
- Keep the Session 1 procedures:
  - Procedure R before every apply.
  - IAM window 1 at deploy and IAM window 2 at cleanup.
  - New provider keys that go only into Secrets Manager, are deleted at cleanup and revoked afterwards.
  - The commit freeze.
  - The two-pass destroy.
  - The next-day cost check (C11).
- Out of scope: any change to code, Terraform, scripts, datasets, manifests or tests. Those changes are prerequisites with named owners (section 4).

## 1a. Human-supplied record: instructor reply to another student's reduced-scale request, posted in the class channel (2026-11-12); class-wide guidance only, not an approval for ScholarChain

The instructor posted this reply in the class channel in answer to **another student's** request. The human keeps the original; it is not in the repository and the student is not named. In summary, a justified reduction must document:

- the original requirements, actual sizes and reasons for each reduction;
- costs, execution times and limitations;
- measurements at several sizes where possible;
- a separation of fixture-data functionality from real-data validation.

Other points from that reply:

- A smaller vector set does not excuse missing ingestion and retrieval.
- The USD 25 limit stays in effect.
- Approval of a reduced scale does not guarantee full credit.

## 1b. Human-supplied record: instructor reply to ScholarChain's own request (received 2026-11-15)

The human pasted this reply into the coordinator chat. **The human keeps the original; there is no copy in the repository.** Summary, not a quotation:

- **Approved for ScholarChain:**
  - **The integrated run on real DBLP at about 10.5k and about 50k works** instead of 100k. Document execution times, resource utilization and the performance differences between the two scales; two scales are valued as scalability evidence.
  - **S3 Vectors up to 10,000 real voyage-4-lite vectors.** Report the actual count and demonstrate ingestion and retrieval.
  - **ER gold set:** 200 reviewed with 194 definitive is close to the requirement. Resolve the 6 uncertain pairs if practical; otherwise document the ambiguity and explain how the AI-assisted reviews were independently validated.
- **Declined:** the budget raise. **The USD 25 limit stays.**
- **Guidance:**
  - Prioritize experiments that give the strongest evidence of correctness, scalability and elasticity within budget.
  - A smaller, carefully designed elasticity experiment is acceptable if its setup, results and limitations are explained.
  - Document all costs, sizes and results, and anything not evaluated because of resource limits.
  - Grading weighs technical quality, evidence and rigor, not dataset size or spend.

The original course minimums (course README "Minimum acceptance criteria", read 2026-11-15T16:51:58Z) are:

- at least 100,000 DBLP works in the integrated run (**approved reduction**: about 10.5k and about 50k);
- at least 1,000,000 graph edges in the scale experiment, subject to budget;
- at least 10,000 text chunks in S3 Vectors (**approved**: up to 10,000, actual count reported);
- at least 200 manually reviewed entity-match examples (**close**; see 1b);
- at least 30 benchmark questions;
- at least four concurrency levels;
- at least one scale-out and one scale-in event.

## 2. Sources used (with read dates)

| Source | What it gave | Read |
|---|---|---|
| [Phase 14 runbook](phase-14-live-session.md) | Stages, Procedure R, receipts, IAM roles and session lengths, cleanup two-pass, cost model, failure playbook | 2026-11-15, full |
| `target/phase14/evidence/14b/b8-3-graph-only-decision.md` (git-ignored) | Session 1 timeline, decisions, durations, failures | 2026-11-15, full |
| [Approval request, section 3](../agent-runs/phase-14/approval-request-14b-replan.md) | Hourly rates (infra survey 2026-11-08), session totals, tax assumption | 2026-11-15 |
| Session 1 evidence under `target/phase14/evidence/` (file times, `RESULT:` lines, `session-clock.log`, ledger status, `14c/ingest-report*.json`, `14c/query-report.json`, `14c/render-report.json`) and the committed excerpt `docs/agent-runs/phase-14/evidence/14b/session-1/14c-load/14c-results.txt` | Stage durations (CST = UTC-6), vector counts, retrieval smoke | 2026-11-15 |
| [Terraform root](../../infra/terraform/main.tf), [phase12b.tf](../../infra/terraform/phase12b.tf), modules `network`, `runtime`, `observability`, `emr`, `neptune` | Feasibility (section 3) | 2026-11-15 |
| [deploy.sh](../../scripts/deploy.sh), [plan.sh](../../scripts/plan.sh), [cleanup.sh](../../scripts/cleanup.sh), [release.conf](../../scripts/config/release.conf), [emr-pricing.conf](../../scripts/config/emr-pricing.conf), [pipeline.py](../../scripts/lib/pipeline.py), [sc-step.sh](../../scripts/emr/sc-step.sh) | Stage behaviour, ceilings, ledger caps, EMR rates, step chain | 2026-11-15 |
| [15A manifests](../../experiments/manifests/15a-emr-size-100.json), `experiments/scripts/make_dblp_subsets.py`, `experiments/inputs/15a/prep-config.json`, `target/experiment-inputs/15a/*.subset.json`, [DBLP slice manifest](../../datasets/phase6/dblp-slice-manifest.v1.json), `modules/hadoop/.../HadoopIO.scala` (`SampleBound`) | How dataset size is chosen and bounded | 2026-11-15 |
| Phase 6 local run evidence `docs/agent-runs/phase-06/evidence/6fg/` (`hadoop-run.txt`, `er-run.txt`, `commands.md`, `real-slice-export.md`) and local output sizes under `target/phase6-runs/` | Local execution times, counters, output sizes at 10,577 works | 2026-11-15 |
| [ER gold labels](../../datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/README.md), `docs/agent-runs/phase-05/evidence/5e/` (`evaluation-report.md`, `disabled-a-held-out*/evaluation.json`, `sampling-strata-summary.json`) | Gold-set size, selection, balance, metrics | 2026-11-15 |
| [15B manifest](../../experiments/manifests/15b-ecs-scaling.json), [load profile](../../load-tests/config/load-profile.v1.json) | Load generator, scaling settings, Anthropic rate | 2026-11-15 |
| Phase 15, 16 and 17 plans (the human's planning folder, outside the repository): design and checklist sections | Experiment, evaluation and demo requirements | 2026-11-15 |
| Course README, https://raw.githubusercontent.com/0x1DOCD00D/ScholarChain/main/README.md | Minimum acceptance criteria, demonstration requirements (22 items), metrics, deductions | 2026-11-15T16:51:58Z |
| AWS pricing pages https://aws.amazon.com/emr/pricing/, /neptune/pricing/, /cloudwatch/pricing/, /fargate/pricing/, /vpc/pricing/, /elasticloadbalancing/pricing/, /s3/pricing/, /dynamodb/pricing/ | Billing rules: EMR billed per second with a one-minute minimum; Neptune Serverless NCUs billed per second; a partial NAT gateway hour or ALB hour bills as a full hour; CloudWatch free tier of 3 dashboards of up to 50 metrics each per month. **The numeric rates on these pages are filled in by JavaScript and were not readable by a plain fetch.** The rates below come from the repository survey and Session 1; confirm them in a browser. | 2026-11-15T16:53Z |
| S3 Vectors section of the public AWS S3 pricing page (https://aws.amazon.com/s3/pricing/), **read by the coordinator** and passed on in work order P40-D; not re-read by the documentation-engineer | Query API requests USD 2.50 per million; query data processed USD 0.004 per TB for the first 100K vectors in the index (0.002 per TB from 100K to 10M); data processed per query = average vector size (vector data, key and filterable metadata; non-filterable metadata excluded) x the number of vectors in the queried index. **The page shows US East (N. Virginia) figures; US East (Ohio), our region, is not listed.** Used in section 6.3a. | 2026-11-15 |
| https://aws.amazon.com/route53/pricing/, https://aws.amazon.com/cloud-map/pricing/ | Hosted zone USD 0.50 per month, not prorated; a hosted zone deleted within 12 hours of creation is not charged; the Cloud Map DNS namespace uses the same hosted-zone price | 2026-11-15T17:03:36Z |
| Instructor reply to another student, class channel (section 1a, human-supplied) | Class-wide guidance on documenting reductions; not an approval for ScholarChain | dated 2026-11-12, received 2026-11-15 |
| Instructor reply to ScholarChain's own request (section 1b, human-supplied) | Approved scales; budget raise declined; priorities | received 2026-11-15 |
| Human-supplied billing: Cost Explorer Nov 1-15 by service (before tax, credits excluded) and the Bills page (tax 0, net 0 after credits) | Empirical rates (6.1) | 2026-11-15, provisional |
| Amazon Neptune User Guide, "Capacity scaling in a Neptune Serverless DB cluster", **read by the infra-engineer** (recorded in `docs/agent-runs/phase-15/repairs.md` E1 and `infra/terraform/README.md`, "Neptune capacity (P34, not changed)"); not re-read by the documentation-engineer | The smallest value for the maximum capacity is 2.5 NCU; the lowest minimum is 1.0 NCU. P34 (max 1 NCU) is therefore not possible (sections 4 and 6.1a) | 2026-11-16 |

Anthropic and Voyage AI pricing pages were **not** fetched; they were not on the allowed list. Their figures come from repository records (section 6.1).

---

## 3. Feasibility check (verified against the code; nothing run)

Each row gives the finding, its evidence and the verdict. Every gap becomes a prerequisite row (P-number) in section 4.

| # | Question | Evidence (path) | Verdict |
|---|---|---|---|
| F1 | Can stage a (S3 + EMR, no Neptune, no ECS services, no ALB) be expressed with the existing flags? | `neptune_enabled` gates every Neptune resource (`modules/neptune/main.tf`, `count = local.active`). ECS services, task definitions, ALB, listener and autoscaling exist only with `runtime_enabled` and `image_revision` set (`modules/runtime/compute.tf`). `emr_config.enabled` gates `module.emr`. `course.tfvars` defaults `neptune_enabled = false`. | **Yes, by flags.** Not yet proven by a plan with exactly this variable set → **P7** |
| F2 | What does EMR need, and is it there without Neptune or the runtime? | The NAT gateway, EIP, application-subnet default route, S3 and DynamoDB gateway endpoints and EMR security groups are unconditional (`modules/network/main.tf`). KMS and the EMR roles are in `module.identity`; EFS staging is in `module.emr`. No interface endpoints by default. | **Yes.** The NAT gateway bills in stage a (about USD 0.05/h). |
| F3 | Which `deploy.sh` stage applies the EMR-enabling plan in stage a? | `runtime-apply` requires a push record (`deploy.sh` line 761) and fails at `record-ecs` unless all four ECS services exist (line 1073). `base-apply` applies the approved plan, checks only that the runtime is not partially live, and has `--skip-runtime-archive`. | **Gap.** Stage a needs two applies: the bucket and the uploads must exist before the cluster bootstraps. The second would be `--stage base-apply --skip-runtime-archive` with an EMR-only plan, a use nobody has reviewed → **P7** |
| F4 | Does the R-b base plan remove the stage-a EMR resources? | After a cluster terminated, Session 1 re-plans proposed creating a new cluster each time (EMR plans 3-5). | **Gap.** The R-b base plan must set `emr_config.enabled = false`. Its base plan therefore **deletes** the `module.emr` leftovers, which the expected-delta lists do not yet cover → **P7** |
| F5 | Is there a CloudWatch dashboard resource? | `aws_cloudwatch_dashboard.elasticity`, `count = var.dashboard_enabled ? 1 : 0` (`modules/observability/main.tf` lines 23-25). Session 1 set it false. The Session 1 destroy listing has 9 observability deletes (5 log groups, 4 alarms) and **no dashboard**. | **Confirmed: the resource exists but was never created.** Its task panels read Container Insights metrics, which do not exist while Container Insights is off. It references well over 50 metrics → **P9** |
| F6 | Is there an elasticity load generator? | `load-tests/loadgen.py` with `15b-ecs-scaling.json`: levels 1/5/25/50, a 10-minute hold, 30 minutes of no load. No route calls Voyage. | **Exists, never run live** → **P13** |
| F7 | ECS autoscaling and scale-in | `aws_appautoscaling_policy.http_cpu` (query-api, graph-service, semantic-service): CPU target 60%, scale-out cooldown 60 s, scale-in cooldown 300 s; HTTP services max 2 tasks. | **Exists.** Scale-in takes about 15 low minutes plus the cooldown (per the 15B manifest note; not re-confirmed against AWS documentation here). Whether the load reaches 60% CPU is **unverified**. |
| F8 | Stage-a output → loader input shape | The loaders read a **local** Spark export directory with `load-manifests/` and the `neptune-opencypher-csv/` sidecar. EMR `spark-job` runs the same `Phase6Main` into `${RUN_ROOT}/spark`. `copy-out` sends `hadoop, er, spark, results, config` to `s3://<artifacts>/pipeline/<run-prefix>/15a/size-<P>/<run-id>/`. | **Plausible, unproven** → **P6** |
| F9 | Researcher-ID continuity for questions and include-ids | The 14C/16B inputs came from export `run:f6e63b4b…`, built with the **ER-disabled** run. The EMR chain runs `Phase5Main resolve`. Size S is byte-identical to the Phase 6 slice. | **Gap** → **P10** |
| F10 | voyage-4-lite at 256 dimensions | `phase14b-providers.tf` line 27; `phase12b.tf` precondition `vector_dimension == 256`; `VoyageEmbedding.scala` sends `output_dimension`. | **Confirmed.** No gap. |
| F11 | Cleanup rules and leftover state | `CLEANUP_TEARDOWN_ADDRESS_RULES` (`release.conf` line 190) has no `terraform_data.*` rule (Session 1 listing refused `phase12b_guard`). The after-inventory still lists `terraform_data.configuration_guard` and `terraform_data.provider_guard`. | **Gap** → **P5**, **P18** |
| F12 | LLM ledger | At cleanup: 55 answers used; buckets 14c 10/10, 15b 0/60, 16b 40/40, 17 5/5. | 60 answers left, all in bucket 15b → **P12** |
| F13 | Failure-and-recovery example | No experiment-F manifest. The operator loader role may `ecs:StopTask` only on tunnel tasks (`deployer/operator_roles.tf` lines 175-179). | **Gap** → **P11** |
| F14 | Live-demo read access | The reader role has `neptune-db:ReadDataViaQuery`, DynamoDB reads and `s3vectors:QueryVectors` (`operator_roles.tf` lines 205-230). | Available once the operator roles are recreated (A4) |
| **F15** | **How is the dataset size chosen, and what real DBLP exists?** | Each 15A manifest points to an input tree `target/experiment-inputs/15a/size-<P>/`, built by `make_dblp_subsets.py`: the first `ceil(n_venue x P / 100)` records per venue of the Phase 6 slice, nested. The Phase 6 slice (`datasets/phase6/dblp-slice-manifest.v1.json`) is **10,577 inproceedings**: 8 systems venues, 2005-2026, at most 2,500 per venue, selected from 3,980,085 inproceedings in `dblp-2026-10-03` (6.0 MB XML). Sizes 25/50/100 are 2,645 / 5,289 / 10,577 works. The 1.1 GB archive is **not** kept locally (the default archive path no longer holds it). | **Gap for any size above 10,577.** L needs a new, larger slice, which means re-downloading the pinned archive and changing the venue or per-venue rule → **P21** |
| **F16** | **Hadoop record ceiling** | `prep-config.json` sets `maxLocalSampleRecords: 12000`, and the pinned ceiling is `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS=12000` (`release.conf` line 308). `SampleBound` (`HadoopIO.scala` lines 279-305) applies it as one budget across all inputs. Records past it are **rejected** as `OversizeRecord` / `maxLocalSampleRecords`. The bound is installed for every job, whatever the execution mode. | **Blocking for L:** at 50,000 works about 38,000 records would be rejected. S (10,577 + small samples) fits → **P22** |
| **F17** | **Copy-out ceiling** | `PIPELINE_MAX_COPYOUT_BYTES=268435456` (256 MiB, `release.conf` line 301); `body_copy_out` refuses when the sum of `hadoop, er, spark, results, config` is larger (`sc-step.sh` lines 333-355). The local outputs at 10,577 works are much larger: Hadoop 1.0 GB (613 MB of it intermediate), ER 757 MB, Spark export 579 MB (446 MB of it Neptune CSV). | **Blocking even for S**, unless EMR output is far smaller than local output (unknown). At L the outputs would be roughly 5 times larger → **P23** |
| **F18** | **Spark configuration for L** | The EMR Spark template (`docs/agent-runs/phase-06/evidence/6fg/local-spark-first-config.json`) sets `shufflePartitions: 4`. The first Session 1 export at 4 partitions had sidecar CSV parts of 43-124 MB, above the loader cap; the accepted export used 64 partitions. The template is phase evidence and must not be edited; its sha256 is pinned in the 15A manifests. | **Gap.** S needs the 64-partition settings if its output is loaded. L needs a size-appropriate template → **P24** |
| **F19** | **EMR run ledger and caps** | `EMR_MAX_LIVE_RUNS=3`, `EMR_CUMULATIVE_CAP_USD=2.52`, `EMR_MAX_RUN_USD=3` (`release.conf` lines 227-229). The ledger holds 2 live runs and USD 1.68 of estimate. As found (before D3), each run was estimated at 0.84 = 2 x 0.24 x 1.75 h (90 min plus the 15-minute idle); since D3 an S run is capped at 75 min and reserves 0.84 = 0.555/h x (75 + 15) min. `PIPELINE_MAX_RUNTIME_MINUTES=180` and `PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=900`. | **Two runs are refused today**: run 4 exceeds 3 live runs, and 1.68 + 2 x 0.84 = 3.36 exceeds 2.52 → **P25** (your decision) |
| **F20** | **Back-to-back runs on one cluster** | The cluster auto-terminates 15 minutes after its last step. Each run needs its own single-use approval record naming the cluster ID (runbook B9.5); records can be pre-written while the previous run executes. | **Feasible** if run L is submitted within 15 minutes of run S ending. Otherwise runbook E9 applies (a new cluster: another apply and cold start). |
| **F21** | **Vector count** | Session 1: `render-report.json` scanned 100,769 rows (100,765 semantic summaries plus 4 topic and institution nodes) and selected **104** documents. The cause was `maxSummaries: 100` in the private render config (25 per document type) plus 4 nodes. The ingest wrote 104 vectors in total over two runs (ingest-2 alone: 95 written, 9 unchanged, 0 rejected; throughput 0.614 vectors/s). Five indexes: community 25, path 25, paper 25, researcher profile 25, topic/institution 4. `maxManifestItems` is 10,000 in the 14C template. | **Gap on count** against the course's 10,000 and the class-wide guidance: the subset has about 100k meaningful units, so 104 is a selection cap, not a shortage. Raising it to about 10,000 is a config change, but at Session 1 throughput 10,000 vectors take about 4.5 h → **P26** |
| **F22** | **Option (a): can the ECS services and ALB run with `neptune_enabled = false`?** | (1) Terraform: the `phase12b.tf` precondition requires `var.neptune_enabled` whenever `runtime_enabled` is set, and the runtime module always passes `SCHOLARCHAIN_NEPTUNE_ENDPOINT = var.neptune_endpoint` (`modules/runtime/compute.tf` line 51). (2) Services: `AwsConfig.scala` requires `SCHOLARCHAIN_NEPTUNE_ENDPOINT` as an https URI with an explicit port (lines 47, 261). graph-service readiness runs a Neptune `node` probe. query-api `/readyz` includes graph-service's and semantic-service's `/readyz` (`modules/services/README.md`, readiness table). (3) The ALB target-group health check path is `/readyz` (`compute.tf` line 218). | **Not possible without code changes.** It would need a reviewed "graph disabled" mode in services (optional endpoint; graph-service ready without Neptune; query-api readiness without graph-service) plus Terraform changes (precondition, null endpoint, possibly a health path). Owners: `service-engineer`, `infra-engineer`, `test-engineer` (**P33**). It would also make the elasticity run a non-production configuration. |
| **F23** | **Option (b): how is Neptune capacity set, and why did it cost 0.297/h?** | Serverless v2: `min_capacity = var.neptune_min_ncu` (1), `max_capacity = var.neptune_max_ncu` (2.5), one `db.serverless` writer, audit logs exported (`modules/neptune/main.tf` lines 26-62). The `phase12b.tf` precondition pins max to **exactly 2.5** and min to at least 1. The Nov 14 bill is 7.12 for 24 h = 0.297/h, against 0.1608 per NCU-hour (1 NCU). | **Resolved by P32 (2026-11-15):** the whole Neptune bill (9.05) was `ServerlessUsage`, with backup, storage and I/O all 0. The average was about 1.8 NCU (about 1.35 on Nov 13 with an empty graph, about 1.85 on Nov 14), and capacity never returned to 1. **The planned fix, P34 (`neptune_max_ncu = 1`), is not possible (2026-11-16):** AWS sets the smallest maximum capacity at 2.5 NCU (section 2). Capacity stays min 1 / max 2.5 NCU (your decision 2026-11-16), so the Neptune ceiling is 2.5 x 0.1608 per NCU-hour = **0.402/h**, and the plan uses the observed 0.297/h as its planning rate (sections 6.1a and 6.3). |
| **F24** | **Can the load generator drive CPU without Neptune data?** | `loadgen.py` drops graph and evidence routes when no node-ID or evidence-ID file is given (runbook B10.1, `ROUTE-DROPPED`). The remaining routes are `/healthz` (no auth), `/readyz` (no auth; fans out to graph-service and semantic-service and their Neptune and S3 Vectors probes) and `/metrics` (auth). `/v1/query` is used only with `--llm`. | **Yes, with no code change.** Whether this mix pushes a 0.25 vCPU task over the 60% CPU target is **unverified**. Rehearse locally with a 0.25-vCPU container limit (**P35**); if it does not, lower `cpu_target_percent` in the private tfvars (allowed 10-80) as a recorded experiment parameter. |
| **F25** | **A load target that does real work without the graph: semantic retrieval** | `POST /internal/v1/semantic/retrieve` is served by semantic-service (`SemanticApi.fromPorts`: embeds the question, then `vectors.query(index, …)` on S3 Vectors) and proxied by query-api (`RemoteSemanticApi`, `RemoteServices.scala` line 201; `ApiApplication.scala` line 215). Paths under `/internal/` require the **internal token**, not the API key (`ApiApplication.scala` lines 129-131). The raw internal token exists only in Secrets Manager (runbook A7 deletes the local copy, and `get-secret-value` is forbidden). The route never touches graph-service or Neptune. **Each request calls Voyage once to embed the question**; `rag` and `services` have no embedding cache. The ALB has one HTTPS listener and no path rules, so every path reaches query-api. | **Not usable as is.** It needs: (1) a public, API-key-authenticated route on query-api, for example `POST /v1/semantic/retrieve`, with the same `SemanticApiConfig` limits and no query text in logs (`service-engineer`, plus OpenAPI); (2) a bounded query-embedding cache keyed by (model, text) in semantic-service, so a fixed question set calls Voyage once per distinct question; this avoids Voyage rate limits (Session 1: the free trial allowed about 3 requests per minute; the paid tier limits are unverified) (`rag-engineer` for the decorator, `service-engineer` for wiring and config); (3) a `semantic` route in the load generator with a fixed questions file and a manifest variant (`experiment-engineer`) → **P40**, **P42** |
| **F26** | **Load-driven scaling: ALB request count per target** | `aws_appautoscaling_policy.http_cpu` covers query-api, graph-service and semantic-service on `ECSServiceAverageCPUUtilization` (`modules/runtime/compute.tf` lines 303-315). There is no request-count policy. `aws_lb.query` and `aws_lb_target_group.query` exist when the runtime is deployed, so the `resource_label` `"<alb arn_suffix>/<target group arn_suffix>"` can be built. The deployer already allows `application-autoscaling:PutScalingPolicy` and `cloudwatch:PutMetricAlarm` on `alarm:TargetTracking-*` (`deployer/phase14_main.tf` lines 452-462 and 578-588), which are the alarms target tracking creates. Tests pin `cpu_target = 60` (`tests/phase14b*.tftest.hcl`). | **Feasible with Terraform only** (no deployer change): a second target-tracking policy for query-api with `ALBRequestCountPerTarget`, a validated variable for the target, a dashboard panel, and a `terraform test` run. When both policies exist, scale-out happens if either asks for it and scale-in only when both allow it (AWS target-tracking behaviour; not re-read here) → **P41** |

**Conclusion on stage a** (superseded 2026-11-16: L is dropped on EMR, and both EMR runs go to S and its retry)**:** two sizes on one cluster are feasible in principle. They are blocked today by F15 (no real slice above 10,577 works locally), F16 (Hadoop ceiling 12,000), F17 (copy-out 256 MiB), F18 (Spark partitions) and F19 (ledger). Even S alone is blocked by F17 unless EMR output turns out small. F3, F4 and the EFS bootstrap race (P7) apply as before.

**Conclusion on elasticity:**

- Option (b), Neptune at min 1 / max 2.5 NCU with an empty graph, uses the production runtime path that Session 1 proved live in its 14B smoke. It needs no service code change, only P35 (rehearsal), P9 (dashboard) and P11 (stop-task permission). The optional 1-NCU cap (P34) proved not possible on 2026-11-16.
- Option (a), Neptune-free, needs new service and Terraform code paths days before the freeze (P33). Not recommended.

---

## 3a. Course requirements and the approved scales, checked against the repository (read-only)

The ER gold set is judged against the **course specification** ("at least 200 manually reviewed entity-match examples in the evaluation gold set") and the instructor's reply to our request (section 1b). The integrated-run sizes (about 10.5k and about 50k) and the vector count (up to 10,000) are **approved for ScholarChain** (section 1b); what remains is to document them.

| Condition | What the repository shows | Verdict | Gap owner (prerequisite) |
|---|---|---|---|
| **ER count (course: at least 200)** | Gold labels in `datasets/entity-resolution/labels/2026-10-20-danny-ai-assisted-v1/` (`validated-labels.json`, sha256 `5fbf6f5b…`): **240 reviewed** (40 development, 200 held-out). The held-out evaluation set has **194 binary + 6 uncertain**; development has 38 binary + 2 uncertain. 83 same, 149 different, 8 uncertain overall; 60 reserves untouched. Without the 22 externally assisted Researcher cases: 181 held-out binary. | **Close to the requirement** (instructor, section 1b): 200 held-out reviewed (240 in total), 194 definitive. Resolve the 6 uncertain pairs if practical (**P30**); otherwise document the ambiguity. Explain how the AI-assisted reviews were validated (**P31**). | human (labels), dataset-engineer, entity-resolution-engineer (P30); experiment-engineer, documentation-engineer (P31) |
| ER selection explained | The dataset README and the 5E report describe it: a frozen review queue from the candidate population, sampling strata (`missing-authoritative-id`, `observed-id-disagreement`, `shared-observed-id`), held-out split by whole components, a convenience sample with unweighted strata, AI-assisted human review (not blind), self-attested reviewer | **Partly met**; needs one consolidated, plain-language report paragraph | documentation-engineer (Phase 17A report, P28) |
| ER meaningful positives and negatives | Held-out: **72 same / 122 different / 6 uncertain** (Work 26/73/1, Researcher 46/49/5). Development 11/27/2. Outcomes on held-out (primary): TP 57, FP 0, FN 15, TN 122. 55 of the 57 accepts are exact-identifier matches. Error examples: `representative-errors.json` has all 4 development FN and 10 of 15 held-out FN. FP: none observed. | **Met for balance.** Note that most true positives are easy exact-ID cases. The course's "10 false positives" cannot be shown because none were observed. | documentation-engineer (report) |
| ER reliability discussion | The 5E report's limits paragraph names the convenience sample, AI-assisted labels and the absence of calibration. It gives **no confidence intervals or sample-size analysis**. Computed for this draft from the recorded counts (Wilson 95%, to be reproduced by the owner's script): held-out recall 57/72 = 0.792, interval [0.684, 0.870]; precision 57/57 = 1.000, interval [0.937, 1.000]; without assisted pairs recall 51/59 = 0.864, interval [0.755, 0.930]. | **Gap** | experiment-engineer (Phase 16A ER metrics script under `experiments/**`), with entity-resolution-engineer review (**P27**) |
| **Vectors count (course: at least 10,000; guidance: fewer only if fewer meaningful units)** | 104 vectors (F21), selected by a cap, from about 100k units | **Gap on count** (target about 10,000; approved: up to 10,000, report the actual count) | rag-engineer (throughput, limits), human (render config), **P26** |
| Vectors: how generated | `ingest-report-2.json` and `render-report.json`: Voyage `voyage-4-lite`, 256 dimensions, template version `phase14c-v1`, text prefix `embedding-text`, chunks of at most 1,000 characters with 100 overlap. Text source: the Spark `semantic-summaries` table (deterministic summaries per researcher, paper, community and path, by time window) plus topic and institution nodes of the real export. | **Met** (documented in evidence; needs the report paragraph) | documentation-engineer (P28) |
| Vectors: ingestion and retrieval work | Session 1 ingest: `rejected 0`, `conflicts 0` (ingest-2). Live query smoke (`query-report.json`): 5 of 5 samples, one per index; all expected neighbours matched; 7 verified source pointers; per-index p50 about 132-187 ms. | **Met** for Session 1; must be repeated at the Session 2 count (B8.7) | stage a (live, R0) |
| **Integrated run on real data (course: at least 100,000 works)** | Session 1 ran Hadoop, ER and Spark **locally** on the real 10,577-work slice and loaded the AWS stores and the API from it (Neptune `LOAD_COMPLETED`, 78,104 nodes, 328,967 edges). Session 2 S runs the same slice **on EMR** and loads it. | **Met at 10,577 works**; the reduction to about 10.5k and about 50k is **approved** (section 1b) | — |
| Integrated run: reduction approved; execution times, utilization and performance differences documented | **Approved** (section 1b). Still needed: stage-a step times, EMR/YARN/EC2 utilization and Spark and Hadoop counters at S and L, compared. **Since 2026-11-16: S on EMR; L from local P6 evidence only (L dropped on EMR)** | **Gap until stage a** | experiment-engineer (measurements), documentation-engineer (report) |
| Integrated run: fixture versus real data separated | Fixture paths exist (offline-synthetic service mode, `scripts/smoke-local.sh`, deterministic-fake ER adjudicator, small committed OpenAlex, Crossref and ORCID samples that are not scaled). No report section separates them yet. | **Gap** | documentation-engineer (Phase 17A report, P28) |
| Multiple dataset sizes | Session 2 stage a: S on EMR (L dropped on EMR 2026-11-16; L local evidence: Hadoop, and Spark with ER bypassed, section 8). Was: S and L on EMR. The offline 15A trees (25/50/100% = 2,645 / 5,289 / 10,577) exist for local runs. | **Planned** | experiment-engineer |
| 30 benchmark questions covering the course topics | 40 questions asked in 16B, in four kinds only (8 component, 8 ranking, 14 direct coauthors, 10 path) | **Coverage gap** (no team size, communities, bridges, temporal, topics or institutions) | experiment-engineer (Phase 16 benchmark); not added to this session's scope (open question Q12) |

---

## 4. Prerequisites (offline; each proven locally and reviewed before any live step)

Owners are taken from [docs/agents.md](../agents.md). "Reviewer gate" means an independent read-only `code-reviewer` verdict that the orchestrator routes, followed by the human's own review. "Commit" means one commit per owner after APPROVE and the human's explicit yes. No commit is allowed after the stage-a base plan (commit freeze). P1-P20 are unchanged from the first draft except where marked; P21-P28 are new.

| ID | What | Owner(s) | Local proof (observed, not claimed) | Reviewer gate | Commit |
|---|---|---|---|---|---|
| P1 | EMR Hadoop config upload: change manifest `hadoop_config` to an `s3://${SCHOLARCHAIN_ARTIFACTS_BUCKET}/emr/${SCHOLARCHAIN_RUN_PREFIX}/config/…` URI with its sha256, and add an option to `upload-emr-artifacts.sh` (for example `--hadoop-config FILE`) | `experiment-engineer` (manifests, check and render scripts); `infra-engineer` (upload script, `scripts/tests/`); `test-engineer` (`tests/scripts/`) | Upload dry run prints the key and sha256; `check_manifests.py --final` returns `RESULT: OK`; fake-node `localize` succeeds | `code-reviewer` | separate commits |
| P2 | Real-CLI-shaped fakes: review of 7ecc572, b6dc94d and 2b2d263, plus an audit of every remaining `aws` call against offline `--generate-cli-skeleton` shapes | `infra-engineer`; `test-engineer` | Audit table; script test counts | `code-reviewer` | infra and test commits |
| P3 | Context budget for direct-coauthor questions (`contextTokenBudget = 4096`, `modules/core/src/main/resources/scholarchain.runtime-config.v1.json` line 16) | `domain-engineer`; `rag-engineer` | 22-coauthor fixture answers within budget; `sbt check` exit 0 | `code-reviewer` | domain and rag commits |
| P4 | Root cause and fix for the 16B path abstentions (0/10) from `target/experiment-runs/16b-live-evaluation-16b-1/raw/` | `rag-engineer` (others only if the cause is in their module) | A reproducing test fails before the fix and passes after; root-cause note | `code-reviewer` | rag commit |
| P5 | `terraform_data.phase12b_guard` added to `CLEANUP_TEARDOWN_ADDRESS_RULES`; decide about `configuration_guard` and `provider_guard` | `infra-engineer`; `test-engineer` if `tests/infra` is affected | Listing test returns a token; a rogue address is still refused | `code-reviewer` | infra commit, then pins refresh |
| P6 (**extended**) | Local dry run of the full EMR step chain **at both S and L**: stage-in → hadoop-prep → ER → Spark (same templates) → copy-out tree, recording local wall time and output bytes per part. Then on S: `StorageLoadMain --dry-run`, `RuntimeArtifactMain`, `EmbeddingManifestMain` render-only, upload-slice dry run. **Added 2026-11-16 (your 4a review answer 4; fallback in section 5.2 step 7b): keep the S Spark export for Thursday.** Requirements:<br>(a) **what:** the complete Spark export directory of the P6 S run, the one passed as `--export`, kept whole and unmodified. It holds `load-manifests/s3.json`, `load-manifests/s3vectors.json`, `semantic-summaries/`, `nodes/type=topic/`, `nodes/type=institution/`, all other tables and `_SCHOLARCHAIN_SPARK_COMPLETE`; the reader checks the tables against their manifests and reads the qualifications (`Phase6EmbeddingSource.scala:66`, `:76`, `:98`, `:108-112`, `:121` at HEAD `7a02de2`);<br>(b) **where:** a git-ignored directory under `target/`, outside `target/phase14/private/` and outside any directory a build `clean` removes (to confirm with the build-engineer). The harness owner sets the path; a proposal is `target/phase15/p6/size-S/<p6-run-id>/` with the export in `spark/`. That path does not exist yet;<br>(c) **sha manifest:** `SHA256SUMS` in that directory, one line per file of `spark/` (relative paths, sorted), plus a provenance file: git commit, job JAR sha256 (equal to the S manifest's), Spark template sha256 (P24), the S input tree's sha256, the P6 run ID (equal to the render report's `sourceRunId`), and start and end UTC. Also keep the P6 `EmbeddingManifestMain` render-only report of the same export;<br>(d) **reproducibility:** P6 S runs on the frozen session commit, after the P15 rebuild. If a later commit changes the Hadoop, ER, Spark or export code or the templates, rerun P6 S. Keep the directory until the Session 2 report is accepted. Thursday check: `shasum -a 256 -c SHA256SUMS` exits 0 and the commit equals `git rev-parse HEAD` | `infra-engineer` (harness under `scripts/**`); `test-engineer` (e2e test); `hadoop-engineer`, `spark-engineer`, `storage-engineer` for defects. **Any path outside `scripts/**` needs a human owner assignment first.** | **Results (2026-11-16; lane logs under `target/phase15/lanes/`):** S passed all 6 steps locally, final run `p6-S-20261116T171431Z` without workarounds (Hadoop 47 s, ER 165 s at 12g, Spark 490 s, copy-out 5 s). D1 and D2 (Hadoop CLI arguments built by `sc-step.sh`) are fixed and tested. L: Hadoop passes (132 s; 210 works dropped by the team limit; maximum team 79), ER runs out of memory at 22g after 16 min, so L is dropped on EMR; Spark at L ran locally with ER bypassed (identity pass-through, local only, not the EMR path). **Retention:** `target/phase15/p6/size-S/run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae/` with `spark/`, `render/`, `provenance.json` and `SHA256SUMS` (sha256 `c9b3fb2d602a680fcd31c59af387e7730c5c2d313541e1496ffbc7988b2b5000`). It comes from retention run `p6-S-20261116T164523Z`, made on the working tree with the D1/D2 workaround, **not the frozen commit**, so requirement (d) still needs a rerun. Check it with `cd "target/phase15/p6/size-S/run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae" && shasum -a 256 -c SHA256SUMS`; the paths in `SHA256SUMS` are relative. **Do not run `sbt clean`:** the build has no keep rule for `target/`, so a root `sbt clean` would delete the retention (build-engineer or human decision pending). Acceptance: each step exits 0; counters and rejects present with **0** `maxLocalSampleRecords` rejects; `_SCHOLARCHAIN_SPARK_COMPLETE`; loader dry-run counts on S (compare 78,104 / 328,967 / 269,753); sidecar parts within the loader cap; a size and time table for S and L. **(Superseded 2026-11-16: L is dropped on EMR; the S cap is 75 min, and the P6 S step timeouts sum to 4500 s = 75 min.)** | `code-reviewer` | infra and test commits |
| P7 | Stage-a apply path: (a) a `terraform test` run for the stage-a variable set; (b) expected deltas for stage-a base, stage-a EMR enable and the R-b base plan (including `module.emr` deletes); (c) a fake-terraform test that `deploy.sh --stage base-apply --skip-runtime-archive` accepts the EMR-only plan, or a named stage; (d) EFS mount-target `depends_on` | `infra-engineer` | test counts | `code-reviewer` | infra commit, then pins refresh |
| P9 | Elasticity dashboard on free native metrics (ALB `HealthyHostCount`, `RequestCount`, `TargetResponseTime` p50/p95/p99, 5XX; `AWS/ECS` CPU and memory), at most 50 metrics | `infra-engineer` | `terraform test` on the widget metric count | `code-reviewer` | infra commit |
| P10 | ID continuity between the S export from EMR and `experiments/inputs/14c/*`; if IDs differ, re-derive the inputs or match the ER mode (your decision) | `experiment-engineer`; `entity-resolution-engineer` | Script output on the P6 S export | `code-reviewer` | experiment commit |
| P11 | Failure-and-recovery manifest and procedure; a narrow permission if needed | `experiment-engineer`; `infra-engineer` | Manifest check; deployer test | `code-reviewer` | commits |
| P12 | LLM answers: transfers from bucket 15b or a new allocation; `eval16b.py` subset mode (24 answers) | `experiment-engineer` | `load-tests/tests` counts; subset `PLAN-OK` | `code-reviewer` | experiment commit |
| P13 | Local elasticity rehearsal against `scripts/smoke-local.sh` | `experiment-engineer` | Run record `completed` | `code-reviewer` | evidence only |
| P14 | Warm-up readiness gate (first query after idle could return 504) | `service-engineer` | `readyz` waits for the warm-up | `code-reviewer` | service commit (recommended) |
| P15 | Rebuild after the fixes: re-render manifests (A1.4), pins (A2), full check (A1.7), images (A12) | the human runs these; script owners as listed | `check.sh` returns `RESULT: PASS gates=7` | `test-engineer` report | human commits |
| P16 | (optional, option L) `StorageLoadMain --cache-only` | `storage-engineer` | Storage test | `code-reviewer` | storage commit |
| P17 | (only if B8.5 is rerun) itest fixture `toRealPath()` | `storage-engineer` | Fixture unit test | `code-reviewer` | storage commit |
| P18 | Base plan against the residual state (2 guards), or a human-approved move-aside | `infra-engineer`; **the human decides** | Script test | `code-reviewer` | infra commit |
| P19 | Session 2 approval request (wording and caps) and runbook deltas; **draft wording for option (i) in section 4a** (2026-11-16) | request text: `documentation-engineer`; approval record: **human** | Link and arithmetic check | human | human commit |
| P20 | Final `sbt check` (JDK 17) | `build-engineer` gate; `test-engineer` report | exit 0 with counts | `code-reviewer` | none |
| **P21** | **Real DBLP slice L (about 50,000 works), a superset of the 10,577-work slice**, so S ⊂ L. Re-download the pinned `dblp-2026-10-03` archive (1.1 GB; the earlier download took 245 s) under an approved network cap, and extend the selection rule (more venues or a higher per-venue cap; the current 8 venues are capped at 2,500 each), keeping CC0 license provenance. Then build the L input tree and an L manifest (`experiments/manifests/15a-emr-size-<L>.json`) | `dataset-engineer` (`datasets/**`, acquisition script and slice manifest; **the network download needs your recorded approval**); `experiment-engineer` (input tree script and manifest) | Slice manifest with `publicationCount`, sha256, per-venue counts, distinct authors; nesting check S ⊂ L; `check_manifests.py --final` OK | `code-reviewer`; dataset manifest review | dataset and experiment commits |
| **P22** | **Hadoop record ceiling:** raise `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS` (`release.conf`, pinned) and `prep-config.json` `maxLocalSampleRecords` to at least L plus the other-source records. Confirm that the bound's semantics are intended in cluster mode | `infra-engineer` (`release.conf`, `scripts/tests/`); `experiment-engineer` (`prep-config.json`); `hadoop-engineer` (semantics review, Hadoop tests if behaviour changes) | P6 at L shows 0 `maxLocalSampleRecords` rejects; ceiling-check tests | `code-reviewer` | separate commits, then pins refresh |
| **P23** | **Copy-out ceiling:** raise `PIPELINE_MAX_COPYOUT_BYTES` and/or limit copy-out to what the report and loaders need (Spark export, Hadoop counters, rejects and stats, results, config; not `hadoop/intermediate` or the full ER export). The copy-out script is pinned by sha256 in `infra/terraform/emr-step-programs.json`, so that pin changes too | `infra-engineer` (`scripts/emr/sc-step.sh`, `release.conf`, `infra/terraform/emr-step-programs.json`, `scripts/tests/`) | P6 copy-out sizes for S and L under the new ceiling; step-program pin test | `code-reviewer` | infra commit, then pins refresh |
| **P24** | **Spark config for EMR:** a reviewed template with the accepted 64 shuffle partitions for S, and a size-appropriate value for L, in an owned path (for example `experiments/inputs/15a/`), with new sha256 pins in the manifests. Do not edit the Phase 6 evidence file. | `experiment-engineer` (template file and manifests); `spark-engineer` (confirm settings) | P6 sidecar CSV parts within the loader cap at S; L completes locally | `code-reviewer` | experiment commit |
| **P25** | **EMR ledger and caps (your decision):** for two more runs set `EMR_MAX_LIVE_RUNS` 3 → **4** and `EMR_CUMULATIVE_CAP_USD` 2.52 → **3.53** (was 3.36 = 4 x 0.84). **D3 (2026-11-16):** S run cap 75 min with r5.xlarge primary; the ledger reserves 0.84 per run (budget.py, 0.555/h x (75 + 15) min = 0.833). **Raised 3.36 → 3.53 (your decision 2026-11-16, "Raise cap to 3.53", after the pipeline-bundle review 1 finding 1):** 3.53 = 1.68 (Session 1) + 3.33 h x 0.555/h = 1.85. The ledger worst case is 1.68 + 0.84 + 0.84 = **3.36 of 3.53** before actuals (0.17 of room; it was zero margin at 3.36). The project figures do not change (19.54 / 22.98; the EMR block stays 3.33 h = 1.93, already inside 22.98; the pre-R-b check stays spend + 3.57 <= 23.00). L is dropped on EMR (2026-11-16), so no L manifest sets a longer runtime; if a later S manifest ever needs one (at most `PIPELINE_MAX_RUNTIME_MINUTES` 180), recompute the cap with the script's estimate formula. **Rounding budget (review 2 finding 1; accepted by you 2026-11-16, "Accept, add steps"):** every ledger term rounds up to the cent, so with a full 75-min S the retry is admitted only if the time from cluster creation to S submission plus the wait before `--record-actual` is at most about 19 min (steps 5, 5a and 6 of section 5.2); the cap stays 3.53. The alternative, a fresh Session 2 ledger, is not recommended because the caps were decided as cumulative. | `infra-engineer` (`scripts/config/release.conf`, `scripts/tests/`); **the human records the decision** | Ledger tests: run 3 and run 4 reserved, run 5 refused; cumulative-cap refusal at 3.53 (was 3.36) | `code-reviewer` | infra commit, then pins refresh |
| **P26** | **Vector count up to about 10,000:** (a) a render-only proof with the private render config raised (`maxSummaries`, topic and institution caps) that the manifest holds about 10,000 items within `maxManifestItems`, `maxManifestBytes` and the per-text limits, with the exact per-index split; (b) ingest throughput: Session 1 managed 0.614 vectors/s (10,000 would take about 4.5 h), so either batched Voyage embedding requests or the unbatched ingest overlapping run L at stage-a rates (section 5.2, Q8); (c) check the Voyage account tier limits on the dashboard | `rag-engineer` (limits, batching, tests); **the human** (private render config, Q8) | Render-only report: `selectedDocuments` about 10,000, `embeddingCalls=0`; rag tests for batching; a measured local throughput with a fake embedder | `code-reviewer` | rag commit |
| **P27** | **ER reliability section:** Wilson or bootstrap 95% intervals for precision, recall and F1 by entity and with/without assisted pairs; positive and negative balance table; selection method; how sample size limits conclusions; state 240 reviewed / 194 + 6 held-out against the course's 200 | `experiment-engineer` (metrics script under `experiments/**`); `entity-resolution-engineer` review | Script output reproduces the intervals in section 3a from the recorded counts | `code-reviewer` | experiment commit |
| **P28** | **Final-report scale table and the fixture-versus-real section** (section 8 template) | `documentation-engineer` (Phase 17A) | Every row filled from evidence; links resolve | reviewer, then human | docs commit |
| **P29** | **Done 2026-11-15** (human-supplied record, section 1b). The instructor **approved** ScholarChain's reduced scales (integrated run at about 10.5k and about 50k works; up to 10,000 real voyage-4-lite vectors; the ER set of 200 reviewed / 194 definitive as close) and **declined** the budget raise. | human | Instructor reply kept by the human | none | none |
| **P0** | **Budget guard before any apply.** **Your answers (2026-11-15), all five defaults accepted:** (1) actual-spend alerts at **USD 18 / 20 / 22**, no forecast alerts; (2) limit **USD 25**, custom period **2026-10-01 to 2027-01-01**; (3) the same private recipient (not written here); (4) live modify on **Tue 2026-11-17** through the reviewed billing procedure (runbook A3: plan, gate record, `budget_execution.py modify`, verification). **Decision A (your answer, 2026-11-15):** the modify gate record goes under `docs/agent-runs/phase-14/` and its packet under `docs/agent-runs/phase-14/evidence/14b/`, because the wrapper accepts only those prefixes (`budget_execution.py` `MODIFY_RECORD_PREFIX` and `MODIFY_PACKET_PREFIX`, lines 58-59; `budget_verification.py` requires `docs/agent-runs/phase-14/evidence/14b/budget-modify-verify-<name>`, line 431). The Phase 15 records cross-reference them; no code change; (5) beforehand, a **read-only Switch Role check** of `scholarchain-billing-deployer`. **Your condition:** the budget must **exclude credits and refunds**, so it measures spend before credits and matches Cost Explorer's 15.75. With about USD 140 of credits, a credit-inclusive budget would stay at 0 and never alert. **Facts:** `infra/terraform/billing-bootstrap/main.tf` sets `cost_types { include_credit = false, include_refund = false, include_tax = true … }`; `scripts/billing/budget_execution.py` pins `COST_TYPES` (`IncludeCredit: False`, `IncludeRefund: False`, `IncludeTax: True`, …) and its readback refuses (`COST_TYPES`) when a returned `CostTypes` differs. The live Phase 12 budget has **no recorded API `CostTypes` readback** (the Phase 12D readback was BLOCKED-ON). It does show USD 15.75 spent, equal to Cost Explorer with credits excluded, while Bills shows 0.00 net, so it **behaves as credit-excluding**. **P0's modify readback will be the first recorded confirmation.** Note: the AWS budget and its alerts cover **AWS only**. Anthropic and Voyage are tracked in the LLM ledger and the combined `C11_TOTAL_USD`, and the USD 25 cap gates (receipts, gate 1 and the pre-R-b check; gate 2 is no longer applied since R-c was dropped on 2026-11-16) use the **combined** total. | **human** (executes the check and the modify, owns the decisions); `infra-engineer` (`scripts/billing/**`, `infra/terraform/billing-bootstrap/**`) if modify inputs or pins must change | Switch-role check log; modify apply log; verification output with `notification_count: 3` and the readback passing `COST_TYPES` (credits and refunds excluded) | `code-reviewer` for any changed billing file | human commit (gate record, public packet, pins) |
| **P30** | **Resolve the 6 uncertain held-out ER pairs.** A human re-review of exactly those 6 tasks, recorded as a **new** label version (the 2026-10-20 directory is immutable), then import and re-evaluation. If a pair stays ambiguous, document why. | **human** (the labelling decisions); `dataset-engineer` (the new label-version records under `datasets/entity-resolution/labels/**`); `entity-resolution-engineer` (import with the existing CLI, re-run the held-out evaluation in `modules/entity-resolution`) | New `validated-labels.json` with 200 held-out definitive or with documented residual ambiguity; evaluation re-run; metrics before and after | `code-reviewer`; gold-set evaluation review | dataset and ER commits |
| **P31** | **Document how the AI-assisted reviews were validated, honestly.** The label README says the labels are "human-reviewed, AI-assisted, not independent blind gold"; 22 external source checks were not retained. Existing partial checks to report: (1) 55 of 57 held-out true positives are exact-identifier matches (DOI or ORCID agreement, independent of the AI); (2) the 17 human decisions that differ from the AI proposal; (3) the sensitivity run without the 22 assisted pairs (181 binary, recall 0.864). **Optional, stronger:** a blind second pass by the human on a random seeded sample (for example 30 pairs, no AI suggestions shown) with an agreement measure (Cohen's kappa). | **human** (blind re-review, if chosen); `experiment-engineer` (agreement and interval script under `experiments/**`, with P27); `documentation-engineer` (report text) | Agreement script on fixtures; the sample seed and pair list recorded | `code-reviewer` | experiment commit; docs commit |
| **P32** | **Done 2026-11-15.** Your screenshot: Cost Explorer, 2026-11-13 to 15, service Neptune, by usage type, credits excluded. **USE2-Neptune:ServerlessUsage 9.05; BackupUsage 0.00; StorageIOUsage 0.00; StorageUsage 0.00.** All Neptune cost was serverless capacity: 9.05 / 0.1608 per NCU-hour = about 56 NCU-hours over about 32 h, an average of about **1.8 NCU**. It scaled up and did not return to 1. | **human** (done) | Screenshot kept by you (git-ignored evidence) | none | none |
| **P33** | (Option (a) only; **not recommended**) "graph disabled" runtime mode: optional Neptune endpoint, graph-service and query-api readiness without Neptune, Terraform precondition and endpoint changes, ALB health path | `service-engineer`; `infra-engineer`; `test-engineer` | Service and Terraform tests; offline-synthetic smoke in the new mode | `code-reviewer` | service and infra commits |
| **P34** | **Closed 2026-11-16: not possible. Capacity stays min 1 / max 2.5 NCU (the Session 1 configuration).** The plan was to allow and set `neptune_max_ncu = 1`, a 0.1608/h ceiling. The Amazon Neptune User Guide ("Capacity scaling in a Neptune Serverless DB cluster", read by the infra-engineer 2026-11-16; section 2) gives 2.5 NCU as the smallest maximum capacity. Your decision (2026-11-16): "P34 as planned is impossible. Set min 1 / max 2.5 NCU." Terraform already enforces this: the `phase12b.tf` precondition (line 22) requires min >= 1 and max exactly 2.5, and `tests/phase15_elasticity.tftest.hcl` pins that max 1 is refused. **No Terraform change is made** (none existed to revert). Consequence: the Neptune ceiling is 2.5 x 0.1608 per NCU-hour = **0.402/h**; the plan uses the observed 0.297/h (about 1.85 NCU, P32) for planned figures and 0.402/h for caps (sections 6.3 and 6.4). | `infra-engineer` (no change); **your decision (Q3 yes on 2026-11-15; outcome 2026-11-16: not possible)** | None needed; the existing guard and `phase15_elasticity.tftest.hcl` cover min 1 / max 2.5 | none | none |
| **P35** | **Elasticity rehearsal of the chosen combination (semantic load + ALB request-count scaling).** Run `scripts/smoke-local.sh` (query-api in offline-synthetic mode, with the P40 route and cache using fakes) with query-api limited to 0.25 vCPU, and `loadgen.py run` with the P42 semantic manifest. **Acceptance:** (1) run outcome `completed`, error rate 0; (2) measured requests per second at each level, from which you derive the `query_requests_per_target_target` value: below target at level 1, at least twice the target at levels 25 and 50 (per-minute count per task). **Amended 2026-11-15:** that rate counts **successful responses only**; 429s are counted per level and reported separately, and they are excluded from the rate, latency and throughput figures; (3) embed calls equal the number of distinct questions **per semantic-service task** (cache hits for the rest), read from the cache hit and miss counters on `/metrics` (offline, in-process, so this check is unaffected by review finding R2. In aws mode those counters exist only on semantic-service's `/metrics`, which the ALB does not route to, so the same figure cannot be read that way in R-b. **R2 decided 2026-11-16:** in Session 2 the figure comes from the Voyage usage page, read by you after the session with its read time, reported as the total for the **R-b load window** only (the stage-a ingest and the query smoke also call Voyage) and compared with the fixed question-set size, allowing for the section 6.3a caveats (up to about 4 × distinct questions from task starts, plus a few duplicate calls from a cold task's uncoalesced concurrent misses), or marked "unverified" if the page cannot isolate the R-b window; see section 5.3 step 4); (4) query-api CPU per level recorded; (5) **(added 2026-11-15; your Q16 answer)** the Session 2 rate-limit value is set from the measurement: **`r_S2` = at least 2 x the measured peak served requests per second per query-api task at level 50**. It must be within the code range 1-100,000, with **burst `b_S2` = 2 x `r_S2`**. It is applied through the P41 root variables `query_semantic_rate_limit_per_second` = `r_S2` and `query_semantic_rate_limit_burst` = `b_S2` (which set `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` on query-api in aws mode; reworded 2026-11-16, your P41-D follow-up answer 2). The offline-synthetic rehearsal has no S3 Vectors latency, so its served rate is likely higher than live, which errs toward no throttling. A high `r_S2` does not raise cost, because the required P42 per-level limits bound the query count (section 6.3a); (6) **zero 429s at every level** (`api_rate_limited_total` unchanged, and no 429 in the load generator's per-level counts). **Result and decision (2026-11-16):** see the P35 results paragraph below this table. The measured local per-level rates did **not** replace the 200 ms planning assumption in section 6.3a: you set the target from the live estimate instead (T = 3000), a recorded deviation from the local rule in item (2). The request-count policy itself cannot run locally; it is covered by P41's `terraform test`. | `experiment-engineer` (load side); `service-engineer` (offline-synthetic route availability, P40) | Run record, a CPU and request-rate table per level, and the derived target value | `code-reviewer` | evidence only (plus the manifest commit in P42) |
| **P36 (N1)** | **synthesis-v2 version bump before any Session 2 paid answer.** In Session 1 the prompt was edited in place under the `synthesis-v1` label (the decision record notes that a bump needed core/service config). Give the changed prompt and schema a new version label wherever the runtime records prompt versions. | `rag-engineer` (`prompts/runtime/**`, `prompts/schemas/**`, rag tests); `domain-engineer` (the prompt-version value in `modules/core` config, if it lives there); `service-engineer` (only if service config pins it) | Tests show the new label in explain output and the old label refused or not used; `sbt check` | `code-reviewer` | separate commits |
| **P37 (N4)** | **Image-digest check as a Session 2 step:** after every runtime-apply and the R-c pointer apply, compare running task image digests with the push record (runbook B6.5 commands) and save the result | **human** executes; `infra-engineer` only if a helper script is wanted | `digests match` line in the session evidence | none | none |
| **P38 (N5)** | **Logging for the storage and rag command-line tools** (`StorageLoadMain`, `RuntimeArtifactMain`, `EmbeddingManifestMain`, `LiveEmbeddingIngestMain`, `LiveEmbeddingSmokeMain`). Session 1's integration-test logs carried DEBUG wire logs with temporary SigV4 session tokens. Give these tools a packaged logback configuration at INFO, with AWS SDK and HTTP wire logging at WARN, as the services got in repair 6. | `storage-engineer` (`modules/storage`); `rag-engineer` (`modules/rag`); `build-engineer` if it is a build-level resource | A test or check showing no DEBUG wire lines when a tool runs against fakes | `code-reviewer` | separate commits |
| **P39 (N9)** | **Remove the deployer role at the final cleanup.** After C4 (operator roles off) and C5, destroy the remaining deployer stack (`aws_iam_role.deployer`, its permission-set policies and attachments, boundaries) with the admin profile inside IAM window 2. A reviewed plan must show only deployer-state resources; the billing roles and budget are kept. | `infra-engineer` (procedure, expected destroy count, test); **human** executes and approves | Deployer `terraform plan -destroy` listing reviewed; after-inventory shows no `scholarchain-deployer` role | `code-reviewer` | infra commit (procedure) |
| **P40** | **Public semantic route + query-embedding cache** (F25), as you specified (section 9.2, answer 1): `POST /v1/semantic/retrieve` on query-api, forwarding to semantic-service, plus a bounded LRU embedding cache (size from config; hit and miss counters on `/metrics`) wrapping the Voyage client in semantic-service. Also served in offline-synthetic mode for P35. **Cutoff: reviewed and committed by Wed Nov 18, 12:00 CST.** Otherwise use the fallback (request-count scaling on health-check load, labelled as weaker evidence). No last-minute changes. **Accepted defaults (your Work order 2 answers, 2026-11-15):**<br>(a) **public limits:** topK at most 20, question at most 1,000 characters, body at most 8 KiB, filters at most 16 (same filter shape as the internal route); the internal route keeps its limits;<br>(b) **rate limit:** an in-memory token bucket per API key in each query-api task; code default 50 requests/s with a burst of 100, overridable on query-api by `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` (default 50, range 1-100,000) and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` (default 100); a typed 429 `RATE_LIMITED` reply marked retryable; 429s counted on `/metrics`. The Session 2 value `r_S2` is set from P35 (at least 2 x the measured peak served rate per task at level 50, burst 2 x `r_S2`) so that no level is throttled;<br>(c) **cache:** an in-memory LRU per semantic-service task, 1,024 entries by default (`SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES` on semantic-service, default 1024), keyed by (model, input type, hash of the question text), no TTL; only successful embeddings are cached; the key and logs never hold the question text in clear;<br>(d) **`/metrics`** carries `api_rate_limited_total`, `api_route_requests_total{route,status}`, and `embedding_cache_hits_total`, `embedding_cache_misses_total`, `embedding_cache_evictions_total`, `embedding_cache_size` and `embedding_cache_capacity` (names as implemented, `ApiApplication.scala` lines 77-91; env names in `PublicSemanticRoute.scala` lines 42-43 and 59; read 2026-11-15);<br>(e) **no Terraform change in P40**: the code defaults apply, and any environment override rides with P41's infra change;<br>(f) **schedule:** build now, one review of the whole P40 bundle on Mon 2026-11-16, commit by Tue 2026-11-17 after your "Yes, commit" (Wed morning is buffer). | `service-engineer` (route, rate limiter, composition, OpenAPI, config, service tests); `rag-engineer` (cache decorator and its tests); `test-engineer` (independent API test under `tests/**`) | **Acceptance:** (1) the **same API key** as the other `/v1` routes; 401 without it; (2) **bounded top-k and question length** (the public limits in (a); 400 when exceeded); (3) **rate limiting** on the route, with a configured per-key request rate and a typed 429 reply (as in (b)); (4) **typed errors** in the existing `ApiError` shape (400, 401, 429, 503/504 downstream); (5) the **response is no wider than the internal route** (`hits` with key, distance, metadata, plus `model`; no extra fields); (6) one embed call per distinct question (cache); (7) no question text in logs; (8) unit and service tests for (1)-(7), **plus an independent `test-engineer` API test**; (9) the offline-synthetic smoke calls the route | `code-reviewer` (security-relevant: new public route) | separate commits by the cutoff; images rebuilt (P15) |
| **P41** | **ALB request-count target tracking for query-api** (F26): `aws_appautoscaling_policy` with `ALBRequestCountPerTarget` and `resource_label` from `aws_lb.query[0].arn_suffix` / `aws_lb_target_group.query[0].arn_suffix`; a validated variable (for example `query_requests_per_target_target`, nullable, positive, bounded); scale-in cooldown 300 s and scale-out cooldown 60 s as for CPU; the CPU policy kept; a dashboard panel for `RequestCountPerTarget` (inside P9's 50-metric limit). **Accepted defaults (your Work order 3 answers, 2026-11-16: "Accept defaults"; the implementation is not yet reviewed):**<br>(a) **policy:** a second target-tracking policy for **query-api only** on `ALBRequestCountPerTarget`, `resource_label` `"<alb arn_suffix>/<target group arn_suffix>"`; it exists only when the runtime is deployed and the target is set; cooldowns 300 s (scale-in) / 60 s (scale-out); scale-in stays on; the CPU policy and its target 60 are unchanged for all three HTTP services;<br>(b) **root variables:** `query_requests_per_target_target` (number, default null = no policy, a whole number from 1 to 100,000 requests per target per minute; the value comes from P35: **3000**, your decision of 2026-11-16, see the P35 results paragraph below the prerequisites table); `query_semantic_rate_limit_per_second` (null or 1-100,000) and `query_semantic_rate_limit_burst` (null or 1-1,000,000), where null leaves the environment setting unset so the P40 code defaults 50 / 100 apply (Session 2 values from P35: **3500** and **7000**); the two rate-limit values are set on **query-api only, in aws mode**;<br>(c) **no cache-size variable:** the code default of 1,024 entries is well above the 100-200 questions;<br>(d) **one dashboard panel** for ALB `RequestCountPerTarget` and `HTTPCode_Target_4XX_Count`, within P9's 50-metric limit;<br>(e) **schedule:** build Mon 2026-11-16, one review Tue 2026-11-17, commit by Wed 2026-11-18 12:00 CST after your "Yes, commit". | `infra-engineer` (`infra/terraform/**` and its `terraform test` files); `test-engineer` (`tests/infra/**`, only where the shape checks list scaling policies or environment names) | `terraform test`: policy exists only with the runtime deployed and the variable set; label format; CPU policy unchanged; existing tests pass; pins refresh | `code-reviewer` | infra commit, then pins refresh |
| **P42** | **Load generator `semantic` route and manifest:** a `semantic` route (POST, API key, body `{"question": …, "topK": …}` from a fixed questions file of real DBLP topic phrases), weights favouring `semantic`, max-request caps per level, and a manifest variant (for example `15b-ecs-scaling-semantic.json`) with levels 1/5/25/50, a hold, and at least 25 quiet minutes. **Added 2026-11-15 (your Work order 2 answer 2):**<br>- the questions file is a **fixed set of about 100-200 distinct questions**, so Voyage calls are bounded by cache misses (section 6.3a);<br>- **429s are reported separately** from successful responses, as a count per level, and are **excluded from the latency and throughput figures** and from the request rate P35 uses to derive the request-count target;<br>- **Required (your Q16 answer, 2026-11-15):** the per-level request limits **600 / 3,000 / 15,000 / 30,000 / 150,000** (levels 1, 5, 25, 50 and the hold at 50; 198,600 in total). They are the cost bound of R-b (section 6.3a) and must not be raised;<br>- **a warm-up pass before the ramp:** each distinct question is sent once at level 1, so embed calls equal the distinct questions per semantic-service task. Concurrent misses for the same question are not coalesced, so without the warm-up two workers could miss on the same question at once. The warm-up sends at most 200 requests; it either counts inside the level-1 limit of 600 or is its own phase with `max_requests` at most 200;<br>- 429s reported per level and excluded from latency and throughput, as above;<br>- **Review finding R2 (P40 review 1; decided 2026-11-16, your P41-D follow-up answer (a)):** in R-b the warm-up's effect ("embed calls equal the distinct questions per semantic-service task") cannot be read from the `embedding_cache_*` counters, because in aws mode they exist only on semantic-service's `/metrics` and the ALB routes every path to query-api. The evidence source is the Voyage usage page, read by you after the session with its read time. The figure is the total for the R-b load window only (not per task, not the whole Session 2 day), checked against the fixed question-set size (misses ≤ distinct questions). Per section 6.3a, a total up to about 4 × distinct questions is explained by semantic-service task starts (restarts or a second scale-out), and a cold task's uncoalesced concurrent misses can add a few duplicate calls; only a total clearly above that would point to a cache problem. If the page cannot isolate the R-b window, the figure is "unverified" (section 5.3 step 4). | `experiment-engineer` (`load-tests/**`, `experiments/manifests/**`) | `load-tests/tests` for route building, auth header, caps, abort rules, the 429 separation (a 429 counted per level, absent from the latency and throughput figures) and the warm-up pass; `validate-manifest` OK with the required per-level limits | `code-reviewer` | experiment commit |
| **P43** | **(R-c only) answer-path readiness:** P3, P4, P10 (ID continuity of the 24 questions against S's EMR output), P12 (subset mode and a ledger transfer of 28 answers out of bucket 15b), P14 (warm-up readiness) and P16 (`--cache-only` so the DynamoDB cache loads during stage a), each passing locally | owners as in those rows | `eval16b.py plan` for the 24-question subset prints `PLAN-OK`; P3 and P4 tests pass; P10 shows all IDs present | `code-reviewer` | as in those rows |

**Which prerequisites each part needs:**

| Part | Prerequisites |
|---|---|
| **R0 + R-b (approved plan)** | P0, P1, P2, P5, P6 (S chain and render-only on S; L local evidence), P7, P9, P11 (option (i)), P15, P18, P19, P20, P21-P27, P30-P32, P32 (done), P35, P37, P38, P39, P40, P41, P42 |
| **R-c (dropped, option (i), 2026-11-16)** | was: all of the above plus P36 (N1) and P43 (P3, P4, P10, P12, P14, P16) |
| **Not needed** | P13 (replaced by P35), P17, P33, P34 (closed 2026-11-16: not possible) |

**P35 results and decision (added 2026-11-16; observed, from `docs/agent-runs/phase-15/evidence/p35/` and the experiment-engineer's P35 report in `docs/agent-runs/phase-15/owner-report.md`).**

- **Run:** `p35-local-1`, outcome **completed**. query-api in offline-synthetic mode in Docker at 0.25 vCPU (cgroup `cpu.max` 25000 100000), one task, local rate limit raised to 100000 / 100000, load generator on the host over loopback. **198,750 requests** (150 warm-up plus 198,600 ramp), **0 errors**, **0 x 429** in every phase (the server's `api_rate_limited_total` was 0 before and after).
- **Served rate per task, 429s excluded (there were none)**, from `rehearsal/per-level-results.json` (`success_rps`, per minute = x 60) and `loadgen/derived/summary.json`:

| Phase | Level | Requests | Served per second | Served per minute | Peak 1 s | CPU, % of 0.25 vCPU |
|---|---|---|---|---|---|---|
| warm-up | 1 | 150 | 33.319 | 1,999 | 52 | 99.4 |
| baseline | 1 | 600 | 88.08 | 5,285 | 131 | 100.0 |
| level 5 | 5 | 3,000 | 222.469 | 13,348 | 293 | 98.8 |
| level 25 | 25 | 15,000 | 450.572 | 27,034 | 668 | 98.4 |
| level 50 | 50 | 30,000 | 806.235 | 48,374 | 1,262 | 96.5 |
| hold at 50 | 50 | 150,000 | 1,015.538 | 60,932 | 1,737 | 95.1 |

- **Embed calls:** `embedding_cache_misses_total` 150 equals the 150 distinct pinned questions (one task); `embedding_cache_hits_total` 180,594; hits plus misses 180,744, the number of semantic requests; no evictions; cache size 150 of capacity 1024. This offline check is not affected by review finding R2.
- **CPU (interpolated, approximate):** the per-phase CPU figures are interpolated from 2 s cgroup samples; the warm-up and baseline phases span only 2-4 samples. The 0.25 vCPU limit was saturated at **every** level (95-100% of the limit; 98-100% of periods throttled), including level 1. The CPU policy therefore cannot be assessed from this run.
- **Caveat (offline-synthetic):** there is no S3 Vectors, Voyage or network latency and the fake route returns an empty hit list, so the served rates are a local CPU-bound figure, far above what live will serve. They do not predict live rates. The short phases (7-148 s) end at their request caps, and level 1 is JVM-cold.
- **Local rule (not used for T):** T > 5,285 and 2T <= 27,034 gives 5,285 < T <= 13,517 (the experiment-engineer proposed 10,000). With the plan's live estimate of 200 ms per request, level 25 offers only about 7,500 per minute per task, so T = 10,000 would probably not scale out at level 25 live.
- **Decision (yours, 2026-11-16; your words: "T = 3,000 (Recommended)"):** `query_requests_per_target_target` = **3000**, set from the live 200 ms estimate and recorded as a **deviation from the local rule**. At 200 ms a worker sends 5 requests per second, so one task offers about 300 per minute per level step: level 1 about 300 and level 5 about 1,500 per minute stay **below** T; level 25 (about 7,500) is about **2.5 x** T and level 50 (about 15,000) about **5 x** T. These are estimates, not measurements. Scale-out is still capped by the Terraform maximum task count (query-api max 2).
  - **Cap at 2 tasks:** after scale-out to 2 tasks, level 50 still offers about 7,500 per target per minute (2.5 x T). The policy would want about 5 tasks (15,000 / 3,000), so it stays pinned at the maximum of 2 through the hold; scale-in follows only the end of the load.
  - **Level 25 is not expected to trigger scale-out:** at 200 ms it reaches its 15,000-request cap in about 120 s (section 6.3a), which is shorter than the plan's own scale-out estimate of about 6.5 min (three one-minute datapoints plus task start; section 6.4 hold arithmetic). Scale-out is therefore expected during level 50 and the hold.
  - **Sensitivity (estimates):** at 400 ms per request, level 25 offers only about 3,750 per minute per task, 1.25 x T. At 100 ms or less, level 5 offers about 3,000 or more per minute and reaches T.
- **Rate limit (coordinator default from your Q16 formula, not asked):** the highest level-50 peak served rate was 1,737 requests per second (hold; the 50-level phase alone 1,262). 2 x 1,737 = 3,474, rounded up: `query_semantic_rate_limit_per_second` = **3500**, `query_semantic_rate_limit_burst` = **7000** (2 x). Both are inside the code ranges (1-100,000 and 1-1,000,000). The per-run request caps (198,600) bind the R-b S3 Vectors cost, so these values do not change it (section 6.3a).
- **Set by you in the private tfvars:** `query_requests_per_target_target` = 3000, `query_semantic_rate_limit_per_second` = 3500, `query_semantic_rate_limit_burst` = 7000. This document does not set them.
- **Not shown by P35:** how the policy behaves on AWS (ALB metric timing, scale-out time), the live served rate, and whether level 1 stays below T live. The local level-1 rate (5,285 per minute) is above 3000 only because the offline task is CPU-bound; at 200 ms live it is about 300.

## 4a. P19: draft wording for the Session 2 approval record (option (i))

**Draft wording for the human's record; not a record.** Drafted 2026-11-16 by the documentation-engineer from your decisions recorded verbatim in `docs/agent-runs/phase-15/prompt.md` (P25 and P21 decisions; R-b option decision (i); key-handling approval) and from sections 5 and 6 of this plan. Copy it, change anything you disagree with, fill in the blanks, date it and commit it yourself. No agent writes or commits the record. The figures are planning estimates, not measurements.

```text
ScholarChain Session 2 approval record (Procedure R)

Approver: ______________________   Date: ____-__-__   Time (UTC): __:__Z

I approve Session 2 under plan option (i), as written in
docs/runbooks/session-2-plan.md at commit ______________, with these limits:

1. Budget. Firm limit USD 25.00. Floor 2: the project total
   (C11_TOTAL_USD plus Session 2 spend) must stay at or below USD 23.00.
   Planned project total 19.54; at caps 22.98 (tax-0 column; margin 0.02).

2. Tax: 0 on credit-covered spend (my decision 2026-11-16); valid while
   credits cover the spend.
   AWS credit balance read: USD ________ at __:__Z (UTC). It must be at
   least the Session 2 AWS cap of USD 6.73; otherwise this approval is
   void.

3. Stage a, EMR. S = 10,577 works on EMR. L is dropped on EMR (P25
   rule); both EMR runs go to S and its retry. L is reported from local
   evidence only: Hadoop 132 s, 210 works dropped by the team limit,
   maximum team 79, ER out of memory at 22g after 16 min; Spark with ER
   bypassed (identity pass-through, local only, not the EMR path) 1,110 s,
   48,188 works, 76,623 researchers, 320,690 all-years edges.
   Cluster: r5.xlarge primary and m5.xlarge core, 0.555/h; ER heap 12g; S run cap 75 min;
   step timeouts stage-in 225 s, hadoop-prep 900 s, ER 900 s,
   class-origin 225 s, spark 1800 s, copy-out 450 s. EMR cap block
   2 x (75 + 15) min + 20 min cold start = 3.33 h, USD 1.93.
   EMR ledger caps: 4 live runs and USD 3.53 cumulative (was 3.36),
   including Session 1's EMR spend: 3.53 = 1.68 + 3.33 h x 0.555/h = 1.85.
   Worst case before actuals: 1.68 + 0.84 + 0.84 = 3.36 of 3.53. The
   project figures do not change: 19.54 / 22.98, EMR block 3.33 h =
   1.93, and the pre-R-b check stays spend + 3.57 <= 23.00.
   Pricing restated (it sits under emr-pricing.conf's human pricing
   confirmation): r5.xlarge primary EC2 0.252 + EMR 0.063 = 0.315/h;
   m5.xlarge core 0.240/h; cluster total 0.555/h.
   S retry condition: after S's actual is recorded, the retry is admitted
   only if S's measured cost (from cluster creation, boot included) is
   at most 0.87 (3.53 - 1.68 - 0.84 - 0.14 tail), about 94 min at
   0.555/h. Otherwise the retry is refused (fail-closed) and the plan
   goes to the "S fails twice" fallback (P6 local S export).
   Rounding budget (accepted 2026-11-16, "Accept, add steps"; cap stays
   3.53): every ledger term rounds up to the cent. With a full 75-min S,
   the retry is admitted only if the time from cluster creation to S
   submission, plus the wait before --record-actual, is at most about
   19 min (95 min = 0.87875, rounded up to 0.88; 1.68 + 0.88 + 0.14 +
   0.84 = 3.54 > 3.53). Measured cold start is 4-5 min. Operator steps:
   (a) write record 1 and submit S as soon as the cluster ID exists;
   (b) run --record-actual immediately after an S failure, before
   anything else.
   The EMR actual cost is recorded right after each S run
   (run-bounded-pipeline.sh --record-actual), and gate 1 and the
   pre-R-b check use the recorded actuals, not the cap. Run rule: S first; if S
   succeeds the next run is L; if S fails, retry S once and drop L as a
   stated limitation. If L fails, no retry: report it with logs.
   If S fails twice, R-b is not dropped: the chunks and vectors come
   from the retained local P6 S export (same Voyage cap), they are
   loaded, and R-b runs if gate 1 and the pre-R-b check pass by about
   12:15 CST. The report states "vectors derived from the local P6 S run".
   Vectors: up to 10,000 real voyage-4-lite vectors, actual count reported.

4. Gate 1 and the pre-R-b check (both must pass before any R-b apply).
   Gate 1: X_a <= 7.17 - E_b - 0.75 = 7.17 - 3.57 - 0.75 = 2.85.
   Pre-R-b check: spend to date (C11_TOTAL_USD as last read, with its read
   time, plus the clock-based estimate since that read) + R-b cap
   (E_b = 3.57) <= 23.00 (floor 2). Above 23.00, R-b is skipped and
   cleanup starts, unless I record a new decision.

5. R-b Neptune. Capacity min 1 / max 2.5 NCU (P34, max 1 NCU, is not
   possible). The Neptune window is a hard stop at 5.8 h:
   - T_N0 = the actual start of the Neptune base-apply, written in the
     session log (planned 10:50 CST / 16:50Z);
   - the R-b load starts immediately after the B6 smoke passes (planned
     12:45 CST / 18:45Z); the failure example comes after the load
     collection;
   - latest full-variant (about 50 min) load start: T_N0 + 3 h 35 min
     (planned 14:25 CST / 20:25Z);
   - latest load start of any kind (37-min short variant): T_N0 + 3 h 48 min
     (planned 14:38 CST / 20:38Z);
   - the pre-destroy steps (B13, C2 cleanup-prepare plan and apply, the
     C3 pass-1 listing; about 50 min) start no later than T_N0 + 4 h 25 min
     (planned 15:15 CST / 21:15Z);
   - target: the Neptune destroy is issued at T_N0 + 5 h 15 min
     (planned 16:05 CST / 22:05Z);
   - absolute hard stop: the Neptune destroy is issued no later than
     T_N0 + 5 h 30 min (planned 16:20 CST / 22:20Z), whether R-b has
     finished or not, so that about 18 min of deletion (an estimate) ends
     by 5.8 h. Whatever elasticity data was captured is kept, and the
     report states what was cut.
   The overall session hard stop stays 19:00 CST (01:00Z next day).

6. R-b load. The level-50 hold stays at 150,000 requests. The per-level
   request limits are 600 / 3,000 / 15,000 / 30,000 / 150,000 (levels 1, 5,
   25, 50 and the hold at 50) and must not be raised.

7. R-c is dropped. No Neptune graph load and no paid answers in Session 2.

8. Provider keys, including the Session 2 Voyage key (stage-a ingest and
   query smoke) and the Anthropic key. Each key goes only into Secrets Manager or the
   environment of the one process that needs it, never as a command-line
   argument; shell tracing is off (set +x); the Anthropic key has a USD 1
   spend limit; every key is deleted at cleanup and revoked afterwards,
   with UTC times recorded.

Signed: ______________________
```

**Superseded note (outside the record wording; added 2026-11-16 by the documentation-engineer).** In item 3 of the text above, the sentence "Run rule: S first; if S succeeds the next run is L; if S fails, retry S once and drop L as a stated limitation. If L fails, no retry: report it with logs." is kept as your original P25 wording. It is superseded by your 2026-11-16 decision to drop L on EMR (item 3's own first paragraph and P25): the "if S succeeds the next run is L" and "if L fails" parts no longer apply, and the second EMR run exists only as the S retry.

Notes on the draft (not part of the wording):

- Item 8 comes from your key-handling approval of 2026-11-16 (given for the Q12 Anthropic run). Your 4a review (answer 5) keeps it: it covers the Session 2 Voyage key.
- Item 3's run rule is your P25 decision, verbatim. The fallback sentence after it is your 4a review answer 4 (section 5.2 step 7b). It replaces the earlier stage-a stop rule for an S failure.
- Your 4a review of 2026-11-16 (answers 1-5) is applied here: item 5 already carried the corrected clock (target `T_N0` + 5 h 15 min, absolute + 5 h 30 min, latest loads 14:25 and 14:38 CST); items 2, 3, 4 and 8 changed.
- Item 5's clock uses a pre-destroy duration of about 50 min, sized from Session 1 in section 5.5 (part measured, part estimate).

---

## 5. Session outline (one day; recommended plan R0 + R-b)

The step details live in the [Phase 14 runbook](phase-14-live-session.md); this outline names its sections rather than copying them. Durations come from Session 1 evidence (UTC; H0 = 2026-11-13T17:44:01Z) unless marked "estimate".

### 5.0 Measured durations used below

| Step | Observed | Source |
|---|---|---|
| Base-apply with Neptune | about 50 min (the writer alone took over 19 min) | Session 1 |
| Push four images | about 10 min | Session 1 |
| Runtime-apply | about 45 min of apply (one earlier failed attempt) | Session 1 |
| Voyage ingest of 104 vectors | 0.614 vectors/s; 10,000 vectors would take about 4.5 h unbatched | Session 1 |
| EMR cold start | about 4-5 min apply to WAITING; about 15-20 min idle before auto-termination | Session 1 |
| Hadoop, ER and Spark at 10,577 works (local) | 37 s, 97 s (20,000-comparison cap), 180-307 s | Phase 6 evidence |
| Cleanup prepare to pass 2 | about 1 h | Session 1 |

### 5.1 Pre-session (Wed Nov 18 and the morning of the session)

- **Entry:** the required prerequisites (section 4) done and reviewed; C11 check done; P0 budget guard confirmed; your variant decision recorded.
- **IAM window 1 (record open and close times; check them later in CloudTrail):**
  - A4 deployer apply: operator roles on, new `<run-prefix>`, and the P11 stop-task statement.
  - A5 sign-in rehearsal.
  - A7 four service secrets (needed only if R-b runs).
  - Close the window.
- **Keys:** create the new Voyage key (stage a ingest) and Anthropic key (needed only so ECS can start in R-b; the key containers must not be empty) just before entering them in Secrets Manager (B3b). The ingest reads the Voyage key from your shell (runbook B8.6 step 2b).
- **AWS credit balance (your 4a review answer 2, 2026-11-16):** read the remaining AWS credit balance and record it with its UTC time. It must be at least the Session 2 AWS cap, **USD 6.73** (the R0 + R-b AWS part at caps under option (i): 7.15 - 0.42; 6.72 before D3), because tax 0 holds only on credit-covered spend. Otherwise the approval is void.
- **Approval record:** written by you; names S on EMR (L dropped on EMR, P25 rule; the D3 cluster, ER heap 12g, 75-min S cap), the ledger raise (P25), the vector count, the R-b extension and its gates, the floor, the Neptune hard stop and the session hard stop. Draft wording for option (i): section 4a.

### 5.2 Stage a: S3 + EMR at S (L dropped on EMR), then the vectors (no Neptune, ECS or ALB)

1. **P18 precondition, before the stage-a plan** (your answer, 2026-11-16: "Plan stage a against the leftover state after `terraform state list` (addresses only, no state file reads) shows exactly the two guards. Anything else: stop and report."). Run `terraform -chdir=infra/terraform state list`; it prints addresses only. Never read the state file. The output must be exactly these two lines:
   - `terraform_data.configuration_guard`
   - `terraform_data.provider_guard`

   Anything else (another address, or a missing guard): **stop and report to the human; do not plan.** With exactly the two guards, plan stage a against that leftover state, with no move-aside (P18: the guards plan as no-op, the base plan adds resources only). Then:
   B0, then B1 with stage-a tfvars:
   - `neptune_enabled = false`, `runtime_enabled = false`, `emr_config.enabled = false`, `dashboard_enabled = false`.
   - `api_domain_name` set, so the certificate validates for R-b.
   - Procedure R, then base-apply (uploads the runtime archive). About 30 min.
2. B2 validation CNAME.
3. B9.1 upload: EMR artifacts, input S, the Hadoop config (P1) and the Spark template (P24). (Input L is not uploaded: L is dropped on EMR.)
4. B9.2, then the EMR-enable plan with the P7 delta check, then `base-apply --skip-runtime-archive`. Cluster WAITING in about 5 min.
5. B9.4 and B9.5 **run S** (75-min cap; r5.xlarge primary, ER heap 12g); pre-write record 2 (for a possible S retry) while it runs. **Operator step (a), rounding budget (review 2 finding 1; your answer "Accept, add steps"): write record 1 and submit S as soon as the cluster ID exists, with nothing else in between**, because the time from cluster creation to S submission counts against the retry budget in step 5a. Pre-write record 2 only after S is submitted.
5a. **EMR actuals, right after each S run** (your rule, 2026-11-16: "Record the EMR actuals right after each S run so the pre-R-b check uses real numbers, not the cap"). Run it after run S and again after the S retry:
   - `aws emr describe-cluster --region us-east-2 --cluster-id <j-id> --output json > <private file>` with the operator profile. Save it to a git-ignored private path, never committed: the output carries ARNs with the account ID. Note the UTC time the file was saved.
   - `scripts/run-bounded-pipeline.sh --record-actual --run-id <run id> --describe <private file> [--as-of-utc <UTC save time>]`. `--as-of-utc` is required while the cluster has not ended. The command records the run's measured EMR cost in the ledger and makes no cloud call (`scripts/run-bounded-pipeline.sh` lines 18, 67-70 and 124-126, re-read in the working tree 2026-11-16; part of the D3 infra change, committed in `f801d28` (pipeline-bundle review 1: APPROVE; the working tree carries a later one-line change to that script); `scripts/lib/budget.py` `ledger-record-actual`).
   - Write the recorded actual and the ledger cumulative in the session log. Gate 1 and the pre-R-b check use them.
   - **Retry admission condition (pipeline-bundle review 1, finding 1; cap 3.53 per your decision of 2026-11-16):** the actual is measured from the cluster's creation (boot included) and the ledger adds a pending 0.14 idle tail (900 s at 0.555/h), while the retry still reserves 0.84. After S's actual is recorded, the S retry is admitted only if S's measured cost is **<= 0.87** (3.53 - 1.68 - 0.84 - 0.14), about **94 min from cluster creation** at 0.555/h. If S's measured cost is above 0.87, the retry is **refused (fail-closed)** and the plan goes to the "S fails twice" fallback, step 7b (vectors from the local P6 S export). Do not edit the ledger to get around the refusal.
   - **Rounding budget (review 2 finding 1; your decision 2026-11-16, "Accept, add steps"; the cap stays 3.53):** every ledger term rounds up to the cent. With a **full 75-min S**, the retry is admitted only if the time from cluster creation to S submission, **plus the wait before `--record-actual`**, is **at most about 19 min**. Arithmetic: 75 + 20 = 95 min x 0.555/h = 0.87875, rounded up to 0.88, and 1.68 + 0.88 + 0.14 + 0.84 = **3.54 > 3.53**, so the retry is refused; at 94 min the cost is 0.8695, rounded up to 0.87, which just fits (3.53). The measured cold start is about 4-5 min (section 5.0), so this normally fits with a wide margin; the budget is lost only by delay. Two operator steps keep it: **(a)** write record 1 and submit S as soon as the cluster ID exists (step 5); **(b)** run `--record-actual` **immediately after an S failure, before anything else** (before downloading logs, before pre-writing record 2, before any diagnosis), because the measured cost runs to the UTC time of the saved describe file while the cluster is still up, so every minute of delay adds to it. The 94-min total is what counts: an S that fails earlier than 75 min leaves correspondingly more room than the 19 min.
6. **S retry, only if S failed** (P25 rule), submitted within 15 minutes of the failure (F20) on the same cluster, **and only if S's recorded measured cost is <= 0.87 (about 94 min from cluster creation; step 5a). Otherwise the retry is refused (fail-closed) and you go to step 7b.** The 0.87 limit has a rounding budget (step 5a): with a full 75-min S, creation to S submission plus the wait before `--record-actual` must be at most about 19 min; run `--record-actual` immediately after an S failure (operator step (b)). Then step 5a again. Fresh pipeline login in between; never start a run with less than 100 minutes of session left. **No run L on EMR** (dropped 2026-11-16; was "Run L, submitted within 15 minutes of S finishing").
7. **After S passes (laptop; formerly "while L runs"):**
   - download S's Spark export, its counters, rejects and results, and the Spark event-log summary (`SHA256SUMS`);
   - P6 render-only on S;
   - B8.6 **ingest about 10,000 vectors** with the loader role;
   - B8.7 **query smoke**, one sample per index. These need only S3 Vectors, the DynamoDB run ledger and the rag bucket, all created in stage a.
   - **Not run since 2026-11-16 (R-c dropped, option (i)); kept as a record:** (Only if R-c may follow) `StorageLoadMain --cache-only` (P16) loads the DynamoDB caches from S's export: about 2 h, at stage-a rates, no Neptune needed. **P38** logging applies to all these tools.
7b. **Fallback when the S retry also fails: vectors from the local P6 S run** (your 4a review answer 4, 2026-11-16: "S fails twice: don't drop R-b. Use the P6 local S export for chunks and vectors (same Voyage cap), load them, and run R-b. The report states that the vectors came from the local run."). L is already dropped by the P25 rule. Everything else in stage a and R-b stays the same.
   - **Feasibility (read-only, checked at HEAD `7a02de2` with `git show`; 2026-11-16): feasible with no code change, but time-conditional (see the clock condition below).**
     - The render takes any **local** Spark export directory: `EmbeddingManifestMain` accepts `--export`, `--work-manifest`, `--config`, `--manifest-output` and `--report` (`modules/rag/.../EmbeddingManifestMain.scala:15`) and loads the export with `Phase6EmbeddingSource.load(Path.of(--export), …)` (`:61-62`). Session 1 already rendered from a local export (`phase-14-live-session.md:1136`).
     - The export must hold `load-manifests/s3.json` and `load-manifests/s3vectors.json` and the tables `semantic-summaries`, `nodes/type=topic` and `nodes/type=institution` (`modules/storage/.../Phase6EmbeddingSource.scala:66`, `:76`, `:98`). The reader also checks each table against its manifest (`sortedRowsSha256` and the other fields, `:108-112`) and reads the qualifications (`:121`), so the tree must be kept whole and unmodified.
     - The ingest does **not** need the export in S3. Each `textS3Uri` must start with `s3://<textBucket>/<textPrefix>/versions/` (`LiveEmbeddingIngestMain.scala:255`), and the ingest writes each chunk's text object there itself (`modules/storage/.../EmbeddingManifest.scala:436`). `textBucket` is the rag bucket and `textPrefix` is `embedding-text` (`docs/agent-runs/phase-14/evidence/14b/replan/14c-templates.md:9`, `:24-25`). `scripts/upload-slice.sh` (runbook B8.1, `phase-14-live-session.md:1045-1046`) is for the graph-load path and is not needed.
     - **Schema:** the P6 harness runs the same chain with the same templates as EMR (P6 row: "same templates"), so the P6 S export has the EMR export's schema by construction, **provided P6 uses the frozen session commit, the same job JAR and the same Spark template (P24)**. Bytes will differ (run ID, timestamps). Not verified by comparison: no EMR S export exists yet.
     - **Config changes:** none to `render-config.json` (the same file and P26 settings as the planned stage-a render) or to `live-config.json` (same text bucket, prefix, vector bucket and caps). In `ingest-approval.json` only `manifestSha256` changes (the new manifest; rule at `phase-14-live-session.md:1139`), plus a fresh expiry. The caps stay at `vectorCap` 10000, `concurrencyCap` 2, `embeddingCallCap` 20000 and `dollarCapUsd` 0.25 (`14c-templates.md:74`): **the same Voyage cap**.
   - **Clock condition (estimate):** the fallback render, ingest and B8.7 smoke must finish, and gate 1 and the pre-R-b check must pass, by about **12:15 CST (18:15Z)**. That keeps `T_N0` at or before about 12:20 CST, so that the destroy target (`T_N0` + 5 h 15 min) plus pass 1 (18 min 27 s in Session 1), pass 2 with its listing (about 7 min in Session 1, 02:01:09Z-02:07:45Z), IAM window 2 (about 45 min, 6.7) and C5b-C9 (about 15 min, estimate) end by the 19:00 CST hard stop. If two full S runs (each up to the 75-minute cap) end at about 11:30 CST, about 45 min remain. 10,000 vectors would then need about 5 vectors/s, against Session 1's unbatched 0.614 vectors/s; it depends on the P26 batched throughput, which has not been measured live. **If it does not fit, R-b is skipped unless you record a new decision.** Two options would need your decision: start the fallback ingest in parallel with the S retry, or render fewer vectors.
   - **Commands** (the B8.6 and B8.7 commands, unchanged except `EXPORT`; `$S2WORK` is the same work directory as the planned stage-a B8.6 render, as `target/phase14/14c-work/` was in Session 1):
     1. Check the retained export (paths set by the P6 harness; see the P6 row): `cd "target/phase15/p6/size-S/run:b8df1ae6-a66e-4e6e-84c7-6cb3169fd0ae" && shasum -a 256 -c SHA256SUMS`, which must exit 0 (the paths in `SHA256SUMS` are relative, so the check must run inside the directory). Then confirm that the commit recorded in its provenance file equals `git rev-parse HEAD`.
     2. `EXPORT=<P6 S retention dir>/spark` (the retained export, in place of S's downloaded EMR export).
     3. Render (`phase-14-live-session.md:1134-1138`): `sbt -batch "rag / Compile / runMain edu.uic.cs441.scholarchain.rag.EmbeddingManifestMain --export $EXPORT --work-manifest $EXPORT/load-manifests/s3vectors.json --config $S2WORK/render-config.json --manifest-output $S2WORK/real-model-manifest.json --report $S2WORK/render-report.json"`. Success: `mode` `render-only`, `embeddingCalls` 0 (`EmbeddingManifestMain.scala:78`), and `sourceRunId` equal to the P6 run ID (`:81`).
     4. Update `ingest-approval.json` (`manifestSha256`, expiry) as in `phase-14-live-session.md:1139`.
     5. Voyage key in the one ingest shell only (`phase-14-live-session.md:1140`; set +x; `unset` afterwards).
     6. Ingest (`phase-14-live-session.md:1141-1144`), unchanged: `LiveEmbeddingIngestMain --config $S2WORK/live-config.json --manifest $S2WORK/real-model-manifest.json --approval $S2WORK/ingest-approval.json --report <evidence>/ingest-report.json --run-id ${RUN_PREFIX}-ingest`.
     7. B8.7 query smoke (`phase-14-live-session.md:1150-1153`), unchanged.
   - **Report wording:** "vectors derived from the local P6 S run". Give the P6 run ID (the render report's `sourceRunId`), the sha256 of the retained `SHA256SUMS`, the commit, and the two failed EMR S runs with their logs. Stage a's EMR evidence is then the two failed runs; there is no EMR S or L output.
8. B9.8 confirm `TERMINATED`.

**Utilization evidence without Container Insights** (record for each size; read with your read-only admin console or CLI):

- `AWS/ElasticMapReduce` 5-minute metrics: `YARNMemoryAvailablePercentage`, `ContainerAllocated`, `ContainerPending`, `AppsRunning`, `MemoryAllocatedMB`, `CoreNodesRunning`.
- `AWS/EC2` `CPUUtilization` for the two nodes (basic 5-minute monitoring).
- Step start and end times from the run log (`describe-step`).
- Hadoop job counters (including CPU and GC time, spilled records) in the copied-out counters files.
- Spark stage durations, shuffle read and write, and executor counts from `event-log-summary.json`.
- Note the 5-minute granularity: run S gives only about 6-8 datapoints.

**Demo:** record items 9, 10 (S on EMR; L from local evidence), 12 (the ingest run-ledger record, read with the reader role) and 13 (the query smoke) live.

**Duration (estimate):** the schedule keeps gate 1 at 10:45 CST, because the vector ingest needs the time; L no longer runs. EMR cost planned before tax at 0.58 per cluster-hour: S about 0.35 (0.60 h), boot and idle about 0.21 (0.36 h), total 0.56; cap 1.93 (S and its retry, 3.33 h). (Was: about 3.5 h to the end of L; S about 0.30, L about 0.55, boot and idle about 0.18 at 0.50.)

**Stop conditions:**

- S fails at any step: **retry S once and drop L** as a stated limitation (your P25 rule, 2026-11-16: "S first; if S succeeds the next run is L; if S fails, retry S once and drop L as a stated limitation. If L fails, no retry: report it with logs."). **If the S retry also fails:** use the fallback in step 7b (vectors from the local P6 S run, same Voyage cap), then continue to gate 1; your 4a review answer 4 (2026-11-16). Superseded the same day: "stop, report with logs, no R-b" (a consequence drawn from the P25 rule). Earlier rule, kept as a record: "stop and report; no L and no R-b".
- L: not run on EMR (dropped 2026-11-16, P25 rule). The former rule was "L fails or hits its cap: keep S, record L as failed with logs, no retry".
- `AccessDenied`.
- Ingest `rejected > 0`, or the query smoke fails: report it, and continue to the go/no-go.

> **GO / NO-GO for the elasticity extension R-b (write the UTC time and the three bills)**
> - [ ] Run S (or its retry) PASS, with the EMR actual recorded (step 5a), **or** S failed twice and the step 7b fallback vectors (local P6 S run) are ingested, by about 12:15 CST; cluster `TERMINATED`; downloads hashed
> - [ ] Vectors: written count recorded, `rejected: 0`; query smoke exit 0 with verified pointers
> - [ ] **Gate 1, money (clock-based, because billing lags 8-24 h):** estimate stage-a spend `X_a` = hours x 0.063 + **the recorded EMR actuals of the Session 2 runs** (step 5a: the ledger cumulative minus Session 1's 1.68) + 0.10 (was measured cluster-hours x 0.50) (the R-c cache load, +0.22, is no longer run: R-c dropped). R-b requires `X_a <= 7.17 - E_b - 0.75` (floor 2, option (i)), where 0.75 is the Route 53 contingency (0.50) plus the remaining stage-a-level hours (0.25):
>   - with Neptune at min 1 / max 2.5 NCU (P34 not possible) and the 5.8 h Neptune hard stop: `E_b = 3.57`, threshold **2.85** (R-b's Neptune cap 5.8 h x 0.402/h = 2.33; `E_b` includes the S3 Vectors query cap of 0.53 and Voyage cache misses 0.02, section 6.3a). Planned `X_a` about 0.88 **passes by 1.97** (S only on EMR at 0.58 per cluster-hour; 1.35 and 1.50 before L was dropped);
>   - history: amended 2026-11-15, first 2.11 / 3.31, then 2.61 / 2.81 with the 300,000 backstop, then 2.36 / 3.06 with the required per-level limits (at the 1-NCU rate, 0.1608 per NCU-hour, floor 3); amended 2026-11-16 (P34 impossible) to 4.05 / 1.37 (7.0 h at 0.402/h, floor 3; planned `X_a` 1.57 with the cache load failed by 0.20); amended 2026-11-16 (option (i)) to 3.57 / 2.85 (floor 2, 5.8 h). The former "without P34" threshold 2.11 (`E_b = 3.31`, 0.297/h through the cap hours) is superseded, because caps now use the 0.402/h ceiling.
> - [ ] **Pre-R-b check (option (i), your condition 3):** spend to date (`C11_TOTAL_USD` as last read, **with its read time**, plus the clock-based estimate since that read) + R-b cap (`E_b` = 3.57) **<= 23.00** (floor 2; your 4a review answer 3, 2026-11-16: "the pre-R-b check is spend to date + 3.57 ≤ 23.00 (floor 2), not 25.00. Above 23.00, R-b is skipped unless I record a new decision."); otherwise skip R-b and go to cleanup (5.5), unless you record a new decision. The EMR part of spend to date is the recorded actual (step 5a), not the cap. Planned: 15.83 + 0.88 + 3.57 = 20.28 (margin 2.72; 20.75 before L was dropped). Both gate 1 and this check must pass. (Was `<= 25.00` until the 4a review.)
>   - `E_b` does not depend on `r_S2`: the required P42 per-level limits (198,600 requests) bound the S3 Vectors queries whatever the rate limit is.
> - [ ] Time: at least 6 h left before the hard stop
> - [ ] P35 acceptance met; the `query_requests_per_target_target` value (**3000**, your decision of 2026-11-16, set from the live 200 ms estimate, not the local rule) is in the runtime tfvars; the Session 2 rate-limit value `r_S2` (**3500**, at least 2 x the measured local peak of 1,737 served requests per second per task at level 50; burst `b_S2` **7000**, 2 x `r_S2`) is recorded, and P35 showed zero 429s at every level (observed: 0 of 198,750); the P42 manifest carries the required per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000
>
> **GO:** R-b. **NO-GO:** go straight to cleanup (5.5). R0 alone is then the session.

### 5.3 R-b: small elasticity experiment on the production runtime (Neptune at min 1 / max 2.5 NCU, empty graph, semantic load)

> **Neptune hard stop (R-b option (i), decided 2026-11-16; your condition 2: "The 5.8 h Neptune window is a hard stop: run the R-b load early in the window. At 5.8 h, destroy Neptune whether R-b has finished or not, and keep whatever elasticity data was captured. Put the clock times in the runbook.")** All times CST with UTC; planned times assume the schedule in 6.7.
>
> | Clock point | Rule | Planned |
> |---|---|---|
> | `T_N0` | The actual start of the Neptune base-apply (step 1), **written in the session log** | 10:50 CST (16:50Z) |
> | Load start | Start the R-b load **immediately after the B6 smoke passes** (step 4); the failure example (step 5) comes after the load collection | 12:45 CST (18:45Z) |
> | Latest full-variant start | Destroy target - pre-destroy duration (about 50 min) - full variant (about 50 min) = `T_N0` + 3 h 35 min | 14:25 CST (20:25Z) |
> | Latest load start (any) | Destroy target - about 50 min - short variant (37 min) = `T_N0` + 3 h 48 min | 14:38 CST (20:38Z) |
> | Latest failure-example start | It must end (about 20 min) before the pre-destroy steps start; skip it otherwise | 14:55 CST (20:55Z) |
> | Latest pre-destroy start | B13, C2 cleanup-prepare plan and apply, C3 pass-1 listing (about 50 min, section 5.5) start by `T_N0` + 4 h 25 min | 15:15 CST (21:15Z) |
> | Destroy target | Neptune destroy (the confirmed C3 destroy pass, section 5.5) issued at `T_N0` + 5 h 15 min | 16:05 CST (22:05Z) |
> | **Absolute hard stop** | Neptune destroy issued **no later than `T_N0` + 5 h 30 min, whether R-b has finished or not**, so that about 18 min of deletion ends by 5.8 h after `T_N0` even if billing starts at `T_N0`. Keep whatever elasticity data was captured; the report states what was cut | 16:20 CST (22:20Z) |
> | Session hard stop | Unchanged | 19:00 CST (01:00Z Nov 20) |
>
> Planned Neptune window 5.0 h, hard cap 5.8 h (R-b Neptune cap 5.8 x 0.402 = 2.33). **The deletion time is an estimate:** about 18 min, from Session 1's confirmed destroy pass 1, which took 18 min 27 s in total (01:42:13Z to 02:00:40Z on 2026-11-15, `cleanup-pass-1.log`) and deleted Neptune among 247 resources; Neptune's own deletion time was not separated. The planned load start (12:45) leaves **100 min** before the latest full-variant start (14:25), more than 60 min.
>
> Amended 2026-11-16 (conservative clock): the first option (i) clock was target `T_N0` + 5 h 30 min (16:20 CST), absolute `T_N0` + 5 h 48 min (16:38 CST) and latest new load start `T_N0` + 4 h 50 min (15:40 CST). It held only if billing started at least about 18 min after `T_N0`, and it left about 3 min for the pre-destroy steps.

1. Write `T_N0` (UTC) in the session log when the Neptune base-apply starts. Base plan with `neptune_enabled = true`, `neptune_min_ncu = 1` and `neptune_max_ncu = 2.5` (unchanged from Session 1; the guard refuses max 1, so P34 is not possible) and `emr_config.enabled = false` (Neptune creates plus the reviewed `module.emr` deletes; P7). Procedure R, then `base-apply --skip-runtime-archive`. About 50 min; push (B3) in parallel.
2. B3b keys (if not done), then B4 runtime plan and runtime-apply:
   - no `neptune_tunnel_enabled = true`: it was needed only for R-c, which is dropped (option (i), 2026-11-16);
   - `dashboard_enabled = true` (P9); Container Insights off;
   - `service_capacity` query-api and semantic-service `min 1, max 2`;
   - `cpu_target_percent` 60 (unchanged);
   - `query_requests_per_target_target` = **3000** (P41; your P35 decision of 2026-11-16, a deviation from the local rule; set by you in the private tfvars);
   - the query-api rate-limit override from P35, through the P41 root variables: `query_semantic_rate_limit_per_second` = `r_S2` = **3500** and `query_semantic_rate_limit_burst` = `b_S2` = 2 x `r_S2` = **7000** (set by you in the private tfvars; they set `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` and `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` on query-api in aws mode; left null, the P40 code defaults 50 and 100 apply).
   - About 45 min.
3. **P37 (N4):** digest check. B5 `api` CNAME; B6 smoke.
4. **Elasticity (B10, adapted), started immediately after the B6 smoke passes** (option (i): the load runs early in the Neptune window; latest full-variant start 14:25 CST, latest load start of any kind 14:38 CST, as in the clock table above):
   - start the T3 poll;
   - open the dashboard;
   - `loadgen.py run --manifest <P42 semantic manifest> --questions-file <fixed semantic questions>` (a fixed set of about 100-200 distinct questions, sent once each in the P42 warm-up pass before the ramp), without `--node-ids-file`, `--evidence-ids-file` or `--llm`.
   - Each semantic request does real work: query-api forwards to semantic-service, which reads the cached query embedding and queries one S3 Vectors index (the one named by `SCHOLARCHAIN_SEMANTIC_INDEX`) of the about-10,000 R0 vectors. Voyage is called at most once per distinct question per semantic-service task (section 6.3a). A request that gets 429 from the rate limiter never reaches semantic-service, Voyage or S3 Vectors.
   - Wait at least 25 quiet minutes.
   - Collect, all in UTC: scaling activities; ALB `RequestCountPerTarget`, `HealthyHostCount`, `TargetResponseTime` p50/p95/p99 and 5XX; `AWS/ECS` CPU and memory for query-api and semantic-service; Neptune `ServerlessDatabaseCapacity`; from query-api's `/metrics` (through the ALB), the 429 counter `api_rate_limited_total`.
   - **Review finding R2 (P40 review 1; raised 2026-11-16, decided 2026-11-16; for P42 and this runbook):** in aws mode the `embedding_cache_*` counters exist only on **semantic-service's** `/metrics` (`AwsComposition.scala` lines 256-257, the semantic role), and the ALB sends every path to query-api (F25). The cache hit and miss counters therefore **cannot be read through the ALB**, so the claim "Voyage calls <= distinct questions per semantic-service task" has no source in this collection list. No mechanism to read them exists today. **Decided 2026-11-16 (your P41-D follow-up answer (a)):** "I'll read the Voyage usage page after the session and note the read time. Report it as the total for the session window, not per task, and compare it with the size of the fixed question set (misses ≤ distinct questions). If the page doesn't separate the window, mark it "unverified"." The rule as applied:
     - after the session, you read the Voyage usage page and record the read time;
     - the reported figure is the **total for the R-b load window only, not per task** (your second follow-up answer 2(a), 2026-11-16: not the whole Session 2 day, because the stage-a ingest and the B8.7 query smoke also call Voyage);
     - the reported check compares that total with the size of the fixed question set (**misses ≤ distinct questions**);
     - the section 6.3a caveats apply (your second follow-up answer 1(a), 2026-11-16): a total up to about **4 × distinct questions** is explained by semantic-service task starts (restarts or a second scale-out), and a cold task's uncoalesced concurrent misses can add a few duplicate calls. Only a total clearly above that would point to a cache problem;
     - if the page cannot isolate the R-b load window, the figure is reported as **"unverified"**.
     - Nothing has been measured.
   - **Measurement rule (your answer, 2026-11-15):** report the 429 count per level separately from the successful responses, and exclude 429s from every latency and throughput figure. Note that ALB `RequestCount`, `RequestCountPerTarget` and `TargetResponseTime` include 429 replies; the load generator's per-level figures for successful responses are the primary latency and throughput figures. **Scaling analysis (your Q16 answer, 2026-11-15):** `r_S2` is set from P35 so that no level is throttled. Any 429 in R-b is reported per level. The analysis states that scale-out and scale-in were driven by **served** requests: the ALB request counts include 429 replies, so with zero 429s they equal the served requests. If any 429 occurred, the analysis gives its count per level and its share of `RequestCountPerTarget` in the minutes around each scaling activity.
   - About 50 min (about 37 min with a short variant).
5. **Failure and recovery (P11 option (i)), after the load collection** and only if it can start by 14:55 CST (it must end before the pre-destroy steps start at 15:15 CST): stop one query-api task with the narrowly granted role. Record service events, the replacement task, healthy-host recovery and `healthz`/`readyz` passing again, with timestamps. About 20 min.
6. Record demo items 18-21.

The Neptune window is about 5 h planned, with the 5.8 h hard stop above; the runtime is up about 3.5 h. (Before option (i): about 7.5 h of Neptune and 6 h of runtime with R-c, which is now dropped.)

### 5.4 R-c: dropped (option (i), 2026-11-16); kept as a record

**Dropped (option (i), 2026-11-16).** R-c is not run. The 5.8 h Neptune hard stop (section 5.3) cannot hold R-c's Neptune window (about 7.5 h with R-b), and gate 2 fails on planned figures anyway (planned `X_spent` about 3.47 against 2.36). The report uses the Session 1 results (0/14 and 0/10) plus the offline P3 and P4 proofs. The rest of this section is the former R-c design with its 2026-11-16 recomputed figures, kept as a record; none of it is a live step.

Former title: R-c (optional): load the 10.5k graph and rerun the 24 direct-coauthor and path questions.

**Entry:**

- P36 (N1) and P43 passed locally.
- The DynamoDB cache was loaded during stage a with `StorageLoadMain --cache-only` (P16) from S's EMR export: about 2 h at stage-a rates, overlapping run L and the vector ingest. R-c therefore needs **only the Neptune graph load**, not the about-2 h DynamoDB load.
- The tunnel task definition exists (step 2 above).
- Gate 2 passes.

> **GATE 2 (not applied since 2026-11-16: R-c dropped, option (i); record only) (money and clock; write the UTC time, the three bills and the Neptune capacity read from CloudWatch)**
> - [ ] **Tax-0 column:** `15.83 + X_spent + 2.63 + 0.68 + 0.50 <= 22.00`, that is **`X_spent <= 2.36`** (amended 2026-11-16, P34 impossible; was `+ 2.26`, `X_spent <= 2.73`).
>   - `X_spent` = the clock-based estimate of everything spent in Session 2 so far: stage a plus R-b, with Neptune at the measured `ServerlessDatabaseCapacity` x 0.1608 per NCU-hour.
>   - 2.63 = R-c cap (below); 0.68 = about 1.5 h of cleanup at 0.453/h; 0.50 = Route 53 contingency.
> - (The x 1.11 check line was dropped 2026-11-16, your tax decision; old values in the section 6.4 history line.)
> - [ ] **Clock:** R-c starts **no later than 14:15 CST**; if Neptune has not reached `LOAD_COMPLETED` by **15:45 CST**, abort R-c and go to cleanup; answers done by **16:45 CST**.
>
> **NO-GO:** R-c is dropped. The report records why (money gate, clock, or a prerequisite missing) and uses the Session 1 results (0/14 and 0/10) plus the offline P3 and P4 proofs.

**Steps:**

1. Fresh loader login.
2. B7 tunnel, with keep-alive traffic on the tunnel.
3. B8.3 **`--graph-only`** load of S's export. Session 1: 3,540 s at max 2.5 NCU, including about 19 min of local validation. Session 2 runs at the same min 1 / max 2.5 NCU; the 15:45 cutoff covers a slower load (for example a tunnel retry).
4. B8.2 runtime artifact; B8.4 pointer runtime-apply (rolls query-api); **P37** digest check.
5. Warm-up queries until `readyz` and a warm-up answer succeed (cold artifact load 28-45 s; first query after idle can return 504).
6. `llm_budget.py` transfer of 28 answers from bucket 15b (your approval line), then `eval16b.py run` in subset mode (14 direct-coauthor + 10 path).
7. Record demo items 11, 14, 15 and 16 live.
8. Stop the tunnel.

**R-c cost (tax 0):**

| Item | Planned | Cap |
|---|---:|---:|
| Neptune 2.5 h at the planning rate 0.297/h (Session 1 average about 1.85 NCU, P32); cap 3.5 h at the 2.5-NCU ceiling, 2.5 x 0.1608 per NCU-hour = 0.402/h | 0.74 | 1.41 (at 0.402/h) |
| Runtime increment (0.093/h) | 0.23 | 0.33 |
| Stage-a-level hours | 0.16 | 0.22 |
| DynamoDB cache load (in stage a) | 0.22 | 0.22 |
| Tunnel task | 0.02 | 0.05 |
| 28 answers x 0.001365 (`claude-haiku-5-5`, ledger estimate) | 0.04 | 0.10 |
| Neptune I/O allowance for the bulk load | — | 0.30 |
| **Total** | **1.41** | **2.63** |

Amended 2026-11-16 (P34 impossible): the Neptune row was 0.40 / 1.04 (2.5 h at the 1-NCU rate 0.1608/h; cap 3.5 h at 0.297/h) and the total 1.07 / 2.26.

**R-c risks:**

- Cold warm-up and first-query 504 (P14, warm-up queries).
- The Neptune load fails on a tunnel drop (Session 1: after 8,429 s). Keep-alive traffic; one `--graph-only` retry only if the clock allows.
- The fixed questions may still abstain; report the result as measured.
- An ID mismatch between the questions and the EMR export (P10).

### 5.5 Archive, inventories, destroy (always)

**Order and Neptune clock (option (i), 2026-11-16).** The runtime and Neptune are deleted in the same confirmed C3 destroy pass; Neptune cannot be removed first while the runtime exists, because the `phase12b.tf:42` precondition requires `neptune_enabled` whenever the runtime is enabled. "Neptune destroy issued" therefore means **the confirmed C3 pass 1 starts** (in Session 1, Neptune was deleted in destroy pass 1, section 6.1a). It must start by `T_N0` + 5 h 15 min (target, planned 16:05 CST / 22:05Z) and **no later than `T_N0` + 5 h 30 min** (absolute, planned 16:20 CST / 22:20Z), section 5.3. Steps 1-2, C2 (cleanup-prepare plan and apply) and the C3 pass-1 listing must be finished before that time. C1 (tunnel stop) does not apply: R-c is dropped and there is no tunnel.

**Pre-destroy duration: about 50 min** (part measured in Session 1, part estimate; Session 1 cleanup logs under `target/phase14/evidence/14b/` (git-ignored)):

| Step | Session 1 | Used here |
|---|---|---|
| B13.1 facts (outputs, KMS ARN, state sha) and any remaining R-b downloads | Not measured as a block: B13.1 and B13.2 ran at about 21:28Z on 2026-11-14 (`state-sha-before-cleanup.log` file time), hours before cleanup; B13.3 was deferred offline. Session 2 downloads the EMR outputs during stage a (5.2 step 7) | about 10 min (**estimate**) |
| C2 cleanup-prepare plan → confirmed C3 pass 1 starts (prepare plan, Procedure R record, dry run, prepare apply, fresh login, C3 listing with the before-inventory, confirm) | **Measured 37 min 49 s:** prepare plan starts 01:04:24Z (`cleanup-prepare-plan.log`), dry run 01:10:33Z, apply 01:10:36Z-01:11:15Z (`cleanup-prepare.log`), listing 1 01:27:27Z-01:33:05Z (`cleanup-list-1.log`, refused by policy), state rm of the guard after your 01:34:05Z decision, listing 1b 01:35:10Z-01:40:53Z (`cleanup-list-1b.log`), confirmed pass 1 starts 01:42:13Z (`cleanup-pass-1.log`). It includes about 7.7 min of policy detour (listing 1 to listing 1b) that P5 should remove, and a gap of 16 min 12 s between the apply and listing 1 whose cause is not recorded | about 38 min (measured, kept whole as a margin) |
| Margin | — | about 2 min |
| **Total** | | **about 50 min** |

- Planned: cleanup starts at about 14:15 CST (20:15Z) after R-b (11:00 CST if NO-GO at gate 1), so pass 1 starts at about 15:05 CST, an hour before the target.
- The latest load starts in section 5.3 (14:25 CST full variant, 14:38 CST short variant) subtract this 50 min from the 16:05 CST target.

1. B13 archive with checksums.
2. Before-cleanup inventory.
3. C1-C3 two-pass destroy (P5); the confirmed pass 1 meets the Neptune clock above.
4. **IAM window 2:** C4 operator roles off, C5 secrets, **then P39 (N9): destroy the deployer stack** from a reviewed plan. Record the window's open and close times.
5. C5b key revocation with UTC times.
6. C6-C9: the after-cleanup inventory in a private window as the IAM user; **never run `aws login` while signed in as root**. Also confirm no `scholarchain-deployer` role remains.
7. Next day: C11 and C11b (three bills).

About 1.5-2 h. **Finish within 12 hours of the first base-apply**, so the Cloud Map hosted zone is not charged. The session hard stop stays 19:00 CST (01:00Z).

## 6. Budget (recalibrated with real Session 1 billing, provisional)

All amounts are USD.

**Billing input (human-supplied, 2026-11-15):** Cost Explorer for Nov 1-15 2026, daily, by service, credits excluded, **before tax**. It is provisional because Nov 15 may still be filling in. The total is **15.75** (Nov 4 0.35, Nov 12 0.01, Nov 13 2.31, Nov 14 12.16, Nov 15 0.92); the Ohio region accounts for 15.25 and Route 53 for 0.50.

| Service | Total | Nov 13 | Nov 14 | Nov 15 |
|---|---:|---:|---:|---:|
| Neptune | 9.05 | 1.30 | 7.12 | 0.63 |
| ECS | 1.78 | 0.23 | 1.45 | 0.10 |
| EC2-Other (NAT gateway hours and data, EBS) | 1.72 | 0.32 | 1.13 | 0.09 |
| EC2-Instances (Nov 14 = EMR nodes; 0.12 on Nov 4) | 0.75 | 0.00 | 0.63 | 0.00 |
| ELB | 0.68 | 0.09 | 0.54 | 0.05 |
| Route 53 (hosted zone) | 0.50 | | 0.50 | |
| VPC (public IPv4) | 0.46 | 0.07 | 0.36 | 0.03 |
| DynamoDB | 0.22 | 0.21 | 0.01 | 0.00 |
| S3 | 0.22 | | | |
| Secrets Manager | 0.15 | | | |
| Elastic MapReduce (service fee; 0.01 on Nov 4) | 0.14 | | 0.13 | |
| KMS 0.05, EFS 0.03, ECR 0.01; Glue, SNS, SQS, ACM, Step Functions, CloudWatch 0.00 | 0.09 | | | |

**Tax (human-supplied, Bills page, November; decided 2026-11-16):**

- Net charges are USD 0.00 after credits, and "Taxes by service" shows USD 0.00 (no taxed service). The page notes that estimates exclude taxes unless listed.
- **Usage before credits (15.75) counts toward the USD 25 cap**, but tax is currently 0 because credits cover the charges.
- **Your tax decision (2026-11-16), verbatim:** "the portion of your bill deducted/covered by AWS credits is not taxed. Since they are credits so tax is 0". The plan therefore uses **tax 0 (factor 1.00) on new spend**. This holds **while AWS credits cover the spend**; the pre-R-b check (spend to date + 3.57 <= 23.00) stays as the firm-limit control.
- History: until 2026-11-16 the plan showed two columns, A (tax 0, factor 1.00) and B (conservative 11%, factor 1.11), and kept B pending the tax read. Column B was dropped 2026-11-16, your tax decision (old values in the section 6.4 history line).

**Anthropic:** about 0.075 (ledger estimate, 55 answers; the console showed 0.00 at the Nov 14 read). **Voyage:** 0.

### 6.1 Empirical rates (derivation)

Nov 14 (UTC) is the one full day on which the full stack ran for all 24 hours. Remove that day's one-off items: EMR nodes 0.63, EMR fee 0.13, Route 53 0.50 and EFS about 0.03 (EMR staging). What remains is the all-in idle cost of the full stack.

| Component (Nov 14, per hour, before tax) | Derivation | USD/h | Modeled before |
|---|---|---:|---:|
| Neptune | 7.12 / 24 | **0.297** | 0.1608 (1 NCU). The observed rate is about 1.85 times the 1-NCU model: capacity above 1 NCU and/or storage and I/O are included |
| ECS (Fargate, 4 tasks) | 1.45 / 24 | 0.060 | 0.0583 |
| EC2-Other (NAT gateway hours and data processing, EBS) | 1.13 / 24 | 0.047 | 0.045 (NAT) |
| ELB | 0.54 / 24 | 0.023 | 0.0405 incl. 2 IPv4 (the IPv4 charge shows under VPC) |
| VPC (3 public IPv4: NAT EIP + 2 ALB) | 0.36 / 24 | 0.015 | 0.005 x 3 |
| Residual (S3, Secrets, KMS, ECR, small items) | (10.87 - 10.60) / 24 | 0.011 | about 0.005 |
| **Full-stack all-in, before tax** | 10.87 / 24 | **0.453** | 0.3146 |

**Stage-a rate (S3 + NAT + VPC, no Neptune, ECS or ALB), before tax:** EC2-Other 0.047 + one public IPv4 0.005 + residual 0.011 = **0.063 per hour**.

**EMR:**

- Nov 14 had EC2-Instances 0.63 and an EMR fee of 0.13 for five cluster starts. Dividing by the modeled rates (EC2 0.384 and EMR 0.096 per cluster-hour) gives about 1.4-1.6 cluster-hours.
- That confirms the model rate of 0.48 per cluster-hour. Adding about 0.02 for EBS, this plan used **0.50 per cluster-hour** until 2026-11-16.
- **D3 (your decision, 2026-11-16):** r5.xlarge primary (EC2 0.252 + EMR 0.063 = 0.315/h) and m5.xlarge core (EC2 0.192 + EMR 0.048 = 0.240/h), so the model rate is 0.555 per cluster-hour (AWS price lists read by the coordinator 2026-11-16). By the same method (model rate plus about 0.02 for EBS, here 0.575, rounded up to the cent), this plan uses **0.58 per cluster-hour**.
- The EMR service fee is small; EC2 is most of the cost.

**One-off items (before tax):**

- Route 53 hosted zone 0.50. The Cloud Map namespace is created at base-apply; this is free if it is destroyed within 12 hours of creation (Route 53 pricing page, 2026-11-15).
- DynamoDB full cache load (166,088 writes) about 0.22 (Nov 13).
- S3 storage of EMR outputs plus download egress about 0.10 (estimate).

| Rate | Tax 0 |
|---|---:|
| Full stack, per hour | **0.453** |
| Stage a without cluster, per hour | 0.063 |
| EMR cluster (r5.xlarge primary + m5.xlarge core + EBS), per hour | 0.58 (0.50 for 2 x m5.xlarge before 2026-11-16) |

The Anthropic and Voyage rates are as before: `claude-haiku-5-5` estimate 0.001365 per answer (`load-profile.v1.json`); Voyage 0 inside the first 200M tokens (repository records, not re-checked against Voyage's page; about 10,000 vectors is about 2.25M tokens).

### 6.1a What made Nov 14 expensive (preliminary; you asked for this before P34)

From the provisional bill and the Session 1 timeline (no usage-type breakdown yet):

| Day (UTC) | Neptune charge | Hours the cluster existed | Rate | What happened |
|---|---:|---:|---:|---|
| Nov 13 | 1.30 | about 6 (created about 18:00Z) | **about 0.22/h** | Cluster creation; the graph was **empty all day**. The 21:37Z load never submitted a Neptune job. Only readiness probes touched Neptune. |
| Nov 14 | 7.12 | 24 | **0.297/h** | The graph-only bulk load (about 01:59-02:58Z, 328,967 edges), then the loaded graph serving smokes, the 16B evaluation and the demo |
| Nov 15 | 0.63 | about 1.8 | about 0.35/h | Cleanup-prepare modifications, then deletion in destroy pass 1 |

**Finding (P32, done 2026-11-15):** Cost Explorer for Neptune, Nov 13-15, by usage type (credits excluded):

| Usage type | USD |
|---|---:|
| ServerlessUsage | **9.05** |
| BackupUsage | 0.00 |
| StorageIOUsage | 0.00 |
| StorageUsage | 0.00 |

- **All Neptune cost was serverless capacity:** 9.05 / 0.1608 per NCU-hour = about 56 NCU-hours over about 32 h, an **average of about 1.8 NCU**.
- By day:

| Day | NCU-hours | Hours | Average NCU | Note |
|---|---:|---:|---:|---|
| Nov 13 | about 8.1 | about 6 | about 1.35 | graph still empty |
| Nov 14 | about 44.3 | 24 | about 1.85 | |

- The cluster scaled above 1 NCU, already with an empty graph, and **did not return to 1**. The one-hour bulk load explains at most about 0.24 of the Nov 14 excess; the rest is sustained capacity.

**Fix: P34 (max 1 NCU): not possible (2026-11-16).**

- The planned fix was to cap serverless capacity at 1 NCU, so that Neptune would bill at most 0.1608/h. AWS does not allow it: the smallest maximum capacity of Neptune Serverless is **2.5 NCU** (Amazon Neptune User Guide, read by the infra-engineer 2026-11-16; section 2). Your decision (2026-11-16): "P34 as planned is impossible. Set min 1 / max 2.5 NCU."
- Capacity therefore stays **min 1 / max 2.5 NCU**, the Session 1 configuration. No Terraform change: the `phase12b.tf` guard already requires max exactly 2.5.
- **Rates used from now on** (storage, I/O and backup were 0 at this data size, so capacity is the whole Neptune cost):
  - **ceiling:** 2.5 NCU x 0.1608 per NCU-hour = **0.402/h**, used for every cap and for `E_b`;
  - **planning rate:** the observed **0.297/h** (Nov 14, about 1.85 NCU on average, P32), because the same min 1 / max 2.5 configuration ran in Session 1;
  - **low scenario:** 0.22/h (Nov 13, about 1.35 NCU, empty graph), shown in 6.4 for comparison only.
- R-c's graph-only load and its 24 answers run at the same max 2.5 NCU as Session 1 (load 3,540 s; answer latencies 2-6 s), so there is no capacity-related slowdown to plan for.
- Amended 2026-11-16 (P34 impossible): before this, every planned figure and every gate threshold used the 1-NCU rate 0.1608/h, and the 0.22/h and 0.297/h rows in 6.4 applied only to a session run without P34.

### 6.2 Firm USD 25: session cap by floor

**Budget alerts (P0, your answers 2026-11-15):**

- Actual-spend alerts at USD 18, 20 and 22 against the USD 25 limit (period 2026-10-01 to 2027-01-01). They measure **AWS spend before credits and refunds**, the same basis as the 15.75 in Cost Explorer.
- The alerts are e-mails only and lag 8-24 h; the gates in this plan do the protecting.
- **The AWS budget covers AWS only.** Anthropic and Voyage are tracked in the LLM ledger and in the combined `C11_TOTAL_USD`, and every cap and gate here uses the **combined** total.
- **Where the alert lines fall (recomputed 2026-11-15, tax-0 column; AWS-only = 15.75 + the AWS part of each plan, so Anthropic and Voyage are excluded):**

| Plan | AWS-only total, planned / cap | Alerts expected to fire, planned / cap |
|---|---|---|
| R0 | 16.92 / 18.93 | none / 18 |
| R0 + R-b | 19.46 / 22.48 | 18 / 18, 20 and 22 |
| R0 + R-b + R-c (**dropped**, option (i); record only, at the former 7.0 h R-b Neptune cap) | 21.30 / 25.48 | 18 and 20 / 18, 20 and 22 (cap above the 25 budget) |

  The AWS part is the plan figure minus its Anthropic and Voyage items: R0 + R-b cap 7.15 - 0.42 = 6.73; R-c planned 5.59 - 0.04 = 5.55; R-c cap 10.25 - 0.52 = 9.73. (Recomputed 2026-11-15 after Q16; the previous values were 19.30 / 21.53 and 20.33 / 23.69. Amended 2026-11-16, P34 impossible: was 19.25 / 21.26 and 20.28 / 23.42, with AWS parts 5.93 - 0.42 = 5.51, 4.57 - 0.04 = 4.53 and 8.19 - 0.52 = 7.67. Amended 2026-11-16, option (i): the R0 + R-b cap was 22.95 with AWS part 7.62 - 0.42 = 7.20. Amended 2026-11-16, L dropped and D3: R0 was 17.39 / 18.92 and R0 + R-b 19.93 / 22.47, with AWS part 7.14 - 0.42 = 6.72.) Because alerts lag 8-24 h, an alert that fires during the session is a warning, not a control.

`C11_TOTAL_USD` = AWS usage before credits x tax factor + Anthropic + Voyage (tax factor 1.00 on credit-covered spend, your decision 2026-11-16; provisional until the December invoice):

| | Tax 0 |
|---|---:|
| `C11_TOTAL_USD` | 15.75 + 0.075 + 0 = **15.83** |
| `S` at floor 3 (your rule until 2026-11-16) | 6.17 |
| `S` at floor 2 (**option (i), 2026-11-16**) | **7.17** |
| `S` at floor 1 | 8.17 |

**Floor: 2 since 2026-11-16 (your option (i) decision, section 6.4), so `S` = 7.17 and the project total must stay at or below 23.00.**

- R0 + R-b planned is 3.71, under `S` = 7.17 (project 19.54).
- At caps, with the 5.8 h Neptune hard stop and the D3 cluster (S only on EMR), R0 + R-b is 7.15, under `S` = 7.17 (project 22.98, margin 0.02). Before L was dropped and D3: 4.18 / 7.14 (project 20.01 / 22.97).
- **Condition 1 (tax): answered 2026-11-16 (tax 0 on credit-covered spend).** Column B (x 1.11; R0 + R-b cap 25.44) was dropped. **Credit check (your 4a review answer 2):** before the session you read the remaining AWS credit balance, with its UTC time; it must be at least the Session 2 AWS cap of **USD 6.73** (R0 + R-b at caps 7.15 minus the Anthropic and Voyage items 0.42; 6.72 before D3), otherwise the approval is void. Limit: this holds while AWS credits cover the spend, so the pre-R-b check (spend to date + 3.57 <= 23.00) stays.
- History: until 2026-11-16 the recommendation was "keep the floor at 3" (your Q1 answer); R0 + R-b then fitted at caps (5.93, project 21.76) until the P34 correction (7.62, project 23.45, over floor 3 by 1.45). The former note read "Floor 2 would only buy option R-b+ planned figures, never its caps"; R-b+ is not defined elsewhere in this revision.
- A floor covers the 8-24 h billing lag and unobserved rates, and Session 1 already showed a 44% underestimate. Floor 2 leaves USD 2.00 for that, and the pre-R-b check (spend to date + 3.57 <= 23.00) protects the firm limit.

### 6.3 Building blocks (before tax; tax 0 on credit-covered spend)

| Block | Rate or amount | Source |
|---|---:|---|
| Stage-a-level infrastructure (NAT, 1 IPv4, residual) | 0.063 per hour | 6.1 |
| Neptune at min 1 / max 2.5 NCU (R-b window planned 5.0 h, hard stop 5.8 h, option (i)) | **planned 0.297 per hour** (observed Nov 14, about 1.85 NCU on average, P32; the same configuration ran in Session 1); **cap 0.402 per hour** (the 2.5-NCU ceiling: 2.5 x 0.1608 per NCU-hour). Amended 2026-11-16 (P34 impossible): was 0.297 observed, with 0.1608 per hour used if held at 1 NCU | 6.1, 6.1a, F23 |
| Runtime increment (Fargate 4 tasks 0.060 + ALB 0.023 + 2 IPv4 0.010) | 0.093 per hour | 6.1 |
| EMR cluster | **0.58 per cluster-hour** (D3: model 0.555 + about 0.02 EBS, rounded up); cap **3.33 h = 1.93** (S and its retry: 2 x (75 min cap + 15 min idle) + 20 min cold start; 3.333 h x 0.58 = 1.933); planned **0.96 h = 0.56** (S only: about 0.60 h + boot and idle about 0.36 h). Was 0.50 per cluster-hour; cap 3.83 h = 1.92 (S + L, 90-min runs); planned 2.05 h = 1.03 | 6.1, F19, P25 |
| S3 EMR outputs and egress | 0.10 | estimate |
| Route 53 hosted zone | 0.50 only if the namespace lives over 12 h (contingency in caps) | Route 53 page |
| Extras (one extra query-api task, small items) | 0.02 planned / 0.07 cap | 6.1 |
| S3 Vectors queries of the R-b load (added 2026-11-15) | 0.53 planned / 0.53 cap (at most 198,600 queries from the required per-level limits, plus at most 200 warm-up queries), at 2.67 per million queries | 6.3a |
| Voyage cache misses of the R-b load (added 2026-11-15, your Q16 answer) | 0 planned (free tokens) / 0.02 cap (at most 800 calls x 1,000 tokens = 0.8M tokens = 0.016), carried in R-b's cap in addition to the session-wide Voyage cap below (conservative double count) | 6.3a |
| Voyage | 0 planned (about 2.25M tokens inside the free allowance; R-b query embeddings bounded by cache misses, at most about 0.8M tokens, 6.3a) / 0.30 cap | 6.1, 6.3a |
| Anthropic | 0 planned in R0 and R-b (no answers) / 0.10 cap | 6.1 |
| DynamoDB (ingest run ledger only) | about 0.01 | bill (Nov 13 load was 0.22 for 166,088 writes) |

### 6.3a S3 Vectors query cost and Voyage bound of the R-b load (added 2026-11-15, your Work order 2 answers)

**Prices** (section 2; the coordinator's read of the public S3 pricing page on 2026-11-15; **US East (N. Virginia) figures; US East (Ohio) is not listed on the page**, so the Ohio rate is assumed equal; confirm on the bill):

- query API requests: USD 2.50 per million;
- query data processed: USD 0.004 per TB for the first 100K vectors in the queried index (0.002 per TB from 100K to 10M; not reached here);
- data processed per query = average vector size (vector data + key + filterable metadata; non-filterable metadata excluded) x the number of vectors in the queried index.

**What one request queries** (read from the code, 2026-11-15): each accepted `/v1/semantic/retrieve` request makes one `QueryVectors` call against **one** index, the one named by `SCHOLARCHAIN_SEMANTIC_INDEX` (`SemanticApi.scala` line 100, `vectors.query(index, …)`, after the embed call at line 98; `AwsConfig.scala` line 251; corrected 2026-11-16, review finding R3, re-read at HEAD `cceb1f5`). Readiness probes use `GetVectors`, not `QueryVectors` (`AwsComposition.scala` lines 267-268 and 316). A request rejected with 429 by the P40 rate limiter never reaches S3 Vectors.

**`/readyz` stays in the P42 semantic mix (coordinator default, review 2 finding 6, 2026-11-16; not asked).** The mix is semantic 40, `/healthz` 2, `/readyz` 1, `/metrics` 1 (weight 1 of 44), so at the 198,600-request bound about 4,500 calls are `/readyz` (198,600 / 44 = 4,513). Each fans out to the graph-service and semantic-service probes, the latter a `GetVectors` call. **Unverified:** the claim in `experiments/README.md` that these probes "carry no per-request charge" was not checked against S3 Vectors pricing (no network in that review). The cost is bounded and small either way. As an illustration only (the `GetVectors` rate is not known to this plan), if each of the 4,513 probes were billed at the 2.67 per million query rate, the extra would be about USD 0.012 (4,513 x 0.00000267); the 198,600 bound behind the 0.53 figure already counts these roughly 4,500 `/readyz` requests, each priced as a query call, so only the extra cost of a probe that may call `GetVectors` on more than one index is not covered, and no cap changes. You may verify the pricing or accept the default as it stands.

**Per-query cost (assumptions stated):**

| Item | Typical (assumed) | Conservative upper bound (used) |
|---|---:|---:|
| Vector data: 256 float32 values x 4 bytes | 1,024 B | 1,024 B |
| Key | about 100 B | 1,024 B (assumed S3 Vectors key limit, not re-read) |
| Filterable metadata (`textS3Uri` is non-filterable and excluded) | about 400 B | 2,048 B (the repository's own limit, `maxFilterableBytes = 2 * 1024`, `Phase7Configs.scala` line 66) |
| **Average vector size** | **about 1,500 B** | **4,096 B** |
| Vectors in the queried index | per-index split not known until stage a (P26) | **10,000** (as if all vectors sat in the queried index) |
| Data processed per query | 1,500 x 10,000 = 15,000,000 B = 0.000015 TB | 4,096 x 10,000 = 40,960,000 B = 0.00004096 TB (TB = 10^12 B, the larger count) |
| Data-processed charge per query | 0.000015 x 0.004 = USD 0.00000006 | 0.00004096 x 0.004 = USD 0.000000164 |
| Request charge per query | 2.50 / 1,000,000 = USD 0.0000025 | USD 0.0000025 |
| **Cost per query** | USD 0.00000256 (2.56 per million) | **USD 0.00000266 (2.66 per million; this plan uses 2.67)** |

The request charge is about 94% of the per-query cost. The index size matters little at 10,000 vectors.

**Planned query count** (an assumption; **the P35 local measurement did not replace it**: the offline rehearsal has no S3 Vectors latency, and you set the request target from this live estimate, 2026-11-16, see the P35 results paragraph in section 4). The plan gives no throughput figure, so:

- The load generator is closed-loop: `level` workers each send the next request when the previous one returns (`loadgen.py` line 667).
- **Assumed latency L = 200 ms per request**, unsaturated (Session 1's per-index query p50 was 132-187 ms, rounded up), with no throttling (P35 sets `r_S2` so that level 50 is not throttled: `r_S2` = 3500). Each worker then sends 5 requests/s.
- Durations as in the 15B manifest that the P42 variant copies: level 1 for 120 s, level 5 for 120 s, level 25 for 150 s, level 50 for 180 s, then a hold at 50 for 600 s. That is a load window `T_plan` of 1,170 s (19.5 min), plus at least 25 quiet minutes.
- Offered queries = sum(level x duration) / L = (1 x 120 + 5 x 120 + 25 x 150 + 50 x 180 + 50 x 600) / 0.2 = 43,470 / 0.2 = 217,350 (USD 0.58 before the per-level limits; this was the planned figure until your Q16 answer).
- **Required per-level limits (P42, your Q16 answer, 2026-11-15): 600 / 3,000 / 15,000 / 30,000 / 150,000**. The planned count is the smaller of offered and limit per phase: 600 + 3,000 + 15,000 (offered 18,750) + 30,000 (offered 45,000) + 150,000 = **198,600**, plus at most 200 warm-up requests.
- **Planned cost: 198,600 x 0.00000267 = USD 0.53** (198,800 with the warm-up: still 0.53).
- At this assumption, levels 25 and 50 reach their limits after about 120 s (15,000 / 125 per second; 30,000 / 250 per second). For the rest of those phases the load generator sends nothing, because the workers stop at the phase limit (`loadgen.py` lines 426-431 and 634-636): a gap of about 30 s and 60 s. The 600 s hold at 250 per second ends exactly at its limit. P35's measured rates show whether this happens.
- At this assumption level 50 offers about 250 requests/s, so a single query-api task (before scale-out) needs `r_S2` of at least 250 not to throttle it. P35 set `r_S2` to at least 2 x the measured local peak (P35 row): 2 x 1,737 = 3,474, so `r_S2` = 3500 and `b_S2` = 7000. The local peak is far above this 250 live planning rate, which errs toward no throttling.

**Worst case** (amended after your Q16 answer, 2026-11-15; the required per-level limits are the bound):

- **Bound:** the load generator stops each phase at its `max_requests` and counts 429 replies toward it (`loadgen.py` lines 282 and 426-431). The required limits therefore bound the requests sent, and so the S3 Vectors queries, at **198,600, plus at most 200 warm-up requests**, whatever `r_S2` is. A higher `r_S2` does not raise cost.
- **S3 Vectors at 198,600 queries:**
  - requests 198,600 x 0.0000025 = USD 0.4965;
  - data processed 198,600 x 0.000000164 = USD 0.0325;
  - total **USD 0.5290, carried as 0.53**.
  - With the warm-up (198,800): 0.4970 + 0.0326 = 0.5296, still 0.53.
- **Voyage cache misses:** at most USD 0.016 (bound below), **carried as 0.02** in R-b's cap.
- **R-b worst case (2026-11-15, at the 1-NCU Neptune rate)** = previous R-b cap 2.61 - 0.80 (the 300,000 backstop) + 0.53 + 0.02 = 2.36.
  - R0 + R-b cap = 3.57 + 2.36 = 5.93.
  - Project at caps = 15.83 + 5.93 = 21.76 <= 22.00.
  - Your condition held then, and the per-level limits were kept.
- **R-b worst case corrected 2026-11-16 (P34 impossible):** R-b's Neptune window cap is 7.0 h (back-solved from the earlier 6.4 rows: (6.34 - 5.93) / 0.0592 = 6.93 and (6.88 - 5.93) / 0.1362 = 6.98). At the 2.5-NCU ceiling its Neptune cap is 7.0 x 0.402 = 2.81 instead of 7.0 x 0.1608 = 1.13, so:
  - `E_b` = 2.36 + 7.0 x (0.402 - 0.1608) = 2.36 + 1.69 = **4.05**;
  - R0 + R-b cap = 3.57 + 4.05 = **7.62**;
  - project at caps = 15.83 + 7.62 = **23.45 > 22.00**.
  - The Q16 condition did not hold at caps; a decision was pending.
- **R-b worst case under option (i) (decided 2026-11-16, section 6.4):** the Neptune window has a hard stop at 5.8 h, so R-b's Neptune cap is 5.8 x 0.402 = 2.33 and
  - `E_b` = 4.05 - (7.0 - 5.8) x 0.402 = 4.05 - 0.48 = **3.57**;
  - R0 + R-b cap = 3.57 + 3.57 = **7.14**;
  - project at caps = 15.83 + 7.14 = **22.97 <= 23.00** (floor 2, margin 0.03).
  - **After L was dropped and D3 (2026-11-16):** `E_b` is unchanged (3.57; R-b has no EMR part). The EMR cap block rises from 1.92 to 1.93, so R0 cap = 3.58, R0 + R-b cap = 3.58 + 3.57 = **7.15**, and project at caps = 15.83 + 7.15 = **22.98 <= 23.00** (margin 0.02).
  - The per-level limits are unchanged (600 / 3,000 / 15,000 / 30,000 / 150,000), with the 150,000 hold.
- For the record, the rate-limiter bound is still `Q_max(r) = r x N x T + b x N = 3,000 x r + 2 x b` (N = 2 query-api tasks, T = 1,500 s, the longest load window the plan allows). At the code default (`r` = 50, `b` = 100) it gives 150,200. At `r_S2` of 250 or more it is above the per-level limits, so the limits bind. The load generator's own `max_total_requests` of 300,000 (`load-profile.v1.json`) is now only a backstop.
- Not counted (negligible): the stage-a query smoke (one query per index), and transport retries of a failed call. Retries are at most 3 attempts per call, and the load generator aborts at 20 failures in 40 requests.

**Voyage bound (cache misses only):**

- Each semantic-service task has its own LRU cache (1,024 entries, larger than the question set, so no eviction). Voyage calls are therefore at most (distinct questions, about 100-200) x (semantic-service task starts during R-b), plus any restarts.
- With min 1 and max 2 tasks and one scale-out, that is 2 starts: **at most about 400 calls**. Allowing two extra starts (restarts or a second scale-out) gives at most about 800. The planned failure example stops a query-api task, which does not empty a semantic-service cache.
- The P42 warm-up pass sends each distinct question once before the ramp, so the first task's calls equal the distinct questions. A task started by scale-out begins cold under load. Concurrent misses for the same question are not coalesced, so that task can make a few duplicate calls. Even an extreme 200 questions x 50 workers = 10,000 calls (10M tokens at 1,000 tokens each) stays inside the 200M free tokens.
- Tokens: a question has at most 1,000 characters (P40 limit). At a conservative 1 token per character, that is at most 800 x 1,000 = **0.8M tokens**, which would be USD 0.016 at USD 0.02 per million (`load-profile.v1.json`).
- Inside the 200M free tokens (repository record, section 6.1), the cost is **USD 0**. Typical short topic phrases (about 20 tokens) give about 400 x 20 = 8,000 tokens.
- The session-wide Voyage cap stays 0.30. R-b's cap additionally carries 0.02 for these misses (your Q16 condition), a conservative double count.
- **Rate-limit dependency:** the first pass sends up to 200 cache misses per task. At the Session 1 free-trial limit (about 3 requests per minute), that pass alone would take about 67 minutes, and misses refused by Voyage would surface as downstream errors. The P26 (c) tier check must confirm the paid limits first.

### 6.4 Variants, costs and fit (tax 0 on credit-covered spend; firm USD 25; floor 2 since 2026-11-16, so the project total is at most 23.00)

**Neptune (amended 2026-11-16, P34 impossible):** capacity stays min 1 / max 2.5 NCU, so planned figures use the observed **0.297/h** (Nov 14, about 1.85 NCU, P32) and caps use the 2.5-NCU ceiling **0.402/h** (2.5 x 0.1608 per NCU-hour). Before this amendment the plan priced Neptune at 0.1608/h with P34. R-b's Neptune window is **5.0 h planned**; its cap was **7.0 h**, back-solved from the earlier rows of this table: planned (3.80 - 3.50) / 0.0592 = 5.07 and (4.18 - 3.50) / 0.1362 = 4.99; cap (6.34 - 5.93) / 0.0592 = 6.93 and (6.88 - 5.93) / 0.1362 = 6.98 (0.0592 = 0.22 - 0.1608; 0.1362 = 0.297 - 0.1608). R-b's Neptune cost therefore went from 0.80 planned / 1.13 cap (at 0.1608/h) to 1.49 planned (5.0 x 0.297) / 2.81 cap (7.0 x 0.402). **Under option (i) the cap is a hard stop at 5.8 h: 5.8 x 0.402 = 2.33.**

**Amended 2026-11-15:** R-b's semantic load now carries its S3 Vectors query cost from section 6.3a. This replaces the earlier allowance of 0.10 / 0.30, which had been used because the rate was not known. **After your Q16 answer** the required P42 per-level limits bound the queries at 198,600: **0.53 planned / 0.53 cap, plus 0.02 for Voyage cache misses in the cap**. R-b therefore rises by 0.43 planned and 0.25 at cap against the original plan. Voyage stays about 0 planned, because calls are bounded by cache misses (6.3a).

| Plan | Planned | Cap | Project total, planned / cap | Fits floor 2? |
|---|---:|---:|---|---|
| **R0** (stage a + vectors; S only on EMR, D3 cluster) | 1.17 | 3.58 | 17.00 / 19.41 | **yes** |
| **R0 + R-b** (option (i): Neptune min 1 / max 2.5 NCU with a 5.8 h hard stop, 150,000 hold, semantic load, request-count scaling) | **3.71** | **7.15** | **19.54 / 22.98** | **yes, even at caps (margin 0.02)** |
| R0 + R-b, **low scenario (comparison only)**: Neptune averages about 1.35 NCU (Nov 13, empty graph, 0.22/h) through the planned and cap hours | 3.33 | 6.09 | 19.16 / 21.92 | yes |
| R0 + R-b + R-c (**dropped**, option (i), 2026-11-16; record only, computed with the former 7.0 h R-b Neptune cap) | 5.59 | 10.25 | 21.42 / 26.08 | dropped (cap above the USD 25 firm limit; gate 2 failed on planned `X_spent`) |

Column B (x 1.11) dropped 2026-11-16, human's tax decision ("the portion of your bill deducted/covered by AWS credits is not taxed. Since they are credits so tax is 0"). Old values: `C11_TOTAL_USD` 17.56; `S` at floor 3 / 2 / 1 = 4.44 / 5.44 / 6.44; rates 0.503 (full stack), 0.070 (stage a), 0.555 (EMR) per hour; project total B, planned / cap: R0 19.38 / 21.49, R0 + R-b 22.20 / 25.44 (25.97 at the 7.0 h cap; 21.45 / 24.10 before the P34 correction), low scenario 21.78 / 24.26, R0 + R-b + R-c 23.76 / 28.88; the gate-2 x 1.11 check `X_spent <= 0.20` (0.57 before the P34 correction). Method: 17.56 + 1.11 x the AWS part + the Anthropic and Voyage caps (0.42; 0.52 with R-c).

Derivations after L was dropped and D3 (2026-11-16; the plan's method: the EMR rate is the model rate plus about 0.02 for EBS, rounded up to the cent, 0.555 + 0.02 = 0.575 → 0.58; each block is hours x rate, rounded to the cent): EMR planned 0.96 h x 0.58 = 0.5568 → 0.56 (was 1.03, so -0.47); EMR cap 3.333 h x 0.58 = 1.9333 → 1.93 (was 1.92, so +0.01). R0 1.64 - 0.47 = 1.17 and 3.57 + 0.01 = 3.58; R0 + R-b 4.18 - 0.47 = 3.71 and 7.14 + 0.01 = 7.15; project 15.83 + 3.71 = 19.54 and 15.83 + 7.15 = 22.98; low scenario 3.80 - 0.47 = 3.33 and 6.08 + 0.01 = 6.09. At the exact 0.555 rate without the EBS margin the block would be 1.85 (project 22.90). The figures before this were derived as follows. Derivations (tax 0): R0 + R-b planned 3.50 + 5.0 x (0.297 - 0.1608) = 3.50 + 0.68 = 4.18; cap 3.57 + `E_b` 3.57 = 7.14 (section 6.3a), that is 5.93 + 5.8 x 0.402 - 7.0 x 0.1608 = 5.93 + 2.3316 - 1.1256 = 7.136, about 7.14. Low scenario cap 5.93 - 1.1256 + 5.8 x 0.22 = 6.08 (derived by the documentation-engineer). R0 + R-b + R-c (record): planned 4.57 + 0.68 + 0.34 = 5.59; cap 8.19 + 1.69 + 0.37 = 10.25, with the R-c Neptune change from section 5.4 (0.40 → 0.74 planned, 1.04 → 1.41 cap).

The former row "R0 + R-b without P34, Neptune at about 1.85 NCU (Nov 14, 0.297/h)" (4.18 / 6.88; 20.01 / 22.71; 22.20 / 25.15) became the R0 + R-b row on 2026-11-16: its planned figures are the plan, and its cap (6.88, 0.297/h through the cap hours) was superseded by the 0.402/h ceiling.

Amended 2026-11-15 in two steps, and 2026-11-16 twice. Previous values (planned / cap; project total A; project total B):

- **Step 1** (S3 Vectors at the 300,000-request backstop: +0.48 planned, +0.50 cap): R0 + R-b 3.55 / 6.18; 19.38 / 22.01; 21.50 / 24.38. Without P34 at 1.35 NCU 3.85 / 6.59; 19.68 / 22.42; 21.83 / 24.83. At 1.85 NCU 4.23 / 7.13; 20.06 / 22.96; 22.26 / 25.43. R0 + R-b + R-c 4.62 / 8.44; 20.45 / 24.27; 22.69 / 26.87.
- **Step 2** (your Q16 answer: per-level limits 198,600 and Voyage 0.02; -0.05 planned, -0.25 cap): R0 + R-b (with P34) 3.50 / 5.93; 19.33 / 21.76; 21.45 / 24.10 (fitted floor 3 even at caps). Without P34 at 1.35 NCU 3.80 / 6.34; 19.63 / 22.17; 21.78 / 24.55. At 1.85 NCU 4.18 / 6.88; 20.01 / 22.71; 22.20 / 25.15. R0 + R-b + R-c 4.57 / 8.19; 20.40 / 24.02; 22.63 / 26.59.
- **Amended 2026-11-16 (P34 impossible;** Neptune planned at 0.297/h and capped at 0.402/h instead of 0.1608/h, R-b cap 7.0 h; +0.68 planned and +1.69 cap for R-b, plus +0.34 / +0.37 for R-c's Neptune; floor 3): R0 + R-b 4.18 / 7.62; 20.01 / 23.45 (cap over floor 3 by 1.45); 22.20 / 25.97. R0 + R-b + R-c 5.59 / 10.25; 21.42 / 26.08; 23.76 / 28.88.
- **Amended 2026-11-16 (option (i);** floor 2, R-b Neptune hard stop 5.8 h, -0.48 cap; R-c dropped): R0 1.64 / 3.57; 17.47 / 19.40. R0 + R-b 4.18 / 7.14; 20.01 / 22.97. Low scenario 3.80 / 6.08; 19.63 / 21.91.
- **Amended 2026-11-16 (L dropped on EMR; D3 cluster; 75-min S cap;** -0.47 planned, +0.01 cap): the table above. The R-c record row was not recomputed.
- **Original** (before the amendment): R0 + R-b 3.07 / 5.68; 18.90 / 21.51; 20.97 / 23.82. At 1.35 NCU 3.37 / 6.09; 19.20 / 21.92; 21.30 / 24.27. At 1.85 NCU 3.75 / 6.63; 19.58 / 22.46; 21.73 / 24.87. R0 + R-b + R-c 4.14 / 7.94; 19.97 / 23.77; 22.15 / 26.32.

**Tax (your decision 2026-11-16):** tax 0 on credit-covered spend, valid while AWS credits cover the spend; column B was dropped (history line above).

> **Decided 2026-11-16: option (i).** (This is the R-b option (i) of this section, not P11 option (i).) Your words, verbatim:
>
> "(i), with conditions:
> 1. Tax: Session 1's Bills page showed tax 0.00. Confirm whether tax applies to this account. If not, drop the ×1.11 row; if it does, come back to me, since 25.44 is over the hard ceiling.
> 2. The 5.8 h Neptune window is a hard stop: run the R-b load early in the window. At 5.8 h, destroy Neptune whether R-b has finished or not, and keep whatever elasticity data was captured. Put the clock times in the runbook.
> 3. Pre-R-b check: before applying R-b, spend to date (with its read time) + R-b cap must be ≤ 25.00; otherwise skip R-b.
> 4. Update the plan to floor 2 / project ≤ 23.00, list every changed number, and give me the exact wording for the P19 approval record."
>
> **As applied:**
>
> - floor 2 for the whole plan: `S` = 7.17, project total at most 23.00 (section 6.2);
> - the 150,000 hold and the per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 are kept;
> - R-b's Neptune window: planned 5.0 h, **hard stop 5.8 h**, with the clock in section 5.3 and the teardown order in section 5.5; worst case 23.45 - 1.2 x 0.402 = **22.97** (**22.98** since L was dropped and the D3 cluster, 2026-11-16); `E_b` **3.57**; gate 1 threshold **2.85**;
> - the pre-R-b check below (condition 3);
> - **R-c dropped**: the 5.8 h hard stop cannot hold R-c's Neptune window (about 7.5 h), and gate 2 fails anyway;
> - condition 1 (tax): **answered 2026-11-16 (tax 0 on credit-covered spend)**, your words: "the portion of your bill deducted/covered by AWS credits is not taxed. Since they are credits so tax is 0". Column B (cap 25.44) is dropped. Limit: this holds while AWS credits cover the spend, so the pre-R-b check stays;
> - condition 4: this amendment, the changed-number list in the documentation-engineer's report, and the draft P19 wording in section 4a.
>
> **Background (2026-11-16, before the decision):** at the 0.402/h ceiling and a 7.0 h window, R0 + R-b at caps was 23.45 against the floor-3 limit of 22.00, over by 1.45. Your Q16 condition (section 9.3) asked for the worst case to keep the project at or below USD 22, and otherwise to "lower the per-level limits to the minimum that still shows scale-out to 2 tasks and scale-in". Your earlier decision 2 of 2026-11-16, verbatim: "Neptune: (a), lower the hold from 150,000 to 90,000. Condition: use the P35 measured rate (or the planning rate until P35 runs) and state how many minutes the level-50 hold lasts. It must cover scale-out plus at least 3 minutes of steady state at the scaled-out task count. If it doesn't, come back to me before choosing (c)." It was taken on a wrong coordinator figure ("+0.37, worst case 22.13", which used R-c's 3.5 h Neptune cap instead of R-b's 7.0 h; repairs E5), and its condition failed at the planning rate, so it was not applied. The options (a)-(c) it refers to were given in chat and are not recorded in this file.
>
> **Hold arithmetic (estimates; P35 is local and cannot measure AWS alarm timing):** at the planning rate (L = 200 ms, 50 workers = 250 requests/s, section 6.3a), a 90,000 hold lasts 360 s = **6.0 min** and a 150,000 hold 600 s = **10.0 min**. The estimated scale-out time is about **6.5 min**: about 4 min for the target-tracking alarm (3 one-minute datapoints plus metric delay), plus task start and 3 ALB health-check passes at 30 s. With 3 min of steady state that is about **9.5 min**, so 90,000 does not meet the condition and 150,000 meets it narrowly.
>
> **Rejected alternatives (record):**
>
> - (ii) keep floor 3: needs a Neptune window cap of 3.4 h with the 150,000 hold (7.0 - 1.45 / 0.402) or 3.8 h with a 90,000 hold (7.0 - (1.45 - 0.16) / 0.402; 60,000 fewer queries x 0.00000267 = 0.16), against a planned R-b sequence of about 5 h of Neptune; judged infeasible;
> - (iii) drop R-b: elasticity only from the local P35 rehearsal; project R0 17.47 / 19.40;
> - (iv) run R-b without Neptune: needs Terraform changes (the runtime precondition at `phase12b.tf:42` requires `neptune_enabled`) and service changes (F22, P33) before Wednesday, on an unproven live path; would save 1.49 planned / 2.81 cap (project cap about 20.64).

**Gates:**

- **Gate 1** (before R-b): `X_a <= 7.17 - E_b - 0.75` (floor 2). Threshold **2.85** (`E_b` = 3.57, R-b's 5.8 h Neptune hard stop at the 0.402/h ceiling; section 5.2). Planned `X_a` about **0.88 passes by 1.97** (S only on EMR at 0.58 per cluster-hour: 1.35 - 2.05 x 0.50 + 0.96 x 0.58 = 0.88; was 1.35 passing by 1.50). The EMR term of `X_a` is the recorded actual of the Session 2 runs (section 5.2 step 5a). The R-c DynamoDB cache load (0.22) is no longer run, because R-c is dropped, so it is not in planned `X_a` (was 1.57 with it). History: amended 2026-11-15, 3.31 / 2.36 originally, then 2.81 / 1.86, then 3.06 / 2.11 (3.06 with P34 at the 1-NCU rate, `E_b` = 2.36; 2.11 without P34, `E_b` = 3.31; floor 3), when planned `X_a` passed with a margin of about 1.49; amended 2026-11-16 (P34 impossible) to 1.37 (`E_b` = 4.05, floor 3; planned `X_a` 1.57 failed by 0.20); amended 2026-11-16 (option (i)) to 2.85.
- **Pre-R-b check** (before R-b, option (i), your condition 3): spend to date (`C11_TOTAL_USD` as last read, with its read time, plus the clock-based estimate since that read) + R-b cap (`E_b` = 3.57) **<= 23.00** (floor 2; your 4a review answer 3, 2026-11-16; was 25.00); above 23.00 R-b is skipped and cleanup (5.5) starts, unless you record a new decision. The EMR part of spend to date is the recorded actual (section 5.2 step 5a), not the cap. Planned: 15.83 + 0.88 + 3.57 = 20.28 (margin 2.72; was 20.75). **Both gate 1 and this check must pass.** If S fails twice, gate 1 applies after the section 5.2 step 7b fallback (vectors from the local P6 S run), with the same thresholds.
- **Gate 2** (before R-c): **not applied since 2026-11-16 (R-c dropped, option (i)).** Kept as a record: `15.83 + X_spent + 2.63 + 0.68 + 0.50 <= 22`, so `X_spent <= 2.36` (amended 2026-11-16 for the R-c cap 2.63; was 2.26 and `X_spent <= 2.73`).
  - Planned `X_spent` at the end of R-b was about **3.47** (3.02 before the 2026-11-16 Neptune correction; originally 2.59, 3.07 in step 1): stage a about 1.57 including the cache load, plus R-b so far about 1.90. The R-b part was 3.3 h of stage-a-level hours 0.21, **Neptune 0.98** (3.3 h x 0.297; was 0.53 at the 1-NCU rate), runtime 0.16, **S3 Vectors 0.53** (originally 0.10) and extras 0.02.
  - **The margin was about -1.11** (-0.29 before the Neptune correction; originally +0.14): on planned figures R-c failed gate 2.
  - **Your Q17 answer (2026-11-15):** keep R-b as designed and expect R-c to be dropped. The report states why: R-c is dropped under option (i) because the 5.8 h Neptune hard stop cannot hold its Neptune window, and gate 2 also fails on planned figures (`X_spent` about 3.47 against 2.36, because of R-b's S3 Vectors query cost of 0.53, which replaced the 0.10 allowance, and the real Neptune rate; 3.02 against 2.73 before the 2026-11-16 correction; 3.07 before the per-level limits).
  - Even with no S3 Vectors queries, planned `X_spent` would have been about 2.94 (3.47 - 0.53), still above 2.36. (Before the correction: S3 Vectors at most about 0.24, about 90,000 queries.) In the low scenario (about 1.35 NCU, 0.22/h) `X_spent` was about 3.22, which also failed.
  - The former rule: the gate was applied to the clock-based `X_spent` measured in the session, with Neptune at the measured `ServerlessDatabaseCapacity` x 0.1608 per NCU-hour.

### 6.5 Elasticity load target and scaling signal (decision)

| | (a) Semantic retrieval load (F25) | (b) ALB request count per target (F26) |
|---|---|---|
| Code | **Yes:** public `/v1/semantic/retrieve` route on query-api and wiring (service-engineer); query-embedding cache (rag-engineer); load generator route and manifest (experiment-engineer) | None |
| Terraform | None (the ALB already passes every path) | One `aws_appautoscaling_policy` plus a validated variable, wiring in the root, a dashboard panel (infra-engineer); **no deployer change** (PutScalingPolicy and `alarm:TargetTracking-*` already allowed) |
| Tests | Service route tests (auth, limits, no query-text logging), cache tests (one embed per distinct question), an independent API test (test-engineer), load generator tests | `terraform test`: policy present only with the runtime deployed and the variable set; label format; CPU policy unchanged |
| Review rounds | About 2 per owner, three owners; one security look at a new public route | 1-2 |
| Risk before Wed Nov 18 (the session HEAD must be committed and the images built by then; the Nov 24 freeze is later) | **Moderate:** a new public endpoint and cache, plus an image rebuild. Fallback if not ready: (b) with the healthz/readyz/metrics load (weaker evidence, stated) | **Low:** a single additive resource |
| Cost during R-b | S3 Vectors queries 0.53 planned / 0.53 cap (198,600 queries, bounded by the required P42 per-level limits) at 2.67 per million queries (section 6.3a; amended 2026-11-15); Voyage about 0 planned, 0.02 in the cap (at most about 400-800 calls, bounded by cache misses of the 100-200 fixed questions per semantic-service task); one extra semantic-service task about 0.015/h | Two more CloudWatch alarms (about 12 in total, 10 free; cents at most) |
| Evidence value | Real retrieval work (embedding lookup, S3 Vectors k-NN over about 10,000 real vectors, JSON results) scaling **two** services (query-api through the ALB; semantic-service on CPU) | Scale-out is driven by load, not by lowering the CPU target; the dashboard can show requests per task crossing the target |

**Recommended combination: (a) + (b), keeping the CPU policy.** Scaling follows offered load (requests per target) while the work per request is genuine retrieval. P35 rehearses both the load side and the derived request target.

### 6.6 Demo coverage by plan (see [demo-script.md](../demo-script.md), section 4)

| Plan | Recorded live in Session 2 | From Session 1 evidence (labelled "Session 1, 2026-11-13/14") | Offline (labelled "fixture" or "local") |
|---|---|---|---|
| R0 + R-b | 9, 10, 12, 13, 18, 19, 20, 21, 22 | 11, 14, 15, 16 (live part) | 1-8, 16 (unit test), 17 |
| R0 + R-b + R-c (**dropped**, option (i), 2026-11-16; record only) | 9-16, 18-22 (all live items) | — (Session 1 as comparison only) | 1-8, 16 (unit test), 17 |

**Not evaluated because of the USD 25 limit (state this in the report):**

- loading L into the stores;
- elasticity of the graph and LLM paths under load;
- EMR managed scaling;
- R-c is dropped (option (i), 2026-11-16): no live graph load at S, no live API answers and no 24 reruns in Session 2;
- the other 16 benchmark questions in Session 2.

### 6.7 Schedule (CST with UTC)

| When | What |
|---|---|
| Sun Nov 15 to Tue Nov 17 | Offline prerequisites and reviews (section 4); P21 download; your P30 review of the 6 pairs; P32 done (capacity only); P34 closed 2026-11-16 (not possible; capacity stays min 1 / max 2.5 NCU) |
| Tue Nov 17 | Confirm that Nov 15 billing is complete. **P0 (your answers):** read-only Switch Role check of `scholarchain-billing-deployer`, then the live budget modify: USD 25, 2026-10-01 to 2027-01-01, actual-spend alerts at 18/20/22, no forecast alerts, credits and refunds excluded; the readback confirms `CostTypes` |
| **Wed Nov 18, 12:00 CST** | **P40 cutoff:** the semantic route must be reviewed and committed, or the fallback (request-count scaling on health-check load, labelled weaker) is used. No last-minute changes. |
| Wed Nov 18 | P6 at S (L done 2026-11-16 as local evidence only; **P6 S on the frozen session commit, after the P15 rebuild; its Spark export kept with `SHA256SUMS` for the step 7b fallback**); P35 rehearsal; P15 rebuild and pins; P20; **your read of the remaining AWS credit balance with its UTC time (at least USD 6.73)**; the **Session 2 approval record (Procedure R) written by you**. This plan's approval is not that record. |
| **Thu Nov 19**, 06:30-07:30 CST (12:30-13:30Z) | Pre-session; **IAM window 1** (A4 operator roles + P11 stop-task statement; A5; A7) |
| **07:30 CST (13:30Z)** | **H0: first base-apply** |
| 08:30-10:30 CST | Run S on EMR (75-min cap), then its EMR actual recorded (step 5a); an S retry only if S failed, then its actual recorded. No L on EMR. Meanwhile the vector ingest and the query smoke (the `--cache-only` DynamoDB load is not run: R-c dropped). If S fails twice: the step 7b fallback (vectors from the local P6 S run), which must finish with gate 1 by about **12:15 CST (18:15Z)**; `T_N0` then moves later, and every Neptune clock point moves with it |
| **10:45 CST (16:45Z)** | **Gate 1** (R-b, threshold 2.85) **and the pre-R-b check** (spend to date with its read time + 3.57 <= 23.00) |
| **10:50 CST (16:50Z)** | **`T_N0`**: the actual start of the Neptune base-apply, written in the session log (min 1 / max 2.5 NCU) |
| 10:50-12:45 CST | Neptune base-apply, push, runtime-apply (no tunnel definition: R-c dropped), P37, DNS, B6 smoke |
| **12:45 CST (18:45Z)** | **R-b load starts immediately after the B6 smoke passes** |
| 12:45-14:10 CST | Semantic-load elasticity and collection, then the failure example; items 18-21 |
| **14:15 CST (20:15Z)** | **Planned cleanup start** (11:00 CST if NO-GO at gate 1 or the pre-R-b check) |
| **14:25 CST (20:25Z)** | **Latest full-variant (about 50 min) load start** (`T_N0` + 3 h 35 min) |
| **14:38 CST (20:38Z)** | **Latest load start of any kind** (37-min short variant; `T_N0` + 3 h 48 min) |
| **14:55 CST (20:55Z)** | Latest failure-example start (skip it otherwise) |
| **15:15 CST (21:15Z)** | **Latest start of the pre-destroy steps** (B13, C2, C3 pass-1 listing; about 50 min, section 5.5) |
| **16:05 CST (22:05Z)** | **Target: Neptune destroy issued** (`T_N0` + 5 h 15 min; the confirmed C3 pass 1, section 5.5) |
| **16:20 CST (22:20Z)** | **Absolute: Neptune destroy issued, whether R-b has finished or not** (`T_N0` + 5 h 30 min; about 18 min of deletion, an estimate, ends by 5.8 h) |
| **17:15 CST (23:15Z)** | **Latest cleanup start only if Neptune was never created** (NO-GO at gate 1); otherwise the Neptune clock above governs |
| about 18:00-18:45 CST | **IAM window 2**: C4, C5, P39 deployer removal |
| **19:00 CST (01:00Z Nov 20)** | **Hard stop** (H0 + 11.5 h, inside the 12-hour Route 53 window) |
| Fri Nov 20 | C11-style check (three bills), cost report |
| Sat Nov 21 / Sun Nov 22 | Fallback day with the same timings |

Amended 2026-11-16 (option (i)): the gate 2 slot (14:15 CST, latest R-c start) and the R-c block (14:15-16:45 CST) are removed because R-c is dropped; the planned cleanup start with R-c was 16:45 CST, the latest cleanup start 17:15 CST, and the Neptune base-apply line read "(max 1 NCU)" until the P34 correction. The first option (i) clock (same day) had no new load start after 15:40 CST, the destroy target at 16:20 CST and the absolute stop at 16:38 CST; it was made conservative the same day. The planned clock times assume `T_N0` = 10:50 CST; the rules are relative to the actual `T_N0` (section 5.3).
| Tue Nov 24 | Freeze target |
| Wed Nov 25, 23:00 CST | Submission deadline |

---

## 7. Risks and what Session 1 taught

| Lesson or risk (evidence) | Session 2 control |
|---|---|
| **Fakes are not the real CLI** (`list-instance-groups` absent in CLI 2.35.4; `HadoopJarStep` rejected; `describe-cluster` needs `ListBootstrapActions`) | P2 audit with offline `--generate-cli-skeleton` |
| **Silent size limits.** The Hadoop 12,000-record ceiling would reject most of L as "oversize", and the 256 MiB copy-out ceiling is below the local outputs at S | P22, P23, and P6 at both sizes before going live (done 2026-11-16: S passed; L fails ER at 22g, so L is dropped on EMR) |
| **First complete EMR run of this chain.** No Session 1 timing exists beyond stage-in | Run S first; P6 local timings; the S cap is 75 min (D3; was 90) |
| **EMR cold starts and idle clusters** (five clusters; bootstrap race with the EFS mount target; about USD 0.4 idle) | P7 (d); one cluster for S and its retry; submit the retry within 15 minutes of a failure (L dropped on EMR); record the EMR actuals after each run |
| **A local path in a manifest is invisible on the cluster** | P1, P6 |
| **Idle full stack overnight** (about 11 h, about USD 5.0 at the measured rate) | One-day session; Neptune and the runtime exist only inside the R-b window |
| **Token expiry** (deployer 1 h, operator roles 4 h) | Fresh Switch Role and `aws login` before each step; at least 100 minutes left before each EMR run |
| **Tunnel drop** during the about-2-hour DynamoDB phase | Not applicable to R0 or R-b (no tunnel, no graph load) |
| **Cold service** (504 on the first query; 28-45 s artifact load) | P14 or a warm-up query |
| **Root-versus-IAM login slip** (C4 attempt 1) | Root only in a private window, read-only |
| **Billing lag; tax arrives with the invoice** | Read all three bills at every go/no-go; caps stop work, alerts do not |
| **Voyage rate limits** (free trial about 3 requests per minute; throughput 0.614 vectors/s even after adding a payment method) | Check the tier on the dashboard; P26 batching; the ingest overlaps run L |
| **Archive limit** (logs over 1 MiB) | Curated includes and external locations planned before stage d |
| **Video exposure** (account ID visible in the Session 1 video) | Blur headers and ARNs; never print bucket names |
| **Neptune was the dominant cost**: 9.05 of 15.75, all serverless capacity (P32) | Neptune at min 1 / max 2.5 NCU (P34, max 1 NCU, is not possible; 2026-11-16); the Neptune window is about 5 h planned with a **5.8 h hard stop** (option (i), clock in section 5.3); R-c dropped. Was: "P34 max 1 NCU; the Neptune window is limited to about 5 h (about 7.5 h with R-c)" |
| **No scale-out** if the no-data routes cannot push a 0.25 vCPU task over the target | P35 rehearsal first (done 2026-11-16: the local task was CPU-saturated at every level, so it shows the load can saturate 0.25 vCPU but says nothing about the live CPU policy); the request-count target is **3000** (your decision, set from the live estimate: level 25 about 2.5 x and level 50 about 5 x T; with the 2-task maximum, level 50 stays about 2.5 x T per target after scale-out, so the policy stays pinned at 2 through the hold; level 25 ends in about 120 s, before the about 6.5 min scale-out estimate, so scale-out is expected during level 50 and the hold; at 400 ms level 25 is only 1.25 x T, and at 100 ms or less level 5 reaches T); a lower `cpu_target_percent` as a recorded parameter; if still no scale-out, report the CPU values honestly |
| **Firm USD 25** (budget raise declined, section 1b) | Floor 2 since 2026-11-16 (option (i); floor 3 before): project at most 23.00; gate 1 plus the pre-R-b check (spend to date + 3.57 <= 23.00); the 5.8 h Neptune hard stop; tax 0 on credit-covered spend (your decision 2026-11-16; valid while credits cover the spend); one day within 12 h of the first apply; every unevaluated item documented |
| **Elasticity on an empty graph** exercises the HTTP and readiness paths, not graph or LLM work under load | State the setup and limits (the instructor accepts a small, explained experiment); Session 1 evidence for the graph and answer paths |
| **Late code changes** (P21-P27, P30, P35) before a Nov 19 session | Only reviewed, tested changes; R-a (P33) rejected for this reason; fallback day Nov 21 or 22 |
| **Neptune capacity drift** (P32: all 9.05 was serverless capacity, average about 1.8 NCU, never back to 1, even with an empty graph) | A 1-NCU cap is not possible (P34 closed 2026-11-16). Capacity stays min 1 / max 2.5 NCU: planned at 0.297/h, ceiling 0.402/h (2.5 x 0.1608 per NCU-hour) in every cap; the 5.8 h Neptune hard stop bounds the hours. Was: "P34 caps it at 1 NCU (0.1608/h ceiling)" |
| **New public semantic route** (P40) close to the session | Security-focused review; API key, body and topK limits, no query-text logs; fallback load without it |
| **Voyage rate limits under load** | The query-embedding cache bounds Voyage calls by cache misses: at most the distinct questions (about 100-200) per semantic-service task (section 6.3a); P35 checks it; the P26 (c) tier check covers the first pass of misses |
| **R-c margin is negative at plan** (about -1.11 since the 2026-11-16 Neptune correction; -0.29 after the 2026-11-15 S3 Vectors amendment and your Q16 answer; was about 0.14). Your Q17 answer: R-c is expected to be dropped | **R-c dropped** (option (i), 2026-11-16): the 5.8 h Neptune hard stop cannot hold its window. Former control: gate 2 with the measured Neptune capacity; clock cutoffs (15:45 load, 16:45 answers) |
| **Session 1 nonblocking findings** (external review) | N1 → P36 before any paid answer; N4 → P37 digest checks; N5 → P38 tool logging; N9 → P39 deployer removal |

---

## 8. Final-report scale table (template for the Phase 17 report; owner documentation-engineer, P28)

One row per scaled item. Pre-filled values come from the evidence named; `<…>` placeholders name the Session 2 stage that fills them. "Fixture or real" says whether the item ran on fixture data or real data.

| Item | Original requirement (course) | Actual size | Reason for reduction | Cost | Execution time | Limitations | Fixture or real |
|---|---|---|---|---|---|---|---|
| DBLP integrated functional run (works through Hadoop → ER → Spark → stores → API) | at least 100,000 DBLP works; **approved for ScholarChain: about 10.5k and about 50k** (section 1b) | Session 1: **10,577** (local Hadoop, ER and Spark; loaded into Neptune, DynamoDB, S3 Vectors; API answers). Session 2: S = **10,577** on EMR → about 10,000 vectors in S3 Vectors (`<stage a>`); not reloaded into Neptune (budget) | Approved reduction; USD 25 firm (budget raise declined) | Session 1 AWS usage before credits 15.75 (Neptune 9.05, ECS 1.78, EC2-Other 1.72, EMR EC2 0.63 + fee 0.13, ELB 0.68, Route 53 0.50, VPC 0.46, DynamoDB 0.22, S3 0.22, other 0.43; tax 0 on the Bills page so far). Session 2: `<stage a run S>` | Local: Hadoop 37 s, ER 97 s, Spark 180-307 s (Phase 6); P6 S chain 2026-11-16: Hadoop 47 s, ER 165 s, Spark 490 s, copy-out 5 s; EMR `<stage a, per step>` | Convenience slice (8 systems venues, 2005-2026, at most 2,500 per venue, not random); other sources are small unscaled samples; no Session 2 graph reload | real (DBLP dblp-2026-10-03, CC0); other sources real but tiny |
| EMR scale measurement (two sizes) | measurements at several sizes; **approved: about 10.5k and about 50k** | S = 10,577 on EMR (`<stage a>`). **L (48,188 canonical works in the local graph) dropped on EMR**; local evidence (P6, 2026-11-16): Hadoop 132 s, 210 works dropped by the team limit, maximum team 79; ER out of memory at 22g after 16 min; Spark with **ER bypassed (identity pass-through, local only, not the EMR path)** 1,110 s at L against 460 s at S, graph 48,188 works / 76,623 researchers / 320,690 all-years edges at L against 10,578 / 21,819 / 81,181 at S (`target/phase15/lanes/l-bypass-progress.md`, evidence `target/phase15/p6/l-bypass/`) | Approved reduction; L on EMR dropped (ER memory, P25 rule) | Session 1 EMR attempts (no complete run): EC2 0.63 + fee 0.13. Session 2: S `<recorded actual>` (planned 0.56 including boot and idle, at 0.58 per cluster-hour) | `<stage a: per-step times; YARN memory, containers, EC2 CPU (5-min); Hadoop CPU and GC counters; Spark stage, shuffle and executor summary>` | One size on EMR (S); L from local runs only, and its Spark figures bypass ER; r5.xlarge primary and one m5.xlarge core node; ER heap 12g; ER capped at 20,000 comparisons; 5-minute metric granularity | real (L Spark: ER bypassed, disclosed) |
| Graph edges in the scale experiment | at least 1,000,000 edges, subject to budget | Session 1: **328,967** at 10,577 works (100,252 graph + 228,715 coauthor edges). L (local, ER bypassed): **320,690** all-years edges at 48,188 works; S with the same bypass: 81,181 (P6, 2026-11-16). The former estimate "about 1.5M" is replaced by this measurement | Budget; L dropped on EMR | in the EMR row | in the EMR row | L is not loaded into Neptune (cost); measured in local Spark output only, with ER bypassed | real (ER bypassed at L) |
| Neptune graph | (store the processed graph) | Session 1: **78,104 nodes, 328,967 edges**, `LOAD_COMPLETED` (graph-only 3,540 s). Session 2 (R-b): Neptune up about 5 h, **empty** (readiness only) | Not reloaded: USD 25 firm | Session 1: **9.05** (about 32 h, 0.297/h); Session 2 `<R-b>` | — | Not evaluated live in Session 2 (resource limit) | real (Session 1) |
| DynamoDB items | (operational records, caches, run ledger) | Session 1: **166,088** cache writes plus run-ledger records. Session 2: ingest run-ledger records only (`<stage a>`) | No cache reload (budget) | Session 1: **0.22** (Nov 13) | about 2 h in Session 1 | Session 2 shows a live run-ledger record, not the cache | real |
| ER gold set | at least 200 manually reviewed pairs; instructor: 200 reviewed / 194 definitive is **close** | **240 reviewed** (40 dev, 200 held-out); held-out **194 binary + 6 uncertain** → `<P30 result>`; 181 binary without the 22 assisted | — | 0 (offline) | offline (Phase 5) | AI-assisted, self-attested; validation per P31 (exact-ID agreement on 55 of 57 TPs, 17 human overrides of AI proposals, without-assisted sensitivity, optional blind sample with kappa); convenience strata; 0 FP observed; held-out recall 0.792 [0.684, 0.870] (Wilson 95%, P27) | real records, human labels |
| S3 Vectors | at least 10,000 chunks; **approved: up to 10,000 real voyage-4-lite vectors, actual count reported** | Session 1: **104** (5 indexes: 25/25/25/25/4) from 100,765 summaries. Session 2: `<stage a: actual count and per-index split>` from S's EMR output | Approved | Voyage `<…>` (planned 0, free tokens) | Session 1: 0.614 vectors/s; Session 2 `<…>` | Deterministic Spark summaries, not raw abstracts | real (derived from the EMR export) |
| Vector retrieval | ingestion and retrieval must be demonstrated | Session 1: 5 of 5, all neighbours matched, 7 verified pointers, p50 132-187 ms. Session 2: `<stage a B8.7 query smoke>` | — | included above | `<…>` | Sample queries per index; no API-level semantic answers in Session 2 | real |
| 16B benchmark questions | at least 30 questions across 11 topics | **40** asked in Session 1 (8 component, 8 ranking, 14 direct coauthors, 10 path); results 7/8, 7/8, 0/14, 0/10. Session 2: none; R-c dropped (option (i), 2026-11-16: the 5.8 h Neptune hard stop, and gate 2 failed on planned figures) | Budget (USD 25 firm) | Anthropic Session 1 about 0.055; Session 2 none (R-c dropped) | Session 1 about 3 min | Four question kinds only; ranking only over included researchers | real |
| Elasticity | at least four concurrency levels; one scale-out and one scale-in; instructor: a small, explained experiment is acceptable | Session 2 (R-b): semantic-retrieval load (P40, P42) at levels 1/5/25/50 + hold, query-api and semantic-service max 2 tasks, **ALB request-count target tracking** (target `<P35 value>`) plus CPU 60%, **empty graph**, Neptune at min 1 / max 2.5 NCU with a 5.8 h hard stop | USD 25 firm | `<R-b>` (increment about 2.54 planned, including S3 Vectors queries 0.53 and Neptune 1.49; 1.86 before the 2026-11-16 Neptune correction; originally 1.43, 1.91 before the per-level limits) | about 37-50 min plus a quiet window | Retrieval-tier only: no graph or LLM work under load; fixed set of about 100-200 distinct questions (warm-up pass, then embeddings served from the cache); request count bounded by the per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000; 429s reported per level and excluded from latency and throughput (scaling driven by served requests when there are zero 429s); Container Insights off (tasks from ALB healthy hosts and polling); worker fixed at 1 | real deployment, real vectors, synthetic request mix |
| EMR cluster size | (burst or managed scaling in the Phase 15 plan) | 1 primary r5.xlarge + 1 core m5.xlarge (D3, 2026-11-16), no task nodes, no managed scaling; S runs capped at 75 min (was 2 x m5.xlarge, 90 min) | Cost | in the EMR row | in the EMR row | No EMR capacity change will be shown | — |
| LLM answers | (bounded by budget) | Session 1: 55 answers (`claude-haiku-5-5`). Session 2: none planned | Budget | Session 1 about 0.075 (ledger) | — | No temperature 0 on the Anthropic path | real (Session 1) |
| Not evaluated because of resource limits | — | Session 2: live graph load at S; live API answers; coauthor and path reruns; Neptune queries; elasticity of the graph and LLM paths; EMR managed scaling; L on EMR (dropped: ER memory, P25 rule); loading L into the stores | USD 25 firm (budget raise declined 2026-11-15) | — | — | Session 1 evidence covers graph load and answers at 10,577 works | — |

---

## 9. Open questions for the human

### 9.1 Answered (human, 2026-11-15)

Your words: "Plan approved with these answers: Q1 yes (keep USD 3 margin). Q3 yes (cap Neptune at 1 NCU), but first report what made Nov 14 expensive. Q4 yes, I'll review the 6 ER pairs. Q9 yes, narrow ecs:StopTask, granted in an IAM window. Q11 alerts at 18 / 20 / 22. Other §9 questions: your recommended defaults."

- **Amended 2026-11-16: floor 2 (option (i)).** Your Q1 answer above ("keep USD 3 margin") is superseded by your option (i) decision (section 6.4): floor 2, project at most 23.00.
- **Outcome 2026-11-16 for Q3: not possible, see P34.** AWS sets the smallest maximum capacity at 2.5 NCU; your decision of 2026-11-16 sets min 1 / max 2.5 NCU.

**This approves the plan document only. It is not the Session 2 approval record**: Procedure R (approval record and pre-spend receipt) must still exist before every live step.

| Question (revision 2 numbering) | Answer |
|---|---|
| Q1 Floor | **Keep USD 3** (yours). **Amended 2026-11-16: floor 2 (option (i)), project at most 23.00** |
| Q2 Variant | Default taken: **R0, with R-b decided at gate 1**; now also optional R-c behind gate 2 (this revision). **2026-11-16: R-c dropped (option (i))** |
| Q3 Neptune at 1 NCU (P34) | **Yes** (yours). The Nov 14 cause is now confirmed by P32: serverless capacity only (section 6.1a). **Outcome 2026-11-16: not possible, see P34**; capacity stays min 1 / max 2.5 NCU (your decision 2026-11-16) |
| Q4 ER 6 uncertain pairs (P30, P31) | **Yes; you review the 6 pairs** (yours). Default taken for the optional blind second pass: **do it** on a seeded 30-pair sample if time allows before Nov 18; otherwise document the existing checks only |
| Q5 EMR ledger (P25) | Default taken: **raise to 4 runs / 3.36 (was; now 3.53); no retry beyond S and L**. 2026-11-16: both runs go to S and its retry (L dropped on EMR); cap raised 3.36 → 3.53 (your decision, "Raise cap to 3.53"); worst case before actuals 1.68 + 0.84 + 0.84 = 3.36 of 3.53 |
| Q6 L size | Default taken: **about 50,000**, reduced only if the P6 local timing puts the EMR cap at risk (at the time, 90 min; the S cap is now 75 min). **Outcome 2026-11-16: L dropped on EMR** (ER out of memory at 22g locally); local evidence only |
| Q7 DBLP archive download (P21) | Default taken: **approve one 1.1 GB download** from the pinned URL under a network cap (record it in the dataset evidence) |
| Q8 Ingest batching (P26) | Default taken: **batched ingest preferred**; unbatched, overlapping run L, is the fallback |
| Q9 Stop-task permission (P11) | **Yes, narrow `ecs:StopTask`, granted in an IAM window** (yours) |
| Q10 CPU target | **Superseded:** scaling is load-driven by the request-count policy (P41); the CPU target stays 60 |
| Q11 Budget alerts (P0) | **18 / 20 / 22** (yours) |
| Q12 Tax column | Default taken: **column A primary**, B shown as a check; recheck after the December invoice. **Superseded 2026-11-16: tax 0 on credit-covered spend (your decision); column B dropped** |
| Q13 Residual state (P18) | Default taken: **plan against the residual state** (no move-aside), proven by P18's test |
| Q14 Keys | Default taken: **create both keys in the pre-session** (Voyage for the stage-a ingest; Anthropic because ECS cannot start with an empty key container; R-c also uses it) |
| Q15 Benchmark coverage | Default taken: **keep the 40-question benchmark** and document the topic gap |

### 9.2 Revision 3 questions: answered (human, 2026-11-15)

Your words: "1. Yes to /v1/semantic/retrieve, with the same API key as the other routes, bounded top-k and query length, rate limiting, typed errors, tests, and no data beyond what the internal route returns. 2. Yes, keep R-c optional behind the ≤ 22 gate. 3. Yes, 15b->16b:28. 4. Yes, remove the deployer role in final cleanup. P40 cutoff: if it isn't reviewed and committed by Wed Nov 18 at 12:00 CST, use the fallback (request-count scaling on health-check load, labelled as weaker evidence). No last-minute changes."

| Question | Answer and where it is applied |
|---|---|
| 1. Public semantic route | **Yes**, with the listed requirements: P40 acceptance check (1)-(9); cutoff Wed Nov 18, 12:00 CST (P40, schedule 6.7) |
| 2. R-c | **Yes, optional behind the project total ≤ 22.00 gate** (gate 2, sections 5.4 and 6.4). **Superseded 2026-11-16: R-c dropped (option (i))** |
| 3. Ledger transfer | **Yes:** `APPROVED_LLM_TRANSFER=15b->16b:28` (R-c step 6) |
| 4. Deployer removal | **Yes, in final cleanup** (P39, section 5.5 step 4) |

The Session 2 approval record (Procedure R) is still yours to write before any live step.

### 9.3 Questions from the 2026-11-15 amendment (S3 Vectors query cost): answered (human, 2026-11-15)

Your Work order 2 answers (2026-11-15) put the S3 Vectors query cost into R-b (section 6.3a), which raised the two questions below. Your words: "Q17: accept. Keep R-b as designed and expect R-c to be dropped (document why in the report). Q16: accept the existing per-level limits only if the worst case (198,600 queries: S3 Vectors query and data-processed charges plus Voyage cache misses) is already in R-b's worst case and keeps the project ≤ USD 22. Show the numbers. If it doesn't fit, lower the per-level limits to the minimum that still shows scale-out to 2 tasks and scale-in. Also confirm the rate-limit setting from P35 won't throttle the heaviest load level, so scaling is driven by served requests, not 429s."

**Answers as applied:**

- **Outcome 2026-11-16:** the Q16 figures below were applied on 2026-11-15 at the 1-NCU Neptune rate. After the P34 correction the condition no longer held at caps (R-b worst case 4.05, R0 + R-b cap 7.62, project 23.45 > 22.00). You then decided option (i) (section 6.4): floor 2, project at most 23.00, a 5.8 h Neptune hard stop (`E_b` 3.57, cap 7.14, project 22.97; 7.15 and 22.98 since L was dropped and the D3 cluster), the per-level limits kept. R-c is dropped, which settles Q17.
- **Q16, option (a) with your condition, which holds (as applied 2026-11-15):**
  - S3 Vectors at 198,600 queries: requests 0.4965 + data processed 0.0325 = 0.5290, carried as **0.53**. With up to 200 warm-up requests: 0.5296, still 0.53.
  - Voyage cache misses: at most 0.016, carried as **0.02**.
  - R-b worst case: 2.61 - 0.80 + 0.53 + 0.02 = **2.36**.
  - R0 + R-b cap: **5.93**.
  - Project at caps: 15.83 + 5.93 = **21.76 <= 22.00**.
  - The per-level limits 600 / 3,000 / 15,000 / 30,000 / 150,000 are kept and **required** (P42); they were not lowered.
  - The rate limit is confirmed by P35 acceptance (5) and (6): `r_S2` is at least 2 x the measured peak served rate per task at level 50, with burst 2 x `r_S2` (observed 2026-11-16: peak 1,737 per second, `r_S2` = 3500, `b_S2` = 7000), and there are zero 429s at every level (observed: 0 of 198,750). R-b's analysis states that scaling was driven by served requests (section 5.3).
- **Q17, option (a) (as applied 2026-11-15):** R-b as designed; R-c is expected to be dropped. Gate 2 is still checked with the measured `X_spent`. The report states why: planned `X_spent` about 3.02 against 2.73 (section 6.4). Since 2026-11-16: 3.47 against 2.36, and R-c is dropped under option (i).

The original question table follows for the record:

| Question | Facts | Options (the default is marked) |
|---|---|---|
| **Q16 R-b S3 Vectors cap** | At the hard backstop of 300,000 queries per run (USD 0.80), R0 + R-b at full caps is 6.18, which is **0.01 over** `S` = 6.17 (project total 22.01). Gate 1 (threshold 2.81) still keeps the actual session inside the floor. At the code default `r` = 50, the limiter bound is 150,200 queries (USD 0.40). Under the planning assumption, though, P35 would set `r_S2` to at least 250, and then the backstop binds. | **(a) default:** P42's per-phase caps keep the 15B values (600 / 3,000 / 15,000 / 30,000 / 150,000 = 198,600 per run). S3 Vectors cap 0.53; R-b cap 2.34; R0 + R-b cap 5.91 (project 21.74); gate 1 threshold 3.08. The planned count is then also capped at 198,600 (0.53).<br>(b) Keep the 300,000 backstop and rely on gate 1 (2.81).<br>(c) Hold `r_S2` at most 98 per task (`Q_max` = 3,000 x 98 + 2 x 196 = 294,392 queries, USD 0.79; R0 + R-b cap 6.17, which fits exactly). This may throttle level 50, against your P40 answer 2. |
| **Q17 R-c after the S3 Vectors cost** | Planned `X_spent` at the end of R-b is about 3.07 against the gate-2 limit of 2.73 (margin about -0.34; was +0.14). R-c fails gate 2 on planned figures. It could pass only if R-b's semantic queries stay below about 90,000 (S3 Vectors at most 0.24), or if the measured throughput is far below the 200 ms assumption. | **(a) default:** keep R-b as designed and expect R-c to be dropped. Gate 2 is still checked with the measured `X_spent`, and the report says why if R-c is dropped.<br>(b) Cap R-b's semantic queries at about 90,000 per run through the P42 per-phase caps (for example a shorter hold). This weakens the elasticity load, an experiment change for you to decide.<br>(c) Lower `r_S2` so that levels 25 and 50 are throttled, against your P40 answer 2. |

---

## 10. How this draft was produced (provenance)

- Read-only commands only: `sed`, `grep`, `ls`, `du`, `cat` and small `python3 -I` readers over repository files, git-ignored Session 1 and Phase 6 evidence and local outputs; `curl` of the public course README and the public AWS pricing and docs pages in section 2.
- No AWS, Anthropic or Voyage API call, no AWS CLI, no Terraform or `sbt` run.
- Not read: `*.local.tfvars`, `*.tfstate*`, `~/.aws`, `.env`, private keys, `target/phase14/private/`.
- The Wilson intervals in section 3a are derived from recorded counts and must be reproduced by the owner's script (P27).
- Amendment of 2026-11-15 (work order P40-D): the S3 Vectors prices come from the coordinator's read of the public S3 pricing page, which the documentation-engineer did not re-read. The code facts in section 6.3a come from read-only `grep` and `sed` over `modules/services`, `modules/storage`, `load-tests/loadgen.py`, `load-tests/config/load-profile.v1.json`, `experiments/manifests/15b-ecs-scaling.json` and `scripts/billing/budget_*.py`. The arithmetic was checked with a `python3 -I` one-off calculation. No AWS, Anthropic or Voyage call was made. **Disclosure:** during this amendment, a recursive `grep` for `SCHOLARCHAIN_SEMANTIC_INDEX` over `infra/terraform` also matched lines in the local Terraform state files (`terraform.tfstate*`), contrary to the not-read rule above. Nothing from that output is used or copied into this file; the index fact in section 6.3a comes from the Scala source.
- Amendment of 2026-11-16 (work order P41-D): the P41 defaults come from `docs/agent-runs/phase-15/prompt.md` (Work order 3) and the R2 and R3 wording from `docs/agent-runs/phase-15/review.md` (Work order 2, review 1). The line numbers were re-read at HEAD `cceb1f5` with `grep -n` and `sed -n` over `SemanticApi.scala` (embed call line 98, `vectors.query` line 100), `AwsComposition.scala` (lines 256-257) and `AwsConfig.scala` (line 251). No AWS, Anthropic or Voyage call; no Terraform or `sbt` run. Follow-up the same day: the R2 rule and the P35 item (5) wording come from your P41-D follow-up answers, recorded verbatim in `docs/agent-runs/phase-15/prompt.md` ("P41-D follow-up answers"). The 2 × distinct-questions note was checked against section 6.3a's bound (distinct questions × semantic-service task starts; 2 starts with one scale-out). No Voyage usage figure has been read. Second follow-up the same day: the R-b-window and 4 × wording come from your answers 1(a) and 2(a), recorded in `docs/agent-runs/phase-15/prompt.md` ("Second follow-up"), and the caveats from section 6.3a (task starts and uncoalesced duplicate misses).
- Amendments of 2026-11-16 (P34 impossible; then option (i)): the human's decisions come from `docs/agent-runs/phase-15/prompt.md` ("Relaunch, Neptune and P34 decisions" and "R-b option decision", both verbatim) and the coordinator's brief and decision update. The Neptune capacity fact comes from the infra-engineer's read of the Amazon Neptune User Guide, recorded in `docs/agent-runs/phase-15/repairs.md` E1 and `infra/terraform/README.md` ("Neptune capacity (P34, not changed)"); the documentation-engineer did not re-read the AWS page. `phase12b.tf` lines 22 and 42 and `infra/terraform/tests/phase15_elasticity.tftest.hcl` were read with `grep -n`; the cleanup order was read from the Phase 14 runbook (B13 and C1-C3). The figures were checked with `python3 -I` one-off calculations; the coordinator's figures reproduce when the rate differences are not rounded first. Values derived by the documentation-engineer beyond the coordinator's list: the R-b planned increment (2.54), the gate-2 x 1.11 check (`X_spent <= 0.20`, dropped with column B on 2026-11-16), the low-scenario row at 5.8 h (6.08; 21.91; 24.26), the pre-R-b planned figure (20.75) and the gap of about 3 min in section 5.5. The scale-out time (about 6.5 min), the deletion time (about 18 min) and every clock duration are estimates. No AWS, Anthropic or Voyage call; no Terraform or `sbt` run.
- Follow-ups of 2026-11-16 (conservative clock, tax decision): the pre-destroy duration comes from the timestamps and file times of the Session 1 logs `cleanup-prepare-plan.log`, `cleanup-prepare-dry.log`, `cleanup-prepare.log`, `cleanup-list-1.log`, `cleanup-list-1b.log`, `cleanup-pass-1.log`, `cleanup-list-2.log`, `cleanup-pass-2.log` and `state-sha-before-cleanup.log` under `target/phase14/evidence/14b/` (git-ignored), read with `grep` and `stat`, and from the Session 1 decision record (`b8-3-graph-only-decision.md`, B13 and C2-C3 entries). Nothing under `target/phase14/private/` was read. The tax decision is quoted from the coordinator's relay of your words.
- 4a review fixes (2026-11-16): the fallback feasibility was checked read-only at HEAD `7a02de2` with `git show` (the working tree holds unreviewed lane drafts of some of the same files) over `EmbeddingManifestMain.scala`, `LiveEmbeddingIngestMain.scala`, `Phase6EmbeddingSource.scala` and `EmbeddingManifest.scala`, and with `grep -n` over `phase-14-live-session.md` and `14c-templates.md`. The latest-`T_N0` estimate uses the Session 1 cleanup log times and the schedule in 6.7. No P6 harness exists yet; the retention path is a proposal.
- L-dropped and D3 pass (2026-11-16): the decisions come from `docs/agent-runs/phase-15/prompt.md` ("L, second size" to the end) and the coordinator's brief. The P6 and L figures come from the git-ignored lane logs `target/phase15/lanes/p6-progress.md`, `lane-A-p6-progress2.txt`, `lane-A-progress.md` and `l-bypass-progress.md`, read with `grep` and `sed`. The retention directory listing and its `SHA256SUMS` sha256 were checked with `ls` and `shasum`. The `--record-actual` lines were read with `grep -n` from the working-tree `scripts/run-bounded-pipeline.sh` and `scripts/lib/budget.py` (uncommitted D3 drafts). The arithmetic follows the plan's own rounding method, stated in section 6.4.
- P35 pass (2026-11-16): the rehearsal figures come from `docs/agent-runs/phase-15/evidence/p35/rehearsal/results-summary.md`, `rehearsal/per-level-results.json`, `rehearsal/metrics-after.txt` and `loadgen/derived/summary.json`, and the agent report at the end of `docs/agent-runs/phase-15/owner-report.md`; the decision and the coordinator defaults (3500, 7000) from the last section of `docs/agent-runs/phase-15/prompt.md`. The live per-level estimates (about 300, 1,500, 7,500 and 15,000 per minute per task) follow from the 200 ms planning assumption (section 6.3a), not from a measurement. No AWS, Anthropic or Voyage call; the evidence directories were read-only.
- Every Session 2 figure is an estimate until observed live.
