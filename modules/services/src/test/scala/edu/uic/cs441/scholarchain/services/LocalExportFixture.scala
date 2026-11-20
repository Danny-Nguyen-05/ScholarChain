package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import upickle.default.writeJs

/** A hand-derivable synthetic Phase 6 export for the local stack tests: one hub researcher (Ada
  * Alpha) with `coauthors` direct coauthors, each pair having `worksPerEdge` joint works in
  * all-years (years cycle 2010..2019). Researcher i has the stable ID `researcher:dblp:` plus the
  * 64-digit hex of i, so the hub (0) sorts first and every edge is (hub, i). Everything is derived
  * from the parameters, not from the loader.
  */
final class LocalExportFixture(val coauthors: Int, val worksPerEdge: Int) {
  require(coauthors >= 1 && coauthors <= 90 && worksPerEdge >= 1)
  val runId = "run:00112233-4455-4677-8899-aabbccddeeff"
  val windows: Vector[String] = Vector("all-years", "2010-2014", "2015-2019", "2020-2026")
  def id(i: Int): String = "researcher:dblp:" + f"$i%064x"
  val hub: String = id(0)
  val hubName = "Ada Alpha"
  def coauthorName(i: Int): String =
    "Collab " + ('A' + (i - 1) / 26).toChar + ('a' + (i - 1) % 26).toChar
  def name(i: Int): String = if (i == 0) hubName else coauthorName(i)
  def work(i: Int, j: Int): String = f"work:dblp:synthetic/e$i%02dw$j%02d"
  val absentResearcher: String = "researcher:dblp:" + "9" * 64
  val people: Vector[Int] = (0 to coauthors).toVector

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
  private val cw = context.copy(windowId = Some("all-years"))
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
  private def obj[A: upickle.default.Writer](v: A): ujson.Obj = ujson.Obj.from(writeJs(v).obj)
  private def community(i: Int): String = "community:" + StableIds.sha256Hex(id(i))
  private def degree(i: Int): Long = if (i == 0) coauthors.toLong else 1L

  private val edges: Vector[SparkCoauthorEdge] = (1 to coauthors).toVector.map { i =>
    val edgeId = StableIds
      .sparkCoauthorEdgeId(
        hub,
        id(i),
        SparkWindow("all-years", None, None, None),
        "synthetic-graph"
      )
      .toOption
      .get
    SparkCoauthorEdge(
      cw,
      edgeId,
      hub,
      id(i),
      "synthetic-graph",
      worksPerEdge.toLong,
      Some(2010),
      Some(2019),
      (1 to math.min(3, worksPerEdge)).toVector.map(work(i, _)),
      None,
      None
    )
  }
  private val supports: Vector[CoauthorEdgeSupport] = edges.zipWithIndex.flatMap { (e, k) =>
    (1 to worksPerEdge).toVector
      .map(j => CoauthorEdgeSupport(cw, e.edgeId, work(k + 1, j), Some(2010 + (j % 10))))
  }
  val edgeIds: Vector[String] = edges.map(_.edgeId)

  val source: Map[String, Vector[ujson.Obj]] = Map(
    "nodes/type=researcher" -> people.map { i =>
      obj(
        GraphNode(
          id(i),
          SchemaVersions.domain,
          GraphNodeClass.Researcher,
          name(i),
          Vector.empty,
          provenance
        )
      )
    },
    "metrics/type=researcher_collaboration" -> people.map { i =>
      val dg = degree(i)
      obj(
        ResearcherMetricsDetail(
          cw,
          id(i),
          "synthetic-metrics",
          dg,
          dg,
          dg,
          1.0,
          1,
          Vector(work(math.max(i, 1), 1)),
          dg,
          dg,
          "component:" + "f" * 64,
          Some(community(i)),
          Some(1)
        )
      )
    },
    "metrics/type=communities" ->
      people.map(i => obj(CommunityMembership(cw, id(i), community(i), 20, false))),
    "metrics/type=community_summaries" ->
      people.map(i => obj(CommunitySummary(cw, community(i), 1, 20, 1, false))),
    "metrics/type=bridges" -> people.map { i =>
      obj(
        ResearcherBridgeMetrics(
          cw,
          id(i),
          "synthetic-bridges",
          degree(i),
          degree(i),
          degree(i),
          0.0
        )
      )
    },
    "metrics/type=temporal_changes" -> Vector.empty[ujson.Obj],
    "edges/type=coauthored_with" -> edges.map(obj(_)),
    "edges/type=coauthored_with_support" -> supports.map(obj(_))
  )

  private def keys(name: String): Vector[String] = name match {
    case "metrics/type=community_summaries" => Vector("communityId")
    case "metrics/type=temporal_changes"    => Vector("researcherId", "fromWindowId", "toWindowId")
    case "edges/type=coauthored_with_support" => Vector("edgeId", "workId")
    case n if n.startsWith("nodes/")          => Vector("nodeId")
    case n if n.startsWith("edges/")          => Vector("edgeId")
    case _                                    => Vector("researcherId")
  }

  val manifests: Vector[LoadManifest] = source.toVector.sortBy(_._1).map { (name, values) =>
    LoadManifest(
      context,
      "s3",
      name,
      Vector(name),
      "parquet",
      values.size.toLong,
      keys(name),
      Vector("run_id"),
      FixtureTableHash.of(values),
      windows,
      "service-engineer",
      Vector.empty
    )
  }

  private final class Reader extends ManifestRowReader {
    def qualifications(run: String): StorageResult[String] = StorageResult.Found(
      ujson
        .Obj("runManifest" -> ujson.Obj("runId" -> run), "runMetadata" -> ujson.Obj("runId" -> run))
        .render()
    )
    def open(m: LoadManifest): StorageResult[CloseableRowIterator] = {
      val it = source(m.logicalDataset).iterator
      StorageResult.Found(new CloseableRowIterator {
        def hasNext: Boolean = it.hasNext
        def next(): ujson.Obj = ujson.Obj.from(ujson.read(it.next().render()).obj)
        def close(): Unit = ()
      })
    }
  }

  /** The export loaded with every table hash verified. */
  def stores(scope: RuntimeArtifactScope = RuntimeArtifactScope.WholeExport): LocalExportStores =
    LocalExportStores
      .load(manifests, new Reader, LocalExportOptions(artifactScope = scope))
      .fold(e => throw new AssertionError("fixture refused: " + e), identity)
}
