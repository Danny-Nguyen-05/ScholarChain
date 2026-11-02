mock_provider "aws" { override_during = plan }
variables {
  aws_account_id       = "111122223333"
  budget_name          = "synthetic-project-budget"
  deployment_role_name = "synthetic-billing-role"
}
run "budget_policy_is_exact_and_complete" {
  command = plan
  assert {
    condition = jsondecode(output.execution_policy_json) == {
      Version = "2012-10-17"
      Statement = [{
        Sid      = "ManageOnlyProjectBudget"
        Effect   = "Allow"
        Action   = ["budgets:ModifyBudget", "budgets:ViewBudget", "budgets:TagResource", "budgets:UntagResource", "budgets:ListTagsForResource"]
        Resource = ["arn:aws:budgets::111122223333:budget/synthetic-project-budget"]
      }]
    }
    error_message = "Allow only the five required Budgets IAM actions on the single project budget; no global console, IAM or paid-service grant."
  }
  assert {
    condition     = output.trust_policy_json == null && output.caller_policy_json == null
    error_message = "An unset operator must not produce an executable trust or caller grant."
  }
}
run "trust_and_caller_require_exact_distinct_mfa_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/offline-billing-operator" }
  assert {
    condition = jsondecode(output.trust_policy_json) == {
      Version = "2012-10-17"
      Statement = [{
        Sid       = "DistinctOperatorWithMFA"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::111122223333:user/offline-billing-operator" }
        Action    = ["sts:AssumeRole"]
        Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
      }]
    }
    error_message = "Trust must name only the distinct operator and fail closed without MFA."
  }
  assert {
    condition = jsondecode(output.caller_policy_json) == {
      Version = "2012-10-17"
      Statement = [{
        Sid       = "AssumeOnlyBillingRoleWithMFA"
        Effect    = "Allow"
        Action    = ["sts:AssumeRole"]
        Resource  = ["arn:aws:iam::111122223333:role/synthetic-billing-role"]
        Condition = { Bool = { "aws:MultiFactorAuthPresent" = "true" } }
      }]
    }
    error_message = "The proposed caller grant must reach only the billing role and require MFA."
  }
}
run "different_budget_is_bound_independently" {
  command = plan
  variables { budget_name = "other-synthetic-budget" }
  assert {
    condition     = jsondecode(output.execution_policy_json).Statement[0].Resource == ["arn:aws:budgets::111122223333:budget/other-synthetic-budget"]
    error_message = "Changing the budget input must change its exact permission boundary."
  }
}
run "planner_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/scholarchain-planner" }
  expect_failures = [var.operator_user_arn]
}
run "root_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:root" }
  expect_failures = [var.operator_user_arn]
}
run "foreign_account_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::444455556666:user/offline-billing-operator" }
  expect_failures = [var.operator_user_arn]
}
run "wildcard_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/*" }
  expect_failures = [var.operator_user_arn]
}
run "wildcard_cannot_be_budget" {
  command = plan
  variables { budget_name = "*" }
  expect_failures = [var.budget_name]
}
run "role_cannot_replace_user_mfa_contract" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:role/offline-billing-operator" }
  expect_failures = [var.operator_user_arn]
}
run "invalid_account_is_rejected" {
  command = plan
  variables { aws_account_id = "*" }
  expect_failures = [var.aws_account_id]
}
run "planner_under_path_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/team/scholarchain-planner" }
  expect_failures = [var.operator_user_arn]
}

run "login_policy_is_exact_same_device_only" {
  command = plan
  assert {
    condition = jsondecode(output.login_policy_json) == {
      Version = "2012-10-17"
      Statement = [{
        Sid      = "BillingRoleSameDeviceLogin"
        Effect   = "Allow"
        Action   = ["signin:AuthorizeOAuth2Access", "signin:CreateOAuth2Token"]
        Resource = ["arn:aws:signin:us-east-2:111122223333:oauth2/public-client/localhost"]
        Condition = {
          StringEquals = {
            "signin:OAuthClientId" = "arn:aws:signin:::devtools/same-device"
          }
        }
      }]
    }
    error_message = "Allow exactly the two login actions on one account/region localhost resource, pinned to the same-device client ID."
  }
}
run "login_region_changes_only_authentication_binding" {
  command = plan
  variables { aws_region = "eu-west-1" }
  assert {
    condition     = jsondecode(output.login_policy_json).Statement[0].Resource == ["arn:aws:signin:eu-west-1:111122223333:oauth2/public-client/localhost"]
    error_message = "Authentication region must bind the login resource exactly."
  }
  assert {
    condition = jsondecode(output.execution_policy_json) == {
      Version = "2012-10-17"
      Statement = [{
        Sid      = "ManageOnlyProjectBudget"
        Effect   = "Allow"
        Action   = ["budgets:ModifyBudget", "budgets:ViewBudget", "budgets:TagResource", "budgets:UntagResource", "budgets:ListTagsForResource"]
        Resource = ["arn:aws:budgets::111122223333:budget/synthetic-project-budget"]
      }]
    }
    error_message = "A login-region change must not broaden or merge the existing budget statement."
  }
}
run "login_account_changes_independently" {
  command = plan
  variables { aws_account_id = "444455556666" }
  assert {
    condition     = jsondecode(output.login_policy_json).Statement[0].Resource == ["arn:aws:signin:us-east-2:444455556666:oauth2/public-client/localhost"]
    error_message = "The configured account, not a constant or wildcard, must bind login access."
  }
}
run "mixed_case_planner_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/ScHoLaRcHaIn-PlAnNeR" }
  expect_failures = [var.operator_user_arn]
}
run "mixed_case_planner_under_path_cannot_be_operator" {
  command = plan
  variables { operator_user_arn = "arn:aws:iam::111122223333:user/team/SCHOLARCHAIN-PLANNER" }
  expect_failures = [var.operator_user_arn]
}
run "wildcard_region_is_rejected" {
  command = plan
  variables { aws_region = "us-*-2" }
  expect_failures = [var.aws_region]
}
run "question_mark_region_is_rejected" {
  command = plan
  variables { aws_region = "us-east-?" }
  expect_failures = [var.aws_region]
}
run "malformed_region_is_rejected" {
  command = plan
  variables { aws_region = "us-east-2:console" }
  expect_failures = [var.aws_region]
}
