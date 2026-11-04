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
