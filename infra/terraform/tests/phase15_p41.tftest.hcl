# Phase 15 P41 (docs/runbooks/session-2-plan.md rows F26 and P41; Work order 3 defaults accepted 2026-11-16), ROOT level: the
# query-api ALB request-count target-tracking policy, the P40 rate-limit environment override and the dashboard ALB panel, all through
# the root variables query_requests_per_target_target, query_semantic_rate_limit_per_second and query_semantic_rate_limit_burst
# (phase12b-variables.tf). Module-level cases (no HTTPS, enabled = false, the aws-mode condition) are in phase15_p41_runtime.tftest.hcl.
# Every expectation is hand-derived:
#  - the policy exists only when the runtime is deployed (runtime_enabled and image_revision, the aws_lb.query condition) AND the target
#    is non-null; its resource_label is "<ALB arn_suffix>/<target group arn_suffix>" (Application Auto Scaling ResourceLabel format
#    app/<name>/<id>/targetgroup/<name>/<id>), metric ALBRequestCountPerTarget, cooldowns 300 s in / 60 s out, scale-in enabled;
#  - the three HTTP CPU policies are unchanged in every case: keys query-api, graph-service, semantic-service, target 60,
#    ECSServiceAverageCPUUtilization, cooldowns 300 / 60;
#  - the two rate-limit variables reach the query-api task environment only, as decimal strings, each only when its own variable is set;
#  - the dashboard ALB panel has 2 metrics (RequestCountPerTarget by TargetGroup; HTTPCode_Target_4XX_Count by LoadBalancer + TargetGroup),
#    period 60, Sum, and exists only while the ALB exists. Dashboard metric count with Neptune on and EMR off (this fixture), counted by
#    hand from modules/observability/main.tf after Phase 15 P9: 6 ECS utilization (3 HTTP services x CPU, memory) + 2 queue depth + 1 queue
#    age + 2 Step Functions + 12 DynamoDB throttle (6 tables x read, write) = 23 base, plus 5 Neptune = 28 without the ALB, plus 9 ALB
#    (1 healthy hosts + 3 requests/5XX + 3 response-time percentiles + 2 in the P41 panel) = 37 with it. (Before P9: 114 and 116.)
#    The P9 limit (at most 50 in every combination) is asserted in phase15_elasticity_dashboard.tftest.hcl.
#  - validation: target 1..100000 whole (0, 100001, 1.5 refused); rate 1..100000 whole (0, 100001, 2.5 refused); burst 1..1000000 whole
#    (0, 1000001, 2.5 refused); the boundary values 1 / 100000 / 1000000 are accepted.
# All identifiers in this file are synthetic mock fixtures. No AWS client runs. Plan-only: never remove the mock_provider or run apply.
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
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:loadbalancer/app/synthetic/1234567890123456", arn_suffix = "app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-1:111122223333:targetgroup/synthetic/6543210987654321", arn_suffix = "targetgroup/synthetic/6543210987654321" } }
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
  # Repair round 3: this file asserts the Bedrock path (the primary providers are anthropic and voyage; see phase14b_providers.tftest.hcl).
  synthesis_provider               = "bedrock"
  embedding_provider               = "bedrock"
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


# ---- defaults: nothing new ------------------------------------------------------------------------------------------------------

run "default_deployed_runtime_has_no_request_policy_and_unchanged_cpu_policies" {
  command = plan

  assert {
    condition     = output.phase12b_controls.runtime.request_policy == null
    error_message = "Default (query_requests_per_target_target = null): no request-count policy."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.cpu_policies)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in output.phase12b_controls.runtime.cpu_policies : one(p.target_tracking_scaling_policy_configuration).target_value == 60 && one(p.target_tracking_scaling_policy_configuration).scale_in_cooldown == 300 && one(p.target_tracking_scaling_policy_configuration).scale_out_cooldown == 60 && one(one(p.target_tracking_scaling_policy_configuration).predefined_metric_specification).predefined_metric_type == "ECSServiceAverageCPUUtilization"])
    error_message = "The three HTTP CPU policies are unchanged: target 60, 300 / 60 s, ECSServiceAverageCPUUtilization."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")]) == 0])
    error_message = "Default: no SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_* variable in any task environment (the service defaults 50 / 100 apply)."
  }
}

# ---- the request-count policy ---------------------------------------------------------------------------------------------------

run "deployed_runtime_with_a_target_has_the_query_api_request_count_policy" {
  command = plan
  variables {
    query_requests_per_target_target = 1200
  }

  assert {
    condition     = output.phase12b_controls.runtime.request_policy != null
    error_message = "Runtime deployed and target set: the request-count policy exists."
  }
  assert {
    condition     = one(one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).predefined_metric_specification).resource_label == "app/synthetic/1234567890123456/targetgroup/synthetic/6543210987654321"
    error_message = "resource_label is \"<ALB arn_suffix>/<target group arn_suffix>\" in that order."
  }
  assert {
    condition     = one(one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).predefined_metric_specification).predefined_metric_type == "ALBRequestCountPerTarget" && length(one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).customized_metric_specification) == 0
    error_message = "The policy tracks the predefined ALBRequestCountPerTarget metric, no custom metric."
  }
  assert {
    condition     = one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).target_value == 1200 && one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).scale_in_cooldown == 300 && one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).scale_out_cooldown == 60 && one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).disable_scale_in == false
    error_message = "Target 1200 requests per target per minute, scale-in cooldown 300 s, scale-out cooldown 60 s, scale-in enabled."
  }
  assert {
    condition     = output.phase12b_controls.runtime.request_policy.policy_type == "TargetTrackingScaling" && output.phase12b_controls.runtime.request_policy.service_namespace == "ecs" && output.phase12b_controls.runtime.request_policy.scalable_dimension == "ecs:service:DesiredCount" && output.phase12b_controls.runtime.request_policy.resource_id == output.phase12b_controls.runtime.scaling_targets["query-api"].resource_id && output.phase12b_controls.runtime.request_policy.name == "scholarchain-course-query-api-requests"
    error_message = "A target-tracking policy on the query-api scalable target (ecs:service:DesiredCount) only."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.cpu_policies)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in output.phase12b_controls.runtime.cpu_policies : one(p.target_tracking_scaling_policy_configuration).target_value == 60 && one(p.target_tracking_scaling_policy_configuration).scale_in_cooldown == 300 && one(p.target_tracking_scaling_policy_configuration).scale_out_cooldown == 60 && one(one(p.target_tracking_scaling_policy_configuration).predefined_metric_specification).predefined_metric_type == "ECSServiceAverageCPUUtilization"])
    error_message = "The CPU policy is kept for all three HTTP services with target 60 beside the request-count policy."
  }
}

run "target_set_but_runtime_not_deployed_has_no_request_policy" {
  command = plan
  variables {
    runtime_enabled                  = false
    image_revision                   = null
    https_certificate_arn            = null
    query_requests_per_target_target = 1200
  }

  assert {
    condition     = output.phase12b_controls.runtime.request_policy == null && length(output.phase12b_controls.runtime.load_balancers) == 0 && length(output.phase12b_controls.runtime.cpu_policies) == 0
    error_message = "No ALB, no CPU policy and no request-count policy while the runtime is not deployed (no index error)."
  }
}

# ---- rate-limit environment --------------------------------------------------------------------------------------------------------

run "rate_only_sets_only_the_per_second_variable_on_query_api" {
  command = plan
  variables {
    query_semantic_rate_limit_per_second = 250
  }

  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_") } == { SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = "250" }
    error_message = "query-api carries SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = \"250\" and no burst variable."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")]) == 0])
    error_message = "No other role receives a rate-limit variable."
  }
}

run "burst_only_sets_only_the_burst_variable_on_query_api" {
  command = plan
  variables {
    query_semantic_rate_limit_burst = 500
  }

  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_") } == { SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = "500" }
    error_message = "query-api carries SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = \"500\" and no per-second variable."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")]) == 0])
    error_message = "No other role receives a rate-limit variable."
  }
}

run "both_rate_limit_values_at_their_upper_bounds_reach_query_api_as_plain_decimal_strings" {
  command = plan
  variables {
    query_semantic_rate_limit_per_second = 100000
    query_semantic_rate_limit_burst      = 1000000
    query_requests_per_target_target     = 100000
  }

  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_") } == { SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = "100000", SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = "1000000" }
    error_message = "The upper bounds are accepted and rendered as \"100000\" and \"1000000\" (no exponent form the service would refuse)."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")]) == 0]) && length([for d in output.phase12b_controls.runtime.task_definitions : d if strcontains(d.container_definitions, "RATE_LIMIT")]) == 1
    error_message = "Only the query-api task definition carries the rate-limit variables."
  }
  assert {
    condition     = one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).target_value == 100000
    error_message = "The target upper bound 100000 is accepted."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : !can(regex("RATE_LIMIT", jsonencode(jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].secrets)))])
    error_message = "The rate-limit values are plain settings in `environment`, never secret bindings."
  }
}

run "lower_bounds_are_accepted" {
  command = plan
  variables {
    query_requests_per_target_target     = 1
    query_semantic_rate_limit_per_second = 1
    query_semantic_rate_limit_burst      = 1
  }

  assert {
    condition     = one(output.phase12b_controls.runtime.request_policy.target_tracking_scaling_policy_configuration).target_value == 1 && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_") } == { SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = "1", SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = "1" }
    error_message = "1 is accepted for all three."
  }
}

# ---- dashboard ALB panel ---------------------------------------------------------------------------------------------------------

run "dashboard_has_the_alb_panel_while_the_alb_exists" {
  command = plan

  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "ALB requests per target and target 4XX (query-api)" && w.properties.period == 60 && w.properties.stat == "Sum" && w.properties.metrics == [["AWS/ApplicationELB", "RequestCountPerTarget", "TargetGroup", "targetgroup/synthetic/6543210987654321"], ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "app/synthetic/1234567890123456", "TargetGroup", "targetgroup/synthetic/6543210987654321"]]]) == 1
    error_message = "One ALB panel: RequestCountPerTarget (TargetGroup) and HTTPCode_Target_4XX_Count (LoadBalancer + TargetGroup), period 60, Sum."
  }
  assert {
    condition     = sum([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : length(try(w.properties.metrics, []))]) == 37
    error_message = "Dashboard metric count with Neptune on, EMR off and the ALB: 23 + 5 + 9 = 37 (hand count in the header; P9)."
  }
}

run "dashboard_has_no_alb_panel_without_the_alb" {
  command = plan
  variables {
    runtime_enabled       = false
    image_revision        = null
    https_certificate_arn = null
  }

  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if strcontains(jsonencode(w), "AWS/ApplicationELB")]) == 0 && alltrue([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : try(length(w.properties.metrics) > 0, true)])
    error_message = "No ALB: no ALB panel and no empty widget."
  }
  assert {
    condition     = sum([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : length(try(w.properties.metrics, []))]) == 28
    error_message = "Dashboard metric count without the ALB: 23 + 5 = 28 (Neptune on, EMR off; P9)."
  }
}

run "dashboard_off_with_the_alb_has_no_dashboard" {
  command = plan
  variables {
    dashboard_enabled                = false
    query_requests_per_target_target = 1200
  }

  assert {
    condition     = output.phase12b_controls.observability.dashboard == null && output.phase12b_controls.runtime.request_policy != null
    error_message = "dashboard_enabled = false still removes the dashboard; the policy does not depend on the dashboard."
  }
}

# ---- validation refusals at the boundaries ----------------------------------------------------------------------------------------

run "target_zero_is_refused" {
  command = plan
  variables {
    query_requests_per_target_target = 0
  }
  expect_failures = [var.query_requests_per_target_target]
}

run "target_above_100000_is_refused" {
  command = plan
  variables {
    query_requests_per_target_target = 100001
  }
  expect_failures = [var.query_requests_per_target_target]
}

run "fractional_target_is_refused" {
  command = plan
  variables {
    query_requests_per_target_target = 1.5
  }
  expect_failures = [var.query_requests_per_target_target]
}

run "rate_zero_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_per_second = 0
  }
  expect_failures = [var.query_semantic_rate_limit_per_second]
}

run "rate_above_100000_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_per_second = 100001
  }
  expect_failures = [var.query_semantic_rate_limit_per_second]
}

run "fractional_rate_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_per_second = 2.5
  }
  expect_failures = [var.query_semantic_rate_limit_per_second]
}

run "burst_zero_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_burst = 0
  }
  expect_failures = [var.query_semantic_rate_limit_burst]
}

run "burst_above_1000000_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_burst = 1000001
  }
  expect_failures = [var.query_semantic_rate_limit_burst]
}

# P41 review 1 F3: the whole-number (floor) check on the burst is exercised.
run "fractional_burst_is_refused" {
  command = plan
  variables {
    query_semantic_rate_limit_burst = 2.5
  }
  expect_failures = [var.query_semantic_rate_limit_burst]
}
