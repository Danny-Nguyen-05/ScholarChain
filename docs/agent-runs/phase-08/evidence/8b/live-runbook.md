# Authored 8C command — UNEXECUTED

This is the 8B plan-required handoff only. 8C has not started. No live invocation, credential read, resource creation, provider request or cleanup has occurred. The disabled templates are authoring examples, never human approval records. Zero caps, expired timestamp and executionApproved=false fail closed.

Before a future user-authorized 8C: Phase14 must deploy and verify existing ordinary-S3/vector buckets, all five configured indexes, IAM and DynamoDB tables through Terraform. Confirm immutable dimension256/cosine against the pinned configured TitanV2 model and index metadata. Keep source qualifications and abstract permissions. Resolve remaining pre-live findings according to the human's decision. Build and review the exact local manifest, including complete chunk groups.

The human writes a new actual approval file outside this template, with explicit environment/runID, byte SHA256 of the exact config/manifest/Phase14 gate, future expiry, vector/concurrency/embedding-call/dollar caps and verified price/budget assumptions. Fill the config from deployed nonsecret resource names; no credentials belong in files. Price bounds include retry attempts plus conservative storage/overhead assumptions; estimated dollars are not a billing guarantee. Independent cloud billing/budget controls must be reviewed by the human.

Authored command (NOT RUN):
```sh
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
export SBT_OPTS="-Dlogback.configurationFile=$PWD/docs/agent-runs/phase-04/xml-repair-logback.xml"
sbt -batch 'rag / Compile / runMain edu.uic.cs441.scholarchain.rag.LiveEmbeddingIngestMain --config /absolute/path/to/human-live-config.json --manifest /absolute/path/to/reviewed-embedding-manifest.json --approval /absolute/path/to/human-live-approval.json --report /absolute/path/to/live-ingestion-report.json --run-id approved-execution-run'
```

Only the future deploy-engineer executes the separately approved command. This runbook deliberately uses operator-filled paths; these are unrun template inputs, not claimed existing files. The executable checks configured caps and exact approved bytes before constructing SDK clients. It checks existing indexes rather than provisioning them. Observed live counts, query latency, cost, object counts and provider quality remain unverified.

## Cleanup procedure — instructions only, never executed in 8B

1. Retain manifest, report, rejected records and RunLedger evidence. Identify exact vector keys/indexes, ordinary-S3 versions/checkpoints and registry bindings created by the approved run. Shared and pre-existing objects must be identified before any deletion; unchanged items are not owned by this run merely because they appear in its manifest.
2. Human approves an explicit bounded deletion inventory and impact/rollback plan. Route resource changes through reviewed Terraform; route data deletion to the deploy-engineer with that separate human gate. Deleting vectors alone leaves immutable group/artifact reservations; do not reuse a half-cleaned namespace or silently remove shared registry state.
3. Stop consumers/ingestion as approved, delete only approved data and registry reservations in dependency order, then verify exact counts and pointer consistency. Terraform destroy/apply is separately reviewed and human-approved; never run account-wide bucket emptying or broad deletion.
4. Save cleanup receipts, final object/vector counts and remaining shared resources. If cleanup is deferred, record that state in the future human-owned approval/closure evidence.

N2–N8 and R2–R3 remain nonblocking/deferred. R1 repair is validated offline in8B; no live transaction/group delete behavior is claimed.
