# Phase 14 approval request (Subphase 14A)

Prepared by the coordinator on 2026-11-07 UTC. This is a **request**, not an approval. No agent writes an approval record, a pre-spend receipt or `human-gate.md`. Nothing here authorizes any live command; each stage needs its own human-written record and a fresh receipt.

`<C>` below is the 40-hex SHA of the 14A commit that you make after the 14A reviewer's APPROVE (decision Q11). It is not `b2cd7ee`.

## 1. Pre-flight checklist (plan Section 7.1)

Status key:
- **V**: verified from retained evidence;
- **H**: you verify or supply it;
- **L**: checked by the scripts at run time;
- **M**: missing.

| # | Item | Status | Evidence / what you do |
|---|---|---|---|
| 1 | AWS account created and active, Paid plan, region us-east-2 | V (account and region) / H (plan status, quotas) | 12C cost memo: "Coordinator separately confirmed PAID/ACTIVE account status". Region `us-east-2` is the 12C and 12D region. Quotas and regional service access are not checked from evidence; confirm in the console: Neptune Serverless, Fargate vCPU, EIP, NAT, ALB and S3 Vectors in us-east-2. |
| 2 | Plan and plan-receipt checksums equal `APPROVED_PLAN_SHA256` / `APPROVED_RECEIPT_SHA256`; the receipt shows a clean tree at `<C>` | L | `deploy.sh` steps `plan-checksum`, `plan-provenance`, `state-binding`, `plan-inspect`; the dry-run evidence shows the checks run in order. |
| 3 | Account and region are the intended ones | H + L | You compute `APPROVED_ACCOUNT_SHA256` yourself. `deploy.sh --execute` re-hashes `sts get-caller-identity` before any mutation (`account-check`). |
| 4 | Cost bound within USD 200 | H | Section 5 below (estimate) plus your private cost-to-date before 14B. Last recorded spend: USD 0.34 (Phase 12 human gate, Bills page 2026-11-05 10:25 CST). |
| 5 | Apply identity is not root; MFA and short-lived role session; least privilege separate from the read-only planner | V (design) / H (session) | Profile `scholarchain-deployer-tf` assumes the deployer role with MFA (Phase 12D). The `phase14-main` set is in Section 2. You run every `--execute` yourself; agents never hold MFA credentials. |
| 6 | No unexplained destroy or replacement | L + H | First base plan: `--expect-new-state`, so every action should be `create`. `plan.sh` prints every `PLAN-ACTION`; read them before writing record A. Runtime plan: creates in `module.runtime`, and no delete or replace outside it. `runtime-preservation` refuses deletes of protected runtime types. |
| 7 | The approved command is the documented `deploy.sh` path | V | Section 3 is copied from `scripts/README.md` "First deployment". |
| 8 | Clean tree, HEAD = `<C>`, images tagged `<C>` | L | `clean-tree`, `commit-match`; `package.sh` tags `<C>`, or `<C>-dirty`, which deploy refuses. |
| 9 | Secrets exist by name; model access confirmed; budget with 50/80/100% alerts active before any paid step; Cost Explorer status; billing-bootstrap budget reconciled | H | Decisions 14-3 and 14-4. `course.tfvars` keeps `enable_budget_resource = false`, so the main root creates **no** budget: the Phase 12D billing-bootstrap budget is the only one, with no dual management. `budget_execution.py` refuses if the main budget is enabled (`MAIN_BUDGET_ENABLED`). |
| 10 | Deployer `phase14-main` reviewed, then applied by you | H | Section 2. It must be applied before the base plan; the old `spike-emr` set cannot create the main stack. |
| 11 | G5 runtime archive present with the pinned size and sha256 | V | `target/phase12d-runtime-repair-20261103/artifacts/scholarchain-spark3.5.4-scala2.13.14-java17-runtime.tgz`: 321876735 bytes, sha256 `789a9684…916de5`, equal to `RUNTIME_ARCHIVE_EXPECTED_*` in `scripts/config/release.conf` (re-hashed 2026-11-07). |
| 12 | Images built for `<C>` | M (expected) | No release manifest exists for `b2cd7ee` or `<C>` yet (only `target/release/8bee663…`). Run `package.sh` at `<C>` (Section 3, step 2). |
| 13 | Phase 11 whole-repository review | V | `docs/agent-runs/phase-11/human-gate.md`: APPROVE for 11A and 11B, and 11C APPROVE after its repair round. |
| 14 | Private tfvars complete | H | `infra/terraform/environments/course.local.tfvars.example` lists every variable; you fill the ignored `*.local.tfvars`. Agents never read it. |
| 15 | `extra_artifacts` step programs | H | Four entries and their sha256 values are in the example (from `python3 -I scripts/lib/pipeline.py step-manifest`). |
| 16 | Live state | H | `infra/terraform/terraform.tfstate` (local, git-ignored). It is absent now, so the first base plan needs `--expect-new-state`. Back it up to Drive after every apply and record its sha256. |
| 17 | Live service composition (review 1, F1) | V (offline, repair round 1) / H (acknowledgment) | The services could not become ready: they ran `unconfigured`, `/readyz` returned 503 to the `/readyz` ALB check, and the ECS circuit breaker would roll back. Repaired before the 14A commit, by your decision of 2026-11-07:<br>- `modules/services`: `SCHOLARCHAIN_SERVICE_MODE=aws`, built from the storage and rag adapters, with bounded readiness (service-engineer);<br>- `modules/storage`: `NeptuneGraphReader.connect` and directed edges (storage-engineer);<br>- `modules/runtime` and `modules/identity`: the per-role task environment, the profile ID as the synthesis model, the embedding-worker QuerySession grant and a scoped rag `s3:ListBucket` (infra-engineer).<br>Tests are offline only; see `test-report.md` and `owner-report.md`. The task mode is `aws` only when `runtime_enabled` and `runtime_composition_verified` are both true. Set `runtime_composition_verified = true` only after the 14A recheck APPROVE and your commit, never earlier. Nothing is live-verified: IAM, Neptune row shapes, Bedrock access, and the S3 HEAD-of-absent-key behavior under the `Null s3:prefix` statement. |
| 18 | aws-mode values in the private tfvars (F1) | H | Before the runtime plan, set these in `course.local.tfvars`, and use the same values in the 14C ingest config:<br>- `embedding_model_version`: no default; the ingest stamps `model.version` from its `--config`, and the 8b template still says `REPLACE_WITH_PINNED_MODEL_VERSION`; the root refuses aws mode without it;<br>- `embedding_text_prefix`: default `embedding-text`, which must equal the ingest `textPrefix`; the 8b template shows `graph/rag`;<br>- `semantic_index_name`: default `researcher-profile-v1`.<br>A mismatch makes the services refuse the vectors or find nothing. |

## 2. Deployer `phase14-main` (apply in your terminal, before any 14B stage)

**What it is.** Seven managed policy documents, `scholarchain-deployer-phase14-main--<part>`. Sizes in characters (limit 6,144):
- network 3,824
- network-mod 1,702 (was 2,540 before repair round 1, F2)
- data 5,164
- keys-obs 3,327 (was 4,999; KMS key administration moved into the key policies, F2)
- compute 5,696
- emr-efs 5,113
- iam 5,637

That makes 7 managed attachments (quota 10), plus the inline same-device login policy. Two boundary policies are created by the deployer root and are not attached to the deployer:
- `scholarchain-course-permissions-boundary` (3,372 characters), carried by every main role except the EMR service role;
- `scholarchain-course-emr-service-boundary` (4,607 characters), carried by the EMR service role only.

`spike-emr` is disabled and cannot be combined with `phase14-main`. The trust (MFA, one principal) and `max_session_duration = 3600` are unchanged. Every action, per document, is listed in `evidence/14a/r1/phase14-main-actions.txt` (current; the round-0 list is `evidence/14a/phase14-main-actions.txt`). The broad statements are in the deployer README's honest list.

**Repair round 1 (F2), which supersedes D4 and D6 for these statements:**
- The main-stack KMS key policy grants the deployer role (`arn:aws:iam::<account>:role/scholarchain-deployer`) key administration, use through services, and grants for AWS resources only. IAM keeps only `kms:CreateKey`, a `kms:TagResource` on `key/*` limited by request tags and tag keys, the alias actions and `kms:ListAliases`.
- The VPC default security group is no longer adopted (as in the Phase 12D spike), so both adoption statements are gone. The default group keeps AWS's default rules, and nothing is a member of it.
- Because the key policy names the deployer role, the deployer root must be applied before the base plan; that is already the order in Section 3.

**Disclosure (14-6).** A missed action shows up as AccessDenied during `base-apply`. It is fixed by a routed infra-engineer repair, a new reviewed deployer apply and a new plan.

**Order (D1).** 14A commit → back up the deployer state → apply the deployer root with **your admin profile** → `plan.sh` for the base plan. The boundaries must exist before the main root's first apply, or role creation fails with NoSuchEntity.

**Exact commands, expected plan and STOP rules:** `evidence/14a/deployer-apply-proposal.md`. In short:
- state `-state="$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate"` (quoted), with a timestamped `cp` backup and its `shasum -a 256` before the plan;
- `terraform plan -out`, then `show`, then the `jq` action list;
- on `LimitExceeded` during apply (11 > 10 attachments while detachments race), stop, re-plan, expect only the remaining attachment creates, and re-apply; any other change is a STOP (review 1 F5);
- expected `Plan: 16 to add, 0 to change, 9 to destroy.` (or 1 to change, for a `tags_all` or `description` drift on the role):
  - create: 2 boundaries, 7 `permission_set["phase14-main--*"]` policies and their 7 attachments;
  - destroy: the 4 `spike-emr--*` policies, their 4 attachments and `aws_iam_policy.spike_boundary[0]`;
- **any replacement of `aws_iam_role.deployer`, any other address, or a change to `aws_iam_role_policy.login` = STOP.**
- `terraform import` is a fallback only, if the state file is missing.

The plan writes `deployer.local.tfvars`, the `.tfplan` and `.terraform/` inside `infra/terraform/deployer/`. Git ignores all three (checked), so the tree stays clean for `plan.sh`. `.terraform.lock.hcl` is tracked, and `init -lockfile=readonly` leaves it unchanged.

## 3. Human-run command sequence

Run everything from `/Users/danny/Documents/UIC/CS441/ScholarChain` in your own terminal, under the MFA session for profile `scholarchain-deployer-tf`. `R=us-east-2`, `P=scholarchain-deployer-tf`. `deploy-engineer` prepares and verifies each command in 14B, and you run every `--execute`.

0. **After the 14A APPROVE:** the coordinator appends the verdict, you edit `reviewed-pins.json`, the full seven-gate `scripts/check.sh` is re-run on that final tree, and then you commit (HEAD = `<C>`) (Section 7).
1. **Deployer root:** plan, review, apply (Section 2).
2. **Images (no cost):** `scripts/package.sh` at `<C>`. It writes `target/release/<C>/release-manifest.json`. Running it before the base plan shortens the paid idle time; the README also allows it after `base-apply`.
3. **Base plan (`base-apply` must not run before Nov 11; Nov 15 is the target):**
   `scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --expect-new-state --execute`
   Use the private tfvars with the runtime **disabled**. Read `PLAN-TEXT`, check every `PLAN-ACTION`, and note the plan path, plan sha256 and receipt sha256 that it prints.
   **The commit freeze starts here:** nothing may be committed or written into the repository until `runtime-apply` succeeds.
4. **Receipt A and record A:** write `target/phase14/prespend-receipt.json` (Section 4), compute its sha256, and write record A into `docs/agent-runs/phase-14/human-gate.md`.
5. `scripts/deploy.sh --stage base-apply --plan <base plan> --region us-east-2 --profile scholarchain-deployer-tf --execute`
   This applies the base plan, creates the ECR repositories and uploads the G5 archive. Then back up `infra/terraform/terraform.tfstate` and record its sha256. On the first apply that creates EMR-related ENIs, record the item 17 stack tags on them.
6. **Archive:** copy `human-gate.md` to `target/phase14/approvals/base-apply.md`.
7. **Receipt B and record B (push):** write a fresh receipt, then:
   `scripts/deploy.sh --stage push --region us-east-2 --profile scholarchain-deployer-tf --execute`
   This pushes the four `linux/amd64` images tagged `<C>`, verifies their digests and writes `target/release/<C>/push-record.json`. Archive to `target/phase14/approvals/push.md`.
8. **Runtime plan.** Do this only when all of these hold:
   - `<C>` contains the reviewed live composition (row 17) and the 14A recheck is APPROVE;
   - the row 18 values are set in the private tfvars.

   Then set `runtime_enabled = true` and `runtime_composition_verified = true` there, along with the other runtime variables in the example.

   **Never set `runtime_composition_verified = true` before that.** Without that acknowledgment the root refuses the runtime plan. In `unconfigured` mode the services would also stay unready: `/readyz` 503, unhealthy ALB targets, and an ECS circuit-breaker rollback while the stack keeps billing. If any condition is unmet, stop after step 7 and tell the coordinator. Then:
   `scripts/plan.sh --env course --region us-east-2 --profile scholarchain-deployer-tf --image-revision <C> --execute`
9. **Receipt C and record C (runtime-apply):**
   `scripts/deploy.sh --stage runtime-apply --plan <runtime plan> --region us-east-2 --profile scholarchain-deployer-tf --execute`
   This verifies the push record and registry digests, applies, and verifies the four ECS services and task definitions. Back up the state and record its sha256. Archive to `target/phase14/approvals/runtime-apply.md`.
10. **Smoke:** `scripts/smoke-test.sh --url <query endpoint> --api-key-env <NAME>`. `/readyz` passes only when the tasks run the live mode from the F1 repair and their dependencies (Neptune, DynamoDB, S3 / S3 Vectors, SQS, Bedrock) are reachable and authorized. In `unconfigured` mode it returns 503 and the smoke fails at `smoke-readyz`. Before the 14C data load, readiness does not require loaded data. The evidence-backed query is a 14C criterion.
11. **The commit freeze ends.** The coordinator copies lean evidence and the three archived records to `docs/agent-runs/phase-14/evidence/14b/`, and you commit.

## 4. Templates

### Approval record (`docs/agent-runs/phase-14/human-gate.md`, one stage at a time)

`KEY=value`, each line exactly once, lowercase hex, no quotes, no CR line endings. Prose lines are ignored; an unknown `APPROVED_*` key refuses.

```text
APPROVED_STAGE=base-apply
APPROVED_COMMIT=<C>
APPROVED_ACCOUNT_SHA256=<account sha256>
APPROVED_REGION=us-east-2
APPROVED_ENVIRONMENT=course
APPROVED_PRESPEND_SHA256=<prespend sha256>
APPROVED_PLAN_SHA256=<plan sha256>
APPROVED_RECEIPT_SHA256=<receipt sha256>
```

Every value line above is copy-safe once its `<...>` is replaced. `deploy.sh` reads everything after `=` as the value, so never add a trailing comment. How to fill each placeholder:
- `APPROVED_STAGE`: `base-apply` for record A, `push` for record B, `runtime-apply` for record C.
- `<account sha256>`: `printf '%s' "$id" | shasum -a 256`, keeping only the hex, where `$id` is the 12-digit account ID.
- `<prespend sha256>`: `shasum -a 256 target/phase14/prespend-receipt.json`, keeping only the hex.
- `<plan sha256>` and `<receipt sha256>`: the values `plan.sh` printed, for `base-apply` and `runtime-apply` only. **Delete both lines for `push`.**

Required prose in the same file (decision 14-2; no personal email address):
- the original project ceiling: USD 200;
- reported cost-to-date, its billing data period and its retrieval time (UTC);
- estimated unreported costs;
- reserved baseline and retention costs;
- the conservative estimated remaining shared budget;
- the approved deployment and live-test suballocation;
- the exact start, end and cleanup limits;
- the explicitly authorized command(s) for this stage.

### Pre-spend receipt (`target/phase14/prespend-receipt.json`, fresh per stage)

```json
{
  "schema": "scholarchain.prespend-receipt.v1",
  "monitoring_confirmed_active": true,
  "cost_snapshot_utc": "YYYY-MM-DDTHH:MM:SSZ",
  "reported_spend_usd": 0.00,
  "unreported_usage_allowance_usd": 0.00,
  "reserves_usd": 0.00,
  "remaining_headroom_usd": 0.00
}
```

All four `*_usd` fields are JSON numbers. The snapshot must be no older than 24 h at **every** paid operation: ECR login, each push, each apply and the archive upload. Remaining headroom must be at least USD 20. `reserves_usd` must cover the Nov 15–24 run (decision 14-1); see Section 5.

## 5. Cost estimate, Nov 15 00:00 CST → Nov 24 23:00 CST (239 h), before credits

The rates are the Phase 12C Ohio retail rates (`docs/agent-runs/phase-12/evidence/12c/cost/cost-memo.md`, `cost-calculations.json`, fetched 2026-10-30), applied to the shape as authored now. This is a model, not observed spend. The full stack is assumed to run at minimum capacity for the whole window: Neptune Serverless at 1 NCU; four Fargate tasks at 0.5 vCPU / 1 GiB; one ALB with 1 LCU and 2 public IPv4; one NAT gateway with its EIP; no interface endpoints (default `[]`).

| Component | Per hour | Per day (24 h) | 239 h |
|---|---:|---:|---:|
| Neptune Serverless, 1 NCU | 0.1608 | 3.86 | 38.43 |
| Fargate, 4 tasks | 0.0987 | 2.37 | 23.60 |
| ALB + 1 LCU + 2 IPv4 | 0.0405 | 0.97 | 9.68 |
| NAT gateway + EIP | 0.0500 | 1.20 | 11.95 |
| 80 custom/Container Insights metric-equivalents (prorated) | 0.0333 | 0.80 | 7.97 |
| **Run rate** | **0.3834** | **9.20** | **91.63** |

Daily: Nov 15–23, USD 9.20 each; Nov 24 (23 h), USD 8.82.

| Item | USD |
|---|---:|
| Run rate, 239 h | 91.63 |
| Full-month allowances (KMS key, dashboard, alarms, hosted zone 5.00; Cloud Map 0.30; 4 secrets 1.60) | 6.90 |
| Illustrative store/API usage (NAT data, S3, ECR, DynamoDB, logs, KMS, vectors, SQS, Step Functions, Neptune storage/I/O, Titan 10 M tokens) | 4.37 |
| One extra month of retained S3, vectors, key and ECR after cleanup | 1.64 |
| **Subtotal, modeled** | **104.54** |
| Reserve: EMR, Phase 15 (G6: USD 3 per run × 3, cap 9.50) | 9.50 |
| Reserve: PendingDeletion KMS keys (Phase 13 G6 hold) | 5.00 |
| Reserve: synthesis model Claude Haiku 4.5 (selected; profile `us.anthropic.claude-haiku-4-5-20251001-v1:0`), 9C and evaluation. A cap, not a priced estimate: the per-token rate was not fetched in 14A. Its model card says it is billed through AWS Marketplace and shows under the provider in Cost Explorer, not under Amazon Bedrock. Confirm the rate on the Bedrock pricing page before 9C, and stop synthesis runs before this reserve is used up. | 20.00 |
| Reserve: unreported usage, tax, other | 20.00 |
| **Total with reserves** | **159.04** |
| Headroom against USD 200, before subtracting the reported cost-to-date (0.34 last recorded) | 40.96 |

Sensitivities:
- each interface endpoint service in 2 AZs adds USD 0.48/day (4.78 per window) plus data;
- sustained authored maxima (2.5 NCU, 10 tasks) run at USD 0.7726/h ≈ 18.54/day. That is 0.402 Neptune + 0.2468 Fargate + 0.0405 ALB + 0.0500 NAT + 0.0333 metrics; review 1 F4 corrected the earlier 0.739, which left out metrics. Over the window that exceeds USD 200, so caps and short bursts matter;
- an upper-duration start on Nov 11 adds 96 h ≈ USD 36.80 of run rate.

Billing data lags by a day or more, so enforce the caps instead of waiting for alerts.

## 6. Commit freeze and archiving (decision 14-9 and Q11)

- From the base plan (step 3) until `runtime-apply` succeeds, **nothing is committed and nothing new is written into the repository**: not `prompt.md`, `review.md`, `owner-report.md` or `test-report.md`. The only exception is your `human-gate.md`. Coordinator evidence goes to `target/phase14/evidence/` (git-ignored).
- After each stage, you copy `human-gate.md` to `target/phase14/approvals/<stage>.md` before writing the next record.
- After `runtime-apply`, the coordinator copies lean evidence and the three archived records into `docs/agent-runs/phase-14/evidence/14b/`, and you commit.
- The closeout `human-gate.md` is written last and replaces the final approval record.

## 7. Before your 14A commit

- The full seven-gate `scripts/check.sh` has already passed on the reviewed tree before review: after repair round 1, snapshot `c4dbd00ea8dbf2eaf1c5300836cb8dd8e5713751`, `RESULT: PASS gates=7` (`evidence/14a/gates/check-full-r1.txt`; `test-report.md`, "Repair round 1", R2). A re-run is required once more after the APPROVE if anything outside `docs/agent-runs/phase-14/` changes, which includes your `reviewed-pins.json` edit. Run it on the final tree before the commit.
- `scripts/billing/reviewed-pins.json` (Q12):
  - 23 of the 209 `source_freeze` rows have drifted after repair round 1 (20 before; the 3 new ones are `modules/runtime/{compute,outputs,variables}.tf`). Their pinned and current size and sha256 are in `evidence/14a/pin-drift.txt`; you update those 23 rows once.
  - New files (for example `tests/infra/test_phase14_main.py`) are not in `source_freeze`, so they need no row.
  - Changing `reviewed-pins.json` changes a `scripts/billing` file whose hash is bound in the billing execution gate (`wrapper_files`). Any later billing `verify` or `readback` therefore needs a new billing gate. The applied budget itself is unaffected.
- Model values for your private tfvars (14-3):
  - `synthesis_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"`
  - `synthesis_inference_profile_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`
  - `synthesis_inference_profile_regions = ["us-east-1","us-east-2","us-west-2"]`
  - `embedding_model_id = "amazon.titan-embed-text-v2:0"`, with no profile.

  Optional read-only check: `aws bedrock get-inference-profile --region us-east-2 --inference-profile-identifier us.anthropic.claude-haiku-4-5-20251001-v1:0 --query 'models[].modelArn'`.
