# Phase 15 P9 (docs/runbooks/session-2-plan.md rows F5 and P9): the elasticity dashboard holds only free native AWS metrics and at most
# 50 metrics in every combination of its optional sources (CloudWatch free tier: 3 dashboards of up to 50 metrics each). Counts:
# base 23 (6 ECS + 3 SQS + 2 Step Functions + 12 DynamoDB throttle), + 9 with the ALB, + 5 with Neptune, + 6 with EMR = 43 at most.
# Dropped from the Phase 12-14 dashboard (109 base metrics), with the reason:
#  - 12 ECS/ContainerInsights task counts: Container Insights is off on the course-cap plan, so they have no data (and are billed custom
#    metrics when it is on); the query-api task count is read from the ALB HealthyHostCount instead;
#  - 2 AWS/ECS utilization series of embedding-worker: not an HTTP service, and it is fixed at one task in the elasticity run;
#  - 12 custom-namespace application series (latency, requests/errors, LLM tokens/cost): no publisher exists, so they never had data;
#    the latency and error-percent alarms that read them are kept;
#  - 12 DynamoDB ConsumedRead/WriteCapacityUnits: the tables are on-demand, so consumption is a cost signal, not a scaling limit; the
#    throttle events (kept) are the capacity-limit signal;
#  - 6 DynamoDB ConditionalCheckFailedRequests and 42 per-operation SuccessfulRequestLatency series (Phase 12C N12): correctness and
#    per-operation latency of the adapters, not elasticity; they stay readable in the CloudWatch metrics console without a dashboard.
locals {
  services              = toset(["query-api", "graph-service", "semantic-service", "embedding-worker"])
  http_services         = ["query-api", "graph-service", "semantic-service"]
  utilization_metrics   = concat([for service in local.http_services : [for metric in ["CPUUtilization", "MemoryUtilization"] : ["AWS/ECS", metric, "ClusterName", var.name_prefix, "ServiceName", service]]]...)
  throttle_metrics      = concat([for name in values(var.table_names) : [for metric in ["ReadThrottleEvents", "WriteThrottleEvents"] : ["AWS/DynamoDB", metric, "TableName", name]]]...)
  neptune_error_metrics = var.neptune_identifier == null ? [] : [for metric in ["TotalClientErrorsPerSec", "TotalServerErrorsPerSec"] : ["AWS/Neptune", metric, "DBClusterIdentifier", var.neptune_identifier]]
  neptune_metrics       = var.neptune_identifier == null ? [] : [for metric in ["CPUUtilization", "ServerlessDatabaseCapacity", "NCUUtilization"] : ["AWS/Neptune", metric, "DBClusterIdentifier", var.neptune_identifier]]
  emr_metrics           = var.emr_cluster_id == null ? [] : [for metric in ["CoreNodesRunning", "TaskNodesRunning", "CoreNodesPending", "TaskNodesPending", "TotalNodesRequested", "TotalNodesRunning"] : ["AWS/ElasticMapReduce", metric, "JobFlowId", var.emr_cluster_id]]
  # ALB dimension values, null-safe so the widget list below can always be evaluated; the dashboard includes those widgets only when
  # var.alb_metric_dimensions is non-null (the ALB exists).
  alb_lb = var.alb_metric_dimensions == null ? "" : var.alb_metric_dimensions.load_balancer
  alb_tg = var.alb_metric_dimensions == null ? "" : var.alb_metric_dimensions.target_group
  alb_widgets = [
    { type = "metric", x = 12, y = 3, width = 12, height = 6, properties = { title = "ALB healthy query-api targets", region = var.aws_region, period = 60, stat = "Minimum", metrics = [
      ["AWS/ApplicationELB", "HealthyHostCount", "LoadBalancer", local.alb_lb, "TargetGroup", local.alb_tg]
    ] } },
    { type = "metric", x = 0, y = 9, width = 12, height = 6, properties = { title = "ALB requests and 5XX (query-api)", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", local.alb_lb, "TargetGroup", local.alb_tg],
      ["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count", "LoadBalancer", local.alb_lb, "TargetGroup", local.alb_tg],
      ["AWS/ApplicationELB", "HTTPCode_ELB_5XX_Count", "LoadBalancer", local.alb_lb]
    ] } },
    { type = "metric", x = 12, y = 9, width = 12, height = 6, properties = { title = "ALB target response time p50/p95/p99 (seconds, query-api)", region = var.aws_region, period = 60, metrics = [for p in ["p50", "p95", "p99"] : ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", local.alb_lb, "TargetGroup", local.alb_tg, { stat = p }]] } },
    { type = "metric", x = 0, y = 15, width = 24, height = 6, properties = { title = "ALB requests per target and target 4XX (query-api)", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      ["AWS/ApplicationELB", "RequestCountPerTarget", "TargetGroup", local.alb_tg],
      ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", local.alb_lb, "TargetGroup", local.alb_tg]
    ] } }
  ]
}
resource "aws_cloudwatch_log_group" "service" {
  for_each          = local.services
  name              = "/${var.name_prefix}/${each.key}"
  retention_in_days = var.retention_days
  tags              = var.tags
}
resource "aws_cloudwatch_log_group" "neptune_audit" {
  name              = "/aws/neptune/${var.name_prefix}-graph/audit"
  retention_in_days = var.retention_days
  tags              = var.tags
}
resource "aws_cloudwatch_dashboard" "elasticity" {
  count          = var.dashboard_enabled ? 1 : 0
  dashboard_name = "${var.name_prefix}-elasticity"
  dashboard_body = jsonencode({ widgets = concat([
    { type = "text", x = 0, y = 0, width = 24, height = 3, properties = { markdown = "# ScholarChain elasticity\nFree native AWS metrics only, at most 50 (P9). ALB panels appear only while the runtime ALB exists; with Container Insights off, the query-api task count is the ALB HealthyHostCount. Custom-namespace application panels (publisher required) are not on this dashboard; their alarms remain and stay INSUFFICIENT_DATA until a publisher exists. Missing data is not zero errors. EMR native metrics have a 300-second cadence. No LLM dollar cost is inferred from tokens." } },
    { type = "metric", x = 0, y = 3, width = 12, height = 6, properties = { title = "ECS CPU and memory utilization (%), HTTP services", region = var.aws_region, period = 60, stat = "Average", metrics = local.utilization_metrics } },
    { type = "metric", x = 0, y = 21, width = 12, height = 6, properties = { title = "Embedding queue and DLQ depth", region = var.aws_region, period = 60, stat = "Maximum", metrics = [
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.queue_name],
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "${var.name_prefix}-embedding-dlq"]
    ] } },
    { type = "metric", x = 12, y = 21, width = 12, height = 6, properties = { title = "Oldest embedding message age (seconds)", region = var.aws_region, period = 60, stat = "Maximum", metrics = [["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", var.queue_name]] } },
    { type = "metric", x = 0, y = 27, width = 24, height = 6, properties = { title = "Step Functions failures/timeouts", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      ["AWS/States", "ExecutionsFailed", "StateMachineArn", var.workflow_arn],
      ["AWS/States", "ExecutionsTimedOut", "StateMachineArn", var.workflow_arn]
    ] } },
    { type = "metric", x = 0, y = 33, width = 24, height = 6, properties = { title = "DynamoDB table throttle events", region = var.aws_region, period = 60, stat = "Sum", metrics = local.throttle_metrics } }
    ],
    # Phase 15 P9 + P41: four ALB panels (9 metrics) for query-api, only while the ALB exists (the runtime is deployed). Dimensions and
    # statistics from the Elastic Load Balancing User Guide, "CloudWatch metrics for your Application Load Balancer" (read 2026-11-16):
    # HealthyHostCount needs LoadBalancer + TargetGroup (Minimum: healthy as seen by every load balancer node); RequestCount,
    # HTTPCode_Target_5XX_Count and TargetResponseTime take LoadBalancer + TargetGroup; HTTPCode_ELB_5XX_Count has no TargetGroup
    # dimension (LoadBalancer only); RequestCountPerTarget takes TargetGroup alone, and its only valid statistic is Sum, which AWS documents
    # as the per-target average; HTTPCode_Target_4XX_Count has no TargetGroup-only dimension set. The 4XX and request counts include the P40
    # rate limiter's 429 replies.
    # The four panels differ in shape, so a conditional cannot unify them with []; the filtered for-expression keeps them as a tuple.
    [for w in local.alb_widgets : w if var.alb_metric_dimensions != null],
    var.emr_cluster_id == null ? [] : [{ type = "metric", x = 0, y = 39, width = 12, height = 6, properties = { title = "EMR running/pending/requested nodes", region = var.aws_region, period = 300, stat = "Average", metrics = local.emr_metrics } }],
    var.neptune_identifier == null ? [] : [{ type = "metric", x = 12, y = 39, width = 12, height = 6, properties = { title = "Neptune capacity and utilization", region = var.aws_region, period = 60, stat = "Average", metrics = local.neptune_metrics } },
      { type = "metric", x = 0, y = 45, width = 24, height = 6, properties = { title = "Neptune client/server errors per second", region = var.aws_region, period = 60, stat = "Average", metrics = local.neptune_error_metrics } }
    ]
  ) })
}
resource "aws_cloudwatch_metric_alarm" "queue_age" {
  alarm_name          = "${var.name_prefix}-embedding-age"
  alarm_description   = "Embedding oldest-message age; human notification target is optional and unset by default"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  dimensions          = { QueueName = var.queue_name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.queue_age_seconds
  treat_missing_data  = "missing"
  alarm_actions       = var.notification_arns
  tags                = var.tags
}
resource "aws_cloudwatch_metric_alarm" "latency" {
  for_each            = toset(["query-api", "graph-service"])
  alarm_name          = "${var.name_prefix}-${each.key}-latency"
  alarm_description   = "REQUIRES future application metrics publisher; no current latency telemetry claim"
  namespace           = var.application_namespace
  metric_name         = "RequestLatencySeconds"
  dimensions          = { Service = each.key }
  extended_statistic  = "p95"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanThreshold"
  threshold           = var.latency_seconds
  treat_missing_data  = "missing"
  alarm_actions       = var.notification_arns
  tags                = var.tags
}
resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${var.name_prefix}-api-error-percent"
  alarm_description   = "REQUIRES future HttpRequests/HttpServerErrors publisher; missing data is not success"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  threshold           = var.api_error_percent
  treat_missing_data  = "missing"
  alarm_actions       = var.notification_arns
  metric_query {
    id          = "requests"
    return_data = false
    metric {
      namespace   = var.application_namespace
      metric_name = "HttpRequests"
      dimensions  = { Service = "query-api" }
      period      = 60
      stat        = "Sum"
    }
  }
  metric_query {
    id          = "errors"
    return_data = false
    metric {
      namespace   = var.application_namespace
      metric_name = "HttpServerErrors"
      dimensions  = { Service = "query-api" }
      period      = 60
      stat        = "Sum"
    }
  }
  metric_query {
    id          = "errorrate"
    expression  = "IF(requests > 0, 100 * errors / requests, 0)"
    label       = "HTTP5xx percentage"
    return_data = true
  }
  tags = var.tags
}
