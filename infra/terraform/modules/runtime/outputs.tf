output "repository_arns" { value = { for k, v in aws_ecr_repository.service : k => v.arn } }
output "repository_urls" { value = { for k, v in aws_ecr_repository.service : k => v.repository_url } }
output "controls" {
  value = { for k, r in aws_ecr_repository.service : k => {
    immutable    = r.image_tag_mutability
    scan_on_push = one(r.image_scanning_configuration).scan_on_push
    encryption   = one(r.encryption_configuration).encryption_type
    force_delete = r.force_delete
  } }
}
output "cluster_name" { value = aws_ecs_cluster.course.name }
output "deployment_contract" { value = {
  table_names                 = var.table_names
  neptune_endpoint            = var.neptune_endpoint
  vector_bucket               = var.vector_bucket
  queue_url                   = var.queue_url
  dead_letter_queue_url       = var.dlq_url
  service_discovery_namespace = local.namespace
  live_composition_supported  = false
} }
output "compute_controls" { value = {
  enabled          = var.enabled
  cluster_settings = aws_ecs_cluster.course.setting
  task_definitions = aws_ecs_task_definition.service
  services         = aws_ecs_service.service
  scaling_targets  = aws_appautoscaling_target.service
  cpu_policies     = aws_appautoscaling_policy.http_cpu
  worker_policy    = one(aws_appautoscaling_policy.worker_backlog)
  listeners        = aws_lb_listener.https
  load_balancers   = aws_lb.query
} }
