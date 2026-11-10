package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import upickle.default.writeJs
import StorageResult.*

/** Hand-derivable synthetic export used by the bounded runtime-artifact tests.
  *
  * Researchers a..f; coauthor edges a-b, a-c, a-d, b-c, e-f (one joint work each, all-years).
  * Degrees: a=3, b=2, c=2, d=1, e=1, f=1 (ties b<c and d<e<f by stable ID). Authors: a:
  * w_ab,w_ac,w_ad; b: w_ab,w_bc; c: w_ac,w_bc; d: w_ad; e: w_ef; f: w_ef. Associations: w_ab has
  * topic T1 and venue V; w_ef has topic T2; a is affiliated with I1 and e with I2. Closure sizes
  * derived by hand (rows per entity, counting each row once): a=24, b=17, c=13, d=9, e=13, f=11;
  * whole source=61 rows.
  */
private[storage] object SubsetFixture {
  val runId = "run:00112233-4455-4677-8899-aabbccddeeff"
  val ids: Map[Char, String] = "abcdef".map(c => c -> ("researcher:dblp:" + c.toString * 64)).toMap
  val a: String = ids('a')
  val b: String = ids('b')
  val c: String = ids('c')
  val d: String = ids('d')
  val e: String = ids('e')
  val f: String = ids('f')
  val people: Vector[String] = Vector(a, b, c, d, e, f)
  val wab = "work:dblp:synthetic/ab"
  val wac = "work:dblp:synthetic/ac"
  val wad = "work:dblp:synthetic/ad"
  val wbc = "work:dblp:synthetic/bc"
  val wef = "work:dblp:synthetic/ef"
  val topic1 = "topic:openalex:T1"
  val topic2 = "topic:openalex:T2"
  val venue = "venue:dblp-booktitle:synthetic"
  val institution1 = "institution:openalex:I1"
  val institution2 = "institution:openalex:I2"
  val windows: Vector[String] = Vector("all-years", "2010-2014", "2015-2019", "empty-window")
  val unknownResearcher: String = "researcher:dblp:" + "9" * 64
  val closureRows: Map[String, Int] = Map(a -> 24, b -> 17, c -> 13, d -> 9, e -> 13, f -> 11)
  val sourceRowTotal = 61

  private val lineage =
    SparkLineage(
      runId,
      "synthetic-snapshot",
      runId,
      "synthetic-er",
      "e" * 64,
      Vector.empty,
      Vector.empty
    )
  private val context = SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage)
  val cw: SparkRecordContext = context.copy(windowId = Some("all-years"))
  val sourceContext: SparkRecordContext = context
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-source",
    None,
    "synthetic-snapshot",
    None,
    None,
    runId,
    Vector("Synthetic fixture only")
  )

  private def obj[A: upickle.default.Writer](v: A): ujson.Obj =
    ujson.Obj.from(writeJs(v).obj)
  private def node(id: String, kind: GraphNodeClass): GraphNode =
    GraphNode(
      id,
      SchemaVersions.domain,
      kind,
      "Synthetic " + id.takeRight(4),
      Vector.empty,
      provenance
    )
  private def graphEdge(from: String, to: String, kind: GraphEdgeType): GraphEdge = {
    val supportingWork = kind match {
      case GraphEdgeType.Authored                             => to
      case GraphEdgeType.HasTopic | GraphEdgeType.PublishedIn => from
      case _                                                  => wab
    }
    val evidence = GraphSourceEvidence.Work(supportingWork)
    GraphEdge(
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
  }
  private def community(id: String): String = "community:" + StableIds.sha256Hex(id)

  private val degree: Map[String, Long] = Map(a -> 3L, b -> 2L, c -> 2L, d -> 1L, e -> 1L, f -> 1L)
  private val coauthored = Vector((a, b, wab), (a, c, wac), (a, d, wad), (b, c, wbc), (e, f, wef))
  private val edges = coauthored.map { (x, y, work) =>
    val id = StableIds
      .sparkCoauthorEdgeId(x, y, SparkWindow("all-years", None, None, None), "synthetic-graph")
      .toOption
      .get
    SparkCoauthorEdge(
      cw,
      id,
      x,
      y,
      "synthetic-graph",
      1,
      Some(2015),
      Some(2015),
      Vector(work),
      None,
      None
    )
  }
  private val supports =
    edges.map(e => CoauthorEdgeSupport(cw, e.edgeId, e.representativeWorkIds.head, Some(2015)))
  private val authored = Vector(
    a -> wab,
    a -> wac,
    a -> wad,
    b -> wab,
    b -> wbc,
    c -> wac,
    c -> wbc,
    d -> wad,
    e -> wef,
    f -> wef
  )
  private val temporal = TemporalChange(
    cw.copy(windowId = Some("2015-2019")),
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
    Some(community(a)),
    None,
    None,
    None,
    None,
    None
  )

  val source: Map[String, Vector[ujson.Obj]] = Map(
    "nodes/type=researcher" -> people.map(id => obj(node(id, GraphNodeClass.Researcher))),
    "nodes/type=topic" -> Vector(topic1, topic2).map(id => obj(node(id, GraphNodeClass.Topic))),
    "nodes/type=venue" -> Vector(obj(node(venue, GraphNodeClass.Venue))),
    "nodes/type=institution" ->
      Vector(institution1, institution2).map(id => obj(node(id, GraphNodeClass.Institution))),
    "metrics/type=researcher_collaboration" -> people.map { id =>
      val dg = degree(id)
      obj(
        ResearcherMetricsDetail(
          cw,
          id,
          "synthetic-metrics",
          dg,
          dg,
          dg,
          1.0,
          1,
          Vector(wab),
          dg,
          dg,
          "component:" + "f" * 64,
          Some(community(id)),
          Some(1)
        )
      )
    },
    "metrics/type=communities" ->
      people.map(id => obj(CommunityMembership(cw, id, community(id), 20, false))),
    "metrics/type=community_summaries" ->
      people.map(id => obj(CommunitySummary(cw, community(id), 1, 20, 1, false))),
    "metrics/type=bridges" -> people.map { id =>
      obj(
        ResearcherBridgeMetrics(
          cw,
          id,
          "synthetic-bridges",
          degree(id),
          degree(id),
          degree(id),
          0.0
        )
      )
    },
    "metrics/type=temporal_changes" -> Vector(obj(temporal)),
    "edges/type=coauthored_with" -> edges.map(obj(_)),
    "edges/type=coauthored_with_support" -> supports.map(obj(_)),
    "edges/type=authored" -> authored.map((r, w) => obj(graphEdge(r, w, GraphEdgeType.Authored))),
    "edges/type=has_topic" -> Vector(
      obj(graphEdge(wab, topic1, GraphEdgeType.HasTopic)),
      obj(graphEdge(wef, topic2, GraphEdgeType.HasTopic))
    ),
    "edges/type=published_in" -> Vector(obj(graphEdge(wab, venue, GraphEdgeType.PublishedIn))),
    "edges/type=affiliated_with" -> Vector(
      obj(graphEdge(a, institution1, GraphEdgeType.AffiliatedWith)),
      obj(graphEdge(e, institution2, GraphEdgeType.AffiliatedWith))
    )
  )

  /** A path graph of `n` researchers (0 - 1 - ... - n-1), one joint work per edge and one authored
    * work per researcher. Row count is 8n - 2; the ends have degree 1 and everyone else degree 2.
    */
  def pathId(i: Int): String = "researcher:dblp:" + f"$i%064x"
  def pathSource(n: Int): Map[String, Vector[ujson.Obj]] = {
    val ids = (0 until n).map(pathId).toVector
    def deg(i: Int): Long = if (i == 0 || i == n - 1) 1L else 2L
    val pathEdges = (0 until n - 1).toVector.map { i =>
      val edgeId = StableIds
        .sparkCoauthorEdgeId(
          ids(i),
          ids(i + 1),
          SparkWindow("all-years", None, None, None),
          "synthetic-graph"
        )
        .toOption
        .get
      SparkCoauthorEdge(
        cw,
        edgeId,
        ids(i),
        ids(i + 1),
        "synthetic-graph",
        1,
        Some(2015),
        Some(2015),
        Vector(s"work:dblp:synthetic/p$i"),
        None,
        None
      )
    }
    Map(
      "nodes/type=researcher" -> ids.map(id => obj(node(id, GraphNodeClass.Researcher))),
      "nodes/type=topic" -> Vector.empty[ujson.Obj],
      "metrics/type=researcher_collaboration" -> ids.zipWithIndex.map { (id, i) =>
        obj(
          ResearcherMetricsDetail(
            cw,
            id,
            "synthetic-metrics",
            deg(i),
            deg(i),
            deg(i),
            1.0,
            1,
            Vector(s"work:dblp:synthetic/p$i"),
            deg(i),
            deg(i),
            "component:" + "f" * 64,
            Some(community(id)),
            Some(1)
          )
        )
      },
      "metrics/type=communities" ->
        ids.map(id => obj(CommunityMembership(cw, id, community(id), 20, false))),
      "metrics/type=community_summaries" ->
        ids.map(id => obj(CommunitySummary(cw, community(id), 1, 20, 1, false))),
      "metrics/type=bridges" -> ids.zipWithIndex.map { (id, i) =>
        obj(ResearcherBridgeMetrics(cw, id, "synthetic-bridges", deg(i), deg(i), deg(i), 0.0))
      },
      "metrics/type=temporal_changes" -> Vector.empty[ujson.Obj],
      "edges/type=coauthored_with" -> pathEdges.map(obj(_)),
      "edges/type=coauthored_with_support" ->
        pathEdges.map(e =>
          obj(CoauthorEdgeSupport(cw, e.edgeId, e.representativeWorkIds.head, Some(2015)))
        ),
      "edges/type=authored" -> ids.zipWithIndex.map { (id, i) =>
        obj(graphEdge(id, s"work:dblp:synthetic/p$i", GraphEdgeType.Authored))
      }
    )
  }

  def keys(name: String): Vector[String] = name match {
    case "metrics/type=community_summaries" => Vector("communityId")
    case "metrics/type=temporal_changes"    => Vector("researcherId", "fromWindowId", "toWindowId")
    case "edges/type=coauthored_with_support" => Vector("edgeId", "workId")
    case n if n.startsWith("nodes/")          => Vector("nodeId")
    case n if n.startsWith("edges/")          => Vector("edgeId")
    case _                                    => Vector("researcherId")
  }

  def manifests(rows: Map[String, Vector[ujson.Obj]] = source): Vector[LoadManifest] =
    rows.toVector.sortBy(_._1).map { (name, values) =>
      LoadManifest(
        context,
        "s3",
        name,
        Vector(name),
        "parquet",
        values.size.toLong,
        keys(name),
        Vector("run_id"),
        Phase6RuntimeArtifacts.tableHash(values),
        windows,
        "storage-engineer",
        Vector.empty
      )
    }

  /** Serves rows in the given order. `rows` may differ from the manifested rows to simulate
    * tampering; the manifest hash is what the build must verify.
    */
  final class Reader(rows: Map[String, Vector[ujson.Obj]], reverse: Boolean = false)
      extends ManifestRowReader {
    def qualifications(id: String): StorageResult[String] = Found(
      ujson
        .Obj("runManifest" -> ujson.Obj("runId" -> id), "runMetadata" -> ujson.Obj("runId" -> id))
        .render()
    )
    def open(m: LoadManifest): StorageResult[CloseableRowIterator] = {
      val values = rows(m.logicalDataset)
      val it = (if (reverse) values.reverse else values).iterator
      Found(new CloseableRowIterator {
        def hasNext: Boolean = it.hasNext
        def next(): ujson.Obj = ujson.read(it.next().render()).obj match {
          case fields => ujson.Obj.from(fields)
        }
        def close(): Unit = ()
      })
    }
  }
}
