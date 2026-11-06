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
| `spike_kms_tag_keys` | carried item 14: the only tag keys `kms:TagResource` may apply (default: the spike root's eight keys); must include `scholarchain:stack`, no wildcard |
| `spike_role_names` | carried item 16: exactly the two role names `iam:CreateRole` may create (default `scholarchain-spike-emr-service` and `-instance`) |

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

### Create and attach calls: actions, resources authorized, condition

A create or attach call is authorized against every resource type the Service Authorization Reference lists for it, not only the new resource. A request tag applies to the resource being created; **existing parents are matched on their resource tag.** A live run failed with AccessDenied on `ec2:CreateSubnet`, `CreateRouteTable` and `CreateSecurityGroup` on the VPC because only the request-tag statement existed. Sources: https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html and https://docs.aws.amazon.com/service-authorization/latest/reference/list_efs.html . All rows add `aws:RequestedRegion = us-east-2`; "stack" is `scholarchain:stack = spike-emr`.

| Action | Resources it is authorized against | Condition |
|---|---|---|
| `ec2:CreateVpc` | new `vpc` | request tag stack |
| `ec2:CreateSubnet` | new `subnet`; existing `vpc` | request tag stack; resource tag stack |
| `ec2:CreateInternetGateway`, `ec2:AllocateAddress` | new `internet-gateway`, `elastic-ip` | request tag stack |
| `ec2:CreateRouteTable` | new `route-table`; existing `vpc` | request tag stack; resource tag stack |
| `ec2:CreateSecurityGroup` | new `security-group`; existing `vpc` | request tag stack; resource tag stack |
| `ec2:CreateNatGateway` | new `natgateway`; existing `subnet`, `elastic-ip` (and `vpc`) | request tag stack; resource tag stack |
| `ec2:CreateVpcEndpoint` | new `vpc-endpoint`; existing `vpc`, `route-table` | request tag stack; resource tag stack |
| `ec2:AttachInternetGateway` | existing `internet-gateway`, `vpc` | resource tag stack |
| `ec2:AssociateRouteTable`, `CreateRoute`, `DeleteRoute` | existing `route-table` (and `subnet`) | resource tag stack |
| `ec2:AuthorizeSecurityGroupIngress/Egress` | existing `security-group`; new `security-group-rule` (only when the request carries tags) | resource tag stack; request tag stack |
| `ec2:ModifyVpcAttribute`, `DeleteVpc`, `DeleteSubnet`, `DeleteNatGateway`, `ReleaseAddress`, `DeleteVpcEndpoints`, `Revoke*` | the existing resource named | resource tag stack |
| `ec2:DisassociateAddress` | `elastic-ip` (the reference lists `elastic-ip`, `network-interface` and `instance` as optional types and no association type) | resource tag stack |
| `ec2:CreateTags` | the resource being created, as part of a create call | `ec2:CreateAction` in the create actions, plus request tag stack (never post-hoc) |
| `ec2:CreateNetworkInterface` (EFS mount target) | existing `subnet`, `security-group`; the new ENI | resource tag stack; ENI region-only (see above) |
| `elasticfilesystem:CreateFileSystem` | new `file-system` | request tag stack (CreateAccessPoint is not in this statement) |
| `elasticfilesystem:CreateAccessPoint` | the existing `file-system` only (the reference lists no separate access-point resource for this action) | resource tag stack **and** request tag stack, both required: the resource tag keeps it off foreign file systems, the request tag keeps the access point from being created untagged (https://docs.aws.amazon.com/efs/latest/APIReference/API_CreateAccessPoint.html) |
| `elasticfilesystem:CreateMountTarget` and the other file-system actions | existing `file-system` | resource tag stack |
| `elasticfilesystem:TagResource` | the resource being created | `elasticfilesystem:CreateAction` plus request tag stack |

The statement for the existing parents (`Ec2CreateOnExistingStackParents`) is resource-tag-only and names no wildcard resource; a new resource has no tag yet, so it cannot authorize a create. The mock test `every_spike_create_and_attach_call_is_allowed_on_its_existing_parents` checks each row against the rendered policy. Policy sizes: emr 2574, iam 3314, network 4569, storage 5202, boundary 5559 characters (limit 6144).

### Spike boundary

`scholarchain-spike-emr-boundary` allows only what the two spike roles may ever use: the EC2 actions of `AmazonEMRServicePolicy_v2`, mirrored statement by statement with its tag conditions (https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html): actions on existing resources (terminate, modify, delete, security-group authorize/revoke, launching into a subnet or security group) require `aws:ResourceTag/for-use-with-amazon-emr-managed-policies = true`, and for subnets, security groups and the VPC also `aws:ResourceTag/scholarchain:stack = spike-emr` (Terraform tags them at creation through provider `default_tags`); creating NEW instances, volumes, network interfaces and security groups requires `aws:RequestTag/for-use-with-amazon-emr-managed-policies = true`; EXISTING launch dependencies (the AMI `arn:aws:ec2:us-east-2::image/ami-*`, key pairs, capacity reservations, dedicated hosts, fleets, `placement-group/EMR_*`) are allowed for `ec2:RunInstances`/`CreateFleet` on the region condition alone, exactly as v2's `ResourcesToLaunchEC2` does, because a request tag never applies to an existing resource (live attempt 2: the boundary denied RunInstances on an AMI ARN). This does not widen reach: launching still requires the stack-tagged subnet and security group and EMR-tagged new instances, volumes and ENIs, so an AMI or key-pair grant alone launches nothing; `ec2:CreateTags` only with `ec2:CreateAction`; `ec2:Describe*` on `*`. v2's VPC-endpoint, launch-template and resource-group statements are left out because the observed launch uses none of them (if EMR turns out to need one, the launch fails closed and a human decides). The intersection with v2 means node code on a spike role (as of carried item 17, closed in Phase 13C) cannot authorize or revoke rules on a security group that lacks the stack and EMR tags, cannot terminate, modify, untag or delete the ENI of any instance or network interface that lacks the stack tag (the EMR managed-policies tag alone, which every EMR cluster in the account carries, no longer suffices), and cannot launch into a subnet, security group or VPC that lacks the stack tag. What it does NOT guarantee: creating a NEW security group needs only the EMR request tag on the new group plus the stack-tagged VPC (V2UseTaggedNetwork), so the stack tag is not required on the group being created; launching still allows any AMI and instance type into the tagged subnet (carried item 25); and a spike role can still use S3 and KMS only as listed next, S3 `GetObject`/`PutObject`/`AbortMultipartUpload`/`ListBucket` on spike buckets, KMS data-key and grant actions on keys aliased `alias/scholarchain-spike-emr-key` (alias, not tag; EC2 calls KMS as the caller for the encrypted volumes, and the reference lists `kms:ResourceAliases` for CreateGrant, GenerateDataKey(WithoutPlaintext), Decrypt, Encrypt, ReEncrypt, ListGrants and RevokeGrant; the key ARN is not known when the deployer root is applied, so a variable ARN is not possible; `kms:DescribeKey` is additionally allowed via `kms:ViaService = ec2.us-east-2.amazonaws.com` because its row was not read, and it is read-only metadata), EMR `Get/Put/RemoveAutoTerminationPolicy` on stack-tagged clusters (the idle timeout does not work without them on the instance profile: https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination), EFS `ClientMount`/`ClientWrite`, and `iam:PassRole` of spike roles to EC2. The boundary does not include `iam:*`, STS, budgets or other services, so even a mistaken inline policy on a spike role cannot reach them. Policy size: the boundary is 5559 characters of the 6144 limit, so any further statement needs merging.

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

## Phase 13C: carried items 2, 14, 16, 17 and 18

* **Item 17 (closed).** `V2ManageTaggedInstancesAndEnis` (`ec2:TerminateInstances`, `ModifyInstanceAttribute`, `DeleteNetworkInterface`) and `V2DeleteTagsOnEmrTaggedResources` now require `aws:ResourceTag/scholarchain:stack = spike-emr` in addition to the EMR managed-policies tag and the region. v2's launch-template statements stay out of the boundary; `item_17_boundary_instance_and_eni_mutations_require_the_stack_tag` fails if any boundary statement that can act on an existing instance, network interface or launch template lacks the stack tag. The stack tag reaches the spike's instances through the cluster tags (provider `default_tags`) and the RunInstances tag specifications (live attempt 2 showed instance, volume and network-interface carry both tags). Not verified live: the ENI that EMR creates in the private subnet for service access.
* **Item 2.** `ec2:DeleteNetworkInterface` and `ec2:ModifyNetworkInterfaceAttribute` are allowed only on `network-interface/*` (and, in the boundary, `instance/*`) ARNs of us-east-2 and this account with `aws:RequestedRegion = us-east-2`. The code already had both at the Phase 13C base; the 13C test `item_2_eni_delete_and_modify_are_scoped_to_the_region_and_account` pins them (it also rejects a vacuous pass). The ENI created by the EFS mount-target call stays tag-unscopable (disclosed above).
* **Item 14.** `kms:TagResource` stays in IAM only because `kms:CreateKey` needs it to carry its tags (and `kms:CreateKey` has no resource type, so its request-tag condition is its only scope; creating the key untagged would mean dropping that condition). It now also requires `ForAllValues:StringEquals aws:TagKeys` to be the eight keys of `spike_kms_tag_keys`. Residual: the deployer can still set those keys on a foreign key; nothing in this root keys off a KMS tag (key administration and use come from the key policy, the boundary uses `kms:ResourceAliases`).
* **Item 16.** IAM has no condition key that inspects a role's trust policy document (I found none in the documentation; verify before relying on this), so a trust policy naming another principal cannot be refused by IAM conditions. Controls kept or added: `iam:CreateRole` is limited to the two exact spike role ARNs (`spike_role_names`) instead of the prefix; it requires the boundary and the stack request tag; `iam:UpdateAssumeRolePolicy`, `PutRolePermissionsBoundary` and `DeleteRolePermissionsBoundary` stay denied; the deployer cannot assume a spike role; and with item 17 closed a role given a foreign trust policy is bounded to stack-tagged EMR/EC2 resources, the spike bucket and the spike key alias. The spike root's own trust policies are asserted to name only the EMR and EC2 service principals (`item_16_the_spike_roles_trust_only_the_emr_and_ec2_service_principals`).
* **Item 18.** The boundary paragraph above no longer claims that node code cannot terminate a foreign instance or that creating a security group needs the stack tag.
* Policy sizes after these changes are asserted below 6144 characters by the existing size tests.
