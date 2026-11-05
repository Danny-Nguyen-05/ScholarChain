locals {
  services              = toset(["query-api", "graph-service", "semantic-service", "embedding-worker"])
  task_metrics          = concat([for service in local.services : [for metric in ["DesiredTaskCount", "RunningTaskCount", "PendingTaskCount"] : ["ECS/ContainerInsights", metric, "ClusterName", var.name_prefix, "ServiceName", service]]]...)
  utilization_metrics   = concat([for service in local.services : [for metric in ["CPUUtilization", "MemoryUtilization"] : ["AWS/ECS", metric, "ClusterName", var.name_prefix, "ServiceName", service]]]...)
  table_metrics         = concat([for name in values(var.table_names) : [for metric in ["ConsumedReadCapacityUnits", "ConsumedWriteCapacityUnits", "ReadThrottleEvents", "WriteThrottleEvents"] : ["AWS/DynamoDB", metric, "TableName", name]]]...)
  conditional_metrics   = [for name in values(var.table_names) : ["AWS/DynamoDB", "ConditionalCheckFailedRequests", "TableName", name]]
  latency_metrics       = concat([for name in values(var.table_names) : [for operation in ["GetItem", "PutItem", "UpdateItem", "DeleteItem", "Query", "BatchGetItem", "BatchWriteItem"] : ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", name, "Operation", operation]]]...)
  neptune_error_metrics = var.neptune_identifier == null ? [] : [for metric in ["TotalClientErrorsPerSec", "TotalServerErrorsPerSec"] : ["AWS/Neptune", metric, "DBClusterIdentifier", var.neptune_identifier]]
  neptune_metrics       = var.neptune_identifier == null ? [] : [for metric in ["CPUUtilization", "ServerlessDatabaseCapacity", "NCUUtilization"] : ["AWS/Neptune", metric, "DBClusterIdentifier", var.neptune_identifier]]
  emr_metrics           = var.emr_cluster_id == null ? [] : [for metric in ["CoreNodesRunning", "TaskNodesRunning", "CoreNodesPending", "TaskNodesPending", "TotalNodesRequested", "TotalNodesRunning"] : ["AWS/ElasticMapReduce", metric, "JobFlowId", var.emr_cluster_id]]
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
  dashboard_name = "${var.name_prefix}-elasticity"
  dashboard_body = jsonencode({ widgets = concat([
    { type = "text", x = 0, y = 0, width = 24, height = 3, properties = { markdown = "# ScholarChain elasticity\nNative metrics appear after activation. Custom panels and alarms require a verified Phase13/14 publisher; missing data is not zero errors. EMR native metrics have300-second cadence. No LLM dollar cost is inferred from tokens. The custom publisher contract is documented in README.md." } },
    { type = "metric", x = 0, y = 3, width = 12, height = 6, properties = { title = "ECS desired/running/pending tasks", region = var.aws_region, period = 60, stat = "Average", metrics = local.task_metrics } },
    { type = "metric", x = 12, y = 3, width = 12, height = 6, properties = { title = "ECS CPU and memory utilization (%)", region = var.aws_region, period = 60, stat = "Average", metrics = local.utilization_metrics } },
    { type = "metric", x = 0, y = 9, width = 12, height = 6, properties = { title = "Embedding queue and DLQ depth", region = var.aws_region, period = 60, stat = "Maximum", metrics = [
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.queue_name],
      ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", "${var.name_prefix}-embedding-dlq"]
    ] } },
    { type = "metric", x = 12, y = 9, width = 12, height = 6, properties = { title = "Oldest embedding message age (seconds)", region = var.aws_region, period = 60, stat = "Maximum", metrics = [["AWS/SQS", "ApproximateAgeOfOldestMessage", "QueueName", var.queue_name]] } },
    { type = "metric", x = 0, y = 21, width = 24, height = 6, properties = { title = "DynamoDB capacity units and table throttle events", region = var.aws_region, period = 60, stat = "Sum", metrics = local.table_metrics } },
    { type = "metric", x = 0, y = 27, width = 12, height = 6, properties = { title = "API p50/p95/p99 latency (publisher required)", region = var.aws_region, period = 60, metrics = [for p in ["p50", "p95", "p99"] : [var.application_namespace, "RequestLatencySeconds", "Service", "query-api", { stat = p }]] } },
    { type = "metric", x = 12, y = 27, width = 12, height = 6, properties = { title = "Graph/vector/LLM p95 latency (publisher required)", region = var.aws_region, period = 60, metrics = [
      [var.application_namespace, "RequestLatencySeconds", "Service", "graph-service", { stat = "p95" }],
      [var.application_namespace, "VectorQueryLatencySeconds", "Service", "semantic-service", { stat = "p95" }],
      [var.application_namespace, "LlmLatencySeconds", "Service", "query-api", { stat = "p95" }]
    ] } },
    { type = "metric", x = 0, y = 33, width = 12, height = 6, properties = { title = "API requests/errors and vector errors (publisher required)", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      [var.application_namespace, "HttpRequests", "Service", "query-api"],
      [var.application_namespace, "HttpServerErrors", "Service", "query-api"],
      [var.application_namespace, "VectorClientErrors", "Service", "semantic-service"]
    ] } },
    { type = "metric", x = 12, y = 33, width = 12, height = 6, properties = { title = "LLM tokens and explicitly published USD cost (publisher required)", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      [var.application_namespace, "LlmInputTokens", "Service", "query-api"],
      [var.application_namespace, "LlmOutputTokens", "Service", "query-api"],
      [var.application_namespace, "LlmEstimatedCostUsd", "Service", "query-api", { yAxis = "right" }]
    ] } },
    { type = "metric", x = 0, y = 39, width = 24, height = 6, properties = { title = "Step Functions failures/timeouts", region = var.aws_region, period = 60, stat = "Sum", metrics = [
      ["AWS/States", "ExecutionsFailed", "StateMachineArn", var.workflow_arn],
      ["AWS/States", "ExecutionsTimedOut", "StateMachineArn", var.workflow_arn]
    ] } }
    ],
    var.emr_cluster_id == null ? [] : [{ type = "metric", x = 0, y = 15, width = 12, height = 6, properties = { title = "EMR running/pending/requested nodes", region = var.aws_region, period = 300, stat = "Average", metrics = local.emr_metrics } }],
    var.neptune_identifier == null ? [] : [{ type = "metric", x = 12, y = 15, width = 12, height = 6, properties = { title = "Neptune capacity and utilization", region = var.aws_region, period = 60, stat = "Average", metrics = local.neptune_metrics } },
      { type = "metric", x = 0, y = 57, width = 24, height = 6, properties = { title = "Neptune client/server errors per second", region = var.aws_region, period = 60, stat = "Average", metrics = local.neptune_error_metrics } }
    ],
    [
      { type = "metric", x = 0, y = 45, width = 24, height = 6, properties = { title = "DynamoDB conditional write failures", region = var.aws_region, period = 60, stat = "Sum", metrics = local.conditional_metrics } },
      { type = "metric", x = 0, y = 51, width = 24, height = 6, properties = { title = "DynamoDB successful request latency (milliseconds)", region = var.aws_region, period = 60, stat = "Average", metrics = local.latency_metrics } }
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
