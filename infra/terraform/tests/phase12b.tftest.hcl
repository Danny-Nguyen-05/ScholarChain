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

run "inactive_defaults_and_vector_contract" {
  command = plan
  assert {
    condition = length([for statement in jsondecode(output.iam_controls.kms_policy).Statement : statement if try(statement.Principal.Service, "") == "indexing.s3vectors.amazonaws.com" && statement.Effect == "Allow" && statement.Action == ["kms:Decrypt"] && statement.Resource == "*" && try(statement.Condition, {}) == {
      StringEquals               = { "aws:SourceAccount" = "111122223333" }
      ArnLike                    = { "aws:SourceArn" = ["arn:aws:s3vectors:us-east-1:111122223333:bucket/scholarchain-course-111122223333-vectors", "arn:aws:s3vectors:us-east-1:111122223333:bucket/scholarchain-course-111122223333-vectors/index/*"] }
      "ForAnyValue:StringEquals" = { "kms:EncryptionContextKeys" = ["aws:s3vectors:arn", "aws:s3vectors:resource-id"] }
    }]) == 1 && length(jsondecode(output.iam_controls.kms_policy).Statement) == 2
    error_message = "B3: The project CMK must allow exactly one S3 Vectors indexing service decrypt grant, restricted to the expected account, project vector bucket and index ARNs and S3 Vectors encryption context keys."
  }
  assert {
    condition     = !output.phase12b_controls.runtime.enabled && length(output.phase12b_controls.runtime.services) == 0 && length(output.phase12b_controls.runtime.scaling_targets) == 0 && !output.phase12b_controls.emr.enabled && output.phase12b_controls.emr.cluster == null && !output.phase12b_controls.neptune.enabled
    error_message = "Pending composition/runtime/engine selections must create no EMR cluster, Neptune or ECS tasks/services/scaling targets."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.vectors.indexes)) == toset(["researcher-profile-v1", "collaboration-community-v1", "paper-abstract-v1", "collaboration-path-v1", "topic-institution-summary-v1"]) && alltrue([for i in output.phase12b_controls.vectors.indexes : i.dimension == 256 && i.distance_metric == "cosine" && i.data_type == "float32" && one(i.metadata_configuration).non_filterable_metadata_keys == toset(["textS3Uri"]) && one(i.encryption_configuration).sse_type == "aws:kms"]) && !output.phase12b_controls.vectors.bucket.force_destroy && one(output.phase12b_controls.vectors.bucket.encryption_configuration).sse_type == "aws:kms"
    error_message = "Exactly the five Phase7 indexes must match the256/cosine/float32 Phase8 contract and CMK/deletion safeguards."
  }
  assert {
    condition     = jsondecode(output.phase12b_controls.vectors.policy).Statement[0].Effect == "Deny" && jsondecode(output.phase12b_controls.vectors.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    error_message = "Vector policy must deny insecure transport, never grant public access."
  }
  assert {
    condition     = alltrue([for g in output.phase12b_controls.observability.log_groups : g.retention_in_days == 7]) && output.phase12b_controls.observability.audit_log.retention_in_days == 7 && length(output.phase12b_controls.observability.queue_alarm.alarm_actions) == 0 && output.phase12b_controls.observability.queue_alarm.threshold == 300 && alltrue([for a in output.phase12b_controls.observability.latency_alarms : a.threshold == 5 && a.treat_missing_data == "missing"]) && output.phase12b_controls.observability.error_alarm.threshold == 5
    error_message = "Seven-day logs, truthful missing telemetry and selected finite alarm thresholds require no invented notification target."
  }
  assert {
    condition     = strcontains(output.phase12b_controls.observability.dashboard, "publisher required") && !output.phase12b_controls.deployment_contract.live_composition_supported
    error_message = "Custom application metrics and live service composition must remain explicitly disclosed deployment dependencies."
  }
}
run "dashboard_metric_shapes_and_route_ownership" {
  command = plan
  assert {
    condition     = alltrue(flatten([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : [for m in try(w.properties.metrics, []) : can(m[0]) && can(m[1])]])) && length([for m in one([for w in jsondecode(output.phase12b_controls.observability.dashboard).widgets : w.properties.metrics if try(w.properties.title, "") == "DynamoDB capacity units and table throttle events"]) : m if m[0] == "AWS/DynamoDB" && contains(["ReadThrottleEvents", "WriteThrottleEvents"], m[1]) && m[2] == "TableName" && length(m) == 4]) == 12
    error_message = "CloudWatch metrics must be arrays (not recursively flattened strings); each of six tables gets correctly dimensioned read/write throttle-event series."
  }
  assert {
    condition     = alltrue([for filename in fileset(path.module, "**/*.tf") : startswith(filename, "modules/network/") || length(regexall("resource\\s+\"aws_(route|route_table|route_table_association|default_route_table|main_route_table_association)\"", file("${path.module}/${filename}"))) == 0])
    error_message = "R1 requires every authored route and route-table resource to stay inside modules/network."
  }
}
run "private_neptune_and_read_only_graph" {
  command = plan
  variables {
    neptune_enabled          = true
    neptune_engine_version   = "1.4.6.3"
    neptune_parameter_family = "neptune1.4"
  }
  assert {
    condition     = output.phase12b_controls.neptune.cluster.storage_encrypted && output.phase12b_controls.neptune.cluster.iam_database_authentication_enabled && output.phase12b_controls.neptune.cluster.deletion_protection && !output.phase12b_controls.neptune.cluster.skip_final_snapshot && output.phase12b_controls.neptune.cluster.backup_retention_period == 7 && !output.phase12b_controls.neptune.instance.publicly_accessible && output.phase12b_controls.neptune.instance.instance_class == "db.serverless" && one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).min_capacity == 1 && one(output.phase12b_controls.neptune.cluster.serverless_v2_scaling_configuration).max_capacity == 2.5
    error_message = "Neptune must be private, IAM-authenticated, encrypted, backed up, protected and bounded to1-2.5NCU."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["graph-service"]).Statement : st if st.Sid == "ReadOnlyNeptuneGraph" && st.Action == ["neptune-db:ReadDataViaQuery", "neptune-db:GetQueryStatus", "neptune-db:CancelQuery"] && st.Resource == ["arn:aws:neptune-db:us-east-1:111122223333:cluster-synthetic-graph/*"]]) == 1 && alltrue(flatten([for st in jsondecode(output.iam_controls.task_policies["graph-service"]).Statement : [for a in st.Action : !can(regex("(?i)(write|delete|put|update|insert|reset|startloader)", a))]]))
    error_message = "The graph role must have only explicit read/query-control access to the concrete Neptune data ARN and no write action."
  }
}
run "scoped_embedding_producer_and_models" {
  command = plan
  assert {
    condition     = jsondecode(output.phase12b_controls.workflow.producer_policy).Statement[0].Action == ["sqs:SendMessage"] && toset(jsondecode(output.phase12b_controls.workflow.producer_policy).Statement[0].Resource) == toset(["arn:aws:sqs:us-east-1:111122223333:synthetic-work", "arn:aws:sqs:us-east-1:111122223333:synthetic-dlq"]) && jsondecode(output.phase12b_controls.workflow.trust).Statement[0].Condition.ArnEquals["aws:SourceArn"] == "arn:aws:states:us-east-1:111122223333:stateMachine:scholarchain-course-embedding-dispatch"
    error_message = "The pipeline producer must trust only this state machine and send only to this work queue and failure DLQ."
  }
  assert {
    condition     = jsondecode(output.phase12b_controls.workflow.definition).States.Enqueue.Parameters.QueueUrl == "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-work" && jsondecode(output.phase12b_controls.workflow.definition).States.Enqueue.Retry[0].MaxAttempts == 2 && jsondecode(output.phase12b_controls.workflow.definition).TimeoutSeconds == 120 && jsondecode(output.phase12b_controls.workflow.definition).States.RecordFailure.Parameters.QueueUrl == "https://sqs.us-east-1.amazonaws.com/111122223333/synthetic-dlq"
    error_message = "The functional workflow must use fixed queue URLs, a bounded execution and bounded retry/failure routing."
  }
  assert {
    condition     = alltrue([for st in jsondecode(output.phase12b_controls.workflow.producer_policy).Statement : alltrue([for a in st.Action : !strcontains(a, "*")]) && alltrue([for arn in st.Resource : arn != "*"])]) && length([for st in jsondecode(output.phase12b_controls.workflow.producer_policy).Statement : st if st.Sid == "EncryptWorkflowState" && !contains(keys(st.Condition.StringEquals), "kms:ViaService") && st.Condition.StringEquals["kms:EncryptionContext:aws:states:stateMachineArn"] == "arn:aws:states:us-east-1:111122223333:stateMachine:scholarchain-course-embedding-dispatch"]) == 1
    error_message = "Queue and workflow encryption need distinct CMK-scoped grants with exact state-machine encryption context."
  }
  assert {
    condition     = alltrue([for s in ["semantic-service", "embedding-worker"] : length([for st in jsondecode(output.iam_controls.task_policies[s]).Statement : st if st.Sid == "InvokeConfiguredEmbeddingModel" && st.Action == ["bedrock:InvokeModel"] && st.Resource == ["arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"]]) == 1]) && alltrue([for st in jsondecode(output.iam_controls.task_policies["query-api"]).Statement : !contains(st.Action, "bedrock:InvokeModel")])
    error_message = "Only embedding participants get the configured Titan ARN; an unset synthesis model grants no query-model invocation."
  }
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.emr_data_policy).Statement : st if st.Sid == "CommitOutputTemporaryFiles" && st.Action == ["s3:DeleteObject"] && length(st.Resource) == 4 && alltrue([for arn in st.Resource : endswith(arn, "/pipeline/*")])]) == 1 && !strcontains(lower(output.iam_controls.emr_data_policy), "dynamodb:")
    error_message = "EMR deletes must be output-prefix-only for commits; EMR must continue to have no DynamoDB permission."
  }
}
run "bounded_runtime_scaling_and_secret_wiring" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
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
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.services)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) && alltrue([for service in output.phase12b_controls.runtime.services : !one(service.network_configuration).assign_public_ip]) && alltrue([for s, t in output.phase12b_controls.runtime.scaling_targets : t.min_capacity == 1 && t.max_capacity == (s == "embedding-worker" ? 4 : 2)])
    error_message = "Each private Fargate service must have its own bounded scaling target; worker max4 and HTTP max2."
  }
  assert {
    condition     = alltrue([for t in output.phase12b_controls.runtime.task_definitions : t.cpu == "512" && t.memory == "1024" && jsondecode(t.container_definitions)[0].readonlyRootFilesystem && alltrue([for ref in jsondecode(t.container_definitions)[0].secrets : startswith(ref.valueFrom, "arn:aws:secretsmanager:")]) && length([for e in jsondecode(t.container_definitions)[0].environment : e if e.name == "SCHOLARCHAIN_SERVICE_MODE" && e.value == "unconfigured"]) == 1])
    error_message = "Task sizes and secret references must match the accepted contract without silently selecting synthetic/live composition."
  }
  assert {
    condition     = toset(keys(output.phase12b_controls.runtime.cpu_policies)) == toset(["query-api", "graph-service", "semantic-service"]) && alltrue([for p in output.phase12b_controls.runtime.cpu_policies : one(p.target_tracking_scaling_policy_configuration).target_value == 60]) && one(output.phase12b_controls.runtime.worker_policy.target_tracking_scaling_policy_configuration).target_value == 10 && length([for setting in output.phase12b_controls.runtime.cluster_settings : setting if setting.name == "containerInsights" && setting.value == "enabled"]) == 1
    error_message = "All three HTTP CPU policies and worker backlog-per-running-task policy require bounded targets and Container Insights metrics."
  }
  assert {
    condition     = length(output.phase12b_controls.runtime.listeners) == 0 && length([for b in output.phase12b_controls.runtime.load_balancers : b if b.enable_deletion_protection && !b.internal && length(b.access_logs) == 0]) == 1
    error_message = "Without an approved certificate there must be no listener; ALB logging must remain explicitly off."
  }
}
run "https_has_no_http_fallback" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
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
  assert {
    condition     = length(output.phase12b_controls.runtime.listeners) == 1 && output.phase12b_controls.runtime.listeners[0].protocol == "HTTPS" && output.phase12b_controls.runtime.listeners[0].port == 443
    error_message = "Only an explicitly configured HTTPS443 listener is allowed."
  }
}
run "bounded_emr_mock_runtime_only" {
  command = plan
  variables {
    emr_config              = { enabled = true, release_label = "emr-7.8.0", runtime_reference = "SYNTHETIC-NOT-LIVE-RUNTIME-PROOF", runtime_verified = true, bootstrap_uri = "s3://synthetic-artifacts/bootstrap/spark-213.sh", tls_certificate_uri = "s3://synthetic-artifacts/tls/synthetic.zip" }
    emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:DescribeInstances\"],\"Resource\":[\"*\"]}]}"
  }
  assert {
    condition     = output.phase12b_controls.emr.cluster.applications == toset(["Hadoop", "Spark"]) && one(output.phase12b_controls.emr.cluster.master_instance_group).instance_count == 1 && one(output.phase12b_controls.emr.cluster.core_instance_group).instance_count == 1 && one(output.phase12b_controls.emr.scaling.compute_limits).minimum_capacity_units == 1 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_capacity_units == 3 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_core_capacity_units == 1 && one(output.phase12b_controls.emr.scaling.compute_limits).maximum_ondemand_capacity_units == 3
    error_message = "EMR has one primary plus1-3 on-demand workers, at most one core and at most two task nodes."
  }
  assert {
    condition     = one(output.phase12b_controls.emr.cluster.auto_termination_policy).idle_timeout == 1800 && one(output.phase12b_controls.emr.cluster.master_instance_group).bid_price == null && one(output.phase12b_controls.emr.cluster.core_instance_group).bid_price == null && jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.EnableInTransitEncryption && jsondecode(output.phase12b_controls.emr.security.configuration).EncryptionConfiguration.EnableAtRestEncryption
    error_message = "EMR must have finite idle termination, no Spot bids and explicit in-transit/at-rest encryption."
  }
}
run "runtime_cannot_activate_without_composition" {
  command = plan
  variables { runtime_enabled = true }
  expect_failures = [terraform_data.phase12b_guard]
}
run "emr_cannot_activate_without_runtime" {
  command = plan
  variables { emr_config = { enabled = true } }
  expect_failures = [terraform_data.phase12b_guard]
}
run "neptune_requires_matching_engine_family" {
  command = plan
  variables {
    neptune_enabled          = true
    neptune_engine_version   = "1.4.6.3"
    neptune_parameter_family = "neptune1.3"
  }
  expect_failures = [terraform_data.phase12b_guard]
}
run "vector_dimension_migration_is_not_silent" {
  command = plan
  variables { vector_dimension = 512 }
  expect_failures = [terraform_data.phase12b_guard]
}
run "emr_delete_cannot_reach_raw" {
  command = plan
  variables { emr_output_prefixes = { raw = ["pipeline/"] } }
  expect_failures = [var.emr_output_prefixes]
}

run "neptune_rejects_missing_engine" {
  command = plan
  variables { neptune_enabled = true }
  expect_failures = [terraform_data.phase12b_guard]
}
run "emr_rejects_global_write_policy" {
  command = plan
  variables { emr_service_policy_json = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"ec2:RunInstances\"],\"Resource\":[\"*\"]}]}" }
  expect_failures = [var.emr_service_policy_json]
}
run "model_wildcards_are_rejected" {
  command = plan
  variables { synthesis_model_id = "*" }
  expect_failures = [terraform_data.phase12b_guard]
}
run "vector_writer_scopes_exact_indexes" {
  command = plan
  assert {
    condition     = length([for st in jsondecode(output.iam_controls.task_policies["embedding-worker"]).Statement : st if st.Sid == "WriteConfiguredEmbeddingVectors" && st.Action == ["s3vectors:PutVectors"] && toset(st.Resource) == toset([for name in ["researcher-profile-v1", "collaboration-community-v1", "paper-abstract-v1", "collaboration-path-v1", "topic-institution-summary-v1"] : "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-vectors/index/${name}"])]) == 1 && alltrue(flatten([for svc in ["query-api", "graph-service", "semantic-service"] : [for st in jsondecode(output.iam_controls.task_policies[svc]).Statement : !contains(st.Action, "s3vectors:PutVectors")]]))
    error_message = "Only the embedding writer can put vectors, scoped to exactly the five distinguishable index ARNs."
  }
}

run "vector_pointer_metadata_contract_is_required" {
  command = plan
  variables { vector_non_filterable_metadata_keys = [] }
  expect_failures = [var.vector_non_filterable_metadata_keys]
}

run "graph_replicas_require_shared_cursor_key" {
  command = plan
  variables {
    runtime_enabled              = true
    runtime_composition_verified = true
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
  expect_failures = [terraform_data.phase12b_guard]
}
