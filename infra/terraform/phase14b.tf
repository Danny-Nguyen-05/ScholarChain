# Replan W5b (Phase 14B, USD 25 course cap): the API certificate and the plan-time decisions that follow from it.
#
# Staging (user decision 4 and the naming contract in infra/terraform/deployer/README.md, "Replan W5a"):
#   base-apply     aws_acm_certificate.api exists as soon as api_domain_name is set (runtime on or off). It is requested with DNS
#                  validation and returns immediately in state "pending validation"; the validation CNAME is a root output
#                  (acm_validation_records). Nothing in base-apply waits for validation.
#   runtime-apply  aws_acm_certificate_validation.api exists only when the runtime is deployed (runtime_enabled with an image_revision).
#                  It waits (bounded by acm_validation_timeout) until ACM has seen the CNAME the human added, and the HTTPS listener uses
#                  its certificate_arn, so the listener is never created with an unvalidated certificate.
# The external https_certificate_arn input stays; exactly one of the two sources may be set (phase12b.tf guard).
locals {
  runtime_deployed = var.runtime_enabled && var.image_revision != null
  # Plan-time booleans (known before apply, unlike the certificate ARN of a certificate created by the same apply).
  acm_managed       = var.api_domain_name != null
  acm_validated     = local.acm_managed && local.runtime_deployed
  https_enabled     = var.https_certificate_arn != null || local.acm_validated
  neptune_tunnel    = var.neptune_tunnel_enabled && local.runtime_deployed
  listener_cert_arn = var.https_certificate_arn != null ? var.https_certificate_arn : one(aws_acm_certificate_validation.api[*].certificate_arn)
}

resource "aws_acm_certificate" "api" {
  count             = local.acm_managed ? 1 : 0
  domain_name       = var.api_domain_name
  validation_method = "DNS"
  # Default key algorithm (RSA 2048). Tags satisfy the deployer's tag-conditioned ACM statements (acm:ValidationMethod = DNS,
  # aws:RequestTag/project and /environment on RequestCertificate, resource tags on Delete/AddTags/ListTags/RemoveTags): they are
  # the root's required tags (module.foundation.tags: course, project, environment, owner, expiration_date, and additional_tags), the
  # same value the provider default_tags carry.
  tags = module.foundation.tags
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_acm_certificate_validation" "api" {
  count           = local.acm_validated ? 1 : 0
  certificate_arn = aws_acm_certificate.api[0].arn
  # No validation_record_fqdns: the DNS record lives at Cloudflare, outside Terraform. ACM validates when it sees the CNAME.
  timeouts {
    create = var.acm_validation_timeout
  }
}
