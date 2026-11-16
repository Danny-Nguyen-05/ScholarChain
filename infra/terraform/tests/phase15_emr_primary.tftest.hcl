# Phase 15 D3: a separate EMR PRIMARY (master) instance type. Human decision, docs/agent-runs/phase-15/prompt.md ("D3 decision" and
# "S run cap and D3 go-ahead", 2026-11-16): "Use r5.xlarge for the primary node only ... Go ahead: r5.xlarge primary, ER heap 12g, S run
# cap 75 min". The entity-resolution step is a single JVM on the PRIMARY node (scripts/emr/sc-step.sh); P6 measured RSS 13.9 GB at
# -Xmx12g, so the 16 GiB m5.xlarge primary is replaced by the 32 GiB r5.xlarge (same 4 vCPU). Spark executors run on the core node,
# which stays m5.xlarge. Exactly the reviewed pair is allowed: primary in {m5.xlarge, r5.xlarge}, core (and task) m5.xlarge.
# Rates (coordinator, public AWS price lists read 2026-11-16, us-east-2): r5.xlarge 0.252 EC2 + 0.063 EMR, m5.xlarge 0.192 + 0.048
# (scripts/config/emr-pricing.conf); r5.xlarge is supported from emr-7.0.0, so it runs on the pinned emr-7.8.0.
# All identifiers are synthetic (the account id is assembled from parts, so no 12-digit literal is stored in this file).
# Plan-only: never remove the mock_provider or run apply.

mock_provider "aws" {
  override_during = plan
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-1:aws:key/00000000-0000-0000-0000-00000000000a"
      key_id = "00000000-0000-0000-0000-00000000000a"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::synthetic-phase12a-bucket", id = "synthetic-phase12a-bucket" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-1:aws:table/synthetic-phase12a-table" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-1:aws:synthetic-phase12a-queue"
      id  = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-phase12a-queue"
      url = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-phase12a-queue"
    }
  }
  mock_resource "aws_sfn_state_machine" { defaults = { arn = "arn:aws:states:us-east-1:aws:stateMachine:scholarchain-course-embedding-dispatch" } }
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::aws:role/synthetic-phase12b-role" } }
  mock_resource "aws_s3vectors_vector_bucket" { defaults = { vector_bucket_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors" } }
  mock_resource "aws_neptune_cluster" { defaults = { cluster_resource_id = "cluster-synthetic-graph", endpoint = "synthetic.cluster.neptune.amazonaws.com", reader_endpoint = "synthetic.cluster-ro.neptune.amazonaws.com" } }
  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:us-east-1:aws:certificate/00000000-0000-0000-0000-0000000000a1"
      domain_validation_options = [{
        domain_name           = "api.example.invalid"
        resource_record_name  = "_0123456789abcdef.api.example.invalid."
        resource_record_type  = "CNAME"
        resource_record_value = "_fedcba9876543210.acm-validations.invalid."
      }]
    }
  }
  mock_resource "aws_secretsmanager_secret" { defaults = { arn = "arn:aws:secretsmanager:us-east-1:aws:secret:synthetic-provider-secret-AbCdEf" } }
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-1:aws:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-1:aws:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-1:aws:repository/synthetic-phase12b-repo", repository_url = "synthetic-account.dkr.ecr.us-east-1.amazonaws.com/synthetic-phase12b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:aws:loadbalancer/app/synthetic/abcdef0123456789" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:aws:targetgroup/synthetic/abcdef0123456789" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-1:aws:service/srv-synthetic" } }
  mock_resource "aws_vpc_endpoint" {
    defaults = { prefix_list_id = "pl-synthetic" }
  }
}
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
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["researcher-profile-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors/index/researcher-profile-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-community-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors/index/collaboration-community-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["paper-abstract-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors/index/paper-abstract-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-path-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors/index/collaboration-path-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["topic-institution-summary-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-1:aws:bucket/synthetic-vectors/index/topic-institution-summary-v1" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.embedding
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:aws:synthetic-work", url = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-work", id = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-work" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.dead_letter
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-1:aws:synthetic-dlq", url = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-dlq", id = "https://sqs.us-east-1.amazonaws.com/synthetic-account/synthetic-dlq" }
}
override_resource {
  target          = module.identity.aws_iam_role.execution["graph-service"]
  override_during = plan
  values          = { arn = "arn:aws:iam::aws:role/synthetic-graph-service-execution" }
}
override_resource {
  target          = module.network.aws_subnet.application["0"]
  override_during = plan
  values          = { id = "subnet-synthetic-app-0" }
}
override_resource {
  target          = module.network.aws_subnet.application["1"]
  override_during = plan
  values          = { id = "subnet-synthetic-app-1" }
}
override_resource {
  target          = module.network.aws_security_group.role["graph-service"]
  override_during = plan
  values          = { id = "sg-synthetic-graph-service" }
}
override_resource {
  target          = module.identity.aws_iam_role.neptune_tunnel_task[0]
  override_during = plan
  values          = { arn = "arn:aws:iam::aws:role/synthetic-neptune-tunnel-task" }
}
variables {
  aws_account_id                   = join("", ["1111", "2222", "3333"])
  aws_region                       = "us-east-1"
  aws_profile                      = "synthetic-not-a-real-profile"
  availability_zones               = ["us-east-1a", "us-east-1b"]
  deployment_trusted_principal_arn = "arn:aws:iam::${join("", ["1111", "2222", "3333"])}:role/synthetic-architect"
  budget_limit_usd                 = 50 # Synthetic validation input, not the user's budget.
  emr_service_policy_json          = replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", "us-east-1"), "<12-digit-account-id>", join("", ["1111", "2222", "3333"])), "<environment>", "course")
}

run "emr_disabled_with_the_default_primary_type_validates_and_creates_no_cluster" {
  command = plan
  assert {
    condition     = output.phase12b_controls.emr.cluster == null && output.phase12b_controls.emr.caps.primary_instance_type == "r5.xlarge" && output.phase12b_controls.emr.caps.instance_type == "m5.xlarge"
    error_message = "D3: with EMR off nothing is created, and the defaults are primary r5.xlarge, core m5.xlarge."
  }
}

run "default_plan_shows_an_r5_xlarge_primary_and_an_m5_xlarge_core" {
  command = plan
  variables {
    emr_config = {
      enabled             = true
      runtime_reference   = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified    = true
      bootstrap_uri       = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256    = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256      = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts     = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
    }
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.master_instance_group).instance_type == "r5.xlarge" && one(output.phase12b_controls.emr.cluster.master_instance_group).instance_count == 1
    error_message = "D3: the plan's master (primary) group is one r5.xlarge by default."
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.core_instance_group).instance_type == "m5.xlarge" && one(output.phase12b_controls.emr.cluster.core_instance_group).instance_count == 1
    error_message = "D3: the core group stays one m5.xlarge (Spark executors run on core)."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_instance_type == "r5.xlarge" && output.phase12b_controls.emr.caps.instance_type == "m5.xlarge" && output.phase12b_controls.emr.cluster.release_label == "emr-7.8.0"
    error_message = "D3: the caps expose primary r5.xlarge and core m5.xlarge on the pinned emr-7.8.0 (r5.xlarge needs emr-7.0.0 or later)."
  }
  assert {
    condition     = one(one(output.phase12b_controls.emr.cluster.master_instance_group).ebs_config).size == one(one(output.phase12b_controls.emr.cluster.core_instance_group).ebs_config).size && one(one(output.phase12b_controls.emr.cluster.master_instance_group).ebs_config).type == "gp3"
    error_message = "D3 changes only the primary instance type: EBS stays gp3 and equal to the core group."
  }
}

run "an_explicit_r5_xlarge_primary_is_accepted" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "r5.xlarge"
      instance_type         = "m5.xlarge"
    }
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.master_instance_group).instance_type == "r5.xlarge" && one(output.phase12b_controls.emr.cluster.core_instance_group).instance_type == "m5.xlarge"
    error_message = "D3: primary r5.xlarge with core m5.xlarge is the reviewed pair."
  }
}

run "an_m5_xlarge_primary_is_still_accepted" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "m5.xlarge"
    }
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.master_instance_group).instance_type == "m5.xlarge" && one(output.phase12b_controls.emr.cluster.core_instance_group).instance_type == "m5.xlarge"
    error_message = "D3: the earlier all-m5.xlarge cluster stays expressible (primary m5.xlarge, core m5.xlarge)."
  }
}

run "a_task_node_uses_the_core_type_not_the_primary_type" {
  command = plan
  variables {
    emr_config = {
      enabled             = true
      runtime_reference   = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified    = true
      bootstrap_uri       = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256    = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256      = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts     = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      max_task_nodes      = 1
      task_node_count     = 1
    }
  }
  assert {
    condition     = length(output.phase12b_controls.emr.task_groups) == 1 && output.phase12b_controls.emr.task_groups[0].instance_type == "m5.xlarge" && one(output.phase12b_controls.emr.cluster.master_instance_group).instance_type == "r5.xlarge"
    error_message = "D3: only the primary is r5.xlarge; a task node uses the core type m5.xlarge."
  }
}

run "the_largest_cluster_with_an_r5_primary_stays_inside_the_g6_per_run_cap" {
  command = plan
  variables {
    emr_config = {
      enabled             = true
      runtime_reference   = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified    = true
      bootstrap_uri       = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256    = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256      = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts     = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      max_task_nodes      = 1
    }
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.max_instances == 3 && ((tonumber(regex("(?m)^EMR_RATE_EC2_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) + 2 * (tonumber(regex("(?m)^EMR_RATE_EC2_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]))) * (tonumber(regex("(?m)^PIPELINE_MAX_RUNTIME_MINUTES=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) * 60 + tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])) / 3600 <= tonumber(regex("(?m)^EMR_MAX_RUN_USD=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "G6: r5.xlarge primary + m5.xlarge core + one m5.xlarge task, at PIPELINE_MAX_RUNTIME_MINUTES plus the idle tail, costs at most EMR_MAX_RUN_USD (0.795 x 3.25 = 2.58375, USD 2.59 rounded up, <= 3)."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_instance_type == "r5.xlarge" && ((tonumber(regex("(?m)^EMR_RATE_EC2_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) + 3 * (tonumber(regex("(?m)^EMR_RATE_EC2_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]))) * (tonumber(regex("(?m)^PIPELINE_MAX_RUNTIME_MINUTES=([^\\n]*)$", file("../../scripts/config/release.conf"))[0]) * 60 + tonumber(regex("(?m)^PIPELINE_MAX_IDLE_TIMEOUT_SECONDS=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])) / 3600 > tonumber(regex("(?m)^EMR_MAX_RUN_USD=([^\\n]*)$", file("../../scripts/config/release.conf"))[0])
    error_message = "G6: a fourth instance (second task node) would exceed the per-run cap even with the r5 primary (1.035 x 3.25 = 3.36375, USD 3.37 rounded up, > 3), so the one-task-node bound stays the tightest."
  }
  assert {
    condition     = output.phase12b_controls.emr.caps.primary_instance_type == "r5.xlarge" && (tonumber(regex("(?m)^EMR_RATE_EC2_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_R5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) == 0.315 && (tonumber(regex("(?m)^EMR_RATE_EC2_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0]) + tonumber(regex("(?m)^EMR_RATE_EMR_M5_XLARGE=([^\\n]*)$", file("../../scripts/config/emr-pricing.conf"))[0])) == 0.24
    error_message = "The reviewed hourly rates (prompt.md coordinator check, 2026-11-16): r5.xlarge 0.252 + 0.063 = 0.315 and m5.xlarge 0.192 + 0.048 = 0.240 USD per hour."
  }
}

run "an_r5_2xlarge_primary_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "r5.2xlarge"
    }
  }
  expect_failures = [var.emr_config]
}

run "an_m5_2xlarge_primary_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "m5.2xlarge"
    }
  }
  expect_failures = [var.emr_config]
}

run "an_r6i_xlarge_primary_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "r6i.xlarge"
    }
  }
  expect_failures = [var.emr_config]
}

run "an_upper_case_primary_type_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "R5.XLARGE"
    }
  }
  expect_failures = [var.emr_config]
}

run "an_r5_xlarge_core_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled             = true
      runtime_reference   = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified    = true
      bootstrap_uri       = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256    = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256      = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts     = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      instance_type       = "r5.xlarge"
    }
  }
  expect_failures = [var.emr_config]
}

run "an_r5_xlarge_core_with_an_r5_primary_is_refused" {
  command = plan
  variables {
    emr_config = {
      enabled               = true
      runtime_reference     = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified      = true
      bootstrap_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256      = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri   = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256        = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts       = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
      primary_instance_type = "r5.xlarge"
      instance_type         = "r5.xlarge"
    }
  }
  expect_failures = [var.emr_config]
}
