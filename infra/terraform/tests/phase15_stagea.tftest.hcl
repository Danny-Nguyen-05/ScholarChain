# Phase 15 P7 (a) and (b): the Session 2 stage-a variable set and the offline derivation of the three base plans the session makes.
#   stage-a base       : S3, DynamoDB, vectors, network, identity, the API certificate; NO Neptune, NO ECS service, NO ALB, NO EMR
#                        (runbook session-2-plan section 5.2 step 1: neptune_enabled, runtime_enabled, emr_config.enabled and
#                        dashboard_enabled false, api_domain_name set);
#   stage-a EMR enable : the same plus emr_config enabled (section 5.2 step 4; applied with base-apply --skip-runtime-archive);
#   R-b base           : neptune_enabled true and emr_config.enabled false (section 5.3 step 1): Neptune creates plus module.emr deletes.
# Three plan-only runs. Terraform cannot plan against a state offline, so each incremental plan is the difference between
# consecutive full plans (scripts/lib/plan_deltas.py derive --set stagea), reviewed into scripts/config/expected-plan-deltas.json.
# The assertions pin what may and may not differ between the runs. P34 (neptune_max_ncu = 1) is not modelled: the committed guard
# still pins 2.5, so the R-b run uses the default; P34 changes Neptune attributes, not addresses.
# All identifiers are synthetic (the account id is assembled in the variables block, so no 12-digit literal is stored in this file).
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
  runtime_enabled                  = false
  runtime_composition_verified     = false
  neptune_enabled                  = false
  neptune_engine_version           = "1.4.6.3"
  neptune_parameter_family         = "neptune1.4"
  api_domain_name                  = "api.example.invalid"
  container_insights_enabled       = false
  dashboard_enabled                = false
  emr_service_policy_json          = replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", "us-east-1"), "<12-digit-account-id>", join("", ["1111", "2222", "3333"])), "<environment>", "course")
  emr_config = {
    enabled                 = false
    release_label           = "emr-7.8.0"
    max_task_nodes          = 0
    task_node_count         = 0
    managed_scaling_enabled = false
    idle_timeout_seconds    = 900
  }
}

# ---- plan 1: stage-a base (first apply of Session 2) --------------------------------------------------------------------------

run "stagea_1_base_has_no_neptune_runtime_alb_or_emr" {
  command = plan
  assert {
    condition     = output.phase12b_controls.neptune.enabled == false && output.phase12b_controls.neptune.cluster == null && output.phase12b_controls.neptune.instance == null
    error_message = "Stage a: no Neptune cluster or instance."
  }
  assert {
    condition     = length(output.phase12b_controls.runtime.services) == 0 && length(output.phase12b_controls.runtime.task_definitions) == 0 && length(output.phase12b_controls.runtime.load_balancers) == 0 && length(output.phase12b_controls.runtime.listeners) == 0 && length(output.phase12b_controls.runtime.target_groups) == 0
    error_message = "Stage a: no ECS service, task definition, load balancer, target group or listener."
  }
  assert {
    condition     = output.phase12b_controls.emr.enabled == false && output.phase12b_controls.emr.cluster == null && output.phase12b_controls.emr.efs == null && output.phase12b_controls.emr.efs_mount_target == null
    error_message = "Stage a base: no EMR cluster and no EFS staging."
  }
  assert {
    condition     = output.phase12b_controls.observability.dashboard == null
    error_message = "Stage a: dashboard_enabled = false creates no dashboard."
  }
  assert {
    condition     = length(output.phase14b_controls.certificates) == 1 && output.phase14b_controls.certificates[0].domain_name == "api.example.invalid" && length(output.phase14b_controls.validations) == 0 && output.phase14b_controls.runtime_deployed == false
    error_message = "Stage a requests the API certificate (so it validates before R-b) but does not wait for its validation."
  }
  assert {
    condition     = output.iam_controls.emr_control_policy == null
    error_message = "Stage a base: the EMR control-plane policy exists only with EMR enabled."
  }
}

# ---- plan 2: stage-a EMR enable (second apply; base-apply --skip-runtime-archive) ---------------------------------------------

run "stagea_2_emr_enable_adds_only_the_emr_resources" {
  command = plan
  variables {
    emr_config = {
      enabled                 = true
      release_label           = "emr-7.8.0"
      max_task_nodes          = 0
      task_node_count         = 0
      managed_scaling_enabled = false
      idle_timeout_seconds    = 900
      runtime_reference       = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified        = true
      bootstrap_uri           = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/bin/bootstrap.sh"
      bootstrap_sha256        = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri     = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/runtime/scholarchain-runtime.tgz"
      job_jar_uri             = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/jars/spark-job.jar"
      job_jar_sha256          = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts         = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261118/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
    }
  }
  assert {
    condition     = output.phase12b_controls.emr.enabled == true && output.phase12b_controls.emr.cluster != null && output.phase12b_controls.emr.efs != null && output.phase12b_controls.emr.efs_mount_target != null && output.phase12b_controls.emr.security != null
    error_message = "With emr_config.enabled the cluster, the EFS stack and its mount target are planned."
  }
  assert {
    condition     = output.phase12b_controls.neptune.cluster == null && length(output.phase12b_controls.runtime.services) == 0 && length(output.phase12b_controls.runtime.load_balancers) == 0
    error_message = "Enabling EMR in stage a creates no Neptune, ECS service or ALB."
  }
  assert {
    condition = (jsonencode(output.iam_controls.task_policies) == jsonencode(run.stagea_1_base_has_no_neptune_runtime_alb_or_emr.iam_controls.task_policies)
      && jsonencode(output.iam_controls.execution_policies) == jsonencode(run.stagea_1_base_has_no_neptune_runtime_alb_or_emr.iam_controls.execution_policies)
    && output.iam_controls.loader_policy == run.stagea_1_base_has_no_neptune_runtime_alb_or_emr.iam_controls.loader_policy)
    error_message = "Enabling EMR changes no runtime or loader role policy document (only the two EMR inline policies are added)."
  }
  assert {
    condition     = output.iam_controls.emr_control_policy != null
    error_message = "The EMR control-plane policy is added with EMR."
  }
}

# ---- plan 3: R-b base (Neptune on, EMR off) -----------------------------------------------------------------------------------

run "stagea_3_rb_base_adds_neptune_and_drops_emr" {
  command = plan
  variables {
    neptune_enabled = true
  }
  assert {
    condition     = output.phase12b_controls.neptune.enabled == true && output.phase12b_controls.neptune.cluster != null && output.phase12b_controls.neptune.instance != null
    error_message = "R-b base: the Neptune cluster and writer instance are planned."
  }
  assert {
    condition     = output.phase12b_controls.emr.enabled == false && output.phase12b_controls.emr.cluster == null && output.phase12b_controls.emr.efs == null && output.phase12b_controls.emr.efs_mount_target == null && output.iam_controls.emr_control_policy == null
    error_message = "R-b base: emr_config.enabled = false removes every module.emr resource and the two EMR inline policies (the plan deletes them)."
  }
  assert {
    condition     = length(output.phase12b_controls.runtime.services) == 0 && length(output.phase12b_controls.runtime.load_balancers) == 0 && length(output.phase14b_controls.validations) == 0
    error_message = "R-b base is still a base plan: no ECS service, ALB or certificate validation (those come with runtime-apply)."
  }
}
