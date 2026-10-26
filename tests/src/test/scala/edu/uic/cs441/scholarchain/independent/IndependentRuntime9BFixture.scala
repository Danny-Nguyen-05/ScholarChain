package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.AtomicInteger

/** Literal G1 facts from the Phase 6 independent specification. The declared community partition
  * and metadata overlays are synthetic test inputs, not outputs of real enrichment or clustering.
  * Overlay authorship rows do not change the original ten-node/nine-edge collaboration fixture.
  */
private[independent] object IndependentRuntime9BFixture {
  val baseConfig = IndependentRuntime9AFixture.config
  val config = baseConfig.copy(windows =
    Vector(
      RuntimeWindow("all-years", None, None, YearWindow(1000, 9999)),
      RuntimeWindow("2015-2017", Some(2015), Some(2017), YearWindow(2015, 2017)),
      RuntimeWindow("2018-2021", Some(2018), Some(2021), YearWindow(2018, 2021))
    )
  )
  val runId = IndependentPhase6G1.sparkRunId
  val policy = IndependentPhase6G1.graphPolicy
  val provenance = IndependentStorageFixtures.provenance.copy(
    runId = runId,
    uncertaintyNotes =
      Vector("Synthetic independently transcribed Phase 6 G1 and declared metadata overlay.")
  )
  val context = SparkRecordContext(
    SchemaVersions.sparkAnalytics,
    runId,
    Some("all-years"),
    SparkLineage(
      IndependentPhase6G1.hadoopRunId,
      IndependentPhase6G1.snapshot,
      IndependentPhase6G1.erRunId,
      IndependentPhase6G1.erPolicy,
      "a" * 64,
      Vector.empty,
      Vector.empty
    )
  )
  val names = ('A' to 'J').map(_.toString).toVector
  def id(name: String): String = IndependentPhase6G1.researcherId(name)
  def component(name: String): String = "component:" + StableIds.sha256Hex(
    if (Set("H", "I")(name)) "g1-hi" else if (name == "J") "g1-j" else "g1-ag"
  )
  def partition(name: String): String = name match {
    case "A" | "B" | "C"       => "left"
    case "D" | "E" | "F" | "G" => "right"
    case "H" | "I"             => "other"
    case _                     => "solo"
  }
  def community(name: String): String = "community:" + StableIds.sha256Hex(partition(name))
  // publication count, distinct coauthors, occurrences, average, maximum, maximizing work, core.
  val expected = Vector(
    ("A", 3L, 2L, 4L, 4.0 / 3.0, 2L, "w1", 2),
    ("B", 3L, 2L, 4L, 4.0 / 3.0, 2L, "w1", 2),
    ("C", 2L, 3L, 3L, 1.5, 2L, "w1", 2),
    ("D", 2L, 3L, 3L, 1.5, 2L, "w4", 2),
    ("E", 2L, 2L, 3L, 1.5, 2L, "w4", 2),
    ("F", 3L, 3L, 4L, 4.0 / 3.0, 2L, "w4", 2),
    ("G", 1L, 1L, 1L, 1.0, 1L, "w6", 1),
    ("H", 1L, 1L, 1L, 1.0, 1L, "w7", 1),
    ("I", 1L, 1L, 1L, 1.0, 1L, "w7", 1),
    ("J", 1L, 0L, 0L, 0.0, 0L, "w8", 0)
  )
  val details = expected.map { (n, p, c, t, a, m, w, core) =>
    ResearcherMetricsDetail(
      context,
      id(n),
      policy,
      p,
      c,
      t,
      a,
      m,
      Vector(IndependentPhase6G1.canonicalWorkId(w)),
      1L,
      t,
      component(n),
      Some(community(n)),
      Some(core)
    )
  }
  val nodes = names.map(n =>
    GraphNode(id(n), SchemaVersions.domain, GraphNodeClass.Researcher, n, Vector.empty, provenance)
  )
  val memberships = names.map(n => CommunityMembership(context, id(n), community(n), 3, false))
  val summaries = Vector("A" -> 3L, "D" -> 4L, "H" -> 2L, "J" -> 1L).map { (n, size) =>
    CommunitySummary(context, community(n), size, 3, 1L, false)
  }
  val bridges = names.map { n =>
    val bridge = n == "C" || n == "D"
    ResearcherBridgeMetrics(
      context,
      id(n),
      policy,
      if (bridge) 1L else 0L,
      if (bridge) 1L else 0L,
      if (bridge) 1L else 0L,
      if (bridge) 4.0 / 9.0 else 0.0
    )
  }
  val edges = IndependentPhase6G1.expectedEdges.filter(_.windowId == "all-years").map { e =>
    val endpoints = Vector(id(e.left), id(e.right)).sorted
    val edgeId = StableIds
      .sparkCoauthorEdgeId(endpoints.head, endpoints.last, IndependentPhase6G1.windows.head, policy)
      .toOption
      .get
    SparkCoauthorEdge(
      context,
      edgeId,
      endpoints.head,
      endpoints.last,
      policy,
      e.weight,
      Some(e.first),
      Some(e.last),
      e.supportingWorks.toVector.sorted.map(IndependentPhase6G1.canonicalWorkId),
      None,
      None
    )
  }
  val supports =
    IndependentPhase6G1.expectedEdges.filter(_.windowId == "all-years").zip(edges).flatMap {
      (e, edge) =>
        e.supportingWorks.toVector.sorted.map { w =>
          CoauthorEdgeSupport(
            context,
            edge.edgeId,
            IndependentPhase6G1.canonicalWorkId(w),
            IndependentPhase6G1.papers.find(_.label == w).get.year
          )
        }
    }
  def edge(a: String, b: String): SparkCoauthorEdge =
    edges.find(e => Set(e.researcherA, e.researcherB) == Set(id(a), id(b))).get
  val topic = StableIds.topicIdFromOpenAlex("T900001").toOption.get
  val otherTopic = StableIds.topicIdFromOpenAlex("T900002").toOption.get
  val institution = StableIds.institutionIdFromOpenAlex("I900001").toOption.get
  val otherInstitution = StableIds.institutionIdFromOpenAlex("I900002").toOption.get
  val venue = StableIds.venueIdFromDblpBooktitle("Synthetic Independent 9B Venue").toOption.get
  val otherVenue =
    StableIds.venueIdFromDblpBooktitle("Synthetic Independent 9B Other Venue").toOption.get
  def association(from: String, kind: GraphEdgeType, to: String, work: String): GraphEdge = {
    val source = GraphSourceEvidence.Work(work)
    GraphEdge(
      StableIds.graphEdgeId(kind, from, to, policy, source).toOption.get,
      SchemaVersions.domain,
      from,
      kind,
      to,
      policy,
      source,
      Vector.empty,
      None,
      provenance
    )
  }
  // Complete authoritative metadata for the synthetic population; A/B are the selected group.
  val overlay = names.map { n =>
    val work = StableIds.workIdFromDblpKey("conf/independent-9b-overlay/" + n).toOption.get
    val selected = Set("A", "B")(n)
    (
      association(id(n), GraphEdgeType.Authored, work, work),
      association(
        id(n),
        GraphEdgeType.AffiliatedWith,
        if (selected) institution else otherInstitution,
        work
      ),
      association(work, GraphEdgeType.HasTopic, if (selected) topic else otherTopic, work),
      association(work, GraphEdgeType.PublishedIn, if (selected) venue else otherVenue, work)
    )
  }
  def row[A: upickle.default.Writer](v: A): ujson.Obj =
    ujson.Obj.from(upickle.default.writeJs(v).obj)
  // D has one coauthor on w3 in the early window and two on w4 in the later window.
  val temporalD = TemporalChange(
    context.copy(windowId = Some("2018-2021")),
    id("D"),
    "2015-2017",
    "2018-2021",
    true,
    true,
    Some(1L),
    Some(1.0),
    Some(1L),
    Some(0L),
    false,
    false,
    Some(community("D")),
    Some(community("D")),
    Some(0.25),
    Some(-1L),
    Some(-1L),
    Some(-1L),
    Some(0.0)
  )
  def artifacts(enriched: Boolean = true, temporal: Boolean = false): RuntimeArtifactStore = {
    val comparisonMemberships =
      if (temporal)
        Vector("2015-2017", "2018-2021").map(w =>
          CommunityMembership(context.copy(windowId = Some(w)), id("D"), community("D"), 3, false)
        )
      else Vector.empty
    val base = Map(
      "nodes/type=researcher" -> nodes.map(row(_)),
      "metrics/type=researcher_collaboration" -> details.map(row(_)),
      "metrics/type=communities" -> (memberships ++ comparisonMemberships).map(row(_)),
      "metrics/type=community_summaries" -> summaries.map(row(_)),
      "metrics/type=bridges" -> bridges.map(row(_)),
      "metrics/type=temporal_changes" -> (if (temporal) Vector(row(temporalD))
                                          else Vector.empty[ujson.Obj]),
      "edges/type=coauthored_with" -> edges.map(row(_)),
      "edges/type=coauthored_with_support" -> supports.map(row(_))
    )
    val additions =
      if (!enriched) Map.empty[String, Vector[ujson.Obj]]
      else
        Map(
          "edges/type=authored" -> overlay.map(v => row(v._1)),
          "edges/type=affiliated_with" -> overlay.map(v => row(v._2)),
          "edges/type=has_topic" -> overlay.map(v => row(v._3)),
          "edges/type=published_in" -> overlay.map(v => row(v._4))
        )
    new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeArtifactStore(
      context.copy(windowId = None),
      base ++ additions,
      if (temporal) config.windowIds else Vector("all-years")
    )
  }
  def metricStore(): InMemoryResearcherMetricStore = {
    val store = new InMemoryResearcherMetricStore
    details.foreach(m =>
      require(
        StorageResult.successful(
          store.put(
            ResearcherMetricRecord(
              m.researcherId,
              "all-years",
              policy,
              runId,
              CoreJson.compact(m),
              "{\"converged\":false,\"iterations\":3}"
            )
          )
        )
      )
    )
    store
  }
  def candidates(ns: String*): Vector[ResearcherCandidate] = ns.toVector.map(n =>
    ResearcherCandidate(
      id(n),
      n,
      Vector("synthetic:" + n),
      Vector.empty,
      None,
      Vector.empty,
      Vector("synthetic-source:" + n),
      Vector(runId)
    )
  )
  def plan(
      operation: QueryOperation,
      ns: Vector[String] = Vector.empty,
      metric: Option[CollaborationMetric] = None,
      mode: RetrievalMode = RetrievalMode.Fused,
      limit: Int = 25,
      depth: Int = 6
  ): QueryPlan = QueryPlan(
    "plan:" + "b" * 64,
    SchemaVersions.domain,
    "synthetic independent 9B question",
    Vector(operation),
    YearWindow(1000, 9999),
    Vector.empty,
    Vector.empty,
    Vector.empty,
    metric,
    limit,
    10,
    depth,
    provenance,
    Some(
      RuntimeQueryOptions(
        researcherNames = ns,
        windowIds = Vector("all-years"),
        retrievalMode = mode,
        evidenceOnly = true,
        rankingMeasure =
          Option.when(operation == QueryOperation.BridgeRanking)("CROSS_COMMUNITY_DEGREE")
      )
    )
  )
  def input(operation: QueryOperation, ns: String*): RetrievalInput =
    RetrievalInput(plan(operation, ns.toVector), candidates(ns*))
  def cache(homonyms: Boolean = false): EntityLinkCache = {
    val cache = new InMemoryEntityLinkCache
    val records = names.map(n => (n, id(n), n)) ++ (if (homonyms)
                                                      Vector(
                                                        ("Name", id("Name 0001"), "Name 0001"),
                                                        ("Name", id("Name 0002"), "Name 0002"),
                                                        ("Name 0001", id("Name 0001"), "Name 0001"),
                                                        ("Name 0002", id("Name 0002"), "Name 0002")
                                                      )
                                                    else Vector.empty)
    records.foreach { (name, researcher, display) =>
      require(
        StorageResult.successful(
          cache.putLink(
            EntityLink(
              "name",
              TextNorm.personName(name),
              policy,
              "synthetic:" + display,
              researcher,
              display,
              Vector.empty,
              None,
              runId,
              Vector("synthetic-evidence:" + display)
            )
          )
        )
      )
    }
    cache
  }
  class Graph extends GraphReader {
    val shortestCalls = new AtomicInteger
    val neighborCalls = new AtomicInteger
    @volatile var pathOverride: Option[StorageResult[Vector[GraphPath]]] = None
    @volatile var delayMillis: Long = 0
    def node(researcher: String): StorageResult[GraphNode] = nodes
      .find(_.nodeId == researcher)
      .map(StorageResult.Found(_))
      .getOrElse(StorageResult.Missing)
    def adjacent(researcher: String): Vector[GraphNeighbor] = edges
      .filter(e => e.researcherA == researcher || e.researcherB == researcher)
      .map(e =>
        GraphNeighbor(
          if (e.researcherA == researcher) e.researcherB else e.researcherA,
          e.edgeId,
          "COAUTHORED_WITH",
          Map("jointPublicationCount" -> e.jointPublicationCount.toString)
        )
      )
    def neighbors(
        researcher: String,
        window: String,
        kinds: Set[String],
        limit: Int,
        cursor: Option[String]
    ): StorageResult[GraphPage] = {
      neighborCalls.incrementAndGet()
      val all = adjacent(researcher)
      StorageResult.Found(GraphPage(all.take(limit), Option.when(all.size > limit)("more")))
    }
    def directCoauthors(researcher: String, window: String, limit: Int): StorageResult[GraphPage] =
      neighbors(researcher, window, Set("COAUTHORED_WITH"), limit, None)
    def shortestPaths(
        a: String,
        b: String,
        maxDepth: Int,
        window: String,
        limit: Int
    ): StorageResult[Vector[GraphPath]] = {
      shortestCalls.incrementAndGet()
      if (delayMillis > 0) Thread.sleep(delayMillis)
      pathOverride.getOrElse {
        val route =
          if (a == id("A") && b == id("G") && maxDepth >= 4)
            Vector(
              GraphPath(
                Vector("A", "C", "D", "F", "G").map(id),
                Vector(
                  edge("A", "C").edgeId,
                  edge("C", "D").edgeId,
                  edge("D", "F").edgeId,
                  edge("F", "G").edgeId
                )
              )
            )
          else Vector.empty
        StorageResult.Found(route.take(limit))
      }
    }
    def communityMembers(
        communityId: String,
        window: String,
        limit: Int
    ): StorageResult[Vector[String]] =
      StorageResult.Found(names.filter(n => community(n) == communityId).map(id).take(limit))
    def crossCommunityEdges(
        communityId: String,
        window: String,
        limit: Int
    ): StorageResult[GraphPage] = {
      val cross =
        if (communityId == community("C"))
          Vector(GraphNeighbor(id("D"), edge("C", "D").edgeId, "COAUTHORED_WITH", Map.empty))
        else if (communityId == community("D"))
          Vector(GraphNeighbor(id("C"), edge("C", "D").edgeId, "COAUTHORED_WITH", Map.empty))
        else Vector.empty
      StorageResult.Found(GraphPage(cross.take(limit), Option.when(cross.size > limit)("more")))
    }
  }
}
