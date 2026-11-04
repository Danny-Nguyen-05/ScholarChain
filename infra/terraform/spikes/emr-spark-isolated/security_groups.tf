# Custom EMR-managed security groups for a private subnet. EMR adds the same
# required inbound rules itself at launch; declaring them here keeps the plan
# complete. revoke_rules_on_delete breaks the primary/core cross references
# that EMR adds so the groups can be deleted.
# Reference: https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-man-sec-groups.html

resource "aws_security_group" "primary" {
  name                   = "${local.prefix}-primary"
  description            = "EMR managed primary (private subnet); no SSH, no public ingress"
  vpc_id                 = aws_vpc.spike.id
  revoke_rules_on_delete = true
  tags                   = { Name = "${local.prefix}-primary" }
}

resource "aws_security_group" "core" {
  name                   = "${local.prefix}-core"
  description            = "EMR managed core (private subnet); no SSH, no public ingress"
  vpc_id                 = aws_vpc.spike.id
  revoke_rules_on_delete = true
  tags                   = { Name = "${local.prefix}-core" }
}

resource "aws_security_group" "service_access" {
  name                   = "${local.prefix}-service-access"
  description            = "EMR service access for private subnets"
  vpc_id                 = aws_vpc.spike.id
  revoke_rules_on_delete = true
  tags                   = { Name = "${local.prefix}-service-access" }
}

resource "aws_security_group" "efs" {
  name                   = "${local.prefix}-efs"
  description            = "NFS 2049 from the EMR primary and core groups only"
  vpc_id                 = aws_vpc.spike.id
  revoke_rules_on_delete = true
  tags                   = { Name = "${local.prefix}-efs" }
}

# primary: intra-cluster traffic plus cluster-manager 8443
resource "aws_vpc_security_group_ingress_rule" "primary_self" {
  security_group_id            = aws_security_group.primary.id
  referenced_security_group_id = aws_security_group.primary.id
  ip_protocol                  = "-1"
  description                  = "all traffic within the primary group"
}

resource "aws_vpc_security_group_ingress_rule" "primary_from_core" {
  security_group_id            = aws_security_group.primary.id
  referenced_security_group_id = aws_security_group.core.id
  ip_protocol                  = "-1"
  description                  = "all traffic from the core group"
}

resource "aws_vpc_security_group_ingress_rule" "primary_from_service_access" {
  security_group_id            = aws_security_group.primary.id
  referenced_security_group_id = aws_security_group.service_access.id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  description                  = "cluster manager to primary (EMR 7.x and earlier)"
}

resource "aws_vpc_security_group_egress_rule" "primary_all" {
  security_group_id = aws_security_group.primary.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "outbound via NAT and the S3 gateway endpoint"
}

# core
resource "aws_vpc_security_group_ingress_rule" "core_self" {
  security_group_id            = aws_security_group.core.id
  referenced_security_group_id = aws_security_group.core.id
  ip_protocol                  = "-1"
  description                  = "all traffic within the core group"
}

resource "aws_vpc_security_group_ingress_rule" "core_from_primary" {
  security_group_id            = aws_security_group.core.id
  referenced_security_group_id = aws_security_group.primary.id
  ip_protocol                  = "-1"
  description                  = "all traffic from the primary group"
}

resource "aws_vpc_security_group_ingress_rule" "core_from_service_access" {
  security_group_id            = aws_security_group.core.id
  referenced_security_group_id = aws_security_group.service_access.id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  description                  = "cluster manager to core (EMR 7.x and earlier)"
}

resource "aws_vpc_security_group_egress_rule" "core_all" {
  security_group_id = aws_security_group.core.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "outbound via NAT and the S3 gateway endpoint"
}

# service access: 9443 in from the primary group; 8443 out to primary and core
resource "aws_vpc_security_group_ingress_rule" "service_access_from_primary" {
  security_group_id            = aws_security_group.service_access.id
  referenced_security_group_id = aws_security_group.primary.id
  ip_protocol                  = "tcp"
  from_port                    = 9443
  to_port                      = 9443
  description                  = "primary to service access (EMR 5.30 to 7.x)"
}

resource "aws_vpc_security_group_egress_rule" "service_access_to_primary" {
  security_group_id            = aws_security_group.service_access.id
  referenced_security_group_id = aws_security_group.primary.id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  description                  = "cluster manager to primary"
}

resource "aws_vpc_security_group_egress_rule" "service_access_to_core" {
  security_group_id            = aws_security_group.service_access.id
  referenced_security_group_id = aws_security_group.core.id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  description                  = "cluster manager to core"
}

# EFS: NFS only from the two EMR groups
resource "aws_vpc_security_group_ingress_rule" "efs_from_primary" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.primary.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  description                  = "NFS from the EMR primary group"
}

resource "aws_vpc_security_group_ingress_rule" "efs_from_core" {
  security_group_id            = aws_security_group.efs.id
  referenced_security_group_id = aws_security_group.core.id
  ip_protocol                  = "tcp"
  from_port                    = 2049
  to_port                      = 2049
  description                  = "NFS from the EMR core group"
}
