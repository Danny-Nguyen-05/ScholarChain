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
  description = "Permission sets attached to the role. Default phase14-main (decision 14-6): the spike is destroyed and Phase 15 uses the main EMR module, so spike-emr is no longer enabled. The spike-emr definition stays in code and is selectable (the independent spike tests plan it) but must not be combined with phase14-main."
  type        = set(string)
  default     = ["phase14-main"]
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

variable "main_environment" {
  description = "Environment name of the MAIN root (its `environment` variable, tfvars default course). It names every resource (scholarchain-<environment>-...), so it scopes the phase14-main ARNs and tag conditions. Must equal the main root's value."
  type        = string
  default     = "course"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,9}$", var.main_environment))
    error_message = "main_environment must be 2-10 lowercase letters, digits or hyphens (the main root's own rule)."
  }
}

variable "main_emr_stack_tag_value" {
  description = "Value of the scholarchain:stack tag on the main EMR cluster (main root emr_config.stack_tag_value, default main-emr). RunJobFlow requires this request tag."
  type        = string
  default     = "main-emr"
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{2,39}$", var.main_emr_stack_tag_value))
    error_message = "main_emr_stack_tag_value must be 3-40 lowercase letters, digits or hyphens."
  }
}

variable "main_tag_keys" {
  description = "The only tag keys the one statement that cannot key off an existing tag may apply: kms:TagResource at key creation (AWS requires it to cover all keys of the account and region). They are the main root's provider default_tags (course, project, environment, owner, expiration_date) and the module tags it sets by hand (Name, tier, role, purpose, runtime_evidence, scholarchain:stack, for-use-with-amazon-emr-managed-policies). Add a key here when additional_tags uses one."
  type        = list(string)
  default     = ["course", "project", "environment", "owner", "expiration_date", "Name", "tier", "role", "purpose", "runtime_evidence", "scholarchain:stack", "for-use-with-amazon-emr-managed-policies"]
  validation {
    condition     = contains(var.main_tag_keys, "project") && contains(var.main_tag_keys, "environment") && length(var.main_tag_keys) == length(distinct(var.main_tag_keys)) && alltrue([for k in var.main_tag_keys : length(k) > 0 && !strcontains(k, "*") && !strcontains(k, "?") && !startswith(lower(k), "aws:")])
    error_message = "main_tag_keys must be distinct literal keys (no wildcard, no aws: prefix) and include project and environment."
  }
}

# Repair round 3 (Phase 14B): the provider choice of the main root (infra/terraform variables synthesis_provider and embedding_provider;
# keep the values equal). Amazon Bedrock grants exist only while a Bedrock provider is selected: with the primary providers (Anthropic API
# for synthesis, Voyage AI for embeddings) the runtime boundary carries no Bedrock statement and the operator-loader role no Titan grant.
variable "main_synthesis_provider" {
  description = "Synthesis provider of the main root: anthropic (default) or bedrock. bedrock adds the Bedrock invoke statement to the runtime boundary."
  type        = string
  default     = "anthropic"
  nullable    = false
  validation {
    condition     = contains(["anthropic", "bedrock"], var.main_synthesis_provider)
    error_message = "main_synthesis_provider must be anthropic or bedrock."
  }
}

variable "main_embedding_provider" {
  description = "Embedding provider of the main root: voyage (default) or bedrock. bedrock adds the Bedrock invoke statement to the runtime boundary and the Titan Text Embeddings V2 grant to the operator-loader role."
  type        = string
  default     = "voyage"
  nullable    = false
  validation {
    condition     = contains(["voyage", "bedrock"], var.main_embedding_provider)
    error_message = "main_embedding_provider must be voyage or bedrock."
  }
}

variable "main_bedrock_regions" {
  description = "Regions in which the runtime boundary lets the task roles invoke foundation models (the destinations of the cross-region inference profile the synthesis model uses). Default: the destinations of the us.* profiles when called from us-east-2 (us-east-1, us-east-2, us-west-2; model cards for Sonnet 4.6, Opus 4.1 and Haiku 5.5, 2026-11-06). The boundary also carries the region-less foundation-model ARN that global.* profiles need. It is only a ceiling: the main root's own inline policy names the exact regions."
  type        = list(string)
  default     = ["us-east-1", "us-east-2", "us-west-2"]
  validation {
    condition     = length(var.main_bedrock_regions) > 0 && contains(var.main_bedrock_regions, var.region) && length(var.main_bedrock_regions) == length(distinct(var.main_bedrock_regions)) && alltrue([for r in var.main_bedrock_regions : can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]+$", r))])
    error_message = "main_bedrock_regions must be distinct AWS region names and include the home region."
  }
}

# ---- Phase 14B/14C operator roles (replan W5a) ---------------------------------------------------------------------------
# Three short-lived, MFA-only roles for the human's 14C data loading, reading and data cleanup. They live in THIS root (IAM only, free)
# so that one deployer apply creates them and a later apply with operator_roles_enabled = false removes them.

variable "operator_roles_enabled" {
  description = "Create the three operator roles (scholarchain-<main_environment>-operator-loader, -reader, -cleanup) and their inline policies. Default false: nothing is created. Set it to false and apply again to remove them at cleanup."
  type        = bool
  default     = false
  nullable    = false
}

variable "operator_run_prefix" {
  description = "Run folder the operator roles may touch in the graph and curated buckets: the object keys <operator_run_prefix>/* only (the 14C tools are configured with graphPrefix = <operator_run_prefix>/graph and a curated upload folder under it). Chosen by the human before the session. The mandatory 'run-' start keeps it apart from every fixed prefix (pipeline/, embedding-text, evidence-index, runtime-audit, source-qualifications, vector-rejects). Required when operator_roles_enabled is true."
  type        = string
  default     = null
  validation {
    condition     = var.operator_run_prefix == null || can(regex("^run-[a-z0-9][a-z0-9-]{1,27}$", var.operator_run_prefix))
    error_message = "operator_run_prefix must match ^run-[a-z0-9][a-z0-9-]{1,27}$ (for example run-20261115)."
  }
  validation {
    condition     = !var.operator_roles_enabled || var.operator_run_prefix != null
    error_message = "operator_run_prefix is required when operator_roles_enabled is true."
  }
}

variable "operator_embedding_text_prefix" {
  description = "Rag-bucket prefix of the 14C embedding text. Must equal the main root's embedding_text_prefix (the runtime roles can read only that prefix, so the loader cannot use a run-specific one there). The operator roles get <prefix>/* in the rag bucket and nothing else."
  type        = string
  default     = "embedding-text"
  validation {
    condition     = can(regex("^[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*$", var.operator_embedding_text_prefix))
    error_message = "A literal key prefix without wildcard, leading or trailing slash (the main root's own rule)."
  }
}

variable "operator_neptune_cluster_resource_id" {
  description = "Neptune cluster resource id (cluster-XXXX..., `aws neptune describe-db-clusters --query DBClusters[].DbClusterResourceId`) for the neptune-db statements. It exists only after the main root's base-apply, so the deployer apply that precedes it cannot know it. null (the default) falls back to cluster-*/* in this account and region (every Neptune cluster here; the course account holds only the project's). After base-apply the human may set it and apply the deployer root again (an in-place IAM policy update) to tighten the scope to the one cluster."
  type        = string
  default     = null
  validation {
    condition     = var.operator_neptune_cluster_resource_id == null || can(regex("^cluster-[A-Z0-9]{10,40}$", var.operator_neptune_cluster_resource_id))
    error_message = "operator_neptune_cluster_resource_id must look like cluster-ABCDEFGHIJKLMNOPQRSTUVWXYZ."
  }
}
