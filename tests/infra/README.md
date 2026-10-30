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
concrete `ec2:Describe...` actions on `Resource="*"`. A neighboring rogue Allow
is still rejected. Project-scoped object/index/log-stream suffix globs are allowed.

These are deliberately bounded text checks, not a complete HCL parser, IAM
evaluator or security scanner. They do not evaluate locals, variable-supplied
JSON, `aws_iam_policy_document` defaults, heredoc/encoded policy documents, dynamic
interpolation scope, effective permissions or live service behavior. Native
Terraform feature tests and the disclosed manual security review remain required.
The synthetic cases test unsafe fixtures without changing repository infrastructure.
