output "ids" {
  value = {
    vpc_id                 = aws_vpc.course.id
    public_subnet_ids      = [for s in aws_subnet.public : s.id]
    application_subnet_ids = [for s in aws_subnet.application : s.id]
    data_subnet_ids        = [for s in aws_subnet.data : s.id]
    security_group_ids     = { for k, s in aws_security_group.role : k => s.id }
  }
}
output "controls" {
  value = {
    azs                    = [for s in aws_subnet.application : s.availability_zone]
    public_subnet_count    = length(aws_subnet.public)
    app_subnet_count       = length(aws_subnet.application)
    data_subnet_count      = length(aws_subnet.data)
    public_ip_on_launch    = [for s in concat(values(aws_subnet.public), values(aws_subnet.application), values(aws_subnet.data)) : s.map_public_ip_on_launch]
    nat_gateway_count      = length([aws_nat_gateway.course])
    gateway_services       = keys(aws_vpc_endpoint.gateway)
    interface_services     = keys(aws_vpc_endpoint.interface)
    dependency_ports       = { for k, r in aws_vpc_security_group_ingress_rule.dependency : k => r.from_port }
    dependency_cidrs       = [for r in aws_vpc_security_group_ingress_rule.dependency : r.cidr_ipv4]
    public_ingress_count   = length(aws_vpc_security_group_ingress_rule.alb)
    public_ingress_ports   = [for r in aws_vpc_security_group_ingress_rule.alb : r.from_port]
    https_egress_ports     = [for r in aws_vpc_security_group_egress_rule.https : r.from_port]
    neptune_s3_egress_port = aws_vpc_security_group_egress_rule.neptune_s3.from_port
    data_route_count       = length([for route in aws_route.default : route if route.route_table_id == aws_route_table.data.id])
  }
}
