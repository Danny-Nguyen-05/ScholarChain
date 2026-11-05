# Dedicated VPC: one private subnet (nodes + EFS mount target), one public
# subnet that only hosts the NAT gateway and its EIP.

resource "aws_vpc" "spike" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = "${local.prefix}-vpc" }
}

resource "aws_internet_gateway" "spike" {
  vpc_id = aws_vpc.spike.id
  tags   = { Name = "${local.prefix}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.spike.id
  cidr_block              = "10.42.0.0/24"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.prefix}-public-nat" }
}

resource "aws_subnet" "private" {
  vpc_id                  = aws_vpc.spike.id
  cidr_block              = "10.42.1.0/24"
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false
  tags                    = { Name = "${local.prefix}-private" }
}

resource "aws_eip" "nat" {
  domain = "vpc"
  tags   = { Name = "${local.prefix}-nat-eip" }
}

resource "aws_nat_gateway" "spike" {
  allocation_id     = aws_eip.nat.id
  subnet_id         = aws_subnet.public.id
  connectivity_type = "public"
  tags              = { Name = "${local.prefix}-nat" }
  depends_on        = [aws_internet_gateway.spike]
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.spike.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.spike.id
  }
  tags = { Name = "${local.prefix}-public-rt" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.spike.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.spike.id
  }
  tags = { Name = "${local.prefix}-private-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}

# Gateway endpoint with the default (full-access) policy. Restricting it would
# have to enumerate the EMR and Amazon Linux repository buckets; see README.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.spike.id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]
  tags              = { Name = "${local.prefix}-s3-gateway" }
}

# The VPC default security group is deliberately NOT managed: adopting it would
# need rights on an untagged group that cannot be scoped. It keeps the AWS
# default rules, and nothing in this root attaches to it (the EMR groups,
# the EFS mount target and the NAT gateway all use their own groups).
