# Execution identity and saved plan


## Billing-plan execution identity clarification

The saved planning artifact is bound to the explicitly configured scholarchain-planner profile, which remains read-only. It is not an execution plan for an as-yet unselected deployment identity. Before any apply, select the scoped non-root temporary deployment profile, generate a fresh plan using that profile, review its diff and checksum, and obtain the human's written approval for that exact execution plan. Do not elevate or silently repurpose the planner, and do not treat an environment-profile change as overriding an explicit provider profile in the saved plan. Nothing is applied by this clarification.

Primary references: provider 6.44.0 authentication precedence (explicit provider configuration before environment): https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/v6.44.0/website/docs/index.html.markdown ; saved-plan mode does not accept extra planning options: https://developer.hashicorp.com/terraform/cli/commands/apply .
