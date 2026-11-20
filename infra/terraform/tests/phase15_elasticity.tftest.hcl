# Phase 15 elasticity bundle, ROOT level (docs/runbooks/session-2-plan.md rows F5, P9, F23 and P34):
#  - P9: the elasticity dashboard through the real root wiring has at most 50 metrics, from the smallest plan (runtime, Neptune and EMR
#    off: 23) to the largest (runtime with its ALB, Neptune and EMR: 23 + 9 + 5 + 6 = 43). The full 8-combination matrix with the
#    hand count is module-level, in phase15_elasticity_dashboard.tftest.hcl; Neptune + ALB (37) and Neptune alone (28) are pinned in
#    phase15_p41.tftest.hcl.
#  - Neptune capacity guard (terraform_data.phase12b_guard, phase12b.tf): min >= 1 and max exactly 2.5 NCU. P34 asked to allow max 1;
#    the Amazon Neptune User Guide, "Capacity scaling in a Neptune Serverless DB cluster" (read 2026-11-16), says "the smallest value you
#    can set for the maximum capacity is 2.5 NCUs" and "the lowest minimum is 1.0 NCUs", so max 1 stays refused here pending the human's
#    P34 decision. These runs pin the guard as it is; they change nothing.
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
  mock_resource "aws_emr_cluster" { defaults = { id = "j-SYNTHETICP9" } }
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
  synthesis_provider               = "bedrock"
  embedding_provider               = "bedrock"
  aws_account_id                   = "111122223333"
  aws_region                       = "us-east-1"
  aws_profile                      = "synthetic-not-a-real-profile"
  availability_zones               = ["us-east-1a", "us-east-1b"]
  deployment_trusted_principal_arn = "arn:aws:iam::111122223333:role/synthetic-architect"
  budget_limit_usd                 = 50 # Synthetic validation input, not the user's budget.
  # A load-balanced runtime plan with Neptune (the phase15_p41.tftest.hcl fixture).
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

# ---- P9: root dashboard metric count ---------------------------------------------------------------------------------------------

run "root_smallest_plan_dashboard_has_23_metrics" {
  command = plan
  variables {
    runtime_enabled       = false
    image_revision        = null
    https_certificate_arn = null
    neptune_enabled       = false
  }

  assert {
    condition     = sum([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : length(try(w.properties.metrics, []))]) == 23
    error_message = "Runtime, Neptune and EMR off: 23 metrics (6 ECS + 3 SQS + 2 Step Functions + 12 DynamoDB throttle)."
  }
  assert {
    condition     = alltrue(flatten([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : [for m in try(w.properties.metrics, []) : startswith(m[0], "AWS/")]])) && !strcontains(output.phase12b_controls.observability.dashboard, "ECS/ContainerInsights")
    error_message = "Free native AWS/* metrics only."
  }
}

run "root_largest_plan_with_runtime_neptune_and_emr_has_43_metrics_at_most_50" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "${jsondecode(file("emr-step-programs.json")).bin_dir}/${n}" }] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  override_resource {
    target          = module.identity.aws_iam_role.emr_service
    override_during = plan
    values          = { id = "synthetic-emr-service", arn = "arn:aws:iam::111122223333:role/synthetic-emr-service" }
  }
  override_resource {
    target          = module.identity.aws_iam_role.emr_ec2
    override_during = plan
    values          = { id = "synthetic-emr-ec2", arn = "arn:aws:iam::111122223333:role/synthetic-emr-ec2" }
  }

  assert {
    condition     = sum([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : length(try(w.properties.metrics, []))]) == 43
    error_message = "Runtime ALB, Neptune and EMR: 23 + 9 + 5 + 6 = 43 metrics."
  }
  assert {
    condition     = sum([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : length(try(w.properties.metrics, []))]) <= 50
    error_message = "P9: at most 50 metrics with every optional source."
  }
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if strcontains(jsonencode(w), "AWS/ApplicationELB")]) == 4 && length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if can(regex("^(EMR |Neptune )", try(w.properties.title, "")))]) == 3
    error_message = "Four ALB panels, one EMR panel and two Neptune panels."
  }
}

# ---- Neptune capacity guard as it stands (P34 pending the human decision) -------------------------------------------------------

run "neptune_default_capacity_1_to_2_5_is_accepted" {
  command = plan

  assert {
    condition     = one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).min_capacity == 1 && one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).max_capacity == 2.5
    error_message = "Defaults: min 1 NCU (the AWS lowest minimum) and max 2.5 NCU (the AWS smallest maximum)."
  }
}

run "neptune_max_1_is_refused_below_the_aws_smallest_maximum_2_5" {
  command = plan
  variables {
    neptune_max_ncu = 1
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "neptune_max_above_2_5_is_refused" {
  command = plan
  variables {
    neptune_max_ncu = 3
  }
  expect_failures = [terraform_data.phase12b_guard]
}

# min below 1 is not a run here: the AWS provider's schema validation already refuses it before the guard is checked (observed
# 2026-11-16 with neptune_min_ncu = 0.5: "expected serverless_v2_scaling_configuration.0.min_capacity to be at least (1.000000)"),
# and expect_failures cannot name a provider validation error.
