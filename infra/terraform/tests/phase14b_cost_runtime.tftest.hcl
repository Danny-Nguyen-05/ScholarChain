# Phase 14B replan under the USD 25 course cap (W1), module level: modules/runtime container_insights_enabled.
# Hand-derived: the cluster setting is "enabled" or "disabled"; the worker backlog policy needs Container Insights (RunningTaskCount)
# in addition to enabled = true and an image revision, so it has count 1 only for all three; the three HTTP CPU policies always exist
# while the runtime is enabled (free AWS/ECS metric) and none exists while it is disabled. Root-level flow is in phase14b_cost.tftest.hcl.
# All identifiers are synthetic mock fixtures. No AWS client runs. Plan-only: never remove the mock_provider or run apply.
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

run "module_default_has_container_insights_enabled_and_the_worker_backlog_policy" {
  command = plan
  module {
    source = "./modules/runtime"
  }

  assert {
    condition     = length([for setting in output.compute_controls.cluster_settings : setting if setting.name == "containerInsights" && setting.value == "enabled"]) == 1 && output.compute_controls.worker_policy != null && length(output.compute_controls.cpu_policies) == 3
    error_message = "Module default (true): insights enabled, worker policy present, three CPU policies."
  }
}

run "module_container_insights_false_disables_the_cluster_setting_and_removes_the_worker_policy" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    container_insights_enabled = false
  }

  assert {
    condition     = length([for setting in output.compute_controls.cluster_settings : setting if setting.name == "containerInsights" && setting.value == "disabled"]) == 1 && length(output.compute_controls.cluster_settings) == 1
    error_message = "containerInsights = disabled."
  }
  assert {
    condition     = output.compute_controls.worker_policy == null && toset(keys(output.compute_controls.cpu_policies)) == toset(["query-api", "graph-service", "semantic-service"])
    error_message = "Worker backlog policy count 0; the CPU policies stay."
  }
}

run "module_without_an_image_revision_has_no_worker_policy_even_with_insights_on" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    image_revision = null
  }

  assert {
    condition     = output.compute_controls.worker_policy == null && length(output.compute_controls.cluster_settings) == 1
    error_message = "The existing image-revision condition is preserved: no worker policy without an image revision."
  }
}

run "module_disabled_runtime_has_no_policies_and_still_records_the_setting" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    enabled                    = false
    container_insights_enabled = false
  }

  assert {
    condition     = output.compute_controls.worker_policy == null && length(output.compute_controls.cpu_policies) == 0 && length([for setting in output.compute_controls.cluster_settings : setting if setting.value == "disabled"]) == 1
    error_message = "With the runtime disabled no scaling policy exists; the cluster setting still follows the variable."
  }
}

run "module_null_container_insights_falls_back_to_the_true_default" {
  command = plan
  module {
    source = "./modules/runtime"
  }
  variables {
    container_insights_enabled = null
  }

  assert {
    condition     = output.compute_controls.worker_policy != null && length([for setting in output.compute_controls.cluster_settings : setting if setting.value == "enabled"]) == 1
    error_message = "nullable = false: null becomes the default true."
  }
}
