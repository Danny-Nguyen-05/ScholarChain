# Mock-only tests: no AWS call is possible. Run with `terraform test` in this root.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id             = "111122223333"
  operator_principal_arn = "arn:aws:iam::111122223333:user/example-operator"
  owner                  = "example-owner"
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
    condition     = toset(output.available_permission_sets) == toset(["spike-emr"]) && output.role_name == "scholarchain-deployer"
    error_message = "Only spike-emr is implemented."
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

