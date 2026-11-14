# Terraform literal-source checks

Run from the repository root:

```bash
python3 -I tests/infra/terraform_source_guard.py --self-test
python3 -I tests/infra/terraform_source_guard.py --repo-root .
```

`IndependentTerraformSourceSpec` runs both commands during the independent test
project's normal `sbt check` gate. The helper uses Python's standard library only,
does not call AWS, and only opens Git-visible files under `infra/terraform` with these
names: `.tf`, `.tfvars`, policy JSON templates (`*.json.tftpl`, for example
`deployer/boundaries/`) and `environments/*.json.example` (direct children only). It does
not open ignored local variables, state, plans, credential files, provider directories or
test fixtures (`*.tftest.hcl`). In a template, `${...}` and `%{...}` interpolations are
blanked before scanning (a placeholder is never read as a wildcard and line numbers are
unchanged); what they render to is not evaluated here, only by the plan tests.

The checks reject literal wildcard IAM actions outside an enclosing Deny, global
Allow resources, public Allow principals, public ACLs/all-users grants, and common
credential-shaped literals or literal credential assignments. Findings include
only path, line and category; source values are never printed. Exceptions apply
to individual statements: key-policy `Resource="*"` inside an `aws_kms_key`,
`ecr:GetAuthorizationToken` (which cannot use resource-level permissions), and
concrete `ec2:Describe...` actions on `Resource="*"`, and the exact actions below
(no IAM resource type). A statement is exempt only if every action in it is exempt;
mixing in any other action, a wildcard such as `kms:Create*`, or a service-wide
`elasticmapreduce:*` is still flagged. A neighboring rogue Allow is still rejected. Project-scoped object/index/log-stream suffix globs are allowed.

Allowlisted no-resource-type actions (exact, case-sensitive match; `NO_RESOURCE_TYPE_ACTIONS`
in the guard), verified by the infra owner against the AWS Service Authorization Reference:

- `tag:GetResources`
  (https://docs.aws.amazon.com/service-authorization/latest/reference/list_resourcegroupstaggingapi.html)
- `elasticmapreduce:ListClusters`, `elasticmapreduce:ListSecurityConfigurations`,
  `elasticmapreduce:DescribeSecurityConfiguration`,
  `elasticmapreduce:CreateSecurityConfiguration`,
  `elasticmapreduce:DeleteSecurityConfiguration`, `elasticmapreduce:RunJobFlow`
  (https://docs.aws.amazon.com/service-authorization/latest/reference/list_emr.html)
- `kms:CreateKey`, `kms:ListAliases`
  (https://docs.aws.amazon.com/service-authorization/latest/reference/list_kms.html)

The guard does not fetch or re-verify these URLs; the allowlist is a reviewed claim,
and other limitations below still apply.

### Statement-level global-resource allowlist (Phase 14A, decision 14-6)

`phase14_main.tf` has seven Allow statements on `Resource = "*"` whose actions are list-style reads or have no
resource type (Phase 14A); the USD 25 replan (W5a/W5b) adds three more entries, below. Each is one `GlobalGrant` entry in
`GLOBAL_RESOURCE_ALLOWLIST` (guard source) with the file path, the
EXACT action set, a justification and the Service Authorization Reference page. The exemption is per statement: the
same actions in another file, a subset, or a superset (one extra action) are still `global-iam-resource`. Six
entries also require the statement to keep a non-empty `Condition` (the region condition); a stripped condition is
`unconditioned-allowlisted-global-grant`. The Route 53 entry has no region condition because Route 53 is global and
is exempt from that requirement only. An entry that exempts nothing in the current tree is reported as
`stale-global-allowlist-entry`, so a moved or deleted statement cannot leave a silent pass behind.

| Statement (phase14_main.tf) | Exact actions | Page |
|---|---|---|
| Neptune describes | ten `rds:Describe*` actions | list_amazonrds.html |
| Alarms and dashboards | `cloudwatch:DescribeAlarms`, `ListDashboards` | list_amazoncloudwatch.html |
| Register task definition | `ecs:RegisterTaskDefinition` | list_amazonelasticcontainerservice.html |
| Task-definition lifecycle | `ecs:DeregisterTaskDefinition`, `DescribeTaskDefinition`, `DeleteTaskDefinitions` | list_amazonelasticcontainerservice.html |
| Load balancer describes | nine `elasticloadbalancing:Describe*` actions and `acm:DescribeCertificate` | list_elasticloadbalancingv2.html |
| Cloud Map and scaling reads | `servicediscovery:GetOperation` and three `application-autoscaling:Describe*` actions | list_awscloudmap.html, list_applicationautoscaling.html |
| Cloud Map private zone | nine `route53:` actions (create, get, list, delete, change, tags) | list_amazonroute53.html |

Replan additions (10 entries in total; each verified against the Service Authorization Reference by the test-engineer on
2026-11-08, pages fetched over HTTPS and read, not recalled):

| Statement | Exact actions | Rule beyond the exact action set |
|---|---|---|
| `phase14_main.tf`, ACM certificate request | `acm:RequestCertificate` | `list_acm.html` lists NO resource type for it (only condition keys). The statement must keep, in its Condition, the region lock (`c_region` or `aws:RequestedRegion`), `acm:ValidationMethod` = `"DNS"` and the request tags (`c_req_main` or an `aws:RequestTag/` key); a weakened one is `weakened-allowlisted-global-grant` |
| `deployer/boundaries/runtime.json.tftpl`, ECS Exec channels | `ssmmessages:CreateControlChannel`, `CreateDataChannel`, `OpenControlChannel`, `OpenDataChannel` | no condition (none applies to a Fargate task). CORRECTION to the request: `list_ssmmessages.html` lists no resource type for the first three, but `OpenDataChannel` lists the `session` resource type (`arn:<partition>:ssm:<region>:<account>:session/<SessionId>`); the session ID exists only after the ECS Exec session opens, and the AWS ECS guide (task-iam-roles.html) grants all four on `"*"`, so the guard accepts the four as one reviewed set, not as "no resource type" |
| `modules/identity/neptune_tunnel.tf`, tunnel task role | the same four | same set in the one file. The policy writes `Action = local.neptune_tunnel_actions`, so the guard resolves ONE same-file `name = [...]` literal list (zero or several definitions, or a `var.` reference, resolve to nothing and are not exempt) |

All pages are under https://docs.aws.amazon.com/service-authorization/latest/reference/. The justifications are the
infra owner's reviewed claims (statement comments and `deployer/README.md` "Honest list"); the test-engineer could
not reach those pages from the offline environment and did not re-verify them.

`test_guard_phase14.py` runs the guard CLI on a scratch git repository holding copies of the real files: the tree is
clean, a new unjustified global grant, an added or removed action, the same statements in a renamed file, a stripped
condition and a stale entry all fail, and a rogue grant in a `*.json.tftpl` or `environments/*.json.example` fails
while interpolations in the real boundary templates do not.

These are deliberately bounded text checks, not a complete HCL parser, IAM
evaluator or security scanner. They do not evaluate locals, variable-supplied
JSON, `aws_iam_policy_document` defaults, heredoc/encoded policy documents, dynamic
interpolation scope, effective permissions or live service behavior. Native
Terraform feature tests and the disclosed manual security review remain required.
The synthetic cases test unsafe fixtures without changing repository infrastructure.

## Request-tag-scoped actions must keep a condition (Phase 13C, review item 10)

`kms:CreateKey` and `elasticmapreduce:RunJobFlow` have no IAM resource type, so only request tags (and the region)
scope them. The guard therefore also reports `unconditioned-request-scoped-action` for an Allow statement that
names either action and has no `Condition`, an empty or `null` Condition, or a literal Condition with no
`aws:RequestTag/` key. A Condition built from locals or functions (for example `merge(local.c_region,
local.c_req_stack)`) cannot be evaluated by a literal-source check and is accepted here; the rendered policy
conditions, including the exact tag values, are asserted by `test_deployer_hardening.py`.

## Phase 13C test modules (`python3 -m unittest discover -s tests/infra -v`)

Offline and deterministic; they need terraform 1.13.5 and the providers that the `scripts/check.sh` terraform gate
installs in each root (a root that was not initialised makes them FAIL, never skip). Every mutation edits a scratch
copy under a temporary directory, never the repository.

- `test_spike_hardening.py`: spike root, review items 6 (mutation cases), 7 (`tags_all`) and 12.
- `test_deployer_hardening.py`: deployer root, items 10 (rendered conditions), 20 (tag values) and 21 (login attachment).
- `test_guard_conditions.py`: the guard inspects conditions (item 10).
- `test_static_sources.py`: text-only checks, item 12 (default security group) and the HCL scanner they use. Since 14A repair
  round 1 (review F2) neither the spike nor the main root and its modules may declare `aws_default_security_group`.
- `infra_support.py`, `spike_checks.py`, `deployer_checks.py`, `hcl_text.py`, `tftests/*.tftest.hcl`: support. The
  plan view is a real offline `terraform plan` (fake static credentials, `skip_*` flags, closed proxy); the state
  view is a `mock_provider` apply. Set `SC_INFRA_EVIDENCE_FILE` to keep a JSON-lines record of each mutation result.

## Second pass (Phase 13C): IAM items and the ported EMR module

- `test_iam_items_13c.py`: carried findings 2, 5 (spike key policy and main project key), 14, 16 and 17, each with scratch-copy mutations.
- `test_emr_module_13c.py`: the main EMR module (decision 12-10, TLS off, G2/G3, G6 bounds computed from `scripts/config`,
  EFS NFS-only, stack tag) through a scratch wrapper root; one `expectedFailure` documents a production finding
  (the optional task group does not pin `throughput`) and turns into a failure once that is fixed, prompting its removal.
- `emr_module_checks.py`, `tftests/emr_module_snapshot.tftest.hcl`: support.

## Phase 14A: the `phase14-main` deployer set, the main-root roles and the EMR network tag

The Phase 13 deployer suites (`test_deployer_hardening.py`, `test_iam_items_13c.py`) are retained spike-era evidence. Decision
14-6 changed the deployer's default `enabled_permission_sets` to `["phase14-main"]`, so `infra_support.ROOTS["deployer"]`
and `tftests/deployer_snapshot.tftest.hcl` now pin `["spike-emr"]` explicitly; no assertion was weakened. The new modules use
`ROOTS["deployer14"]` (no override, so the root's default is under test) and `ROOTS["main14"]` (the main root planned
offline with the real provider; the profile is nulled in a scratch override, all values synthetic).

- `phase14_checks.py`: named invariants, each hand-derived from decisions 14-6, D1 and D2 (selection, 6,144-character size and
  10-attachment limits, `aws:RequestedRegion` on every regional Allow with only IAM and Route 53 exempt, IAM scope to
  `scholarchain-<env>-*` and never the deployer or billing role, `iam:CreateRole` boundary condition, boundary-tamper and
  secret-read Denies, `iam:PassRole` with `iam:PassedToService`, no `*`, `*:*` or `<svc>:*` action, MFA trust and 3600 s
  session; in the main plan all 13 role instances of the seven role blocks carry the boundary the deployer root creates, and
  the EMR managed-policies tag is on exactly the application subnets and the two EMR security groups).
  Repair round 1 (F2) added three deployer checks and one main-root check: no IAM statement grants KMS administration, key use
  or grants (only `kms:CreateKey` and `kms:TagResource` with request tags and a literal `aws:TagKeys` list, plus alias actions on
  alias ARNs and `kms:ListAliases`); security-group Authorize/Revoke/Delete/ModifyRules need `aws:ResourceTag/project`;
  `ec2:CreateTags` that reaches a security group needs `ec2:CreateAction` or the project resource tag (so a foreign group cannot
  be tagged into scope); and the main plan has no `aws_default_security_group`.
- `test_phase14_main.py`: real-tree cases (including a changed environment name in both roots, and the longest environment
  name), one scratch-copy mutation per assertion (the over-6,144 pad is computed from the current document size), and
  `Phase14F2InMemory`, which edits a copy of the parsed plan in memory (no Terraform run) to prove each F2 check fires; each
  result goes to `$SC_INFRA_EVIDENCE_FILE` when set.
- `test_guard_phase14.py`: the guard's statement allowlist and its template coverage (see above).

## Phase 14B repair round 1: query-api grace period and explicit ALB health-check timing (review 1 finding B1, option (a))

- `test_phase14b_grace.py` with `phase14b_checks.py`: static, text-only, stdlib-only (no Terraform, no AWS). Hand-derived from
  the user's decision (it supersedes the earlier "grace default 120, module only" requirement, so the 120 assertions and the
  "root passes a different default" check are gone):
  - `aws_ecs_service.service` in `modules/runtime/compute.tf` sets `health_check_grace_period_seconds` only where the
    `dynamic "load_balancer"` block attaches (query-api with a certificate) and yields `null` for the other three services. Both
    conditions are EVALUATED for the four services with and without a certificate (after resolving `local.*`), so a shared local or
    an equivalent rewrite passes and a wrong condition fails.
  - The module grace variable: `type = number`, `default = 300`, and validation that accepts the default and rejects a negative, a
    fractional and a beyond-int32 value (the validation conditions are evaluated, not just looked for).
  - Root wiring: the root `module "runtime"` call passes the module grace variable as a plain `var.<name>` reference (a literal, an
    absent line, or an undeclared variable fails); that root variable has default 300 and the same validation; the example tfvars
    (`environments/course.local.tfvars.example`) documents it as a commented `# <name> = 300` line and never sets it uncommented.
  - Target group `aws_lb_target_group.query` health_check: path `"/readyz"`, matcher `"200"`, and explicit `interval`, `timeout`,
    `healthy_threshold`, `unhealthy_threshold`, each a `var.<name>` reference (never a literal) to a validated number variable with
    default 30 / 5 / 3 / 3.
  - Guards: a lifecycle precondition on `aws_ecs_service.service` is evaluated over a grid (grace, healthy, interval) for every
    service with and without a certificate; it must refuse a load-balanced grace below `healthy_threshold x interval` (89 refused,
    90 accepted for 3 x 30; 299 refused for 10 x 30) and must never block a service that carries no grace. A precondition on the
    target group must hold exactly when `timeout < interval`.
  - Hand-derived arithmetic from the module defaults: unhealthy after 3 x 30 = 90 s, recovery 3 x 30 = 90 s, default grace
    300 >= 90 with 300 - 90 = 210 >= 200 s left for peer readiness. The deployment circuit breaker stays `enable = true`,
    `rollback = true`.
- Three groups: `RealTree` (read only), `CheckerSelfTest` (a synthetic fixture must be clean, so a mutation cannot "fail" for
  another reason; the numeric evaluator and the inline-condition rewrite are also tested here) and `Mutations` (57 edits, each applied
  to an in-memory copy of the fixture and of the real text, so 114 results; the repository is never written; each must be reported
  with its own check id). `SC_INFRA_EVIDENCE_FILE` keeps the raw results as JSON lines (expected ids, found ids, caught).
- Limits: it does not run Terraform or the AWS provider's validation, so it cannot prove ECS or the ALB accept the plan; the
  `infra/terraform/tests/phase14b.tftest.hcl` and `phase14b_root.tftest.hcl` plan tests and the live apply are the other evidence.
  Real module and root text is read with comments stripped; the example tfvars is read raw. The guard is expected as a lifecycle
  precondition on the service resource (the infra-engineer's implementation); an equivalent guard elsewhere (a `check` block, a
  variable validation) would need the test extended deliberately. The evaluator supports numbers, strings, `each.key`,
  `var.<name>` from an explicit environment, `floor()`, `+ - * / %`, comparisons, `==`, `!=`, `&&`, `||`, `!` and the ternary; a
  condition outside that grammar fails with a `*-not-evaluable` or `*-validation-lax` id.

## Phase 14B replan under the USD 25 cap, PART 1 (test-engineer, 2026-11-08)

Independent tests from the requirements in `docs/agent-runs/phase-14/prompt.md` ("Subphase 14B - replan"); all offline, no AWS call,
repository files only read (every mutation edits a scratch copy).

- `test_runtime_shape_14b.py` with `runtime_shape_checks.py` (W1): a scratch root that calls a scratch copy of `modules/runtime` and of
  `modules/observability` with synthetic inputs (the required variables are discovered from `variables.tf`, so an added variable does
  not break the wrapper) and a REAL offline `terraform plan`; plus a providerless root holding the real `variable` blocks of
  `phase12b-variables.tf`. Container Insights off: cluster setting `disabled`, no `worker_backlog` policy, the three HTTP policies
  remain on the predefined `ECSServiceAverageCPUUtilization` metric, no `ECS/ContainerInsights` text anywhere in the plan; dashboard off:
  only the dashboard disappears; `service_capacity` accepts 256/1024 and 256/2048, refuses 256/512 and 256/4096; committed defaults
  512/1024 (worker max 4); the cheap values in `course.local.tfvars.example` are valid.
- `test_billing_replan_14b.py` with `account_scan.py` (W3): `ROOTS["billing"]` plan: limit 25, exactly three ACTUAL / ABSOLUTE_VALUE /
  GREATER_THAN alerts at 10, 15, 20, credits excluded, ceiling variable accepts only 25; `scripts/billing/modify-public-inputs.template.json`
  has no 12-digit number and the `<acct>` placeholder; a scan of what the working tree ADDS (diff against HEAD plus untracked files, not
  `docs/agent-runs/phase-12/**`) for a 12-digit run that is not `111122223333` or `000000000000`. It reports path and line only, never
  the digits. File-scoped synthetic values are listed in `SCOPED_SYNTHETIC` as named `ScopedSynthetic(name, value, path, pattern)`
  entries (see the account-scan notes below for the three entries and the 2026-11-09 user decision).
  Limit: after the work is committed the diff is empty, so the scan then covers only untracked files; rerun it before committing.
- `test_operator_roles_14b.py` with `operator_checks.py` (W5a): `ROOTS["deployer14ops"]`; invariants O1..O9 (default off; three named
  roles; MFA-only trust on the single operator; 14,400 s; same-device login policy; no `aws-marketplace` anywhere; no wildcard action;
  data-plane and run-prefix scope; the runtime boundary has the four ssmmessages actions and no Neptune load/write action) and an
  in-memory mutation for each.
- `test_guard_phase14.py` (`ReplanW5Grants`) and the guard self-test: the three new allowlist entries above.

## Phase 14B replan, PART 2 (test-engineer, 2026-11-08): W5b, W4 and W5a-3

- `test_phase14b_grace.py` / `phase14b_checks.py`: the module's HTTPS decision is now `local.https = var.https_enabled != null ?
  var.https_enabled : var.certificate_arn != null`. The evaluator knows `var.https_enabled`; load balancing and the grace period are
  checked over the scenario grid (certificate none/some x https_enabled null/true/false): query-api is load balanced exactly when HTTPS
  is on, the grace period follows it, every other service gets null. `check_root_https` evaluates the root's plan-time boolean over
  `https_certificate_arn x api_domain_name x runtime_enabled x image_revision` (true exactly with an external certificate, or a managed one
  validated in the same apply); it must never read a resource attribute. Nine new mutations; the synthetic fixture mirrors the new shape.
- `test_w5b_w4_14b.py` with `main_root_shape.py` and `tftests/runtime_module_snapshot.tftest.hcl`:
  - `AcmCertificate`: real offline plans of the main root. Base stage: one DNS-validated certificate, no `aws_acm_certificate_validation`,
    no listener or ALB. Runtime stage: exactly one validation (15m default, no fqdn list) and a listener whose certificate is unknown until
    the validation. An external certificate excludes the managed one; exactly-one-source, domain and timeout validations; tags satisfy the
    deployer's tag conditions; the validation-record, certificate-ARN and `alb_dns_name` outputs; source-level proof that the listener
    uses the validation attribute, never the raw certificate.
  - `RepositoryHasNoRealDomain`: every quoted value assigned to `api_domain_name` in Git-visible files (not Phase 12 evidence) ends in `example.invalid`.
  - `NeptuneTunnel` / `TunnelContainer`: absent by default and without a deployed runtime; role name, runtime boundary (equal to the task
    roles'), trust, exactly the four ssmmessages actions; task definition family, Fargate 256/512, sleep entrypoint, init process,
    graph-service image and execution role, no environment, secrets or ports (container definitions come from a mock-provider apply of a
    scratch wrapper, because the real provider leaves them unknown offline); no ECS service for it; the writer endpoint, port, cluster
    resource id and tunnel outputs.
  - `CleanupPurge`: no `prevent_destroy` in the data lake or S3 Vectors modules (and none anywhere in the main root except the state backend
    bootstrap and the budget); `force_destroy` false by default and true only with `cleanup_mode`; the pinned teardown and preserve rules in
    `scripts/config/release.conf`; every cloud resource of the full plan classified (only `terraform_data` guards stay unlisted).
  - `DeployerDeleteGrant`: the five W5a-3 points on the rendered deployer documents.
- `tests/scripts/test_upload_slice_14b.py`: `scripts/upload-slice.sh` against a fake `aws` written in the test (a directory-backed S3 plus
  sts): dry run (no aws call, nothing written), refusals, `put-object` with SHA-256 and `--if-none-match`, `head-object` verification,
  manifest with `<acct>`, idempotent re-run, partial completion, put failure (exit 5) and verification failure (exit 4).
- Account scan (see the final-round notes below): the file-scoped synthetic exceptions in `account_scan.py` (`SCOPED_SYNTHETIC`: the second fake account in
  `infra/terraform/**/tests/*.tftest.hcl` and the foreign account in `scripts/tests/test_upload_slice.py`) were confirmed synthetic by the
  coordinator (2026-11-08) and stay (named `infra-tftest-second-account` and `upload-slice-test-account`, still scoped by a regex `pattern`).
  The third entry, named `aws-documentation-example-account`, was accepted by the user on 2026-11-09 under these conditions: it covers only
  AWS's documentation example account, only in `modules/services/src/test/scala/edu/uic/cs441/scholarchain/services/AwsTestSupport.scala`,
  as a named, file-scoped allowlist entry, not a pattern. Its `path` is an exact repository-relative string compared with `==` (no regex,
  `pattern` is `None`); the scanner still fails on any other 12-digit account ID in that file and on that example ID in any other file
  (a sibling file, a different case, a prefix or a suffix included). Tests: `AwsDocumentationExampleAccountEntry` in
  `test_billing_replan_14b.py`; the value is split in the source so that the tests hold no literal 12-digit run.

## Phase 14B replan, FINAL ROUND (test-engineer, 2026-11-08)

- Weak catches closed. `AcmCertificate` no longer plans in `setUpClass`: a failing plan fails each test that needs it, and
  `test_the_base_stage_plan_succeeds_and_contains_exactly_one_api_certificate` asserts exactly one `aws_acm_certificate.api` directly
  (mutant A3b, a coherent "certificate only with the runtime", plans fine and is caught only by it). The fake `aws` of the upload tests
  (`tests/scripts/fake_s3.py`) behaves like S3 and no longer refuses a missing `--if-none-match` itself: the tests assert on the recorded
  `put-object` argv and on a race (a key created just before the put is never overwritten).
- `operator_checks.py` / `test_operator_roles_14b.py`: FOUR operator roles (loader, reader, cleanup, pipeline). Pipeline invariants P1..P7
  (MFA trust, 14,400 s, no boundary, same-device login; exactly the seven EMR actions on `cluster/*` with region plus project, environment and
  stack tag conditions; nothing that starts or ends a cluster, deletes objects or touches IAM/STS/EC2/ECS; PutObject create-only under artifacts
  `emr/<run>/` only, read-only on `pipeline/<run>/` and the `emr/` logs; KMS through S3 only; services limited to elasticmapreduce, s3, kms) and
  the loader runtime-artifact invariant L1 (create-only PutObject on rag `runtime-artifacts/<run>/*`, read-back, no delete, no other writer).
- `test_gmain_14b.py`: the runtime-artifact pointer (root guards by real plans; container environments by a mock apply of `modules/runtime`;
  the query-api policy by a mock apply of `modules/identity`, `tftests/identity_module_snapshot.tftest.hcl`).
- `tests/scripts`: `test_upload_emr_artifacts_14b.py`, `test_experiment_tokens_14b.py`, `test_smoke_checks_14b.py`, `test_llm_budget_14b.py`;
  `PIPELINE_CEILING_MAX_LOCAL_SAMPLE_RECORDS` is 12,000 (pipeline-specific) while `phase4-emr-smoke.sh` keeps 1,000 and the other six ceilings stay
  equal to Phase 4 (`sc_support.CEILINGS`, `test_pipeline_refusals.py`, `test_pipeline_dryrun.py`).
