# One CMK for EBS and local-disk encryption (EMR security configuration), EFS,
# and S3 SSE-KMS. Rotation is not needed for a same-day spike. The short
# deletion window keeps the post-destroy residue (PendingDeletion) brief.
#
# The key policy is a literal inside the aws_kms_key resource, with enumerated
# actions only (no kms:* and no prefix wildcards). Resource "*" in a key policy
# means "this key".

locals {
  service_role_name  = "${local.prefix}-service"
  instance_role_name = "${local.prefix}-instance"
  service_role_arn   = "arn:aws:iam::${var.account_id}:role/${local.service_role_name}"
  instance_role_arn  = "arn:aws:iam::${var.account_id}:role/${local.instance_role_name}"
}

resource "aws_kms_key" "spike" {
  description             = "ScholarChain Phase 12D spike (EBS, EFS, S3)"
  enable_key_rotation     = false
  deletion_window_in_days = 7
  tags                    = { Name = "${local.prefix}-key" }

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # The account root delegates to IAM (the deployer role), limited to the
        # administration and use actions the spike needs, including deletion.
        Sid       = "AccountRootAdministersAndDelegates"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${var.account_id}:root" }
        Action = [
          "kms:CancelKeyDeletion", "kms:CreateAlias", "kms:CreateGrant", "kms:DeleteAlias",
          "kms:Decrypt", "kms:DescribeKey", "kms:DisableKey", "kms:DisableKeyRotation",
          "kms:EnableKey", "kms:EnableKeyRotation", "kms:Encrypt", "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext", "kms:GetKeyPolicy", "kms:GetKeyRotationStatus",
          "kms:ListGrants", "kms:ListKeyPolicies", "kms:ListResourceTags", "kms:PutKeyPolicy",
          "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:RetireGrant", "kms:RevokeGrant",
          "kms:ScheduleKeyDeletion", "kms:TagResource", "kms:UntagResource", "kms:UpdateAlias",
          "kms:UpdateKeyDescription",
        ]
        Resource = "*"
      },
      {
        # Key administration is granted here, directly to the deployer role, not
        # through IAM tag conditions (tags can be applied by anyone with tag rights).
        Sid       = "DeployerAdministersKey"
        Effect    = "Allow"
        Principal = { AWS = var.deployer_role_arn }
        Action = [
          "kms:DescribeKey", "kms:GetKeyPolicy", "kms:PutKeyPolicy", "kms:ListResourceTags",
          "kms:GetKeyRotationStatus", "kms:EnableKeyRotation", "kms:DisableKeyRotation",
          "kms:ScheduleKeyDeletion", "kms:CancelKeyDeletion", "kms:CreateAlias", "kms:DeleteAlias",
        ]
        Resource = "*"
      },
      {
        # The deployer uploads staged objects (S3) and creates the file system (EFS) with this key.
        Sid       = "DeployerUsesKeyOnlyViaS3AndEfs"
        Effect    = "Allow"
        Principal = { AWS = var.deployer_role_arn }
        Action = [
          "kms:Encrypt", "kms:Decrypt", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext", "kms:CreateGrant",
        ]
        Resource = "*"
        Condition = {
          StringEquals = { "kms:ViaService" = ["s3.${var.region}.amazonaws.com", "elasticfilesystem.${var.region}.amazonaws.com"] }
        }
      },
      {
        # https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-encryption-enable.html
        Sid       = "EmrServiceRoleEbsEncryption"
        Effect    = "Allow"
        Principal = { AWS = local.service_role_arn }
        Action = [
          "kms:Encrypt", "kms:Decrypt", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext", "kms:DescribeKey", "kms:CreateGrant", "kms:ListGrants",
          "kms:RevokeGrant",
        ]
        Resource = "*"
      },
      {
        Sid       = "InstanceProfileDataKeyUse"
        Effect    = "Allow"
        Principal = { AWS = local.instance_role_arn }
        Action = [
          "kms:Encrypt", "kms:Decrypt", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext", "kms:DescribeKey",
        ]
        Resource = "*"
      },
    ]
  })

  # The principals named in the key policy must exist first.
  depends_on = [aws_iam_role.service, aws_iam_role.instance]
}

resource "aws_kms_alias" "spike" {
  name          = "alias/${local.prefix}-key"
  target_key_id = aws_kms_key.spike.key_id
}
