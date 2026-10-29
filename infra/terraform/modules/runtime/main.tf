# Immutable per-service repositories, retained from12A.
locals { services = toset(["query-api", "graph-service", "semantic-service", "embedding-worker"]) }
resource "aws_ecr_repository" "service" {
  for_each             = local.services
  name                 = "${var.name_prefix}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = var.cleanup_mode
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key_arn
  }
  tags = var.tags
}
