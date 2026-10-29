variable "name_prefix" { type = string }
variable "aws_account_id" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "dimension" { type = number }
variable "metric" { type = string }
variable "tags" { type = map(string) }
variable "non_filterable_metadata_keys" { type = set(string) }
