# Attempt 1: partial apply failed before any cluster existed (2026-11-04)

All times are CST. The account ID is redacted. Raw outputs are in `target/phase12d-spike-live/` (git-ignored, with a sha256 manifest).

1. **11:19:45** Preflight, run by the deploy-engineer as `assumed-role/scholarchain-deployer`: exit 0. Init: exit 0.
2. **11:19:51** First spike plan: exit 1. `deployer_role_arn` was malformed: zsh expanded `$acct:role` as the `:r` modifier. The human rewrote `spike.tfvars` using `${acct}`.
3. **11:21:25** Second plan: exit 0, `Plan: 55 to add, 0 to change, 0 to destroy`, sha256 `87936de0391fff6b97cb45ac69cb0d3569271dc446b35a09b9b85db6c3208334`. The plan rule passed: create 55, update/delete/replace 0, one `aws_emr_cluster`, no default SG, and the shape matched the approval exactly.
4. **The deploy-engineer's `terraform apply` was blocked** by Claude Code's permission classifier ("Protected-Scope IaC Apply"), so it never executed. By the coordinator's guidance, the human ran the same saved plan in their own terminal.
5. **Apply failed partway:**
   - 403 `UnauthorizedOperation` on `ec2:CreateSubnet` (twice), `ec2:CreateRouteTable` and `ec2:CreateSecurityGroup` (four groups), all against the *parent* `vpc/…` resource. The deployer statement `Ec2CreateOnlyWithStackTag` requires `aws:RequestTag/scholarchain:stack`, which an existing VPC cannot satisfy. This is a deployer-policy defect, found only live.
   - `ExpiredToken` during the S3 multipart upload of the runtime tgz. Terraform did not refresh the short-lived `aws login` credentials.
   - **No EMR cluster, subnet, NAT gateway or instance was created. The single cluster attempt is unused.**
6. **Partial state:** 27 resources: VPC, IGW, EIP, KMS key and alias, EFS (file system, access point, backup policy, file-system policy), EMR security configuration, IAM roles, role policies, instance profile and attachment, the S3 bucket and its controls, and 6 small S3 objects.
7. **Destroy**, run by the human: "Destroy complete! Resources: 27 destroyed." (reported in chat).
8. **11:35:51 After-inventory**, run by the deploy-engineer, read-only: exit 0, `clean: true`, no billable resources remaining. Only the KMS key `…138bf` remains, in PendingDeletion (expected retained). `head-bucket`: 404 Not Found. `list-clusters` since 16:00Z: empty.

**Cost exposure:** about 15 minutes of one unattached EIP, a KMS key (counted at a month, at most USD 1), seconds of EFS, and a partial multipart upload that was deleted with the bucket. Well under USD 0.10 plus the KMS allowance. To be confirmed in the Billing console when data arrives.

**Next:** the infra-engineer fixes the parent-resource create permissions and documents a `credential_process` profile so Terraform refreshes credentials. That needs a short review, a human deployer re-apply in another admin window, and the human's explicit OK for retry attempt 2 within the window or timebox.
