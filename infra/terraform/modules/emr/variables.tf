variable "name_prefix" { type = string }
variable "config" { type = object({ enabled = bool, release_label = string, runtime_reference = string, runtime_verified = bool, bootstrap_uri = string, tls_certificate_uri = string, instance_type = string, max_task_nodes = number, idle_timeout_seconds = number }) }
variable "kms_key_arn" { type = string }
variable "log_bucket" { type = string }
variable "subnet_id" { type = string }
variable "security_group_id" { type = string }
variable "service_access_group_id" { type = string }
variable "instance_profile_arn" { type = string }
variable "service_role_arn" { type = string }
variable "tags" { type = map(string) }
