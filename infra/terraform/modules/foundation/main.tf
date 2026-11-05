locals {
  tags = merge(var.additional_tags, {
    course          = var.course
    project         = var.project
    environment     = var.environment
    owner           = var.owner
    expiration_date = var.expiration_date
  })
}
resource "aws_budgets_budget" "course" {
  count        = var.enable_budget ? 1 : 0
  name         = "${var.name_prefix}-monthly-budget"
  budget_type  = "COST"
  limit_amount = tostring(var.budget_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  cost_filter {
    name   = "TagKeyValue"
    values = [format("user:project$%s", var.project)]
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = var.notification_threshold_percent
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.notification_emails
  }
  tags = local.tags
  lifecycle {
    precondition {
      condition     = length(var.notification_emails) > 0
      error_message = "Budget notifications require actual human-supplied subscriber addresses."
    }
  }
}
