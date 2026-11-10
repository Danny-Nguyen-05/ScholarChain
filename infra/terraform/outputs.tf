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

# ---- Replan W5b: what the human needs after base-apply and runtime-apply (no secret values) ----
# The DNS validation record(s) of the API certificate: add each as a Cloudflare CNAME, "DNS only" (not proxied), BEFORE runtime-apply.
# Empty while api_domain_name is unset. Values are known after the certificate exists (base-apply).
output "acm_validation_records" {
  value = local.acm_managed ? [for o in tolist(aws_acm_certificate.api[0].domain_validation_options) : {
    domain_name = o.domain_name
    name        = o.resource_record_name
    type        = o.resource_record_type
    value       = o.resource_record_value
  }] : []
}
output "acm_certificate_arn" { value = one(aws_acm_certificate.api[*].arn) }
# The ALB DNS name for the Cloudflare CNAME `api.<domain>` -> this value (DNS only). Null until the runtime is deployed.
output "alb_dns_name" { value = module.runtime.alb_dns_name }
# Neptune: the WRITER (cluster) endpoint hostname and port for the bulk loader and awsIntegration suite through the tunnel (SigV4 and
# TLS use this exact hostname), and the cluster resource id for the deployer's operator_neptune_cluster_resource_id. Null while
# Neptune is disabled. The existing reader endpoint stays in the runtime environment (module.neptune.endpoint).
output "neptune_writer_endpoint" { value = module.neptune.writer_endpoint }
output "neptune_port" { value = module.neptune.port }
output "neptune_cluster_resource_id" { value = module.neptune.cluster_resource_id }
# The one-off Neptune tunnel task (ecs:RunTask --enable-execute-command; no ECS service): everything the run-task command needs.
# Null unless neptune_tunnel_enabled and the runtime is deployed with an image revision.
output "neptune_tunnel" { value = module.runtime.neptune_tunnel }
# Offline assertions (selected attributes only: the certificate resource carries a sensitive private_key attribute that must never be
# copied into an output; no secret values here).
output "phase14b_controls" {
  value = {
    tunnel_role      = module.identity.neptune_tunnel_controls
    tunnel_task      = module.runtime.neptune_tunnel_controls
    certificates     = [for c in aws_acm_certificate.api : { domain_name = c.domain_name, validation_method = c.validation_method, key_algorithm = c.key_algorithm, tags = c.tags }]
    validations      = [for v in aws_acm_certificate_validation.api : { certificate_arn = v.certificate_arn, timeouts = v.timeouts }]
    https_enabled    = local.https_enabled
    listener_cert    = local.listener_cert_arn
    runtime_deployed = local.runtime_deployed
  }
}
