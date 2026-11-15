# Replan W5b (user decision 1): the task role of the temporary Neptune tunnel task (a one-off ECS task the operator opens an ECS Exec
# port-forwarding session to). Naming contract with the deployer root (infra/terraform/deployer/README.md, "Replan W5a"): the role is
# `<project>-<environment>-neptune-tunnel-task`, which matches the deployer's `*-task` iam:CreateRole / iam:PassRole patterns; it is
# created with the runtime permissions boundary (the only boundary the deployer accepts for it) and the project tags.
#
# The inline policy holds ONLY the four ssmmessages channel actions ECS Exec needs. They have no resource type (Resource "*" is the
# only form), and the boundary (deployer/boundaries/runtime.json.tftpl, EcsExecChannelsForTheNeptuneTunnel) allows exactly these four.
# No data access of any kind: the tunnel carries traffic, and the human's operator-loader session signs the Neptune requests.
locals {
  neptune_tunnel_actions = ["ssmmessages:CreateControlChannel", "ssmmessages:CreateDataChannel", "ssmmessages:OpenControlChannel", "ssmmessages:OpenDataChannel"]
}

resource "aws_iam_role" "neptune_tunnel_task" {
  count                = var.neptune_tunnel_role_enabled ? 1 : 0
  permissions_boundary = local.boundary_arn.runtime
  name                 = "${var.name_prefix}-neptune-tunnel-task"
  assume_role_policy   = local.ecs_trust
  tags                 = var.tags
}

resource "aws_iam_role_policy" "neptune_tunnel_task" {
  count = var.neptune_tunnel_role_enabled ? 1 : 0
  name  = "ecs-exec-channels"
  role  = aws_iam_role.neptune_tunnel_task[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "EcsExecSessionChannelsOnly"
      Effect   = "Allow"
      Action   = local.neptune_tunnel_actions
      Resource = "*" # The ssmmessages channel actions support no resource-level permissions.
    }]
  })
}

# Concrete policy dependency, like runtime_ready_roles: the task definition never references a trust-only role.
output "neptune_tunnel_task_role_arn" {
  value      = one(aws_iam_role.neptune_tunnel_task[*].arn)
  depends_on = [aws_iam_role_policy.neptune_tunnel_task]
}
output "neptune_tunnel_controls" {
  value = var.neptune_tunnel_role_enabled ? {
    role_name   = aws_iam_role.neptune_tunnel_task[0].name
    boundary    = aws_iam_role.neptune_tunnel_task[0].permissions_boundary
    trust       = aws_iam_role.neptune_tunnel_task[0].assume_role_policy
    policy      = aws_iam_role_policy.neptune_tunnel_task[0].policy
    policy_name = aws_iam_role_policy.neptune_tunnel_task[0].name
  } : null
}
