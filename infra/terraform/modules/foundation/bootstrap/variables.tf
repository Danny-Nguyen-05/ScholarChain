variable "state_bucket_name" {
  type        = string
  description = "Explicit globally unique name from the approved state-bootstrap work order."
}
variable "lock_table_name" {
  type        = string
  description = "Explicit name of the DynamoDB state-lock table (not an application table)."
}
variable "tags" {
  type        = map(string)
  description = "Required course/project/environment/owner/expiration tags from calling root."
  validation {
    condition     = alltrue([for key in ["course", "project", "environment", "owner", "expiration_date"] : try(length(trimspace(var.tags[key])) > 0, false)])
    error_message = "All five required tag keys must have nonempty values."
  }
}
