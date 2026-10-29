locals { active = var.enabled && var.engine_version != null && var.parameter_family != null }
resource "aws_neptune_subnet_group" "data" {
  count      = local.active ? 1 : 0
  name       = "${var.name_prefix}-neptune"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}
resource "aws_neptune_cluster_parameter_group" "data" {
  count       = local.active ? 1 : 0
  name        = "${var.name_prefix}-neptune-cluster"
  family      = var.parameter_family
  description = "Course Neptune cluster configuration"
  parameter {
    name  = "neptune_enable_audit_log"
    value = "1"
  }
  tags = var.tags
}
resource "aws_neptune_parameter_group" "data" {
  count       = local.active ? 1 : 0
  name        = "${var.name_prefix}-neptune-instance"
  family      = var.parameter_family
  description = "Course Neptune instance configuration"
  tags        = var.tags
}
resource "aws_neptune_cluster" "data" {
  count                                = local.active ? 1 : 0
  cluster_identifier                   = "${var.name_prefix}-graph"
  engine_version                       = var.engine_version
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.data[0].name
  neptune_subnet_group_name            = aws_neptune_subnet_group.data[0].name
  vpc_security_group_ids               = [var.security_group_id]
  port                                 = var.port
  storage_encrypted                    = true
  kms_key_arn                          = var.kms_key_arn
  iam_database_authentication_enabled  = true
  iam_roles                            = [var.loader_role_arn]
  backup_retention_period              = var.backup_days
  copy_tags_to_snapshot                = true
  deletion_protection                  = !var.cleanup_mode
  skip_final_snapshot                  = var.cleanup_mode
  final_snapshot_identifier            = var.cleanup_mode ? null : "${var.name_prefix}-graph-final"
  enable_cloudwatch_logs_exports       = var.audit_log_group_name != null ? ["audit"] : []
  serverless_v2_scaling_configuration {
    min_capacity = var.min_capacity
    max_capacity = var.max_capacity
  }
  tags = var.tags
}
resource "aws_neptune_cluster_instance" "writer" {
  count                        = local.active ? 1 : 0
  identifier                   = "${var.name_prefix}-graph-writer"
  cluster_identifier           = aws_neptune_cluster.data[0].id
  instance_class               = "db.serverless"
  neptune_parameter_group_name = aws_neptune_parameter_group.data[0].name
  neptune_subnet_group_name    = aws_neptune_subnet_group.data[0].name
  publicly_accessible          = false
  auto_minor_version_upgrade   = false
  tags                         = var.tags
}
