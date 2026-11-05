output "tags" { value = local.tags }
output "budget_controls" {
  value = {
    enabled         = var.enable_budget
    limit_usd       = var.budget_limit_usd
    notification_at = var.notification_threshold_percent
    scope           = "project-tag-monthly"
  }
}
