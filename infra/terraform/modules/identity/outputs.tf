output "kms_key_arn" { value = aws_kms_key.data.arn }
output "role_arns" {
  value = {
    tasks          = { for k, r in aws_iam_role.task : k => r.arn }
    execution      = { for k, r in aws_iam_role.execution : k => r.arn }
    neptune_loader = aws_iam_role.neptune_loader.arn
    emr_ec2        = aws_iam_role.emr_ec2.arn
    emr_service    = aws_iam_role.emr_service.arn
    emr_profile    = aws_iam_instance_profile.emr.arn
    deployment     = aws_iam_role.deployment.arn
  }
}
output "controls" {
  value = {
    task_policies      = { for k, p in aws_iam_role_policy.task : k => p.policy }
    execution_policies = { for k, p in aws_iam_role_policy.execution : k => p.policy }
    loader_policy      = aws_iam_role_policy.neptune_loader.policy
    emr_data_policy    = aws_iam_role_policy.emr_data.policy
    emr_control_policy = try(aws_iam_role_policy.emr_control[0].policy, null)
    kms_policy         = aws_kms_key.data.policy
    kms_rotation       = aws_kms_key.data.enable_key_rotation
    deployment_trust   = aws_iam_role.deployment.assume_role_policy
    task_trust         = { for k, r in aws_iam_role.task : k => r.assume_role_policy }
  }
}

# Concrete policy dependencies avoid starting an ECS/EMR workload with trust-only roles.
output "runtime_ready_roles" {
  value      = { tasks = { for k, r in aws_iam_role.task : k => r.arn }, execution = { for k, r in aws_iam_role.execution : k => r.arn } }
  depends_on = [aws_iam_role_policy.task, aws_iam_role_policy.execution]
}
output "emr_ready_service_arn" {
  value      = aws_iam_role.emr_service.arn
  depends_on = [aws_iam_role_policy.emr_control]
}
output "emr_ready_profile_arn" {
  value      = aws_iam_instance_profile.emr.arn
  depends_on = [aws_iam_role_policy.emr_data, aws_iam_role_policy.emr_disk_encryption]
}
