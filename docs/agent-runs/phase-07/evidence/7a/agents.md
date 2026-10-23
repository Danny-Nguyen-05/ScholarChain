# Native agent ownership ledger

All agents inherit the parent system model GPT-6; exact deployed build unavailable. Native IDs are the canonical task IDs below. No model overrides; no nested delegation; no reviewer launched.

| Native ID | Role | Exclusive write territory | Work order |
|---|---|---|---|
| /root | Coordinator | docs/agent-runs/phase-07/**; Git branch operation | Questions, routing, evidence, owner-requested verification, final packet |
| /root/build_engineer | build-engineer | build.sbt, project/** | SDK/Parquet dependencies, storage test wiring, off-default guarded awsIntegration configuration |
| /root/storage_engineer | storage-engineer | modules/storage/** | All ports/main fakes, S3 + six DynamoDB adapters, manifest loaders, module tests/README |
| /root/test_engineer | test-engineer | tests/** | Independent interface-first 7A tests; no review role |

Spark owner is queued for task 6 after documented format gate. Domain owner is invoked only for an evidenced shared-contract blocker. Coordinator may execute owner-requested formatting/test commands while holding the single shared sbt slot; that execution does not transfer source ownership. Reports are assembled only by coordinator.

| /root/spark_engineer | spark-engineer | modules/spark/** | Approved task 6 only: distributed Neptune openCypher CSV export, module tests and scoped documentation |

Build owner finished and released the shared sbt slot before Spark agent launch. Build role remains available for routed repairs only. No domain owner was launched because storage-local records currently suffice.
