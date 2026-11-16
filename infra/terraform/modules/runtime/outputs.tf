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
  live_composition_supported  = local.aws_mode
} }
output "compute_controls" { value = {
  enabled          = var.enabled
  cluster_settings = aws_ecs_cluster.course.setting
  task_definitions = aws_ecs_task_definition.service
  services         = aws_ecs_service.service
  scaling_targets  = aws_appautoscaling_target.service
  cpu_policies     = aws_appautoscaling_policy.http_cpu
  worker_policy    = one(aws_appautoscaling_policy.worker_backlog)
  request_policy   = one(aws_appautoscaling_policy.query_requests)
  listeners        = aws_lb_listener.https
  load_balancers   = aws_lb.query
  target_groups    = aws_lb_target_group.query
} }
# Phase 15 P41: the ALB and target-group CloudWatch dimension values (the ARN suffixes) for the dashboard request panel. The object is null
# while no ALB exists; its null-ness depends only on the count (known at plan time), its values become known when the ALB is created.
output "alb_metric_dimensions" {
  value = length(aws_lb.query) == 1 ? { load_balancer = aws_lb.query[0].arn_suffix, target_group = aws_lb_target_group.query[0].arn_suffix } : null
}
# Replan W5b: the ALB DNS name the human points the Cloudflare CNAME `api.<domain>` at (DNS only). Null until the runtime is deployed.
output "alb_dns_name" { value = one(aws_lb.query[*].dns_name) }
# Replan W5b: everything `aws ecs run-task --enable-execute-command` needs for the one-off Neptune tunnel task; null when it is not
# registered. The security group is the graph-service group (the only one Neptune admits), the subnets are the application subnets.
output "neptune_tunnel" {
  value = length(aws_ecs_task_definition.neptune_tunnel) == 1 ? {
    cluster_name        = aws_ecs_cluster.course.name
    family              = aws_ecs_task_definition.neptune_tunnel[0].family
    task_definition_arn = aws_ecs_task_definition.neptune_tunnel[0].arn
    container_name      = "neptune-tunnel"
    subnet_ids          = var.application_subnets
    security_group_id   = var.security_groups["graph-service"]
  } : null
}
# Offline assertions only (the full resource, like compute_controls). There is deliberately no aws_ecs_service for the tunnel.
output "neptune_tunnel_controls" { value = aws_ecs_task_definition.neptune_tunnel }
