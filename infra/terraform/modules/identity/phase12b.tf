locals {
  embedding_model_arns = var.embedding_model_id == null ? [] : ["arn:aws:bedrock:${var.aws_region}::foundation-model/${var.embedding_model_id}"]
  synthesis_model_arns = var.synthesis_model_id == null ? [] : ["arn:aws:bedrock:${var.aws_region}::foundation-model/${var.synthesis_model_id}"]
  additional_task_statements = { for service in local.services : service => concat(
    service == "graph-service" && var.neptune_data_arn != null ? [{
      Sid      = "ReadOnlyNeptuneGraph", Effect = "Allow",
      Action   = ["neptune-db:ReadDataViaQuery", "neptune-db:GetQueryStatus", "neptune-db:CancelQuery"],
      Resource = [var.neptune_data_arn], Condition = { StringEquals = { "neptune-db:QueryLanguage" = "OpenCypher" } }
    }] : [],
    service == "graph-service" && var.neptune_data_arn != null ? [{
      Sid = "ReadNeptuneEngineStatus", Effect = "Allow", Action = ["neptune-db:GetEngineStatus"], Resource = [var.neptune_data_arn]
    }] : [],
    contains(["semantic-service", "embedding-worker"], service) ? [{
      Sid = "ReadConfiguredVectorIndexes", Effect = "Allow", Action = ["s3vectors:GetIndex", "s3vectors:GetVectors", "s3vectors:QueryVectors"], Resource = values(var.vector_index_arns)
    }] : [],
    service == "embedding-worker" ? [{
      Sid = "WriteConfiguredEmbeddingVectors", Effect = "Allow", Action = ["s3vectors:PutVectors"], Resource = values(var.vector_index_arns)
    }] : [],
    contains(["semantic-service", "embedding-worker"], service) && length(local.embedding_model_arns) > 0 ? [{
      Sid = "InvokeConfiguredEmbeddingModel", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = local.embedding_model_arns
    }] : [],
    service == "query-api" && length(local.synthesis_model_arns) > 0 ? [{
      Sid = "InvokeConfiguredSynthesisModel", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = local.synthesis_model_arns
  }] : []) }
}
# This explicit policy has no broad default. Even a mock activation must supply
# concrete service permissions; real12C security review verifies them for the selected runtime.
resource "aws_iam_role_policy" "emr_control" {
  count  = var.enable_emr && var.emr_service_policy_json != null ? 1 : 0
  name   = "selected-emr-control-plane"
  role   = aws_iam_role.emr_service.id
  policy = var.emr_service_policy_json
}
# EBS encryption is performed through the EMR service role. The EC2 role keeps
# only its S3 data-key permissions; EBS grants are limited to this project CMK.
resource "aws_iam_role_policy" "emr_disk_encryption" {
  count = var.enable_emr && var.emr_service_policy_json != null ? 1 : 0
  name  = "project-encrypted-emr-disks"
  role  = aws_iam_role.emr_service.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "UseProjectKeyForEbs", Effect = "Allow", Action = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKeyWithoutPlaintext", "kms:ReEncryptFrom", "kms:ReEncryptTo"], Resource = [aws_kms_key.data.arn] },
    { Sid = "GrantOnlyAwsResourceUseOfProjectKey", Effect = "Allow", Action = ["kms:CreateGrant"], Resource = [aws_kms_key.data.arn], Condition = { Bool = { "kms:GrantIsForAWSResource" = "true" } } }
  ] })
}
