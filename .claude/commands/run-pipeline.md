---
description: Route a bounded ScholarChain data pipeline run through approved scripts
---

Treat `$ARGUMENTS` as a proposed dataset snapshot, bounded input size and environment. The `dataset-engineer` verifies source manifests and licenses; `hadoop-engineer`, `entity-resolution-engineer` and `spark-engineer` verify their stage contracts. The `infra-engineer` owns the source-controlled bounded pipeline script. The orchestrator routes execution only after the human approves environment, budget and data scope. Record script revision, input checksums, output IDs, counters, rejects, graph invariants, cost and cleanup state. Stop on missing provenance or unapproved scale.
