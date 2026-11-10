locals {
  # Decision 14-6 / D1: every role carries a permissions boundary created by the deployer root (infra/terraform/deployer,
  # boundaries/*.json.tftpl). The ARN is built from the account ID and the fixed names scholarchain-<environment>-permissions-boundary
  # and -emr-service-boundary (name_prefix is "<project>-<environment>"); no remote state is read. The EMR service role gets the
  # EMR service boundary (EC2 launch ceiling), every other role the runtime boundary. The deployer role can create these roles
  # only with exactly these ARNs, so the boundaries must exist (deployer apply) before the first plan of this root is applied.
  boundary_arn = {
    runtime     = "arn:aws:iam::${var.aws_account_id}:policy/${var.name_prefix}-permissions-boundary"
    emr_service = "arn:aws:iam::${var.aws_account_id}:policy/${var.name_prefix}-emr-service-boundary"
  }
  services = toset(["query-api", "graph-service", "semantic-service", "embedding-worker"])
  root_arn = "arn:aws:iam::${var.aws_account_id}:root"
  # KMS key policies require Resource="*", meaning THIS key, not every key.
  key_admin_actions = [
    "kms:CreateKey", "kms:DescribeKey", "kms:EnableKey", "kms:DisableKey",
    "kms:GetKeyPolicy", "kms:PutKeyPolicy", "kms:GetKeyRotationStatus",
    "kms:EnableKeyRotation", "kms:DisableKeyRotation", "kms:ScheduleKeyDeletion",
    "kms:CancelKeyDeletion", "kms:TagResource", "kms:UntagResource",
    "kms:ListResourceTags", "kms:UpdateKeyDescription", "kms:CreateAlias",
    "kms:UpdateAlias", "kms:DeleteAlias", "kms:Encrypt", "kms:Decrypt",
    "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:GenerateDataKey",
    "kms:GenerateDataKeyWithoutPlaintext", "kms:DescribeKey", "kms:CreateGrant",
    "kms:ListGrants", "kms:RevokeGrant", "kms:RetireGrant"
  ]
  # The deployer role (infra/terraform/deployer, variable role_name default "scholarchain-deployer"; the deployer tests assert the
  # default, the root tests assert this ARN). Fixed name, not remote state.
  deployer_role_arn = "arn:aws:iam::${var.aws_account_id}:role/scholarchain-deployer"
  deployer_key_admin_actions = [
    "kms:DescribeKey", "kms:GetKeyPolicy", "kms:PutKeyPolicy", "kms:GetKeyRotationStatus",
    "kms:EnableKeyRotation", "kms:DisableKeyRotation", "kms:ListResourceTags", "kms:TagResource", "kms:UntagResource",
    "kms:UpdateKeyDescription", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion",
    "kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias",
  ]
  # Services act for the deployer when they create encrypted resources (S3 SSE-KMS and the artifact upload, DynamoDB, SQS, ECR, EFS,
  # Neptune, Step Functions, EMR, S3 Vectors): the data-key actions only through those services.
  deployer_key_use_actions = [
    "kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext", "kms:ReEncryptFrom", "kms:ReEncryptTo",
  ]
  deployer_key_grant_actions = ["kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant", "kms:RetireGrant"]
  deployer_via_services      = ["s3", "dynamodb", "sqs", "ecr", "elasticfilesystem", "rds", "states", "elasticmapreduce", "s3vectors"]
  ecs_trust = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.aws_account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:ecs:${var.aws_region}:${var.aws_account_id}:*" }
      }
    }]
  })
  service_tables = {
    query-api        = ["EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache"]
    graph-service    = ["EntityLinkCache", "ResearcherMetricCache", "ArtifactRegistry"]
    semantic-service = ["ArtifactRegistry"]
    embedding-worker = ["RunLedger", "ArtifactRegistry"]
  }
  # s3:ListBucket on the rag bucket for the two roles that HEAD keys there. Without it S3 answers 403 (not 404) for an absent key, and
  # S3ObjectStore.head maps only 404 to "missing", so every new evidence item would be rejected. Two statements, see below.
  rag_list_services = toset(["query-api", "embedding-worker"])
  rag_list_prefixes = flatten([for p in var.rag_prefixes : [p, "${p}/*"]])
  service_read_buckets = {
    query-api        = ["rag", "artifacts", "graph"]
    graph-service    = ["graph", "artifacts"]
    semantic-service = ["rag"]
    embedding-worker = ["rag", "artifacts"]
  }
  service_write_buckets = {
    query-api        = ["rag"]
    graph-service    = []
    semantic-service = []
    embedding-worker = ["rag", "artifacts"]
  }
  # Explicit action/resource statements, one policy per runtime component.
  task_statements = { for s in local.services : s => concat([
    {
      Sid      = "ReadConfiguredTables"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query"]
      Resource = [for t in local.service_tables[s] : var.table_arns[t]]
    },
    {
      Sid      = "ReadConfiguredObjects"
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:GetObjectVersion"]
      Resource = [for b in local.service_read_buckets[s] : "${var.bucket_arns[b]}/*"]
    },
    {
      Sid      = "DecryptConfiguredData"
      Effect   = "Allow"
      Action   = ["kms:Decrypt", "kms:DescribeKey"]
      Resource = [aws_kms_key.data.arn]
    }
    ], length(local.service_write_buckets[s]) > 0 ? [{
      Sid      = "WriteImmutableApplicationObjects"
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = [for b in local.service_write_buckets[s] : "${var.bucket_arns[b]}/*"]
      }, {
      Sid      = "EncryptApplicationObjects"
      Effect   = "Allow"
      Action   = ["kms:GenerateDataKey"]
      Resource = [aws_kms_key.data.arn]
      }] : [], s == "query-api" ? [{
      Sid      = "QuerySessionIdempotencyIndex"
      Effect   = "Allow"
      Action   = ["dynamodb:Query"]
      Resource = [var.query_session_index_arn]
      }, {
      Sid    = "ConditionalSessionAndEvidenceWrites"
      Effect = "Allow"
      Action = ["dynamodb:PutItem", "dynamodb:UpdateItem"]
      # DynamoDB transactions authorize each constituent PutItem/UpdateItem;
      # there is no separate TransactWriteItems IAM action.
      Resource = [var.table_arns["QuerySession"], var.table_arns["EvidenceBundle"]]
      }] : [], s == "embedding-worker" ? [{
      Sid      = "ConditionalEmbeddingLedger"
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:UpdateItem"]
      Resource = [var.table_arns["RunLedger"], var.table_arns["ArtifactRegistry"]]
      }, {
      Sid      = "ConsumeEmbeddingQueue"
      Effect   = "Allow"
      Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes", "sqs:GetQueueUrl"]
      Resource = [var.queue_arn]
      }, {
      Sid      = "SendFailedEmbeddingToDlq"
      Effect   = "Allow"
      Action   = ["sqs:SendMessage"]
      Resource = [var.dead_letter_queue_arn]
      }, {
      Sid      = "EncryptQueueMessages"
      Effect   = "Allow"
      Action   = ["kms:GenerateDataKey"]
      Resource = [aws_kms_key.data.arn]
      }, {
      # Evidence: the reservation record lives in the QuerySession table (the worker's durable reservation, AwsComposition readiness).
      Sid      = "ReservationInQuerySessionTableAndIndex"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
      Resource = [var.table_arns["QuerySession"], var.query_session_index_arn]
    }] : [],
    [for st in [{
      # Real listings are limited to the prefixes these roles use.
      Sid       = "ListRagBucketPrefixes"
      Effect    = "Allow"
      Action    = ["s3:ListBucket"]
      Resource  = [var.bucket_arns["rag"]]
      Condition = { StringLike = { "s3:prefix" = local.rag_list_prefixes } }
      }, {
      # HeadObject carries no s3:prefix, so the statement above can never match it. S3 uses s3:ListBucket on the bucket only to answer
      # 404 instead of 403 for an absent key; with the key Null the grant cannot list anything (every list request carries s3:prefix,
      # empty when unspecified), and these roles can already GetObject every key in the bucket. Unverified against live S3.
      Sid       = "HeadAbsentRagKeyAs404NotListing"
      Effect    = "Allow"
      Action    = ["s3:ListBucket"]
      Resource  = [var.bucket_arns["rag"]]
      Condition = { Null = { "s3:prefix" = "true" } }
  }] : st if contains(local.rag_list_services, s)]) }
}
resource "aws_kms_key" "data" {
  description             = "${var.name_prefix} encrypted course data"
  enable_key_rotation     = true
  deletion_window_in_days = var.kms_deletion_window_days
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "EnableExplicitAccountIamDelegationForThisKey"
      Effect    = "Allow"
      Principal = { AWS = local.root_arn }
      Action    = distinct(local.key_admin_actions)
      Resource  = "*"
      }, {
      Sid       = "AllowS3VectorsServicePrincipal"
      Effect    = "Allow"
      Principal = { Service = "indexing.s3vectors.amazonaws.com" }
      Action    = ["kms:Decrypt"]
      Resource  = "*" # This CMK only, as required by a KMS key policy.
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.aws_account_id }
        ArnLike = { "aws:SourceArn" = [
          "arn:aws:s3vectors:${var.aws_region}:${var.aws_account_id}:bucket/${var.name_prefix}-${var.aws_account_id}-vectors",
          "arn:aws:s3vectors:${var.aws_region}:${var.aws_account_id}:bucket/${var.name_prefix}-${var.aws_account_id}-vectors/index/*"
        ] }
        "ForAnyValue:StringEquals" = { "kms:EncryptionContextKeys" = ["aws:s3vectors:arn", "aws:s3vectors:resource-id"] }
      }
      }, {
      # Repair round 1 (F2): administration, use and grants of THIS key for the deployer role live here, in the key policy, and no IAM
      # statement of the deployer's phase14-main set grants them by tag. A foreign key tagged into the project's tag scope therefore
      # gains nothing. The principal is built from the account ID and the fixed deployer role name (no remote state); the role exists
      # (deployer root applied first), which CreateKey requires of every principal in a key policy. The account-root statement above
      # is kept: it is the lockout-safety and break-glass path (the policy must let the caller, this role, call PutKeyPolicy again:
      # https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html), and the runtime roles use the IAM delegation.
      Sid       = "DeployerAdministersThisKey"
      Effect    = "Allow"
      Principal = { AWS = local.deployer_role_arn }
      Action    = local.deployer_key_admin_actions
      Resource  = "*"
      }, {
      Sid       = "DeployerUsesThisKeyOnlyThroughServices"
      Effect    = "Allow"
      Principal = { AWS = local.deployer_role_arn }
      Action    = local.deployer_key_use_actions
      Resource  = "*"
      Condition = { StringEquals = { "kms:ViaService" = [for s in local.deployer_via_services : "${s}.${var.aws_region}.amazonaws.com"] } }
      }, {
      Sid       = "DeployerGrantsForAwsResourcesOnly"
      Effect    = "Allow"
      Principal = { AWS = local.deployer_role_arn }
      Action    = local.deployer_key_grant_actions
      Resource  = "*"
      Condition = { Bool = { "kms:GrantIsForAWSResource" = "true" } }
    }]
  })
  tags = var.tags
}
resource "aws_kms_alias" "data" {
  name          = "alias/${var.name_prefix}-data"
  target_key_id = aws_kms_key.data.key_id
}
resource "aws_iam_role" "task" {
  permissions_boundary = local.boundary_arn.runtime
  for_each             = local.services
  name                 = "${var.name_prefix}-${each.key}-task"
  assume_role_policy   = local.ecs_trust
  tags                 = var.tags
}
resource "aws_iam_role_policy" "task" {
  for_each = local.services
  name     = "${each.key}-data"
  role     = aws_iam_role.task[each.key].id
  policy   = jsonencode({ Version = "2012-10-17", Statement = concat(local.task_statements[each.key], local.additional_task_statements[each.key]) })
}
resource "aws_iam_role" "execution" {
  permissions_boundary = local.boundary_arn.runtime
  for_each             = local.services
  name                 = "${var.name_prefix}-${each.key}-execution"
  assume_role_policy   = local.ecs_trust
  tags                 = var.tags
}
resource "aws_iam_role_policy" "execution" {
  for_each = local.services
  name     = "${each.key}-bootstrap"
  role     = aws_iam_role.execution[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid      = "EcrAuthentication"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = ["*"] # This API does not support resource-level permissions.
      },
      {
        Sid      = "PullOwnServiceImage"
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"]
        Resource = [var.repository_arns[each.key]]
      },
      {
        Sid      = "WriteOwnServiceLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = ["arn:aws:logs:${var.aws_region}:${var.aws_account_id}:log-group:/${var.name_prefix}/${each.key}:log-stream:*"]
      }
      ], length(lookup(var.provider_secret_arns, each.key, [])) > 0 ? [{
        # Repair round 3: the provider API key container(s) this role's service needs (query-api: Anthropic; semantic-service and
        # embedding-worker: Voyage; graph-service: none). Exactly the name-plus-suffix patterns the root passes, never a wildcard. The containers use the
        # AWS-managed key aws/secretsmanager, so no kms:Decrypt statement belongs here (one would be needed only for a CMK).
        Sid      = "InjectProviderApiKey"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = tolist(var.provider_secret_arns[each.key])
        }] : [], length(lookup(var.service_secret_arns, each.key, [])) > 0 ? [{
        Sid      = "InjectOnlyConfiguredSecrets"
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = tolist(var.service_secret_arns[each.key])
        }, {
        Sid      = "DecryptInjectedSecretIfUsingProjectKey"
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.data.arn]
    }] : [])
  })
}
resource "aws_iam_role" "neptune_loader" {
  permissions_boundary = local.boundary_arn.runtime
  name                 = "${var.name_prefix}-neptune-loader"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.aws_account_id } }
    }]
  })
  tags = var.tags
}
resource "aws_iam_role_policy" "neptune_loader" {
  name = "read-graph-export"
  role = aws_iam_role.neptune_loader.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${var.bucket_arns["graph"]}/*"] },
      { Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = [var.bucket_arns["graph"]] },
      { Effect = "Allow", Action = ["kms:Decrypt", "kms:DescribeKey"], Resource = [aws_kms_key.data.arn] }
    ]
  })
}
resource "aws_iam_role" "emr_ec2" {
  permissions_boundary = local.boundary_arn.runtime
  name                 = "${var.name_prefix}-emr-ec2"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}
resource "aws_iam_instance_profile" "emr" {
  name = "${var.name_prefix}-emr"
  role = aws_iam_role.emr_ec2.name
  tags = var.tags
}
# EMR Hadoop/Spark jobs read/write S3 only. Separately operated storage loaders,
# not this instance role, own DynamoDB loading and runtime-audit access.
resource "aws_iam_role_policy" "emr_data" {
  name = "pipeline-data"
  role = aws_iam_role.emr_ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Sid = "ReadInputAndArtifacts", Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"], Resource = [for b in ["raw", "curated", "graph", "artifacts"] : "${var.bucket_arns[b]}/*"] },
      { Sid = "ListPipelineBuckets", Effect = "Allow", Action = ["s3:ListBucket", "s3:GetBucketLocation"], Resource = [for b in ["raw", "curated", "graph", "artifacts", "logs", "reports"] : var.bucket_arns[b]] },
      { Sid = "WriteOutputs", Effect = "Allow", Action = ["s3:PutObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"], Resource = [for b in ["curated", "graph", "artifacts", "logs", "reports"] : "${var.bucket_arns[b]}/*"] },
      { Sid = "CommitOutputTemporaryFiles", Effect = "Allow", Action = ["s3:DeleteObject"], Resource = flatten([for b, prefixes in var.emr_output_prefixes : [for prefix in prefixes : "${var.bucket_arns[b]}/${prefix}*"]]) },
      { Sid = "EncryptPipelineData", Effect = "Allow", Action = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"], Resource = [aws_kms_key.data.arn] }
    ]
  })
}
# Control-plane grants require the selected EMR/network runtime in 12B.
resource "aws_iam_role" "emr_service" {
  permissions_boundary = local.boundary_arn.emr_service
  name                 = "${var.name_prefix}-emr-service"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "elasticmapreduce.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = { StringEquals = { "aws:SourceAccount" = var.aws_account_id } }
    }]
  })
  tags = var.tags
}
# An independent role identity, deliberately without provisioning permissions.
# Populate only from the reviewed full-tree plan and the Phase 14 human gate.
resource "aws_iam_role" "deployment" {
  permissions_boundary = local.boundary_arn.runtime
  name                 = "${var.name_prefix}-deployment"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { AWS = var.deployment_trusted_principal_arn }, Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}
