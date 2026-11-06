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
# Decision 12-10 and the 13C decisions (TLS off, G2, G3, G5). Every bound is validated here (so a plan fails on an
# out-of-range tfvars value and the tests can expect it) and again in modules/emr/variables.tf, where the G6 cap rationale
# lives; keep the two copies identical. Task nodes and managed scaling are off unless this variable turns them on.
variable "emr_config" {
  type = object({
    enabled                      = optional(bool, false)
    release_label                = optional(string, "emr-7.8.0")
    runtime_reference            = optional(string)
    runtime_verified             = optional(bool, false)
    bootstrap_uri                = optional(string)
    bootstrap_sha256             = optional(string)
    runtime_archive_uri          = optional(string)
    runtime_archive_sha256       = optional(string, "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5")
    job_jar_uri                  = optional(string)
    job_jar_sha256               = optional(string)
    extra_artifacts              = optional(list(object({ uri = string, sha256 = string, dest = string })), [])
    instance_type                = optional(string, "m5.xlarge")
    max_task_nodes               = optional(number, 0)
    task_node_count              = optional(number, 0)
    managed_scaling_enabled      = optional(bool, false)
    managed_scaling_max_capacity = optional(number, 1)
    idle_timeout_seconds         = optional(number, 900)
    node_deadline_minutes        = optional(number, 240)
    startup_allowance_minutes    = optional(number, 5)
    ebs_size_gb                  = optional(number, 32)
    ebs_iops                     = optional(number, 3000)
    ebs_throughput               = optional(number, 125)
    stack_tag_value              = optional(string, "main-emr")
  })

  default = {}

  validation {
    condition     = var.emr_config.release_label == "emr-7.8.0"
    error_message = "Decision 12-10 is proven only on emr-7.8.0; the release label is pinned."
  }
  validation {
    condition     = var.emr_config.instance_type == "m5.xlarge"
    error_message = "Only m5.xlarge keeps the smallest cluster (primary + core) inside the USD 3 per-run cap at the maximum runtime plus idle tail (G6); m5.2xlarge would not."
  }
  validation {
    condition     = floor(var.emr_config.max_task_nodes) == var.emr_config.max_task_nodes && var.emr_config.max_task_nodes >= 0 && var.emr_config.max_task_nodes <= 1
    error_message = "G3/G6: at most one task node. Two would make four m5.xlarge instances, which cost USD 3.12 at 180 minutes plus the 900 s idle tail, above the USD 3 per-run cap."
  }
  validation {
    condition     = floor(var.emr_config.task_node_count) == var.emr_config.task_node_count && var.emr_config.task_node_count >= 0 && var.emr_config.task_node_count <= var.emr_config.max_task_nodes
    error_message = "task_node_count must be a whole number from 0 to max_task_nodes (default 0)."
  }
  validation {
    condition     = !var.emr_config.managed_scaling_enabled || var.emr_config.max_task_nodes > 0
    error_message = "Managed scaling needs max_task_nodes > 0; with no task nodes there is nothing to scale."
  }
  validation {
    condition     = floor(var.emr_config.managed_scaling_max_capacity) == var.emr_config.managed_scaling_max_capacity && var.emr_config.managed_scaling_max_capacity >= 1 && var.emr_config.managed_scaling_max_capacity <= 1 + var.emr_config.max_task_nodes
    error_message = "managed_scaling_max_capacity counts core plus task instances: 1 to 1 + max_task_nodes."
  }
  validation {
    condition     = floor(var.emr_config.idle_timeout_seconds) == var.emr_config.idle_timeout_seconds && var.emr_config.idle_timeout_seconds >= 60 && var.emr_config.idle_timeout_seconds <= 900
    error_message = "Auto-termination idle timeout must be 60 to 900 s (carried finding B3; the same cap as PIPELINE_MAX_IDLE_TIMEOUT_SECONDS)."
  }
  validation {
    condition     = floor(var.emr_config.node_deadline_minutes) == var.emr_config.node_deadline_minutes && var.emr_config.node_deadline_minutes >= 60 && var.emr_config.node_deadline_minutes <= 240
    error_message = "The node shutdown deadline is 60 to 240 minutes (best effort; four hours of three m5.xlarge nodes is USD 2.88)."
  }
  validation {
    condition     = floor(var.emr_config.startup_allowance_minutes) == var.emr_config.startup_allowance_minutes && var.emr_config.startup_allowance_minutes >= 1 && var.emr_config.startup_allowance_minutes <= 20
    error_message = "startup_allowance_minutes must be 1 to 20."
  }
  validation {
    condition     = var.emr_config.ebs_size_gb >= 32 && var.emr_config.ebs_size_gb <= 128 && var.emr_config.ebs_iops == 3000 && var.emr_config.ebs_throughput == 125
    error_message = "EBS is gp3 32-128 GiB at the baseline 3000 IOPS and 125 MiB/s (no provisioned performance surcharge)."
  }
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,39}$", var.emr_config.stack_tag_value))
    error_message = "stack_tag_value must be 3-40 lowercase letters, digits or hyphens."
  }
  validation {
    condition     = alltrue([for h in [var.emr_config.bootstrap_sha256, var.emr_config.runtime_archive_sha256, var.emr_config.job_jar_sha256] : h == null || can(regex("^[0-9a-f]{64}$", h))]) && alltrue([for a in var.emr_config.extra_artifacts : can(regex("^[0-9a-f]{64}$", a.sha256))])
    error_message = "Every sha256 must be 64 lowercase hex characters."
  }
  validation {
    condition     = var.emr_config.runtime_archive_sha256 == "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5"
    error_message = "Carried finding C2: the runtime archive sha256 must equal the decision 12-10 pin (RUNTIME_ARCHIVE_EXPECTED_SHA256 in scripts/config/release.conf). A different hash would install a different runtime; the class-origin check would only notice at run time, after spend."
  }
  validation {
    condition     = alltrue([for u in concat([for x in [var.emr_config.bootstrap_uri, var.emr_config.runtime_archive_uri, var.emr_config.job_jar_uri] : x if x != null], [for a in var.emr_config.extra_artifacts : a.uri]) : can(regex("^s3://[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]/[A-Za-z0-9._/=+@-]+$", u))])
    error_message = "Every artifact reference must be a plain s3://bucket/key URI."
  }
  validation {
    condition     = alltrue([for a in var.emr_config.extra_artifacts : can(regex("^/(opt/scholarchain-runtime|opt/scholarchain-spike/bin|mnt/scholarchain/config)/[A-Za-z0-9_.+/-]+$", a.dest)) && !strcontains(a.dest, "..") && !strcontains(a.dest, "//")])
    error_message = "extra_artifacts dest must be under /opt/scholarchain-runtime/, /opt/scholarchain-spike/bin/ or /mnt/scholarchain/config/ (no '..')."
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
