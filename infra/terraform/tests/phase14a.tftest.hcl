# Phase 14A (decision 14-3): the Bedrock grant with and without a cross-region inference profile. Every expectation is
# hand-derived from the AWS policy shape documented at
# https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html (profile ARN in the home region,
# foundation-model ARN per routed region, bedrock:InferenceProfileArn condition). All identifiers are synthetic mock fixtures
# (the model ID below is not a real model). No AWS client runs. Plan-only: never remove the mock_provider or run apply.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_efs_file_system" { defaults = { arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:file-system/fs-0123456789abcdef0", id = "fs-0123456789abcdef0" } }
  mock_resource "aws_efs_access_point" { defaults = { arn = "arn:aws:elasticfilesystem:us-east-2:111122223333:access-point/fsap-0123456789abcdef0", id = "fsap-0123456789abcdef0" } }
  mock_resource "aws_kms_key" {
    defaults = {
      arn    = "arn:aws:kms:us-east-2:111122223333:key/00000000-0000-0000-0000-000000000001"
      key_id = "00000000-0000-0000-0000-000000000001"
    }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::synthetic-phase12a-bucket", id = "synthetic-phase12a-bucket" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/synthetic-phase12a-table" }
  }
  mock_resource "aws_sqs_queue" {
    defaults = {
      arn = "arn:aws:sqs:us-east-2:111122223333:synthetic-phase12a-queue"
      id  = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-phase12a-queue"
      url = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-phase12a-queue"
    }
  }
  mock_resource "aws_sfn_state_machine" { defaults = { arn = "arn:aws:states:us-east-2:111122223333:stateMachine:scholarchain-course-embedding-dispatch" } }
  mock_resource "aws_iam_role" { defaults = { arn = "arn:aws:iam::111122223333:role/synthetic-phase12b-role" } }
  mock_resource "aws_s3vectors_vector_bucket" { defaults = { vector_bucket_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors" } }
  mock_resource "aws_neptune_cluster" { defaults = { cluster_resource_id = "cluster-synthetic-graph", endpoint = "synthetic.cluster.neptune.amazonaws.com", reader_endpoint = "synthetic.cluster-ro.neptune.amazonaws.com" } }
  mock_resource "aws_ecs_cluster" { defaults = { id = "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course" } }
  mock_resource "aws_ecs_task_definition" { defaults = { arn = "arn:aws:ecs:us-east-2:111122223333:task-definition/synthetic-service:1" } }
  mock_resource "aws_ecr_repository" { defaults = { arn = "arn:aws:ecr:us-east-2:111122223333:repository/synthetic-phase12b-repo", repository_url = "111122223333.dkr.ecr.us-east-2.amazonaws.com/synthetic-phase12b-repo" } }
  mock_resource "aws_lb" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:loadbalancer/app/synthetic/1234567890123456" } }
  mock_resource "aws_lb_target_group" { defaults = { arn = "arn:aws:elasticloadbalancing:us-east-2:111122223333:targetgroup/synthetic/1234567890123456" } }
  mock_resource "aws_service_discovery_service" { defaults = { arn = "arn:aws:servicediscovery:us-east-2:111122223333:service/srv-synthetic" } }
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
  aws_region                       = "us-east-2"
  aws_profile                      = "synthetic-not-a-real-profile"
  availability_zones               = ["us-east-2a", "us-east-2b"]
  deployment_trusted_principal_arn = "arn:aws:iam::111122223333:role/synthetic-architect"
  budget_limit_usd                 = 50 # Synthetic validation input, not the user's budget.
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["researcher-profile-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors/index/researcher-profile-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-community-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors/index/collaboration-community-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["paper-abstract-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors/index/paper-abstract-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["collaboration-path-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors/index/collaboration-path-v1" }
}
override_resource {
  target          = module.s3vectors.aws_s3vectors_index.document["topic-institution-summary-v1"]
  override_during = plan
  values          = { index_arn = "arn:aws:s3vectors:us-east-2:111122223333:bucket/synthetic-vectors/index/topic-institution-summary-v1" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.embedding
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-2:111122223333:synthetic-work", url = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-work", id = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-work" }
}
override_resource {
  target          = module.messaging.aws_sqs_queue.dead_letter
  override_during = plan
  values          = { arn = "arn:aws:sqs:us-east-2:111122223333:synthetic-dlq", url = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-dlq", id = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-dlq" }
}


# Distinct bucket ARNs so that a grant on the wrong bucket is visible (the shared header mock gives every bucket the same ARN).
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["raw"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-raw", id = "scholarchain-course-111122223333-raw" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["curated"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-curated", id = "scholarchain-course-111122223333-curated" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["graph"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-graph", id = "scholarchain-course-111122223333-graph" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["rag"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-rag", id = "scholarchain-course-111122223333-rag" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["artifacts"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-artifacts", id = "scholarchain-course-111122223333-artifacts" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["logs"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-logs", id = "scholarchain-course-111122223333-logs" }
}
override_resource {
  target          = module.datalake.aws_s3_bucket.zone["reports"]
  override_during = plan
  values          = { arn = "arn:aws:s3:::scholarchain-course-111122223333-reports", id = "scholarchain-course-111122223333-reports" }
}
# Distinct table ARNs for the same reason.
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["RunLedger"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-RunLedger" }
}
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["EntityLinkCache"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-EntityLinkCache" }
}
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["QuerySession"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-QuerySession" }
}
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["EvidenceBundle"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-EvidenceBundle" }
}
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["ArtifactRegistry"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-ArtifactRegistry" }
}
override_resource {
  target          = module.dynamodb.aws_dynamodb_table.table["ResearcherMetricCache"]
  override_during = plan
  values          = { arn = "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-ResearcherMetricCache" }
}

run "without_a_profile_the_grant_is_the_home_region_foundation_model_only" {
  command = plan
  variables { synthesis_model_id = "anthropic.claude-synthetic-test-v1:0" }

  assert {
    condition = alltrue([for s in ["semantic-service", "embedding-worker"] :
      [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st if startswith(st.Sid, "InvokeConfiguredEmbedding")] == [{ Sid = "InvokeConfiguredEmbeddingModel", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = ["arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v2:0"] }]
    ])
    error_message = "Without an embedding profile: exactly one statement, bedrock:InvokeModel on the us-east-2 Titan V2 foundation-model ARN and no condition (behavior unchanged)."
  }
  assert {
    condition     = [for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if startswith(st.Sid, "InvokeConfiguredSynthesis")] == [{ Sid = "InvokeConfiguredSynthesisModel", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = ["arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-synthetic-test-v1:0"] }]
    error_message = "Without a synthesis profile: exactly one statement on the home-region foundation-model ARN."
  }
  assert {
    condition     = !anytrue([for s in ["query-api", "semantic-service", "embedding-worker"] : strcontains(output.iam_controls.task_policies[s], "inference-profile")])
    error_message = "No inference-profile ARN anywhere when no profile is configured."
  }
}

run "a_synthesis_profile_adds_the_profile_arn_and_one_conditioned_model_arn_per_routed_region" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
  }

  assert {
    condition = [for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if st.Sid == "InvokeConfiguredSynthesisProfile"] == [{
      Sid      = "InvokeConfiguredSynthesisProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"],
      Resource = ["arn:aws:bedrock:us-east-2:111122223333:inference-profile/us.anthropic.claude-synthetic-test-v1:0"]
    }]
    error_message = "The profile statement grants bedrock:InvokeModel on exactly the home-region, account-scoped profile ARN."
  }
  assert {
    condition = [for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if st.Sid == "InvokeConfiguredSynthesisModelViaProfile"] == [{
      Sid = "InvokeConfiguredSynthesisModelViaProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"],
      Resource = [
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-synthetic-test-v1:0",
        "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-synthetic-test-v1:0",
        "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-synthetic-test-v1:0",
      ]
      Condition = { StringEquals = { "bedrock:InferenceProfileArn" = "arn:aws:bedrock:us-east-2:111122223333:inference-profile/us.anthropic.claude-synthetic-test-v1:0" } }
    }]
    error_message = "One foundation-model ARN per routed region, each usable only through the profile (bedrock:InferenceProfileArn equals the profile ARN)."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if startswith(st.Sid, "InvokeConfiguredSynthesis")]) == 2
    error_message = "Exactly two synthesis statements for a geographic profile (no unconditioned model statement, no global statement)."
  }
  assert {
    condition     = !strcontains(output.iam_controls.task_policies["query-api"], "InvokeModelWithResponseStream")
    error_message = "Streaming is not granted: modules/rag calls Converse, never ConverseStream or InvokeModelWithResponseStream."
  }
}

run "query_api_gets_only_the_synthesis_grant_and_the_embedding_services_only_the_embedding_grant" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
  }

  assert {
    condition     = !strcontains(output.iam_controls.task_policies["query-api"], "titan-embed") && alltrue([for s in ["semantic-service", "embedding-worker"] : !strcontains(output.iam_controls.task_policies[s], "anthropic") && !strcontains(output.iam_controls.task_policies[s], "inference-profile")])
    error_message = "query-api never gets the embedding model; semantic-service and embedding-worker never get the synthesis model or its profile."
  }
  assert {
    condition     = alltrue([for s in ["graph-service"] : !strcontains(output.iam_controls.task_policies[s], "bedrock")])
    error_message = "graph-service has no Bedrock grant at all."
  }
  assert {
    condition     = alltrue([for s in ["semantic-service", "embedding-worker"] : [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st.Sid if startswith(st.Sid, "InvokeConfigured")] == ["InvokeConfiguredEmbeddingModel"]])
    error_message = "The embedding services keep exactly the one in-region Titan statement."
  }
}

run "an_embedding_profile_reaches_only_the_embedding_services" {
  command = plan
  variables {
    embedding_model_id                  = "amazon.synthetic-embed-v9:0"
    embedding_inference_profile_id      = "us.amazon.synthetic-embed-v9:0"
    embedding_inference_profile_regions = ["us-east-2", "us-west-2"]
  }

  assert {
    condition = alltrue([for s in ["semantic-service", "embedding-worker"] :
      [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st.Resource if startswith(st.Sid, "InvokeConfiguredEmbedding")] == [
        ["arn:aws:bedrock:us-east-2:111122223333:inference-profile/us.amazon.synthetic-embed-v9:0"],
        ["arn:aws:bedrock:us-east-2::foundation-model/amazon.synthetic-embed-v9:0", "arn:aws:bedrock:us-west-2::foundation-model/amazon.synthetic-embed-v9:0"],
      ]
    ])
    error_message = "The embedding profile grant is the profile ARN plus one model ARN per routed region, for both embedding services."
  }
  assert {
    condition     = !strcontains(output.iam_controls.task_policies["query-api"], "bedrock") && !strcontains(output.iam_controls.task_policies["graph-service"], "bedrock")
    error_message = "query-api and graph-service get no embedding grant."
  }
}

run "a_global_profile_adds_the_region_less_model_arn_with_an_unspecified_region_condition" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "global.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2"]
  }

  assert {
    condition = [for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if st.Sid == "InvokeConfiguredSynthesisModelViaGlobalProfile"] == [{
      Sid       = "InvokeConfiguredSynthesisModelViaGlobalProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"],
      Resource  = ["arn:aws:bedrock:::foundation-model/anthropic.claude-synthetic-test-v1:0"]
      Condition = { StringEquals = { "aws:RequestedRegion" = "unspecified", "bedrock:InferenceProfileArn" = "arn:aws:bedrock:us-east-2:111122223333:inference-profile/global.anthropic.claude-synthetic-test-v1:0" } }
    }]
    error_message = "A global.* profile needs the region-less model ARN, conditioned on the profile and aws:RequestedRegion = unspecified (AWS global cross-region inference policy)."
  }
}

run "bedrock_statements_never_use_wildcards" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
  }

  assert {
    condition = alltrue([for s in ["query-api", "semantic-service", "embedding-worker"] :
      alltrue([for st in jsondecode(output.iam_controls.task_policies[s]).Statement :
        !anytrue([for a in st.Action : startswith(a, "bedrock:")]) || (alltrue([for a in st.Action : !strcontains(a, "*")]) && alltrue([for r in st.Resource : !strcontains(r, "*")]))
      ])
    ])
    error_message = "Bedrock actions and resources stay explicit: no wildcard action, no wildcard region or model."
  }
}

run "a_profile_without_a_model_is_rejected" {
  command = plan
  variables {
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_id]
}

run "a_profile_id_that_is_not_prefix_dot_model_id_is_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-other-v1:0"
    synthesis_inference_profile_regions = ["us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_id]
}

run "an_unknown_geographic_prefix_is_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "mars.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_id]
}

run "a_wildcard_profile_id_is_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.*"
    synthesis_inference_profile_regions = ["us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_id]
}

run "an_invalid_region_name_is_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2", "*"]
  }
  expect_failures = [var.synthesis_inference_profile_regions]
}

run "duplicate_regions_are_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2", "us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_regions]
}

run "a_geographic_profile_without_routed_regions_is_rejected" {
  command = plan
  variables {
    synthesis_model_id             = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id = "us.anthropic.claude-synthetic-test-v1:0"
  }
  expect_failures = [var.synthesis_inference_profile_regions]
}

run "routed_regions_that_omit_the_home_region_are_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-west-2"]
  }
  expect_failures = [var.synthesis_inference_profile_regions]
}

run "routed_regions_without_a_profile_are_rejected" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-synthetic-test-v1:0"
    synthesis_inference_profile_regions = ["us-east-2"]
  }
  expect_failures = [var.synthesis_inference_profile_regions]
}

run "an_invalid_embedding_profile_is_rejected" {
  command = plan
  variables {
    embedding_inference_profile_id      = "us.amazon.titan-embed-text-v2:0"
    embedding_inference_profile_regions = ["us-east-2"]
    embedding_model_id                  = null
  }
  expect_failures = [var.embedding_inference_profile_id]
}

# ---- Task 3: the four EMR step programs, the private tfvars example, and the guard that depends on them ------------------

run "the_tfvars_example_carries_exactly_the_manifest_hashes_for_the_four_step_programs" {
  command = plan

  assert {
    condition     = var.project == "scholarchain" && length(jsondecode(file("emr-step-programs.json")).programs) == 4 && alltrue([for n, sha in jsondecode(file("emr-step-programs.json")).programs : strcontains(file("environments/course.local.tfvars.example"), "${jsondecode(file("emr-step-programs.json")).bin_dir}/${n}\"") && strcontains(file("environments/course.local.tfvars.example"), "sha256 = \"${sha}\"")])
    error_message = "environments/course.local.tfvars.example must list all four step programs with the sha256 and destination of infra/terraform/emr-step-programs.json (regenerate with python3 -I scripts/lib/pipeline.py step-manifest)."
  }
}

run "the_tfvars_example_holds_placeholders_only" {
  command = plan

  assert {
    condition     = var.project == "scholarchain" && !can(regex("[0-9]{12}", replace(replace(file("environments/course.local.tfvars.example"), "/[0-9a-f]{64}/", ""), "<12-digit-account-id>", ""))) && !can(regex("@", file("environments/course.local.tfvars.example"))) && !can(regex("AKIA|ASIA|BEGIN [A-Z ]*PRIVATE KEY|aws_secret|password *=", file("environments/course.local.tfvars.example")))
    error_message = "The example must hold no account ID, e-mail address, key material or secret value."
  }
  assert {
    condition     = var.project == "scholarchain" && alltrue([for v in ["aws_account_id", "availability_zones", "deployment_trusted_principal_arn", "budget_limit_usd", "neptune_enabled", "neptune_engine_version", "neptune_parameter_family", "synthesis_model_id", "synthesis_inference_profile_id", "synthesis_inference_profile_regions", "runtime_enabled", "runtime_composition_verified", "service_secret_bindings", "service_secret_arns", "public_ingress_cidrs", "https_certificate_arn", "alarm_notification_arns", "emr_config", "emr_service_policy_json", "image_revision", "aws_region", "aws_profile", "extra_artifacts", "embedding_model_version", "semantic_index_name", "embedding_text_prefix"] : strcontains(file("environments/course.local.tfvars.example"), v)])
    error_message = "The example must mention every variable the human supplies for the base and runtime plans."
  }
  assert {
    condition     = var.project == "scholarchain" && alltrue([for line in split("\n", file("environments/course.local.tfvars.example")) : !startswith(trimspace(line), "#") && trimspace(line) != "" ? can(regex("<[^>]+>", line)) || !can(regex("^[a-z_]+ *= *\"", line)) || can(regex("^(synthesis_model_id|synthesis_inference_profile_id|embedding_model_id|semantic_index_name|embedding_text_prefix) *= *\"[a-z0-9.:-]+\"$", trimspace(line))) : true])
    error_message = "Every uncommented string assignment in the example is a <placeholder>, except the documented model and inference-profile IDs (accounts, e-mail addresses and keys stay forbidden by the assertions above)."
  }
}

run "emr_disabled_needs_no_step_programs" {
  command = plan
  # Default: emr_config.enabled = false. The guard on extra_artifacts holds only when enabled.
  assert {
    condition     = var.emr_config.enabled == false && length(var.emr_config.extra_artifacts) == 0
    error_message = "With EMR disabled the plan needs no step programs."
  }
}

run "emr_enabled_without_the_step_programs_is_refused_by_the_guard" {
  command = plan
  variables {
    emr_config              = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "emr_enabled_with_one_step_program_missing_is_refused" {
  command = plan
  variables {
    emr_config = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222",
    extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" } if n != "sc-step.sh"] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "emr_enabled_with_the_four_step_programs_of_the_example_is_accepted" {
  command = plan
  variables {
    emr_config = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222",
      extra_artifacts = [
        { uri = "s3://scholarchain-course-111122223333-artifacts/steps/sc-ceiling-check.py", sha256 = "57e9543cd94d5924bfb4bb8cec150ad755ba251ee5b6822275d9bc7a56d10b5c", dest = "/opt/scholarchain-spike/bin/sc-ceiling-check.py" },
        { uri = "s3://scholarchain-course-111122223333-artifacts/steps/sc-class-origin-verify.py", sha256 = "5df9197a60fe41530859377518609b67c70eec60c93c8256e6742ad5ffd17a79", dest = "/opt/scholarchain-spike/bin/sc-class-origin-verify.py" },
        { uri = "s3://scholarchain-course-111122223333-artifacts/steps/sc-render-spark-config.py", sha256 = "5d606d4883a0d4e4d869ff7f69ab56317743a4912940ac34e5c80337a8fa056c", dest = "/opt/scholarchain-spike/bin/sc-render-spark-config.py" },
        { uri = "s3://scholarchain-course-111122223333-artifacts/steps/sc-step.sh", sha256 = "ad7258d1221344de2b065bff18dc5d21356a1fb71b52e21dc52b47e499b99ed3", dest = "/opt/scholarchain-spike/bin/sc-step.sh" },
    ] }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.cluster != null
    error_message = "The four step programs with the pinned hashes satisfy the guard."
  }
}

run "the_example_emr_service_policy_passes_the_variable_validation_once_placeholders_are_filled" {
  command = plan
  variables {
    emr_service_policy_json = replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", "us-east-2"), "<12-digit-account-id>", "111122223333"), "<environment>", "course")
  }
  assert {
    condition     = length(jsondecode(var.emr_service_policy_json).Statement) == 13
    error_message = "The example policy has thirteen statements and passes the no-wildcard-action, concrete-ARN validation of emr_service_policy_json."
  }
}

run "an_example_policy_with_a_wildcard_action_is_refused" {
  command = plan
  variables {
    emr_service_policy_json = replace(replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", "us-east-2"), "<12-digit-account-id>", "111122223333"), "<environment>", "course"), "ec2:TerminateInstances", "ec2:Terminate*")
  }
  expect_failures = [var.emr_service_policy_json]
}

run "the_example_emr_service_policy_actions_are_exactly_the_set_the_deployer_boundary_is_tested_against" {
  command = plan

  # Keep identical with the list in deployer/tests/deployer.tftest.hcl (p14_the_emr_service_boundary_covers_...).
  assert {
    condition     = var.project == "scholarchain" && toset(distinct(flatten([for st in jsondecode(file("environments/emr-service-policy.json.example")).Statement : st.Action]))) == toset(["ec2:CreateNetworkInterface", "ec2:RunInstances", "ec2:CreateFleet", "ec2:DeleteNetworkInterface", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances", "ec2:CreateTags", "ec2:DeleteTags", "ec2:DescribeAccountAttributes", "ec2:DescribeCapacityReservations", "ec2:DescribeDhcpOptions", "ec2:DescribeImages", "ec2:DescribeInstances", "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeLaunchTemplates", "ec2:DescribeNetworkAcls", "ec2:DescribeNetworkInterfaces", "ec2:DescribePlacementGroups", "ec2:DescribeRouteTables", "ec2:DescribeSecurityGroups", "ec2:DescribeSubnets", "ec2:DescribeVolumes", "ec2:DescribeVolumeStatus", "ec2:DescribeVpcAttribute", "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcs", "ec2:CreateSecurityGroup", "ec2:AuthorizeSecurityGroupEgress", "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "iam:PassRole"])
    error_message = "The example EMR service policy changed its action set: update the list in this test and in the deployer test, and check the EMR boundary in deployer/phase14_main.tf."
  }
}

# ---- D1: permissions boundaries on all seven roles, and a test that no role policy exceeds its boundary --------------------

run "every_role_carries_the_boundary_the_deployer_root_creates_for_it" {
  command = plan

  # Naming consistency: the deployer root creates scholarchain-<environment>-permissions-boundary and
  # scholarchain-<environment>-emr-service-boundary (deployer/phase14_main.tf; its own tests assert the same literals).
  assert {
    condition     = var.project == "scholarchain" && strcontains(file("deployer/phase14_main.tf"), "m_boundary_runtime_name = \"$${local.mp}-permissions-boundary\"") && strcontains(file("deployer/phase14_main.tf"), "m_boundary_emr_name     = \"$${local.mp}-emr-service-boundary\"") && strcontains(file("deployer/phase14_main.tf"), "mp = \"scholarchain-$${var.main_environment}\"")
    error_message = "The deployer root must keep the boundary naming scheme scholarchain-<environment>-permissions-boundary / -emr-service-boundary."
  }
  assert {
    condition = output.iam_controls.role_boundaries == {
      "task-query-api"             = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "task-graph-service"         = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "task-semantic-service"      = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "task-embedding-worker"      = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "execution-query-api"        = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "execution-graph-service"    = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "execution-semantic-service" = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      "execution-embedding-worker" = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      neptune_loader               = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      emr_ec2                      = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      deployment                   = "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
      emr_service                  = "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"
    }
    error_message = "Eleven identity roles carry the runtime boundary and the EMR service role carries the EMR service boundary."
  }
  assert {
    condition     = output.phase12b_controls.workflow.boundary == "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary"
    error_message = "The Step Functions producer role carries the runtime boundary."
  }
}

run "every_action_of_every_role_policy_is_allowed_by_that_roles_boundary" {
  command = plan
  variables {
    emr_config                          = { enabled = true, runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://scholarchain-course-111122223333-artifacts/bootstrap/bootstrap.sh", bootstrap_sha256 = "1111111111111111111111111111111111111111111111111111111111111111", runtime_archive_uri = "s3://scholarchain-course-111122223333-artifacts/runtime/scholarchain-runtime.tgz", job_jar_uri = "s3://scholarchain-course-111122223333-artifacts/jobs/scholarchain-job.jar", job_jar_sha256 = "2222222222222222222222222222222222222222222222222222222222222222", extra_artifacts = [for n, s in jsondecode(file("emr-step-programs.json")).programs : { uri = "s3://scholarchain-course-111122223333-artifacts/steps/${n}", sha256 = s, dest = "/opt/scholarchain-spike/bin/${n}" }] }
    emr_service_policy_json             = replace(replace(replace(file("environments/emr-service-policy.json.example"), "<region>", "us-east-2"), "<12-digit-account-id>", "111122223333"), "<environment>", "course")
    neptune_enabled                     = true
    neptune_engine_version              = "1.4.5.1"
    neptune_parameter_family            = "neptune1.4"
    synthesis_model_id                  = "anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
    service_secret_bindings             = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => { SCHOLARCHAIN_API_KEY_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}" } }
  }

  # Wildcard-aware, action-level matching: a boundary action matches itself or, when it ends in "*", any action with that prefix.
  # Runtime boundary: 4 task policies, 4 execution policies, Neptune loader, EMR instance role (data + node policy), producer.
  assert {
    condition = alltrue([
      for doc in concat(values(output.iam_controls.task_policies), values(output.iam_controls.execution_policies), [output.iam_controls.loader_policy, output.iam_controls.emr_data_policy, output.phase12b_controls.emr.node_policy, output.phase12b_controls.workflow.producer_policy]) :
      alltrue([
        for a in flatten([for st in jsondecode(doc).Statement : st.Effect == "Allow" ? flatten([st.Action]) : []]) :
        anytrue([
          for b in flatten([for bs in jsondecode(templatefile("deployer/boundaries/runtime.json.tftpl", { acct = var.aws_account_id, region = var.aws_region, mp = "${var.project}-${var.environment}", env = var.environment, bedrock_fm_arns = join(", ", [for r in ["us-east-1", "us-east-2", "us-west-2"] : jsonencode("arn:aws:bedrock:${r}::foundation-model/*")]) })).Statement : bs.Effect == "Allow" ? flatten([bs.Action]) : []]) :
          b == a || (endswith(b, "*") && startswith(a, trimsuffix(b, "*")))
        ])
      ])
    ])
    error_message = "A runtime-boundary role has a policy action that its boundary (deployer/boundaries/runtime.json.tftpl) does not allow: the role would fail at runtime or the boundary is stale."
  }
  # EMR service boundary: the supplied control-plane policy (the reviewed example) and the fixed EBS-key policy.
  assert {
    condition = alltrue([
      for doc in [output.iam_controls.emr_control_policy, output.iam_controls.emr_disk_encryption.policy] :
      alltrue([
        for a in flatten([for st in jsondecode(doc).Statement : st.Effect == "Allow" ? flatten([st.Action]) : []]) :
        anytrue([
          for b in flatten([for bs in jsondecode(templatefile("deployer/boundaries/emr-service.json.tftpl", { acct = var.aws_account_id, region = var.aws_region, mp = "${var.project}-${var.environment}", env = var.environment, bedrock_fm_arns = "" })).Statement : bs.Effect == "Allow" ? flatten([bs.Action]) : []]) :
          b == a || (endswith(b, "*") && startswith(a, trimsuffix(b, "*")))
        ])
      ])
    ])
    error_message = "The EMR service role has a policy action that the EMR service boundary (deployer/boundaries/emr-service.json.tftpl) does not allow."
  }
  # Not vacuous: the policies under test really contain the actions that matter.
  assert {
    condition = alltrue([
      for a in ["secretsmanager:GetSecretValue", "neptune-db:ReadDataViaQuery", "elasticfilesystem:ClientMount", "bedrock:InvokeModel", "sqs:SendMessage", "s3vectors:PutVectors", "s3:DeleteObject", "s3:ListBucket", "ecr:BatchGetImage", "logs:PutLogEvents", "dynamodb:UpdateItem", "elasticmapreduce:PutAutoTerminationPolicy"] :
      contains(flatten([for doc in concat(values(output.iam_controls.task_policies), values(output.iam_controls.execution_policies), [output.iam_controls.loader_policy, output.iam_controls.emr_data_policy, output.phase12b_controls.emr.node_policy, output.phase12b_controls.workflow.producer_policy]) : [for st in jsondecode(doc).Statement : flatten([st.Action])]]), a)
    ]) && length(flatten([for st in jsondecode(output.iam_controls.emr_control_policy).Statement : flatten([st.Action])])) > 20
    error_message = "The role policies under test must contain the representative actions (the test must not pass on empty policies)."
  }
}

# ---- D2: EMR managed-policies tag on the EMR network, and only there ---------------------------------------------------------

run "emr_tag_is_on_the_application_subnets_the_emr_node_group_and_the_service_access_group_only" {
  command = plan

  assert {
    condition     = length(output.network_controls.tags.application_subnets) == 2 && alltrue([for t in output.network_controls.tags.application_subnets : t["for-use-with-amazon-emr-managed-policies"] == "true"])
    error_message = "Both application subnets must carry for-use-with-amazon-emr-managed-policies = \"true\" exactly."
  }
  assert {
    condition     = output.network_controls.tags.role_groups["emr"]["for-use-with-amazon-emr-managed-policies"] == "true" && output.network_controls.tags.emr_service_access["for-use-with-amazon-emr-managed-policies"] == "true"
    error_message = "The EMR node group and the EMR service-access group must carry the tag with the exact value \"true\"."
  }
  assert {
    condition     = alltrue([for k, t in output.network_controls.tags.role_groups : k == "emr" || !contains(keys(t), "for-use-with-amazon-emr-managed-policies")]) && length(output.network_controls.tags.role_groups) == 8
    error_message = "No other role security group (alb, query-api, graph-service, semantic-service, embedding-worker, neptune, endpoints) may carry the EMR tag."
  }
  assert {
    condition     = alltrue([for t in concat(output.network_controls.tags.public_subnets, output.network_controls.tags.data_subnets, [output.network_controls.tags.vpc]) : !contains(keys(t), "for-use-with-amazon-emr-managed-policies")])
    error_message = "Public subnets, data subnets and the VPC must not carry the EMR tag (the cluster launches into an application subnet; the Neptune data subnets stay out of EMR's reach)."
  }
}

# ---- Synthesis model example (Claude Haiku 4.5), exactly the documented values ---------------------------------------------

run "the_documented_haiku_4_5_example_values_produce_the_expected_arns" {
  command = plan
  variables {
    synthesis_model_id                  = "anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
    embedding_model_id                  = "amazon.titan-embed-text-v2:0"
  }

  assert {
    condition = [for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : st if startswith(st.Sid, "InvokeConfiguredSynthesis")] == [
      {
        Sid      = "InvokeConfiguredSynthesisProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"],
        Resource = ["arn:aws:bedrock:us-east-2:111122223333:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"]
      },
      {
        Sid = "InvokeConfiguredSynthesisModelViaProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"],
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
          "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        ]
        Condition = { StringEquals = { "bedrock:InferenceProfileArn" = "arn:aws:bedrock:us-east-2:111122223333:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0" } }
      },
    ]
    error_message = "Haiku 4.5: the us-east-2 profile ARN, and the three foundation-model ARNs carrying the InferenceProfileArn condition."
  }
  assert {
    condition     = alltrue([for s in ["semantic-service", "embedding-worker"] : [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st.Resource if startswith(st.Sid, "InvokeConfigured")] == [["arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v2:0"]]])
    error_message = "Titan Text Embeddings V2 stays in-region with no profile for the embedding services."
  }
}

# ---- Repair round 1 (F2): key administration lives in the key policy; the default security group is not adopted -------------------

run "the_main_stack_key_policy_grants_the_deployer_role_exactly_its_administration_and_nothing_else" {
  command = plan

  # Statements: account-root IAM delegation (kept: lockout-safety and break-glass path, and the runtime roles use it), the S3 Vectors
  # indexing service decrypt, and three statements naming the deployer role by ARN built from the account ID and the fixed role name.
  assert {
    condition     = length(jsondecode(output.iam_controls.kms_policy).Statement) == 5 && toset([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Sid]) == toset(["EnableExplicitAccountIamDelegationForThisKey", "AllowS3VectorsServicePrincipal", "DeployerAdministersThisKey", "DeployerUsesThisKeyOnlyThroughServices", "DeployerGrantsForAwsResourcesOnly"])
    error_message = "The key policy has exactly five statements."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(output.iam_controls.kms_policy).Statement :
      !startswith(st.Sid, "Deployer") || (st.Effect == "Allow" && st.Principal == { AWS = "arn:aws:iam::111122223333:role/scholarchain-deployer" } && st.Resource == "*" && alltrue([for a in st.Action : startswith(a, "kms:") && !strcontains(a, "*")]))
    ])
    error_message = "The three deployer statements name exactly the deployer role ARN, with enumerated kms actions."
  }
  assert {
    condition     = toset([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Action if st.Sid == "DeployerAdministersThisKey"][0]) == toset(["kms:DescribeKey", "kms:GetKeyPolicy", "kms:PutKeyPolicy", "kms:GetKeyRotationStatus", "kms:EnableKeyRotation", "kms:DisableKeyRotation", "kms:ListResourceTags", "kms:TagResource", "kms:UntagResource", "kms:UpdateKeyDescription", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias"])
    error_message = "The deployer administers the key with exactly these fifteen actions."
  }
  assert {
    condition     = toset([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Action if st.Sid == "DeployerUsesThisKeyOnlyThroughServices"][0]) == toset(["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext", "kms:ReEncryptFrom", "kms:ReEncryptTo"]) && toset([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Condition.StringEquals["kms:ViaService"] if st.Sid == "DeployerUsesThisKeyOnlyThroughServices"][0]) == toset([for s in ["s3", "dynamodb", "sqs", "ecr", "elasticfilesystem", "rds", "states", "elasticmapreduce", "s3vectors"] : "${s}.us-east-2.amazonaws.com"])
    error_message = "Data-key use only through the nine services in the region."
  }
  assert {
    condition     = toset([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Action if st.Sid == "DeployerGrantsForAwsResourcesOnly"][0]) == toset(["kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant", "kms:RetireGrant"]) && [for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Condition if st.Sid == "DeployerGrantsForAwsResourcesOnly"][0] == { Bool = { "kms:GrantIsForAWSResource" = "true" } }
    error_message = "Grants only for AWS resources."
  }
  # Lockout-check shape (https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html): the calling principal (the deployer role) can
  # call PutKeyPolicy again, and so can the account root.
  assert {
    condition     = anytrue([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Sid == "DeployerAdministersThisKey" && contains(st.Action, "kms:PutKeyPolicy")]) && anytrue([for st in jsondecode(output.iam_controls.kms_policy).Statement : st.Sid == "EnableExplicitAccountIamDelegationForThisKey" && st.Principal == { AWS = "arn:aws:iam::111122223333:root" } && contains(st.Action, "kms:PutKeyPolicy")])
    error_message = "Both the deployer role and the account root can call PutKeyPolicy (lockout safety check)."
  }
  assert {
    condition     = alltrue([for st in jsondecode(output.iam_controls.kms_policy).Statement : try(st.Principal.AWS, "") != "*" && !contains(try(flatten([st.Principal.AWS]), []), "*")])
    error_message = "No statement may name a wildcard principal."
  }
  # The fixed deployer role name matches the deployer root's default.
  assert {
    condition     = var.project == "scholarchain" && strcontains(file("deployer/variables.tf"), "default     = \"scholarchain-deployer\"")
    error_message = "The key policy names scholarchain-deployer; the deployer root's default role_name must stay the same."
  }
}

run "the_vpc_default_security_group_is_not_managed_and_no_adoption_statement_remains" {
  command = plan

  assert {
    condition     = var.project == "scholarchain" && !strcontains(file("modules/network/main.tf"), "resource \"aws_default_security_group\"") && !strcontains(file("deployer/phase14_main.tf"), "Ec2AdoptedDefaultSg")
    error_message = "modules/network must not adopt the default security group, and the deployer set must not carry adoption statements (F2)."
  }
}

# ---- Repair round 1 (F1, infra part): the aws-mode task environment and two task-role grants ------------------------------------
# Expectations are written by hand from modules/services/README.md ("Environment contract") and AwsConfig.scala, not read back.

run "aws_mode_environment_per_role_is_exactly_the_service_contract" {
  command = plan
  variables {
    runtime_enabled                     = true
    runtime_composition_verified        = true
    image_revision                      = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    neptune_enabled                     = true
    neptune_engine_version              = "1.4.6.3"
    neptune_parameter_family            = "neptune1.4"
    synthesis_model_id                  = "anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_id      = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    synthesis_inference_profile_regions = ["us-east-1", "us-east-2", "us-west-2"]
    embedding_model_version             = "synthetic-pinned-version"
    service_secret_bindings = {
      "query-api" = {
        SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-q-api-AbCdEf"
        SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-q-hash-AbCdEf"
        SCHOLARCHAIN_INTERNAL_TOKEN        = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-q-token-AbCdEf"
      }
      "graph-service" = {
        SCHOLARCHAIN_GRAPH_CURSOR_KEY      = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-g-cursor-AbCdEf"
        SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-g-api-AbCdEf"
        SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-g-hash-AbCdEf"
      }
      "semantic-service" = {
        SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-s-api-AbCdEf"
        SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-s-hash-AbCdEf"
      }
      "embedding-worker" = {
        SCHOLARCHAIN_API_KEY_SHA256        = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-w-api-AbCdEf"
        SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-w-hash-AbCdEf"
      }
    }
  }

  # Tables and index: every aws role.
  assert {
    condition = alltrue([
      for svc in ["query-api", "graph-service", "semantic-service", "embedding-worker"] :
      alltrue([
        for k, v in {
          SCHOLARCHAIN_SERVICE_MODE                           = "aws"
          AWS_REGION                                          = "us-east-2"
          SCHOLARCHAIN_HTTP_HOST                              = "0.0.0.0"
          SCHOLARCHAIN_HTTP_PORT                              = "8080"
          SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER              = "scholarchain-course-RunLedger"
          SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE       = "scholarchain-course-EntityLinkCache"
          SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION           = "scholarchain-course-QuerySession"
          SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE         = "scholarchain-course-EvidenceBundle"
          SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY       = "scholarchain-course-ArtifactRegistry"
          SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE = "scholarchain-course-ResearcherMetricCache"
          SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX           = "by-idempotency-key"
        } :
        { for e in jsondecode(output.phase12b_controls.runtime.task_definitions[svc].container_definitions)[0].environment : e.name => e.value }[k] == v
      ])
    ])
    error_message = "Every aws role receives mode aws, the region, host and port, the six table names and the QuerySession index name."
  }
  assert {
    condition = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value } == {
      SCHOLARCHAIN_SERVICE_MODE                           = "aws"
      AWS_REGION                                          = "us-east-2"
      SCHOLARCHAIN_HTTP_HOST                              = "0.0.0.0"
      SCHOLARCHAIN_HTTP_PORT                              = "8080"
      SCHOLARCHAIN_GRAPH_BASE_URI                         = "http://graph-service.scholarchain-course.internal:8080"
      SCHOLARCHAIN_SEMANTIC_BASE_URI                      = "http://semantic-service.scholarchain-course.internal:8080"
      SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER              = "scholarchain-course-RunLedger"
      SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE       = "scholarchain-course-EntityLinkCache"
      SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION           = "scholarchain-course-QuerySession"
      SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE         = "scholarchain-course-EvidenceBundle"
      SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY       = "scholarchain-course-ArtifactRegistry"
      SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE = "scholarchain-course-ResearcherMetricCache"
      SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX           = "by-idempotency-key"
      SCHOLARCHAIN_STORAGE_RAG_BUCKET                     = "scholarchain-course-111122223333-rag"
      SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL                 = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
      SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION                = "anthropic.claude-haiku-4-5-20251001-v1:0"
      SCHOLARCHAIN_MODELS_EMBEDDING_MODEL                 = "amazon.titan-embed-text-v2:0"
      SCHOLARCHAIN_EMBEDDING_MODEL_VERSION                = "synthetic-pinned-version"
      SCHOLARCHAIN_EMBEDDING_DIMENSION                    = "256"
      SCHOLARCHAIN_EVIDENCE_INDEX_PREFIX                  = "evidence-index"
      SCHOLARCHAIN_AUDIT_PREFIX                           = "runtime-audit"
    }
    error_message = "query-api: the inference-profile ID is the synthesis model, the foundation-model ID its version, plus the rag bucket, the embedding triple and the two prefixes."
  }
  assert {
    condition = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].environment : e.name => e.value } == {
      SCHOLARCHAIN_SERVICE_MODE                           = "aws"
      AWS_REGION                                          = "us-east-2"
      SCHOLARCHAIN_HTTP_HOST                              = "0.0.0.0"
      SCHOLARCHAIN_HTTP_PORT                              = "8080"
      SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER              = "scholarchain-course-RunLedger"
      SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE       = "scholarchain-course-EntityLinkCache"
      SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION           = "scholarchain-course-QuerySession"
      SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE         = "scholarchain-course-EvidenceBundle"
      SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY       = "scholarchain-course-ArtifactRegistry"
      SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE = "scholarchain-course-ResearcherMetricCache"
      SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX           = "by-idempotency-key"
      SCHOLARCHAIN_NEPTUNE_ENDPOINT                       = "https://synthetic.cluster-ro.neptune.amazonaws.com:8182"
      SCHOLARCHAIN_STORAGE_GRAPH_BUCKET                   = "scholarchain-course-111122223333-graph"
    }
    error_message = "graph-service: https Neptune endpoint with the explicit port and the graph bucket."
  }
  assert {
    condition = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["semantic-service"].container_definitions)[0].environment : e.name => e.value } == {
      SCHOLARCHAIN_SERVICE_MODE                           = "aws"
      AWS_REGION                                          = "us-east-2"
      SCHOLARCHAIN_HTTP_HOST                              = "0.0.0.0"
      SCHOLARCHAIN_HTTP_PORT                              = "8080"
      SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER              = "scholarchain-course-RunLedger"
      SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE       = "scholarchain-course-EntityLinkCache"
      SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION           = "scholarchain-course-QuerySession"
      SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE         = "scholarchain-course-EvidenceBundle"
      SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY       = "scholarchain-course-ArtifactRegistry"
      SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE = "scholarchain-course-ResearcherMetricCache"
      SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX           = "by-idempotency-key"
      SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET               = "scholarchain-course-111122223333-vectors"
      SCHOLARCHAIN_SEMANTIC_INDEX                         = "researcher-profile-v1"
      SCHOLARCHAIN_S3_VECTORS_METRIC                      = "cosine"
      SCHOLARCHAIN_STORAGE_RAG_BUCKET                     = "scholarchain-course-111122223333-rag"
      SCHOLARCHAIN_MODELS_EMBEDDING_MODEL                 = "amazon.titan-embed-text-v2:0"
      SCHOLARCHAIN_EMBEDDING_MODEL_VERSION                = "synthetic-pinned-version"
      SCHOLARCHAIN_EMBEDDING_DIMENSION                    = "256"
    }
    error_message = "semantic-service: vector bucket, index, metric, rag bucket and the embedding triple."
  }
  assert {
    condition = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["embedding-worker"].container_definitions)[0].environment : e.name => e.value } == {
      SCHOLARCHAIN_SERVICE_MODE                           = "aws"
      AWS_REGION                                          = "us-east-2"
      SCHOLARCHAIN_HTTP_HOST                              = "0.0.0.0"
      SCHOLARCHAIN_HTTP_PORT                              = "8080"
      SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER              = "scholarchain-course-RunLedger"
      SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE       = "scholarchain-course-EntityLinkCache"
      SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION           = "scholarchain-course-QuerySession"
      SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE         = "scholarchain-course-EvidenceBundle"
      SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY       = "scholarchain-course-ArtifactRegistry"
      SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE = "scholarchain-course-ResearcherMetricCache"
      SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX           = "by-idempotency-key"
      SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET               = "scholarchain-course-111122223333-vectors"
      SCHOLARCHAIN_SEMANTIC_INDEX                         = "researcher-profile-v1"
      SCHOLARCHAIN_S3_VECTORS_METRIC                      = "cosine"
      SCHOLARCHAIN_MODELS_EMBEDDING_MODEL                 = "amazon.titan-embed-text-v2:0"
      SCHOLARCHAIN_EMBEDDING_MODEL_VERSION                = "synthetic-pinned-version"
      SCHOLARCHAIN_EMBEDDING_DIMENSION                    = "256"
      SCHOLARCHAIN_SQS_QUEUE_URL                          = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-work"
      SCHOLARCHAIN_SQS_DLQ_URL                            = "https://sqs.us-east-2.amazonaws.com/111122223333/synthetic-dlq"
      SCHOLARCHAIN_STORAGE_RAG_BUCKET                     = "scholarchain-course-111122223333-rag"
      SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX                  = "embedding-text"
      SCHOLARCHAIN_WORKER_VISIBILITY_TIMEOUT_SECONDS      = "300"
      SCHOLARCHAIN_WORKER_WAIT_SECONDS                    = "20"
    }
    error_message = "embedding-worker: queue and DLQ URLs, rag bucket, text prefix, vector settings, embedding triple, visibility 300 and long poll 20 (the root defaults)."
  }
  # Secrets stay ARN bindings: no secret name or ARN in `environment`, and every binding is in `secrets`.
  assert {
    condition = alltrue([
      for svc in ["query-api", "graph-service", "semantic-service", "embedding-worker"] :
      alltrue([for e in jsondecode(output.phase12b_controls.runtime.task_definitions[svc].container_definitions)[0].environment : !startswith(e.value, "arn:aws:secretsmanager") && !contains(["SCHOLARCHAIN_INTERNAL_TOKEN", "SCHOLARCHAIN_GRAPH_CURSOR_KEY", "SCHOLARCHAIN_API_KEY_SHA256", "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"], e.name)])
    ]) && length(jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].secrets) == 3 && length(jsondecode(output.phase12b_controls.runtime.task_definitions["graph-service"].container_definitions)[0].secrets) == 3
    error_message = "No secret value, ARN or secret variable name may appear in `environment`; the bindings remain in `secrets`."
  }
}

run "without_an_inference_profile_the_foundation_model_id_is_the_synthesis_model" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    neptune_enabled              = true
    neptune_engine_version       = "1.4.6.3"
    neptune_parameter_family     = "neptune1.4"
    synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
    embedding_model_version      = "synthetic-pinned-version"
    service_secret_bindings = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => merge(
      { SCHOLARCHAIN_API_KEY_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-a", SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-b" },
      s == "query-api" ? { SCHOLARCHAIN_INTERNAL_TOKEN = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-c" } : {},
      s == "graph-service" ? { SCHOLARCHAIN_GRAPH_CURSOR_KEY = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-d" } : {}
    ) }
  }

  assert {
    condition     = { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL"] == "anthropic.claude-synthetic-test-v1:0" && { for e in jsondecode(output.phase12b_controls.runtime.task_definitions["query-api"].container_definitions)[0].environment : e.name => e.value }["SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION"] == "anthropic.claude-synthetic-test-v1:0"
    error_message = "Without a profile the foundation-model ID is both the Converse model and its version."
  }
}

run "the_aws_service_mode_is_refused_without_the_embedding_model_version_and_the_runtime_needs_the_acknowledgment" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    neptune_enabled              = true
    neptune_engine_version       = "1.4.6.3"
    neptune_parameter_family     = "neptune1.4"
    synthesis_model_id           = "anthropic.claude-synthetic-test-v1:0"
    service_secret_bindings = { for s in ["query-api", "graph-service", "semantic-service", "embedding-worker"] : s => merge(
      { SCHOLARCHAIN_API_KEY_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-a", SCHOLARCHAIN_INTERNAL_TOKEN_SHA256 = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-b" },
      s == "query-api" ? { SCHOLARCHAIN_INTERNAL_TOKEN = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-c" } : {},
      s == "graph-service" ? { SCHOLARCHAIN_GRAPH_CURSOR_KEY = "arn:aws:secretsmanager:us-east-2:111122223333:secret:synthetic-${s}-d" } : {}
    ) }
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "runtime_without_the_acknowledgment_is_refused" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = false
    image_revision               = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    neptune_enabled              = true
    neptune_engine_version       = "1.4.6.3"
    neptune_parameter_family     = "neptune1.4"
  }
  expect_failures = [terraform_data.phase12b_guard]
}

run "a_malformed_embedding_model_version_is_rejected" {
  command = plan
  variables {
    embedding_model_version = "has spaces"
  }
  expect_failures = [var.embedding_model_version]
}

run "the_runtime_module_keeps_mode_unconfigured_and_adds_no_aws_variable_without_the_acknowledgment" {
  command = plan
  module {
    source = "./modules/runtime"
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
    certificate_arn          = null
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

  assert {
    condition = alltrue([
      for svc, td in output.compute_controls.task_definitions :
      length([for e in jsondecode(td.container_definitions)[0].environment : e if e.name == "SCHOLARCHAIN_SERVICE_MODE" && e.value == "unconfigured"]) == 1 && alltrue([for e in jsondecode(td.container_definitions)[0].environment : !startswith(e.name, "SCHOLARCHAIN_DYNAMODB") && !startswith(e.name, "SCHOLARCHAIN_STORAGE") && !startswith(e.name, "SCHOLARCHAIN_MODELS") && !startswith(e.name, "SCHOLARCHAIN_SQS") && e.name != "SCHOLARCHAIN_NEPTUNE_ENDPOINT"])
    ]) && length(output.compute_controls.task_definitions) == 4 && !output.deployment_contract.live_composition_supported
    error_message = "Without the acknowledgment the four tasks are unconfigured and carry none of the aws variables."
  }
}

run "runtime_disabled_creates_no_task_definition_and_so_no_environment" {
  command = plan

  assert {
    condition     = length(output.phase12b_controls.runtime.task_definitions) == 0 && !output.phase12b_controls.deployment_contract.live_composition_supported
    error_message = "With the runtime disabled there is no task definition, hence no environment."
  }
}

# ---- the two task-role grants -----------------------------------------------------------------------------------------------

run "the_embedding_worker_may_use_the_query_session_table_and_index_exactly" {
  command = plan

  assert {
    condition = [for st in jsondecode(output.iam_controls.task_policies["embedding-worker"]).Statement : st if st.Sid == "ReservationInQuerySessionTableAndIndex"] == [{
      Sid      = "ReservationInQuerySessionTableAndIndex", Effect = "Allow",
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"],
      Resource = ["arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-QuerySession", "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-QuerySession/index/by-idempotency-key"]
    }]
    error_message = "The embedding worker has one statement with exactly GetItem, PutItem, UpdateItem and Query on the QuerySession table and its index."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "graph-service", "semantic-service"] : !strcontains(output.iam_controls.task_policies[s], "ReservationInQuerySessionTableAndIndex")])
    error_message = "No other role gets the reservation statement."
  }
  assert {
    condition     = !anytrue([for st in jsondecode(output.iam_controls.task_policies["embedding-worker"]).Statement : contains(st.Action, "dynamodb:DeleteItem") || contains(st.Action, "dynamodb:Scan") || contains(st.Action, "dynamodb:BatchWriteItem")])
    error_message = "The worker never gets DeleteItem, Scan or BatchWriteItem."
  }
}

run "query_api_and_the_embedding_worker_may_list_only_their_rag_prefixes_and_head_absent_keys" {
  command = plan

  assert {
    condition = alltrue([
      for s in ["query-api", "embedding-worker"] :
      [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : {
        sid = st.Sid, action = st.Action, condition = st.Condition, arns = length(st.Resource), bucketlevel = !strcontains(st.Resource[0], "/")
        } if st.Sid == "ListRagBucketPrefixes"] == [{
        sid       = "ListRagBucketPrefixes", action = ["s3:ListBucket"], arns = 1, bucketlevel = true,
        condition = { StringLike = { "s3:prefix" = ["evidence-index", "evidence-index/*", "runtime-audit", "runtime-audit/*", "embedding-text", "embedding-text/*"] } }
      }]
    ])
    error_message = "ListBucket on the rag bucket ARN (no object suffix) with s3:prefix limited to evidence-index, runtime-audit and embedding-text (and their sub-paths)."
  }
  assert {
    condition = alltrue([
      for s in ["query-api", "embedding-worker"] :
      [for st in jsondecode(output.iam_controls.task_policies[s]).Statement : { action = st.Action, condition = st.Condition, bucket = endswith(st.Resource[0], "-rag") } if st.Sid == "HeadAbsentRagKeyAs404NotListing"] == [{ action = ["s3:ListBucket"], condition = { Null = { "s3:prefix" = "true" } }, bucket = true }]
    ])
    error_message = "The HEAD-404 statement is ListBucket on the rag bucket only when s3:prefix is absent (it cannot list)."
  }
  assert {
    condition     = alltrue([for s in ["graph-service", "semantic-service"] : !strcontains(output.iam_controls.task_policies[s], "s3:ListBucket")])
    error_message = "graph-service and semantic-service get no ListBucket."
  }
  assert {
    condition     = alltrue([for s in ["query-api", "embedding-worker"] : !anytrue([for st in jsondecode(output.iam_controls.task_policies[s]).Statement : contains(st.Action, "s3:ListBucket") && anytrue([for r in st.Resource : strcontains(r, "-raw") || strcontains(r, "-curated") || strcontains(r, "-graph") || strcontains(r, "-artifacts") || strcontains(r, "-logs") || strcontains(r, "-reports") || r == "*"])])])
    error_message = "ListBucket only on the rag bucket."
  }
}
