variable "region" {
  type    = string
  default = "us-east-2"
  validation {
    condition     = var.region == "us-east-2"
    error_message = "This proposal is costed only for Ohio; another region requires a new decision."
  }
}
variable "instance_type" {
  type    = string
  default = "m5.xlarge"
  validation {
    condition     = var.instance_type == "m5.xlarge"
    error_message = "Only the proposed m5.xlarge shape may be reviewed under this work order."
  }
}
variable "spike_allowance_usd" {
  type    = number
  default = 5
  validation {
    condition     = var.spike_allowance_usd > 0 && var.spike_allowance_usd <= 5
    error_message = "The proposed allowance is at most USD 5 from the shared USD 200, never an additional budget."
  }
}
variable "maximum_total_runtime_hours" {
  type    = number
  default = 2
  validation {
    condition     = var.maximum_total_runtime_hours > 0 && var.maximum_total_runtime_hours <= 2
    error_message = "Total billed cluster runtime across retries must not exceed the proposed two-hour allowance."
  }
}
variable "launch_requested" {
  type    = bool
  default = false
  validation {
    condition     = !var.launch_requested
    error_message = "This preparation root cannot launch resources. Resolve the documented prerequisites and obtain a separately reviewed runnable plan and human-written approval."
  }
}
