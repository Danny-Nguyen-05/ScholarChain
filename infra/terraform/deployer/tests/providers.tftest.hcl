# Repair round 3 (Phase 14B): Anthropic API (synthesis) and Voyage AI (embeddings) are the primary providers, so the account-level IAM
# of the main root changes in three places. Hand-derived expectations; mock provider, no AWS call is possible.
#   1. phase14-main (keys-obs): the deployer may create, tag, update and delete exactly the two provider key containers
#      (secret names scholarchain-<env>/anthropic-api-key and scholarchain-<env>/voyage-api-key, prefix scholarchain-<env>/), and still
#      never read or write a secret value;
#   2. runtime permissions boundary: the Bedrock invoke statement exists only while a Bedrock provider is selected; the provider keys need
#      only secretsmanager:GetSecretValue, which the boundary already allows on Secrets Manager secrets (the inline policies name the ARNs);
#   3. operator-loader role: the Titan Text Embeddings V2 grant exists only with Bedrock embeddings.
# No role holds a Marketplace permission in any configuration.
mock_provider "aws" {
  override_during = plan
}

variables {
  account_id              = join("", ["1111", "2222", "3333"])
  operator_principal_arn  = "arn:aws:iam::${join("", ["1111", "2222", "3333"])}:user/example-operator"
  owner                   = "example-owner"
  enabled_permission_sets = ["phase14-main"]
  operator_roles_enabled  = true
  operator_run_prefix     = "run-20261115"
}

run "the_deployer_manages_exactly_the_two_provider_key_containers_by_name_prefix" {
  command = plan

  assert {
    condition = [for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : st if st.Sid == "SecretsManagerProviderKeyContainersCreateAndTag"] == [{
      Sid      = "SecretsManagerProviderKeyContainersCreateAndTag", Effect = "Allow", Action = ["secretsmanager:CreateSecret", "secretsmanager:TagResource"],
      Resource = ["arn:aws:secretsmanager:us-east-2:${var.account_id}:secret:scholarchain-course/*"],
      Condition = { StringEquals = {
        "aws:RequestedRegion" = "us-east-2", "aws:RequestTag/project" = "scholarchain", "aws:RequestTag/environment" = "course"
      } }
    }]
    error_message = "Create and tag: only secrets named scholarchain-course/..., only in us-east-2, only with the project and environment request tags."
  }
  assert {
    condition = [for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : st if st.Sid == "SecretsManagerProviderKeyContainersUpdateUntagDelete"] == [{
      Sid      = "SecretsManagerProviderKeyContainersUpdateUntagDelete", Effect = "Allow", Action = ["secretsmanager:UpdateSecret", "secretsmanager:UntagResource", "secretsmanager:DeleteSecret"],
      Resource = ["arn:aws:secretsmanager:us-east-2:${var.account_id}:secret:scholarchain-course/*"],
      Condition = { StringEquals = {
        "aws:RequestedRegion" = "us-east-2", "aws:ResourceTag/project" = "scholarchain", "aws:ResourceTag/environment" = "course"
      } }
    }]
    error_message = "Update, untag and delete: the same name prefix and region, and only secrets that already carry the project and environment tags."
  }
  assert {
    condition = toset(flatten([
      for k, p in aws_iam_policy.permission_set : [for st in jsondecode(p.policy).Statement : [for a in st.Action : a if startswith(a, "secretsmanager:") && st.Effect == "Allow"]]
    ])) == toset(["secretsmanager:DescribeSecret", "secretsmanager:GetResourcePolicy", "secretsmanager:CreateSecret", "secretsmanager:TagResource", "secretsmanager:UpdateSecret", "secretsmanager:UntagResource", "secretsmanager:DeleteSecret"])
    error_message = "The Allow actions on Secrets Manager across all deployer documents are exactly these seven: no PutSecretValue, GetSecretValue, PutResourcePolicy, RotateSecret, ReplicateSecretToRegions or ListSecrets."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_policy.permission_set : [
        for st in jsondecode(p.policy).Statement :
        !anytrue([for a in st.Action : contains(["secretsmanager:CreateSecret", "secretsmanager:TagResource", "secretsmanager:UpdateSecret", "secretsmanager:UntagResource", "secretsmanager:DeleteSecret"], a)]) || (st.Effect == "Allow" && length(st.Resource) == 1 && endswith(st.Resource[0], ":secret:scholarchain-course/*"))
      ]
    ]))
    error_message = "Every statement that creates, changes or deletes a secret is scoped to the scholarchain-course/ name prefix, never secret:*."
  }
  assert {
    condition = anytrue([
      for st in jsondecode(aws_iam_policy.permission_set["phase14-main--iam"].policy).Statement :
      st.Sid == "DenyReadingSecretValues" && st.Effect == "Deny" && toset(st.Action) == toset(["secretsmanager:GetSecretValue", "secretsmanager:BatchGetSecretValue"]) && st.Resource == ["*"]
    ])
    error_message = "The explicit Deny of secret value reads stays: the deployer role can never read a provider key."
  }
}

run "the_secret_prefix_follows_main_environment" {
  command = plan
  variables { main_environment = "alt" }

  assert {
    condition     = alltrue([for st in jsondecode(aws_iam_policy.permission_set["phase14-main--keys-obs"].policy).Statement : st.Resource == ["arn:aws:secretsmanager:us-east-2:${var.account_id}:secret:scholarchain-alt/*"] if startswith(st.Sid, "SecretsManagerProviderKeyContainers")])
    error_message = "The prefix is scholarchain-<main_environment>."
  }
}

run "primary_providers_leave_the_runtime_boundary_without_bedrock" {
  command = plan

  assert {
    condition     = !strcontains(aws_iam_policy.main_boundary_runtime[0].policy, "bedrock") && !strcontains(lower(aws_iam_policy.main_boundary_runtime[0].policy), "marketplace")
    error_message = "With anthropic and voyage selected the runtime boundary names no Bedrock action or ARN and no Marketplace action."
  }
  assert {
    condition     = anytrue([for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement : st.Sid == "InjectConfiguredSecrets" && st.Action == ["secretsmanager:GetSecretValue"]])
    error_message = "The boundary keeps the GetSecretValue ceiling the services' inline execution-role grants (the two provider ARN patterns and the human-created auth secrets) sit under."
  }
  assert {
    condition     = !strcontains(aws_iam_policy.main_boundary_emr[0].policy, "bedrock") && !strcontains(lower(aws_iam_policy.main_boundary_emr[0].policy), "marketplace")
    error_message = "The EMR service boundary never carried Bedrock or Marketplace."
  }
}

run "bedrock_for_synthesis_restores_the_boundary_statement" {
  command = plan
  variables { main_synthesis_provider = "bedrock" }

  assert {
    condition     = [for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement : st.Action if st.Sid == "BedrockInvokeRegionalFoundationModelsAndProfiles"] == [["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]] && !strcontains(lower(aws_iam_policy.main_boundary_runtime[0].policy), "marketplace")
    error_message = "A Bedrock provider restores exactly the existing Bedrock invoke statement; still no Marketplace permission."
  }
}

run "bedrock_for_embeddings_restores_the_boundary_statement_and_the_loader_titan_grant" {
  command = plan
  variables { main_embedding_provider = "bedrock" }

  assert {
    condition     = length([for st in jsondecode(aws_iam_policy.main_boundary_runtime[0].policy).Statement : st if st.Sid == "BedrockInvokeRegionalFoundationModelsAndProfiles"]) == 1
    error_message = "Bedrock embeddings restore the boundary statement."
  }
  assert {
    condition     = [for st in jsondecode(aws_iam_role_policy.operator["loader--data"].policy).Statement : st.Resource if st.Sid == "InvokeTitanTextEmbeddingsV2Only"] == [["arn:aws:bedrock:us-east-2::foundation-model/amazon.titan-embed-text-v2:0"]]
    error_message = "Bedrock embeddings restore the loader's Titan grant: exactly the in-region Titan V2 foundation-model ARN."
  }
}

run "primary_providers_leave_the_operator_roles_without_any_bedrock_or_marketplace_action" {
  command = plan

  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [for st in jsondecode(p.policy).Statement : [for a in st.Action : !startswith(a, "bedrock:") && !startswith(a, "aws-marketplace:") && !startswith(a, "bedrock-mantle:")]]
    ]))
    error_message = "With the primary providers none of the operator roles holds any Bedrock or Marketplace action."
  }
  assert {
    condition = alltrue(flatten([
      for k, p in aws_iam_role_policy.operator : [for st in jsondecode(p.policy).Statement : [for a in st.Action : !startswith(a, "secretsmanager:")]]
    ]))
    error_message = "No operator role touches Secrets Manager: the human enters the provider keys with their own identity."
  }
}

run "an_unknown_synthesis_provider_is_rejected" {
  command = plan
  variables { main_synthesis_provider = "openai" }
  expect_failures = [var.main_synthesis_provider]
}

run "an_unknown_embedding_provider_is_rejected" {
  command = plan
  variables { main_embedding_provider = "cohere" }
  expect_failures = [var.main_embedding_provider]
}
