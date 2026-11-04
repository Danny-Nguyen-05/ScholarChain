output "shape" {
  description = "The pinned cluster shape."
  value = {
    region                = var.region
    release_label         = var.release_label
    primary               = { type = var.primary_instance_type, count = var.primary_instance_count }
    core                  = { type = var.core_instance_type, count = var.core_instance_count }
    task_nodes            = var.task_instance_count
    spot                  = var.use_spot
    instance_fleets       = var.use_instance_fleets
    autoscaling           = var.use_autoscaling
    max_cluster_minutes   = var.max_cluster_minutes
    idle_timeout_seconds  = var.idle_timeout_seconds
    cap_usd               = var.cap_usd
    max_attempts          = var.max_attempts
    ebs_volumes_total     = 4
    ebs_gib_total         = 128
    in_transit_encryption = false
    spark_network_crypto  = "AES-CTR authEngineVersion 1"
  }
}

output "bucket" {
  value = aws_s3_bucket.spike.id
}

output "cluster_id" {
  value = aws_emr_cluster.spike.id
}

output "efs_file_system_id" {
  value = aws_efs_file_system.spike.id
}

output "kms_key_arn" {
  value = aws_kms_key.spike.arn
}

output "vpc_id" {
  value = aws_vpc.spike.id
}

output "staged_object_keys" {
  value = sort([
    local.key_runtime, local.key_inputs, local.key_bootstrap, local.key_run_step,
    local.key_collect, local.key_g1_config, local.key_spark_default,
  ])
}

output "spark_defaults" {
  value = local.spark_defaults_text
}

output "default_tags" {
  description = "Applied to every taggable resource through the provider default_tags block."
  value       = local.default_tags
}
