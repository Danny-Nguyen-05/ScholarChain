# Replan G-MAIN (Phase 14B, gap G3): the runtime-artifact pointer reaches the query-api task environment and nothing else.
# Every expectation is hand-derived from the services contract (modules/services/README.md, "Environment contract", and AwsConfig.scala):
#   - only the query-api role reads SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY / _SHA256 / _SOURCE_RUN_ID (the `case _ =>` branch of the role match;
#     graph-service, semantic-service and embedding-worker have their own branches that never read them);
#   - the three are all or none (AwsConfig: a partial set is `r.refuse("SCHOLARCHAIN_RUNTIME_ARTIFACT_*")`);
#   - the key must contain /versions/ and no '..' segment, the sha256 must be 64 lowercase hex;
#   - SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET is optional and defaults to the rag bucket, which is the bucket the contract uses; Terraform sets it
#     only when runtime_artifact_bucket is given, and then only the rag bucket's own name is accepted (root guard);
#   - query-api already holds s3:GetObject on every key of the rag bucket (modules/identity service_read_buckets["query-api"]), so no new
#     IAM statement is needed for the read.
# The mock and override header is copied from phase14b_replan.tftest.hcl (a test file cannot import another file's mocks).
# All identifiers are synthetic (account 111122223333, api.example.invalid). Plan-only: never remove the mock_provider or run apply.

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
  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:us-east-1:111122223333:certificate/00000000-0000-0000-0000-0000000000a1"
      domain_validation_options = [{
        domain_name           = "api.example.invalid"
        resource_record_name  = "_0123456789abcdef.api.example.invalid."
        resource_record_type  = "CNAME"
        resource_record_value = "_fedcba9876543210.acm-validations.invalid."
      }]
    }
  }
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
override_resource {
  target          = module.identity.aws_iam_role.execution["graph-service"]
  override_during = plan
  values          = { arn = "arn:aws:iam::111122223333:role/synthetic-graph-service-execution" }
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
  values          = { arn = "arn:aws:iam::111122223333:role/synthetic-neptune-tunnel-task" }
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
  # Base shape: the runtime is disabled; every run flips what it needs. Neptune is configured so the runtime runs are valid.
  runtime_enabled              = false
  runtime_composition_verified = false
  embedding_model_version      = "synthetic-pinned-version"
  synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
  neptune_enabled              = true
  neptune_engine_version       = "1.4.6.3"
  neptune_parameter_family     = "neptune1.4"
  api_domain_name              = "api.example.invalid"
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
}


run "with_no_pointer_no_service_receives_any_runtime_artifact_variable" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "The pointer is null by default (it is published by the 14C load): query-api receives no SCHOLARCHAIN_RUNTIME_ARTIFACT_* variable, so the services refuse artifact reads as before."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "The pointer is null by default (it is published by the 14C load): graph-service receives no SCHOLARCHAIN_RUNTIME_ARTIFACT_* variable, so the services refuse artifact reads as before."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["semantic-service"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "The pointer is null by default (it is published by the 14C load): semantic-service receives no SCHOLARCHAIN_RUNTIME_ARTIFACT_* variable, so the services refuse artifact reads as before."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["embedding-worker"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "The pointer is null by default (it is published by the 14C load): embedding-worker receives no SCHOLARCHAIN_RUNTIME_ARTIFACT_* variable, so the services refuse artifact reads as before."
  }
}

run "the_pointer_reaches_the_query_api_environment_with_exactly_the_three_values" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY"] == "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256"] == "abababababababababababababababababababababababababababababababab" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID"] == "run:3aa10c2d-0000-4000-8000-000000000001"
    error_message = "query-api receives the key, the sha256 and the source run id exactly as supplied."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 3
    error_message = "Exactly three SCHOLARCHAIN_RUNTIME_ARTIFACT_* variables: with runtime_artifact_bucket unset the optional bucket variable is not set (the services default is the rag bucket)."
  }
  assert {
    condition     = !contains(keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }), "SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET") && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_STORAGE_RAG_BUCKET"] == "scholarchain-course-111122223333-rag"
    error_message = "The artifact bucket is left to the services default, which is the rag bucket query-api is configured with."
  }
}

run "the_pointer_reaches_no_other_service" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "graph-service never reads the runtime-artifact pointer (AwsConfig reads it in the query-api role only), so it must not receive it."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["semantic-service"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "semantic-service never reads the runtime-artifact pointer (AwsConfig reads it in the query-api role only), so it must not receive it."
  }
  assert {
    condition     = length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["embedding-worker"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0
    error_message = "embedding-worker never reads the runtime-artifact pointer (AwsConfig reads it in the query-api role only), so it must not receive it."
  }
}

run "the_pointer_is_environment_text_never_a_secret_binding" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = length(jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].secrets) == 3 && alltrue([for s in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].secrets : !startswith(s.name, "SCHOLARCHAIN_RUNTIME_ARTIFACT")])
    error_message = "The pointer is not a secret: the three secret bindings of query-api are unchanged and none is a runtime-artifact name."
  }
}

run "the_rest_of_the_query_api_environment_is_unchanged_by_the_pointer" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = length({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }) == 26 && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_SERVICE_MODE"] == "aws"
    error_message = "query-api has 21 variables without the pointer (4 base + 2 service URIs + 6 table names + the session index + the rag bucket + 2 synthesis + 3 embedding + 2 prefixes = 21, the same 21 as the exact map in phase14a.tftest.hcl) plus the 3 of the pointer = 24; repair round 3 adds the two provider switches (SCHOLARCHAIN_SYNTHESIS_PROVIDER, SCHOLARCHAIN_EMBEDDING_PROVIDER) = 26."
  }
}

run "query_api_can_already_read_every_key_of_the_rag_bucket_so_no_new_iam_statement_is_needed" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if st.Sid == "ReadConfiguredObjects" && st.Action == ["s3:GetObject", "s3:GetObjectVersion"] && length(st.Resource) == 3 && alltrue([for r in st.Resource : endswith(r, "/*")])]) == 1
    error_message = "query-api has one object-read statement over the whole of three buckets (rag, artifacts, graph; every resource ends in /*), which includes runtime-artifacts/<run_prefix>/ in the rag bucket."
  }
  assert {
    condition     = output.iam_controls != null && can(regex("query-api\\s*=\\s*\\[\"rag\", \"artifacts\", \"graph\"\\]", file("modules/identity/main.tf")))
    error_message = "The three read buckets of query-api are rag, artifacts and graph: the rag bucket is the one that holds the runtime artifact."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length([for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st if st.Sid == "ReadConfiguredObjects"]) == 1])
    error_message = "Statement set of the other roles is unchanged (one read statement each)."
  }
}

run "the_runtime_environment_is_valid_when_the_pointer_key_uses_the_longest_run_prefix" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_key           = "runtime-artifacts/run-aaaaaaaaaaaaaaaaaaaaaaaaaaaa/versions/v1/x.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:1"
  }
  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY"] == "runtime-artifacts/run-aaaaaaaaaaaaaaaaaaaaaaaaaaaa/versions/v1/x.json"
    error_message = "run- plus 28 characters is the longest run prefix the deployer's operator_run_prefix accepts; it is accepted."
  }
}

run "a_partial_pointer_with_only_the_key_is_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    runtime_artifact_key         = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_partial_pointer_with_only_the_sha256_is_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    runtime_artifact_sha256      = "abababababababababababababababababababababababababababababababab"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_partial_pointer_with_only_the_source_run_id_is_refused" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_partial_pointer_with_the_key_and_the_sha256_without_the_run_id_is_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    runtime_artifact_key         = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256      = "abababababababababababababababababababababababababababababababab"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_partial_pointer_with_the_sha256_and_the_run_id_without_the_key_is_refused" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_pointer_without_the_runtime_is_refused" {
  command = plan
  variables {
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_key_outside_the_runtime_artifacts_prefix_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "pipeline/run-20261115/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_under_the_prefix_but_without_a_run_prefix_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_an_invalid_run_prefix_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-A/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_one_character_run_prefix_suffix_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-a/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_too_long_run_prefix_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-aaaaaaaaaaaaaaaaaaaaaaaaaaaaa/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_without_the_versions_segment_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_nothing_after_versions_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_parent_segment_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/../y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_dot_segment_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/./y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_an_empty_segment_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions//y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_leading_slash_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "/runtime-artifacts/run-20261115/versions/x/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_space_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/x/y z.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_colon_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/run:1/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_with_a_wildcard_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/*/y.json"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_key_over_900_characters_is_rejected" {
  command = plan
  variables {
    runtime_artifact_key = "runtime-artifacts/run-20261115/versions/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.runtime_artifact_key]
}

run "a_sha256_of_uppercase_hex_is_rejected" {
  command = plan
  variables {
    runtime_artifact_sha256 = "ABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABABAB"
  }
  expect_failures = [var.runtime_artifact_sha256]
}

run "a_sha256_of_63_characters_is_rejected" {
  command = plan
  variables {
    runtime_artifact_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.runtime_artifact_sha256]
}

run "a_sha256_of_65_characters_is_rejected" {
  command = plan
  variables {
    runtime_artifact_sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [var.runtime_artifact_sha256]
}

run "a_sha256_of_non_hex_characters_is_rejected" {
  command = plan
  variables {
    runtime_artifact_sha256 = "gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg"
  }
  expect_failures = [var.runtime_artifact_sha256]
}

run "a_sha256_of_empty_is_rejected" {
  command = plan
  variables {
    runtime_artifact_sha256 = ""
  }
  expect_failures = [var.runtime_artifact_sha256]
}

run "a_source_run_id_with_a_space_is_rejected" {
  command = plan
  variables {
    runtime_artifact_source_run_id = "run 1"
  }
  expect_failures = [var.runtime_artifact_source_run_id]
}

run "a_source_run_id_with_a_slash_is_rejected" {
  command = plan
  variables {
    runtime_artifact_source_run_id = "run/1"
  }
  expect_failures = [var.runtime_artifact_source_run_id]
}

run "a_source_run_id_with_a_leading_dash_is_rejected" {
  command = plan
  variables {
    runtime_artifact_source_run_id = "-run"
  }
  expect_failures = [var.runtime_artifact_source_run_id]
}

run "a_source_run_id_with_empty_is_rejected" {
  command = plan
  variables {
    runtime_artifact_source_run_id = ""
  }
  expect_failures = [var.runtime_artifact_source_run_id]
}

run "a_source_run_id_with_129_characters_is_rejected" {
  command = plan
  variables {
    runtime_artifact_source_run_id = "rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr"
  }
  expect_failures = [var.runtime_artifact_source_run_id]
}

run "a_bucket_equal_to_the_rag_bucket_adds_the_fourth_variable_to_query_api_only" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_bucket        = "scholarchain-course-111122223333-rag"
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET"] == "scholarchain-course-111122223333-rag" && length([for n in keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }) : n if startswith(n, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 4 && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET"] == { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_STORAGE_RAG_BUCKET"]
    error_message = "With runtime_artifact_bucket equal to the rag bucket query-api receives four variables and the bucket equals SCHOLARCHAIN_STORAGE_RAG_BUCKET."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service", "embedding-worker"] : length([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e.name if startswith(e.name, "SCHOLARCHAIN_RUNTIME_ARTIFACT")]) == 0])
    error_message = "The bucket variable, like the rest of the pointer, reaches query-api only."
  }
}

run "a_bucket_other_than_the_rag_bucket_is_refused" {
  command = plan
  variables {
    runtime_enabled                = true
    runtime_composition_verified   = true
    image_revision                 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs           = ["192.0.2.0/24"]
    runtime_artifact_bucket        = "scholarchain-course-111122223333-artifacts"
    runtime_artifact_key           = "runtime-artifacts/run-20261115/versions/run-3aa1-0c2d/runtime-subset-abababababababababababababababababababababababababababababababab.json"
    runtime_artifact_sha256        = "abababababababababababababababababababababababababababababababab"
    runtime_artifact_source_run_id = "run:3aa10c2d-0000-4000-8000-000000000001"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_bucket_without_the_pointer_is_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
    runtime_artifact_bucket      = "scholarchain-course-111122223333-rag"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_malformed_bucket_name_is_rejected" {
  command = plan
  variables {
    runtime_artifact_bucket = "Not_A_Bucket"
  }
  expect_failures = [var.runtime_artifact_bucket]
}

run "the_rag_list_scope_of_the_runtime_roles_includes_the_runtime_artifacts_prefix" {
  command = plan

  assert {
    condition = alltrue([
      for s in ["query-api", "embedding-worker"] :
      alltrue([for st in jsondecode(output.iam_controls.task_policies[s]).Statement : contains(st.Condition.StringLike["s3:prefix"], "runtime-artifacts") && contains(st.Condition.StringLike["s3:prefix"], "runtime-artifacts/*") if st.Sid == "ListRagBucketPrefixes"])
    ])
    error_message = "ListRagBucketPrefixes also covers runtime-artifacts and runtime-artifacts/* (the prefix the runtime artifact is uploaded to), so a listing under it is allowed for the roles that already list the other rag prefixes."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if st.Sid == "ListRagBucketPrefixes" && length(st.Condition.StringLike["s3:prefix"]) == 8]) == 1
    error_message = "Exactly eight prefix patterns: four prefixes, each with its sub-path pattern."
  }
}
