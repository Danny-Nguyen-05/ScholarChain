# Replan W5a (14B, USD 25 cap): ACM actions for the main root's HTTPS certificate, the ECS Exec channels in the runtime boundary and the
# three operator roles. Hand-derived expectations; mock provider, no AWS call is possible. Run with `terraform test` in this root.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id              = "111122223333"
  operator_principal_arn  = "arn:aws:iam::111122223333:user/example-operator"
  owner                   = "example-owner"
  enabled_permission_sets = ["phase14-main"]
}

# ---- ACM ----------------------------------------------------------------------------------------------------------------

run "acm_actions_are_exactly_the_certificate_lifecycle_set_and_region_locked" {
  command = plan

  assert {
    condition = toset(flatten([
      for k, p in aws_iam_policy.permission_set : [for st in jsondecode(p.policy).Statement : [for a in st.Action : a if startswith(a, "acm:")]]
      ])) == toset([
      "acm:RequestCertificate", "acm:AddTagsToCertificate", "acm:DeleteCertificate", "acm:ListTagsForCertificate",
      "acm:RemoveTagsFromCertificate", "acm:DescribeCertificate",
    ])
    error_message = "The ACM actions across all documents are exactly the six certificate-lifecycle actions (no ListCertificates, Import, Export, Renew, Revoke, Resend)."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "acm:")]) || (st.Effect == "Allow" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2")
      ]
    ]))
    error_message = "Every statement with an ACM action is an Allow pinned to us-east-2."
  }
  assert {
    condition     = contains(flatten([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : st.Action]), "acm:RequestCertificate") && contains(flatten([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : st.Action]), "acm:DeleteCertificate")
    error_message = "The ACM statements live in the keys-obs document."
  }
}

run "acm_request_certificate_needs_dns_validation_and_the_project_request_tags" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement :
      st.Sid == "AcmRequestCertificateDnsValidationWithProjectTags" && st.Effect == "Allow" && st.Action == ["acm:RequestCertificate"] && st.Resource == ["*"] &&
      st.Condition.StringEquals["acm:ValidationMethod"] == "DNS" && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain" &&
      st.Condition.StringEquals["aws:RequestTag/environment"] == "course" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "RequestCertificate (no resource type) requires DNS validation, the project and environment request tags and the region."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement :
      st.Sid == "AcmTagOnCreateWithProjectTags" && st.Action == ["acm:AddTagsToCertificate"] && st.Resource == ["arn:aws:acm:us-east-2:111122223333:certificate/*"] &&
      st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain" && st.Condition.StringEquals["aws:RequestTag/environment"] == "course" &&
      length(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"]) == 12 && !contains(keys(st.Condition.StringEquals), "acm:ValidationMethod")
    ])
    error_message = "Tag-on-create is limited to certificate ARNs of this account and region, the request tags and the twelve declared tag keys."
  }
}

run "acm_delete_and_tag_maintenance_need_the_project_resource_tags" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement :
      st.Sid == "AcmManageProjectTaggedCertificates" && toset(st.Action) == toset(["acm:DeleteCertificate", "acm:ListTagsForCertificate", "acm:AddTagsToCertificate", "acm:RemoveTagsFromCertificate"]) &&
      st.Resource == ["arn:aws:acm:us-east-2:111122223333:certificate/*"] && st.Condition.StringEquals["aws:ResourceTag/project"] == "scholarchain" &&
      st.Condition.StringEquals["aws:ResourceTag/environment"] == "course" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "Delete, list tags, retag and untag apply only to certificates that already carry the project tags."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement :
      st.Sid != "AcmManageProjectTaggedCertificates" || !anytrue([for ck in keys(st.Condition.StringEquals) : startswith(ck, "aws:RequestTag/")])
    ])
    error_message = "The tag-scoped ACM statement keys off the resource tags only."
  }
  assert {
    condition     = alltrue([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : !contains(st.Action, "acm:DeleteCertificate") || st.Resource != ["*"]])
    error_message = "acm:DeleteCertificate is never granted on Resource *."
  }
}

# ---- documents stay small, nothing from Marketplace ---------------------------------------------------------------------------------

run "every_document_boundary_and_operator_policy_is_under_6144_characters" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition     = alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144]) && length(aws_iam_policy.main_boundary_runtime[0].policy) < 6144 && length(aws_iam_policy.main_boundary_emr[0].policy) < 6144
    error_message = "Every managed document and both boundaries stay under 6144 characters after the ACM and ECS Exec additions."
  }
  assert {
    condition     = alltrue([for k, p in aws_iam_role_policy.operator : length(p.policy) < 6144]) && length(aws_iam_role_policy.operator) == 4
    error_message = "The four operator inline policies each stay under 6144 characters."
  }
  assert {
    condition     = length(aws_iam_role_policy.operator["loader--data"].policy) + length(aws_iam_role_policy.operator["loader--tunnel"].policy) < 10240
    error_message = "The loader's inline policies together stay under the 10240-character inline-policy limit."
  }
}

run "no_aws_marketplace_permission_anywhere_and_no_star_star" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = !anytrue(concat(
      [for k, p in aws_iam_policy.permission_set : strcontains(lower(p.policy), "marketplace")],
      [for k, p in aws_iam_role_policy.operator : strcontains(lower(p.policy), "marketplace")],
      [for k, p in aws_iam_role_policy.operator_login : strcontains(lower(p.policy), "marketplace")],
      [strcontains(lower(aws_iam_policy.main_boundary_runtime[0].policy), "marketplace"), strcontains(lower(aws_iam_policy.main_boundary_emr[0].policy), "marketplace")],
      [for k, r in aws_iam_role.operator : strcontains(lower(r.assume_role_policy), "marketplace")],
      [strcontains(lower(aws_iam_role_policy.login.policy), "marketplace")]
    ))
    error_message = "No document, boundary, operator policy or trust policy mentions aws-marketplace."
  }
  assert {
    condition = !anytrue(concat(
      [for k, p in aws_iam_policy.permission_set : strcontains(p.policy, "\"*:*\"") || strcontains(p.policy, "\"Action\":\"*\"") || strcontains(p.policy, "\"Action\":[\"*\"")],
      [for k, p in aws_iam_role_policy.operator : strcontains(p.policy, "\"*:*\"") || strcontains(p.policy, "\"Action\":\"*\"") || strcontains(p.policy, "\"Action\":[\"*\"")]
    ))
    error_message = "No *:* or bare * action anywhere."
  }
}

# ---- runtime boundary -------------------------------------------------------------------------------------------------------------

run "runtime_boundary_has_the_four_ssmmessages_channels_and_no_neptune_write_or_load" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement :
      st.Effect == "Allow" && toset(st.Action) == toset(["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"]) && st.Resource == ["*"]
    ])
    error_message = "The runtime boundary allows exactly the four ssmmessages ECS Exec channel actions (they have no resource type)."
  }
  assert {
    condition = toset(flatten([
      for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement : [for a in st.Action : a if startswith(a, "neptune-db:")]
    ])) == toset(["neptune-db:ReadDataViaQuery", "neptune-db:GetQueryStatus", "neptune-db:CancelQuery", "neptune-db:GetEngineStatus"])
    error_message = "The runtime boundary keeps only the four Neptune read actions: no WriteDataViaQuery, DeleteDataViaQuery, StartLoaderJob, ResetDatabase or other loader action."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement :
      !anytrue([for a in st.Action : startswith(a, "ssm:") || startswith(a, "ecs:") || startswith(a, "iam:")])
    ])
    error_message = "The boundary gains no ssm:, ecs: or iam: action: the operator roles are not runtime roles."
  }
  assert {
    condition     = length(aws_iam_policy.main_boundary_runtime[0].policy) < 6144
    error_message = "The runtime boundary stays under 6144 characters."
  }
}

# ---- operator roles: toggle ---------------------------------------------------------------------------------------------------------

run "operator_roles_are_absent_by_default" {
  command = plan

  assert {
    condition     = var.operator_roles_enabled == false && length(aws_iam_role.operator) == 0 && length(aws_iam_role_policy.operator) == 0 && length(aws_iam_role_policy.operator_login) == 0
    error_message = "With the default (false) no operator role, no data inline policy and no login inline policy is planned; applying false after true removes them."
  }
  assert {
    condition     = output.operator_role_arns == null && output.operator_scope == null && output.operator_roles_caller_policy_json == null
    error_message = "The operator outputs are null while disabled."
  }
  assert {
    condition     = aws_iam_role_policy.login.name == "scholarchain-deployer-same-device-login"
    error_message = "The deployer's own same-device login policy is unchanged by the operator toggle."
  }
  assert {
    condition     = aws_iam_role.deployer.max_session_duration == 3600 && length(aws_iam_role_policy_attachment.permission_set) == 7
    error_message = "The deployer role and its seven attachments are unchanged by the operator toggle."
  }
}

run "operator_roles_exist_when_enabled_with_mfa_trust_and_four_hours" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition     = toset(keys(aws_iam_role.operator)) == toset(["loader", "reader", "cleanup"]) && aws_iam_role.operator["loader"].name == "scholarchain-course-operator-loader" && aws_iam_role.operator["reader"].name == "scholarchain-course-operator-reader" && aws_iam_role.operator["cleanup"].name == "scholarchain-course-operator-cleanup"
    error_message = "Exactly the loader, reader and cleanup roles with the contract names scholarchain-<env>-operator-<kind>."
  }
  assert {
    condition     = alltrue([for k, r in aws_iam_role.operator : r.max_session_duration == 14400])
    error_message = "Every operator role has a 4 hour (14400 s) maximum session."
  }
  assert {
    condition = alltrue([
      for k, r in aws_iam_role.operator :
      length(jsondecode(r.assume_role_policy).Statement) == 1 &&
      jsondecode(r.assume_role_policy).Statement[0].Effect == "Allow" &&
      jsondecode(r.assume_role_policy).Statement[0].Principal.AWS == "arn:aws:iam::111122223333:user/example-operator" &&
      jsondecode(r.assume_role_policy).Statement[0].Action == "sts:AssumeRole" &&
      jsondecode(r.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true" &&
      !strcontains(r.assume_role_policy, "*")
    ])
    error_message = "Trust is the same single operator principal as the deployer role, MFA required, no wildcard."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Principal.AWS == jsondecode(aws_iam_role.operator["loader"].assume_role_policy).Statement[0].Principal.AWS
    error_message = "The operator roles trust exactly the principal the deployer role trusts."
  }
  assert {
    condition     = alltrue([for k, r in aws_iam_role.operator : r.name != aws_iam_role.deployer.name]) && length(aws_iam_role_policy_attachment.permission_set) == 7
    error_message = "No name collision with the deployer; operator policies are inline and do not use the managed-policy quota."
  }
  assert {
    condition     = toset(keys(aws_iam_role_policy.operator)) == toset(["loader--data", "loader--tunnel", "reader--data", "cleanup--data"])
    error_message = "Four inline policies: loader data and tunnel, reader, cleanup."
  }
  assert {
    condition     = !anytrue([for k, r in aws_iam_role.operator : r.permissions_boundary != null && r.permissions_boundary != ""])
    error_message = "Operator roles are not runtime roles and carry no runtime boundary."
  }
  assert {
    condition     = anytrue([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement : st.Effect == "Deny" && st.Action == ["sts:AssumeRole"] && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-*"]])
    error_message = "The deployer's explicit deny of assuming scholarchain-<env>-* roles covers the operator roles."
  }
}

# ---- operator roles: sign-in exactly like the deployer (replan W5a-2) -------------------------------------------------------------
# Flow under test: IAM user console sign-in with MFA -> console switch role (the trust MFA condition is evaluated there) ->
# `aws login --profile scholarchain-<kind>` selects that role session. The role itself needs the two sign-in actions on the
# localhost client; no role chaining, so no role principal in the trust and no sts action in the permissions.

run "each_operator_role_carries_the_deployers_same_device_login_policy" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition     = toset(keys(aws_iam_role_policy.operator_login)) == toset(["loader", "reader", "cleanup"])
    error_message = "One login policy per operator role: loader, reader, cleanup."
  }
  assert {
    condition = (
      aws_iam_role_policy.operator_login["loader"].name == "scholarchain-course-operator-loader-same-device-login" &&
      aws_iam_role_policy.operator_login["reader"].name == "scholarchain-course-operator-reader-same-device-login" &&
      aws_iam_role_policy.operator_login["cleanup"].name == "scholarchain-course-operator-cleanup-same-device-login"
    )
    error_message = "Login policy names are <role name>-same-device-login."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_role_policy.operator_login :
      p.name == "${aws_iam_role.operator[k].name}-same-device-login"
    ])
    error_message = "Each login policy is named after, and keyed to, its own operator role (the role id itself is unknown until apply)."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_role_policy.operator_login :
      jsondecode(p.policy).Version == "2012-10-17" &&
      length(jsondecode(p.policy).Statement) == 1 &&
      jsondecode(p.policy).Statement[0].Sid == "OperatorSameDeviceLogin" &&
      jsondecode(p.policy).Statement[0].Effect == "Allow" &&
      toset(jsondecode(p.policy).Statement[0].Action) == toset(["signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"]) &&
      length(jsondecode(p.policy).Statement[0].Action) == 2 &&
      jsondecode(p.policy).Statement[0].Resource == ["arn:aws:signin:us-east-2:111122223333:oauth2/public-client/localhost"] &&
      jsondecode(p.policy).Statement[0].Condition == { StringEquals = { "signin:OAuthClientId" = "arn:aws:signin:::devtools/same-device" } }
    ])
    error_message = "Exactly the two sign-in actions on the account/region localhost client, pinned to the same-device OAuth client id (hand-derived)."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_role_policy.operator_login :
      jsondecode(p.policy).Statement[0].Action == jsondecode(aws_iam_role_policy.login.policy).Statement[0].Action &&
      jsondecode(p.policy).Statement[0].Resource == jsondecode(aws_iam_role_policy.login.policy).Statement[0].Resource &&
      jsondecode(p.policy).Statement[0].Condition == jsondecode(aws_iam_role_policy.login.policy).Statement[0].Condition
    ])
    error_message = "The operator login policy is the deployer's login policy apart from the Sid."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_role_policy.operator_login :
      !strcontains(p.policy, "*") && !strcontains(p.policy, "remote") && !strcontains(p.policy, "cross-device")
    ])
    error_message = "No wildcard, no cross-device (remote) client in the operator login policy."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_role_policy.operator_login :
      length(p.policy) + sum([for kk, d in aws_iam_role_policy.operator : length(d.policy) if startswith(kk, "${k}--")]) < 10240
    ])
    error_message = "Each role's inline policies (data, tunnel and login) together stay under the 10240-character aggregate inline-policy limit."
  }
}

run "operator_trust_is_the_deployers_trust_shape_that_a_console_role_switch_satisfies" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = alltrue([
      for k, r in aws_iam_role.operator :
      jsondecode(r.assume_role_policy).Statement[0].Principal == jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Principal &&
      jsondecode(r.assume_role_policy).Statement[0].Action == jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Action &&
      jsondecode(r.assume_role_policy).Statement[0].Condition == jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Condition
    ])
    error_message = "Operator trust equals the deployer trust apart from the Sid: same principal, sts:AssumeRole, same condition."
  }
  assert {
    condition = alltrue([
      for k, r in aws_iam_role.operator :
      jsondecode(r.assume_role_policy).Statement[0].Condition == { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    ])
    error_message = "The only trust condition is Bool aws:MultiFactorAuthPresent = true (the console switch carries the MFA sign-in; no MFA-age, BoolIfExists or other condition that the flow could not satisfy)."
  }
  assert {
    condition = alltrue([
      for k, r in aws_iam_role.operator :
      startswith(jsondecode(r.assume_role_policy).Statement[0].Principal.AWS, "arn:aws:iam::111122223333:user/") &&
      !strcontains(r.assume_role_policy, ":role/") && !strcontains(r.assume_role_policy, "assumed-role") && !strcontains(r.assume_role_policy, "Service")
    ])
    error_message = "The trusted principal is the IAM user (a console switch from the user is not role chaining); no role, assumed-role or service principal."
  }
  assert {
    condition     = alltrue([for k, r in aws_iam_role.operator : r.max_session_duration == 14400 && r.max_session_duration >= 3600 && r.max_session_duration <= 43200])
    error_message = "14400 s is inside the 1 h to 12 h range a console role switch and aws login support."
  }
  assert {
    condition = !anytrue(flatten([
      for k, p in aws_iam_role_policy.operator : [
        for st in jsondecode(p.policy).Statement :
        anytrue([for a in st.Action : startswith(a, "sts:") || startswith(a, "signin:")]) || strcontains(jsonencode(try(st.Condition, {})), "MultiFactorAuth")
      ]
    ]))
    error_message = "No operator data policy assumes another role, signs in or depends on an MFA flag in the session (whether aws login credentials carry aws:MultiFactorAuthPresent is unverified; MFA is enforced in the trust)."
  }
}

run "operator_caller_policy_output_names_exactly_the_four_roles_with_mfa" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = (
      length(jsondecode(output.operator_roles_caller_policy_json).Statement) == 1 &&
      jsondecode(output.operator_roles_caller_policy_json).Statement[0].Effect == "Allow" &&
      jsondecode(output.operator_roles_caller_policy_json).Statement[0].Action == ["sts:AssumeRole"] &&
      jsondecode(output.operator_roles_caller_policy_json).Statement[0].Resource == [
        "arn:aws:iam::111122223333:role/scholarchain-course-operator-cleanup",
        "arn:aws:iam::111122223333:role/scholarchain-course-operator-loader",
        "arn:aws:iam::111122223333:role/scholarchain-course-operator-pipeline",
        "arn:aws:iam::111122223333:role/scholarchain-course-operator-reader",
      ] &&
      jsondecode(output.operator_roles_caller_policy_json).Statement[0].Condition == { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
    )
    error_message = "The optional caller policy allows only sts:AssumeRole on the four operator role ARNs (loader, reader, cleanup and, G-DEPLOYER, pipeline), MFA required, no wildcard and not the deployer or any main role."
  }
}

# ---- operator roles: loader ---------------------------------------------------------------------------------------------------

run "loader_actions_are_exactly_the_approved_set" {
  command = plan
  variables {
    operator_roles_enabled  = true
    operator_run_prefix     = "run-20261115"
    main_embedding_provider = "bedrock" # repair round 3: the Titan grant exists only with Bedrock embeddings (providers.tftest.hcl covers the default)
  }

  assert {
    condition = toset(flatten([
      for k in ["loader--data", "loader--tunnel"] : [for st in jsondecode(aws_iam_role_policy.operator[k].policy).Statement : st.Action]
      ])) == toset([
      "s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts", "s3:ListBucket",
      "kms:GenerateDataKey", "kms:Decrypt",
      "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem", "dynamodb:ConditionCheckItem",
      "s3vectors:GetIndex", "s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:QueryVectors",
      "bedrock:InvokeModel",
      "neptune-db:StartLoaderJob", "neptune-db:GetLoaderJobStatus", "neptune-db:ListLoaderJobs", "neptune-db:CancelLoaderJob", "neptune-db:GetEngineStatus",
      "ecs:RunTask", "ecs:StopTask", "ecs:DescribeTasks", "ecs:ExecuteCommand",
      "ssm:StartSession", "ssm:TerminateSession", "ssmmessages:OpenDataChannel",
      "iam:PassRole",
    ])
    error_message = "The loader's actions are exactly the approved list plus the documented multipart/version/attribute S3 reads and ssmmessages:OpenDataChannel."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3ObjectsUnderRunPrefixes" && toset(st.Resource) == toset([
        "arn:aws:s3:::scholarchain-course-111122223333-graph/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-graph/source-qualifications/*",
        "arn:aws:s3:::scholarchain-course-111122223333-curated/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/embedding-text/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/vector-rejects/*",
      ])
    ])
    error_message = "Loader object writes are limited to the run folder (graph, curated) and the key prefixes the storage tools write (graph source-qualifications, rag embedding-text and vector-rejects)."
  }
  assert {
    condition = toset([for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement : st.Sid if st.Sid == "S3ListGraphPrefixes" || st.Sid == "S3ListCuratedPrefixes" || st.Sid == "S3ListRagPrefixes"]) == toset(["S3ListGraphPrefixes", "S3ListCuratedPrefixes", "S3ListRagPrefixes"]) && anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3ListCuratedPrefixes" && st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-curated"] && st.Condition.StringLike["s3:prefix"] == ["run-20261115", "run-20261115/*"]
      ]) && anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3ListRagPrefixes" && st.Condition.StringLike["s3:prefix"] == ["embedding-text", "embedding-text/*", "vector-rejects", "vector-rejects/*", "runtime-artifacts/run-20261115", "runtime-artifacts/run-20261115/*"]
    ])
    error_message = "ListBucket is limited per bucket to the same prefixes."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "DynamoDbItemsOfTheSixTables" && length(st.Resource) == 12 && alltrue([for t in ["RunLedger", "EntityLinkCache", "QuerySession", "EvidenceBundle", "ArtifactRegistry", "ResearcherMetricCache"] : contains(st.Resource, "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-${t}") && contains(st.Resource, "arn:aws:dynamodb:us-east-2:111122223333:table/scholarchain-course-${t}/index/*")])
    ])
    error_message = "DynamoDB access names the six tables and their indexes, no table-name wildcard."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "S3VectorsIndexData" && st.Resource == ["arn:aws:s3vectors:us-east-2:111122223333:bucket/scholarchain-course-111122223333-vectors/index/*"]
    ])
    error_message = "S3 Vectors data access is limited to the indexes of the project vector bucket."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Action == ["bedrock:InvokeModel"] && st.Resource == ["arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v2:0"]
    ]) && length([for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement : st if anytrue([for a in st.Action : startswith(a, "bedrock:")])]) == 1
    error_message = "Bedrock InvokeModel is limited to Titan Text Embeddings V2; no streaming, no other model."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "ProjectKeyThroughServices" && toset(st.Action) == toset(["kms:GenerateDataKey", "kms:Decrypt"]) && st.Resource == ["arn:aws:kms:us-east-2:111122223333:key/*"] &&
      st.Condition.StringEquals["kms:ViaService"] == ["s3.us-east-2.amazonaws.com", "dynamodb.us-east-2.amazonaws.com", "s3vectors.us-east-2.amazonaws.com"] &&
      st.Condition["ForAnyValue:StringEquals"]["kms:ResourceAliases"] == "alias/scholarchain-course-data"
    ])
    error_message = "The project key is usable only through S3, DynamoDB and S3 Vectors, and only the key aliased alias/scholarchain-course-data."
  }
}

run "loader_tunnel_is_a_one_off_task_with_ecs_exec_port_forwarding_only" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--tunnel"].policy).Statement :
      st.Action == ["ecs:RunTask"] && st.Resource == ["arn:aws:ecs:us-east-2:111122223333:task-definition/scholarchain-course-neptune-tunnel:*"] && st.Condition.ArnEquals["ecs:cluster"] == "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "RunTask is limited to the tunnel task-definition family in the project cluster."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--tunnel"].policy).Statement :
      toset(st.Action) == toset(["ecs:StopTask", "ecs:DescribeTasks", "ecs:ExecuteCommand"]) && toset(st.Resource) == toset(["arn:aws:ecs:us-east-2:111122223333:task/scholarchain-course/*", "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course"]) && st.Condition.ArnEquals["ecs:cluster"] == "arn:aws:ecs:us-east-2:111122223333:cluster/scholarchain-course"
    ])
    error_message = "StopTask, DescribeTasks and ExecuteCommand cover the project cluster's tasks only."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--tunnel"].policy).Statement :
      st.Action == ["ssm:StartSession"] && toset(st.Resource) == toset(["arn:aws:ecs:us-east-2:111122223333:task/scholarchain-course/*", "arn:aws:ssm:us-east-2::document/AWS-StartPortForwardingSessionToRemoteHost"])
    ])
    error_message = "StartSession is limited to the ECS task target and the remote-host port-forwarding document."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--tunnel"].policy).Statement :
      toset(st.Action) == toset(["ssm:TerminateSession", "ssmmessages:OpenDataChannel"]) && st.Resource == ["arn:aws:ssm:*:*:session/$${aws:userid}-*"]
    ])
    error_message = "TerminateSession (and the data channel) apply to the caller's own sessions only."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--tunnel"].policy).Statement :
      st.Action == ["iam:PassRole"] && toset(st.Resource) == toset(["arn:aws:iam::111122223333:role/scholarchain-course-neptune-tunnel-task", "arn:aws:iam::111122223333:role/scholarchain-course-graph-service-execution"]) && st.Condition.StringEquals["iam:PassedToService"] == ["ecs-tasks.amazonaws.com"] && !can(st.Condition.StringEquals["aws:RequestedRegion"])
    ])
    error_message = "PassRole: only the tunnel task role and the graph-service execution role, only to ECS tasks (global service: no region condition)."
  }
  assert {
    condition     = alltrue([for k in ["loader--data", "loader--tunnel", "reader--data", "cleanup--data"] : alltrue([for st in jsondecode(aws_iam_role_policy.operator[k].policy).Statement : !anytrue([for a in st.Action : startswith(a, "iam:") && a != "iam:PassRole"])])])
    error_message = "No IAM action other than the two-role PassRole in any operator policy."
  }
}

run "loader_neptune_scope_falls_back_to_account_clusters_and_tightens_with_the_resource_id" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement :
      st.Sid == "NeptuneBulkLoader" && st.Resource == ["arn:aws:neptune-db:us-east-2:111122223333:cluster-*/*"]
    ])
    error_message = "Without a cluster resource id the Neptune statements cover cluster-*/* of this account and region only."
  }
  assert {
    condition     = output.operator_scope.neptune_scope_is_fallback == true
    error_message = "The output flags the fallback scope."
  }
}

run "neptune_scope_is_the_exact_cluster_when_the_resource_id_is_set" {
  command = plan
  variables {
    operator_roles_enabled               = true
    operator_run_prefix                  = "run-20261115"
    operator_neptune_cluster_resource_id = "cluster-ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  }

  assert {
    condition = alltrue([
      for k in ["loader--data", "reader--data", "cleanup--data"] : anytrue([
        for st in jsondecode(aws_iam_role_policy.operator[k].policy).Statement :
        anytrue([for a in st.Action : startswith(a, "neptune-db:")]) && st.Resource == ["arn:aws:neptune-db:us-east-2:111122223333:cluster-ABCDEFGHIJKLMNOPQRSTUVWXYZ/*"]
      ])
    ])
    error_message = "With the resource id set, every neptune-db statement names exactly that cluster."
  }
  assert {
    condition     = output.operator_scope.neptune_scope_is_fallback == false
    error_message = "The output no longer flags the fallback."
  }
}

# ---- operator roles: reader and cleanup ---------------------------------------------------------------------------------------

run "reader_actions_are_exactly_the_approved_set_and_read_only" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = toset(flatten([for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement : st.Action])) == toset([
      "neptune-db:ReadDataViaQuery", "neptune-db:GetQueryStatus", "neptune-db:GetEngineStatus",
      "dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem",
      "s3vectors:QueryVectors", "s3vectors:GetVectors",
      "s3:GetObject", "s3:ListBucket",
      "kms:Decrypt",
    ])
    error_message = "The reader's actions are exactly the approved read list plus kms:Decrypt (it must decrypt what it reads)."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement :
      st.Sid == "S3ReadUnderRunPrefixes" && st.Action == ["s3:GetObject"] && toset(st.Resource) == toset([
        "arn:aws:s3:::scholarchain-course-111122223333-graph/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-graph/source-qualifications/*",
        "arn:aws:s3:::scholarchain-course-111122223333-curated/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/embedding-text/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/vector-rejects/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*",
      ])
    ])
    error_message = "Reader object access is the same prefixes as the loader's, read only."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement :
      st.Sid == "DynamoDbReadOfTheSixTables" && length(st.Resource) == 12
      ]) && anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement :
      st.Sid == "S3VectorsRead" && st.Resource == ["arn:aws:s3vectors:us-east-2:111122223333:bucket/scholarchain-course-111122223333-vectors/index/*"]
    ])
    error_message = "Reader DynamoDB access names the six tables with indexes; vectors are limited to the project indexes."
  }
  assert {
    condition = !anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["reader--data"].policy).Statement :
      anytrue([for a in st.Action : contains(["s3:PutObject", "s3:DeleteObject", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem", "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery", "neptune-db:StartLoaderJob", "s3vectors:PutVectors", "s3vectors:DeleteVectors", "bedrock:InvokeModel"], a)])
    ])
    error_message = "The reader holds no write, delete, load or model-invoke action."
  }
}

run "cleanup_actions_are_exactly_the_approved_set_and_delete_only" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = toset(flatten([for st in jsondecode(aws_iam_role_policy.operator["cleanup--data"].policy).Statement : st.Action])) == toset([
      "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery", "neptune-db:ReadDataViaQuery",
      "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:GetItem",
      "s3vectors:DeleteVectors", "s3vectors:ListVectors",
      "s3:DeleteObject", "s3:DeleteObjectVersion", "s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket", "s3:ListBucketVersions",
      "kms:Decrypt",
    ])
    error_message = "The cleanup actions are exactly the approved list plus the version-aware S3 actions (the buckets are versioned) and kms:Decrypt."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["cleanup--data"].policy).Statement :
      st.Sid == "S3DeleteUnderRunPrefixes" && toset(st.Resource) == toset([
        "arn:aws:s3:::scholarchain-course-111122223333-graph/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-graph/source-qualifications/*",
        "arn:aws:s3:::scholarchain-course-111122223333-curated/run-20261115/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/embedding-text/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/vector-rejects/*",
        "arn:aws:s3:::scholarchain-course-111122223333-rag/runtime-artifacts/run-20261115/*",
      ])
    ])
    error_message = "Cleanup deletes only under the run prefixes and the tool prefixes."
  }
  assert {
    condition = !anytrue([
      for st in jsondecode(aws_iam_role_policy.operator["cleanup--data"].policy).Statement :
      anytrue([for a in st.Action : contains(["s3:PutObject", "dynamodb:PutItem", "dynamodb:UpdateItem", "neptune-db:StartLoaderJob", "s3vectors:PutVectors", "bedrock:InvokeModel", "ecs:RunTask", "ssm:StartSession"], a)])
    ])
    error_message = "The cleanup role cannot load, write items or vectors, invoke models or open the tunnel."
  }
}

# ---- cross-role invariants ---------------------------------------------------------------------------------------------------------------

run "no_operator_statement_is_unscoped_or_wildcard_service" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
  }

  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Allow" && !contains(st.Resource, "*") && alltrue([for a in st.Action : !endswith(a, "*") && a != "*" && length(split(":", a)) == 2])
      ]
    ]))
    error_message = "Every operator statement is an Allow with explicit resources and enumerated actions (no Resource *, no wildcard action or service)."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [
        for st in jsondecode(p.policy).Statement :
        st.Action == ["iam:PassRole"] || st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
      ]
    ]))
    error_message = "Every operator Allow statement except the global iam:PassRole is pinned to us-east-2."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "ec2:") || startswith(a, "rds:") || startswith(a, "elasticmapreduce:") || startswith(a, "cloudformation:") || startswith(a, "lambda:") || startswith(a, "secretsmanager:") || startswith(a, "sts:") || startswith(a, "organizations:") || startswith(a, "budgets:") || startswith(a, "ce:") || startswith(a, "aws-marketplace:")])
      ]
    ]))
    error_message = "No infrastructure, secrets, STS, billing or Marketplace action in any operator policy."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [
        for st in jsondecode(p.policy).Statement :
        !anytrue([for r in st.Resource : strcontains(r, "-111122223333-raw") || strcontains(r, "-111122223333-artifacts") || strcontains(r, "-111122223333-logs") || strcontains(r, "-111122223333-reports")])
      ]
    ]))
    error_message = "The loader, reader and cleanup roles never touch the raw, artifacts, logs or reports buckets (bucket names are matched with the account id, so the key prefix runtime-artifacts/ in the rag bucket is not a false hit). Only the pipeline role reads the artifacts and logs buckets (its own tests)."
  }
}

run "operator_names_and_arns_follow_main_environment" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115"
    main_environment       = "abcdefghij"
  }

  assert {
    condition     = aws_iam_role.operator["loader"].name == "scholarchain-abcdefghij-operator-loader" && aws_iam_role.operator["cleanup"].name == "scholarchain-abcdefghij-operator-cleanup"
    error_message = "Role names follow main_environment."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.operator["loader--data"].policy, "scholarchain-course") && !strcontains(aws_iam_role_policy.operator["loader--tunnel"].policy, "scholarchain-course") && strcontains(aws_iam_role_policy.operator["loader--tunnel"].policy, "scholarchain-abcdefghij-neptune-tunnel")
    error_message = "No hard-coded environment value in the operator policies."
  }
  assert {
    condition     = alltrue([for k, p in aws_iam_role_policy.operator : length(p.policy) < 6144])
    error_message = "A 10-character environment name does not push an operator policy over the limit."
  }
}

# ---- variable validation ---------------------------------------------------------------------------------------------------------------

run "enabling_without_a_run_prefix_is_rejected" {
  command = plan
  variables {
    operator_roles_enabled = true
  }
  expect_failures = [var.operator_run_prefix]
}

run "run_prefix_must_start_with_run_dash_and_be_a_literal_folder" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "pipeline"
  }
  expect_failures = [var.operator_run_prefix]
}

run "run_prefix_with_a_slash_or_uppercase_is_rejected" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-20261115/../raw"
  }
  expect_failures = [var.operator_run_prefix]
}

run "run_prefix_with_a_wildcard_is_rejected" {
  command = plan
  variables {
    operator_roles_enabled = true
    operator_run_prefix    = "run-*"
  }
  expect_failures = [var.operator_run_prefix]
}

run "a_malformed_neptune_cluster_resource_id_is_rejected" {
  command = plan
  variables {
    operator_roles_enabled               = true
    operator_run_prefix                  = "run-20261115"
    operator_neptune_cluster_resource_id = "*"
  }
  expect_failures = [var.operator_neptune_cluster_resource_id]
}

run "an_embedding_text_prefix_with_a_wildcard_is_rejected" {
  command = plan
  variables {
    operator_roles_enabled         = true
    operator_run_prefix            = "run-20261115"
    operator_embedding_text_prefix = "embedding-*"
  }
  expect_failures = [var.operator_embedding_text_prefix]
}

# ---- W5a-3: object deletes for force_destroy at cleanup ---------------------------------------------------------------------
# AWS provider 6.44.0 emptyBucket: ListObjectVersions, then DeleteObjects (versions and delete markers; DeleteObject for odd keys).
# The vector bucket's force_destroy lists and deletes indexes only. Hand-derived expectations.

run "force_destroy_object_deletes_are_exactly_two_actions_on_the_project_bucket_objects" {
  command = plan

  assert {
    condition = length(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement : st if st.Effect == "Allow" && contains(st.Action, "s3:DeleteObject")
      ]
    ])) == 1
    error_message = "Exactly one Allow statement in the documents grants s3:DeleteObject."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--data"].policy).Statement :
      st.Sid == "S3ObjectsDeleteForForceDestroy" &&
      st.Effect == "Allow" &&
      toset(st.Action) == toset(["s3:DeleteObject", "s3:DeleteObjectVersion"]) && length(st.Action) == 2 &&
      st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-*/*"] &&
      st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" } }
    ])
    error_message = "The delete statement lives in the data document: exactly s3:DeleteObject and s3:DeleteObjectVersion on arn:aws:s3:::scholarchain-<env>-<account>-*/* in us-east-2."
  }
  assert {
    condition = !anytrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Allow" && anytrue([for a in st.Action : contains(["s3:DeleteObjectVersion", "s3:BypassGovernanceRetention", "s3:PutBucketObjectLockConfiguration", "s3:PutObjectRetention", "s3:PutObjectLegalHold", "s3:DeleteObjectTagging"], a) || a == "s3:*"]) &&
        st.Sid != "S3ObjectsDeleteForForceDestroy"
      ]
    ]))
    error_message = "No other statement deletes object versions, bypasses retention or touches Object Lock."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        !(st.Effect == "Allow" && contains(st.Action, "s3:AbortMultipartUpload")) || st.Resource == ["arn:aws:s3:::scholarchain-course-111122223333-artifacts/*"]
      ]
    ]))
    error_message = "s3:AbortMultipartUpload stays limited to the artifacts bucket: the provider's emptyBucket does not abort multipart uploads, so none was added for the other buckets."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        !(st.Effect == "Allow" && anytrue([for a in st.Action : startswith(a, "s3:") && endswith(a, "Object")])) ||
        alltrue([for r in st.Resource : startswith(r, "arn:aws:s3:::scholarchain-course-111122223333-") && endswith(r, "/*")])
      ]
    ]))
    error_message = "Every s3 object-level Allow is on an object ARN of a bucket named scholarchain-<env>-<account>-...: no other bucket, no Resource *."
  }
  assert {
    condition     = length(aws_iam_policy.permission_set["phase14-main--data"].policy) < 6144 && alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144])
    error_message = "The data document and every other managed document stay under 6144 characters after the delete statement."
  }
}

run "force_destroy_object_deletes_follow_main_environment" {
  command = plan
  variables {
    main_environment = "abcdefghij"
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--data"].policy).Statement :
      st.Sid == "S3ObjectsDeleteForForceDestroy" && st.Resource == ["arn:aws:s3:::scholarchain-abcdefghij-111122223333-*/*"]
    ])
    error_message = "The delete resource follows main_environment and the account id (no hard-coded course)."
  }
}

run "vector_bucket_force_destroy_needs_no_vector_level_action" {
  command = plan

  assert {
    condition = toset(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement : [for a in st.Action : a if startswith(a, "s3vectors:")]
      ]
      ])) == toset([
      "s3vectors:CreateVectorBucket", "s3vectors:GetVectorBucket", "s3vectors:DeleteVectorBucket",
      "s3vectors:PutVectorBucketPolicy", "s3vectors:GetVectorBucketPolicy", "s3vectors:DeleteVectorBucketPolicy",
      "s3vectors:CreateIndex", "s3vectors:GetIndex", "s3vectors:DeleteIndex", "s3vectors:ListIndexes",
      "s3vectors:TagResource", "s3vectors:UntagResource", "s3vectors:ListTagsForResource",
    ])
    error_message = "The deployer's s3vectors actions are exactly the thirteen bucket and index actions; ListIndexes and DeleteIndex (what the provider's force_destroy calls) are among them, and there is no ListVectors, DeleteVectors, PutVectors, GetVectors or QueryVectors."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "s3vectors:")]) || alltrue([for r in st.Resource : startswith(r, "arn:aws:s3vectors:us-east-2:111122223333:bucket/scholarchain-course-111122223333-vectors")])
      ]
    ]))
    error_message = "Every s3vectors statement is limited to the project vector bucket and its indexes."
  }
}
