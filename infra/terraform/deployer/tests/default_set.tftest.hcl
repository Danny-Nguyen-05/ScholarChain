# The variable default itself (no enabled_permission_sets override): decision 14-6 removes spike-emr and enables phase14-main.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id             = "111122223333"
  operator_principal_arn = "arn:aws:iam::111122223333:user/example-operator"
  owner                  = "example-owner"
}

run "p14_default_enabled_set_is_phase14_main_only" {
  command = plan

  assert {
    condition     = toset(var.enabled_permission_sets) == toset(["phase14-main"])
    error_message = "The default enabled_permission_sets must be exactly phase14-main (spike-emr removed)."
  }
  assert {
    condition     = length(aws_iam_policy.permission_set) == 7 && alltrue([for k, p in aws_iam_policy.permission_set : startswith(k, "phase14-main--")])
    error_message = "The default plan attaches the seven phase14-main documents and nothing from the spike."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary) == 0 && length(aws_iam_policy.main_boundary_runtime) == 1 && length(aws_iam_policy.main_boundary_emr) == 1
    error_message = "The default plan creates the two main boundaries and no spike boundary."
  }
}
