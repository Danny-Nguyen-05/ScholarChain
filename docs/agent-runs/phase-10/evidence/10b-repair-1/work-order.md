# Subphase 10B repair round 1

The user selected **F6 + F9 count corrections (Recommended)** in Step 0. F6 is the only blocking finding. F7–F8 and F10–F15 remain carried and are not authorized for implementation in this round.

Service-engineer owns modules/services/** for F6 error classification/serialization/retry/breaker behavior, module tests and changed API documentation, plus F9 README correction. Test-engineer owns tests/** for the independent HTTP deadline and real-outage cases. Build-engineer owns packaging and local four-image rebuild/smoke after root's successful packageServices. Root alone assembles phase evidence/reports and corrects F9 in repairs.md.

Acceptance: at least four public neighbor requests through query-api with threshold3 end in graph-service's own typed504, one downstream call per request, caller trace preserved, graph breaker CLOSED, query readiness200, later normal request succeeds. Real connection refusal, no-response client timeout and unhealthy5xx still trip the breaker and yield traced readiness503. Existing breaker tests and three-main Docker stop-graph check remain green.

No changes to unrelated findings, Phase11, cloud/provider calls, commits, pushes, reviewers or human decisions. Preserve all uncommitted10B changes. JDK17 environment is mandatory for every sbt invocation; source hashes/log metadata before every gate. Root centrally runs all sbt and formatting only after owner source freezes. Gate evidence stays in this subtree; prior10B evidence is historical and unchanged.
