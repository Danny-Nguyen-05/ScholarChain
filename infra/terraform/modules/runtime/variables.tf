variable "name_prefix" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "tags" { type = map(string) }
variable "enabled" { type = bool }
variable "composition_verified" { type = bool }
variable "image_revision" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }
variable "application_subnets" { type = list(string) }
variable "public_subnets" { type = list(string) }
variable "security_groups" { type = map(string) }
variable "task_roles" { type = map(string) }
variable "execution_roles" { type = map(string) }
variable "service_secret_bindings" { type = map(map(string)) }
variable "capacity" { type = map(object({ cpu = number, memory = number, min = number, max = number })) }
variable "cpu_target" { type = number }
variable "container_insights_enabled" {
  type        = bool
  default     = true
  nullable    = false
  description = "ECS cluster setting containerInsights = enabled (true) or disabled (false). Container Insights bills custom metrics and logs. When false the embedding-worker backlog-per-running-task policy is not created because its RunningTaskCount metric exists only with Container Insights; the free AWS/ECS CPU target-tracking policies are unaffected."
}
variable "backlog_target" { type = number }
variable "service_port" { type = number }
variable "certificate_arn" { type = string }
variable "health_check_grace_period_seconds" {
  type        = number
  default     = 300
  description = "Seconds ECS ignores failing ALB health checks after a query-api task starts. Applied only to the load-balanced query-api service (null elsewhere; ECS rejects it without a load balancer). Sized for the first apply, where query-api's /readyz waits for graph-service and semantic-service that start at the same time: peers ready (about 200 s at most) plus healthy_threshold x interval (90 s by default) of passing checks. A precondition on the service requires it to be at least healthy_threshold x interval. Tuned from the root variable query_health_check_grace_period_seconds."
  validation {
    condition     = var.health_check_grace_period_seconds >= 0 && var.health_check_grace_period_seconds <= 3600 && var.health_check_grace_period_seconds == floor(var.health_check_grace_period_seconds)
    error_message = "health_check_grace_period_seconds must be a whole number of seconds from 0 to 3600 (a longer grace hides a task that never becomes ready and delays the circuit breaker)."
  }
}
# Explicit ALB target-group health-check timing for query-api (/readyz, matcher 200). Set explicitly because the defaults differ:
# the ELBv2 API documents 30 s / unhealthy 2 / healthy 5, the aws provider documents 30 s / 3 / 3. Limits are the ELBv2 HealthCheck
# limits: interval 5-300 s, thresholds 2-10, timeout 2-120 s (and timeout must be smaller than interval; a precondition on the
# target group checks that). Not wired from the root: the grace period is the tunable; these stay module defaults.
variable "health_check_interval_seconds" {
  type        = number
  default     = 30
  description = "Seconds between ALB health checks of a query-api target (ELBv2 range 5-300)."
  validation {
    condition     = var.health_check_interval_seconds >= 5 && var.health_check_interval_seconds <= 300 && var.health_check_interval_seconds == floor(var.health_check_interval_seconds)
    error_message = "health_check_interval_seconds must be a whole number of seconds from 5 to 300."
  }
}
variable "health_check_timeout_seconds" {
  type        = number
  default     = 5
  description = "Seconds without a response that count as a failed ALB health check (ELBv2 range 2-120; must be smaller than the interval). 5 is the ELBv2 default for HTTP targets, made explicit so a shorter interval cannot silently produce an invalid pair."
  validation {
    condition     = var.health_check_timeout_seconds >= 2 && var.health_check_timeout_seconds <= 120 && var.health_check_timeout_seconds == floor(var.health_check_timeout_seconds)
    error_message = "health_check_timeout_seconds must be a whole number of seconds from 2 to 120."
  }
}
variable "health_check_healthy_threshold" {
  type        = number
  default     = 3
  description = "Consecutive passing checks before a target is healthy (ELBv2 range 2-10). Recovery after an unhealthy mark takes this many intervals."
  validation {
    condition     = var.health_check_healthy_threshold >= 2 && var.health_check_healthy_threshold <= 10 && var.health_check_healthy_threshold == floor(var.health_check_healthy_threshold)
    error_message = "health_check_healthy_threshold must be a whole number from 2 to 10."
  }
}
variable "health_check_unhealthy_threshold" {
  type        = number
  default     = 3
  description = "Consecutive failing checks before a target is unhealthy (ELBv2 range 2-10)."
  validation {
    condition     = var.health_check_unhealthy_threshold >= 2 && var.health_check_unhealthy_threshold <= 10 && var.health_check_unhealthy_threshold == floor(var.health_check_unhealthy_threshold)
    error_message = "health_check_unhealthy_threshold must be a whole number from 2 to 10."
  }
}
variable "queue_name" { type = string }
variable "queue_url" { type = string }
variable "dlq_url" { type = string }
variable "table_names" { type = map(string) }
variable "neptune_endpoint" { type = string }
variable "vector_bucket" { type = string }
variable "log_groups" { type = map(string) }

# Task environment of the aws service mode (SCHOLARCHAIN_SERVICE_MODE=aws; contract: modules/services/README.md and AwsConfig.scala).
# Every value is supplied by the root from a resource output or a variable; nothing is compiled in here.
variable "rag_bucket" { type = string }
variable "graph_bucket" { type = string }
variable "embedding_model_id" { type = string }
variable "embedding_model_version" {
  type    = string
  default = null
}
variable "vector_dimension" { type = number }
variable "vector_metric" { type = string }
variable "query_session_index" { type = string }
variable "queue_visibility_seconds" { type = number }
variable "queue_wait_seconds" { type = number }
variable "semantic_index" { type = string }
variable "embedding_text_prefix" { type = string }
variable "evidence_index_prefix" { type = string }
variable "audit_prefix" { type = string }
variable "synthesis_model_id" {
  type    = string
  default = null
}
variable "synthesis_inference_profile_id" {
  type    = string
  default = null
}

# Replan G-MAIN (G3): the runtime-artifact pointer. Reaches the query-api task environment only (the only role whose AwsConfig reads it),
# only in the aws mode and only when all three are set. The bucket is optional: null leaves the services default (the rag bucket); the root
# guard allows only the rag bucket's own name.
variable "runtime_artifact_bucket" {
  type    = string
  default = null
}
variable "runtime_artifact_key" {
  type    = string
  default = null
}
variable "runtime_artifact_sha256" {
  type    = string
  default = null
}
variable "runtime_artifact_source_run_id" {
  type    = string
  default = null
}

# Replan W5b: the HTTPS decision as a plan-time boolean. The root passes true when the listener certificate is an ACM certificate
# created by the same apply (aws_acm_certificate_validation.certificate_arn is unknown at plan time, and a count that depends on an
# unknown value cannot be planned). null keeps the earlier rule: HTTPS exactly when certificate_arn is set.
variable "https_enabled" {
  type        = bool
  default     = null
  description = "null: HTTPS iff certificate_arn is not null (unchanged behavior). true/false: decided by the caller from plan-time values; certificate_arn may then be unknown until apply."
}

# Replan W5b (user decision 1): the temporary Neptune tunnel. A task definition only (no ECS service): the operator starts it with
# `aws ecs run-task --enable-execute-command` for the load window and stops it afterwards, so nothing runs or bills between loads.
variable "neptune_tunnel_enabled" {
  type        = bool
  default     = false
  nullable    = false
  description = "Register the Neptune tunnel task definition (needs enabled, an image_revision and neptune_tunnel_task_role_arn)."
}
variable "neptune_tunnel_task_role_arn" {
  type        = string
  default     = null
  description = "Task role of the tunnel task (modules/identity: four ssmmessages channel actions only). Required when the tunnel is registered."
}
