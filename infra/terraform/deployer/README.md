# Scoped deployer role (Phase 12D Step A, authored offline)

Small Terraform root that defines one IAM role, `scholarchain-deployer`, for the **human operator** to assume (with MFA) when applying the isolated EMR spike. It is separate from, and grants nothing on, `scholarchain-billing-deployer` or budgets.

Nothing here has been planned against, or applied to, AWS. The human applies this root later, under the recorded phase gate; an agent never applies it.

## What it creates

| Resource | Purpose |
|---|---|
| `aws_iam_role.deployer` | trust: exactly `operator_principal_arn`, condition `aws:MultiFactorAuthPresent = true`; `max_session_duration = 3600` |
| `aws_iam_policy.permission_set["spike-emr--emr"]`, `--network`, `--storage`, `--iam` | the `spike-emr` permission set, split in four documents because a managed policy is limited to 6144 characters (tests assert every document stays below it) |
| `aws_iam_role_policy.login` (`scholarchain-deployer-same-device-login`) | inline policy for same-device `aws login`, always attached whatever `enabled_permission_sets` holds; see below |
| `aws_iam_policy.spike_boundary` (`scholarchain-spike-emr-boundary`) | permissions boundary that every spike IAM role must carry |
| `aws_iam_role_policy_attachment.permission_set[...]` | attaches the four documents |

Outputs: `role_arn`, `spike_permissions_boundary_arn` (pass to the spike root as `permissions_boundary_arn`), `operator_caller_policy_json` (the document the human operator needs to call `sts:AssumeRole`; nothing is attached to the operator by this root), `available_permission_sets`, `policy_names`.

## Variables

| Variable | Notes |
|---|---|
| `account_id` | 12 digits; also `allowed_account_ids` |
| `region` | validated to `us-east-2` |
| `operator_principal_arn` | validated: concrete IAM user or role ARN, same account, no wildcard, not the account root |
| `role_name` | default `scholarchain-deployer`; must match `^scholarchain-...` and must not be `scholarchain-billing-deployer` |
| `enabled_permission_sets` | default `["spike-emr"]`; an unknown name fails a lifecycle precondition on the role |
| `owner` | tag |

## Same-device login (`aws login`)

The human signs in with `aws login --profile scholarchain-deployer` (browser OAuth on the same device), which needs sign-in permissions on the role itself. `aws_iam_role_policy.login` grants exactly `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token` on `arn:aws:signin:us-east-2:<account>:oauth2/public-client/localhost`, conditioned on `signin:OAuthClientId = arn:aws:signin:::devtools/same-device`. It is separate from the permission sets (every set needs it), mirrors the already installed and reviewed billing-role login policy (`docs/agent-runs/phase-12/evidence/12d-human-identity-bootstrap/user-supplied-policy-readbacks/role-login-policy.json`), grants sign-in only (no `signin:*`, no `*` resource), and is not added to `operator_caller_policy_json`; the operator's own login is handled separately. AWS documents these two actions as the OAuth permissions in the IAM policy: https://aws.amazon.com/blogs/security/introducing-oauth-support-for-aws-mcp-server/ . The `aws login` flow itself was not run or tested here.

## Extending for Phase 14 (no restructuring)

Permission sets are entries of the map `local.permission_sets` in `permission_sets.tf`. Each entry is a map of named policy documents. To add one:

1. add `"phase14-<name>" = { <part> = local.<document>, ... }` to `local.permission_sets` and define the document locals next to it;
2. list the name in `enabled_permission_sets`.

`main.tf` flattens the selected sets with `for_each` into one managed policy plus one attachment per document. Nothing else changes. Keep each document below 6144 characters and remember a role defaults to at most 10 attached managed policies (`spike-emr` uses 4).

## The `spike-emr` set

Least privilege for creating and destroying exactly the isolated spike root's resources.

* Scoping conditions used wherever the service supports them: `aws:RequestedRegion = us-east-2` on every regional action; `aws:RequestTag/scholarchain:stack = spike-emr` on create actions; `aws:ResourceTag/scholarchain:stack = spike-emr` on modify, delete and describe-by-resource actions.
* EMR: `RunJobFlow` additionally requires the request tag `for-use-with-amazon-emr-managed-policies = true`. Describe, list, auto-termination, termination-protection, `TerminateJobFlows` are on tagged clusters only.
* IAM: only `arn:aws:iam::<account>:role|instance-profile/scholarchain-spike-emr-*`; no customer-managed policy rights at all. `iam:CreateRole` requires `iam:PermissionsBoundary` = the boundary above and the stack request tag. `PutRolePolicy`, `DeleteRolePolicy`, `DetachRolePolicy`, `AttachRolePolicy` require the target role to carry that boundary. `AttachRolePolicy` also requires `iam:PolicyARN` to equal exactly `arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2` (no list, no pattern). The spike creates no customer-managed policies, so there is no `iam:CreatePolicy`, `CreatePolicyVersion`, `DeletePolicy` or `TagPolicy` grant (a pattern grant on `policy/scholarchain-spike-emr-*` would also have matched the boundary and allowed a new boundary version). Explicit Denies: `iam:CreatePolicyVersion`, `SetDefaultPolicyVersion`, `DeletePolicy`, `DeletePolicyVersion` on the boundary; `iam:PutRolePermissionsBoundary`, `DeleteRolePermissionsBoundary`, `UpdateAssumeRolePolicy` on spike roles; `sts:AssumeRole` on spike roles. `iam:PassRole` is granted only for spike roles and only with `iam:PassedToService` in `elasticmapreduce.amazonaws.com`, `ec2.amazonaws.com`. Not granted (and denied): editing a spike role's boundary or trust, assuming a spike role.
* S3: only buckets named `scholarchain-spike-emr-*` and their objects.
* KMS: IAM grants only `kms:CreateKey` (request tag), `kms:TagResource` (request tag, for tag-on-create), aliases `alias/scholarchain-spike-emr-*`, and `kms:ListAliases`. **Key administration and use (PutKeyPolicy, ScheduleKeyDeletion, CancelKeyDeletion, rotation, DescribeKey, crypto via S3/EFS) are granted by the key policy directly to this role's ARN** (spike variable `deployer_role_arn`), not through IAM tag conditions. `kms:TagResource` is deliberately broad on `key/*` because the API requires it in IAM to tag at creation (https://docs.aws.amazon.com/kms/latest/developerguide/customer-managed-policies.html); nothing here keys off a KMS tag, so tagging a foreign key gains nothing.
* Tags apply at creation only (no tag-laundering): `ec2:CreateTags` and `elasticfilesystem:TagResource` require the `CreateAction` condition plus the stack request tag, so a standalone tagging call cannot bring an existing resource into scope; EMR `AddTags` requires the cluster to already carry the stack tag (AWS's own tag-based example uses the same shape, https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-fine-grained-cluster-access.html), `RunJobFlow` carries its tags itself, so `TerminateJobFlows` cannot reach a foreign cluster. No untag action is granted. Residual: if EMR's internal authorization of `AddTags` during `RunJobFlow` is evaluated against the not-yet-tagged new cluster, `RunJobFlow` would be denied at the first real plan/apply; that cannot be checked offline.
* Read-only inventory: `tag:GetResources`. `sts:GetCallerIdentity` needs no permission and is not granted.

### Actions that cannot be resource-scoped (the honest list)

Each of the nine non-EC2-Describe actions sits in its own single-action statement with `aws:RequestedRegion = us-east-2`. The EFS describe actions are scoped to `file-system/*` and `access-point/*` in the region and account; if the inventory's list-all call is denied by that scope the inventory exits 3 (inconclusive) rather than passing.

Sources (Service Authorization Reference): https://docs.aws.amazon.com/service-authorization/latest/reference/list_emr.html , https://docs.aws.amazon.com/service-authorization/latest/reference/list_kms.html , https://docs.aws.amazon.com/service-authorization/latest/reference/list_resourcegroupstaggingapi.html , https://docs.aws.amazon.com/service-authorization/latest/reference/list_efs.html .

| Action(s) | Why |
|---|---|
| `ec2:Describe*` (21 listed in the `network` document) | describe actions have no resource-level scoping |
| `tag:GetResources` | no resource type (list_resourcegroupstaggingapi) |
| `elasticmapreduce:ListClusters`, `ListSecurityConfigurations`, `DescribeSecurityConfiguration`, `CreateSecurityConfiguration`, `DeleteSecurityConfiguration`, `RunJobFlow` | no resource type in the Service Authorization Reference (list_emr); RunJobFlow is scoped by request tags |
| `kms:CreateKey`, `kms:ListAliases` | no resource type (list_kms); CreateKey is scoped by request tags |
| `ec2:CreateNetworkInterface`, `DeleteNetworkInterface`, `ModifyNetworkInterfaceAttribute` on `network-interface/*` | the EFS mount-target call creates an untagged ENI with the caller's permissions; subnet and security group are tag-scoped, the ENI is not |
| `iam:CreateServiceLinkedRole` for `AWSServiceRoleForEMRCleanup` and `AWSServiceRoleForAmazonElasticFileSystem` | service-linked roles live under `role/aws-service-role/`, not the spike prefix; limited to those two ARNs and `iam:AWSServiceName` |

S3 has no tag condition used here; bucket scoping is the name prefix plus region.

### Spike boundary

`scholarchain-spike-emr-boundary` allows only what the two spike roles may ever use: the EC2 actions of `AmazonEMRServicePolicy_v2`, mirrored statement by statement with its tag conditions (https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html): actions on existing resources (terminate, modify, delete, security-group authorize/revoke, launching into a subnet or security group) require `aws:ResourceTag/for-use-with-amazon-emr-managed-policies = true`, and for subnets, security groups and the VPC also `aws:ResourceTag/scholarchain:stack = spike-emr` (Terraform tags them at creation through provider `default_tags`); creating instances, volumes, network interfaces, launch templates and security groups requires `aws:RequestTag/for-use-with-amazon-emr-managed-policies = true`; `ec2:CreateTags` only with `ec2:CreateAction`; `ec2:Describe*` on `*`. v2's VPC-endpoint, placement-group and launch-template-version statements are left out because this cluster does not use them (if EMR turns out to need one, the launch fails closed and a human decides). The intersection with v2 means node code on a spike role cannot open a foreign security group, terminate a foreign instance or launch into a foreign subnet, S3 `GetObject`/`PutObject`/`AbortMultipartUpload`/`ListBucket` on spike buckets, KMS data-key and grant actions on keys aliased `alias/scholarchain-spike-emr-key` (alias, not tag), EMR `Get/Put/RemoveAutoTerminationPolicy` on stack-tagged clusters (the idle timeout does not work without them on the instance profile: https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination), EFS `ClientMount`/`ClientWrite`, and `iam:PassRole` of spike roles to EC2. The boundary does not include `iam:*`, STS, budgets or other services, so even a mistaken inline policy on a spike role cannot reach them. Policy size: the boundary is 5672 characters of the 6144 limit, so any further statement needs merging.

## Tests

All mock-only (`mock_provider "aws"`); no AWS call is possible.

```
export TF_CLI_CONFIG_FILE=<offline mirror tfrc>   # hashicorp/aws 6.44.0 only
export TF_DATA_DIR=<scratch dir>                   # keeps .terraform out of the source tree
terraform -chdir=infra/terraform/deployer init -backend=false
terraform -chdir=infra/terraform/deployer fmt -check -recursive
terraform -chdir=infra/terraform/deployer validate
terraform -chdir=infra/terraform/deployer test
```

They assert: MFA and exact-principal trust; four policies each under the managed-policy size limit; no wildcard or prefix-wildcard action; region condition on regional statements; IAM statements only on the spike prefix; PassRole, boundary and attach conditions; nothing for budgets, Organizations, Cost Explorer or the billing deployer; unknown permission set, wildcard or foreign operator, wrong region, billing role name and bad account id all fail.

## Limits of this authoring

* Policies were written from the provider's behaviour and AWS documentation, not from a recorded run. A real `terraform plan`/`apply` may reveal an additional read action; add it to the matching document and re-run the tests (never widen to `Service:*`).
* `.terraform.lock.hcl` pins `hashicorp/aws 6.44.0` with the `h1:` hash of the offline mirror's darwin_arm64 build only. Another platform needs `terraform providers lock` against the same version.
* Applying this root needs a principal that can create IAM roles and policies; that principal is the human architect, not this role.
