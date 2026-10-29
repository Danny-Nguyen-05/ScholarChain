locals {
  azs   = { for i, az in var.availability_zones : tostring(i) => az }
  roles = toset(["alb", "query-api", "graph-service", "semantic-service", "embedding-worker", "neptune", "endpoints", "emr"])
  # Service SG references express the permitted dependency graph, never VPC CIDRs.
  connections = {
    alb_query      = { from = "alb", to = "query-api", port = var.service_port }
    query_graph    = { from = "query-api", to = "graph-service", port = var.service_port }
    query_semantic = { from = "query-api", to = "semantic-service", port = var.service_port }
    graph_neptune  = { from = "graph-service", to = "neptune", port = var.neptune_port }
  }
  https_clients = toset(["query-api", "graph-service", "semantic-service", "embedding-worker", "emr"])
}
resource "aws_vpc" "course" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(var.tags, { Name = var.name_prefix })
}
resource "aws_default_security_group" "closed" {
  vpc_id = aws_vpc.course.id
  # Revoke AWS's permissive default group rules; no workload uses this group.
  tags = merge(var.tags, { Name = "${var.name_prefix}-default-unused" })
}
resource "aws_internet_gateway" "course" {
  vpc_id = aws_vpc.course.id
  tags   = var.tags
}
resource "aws_subnet" "public" {
  for_each                = local.azs
  vpc_id                  = aws_vpc.course.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, tonumber(each.key))
  map_public_ip_on_launch = false
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-public-${each.key}", tier = "public" })
}
resource "aws_subnet" "application" {
  for_each                = local.azs
  vpc_id                  = aws_vpc.course.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 10 + tonumber(each.key))
  map_public_ip_on_launch = false
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-app-${each.key}", tier = "application" })
}
resource "aws_subnet" "data" {
  for_each                = local.azs
  vpc_id                  = aws_vpc.course.id
  availability_zone       = each.value
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 20 + tonumber(each.key))
  map_public_ip_on_launch = false
  tags                    = merge(var.tags, { Name = "${var.name_prefix}-data-${each.key}", tier = "data" })
}
resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = var.tags
}
resource "aws_nat_gateway" "course" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["0"].id
  tags          = var.tags
  depends_on    = [aws_internet_gateway.course]
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.course.id
  tags   = merge(var.tags, { tier = "public" })
}
resource "aws_route_table" "application" {
  vpc_id = aws_vpc.course.id
  tags   = merge(var.tags, { tier = "application" })
}
resource "aws_route_table" "data" {
  vpc_id = aws_vpc.course.id
  tags   = merge(var.tags, { tier = "data" })
  # No internet/NAT default route in data subnets.
}
# All authored routes live in this collection. The native test enforces one
# aws_route declaration and no inline route-table routes, so a new route cannot
# bypass the resource-backed data-isolation control through another declaration.
locals {
  default_routes = {
    public = {
      route_table_id = aws_route_table.public.id
      gateway_id     = aws_internet_gateway.course.id
      nat_gateway_id = null
    }
    application = {
      route_table_id = aws_route_table.application.id
      gateway_id     = null
      nat_gateway_id = aws_nat_gateway.course.id
    }
  }
}
resource "aws_route" "default" {
  for_each               = local.default_routes
  route_table_id         = each.value.route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = each.value.gateway_id
  nat_gateway_id         = each.value.nat_gateway_id
}
resource "aws_route_table_association" "public" {
  for_each       = aws_subnet.public
  subnet_id      = each.value.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table_association" "application" {
  for_each       = aws_subnet.application
  subnet_id      = each.value.id
  route_table_id = aws_route_table.application.id
}
resource "aws_route_table_association" "data" {
  for_each       = aws_subnet.data
  subnet_id      = each.value.id
  route_table_id = aws_route_table.data.id
}
resource "aws_vpc_endpoint" "gateway" {
  for_each          = toset(["s3", "dynamodb"])
  vpc_id            = aws_vpc.course.id
  service_name      = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.application.id, aws_route_table.data.id]
  tags              = var.tags
  # Identity and bucket/table policies remain the authorization boundary. The
  # gateway's default endpoint policy does not itself grant IAM permissions.
}
resource "aws_security_group" "role" {
  for_each    = local.roles
  name        = "${var.name_prefix}-${each.key}"
  description = "ScholarChain ${each.key}; explicit role-to-role rules only"
  vpc_id      = aws_vpc.course.id
  tags        = merge(var.tags, { role = each.key })
}
resource "aws_vpc_security_group_ingress_rule" "dependency" {
  for_each                     = local.connections
  security_group_id            = aws_security_group.role[each.value.to].id
  referenced_security_group_id = aws_security_group.role[each.value.from].id
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
  description                  = each.key
  tags                         = var.tags
}
resource "aws_vpc_security_group_egress_rule" "dependency" {
  for_each                     = local.connections
  security_group_id            = aws_security_group.role[each.value.from].id
  referenced_security_group_id = aws_security_group.role[each.value.to].id
  ip_protocol                  = "tcp"
  from_port                    = each.value.port
  to_port                      = each.value.port
  description                  = each.key
  tags                         = var.tags
}
resource "aws_vpc_security_group_ingress_rule" "alb" {
  for_each          = var.public_ingress_cidrs
  security_group_id = aws_security_group.role["alb"].id
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Explicitly approved public HTTPS client network"
  tags              = var.tags
}
resource "aws_vpc_security_group_egress_rule" "https" {
  for_each          = local.https_clients
  security_group_id = aws_security_group.role[each.key].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Outbound AWS/external-provider HTTPS via NAT or gateway endpoints"
  tags              = var.tags
}
resource "aws_vpc_security_group_ingress_rule" "endpoint" {
  for_each                     = local.https_clients
  security_group_id            = aws_security_group.role["endpoints"].id
  referenced_security_group_id = aws_security_group.role[each.key].id
  ip_protocol                  = "tcp"
  from_port                    = 443
  to_port                      = 443
  description                  = "Private AWS interface endpoint clients"
  tags                         = var.tags
}
resource "aws_vpc_security_group_egress_rule" "neptune_s3" {
  security_group_id = aws_security_group.role["neptune"].id
  prefix_list_id    = aws_vpc_endpoint.gateway["s3"].prefix_list_id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  description       = "Bulk loader to S3 gateway endpoint only"
  tags              = var.tags
}
# Hadoop/Spark RPC and ephemeral executor ports require all-protocol traffic
# within the EMR role SG only; no CIDR or non-EMR principal is admitted.
resource "aws_vpc_security_group_ingress_rule" "emr_self" {
  security_group_id            = aws_security_group.role["emr"].id
  referenced_security_group_id = aws_security_group.role["emr"].id
  ip_protocol                  = "-1"
  description                  = "Bounded EMR members only: dynamic Hadoop/Spark RPC"
  tags                         = var.tags
}
resource "aws_vpc_security_group_egress_rule" "emr_self" {
  security_group_id            = aws_security_group.role["emr"].id
  referenced_security_group_id = aws_security_group.role["emr"].id
  ip_protocol                  = "-1"
  description                  = "Bounded EMR members only: dynamic Hadoop/Spark RPC"
  tags                         = var.tags
}
resource "aws_vpc_endpoint" "interface" {
  for_each            = var.interface_endpoint_services
  vpc_id              = aws_vpc.course.id
  service_name        = "com.amazonaws.${var.aws_region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [for s in aws_subnet.application : s.id]
  security_group_ids  = [aws_security_group.role["endpoints"].id]
  private_dns_enabled = true
  tags                = var.tags
}

resource "aws_security_group" "emr_service_access" {
  name        = "${var.name_prefix}-emr-service-access"
  description = "EMR private subnet service access; role references only"
  vpc_id      = aws_vpc.course.id
  tags        = merge(var.tags, { "for-use-with-amazon-emr-managed-policies" = "true" })
}
resource "aws_vpc_security_group_ingress_rule" "emr_service_to_nodes" {
  security_group_id            = aws_security_group.role["emr"].id
  referenced_security_group_id = aws_security_group.emr_service_access.id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  tags                         = var.tags
}
resource "aws_vpc_security_group_egress_rule" "emr_service_to_nodes" {
  security_group_id            = aws_security_group.emr_service_access.id
  referenced_security_group_id = aws_security_group.role["emr"].id
  ip_protocol                  = "tcp"
  from_port                    = 8443
  to_port                      = 8443
  tags                         = var.tags
}
resource "aws_vpc_security_group_ingress_rule" "emr_nodes_to_service" {
  security_group_id            = aws_security_group.emr_service_access.id
  referenced_security_group_id = aws_security_group.role["emr"].id
  ip_protocol                  = "tcp"
  from_port                    = 9443
  to_port                      = 9443
  tags                         = var.tags
}
resource "aws_vpc_security_group_egress_rule" "emr_nodes_to_service" {
  security_group_id            = aws_security_group.role["emr"].id
  referenced_security_group_id = aws_security_group.emr_service_access.id
  ip_protocol                  = "tcp"
  from_port                    = 9443
  to_port                      = 9443
  tags                         = var.tags
}
