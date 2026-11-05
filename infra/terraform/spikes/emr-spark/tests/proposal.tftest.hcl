mock_provider "aws" { override_during = plan }
run "bounded_single_attempt_proposal" {
  command = plan
  assert {
    condition     = output.proposal.primary_nodes == 1 && output.proposal.core_nodes == 1 && output.proposal.task_nodes == 0 && output.proposal.spot_nodes == 0 && output.proposal.instance_type == "m5.xlarge" && output.proposal.region == "us-east-2" && output.proposal.maximum_attempts == 1
    error_message = "The proposal is exactly one primary and one core m5.xlarge in Ohio, no task or Spot nodes, one attempt."
  }
  assert {
    condition     = output.proposal.maximum_total_runtime_hours == 2 && output.proposal.spike_allowance_usd == 5 && output.proposal.shared_project_ceiling_usd == 200
    error_message = "The proposed two-hour/USD 5 envelope is part of the shared USD 200."
  }
  assert {
    condition     = !output.proposal.launchable && !output.proposal.live_compatibility_verified && output.proposal.aws_resources_declared == 0 && length(output.proposal.unresolved_prerequisites) == 8
    error_message = "A proposal with unresolved prerequisites must never claim live proof or executable cluster resources."
  }
}
run "launch_is_unconditionally_blocked" {
  command = plan
  variables { launch_requested = true }
  expect_failures = [var.launch_requested]
}
run "cannot_raise_spike_allowance" {
  command = plan
  variables { spike_allowance_usd = 6 }
  expect_failures = [var.spike_allowance_usd]
}
run "cannot_extend_runtime" {
  command = plan
  variables { maximum_total_runtime_hours = 3 }
  expect_failures = [var.maximum_total_runtime_hours]
}
run "cannot_change_instance_shape" {
  command = plan
  variables { instance_type = "m5.24xlarge" }
  expect_failures = [var.instance_type]
}
run "cannot_change_region" {
  command = plan
  variables { region = "us-west-2" }
  expect_failures = [var.region]
}
