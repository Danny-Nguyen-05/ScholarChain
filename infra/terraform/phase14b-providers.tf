# Repair round 3 (Phase 14B): the Anthropic API (synthesis) and Voyage AI (embeddings) providers, with Amazon Bedrock kept as the
# selectable alternative (instructor ruling 2026-11-09). Everything that follows from the two provider choices is derived here once:
# the effective model identifiers, the Bedrock identifiers that reach the IAM grants (null when the provider is not Bedrock, so no
# Bedrock invoke grant exists), and the two empty Secrets Manager containers for the provider API keys.
#
# KEY HANDLING. Terraform creates only the containers. There is deliberately NO aws_secretsmanager_secret_version, no secret_string,
# no data source that reads a secret and no output carrying a value: the human enters each key value during the live session
# (README, "Provider API keys"), so a key never enters the repository, a variable file, the plan or the state. A secret is created
# only when its provider is selected. Each is encrypted with the AWS-managed key aws/secretsmanager (no kms_key_id): the task
# execution role then needs no kms:Decrypt grant (a CMK would need one), and no key policy of this stack changes.
#
# NAMES. The name prefix is the main stack's (scholarchain-<environment>), the same prefix the deployer's phase14-main set scopes
# Secrets Manager create, update and delete to (infra/terraform/deployer/phase14_main.tf, "SecretsManagerProviderKeyContainers").
#   <name_prefix>/anthropic-api-key   ARN pattern arn:aws:secretsmanager:<region>:<account>:secret:<name_prefix>/anthropic-api-key-??????
#   <name_prefix>/voyage-api-key      ARN pattern arn:aws:secretsmanager:<region>:<account>:secret:<name_prefix>/voyage-api-key-??????
# (Secrets Manager appends six random characters to every secret ARN.)
#
# DELETION. recovery_window_in_days = 0 makes the delete (cleanup's destroy) a force delete without a recovery window, so the secret and
# its value are gone at once and the name can be reused. A secret scheduled for deletion would otherwise keep a revocable key readable
# for up to 30 days.
locals {
  synthesis_anthropic = var.synthesis_provider == "anthropic"
  embedding_voyage    = var.embedding_provider == "voyage"

  # Primary-provider identifiers (the contract of the round 3 work order).
  anthropic_synthesis_model = "claude-haiku-5-5"
  voyage_embedding_model    = "voyage-4-lite"
  bedrock_titan_embedding   = "amazon.titan-embed-text-v2:0"

  # Effective identifiers: what the runtime environment, the version tags and the guards see.
  synthesis_model_effective         = local.synthesis_anthropic ? local.anthropic_synthesis_model : var.synthesis_model_id
  embedding_model_effective         = local.embedding_voyage ? local.voyage_embedding_model : coalesce(var.embedding_model_id, local.bedrock_titan_embedding)
  embedding_model_version_effective = local.embedding_voyage ? coalesce(var.embedding_model_version, local.voyage_embedding_model) : var.embedding_model_version

  # Bedrock identifiers for the IAM grants: null (no grant of any kind) unless that purpose uses Bedrock.
  bedrock_synthesis_model = local.synthesis_anthropic ? null : var.synthesis_model_id
  bedrock_embedding_model = local.embedding_voyage ? null : local.embedding_model_effective

  anthropic_secret_name = "${local.name_prefix}/anthropic-api-key"
  voyage_secret_name    = "${local.name_prefix}/voyage-api-key"

  # IAM Resource patterns for the two containers: the exact name plus the six random characters Secrets Manager appends ("?" is one
  # character). They are built from the name, not from the resource ARN attribute, so they are known at plan time: the execution
  # role policy stays fully readable in a reviewed plan instead of "known after apply" for the ARN created in the same apply.
  # https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_iam-permissions.html (ARN format with the random suffix)
  anthropic_secret_iam_arn = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${local.anthropic_secret_name}-??????"
  voyage_secret_iam_arn    = "arn:aws:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${local.voyage_secret_name}-??????"

  # Secret ARNs per service. query-api calls the synthesis model; semantic-service (query embeddings) and embedding-worker (document
  # embeddings) call the embedding model. graph-service and the Neptune tunnel use neither provider. Keys of the binding maps are the
  # environment variable names the services read.
  provider_secret_iam_arns = {
    "query-api"        = local.synthesis_anthropic ? [local.anthropic_secret_iam_arn] : []
    "graph-service"    = []
    "semantic-service" = local.embedding_voyage ? [local.voyage_secret_iam_arn] : []
    "embedding-worker" = local.embedding_voyage ? [local.voyage_secret_iam_arn] : []
  }
  # ECS `secrets` take the real ARN (valueFrom). It is known once the secret exists (base-apply creates it; the runtime stage follows).
  provider_secret_bindings = {
    "query-api"        = { for n in(local.synthesis_anthropic ? ["SCHOLARCHAIN_ANTHROPIC_API_KEY"] : []) : n => aws_secretsmanager_secret.anthropic[0].arn }
    "graph-service"    = {}
    "semantic-service" = { for n in(local.embedding_voyage ? ["SCHOLARCHAIN_VOYAGE_API_KEY"] : []) : n => aws_secretsmanager_secret.voyage[0].arn }
    "embedding-worker" = { for n in(local.embedding_voyage ? ["SCHOLARCHAIN_VOYAGE_API_KEY"] : []) : n => aws_secretsmanager_secret.voyage[0].arn }
  }
}

resource "aws_secretsmanager_secret" "anthropic" {
  count                   = local.synthesis_anthropic ? 1 : 0
  name                    = local.anthropic_secret_name
  description             = "Anthropic API key for ${local.name_prefix} synthesis (claude-haiku-5-5). Container only: the value is entered by hand, never by Terraform."
  recovery_window_in_days = 0
  tags                    = module.foundation.tags
}

resource "aws_secretsmanager_secret" "voyage" {
  count                   = local.embedding_voyage ? 1 : 0
  name                    = local.voyage_secret_name
  description             = "Voyage AI API key for ${local.name_prefix} embeddings (voyage-4-lite). Container only: the value is entered by hand, never by Terraform."
  recovery_window_in_days = 0
  tags                    = module.foundation.tags
}

resource "terraform_data" "provider_guard" {
  lifecycle {
    # Anthropic: the model is fixed. A Bedrock model id or inference profile left in a private tfvars file from the earlier plan would
    # otherwise reach the runtime as the Anthropic model name (and the Bedrock grants would silently disappear).
    precondition {
      condition     = !local.synthesis_anthropic || (var.synthesis_model_id == null && var.synthesis_inference_profile_id == null && length(var.synthesis_inference_profile_regions) == 0)
      error_message = "synthesis_provider anthropic fixes the model (claude-haiku-5-5): leave synthesis_model_id, synthesis_inference_profile_id and synthesis_inference_profile_regions unset, or select synthesis_provider bedrock."
    }
    precondition {
      condition     = !local.embedding_voyage || (var.embedding_model_id == null && var.embedding_inference_profile_id == null && length(var.embedding_inference_profile_regions) == 0)
      error_message = "embedding_provider voyage fixes the model (voyage-4-lite): leave embedding_model_id, embedding_inference_profile_id and embedding_inference_profile_regions unset, or select embedding_provider bedrock."
    }
    precondition {
      condition     = !local.embedding_voyage || var.embedding_model_version == null || var.embedding_model_version == local.voyage_embedding_model
      error_message = "embedding_provider voyage stamps the model version tag voyage-4-lite on every vector: leave embedding_model_version unset (or exactly voyage-4-lite). The services refuse a vector whose tag differs."
    }
    # Voyage's output_dimension 256 is the index dimension (the root also pins 256 and cosine in phase12b_guard).
    precondition {
      condition     = !local.embedding_voyage || var.vector_dimension == 256
      error_message = "embedding_provider voyage uses output_dimension 256: vector_dimension must be 256."
    }
  }
}

# Offline assertions (no secret value exists anywhere in this configuration: only names, the IAM patterns and container settings).
output "provider_controls" {
  value = {
    synthesis_provider      = var.synthesis_provider
    embedding_provider      = var.embedding_provider
    synthesis_model         = local.synthesis_model_effective
    embedding_model         = local.embedding_model_effective
    embedding_model_version = local.embedding_model_version_effective
    vector_dimension        = var.vector_dimension
    bedrock_synthesis_model = local.bedrock_synthesis_model
    bedrock_embedding_model = local.bedrock_embedding_model
    secrets = merge(
      { for s in aws_secretsmanager_secret.anthropic : "anthropic" => { name = s.name, recovery_window_in_days = s.recovery_window_in_days, kms_key_id = s.kms_key_id, tags = s.tags } },
      { for s in aws_secretsmanager_secret.voyage : "voyage" => { name = s.name, recovery_window_in_days = s.recovery_window_in_days, kms_key_id = s.kms_key_id, tags = s.tags } },
    )
    iam_arn_patterns = local.provider_secret_iam_arns
  }
}
