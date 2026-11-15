variable "aws_account_id" {
  description = "Actual approved account ID, supplied only after account creation. No invented default."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the approved 12-digit AWS account ID."
  }
}
variable "aws_region" {
  description = "User-selected commercial AWS region; verify all required services before planning."
  type        = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "Supply an approved commercial AWS region name."
  }
}
variable "aws_profile" {
  description = "Approved local profile NAME only; never credentials. Required for a real plan."
  type        = string
  validation {
    condition     = length(trimspace(var.aws_profile)) > 0
    error_message = "Supply an approved profile name."
  }
}
variable "availability_zones" {
  description = "Two distinct approved AZ names in aws_region; no AWS lookup during local validation."
  type        = list(string)
  validation {
    condition     = length(var.availability_zones) == 2 && length(toset(var.availability_zones)) == 2
    error_message = "Select exactly two distinct Availability Zones."
  }
}
variable "deployment_trusted_principal_arn" {
  description = "Existing approved IAM role/user ARN allowed to assume the separate deployment role."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:(role|user)/.+$", var.deployment_trusted_principal_arn))
    error_message = "Provide an explicit approved IAM role or user ARN; no wildcard/root trust."
  }
}
variable "budget_limit_usd" {
  description = "Human budget ceiling in USD, required before any real plan; not a billing stop."
  type        = number
  validation {
    condition     = var.budget_limit_usd > 0
    error_message = "A positive human-selected budget is required before planning."
  }
}
variable "project" {
  type        = string
  description = "Resource-name prefix and project tag."
  default     = "scholarchain"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,15}$", var.project))
    error_message = "Project must be 3-16 lowercase letters/digits/hyphens."
  }
}
variable "environment" {
  type        = string
  description = "Environment name, confirmed course in Step 0."
  default     = "course"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,9}$", var.environment))
    error_message = "Environment must be 2-10 lowercase letters/digits/hyphens."
  }
}
variable "course" {
  type        = string
  description = "Required cost-allocation course tag."
  default     = "CS441"
  validation {
    condition     = length(trimspace(var.course)) > 0
    error_message = "Course tag must not be empty."
  }
}
variable "owner" {
  type        = string
  description = "Required owner tag; no email address or credentials."
  default     = "danny"
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "Owner tag must not be empty."
  }
}
variable "expiration_date" {
  type        = string
  description = "Provisional expiration tag; reconfirm before deployment. Not an automatic cleanup."
  default     = "2026-11-25"
  validation {
    condition     = can(formatdate("YYYY-MM-DD", "${var.expiration_date}T00:00:00Z"))
    error_message = "Expiration must be a valid YYYY-MM-DD date."
  }
}
variable "additional_tags" {
  type        = map(string)
  description = "Optional account-supported cost tags; required tags take precedence."
  default     = {}
}
variable "cleanup_mode" {
  type        = bool
  description = "Explicit reviewed cleanup configuration; no authorization to destroy. It switches force_destroy on the S3 buckets and the S3 Vectors bucket (no prevent_destroy since the USD 25 replan, W4), force_delete on ECR and the deletion protections of Neptune, the ALB and DynamoDB."
  default     = false
}
variable "persistent_environment" {
  type        = bool
  description = "Persistent environments forbid intermediate expiration; deletion protections remain on unless explicit cleanup_mode."
  default     = false
}
variable "enable_budget_resource" {
  type        = bool
  description = "Enable only after account supports Budgets and human supplies notification subscribers."
  default     = false
}
variable "budget_notification_emails" {
  type        = set(string)
  description = "User-supplied subscribers for an optional monthly budget; no fabricated recipient."
  default     = []
  validation {
    condition     = !var.enable_budget_resource || length(var.budget_notification_emails) > 0
    error_message = "Enabled budgets require actual human-supplied subscribers."
  }
}
variable "vpc_cidr" {
  type        = string
  description = "Private course VPC address space; a local default, not an existing network claim."
  default     = "10.44.0.0/16"
}
variable "public_ingress_cidrs" {
  type        = set(string)
  description = "Approved ALB HTTPS/HTTP client CIDRs; default none until human ingress decision. Never data-store ingress."
  default     = []
}
variable "service_port" {
  type        = number
  description = "Phase 10 containers share configurable HTTP port 8080."
  default     = 8080
  validation {
    condition     = var.service_port >= 1 && var.service_port <= 65535 && floor(var.service_port) == var.service_port
    error_message = "Service port must be an integer between 1 and 65535."
  }
}
variable "neptune_port" {
  type        = number
  description = "Neptune standard TLS port; externalized for later module wiring."
  default     = 8182
}
variable "interface_endpoint_services" {
  type        = set(string)
  description = "Justified private interfaces only; NAT currently covers AWS HTTPS, so none by default."
  default     = []
  validation {
    condition     = alltrue([for s in var.interface_endpoint_services : contains(["ecr.api", "ecr.dkr", "logs", "secretsmanager", "sqs", "kms", "bedrock-runtime"], s)])
    error_message = "Only explicitly supported application AWS service endpoints are allowed."
  }
}
variable "query_session_gsi_name" {
  type        = string
  description = "Phase 7 QuerySession idempotency-key GSI name; pass matching name to StorageConfig."
  default     = "by-idempotency-key"
}
variable "enable_query_session_ttl" {
  type        = bool
  description = "Enable expiresAt cleanup only when runtime disposableSessionTtlSeconds is configured."
  default     = false
}
variable "intermediate_retention_days" {
  type        = number
  description = "Course intermediates/ prefix expiration; preserved in persistent environments."
  default     = 14
  validation {
    condition     = var.intermediate_retention_days >= 1 && floor(var.intermediate_retention_days) == var.intermediate_retention_days
    error_message = "Intermediate retention must be positive whole days."
  }
}
variable "sqs_visibility_timeout_seconds" {
  type        = number
  description = "Worker processing budget must stay below this configurable visibility timeout."
  default     = 300
}
variable "sqs_max_receive_count" {
  type        = number
  description = "Bound poison-message deliveries before DLQ. Coordinate runtime attempts in Phase 13."
  default     = 3
}
variable "sqs_retention_seconds" {
  type        = number
  description = "Source queue retention, four days; DLQ keeps fourteen days."
  default     = 345600
}
variable "kms_deletion_window_days" {
  type        = number
  description = "CMK recovery window; minimum AWS-supported 7 days for course cost awareness."
  default     = 7
  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30 && floor(var.kms_deletion_window_days) == var.kms_deletion_window_days
    error_message = "KMS deletion window must be 7-30 whole days."
  }
}
variable "service_secret_arns" {
  type        = map(set(string))
  description = "Existing Secrets Manager ARNs per service; ARN references only, never secret values or version data sources."
  default     = {}
  validation {
    condition = alltrue([for service in keys(var.service_secret_arns) : contains(["query-api", "graph-service", "semantic-service", "embedding-worker"], service)]) && alltrue(flatten([for service, arns in var.service_secret_arns : [
      for arn in arns : contains(["query-api", "graph-service", "semantic-service", "embedding-worker"], service) && can(regex("^arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:.+$", arn))
    ]]))
    error_message = "Supply only existing Secrets Manager ARNs keyed by one of the four service names."
  }
}

variable "budget_notification_threshold_percent" {
  type        = number
  description = "Warn at 80% by default so there is time to act; a notification is not a spending stop."
  default     = 80
  validation {
    condition     = var.budget_notification_threshold_percent > 0 && var.budget_notification_threshold_percent <= 100
    error_message = "Budget warning percentage must be greater than zero and at most 100."
  }
}
variable "multipart_abort_days" {
  type        = number
  description = "Abort unfinished S3 uploads after seven days to avoid orphan-part storage cost."
  default     = 7
  validation {
    condition     = var.multipart_abort_days >= 1 && floor(var.multipart_abort_days) == var.multipart_abort_days
    error_message = "Multipart abort retention must be positive whole days."
  }
}
variable "sqs_dlq_retention_seconds" {
  type        = number
  description = "Keep poison-message evidence for the AWS maximum fourteen days by default."
  default     = 1209600
  validation {
    condition     = var.sqs_dlq_retention_seconds >= 60 && var.sqs_dlq_retention_seconds <= 1209600 && floor(var.sqs_dlq_retention_seconds) == var.sqs_dlq_retention_seconds
    error_message = "DLQ retention must be 60-1209600 whole seconds."
  }
}
variable "sqs_long_poll_seconds" {
  type        = number
  description = "SQS long polling uses the maximum twenty seconds to reduce idle requests."
  default     = 20
  validation {
    condition     = var.sqs_long_poll_seconds >= 0 && var.sqs_long_poll_seconds <= 20 && floor(var.sqs_long_poll_seconds) == var.sqs_long_poll_seconds
    error_message = "SQS long poll must be 0-20 whole seconds."
  }
}
