locals {
  name_prefix = "${var.project}-${var.environment}"
}
resource "terraform_data" "configuration_guard" {
  lifecycle {
    precondition {
      condition     = alltrue([for az in var.availability_zones : startswith(az, var.aws_region) && length(az) == length(var.aws_region) + 1])
      error_message = "Both AZs must belong to the explicitly selected region."
    }
    precondition {
      condition     = length("${local.name_prefix}-${var.aws_account_id}-artifacts") <= 63
      error_message = "Configured bucket naming exceeds S3's 63-character limit."
    }
  }
}
module "foundation" {
  source                         = "./modules/foundation"
  name_prefix                    = local.name_prefix
  course                         = var.course
  project                        = var.project
  environment                    = var.environment
  owner                          = var.owner
  expiration_date                = var.expiration_date
  additional_tags                = var.additional_tags
  budget_limit_usd               = var.budget_limit_usd
  enable_budget                  = var.enable_budget_resource
  notification_emails            = var.budget_notification_emails
  notification_threshold_percent = var.budget_notification_threshold_percent
}
module "network" {
  source                      = "./modules/network"
  name_prefix                 = local.name_prefix
  aws_region                  = var.aws_region
  availability_zones          = var.availability_zones
  vpc_cidr                    = var.vpc_cidr
  public_ingress_cidrs        = var.public_ingress_cidrs
  service_port                = var.service_port
  neptune_port                = var.neptune_port
  interface_endpoint_services = var.interface_endpoint_services
  tags                        = module.foundation.tags
}
module "identity" {
  source                              = "./modules/identity"
  name_prefix                         = local.name_prefix
  aws_region                          = var.aws_region
  aws_account_id                      = var.aws_account_id
  deployment_trusted_principal_arn    = var.deployment_trusted_principal_arn
  kms_deletion_window_days            = var.kms_deletion_window_days
  bucket_arns                         = module.datalake.bucket_arns
  table_arns                          = module.dynamodb.table_arns
  query_session_index_arn             = module.dynamodb.query_session_index_arn
  queue_arn                           = module.messaging.queue_arn
  dead_letter_queue_arn               = module.messaging.dead_letter_queue_arn
  repository_arns                     = module.runtime.repository_arns
  service_secret_arns                 = { for service in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : service => setunion(lookup(var.service_secret_arns, service, toset([])), toset(values(lookup(var.service_secret_bindings, service, {})))) }
  emr_output_prefixes                 = var.emr_output_prefixes
  emr_service_policy_json             = var.emr_service_policy_json
  enable_emr                          = var.emr_config.enabled
  neptune_data_arn                    = module.neptune.data_arn
  vector_index_arns                   = module.s3vectors.index_arns
  embedding_model_id                  = local.bedrock_embedding_model
  synthesis_model_id                  = local.bedrock_synthesis_model
  provider_secret_arns                = local.provider_secret_iam_arns
  rag_prefixes                        = [var.evidence_index_prefix, var.runtime_audit_prefix, var.embedding_text_prefix, "runtime-artifacts"]
  embedding_inference_profile_id      = var.embedding_inference_profile_id
  embedding_inference_profile_regions = var.embedding_inference_profile_regions
  synthesis_inference_profile_id      = var.synthesis_inference_profile_id
  synthesis_inference_profile_regions = var.synthesis_inference_profile_regions
  neptune_tunnel_role_enabled         = local.neptune_tunnel
  tags                                = module.foundation.tags
}
module "datalake" {
  source                      = "./modules/datalake"
  name_prefix                 = local.name_prefix
  aws_account_id              = var.aws_account_id
  kms_key_arn                 = module.identity.kms_key_arn
  cleanup_mode                = var.cleanup_mode
  persistent_environment      = var.persistent_environment
  intermediate_retention_days = var.intermediate_retention_days
  multipart_abort_days        = var.multipart_abort_days
  tags                        = module.foundation.tags
}
module "dynamodb" {
  source                   = "./modules/dynamodb"
  name_prefix              = local.name_prefix
  kms_key_arn              = module.identity.kms_key_arn
  cleanup_mode             = var.cleanup_mode
  query_session_gsi_name   = var.query_session_gsi_name
  enable_query_session_ttl = var.enable_query_session_ttl
  tags                     = module.foundation.tags
}
module "messaging" {
  source                     = "./modules/messaging"
  name_prefix                = local.name_prefix
  aws_account_id             = var.aws_account_id
  kms_key_arn                = module.identity.kms_key_arn
  visibility_timeout_seconds = var.sqs_visibility_timeout_seconds
  max_receive_count          = var.sqs_max_receive_count
  message_retention_seconds  = var.sqs_retention_seconds
  dlq_retention_seconds      = var.sqs_dlq_retention_seconds
  long_poll_seconds          = var.sqs_long_poll_seconds
  tags                       = module.foundation.tags
}
module "runtime" {
  enabled                           = var.runtime_enabled
  composition_verified              = var.runtime_composition_verified
  image_revision                    = var.image_revision
  aws_region                        = var.aws_region
  vpc_id                            = module.network.ids.vpc_id
  application_subnets               = module.network.ids.application_subnet_ids
  public_subnets                    = module.network.ids.public_subnet_ids
  security_groups                   = module.network.ids.security_group_ids
  task_roles                        = module.identity.runtime_ready_roles.tasks
  execution_roles                   = module.identity.runtime_ready_roles.execution
  rag_bucket                        = module.datalake.bucket_names["rag"]
  graph_bucket                      = module.datalake.bucket_names["graph"]
  service_secret_bindings           = var.service_secret_bindings
  provider_secret_bindings          = local.provider_secret_bindings
  synthesis_provider                = var.synthesis_provider
  embedding_provider                = var.embedding_provider
  embedding_model_id                = local.embedding_model_effective
  embedding_model_version           = local.embedding_model_version_effective
  vector_dimension                  = var.vector_dimension
  vector_metric                     = var.vector_metric
  query_session_index               = var.query_session_gsi_name
  queue_visibility_seconds          = var.sqs_visibility_timeout_seconds
  queue_wait_seconds                = var.sqs_long_poll_seconds
  semantic_index                    = var.semantic_index_name
  embedding_text_prefix             = var.embedding_text_prefix
  evidence_index_prefix             = var.evidence_index_prefix
  audit_prefix                      = var.runtime_audit_prefix
  synthesis_model_id                = local.synthesis_model_effective
  synthesis_inference_profile_id    = var.synthesis_inference_profile_id
  runtime_artifact_bucket           = var.runtime_artifact_bucket
  runtime_artifact_key              = var.runtime_artifact_key
  runtime_artifact_sha256           = var.runtime_artifact_sha256
  runtime_artifact_source_run_id    = var.runtime_artifact_source_run_id
  capacity                          = var.service_capacity
  cpu_target                        = var.cpu_target_percent
  container_insights_enabled        = var.container_insights_enabled
  backlog_target                    = var.worker_backlog_target
  service_port                      = var.service_port
  certificate_arn                   = local.listener_cert_arn
  https_enabled                     = local.https_enabled
  neptune_tunnel_enabled            = local.neptune_tunnel
  neptune_tunnel_task_role_arn      = module.identity.neptune_tunnel_task_role_arn
  health_check_grace_period_seconds = var.query_health_check_grace_period_seconds
  queue_name                        = "${local.name_prefix}-embedding"
  queue_url                         = module.messaging.queue_urls.embedding
  dlq_url                           = module.messaging.queue_urls.dead_letter
  table_names                       = module.dynamodb.table_names
  neptune_endpoint                  = module.neptune.endpoint
  vector_bucket                     = module.s3vectors.bucket_name
  log_groups                        = module.observability.log_group_names
  source                            = "./modules/runtime"
  name_prefix                       = local.name_prefix
  kms_key_arn                       = module.identity.kms_key_arn
  cleanup_mode                      = var.cleanup_mode
  tags                              = module.foundation.tags
}
