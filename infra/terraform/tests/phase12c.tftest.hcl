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
  mock_resource "aws_emr_cluster" { defaults = { id = "j-SYNTHETIC12C" } }
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

# Phase12C requirements. Every run uses only the mock provider above.
run "s3vectors_key_covers_project_bucket_and_indexes" {
  command = plan
  assert {
    condition = length([for st in jsondecode(output.iam_controls.kms_policy).Statement : st if try(st.Principal.Service, "") == "indexing.s3vectors.amazonaws.com" && st.Effect == "Allow" && st.Action == ["kms:Decrypt"] && st.Resource == "*" && try(st.Condition, {}) == {
      StringEquals               = { "aws:SourceAccount" = "111122223333" }
      ArnLike                    = { "aws:SourceArn" = ["arn:aws:s3vectors:us-east-1:111122223333:bucket/scholarchain-course-111122223333-vectors", "arn:aws:s3vectors:us-east-1:111122223333:bucket/scholarchain-course-111122223333-vectors/index/*"] }
      "ForAnyValue:StringEquals" = { "kms:EncryptionContextKeys" = ["aws:s3vectors:arn", "aws:s3vectors:resource-id"] }
    }]) == 1 && length(jsondecode(output.iam_controls.kms_policy).Statement) == 2
    error_message = "N17: Indexing decrypt requires exactly this project's bucket and index ARN paths, account and documented context; no wider key grant."
  }
}
run "disabled_sources_have_no_empty_dashboard_widgets" {
  command = plan
  assert {
    condition     = alltrue([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : try(length(w.properties.metrics) > 0, true)]) && length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if can(regex("^(EMR |Neptune )", try(w.properties.title, "")))]) == 0
    error_message = "N11: Disabled EMR/Neptune must omit their widgets; no metric widget may have an empty metric array."
  }
}
run "dynamodb_native_failure_and_latency_panels" {
  command = plan
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "DynamoDB conditional write failures" && try(w.properties.stat, "") == "Sum" && try(length(w.properties.metrics), 0) == 6 && alltrue([for m in w.properties.metrics : m[0] == "AWS/DynamoDB" && m[1] == "ConditionalCheckFailedRequests" && m[2] == "TableName" && length(m) == 4])]) == 1
    error_message = "N12: All six tables need native conditional-write failure counts with TableName and Sum."
  }
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "DynamoDB successful request latency (milliseconds)" && try(w.properties.stat, "") == "Average" && try(length(w.properties.metrics), 0) == 42 && alltrue([for m in w.properties.metrics : m[0] == "AWS/DynamoDB" && m[1] == "SuccessfulRequestLatency" && m[2] == "TableName" && m[4] == "Operation" && contains(["GetItem", "PutItem", "UpdateItem", "DeleteItem", "Query", "BatchGetItem", "BatchWriteItem"], m[5]) && length(m) == 6])]) == 1
    error_message = "N12: Six tables and seven adapter operations need native successful latency with TableName/Operation and Average."
  }
}
run "neptune_native_errors_when_enabled" {
  command = plan
  variables {
    neptune_enabled          = true
    neptune_engine_version   = "1.4.6.3"
    neptune_parameter_family = "neptune1.4"
  }
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "Neptune client/server errors per second" && try(w.properties.stat, "") == "Average" && try(length(w.properties.metrics), 0) == 2 && toset([for m in w.properties.metrics : m[1]]) == toset(["TotalClientErrorsPerSec", "TotalServerErrorsPerSec"]) && alltrue([for m in w.properties.metrics : m[0] == "AWS/Neptune" && m[2] == "DBClusterIdentifier" && m[3] == "scholarchain-course-graph" && length(m) == 4])]) == 1
    error_message = "N12: Active Neptune needs correctly dimensioned native client/server error-rate series, averaged per second."
  }
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "Neptune capacity and utilization"]) == 1 && alltrue([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : try(length(w.properties.metrics) > 0, true)])
    error_message = "N11: An active Neptune writer retains its capacity widget without introducing empty EMR widgets."
  }
}
run "emr_service_role_owns_ebs_key_permissions" {
  command = plan
  variables {
    emr_config              = { enabled = true, release_label = "emr-7.8.0", runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://synthetic-artifacts/bootstrap/spark-213.sh", tls_certificate_uri = "s3://synthetic-artifacts/tls/synthetic.zip" }
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
    condition     = output.iam_controls.emr_disk_encryption.role == "synthetic-emr-service" && length(jsondecode(output.iam_controls.emr_disk_encryption.policy).Statement) == 2 && length([for st in jsondecode(output.iam_controls.emr_disk_encryption.policy).Statement : st if st.Action == ["kms:CreateGrant"] && st.Resource == ["arn:aws:kms:us-east-1:111122223333:key/00000000-0000-0000-0000-000000000001"] && try(st.Condition.Bool["kms:GrantIsForAWSResource"], "false") == "true"]) == 1 && length([for st in jsondecode(output.iam_controls.emr_disk_encryption.policy).Statement : st if toset(st.Action) == toset(["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKeyWithoutPlaintext", "kms:ReEncryptFrom", "kms:ReEncryptTo"]) && st.Resource == ["arn:aws:kms:us-east-1:111122223333:key/00000000-0000-0000-0000-000000000001"]]) == 1
    error_message = "N9: The EMR service role, not the EC2 role, needs only the project CMK's explicit EBS actions and AWS-resource-conditioned CreateGrant."
  }
  assert {
    condition     = length([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w if try(w.properties.title, "") == "EMR running/pending/requested nodes"]) == 1 && alltrue([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : try(length(w.properties.metrics) > 0, true)])
    error_message = "N11: Active EMR retains its native nodes widget while inactive Neptune widgets are absent."
  }
}
run "missing_work_item_reaches_invalid_work" {
  command = plan
  assert {
    condition     = try(jsondecode(output.phase12b_controls.workflow.definition).States.ValidateWork.Choices[0], {}) == { And = [{ Variable = "$.workItem", IsPresent = true }, { Variable = "$.workItem", IsString = true }], Next = "Enqueue" } && jsondecode(output.phase12b_controls.workflow.definition).States.ValidateWork.Default == "InvalidWork" && jsondecode(output.phase12b_controls.workflow.definition).States.InvalidWork.Error == "InvalidEmbeddingWork"
    error_message = "N14: Guard IsString with IsPresent in that order so missing input routes to InvalidWork without States.Runtime."
  }
}
run "emr_rejects_wildcard_region_account" {
  command = plan
  variables { emr_service_policy_json = "{\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:TerminateInstances\"],\"Resource\":[\"arn:aws:ec2:*:*:instance/*\"]}]}" }
  expect_failures = [var.emr_service_policy_json]
}
run "emr_rejects_wildcard_arn_service" {
  command = plan
  variables { emr_service_policy_json = "{\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"iam:PassRole\"],\"Resource\":[\"arn:*\"]}]}" }
  expect_failures = [var.emr_service_policy_json]
}
run "emr_accepts_scoped_future_resource_suffix" {
  command = plan
  variables { emr_service_policy_json = "{\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:TerminateInstances\"],\"Resource\":[\"arn:aws:ec2:us-east-1:111122223333:instance/*\"]},{\"Effect\":\"Allow\",\"Action\":[\"iam:PassRole\"],\"Resource\":[\"arn:aws:iam::111122223333:role/scoped-emr-*\"]}]}" }
  assert {
    condition     = !output.phase12b_controls.emr.enabled
    error_message = "Scoped future-ID suffixes may be reviewed as inputs without activating EMR."
  }
}
