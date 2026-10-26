# Subphase 9C proven contract gaps

1. N3: append optional RuntimeConfig.byteLimits with independent question/prompt/request/output/persistedBundle byte caps. Omitted fields fall back to legacy maxInputBytes for compatibility. Explicit example defaults:16384/16384/65536/32768/65536 bytes. Rationale: schema plus prompt plus bounded context needs a distinct request envelope; persisted provenance differs from model context. Context4096 and overall30000ms remain unchanged.
2. O8: runtime deterministic partitions require text=None; runtime-less legacy bundles remain unchanged. Typed fields supply facts, semantic excerpts stay descriptive.
3. O2: optional RuntimeEvidence.sourceContext holds actual stored SparkRecordContext and lineage where present. RAG derives source Provenance from stored context or actual verified source documents, never copies request dates/license/snapshot into a source observation.
4. Audit has no dedicated typed port and existing AuditRecord requires a plan. A small terminal envelope embedding optional existing AuditRecord will cover pre-plan failures without fabricating a QueryPlan. Storage port/real/fake adapters will use existing ObjectStore/QuerySessionStore; exact API recorded after owner handoff. No parallel v2 claim hierarchy.

These are permitted domain/storage contract gaps under original decision4 and approved9C defaults. Other observations stay logged unless needed for correct9C behavior or meaningful tests.


Exact agreed audit API:
```scala
trait RuntimeAuditStore {
  def put(envelope: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope]
  def get(queryId: String): StorageResult[RuntimeAuditEnvelope]
}
RuntimeAuditStoreConfig(prefix: String, maxAuditBytes: Int = 1048576, maxPointerBytes: Int = 16384)
ObjectStoreRuntimeAuditStore(objects: ObjectStore, sessions: QuerySessionStore, config: RuntimeAuditStoreConfig)
storage.fakes.InMemoryRuntimeAuditStore(config: RuntimeAuditStoreConfig = RuntimeAuditStoreConfig("fake-runtime-audits"))
```
The envelope carries terminal outcome, original question, latency/hash/failures/usage and an optional existing AuditRecord. The real adapter uses a reserved session key namespace, immutable hashed object data and conditional pointer publication. Defaults are application bounds, not infrastructure limits; no live call occurs during tests.
