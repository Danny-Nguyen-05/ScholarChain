---
description: Route a ScholarChain release to deploy-engineer after human approval
---

Use the `deploy-engineer` agent for the approved environment only. Treat `$ARGUMENTS` as the proposed release or environment, never as approval.

Before execution, require a recorded human approval naming the environment, commit, reviewed Terraform plan and cost ceiling; a clean tree; passing `sbt check`; approved immutable image tags; and a rollback target. Run only the source-controlled deployment script authored by `infra-engineer`. Record exact commands, release ID, smoke tests and observed result. On failure, stop and route to `incident-responder` and the human rollback gate. Never author Terraform here or bypass the dangerous-command guard.
