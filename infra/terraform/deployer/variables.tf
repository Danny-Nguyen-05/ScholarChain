variable "region" {
  description = "Only supported region."
  type        = string
  default     = "us-east-2"
  validation {
    condition     = var.region == "us-east-2"
    error_message = "The deployer role is region-pinned to us-east-2."
  }
}

variable "account_id" {
  description = "12-digit AWS account id the role is created in (also used for provider allowed_account_ids)."
  type        = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be exactly 12 digits."
  }
}

variable "operator_principal_arn" {
  description = "ARN of the single human operator IAM user or role allowed to assume the deployer role (MFA required). No wildcard, no account root."
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:(user|role)/[A-Za-z0-9+=,.@_/-]+$", var.operator_principal_arn))
    error_message = "operator_principal_arn must be a concrete IAM user or role ARN (no wildcard, no root)."
  }
  validation {
    condition     = can(regex("^arn:aws:iam::${var.account_id}:", var.operator_principal_arn))
    error_message = "operator_principal_arn must be in the same account as account_id."
  }
}

variable "role_name" {
  description = "Deployer role name. Must not collide with the billing deployer."
  type        = string
  default     = "scholarchain-deployer"
  validation {
    condition     = can(regex("^scholarchain-[a-z0-9-]{1,40}$", var.role_name)) && var.role_name != "scholarchain-billing-deployer"
    error_message = "role_name must match ^scholarchain-[a-z0-9-]+$ and must not be scholarchain-billing-deployer."
  }
}

variable "enabled_permission_sets" {
  description = "Permission sets attached to the role. Only spike-emr is implemented; a later phase adds a registry entry in permission_sets.tf and lists it here."
  type        = set(string)
  default     = ["spike-emr"]
  validation {
    condition     = length(var.enabled_permission_sets) > 0 && alltrue([for s in var.enabled_permission_sets : can(regex("^[a-z0-9]+(-[a-z0-9]+)*$", s))])
    error_message = "enabled_permission_sets must be non-empty and contain kebab-case names."
  }
}

variable "owner" {
  description = "Owner tag value."
  type        = string
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "owner must be non-empty."
  }
}

variable "spike_kms_tag_keys" {
  description = "The only tag keys kms:TagResource may apply (carried item 14). They are the keys of the spike root's provider default_tags plus Name; kms:TagResource is needed in IAM only so kms:CreateKey can carry its tags, so it is limited to these keys."
  type        = list(string)
  default     = ["course", "project", "environment", "owner", "expiration", "scholarchain:stack", "for-use-with-amazon-emr-managed-policies", "Name"]
  validation {
    condition     = contains(var.spike_kms_tag_keys, "scholarchain:stack") && length(var.spike_kms_tag_keys) == length(distinct(var.spike_kms_tag_keys)) && alltrue([for k in var.spike_kms_tag_keys : length(k) > 0 && !strcontains(k, "*") && !strcontains(k, "?") && !startswith(lower(k), "aws:")])
    error_message = "spike_kms_tag_keys must be distinct literal keys (no wildcard, no aws: prefix) and include scholarchain:stack."
  }
}

variable "spike_role_names" {
  description = "The exact names of the two IAM roles the spike root may create (carried item 16). iam:CreateRole is limited to these ARNs instead of the whole scholarchain-spike-emr-* prefix, so the deployer can create only the roles the spike needs."
  type        = list(string)
  default     = ["scholarchain-spike-emr-service", "scholarchain-spike-emr-instance"]
  validation {
    condition     = length(var.spike_role_names) == 2 && length(var.spike_role_names) == length(distinct(var.spike_role_names)) && alltrue([for n in var.spike_role_names : can(regex("^scholarchain-spike-emr-[a-z0-9-]+$", n))])
    error_message = "spike_role_names must be exactly two distinct names matching scholarchain-spike-emr-[a-z0-9-]+."
  }
}
