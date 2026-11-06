locals {
  cfg = var.config
  # Everything the bootstrap and the cluster need is supplied; otherwise nothing is created.
  active = local.cfg.enabled && local.cfg.runtime_reference != null && local.cfg.bootstrap_uri != null && local.cfg.bootstrap_sha256 != null && local.cfg.runtime_archive_uri != null && local.cfg.job_jar_uri != null && local.cfg.job_jar_sha256 != null

  artifact_uris = concat([for u in [local.cfg.bootstrap_uri, local.cfg.runtime_archive_uri, local.cfg.job_jar_uri] : u if u != null], [for a in local.cfg.extra_artifacts : a.uri])

  # Decision 12-10 Spark settings, rendered as the node's spark-defaults.conf: "key value" lines in key order. The bootstrap
  # verifies the sha256 below, removes any JAVA_HOME entry and appends the Java 17 it resolved on the node.
  spark_defaults_text = "${join("\n", [for k in sort(keys(var.spark_defaults)) : "${k} ${var.spark_defaults[k]}"])}\n"

  bootstrap_args = local.active ? concat([
    "--region", var.aws_region,
    "--max-minutes", tostring(local.cfg.node_deadline_minutes),
    "--startup-allowance-minutes", tostring(local.cfg.startup_allowance_minutes),
    "--self-sha256", local.cfg.bootstrap_sha256,
    "--runtime-uri", local.cfg.runtime_archive_uri, "--runtime-sha256", local.cfg.runtime_archive_sha256,
    "--job-jar-uri", local.cfg.job_jar_uri, "--job-jar-sha256", local.cfg.job_jar_sha256,
    "--spark-defaults-b64", base64encode(local.spark_defaults_text), "--spark-defaults-sha256", sha256(local.spark_defaults_text),
    "--efs-id", aws_efs_file_system.staging[0].id, "--access-point-id", aws_efs_access_point.staging[0].id,
  ], flatten([for a in local.cfg.extra_artifacts : ["--artifact", "${a.uri},${a.sha256},${a.dest}"]])) : []

  # G3/G6 caps, exposed for the cross-check tests.
  caps = {
    primary_nodes        = 1
    core_nodes           = 1
    max_task_nodes       = local.cfg.max_task_nodes
    max_instances        = 2 + local.cfg.max_task_nodes
    instance_type        = local.cfg.instance_type
    idle_timeout_seconds = local.cfg.idle_timeout_seconds
  }

  ebs = { type = "gp3", size = local.cfg.ebs_size_gb, iops = local.cfg.ebs_iops, throughput = local.cfg.ebs_throughput, volumes_per_instance = 1 }
}

# At-rest encryption only: S3 SSE-KMS plus local-disk and EBS encryption with the project CMK. In-transit TLS is DISABLED by
# the human's 13C decision (the PEM configuration is untested with the custom runtime and 13C cannot test it live); Spark's own
# authentication, AES-CTR network encryption and IO encryption stay on (see spark_defaults). Hadoop and YARN RPC inside the
# private subnet are unencrypted. See infra/terraform/README.md, "Disclosed limitations".
resource "aws_emr_security_configuration" "encrypted" {
  count = local.active ? 1 : 0
  name  = "${var.name_prefix}-encrypted"
  configuration = jsonencode({ EncryptionConfiguration = {
    EnableInTransitEncryption = false
    EnableAtRestEncryption    = true
    AtRestEncryptionConfiguration = {
      S3EncryptionConfiguration        = { EncryptionMode = "SSE-KMS", AwsKmsKey = var.kms_key_arn }
      LocalDiskEncryptionConfiguration = { EncryptionKeyProviderType = "AwsKms", AwsKmsKey = var.kms_key_arn, EnableEbsEncryption = true }
    }
  } })
}

resource "aws_emr_cluster" "pipeline" {
  count         = local.active ? 1 : 0
  name          = "${var.name_prefix}-pipeline"
  release_label = local.cfg.release_label
  # Hadoop only: the stock Spark 3.5.4-amzn / Scala 2.12 is not installed; the bootstrap installs the portable runtime.
  applications                      = ["Hadoop"]
  service_role                      = var.service_role_arn
  log_uri                           = "s3://${var.log_bucket}/emr/"
  log_encryption_kms_key_id         = var.kms_key_arn
  security_configuration            = aws_emr_security_configuration.encrypted[0].name
  keep_job_flow_alive_when_no_steps = true
  termination_protection            = false
  unhealthy_node_replacement        = false
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
    instance_type  = local.cfg.instance_type
    ebs_config {
      type                 = local.ebs.type
      size                 = local.ebs.size
      iops                 = local.ebs.iops
      throughput           = local.ebs.throughput
      volumes_per_instance = local.ebs.volumes_per_instance
    }
  }
  core_instance_group {
    name           = "core"
    instance_count = 1
    instance_type  = local.cfg.instance_type
    ebs_config {
      type                 = local.ebs.type
      size                 = local.ebs.size
      iops                 = local.ebs.iops
      throughput           = local.ebs.throughput
      volumes_per_instance = local.ebs.volumes_per_instance
    }
  }
  bootstrap_action {
    name = "scholarchain-bootstrap"
    path = local.cfg.bootstrap_uri
    args = local.bootstrap_args
  }
  auto_termination_policy { idle_timeout = local.cfg.idle_timeout_seconds }
  # Carried item 17: the scholarchain:stack tag propagates from the cluster to its EC2 instances and ENIs, so an IAM boundary
  # can require it on instance/* and network-interface/*. The EMR managed-policies tag is kept because the supplied service
  # policy (emr_service_policy_json) follows AmazonEMRServicePolicy_v2's tag conditions; the network module tags the security
  # groups the same way.
  tags = merge(var.tags, {
    runtime_evidence                           = local.cfg.runtime_reference
    "scholarchain:stack"                       = local.cfg.stack_tag_value
    "for-use-with-amazon-emr-managed-policies" = "true"
  })
  lifecycle { ignore_changes = [core_instance_group[0].instance_count] }
}

# G3: no task group unless tfvars allow task nodes; the initial count is task_node_count (default 0).
resource "aws_emr_instance_group" "task" {
  count          = local.active && local.cfg.max_task_nodes > 0 ? 1 : 0
  name           = "task"
  cluster_id     = aws_emr_cluster.pipeline[0].id
  instance_type  = local.cfg.instance_type
  instance_count = local.cfg.task_node_count
  # gp3 at the baseline 3000 IOPS like the primary and core groups. hashicorp/aws 6.44.0 has NO `throughput` argument on
  # aws_emr_instance_group.ebs_config (only on the cluster's master and core groups, checked with
  # `terraform providers schema`), so the 125 MiB/s baseline throughput of gp3 cannot be written here; EMR applies the gp3
  # default of 125 MiB/s when none is given.
  ebs_config {
    type                 = local.ebs.type
    size                 = local.ebs.size
    iops                 = local.ebs.iops
    volumes_per_instance = local.ebs.volumes_per_instance
  }
  lifecycle { ignore_changes = [instance_count] }
}

# G3: managed scaling is OFF unless tfvars enable it; the cap is managed_scaling_max_capacity (core + task, primary excluded).
resource "aws_emr_managed_scaling_policy" "bounded" {
  count      = local.active && local.cfg.managed_scaling_enabled ? 1 : 0
  cluster_id = aws_emr_cluster.pipeline[0].id
  compute_limits {
    unit_type                       = "Instances"
    minimum_capacity_units          = 1
    maximum_capacity_units          = local.cfg.managed_scaling_max_capacity
    maximum_core_capacity_units     = 1
    maximum_ondemand_capacity_units = local.cfg.managed_scaling_max_capacity
  }
}
