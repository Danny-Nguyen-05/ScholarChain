package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeArtifactStore

/** One hub researcher with `coauthors` direct coauthors, built with the identifier shapes of the
  * real runtime (64-hex researcher and edge IDs, DBLP work keys, production-sized candidate
  * provenance). Coauthor i shares `1 + i % 4` works with the hub; the work years run 2010..2025, so
  * the 2015-2019 window holds a strict subset of the all-years rows. A second layer links coauthor
  * `i` to coauthor `i + 1` so two-hop paths exist. Everything is synthetic and offline.
  */
private[rag] final class CoauthorScaleFixture(
    val coauthors: Int,
    hubJoint: Int => Int = i => 1 + (i + 1) % 4,
    /** When set, the stored metric of the hub reports this distinct-coauthor count instead of the
      * number of its edge rows: the graph and the metrics then disagree.
      */
    hubMetricDistinct: Option[Int] = None
) {
  val run = "run:66666666-6666-4666-8666-666666666666"
  private val upstream = "run:33333333-3333-4333-8333-333333333333"
  private val er = "run:44444444-4444-4444-8444-444444444444"
  val policy = "module-scale-v1"
  val windows: Vector[(String, Option[Int], Option[Int])] =
    Vector(("all-years", None, None), ("2015-2019", Some(2015), Some(2019)))
  val provenance: Provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-scale",
    None,
    "synthetic-scale",
    Some("2026-11-20"),
    None,
    run,
    Vector("Synthetic coauthor-scale fixture.")
  )
  def context(window: String): SparkRecordContext = SparkRecordContext(
    SchemaVersions.sparkAnalytics,
    run,
    Some(window),
    SparkLineage(upstream, "synthetic-scale", er, policy, "a" * 64, Vector.empty, Vector.empty)
  )
  val config: RuntimeConfig = Runtime9BG1Fixture.config

  val hubName = "Hub Researcher"
  def coauthorName(i: Int): String = s"Coauthor Number $i"
  def id(name: String): String = StableIds.researcherIdFromDblpName(policy, name).toOption.get
  val hub: String = id(hubName)
  val coauthorIds: Vector[String] = (1 to coauthors).toVector.map(i => id(coauthorName(i)))

  private final case class Pair(a: String, b: String, works: Vector[(String, Int)])
  private def works(tag: String, count: Int, salt: Int): Vector[(String, Int)] =
    (0 until count).toVector.map { k =>
      (
        StableIds.workIdFromDblpKey(s"conf/scale/Author${tag}Venue${salt}K$k").toOption.get,
        2010 + (salt + 3 * k) % 16
      )
    }
  private val pairs: Vector[Pair] =
    coauthorIds.zipWithIndex.map { (c, i) =>
      Pair(hub, c, works("Hub", hubJoint(i), i + 1))
    } ++ coauthorIds.zip(coauthorIds.drop(1)).zipWithIndex.map { case ((a, b), i) =>
      Pair(a, b, works("Chain", 1 + i % 2, i + 7))
    }
  private def inWindow(year: Int, start: Option[Int], end: Option[Int]) =
    start.forall(year >= _) && end.forall(year <= _)

  private final case class Row(
      window: String,
      edge: SparkCoauthorEdge,
      support: Vector[CoauthorEdgeSupport]
  )
  private val rows: Vector[Row] = for {
    (window, start, end) <- windows
    p <- pairs
    inside = p.works.filter(w => inWindow(w._2, start, end))
    if inside.nonEmpty
  } yield {
    val ordered = Vector(p.a, p.b).sorted
    val edgeId = StableIds
      .sparkCoauthorEdgeId(
        ordered.head,
        ordered.last,
        SparkWindow(window, start, end, None),
        policy
      )
      .toOption
      .get
    val ctx = context(window)
    Row(
      window,
      SparkCoauthorEdge(
        ctx,
        edgeId,
        ordered.head,
        ordered.last,
        policy,
        inside.size.toLong,
        Some(inside.map(_._2).min),
        Some(inside.map(_._2).max),
        inside.map(_._1),
        start,
        end
      ),
      inside.map(w => CoauthorEdgeSupport(ctx, edgeId, w._1, Some(w._2)))
    )
  }

  def degree(who: String, window: String): Int =
    rows.count(r => r.window == window && Set(r.edge.researcherA, r.edge.researcherB)(who))

  private def detail(who: String, window: String): ResearcherMetricsDetail = {
    val mine =
      rows.filter(r => r.window == window && Set(r.edge.researcherA, r.edge.researcherB)(who))
    val total = mine.map(_.edge.jointPublicationCount).sum
    ResearcherMetricsDetail(
      context(window),
      who,
      policy,
      total,
      (if (who == hub) hubMetricDistinct else None).getOrElse(mine.size).toLong,
      total,
      1.0,
      1L,
      Vector(mine.head.support.head.workId),
      1L,
      total,
      "component:" + StableIds.sha256Hex("scale"),
      None,
      Some(1)
    )
  }
  private def row[A: upickle.default.Writer](a: A): ujson.Obj =
    ujson.Obj.from(upickle.default.writeJs(a).obj)
  def artifacts(): RuntimeArtifactStore =
    new InMemoryRuntimeArtifactStore(
      context("all-years").copy(windowId = None),
      Map(
        "nodes/type=researcher" -> (hub +: coauthorIds).map(x =>
          row(
            GraphNode(
              x,
              SchemaVersions.domain,
              GraphNodeClass.Researcher,
              x,
              Vector.empty,
              provenance
            )
          )
        ),
        "metrics/type=researcher_collaboration" -> (for {
          (w, _, _) <- windows
          who <- hub +: coauthorIds
          if degree(who, w) > 0
        } yield row(detail(who, w))),
        "metrics/type=communities" -> Vector.empty[ujson.Obj],
        "metrics/type=community_summaries" -> Vector.empty[ujson.Obj],
        "metrics/type=bridges" -> Vector.empty[ujson.Obj],
        "metrics/type=temporal_changes" -> Vector.empty[ujson.Obj],
        "edges/type=coauthored_with" -> rows.map(r => row(r.edge)),
        "edges/type=coauthored_with_support" -> rows.flatMap(_.support.map(row(_)))
      ),
      windows.map(_._1)
    )
  def metricStore(): InMemoryResearcherMetricStore = {
    val store = new InMemoryResearcherMetricStore
    for ((w, _, _) <- windows; who <- hub +: coauthorIds if degree(who, w) > 0) {
      val m = detail(who, w)
      store.put(
        ResearcherMetricRecord(who, w, policy, run, CoreJson.compact(m), ujson.Obj().render())
      )
    }
    store
  }
  def graph(): GraphReader = new InMemoryGraphReader(
    edges = rows.map(r =>
      FakeGraphEdge(
        r.edge.researcherA,
        r.edge.researcherB,
        r.edge.edgeId,
        "COAUTHORED_WITH",
        r.window
      )
    )
  )

  /** Production-sized resolved identity: 5 source IDs and 23 evidence references (the Session 1 16B
    * path candidates had 5 source IDs and 16 to 23 references).
    */
  def candidate(who: String, name: String): ResearcherCandidate = ResearcherCandidate(
    who,
    name,
    (1 to 5).toVector.map(k =>
      s"mention:dblp:conf/scale/${name.replace(' ', '_')}ConferencePaper$k#$k"
    ),
    Vector.empty,
    None,
    Vector.empty,
    Vector("edges/type=resolves_to", "nodes/type=researcher") ++
      (1 to 21).toVector.map(k => "graph-edge:" + StableIds.sha256Hex(s"$who|$k")),
    Vector(run)
  )

  /** A candidate at the resolver bound (16 source IDs) whose stored provenance was truncated: the
    * summary reports more IDs and references than the retained lists.
    */
  def truncatedCandidate(who: String, name: String): ResearcherCandidate =
    candidate(who, name).copy(
      sourceIds = (1 to 16).toVector.map(k => s"mention:dblp:conf/scale/Truncated$k#$k"),
      provenanceSummary = Some(ResearcherCandidateProvenanceSummary(40, 60, 0, 1, true))
    )
  def candidates(names: String*): Vector[ResearcherCandidate] =
    names.toVector.map(n => candidate(id(n), n))

  def plan(
      op: QueryOperation,
      window: String,
      graphLimit: Int,
      names: String*
  ): QueryPlan = QueryPlan(
    "plan:" + "b" * 64,
    SchemaVersions.domain,
    "Synthetic scale question",
    Vector(op),
    YearWindow(1000, 9999),
    Vector.empty,
    Vector.empty,
    Vector.empty,
    Some(CollaborationMetric.DistinctCoauthorCount),
    graphLimit,
    10,
    6,
    provenance,
    Some(
      RuntimeQueryOptions(
        researcherNames = names.toVector,
        windowIds = Vector(window),
        retrievalMode = RetrievalMode.Graph,
        evidenceOnly = false
      )
    )
  )
}
