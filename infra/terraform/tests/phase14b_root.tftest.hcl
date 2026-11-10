# Phase 14B repair round 1 (review finding B1): the ROOT variable query_health_check_grace_period_seconds reaches the query-api
# ECS service through module "runtime". The mock and override header is copied from phase12b.tftest.hcl because a test file cannot
# import another file's mocks; the module-level behavior is asserted in phase14b.tftest.hcl.
# Every expectation is hand-derived: root default 300; recovery floor healthy_threshold x interval = 3 x 30 = 90 s.
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

run "root_default_grace_is_300_on_query_api_only_with_explicit_target_group_timing" {
  command = plan

  assert {
    condition     = output.phase12b_controls.runtime.services["query-api"].health_check_grace_period_seconds == 300
    error_message = "The root default (300) reaches the load-balanced query-api service."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.services[s].health_check_grace_period_seconds == null])
    error_message = "The other three services have no load balancer and no grace period."
  }
  assert {
    condition     = length(output.phase12b_controls.runtime.target_groups) == 1 && one(output.phase12b_controls.runtime.target_groups[0].health_check).interval == 30 && one(output.phase12b_controls.runtime.target_groups[0].health_check).healthy_threshold == 3 && one(output.phase12b_controls.runtime.target_groups[0].health_check).unhealthy_threshold == 3 && one(output.phase12b_controls.runtime.target_groups[0].health_check).path == "/readyz" && one(output.phase12b_controls.runtime.target_groups[0].health_check).matcher == "200"
    error_message = "Through the root the target group keeps /readyz, matcher 200 and the explicit 30 s / 3 / 3 timing."
  }
}

run "a_non_default_root_grace_reaches_the_query_api_service" {
  command = plan
  variables {
    query_health_check_grace_period_seconds = 600
  }

  assert {
    condition     = output.phase12b_controls.runtime.services["query-api"].health_check_grace_period_seconds == 600
    error_message = "The root variable, not a module default, sets the query-api grace period."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : output.phase12b_controls.runtime.services[s].health_check_grace_period_seconds == null])
    error_message = "A root override still never reaches a service without a load balancer."
  }
}

# The refusal of a grace below 90 s is a precondition on the module's aws_ecs_service; terraform test cannot expect_failures on a
# module-scoped resource from a root run ("You cannot expect failures from module.runtime.aws_ecs_service"), so the refusal is
# asserted at module level in phase14b.tftest.hcl (89 s and 0 s refused, 90 s accepted).

run "the_root_grace_equal_to_the_recovery_floor_of_90_seconds_is_accepted" {
  command = plan
  variables {
    query_health_check_grace_period_seconds = 90
  }

  assert {
    condition     = output.phase12b_controls.runtime.services["query-api"].health_check_grace_period_seconds == 90
    error_message = "healthy_threshold x interval = 3 x 30 = 90 is the inclusive floor."
  }
}

run "a_root_grace_above_3600_is_rejected" {
  command = plan
  variables {
    query_health_check_grace_period_seconds = 3601
  }
  expect_failures = [var.query_health_check_grace_period_seconds]
}

run "a_negative_root_grace_is_rejected" {
  command = plan
  variables {
    query_health_check_grace_period_seconds = -1
  }
  expect_failures = [var.query_health_check_grace_period_seconds]
}

run "a_fractional_root_grace_is_rejected" {
  command = plan
  variables {
    query_health_check_grace_period_seconds = 120.5
  }
  expect_failures = [var.query_health_check_grace_period_seconds]
}
