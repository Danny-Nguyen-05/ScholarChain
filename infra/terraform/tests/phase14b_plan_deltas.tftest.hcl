# Phase 14B pre-session item 9: the offline derivation of the two runtime-apply plans the live session makes after the base apply.
#   pointer runtime-apply : the base runtime state plus the four runtime_artifact_* values (runbook B8, "pointer");
#   EMR runtime-apply     : that state plus emr_config and emr_service_policy_json (runbook B9.3).
# Three plan-only runs with the real-session shape (anthropic and voyage defaults, Container Insights and dashboard off, the first
# runtime plan already containing the Neptune tunnel). Terraform cannot plan against a state offline, so the incremental plan is
# derived as the difference between consecutive full plans: the assertions below pin what may and may not differ between the runs (this
# is what makes "only the query-api task definition changes" and "EMR adds resources and nothing else changes" checkable), and the
# resource addresses come from `terraform test -verbose` through scripts/lib/plan_deltas.py (derive), which writes the reviewed list
# scripts/config/expected-plan-deltas.json compares against in the live session. The mock provider cannot show a computed attribute
# changing (it fills the task definition ARN with a constant), so the in-place update of the query-api ECS service that follows a
# task definition replacement is derived by hand from the dependency (aws_ecs_service.service.task_definition) and is marked as such.
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
  neptune_enabled                  = true
  neptune_engine_version           = "1.4.6.3"
  neptune_parameter_family         = "neptune1.4"
  api_domain_name                  = "api.example.invalid"
  service_secret_bindings = {
    "query-api" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-query-api-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-query-api-internal-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN        = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-query-api-internal-token-AbCdEf"
    }
    "graph-service" = {
      SCHOLARCHAIN_GRAPH_CURSOR_KEY      = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-graph-cursor-AbCdEf"
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-graph-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-graph-service-internal-hash-AbCdEf"
    }
    "semantic-service" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-semantic-service-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-semantic-service-internal-hash-AbCdEf"
    }
    "embedding-worker" = {
      SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-embedding-worker-api-hash-AbCdEf"
      SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-1:${join("", ["1111", "2222", "3333"])}:secret:synthetic-embedding-worker-internal-hash-AbCdEf"
    }
  }
}

# ---- plan 1: the state before the pointer apply (first runtime-apply shape) ----------------------------------------------------

run "plan_1_first_runtime_shape_has_no_pointer_and_no_emr" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
    container_insights_enabled   = false
    dashboard_enabled            = false
    service_capacity = {
      query-api        = { cpu = 256, memory = 1024, min = 1, max = 2 }
      graph-service    = { cpu = 256, memory = 1024, min = 1, max = 2 }
      semantic-service = { cpu = 256, memory = 1024, min = 1, max = 2 }
      embedding-worker = { cpu = 256, memory = 1024, min = 1, max = 2 }
    }
    query_health_check_grace_period_seconds = 300
  }
  assert {
    condition     = length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name if startswith(e.name, "SCHOLARCHAIN_RUNTIME_ARTIFACT_")]) == 0
    error_message = "Before the pointer apply query-api carries no SCHOLARCHAIN_RUNTIME_ARTIFACT_* variable."
  }
  assert {
    condition     = output.phase12b_controls.emr.enabled == false && output.phase12b_controls.emr.cluster == null && output.phase12b_controls.emr.efs == null
    error_message = "Before the EMR apply there is no cluster, no EFS and no EMR policy."
  }
  assert {
    condition     = output.phase12b_controls.observability.dashboard == null
    error_message = "dashboard_enabled = false: no dashboard resource exists to change when EMR is enabled."
  }
}

# ---- plan 2: pointer runtime-apply ---------------------------------------------------------------------------------------------

run "plan_2_pointer_changes_only_the_query_api_task_definition" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
    container_insights_enabled   = false
    dashboard_enabled            = false
    service_capacity = {
      query-api        = { cpu = 256, memory = 1024, min = 1, max = 2 }
      graph-service    = { cpu = 256, memory = 1024, min = 1, max = 2 }
      semantic-service = { cpu = 256, memory = 1024, min = 1, max = 2 }
      embedding-worker = { cpu = 256, memory = 1024, min = 1, max = 2 }
    }
    query_health_check_grace_period_seconds = 300
    runtime_artifact_key                    = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256                 = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id          = "run:3aa10c2d-0000-4000-8000-00000000000a"
  }
  assert {
    condition     = length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name if startswith(e.name, "SCHOLARCHAIN_RUNTIME_ARTIFACT_")]) == 3
    error_message = "With the pointer query-api carries exactly the three SCHOLARCHAIN_RUNTIME_ARTIFACT_* variables."
  }
  assert {
    condition = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] :
      output.phase12b_controls.runtime.task_definitions[s].container_definitions == run.plan_1_first_runtime_shape_has_no_pointer_and_no_emr.phase12b_controls.runtime.task_definitions[s].container_definitions
    ])
    error_message = "The pointer changes no other task definition: graph-service, semantic-service and embedding-worker are identical to plan 1."
  }
  assert {
    condition = (jsonencode([for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e if !startswith(e.name, "SCHOLARCHAIN_RUNTIME_ARTIFACT_")])
    == jsonencode([for e in jsondecode(run.plan_1_first_runtime_shape_has_no_pointer_and_no_emr.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e]))
    error_message = "Apart from the three pointer variables the query-api environment is identical to plan 1."
  }
  assert {
    condition = (jsonencode(output.iam_controls.task_policies) == jsonencode(run.plan_1_first_runtime_shape_has_no_pointer_and_no_emr.iam_controls.task_policies)
    && jsonencode(output.iam_controls.execution_policies) == jsonencode(run.plan_1_first_runtime_shape_has_no_pointer_and_no_emr.iam_controls.execution_policies))
    error_message = "The pointer changes no IAM policy: query-api already reads every key of the rag bucket."
  }
}

# ---- plan 3: EMR runtime-apply (pointer values kept) -------------------------------------------------------------------------

run "plan_3_emr_adds_the_emr_resources_and_changes_no_runtime_or_iam_document" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    neptune_tunnel_enabled       = true
    container_insights_enabled   = false
    dashboard_enabled            = false
    service_capacity = {
      query-api        = { cpu = 256, memory = 1024, min = 1, max = 2 }
      graph-service    = { cpu = 256, memory = 1024, min = 1, max = 2 }
      semantic-service = { cpu = 256, memory = 1024, min = 1, max = 2 }
      embedding-worker = { cpu = 256, memory = 1024, min = 1, max = 2 }
    }
    query_health_check_grace_period_seconds = 300
    runtime_artifact_key                    = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256                 = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id          = "run:3aa10c2d-0000-4000-8000-00000000000a"
    emr_config = {
      enabled             = true
      runtime_reference   = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF"
      runtime_verified    = true
      bootstrap_uri       = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261115/bin/bootstrap.sh"
      bootstrap_sha256    = "1111111111111111111111111111111111111111111111111111111111111111"
      runtime_archive_uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261115/runtime/scholarchain-runtime.tgz"
      job_jar_uri         = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261115/jars/spark-job.jar"
      job_jar_sha256      = "2222222222222222222222222222222222222222222222222222222222222222"
      extra_artifacts     = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-${join("", ["1111", "2222", "3333"])}-artifacts/emr/run-20261115/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }]
    }
    emr_service_policy_json = replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", var.aws_region), "<12-digit-account-id>", var.aws_account_id), "<environment>", "course")
  }
  assert {
    condition     = output.phase12b_controls.emr.enabled == true && output.phase12b_controls.emr.cluster != null && output.phase12b_controls.emr.efs != null && output.phase12b_controls.emr.security != null && output.phase12b_controls.emr.efs_security_group != null
    error_message = "With emr_config.enabled the cluster, the EFS stack and the node policy are planned."
  }
  assert {
    condition = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] :
      output.phase12b_controls.runtime.task_definitions[s].container_definitions == run.plan_2_pointer_changes_only_the_query_api_task_definition.phase12b_controls.runtime.task_definitions[s].container_definitions
    ])
    error_message = "Enabling EMR changes no task definition: the ECS services show no change."
  }
  assert {
    condition = (jsonencode(output.iam_controls.task_policies) == jsonencode(run.plan_2_pointer_changes_only_the_query_api_task_definition.iam_controls.task_policies)
      && jsonencode(output.iam_controls.execution_policies) == jsonencode(run.plan_2_pointer_changes_only_the_query_api_task_definition.iam_controls.execution_policies)
    && output.iam_controls.loader_policy == run.plan_2_pointer_changes_only_the_query_api_task_definition.iam_controls.loader_policy)
    error_message = "Enabling EMR changes no runtime role policy document (only the two EMR inline policies are added)."
  }
  assert {
    condition     = length(jsondecode(var.emr_service_policy_json).Statement) == 13
    error_message = "The EMR service policy is the 13-statement example with the three placeholders replaced."
  }
}
