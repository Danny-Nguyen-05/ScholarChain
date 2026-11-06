# Terraform literal-source checks

Run from the repository root:

```bash
python3 -I tests/infra/terraform_source_guard.py --self-test
python3 -I tests/infra/terraform_source_guard.py --repo-root .
```

`IndependentTerraformSourceSpec` runs both commands during the independent test
project's normal `sbt check` gate. The helper uses Python's standard library only,
does not call AWS, and only opens Git-visible `.tf` and `.tfvars` files under
`infra/terraform`. It does not open ignored local variables, state, plans,
credential files, provider directories or test fixtures (`*.tftest.hcl`).

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
- `test_static_sources.py`: text-only checks, item 12 (default security group) and the HCL scanner they use.
- `infra_support.py`, `spike_checks.py`, `deployer_checks.py`, `hcl_text.py`, `tftests/*.tftest.hcl`: support. The
  plan view is a real offline `terraform plan` (fake static credentials, `skip_*` flags, closed proxy); the state
  view is a `mock_provider` apply. Set `SC_INFRA_EVIDENCE_FILE` to keep a JSON-lines record of each mutation result.

## Second pass (Phase 13C): IAM items and the ported EMR module

- `test_iam_items_13c.py`: carried findings 2, 5 (spike key policy and main project key), 14, 16 and 17, each with scratch-copy mutations.
- `test_emr_module_13c.py`: the main EMR module (decision 12-10, TLS off, G2/G3, G6 bounds computed from `scripts/config`,
  EFS NFS-only, stack tag) through a scratch wrapper root; one `expectedFailure` documents a production finding
  (the optional task group does not pin `throughput`) and turns into a failure once that is fixed, prompting its removal.
- `emr_module_checks.py`, `tftests/emr_module_snapshot.tftest.hcl`: support.
