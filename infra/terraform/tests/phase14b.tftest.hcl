# Phase 14B Step 0 repair (review 2 finding N3) and repair round 1 (review finding B1): the query-api health-check grace period and the
# explicit ALB target-group health-check timing.
# Every expectation is hand-derived from:
#  - the ECS rule (https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_CreateService.html): healthCheckGracePeriodSeconds is
#    valid only for services configured to use a load balancer; the grace period and the load_balancer block share
#    local.load_balanced_service (query-api, only when certificate_arn is set);
#  - the ELBv2 HealthCheck limits (https://docs.aws.amazon.com/elasticloadbalancing/latest/APIReference/API_CreateTargetGroup.html):
#    interval 5-300 s, thresholds 2-10, timeout 2-120 s and smaller than the interval;
#  - the recovery arithmetic: a once-unhealthy target needs healthy_threshold x interval of passes, 3 x 30 = 90 s by default, so the
#    default grace is 300 s and the guard floor is 90 s (inclusive).
# The root variable flow is asserted in phase14b_root.tftest.hcl. All identifiers are synthetic mock fixtures.
# No AWS client runs. Plan-only: never remove the mock_provider or run apply.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-2:111122223333:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-2:111122223333:repository/synthetic-phase14b-repo", repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/synthetic-phase14b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:loadbalancer/app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:targetgroup/synthetic/1234567890123456" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-2:111122223333:service/srv-synthetic" } }
}

variables {
  name_prefix              = "scholarchain-course"
  kms_key_arn              = "arn:aws:kms:us-east-2:111122223333:key/00000000-0000-0000-0000-000000000001"
  cleanup_mode             = false
  tags                     = {}
  enabled                  = true
  composition_verified     = false
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

# ---- grace period: default, scope, pass-through -------------------------------------------------------------------------------

run "query_api_behind_the_alb_gets_the_default_300_second_grace_period_and_no_other_service_does" {
  command = plan
  module {
    source = "./modules/runtime"
  }

  assert {
    condition     = length(output.compute_controls.services) == 4 && output.compute_controls.services["query-api"].health_check_grace_period_seconds == 300
    error_message = "With a certificate, query-api (the only load-balanced service) has a 300 second grace period by default."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : output.compute_controls.services[s].health_check_grace_period_seconds == null])
    error_message = "graph-service, semantic-service and embedding-worker have no load balancer, so the grace period must be absent."
  }
  assert {
    condition     = length(output.compute_controls.services["query-api"].load_balancer) == 1 && alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length(output.compute_controls.services[s].load_balancer) == 0])
    error_message = "The grace period is present exactly where the load_balancer block is present."
  }
}

run "query_api_without_a_certificate_has_no_load_balancer_and_no_grace_period" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    certificate_arn = null
  }

  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.compute_controls.services[s].health_check_grace_period_seconds == null && length(output.compute_controls.services[s].load_balancer) == 0])
    error_message = "Without certificate_arn no service is load-balanced, so none may carry a grace period (ECS rejects it)."
  }
}

run "a_non_default_grace_period_reaches_only_query_api" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 600
  }

  assert {
    condition     = output.compute_controls.services["query-api"].health_check_grace_period_seconds == 600
    error_message = "The configured value, not a constant, reaches the load-balanced service."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : output.compute_controls.services[s].health_check_grace_period_seconds == null])
    error_message = "A non-default value still never reaches a service without a load balancer."
  }
}

# ---- grace period: validation of the variable ---------------------------------------------------------------------------------

run "the_upper_bound_3600_is_accepted" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 3600
  }

  assert {
    condition     = output.compute_controls.services["query-api"].health_check_grace_period_seconds == 3600
    error_message = "3600 seconds is the inclusive upper bound."
  }
}

run "a_grace_period_above_3600_seconds_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 3601
  }
  expect_failures = [var.health_check_grace_period_seconds]
}

run "a_negative_grace_period_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = -1
  }
  expect_failures = [var.health_check_grace_period_seconds]
}

run "a_fractional_grace_period_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 12.5
  }
  expect_failures = [var.health_check_grace_period_seconds]
}

# ---- cross-variable guard: grace >= healthy_threshold x interval --------------------------------------------------------------

run "the_guard_floor_is_healthy_threshold_times_interval_inclusive_90_seconds_by_default" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 90
  }

  assert {
    condition     = output.compute_controls.services["query-api"].health_check_grace_period_seconds == 90
    error_message = "3 x 30 = 90 is accepted: the target can just recover inside the grace."
  }
}

run "a_grace_period_of_89_seconds_is_refused_by_the_guard" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 89
  }
  expect_failures = [aws_ecs_service.service]
}

run "zero_grace_is_refused_by_the_guard_while_query_api_is_load_balanced" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_grace_period_seconds = 0
  }
  expect_failures = [aws_ecs_service.service]
}

run "zero_grace_without_a_load_balancer_is_not_guarded_and_stays_absent" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    certificate_arn                   = null
    health_check_grace_period_seconds = 0
  }

  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : output.compute_controls.services[s].health_check_grace_period_seconds == null])
    error_message = "Without a load balancer the grace period is absent everywhere and the recovery guard does not apply."
  }
}

run "the_guard_follows_the_timing_overrides_healthy_5_times_interval_60_needs_300_seconds" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds     = 60
    health_check_healthy_threshold    = 5
    health_check_grace_period_seconds = 299
  }
  expect_failures = [aws_ecs_service.service]
}

run "the_guard_accepts_exactly_healthy_5_times_interval_60_equals_300_seconds" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds     = 60
    health_check_healthy_threshold    = 5
    health_check_grace_period_seconds = 300
  }

  assert {
    condition     = output.compute_controls.services["query-api"].health_check_grace_period_seconds == 300
    error_message = "5 x 60 = 300 is the inclusive floor for that timing."
  }
}

# ---- target-group health-check timing: explicit, overridable ------------------------------------------------------------------

run "the_target_group_health_check_is_explicit_30_3_3_with_readyz_and_200" {
  command = plan
  module {
    source = "./modules/runtime"
  }

  assert {
    condition     = length(output.compute_controls.target_groups) == 1 && one(output.compute_controls.target_groups[0].health_check).interval == 30 && one(output.compute_controls.target_groups[0].health_check).healthy_threshold == 3 && one(output.compute_controls.target_groups[0].health_check).unhealthy_threshold == 3
    error_message = "The target group sets interval 30, healthy 3 and unhealthy 3 explicitly instead of relying on a default."
  }
  assert {
    condition     = one(output.compute_controls.target_groups[0].health_check).timeout == 5 && one(output.compute_controls.target_groups[0].health_check).path == "/readyz" && one(output.compute_controls.target_groups[0].health_check).matcher == "200"
    error_message = "Timeout is explicit 5 (smaller than the interval); path /readyz and matcher 200 are unchanged."
  }
}

run "the_target_group_timing_is_explicit_even_without_a_certificate" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    certificate_arn = null
  }

  assert {
    condition     = length(output.compute_controls.target_groups) == 1 && one(output.compute_controls.target_groups[0].health_check).interval == 30 && one(output.compute_controls.target_groups[0].health_check).healthy_threshold == 3 && one(output.compute_controls.target_groups[0].health_check).unhealthy_threshold == 3
    error_message = "The target group exists whenever the runtime and image revision are set; its timing is explicit with or without a listener."
  }
}

run "the_target_group_timing_can_be_overridden" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds     = 15
    health_check_timeout_seconds      = 10
    health_check_healthy_threshold    = 4
    health_check_unhealthy_threshold  = 2
    health_check_grace_period_seconds = 300
  }

  assert {
    condition     = one(output.compute_controls.target_groups[0].health_check).interval == 15 && one(output.compute_controls.target_groups[0].health_check).timeout == 10 && one(output.compute_controls.target_groups[0].health_check).healthy_threshold == 4 && one(output.compute_controls.target_groups[0].health_check).unhealthy_threshold == 2
    error_message = "The configured values, not constants, reach the target group."
  }
}

run "the_lowest_allowed_timing_5_2_2_2_is_accepted" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds    = 5
    health_check_timeout_seconds     = 2
    health_check_healthy_threshold   = 2
    health_check_unhealthy_threshold = 2
  }

  assert {
    condition     = one(output.compute_controls.target_groups[0].health_check).interval == 5 && one(output.compute_controls.target_groups[0].health_check).timeout == 2
    error_message = "Interval 5, timeout 2 and thresholds 2 are the inclusive lower bounds."
  }
}

run "the_highest_allowed_timing_300_120_10_10_is_accepted" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds     = 300
    health_check_timeout_seconds      = 120
    health_check_healthy_threshold    = 10
    health_check_unhealthy_threshold  = 10
    health_check_grace_period_seconds = 3000
  }

  assert {
    condition     = one(output.compute_controls.target_groups[0].health_check).interval == 300 && one(output.compute_controls.target_groups[0].health_check).timeout == 120 && one(output.compute_controls.target_groups[0].health_check).healthy_threshold == 10
    error_message = "Interval 300, timeout 120 and thresholds 10 are the inclusive upper bounds (10 x 300 = 3000 <= grace 3000)."
  }
}

run "a_timeout_equal_to_the_interval_is_refused_by_the_target_group" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds = 10
    health_check_timeout_seconds  = 10
  }
  expect_failures = [aws_lb_target_group.query]
}

# ---- target-group health-check timing: validation ranges ----------------------------------------------------------------------

run "an_interval_below_5_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds = 4
  }
  expect_failures = [var.health_check_interval_seconds]
}

run "an_interval_above_300_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds = 301
  }
  expect_failures = [var.health_check_interval_seconds]
}

run "a_fractional_interval_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_interval_seconds = 30.5
  }
  expect_failures = [var.health_check_interval_seconds]
}

run "a_timeout_below_2_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_timeout_seconds = 1
  }
  expect_failures = [var.health_check_timeout_seconds]
}

run "a_timeout_above_120_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_timeout_seconds = 121
  }
  expect_failures = [var.health_check_timeout_seconds]
}

run "a_healthy_threshold_below_2_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_healthy_threshold = 1
  }
  expect_failures = [var.health_check_healthy_threshold]
}

run "a_healthy_threshold_above_10_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_healthy_threshold = 11
  }
  expect_failures = [var.health_check_healthy_threshold]
}

run "a_fractional_healthy_threshold_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_healthy_threshold = 2.5
  }
  expect_failures = [var.health_check_healthy_threshold]
}

run "an_unhealthy_threshold_below_2_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_unhealthy_threshold = 1
  }
  expect_failures = [var.health_check_unhealthy_threshold]
}

run "an_unhealthy_threshold_above_10_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_unhealthy_threshold = 11
  }
  expect_failures = [var.health_check_unhealthy_threshold]
}

run "a_fractional_unhealthy_threshold_is_rejected" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    health_check_unhealthy_threshold = 3.5
  }
  expect_failures = [var.health_check_unhealthy_threshold]
}
