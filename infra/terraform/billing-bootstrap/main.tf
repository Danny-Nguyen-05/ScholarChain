provider "aws" {
  region              = var.aws_region
  profile             = var.aws_profile
  allowed_account_ids = [var.aws_account_id]
}

locals {
  # This monitor outlives the stack: its date follows retention/reconciliation,
  # never the main stack's provisional November 25 expiration.
  required_tags = merge(var.resource_tags, {
    expiration_date = try(formatdate("YYYY-MM-DD", "${replace(var.project_period_end_utc, "_", "T")}:00Z"), "")
  })
}

# A fixed CUSTOM period prevents an October/November monthly reset from
# presenting two separate allowances. No region/service/tag filters.
# Phase 14B replan: the ceiling is the professor's USD 25 course cap (the
# budget was created at USD 200 in Phase 12D and is moved here by an in-place
# update; see README "Phase 14B: modify the live budget to USD 25").
resource "aws_budgets_budget" "project" {
  count             = var.enable_budget ? 1 : 0
  account_id        = var.aws_account_id
  name              = var.budget_name
  budget_type       = "COST"
  limit_amount      = tostring(var.budget_limit_usd)
  limit_unit        = "USD"
  time_unit         = "CUSTOM"
  time_period_start = var.project_period_start_utc
  time_period_end   = var.project_period_end_utc
  tags              = local.required_tags
  cost_types {
    include_credit             = false
    include_refund             = false
    include_discount           = true
    include_other_subscription = true
    include_recurring          = true
    include_subscription       = true
    include_support            = true
    include_tax                = true
    include_upfront            = true
    use_amortized              = false
    use_blended                = false
  }
  # Human decision 2026-11-15: actual-spend alerts at fixed dollar amounts under
  # the USD 25 cap (USD 18/20/22, ABSOLUTE_VALUE, not percentages; this replaces
  # the never-applied 10/15/20 set). AWS charges only; credits and refunds are
  # excluded above. Monitoring only, not a spending stop. Notifications are
  # inline blocks, so changing them is an in-place update of this one resource,
  # never a replacement.
  dynamic "notification" {
    for_each = toset([18, 20, 22])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "ABSOLUTE_VALUE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.budget_notification_emails
    }
  }
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = length(var.budget_notification_emails) > 0
      error_message = "Enabling the budget requires a private notification recipient."
    }
  }
}
