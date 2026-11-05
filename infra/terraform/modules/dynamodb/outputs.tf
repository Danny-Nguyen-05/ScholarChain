output "table_names" { value = { for k, v in aws_dynamodb_table.table : k => v.name } }
output "table_arns" { value = { for k, v in aws_dynamodb_table.table : k => v.arn } }
output "query_session_index_arn" {
  value = "${aws_dynamodb_table.table["QuerySession"].arn}/index/${var.query_session_gsi_name}"
}
output "controls" {
  value = { for k, t in aws_dynamodb_table.table : k => {
    pk                  = t.hash_key
    sk                  = t.range_key
    billing_mode        = t.billing_mode
    deletion_protection = t.deletion_protection_enabled
    pitr                = one(t.point_in_time_recovery).enabled
    encryption          = one(t.server_side_encryption).enabled
    gsis                = t.global_secondary_index
    ttl                 = t.ttl
  } }
}
