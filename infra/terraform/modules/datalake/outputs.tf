output "bucket_names" { value = { for k, v in aws_s3_bucket.zone : k => v.bucket } }
output "bucket_arns" { value = { for k, v in aws_s3_bucket.zone : k => v.arn } }
output "controls" {
  value = { for k, b in aws_s3_bucket.zone : k => {
    force_destroy   = b.force_destroy
    public_access   = aws_s3_bucket_public_access_block.zone[k]
    ownership       = one(aws_s3_bucket_ownership_controls.zone[k].rule).object_ownership
    versioning      = one(aws_s3_bucket_versioning.zone[k].versioning_configuration).status
    encryption      = one(one(aws_s3_bucket_server_side_encryption_configuration.zone[k].rule).apply_server_side_encryption_by_default).sse_algorithm
    lifecycle_rules = aws_s3_bucket_lifecycle_configuration.zone[k].rule
    tls_policy      = aws_s3_bucket_policy.tls[k].policy
  } }
}
