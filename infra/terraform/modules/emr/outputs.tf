output "cluster_id" { value = try(aws_emr_cluster.pipeline[0].id, null) }
output "controls" {
  value = {
    enabled             = var.config.enabled
    cluster             = one(aws_emr_cluster.pipeline)
    scaling             = one(aws_emr_managed_scaling_policy.bounded)
    security            = one(aws_emr_security_configuration.encrypted)
    task_groups         = aws_emr_instance_group.task
    efs                 = one(aws_efs_file_system.staging)
    efs_access_point    = one(aws_efs_access_point.staging)
    efs_mount_target    = one(aws_efs_mount_target.staging)
    efs_security_group  = one(aws_security_group.efs)
    efs_ingress_rule    = one(aws_vpc_security_group_ingress_rule.efs_from_emr)
    efs_egress_rule     = one(aws_vpc_security_group_egress_rule.emr_to_efs)
    efs_backup          = one(aws_efs_backup_policy.staging)
    efs_policy          = try(one(aws_efs_file_system_policy.staging).policy, null)
    node_policy         = try(one(aws_iam_role_policy.node).policy, null)
    bootstrap_args      = local.bootstrap_args
    spark_defaults_text = local.spark_defaults_text
    caps                = local.caps
    node_paths          = var.node_paths
  }
}
