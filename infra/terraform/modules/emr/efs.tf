# G1 option (ii): EFS staging with explicit S3 copy steps (the pipeline's stage-in and copy-out). Ported from the live-proven
# Phase 12D spike (spikes/emr-spark-isolated/efs.tf): encrypted with the project CMK, one mount target in the cluster subnet,
# NFS 2049 admitted only from the EMR security group, and an access point that fixes the POSIX identity and root directory.
# Created under the same flag as the cluster (local.active).
resource "aws_efs_file_system" "staging" {
  count            = local.active ? 1 : 0
  encrypted        = true
  kms_key_id       = var.kms_key_arn
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  tags             = merge(var.tags, { Name = "${var.name_prefix}-emr-staging" })
}

# Automatic backups are explicitly disabled: staged data is a copy of S3 inputs and outputs are copied back.
resource "aws_efs_backup_policy" "staging" {
  count          = local.active ? 1 : 0
  file_system_id = aws_efs_file_system.staging[0].id
  backup_policy { status = "DISABLED" }
}

resource "aws_security_group" "efs" {
  count                  = local.active ? 1 : 0
  name                   = "${var.name_prefix}-emr-efs"
  description            = "NFS 2049 from the EMR node security group only"
  vpc_id                 = var.vpc_id
  revoke_rules_on_delete = true
  tags                   = merge(var.tags, { Name = "${var.name_prefix}-emr-efs" })
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_emr" {
  count                        = local.active ? 1 : 0
  security_group_id            = aws_security_group.efs[0].id
  referenced_security_group_id = var.security_group_id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  description                  = "NFS from the EMR node group only"
}

# The EMR group's egress is rule-by-rule (network module), so the NFS path to the EFS group is added here.
resource "aws_vpc_security_group_egress_rule" "emr_to_efs" {
  count                        = local.active ? 1 : 0
  security_group_id            = var.security_group_id
  referenced_security_group_id = aws_security_group.efs[0].id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  description                  = "NFS to the EMR staging file system only"
}

resource "aws_efs_mount_target" "staging" {
  count           = local.active ? 1 : 0
  file_system_id  = aws_efs_file_system.staging[0].id
  subnet_id       = var.subnet_id
  security_groups = [aws_security_group.efs[0].id]
}

resource "aws_efs_access_point" "staging" {
  count          = local.active ? 1 : 0
  file_system_id = aws_efs_file_system.staging[0].id
  posix_user {
    uid = var.node_paths.efs_uid
    gid = var.node_paths.efs_gid
  }
  root_directory {
    path = var.node_paths.efs_root_dir
    creation_info {
      owner_uid   = var.node_paths.efs_uid
      owner_gid   = var.node_paths.efs_gid
      permissions = "0750"
    }
  }
  tags = merge(var.tags, { Name = "${var.name_prefix}-emr-ap" })
}

resource "aws_efs_file_system_policy" "staging" {
  count          = local.active ? 1 : 0
  file_system_id = aws_efs_file_system.staging[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonTls"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "*"
        Resource  = aws_efs_file_system.staging[0].arn
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "AllowInstanceRoleViaAccessPointOnly"
        Effect    = "Allow"
        Principal = { AWS = var.instance_role_arn }
        Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource  = aws_efs_file_system.staging[0].arn
        Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.staging[0].arn } }
      },
    ]
  })
}

# Identity-side permissions of the EMR instance role that exist only because of this module: the EFS client (through this
# access point only) and EMR auto-termination (the idle timeout does not work without these on the instance profile,
# https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination), limited to clusters carrying the stack tag.
resource "aws_iam_role_policy" "node" {
  count = local.active ? 1 : 0
  name  = "emr-efs-and-auto-termination"
  role  = var.instance_role_name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "MountStagingFileSystemViaAccessPoint"
        Effect    = "Allow"
        Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource  = [aws_efs_file_system.staging[0].arn]
        Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.staging[0].arn } }
      },
      {
        Sid       = "AutoTerminationPolicyOnStackClusters"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy", "elasticmapreduce:RemoveAutoTerminationPolicy"]
        Resource  = ["arn:aws:elasticmapreduce:${var.aws_region}:${var.aws_account_id}:cluster/*"]
        Condition = { StringEquals = { "aws:ResourceTag/scholarchain:stack" = local.cfg.stack_tag_value } }
      },
    ]
  })
}
