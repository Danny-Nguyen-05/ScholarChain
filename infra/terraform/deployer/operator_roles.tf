# Replan W5a: the three operator roles for 14B/14C (loader, reader, cleanup). IAM only (free). They are NOT runtime roles: they carry no
# permissions boundary, the main root's deployer role cannot assume them (DenyAssumingMainRoles covers scholarchain-<env>-*), and
# toggling operator_roles_enabled to false and applying removes the roles and their inline policies.
#
# Trust: exactly the principal that can assume the deployer role (var.operator_principal_arn), MFA required, 4 h sessions.
# Permissions: data-plane only. No IAM, no infrastructure mutation, no aws-marketplace, no wildcard action, no wildcard service.
#
# Sign-in (replan W5a-2): each role is used exactly like the deployer role. The human signs in to the console as the IAM user (MFA),
# switches to the role (the trust MFA condition is evaluated by that console AssumeRole), and runs
# `aws login --profile scholarchain-<loader|reader|cleanup>`, which selects the already-assumed role session. The role therefore carries
# the SAME same-device login policy as the deployer (aws_iam_role_policy.operator_login, derived from local.login_policy so the two cannot
# drift). There is no source_profile, no role_arn profile and no second AssumeRole: role chaining would cap the session at 1 hour.
# max_session_duration 14400 is valid for this flow: a console switch gives min(role maximum, remaining IAM user console session).
#
# Naming contract with the main root (W5b), also in deployer/README.md:
#   roles   scholarchain-<env>-operator-loader | -operator-reader | -operator-cleanup
#   tunnel  task role scholarchain-<env>-neptune-tunnel-task, task-definition family scholarchain-<env>-neptune-tunnel in cluster
#           scholarchain-<env>, run as a ONE-OFF task (ecs:RunTask, ECS Exec on), execution role scholarchain-<env>-graph-service-execution,
#           graph-service security group (the only one Neptune admits)
# Key layouts (modules/storage): <prefix>/versions/<version>/<name>. Which bucket each tool writes (from the modules' code):
#   graph    NeptuneGraphLoader <graphPrefix>/versions/<fingerprint>/validated/..., SourceQualifications source-qualifications/versions/...
#   curated  the 28-table Parquet upload, under the run folder
#   rag      EmbeddingManifest <textPrefix>/versions/..., <textPrefix>/prepared/..., <textPrefix>/rejected/..., S3VectorStore vector-rejects/...,
#            RuntimeArtifactMain runtime-artifacts/<run prefix>/versions/... (G4, loader: create-only)
# A fourth role, scholarchain-<env>-operator-pipeline (G5/G6), is in operator_pipeline.tf: EMR step submission and the EMR artifact upload.

locals {
  op_run = coalesce(var.operator_run_prefix, "run-unset")

  op_role_names = {
    loader  = "${local.mp}-operator-loader"
    reader  = "${local.mp}-operator-reader"
    cleanup = "${local.mp}-operator-cleanup"
  }

  # Tunnel (one-off Fargate task + ECS Exec port forwarding to the Neptune endpoint).
  op_cluster_arn         = "${local.m_arn_ecs}:cluster/${local.mp}"
  op_tunnel_family       = "${local.mp}-neptune-tunnel"
  op_tunnel_taskdef_arn  = "${local.m_arn_ecs}:task-definition/${local.op_tunnel_family}:*"
  op_tunnel_task_arns    = "${local.m_arn_ecs}:task/${local.mp}/*"
  op_tunnel_task_role    = "${local.arn_iam}:role/${local.mp}-neptune-tunnel-task"
  op_tunnel_exec_role    = "${local.arn_iam}:role/${local.mp}-graph-service-execution"
  op_ssm_pf_document_arn = "arn:aws:ssm:${local.region}::document/AWS-StartPortForwardingSessionToRemoteHost"
  op_ssm_own_sessions    = "arn:aws:ssm:*:*:session/$${aws:userid}-*"
  c_op_cluster           = { "ecs:cluster" = local.op_cluster_arn }

  # Neptune: the cluster resource id exists only after base-apply; the fallback is every cluster of this account and region.
  op_neptune_arn = "arn:aws:neptune-db:${local.region}:${local.acct}:${coalesce(var.operator_neptune_cluster_resource_id, "cluster-*")}/*"

  op_tables      = ["RunLedger", "EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache"]
  op_table_arns  = flatten([for t in local.op_tables : ["${local.m_arn_ddb}:table/${local.mp}-${t}", "${local.m_arn_ddb}:table/${local.mp}-${t}/index/*"]])
  op_vector_arns = ["${local.m_arn_s3v}:bucket/${local.mp}-${local.acct}-vectors/index/*"]
  op_titan_arn   = "arn:aws:bedrock:${local.region}::foundation-model/amazon.titan-embed-text-v2:0"

  # G4 (runtime artifact contract): RuntimeArtifactMain (modules/storage) writes
  # runtime-artifacts/<run prefix>/versions/<run id>/runtime-subset-<sha256>.json (run it with --key-prefix runtime-artifacts/<run prefix>)
  # into the bucket the services read (SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET, default: the rag bucket). The loader may CREATE objects
  # there only (PutObject with If-None-Match, which S3ObjectStore.put always sends); it never gets the unconditional write that
  # op_object_arns_rw gives it on the other prefixes. The main root must add runtime-artifacts to the runtime roles' rag read prefixes.
  op_runtime_prefix = "runtime-artifacts/${local.op_run}"

  # S3 key prefixes per bucket (no leading or trailing slash).
  op_s3_prefixes = {
    graph   = [local.op_run, "source-qualifications"]
    curated = [local.op_run]
    rag     = [var.operator_embedding_text_prefix, "vector-rejects", local.op_runtime_prefix]
  }
  op_bucket_arn = { for b in keys(local.op_s3_prefixes) : b => "arn:aws:s3:::${local.mp}-${local.acct}-${b}" }
  # Every prefix (reader reads, cleanup deletes, output) and the prefixes the loader may write without the create-only condition.
  op_object_arns    = flatten([for b, ps in local.op_s3_prefixes : [for p in ps : "${local.op_bucket_arn[b]}/${p}/*"]])
  op_object_arns_rw = flatten([for b, ps in local.op_s3_prefixes : [for p in ps : "${local.op_bucket_arn[b]}/${p}/*" if p != local.op_runtime_prefix]])
  op_runtime_arn    = "${local.op_bucket_arn["rag"]}/${local.op_runtime_prefix}/*"

  # One s3:ListBucket (or ListBucketVersions) statement per bucket, limited to its prefixes.
  op_s3_list = { for b in sort(keys(local.op_s3_prefixes)) : b => {
    Resource  = [local.op_bucket_arn[b]]
    Condition = { StringEquals = local.c_region, StringLike = { "s3:prefix" = flatten([for p in local.op_s3_prefixes[b] : [p, "${p}/*"]]) } }
  } }

  # Project key, used only through the services that hold the encrypted data.
  op_kms_condition = {
    StringEquals               = merge(local.c_region, { "kms:ViaService" = [for s in ["s3", "dynamodb", "s3vectors"] : "${s}.${local.region}.amazonaws.com"] })
    "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = "alias/${local.mp}-data" }
  }

  op_loader_data = {
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid    = "S3ObjectsUnderRunPrefixes"
        Effect = "Allow"
        Action = [
          "s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes",
          "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
        ]
        Resource  = local.op_object_arns_rw
        Condition = { StringEquals = local.c_region }
      },
      {
        # G4: create-only. S3 evaluates s3:if-none-match from the request header; S3ObjectStore.put always sends If-None-Match: *.
        # A PutObject without the header (an overwrite) is not allowed. Single-part writes only (the artifact is at most 16 MiB), so
        # no multipart statement and no AbortMultipartUpload on this prefix.
        Sid       = "S3RuntimeArtifactCreateOnly"
        Effect    = "Allow"
        Action    = ["s3:PutObject"]
        Resource  = [local.op_runtime_arn]
        Condition = { StringEquals = local.c_region, Null = { "s3:if-none-match" = "false" } }
      },
      {
        # Read-back for the 412 comparison in S3ObjectStore.put and for the upload verification (HEAD needs s3:GetObject).
        Sid       = "S3RuntimeArtifactReadBack"
        Effect    = "Allow"
        Action    = ["s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes"]
        Resource  = [local.op_runtime_arn]
        Condition = { StringEquals = local.c_region }
      },
      ], [
      for b, v in local.op_s3_list : {
        Sid = "S3List${title(b)}Prefixes", Effect = "Allow", Action = ["s3:ListBucket"], Resource = v.Resource, Condition = v.Condition
      }
      ], [
      {
        Sid       = "ProjectKeyThroughServices"
        Effect    = "Allow"
        Action    = ["kms:GenerateDataKey", "kms:Decrypt"]
        Resource  = ["${local.arn_kms}:key/*"]
        Condition = local.op_kms_condition
      },
      {
        Sid       = "DynamoDbItemsOfTheSixTables"
        Effect    = "Allow"
        Action    = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem", "dynamodb:ConditionCheckItem"]
        Resource  = local.op_table_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3VectorsIndexData"
        Effect    = "Allow"
        Action    = ["s3vectors:GetIndex", "s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:QueryVectors"]
        Resource  = local.op_vector_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "InvokeTitanTextEmbeddingsV2Only"
        Effect    = "Allow"
        Action    = ["bedrock:InvokeModel"]
        Resource  = [local.op_titan_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "NeptuneBulkLoader"
        Effect    = "Allow"
        Action    = ["neptune-db:StartLoaderJob", "neptune-db:GetLoaderJobStatus", "neptune-db:ListLoaderJobs", "neptune-db:CancelLoaderJob", "neptune-db:GetEngineStatus"]
        Resource  = [local.op_neptune_arn]
        Condition = { StringEquals = local.c_region }
      },
    ])
  }

  # The Neptune tunnel: start and stop the one-off task, find its runtime id, port-forward through ECS Exec.
  op_loader_tunnel = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "RunTheTunnelTaskDefinitionInTheProjectCluster"
        Effect    = "Allow"
        Action    = ["ecs:RunTask"]
        Resource  = [local.op_tunnel_taskdef_arn]
        Condition = { StringEquals = local.c_region, ArnEquals = local.c_op_cluster }
      },
      {
        Sid       = "StopDescribeAndExecIntoTunnelTasks"
        Effect    = "Allow"
        Action    = ["ecs:StopTask", "ecs:DescribeTasks", "ecs:ExecuteCommand"]
        Resource  = [local.op_tunnel_task_arns, local.op_cluster_arn]
        Condition = { StringEquals = local.c_region, ArnEquals = local.c_op_cluster }
      },
      {
        # The ECS target form (task/<cluster>/*) and the document ARN are the ones Session Manager authorizes for ECS Exec port
        # forwarding; unverified against a live session (first live check: the 14B tunnel test).
        Sid       = "StartPortForwardingToTheTunnelTasksOnly"
        Effect    = "Allow"
        Action    = ["ssm:StartSession"]
        Resource  = [local.op_tunnel_task_arns, local.op_ssm_pf_document_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "TerminateAndUseOwnSessionsOnly"
        Effect    = "Allow"
        Action    = ["ssm:TerminateSession", "ssmmessages:OpenDataChannel"]
        Resource  = [local.op_ssm_own_sessions]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Global service: no RequestedRegion condition (same as the deployer's own iam statements).
        Sid       = "PassOnlyTheTunnelTaskRoleAndTheGraphServiceExecutionRole"
        Effect    = "Allow"
        Action    = ["iam:PassRole"]
        Resource  = [local.op_tunnel_task_role, local.op_tunnel_exec_role]
        Condition = { StringEquals = { "iam:PassedToService" = ["ecs-tasks.amazonaws.com"] } }
      },
    ]
  }

  op_reader = {
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid       = "NeptuneReadOnly"
        Effect    = "Allow"
        Action    = ["neptune-db:ReadDataViaQuery", "neptune-db:GetQueryStatus", "neptune-db:GetEngineStatus"]
        Resource  = [local.op_neptune_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "DynamoDbReadOfTheSixTables"
        Effect    = "Allow"
        Action    = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"]
        Resource  = local.op_table_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3VectorsRead"
        Effect    = "Allow"
        Action    = ["s3vectors:QueryVectors", "s3vectors:GetVectors"]
        Resource  = local.op_vector_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3ReadUnderRunPrefixes"
        Effect    = "Allow"
        Action    = ["s3:GetObject"]
        Resource  = local.op_object_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "ProjectKeyDecryptThroughServices"
        Effect    = "Allow"
        Action    = ["kms:Decrypt"]
        Resource  = ["${local.arn_kms}:key/*"]
        Condition = local.op_kms_condition
      },
      ], [
      for b, v in local.op_s3_list : {
        Sid = "S3List${title(b)}Prefixes", Effect = "Allow", Action = ["s3:ListBucket"], Resource = v.Resource, Condition = v.Condition
      }
    ])
  }

  op_cleanup = {
    Version = "2012-10-17"
    Statement = concat([
      {
        Sid       = "NeptuneRunDataCleanup"
        Effect    = "Allow"
        Action    = ["neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery", "neptune-db:ReadDataViaQuery"]
        Resource  = [local.op_neptune_arn]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "DynamoDbDeleteOfTheSixTables"
        Effect    = "Allow"
        Action    = ["dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:GetItem"]
        Resource  = local.op_table_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "S3VectorsDeleteAndList"
        Effect    = "Allow"
        Action    = ["s3vectors:DeleteVectors", "s3vectors:ListVectors"]
        Resource  = local.op_vector_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        # The buckets are versioned and the storage cleanup removes the exact owned key AND version after checking its metadata, so
        # the cleanup role also reads the object and deletes versions (a plain DeleteObject only adds a delete marker).
        Sid       = "S3DeleteUnderRunPrefixes"
        Effect    = "Allow"
        Action    = ["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:GetObject", "s3:GetObjectVersion"]
        Resource  = local.op_object_arns
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid       = "ProjectKeyDecryptThroughServices"
        Effect    = "Allow"
        Action    = ["kms:Decrypt"]
        Resource  = ["${local.arn_kms}:key/*"]
        Condition = local.op_kms_condition
      },
      ], [
      for b, v in local.op_s3_list : {
        Sid       = "S3List${title(b)}Prefixes"
        Effect    = "Allow"
        Action    = ["s3:ListBucket", "s3:ListBucketVersions"]
        Resource  = v.Resource
        Condition = v.Condition
      }
    ])
  }

  op_policies = {
    "loader--data"   = { role = "loader", part = "data", document = local.op_loader_data }
    "loader--tunnel" = { role = "loader", part = "tunnel", document = local.op_loader_tunnel }
    "reader--data"   = { role = "reader", part = "data", document = local.op_reader }
    "cleanup--data"  = { role = "cleanup", part = "data", document = local.op_cleanup }
  }

  # The deployer's login policy with only the Sid renamed: identical actions, resource (account, region, localhost client) and
  # signin:OAuthClientId = arn:aws:signin:::devtools/same-device condition.
  op_login_policy = {
    Version   = local.login_policy.Version
    Statement = [merge(local.login_policy.Statement[0], { Sid = "OperatorSameDeviceLogin" })]
  }

  # Output only, same shape as operator_caller_policy for the deployer. A same-account trust policy that names the IAM user is already
  # sufficient to assume a role, so this is a fallback for an AccessDenied on the console role switch, not a prerequisite.
  op_caller_policy = {
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AssumeOnlyTheOperatorRolesWithMfa"
      Effect    = "Allow"
      Action    = ["sts:AssumeRole"]
      Resource  = sort(concat([for k in keys(local.op_role_names) : "${local.arn_iam}:role/${local.op_role_names[k]}"], ["${local.arn_iam}:role/${local.op_pipeline_role_name}"]))
      Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    }]
  }

  op_trust_policy = {
    Version = "2012-10-17"
    Statement = [{
      Sid       = "HumanOperatorWithMfaOnly"
      Effect    = "Allow"
      Principal = { AWS = var.operator_principal_arn }
      Action    = "sts:AssumeRole"
      Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    }]
  }
}

resource "aws_iam_role" "operator" {
  for_each             = { for k, n in local.op_role_names : k => n if var.operator_roles_enabled }
  name                 = each.value
  description          = "ScholarChain 14B/14C ${each.key} operator: MFA-only, 4 h, data plane only, scoped to run prefix ${local.op_run}; same-device aws login."
  max_session_duration = 14400
  assume_role_policy   = jsonencode(local.op_trust_policy)
}

resource "aws_iam_role_policy" "operator" {
  for_each = { for k, p in local.op_policies : k => p if var.operator_roles_enabled }
  name     = "${local.op_role_names[each.value.role]}-${each.value.part}"
  role     = aws_iam_role.operator[each.value.role].id
  policy   = jsonencode(each.value.document)
}

# Same-device `aws login` for each operator role, always attached with the role (same document as aws_iam_role_policy.login of the
# deployer). Separate from aws_iam_role_policy.operator so the data-plane invariants (no sign-in or other service in those four
# documents) keep holding. It grants sign-in only.
resource "aws_iam_role_policy" "operator_login" {
  for_each = { for k, n in local.op_role_names : k => n if var.operator_roles_enabled }
  name     = "${each.value}-same-device-login"
  role     = aws_iam_role.operator[each.key].id
  policy   = jsonencode(local.op_login_policy)
}
