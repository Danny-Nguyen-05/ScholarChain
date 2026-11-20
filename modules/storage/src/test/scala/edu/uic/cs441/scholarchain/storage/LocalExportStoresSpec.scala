package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write
import StorageResult.*

/** The local export loader on the hand-derivable synthetic export of `SubsetFixture`: researchers
  * a..f, five coauthor edges in all-years (a-b, a-c, a-d, b-c, e-f), ten authored edges to five
  * works. Expected values below are derived from that description, not from the loader.
  */
class LocalExportStoresSpec extends AnyFunSuite {
  import SubsetFixture.*

  private def community(id: String) = "community:" + StableIds.sha256Hex(id)
  private val works = Vector(wab, wac, wad, wbc, wef)

  /** The fixture plus the work nodes its authored edges point at. */
  private def withWorks(rows: Map[String, Vector[ujson.Obj]]): Map[String, Vector[ujson.Obj]] = {
    val template = rows("nodes/type=researcher").head
    rows + ("nodes/type=work" -> works.map { id =>
      val row = ujson.read(template.render()).obj
      row("nodeId") = id
      row("nodeClass") = "WORK"
      row("label") = "Synthetic work " + id.takeRight(2)
      ujson.Obj.from(row)
    })
  }
  private val rows = withWorks(source)
  private def load(
      data: Map[String, Vector[ujson.Obj]] = rows,
      served: Map[String, Vector[ujson.Obj]] = null,
      options: LocalExportOptions = LocalExportOptions()
  ) = LocalExportStores.load(manifests(data), new Reader(Option(served).getOrElse(data)), options)
  private def stores(options: LocalExportOptions = LocalExportOptions()) =
    load(options = options).fold(e => fail(e.toString), identity)

  test("counts, provenance and stores come from the manifest-verified source rows") {
    val s = stores()
    assert(
      s.counts.nodesByClass == Map(
        "RESEARCHER" -> 6L,
        "WORK" -> 5L,
        "TOPIC" -> 2L,
        "VENUE" -> 1L,
        "INSTITUTION" -> 2L
      )
    )
    assert(
      s.counts.edgesByType == Map(
        "COAUTHORED_WITH" -> 5L,
        "AUTHORED" -> 10L,
        "HAS_TOPIC" -> 2L,
        "PUBLISHED_IN" -> 1L,
        "AFFILIATED_WITH" -> 2L
      )
    )
    assert(s.counts.coauthorEdgesByWindow == Map("all-years" -> 5L))
    assert(s.counts.coauthorSupportRows == 5L && s.counts.metricRows == 6L)
    assert(s.counts.communityMembershipRows == 6L && s.counts.temporalChangeRows == 1L)
    assert(s.counts.cacheRejected == 0L)
    assert(s.runId == runId && s.provenance.artifactScope == "whole-export")
    assert(s.provenance.tables.forall(_.hashVerified))
    assert(s.provenance.tables.map(_.dataset).contains("edges/type=coauthored_with_support"))
    assert(
      s.artifactPointer.sourceRunId == runId && s.artifactPointer.sha256.matches("[0-9a-f]{64}")
    )
    // The pointer is a function of the source table hashes alone.
    assert(stores().artifactPointer == s.artifactPointer)
  }

  test("graph reader returns stored endpoints, window rule and Neptune ordering") {
    val g = stores().graphReader
    assert(StorageResult.value(g.node(a)).map(_.nodeId) == Some(a))
    assert(g.node(unknownResearcher) == Missing)
    def edges(id: String, window: String, dir: EdgeDirection, types: Set[String] = Set.empty) =
      StorageResult
        .value(g.directedEdges(id, window, dir, types, 100, None))
        .get
        .items
    val out = edges(a, "all-years", EdgeDirection.Both)
    // outgoing coauthor edges (a is the canonical first endpoint), three authored, one affiliation
    assert(out.map(_.edgeType).count(_ == "COAUTHORED_WITH") == 3)
    assert(
      out.count(_.edgeType == "AUTHORED") == 3 && out.count(_.edgeType == "AFFILIATED_WITH") == 1
    )
    assert(out.map(_.edgeId) == out.map(_.edgeId).sorted)
    // the window constrains COAUTHORED_WITH only
    val other = edges(a, "2015-2019", EdgeDirection.Both)
    assert(other.count(_.edgeType == "COAUTHORED_WITH") == 0 && other.size == 4)
    assert(edges(a, "all-years", EdgeDirection.Both, Set("COAUTHORED_WITH")).size == 3)
    // incoming edges of b: coauthor a-b, plus its own outgoing b-c
    val b1 = edges(b, "all-years", EdgeDirection.In, Set("COAUTHORED_WITH"))
    assert(b1.map(_.fromId) == Vector(a) && b1.head.toId == b)
    // edge properties are the stored text-rendered ones and carry the evidence pointers
    val coauthor = out.find(_.edgeType == "COAUTHORED_WITH").get
    assert(coauthor.properties("windowId") == "all-years")
    assert(coauthor.properties("evidenceTable") == "edges/type=coauthored_with_support")
    assert(coauthor.properties("evidenceEdgeId") == coauthor.edgeId)
    assert(coauthor.properties("jointPublicationCount") == "1")
    assert(ujson.read(coauthor.properties("representativeWorkIdsJson")).arr.size == 1)
    assert(coauthor.provenance == Left("edge-provenance-absent"))
    val authored = out.find(_.edgeType == "AUTHORED").get
    assert(authored.provenance.isRight && authored.properties.contains("sourceEvidenceJson"))
    assert(authored.properties("policyVersion") == "synthetic-association")
    // paging: every page is bounded and the cursor resumes
    val first = StorageResult
      .value(g.directedEdges(a, "all-years", EdgeDirection.Both, Set.empty, 3, None))
      .get
    assert(first.items.size == 3 && first.cursor.nonEmpty)
    val second = StorageResult
      .value(g.directedEdges(a, "all-years", EdgeDirection.Both, Set.empty, 3, first.cursor))
      .get
    assert((first.items ++ second.items).map(_.edgeId).startsWith(out.take(3).map(_.edgeId)))
    assert(
      g.directedEdges(a, "all-years", EdgeDirection.Both, Set.empty, 0, None) == Rejected(
        "invalid-bound"
      )
    )
    assert(
      g.directedEdges(a, "all-years", EdgeDirection.Both, Set("NOPE"), 5, None) == Rejected(
        "invalid-bound"
      )
    )
  }

  test("shortest paths follow only same-window coauthor edges") {
    val g = stores().graphReader
    def ids(id1: String, id2: String) = StorageResult
      .value(
        g.directedEdges(id1, "all-years", EdgeDirection.Both, Set("COAUTHORED_WITH"), 100, None)
      )
      .get
      .items
    val da = ids(a, a).find(_.toId == d).get.edgeId
    val ab = ids(a, a).find(_.toId == b).get.edgeId
    assert(
      g.shortestPaths(d, b, 6, "all-years", 10) ==
        Found(Vector(GraphPath(Vector(d, a, b), Vector(da, ab))))
    )
    assert(g.shortestPaths(a, e, 6, "all-years", 10) == Found(Vector.empty))
    assert(g.shortestPaths(d, b, 1, "all-years", 10) == Found(Vector.empty))
    assert(g.shortestPaths(d, b, 6, "2015-2019", 10) == Found(Vector.empty))
    assert(g.shortestPaths(a, a, 6, "all-years", 10) == Found(Vector.empty))
    assert(g.shortestPaths(a, b, 0, "all-years", 10) == Rejected("invalid-bound"))
    assert(g.shortestPaths(a, b, 7, "all-years", 10) == Rejected("invalid-bound"))
    assert(g.shortestPaths(a, b, 3, "all-years", 101) == Rejected("invalid-bound"))
  }

  test("equal-length shortest paths are listed in node-ID order and bounded by the limit") {
    val ids = Vector("s", "t", "x", "y", "z").map("researcher:" + _)
    val Vector(s, t, x, y, z) = ids
    def edge(id: String, from: String, to: String) =
      new LocalEdge(id, from, to, "COAUTHORED_WITH", "w", () => Map.empty)
    val g = new LocalGraphReader(
      Map.empty,
      Vector(
        edge("e1", s, x),
        edge("e2", s, y),
        edge("e3", s, z),
        edge("e4", t, x),
        edge("e5", t, y),
        edge("e6", t, z)
      ),
      Map.empty
    )
    val all = StorageResult.value(g.shortestPaths(s, t, 3, "w", 10)).get
    assert(all.map(_.nodeIds) == Vector(Vector(s, x, t), Vector(s, y, t), Vector(s, z, t)))
    assert(all.map(_.edgeIds) == Vector(Vector("e1", "e4"), Vector("e2", "e5"), Vector("e3", "e6")))
    assert(StorageResult.value(g.shortestPaths(s, t, 3, "w", 2)).get.size == 2)
  }

  test("community members and cross-community edges come from the stored memberships") {
    val g = stores().graphReader
    assert(g.communityMembers(community(a), "all-years", 10) == Found(Vector(a)))
    assert(g.communityMembers(community(a), "2015-2019", 10) == Found(Vector.empty))
    val cross = StorageResult.value(g.crossCommunityEdges(community(a), "all-years", 10)).get
    assert(cross.items.map(_.nodeId).toSet == Set(b, c, d))
    assert(cross.items.forall(_.properties.contains("communityQualificationsJson")))
    assert(g.communityMembers(community(a), "all-years", 0) == Rejected("invalid-bound"))
  }

  test("metric store, entity links and runtime artifact answer for the same export") {
    val s = stores()
    val metric = StorageResult.value(s.metrics.get(a, "all-years")).get
    assert(
      metric.runId == runId && ujson.read(metric.payloadJson)("distinctCoauthorCount").num == 3
    )
    val q = ujson.read(metric.qualificationsJson)
    assert(q("communityMembership")("communityId").str == community(a))
    assert(
      SourceQualifications
        .get(
          upickle.default.read[SourceRunPointer](q("sourceRunPointer").render()),
          s.objects,
          s.artifactRegistry
        ) != Missing
    )
    val links = StorageResult.value(s.entityLinks.lookupByNormalizedName("Synthetic aaaa")).get
    assert(links.map(_.researcherId) == Vector(a) && links.head.runId == runId)
    val page = StorageResult
      .value(
        s.runtimeArtifacts.rank(
          "all-years",
          RuntimeRankingMetric.DistinctCoauthorCount,
          RuntimePopulationFilter(),
          3
        )
      )
      .get
    assert(page.items.map(_.metric.researcherId) == Vector(a, b, c))
    assert(page.populationCount == 6L && page.sourceRunId == runId)
    assert(page.sourceArtifactHash == s.artifactPointer.sha256)
    assert(s.runtimeArtifacts.communitySummary(community(a), "all-years").isInstanceOf[Found[?]])
    assert(s.runtimeArtifacts.bridgeMetrics(a, "all-years").isInstanceOf[Found[?]])
    assert(s.runtimeArtifacts.temporalChange(a, "2010-2014", "2015-2019").isInstanceOf[Found[?]])
    val context = StorageResult.value(s.runtimeArtifacts.researcherContext(a, "all-years", 10)).get
    assert(context.coauthorIds == Vector(b, c, d))
    // venue and topic associations are served; affiliations exist for a only
    assert(context.venueIds == Some(Vector(venue)) && context.topicIds == Some(Vector(topic1)))
    val edge = StorageResult
      .value(
        s.graphReader
          .directedEdges(a, "all-years", EdgeDirection.Out, Set("COAUTHORED_WITH"), 1, None)
      )
      .get
      .items
      .head
    assert(s.runtimeArtifacts.edgeSupport(edge.edgeId, "all-years").isInstanceOf[Found[?]])
  }

  test("an include-ids scope serves the bounded subset artifact from the object store") {
    val list = IncludeList.parse(a.getBytes(UTF_8)).toOption.get
    // 24 rows is exactly the closure of researcher a, so the degree fill adds nobody.
    val s = stores(
      LocalExportOptions(
        limits = LocalExportLimits(subsetArtifact = RuntimeArtifactConfig(maxRows = 24)),
        artifactScope = RuntimeArtifactScope.IncludeIds(list)
      )
    )
    assert(s.provenance.artifactScope == "include-ids:" + list.normalizedSha256)
    assert(s.objects.head(s.artifactPointer.key).isInstanceOf[Found[?]])
    val page = StorageResult
      .value(
        s.runtimeArtifacts.rank(
          "all-years",
          RuntimeArtifactDistinct,
          RuntimePopulationFilter(),
          5
        )
      )
      .get
    assert(page.items.map(_.metric.researcherId).contains(a))
    assert(page.populationCount == 1L)
    // the graph is still complete
    assert(s.counts.nodesByClass("RESEARCHER") == 6L)
    val unknown = IncludeList.parse(unknownResearcher.getBytes(UTF_8)).toOption.get
    val refused =
      load(options = LocalExportOptions(artifactScope = RuntimeArtifactScope.IncludeIds(unknown)))
    assert(refused.left.map(_.code) == Left("include-id-not-found"))
  }

  test("tampered rows, missing tables and bounds are refused with a typed error") {
    val changed = rows("metrics/type=bridges").head
    val served = rows + ("metrics/type=bridges" -> rows("metrics/type=bridges").map { row =>
      if (row == changed) {
        val copy = ujson.read(row.render()).obj; copy("participationCoefficient") = 0.5
        ujson.Obj.from(copy)
      } else row
    })
    assert(
      load(served = served).left.map(_.code) == Left(LocalExportError.contentHashMismatch),
      "rows that differ from the manifested hash"
    )
    val missing = manifests(rows).filterNot(_.logicalDataset == "metrics/type=bridges")
    assert(
      LocalExportStores.load(missing, new Reader(rows), LocalExportOptions()).left.map(_.code) ==
        Left(LocalExportError.missingTable)
    )
    val tooLarge = LocalExportOptions(limits = LocalExportLimits(maxRows = 10))
    assert(load(options = tooLarge).left.map(_.code) == Left(LocalExportError.exportTooLarge))
    val miscounted = manifests(rows).map(m =>
      if (m.logicalDataset == "edges/type=coauthored_with") m.copy(rowCount = m.rowCount + 1) else m
    )
    assert(
      LocalExportStores.load(miscounted, new Reader(rows), LocalExportOptions()).left.map(_.code) ==
        Left(LocalExportError.rowCountMismatch)
    )
    // authored edges need their work nodes: a dangling endpoint is not served
    val dangling = load(data = source)
    assert(dangling.left.map(_.code) == Left(LocalExportError.missingEndpoint))
    // a malformed edge ID fails the domain contract
    val badEdge = rows + ("edges/type=authored" -> rows("edges/type=authored")
      .map { row =>
        val copy = ujson.read(row.render()).obj
        copy("edgeId") = "graph-edge:" + "0" * 64
        ujson.Obj.from(copy)
      }
      .take(1))
    assert(load(badEdge).isLeft)
  }

  test("an export directory is refused unless it is a completed, bound Spark export") {
    val temp = Files.createTempDirectory("local-export-spec-")
    try {
      assert(
        LocalExportStores.load(temp.resolve("absent"), LocalExportLimits()).left.map(_.code) ==
          Left(LocalExportError.exportDirectoryMissing)
      )
      assert(
        LocalExportStores.load(temp, LocalExportLimits()).left.map(_.code) ==
          Left(LocalExportError.invalidManifests)
      )
      Files.createDirectories(temp.resolve("load-manifests"))
      Files.writeString(temp.resolve("load-manifests/s3.json"), write(manifests(rows)), UTF_8)
      // manifests exist, but there is no completion marker, run manifest or Parquet data
      val refused = LocalExportStores.load(temp, LocalExportLimits())
      assert(refused.left.map(_.code) == Left(LocalExportError.sourceRunIncomplete))
      Files.writeString(temp.resolve("load-manifests/s3.json"), "[", UTF_8)
      assert(
        LocalExportStores.load(temp, LocalExportLimits()).left.map(_.code) ==
          Left(LocalExportError.invalidManifests)
      )
    } finally {
      val walk = Files.walk(temp)
      try
        walk.sorted(java.util.Comparator.reverseOrder[Path]()).forEach(p => Files.deleteIfExists(p))
      finally walk.close()
    }
  }

  test("query-time ports are fresh and empty") {
    val s = stores()
    assert(s.newQuerySessionStore().get("query:none") == Missing)
    assert(s.newEvidenceStore().get("evidence:none") != null)
    assert(s.newAuditStore().get("query:none") != null)
  }

  test("every local edge property map equals the validator's CSV projection of its source row") {
    val s = stores()
    val g = s.graphReader
    val sourceRows = (rows("edges/type=coauthored_with") ++ rows("edges/type=authored") ++
      rows("edges/type=has_topic") ++ rows("edges/type=published_in") ++
      rows("edges/type=affiliated_with")).map(r => r("edgeId").str -> r).toMap
    val ids = (people ++ works ++ Vector(topic1, topic2, venue, institution1, institution2))
    val served = ids.flatMap(id =>
      StorageResult
        .value(g.directedEdges(id, "all-years", EdgeDirection.Out, Set.empty, 100, None))
        .get
        .items
    )
    assert(served.size == sourceRows.size && served.map(_.edgeId).toSet == sourceRows.keySet)
    served.foreach { edge =>
      val row = sourceRows(edge.edgeId)
      val columns =
        if (edge.edgeType == "COAUTHORED_WITH") GraphProjection.coauthorFromRow(row)
        else GraphProjection.graphEdge(row)
      assert(edge.properties == GraphProjection.properties(columns), edge.edgeId)
      // the structural columns are the stored endpoints and type
      assert(
        columns.take(4).map(_._2.str) == Vector(edge.edgeId, edge.fromId, edge.toId, edge.edgeType)
      )
    }
    // a coauthor edge, written out by hand from its row
    val coauthor = served.find(_.edgeType == "COAUTHORED_WITH").get
    val row = sourceRows(coauthor.edgeId)
    assert(
      coauthor.properties == Map(
        "policyVersion" -> row("policyVersion").str,
        "jointPublicationCount" -> "1",
        "firstCollaborationYear" -> "2015",
        "lastCollaborationYear" -> "2015",
        "windowId" -> "all-years",
        "representativeWorkIdsJson" -> row("representativeWorkIds").render(),
        "evidenceTable" -> "edges/type=coauthored_with_support",
        "evidenceEdgeId" -> coauthor.edgeId,
        "contextJson" -> row("context").render()
      )
    )
  }

  test("the projection strips type suffixes, drops nulls and renders integers as decimals") {
    val columns = GraphProjection.coauthor(
      "e",
      "a",
      "b",
      "p",
      12L,
      Some(2019),
      None,
      None,
      Some(2020),
      Some("w"),
      Some("[]"),
      None
    )
    assert(
      GraphProjection.properties(columns) == Map(
        "policyVersion" -> "p",
        "jointPublicationCount" -> "12",
        "firstCollaborationYear" -> "2019",
        "windowEndYear" -> "2020",
        "windowId" -> "w",
        "representativeWorkIdsJson" -> "[]",
        "evidenceTable" -> "edges/type=coauthored_with_support",
        "evidenceEdgeId" -> "e"
      )
    )
  }

  test("hash verification can be turned off, and the pointer then says so") {
    val changed = rows("metrics/type=bridges").head
    val served = rows + ("metrics/type=bridges" -> rows("metrics/type=bridges").map { row =>
      if (row == changed) {
        val copy = ujson.read(row.render()).obj; copy("participationCoefficient") = 0.5
        ujson.Obj.from(copy)
      } else row
    })
    val unverified = load(served = served, options = LocalExportOptions(verifySourceHashes = false))
      .fold(e => fail(e.toString), identity)
    assert(unverified.provenance.tables.forall(!_.hashVerified))
    assert(unverified.artifactPointer.sha256 != stores().artifactPointer.sha256)
    // the same rows with verification on are refused
    assert(load(served = served).left.map(_.code) == Left(LocalExportError.contentHashMismatch))
  }

  test("duplicate support rows, a repeated edge ID and dangling coauthor endpoints are refused") {
    val supports = rows("edges/type=coauthored_with_support")
    val duplicated = rows + ("edges/type=coauthored_with_support" -> (supports :+ supports.head))
    val dup = load(data = duplicated)
    assert(dup.left.map(_.code) == Left(LocalExportError.duplicateKey))
    assert(dup.left.map(_.part) == Left("table:edges/type=coauthored_with_support"))
    // researcher f is absent, with its authored edges, but its coauthor edge e-f remains
    val withoutF = rows +
      ("nodes/type=researcher" -> rows("nodes/type=researcher").filterNot(_("nodeId").str == f)) +
      ("edges/type=authored" -> rows("edges/type=authored").filterNot(_("fromId").str == f))
    val dangling = load(data = withoutF)
    assert(dangling.left.map(_.code) == Left(LocalExportError.missingEndpoint))
    assert(dangling.left.map(_.part) == Left("table:edges/type=coauthored_with"))
    val repeated = rows + ("edges/type=has_topic" -> (rows("edges/type=has_topic") :+ rows(
      "edges/type=has_topic"
    ).head))
    assert(load(data = repeated).left.map(_.code) == Left(LocalExportError.duplicateKey))
  }

  private val RuntimeArtifactDistinct = RuntimeRankingMetric.DistinctCoauthorCount
}
