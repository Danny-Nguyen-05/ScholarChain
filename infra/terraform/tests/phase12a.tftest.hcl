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
  mock_resource "aws_ecr_repository" {
    defaults = { arn = "arn:aws:ecr:us-east-1:111122223333:repository/synthetic-phase12a-repo" }
  }
  # New12B outputs participate in existing runtime policy assertions.
  mock_resource "aws_s3vectors_index" {
    defaults = { index_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-phase12a-vectors/index/synthetic-index" }
  }
  mock_resource "aws_s3vectors_vector_bucket" {
    defaults = { vector_bucket_arn = "arn:aws:s3vectors:us-east-1:111122223333:bucket/synthetic-phase12a-vectors" }
  }
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
run "course_data_safety" {
  command = plan
  assert {
    condition     = toset(keys(output.bucket_names)) == toset(["raw", "curated", "graph", "rag", "artifacts", "logs", "reports"])
    error_message = "The seven course data-lake purposes must all exist."
  }
  assert {
    condition = alltrue([for b in output.data_controls.buckets :
      !b.force_destroy && b.versioning == "Enabled" && b.encryption == "aws:kms" && b.ownership == "BucketOwnerEnforced" &&
      b.public_access.block_public_acls && b.public_access.block_public_policy && b.public_access.ignore_public_acls && b.public_access.restrict_public_buckets
    ])
    error_message = "Every bucket must have safe deletion defaults, CMK encryption, versioning, owner-enforced ACLs, and all public-access blocks."
  }
  assert {
    condition = alltrue([for b in output.data_controls.buckets :
      jsondecode(b.tls_policy).Statement[0].Effect == "Deny" && jsondecode(b.tls_policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    ])
    error_message = "Every bucket must deny insecure transport."
  }
  assert {
    condition = { for k, t in output.data_controls.tables : k => [t.pk, t.sk] } == {
      RunLedger             = ["runId", "stageKey"]
      EntityLinkCache       = ["entityType#normalizedKey", "policyVersion#sourceId"]
      QuerySession          = ["queryId", "itemType"]
      EvidenceBundle        = ["evidenceId", "part"]
      ArtifactRegistry      = ["artifactId", "version"]
      ResearcherMetricCache = ["researcherId", "windowId"]
    }
    error_message = "Exactly the six Phase 7 tables and literal key attribute names are required."
  }
  assert {
    condition     = alltrue([for t in output.data_controls.tables : t.billing_mode == "PAY_PER_REQUEST" && t.pitr && t.encryption && t.deletion_protection])
    error_message = "All tables must be on-demand, encrypted, recoverable, and protected by default."
  }
  assert {
    condition     = length(output.data_controls.tables.QuerySession.gsis) == 1 && one(one(output.data_controls.tables.QuerySession.gsis).key_schema).attribute_name == "idempotencyKey" && one(one(output.data_controls.tables.QuerySession.gsis).key_schema).key_type == "HASH" && one(output.data_controls.tables.QuerySession.gsis).projection_type == "ALL" && alltrue([for k, t in output.data_controls.tables : length(t.gsis) == 0 if k != "QuerySession"])
    error_message = "Only QuerySession gets its idempotency-key ALL-projection GSI."
  }
  assert {
    condition     = !one(output.data_controls.tables.QuerySession.ttl).enabled && alltrue([for k, t in output.data_controls.tables : length(t.ttl) == 0 if k != "QuerySession"])
    error_message = "Durable tables must have no TTL; disposable session TTL is opt-in."
  }
  assert {
    condition     = jsondecode(output.data_controls.queues.redrive).maxReceiveCount == 3 && jsondecode(output.data_controls.queues.redrive_allow).redrivePermission == "byQueue" && output.data_controls.queues.dlq_retention > output.data_controls.queues.retention && alltrue([for k in output.data_controls.queues.encryption_keys : startswith(k, "arn:aws:kms:")])
    error_message = "Encrypted embedding work must redrive after three deliveries to a longer-retained queue with restricted redrive sources."
  }
  assert {
    condition     = toset(keys(output.data_controls.ecr)) == toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) && alltrue([for r in output.data_controls.ecr : r.immutable == "IMMUTABLE" && r.scan_on_push && r.encryption == "KMS" && !r.force_delete])
    error_message = "Exactly four encrypted ECR repositories must be immutable, scanned, and deletion-safe."
  }
  assert {
    condition     = output.required_tags.course == "CS441" && output.required_tags.project == "scholarchain" && output.required_tags.environment == "course" && output.required_tags.owner == "danny" && output.required_tags.expiration_date == "2026-11-25"
    error_message = "Required course/project/environment/owner/expiration tags must be present."
  }
  assert {
    condition     = !output.budget_controls.enabled
    error_message = "No budget resource should be created without account capability and approved notifications."
  }
}
run "network_role_boundaries" {
  command = plan
  assert {
    condition     = length(flatten(regexall("resource\\s+\"aws_route\"\\s+\"([^\"]+)\"", join("\n", [for name in fileset("${path.module}/modules/network", "*.tf") : file("${path.module}/modules/network/${name}")])))) == 1 && toset(flatten(regexall("resource\\s+\"aws_route\"\\s+\"([^\"]+)\"", join("\n", [for name in fileset("${path.module}/modules/network", "*.tf") : file("${path.module}/modules/network/${name}")])))) == toset(["default"]) && length(regexall("\\broute\\s*(=|\\{)|dynamic\\s+\"route\"", join("\n", [for name in fileset("${path.module}/modules/network", "*.tf") : file("${path.module}/modules/network/${name}")]))) == 0
    error_message = "Every authored network route must use the single aws_route.default collection; standalone or inline route declarations bypass the isolation control."
  }
  assert {
    condition     = output.network_controls.azs == ["us-east-1a", "us-east-1b"] && output.network_controls.public_subnet_count == 2 && output.network_controls.app_subnet_count == 2 && output.network_controls.data_subnet_count == 2
    error_message = "Use two AZs and distinct public/application/data subnet tiers."
  }
  assert {
    condition     = alltrue([for public in output.network_controls.public_ip_on_launch : !public]) && output.network_controls.data_route_count == 0
    error_message = "Instances must not receive public IPs automatically; data subnets have no default route."
  }
  assert {
    condition     = output.network_controls.nat_gateway_count == 1 && toset(output.network_controls.gateway_services) == toset(["s3", "dynamodb"]) && length(output.network_controls.interface_services) == 0
    error_message = "Cost-aware defaults require one NAT, two free gateway endpoints, no unneeded private interfaces."
  }
  assert {
    condition = output.network_controls.dependency_ports == {
      alb_query = 8080, query_graph = 8080, query_semantic = 8080, graph_neptune = 8182
    } && alltrue([for c in output.network_controls.dependency_cidrs : c == null]) && output.network_controls.public_ingress_count == 0
    error_message = "The dependency chain must reference SG roles; no broad CIDR data ingress or unapproved public ingress."
  }
  assert {
    condition     = alltrue([for port in output.network_controls.https_egress_ports : port == 443]) && output.network_controls.neptune_s3_egress_port == 443
    error_message = "External egress is HTTPS, and Neptune bulk loading only reaches the S3 gateway."
  }
}
run "runtime_identity_boundaries" {
  command = plan
  assert {
    condition = alltrue(flatten([for statement in jsondecode(output.iam_controls.emr_data_policy).Statement : [
      for action in statement.Action : !strcontains(action, "*") && !startswith(lower(action), "dynamodb:")
    ]]))
    error_message = "EMR jobs do not use DynamoDB; the EMR data role must have no DynamoDB action, including runtime audit writes."
  }
  assert {
    condition = alltrue(flatten([for policy in output.iam_controls.task_policies : [for statement in jsondecode(policy).Statement :
      alltrue([for a in statement.Action : !strcontains(a, "*")]) && alltrue([for r in statement.Resource : r != "*"])
    ]]))
    error_message = "Runtime allows must use explicit actions and resource-scoped grants."
  }
  assert {
    condition = alltrue(flatten([for statement in jsondecode(output.iam_controls.task_policies["graph-service"]).Statement : [for action in statement.Action :
      !can(regex("(?i)(put|update|delete|write|insert|create|remove)", action))
    ]]))
    error_message = "The graph runtime reader must have no write action."
  }
  assert {
    condition = alltrue(flatten([for policy in output.iam_controls.execution_policies : [for statement in jsondecode(policy).Statement :
      alltrue([for action in statement.Action : !strcontains(action, "*")]) && (statement.Sid == "EcrAuthentication" ? statement.Action == ["ecr:GetAuthorizationToken"] && statement.Resource == ["*"] : alltrue([for r in statement.Resource : r != "*"]))
    ]]))
    error_message = "Only the documented ECR token API may have an unscoped execution-role resource."
  }
  assert {
    condition     = alltrue([for policy in output.iam_controls.execution_policies : !strcontains(policy, "secretsmanager:GetSecretValue")]) && output.iam_controls.kms_rotation
    error_message = "No secret read permissions should exist without configured secret ARNs; CMK rotation is required."
  }
  assert {
    condition     = jsondecode(output.iam_controls.deployment_trust).Statement[0].Principal.AWS == "arn:aws:iam::111122223333:role/synthetic-architect" && alltrue([for policy in output.iam_controls.task_trust : jsondecode(policy).Statement[0].Principal.Service == "ecs-tasks.amazonaws.com" && jsondecode(policy).Statement[0].Condition.StringEquals["aws:SourceAccount"] == "111122223333"])
    error_message = "Deployment must trust only the approved principal; runtime tasks require same-account ECS service trust."
  }
}
run "cleanup_is_explicit_and_ttl_is_narrow" {
  command = plan
  variables {
    cleanup_mode             = true
    enable_query_session_ttl = true
  }
  assert {
    condition     = alltrue([for t in output.data_controls.tables : !t.deletion_protection]) && alltrue([for b in output.data_controls.buckets : b.force_destroy]) && alltrue([for r in output.data_controls.ecr : r.force_delete])
    error_message = "Only explicit cleanup mode may release native deletion settings; static bucket prevent_destroy remains a separate human code gate."
  }
  assert {
    condition     = one(output.data_controls.tables.QuerySession.ttl).enabled && one(output.data_controls.tables.QuerySession.ttl).attribute_name == "expiresAt" && alltrue([for k, t in output.data_controls.tables : length(t.ttl) == 0 if k != "QuerySession"])
    error_message = "Opt-in cleanup applies only to expiresAt on disposable QuerySession rows."
  }
}
run "persistent_data_has_no_intermediate_expiration" {
  command = plan
  variables { persistent_environment = true }
  assert {
    condition     = alltrue([for b in output.data_controls.buckets : length(b.lifecycle_rules) == 1 && one(b.lifecycle_rules).id == "abort-incomplete-multipart"])
    error_message = "Persistent buckets must not expire stored objects or versions by the course intermediate lifecycle."
  }
}
run "configured_secrets_are_arn_only_and_per_service" {
  command = plan
  variables {
    service_secret_arns = {
      query-api = ["arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-reference-AbCdEf"]
    }
  }
  assert {
    condition     = length([for s in jsondecode(output.iam_controls.execution_policies["query-api"]).Statement : s if s.Sid == "InjectOnlyConfiguredSecrets" && s.Action == ["secretsmanager:GetSecretValue"] && s.Resource == ["arn:aws:secretsmanager:us-east-1:111122223333:secret:synthetic-query-reference-AbCdEf"]]) == 1 && alltrue([for service, policy in output.iam_controls.execution_policies : !strcontains(policy, "secretsmanager:GetSecretValue") if service != "query-api"])
    error_message = "Only the configured service execution role may inject exactly the named secret ARN."
  }
}
run "invalid_account_is_rejected" {
  command = plan
  variables { aws_account_id = "not-an-account" }
  expect_failures = [var.aws_account_id]
}
run "invalid_budget_is_rejected" {
  command = plan
  variables { budget_limit_usd = 0 }
  expect_failures = [var.budget_limit_usd]
}
run "wrong_region_az_is_rejected" {
  command = plan
  variables { availability_zones = ["us-west-2a", "us-west-2b"] }
  expect_failures = [terraform_data.configuration_guard]
}
run "duplicate_az_is_rejected" {
  command = plan
  variables { availability_zones = ["us-east-1a", "us-east-1a"] }
  expect_failures = [var.availability_zones]
}
run "malformed_secret_reference_is_rejected" {
  command = plan
  variables { service_secret_arns = { query-api = ["unapproved-inline-value"] } }
  expect_failures = [var.service_secret_arns]
}

run "optional_bootstrap_preserves_state" {
  command = plan
  module { source = "./modules/foundation/bootstrap" }
  variables {
    state_bucket_name = "synthetic-only-state-bucket"
    lock_table_name   = "synthetic-only-lock-table"
    tags = {
      course = "CS441", project = "scholarchain", environment = "synthetic", owner = "synthetic", expiration_date = "2026-11-25"
    }
  }
  assert {
    condition     = output.controls.versioning == "Enabled" && output.controls.encryption == "AES256" && !output.controls.force_destroy && output.controls.public_access_block.block_public_acls && output.controls.public_access_block.block_public_policy && output.controls.public_access_block.ignore_public_acls && output.controls.public_access_block.restrict_public_buckets
    error_message = "Remote state must be versioned, encrypted with the approved AWS-managed choice, private, and not force-destroyable."
  }
  assert {
    condition     = output.controls.lock_key == "LockID" && output.controls.lock_deletion_protection && output.controls.lock_pitr && output.controls.lock_encryption && jsondecode(output.controls.tls_policy).Statement[0].Effect == "Deny"
    error_message = "Bootstrap locking must use LockID, encryption, PITR, native deletion protection, and a state-bucket TLS deny."
  }
}
run "budget_requires_actual_subscribers" {
  command = plan
  variables { enable_budget_resource = true }
  expect_failures = [var.budget_notification_emails]
}
