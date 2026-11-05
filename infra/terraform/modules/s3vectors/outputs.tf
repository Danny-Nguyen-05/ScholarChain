output "index_arns" { value = { for k, i in aws_s3vectors_index.document : k => i.index_arn } }
output "bucket_name" { value = aws_s3vectors_vector_bucket.embeddings.vector_bucket_name }
output "controls" { value = { bucket = aws_s3vectors_vector_bucket.embeddings, indexes = aws_s3vectors_index.document, policy = aws_s3vectors_vector_bucket_policy.tls.policy } }
