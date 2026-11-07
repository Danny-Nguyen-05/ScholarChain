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
resource type. Each is one `GlobalGrant` entry in `GLOBAL_RESOURCE_ALLOWLIST` (guard source) with the file path, the
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
