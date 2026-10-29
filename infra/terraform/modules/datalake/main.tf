locals {
  purposes = toset(["raw", "curated", "graph", "rag", "artifacts", "logs", "reports"])
}
resource "aws_s3_bucket" "zone" {
  for_each      = local.purposes
  bucket        = "${var.name_prefix}-${var.aws_account_id}-${each.key}"
  force_destroy = var.cleanup_mode
  tags          = merge(var.tags, { purpose = each.key })
  # Terraform requires this to be literal. Cleanup also needs a human-reviewed
  # source change to remove this guard; cleanup_mode alone cannot delete buckets.
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "zone" {
  for_each                = aws_s3_bucket.zone
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_ownership_controls" "zone" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  rule { object_ownership = "BucketOwnerEnforced" }
}
resource "aws_s3_bucket_versioning" "zone" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "zone" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}
resource "aws_s3_bucket_policy" "tls" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"      # Deliberate universal DENY, not a public access grant.
      Action    = ["s3:*"] # Universal transport DENY must cover current and future operations; no grant.
      Resource  = [each.value.arn, "${each.value.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.zone]
}
resource "aws_s3_bucket_lifecycle_configuration" "zone" {
  for_each = aws_s3_bucket.zone
  bucket   = each.value.id
  rule {
    id     = "abort-incomplete-multipart"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = var.multipart_abort_days }
  }
  dynamic "rule" {
    for_each = !var.persistent_environment && contains(["curated", "graph", "rag", "artifacts"], each.key) ? [1] : []
    content {
      id     = "expire-explicit-intermediates-only"
      status = "Enabled"
      filter { prefix = "intermediates/" }
      expiration { days = var.intermediate_retention_days }
      noncurrent_version_expiration { noncurrent_days = var.intermediate_retention_days }
    }
  }
  depends_on = [aws_s3_bucket_versioning.zone]
}
