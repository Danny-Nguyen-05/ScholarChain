---
description: Route a ScholarChain rollback through incident-responder and the human gate
---

Use `incident-responder` to diagnose the release named by `$ARGUMENTS`. Require the human to approve the target version, environment, expected data impact and source-controlled rollback procedure before any live action. The `deploy-engineer` may execute the approved script; the `infra-engineer` owns script repair. Preserve trace IDs, before/after state, smoke results and the incident timeline. Do not delete data or grading evidence.
