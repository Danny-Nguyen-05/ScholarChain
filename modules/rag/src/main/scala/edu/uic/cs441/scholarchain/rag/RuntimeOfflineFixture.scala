package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*

/** Literal Phase6 G1 inputs and hand-derived all-years values. Community labels and metadata below
  * are declared synthetic overlays; neither a real clustering result nor enrichment coverage.
  */
object RuntimeOfflineFixture {
  val run = "run:55555555-5555-4555-8555-555555555555"
  val upstream = "run:33333333-3333-4333-8333-333333333333"
  val er = "run:44444444-4444-4444-8444-444444444444"
  val policy = "module-g1-v1"
  val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-9b-g1",
    None,
    "synthetic-9b",
    Some("2026-10-26"),
    None,
    run,
    Vector("Synthetic Phase6 G1 fixture; overlays separate.")
  )
  val context = SparkRecordContext(
    SchemaVersions.sparkAnalytics,
    run,
    Some("all-years"),
    SparkLineage(upstream, "synthetic-9b", er, policy, "a" * 64, Vector.empty, Vector.empty)
  )
  val baseConfig: RuntimeConfig = {
    val in = getClass.getResourceAsStream("/scholarchain.runtime-config.v1.json")
    try
      RuntimeConfigLoader
        .fromJson(new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8))
        .toOption
        .get
    finally in.close()
  }
  val config = baseConfig.copy(
    windows = Vector(
      RuntimeWindow("all-years", None, None, YearWindow(1000, 9999)),
      RuntimeWindow("2015-2017", Some(2015), Some(2017), YearWindow(2015, 2017)),
      RuntimeWindow("2018-2021", Some(2018), Some(2021), YearWindow(2018, 2021))
    ),
    retrievalMode = RetrievalMode.Graph,
    evidenceOnly = false
  )
  def id(n: String): String = StableIds.researcherIdFromDblpName(policy, n).toOption.get
  def work(n: String): String = StableIds.workIdFromDblpKey("conf/module-g1/" + n).toOption.get
  val names = ('A' to 'J').map(_.toString).toVector
  val papers = Vector(
    ("w1", 2015, Vector("A", "B", "C")),
    ("w2", 2016, Vector("A", "B")),
    ("w9", 2016, Vector("A", "A", "B")),
    ("w3", 2017, Vector("C", "D")),
    ("w4", 2018, Vector("D", "E", "F")),
    ("w5", 2019, Vector("E", "F")),
    ("w6", 2020, Vector("F", "G")),
    ("w7", 2020, Vector("H", "I")),
    ("w8", 2021, Vector("J"))
  )
  def component(n: String): String =
    "component:" + StableIds.sha256Hex(if (Set("H", "I")(n)) "hi" else if (n == "J") "j" else "ag")
  def community(n: String): String = "community:" + StableIds.sha256Hex(
    if (Set("A", "B", "C")(n)) "abc"
    else if (Set("D", "E", "F", "G")(n)) "defg"
    else if (Set("H", "I")(n)) "hi"
    else "j"
  )
  // P, C, T, A, M, maximizing work, coreness. These values are literal, never graph recomputation.
  val expected = Vector(
    ("A", 3L, 2L, 4L, 4.0 / 3, 2L, "w1", 2),
    ("B", 3L, 2L, 4L, 4.0 / 3, 2L, "w1", 2),
    ("C", 2L, 3L, 3L, 1.5, 2L, "w1", 2),
    ("D", 2L, 3L, 3L, 1.5, 2L, "w4", 2),
    ("E", 2L, 2L, 3L, 1.5, 2L, "w4", 2),
    ("F", 3L, 3L, 4L, 4.0 / 3, 2L, "w4", 2),
    ("G", 1L, 1L, 1L, 1.0, 1L, "w6", 1),
    ("H", 1L, 1L, 1L, 1.0, 1L, "w7", 1),
    ("I", 1L, 1L, 1L, 1.0, 1L, "w7", 1),
    ("J", 1L, 0L, 0L, 0.0, 0L, "w8", 0)
  )
  val details = expected.map { (n, p, c, t, a, m, w, k) =>
    ResearcherMetricsDetail(
      context,
      id(n),
      policy,
      p,
      c,
      t,
      a,
      m,
      Vector(work(w)),
      1,
      t,
      component(n),
      Some(community(n)),
      Some(k)
    )
  }
  val memberships = names.map(n => CommunityMembership(context, id(n), community(n), 3, false))
  val bridges = names.map(n =>
    ResearcherBridgeMetrics(
      context,
      id(n),
      policy,
      if (Set("C", "D")(n)) 1 else 0,
      if (Set("C", "D")(n)) 1 else 0,
      if (Set("C", "D")(n)) 1 else 0,
      if (Set("C", "D")(n)) 4.0 / 9 else 0.0
    )
  )
  val summaries = Vector("A" -> 3L, "D" -> 4L, "H" -> 2L, "J" -> 1L).map((n, s) =>
    CommunitySummary(context, community(n), s, 3, 1, false)
  )
  val edgesLiteral = Vector(
    ("A", "B", 3L, Vector("w1", "w2", "w9")),
    ("A", "C", 1L, Vector("w1")),
    ("B", "C", 1L, Vector("w1")),
    ("C", "D", 1L, Vector("w3")),
    ("D", "E", 1L, Vector("w4")),
    ("D", "F", 1L, Vector("w4")),
    ("E", "F", 2L, Vector("w4", "w5")),
    ("F", "G", 1L, Vector("w6")),
    ("H", "I", 1L, Vector("w7"))
  )
  val edges = edgesLiteral.map { (a, b, count, ws) =>
    val ordered = Vector(id(a), id(b)).sorted
    val years = ws.map(w => papers.find(_._1 == w).get._2)
    SparkCoauthorEdge(
      context,
      StableIds
        .sparkCoauthorEdgeId(
          ordered.head,
          ordered.last,
          SparkWindow("all-years", None, None, None),
          policy
        )
        .toOption
        .get,
      ordered.head,
      ordered.last,
      policy,
      count,
      Some(years.min),
      Some(years.max),
      ws.map(work),
      None,
      None
    )
  }
  val supports = edgesLiteral.zip(edges).flatMap { (literal, e) =>
    literal._4.map(w =>
      CoauthorEdgeSupport(context, e.edgeId, work(w), Some(papers.find(_._1 == w).get._2))
    )
  }
  def row[A: upickle.default.Writer](a: A): ujson.Obj =
    ujson.Obj.from(upickle.default.writeJs(a).obj)
  val topic = StableIds.topicIdFromOpenAlex("T900001").toOption.get
  val otherTopic = StableIds.topicIdFromOpenAlex("T900002").toOption.get
  val institution = StableIds.institutionIdFromOpenAlex("I900001").toOption.get
  val otherInstitution = StableIds.institutionIdFromOpenAlex("I900002").toOption.get
  val venue = StableIds.venueIdFromDblpBooktitle("Synthetic Runtime Venue").toOption.get
  val otherVenue = StableIds.venueIdFromDblpBooktitle("Synthetic Other Venue").toOption.get
  private def association(a: String, kind: GraphEdgeType, b: String, w: String): GraphEdge = {
    val source = GraphSourceEvidence.Work(w)
    GraphEdge(
      StableIds.graphEdgeId(kind, a, b, policy, source).toOption.get,
      SchemaVersions.domain,
      a,
      kind,
      b,
      policy,
      source,
      Vector.empty,
      None,
      provenance
    )
  }
  private val overlay = names.map { n =>
    val w = work("overlay-" + n); val selected = Set("A", "B")(n)
    Vector(
      association(id(n), GraphEdgeType.Authored, w, w),
      association(
        id(n),
        GraphEdgeType.AffiliatedWith,
        if (selected) institution else otherInstitution,
        w
      ),
      association(w, GraphEdgeType.HasTopic, if (selected) topic else otherTopic, w),
      association(w, GraphEdgeType.PublishedIn, if (selected) venue else otherVenue, w)
    )
  }.flatten
  private val temporal = TemporalChange(
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
  def artifacts(): RuntimeArtifactStore =
    new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeArtifactStore(
      context.copy(windowId = None),
      Map(
        "nodes/type=researcher" -> names.map(n =>
          row(
            GraphNode(
              id(n),
              SchemaVersions.domain,
              GraphNodeClass.Researcher,
              n,
              Vector.empty,
              provenance
            )
          )
        ),
        "metrics/type=researcher_collaboration" -> details.map(row(_)),
        "metrics/type=communities" -> (memberships ++ Vector("2015-2017", "2018-2021").map(w =>
          CommunityMembership(context.copy(windowId = Some(w)), id("D"), community("D"), 3, false)
        )).map(row(_)),
        "metrics/type=community_summaries" -> summaries.map(row(_)),
        "metrics/type=bridges" -> bridges.map(row(_)),
        "metrics/type=temporal_changes" -> Vector(row(temporal)),
        "edges/type=coauthored_with" -> edges.map(row(_)),
        "edges/type=coauthored_with_support" -> supports.map(row(_))
      ) ++
        Vector(
          GraphEdgeType.Authored,
          GraphEdgeType.AffiliatedWith,
          GraphEdgeType.HasTopic,
          GraphEdgeType.PublishedIn
        ).map(kind =>
          ("edges/type=" + kind.wire
            .toLowerCase(java.util.Locale.ROOT)) -> overlay.filter(_.edgeType == kind).map(row(_))
        ).toMap,
      config.windowIds
    )
  def metricStore(): InMemoryResearcherMetricStore = {
    val store = new InMemoryResearcherMetricStore
    details.foreach(m =>
      store.put(
        ResearcherMetricRecord(
          m.researcherId,
          "all-years",
          policy,
          run,
          CoreJson.compact(m),
          ujson
            .Obj(
              "communityMembership" -> upickle.default
                .writeJs(memberships.find(_.researcherId == m.researcherId).get)
            )
            .render()
        )
      )
    )
    store
  }
  def graph(): GraphReader = new InMemoryGraphReader(
    edges = edges.map(e =>
      FakeGraphEdge(e.researcherA, e.researcherB, e.edgeId, "COAUTHORED_WITH", "all-years")
    ),
    communities = names.groupBy(community).map((c, ns) => (c -> "all-years") -> ns.map(id))
  )
  def candidates(ns: String*): Vector[ResearcherCandidate] = ns.toVector.map(n =>
    ResearcherCandidate(
      id(n),
      n,
      Vector("synthetic:" + n),
      Vector.empty,
      None,
      Vector.empty,
      Vector("g1:" + n),
      Vector(run)
    )
  )
  def plan(op: QueryOperation, ns: String*): QueryPlan = QueryPlan(
    "plan:" + "a" * 64,
    SchemaVersions.domain,
    "Synthetic G1 question",
    Vector(op),
    YearWindow(1000, 9999),
    Vector.empty,
    Vector.empty,
    Vector.empty,
    Some(CollaborationMetric.DistinctCoauthorCount),
    25,
    10,
    6,
    provenance,
    Some(
      RuntimeQueryOptions(
        researcherNames = ns.toVector,
        windowIds = Vector("all-years"),
        retrievalMode = RetrievalMode.Graph,
        evidenceOnly = true
      )
    )
  )
  def input(op: QueryOperation, ns: String*): RetrievalInput =
    RetrievalInput(plan(op, ns*), candidates(ns*))
  // Identity and metadata overlays do not modify G1 graph/metric rows.
  val metadataOverlay = Map(
    "A" -> ("Synthetic Systems", "Synthetic UIC", "Synthetic Venue"),
    "B" -> ("Synthetic Systems", "Synthetic UIC", "Synthetic Venue")
  )
  def cache(): EntityLinkCache = {
    val cache = new InMemoryEntityLinkCache
    (names ++ Vector("Name 0001", "Name 0002")).foreach { n =>
      val link = EntityLink(
        "name",
        TextNorm.personName(n),
        policy,
        "synthetic:" + n,
        id(n),
        n,
        Vector.empty,
        None,
        run,
        Vector("g1:" + n)
      )
      cache.putLink(link)
      if (n.startsWith("Name "))
        cache.putLink(link.copy(normalizedKey = TextNorm.personName("Name")))
    }; cache
  }
}
