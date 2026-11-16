locals {
  active_services = var.enabled && var.image_revision != null ? local.services : toset([])
  http_services   = var.enabled && var.image_revision != null ? setsubtract(local.services, toset(["embedding-worker"])) : toset([])
  namespace       = "${var.name_prefix}.internal"

  # The aws service mode needs the human acknowledgment (runtime_composition_verified, a precondition of runtime_enabled in the root)
  # AND an enabled runtime. Otherwise the tasks keep SCHOLARCHAIN_SERVICE_MODE=unconfigured and receive none of the aws variables.
  aws_mode = var.enabled && var.composition_verified

  # The runtime-artifact pointer exists only when all three values are set (a partial pointer is refused by the root guard and by the services).
  runtime_artifact_pointer = var.runtime_artifact_key != null && var.runtime_artifact_sha256 != null && var.runtime_artifact_source_run_id != null

  # HTTPS (listener, query-api load balancing): the caller's plan-time boolean when given (an ACM certificate created in the same
  # apply has an ARN that is unknown at plan time), otherwise "a certificate ARN was supplied" (the earlier rule).
  https = var.https_enabled != null ? var.https_enabled : var.certificate_arn != null

  # The Neptune tunnel task definition exists only with a deployed runtime (image revision) and an explicit request.
  tunnel_seconds = 14400 # the task sleeps at most 4 h (the operator session maximum), then exits on its own

  # The one condition that attaches the query-api service to the ALB target group. The dynamic load_balancer block and
  # health_check_grace_period_seconds both read it, so they cannot diverge: ECS rejects a grace period on a service that has no
  # load balancer.
  load_balanced_service = local.https ? "query-api" : null

  # Synthesis: the inference-profile ID is the Converse modelId when one is configured; the foundation-model ID is its version tag.
  synthesis_model = var.synthesis_inference_profile_id != null ? var.synthesis_inference_profile_id : var.synthesis_model_id

  # Variables every aws role needs: the six tables and the QuerySession index (names from the root's table contract).
  aws_common_env = merge(
    { for t, suffix in {
      RunLedger      = "RUN_LEDGER", EntityLinkCache = "ENTITY_LINK_CACHE", QuerySession = "QUERY_SESSION",
      EvidenceBundle = "EVIDENCE_BUNDLE", ArtifactRegistry = "ARTIFACT_REGISTRY", ResearcherMetricCache = "RESEARCHER_METRIC_CACHE"
    } : "SCHOLARCHAIN_DYNAMODB_TABLE_${suffix}" => var.table_names[t] },
    { SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX = var.query_session_index }
  )
  aws_embedding_env = {
    SCHOLARCHAIN_EMBEDDING_PROVIDER      = var.embedding_provider
    SCHOLARCHAIN_MODELS_EMBEDDING_MODEL  = var.embedding_model_id
    SCHOLARCHAIN_EMBEDDING_MODEL_VERSION = var.embedding_model_version
    SCHOLARCHAIN_EMBEDDING_DIMENSION     = tostring(var.vector_dimension)
  }
  aws_vector_env = {
    SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET = var.vector_bucket
    SCHOLARCHAIN_SEMANTIC_INDEX           = var.semantic_index
    SCHOLARCHAIN_S3_VECTORS_METRIC        = var.vector_metric
  }
  # Per role, exactly the contract of modules/services/README.md "Environment contract". Secrets are NOT here: they are `secrets`
  # (ARN bindings). Optional variables with no Terraform source are left unset.
  aws_role_env = {
    "graph-service" = {
      SCHOLARCHAIN_NEPTUNE_ENDPOINT     = var.neptune_endpoint # module.neptune.endpoint is already "https://<reader endpoint>:<port>"
      SCHOLARCHAIN_STORAGE_GRAPH_BUCKET = var.graph_bucket
    }
    "semantic-service" = merge(local.aws_vector_env, local.aws_embedding_env, { SCHOLARCHAIN_STORAGE_RAG_BUCKET = var.rag_bucket })
    "query-api" = merge(local.aws_embedding_env, {
      SCHOLARCHAIN_STORAGE_RAG_BUCKET      = var.rag_bucket
      SCHOLARCHAIN_SYNTHESIS_PROVIDER      = var.synthesis_provider
      SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL  = local.synthesis_model
      SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION = var.synthesis_model_id
      SCHOLARCHAIN_EVIDENCE_INDEX_PREFIX   = var.evidence_index_prefix
      SCHOLARCHAIN_AUDIT_PREFIX            = var.audit_prefix
      }, local.runtime_artifact_pointer ? {
      # G3: all three or none (AwsConfig refuses a partial set). The optional bucket is set only when given (the root guard allows the rag bucket
      # only); null leaves the services default, which is the rag bucket.
      SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY           = var.runtime_artifact_key
      SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256        = var.runtime_artifact_sha256
      SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID = var.runtime_artifact_source_run_id
      } : {}, local.runtime_artifact_pointer && var.runtime_artifact_bucket != null ? {
      SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET = var.runtime_artifact_bucket
      } : {}, var.semantic_rate_limit_per_second != null ? {
      # Phase 15 P41: the P40 public-route rate-limit override (PublicSemanticRoute.scala RateLimitSettings). Each is set only when its
      # variable is non-null, independently; null leaves it unset so the service defaults (50 per second, burst 100) apply.
      SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND = tostring(var.semantic_rate_limit_per_second)
      } : {}, var.semantic_rate_limit_burst != null ? {
      SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST = tostring(var.semantic_rate_limit_burst)
    } : {})
    "embedding-worker" = merge(local.aws_vector_env, local.aws_embedding_env, {
      SCHOLARCHAIN_SQS_QUEUE_URL                     = var.queue_url
      SCHOLARCHAIN_SQS_DLQ_URL                       = var.dlq_url
      SCHOLARCHAIN_STORAGE_RAG_BUCKET                = var.rag_bucket
      SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX             = var.embedding_text_prefix
      SCHOLARCHAIN_WORKER_VISIBILITY_TIMEOUT_SECONDS = tostring(var.queue_visibility_seconds)
      SCHOLARCHAIN_WORKER_WAIT_SECONDS               = tostring(var.queue_wait_seconds)
    })
  }
}
resource "aws_ecs_cluster" "course" {
  name = var.name_prefix
  setting {
    name  = "containerInsights"
    value = var.container_insights_enabled ? "enabled" : "disabled"
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
    # SCHOLARCHAIN_SERVICE_MODE is "aws" only when the runtime is enabled AND the human acknowledged the composition
    # (runtime_composition_verified); otherwise "unconfigured" with none of the aws variables. The aws mode is implemented in
    # modules/services (AwsComposition); graph-service's Neptune reader wiring is implemented in modules/services and
    # modules/storage. Nothing here is live-verified.
    environment = concat([
      { name = "SCHOLARCHAIN_HTTP_HOST", value = "0.0.0.0" },
      { name = "SCHOLARCHAIN_HTTP_PORT", value = tostring(var.service_port) },
      { name = "SCHOLARCHAIN_SERVICE_MODE", value = local.aws_mode ? "aws" : "unconfigured" },
      { name = "AWS_REGION", value = var.aws_region }
      ], each.key == "query-api" ? [
      { name = "SCHOLARCHAIN_GRAPH_BASE_URI", value = "http://graph-service.${local.namespace}:${var.service_port}" },
      { name = "SCHOLARCHAIN_SEMANTIC_BASE_URI", value = "http://semantic-service.${local.namespace}:${var.service_port}" }
      ] : [],
      [for name in sort(keys(merge(local.aws_common_env, local.aws_role_env[each.key]))) : { name = name, value = merge(local.aws_common_env, local.aws_role_env[each.key])[name] } if local.aws_mode]
    )
    # Secrets stay ARN bindings (never in `environment`); the names are those the services read.
    # Repair round 3: the provider API key containers join `secrets` in the aws service mode only (ECS refuses to start a task whose
    # secret has no value yet). The names are SCHOLARCHAIN_ANTHROPIC_API_KEY (query-api) and SCHOLARCHAIN_VOYAGE_API_KEY
    # (semantic-service, embedding-worker); a key value is never in `environment`.
    secrets      = [for name, arn in merge(lookup(var.service_secret_bindings, each.key, {}), local.aws_mode ? lookup(var.provider_secret_bindings, each.key, {}) : {}) : { name = name, valueFrom = arn }]
    portMappings = [{ containerPort = var.service_port, hostPort = var.service_port, protocol = "tcp" }]
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group = var.log_groups[each.key], awslogs-region = var.aws_region, awslogs-stream-prefix = "service"
    } }
  }])
  tags = var.tags
}
# Replan W5b (user decision 1, naming contract: infra/terraform/deployer/README.md "Replan W5a"): family <prefix>-neptune-tunnel. A task
# DEFINITION only: no ECS service exists for it. The operator runs it as a one-off task (ecs:RunTask --enable-execute-command) in the
# application subnets with the graph-service security group (the only one Neptune admits), opens an ECS Exec port-forwarding session to
# the Neptune WRITER endpoint, and stops the task when the load is done. The container does nothing but sleep for a bounded time.
#  - image: the graph-service image at the immutable revision (already pushed; JRE image with `sleep`, nothing new to build or scan);
#  - execution role: the graph-service execution role (pulls that image, writes to the graph-service log group only);
#  - task role: modules/identity neptune-tunnel-task (the four ssmmessages channel actions, nothing else);
#  - readonlyRootFilesystem is FALSE on purpose: the SSM agent that ECS Exec injects must write its own directories, and AWS documents
#    that ECS Exec cannot work with a read-only root file system (https://repost.aws/knowledge-center/ecs-error-execute-command);
#  - initProcessEnabled = true: ECS Exec leaves child processes (the SSM agent sessions) that need an init process to be reaped.
resource "aws_ecs_task_definition" "neptune_tunnel" {
  count                    = var.enabled && var.image_revision != null && var.neptune_tunnel_enabled ? 1 : 0
  family                   = "${var.name_prefix}-neptune-tunnel"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = var.neptune_tunnel_task_role_arn
  execution_role_arn       = var.execution_roles["graph-service"]
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  container_definitions = jsonencode([{
    name                   = "neptune-tunnel"
    image                  = "${aws_ecr_repository.service["graph-service"].repository_url}:${var.image_revision}"
    essential              = true
    readonlyRootFilesystem = false
    entryPoint             = ["sleep"]
    command                = [tostring(local.tunnel_seconds)]
    linuxParameters        = { initProcessEnabled = true }
    logConfiguration = { logDriver = "awslogs", options = {
      awslogs-group = var.log_groups["graph-service"], awslogs-region = var.aws_region, awslogs-stream-prefix = "neptune-tunnel"
    } }
  }])
  tags = var.tags
  lifecycle {
    precondition {
      condition     = var.neptune_tunnel_task_role_arn != null
      error_message = "The Neptune tunnel task definition needs the tunnel task role (modules/identity, neptune_tunnel_role_enabled)."
    }
  }
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
    path                = "/readyz"
    matcher             = "200"
    interval            = var.health_check_interval_seconds
    timeout             = var.health_check_timeout_seconds
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
  }
  tags = var.tags
  lifecycle {
    precondition {
      condition     = var.health_check_timeout_seconds < var.health_check_interval_seconds
      error_message = "The ALB requires the health-check timeout to be smaller than the interval."
    }
  }
}
resource "aws_lb_listener" "https" {
  count             = var.enabled && var.image_revision != null && local.https ? 1 : 0
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
  # query-api's /readyz waits for graph-service and semantic-service, which start in the same apply. The grace period keeps ECS
  # and the ALB from counting those first failed checks against the task (and tripping the circuit breaker). A target marked
  # unhealthy needs healthy_threshold x interval more of passing checks, so the grace must cover that too (precondition below).
  # Set only on the load-balanced service; null (absent) elsewhere.
  health_check_grace_period_seconds = each.key == local.load_balanced_service ? var.health_check_grace_period_seconds : null
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
    for_each = each.key == local.load_balanced_service ? [each.key] : []
    content {
      target_group_arn = aws_lb_target_group.query[0].arn
      container_name   = each.key
      container_port   = var.service_port
    }
  }
  tags = var.tags
  lifecycle {
    ignore_changes = [desired_count]
    # A once-unhealthy target needs healthy_threshold x interval of passes to recover; a shorter grace can never cover that.
    precondition {
      condition     = each.key != local.load_balanced_service || var.health_check_grace_period_seconds >= var.health_check_healthy_threshold * var.health_check_interval_seconds
      error_message = "health_check_grace_period_seconds must be at least health_check_healthy_threshold x health_check_interval_seconds (the time a once-unhealthy query-api target needs to become healthy again)."
    }
  }
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
# Phase 15 P41 (session-2-plan.md F26/P41): a second target-tracking policy for query-api only, on the free predefined ALB metric
# RequestCountPerTarget (requests per healthy target per minute). It sits beside the CPU policy above, which is unchanged: with two
# target-tracking policies on one scalable target, Application Auto Scaling scales out when either asks and scales in only when both
# allow it (https://docs.aws.amazon.com/autoscaling/application/userguide/target-tracking-scaling-policy-overview.html, "Multiple
# scaling policies", read 2026-11-16). Scale-in is not disabled.
# Count: the same deployed-runtime condition as aws_lb.query and aws_lb_target_group.query (so the [0] indexes below always exist
# when this resource does) AND a non-null target. Index errors are impossible: with count 0 the [0] references are never evaluated.
# resource_label is "<alb arn_suffix>/<target group arn_suffix>", i.e. app/<name>/<id>/targetgroup/<name>/<id> (Application Auto Scaling
# PredefinedMetricSpecification.ResourceLabel). AWS accepts the label only when the target group is attached to the ECS service, which
# here happens only with HTTPS (local.load_balanced_service); the precondition refuses the plan instead of failing at apply.
resource "aws_appautoscaling_policy" "query_requests" {
  count              = var.enabled && var.image_revision != null && var.query_requests_per_target_target != null ? 1 : 0
  name               = "${var.name_prefix}-query-api-requests"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.service["query-api"].resource_id
  scalable_dimension = aws_appautoscaling_target.service["query-api"].scalable_dimension
  service_namespace  = "ecs"
  target_tracking_scaling_policy_configuration {
    target_value       = var.query_requests_per_target_target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    disable_scale_in   = false
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.query[0].arn_suffix}/${aws_lb_target_group.query[0].arn_suffix}"
    }
  }
  lifecycle {
    precondition {
      condition     = local.load_balanced_service == "query-api"
      error_message = "query_requests_per_target_target needs the query-api service attached to the ALB target group, which happens only with HTTPS (a listener certificate). Without it the ALBRequestCountPerTarget label is refused by AWS; set query_requests_per_target_target = null."
    }
  }
}
resource "aws_appautoscaling_policy" "worker_backlog" {
  # The backlog metric divides by ECS/ContainerInsights RunningTaskCount, which exists only with Container Insights.
  count              = var.enabled && var.image_revision != null && var.container_insights_enabled ? 1 : 0
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
