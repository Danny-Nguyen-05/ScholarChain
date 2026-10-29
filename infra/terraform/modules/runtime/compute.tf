locals {
  active_services = var.enabled && var.image_revision != null ? local.services : toset([])
  http_services   = var.enabled && var.image_revision != null ? setsubtract(local.services, toset(["embedding-worker"])) : toset([])
  namespace       = "${var.name_prefix}.internal"
}
resource "aws_ecs_cluster" "course" {
  name = var.name_prefix
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = var.tags
}
resource "aws_service_discovery_private_dns_namespace" "course" {
  name = local.namespace
  vpc  = var.vpc_id
  tags = var.tags
}
resource "aws_service_discovery_service" "http" {
  for_each = local.http_services
  name     = each.key
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.course.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {}
  tags = var.tags
}
resource "aws_ecs_task_definition" "service" {
  for_each                 = local.active_services
  family                   = "${var.name_prefix}-${each.key}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = tostring(var.capacity[each.key].cpu)
  memory                   = tostring(var.capacity[each.key].memory)
  task_role_arn            = var.task_roles[each.key]
  execution_role_arn       = var.execution_roles[each.key]
  volume { name = "temporary" }
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name                   = each.key
    image                  = "${aws_ecr_repository.service[each.key].repository_url}:${var.image_revision}"
    essential              = true
    readonlyRootFilesystem = true
    mountPoints            = [{ sourceVolume = "temporary", containerPath = "/tmp", readOnly = false }]
    # Current entrypoints support unconfigured/offline-synthetic only. Even an
    # activation acknowledgment does not silently opt into fake or invented live mode.
    environment = concat([
      { name = "SCHOLARCHAIN_HTTP_HOST", value = "0.0.0.0" },
      { name = "SCHOLARCHAIN_HTTP_PORT", value = tostring(var.service_port) },
      { name = "SCHOLARCHAIN_SERVICE_MODE", value = "unconfigured" },
      { name = "AWS_REGION", value = var.aws_region }
      ], each.key == "query-api" ? [
      { name = "SCHOLARCHAIN_GRAPH_BASE_URI", value = "http://graph-service.${local.namespace}:${var.service_port}" },
      { name = "SCHOLARCHAIN_SEMANTIC_BASE_URI", value = "http://semantic-service.${local.namespace}:${var.service_port}" }
    ] : [])
    # Infrastructure endpoints/names below are deployment outputs, not invented
    # application environment names; Phase13/14 owns the live SDK composition contract.
    secrets      = [for name, arn in lookup(var.service_secret_bindings, each.key, {}) : { name = name, valueFrom = arn }]
    portMappings = [{ containerPort = var.service_port, hostPort = var.service_port, protocol = "tcp" }]
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group = var.log_groups[each.key], awslogs-region = var.aws_region, awslogs-stream-prefix = "service"
    } }
  }])
  tags = var.tags
}
resource "aws_lb" "query" {
  count                      = var.enabled && var.image_revision != null ? 1 : 0
  name                       = "${var.name_prefix}-query"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [var.security_groups.alb]
  subnets                    = var.public_subnets
  enable_deletion_protection = !var.cleanup_mode
  drop_invalid_header_fields = true
  # ALB access logging deliberately OFF. The existing logs bucket uses SSE-KMS,
  # which ALB/S3 server access log destinations do not support.
  tags = var.tags
}
resource "aws_lb_target_group" "query" {
  count       = var.enabled && var.image_revision != null ? 1 : 0
  name        = "${var.name_prefix}-query"
  port        = var.service_port
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check {
    path    = "/readyz"
    matcher = "200"
  }
  tags = var.tags
}
resource "aws_lb_listener" "https" {
  count             = var.enabled && var.image_revision != null && var.certificate_arn != null ? 1 : 0
  load_balancer_arn = aws_lb.query[0].arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.query[0].arn
  }
  tags = var.tags
}
resource "aws_ecs_service" "service" {
  for_each                = local.active_services
  name                    = each.key
  cluster                 = aws_ecs_cluster.course.id
  task_definition         = aws_ecs_task_definition.service[each.key].arn
  desired_count           = var.capacity[each.key].min
  launch_type             = "FARGATE"
  platform_version        = "1.4.0"
  enable_execute_command  = false
  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    assign_public_ip = false
    subnets          = var.application_subnets
    security_groups  = [var.security_groups[each.key]]
  }
  dynamic "service_registries" {
    for_each = each.key == "embedding-worker" ? [] : [each.key]
    content { registry_arn = aws_service_discovery_service.http[each.key].arn }
  }
  dynamic "load_balancer" {
    for_each = each.key == "query-api" && var.certificate_arn != null ? [each.key] : []
    content {
      target_group_arn = aws_lb_target_group.query[0].arn
      container_name   = each.key
      container_port   = var.service_port
    }
  }
  tags = var.tags
  lifecycle { ignore_changes = [desired_count] }
  depends_on = [aws_lb_listener.https]
}
resource "aws_appautoscaling_target" "service" {
  for_each           = local.active_services
  max_capacity       = var.capacity[each.key].max
  min_capacity       = var.capacity[each.key].min
  resource_id        = "service/${aws_ecs_cluster.course.name}/${aws_ecs_service.service[each.key].name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  tags               = var.tags
}
resource "aws_appautoscaling_policy" "http_cpu" {
  for_each           = local.http_services
  name               = "${var.name_prefix}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.service[each.key].scalable_dimension
  service_namespace  = "ecs"
  target_tracking_scaling_policy_configuration {
    target_value       = var.cpu_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification { predefined_metric_type = "ECSServiceAverageCPUUtilization" }
  }
}
resource "aws_appautoscaling_policy" "worker_backlog" {
  count              = var.enabled && var.image_revision != null ? 1 : 0
  name               = "${var.name_prefix}-embedding-backlog"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service["embedding-worker"].resource_id
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
  target_tracking_scaling_policy_configuration {
    target_value       = var.backlog_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    customized_metric_specification {
      metrics {
        id          = "queue"
        return_data = false
        metric_stat {
          stat = "Average"
          metric {
            metric_name = "ApproximateNumberOfMessagesVisible"
            namespace   = "AWS/SQS"
            dimensions {
              name  = "QueueName"
              value = var.queue_name
            }
          }
        }
      }
      metrics {
        id          = "tasks"
        return_data = false
        metric_stat {
          stat = "Average"
          metric {
            metric_name = "RunningTaskCount"
            namespace   = "ECS/ContainerInsights"
            dimensions {
              name  = "ClusterName"
              value = aws_ecs_cluster.course.name
            }
            dimensions {
              name  = "ServiceName"
              value = "embedding-worker"
            }
          }
        }
      }
      metrics {
        id          = "backlog"
        expression  = "queue / IF(tasks > 0, tasks, 1)"
        label       = "Visible embedding messages per running task"
        return_data = true
      }
    }
  }
}
