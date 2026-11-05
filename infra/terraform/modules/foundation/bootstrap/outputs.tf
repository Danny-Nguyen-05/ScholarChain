output "state_bucket_name" { value = aws_s3_bucket.state.bucket }
output "lock_table_name" { value = aws_dynamodb_table.lock.name }
output "controls" {
  value = {
    versioning               = one(aws_s3_bucket_versioning.state.versioning_configuration).status
    encryption               = one(one(aws_s3_bucket_server_side_encryption_configuration.state.rule).apply_server_side_encryption_by_default).sse_algorithm
    public_access_block      = aws_s3_bucket_public_access_block.state
    force_destroy            = aws_s3_bucket.state.force_destroy
    lock_key                 = aws_dynamodb_table.lock.hash_key
    lock_deletion_protection = aws_dynamodb_table.lock.deletion_protection_enabled
    lock_pitr                = one(aws_dynamodb_table.lock.point_in_time_recovery).enabled
    lock_encryption          = one(aws_dynamodb_table.lock.server_side_encryption).enabled
    tls_policy               = aws_s3_bucket_policy.state_tls.policy
  }
}
