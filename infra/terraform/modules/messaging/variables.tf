variable "name_prefix" { type = string }
variable "aws_account_id" { type = string }
variable "kms_key_arn" { type = string }
variable "visibility_timeout_seconds" {
  type = number
  validation {
    condition     = var.visibility_timeout_seconds >= 1 && var.visibility_timeout_seconds <= 43200
    error_message = "SQS visibility timeout must be 1-43200 seconds."
  }
}
variable "max_receive_count" {
  type = number
  validation {
    condition     = var.max_receive_count >= 1 && var.max_receive_count <= 10 && floor(var.max_receive_count) == var.max_receive_count
    error_message = "Bound redrive attempts to 1-10 whole deliveries."
  }
}
variable "message_retention_seconds" {
  type = number
  validation {
    condition     = var.message_retention_seconds >= 60 && var.message_retention_seconds < var.dlq_retention_seconds
    error_message = "Source retention must be 60 seconds to less than the configured DLQ retention."
  }
}
variable "tags" { type = map(string) }
variable "dlq_retention_seconds" { type = number }
variable "long_poll_seconds" { type = number }
