# Attribute names are the Phase 7 adapter contract, including the literal '#'.
locals {
  tables = {
    RunLedger             = { pk = "runId", sk = "stageKey" }
    EntityLinkCache       = { pk = "entityType#normalizedKey", sk = "policyVersion#sourceId" }
    QuerySession          = { pk = "queryId", sk = "itemType" }
    EvidenceBundle        = { pk = "evidenceId", sk = "part" }
    ArtifactRegistry      = { pk = "artifactId", sk = "version" }
    ResearcherMetricCache = { pk = "researcherId", sk = "windowId" }
  }
}
resource "aws_dynamodb_table" "table" {
  for_each                    = local.tables
  name                        = "${var.name_prefix}-${each.key}"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = each.value.pk
  range_key                   = each.value.sk
  deletion_protection_enabled = !var.cleanup_mode
  attribute {
    name = each.value.pk
    type = "S"
  }
  attribute {
    name = each.value.sk
    type = "S"
  }
  dynamic "attribute" {
    for_each = each.key == "QuerySession" ? [1] : []
    content {
      name = "idempotencyKey"
      type = "S"
    }
  }
  dynamic "global_secondary_index" {
    for_each = each.key == "QuerySession" ? [1] : []
    content {
      name = var.query_session_gsi_name
      key_schema {
        attribute_name = "idempotencyKey"
        key_type       = "HASH"
      }
      projection_type = "ALL"
    }
  }
  point_in_time_recovery { enabled = true }
  server_side_encryption {
    enabled     = true
    kms_key_arn = var.kms_key_arn
  }
  dynamic "ttl" {
    for_each = each.key == "QuerySession" ? [1] : []
    content {
      attribute_name = "expiresAt"
      enabled        = var.enable_query_session_ttl
    }
  }
  tags = var.tags
}
