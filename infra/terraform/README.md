# ScholarChain Terraform — Phase12A–12C

This tree authors the12A foundation plus12B Neptune, native S3 Vectors, bounded EMR,
ECS/Fargate/discovery/HTTPS ALB, autoscaling, observability, and a functional
Step Functions embedding-dispatch workflow. Phase12C adds the selected control
repairs and a real read-only plan, **not a deployment or an apply-ready runtime**.
The user supplied account/profile inputs privately, selected Ohio (`us-east-2`)
and a shared USD200 project ceiling before credits. Nothing was applied or called
a paid model. Neptune, EMR and ECS service activation remain off pending the
explicit prerequisites below. Budget creation/notification and Cost Explorer
activation remain separate pre-spend account setup gates.

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
| `budget_limit_usd` | USD200 shared project ceiling before credits; no deployment/spend approval implied |

The account is now configured and12C read-only planning was explicitly authorized.
Live values remain outside Git; never inspect credential files or print session
credentials. The optional12D spike still needs its own written dollar, instance,
duration and teardown approval plus active pre-spend monitoring. The selected
read-only plan authorizes no apply, credential creation or paid model/Cost Explorer
request. Do not infer live inputs or spending authority from mock fixtures.

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
charges across multiple monthly limits. The selected USD200 ceiling is shared
across all cloud phases, including early spikes, optional9C smoke and retained
evidence. Cost November15–24 as the base case and November11–24 as the upper case;
actual deployment/runtime remains separately approved. The default plan keeps this
budget disabled: the early account-wide monitoring bootstrap is a separate,
human-approved Terraform work order, and must not depend on project tags already
being active. Do not duplicate or manage one budget from two Terraform states.
Pass the subscriber address privately through `TF_VAR_budget_notification_emails`
or an ignored local tfvars file; never put it in committed course.tfvars or logs.
State, plan binaries/JSON and unredacted outputs remain outside Git/evidence.
Billing reports lag; runtime/capacity/request limits enforce each run, not a
Cost Explorer query. No cost-fit or active-notification claim follows from a plan.

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

## Subphase12B configuration and deployment prerequisites

The user accepted the recommendations in the coordinator's
`docs/agent-runs/phase-12/evidence/12b/step-0-answers.md`. All new inputs are in
`phase12b-variables.tf`, with local-only choices in `environments/course.tfvars`.
Activation flags do not authorize any cloud action; the human gates still apply.

| Area | Authored behavior and required later input |
| --- | --- |
| Neptune | One private serverless writer, IAM authentication, project CMK, audit export, subnet/cluster/instance parameter groups,7-day backups,1–2.5NCU, deletion protection and final snapshot outside cleanup. `neptune_enabled=false` until the user selects `neptune_engine_version` and matching `neptune_parameter_family`; no implicit latest engine or regional support claim. |
| Vectors | Native vector bucket and exactly five float32 indexes,256 dimensions,cosine,project CMK,TLS Deny. Names match `VectorIndexes` in `modules/storage/.../Phase7Configs.scala:86-93`; planned dimension/metric match `modules/rag/README.md:57-61`. Every index marks exactly `textS3Uri` non-filterable, matching `VectorAdapterConfig` (`Phase7Configs.scala:67`) and live ingest/query GetIndex preflight. Changing dimension/metric/metadata requires an explicitly reviewed index migration. Literal `prevent_destroy=true` remains on bucket AND indexes even in cleanup. |
| EMR | Disabled by default. One primary plus one core, at most two task nodes, on-demand only, managed scaling uses1–3 worker instances (primary excluded), one-core ceiling, idle termination1800s, bounded instance choices,encrypted local disks/S3 and in-transit TLS. |
| ECS | One cluster with Container Insights and private DNS. Four Fargate service/task definitions are declared behind `runtime_enabled=false`. Default active task shape is512CPU/1024MiB. HTTP services min1/max2 and worker min1/max4. Each HTTP service has CPU target60%; worker uses visible SQS messages divided by RunningTaskCount, target10/task. No service OR scaling target exists while disabled. |
| Ingress | No HTTP listener. HTTPS443 requires an existing same-account/region ACM ARN and approved CIDRs. Certificate remains unset and CIDRs empty. ALB access logging is intentionally OFF because the existing logs bucket uses SSE-KMS; ALB/S3 server access logs require an SSE-S3 destination. Ordinary application/EMR logs can still use that bucket. |
| Workflow | Standard Step Functions dispatches one serialized EmbeddingWorkItem to the fixed embedding queue, with120s overall timeout,20s tasks, two retries and fixed DLQ failure routing. The separate `embedding-producer` execution identity trusts only this exact state machine/account and has queue-only SendMessage plus CMK rights. The Phase13 pipeline invokes it; no caller identity/StartExecution grant or production enqueue caller is invented here. |
| Bedrock | Embedding participants only may InvokeModel on configured TitanV2 foundation-model ARN. `synthesis_model_id=null` means no query-api invocation grant. Model IDs are configurable, never wildcard; actual regional availability/model access is unverified. |
| Logs/alarms | Service and Neptune audit groups retain7 days using CloudWatch's default service encryption. Queue age>300s, API/graph p95>5s, API errors>5%; missing data remains missing. SNS targets default empty; alarm resources alone do not notify a person. |

**EMR runtime and permissions remain unresolved.** The Phase6A compatibility memo
(`docs/agent-runs/phase-06/evidence/6a/emr-compatibility.md`) records that the
repository's Scala3 / spark-sql_2.13 job is not proven on stock EMR Scala2.12.
The user chose offline module authoring before the preferred12D spike.
`emr_config.enabled=true` requires an explicit release label, reviewed bootstrap
S3 URI, TLS certificate bundle URI, proven runtime reference and acknowledgment.
It also requires nonempty `emr_service_policy_json`; the12A service role is trust-only
without it. The policy rejects wildcard actions and wildcard ARN partition,
service, region or account segments; only concrete EC2 Describe actions may use
literal `Resource=["*"]`, because those read APIs do not support resource scoping.
Concrete region/account ARN prefixes may retain a reviewed future-resource suffix
such as `instance/*`; that does not authorize EMR activation. Selected control-plane
permissions still require a concrete security review before a live runtime. No broad managed policy
is silently attached. The synthetic test policy permits DescribeInstances only:
it is a configuration fixture, deliberately **not enough to launch a real cluster**.
Real IAM effectiveness, service connectivity, certificates and runtime are unverified.

Private EMR service communication uses SG references on8443/9443; the existing
HTTPS443 egress reaches AWS/S3. All route and route-table resources remain inside
`modules/network` (R1); route-table IDs are not exported. The selected runtime's
full egress and EMR-managed SG behavior must be verified before live activation.

**N1 output commit rationale:** Hadoop/EMRFS rename and Spark temporary-output
cleanup can require s3:DeleteObject. `emr_output_prefixes` defaults to `pipeline/`
in curated,graph,artifacts,reports only. Configure job output URIs under those
prefixes. The role cannot delete raw data, logs, arbitrary bucket roots or versions;
versioned deletes create recoverable delete markers. Output puts retain the12A
scope. EMR continues to have **no DynamoDB action**, including QuerySession and
EvidenceBundle. Real output commit behavior must still be checked in12C/12D.

**Current service code cannot run a live AWS composition.**
`modules/services/.../ServiceMains.scala:42-44` accepts unconfigured and
explicit offline-synthetic modes only. Endpoints/table/vector/queue names are
exposed through `phase12b_controls.deployment_contract` for future adapter composition;
no unimplemented environment variable name is passed as though the application
consumed it. Task environments wire existing HTTP/region/downstream URI contracts,
existing secret bindings by ARN, and deliberately retain
`SCHOLARCHAIN_SERVICE_MODE=unconfigured`. `runtime_enabled` additionally requires
`runtime_composition_verified`, an immutable40-character image revision, Neptune,
auth-secret references for all four services, query's outgoing token reference,
and graph-service's shared `SCHOLARCHAIN_GRAPH_CURSOR_KEY` by ARN. The shared
cursor key prevents autoscaled replicas from rejecting each other's cursors.
These are configuration guardrails, **not evidence of a live working artifact**.
Phase13/14 must route actual live composition to the service owner and update the
mode contract under review before deployment. Auth hashes must be distinct and the
outgoing internal token must match its configured hash; Terraform never reads these
values. Acknowledgment alone does not implement those checks. Readiness remains503
for the current unconfigured artifacts. Writable ephemeral `/tmp` supports Java
without making the container image root writable. Image CPU architecture must
match task X86_64; Phase13 packaging owns that validation.

## Observability contract and honest missing data

The dashboard separates task counts, utilization, queue depth/age, EMR nodes,
Neptune, DynamoDB, API percentiles, graph/vector/LLM latency, usage/errors and
workflow failures/timeouts. Native EMR charts use300s intervals; Container Insights
provides RunningTaskCount for worker metric math. The worker never scales to zero
when activated, so a missing divisor does not deadlock scale-out; the metric math
also floors a zero divisor to one.

Current `/metrics` endpoints are Prometheus. No CloudWatch application publisher
exists yet. The declared application namespace defaults `ScholarChain/Application`
with exact dimension `Service=<service-name>` and the following **future publisher
contract**, not a claim about emitted names today:

| Metric | Value/statistic required |
| --- | --- |
| HttpRequests / HttpServerErrors | Interval request/5xx counts; publish zero errors for active intervals; Sum yields the alarm's error percentage. |
| RequestLatencySeconds | Raw/distribution latency samples for query-api and graph-service; support CloudWatch p50/p95/p99, not a percentile-of-percentiles. |
| VectorQueryLatencySeconds / VectorClientErrors | Semantic service latency samples / interval error counts. |
| LlmLatencySeconds / LlmInputTokens / LlmOutputTokens | Query service model-call latency samples / observed interval token counts. |
| LlmEstimatedCostUsd | Explicitly computed publisher estimate using configured current model rates; absent until those inputs exist. Tokens are not silently converted to cost here. |

Until Phase13/14 supplies and verifies that publisher, these panels/alarms remain
empty or INSUFFICIENT_DATA. They are not measured performance, zero errors or an
operational alert. No PutMetricData wildcard grant or collector image is invented.
DynamoDB charts use ReadThrottleEvents/WriteThrottleEvents with TableName; the
ThrottledRequests metric would instead require Operation and is deliberately absent.
Neptune audit log export is precreated with7-day retention, avoiding default
indefinite retention. Step Functions execution-data CloudWatch logging is off to
avoid copying manifest/document payloads; native execution metrics remain charted.

## Deferred scope and provenance

12C owns the real non-destructive plan/checksum, regional quota/engine/model checks,
pricing against the actual user budget, and full security preparation.12D remains
a separately approved runtime experiment; no spike root or live action is authored
here. Account/profile inputs, Ohio AZs and the shared budget were supplied for
read-only12C planning; certificate, image publication, actual live service access,
quotas and runtime prerequisites remain separately gated. Deployment roles remain
separate and not granted generic provisioning rights.

Step Functions is now present following the user's12B answer, addressing N8's
previous omission. This does not constitute instructor acceptance of the whole
workflow or waive any course obligation. EventBridge,OpenSearch,Glue catalog,
extra services/indexes and CI workflows remain omitted because they are not used.
Required operational scripts are assigned to Phase13 by this work order. No
course/instructor approval of that schedule deviation or Codex-led workflow is implied.

N2's queue producer identity and functional dispatch path are authored; its
production caller remains Phase13. N5 is resolved by explicitly disabling ALB
access logs. N3's general12A mock bucket/table ARN differentiation, N4's optional
loader/KMS test extension and N6's cosmetic key-action cleanup are not repaired.
The existing B1/B2 protections and N7's post-final-freeze gate order are retained.

`tests/phase12b.tftest.hcl` exercises enabled and disabled mock paths, actual
Neptune privacy/protections, exact vector schema/metadata/resource scoping,
read-only graph IAM, bounded autoscaling and EMR capacity, fixed-queue workflow,
CMK encryption context and explicit input rejection. Separate scratch mutations
prove security/metric regressions fail assertions without changing repository
source. Mock feature checks do not establish live authorization or cost fit.

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
  and tags; the12B implementation uses them directly.
- [Neptune](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/neptune_cluster),
  [EMR managed scaling](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/emr_managed_scaling_policy),
  [ECS application autoscaling](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/appautoscaling_policy)
  were consulted for boundary/dependency compatibility, not authored in 12A.
- [Neptune loader trust/encryption](https://docs.aws.amazon.com/neptune/latest/userguide/bulk-load-tutorial-IAM-CreateRole.html).

Registry HTML required JavaScript in this environment. The versioned provider
Markdown sources at `https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.44.0/website/docs/r/`
and installed provider schema were used to verify the documented fields.

Additional12B primary references:

- [Neptune parameter families](https://docs.aws.amazon.com/neptune/latest/userguide/parameter-groups.html),
  [serverless capacity bounds](https://docs.aws.amazon.com/neptune/latest/userguide/neptune-serverless-capacity-scaling.html),
  [read-only data actions](https://docs.aws.amazon.com/neptune/latest/userguide/iam-dp-actions.html).
- [EMR private security groups](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-man-sec-groups.html),
  [EMR service-role requirements](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-iam-role.html),
  [EMRFS S3 permissions](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-emrfs-iam-roles.html).
- [Worker backlog metric math](https://registry.terraform.io/providers/hashicorp/aws/6.44.0/docs/resources/appautoscaling_policy),
  [ECS queue scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-autoscaling-queue.html).
- [Step Functions fixed SQS integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-sqs.html),
  [execution-role CMK encryption context](https://docs.aws.amazon.com/step-functions/latest/dg/encryption-at-rest.html).
  The latter explicitly warns against ViaService on an execution-role grant; only
  the separate SQS grant uses ViaService here.
- [DynamoDB metric dimensions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html),
  [EMR native metrics](https://docs.aws.amazon.com/emr/latest/ManagementGuide/UsingEMR_ViewingMetrics.html),
  [Neptune log publication](https://docs.aws.amazon.com/neptune/latest/userguide/cloudwatch-logs.html).

For cost comparison only, the public Ohio offer file checked during12B lists
standard `db.t4g.medium` atUSD0.093/hour and Serverless atUSD0.1608/NCU-hour.
At1–2.5NCUs that isUSD0.1608–0.402/hour for compute alone, before storage,I/O,
network and other services. These are retained12B comparison prices, not the
12C dated estimate or a free-tier eligibility claim. Ohio is now selected for
read-only planning; revalidate each price for the actual activation window. AWS discourages
small T-family instances for openCypher/performance testing; accepted sizing is
Serverless with live revalidation deferred to12C.
[Regional public price file](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonNeptune/current/us-east-2/index.json),
[AWS sizing/cost guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/neptune-well-architected-framework/cost-optimization-pillar.html).

B3 CMK control: the key policy grants only `kms:Decrypt` to
`indexing.s3vectors.amazonaws.com`, restricted to the configured account, the
project vector-bucket ARN plus its `/index/*` descendants, and the documented
S3 Vectors encryption-context keys. `Resource="*"`
in this key policy means this CMK only; the account-root delegation is unchanged.
[AWS S3 Vectors encryption requirements](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-data-encryption.html).


## Phase12C control repairs and plan boundary

The selected follow-ups N9/N10/N11/N12/N14/N17 are exercised by the new mock
requirements in `tests/phase12c.tftest.hcl`; original12A/12B safety runs remain.

- N9: EBS CMK permissions belong to the EMR **service role**, not the EC2 instance
  role. When EMR is explicitly activated, a separate policy permits only this
  project's key: Decrypt, DescribeKey, GenerateDataKeyWithoutPlaintext and the
  explicit ReEncryptFrom/ReEncryptTo actions. CreateGrant is separate and requires
  `kms:GrantIsForAWSResource=true`. EMR-ready service output depends on this policy.
  The EC2 data role retains its S3 key-use scope and still has no DynamoDB access.
- N10: malformed or wildcard ARN service/region/account prefixes are rejected,
  including `arn:*` and `arn:aws:ec2:*:*:instance/*`. Concrete future-ID suffixes
  remain subject to activation review; only concrete EC2 Describe actions get the
  literal global-resource exception. A mock Describe-only fixture is not a usable
  real provisioning policy.
- N11/N12: dashboard construction omits the EMR and Neptune widgets when their
  source is null. When enabled, Neptune native client/server error rates use
  DBClusterIdentifier and Average. DynamoDB conditional-write failures use
  TableName/Sum; successful-request latency uses TableName/Operation/Average,
  with seven adapter-relevant operations for each of six tables. Missing telemetry
  and application publisher requirements are unchanged.
- N14: the workflow checks IsPresent before IsString in an ordered And condition;
  a missing workItem reaches InvalidWork rather than evaluating a missing string.
- N17: service indexing decrypt is allowed for exactly this project's vector
  bucket and its index descendants; principal, action, account and encryption
  context restrictions remain strict. Actual service-supplied SourceArn and KMS
  behavior still require the Phase14 smoke test.

The default read-only plan proposes171 managed creates, zero changes, zero destroys
and zero replacements, with Neptune, EMR, ECS runtime and the budget resource off.
The binary, JSON and private input file are outside Git. A fresh-state plan proves
no route replacements are proposed; it is not a resource inventory or proof of
IAM effectiveness. Policies that depend on future ARNs are honestly unknown until
apply; source and mock contracts establish their intended scopes.

N15 remains disclosed: ALB-to-query and internal query-to-graph/semantic traffic
uses HTTP inside the VPC. N16 remains deferred: Phase13 must supply authorized
loader/writer/StartExecution callers; no principal here can start a Neptune loader
or write pipeline tables as a pipeline loader. Live composition, application metric
publication, EMR runtime compatibility, actual model access and spend authorization
are not established by this plan. N13 and optional N3/N4/N6 were not expanded.

[EMR service-role EBS encryption](https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-encryption-enable.html),
[EBS minimum key actions and grant condition](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-encryption-requirements.html),
[Neptune native metrics](https://docs.aws.amazon.com/neptune/latest/userguide/cw-metrics.html),
[DynamoDB metric dimensions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html),
[Step Functions ordered IsPresent/IsString guard](https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html).
