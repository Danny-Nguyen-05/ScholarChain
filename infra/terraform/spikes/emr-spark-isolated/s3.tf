resource "aws_s3_bucket" "spike" {
  bucket        = local.bucket_name
  force_destroy = true
  tags          = { Name = local.bucket_name }
}

resource "aws_s3_bucket_public_access_block" "spike" {
  bucket                  = aws_s3_bucket.spike.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "spike" {
  bucket = aws_s3_bucket.spike.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# SSE-KMS by default with a bucket key. No versioning, no lifecycle rules.
resource "aws_s3_bucket_server_side_encryption_configuration" "spike" {
  bucket = aws_s3_bucket.spike.id
  rule {
    bucket_key_enabled = true
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.spike.arn
    }
  }
}

resource "aws_s3_bucket_policy" "spike" {
  bucket = aws_s3_bucket.spike.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.spike.arn, "${aws_s3_bucket.spike.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.spike]
}

# ---- staged objects. Adding or removing one requires updating
# scripts/phase12d-spike/request-manifest.json (a script test enforces it). ----

# The provider uploads through the AWS SDK v2 s3 manager (multipart above its
# part size); see README "S3 request model".
resource "aws_s3_object" "runtime" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_runtime
  source                 = var.runtime_tgz_path
  source_hash            = var.runtime_tgz_sha256
  content_type           = "application/gzip"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "inputs" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_inputs
  source                 = var.inputs_tgz_path
  source_hash            = var.inputs_tgz_sha256
  content_type           = "application/gzip"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "bootstrap" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_bootstrap
  source                 = "${local.scripts_dir}/bootstrap.sh"
  source_hash            = filesha256("${local.scripts_dir}/bootstrap.sh")
  content_type           = "text/x-shellscript"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "run_step" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_run_step
  source                 = "${local.scripts_dir}/run-step.sh"
  source_hash            = filesha256("${local.scripts_dir}/run-step.sh")
  content_type           = "text/x-shellscript"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "collect_results" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_collect
  source                 = "${local.scripts_dir}/collect-results.sh"
  source_hash            = filesha256("${local.scripts_dir}/collect-results.sh")
  content_type           = "text/x-shellscript"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "g1_config" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_g1_config
  content                = local.g1_config_rendered
  content_type           = "application/json"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}

resource "aws_s3_object" "spark_defaults" {
  bucket                 = aws_s3_bucket.spike.id
  key                    = local.key_spark_default
  content                = local.spark_defaults_text
  content_type           = "text/plain"
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.spike.arn
  bucket_key_enabled     = true
  depends_on             = [aws_s3_bucket_server_side_encryption_configuration.spike, aws_s3_bucket_policy.spike]
}
