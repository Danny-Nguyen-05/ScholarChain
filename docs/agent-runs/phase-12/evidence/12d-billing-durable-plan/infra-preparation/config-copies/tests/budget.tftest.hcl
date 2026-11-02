mock_provider "aws" {
  override_during = plan
  mock_resource "aws_budgets_budget" {
    defaults = { cost_filter = [], filter_expression = [] }
  }
}
variables {
  aws_account_id = "111122223333"
  aws_profile    = "synthetic-no-login"
  aws_region     = "us-east-2"
  budget_name    = "synthetic-project-budget"
  resource_tags = {
    course      = "SYNTH441"
    project     = "tag-probe"
    environment = "offline"
    owner       = "synthetic-owner"
  }
  project_period_start_utc = "2026-10-01_00:00"
  project_period_end_utc   = "2027-01-01_00:00"
}
run "disabled_by_default" {
  command = plan
  assert {
    condition     = !output.controls.enabled && output.controls.budget == null
    error_message = "Offline authoring must not enable a budget by default."
  }
}
run "one_cumulative_before_credit_account_budget" {
  command = plan
  variables {
    enable_budget              = true
    budget_notification_emails = ["synthetic@example.invalid"]
  }
  assert {
    condition     = output.controls.budget.account_id == "111122223333" && tonumber(output.controls.budget.amount) == 200 && output.controls.budget.currency == "USD" && output.controls.budget.period == "CUSTOM" && output.controls.budget.start == "2026-10-01_00:00" && output.controls.budget.end == "2027-01-01_00:00" && length(output.controls.budget.filters) == 0 && length(output.controls.budget.expression) == 0
    error_message = "One account-wide USD 200 CUSTOM period must cover October and November without a reset or tag filter."
  }
  assert {
    condition = output.controls.budget.tags == tomap({
      course          = "SYNTH441"
      project         = "tag-probe"
      environment     = "offline"
      owner           = "synthetic-owner"
      expiration_date = "2027-01-01"
    })
    error_message = "The budget resource must carry all five configured ownership tags, with expiration tied to its reconciliation end."
  }
  assert {
    condition     = !output.controls.budget.cost_types[0].include_credit && !output.controls.budget.cost_types[0].include_refund && output.controls.budget.cost_types[0].include_tax && output.controls.budget.cost_types[0].include_support && !output.controls.budget.cost_types[0].use_blended && !output.controls.budget.cost_types[0].use_amortized
    error_message = "Credits/refunds must not hide pre-credit project usage; include taxes and support."
  }
  assert {
    condition     = length(output.controls.budget.notifications) == 3 && toset([for n in output.controls.budget.notifications : n.threshold]) == toset([50, 80, 100]) && alltrue([for n in output.controls.budget.notifications : n.comparison == "GREATER_THAN" && n.type == "PERCENTAGE" && n.basis == "ACTUAL"])
    error_message = "Require exactly the three actual-spend percentage alerts: USD 100, 160 and 200."
  }
}
run "cannot_enable_without_private_subscriber" {
  command = plan
  variables { enable_budget = true }
  expect_failures = [aws_budgets_budget.project]
}
run "cannot_raise_shared_budget" {
  command = plan
  variables { budget_limit_usd = 400 }
  expect_failures = [var.budget_limit_usd]
}
run "end_must_follow_start" {
  command = plan
  variables { project_period_end_utc = "2026-09-01_00:00" }
  expect_failures = [var.project_period_end_utc]
}

run "expiration_follows_budget_reconciliation_end" {
  command = plan
  variables {
    enable_budget              = true
    budget_notification_emails = ["synthetic@example.invalid"]
    project_period_end_utc     = "2027-02-03_06:00"
  }
  assert {
    condition     = output.controls.budget.tags["expiration_date"] == "2027-02-03"
    error_message = "Budget expiration must follow its own retention/reconciliation end, not the stack's November 25 date."
  }
}
run "blank_required_tag_is_rejected" {
  command = plan
  variables {
    resource_tags = {
      course      = "SYNTH441"
      project     = "tag-probe"
      environment = "offline"
      owner       = " "
    }
  }
  expect_failures = [var.resource_tags]
}
