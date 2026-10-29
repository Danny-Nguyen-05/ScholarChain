output "cluster_id" { value = try(aws_emr_cluster.pipeline[0].id, null) }
output "controls" { value = { enabled = var.config.enabled, cluster = one(aws_emr_cluster.pipeline), scaling = one(aws_emr_managed_scaling_policy.bounded), security = one(aws_emr_security_configuration.encrypted), task_groups = aws_emr_instance_group.task } }
