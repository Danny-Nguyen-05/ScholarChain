# Read-only account pre-flight

Observed 2026-10-30 through the explicitly authorized named profile. These are read/control-plane observations, not apply, paid-model or service-composition tests.

| Check | Observed result | Evidence |
|---|---|---|
| Initial identity | Session expired, exit 255; user refreshed it interactively | account-identity.log.txt |
| Refreshed identity | Account 530332961125; IAM user scholarchain-planner, not root | account-identity-refreshed.log.txt |
| Account plan | PAID, ACTIVE | account-plan-type.log.txt |
| Ohio AZs | us-east-2a/use2-az1 and us-east-2b/use2-az2 available, opt-in not required | availability-zones.log.txt |
| Neptune | db.serverless orderable options returned; no engine/family selected or cluster created | neptune-serverless-options.log.txt |
| Titan V2 | amazon.titan-embed-text-v2:0 catalog status ACTIVE, ON_DEMAND | bedrock-titan-catalog.log.txt |
| EMR | Region returns release catalog; no compatible runtime selected or cluster created | emr-release-catalog.log.txt |
| Planner managed policies | ReadOnlyAccess, IAMUserChangePassword, SignInLocalDevelopmentAccess | planner-attached-policy-names.log.txt |
| Regional quotas | VPC 5; NAT per-AZ 5; EC2-VPC EIP 5; Fargate On-Demand 6 vCPU | respective *-quota.log.txt |
| Budget inventory | Zero budgets returned | existing-budget-inventory-corrected.log.txt |

The first budget-inventory query failed locally because AWS omitted the empty array and length(null) is invalid. Its retained failure is not a pass; the corrected query explicitly coalesces an omitted array to [] and returns count zero. No permission or cloud state was changed to repair this query.

Quota values alone do not prove complete headroom or deployment success. Recheck usage at deployment, and verify all service-specific limits before activation. S3 Vectors regional support is documented; live index/KMS behavior remains unverified. Catalog presence does not prove model invocation rights, EMR Spark/Scala compatibility or Neptune live behavior. Actual deployment identities remain separate from the planner.

Pre-spend monitoring is OPEN: no budget exists, Cost Explorer activation is unverified, and no paid Cost Explorer query was run. Primary plan retains budget-resource activation false; the small separate billing bootstrap and private subscriber input need their own approved work order before any paid run. This does not block the authorized read-only primary plan. No root operation, credential inspection, AWS write, apply/destroy/import or paid model call occurred.

Exact argument arrays, cwd, timestamps, exits and SHA-256 values are in coordinator-commands.jsonl. Logs contain only selected metadata; no email, password, token, key or credential cache was inspected.
