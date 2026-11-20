# Replan G-DEPLOYER (14B, gaps G5 and G6): the fourth operator role, scholarchain-<env>-operator-pipeline. IAM only (free), created in the
# SAME single deployer apply as the other operator roles (operator_roles_enabled) and removed with them.
#
# Who runs scripts/run-bounded-pipeline.sh --execute and the EMR artifact upload? This role, not the deployer role and not the loader:
#   * the deployer role has a 1 hour session (a pipeline run is capped at 90 minutes of cluster time plus the upload) and is the
#     infrastructure-administration role; adding step submission (arbitrary commands on the cluster) to it widens the wrong role;
#   * the loader holds Bedrock, DynamoDB, S3 Vectors and Neptune loader rights that a pipeline run never needs, and the reverse;
#   * a separate role gets the same sign-in (console Switch Role from the IAM user with MFA, then `aws login`), a 4 hour session and
#     no role chaining, exactly like the other operator roles.
#
# What the pipeline calls from the laptop (read from scripts/run-bounded-pipeline.sh; sts:GetCallerIdentity needs no permission):
#   aws emr describe-cluster, get-auto-termination-policy                         (cluster check, before any paid step; AWS CLI v2 has no
#   list-instance-groups command: the instance groups come from describe-cluster, whose CLI v2 customization calls ListInstanceGroups and
#   ListBootstrapActions; add-steps calls DescribeCluster first)
#   aws emr add-steps, describe-step, cancel-steps                                (submit, poll, cancel)
# The steps themselves (S3 stage-in, copy-out, the bootstrap downloads) run on the nodes with the EMR instance role, not with this role.
# Local files are hashed locally. So this role needs: those seven EMR actions on the project cluster, an upload path for the EMR
# artifacts and datasets, and read access to the outputs and the cluster logs. Nothing else.
#
# Key contract (artifacts bucket scholarchain-<env>-<account>-artifacts), the run folder is operator_run_prefix:
#   emr/<run>/...        bootstrap script, job and Hadoop/ER JARs, the four step programs, policy/config files, and the EMR input
#                        datasets (emr/<run>/input/<size>/datasets/samples/...). Every s3:// URI in emr_config and the pipeline flags
#                        (--input-prefix, --hadoop-submit-jar, ...) lies below this prefix.  CREATE-ONLY for this role.
#   pipeline/<run>/...   --output-prefix s3://<artifacts>/pipeline/<run>  (results go to <prefix>/<run-id>/{hadoop,er,spark,results,config}/).
#                        Written by the EMR instance role; this role only reads it. pipeline/ is the prefix the main root's
#                        emr_output_prefixes allows the instance role to clean up.
# Logs: the EMR cluster log_uri is s3://<logs bucket>/emr/ (modules/emr); this role reads that prefix only.
#
# Create-only: S3 evaluates s3:if-none-match from the If-None-Match request header (documented for IAM identity policies at
# https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html). PutObject and CompleteMultipartUpload must carry
# it; CreateMultipartUpload and UploadPart cannot, so they are allowed by the second statement through s3:ObjectCreationOperation = false.
# Upload with `aws s3api put-object --if-none-match '*'` (scripts/upload-slice.sh does) or a multipart client that sets it on the
# final call. Whether S3 enforces the key in an identity policy exactly as documented has not been run here (UNVERIFIED).

locals {
  op_pipeline_role_name = "${local.mp}-operator-pipeline"

  op_emr_prefix      = "emr/${local.op_run}"
  op_pipeline_prefix = "pipeline/${local.op_run}"
  op_logs_prefix     = "emr"

  op_artifacts_bucket_arn = "arn:aws:s3:::${local.mp}-${local.acct}-artifacts"
  op_logs_bucket_arn      = "arn:aws:s3:::${local.mp}-${local.acct}-logs"
  op_emr_upload_arn       = "${local.op_artifacts_bucket_arn}/${local.op_emr_prefix}/*"
  op_pipeline_out_arn     = "${local.op_artifacts_bucket_arn}/${local.op_pipeline_prefix}/*"
  op_emr_logs_arn         = "${local.op_logs_bucket_arn}/${local.op_logs_prefix}/*"
  op_emr_cluster_arns     = ["arn:aws:elasticmapreduce:${local.region}:${local.acct}:cluster/*"]

  # The cluster must carry all three tags Terraform sets (RunJobFlow requires them as request tags in the phase14-main set).
  c_op_cluster_tags = {
    "aws:ResourceTag/project"            = local.m_project
    "aws:ResourceTag/environment"        = var.main_environment
    "aws:ResourceTag/scholarchain:stack" = var.main_emr_stack_tag_value
  }

  op_pipeline = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EmrReadTheProjectClusterAndItsSteps"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:DescribeCluster", "elasticmapreduce:ListInstanceGroups", "elasticmapreduce:ListBootstrapActions", "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:DescribeStep"]
        Resource  = local.op_emr_cluster_arns
        Condition = { StringEquals = merge(local.c_region, local.c_op_cluster_tags) }
      },
      {
        # Steps are command-runner.jar commands that run as the EMR instance role (read raw, curated, graph, artifacts; write
        # curated, graph, artifacts, logs, reports). That is inherent to submitting steps; the tag conditions keep it on the project cluster.
        Sid       = "EmrSubmitAndCancelStepsOnTheProjectClusterOnly"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:AddJobFlowSteps", "elasticmapreduce:CancelSteps"]
        Resource  = local.op_emr_cluster_arns
        Condition = { StringEquals = merge(local.c_region, local.c_op_cluster_tags) }
      },
      {
        Sid       = "S3EmrArtifactsCreateOnlyWithIfNoneMatch"
        Effect    = "Allow"
        Action    = ["s3:PutObject"]
        Resource  = [local.op_emr_upload_arn]
        Condition = { StringEquals = local.c_region, Null = { "s3:if-none-match" = "false" } }
      },
      {
        Sid       = "S3EmrArtifactsMultipartPartsWithoutTheHeader"
        Effect    = "Allow"
        Action    = ["s3:PutObject"]
        Resource  = [local.op_emr_upload_arn]
        Condition = { StringEquals = local.c_region, Bool = { "s3:ObjectCreationOperation" = "false" } }
      },
      {
        # Checksum read-back after the upload (head-object, get-object-attributes) and cleanup of an abandoned multipart upload.
        Sid       = "S3EmrArtifactsReadBackAndMultipartMaintenance"
        Effect    = "Allow"
        Action    = ["s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]
        Resource  = [local.op_emr_upload_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3PipelineOutputsAndEmrLogsReadOnly"
        Effect    = "Allow"
        Action    = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource  = [local.op_pipeline_out_arn, local.op_emr_logs_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3ListArtifactsRunPrefixes"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = [local.op_artifacts_bucket_arn]
        Condition = { StringEquals = local.c_region, StringLike = { "s3:prefix" = [local.op_emr_prefix, "${local.op_emr_prefix}/*", local.op_pipeline_prefix, "${local.op_pipeline_prefix}/*"] } }
      },
      {
        Sid       = "S3ListEmrLogsPrefix"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = [local.op_logs_bucket_arn]
        Condition = { StringEquals = local.c_region, StringLike = { "s3:prefix" = [local.op_logs_prefix, "${local.op_logs_prefix}/*"] } }
      },
      {
        # The buckets are SSE-KMS with the project data key: uploads need a data key, reads need Decrypt. S3 only (no other service).
        Sid      = "ProjectKeyThroughS3Only"
        Effect   = "Allow"
        Action   = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource = ["${local.arn_kms}:key/*"]
        Condition = {
          StringEquals               = merge(local.c_region, { "kms:ViaService" = "s3.${local.region}.amazonaws.com" })
          "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = "alias/${local.mp}-data" }
        }
      },
    ]
  }
}

resource "aws_iam_role" "operator_pipeline" {
  count                = var.operator_roles_enabled ? 1 : 0
  name                 = local.op_pipeline_role_name
  description          = "ScholarChain 14B/15 pipeline operator: MFA-only, 4 h, EMR step submission on the project cluster and the EMR artifact upload under ${local.op_emr_prefix}/; same-device aws login."
  max_session_duration = 14400
  assume_role_policy   = jsonencode(local.op_trust_policy)
}

resource "aws_iam_role_policy" "operator_pipeline" {
  count  = var.operator_roles_enabled ? 1 : 0
  name   = "${local.op_pipeline_role_name}-data"
  role   = aws_iam_role.operator_pipeline[0].id
  policy = jsonencode(local.op_pipeline)
}

# Same document as every other operator role (derived from the deployer's login policy; only the Sid differs).
resource "aws_iam_role_policy" "operator_pipeline_login" {
  count  = var.operator_roles_enabled ? 1 : 0
  name   = "${local.op_pipeline_role_name}-same-device-login"
  role   = aws_iam_role.operator_pipeline[0].id
  policy = jsonencode(local.op_login_policy)
}
