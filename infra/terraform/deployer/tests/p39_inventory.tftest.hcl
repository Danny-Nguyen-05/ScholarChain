# P39 (deployer role removal after Session 2): the inventory this configuration defines once the operator roles are off
# (operator_roles_enabled = false) and the default permission set is enabled. It is derived from the code, not read from any
# real state: the P39 section of the README (block 2) checks the real state against the same 18 addresses. Mock-only; nothing
# is read from or sent to AWS.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id             = "111122223333"
  operator_principal_arn = "arn:aws:iam::111122223333:user/example-operator"
  owner                  = "example-owner"
  operator_roles_enabled = false
}

run "p39_state_after_c4_is_18_resources" {
  command = plan

  # 1 role + 1 inline login policy
  assert {
    condition     = aws_iam_role.deployer.name == "scholarchain-deployer" && aws_iam_role_policy.login.name == "scholarchain-deployer-same-device-login"
    error_message = "The deployer role and its same-device login inline policy must both be in the root."
  }
  # 7 permission-set policies and 7 attachments, keyed exactly as the P39 address list says
  assert {
    condition = toset(keys(aws_iam_policy.permission_set)) == toset([
      "phase14-main--compute", "phase14-main--data", "phase14-main--emr-efs", "phase14-main--iam",
      "phase14-main--keys-obs", "phase14-main--network", "phase14-main--network-mod",
    ])
    error_message = "The seven phase14-main policies are compute, data, emr-efs, iam, keys-obs, network, network-mod."
  }
  assert {
    condition     = toset(keys(aws_iam_role_policy_attachment.permission_set)) == toset(keys(aws_iam_policy.permission_set))
    error_message = "One attachment per permission-set policy."
  }
  # 2 boundaries, no spike boundary
  assert {
    condition     = length(aws_iam_policy.main_boundary_runtime) == 1 && length(aws_iam_policy.main_boundary_emr) == 1 && length(aws_iam_policy.spike_boundary) == 0
    error_message = "Two main boundaries, no spike boundary."
  }
  # operator roles are off: nothing from operator_roles.tf or operator_pipeline.tf
  assert {
    condition = (
      length(aws_iam_role.operator) == 0 && length(aws_iam_role_policy.operator) == 0 && length(aws_iam_role_policy.operator_login) == 0 &&
      length(aws_iam_role.operator_pipeline) == 0 && length(aws_iam_role_policy.operator_pipeline) == 0 && length(aws_iam_role_policy.operator_pipeline_login) == 0
    )
    error_message = "With operator_roles_enabled = false no operator or pipeline role resource exists."
  }
  # the total: 1 + 1 + 7 + 7 + 2 = 18
  assert {
    condition     = 1 + 1 + length(aws_iam_policy.permission_set) + length(aws_iam_role_policy_attachment.permission_set) + length(aws_iam_policy.main_boundary_runtime) + length(aws_iam_policy.main_boundary_emr) == 18
    error_message = "The configuration defines exactly 18 resources with the operator roles off."
  }
}
