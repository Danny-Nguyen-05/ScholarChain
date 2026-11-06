# Phase 13 repairs

## Subphase 13A — repair round 1 (from review 1, REQUEST-CHANGES)

The source is the user-supplied external review in `review.md` (Subphase 13A, review 1). Severity, owner and acceptance checks are kept as the reviewer gave them.

| ID | Severity / blocking | Owner | Paths named by the reviewer | Acceptance check (reviewer) | Repair status |
|---|---|---|---|---|---|
| F1 | P1 / yes | infra-engineer | deploy exclusion; Git helper (`scripts/deploy.sh`, `scripts/lib/common.sh`) | Only the literal agreed record path is exempt. Test an alternate in-repo approval path, an inherited `SC_DIRTY_EXTRA_EXCLUDE`, pathspec metacharacters, and a failing `git status`. Each must refuse before AWS or Docker runs. | fixed (repair-1) |
| F2 | P1 / yes | infra-engineer | deploy checks, optional receipt, apply, Terraform provider (`scripts/deploy.sh`, `scripts/plan.sh`) | Verify the saved plan's target and revision, require clean plan provenance tied to its checksum, and apply the verified bytes. Fake tests: missing or mismatched provenance; a different planned account, region or image revision; a plan replaced between verification and apply. | fixed (repair-1) |
| F3 | P1 / yes | infra-engineer | preserve list, inventory token, destroy sequence, bucket protection, grading log resources (`scripts/cleanup.sh`, config) | Produce a policy-compliant teardown plan, list its actual destructive actions, and bind confirmation to the exact saved plan, account, region and environment. Fake tests reject a protected target, an unlisted delete, a changed plan and token reuse across accounts. Keep the Terraform protections and the two-pass IAM constraint. | fixed (repair-1) |
| F4 | P1 / yes | infra-engineer | plan output paths, raw JSON capture, ignore rules, timeout trace, persistent logs (`scripts/plan.sh`, `scripts/lib/timeout.py`, `scripts/lib/common.sh`) | Keep raw plan exports private and outside commit scope for every supported output path. Test `.plan` and an exact-name ignore rule, plus fake private values in subprocess diagnostics and account-bearing argv. Assert that stdout, stderr and retained logs contain no canaries. | fixed (repair-1) |
| F5 | P1 / yes | infra-engineer | deploy mutation sequence; plan §7.3a (`scripts/deploy.sh`, rollback inherits) | Verify human-approved pre-spend evidence before any paid mutation. Fakes prove that missing monitoring, stale or missing cost evidence, and insufficient headroom each prevent push, apply and upload. | fixed (repair-1) |
| F6 | P2 / yes | infra-engineer | manifest validation, image push, ECS result, single-service fake (`scripts/deploy.sh`, `scripts/tests/test_deploy.py`) | Verify the identity and architecture of the images actually pushed. For a runtime deployment, verify all four task definitions and their expected image references before recording success. Fakes: a replaced local tag, a missing service, a stale task definition. | fixed (repair-1) |
| F7 | P2 / yes | infra-engineer | rollback instructions, rollback fixture, first-deployment flow (`scripts/rollback.sh`, `scripts/README.md`, tests) | Document and fake-test the complete flow with a previous tree that lacks the release scripts, and with separately approved base apply, image push and runtime apply. Keep the ECR-existence refusal and the two-stage rollback. | fixed (repair-1) |
| F8 | P2 / yes | infra-engineer | plan invocation, output truncation (`scripts/plan.sh`, `scripts/lib/common.sh`) | A complete review path for the exact saved plan, with private values protected. A fake plan longer than 40 lines keeps an early action and keeps a synthetic private value out of shareable output. | fixed (repair-1) |
| F9 | P2 / yes | infra-engineer (suite runner); orchestrator (evidence) | suite runner, clean-copy log, full-run tree snapshot (`scripts/check.sh`, config) | The default gate fails, or reports partial, when a required suite is omitted or empty. Retain one final real seven-gate `scripts/check.sh` exit 0 from a clean snapshot of the repaired sources under JDK 17. | fixed (repair-1) |
| F10 | P2 / yes | infra-engineer | fixture setup, inside-network assertion (`scripts/tests/test_terraform_r1.py`) | Build the fixture from approved source inputs only and isolate Terraform working metadata. Test with synthetic ignored private files and verify they are excluded. Use a valid inside-network fixture and require a successful run before reporting that case as passing. | fixed (repair-1) |
| N1 | P3 / no | infra-engineer | rollback command construction, version probe, timeout validation | Assert `--profile` propagation in the dry-run text, bound the version probe, and reject `nan`/`inf` before spawning a child. | fixed (repair-1) |
| N2 | P3 / no | orchestrator | test report, ignore rule | Retain small commit-eligible excerpts of the JDK 27 refusal and the live-probe logs, with commands and results. | fixed (repair-1) |

### User decisions for repair round 1 (2026-11-05)

- **F5 pre-spend gate:** the human writes a pre-spend receipt (JSON). It records: monitoring/budget alert confirmed active; cost snapshot UTC time; reported spend; unreported-usage allowance; reserves; remaining headroom. The approval record names it with `APPROVED_PRESPEND_SHA256`. `deploy.sh`, and `rollback.sh` through it, refuse before any push, apply or upload when any of these holds:
  - the receipt is missing;
  - its hash differs;
  - the snapshot is older than 24 h;
  - monitoring is not confirmed;
  - headroom is below USD 20 (a pinned config value);
  - any cost field is missing. Missing cost data is never treated as zero.
- **F3 preservation policy:** never destroy:
  - Terraform state/backend;
  - all S3 buckets and objects (datalake, evidence, artifacts);
  - S3 Vectors;
  - the KMS keys and key policies that keep preserved data readable;
  - CloudWatch log groups needed for grading.

  Teardown classes: ECS/ECR runtime, EMR, Neptune, DynamoDB, SQS, Step Functions, and the network (NAT/EIP, endpoints, VPC). Destroy stays two-pass (carried item 24); IAM is not widened.

Phase 14 access-gate observation (not a 13A finding): the deployer permission sets have no ECR/ECS actions for the new path. Terraform/IAM widening is outside the authorized 13A repair scope, so this is carried to the Phase 14 human gate (and 13C, if the user chooses).

### Repair round 1 results

Repaired by `infra-engineer`: a fresh context, model `sonnet` (Sonnet 5.5), effort `high`, native ID `ac3278ecc022a0927`. All edits are under `scripts/**`. The tables below show the change for each finding and the tests that prove the acceptance check. Full test names are in `owner-report.md` (13A repair round 1).

#### Blocking findings

| ID | Change | Proving tests |
|---|---|---|
| F1 | Exact-path exemption is parsed from `git status --porcelain=v1 -z`. `--approval` adds no exemption, inherited exclusion env vars are gone, `GIT_*` variables are stripped, and a git error or unparsable output refuses. | `test_deploy.DeployDirtyTreeTests` (9) |
| F2 | plan.sh writes a v2 provenance receipt and deploy.sh requires it. The plan is copied once into a private directory, and the copy's sha is checked against both the record and the receipt. The copy's `show -json` must match the record's region, account hash and image revision. The copy is re-hashed and applied only as that copy. | `test_deploy.DeployPlanProvenanceTests` (10), `test_plan.PlanTargetBindingTests` |
| F3 | Pinned preserve and teardown classification. Targeted destroy plan. Every `DESTROY-ACTION` is listed, and the run refuses on a preserved-class delete or replace, an unlisted delete, or a non-delete action. Token = sha256 of (plan sha, account hash, region, environment, sorted actions). The confirm run applies the verified copy only. The item 24 two-pass note is kept. | `test_cleanup.CleanupListingTests`, `CleanupConfirmTests`, `CleanupPolicyConfigTests` |
| F4 | Plan outputs are confined to PLAN_DIR (realpath). Every derived path must pass `git check-ignore`. Modes are 0700/0600. The timeout trace and `--log` output are redacted before they are written; if the redactor is missing, nothing is traced. | `test_plan.PlanOutputPathTests`, `PlanRedactionTests`, `test_timeout`, `test_package`, `test_safety` |
| F5 | `APPROVED_PRESPEND_SHA256` plus the pre-spend receipt are required, with pinned limits of 24 h and USD 20. A missing, null or non-numeric field is never read as zero. The checks run before any aws, docker, apply or upload, in all stages. | `test_deploy.DeployPrespendTests`; rollback refusal test |
| F6 | Local tags are re-inspected against the manifest image ID and architecture before push. The pushed digest must equal the ECR digest. After a runtime apply, all four services must reference their own image before success is recorded. | `test_deploy.DeployPushTests`, `DeployRuntimeApplyTests` |
| F7 | `deploy.sh --stage base-apply\|push\|runtime-apply` with `APPROVED_STAGE`. Rollback runs the current scripts against the previous commit's `infra/terraform`, materialized with `git archive`. The first-deployment and rollback sequences are documented. | `test_rollback.InfraRollbackFromATreeWithoutScriptsTests`; stage tests in `test_deploy` |
| F8 | The full private plan text is saved, and its path and sha are printed. The `PLAN-ACTION` list is never truncated and holds address and action only. | `test_plan.PlanReviewPathTests` (77-action plan) |
| F9 | Required suites are pinned inside check.sh. An omitted suite, or one that executes zero tests, fails the gate. Orchestrator evidence: clean-snapshot seven-gate run, exit 0. | `test_check.CheckScriptTestGateTests`; `evidence/13a/repair-1/check-full-clean-snapshot.txt` |
| F10 | The fixture is built only from `git ls-files`. TF_DATA_DIR is isolated and providers come from a read-only `-plugin-dir`. The inside-network case must succeed (18 passed). | `test_terraform_r1` (10, none skipped) |

#### Nonblocking findings

| ID | Change | Proving tests |
|---|---|---|
| N1 | `--profile` is propagated to delegated commands. The version probe goes through the timeout helper. nan, inf and values ≤ 0 are rejected before spawn. | `test_rollback`, `test_timeout` |
| N2 | The JDK 27 refusal and the live-probe logs were renamed from `.log` to commit-eligible `.txt`, each with a command header. | `evidence/13a/build/*.txt` |

#### Open for the human

**A2.** The pinned teardown set also includes the runtime IAM roles and policies (`module.identity` task, execution, emr_ec2, emr_service and neptune_loader roles; their role policies; the EMR instance profile) and `module.observability` alarms and dashboard. A targeted destroy pulls these in as dependents. KMS keys, log groups and the deployment role remain preserved or unlisted.

## Subphase 13A — repair round 2 (from review 2, REQUEST-CHANGES)

The source is the user-supplied external review 2 in `review.md`. All findings are owned by `infra-engineer`. F1, F8, F9, F10, N1 and N2 stay closed. A2 stays **pending** until the human records a decision. The user asked the orchestrator to fix all blocking findings (2026-11-05).

### Findings

| ID | Severity / blocking | Reviewer source references | Acceptance check (reviewer) | Status |
|---|---|---|---|---|
| R1 (F7) | P1 / yes | `scripts/plan.sh:202`, `scripts/deploy.sh:357`, `infra/terraform/README.md:179` | No-cloud regression with populated local state and an older commit that lacks the release scripts. Rollback must plan against the existing state and refuse a missing or different state before apply. Two-stage approval kept. | fixed (repair-2) |
| R2 (F4) | P1 / yes | `scripts/plan.sh:164`, `scripts/lib/timeout.py:63`, `scripts/cleanup.sh:181` | Every output is confined to a private directory at write time. Symlinks and colliding output paths are rejected. Fakes cover pre-existing links at the derived filenames, and an outside canary file stays intact. | fixed (repair-2) |
| R3 (F2) | P1 / yes | `.gitignore:51`, `scripts/plan.sh:194`, `scripts/deploy.sh:345`, `scripts/lib/verify.py:197` | Verify which source Terraform loaded, check the saved plan's actual environment, and bind the reviewed provenance to the approval. Regressions: an ignored Terraform override, a mismatched planned environment, a receipt edited after review. | fixed (repair-2) |
| R4 (F6) | P2 / yes | `scripts/deploy.sh:623`, `scripts/deploy.sh:638`, `scripts/tests/test_deploy.py:812` | Runtime apply is bound to the verified push record for the same commit, account, region and four repositories. A missing record or a changed digest refuses before apply. The four-service ECS verification and the rollback digest checks are kept. | fixed (repair-2) |
| R5 (F3) | P2 / yes | `scripts/cleanup.sh:55`, `infra/terraform/modules/neptune/main.tf:26`, `infra/terraform/modules/runtime/compute.tf:74` | Document and gate the separately reviewed Terraform preparation for every protected teardown resource. Active protection blocks the destructive sequence until preparation is complete. Preservation policy, saved-plan confirmation and the two-pass IAM constraint are kept. | fixed (repair-2) |
| R6 (F7) | P2 / yes | `docs/agent-runs/phase-13/prompt.md:37`, `scripts/deploy.sh:325`, `scripts/README.md:162` | Show the recorded sequence (approved base apply → push → runtime plan) end to end with fakes, including a separately approved push that refuses when the ECR repositories are missing. No contract change without a recorded human decision. | fixed (repair-2) |
| R7 (F5) | P2 / yes | `scripts/deploy.sh:292`, `scripts/deploy.sh:530`, `repairs.md:24` | A controllable clock in fake tests. A receipt that expires after initial verification prevents the next paid operation, including the upload after base apply. | fixed (repair-2) |
| R8 | P2 / yes | `scripts/deploy.sh:357`, `scripts/tests/test_deploy.py:612` | Dry runs print the `show` command and disclose that inspection is deferred. No AWS, Docker or Terraform operation beyond the version probe. Inspection of the verified plan stays mandatory before any execute-path mutation. | fixed (repair-2) |
| R9 (G5) | P2 / yes | `scripts/deploy.sh:405`, `scripts/deploy.sh:530` | Upload the same private copy whose bytes passed the pinned size and SHA-256 checks. A fake apply replaces the original archive; the replacement is never uploaded or recorded as verified. | fixed (repair-2) |
| N3 | P3 / no | `scripts/tests/test_terraform_r1.py:73` | Honor `TERRAFORM_BIN`, and show the R1 cases ran on an installation that has Terraform only through that override. | fixed (repair-2) |

### Orchestrator repair design (within the recorded decisions; no contract change)

- **R6:** the `push` stage needs no plan. Its approval record carries commit, account hash, region, stage and pre-spend lines, and no plan line. This restores the recorded order: base apply → push → runtime plan → new approval → runtime apply.
- **R3:** binding provenance to the approval means a new required approval-record line, `APPROVED_RECEIPT_SHA256`, for the stages that apply a plan. This extends the 13-2 format the same way F5 added `APPROVED_PRESPEND_SHA256`. Planning always runs from a `git archive` of the commit, never from the worktree, so ignored override files cannot load.
- **R5:** uses the existing `cleanup_mode` variable, which already switches off Neptune, ALB and DynamoDB deletion protection and turns on ECR `force_delete`. No Terraform change is needed.

### Repair round 2 results

Repaired by `infra-engineer` (fresh context, model `sonnet` / Sonnet 5.5, effort `high`, native ID `ac38b9848cff4b821`). The orchestrator paused it once for the user's usage budget and resumed it with its context intact. All edits are under `scripts/**`. Evidence is in `evidence/13a/repair-2/`.

#### Blocking findings

| ID | Change | Proving tests (in `scripts/tests/`) |
|---|---|---|
| R1 | The materialized source gets a generated `backend "local" { path = <abs live state> }` binding, proven with real Terraform 1.13.5. The receipt records state lineage, serial and sha256. Deploy refuses a missing state, a different lineage, or any serial/sha change before every apply. `--expect-new-state` covers the first deployment. The two-stage rollback is kept. | `test_terraform_state_binding.py` (7, real Terraform on a local fixture: rollback plans against the existing state with no create; control without state proposes create; missing, different-lineage or changed state refused before apply), `test_plan.PlanStateBindingTests`, `test_deploy.DeployStateBindingTests`, `test_rollback`, `test_state_records` |
| R2 | A fresh 0700 run directory per run. Every output must be absent beforehand, inside its directory with no symlink component, ignored by Git and distinct from the others, and is opened with O_CREAT\|O_EXCL\|O_NOFOLLOW (no O_TRUNC). The same writer serves timeout capture/trace, receipts, manifests, push records and cleanup evidence. The cleanup evidence directory may not alias or nest in the plan directory. | `test_plan.PlanOutputPathTests` (symlink at each derived name; the outside canary stays unchanged), `test_cleanup.CleanupOutputConfinementTests`, `test_safeio` (15) |
| R3 | Planning always runs from a `git archive` of the commit, and `source_tree_sha256` is re-checked at deploy. The saved plan's `environment`/`project` are checked against the receipt, the config and `APPROVED_ENVIRONMENT`. `APPROVED_RECEIPT_SHA256` is required for the plan-applying stages. | `test_plan.PlanSourceTests`, `test_deploy.DeployReceiptBindingTests` (a receipt edited after review; an ignored override at deploy), real-Terraform override test |
| R4 | The push stage writes a private push record only after digest verification. Runtime apply requires it for the same commit, account, region, environment and four repositories, and requires the current registry digests to equal the pushed digests before apply. | `test_deploy.DeployPushRecordBindingTests`, `DeployPushTests`, `DeployRuntimeApplyTests` |
| R5 | Cleanup reads the current protection state and refuses with `PREPARE-REQUIRED` while any Neptune, ALB, DynamoDB or ECR protection is active. `cleanup.sh --prepare` builds a `cleanup_mode=true` plan limited to the protection/force flags of teardown resources, applied through the new `deploy.sh --stage cleanup-prepare` (approval record, receipt hash, pre-spend). | `test_cleanup.CleanupProtectionTests`, `CleanupPrepareTests`, `test_deploy.DeployCleanupPrepareStageTests`, `test_state_records` |
| R6 | The push stage needs no plan. A plan or receipt line in a push approval record is refused. The recorded order is restored, and push refuses while ECR repositories are missing. | `test_deploy.DeployFirstDeploymentSequenceTests` (end to end, three approval records), `DeployApprovalRecordTests` |
| R7 | The pre-spend receipt is re-verified before the ECR login, each push, each apply and the archive upload. A test clock is honoured only with the announced test-only config file. | `test_deploy.DeployPrespendFreshnessTests` (10), `test_state_records.PrespendClockTests` |
| R8 | A dry run runs only the Terraform version probe. It prints the deferred init/show commands. Inspection stays mandatory before any execute-path mutation. | `test_deploy.DeployDryRunTests`, `test_safety`, `test_rollback` |
| R9 | The archive is copied once to the private run directory. Size and sha256 are verified on the copy, which is re-hashed before upload. The copy is what gets uploaded, its own hash becomes the metadata, and the upload is verified against the copy. | `test_deploy.DeployBaseApplyTests` (an original replaced during apply is never uploaded or recorded) |

#### Nonblocking finding

| ID | Change | Evidence |
|---|---|---|
| N3 | The R1 test honors `TERRAFORM_BIN`. | `n3-terraform-bin-only.txt` (no Terraform on PATH; 10/10 executed, 0 skipped) |

#### Approval-format additions (pending human acknowledgment)

These extend the agreed 13-2 format as part of the repair. They do not change the recorded deployment order:
- `APPROVED_RECEIPT_SHA256` (orchestrator design for R3).
- `APPROVED_ENVIRONMENT` (infra-engineer, for R3's planned-environment binding).
- A new `cleanup-prepare` deploy stage (R5).
- `cleanup.sh --confirm` now also takes `--plan <destroy plan>`.

#### Still pending

- **A2:** the human decision is still pending.
- **Live state location:** the real checkout has no `infra/terraform/terraform.tfstate` yet. A first base apply needs `plan.sh --expect-new-state`, and the human should confirm where live state will live.

## Subphase 13A — repair round 3 (from review 3, REQUEST-CHANGES)

The source is the user-supplied external review 3 in `review.md`. Review 3 confirmed that R1–R9 and N3 meet their acceptance checks, and that F1, F8, F9, F10, N1 and N2 remain closed.

| ID | Severity / blocking | Owner | Paths (reviewer) | Acceptance check (reviewer) | Status |
|---|---|---|---|---|---|
| S1 | P2 / yes | infra-engineer | `scripts/deploy.sh:279-281,419-422`; `scripts/rollback.sh:246,248`; `scripts/lib/verify.py:248-250,301-303`; `infra/terraform/phase12b.tf:25`; `infra/terraform/modules/runtime/compute.tf:2,75`; `scripts/README.md:203-206`; `scripts/tests/test_rollback.py:223,307` | Either (a) infra rollback carries a deployed image revision, bound to a verified previous deploy manifest or to a push record whose registry digests are checked before apply (as with `--reuse-images`); the receipt, approval and plan-target checks stay; all four ECS services are verified afterwards; fake tests cover a populated state with the runtime enabled. Or (b) a recorded human decision limits infra rollback to runtime-disabled states, and any infra-rollback plan that deletes or replaces runtime-class resources, or fails the runtime precondition, is refused fail-closed with a clear `STEP` marker, documented in `--help` and `scripts/README.md`, with a fake test. Either way, keep the two-stage flow, the state binding, the ECR-existence refusal and the recorded first-deployment order. | routed |
| N4 | P3 / no | infra-engineer; orchestrator (evidence wording) | `scripts/tests/test_terraform_state_binding.py:53-55`; `scripts/check.sh:267-300`; `evidence/13a/repair-2/check-full-clean-snapshot.txt:54` | The default gate runs these tests on a clean checkout, for example by initialising providers first, ordering the Terraform gate earlier, or failing on a skip of a required class. Reword the evidence counts. | routed (optional) |
| N5 | P3 / no | infra-engineer | `scripts/deploy.sh:757-769` | Optional: compare the object's S3-computed `ChecksumSHA256`, or document why the upload-time check is enough. | routed (optional) |

### User decision for repair round 3 (2026-11-05)

**S1: option (a), keep the runtime.** Infra rollback carries the currently deployed image revision. That revision is bound to a verified previous deploy manifest or push record, and its registry digests are checked before apply. The four ECS services are re-verified afterwards. The receipt, approval and plan-target checks stay.

### Evidence wording correction (N4, orchestrator)

The repair-2 clean-snapshot evidence said "426 executed + 1 skipped". The accurate statement: 427 tests executed, and the 7 `test_terraform_state_binding` tests did not run (one class-level skip, which `Ran` does not count). The separate snapshot rerun (`state-binding-in-snapshot.txt`, 7 OK) proves R1; the default gate alone did not.

### Still pending human decisions

- A2.
- The approval-format additions (`APPROVED_RECEIPT_SHA256`, `APPROVED_ENVIRONMENT`, the `cleanup-prepare` stage, `cleanup --confirm --plan`).
- The live-state location.

### Repair round 3 results

Repaired by `infra-engineer`: fresh context, model `sonnet` (Sonnet 5.5), effort `high`, native ID `a89ab5013d9c6e932`. All edits are under `scripts/**`. Evidence is in `evidence/13a/repair-3/`.

| ID | Change | Proving tests (in `scripts/tests/`) | Status |
|---|---|---|---|
| S1 | **Rollback keeps the runtime.** In infra mode, `rollback.sh` takes `--deployed-manifest` or `--deployed-push-record`. It reads the live state (STEP `runtime-state`). A live runtime without a binding is refused, and so is a binding when no runtime is live. It then verifies the binding (`deployed-revision`) and checks the registry digests before any plan (`verify-registry-digests`). The plan is `plan.sh --source-commit PREV --image-revision REV`, checked by `runtime-preservation`. The apply is `deploy.sh --stage runtime-apply --source-commit PREV` with `--reuse-images` or `--image-revision` plus `--push-record`. Approval stays `APPROVED_STAGE=runtime-apply`, with `APPROVED_COMMIT=PREV` and `APPROVED_RECEIPT_SHA256`. While the state shows the runtime, the safety net refuses any delete or replace of an ECS cluster or service, a load balancer, a listener or a target group, for base-apply and for carried rollbacks. All four services are verified after apply. A runtime-disabled rollback is unchanged. | `test_runtime_rollback.py` (51), `test_runtime_guard.py` (24) | fixed (repair-3) |
| N4 | **Default gates run the real-Terraform classes.** Gate order is now constitution, hooks, shell, python, terraform, script-tests, sbt. Discover suites run through `lib/suite_run.py`, which reports `executed = Ran − method skips` and lists class skips separately. A default full run fails if `test_terraform_state_binding.RealStateBindingTests` or `test_terraform_r1.RouteOwnershipTest` is skipped or missing; a partial run only warns. The orchestrator corrected the evidence wording above. | `test_check.CheckRequiredRealTerraformTests` (7), `SuiteRunTests` (4); real run: required classes executed 7 and 6 | fixed (repair-3) |
| N5 | **Upload checksum is computed by S3.** The post-upload `head-object --checksum-mode ENABLED` must report a `ChecksumSHA256` equal to base64 of the copy's raw sha256. For multipart objects, every part is verified through `get-object-attributes ObjectParts` and the composite checksum is recomputed. | `test_upload_checksum.py` (9), `test_runtime_guard.S3ChecksumTests` | fixed (repair-3) |

#### Approval-format fact for Phase 14 (S1)

An infrastructure rollback that keeps the runtime uses `APPROVED_STAGE=runtime-apply`, with `APPROVED_COMMIT` set to the previous (Terraform source) commit, not HEAD. This sits alongside the still-pending approval-format additions.

#### Verification scope (user decision, round 3)

The clean-snapshot `check.sh` ran with `--skip sbt`. The sbt evidence is reused from repair round 2, because all 459 Scala/build input files are byte-identical to the round-2 snapshot (`sbt-input-identity.txt`). The full seven-gate run is deferred until after reviewer approval and before the user's commit.

## Subphase 13A — repair round 4 (from review 4, REQUEST-CHANGES)

The source is the user-supplied external review 4 in `review.md`. Review 4 confirmed that N4 and N5 are closed, that S1 is closed except for T1, and that F1–F10, N1–N3 and R1–R9 stay closed. The user asked the orchestrator to fix the blocking finding and to use Opus 5.5 (effort high) for the subagent (2026-11-05).

| ID | Severity / blocking | Owner | Paths (reviewer) | Acceptance check (reviewer) | Status |
|---|---|---|---|---|---|
| T1 | P2 / yes | infra-engineer | `scripts/config/release.conf:164-165`; `scripts/lib/verify.py:576-610`; `scripts/rollback.sh` (STEP `runtime-state`); the `runtime-preservation` calls in `scripts/deploy.sh`; `infra/terraform/modules/runtime/compute.tf:6`; `infra/terraform/main.tf:97`; `scripts/tests/test_runtime_rollback.py:226` | Decide "runtime live" from resources that exist only when the runtime is deployed, such as `aws_ecs_service` instances, or `aws_lb` / `aws_lb_target_group` with `count`. Keep `aws_ecs_cluster` protected against delete or replace while the runtime is live. Add fixtures that model a realistic post-base-apply state (the ECS cluster and ECR repositories, plus non-runtime modules, with no services). Tests must show three things: the runtime-disabled infra rollback is accepted; a manifest or push-record binding is refused with "would CREATE the runtime"; a base-apply plan that keeps the cluster passes. Keep every existing S1 refusal and test. | fixed (repair-4) |
| O1 | nonblocking (disclosed, no action required) | infra-engineer | — | Nothing confirms that the revision named by `--deployed-push-record` is the one currently running. It could later be tightened with a read-only pre-apply `ecs describe-services` read during execute. | disclosed; not implemented (would need a live ECS read) |

### Repair round 4 results

Repaired by `infra-engineer` with a fresh context, model `opus` (Opus 5.5), effort `high`, at the user's request. Native ID `ae02e16d0b35969ce`. All edits are under `scripts/**`. Evidence is in `evidence/13a/repair-4/`.

Orchestrator gates for round 4:
- full seven-gate clean-snapshot `check.sh`: PASS, exit 0;
- working-tree `sbt -batch check`: exit 0.

Details are in `test-report.md`.

**T1 — fixed (repair-4).** The change has four parts:
- **New indicator key.** A new pinned key, `RUNTIME_LIVE_INDICATOR_TYPES=aws_ecs_service=4,aws_lb=1,aws_lb_target_group=1,aws_lb_listener=0-1`, lists the resources that exist only when the runtime is deployed. These types are derived from the count/for_each gating in `modules/runtime/compute.tf`.
- **Protected types kept.** `RUNTIME_LIVE_PROTECTED_TYPES` still holds the indicators plus `aws_ecs_cluster`, so the cluster stays protected while the runtime is live.
- **Three-way verdict.** `verify.py` now returns `absent`, `live` or `partial`. A partial state fails closed at `runtime-state` and in `runtime-preservation`.
- **Fixtures.** New realistic fixtures model the post-base-apply state (cluster, service-discovery namespace, four ECR repositories and non-runtime modules) and a complete live state.

Proving tests (all in `scripts/tests/`):

| Case | Tests |
|---|---|
| (a) runtime-disabled infra rollback on the post-base-apply state is accepted | `test_runtime_base_apply.RollbackOnPostBaseApplyStateTests.test_a_*` |
| (b) a manifest or push-record binding is refused with "would CREATE the runtime" | `test_b_*` in `RollbackOnPostBaseApplyStateTests`, `DeployOnPostBaseApplyStateTests` and `RuntimePreservationOnRealisticStatesTests` |
| (c) a base-apply that keeps the cluster passes | `test_c_*` |
| the cluster is still protected while the runtime is live | `RuntimePreservationOnRealisticStatesTests.test_c_a_live_runtime_still_refuses_a_cluster_delete_or_replace`; `DeployOnRealisticLiveStateTests` |
| a partial state fails closed | `test_a_partial_runtime_fails_closed` (7 shapes); `RollbackOnPartialStateTests`; `DeployOnPartialStateTests` |
| the gating is derived from the real Terraform source | `SourceDerivedClassificationTests` (7, parsing the real Terraform) |

All 51 round-3 `test_runtime_rollback` tests are unchanged and still pass. Three `test_runtime_guard` fixtures encoded the wrong assumption and were corrected:
- the default now includes the target group;
- the "7 instances" count no longer includes the cluster;
- a lone nested LB is now classed as `partial`.

Still pending human decisions:
- A2.
- The approval-format additions, including a carried rollback using `APPROVED_STAGE=runtime-apply` with `APPROVED_COMMIT=PREV`.
- The live-state location.
