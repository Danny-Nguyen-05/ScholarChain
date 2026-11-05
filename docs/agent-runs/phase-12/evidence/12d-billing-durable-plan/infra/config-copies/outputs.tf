# Deliberately expose neither the recipient nor the complete notification block.
output "controls" {
  # Terraform conservatively propagates sensitivity from the provider's complete
  # notification set even though this projection omits every recipient field.
  sensitive = true
  value = {
    enabled = var.enable_budget
    budget = one([for budget in aws_budgets_budget.project : {
      account_id = budget.account_id
      amount     = budget.limit_amount
      currency   = budget.limit_unit
      period     = budget.time_unit
      start      = budget.time_period_start
      end        = budget.time_period_end
      filters    = budget.cost_filter
      expression = budget.filter_expression
      cost_types = budget.cost_types
      tags       = budget.tags
      notifications = [for n in budget.notification : {
        comparison = n.comparison_operator
        threshold  = n.threshold
        type       = n.threshold_type
        basis      = n.notification_type
      }]
    }])
  }
}
