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
