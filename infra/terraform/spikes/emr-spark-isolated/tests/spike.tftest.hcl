# Mock-only tests (no AWS call is possible). Run from this root: `terraform test`.
# command = apply runs against mock_provider only, so computed attributes
# (ARNs, ids) exist and the IAM policies that embed them can be inspected.
mock_provider "aws" {
  # The provider validates ARN-typed arguments even against a mock, so computed
  # ARNs and ids get realistic fixed values.
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-2:111122223333:key/11111111-2222-3333-4444-555555555555"
      key_id = "11111111-2222-3333-4444-555555555555"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = {
      id  = "scholarchain-spike-emr-111122223333-us-east-2"
      arn = "arn:aws:s3:::scholarchain-spike-emr-111122223333-us-east-2"
    }
  }
  mock_resource "aws_efs_file_system" {
    defaults = {
      id  = "fs-0123456789abcdef0"
      arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:file-system/fs-0123456789abcdef0"
    }
  }
  mock_resource "aws_efs_access_point" {
    defaults = {
      id  = "fsap-0123456789abcdef0"
      arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:access-point/fsap-0123456789abcdef0"
    }
  }
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::111122223333:role/mock-role"
    }
  }
  mock_resource "aws_iam_instance_profile" {
    defaults = {
      arn = "arn:aws:iam::111122223333:instance-profile/mock-profile"
    }
  }
}

variables {
  account_id               = "111122223333"
  owner                    = "example-owner"
  expiration_date          = "2026-11-04"
  permissions_boundary_arn = "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary"
  deployer_role_arn        = "arn:aws:iam::111122223333:role/scholarchain-deployer"
  # The runtime tarball is replaced by a tiny fixture; the real one is 321 MB
  # and lives in an ignored target/ directory.
  runtime_tgz_path   = "tests/fixtures/runtime-fixture.bin"
  runtime_tgz_sha256 = "3cdbba1642f4fa67dee2a3d68b95263c0155f21e6c05735ce428ecac875ab782"
  # The real G1 inputs tarball and relocated config are tracked in the repo.
  inputs_tgz_path         = "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/g1-upstream-inputs.tgz"
  g1_config_template_path = "../../../../docs/agent-runs/phase-12/evidence/12d-portable-runtime/build/relocated-g1-config.json"
}

# ---- pinned shape ------------------------------------------------------------

run "pinned_shape" {
  command = apply

  assert {
    condition     = output.shape.region == "us-east-2" && output.shape.release_label == "emr-7.8.0" && output.shape.primary.type == "m5.xlarge" && output.shape.core.type == "m5.xlarge" && output.shape.primary.count == 1 && output.shape.core.count == 1 && output.shape.task_nodes == 0
    error_message = "Shape must be one primary and one core m5.xlarge, emr-7.8.0, us-east-2, no task nodes."
  }
  assert {
    condition     = output.shape.max_cluster_minutes == 120 && output.shape.cap_usd == 10 && output.shape.max_attempts == 1 && !output.shape.spot && !output.shape.instance_fleets && !output.shape.autoscaling
    error_message = "120 minutes, USD 10, one attempt, no Spot, fleets or scaling."
  }
}

run "rejects_changed_region" {
  command = plan
  variables {
    region = "us-west-2"
  }
  expect_failures = [var.region]
}

run "rejects_changed_release" {
  command = plan
  variables {
    release_label = "emr-7.9.0"
  }
  expect_failures = [var.release_label]
}

run "rejects_changed_primary_type" {
  command = plan
  variables {
    primary_instance_type = "m5.2xlarge"
  }
  expect_failures = [var.primary_instance_type]
}

run "rejects_changed_core_type" {
  command = plan
  variables {
    core_instance_type = "r5.xlarge"
  }
  expect_failures = [var.core_instance_type]
}

run "rejects_two_core_nodes" {
  command = plan
  variables {
    core_instance_count = 2
  }
  expect_failures = [var.core_instance_count]
}

run "rejects_two_primary_nodes" {
  command = plan
  variables {
    primary_instance_count = 3
  }
  expect_failures = [var.primary_instance_count]
}

run "rejects_task_nodes" {
  command = plan
  variables {
    task_instance_count = 1
  }
  expect_failures = [var.task_instance_count]
}

run "rejects_spot" {
  command = plan
  variables {
    use_spot = true
  }
  expect_failures = [var.use_spot]
}

run "rejects_instance_fleets" {
  command = plan
  variables {
    use_instance_fleets = true
  }
  expect_failures = [var.use_instance_fleets]
}

run "rejects_autoscaling" {
  command = plan
  variables {
    use_autoscaling = true
  }
  expect_failures = [var.use_autoscaling]
}

run "rejects_max_minutes_above_120" {
  command = plan
  variables {
    max_cluster_minutes = 121
  }
  expect_failures = [var.max_cluster_minutes]
}

run "rejects_changed_cap" {
  command = plan
  variables {
    cap_usd = 11
  }
  expect_failures = [var.cap_usd]
}

run "rejects_second_attempt" {
  command = plan
  variables {
    max_attempts = 2
  }
  expect_failures = [var.max_attempts]
}

run "rejects_bad_expiration_date" {
  command = plan
  variables {
    expiration_date = "2026-13-45"
  }
  expect_failures = [var.expiration_date]
}

run "rejects_foreign_boundary" {
  command = plan
  variables {
    permissions_boundary_arn = "arn:aws:iam::111122223333:policy/some-other-policy"
  }
  expect_failures = [var.permissions_boundary_arn]
}

run "step_timeouts_must_fit_the_deadline" {
  command = plan
  variables {
    max_cluster_minutes = 60
  }
  expect_failures = [aws_emr_cluster.spike]
}

# ---- artifact checksums -------------------------------------------------------

run "runtime_sha_mismatch_fails" {
  command = plan
  variables {
    runtime_tgz_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
  }
  expect_failures = [var.runtime_tgz_sha256]
}

run "inputs_sha_mismatch_fails" {
  command = plan
  variables {
    inputs_tgz_sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
  }
  expect_failures = [var.inputs_tgz_sha256]
}

run "missing_runtime_file_fails" {
  command = plan
  variables {
    runtime_tgz_path = "tests/fixtures/does-not-exist.bin"
  }
  expect_failures = [var.runtime_tgz_sha256]
}

# ---- network: no public IP, no key, no SSH ------------------------------------

run "no_public_ips_no_key_no_ssh" {
  command = apply

  assert {
    condition     = !aws_subnet.private.map_public_ip_on_launch && !aws_subnet.public.map_public_ip_on_launch
    error_message = "Neither subnet may assign public IPs."
  }
  assert {
    condition     = one(aws_emr_cluster.spike.ec2_attributes).key_name == null || one(aws_emr_cluster.spike.ec2_attributes).key_name == ""
    error_message = "No EC2 key pair."
  }
  assert {
    condition = alltrue([
      for r in [
        aws_vpc_security_group_ingress_rule.primary_self, aws_vpc_security_group_ingress_rule.primary_from_core,
        aws_vpc_security_group_ingress_rule.primary_from_service_access, aws_vpc_security_group_ingress_rule.core_self,
        aws_vpc_security_group_ingress_rule.core_from_primary, aws_vpc_security_group_ingress_rule.core_from_service_access,
        aws_vpc_security_group_ingress_rule.service_access_from_primary, aws_vpc_security_group_ingress_rule.efs_from_primary,
        aws_vpc_security_group_ingress_rule.efs_from_core,
      ] :
      r.cidr_ipv4 == null && r.cidr_ipv6 == null && r.from_port != 22 && r.referenced_security_group_id != null
    ])
    error_message = "Every ingress rule references a security group (no CIDR) and none opens port 22."
  }
  assert {
    condition     = aws_vpc_security_group_ingress_rule.service_access_from_primary.from_port == 9443 && aws_vpc_security_group_ingress_rule.efs_from_primary.from_port == 2049 && aws_vpc_security_group_ingress_rule.efs_from_core.to_port == 2049
    error_message = "Service access must accept 9443 from primary; EFS accepts 2049 only."
  }
  assert {
    condition     = aws_vpc_endpoint.s3.vpc_endpoint_type == "Gateway" && endswith(aws_vpc_endpoint.s3.service_name, ".s3")
    error_message = "A gateway endpoint for S3 is required."
  }
}

# ---- cluster ----------------------------------------------------------------------

run "termination_layers_and_shape" {
  command = apply

  assert {
    condition     = aws_emr_cluster.spike.keep_job_flow_alive_when_no_steps == false && aws_emr_cluster.spike.termination_protection == false
    error_message = "Layer 1: the cluster must end after the steps; termination protection off."
  }
  assert {
    condition     = one(aws_emr_cluster.spike.auto_termination_policy).idle_timeout == 900 && one(aws_emr_cluster.spike.auto_termination_policy).idle_timeout > 0
    error_message = "Layer 4: the idle timeout must be set."
  }
  assert {
    condition     = aws_emr_cluster.spike.release_label == "emr-7.8.0" && toset(aws_emr_cluster.spike.applications) == toset(["Hadoop"])
    error_message = "Hadoop only, no stock Spark."
  }
  assert {
    condition     = aws_emr_cluster.spike.step_concurrency_level == 1 && aws_emr_cluster.spike.unhealthy_node_replacement == false && aws_emr_cluster.spike.ebs_root_volume_size == 32
    error_message = "Single step concurrency, no node replacement, 32 GiB gp3 root."
  }
  assert {
    condition     = length(aws_emr_cluster.spike.step) == 3 && [for s in aws_emr_cluster.spike.step : s.name] == ["probe", "g1", "collect"] && [for s in aws_emr_cluster.spike.step : s.action_on_failure] == ["CONTINUE", "CONTINUE", "TERMINATE_CLUSTER"]
    error_message = "Exactly three steps: probe CONTINUE, g1 CONTINUE, collect TERMINATE_CLUSTER."
  }
  assert {
    condition     = aws_emr_cluster.spike.security_configuration == "scholarchain-spike-emr-seccfg" && startswith(aws_emr_cluster.spike.log_uri, "s3://scholarchain-spike-emr-111122223333-us-east-2/")
    error_message = "Security configuration and a log URI inside the spike bucket are required."
  }
  assert {
    condition     = length(aws_emr_cluster.spike.bootstrap_action) == 1
    error_message = "One bootstrap action."
  }
}

run "ebs_layout_is_exactly_four_volumes_128_gib" {
  command = apply

  assert {
    condition = alltrue([
      for g in [one(aws_emr_cluster.spike.master_instance_group), one(aws_emr_cluster.spike.core_instance_group)] :
      length(g.ebs_config) == 1 && one(g.ebs_config).size == 32 && one(g.ebs_config).type == "gp3" && one(g.ebs_config).volumes_per_instance == 1 && g.instance_type == "m5.xlarge" && g.instance_count == 1
    ])
    error_message = "Each group: exactly one 32 GiB gp3 data volume per instance; one m5.xlarge."
  }
  assert {
    condition     = aws_emr_cluster.spike.ebs_root_volume_size + one(one(aws_emr_cluster.spike.master_instance_group).ebs_config).size == 64 && output.shape.ebs_volumes_total == 4 && output.shape.ebs_gib_total == 128
    error_message = "Root 32 + data 32 per node, two nodes: 4 volumes, 128 GiB."
  }
}

run "steps_use_the_custom_runtime_under_timeout" {
  command = apply

  assert {
    condition = alltrue([
      for i in [0, 1] :
      aws_emr_cluster.spike.step[i].hadoop_jar_step[0].jar == "command-runner.jar" &&
      aws_emr_cluster.spike.step[i].hadoop_jar_step[0].args[0] == "/opt/scholarchain-spike/bin/run-step.sh" &&
      aws_emr_cluster.spike.step[i].hadoop_jar_step[0].args[2] == "/opt/scholarchain-runtime/bin/spark-submit" &&
      contains(aws_emr_cluster.spike.step[i].hadoop_jar_step[0].args, "yarn") &&
      contains(aws_emr_cluster.spike.step[i].hadoop_jar_step[0].args, "cluster") &&
      contains(aws_emr_cluster.spike.step[i].hadoop_jar_step[0].args, "local:/opt/scholarchain-runtime/application/scholarchain-job.jar")
    ])
    error_message = "Both Spark steps run the custom spark-submit in YARN cluster mode through run-step.sh (timeout wrapper) on the local job JAR."
  }
  assert {
    condition     = aws_emr_cluster.spike.step[0].hadoop_jar_step[0].args[1] == "1200" && aws_emr_cluster.spike.step[1].hadoop_jar_step[0].args[1] == "3000" && aws_emr_cluster.spike.step[2].hadoop_jar_step[0].args[1] == "600"
    error_message = "Step timeouts are 1200, 3000 and 600 seconds."
  }
  assert {
    condition     = contains(aws_emr_cluster.spike.step[0].hadoop_jar_step[0].args, "edu.uic.cs441.scholarchain.spark.Phase12Readiness") && contains(aws_emr_cluster.spike.step[0].hadoop_jar_step[0].args, "/mnt/scholarchain/probe-shared") && contains(aws_emr_cluster.spike.step[0].hadoop_jar_step[0].args, "/mnt/scholarchain/results/probe-distributed.json") && contains(aws_emr_cluster.spike.step[0].hadoop_jar_step[0].args, "distributed")
    error_message = "Probe step arguments."
  }
  assert {
    condition     = contains(aws_emr_cluster.spike.step[1].hadoop_jar_step[0].args, "edu.uic.cs441.scholarchain.spark.Phase6Main") && contains(aws_emr_cluster.spike.step[1].hadoop_jar_step[0].args, "/mnt/scholarchain/config/spark-g1-portable.json")
    error_message = "G1 step arguments."
  }
  assert {
    condition     = aws_emr_cluster.spike.step[2].hadoop_jar_step[0].args[2] == "/opt/scholarchain-spike/bin/collect-results.sh"
    error_message = "Collect step runs the collect script."
  }
}

# ---- Spark settings ----------------------------------------------------------------

run "spark_defaults_content" {
  command = apply

  assert {
    condition     = strcontains(output.spark_defaults, "spark.yarn.jars local:/opt/scholarchain-runtime/jars/*\n") && strcontains(output.spark_defaults, "spark.yarn.populateHadoopClasspath false\n") && strcontains(output.spark_defaults, "spark.hadoop.fs.defaultFS file:///\n")
    error_message = "Custom runtime jars, no Hadoop classpath, local file system."
  }
  assert {
    condition     = strcontains(output.spark_defaults, "spark.yarn.stagingDir file:///mnt/scholarchain/staging\n")
    error_message = "Staging must be on the shared EFS mount."
  }
  assert {
    condition     = strcontains(output.spark_defaults, "spark.yarn.appMasterEnv.JAVA_HOME /usr/lib/jvm/java-17-amazon-corretto\n") && strcontains(output.spark_defaults, "spark.executorEnv.JAVA_HOME /usr/lib/jvm/java-17-amazon-corretto\n")
    error_message = "AM and executors use the documented Corretto 17 path."
  }
  assert {
    condition     = strcontains(output.spark_defaults, "spark.executor.instances 2\n") && strcontains(output.spark_defaults, "spark.executor.cores 1\n") && strcontains(output.spark_defaults, "spark.task.maxFailures 1\n") && strcontains(output.spark_defaults, "spark.yarn.maxAppAttempts 1\n") && strcontains(output.spark_defaults, "spark.dynamicAllocation.enabled false\n") && strcontains(output.spark_defaults, "spark.shuffle.service.enabled false\n")
    error_message = "Two single-core executors, one attempt, no dynamic allocation, no shuffle service."
  }
  assert {
    condition     = strcontains(output.spark_defaults, "spark.authenticate true\n") && strcontains(output.spark_defaults, "spark.network.crypto.enabled true\n") && strcontains(output.spark_defaults, "spark.network.crypto.authEngineVersion 1\n") && strcontains(output.spark_defaults, "spark.network.crypto.saslFallback false\n") && strcontains(output.spark_defaults, "spark.io.encryption.enabled true\n")
    error_message = "AES-CTR (authEngineVersion 1) network crypto, no SASL fallback, spill encryption."
  }
  assert {
    condition     = !strcontains(output.spark_defaults, "spark.authenticate.secret") && !strcontains(output.spark_defaults, "spark.network.crypto.cipher") && !strcontains(output.spark_defaults, "GCM") && !strcontains(output.spark_defaults, "spark.io.encryption.keySizeBits")
    error_message = "No secret value, no cipher override, no AES-GCM."
  }
  assert {
    condition     = strcontains(output.spark_defaults, "spark.driver.extraJavaOptions -Xlog:class+load=info\n") && strcontains(output.spark_defaults, "spark.executor.extraJavaOptions -Xlog:class+load=info\n")
    error_message = "Class-load logging for driver and executors."
  }
}

# ---- rendered G1 config ---------------------------------------------------------------

run "g1_config_only_changes_path_prefixes" {
  command = apply

  assert {
    condition     = !strcontains(aws_s3_object.g1_config.content, "/private/tmp") && jsondecode(aws_s3_object.g1_config.content).outputRoot == "/mnt/scholarchain/outputs/g1-portable" && jsondecode(aws_s3_object.g1_config.content).checkpointDirectory == "/mnt/scholarchain/checkpoints/g1-portable"
    error_message = "All node-local prefixes become /mnt/scholarchain; the checkpoint directory is on EFS."
  }
  assert {
    condition     = jsondecode(aws_s3_object.g1_config.content).entityResolutionRunRoot == "/mnt/scholarchain/inputs/g1/er" && jsondecode(aws_s3_object.g1_config.content).hadoopRunRoot == "/mnt/scholarchain/inputs/g1/hadoop"
    error_message = "Input roots follow the extracted inputs layout."
  }
  assert {
    condition = alltrue([
      for k, v in jsondecode(file(var.g1_config_template_path)) :
      contains(["checkpointDirectory", "entityResolutionRunRoot", "hadoopRunRoot", "outputRoot"], k) || jsonencode(v) == jsonencode(jsondecode(aws_s3_object.g1_config.content)[k])
    ]) && length(jsondecode(file(var.g1_config_template_path))) == length(jsondecode(aws_s3_object.g1_config.content))
    error_message = "Every non-path field is identical to the template and no field is added or removed."
  }
}

# ---- bucket ------------------------------------------------------------------------------

run "bucket_is_private_encrypted_and_destroyable" {
  command = apply

  assert {
    condition     = aws_s3_bucket.spike.force_destroy == true && aws_s3_bucket.spike.bucket == "scholarchain-spike-emr-111122223333-us-east-2"
    error_message = "force_destroy true and the account+region suffixed name."
  }
  assert {
    condition     = aws_s3_bucket_public_access_block.spike.block_public_acls && aws_s3_bucket_public_access_block.spike.block_public_policy && aws_s3_bucket_public_access_block.spike.ignore_public_acls && aws_s3_bucket_public_access_block.spike.restrict_public_buckets
    error_message = "All four public access blocks."
  }
  assert {
    condition     = one(aws_s3_bucket_ownership_controls.spike.rule).object_ownership == "BucketOwnerEnforced"
    error_message = "BucketOwnerEnforced."
  }
  assert {
    condition     = one(aws_s3_bucket_server_side_encryption_configuration.spike.rule).bucket_key_enabled == true && one(one(aws_s3_bucket_server_side_encryption_configuration.spike.rule).apply_server_side_encryption_by_default).sse_algorithm == "aws:kms"
    error_message = "SSE-KMS by default with a bucket key."
  }
  assert {
    condition     = jsondecode(aws_s3_bucket_policy.spike.policy).Statement[0].Effect == "Deny" && jsondecode(aws_s3_bucket_policy.spike.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    error_message = "TLS-only deny."
  }
  assert {
    condition     = toset(output.staged_object_keys) == toset(["staging/runtime/scholarchain-runtime.tgz", "staging/inputs/g1-upstream-inputs.tgz", "staging/bootstrap/bootstrap.sh", "staging/bin/run-step.sh", "staging/bin/collect-results.sh", "staging/config/spark-g1-portable.json", "staging/config/spark-defaults.conf"])
    error_message = "Exactly the seven reviewed staged objects."
  }
}

# ---- KMS, security configuration, EFS ---------------------------------------------------

run "kms_and_security_configuration" {
  command = apply

  assert {
    condition     = aws_kms_key.spike.deletion_window_in_days == 7 && aws_kms_key.spike.enable_key_rotation == false
    error_message = "Seven-day deletion window; no rotation for a same-day spike."
  }
  assert {
    condition     = jsondecode(aws_emr_security_configuration.spike.configuration).EncryptionConfiguration.EnableAtRestEncryption == true && jsondecode(aws_emr_security_configuration.spike.configuration).EncryptionConfiguration.EnableInTransitEncryption == false
    error_message = "At-rest encryption on; in-transit TLS dropped by human decision."
  }
  assert {
    condition     = jsondecode(aws_emr_security_configuration.spike.configuration).EncryptionConfiguration.AtRestEncryptionConfiguration.LocalDiskEncryptionConfiguration.EnableEbsEncryption == true && jsondecode(aws_emr_security_configuration.spike.configuration).EncryptionConfiguration.AtRestEncryptionConfiguration.S3EncryptionConfiguration.EncryptionMode == "SSE-KMS"
    error_message = "EBS and local disk encryption via KMS, S3 SSE-KMS."
  }
  assert {
    condition     = !strcontains(aws_emr_security_configuration.spike.configuration, "TLSCertificateConfiguration") && !strcontains(aws_emr_security_configuration.spike.configuration, ".pem")
    error_message = "No certificate material."
  }
}

run "efs_is_encrypted_without_backup_and_restricted" {
  command = apply

  assert {
    condition     = aws_efs_file_system.spike.encrypted == true && aws_efs_file_system.spike.performance_mode == "generalPurpose" && aws_efs_file_system.spike.throughput_mode == "elastic"
    error_message = "Encrypted, General Purpose, Elastic throughput."
  }
  assert {
    condition     = one(aws_efs_backup_policy.spike.backup_policy).status == "DISABLED"
    error_message = "Backups explicitly disabled."
  }
  assert {
    condition     = one(aws_efs_access_point.spike.posix_user).uid == 1500 && one(aws_efs_access_point.spike.posix_user).gid == 1500 && one(aws_efs_access_point.spike.root_directory).path == "/scholarchain-spike"
    error_message = "Dedicated POSIX identity and root directory."
  }
  assert {
    condition     = jsondecode(aws_efs_file_system_policy.spike.policy).Statement[0].Effect == "Deny" && jsondecode(aws_efs_file_system_policy.spike.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    error_message = "File system policy denies non-TLS."
  }
  assert {
    condition     = length(aws_efs_mount_target.private.security_groups) == 1
    error_message = "One mount target behind the EFS security group."
  }
}

# ---- IAM -------------------------------------------------------------------------------------

run "iam_roles_carry_the_boundary_and_prefix" {
  command = apply

  assert {
    condition     = startswith(aws_iam_role.service.name, "scholarchain-spike-emr-") && startswith(aws_iam_role.instance.name, "scholarchain-spike-emr-") && startswith(aws_iam_instance_profile.instance.name, "scholarchain-spike-emr-")
    error_message = "All IAM names carry the spike prefix."
  }
  assert {
    condition     = aws_iam_role.service.permissions_boundary == var.permissions_boundary_arn && aws_iam_role.instance.permissions_boundary == var.permissions_boundary_arn
    error_message = "Both roles attach the deployer's boundary."
  }
  assert {
    condition     = aws_iam_role_policy_attachment.service_emr_v2.policy_arn == "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
    error_message = "The EMR service role uses AmazonEMRServicePolicy_v2."
  }
  assert {
    condition     = jsondecode(aws_iam_role_policy.service_pass_instance_role.policy).Statement[0].Resource == "arn:aws:iam::111122223333:role/scholarchain-spike-emr-instance"
    error_message = "The service role may pass only the instance role."
  }
}

run "instance_profile_policy_has_no_wildcard_resources" {
  command = apply

  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_role_policy.instance.policy).Statement :
      alltrue([for r in tolist(try(tolist(st.Resource), [st.Resource])) : r != "*" && !endswith(r, ":*") && !strcontains(r, "*") || endswith(r, "/*") && !startswith(r, "*")])
    ])
    error_message = "No bare '*' Resource for S3, KMS or EFS."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_role_policy.instance.policy).Statement :
      alltrue([for a in st.Action : !endswith(a, "*")])
    ])
    error_message = "Actions are enumerated."
  }
  assert {
    condition = toset(flatten([for st in jsondecode(aws_iam_role_policy.instance.policy).Statement : st.Action])) == toset([
      "s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListBucket",
      "kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:DescribeKey",
      "elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite",
      "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy",
    ])
    error_message = "The instance profile has S3, KMS, EFS client and the three EMR auto-termination actions only."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.instance.policy).Statement :
      toset(st.Action) == toset(["elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy"]) && st.Resource == ["arn:aws:elasticmapreduce:us-east-2:111122223333:cluster/*"] && st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "Auto-termination actions (needed for the idle timeout to work, per AWS re:Post) on stack-tagged clusters in us-east-2 only."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_role_policy.instance.policy).Statement :
      !strcontains(jsonencode(st.Resource), "\"*\"")
    ])
    error_message = "Resources are bucket prefixes, one key and one file system."
  }
}

run "key_policy_names_only_known_principals" {
  command = apply

  assert {
    condition = toset([for st in jsondecode(aws_kms_key.spike.policy).Statement : st.Principal.AWS]) == toset([
      "arn:aws:iam::111122223333:root",
      "arn:aws:iam::111122223333:role/scholarchain-spike-emr-service",
      "arn:aws:iam::111122223333:role/scholarchain-spike-emr-instance",
      "arn:aws:iam::111122223333:role/scholarchain-deployer",
    ])
    error_message = "The key policy grants the account root, the deployer role, the service role and the instance role only."
  }
}

# ---- tags -------------------------------------------------------------------------------------

run "required_tags_come_from_provider_default_tags" {
  command = apply

  assert {
    condition = output.default_tags == {
      course                                     = "CS441"
      project                                    = "ScholarChain"
      environment                                = "spike"
      owner                                      = "example-owner"
      expiration                                 = "2026-11-04"
      "scholarchain:stack"                       = "spike-emr"
      "for-use-with-amazon-emr-managed-policies" = "true"
    }
    error_message = "provider default_tags must carry the seven required tags."
  }
  assert {
    condition = alltrue([
      for t in [aws_vpc.spike.tags, aws_subnet.private.tags, aws_subnet.public.tags, aws_eip.nat.tags, aws_nat_gateway.spike.tags, aws_security_group.primary.tags, aws_security_group.core.tags, aws_security_group.service_access.tags, aws_security_group.efs.tags, aws_kms_key.spike.tags, aws_s3_bucket.spike.tags, aws_efs_file_system.spike.tags] :
      alltrue([for k in keys(t) : !contains(keys(output.default_tags), k)])
    ])
    error_message = "Resources must not override or duplicate the default tag keys."
  }
}

run "key_policy_has_only_enumerated_actions_and_can_be_administered" {
  command = apply

  assert {
    condition = alltrue([
      for st in jsondecode(aws_kms_key.spike.policy).Statement :
      alltrue([for a in st.Action : !strcontains(a, "*")])
    ])
    error_message = "The key policy must not use kms:* or any wildcard action."
  }
  assert {
    condition = alltrue([
      for a in ["kms:PutKeyPolicy", "kms:GetKeyPolicy", "kms:DescribeKey", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:EnableKey", "kms:DisableKey", "kms:TagResource", "kms:UntagResource", "kms:ListResourceTags", "kms:GetKeyRotationStatus", "kms:EnableKeyRotation", "kms:DisableKeyRotation", "kms:UpdateKeyDescription", "kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant", "kms:CreateAlias", "kms:DeleteAlias"] :
      contains(jsondecode(aws_kms_key.spike.policy).Statement[0].Action, a)
    ])
    error_message = "The account root statement must keep the key manageable and deletable."
  }
}

run "key_administration_is_granted_to_the_deployer_role_in_the_key_policy" {
  command = apply

  assert {
    condition = anytrue([
      for st in jsondecode(aws_kms_key.spike.policy).Statement :
      st.Principal.AWS == "arn:aws:iam::111122223333:role/scholarchain-deployer" && alltrue([for a in ["kms:PutKeyPolicy", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:DescribeKey", "kms:GetKeyPolicy", "kms:CreateAlias", "kms:DeleteAlias"] : contains(st.Action, a)]) && !can(st.Condition)
    ])
    error_message = "The deployer role ARN is granted key administration directly in the key policy."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_kms_key.spike.policy).Statement :
      st.Principal.AWS == "arn:aws:iam::111122223333:role/scholarchain-deployer" && contains(st.Action, "kms:Decrypt") && toset(st.Condition.StringEquals["kms:ViaService"]) == toset(["s3.us-east-2.amazonaws.com", "elasticfilesystem.us-east-2.amazonaws.com"]) && !contains(st.Action, "kms:PutKeyPolicy")
    ])
    error_message = "The deployer may use the key only through S3 and EFS."
  }
}

run "rejects_bad_deployer_role_arn" {
  command = plan
  variables {
    deployer_role_arn = "arn:aws:iam::111122223333:role/*"
  }
  expect_failures = [var.deployer_role_arn]
}

run "rejects_foreign_account_deployer_role_arn" {
  command = plan
  variables {
    deployer_role_arn = "arn:aws:iam::999999999999:role/scholarchain-deployer"
  }
  expect_failures = [var.deployer_role_arn]
}

