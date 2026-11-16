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
| `synthesis_provider`, `embedding_provider` | `anthropic`, `voyage` (repair round 3: the Anthropic API and Voyage AI are the primary providers; `bedrock` selects Amazon Bedrock for that purpose; see "Repair round 3: Anthropic API and Voyage AI providers") |
| `synthesis_inference_profile_id` / `_regions`, `embedding_inference_profile_id` / `_regions` | Unset, and only with the matching provider `bedrock`; only for a model Bedrock serves through a cross-region inference profile (see "Bedrock inference profiles"); without them the Bedrock grant is the single in-region foundation-model ARN |
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
  The VPC's default SG is no longer managed (repair round 1, F2: adopting it needed a deployer permission that could not be scoped); nothing is a member of it. Role SG references allow ALB → query-api → graph /
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
force deletion and S3 / S3 Vectors force-empty settings in a reviewed cleanup plan. **It is
configuration, not authorization**, and is false by default in the course tfvars.
**USD 25 replan (W4, user decision 5):** the data lake buckets (`modules/datalake`) and the
S3 Vectors bucket and indexes (`modules/s3vectors`) no longer carry `prevent_destroy`; the
session ends with a full purge. Their deletion is possible only through the reviewed cleanup
path: `force_destroy = cleanup_mode` (false by default, so a destroy plan stops at a non-empty
bucket), switched on by `scripts/cleanup.sh --prepare` and applied through `deploy.sh --stage
cleanup-prepare`, then removed by the token-bound destroy plan. The optional state-backend
bootstrap module (`modules/foundation/bootstrap`, unreferenced) keeps its `prevent_destroy`
guards: the Terraform state backend is the one thing the purge preserves. The KMS key is
scheduled for deletion with `kms_deletion_window_days` (7, free while pending). Resource
addresses never switch between protected and unprotected variants, avoiding accidental
replacements on a mode toggle. The ordered teardown is in `scripts/README.md`.

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
| Vectors | Native vector bucket and exactly five float32 indexes,256 dimensions,cosine,project CMK,TLS Deny. Names match `VectorIndexes` in `modules/storage/.../Phase7Configs.scala:86-93`; planned dimension/metric match `modules/rag/README.md:57-61`. Every index marks exactly `textS3Uri` non-filterable, matching `VectorAdapterConfig` (`Phase7Configs.scala:67`) and live ingest/query GetIndex preflight. Changing dimension/metric/metadata requires an explicitly reviewed index migration. Since the USD 25 replan (W4) there is **no `prevent_destroy`** on the vector bucket or the indexes; `force_destroy` on the bucket follows `cleanup_mode`, so they can be deleted only after the cleanup preparation. |
| EMR | Disabled by default. 13C: one primary plus one core on `emr-7.8.0` with applications `["Hadoop"]` only and the portable Spark runtime installed by `scripts/emr/bootstrap.sh`; **no task nodes and no managed scaling unless tfvars enable them**, at most one task node, `m5.xlarge` only (G3/G6 caps below); on-demand only; idle termination at most 900 s; encrypted S3, local disks and EBS; **in-transit TLS disabled** (disclosed limitation below); an encrypted EFS staging file system (G1 option ii). See "Phase 13C" below. |
| ECS | One cluster with private DNS and Container Insights (`container_insights_enabled`, default true; the USD 25 cap tfvars sets false, which also removes the worker backlog policy because RunningTaskCount exists only with Container Insights). Four Fargate service/task definitions are declared behind `runtime_enabled=false`. Default active task shape is512CPU/1024MiB; `service_capacity` also accepts cpu 256 with memory 1024 or 2048 (0.25 vCPU / 1 GiB for the cap plan). HTTP services min1/max2 and worker min1/max4. Each HTTP service has CPU target60%; query-api can also track ALB requests per target when `query_requests_per_target_target` is set (Phase 15 P41, below); worker uses visible SQS messages divided by RunningTaskCount, target10/task. No service OR scaling target exists while disabled. |
| Ingress | No HTTP listener. HTTPS443 requires an ACM certificate (an existing same-account/region ARN in `https_certificate_arn`, or one Terraform requests for `api_domain_name`; exactly one of the two, see "Phase 14B replan W5b") and approved CIDRs. Certificate remains unset and CIDRs empty. ALB access logging is intentionally OFF because the existing logs bucket uses SSE-KMS; ALB/S3 server access logs require an SSE-S3 destination. Ordinary application/EMR logs can still use that bucket. |
| Workflow | Standard Step Functions dispatches one serialized EmbeddingWorkItem to the fixed embedding queue, with120s overall timeout,20s tasks, two retries and fixed DLQ failure routing. The separate `embedding-producer` execution identity trusts only this exact state machine/account and has queue-only SendMessage plus CMK rights. The Phase13 pipeline invokes it; no caller identity/StartExecution grant or production enqueue caller is invented here. |
| Bedrock | Embedding participants only may InvokeModel on configured TitanV2 foundation-model ARN. `synthesis_model_id=null` means no query-api invocation grant. Model IDs are configurable, never wildcard; actual regional availability/model access is unverified. |
| Logs/alarms | Service and Neptune audit groups retain7 days using CloudWatch's default service encryption. Queue age>300s, API/graph p95>5s, API errors>5%; missing data remains missing. SNS targets default empty; alarm resources alone do not notify a person. |

**EMR runtime (decision 12-10, ported in Phase 13C) and permissions.** The Phase6A compatibility memo
(`docs/agent-runs/phase-06/evidence/6a/emr-compatibility.md`) records that the
repository's Scala3 / spark-sql_2.13 job is not proven on stock EMR Scala2.12; the
12D spike proved a bootstrap-installed portable Spark 3.5.4 / Scala 2.13.14 runtime on
Java 17, and 13C ported that configuration to `modules/emr` (section "Phase 13C" below).
`emr_config.enabled=true` requires a proven runtime reference, the bootstrap S3 URI and
its sha256, the runtime archive S3 URI (G5) and the job JAR S3 URI and sha256, all in the
project artifacts bucket, and acknowledgment (`runtime_verified`).
It also requires nonempty `emr_service_policy_json`; the12A service role is trust-only
without it. The policy rejects wildcard actions and wildcard ARN partition,
service, region or account segments; only concrete EC2 Describe actions may use
literal `Resource=["*"]`, because those read APIs do not support resource scoping.
Concrete region/account ARN prefixes may retain a reviewed future-resource suffix
such as `instance/*`; that does not authorize EMR activation. Selected control-plane
permissions still require a concrete security review before a live runtime. No broad managed policy
is silently attached. The synthetic test policy permits DescribeInstances only:
it is a configuration fixture, deliberately **not enough to launch a real cluster**.
Real IAM effectiveness, service connectivity and runtime are unverified.

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

**State of the service composition (updated in repair round 1, F1).** `modules/services` now has an explicit `SCHOLARCHAIN_SERVICE_MODE=aws`
(`AwsComposition`, `AwsConfig`; contract in `modules/services/README.md`, "Live AWS mode"), composed only from the existing storage and rag
adapters. graph-service's Neptune reader wiring is implemented in `modules/services` and `modules/storage`, and **nothing is live-verified**. `modules/runtime/compute.tf` sets the mode to `aws` only when the runtime is enabled **and**
`runtime_composition_verified` is true (the human acknowledgment, never set in a committed tfvars); otherwise the tasks keep
`SCHOLARCHAIN_SERVICE_MODE=unconfigured` and receive none of the aws variables. In aws mode each role gets exactly the variables of that
contract that have a Terraform source: the six table names and the QuerySession index (all roles); Neptune reader endpoint and graph bucket
(graph-service); vector bucket, index, metric, rag bucket and the embedding model, version and dimension (semantic-service); additionally the
profile-or-model synthesis ID, its version, the evidence and audit prefixes (query-api); queue and DLQ URLs, text prefix and the SQS visibility
and long-poll seconds (embedding-worker). Secrets stay ARN bindings in `secrets`. Optional variables with no Terraform source (timeouts,
`SCHOLARCHAIN_QUERY_SESSION_TTL_SECONDS`, `SCHOLARCHAIN_GRAPH_SNAPSHOT_ID`, deadlines) are left unset, so
the packaged defaults apply. The `SCHOLARCHAIN_RUNTIME_ARTIFACT_*` pointer has a source since replan G-MAIN (G3): four optional root variables the
human fills in after the 14C upload, wired to query-api only (see "Phase 14B replan G-MAIN" at the end of this file). `runtime_enabled` additionally requires
`runtime_composition_verified`, an immutable40-character image revision, Neptune,
auth-secret references for all four services, query's outgoing token reference,
and graph-service's shared `SCHOLARCHAIN_GRAPH_CURSOR_KEY` by ARN, and, for the aws mode, `embedding_model_version`, `synthesis_model_id` and
`embedding_model_id`. The shared cursor key prevents autoscaled replicas from rejecting each other's cursors.
These are configuration guardrails, **not evidence of a live working artifact**.

**query-api readiness grace period and health-check timing (Phase 14B Step 0, review N3 and repair round 1 B1).** The ALB target group
health-checks query-api at `/readyz` (matcher `200`, unchanged), which waits for graph-service and semantic-service; all start in the same
apply. The query-api ECS service therefore sets `health_check_grace_period_seconds`. It is set only where the `load_balancer` block exists
(query-api with `https_certificate_arn`; both read `local.load_balanced_service`); it is null on graph-service, semantic-service,
embedding-worker and on query-api without a certificate, because ECS rejects it on a service with no load balancer.

The target-group timing is now explicit, because the defaults differ: the ELBv2 API documents interval 30 s, unhealthy threshold 2 and
healthy threshold 5, while the aws provider documents 30 s, 3 and 3. The `modules/runtime` variables, with ELBv2 limits as validation:

| Variable (module) | Default | Validation |
|---|---|---|
| `health_check_interval_seconds` | 30 | whole, 5 to 300 |
| `health_check_healthy_threshold` | 3 | whole, 2 to 10 |
| `health_check_unhealthy_threshold` | 3 | whole, 2 to 10 |
| `health_check_timeout_seconds` | 5 | whole, 2 to 120; a target-group precondition requires timeout < interval |
| `health_check_grace_period_seconds` | 300 | whole, 0 to 3600 |

The grace is the one tunable wired from the root: `query_health_check_grace_period_seconds` (`phase12b-variables.tf`, next to
`https_certificate_arn`; default 300, whole seconds 0 to 3600), passed to `module "runtime"`, so it can be set in the private
`course.local.tfvars` (see the commented example in `environments/course.local.tfvars.example`) without a commit. The interval,
thresholds and timeout stay module defaults (lean scope); changing them needs a commit.

Arithmetic (defaults, 3 x 30): a target is marked unhealthy after `unhealthy_threshold x interval` of failures (90 s); once unhealthy it
needs `healthy_threshold x interval` of consecutive passes (90 s) after the peers become ready. The grace must cover the peers' readiness
time plus that recovery time plus margin, so 300 s covers peers that are ready within about 200 s (300 - 90 = 210 s, minus margin). A
120 s grace, the earlier value, would have protected almost no case. A precondition on the query-api service
(`aws_ecs_service.service`) refuses a plan where the grace is below `healthy_threshold x interval` (90 s by default), because a
once-unhealthy target could then never recover inside the grace. Grace 0 is accepted by the variable but refused by that precondition
whenever a certificate makes query-api load-balanced. Covered by `tests/phase14b.tftest.hcl`; not live-verified.
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
workflow failures/timeouts. `dashboard_enabled` (default true; the USD 25 cap tfvars sets false) gates the
dashboard resource; the alarms and log groups do not depend on it. Native EMR charts use300s intervals; Container Insights
provides RunningTaskCount for worker metric math (policy absent when `container_insights_enabled=false`). The worker never scales to zero
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

## Phase 13C: main EMR module on decision 12-10 (Subphase 13C; nothing applied, no live AWS call)

`modules/emr` now matches the proven spike (`spikes/emr-spark-isolated/`) and decision 12-10
(`docs/agent-runs/phase-12/evidence/12d-spike-closeout/decision-12-10.md`).

| Item | What the module does | Where it is tested |
| --- | --- | --- |
| Release and applications | `emr-7.8.0` (a validated tfvars value, pinned), `applications = ["Hadoop"]` only: the stock Spark 3.5.4-amzn / Scala 2.12 is never installed | `tests/phase13c.tftest.hcl` `main_emr_matches_decision_12_10`, `release_label_other_than_emr_7_8_0_is_rejected` |
| Bootstrap | the real `scripts/emr/bootstrap.sh` (a human uploads it in Phase 14); Terraform passes its S3 URI and sha256, the runtime archive URI and sha256 (G5), the job JAR URI and sha256, the rendered spark-defaults with its sha256, the EFS ids and optional `extra_artifacts` (step scripts and config, each with sha256 and an allowed destination) | `bootstrap_args` assertions; `scripts/tests/test_emr_bootstrap.py` (36 tests) |
| Spark settings | rendered by the module (variable `spark_defaults`, validated): `spark.yarn.jars=local:/opt/scholarchain-runtime/jars/*`, `populateHadoopClasspath=false`, codecs without LZO, `spark.authenticate`, AES-CTR with `authEngineVersion=1`, IO encryption, G2 `spark.dynamicAllocation.shuffleTracking.enabled=true`, YARN cluster mode (set by the pipeline step). JAVA_HOME is resolved on each node by the bootstrap and never rendered | `spark_settings_rendered_by_the_module_equal_scripts_config_spark_12_10_conf` FAILS when the rendered text differs from `scripts/config/spark-12-10.conf` (same keys, same values, 22 settings) |
| Node paths | runtime `/opt/scholarchain-runtime`, job JAR under it, Java-home file `/opt/scholarchain-spike/java-home`, step-program directory `/opt/scholarchain-spike/bin` (`PIPELINE_STEP_BIN_DIR`), EFS mount `/mnt/scholarchain`: the values pinned in `scripts/config/release.conf` | `node_paths_equal_the_pinned_release_conf_paths`, `emr_step_programs_are_pinned_artifacts_in_the_release_conf_directory` |
| EMR step programs (finding C1) | EMR accepts at most 10,280 characters per step argument, so the step runner `sc-step.sh` and three Python programs are installed on the primary node as sha256-pinned `extra_artifacts` in `/opt/scholarchain-spike/bin/` and each EMR step is only a short launcher plus parameters (see `scripts/README.md`). `infra/terraform/emr-step-programs.json` (inside the root, so the plan materialization contains it) pins the hashes; the root guard requires every program exactly once with that hash and directory when `emr_config.enabled` | `emr_without_the_step_programs_is_rejected`, `a_step_program_with_a_stale_sha256_is_rejected`, `a_step_program_installed_in_the_wrong_directory_is_rejected`, `a_missing_step_program_is_rejected`, `a_step_program_listed_twice_is_rejected`; the manifest equals `filesha256` of the files under `scripts/emr/` (asserted in the test) |
| EFS staging (G1 option ii) | encrypted with the project CMK, elastic throughput, backups disabled, one mount target, a security group admitting NFS 2049 only from the EMR group (with a matching NFS-only egress rule on the EMR group), an access point fixing uid/gid 1500 and the root directory, and a file-system policy that denies non-TLS and admits the EMR instance role only through the access point. Created under the same flag as the cluster | `efs_staging_is_ported_and_scoped`, `emr_disabled_by_default_creates_nothing` |
| Instance-role policy | EFS client only through the access point; EMR auto-termination actions only on clusters carrying the stack tag | `instance_role_policy_is_scoped_to_the_access_point_and_the_stack_tag` |

### Disclosed limitation: EMR in-transit TLS is disabled (human decision, 13C Step 0)

The previous module enabled EMR in-transit TLS with a PEM certificate bundle. That combination is
**untested with the custom runtime** and Phase 13 cannot test it live, so TLS is off (`EnableInTransitEncryption=false`,
no `tls_certificate_uri` input). What stays on: S3 SSE-KMS and local-disk/EBS encryption with the project CMK (at rest),
Spark authentication, AES-CTR network encryption (`authEngineVersion=1`; AES-GCM is not used) and Spark IO encryption.
What is not encrypted in transit: Hadoop and YARN RPC and shuffle traffic outside Spark's own crypto, between nodes inside
the private subnet (the EMR security group admits only its own members and the service-access group). The test
`tls_is_disabled_and_at_rest_encryption_stays_on` pins this state, so re-enabling TLS is a reviewed change, not drift.

### G2, G3, G5 and the G6 cap cross-check

* **G2** dynamic allocation uses shuffle tracking (no yarn-shuffle JAR). First proven live in Phase 15.
* **G3** `max_task_nodes` defaults to 0 and managed scaling to off; both are enabled only through `emr_config` in tfvars, with
  validated caps: `max_task_nodes` at most 1, `task_node_count` at most `max_task_nodes`, `managed_scaling_max_capacity`
  (core plus task, primary excluded) at most `1 + max_task_nodes`, idle timeout 60 to 900 s, instance type `m5.xlarge`.
* **G6 cross-check.** The estimate the scripts use is instances x (EC2 + EMR rate) x (maximum runtime + idle timeout). Under the
  pinned rates (m5.xlarge 0.192 + 0.048 USD/h), 180 minutes and 900 s, three instances cost 2.34 USD and four cost 3.12 USD,
  above the 3 USD per-run cap, so the Terraform bound is **one** task node (not the 12B bound of two). m5.2xlarge is rejected
  because even primary + core cost 3.12 USD. `terraform_caps_stay_inside_the_g6_per_run_cap_under_the_pinned_rates` reads
  `scripts/config/release.conf` and `emr-pricing.conf` and fails if the largest permitted cluster exceeds `EMR_MAX_RUN_USD`, if
  a fourth instance would not exceed it (so the bound is no longer the tightest), or if the idle timeout exceeds the script cap.
  `scripts/config/release.conf` keeps `PIPELINE_MAX_CAPACITY=4`, so the scripts still accept up to four instances and refuse by
  estimate. Prices are public list prices and `EMR_PRICING_CONFIRMED_BY_HUMAN` stays `false`.
* **Task group EBS.** The task instance group pins gp3, the configured size and 3000 IOPS like the core group. `hashicorp/aws` 6.44.0 has no `throughput` argument on `aws_emr_instance_group.ebs_config` (it exists only on the cluster's primary and core groups, checked with `terraform providers schema`), so gp3's 125 MiB/s baseline is the unpinned default there.
* **G5** the bootstrap downloads the runtime archive from `runtime_archive_uri` and verifies `runtime_archive_sha256`
  (default `789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5`) before extracting it; nothing is uploaded
  before Phase 14. Every artifact URI must lie in the project artifacts bucket (the bucket the EMR instance role reads).

### Bootstrap inputs (what the human supplies in Phase 14, in an ignored `*.local.tfvars`)

`emr_config = { enabled = true, runtime_reference, runtime_verified = true, bootstrap_uri, bootstrap_sha256, runtime_archive_uri,
job_jar_uri, job_jar_sha256, extra_artifacts = [{ uri, sha256, dest }] }` plus `emr_service_policy_json`. `extra_artifacts` MUST
contain the four EMR step programs (finding C1), each once, at `dest = "/opt/scholarchain-spike/bin/<name>"` with the `sha256`
printed by `python3 -I scripts/lib/pipeline.py step-manifest` (the file `emr-step-programs.json`): `sc-step.sh`,
`sc-ceiling-check.py`, `sc-class-origin-verify.py` and `sc-render-spark-config.py`, uploaded from `scripts/emr/` at the approved
commit. The guard refuses any other hash. `runtime_archive_sha256` must equal the decision 12-10 pin (carried finding C2); it is
validated at the root variable and in the module, so a tfvars override cannot install a different runtime. The bootstrap script's own
hash is passed as `--self-sha256`: EMR downloads the script, so this is drift detection, not tamper protection (the artifact
hashes share the same trust root, the reviewed tfvars). The bootstrap's installed paths are the ones pinned in `scripts/config/release.conf`, so
changing a path means changing `scripts/config/release.conf`, the module `node_paths` and the tests together.

### Carried item 17 (closed) and the other IAM items

The deployer's spike boundary now requires the stack tag (`scholarchain:stack = spike-emr`) as well as the EMR managed-policies
tag for `ec2:TerminateInstances`, `ec2:ModifyInstanceAttribute`, `ec2:DeleteNetworkInterface` and `ec2:DeleteTags` on
`instance/*`, `network-interface/*` (and `volume/*`); it grants no launch-template action, and the test fails if one without the stack
tag is ever added. Because EMR propagates cluster tags to the instances it launches, the main cluster carries `scholarchain:stack`
(`emr_config.stack_tag_value`, default `main-emr`) and the EMR managed-policies tag (kept because the supplied service policy follows
AmazonEMRServicePolicy_v2's tag conditions). Not verified live: the tag on the ENI that EMR creates for service access in a private
subnet; if its delete is denied, the human reviews it. See `deployer/README.md` for items 2, 14, 16 and 18. Item 5: the spike key policy and the
main service-role policy give `kms:CreateGrant` only with `kms:GrantIsForAWSResource=true`. Items 15 and 30 are wording fixes; item
23 removes extra blank lines at the end of two files.

Destroy still needs **two passes** because of the `aws_eip.nat` `DisassociateAddress` 403 (carried item 24); the grant is not widened.

### Tests added or changed in 13C

`tests/phase13c.tftest.hcl` (28 runs); `tests/phase12b.tftest.hcl` and `phase12c.tftest.hcl` follow the new `emr_config` shape (Hadoop only,
TLS off, idle 900); `deployer/tests/deployer.tftest.hcl` adds the item 2, 14, 16 and 17 negative tests; `spikes/emr-spark-isolated/tests/spike.tftest.hcl`
adds the item 5 and 16 tests. Each negative test was shown to FAIL on the old policy by a temporary mutation (recorded in the 13C evidence).

## Phase 14A additions (authored offline, nothing applied)

### Private values: where they go, and what each plan needs

Copy `environments/course.local.tfvars.example` to `environments/course.local.tfvars` (git-ignored by the `*.tfvars` rule: `git check-ignore -v` reports `.gitignore:52:*.tfvars` for the copy and nothing for the `.example`, exit 1) and export `SCHOLARCHAIN_TF_PRIVATE_VARS` with its path. `scripts/plan.sh` passes exactly `-var-file=environments/<env>.tfvars` (read from the git archive of the planned commit), `-var-file=$SCHOLARCHAIN_TF_PRIVATE_VARS`, `-var=aws_region`, `-var=aws_profile` and, for the runtime plan, `-var=image_revision`; the `.example` file is never loaded by Terraform or by `plan.sh` (it is not `terraform.tfvars`, `*.auto.tfvars`, or the `<env>.tfvars` name). The file lists every variable the human supplies and marks each BASE, RUNTIME, BOTH or EMR:

| Variable(s) | Plan |
|---|---|
| `aws_account_id`, `availability_zones`, `deployment_trusted_principal_arn`, `budget_limit_usd` | BOTH (no defaults) |
| `aws_region`, `aws_profile` | BOTH, supplied by `plan.sh` on the command line (optional in the file; must equal it if present) |
| `neptune_enabled`, `neptune_engine_version`, `neptune_parameter_family` | BASE optional; RUNTIME requires `neptune_enabled = true` (guard in `phase12b.tf:41-44`); an engine version needs the matching `neptune<major>.<minor>` family |
| `synthesis_provider`, `embedding_provider` | BOTH (they decide the IAM text and which key containers exist); defaults `anthropic` and `voyage` |
| `synthesis_model_id` and, only for a model without an in-region endpoint, `synthesis_inference_profile_id` and `_regions` (only with `synthesis_provider = "bedrock"`; with `anthropic` they must stay unset) | BOTH (IAM text) |
| `runtime_enabled`, `runtime_composition_verified`, `service_secret_bindings` (ARNs of secrets the human creates in Secrets Manager outside Terraform, so values never enter state), optional `service_secret_arns`, `public_ingress_cidrs`, `https_certificate_arn` | RUNTIME (`false` and empty in the base plan) |
| `image_revision` | RUNTIME, passed as `-var` by `plan.sh --image-revision <40-hex>`; not in the file |
| `alarm_notification_arns` | BOTH, optional SNS topic ARNs (no e-mail address) |
| `emr_config` (bootstrap, runtime archive, job JAR, `extra_artifacts`), `emr_service_policy_json` | EMR only, see below |

`enable_budget_resource` stays `false` (the account-level budget exists outside this root); no e-mail address belongs in any file.

**The `extra_artifacts` guard.** `terraform_data.phase12b_guard` (`phase12b.tf:33-36`) refuses the plan unless `emr_config.extra_artifacts` installs each of the four step programs exactly once at `<bin_dir>/<name>` with the sha256 pinned in `emr-step-programs.json` (`sc-ceiling-check.py`, `sc-class-origin-verify.py`, `sc-render-spark-config.py`, `sc-step.sh`). The example carries the four values read from `python3 -I scripts/lib/pipeline.py step-manifest` on 2026-11-06 at the 14A base commit (the same values as the JSON; the test `the_tfvars_example_carries_exactly_the_manifest_hashes_for_the_four_step_programs` fails when they drift). **The guard holds only when `emr_config.enabled` is `true`**: its condition begins `!var.emr_config.enabled ||`, so a plan with EMR disabled needs no step programs, and `emr_disabled_needs_no_step_programs`, `emr_enabled_without_the_step_programs_is_refused_by_the_guard` and `emr_enabled_with_one_step_program_missing_is_refused` (`tests/phase14a.tftest.hcl`) show both sides.

**Is EMR enabled in the Phase 14 plans?** Per the source, **no: EMR is enabled only in a Phase 15 plan.** The committed `environments/course.tfvars` sets `emr_config.enabled = false`; the guard needs the bootstrap, runtime archive and job JAR URIs and hashes before it allows `true` (`phase12b.tf:29-32`), and the job JAR does not exist yet (ER JAR packaging is a Phase 15 prerequisite); the only artifact a `deploy.sh` stage uploads is the G5 runtime archive (`base-apply`), never the bootstrap or the JAR; `scripts/README.md` lists the first-deployment plans as "runtime disabled" and "runtime enabled" with no EMR variable; and `scripts/run-bounded-pipeline.sh` runs on an existing Terraform-created cluster, with its experiments in Phase 15. So the first EMR-created ENIs (nodes, service access, and the EFS mount-target ENI) appear when a Phase 15 plan enables EMR, **not** at Phase 14 `base-apply` or `runtime-apply`; the item 17 live check on the EMR-created ENIs therefore belongs to that first EMR apply. The `phase14-main` deployer set already allows EMR and EFS, so enabling it later needs no deployer change. Nothing in the source forbids the human from enabling EMR in the runtime plan; if they do, the guard above applies.

### Bedrock inference profiles (decision 14-3)

`modules/identity/phase12b.tf` used to grant `bedrock:InvokeModel` only on `arn:aws:bedrock:<region>::foundation-model/<model id>`. That grant is unchanged when no profile is configured. For a model that Bedrock serves only through a system-defined cross-region inference profile, set (root variables in `phase12b-variables.tf`, wired to `module.identity`): `synthesis_inference_profile_id` (`<geo prefix>.<synthesis_model_id>`, prefix one of `us eu apac au jp ca us-gov global`, validated to equal the model ID after the prefix) and `synthesis_inference_profile_regions` (every region the profile routes to from `aws_region`, home region included; distinct region names; required for a geographic profile, rejected without a profile). The embedding model has the same pair (`embedding_inference_profile_id`, `_regions`). With a profile, the grant is three-part, as AWS documents (https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html, https://aws.amazon.com/blogs/machine-learning/securing-amazon-bedrock-cross-region-inference-geographic-and-global/):

1. `bedrock:InvokeModel` on `arn:aws:bedrock:<home region>:<account>:inference-profile/<profile id>`;
2. `bedrock:InvokeModel` on `arn:aws:bedrock:<each routed region>::foundation-model/<model id>`, with the condition `bedrock:InferenceProfileArn = <that profile ARN>` (AWS documents `StringEquals` and `StringLike` forms of this condition, so the model cannot be invoked directly in those regions);
3. for a `global.*` profile only, `arn:aws:bedrock:::foundation-model/<model id>` with `aws:RequestedRegion = unspecified` and the same `bedrock:InferenceProfileArn` condition.

`query-api` gets only the synthesis grant; `semantic-service` and `embedding-worker` only the embedding grant; `graph-service` none. **Streaming:** `bedrock:InvokeModelWithResponseStream` is not granted because no module calls a streaming operation: synthesis uses the Converse API (`modules/rag/.../RuntimeLlm.scala:134`, `client.converse`), embedding uses `invokeModel` (`EmbeddingClients.scala:131`), and `converseStream` appears nowhere under `modules/`. Converse needs only `bedrock:InvokeModel` (https://repost.aws/knowledge-center/bedrock-api-cross-account-access: "For the Converse API use bedrock:InvokeModel; ConverseStream requires bedrock:InvokeModelWithResponseStream"). The application must pass the **profile ID** (not the foundation-model ID) as `modelId` for a profile-only model; that is service configuration, not Terraform.

**What the AWS documentation says (read 2026-11-06; for the human to fill the variables once the model ID is known):**

* `amazon.titan-embed-text-v2:0` is invoked **on demand in-region** and needs no profile: its model card (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-titan-text-embeddings-v2.html) lists inference types "On-Demand, Provisioned Throughput", lists `us-east-2` (Ohio) in its regional availability table, and shows "Geo inference ID: Not supported, Global inference ID: Not supported". (The tick marks of the availability table are not in the retrieved text; the evidence is the listed row plus "Not supported" for profiles. 256 dimensions is a supported output size, https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html.) Leave the embedding profile variables unset.
* **Current Anthropic models are served through profiles.** The model cards for Claude Sonnet 4.6 (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html), Claude Haiku 5.5 (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html) and Claude Sonnet 4 (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4.html) show "In-Region endpoint URL: N/A" with geo IDs `us.anthropic.<model id>` (and `global.anthropic.<model id>`): a profile is **required**. Cards read: Opus 4.1, Sonnet 4.6, Haiku 5.5, Sonnet 4 (programmatic access only). Rule: if a model card's "In-Region endpoint URL" is N/A, use a profile; do not assume for a model whose card was not read.
* **Routing of the `us.` profiles from us-east-2** (model cards, "Geo inference details", source us-east-2): Sonnet 4.6, Opus 4.1 (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-1.html) and Haiku 5.5 each route to **us-east-1, us-east-2 and us-west-2**. AWS states that a geographic profile's destination list never changes; the authoritative, read-only check from the home region is `aws bedrock get-inference-profile --region us-east-2 --inference-profile-identifier <profile id> --query 'models[].modelArn'` (https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html). The `global.` profile routes to all commercial regions and needs the third statement above.
* Phase 14 model (decision, model access enabled in the three regions): Claude Haiku 4.5, `synthesis_model_id = "anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"`, `synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]`, with `embedding_model_id = "amazon.titan-embed-text-v2:0"` and no embedding profile. These are the documented values in `environments/course.local.tfvars.example`; the validators accept exactly them and `the_documented_haiku_4_5_example_values_produce_the_expected_arns` checks the resulting ARNs. The Haiku 4.5 model card (https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html, read 2026-11-06) confirms it: `bedrock-runtime` has no bare model ID ("requires a geo or global inference profile ID"), and the `us.anthropic.claude-haiku-4-5-20251001-v1:0` profile routes from us-east-2 to us-east-1, us-east-2 and us-west-2. Confirm with `get-inference-profile` before the base plan. Model access must be enabled in every routed region (the CDK construct notes the same requirement).
* **Endpoint policy.** The `bedrock-runtime` interface endpoint is optional (`interface_endpoint_services` default `[]`, `environments/course.tfvars` leaves it empty, NAT supplies HTTPS egress). When enabled, `aws_vpc_endpoint.interface` (`modules/network/main.tf:206-215`) sets no `policy`, so AWS's default policy (full access) applies and the profile ARN needs no addition. A restrictive endpoint policy added later must be tested, because the request names the profile ARN.

Tests: `tests/phase14a.tftest.hcl` (no profile = home-region foundation-model ARN only; profile = profile ARN + one conditioned model ARN per routed region; global adds the region-less ARN; `query-api` only synthesis, `semantic-service` and `embedding-worker` only embedding; invalid profile ID, prefix, wildcard, region name, duplicate, missing home region, regions without a profile are rejected). Mutation results are in the 14A owner report.

### Permissions boundaries on every role (D1, round 2)

All seven `aws_iam_role` blocks now carry `permissions_boundary` (`modules/identity/main.tf`: `local.boundary_arn`, six roles; `modules/workflow/main.tf:3`, the producer role). The ARN is built from the account ID and the fixed names `<project>-<environment>-permissions-boundary` and `<project>-<environment>-emr-service-boundary`; nothing is read from remote state and no new tfvars entry is needed. Mapping: the four task roles, the four execution roles, the Neptune loader, the EMR instance role (`-emr-ec2`), the deployment role and the Step Functions producer carry the runtime boundary; `-emr-service` carries the EMR service boundary. The deployer root (`deployer/`) creates both policies from `deployer/boundaries/*.json.tftpl`, the same files `tests/phase14a.tftest.hcl` renders to assert that every action of every policy attached to each role is allowed by its boundary (and that the naming scheme matches the deployer root's). Apply the deployer root before the main root's first apply; see `deployer/README.md`.

### EMR service policy review (Q13; documentation only, the human decides in the 14A acceptance)

**How the main stack attaches it.** The EMR service role `aws_iam_role.emr_service` (`modules/identity/main.tf:255-267`) is trust-only (`elasticmapreduce.amazonaws.com`, `aws:SourceAccount`). `emr_service_policy_json` (root variable, `phase12b-variables.tf:262-285`; passed at `main.tf:57`, with `enable_emr = var.emr_config.enabled` at `main.tf:58`) becomes the inline policy `selected-emr-control-plane` (`modules/identity/phase12b.tf:58-63`, `count = enable_emr && JSON != null`), plus the fixed inline policy `project-encrypted-emr-disks` (`phase12b.tf:66-73`: project-key Decrypt, DescribeKey, GenerateDataKeyWithoutPlaintext, ReEncrypt, and `CreateGrant` only when `kms:GrantIsForAWSResource`). There is **no managed-policy attachment** and no default: an enabled EMR with a null JSON is refused (`phase12b.tf:29-32`). The spike did the opposite: it attached the managed `AmazonEMRServicePolicy_v2` (`spikes/emr-spark-isolated/iam.tf:22-25`) and added one `iam:PassRole` for its instance role (`iam.tf:27-41`).

**What the human must supply.** One JSON string `emr_service_policy_json`, only when `emr_config.enabled` is true. The validator (`phase12b-variables.tf:271-281`) rejects any wildcard in an action, any ARN whose partition, service, region or account segment contains a wildcard, and `"*"` as a resource except for `ec2:Describe*` actions. The published v2 text therefore cannot be pasted (it uses `arn:aws:ec2:*:*:...` and `Resource: "*"` on write actions): it must be concretized to `us-east-2` and the account.

**Recommended reviewed option.** `environments/emr-service-policy.json.example`: the parts of v2 the cluster uses (https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html), concretized to region and account (the `Resource: "*"` write statements limited to `instance/*`, `network-interface/*`, `volume/*`, `subnet/*`, `security-group/*`, `vpc/*`), keeping v2's tag conditions, and replacing v2's hard-coded `EMR_EC2_DefaultRole` PassRole with `scholarchain-<environment>-emr-ec2` to EC2. It has 13 statements; v2's launch-template, placement-group, Application Auto Scaling, resource-group and EMR service VPC-endpoint parts are left out (the spike's live launch on `emr-7.8.0` used none of them, so a missing one fails closed and a human decides). It passes the validator once the three placeholders are filled (test `the_example_emr_service_policy_passes_the_variable_validation_once_placeholders_are_filled`), and every action is inside the EMR boundary `scholarchain-<environment>-emr-service-boundary` (deployer test `p14_the_emr_service_boundary_covers_every_action_of_the_example_service_policy`). Scoping: tag conditions (`aws:ResourceTag/for-use-with-amazon-emr-managed-policies = true` on existing subnets, security groups, VPC, instances, ENIs; the matching `aws:RequestTag` on new instances, volumes, ENIs and security groups), `ec2:CreateAction` to restrict tagging to creation, region and account in every ARN, `iam:PassRole` of the project instance role to `ec2.amazonaws.com` only.

*Trade-offs.* (a) The managed `AmazonEMRServicePolicy_v2` (the spike's choice, live-proven there): AWS maintains it, but it is not region- or account-bound (several write statements are `Resource: "*"` under tag conditions), can change underneath the stack, and attaching it needs a code change in `modules/identity` plus `iam:AttachRolePolicy` for that exact ARN in the deployer set (a routed repair and a new deployer apply). (b) The example above: bound to this region and account, reviewable text in the tfvars, no new deployer permission, but narrower than v2 (a launch that needs a left-out statement fails with AccessDenied and needs a repair) and it relies on the tag fix below. (c) Resource-ID-scoped ARNs are impossible before the first apply.

**Defects and observations (nothing was widened).**

1. **Tag gap (fixed in round 2, D2).** v2's `CreateInTaggedNetwork` requires `for-use-with-amazon-emr-managed-policies = true` on the subnet and security groups the cluster launches into. It was present only on `aws_security_group.emr_service_access`. `modules/network/main.tf` now also tags the application subnets and the EMR node group `aws_security_group.role["emr"]` with exactly `"true"`; the public and data subnets, the VPC and every other role group stay untagged (test `emr_tag_is_on_the_application_subnets_the_emr_node_group_and_the_service_access_group_only`, 6 mutations). The deployer's `main_tag_keys` already contains the key and its tag-on-create statements do not restrict tag keys (deployer test `p14_the_emr_managed_policies_tag_may_be_applied_to_subnets_and_security_groups`). Not live-verified (Phase 15 apply).
2. Observation: the trust has `aws:SourceAccount` only (`modules/identity/main.tf:261-263`); the spike also had `aws:SourceArn` (`spikes/emr-spark-isolated/iam.tf:14-15`). A hardening option, not a defect.
3. The role now carries `scholarchain-<environment>-emr-service-boundary` (D1), which mirrors the same v2 tag conditions; with defect 1 fixed the tagged network satisfies both.

### Assembling `emr_service_policy_json` (Phase 14B pre-session item 4; offline, no AWS call)

`emr_service_policy_json` is `environments/emr-service-policy.json.example` with exactly three placeholders replaced: `<region>` (`us-east-2`), `<12-digit-account-id>` (the approved account, which stays out of the repository) and `<environment>` (`course`, giving the PassRole target `scholarchain-course-emr-ec2`). Nothing else is edited. The helper `scripts/lib/emr_service_policy.py` does this and checks the result; the account id is read from an environment variable and written only into a new private file.

1. In the repository root, type the account id into an environment variable (nothing is echoed or stored): `read -r ACCT; export ACCT`.
2. Render into a private, git-ignored file (the command refuses an existing file and writes mode 600): `python3 -I scripts/lib/emr_service_policy.py render --region us-east-2 --environment course --account-env ACCT --out target/phase14/private/emr-service-policy.tfvars; unset ACCT`. Expect `EMR-POLICY: statements=13 ...` and `RESULT: PASS rendered and checked`. The summary shows no account id.
3. Check it again and keep the output as evidence (the account id is masked as `<acct>`): `python3 -I scripts/lib/emr_service_policy.py check --file target/phase14/private/emr-service-policy.tfvars --region us-east-2 --environment course`. Expect twelve `OK:` lines and `RESULT: PASS`. The checks: valid JSON, `Version` `2012-10-17`, exactly the 13 reviewed statement ids in order, every statement `Allow`, no placeholder left, no wildcard action, every resource a concrete ARN (the Terraform validator's regex), `"*"` only on `ec2:Describe*`, exactly one `iam:PassRole` passed to `ec2.amazonaws.com`, one account throughout, every EC2 ARN in the region, the PassRole target `scholarchain-<environment>-emr-ec2`.
4. Show the coordinator the step 3 output (not the file) for the review the runbook asks for before B9.
5. Append the file to the private tfvars and delete it: `cat target/phase14/private/emr-service-policy.tfvars >> infra/terraform/environments/course.local.tfvars && rm target/phase14/private/emr-service-policy.tfvars`. The file holds `emr_service_policy_json = <<-EOT ... EOT` (a heredoc, as in `environments/course.local.tfvars.example`).
6. Terraform applies the variable validation (`phase12b-variables.tf`, `emr_service_policy_json`) at the next plan. Observed offline on a scratch module that holds only that variable block: a file rendered by step 2 loaded as a tfvars file and `length(jsondecode(var.emr_service_policy_json).Statement)` was 13; the same file with `ec2:TerminateInstances` changed to `ec2:Terminate*` was refused by the validator.

Offline tests: `scripts/tests/test_emr_service_policy.py` (render, the substitution equal to the one `tests/phase14a.tftest.hcl` performs with `replace()`, the exclusive 0600 output, refusal of a bad account, region or environment, and thirteen mutations of the rendered policy, each reported as `FAIL:` with exit 1) and, in Terraform, `the_example_emr_service_policy_passes_the_variable_validation_once_placeholders_are_filled` in `tests/phase14a.tftest.hcl`.

**Where the other two EMR values come from (reviewed by the coordinator).** `emr_config.runtime_reference` is free text that only has to be non-empty when EMR is enabled (`phase12b.tf:30`); it is stamped on the cluster as the tag `runtime_evidence` (`modules/emr/main.tf:111`). The repository has no fixed value; the record of the proven runtime is `docs/agent-runs/phase-12/evidence/12d-spike-closeout/decision-12-10.md` (the decision, accepted in `docs/agent-runs/phase-12/human-gate.md:28`; the runtime archive sha256 is at `decision-12-10.md:17` and equals `RUNTIME_ARCHIVE_EXPECTED_SHA256` in `scripts/config/release.conf:106`). A tag value may not contain `#`, so use the path alone. The render-config `templateVersion` is likewise not fixed anywhere: `docs/agent-runs/phase-08/evidence/8b-r1/render-config.template.json:10` holds `REPLACE_WITH_REVIEWED_TEMPLATE_VERSION`; the Phase 8b local runs used `independent-local-v1` (`docs/agent-runs/phase-08/evidence/8b/real-local-config.json`) and the unit tests `template-v1`. The only code constraint is `EmbeddingContracts.scala:196-198` (non-blank, at most 256 bytes, no whitespace or control character); the value is part of the stable vector slot key, so a later change re-embeds everything.

### Round 2 tests (`tests/phase14a.tftest.hcl`, 29 runs in total)

* `every_role_carries_the_boundary_the_deployer_root_creates_for_it`: the role to boundary mapping (11 identity roles runtime, `emr_service` EMR service, the producer runtime) and the naming scheme shared with `deployer/phase14_main.tf`.
* `every_action_of_every_role_policy_is_allowed_by_that_roles_boundary`: renders `deployer/boundaries/*.json.tftpl` and checks, wildcard-aware, every Allow action of every inline policy of the 13 roles against its boundary (the deployment role has no policy), with EMR enabled and the reviewed example EMR policy, Neptune on, a synthesis profile and secret bindings so that no statement is absent. Actions only, not resource ARNs.
* `emr_tag_is_on_the_application_subnets_the_emr_node_group_and_the_service_access_group_only` (D2).
* `the_documented_haiku_4_5_example_values_produce_the_expected_arns`.

### Repair round 1 (F2, F5): key administration in the key policy, no default-security-group adoption

* `modules/identity/main.tf`: the project key policy has five statements: the account-root IAM delegation (kept: lockout-safety and break-glass path, and the runtime roles use it), the S3 Vectors service decrypt, and three statements that name the deployer role (`arn:aws:iam::<account>:role/scholarchain-deployer`, built from the account ID and the fixed role name, no remote state): administration (15 actions including `PutKeyPolicy`, `ScheduleKeyDeletion`, `DisableKeyRotation`, `UntagResource`), data-key use only through nine services, and grants only for AWS resources. The deployer role must exist before the first key is created (CreateKey requires every principal of a key policy to exist), which the deployer-first order already guarantees. AWS rules relied on: tagging at `CreateKey` needs `kms:TagResource` in an IAM policy covering all keys of the account and region (https://docs.aws.amazon.com/kms/latest/developerguide/add-tags.html) and the key policy must let the caller call `PutKeyPolicy` again (https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html); the deployer's IAM set therefore keeps only `kms:CreateKey`, `kms:TagResource`, alias actions on alias ARNs and `kms:ListAliases`.
* `modules/network/main.tf`: `aws_default_security_group` is removed (the Phase 12D spike made the same choice). The deployer set lost `Ec2AdoptedDefaultSgRevokeRules` and `Ec2AdoptedDefaultSgFirstTags`.
* `scripts/phase12d-spike/tests/test_terraform_static.py`: the D6 named exception is removed; every `Action = ["ec2:CreateTags"]` statement needs `ec2:CreateAction` again.
* Tests: the existing `kms_policy` assertions (`tests/phase12b.tftest.hcl`, `tests/phase12c.tftest.hcl`) now expect the five statements; new root test `the_main_stack_key_policy_grants_the_deployer_role_exactly_its_administration_and_nothing_else` and `the_vpc_default_security_group_is_not_managed_and_no_adoption_statement_remains`.

### Repair round 1 (F1, infra part): aws-mode task environment and two task-role grants

* **Synthesis model.** `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL` is the inference-profile ID when `synthesis_inference_profile_id` is set (it is the Converse `modelId`), else `synthesis_model_id`; `SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION` is `synthesis_model_id`.
* **Embedding model version: a human decision, no default.** The version the 14C ingest stamps on vectors comes from the `model.version` of the live-ingest config file (`LiveEmbeddingIngestMain.scala:227` reports `plan.config.model.version`; `docs/agent-runs/phase-08/evidence/8b-r1/live-config.template.json` holds `REPLACE_WITH_PINNED_MODEL_VERSION`), so no single value exists in code. New root variable `embedding_model_version` (null default, listed in `environments/course.local.tfvars.example`) must equal it; the aws mode is refused without it. **BLOCKED-ON human decision: choose the pinned version once and use it in both places.**
* **New root variables** (defaults in `phase12b-variables.tf`): `semantic_index_name` (default `researcher-profile-v1`, a human choice for the retrieval use case), `embedding_text_prefix` (default `embedding-text`; must equal the ingest `textPrefix`, which the 8b template shows as `graph/rag`: also a human decision), `evidence_index_prefix`, `runtime_audit_prefix` (the `AwsConfig` defaults). The prefixes feed both the task environment and the IAM scope below.
* **Grants (modules/identity).** `embedding-worker`: `ReservationInQuerySessionTableAndIndex` (`dynamodb:GetItem`, `PutItem`, `UpdateItem`, `Query` on the QuerySession table and its index; the reservation record lives there). `query-api` and `embedding-worker`: `s3:ListBucket` on the rag bucket ARN in two statements, because S3 answers 403 instead of 404 for an absent key without it (https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html) and `S3ObjectStore.head` maps only 404 to missing: `ListRagBucketPrefixes` (real listings, `s3:prefix` limited to the three prefixes and their sub-paths) and `HeadAbsentRagKeyAs404NotListing` (`Null s3:prefix = true`). The second exists because **AWS does not document that `s3:prefix` is populated for HeadObject**; if it is not, a prefix-only grant would never match and the 403 would persist. A list request always carries `s3:prefix` (empty when unspecified), so the `Null` statement cannot list, and these roles can already `GetObject` every key in the bucket. This is unverified against live S3 and is a risk to check in 14B. Both grants are inside the runtime permissions boundary (the coverage test passes unchanged).

## Phase 14B replan W5b: API certificate, Neptune tunnel, outputs and purge-ready stores (authored offline, nothing applied)

USD 25 course-cap replan; sources: `docs/agent-runs/phase-14/prompt.md` (replan decisions 4 and 5, 14C decisions 1 and 5) and the naming contract in
`deployer/README.md`, "Replan W5a". Tests: `tests/phase14b_replan.tftest.hcl` (35 runs, plan-only with the mock provider; the 35th pins the `vector_bucket_name` output).

**New root variables** (`phase14b-variables.tf`; all optional, defaults keep the earlier behavior):

| Variable | Default | Meaning |
|---|---|---|
| `api_domain_name` | `null` | FQDN of the API hostname (lowercase, at least three labels, no wildcard or trailing dot) of a domain the human owns, DNS at Cloudflare. **Private tfvars only; never committed** (tests and examples use `api.example.invalid`). Set: base-apply creates ONE DNS-validated `aws_acm_certificate`. |
| `acm_validation_timeout` | `"15m"` | Bound of the runtime-stage validation wait: whole minutes `1m` to `60m`. |
| `neptune_tunnel_enabled` | `false` | Register the one-off tunnel task definition and role; effective only with `runtime_enabled` and an `image_revision`. |

**Certificate staging.** `https_certificate_arn` (an externally provided ARN) is unchanged. Exactly one of it and `api_domain_name` may be set (guard in `phase12b.tf`); with the runtime enabled both paths need approved `public_ingress_cidrs` (no HTTP fallback).

| Stage | Resources | What happens |
|---|---|---|
| base-apply (`api_domain_name` set, runtime off) | `aws_acm_certificate.api` (DNS validation, default key algorithm, tags = the root's required tags) | Returns at once in "pending validation". **No `aws_acm_certificate_validation`, so the apply never waits.** Output `acm_validation_records` lists the CNAME name, type and value. |
| human, before runtime-apply | Cloudflare, by hand | Add the validation CNAME, **DNS only (not proxied)**. Check: `aws acm describe-certificate --certificate-arn <acm_certificate_arn> --query Certificate.Status` is `ISSUED` (read the output from the pinned state with the exact form in "G10" at the end of this file: a bare `terraform output` in the live checkout fails unless the root is initialised, and `-state=` is relative to `-chdir`) (a few minutes). |
| runtime-apply (runtime enabled with an image revision) | `aws_acm_certificate_validation.api` (create timeout = `acm_validation_timeout`), the HTTPS listener | The validation waits (bounded) until ACM has seen the record; the listener's `certificate_arn` is the validation's, so the listener never uses an unvalidated certificate. query-api is load-balanced from the plan on (the decision uses plan-time booleans, because the certificate ARN of a same-apply certificate is unknown at plan). |
| human, after the ALB exists | Cloudflare, by hand | CNAME `api.<domain>` -> output `alb_dns_name`, **DNS only**, so TLS ends at the ALB. |

The deployer's ACM statements are tag-conditioned (`acm:ValidationMethod = DNS`, `aws:RequestTag/project` and `/environment`, resource tags on delete/tag calls, `aws:TagKeys` within `main_tag_keys`); the certificate carries `module.foundation.tags` (course, project, environment, owner, expiration_date), which satisfy them (test `the_certificate_carries_the_required_project_tags_the_deployer_conditions_on`). Before the session, check the domain for CAA records and, if any exist, add one that allows `amazon.com`.

**Neptune tunnel** (`neptune_tunnel_enabled = true`, runtime deployed). `modules/identity/neptune_tunnel.tf`: role `scholarchain-<env>-neptune-tunnel-task` (ECS-tasks trust with the same source account and ECS source ARN conditions as the other task roles, the runtime permissions boundary, an inline policy `ecs-exec-channels` with exactly the four `ssmmessages:` channel actions on `*`, no data access). `modules/runtime/compute.tf`: task definition family `scholarchain-<env>-neptune-tunnel` (Fargate, awsvpc, 256 CPU / 512 MiB, linux/amd64, the graph-service image at the image revision, execution role `scholarchain-<env>-graph-service-execution`, entry point `sleep 14400`, `initProcessEnabled`, awslogs to the graph-service log group only, no environment, secrets or ports). `readonlyRootFilesystem` is **false** on purpose: AWS documents that ECS Exec cannot work with a read-only root file system. **No ECS service**: the human runs it as a one-off task and stops it afterwards, so nothing bills between loads. Output `neptune_tunnel` = `{cluster_name, family, task_definition_arn, container_name, subnet_ids, security_group_id}`; the run-task command, with the loader session:

```
aws ecs run-task --cluster <cluster_name> --task-definition <family> --launch-type FARGATE --enable-execute-command \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet_ids>],securityGroups=[<security_group_id>],assignPublicIp=DISABLED}"
```

Do not pass `--tags`, `--propagate-tags` or `--enable-ecs-managed-tags` (the loader role holds no `ecs:TagResource`). The security group is graph-service's, the only one Neptune admits. Unverified against a live account: ECS Exec with the image's non-root default user, and the port-forward to the Neptune writer endpoint (the 14B tunnel test).

**New outputs:** `acm_validation_records` (list of `{domain_name, name, type, value}`), `acm_certificate_arn`, `alb_dns_name`, `neptune_writer_endpoint` (hostname; the reader endpoint stays in the runtime environment), `neptune_port`, `neptune_cluster_resource_id` (for the deployer's `operator_neptune_cluster_resource_id`), `neptune_tunnel` and `phase14b_controls` (offline assertions only).

**Purge-ready data stores (W4).** See "State and cleanup design". Tests: `the_data_buckets_and_vector_stores_have_no_prevent_destroy`, `force_destroy_is_off_by_default_...` and `force_destroy_is_on_only_in_cleanup_mode_...`.

## Phase 14B replan G-MAIN: runtime-artifact pointer, tunnel timing, reading outputs, EMR in the session (authored offline, nothing applied)

Tests: `tests/phase14b_gmain.tftest.hcl` (43 runs, plan-only with the mock provider, every expectation derived by hand from `modules/services/README.md` and `AwsConfig.scala`).

### G3: the runtime-artifact pointer reaches the services that read it

Only the **query-api** role reads the pointer (`AwsConfig.scala`, the `case _ =>` branch that builds `QueryRoleConfig`; graph-service, semantic-service and embedding-worker never do). Four optional root variables (`phase14b-variables.tf`, default `null`, never secret, set in the PRIVATE tfvars so no commit is needed) map one to one to what `RuntimeArtifactMain` (`modules/storage`) prints:

| Printed by RuntimeArtifactMain | Root variable | Validation | Reaches |
|---|---|---|---|
| `SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET` | `runtime_artifact_bucket` | S3 bucket-name shape; when set it must equal the **rag bucket** (`module.datalake.bucket_names["rag"]`, root guard) and the pointer must be set | query-api only |
| `SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY` | `runtime_artifact_key` | `runtime-artifacts/<run_prefix>/versions/<segments>`, `<run_prefix>` = `^run-[a-z0-9][a-z0-9-]{1,27}$` (the deployer's `operator_run_prefix`), segments `A-Za-z0-9._=-` only, no `.` or `..` or empty segment, at most 900 characters | query-api only |
| `SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256` | `runtime_artifact_sha256` | 64 lowercase hex | query-api only |
| `SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID` | `runtime_artifact_source_run_id` | starts with a letter or digit, then `A-Za-z0-9._:-`, at most 128 characters (a run id has the form `run:<uuid>`) | query-api only |

Rules (root guard `terraform_data.phase12b_guard`): key, sha256 and source run id are **all or none** (the services refuse a partial pointer), and any of them needs `runtime_enabled` and `runtime_composition_verified` (the pointer exists only in the aws service mode). With none set, no task receives any `SCHOLARCHAIN_RUNTIME_ARTIFACT_*` variable and the services refuse artifact reads, as before. The bucket variable is optional because the services default for `SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET` **is the rag bucket**, so leaving it unset means the same bucket; when set it must equal that name.

**Final location contract (the deployer grant being written in parallel must match):** bucket `scholarchain-<env>-<account>-rag`, key `runtime-artifacts/<run_prefix>/versions/<run id with ':' replaced by '-'>/runtime-subset-<sha256>.json`. Produce it with `RuntimeArtifactMain ... --bucket <rag bucket> --key-prefix runtime-artifacts/<run_prefix>` (its default key prefix `runtime-artifacts` lacks the `<run_prefix>` level, so the flag is required). The operator that uploads needs `s3:PutObject` (create-only) on `<rag bucket>/runtime-artifacts/<run_prefix>/*` (BLOCKED-ON the deployer owner if the loader role does not hold it: its `rag` prefixes today are the embedding text prefix and `vector-rejects`).

**Read grant (modules/identity): already sufficient, so no statement was added.** The query-api task role has `ReadConfiguredObjects` (`s3:GetObject`, `s3:GetObjectVersion`) on `/*` of the rag, artifacts and graph buckets, which covers `runtime-artifacts/*` in the rag bucket, plus `kms:Decrypt` on the project key and, for the 403-instead-of-404 case, the `HeadAbsentRagKeyAs404NotListing` list statement. `runtime-artifacts` is also one of the four `rag_prefixes` (root `main.tf`), so the `ListRagBucketPrefixes` statement of query-api and embedding-worker allows listing `runtime-artifacts` and `runtime-artifacts/*` (pinned by `the_rag_list_scope_of_the_runtime_roles_includes_the_runtime_artifacts_prefix`; the list scope is eight patterns, and the existing `phase14a` test expects them). Test `query_api_can_already_read_every_key_of_the_rag_bucket_so_no_new_iam_statement_is_needed` pins that. A prefix-scoped statement would only be narrower than a grant the role already has; narrowing the existing bucket-wide read is a separate, reviewed change.

**How it is applied.** The values do not exist at the first runtime plan (the 14C load produces them). After the upload, put the four values in the private tfvars and run **one more runtime-apply** at the same clean HEAD: `plan.sh --image-revision <HEAD>`, a new approval record (`APPROVED_STAGE=runtime-apply`), a fresh pre-spend receipt, `deploy.sh --stage runtime-apply`. The only change is a new query-api task definition revision (a rolling replacement of that one service); no image push and no commit. Not live-verified.

### G12: `neptune_tunnel_enabled = true` belongs in the FIRST runtime plan

The tunnel task definition exists only in a plan that has the runtime **and** an image revision (`local.neptune_tunnel = neptune_tunnel_enabled && runtime_enabled && image_revision != null`), which is the runtime-apply itself. If the first runtime plan leaves it out, the 14B tunnel test (right after the first runtime-apply) needs a second runtime-apply with its own approval record and pre-spend receipt. Set it in the private tfvars before that first plan (commented example in `environments/course.local.tfvars.example`); the task definition costs nothing while no task runs.

### G10: reading the outputs from the pinned local state

`plan.sh` and `deploy.sh` run from a materialized copy bound to the pinned state file `infra/terraform/terraform.tfstate`, so the live checkout is usually not initialised and `terraform output` there fails with "Required plugins are not installed" (observed on a scratch copy of the root without `.terraform`). `terraform output -help` (Terraform 1.13.5) lists `-state=path`, `-raw`, `-json`, `-no-color`. Two forms that were run against a synthetic state file:

```
# no init needed: an empty working directory, absolute state path (the shell expands $PWD before -chdir applies)
terraform -chdir="$(mktemp -d)" output -no-color -state="$PWD/infra/terraform/terraform.tfstate" -raw alb_dns_name
# if the root is initialised: the state path is relative to -chdir, NOT to the repository
terraform -chdir=infra/terraform output -no-color -state=terraform.tfstate -raw alb_dns_name
```

**Pitfall:** `terraform -chdir=infra/terraform output -state=infra/terraform/terraform.tfstate ...` resolves the path against the new directory (`infra/terraform/infra/terraform/...`), finds no file and prints "No outputs found" with exit code 0, which looks like an empty stack. Use `-json` (no `-raw`) with no name to list every output; `acm_validation_records` and `neptune_tunnel` are lists or objects, so read them with `-json`.

### G18 (infra part): EMR in the session

No Terraform change is needed to enable EMR in the middle of the session: `emr_config` is a private tfvars object, applied by a runtime-apply plan. The exact sequence, the idle-timeout arithmetic and the approval records for three runs on one cluster are in `scripts/README.md`, "Phase 15A: three runs, one cluster". The bucket and prefix layout for the EMR artifacts and input datasets is `s3://<artifacts bucket>/emr/<run_prefix>/{bin,jars,steps,config,input/<label>}` (jars `hadoop-submit.jar`, `hadoop-bundle.jar`, `entity-resolution.jar`, `spark-job.jar`; config `er-policy.json`, `er-config.json`, `spark-config-template.json`; the pipeline output goes to `s3://<artifacts bucket>/pipeline/<run_prefix>/15a/size-N`), uploaded with the `scholarchain-pipeline` profile of the `operator-pipeline` role; every `emr_config` URI must lie in the artifacts bucket (root guard), and `scripts/upload-emr-artifacts.sh` uploads exactly those keys and prints the values to paste.

### Vector bucket name output (Phase 14B pre-session item 7)

Root output `vector_bucket_name` (`outputs.tf`, next to `embedding_dispatch_arn`) is the existing `module.s3vectors.bucket_name`, i.e. `scholarchain-<environment>-<account>-vectors` (`modules/s3vectors/main.tf:3`). No resource changes: the next plan shows only `Changes to Outputs`. Read it like the other outputs (G10): `terraform -chdir="$(mktemp -d)" output -no-color -state="$PWD/infra/terraform/terraform.tfstate" -raw vector_bucket_name`. Test: `the_vector_bucket_name_is_a_root_output_equal_to_the_vector_bucket_name_expression` in `tests/phase14b_replan.tftest.hcl` (equals `"scholarchain-course-${var.aws_account_id}-vectors"`, the planned bucket resource's name and the module output).

### Expected plan addresses for the pointer and EMR runtime-applies (Phase 14B pre-session item 9)

**These lists are derived offline with the mock provider. They are not a live plan. The real plan is compared against them in the session; a difference is not automatically wrong, it is something the human and the coordinator must explain before any apply, and a match is not an approval to apply.**

Method. Terraform cannot plan against a state offline, so `tests/phase14b_plan_deltas.tftest.hcl` makes three plan-only runs with the real-session shape (anthropic and voyage defaults, `neptune_tunnel_enabled = true`, `container_insights_enabled = false`, `dashboard_enabled = false`, grace 300, four services 256/1024): (1) the first runtime shape, (2) plus the four `runtime_artifact_*` values, (3) plus `emr_config` and `emr_service_policy_json`. Their assertions pin what may differ between the runs (only the query-api container definition between 1 and 2; no task definition and no role policy document between 2 and 3). `cd infra/terraform && terraform test -verbose -filter=tests/phase14b_plan_deltas.tftest.hcl > <file>` prints the three full plans and `python3 -I scripts/lib/plan_deltas.py derive --verbose-output <file>` diffs them (ignoring the mock's random 8-character values). Result, written to `scripts/config/expected-plan-deltas.json`:

| Stage | Plan | Address and action | Basis |
|---|---|---|---|
| pointer runtime-apply (runbook B8.4) | `Plan: 1 to add, 1 to change, 1 to destroy.` (`summary: add=0 change=1 destroy=0 replace=1`) | `module.runtime.aws_ecs_task_definition.service["query-api"]` replace (`PLAN-ACTION: delete+create`) | the only resource whose attributes differ between plans 1 and 2 (mock-derived); the action replace is the known provider behavior for a changed `container_definitions` and is unverified until live |
| | | `module.runtime.aws_ecs_service.service["query-api"]` update in place | hand-derived: `task_definition` references the replaced ARN; the mock gives the ARN a constant and cannot show it |
| EMR runtime-apply (runbook B9.3) | `Plan: 13 to add, 0 to change, 0 to destroy.` (`summary: add=13 change=0 destroy=0 replace=0`) | 13 `create`: `module.emr.aws_efs_access_point.staging[0]`, `aws_efs_backup_policy.staging[0]`, `aws_efs_file_system.staging[0]`, `aws_efs_file_system_policy.staging[0]`, `aws_efs_mount_target.staging[0]`, `aws_emr_cluster.pipeline[0]`, `aws_emr_security_configuration.encrypted[0]`, `aws_iam_role_policy.node[0]`, `aws_security_group.efs[0]`, `aws_vpc_security_group_egress_rule.emr_to_efs[0]`, `aws_vpc_security_group_ingress_rule.efs_from_emr[0]` (all `module.emr.`), plus `module.identity.aws_iam_role_policy.emr_control[0]` and `module.identity.aws_iam_role_policy.emr_disk_encryption[0]` | set difference between plans 2 and 3 (mock-derived); nothing else differs |

With `dashboard_enabled = true` the EMR plan would also show an in-place update of `module.observability.aws_cloudwatch_dashboard.elasticity[0]` (its body gains EMR widgets); the course tfvars sets it to `false`. Not modelled: drift on existing resources (`tags_all`, `description`), anything a mock hides. Compare in the session with `python3 -I scripts/lib/plan_deltas.py check --stage pointer-apply|emr-apply --plan-log <the plan.sh log>`: it reads the `PLAN-ACTION:` lines, prints `MATCH`, `MISSING`, `UNEXPECTED` or `ACTION-DIFFERS` per address and ends with `RESULT: IDENTICAL` (exit 0) or `RESULT: DIFFERS` (exit 1). Tests: `scripts/tests/test_plan_deltas.py` (15).

## Repair round 3 (Phase 14B): Anthropic API and Voyage AI providers (authored offline, nothing applied)

**Why.** Amazon Bedrock model access was restricted for the course account (quota). The instructor approved the Anthropic API for synthesis and Voyage AI for embeddings, with the rest of the infrastructure on AWS (ruling recorded verbatim in `docs/agent-runs/phase-14/prompt.md`, "Repair round 3"). External API charges count toward the USD 25 project limit and are reported as separate items (AWS, Anthropic, Voyage AI) followed by the combined total (`scripts/lib/cost_report.py`). The Bedrock switch is retained.

### The two switches

| Configuration | `synthesis_provider` | `embedding_provider` | Models (runtime environment) | Vector dimension | API key containers |
|---|---|---|---|---|---|
| **Primary (default)** | `anthropic` | `voyage` | synthesis `claude-haiku-5-5` (Messages API `https://api.anthropic.com/v1/messages`), embeddings `voyage-4-lite` (`https://api.voyageai.com`, `output_dimension` 256), embedding model version tag `voyage-4-lite` | 256 | both |
| Bedrock synthesis only | `bedrock` | `voyage` | synthesis `synthesis_model_id` (for example Claude Haiku 4.5, `anthropic.claude-haiku-4-5-20251001-v1:0`, with `synthesis_inference_profile_id`/`_regions` as in "Bedrock inference profiles"), embeddings as above | 256 | Voyage only |
| Bedrock embeddings only | `anthropic` | `bedrock` | synthesis as above, embeddings `embedding_model_id` (default Titan Text Embeddings V2, `amazon.titan-embed-text-v2:0`; `embedding_model_version` is required in the aws mode) | 256 | Anthropic only |
| Bedrock for both | `bedrock` | `bedrock` | the earlier plan | 256 | none |

Select a configuration by setting the two variables in the private tfvars (`environments/course.local.tfvars`); nothing else changes. Both models for a provider are fixed by the provider: with `anthropic` leave `synthesis_model_id` and `synthesis_inference_profile_*` unset, with `voyage` leave `embedding_model_id`, `embedding_inference_profile_*` and `embedding_model_version` unset (or exactly `voyage-4-lite`); a Bedrock id left over from the earlier plan is refused by `terraform_data.provider_guard` (`phase14b-providers.tf`) instead of being sent to the Anthropic API as a model name. `vector_dimension` stays 256 and the metric cosine (`phase12b_guard`).

**Vector consistency.** Stored and query vectors must share provider, model and dimension. Changing `embedding_provider` (or the embedding model) is not a configuration toggle: it needs a full re-embed of every stored vector and a rebuild of the affected vector indexes (the services refuse a vector whose model tag differs). Do it with the 14C ingest, not with Terraform.

### Runtime environment

| Variable | Roles | Value |
|---|---|---|
| `SCHOLARCHAIN_SYNTHESIS_PROVIDER` | `query-api` | `anthropic` or `bedrock` |
| `SCHOLARCHAIN_EMBEDDING_PROVIDER` | every role that carries the embedding identity (`query-api`, `semantic-service`, `embedding-worker`) | `voyage` or `bedrock` |
| `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL`, `SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION` | `query-api` | `claude-haiku-5-5` with the Anthropic provider (otherwise as before: the inference-profile id or the model id, and the model id) |
| `SCHOLARCHAIN_MODELS_EMBEDDING_MODEL`, `SCHOLARCHAIN_EMBEDDING_MODEL_VERSION`, `SCHOLARCHAIN_EMBEDDING_DIMENSION` | `query-api`, `semantic-service`, `embedding-worker` | `voyage-4-lite`, `voyage-4-lite`, `256` with Voyage |

All of them are `environment` entries of the aws service mode only (`modules/runtime/compute.tf:37` and `:57`). The two keys are `secrets` (below), never `environment`.

### Provider API keys: empty containers, values entered by hand

`phase14b-providers.tf` declares two `aws_secretsmanager_secret` resources, each created **only when its provider is selected**, with no secret version, no `secret_string`, no data source and no output that could carry a value (`tests/phase14b_providers.tftest.hcl` scans every `.tf` file for that). Both use the AWS-managed key `aws/secretsmanager` (no `kms_key_id`), so no `kms:Decrypt` grant is needed (one would be needed only for a customer key), and `recovery_window_in_days = 0`, so the destroy that `scripts/cleanup.sh` runs is a force delete without a recovery window.

| Secret name | IAM Resource pattern (the six `?` are the random suffix Secrets Manager appends) | Injected as | Read by (execution role) |
|---|---|---|---|
| `scholarchain-<environment>/anthropic-api-key` | `arn:aws:secretsmanager:<region>:<account>:secret:scholarchain-<environment>/anthropic-api-key-??????` | `SCHOLARCHAIN_ANTHROPIC_API_KEY` | `scholarchain-<environment>-query-api-execution` |
| `scholarchain-<environment>/voyage-api-key` | `arn:aws:secretsmanager:<region>:<account>:secret:scholarchain-<environment>/voyage-api-key-??????` | `SCHOLARCHAIN_VOYAGE_API_KEY` | `-semantic-service-execution`, `-embedding-worker-execution` |

The execution role statement is `InjectProviderApiKey` (`modules/identity/main.tf:271`): `secretsmanager:GetSecretValue` on exactly that role's pattern, and nothing else (the patterns are built from the name, so the policy is fully known in a reviewed plan). `graph-service` uses neither provider and gets neither key. No task role touches Secrets Manager (the key is injected at task start by the execution role, so application code never calls the SDK for it). ECS `secrets` entries take the real ARN of the container (`modules/runtime/compute.tf:147`) and only in the aws service mode: a task cannot start while its secret holds no value, so the values must be entered **before** the runtime apply that turns the aws mode on.

**Entering a key (human steps; no agent ever sees, prints or writes a value).**

1. After the base apply the two empty containers exist (`terraform output -json provider_controls` shows the names, never a value). `aws secretsmanager describe-secret --secret-id scholarchain-<environment>/anthropic-api-key` shows no `VersionIdsToStages` while the container is empty.
2. Create the key in the provider console (Anthropic Console, Voyage AI dashboard). Name it for this project so you can find and revoke it later.
3. Put the value into the container with an identity that holds `secretsmanager:PutSecretValue` on that one secret. **No Terraform-created role holds it** (not the deployer, not the operator roles): either use your own IAM identity in the AWS console (Secrets Manager, open the secret, Secret value, Edit, Plaintext, paste, Save) or, from a terminal that does not record the value, `read -rs KEY` then `printf '%s' "$KEY" | aws secretsmanager put-secret-value --secret-id <name> --secret-string file:///dev/stdin` and `unset KEY`. These commands were not run here (offline authoring): the first human run is their verification.
4. `describe-secret` now shows an `AWSCURRENT` version. Never run `get-secret-value`: the deployer role denies it by design.
5. After the session, `scripts/cleanup.sh` deletes both containers and prints a reminder: **deleting the container does not revoke the key.** Revoke both keys in the provider consoles yourself.

### IAM and boundaries

* **Deployer** (`infra/terraform/deployer`, set `phase14-main`, document `keys-obs`): `SecretsManagerProviderKeyContainersCreateAndTag` (`CreateSecret`, `TagResource`; resource `secret:scholarchain-<environment>/*`; region and the project/environment **request** tags) and `SecretsManagerProviderKeyContainersUpdateUntagDelete` (`UpdateSecret`, `UntagResource`, `DeleteSecret`; same prefix and region; project/environment **resource** tags). Not granted: `PutSecretValue`, `GetSecretValue` (explicit Deny kept), `PutResourcePolicy`, rotation, replication, `ListSecrets`, any other prefix. Document size 5339 of 6144 characters.
* **Runtime permissions boundary** (`deployer/boundaries/runtime.json.tftpl`): the Bedrock statement is rendered only when `main_synthesis_provider` or `main_embedding_provider` is `bedrock` (deployer variables, defaults `anthropic` and `voyage`; keep them equal to the main root's). `InjectConfiguredSecrets` stays `secretsmanager:GetSecretValue` on Secrets Manager secrets of the account: it is a ceiling over the inline grants that name the two provider patterns and the human-created auth secrets (arbitrary names), so it cannot be narrowed to a prefix without breaking those.
* **Operator-loader role**: the Titan grant (`InvokeTitanTextEmbeddingsV2Only`) exists only with `main_embedding_provider = "bedrock"`. With Voyage the loader holds no Bedrock permission; the 14C ingest embeds through the Voyage API with a key the human provides locally (assumption, outside Terraform).
* **Bedrock invoke grants** (task roles, `modules/identity/phase12b.tf`) exist per purpose only when that purpose's provider is `bedrock` (the Bedrock model id reaching the module is null otherwise). **No role of any root holds a Marketplace permission** in any configuration (asserted for every task, execution, loader, EMR and operator policy and both boundaries).

### Egress to `api.anthropic.com` and `api.voyageai.com`

Unchanged: the single NAT gateway on TCP 443; no interface endpoint, no new rule, no new port. The path, from the source:

1. The four services run in the application subnets with `assign_public_ip = false` (`modules/runtime/compute.tf:268`).
2. Their role security groups carry the egress rule TCP 443 to `0.0.0.0/0` (`modules/network/main.tf:165-174`, for `local.https_clients` at `:11`: `query-api`, `graph-service`, `semantic-service`, `embedding-worker`, `emr`). `query-api` (Anthropic) and `semantic-service`/`embedding-worker` (Voyage) are in that set.
3. The application route table's default route is the NAT gateway (`modules/network/main.tf:91` inside `aws_route.default`, `:95`); the NAT sits in a public subnet behind the internet gateway.
4. DNS resolves through the VPC resolver (`enable_dns_support`, `modules/network/main.tf:15`).
5. The execution role fetches the key from Secrets Manager over the same NAT path before the container starts.

Asserted by `tests/phase14b_providers.tftest.hcl` (`egress_to_the_provider_apis_is_the_single_nat_on_tcp_443_and_nothing_new`). Not live-verified: a first call from a running task is the proof, and no security group can restrict by hostname (the rule is by port).

### Tests

`cd infra/terraform && terraform init -backend=false && terraform test` (new test runs that use a `module` block need `terraform init` once so the test modules are registered). New: `tests/phase14b_providers.tftest.hcl` (defaults and identifiers, empty containers, no version/secret value, execution-role patterns, no Bedrock/Marketplace, environment and `secrets`, the Bedrock selections, guards, boundary closure, egress), three module runs in `tests/phase14b_cost_runtime.tftest.hcl`, and `deployer/tests/providers.tftest.hcl`. The earlier test files that assert the Bedrock path now select `synthesis_provider = "bedrock"` and `embedding_provider = "bedrock"` explicitly.

## Phase 15 P41: ALB request-count scaling and the semantic rate-limit override (authored offline, nothing applied)

Source: `docs/runbooks/session-2-plan.md` rows F26 and P41 and section 5.3 step 2; Work order 3 in `docs/agent-runs/phase-15/prompt.md`
(defaults accepted 2026-11-16). Three optional root variables in `phase12b-variables.tf` (end of file), all default `null`. With all three `null` the plan
is the same as before (no new resource, no new environment variable). Their Session 2 values come from the P35 rehearsal record and go in
the private `course.local.tfvars` (commented template in `environments/course.local.tfvars.example`).

| Root variable | Unit and range | Where it goes | `null` |
| --- | --- | --- | --- |
| `query_requests_per_target_target` | requests per target (query-api task) per **minute**, whole number 1-100000 | `module.runtime.aws_appautoscaling_policy.query_requests[0]`, target value | no request-count policy |
| `query_semantic_rate_limit_per_second` | requests per **second** per API key per query-api task, whole number 1-100000 (r_S2) | `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND` on query-api | unset; service default 50 |
| `query_semantic_rate_limit_burst` | token-bucket burst in requests, whole number 1-1000000 (2 x r_S2) | `SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST` on query-api | unset; service default 100 |

**Request-count policy.** A second target-tracking policy on the query-api scalable target, named `<prefix>-query-api-requests`, with the
predefined metric `ALBRequestCountPerTarget`, `resource_label = "<ALB arn_suffix>/<target group arn_suffix>"`
(`app/<name>/<id>/targetgroup/<name>/<id>`), scale-in cooldown 300 s, scale-out cooldown 60 s and scale-in enabled. Its count is
`enabled && image_revision != null && query_requests_per_target_target != null`: the first two terms are the count of `aws_lb.query` and
`aws_lb_target_group.query`, so the `[0]` references exist whenever the policy does, and with count 0 they are never evaluated. AWS accepts
the label only when the target group is attached to the ECS service; here that needs HTTPS (a listener certificate), so a precondition
refuses a plan that sets the target without HTTPS rather than failing at apply. The three CPU policies (`http_cpu`, target
`cpu_target_percent`, 60 by default) are unchanged. With both policies on query-api, Application Auto Scaling scales out when either asks and
scales in only when both allow it ([target tracking, "Multiple scaling policies"](https://docs.aws.amazon.com/autoscaling/application/userguide/target-tracking-scaling-policy-overview.html), read 2026-11-16).
The deployer's existing `AppAutoScalingEcsServices` (`PutScalingPolicy`, `DeleteScalingPolicy` on `scalable-target/*`) and
`CloudWatchAlarmsDashboardsOfTheMainStack` (`alarm:TargetTracking-*`) statements already cover it; no IAM change. Not live-verified.

**Rate-limit override.** Each value reaches the query-api task environment as a decimal string, only in the aws service mode
(`runtime_composition_verified`), and only when its own variable is set; no other role receives it. Neither is a secret. The module input
names are `semantic_rate_limit_per_second` and `semantic_rate_limit_burst`.

**Dashboard panel.** When the ALB exists (`module.runtime.alb_metric_dimensions` is non-null) and `dashboard_enabled = true`, the elasticity
dashboard gains one panel "ALB requests per target and target 4XX (query-api)", period 60, statistic Sum, with two metrics:
`AWS/ApplicationELB RequestCountPerTarget` by `TargetGroup`, and `HTTPCode_Target_4XX_Count` by `LoadBalancer` + `TargetGroup` (that
metric has no TargetGroup-only dimension set; [ALB CloudWatch metrics](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html), read 2026-11-16).
Both counts include 429 replies of the P40 rate limiter. The dimension values are ARN suffixes, so the dashboard body is "known after
apply" in the plan that creates the ALB. **Metric count:** the dashboard has 109 metrics without Neptune, EMR and the ALB; 114 with Neptune
(the test fixture), 116 with Neptune and the ALB panel, 122 with all optional sources. It is therefore already above P9's 50-metric
free-tier target before this change; P41 adds 2 and P9 still owns the reduction.

**Tests.** `tests/phase15_p41.tftest.hcl` (root, 18 runs) and `tests/phase15_p41_runtime.tftest.hcl` (module, 11 runs); run
`terraform init -backend=false` once so the module runs are registered, then `terraform test`.
