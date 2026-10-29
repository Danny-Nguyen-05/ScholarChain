output "data_arn" { value = local.active ? "arn:aws:neptune-db:${var.aws_region}:${var.aws_account_id}:${aws_neptune_cluster.data[0].cluster_resource_id}/*" : null }
output "endpoint" { value = local.active ? "https://${aws_neptune_cluster.data[0].reader_endpoint}:${var.port}" : null }
output "cluster_identifier" { value = local.active ? aws_neptune_cluster.data[0].cluster_identifier : null }
output "controls" { value = {
  enabled  = local.active
  cluster  = one(aws_neptune_cluster.data)
  instance = one(aws_neptune_cluster_instance.writer)
} }
