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

# Accepted12B local authoring choices. These flags authorize no cloud action.
neptune_enabled                     = false # Explicit engine/family still pending.
runtime_enabled                     = false # Current service entrypoints do not compose live AWS stores.
runtime_composition_verified        = false
emr_config                          = { enabled = false } # Release/runtime/bootstrap remain unselected.
neptune_min_ncu                     = 1
neptune_max_ncu                     = 2.5
neptune_backup_days                 = 7
vector_dimension                    = 256
vector_metric                       = "cosine"
vector_non_filterable_metadata_keys = ["textS3Uri"]
log_retention_days                  = 7
alarm_notification_arns             = []
public_ingress_cidrs                = []
