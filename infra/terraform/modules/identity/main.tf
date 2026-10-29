locals {
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
  }] : []) }
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
    }]
  })
  tags = var.tags
}
resource "aws_kms_alias" "data" {
  name          = "alias/${var.name_prefix}-data"
  target_key_id = aws_kms_key.data.key_id
}
resource "aws_iam_role" "task" {
  for_each           = local.services
  name               = "${var.name_prefix}-${each.key}-task"
  assume_role_policy = local.ecs_trust
  tags               = var.tags
}
resource "aws_iam_role_policy" "task" {
  for_each = local.services
  name     = "${each.key}-data"
  role     = aws_iam_role.task[each.key].id
  policy   = jsonencode({ Version = "2012-10-17", Statement = local.task_statements[each.key] })
}
resource "aws_iam_role" "execution" {
  for_each           = local.services
  name               = "${var.name_prefix}-${each.key}-execution"
  assume_role_policy = local.ecs_trust
  tags               = var.tags
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
      ], length(lookup(var.service_secret_arns, each.key, [])) > 0 ? [{
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
  name = "${var.name_prefix}-neptune-loader"
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
  name = "${var.name_prefix}-emr-ec2"
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
      { Sid = "EncryptPipelineData", Effect = "Allow", Action = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"], Resource = [aws_kms_key.data.arn] }
    ]
  })
}
# Control-plane grants require the selected EMR/network runtime in 12B.
resource "aws_iam_role" "emr_service" {
  name = "${var.name_prefix}-emr-service"
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
  name = "${var.name_prefix}-deployment"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { AWS = var.deployment_trusted_principal_arn }, Action = "sts:AssumeRole" }]
  })
  tags = var.tags
}
