# Local authoring defaults. Deployment activation requires explicit reviewed inputs.
variable "neptune_enabled" {
  type        = bool
  default     = false
  description = "Select engine/family before provisioning; no inferred regional engine availability."
}
variable "neptune_engine_version" {
  type     = string
  default  = null
  nullable = true
}
variable "neptune_parameter_family" {
  type     = string
  default  = null
  nullable = true
}
variable "neptune_min_ncu" {
  type    = number
  default = 1
}
variable "neptune_max_ncu" {
  type    = number
  default = 2.5
}
variable "neptune_backup_days" {
  type    = number
  default = 7
}
variable "vector_dimension" {
  type    = number
  default = 256
}
variable "vector_metric" {
  type    = string
  default = "cosine"
}
variable "embedding_model_id" {
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
  description = "Phase8 planned TitanV2; regional availability/access remains unverified."
}
variable "synthesis_model_id" {
  type        = string
  default     = null
  nullable    = true
  description = "No synthesis model chosen and no invocation grant when unset."
}
variable "emr_output_prefixes" {
  type = map(set(string))

  default = { curated = ["pipeline/"], graph = ["pipeline/"], artifacts = ["pipeline/"], reports = ["pipeline/"]
  }

  description = "Only these nonempty per-bucket output prefixes permit EMR commit/temp cleanup deletes. Configure all job outputs accordingly."
  validation {
    condition = length(var.emr_output_prefixes) > 0 && alltrue([for b, prefixes in var.emr_output_prefixes : contains(["curated", "graph", "artifacts", "reports"], b) && length(prefixes) > 0 && alltrue([for p in prefixes : length(p) > 1 && endswith(p, "/") && !startswith(p, "/") && !strcontains(p, "*") && !strcontains(p, "?") && !strcontains(p, "..")])])

    error_message = "EMR delete prefixes must be nonempty literal output paths within curated/graph/artifacts/reports only, never raw or audit data."
  }
}
variable "emr_config" {
  type = object({
    enabled              = optional(bool, false)
    release_label        = optional(string)
    runtime_reference    = optional(string)
    runtime_verified     = optional(bool, false)
    bootstrap_uri        = optional(string)
    tls_certificate_uri  = optional(string)
    instance_type        = optional(string, "m5.xlarge")
    max_task_nodes       = optional(number, 2)
    idle_timeout_seconds = optional(number, 1800)
  })

  default = {}
  validation {
    condition = var.emr_config.max_task_nodes >= 0 && var.emr_config.max_task_nodes <= 2 && floor(var.emr_config.max_task_nodes) == var.emr_config.max_task_nodes && var.emr_config.idle_timeout_seconds >= 60 && var.emr_config.idle_timeout_seconds <= 3600 && contains(["m5.xlarge", "m5.2xlarge"], var.emr_config.instance_type)

    error_message = "EMR capacity is one primary/one core, zero-to-two task nodes, approved bounded instance shape and 60-3600s idle timeout."
  }
}
variable "runtime_enabled" {
  type    = bool
  default = false
}
variable "runtime_composition_verified" {
  type        = bool
  default     = false
  description = "Future deployment acknowledgment only after replacing/testing current unconfigured-only AWS composition."
}
variable "image_revision" {
  type     = string
  default  = null
  nullable = true
  validation {
    condition     = var.image_revision == null ? true : can(regex("^[0-9a-f]{40}$", var.image_revision))
    error_message = "Use an immutable full 40-character Git SHA image tag."
  }
}
variable "service_secret_bindings" {
  type = map(map(string))

  default = {}

  description = "Service -> exact environment name -> existing SecretsManager ARN. No secret values, no secret-version data reads."
  validation {
    condition = alltrue([for s, bindings in var.service_secret_bindings : contains(["query-api", "graph-service", "semantic-service", "embedding-worker"], s) && alltrue([for n, arn in bindings : contains(["SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN", "SCHOLARCHAIN_GRAPH_CURSOR_KEY"], n) && can(regex("^arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:.+$", arn))])])

    error_message = "Bindings must name supported secret environment variables and existing SecretsManager ARNs only."
  }
}
variable "service_capacity" {
  type = map(object({ cpu = number, memory = number, min = number, max = number }))

  default = {
    query-api = { cpu = 512, memory = 1024, min = 1, max = 2
    }
    graph-service = { cpu = 512, memory = 1024, min = 1, max = 2
    }
    semantic-service = { cpu = 512, memory = 1024, min = 1, max = 2
    }
    embedding-worker = { cpu = 512, memory = 1024, min = 1, max = 4
    }
  }
  validation {
    condition = toset(keys(var.service_capacity)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) && alltrue([for s, c in var.service_capacity : c.min >= 1 && floor(c.min) == c.min && c.max >= c.min && floor(c.max) == c.max && c.max <= (s == "embedding-worker" ? 4 : 2) && contains([512, 1024], c.cpu) && contains([1024, 2048], c.memory) && c.memory >= c.cpu * 2])

    error_message = "Exactly four bounded Fargate services: HTTP max2, worker max4, positive integer minimum and approved CPU/memory pairs."
  }
}
variable "cpu_target_percent" {
  type    = number
  default = 60
  validation {
    condition     = var.cpu_target_percent >= 10 && var.cpu_target_percent <= 80
    error_message = "CPU target must be 10-80 percent."
  }
}
variable "worker_backlog_target" {
  type    = number
  default = 10
  validation {
    condition     = var.worker_backlog_target > 0 && var.worker_backlog_target <= 100
    error_message = "Worker backlog target must be greater than zero and at most 100 messages/task."
  }
}
variable "https_certificate_arn" {
  type     = string
  default  = null
  nullable = true
  validation {
    condition     = var.https_certificate_arn == null ? true : can(regex("^arn:aws:acm:[a-z0-9-]+:[0-9]{12}:certificate/[a-z0-9-]+$", var.https_certificate_arn))
    error_message = "Certificate must be an existing ACM ARN; never private key material."
  }
}
variable "log_retention_days" {
  type    = number
  default = 7
  validation {
    condition     = contains([7, 14, 30], var.log_retention_days)
    error_message = "Course log retention is explicitly 7,14 or30 days."
  }
}
variable "alarm_notification_arns" {
  type    = set(string)
  default = []
  validation {
    condition     = alltrue([for a in var.alarm_notification_arns : can(regex("^arn:aws:sns:[a-z0-9-]+:[0-9]{12}:[A-Za-z0-9_-]+$", a))])
    error_message = "Notifications require existing SNS topic ARNs, never invented emails."
  }
}
variable "api_error_rate_percent" {
  type    = number
  default = 5
}
variable "latency_alarm_seconds" {
  type    = number
  default = 5
}
variable "queue_age_alarm_seconds" {
  type    = number
  default = 300
}
variable "application_metrics_namespace" {
  type        = string
  default     = "ScholarChain/Application"
  description = "Phase13/14 must wire a verified Prometheus-to-CloudWatch collector; custom panels stay empty until then."
}

variable "emr_service_policy_json" {
  type = string

  default = null

  nullable = true

  description = "Explicit scoped control-plane policy supplied only after selecting runtime/network. No default broad managed-policy attachment. Activation refuses a trust-only service role."
  validation {
    condition = var.emr_service_policy_json == null ? true : try(
      length(jsondecode(var.emr_service_policy_json).Statement) > 0 &&
      alltrue([for st in jsondecode(var.emr_service_policy_json).Statement :
        length(st.Action) > 0 && length(st.Resource) > 0 &&
        alltrue([for action in st.Action : !can(regex("[?*]", action))]) &&
        alltrue([for arn in st.Resource :
          arn == "*" ? alltrue([for action in st.Action : startswith(action, "ec2:Describe")]) :
          can(regex("^arn:aws:[a-z0-9-]+:[a-z0-9-]*:([0-9]{12})?:.+$", arn))
        ])
    ]), false)


    error_message = "Supply nonempty concrete action/resource lists. ARN partition, service, region and account segments cannot contain wildcards; only literal global resources for EC2 Describe APIs are allowed. Review scoped future-ID resource suffixes before activation."
  }
}


variable "vector_non_filterable_metadata_keys" {
  type        = set(string)
  default     = ["textS3Uri"]
  description = "Phase7/8 exact GetIndex preflight contract; changing it requires an index migration."
  validation {
    condition     = var.vector_non_filterable_metadata_keys == toset(["textS3Uri"])
    error_message = "All indexes must mark exactly textS3Uri as non-filterable, matching live ingest/query preflight."
  }
}
