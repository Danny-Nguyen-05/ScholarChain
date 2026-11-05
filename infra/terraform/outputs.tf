output "required_tags" { value = module.foundation.tags }
output "bucket_names" { value = module.datalake.bucket_names }
output "table_names" { value = module.dynamodb.table_names }
output "queue_urls" { value = module.messaging.queue_urls }
output "repository_urls" { value = module.runtime.repository_urls }
output "role_arns" { value = module.identity.role_arns }
output "network_ids" { value = module.network.ids }
output "kms_key_arn" { value = module.identity.kms_key_arn }
# Public configuration controls used by offline feature assertions; no secret values.
output "data_controls" {
  value = {
    buckets = module.datalake.controls
    tables  = module.dynamodb.controls
    queues  = module.messaging.controls
    ecr     = module.runtime.controls
  }
}
output "network_controls" { value = module.network.controls }
output "iam_controls" { value = module.identity.controls }
output "budget_controls" { value = module.foundation.budget_controls }

output "phase12b_controls" { value = {
  neptune             = module.neptune.controls
  vectors             = module.s3vectors.controls
  emr                 = module.emr.controls
  runtime             = module.runtime.compute_controls
  workflow            = module.workflow.controls
  observability       = module.observability.controls
  deployment_contract = module.runtime.deployment_contract
} }
output "embedding_dispatch_arn" { value = module.workflow.arn }
