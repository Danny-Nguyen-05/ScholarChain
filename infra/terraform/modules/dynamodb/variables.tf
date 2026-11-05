variable "name_prefix" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "query_session_gsi_name" { type = string }
variable "enable_query_session_ttl" { type = bool }
variable "tags" { type = map(string) }
