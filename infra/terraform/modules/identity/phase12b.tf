locals {
  # Bedrock grants, one per model purpose. Without an inference profile the grant is the single in-region foundation-model ARN
  # (unchanged Phase 12B behavior). With a profile (a system-defined cross-region profile such as us.anthropic.<model>, which
  # Bedrock requires for models that have no in-region on-demand endpoint) AWS documents a three-part grant:
  #   1. the profile in the home region (arn:aws:bedrock:<home>:<account>:inference-profile/<profile id>);
  #   2. the foundation model in EVERY region the profile routes to, usable only through that profile
  #      (condition bedrock:InferenceProfileArn, so the model cannot be invoked directly in those regions);
  #   3. for a global.* profile only, the region-less foundation-model ARN with aws:RequestedRegion = "unspecified".
  # https://docs.aws.amazon.com/bedrock/latest/userguide/global-cross-region-inference.html (the policy shape and the condition)
  # https://aws.amazon.com/blogs/machine-learning/securing-amazon-bedrock-cross-region-inference-geographic-and-global/
  # The Converse API (which modules/rag RuntimeLlm calls, not ConverseStream) needs only bedrock:InvokeModel; streaming
  # (bedrock:InvokeModelWithResponseStream) is deliberately not granted because no module calls a streaming operation.
  bedrock_purposes = {
    embedding = { sid = "InvokeConfiguredEmbedding", model = var.embedding_model_id, profile = var.embedding_inference_profile_id, regions = var.embedding_inference_profile_regions }
    synthesis = { sid = "InvokeConfiguredSynthesis", model = var.synthesis_model_id, profile = var.synthesis_inference_profile_id, regions = var.synthesis_inference_profile_regions }
  }
  bedrock_home_model_arns = { for k, v in local.bedrock_purposes : k => v.model == null ? [] : ["arn:aws:bedrock:${var.aws_region}::foundation-model/${v.model}"] }
  bedrock_profile_arns    = { for k, v in local.bedrock_purposes : k => v.model == null || v.profile == null ? null : "arn:aws:bedrock:${var.aws_region}:${var.aws_account_id}:inference-profile/${v.profile}" }
  bedrock_statements = { for k, v in local.bedrock_purposes : k => concat(
    v.model != null && v.profile == null ? [{
      Sid = "${v.sid}Model", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = local.bedrock_home_model_arns[k]
    }] : [],
    v.model != null && v.profile != null ? [{
      Sid = "${v.sid}Profile", Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = [local.bedrock_profile_arns[k]]
    }] : [],
    v.model != null && v.profile != null ? [{
      Sid       = "${v.sid}ModelViaProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"]
      Resource  = [for r in v.regions : "arn:aws:bedrock:${r}::foundation-model/${v.model}"]
      Condition = { StringEquals = { "bedrock:InferenceProfileArn" = local.bedrock_profile_arns[k] } }
    }] : [],
    v.model != null && try(startswith(v.profile, "global."), false) ? [{
      Sid       = "${v.sid}ModelViaGlobalProfile", Effect = "Allow", Action = ["bedrock:InvokeModel"]
      Resource  = ["arn:aws:bedrock:::foundation-model/${v.model}"]
      Condition = { StringEquals = { "aws:RequestedRegion" = "unspecified", "bedrock:InferenceProfileArn" = local.bedrock_profile_arns[k] } }
    }] : [])
  }
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
    [for st in local.bedrock_statements["embedding"] : st if contains(["semantic-service", "embedding-worker"], service)],
    [for st in local.bedrock_statements["synthesis"] : st if service == "query-api"]
  ) }
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
