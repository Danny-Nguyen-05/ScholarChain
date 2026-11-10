# Phase 14B replan under the USD 25 course cap (W1, Terraform shape): ECS Container Insights switch, CloudWatch dashboard switch and
# the 0.25 vCPU Fargate shape, all through the ROOT variables container_insights_enabled, dashboard_enabled and service_capacity.
# Defaults keep the earlier behavior (insights on, dashboard on, 512/1024); the cheap values come from the private tfvars.
# Every expectation is hand-derived:
#  - ECS cluster setting containerInsights is "enabled" (true) or "disabled" (false) (ECS CreateCluster setting values);
#  - the worker backlog policy divides SQS depth by ECS/ContainerInsights RunningTaskCount, a metric that exists only with Container
#    Insights, so it has count 1 only when runtime is enabled with an image revision AND insights is on; the three HTTP CPU policies use the
#    free predefined ECSServiceAverageCPUUtilization metric: always 3 (query-api, graph-service, semantic-service), target 60;
#  - the dashboard resource has count 1 or 0, so the dashboard output is a string or null; alarms and log groups do not depend on it:
#    log groups 4 (one per service), latency alarms 2 (query-api, graph-service), 1 queue alarm (threshold 300 s), 1 error alarm (5 percent);
#  - Fargate pairs: cpu 256 allows 512/1024/2048 MiB, 512 allows 1024-4096, 1024 allows 2048-8192; the variable additionally limits memory to
#    1024 or 2048 and requires memory >= 2 x cpu, so 256/1024 and 256/2048 pass, 256/512 (below the variable's 1024 floor), 256/4096
#    (above the variable's 2048 ceiling) and cpu 128 fail, and 1024/1024 still fails (1024 < 2 x 1024).
# All identifiers in this file are synthetic mock fixtures. No AWS client runs.
# Plan-only runs: never remove the mock_provider or change command to apply.
mock_provider "aws" {
  override_during = plan
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
  # A load-balanced runtime plan: enabled, certificate and ingress set (the same synthetic inputs as phase12b "https_has_no_http_fallback").
  runtime_enabled              = true
  runtime_composition_verified = true
  embedding_model_version      = "synthetic-pinned-version"
  synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
  image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  neptune_enabled              = true
  neptune_engine_version       = "1.4.6.3"
  neptune_parameter_family     = "neptune1.4"
  service_secret_bindings = {
    "query-api" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-internal-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-api-internal-token-AbCdEf"
    }
    "graph-service" = {
      SCHOLARCHAIN_GRAPH_CURSOR_KEY      = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-cursor-AbCdEf"
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-graph-service-internal-hash-AbCdEf"
    }
    "semantic-service" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-semantic-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-semantic-service-internal-hash-AbCdEf"
    }
    "embedding-worker" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-embedding-worker-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-embedding-worker-internal-hash-AbCdEf"
    }
  }
  https_certificate_arn = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-000000000001"
  public_ingress_cidrs  = ["192.0.2.0/24"]
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


# ---- defaults are unchanged ---------------------------------------------------------------------------------------------------

run "defaults_keep_container_insights_on_the_dashboard_on_and_the_512_1024_shape" {
  command = plan

  assert {
    condition     = length(output.phase12b_controls.runtime.cluster_settings) == 1 && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.name == "containerInsights" && setting.value == "enabled"]) == 1
    error_message = "Default: the cluster has exactly one setting, containerInsights = enabled."
  }
  assert {
    condition     = output.phase12b_controls.runtime.worker_policy != null && one(output.phase12b_controls.runtime.worker_policy.target_tracking_scaling_policy_configuration).target_value == 10
    error_message = "Default: the worker backlog policy exists with target 10 messages per running task."
  }
  assert {
    condition     = output.phase12b_controls.observability.dashboard != null && strcontains(output.phase12b_controls.observability.dashboard, "ScholarChain elasticity")
    error_message = "Default: the dashboard exists."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.task_definitions[s].cpu == "512" && output.phase12b_controls.runtime.task_definitions[s].memory == "1024"]) && length(output.phase12b_controls.runtime.task_definitions) == 4
    error_message = "Default: four task definitions at 512 CPU units / 1024 MiB."
  }
}

# ---- Container Insights off ---------------------------------------------------------------------------------------------------

run "container_insights_off_sets_disabled_and_drops_only_the_worker_backlog_policy" {
  command = plan
  variables {
    container_insights_enabled = false
  }

  assert {
    condition     = length(output.phase12b_controls.runtime.cluster_settings) == 1 && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.name == "containerInsights" && setting.value == "disabled"]) == 1 && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.value == "enabled"]) == 0
    error_message = "containerInsights = disabled and no setting is enabled."
  }
  assert {
    condition     = output.phase12b_controls.runtime.worker_policy == null
    error_message = "No worker backlog policy (count 0) without Container Insights: its RunningTaskCount metric would never exist."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.cpu_policies)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in output.phase12b_controls.runtime.cpu_policies : one(p.target_tracking_scaling_policy_configuration).target_value == 60 && one(one(p.target_tracking_scaling_policy_configuration).predefined_metric_specification).predefined_metric_type == "ECSServiceAverageCPUUtilization"])
    error_message = "The three HTTP CPU target-tracking policies (free AWS/ECS metric) are unaffected."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.scaling_targets)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) && length(output.phase12b_controls.runtime.services) == 4
    error_message = "All four scaling targets and services remain; only the worker backlog policy is gone."
  }
}

# ---- dashboard ----------------------------------------------------------------------------------------------------------------

run "dashboard_off_has_no_dashboard_and_keeps_alarms_log_groups_and_a_valid_controls_output" {
  command = plan
  variables {
    dashboard_enabled = false
  }

  assert {
    condition     = output.phase12b_controls.observability.dashboard == null
    error_message = "dashboard_enabled=false: no dashboard resource, the dashboard output is null."
  }
  assert {
    condition     = length(output.phase12b_controls.observability.log_groups) == 4 && toset(keys(output.phase12b_controls.observability.latency_alarms)) == toset(["query-api", "graph-service"]) && output.phase12b_controls.observability.queue_alarm.threshold == 300 && output.phase12b_controls.observability.error_alarm.threshold == 5
    error_message = "Alarms (queue age 300 s, p95 latency on two services, error percent 5) and the four log groups do not depend on the dashboard."
  }
  assert {
    condition     = output.phase12b_controls.runtime.worker_policy != null && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.value == "enabled"]) == 1
    error_message = "The dashboard switch is independent of Container Insights."
  }
}

run "both_cost_switches_off_together_is_the_cap_plan_shape" {
  command = plan
  variables {
    container_insights_enabled = false
    dashboard_enabled          = false
    service_capacity           = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 256, memory = 1024, min = 1, max = 2 } }
  }

  assert {
    condition     = output.phase12b_controls.observability.dashboard == null && output.phase12b_controls.runtime.worker_policy == null && length(output.phase12b_controls.runtime.cpu_policies) == 3
    error_message = "Dashboard null, worker policy null, three CPU policies."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.task_definitions[s].cpu == "256" && output.phase12b_controls.runtime.task_definitions[s].memory == "1024"]) && alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.scaling_targets[s].min_capacity == 1 && output.phase12b_controls.runtime.scaling_targets[s].max_capacity == 2])
    error_message = "Four task definitions at 256 CPU units / 1024 MiB, min 1, max 2."
  }
  assert {
    condition     = one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).min_capacity == 1 && one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).max_capacity == 2.5 && output.network_controls.nat_gateway_count == 1
    error_message = "Neptune stays at the 1 to 2.5 NCU guard and the network keeps its one NAT gateway."
  }
}

run "null_flags_fall_back_to_the_true_defaults_because_the_variables_are_not_nullable" {
  command = plan
  variables {
    container_insights_enabled = null
    dashboard_enabled          = null
  }

  assert {
    condition     = output.phase12b_controls.runtime.worker_policy != null && output.phase12b_controls.observability.dashboard != null && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.value == "enabled"]) == 1
    error_message = "nullable = false: a null value is replaced by the default (true), so a null can never silently disable a control."
  }
}

# ---- Fargate shape ------------------------------------------------------------------------------------------------------------

run "cpu_256_with_2048_mib_is_accepted" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 256, memory = 2048, min = 1, max = 2 } }
  }

  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.task_definitions[s].cpu == "256" && output.phase12b_controls.runtime.task_definitions[s].memory == "2048"])
    error_message = "256 CPU units with 2048 MiB is a valid Fargate pair and is accepted."
  }
}

run "cpu_256_with_512_mib_is_rejected" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 256, memory = 512, min = 1, max = 2 } }
  }
  expect_failures = [var.service_capacity]
}

run "cpu_256_with_4096_mib_is_rejected" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 256, memory = 4096, min = 1, max = 2 } }
  }
  expect_failures = [var.service_capacity]
}

run "cpu_128_is_rejected" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 128, memory = 1024, min = 1, max = 2 } }
  }
  expect_failures = [var.service_capacity]
}

run "cpu_1024_with_1024_mib_is_still_rejected" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 1024, memory = 1024, min = 1, max = 2 } }
  }
  expect_failures = [var.service_capacity]
}

run "cpu_256_does_not_widen_the_service_maximum" {
  command = plan
  variables {
    service_capacity = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 256, memory = 1024, min = 1, max = 3 } }
  }
  expect_failures = [var.service_capacity]
}
