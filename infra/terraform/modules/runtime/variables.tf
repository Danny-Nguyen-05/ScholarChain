variable "name_prefix" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "tags" { type = map(string) }
