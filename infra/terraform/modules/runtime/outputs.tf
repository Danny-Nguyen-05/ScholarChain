output "repository_arns" { value = { for k, v in aws_ecr_repository.service : k => v.arn } }
output "repository_urls" { value = { for k, v in aws_ecr_repository.service : k => v.repository_url } }
output "controls" {
  value = { for k, r in aws_ecr_repository.service : k => {
    immutable    = r.image_tag_mutability
    scan_on_push = one(r.image_scanning_configuration).scan_on_push
    encryption   = one(r.encryption_configuration).encryption_type
    force_delete = r.force_delete
  } }
}
