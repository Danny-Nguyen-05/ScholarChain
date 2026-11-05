# Phase 12D — portable runtime and request inventory

User authorization: “alright let's go”, accepting the next offline portable-runtime/request-inventory task after two commits were pushed. Base99c8b923ea245b20447de641b417dbb883313cee. This is a new bounded work order, not a live gate.

Build-engineer owns portable packaging and local verification; coordinator owns this phase evidence, public request/cost analysis and the handoff. Preserve application/source versions and the exact reviewed job JAR and G1 lineage. Public Apache artifact acquisition with checksum/signature verification and bounded local probes are in scope. Any required application change returns to its module owner and requires a new tested baseline. Actual build source changes require its deterministic tests and sbt check.

Inventory portable archive members, versions/hashes/permissions, compressed/uncompressed sizes, staging objects and conditional PUT/LIST/GET/HEAD/multipart/copy/retry/KMS/request assumptions. Evaluate the lower-request proposal without assuming it selected or proven. Document the carried no-extra-cluster canary, transit-certificate cost/mechanism and explicit EBS requirements for the separate later infrastructure task.

No account login/API, AWS credentials/private recipient/state/plan access, security or resource mutation, Terraform init/plan/apply/destroy, cluster/canary creation, spending, reviewer launch, commit/push, cleanup or Phase12 completion. No saved Markdown review prompt; final review instructions are chat-only. Historical reviewed evidence and human decisions remain unchanged. Stop at a complete independently reviewable offline handoff.
