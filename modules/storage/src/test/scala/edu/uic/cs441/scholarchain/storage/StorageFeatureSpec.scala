package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import StorageResult.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*

/** Hand-derived fixtures: no observed identity, dataset or metric claim. */
class StorageFeatureSpec extends AnyFunSuite {
  private val run = "run:00112233-4455-4677-8899-aabbccddeeff"
  private val researcher = "researcher:dblp:" + "a" * 64
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-storage",
    None,
    "synthetic-snapshot",
    None,
    None,
    run,
    Vector("Synthetic feature fixture")
  )
  private val context = SparkRecordContext(
    SchemaVersions.sparkAnalytics,
    run,
    Some("all-years"),
    SparkLineage(
      run,
      "synthetic-snapshot",
      run,
      "synthetic-er",
      "b" * 64,
      Vector("work:dblp:synthetic/a"),
      Vector.empty
    )
  )
  private val node = GraphNode(
    researcher,
    SchemaVersions.domain,
    GraphNodeClass.Researcher,
    "Synthetic Example",
    Vector.empty,
    provenance
  )
  private val detail = ResearcherMetricsDetail(
    context,
    researcher,
    "synthetic-metric",
    2,
    1,
    1,
    0.5,
    1,
    Vector("work:dblp:synthetic/a"),
    1,
    1,
    "component:" + "c" * 64,
    None,
    Some(1)
  )
  private def fixture(rows: Vector[ujson.Obj], dataset: String): LoadManifest = {
    // One fixture row has exactly one nonempty shard. Derive the expected wire hash directly
    // from its documented formula, without invoking the loader's implementation.
    require(rows.size == 1)
    val json = ujson.Obj.from(rows.head.obj.toVector.sortBy(_._1)).render()
    val rowHash = StableIds.sha256Hex(json)
    val finalHash = StableIds.sha256Hex(
      "sha256-fixed-256-shard-sorted-row-json-merkle-v1\n" + rowHash.take(2) + ":1:" + rowHash
    )
    LoadManifest(
      context.copy(windowId = None),
      "s3",
      dataset,
      Vector(dataset),
      "parquet",
      1,
      Vector(
        if (dataset.startsWith("nodes")) "nodeId"
        else if (dataset.startsWith("edges")) "edgeId"
        else "researcherId"
      ),
      Vector("run_id"),
      finalHash,
      Vector("all-years"),
      "storage-engineer",
      Vector.empty
    )
  }
  private class Reader(data: Map[String, Vector[ujson.Obj]]) extends ManifestRowReader {
    var closed = 0
    def qualifications(runId: String): StorageResult[String] = Found("{\"source\":\"synthetic\"}")
    def open(m: LoadManifest): StorageResult[CloseableRowIterator] = {
      val sourceIterator = data(m.logicalDataset).iterator
      Found(new CloseableRowIterator {
        def hasNext: Boolean = sourceIterator.hasNext;
        def next(): ujson.Obj = sourceIterator.next();
        def close(): Unit = { closed += 1 }
      })
    }
  }
  test("ledger requires stage completion and preserves failed retry provenance") {
    val ledger = new InMemoryRunLedger
    assert(ledger.startRun(run).isInstanceOf[Written[?]])
    assert(ledger.recordStage(run, "objects").isInstanceOf[Written[?]])
    assert(ledger.completeRun(run) == Rejected("incomplete-stage"))
    assert(ledger.recordFailure(run, "objects", 1, "synthetic-failure").isInstanceOf[Written[?]])
    assert(ledger.completeRun(run) == Rejected("incomplete-stage"))
    assert(ledger.recordStage(run, "objects").isInstanceOf[Written[?]])
    assert(StorageResult.value(ledger.completeStage(run, "objects")).get.retryCount == 1)
    assert(ledger.completeRun(run).isInstanceOf[Written[?]])
    assert(ledger.startRun(run).isInstanceOf[Unchanged[?]])
    assert(
      StorageResult.value(ledger.getRun(run)).get.failures == Vector(
        RunStage("objects", "failed", 1, Some("synthetic-failure"))
      )
    )
    assert(ledger.recordStage(run, "late") == Rejected("run-not-running"))
  }
  test("every fake store keeps immutable content and repeat counts; object manifest is last") {
    val objects = new InMemoryObjectStore
    val payload =
      ObjectUpload("synthetic/versions/001/data", Vector(1.toByte), "application/octet-stream")
    val manifest =
      ObjectUpload("synthetic/versions/001/manifest", Vector(2.toByte), "application/json")
    val publisher = new RunObjectPublisher(objects)
    assert(publisher.publish(Vector(payload), manifest).isInstanceOf[Written[?]])
    assert(objects.writeOrder.toVector == Vector(payload.key, manifest.key))
    assert(publisher.publish(Vector(payload), manifest).isInstanceOf[Unchanged[?]])
    assert(objects.writeOrder.size == 2)
    val failed = new RunObjectPublisher(new InMemoryObjectStore)
    assert(
      failed.publish(Vector(payload.copy(key = "unversioned")), manifest) == Rejected(
        "unversioned-key"
      )
    )
    val registry = new InMemoryArtifactRegistry
    assert(registry.register("text", "0001", "synthetic://text", "a" * 64).isInstanceOf[Written[?]])
    assert(
      registry.register("text", "0001", "synthetic://text", "b" * 64) == Rejected(
        "immutable-conflict"
      )
    )
    val sessions = new InMemoryQuerySessionStore
    assert(sessions.createIfAbsent("query-1", "same").isInstanceOf[Written[?]])
    assert(sessions.createIfAbsent("query-2", "same") == Rejected("idempotency-key-conflict"))
    assert(sessions.createIfAbsent("query-1", "different") == Rejected("query-id-conflict"))
    assert(sessions.lookupByIdempotencyKey("different") == Missing)
  }
  test(
    "validated canonical metric copies load once and preserve observed convergence true and false"
  ) {
    Vector(true, false).foreach { converged =>
      val nodeRow = ujson.read(CoreJson.compact(node)).asInstanceOf[ujson.Obj]
      val metricRow = ujson.read(CoreJson.compact(detail)).asInstanceOf[ujson.Obj]
      val community =
        CommunityMembership(context, researcher, "community:" + "d" * 64, 20, converged)
      val communityRow = ujson.read(CoreJson.compact(community)).asInstanceOf[ujson.Obj]
      val data = Map(
        "nodes/type=researcher" -> Vector(nodeRow),
        "metrics/type=researcher_collaboration" -> Vector(metricRow),
        "metrics/type=kcore" -> Vector(metricRow),
        "metrics/type=communities" -> Vector(communityRow)
      )
      val reader = new Reader(data); val links = new InMemoryEntityLinkCache;
      val metrics = new InMemoryResearcherMetricStore
      val loader =
        new Phase6CacheLoader(
          links,
          metrics,
          reader,
          CacheLoaderConfig(sortChunkRows = 1),
          new InMemoryObjectStore,
          new InMemoryArtifactRegistry
        )
      val manifests = data.toVector.map((name, rows) => fixture(rows, name))
      assert(loader.load(manifests) == Written(CacheLoadReport(2, 0, 0, 4)))
      assert(loader.load(manifests) == Unchanged(CacheLoadReport(0, 2, 0, 4)))
      val record = StorageResult.value(metrics.get(researcher, "all-years")).get
      assert(record.payloadJson == CoreJson.compact(detail))
      assert(
        ujson.read(record.qualificationsJson)("communityMembership")("converged").bool == converged
      )
      assert(reader.closed == 8)
    }
  }
  test(
    "hash mismatch, wrong count and conflicting duplicate metric copies are rejected before writes"
  ) {
    val row = ujson.read(CoreJson.compact(detail)).asInstanceOf[ujson.Obj]
    val reader = new Reader(Map("metrics/type=researcher_collaboration" -> Vector(row)))
    val metrics = new InMemoryResearcherMetricStore
    val loader = new Phase6CacheLoader(
      new InMemoryEntityLinkCache,
      metrics,
      reader,
      sourceObjects = new InMemoryObjectStore,
      sourceRegistry = new InMemoryArtifactRegistry
    )
    val m = fixture(Vector(row), "metrics/type=researcher_collaboration")
    assert(
      loader.load(Vector(m.copy(sortedRowsSha256 = "0" * 64))) == Rejected(
        "manifest-content-hash-mismatch"
      )
    )
    assert(loader.load(Vector(m.copy(rowCount = 2))) == Rejected("manifest-row-count-mismatch"))
    assert(metrics.get(researcher, "all-years") == Missing)
    val conflicting = ujson
      .read(CoreJson.compact(detail.copy(policyVersion = "conflicting-version")))
      .asInstanceOf[ujson.Obj]
    val duplicateReader = new Reader(
      Map(
        "metrics/type=researcher_collaboration" -> Vector(row),
        "metrics/type=kcore" -> Vector(conflicting)
      )
    )
    val duplicateLoader =
      new Phase6CacheLoader(
        new InMemoryEntityLinkCache,
        metrics,
        duplicateReader,
        sourceObjects = new InMemoryObjectStore,
        sourceRegistry = new InMemoryArtifactRegistry
      )
    assert(
      duplicateLoader.load(
        Vector(m, fixture(Vector(conflicting), "metrics/type=kcore"))
      ) == Rejected("conflicting-duplicate-metric")
    )
    assert(metrics.get(researcher, "all-years") == Missing)
  }
  test(
    "graph and vector main fakes provide usable deterministic retrieval without provider calls"
  ) {
    val other = node.copy(nodeId = "researcher:dblp:" + "e" * 64)
    val graph = new InMemoryGraphReader(
      Vector(node, other),
      Vector(
        FakeGraphEdge(researcher, other.nodeId, "edge-fixture", "COAUTHORED_WITH", "all-years")
      )
    )
    assert(
      StorageResult
        .value(graph.directCoauthors(researcher, "all-years", 1))
        .get
        .items
        .map(_.nodeId) == Vector(other.nodeId)
    )
    assert(
      StorageResult
        .value(graph.shortestPaths(researcher, other.nodeId, 1, "all-years", 1))
        .get
        .head
        .nodeIds == Vector(researcher, other.nodeId)
    )
    val vectors = new InMemoryVectorStore
    assert(vectors.ensureIndex("researcher-profile-v1", 2, "euclidean").isInstanceOf[Written[?]])
    assert(
      vectors
        .putBatch(
          "researcher-profile-v1",
          Vector(
            VectorDocument("one", Vector(0f, 0f), Map("type" -> "researcher"), "a" * 64),
            VectorDocument("two", Vector(3f, 4f), Map("type" -> "researcher"), "b" * 64)
          )
        )
        .isInstanceOf[Written[?]]
    )
    val hits = StorageResult
      .value(vectors.query("researcher-profile-v1", Vector(0f, 0f), 2, Map("type" -> "researcher")))
      .get
    assert(hits.map(h => h.key -> h.distance) == Vector("one" -> 0.0, "two" -> 5.0))
  }
  test("support keys use collision-safe edge and work pairs without altering either Spark ID") {
    assert(StorageKeys.support("a#b", "c") != "a#b#c")
    assert(StorageKeys.support("a#b", "c") != StorageKeys.support("a", "b#c"))
    assert(
      StorageKeys.support(
        "edge-unchanged",
        "work-unchanged"
      ) == "14:edge-unchanged14:work-unchanged"
    )
  }
  test("stream IO failures receive bounded retries and sanitized exhaustion") {
    val retry =
      new StorageRetry(RetryConfig(maxAttempts = 2, baseDelayMillis = 0, maxDelayMillis = 0))
    var attempts = 0
    val succeeds = retry {
      attempts += 1; if (attempts == 1) throw new java.io.IOException("synthetic-private-detail");
      Found("body")
    }
    assert(succeeds == Retried(1, Found("body")))
    assert(attempts == 2)
    val fails = retry[String] { throw new java.io.IOException("synthetic-private-detail") }
    assert(fails == Retried(1, Rejected("transport-retry-exhausted")))
    assert(!fails.toString.contains("synthetic-private-detail"))
  }

  test("valid researcher indexes authorize applied mention aliases before cache publication") {
    val mention = node.copy(
      nodeId = "mention:dblp:" + "f" * 64,
      nodeClass = GraphNodeClass.AuthorMention,
      label = "Synthetic Alias"
    )
    val nodeRow = ujson.read(CoreJson.compact(node)).asInstanceOf[ujson.Obj]
    val mentionRow = ujson.read(CoreJson.compact(mention)).asInstanceOf[ujson.Obj]
    val edge = ujson.Obj(
      "edgeId" -> "synthetic-resolution-edge",
      "fromId" -> mention.nodeId,
      "toId" -> node.nodeId,
      "context" -> ujson.read(CoreJson.compact(context))
    )
    val data = Map(
      "nodes/type=researcher" -> Vector(nodeRow),
      "nodes/type=author_mention" -> Vector(mentionRow),
      "edges/type=resolves_to" -> Vector(edge)
    )
    val links = new InMemoryEntityLinkCache
    val loader = new Phase6CacheLoader(
      links,
      new InMemoryResearcherMetricStore,
      new Reader(data),
      sourceObjects = new InMemoryObjectStore,
      sourceRegistry = new InMemoryArtifactRegistry
    )
    val result = loader.load(data.toVector.map((name, rows) => fixture(rows, name)))
    assert(result == Written(CacheLoadReport(2, 0, 0, 3)))
    val alias = StorageResult.value(links.lookupByNormalizedName("Synthetic Alias")).get
    assert(alias.size == 1)
    assert(alias.head.researcherId == node.nodeId)
    assert(alias.head.sourceId == mention.nodeId)
    assert(alias.head.evidenceRefs == Vector("edges/type=resolves_to", "synthetic-resolution-edge"))
  }

}
