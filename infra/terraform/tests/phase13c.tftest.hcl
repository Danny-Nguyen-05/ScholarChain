# Phase 13C: the main EMR module ported to decision 12-10, the 13C TLS decision, G2/G3/G5 and the G6 cap cross-checks.
# All identifiers in this file are synthetic mock fixtures. No AWS client runs.
# Plan-only runs: never remove the mock_provider or change command to apply.
#
# Paths below are relative to the working directory of `terraform test`, which is infra/terraform (the root).
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_efs_file_system" { defaults = { arn = "arn:aws:elasticfilesystem:us-east-1:111122223333:file-system/fs-0123456789abcdef0", id = "fs-0123456789abcdef0" } }
  mock_resource "aws_efs_access_point" { defaults = { arn = "arn:aws:elasticfilesystem:us-east-1:111122223333:access-point/fsap-0123456789abcdef0", id = "fsap-0123456789abcdef0" } }
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-1:111122223333:key/00000000-0000-0000-0000-000000000001"
      key_id = "00000000-0000-0000-0000-000000000001"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::synthetic-phase12a-bucket", id = "synthetic-phase12a-bucket" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-1:111122223333:table/synthetic-phase12a-table" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-phase12a-queue"
      id  = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-phase12a-queue"
      url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-phase12a-queue"
    }
  }
  mock_resource "aws_sfn_state_machine" { defaults = { arn = "arn:aws:states:us-east-1:111122223333:stateMachine:scholarchain-course-embedding-dispatch" } }
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::111122223333:role/synthetic-phase12b-role" } }
  mock_resource "aws_s3vectors_vector_bucket" { defaults = { vector_bucket_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors" } }
  mock_resource "aws_neptune_cluster" { defaults = { cluster_resource_id = "cluster-synthetic-graph", endpoint = "synthetic.cluster.neptune.amazonaws.com", reader_endpoint = "synthetic.cluster-ro.neptune.amazonaws.com" } }
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-1:111122223333:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-1:111122223333:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-1:111122223333:repository/synthetic-phase12b-repo", repository_url = "111122223333.dkr.ecr.us-east-1.amazonaws.com/synthetic-phase12b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/synthetic/1234567890123456" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-1:111122223333:service/srv-synthetic" } }
  mock_resource "aws_vpc_endpoint" {
    defaults = { prefix_list_id = "pl-synthetic" }
  }
}
# Distinct IDs make resource-backed routing comparisons meaningful in mock plans.
override_resource {
  target          = module.network.aws_route_table.public
  override_during = plan
  values          = { id = "rtb-synthetic-public" }
}
override_resource {
  target          = module.network.aws_route_table.application
  override_during = plan
  values          = { id = "rtb-synthetic-application" }
}
override_resource {
  target          = module.network.aws_route_table.data
  override_during = plan
  values          = { id = "rtb-synthetic-data" }
}
variables {
  aws_account_id                   = "111122223333"
  aws_region                       = "us-east-1"
  aws_profile                      = "synthetic-not-a-real-profile"
  availability_zones               = ["us-east-1a", "us-east-1b"]
  deployment_trusted_principal_arn = "arn:aws:iam::111122223333:role/synthetic-architect"
  budget_limit_usd                 = 50 # Synthetic validation input, not the user's budget.
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["researcher-profile-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/researcher-profile-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-community-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/collaboration-community-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["paper-abstract-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/paper-abstract-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-path-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/collaboration-path-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["topic-institution-summary-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/topic-institution-summary-v1" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.embedding
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-work", url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-work", id = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-work" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.dead_letter
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:111122223333:synthetic-dlq", url = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-dlq", id = "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-dlq" }
}

run "emr_disabled_by_default_creates_nothing" {
  command = plan
  assert {
    condition     = output.phase12b_controls.emr.cluster == null && output.phase12b_controls.emr.efs == null && output.phase12b_controls.emr.efs_policy == null && output.phase12b_controls.emr.node_policy == null && output.phase12b_controls.emr.bootstrap_args == [] && length(output.phase12b_controls.emr.task_groups) == 0 && output.phase12b_controls.emr.scaling == null
    error_message = "Disabled EMR creates no cluster, EFS, instance-role policy, task group or scaling policy."
  }
}
run "main_emr_matches_decision_12_10" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.cluster.applications == toset(["Hadoop"]) && output.phase12b_controls.emr.cluster.release_label == "emr-7.8.0"
    error_message = "Decision 12-10: Hadoop only on emr-7.8.0, never the stock Spark 2.12 install."
  }
  assert {
    condition     = contains(output.phase12b_controls.emr.bootstrap_args, "789a9684f91527dfd9b97d56acce9dbfe5dd4c328299542245da92968f916de5") && output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--runtime-sha256") + 1] == regex("(?m)^RUNTIME_ARCHIVE_EXPECTED_SHA256=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]
    error_message = "G5: the bootstrap receives the pinned runtime archive sha256, equal to scripts/config/release.conf RUNTIME_ARCHIVE_EXPECTED_SHA256."
  }
  assert {
    condition     = output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--runtime-uri") + 1] == "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz" && output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--job-jar-uri") + 1] == "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar" && output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--job-jar-sha256") + 1] == "2222222222222222222222222222222222222222222222222222222222222222" && output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--self-sha256") + 1] == "1111111111111111111111111111111111111111111111111111111111111111"
    error_message = "G5/item 8: runtime, job jar and bootstrap references and hashes come from tfvars."
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.bootstrap_action).path == "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh" && one(output.phase12b_controls.emr.cluster.bootstrap_action).args == output.phase12b_controls.emr.bootstrap_args
    error_message = "The cluster runs the real bootstrap script at the tfvars URI with the rendered arguments."
  }
  assert {
    condition     = output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--max-minutes") + 1] == "240" && one(output.phase12b_controls.emr.cluster.auto_termination_policy).idle_timeout == 900
    error_message = "Defaults: 240-minute node deadline and a 900 s idle timeout."
  }
}
run "tls_is_disabled_and_at_rest_encryption_stays_on" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.EnableInTransitEncryption == false
    error_message = "13C decision: EMR in-transit TLS is disabled (untested with the custom runtime)."
  }
  assert {
    condition     = jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.EnableAtRestEncryption == true && jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.AtRestEncryptionConfiguration.S3EncryptionConfiguration.EncryptionMode == "SSE-KMS" && jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.AtRestEncryptionConfiguration.LocalDiskEncryptionConfiguration.EnableEbsEncryption == true
    error_message = "At-rest S3 SSE-KMS and local-disk/EBS encryption stay on."
  }
  assert {
    condition     = !can(jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.InTransitEncryptionConfiguration) && !strcontains(output.phase12b_controls.emr.security.configuration, "PEM") && !strcontains(output.phase12b_controls.emr.security.configuration, "TLSCertificate")
    error_message = "No PEM or TLS certificate configuration remains."
  }
  assert {
    condition     = output.phase12b_controls.emr.efs.encrypted == true
    error_message = "The EFS staging file system is encrypted at rest."
  }
}
run "spark_settings_rendered_by_the_module_equal_scripts_config_spark_12_10_conf" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = { for l in split("\n", output.phase12b_controls.emr.spark_defaults_text) : split(" ", l)[0] => join(" ", slice(split(" ", l), 1, length(split(" ", l)))) if l != "" } == { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }
    error_message = "The module renders EXACTLY the Spark settings in scripts/config/spark-12-10.conf (same keys, same values); a difference fails this test."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_nodes == 1 && length(keys({ for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") })) == 22 && alltrue([for k in keys({ for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }) : startswith(k, "spark.")])
    error_message = "The reviewed conf holds the 22 decision 12-10 settings (a drift in either file changes this count)."
  }
  assert {
    condition     = output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--spark-defaults-b64") + 1] == base64encode(output.phase12b_controls.emr.spark_defaults_text) && output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--spark-defaults-sha256") + 1] == sha256(output.phase12b_controls.emr.spark_defaults_text)
    error_message = "The bootstrap gets the rendered text and its sha256 (item 8)."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_nodes == 1 && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.yarn.jars"] == "local:/opt/scholarchain-runtime/jars/*" && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.yarn.populateHadoopClasspath"] == "false" && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.authenticate"] == "true" && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.network.crypto.authEngineVersion"] == "1" && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.io.encryption.enabled"] == "true" && { for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.dynamicAllocation.shuffleTracking.enabled"] == "true" && !strcontains(lower({ for l in split("\n", file("../../scripts/config/spark-12-10.conf")) : split(" ", trimspace(l))[0] => join(" ", slice(split(" ", trimspace(l)), 1, length(split(" ", trimspace(l))))) if trimspace(l) != "" && !startswith(trimspace(l), "#") }["spark.hadoop.io.compression.codecs"]), "lzo")
    error_message = "Decision 12-10 and G2 values in the reviewed conf: local runtime jars, no Hadoop classpath, authentication, AES-CTR engine 1, IO encryption, shuffle tracking, no LZO."
  }
  assert {
    condition     = !strcontains(output.phase12b_controls.emr.spark_defaults_text, "JAVA_HOME") && !strcontains(output.phase12b_controls.emr.spark_defaults_text, "stagingDir")
    error_message = "JAVA_HOME is resolved on each node by the bootstrap and never rendered by Terraform."
  }
}
run "node_paths_equal_the_pinned_release_conf_paths" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.node_paths.runtime_dir == regex("(?m)^PIPELINE_RUNTIME_DIR=([^\\n]*)$", file("../../scripts/config/release.conf"))[0] && output.phase12b_controls.emr.node_paths.job_jar_path == regex("(?m)^PIPELINE_JOB_JAR_PATH=([^\\n]*)$", file("../../scripts/config/release.conf"))[0] && output.phase12b_controls.emr.node_paths.java_home_file == regex("(?m)^PIPELINE_JAVA_HOME_FILE=([^\\n]*)$", file("../../scripts/config/release.conf"))[0] && output.phase12b_controls.emr.node_paths.efs_mount == regex("(?m)^PIPELINE_EFS_MOUNT=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]
    error_message = "The module paths equal the paths scripts/config/release.conf pins and the pipeline steps read."
  }
}
run "efs_staging_is_ported_and_scoped" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.efs.encrypted == true && output.phase12b_controls.emr.efs.performance_mode == "generalPurpose" && output.phase12b_controls.emr.efs.throughput_mode == "elastic" && output.phase12b_controls.emr.efs_backup.backup_policy[0].status == "DISABLED"
    error_message = "EFS: encrypted, elastic, backups explicitly disabled."
  }
  assert {
    condition     = output.phase12b_controls.emr.efs_ingress_rule.from_port == 2049 && output.phase12b_controls.emr.efs_ingress_rule.to_port == 2049 && output.phase12b_controls.emr.efs_ingress_rule.ip_protocol == "tcp" && output.phase12b_controls.emr.efs_ingress_rule.cidr_ipv4 == null && output.phase12b_controls.emr.efs_ingress_rule.cidr_ipv6 == null && output.phase12b_controls.emr.efs_ingress_rule.prefix_list_id == null
    error_message = "EFS: NFS 2049 only from a referenced security group, never a CIDR."
  }
  assert {
    condition     = output.phase12b_controls.emr.efs_egress_rule.from_port == 2049 && output.phase12b_controls.emr.efs_egress_rule.to_port == 2049 && output.phase12b_controls.emr.efs_egress_rule.cidr_ipv4 == null
    error_message = "The EMR group gets an NFS-only egress rule to the EFS group."
  }
  assert {
    condition     = one(output.phase12b_controls.emr.efs_access_point.posix_user).uid == 1500 && one(output.phase12b_controls.emr.efs_access_point.posix_user).gid == 1500 && one(output.phase12b_controls.emr.efs_access_point.root_directory).path == "/scholarchain-emr" && one(one(output.phase12b_controls.emr.efs_access_point.root_directory).creation_info).permissions == "0750"
    error_message = "The access point fixes the POSIX identity and a scoped root directory."
  }
  assert {
    condition     = length(jsondecode(output.phase12b_controls.emr.efs_policy).Statement) == 2 && jsondecode(output.phase12b_controls.emr.efs_policy).Statement[0].Effect == "Deny" && jsondecode(output.phase12b_controls.emr.efs_policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false" && jsondecode(output.phase12b_controls.emr.efs_policy).Statement[1].Action == ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"] && can(jsondecode(output.phase12b_controls.emr.efs_policy).Statement[1].Condition.StringEquals["elasticfilesystem:AccessPointArn"])
    error_message = "EFS policy: deny non-TLS; the instance role may mount and write only through the access point."
  }
  assert {
    condition     = length(output.phase12b_controls.emr.efs_mount_target.security_groups) == 1
    error_message = "One mount target on the EFS security group only."
  }
}
run "instance_role_policy_is_scoped_to_the_access_point_and_the_stack_tag" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = length(jsondecode(output.phase12b_controls.emr.node_policy).Statement) == 2 && jsondecode(output.phase12b_controls.emr.node_policy).Statement[0].Action == ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"] && can(jsondecode(output.phase12b_controls.emr.node_policy).Statement[0].Condition.StringEquals["elasticfilesystem:AccessPointArn"])
    error_message = "Instance role: EFS client only through the access point."
  }
  assert {
    condition     = toset(jsondecode(output.phase12b_controls.emr.node_policy).Statement[1].Action) == toset(["elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy"]) && jsondecode(output.phase12b_controls.emr.node_policy).Statement[1].Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "main-emr"
    error_message = "Instance role: auto-termination actions only on clusters that carry the stack tag (carried item 17, main-module side)."
  }
}
run "the_stack_tag_propagates_from_the_cluster" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.cluster.tags["scholarchain:stack"] == "main-emr" && output.phase12b_controls.emr.cluster.tags["for-use-with-amazon-emr-managed-policies"] == "true"
    error_message = "Carried item 17: the stack tag is on the cluster so EMR propagates it to the instances and ENIs the boundary names."
  }
}
run "task_nodes_and_managed_scaling_default_to_off" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = length(output.phase12b_controls.emr.task_groups) == 0 && output.phase12b_controls.emr.scaling == null
    error_message = "G3: no task group and no managed scaling unless tfvars turn them on."
  }
}
run "task_nodes_and_managed_scaling_are_enabled_only_by_tfvars_within_the_caps" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }], max_task_nodes = 1, task_node_count = 0, managed_scaling_enabled = true, managed_scaling_max_capacity = 2 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = length(output.phase12b_controls.emr.task_groups) == 1 && alltrue([for k, g in output.phase12b_controls.emr.task_groups : g.instance_count == 0])
    error_message = "G3: a task group exists at count 0 when tfvars allow one task node."
  }
  assert {
    condition     = one(output.phase12b_controls.emr.scaling.compute_limits).minimum_capacity_units == 1 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_capacity_units == 2 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_core_capacity_units == 1 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_ondemand_capacity_units == 2 && one(output.phase12b_controls.emr.scaling.compute_limits).unit_type == "Instances"
    error_message = "G3: managed scaling is capped at core + one task node."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.max_instances == 3
    error_message = "Capacity caps: one primary, one core, one task node."
  }
}
run "task_node_group_pins_gp3_iops_and_size_like_the_core_groups" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }], max_task_nodes = 1 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  # Follow-up defect 2: the task group pins gp3, 32 GiB and 3000 IOPS exactly like the master and core groups. The provider has no
  # throughput argument on aws_emr_instance_group (see modules/emr/main.tf), so throughput is pinned only on the cluster groups.
  assert {
    condition     = length(output.phase12b_controls.emr.task_groups) == 1 && alltrue([for k, g in output.phase12b_controls.emr.task_groups : length(g.ebs_config) == 1 && one(g.ebs_config).type == "gp3" && one(g.ebs_config).size == 32 && one(g.ebs_config).iops == 3000 && one(g.ebs_config).volumes_per_instance == 1])
    error_message = "The task instance group must pin gp3, 32 GiB, 3000 IOPS and one volume per instance like the core group."
  }
  assert {
    condition     = one(one(output.phase12b_controls.emr.cluster.core_instance_group).ebs_config).throughput == 125 && one(one(output.phase12b_controls.emr.cluster.master_instance_group).ebs_config).throughput == 125 && one(one(output.phase12b_controls.emr.cluster.core_instance_group).ebs_config).iops == 3000
    error_message = "The primary and core groups pin gp3 throughput 125 and 3000 IOPS."
  }
}
run "terraform_caps_stay_inside_the_g6_per_run_cap_under_the_pinned_rates" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }], max_task_nodes = 1 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.max_instances == 3 && output.phase12b_controls.emr.caps.max_instances <= tonumber(regex("(?m)^PIPELINE_MAX_CAPACITY=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "The largest cluster Terraform permits (3 instances) is within the script capacity cap."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_nodes == 1 && 3 * (tonumber(regex("(?m)^EMR_RATE_EC2_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) * (tonumber(regex("(?m)^PIPELINE_MAX_RUNTIME_MINUTES=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) * 60 + tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])) / 3600 <= tonumber(regex("(?m)^EMR_MAX_RUN_USD=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "The largest permitted cluster costs (instances x rate x (max runtime + idle)) no more than EMR_MAX_RUN_USD per run under the pinned rates."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.idle_timeout_seconds <= tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) && one(output.phase12b_controls.emr.cluster.auto_termination_policy).idle_timeout <= tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "The cluster idle timeout never exceeds the script idle cap."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_nodes == 1 && 4 * (tonumber(regex("(?m)^EMR_RATE_EC2_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) * (tonumber(regex("(?m)^PIPELINE_MAX_RUNTIME_MINUTES=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) * 60 + tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])) / 3600 > tonumber(regex("(?m)^EMR_MAX_RUN_USD=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "A fourth instance WOULD exceed the per-run cap, so the Terraform bound of one task node is the tightest permitted (this fails if rates or caps change: re-derive the Terraform bound)."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_nodes == 1 && 2 * (tonumber(regex("(?m)^EMR_RATE_EC2_M5_2XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_2XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) * (tonumber(regex("(?m)^PIPELINE_MAX_RUNTIME_MINUTES=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) * 60 + tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])) / 3600 > tonumber(regex("(?m)^EMR_MAX_RUN_USD=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "Even the smallest m5.2xlarge cluster exceeds the per-run cap, so Terraform allows only m5.xlarge."
  }
}
run "two_task_nodes_exceed_the_g6_cap_and_are_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", max_task_nodes = 2 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "m5_2xlarge_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", instance_type = "m5.2xlarge" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "release_label_other_than_emr_7_8_0_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", release_label = "emr-7.9.0" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "idle_timeout_above_900_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", idle_timeout_seconds = 901 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "the_former_3600_idle_timeout_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", idle_timeout_seconds = 3600 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "idle_timeout_below_60_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", idle_timeout_seconds = 59 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "managed_scaling_without_task_nodes_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", managed_scaling_enabled = true }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "managed_scaling_capacity_above_core_plus_task_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", max_task_nodes = 1, managed_scaling_enabled = true, managed_scaling_max_capacity = 3 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "task_node_count_above_the_cap_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", max_task_nodes = 1, task_node_count = 2 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "a_malformed_sha256_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", job_jar_sha256 = "XYZ" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "a_non_s3_artifact_uri_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", job_jar_uri = "https://example.invalid/job.jar" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "an_extra_artifact_outside_the_allowed_directories_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [{ uri = "s3://scholarchain-course-111122223333-artifacts/x.sh", sha256 = "3333333333333333333333333333333333333333333333333333333333333333", dest = "/etc/cron.d/x" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "a_node_deadline_above_240_minutes_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", node_deadline_minutes = 241 }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
run "an_artifact_outside_the_project_artifacts_bucket_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://some-other-bucket/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "emr_requires_the_runtime_archive_and_job_jar_references" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

# ---- carried item 16, main-module side: the EMR roles trust only their service principals -----------------------------------
run "main_emr_roles_trust_only_their_service_principals" {
  command = plan
  assert {
    condition     = length(jsondecode(output.iam_controls.emr_service_trust).Statement) == 1 && jsondecode(output.iam_controls.emr_service_trust).Statement[0].Principal == { Service = "elasticmapreduce.amazonaws.com" } && jsondecode(output.iam_controls.emr_service_trust).Statement[0].Condition.StringEquals["aws:SourceAccount"] == "111122223333"
    error_message = "Item 16: the main EMR service role trusts only the EMR service principal for this account."
  }
  assert {
    condition     = length(jsondecode(output.iam_controls.emr_ec2_trust).Statement) == 1 && jsondecode(output.iam_controls.emr_ec2_trust).Statement[0].Principal == { Service = "ec2.amazonaws.com" }
    error_message = "Item 16: the main EMR instance role trusts only the EC2 service principal."
  }
  assert {
    condition     = alltrue([for t in [output.iam_controls.emr_service_trust, output.iam_controls.emr_ec2_trust] : !strcontains(t, "\"AWS\"") && !strcontains(t, "Federated")])
    error_message = "Item 16: no AWS or federated principal in either main EMR trust policy."
  }
}

# ---- carried item 5, main-module side (N9): CreateGrant on the project CMK only for AWS-service grants -----------------------
run "main_emr_service_role_create_grant_is_conditioned_on_aws_resources" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = alltrue([for st in jsondecode(output.iam_controls.emr_disk_encryption.policy).Statement : !contains(st.Action, "kms:CreateGrant") || try(st.Condition.Bool["kms:GrantIsForAWSResource"], "false") == "true"]) && anytrue([for st in jsondecode(output.iam_controls.emr_disk_encryption.policy).Statement : contains(st.Action, "kms:CreateGrant")])
    error_message = "Item 5 (N9): every kms:CreateGrant the main EMR service role holds carries kms:GrantIsForAWSResource = true."
  }
}

# ---- 13C repair round 1, finding C1: the EMR step programs are pinned artifacts ------------------------------------------------
run "emr_step_programs_are_pinned_artifacts_in_the_release_conf_directory" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = jsondecode(file("emr-step-programs.json")).bin_dir == regex("(?m)^PIPELINE_STEP_BIN_DIR=([^\\n]*)$", file("../../scripts/config/release.conf"))[0] && output.phase12b_controls.emr.node_paths.step_bin_dir == regex("(?m)^PIPELINE_STEP_BIN_DIR=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]
    error_message = "Finding C1: the Terraform manifest and the module install the step programs in the directory scripts/config/release.conf pins (PIPELINE_STEP_BIN_DIR), which the EMR step launcher runs from."
  }
  assert {
    condition     = length(output.phase12b_controls.emr.bootstrap_args) > 0 && alltrue([for n, s in jsondecode(file("emr-step-programs.json")).programs : s == filesha256("../../scripts/emr/${n}")]) && length(jsondecode(file("emr-step-programs.json")).programs) == 4 && toset(keys(jsondecode(file("emr-step-programs.json")).programs)) == toset(["sc-step.sh", "sc-ceiling-check.py", "sc-class-origin-verify.py", "sc-render-spark-config.py"])
    error_message = "Finding C1: infra/terraform/emr-step-programs.json holds exactly the sha256 of the four files under scripts/emr/ (regenerate it with: python3 -I scripts/lib/pipeline.py step-manifest --write)."
  }
  assert {
    condition     = alltrue([for n, s in jsondecode(file("emr-step-programs.json")).programs : contains(output.phase12b_controls.emr.bootstrap_args, "s3://scholarchain-course-111122223333-artifacts/steps/${n},${s},${jsondecode(file("emr-step-programs.json")).bin_dir}/${n}")]) && length([for a in output.phase12b_controls.emr.bootstrap_args : a if a == "--artifact"]) == 4
    error_message = "Finding C1: the bootstrap action installs each step program as a sha256-pinned --artifact (uri,sha256,dest) in the pinned directory."
  }
  assert {
    condition     = length(output.phase12b_controls.emr.bootstrap_args) > 0 && alltrue([for n, s in jsondecode(file("emr-step-programs.json")).programs : can(regex("^[0-9a-f]{64}$", s))])
    error_message = "Every pinned step program hash is 64 lowercase hex."
  }
}
run "emr_without_the_step_programs_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "a_step_program_with_a_stale_sha256_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = n == "sc-step.sh" ? "3333333333333333333333333333333333333333333333333333333333333333" : s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "a_step_program_installed_in_the_wrong_directory_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = n == "sc-step.sh" ? "/opt/scholarchain-runtime/${n}" : "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "a_missing_step_program_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" } if n != "sc-class-origin-verify.py"] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "a_step_program_listed_twice_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = concat([for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }], [{ uri = "s3://scholarchain-course-111122223333-artifacts/steps/again.sh", sha256 = jsondecode(file("emr-step-programs.json")).programs["sc-step.sh"], dest = "/opt/scholarchain-spike/bin/sc-step.sh" }]) }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

# ---- carried finding C2: the runtime archive hash must equal the decision 12-10 pin ---------------------------------------------
run "the_runtime_archive_sha256_must_equal_the_decision_12_10_pin" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.bootstrap_args[index(output.phase12b_controls.emr.bootstrap_args, "--runtime-sha256") + 1] == regex("(?m)^RUNTIME_ARCHIVE_EXPECTED_SHA256=([^\\n]*)$", file("../../scripts/config/release.conf"))[0] && var.emr_config.runtime_archive_sha256 == regex("(?m)^RUNTIME_ARCHIVE_EXPECTED_SHA256=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]
    error_message = "C2: the runtime archive sha256 in effect equals the decision 12-10 pin in scripts/config/release.conf."
  }
}
run "a_different_runtime_archive_sha256_is_rejected" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", runtime_archive_sha256 = "4444444444444444444444444444444444444444444444444444444444444444", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [var.emr_config]
}
