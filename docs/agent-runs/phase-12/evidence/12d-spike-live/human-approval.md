# Phase 12D live spike — human approval record


## Spend

- **Cap:** USD 10 hard, a suballocation of the shared USD 200 project budget. No extra funds and no reliance on credits.
- **Billing check:** budget `scholarchain-project-budget` showed USD 0.00 of USD 200 spent, health "Healthy", 1/1 alert email verified, observed at about 2026-11-04 11:00 CST. AWS budget and billing data can lag by up to about a day.
- **Conservative remaining allowance:** about USD 200 (the budget showed USD 0.00 spent). This covers the USD 10 cap.
- **Modeled cost** (`../12d-spike-offline/cost-replay.json`): USD 4.13 nominal. USD 5.50 if ancillary resources stay up 24 h, USD 8.64 if 72 h.
- **Leftover cost if destroy is missed:** USD 1.57 per day (NAT gateway 1.08, public IPv4 0.12, EFS 0.05, S3 under 0.01, before tax).

## Approved shape (Terraform root `infra/terraform/spikes/emr-spark-isolated`, commit `f6ee322`)

- Region us-east-2, availability zone us-east-2a.
- EMR release emr-7.8.0, Hadoop only, with the custom Spark 3.5.4 / Scala 2.13.14 runtime.
- 1 primary + 1 core node, both m5.xlarge. No task nodes, no Spot, no instance fleets, no scaling.
- Four gp3 volumes of 32 GiB each (128 GiB total).
- **Exactly one cluster attempt.** No retry. If it fails, report the plan's 12D fallback options. EMR Serverless (candidate b) is unavailable by the human's decision.
- **Maximum cluster lifetime 120 minutes.** Idle auto-termination at 900 s. Step timeouts: probe 20 min, G1 50 min, collect 10 min.

## Run window

- Date: 2026-11-04. Start 11:20 CST, end 15:20 CST, at most 4 h. The human changed this in chat at 11:18 CST; it was originally 11:45–15:45. including destroy and inventory.
- Timebox: if no runtime is proven on AWS by 2026-11-06, stop and report the fallback options.

## Actions authorized (deploy-engineer, identity `scholarchain-deployer` via MFA role switch and `aws login`)

1. Run the preflight. It must print `assumed-role/scholarchain-deployer` with exit 0.
2. Real `terraform plan` of the spike root, using variables and state kept outside the repository.
3. **Plan rule:** apply only if the plan shows only creates, 0 to change and 0 to destroy, with the expected resource set, and the `shape` output matches the approved shape above. Otherwise stop and report.
4. `terraform apply` of that saved plan. The cluster runs the probe, G1 and collect steps defined in the cluster resource.
5. Bounded status polling, at most 130 checks one minute apart.
6. Download EMR logs and job outputs to `docs/agent-runs/phase-12/evidence/12d-spike-live/` with SHA-256 manifests, then compare locally against the Phase 6 G1 baseline.
7. **`terraform destroy` in the same session**, including deleting the S3 bucket (`force_destroy`) after the local copy is verified.
8. After-destroy inventory (`scripts/phase12d-spike/inventory.sh`).

Not authorized: any second cluster, a changed shape, region or instance type, Docker or EMR Serverless, or keeping resources beyond the window.

## Teardown and retention

- Everything is destroyed the same day. The KMS key stays in PendingDeletion for 7 days (counted as one month, at most about USD 1). Nothing else is retained in AWS.
- The `scholarchain-deployer` role and its policies stay; they are IAM only and cost nothing. Before Phase 14 or any other EMR cluster in us-east-2, the boundary's EMR-tagged instance reach must be closed (carried item 17).

## Accepted residual risks

- Hadoop/YARN RPC is unencrypted inside the single private subnet; there is no in-transit TLS. Spark uses authentication plus AES-CTR (`authEngineVersion` 1).
- The node shutdown timer is best-effort. The guarantees are steps-then-terminate, TERMINATE_CLUSTER on collect, the 900 s idle timeout and the same-session destroy.
- The launch may fail closed on a permissions gap: `AddTags` during `RunJobFlow`, the boundary being tighter than the EMR v2 policy, or KMS alias evaluation. That spends the one attempt.
- The inventory may return "inconclusive" (exit 3) because the EFS describe actions are ARN-scoped.

## Manual IAM exception (outside Terraform, documented)

- **Root:** used once, in the console only, to attach the AWS-managed `IAMFullAccess` to `scholarchain-billing-operator` at about 2026-11-04 10:45 CST (human's estimate, given in chat). No root access keys exist or were created.
- **As the operator, during the window:**
  - added the inline policy `scholarchain-operator-cli-login` (same-device `aws login`);
  - applied `infra/terraform/deployer` (11 resources, plan sha256 `c823637800eb9e7b2f36d76760efd328b17ced6388e32ef3faae8aa56bd6ba58`);
  - added the inline policy `scholarchain-assume-deployer` (`sts:AssumeRole` on `scholarchain-deployer` with MFA). This one is retained.
- **Window closed:** `IAMFullAccess` and `scholarchain-operator-cli-login` were removed by the operator at about 2026-11-04 11:07 CST (17:07 UTC), the time reported in chat. Confirm in CloudTrail.

## Confirmation

Approved - Danny Nguyen, 2026-11-04 11:16 CST

(The human gave the approval wording and all values in chat. The coordinator transcribed them into this file at the human's request.)

## Amendment 1 (2026-11-04 12:36 CST)

The human gave all of the following in chat; the coordinator transcribed it.

- **Attempt 1** failed before any EMR cluster existed: an IAM parent-resource gap plus a credential refresh failure. Its 27 partial resources were destroyed, and the read-only inventory was clean. See `attempt1-partial-apply.md`.
- **Second manual IAM window:** `IAMFullAccess` and `scholarchain-operator-cli-login` were added again to `scholarchain-billing-operator`, root again used only in the console. The reviewed deployer fix (commit `7963b87`) was applied: plan `0 to add, 2 to change, 0 to destroy`, sha256 `2c59e40e7c3973203622864c17284bba8d489f892bf9fd31d90e73450a353037`, updating only `permission_set["spike-emr--network"]` and `["spike-emr--storage"]`. Both policies were removed again. The window closed at about 12:35 CST, the time reported in chat.
- **Approved: retry attempt 2,** with the same shape, cap, single cluster, teardown and accepted risks as above, finishing by 15:20 CST. The human runs the Terraform apply and destroy commands in their own terminal, because Claude Code's permission classifier blocks the agent from running them. The deploy-engineer plans, checks the plan rule, monitors, collects, compares and inventories. Terraform uses the `scholarchain-deployer-tf` credential_process profile.

Approved attempt 2 - Danny Nguyen (chat answer "Approve attempt 2", 2026-11-04 12:36 CST)

## Amendment 2 (2026-11-04 13:56 CST)

The human gave all of the following in chat; the coordinator transcribed it.

- **Attempt 2:** the EMR cluster failed validation. CloudTrail showed the boundary denying `ec2:RunInstances` on the AMI, and no instance was launched. Everything was destroyed and the inventory was clean. See `attempt2-validation-failure.md`.
- **Third manual IAM window:** `IAMFullAccess` and `scholarchain-operator-cli-login` were added again; root was used only in the console. Root was also used separately, read-only, to view CloudTrail Event history. The reviewed boundary fix (commit `35e868a`) was applied, updating only `aws_iam_policy.spike_boundary[0]` and `permission_set["spike-emr--network"]` ("0 added, 2 changed, 0 destroyed"). Both policies were removed again; the human reported "removed" at about 13:56 CST.
- **Approved: attempt 3, starting now,** with the same shape, cap, single cluster, teardown and accepted risks, and the same division of work as Amendment 1. It must finish, including destroy, by 15:20 CST. If it can't finish in time, destroy anyway.

Approved attempt 3 - Danny Nguyen (chat answer "removed, start the attempt 3 now", 2026-11-04 13:56 CST)

## Amendment 3 (2026-11-04 14:12 CST)

The human gave all of the following in chat; the coordinator transcribed it.

- **Attempt 3:** both instances launched (the IAM fix was proven live). The bootstrap exited with code 4: the hard-coded Java path is absent on EMR 7.8.0. Everything was destroyed in two passes, and the inventory was clean. See `attempt3-bootstrap-java-path.md`.
- **Approved: attempt 4 today**, after a reviewed Java-detection fix limited to the spike root and its scripts, with no deployer or IAM change. It keeps the same shape, cap, single cluster, teardown, accepted risks and division of work as Amendments 1 and 2.
- **Run window:** from now until 17:30 CST. This is the coordinator's proposed end time, which the human approved in chat ("I approve that new windows so don't worry"). The destroy must complete inside the window. If the run can't finish, destroy anyway.

Approved attempt 4 - Danny Nguyen (chat, 2026-11-04 14:12 CST)

## Amendment 4 (2026-11-04, about 14:55 CST)

The human gave all of the following in chat; the coordinator transcribed it.

- **Attempt 4:** the Scala 2.13 runtime is proven on EMR, on the driver and executors. The G1 step failed on EMR's LZO entry in `io.compression.codecs`. Everything was destroyed in two passes and the inventory was clean. See `attempt4-runtime-proven-g1-codec.md`.
- **Approved: attempt 5 today**, after a reviewed fix that sets `spark.hadoop.io.compression.codecs` without the LZO codecs. The fix is limited to the spike root and its scripts, with no IAM change. Shape, cap, single cluster, teardown, accepted risks and the division of work are the same as before.
- **Run window:** unchanged, until 17:30 CST. The destroy must finish within the window.

Approved attempt 5 - Danny Nguyen (chat answer "Yes, attempt 5 today", 2026-11-04)
