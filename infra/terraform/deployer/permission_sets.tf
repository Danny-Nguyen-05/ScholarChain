# Permission-set registry.
#
# Each permission set is a map of named policy documents (each becomes one
# customer-managed policy, <= 6144 non-whitespace characters each). Adding a
# later phase (for example "phase14-...") means adding one key to
# local.permission_sets below and listing it in var.enabled_permission_sets.
# No resource in main.tf needs to change.
#
# Policy documents only: no data source, no credential lookup.

locals {
  acct   = var.account_id
  region = var.region

  # ---- spike-emr constants -------------------------------------------------
  spike_prefix      = "scholarchain-spike-emr-"
  spike_stack_key   = "scholarchain:stack"
  spike_stack_value = "spike-emr"
  spike_emr_tag_key = "for-use-with-amazon-emr-managed-policies"

  spike_boundary_name = "${local.spike_prefix}boundary"
  spike_boundary_arn  = "arn:aws:iam::${local.acct}:policy/${local.spike_boundary_name}"
  spike_key_alias     = "alias/${local.spike_prefix}key"

  arn_ec2 = "arn:aws:ec2:${local.region}:${local.acct}"
  arn_emr = "arn:aws:elasticmapreduce:${local.region}:${local.acct}"
  arn_efs = "arn:aws:elasticfilesystem:${local.region}:${local.acct}"
  arn_kms = "arn:aws:kms:${local.region}:${local.acct}"
  arn_s3  = "arn:aws:s3:::${local.spike_prefix}*"
  arn_iam = "arn:aws:iam::${local.acct}"

  # Condition fragments.
  c_region        = { "aws:RequestedRegion" = local.region }
  c_req_stack     = { "aws:RequestTag/${local.spike_stack_key}" = local.spike_stack_value }
  c_res_stack     = { "aws:ResourceTag/${local.spike_stack_key}" = local.spike_stack_value }
  c_req_emr_tag   = { "aws:RequestTag/${local.spike_emr_tag_key}" = "true" }
  c_res_emr_tag   = { "aws:ResourceTag/${local.spike_emr_tag_key}" = "true" }
  ec2_create_kind = ["vpc", "subnet", "internet-gateway", "route-table", "security-group", "natgateway", "vpc-endpoint", "elastic-ip"]
  ec2_resources   = [for t in local.ec2_create_kind : "${local.arn_ec2}:${t}/*"]
  ec2_rule_arn    = "${local.arn_ec2}:security-group-rule/*"
  role_arns       = ["${local.arn_iam}:role/${local.spike_prefix}*"]
  # Services the spike roles may be passed to.
  pass_services = ["elasticmapreduce.amazonaws.com", "ec2.amazonaws.com"]

  # ---- spike-emr policy part: EMR + inventory ------------------------------
  spike_emr_part_emr = {
    Version = "2012-10-17"
    Statement = [
      {
        # Service Authorization Reference lists no resource type for tag:GetResources (list_resourcegroupstaggingapi).
        Sid       = "TagGetResourcesNoResourceType"
        Effect    = "Allow"
        Action    = ["tag:GetResources"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Service Authorization Reference lists no resource type for elasticmapreduce:ListClusters (list_emr).
        Sid       = "EmrListClustersNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:ListClusters"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Service Authorization Reference lists no resource type for elasticmapreduce:ListSecurityConfigurations (list_emr).
        Sid       = "EmrListSecurityConfigurationsNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:ListSecurityConfigurations"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Service Authorization Reference lists no resource type for elasticmapreduce:DescribeSecurityConfiguration (list_emr).
        Sid       = "EmrDescribeSecurityConfigurationNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:DescribeSecurityConfiguration"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Service Authorization Reference lists no resource type for elasticmapreduce:CreateSecurityConfiguration (list_emr).
        Sid       = "EmrCreateSecurityConfigurationNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:CreateSecurityConfiguration"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Service Authorization Reference lists no resource type for elasticmapreduce:DeleteSecurityConfiguration (list_emr).
        Sid       = "EmrDeleteSecurityConfigurationNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:DeleteSecurityConfiguration"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # elasticmapreduce:RunJobFlow has no resource type (list_emr); only request tags scope it.
        Sid      = "EmrRunJobFlowRequireStackTags"
        Effect   = "Allow"
        Action   = ["elasticmapreduce:RunJobFlow"]
        Resource = ["*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack, local.c_req_emr_tag)
        }
      },
      {
        # AddTags only on a cluster that already carries the stack tag, so a foreign
        # cluster can never be tagged into scope. Same shape as AWS's own tag-based
        # example (emr-fine-grained-cluster-access). RunJobFlow carries its tags itself.
        Sid      = "EmrAddTagsOnlyOnAlreadyTaggedClusters"
        Effect   = "Allow"
        Action   = ["elasticmapreduce:AddTags"]
        Resource = ["${local.arn_emr}:cluster/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_res_stack)
        }
      },
      {
        Sid    = "EmrManageStackClusters"
        Effect = "Allow"
        Action = [
          "elasticmapreduce:DescribeCluster",
          "elasticmapreduce:ListInstanceGroups",
          "elasticmapreduce:ListInstanceFleets",
          "elasticmapreduce:ListInstances",
          "elasticmapreduce:ListBootstrapActions",
          "elasticmapreduce:ListSteps",
          "elasticmapreduce:DescribeStep",
          "elasticmapreduce:GetAutoTerminationPolicy",
          "elasticmapreduce:GetManagedScalingPolicy",
          "elasticmapreduce:PutAutoTerminationPolicy",
          "elasticmapreduce:SetTerminationProtection",
          "elasticmapreduce:SetUnhealthyNodeReplacement",
          "elasticmapreduce:TerminateJobFlows",
        ]
        Resource = ["${local.arn_emr}:cluster/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_res_stack)
        }
      },
    ]
  }

  # ---- spike-emr policy part: network (EC2/VPC) ----------------------------
  spike_emr_part_network = {
    Version = "2012-10-17"
    Statement = [
      {
        # Describe actions never support resource-level scoping.
        Sid    = "Ec2DescribeNoResourceScoping"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAccountAttributes", "ec2:DescribeAddresses", "ec2:DescribeAddressesAttribute",
          "ec2:DescribeAvailabilityZones", "ec2:DescribeInstances", "ec2:DescribeInstanceTypeOfferings",
          "ec2:DescribeInternetGateways", "ec2:DescribeNatGateways", "ec2:DescribeNetworkAcls",
          "ec2:DescribeNetworkInterfaces", "ec2:DescribePrefixLists", "ec2:DescribeRouteTables",
          "ec2:DescribeSecurityGroupRules", "ec2:DescribeSecurityGroups", "ec2:DescribeSubnets",
          "ec2:DescribeTags", "ec2:DescribeVolumes", "ec2:DescribeVpcAttribute",
          "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcEndpointServices", "ec2:DescribeVpcs",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "Ec2CreateOnlyWithStackTag"
        Effect = "Allow"
        Action = [
          "ec2:CreateVpc", "ec2:CreateSubnet", "ec2:CreateInternetGateway", "ec2:CreateRouteTable",
          "ec2:CreateSecurityGroup", "ec2:CreateNatGateway", "ec2:CreateVpcEndpoint", "ec2:AllocateAddress",
        ]
        Resource  = local.ec2_resources
        Condition = { StringEquals = merge(local.c_region, local.c_req_stack) }
      },
      {
        Sid      = "Ec2TagOnCreateOnly"
        Effect   = "Allow"
        Action   = ["ec2:CreateTags"]
        Resource = concat(local.ec2_resources, [local.ec2_rule_arn])
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack, {
            "ec2:CreateAction" = [
              "CreateVpc", "CreateSubnet", "CreateInternetGateway", "CreateRouteTable",
              "CreateSecurityGroup", "CreateNatGateway", "CreateVpcEndpoint", "AllocateAddress",
              "AuthorizeSecurityGroupIngress", "AuthorizeSecurityGroupEgress",
            ]
          })
        }
      },
      {
        Sid    = "Ec2ModifyDeleteStackTaggedOnly"
        Effect = "Allow"
        Action = [
          "ec2:DeleteVpc", "ec2:ModifyVpcAttribute", "ec2:DeleteSubnet", "ec2:ModifySubnetAttribute",
          "ec2:DeleteInternetGateway", "ec2:AttachInternetGateway", "ec2:DetachInternetGateway",
          "ec2:DeleteRouteTable", "ec2:CreateRoute", "ec2:DeleteRoute", "ec2:AssociateRouteTable",
          "ec2:DisassociateRouteTable", "ec2:DeleteSecurityGroup", "ec2:AuthorizeSecurityGroupIngress",
          "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress",
          "ec2:ModifySecurityGroupRules", "ec2:DeleteNatGateway", "ec2:DeleteVpcEndpoints",
          "ec2:ModifyVpcEndpoint", "ec2:ReleaseAddress",
        ]
        Resource  = concat(local.ec2_resources, [local.ec2_rule_arn])
        Condition = { StringEquals = merge(local.c_region, local.c_res_stack) }
      },
      {
        # Rules do not exist before the call; only request tags can scope them.
        Sid       = "Ec2AuthorizeRulesWithStackTag"
        Effect    = "Allow"
        Action    = ["ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress"]
        Resource  = [local.ec2_rule_arn]
        Condition = { StringEquals = merge(local.c_region, local.c_req_stack) }
      },
    ]
  }

  # ---- spike-emr policy part: storage (S3, KMS, EFS) -----------------------
  spike_emr_part_storage = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketsWithSpikePrefix"
        Effect = "Allow"
        Action = [
          "s3:CreateBucket", "s3:DeleteBucket", "s3:ListBucket", "s3:ListBucketVersions",
          "s3:ListBucketMultipartUploads", "s3:GetBucketLocation", "s3:GetBucketAcl", "s3:GetBucketCORS",
          "s3:GetBucketLogging", "s3:GetBucketObjectLockConfiguration", "s3:GetBucketRequestPayment",
          "s3:GetBucketVersioning", "s3:GetBucketWebsite", "s3:GetAccelerateConfiguration",
          "s3:GetLifecycleConfiguration", "s3:GetReplicationConfiguration", "s3:GetEncryptionConfiguration",
          "s3:PutEncryptionConfiguration", "s3:GetBucketPolicy", "s3:PutBucketPolicy", "s3:DeleteBucketPolicy",
          "s3:GetBucketPublicAccessBlock", "s3:PutBucketPublicAccessBlock", "s3:GetBucketOwnershipControls",
          "s3:PutBucketOwnershipControls", "s3:GetBucketTagging", "s3:PutBucketTagging",
        ]
        Resource  = [local.arn_s3]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "S3ObjectsInSpikeBuckets"
        Effect = "Allow"
        Action = [
          "s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:DeleteObject", "s3:DeleteObjectVersion",
          "s3:GetObjectTagging", "s3:PutObjectTagging", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
        ]
        Resource  = ["${local.arn_s3}/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # kms:CreateKey has no resource type (list_kms); only request tags scope it.
        Sid      = "KmsCreateKeyWithStackTag"
        Effect   = "Allow"
        Action   = ["kms:CreateKey"]
        Resource = ["*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack)
        }
      },
      {
        # Needed so CreateKey can attach its tags. Deliberately broad on key/*: no IAM
        # statement or boundary in this root keys off a KMS tag (key administration
        # and use are granted by the key policy to the deployer role ARN, and the
        # boundary uses kms:ResourceAliases), so tagging a foreign key gains nothing.
        Sid      = "KmsTagOnCreate"
        Effect   = "Allow"
        Action   = ["kms:TagResource"]
        Resource = ["${local.arn_kms}:key/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack)
        }
      },
      {
        Sid       = "KmsAliasesWithSpikePrefix"
        Effect    = "Allow"
        Action    = ["kms:CreateAlias", "kms:DeleteAlias"]
        Resource  = ["${local.arn_kms}:alias/${local.spike_prefix}*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # kms:ListAliases has no resource type (list_kms).
        Sid       = "KmsListAliasesNoResourceScoping"
        Effect    = "Allow"
        Action    = ["kms:ListAliases"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # These actions accept file-system and access-point resource types (list_efs).
        Sid       = "EfsDescribeScopedToRegionAndAccount"
        Effect    = "Allow"
        Action    = ["elasticfilesystem:DescribeFileSystems", "elasticfilesystem:DescribeMountTargets", "elasticfilesystem:DescribeAccessPoints"]
        Resource  = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid      = "EfsCreateWithStackTag"
        Effect   = "Allow"
        Action   = ["elasticfilesystem:CreateFileSystem", "elasticfilesystem:CreateAccessPoint"]
        Resource = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack)
        }
      },
      {
        # Tag-on-create only: the elasticfilesystem:CreateAction key is absent from a
        # standalone TagResource call, so existing file systems cannot be tagged into scope.
        Sid      = "EfsTagOnCreateOnly"
        Effect   = "Allow"
        Action   = ["elasticfilesystem:TagResource"]
        Resource = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_stack, {
            "elasticfilesystem:CreateAction" = ["CreateFileSystem", "CreateAccessPoint"]
          })
        }
      },
      {
        Sid    = "EfsManageStackResources"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:DeleteFileSystem", "elasticfilesystem:DeleteAccessPoint",
          "elasticfilesystem:CreateMountTarget", "elasticfilesystem:DeleteMountTarget",
          "elasticfilesystem:DescribeMountTargetSecurityGroups", "elasticfilesystem:ModifyMountTargetSecurityGroups",
          "elasticfilesystem:DescribeLifecycleConfiguration", "elasticfilesystem:DescribeBackupPolicy",
          "elasticfilesystem:PutBackupPolicy", "elasticfilesystem:DescribeFileSystemPolicy",
          "elasticfilesystem:PutFileSystemPolicy", "elasticfilesystem:DeleteFileSystemPolicy",
          "elasticfilesystem:UpdateFileSystem", "elasticfilesystem:ListTagsForResource",
        ]
        Resource  = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_stack) }
      },
      {
        Sid      = "EfsMountTargetNetworkSubnetAndGroup"
        Effect   = "Allow"
        Action   = ["ec2:CreateNetworkInterface"]
        Resource = ["${local.arn_ec2}:subnet/*", "${local.arn_ec2}:security-group/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_res_stack)
        }
      },
      {
        # The ENI is created by the EFS mount-target call and carries no stack tag
        # yet. NOT resource-scopable by tag; see README.
        Sid      = "EfsMountTargetNetworkInterfaceUnscopable"
        Effect   = "Allow"
        Action   = ["ec2:CreateNetworkInterface", "ec2:DeleteNetworkInterface", "ec2:ModifyNetworkInterfaceAttribute"]
        Resource = ["${local.arn_ec2}:network-interface/*"]
        Condition = {
          StringEquals = local.c_region
        }
      },
    ]
  }

  # ---- spike-emr policy part: IAM limited to the spike prefix --------------
  spike_emr_part_iam = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "CreateSpikeRolesOnlyWithBoundaryAndTag"
        Effect   = "Allow"
        Action   = ["iam:CreateRole"]
        Resource = local.role_arns
        Condition = {
          StringEquals = merge(local.c_req_stack, { "iam:PermissionsBoundary" = local.spike_boundary_arn })
        }
      },
      {
        Sid      = "TagSpikeRolesWithStackTag"
        Effect   = "Allow"
        Action   = ["iam:TagRole"]
        Resource = local.role_arns
        Condition = {
          StringEquals = local.c_req_stack
        }
      },
      {
        Sid      = "AttachAndPutOnBoundedSpikeRolesOnly"
        Effect   = "Allow"
        Action   = ["iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:DetachRolePolicy"]
        Resource = local.role_arns
        Condition = {
          StringEquals = { "iam:PermissionsBoundary" = local.spike_boundary_arn }
        }
      },
      {
        # Exactly one managed policy may ever be attached: the EMR v2 service policy.
        Sid      = "AttachOnlyTheEmrV2ServicePolicy"
        Effect   = "Allow"
        Action   = ["iam:AttachRolePolicy"]
        Resource = local.role_arns
        Condition = {
          StringEquals = {
            "iam:PermissionsBoundary" = local.spike_boundary_arn
            "iam:PolicyARN"           = "arn:aws:iam::aws:policy/service-role/AmazonEMRServicePolicy_v2"
          }
        }
      },
      {
        Sid    = "ReadAndDeleteSpikeRoles"
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:DeleteRole", "iam:GetRolePolicy", "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies", "iam:ListInstanceProfilesForRole", "iam:ListRoleTags",
        ]
        Resource = local.role_arns
      },
      {
        Sid    = "ManageSpikeInstanceProfiles"
        Effect = "Allow"
        Action = [
          "iam:CreateInstanceProfile", "iam:DeleteInstanceProfile", "iam:GetInstanceProfile",
          "iam:AddRoleToInstanceProfile", "iam:RemoveRoleFromInstanceProfile", "iam:TagInstanceProfile",
          "iam:ListInstanceProfileTags",
        ]
        Resource = ["${local.arn_iam}:instance-profile/${local.spike_prefix}*"]
      },
      {
        Sid      = "PassSpikeRolesOnlyToEmrAndEc2"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = local.role_arns
        Condition = {
          StringEquals = { "iam:PassedToService" = local.pass_services }
        }
      },
      {
        # The boundary is immutable for the deployer: no new version, no default
        # switch, no deletion. (No iam:CreatePolicyVersion is granted anywhere;
        # these denies hold even if a later permission set adds one.)
        Sid    = "DenyBoundaryPolicyMutation"
        Effect = "Deny"
        Action = [
          "iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion",
        ]
        Resource = [local.spike_boundary_arn]
      },
      {
        Sid      = "DenyBoundaryRemovalOnSpikeRoles"
        Effect   = "Deny"
        Action   = ["iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy"]
        Resource = local.role_arns
      },
      {
        # The deployer must never assume a spike role, whatever its trust policy says.
        Sid      = "DenyAssumingSpikeRoles"
        Effect   = "Deny"
        Action   = ["sts:AssumeRole"]
        Resource = local.role_arns
      },
      {
        # Service-linked roles are created under aws-service-role/, not the spike
        # prefix. Narrow exception; see README.
        Sid    = "CreateRequiredServiceLinkedRolesOnly"
        Effect = "Allow"
        Action = ["iam:CreateServiceLinkedRole"]
        Resource = [
          "${local.arn_iam}:role/aws-service-role/elasticmapreduce.amazonaws.com/AWSServiceRoleForEMRCleanup",
          "${local.arn_iam}:role/aws-service-role/elasticfilesystem.amazonaws.com/AWSServiceRoleForAmazonElasticFileSystem",
        ]
        Condition = {
          StringEquals = { "iam:AWSServiceName" = ["elasticmapreduce.amazonaws.com", "elasticfilesystem.amazonaws.com"] }
        }
      },
    ]
  }

  # ---- spike permissions boundary (the ceiling for the spike roles) --------
  # Union of what the EMR service role (AmazonEMRServicePolicy_v2), the EC2
  # instance-profile role, and the service role's PassRole add-on may ever use.
  spike_boundary_policy = {
    Version = "2012-10-17"
    Statement = [
      # ---- EC2 ceiling: mirrors AmazonEMRServicePolicy_v2, statement by statement, so the
      # effective service-role permission is v2 itself and never wider. Source:
      # https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html
      # Existing resources must carry for-use-with-amazon-emr-managed-policies=true; the
      # subnet, security group and VPC must also carry the stack tag (Terraform tags them
      # at creation through provider default_tags). New instances, volumes and ENIs must be
      # created with the same request tag. VPC-endpoint, placement-group and launch-template
      # version actions of v2 are left out: this cluster does not use them.
      {
        # v2 CreateInTaggedNetwork + CreateSecurityGroupInVPCWithEMRTags: launching into,
        # or creating a group in, an EXISTING tagged subnet/security group/VPC.
        Sid    = "V2UseTaggedNetwork"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface", "ec2:RunInstances", "ec2:CreateFleet",
          "ec2:CreateLaunchTemplate", "ec2:CreateSecurityGroup",
        ]
        Resource  = ["${local.arn_ec2}:subnet/*", "${local.arn_ec2}:security-group/*", "${local.arn_ec2}:vpc/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_emr_tag, local.c_res_stack) }
      },
      {
        # v2 CreateWithEMRTaggedLaunchTemplate + ManageEMRTaggedResources (launch templates).
        Sid       = "V2UseTaggedLaunchTemplate"
        Effect    = "Allow"
        Action    = ["ec2:CreateFleet", "ec2:RunInstances", "ec2:DeleteLaunchTemplate"]
        Resource  = ["${local.arn_ec2}:launch-template/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_emr_tag) }
      },
      {
        # v2 CreateEMRTaggedLaunchTemplate / CreateEMRTaggedInstancesAndVolumes /
        # CreateNetworkInterfaceNeededForPrivateSubnet / default security group, and
        # ResourcesToLaunchEC2 (which v2 leaves unconditioned; here it carries the tag too).
        Sid    = "V2CreateNewWithEmrRequestTag"
        Effect = "Allow"
        Action = [
          "ec2:RunInstances", "ec2:CreateFleet", "ec2:CreateLaunchTemplate", "ec2:CreateNetworkInterface",
          "ec2:CreateSecurityGroup",
        ]
        Resource = [
          "${local.arn_ec2}:instance/*", "${local.arn_ec2}:volume/*", "${local.arn_ec2}:network-interface/*",
          "${local.arn_ec2}:launch-template/*", "${local.arn_ec2}:security-group/*",
          "arn:aws:ec2:${local.region}::image/ami-*", "${local.arn_ec2}:key-pair/*",
          "${local.arn_ec2}:capacity-reservation/*", "${local.arn_ec2}:fleet/*", "${local.arn_ec2}:dedicated-host/*",
        ]
        Condition = { StringEquals = merge(local.c_region, local.c_req_emr_tag) }
      },
      {
        # v2 ManageEMRTaggedResources (instances, ENIs).
        Sid       = "V2ManageTaggedInstancesAndEnis"
        Effect    = "Allow"
        Action    = ["ec2:DeleteNetworkInterface", "ec2:ModifyInstanceAttribute", "ec2:TerminateInstances"]
        Resource  = ["${local.arn_ec2}:network-interface/*", "${local.arn_ec2}:instance/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_emr_tag) }
      },
      {
        # v2 ManageSecurityGroups.
        Sid    = "V2ManageSecurityGroups"
        Effect = "Allow"
        Action = [
          "ec2:AuthorizeSecurityGroupEgress", "ec2:AuthorizeSecurityGroupIngress",
          "ec2:RevokeSecurityGroupEgress", "ec2:RevokeSecurityGroupIngress",
        ]
        Resource  = ["${local.arn_ec2}:security-group/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_emr_tag, local.c_res_stack) }
      },
      {
        # Tags may be applied only as part of a create call, never to existing resources.
        Sid      = "V2TagOnCreateOnly"
        Effect   = "Allow"
        Action   = ["ec2:CreateTags"]
        Resource = ["${local.arn_ec2}:instance/*", "${local.arn_ec2}:volume/*", "${local.arn_ec2}:network-interface/*", "${local.arn_ec2}:launch-template/*", "${local.arn_ec2}:security-group/*"]
        Condition = {
          StringEquals = merge(local.c_region, {
            "ec2:CreateAction" = ["RunInstances", "CreateFleet", "CreateLaunchTemplate", "CreateNetworkInterface", "CreateSecurityGroup"]
          })
        }
      },
      {
        # Removing tags never widens access; limited to EMR-managed resources.
        Sid      = "V2DeleteTagsOnEmrTaggedResources"
        Effect   = "Allow"
        Action   = ["ec2:DeleteTags"]
        Resource = ["${local.arn_ec2}:instance/*", "${local.arn_ec2}:volume/*", "${local.arn_ec2}:network-interface/*", "${local.arn_ec2}:launch-template/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_res_emr_tag)
        }
      },
      {
        Sid    = "EmrServiceRoleEc2DescribeCeiling"
        Effect = "Allow"
        Action = [
          "ec2:DescribeAccountAttributes", "ec2:DescribeCapacityReservations", "ec2:DescribeDhcpOptions",
          "ec2:DescribeImages", "ec2:DescribeInstances", "ec2:DescribeInstanceTypeOfferings",
          "ec2:DescribeLaunchTemplates", "ec2:DescribeNetworkAcls", "ec2:DescribeNetworkInterfaces",
          "ec2:DescribePlacementGroups", "ec2:DescribeRouteTables", "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets", "ec2:DescribeVolumes", "ec2:DescribeVolumeStatus", "ec2:DescribeVpcAttribute",
          "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcs",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid      = "SpikeNodeS3Ceiling"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:ListBucket"]
        Resource = [local.arn_s3, "${local.arn_s3}/*"]
      },
      {
        Sid    = "SpikeKeyCeiling"
        Effect = "Allow"
        Action = [
          "kms:Encrypt", "kms:Decrypt", "kms:ReEncryptFrom", "kms:ReEncryptTo", "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext", "kms:DescribeKey", "kms:CreateGrant", "kms:ListGrants", "kms:RevokeGrant",
        ]
        Resource = ["${local.arn_kms}:key/*"]
        Condition = {
          StringEquals = local.c_region
          # Alias, not tag: only the key aliased alias/scholarchain-spike-emr-key, and the
          # deployer cannot alias a key unless that key's own policy lets it.
          "ForAnyValue:StringEquals" = { "kms:ResourceAliases" = local.spike_key_alias }
        }
      },
      {
        # Cluster auto-termination (layer 4) needs these from the instance profile:
        # https://repost.aws/knowledge-center/emr-troubleshoot-cluster-termination
        Sid    = "SpikeEmrAutoTerminationCeiling"
        Effect = "Allow"
        Action = [
          "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy",
          "elasticmapreduce:RemoveAutoTerminationPolicy",
        ]
        Resource  = ["${local.arn_emr}:cluster/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_stack) }
      },
      {
        Sid      = "SpikeEfsClientCeiling"
        Effect   = "Allow"
        Action   = ["elasticfilesystem:ClientMount", "elasticfilesystem:ClientWrite"]
        Resource = ["${local.arn_efs}:file-system/*"]
      },
      {
        Sid      = "SpikePassInstanceRoleCeiling"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = local.role_arns
        Condition = {
          StringEquals = { "iam:PassedToService" = ["ec2.amazonaws.com"] }
        }
      },
    ]
  }

  # ---- registry ------------------------------------------------------------
  permission_sets = {
    "spike-emr" = {
      emr     = local.spike_emr_part_emr
      network = local.spike_emr_part_network
      storage = local.spike_emr_part_storage
      iam     = local.spike_emr_part_iam
    }
    # Phase 14 example (do not implement now):
    # "phase14-..." = { part = local.some_policy_document }
  }
}
