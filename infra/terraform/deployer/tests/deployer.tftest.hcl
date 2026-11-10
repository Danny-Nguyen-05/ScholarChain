# Mock-only tests: no AWS call is possible. Run with `terraform test` in this root.
mock_provider "aws" {
  override_during = plan
}

# The default permission set is now phase14-main (decision 14-6). The spike-emr tests below keep planning the spike
# definition, which stays in code, so they select it explicitly; the phase14-main runs select their own set per run.
variables {
  account_id              = "111122223333"
  operator_principal_arn  = "arn:aws:iam::111122223333:user/example-operator"
  owner                   = "example-owner"
  enabled_permission_sets = ["spike-emr"]
}

run "trust_requires_mfa_and_exact_principal" {
  command = plan

  assert {
    condition     = jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Principal.AWS == "arn:aws:iam::111122223333:user/example-operator"
    error_message = "Trust must name exactly the supplied operator ARN."
  }
  assert {
    condition     = length(jsondecode(aws_iam_role.deployer.assume_role_policy).Statement) == 1 && jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true"
    error_message = "Trust must have one statement requiring aws:MultiFactorAuthPresent true."
  }
  assert {
    condition     = !strcontains(aws_iam_role.deployer.assume_role_policy, "*")
    error_message = "Trust policy must contain no wildcard."
  }
  assert {
    condition     = aws_iam_role.deployer.max_session_duration == 3600 && aws_iam_role.deployer.name == "scholarchain-deployer"
    error_message = "Default role name and a 3600-second session are required."
  }
}

run "four_spike_policies_each_under_the_managed_policy_limit" {
  command = plan

  assert {
    condition     = length(aws_iam_policy.permission_set) == 4
    error_message = "spike-emr is split into four managed policies."
  }
  assert {
    condition     = alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144])
    error_message = "Every managed policy must stay below the 6144-character limit."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary[0].policy) < 6144
    error_message = "The boundary policy must stay below the 6144-character limit."
  }
  assert {
    condition     = length(aws_iam_role_policy_attachment.permission_set) == 4
    error_message = "All four policies are attached."
  }
}

run "no_wildcard_actions_anywhere" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([for st in jsondecode(p.policy).Statement : alltrue([for a in st.Action : a != "*" && !endswith(a, ":*") && !endswith(a, "*")])])
    ])
    error_message = "Actions must be enumerated; no '*', 'svc:*' or prefix wildcard."
  }
  assert {
    condition     = alltrue([for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement : alltrue([for a in st.Action : !endswith(a, "*")])])
    error_message = "The boundary must enumerate actions too."
  }
}

run "regional_statements_carry_the_region_condition" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        try(st.Condition.StringEquals["aws:RequestedRegion"], "") == "us-east-2" || startswith(st.Action[0], "iam:") || startswith(st.Action[0], "sts:")
      ])
    ])
    error_message = "Every non-IAM, non-STS statement must pin aws:RequestedRegion to us-east-2."
  }
}

run "iam_statements_only_touch_the_spike_prefix" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !startswith(st.Action[0], "iam:") || alltrue([
          for r in st.Resource :
          strcontains(r, "scholarchain-spike-emr-") || strcontains(r, ":role/aws-service-role/")
        ])
      ])
    ])
    error_message = "Every IAM statement must be limited to scholarchain-spike-emr-* (or the two named service-linked roles)."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "iam:CreateServiceLinkedRole") || alltrue([for r in st.Resource : strcontains(r, "AWSServiceRoleForEMRCleanup") || strcontains(r, "AWSServiceRoleForAmazonElasticFileSystem")])
      ])
    ])
    error_message = "Service-linked-role creation is limited to two named roles."
  }
}

run "passrole_boundary_and_attach_conditions" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      contains(st.Action, "iam:PassRole") && toset(st.Condition.StringEquals["iam:PassedToService"]) == toset(["elasticmapreduce.amazonaws.com", "ec2.amazonaws.com"])
    ])
    error_message = "PassRole must be limited to elasticmapreduce and ec2 via iam:PassedToService."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      contains(st.Action, "iam:CreateRole") && st.Condition.StringEquals["iam:PermissionsBoundary"] == "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary" && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "CreateRole requires the spike boundary and the stack request tag."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      contains(st.Action, "iam:AttachRolePolicy") && st.Condition.StringEquals["iam:PermissionsBoundary"] == "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary" && st.Condition.StringEquals["iam:PolicyARN"] == "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2" && !can(st.Condition.ArnLike)
    ])
    error_message = "AttachRolePolicy: the iam:PolicyARN allowlist must be EXACTLY the EMR v2 service policy (exact equality, no list, no pattern)."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" || (!contains(st.Action, "iam:PutRolePermissionsBoundary") && !contains(st.Action, "iam:DeleteRolePermissionsBoundary") && !contains(st.Action, "iam:UpdateAssumeRolePolicy"))
    ])
    error_message = "The boundary and trust of spike roles must not be editable."
  }
}

run "nothing_for_billing_or_budgets" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      !strcontains(lower(p.policy), "budgets") && !strcontains(p.policy, "scholarchain-billing-deployer") && !strcontains(p.policy, "\"organizations:") && !strcontains(p.policy, "\"ce:")
    ])
    error_message = "No budgets, billing deployer, organizations or cost-explorer access."
  }
  assert {
    condition     = !strcontains(aws_iam_policy.spike_boundary[0].policy, "budgets") && !strcontains(aws_iam_policy.spike_boundary[0].policy, "scholarchain-billing-deployer")
    error_message = "The boundary must not mention budgets or the billing deployer."
  }
}

run "run_job_flow_requires_stack_and_emr_managed_tags" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--emr"].policy).Statement :
      contains(st.Action, "elasticmapreduce:RunJobFlow") && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr" && st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"] == "true"
    ])
    error_message = "RunJobFlow must require both request tags."
  }
}

run "boundary_policy_name_and_output" {
  command = plan

  assert {
    condition     = aws_iam_policy.spike_boundary[0].name == "scholarchain-spike-emr-boundary" && output.spike_permissions_boundary_arn == "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary"
    error_message = "The boundary name and ARN output must match what the IAM statements require."
  }
  assert {
    condition     = toset(output.available_permission_sets) == toset(["spike-emr", "phase14-main"]) && output.role_name == "scholarchain-deployer"
    error_message = "The registry holds exactly spike-emr (kept in code, not enabled by default) and phase14-main."
  }
}

run "unknown_permission_set_is_rejected" {
  command = plan
  variables {
    enabled_permission_sets = ["spike-emr", "phase14-not-implemented"]
  }
  expect_failures = [aws_iam_role.deployer]
}

run "empty_permission_set_list_is_rejected" {
  command = plan
  variables {
    enabled_permission_sets = []
  }
  expect_failures = [var.enabled_permission_sets]
}

run "wildcard_operator_is_rejected" {
  command = plan
  variables {
    operator_principal_arn = "arn:aws:iam::111122223333:user/*"
  }
  expect_failures = [var.operator_principal_arn]
}

run "account_root_operator_is_rejected" {
  command = plan
  variables {
    operator_principal_arn = "arn:aws:iam::111122223333:root"
  }
  expect_failures = [var.operator_principal_arn]
}

run "foreign_account_operator_is_rejected" {
  command = plan
  variables {
    operator_principal_arn = "arn:aws:iam::999999999999:user/other"
  }
  expect_failures = [var.operator_principal_arn]
}

run "region_other_than_ohio_is_rejected" {
  command = plan
  variables {
    region = "us-west-2"
  }
  expect_failures = [var.region]
}

run "billing_deployer_name_is_rejected" {
  command = plan
  variables {
    role_name = "scholarchain-billing-deployer"
  }
  expect_failures = [var.role_name]
}

run "bad_account_id_is_rejected" {
  command = plan
  variables {
    account_id = "1234"
  }
  expect_failures = [var.account_id]
}

run "resource_star_only_for_actions_without_a_resource_type_or_ec2_describe" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Resource, "*") || (length(st.Action) == 1 && contains([
          "tag:GetResources", "elasticmapreduce:ListClusters", "elasticmapreduce:ListSecurityConfigurations",
          "elasticmapreduce:DescribeSecurityConfiguration", "elasticmapreduce:CreateSecurityConfiguration",
          "elasticmapreduce:DeleteSecurityConfiguration", "elasticmapreduce:RunJobFlow", "kms:CreateKey", "kms:ListAliases",
        ], st.Action[0])) || alltrue([for a in st.Action : startswith(a, "ec2:Describe")])
      ])
    ])
    error_message = "Resource * is allowed only for the nine single-action statements without a resource type, and for ec2:Describe*."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !contains(st.Resource, "*") || alltrue([for a in st.Action : startswith(a, "ec2:Describe")])
    ])
    error_message = "The boundary may use Resource * only for ec2:Describe*."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set : !strcontains(p.policy, "sts:GetCallerIdentity")
    ])
    error_message = "sts:GetCallerIdentity needs no permission and is not granted."
  }
}

# ---- B1: boundary immutability and no policy-version / customer-policy rights

run "boundary_cannot_be_rewritten_or_assumed_around" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" && toset(st.Action) == toset(["iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion"]) && st.Resource == ["arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary"]
    ])
    error_message = "An explicit Deny on policy-version changes and deletion of the boundary is required."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" && st.Action == ["sts:AssumeRole"] && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-spike-emr-*"]
    ])
    error_message = "An explicit Deny of sts:AssumeRole on spike roles is required."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" && toset(st.Action) == toset(["iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy"])
    ])
    error_message = "Deny on changing a spike role's boundary or trust."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Deny" || !anytrue([for a in st.Action : contains(["iam:CreatePolicy", "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion", "iam:TagPolicy"], a)])
      ])
    ])
    error_message = "No Allow grants customer-managed policy creation, versioning or deletion."
  }
  assert {
    condition     = !strcontains(aws_iam_policy.permission_set["spike-emr--iam"].policy, "policy/scholarchain-spike-emr-*")
    error_message = "No statement may match spike-prefixed customer policies by pattern (that would include the boundary)."
  }
}

# ---- B2: tags can only be applied at creation, so tag conditions cannot be laundered

run "tags_apply_only_at_creation_and_nothing_unconditioned" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Deny" || !contains(st.Action, "ec2:CreateTags") || (
          try(st.Condition.StringEquals["ec2:CreateAction"], null) != null && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr"
        )
      ])
    ])
    error_message = "ec2:CreateTags only with ec2:CreateAction and the stack request tag."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "ec2:RevokeSecurityGroupIngress") || try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr"
      ])
    ])
    error_message = "Security group rule revocation is only for stack-tagged groups; the default-security-group adoption statement is gone."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "elasticfilesystem:TagResource") || (st.Condition.StringEquals["elasticfilesystem:CreateAction"] == ["CreateFileSystem", "CreateAccessPoint"])
      ])
    ])
    error_message = "elasticfilesystem:TagResource only with the CreateAction condition."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "elasticmapreduce:AddTags") || (try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr" && !can(st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"]))
      ])
    ])
    error_message = "EMR AddTags requires the cluster to already carry the stack tag; a request tag alone must never satisfy it."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "elasticmapreduce:TerminateJobFlows") || st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr"
      ])
    ])
    error_message = "TerminateJobFlows only on stack-tagged clusters."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !contains(st.Action, "elasticmapreduce:RemoveTags") && !contains(st.Action, "ec2:DeleteTags") && !contains(st.Action, "kms:UntagResource") && !contains(st.Action, "elasticfilesystem:UntagResource")
      ])
    ])
    error_message = "No untagging actions are granted."
  }
}

run "kms_administration_is_in_the_key_policy_not_iam" {
  command = plan

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Deny" || !anytrue([for a in st.Action : contains(["kms:PutKeyPolicy", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:DisableKey", "kms:EnableKey", "kms:EnableKeyRotation", "kms:DisableKeyRotation", "kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:CreateGrant", "kms:DescribeKey", "kms:GetKeyPolicy"], a)])
      ])
    ])
    error_message = "Key administration and use are granted by the key policy to the deployer role ARN, not by IAM tag scoping."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "kms:")]) || !can(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"])
      ])
    ])
    error_message = "No IAM KMS statement may key off a resource tag."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--storage"].policy).Statement :
      st.Action == ["kms:TagResource"] && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "kms:TagResource stays only for tag-on-create."
  }
}

run "boundary_tags_on_create_only_and_auto_termination_actions" {
  command = plan

  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !contains(st.Action, "ec2:CreateTags") || can(st.Condition.StringEquals["ec2:CreateAction"])
    ])
    error_message = "The boundary allows ec2:CreateTags only with ec2:CreateAction."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for a in st.Action : a == "ec2:CreateTags" || a == "ec2:DeleteTags"]) || length(st.Action) == 1
    ])
    error_message = "Tag actions sit in their own boundary statements, apart from the mutating actions."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      toset(st.Action) == toset(["elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy"]) && st.Resource == ["arn:aws:elasticmapreduce:us-east-2:111122223333:cluster/*"] && st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "The boundary must allow the three auto-termination actions on stack-tagged clusters in us-east-2."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      contains(st.Action, "kms:Decrypt") && st.Condition["ForAnyValue:StringEquals"]["kms:ResourceAliases"] == "alias/scholarchain-spike-emr-key" && !can(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"])
    ])
    error_message = "The boundary scopes KMS use by the spike key alias, not by a tag."
  }
}

# ---- R1: the boundary's EC2 ceiling mirrors AmazonEMRServicePolicy_v2's tag conditions

run "boundary_ec2_mutations_are_tag_conditioned_like_emr_v2" {
  command = plan

  # Every non-Describe EC2 statement: CreateTags needs ec2:CreateAction; everything else needs
  # the EMR managed-policies tag as a resource tag (existing) or request tag (new), except the
  # launch-dependency statement, whose resources are untaggable existing AMI/key-pair/... types.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for a in st.Action : startswith(a, "ec2:") && !startswith(a, "ec2:Describe")]) || (
        st.Action == ["ec2:CreateTags"]
        ? can(st.Condition.StringEquals["ec2:CreateAction"])
        : (
          can(st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"]) || can(st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"]) ||
          (st.Sid == "V2ExistingLaunchDependencies" && toset(st.Action) == toset(["ec2:RunInstances", "ec2:CreateFleet"]) && alltrue([for r in st.Resource : anytrue([for t in ["image/ami-", "key-pair/", "capacity-reservation/", "dedicated-host/", "fleet/", "placement-group/EMR_"] : strcontains(r, t)])]))
        )
      )
    ])
    error_message = "Every non-Describe EC2 boundary statement needs an EMR-tag (resource or request) condition, or ec2:CreateAction for CreateTags, or be the launch-dependency statement over untaggable existing types."
  }
  # Actions that are not creates act on EXISTING resources and need the resource tag.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([
        for a in st.Action :
        startswith(a, "ec2:") && !startswith(a, "ec2:Describe") && !contains(["ec2:RunInstances", "ec2:CreateFleet", "ec2:CreateLaunchTemplate", "ec2:CreateNetworkInterface", "ec2:CreateSecurityGroup", "ec2:CreateTags"], a)
      ]) || can(st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"])
    ])
    error_message = "Delete, Modify, Terminate, Authorize, Revoke and DeleteTags need aws:ResourceTag for-use-with-amazon-emr-managed-policies."
  }
  # Create actions on NEW instances, volumes and ENIs need the request tag.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for r in st.Resource : strcontains(r, ":instance/") || strcontains(r, ":volume/") || strcontains(r, ":network-interface/")]) || st.Action == ["ec2:DeleteNetworkInterface", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances"] || st.Action == ["ec2:DeleteTags"] || st.Action == ["ec2:CreateTags"] || can(st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"])
    ])
    error_message = "Creating instances, volumes and network interfaces requires aws:RequestTag for-use-with-amazon-emr-managed-policies."
  }
  # Existing subnets, security groups and VPCs must also carry the stack tag.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for r in st.Resource : strcontains(r, ":subnet/") || strcontains(r, ":vpc/") || (strcontains(r, ":security-group/") && can(st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"]))]) || st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "Existing subnet, VPC and security-group targets must carry both the EMR tag and the stack tag."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for a in st.Action : startswith(a, "ec2:") && !startswith(a, "ec2:Describe")]) || !contains(st.Resource, "*")
    ])
    error_message = "EC2 mutations name resource ARNs, never '*'."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for a in st.Action : contains(["ec2:CreateVpcEndpoint", "ec2:ModifyVpcEndpoint", "ec2:CreatePlacementGroup", "ec2:DeletePlacementGroup", "ec2:CreateLaunchTemplateVersion"], a)])
    ])
    error_message = "EMR 8 VPC-endpoint, placement-group and launch-template-version actions of v2 are deliberately outside this cluster's ceiling."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary[0].policy) < 6144
    error_message = "The boundary must stay below the managed-policy limit."
  }
}

# ---- same-device `aws login` for the deployer role

run "login_policy_is_exact_and_independent_of_permission_sets" {
  command = plan

  assert {
    condition = jsondecode(aws_iam_role_policy.login.policy).Statement == [{
      Sid       = "DeployerSameDeviceLogin"
      Effect    = "Allow"
      Action    = ["signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"]
      Resource  = ["arn:aws:signin:us-east-2:111122223333:oauth2/public-client/localhost"]
      Condition = { StringEquals = { "signin:OAuthClientId" = "arn:aws:signin:::devtools/same-device" } }
    }]
    error_message = "Exactly the two signin actions on the localhost public-client ARN with the same-device client condition."
  }
  assert {
    condition     = !strcontains(aws_iam_role_policy.login.policy, "signin:*") && !strcontains(aws_iam_role_policy.login.policy, "\"*\"")
    error_message = "No signin:* and no '*' resource."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      !strcontains(p.policy, "signin:")
    ]) && !strcontains(aws_iam_policy.spike_boundary[0].policy, "signin:")
    error_message = "The permission sets and the boundary carry no signin actions; login is a separate policy."
  }
}

run "login_policy_exists_as_its_own_resource_not_a_permission_set_part" {
  command = plan

  assert {
    condition     = aws_iam_role_policy.login.name == "scholarchain-deployer-same-device-login" && !contains(keys(aws_iam_policy.permission_set), "spike-emr--login")
    error_message = "The login policy is a separate inline policy, outside enabled_permission_sets."
  }
}

# ---- live-apply AccessDenied: create/attach calls are also authorized against EXISTING
# parent resources, which need the stack ResourceTag (a request tag never applies to them).
# Resource types per call: Service Authorization Reference list_ec2 / list_efs.

run "every_spike_create_and_attach_call_is_allowed_on_its_existing_parents" {
  command = plan

  assert {
    condition = alltrue([
      for c in [
        { a = "ec2:CreateSubnet", t = "vpc" },
        { a = "ec2:CreateRouteTable", t = "vpc" },
        { a = "ec2:CreateSecurityGroup", t = "vpc" },
        { a = "ec2:CreateVpcEndpoint", t = "vpc" },
        { a = "ec2:CreateVpcEndpoint", t = "route-table" },
        { a = "ec2:CreateNatGateway", t = "subnet" },
        { a = "ec2:CreateNatGateway", t = "elastic-ip" },
        { a = "ec2:AttachInternetGateway", t = "vpc" },
        { a = "ec2:AttachInternetGateway", t = "internet-gateway" },
        { a = "ec2:AssociateRouteTable", t = "route-table" },
        { a = "ec2:AssociateRouteTable", t = "subnet" },
        { a = "ec2:CreateRoute", t = "route-table" },
        { a = "ec2:DeleteRoute", t = "route-table" },
        { a = "ec2:AuthorizeSecurityGroupIngress", t = "security-group" },
        { a = "ec2:AuthorizeSecurityGroupEgress", t = "security-group" },
        { a = "ec2:RevokeSecurityGroupIngress", t = "security-group" },
        { a = "ec2:ModifyVpcAttribute", t = "vpc" },
        { a = "ec2:CreateNetworkInterface", t = "subnet" },
        { a = "ec2:CreateNetworkInterface", t = "security-group" },
        { a = "ec2:DeleteNatGateway", t = "natgateway" },
        { a = "ec2:ReleaseAddress", t = "elastic-ip" },
        { a = "ec2:DeleteVpcEndpoints", t = "vpc-endpoint" },
        { a = "ec2:DeleteSubnet", t = "subnet" },
        { a = "ec2:DeleteVpc", t = "vpc" },
      ] :
      anytrue([
        for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
        st.Effect == "Allow" && contains(st.Action, c.a) && contains(st.Resource, "arn:aws:ec2:us-east-2:111122223333:${c.t}/*") &&
        try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr" && try(st.Condition.StringEquals["aws:RequestedRegion"], "") == "us-east-2"
      ])
    ])
    error_message = "Every EC2 call the spike root makes must be allowed on each existing parent/referenced resource type with the stack ResourceTag and the region condition."
  }
  assert {
    condition = alltrue([
      for c in [
        { a = "elasticfilesystem:CreateAccessPoint", t = "file-system" },
        { a = "elasticfilesystem:CreateMountTarget", t = "file-system" },
        { a = "elasticfilesystem:PutFileSystemPolicy", t = "file-system" },
        { a = "elasticfilesystem:PutBackupPolicy", t = "file-system" },
        { a = "elasticfilesystem:DeleteMountTarget", t = "file-system" },
      ] :
      anytrue([
        for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
        st.Effect == "Allow" && contains(st.Action, c.a) && contains(st.Resource, "arn:aws:elasticfilesystem:us-east-2:111122223333:${c.t}/*") &&
        try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr"
      ])
    ])
    error_message = "EFS calls that act on an existing file system need the stack ResourceTag."
  }
  # The parent statement cannot create anything new and tags are still create-only.
  assert {
    condition = alltrue([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st.Sid != "Ec2CreateOnExistingStackParents" || (!can(st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"]) && !contains(st.Action, "ec2:CreateTags") && !contains(st.Action, "ec2:CreateVpc") && !contains(st.Resource, "*"))
    ])
    error_message = "The parent statement is ResourceTag-only, names no wildcard resource, and grants no CreateTags or CreateVpc."
  }
}

run "create_access_point_requires_both_stack_tags_everywhere" {
  command = plan

  assert {
    condition = alltrue([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st.Effect != "Allow" || !contains(st.Action, "elasticfilesystem:CreateAccessPoint") || (
        try(st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"], "") == "spike-emr" &&
        try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr" &&
        try(st.Condition.StringEquals["aws:RequestedRegion"], "") == "us-east-2"
      )
    ])
    error_message = "Every Allow of elasticfilesystem:CreateAccessPoint must carry BOTH the stack request tag and the stack resource tag (plus region): a request tag alone allows foreign file systems, a resource tag alone allows untagged access points."
  }
  assert {
    condition = length([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st if st.Effect == "Allow" && contains(st.Action, "elasticfilesystem:CreateAccessPoint")
    ]) == 1
    error_message = "Exactly one Allow grants CreateAccessPoint."
  }
}

# ---- live attempt 2: RunInstances request shape. The EMR service role launched with tag
# specifications for instance, network-interface and volume (EMR tag + stack tag) into the stack
# subnet with the stack security group, using an existing AMI and an encrypted volume.
# A request tag applies only to the resource being created: existing AMI/subnet/security group
# can match only on region or on their own resource tags.

run "run_instances_request_shape_matches_a_boundary_statement_for_every_resource_type" {
  command = plan

  assert {
    condition = alltrue([
      for c in [
        { t = "instance", ctx = "new" },
        { t = "volume", ctx = "new" },
        { t = "network-interface", ctx = "new" },
        { t = "subnet", ctx = "existing" },
        { t = "security-group", ctx = "existing" },
        { t = "key-pair", ctx = "bare" },
        { t = "capacity-reservation", ctx = "bare" },
      ] :
      anytrue([
        for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
        st.Effect == "Allow" && contains(st.Action, "ec2:RunInstances") && contains(st.Resource, "arn:aws:ec2:us-east-2:111122223333:${c.t}/*") &&
        length(keys(st.Condition)) == 1 && alltrue([
          for k, v in st.Condition.StringEquals : try((c.ctx == "new" ? {
            "aws:RequestedRegion"                                     = "us-east-2"
            "aws:RequestTag/for-use-with-amazon-emr-managed-policies" = "true"
            "aws:RequestTag/scholarchain:stack"                       = "spike-emr"
            } : c.ctx == "existing" ? {
            "aws:RequestedRegion"                                      = "us-east-2"
            "aws:ResourceTag/for-use-with-amazon-emr-managed-policies" = "true"
            "aws:ResourceTag/scholarchain:stack"                       = "spike-emr"
          } : { "aws:RequestedRegion" = "us-east-2" })[k] == v, false)
        ])
      ])
    ])
    error_message = "Each RunInstances resource type must be matched by a boundary Allow whose conditions are all satisfiable: request tags only for new instance/volume/ENI, resource tags only for the existing subnet and security group, region only for untaggable existing types."
  }
  # The AMI has an account-less ARN and no tags to match: region only.
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Effect == "Allow" && contains(st.Action, "ec2:RunInstances") && contains(st.Resource, "arn:aws:ec2:us-east-2::image/ami-*") && st.Condition == { StringEquals = { "aws:RequestedRegion" = "us-east-2" } }
    ])
    error_message = "RunInstances on an existing image ARN must be allowed on the region condition alone."
  }
  # Existing-resource types never depend on a request tag.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for r in st.Resource : anytrue([for t in [":image/", ":key-pair/", ":capacity-reservation/", ":dedicated-host/", ":placement-group/", ":subnet/", ":vpc/"] : strcontains(r, t)])]) || !can(st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"])
    ])
    error_message = "Boundary statements that name existing-resource types (image, key pair, capacity reservation, dedicated host, placement group, subnet, vpc) must not require a request tag."
  }
  # New instances, volumes and ENIs are never allowed without the request tag.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Effect != "Allow" || !contains(st.Action, "ec2:RunInstances") || !anytrue([for r in st.Resource : anytrue([for t in [":instance/", ":volume/", ":network-interface/"] : strcontains(r, t)])]) || st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"] == "true"
    ])
    error_message = "RunInstances on new instance, volume and ENI resources requires aws:RequestTag for-use-with-amazon-emr-managed-policies."
  }
  # Encrypted volumes: the key conditions the boundary uses.
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      alltrue([for a in ["kms:CreateGrant", "kms:GenerateDataKeyWithoutPlaintext", "kms:Decrypt", "kms:DescribeKey"] : contains(st.Action, a)]) && st.Condition["ForAnyValue:StringEquals"]["kms:ResourceAliases"] == "alias/scholarchain-spike-emr-key"
      ]) && anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Action == ["kms:DescribeKey"] && st.Condition.StringEquals["kms:ViaService"] == "ec2.us-east-2.amazonaws.com"
    ])
    error_message = "KMS: CreateGrant, GenerateDataKeyWithoutPlaintext, Decrypt by key alias; DescribeKey also via EC2."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Action == ["iam:PassRole"] && st.Condition.StringEquals["iam:PassedToService"] == ["ec2.amazonaws.com"]
    ])
    error_message = "The instance-profile role may be passed to EC2 (RunInstances with an instance profile needs iam:PassRole; instance-profile is not an EC2 resource type)."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary[0].policy) < 6144
    error_message = "The boundary must stay below the managed-policy limit."
  }
}

run "disassociate_address_is_allowed_on_stack_elastic_ips" {
  command = plan

  assert {
    condition = anytrue([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st.Effect == "Allow" && contains(st.Action, "ec2:DisassociateAddress") && contains(st.Resource, "arn:aws:ec2:us-east-2:111122223333:elastic-ip/*") && st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "ec2:DisassociateAddress on stack-tagged elastic IPs (the reference lists elastic-ip, network-interface and instance as optional resource types, no association type)."
  }
}

# ---- Phase 13C carried items 2, 14, 16 and 17: each negative test fails on the policy it replaced -----------------------------

run "item_17_boundary_instance_and_eni_mutations_require_the_stack_tag" {
  command = plan

  # Every boundary Allow that can act on an EXISTING instance, network interface or launch template (anything other than the
  # create calls, which are scoped by request tags) must require the stack resource tag, so a passed spike role cannot
  # terminate, modify, untag or delete another stack's EMR-tagged resources.
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Effect != "Allow" || !anytrue([for r in st.Resource : anytrue([for t in [":instance/", ":network-interface/", ":launch-template/"] : strcontains(r, t)])]) ||
      alltrue([for a in st.Action : contains(["ec2:RunInstances", "ec2:CreateNetworkInterface", "ec2:CreateSecurityGroup", "ec2:CreateFleet", "ec2:CreateTags"], a)]) ||
      try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr"
    ])
    error_message = "Item 17: a boundary statement that can act on an existing instance, network-interface or launch-template must require aws:ResourceTag/scholarchain:stack = spike-emr (the EMR managed-policies tag alone reaches every EMR cluster in the account)."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Sid == "V2ManageTaggedInstancesAndEnis" && toset(st.Action) == toset(["ec2:DeleteNetworkInterface", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances"]) &&
      toset(st.Resource) == toset(["arn:aws:ec2:us-east-2:111122223333:network-interface/*", "arn:aws:ec2:us-east-2:111122223333:instance/*"]) &&
      st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr" && st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"] == "true" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "Item 17: terminate, modify-attribute and ENI delete need the stack tag, the EMR tag and the region."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      st.Action == ["ec2:DeleteTags"] && st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"] == "spike-emr" && st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"] == "true"
    ])
    error_message = "Item 17: removing tags is a modification and needs the stack tag too."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement :
      !anytrue([for a in st.Action : strcontains(lower(a), "launchtemplate") && !startswith(a, "ec2:Describe")]) || try(st.Condition.StringEquals["aws:ResourceTag/scholarchain:stack"], "") == "spike-emr"
    ])
    error_message = "Item 17: no launch-template action may be granted without the stack tag (v2's launch-template statements are deliberately left out of the boundary)."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary[0].policy) < 6144
    error_message = "The tightened boundary must stay below the managed-policy limit."
  }
}

run "item_2_eni_delete_and_modify_are_scoped_to_the_region_and_account" {
  command = plan

  assert {
    condition = length([
      for st in flatten(concat([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement], jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement)) :
      st if st.Effect == "Allow" && anytrue([for a in st.Action : contains(["ec2:DeleteNetworkInterface", "ec2:ModifyNetworkInterfaceAttribute"], a)])
    ]) >= 2
    error_message = "The ENI delete/modify grants exist (a vacuous pass is not accepted)."
  }
  assert {
    condition = alltrue([
      for st in flatten(concat([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement], jsondecode(aws_iam_policy.spike_boundary[0].policy).Statement)) :
      st.Effect != "Allow" || !anytrue([for a in st.Action : contains(["ec2:DeleteNetworkInterface", "ec2:ModifyNetworkInterfaceAttribute"], a)]) || (
        alltrue([for r in st.Resource : startswith(r, "arn:aws:ec2:us-east-2:111122223333:network-interface/") || startswith(r, "arn:aws:ec2:us-east-2:111122223333:instance/")]) && try(st.Condition.StringEquals["aws:RequestedRegion"], "") == "us-east-2"
      )
    ])
    error_message = "Item 2: every Allow of ec2:DeleteNetworkInterface or ec2:ModifyNetworkInterfaceAttribute names network-interface (or, in the boundary, instance) ARNs of this region and account and pins aws:RequestedRegion to us-east-2."
  }
}

run "item_14_kms_tag_resource_is_limited_to_the_spike_tag_keys" {
  command = plan

  assert {
    condition = length([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st if st.Effect == "Allow" && contains(st.Action, "kms:TagResource")
    ]) == 1
    error_message = "Exactly one Allow grants kms:TagResource."
  }
  assert {
    condition = alltrue([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st.Effect != "Allow" || !contains(st.Action, "kms:TagResource") || (
        toset(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"]) == toset(["course", "project", "environment", "owner", "expiration", "scholarchain:stack", "for-use-with-amazon-emr-managed-policies", "Name"]) &&
        st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
      )
    ])
    error_message = "Item 14: kms:TagResource is limited to the eight tag keys of the spike root (aws:TagKeys, ForAllValues) with the stack request tag; a statement without the key restriction must fail this test."
  }
}

run "item_14_a_wildcard_or_missing_tag_key_list_is_rejected" {
  command = plan
  variables {
    spike_kms_tag_keys = ["*"]
  }
  expect_failures = [var.spike_kms_tag_keys]
}

run "item_14_the_tag_key_list_must_keep_the_stack_key" {
  command = plan
  variables {
    spike_kms_tag_keys = ["course", "owner"]
  }
  expect_failures = [var.spike_kms_tag_keys]
}

run "item_16_create_role_is_limited_to_the_two_spike_roles_and_the_trust_policy_stays_fixed" {
  command = plan

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Allow" && st.Action == ["iam:CreateRole"] &&
      toset(st.Resource) == toset(["arn:aws:iam::111122223333:role/scholarchain-spike-emr-service", "arn:aws:iam::111122223333:role/scholarchain-spike-emr-instance"]) && length(st.Resource) == 2 &&
      st.Condition.StringEquals["iam:PermissionsBoundary"] == "arn:aws:iam::111122223333:policy/scholarchain-spike-emr-boundary" && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "spike-emr"
    ])
    error_message = "Item 16: iam:CreateRole names exactly the two spike role ARNs (no prefix wildcard), with the boundary and stack tag required."
  }
  assert {
    condition = alltrue([
      for st in flatten([for k, p in aws_iam_policy.permission_set : jsondecode(p.policy).Statement]) :
      st.Effect != "Allow" || (!contains(st.Action, "iam:UpdateAssumeRolePolicy") && (!contains(st.Action, "iam:CreateRole") || alltrue([for r in st.Resource : !strcontains(r, "*")])))
    ])
    error_message = "Item 16: no Allow of iam:UpdateAssumeRolePolicy anywhere, and iam:CreateRole never on a wildcard resource."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" && contains(st.Action, "iam:UpdateAssumeRolePolicy") && contains(st.Action, "iam:PutRolePermissionsBoundary") && contains(st.Action, "iam:DeleteRolePermissionsBoundary")
      ]) && anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["spike-emr--iam"].policy).Statement :
      st.Effect == "Deny" && st.Action == ["sts:AssumeRole"]
    ])
    error_message = "Item 16: the trust policy cannot be changed after creation and the deployer cannot assume a spike role."
  }
}

run "item_16_role_names_outside_the_spike_prefix_or_a_prefix_wildcard_are_rejected" {
  command = plan
  variables {
    spike_role_names = ["scholarchain-spike-emr-*", "scholarchain-spike-emr-instance"]
  }
  expect_failures = [var.spike_role_names]
}

run "item_16_only_two_role_names_are_accepted" {
  command = plan
  variables {
    spike_role_names = ["scholarchain-spike-emr-service", "scholarchain-spike-emr-instance", "scholarchain-spike-emr-extra"]
  }
  expect_failures = [var.spike_role_names]
}

# ======================================================================================================================
# Phase 14 (decision 14-6): the phase14-main permission set. Every expectation below is hand-derived from the resource types
# of the main root and from the AWS documentation named in deployer/README.md, not read back from the policy text.
# Mock-only; each run selects the set explicitly (the file-level default above still plans the spike for the old tests).
# ======================================================================================================================

run "p14_default_permission_set_is_phase14_main_and_not_the_spike" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition     = toset(keys(aws_iam_policy.permission_set)) == toset(["phase14-main--network", "phase14-main--network-mod", "phase14-main--data", "phase14-main--keys-obs", "phase14-main--compute", "phase14-main--emr-efs", "phase14-main--iam"])
    error_message = "phase14-main is exactly seven named documents."
  }
  assert {
    condition     = length(aws_iam_policy.spike_boundary) == 0 && alltrue([for k, p in aws_iam_policy.permission_set : !startswith(k, "spike-emr--")])
    error_message = "spike-emr (and its boundary) must not be attached when phase14-main is enabled."
  }
  assert {
    condition     = output.spike_permissions_boundary_arn == null
    error_message = "No spike boundary output while the spike is not enabled."
  }
}

run "p14_spike_and_phase14_main_together_are_rejected" {
  command = plan
  variables {
    enabled_permission_sets = ["spike-emr", "phase14-main"]
  }
  expect_failures = [aws_iam_role.deployer]
}

run "p14_every_document_is_under_6144_characters_and_attachments_fit_the_quota" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition     = alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144])
    error_message = "Every phase14-main document must stay below 6144 characters (the size AWS counts)."
  }
  assert {
    condition     = length(aws_iam_policy.main_boundary_runtime[0].policy) < 6144 && length(aws_iam_policy.main_boundary_emr[0].policy) < 6144
    error_message = "Both boundaries must stay below 6144 characters."
  }
  assert {
    condition     = length(aws_iam_role_policy_attachment.permission_set) == 7 && length(aws_iam_role_policy_attachment.permission_set) <= 10
    error_message = "Seven managed attachments (quota 10); the login policy is inline and does not count."
  }
  assert {
    condition     = aws_iam_role_policy.login.name == "scholarchain-deployer-same-device-login"
    error_message = "The always-attached login policy is the only inline policy (it does not count toward the managed-policy quota)."
  }
}

run "p14_documents_still_fit_with_the_longest_allowed_environment_name" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
    main_environment        = "abcdefghij"
  }

  assert {
    condition     = alltrue([for k, p in aws_iam_policy.permission_set : length(p.policy) < 6144])
    error_message = "A 10-character environment name (the main root's maximum) must not push a document over the limit."
  }
  assert {
    condition     = !strcontains(aws_iam_policy.main_boundary_emr[0].policy, "course") && !strcontains(aws_iam_policy.main_boundary_runtime[0].policy, "course") && strcontains(aws_iam_policy.main_boundary_emr[0].policy, "\"aws:ResourceTag/environment\":\"abcdefghij\"") && strcontains(aws_iam_policy.main_boundary_runtime[0].policy, "scholarchain-abcdefghij-data")
    error_message = "Both boundaries must follow main_environment everywhere (no hard-coded environment value)."
  }
}

run "p14_trust_requires_mfa_and_the_session_is_one_hour" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition     = jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Condition.Bool["aws:MultiFactorAuthPresent"] == "true" && length(jsondecode(aws_iam_role.deployer.assume_role_policy).Statement) == 1
    error_message = "Trust must have exactly one statement that requires MFA."
  }
  assert {
    condition     = aws_iam_role.deployer.max_session_duration == 3600
    error_message = "MaxSessionDuration must be 3600 seconds."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deployer.assume_role_policy).Statement[0].Principal.AWS == "arn:aws:iam::111122223333:user/example-operator"
    error_message = "Trust must name exactly the operator."
  }
}

run "p14_no_wildcard_action_and_resource_star_only_for_reads_or_the_honest_list" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([for st in jsondecode(p.policy).Statement : alltrue([for a in st.Action : a != "*" && a != "*:*" && !endswith(a, ":*") && !endswith(a, "*")])])
    ])
    error_message = "No Action '*', '*:*', '<svc>:*' or prefix wildcard in any phase14-main document."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Deny" || !contains(st.Resource, "*") || alltrue([
          for a in st.Action :
          can(regex("^(Describe|List|Get)", split(":", a)[1])) || contains(
            ["kms:CreateKey", "ecs:RegisterTaskDefinition", "ecs:DeregisterTaskDefinition", "ecs:DeleteTaskDefinitions", "elasticmapreduce:RunJobFlow", "elasticmapreduce:CreateSecurityConfiguration", "elasticmapreduce:DeleteSecurityConfiguration", "route53:CreateHostedZone", "route53:DeleteHostedZone", "route53:ChangeResourceRecordSets", "route53:ChangeTagsForResource", "acm:RequestCertificate"],
            a
          )
        ])
      ])
    ])
    error_message = "Resource '*' is allowed only for Describe/List/Get reads or the documented honest-list write actions."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement : alltrue([for a in st.Action : !endswith(a, "*")])
    ]) && alltrue([for st in jsondecode(aws_iam_policy.main_boundary_emr[0].policy).Statement : alltrue([for a in st.Action : !endswith(a, "*")])])
    error_message = "Both boundaries enumerate their actions."
  }
}

run "p14_every_regional_allow_statement_is_pinned_to_us_east_2" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Deny" || startswith(st.Action[0], "iam:") || startswith(st.Action[0], "route53:") || try(st.Condition.StringEquals["aws:RequestedRegion"], "") == "us-east-2"
      ])
    ])
    error_message = "Every Allow statement outside the global services (iam, route53) must carry aws:RequestedRegion = us-east-2."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([for st in jsondecode(p.policy).Statement : !(startswith(st.Action[0], "iam:") || startswith(st.Action[0], "route53:")) || !contains(keys(try(st.Condition.StringEquals, {})), "aws:RequestedRegion")])
    ])
    error_message = "Global services must not carry a RequestedRegion condition: IAM and Route 53 are served from one endpoint, so the condition would block them."
  }
}

run "p14_iam_statements_only_touch_scholarchain_course_roles_profiles_and_boundaries" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      alltrue([
        for r in st.Resource :
        startswith(r, "arn:aws:iam::111122223333:role/scholarchain-course-") || startswith(r, "arn:aws:iam::111122223333:instance-profile/scholarchain-course-") || startswith(r, "arn:aws:iam::111122223333:policy/scholarchain-course-") || startswith(r, "arn:aws:iam::111122223333:role/aws-service-role/") || r == "*"
      ])
    ])
    error_message = "Every IAM resource must be a scholarchain-course-* role, instance profile or boundary policy, or a named service-linked role (the one '*' is the secret-value Deny)."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      !startswith(st.Action[0], "iam:") || alltrue([for r in st.Resource : !strcontains(r, "scholarchain-deployer") && !strcontains(r, "scholarchain-billing") && !endswith(r, ":role/*") && !endswith(r, ":role/scholarchain-*")])
    ])
    error_message = "The prefix must not reach scholarchain-deployer or scholarchain-billing-deployer."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      k == "phase14-main--iam" || alltrue([for st in jsondecode(p.policy).Statement : !anytrue([for a in st.Action : startswith(a, "iam:")])])
    ])
    error_message = "IAM actions live only in the iam document."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Effect == "Deny" || !anytrue([for a in st.Action : contains(["iam:CreatePolicy", "iam:CreatePolicyVersion", "iam:AttachRolePolicy", "iam:DetachRolePolicy", "iam:CreateUser", "iam:CreateAccessKey", "iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy"], a)])
    ])
    error_message = "The main root creates no customer-managed policy, user or managed-policy attachment: none of those actions may be allowed."
  }
}

run "p14_create_role_requires_the_project_boundary_and_the_project_tags" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = length([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement : st
      if st.Effect == "Allow" && contains(st.Action, "iam:CreateRole")
    ]) == 2
    error_message = "Exactly two CreateRole statements: the runtime roles and the EMR service role."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      !(st.Effect == "Allow" && contains(st.Action, "iam:CreateRole")) || (contains(
        ["arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary", "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"],
        st.Condition.StringEquals["iam:PermissionsBoundary"]
      ) && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain" && st.Condition.StringEquals["aws:RequestTag/environment"] == "course")
    ])
    error_message = "CreateRole must require exactly the runtime or the EMR boundary ARN and the project and environment request tags."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      contains(st.Action, "iam:CreateRole") && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-emr-service"] && st.Condition.StringEquals["iam:PermissionsBoundary"] == "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"
    ])
    error_message = "The EMR service role must be created only with the EMR service boundary."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      !(st.Effect == "Allow" && (contains(st.Action, "iam:PutRolePolicy") || contains(st.Action, "iam:DeleteRolePolicy"))) || toset(st.Condition.StringEquals["iam:PermissionsBoundary"]) == toset(["arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary", "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"])
    ])
    error_message = "Putting or deleting a role policy needs the role to carry one of the two boundaries."
  }
}

run "p14_boundary_tamper_denies_exist_and_no_allow_undoes_them" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Effect == "Deny" && toset(st.Action) == toset(["iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion"]) && toset(st.Resource) == toset(["arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary", "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"])
    ])
    error_message = "Both boundary policies must be protected from new versions, default switches and deletion."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Effect == "Deny" && contains(st.Action, "iam:PutRolePermissionsBoundary") && contains(st.Action, "iam:DeleteRolePermissionsBoundary") && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-*"]
    ])
    error_message = "Replacing or removing a role's boundary must be denied on every main role."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Effect == "Deny" && st.Action == ["sts:AssumeRole"] && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-*"]
    ])
    error_message = "The deployer must never be able to assume a main role, whatever its trust policy says."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Effect == "Deny" && st.Action == ["secretsmanager:GetSecretValue", "secretsmanager:BatchGetSecretValue"] && st.Resource == ["*"] && !can(st.Condition)
    ])
    error_message = "Reading secret values must be denied unconditionally."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([for st in jsondecode(p.policy).Statement : st.Effect == "Deny" || !anytrue([for a in st.Action : contains(["secretsmanager:GetSecretValue", "secretsmanager:BatchGetSecretValue", "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion", "iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "sts:AssumeRole"], a)])])
    ])
    error_message = "No Allow statement may grant the denied actions."
  }
}

run "p14_pass_role_is_limited_by_passed_to_service" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      !contains(st.Action, "iam:PassRole") || (length(st.Condition.StringEquals["iam:PassedToService"]) == 1 && !contains(st.Resource, "*") && alltrue([for r in st.Resource : startswith(r, "arn:aws:iam::111122223333:role/scholarchain-course-")]))
    ])
    error_message = "Every PassRole statement must name exactly one service via iam:PassedToService and only scholarchain-course-* roles."
  }
  assert {
    condition = toset(flatten([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      contains(st.Action, "iam:PassRole") ? st.Condition.StringEquals["iam:PassedToService"] : []
    ])) == toset(["ecs-tasks.amazonaws.com", "elasticmapreduce.amazonaws.com", "ec2.amazonaws.com", "rds.amazonaws.com", "states.amazonaws.com"])
    error_message = "PassRole may reach exactly ecs-tasks, elasticmapreduce, ec2, rds (Neptune) and states."
  }
}

run "p14_tag_conditions_carry_the_exact_project_and_environment_values" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement : [
          for ck, cv in try(st.Condition.StringEquals, {}) :
          ck == "aws:RequestTag/project" || ck == "aws:ResourceTag/project" ? cv == "scholarchain" : (ck == "aws:RequestTag/environment" || ck == "aws:ResourceTag/environment" ? cv == "course" : true)
        ]
      ]
    ]))
    error_message = "Tag conditions must carry the exact values scholarchain and course, not merely the keys."
  }
  assert {
    condition = length(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement : [for ck, cv in try(st.Condition.StringEquals, {}) : ck if startswith(ck, "aws:RequestTag/") || startswith(ck, "aws:ResourceTag/")]
      ]
    ])) >= 40
    error_message = "Tag-condition coverage is too low to be meaningful (hand-counted: at least 40 across the set)."
  }
}

run "p14_actions_without_a_resource_type_keep_their_request_tags" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement :
      st.Effect == "Allow" && st.Action == ["kms:CreateKey"] && st.Resource == ["*"] && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain" && st.Condition.StringEquals["aws:RequestedRegion"] == "us-east-2"
    ])
    error_message = "kms:CreateKey (no resource type) is allowed only under the request tags and the region."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--emr-efs"].policy).Statement :
      st.Effect == "Allow" && st.Action == ["elasticmapreduce:RunJobFlow"] && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain" && st.Condition.StringEquals["aws:RequestTag/scholarchain:stack"] == "main-emr" && st.Condition.StringEquals["aws:RequestTag/for-use-with-amazon-emr-managed-policies"] == "true"
    ])
    error_message = "RunJobFlow requires the project tags, the main-emr stack tag and the EMR managed-policies tag."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--compute"].policy).Statement :
      st.Effect == "Allow" && st.Action == ["ecs:RegisterTaskDefinition"] && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain"
    ])
    error_message = "Registering a task definition requires the request tags."
  }
}

# Repair round 1 (F2). The deployer's IAM set grants NOTHING on a customer-managed key by resource tag, and nothing on a security group
# that can be tagged into scope without ec2:CreateAction. A foreign key or group that carries the project tags therefore gains no rights.
run "p14_negative_a_foreign_key_with_the_project_tags_gains_no_administration_use_or_grant_rights_from_iam" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "kms:")]) || (st.Effect == "Deny" || alltrue([for a in st.Action : contains(["kms:CreateKey", "kms:TagResource", "kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias", "kms:ListAliases"], a)]))
      ])
    ])
    error_message = "IAM may hold only kms:CreateKey, kms:TagResource (tag-at-create), alias actions on alias ARNs and kms:ListAliases; every other key action lives in the key policy."
  }
  assert {
    condition = !anytrue([
      for k, p in aws_iam_policy.permission_set :
      anytrue([
        for st in jsondecode(p.policy).Statement :
        st.Effect == "Allow" && anytrue([for a in st.Action : contains(["kms:PutKeyPolicy", "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:DisableKeyRotation", "kms:EnableKeyRotation", "kms:UntagResource", "kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant", "kms:RetireGrant", "kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:DescribeKey", "kms:GetKeyPolicy", "kms:GetKeyRotationStatus", "kms:ListResourceTags", "kms:UpdateKeyDescription", "kms:EnableKey", "kms:DisableKey"], a)])
      ])
    ])
    error_message = "No document may allow PutKeyPolicy, ScheduleKeyDeletion, DisableKeyRotation, UntagResource, CreateGrant, Decrypt or any other key administration or use action."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : startswith(a, "kms:")]) || !anytrue([for ck in flatten([for op, kv in try(st.Condition, {}) : keys(kv)]) : startswith(ck, "aws:ResourceTag/")])
      ])
    ])
    error_message = "No kms statement may be scoped by a resource tag: tagging a foreign key must not bring it into any IAM scope."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !(st.Effect == "Allow" && anytrue([for r in st.Resource : strcontains(r, ":key/")])) || (st.Action == ["kms:TagResource"] && contains(keys(st.Condition["ForAllValues:StringEquals"]), "aws:TagKeys") && st.Condition.StringEquals["aws:RequestTag/project"] == "scholarchain")
      ])
    ])
    error_message = "The only statement that may name key/* is kms:TagResource, limited by request tags and aws:TagKeys (AWS requires it to cover all keys of the account and region: https://docs.aws.amazon.com/kms/latest/developerguide/add-tags.html)."
  }
}

run "p14_negative_a_security_group_with_the_project_tags_gains_no_mutation_rights_from_iam" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  # No statement may tag a security group into scope without ec2:CreateAction, so a foreign group cannot acquire the resource tags
  # that the Authorize, Revoke, Delete and ModifySecurityGroupRules statements require.
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !(st.Effect == "Allow" && contains(st.Action, "ec2:CreateTags") && anytrue([for r in st.Resource : strcontains(r, "security-group")])) || contains(keys(st.Condition.StringEquals), "ec2:CreateAction") || contains(keys(st.Condition.StringEquals), "aws:ResourceTag/project")
      ])
    ])
    error_message = "ec2:CreateTags on security groups needs ec2:CreateAction (tag-on-create) or an existing project resource tag; request tags alone would let a foreign group be tagged into scope."
  }
  assert {
    condition = alltrue([
      for k, p in aws_iam_policy.permission_set :
      alltrue([
        for st in jsondecode(p.policy).Statement :
        !(st.Effect == "Allow" && anytrue([for a in st.Action : contains(["ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:DeleteSecurityGroup", "ec2:ModifySecurityGroupRules"], a)]) && anytrue([for r in st.Resource : strcontains(r, ":security-group/")])) || contains(keys(st.Condition.StringEquals), "aws:ResourceTag/project")
      ])
    ])
    error_message = "Every Authorize, Revoke, Delete and ModifySecurityGroupRules statement that names a security group must require the project resource tag."
  }
  assert {
    condition     = !anytrue([for k, p in aws_iam_policy.permission_set : strcontains(p.policy, "Ec2AdoptedDefaultSg")])
    error_message = "The VPC default security group is not adopted: no adoption statements (the root test asserts the network module has no aws_default_security_group)."
  }
}

run "p14_the_documents_cover_every_resource_type_the_main_root_creates" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  # Hand-derived: create, update, delete and the refresh reads of each resource type enumerated in
  # target/phase14/evidence/14a-infra/resource-types.txt. A removed action fails this run.
  assert {
    condition = alltrue([
      for a in [
        "ec2:CreateVpc", "ec2:DeleteVpc", "ec2:DescribeVpcs", "ec2:DescribeVpcAttribute", "ec2:ModifyVpcAttribute",
        "ec2:CreateSubnet", "ec2:DeleteSubnet", "ec2:DescribeSubnets", "ec2:ModifySubnetAttribute",
        "ec2:CreateInternetGateway", "ec2:AttachInternetGateway", "ec2:DetachInternetGateway", "ec2:DeleteInternetGateway", "ec2:DescribeInternetGateways",
        "ec2:AllocateAddress", "ec2:ReleaseAddress", "ec2:DescribeAddresses",
        "ec2:CreateNatGateway", "ec2:DeleteNatGateway", "ec2:DescribeNatGateways",
        "ec2:CreateRouteTable", "ec2:DeleteRouteTable", "ec2:CreateRoute", "ec2:DeleteRoute", "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable", "ec2:DescribeRouteTables",
        "ec2:CreateVpcEndpoint", "ec2:DeleteVpcEndpoints", "ec2:DescribeVpcEndpoints", "ec2:ModifyVpcEndpoint",
        "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:ModifySecurityGroupRules", "ec2:DescribeSecurityGroups", "ec2:DescribeSecurityGroupRules",
        "s3:CreateBucket", "s3:DeleteBucket", "s3:PutBucketPolicy", "s3:PutLifecycleConfiguration", "s3:PutBucketVersioning", "s3:PutEncryptionConfiguration", "s3:PutBucketPublicAccessBlock", "s3:PutBucketOwnershipControls", "s3:GetBucketTagging", "s3:PutObject",
        "s3vectors:CreateVectorBucket", "s3vectors:CreateIndex", "s3vectors:PutVectorBucketPolicy", "s3vectors:DeleteIndex", "s3vectors:DeleteVectorBucket",
        "dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:DescribeTable", "dynamodb:UpdateTable", "dynamodb:UpdateContinuousBackups", "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeTimeToLive", "dynamodb:UpdateTimeToLive", "dynamodb:ListTagsOfResource",
        "sqs:CreateQueue", "sqs:DeleteQueue", "sqs:SetQueueAttributes", "sqs:GetQueueAttributes", "sqs:ListQueueTags",
        "states:CreateStateMachine", "states:DeleteStateMachine", "states:DescribeStateMachine",
        "kms:CreateKey", "kms:TagResource", "kms:CreateAlias", "kms:ListAliases",
        "logs:CreateLogGroup", "logs:DescribeLogGroups", "logs:PutRetentionPolicy", "logs:DeleteLogGroup", "logs:ListTagsForResource",
        "cloudwatch:PutMetricAlarm", "cloudwatch:DescribeAlarms", "cloudwatch:DeleteAlarms", "cloudwatch:PutDashboard", "cloudwatch:GetDashboard", "cloudwatch:DeleteDashboards",
        "ecs:CreateCluster", "ecs:DescribeClusters", "ecs:DeleteCluster", "ecs:RegisterTaskDefinition", "ecs:DescribeTaskDefinition", "ecs:CreateService", "ecs:UpdateService", "ecs:DescribeServices", "ecs:DeleteService",
        "ecr:CreateRepository", "ecr:DescribeRepositories", "ecr:DeleteRepository", "ecr:ListTagsForResource", "ecr:PutImage", "ecr:GetAuthorizationToken",
        "elasticloadbalancing:CreateLoadBalancer", "elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:CreateTargetGroup", "elasticloadbalancing:CreateListener", "elasticloadbalancing:DeleteListener", "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeTargetGroups",
        "application-autoscaling:RegisterScalableTarget", "application-autoscaling:PutScalingPolicy", "application-autoscaling:DescribeScalableTargets", "application-autoscaling:DescribeScalingPolicies",
        "servicediscovery:CreatePrivateDnsNamespace", "servicediscovery:GetNamespace", "servicediscovery:CreateService", "servicediscovery:GetService", "servicediscovery:DeleteService", "servicediscovery:DeleteNamespace",
        "route53:CreateHostedZone", "route53:GetHostedZone", "route53:ListHostedZonesByName",
        "rds:CreateDBCluster", "rds:DescribeDBClusters", "rds:CreateDBInstance", "rds:CreateDBSubnetGroup", "rds:CreateDBClusterParameterGroup", "rds:CreateDBParameterGroup", "rds:DeleteDBCluster", "rds:DeleteDBInstance", "rds:AddRoleToDBCluster",
        "elasticmapreduce:RunJobFlow", "elasticmapreduce:DescribeCluster", "elasticmapreduce:ListInstanceGroups", "elasticmapreduce:TerminateJobFlows", "elasticmapreduce:CreateSecurityConfiguration", "elasticmapreduce:PutManagedScalingPolicy", "elasticmapreduce:AddInstanceGroups",
        "elasticfilesystem:CreateFileSystem", "elasticfilesystem:DescribeFileSystems", "elasticfilesystem:CreateMountTarget", "elasticfilesystem:CreateAccessPoint", "elasticfilesystem:PutFileSystemPolicy", "elasticfilesystem:PutBackupPolicy", "elasticfilesystem:DeleteFileSystem",
        "iam:CreateRole", "iam:PutRolePolicy", "iam:GetRole", "iam:DeleteRole", "iam:CreateInstanceProfile", "iam:AddRoleToInstanceProfile", "iam:PassRole", "iam:CreateServiceLinkedRole",
        "tag:GetResources",
      ] :
      contains(flatten([for k, p in aws_iam_policy.permission_set : [for st in jsondecode(p.policy).Statement : st.Effect == "Allow" ? st.Action : []]]), a)
    ])
    error_message = "A hand-derived action for a resource type of the main root is missing from every document."
  }
  assert {
    condition = alltrue([
      for a in ["secretsmanager:GetSecretValue", "s3:GetObject", "sts:AssumeRole", "budgets:ModifyBudget", "ce:GetCostAndUsage", "organizations:ListAccounts", "iam:CreateUser", "iam:CreateAccessKey", "ec2:RunInstances", "ec2:TerminateInstances", "neptune-db:ReadDataViaQuery", "bedrock:InvokeModel"] :
      !contains(flatten([for k, p in aws_iam_policy.permission_set : [for st in jsondecode(p.policy).Statement : st.Effect == "Allow" && !strcontains(join(",", [for r in st.Resource : r]), "artifacts") ? st.Action : []]]), a)
    ])
    error_message = "Nothing outside the stack: no secret value, foreign object, budget, cost, organization, user, instance launch (EMR launches through its service role), data-plane or model action."
  }
}

run "p14_nothing_for_budgets_billing_or_the_billing_deployer" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = !anytrue([
      for k, p in aws_iam_policy.permission_set :
      anytrue([for st in jsondecode(p.policy).Statement : anytrue([for a in st.Action : startswith(a, "budgets:") || startswith(a, "ce:") || startswith(a, "organizations:") || startswith(a, "billing:") || startswith(a, "account:")])])
    ])
    error_message = "No budget, cost, billing, organization or account action (the optional budget stays disabled in the main root)."
  }
}

run "p14_main_environment_must_be_a_valid_main_root_value" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
    main_environment        = "Course"
  }
  expect_failures = [var.main_environment]
}

run "p14_main_tag_keys_must_be_literal_and_keep_project_and_environment" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
    main_tag_keys           = ["project", "environment", "*"]
  }
  expect_failures = [var.main_tag_keys]
}

run "p14_unscoped_tagging_statement_is_limited_to_the_declared_tag_keys" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  # After repair round 1 the only statement that cannot key off an existing tag is kms:TagResource (tag-at-create).
  assert {
    condition = length([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement : st
        if st.Effect == "Allow" && !can(st.Condition.StringEquals["ec2:CreateAction"]) && !anytrue([for ck in flatten([for op, kv in try(st.Condition, {}) : keys(kv)]) : startswith(ck, "aws:ResourceTag/")]) && anytrue([for a in st.Action : endswith(a, ":TagResource") || endswith(a, ":CreateTags")]) && can(st.Condition["ForAllValues:StringEquals"])
      ]
      ]) > 0 && alltrue(flatten([
        for k, p in aws_iam_policy.permission_set : [
          for st in jsondecode(p.policy).Statement :
          !can(st.Condition["ForAllValues:StringEquals"]) || (contains(["KmsTagWithProjectTags", "AcmTagOnCreateWithProjectTags"], st.Sid) && length(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"]) == 12 && contains(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"], "project") && !contains(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"], "*"))
        ]
    ]))
    error_message = "The only statements with an aws:TagKeys restriction are KmsTagWithProjectTags and AcmTagOnCreateWithProjectTags (replan W5a), each limited to the twelve declared keys."
  }
}

run "p14_boundary_policies_are_bounded_and_the_emr_boundary_mirrors_the_tag_conditions" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.main_boundary_emr[0].policy).Statement :
      !contains(st.Action, "ec2:TerminateInstances") || (st.Condition.StringEquals["aws:ResourceTag/for-use-with-amazon-emr-managed-policies"] == "true" && st.Condition.StringEquals["aws:ResourceTag/project"] == "scholarchain")
    ])
    error_message = "The EMR boundary may terminate only EMR-tagged project instances."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement :
      !contains(st.Resource, "*") || alltrue([for a in st.Action : contains(["ecr:GetAuthorizationToken", "ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"], a)])
    ])
    error_message = "The runtime boundary has Resource '*' only for ecr:GetAuthorizationToken and the four ssmmessages ECS Exec channel actions (replan W5a)."
  }
  assert {
    condition = alltrue([
      for st in concat(jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement, jsondecode(aws_iam_policy.main_boundary_emr[0].policy).Statement) :
      !anytrue([for a in st.Action : startswith(a, "iam:") && a != "iam:PassRole"])
    ])
    error_message = "A boundary never allows IAM actions except the EMR service role's PassRole of the instance role."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.main_boundary_emr[0].policy).Statement :
      st.Action == ["iam:PassRole"] && st.Resource == ["arn:aws:iam::111122223333:role/scholarchain-course-emr-ec2"] && st.Condition.StringEquals["iam:PassedToService"] == ["ec2.amazonaws.com"]
    ])
    error_message = "The EMR boundary lets the service role pass only the instance role, only to EC2."
  }
}

run "p14_outputs_name_both_boundaries" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  assert {
    condition     = output.main_permissions_boundary_arns.runtime == "arn:aws:iam::111122223333:policy/scholarchain-course-permissions-boundary" && output.main_permissions_boundary_arns.emr_service == "arn:aws:iam::111122223333:policy/scholarchain-course-emr-service-boundary"
    error_message = "The outputs must name the two boundary ARNs the main root's roles must carry."
  }
}

run "p14_the_emr_service_boundary_covers_every_action_of_the_example_service_policy" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  # environments/emr-service-policy.json.example is what the human reviews for emr_service_policy_json. Whatever the human
  # finally supplies must stay inside the ceiling the EMR service role carries, or the role could not launch a cluster. The
  # list below is the example's distinct action set (this root must not read files outside itself: tests/infra copies the
  # root); infra/terraform/tests/phase14a.tftest.hcl asserts that the example still has exactly this set.
  assert {
    condition = alltrue([
      for a in ["ec2:CreateNetworkInterface", "ec2:RunInstances", "ec2:CreateFleet", "ec2:DeleteNetworkInterface", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances", "ec2:CreateTags", "ec2:DeleteTags", "ec2:DescribeAccountAttributes", "ec2:DescribeCapacityReservations", "ec2:DescribeDhcpOptions", "ec2:DescribeImages", "ec2:DescribeInstances", "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeLaunchTemplates", "ec2:DescribeNetworkAcls", "ec2:DescribeNetworkInterfaces", "ec2:DescribePlacementGroups", "ec2:DescribeRouteTables", "ec2:DescribeSecurityGroups", "ec2:DescribeSubnets", "ec2:DescribeVolumes", "ec2:DescribeVolumeStatus", "ec2:DescribeVpcAttribute", "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcs", "ec2:CreateSecurityGroup", "ec2:AuthorizeSecurityGroupEgress", "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "iam:PassRole"] :
      contains(flatten([for st in jsondecode(aws_iam_policy.main_boundary_emr[0].policy).Statement : st.Action]), a)
    ])
    error_message = "Every action of the example EMR service policy must be inside the EMR service-role boundary."
  }
}

run "p14_the_emr_managed_policies_tag_may_be_applied_to_subnets_and_security_groups" {
  command = plan
  variables {
    enabled_permission_sets = ["phase14-main"]
  }

  # D2: the main root now tags the application subnets and the EMR security groups with this key at creation (and may retag them).
  assert {
    condition     = contains(var.main_tag_keys, "for-use-with-amazon-emr-managed-policies")
    error_message = "main_tag_keys must contain the EMR managed-policies key."
  }
  assert {
    condition = alltrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--network"].policy).Statement :
      !(st.Effect == "Allow" && contains(st.Action, "ec2:CreateTags")) || !can(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"]) || contains(st.Condition["ForAllValues:StringEquals"]["aws:TagKeys"], "for-use-with-amazon-emr-managed-policies")
    ])
    error_message = "Every ec2:CreateTags statement that restricts aws:TagKeys must allow the EMR managed-policies key."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--network"].policy).Statement :
      st.Effect == "Allow" && contains(st.Action, "ec2:CreateTags") && contains(st.Resource, "arn:aws:ec2:us-east-2:111122223333:subnet/*") && contains(st.Resource, "arn:aws:ec2:us-east-2:111122223333:security-group/*") && !can(st.Condition["ForAllValues:StringEquals"]) && contains(try(st.Condition.StringEquals["ec2:CreateAction"], []), "CreateSubnet") && contains(try(st.Condition.StringEquals["ec2:CreateAction"], []), "CreateSecurityGroup")
    ])
    error_message = "Tag-on-create for CreateSubnet and CreateSecurityGroup carries no tag-key restriction, so the extra tag is allowed."
  }
}
