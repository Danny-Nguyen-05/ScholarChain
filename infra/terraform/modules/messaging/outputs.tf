output "queue_arn" { value = aws_sqs_queue.embedding.arn }
output "dead_letter_queue_arn" { value = aws_sqs_queue.dead_letter.arn }
output "queue_urls" {
  value = { embedding = aws_sqs_queue.embedding.url, dead_letter = aws_sqs_queue.dead_letter.url }
}
output "controls" {
  value = {
    visibility_timeout = aws_sqs_queue.embedding.visibility_timeout_seconds
    retention          = aws_sqs_queue.embedding.message_retention_seconds
    dlq_retention      = aws_sqs_queue.dead_letter.message_retention_seconds
    redrive            = aws_sqs_queue.embedding.redrive_policy
    redrive_allow      = aws_sqs_queue_redrive_allow_policy.dead_letter.redrive_allow_policy
    encryption_keys    = [aws_sqs_queue.embedding.kms_master_key_id, aws_sqs_queue.dead_letter.kms_master_key_id]
    tls_policies       = [for p in aws_sqs_queue_policy.tls : p.policy]
  }
}
