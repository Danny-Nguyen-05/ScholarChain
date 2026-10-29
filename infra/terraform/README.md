# ScholarChain Terraform — Phase 12A

This tree currently implements **12A only**: foundation, network, identity,
seven ordinary-S3 zones, six application DynamoDB tables, embedding SQS/DLQ,
and four ECR repositories. It is source and offline validation, **not a deployment**.
No AWS account, profile, region, budget, live resource, or runtime success is implied.
The user approved the recommended local-only choices and asked to be told when an
AWS account becomes necessary.

## Local checks without an AWS account

Use Terraform **1.13.5** and AWS provider **6.44.0**, exact pins throughout.
The provider lockfile is tracked. The initial macOS ARM64 Terraform binary was
obtained from the [official release](https://releases.hashicorp.com/terraform/1.13.5/)
and checked against the published SHA-256 sums over HTTPS; detached-signature
verification was not performed. The provider installer verified HashiCorp's signature.
A developer may install the pinned CLI normally; the recorded run used the isolated
`/tmp/scholarchain-phase12a-infra-toolchain/terraform` executable.

From this directory, with the pinned CLI on PATH:

```bash
terraform init -backend=false -input=false
terraform fmt -check -recursive
terraform validate
terraform test
```

`init` downloads the provider and uses network access; it does not contact AWS
service APIs. `validate` checks the configuration and provider schema. Every test
run uses `mock_provider "aws"` with `override_during = plan` and `command = plan`.
Test identifiers, AZs, budget numbers, URLs and ARNs are explicitly synthetic.
They are never course environment defaults or evidence of AWS access. Mock plans
exercise configuration and invariants, not AWS authorization, quotas, service
availability, cost, state transitions or runtime behavior. Do not replace the
mock provider or change a test to `apply` for this phase.

## Inputs and naming

`environments/course.tfvars` contains confirmed non-secret choices, and deliberately
omits all live-account inputs. The following **have no defaults** and must be
supplied before a real plan can proceed:

| Input | Required decision |
| --- | --- |
| `aws_account_id` | Actual approved account, also enforced by provider `allowed_account_ids` |
| `aws_region` | Region supporting Neptune, S3 Vectors, chosen Bedrock models and EMR |
| `aws_profile` | Local profile name only, configured by the human; never credentials |
| `availability_zones` | Two distinct actual AZ names in the chosen region |
| `deployment_trusted_principal_arn` | Approved existing IAM role/user permitted to assume the separate deployment role |
| `budget_limit_usd` | Positive human-selected total spending ceiling; no amount has been approved |

When 12C is ready, tell the user to create/configure the AWS account and provide
these values and permission for read-only planning. If the user moves the optional
12D spike earlier, that spike needs the account first plus its own written dollar,
instance, duration and teardown approval. Do not run a live plan, create credentials,
or infer a budget from the test fixtures.

Resource names derive from the configurable `project`/`environment` prefix.
Bucket names additionally use the supplied account ID for global uniqueness;
using the same project/environment in another region requires a different
configured environment name because S3 names are global. Table names preserve
logical Phase 7 names behind that prefix. Endpoints derive from the actual region,
not hardcoded service hosts. AWS commercial partition (`arn:aws`) is the supported
scope; GovCloud/China would require a separately reviewed configuration.

| Optional input(s) | Default and rationale |
| --- | --- |
| `project`, `environment`, `course`, `owner` | `scholarchain`, `course`, `CS441`, `danny`; confirmed course scope |
| `expiration_date` | `2026-11-25`, provisional and must be reconfirmed before deployment; tag does not delete anything |
| `additional_tags` | Empty; required tags override collisions; cost-allocation activation is an account action |
| `cleanup_mode` | `false`; ordinary operation keeps native deletion controls enabled |
| `persistent_environment` | `false` for the course; `true` disables object/version intermediate expiration |
| `vpc_cidr` | `10.44.0.0/16`, local course address plan, not an existing network claim |
| `public_ingress_cidrs` | Empty, so no public ingress is authorized by default |
| `service_port`, `neptune_port` | `8080` (Phase 10 container contract), `8182` (Neptune TLS) |
| `interface_endpoint_services` | Empty; NAT supplies HTTPS access, avoiding unnecessary interface endpoint charges |
| `query_session_gsi_name` | `by-idempotency-key`; inject the same name into the storage adapter |
| `enable_query_session_ttl` | `false`; enable only alongside runtime disposable-session TTL configuration |
| `intermediate_retention_days` | `14`; only `intermediates/` objects/versions in curated, graph, rag, artifacts buckets expire |
| `multipart_abort_days` | `7`; remove abandoned multipart upload parts, not completed source/evidence objects |
| `sqs_visibility_timeout_seconds` | `300`; later worker time budgets must be strictly shorter |
| `sqs_max_receive_count` | `3`; bounded deliveries before redrive, separately coordinated with runtime retries |
| `sqs_retention_seconds`, `sqs_dlq_retention_seconds` | Four days / fourteen days; DLQ must retain messages longer than the source |
| `sqs_long_poll_seconds` | `20`; reduce idle polling costs |
| `kms_deletion_window_days` | `7`; recoverable scheduled-deletion window, not immediate key removal |
| `service_secret_arns` | Empty; only explicit existing Secrets Manager ARN references per service |
| `enable_budget_resource` | `false` until account capability and notification recipients are known |
| `budget_notification_emails`, `budget_notification_threshold_percent` | No invented recipients; warning at 80% by default when explicitly enabled |

The optional monthly AWS Budget filters the project tag. It is an **alert**, not
a hard spending stop or a full-stack cost estimate; a multi-month window can incur
charges across multiple monthly limits. The human's total budget and 7–10 day
working duration still need the 12C estimate and experiment controls. Do not claim
the configuration fits an unselected budget. Budget tags/filter activation and
permissions are unverified until an account is available.

## Module boundaries and security controls

- `foundation`: required tags and optional scoped budget notification.
- `network`: two AZs, separate public/application/data subnet pairs, one NAT in
  the first public subnet, S3/DynamoDB gateway endpoints on application/data route
  tables. Application subnets use NAT; data subnets have no internet default route.
  The one-NAT choice reduces cost but creates a single-AZ egress dependency and
  possible cross-AZ transfer charges. No subnet auto-assigns public instance IPs.
  The default SG is emptied. Role SG references allow ALB → query-api → graph /
  semantic, with graph → Neptune. External application egress is TCP 443. Optional
  interface endpoint SG ingress admits only the service role groups on TCP 443.
  Neptune can reach S3 through its managed prefix list on TCP 443. EMR members
  permit dynamic Hadoop/Spark RPC only within the EMR SG. Public ingress is empty;
  when configured it allows HTTPS 443 to the ALB group only. Certificate/listener
  decisions belong to 12B; no HTTP fallback has been authorized. Gateway endpoints
  retain AWS's default endpoint policy: it does not grant identity permissions;
  the scoped IAM and bucket/table policies remain the authorization boundary.
- `identity`: one rotating project data CMK, separate task and execution roles per
  service, Neptune S3 loader role, EMR EC2 data role/profile, EMR service role, and
  a separate deployment role trusting one configured principal. Runtime policies
  use exact actions and existing 12A resource references. The graph task role has
  **no write action**, including no graph-bucket writes. The Neptune loader trusts
  `rds.amazonaws.com`, reads the graph bucket only, and decrypts the project CMK.
  EMR Hadoop/Spark workloads use S3, not DynamoDB. The EMR data policy therefore
  has no DynamoDB action; separately operated storage loaders require their own
  scoped identity, and EMR cannot write query-session or evidence audit records.
  ECS execution roles pull only their own repository, write only their own service
  log streams, and can inject only explicitly configured secret ARNs. Referenced
  secrets must use AWS-managed encryption or this project's key; a secret using
  another CMK needs an explicitly reviewed extra key grant. No secret-version
  data source or secret-value resource exists.
- `datalake`: seven versioned buckets, project CMK encryption, bucket keys,
  owner-enforced ACLs, all four public-access blocks and TLS deny policies.
  Only explicit intermediate prefixes expire; raw data, reports, logs and normal
  evidence/version prefixes are not expired by the course lifecycle.
- `dynamodb`: exactly RunLedger (`runId`, `stageKey`), EntityLinkCache
  (`entityType#normalizedKey`, `policyVersion#sourceId`), QuerySession (`queryId`,
  `itemType`), EvidenceBundle (`evidenceId`, `part`), ArtifactRegistry (`artifactId`,
  `version`), ResearcherMetricCache (`researcherId`, `windowId`). All use on-demand,
  project-CMK encryption, PITR and native deletion protection by default. Only
  QuerySession has the ALL-projection `idempotencyKey` GSI and optional `expiresAt`
  TTL. The literal attribute names and TTL semantics follow `modules/storage/README.md`.
- `messaging`: encrypted work queue and DLQ, finite visibility, bounded redrive,
  source-restricted redrive policy and universal insecure-transport denies.
- `runtime`: ECR only. Four immutable, scan-on-push, CMK-encrypted repositories.
  ECR immutability prevents overwriting a tag; **Git-SHA tag naming is a Phase 13
  publication-script responsibility**, not enforced by ECR itself.

IAM exceptions are deliberate and individually scoped:

| Pattern | Reason and boundary |
| --- | --- |
| `ecr:GetAuthorizationToken`, `Resource=["*"]` | ECR authentication does not support resource-level grants; subsequent pull actions are restricted to the one service repository |
| KMS key-policy `Resource="*"` | In a KMS key policy this denotes that key; exact administrative/use actions delegate to this account's IAM, not arbitrary principals or keys |
| `s3:*` / `sqs:*`, `Principal="*"` in TLS policies | Universal **Deny** for insecure requests, covering all present/future operations; no wildcard action occurs in an Allow statement |
| `<owned-bucket-arn>/*` | Object actions need object ARNs; runtime components see only their listed purpose buckets, not every bucket in the account |
| `<own-log-group>:log-stream:*` | A service can create/write its own dynamic log streams, not other log groups |
| Same-account ECS SourceArn suffix `:*` | Same-account ECS task trust constraint; this is a trust condition, not an AWS resource permission grant |

These grants are intentionally incomplete until their owning resources exist:
**EMR service control-plane permissions are absent**, pending 12B runtime/network
selection. **Deployment role is trust-only**, with no provisioning permissions;
its permission policy requires the reviewed full-tree plan and human deployment
gate. Neptune runtime read/job-loader permissions, S3 Vectors and Bedrock grants
must be bound to actual resources/model configuration in 12B. No future-resource
wildcard or fabricated Neptune resource ID/model ARN was introduced to fill gaps.
Service log groups are 12B work; their expected names are `/<project>-<environment>/<service>`.
This is not an apply-ready infrastructure stack.

## State and cleanup design

The course root has **no remote backend block** and uses local state. State, backup
state, provider caches, local variable files and plans are ignored by Git. A local
state file can contain sensitive data in plaintext: protect it using the user's
local account/storage controls, never print or copy it into evidence, and keep
any backup outside tracked files. `.terraform.lock.hcl` contains provider checksums
and remains tracked.

`modules/foundation/bootstrap` is a tiny **unreferenced child module** implementing
the accepted optional S3 + DynamoDB locking design: versioned private state bucket
with AWS-managed AES256 encryption and TLS enforcement, and an encrypted on-demand
`LockID` String-key table with PITR/native deletion protection. Both have static
`prevent_destroy=true`. It creates **no resources unless a future separately
reviewed bootstrap root calls it and an authorized human gate permits apply**.
It is tested solely through the mock provider. The six application tables are
unchanged; this optional state-lock table is separate and never part of their root.

A future bootstrap root must supply unique names, the five required tags and a
separate backend administration identity. Restrict state-object read/write and
lock-table actions to that identity, keep bootstrap state separate, and review the
migration before any backend change. No bootstrap, apply or state-migration command
has been run here. Do not migrate simply by editing the current backend.

[HashiCorp's S3 backend documentation](https://developer.hashicorp.com/terraform/language/backend/s3)
now deprecates DynamoDB locking and supports `use_lockfile=true` for native S3
locking. The child module preserves the accepted compatibility design, but any
actual remote-state migration must select/review the locking method; the DynamoDB
component can be omitted if native S3 locking is approved. No silent design change
or state migration is performed in 12A.

`cleanup_mode=true` releases native DynamoDB deletion protection and allows ECR
force deletion/S3 force-empty settings in a future reviewed cleanup plan. **It is
configuration, not authorization**, and is false by default in the course tfvars.
S3's `prevent_destroy=true` is a literal Terraform lifecycle guard and remains on
in every mode. Terraform cannot make that setting conditional. Bucket destruction
therefore additionally requires a human-reviewed source change removing the guard,
an inventory/backups decision and the phase's human gate; normal cleanup mode alone
will not destroy the buckets. Resource addresses never switch between protected
and unprotected variants, avoiding accidental replacements on a mode toggle.
Cleanup/migration/deployment scripts belong to Phase 13 and are not authored here.

## Test coverage and manual security checklist

`tests/phase12a.tftest.hcl` asserts hand-written requirements: seven data zones;
private/encrypted/versioned/owner-enforced buckets and TLS; exact six table keys,
sole GSI and opt-in session-only TTL; PITR/on-demand/deletion protection; encrypted
bounded SQS redrive and longer DLQ retention; four immutable/scanned ECR repos;
required tags; two-AZ subnet separation and SG role ports; no public-IP or data
internet route; cost-aware endpoint/NAT defaults; scoped runtime/execution policies;
EMR has no DynamoDB action; data-route isolation counts actual `aws_route.default`
instances targeting the data table, using distinct mock route-table IDs rather than
mocked `aws_route_table.route` contents. Tests require all authored routes to remain
in that single collection and forbid standalone/inline route declarations, so an
additional route cannot silently bypass the resource-backed isolation assertion;
graph-reader no-write invariant; no unconfigured secret grants; exact deployment
principal and ECS same-account trust; cleanup/persistent mode behavior; per-service
secret references; invalid account/budget/AZ/secret inputs; optional state bootstrap
protections and required budget subscribers. It does not perform a live AWS plan.

Manual review of this 12A source checks: (1) IAM Allow action/resource scope and
written exceptions above; (2) no public bucket/table/database or CIDR data ingress;
(3) S3/DynamoDB/SQS/ECR encryption and KMS rotation; (4) separate runtime/deployment
roles and graph reader no write; (5) default deletion controls and explicit cleanup;
(6) no inline secrets, credentials, secret-value resources or secret-version reads.
Neither Trivy nor Checkov was installed at preflight. This manual review plus
Terraform schema/feature checks is the approved fallback, **not an independent
security approval or scanner result**. Security/API behavior must still be reviewed
independently and checked with the actual account in later gates.

## Deferred scope and provenance

12B owns Neptune, S3 Vectors, EMR, ECS/Fargate/ALB/discovery, autoscaling, log groups,
dashboards and alarms. Their directories are not filled with speculative code in
12A. 12C owns the real non-destructive plan/checksum, pricing against the actual
budget, and full security preparation. 12D is the separately approved optional
Spark compatibility experiment. Neptune sizing/pricing, EMR release/instance
selection and Scala 2.13 compatibility remain unselected/unverified; use the Phase
6A memo in `docs/agent-runs/phase-06/evidence/6a/emr-compatibility.md`. Phase 10 live
service-store composition is also a later deployment prerequisite; its offline
synthetic mode is not evidence of working AWS services.

Step Functions, EventBridge, OpenSearch, Glue catalog, extra indexes/services and
CI workflows are omitted under the approved lean phase plan. **The course Phase 12
workflow list explicitly names Step Functions; the plan's omission is a disclosed
scope discrepancy requiring human/instructor resolution before full phase closure,
not proof the course waived it.** Required operational scripts in the course's
Phase 12 section are assigned to Phase 13 by this work order. No course/instructor
approval of those schedule/scope deviations is implied.

Primary references read for authoring (AWS provider **6.44.0**, versioned links):

- [Course requirements](https://github.com/0x1DOCD00D/ScholarChain/blob/main/README.md#phase-12-create-the-aws-infrastructure-in-terraform).
- [Budgets](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/budgets_budget),
  [VPC endpoints](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/vpc_endpoint),
  [KMS key](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/kms_key),
  [IAM role](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/iam_role).
- [S3 bucket](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/s3_bucket),
  [S3 lifecycle](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/s3_bucket_lifecycle_configuration),
  [DynamoDB table](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/dynamodb_table),
  [SQS queue](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/sqs_queue),
  [ECR repository](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/ecr_repository).
- [Native S3 Vectors bucket](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/s3vectors_vector_bucket),
  [Native S3 Vectors index](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/s3vectors_index).
  Both resource schemas exist in the installed pinned provider, including encryption
  and tags; no CloudFormation workaround is needed. Resources themselves are 12B.
- [Neptune](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/neptune_cluster),
  [EMR managed scaling](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/emr_managed_scaling_policy),
  [ECS application autoscaling](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/appautoscaling_policy)
  were consulted for boundary/dependency compatibility, not authored in 12A.
- [Neptune loader trust/encryption](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-IAM-CreateRole.html).

Registry HTML required JavaScript in this environment. The versioned provider
Markdown sources at `https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.44.0/website/docs/r/`
and installed provider schema were used to verify the documented fields.
