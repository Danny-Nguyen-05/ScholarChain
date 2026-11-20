variable "name_prefix" { type = string }
variable "aws_region" { type = string }
variable "retention_days" { type = number }
variable "notification_arns" { type = set(string) }
variable "application_namespace" { type = string }
variable "api_error_percent" { type = number }
variable "latency_seconds" { type = number }
variable "queue_age_seconds" { type = number }
variable "queue_name" { type = string }
variable "table_names" { type = map(string) }
variable "neptune_identifier" { type = string }
variable "emr_cluster_id" { type = string }
variable "tags" { type = map(string) }
variable "workflow_arn" { type = string }
variable "dashboard_enabled" {
  type        = bool
  default     = true
  nullable    = false
  description = "Create the elasticity dashboard (count 1) or not (count 0). The log groups and alarms do not depend on it."
}
# Phase 15 P41: CloudWatch dimension values of the query ALB and its target group (the ARN suffixes app/<name>/<id> and
# targetgroup/<name>/<id>), from module.runtime.alb_metric_dimensions. null while no ALB exists: then no ALB panel.
variable "alb_metric_dimensions" {
  type        = object({ load_balancer = string, target_group = string })
  default     = null
  nullable    = true
  description = "ALB and target-group ARN suffixes for the dashboard request panel; null (no ALB) omits the panel."
}
