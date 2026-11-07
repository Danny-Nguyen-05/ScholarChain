variable "name_prefix" { type = string }
variable "kms_key_arn" { type = string }
variable "cleanup_mode" { type = bool }
variable "tags" { type = map(string) }
variable "enabled" { type = bool }
variable "composition_verified" { type = bool }
variable "image_revision" { type = string }
variable "aws_region" { type = string }
variable "vpc_id" { type = string }
variable "application_subnets" { type = list(string) }
variable "public_subnets" { type = list(string) }
variable "security_groups" { type = map(string) }
variable "task_roles" { type = map(string) }
variable "execution_roles" { type = map(string) }
variable "service_secret_bindings" { type = map(map(string)) }
variable "capacity" { type = map(object({ cpu = number, memory = number, min = number, max = number })) }
variable "cpu_target" { type = number }
variable "backlog_target" { type = number }
variable "service_port" { type = number }
variable "certificate_arn" { type = string }
variable "queue_name" { type = string }
variable "queue_url" { type = string }
variable "dlq_url" { type = string }
variable "table_names" { type = map(string) }
variable "neptune_endpoint" { type = string }
variable "vector_bucket" { type = string }
variable "log_groups" { type = map(string) }

# Task environment of the aws service mode (SCHOLARCHAIN_SERVICE_MODE=aws; contract: modules/services/README.md and AwsConfig.scala).
# Every value is supplied by the root from a resource output or a variable; nothing is compiled in here.
variable "rag_bucket" { type = string }
variable "graph_bucket" { type = string }
variable "embedding_model_id" { type = string }
variable "embedding_model_version" {
  type    = string
  default = null
}
variable "vector_dimension" { type = number }
variable "vector_metric" { type = string }
variable "query_session_index" { type = string }
variable "queue_visibility_seconds" { type = number }
variable "queue_wait_seconds" { type = number }
variable "semantic_index" { type = string }
variable "embedding_text_prefix" { type = string }
variable "evidence_index_prefix" { type = string }
variable "audit_prefix" { type = string }
variable "synthesis_model_id" {
  type    = string
  default = null
}
variable "synthesis_inference_profile_id" {
  type    = string
  default = null
}
