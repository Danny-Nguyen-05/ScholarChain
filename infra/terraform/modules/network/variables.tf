variable "name_prefix" { type = string }
variable "aws_region" { type = string }
variable "availability_zones" { type = list(string) }
variable "vpc_cidr" {
  type = string
  validation {
    condition     = can(cidrsubnet(var.vpc_cidr, 8, 30))
    error_message = "VPC CIDR must support the configured subnet division."
  }
}
variable "public_ingress_cidrs" {
  type = set(string)
  validation {
    condition     = alltrue([for c in var.public_ingress_cidrs : can(cidrnetmask(c))])
    error_message = "ALB ingress values must be valid IPv4 CIDRs."
  }
}
variable "service_port" { type = number }
variable "neptune_port" { type = number }
variable "interface_endpoint_services" { type = set(string) }
variable "tags" { type = map(string) }
