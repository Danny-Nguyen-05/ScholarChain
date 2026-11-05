resource "aws_sqs_queue" "dead_letter" {
  name                      = "${var.name_prefix}-embedding-dlq"
  message_retention_seconds = var.dlq_retention_seconds
  kms_master_key_id         = var.kms_key_arn
  tags                      = var.tags
}
resource "aws_sqs_queue" "embedding" {
  name                       = "${var.name_prefix}-embedding"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = var.long_poll_seconds
  kms_master_key_id          = var.kms_key_arn
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = var.max_receive_count
  })
  tags = var.tags
}
resource "aws_sqs_queue_redrive_allow_policy" "dead_letter" {
  queue_url = aws_sqs_queue.dead_letter.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.embedding.arn]
  })
}
resource "aws_sqs_queue_policy" "tls" {
  for_each  = { embedding = aws_sqs_queue.embedding, dead_letter = aws_sqs_queue.dead_letter }
  queue_url = each.value.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"       # All principals denied insecure transport; no public allow.
      Action    = ["sqs:*"] # Universal transport DENY; never a wildcard allow.
      Resource  = each.value.arn
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}
