variable "name_prefix" { type = string }
variable "aws_region" { type = string }
variable "aws_account_id" { type = string }
variable "deployment_trusted_principal_arn" { type = string }
variable "kms_deletion_window_days" { type = number }
variable "bucket_arns" { type = map(string) }
variable "table_arns" { type = map(string) }
variable "query_session_index_arn" { type = string }
variable "queue_arn" { type = string }
variable "dead_letter_queue_arn" { type = string }
variable "repository_arns" { type = map(string) }
variable "service_secret_arns" { type = map(set(string)) }
variable "tags" { type = map(string) }

variable "emr_output_prefixes" { type = map(set(string)) }
variable "enable_emr" { type = bool }
variable "emr_service_policy_json" { type = string }
variable "neptune_data_arn" { type = string }
variable "vector_index_arns" { type = map(string) }
variable "embedding_model_id" { type = string }
variable "synthesis_model_id" { type = string }

# Bedrock cross-region inference profiles (decision 14-3). All four are optional; with no profile the grant is the single
# in-region foundation-model ARN. Shapes are validated again in the root.
variable "embedding_inference_profile_id" {
  type    = string
  default = null
}
variable "embedding_inference_profile_regions" {
  type    = list(string)
  default = []
}
variable "synthesis_inference_profile_id" {
  type    = string
  default = null
}
variable "synthesis_inference_profile_regions" {
  type    = list(string)
  default = []
}

# Rag-bucket key prefixes the query-api and embedding-worker read (evidence index, runtime audit, embedding text, runtime artifacts): the s3:prefix scope
# of their s3:ListBucket grants.
variable "rag_prefixes" {
  type = list(string)
}

# Replan W5b: the Neptune tunnel task role (modules/identity/neptune_tunnel.tf). The root sets it only when neptune_tunnel_enabled and
# the runtime is deployed with an image revision.
variable "neptune_tunnel_role_enabled" {
  type        = bool
  default     = false
  nullable    = false
  description = "Create the tunnel task role and its inline policy (four ssmmessages channel actions, no data access)."
}
