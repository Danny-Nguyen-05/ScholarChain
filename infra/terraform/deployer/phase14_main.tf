# Phase 14 permission set "phase14-main" (decision 14-6): what the human operator's MFA role needs to plan, apply, verify and
# tear down the MAIN root (infra/terraform, every module) with the runtime, Neptune and EMR enabled. Authored offline; the
# action lists were derived from the resource types enumerated across infra/terraform/*.tf and infra/terraform/modules/**
# (the table is in docs and evidence: target/phase14/evidence/14a-infra/resource-types.txt) and from the AWS provider's
# create, read (refresh), update and delete calls, plus the AWS CLI calls scripts/deploy.sh makes under this role.
#
# Scoping, in order of preference: (1) the resource ARN, built on the main stack's name prefix (scholarchain-<environment>)
# wherever the service lets the ARN carry the name; (2) project/environment tags (request tag on create calls, resource tag on
# calls against existing resources; the main root's provider default_tags put both on everything that can carry a tag);
# (3) aws:RequestedRegion = us-east-2 on every regional statement. Actions without a resource type, and list-style reads, are
# the "honest list" in deployer/README.md. IAM and Route 53 are global services: no RequestedRegion condition.
#
# Sources: Service Authorization Reference, https://docs.aws.amazon.com/service-authorization/latest/reference/reference_policies_actions-resources-contextkeys.html
# (one page per service, linked in the README), the provider's resource code paths, and the services' own IAM pages.

locals {
  mp = "scholarchain-${var.main_environment}"

  # Tag conditions. The main root's provider default_tags set project and environment on every taggable resource.
  c_req_main = { "aws:RequestTag/project" = local.m_project, "aws:RequestTag/environment" = var.main_environment }
  c_res_main = { "aws:ResourceTag/project" = local.m_project, "aws:ResourceTag/environment" = var.main_environment }
  m_project  = "scholarchain"

  # Boundaries (created by this root; carried by every role the main root creates).
  m_boundary_runtime_name = "${local.mp}-permissions-boundary"
  m_boundary_emr_name     = "${local.mp}-emr-service-boundary"
  m_boundary_runtime_arn  = "arn:aws:iam::${local.acct}:policy/${local.m_boundary_runtime_name}"
  m_boundary_emr_arn      = "arn:aws:iam::${local.acct}:policy/${local.m_boundary_emr_name}"
  m_boundary_arns         = [local.m_boundary_runtime_arn, local.m_boundary_emr_arn]

  # ARN builders (account and region come from the variables; nothing is hardcoded).
  m_arn_rds    = "arn:aws:rds:${local.region}:${local.acct}"
  m_arn_ecs    = "arn:aws:ecs:${local.region}:${local.acct}"
  arn_acm      = "arn:aws:acm:${local.region}:${local.acct}"
  m_arn_elb    = "arn:aws:elasticloadbalancing:${local.region}:${local.acct}"
  m_arn_logs   = "arn:aws:logs:${local.region}:${local.acct}"
  m_arn_cw     = "arn:aws:cloudwatch:${local.region}:${local.acct}"
  m_arn_ddb    = "arn:aws:dynamodb:${local.region}:${local.acct}"
  m_arn_sqs    = "arn:aws:sqs:${local.region}:${local.acct}"
  m_arn_sfn    = "arn:aws:states:${local.region}:${local.acct}"
  m_arn_ecr    = "arn:aws:ecr:${local.region}:${local.acct}"
  m_arn_s3v    = "arn:aws:s3vectors:${local.region}:${local.acct}"
  m_arn_aas    = "arn:aws:application-autoscaling:${local.region}:${local.acct}"
  m_arn_sd     = "arn:aws:servicediscovery:${local.region}:${local.acct}"
  m_arn_secret = "arn:aws:secretsmanager:${local.region}:${local.acct}"
  m_arn_s3     = "arn:aws:s3:::${local.mp}-${local.acct}-*"
  m_arn_s3_art = "arn:aws:s3:::${local.mp}-${local.acct}-artifacts"
  m_role_arns  = ["${local.arn_iam}:role/${local.mp}-*"]

  m_ec2_create_actions = [
    "CreateVpc", "CreateSubnet", "CreateInternetGateway", "CreateRouteTable", "CreateSecurityGroup",
    "CreateNatGateway", "CreateVpcEndpoint", "AllocateAddress",
    "AuthorizeSecurityGroupIngress", "AuthorizeSecurityGroupEgress",
  ]

  # ---- document 1: network (VPC, subnets, NAT, endpoints, security groups and rules) -----------------------------------
  m14_network = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Ec2DescribeNoResourceScoping"
        Effect = "Allow"
        Action = [

          "ec2:DescribeAccountAttributes", "ec2:DescribeAddresses", "ec2:DescribeAddressesAttribute",
          "ec2:DescribeAvailabilityZones", "ec2:DescribeInstances", "ec2:DescribeInstanceTypeOfferings",
          "ec2:DescribeInternetGateways", "ec2:DescribeNatGateways", "ec2:DescribeNetworkAcls",
          "ec2:DescribeNetworkInterfaces", "ec2:DescribePrefixLists", "ec2:DescribeRegions",
          "ec2:DescribeRouteTables", "ec2:DescribeSecurityGroupRules", "ec2:DescribeSecurityGroups",
          "ec2:DescribeSubnets", "ec2:DescribeTags", "ec2:DescribeVolumes", "ec2:DescribeVpcAttribute",
          "ec2:DescribeVpcEndpoints", "ec2:DescribeVpcEndpointServices", "ec2:DescribeVpcs",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "Ec2CreateOnlyWithProjectTags"
        Effect = "Allow"
        Action = [
          "ec2:CreateVpc", "ec2:CreateSubnet", "ec2:CreateInternetGateway", "ec2:CreateRouteTable",
          "ec2:CreateSecurityGroup", "ec2:CreateNatGateway", "ec2:CreateVpcEndpoint", "ec2:AllocateAddress",
        ]
        Resource  = local.ec2_resources
        Condition = { StringEquals = merge(local.c_region, local.c_req_main) }
      },
      {
        # The same create calls are authorized against EXISTING parents (subnet, route table, vpc, EIP, security group);
        # a request tag never applies to those, so they need the resource tag (learned in the Phase 12D live run).
        Sid    = "Ec2CreateOnExistingProjectParents"
        Effect = "Allow"
        Action = [
          "ec2:CreateSubnet", "ec2:CreateRouteTable", "ec2:CreateSecurityGroup",
          "ec2:CreateNatGateway", "ec2:CreateVpcEndpoint",
        ]
        Resource = [
          "${local.arn_ec2}:vpc/*", "${local.arn_ec2}:subnet/*", "${local.arn_ec2}:route-table/*",
          "${local.arn_ec2}:elastic-ip/*", "${local.arn_ec2}:security-group/*",
        ]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        Sid      = "Ec2TagOnCreateOnly"
        Effect   = "Allow"
        Action   = ["ec2:CreateTags"]
        Resource = concat(local.ec2_resources, [local.ec2_rule_arn])
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_main, { "ec2:CreateAction" = local.m_ec2_create_actions })
        }
      },
      {
        # In-place tag changes (for example expiration_date) on resources that already carry the project tags.
        Sid       = "Ec2RetagProjectResources"
        Effect    = "Allow"
        Action    = ["ec2:CreateTags", "ec2:DeleteTags"]
        Resource  = concat(local.ec2_resources, [local.ec2_rule_arn])
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
    ]
  }

  # ---- document 1b: network, modify, delete and security group rules -----------------------------------------------
  m14_network_mod = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Ec2ModifyDeleteProjectTaggedOnly"
        Effect = "Allow"
        Action = [
          "ec2:DeleteVpc", "ec2:ModifyVpcAttribute", "ec2:DeleteSubnet", "ec2:ModifySubnetAttribute",
          "ec2:DeleteInternetGateway", "ec2:AttachInternetGateway", "ec2:DetachInternetGateway",
          "ec2:DeleteRouteTable", "ec2:CreateRoute", "ec2:ReplaceRoute", "ec2:DeleteRoute",
          "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable", "ec2:DeleteSecurityGroup",
          "ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress",
          "ec2:RevokeSecurityGroupIngress", "ec2:RevokeSecurityGroupEgress", "ec2:ModifySecurityGroupRules",
          "ec2:DeleteNatGateway", "ec2:DeleteVpcEndpoints", "ec2:ModifyVpcEndpoint",
          "ec2:ReleaseAddress", "ec2:DisassociateAddress",
        ]
        Resource  = concat(local.ec2_resources, [local.ec2_rule_arn])
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        # Rules do not exist before the call; only the request tags can scope them.
        Sid       = "Ec2AuthorizeRulesWithProjectTags"
        Effect    = "Allow"
        Action    = ["ec2:AuthorizeSecurityGroupIngress", "ec2:AuthorizeSecurityGroupEgress"]
        Resource  = [local.ec2_rule_arn]
        Condition = { StringEquals = merge(local.c_region, local.c_req_main) }
      },
    ]
  }

  # ---- document 2: data stores (S3, S3 Vectors, DynamoDB, SQS, Step Functions) and Neptune (rds API namespace) ---------------------------------------
  m14_data = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3BucketsOfTheMainStack"
        Effect = "Allow"
        Action = [
          "s3:CreateBucket", "s3:DeleteBucket", "s3:ListBucket", "s3:ListBucketVersions", "s3:ListBucketMultipartUploads",
          "s3:GetBucketLocation", "s3:GetBucketAcl", "s3:GetBucketCORS", "s3:GetBucketLogging",
          "s3:GetBucketObjectLockConfiguration", "s3:GetBucketRequestPayment", "s3:GetBucketVersioning",
          "s3:PutBucketVersioning", "s3:GetBucketWebsite", "s3:GetAccelerateConfiguration",
          "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration", "s3:GetReplicationConfiguration",
          "s3:GetEncryptionConfiguration", "s3:PutEncryptionConfiguration", "s3:GetBucketPolicy",
          "s3:PutBucketPolicy", "s3:DeleteBucketPolicy", "s3:GetBucketPublicAccessBlock",
          "s3:PutBucketPublicAccessBlock", "s3:GetBucketOwnershipControls", "s3:PutBucketOwnershipControls",
          "s3:GetBucketTagging", "s3:PutBucketTagging",
        ]
        Resource  = [local.m_arn_s3]
        Condition = { StringEquals = local.c_region }
      },
      {
        # scripts/deploy.sh: runtime-archive upload (multipart, SHA-256 checksum), head-object and get-object-attributes
        # verification. Only the artifacts bucket; no other bucket (the 14C data loads need their own grant). Deletes are the separate statement below.
        Sid    = "S3ArtifactsObjectsUploadAndVerify"
        Effect = "Allow"
        Action = [
          "s3:PutObject", "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectAttributes",
          "s3:GetObjectVersionAttributes", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts",
        ]
        Resource  = ["${local.m_arn_s3_art}/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # W5a-3: cleanup (force_destroy = cleanup_mode on the project buckets). The AWS provider (6.44.0, s3/delete.go emptyBucket)
        # lists object versions (s3:ListBucketVersions, granted above) and deletes every version and delete marker with DeleteObjects
        # (or DeleteObject for keys outside the XML range); an unversioned key needs s3:DeleteObject, a versioned entry
        # s3:DeleteObjectVersion. It does not abort multipart uploads and the buckets have no Object Lock, so neither
        # s3:AbortMultipartUpload on these buckets nor s3:BypassGovernanceRetention is granted. Objects of the project buckets only.
        Sid       = "S3ObjectsDeleteForForceDestroy"
        Effect    = "Allow"
        Action    = ["s3:DeleteObject", "s3:DeleteObjectVersion"]
        Resource  = ["${local.m_arn_s3}/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # The provider's vector-bucket force_destroy (s3vectors/vector_bucket.go) lists the indexes and deletes each index; it calls
        # neither ListVectors nor DeleteVectors, so no vector-level action is granted (ListIndexes and DeleteIndex are below).
        Sid    = "S3VectorsBucketAndIndexes"
        Effect = "Allow"
        Action = [
          "s3vectors:CreateVectorBucket", "s3vectors:GetVectorBucket", "s3vectors:DeleteVectorBucket",
          "s3vectors:PutVectorBucketPolicy", "s3vectors:GetVectorBucketPolicy", "s3vectors:DeleteVectorBucketPolicy",
          "s3vectors:CreateIndex", "s3vectors:GetIndex", "s3vectors:DeleteIndex", "s3vectors:ListIndexes",
          "s3vectors:TagResource", "s3vectors:UntagResource", "s3vectors:ListTagsForResource",
        ]
        Resource  = ["${local.m_arn_s3v}:bucket/${local.mp}-${local.acct}-vectors", "${local.m_arn_s3v}:bucket/${local.mp}-${local.acct}-vectors/index/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "DynamoDbTables"
        Effect = "Allow"
        Action = [
          "dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:DescribeTable", "dynamodb:UpdateTable",
          "dynamodb:DescribeTimeToLive", "dynamodb:UpdateTimeToLive", "dynamodb:DescribeContinuousBackups",
          "dynamodb:UpdateContinuousBackups", "dynamodb:DescribeKinesisStreamingDestination",
          "dynamodb:DescribeTableReplicaAutoScaling", "dynamodb:ListTagsOfResource", "dynamodb:TagResource",
          "dynamodb:UntagResource",
        ]
        Resource  = ["${local.m_arn_ddb}:table/${local.mp}-*", "${local.m_arn_ddb}:table/${local.mp}-*/index/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "SqsQueues"
        Effect = "Allow"
        Action = [
          "sqs:CreateQueue", "sqs:DeleteQueue", "sqs:GetQueueAttributes", "sqs:SetQueueAttributes",
          "sqs:GetQueueUrl", "sqs:ListQueueTags", "sqs:TagQueue", "sqs:UntagQueue",
        ]
        Resource  = ["${local.m_arn_sqs}:${local.mp}-*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "StepFunctionsStateMachine"
        Effect = "Allow"
        Action = [
          "states:CreateStateMachine", "states:DeleteStateMachine", "states:DescribeStateMachine",
          "states:UpdateStateMachine", "states:ListStateMachineVersions", "states:ListTagsForResource",
          "states:TagResource", "states:UntagResource",
        ]
        Resource  = ["${local.m_arn_sfn}:stateMachine:${local.mp}-*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "NeptuneClusterInstanceGroupsOfTheMainStack"
        Effect = "Allow"
        Action = [
          "rds:CreateDBCluster", "rds:ModifyDBCluster", "rds:DeleteDBCluster", "rds:AddRoleToDBCluster",
          "rds:RemoveRoleFromDBCluster", "rds:CreateDBClusterSnapshot", "rds:CreateDBInstance",
          "rds:ModifyDBInstance", "rds:DeleteDBInstance", "rds:CreateDBSubnetGroup", "rds:ModifyDBSubnetGroup",
          "rds:DeleteDBSubnetGroup", "rds:CreateDBClusterParameterGroup", "rds:ModifyDBClusterParameterGroup",
          "rds:ResetDBClusterParameterGroup", "rds:DeleteDBClusterParameterGroup", "rds:CreateDBParameterGroup",
          "rds:ModifyDBParameterGroup", "rds:ResetDBParameterGroup", "rds:DeleteDBParameterGroup",
          "rds:AddTagsToResource", "rds:RemoveTagsFromResource", "rds:ListTagsForResource",
        ]
        Resource = [
          "${local.m_arn_rds}:cluster:${local.mp}-*", "${local.m_arn_rds}:db:${local.mp}-*",
          "${local.m_arn_rds}:subgrp:${local.mp}-*", "${local.m_arn_rds}:cluster-pg:${local.mp}-*",
          "${local.m_arn_rds}:pg:${local.mp}-*", "${local.m_arn_rds}:cluster-snapshot:${local.mp}-*",
        ]
        Condition = { StringEquals = local.c_region }
      },
      {
        # rds describe calls are list-style (the provider filters by identifier or lists): honest list.
        Sid    = "RdsDescribeNoResourceScoping"
        Effect = "Allow"
        Action = [
          "rds:DescribeDBClusters", "rds:DescribeDBInstances", "rds:DescribeDBSubnetGroups",
          "rds:DescribeDBClusterParameterGroups", "rds:DescribeDBClusterParameters",
          "rds:DescribeDBParameterGroups", "rds:DescribeDBParameters", "rds:DescribeDBClusterSnapshots",
          "rds:DescribeDBEngineVersions", "rds:DescribeGlobalClusters",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
    ]
  }

  # ---- document 3: KMS, ACM certificate lifecycle, Secrets Manager metadata, CloudWatch (logs, alarms, dashboards), tag inventory ----
  m14_keys_obs = {
    Version = "2012-10-17"
    Statement = [
      {
        # kms:CreateKey has no resource type; only the request tags scope it.
        Sid       = "KmsCreateKeyWithProjectTags"
        Effect    = "Allow"
        Action    = ["kms:CreateKey"]
        Resource  = ["*"]
        Condition = { StringEquals = merge(local.c_region, local.c_req_main) }
      },
      {
        # CreateKey with Tags needs kms:TagResource in an IAM policy, because the key and its key policy do not exist yet; AWS says the
        # permission "must cover all KMS keys in the account and Region" (https://docs.aws.amazon.com/kms/latest/developerguide/add-tags.html).
        # That is as narrow as AWS allows, so it is narrowed by request tags and the tag-key list. Tags confer nothing here: since
        # repair round 1 (F2) no IAM statement grants anything on a key by tag; administration, use and grants of the main-stack keys
        # are in each key's own policy (modules/identity/main.tf), which names this role. Residual: a foreign key can receive or have
        # these tag keys overwritten.
        Sid      = "KmsTagWithProjectTags"
        Effect   = "Allow"
        Action   = ["kms:TagResource"]
        Resource = ["${local.arn_kms}:key/*"]
        Condition = {
          StringEquals                = merge(local.c_region, local.c_req_main)
          "ForAllValues:StringEquals" = { "aws:TagKeys" = var.main_tag_keys }
        }
      },
      {
        Sid       = "KmsAliasesOfTheMainStack"
        Effect    = "Allow"
        Action    = ["kms:CreateAlias", "kms:UpdateAlias", "kms:DeleteAlias"]
        Resource  = ["${local.arn_kms}:alias/${local.mp}-*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # kms:ListAliases has no resource type (the provider reads an alias by listing).
        Sid       = "KmsListAliasesNoResourceType"
        Effect    = "Allow"
        Action    = ["kms:ListAliases"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Metadata only: confirms the human-created secrets exist. The values are never readable (explicit Deny in the iam
        # document); Terraform reads no secret (the ARNs are variables).
        Sid       = "SecretsManagerMetadataOnly"
        Effect    = "Allow"
        Action    = ["secretsmanager:DescribeSecret", "secretsmanager:GetResourcePolicy"]
        Resource  = ["${local.m_arn_secret}:secret:*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Replan W5a: the HTTPS certificate of the main root (one aws_acm_certificate, DNS validation, base-apply). RequestCertificate has
        # no resource type, so region, DNS validation (the Cloudflare CNAME is added by hand) and the request tags scope it; the
        # acm:DomainNames key is left open because the domain is a private tfvars value the deployer must not know. The Service
        # Authorization Reference lists these ACM condition keys: acm:CertificateAuthority, CertificateKeyPairOrigin,
        # CertificateTransparencyLogging, DomainNames, Export, KeyAlgorithm, ValidationMethod, aws:RequestTag, aws:ResourceTag, aws:TagKeys.
        # https://docs.aws.amazon.com/service-authorization/latest/reference/list_acm.html
        Sid       = "AcmRequestCertificateDnsValidationWithProjectTags"
        Effect    = "Allow"
        Action    = ["acm:RequestCertificate"]
        Resource  = ["*"]
        Condition = { StringEquals = merge(local.c_region, local.c_req_main, { "acm:ValidationMethod" = "DNS" }) }
      },
      {
        # RequestCertificate with tags is authorized as acm:AddTagsToCertificate against a certificate that does not exist yet, so
        # only the request tags and the tag-key list can scope it (the same shape as KmsTagWithProjectTags). Residual: a foreign
        # certificate in this account can be given these tag keys and then falls under the tag-scoped statement below.
        Sid      = "AcmTagOnCreateWithProjectTags"
        Effect   = "Allow"
        Action   = ["acm:AddTagsToCertificate"]
        Resource = ["${local.arn_acm}:certificate/*"]
        Condition = {
          StringEquals                = merge(local.c_region, local.c_req_main)
          "ForAllValues:StringEquals" = { "aws:TagKeys" = var.main_tag_keys }
        }
      },
      {
        # Read tags, retag, remove tags and delete only certificates that already carry the project tags. DescribeCertificate is
        # already allowed read-only on all certificates by ElbDescribeNoResourceScoping. ListCertificates is not needed by the
        # aws_acm_certificate resource (the data source uses it) and is not granted.
        Sid    = "AcmManageProjectTaggedCertificates"
        Effect = "Allow"
        Action = [
          "acm:DeleteCertificate", "acm:ListTagsForCertificate", "acm:AddTagsToCertificate", "acm:RemoveTagsFromCertificate",
        ]
        Resource  = ["${local.arn_acm}:certificate/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        Sid    = "LogGroupsOfTheMainStack"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy",
          "logs:ListTagsForResource", "logs:ListTagsLogGroup", "logs:TagResource", "logs:UntagResource",
          "logs:TagLogGroup", "logs:UntagLogGroup",
        ]
        Resource = [
          "${local.m_arn_logs}:log-group:/${local.mp}/*", "${local.m_arn_logs}:log-group:/${local.mp}/*:*",
          "${local.m_arn_logs}:log-group:/aws/neptune/${local.mp}-*", "${local.m_arn_logs}:log-group:/aws/neptune/${local.mp}-*:*",
        ]
        Condition = { StringEquals = local.c_region }
      },
      {
        # DescribeLogGroups is a list call authorized on log-group:* (honest list).
        Sid       = "LogsDescribeNoNameScoping"
        Effect    = "Allow"
        Action    = ["logs:DescribeLogGroups"]
        Resource  = ["${local.m_arn_logs}:log-group:*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "CloudWatchAlarmsDashboardsOfTheMainStack"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms",
          "cloudwatch:ListTagsForResource", "cloudwatch:TagResource", "cloudwatch:UntagResource",
          "cloudwatch:PutDashboard", "cloudwatch:GetDashboard", "cloudwatch:DeleteDashboards",
        ]
        Resource = [
          "${local.m_arn_cw}:alarm:${local.mp}-*", "${local.m_arn_cw}:alarm:TargetTracking-*",
          "arn:aws:cloudwatch::${local.acct}:dashboard/${local.mp}-*",
        ]
        Condition = { StringEquals = local.c_region }
      },
      {
        # List-style reads without a usable resource scope (alarms are read by name, dashboards are listed).
        Sid       = "CloudWatchReadNoResourceScoping"
        Effect    = "Allow"
        Action    = ["cloudwatch:DescribeAlarms", "cloudwatch:ListDashboards"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },

      {
        # scripts/cleanup.sh inventory; the Service Authorization Reference lists no resource type.
        Sid       = "TagInventoryNoResourceType"
        Effect    = "Allow"
        Action    = ["tag:GetResources"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
    ]
  }

  # ---- document 4: compute (ECS, ECR, ALB, Cloud Map, Application Auto Scaling) -------------------------------------
  m14_compute = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EcsClusterAndServicesOfTheMainStack"
        Effect = "Allow"
        Action = [
          "ecs:CreateCluster", "ecs:DeleteCluster", "ecs:DescribeClusters", "ecs:UpdateCluster",
          "ecs:UpdateClusterSettings", "ecs:CreateService", "ecs:UpdateService", "ecs:DeleteService",
          "ecs:DescribeServices", "ecs:TagResource", "ecs:UntagResource", "ecs:ListTagsForResource",
        ]
        Resource  = ["${local.m_arn_ecs}:cluster/${local.mp}", "${local.m_arn_ecs}:service/${local.mp}/*", "${local.m_arn_ecs}:task-definition/${local.mp}-*:*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # RegisterTaskDefinition, DeregisterTaskDefinition, DescribeTaskDefinition and DeleteTaskDefinitions do not take a
        # resource type that can carry the family name for every call (honest list); registering needs the request tags.
        Sid       = "EcsRegisterTaskDefinitionWithProjectTags"
        Effect    = "Allow"
        Action    = ["ecs:RegisterTaskDefinition"]
        Resource  = ["*"]
        Condition = { StringEquals = merge(local.c_region, local.c_req_main) }
      },
      {
        Sid       = "EcsTaskDefinitionLifecycleNoResourceType"
        Effect    = "Allow"
        Action    = ["ecs:DeregisterTaskDefinition", "ecs:DescribeTaskDefinition", "ecs:DeleteTaskDefinitions"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "EcrRepositoriesOfTheMainStack"
        Effect = "Allow"
        Action = [
          "ecr:CreateRepository", "ecr:DeleteRepository", "ecr:DescribeRepositories", "ecr:ListTagsForResource",
          "ecr:TagResource", "ecr:UntagResource", "ecr:PutImageTagMutability", "ecr:PutImageScanningConfiguration",
          "ecr:GetRepositoryPolicy", "ecr:GetLifecyclePolicy",
        ]
        Resource  = ["${local.m_arn_ecr}:repository/${local.mp}/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # scripts/deploy.sh push stage (docker login, docker push by commit SHA, digest verification).
        Sid    = "EcrPushAndVerifyImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:DescribeImages", "ecr:ListImages",
        ]
        Resource  = ["${local.m_arn_ecr}:repository/${local.mp}/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # ecr:GetAuthorizationToken does not support resource-level permissions.
        Sid       = "EcrAuthorizationTokenNoResourceType"
        Effect    = "Allow"
        Action    = ["ecr:GetAuthorizationToken"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "ElbLoadBalancerListenerTargetGroup"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:CreateLoadBalancer", "elasticloadbalancing:DeleteLoadBalancer",
          "elasticloadbalancing:ModifyLoadBalancerAttributes", "elasticloadbalancing:SetSecurityGroups",
          "elasticloadbalancing:SetSubnets", "elasticloadbalancing:CreateTargetGroup",
          "elasticloadbalancing:DeleteTargetGroup", "elasticloadbalancing:ModifyTargetGroup",
          "elasticloadbalancing:ModifyTargetGroupAttributes", "elasticloadbalancing:CreateListener",
          "elasticloadbalancing:DeleteListener", "elasticloadbalancing:ModifyListener",
          "elasticloadbalancing:ModifyListenerAttributes", "elasticloadbalancing:AddTags",
          "elasticloadbalancing:RemoveTags",
        ]
        Resource = [
          "${local.m_arn_elb}:loadbalancer/app/${local.mp}-*/*", "${local.m_arn_elb}:targetgroup/${local.mp}-*/*",
          "${local.m_arn_elb}:listener/app/${local.mp}-*/*/*",
        ]
        Condition = { StringEquals = local.c_region }
      },
      {
        # The Elastic Load Balancing v2 describe calls are list-style and take no name-scoped resource (honest list).
        Sid    = "ElbDescribeNoResourceScoping"
        Effect = "Allow"
        Action = [
          "elasticloadbalancing:DescribeLoadBalancers", "elasticloadbalancing:DescribeLoadBalancerAttributes",
          "elasticloadbalancing:DescribeTargetGroups", "elasticloadbalancing:DescribeTargetGroupAttributes",
          "elasticloadbalancing:DescribeListeners", "elasticloadbalancing:DescribeListenerAttributes",
          "elasticloadbalancing:DescribeTags", "elasticloadbalancing:DescribeTargetHealth", "elasticloadbalancing:DescribeCapacityReservation",
          "acm:DescribeCertificate",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "AppAutoScalingEcsServices"
        Effect = "Allow"
        Action = [
          "application-autoscaling:RegisterScalableTarget", "application-autoscaling:DeregisterScalableTarget",
          "application-autoscaling:PutScalingPolicy", "application-autoscaling:DeleteScalingPolicy",
          "application-autoscaling:TagResource", "application-autoscaling:UntagResource",
          "application-autoscaling:ListTagsForResource",
        ]
        Resource  = ["${local.m_arn_aas}:scalable-target/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "AppAutoScalingAndCloudMapReadNoResourceScoping"
        Effect = "Allow"
        Action = [
          "servicediscovery:GetOperation", "application-autoscaling:DescribeScalableTargets", "application-autoscaling:DescribeScalingPolicies",
          "application-autoscaling:DescribeScalingActivities",
        ]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        Sid    = "CloudMapNamespaceAndServices"
        Effect = "Allow"
        Action = [
          "servicediscovery:CreatePrivateDnsNamespace", "servicediscovery:DeleteNamespace",
          "servicediscovery:GetNamespace", "servicediscovery:CreateService",
          "servicediscovery:UpdateService", "servicediscovery:DeleteService", "servicediscovery:GetService",
          "servicediscovery:TagResource", "servicediscovery:UntagResource", "servicediscovery:ListTagsForResource",
        ]
        Resource  = ["${local.m_arn_sd}:namespace/*", "${local.m_arn_sd}:service/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # Cloud Map creates and deletes the Route 53 private hosted zone with the caller's permissions (Cloud Map identity
        # policy examples). Route 53 is global: hosted-zone IDs are unknown before creation, so no name or tag scope.
        Sid    = "Route53PrivateZoneForCloudMapNoScoping"
        Effect = "Allow"
        Action = [
          "route53:CreateHostedZone", "route53:GetHostedZone", "route53:ListHostedZonesByName",
          "route53:DeleteHostedZone", "route53:ChangeResourceRecordSets", "route53:ListResourceRecordSets",
          "route53:GetChange", "route53:ListTagsForResource", "route53:ChangeTagsForResource",
        ]
        Resource = ["*"]
      },
    ]
  }

  # ---- document 6: EMR and the EFS staging file system --------------------------------------------------------------
  m14_emr_efs = {
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EmrSecurityConfigurationsNoResourceType"
        Effect    = "Allow"
        Action    = ["elasticmapreduce:CreateSecurityConfiguration", "elasticmapreduce:DeleteSecurityConfiguration", "elasticmapreduce:DescribeSecurityConfiguration", "elasticmapreduce:ListSecurityConfigurations", "elasticmapreduce:ListClusters"]
        Resource  = ["*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # RunJobFlow has no resource type (list_emr); the request tags scope it. The cluster's tags are set by Terraform.
        Sid      = "EmrRunJobFlowRequireProjectTags"
        Effect   = "Allow"
        Action   = ["elasticmapreduce:RunJobFlow"]
        Resource = ["*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_main, {
            "aws:RequestTag/scholarchain:stack"                       = var.main_emr_stack_tag_value
            "aws:RequestTag/for-use-with-amazon-emr-managed-policies" = "true"
          })
        }
      },
      {
        Sid    = "EmrManageProjectClusters"
        Effect = "Allow"
        Action = [
          "elasticmapreduce:AddTags", "elasticmapreduce:RemoveTags", "elasticmapreduce:DescribeCluster",
          "elasticmapreduce:ListInstanceGroups", "elasticmapreduce:ListInstanceFleets", "elasticmapreduce:ListInstances",
          "elasticmapreduce:ListBootstrapActions", "elasticmapreduce:ListSteps", "elasticmapreduce:DescribeStep",
          "elasticmapreduce:GetAutoTerminationPolicy", "elasticmapreduce:PutAutoTerminationPolicy",
          "elasticmapreduce:RemoveAutoTerminationPolicy", "elasticmapreduce:GetManagedScalingPolicy",
          "elasticmapreduce:PutManagedScalingPolicy", "elasticmapreduce:RemoveManagedScalingPolicy",
          "elasticmapreduce:AddInstanceGroups", "elasticmapreduce:ModifyInstanceGroups",
          "elasticmapreduce:ModifyCluster", "elasticmapreduce:SetTerminationProtection",
          "elasticmapreduce:SetUnhealthyNodeReplacement", "elasticmapreduce:SetVisibleToAllUsers",
          "elasticmapreduce:TerminateJobFlows",
        ]
        Resource  = ["arn:aws:elasticmapreduce:${local.region}:${local.acct}:cluster/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        Sid    = "EfsDescribeInRegion"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:DescribeFileSystems", "elasticfilesystem:DescribeMountTargets",
          "elasticfilesystem:DescribeAccessPoints",
        ]
        Resource  = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = { StringEquals = local.c_region }
      },
      {
        # CreateAccessPoint is authorized on the existing file system only: both the resource tag and the request tags.
        Sid       = "EfsCreateFileSystemAndAccessPointWithProjectTags"
        Effect    = "Allow"
        Action    = ["elasticfilesystem:CreateFileSystem", "elasticfilesystem:CreateAccessPoint"]
        Resource  = ["${local.arn_efs}:file-system/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_req_main) }
      },
      {
        Sid       = "EfsAccessPointOnProjectFileSystem"
        Effect    = "Allow"
        Action    = ["elasticfilesystem:CreateAccessPoint"]
        Resource  = ["${local.arn_efs}:file-system/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        Sid      = "EfsTagOnCreateOnly"
        Effect   = "Allow"
        Action   = ["elasticfilesystem:TagResource"]
        Resource = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = {
          StringEquals = merge(local.c_region, local.c_req_main, { "elasticfilesystem:CreateAction" = ["CreateFileSystem", "CreateAccessPoint"] })
        }
      },
      {
        Sid    = "EfsManageProjectResources"
        Effect = "Allow"
        Action = [
          "elasticfilesystem:DeleteFileSystem", "elasticfilesystem:DeleteAccessPoint", "elasticfilesystem:CreateMountTarget",
          "elasticfilesystem:DeleteMountTarget", "elasticfilesystem:DescribeMountTargetSecurityGroups",
          "elasticfilesystem:ModifyMountTargetSecurityGroups", "elasticfilesystem:DescribeLifecycleConfiguration",
          "elasticfilesystem:DescribeBackupPolicy", "elasticfilesystem:PutBackupPolicy",
          "elasticfilesystem:DescribeFileSystemPolicy", "elasticfilesystem:PutFileSystemPolicy",
          "elasticfilesystem:DeleteFileSystemPolicy", "elasticfilesystem:UpdateFileSystem",
          "elasticfilesystem:ListTagsForResource", "elasticfilesystem:UntagResource",
        ]
        Resource  = ["${local.arn_efs}:file-system/*", "${local.arn_efs}:access-point/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        Sid       = "EfsMountTargetSubnetAndGroup"
        Effect    = "Allow"
        Action    = ["ec2:CreateNetworkInterface"]
        Resource  = ["${local.arn_ec2}:subnet/*", "${local.arn_ec2}:security-group/*"]
        Condition = { StringEquals = merge(local.c_region, local.c_res_main) }
      },
      {
        # The ENI is created by the EFS mount-target call and carries no project tag yet: region-only (honest list).
        Sid       = "EfsMountTargetNetworkInterfaceUntagged"
        Effect    = "Allow"
        Action    = ["ec2:CreateNetworkInterface", "ec2:DeleteNetworkInterface", "ec2:ModifyNetworkInterfaceAttribute"]
        Resource  = ["${local.arn_ec2}:network-interface/*"]
        Condition = { StringEquals = local.c_region }
      },
    ]
  }

  # ---- document 7: IAM for scholarchain-<environment>-* roles, boundary protections, service-linked roles -------------
  m14_iam = {
    Version = "2012-10-17"
    Statement = [
      {
        # The runtime roles (tasks, executions, Neptune loader, EMR instance, producer, deployment) carry the runtime boundary.
        Sid      = "CreateRuntimeRolesOnlyWithRuntimeBoundary"
        Effect   = "Allow"
        Action   = ["iam:CreateRole"]
        Resource = [for r in ["*-task", "*-execution", "neptune-loader", "emr-ec2", "embedding-producer", "deployment"] : "${local.arn_iam}:role/${local.mp}-${r}"]
        Condition = {
          StringEquals = merge(local.c_req_main, { "iam:PermissionsBoundary" = local.m_boundary_runtime_arn })
        }
      },
      {
        Sid      = "CreateEmrServiceRoleOnlyWithEmrBoundary"
        Effect   = "Allow"
        Action   = ["iam:CreateRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-emr-service"]
        Condition = {
          StringEquals = merge(local.c_req_main, { "iam:PermissionsBoundary" = local.m_boundary_emr_arn })
        }
      },
      {
        Sid       = "TagMainRolesWithProjectTags"
        Effect    = "Allow"
        Action    = ["iam:TagRole"]
        Resource  = local.m_role_arns
        Condition = { StringEquals = local.c_req_main }
      },
      {
        Sid      = "RolePoliciesOnBoundedMainRolesOnly"
        Effect   = "Allow"
        Action   = ["iam:PutRolePolicy", "iam:DeleteRolePolicy"]
        Resource = local.m_role_arns
        Condition = {
          StringEquals = { "iam:PermissionsBoundary" = local.m_boundary_arns }
        }
      },
      {
        Sid    = "ReadUpdateDeleteMainRoles"
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:DeleteRole", "iam:UpdateRole", "iam:UpdateRoleDescription", "iam:UntagRole",
          "iam:GetRolePolicy", "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
          "iam:ListInstanceProfilesForRole", "iam:ListRoleTags",
        ]
        Resource = local.m_role_arns
      },
      {
        Sid    = "ManageMainInstanceProfile"
        Effect = "Allow"
        Action = [
          "iam:CreateInstanceProfile", "iam:DeleteInstanceProfile", "iam:GetInstanceProfile",
          "iam:AddRoleToInstanceProfile", "iam:RemoveRoleFromInstanceProfile", "iam:TagInstanceProfile",
          "iam:UntagInstanceProfile", "iam:ListInstanceProfileTags",
        ]
        Resource = ["${local.arn_iam}:instance-profile/${local.mp}-*"]
      },
      {
        Sid      = "PassRoleToEcsTasks"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-*-task", "${local.arn_iam}:role/${local.mp}-*-execution"]
        Condition = {
          StringEquals = { "iam:PassedToService" = ["ecs-tasks.amazonaws.com"] }
        }
      },
      {
        Sid      = "PassRoleToEmr"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-emr-service"]
        Condition = {
          StringEquals = { "iam:PassedToService" = ["elasticmapreduce.amazonaws.com"] }
        }
      },
      {
        Sid      = "PassRoleToEc2InstanceProfile"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-emr-ec2"]
        Condition = {
          StringEquals = { "iam:PassedToService" = ["ec2.amazonaws.com"] }
        }
      },
      {
        Sid      = "PassRoleToNeptune"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-neptune-loader"]
        Condition = {
          StringEquals = { "iam:PassedToService" = ["rds.amazonaws.com"] }
        }
      },
      {
        Sid      = "PassRoleToStepFunctions"
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = ["${local.arn_iam}:role/${local.mp}-embedding-producer"]
        Condition = {
          StringEquals = { "iam:PassedToService" = ["states.amazonaws.com"] }
        }
      },
      {
        # The boundaries are immutable for this role: no new version, no default switch, no deletion.
        Sid      = "DenyBoundaryPolicyMutation"
        Effect   = "Deny"
        Action   = ["iam:CreatePolicyVersion", "iam:SetDefaultPolicyVersion", "iam:DeletePolicy", "iam:DeletePolicyVersion"]
        Resource = local.m_boundary_arns
      },
      {
        # No boundary can be replaced or removed, no trust policy rewritten, and the deployer never assumes a main role.
        Sid      = "DenyBoundaryRemovalAndTrustChangeOnMainRoles"
        Effect   = "Deny"
        Action   = ["iam:PutRolePermissionsBoundary", "iam:DeleteRolePermissionsBoundary", "iam:UpdateAssumeRolePolicy"]
        Resource = local.m_role_arns
      },
      {
        Sid      = "DenyAssumingMainRoles"
        Effect   = "Deny"
        Action   = ["sts:AssumeRole"]
        Resource = local.m_role_arns
      },
      {
        # The values stay readable only to the services. Nothing in this role can read a secret value.
        Sid      = "DenyReadingSecretValues"
        Effect   = "Deny"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:BatchGetSecretValue"]
        Resource = ["*"]
      },
      {
        Sid    = "CreateRequiredServiceLinkedRolesOnly"
        Effect = "Allow"
        Action = ["iam:CreateServiceLinkedRole"]
        Resource = [
          "${local.arn_iam}:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
          "${local.arn_iam}:role/aws-service-role/ecs.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_ECSService",
          "${local.arn_iam}:role/aws-service-role/elasticloadbalancing.amazonaws.com/AWSServiceRoleForElasticLoadBalancing",
          "${local.arn_iam}:role/aws-service-role/rds.amazonaws.com/AWSServiceRoleForRDS",
          "${local.arn_iam}:role/aws-service-role/elasticmapreduce.amazonaws.com/AWSServiceRoleForEMRCleanup",
          "${local.arn_iam}:role/aws-service-role/elasticfilesystem.amazonaws.com/AWSServiceRoleForAmazonElasticFileSystem",
        ]
        Condition = {
          StringEquals = {
            "iam:AWSServiceName" = [
              "ecs.amazonaws.com", "ecs.application-autoscaling.amazonaws.com", "elasticloadbalancing.amazonaws.com",
              "rds.amazonaws.com", "elasticmapreduce.amazonaws.com", "elasticfilesystem.amazonaws.com",
            ]
          }
        }
      },
    ]
  }


  # ---- the two permissions boundaries (ceilings for the roles the main root creates) ---------------------------------
  # The documents live in boundaries/*.json.tftpl so that ONE source serves two readers: this root (it creates the policies)
  # and the main root's tests (infra/terraform/tests/phase14a.tftest.hcl renders the same files and asserts that every action of
  # every role policy is inside the role's boundary). Runtime: the union of what modules/identity and modules/workflow grant, at the
  # same resource patterns; a role's effective permission is the intersection with its own inline policy, so this only bounds a
  # mistake. EMR service: AmazonEMRServicePolicy_v2 (EC2 parts the cluster uses) mirrored with the project tags, the instance-role
  # PassRole the supplied policy must add, and the project-key grants of modules/identity emr_disk_encryption.
  # https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonEMRServicePolicy_v2.html
  m_boundary_vars = {
    acct            = local.acct
    region          = local.region
    mp              = local.mp
    env             = var.main_environment
    bedrock_fm_arns = join(", ", [for r in var.main_bedrock_regions : jsonencode("arn:aws:bedrock:${r}::foundation-model/*")])
  }
  m14_boundary_runtime = jsondecode(templatefile("${path.module}/boundaries/runtime.json.tftpl", local.m_boundary_vars))
  m14_boundary_emr     = jsondecode(templatefile("${path.module}/boundaries/emr-service.json.tftpl", local.m_boundary_vars))
}
