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

output "operator_role_arns" {
  description = "Replan W5a (+ G-DEPLOYER): ARNs of the loader, reader, cleanup and pipeline operator roles (null when operator_roles_enabled is false). The human assumes them with MFA for at most 4 hours."
  value       = var.operator_roles_enabled ? merge({ for k, r in aws_iam_role.operator : k => r.arn }, { pipeline = aws_iam_role.operator_pipeline[0].arn }) : null
}

output "operator_roles_caller_policy_json" {
  description = "Replan W5a-2: policy that lets the human IAM user call sts:AssumeRole (MFA) on exactly the four operator roles (null when disabled). Optional fallback; nothing is attached by this root."
  value       = var.operator_roles_enabled ? jsonencode(local.op_caller_policy) : null
}

output "operator_scope" {
  description = "Replan W5a: what the operator roles are scoped to (null when disabled). neptune_scope_is_fallback is true until operator_neptune_cluster_resource_id is set."
  value = var.operator_roles_enabled ? {
    run_prefix                 = local.op_run
    s3_object_arns             = local.op_object_arns
    dynamodb_tables            = local.op_tables
    neptune_resource           = local.op_neptune_arn
    neptune_scope_is_fallback  = var.operator_neptune_cluster_resource_id == null
    tunnel_task_definition     = local.op_tunnel_family
    tunnel_task_role           = local.op_tunnel_task_role
    tunnel_execution_role      = local.op_tunnel_exec_role
    max_session_duration_hours = 4
    # G4: runtime artifact (loader create-only; reader reads; cleanup deletes), in the rag bucket
    runtime_artifact_arn = local.op_runtime_arn
    # G5/G6: the pipeline operator role (artifacts bucket upload prefix, output prefix, EMR cluster scope)
    pipeline_role_name  = local.op_pipeline_role_name
    emr_upload_arn      = local.op_emr_upload_arn
    pipeline_output_arn = local.op_pipeline_out_arn
    emr_logs_arn        = local.op_emr_logs_arn
    emr_cluster_arns    = local.op_emr_cluster_arns
  } : null
}
