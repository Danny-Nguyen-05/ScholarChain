locals { active = var.config.enabled && var.config.release_label != null && var.config.bootstrap_uri != null && var.config.tls_certificate_uri != null && var.config.runtime_reference != null }
resource "aws_emr_security_configuration" "encrypted" {
  count = local.active ? 1 : 0
  name  = "${var.name_prefix}-encrypted"
  configuration = jsonencode({ EncryptionConfiguration = {
    EnableInTransitEncryption        = true
    EnableAtRestEncryption           = true
    InTransitEncryptionConfiguration = { TLSCertificateConfiguration = { CertificateProviderType = "PEM", S3Object = var.config.tls_certificate_uri } }
    AtRestEncryptionConfiguration = {
      S3EncryptionConfiguration        = { EncryptionMode = "SSE-KMS", AwsKmsKey = var.kms_key_arn }
      LocalDiskEncryptionConfiguration = { EncryptionKeyProviderType = "AwsKms", AwsKmsKey = var.kms_key_arn, EnableEbsEncryption = true }
    }
  } })
}
resource "aws_emr_cluster" "pipeline" {
  count                             = local.active ? 1 : 0
  name                              = "${var.name_prefix}-pipeline"
  release_label                     = var.config.release_label
  applications                      = ["Hadoop", "Spark"]
  service_role                      = var.service_role_arn
  log_uri                           = "s3://${var.log_bucket}/emr/"
  log_encryption_kms_key_id         = var.kms_key_arn
  security_configuration            = aws_emr_security_configuration.encrypted[0].name
  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false
  scale_down_behavior               = "TERMINATE_AT_TASK_COMPLETION"
  ebs_root_volume_size              = 32
  step_concurrency_level            = 1
  ec2_attributes {
    subnet_id                         = var.subnet_id
    instance_profile                  = var.instance_profile_arn
    emr_managed_master_security_group = var.security_group_id
    emr_managed_slave_security_group  = var.security_group_id
    service_access_security_group     = var.service_access_group_id
  }
  master_instance_group {
    name           = "primary"
    instance_count = 1
    instance_type  = var.config.instance_type
  }
  core_instance_group {
    name           = "core"
    instance_count = 1
    instance_type  = var.config.instance_type
  }
  bootstrap_action {
    name = "explicit-reviewed-spark-runtime"
    path = var.config.bootstrap_uri
    args = [var.config.runtime_reference]
  }
  auto_termination_policy { idle_timeout = var.config.idle_timeout_seconds }
  tags = merge(var.tags, { runtime_evidence = var.config.runtime_reference, "for-use-with-amazon-emr-managed-policies" = "true" })
  lifecycle { ignore_changes = [core_instance_group[0].instance_count] }
}
resource "aws_emr_instance_group" "task" {
  count          = local.active && var.config.max_task_nodes > 0 ? 1 : 0
  name           = "task"
  cluster_id     = aws_emr_cluster.pipeline[0].id
  instance_type  = var.config.instance_type
  instance_count = 0
  lifecycle { ignore_changes = [instance_count] }
}
resource "aws_emr_managed_scaling_policy" "bounded" {
  count      = local.active ? 1 : 0
  cluster_id = aws_emr_cluster.pipeline[0].id
  compute_limits {
    unit_type                       = "Instances"
    minimum_capacity_units          = 1
    maximum_capacity_units          = 1 + var.config.max_task_nodes
    maximum_core_capacity_units     = 1
    maximum_ondemand_capacity_units = 1 + var.config.max_task_nodes
  }
}
