package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.auth.credentials.{
  AwsBasicCredentials,
  AwsCredentials,
  AwsCredentialsProvider,
  StaticCredentialsProvider
}
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.net.URI
import java.util.concurrent.atomic.AtomicInteger
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import StorageResult.*

/** Offline tests for the storage-owned reader factory and the additive directed edge read. The
  * expected rows are written by hand from the graph below, never computed by the reader.
  *
  * Stored edges (start -> end), edge IDs sort e1 < e2 < e3 < e4 < e5:
  * {{{
  *   e1  A -> B  AUTHORED        (carries provenanceJson)
  *   e2  C -> A  AFFILIATED_WITH
  *   e3  A -> A  HAS_TOPIC       (self-loop)
  *   e4  A -> C  COAUTHORED_WITH window w1 (evidence pointers only, no provenanceJson)
  *   e5  B -> C  PUBLISHED_IN
  * }}}
  */
class DirectedGraphReaderSpec extends AnyFunSuite {
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-directed",
    None,
    "synthetic",
    None,
    None,
    "run:00112233-4455-4677-8899-aabbccddeeff",
    Vector("Synthetic module fixture")
  )
  private val provenanceJson = CoreJson.compact(provenance)
  private val e1 = FakeGraphEdge(
    "A",
    "B",
    "e1",
    "AUTHORED",
    "w1",
    Map("provenanceJson" -> provenanceJson, "policyVersion" -> "p1")
  )
  private val e2 =
    FakeGraphEdge("C", "A", "e2", "AFFILIATED_WITH", "w1", Map("policyVersion" -> "p1"))
  private val e3 = FakeGraphEdge("A", "A", "e3", "HAS_TOPIC", "w1")
  private val e4 = FakeGraphEdge(
    "A",
    "C",
    "e4",
    "COAUTHORED_WITH",
    "w1",
    Map("windowId" -> "w1", "evidenceTable" -> "support", "evidenceEdgeId" -> "e4")
  )
  private val e5 = FakeGraphEdge("B", "C", "e5", "PUBLISHED_IN", "w1")
  private val all = Vector(e1, e2, e3, e4, e5)
  private def row(e: FakeGraphEdge) =
    DirectedGraphEdge(e.from, e.to, e.edgeId, e.edgeType, e.properties)

  // Hand-written expectations (edge IDs per node, direction and window).
  private val aOut = Vector(row(e1), row(e3), row(e4))
  private val aIn = Vector(row(e2), row(e3))
  private val aBoth = Vector(row(e1), row(e3), row(e4), row(e2))

  /** An independent stand-in for the engine: it interprets the three allowlisted templates by their
    * MATCH shape and answers from the hand-written edge list, applying the request parameters. The
    * reader must map columns itself.
    */
  private final class Engine(edges: Vector[FakeGraphEdge]) {
    val requests = mutable.Buffer.empty[(String, ujson.Obj)]
    private def text(s: String) = Document.fromString(s)
    val client: NeptunedataClient = Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef =
            method.getName match {
              case "executeOpenCypherQuery" =>
                val request = args(0).asInstanceOf[ExecuteOpenCypherQueryRequest]
                val params = ujson.read(request.parameters()).asInstanceOf[ujson.Obj]
                requests += request.openCypherQuery() -> params
                answer(request.openCypherQuery(), params)
              case "close" => null
              case other   => throw new AssertionError("unexpected SDK operation " + other)
            }
        }
      )
      .asInstanceOf[NeptunedataClient]
    private def answer(query: String, p: ujson.Obj) = {
      val id = p("id").str; val window = p("window").str
      val types = p("types").arr.map(_.str).toSet
      val offset = p("offset").num.toInt; val limit = p("limit").num.toInt
      def ok(e: FakeGraphEdge) =
        types(e.edgeType) && (e.edgeType != "COAUTHORED_WITH" || e.windowOf == window)
      val rows =
        if (query.contains("MATCH (a)-[r]->(b)"))
          edges.filter(e => e.from == id && ok(e)).sortBy(_.edgeId)
        else if (query.contains("id(b) <> id(a)"))
          edges.filter(e => e.to == id && e.from != id && ok(e)).sortBy(_.edgeId)
        else if (query.contains("MATCH (b)-[r]->(a)"))
          edges.filter(e => e.to == id && ok(e)).sortBy(_.edgeId)
        else throw new AssertionError("unrecognized template")
      val documents = rows.slice(offset, offset + limit).map { e =>
        Document.fromMap(
          Map(
            "fromId" -> text(e.from),
            "toId" -> text(e.to),
            "edgeId" -> text(e.edgeId),
            "edgeType" -> text(e.edgeType),
            "properties" -> Document.fromMap(
              e.properties.map((k, v) => k -> text(v)).asJava
            )
          ).asJava
        )
      }
      ExecuteOpenCypherQueryResponse
        .builder()
        .results(Document.fromList(documents.asJava))
        .build()
    }
  }
  extension (e: FakeGraphEdge)
    private def windowOf: String = e.properties.getOrElse("windowId", e.window)

  private def neptune(edges: Vector[FakeGraphEdge] = all, config: GraphReaderConfig = noRetry) = {
    val engine = new Engine(edges)
    engine -> new NeptuneGraphReader(engine.client, config)
  }
  private val noRetry = GraphReaderConfig(retry = RetryConfig(1, 0, 0))
  private def fake(edges: Vector[FakeGraphEdge] = all) = new InMemoryGraphReader(edges = edges)
  // The local reader gets the window "" for every type except COAUTHORED_WITH, as the loader does.
  private def local(edges: Vector[FakeGraphEdge] = all) = new LocalGraphReader(
    Map.empty,
    edges.map(e =>
      new LocalEdge(
        e.edgeId,
        e.from,
        e.to,
        e.edgeType,
        if (e.edgeType == "COAUTHORED_WITH") e.windowOf else "",
        () => e.properties
      )
    ),
    Map.empty
  )
  private def readers: Vector[(String, () => DirectedGraphReader)] = Vector(
    "neptune" -> (() => neptune()._2),
    "fake" -> (() => fake()),
    "local" -> (() => local())
  )
  private def page(
      r: DirectedGraphReader,
      id: String,
      direction: EdgeDirection,
      window: String = "w1",
      types: Set[String] = Set.empty,
      limit: Int = 100,
      cursor: Option[String] = None
  ) = r.directedEdges(id, window, direction, types, limit, cursor)

  for ((name, make) <- readers) {
    test(s"$name: out, in and both return the stored start and end with the hand-derived rows") {
      val r = make()
      assert(page(r, "A", EdgeDirection.Out) == Found(DirectedEdgePage(aOut, None)))
      assert(page(r, "A", EdgeDirection.In) == Found(DirectedEdgePage(aIn, None)))
      assert(page(r, "A", EdgeDirection.Both) == Found(DirectedEdgePage(aBoth, None)))
      // B: out e5, in e1.
      assert(page(r, "B", EdgeDirection.Out) == Found(DirectedEdgePage(Vector(row(e5)), None)))
      assert(page(r, "B", EdgeDirection.In) == Found(DirectedEdgePage(Vector(row(e1)), None)))
      assert(
        page(r, "B", EdgeDirection.Both) == Found(DirectedEdgePage(Vector(row(e5), row(e1)), None))
      )
      // A node with no edges is an empty page, not an error.
      assert(page(r, "Z", EdgeDirection.Both) == Found(DirectedEdgePage(Vector.empty, None)))
    }
    test(s"$name: a self-loop appears once in both and in each single direction") {
      val r = make()
      assert(
        StorageResult.value(page(r, "A", EdgeDirection.Both)).get.items.count(_.edgeId == "e3") == 1
      )
      assert(
        StorageResult.value(page(r, "A", EdgeDirection.Out)).get.items.exists(_.edgeId == "e3")
      )
      assert(StorageResult.value(page(r, "A", EdgeDirection.In)).get.items.exists(_.edgeId == "e3"))
    }
    test(s"$name: edge type filter, window constraint and allowed set are enforced") {
      val r = make()
      assert(
        page(r, "A", EdgeDirection.Out, types = Set("AUTHORED")) ==
          Found(DirectedEdgePage(Vector(row(e1)), None))
      )
      assert(
        page(r, "A", EdgeDirection.In, types = Set("AUTHORED")) ==
          Found(DirectedEdgePage(Vector.empty, None))
      )
      assert(
        page(r, "A", EdgeDirection.Both, types = Set("AUTHORED", "COAUTHORED_WITH")) ==
          Found(DirectedEdgePage(Vector(row(e1), row(e4)), None))
      )
      // Window applies to COAUTHORED_WITH only.
      assert(
        page(r, "A", EdgeDirection.Out, window = "w2") ==
          Found(DirectedEdgePage(Vector(row(e1), row(e3)), None))
      )
      assert(
        page(r, "A", EdgeDirection.Out, types = Set("NOT_ALLOWED")) == Rejected("invalid-bound")
      )
    }
    test(s"$name: limit bounds are enforced and paging walks every row once") {
      val r = make()
      assert(page(r, "A", EdgeDirection.Out, limit = 0) == Rejected("invalid-bound"))
      assert(page(r, "A", EdgeDirection.Out, limit = 101) == Rejected("invalid-bound"))
      // out, limit 2: [e1, e3] then [e4].
      val out1 = StorageResult.value(page(r, "A", EdgeDirection.Out, limit = 2)).get
      assert(out1 == DirectedEdgePage(Vector(row(e1), row(e3)), Some("2")))
      assert(
        page(r, "A", EdgeDirection.Out, limit = 2, cursor = out1.cursor) ==
          Found(DirectedEdgePage(Vector(row(e4)), None))
      )
      // both, limit 2: outgoing exhausts mid page, then incoming fills the next.
      val both1 = StorageResult.value(page(r, "A", EdgeDirection.Both, limit = 2)).get
      assert(both1 == DirectedEdgePage(Vector(row(e1), row(e3)), Some("o:2")))
      assert(
        page(r, "A", EdgeDirection.Both, limit = 2, cursor = both1.cursor) ==
          Found(DirectedEdgePage(Vector(row(e4), row(e2)), None))
      )
      // both, limit 3: outgoing fills the page exactly; incoming continues from "i:0".
      val both3 = StorageResult.value(page(r, "A", EdgeDirection.Both, limit = 3)).get
      assert(both3 == DirectedEdgePage(Vector(row(e1), row(e3), row(e4)), Some("i:0")))
      assert(
        page(r, "A", EdgeDirection.Both, limit = 3, cursor = both3.cursor) ==
          Found(DirectedEdgePage(Vector(row(e2)), None))
      )
      // both, limit 4 returns everything with no cursor.
      assert(
        page(r, "A", EdgeDirection.Both, limit = 4) == Found(DirectedEdgePage(aBoth, None))
      )
      // Malformed or foreign cursors are refused.
      for (c <- Vector("-1", "x", "o:1", "10001", "i:-3", "2.5"))
        assert(page(r, "A", EdgeDirection.Out, cursor = Some(c)) == Rejected("invalid-bound"), c)
      for (c <- Vector("2", "o:-1", "z:1", "o:", "i:10001"))
        assert(page(r, "A", EdgeDirection.Both, cursor = Some(c)) == Rejected("invalid-bound"), c)
    }
    test(s"$name: provenance properties are mapped and absent provenance is never invented") {
      val r = make()
      val rows = StorageResult
        .value(page(r, "A", EdgeDirection.Both))
        .get
        .items
        .map(e => e.edgeId -> e)
        .toMap
      assert(rows("e1").properties("provenanceJson") == provenanceJson)
      assert(rows("e1").provenance == Right(provenance))
      assert(rows("e4").properties("evidenceTable") == "support")
      assert(rows("e4").properties("evidenceEdgeId") == "e4")
      assert(rows("e4").provenance == Left("edge-provenance-absent"))
      assert(
        DirectedGraphEdge(
          "A",
          "B",
          "x",
          "AUTHORED",
          Map("provenanceJson" -> "{not json")
        ).provenance == Left("malformed-edge-provenance")
      )
    }
  }

  test("the fake, local and Neptune mapping agree on every node, direction, window and type set") {
    val (_, neptuneReader) = neptune()
    val fakeReader = fake()
    val localReader = local()
    for {
      id <- Vector("A", "B", "C", "Z")
      direction <- EdgeDirection.values.toVector
      window <- Vector("w1", "w2")
      types <- Vector(Set.empty[String], Set("AUTHORED"), Set("COAUTHORED_WITH", "HAS_TOPIC"))
      limit <- Vector(1, 2, 3, 100)
    } {
      var cursor = Option.empty[String]
      var n = 0
      val collected = Vector.newBuilder[DirectedGraphEdge]
      var done = false
      while (!done) {
        val a = page(neptuneReader, id, direction, window, types, limit, cursor)
        val b = page(fakeReader, id, direction, window, types, limit, cursor)
        assert(a == b, s"$id $direction $window $types $limit $cursor")
        assert(
          page(localReader, id, direction, window, types, limit, cursor) == a,
          s"local: $id $direction $window $types $limit $cursor"
        )
        val got = StorageResult.value(a).get
        collected ++= got.items
        cursor = got.cursor
        n += 1
        done = cursor.isEmpty || n > 10
      }
      assert(cursor.isEmpty)
      assert(collected.result().map(_.edgeId).distinct.size == collected.result().size)
    }
  }

  test("query text is parameterized and carries no user value") {
    val hostile = "x' OR 1=1 //\"; MATCH (n) DETACH DELETE n"
    val (engine, reader) = neptune()
    for (direction <- EdgeDirection.values)
      page(reader, hostile, direction, window = "w'1", types = Set("AUTHORED"))
    assert(engine.requests.nonEmpty)
    engine.requests.foreach { (query, params) =>
      assert(query.startsWith("USING QUERY:TIMEOUTMILLISECONDS 5000 MATCH "))
      assert(!query.contains(hostile) && !query.contains("w'1") && !query.contains("AUTHORED'"))
      Vector("$id", "$types", "$window", "$offset", "$limit").foreach(p =>
        assert(query.contains(p))
      )
      assert(!query.contains("DELETE") && !query.contains("MERGE") && !query.contains("CREATE"))
      assert(params("id").str == hostile)
      assert(params("window").str == "w'1")
      assert(params("types").arr.map(_.str).toVector == Vector("AUTHORED"))
    }
    val queries = engine.requests.map(_._1).toVector
    // out uses the forward pattern, in the reverse one; both runs the out query then the in query
    // without self-loops, so the loop edge is not returned twice.
    assert(queries.count(_.contains("MATCH (a)-[r]->(b)")) == 2)
    assert(queries.count(_.contains("MATCH (b)-[r]->(a) WHERE id(a) = $id AND type(r)")) == 1)
    assert(queries.count(_.contains("id(b) <> id(a)")) == 1)
    assert(
      queries.forall(_.contains("LIMIT $limit")) && queries.forall(_.contains("ORDER BY edgeId"))
    )
  }

  test("each page asks Neptune for at most one row beyond the bounded limit") {
    val (engine, reader) = neptune()
    page(reader, "A", EdgeDirection.Both, limit = 3)
    val limits = engine.requests.map(_._2("limit").num.toInt).toVector
    // Outgoing page fetch is limit+1 = 4 rows, then 1 row to learn whether incoming continues.
    assert(limits == Vector(4, 1))
    assert(limits.forall(_ <= GraphReaderConfig().maxLimit + 1))
  }

  test("a response whose endpoints do not touch the requested node is refused") {
    val wrong = Vector(FakeGraphEdge("X", "Y", "e9", "AUTHORED", "w1"))
    // The engine answers by filter, so craft a client that ignores the node filter.
    val client: NeptunedataClient = Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
            val e = wrong.head
            val document = Document.fromMap(
              Map(
                "fromId" -> Document.fromString(e.from),
                "toId" -> Document.fromString(e.to),
                "edgeId" -> Document.fromString(e.edgeId),
                "edgeType" -> Document.fromString(e.edgeType),
                "properties" -> Document.fromMap(Map.empty[String, Document].asJava)
              ).asJava
            )
            ExecuteOpenCypherQueryResponse
              .builder()
              .results(Document.fromList(Vector(document).asJava))
              .build()
          }
        }
      )
      .asInstanceOf[NeptunedataClient]
    val reader = new NeptuneGraphReader(client, noRetry)
    for (direction <- EdgeDirection.values)
      assert(page(reader, "A", direction) == Rejected("malformed-graph-response"))
  }

  test("a response above the requested bound is refused") {
    val client: NeptunedataClient = Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
            val document = Document.fromMap(
              Map(
                "fromId" -> Document.fromString("A"),
                "toId" -> Document.fromString("B"),
                "edgeId" -> Document.fromString("e1"),
                "edgeType" -> Document.fromString("AUTHORED"),
                "properties" -> Document.fromNull()
              ).asJava
            )
            ExecuteOpenCypherQueryResponse
              .builder()
              .results(Document.fromList(Vector.fill(5)(document).asJava))
              .build()
          }
        }
      )
      .asInstanceOf[NeptunedataClient]
    val reader = new NeptuneGraphReader(client, noRetry)
    assert(page(reader, "A", EdgeDirection.Out, limit = 2) == Rejected("graph-response-limit"))
  }

  test("direction wire names round trip") {
    assert(EdgeDirection.values.toVector.map(_.wire) == Vector("out", "in", "both"))
    EdgeDirection.values.foreach(d => assert(EdgeDirection.fromWire(d.wire).contains(d)))
    assert(EdgeDirection.fromWire("sideways").isEmpty)
  }

  // ---- connect ----------------------------------------------------------------------------

  private final class CountingCredentials extends AwsCredentialsProvider {
    val resolved = new AtomicInteger(0)
    def resolveCredentials(): AwsCredentials = {
      resolved.incrementAndGet(); AwsBasicCredentials.create("AKIDSTATICDUMMY", "dummy-secret")
    }
  }
  private val endpoint = URI.create("https://neptune.synthetic.invalid:8182")

  test("connect builds offline with static dummy credentials, resolves nothing and closes") {
    val counting = new CountingCredentials
    val reader =
      NeptuneGraphReader.connect(endpoint, "us-east-2", counting, GraphReaderConfig())
    assert(reader.isRight)
    val r = reader.toOption.get
    assert(r.isInstanceOf[AutoCloseable] && r.isInstanceOf[DirectedGraphReader])
    // No query was issued, so no credential was requested and nothing touched the network.
    assert(counting.resolved.get == 0)
    r.close(); r.close()
    assert(counting.resolved.get == 0)
    val static = StaticCredentialsProvider.create(AwsBasicCredentials.create("AKIDDUMMY", "dummy"))
    val second = NeptuneGraphReader.connect(endpoint, "us-east-2", static, GraphReaderConfig())
    assert(second.isRight)
    second.toOption.get.close()
  }

  test("connect refuses non-https, missing port, extras, bad region and missing credentials") {
    val creds = new CountingCredentials
    def connect(u: String, region: String = "us-east-2") =
      NeptuneGraphReader.connect(URI.create(u), region, creds, GraphReaderConfig())
    val bad = NeptuneGraphReader.invalidEndpoint
    assert(connect("http://neptune.synthetic.invalid:8182").left.toOption.contains(bad))
    assert(connect("https://neptune.synthetic.invalid").left.toOption.contains(bad))
    assert(connect("https://:8182").left.toOption.contains(bad))
    assert(connect("neptune.synthetic.invalid:8182").left.toOption.contains(bad))
    assert(connect("https://user:pw@neptune.synthetic.invalid:8182").left.toOption.contains(bad))
    assert(connect("https://neptune.synthetic.invalid:8182/gremlin").left.toOption.contains(bad))
    assert(connect("https://neptune.synthetic.invalid:8182?x=1").left.toOption.contains(bad))
    assert(connect("https://neptune.synthetic.invalid:8182#f").left.toOption.contains(bad))
    assert(connect("ftp://neptune.synthetic.invalid:8182").left.toOption.contains(bad))
    assert(
      NeptuneGraphReader
        .connect(null, "us-east-2", creds, GraphReaderConfig())
        .left
        .toOption
        .contains(bad)
    )
    assert(connect("https://neptune.synthetic.invalid:8182/").isRight)
    for (region <- Vector("", "US-EAST-2", "us_east_2", "mars", "us-east-2; drop"))
      assert(
        connect("https://neptune.synthetic.invalid:8182", region).left.toOption
          .contains(NeptuneGraphReader.invalidRegion),
        region
      )
    assert(
      NeptuneGraphReader
        .connect(endpoint, "us-east-2", null, GraphReaderConfig())
        .left
        .toOption
        .contains("missing-credentials")
    )
    assert(creds.resolved.get == 0)
  }

  test("an owning reader closes its client exactly once and an injected one never does") {
    val closes = new AtomicInteger(0)
    val client: NeptunedataClient = Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
            assert(method.getName == "close"); closes.incrementAndGet(); null
          }
        }
      )
      .asInstanceOf[NeptunedataClient]
    new NeptuneGraphReader(client, noRetry).close()
    assert(closes.get == 0)
    val owning = NeptuneGraphReader.owning(client, noRetry)
    owning.close(); owning.close()
    assert(closes.get == 1)
  }

  test("a reader from connect keeps the existing read-only bounds and query timeout") {
    val reader = NeptuneGraphReader
      .connect(endpoint, "us-east-2", new CountingCredentials, GraphReaderConfig(maxLimit = 5))
      .toOption
      .get
    try {
      // Rejected before any SDK call, so no network is attempted.
      assert(page(reader, "A", EdgeDirection.Out, limit = 6) == Rejected("invalid-bound"))
      assert(page(reader, "A", EdgeDirection.Out, types = Set("X")) == Rejected("invalid-bound"))
      assert(reader.shortestPaths("A", "B", 99, "w1", 1) == Rejected("invalid-bound"))
    } finally reader.close()
  }
}
