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
