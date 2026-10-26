package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{Callable, CyclicBarrier, Executors, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import upickle.default.writeJs
import StorageResult.*

/** Synthetic three-person star: A has two distinct coauthors, B/C have one each. These expected
  * answers are specified independently of ranking and retrieval implementations.
  */
class RuntimeArtifactStorageSpec extends AnyFunSuite {
  private val run = "run:00112233-4455-4677-8899-aabbccddeeff"
  private val a = "researcher:dblp:" + "a" * 64
  private val b = "researcher:dblp:" + "b" * 64
  private val c = "researcher:dblp:" + "c" * 64
  private val people = Vector(a, b, c)
  private val communities = people.map(id => "community:" + StableIds.sha256Hex(id))
  private val lineage = SparkLineage(
    run,
    "synthetic-snapshot",
    run,
    "synthetic-er",
    "e" * 64,
    Vector.empty,
    Vector.empty
  )
  private val context = SparkRecordContext(SchemaVersions.sparkAnalytics, run, None, lineage)
  private val cw = context.copy(windowId = Some("all-years"))
  private val windows = Vector("all-years", "2010-2014", "2015-2019", "empty-window")
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-source",
    None,
    "synthetic-snapshot",
    None,
    None,
    run,
    Vector("Synthetic fixture only")
  )
  private val w1 = "work:dblp:synthetic/ab"
  private val w2 = "work:dblp:synthetic/ac"
  private val topic1 = "topic:openalex:T1"
  private val topic2 = "topic:openalex:T2"
  private val venue = "venue:dblp-booktitle:synthetic"
  private val institution = "institution:openalex:I4"
  private val otherInstitution = "institution:openalex:I5"
  private def obj[A: upickle.default.Writer](v: A): ujson.Obj = writeJs(v).obj match {
    case fields => ujson.Obj.from(fields)
  }
  private def node(id: String, kind: GraphNodeClass = GraphNodeClass.Researcher): GraphNode =
    GraphNode(
      id,
      SchemaVersions.domain,
      kind,
      "Synthetic " + id.takeRight(1),
      Vector.empty,
      provenance
    )
  private val metrics = people.zipWithIndex.map { (id, i) =>
    val degree = if (i == 0) 2L else 1L
    ResearcherMetricsDetail(
      cw,
      id,
      "synthetic-metrics",
      degree,
      degree,
      degree,
      1.0,
      1,
      Vector(if (i == 2) w2 else w1),
      degree,
      degree,
      "component:" + "f" * 64,
      Some(communities(i)),
      Some(1)
    )
  }
  private val membership =
    people.zipWithIndex.map((id, i) => CommunityMembership(cw, id, communities(i), 20, false))
  private val bridge = people.zipWithIndex.map((id, i) =>
    ResearcherBridgeMetrics(
      cw,
      id,
      "synthetic-bridges",
      if (i == 0) 2 else 1,
      if (i == 0) 2 else 1,
      if (i == 0) 2 else 1,
      if (i == 0) 0.5 else 0.0
    )
  )
  private val edges = Vector(b -> w1, c -> w2).map { (other, work) =>
    val id = StableIds
      .sparkCoauthorEdgeId(a, other, SparkWindow("all-years", None, None, None), "synthetic-graph")
      .toOption
      .get
    SparkCoauthorEdge(
      cw,
      id,
      a,
      other,
      "synthetic-graph",
      1,
      Some(2015),
      Some(2015),
      Vector(work),
      None,
      None
    )
  }
  private val support =
    edges.map(e => CoauthorEdgeSupport(cw, e.edgeId, e.representativeWorkIds.head, Some(2015)))
  private def graphEdge(from: String, to: String, kind: GraphEdgeType): GraphEdge = {
    val supportingWork = kind match {
      case GraphEdgeType.Authored                             => to
      case GraphEdgeType.HasTopic | GraphEdgeType.PublishedIn => from
      case _                                                  => w1
    }
    val evidence = GraphSourceEvidence.Work(supportingWork)
    val edge = GraphEdge(
      StableIds.graphEdgeId(kind, from, to, "synthetic-association", evidence).toOption.get,
      SchemaVersions.domain,
      from,
      kind,
      to,
      "synthetic-association",
      evidence,
      Vector.empty,
      None,
      provenance
    )
    require(DomainValidation.check(edge).isRight, DomainValidation.check(edge).toString)
    edge
  }
  private val temporal = TemporalChange(
    context.copy(windowId = Some("2015-2019")),
    a,
    "2010-2014",
    "2015-2019",
    false,
    true,
    None,
    None,
    None,
    None,
    true,
    false,
    None,
    Some(communities.head),
    None,
    None,
    None,
    None,
    None
  )
  private val source: Map[String, Vector[ujson.Obj]] = Map(
    "nodes/type=researcher" -> people.map(id => obj(node(id))),
    "nodes/type=topic" -> Vector(
      obj(node(topic1, GraphNodeClass.Topic)),
      obj(node(topic2, GraphNodeClass.Topic))
    ),
    "nodes/type=venue" -> Vector(obj(node(venue, GraphNodeClass.Venue))),
    "nodes/type=institution" -> Vector(
      obj(node(institution, GraphNodeClass.Institution)),
      obj(node(otherInstitution, GraphNodeClass.Institution))
    ),
    "metrics/type=researcher_collaboration" -> metrics.map(obj(_)),
    "metrics/type=communities" -> membership.map(obj(_)),
    "metrics/type=community_summaries" -> communities.map(id =>
      obj(CommunitySummary(cw, id, 1, 20, 1, false))
    ),
    "metrics/type=bridges" -> bridge.map(obj(_)),
    "metrics/type=temporal_changes" -> Vector(obj(temporal)),
    "edges/type=coauthored_with" -> edges.map(obj(_)),
    "edges/type=coauthored_with_support" -> support.map(obj(_)),
    "edges/type=authored" -> Vector(
      graphEdge(a, w1, GraphEdgeType.Authored),
      graphEdge(a, w2, GraphEdgeType.Authored),
      graphEdge(b, w1, GraphEdgeType.Authored),
      graphEdge(c, w2, GraphEdgeType.Authored)
    ).map(obj(_)),
    "edges/type=has_topic" -> Vector(
      graphEdge(w1, topic1, GraphEdgeType.HasTopic),
      graphEdge(w2, topic2, GraphEdgeType.HasTopic)
    ).map(obj(_)),
    "edges/type=published_in" -> Vector(
      graphEdge(w1, venue, GraphEdgeType.PublishedIn),
      graphEdge(w2, venue, GraphEdgeType.PublishedIn)
    ).map(obj(_)),
    "edges/type=affiliated_with" -> people.map(id =>
      obj(
        graphEdge(id, if (id == a) institution else otherInstitution, GraphEdgeType.AffiliatedWith)
      )
    )
  )
  private def fake(
      rows: Map[String, Vector[ujson.Obj]] = source,
      config: RuntimeArtifactConfig = RuntimeArtifactConfig()
  ) =
    new fakes.InMemoryRuntimeArtifactStore(context, rows, windows, config)
  private def found[A](r: StorageResult[A]): A = StorageResult.value(r).getOrElse(fail(r.toString))

  test("complete population is ranked by stored values with deterministic ties and honest top-K") {
    val result = found(
      fake()
        .rank("all-years", RuntimeRankingMetric.DistinctCoauthorCount, RuntimePopulationFilter(), 2)
    )
    assert(result.items.map(_.metric.researcherId) == Vector(a, b))
    assert(result.items.map(_.rankingValue) == Vector("2", "1"))
    assert(result.populationCount == 3 && result.matchedCount == 3 && result.truncated)
    assert(result.sourceRunId == run && result.sourceArtifactHash.matches("[0-9a-f]{64}"))
    assert(
      found(
        fake().rank(
          "empty-window",
          RuntimeRankingMetric.DistinctCoauthorCount,
          RuntimePopulationFilter(),
          2
        )
      ).items.isEmpty
    )
  }
  test("filters select authoritative population BEFORE stored-metric ranking and disclose scope") {
    val result = found(
      fake().rank(
        "all-years",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(
          topicIds = Vector(topic1),
          institutionIds = Vector(otherInstitution),
          venueIds = Vector(venue)
        ),
        1
      )
    )
    assert(result.items.map(_.metric.researcherId) == Vector(b))
    assert(result.populationCount == 3 && result.matchedCount == 1 && !result.truncated)
    assert(result.items.head.metric.distinctCoauthorCount == 1)
    assert(result.filters.metricScope == "population")
  }
  test("absent authoritative metadata, unavailable filtered metrics and unknown windows reject") {
    assert(
      fake(source - "edges/type=has_topic").rank(
        "all-years",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(topicIds = Vector(topic1)),
        1
      ) == Rejected("unsupported-authoritative-filter-metadata")
    )
    assert(
      fake().rank(
        "all-years",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(metricScope = "publication-subgraph"),
        1
      ) == Rejected("unsupported-filtered-metric-scope")
    )
    assert(
      fake().rank(
        "unknown",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(),
        1
      ) == Rejected("unsupported-runtime-window")
    )
    assert(
      fake().rank(
        "all-years",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(),
        101
      ) == Rejected("runtime-result-bound")
    )
  }
  test("bridge and community records preserve degree and iteration-limited qualifications") {
    val store = fake()
    val result = found(store.bridgeMetrics(a, "all-years"))
    assert(result.metrics.crossCommunityDegree == 2 && result.metrics.communitiesConnected == 2)
    assert(result.metrics.participationCoefficient == 0.5 && result.distinctCoauthorCount == 2)
    assert(!result.membership.converged && result.membership.iterations == 20)
    val summary = found(store.communitySummary(communities.head, "all-years"))
    assert(summary.size == 1 && !summary.converged && summary.iterations == 20)
    assert(
      found(
        store.rank(
          "all-years",
          RuntimeRankingMetric.CrossCommunityDegree,
          RuntimePopulationFilter(),
          1
        )
      ).items.head.rankingValue == "2"
    )
  }
  test("edge support, context caps and temporal absent-side semantics retain source records") {
    val store = fake()
    val edge = found(store.edgeSupport(edges.head.edgeId, "all-years"))
    assert(edge.edge.jointPublicationCount == 1 && edge.support.map(_.workId) == Vector(w1))
    assert(edge.support.head.year.contains(2015) && edge.support.head.context.runId == run)
    val researcher = found(store.researcherContext(a, "all-years", 1))
    assert(researcher.coauthorIds == Vector(b) && researcher.coauthorsTruncated)
    assert(researcher.topicIds.contains(Vector(topic1, topic2)) && researcher.sourceRunId == run)
    assert(
      researcher.sourceRefs.exists(ref =>
        ref.table == "edges/type=coauthored_with" && ref.rowKey == edges.head.edgeId
      )
    )
    assert(
      !researcher.sourceRefs.exists(ref =>
        ref.table == "edges/type=coauthored_with" && ref.rowKey == a
      )
    )
    val change = found(store.temporalChange(a, "2010-2014", "2015-2019"))
    assert(change.change == temporal && change.change.deltaDistinctCoauthors.isEmpty)
    assert(store.edgeSupport("missing", "all-years") == Missing)
  }
  test(
    "context distinguishes a stored window with absent researcher metrics from an unknown window"
  ) {
    val period = "2015-2019"
    val periodMetric = metrics.head.copy(context = context.copy(windowId = Some(period)))
    val store = fake(
      source.updated(
        "metrics/type=researcher_collaboration",
        source("metrics/type=researcher_collaboration") :+ obj(periodMetric)
      )
    )
    assert(found(store.researcherContext(a, period, 1)).researcherId == a)
    assert(store.researcherContext(b, period, 1) == Missing)
    assert(store.researcherContext(b, "empty-window", 1) == Missing)
    assert(store.researcherContext("researcher:dblp:" + "d" * 64, period, 1) == Missing)
    assert(store.researcherContext(b, "never-stored", 1) == Rejected("unsupported-runtime-window"))
  }
  private def manifests(rows: Map[String, Vector[ujson.Obj]]): Vector[LoadManifest] =
    rows.toVector.sortBy(_._1).map { (name, values) =>
      val keys =
        if (name == "metrics/type=community_summaries") Vector("communityId")
        else if (name == "metrics/type=temporal_changes")
          Vector("researcherId", "fromWindowId", "toWindowId")
        else if (name == "edges/type=coauthored_with_support") Vector("edgeId", "workId")
        else if (name.startsWith("nodes/")) Vector("nodeId")
        else if (name.startsWith("edges/")) Vector("edgeId")
        else Vector("researcherId")
      LoadManifest(
        context,
        "s3",
        name,
        Vector(name),
        "parquet",
        values.size.toLong,
        keys,
        Vector("run_id"),
        Phase6RuntimeArtifacts.tableHash(values),
        windows,
        "storage-engineer",
        Vector.empty
      )
    }
  private class Reader(rows: Map[String, Vector[ujson.Obj]]) extends ManifestRowReader {
    var opened = 0
    def qualifications(id: String): StorageResult[String] = Found(
      ujson
        .Obj("runManifest" -> ujson.Obj("runId" -> id), "runMetadata" -> ujson.Obj("runId" -> id))
        .render()
    )
    def open(m: LoadManifest): StorageResult[CloseableRowIterator] = {
      opened += 1
      val sourceIterator = rows(m.logicalDataset).iterator
      Found(new CloseableRowIterator {
        def hasNext: Boolean = sourceIterator.hasNext
        def next(): ujson.Obj = sourceIterator.next()
        def close(): Unit = ()
      })
    }
  }
  test(
    "source-verified materialization publishes immutable content and the real object reader works"
  ) {
    val objects = new InMemoryObjectStore
    val key = "runtime/versions/synthetic/snapshot.json"
    val pointer =
      found(Phase6RuntimeArtifacts.publish(manifests(source), new Reader(source), objects, key))
    assert(
      Phase6RuntimeArtifacts.publish(
        manifests(source),
        new Reader(source),
        objects,
        key
      ) == Unchanged(pointer)
    )
    val real = new ObjectStoreRuntimeArtifactStore(objects, pointer)
    assert(
      found(
        real.rank(
          "all-years",
          RuntimeRankingMetric.DistinctCoauthorCount,
          RuntimePopulationFilter(),
          1
        )
      ).items.head.metric == metrics.head
    )
    assert(
      new ObjectStoreRuntimeArtifactStore(objects, pointer.copy(sha256 = "0" * 64))
        .bridgeMetrics(a, "all-years") == Rejected("runtime-artifact-content-mismatch")
    )
    assert(
      new ObjectStoreRuntimeArtifactStore(objects, pointer.copy(sourceRunId = "other"))
        .bridgeMetrics(a, "all-years") == Rejected("runtime-artifact-run-mismatch")
    )
  }
  private def preparedArtifact(): (InMemoryObjectStore, RuntimeArtifactPointer) = {
    val objects = new InMemoryObjectStore
    val pointer = found(
      Phase6RuntimeArtifacts.publish(
        manifests(source),
        new Reader(source),
        objects,
        "runtime/versions/cache-fixture/snapshot.json"
      )
    )
    (objects, pointer)
  }
  private class CountingObjectStore(
      delegate: ObjectStore,
      response: Int => Option[StorageResult[StoredObject]]
  ) extends ObjectStore {
    val reads = new AtomicInteger
    def put(
        key: String,
        bytes: Vector[Byte],
        contentType: String,
        metadata: Map[String, String]
    ): StorageResult[ObjectHead] =
      fail("runtime artifact reader must never write")
    def head(key: String): StorageResult[ObjectHead] = fail(
      "runtime artifact reader needs only its initial bounded GET"
    )
    def get(key: String): StorageResult[StoredObject] = {
      val count = reads.incrementAndGet()
      response(count).getOrElse(delegate.get(key))
    }
  }
  test(
    "mixed warm artifact calls reuse one verified snapshot even when subsequent GETs would throw"
  ) {
    val (objects, pointer) = preparedArtifact()
    val counted = new CountingObjectStore(
      objects,
      count => {
        if (count > 1) throw new IllegalStateException("second object GET forbidden") else None
      }
    )
    val store = new ObjectStoreRuntimeArtifactStore(counted, pointer)
    assert(found(store.researcherContext(a, "all-years", 1)).coauthorIds == Vector(b))
    assert(
      found(
        store.rank(
          "all-years",
          RuntimeRankingMetric.DistinctCoauthorCount,
          RuntimePopulationFilter(),
          1
        )
      ).items.head.metric.researcherId == a
    )
    assert(found(store.bridgeMetrics(a, "all-years")).metrics.crossCommunityDegree == 2)
    assert(found(store.communitySummary(communities.head, "all-years")).size == 1)
    assert(
      found(store.edgeSupport(edges.head.edgeId, "all-years")).support.map(_.workId) == Vector(w1)
    )
    assert(found(store.temporalChange(a, "2010-2014", "2015-2019")).change == temporal)
    assert(store.researcherContext(a, "never-stored", 1) == Rejected("unsupported-runtime-window"))
    assert(counted.reads.get() == 1)
  }
  test("concurrent cold mixed calls share one successful load and safely reuse immutable indexes") {
    val (objects, pointer) = preparedArtifact()
    val counted = new CountingObjectStore(
      objects,
      count => {
        if (count > 1) throw new IllegalStateException("concurrent duplicate GET forbidden")
        else None
      }
    )
    val store = new ObjectStoreRuntimeArtifactStore(counted, pointer)
    val workers = 6
    val barrier = new CyclicBarrier(workers)
    val executor = Executors.newFixedThreadPool(workers)
    try {
      val calls: Vector[() => Boolean] = Vector(
        () => found(store.researcherContext(a, "all-years", 1)).coauthorIds == Vector(b),
        () =>
          found(
            store.rank(
              "all-years",
              RuntimeRankingMetric.CrossCommunityDegree,
              RuntimePopulationFilter(),
              1
            )
          ).items.head.rankingValue == "2",
        () => found(store.bridgeMetrics(a, "all-years")).membership.iterations == 20,
        () => found(store.communitySummary(communities.head, "all-years")).size == 1,
        () => found(store.edgeSupport(edges.head.edgeId, "all-years")).support.head.workId == w1,
        () => found(store.temporalChange(a, "2010-2014", "2015-2019")).change == temporal
      )
      val futures = calls.map(action =>
        executor.submit(new Callable[Boolean] {
          def call(): Boolean = {
            barrier.await(10, TimeUnit.SECONDS)
            action.apply()
          }
        })
      )
      assert(futures.forall(_.get(10, TimeUnit.SECONDS)))
      assert(counted.reads.get() == 1)
    } finally executor.shutdownNow()
  }
  test(
    "failed first loads are not cached; transient rejection and corrupt first bytes remain retryable"
  ) {
    val (objects, pointer) = preparedArtifact()
    val good = found(objects.get(pointer.key))
    val firstResponses: Vector[StorageResult[StoredObject]] = Vector(
      Rejected("synthetic-throttled"),
      Missing,
      Found(good.copy(bytes = good.bytes.updated(0, 'x'.toByte)))
    )
    firstResponses.zipWithIndex.foreach { (first, index) =>
      val counted = new CountingObjectStore(objects, count => if (count == 1) Some(first) else None)
      val store = new ObjectStoreRuntimeArtifactStore(counted, pointer)
      val initial = store.bridgeMetrics(a, "all-years")
      if (index == 0) assert(initial == Rejected("synthetic-throttled"))
      else if (index == 1) assert(initial == Missing)
      else assert(initial == Rejected("runtime-artifact-content-mismatch"))
      assert(found(store.bridgeMetrics(a, "all-years")).metrics.crossCommunityDegree == 2)
      assert(found(store.researcherContext(a, "all-years", 1)).coauthorIds == Vector(b))
      assert(counted.reads.get() == 2)
    }
  }
  test(
    "declared caps reject before opening sources; changed rows or actual overruns publish nothing"
  ) {
    val objects = new InMemoryObjectStore
    val reader = new Reader(source)
    assert(
      Phase6RuntimeArtifacts.publish(
        manifests(source),
        reader,
        objects,
        "runtime/versions/cap/data",
        RuntimeArtifactConfig(maxRows = 1)
      ) == Rejected("runtime-artifact-row-bound")
    )
    assert(reader.opened == 0 && objects.writeOrder.isEmpty)
    val changed = source.updated(
      "metrics/type=researcher_collaboration",
      Vector(obj(metrics.head.copy(distinctCoauthorCount = 1))) ++ source(
        "metrics/type=researcher_collaboration"
      ).tail
    )
    assert(
      Phase6RuntimeArtifacts.publish(
        manifests(source),
        new Reader(changed),
        objects,
        "runtime/versions/changed/data"
      ) == Rejected("runtime-source-logical-hash-mismatch")
    )
    assert(objects.writeOrder.isEmpty)
  }
  test(
    "duplicate keys, missing supporting works and mismatched bridge qualifications fail closed"
  ) {
    assert(
      fake(
        source.updated(
          "metrics/type=researcher_collaboration",
          source("metrics/type=researcher_collaboration") :+ source(
            "metrics/type=researcher_collaboration"
          ).head
        )
      ).bridgeMetrics(a, "all-years") == Rejected("runtime-artifact-duplicate-source-key")
    )
    assert(
      fake(
        source.updated(
          "edges/type=coauthored_with_support",
          source("edges/type=coauthored_with_support").tail
        )
      ).edgeSupport(edges.head.edgeId, "all-years") == Rejected(
        "runtime-artifact-edge-support-mismatch"
      )
    )
    assert(
      fake(
        source.updated(
          "metrics/type=bridges",
          Vector(
            obj(bridge.head.copy(crossCommunityDegree = 3, crossCommunityWeight = 3))
          ) ++ source("metrics/type=bridges").tail
        )
      ).bridgeMetrics(a, "all-years") == Rejected("runtime-artifact-bridge-binding-mismatch")
    )
  }

  test(
    "real cache loader publishes base-name homonym candidates without merging suffix identities"
  ) {
    val rows = Map(
      "nodes/type=researcher" -> Vector(
        obj(node(a).copy(label = "Name 0001")),
        obj(node(b).copy(label = "Name 0002"))
      )
    )
    val cache = new InMemoryEntityLinkCache
    val loaded = new Phase6CacheLoader(
      cache,
      new InMemoryResearcherMetricStore,
      new Reader(rows),
      CacheLoaderConfig(),
      new InMemoryObjectStore,
      new InMemoryArtifactRegistry
    ).load(manifests(rows))
    assert(StorageResult.successful(loaded))
    val candidates = found(cache.lookupByNormalizedName("Name"))
    assert(candidates.map(_.researcherId).toSet == Set(a, b))
    assert(candidates.map(_.displayName).toSet == Set("Name 0001", "Name 0002"))
    assert(candidates.forall(_.confidence.isEmpty))
    assert(found(cache.lookupByNormalizedName("Name 0001")).map(_.researcherId) == Vector(a))
    assert(found(cache.lookupByNormalizedName("Name 0002")).map(_.researcherId) == Vector(b))
  }

  private val evidenceId = StableIds
    .nonTextEvidenceId(
      "metric",
      Seq(a, CollaborationMetric.DistinctCoauthorCount.wire, "2015", "2019", "synthetic-metric")
    )
    .toOption
    .get
  private val item = EvidenceItem(
    evidenceId,
    SchemaVersions.domain,
    EvidenceType.Metric,
    None,
    "synthetic://metrics",
    None,
    None,
    Some(
      MetricEvidenceLocator(
        a,
        CollaborationMetric.DistinctCoauthorCount,
        2015,
        2019,
        "synthetic-metric"
      )
    ),
    None,
    1.0,
    Some("Synthetic two coauthors"),
    provenance
  )
  private val bundle = EvidenceBundle(
    "synthetic-bundle",
    SchemaVersions.domain,
    "synthetic-query",
    Vector(item),
    Vector(a),
    Vector("synthetic-metric"),
    None,
    "Synthetic only",
    provenance
  )
  test("evidence item lookup works by frozen ID, repeated puts and sharing immutable content") {
    val indexed = new IndexedEvidenceBundleStore(
      new InMemoryEvidenceBundleStore,
      new InMemoryObjectStore,
      "item-index"
    )
    assert(indexed.getItem(evidenceId) == Missing)
    assert(indexed.put(bundle).isInstanceOf[Written[?]])
    assert(indexed.put(bundle).isInstanceOf[Unchanged[?]])
    assert(indexed.getItem(evidenceId) == Found(item))
    assert(indexed.put(bundle.copy(bundleId = "second-bundle")).isInstanceOf[Written[?]])
    assert(indexed.getItem(evidenceId) == Found(item))
    assert(
      indexed.put(
        bundle.copy(
          bundleId = "conflicting-bundle",
          items = Vector(item.copy(text = Some("Different content")))
        )
      ) == Rejected("evidence-item-id-conflict")
    )
    val fake = new fakes.InMemoryIndexedEvidenceBundleStore
    assert(StorageResult.successful(fake.put(bundle)) && fake.getItem(evidenceId) == Found(item))
  }
  test("evidence index corruption and failed required index write cannot report success") {
    val objects = new InMemoryObjectStore
    val indexed =
      new IndexedEvidenceBundleStore(new InMemoryEvidenceBundleStore, objects, "item-index")
    val key = StorageKeys.versioned(
      "item-index",
      "item-index-v1",
      StableIds.sha256Hex(evidenceId) + ".json"
    )
    found(objects.put(key, "{}".getBytes(UTF_8).toVector, "application/json", Map.empty))
    assert(indexed.getItem(evidenceId) == Rejected("corrupt-evidence-item-pointer"))
    val failed = new ObjectStore {
      def put(
          k: String,
          bytes: Vector[Byte],
          contentType: String,
          metadata: Map[String, String]
      ): StorageResult[ObjectHead] = Rejected("synthetic-write-failed")
      def get(k: String): StorageResult[StoredObject] = Missing
      def head(k: String): StorageResult[ObjectHead] = Missing
    }
    val underlying = new InMemoryEvidenceBundleStore
    val failure = new IndexedEvidenceBundleStore(underlying, failed, "failed-index")
    assert(failure.put(bundle) == Rejected("evidence-item-index-write-failed"))
    assert(underlying.get(bundle.bundleId) == Found(bundle))
    assert(failure.getItem(evidenceId) == Missing)
  }
}
