# Step 0 storage interface handoff

Published in commentary before production edits were authorized. User answers authorize the
minimum storage prerequisites in9A; this is not a9B retrieval-stage implementation.

```scala
trait RuntimeArtifactStore {
  def rank(windowId: String, metric: RuntimeRankingMetric,
      filters: RuntimePopulationFilter, limit: Int): StorageResult[RuntimeRankingPage]
  def communitySummary(communityId: String, windowId: String): StorageResult[CommunitySummary]
  def bridgeMetrics(researcherId: String, windowId: String): StorageResult[RuntimeBridgeRecord]
  def temporalChange(researcherId: String, fromWindowId: String,
      toWindowId: String): StorageResult[RuntimeTemporalRecord]
  def edgeSupport(edgeId: String, windowId: String): StorageResult[RuntimeEdgeRecord]
  def researcherContext(researcherId: String, windowId: String,
      limit: Int): StorageResult[RuntimeResearcherContext]
}
// Additive method on EvidenceBundleStore:
def getItem(evidenceId: String): StorageResult[EvidenceItem]
```

The domain owner defines shared request/response records under modules/core. The storage owner
implements real ObjectStore-backed artifact reads, matching fakes, bounded preparation from a
validated Phase6 export, and immutable ObjectStore evidence-item-to-bundle pointers. Existing
evidence-ID formats, tables and infrastructure remain. The production assembly for item lookup
must use the indexed bundle-store wrapper, documented and tested by the storage owner.

Ranking filters the authoritative stored population before selecting topK and retains population
counts/truncation. Missing required metadata, unsupported metric scope, inconsistent lineage or
oversized snapshots fail explicitly. No semantic-defined population or invented metric values.
Bridge/temporal results preserve memberships/convergence/iterations. Edge support preserves
stored jointPublicationCount, supporting works, optional years and source lineage.

Accepted preparation approach: a bounded immutable snapshot, read-only through ObjectStore at
runtime. Configured row/byte caps reject larger exports; this phase does not introduce sharding
or claim full-scale runtime validation. No new table, GSI, infrastructure or paid-provider call.
