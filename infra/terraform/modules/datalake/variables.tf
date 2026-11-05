variable "name_prefix" { type = string }
variable "aws_account_id" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "persistent_environment" { type = bool }
variable "intermediate_retention_days" { type = number }
variable "tags" { type = map(string) }
variable "multipart_abort_days" { type = number }
