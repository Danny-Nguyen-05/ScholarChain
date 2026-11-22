package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

/** Shortest-path and community routes of the graph API, and the remote reader over them. */
class GraphPathsAndCommunitiesSpec extends AnyFunSuite {
  private val context = RequestContext("synthetic-paths-request", "synthetic-paths-trace")
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-source",
    None,
    "synthetic-snapshot",
    None,
    None,
    "run:00112233-4455-4677-8899-aabbccddeeff",
    Vector("Synthetic fixture only")
  )
  private def node(id: String) =
    GraphNode(id, SchemaVersions.domain, GraphNodeClass.Researcher, id, Vector.empty, provenance)
  private def edge(id: String, a: String, b: String, edgeType: String = "COAUTHORED_WITH") =
    SnapshotEdge(id, edgeType, a, b, edgeType == "COAUTHORED_WITH", ujson.Null)

  /** Adjacency snapshot over hand-written edges; counts the nodes whose edges were read. */
  private class Adjacency(nodes: Set[String], edges: Vector[SnapshotEdge]) extends GraphSnapshot {
    val reads = new AtomicInteger
    def snapshotId = "synthetic-adjacency"
    def node(id: String): StorageResult[GraphNode] =
      if (nodes(id)) StorageResult.Found(GraphPathsAndCommunitiesSpec.this.node(id))
      else StorageResult.Missing
    def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] =
      StorageResult.Rejected(LiveGraphSnapshot.coreEdgesUnavailable)
    override def incidentEdges(id: String, window: String): StorageResult[Vector[SnapshotEdge]] = {
      reads.incrementAndGet()
      StorageResult.Found(edges.filter(e => e.fromId == id || e.toId == id))
    }
    def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord] =
      StorageResult.Missing
  }
  private def adjacency(edges: Vector[SnapshotEdge], extra: Set[String] = Set.empty) =
    new Adjacency(edges.flatMap(e => Vector(e.fromId, e.toId)).toSet ++ extra, edges)

  private def pathBody(api: GraphApi, from: String, to: String, extra: (String, String)*) =
    api.paths(Map("from" -> from, "to" -> to) ++ extra, context).map(_.body)
  private def nodeIds(body: ujson.Value) = body("paths")(0)("nodeIds").arr.map(_.str).toVector

  /** `from` has 250 coauthors, each with five further coauthors: well over 200 nodes within two
    * hops and over 1,000 within three. `to` is one of the direct coauthors.
    */
  private val hubEdges: Vector[SnapshotEdge] = {
    val direct = (1 to 250).toVector.map(i => edge(f"h$i%03d", "from", f"n$i%03d"))
    val second = for (i <- 1 to 250; j <- 1 to 5) yield edge(f"s$i%03d$j", f"n$i%03d", f"m$i%03d$j")
    direct ++ second
  }

  test("a one-hop pair is found at the runtime depth of 6 though its endpoint has a huge area") {
    val snap = adjacency(hubEdges)
    val api = new GraphApi(snap)
    try {
      val body =
        pathBody(api, "from", "n117", "maxDepth" -> "6", "window" -> "all-years").toOption.get
      assert(nodeIds(body) == Vector("from", "n117"))
      assert(body("paths")(0)("edgeIds").arr.map(_.str) == Vector("h117"))
      assert(body("maxDepth").num == 6 && !body("clamped").bool && !body("truncated").bool)
      assert(body("snapshot").str == "synthetic-adjacency")
      // The search stopped at the first level containing `to`: only `from` was expanded.
      assert(snap.reads.get == 1)
    } finally api.close()
  }

  test("a two-hop pair is found, deterministically, and expands only the levels it needs") {
    val edges = hubEdges ++ Vector(edge("z1", "from", "bridge"), edge("z2", "bridge", "target"))
    val snap = adjacency(edges)
    val api = new GraphApi(snap)
    try {
      val body = pathBody(api, "from", "target", "maxDepth" -> "6").toOption.get
      assert(nodeIds(body) == Vector("from", "bridge", "target"))
      assert(body("paths")(0)("edgeIds").arr.map(_.str) == Vector("z1", "z2"))
      // `from` (level 1), then `bridge`, the first level-one node in order, which reaches `target`.
      assert(snap.reads.get == 2)
      assert(pathBody(api, "from", "target", "maxDepth" -> "6").toOption.get == body)
    } finally api.close()
  }

  test("two equally short routes give one stable answer: the lowest node and edge order wins") {
    val edges = Vector(
      edge("e1", "from", "b"),
      edge("e2", "from", "a"),
      edge("e3", "a", "to"),
      edge("e4", "b", "to")
    )
    val api = new GraphApi(adjacency(edges))
    try {
      val body = pathBody(api, "from", "to").toOption.get
      assert(nodeIds(body) == Vector("from", "a", "to"))
      assert(body("paths")(0)("edgeIds").arr.map(_.str) == Vector("e2", "e3"))
    } finally api.close()
  }

  test("only coauthor edges are walked; a work in common never shortens or creates a path") {
    val edges = Vector(
      edge("w1", "from", "work", "AUTHORED"),
      edge("w2", "to", "work", "AUTHORED"),
      edge("c1", "from", "x"),
      edge("c2", "x", "y"),
      edge("c3", "y", "to")
    )
    val api = new GraphApi(adjacency(edges))
    try {
      val body = pathBody(api, "from", "to").toOption.get
      assert(nodeIds(body) == Vector("from", "x", "y", "to"))
      val noCoauthor = new GraphApi(adjacency(edges.take(2)))
      try
        assert(pathBody(noCoauthor, "from", "to").toOption.get("paths").arr.isEmpty)
      finally noCoauthor.close()
    } finally api.close()
  }

  test("a pair with no path within the limits is an empty, untruncated 200") {
    val api = new GraphApi(adjacency(hubEdges, Set("island")))
    try {
      val body = pathBody(api, "from", "island", "maxDepth" -> "6").toOption.get
      assert(body("paths").arr.isEmpty && !body("truncated").bool && !body("clamped").bool)
      // Same node: a zero-edge path, as before.
      val same = pathBody(api, "from", "from").toOption.get
      assert(nodeIds(same) == Vector("from") && same("paths")(0)("edgeIds").arr.isEmpty)
    } finally api.close()
  }

  test("depth defaults to the path ceiling and a larger request is clamped, never rejected") {
    val chain = (1 to 8).toVector.map(i => edge("c" + i, "p" + (i - 1), "p" + i))
    val api = new GraphApi(adjacency(chain))
    try {
      val byDefault = pathBody(api, "p0", "p6").toOption.get
      assert(byDefault("maxDepth").num == 6 && nodeIds(byDefault).size == 7)
      val tooFar = pathBody(api, "p0", "p8", "maxDepth" -> "50").toOption.get
      assert(tooFar("paths").arr.isEmpty && tooFar("maxDepth").num == 6 && tooFar("clamped").bool)
      assert(pathBody(api, "p0", "p2", "maxDepth" -> "1").toOption.get("paths").arr.isEmpty)
      for (bad <- Vector("0", "-1", "abc", ""))
        assert(pathBody(api, "p0", "p2", "maxDepth" -> bad).left.toOption.exists(_.status == 400))
      assert(pathBody(api, "p0", "", "maxDepth" -> "2").left.toOption.exists(_.status == 400))
      assert(pathBody(api, "p0", "p2", "stray" -> "1").left.toOption.exists(_.status == 400))
      assert(pathBody(api, "absent", "p2").left.toOption.exists(_.status == 404))
    } finally api.close()
    val small = new GraphApi(adjacency(chain), GraphApiConfig(maxPathDepth = 3))
    try {
      val body = pathBody(small, "p0", "p4", "maxDepth" -> "6").toOption.get
      assert(body("paths").arr.isEmpty && body("maxDepth").num == 3 && body("clamped").bool)
      assert(pathBody(small, "p0", "p3", "maxDepth" -> "6").toOption.get("paths").arr.nonEmpty)
    } finally small.close()
    intercept[IllegalArgumentException](GraphApiConfig(maxDepth = 3, maxPathDepth = 2))
  }

  test("a node or scan cap hit before `to` is a bounded truncated 200, not a hard error") {
    val edges = hubEdges ++ Vector(edge("z1", "from", "zbridge"), edge("z2", "zbridge", "target"))
    val nodeCapped = new GraphApi(adjacency(edges), GraphApiConfig(maxVisitedNodes = 100))
    try {
      val body = pathBody(nodeCapped, "from", "target", "maxDepth" -> "6").toOption.get
      assert(body("paths").arr.isEmpty && body("truncated").bool)
      assert(body("truncationReason").str == "node-cap")
    } finally nodeCapped.close()
    val scanCapped = new GraphApi(adjacency(edges), GraphApiConfig(maxScannedEdges = 300))
    try {
      val body = pathBody(scanCapped, "from", "target", "maxDepth" -> "6").toOption.get
      assert(body("paths").arr.isEmpty && body("truncated").bool)
      assert(body("truncationReason").str == "scan-cap")
    } finally scanCapped.close()
  }

  test("snapshot read failures and the deadline stay typed errors") {
    val failing = new GraphApi(new Adjacency(Set("from", "to"), Vector.empty) {
      override def incidentEdges(id: String, window: String) =
        StorageResult.Rejected("edge-read-failed")
    })
    try assert(pathBody(failing, "from", "to").left.toOption.exists(_.status == 502))
    finally failing.close()
    val slow = new GraphApi(new Adjacency(Set("from", "far"), Vector.empty) {
      override def incidentEdges(id: String, window: String) = {
        Thread.sleep(300); StorageResult.Found(Vector(edge("e", "from", "next")))
      }
    })
    try {
      val error = slow
        .paths(Map("from" -> "from", "to" -> "far", "timeoutMs" -> "50"), context)
        .left
        .toOption
        .get
      assert(ApiError.isGraphDeadline(error))
    } finally slow.close()
  }

  // ---- the remote reader over the graph API over the local export ------------------------------

  private val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 1)
  private def communityOf(i: Int) = "community:" + StableIds.sha256Hex(fixture.id(i))
  private def liveApi(config: GraphApiConfig = GraphApiConfig()) = {
    val stores = fixture.stores()
    val graph = new GraphApi(
      new LiveGraphSnapshot("local-test", stores.graphReader, stores.metrics),
      config
    )
    (stores, graph)
  }

  test("the remote reader returns the stored community members and cross-community edges") {
    val (stores, api) = liveApi()
    try {
      val remote = new RemoteGraphReader(api, context)
      val id = communityOf(0)
      assert(
        remote.communityMembers(id, "all-years", 50) == StorageResult.Found(Vector(fixture.hub))
      )
      assert(
        remote.communityMembers(id, "all-years", 50) ==
          stores.graphReader.communityMembers(id, "all-years", 50)
      )
      val cross = StorageResult.value(remote.crossCommunityEdges(id, "all-years", 50)).get
      assert(cross.cursor.isEmpty)
      assert(cross.items.map(_.edgeId).toSet == fixture.edgeIds.toSet && cross.items.size == 3)
      assert(cross.items.map(_.nodeId).toSet == (1 to 3).map(fixture.id).toSet)
      assert(cross.items.forall(_.edgeType == "COAUTHORED_WITH"))
      val direct =
        StorageResult.value(stores.graphReader.crossCommunityEdges(id, "all-years", 50)).get
      assert(cross.items == direct.items)
      // A coauthor's community lists the hub across the same edge.
      val back =
        StorageResult.value(remote.crossCommunityEdges(communityOf(1), "all-years", 50)).get
      assert(back.items.map(_.nodeId) == Vector(fixture.hub))
      // The limit bounds the page; an unknown community is an empty, honest answer.
      assert(
        StorageResult.value(remote.crossCommunityEdges(id, "all-years", 2)).get.items.size == 2
      )
      assert(
        remote.communityMembers("community:absent", "all-years", 5) == StorageResult.Found(
          Vector.empty
        )
      )
    } finally api.close()
  }

  test("community routes validate their bounds and a snapshot without communities refuses typed") {
    val (_, api) = liveApi()
    try {
      for (bad <- Vector("0", "201", "x"))
        for (call <- Vector(api.communityMembers _, api.crossCommunityEdges _))
          assert(
            call(communityOf(0), Map("limit" -> bad), context).left.toOption.exists(_.status == 400)
          )
      assert(api.communityMembers(communityOf(0), Map("stray" -> "1"), context).isLeft)
      assert(api.communityMembers("", Map.empty, context).left.toOption.exists(_.status == 400))
      assert(
        api
          .communityMembers(communityOf(0), Map("timeoutMs" -> "0"), context)
          .left
          .toOption
          .exists(_.status == 400)
      )
      val ok = api.communityMembers(communityOf(0), Map.empty, context).toOption.get.body
      assert(ok("members").arr.map(_.str) == Vector(fixture.hub) && ok("window").str == "all-years")
    } finally api.close()
    val none = new GraphApi(adjacency(Vector(edge("e", "a", "b"))))
    try {
      val refused = none.communityMembers("community:x", Map.empty, context).left.toOption.get
      assert(refused.status == 422 && refused.code == "COMMUNITY_UNSUPPORTED")
      val remote = new RemoteGraphReader(none, context)
      assert(
        remote.communityMembers("community:x", "all-years", 5) ==
          StorageResult.Rejected("remote-graph-operation-unsupported")
      )
      assert(
        remote.crossCommunityEdges("community:x", "all-years", 5) ==
          StorageResult.Rejected("remote-graph-operation-unsupported")
      )
    } finally none.close()
  }

  test("the remote reader maps shortest-path replies to the statuses the retrieval agent reads") {
    val (_, api) = liveApi()
    try {
      val remote = new RemoteGraphReader(api, context)
      // Two coauthors reach each other through the hub, at the runtime depth of 6.
      val found = StorageResult
        .value(remote.shortestPaths(fixture.id(1), fixture.id(2), 6, "all-years", 5))
        .get
      assert(found.map(_.nodeIds) == Vector(Vector(fixture.id(1), fixture.hub, fixture.id(2))))
      assert(found.head.edgeIds.size == 2 && found.head.edgeIds.forall(fixture.edgeIds.contains))
      assert(
        remote.shortestPaths(fixture.id(1), fixture.hub, 6, "all-years", 5) ==
          StorageResult.Found(
            Vector(GraphPath(Vector(fixture.id(1), fixture.hub), Vector(fixture.edgeIds.head)))
          )
      )
      assert(
        remote.shortestPaths(fixture.id(1), fixture.absentResearcher, 6, "all-years", 5) ==
          StorageResult.Missing
      )
      assert(
        remote.shortestPaths(fixture.absentResearcher, fixture.hub, 6, "all-years", 5) ==
          StorageResult.Missing
      )
    } finally api.close()
    val chain = (1 to 5).toVector.map(i => edge("c" + i, "p" + (i - 1), "p" + i))
    // Nothing found and the search was cut short: a closed refusal, never an empty result (which
    // the retrieval agent would verify as "no path within N hops") and never a status claim.
    val clamped = new GraphApi(adjacency(chain), GraphApiConfig(maxPathDepth = 3))
    try {
      val reader = new RemoteGraphReader(clamped, context)
      assert(
        reader.shortestPaths("p0", "p5", 6, "all-years", 5) ==
          StorageResult.Rejected("path-depth-clamped")
      )
      // A path inside the clamped ceiling is still a path; asking for exactly the ceiling is not a clamp.
      assert(StorageResult.value(reader.shortestPaths("p0", "p3", 6, "all-years", 5)).get.size == 1)
      assert(
        reader.shortestPaths("p0", "p5", 3, "all-years", 5) == StorageResult.Found(Vector.empty)
      )
    } finally clamped.close()
    val capEdges = hubEdges ++ Vector(edge("z1", "from", "q"), edge("z2", "q", "t"))
    val capped = new GraphApi(adjacency(capEdges), GraphApiConfig(maxVisitedNodes = 100))
    try
      assert(
        new RemoteGraphReader(capped, context).shortestPaths("from", "t", 6, "all-years", 5) ==
          StorageResult.Rejected("path-search-truncated")
      )
    finally capped.close()
    // Clamped and truncated: the truncation is reported (the search was incomplete either way).
    val both = new GraphApi(
      adjacency(capEdges),
      GraphApiConfig(maxVisitedNodes = 100, maxPathDepth = 3)
    )
    try
      assert(
        new RemoteGraphReader(both, context).shortestPaths("from", "t", 6, "all-years", 5) ==
          StorageResult.Rejected("path-search-truncated")
      )
    finally both.close()
  }

  test("a missing target is a 404 before any search, and the reader reports it as Missing") {
    val snap = adjacency(hubEdges)
    val api = new GraphApi(snap)
    try {
      assert(
        pathBody(api, "from", "absent", "maxDepth" -> "6").left.toOption.exists(_.status == 404)
      )
      assert(snap.reads.get == 0)
      assert(
        new RemoteGraphReader(api, context).shortestPaths("from", "absent", 6, "all-years", 5) ==
          StorageResult.Missing
      )
    } finally api.close()
  }
}
