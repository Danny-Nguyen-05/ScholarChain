# Finding C1 (13C repair round 1): the EMR step runner and its three Python programs are installed on the primary node by the
# bootstrap action, sha256-pinned, and every EMR step verifies them on the node before running. This manifest is the reviewed
# Terraform-side pin of those hashes (it is inside infra/terraform so the plan materialization at a commit contains it). The
# step scripts are produced by `python3 -I scripts/lib/pipeline.py step-manifest --write`; the run configuration the human
# approves carries the same hashes, and scripts/lib/pipeline.py refuses a manifest that differs from scripts/emr/.
locals {
  emr_step_manifest = jsondecode(file("${path.module}/emr-step-programs.json"))
}

resource "terraform_data" "phase12b_guard" {
  lifecycle {
    precondition {
      condition     = alltrue([for id in [var.embedding_model_id, var.synthesis_model_id] : id == null ? true : can(regex("^[a-zA-Z0-9._:-]+$", id))])
      error_message = "Model IDs must be explicit foundation-model identifiers without wildcard actions/resources."
    }

    precondition {
      condition     = !var.neptune_enabled || (var.neptune_engine_version != null && var.neptune_parameter_family != null && try(var.neptune_parameter_family == "neptune${join(".", slice(split(".", var.neptune_engine_version), 0, 2))}", false))
      error_message = "Neptune activation requires an explicit engine version and matching neptuneX.Y parameter family, checked for regional availability before12C."
    }
    precondition {
      condition     = var.neptune_min_ncu >= 1 && var.neptune_max_ncu >= 2.5 && var.neptune_max_ncu <= 2.5 && var.neptune_min_ncu <= var.neptune_max_ncu && var.neptune_backup_days >= 1 && var.neptune_backup_days <= 35
      error_message = "Neptune capacity must stay within the accepted1-2.5NCU ceiling and backups within1-35days."
    }
    precondition {
      condition     = var.vector_dimension == 256 && var.vector_metric == "cosine"
      error_message = "The Phase8 contract requires256 dimensions and cosine; changing it needs an explicit index/model migration."
    }
    precondition {
      condition     = !var.emr_config.enabled || (var.emr_config.runtime_verified && var.emr_service_policy_json != null && try(length(var.emr_config.runtime_reference) > 0, false) && var.emr_config.bootstrap_uri != null && var.emr_config.bootstrap_sha256 != null && var.emr_config.runtime_archive_uri != null && var.emr_config.job_jar_uri != null && var.emr_config.job_jar_sha256 != null)
      error_message = "EMR remains disabled until an explicit proven runtime evidence reference, a bootstrap S3 URI with its sha256, the runtime archive S3 URI (G5) and the job JAR S3 URI with its sha256 are supplied. Stock Scala 2.12 Spark is not installed (decision 12-10)."
    }
    precondition {
      condition     = !var.emr_config.enabled || alltrue([for name, sha in local.emr_step_manifest.programs : length([for a in var.emr_config.extra_artifacts : a if a.dest == "${local.emr_step_manifest.bin_dir}/${name}" && a.sha256 == sha]) == 1])
      error_message = "Finding C1: extra_artifacts must install each EMR step program (sc-step.sh, sc-ceiling-check.py, sc-class-origin-verify.py, sc-render-spark-config.py) exactly once at <bin_dir>/<name> with the sha256 pinned in infra/terraform/emr-step-programs.json (the reviewed hashes of the files under scripts/emr/). Without them every EMR step fails closed on the node after the run budget is reserved."
    }
    precondition {
      condition     = !var.emr_config.enabled || alltrue([for u in concat([for x in [var.emr_config.bootstrap_uri, var.emr_config.runtime_archive_uri, var.emr_config.job_jar_uri] : x if x != null], [for a in var.emr_config.extra_artifacts : a.uri]) : startswith(u, "s3://${module.datalake.bucket_names.artifacts}/")])
      error_message = "Every EMR artifact URI (bootstrap, runtime archive, job jar, extra artifacts) must lie in the project artifacts bucket: that is the bucket the EMR instance role reads."
    }
    precondition {
      condition     = !var.runtime_enabled || (var.runtime_composition_verified && var.image_revision != null && var.neptune_enabled && alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : alltrue([for n in ["SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"] : contains(keys(lookup(var.service_secret_bindings, s, {})), n)])]) && contains(keys(lookup(var.service_secret_bindings, "query-api", {})), "SCHOLARCHAIN_INTERNAL_TOKEN") && contains(keys(lookup(var.service_secret_bindings, "graph-service", {})), "SCHOLARCHAIN_GRAPH_CURSOR_KEY"))
      error_message = "Runtime activation needs a verified future live composition, immutable revision, Neptune and named auth secret references for all services (plus query outgoing token and shared graph cursor key). Current artifacts remain unconfigured."
    }
    precondition {
      condition     = var.https_certificate_arn == null || (var.runtime_enabled && length(var.public_ingress_cidrs) > 0 && startswith(var.https_certificate_arn, "arn:aws:acm:${var.aws_region}:${var.aws_account_id}:certificate/"))
      error_message = "HTTPS needs enabled runtime, approved ingress CIDRs and a certificate in the selected account/region. No HTTP fallback."
    }
    precondition {
      condition     = var.api_error_rate_percent > 0 && var.api_error_rate_percent <= 100 && var.latency_alarm_seconds > 0 && var.queue_age_alarm_seconds > 0
      error_message = "Alarm thresholds must be finite positive bounds."
    }
  }
}
module "neptune" {
  audit_log_group_name = module.observability.neptune_audit_log_group_name
  source               = "./modules/neptune"
  name_prefix          = local.name_prefix
  enabled              = var.neptune_enabled
  engine_version       = var.neptune_engine_version
  parameter_family     = var.neptune_parameter_family
  min_capacity         = var.neptune_min_ncu
  max_capacity         = var.neptune_max_ncu
  backup_days          = var.neptune_backup_days
  cleanup_mode         = var.cleanup_mode
  kms_key_arn          = module.identity.kms_key_arn
  subnet_ids           = module.network.ids.data_subnet_ids
  security_group_id    = module.network.ids.security_group_ids.neptune
  loader_role_arn      = module.identity.role_arns.neptune_loader
  port                 = var.neptune_port
  aws_region           = var.aws_region
  aws_account_id       = var.aws_account_id
  tags                 = module.foundation.tags
}
module "s3vectors" {
  non_filterable_metadata_keys = var.vector_non_filterable_metadata_keys
  source                       = "./modules/s3vectors"
  name_prefix                  = local.name_prefix
  aws_account_id               = var.aws_account_id
  kms_key_arn                  = module.identity.kms_key_arn
  cleanup_mode                 = var.cleanup_mode
  dimension                    = var.vector_dimension
  metric                       = var.vector_metric
  tags                         = module.foundation.tags
}
module "workflow" {
  source         = "./modules/workflow"
  name_prefix    = local.name_prefix
  aws_account_id = var.aws_account_id
  aws_region     = var.aws_region
  queue_arn      = module.messaging.queue_arn
  queue_url      = module.messaging.queue_urls.embedding
  dlq_arn        = module.messaging.dead_letter_queue_arn
  dlq_url        = module.messaging.queue_urls.dead_letter
  kms_key_arn    = module.identity.kms_key_arn
  tags           = module.foundation.tags
}

module "emr" {
  source                  = "./modules/emr"
  name_prefix             = local.name_prefix
  config                  = var.emr_config
  kms_key_arn             = module.identity.kms_key_arn
  log_bucket              = module.datalake.bucket_names.logs
  artifacts_bucket        = module.datalake.bucket_names.artifacts
  aws_region              = var.aws_region
  aws_account_id          = var.aws_account_id
  vpc_id                  = module.network.ids.vpc_id
  instance_role_arn       = module.identity.role_arns.emr_ec2
  instance_role_name      = module.identity.emr_ec2_role_name
  subnet_id               = module.network.ids.application_subnet_ids[0]
  security_group_id       = module.network.ids.security_group_ids.emr
  service_access_group_id = module.network.ids.emr_service_access_group_id
  instance_profile_arn    = module.identity.emr_ready_profile_arn
  service_role_arn        = module.identity.emr_ready_service_arn
  tags                    = module.foundation.tags
}

module "observability" {
  workflow_arn          = module.workflow.arn
  source                = "./modules/observability"
  name_prefix           = local.name_prefix
  aws_region            = var.aws_region
  retention_days        = var.log_retention_days
  notification_arns     = var.alarm_notification_arns
  application_namespace = var.application_metrics_namespace
  api_error_percent     = var.api_error_rate_percent
  latency_seconds       = var.latency_alarm_seconds
  queue_age_seconds     = var.queue_age_alarm_seconds
  queue_name            = "${local.name_prefix}-embedding"
  table_names           = module.dynamodb.table_names
  neptune_identifier    = module.neptune.cluster_identifier
  emr_cluster_id        = module.emr.cluster_id
  tags                  = module.foundation.tags
}
