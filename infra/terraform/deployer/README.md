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
| `aws_iam_role.operator["loader"\|"reader"\|"cleanup"]`, `aws_iam_role_policy.operator[...]` (4 inline data policies) and `aws_iam_role_policy.operator_login[...]` (3 inline same-device login policies) | replan W5a and W5a-2, only when `operator_roles_enabled = true` (default false): the three MFA-only, 4 hour operator roles for 14B/14C, each usable with `aws login` exactly like the deployer role; see "Replan W5a" and "Signing in with `aws login`" below; G-DEPLOYER adds `aws_iam_role.operator_pipeline[0]`, `aws_iam_role_policy.operator_pipeline[0]` and `aws_iam_role_policy.operator_pipeline_login[0]` (the fourth role, `scholarchain-<env>-operator-pipeline`: EMR step submission and the EMR artifact upload; see "Replan G-DEPLOYER") |

Outputs: `role_arn`, `main_permissions_boundary_arns` (the two boundary ARNs the main root's roles must carry), `spike_permissions_boundary_arn` (pass to the spike root as `permissions_boundary_arn`), `operator_caller_policy_json` (the document the human operator needs to call `sts:AssumeRole`; nothing is attached to the operator by this root), `available_permission_sets`, `policy_names`, and (replan W5a) `operator_role_arns`, `operator_scope` and (W5a-2) `operator_roles_caller_policy_json` (all null while the operator roles are disabled; the last is an optional `sts:AssumeRole` document for the three roles, nothing is attached by this root).

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
| `operator_roles_enabled` | replan W5a, bool, default `false`: create the operator roles (loader, reader, cleanup and, G-DEPLOYER, pipeline); `false` plus an apply removes them |
| `operator_run_prefix` | replan W5a, default `null`, required when the roles are enabled, regex `^run-[a-z0-9][a-z0-9-]{1,27}$` (for example `run-20261115`): the run folder in the graph and curated buckets |
| `operator_embedding_text_prefix` | replan W5a, default `embedding-text`: rag-bucket prefix of the 14C embedding text; must equal the main root's `embedding_text_prefix` |
| `operator_neptune_cluster_resource_id` | replan W5a, default `null`, `^cluster-[A-Z0-9]{10,40}$`: the Neptune cluster resource id; `null` falls back to `cluster-*/*` of this account and region |
| `spike_kms_tag_keys` | carried item 14: the only tag keys `kms:TagResource` may apply (default: the spike root's eight keys); must include `scholarchain:stack`, no wildcard |
| `spike_role_names` | carried item 16: exactly the two role names `iam:CreateRole` may create (default `scholarchain-spike-emr-service` and `-instance`) |

## Same-device login (`aws login`)

The human signs in with `aws login --profile scholarchain-deployer` (browser OAuth on the same device), which needs sign-in permissions on the role itself. `aws_iam_role_policy.login` grants exactly `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token` on `arn:aws:signin:us-east-2:<account>:oauth2/public-client/localhost`, conditioned on `signin:OAuthClientId = arn:aws:signin:::devtools/same-device`. It is separate from the permission sets (every set needs it), mirrors the already installed and reviewed billing-role login policy (`docs/agent-runs/phase-12/evidence/12d-human-identity-bootstrap/user-supplied-policy-readbacks/role-login-policy.json`), grants sign-in only (no `signin:*`, no `*` resource), and is not added to `operator_caller_policy_json`; the operator's own login is handled separately. The three operator roles carry the same policy (replan W5a-2, next section). AWS documents these two actions as the OAuth permissions in the IAM policy: https://aws.amazon.com/blogs/security/introducing-oauth-support-for-aws-mcp-server/ . The `aws login` flow itself was not run or tested here.

## Signing in with `aws login`: deployer and operator roles (replan W5a-2)

Authored offline; no `aws login`, console switch or AWS call was run for this section. Placeholders: `<acct>` is the 12-digit account (never written in the repository), `<iam-user>` is the IAM user named by `operator_principal_arn`, `<env>` is `main_environment` (default `course`).

### How `aws login` authenticates in this pattern (facts and what is unverified)

| # | Fact | Source | Status |
|---|---|---|---|
| 1 | `aws login` does not authenticate a role by itself. It lets you "select from your active console sessions", then stores the chosen session in the profile as `login_session = <session ARN>`. For a role this is the **role session that a console Switch Role created**. The sign-in principal is the role session (CloudTrail `AuthorizeOAuth2Access` is logged with an `AssumedRole` identity). | https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html ; https://aws.amazon.com/blogs/security/simplified-developer-access-to-aws-with-aws-login/ ; https://docs.aws.amazon.com/sdkref/latest/guide/feature-login-credentials.html ; repo: Phase 12D candidate B, `docs/agent-runs/phase-12/evidence/12d-login-path-evaluation/decision-memo.md:3` | documented; the human ran it for the billing role (`docs/agent-runs/phase-12/test-report.md:272-274`, user-supplied result `assumed-role/scholarchain-billing-deployer/scholarchain-billing-operator`, session name = IAM user name) |
| 2 | The signed-in role needs exactly two actions, `signin:AuthorizeOAuth2Access` and `signin:CreateOAuth2Token`; `oauth2/public-client/localhost` is the same-device resource (`remote` is `aws login --remote`). The role policy here grants those two on `arn:aws:signin:us-east-2:<acct>:oauth2/public-client/localhost` with `signin:OAuthClientId = arn:aws:signin:::devtools/same-device`. The resource region is the sign-in region, so always pass `--region us-east-2`. | same CLI guide; `infra/terraform/deployer/main.tf:43-59` and `:134-138` (deployer); `operator_roles.tf` `local.op_login_policy` and `aws_iam_role_policy.operator_login` (operators); `docs/agent-runs/phase-12/evidence/12d-human-identity-bootstrap/user-supplied-policy-readbacks/role-login-policy.json:1-21` (installed billing-role original) | documented; the client-id pin and the exact resource were accepted in Phase 12D but their live acceptance beyond the billing-role login is unverified |
| 3 | **MFA.** The trust condition `Bool aws:MultiFactorAuthPresent = true` is evaluated by the console's `AssumeRole` when the IAM user switches roles; the IAM user's MFA console sign-in supplies it. The Phase 12D billing role has the identical strict trust and the same flow worked. Whether the credentials that `aws login` then issues carry `aws:MultiFactorAuthPresent = true` is **UNVERIFIED** (no AWS page says so; the key is documented for AssumeRole, GetSessionToken and console credentials). No permission policy in this root uses that key (tests assert it for the operator roles); keep it so. | https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_condition-keys.html ; `docs/agent-runs/phase-12/repairs.md:249` and `:259` | trust at the console switch: demonstrated once (Phase 12D, user-supplied); MFA flag in the issued credentials: UNVERIFIED |
| 4 | **Lifetime.** Each access credential lives 15 minutes (the token API's maximum `expires_in` is 900); the CLI and the SDKs refresh it automatically with the refresh token, "up to 12 hours", then you must run `aws login` again. The session is "valid for up to the set session duration of the IAM principal (maximum of 12 hours)". A console role switch gives the role `min(role maximum session duration, remaining IAM-user console session)`; IAM-user console sessions last 12 hours by default. So the operator roles give at most 4 hours **counted from the console switch**, not from `aws login`, and never beyond the IAM user's console session. The deployer role gives 1 hour. | https://docs.aws.amazon.com/signin/latest/APIReference/API_dataplane-signin_CreateOAuth2Token.html ; https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-console.html | documented; UNVERIFIED: that the `aws login` credentials end exactly with the role session, and whether switching back or signing out of the console ends the cached refresh token |
| 5 | **No role chaining.** Switching from one role session to another role (in the console, the CLI or the API) is role chaining and is limited to 1 hour whatever the role maximum is. The deployer role's `DenyAssumingMainRoles` also denies it. So switch to each operator role **from the IAM user session** ("Switch back" first), never from the deployer or another operator role. | same switch-role page | documented |
| 6 | **Java.** The AWS SDK for Java 2.x supports `login_session` profiles, but only with the `software.amazon.awssdk:signin` module on the classpath (https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/credentials-temporary.html). `project/Dependencies.scala` pins `software.amazon.awssdk` 2.56.0 for `s3`, `dynamodb`, `neptunedata`, `s3vectors`, `sqs` and `bedrockruntime` only; there is no `signin` entry, so `ProfileCredentialsProvider` (used by `StorageLoadMain`, `RuntimeArtifactMain`, `LiveEmbeddingIngestMain`) cannot read a `login_session` profile today. `signin` 2.56.0 exists on Maven Central (the pom answered HTTP 200; the first listed version is 2.39.0). Use a `credential_process` profile that calls `aws configure export-credentials` (the documented workaround for tools without console-login support); no build or code change. When the module is present the provider refreshes by itself (defaults: prefetch 5 min, stale 1 min, asynchronous). | https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html ; https://docs.aws.amazon.com/java/api/latest/software/amazon/awssdk/services/signin/auth/LoginCredentialsProvider.Builder.html ; `project/Dependencies.scala:16-21` | documented; the `credential_process` form was not run against a live account |

### `~/.aws/config` (the human adds these; placeholders only)

`aws login` writes the `login_session` line itself. Add only the blocks and `region`; the rest is shown as the result of a successful login.

```ini
[profile scholarchain-deployer]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-deployer/<iam-user>

[profile scholarchain-loader]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-loader/<iam-user>

[profile scholarchain-reader]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-reader/<iam-user>

[profile scholarchain-cleanup]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-cleanup/<iam-user>

# Java tools only (StorageLoadMain, RuntimeArtifactMain, LiveEmbeddingIngestMain). The profile name must differ from the login profile.
# Use the absolute path of aws (command -v aws); /opt/homebrew/bin/aws is the Homebrew path on this machine.
[profile scholarchain-loader-java]
credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-loader --format process
region = us-east-2

[profile scholarchain-reader-java]
credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-reader --format process
region = us-east-2

[profile scholarchain-cleanup-java]
credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-cleanup --format process
region = us-east-2
```

The AWS CLI needs version 2.32.0 or newer for `aws login`. Never open or paste `~/.aws/login/cache` (it holds the credentials and the refresh token).

### Sign in (repeat for each role; the console steps come first)

1. Browser: sign in to the AWS console as the IAM user `<iam-user>` with its password and MFA code.
2. Console menu (account name, top right) > **Switch role** > account `<acct>`, role name `scholarchain-<env>-operator-loader` (or `-reader`, `-cleanup`; or `scholarchain-deployer`) > **Switch Role**. You must be in the IAM user session when you do this. If a role is shown, choose **Switch back** first.
3. Note the time of the switch: the operator session ends 4 hours later (1 hour for the deployer).
4. Terminal:

```bash
aws login --profile scholarchain-loader --region us-east-2      # or scholarchain-reader / scholarchain-cleanup / scholarchain-deployer
```

5. In the browser choose the active session that shows the role you just switched to (not the IAM user), then return to the terminal. If the CLI asks to overwrite an existing `login_session` with a different ARN, answer `y` only if the new ARN is the role you intend.
6. Credential check (no permission needed; nothing is changed):

```bash
aws sts get-caller-identity --profile scholarchain-loader --region us-east-2
# expect "Arn": "arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-loader/<iam-user>"
# a user ARN (arn:aws:iam::<acct>:user/...) or a different role means the wrong session was selected: aws logout --profile scholarchain-loader, then repeat
```

7. Java check (resolves the credential process; makes no AWS data call):

```bash
sbt -batch 'storage / Compile / runMain edu.uic.cs441.scholarchain.storage.StorageLoadMain --check-credentials --profile scholarchain-loader-java'
# expect CREDENTIALS-RESOLVED: profile=scholarchain-loader-java sessionToken=true expiresAt=<about 15 minutes ahead>
```

`expiresAt` is the 15-minute access credential, not the end of the session. For each further role: console **Switch back**, switch to the next role, and run its `aws login`. A role already signed in keeps its cached login until it expires.

### Re-login

When a command fails with an expired-session or "run aws login" message (or after the 4 hours, or after you signed out of the console), run `aws login --profile <profile> --region us-east-2` again and select the same role session if the console role session is still active. If the role session itself has ended, repeat steps 1 to 6 (console sign-in with MFA, Switch role from the IAM user, then `aws login`). A load that stops because the session ended can be started again; the loads are idempotent (`modules/storage/README.md`). At the end of a working day or at cleanup run `aws logout --profile <profile>` (or `aws logout --all`).

### Optional fallback: caller policy

A same-account trust policy that names the IAM user is enough for `sts:AssumeRole`; no identity policy on the user is required unless one of its policies denies it. If the console switch is refused with AccessDenied, read `terraform output operator_roles_caller_policy_json` (an `sts:AssumeRole` document for exactly the three operator roles, MFA required) and have the human attach it to the IAM user. This root attaches nothing to the user.

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
| `data` | 5406 | S3 buckets (name prefix), artifact-object upload, object deletes for `force_destroy` (W5a-3), S3 Vectors, DynamoDB, SQS, Step Functions, Neptune (rds API) |
| `keys-obs` | 4544 | KMS (`CreateKey`, tag-at-create, aliases, `ListAliases` only: administration, use and grants of the main-stack keys are in each key's own policy), ACM certificate lifecycle (replan W5a), Secrets Manager metadata, CloudWatch Logs, alarms, dashboards, `tag:GetResources` |
| `compute` | 5696 | ECS, ECR (including push), ALB, Application Auto Scaling, Cloud Map and its Route 53 zone |
| `emr-efs` | 5113 | EMR (RunJobFlow, cluster management), EFS (file system, access point, mount target, policy) and its ENI |
| `iam` | 5637 | roles, instance profile, PassRole, service-linked roles, boundary protections, secret-value Deny |
| boundary `scholarchain-<env>-permissions-boundary` | 3592 | ceiling for the runtime roles (not attached to the deployer) |
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
| `s3:DeleteObject`, `s3:DeleteObjectVersion` (W5a-3, Sid `S3ObjectsDeleteForForceDestroy`) | `arn:aws:s3:::scholarchain-<env>-<account>-*/*`, region `us-east-2` | `force_destroy = cleanup_mode` on the seven project buckets; the deployer does not know the key space, so the object ARN pattern is the bucket-name pattern with `/*` |

**Repair round 1 (F2) removed the two widest rows and supersedes the D4 and D6 acceptances for them.** The user ordered "fix all blocking bugs" after the external review found that tag adoption widened the tag-scoped statements. (1) Keys: `KmsManageProjectKeys`, `KmsUseProjectKeysViaServices` and `KmsGrantsForAwsResourcesOnly` are gone from IAM; administration, use and grants of each main-stack key are in that key's own policy (`modules/identity/main.tf`, Sids `DeployerAdministersThisKey`, `DeployerUsesThisKeyOnlyThroughServices`, `DeployerGrantsForAwsResourcesOnly`), naming this role by an ARN built from the account ID and the fixed name `scholarchain-deployer` (the same pattern as the boundary ARNs; no remote state). The account-root delegation statement stays: it is the lockout-safety and break-glass path (the key policy must allow the caller to call `PutKeyPolicy` again, https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html) and the runtime roles use it. A foreign key tagged into the project's tag scope gains nothing through IAM. (2) Security groups: the main root no longer manages the VPC default security group (`aws_default_security_group` is removed from `modules/network`, as the Phase 12D spike did), so `Ec2AdoptedDefaultSgRevokeRules` and `Ec2AdoptedDefaultSgFirstTags` are deleted and no statement can tag a security group into scope without `ec2:CreateAction`; the `ec2:Vpc` narrowing question (D4) is moot. Residual: the default security group keeps AWS's default rules; nothing is a member of it. Tests: `p14_negative_a_foreign_key_with_the_project_tags_gains_no_administration_use_or_grant_rights_from_iam`, `p14_negative_a_security_group_with_the_project_tags_gains_no_mutation_rights_from_iam`, and in the main root `the_main_stack_key_policy_grants_the_deployer_role_exactly_its_administration_and_nothing_else`.

### Cleanup deletes (W5a-3: `force_destroy` on the project buckets)

The main root sets `force_destroy = cleanup_mode` on the seven project S3 buckets and the S3 Vectors vector bucket (no `prevent_destroy`; user decision: delete everything at cleanup). What the AWS provider calls (6.44.0, read from `internal/service/s3/delete.go` `emptyBucket` and `internal/service/s3vectors/vector_bucket.go`):

* **S3 buckets:** `ListObjectVersions` (`s3:ListBucketVersions`, already granted), then `DeleteObjects` for every object version and delete marker (`DeleteObject` singly for keys outside the XML character range). IAM needs `s3:DeleteObject` (an unversioned key) and `s3:DeleteObjectVersion` (a versioned entry). Both are now granted on `arn:aws:s3:::scholarchain-<env>-<account>-*/*` with the same `aws:RequestedRegion` condition as the neighbouring statements, in the `data` document (5164 -> 5406 characters, limit 6144). The provider does **not** abort multipart uploads and the buckets carry no Object Lock, so `s3:AbortMultipartUpload` (still artifacts-only) and `s3:BypassGovernanceRetention` are not added. Deleting objects needs no KMS permission.
* **Vector bucket:** `force_destroy` lists the indexes (`s3vectors:ListIndexes`) and deletes each index (`s3vectors:DeleteIndex`); both were already granted on the vector bucket and `index/*`. It calls neither `ListVectors` nor `DeleteVectors`, so no vector-level action was added (tests assert the thirteen s3vectors actions are exactly the previous set).
* `force_destroy` takes effect only after a successful apply that set it to true (provider documentation), which is what `scripts/cleanup.sh --prepare` does in the main root.
* Residual: the deployer can now delete any object in any bucket named `scholarchain-<env>-<account>-*` in `us-east-2`. That is the intent of the cleanup decision; the operator roles' own prefix-limited deletes are unchanged.

### Not granted (a routed repair adds them when a later step needs them)

The 14C data-plane work (S3 loads into raw, curated and graph, DynamoDB items, SQS send, `neptune-db`, S3 Vectors puts, Bedrock invoke) and the Phase 15 EMR step submission (`elasticmapreduce:AddJobFlowSteps`, `CancelSteps`) are not in this set (G-DEPLOYER gives step submission and the EMR artifact upload to the separate `operator-pipeline` role, never to the deployer role); neither is `s3:ListAllMyBuckets`, `iam:AttachRolePolicy` (the main root attaches no managed policy; choosing the managed `AmazonEMRServicePolicy_v2` for Q13 would need it), budgets, or anything on the billing deployer. `iam:CreateServiceLinkedRole` is limited to the six roles above; `ec2:DisassociateAddress` is granted on tagged elastic IPs only, so carried item 24 (the NAT address) still needs the second destroy pass. Destructive permissions that exist on purpose: `kms:ScheduleKeyDeletion` and `CancelKeyDeletion` for the main-stack keys only, granted by the key policy (the key carries a 7-day window, `kms_deletion_window_days`; the cleanup policy in `scripts/` keeps keys and buckets, the key policy does not) and the delete actions of every stack resource type, which `scripts/cleanup.sh` needs.

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

## Replan W5a (14B, USD 25 course cap): ACM, ECS Exec channels and the operator roles

Authored offline; nothing here was planned against or applied to AWS. Source: `docs/agent-runs/phase-14/prompt.md`, "Replan decisions" item 4 and "14C decisions" items 1 and 2. The deployer is applied **once**, with the ACM permissions and the operator roles already in it. The files: `phase14_main.tf` (ACM statements in `keys-obs`), `boundaries/runtime.json.tftpl` (ECS Exec channels), `operator_roles.tf` (the roles), `tests/replan_w5a.tftest.hcl` (25 runs).

### Naming contract with the main root (work order W5b follows this)

| Item | Contract |
|---|---|
| ACM certificate | created by the **main root in base-apply** with `aws_acm_certificate`, `validation_method = "DNS"`, **one subdomain** of a private domain taken from private tfvars (never committed), tagged with the project's standard tags (the root's `default_tags` are enough: `project = scholarchain`, `environment = <env>`, and only keys in `main_tag_keys`). `aws_acm_certificate_validation` exists **only in the runtime stage** (the HTTPS listener needs it); base-apply must not wait on validation. The DNS validation record is a root output. |
| Tunnel task role | `scholarchain-<env>-neptune-tunnel-task` (matches the existing `*-task` `iam:CreateRole` and `iam:PassRole` patterns; created with the runtime boundary, tags and `iam:PutRolePolicy` as for the other task roles). Its inline policy needs only the four `ssmmessages:` channel actions (inside the runtime boundary since this change); **no data access**. |
| Tunnel task definition | family `scholarchain-<env>-neptune-tunnel` (matches `task-definition/scholarchain-<env>-*:*`), registered by the main root, Fargate, awsvpc. |
| Tunnel run mode | **a one-off task** (`ecs:RunTask` with `--enable-execute-command`), not a service: nothing runs, and nothing is billed, between loads. `desired_count = 0` is therefore not used. `run-task` must not pass `--tags`, `--propagate-tags` or `--enable-ecs-managed-tags` (the loader role holds no `ecs:TagResource`). |
| Tunnel execution role | `scholarchain-<env>-graph-service-execution` (it can already pull the graph-service image and writes logs to `/scholarchain-<env>/graph-service`; a tunnel container that logs elsewhere would be denied, so log to that group or not at all). |
| Tunnel security group | the graph-service security group, the only one Neptune admits. |
| Operator roles | `scholarchain-<env>-operator-loader`, `scholarchain-<env>-operator-reader`, `scholarchain-<env>-operator-cleanup` (the Phase 7 `awsIntegration` suite expects loader, reader and cleanup profiles). Created and removed by **this** root only. |
| Main root outputs the human needs | the ACM validation record, the ALB DNS name, the Neptune writer endpoint, and the Neptune cluster resource id (`aws_neptune_cluster.<name>.cluster_resource_id`) for `operator_neptune_cluster_resource_id`. |

No deviation from the contract was needed: every name already matches an existing allowed pattern (`*-task` create and pass, `task-definition/scholarchain-<env>-*:*`, log group `/scholarchain-<env>/*`).

### ACM (documents: `keys-obs`, 3327 -> 4544 characters)

Condition keys the ACM Service Authorization Reference lists (https://docs.aws.amazon.com/service-authorization/latest/reference/list_acm.html): `acm:CertificateAuthority`, `acm:CertificateKeyPairOrigin`, `acm:CertificateTransparencyLogging`, `acm:DomainNames`, `acm:Export`, `acm:KeyAlgorithm`, `acm:ValidationMethod`, `aws:RequestTag/${TagKey}`, `aws:ResourceTag/${TagKey}`, `aws:TagKeys`. `RequestCertificate` takes no resource type; the certificate ARN (`arn:aws:acm:<region>:<account>:certificate/<id>`) supports `aws:ResourceTag`.

| Sid | Actions | Resource | Conditions |
|---|---|---|---|
| `AcmRequestCertificateDnsValidationWithProjectTags` | `acm:RequestCertificate` | `*` (no resource type) | region `us-east-2`; `acm:ValidationMethod = DNS` (the Cloudflare CNAME is added by hand, never email); `aws:RequestTag/project`, `aws:RequestTag/environment` |
| `AcmTagOnCreateWithProjectTags` | `acm:AddTagsToCertificate` | `certificate/*` in region and account | region; the request tags; `aws:TagKeys` limited to the twelve `main_tag_keys` (a request with tags is authorized as `AddTagsToCertificate` against a certificate that does not exist yet, so only request tags can scope it) |
| `AcmManageProjectTaggedCertificates` | `acm:DeleteCertificate`, `ListTagsForCertificate`, `AddTagsToCertificate`, `RemoveTagsFromCertificate` | `certificate/*` | region; `aws:ResourceTag/project` and `/environment` |

`acm:DescribeCertificate` was already granted (read only, region-locked, all certificates) in `ElbDescribeNoResourceScoping` and is left there. `acm:ListCertificates` is **not** granted: the `aws_acm_certificate` resource does not call it (the data source does). `acm:DomainNames` is not constrained because the domain is a private tfvars value the deployer must not know. **Residual:** a foreign certificate in the account can be given the project tag keys by `AcmTagOnCreateWithProjectTags` and then falls under the tag-scoped statement (the same shape as `KmsTagWithProjectTags`); the course account holds no other certificate.

### Runtime boundary (3372 -> 3592 characters)

Added `EcsExecChannelsForTheNeptuneTunnel`: `ssmmessages:CreateControlChannel`, `CreateDataChannel`, `OpenControlChannel`, `OpenDataChannel` on `*` (the actions have no resource type). **No `neptune-db` loader or write action was added**; the boundary keeps exactly the four read actions. The operator roles are not runtime roles. Because the boundary only bounds the roles, the tunnel task role's own inline policy (main root) must grant the four actions.

### Operator roles (`operator_roles_enabled`, default false)

* Trust: `var.operator_principal_arn` (the human who assumes the deployer role), `aws:MultiFactorAuthPresent = true`, one statement; byte-for-byte the deployer's trust shape (tests compare principal, action and condition with the deployer role). `max_session_duration = 14400` (4 h). The deployer pattern has no MFA-age condition, so none was added. The principal must be an IAM user: if the operator principal is itself a role (SSO), or the console switch starts from another role session, role chaining caps a session at 1 hour regardless of the maximum.
* Sign-in (W5a-2): every operator role also carries `aws_iam_role_policy.operator_login` (`<role name>-same-device-login`), the deployer's same-device login policy with only the Sid renamed (`local.op_login_policy` is derived from `local.login_policy`, so the two cannot drift), so `aws login --profile scholarchain-<loader|reader|cleanup>` works directly, with no `role_arn`/`source_profile` profile and no second `AssumeRole`. See "Signing in with `aws login`".
* No permissions boundary (not runtime roles). The deployer role cannot assume them (`DenyAssumingMainRoles` covers `scholarchain-<env>-*`) and cannot change their trust (`DenyBoundaryRemovalAndTrustChangeOnMainRoles`) or attach policies (`PutRolePolicy` needs a boundary condition).
* Inline policies, not managed ones: they do not count toward the deployer's quota of 10 and are removed with the role. `loader--data` 4216, `loader--tunnel` 1738, `reader--data` 3653, `cleanup--data` 3815 characters (each under 6144; tests assert it), plus the login policy per role (about 400 characters; tests assert that each role's inline policies together stay under the 10240-character aggregate limit).
* Every Allow carries `aws:RequestedRegion = us-east-2` except the global `iam:PassRole`. No IAM other than that PassRole, no infrastructure, no Marketplace, no `Resource *`, no wildcard action or service.

**S3 prefixes** (key layout in `modules/storage`: `<prefix>/versions/<version>/<name>`; the prefixes are configuration, so the run folder is a configuration contract):

| Bucket | Allowed key prefixes | Why |
|---|---|---|
| graph | `<operator_run_prefix>/*`, `source-qualifications/*` | `NeptuneGraphLoader` writes `<graphPrefix>/versions/<fingerprint>/validated/...` (configure `graphPrefix = <run prefix>/graph`); `SourceQualifications` writes the hard-coded `source-qualifications/versions/...` into the same bucket (`StorageLoadMain` uses one bucket, `cfg("bucket")`) |
| curated | `<operator_run_prefix>/*` | the 28-table Parquet upload, in the run folder |
| rag | `<operator_embedding_text_prefix>/*` (default `embedding-text`), `vector-rejects/*`, and (G4) `runtime-artifacts/<operator_run_prefix>/*` | `EmbeddingManifest` writes `<textPrefix>/versions|prepared|rejected/...`; the runtime roles can read only that prefix (`rag_prefixes`), so it cannot be run-specific; `S3VectorStore` writes `vector-rejects/versions/...`; `RuntimeArtifactMain` writes `runtime-artifacts/<run>/versions/...` (the loader **creates** only, see G4) |

The raw, artifacts, logs and reports buckets are not reachable. A `run-` start is mandatory so the run folder cannot equal a fixed prefix such as `pipeline/` (EMR outputs).

**Per role (actions exactly as tested):**

| Role | Actions | Resources |
|---|---|---|
| loader | `s3:PutObject`, `GetObject`, `GetObjectVersion`, `GetObjectAttributes`, `AbortMultipartUpload`, `ListMultipartUploadParts` (objects), `s3:ListBucket` (buckets, `s3:prefix` limited to the same prefixes); `kms:GenerateDataKey`, `kms:Decrypt`; `dynamodb:PutItem`, `UpdateItem`, `GetItem`, `Query`, `BatchGetItem`, `ConditionCheckItem`; `s3vectors:GetIndex`, `PutVectors`, `GetVectors`, `QueryVectors`; `bedrock:InvokeModel`; `neptune-db:StartLoaderJob`, `GetLoaderJobStatus`, `ListLoaderJobs`, `CancelLoaderJob`, `GetEngineStatus`; tunnel (below) | the prefixes above; the project key; the six tables `RunLedger`, `EntityLinkCache`, `QuerySession`, `EvidenceBundle`, `ArtifactRegistry`, `ResearcherMetricCache` named one by one, and their indexes; `bucket/<mp>-<account>-vectors/index/*`; `foundation-model/amazon.titan-embed-text-v2:0` in `us-east-2` only; Neptune below |
| reader | `neptune-db:ReadDataViaQuery`, `GetQueryStatus`, `GetEngineStatus`; `dynamodb:GetItem`, `Query`, `BatchGetItem`; `s3vectors:QueryVectors`, `GetVectors`; `s3:GetObject`, `s3:ListBucket`; `kms:Decrypt` | same |
| cleanup | `neptune-db:WriteDataViaQuery`, `DeleteDataViaQuery`, `ReadDataViaQuery`; `dynamodb:DeleteItem`, `Query`, `GetItem`; `s3vectors:DeleteVectors`, `ListVectors`; `s3:DeleteObject`, `DeleteObjectVersion`, `GetObject`, `GetObjectVersion`, `s3:ListBucket`, `ListBucketVersions`; `kms:Decrypt` | same |

**Additions beyond the work order's list, with the reason:** loader S3 multipart (`AbortMultipartUpload`, `ListMultipartUploadParts`) for the large Parquet uploads, `GetObjectVersion` and `GetObjectAttributes` for the checksum verification the upload tool records; reader and cleanup `kms:Decrypt` (they read or head objects encrypted with the project key; the work order listed no KMS for them); cleanup `DeleteObjectVersion`, `GetObject`, `GetObjectVersion`, `ListBucketVersions` because the buckets are versioned (`aws_s3_bucket_versioning` Enabled) and the storage cleanup deletes the exact owned key and version after checking its metadata (`modules/storage/README.md`, "Cleanup procedure"); a plain `DeleteObject` would only add a delete marker; `ssmmessages:OpenDataChannel` on the caller's own sessions (the Session Manager quickstart end-user policy lists it next to `TerminateSession`). All stay inside the run and tool prefixes.

**KMS:** `kms:GenerateDataKey` and `kms:Decrypt` on `key/*` of this account and region, with `kms:ViaService` in S3, DynamoDB and S3 Vectors and `kms:ResourceAliases = alias/scholarchain-<env>-data` (the key id is unknown before base-apply; the alias is the same condition the runtime boundary uses). The key policy already delegates to IAM for the account (`EnableExplicitAccountIamDelegationForThisKey` lists Encrypt, Decrypt and GenerateDataKey), so no key-policy change is needed.

**Neptune scope (the tightest workable option):** the cluster resource id exists only after base-apply, which comes after the single deployer apply. neptune-db supports no resource-tag condition (only global context keys, https://aws.amazon.com/blogs/database/fine-grained-access-control-for-amazon-neptune-data-plane-actions/). So `operator_neptune_cluster_resource_id = null` (default) gives `arn:aws:neptune-db:us-east-2:<account>:cluster-*/*` (every Neptune cluster of this account and region; the course account holds only the project's, and the cluster admits only the graph-service security group), and `output.operator_scope.neptune_scope_is_fallback` says so. After base-apply the human may set the id and apply the deployer root again (IAM only, in-place update of the three Neptune statements) to reach `cluster-<id>/*`. Both forms are tested.

**Tunnel (loader only):**

| Sid | Action | Resource and condition |
|---|---|---|
| `RunTheTunnelTaskDefinitionInTheProjectCluster` | `ecs:RunTask` | `task-definition/scholarchain-<env>-neptune-tunnel:*`; `ecs:cluster` = the project cluster ARN |
| `StopDescribeAndExecIntoTunnelTasks` | `ecs:StopTask`, `DescribeTasks`, `ExecuteCommand` | `task/scholarchain-<env>/*` and `cluster/scholarchain-<env>`; `ecs:cluster` |
| `StartPortForwardingToTheTunnelTasksOnly` | `ssm:StartSession` | `task/scholarchain-<env>/*` (the ECS target) and `arn:aws:ssm:us-east-2::document/AWS-StartPortForwardingSessionToRemoteHost` |
| `TerminateAndUseOwnSessionsOnly` | `ssm:TerminateSession`, `ssmmessages:OpenDataChannel` | `arn:aws:ssm:*:*:session/${aws:userid}-*` (the caller's own sessions) |
| `PassOnlyTheTunnelTaskRoleAndTheGraphServiceExecutionRole` | `iam:PassRole` | the tunnel task role and `scholarchain-<env>-graph-service-execution`; `iam:PassedToService = ecs-tasks.amazonaws.com` |

**Unverified against a live account (first live checks, the 14B tunnel test):** the `ssm:StartSession` resource form for an ECS target (`task/<cluster>/*`) and the session ARN form; whether document-level access is enforced without `ssm:SessionDocumentAccessCheck` (not added; the same role can already `ecs:ExecuteCommand` into those tasks, so a shell adds no reach); `ecs:cluster` on `ExecuteCommand`; AWS's June 2026 SSM Agent bulletin (remote-host port forwarding, fixed in agent 3.3.4851.0): the tunnel image must run a current managed agent, which Fargate supplies. An `AccessDenied` on the tunnel start is a routed repair plus another deployer apply, not a console change.

### Human apply sequence (replan; the 14A sequence above still applies, with these differences)

1. Add to `deployer.local.tfvars` (git-ignored): `operator_roles_enabled = true`, `operator_run_prefix = "run-<yyyymmdd>"`, and optionally `operator_embedding_text_prefix` if the main root's differs. Leave `operator_neptune_cluster_resource_id` unset (it is unknown until base-apply).
2. Back up `deployer.tfstate` and record the checksum of the copy (`cp`, `shasum -a 256`, exactly as in the sequence above), then `terraform init -input=false -lockfile=readonly` and `terraform plan -input=false -state="$STATE" -var-file=deployer.local.tfvars -out=deployer-replan.tfplan` with the admin profile.
3. Read the whole plan. Expected additions over the 14A plan: **13 creates** after G-DEPLOYER (10 at W5a, plus `aws_iam_role.operator_pipeline[0]`, `aws_iam_role_policy.operator_pipeline[0]` and `aws_iam_role_policy.operator_pipeline_login[0]`; the 10 are 3 `aws_iam_role.operator["cleanup"|"loader"|"reader"]`, 4 `aws_iam_role_policy.operator["cleanup--data"|"loader--data"|"loader--tunnel"|"reader--data"]` and 3 `aws_iam_role_policy.operator_login["cleanup"|"loader"|"reader"]`); the seven `permission_set` policies are created with the ACM statements already inside `keys-obs`, and `main_boundary_runtime` is created with the ECS Exec channels. If the state already holds the 14A policies (a prior deployer apply), `keys-obs` and `main_boundary_runtime` are in-place updates and nothing is replaced. Detail and counts: `target/phase14/evidence/14b/replan/deployer-apply-proposal-v2.md`.
4. **ANY replacement of `aws_iam_role.deployer` (`-/+`, "must be replaced", `delete,create`) = STOP, do not apply.** Any other destroy outside the 14A list, or any change to `aws_iam_role_policy.login`, also stops the apply.
5. Apply only after the decision is recorded in the phase evidence. Verify with the read-only calls in the proposal (the role list, `MaxSessionDuration` of 14400 on each operator role and the `...-same-device-login` policy name on each).

**Tightening Neptune after base-apply (optional):** set `operator_neptune_cluster_resource_id = "cluster-XXXX..."` and apply again; expect 3 in-place updates (`loader--data`, `reader--data`, `cleanup--data`) and nothing else.

**Removing the operator roles at cleanup:** set `operator_roles_enabled = false` (and leave the rest), back up the state, plan with the admin profile (expect **13 destroys**: the 9 inline policies (4 data, 3 login, the pipeline data and login) and the 4 roles, nothing else, the deployer role untouched), apply after the recorded decision. Sessions already issued keep working until they expire (at most 4 h), so also run the data cleanup first; the policies and roles are gone after the apply, and an issued session loses its permissions as soon as the role is deleted.

## Replan G-DEPLOYER (14B): runtime artifact write (G4), the operator-pipeline role (G5, G6), login profiles (G11), session rule (G13)

Authored offline; nothing here was planned against or applied to AWS (no AWS call, no `aws login`). It is part of the **same single deployer apply** (decision "EMR permission in the same apply"). Files: `operator_pipeline.tf` (new), `operator_roles.tf` (G4), `outputs.tf`, `tests/gdeployer.tftest.hcl` (13 runs), mutation evidence `target/phase14/evidence/14b/replan/infra-gdeployer-mutations.txt` (17 mutations, 17 caught).

### Who runs the bounded pipeline: a fourth operator role, `scholarchain-<env>-operator-pipeline`

| Candidate | Verdict |
|---|---|
| deployer role | No. Session is 1 h (a run is capped at 90 minutes of cluster time, and the script polls until the step ends; an expired session mid-run makes `describe-step` and the cancel fail). It is the infrastructure-administration role; step submission is arbitrary code on the cluster, and the deployer should not hold it. |
| operator-loader | No. It already holds Bedrock, DynamoDB, S3 Vectors and the Neptune loader; a pipeline run needs none of them and the loader needs no EMR. Mixing them breaks least privilege both ways. |
| **new operator-pipeline role** | **Chosen.** Same flow as the other operator roles (console Switch Role from the IAM user with MFA, then `aws login --profile scholarchain-pipeline`; 4 h; no role chaining; the same same-device login policy), IAM-only, free, created and removed by the same toggle (`operator_roles_enabled`). |

What `scripts/run-bounded-pipeline.sh --execute` calls from the laptop (read from the script; `sts get-caller-identity` needs no permission): `aws emr describe-cluster`, `get-auto-termination-policy`, `list-instance-groups` (cluster check), `add-steps`, `describe-step`, `cancel-steps`. Local files are hashed locally (`sc_sha256`); stage-in, copy-out and the bootstrap downloads run on the nodes with the EMR instance role, which already reads raw, curated, graph and artifacts and writes curated, graph, artifacts, logs and reports. `pipeline.py` and `scripts/emr/*.sh` make no AWS call from the laptop (`sc-step.sh` and `bootstrap.sh` call `aws s3 cp` on the node). `run-experiment.sh` delegates to the pipeline.

| Sid (document `operator_pipeline`, 3147 characters; plus the 336-character login policy) | Actions | Resource | Conditions |
|---|---|---|---|
| `EmrReadTheProjectClusterAndItsSteps` | `elasticmapreduce:DescribeCluster`, `ListInstanceGroups`, `GetAutoTerminationPolicy`, `DescribeStep` | `arn:aws:elasticmapreduce:us-east-2:<acct>:cluster/*` | region; `aws:ResourceTag/project = scholarchain`, `/environment = <env>`, `/scholarchain:stack = <main_emr_stack_tag_value>` |
| `EmrSubmitAndCancelStepsOnTheProjectClusterOnly` | `AddJobFlowSteps`, `CancelSteps` | same | same |
| `S3EmrArtifactsCreateOnlyWithIfNoneMatch` | `s3:PutObject` | `<artifacts bucket>/emr/<run>/*` | region; `Null s3:if-none-match = false` (the `If-None-Match` header is present) |
| `S3EmrArtifactsMultipartPartsWithoutTheHeader` | `s3:PutObject` | same | region; `Bool s3:ObjectCreationOperation = false` (`CreateMultipartUpload` and `UploadPart` cannot carry the header; only the final `CompleteMultipartUpload` creates the object and needs the first statement) |
| `S3EmrArtifactsReadBackAndMultipartMaintenance` | `s3:GetObject`, `GetObjectVersion`, `GetObjectAttributes`, `AbortMultipartUpload`, `ListMultipartUploadParts` | same | region |
| `S3PipelineOutputsAndEmrLogsReadOnly` | `s3:GetObject`, `GetObjectVersion` | `<artifacts>/pipeline/<run>/*`, `<logs bucket>/emr/*` | region |
| `S3ListArtifactsRunPrefixes`, `S3ListEmrLogsPrefix` | `s3:ListBucket` | the artifacts bucket, the logs bucket | region; `s3:prefix` limited to `emr/<run>`, `pipeline/<run>` (and `/*`), respectively `emr` (and `/*`) |
| `ProjectKeyThroughS3Only` | `kms:GenerateDataKey`, `kms:Decrypt` | `key/*` of this account and region | region; `kms:ViaService = s3.us-east-2.amazonaws.com`; `kms:ResourceAliases = alias/scholarchain-<env>-data` |

Not granted (tests assert each): `RunJobFlow`, `TerminateJobFlows`, `ListClusters`, `AddTags`, `ModifyCluster`, `SetTerminationProtection`, `Put/RemoveAutoTerminationPolicy`, instance-group changes, `ListSteps` (the script never calls it; add it by a routed repair if the runbook needs it), any `s3:Delete*`, `iam:*` (no PassRole: steps use no runtime role), `sts:*`, any other service, any other bucket (raw, curated, graph, rag, reports), `aws-marketplace`. **Residual (inherent to submitting steps):** a step is a `command-runner.jar` command and runs as the EMR instance role (`scholarchain-<env>-emr-ec2`), so this role can make the cluster read raw, curated, graph and artifacts and write curated, graph, artifacts, logs and reports. The tag conditions keep that on the project cluster; the cluster auto-terminates and `scripts/run-bounded-pipeline.sh` pins the step programs by sha256. `elasticmapreduce:ExecutionRoleArn` is not constrained (no runtime roles are used).

The deployer role keeps its existing `S3ArtifactsObjectsUploadAndVerify` (any key of the artifacts bucket; it uploads the 322 MB runtime archive in `base-apply`). A tidy key for that archive is `emr/<run>/runtime/<file>`; the deployer role is not restricted to it.

### EMR artifact contract (final) and how to upload

All EMR artifacts lie in the artifacts bucket `scholarchain-<env>-<acct>-artifacts` (the Terraform guard and the EMR instance role already require that) **below `emr/<operator_run_prefix>/`**. The folder names under it are not enforced; this layout is the recommendation (and what the tests use):

| Prefix | Content |
|---|---|
| `emr/<run>/bin/` | `bootstrap.sh` (`emr_config.bootstrap_uri`) |
| `emr/<run>/jars/` | job JAR (`job_jar_uri`), Hadoop submit JAR and libjars, entity-resolution JAR |
| `emr/<run>/steps/` | the four step programs `sc-step.sh`, `sc-ceiling-check.py`, `sc-class-origin-verify.py`, `sc-render-spark-config.py` (`extra_artifacts`) |
| `emr/<run>/config/` | prep config, ER policy and config, Spark config template |
| `emr/<run>/input/<size>/datasets/samples/{dblp,openalex,crossref,orcid}/...` | the EMR input datasets, one `<size>` folder per dataset size (`--input-prefix s3://<artifacts>/emr/<run>/input/<size>`) |
| `pipeline/<run>/` | `--output-prefix s3://<artifacts>/pipeline/<run>` (the node writes `<prefix>/<run-id>/{hadoop,er,spark,results,config}/`); this role only reads it; `pipeline/` is the prefix the main root's `emr_output_prefixes` allows the instance role to clean up |
| logs bucket `emr/` | the cluster `log_uri` (read-only here) |

Create-only means an object can never be replaced at its key (the buckets are versioned, so an overwrite would otherwise create a new version silently). To fix a wrong artifact, upload under a new key (and update `emr_config` / the flag), or have the deployer role delete the key. Upload single objects with `put-object` (up to 5 GiB; this is what `scripts/upload-slice.sh` does) so the header is sent in the one request:

```bash
aws s3api put-object --profile scholarchain-pipeline --region us-east-2 \
  --bucket scholarchain-<env>-<acct>-artifacts --key emr/<run>/jars/<file>.jar --body <local file> \
  --checksum-algorithm SHA256 --checksum-sha256 <base64 of the local sha256> --if-none-match '*'
```

`aws s3 cp` only works if the CLI sets `If-None-Match` on the final multipart call; that was not checked (UNVERIFIED), so the upload script should use `put-object`. Whether S3 enforces `s3:if-none-match` in an identity policy exactly as the S3 user guide describes (https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html, written for bucket policies and "IAM policy") has not been run here (UNVERIFIED): the first upload is the check, and an `AccessDenied` is a routed repair plus a deployer apply.

Commands afterwards use `--profile scholarchain-pipeline` (`run-bounded-pipeline.sh --profile`, `AWS_PROFILE`), after the console Switch Role to `scholarchain-<env>-operator-pipeline` and `aws login --profile scholarchain-pipeline --region us-east-2`. A 90-minute run plus its upload fits one 4-hour session; three runs do not, so sign in again (Switch back, Switch Role, `aws login`) when the session ends.

### G4: the runtime artifact the services read (final contract, shared with storage-engineer and the main root)

| Item | Value |
|---|---|
| Bucket | the **rag** bucket `scholarchain-<env>-<acct>-rag` (the default of `SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET`; leave it unset in the services) |
| Key | `runtime-artifacts/<operator_run_prefix>/versions/<run id with ':' replaced by '-'>/runtime-subset-<sha256>.json`; produce it with `RuntimeArtifactMain --key-prefix runtime-artifacts/<operator_run_prefix> --bucket <rag bucket>` (the tool appends `/versions/<run id>/runtime-subset-<sha256>.json`). `SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY` is that whole key. |
| Loader (`operator-loader`) | `s3:PutObject` **create-only** on `runtime-artifacts/<operator_run_prefix>/*` (`Null s3:if-none-match = false`; `S3ObjectStore.put` always sends `If-None-Match: *`, single request, so no multipart and no `AbortMultipartUpload`), plus `s3:GetObject`, `GetObjectVersion`, `GetObjectAttributes` on the same prefix (the 412 comparison and HEAD verification) and `s3:ListBucket` with the prefix. It has no unconditional write there. |
| Reader | `s3:GetObject` and list on the same prefix |
| Cleanup | `s3:DeleteObject`, `DeleteObjectVersion`, `GetObject`, `GetObjectVersion`, list and list-versions on the same prefix |
| Main root must | add `runtime-artifacts` to `rag_prefixes` (the runtime read prefixes, `infra/terraform/main.tf`) so the task roles can read it; the runtime boundary already allows S3 reads on every project bucket. The services read by exact key (`_KEY`, `_SHA256`, `_SOURCE_RUN_ID` in the private tfvars/task environment). |

### G11: profile names the scripts use (`scholarchain-deployer-tf`) versus the `aws login` profile

`scripts/plan.sh` and the other Terraform scripts use `--profile scholarchain-deployer-tf` (scripts/plan.sh:66, scripts/README.md:60) while the human signs in with `aws login --profile scholarchain-deployer`. Add this to `~/.aws/config` (the human; placeholders only; use `command -v aws` for the absolute path):

```ini
[profile scholarchain-deployer]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-deployer/<iam-user>

[profile scholarchain-deployer-tf]
credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-deployer --format process
region = us-east-2

[profile scholarchain-pipeline]
region = us-east-2
# after aws login: login_session = arn:aws:sts::<acct>:assumed-role/scholarchain-<env>-operator-pipeline/<iam-user>
```

Per run: console Switch Role to `scholarchain-deployer`, then `aws login --profile scholarchain-deployer --region us-east-2`, then the script with `--profile scholarchain-deployer-tf`. The `-tf` profile only re-reads the cached login on every call (`export-credentials` refreshes the 15-minute credentials until the role session ends), so there is no second login. Check: `aws sts get-caller-identity --profile scholarchain-deployer-tf --region us-east-2` must show `assumed-role/scholarchain-deployer/<iam-user>`.

Could Terraform (provider 6.44.0) read the `login_session` profile directly? **UNVERIFIED, two sources disagree.** The AWS SDK reference table for the login provider lists "SDK for Go V2 (1.x): No" (https://docs.aws.amazon.com/sdkref/latest/guide/feature-login-credentials.html, read 2026-11-08), but the Phase 12D evaluation recorded that the retained source of the pinned provider's SDK (config 1.32.17, credentials 1.19.16) resolves a native `login_session` (`docs/agent-runs/phase-12/evidence/12d-login-path-evaluation/decision-memo.md`, "What the evidence establishes"). Neither was run against a live account. The `credential_process` profile is the safe form because it does not depend on that question (the credential-process provider is long-standing in the same SDK). If the human prefers a single profile, run `aws login --profile scholarchain-deployer-tf` instead and make the read-only check above (`terraform plan` is the real test); fall back to the block above if Terraform reports no credentials.

**Billing-deployer (G16, README only; `scripts/billing` is not edited here).** The billing tooling uses `AWS_PROFILE=scholarchain-billing-deployer` (`scripts/billing/budget_execution.py:267`). The exact login, for the Phase 12D candidate B flow: console Switch Role to `scholarchain-billing-deployer` (as the IAM user `scholarchain-billing-operator`, MFA), then `aws login --profile scholarchain-billing-deployer --region us-east-2` and select the active **role** session; check with `aws sts get-caller-identity --profile scholarchain-billing-deployer --region us-east-2` (expect `assumed-role/scholarchain-billing-deployer/...`). The billing role's maximum session was set in Phase 12D and is not restated here. If its Terraform step reports no credentials, swap the roles of the names so the script's hard-coded name stays valid: `aws login --profile scholarchain-billing-login`, and `[profile scholarchain-billing-deployer]` with `credential_process = /opt/homebrew/bin/aws configure export-credentials --profile scholarchain-billing-login --format process`. `scripts/billing/README.md:129` should quote the first command; that file belongs to the infra-engineer who owns `scripts/billing`.

### G13: the deployer session is 1 hour (unchanged) and the rule that follows

The deployer role keeps `max_session_duration = 3600` (tested). The one hour counts from the **console Switch Role**, not from `aws login`, and `plan.sh` plus the apply of one stage share it. **Rule: do a fresh Switch Role and `aws login` right before each stage and check `get-caller-identity` before starting; if a stage is likely to run into the end of the hour, stop before it, not during it.** Stages that can exceed one hour (durations are estimates from experience, not measurements; none was run): `base-apply` (plan, then the Neptune cluster and instance, NAT, EFS, buckets, vector bucket, KMS, ACM request, then the 322 MB archive upload); `runtime-apply` (ECS services reaching steady state, and, if the validation CNAME is not already in Cloudflare, `aws_acm_certificate_validation` which the provider documents with a long default create timeout, 75 minutes: confirm the certificate is `ISSUED` before starting this stage); the `cleanup` destroy (Neptune, NAT, EFS mount targets and ENIs release slowly) and `push` (four images). An `ExpiredToken` in the middle of an apply leaves the local state as of the last finished resource: sign in again and re-plan; do not edit the state. The operator roles (4 h) have the same rule at their own length.

### Applying (counts replaced for G-DEPLOYER; the earlier sequence above is otherwise unchanged)

* Case A (state still holds the Phase 13 spike set): **Plan: 29 to add, 0 to change, 9 to destroy** (26 + the three pipeline-role resources). Case B: **13 to add, 3 to change, 0 to destroy**. Details: `target/phase14/evidence/14b/replan/deployer-apply-proposal-v2.md`.
* Verification after the apply adds: `aws iam get-role --role-name scholarchain-<env>-operator-pipeline --query 'Role.MaxSessionDuration'` (14400) and `aws iam list-role-policies --role-name scholarchain-<env>-operator-pipeline` (`...-pipeline-data`, `...-pipeline-same-device-login`).

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

Tests run files `tests/gdeployer.tftest.hcl` (13 runs: G4 runtime artifact and the operator-pipeline role), `tests/replan_w5a.tftest.hcl` (28), `tests/deployer.tftest.hcl` (the `spike-emr` runs select that set explicitly; the `p14_*` runs select `phase14-main`) and `tests/default_set.tftest.hcl` (the variable default itself).

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
