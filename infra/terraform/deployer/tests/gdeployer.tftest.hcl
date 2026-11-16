# Replan G-DEPLOYER (14B): runtime-artifact write for the loader (G4), the operator-pipeline role (G5: EMR step submission, G6: EMR artifact upload).
# Hand-derived expectations (every literal below is written out from the intended contract, not copied from the policy). Mock provider; no AWS call is
# possible. Run with `terraform test` in this root.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id              = "111122223333"
  operator_principal_arn  = "arn:aws:iam::111122223333:user/example-operator"
  owner                   = "example-owner"
  enabled_permission_sets = ["phase14-main"]
  operator_roles_enabled  = true
  operator_run_prefix     = "run-20261115"
}

# ---- G4: loader writes the runtime artifact, create-only, on exactly runtime-artifacts/<run prefix>/ -----------------------------------------

run "g4_loader_runtime_artifact_put_is_create_only_on_exactly_the_run_prefix" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3RuntimeArtifactCreateOnly" && st.Effect == "Allow" && st.Action == ["s3:PutObject"] &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*"] &&
      st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" }, Null = { "s3:if-none-match" = "false" } }
    ])
    error_message = "The loader may PutObject on runtime-artifacts/<run prefix>/* of the rag bucket only with the If-None-Match header present (Null s3:if-none-match = false) and in us-east-2."
  }
  assert {
    condition = length([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st if contains(st.Action, "s3:PutObject") && anytrue([for r in st.Resource : strcontains(r, "runtime-artifacts")])
    ]) == 1
    error_message = "Exactly one statement lets the loader write under runtime-artifacts/: the create-only one."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      !contains(st.Action, "s3:PutObject") || st.Sid == "S3RuntimeArtifactCreateOnly" || !anytrue([for r in st.Resource : strcontains(r, "runtime-artifacts")])
    ])
    error_message = "The unconditional write statement does not cover runtime-artifacts/ (an overwrite there is impossible)."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3RuntimeArtifactReadBack" && toset(st.Action) == toset(["s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes"]) &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*"] && st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" } }
    ])
    error_message = "The loader can read back (412 comparison, HEAD verification) exactly the same prefix: GetObject, GetObjectVersion, GetObjectAttributes."
  }
  assert {
    condition = !anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      anytrue([for a in st.Action : contains(["s3:DeleteObject", "s3:DeleteObjectVersion", "s3:PutObjectAcl", "s3:PutObjectTagging", "s3:BypassGovernanceRetention"], a)]) ||
      (st.Sid == "S3RuntimeArtifactCreateOnly" && (contains(st.Action, "s3:AbortMultipartUpload") || length(st.Action) != 1))
    ])
    error_message = "The loader gains no delete, ACL, tagging or multipart action for the runtime artifact."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3ObjectsUnderRunPrefixes" && length(st.Resource) == 5 && !anytrue([for r in st.Resource : strcontains(r, "runtime-artifacts")])
    ]) && contains(output.operator_scope.s3_object_arns, "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*") && length(output.operator_scope.s3_object_arns) == 6
    error_message = "The unconditional-write statement keeps its five prefixes and excludes the runtime prefix; the all-prefixes output (reader, cleanup) has six including it."
  }
}

run "g4_runtime_artifact_prefix_follows_the_run_prefix_and_the_environment" {
  command = plan
  variables {
    operator_run_prefix = "run-abc-7"
    main_environment    = "abcdefghij"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3RuntimeArtifactCreateOnly" && st.Resource == ["arn:aws:s3:::scholarchain-abcdefghij-111122223333-rag/runtime-artifacts/run-abc-7/*"]
    ])
    error_message = "The runtime-artifact ARN is built from the run prefix and main_environment (no hard-coded values)."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.operator["loader--data"].policy, "run-20261115") && !strcontains(aws_iam_role_policy.operator["loader--data"].policy, "scholarchain-course")
    error_message = "No stale run prefix or environment in the loader policy."
  }
  assert {
    condition     = length(aws_iam_role_policy.operator["loader--data"].policy) < 6144 && length(aws_iam_role_policy.operator["loader--data"].policy) + length(aws_iam_role_policy.operator["loader--tunnel"].policy) + length(aws_iam_role_policy.operator_login["loader"].policy) < 10240
    error_message = "The loader documents stay under 6144 characters each and 10240 together with the tunnel and login policies, with the longest environment name."
  }
}

run "g4_reader_reads_and_cleanup_deletes_the_runtime_artifact_prefix_and_nobody_else_writes_it" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement :
      st.Action == ["s3:GetObject"] && contains(st.Resource, "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*")
    ])
    error_message = "The reader can GetObject the runtime artifact."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["cleanup--data"].policy).Statement :
      st.Sid == "S3DeleteUnderRunPrefixes" && contains(st.Resource, "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*")
      ]) && anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["cleanup--data"].policy).Statement :
      st.Action == ["s3:ListBucket", "s3:ListBucketVersions"] && st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-rag"] && contains(st.Condition.StringLike["s3:prefix"], "runtime-artifacts/run-20261115/*")
    ])
    error_message = "The cleanup role can list and delete the runtime artifact versions (the rag bucket is versioned)."
  }
  assert {
    condition = !anytrue(flatten([
      for k in ["reader--data", "cleanup--data"] : [
        for st in jsondecode(aws_iam_role_policy.operator[k].policy).Statement : contains(st.Action, "s3:PutObject")
      ]
    ])) && !anytrue([for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : anytrue([for r in st.Resource : strcontains(r, "runtime-artifacts")])])
    error_message = "Neither reader, cleanup nor pipeline can write or touch runtime-artifacts/."
  }
  assert {
    condition     = output.operator_scope.runtime_artifact_arn == "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*"
    error_message = "operator_scope shows the runtime-artifact ARN."
  }
}

# ---- G5/G6: the operator-pipeline role ------------------------------------------------------------------------------------------------------

run "pipeline_role_is_absent_while_the_operator_roles_are_disabled" {
  command = plan
  variables {
    operator_roles_enabled = false
    operator_run_prefix    = null
  }

  assert {
    condition     = length(aws_iam_role.operator_pipeline) == 0 && length(aws_iam_role_policy.operator_pipeline) == 0 && length(aws_iam_role_policy.operator_pipeline_login) == 0 && output.operator_role_arns == null
    error_message = "Nothing of the pipeline role is planned with the toggle off (an apply with false removes it)."
  }
}

run "pipeline_role_has_the_contract_name_mfa_trust_four_hours_and_no_boundary" {
  command = plan

  assert {
    condition     = aws_iam_role.operator_pipeline[0].name == "scholarchain-course-operator-pipeline" && aws_iam_role.operator_pipeline[0].max_session_duration == 14400
    error_message = "Name scholarchain-<env>-operator-pipeline, 4 hour maximum session."
  }
  assert {
    condition = (
      jsondecode(aws_iam_role.operator_pipeline[0].assume_role_policy).Statement[0].Principal == jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Principal &&
      jsondecode(aws_iam_role.operator_pipeline[0].assume_role_policy).Statement[0].Action == "sts:AssumeRole" &&
      jsondecode(aws_iam_role.operator_pipeline[0].assume_role_policy).Statement[0].Condition == { Bool = { "aws:MultiFactorAuthPresent" = "true" } } &&
      length(jsondecode(aws_iam_role.operator_pipeline[0].assume_role_policy).Statement) == 1 &&
      !strcontains(aws_iam_role.operator_pipeline[0].assume_role_policy, "*") && !strcontains(aws_iam_role.operator_pipeline[0].assume_role_policy, ":role/")
    )
    error_message = "Trust: exactly the human IAM user, sts:AssumeRole, MFA required, no wildcard, no role principal (a console switch from the user is not role chaining)."
  }
  assert {
    condition     = aws_iam_role.operator_pipeline[0].permissions_boundary == null || aws_iam_role.operator_pipeline[0].permissions_boundary == ""
    error_message = "Not a runtime role: no permissions boundary."
  }
  assert {
    condition = (
      aws_iam_role_policy.operator_pipeline_login[0].name == "scholarchain-course-operator-pipeline-same-device-login" &&
      jsondecode(aws_iam_role_policy.operator_pipeline_login[0].policy).Statement[0].Action == jsondecode(aws_iam_role_policy.login.policy).Statement[0].Action &&
      jsondecode(aws_iam_role_policy.operator_pipeline_login[0].policy).Statement[0].Resource == ["arn:aws:signin:us-east-2:111122223333:oauth2/public-client/localhost"] &&
      jsondecode(aws_iam_role_policy.operator_pipeline_login[0].policy).Statement[0].Condition == { StringEquals = { "signin:OAuthClientId" = "arn:aws:signin:::devtools/same-device" } }
    )
    error_message = "The pipeline role carries the same same-device aws login policy as the deployer and the other operator roles."
  }
  assert {
    condition     = toset(keys(output.operator_role_arns)) == toset(["loader", "reader", "cleanup", "pipeline"])
    error_message = "operator_role_arns lists the four roles (the ARN values are computed by AWS and unknown in a mock plan)."
  }
  assert {
    condition     = anytrue([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement : st.Effect == "Deny" && st.Action == ["sts:AssumeRole"] && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-*"]])
    error_message = "The deployer's explicit deny of assuming scholarchain-<env>-* roles covers the pipeline role too."
  }
}

run "pipeline_actions_are_exactly_the_approved_set" {
  command = plan

  assert {
    condition = toset(flatten([for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : st.Action])) == toset([
      "elasticmapreduce:DescribeCluster", "elasticmapreduce:ListInstanceGroups", "elasticmapreduce:ListBootstrapActions", "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:DescribeStep",
      "elasticmapreduce:AddJobFlowSteps", "elasticmapreduce:CancelSteps",
      "s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts", "s3:ListBucket",
      "kms:GenerateDataKey", "kms:Decrypt",
    ])
    error_message = "The pipeline role's actions are exactly the seven EMR actions the pipeline script's CLI calls make (describe-cluster also calls ListInstanceGroups and ListBootstrapActions), the S3 upload/read-back/list actions and the two KMS data-key actions."
  }
  assert {
    condition = !anytrue(flatten([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : [
        for a in st.Action : contains([
          "elasticmapreduce:RunJobFlow", "elasticmapreduce:TerminateJobFlows", "elasticmapreduce:ListClusters", "elasticmapreduce:ModifyCluster", "elasticmapreduce:SetTerminationProtection",
          "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy", "elasticmapreduce:AddInstanceGroups", "elasticmapreduce:ModifyInstanceGroups",
          "elasticmapreduce:AddTags", "elasticmapreduce:ListSteps", "elasticmapreduce:CreateSecurityConfiguration",
          "s3:DeleteObject", "s3:DeleteObjectVersion", "s3:DeleteBucket", "s3:PutBucketPolicy", "s3:PutObjectAcl", "s3:BypassGovernanceRetention",
        ], a)
      ]
    ]))
    error_message = "The pipeline role cannot create or terminate a cluster, change its capacity or termination policy, tag it, delete objects or touch bucket policy."
  }
  assert {
    condition = !anytrue(flatten([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : [
        for a in st.Action : startswith(a, "iam:") || startswith(a, "sts:") || startswith(a, "ec2:") || startswith(a, "rds:") || startswith(a, "ecs:") || startswith(a, "ssm:") ||
        startswith(a, "dynamodb:") || startswith(a, "s3vectors:") || startswith(a, "bedrock:") || startswith(a, "neptune-db:") || startswith(a, "secretsmanager:") ||
        startswith(a, "budgets:") || startswith(a, "aws-marketplace:") || startswith(a, "logs:") || startswith(a, "signin:")
      ]
    ]))
    error_message = "No IAM, STS, network, data-plane of other services, billing or Marketplace action in the pipeline policy (the login policy is the separate inline document)."
  }
}

run "pipeline_emr_actions_are_scoped_to_clusters_carrying_the_three_project_tags" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "EmrReadTheProjectClusterAndItsSteps" && st.Effect == "Allow" &&
      toset(st.Action) == toset(["elasticmapreduce:DescribeCluster", "elasticmapreduce:ListInstanceGroups", "elasticmapreduce:ListBootstrapActions", "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:DescribeStep"]) &&
      st.Resource == ["arn:aws:elasticmapreduce:us-east-2:111122223333:cluster/*"] &&
      st.Condition == { StringEquals = {
        "aws:RequestedRegion"                = "us-east-2"
        "aws:ResourceTag/project"            = "scholarchain"
        "aws:ResourceTag/environment"        = "course"
        "aws:ResourceTag/scholarchain:stack" = "main-emr"
      } }
    ])
    error_message = "The cluster checks (describe-cluster with its ListInstanceGroups and ListBootstrapActions calls, get-auto-termination-policy, describe-step) need the project, environment and stack resource tags and us-east-2."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "EmrSubmitAndCancelStepsOnTheProjectClusterOnly" && st.Effect == "Allow" &&
      toset(st.Action) == toset(["elasticmapreduce:AddJobFlowSteps", "elasticmapreduce:CancelSteps"]) && length(st.Action) == 2 &&
      st.Resource == ["arn:aws:elasticmapreduce:us-east-2:111122223333:cluster/*"] &&
      st.Condition == { StringEquals = {
        "aws:RequestedRegion"                = "us-east-2"
        "aws:ResourceTag/project"            = "scholarchain"
        "aws:ResourceTag/environment"        = "course"
        "aws:ResourceTag/scholarchain:stack" = "main-emr"
      } }
    ])
    error_message = "AddJobFlowSteps and CancelSteps are separate from the reads, on cluster/* with all three resource tags and the region."
  }
  assert {
    condition = length([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st if anytrue([for a in st.Action : startswith(a, "elasticmapreduce:")])
      ]) == 2 && alltrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      !anytrue([for a in st.Action : startswith(a, "elasticmapreduce:")]) || (!contains(st.Resource, "*") && st.Resource == ["arn:aws:elasticmapreduce:us-east-2:111122223333:cluster/*"])
    ])
    error_message = "Exactly two EMR statements and none uses Resource * (every EMR action in this role has the cluster resource type)."
  }
}

run "pipeline_emr_stack_tag_and_environment_follow_the_variables" {
  command = plan
  variables {
    main_environment         = "abcdefghij"
    main_emr_stack_tag_value = "other-emr"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "EmrSubmitAndCancelStepsOnTheProjectClusterOnly" && st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "other-emr" && st.Condition.StringEquals["aws:ResourceTag/environment"] == "abcdefghij"
    ])
    error_message = "The cluster tag conditions use main_emr_stack_tag_value and main_environment."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.operator_pipeline[0].policy, "scholarchain-course") && !strcontains(aws_iam_role_policy.operator_pipeline[0].policy, "main-emr") && length(aws_iam_role_policy.operator_pipeline[0].policy) < 6144
    error_message = "No hard-coded environment or stack tag; the document stays under 6144 characters with the longest environment name."
  }
}

run "pipeline_artifact_upload_is_create_only_below_emr_run_prefix_in_the_artifacts_bucket" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3EmrArtifactsCreateOnlyWithIfNoneMatch" && st.Effect == "Allow" && st.Action == ["s3:PutObject"] &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"] &&
      st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" }, Null = { "s3:if-none-match" = "false" } }
    ])
    error_message = "PutObject (and CompleteMultipartUpload) needs the If-None-Match header, only below emr/<run prefix>/ of the artifacts bucket."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3EmrArtifactsMultipartPartsWithoutTheHeader" && st.Effect == "Allow" && st.Action == ["s3:PutObject"] &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"] &&
      st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" }, Bool = { "s3:ObjectCreationOperation" = "false" } }
    ])
    error_message = "CreateMultipartUpload and UploadPart (which cannot carry the header) are allowed only through s3:ObjectCreationOperation = false, same prefix."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      !contains(st.Action, "s3:PutObject") || (st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"] && (can(st.Condition.Null["s3:if-none-match"]) || can(st.Condition.Bool["s3:ObjectCreationOperation"])))
    ])
    error_message = "Every statement that allows PutObject is limited to the emr/<run> prefix and carries a create-only condition (a mutation that drops the condition or widens the prefix fails here)."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3EmrArtifactsReadBackAndMultipartMaintenance" && toset(st.Action) == toset(["s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"]) &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-20261115/*"] && st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" } }
    ])
    error_message = "Read-back and multipart maintenance on the same prefix only."
  }
}

run "pipeline_reads_only_its_outputs_and_the_emr_logs_and_lists_only_those_prefixes" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3PipelineOutputsAndEmrLogsReadOnly" && toset(st.Action) == toset(["s3:GetObject", "s3:GetObjectVersion"]) &&
      toset(st.Resource) == toset(["arn:aws:s3:::scholarchain-course-111122223333-artifacts/pipeline/run-20261115/*", "arn:aws:s3:::scholarchain-course-111122223333-logs/emr/*"]) &&
      st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" } }
    ])
    error_message = "Read-only on artifacts pipeline/<run>/* (EMR outputs) and logs emr/* (the cluster log_uri)."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3ListArtifactsRunPrefixes" && st.Action == ["s3:ListBucket"] && st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts"] &&
      st.Condition.StringLike["s3:prefix"] == ["emr/run-20261115", "emr/run-20261115/*", "pipeline/run-20261115", "pipeline/run-20261115/*"] && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
      ]) && anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3ListEmrLogsPrefix" && st.Action == ["s3:ListBucket"] && st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-logs"] &&
      st.Condition.StringLike["s3:prefix"] == ["emr", "emr/*"] && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "ListBucket is limited per bucket to the same prefixes."
  }
  assert {
    condition = alltrue(flatten([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : [
        for r in st.Resource :
        !anytrue([for b in ["raw", "curated", "graph", "rag", "reports", "vectors"] : strcontains(r, "-111122223333-${b}")])
      ]
    ]))
    error_message = "The pipeline role never touches the raw, curated, graph, rag, reports or vector buckets."
  }
}

run "pipeline_kms_is_the_project_key_through_s3_only" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "ProjectKeyThroughS3Only" && toset(st.Action) == toset(["kms:GenerateDataKey", "kms:Decrypt"]) && st.Resource == ["arn:aws:kms:us-east-2:111122223333:key/*"] &&
      st.Condition == {
        StringEquals               = { "aws:RequestedRegion" = "us-east-2", "kms:ViaService" = "s3.us-east-2.amazonaws.com" }
        "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = "alias/scholarchain-course-data" }
      }
    ])
    error_message = "Data-key and decrypt use of the project key only through S3 in us-east-2 and only for the key aliased alias/scholarchain-<env>-data."
  }
}

run "pipeline_policy_has_no_wildcards_no_marketplace_a_region_lock_and_fits_the_limits" {
  command = plan

  assert {
    condition = alltrue(flatten([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement : [
        st.Effect == "Allow" && !contains(st.Resource, "*") && alltrue([for a in st.Action : !endswith(a, "*") && a != "*" && length(split(":", a)) == 2]) &&
        st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
      ]
    ]))
    error_message = "Every pipeline statement is an Allow with explicit resources, enumerated actions and aws:RequestedRegion = us-east-2 (no iam:PassRole here, so no global exception)."
  }
  assert {
    condition     = !strcontains(lower(aws_iam_role_policy.operator_pipeline[0].policy), "marketplace") && !strcontains(aws_iam_role_policy.operator_pipeline[0].policy, "\"*:*\"") && !strcontains(aws_iam_role_policy.operator_pipeline[0].policy, "\"Action\":\"*\"")
    error_message = "No aws-marketplace, no *:* and no bare * action."
  }
  assert {
    condition     = length(aws_iam_role_policy.operator_pipeline[0].policy) < 6144 && length(aws_iam_role_policy.operator_pipeline[0].policy) + length(aws_iam_role_policy.operator_pipeline_login[0].policy) < 10240
    error_message = "The pipeline document is under 6144 characters and, with the login policy, under the 10240-character aggregate inline limit."
  }
  assert {
    condition     = length(aws_iam_policy.permission_set) == 7 && alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144]) && length(aws_iam_role_policy_attachment.permission_set) == 7
    error_message = "The deployer's seven managed documents and attachments are unchanged (no growth, still under 6144)."
  }
}

run "pipeline_prefixes_follow_the_run_prefix" {
  command = plan
  variables {
    operator_run_prefix = "run-xyz-1"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator_pipeline[0].policy).Statement :
      st.Sid == "S3EmrArtifactsCreateOnlyWithIfNoneMatch" && st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-xyz-1/*"]
    ]) && !strcontains(aws_iam_role_policy.operator_pipeline[0].policy, "run-20261115")
    error_message = "The upload and output prefixes are built from operator_run_prefix."
  }
  assert {
    condition     = output.operator_scope.emr_upload_arn == "arn:aws:s3:::scholarchain-course-111122223333-artifacts/emr/run-xyz-1/*" && output.operator_scope.pipeline_output_arn == "arn:aws:s3:::scholarchain-course-111122223333-artifacts/pipeline/run-xyz-1/*" && output.operator_scope.emr_logs_arn == "arn:aws:s3:::scholarchain-course-111122223333-logs/emr/*" && output.operator_scope.pipeline_role_name == "scholarchain-course-operator-pipeline"
    error_message = "operator_scope shows the pipeline contract (upload, output, log ARNs and role name)."
  }
}
