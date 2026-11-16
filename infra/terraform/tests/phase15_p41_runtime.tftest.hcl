# Phase 15 P41 (docs/runbooks/session-2-plan.md rows F26 and P41; Work order 3 defaults accepted 2026-11-16), MODULE level:
# modules/runtime query_requests_per_target_target, semantic_rate_limit_per_second and semantic_rate_limit_burst. Root-level flow,
# validation boundaries and the dashboard panel are in phase15_p41.tftest.hcl.
# Hand-derived:
#  - aws_appautoscaling_policy.query_requests has count 1 only when enabled AND image_revision != null (the aws_lb.query and
#    aws_lb_target_group.query condition) AND the target is non-null; in every other case count 0 and no [0] index is evaluated;
#  - with the target set but no HTTPS (certificate_arn null, https_enabled null) the query-api service has no load balancer, AWS would refuse
#    the ALBRequestCountPerTarget label, and the policy's precondition refuses the plan;
#  - the rate-limit variables reach the query-api environment only in the aws service mode (enabled AND composition_verified);
#  - the CPU policies (three, target 60) are the same in every case;
#  - alb_metric_dimensions is null without the ALB and carries the two ARN suffixes with it.
# All identifiers are synthetic mock fixtures. No AWS client runs. Plan-only: never remove the mock_provider or run apply.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-2:111122223333:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-2:111122223333:repository/synthetic-phase14b-repo", repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/synthetic-phase14b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:loadbalancer/app/synthetic/1234567890123456", arn_suffix = "app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:targetgroup/synthetic/6543210987654321", arn_suffix = "targetgroup/synthetic/6543210987654321" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-2:111122223333:service/srv-synthetic" } }
}

variables {
  name_prefix              = "scholarchain-course"
  kms_key_arn              = "arn:aws:kms:us-east-2:111122223333:key/00000000-0000-0000-0000-000000000001"
  cleanup_mode             = false
  tags                     = {}
  enabled                  = true
  composition_verified     = true
  image_revision           = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  aws_region               = "us-east-2"
  vpc_id                   = "vpc-synthetic"
  application_subnets      = ["subnet-a", "subnet-b"]
  public_subnets           = ["subnet-c", "subnet-d"]
  security_groups          = { alb = "sg-alb", query-api = "sg-q", graph-service = "sg-g", semantic-service = "sg-s", embedding-worker = "sg-w" }
  task_roles               = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => "arn:aws:iam::111122223333:role/synthetic-${s}-task" }
  execution_roles          = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => "arn:aws:iam::111122223333:role/synthetic-${s}-execution" }
  service_secret_bindings  = {}
  capacity                 = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { cpu = 512, memory = 1024, min = 1, max = 2 } }
  cpu_target               = 60
  backlog_target           = 10
  service_port             = 8080
  certificate_arn          = "arn:aws:acm:us-east-2:111122223333:certificate/00000000-0000-0000-0000-000000000001"
  queue_name               = "synthetic-embedding"
  queue_url                = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-work"
  dlq_url                  = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-dlq"
  table_names              = { RunLedger = "t1", EntityLinkCache = "t2", QuerySession = "t3", EvidenceBundle = "t4", ArtifactRegistry = "t5", ResearcherMetricCache = "t6" }
  neptune_endpoint         = "https://synthetic.cluster-ro.neptune.amazonaws.com:8182"
  vector_bucket            = "synthetic-vectors"
  log_groups               = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => "/synthetic/${s}" }
  rag_bucket               = "synthetic-rag"
  graph_bucket             = "synthetic-graph"
  embedding_model_id       = "amazon.titan-embed-text-v2:0"
  vector_dimension         = 256
  vector_metric            = "cosine"
  query_session_index      = "by-idempotency-key"
  queue_visibility_seconds = 300
  queue_wait_seconds       = 20
  semantic_index           = "researcher-profile-v1"
  embedding_text_prefix    = "embedding-text"
  evidence_index_prefix    = "evidence-index"
  audit_prefix             = "runtime-audit"
}

run "module_default_has_no_request_policy_no_rate_limit_env_and_three_cpu_policies" {
  command = plan
  module {
    source = "./modules/runtime"
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 0 && output.compute_controls.request_policy == null
    error_message = "Module default (target null): no request-count policy."
  }
  assert {
    condition     = toset(keys(aws_appautoscaling_policy.http_cpu)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in aws_appautoscaling_policy.http_cpu : p.target_tracking_scaling_policy_configuration[0].target_value == 60])
    error_message = "Three CPU policies at target 60."
  }
  assert {
    condition     = alltrue([for s, d in aws_ecs_task_definition.service : !strcontains(d.container_definitions, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")]) && strcontains(aws_ecs_task_definition.service["query-api"].container_definitions, "\"SCHOLARCHAIN_SERVICE_MODE\",\"value\":\"aws\"")
    error_message = "aws mode on, but no rate-limit variable while both are null."
  }
  assert {
    condition     = output.alb_metric_dimensions == { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
    error_message = "With the ALB, alb_metric_dimensions carries the two ARN suffixes."
  }
}

run "module_target_with_https_creates_the_policy" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    query_requests_per_target_target = 600
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 1 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].predefined_metric_specification[0].resource_label == "app/synthetic/1234567890123456/targetgroup/synthetic/6543210987654321"
    error_message = "One policy; resource_label = \"<ALB arn_suffix>/<target group arn_suffix>\"."
  }
  assert {
    condition     = aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].predefined_metric_specification[0].predefined_metric_type == "ALBRequestCountPerTarget" && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].target_value == 600 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].scale_in_cooldown == 300 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].scale_out_cooldown == 60 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].disable_scale_in == false
    error_message = "ALBRequestCountPerTarget, target 600, cooldowns 300 / 60, scale-in enabled."
  }
  assert {
    condition     = aws_appautoscaling_policy.query_requests[0].resource_id == aws_appautoscaling_target.service["query-api"].resource_id && aws_appautoscaling_policy.query_requests[0].policy_type == "TargetTrackingScaling"
    error_message = "The policy is on the query-api scalable target."
  }
  assert {
    condition     = toset(keys(aws_appautoscaling_policy.http_cpu)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in aws_appautoscaling_policy.http_cpu : p.target_tracking_scaling_policy_configuration[0].target_value == 60 && p.target_tracking_scaling_policy_configuration[0].predefined_metric_specification[0].predefined_metric_type == "ECSServiceAverageCPUUtilization"])
    error_message = "The CPU policies are unchanged beside it."
  }
}

run "module_target_without_image_revision_has_no_policy_and_no_alb" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    image_revision                   = null
    query_requests_per_target_target = 600
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 0 && length(aws_lb.query) == 0 && length(aws_lb_target_group.query) == 0 && output.alb_metric_dimensions == null
    error_message = "No image revision: no ALB, no target group, no policy (no index error), null dimensions."
  }
}

run "module_target_with_the_runtime_disabled_has_no_policy" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    enabled                          = false
    query_requests_per_target_target = 600
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 0 && length(aws_appautoscaling_policy.http_cpu) == 0 && length(aws_lb.query) == 0 && output.alb_metric_dimensions == null
    error_message = "Runtime disabled: no policy of either kind, no ALB."
  }
}

run "module_target_without_https_is_refused_by_the_precondition" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    certificate_arn                  = null
    query_requests_per_target_target = 600
  }
  expect_failures = [aws_appautoscaling_policy.query_requests]
}

run "module_without_https_and_without_target_still_plans" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    certificate_arn = null
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 0 && length(aws_lb.query) == 1
    error_message = "The precondition binds only when the target is set: an HTTP-less deployed runtime without a target plans as before."
  }
}

run "module_rate_limit_env_is_query_api_only" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    semantic_rate_limit_per_second = 300
    semantic_rate_limit_burst      = 600
  }

  assert {
    condition     = { for e in jsondecode(aws_ecs_task_definition.service["query-api"].container_definitions)[0].environment : e.name => e.value if startswith(e.name, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_") } == { SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = "300", SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = "600" }
    error_message = "query-api: per second \"300\" and burst \"600\"."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : !strcontains(aws_ecs_task_definition.service[s].container_definitions, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")])
    error_message = "No other role receives the rate-limit variables."
  }
}

run "module_rate_limit_env_is_absent_outside_the_aws_mode" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    composition_verified           = false
    semantic_rate_limit_per_second = 300
    semantic_rate_limit_burst      = 600
  }

  assert {
    condition     = alltrue([for s, d in aws_ecs_task_definition.service : !strcontains(d.container_definitions, "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_")])
    error_message = "Unverified composition (SCHOLARCHAIN_SERVICE_MODE=unconfigured): no aws variable, including the rate limits."
  }
}

run "module_refuses_a_fractional_target" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    query_requests_per_target_target = 1.5
  }
  expect_failures = [var.query_requests_per_target_target]
}

# P41 review 1 F3: the Session 2 ACM path. The root passes https_enabled = true from plan-time values (api_domain_name) while the
# Terraform-requested certificate's ARN is still unknown (null here); local.https is then true, query-api is load balanced, and the
# precondition passes: exactly one request-count policy.
run "module_target_on_the_acm_path_creates_exactly_one_policy" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    https_enabled                    = true
    certificate_arn                  = null
    query_requests_per_target_target = 600
  }

  assert {
    condition     = length(aws_appautoscaling_policy.query_requests) == 1 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].target_value == 600 && aws_appautoscaling_policy.query_requests[0].target_tracking_scaling_policy_configuration[0].predefined_metric_specification[0].resource_label == "app/synthetic/1234567890123456/targetgroup/synthetic/6543210987654321"
    error_message = "https_enabled = true with certificate_arn = null (the ACM path): exactly one request-count policy, target 600, label \"<ALB>/<TG>\"."
  }
  assert {
    condition     = length(aws_appautoscaling_policy.http_cpu) == 3 && output.alb_metric_dimensions == { load_balancer = "app/synthetic/1234567890123456", target_group = "targetgroup/synthetic/6543210987654321" }
    error_message = "The three CPU policies stay, and the dashboard dimensions are set on the ACM path."
  }
}

run "module_refuses_a_fractional_burst" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    semantic_rate_limit_burst = 2.5
  }
  expect_failures = [var.semantic_rate_limit_burst]
}

run "module_refuses_burst_above_1000000" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    semantic_rate_limit_burst = 1000001
  }
  expect_failures = [var.semantic_rate_limit_burst]
}

run "module_refuses_rate_above_100000" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    semantic_rate_limit_per_second = 100001
  }
  expect_failures = [var.semantic_rate_limit_per_second]
}
