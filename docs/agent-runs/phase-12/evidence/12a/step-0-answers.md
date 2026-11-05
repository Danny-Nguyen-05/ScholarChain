# Phase 12A setup answers

User work order: “let start phase 12 A now”
User confirmed: “Use the recommendations; leave account, region, and budget pending.
Tell me to create it when required”

Scope: Phase 12A only, local authoring/init -backend=false/fmt/validate and mocked tests. No AWS API access, cloud mutation, real AWS plan, live test, model call, commit or push.
Accepted setup recommendations: environment course; owner danny; provisional expiration 2026-11-25 to reconfirm before deployment; local ignored state, documented remote-state/bootstrap design; one NAT and S3/DynamoDB gateway endpoints authored only, required interface endpoints only; omit Step Functions/EventBridge/OpenSearch and disclose; Neptune size and regional cost comparison deferred; EMR runtime/instances unresolved pending feasibility with bounded eventual topology and no initial Spot; manual security checklist and Terraform validation because no scanner found; verify/pin native S3 Vectors provider support; 12D approval and live work deferred. Account/profile, region, budget remain unset. Provisional stack duration 7–10 days, no spending authorized.
Account reminder: tell user to create/configure AWS account before 12C real Terraform plan, or before 12D if scheduled earlier. Phase 12A requires no AWS account.

Coordinator delegated Terraform ownership solely to /root/infra_12a; .gitignore and generated sbt test marker solely to /root/build_12a. Native subagents may not delegate; no reviewer launched. Model: inherited parent model, exact model identifier not exposed by spawn result; no override requested. Coordinator alone assembles phase evidence.
