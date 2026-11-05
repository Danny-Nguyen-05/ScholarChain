resource "aws_efs_file_system" "spike" {
  encrypted        = true
  kms_key_id       = aws_kms_key.spike.arn
  performance_mode = "generalPurpose"
  throughput_mode  = "elastic"
  tags             = { Name = "${local.prefix}-efs" }
}

# Automatic backups explicitly disabled.
resource "aws_efs_backup_policy" "spike" {
  file_system_id = aws_efs_file_system.spike.id
  backup_policy {
    status = "DISABLED"
  }
}

resource "aws_efs_mount_target" "private" {
  file_system_id  = aws_efs_file_system.spike.id
  subnet_id       = aws_subnet.private.id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "spike" {
  file_system_id = aws_efs_file_system.spike.id
  posix_user {
    uid = local.efs_uid
    gid = local.efs_gid
  }
  root_directory {
    path = local.efs_root_dir
    creation_info {
      owner_uid   = local.efs_uid
      owner_gid   = local.efs_gid
      permissions = "0750"
    }
  }
  tags = { Name = "${local.prefix}-ap" }
}

resource "aws_efs_file_system_policy" "spike" {
  file_system_id = aws_efs_file_system.spike.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyNonTls"
        Effect    = "Deny"
        Principal = { AWS = "*" }
        Action    = "*"
        Resource  = aws_efs_file_system.spike.arn
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "AllowInstanceRoleViaAccessPointOnly"
        Effect    = "Allow"
        Principal = { AWS = local.instance_role_arn }
        Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource  = aws_efs_file_system.spike.arn
        Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.spike.arn } }
      },
    ]
  })
  depends_on = [aws_iam_role.instance]
}
