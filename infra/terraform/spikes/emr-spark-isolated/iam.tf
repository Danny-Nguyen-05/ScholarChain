# Both roles carry the deployer's permissions boundary (a variable ARN). The
# deployer can only create roles named scholarchain-spike-emr-* with exactly
# that boundary.

resource "aws_iam_role" "service" {
  name                 = local.service_role_name
  permissions_boundary = var.permissions_boundary_arn
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "elasticmapreduce.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = { "aws:SourceAccount" = var.account_id }
        ArnLike      = { "aws:SourceArn" = "arn:aws:elasticmapreduce:${var.region}:${var.account_id}:*" }
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "service_emr_v2" {
  role       = aws_iam_role.service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
}

# AmazonEMRServicePolicy_v2 only allows iam:PassRole for EMR_EC2_DefaultRole,
# so the custom instance role must be added explicitly.
resource "aws_iam_role_policy" "service_pass_instance_role" {
  name = "${local.prefix}-pass-instance-role"
  role = aws_iam_role.service.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PassInstanceRoleToEc2"
      Effect    = "Allow"
      Action    = "iam:PassRole"
      Resource  = local.instance_role_arn
      Condition = { StringLike = { "iam:PassedToService" = "ec2.amazonaws.com*" } }
    }]
  })
}

resource "aws_iam_role" "instance" {
  name                 = local.instance_role_name
  permissions_boundary = var.permissions_boundary_arn
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Nothing but this bucket's prefixes, this key, and this file system via this
# access point.
resource "aws_iam_role_policy" "instance" {
  name = "${local.prefix}-instance"
  role = aws_iam_role.instance.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ReadStagedArtifacts"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${aws_s3_bucket.spike.arn}/staging/*"]
      },
      {
        Sid      = "WriteResultsAndLogs"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:AbortMultipartUpload"]
        Resource = ["${aws_s3_bucket.spike.arn}/results/*", "${aws_s3_bucket.spike.arn}/emr-logs/*"]
      },
      {
        Sid       = "ListOwnPrefixesOnly"
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = [aws_s3_bucket.spike.arn]
        Condition = { StringLike = { "s3:prefix" = ["staging/*", "results/*", "emr-logs/*"] } }
      },
      {
        Sid      = "UseSpikeKey"
        Effect   = "Allow"
        Action   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:DescribeKey"]
        Resource = [aws_kms_key.spike.arn]
      },
      {
        # EMR auto-termination (layer 4) does not work without these on the instance
        # profile: https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination
        Sid    = "AutoTerminationPolicyOnStackClusters"
        Effect = "Allow"
        Action = [
          "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy",
          "elasticmapreduce:RemoveAutoTerminationPolicy",
        ]
        Resource  = ["arn:aws:elasticmapreduce:${var.region}:${var.account_id}:cluster/*"]
        Condition = { StringEquals = { "aws:ResourceTag/scholarchain:stack" = "spike-emr" } }
      },
      {
        Sid       = "MountSpikeFileSystemViaAccessPoint"
        Effect    = "Allow"
        Action    = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource  = [aws_efs_file_system.spike.arn]
        Condition = { StringEquals = { "elasticfilesystem:AccessPointArn" = aws_efs_access_point.spike.arn } }
      },
    ]
  })
}

resource "aws_iam_instance_profile" "instance" {
  name = "${local.prefix}-instance"
  role = aws_iam_role.instance.name
}
