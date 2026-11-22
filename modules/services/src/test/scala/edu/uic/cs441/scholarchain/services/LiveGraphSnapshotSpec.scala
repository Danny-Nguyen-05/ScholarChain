package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.{
  FakeGraphEdge,
  InMemoryGraphReader,
  InMemoryResearcherMetricStore,
  StorageResult
}
import java.net.URI
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.auth.credentials.{AwsBasicCredentials, StaticCredentialsProvider}

class LiveGraphSnapshotSpec extends AnyFunSuite {
  import AwsTestEnv.*
  private val context = RequestContext("req-graph", "trace-graph")
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "record-1",
    None,
    "snapshot-1",
    Some("2026-11-07"),
    None,
    "run:11111111-1111-4111-8111-111111111111",
    Vector("hand-written")
  )
  private val provenanceJson = upickle.default.write(provenance)
  private val evidenceJson = """{"kind":"work","workId":"w-1"}"""
  private def stored(extra: (String, String)*): Map[String, String] =
    Map("provenanceJson" -> provenanceJson, "sourceEvidenceJson" -> evidenceJson) ++ extra
  private def pointer(works: String = """["w-1","w-2"]"""): Map[String, String] = Map(
    "evidenceTable" -> "support/versions/1/edges.json",
    "evidenceEdgeId" -> "support-3",
    "windowId" -> "all-years",
    "representativeWorkIdsJson" -> works
  )
  private def row(
      id: String,
      from: String,
      to: String,
      edgeType: String,
      props: Map[String, String],
      window: String = "all-years"
  ) = FakeGraphEdge(from, to, id, edgeType, window, props)
  private val node = GraphNode(
    "n1",
    SchemaVersions.domain,
    GraphNodeClass.Researcher,
    "N1",
    Vector.empty,
    provenance
  )

  // Hand-written store. Stored start/end are as written; n1 is the start of e1 and e3, the end of
  // e2 and e4. e5 is another window, e6 a type the API does not serve.
  private val rows = Vector(
    row("e1", "n1", "w1", "AUTHORED", stored()),
    row("e2", "a2", "n1", "AFFILIATED_WITH", stored()),
    row("e3", "n1", "n3", "COAUTHORED_WITH", pointer()),
    row("e4", "n0", "n1", "COAUTHORED_WITH", pointer("""["w-9"]""")),
    row("e5", "n1", "n9", "COAUTHORED_WITH", pointer(), window = "2015-2017"),
    row("e6", "n1", "x1", "RESOLVES_TO", Map.empty)
  )
  private def snapshot(
      edges: Vector[FakeGraphEdge] = rows,
      maxLimit: Int = 100,
      pageSize: Int = 100,
      scanLimit: Int = 10000
  ) = new LiveGraphSnapshot(
    "snapshot-under-test",
    new InMemoryGraphReader(
      nodes = Vector(node, node.copy(nodeId = "n3")),
      edges = edges,
      maxLimit = maxLimit
    ),
    new InMemoryResearcherMetricStore,
    pageSize,
    scanLimit
  )
  private def api(s: LiveGraphSnapshot, config: GraphApiConfig = GraphApiConfig()) =
    new GraphApi(s, config)
  private def neighbors(a: GraphApi, params: Map[String, String]) =
    a.neighbors("n1", params, context).toOption.get.body("items").arr.toVector
  private def ids(items: Vector[ujson.Value]) = items.map(_("edgeId").str)

  test("out, in and both select by stored start and end; the undirected type is incident in all") {
    val a = api(snapshot())
    val out = neighbors(a, Map("direction" -> "out"))
    assert(ids(out) == Vector("e1", "e3", "e4"))
    assert(out.map(_("nodeId").str) == Vector("w1", "n3", "n0"))
    val in = neighbors(a, Map("direction" -> "in"))
    assert(ids(in) == Vector("e2", "e3", "e4"))
    assert(in.map(_("nodeId").str) == Vector("a2", "n3", "n0"))
    val both = neighbors(a, Map("direction" -> "both"))
    assert(ids(both) == Vector("e1", "e2", "e3", "e4"))
    // The stored order is reported as stored, never reoriented.
    val e4 = both.find(_("edgeId").str == "e4").get
    assert(
      e4("fromId").str == "n0" && e4("toId").str == "n1" && e4("edgeType").str == "COAUTHORED_WITH"
    )
  }

  test("window constrains only the undirected type and unserved types are never read") {
    val a = api(snapshot())
    assert(ids(neighbors(a, Map("direction" -> "both"))) == Vector("e1", "e2", "e3", "e4"))
    val other = neighbors(a, Map("direction" -> "both", "window" -> "2015-2017"))
    assert(ids(other) == Vector("e1", "e2", "e5"), "typed edges ignore the window, e5 matches it")
  }

  test("a stored provenance record is reported and a pointer row never gets an invented one") {
    val items = neighbors(api(snapshot()), Map("direction" -> "both"))
    val e1 = items.find(_("edgeId").str == "e1").get
    assert(e1("provenance") == upickle.default.writeJs(provenance))
    assert(e1("evidence") == ujson.read(evidenceJson))
    val e3 = items.find(_("edgeId").str == "e3").get
    assert(e3("provenance") == ujson.Null)
    assert(
      e3("evidence") == ujson.Obj(
        "kind" -> "stored-evidence-pointer",
        "evidenceTable" -> "support/versions/1/edges.json",
        "evidenceEdgeId" -> "support-3",
        "windowId" -> "all-years",
        "representativeWorkIds" -> ujson.Arr("w-1", "w-2")
      )
    )
  }

  test("a row without provenance or a pointer, or with malformed records, refuses the read") {
    def refusal(row: FakeGraphEdge) =
      snapshot(Vector(row)).incidentEdges("n1", "all-years")
    assert(
      refusal(row("x", "n1", "w", "AUTHORED", Map.empty)) == StorageResult.Rejected(
        "edge-provenance-absent"
      )
    )
    assert(
      refusal(row("x", "n1", "n2", "COAUTHORED_WITH", Map("evidenceTable" -> "t"))) ==
        StorageResult.Rejected("edge-provenance-absent")
    )
    assert(
      refusal(row("x", "n1", "w", "AUTHORED", Map("provenanceJson" -> "{not json"))) ==
        StorageResult.Rejected("malformed-edge-provenance")
    )
    assert(
      refusal(row("x", "n1", "w", "AUTHORED", stored("sourceEvidenceJson" -> "{bad"))) ==
        StorageResult.Rejected("malformed-edge-evidence")
    )
    assert(
      refusal(row("x", "n1", "n2", "COAUTHORED_WITH", pointer("[oops"))) ==
        StorageResult.Rejected("malformed-edge-evidence")
    )
    val failing = api(snapshot(Vector(row("x", "n1", "w", "AUTHORED", Map.empty))))
    assert(failing.neighbors("n1", Map.empty, context).left.toOption.get.status == 502)
  }

  test("paging passes the cursor through until the store reports no more rows") {
    val cursors = new java.util.concurrent.ConcurrentLinkedQueue[Option[String]]()
    val inner = new InMemoryGraphReader(
      nodes = Vector(node, node.copy(nodeId = "n3")),
      edges = rows,
      maxLimit = 2
    )
    val counting = new edu.uic.cs441.scholarchain.storage.DirectedGraphReader {
      export inner.{
        node,
        neighbors,
        directCoauthors,
        shortestPaths,
        communityMembers,
        crossCommunityEdges
      }
      def directedEdges(
          id: String,
          window: String,
          direction: edu.uic.cs441.scholarchain.storage.EdgeDirection,
          edgeTypes: Set[String],
          limit: Int,
          cursor: Option[String]
      ) = {
        cursors.add(cursor);
        inner.directedEdges(id, window, direction, edgeTypes, limit, cursor)
      }
    }
    val s = new LiveGraphSnapshot("s", counting, new InMemoryResearcherMetricStore, pageSize = 2)
    val all = StorageResult.value(s.incidentEdges("n1", "all-years")).get
    assert(all.map(_.edgeId) == Vector("e1", "e3", "e2", "e4"), "outgoing by id, then incoming")
    val seen: Vector[Option[String]] = cursors.toArray.toVector.map(_.asInstanceOf[Option[String]])
    assert(
      seen.size == 2 && seen.head.isEmpty && seen(1).nonEmpty,
      "the store cursor is passed back verbatim"
    )
    assert(all.find(_.edgeId == "e3").get.undirected && !all.find(_.edgeId == "e1").get.undirected)
  }

  test("a page size above the store bound propagates invalid-bound and the API reports a failure") {
    val s = snapshot(maxLimit = 2, pageSize = 5)
    assert(s.incidentEdges("n1", "all-years") == StorageResult.Rejected("invalid-bound"))
    assert(api(s).neighbors("n1", Map.empty, context).left.toOption.get.status == 502)
  }

  test("exceeding the scan limit lets the API report its scan cap instead of truncating") {
    val s = snapshot(pageSize = 2, scanLimit = 1)
    val reply = api(s, GraphApiConfig(maxScannedEdges = 1)).neighbors("n1", Map.empty, context)
    assert(reply.left.toOption.get.code == "GRAPH_SCAN_CAP")
  }

  test("shortest paths walk the served edges, including the undirected type") {
    val a = api(snapshot())
    val reply = a.paths(Map("from" -> "n1", "to" -> "n3", "maxDepth" -> "2"), context).toOption.get
    assert(
      reply.body("paths").arr.map(_("nodeIds").arr.map(_.str).toVector) == Vector(
        Vector("n1", "n3")
      )
    )
    assert(reply.body("paths")(0)("edgeIds").arr.map(_.str).toVector == Vector("e3"))
    assert(reply.body("snapshot").str == "snapshot-under-test")
  }

  test("the directed core projection stays refused and metric reads pass through") {
    val s = snapshot()
    assert(
      s.edges("n1", "all-years") == StorageResult.Rejected(LiveGraphSnapshot.coreEdgesUnavailable)
    )
    assert(s.metrics("n1", "all-years") == StorageResult.Missing)
    assert(s.node("n1") == StorageResult.Found(node))
  }

  private val credentials =
    StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test"))
  private val endpoint =
    URI.create("https://sc-reader.cluster-ro-x.us-east-2.neptune.amazonaws.com:8182")

  test("the storage provider maps connect success, each refusal code and an idempotent close") {
    val opened = StorageGraphReaderProvider.open(endpoint, "us-east-2", credentials, 3000)
    assert(opened.isRight)
    opened.toOption.get.close(); opened.toOption.get.close()
    def code(
        e: URI,
        region: String,
        c: software.amazon.awssdk.auth.credentials.AwsCredentialsProvider
    ) =
      StorageGraphReaderProvider.open(e, region, c, 3000).left.toOption.get
    assert(
      code(URI.create("http://h.example:8182"), "us-east-2", credentials) ==
        "invalid-aws-configuration:SCHOLARCHAIN_NEPTUNE_ENDPOINT"
    )
    assert(
      code(URI.create("https://h.example"), "us-east-2", credentials) ==
        "invalid-aws-configuration:SCHOLARCHAIN_NEPTUNE_ENDPOINT"
    )
    assert(code(endpoint, "mars", credentials) == "invalid-aws-configuration:AWS_REGION")
    assert(code(endpoint, "us-east-2", null) == "aws-credentials-unavailable")
    assert(
      StorageGraphReaderProvider.refusal(
        "anything-else"
      ) == StorageGraphReaderProvider.connectFailed
    )
  }

  private final class RecordingProvider(d: Dependencies) extends GraphReaderProvider {
    val opened = new AtomicInteger
    val closed = new AtomicInteger
    @volatile var endpoint: Option[URI] = None
    @volatile var region: Option[String] = None
    @volatile var timeout: Option[Long] = None
    def open(
        e: URI,
        r: String,
        c: software.amazon.awssdk.auth.credentials.AwsCredentialsProvider,
        t: Long
    ) = {
      opened.incrementAndGet(); endpoint = Some(e); region = Some(r); timeout = Some(t)
      Right(OpenedGraphReader(new FakeReader(d), () => { closed.incrementAndGet(); () }))
    }
  }

  test("graph-service starts in aws mode through the provider and readiness follows its checks") {
    val factory = new FakeFactory
    val provider = new RecordingProvider(factory.d)
    factory.graphProvider = Some(provider)
    val env = graph ++ Map(
      "SCHOLARCHAIN_READINESS_CACHE_MS" -> "1",
      "SCHOLARCHAIN_NEPTUNE_QUERY_TIMEOUT_MS" -> "4000"
    )
    val running = ServiceBootstrap.launch("graph-service", env, factory).toOption.get
    try {
      assert(provider.opened.get == 1)
      assert(provider.endpoint.map(_.toString) == Some(graph("SCHOLARCHAIN_NEPTUNE_ENDPOINT")))
      assert(provider.region.contains("us-east-2") && provider.timeout.contains(4000L))
      assert(Http.get(running.port, "/healthz")._1 == 200)
      assert(Http.get(running.port, "/readyz")._1 == 200, "an empty graph is ready")
      factory.d.failing = Set("neptune")
      assert(settle(true)(Http.get(running.port, "/readyz")._1 == 503))
      assert(Http.get(running.port, "/healthz")._1 == 200)
      factory.d.failing = Set.empty
      assert(settle(true)(Http.get(running.port, "/readyz")._1 == 200))
      val headers = Map("Authorization" -> ("Bearer " + internalToken))
      val (status, body) = Http.get(running.port, "/internal/v1/graph/nodes/n1/neighbors", headers)
      assert(status == 404, body)
    } finally running.close()
    assert(provider.closed.get == 1 && factory.closed.get == 1)
  }

  test("a provider refusal exits 2 with only the closed message") {
    val factory = new FakeFactory
    factory.graphProvider = Some(new GraphReaderProvider {
      def open(
          e: URI,
          r: String,
          c: software.amazon.awssdk.auth.credentials.AwsCredentialsProvider,
          t: Long
      ) = Left(StorageGraphReaderProvider.refusal("missing-credentials"))
    })
    val original = System.err
    val buffer = new java.io.ByteArrayOutputStream
    System.setErr(new java.io.PrintStream(buffer, true))
    val result =
      try ServiceBootstrap.launch("graph-service", graph, factory)
      finally System.setErr(original)
    assert(result.left.toOption.contains(2))
    assert(buffer.toString.trim == "aws-credentials-unavailable")
  }
}
