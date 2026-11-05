variable "aws_account_id" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Supply the actual twelve-digit account ID."
  }
}
variable "aws_profile" { type = string }
variable "aws_region" { type = string }
variable "budget_name" {
  type = string
  validation {
    condition     = can(regex("^[A-Za-z0-9_-]{1,100}$", var.budget_name))
    error_message = "Use a unique, nonpersonal project budget name."
  }
}
variable "enable_budget" {
  type        = bool
  default     = false
  description = "Configuration switch only, never evidence of human approval to apply."
}
variable "budget_limit_usd" {
  type    = number
  default = 200
  validation {
    condition     = var.budget_limit_usd == 200
    error_message = "This work order has one shared USD 200 project ceiling before credits."
  }
}
variable "project_period_start_utc" {
  type        = string
  description = "AWS timestamp YYYY-MM-DD_HH:MM; include all project spending, not just the deployment window."
  validation {
    condition     = can(formatdate("YYYY", "${replace(var.project_period_start_utc, "_", "T")}:00Z"))
    error_message = "Use a valid UTC timestamp in YYYY-MM-DD_HH:MM form."
  }
}
variable "project_period_end_utc" {
  type        = string
  description = "Exclusive end YYYY-MM-DD_HH:MM UTC; must include retained evidence costs and remain monitored through final reconciliation."
  validation {
    condition     = can(formatdate("YYYY", "${replace(var.project_period_end_utc, "_", "T")}:00Z")) && try(timecmp("${replace(var.project_period_end_utc, "_", "T")}:00Z", "${replace(var.project_period_start_utc, "_", "T")}:00Z") > 0, false)
    error_message = "Supply a valid UTC project end after the project start."
  }
}
variable "budget_notification_emails" {
  type        = set(string)
  default     = []
  sensitive   = true
  description = "Private input through TF_VAR_budget_notification_emails or an ignored local tfvars; never a committed address."
  validation {
    condition     = length(var.budget_notification_emails) <= 10 && alltrue([for email in var.budget_notification_emails : can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", email))])
    error_message = "Supply at most ten valid private notification addresses."
  }
}

variable "resource_tags" {
  type = object({
    course      = string
    project     = string
    environment = string
    owner       = string
  })
  default = {
    course      = "CS441"
    project     = "scholarchain"
    environment = "course"
    owner       = "danny"
  }
  description = "Human-selected ownership tags; expiration_date is derived from the budget's required retention/reconciliation end. No email addresses."
  validation {
    condition     = alltrue([for value in values(var.resource_tags) : length(trimspace(value)) > 0 && length(value) <= 256 && !strcontains(value, "@")])
    error_message = "All four ownership tags are required, nonblank, at most 256 characters and must not contain email addresses."
  }
}
