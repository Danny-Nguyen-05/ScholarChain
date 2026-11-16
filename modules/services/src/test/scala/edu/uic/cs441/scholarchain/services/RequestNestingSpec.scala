package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.InMemoryQuerySessionStore
import java.io.{ByteArrayOutputStream, PrintStream}
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicReference
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

/** P40-S repair 1: request bodies are depth-bounded on the raw text before any ujson parse, so deep
  * JSON is a typed 400 `INVALID_REQUEST` on `/v1/semantic/retrieve`, `/v1/query` and the internal
  * semantic route, with nothing printed. Depths are counted by hand: the root object is level 1.
  * The maximum is 32 ([[RequestJson.MaxNestingDepth]]). Keys and tokens are synthetic placeholders.
  */
class RequestNestingSpec extends AnyFunSuite {
  private val apiKey = "synthetic-nesting-public-key"
  private val internalToken = "synthetic-nesting-internal-token"
  private val auth = Map("Authorization" -> s"Bearer $apiKey")
  private val internalAuth = Map("Authorization" -> s"Bearer $internalToken")
  private val config = ServiceConfig(Auth.sha256(apiKey), Auth.sha256(internalToken))
  private val Max = RequestJson.MaxNestingDepth

  /** `n` nested arrays around 0: depth `n`. */
  private def arrays(n: Int): String = "[" * n + "0" + "]" * n

  /** `n` nested objects around 0: depth `n`. */
  private def objects(n: Int): String = "{\"a\":" * n + "0" + "}" * n

  private def model = ujson.Obj("modelId" -> "synthetic-model", "version" -> "v1", "dimension" -> 8)
  private def hits(n: Int): ujson.Value = ujson.Obj(
    "hits" -> ujson.Arr.from((1 to n).map { i =>
      ujson.Obj(
        "key" -> s"doc-$i",
        "distance" -> i / 100.0,
        "metadata" -> ujson.Obj("kind" -> "synthetic")
      )
    }),
    "model" -> model
  )

  private final class Semantic(answer: () => Either[ApiError, ujson.Value])
      extends SemanticEndpoints {
    val bodies = new ConcurrentLinkedQueue[String]()
    def retrieve(body: String, context: RequestContext): Either[ApiError, ApiReply] = {
      bodies.add(body); answer().map(ApiReply(200, _))
    }
    def close(): Unit = ()
  }
  private def queries(c: ServiceConfig = config) =
    new QueryService(new InMemoryQuerySessionStore, (_, _, _) => Left(ApiError.unavailable), c)
  private def extended(semantic: SemanticEndpoints) = ExtendedApi(
    new EvidenceApi(UnservedEvidenceStore, UnservedAuditStore),
    UnservedGraphEndpoints,
    semantic
  )
  private def app(
      semantic: SemanticEndpoints,
      role: String = "query-api",
      logs: ConcurrentLinkedQueue[String] = new ConcurrentLinkedQueue[String](),
      c: ServiceConfig = config
  ) = new ApiApplication(
    queries(c),
    c,
    () => true,
    s => { logs.add(s); () },
    role,
    Some(extended(semantic))
  )
  private def typed400(r: HttpReply, label: String): Unit = {
    assert(r.status == 400, s"$label: ${r.status} ${r.body.take(200)}")
    val json = ujson.read(r.body)
    assert(json.obj.keySet == Set("error", "message", "traceId", "retryable"), label)
    assert(json("error").str == "INVALID_REQUEST" && !json("retryable").bool, label)
    assert(
      json("traceId").str.nonEmpty && r.headers.get("X-Trace-Id").contains(json("traceId").str)
    )
  }

  /** Runs `body` with System.out/err and Console out/err captured; returns the captured text. */
  private def captured(body: => Unit): String = {
    val out = new ByteArrayOutputStream
    val stream = new PrintStream(out, true, "UTF-8")
    val (oldOut, oldErr) = (System.out, System.err)
    System.setOut(stream); System.setErr(stream)
    try Console.withOut(stream)(Console.withErr(stream)(body))
    finally { System.setOut(oldOut); System.setErr(oldErr) }
    out.toString("UTF-8")
  }
  private def assertNoTrace(text: String): Unit = {
    assert(!text.contains("StackOverflowError"), text.take(500))
    assert(!text.contains("Exception"), text.take(500))
    assert(!text.contains("\tat "), text.take(500))
  }

  test("the pre-scan admits depth 32 and refuses 33 for arrays, objects and mixed nesting") {
    assert(RequestJson.MaxNestingDepth == 32)
    assert(RequestJson.withinDepth(arrays(32)) && !RequestJson.withinDepth(arrays(33)))
    assert(RequestJson.withinDepth(objects(32)) && !RequestJson.withinDepth(objects(33)))
    val mixed32 = "[{\"a\":" * 16 + "0" + "}]" * 16
    assert(RequestJson.withinDepth(mixed32) && !RequestJson.withinDepth("[" + mixed32 + "]"))
    // Sibling containers do not add up: 1,000 flat arrays inside one array are depth 2.
    assert(RequestJson.withinDepth("[" + Vector.fill(1000)("[]").mkString(",") + "]"))
    Vector("", "{}", "0", "\"x\"", """{"question":"q","filters":{"k":"v"}}""")
      .foreach(t => assert(RequestJson.withinDepth(t), t))
  }

  test("brackets inside strings are ignored and escapes are honoured") {
    // 100 brackets inside a string value: depth 1.
    assert(RequestJson.withinDepth("{\"question\":\"" + "[{" * 100 + "\"}"))
    // An escaped quote does not end the string, so the brackets after it are still text.
    assert(RequestJson.withinDepth("{\"q\":\"\\\"" + "[" * 100 + "\"}"))
    // An escaped backslash does end before the quote: the brackets after it are structure.
    assert(!RequestJson.withinDepth("{\"q\":\"\\\\\"," + "[" * 40 + "0" + "]" * 40 + "}"))
    // " is a quote only after decoding; the raw text keeps the string open.
    assert(RequestJson.withinDepth("{\"q\":\"\\u0022" + "[" * 100 + "\"}"))
    // More closers than openers is malformed and refused.
    assert(!RequestJson.withinDepth("]" * 4096 + "[" * 4096))
  }

  test("the pre-scan refuses without recursion: 200,000 levels, which ujson cannot handle") {
    val deep = "[" * 200000 + "]" * 200000
    // JIT-independent: the scan is one loop with constant state, so no stack depth is involved.
    assert(!RequestJson.withinDepth(deep))
    // Every request-body parser refuses it typed, on the calling thread, before ujson.
    val roomy = config.copy(maxRequestBytes = 1000000)
    assert(QueryRequest.parse(deep, roomy) == Left(ApiError.invalid))
    val route = new PublicSemanticRoute(PublicSemanticLimits(maxBodyBytes = 1000000))
    assert(route.validate(deep) == Left(ApiError.invalid))
    val semantic = new SemanticApi(
      (_, _) => fail("the semantic port must not run"),
      SemanticApiConfig(maxBodyBytes = 1000000)
    )
    assert(semantic.retrieve(deep, RequestContext("r", "t")) == Left(ApiError.invalid))
    semantic.close()
    // The unguarded path overflows: reading this body and asking for an object (as every parser
    // here does) throws StackOverflowError on a 1 MiB thread stack, which NonFatal does not catch.
    val thrown = new AtomicReference[Throwable]()
    val probe: Runnable = () => {
      try { ujson.read(deep).obj; () }
      catch { case e: Throwable => thrown.set(e) }
    }
    val t = new Thread(null, probe, "nesting-probe", 1L << 20)
    t.start(); t.join()
    assert(thrown.get.isInstanceOf[StackOverflowError], String.valueOf(thrown.get))
  }

  test("public route: deep arrays, objects, question, filter and topK are typed 400s") {
    val semantic = new Semantic(() => Right(hits(1)))
    val a = app(semantic)
    def post(b: String) = a.handle("POST", PublicSemanticRoute.Path, auth, b)
    // The reported body: 8,192 bytes, inside the public limit.
    val reported = "[" * 4096 + "]" * 4096
    assert(reported.getBytes(UTF_8).length == 8192)
    // question at total depth d: root (1) + d - 1 arrays; filter value: root, filters, d - 2;
    // topK: root + d - 1.
    def question(d: Int) = "{\"question\":" + arrays(d - 1) + "}"
    def filter(d: Int) = "{\"question\":\"q\",\"filters\":{\"k\":" + arrays(d - 2) + "}}"
    def topK(d: Int) = "{\"question\":\"q\",\"topK\":" + arrays(d - 1) + "}"
    val bodies = Vector(
      "reported" -> reported,
      "arrays-3000" -> ("[" * 3000 + "]" * 3000),
      "objects-1365" -> objects(1365),
      "filter-3900" -> filter(3900),
      "topK-3900" -> topK(3900)
    ) ++ Vector(Max, Max + 1).flatMap { d =>
      Vector(
        s"arrays-$d" -> arrays(d),
        s"objects-$d" -> objects(d),
        s"question-$d" -> question(d),
        s"filter-$d" -> filter(d),
        s"topK-$d" -> topK(d)
      )
    }
    bodies.foreach { (label, b) =>
      assert(b.getBytes(UTF_8).length <= 8192, label)
      // At the maximum the pre-scan admits the body and the shape check refuses it; above the
      // maximum the pre-scan refuses it. Both are the same typed 400.
      val depth = if (label.endsWith(s"-$Max")) Some(true) else None
      depth.foreach(d => assert(RequestJson.withinDepth(b) == d, label))
      if (label.endsWith(s"-${Max + 1}")) assert(!RequestJson.withinDepth(b), label)
      typed400(post(b), label)
    }
    assert(semantic.bodies.isEmpty, "no refused body reached the semantic port")
    assert(post("""{"question":"q","filters":{"k":"v"}}""").status == 200)
  }

  test("/v1/query: deep bodies and deep constraint values are typed 400s") {
    val a = app(new Semantic(() => Right(hits(1))))
    var n = 0
    def post(b: String) = {
      n += 1; a.handle("POST", "/v1/query", auth + ("Idempotency-Key" -> s"nesting-$n"), b)
    }
    def topics(d: Int) =
      "{\"question\":\"q\",\"constraints\":{\"topics\":" + arrays(d - 2) + "}}"
    val bodies = Vector(
      "reported" -> ("[" * 4096 + "]" * 4096),
      "objects-1300" -> objects(1300),
      "topics-3900" -> topics(3900),
      s"arrays-$Max" -> arrays(Max),
      s"arrays-${Max + 1}" -> arrays(Max + 1),
      s"topics-$Max" -> topics(Max),
      s"topics-${Max + 1}" -> topics(Max + 1)
    )
    bodies.foreach((label, b) => typed400(post(b), label))
  }

  test("internal semantic route on semantic-service: deep bodies are typed 400s") {
    val calls = new java.util.concurrent.atomic.AtomicInteger
    val semantic = new SemanticApi((_, _) => { calls.incrementAndGet(); Right(hits(1)) })
    val a = app(semantic, role = "semantic-service")
    def post(b: String) = a.handle("POST", "/internal/v1/semantic/retrieve", internalAuth, b)
    Vector(
      "reported" -> ("[" * 4096 + "]" * 4096),
      s"arrays-${Max + 1}" -> arrays(Max + 1),
      "question-3900" -> ("{\"question\":" + arrays(3900) + "}"),
      "filter-3900" -> ("{\"question\":\"q\",\"filters\":{\"k\":" + arrays(3900) + "}}")
    ).foreach((label, b) => typed400(post(b), label))
    assert(calls.get == 0)
    assert(post("""{"question":"q","filters":{"k":"v"}}""").status == 200)
    assert(calls.get == 1)
  }

  test("query-api's internal route forwarding to a remote semantic-service: deep bodies are 400") {
    // query-api forwards the raw internal body through RemoteSemanticApi; the semantic-service
    // SemanticApi refuses it before parsing, and its 400 maps to INVALID_REQUEST on query-api.
    val calls = new java.util.concurrent.atomic.AtomicInteger
    val remoteConfig = config.copy(breakerFailureThreshold = 100)
    val server = ApiServer.start(
      app(
        new SemanticApi((_, _) => { calls.incrementAndGet(); Right(hits(1)) }),
        role = "semantic-service",
        c = remoteConfig
      )
    )
    val remote = new RemoteSemanticApi(
      new RemoteService(
        URI.create(s"http://127.0.0.1:${server.port}"),
        internalToken,
        remoteConfig,
        new ServiceMetrics,
        "semantic"
      )
    )
    val query = app(remote, c = remoteConfig)
    def post(b: String) = query.handle("POST", "/internal/v1/semantic/retrieve", internalAuth, b)
    try {
      Vector(
        "reported" -> ("[" * 4096 + "]" * 4096),
        s"arrays-${Max + 1}" -> arrays(Max + 1),
        "filter-3900" -> ("{\"question\":\"q\",\"filters\":{\"k\":" + arrays(3900) + "}}")
      ).foreach((label, b) => typed400(post(b), label))
      assert(calls.get == 0)
      assert(post("""{"question":"q"}""").status == 200 && calls.get == 1)
    } finally { query.close(); server.close() }
  }

  test("over HTTP on a fresh listener the reported body is a typed 400 and nothing is printed") {
    val logs = new ConcurrentLinkedQueue[String]()
    val semantic = new Semantic(() => Right(hits(1)))
    val http = HttpClient.newHttpClient()
    var replies = Vector.empty[HttpResponse[String]]
    val text = captured {
      val server = ApiServer.start(app(semantic, logs = logs))
      try {
        def send(path: String, body: String, extra: Map[String, String] = Map.empty) = {
          val builder = HttpRequest
            .newBuilder(URI.create(s"http://127.0.0.1:${server.port}$path"))
            .header("Authorization", s"Bearer $apiKey")
            .header("Content-Type", "application/json")
          extra.foreach((k, v) => builder.header(k, v))
          http.send(
            builder.POST(HttpRequest.BodyPublishers.ofString(body)).build(),
            HttpResponse.BodyHandlers.ofString()
          )
        }
        // The first request on this listener is the deep one, as in the reported run.
        replies = Vector(
          send(PublicSemanticRoute.Path, "[" * 4096 + "]" * 4096),
          send(PublicSemanticRoute.Path, objects(1365)),
          send("/v1/query", "[" * 4096 + "]" * 4096, Map("Idempotency-Key" -> "nesting-http"))
        )
      } finally server.close()
    }
    replies.foreach { r =>
      assert(r.statusCode == 400, r.body)
      val json = ujson.read(r.body)
      assert(json.obj.keySet == Set("error", "message", "traceId", "retryable"))
      assert(json("error").str == "INVALID_REQUEST")
    }
    assertNoTrace(text)
    assert(semantic.bodies.isEmpty)
    assert(logs.size == 3)
    logs.asScala.foreach { l =>
      assert(
        ujson.read(l).obj.keySet == Set(
          "event",
          "requestId",
          "traceId",
          "route",
          "status",
          "elapsedMs"
        )
      )
    }
  }

  test(
    "a residual StackOverflowError behind the route is a typed 500 with a trace ID, not printed"
  ) {
    val semantic = new Semantic(() => throw new StackOverflowError("synthetic"))
    val logs = new ConcurrentLinkedQueue[String]()
    var reply: HttpReply = null
    val text = captured {
      reply = app(semantic, logs = logs)
        .handle("POST", PublicSemanticRoute.Path, auth, """{"question":"q"}""")
    }
    assert(reply.status == 500)
    val json = ujson.read(reply.body)
    assert(json("error").str == "INTERNAL_ERROR" && json("traceId").str.nonEmpty)
    assertNoTrace(text)
    assert(logs.asScala.forall(!_.contains("synthetic")))
  }

  test("(a) the reply keeps at most the forwarded topK hits, in downstream order") {
    val count = new AtomicReference[Int](5)
    val semantic = new Semantic(() => Right(hits(count.get)))
    val a = app(semantic)
    def keys(b: String): Vector[String] = {
      val r = a.handle("POST", PublicSemanticRoute.Path, auth, b)
      assert(r.status == 200, r.body)
      ujson.read(r.body)("hits").arr.toVector.map(_("key").str)
    }
    assert(keys("""{"question":"q","topK":3}""") == Vector("doc-1", "doc-2", "doc-3"))
    assert(keys("""{"question":"q","topK":1}""") == Vector("doc-1"))
    // Fewer hits than topK are returned unchanged.
    assert(keys("""{"question":"q","topK":7}""") == (1 to 5).map(i => s"doc-$i").toVector)
    // The default topK is 20, so 25 downstream hits become the first 20.
    count.set(25)
    assert(keys("""{"question":"q"}""") == (1 to 20).map(i => s"doc-$i").toVector)
    assert(keys("""{"question":"q","topK":20}""").size == 20)
    // The projection itself truncates.
    val route = new PublicSemanticRoute()
    val projected = route.project(ApiReply(200, hits(4)), 2).toOption.get.body
    assert(projected("hits").arr.map(_("key").str).toVector == Vector("doc-1", "doc-2"))
    assert(route.validate("""{"question":"q","topK":4}""").map(_.topK) == Right(4))
    assert(route.validate("""{"question":"q"}""").map(_.topK) == Right(20))
  }
}
