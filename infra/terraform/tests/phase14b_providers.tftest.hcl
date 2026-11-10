# Repair round 3 (Phase 14B): the Anthropic API for synthesis and Voyage AI for embeddings are the primary providers; Bedrock stays selectable.
# Every expectation is hand-derived from the shared contract in docs/agent-runs/phase-14/prompt.md ("Repair round 3 work order"):
#   - synthesis_provider anthropic (default): model claude-haiku-5-5, env SCHOLARCHAIN_SYNTHESIS_PROVIDER=anthropic, one EMPTY Secrets Manager
#     container scholarchain-<env>/anthropic-api-key injected as SCHOLARCHAIN_ANTHROPIC_API_KEY into query-api only;
#   - embedding_provider voyage (default): model and version tag voyage-4-lite, dimension 256, env SCHOLARCHAIN_EMBEDDING_PROVIDER=voyage, one EMPTY
#     container scholarchain-<env>/voyage-api-key injected as SCHOLARCHAIN_VOYAGE_API_KEY into semantic-service and embedding-worker only
#     (query-api makes no embedding call: modules/services/README.md, "Environment contract");
#   - each container exists only while its provider is selected; no secret VERSION, no secret_string, no key value anywhere in Terraform;
#   - the execution role may read exactly its provider ARN pattern (name plus the six random characters), the AWS-managed key means no kms:Decrypt;
#   - Bedrock invoke grants exist only for a purpose whose provider is bedrock; no Marketplace permission on any role;
#   - egress stays the single NAT and TCP 443.
# The mock and override header is copied from phase14b_gmain.tftest.hcl (a test file cannot import another file's mocks).
# All identifiers are synthetic (the account id is assembled in the variables block, so no 12-digit literal is stored in this file). Plan-only: never remove the mock_provider or run apply.

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

# ---- defaults: the primary providers -----------------------------------------------------------------------------------------

run "defaults_select_anthropic_and_voyage_with_the_contract_model_identifiers" {
  command = plan
  assert {
    condition     = output.provider_controls.synthesis_provider == "anthropic" && output.provider_controls.embedding_provider == "voyage"
    error_message = "Defaults: synthesis_provider anthropic, embedding_provider voyage."
  }
  assert {
    condition     = output.provider_controls.synthesis_model == "claude-haiku-5-5" && output.provider_controls.embedding_model == "voyage-4-lite" && output.provider_controls.embedding_model_version == "voyage-4-lite" && output.provider_controls.vector_dimension == 256
    error_message = "Primary providers: synthesis claude-haiku-5-5, embedding voyage-4-lite, version tag voyage-4-lite, dimension 256."
  }
  assert {
    condition     = output.provider_controls.bedrock_synthesis_model == null && output.provider_controls.bedrock_embedding_model == null
    error_message = "With both primary providers no Bedrock model id reaches the IAM module."
  }
}

run "each_primary_provider_creates_one_empty_secret_container_with_force_delete_and_the_managed_key" {
  command = plan
  assert {
    condition     = toset(keys(output.provider_controls.secrets)) == toset(["anthropic", "voyage"])
    error_message = "Exactly two secret containers exist by default: anthropic and voyage."
  }
  assert {
    condition     = output.provider_controls.secrets.anthropic.name == "scholarchain-course/anthropic-api-key" && output.provider_controls.secrets.voyage.name == "scholarchain-course/voyage-api-key"
    error_message = "Secret names are <name_prefix>/anthropic-api-key and <name_prefix>/voyage-api-key (the prefix the deployer's Secrets Manager statement scopes)."
  }
  assert {
    condition     = output.provider_controls.secrets.anthropic.recovery_window_in_days == 0 && output.provider_controls.secrets.voyage.recovery_window_in_days == 0
    error_message = "recovery_window_in_days 0: destroy is a force delete without a recovery window (cleanup revokes nothing it cannot delete)."
  }
  assert {
    condition     = output.provider_controls.secrets.anthropic.kms_key_id == null && output.provider_controls.secrets.voyage.kms_key_id == null
    error_message = "No customer key: the AWS-managed key aws/secretsmanager encrypts the containers, so the execution role needs no kms:Decrypt."
  }
  assert {
    condition     = alltrue([for k, s in output.provider_controls.secrets : s.tags.project == "scholarchain" && s.tags.environment == "course"])
    error_message = "The containers carry the project and environment tags (the deployer's resource-tag conditions and cleanup's tag inventory)."
  }
}

run "terraform_holds_no_secret_value_no_version_resource_and_no_secret_read_anywhere" {
  command = plan
  assert {
    condition = output.provider_controls != null && length([for f in concat(tolist(fileset(".", "*.tf")), tolist(fileset(".", "modules/**/*.tf"))) : f if anytrue([
      for needle in ["aws_secretsmanager_secret_version", "secret_string", "secret_binary", "data \"aws_secretsmanager", "aws_secretsmanager_secret_policy"] :
      strcontains(join("\n", [for l in split("\n", file(f)) : l if !startswith(trimspace(l), "#")]), needle)
    ])]) == 0
    error_message = "No aws_secretsmanager_secret_version, secret_string, secret_binary, secret policy or secretsmanager data source (outside comments) may exist in the main root or its modules: the human enters the key values."
  }
  assert {
    condition     = output.provider_controls != null && length(regexall("(?m)^resource \"aws_secretsmanager_secret\" \"", join("\n", [for f in concat(tolist(fileset(".", "*.tf")), tolist(fileset(".", "modules/**/*.tf"))) : file(f)]))) == 2
    error_message = "Exactly two aws_secretsmanager_secret resources are declared (anthropic, voyage)."
  }
  assert {
    condition     = !strcontains(jsonencode(output.provider_controls), "sk-") && !strcontains(jsonencode(output.provider_controls), "pa-")
    error_message = "No key-shaped string in the provider controls."
  }
}

# ---- IAM: the execution roles and the task roles -------------------------------------------------------------------------------

run "execution_roles_read_exactly_their_provider_secret_pattern_and_nothing_else_of_the_two" {
  command = plan
  assert {
    condition = [for st in jsondecode(output.iam_controls.execution_policies["query-api"]).Statement : st if st.Sid == "InjectProviderApiKey"] == [{
      Sid      = "InjectProviderApiKey", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
      Resource = ["arn:aws:secretsmanager:us-east-1:${var.aws_account_id}:secret:scholarchain-course/anthropic-api-key-??????"]
    }]
    error_message = "query-api's execution role reads exactly the Anthropic container (name pattern with the six random characters)."
  }
  assert {
    condition = alltrue([for s in ["semantic-service", "embedding-worker"] : [for st in jsondecode(output.iam_controls.execution_policies[s]).Statement : st if st.Sid == "InjectProviderApiKey"] == [{
      Sid      = "InjectProviderApiKey", Effect = "Allow", Action = ["secretsmanager:GetSecretValue"],
      Resource = ["arn:aws:secretsmanager:us-east-1:${var.aws_account_id}:secret:scholarchain-course/voyage-api-key-??????"]
    }]])
    error_message = "semantic-service and embedding-worker execution roles read exactly the Voyage container."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.execution_policies["graph-service"]).Statement : st if st.Sid == "InjectProviderApiKey"]) == 0
    error_message = "graph-service uses neither provider: its execution role gets no provider secret grant."
  }
  assert {
    condition     = alltrue([for s, p in output.iam_controls.execution_policies : !anytrue([for st in jsondecode(p).Statement : anytrue([for a in st.Action : startswith(a, "kms:")]) && st.Sid == "InjectProviderApiKey"])]) && alltrue([for s, p in output.iam_controls.execution_policies : !strcontains(p, "secret:*")])
    error_message = "No kms:Decrypt belongs to the provider key grant (the AWS-managed key needs none) and no wildcard secret ARN exists in any execution role."
  }
}

run "primary_providers_leave_no_bedrock_grant_and_no_marketplace_permission_on_any_role" {
  command = plan
  assert {
    condition     = alltrue([for s, p in output.iam_controls.task_policies : !strcontains(p, "bedrock")]) && alltrue([for s, p in output.iam_controls.execution_policies : !strcontains(p, "bedrock")])
    error_message = "With anthropic and voyage selected no task or execution role holds any bedrock action or ARN."
  }
  assert {
    condition     = alltrue([for s, p in merge(output.iam_controls.task_policies, output.iam_controls.execution_policies) : !strcontains(lower(p), "aws-marketplace") && !strcontains(lower(p), "marketplace")]) && !strcontains(lower(output.iam_controls.emr_data_policy), "marketplace") && !strcontains(lower(output.iam_controls.loader_policy), "marketplace")
    error_message = "No role of the main stack holds a Marketplace permission (Anthropic models on Bedrock are the reason a Marketplace grant would otherwise appear)."
  }
  assert {
    condition     = alltrue([for s, p in output.iam_controls.task_policies : !strcontains(p, "secretsmanager:")])
    error_message = "No task (application) role reads Secrets Manager: only the execution role injects the key at task start, so the key is never reachable by application code through the SDK."
  }
}

# ---- runtime environment and secret injection -------------------------------------------------------------------------------

run "aws_mode_exports_the_provider_switches_models_dimension_and_injects_the_two_keys" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }
  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_SYNTHESIS_PROVIDER"] == "anthropic" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL"] == "claude-haiku-5-5" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION"] == "claude-haiku-5-5"
    error_message = "query-api: SCHOLARCHAIN_SYNTHESIS_PROVIDER anthropic, synthesis model and version claude-haiku-5-5."
  }
  assert {
    condition = alltrue([for s in ["query-api", "semantic-service", "embedding-worker"] : {
      p = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_EMBEDDING_PROVIDER"]
      m = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_MODELS_EMBEDDING_MODEL"]
      v = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_EMBEDDING_MODEL_VERSION"]
      d = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_EMBEDDING_DIMENSION"]
    } == { p = "voyage", m = "voyage-4-lite", v = "voyage-4-lite", d = "256" }])
    error_message = "Every role that carries the embedding identity gets provider voyage, model voyage-4-lite, version tag voyage-4-lite and dimension 256."
  }
  assert {
    condition     = !contains(keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].environment : e.name => e.value }), "SCHOLARCHAIN_SYNTHESIS_PROVIDER") && !contains(keys({ for e in jsondecode(output.phase12b_controls.runtime.task_definitions["semantic-service"].container_definitions)[0].environment : e.name => e.value }), "SCHOLARCHAIN_SYNTHESIS_PROVIDER")
    error_message = "The synthesis switch belongs to query-api only (the only role that synthesizes)."
  }
  assert {
    condition     = [for x in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].secrets : x.name if x.name == "SCHOLARCHAIN_ANTHROPIC_API_KEY"] == ["SCHOLARCHAIN_ANTHROPIC_API_KEY"] && alltrue([for s in ["semantic-service", "embedding-worker"] : [for x in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].secrets : x.name if x.name == "SCHOLARCHAIN_VOYAGE_API_KEY"] == ["SCHOLARCHAIN_VOYAGE_API_KEY"]])
    error_message = "ECS `secrets` inject SCHOLARCHAIN_ANTHROPIC_API_KEY into query-api and SCHOLARCHAIN_VOYAGE_API_KEY into semantic-service and embedding-worker."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : !contains([for x in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].secrets : x.name], s == "query-api" ? "SCHOLARCHAIN_VOYAGE_API_KEY" : (s == "graph-service" ? "SCHOLARCHAIN_VOYAGE_API_KEY" : "SCHOLARCHAIN_ANTHROPIC_API_KEY"))]) && length([for x in jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].secrets : x if strcontains(x.name, "ANTHROPIC") || strcontains(x.name, "VOYAGE")]) == 0
    error_message = "A role gets only the key of the provider it calls: query-api no Voyage key, the embedding roles no Anthropic key, graph-service neither."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : !anytrue([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].environment : strcontains(e.name, "API_KEY") && (strcontains(e.name, "ANTHROPIC") || strcontains(e.name, "VOYAGE"))])])
    error_message = "A provider key name or value is never in `environment`: only in `secrets`."
  }
}

run "with_the_runtime_disabled_the_containers_exist_but_no_task_definition_references_them" {
  command = plan
  assert {
    condition     = length(output.provider_controls.secrets) == 2 && length(output.phase12b_controls.runtime.task_definitions) == 0
    error_message = "base-apply (runtime disabled): the two empty containers exist so the human can enter the values, and no task definition exists that would fail to start on an empty secret."
  }
}

# ---- Bedrock stays selectable -------------------------------------------------------------------------------------------------

run "bedrock_synthesis_only_removes_the_anthropic_container_and_grants_the_configured_model" {
  command = plan
  variables {
    synthesis_provider = "bedrock"
    synthesis_model_id = "anthropic.claude-synthetic-test-v1:0"
  }
  assert {
    condition     = toset(keys(output.provider_controls.secrets)) == toset(["voyage"]) && output.provider_controls.synthesis_model == "anthropic.claude-synthetic-test-v1:0"
    error_message = "Bedrock synthesis: no Anthropic container; the configured Bedrock model id is the synthesis model; the Voyage container stays."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if startswith(st.Sid, "InvokeConfiguredSynthesis")]) == 1 && length([for st in jsondecode(output.iam_controls.execution_policies["query-api"]).Statement : st if st.Sid == "InjectProviderApiKey"]) == 0
    error_message = "Bedrock synthesis: query-api has the Bedrock invoke grant and no provider key grant."
  }
  assert {
    condition     = alltrue([for s in ["semantic-service", "embedding-worker", "graph-service"] : !strcontains(output.iam_controls.task_policies[s], "bedrock")])
    error_message = "Only the purpose whose provider is Bedrock gets a Bedrock grant: the embedding roles (Voyage) have none."
  }
}

run "bedrock_embeddings_only_defaults_to_titan_and_removes_the_voyage_container" {
  command = plan
  variables {
    embedding_provider = "bedrock"
  }
  assert {
    condition     = toset(keys(output.provider_controls.secrets)) == toset(["anthropic"]) && output.provider_controls.embedding_model == "amazon.titan-embed-text-v2:0" && output.provider_controls.embedding_model_version == null
    error_message = "Bedrock embeddings: no Voyage container; the model defaults to Titan Text Embeddings V2; the version tag has no default."
  }
  assert {
    condition     = alltrue([for s in ["semantic-service", "embedding-worker"] : length([for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st if st.Sid == "InvokeConfiguredEmbeddingModel" && st.Resource == ["arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"]]) == 1 && length([for st in jsondecode(output.iam_controls.execution_policies[s]).Statement : st if st.Sid == "InjectProviderApiKey"]) == 0])
    error_message = "Bedrock embeddings: the embedding roles get exactly the in-region Titan grant and no provider key grant."
  }
  assert {
    condition     = !strcontains(output.iam_controls.task_policies["query-api"], "bedrock")
    error_message = "query-api (Anthropic synthesis) has no Bedrock grant."
  }
}

run "bedrock_for_both_creates_no_secret_container_and_no_provider_key_grant" {
  command = plan
  variables {
    synthesis_provider           = "bedrock"
    embedding_provider           = "bedrock"
    synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
    embedding_model_version      = "synthetic-pinned-version"
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }
  assert {
    condition     = length(output.provider_controls.secrets) == 0 && alltrue([for s, p in output.iam_controls.execution_policies : !strcontains(p, "InjectProviderApiKey")])
    error_message = "Both providers Bedrock: no container, no provider key grant."
  }
  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_SYNTHESIS_PROVIDER"] == "bedrock" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_EMBEDDING_PROVIDER"] == "bedrock" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_MODELS_EMBEDDING_MODEL"] == "amazon.titan-embed-text-v2:0"
    error_message = "Bedrock for both: the switches say bedrock and the embedding model is the Titan id."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : length([for x in jsondecode(output.phase12b_controls.runtime.task_definitions[s].container_definitions)[0].secrets : x if strcontains(x.name, "ANTHROPIC") || strcontains(x.name, "VOYAGE")]) == 0])
    error_message = "Bedrock for both: no provider key is injected anywhere."
  }
}

# ---- the permissions boundary still bounds every action when the primary providers are selected ----------------------------------

run "every_action_of_every_role_policy_stays_inside_the_boundary_without_the_bedrock_statement" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }

  # The deployer renders the boundary without the Bedrock statement (bedrock_enabled = false) when neither provider is Bedrock.
  assert {
    condition = alltrue([
      for doc in concat(values(output.iam_controls.task_policies), values(output.iam_controls.execution_policies), [output.iam_controls.loader_policy, output.iam_controls.emr_data_policy, output.phase12b_controls.workflow.producer_policy]) :
      alltrue([
        for a in flatten([for st in jsondecode(doc).Statement : st.Effect == "Allow" ? flatten([st.Action]) : []]) :
        anytrue([
          for b in flatten([for bs in jsondecode(templatefile("deployer/boundaries/runtime.json.tftpl", { acct = var.aws_account_id, region = var.aws_region, mp = "${var.project}-${var.environment}", env = var.environment, bedrock_enabled = false, bedrock_fm_arns = "" })).Statement : bs.Effect == "Allow" ? flatten([bs.Action]) : []]) :
          b == a || (endswith(b, "*") && startswith(a, trimsuffix(b, "*")))
        ])
      ])
    ])
    error_message = "With anthropic and voyage selected every role action (including the provider key GetSecretValue grants) is inside the runtime boundary rendered without any Bedrock statement."
  }
  assert {
    condition     = output.provider_controls != null && !strcontains(file("deployer/boundaries/runtime.json.tftpl"), "aws-marketplace") && !strcontains(lower(file("deployer/boundaries/runtime.json.tftpl")), "marketplace") && length(regexall("(?m)^%\\{ if bedrock_enabled ~\\}$", file("deployer/boundaries/runtime.json.tftpl"))) == 1
    error_message = "The boundary template has no Marketplace permission and exactly one conditional (Bedrock) block."
  }
}

# ---- guards ----------------------------------------------------------------------------------------------------------------------

run "an_unknown_synthesis_provider_is_rejected" {
  command = plan
  variables { synthesis_provider = "openai" }
  expect_failures = [var.synthesis_provider]
}

run "an_unknown_embedding_provider_is_rejected" {
  command = plan
  variables { embedding_provider = "cohere" }
  expect_failures = [var.embedding_provider]
}

run "anthropic_refuses_a_leftover_bedrock_synthesis_model_id" {
  command = plan
  variables { synthesis_model_id = "anthropic.claude-synthetic-test-v1:0" }
  expect_failures = [terraform_data.provider_guard]
}

run "voyage_refuses_a_leftover_bedrock_embedding_model_id" {
  command = plan
  variables { embedding_model_id = "amazon.titan-embed-text-v2:0" }
  expect_failures = [terraform_data.provider_guard]
}

run "voyage_refuses_a_version_tag_other_than_the_model_name" {
  command = plan
  variables { embedding_model_version = "synthetic-pinned-version" }
  expect_failures = [terraform_data.provider_guard]
}

run "voyage_with_a_dimension_other_than_256_is_refused" {
  command = plan
  variables { vector_dimension = 512 }
  expect_failures = [terraform_data.provider_guard, terraform_data.phase12b_guard]
}

run "the_aws_mode_with_bedrock_synthesis_and_no_model_id_is_still_refused" {
  command = plan
  variables {
    synthesis_provider           = "bedrock"
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    public_ingress_cidrs         = ["192.0.2.0/24"]
  }
  expect_failures = [terraform_data.phase12b_guard]
}

# ---- egress: the existing single NAT, TCP 443 --------------------------------------------------------------------------------------

run "egress_to_the_provider_apis_is_the_single_nat_on_tcp_443_and_nothing_new" {
  command = plan
  assert {
    condition     = output.network_controls.nat_gateway_count == 1 && length(output.network_controls.interface_services) == 0 && alltrue([for p in output.network_controls.https_egress_ports : p == 443])
    error_message = "Provider egress rides the one NAT gateway on TCP 443; no interface endpoint and no other egress port was added."
  }
  assert {
    condition     = output.provider_controls != null && can(regex("https_clients = toset\\(\\[\"query-api\", \"graph-service\", \"semantic-service\", \"embedding-worker\", \"emr\"\\]\\)", file("modules/network/main.tf"))) && can(regex("cidr_ipv4\\s*=\\s*\"0.0.0.0/0\"\\s*\\n\\s*ip_protocol\\s*=\\s*\"tcp\"\\s*\\n\\s*from_port\\s*=\\s*443", file("modules/network/main.tf")))
    error_message = "query-api, semantic-service and embedding-worker (the provider callers) hold the TCP 443 egress rule to 0.0.0.0/0 (modules/network/main.tf)."
  }
  assert {
    condition     = output.provider_controls != null && can(regex("assign_public_ip\\s*=\\s*false", file("modules/runtime/compute.tf"))) && can(regex("nat_gateway_id\\s*=\\s*aws_nat_gateway.course.id", file("modules/network/main.tf")))
    error_message = "Tasks have no public IP and the application route table's default route is the NAT gateway."
  }
}
