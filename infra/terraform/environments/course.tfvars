# Confirmed Step 0 choices. This is NOT a deployable account configuration.
environment            = "course"
owner                  = "danny"
expiration_date        = "2026-11-25" # Provisional; reconfirm before deployment.
cleanup_mode           = false
persistent_environment = false
enable_budget_resource = false # Pending account support and real budget.

# Intentionally absent: aws_account_id, aws_region, aws_profile,
# availability_zones, deployment_trusted_principal_arn, budget_limit_usd.
# Supply approved non-secret values in an ignored *.local.tfvars after account setup.
# Never put access keys, tokens, secret values, or state/plan content here.
