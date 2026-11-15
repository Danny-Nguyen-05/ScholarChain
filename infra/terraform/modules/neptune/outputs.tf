output "data_arn" { value = local.active ? "arn:aws:neptune-db:${var.aws_region}:${var.aws_account_id}:${aws_neptune_cluster.data[0].cluster_resource_id}/*" : null }
output "endpoint" { value = local.active ? "https://${aws_neptune_cluster.data[0].reader_endpoint}:${var.port}" : null }
output "cluster_identifier" { value = local.active ? aws_neptune_cluster.data[0].cluster_identifier : null }
# W5b: the WRITER (cluster) endpoint, hostname only, for the bulk loader and the Phase 7 awsIntegration suite through the tunnel (the
# reader `endpoint` above stays the runtime services' endpoint). SigV4 and TLS use this exact hostname.
output "writer_endpoint" { value = local.active ? aws_neptune_cluster.data[0].endpoint : null }
output "port" { value = local.active ? var.port : null }
# The id the operator roles' operator_neptune_cluster_resource_id takes (neptune-db ARN cluster-XXXX).
output "cluster_resource_id" { value = local.active ? aws_neptune_cluster.data[0].cluster_resource_id : null }
output "controls" { value = {
  enabled  = local.active
  cluster  = one(aws_neptune_cluster.data)
  instance = one(aws_neptune_cluster_instance.writer)
} }
