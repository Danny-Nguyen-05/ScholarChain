output "log_group_names" { value = { for s, g in aws_cloudwatch_log_group.service : s => g.name } }
output "controls" { value = { log_groups = aws_cloudwatch_log_group.service, audit_log = aws_cloudwatch_log_group.neptune_audit, dashboard = try(aws_cloudwatch_dashboard.elasticity[0].dashboard_body, null), queue_alarm = aws_cloudwatch_metric_alarm.queue_age, latency_alarms = aws_cloudwatch_metric_alarm.latency, error_alarm = aws_cloudwatch_metric_alarm.api_errors } }
output "neptune_audit_log_group_name" { value = aws_cloudwatch_log_group.neptune_audit.name }
