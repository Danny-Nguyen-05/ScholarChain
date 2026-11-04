# ---- pinned shape: every validation rejects any change ----------------------

variable "region" {
  description = "Pinned region."
  type        = string
  default     = "us-east-2"
  validation {
    condition     = var.region == "us-east-2"
    error_message = "The spike is pinned to us-east-2."
  }
}

variable "availability_zone" {
  description = "Single AZ for both nodes, the EFS mount target and both subnets."
  type        = string
  default     = "us-east-2a"
  validation {
    condition     = contains(["us-east-2a", "us-east-2b", "us-east-2c"], var.availability_zone)
    error_message = "availability_zone must be us-east-2a, us-east-2b or us-east-2c."
  }
}

variable "release_label" {
  description = "Pinned EMR release."
  type        = string
  default     = "emr-7.8.0"
  validation {
    condition     = var.release_label == "emr-7.8.0"
    error_message = "The release is pinned to emr-7.8.0."
  }
}

variable "primary_instance_type" {
  type    = string
  default = "m5.xlarge"
  validation {
    condition     = var.primary_instance_type == "m5.xlarge"
    error_message = "The primary instance type is pinned to m5.xlarge."
  }
}

variable "core_instance_type" {
  type    = string
  default = "m5.xlarge"
  validation {
    condition     = var.core_instance_type == "m5.xlarge"
    error_message = "The core instance type is pinned to m5.xlarge."
  }
}

variable "primary_instance_count" {
  type    = number
  default = 1
  validation {
    condition     = var.primary_instance_count == 1
    error_message = "Exactly one primary node."
  }
}

variable "core_instance_count" {
  type    = number
  default = 1
  validation {
    condition     = var.core_instance_count == 1
    error_message = "Exactly one core node."
  }
}

variable "task_instance_count" {
  description = "No task nodes exist in this root; the value is pinned to document that."
  type        = number
  default     = 0
  validation {
    condition     = var.task_instance_count == 0
    error_message = "No task nodes."
  }
}

variable "use_spot" {
  type    = bool
  default = false
  validation {
    condition     = var.use_spot == false
    error_message = "Spot capacity is not allowed."
  }
}

variable "use_instance_fleets" {
  type    = bool
  default = false
  validation {
    condition     = var.use_instance_fleets == false
    error_message = "Instance fleets are not allowed; this root uses two instance groups."
  }
}

variable "use_autoscaling" {
  description = "Covers EMR automatic scaling and managed scaling."
  type        = bool
  default     = false
  validation {
    condition     = var.use_autoscaling == false
    error_message = "Autoscaling and managed scaling are not allowed."
  }
}

variable "cap_usd" {
  description = "Hard spend cap for the spike in USD, from the shared budget. Informational and pinned."
  type        = number
  default     = 10
  validation {
    condition     = var.cap_usd == 10
    error_message = "The spike cap is pinned to USD 10."
  }
}

variable "max_attempts" {
  type    = number
  default = 1
  validation {
    condition     = var.max_attempts == 1
    error_message = "A single attempt only."
  }
}

variable "max_cluster_minutes" {
  description = "Upper bound for the cluster lifetime; arms the node shutdown timer."
  type        = number
  default     = 120
  validation {
    condition     = var.max_cluster_minutes >= 30 && var.max_cluster_minutes <= 120 && floor(var.max_cluster_minutes) == var.max_cluster_minutes
    error_message = "max_cluster_minutes must be a whole number from 30 to 120."
  }
}

variable "idle_timeout_seconds" {
  description = "EMR auto-termination idle timeout (layer 4). Must exceed the collect step timeout so a non-YARN collect step is never judged idle."
  type        = number
  default     = 900
  validation {
    condition     = var.idle_timeout_seconds >= 60 && var.idle_timeout_seconds <= 1800
    error_message = "idle_timeout_seconds must be 60 to 1800."
  }
}

variable "startup_allowance_minutes" {
  description = "Minutes between RunJobFlow and bootstrap start that the node shutdown timer reserves."
  type        = number
  default     = 5
  validation {
    condition     = var.startup_allowance_minutes >= 1 && var.startup_allowance_minutes <= 20
    error_message = "startup_allowance_minutes must be 1 to 20."
  }
}

variable "probe_timeout_seconds" {
  type    = number
  default = 1200
  validation {
    condition     = var.probe_timeout_seconds >= 60 && var.probe_timeout_seconds <= 3600
    error_message = "probe_timeout_seconds must be 60 to 3600."
  }
}

variable "g1_timeout_seconds" {
  type    = number
  default = 3000
  validation {
    condition     = var.g1_timeout_seconds >= 60 && var.g1_timeout_seconds <= 5400
    error_message = "g1_timeout_seconds must be 60 to 5400."
  }
}

variable "collect_timeout_seconds" {
  type    = number
  default = 600
  validation {
    condition     = var.collect_timeout_seconds >= 60 && var.collect_timeout_seconds < 900
    error_message = "collect_timeout_seconds must be 60 to 899 (below the default idle timeout)."
  }
}

# ---- identity, tags, boundary -----------------------------------------------

variable "account_id" {
  description = "12-digit AWS account id (also provider allowed_account_ids)."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be exactly 12 digits."
  }
}

variable "owner" {
  description = "Owner tag."
  type        = string
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must be non-empty."
  }
}

variable "course" {
  type    = string
  default = "CS441"
}

variable "expiration_date" {
  description = "Resource expiration tag, YYYY-MM-DD."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", var.expiration_date)) && can(formatdate("YYYY-MM-DD", "${var.expiration_date}T00:00:00Z"))
    error_message = "expiration_date must be a valid calendar date, YYYY-MM-DD."
  }
}

variable "permissions_boundary_arn" {
  description = "Boundary policy created by the deployer root (output spike_permissions_boundary_arn). Attached to both spike IAM roles."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::${var.account_id}:policy/scholarchain-spike-emr-[A-Za-z0-9+=,.@_-]+$", var.permissions_boundary_arn))
    error_message = "permissions_boundary_arn must be a customer-managed policy named scholarchain-spike-emr-* in this account."
  }
}

variable "deployer_role_arn" {
  description = "ARN of the scoped deployer role (output role_arn of the deployer root). The KMS key policy grants key administration and use directly to this role, so no IAM tag condition is needed for the key."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::${var.account_id}:role/[A-Za-z0-9+=,.@_-]+$", var.deployer_role_arn))
    error_message = "deployer_role_arn must be arn:aws:iam::<account_id>:role/<name> (no path, no wildcard)."
  }
}

# ---- staged artifacts: the plan fails on any checksum mismatch ---------------

variable "runtime_tgz_path" {
  description = "Local path of the portable runtime tarball."
  type        = string
}

variable "runtime_tgz_sha256" {
  type    = string
  default = "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5"
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.runtime_tgz_sha256))
    error_message = "runtime_tgz_sha256 must be 64 lowercase hex characters."
  }
  validation {
    condition     = try(filesha256(var.runtime_tgz_path), "") == var.runtime_tgz_sha256
    error_message = "filesha256(runtime_tgz_path) does not equal runtime_tgz_sha256 (or the file is missing)."
  }
}

variable "job_jar_sha256" {
  description = "sha256 of scholarchain-runtime/application/scholarchain-job.jar inside the runtime tarball; the bootstrap verifies it after extraction."
  type        = string
  default     = "d52f11ebad5ec9e1ffdd1910d562023e934ce7ab62e7c74a5ffd650f8951b86b"
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.job_jar_sha256))
    error_message = "job_jar_sha256 must be 64 lowercase hex characters."
  }
}

variable "inputs_tgz_path" {
  description = "Local path of the G1 upstream inputs tarball."
  type        = string
}

variable "inputs_tgz_sha256" {
  type    = string
  default = "e05931ab0eec2fc66b1a0d0ab33e5b4c070faf81afcb66fc00208287b85ab558"
  validation {
    condition     = can(regex("^[0-9a-f]{64}$", var.inputs_tgz_sha256))
    error_message = "inputs_tgz_sha256 must be 64 lowercase hex characters."
  }
  validation {
    condition     = try(filesha256(var.inputs_tgz_path), "") == var.inputs_tgz_sha256
    error_message = "filesha256(inputs_tgz_path) does not equal inputs_tgz_sha256 (or the file is missing)."
  }
}

variable "g1_config_template_path" {
  description = "Local relocated G1 config whose path prefix is rewritten to the EFS mount."
  type        = string
}

variable "g1_config_source_prefix" {
  description = "Path prefix in the template that is replaced by /mnt/scholarchain."
  type        = string
  default     = "/private/tmp/sc-runtime-test-20261103"
  validation {
    condition     = startswith(var.g1_config_source_prefix, "/") && length(var.g1_config_source_prefix) > 3
    error_message = "g1_config_source_prefix must be an absolute path prefix."
  }
}
