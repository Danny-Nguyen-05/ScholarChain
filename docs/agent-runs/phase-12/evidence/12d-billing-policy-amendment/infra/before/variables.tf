variable "aws_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the exact twelve-digit account ID."
  }
}
variable "budget_name" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,100}$", var.budget_name))
    error_message = "Supply one nonpersonal budget name with no wildcard or path."
  }
}
variable "deployment_role_name" {
  type    = string
  default = "scholarchain-billing-deployer"
  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,64}$", var.deployment_role_name)) && var.deployment_role_name != "scholarchain-planner"
    error_message = "Use a distinct, concrete billing role name."
  }
}
variable "operator_user_arn" {
  type        = string
  default     = null
  nullable    = true
  description = "Unset until the human identifies a separate same-account IAM user with MFA; never the root or read-only planner."
  validation {
    condition = var.operator_user_arn == null ? true : (
      can(regex("^arn:aws:iam::${var.aws_account_id}:user/[A-Za-z0-9+=,.@_/-]+$", var.operator_user_arn)) &&
      !endswith(var.operator_user_arn, "/scholarchain-planner")
    )
    error_message = "Require a concrete same-account IAM user ARN, excluding root, roles, wildcards and scholarchain-planner."
  }
}
