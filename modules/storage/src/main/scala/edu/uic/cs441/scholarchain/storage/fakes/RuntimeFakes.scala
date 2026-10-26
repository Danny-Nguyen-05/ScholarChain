package edu.uic.cs441.scholarchain.storage.fakes

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8

/** Complete bounded source rows with producer-shaped metadata, entirely offline. Real and fake
  * readers share the integrity boundary; tests independently specify expected facts.
  */
final class InMemoryRuntimeArtifactStore(
    context: SparkRecordContext,
    sourceRows: Map[String, Vector[ujson.Obj]],
    windows: Vector[String],
    config: RuntimeArtifactConfig = RuntimeArtifactConfig()
) extends RuntimeArtifactStore {
  private def keys(name: String): Vector[String] = name match {
    case "metrics/type=community_summaries" => Vector("communityId")
    case "metrics/type=temporal_changes"    => Vector("researcherId", "fromWindowId", "toWindowId")
    case "edges/type=coauthored_with_support" => Vector("edgeId", "workId")
    case n if n.startsWith("nodes/")          => Vector("nodeId")
    case n if n.startsWith("edges/")          => Vector("edgeId")
    case _                                    => Vector("researcherId")
  }
  private val tables = sourceRows.toVector.sortBy(_._1).map { (name, rows) =>
    val manifest = LoadManifest(
      context,
      "s3",
      name,
      Vector(name),
      "parquet",
      rows.size.toLong,
      keys(name),
      Vector("run_id"),
      Phase6RuntimeArtifacts.tableHash(rows),
      windows,
      "storage-engineer",
      Vector.empty
    )
    RuntimeArtifactTable(manifest, rows)
  }
  private val snapshot = RuntimeArtifactSnapshot(
    Phase6RuntimeArtifacts.version,
    context,
    ujson
      .Obj(
        "runManifest" -> ujson.Obj("runId" -> context.runId),
        "runMetadata" -> ujson.Obj("runId" -> context.runId),
        "synthetic" -> true
      )
      .render(),
    tables
  )
  private val objects = new edu.uic.cs441.scholarchain.storage.InMemoryObjectStore(config.maxBytes)
  private val bytes = CoreJson.compact(snapshot).getBytes(UTF_8).toVector
  private val key = "runtime-fake/versions/fixture/snapshot.json"
  private val pointer = RuntimeArtifactPointer(key, StorageKeys.sha256(bytes), context.runId)
  private val upload = objects.put(key, bytes, "application/json", Map.empty)
  require(
    StorageResult.successful(upload),
    "bounded fake artifact must fit its configured object cap"
  )
  private val delegate = new ObjectStoreRuntimeArtifactStore(objects, pointer, config)
  def rank(
      w: String,
      m: RuntimeRankingMetric,
      f: RuntimePopulationFilter,
      l: Int
  ): StorageResult[RuntimeRankingPage] = delegate.rank(w, m, f, l)
  def communitySummary(id: String, w: String): StorageResult[CommunitySummary] =
    delegate.communitySummary(id, w)
  def bridgeMetrics(id: String, w: String): StorageResult[RuntimeBridgeRecord] =
    delegate.bridgeMetrics(id, w)
  def temporalChange(id: String, from: String, to: String): StorageResult[RuntimeTemporalRecord] =
    delegate.temporalChange(id, from, to)
  def edgeSupport(id: String, w: String): StorageResult[RuntimeEdgeRecord] =
    delegate.edgeSupport(id, w)
  def researcherContext(id: String, w: String, l: Int): StorageResult[RuntimeResearcherContext] =
    delegate.researcherContext(id, w, l)
}

final class InMemoryIndexedEvidenceBundleStore(indexPrefix: String = "fake-evidence-items")
    extends EvidenceBundleStore {
  private val delegate = new IndexedEvidenceBundleStore(
    new edu.uic.cs441.scholarchain.storage.InMemoryEvidenceBundleStore,
    new edu.uic.cs441.scholarchain.storage.InMemoryObjectStore,
    indexPrefix
  )
  def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle] = delegate.put(bundle)
  def get(id: String): StorageResult[EvidenceBundle] = delegate.get(id)
  override def getItem(id: String): StorageResult[EvidenceItem] = delegate.getItem(id)
}
