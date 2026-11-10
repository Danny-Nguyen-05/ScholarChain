# Replan W5b (Phase 14B, USD 25 course cap): inputs for the API certificate and the temporary Neptune tunnel.
variable "api_domain_name" {
  type        = string
  default     = null
  nullable    = true
  description = "Fully qualified API hostname (for example api.<your-domain>) of a domain the human owns, with DNS at Cloudflare. When set, base-apply creates ONE DNS-validated ACM certificate for it and outputs the validation record (acm_validation_records); the human adds that CNAME (DNS only, not proxied) by hand. The real name lives only in the private tfvars, never in the repository. Exactly one of api_domain_name and https_certificate_arn may be set. The HTTPS listener (runtime stage) waits for the certificate to be validated."
  validation {
    # Lowercase LDH labels, at least three labels (a subdomain, because an apex name cannot take a CNAME), no wildcard, no trailing dot.
    condition     = var.api_domain_name == null ? true : (length(var.api_domain_name) <= 253 && can(regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.){2,}[a-z]([a-z0-9-]{0,61}[a-z0-9])?$", var.api_domain_name)))
    error_message = "api_domain_name must be a lowercase fully qualified subdomain with at least three labels (for example api.example.invalid), without wildcard, port or trailing dot."
  }
}
variable "acm_validation_timeout" {
  type        = string
  default     = "15m"
  nullable    = false
  description = "How long the runtime-stage aws_acm_certificate_validation waits for the DNS record to be seen (whole minutes, 1m to 60m). base-apply never waits. The human adds the validation CNAME BEFORE the runtime apply, so validation normally completes at once."
  validation {
    condition     = can(regex("^[1-9][0-9]?m$", var.acm_validation_timeout)) && try(tonumber(trimsuffix(var.acm_validation_timeout, "m")) <= 60, false)
    error_message = "acm_validation_timeout must be whole minutes from 1m to 60m (for example 15m)."
  }
}
variable "neptune_tunnel_enabled" {
  type        = bool
  default     = false
  nullable    = false
  description = "Register the temporary Neptune tunnel (task role scholarchain-<env>-neptune-tunnel-task and task definition family scholarchain-<env>-neptune-tunnel). It takes effect only with runtime_enabled and an image_revision. No ECS service is created: the human runs it as a one-off task (ecs:RunTask --enable-execute-command) for the load window and stops it afterwards."
  validation {
    condition     = var.neptune_tunnel_enabled == true || var.neptune_tunnel_enabled == false
    error_message = "neptune_tunnel_enabled must be true or false."
  }
}

# Replan G-MAIN (gap G3): the runtime-artifact pointer. modules/services reads SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY, _SHA256 and
# _SOURCE_RUN_ID (all or none) in the query-api role ONLY (AwsConfig.scala, `case _ =>`; graph-service, semantic-service and
# embedding-worker never read them). The 14C load publishes the artifact (RuntimeArtifactMain), so the values do not exist at the
# first runtime plan: they are null then and the services refuse every artifact read, as before. After the 14C upload the human
# puts the three values printed by RuntimeArtifactMain into the PRIVATE tfvars and runs one more runtime-apply (a new task
# definition revision for query-api; no commit is needed). Not secret: a key, a content hash and a run id.
# BUCKET CONTRACT: the object lives in the RAG bucket (scholarchain-<env>-<account>-rag, the services default for
# SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET) under runtime-artifacts/<run_prefix>/. RuntimeArtifactMain prints four values; each maps to exactly one
# root variable: _BUCKET -> runtime_artifact_bucket, _KEY -> runtime_artifact_key, _SHA256 -> runtime_artifact_sha256, _SOURCE_RUN_ID ->
# runtime_artifact_source_run_id. The bucket is optional (null = the services default = the rag bucket) and, when set, must equal the rag bucket.
variable "runtime_artifact_key" {
  type        = string
  default     = null
  nullable    = true
  description = "S3 key of the bounded runtime artifact in the RAG bucket, printed by RuntimeArtifactMain as SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY. Must be runtime-artifacts/<run_prefix>/versions/<...>/<file> (run_prefix as the deployer's operator_run_prefix, ^run-[a-z0-9][a-z0-9-]{1,27}$), with safe segments only. Set together with runtime_artifact_sha256 and runtime_artifact_source_run_id (all or none), in the private tfvars. Null: the services refuse artifact reads."
  validation {
    condition = var.runtime_artifact_key == null ? true : (
      length(var.runtime_artifact_key) <= 900 &&
      can(regex("^runtime-artifacts/run-[a-z0-9][a-z0-9-]{1,27}/versions/[A-Za-z0-9._=-]+(/[A-Za-z0-9._=-]+)*$", var.runtime_artifact_key)) &&
      !contains(split("/", var.runtime_artifact_key), "..") && !contains(split("/", var.runtime_artifact_key), ".")
    )
    error_message = "runtime_artifact_key must be runtime-artifacts/<run_prefix>/versions/<segments>, run_prefix matching ^run-[a-z0-9][a-z0-9-]{1,27}$, segments of A-Za-z0-9._=- only, no '.' or '..' segment, at most 900 characters."
  }
}
variable "runtime_artifact_sha256" {
  type        = string
  default     = null
  nullable    = true
  description = "Lowercase 64-hex SHA-256 of the runtime artifact file (shasum -a 256 runtime-artifact.json), SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256. All or none with runtime_artifact_key and runtime_artifact_source_run_id."
  validation {
    condition     = var.runtime_artifact_sha256 == null ? true : can(regex("^[0-9a-f]{64}$", var.runtime_artifact_sha256))
    error_message = "runtime_artifact_sha256 must be 64 lowercase hexadecimal characters."
  }
}
variable "runtime_artifact_source_run_id" {
  type        = string
  default     = null
  nullable    = true
  description = "Run id of the Phase 6 export the artifact was cut from (for example run:<uuid>), SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID. All or none with runtime_artifact_key and runtime_artifact_sha256."
  validation {
    condition     = var.runtime_artifact_source_run_id == null ? true : can(regex("^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$", var.runtime_artifact_source_run_id))
    error_message = "runtime_artifact_source_run_id must start with a letter or digit and contain only A-Za-z0-9._:- (at most 128 characters)."
  }
}
variable "runtime_artifact_bucket" {
  type        = string
  default     = null
  nullable    = true
  description = "Bucket of the runtime artifact, printed by RuntimeArtifactMain as SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET. Optional: null leaves the services default, which is the rag bucket. When set it must equal the rag bucket scholarchain-<env>-<account>-rag (root guard) and the pointer (key, sha256, source run id) must be set too; the runtime task roles read exactly that bucket."
  validation {
    condition     = var.runtime_artifact_bucket == null ? true : can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.runtime_artifact_bucket))
    error_message = "runtime_artifact_bucket must be an S3 bucket name (3 to 63 lowercase letters, digits, dots and hyphens)."
  }
}
