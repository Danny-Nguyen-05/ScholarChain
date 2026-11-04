# Attempt 2: EMR cluster failed validation (2026-11-04)

Authority: human-approval.md Amendment 1 (12:36 CST). All times are CST. The account ID is redacted. Raw outputs are in `target/phase12d-spike-live/` (git-ignored, sha256 manifest of 31 files).

1. **12:39:09 Preflight** (deploy-engineer, `scholarchain-deployer-tf` credential_process profile): exit 0. `state list` was empty.
2. **12:39:21 Plan**: `55 to add, 0 to change, 0 to destroy`, sha256 `2cc08f54ecf9003ae2c396b84cf20dc8495bcb53044a39c467448932baef2483`. The plan rule passed: the same 55 addresses as attempt 1, one cluster, no default security group, and the shape equal to the approval.
3. **Apply, run by the human in their own terminal:**
   - The VPC, NAT gateway, EFS, S3 staging (including the 321 MB runtime upload, with credential refresh working) and IAM were all created.
   - The EMR cluster `j-…W0WN0HLBZ4UC` was created at 12:50:52 and ended at 12:52:35, after 1 min 43 s.
   - Final state: `TERMINATED_WITH_ERRORS` with `VALIDATION_ERROR: Service role …/scholarchain-spike-emr-service has insufficient EC2 permissions`. There is no ReadyDateTime, `NormalizedInstanceHours` is 0, and `list-instances` is empty, so **no EC2 instance was launched**.
   - Terraform's waiter then failed with "unexpected state 'TERMINATING'". As instructed, the human did not re-run the apply.
4. **The single cluster attempt and the Amendment 1 retry are both spent.**
5. **Destroy, run by the human:**
   - The first run removed everything except `aws_eip.nat`, which failed with a 403 on `ec2:DisassociateAddress`. The deployer lacks it; the association was to the now-deleted NAT gateway.
   - A second run: "Destroy complete! Resources: 1 destroyed."
   - Carried defect: grant `ec2:DisassociateAddress` on stack-tagged EIPs, or set the EIP so destroy does not need it.
6. **12:57 After-inventory** (deploy-engineer, read-only):
   - `inventory.sh` exit 0, `clean: true`, no billable resources remaining.
   - Expected-retained: 2 KMS keys in PendingDeletion (attempts 1 and 2).
   - Tagging-API residue: 13 security-group-rule ARNs and 1 vpc-endpoint ARN, with a deleted NAT gateway still visible. The direct describes return none of them (no VPCs, endpoints, rules or EIPs), which is consistent with tagging-API lag.
   - Bucket: 404. No active clusters.
7. **Cause:** not yet identified at the action level. EMR's message is generic. The deployer role cannot read CloudTrail; the human can read it in the console. The leading hypothesis is the permission boundary's EC2 ceiling. Repair R1 made it deliberately tighter than `AmazonEMRServicePolicy_v2` (request tags on image, key-pair and other launch dependencies; no `CreateLaunchTemplateVersion` or placement groups). EMR's pre-launch validation probably exercises one of these.

**Cost exposure:** about 2 minutes of EMR with no instances (billed by instance-hour, so expected zero), the NAT gateway and EIP for roughly 15 to 25 minutes, minutes of EFS, the S3 upload and requests, and the KMS key allowance. The estimate is under USD 0.20 plus up to USD 2 for the two KMS keys. To be confirmed in Billing when data arrives.

**The runtime question (Scala 2.13 on EMR driver and executors) remains unanswered.** No node ever started.

## Root cause, identified from CloudTrail (read by the human in the root console, read-only)

The EMR service-role session `scholarchain-spike-emr-service/CCSSession` (invokedBy `elasticmapreduce.amazonaws.com`) called `ec2:RunInstances` five times between 12:51:00 and 12:51:30 CST. The 12:51:30 event shows:

- `errorCode`: `Client.UnauthorizedOperation`
- the call was not authorized on resource `arn:aws:ec2:us-east-2::image/ami-…` "because no permissions boundary allows the ec2:RunInstances action".

The request carried TagSpecifications for instance, network-interface and volume, including `for-use-with-amazon-emr-managed-policies=true` and `scholarchain:stack=spike-emr`. It had two gp3 32 GiB volumes encrypted with the spike CMK, a private ENI in the stack subnet and SG, and the spike instance profile.

The boundary statement `V2CreateNewWithEmrRequestTag` conditioned the existing AMI on `aws:RequestTag`, which never applies to an existing resource. `AmazonEMRServicePolicy_v2` allows launch AMIs without that condition. The repair is routed to the infra-engineer.
