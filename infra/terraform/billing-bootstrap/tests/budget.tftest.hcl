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
    condition     = output.controls.budget.account_id == "111122223333" && tonumber(output.controls.budget.amount) == 25 && output.controls.budget.currency == "USD" && output.controls.budget.period == "CUSTOM" && output.controls.budget.start == "2026-10-01_00:00" && output.controls.budget.end == "2027-01-01_00:00" && length(output.controls.budget.filters) == 0 && length(output.controls.budget.expression) == 0
    error_message = "One account-wide USD 25 CUSTOM period must cover October and November without a reset or tag filter."
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
    condition     = length(output.controls.budget.notifications) == 3
    error_message = "Require exactly three budget notifications."
  }
  assert {
    condition     = alltrue([for n in output.controls.budget.notifications : n.comparison == "GREATER_THAN" && n.type == "ABSOLUTE_VALUE" && n.basis == "ACTUAL"])
    error_message = "Every notification must be ACTUAL, ABSOLUTE_VALUE and GREATER_THAN."
  }
  # Hand-written expectation from the 2026-11-15 human decision, not derived
  # from main.tf: USD 18, 20 and 22.
  assert {
    condition     = toset([for n in output.controls.budget.notifications : tonumber(n.threshold)]) == toset([18, 20, 22])
    error_message = "Require exactly the actual-spend dollar alerts USD 18, 20 and 22 (2026-11-15 decision)."
  }
  assert {
    condition     = !anytrue([for n in output.controls.budget.notifications : n.type == "PERCENTAGE"]) && !anytrue([for n in output.controls.budget.notifications : n.basis == "FORECASTED"])
    error_message = "No PERCENTAGE or FORECASTED alert may remain after the USD 25 replan."
  }
  # USD 20 belongs to both the superseded 10/15/20 set and the new set, so the
  # superseded set is refused as a whole and through its two unique members.
  assert {
    condition     = toset([for n in output.controls.budget.notifications : tonumber(n.threshold)]) != toset([10, 15, 20]) && !anytrue([for n in output.controls.budget.notifications : contains([10, 15], tonumber(n.threshold))])
    error_message = "The superseded, never-applied USD 10/15/20 alert set must not remain."
  }
  assert {
    condition     = !anytrue([for n in output.controls.budget.notifications : contains([50, 80, 100], tonumber(n.threshold))])
    error_message = "No legacy 50/80/100 alert may remain after the USD 25 replan."
  }
  assert {
    condition     = alltrue([for n in output.controls.budget.notifications : tonumber(n.threshold) < 25]) && alltrue([for n in output.controls.budget.notifications : tonumber(n.threshold) < tonumber(output.controls.budget.amount)])
    error_message = "Every dollar alert must sit strictly below the USD 25 ceiling."
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
run "superseded_usd_200_ceiling_is_rejected" {
  command = plan
  variables { budget_limit_usd = 200 }
  expect_failures = [var.budget_limit_usd]
}
run "amount_just_above_cap_is_rejected" {
  command = plan
  variables { budget_limit_usd = 26 }
  expect_failures = [var.budget_limit_usd]
}
run "amount_just_below_cap_is_rejected" {
  command = plan
  variables { budget_limit_usd = 24 }
  expect_failures = [var.budget_limit_usd]
}
run "zero_amount_is_rejected" {
  command = plan
  variables { budget_limit_usd = 0 }
  expect_failures = [var.budget_limit_usd]
}
run "default_amount_is_the_course_cap" {
  command = plan
  variables {
    enable_budget              = true
    budget_notification_emails = ["synthetic@example.invalid"]
  }
  assert {
    condition     = tonumber(output.controls.budget.amount) == 25 && var.budget_limit_usd == 25
    error_message = "Omitting budget_limit_usd must yield the USD 25 cap, not the superseded USD 200."
  }
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
