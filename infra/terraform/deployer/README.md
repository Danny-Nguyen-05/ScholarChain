# Scoped deployer role (Phase 12D Step A, authored offline; `phase14-main` added in Phase 14A)

Small Terraform root that defines one IAM role, `scholarchain-deployer`, for the **human operator** to assume (with MFA, one-hour session). It has two permission sets in code: `spike-emr` (the isolated EMR spike, now destroyed, kept in code but **no longer enabled by default**) and `phase14-main` (the main root with the runtime, Neptune and EMR enabled, enabled by default since decision 14-6). It is separate from, and grants nothing on, `scholarchain-billing-deployer` or budgets.

Nothing here has been planned against, or applied to, AWS. The human applies this root under the recorded phase gate; an agent never applies it. Every statement below about AWS behavior is from AWS documentation and the provider's code paths, not from a recorded run.

## What it creates

| Resource | Purpose |
|---|---|
| `aws_iam_role.deployer` | trust: exactly `operator_principal_arn`, condition `aws:MultiFactorAuthPresent = true`; `max_session_duration = 3600` |
| `aws_iam_policy.permission_set["phase14-main--<part>"]` (seven parts: `network`, `network-mod`, `data`, `keys-obs`, `compute`, `emr-efs`, `iam`) | the `phase14-main` permission set (default), split in seven documents because a managed policy is limited to 6144 characters (tests assert every document stays below it). `spike-emr` is `--emr`, `--network`, `--storage`, `--iam` when selected |
| `aws_iam_policy.main_boundary_runtime` (`scholarchain-<env>-permissions-boundary`), `main_boundary_emr` (`scholarchain-<env>-emr-service-boundary`) | the two permissions boundaries the main root's roles must carry (phase14-main only); see "Finding: the main root's roles carry no boundary" |
| `aws_iam_role_policy.login` (`scholarchain-deployer-same-device-login`) | inline policy for same-device `aws login`, always attached whatever `enabled_permission_sets` holds; see below |
| `aws_iam_policy.spike_boundary` (`scholarchain-spike-emr-boundary`) | permissions boundary that every spike IAM role must carry (spike-emr only) |
| `aws_iam_role_policy_attachment.permission_set[...]` | attaches the selected documents (seven for phase14-main) |

Outputs: `role_arn`, `main_permissions_boundary_arns` (the two boundary ARNs the main root's roles must carry), `spike_permissions_boundary_arn` (pass to the spike root as `permissions_boundary_arn`), `operator_caller_policy_json` (the document the human operator needs to call `sts:AssumeRole`; nothing is attached to the operator by this root), `available_permission_sets`, `policy_names`.

## Variables

| Variable | Notes |
|---|---|
| `account_id` | 12 digits; also `allowed_account_ids` |
| `region` | validated to `us-east-2` |
| `operator_principal_arn` | validated: concrete IAM user or role ARN, same account, no wildcard, not the account root |
| `role_name` | default `scholarchain-deployer`; must match `^scholarchain-...` and must not be `scholarchain-billing-deployer` |
| `enabled_permission_sets` | default `["phase14-main"]`; an unknown name, `spike-emr` together with `phase14-main`, or more than 10 managed attachments fails a lifecycle precondition on the role |
| `main_environment` | default `course` (the main root's `environment`); names every phase14-main ARN (`scholarchain-<environment>-...`) and tag condition; same validation as the main root |
| `main_emr_stack_tag_value` | default `main-emr` (the main root's `emr_config.stack_tag_value`); `RunJobFlow` requires this request tag |
| `main_tag_keys` | the twelve tag keys the one statement that cannot key off an existing tag may apply (`kms:TagResource` at key creation); must contain `project` and `environment`, no wildcard |
| `owner` | tag |
| `spike_kms_tag_keys` | carried item 14: the only tag keys `kms:TagResource` may apply (default: the spike root's eight keys); must include `scholarchain:stack`, no wildcard |
| `spike_role_names` | carried item 16: exactly the two role names `iam:CreateRole` may create (default `scholarchain-spike-emr-service` and `-instance`) |

## Same-device login (`aws login`)

The human signs in with `aws login --profile scholarchain-deployer` (browser OAuth on the same device), which needs sign-in permissions on the role itself. `aws_iam_role_policy.login` grants exactly `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token` on `arn:aws:signin:us-east-2:<account>:oauth2/public-client/localhost`, conditioned on `signin:OAuthClientId = arn:aws:signin:::devtools/same-device`. It is separate from the permission sets (every set needs it), mirrors the already installed and reviewed billing-role login policy (`docs/agent-runs/phase-12/evidence/12d-human-identity-bootstrap/user-supplied-policy-readbacks/role-login-policy.json`), grants sign-in only (no `signin:*`, no `*` resource), and is not added to `operator_caller_policy_json`; the operator's own login is handled separately. AWS documents these two actions as the OAuth permissions in the IAM policy: https://aws.amazon.com/blogs/security/introducing-oauth-support-for-aws-mcp-server/ . The `aws login` flow itself was not run or tested here.

## Extending (how `phase14-main` was added, no restructuring)

Permission sets are entries of the map `local.permission_sets` in `permission_sets.tf`. Each entry is a map of named policy documents; the `phase14-main` documents are defined in `phase14_main.tf`. To add a set: add `"<name>" = { <part> = local.<document>, ... }` to `local.permission_sets`, define the document locals, list the name in `enabled_permission_sets`. `main.tf` flattens the selected sets with `for_each` into one managed policy plus one attachment per document. A role defaults to at most 10 attached managed policies: `phase14-main` uses 7 and the login policy is inline (it does not count); the role has a precondition for the quota and against enabling both sets.

## The `phase14-main` set (decision 14-6)

What the operator needs to plan, apply, verify and tear down the **main root** (`infra/terraform`, every module) with the runtime, Neptune and EMR enabled, and to run the `scripts/deploy.sh` stages that use this role. Documents are in `phase14_main.tf`; the permission-set registry entry is in `permission_sets.tf`.

### How the actions were derived (not guessed)

1. Every `resource "aws_*"` block of `infra/terraform/*.tf` and `infra/terraform/modules/**` was enumerated (62 AWS types; `terraform_data` calls no API; there is no `data` source). The table type, module, covering document is `target/phase14/evidence/14a-infra/resource-types.txt` (evidence, git-ignored).
2. For each type, the create, update and delete calls and the read, list, describe and tag calls the AWS provider (6.44.0) makes while refreshing and planning it were listed from the provider's behavior and the service's IAM page (Service Authorization Reference, one page per service: https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html).
3. The AWS CLI calls `scripts/deploy.sh` makes under this role were added: runtime-archive upload and verification (`s3 cp`, `head-object`, `get-object-attributes`), ECR login, push and digest checks, `ecs describe-services` and `describe-task-definition`; `scripts/cleanup.sh` adds `tag:GetResources`.
4. Where the documentation names a prerequisite call, it was added: Cloud Map creates the Route 53 private zone with the caller's permissions (https://docs.aws.amazon.com/cloud-map/latest/dg/security_iam_id-based-policy-examples.html); ECS target tracking needs `cloudwatch:PutMetricAlarm`, `DescribeAlarms`, `DeleteAlarms` (https://docs.aws.amazon.com/autoscaling/application/userguide/security_iam_id-based-policy-examples.html); `GetObjectAttributes` needs `s3:GetObject` and `s3:GetObjectAttributes`, and with SSE-KMS `kms:GenerateDataKey` and `kms:Decrypt` (https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectAttributes.html).

### Documents (characters after `jsonencode`, limit 6144) and attachments

| Managed policy (`scholarchain-deployer-phase14-main--<part>`) | Characters | Covers |
|---|---:|---|
| `network` | 3824 | EC2 describe; VPC, subnet, IGW, route table, security group, NAT, EIP, endpoint creation (request tags, existing-parent resource tags); tagging |
| `network-mod` | 1702 | modify and delete of tagged networking, route and rule changes |
| `data` | 5164 | S3 buckets (name prefix) and artifact-object upload, S3 Vectors, DynamoDB, SQS, Step Functions, Neptune (rds API) |
| `keys-obs` | 3327 | KMS (`CreateKey`, tag-at-create, aliases, `ListAliases` only: administration, use and grants of the main-stack keys are in each key's own policy), Secrets Manager metadata, CloudWatch Logs, alarms, dashboards, `tag:GetResources` |
| `compute` | 5696 | ECS, ECR (including push), ALB, Application Auto Scaling, Cloud Map and its Route 53 zone |
| `emr-efs` | 5113 | EMR (RunJobFlow, cluster management), EFS (file system, access point, mount target, policy) and its ENI |
| `iam` | 5637 | roles, instance profile, PassRole, service-linked roles, boundary protections, secret-value Deny |
| boundary `scholarchain-<env>-permissions-boundary` | 3372 | ceiling for the runtime roles (not attached to the deployer) |
| boundary `scholarchain-<env>-emr-service-boundary` | 4607 | ceiling for the EMR service role (not attached to the deployer) |

**Attachments on `scholarchain-deployer` after the change: 7 managed policies (quota 10) + 1 inline policy (the same-device login policy, which does not count toward the managed quota) = 8 policies.** The full per-document list (document, Sid, actions, resource pattern, conditions; 363 distinct Allow actions across the seven documents, 10 Deny actions) is generated from `terraform console` over the mock configuration into `target/phase14/evidence/14a-infra/phase14-main-actions.txt`.

### Role, trust, session (confirmed, unchanged by this change)

`aws_iam_role.deployer` (`main.tf`): trust is exactly one principal (`operator_principal_arn`) with `Bool aws:MultiFactorAuthPresent = true`, and `max_session_duration = 3600`. The tests `trust_requires_mfa_and_exact_principal` and `p14_trust_requires_mfa_and_the_session_is_one_hour` assert both and fail when either is mutated.

### Scoping rules

* **Region.** Every Allow statement outside IAM and Route 53 carries `aws:RequestedRegion = us-east-2` (from `var.region`, validated to `us-east-2`). IAM and Route 53 are global services; a RequestedRegion condition on them would block them, so they carry none (explicit, tested both ways).
* **Names.** Wherever the ARN can carry a name it is built on `scholarchain-<main_environment>-`: buckets (`...-<account>-*`), tables, queues, ECR repositories, ECS cluster and services, state machine, log groups, alarms, dashboards, KMS aliases, Neptune identifiers.
* **Tags.** Create calls require the request tags `project=scholarchain` and `environment=<main_environment>`; calls on existing resources require the same resource tags (the main root's provider `default_tags` set both on everything that can carry a tag). Create calls are also authorized against existing parents (VPC, subnet, route table, EIP, security group), which need the resource tag (learned in the Phase 12D live run).
* **IAM** is limited to roles `scholarchain-<env>-*` (this prefix excludes `scholarchain-deployer` and `scholarchain-billing-deployer`, tested), the instance profile `scholarchain-<env>-*`, and six named service-linked roles (ECS, ECS Application Auto Scaling, Elastic Load Balancing, RDS for Neptune, EMR cleanup, EFS). No customer-managed policy, user, access key or managed-policy attachment action exists in the set (the main root creates none; tested).
* **`iam:CreateRole` requires a boundary** (`iam:PermissionsBoundary`) and the project request tags: the six runtime roles require `scholarchain-<env>-permissions-boundary`, `scholarchain-<env>-emr-service` requires `scholarchain-<env>-emr-service-boundary`. `PutRolePolicy` and `DeleteRolePolicy` require the target role to carry one of the two boundaries.
* **Boundary tamper protection (Deny).** `CreatePolicyVersion`, `SetDefaultPolicyVersion`, `DeletePolicy`, `DeletePolicyVersion` on both boundaries; `PutRolePermissionsBoundary`, `DeleteRolePermissionsBoundary`, `UpdateAssumeRolePolicy` on every main role (so a trust change needs a role replacement or a routed repair); `sts:AssumeRole` on main roles; `secretsmanager:GetSecretValue` and `BatchGetSecretValue` on everything.
* **PassRole** exists as five statements, each limited by `iam:PassedToService` to exactly one service and to the roles that service needs: `ecs-tasks` (task and execution roles), `elasticmapreduce` (service role), `ec2` (instance role), `rds` (Neptune loader role) and `states` (producer role).
* **No `*:*`, no `"Action": "*"`, no service-wide `"<svc>:*"` and no prefix wildcard action** anywhere in the seven documents or the boundaries (tested; an `s3:*` mutation fails).

### Honest list: statements that cannot be scoped tighter

Each is its own statement, and each carries the region condition unless it is global.

| Action(s) | Resource | Why |
|---|---|---|
| `ec2:Describe*` (22 listed in `network`) | `*` | describe actions have no resource-level scoping |
| `tag:GetResources` | `*` | no resource type |
| `kms:CreateKey` | `*` | no resource type; scoped by request tags |
| `kms:ListAliases` | `*` | no resource type |
| `ecs:RegisterTaskDefinition` (request tags), `ecs:DeregisterTaskDefinition`, `ecs:DescribeTaskDefinition`, `ecs:DeleteTaskDefinitions` | `*` | the task-definition family name is not in the request ARN for every call |
| `ecr:GetAuthorizationToken` | `*` | no resource-level permissions |
| `elasticloadbalancing:Describe*` (9 listed), `acm:DescribeCertificate` | `*` | list-style reads |
| `application-autoscaling:Describe*` (3), `servicediscovery:GetOperation` | `*` | list-style reads |
| `cloudwatch:DescribeAlarms`, `cloudwatch:ListDashboards` | `*` | alarms are read by name, dashboards are listed |
| `logs:DescribeLogGroups` | `log-group:*` in region and account | the name prefix is a request parameter, not part of the ARN |
| `rds:Describe*` (10 listed) | `*` | list-style reads (Neptune uses the rds API namespace) |
| `elasticmapreduce:CreateSecurityConfiguration`, `DeleteSecurityConfiguration`, `DescribeSecurityConfiguration`, `ListSecurityConfigurations`, `ListClusters` | `*` | no resource type |
| `elasticmapreduce:RunJobFlow` | `*` | no resource type; scoped by the request tags project, environment, `scholarchain:stack = <main_emr_stack_tag_value>` and `for-use-with-amazon-emr-managed-policies = true` |
| `route53:CreateHostedZone`, `GetHostedZone`, `ListHostedZonesByName`, `DeleteHostedZone`, `ChangeResourceRecordSets`, `ListResourceRecordSets`, `GetChange`, `ListTagsForResource`, `ChangeTagsForResource` | `*`, no region condition | Cloud Map creates and deletes the private hosted zone with the caller's permissions; the zone ID is unknown before creation |
| `ec2:CreateNetworkInterface`, `DeleteNetworkInterface`, `ModifyNetworkInterfaceAttribute` | `network-interface/*` in region and account | the EFS mount-target call creates an untagged ENI with the caller's permissions |
| `kms:TagResource` | `key/*` in region and account | `CreateKey` with tags needs it in an IAM policy because the key and its key policy do not exist yet, and AWS says it "must cover all KMS keys in the account and Region" (https://docs.aws.amazon.com/kms/latest/developerguide/add-tags.html); narrowed by the request tags and `aws:TagKeys` limited to `main_tag_keys`. Tags confer nothing: no IAM statement grants anything on a key by tag (F2). Residual: a foreign key can receive, or have overwritten, those twelve tag keys. |
| `secretsmanager:DescribeSecret`, `GetResourcePolicy` | `secret:*` in region and account | metadata only, to confirm the human-created secrets; the secret names are not fixed in code. `GetSecretValue` is denied. |
| `s3:GetObject`, `PutObject`, `GetObjectAttributes` and the multipart actions | the artifacts bucket's objects only | the 14C data loads into other buckets are not in this set |

**Repair round 1 (F2) removed the two widest rows and supersedes the D4 and D6 acceptances for them.** The user ordered "fix all blocking bugs" after the external review found that tag adoption widened the tag-scoped statements. (1) Keys: `KmsManageProjectKeys`, `KmsUseProjectKeysViaServices` and `KmsGrantsForAwsResourcesOnly` are gone from IAM; administration, use and grants of each main-stack key are in that key's own policy (`modules/identity/main.tf`, Sids `DeployerAdministersThisKey`, `DeployerUsesThisKeyOnlyThroughServices`, `DeployerGrantsForAwsResourcesOnly`), naming this role by an ARN built from the account ID and the fixed name `scholarchain-deployer` (the same pattern as the boundary ARNs; no remote state). The account-root delegation statement stays: it is the lockout-safety and break-glass path (the key policy must allow the caller to call `PutKeyPolicy` again, https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html) and the runtime roles use it. A foreign key tagged into the project's tag scope gains nothing through IAM. (2) Security groups: the main root no longer manages the VPC default security group (`aws_default_security_group` is removed from `modules/network`, as the Phase 12D spike did), so `Ec2AdoptedDefaultSgRevokeRules` and `Ec2AdoptedDefaultSgFirstTags` are deleted and no statement can tag a security group into scope without `ec2:CreateAction`; the `ec2:Vpc` narrowing question (D4) is moot. Residual: the default security group keeps AWS's default rules; nothing is a member of it. Tests: `p14_negative_a_foreign_key_with_the_project_tags_gains_no_administration_use_or_grant_rights_from_iam`, `p14_negative_a_security_group_with_the_project_tags_gains_no_mutation_rights_from_iam`, and in the main root `the_main_stack_key_policy_grants_the_deployer_role_exactly_its_administration_and_nothing_else`.

### Not granted (a routed repair adds them when a later step needs them)

The 14C data-plane work (S3 loads into raw, curated and graph, DynamoDB items, SQS send, `neptune-db`, S3 Vectors puts, Bedrock invoke) and the Phase 15 EMR step submission (`elasticmapreduce:AddJobFlowSteps`, `CancelSteps`) are not in this set; neither is `s3:ListAllMyBuckets`, `iam:AttachRolePolicy` (the main root attaches no managed policy; choosing the managed `AmazonEMRServicePolicy_v2` for Q13 would need it), budgets, or anything on the billing deployer. `iam:CreateServiceLinkedRole` is limited to the six roles above; `ec2:DisassociateAddress` is granted on tagged elastic IPs only, so carried item 24 (the NAT address) still needs the second destroy pass. Destructive permissions that exist on purpose: `kms:ScheduleKeyDeletion` and `CancelKeyDeletion` for the main-stack keys only, granted by the key policy (the key carries a 7-day window, `kms_deletion_window_days`; the cleanup policy in `scripts/` keeps keys and buckets, the key policy does not) and the delete actions of every stack resource type, which `scripts/cleanup.sh` needs.

### Permissions boundaries on the main root's roles (D1, wired in Phase 14A round 2)

`iam:CreateRole` in `phase14-main` requires a boundary, so every role the main root creates now carries one. The ARN is built from the account ID and the fixed names (no remote state, no extra human input): `arn:aws:iam::<account>:policy/scholarchain-<environment>-permissions-boundary` and `.../scholarchain-<environment>-emr-service-boundary` (`<environment>` = `<project>-<environment>` prefix of the main root, `modules/identity/main.tf` `local.boundary_arn`, `modules/workflow/main.tf`). This root creates the policies from `boundaries/runtime.json.tftpl` and `boundaries/emr-service.json.tftpl`, the same files the main root's tests render.

| Role (main root) | Boundary |
|---|---|
| `scholarchain-<env>-{query-api,graph-service,semantic-service,embedding-worker}-task` (4), `-{...}-execution` (4), `-neptune-loader`, `-emr-ec2` (the EMR instance role), `-deployment`, `-embedding-producer` (Step Functions, `modules/workflow/main.tf:3`) | `scholarchain-<env>-permissions-boundary` (runtime) |
| `scholarchain-<env>-emr-service` | `scholarchain-<env>-emr-service-boundary` (EMR service role: the EC2 launch ceiling that mirrors `AmazonEMRServicePolicy_v2`) |

**Order matters:** the boundaries must exist before the main root's first apply (a role created with a boundary that does not exist fails with `NoSuchEntity`), so the deployer root is applied first. The main root's test `every_action_of_every_role_policy_is_allowed_by_that_roles_boundary` renders the same template files and asserts that every Allow action of every policy attached to each role (inline; the main root attaches no managed policy) is allowed by that role's boundary, wildcard-aware; a role policy that grows past its boundary, or a boundary that loses an action, fails the test instead of the runtime. It checks actions, not resource ARNs.

### Human-run command sequence (deployer root, in the human's terminal, with the human's admin profile, never the deployer role)

The state of this root is local and untracked, at `$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate` (decision D5; an agent never reads it). The path contains a space: **quote it**. The principal that applies needs IAM write permission and MFA (the human architect's admin profile; `scholarchain-deployer` cannot change itself).

```bash
# 0. variables and state path (no secrets in the vars file; it is git-ignored by *.tfvars)
export AWS_PROFILE=<architect-admin-profile>          # MFA-authenticated session
STATE="$HOME/Library/Application Support/ScholarChain/terraform/spike-emr/deployer.tfstate"
cd infra/terraform/deployer
cat > deployer.local.tfvars <<'TFVARS'
account_id             = "<12-digit-account-id>"
operator_principal_arn = "arn:aws:iam::<12-digit-account-id>:user/<operator>"
owner                  = "<owner tag>"
TFVARS

# 1. BACK UP THIS FILE BEFORE APPLY, and record the checksum of the copy
test -f "$STATE" || echo "STATE FILE MISSING: see the import fallback below"
BACKUP="$STATE.pre-phase14-$(date -u +%Y%m%dT%H%M%SZ).bak"
cp "$STATE" "$BACKUP"
shasum -a 256 "$BACKUP"                           # write this hash into the phase evidence

# 2. plan first; the saved plan is what is reviewed and applied
terraform init -input=false -lockfile=readonly
terraform plan -input=false -state="$STATE" -var-file=deployer.local.tfvars -out=deployer-phase14.tfplan
terraform show -no-color deployer-phase14.tfplan > deployer-phase14.plan.txt      # read ALL of it
```

Review expectations (the exact address list is in `target/phase14/evidence/14a-infra/deployer-apply-proposal.md`): **create** 2 boundary policies, 7 `permission_set` policies and 7 attachments; **destroy** the 4 spike policies, the 4 spike attachments and `aws_iam_policy.spike_boundary[0]`; `aws_iam_role.deployer` at most an in-place update, normally no change; no change to `aws_iam_role_policy.login`. **ANY replacement of `aws_iam_role.deployer` (a `-/+` or "must be replaced") = STOP, do not apply.** Any address outside that list = STOP and report. On `LimitExceeded` (11 > 10 attachments while the 4 spike detachments race the 7 new attachments), stop, re-plan, expect only the remaining creates, re-apply; any other change is a stop.

```bash
# 3. only after the human reviewed the saved plan and recorded the decision in the phase evidence
#    (a reviewed plan is not an approval to apply)
terraform apply -state="$STATE" deployer-phase14.tfplan
# 4. read-only verification
aws iam list-attached-role-policies --role-name scholarchain-deployer --query 'length(AttachedPolicies)'   # expect 7
aws iam get-role --role-name scholarchain-deployer --query 'Role.MaxSessionDuration'                       # expect 3600
shasum -a 256 "$STATE"                                                                                       # record the new hash; back the file up again
```

Fallback only if the state file is missing: the role from Phase 12D exists in the account, so import it before planning (`terraform import -state="$STATE" -var-file=deployer.local.tfvars aws_iam_role.deployer scholarchain-deployer`, then the login policy `aws_iam_role_policy.login scholarchain-deployer:scholarchain-deployer-same-device-login`), or the apply fails with `EntityAlreadyExists`; then re-plan and compare with the expectations above, and stop and ask if the spike policies do not appear as destroys.

**Disclosure: "a missed action shows up as AccessDenied during base-apply; it is fixed by a routed infra-engineer repair, a new reviewed deployer apply and a new plan".** Nothing here was executed against AWS; the sets are authored from documentation. Known places where the documentation was ambiguous and a denial is possible: the exact IAM action set `aws_s3_bucket` reads in provider 6.44.0 (`s3:ListAllMyBuckets` is not granted), Cloud Map and Route 53 hosted-zone calls, `kms:ViaService` for S3 Vectors (`s3vectors.<region>.amazonaws.com`, taken from the S3 Vectors encryption page), the grant-condition key `kms:GrantIsForAWSResource` on `RetireGrant`, ECS `TagResource` on task definitions, and KMS tag-based authorization of a key right after `CreateKey` (tag changes are eventually consistent for authorization).

## The `spike-emr` set (kept in code; not enabled by default, spike destroyed)

Kept rather than removed: it is live-proven history, and the independent spike tests and the carried-item evidence still plan it. Remove it only by a reviewed change together with those tests. Least privilege for creating and destroying exactly the isolated spike root's resources.

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

Tests run files `tests/deployer.tftest.hcl` (the `spike-emr` runs select that set explicitly; the `p14_*` runs select `phase14-main`) and `tests/default_set.tftest.hcl` (the variable default itself).

The `p14_*` runs assert, each from a hand-derived expectation: seven named documents, each under 6144 characters (also with the longest allowed environment name), 7 managed attachments (quota 10); spike absent and not combinable; MFA trust and a 3600 s session; no `*`, `*:*`, `<svc>:*` or prefix action, and Resource `*` only for Describe/List/Get reads or the honest-list writes; the us-east-2 condition on every Allow outside IAM and Route 53 (and none on those two); IAM only on `scholarchain-course-*` roles, instance profiles, boundaries and six service-linked roles, never `scholarchain-deployer`; `CreateRole` requires the right boundary and the project tags; the boundary-tamper Denies exist and no Allow undoes them; PassRole is one service per statement; exact tag-condition values; request-tag scoping of `kms:CreateKey`, `RunJobFlow` and `RegisterTaskDefinition`; no IAM statement grants key administration, use or grants and no tag-only path reaches a security group (the two F2 negative runs); coverage of a hand-listed action set for every resource type; nothing for budgets or billing; boundary ceilings (EMR boundary covers every action of `environments/emr-service-policy.json.example`). Round 2 adds: the EMR managed-policies tag key is in `main_tag_keys` and no tag-on-create statement restricts it. The boundary documents are `boundaries/*.json.tftpl` (rendered here with `templatefile`, and by the main root's tests); `tests/default_set.tftest.hcl` asserts the variable default. The older runs assert: MFA and exact-principal trust; four spike policies each under the managed-policy size limit; no wildcard or prefix-wildcard action; region condition on regional statements; IAM statements only on the spike prefix; PassRole, boundary and attach conditions; nothing for budgets, Organizations, Cost Explorer or the billing deployer; unknown permission set, wildcard or foreign operator, wrong region, billing role name and bad account id all fail.

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
