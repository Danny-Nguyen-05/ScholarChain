# PREPARATION CONTRACT ONLY. There is intentionally no provider configuration,
# AWS resource, provisioner, executable bootstrap or remote-state dependency.
# No readiness boolean is treated as approval; this root cannot launch EMR.
output "proposal" {
  value = {
    region                      = var.region
    instance_type               = var.instance_type
    primary_nodes               = 1
    core_nodes                  = 1
    task_nodes                  = 0
    spot_nodes                  = 0
    maximum_attempts            = 1
    maximum_total_runtime_hours = var.maximum_total_runtime_hours
    spike_allowance_usd         = var.spike_allowance_usd
    shared_project_ceiling_usd  = 200
    candidate                   = "EMR on EC2; separately installed Spark 3.5.4 / Scala 2.13"
    aws_resources_declared      = 0
    launchable                  = false
    live_compatibility_verified = false
    unresolved_prerequisites = [
      "active account-wide budget notifications and human-enabled Cost Explorer",
      "remaining budget including delayed/unreported charges, storage and tax",
      "reviewed non-root deployment identity with short-lived credentials",
      "portable G1 CLI bundle and canonical local table-count/content-hash baseline",
      "driver/executor class-origin probe and distributed filesystem proof",
      "independent deadline controller covering startup, retries and teardown",
      "checksummed Spark distribution, job JAR and reviewed TLS/network/IAM artifacts",
      "runnable isolated Terraform plan, independent review and human-written execution approval"
    ]
  }
}
