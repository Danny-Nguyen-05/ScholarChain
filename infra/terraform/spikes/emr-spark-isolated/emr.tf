# At-rest encryption only (local disk + EBS via the CMK, S3 SSE-KMS). In-transit
# TLS artifacts were dropped by human decision; see README "Disclosed limitations".
resource "aws_emr_security_configuration" "spike" {
  name = "${local.prefix}-seccfg"
  configuration = jsonencode({
    EncryptionConfiguration = {
      EnableInTransitEncryption = false
      EnableAtRestEncryption    = true
      AtRestEncryptionConfiguration = {
        S3EncryptionConfiguration = {
          EncryptionMode = "SSE-KMS"
          AwsKmsKey      = aws_kms_key.spike.arn
        }
        LocalDiskEncryptionConfiguration = {
          EncryptionKeyProviderType = "AwsKms"
          AwsKmsKey                 = aws_kms_key.spike.arn
          EnableEbsEncryption       = true
        }
      }
    }
  })
}

locals {
  s3_flags = "--bucket ${aws_s3_bucket.spike.id} --region ${var.region}"
  # Deadline minutes the bootstrap arms the shutdown timer with, before uptime
  # and the startup allowance are subtracted on the node.
  bootstrap_args = [
    "--bucket", aws_s3_bucket.spike.id,
    "--region", var.region,
    "--max-minutes", tostring(var.max_cluster_minutes),
    "--startup-allowance-minutes", tostring(var.startup_allowance_minutes),
    "--runtime-key", local.key_runtime,
    "--runtime-sha256", var.runtime_tgz_sha256,
    "--job-jar-sha256", var.job_jar_sha256,
    "--inputs-key", local.key_inputs,
    "--inputs-sha256", var.inputs_tgz_sha256,
    "--g1-config-key", local.key_g1_config,
    "--spark-defaults-key", local.key_spark_default,
    "--run-step-key", local.key_run_step,
    "--collect-key", local.key_collect,
    "--efs-id", aws_efs_file_system.spike.id,
    "--access-point-id", aws_efs_access_point.spike.id,
  ]

  # Every Spark step is wrapped by run-step.sh, which sets the runtime
  # environment and applies `timeout` with a kill-after.
  probe_args = [
    "${local.spike_bin}/run-step.sh", tostring(var.probe_timeout_seconds),
    local.spark_submit,
    "--master", "yarn", "--deploy-mode", "cluster", "--name", "scholarchain-probe",
    "--class", "edu.uic.cs441.scholarchain.spark.Phase12Readiness",
    "local:${local.job_jar}",
    "probe", "${local.mnt}/probe-shared", "${local.mnt}/results/probe-distributed.json", "distributed",
  ]
  g1_args = [
    "${local.spike_bin}/run-step.sh", tostring(var.g1_timeout_seconds),
    local.spark_submit,
    "--master", "yarn", "--deploy-mode", "cluster", "--name", "scholarchain-g1",
    "--class", "edu.uic.cs441.scholarchain.spark.Phase6Main",
    "local:${local.job_jar}",
    "${local.mnt}/config/spark-g1-portable.json",
  ]
  collect_args = [
    "${local.spike_bin}/run-step.sh", tostring(var.collect_timeout_seconds),
    "${local.spike_bin}/collect-results.sh",
    "--bucket", aws_s3_bucket.spike.id, "--region", var.region,
    "--max-bytes", "67108864",
  ]
}

resource "aws_emr_cluster" "spike" {
  name          = "${local.prefix}-cluster"
  release_label = var.release_label
  applications  = ["Hadoop"] # no stock Spark: the custom runtime is used

  service_role           = aws_iam_role.service.arn
  security_configuration = aws_emr_security_configuration.spike.name
  log_uri                = "s3://${aws_s3_bucket.spike.id}/emr-logs/"

  # Termination layers 1, 2 (step), 4 (idle). Layer 3 is the node timer.
  keep_job_flow_alive_when_no_steps = false
  termination_protection            = false
  unhealthy_node_replacement        = false
  step_concurrency_level            = 1
  auto_termination_policy {
    idle_timeout = var.idle_timeout_seconds
  }

  ebs_root_volume_size = 32

  ec2_attributes {
    subnet_id                         = aws_subnet.private.id
    emr_managed_master_security_group = aws_security_group.primary.id
    emr_managed_slave_security_group  = aws_security_group.core.id
    service_access_security_group     = aws_security_group.service_access.id
    instance_profile                  = aws_iam_instance_profile.instance.arn
    # no key_name: no SSH key pair
  }

  master_instance_group {
    instance_type  = var.primary_instance_type
    instance_count = var.primary_instance_count
    ebs_config {
      type                 = "gp3"
      size                 = 32
      iops                 = 3000
      throughput           = 125
      volumes_per_instance = 1
    }
  }

  core_instance_group {
    instance_type  = var.core_instance_type
    instance_count = var.core_instance_count
    ebs_config {
      type                 = "gp3"
      size                 = 32
      iops                 = 3000
      throughput           = 125
      volumes_per_instance = 1
    }
  }

  bootstrap_action {
    name = "scholarchain-bootstrap"
    path = "s3://${aws_s3_bucket.spike.id}/${local.key_bootstrap}"
    args = local.bootstrap_args
  }

  step {
    name              = "probe"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
      jar  = "command-runner.jar"
      args = local.probe_args
    }
  }

  step {
    name              = "g1"
    action_on_failure = "CONTINUE"
    hadoop_jar_step {
      jar  = "command-runner.jar"
      args = local.g1_args
    }
  }

  step {
    name              = "collect"
    action_on_failure = "TERMINATE_CLUSTER"
    hadoop_jar_step {
      jar  = "command-runner.jar"
      args = local.collect_args
    }
  }

  lifecycle {
    # Steps are ForceNew in the provider and their state changes as they run;
    # the cluster is single-use and never updated in place.
    ignore_changes = [step]

    precondition {
      condition     = local.step_budget_seconds <= local.usable_seconds
      error_message = "probe+g1+collect timeouts (${local.step_budget_seconds}s) must fit in max_cluster_minutes - startup allowance - 10 minutes (${local.usable_seconds}s)."
    }
    precondition {
      condition     = var.idle_timeout_seconds > var.collect_timeout_seconds
      error_message = "idle_timeout_seconds must exceed collect_timeout_seconds."
    }
  }

  depends_on = [
    aws_s3_object.runtime, aws_s3_object.inputs, aws_s3_object.bootstrap, aws_s3_object.run_step,
    aws_s3_object.collect_results, aws_s3_object.g1_config, aws_s3_object.spark_defaults,
    aws_efs_mount_target.private, aws_efs_file_system_policy.spike, aws_efs_backup_policy.spike,
    aws_iam_role_policy.instance, aws_iam_role_policy.service_pass_instance_role,
    aws_iam_role_policy_attachment.service_emr_v2, aws_kms_alias.spike, aws_vpc_endpoint.s3,
    aws_route_table_association.private,
    aws_vpc_security_group_ingress_rule.primary_from_service_access,
    aws_vpc_security_group_ingress_rule.core_from_service_access,
    aws_vpc_security_group_ingress_rule.service_access_from_primary,
    aws_vpc_security_group_egress_rule.service_access_to_primary,
    aws_vpc_security_group_egress_rule.service_access_to_core,
  ]
}
