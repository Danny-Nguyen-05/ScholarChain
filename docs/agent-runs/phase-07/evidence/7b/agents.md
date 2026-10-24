# Native ownership ledger — Subphase 7B

All agents inherit the parent model; no overrides, nested agents or reviewer. Native role continuations reuse the existing canonical IDs.

| Native ID | Role | Exclusive write territory | Work order |
|---|---|---|---|
| /root | Coordinator | docs/agent-runs/phase-07/** | Preflight, accepted decisions, evidence, serialized owner-requested gates and handoff |
| /root/storage_engineer | storage-engineer | modules/storage/** | 7B adapters, composition, N1/N3, N2 hash verification, module tests and README |
| /root/test_engineer | test-engineer | tests/** | Independent 7B behavior/adversarial tests, no review role |
| /root/spark_engineer | spark-engineer | modules/spark/src/test/** | Accepted N2 bounded local real-data CSV replay harness only; production exporter unchanged |

Build/core changes require explicit routed owner dependencies. Coordinator can execute owner-requested sbt/scalafmt while owners retain single write ownership. No live AWS/provider calls, staging, commit or push. No 7C implementation.
