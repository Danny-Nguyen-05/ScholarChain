locals { indexes = toset(["researcher-profile-v1", "collaboration-community-v1", "paper-abstract-v1", "collaboration-path-v1", "topic-institution-summary-v1"]) }
resource "aws_s3vectors_vector_bucket" "embeddings" {
  vector_bucket_name       = "${var.name_prefix}-${var.aws_account_id}-vectors"
  encryption_configuration = [{ sse_type = "aws:kms", kms_key_arn = var.kms_key_arn }]
  # W4 (user decision 5): no prevent_destroy. The vector bucket and its indexes can be deleted only after cleanup_mode = true has
  # set force_destroy (scripts/cleanup.sh --prepare); the provider then also deletes indexes and vectors left in the bucket.
  force_destroy = var.cleanup_mode
  tags          = var.tags
}
resource "aws_s3vectors_index" "document" {
  for_each           = local.indexes
  vector_bucket_name = aws_s3vectors_vector_bucket.embeddings.vector_bucket_name
  index_name         = each.key
  metadata_configuration { non_filterable_metadata_keys = var.non_filterable_metadata_keys }
  data_type                = "float32"
  dimension                = var.dimension
  distance_metric          = var.metric
  encryption_configuration = [{ sse_type = "aws:kms", kms_key_arn = var.kms_key_arn }]
  tags                     = var.tags
}
# Identity policies grant exact index ARNs. No public Allow is authored.
resource "aws_s3vectors_vector_bucket_policy" "tls" {
  vector_bucket_arn = aws_s3vectors_vector_bucket.embeddings.vector_bucket_arn
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3vectors:*",
    Resource  = [aws_s3vectors_vector_bucket.embeddings.vector_bucket_arn, "${aws_s3vectors_vector_bucket.embeddings.vector_bucket_arn}/index/*"],
    Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
}
