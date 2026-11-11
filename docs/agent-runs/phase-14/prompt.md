# Phase 14 work order

Plan: `<Google Drive>/My Drive/plan/phase14.md` (the "Phase 13 handoff" section added 2026-11-06 is binding).
Tool: Claude Code orchestrator (main session). Subagents are launched with model `sonnet` (Sonnet 5.5) at effort `high`, as the user asked.

## Subphase 14A — pre-flight, dry run and the approval request

Scope: Subphase 14A only. No AWS call, no real plan, no apply, no upload, no push, no reviewer launch, no commit or push. No agent writes an approval record.

### Preflight (observed 2026-11-07T03:18Z UTC / 2026-11-06 America/Chicago)

- Branch `phase-14`; base SHA `b2cd7ee99dcc136b5c8ec0667ca181cc5b3a87fd` (the Phase 13 merge, PR #9); `git status --short` empty.
- `java -version` (JDK 17 env): `openjdk version "17.0.20.1" 2026-08-18`.
- Terraform v1.13.5; shellcheck 0.11.0; Python 3.14.5; aws-cli 2.35.4; Docker server `linux/arm64` 29.5.3; jq 1.7.1.

### Step 0 answers (user, 2026-11-06, in substance)

The user accepted every recommended default, with these changes.

- **14-1 Window and budget.** Phase 14 ends on Nov 17, but the stack stays up for Phases 15 and 16 until cleanup on Nov 24. The approval request's cost estimate must cover Nov 15–24, per day and in total, and the pre-spend reserves must assume that. The user will send cost-to-date, its retrieval time and the alert and Cost Explorer status privately before 14B. Environment `course`, region `us-east-2`, shared ceiling USD 200. No email address in any file.
- **14-2 Approval records.** Default accepted. The user writes `docs/agent-runs/phase-14/human-gate.md` once per stage. The coordinator provides per-stage templates and the pre-spend receipt template.
- **14-3 Bedrock.** The user will confirm in the console that Titan Text Embeddings V2 and their synthesis model are enabled in us-east-2, and will give the model ID. `infra-engineer` must check whether that model needs a cross-region inference profile (for example `us.anthropic.*`). If it does, `modules/identity/phase12b.tf:3` (foundation-model ARN only) must also grant `bedrock:InvokeModel` on the inference-profile ARN and on the foundation-model ARN in each region the profile routes to. This needs tests, and it is done in 14A so the 14A commit is the approved commit.
- **14-4 Secrets.** Default accepted. The human creates the secrets in Secrets Manager outside Terraform, on purpose, so the values never enter state. Terraform receives only the ARNs. The owner report discloses this.
- **14-5 Rollback.** Policy 13-5 is kept.
- **14-6 Deployer permissions.** A scoped `phase14-main` set: service-scoped, region-locked to us-east-2, IAM limited to `scholarchain-*` roles with a permissions boundary, MFA, a 1-hour session, each document under 6,144 characters. `spike-emr` is removed from `enabled_permission_sets`. For each resource type the set includes the read, list, describe and tag actions that Terraform needs for refresh, not only create and delete. Every action per document is listed in the evidence for review. The owner report discloses that a missed action shows up as AccessDenied during `base-apply`, and that it is fixed by a routed repair and a new plan.
- **14-7 State.** Local `infra/terraform/terraform.tfstate`, never committed. The user backs it up to Drive after every apply, and its sha256 is recorded in evidence.
- **14-8 A2.** Accepted as written in `docs/agent-runs/phase-13/repairs.md`.
- **14-9 Approval-record handling.** Commit freeze and per-stage archiving to `target/phase14/approvals/<stage>.md` accepted. The format additions (`APPROVED_RECEIPT_SHA256`, `APPROVED_ENVIRONMENT`, the `cleanup-prepare` stage, `cleanup --confirm --plan`) are accepted as implemented.
- **14-10 Dates.** `base-apply` on Nov 15, never before Nov 11. Phase 14 ends on Nov 17; cleanup is on Nov 24. The user gives the exact clock times in the record.
- **Q11 Approved commit, in this order.** After the 14A reviewer's APPROVE, the coordinator appends the verdict to `review.md` and the user commits. That commit becomes `APPROVED_COMMIT`. Only then does the user run `plan.sh --execute`. From the base plan until `runtime-apply` succeeds, nothing is written into the repository, including `prompt.md`, `review.md`, `owner-report.md` and `test-report.md`. `target/phase14/evidence/` is used instead.
- **Q12 Stale pins.** The coordinator reports the current size and sha256 of the stale pinned files. The user edits `scripts/billing/reviewed-pins.json`.
- **Q13 EMR service policy.** `infra-engineer` documents how the main stack attaches and scopes the EMR service policy. The user decides in the 14A acceptance.
- **Q14 Dry runs.** The coordinator runs the `plan.sh` and three `deploy.sh` dry runs; they make no AWS or Docker calls. `deploy-engineer` is not used before 14B. The four step-program entries go to `infra-engineer`, as an example file plus documentation. The coordinator never reads the private tfvars.

### Mid-subphase decisions (user, 2026-11-06, after the infra-engineer's first report)

- **D1 Permissions boundary:** approved. `infra-engineer` wires the boundary into all seven `aws_iam_role` blocks in `modules/identity` and `modules/workflow`, with tests. The boundary ARN is built from the account ID and the fixed boundary name, or passed in `course.local.tfvars`; never from remote state. A test checks that every action in each role's policies is allowed by that role's boundary, so a mismatch fails the test instead of the runtime.
  - Order: 14A commit → the human backs up the deployer state → the human applies the deployer root with their admin profile → `plan.sh` for base-apply.
  - `infra-engineer` writes `target/phase14/evidence/14a-infra/deployer-apply-proposal.md` with the exact argv, the state-backup step and the expected plan: create 2 boundaries, 7 policies and 7 attachments; destroy the 4 spike policies, 4 spike attachments and `spike_boundary[0]`; update `aws_iam_role.deployer` in place only, if at all. Any replacement of `aws_iam_role.deployer` is a stop.
- **D2 EMR tag:** approved. Fix now in `modules/network`, with tests: tag the application subnets and the EMR node security group with `for-use-with-amazon-emr-managed-policies=true`, so Phase 15 needs no network change.
- **D3 Independent tests:** approved. `test-engineer` (Sonnet 5.5, high) pins the old deployer tests to `spike-emr`, adds `phase14-main` checks, and adds each honest-list guard allowlist entry with its justification. After the final diff, the coordinator re-runs every suite itself (deployer, root, `tests/infra` and `sbt check`) and records the exact commands, counts and exit codes in `test-report.md`. Agent-reported numbers are not relied on. The coordinator then lists every file whose pin changed; the user refreshes `reviewed-pins.json` once.
- **D4 Broad statements:** accepted as disclosed in the deployer README; the reviewer judges. Also record whether the `ec2:Vpc` condition key could narrow `RevokeSecurityGroupIngress/Egress`. Note only, no change.
- **D5 Deployer state:** at `$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate`, never read by an agent. The README sequence passes `-state="<that path>"` explicitly, keeps the import step only as a fallback, and says "back up this file before apply".
- **Q13 EMR service policy:** `environments/emr-service-policy.json.example` (v2 scoped to us-east-2 and this account) accepted. Keep the test that the EMR boundary covers every action in it. It is used from Phase 15; Phase 14 plans keep EMR disabled.
- **Item 17:** the live ENI tag check moves to the Phase 15 apply; recorded in carried findings.
- **Synthesis model:** Claude Haiku 4.5 on Bedrock, with model access enabled in us-east-1, us-east-2 and us-west-2. Documented example values only (the user fills the real private file): `synthesis_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_regions = ["us-east-1","us-east-2","us-west-2"]`. Temperature 0.0 and the forced tool choice stay unchanged; Haiku 4.5 accepts both.
- **Carried finding (new):** `BedrockConverseLlmClient` always sends `temperature` and a forced `SpecificToolChoice`. Claude 5.x models, and possibly GPT-6 Luna, reject these, so any later model switch needs a reviewed client change.

### Gate repair decision (user, 2026-11-07)

- **D6 Spike CreateTags invariant:** the first full `check.sh` in the clean snapshot (commit `e690b50`) failed in `script-tests`. The failing test is `scripts/phase12d-spike/tests/test_terraform_static.py` `test_every_ec2_create_tags_has_a_create_action_condition`, on `phase14_main.tf` `Ec2AdoptedDefaultSgFirstTags`. The user chose a named exception:
  - The statement stays, consistent with D4.
  - `infra-engineer` changes that test to exempt exactly this Sid, with its exact Resource and `aws:TagKeys` condition. Every other `ec2:CreateTags` statement must still carry `ec2:CreateAction`.
  - A mutation shows the exemption cannot widen.

### Repair round 1 (user, 2026-11-07, after review 1 REQUEST-CHANGES)

The user said: "fix all blocking bugs for me". The coordinator recorded it as follows; see `repairs.md`.

- **F1 Live service composition: option (1).** Before the 14A commit:
  - `service-engineer` adds a live AWS composition mode to `modules/services`, built from the existing `modules/storage` and `modules/rag` adapters. Readiness must reflect the real dependencies.
  - `infra-engineer` then wires the task environment in `modules/runtime`, including the synthesis inference-profile ID passed as the model ID.
  - `runtime_composition_verified` stays a human acknowledgment, set only after this code is reviewed and tested.
  - Owners outside services (storage-engineer, rag-engineer) only by a routed `BLOCKED-ON`.
- **F2 Tag adoption: narrow.**
  - Key administration moves into the key policy, which names the deployer role.
  - Adopted security groups gain no mutation reach beyond adoption.
  - A negative test shows that a foreign tagged key or security group gains no mutation rights.
- **F3–F5:** fixed in the same edits. F6 is noted only.

### Verification scope (from the user's standing guidance, 2026-11-05)

14A changes no Scala or build input. The coordinator runs the fast gates in a clean snapshot (`check.sh --skip sbt`) and reuses the last passing `sbt check` (the Phase 13 final verification, 2026-11-06), with proof that no `build.sbt`, `project/**` or `modules/**` input changed. The full seven-gate `check.sh` runs once, after the reviewer's APPROVE and before the user's commit.

### Routing

| Agent | Paths | Task |
|---|---|---|
| `infra-engineer` | `infra/terraform/deployer/**`, `infra/terraform/modules/identity/**`, `infra/terraform/tests/**`, `infra/terraform/environments/*.example`, `infra/terraform/README.md`, plus root variables and wiring if the Bedrock change needs them | the `phase14-main` set and its tests; removing `spike-emr`; the Bedrock inference-profile grant and its tests; the `extra_artifacts` example and documentation; the EMR service-policy documentation |
| coordinator | `docs/agent-runs/phase-14/**` (except human-owned files), `target/phase14/**` | prerequisite verification, dry runs, gates, approval request, reports, reviewer prompt |

## Subphase 14B — apply, deploy services and smoke test

### Preflight (observed 2026-11-07 17:41 CST)

- Branch `phase-14`; tree clean; base SHA = HEAD = `e2f0b01ce9670c11ef9c4b3706bb52569f960a1d` (14A `APPROVED_COMMIT` `ed9d241` plus the docs-only record commit).
- Start conditions:
  - deployer `phase14-main` applied: not yet (the user applies it before base-apply: Nov 8–10 for a Nov 11 base-apply, Nov 12–14 for Nov 15; corrected after 14B review 1 N3);
  - date not before Nov 11: **not met** (today is Nov 7);
  - `base-apply` record matching plan, receipt and commit: **not met** (`human-gate.md` does not exist).
- Therefore nothing live runs in this step.

### Step 0 answers (user, 2026-11-07, in substance)

- **Q1 Deployer apply.** The user applies the deployer root with the admin profile before base-apply (Nov 8–10 for a Nov 11 base-apply, Nov 12–14 for Nov 15; corrected after 14B review 1 N3), backs up `deployer.tfstate` first, and saves the output to `target/phase14/evidence/14b/deployer-apply.log`. `deploy-engineer` checks it against the expected plan (create 2 boundaries, 7 policies, 7 attachments). Any replacement of `aws_iam_role.deployer` is a stop.
- **Q2 Approved commit.** Every record names the HEAD at the base plan. That HEAD includes these Step 0 notes and the Q6 fix commit. Images are tagged with that SHA.
- **Q3 Timing.** Base plan and `base-apply` on Nov 15, back to back; then `push` and `runtime-apply` the same day if `base-apply` passes, so the base stack does not sit idle. Each stage has its own record and a fresh pre-spend receipt. The user writes the exact clock times.
  - **Amended (user, 2026-11-07, tentative): `base-apply` "may be" on Nov 11**, the earliest date the shared budget decision allows (the Nov 11–24 upper-duration costing case), to leave slack for a repair cycle before the Nov 25 deadline. The date is final only in the user's `base-apply` record.
  - Consequences: the deployer apply (Q1) moves to Nov 8–10. The open HTTPS-certificate item must be settled before Nov 11. Idle cost rises by about USD 9.20 for each day before Nov 15, about USD 37 for Nov 11; the Nov 11–24 idle total is about USD 128 (13 days × 9.20 + 8.82 for Nov 24), to be checked against the conservative remaining budget in the pre-spend receipt.
- **Q4 Cost-to-date.** The user writes the reported figure, its data period and retrieval time in the record prose and the pre-spend receipt. The coordinator records only the cost-to-date total and the receipt headroom (at least USD 20).
- **Q5 14B pass definition (review N2).**
  - Pass: `/healthz` and `/readyz` 200 through the ALB; the query-api target healthy; the four ECS services steady; deployed image digests match the push record; the two 401 checks (no key, wrong key) pass by hand with `curl`.
  - Expected, not a rollback trigger: `smoke-query` stopping for lack of data (a 200 or SUCCEEDED job with zero claims, or a typed no-evidence error).
  - Failure: a 5xx, AccessDenied, a timeout or an auth failure → evidence, rollback policy 13-5, stop.
  - `smoke-evidence` and `smoke-idempotency` move to 14C.
- **Q6 Readiness (review N3): option (a), fix before Nov 11.**
  - `infra-engineer` sets `health_check_grace_period_seconds = 120` only on the load-balanced query-api service; ECS rejects it on services without a load balancer, so the other three services do not get it. Tests are required.
  - Cost correction for the record: the idle run rate is about USD 9.20/day (`approval-request-14a.md` §5); USD 18.54/day is the sustained authored maximum.
  - Note only, for review: whether the ALB health check should use `/healthz` instead of `/readyz`. No change unless the reviewer asks.
  - After the fix: full check, review, then the user commits. The coordinator lists the changed pinned files; the user refreshes `reviewed-pins.json` once.
- **Q7 P14-7 early check.** Right after `/readyz` passes, one `curl` GET for an absent evidence ID, with the key; expected 404. A 403, or a 500 caused by a 403, is routed to `infra-engineer`. The key comes from an environment variable or file and never appears in the saved command, log or evidence.
- **Q8 aws-mode values (P14-8).** The user sets them in the private `course.local.tfvars` before the runtime plan:
  - `embedding_model_version = "amazon.titan-embed-text-v2:0"`;
  - `embedding_text_prefix = "embedding-text"` (the Terraform default; the 14C ingest config `textPrefix` must be `embedding-text`, not `graph/rag`);
  - `semantic_index_name = "researcher-profile-v1"`.
  14C's ingest config must use the same three values.
- **Q9 Execution.** The user runs each `--execute` in their own terminal and saves the log to `target/phase14/evidence/14b/<stage>.log`. `deploy-engineer` reads and verifies. Logs may contain the raw account ID; they stay in git-ignored `target/`, and anything copied into `docs/` replaces it with `<acct>`. After each stage the user copies the record to `target/phase14/approvals/<stage>.md`. EMR stays disabled, so item 17 does not apply in 14B.
- The user's instruction: "Do the Q6 fix now. No live commands before my records."

### Open Step 0 item found by the coordinator (2026-11-07)

- **HTTPS certificate.** `aws_lb_listener.https` (and so the query-api load-balancer attachment and its grace period) exists only when `https_certificate_arn` is set; `phase12b.tf` also requires `runtime_enabled` and non-empty `public_ingress_cidrs` with it. Without a certificate, query-api has no public endpoint, `smoke-test.sh` (https only for a non-loopback host) cannot run, and the Q5 pass definition cannot be met. The 14A approval request does not list it. Options: an ACM certificate for a domain the user controls (DNS validation), or an imported self-signed certificate (the smoke script and `curl` would then need to trust it; the script does not support that today). The user decides before the runtime plan.

### Repair round 1 (user, 2026-11-07, after 14B review 1 REQUEST-CHANGES)

The user said: "fix all blocking bugs". The coordinator recorded it as follows; see `repairs.md`.

- **B1: option (a)**, the reviewer's recommendation. `infra-engineer`:
  - raises the query-api grace default to 300 s;
  - sets the target-group `interval`, `healthy_threshold` and `unhealthy_threshold` explicitly from validated configuration, so the arithmetic no longer depends on which default (AWS API 30 s / 2 / 5 or provider 30 s / 3 / 3) applies;
  - wires a validated root variable for the grace, so it can be tuned in the private tfvars without a commit;
  - documents the arithmetic in `infra/terraform/README.md`.

  `test-engineer` then updates the independent test from this decision and repeats the mutations.
- **N1 arithmetic (coordinator).** Under the 14A cost model (`approval-request-14a.md` §5): headroom before cost-to-date 40.96; a Nov 11 start adds 96 h at the run rate, about 36.80; minus the last recorded cost-to-date 0.34: **40.96 − 36.80 − 0.34 = USD 3.82**, below the USD 20 receipt floor. `reserves_usd` would also have to cover Nov 11–24, not Nov 15–24. `verify.py` checks only the headroom number written in the receipt, not this arithmetic. **The user's choice is still open:** Nov 11 with a named reserve reduced by at least about USD 16.18 (stated in the record prose), or Nov 15 (the reviewer's recommendation). The tentative Nov 11 above stands only until that choice.
- **N2 (still open, user).** The certificate source and the `public_ingress_cidrs` source must be settled before the 14B commit and before base-apply (this supersedes "before Nov 11" and "before the runtime plan" above). A console or CLI ACM request or import is a direct cloud mutation: either `infra-engineer` authors it in Terraform (only on the user's explicit instruction) or the user records a disclosed exception. See the dated addendum in `approval-request-14a.md`.
- **N3, N4:** fixed by the coordinator. N5 carried.

### Routing (Q6 fix)

| Agent | Paths | Task |
|---|---|---|
| `infra-engineer` | `infra/terraform/modules/runtime/**`, root wiring and variables if needed, `infra/terraform/tests/**`, `infra/terraform/README.md` | the query-api grace period, configurable, with Terraform tests; the stale N4 comment at `compute.tf:105` since the file is touched |
| `test-engineer` | `tests/infra/**` | an independent static test of the grace-period requirement |
| coordinator | `docs/agent-runs/phase-14/**` (except human-owned files), `target/phase14/**` | gates, reports, reviewer prompt |

## Subphase 14B — replan under the USD 25 course cap (user, 2026-11-08)

### New constraint (from the professor, relayed by the user)

- Total AWS spend for the whole project, cumulative and including the USD 0.34 already spent, must stay **under USD 25**.
- AWS Budgets alerts at USD 10, 15 and 20. Alerts do not stop charges, so the project enforces its own caps.
- The approved 14A cost plan (104.54 modeled, 159.04 with reserves, stack up Nov 15–24) no longer fits. **The 14A approval is superseded for cost.** Nothing live runs; the base plan is not run.
- Credits: USD 140 active (Free Tier 100 + 2 × 20), expiring 2027-10-30; the spend so far is covered. The USD 25 course cap still applies to usage. The user confirms before the session whether the credits cover AWS Marketplace (Haiku 4.5).

### Step 0 answers, adjusted (user, 2026-11-08)

- **Q1** Deployer apply accepted (IAM is free): admin profile, `deployer.tfstate` backed up first, log `target/phase14/evidence/14b/deployer-apply.log`.
- **Q2** Records name the HEAD at the base plan, after the replan is committed.
- **Q3 replaced.** No 10-day window: **one live session of about 36–48 h** running 14B, 14C and the Phase 15 runs back to back, then full cleanup. The user picks the date after the new approval request is accepted. (This supersedes the Nov 11 / Nov 15 question, review 1 N1.)
- **Q4, Q5, Q7, Q8, Q9** as recorded above.
- **Q6** keep 300 s with the root variable (the B1 fix).
- **Replan answers:**
  1. Keep the 300 s grace.
  2. **HTTPS certificate: option (a).** An ACM DNS-validated certificate for one subdomain (for example `api.<domain>`) of a domain the user owns, with DNS at Cloudflare. The domain name is a private tfvars value only, never committed. The user adds both records in Cloudflare by hand (no Cloudflare provider or token in Terraform), both "DNS only" (not proxied), so TLS ends at the ALB. The runbook states when each record is added: the validation CNAME before runtime-apply; the api CNAME to the ALB DNS name after the ALB exists. Before the session the user checks for CAA records and, if any exist, adds one allowing `amazon.com`.
  3. Fargate 0.25 vCPU / 1 GiB, one task per service, raised in tfvars only if a service fails to start. The Phase 15 autoscaling maximum stays small and is costed.
  4. NAT: decided after the survey.
  5. Model 36 h and 48 h; every cap set for 48 h.
  6. **Caps: Haiku 4.5 USD 1.50, Titan USD 0.30**, token limits derived from the fetched rates. If the total does not fit, shrink the corpus (at least 10k vectors, or an approved smaller set) or lower the Phase 15 request caps. **Never drop Phase 15**: the professor requires the scaling experiments at different dataset sizes.
  7. Pins: script and Terraform values by `infra-engineer` with tests by `test-engineer`; `reviewed-pins.json` rows refreshed by the user; the cost plan and new approval request by the coordinator.
  8. One review prompt covers B1 and the replan.
- **Requested deliverables (user):** a per-hour cost table for 36–48 h plus fixed charges, total at or under USD 25 including 0.34; shape reductions with savings (dashboard and Container Insights removed, smallest Fargate, Neptune at minimum, NAT avoidance analysis); new pins (pre-spend ceiling 25, minimum headroom about 3, EMR cumulative cap about 3 for three small runs); billing-bootstrap change (budget USD 25 with three ACTUAL alerts at ABSOLUTE_VALUE 10, 15, 20; diff and plan only, applied by the user with the billing-deployer profile); the Haiku 4.5 per-token rate from the Bedrock pricing page and a small token cap; exact cleanup steps right after the session. Route, test, review, then stop at the new approval request.
- **Reporting (user):** every reply starts with a "Where we are" box; manual actions as numbered steps (where, exact command or values, expected result, log file, what to report); decisions explained in plain words; terms explained the first time.

### Billing facts (user, 2026-11-08, confirmed with the AWS billing assistant)

- The account is on the Paid Plan. The USD 140 credits cover Amazon Bedrock native models (Titan Text Embeddings V2: covered).
- **Claude Haiku 4.5 is an AWS Marketplace charge: NOT covered by the credits; it goes to the card.** Keep Haiku 4.5 with the USD 1.50 cap; it still counts toward the USD 25 course cap.
- The Marketplace subscription is created on the first invocation. It has no fixed fee and needs `aws-marketplace:Subscribe` / `ViewSubscriptions` plus a payment method. **No Marketplace permission is added to any application role.** The user makes the first invocation from the Bedrock playground in us-east-2 before the session, so the account-level subscription already exists. The runbook lists this as a human pre-session step, with a check that it is done.
- The cost plan shows the Haiku charges as a separate **out-of-pocket** line, apart from the credit-covered lines.

### Replan decisions (user, 2026-11-08, after the infra-engineer survey)

1. **Session length:** plan 36 h, **hard stop at 42 h**; every cap is sized for 42 h.
2. **NAT:** keep one NAT gateway (no change).
3. **Budget:** `infra-engineer` adds a reviewed "modify" path to the billing tooling; the user applies it with the billing-deployer profile **as the first live step, before the session**. Until then nothing runs.
4. **ACM certificate:** Terraform creates it in base-apply and outputs the DNS validation record. The ACM permissions are added to the deployer now, so the deployer is applied only once. **base-apply must not wait on validation** (no blocking `aws_acm_certificate_validation` in base-apply); validation is awaited only where the HTTPS listener needs it (runtime-apply). The runbook says exactly when to add the Cloudflare CNAME (DNS only) and how to check it is validated before runtime-apply.
5. **Cleanup:** archive the evidence and download what the report needs, then delete everything. The runbook adds a step to record a short demo video during the session, before cleanup.
6. **Fargate:** 0.25 vCPU / 1 GiB for all four services; raised in the private tfvars only if one fails to start.
- **Phase 15 load test and Haiku:** the cap allows about 170 synthesized answers. The concurrency levels (1/5/25/50) mostly hit endpoints that do not call the LLM, with a small fixed sample of synthesized answers inside the USD 1.50 cap; the plan states the answer budget per level.
- Confirm the Haiku rate on the Bedrock pricing page before the approval request.
- **Bulk-load risk:** bring the cheapest fix that runs the Neptune load from inside the VPC (for example a one-off ECS task or an EMR step), with its cost.

### Bedrock quotas (user, 2026-11-08)

- Bedrock quotas in us-east-2 were 0. On 2026-11-08 the user requested, through Service Quotas, Haiku 4.5 cross-region TPM 5,000,000 and RPM 10,000 (the form's minimum). Titan V2 on-demand quotas are 0 and "Not adjustable", so they were added to an AWS Support case on 2026-11-08. The first Haiku playground call failed with "ThrottlingException: Too many tokens per day". All pending.
- **Hard session precondition (runbook):** Haiku 4.5 and Titan V2 quotas are non-zero, and one playground call to each in us-east-2 succeeds. Phase 15 caps are sized to the approved quotas; spend stays limited by the project's own caps.
- A fallback note (no changes) on switching synthesis to an Amazon Nova model is requested; routed read-only to `rag-engineer`.
- Haiku 4.5 rate: the Bedrock pricing page renders its figures client-side and could not be read by the coordinator's fetch; the model card confirms Marketplace billing. The public price list (AmazonBedrockFoundationModels, us-east-2, 2026-10-12) shows USD 1.10 input / 5.50 output per 1M tokens for the geo (`us.`) profile and 1.00 / 5.00 for global. The user confirms the figure on the pricing page in a browser before approving.

### 14C run-path survey (storage-engineer, read-only, 2026-11-08): 14C is blocked as planned

- **B-A** No network path from the laptop to the private Neptune cluster (bulk loader and the Phase 7 `awsIntegration` suite both call it directly).
- **B-B** No principal holds the 14C data-plane permissions (S3 writes outside artifacts, DynamoDB items, S3 Vectors data, Bedrock InvokeModel, Neptune loader/reader/cleanup); the deployer session is 1 h with MFA.
- **B-C** The real Phase 6 slice export has no Neptune openCypher CSV sidecar, so `StorageLoadMain` fails validation in every mode; a Spark re-run with current code is needed.
- **B-D** The runtime artifact has no producing entry point, and its caps (10,000 rows, 16 MiB) do not fit the ~800k-row real slice.
- **B-E** No authored command, bucket or prefix for the 28-table Parquet upload.
- Also: the Terraform `endpoint` output is the Neptune reader endpoint; the loader poll budget is fixed at 300 s; the `awsIntegration` config template says dimension 2 (indexes are 256).
- Recommended Neptune access: a transient Fargate task in the graph-service security group with ECS Exec port-forwarding (about USD 0.06–0.12 for the 14C window); fallback: an in-VPC loader task. Pre-check in 14B right after base-apply: `GetEngineStatus` through the tunnel.

### 14C decisions (user, 2026-11-08)

1. **Neptune tunnel:** accepted. A temporary in-VPC task plus SSM port forwarding from the laptop, tested right after base-apply and before any 14C work. Neptune uses TLS with a certificate for its real endpoint hostname, and with IAM DB auth on, SigV4 signs that hostname; so connections through the tunnel must use the real endpoint name mapped to 127.0.0.1 (for example a temporary `/etc/hosts` entry; a JVM-only hosts file is an alternative that needs no sudo), never "localhost". The runbook gives exact steps, including removing the hosts entry afterwards. The tunnel test must prove a TLS, SigV4-signed request to the loader status endpoint works. The tunnel task is stopped and removed when the load finishes.
2. **Operator roles:** accepted. MFA required, maximum session 4 h, data-loading permissions only, scoped to this run's prefixes and tables; created in the same single deployer apply; removed at cleanup.
3. **Graph files:** `spark-engineer` re-runs the Phase 6 job locally with current code, checks the part sizes, and records the hashes.
4. **Runtime artifact:** a bounded subset within 10,000 rows and 16 MiB, chosen to include the entities used by the smoke test and the Phase 15 evaluation queries. The selection rule and actual counts are stated for the final report.
5. **Upload script:** accepted, with checksums recorded.
- Small fixes accepted (Neptune writer endpoint output, loader timeout override, `awsIntegration` dimension 256).
- Haiku price: the user checks the Bedrock pricing page in a browser and confirms 1.10 / 5.50 per 1M (us. route) or supplies the real numbers.
- The Nova note includes an embedding fallback for Titan.

### Bedrock restriction update (user, 2026-11-08)

- Amazon Nova Micro quotas are also 0 (cross-region TPM/RPM and tokens per day), so this is an **account-wide Bedrock restriction**, not specific models. The user updated the AWS Support case to ask for the restriction to be lifted, and escalates by chat on 2026-11-10 if there is no reply.
- **Nova is not a fallback.** The fallback note (no changes) must instead cover: (a) synthesis on the direct Anthropic API (client, API-key secret, egress, IAM, tests, cost); (b) embeddings without Bedrock: a small open-source model (vectors precomputed locally plus a query-time embedder in the cloud) versus a third-party embeddings API, including the vector dimension change and the cost and memory impact on 1 GiB Fargate.
- **Decision point: 2026-11-12.**

### Haiku 4.5 price confirmed (user, 2026-11-08)

On the Bedrock pricing page (US East Ohio): Geo (`us.`) cross-region USD 1.10 input / 5.50 output per 1M tokens; Global USD 1.00 / 5.00. The cost plan uses the Geo figures.

### Answers (user, 2026-11-08, after W5a and the fallback note)

1. **Sign-in:** the user signs in with the browser-based `aws login --profile scholarchain-deployer --region us-east-2` (not SSO, not static keys); the deployer root already carries the "same-device aws login" policy for that role (mirroring the Phase 12D human-identity bootstrap). The operator roles should use the same method, so the user runs `aws login --profile scholarchain-<loader|reader|cleanup>` directly with no role chaining: each operator role gets the same login policy, with trust and MFA conditions that work with how `aws login` authenticates. Verify from the Phase 12D evidence and AWS docs how long an `aws login` session lasts and whether it refreshes. If the sessions cannot cover the 1–2 h load: either (a) resumable, idempotent DynamoDB and S3 loads in chunks that fit the session, with a re-login step in the runbook, or (b) the load runs inside AWS as a one-off ECS task. Recommend one with its cost; the runbook shows the exact profile config and commands.
2. **Fallback client:** yes. Prepare the Anthropic-API fallback client now, offline and not merged, together with the embedding fallback note. It is activated only by the user's decision on 2026-11-12.
3. **Phase 12 account-ID mentions:** left as they are; decision recorded. No raw account ID in any new or changed file.
4. **Worker autoscaling:** the embedding worker stays fixed at 1. Phase 15 shows ECS scale-out and scale-in on query-api (CPU-based, standard metrics) plus EMR at three dataset sizes. Confirm query-api CPU scaling still works with Container Insights off.
- **EMR:** each run capped at 90 min of cluster time (about USD 0.84 each, 2.52 for all three), with automatic termination; three dataset sizes, one per run.

### Gap routing (user, 2026-11-08, after the deploy-engineer runbook draft)

"Yes — route all must-fix gaps", with conditions:
1. Wait for the live `sbt check` to finish and report its result before any agent edits files.
2. Add the two weak mutation catches (A3: certificate only with the runtime, caught only because the plan fails in `setUpClass`; U1: put without `--if-none-match`, caught only by the fake AWS's own refusal) to the fix list, each with a direct assertion.
3. The EMR-run permission goes into the same single deployer apply; no second apply.
4. EMR upload script and JAR build: written and built locally only. No uploads and no AWS calls until the approval record exists.
5. The Phase 15 load generator keeps LLM calls within the shared Haiku cap of USD 1.50 (shared with 16B) and defaults to the non-LLM endpoints.
6. After the fixes, re-run all test suites and the seven-gate check; then write the approval request, matching the "Replan 2026-11-08" block in phase14.md.

### Haiku answer buckets (user, 2026-11-08)

- Planning figure: about USD 0.01155 per synthesized answer (planner + synthesis at the confirmed geo rates 1.10 / 5.50 per 1M tokens).
- Buckets: **14C 10 / 15B 60 / 16B 40 / 17 demo + final smoke 5** = 115 answers, about USD 1.33 of the 1.50 cap.
- **Each bucket is a hard stop**, not a guideline: once a bucket is used up, that step makes no more Haiku calls. The overall USD 1.50 cap remains the backstop. Spare budget from an earlier step rolls forward **only with the user's OK**.

## Subphase 14B — repair round 2 (14B review 2: REQUEST-CHANGES, blocking B2)

### User decisions (2026-11-09, before the repair)

1. Blank-line fixes: "route them AFTER the review, so the reviewer sees the same tree as snapshot 8. Fix them before the pin refresh." Per the reviewer's follow-up, they are done after the round 2 recheck approves and before the pin refresh. They cover the four tracked files plus the untracked `infra/terraform/tests/phase14b_root.tftest.hcl` and runbook lines 432, 437 and 845.
2. Test exception: "accepted, under these conditions. It covers only AWS's documentation example account (<AWS documentation example account ID>), only in AwsTestSupport.scala. Record it as a named, file-scoped allowlist entry, not a pattern. The scanner must still fail on any other 12-digit account ID in that file, and on that example ID in any other file." The path is `modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/AwsTestSupport.scala`. The ID is written here as a placeholder, because the account scan allows it only in that file; this is the only change to the quoted words.

### User answers (2026-11-09, given in the repair-round-2 prompt; recorded verbatim)

- B2: "Yes. cleanup-prepare has no headroom floor, so negative headroom is accepted. The receipt must still exist, match its hash, be fresh, confirm monitoring and carry every numeric field. Cleanup must never be blocked by overspend."
- N1: "Yes, sales tax counts toward the USD 25. The billing address is in Chicago (60612), so assume about 11% (Chicago's lease tax on cloud services) until the user confirms the exact rate from the AWS bill. Show the 36 h and 42 h totals with tax in approval request §3.2, and say how Neptune scaling to 2.5 NCU would change the total. Say whether the USD 3 headroom floor still holds at 42 h with tax. If it doesn't, list the options (shorter hard stop, lower floor, or cost cuts) for the user to choose. Do not change any cap on your own."
- Scope: "The Bedrock → Anthropic/Voyage fallback switch is NOT part of this round. It comes after this recheck approves and the commit."

### Full-check timing (user, 2026-11-09, during repair round 2)

"alright so let run the check after the reviewer approve to save time"

This decision overrides step (d) of the reviewer's next prompt for this round.
- **Repair round 2 runs targeted checks only:** the affected script suites (`scripts/tests`, `tests/scripts`, `tests/infra`), the live `sbt check` on JDK 17, `git diff --check` and the pin drift.
- **The full seven-gate check runs once, after the recheck approves.** It runs on a fresh clean snapshot with its identity file, after the deferred whitespace fixes and before the pin refresh and the commit.
- **The recheck reviewer prompt states this deferral.**

## Subphase 14B — post-approval (review 3: APPROVE; F1–F3 nonblocking)

### User decisions (2026-11-09, answers to the coordinator's questions)

- **F1, the USD 3 floor at 42 h with tax:** "37 h hard stop (Recommended)", option 1. The session stays at about 36 h, the hard stop moves from H42 to **H37**, and cleanup starts no later than **H35**. No cap or pin changed. Projected headroom with tax at 37 h is USD 3.11 on the planned EMR, or 2.58 if EMR reached its full USD 3.00 cap (approval request §3.2).
- **F3:** "Yes, redact (Recommended)". The plan path at `review.md:136` and `:263` is replaced with `<plan path>`, noted as the only change.
- **N4:** "Accept as is (Recommended)". The Titan split stays 0.25 / 0.05. The uncapped query-time embeddings (about USD 0.001) are accepted, with no reserve and no template change.
- **H0 receipt headroom (coordinator found it after F1, user answered 2026-11-09): "Caps = planned use (Recommended)".**
  - The problem: with 11% tax, the pre-spend receipt that reserves full caps would show USD 2.37 at H0, below the floor of 3.
  - The fix: Haiku shared cap 1.50 → **1.33**; `EMR_CUMULATIVE_CAP_USD` 3.00 → **2.52**. Buckets, run count, per-run cap and the floor of 3 are unchanged.
  - The result: H0 receipt headroom 3.09 and 37 h headroom 3.30, with tax.
  - Routed to infra-engineer (release.conf, scripts), experiment-engineer (llm-allocation.json, load-profile, experiments and load-tests), test-engineer (tests/**), documentation-engineer (runbook R.1 with tax, new caps) and the coordinator (approval request §3.2, §3.3, §4, §11).
- **Review and full-check order (user, 2026-11-09).**
  - The user asked: "why do we need the review prompt? I though it was approved?" The coordinator explained that the cap pins, the runbook receipt formula and the 37 h stop changed after the approval.
  - Then the user asked: "shouldn't we run the full check after the review ?"
  - Decision, as the coordinator proposed and the user raised: a short delta review comes first, covering only the changes since the round-2 approval, with targeted tests. The full seven-gate check on a fresh snapshot runs once, after that review approves, then the pin refresh and the commit.
  - This overrides step (d) of the review-3 next prompt, which asked for the full check before the reviewer prompt.
- **Review 4 questions (user, 2026-11-09):**
  - N4: "Re-derive in round 3 (Recommended)". Nothing changes now. In repair round 3 (the Anthropic/Voyage switch, per the plan's "Update 2026-11-09" block), the coordinator proposes a synthesis cap near planned use at Haiku 5.5 prices, not 1.50, because the receipt reserves the full cap. The user updates the plan text after that decision.
  - N5: "Yes, keep it (Recommended)". The account constant at `scripts/billing/budget_execution.py:26` (Phase 12D) is intentional and stays under decision 3.
- **Pending for round 3:** the plan's "Update 2026-11-09" block says the instructor ruling is recorded verbatim in this file, with a screenshot at `evidence/14b/fallback/instructor-approval.png`. Neither is in the repository yet. The user supplies the ruling text and the screenshot.

## Subphase 14B — repair round 3 (Anthropic API and Voyage AI switch)

Started after the 14B commit `f5490d3` (pushed to `origin/phase-14`, user request 2026-11-09). Nothing live.

### Instructor ruling (2026-11-09; pasted by the user; recorded verbatim)

Screenshot: `evidence/14b/fallback/instructor-approval.png` (2000 × 1127 PNG converted from the user's image; sha256 `8b3822b1c098e61aa705471eb4f2ffe82a7c205b9d75e9d07cfced4fcb2c0c79`). It shows the instructor's reply at 12:38 PM under the student's fallback request.

```text
Yes, I approve using the Anthropic API for synthesis and Voyage AI for embeddings given the Bedrock quota restriction you described. Keep the remaining infrastructure and processing on AWS, and satisfy the project's existing functionality, evaluation, and reproducibility requirements. You may proceed without waiting for AWS to approve the quota increase.

Document the restriction and your fallback configuration in the report and README. Include the providers, exact model identifiers, embedding dimensions, and instructions for selecting and running each configuration. Retain the Bedrock switch as planned. If you change embedding models, regenerate the stored embeddings and rebuild the affected vector index so that stored vectors and query vectors use the same model and configuration.

Count external API charges toward the $25 overall project spending limit. Report AWS, Anthropic, and Voyage charges as separate items, followed by the combined total. Your estimated $1.50 therefore belongs in that total; any service that incurs no charge should be recorded as $0, with its usage documented.

The $25 limit is a ceiling, not a spending target. Monitor actual charges across providers and stop paid resources when your experiments are complete. Moving a bill outside AWS does not make it disappear.
```

The student's request shown in the screenshot proposed Claude Haiku 4.5 on the Anthropic API; the plan's "Update 2026-11-09" block selects `claude-haiku-5-5`. The ruling approves the provider (Anthropic API), not a specific Haiku version.

### Step 0 answers (user, 2026-11-09)

1. Ruling text and screenshot: supplied (above).
2. Price check: "yes please check it". Coordinator result (public documentation only, no account or API call):
   - `claude-haiku-5-5`: USD 0.10 input / 0.50 output per 1M tokens for prompts up to 100,000 tokens; USD 0.50 / 2.50 above that (Anthropic pricing page, fetched 2026-11-09). Anthropic meters before tax.
   - `voyage-4-lite`: USD 0.02 per 1M tokens; 200M free tokens per account; `output_dimension` 256 supported (also 512, 1024 default, 2048); 32,000-token context; up to 1,000 texts and 1M tokens per request (Voyage docs, fetched 2026-11-09).
   - Haiku 5.5 API rules (Claude API reference): `temperature`, `top_p` and `top_k` return 400 at non-default values; assistant prefill returns 400; a forced `tool_choice` is accepted and the response then has no thinking block; `stop_reason: "refusal"` with no server-side fallback; the tokenizer produces about 30% more tokens than Haiku 4.5.
3. Synthesis cap: "remember 25 is just suggestion not a strictly real cap. so choose which way is easiest to implement cheap is second priority".
   - Coordinator choice (easiest): keep the shared cap at USD 1.33 and the 115-answer buckets unchanged. Only the per-answer estimate in the load profile moves to Haiku 5.5 prices with token sizes raised by 30%. At those prices 115 answers estimate well under USD 1.33, so 1.33 becomes a conservative upper bound, the receipt reservation and every cap pin stay as they are, and the bucket counts remain the binding limit.
   - Recorded conflict, not resolved by the coordinator: the instructor ruling above calls USD 25 "the $25 overall project spending limit" and "a ceiling", and the plan calls it a hard ceiling. The existing ceiling checks stay in place; the easiest option needs no change to them.
4. Anthropic client from worktree `phase14-anthropic-fallback`: "A, with conditions" (verbatim):

   ```text
   A, with conditions:
   1. The rag-engineer reviews the worktree diff before merging and records what it took and what it changed.
   2. Update it to the claude-haiku-5-5 rules: no temperature, top_p or top_k, even if the runtime config has temperature 0.0; forced tool_choice kept; no prefill; content blocks read by type; stop_reason "refusal" is a typed, non-retried error; max_tokens sized for ~30% more tokens; $schema, $id and title stripped from the tool schema; strict not set.
   3. Add tests for each rule above (fake HTTP only). Then rerun the full RAG suite here on phase-14. The worktree's 120 passing tests don't count as evidence for this branch.
   4. Leave the worktree and its branch in place. Don't delete them.
   ```

5. API keys: "Yes make sure agents guide me how to put the api key in". Terraform creates empty Secrets Manager containers only; the user enters each key value during the live session following written steps; agents never see, print or write a key value.

### Repair round 3 work order (coordinator, 2026-11-09)

Scope comes from the plan's "Update 2026-11-09" block, the instructor ruling and the Step 0 answers above. Offline only: no live command, no AWS, Anthropic or Voyage call, no key value anywhere, no commit. Every agent runs Sonnet 5.5 at high effort and edits only the paths it owns.

Shared contract (all owners build to these names):

| Item | Value |
|---|---|
| Synthesis switch | env `SCHOLARCHAIN_SYNTHESIS_PROVIDER` = `anthropic` (default) or `bedrock`; Terraform `synthesis_provider` |
| Embedding switch | env `SCHOLARCHAIN_EMBEDDING_PROVIDER` = `voyage` (default) or `bedrock`; Terraform `embedding_provider` |
| Anthropic primary | model `claude-haiku-5-5`; Messages API `https://api.anthropic.com/v1/messages`; no `temperature`, `top_p` or `top_k` (even when config says 0.0); forced `tool_choice` kept; no prefill; content read by block type; `stop_reason` `refusal` is a typed, non-retried error; `max_tokens` sized for about 30% more tokens than Haiku 4.5; tool schema without `$schema`, `$id`, `title`; `strict` not set; prompt must stay under 100,000 tokens (higher price tier above it) |
| Voyage primary | model `voyage-4-lite`; `output_dimension` 256; `input_type` `document` for ingest and `query` for queries; at most 1,000 texts and 1M tokens per request; embedding model version tag `voyage-4-lite` (aws mode; 14C ingest and query smoke use the same values) |
| Vector consistency | stored and query vectors must share provider, model, dimension; a mismatch is refused, and changing the embedding model requires a full re-embed and an index rebuild |
| API keys | ECS injects `SCHOLARCHAIN_ANTHROPIC_API_KEY` and `SCHOLARCHAIN_VOYAGE_API_KEY` from two Secrets Manager secrets, each created only when its provider is selected, with no secret version in Terraform (the user enters the value); the execution role may read only those two ARNs; key values are never logged, printed or written |
| Bedrock fallback | Haiku 4.5 and Titan V2 stay selectable; Bedrock invoke grants exist only when a Bedrock provider is selected; no Marketplace permission on any app role |
| Egress | the existing single NAT, TCP 443 |
| Caps | synthesis shared cap stays USD 1.33 with buckets 10/60/40/5 = 115 answers (Step 0 answer 3; the plan's 1.50 is superseded); per-answer estimate moves to Haiku 5.5 prices (0.10 / 0.50 per 1M) with token sizes raised 30%; embeddings cap USD 0.30 with a token counter (Voyage 0.02 per 1M; first 200M tokens free) |
| Receipts | pre-spend receipts add Anthropic and Voyage spend to date (USD, entered by the user from the provider consoles) |
| Cleanup | deletes both secrets; the runbook tells the user to revoke both keys in the provider consoles afterwards |
| Cost reporting | AWS, Anthropic and Voyage as separate items, then the combined total; a provider with no charge is listed as USD 0 with its usage documented |

Superseded: the "user makes the first Haiku 4.5 playground call" step; the Bedrock quota precondition; open question 14-3 unless a Bedrock run is chosen.

Routing: wave 1 rag-engineer (`modules/rag/**`), service-engineer (`modules/services/**`), infra-engineer (`infra/terraform/**`, `scripts/**`), experiment-engineer (`experiments/**`, `load-tests/**`); wave 2 documentation-engineer (`README.md`, `docs/**` outside the reserved subtrees) and test-engineer (`tests/**`). Anything outside an owner's paths returns as `BLOCKED-ON`.

## Subphase 14B — pre-session items (after review 7: APPROVE; round 3 committed as `13b886a`)

Started after commit `13b886a` (pushed to `origin/phase-14` at the user's request, 2026-11-10). Scope: the 10 open pre-session items in `approval-request-14b-replan.md` §10. Offline only: no live command, no AWS, Anthropic or Voyage call, no key value anywhere, no git stash, no commit without the user's yes.

### Step 0 answers (user, 2026-11-10)

The user's answer, verbatim: "accepts all by default". Every recommended default below is therefore the decision.

| # | Item | Owner | Decision (recommended default, accepted) |
|---|---|---|---|
| 1 | Source of the `--er-policy`, `--er-config` and `--spark-config-template` files | experiment-engineer | Use the files already in the repository from the Phase 5/6 local runs; the agent lists each path and sha256. No new settings. |
| 2 | Real `include-ids.txt`, `real-query.json`, `questions.txt`, `node-ids.txt` | experiment-engineer, storage-engineer | Derive them with a committed, deterministic script from the local export `f6e63b4b`; commit the small ID files (IDs only). |
| 3 | 16B live-evaluation command and question set | experiment-engineer, coordinator | 40 fixed questions drawn from the real-data slice (researchers and pairs present in the export), and one command that runs them through the 16B answer bucket. |
| 4 | Render config `templateVersion`, `runtime_reference`, assembly of `emr_service_policy_json` | coordinator with infra-engineer | Values from `release.conf` and the committed template; the infra-engineer documents and tests the assembly. |
| 5 | `scripts/billing/README.md:129` calls the billing login command unverified | infra-engineer | Match the deployer README's command, marked "verified live in the session". |
| 6 | 28 vs 29 fields | infra-engineer | Count the fields in the code and correct whichever document is wrong. |
| 7 | Vector bucket name is not a Terraform output | infra-engineer | Add it as an output (no AWS change); the runbook stops deriving it from the IAM policy. |
| 8 | 14C template `idempotencyIndex` | rag-engineer | Confirm `by-idempotency-key` from the Terraform and the code; the template is corrected. |
| 9 | Expected plan addresses for the pointer and EMR runtime-applies | infra-engineer | Derive them from the offline Terraform tests and list them; the real plan is compared against them in the session. |
| 10 | Whether `archive-evidence.sh` refuses directories containing plan files | infra-engineer | Read the code and add a test; keep the runbook's file-by-file approach if it refuses. |

Extras (same answer, defaults accepted):

- A. `evidence/14b/replan/14c-templates.md` and `evidence/14b/replan/fallback-note.md` stay unchanged as history; a short superseding note is added on top pointing to the Voyage and Anthropic configuration (coordinator, `docs/agent-runs/**`).
- B. N6: `PRESPEND_PROJECT_CEILING_USD=25` is kept.
- C. Key-entry method: AWS console, the secret's **Edit** control, under the user's own sign-in.
- D. The plan file's synthesis cap text (USD 1.50) is updated to USD 1.33 by the user; agents cannot edit the plan.

### Pre-session work order (coordinator, 2026-11-10)

Every agent runs Sonnet 5.5 at high effort, edits only its own paths, and returns anything else as `BLOCKED-ON`. No AWS, Anthropic or Voyage call; no reading of `*.local.tfvars`, Terraform state, `~/.aws`, `.env` or secret directories; no raw account ID, email address or key value in any file; no git stash.

Wave 1: experiment-engineer (items 1, 2, 3), infra-engineer (items 4 assembly, 5, 6, 7, 9, 10), rag-engineer (item 8). Wave 2: storage-engineer (offline check of the item 2 ID files against `RuntimeArtifactMain` and the include-list format), documentation-engineer (runbook gaps replaced by the delivered paths and values). Coordinator: item 4 values, extra A notes, records.

### Coordinator decisions from the wave 1 reports (2026-11-10)

- Item 4, `emr_config.runtime_reference`: `docs/agent-runs/phase-12/evidence/12d-spike-closeout/decision-12-10.md` (the accepted record of the proven EMR runtime, `docs/agent-runs/phase-12/human-gate.md:28`; its archive sha256 equals `scripts/config/release.conf:106`). Free text, stamped as the cluster tag `runtime_evidence` (`infra/terraform/modules/emr/main.tf:111`); the value contains no `#`.
- Item 4, render-config and live-config `templateVersion`: `phase14c-v1`. Nothing in the repository fixes one (`docs/agent-runs/phase-08/evidence/8b-r1/render-config.template.json:10` is a placeholder); it meets `EmbeddingContracts.scala:196-198` (non-blank, no whitespace, at most 256 bytes). It is part of the stable vector slot key, so it must not change after the 14C ingest (a change re-embeds everything).
- Item 8 / extra A: superseding notes added on top of `evidence/14b/replan/14c-templates.md` and `evidence/14b/replan/fallback-note.md`; the old text is unchanged.
- Item 2 rework: the storage-engineer's offline `RuntimeArtifactMain` run refused the first include list (39 hub researchers, about 27,000 rows against the 10,000-row cap; exit 1, no artifact written). Routed back to the experiment-engineer: degree band and a total-degree budget of at most 900, all five files regenerated together, verified by a local `RuntimeArtifactMain` run (exit 0).
- 16B ledger: `load-tests/eval16b.py` charges bucket 16b itself (as `loadgen.py` does for 15B), so the runbook's "reserve first" step is removed for 16B to avoid double counting.
- Item 10 observation, not routed: `scripts/lib/archive.py` refuses plan files by name; a file named `*.plan.txt` (the runbook's private `deployer-replan.plan.txt`) does not match. No runbook include points at `target/phase14/private`, so it is unreachable today; recorded for the reviewer.

## Subphase 14B — runbook A1 preparation (after commit 2eb30ef)

User answers in chat, verbatim, 2026-11-10/11:
- "Yes start" (coordinator runs A1.2 and A1.4 offline).
- A1.2 expiry: "Yes, keep it" (`expiration_date = "2026-11-25"`).
- "A0 = Anthropic + Voyage"; "questions OK" (`experiments/inputs/14c/questions.txt`, `real-query.json`); "plan cap fxied" (plan file cap text 1.33).
- A1.3: "confirmed that is correct prices"; the user set `EMR_PRICING_CONFIRMED_BY_HUMAN=true` in `scripts/config/emr-pricing.conf` themself.
- A1.5: "For the approval note, I want you to write it for me, then I will read and confirm or ask for any changes", then "I confirm it". The coordinator drafted `approval-14c.md` from the runbook A1.5 checklist; its opening lines say so, and the user adopted it unchanged.

Coordinator decision: the A1.4 render made two experiment tests fail because they assumed the committed 15a manifests hold all-zero placeholder hashes; the experiment-engineer changed only those two tests so they hold in both states (option a), instead of leaving the gate red.
