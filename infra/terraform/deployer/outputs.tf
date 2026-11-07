output "role_arn" {
  description = "ARN of the deployer role."
  value       = aws_iam_role.deployer.arn
}

output "role_name" {
  value = aws_iam_role.deployer.name
}

output "spike_permissions_boundary_arn" {
  description = "Pass this to the spike root as permissions_boundary_arn."
  value       = contains(var.enabled_permission_sets, "spike-emr") ? local.spike_boundary_arn : null
}

output "available_permission_sets" {
  value = sort(local.known_sets)
}

output "operator_caller_policy_json" {
  description = "Policy the human operator needs to assume the role. Nothing is attached by this root."
  value       = jsonencode(local.operator_caller_policy)
}

output "policy_names" {
  value = sort([for p in aws_iam_policy.permission_set : p.name])
}

output "main_permissions_boundary_arns" {
  description = "phase14-main: the runtime boundary and the EMR service-role boundary the main root's roles must carry (null when phase14-main is not enabled)."
  value = contains(var.enabled_permission_sets, "phase14-main") ? {
    runtime     = local.m_boundary_runtime_arn
    emr_service = local.m_boundary_emr_arn
  } : null
}
