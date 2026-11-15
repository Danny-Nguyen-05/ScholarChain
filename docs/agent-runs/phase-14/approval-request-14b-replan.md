# Phase 14 approval request — Replan 2026-11-08 (USD 25 course cap)

Prepared by the coordinator on 2026-11-08 from the agent reports and the user's recorded decisions (`prompt.md`, "Subphase 14B — replan …" to the end). The plan block it implements is "Replan 2026-11-08" in `phase14.md`.

- **What it supersedes:** the 14A approval request, for cost and for the window. The 14A record formats and machinery stay unchanged.
- **What it is not:** an approval. Nothing live has run. Every figure below is modeled, not observed.
- **Step-by-step commands:** in [`docs/runbooks/phase-14-live-session.md`](../../runbooks/phase-14-live-session.md).

## 1. What you are approving

| Item | Value |
|---|---|
| Project ceiling | USD 25, cumulative across all phases, including USD 0.34 already spent |
| Budget alerts | AWS Budgets at USD 10, 15 and 20 (ACTUAL, absolute). Alerts do not stop charges; our own caps do |
| Session | One live session of about 36 h, **hard stop at 37 h** (user decision 2026-11-09, review F1; was 42 h). Cleanup starts no later than **H35** |
| Session order | 14B apply, deploy and smoke → 14C data load and vectors (8C) → 15A EMR runs → 15B experiments → 16B live evaluation → 17 demo video and final smoke → evidence archive → cleanup (delete everything) |
| In-session stops | Short go/no-go checks after each stage. The full independent review runs after cleanup, on the archived evidence |
| Region | us-east-2 |

## 2. Preconditions (all must be true before the base plan)

1. **Bedrock quotas** in us-east-2 are non-zero for Claude Haiku 4.5 (US cross-region profile) and Titan Text Embeddings V2. One playground call to each succeeds.
   - The first Haiku call also creates the AWS Marketplace subscription.
   - No application role gets Marketplace permissions.
   - Status 2026-11-08: account-wide Bedrock quotas are 0. The Support case is open; you escalate by chat on 2026-11-10.
   - **Decision point 2026-11-12.** The fallback is the direct Anthropic API for synthesis and a 256-dimension third-party embedding API (`evidence/14b/replan/fallback-note.md`). The Anthropic client is prepared offline on branch `phase14-anthropic-fallback` and is not merged.
2. **Budget modified** to USD 25 with the 10/15/20 alerts, through the reviewed billing modify path, applied by you with the billing-deployer profile. This is the first live step.
3. **Deployer root applied once:**
   - phase14-main, boundaries and the ACM permissions;
   - the delete-object grant for cleanup;
   - the four operator roles (loader, reader, cleanup, pipeline) with `operator_run_prefix`.
   - `deployer.tfstate` is backed up first.
4. **Pre-session commit:**
   - all reviewed changes;
   - the refreshed `reviewed-pins.json`;
   - `EMR_PRICING_CONFIRMED_BY_HUMAN=true`;
   - the rendered experiment manifests (real sha256, bucket tokens only);
   - `approval-14c.md` (caps and wording only, including the N11 disclosure).

   HEAD at the base plan is the approved commit.
5. **Private settings in place:**
   - secrets in Secrets Manager;
   - the private tfvars values (runbook A8);
   - `~/.aws/config` profiles with sign-in checked;
   - the Cloudflare CAA check;
   - `llm_budget.py init` run.

## 3. Cost plan (modeled, before credits)

**Shape:**
- Neptune Serverless at 1 NCU.
- One NAT gateway.
- ALB with 1 LCU.
- Four Fargate tasks at 0.25 vCPU / 1 GiB.
- Container Insights and dashboard off.
- Embedding worker fixed at 1.

**Rates:** us-east-2 public prices, retrieved 2026-11-08 (infra-engineer survey). Haiku rate confirmed by you on the Bedrock pricing page.

### 3.1 Per-hour run rate

| Component | USD/h |
|---|---:|
| Neptune Serverless, 1 NCU | 0.1608 |
| NAT gateway + EIP | 0.0500 |
| ALB + 1 LCU + 2 public IPv4 | 0.0405 |
| Fargate, 4 × (0.25 vCPU, 1 GiB) | 0.0583 |
| **Run rate** | **0.3096** |

The tunnel task (0.25 vCPU / 0.5 GiB, about USD 0.012/h) runs only during the 14C load: about USD 0.05.

### 3.2 Session totals

The "Credit" column says whether the USD 140 of AWS credits cover the line.

| Line | Credit | 36 h | 42 h (hard stop) |
|---|---|---:|---:|
| Run rate | credit-covered | 11.15 | 13.00 |
| Fixed: KMS key (prorated), 4 secrets, Cloud Map private hosted zone 0.50 (not prorated; 1.00 if the session crosses a month boundary), Cloud Map resources 0.30, alarms | credit-covered | 1.17 | 1.20 |
| Usage: NAT data, logs, S3, DynamoDB writes (about 166k), Neptune storage and I/O, KMS requests, S3 Vectors, SQS, Step Functions, misc | credit-covered | 2.41 | 2.41 |
| Tunnel task (14C only) | credit-covered | 0.05 | 0.05 |
| Titan V2 embeddings, cap (expected about 0.01–0.03) | credit-covered | 0.30 | 0.30 |
| EMR, 3 runs × 90 min cluster time (2 × m5.xlarge at 0.24/h) | credit-covered | 2.52 | 2.52 |
| **Claude Haiku 4.5, cap (AWS Marketplace)** | **out of pocket, on your card** | **1.50** (now 1.33, §3.2 decision) | **1.50** (now 1.33) |
| Already spent | | 0.34 | 0.34 |
| **Total** | | **19.44** | **21.32** |
| **Headroom against USD 25** | | **5.56** | **3.68** |

- With EMR at its full cumulative cap of USD 3.00, the 42 h total is 21.80, leaving USD 3.20 of headroom.

**With sales tax (review N1, user decision 2026-11-09).** Tax counts toward the USD 25. The billing address is in Chicago (60612), so the plan assumes about 11% (Chicago's lease tax on cloud services) until you confirm the exact rate from the AWS bill.

How the tax is applied:
- It is applied to every new line, the Haiku Marketplace line included.
- The USD 0.34 already spent is taken as billed.
- Whether credits cover the tax is not confirmed. Either way it counts toward the cap.

| Case | New spend | Tax at 11% | Total with tax | Headroom against USD 25 | Floor of USD 3 holds? |
|---|---:|---:|---:|---:|---|
| 36 h | 19.10 | 2.10 | **21.54** | **3.46** | yes |
| 42 h (hard stop) | 20.98 | 2.31 | **23.63** | **1.37** | **no** |
| 42 h, EMR at its full USD 3.00 cap | 21.46 | 2.36 | **24.16** | **0.84** | **no** |

- **Hourly cost with tax:** about USD 0.35/h (0.3096 run rate plus about 0.005 of prorated fixed cost, times 1.11). Each hour past 36 h removes about USD 0.35 of headroom.
- **If Neptune scales to 2.5 NCU** (the module's maximum, `infra/terraform/environments/course.local.tfvars.example:171`):
  - Each hour at 2.5 NCU costs 1.5 × 0.1608 = USD 0.2412 more before tax, about 0.268 with tax.
  - Every 10 such hours add about USD 2.68.
  - At 2.5 NCU for the whole session, the totals with tax would be about USD 31.18 (36 h) and 34.88 (42 h), well over the cap.
  - At the 42 h hard stop, the 1.37 of headroom absorbs only about 5 hours at 2.5 NCU before the total reaches USD 25.
  - Neptune scaling is therefore the largest unbounded cost risk. It is not capped by our scripts, only by the module's 2.5 NCU maximum.
- **Floor check:** with tax, the USD 3 headroom floor holds at 36 h but **not at 42 h** (1.37, or 0.84 with EMR at its full cap). No cap has been changed. Choose one or a combination:
  1. **Shorter hard stop.** Headroom stays at least 3 up to about **37 h** (21.54 + 0.35 × 1.3 ≈ 22.0). Cleanup would start by about H35.
  2. **Lower floor.** For example USD 1.25, which leaves almost nothing for the 8–24 h billing lag, Neptune scaling or tax-rate error.
  3. **Cost cuts**, approximate savings with tax:
     - drop one EMR run: about 0.93;
     - lower the Haiku cap from 1.50 to the 1.33 the buckets actually need: about 0.19;
     - each hour cut from the session: about 0.35;
     - cap Neptune at 1 NCU (`max_capacity` 1; needs an infra-engineer change and review): removes the scaling risk but may slow the 14C load and the 15B load test.
   Reaching a headroom of at least 3 at 42 h needs about USD 1.63 of cuts (2.16 with EMR at its full cap).
- **Decision (user, 2026-11-09, review F1): option 1, hard stop at 37 h, cleanup starting by H35.** No cap or pin changed. Projection at the 37 h hard stop, with 11% tax:

  | Case | New spend before tax | Tax | Total with tax | Headroom |
  |---|---:|---:|---:|---:|
  | 37 h, planned EMR (3 runs × 90 min, USD 2.52) | 19.41 | 2.14 | **21.89** | **3.11** (≥ 3) |
  | 37 h, EMR at its full USD 3.00 cumulative cap | 19.89 | 2.21 | **22.42** | **2.58** (< 3) |

  - The floor holds on the planned figures. It would not hold if EMR reached its full USD 3.00 cap, which cannot happen within the per-run 90-minute limits (about USD 0.84 each).
  - Each pre-spend receipt carries the then-current honest reserves, so `deploy.sh` enforces the floor stage by stage. A stage refused below 3 is the signal to stop new paid work and go to cleanup (runbook E12).
  - The hourly figure "about USD 0.31" in this section is **before tax**. With tax it is about USD 0.35/h (review F2).
- **Second decision (user, 2026-11-09): "Caps = planned use".** It fixes the pre-spend receipt, which reserves the full caps. With tax, the H0 receipt as first written would show 25 − 0.34 − 1.11 × (19.58 reserves + 0.50 margin) = **USD 2.37**, so `deploy.sh` would refuse base-apply at the floor of 3. The caps are therefore set to exactly the planned use:
  - Claude Haiku 4.5 shared cap: **USD 1.50 → 1.33**, the buckets 10/60/40/5 = 115 × 0.01155 = 1.32825.
  - EMR cumulative cap (`EMR_CUMULATIVE_CAP_USD`): **USD 3.00 → 2.52**, which is 3 runs × 0.84.
  - Titan: unchanged at 0.30 (N4, accepted).

  **Current projection (these caps, 11% tax). It supersedes the earlier tables where they differ:**

  | Check | Before tax | Total with tax | Headroom against USD 25 |
  |---|---:|---:|---:|
  | Session to the 37 h hard stop (new spend 19.24) | 19.24 + 0.34 | **21.70** | **3.30** |
  | H0 pre-spend receipt: reserves 18.93 (hours to H36, fixed and usage, tunnel, Titan 0.30, EMR 2.52, Haiku 1.33) plus a 0.50 allowance | (18.93 + 0.50) × 1.11 = 21.57, plus 0.34 reported | **21.91** | **3.09** (≥ 3) |

  - Spare slack is gone. A Haiku answer that costs more than the planning figure, or an EMR run above its estimate, now hits the cap before its bucket or run count is used up.
  - If any stage's receipt comes out below 3, stop new paid work and go to cleanup (runbook E12).
- Every hour the stack stays up costs about USD 0.31 before tax (about 0.35 with about 11% tax).
- Billing data lags 8–24 h, so the pre-spend receipts carry an unreported-usage allowance, and the caps, not the alerts, stop spend.
- Credits cover AWS usage. The course cap applies to usage regardless of credits.

### 3.3 Haiku answer buckets (hard stops; ledger `load-tests/llm_budget.py`)

Planning figure: about USD 0.01155 per answer (planner + synthesis at USD 1.10 input / 5.50 output per 1M tokens on the `us.` route).

| Bucket | Answers | About USD |
|---|---:|---:|
| 14C real-data smoke | 10 | 0.12 |
| 15B load test (10 / 15 / 20 / 15 at concurrency 1 / 5 / 25 / 50) | 60 | 0.69 |
| 16B live evaluation | 40 | 0.46 |
| 17 demo video + final smoke | 5 | 0.06 |
| **Total** | **115** | **1.33 of 1.33** (the cap was 1.50 until the 2026-11-09 "caps = planned use" decision, §3.2) |

- Each bucket is a hard stop.
- The USD 1.33 total is the backstop (it was 1.50 before 2026-11-09).
- Spare answers move between buckets only with your approval line `APPROVED_LLM_TRANSFER=<from>-><to>:<N>`.

### 3.4 Titan split (credit-covered)

- USD 0.25 for the 8C ingest (10,000 vectors, 2 attempts).
- USD 0.05 for the 8C query smoke.
- **No reserve is left (review N4).** 0.25 + 0.05 is the whole USD 0.30. The query-time embeddings that the deployed services make during 15B and 16B are outside both caps, and no script or service caps them.
  - Estimate: about 1,000 queries × about 50 tokens ≈ 50,000 tokens. At USD 0.02 per 1M tokens that is about USD 0.001, plus 11% tax, still about 0.001.
  - Before the approval record, either accept this uncapped, negligible line, or set a small reserve, for example ingest 0.24 / smoke 0.05 / query-time 0.01.

### 3.5 Unavoidable residuals

- The hosted zone month (USD 0.50).
- Late-posting usage.
- The KMS key and secrets cost nothing once pending deletion.

## 4. Pins and caps that change

| Pin | Old | New | Where |
|---|---|---|---|
| Pre-spend minimum headroom | 20 | **3** | `scripts/config/release.conf` `PRESPEND_MIN_HEADROOM_USD` |
| Cleanup-stage headroom floor | — | **none**: cleanup-prepare has no headroom floor, so a negative headroom is accepted (review B2, user decision 2026-11-09). The earlier proposal of a floor of 0 is superseded | not a config key: `scripts/deploy.sh` passes `--no-headroom-floor` to `scripts/lib/verify.py` only for `--stage cleanup-prepare`; `PRESPEND_MIN_HEADROOM_CLEANUP_USD` is removed |
| EMR cumulative cap | 9.50 | **2.52** (3 runs × 0.84; was 3.00 in the replan, lowered 2026-11-09 to "caps = planned use"; per-run cap and run count unchanged; each run capped at 90 min ≈ 0.84) | `EMR_CUMULATIVE_CAP_USD` |
| Claude Haiku 4.5 shared cap | — | **1.33** (was 1.50 in the replan, lowered 2026-11-09; buckets unchanged) | `experiments/manifests/llm-allocation.json`, `load-tests/config/load-profile.v1.json` `shared_cap_usd` |
| Pipeline local-sample ceiling | 1000 | **12000** (pipeline-specific; Phase 4 smoke keeps 1000) | `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS` |
| Budget | USD 200, PERCENTAGE 50/80/100 | **USD 25, ACTUAL ABSOLUTE_VALUE 10/15/20** | `infra/terraform/billing-bootstrap` |
| Query-api health-check grace | none | **300 s**, tunable in private tfvars | `query_health_check_grace_period_seconds` |
| Haiku buckets | — | 14c 10 / 15b 60 / 16b 40 / 17 5 | `experiments/manifests/llm-allocation.json` |

## 5. What changed in the repository (offline; test status in section 8)

| Area | Change | Owner |
|---|---|---|
| Shape | Container Insights and dashboard flags; Fargate 256 CPU; explicit target-group timing; 300 s grace with root variable | infra-engineer |
| ACM | Certificate created in base-apply without waiting; validation only in runtime-apply; validation record and ALB DNS outputs | infra-engineer |
| Tunnel | One-off Fargate task in the graph-service security group with ECS Exec channels only; enabled in the first runtime plan | infra-engineer |
| Outputs | Neptune writer endpoint, port, cluster resource id | infra-engineer |
| Cleanup | Delete everything: no `prevent_destroy` on buckets and vectors; `force_destroy` only in cleanup mode; teardown covers buckets, vectors, KMS, log groups, ACM, tunnel role, deployment role; deployer object-delete grant | infra-engineer |
| Deployer | phase14-main ACM actions; runtime boundary ECS Exec channels; four MFA operator roles (4 h, `aws login`) for loader, reader, cleanup and pipeline, removed at cleanup | infra-engineer |
| Billing | Reviewed modify mode; USD 25 budget. New and changed files hold the account ID only as a hash or private render. The billing executor still uses its pre-existing Phase 12 literal (`scripts/billing/budget_execution.py:26`), and the new modify path relies on it (`:1033`, `:1059`); this is kept under decision 3, existing Phase 12 mentions stay (review N5) | infra-engineer |
| Scripts | `upload-slice.sh`; `upload-emr-artifacts.sh`; experiment bucket tokens; `smoke-test.sh --checks`; ER JAR collected by `package.sh` | infra-engineer |
| Build | Reproducible entity-resolution job JAR plus EMR artifact manifest | build-engineer |
| Spark | Neptune CSV parts capped at 16 MiB; real slice re-exported (run `f6e63b4b`, 78,104 nodes, 328,967 edges) | spark-engineer |
| Storage | Bounded runtime artifact (≤ 10,000 rows, 16 MiB; selection rule reported); loader timeout flags; credential check; Phase 8 R3 fixed | storage-engineer |
| RAG | Phase 8 N15 fixed (smoke caps); embedding token cost bound before any Titan call; 14C templates | rag-engineer |
| Experiments | Load generator (non-LLM by default); 15A manifests for three dataset sizes (2,648 / 5,290 / 10,577 publications); 15B and 16B manifests; Haiku bucket ledger | experiment-engineer |
| Tests | Independent tests for every item above; 53 final mutants caught | test-engineer |

## 6. Pinned files you refresh before committing

These 24 `source_freeze` rows in `scripts/billing/reviewed-pins.json` have drifted (`evidence/14b/replan/pin-drift-final.txt`). Refresh them with the one-liner from 14A §7.

**infra/terraform, top level**
- `README.md`
- `main.tf`
- `outputs.tf`
- `variables.tf`
- `phase12b.tf`
- `phase12b-variables.tf`
- `tests/phase12a.tftest.hcl`

**infra/terraform, billing roots**
- `billing-bootstrap/README.md`
- `billing-bootstrap/main.tf`
- `billing-bootstrap/tests/budget.tftest.hcl`
- `billing-bootstrap/variables.tf`
- `billing-execution/README.md`

**infra/terraform/modules**
- `datalake/main.tf`
- `identity/variables.tf`
- `neptune/outputs.tf`
- `observability/main.tf`
- `observability/outputs.tf`
- `observability/variables.tf`
- `runtime/compute.tf`
- `runtime/outputs.tf`
- `runtime/variables.tf`
- `s3vectors/main.tf`

**tests/infra**
- `README.md`
- `terraform_source_guard.py`

Beyond those rows:
- The billing modify path adds a `modify` object (plan sha256, bytes, the private public-input sha256, config rows) after you make the billing plan.
- Every earlier billing gate's `wrapper_files` is obsolete.
- `git add` all new files before the commit.

## 7. Records and receipts

The formats are unchanged from 14A §4 and `scripts/README.md`.

- **Approval record lines:** `APPROVED_STAGE`, `APPROVED_COMMIT`, `APPROVED_ACCOUNT_SHA256`, `APPROVED_REGION`, `APPROVED_ENVIRONMENT`, `APPROVED_PRESPEND_SHA256`, and, for plan stages, `APPROVED_PLAN_SHA256` and `APPROVED_RECEIPT_SHA256`.
- **New stages under the same machinery:** a runtime-apply for the runtime-artifact pointer, a runtime-apply that enables EMR, the per-run EMR approval records (`--approval target/phase14/approvals/emr-run-<n>.md`), and the EMR upload record.
- **Pre-spend receipt:** `remaining_headroom_usd` ≥ 3 for every spending stage. Cleanup-prepare has no floor: any finite number, negative included, is accepted, and the run prints `PRESPEND: cleanup-prepare has no headroom floor (…)`. The cleanup receipt must still exist, match `APPROVED_PRESPEND_SHA256`, be fresh (24 h), confirm monitoring and carry all four numeric cost fields. `reserves_usd` covers what is still to come in the session.
- **Commit freeze:** from the base plan to the end of cleanup, nothing is committed. Evidence goes to `target/phase14/` (runbook section D).

## 8. Gate results

Observed 2026-11-09, after review 5 approved. Details: `test-report.md`, "Subphase 14B — final full check (snapshots 9 and 10)". This replaces the snapshot 8 results; those remain in `evidence/14b/replan/`.

- **Seven-gate check, clean snapshot 10** (`07e1a83f36fb38889f6a6d48911333a16354c436` on base `e2f0b01`; 5,791 files identical to the working tree before the run, 1,640 non-docs files identical after it): `RESULT: PASS gates=7`, `check.sh exit 0`.
  - constitution, hooks, shell, python: PASS.
  - terraform: PASS (139 s); test runs 12, 19, 103, 40, 6, 246 passed (426), 0 failed.
  - script-tests: PASS (3,682 s); `scripts/tests` 1,006 OK (required classes `RealStateBindingTests` 7 and `RouteOwnershipTest` 6 executed, 0 skipped); `phase12d-spike` 78 OK; billing 112, 61, 39 OK; `tests/scripts` 433 OK; `tests/infra` 426 OK. Total 2,155, 0 skipped.
  - sbt: PASS (976 s); JDK 17.0.20.1; 0 failed, 1 canceled (the usual one); `[success] Total time: 969 s`.
  - Evidence: `evidence/14b/final/check-full-final.txt` (sanitized), `evidence/14b/final/snapshot10-identity.txt`.
- **Snapshot 9** (`20734a36…`) failed one test: the account scan flagged `review.md:909`, where the verbatim review 5 text quoted the 12-digit synthetic placeholder from `scripts/tests/test_pipeline.py:438`. The digits were replaced with `<placeholder from test_pipeline.py:438>` and a note (user decision 2026-11-09); no code changed. Evidence: `evidence/14b/final/check-full-snapshot9-fail.txt`.
- **Live `sbt check`:** EXIT 0. 1,415 tests across nine suites, 0 failed, 1 canceled; test marker updated (`evidence/14b/final/sbt-check-live-summary.txt`).
- **`git diff --check`** (untracked files included with `git add -N`, index restored): exit 0 (`evidence/14b/final/whitespace.txt`).
- **Pin drift:** 24 of 209 (§6; `evidence/14b/final/pin-drift.txt`). Refreshed by the user before the commit.

## 9. Known risks (unverified until live)

- IAM completeness of every new grant. An AccessDenied means a routed repair and a new deployer or base plan.
- S3 enforcement of `if-none-match` in the operator policies.
- ECS Exec port-forwarding and SigV4 through the tunnel.
- `aws login` session length and the MFA flag in its credentials.
- Fargate 0.25 vCPU / 1 GiB for the JVM services.
- The 300 s grace period.
- Whether EMR re-creates a cluster after it terminates.
- The Haiku 4.5 retirement notice: its earliest retirement date has passed.

## 10. Open pre-session items (found while writing the runbook; each must be closed before the commit freeze)

| # | Item | Owner |
|---|---|---|
| 1 | Where the local `--er-policy`, `--er-config` and `--spark-config-template` files come from. They are needed for the manifest hashes and the EMR upload | experiment-engineer |
| 2 | Real `include-ids.txt` (runtime artifact), `real-query.json` (real-data smoke), `questions.txt` and `node-ids.txt` (load test), with a recipe to derive them from export `f6e63b4b` | experiment-engineer / storage-engineer |
| 3 | A 16B live-evaluation command and question set. Only the bucket wrapper exists | experiment-engineer, coordinator |
| 4 | The render config `templateVersion`, `runtime_reference`, and the assembly of `emr_service_policy_json` | coordinator with infra-engineer |
| 5 | `scripts/billing/README.md:129` still calls the billing login command unverified. The runbook uses the deployer-README command | infra-engineer |
| 6 | The modify gate is "28 fields" in the billing README; the verify gate is "29" in VERIFICATION.md. Confirm both counts | infra-engineer |
| 7 | The vector bucket name is not a Terraform output (it is derived from the IAM policy) | infra-engineer |
| 8 | The 14C template `idempotencyIndex` is ambiguous. The runbook uses the GSI name `by-idempotency-key` | rag-engineer |
| 9 | The expected plan addresses for the pointer and EMR runtime-applies | infra-engineer |
| 10 | Whether `archive-evidence.sh` refuses directories that contain plan files. The runbook includes plan receipts file by file | infra-engineer |

## 11. What you decide now

1. Accept this cost plan and caps, or amend them.
2. Confirm the Titan split of 0.25 / 0.05, and either accept the uncapped query-time embeddings (about USD 0.001) or set a reserve (§3.4). **Decided 2026-11-09 (review N4): accepted as is**, with no reserve and no template change.
3. **Session length with tax (review F1). Decided 2026-11-09: option 1**, hard stop at 37 h, cleanup starting by H35. Projected headroom with tax at 37 h is USD 3.11, at least 3 (§3.2). The 11% tax rate is still to be confirmed from the AWS bill. **Also decided 2026-11-09: caps = planned use** (Haiku 1.33, EMR cumulative 2.52). With them, the 37 h headroom is USD 3.30 and the H0 receipt headroom is 3.09 (§3.2).
4. After review: refresh the pins, commit, and follow the runbook from step A1.
