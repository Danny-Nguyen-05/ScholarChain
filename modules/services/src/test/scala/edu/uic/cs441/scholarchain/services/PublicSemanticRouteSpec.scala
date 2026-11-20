package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.InMemoryQuerySessionStore
import java.io.{ByteArrayOutputStream, PrintStream}
import java.net.URI
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong}
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

/** P40 acceptance (1)-(5) and (7) for `POST /v1/semantic/retrieve` on query-api. Every expected
  * value below is derived by hand from the accepted defaults: topK 1..20, question at most 1,000
  * code points, body at most 8,192 bytes, at most 16 filters, 50 requests/s with a burst of 100.
  * All keys and tokens are synthetic placeholders.
  */
class PublicSemanticRouteSpec extends AnyFunSuite {
  private val apiKey = "synthetic-p40-public-key"
  private val internalToken = "synthetic-p40-internal-token"
  private val auth = Map("Authorization" -> s"Bearer $apiKey")
  private val config = ServiceConfig(Auth.sha256(apiKey), Auth.sha256(internalToken))
  private val path = "/v1/semantic/retrieve"
  private val sentinel = "SENTINEL-P40-QUESTION-7f3a91c2"

  private val modelJson =
    ujson.Obj("modelId" -> "synthetic-model", "version" -> "v1", "dimension" -> 8)
  private def internalReply: ujson.Value = ujson.Obj(
    "hits" -> ujson.Arr(
      ujson.Obj(
        "key" -> "doc-1",
        "distance" -> 0.25,
        "metadata" -> ujson.Obj("kind" -> "synthetic")
      )
    ),
    "model" -> modelJson
  )

  /** Records every forwarded body; answers with the scripted result. */
  private final class RecordingSemantic(
      @volatile var answer: Either[ApiError, ujson.Value] = Right(ujson.Null),
      @volatile var delayMs: Long = 0
  ) extends SemanticEndpoints {
    val bodies = new ConcurrentLinkedQueue[String]()
    def retrieve(body: String, context: RequestContext): Either[ApiError, ApiReply] = {
      bodies.add(body)
      if (delayMs > 0) Thread.sleep(delayMs)
      answer.map(v => ApiReply(200, if (v.isNull) internalReply else v))
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
  private final class Fixture(
      val clock: AtomicLong = new AtomicLong(0),
      settings: RateLimitSettings = RateLimitSettings(),
      val semantic: RecordingSemantic = new RecordingSemantic
  ) {
    val logs = new ConcurrentLinkedQueue[String]()
    val limiter = new TokenBucketRateLimiter(settings, clock.get)
    val app = new ApiApplication(
      queries(),
      config,
      () => true,
      s => { logs.add(s); () },
      "query-api",
      Some(extended(semantic)),
      new PublicSemanticRoute(PublicSemanticLimits(), limiter)
    )
    def post(body: String, headers: Map[String, String] = auth): HttpReply =
      app.handle("POST", path, headers, body)
    def metrics: String = app.handle("GET", "/metrics", auth, "").body
  }
  private def json(reply: HttpReply): ujson.Value = ujson.read(reply.body)
  private def errorCode(reply: HttpReply): String = json(reply)("error").str
  private def body(question: String, extra: (String, ujson.Value)*): String =
    ujson.Obj.from(Vector("question" -> ujson.Str(question)) ++ extra).render()

  test("(1) the public API key is required: 401 in the ApiError shape, no downstream call") {
    val f = new Fixture
    val refusals = Vector(
      f.post(body("synthetic question"), Map.empty),
      f.post(body("synthetic question"), Map("Authorization" -> "Bearer wrong-synthetic-key")),
      f.post(body("synthetic question"), Map("Authorization" -> apiKey)),
      // The internal token is a separate domain and is not accepted on the public route.
      f.post(body("synthetic question"), Map("Authorization" -> s"Bearer $internalToken"))
    )
    refusals.foreach { r =>
      assert(r.status == 401)
      assert(json(r).obj.keySet == Set("error", "message", "traceId", "retryable"))
      assert(errorCode(r) == "UNAUTHORIZED" && !json(r)("retryable").bool)
    }
    assert(f.semantic.bodies.isEmpty)
    // The public key still does not open the internal route.
    val internal =
      f.app.handle("POST", "/internal/v1/semantic/retrieve", auth, body("synthetic question"))
    assert(internal.status == 401)
    assert(f.post(body("synthetic question")).status == 200)
  }

  test("(1) authentication runs before the rate limiter, so refused keys spend no tokens") {
    val f = new Fixture(settings = RateLimitSettings(requestsPerSecond = 1, burst = 1))
    (1 to 5).foreach(_ => assert(f.post(body("q"), Map.empty).status == 401))
    assert(f.post(body("q")).status == 200)
    assert(f.post(body("q")).status == 429)
  }

  test("(5) the reply holds exactly hits[key, distance, metadata] and model, nothing more") {
    val wide = ujson.Obj(
      "hits" -> ujson.Arr(
        ujson.Obj(
          "key" -> "doc-1",
          "distance" -> 0.5,
          "metadata" -> ujson.Obj("kind" -> "synthetic"),
          "vector" -> ujson.Arr(1, 2, 3),
          "text" -> "extra"
        )
      ),
      "model" -> ujson.Obj(
        "modelId" -> "synthetic-model",
        "version" -> "v1",
        "dimension" -> 8,
        "extra" -> "dropped"
      ),
      "debug" -> "dropped",
      "question" -> "dropped"
    )
    val f = new Fixture(semantic = new RecordingSemantic(Right(wide)))
    val r = f.post(body("synthetic question"))
    assert(r.status == 200)
    val out = json(r)
    assert(out.obj.keySet == Set("hits", "model"))
    assert(out("hits").arr.size == 1)
    assert(out("hits")(0).obj.keySet == Set("key", "distance", "metadata"))
    assert(out("hits")(0)("key").str == "doc-1" && out("hits")(0)("distance").num == 0.5)
    assert(out("hits")(0)("metadata").obj.keySet == Set("kind"))
    assert(out("model") == modelJson)
    assert(r.headers.keySet == Set("Content-Type", "X-Request-Id", "X-Trace-Id", "Cache-Control"))
  }

  test("a malformed downstream body is a 502, never forwarded") {
    val f = new Fixture(semantic = new RecordingSemantic(Right(ujson.Obj("unexpected" -> 1))))
    val r = f.post(body("synthetic question"))
    assert(r.status == 502 && errorCode(r) == "DOWNSTREAM_FAILURE")
  }

  test("the forwarded body is canonical; an omitted topK forwards the public maximum 20") {
    val f = new Fixture
    assert(f.post(body("synthetic question")).status == 200)
    assert(
      f.post(
        body("synthetic question", "topK" -> ujson.Num(3), "filters" -> ujson.Obj("a" -> "b"))
      ).status == 200
    )
    val sent = f.semantic.bodies.asScala.toVector.map(ujson.read(_))
    assert(sent(0) == ujson.Obj("question" -> "synthetic question", "topK" -> 20))
    assert(
      sent(1) == ujson.Obj(
        "question" -> "synthetic question",
        "topK" -> 3,
        "filters" -> ujson.Obj("a" -> "b")
      )
    )
  }

  test("(2) topK boundary: 1 and 20 accepted, 0, 21, 2.5 and non-numbers refused with 400") {
    val f = new Fixture
    Vector(1, 20).foreach(k => assert(f.post(body("q", "topK" -> ujson.Num(k))).status == 200))
    Vector[ujson.Value](ujson.Num(0), ujson.Num(21), ujson.Num(2.5), ujson.Str("5"), ujson.Null)
      .foreach { k =>
        val r = f.post(body("q", "topK" -> k))
        assert(r.status == 400 && errorCode(r) == "INVALID_REQUEST", k.render())
        assert(!json(r)("retryable").bool)
      }
    assert(f.semantic.bodies.size == 2, "refused requests make no downstream call")
  }

  test("(2) question boundary: 1,000 code points accepted, 1,001 refused; blank refused") {
    val f = new Fixture
    assert(f.post(body("q" * 1000)).status == 200)
    assert(f.post(body("q" * 1001)).status == 400)
    // 1,000 supplementary characters are 2,000 UTF-16 units and 4,000 UTF-8 bytes: accepted.
    val emoji = new String(Character.toChars(0x1f600)) * 1000
    assert(emoji.length == 2000 && f.post(body(emoji)).status == 200)
    assert(f.post(body(emoji + new String(Character.toChars(0x1f600)))).status == 400)
    Vector(body(""), body("   "), "{}", """{"question":null}""", """{"question":5}""", "not json")
      .foreach(b => assert(f.post(b).status == 400, b))
    assert(f.post(body("q", "extra" -> ujson.Str("x"))).status == 400)
    assert(f.semantic.bodies.size == 2)
  }

  test("(2) body boundary: exactly 8,192 bytes accepted, 8,193 refused") {
    val f = new Fixture
    val core = body("synthetic question")
    val exact = " " * (8192 - core.length) + core
    assert(exact.getBytes("UTF-8").length == 8192)
    assert(f.post(exact).status == 200)
    val over = " " + exact
    assert(over.getBytes("UTF-8").length == 8193)
    val r = f.post(over)
    assert(r.status == 400 && errorCode(r) == "INVALID_REQUEST")
    assert(f.semantic.bodies.size == 1)
  }

  test("(2) filters: 16 accepted, 17 refused; the internal filter shape is required") {
    val f = new Fixture
    def filters(n: Int) = ujson.Obj.from((1 to n).map(i => s"field$i" -> ujson.Str(s"v$i")))
    assert(f.post(body("q", "filters" -> filters(16))).status == 200)
    assert(f.post(body("q", "filters" -> filters(17))).status == 400)
    Vector[ujson.Value](
      ujson.Obj("" -> "v"),
      ujson.Obj("k" -> 1),
      ujson.Obj("k" -> ujson.Null),
      ujson.Arr("k"),
      ujson.Str("k=v"),
      ujson.Obj("k" -> "v" * 1001)
    ).foreach(bad => assert(f.post(body("q", "filters" -> bad)).status == 400, bad.render()))
    assert(f.post(body("q", "filters" -> ujson.Obj("k" -> "v" * 1000))).status == 200)
    assert(f.semantic.bodies.size == 2)
  }

  test("a query string on the public route is refused") {
    val f = new Fixture
    assert(f.app.handle("POST", path + "?topK=3", auth, body("q")).status == 400)
    assert(f.semantic.bodies.isEmpty)
  }

  test("(3) burst 100 then 429 RATE_LIMITED retryable with Retry-After; refill at 50/s") {
    val f = new Fixture
    (1 to 100).foreach(i => assert(f.post(body("q")).status == 200, s"request $i"))
    val limited = f.post(body("q"))
    assert(limited.status == 429)
    assert(json(limited).obj.keySet == Set("error", "message", "traceId", "retryable"))
    assert(errorCode(limited) == "RATE_LIMITED" && json(limited)("retryable").bool)
    assert(limited.headers.get("Retry-After").contains("1"))
    assert(f.semantic.bodies.size == 100, "a limited request makes no downstream call")
    // 50 tokens per second: one token every 20 ms.
    f.clock.addAndGet(19999999L)
    assert(f.post(body("q")).status == 429)
    f.clock.addAndGet(1L)
    assert(f.post(body("q")).status == 200)
    assert(f.post(body("q")).status == 429)
    // One full second refills exactly 50.
    f.clock.addAndGet(1000000000L)
    (1 to 50).foreach(i => assert(f.post(body("q")).status == 200, s"refill $i"))
    assert(f.post(body("q")).status == 429)
    // A long idle period refills to the burst, never above it.
    f.clock.addAndGet(3600L * 1000000000L)
    (1 to 100).foreach(_ => assert(f.post(body("q")).status == 200))
    assert(f.post(body("q")).status == 429)
    // The limit is checked before validation, so an invalid body over the limit is also 429.
    assert(f.post("not json").status == 429)
    val m = f.metrics
    // Hand count of 429s: the 101st, at +19.999999 ms, after the +1 ns token, after the 1 s
    // refill, after the idle refill, and the invalid body: six.
    assert(m.contains("api_rate_limited_total 6\n"))
    assert(
      m.contains("api_route_requests_total{route=\"/v1/semantic/retrieve\",status=\"200\"} 251")
    )
    assert(m.contains("api_route_requests_total{route=\"/v1/semantic/retrieve\",status=\"429\"} 6"))
  }

  test("(3) buckets are per key hash, independent, and bounded in number") {
    val clock = new AtomicLong(0)
    val limiter =
      new TokenBucketRateLimiter(RateLimitSettings(50, 100, maxKeys = 2), () => clock.get)
    val a = Auth.sha256("synthetic-key-a")
    val b = Auth.sha256("synthetic-key-b")
    (1 to 100).foreach(_ => assert(limiter.acquire(a) == RateDecision.Allowed))
    assert(limiter.acquire(a) == RateDecision.Limited(1))
    (1 to 100).foreach(_ => assert(limiter.acquire(b) == RateDecision.Allowed))
    assert(limiter.acquire(b) == RateDecision.Limited(1))
    // A third key evicts the least recently used bucket (a); the count stays at the bound.
    assert(limiter.acquire(Auth.sha256("synthetic-key-c")) == RateDecision.Allowed)
    assert(limiter.bucketCount == 2)
    assert(limiter.acquire(b) == RateDecision.Limited(1))
  }

  test("(3) a refilled bucket is dropped before a busy one when the bound is reached") {
    val clock = new AtomicLong(0)
    val limiter =
      new TokenBucketRateLimiter(RateLimitSettings(1, 1, maxKeys = 2), () => clock.get)
    val busy = Auth.sha256("synthetic-busy")
    val idle = Auth.sha256("synthetic-idle")
    assert(limiter.acquire(idle) == RateDecision.Allowed)
    clock.set(1000000000L) // idle has refilled to its burst of 1
    assert(limiter.acquire(busy) == RateDecision.Allowed)
    assert(limiter.acquire(idle) == RateDecision.Allowed) // idle is now most recently used
    clock.set(1500000000L) // busy is half refilled, idle is empty
    assert(limiter.acquire(Auth.sha256("synthetic-new")) == RateDecision.Allowed)
    // Neither bucket was full, so the least recently used (busy) was evicted.
    assert(limiter.bucketCount == 2)
    assert(limiter.acquire(idle) == RateDecision.Limited(1))
  }

  test("(3) the route keys buckets by the key hash and never holds the raw key") {
    val f = new Fixture(settings = RateLimitSettings(1, 1))
    assert(f.post(body("q")).status == 200)
    assert(f.limiter.heldKeys == Set(Auth.sha256(apiKey)))
    assert(!f.limiter.heldKeys.exists(_.contains(apiKey)))
  }

  /** A real semantic-service listener (internal-token authenticated) behind the query-api route. */
  private def withRemote(semantic: RecordingSemantic, downstreamTimeoutMs: Long = 5000)(
      test: Fixture => ApiApplication => Unit
  ): Unit = {
    val remoteConfig = config.copy(breakerFailureThreshold = 100)
    val serviceLogs = new ConcurrentLinkedQueue[String]()
    val server = ApiServer.start(
      new ApiApplication(
        queries(remoteConfig),
        remoteConfig,
        () => true,
        s => { serviceLogs.add(s); () },
        "semantic-service",
        Some(extended(semantic))
      )
    )
    val clientConfig = remoteConfig.copy(downstreamTimeoutMs = downstreamTimeoutMs)
    val metrics = new ServiceMetrics
    val remote = new RemoteSemanticApi(
      new RemoteService(
        URI.create(s"http://127.0.0.1:${server.port}"),
        internalToken,
        clientConfig,
        metrics,
        "semantic"
      )
    )
    val logs = new ConcurrentLinkedQueue[String]()
    val app = new ApiApplication(
      new QueryService(
        new InMemoryQuerySessionStore,
        (_, _, _) => Left(ApiError.unavailable),
        clientConfig,
        metrics
      ),
      clientConfig,
      () => true,
      s => { logs.add(s); () },
      "query-api",
      Some(extended(remote))
    )
    try test(new Fixture(semantic = semantic))(app)
    finally {
      app.close(); server.close()
      (logs.asScala ++ serviceLogs.asScala).foreach(l => assert(!l.contains(sentinel)))
    }
  }

  test("(1) forwards through RemoteSemanticApi with the internal token to the internal route") {
    val semantic = new RecordingSemantic
    withRemote(semantic) { _ => app =>
      val r = app.handle("POST", path, auth, body("synthetic question", "topK" -> ujson.Num(4)))
      assert(r.status == 200, r.body)
      assert(ujson.read(r.body).obj.keySet == Set("hits", "model"))
      // The semantic-service listener only routes /internal/v1/semantic/retrieve with the internal
      // token, so a 200 proves the internal route and token were used.
      assert(
        semantic.bodies.asScala.toVector.map(ujson.read(_)) ==
          Vector(ujson.Obj("question" -> "synthetic question", "topK" -> 4))
      )
    }
  }

  test("(4) downstream unavailable is 503 and downstream timeout is 504, typed and retryable") {
    val semantic = new RecordingSemantic(Left(ApiError.unavailable))
    withRemote(semantic, downstreamTimeoutMs = 400) { _ => app =>
      val unavailable = app.handle("POST", path, auth, body("q"))
      assert(unavailable.status == 503)
      assert(ujson.read(unavailable.body)("error").str == "SERVICE_UNAVAILABLE")
      assert(ujson.read(unavailable.body)("retryable").bool)
      semantic.answer = Left(ApiError.timeout)
      val timedOut = app.handle("POST", path, auth, body("q"))
      assert(
        timedOut.status == 504 && ujson.read(timedOut.body)("error").str == "DOWNSTREAM_TIMEOUT"
      )
      assert(ujson.read(timedOut.body)("retryable").bool)
      // A downstream that does not answer within the transport timeout is also a 504.
      semantic.answer = Right(ujson.Null); semantic.delayMs = 1500
      val slow = app.handle("POST", path, auth, body("q"))
      assert(slow.status == 504 && ujson.read(slow.body)("error").str == "DOWNSTREAM_TIMEOUT")
      assert(ujson.read(slow.body).obj.keySet == Set("error", "message", "traceId", "retryable"))
    }
  }

  test("(7) the question never reaches logs, stdout, stderr or metrics on any outcome") {
    val semantic = new RecordingSemantic
    val out = new ByteArrayOutputStream
    val (oldOut, oldErr) = (System.out, System.err)
    val capture = new PrintStream(out, true, "UTF-8")
    System.setOut(capture); System.setErr(capture)
    try
      Console.withOut(capture) {
        Console.withErr(capture) {
          withRemote(semantic) { _ => app =>
            assert(app.handle("POST", path, auth, body(sentinel)).status == 200)
            assert(app.handle("POST", path, auth, body(sentinel + "x" * 1000)).status == 400)
            assert(app.handle("POST", path, Map.empty, body(sentinel)).status == 401)
            semantic.answer = Left(ApiError.unavailable)
            assert(app.handle("POST", path, auth, body(sentinel)).status == 503)
            assert(!app.handle("GET", "/metrics", auth, "").body.contains(sentinel))
          }
          val f = new Fixture(settings = RateLimitSettings(1, 1))
          assert(f.post(body(sentinel)).status == 200)
          assert(f.post(body(sentinel)).status == 429)
          assert(!f.metrics.contains(sentinel))
          assert(f.logs.size == 3 && f.logs.asScala.forall(!_.contains(sentinel)))
          assert(f.logs.asScala.exists(_.contains("\"route\":\"/v1/semantic/retrieve\"")))
        }
      }
    finally { System.setOut(oldOut); System.setErr(oldErr) }
    assert(!out.toString("UTF-8").contains(sentinel))
    assert(semantic.bodies.asScala.exists(_.contains(sentinel)), "the sentinel was forwarded")
  }

  test("the route is served only by query-api and only when the extended API is composed") {
    val counter = new AtomicInteger
    val semantic = new SemanticEndpoints {
      def retrieve(body: String, c: RequestContext) = {
        counter.incrementAndGet(); Left(ApiError.unavailable)
      }
      def close(): Unit = ()
    }
    Vector("graph-service", "semantic-service").foreach { role =>
      val app =
        new ApiApplication(queries(), config, () => true, _ => (), role, Some(extended(semantic)))
      assert(app.handle("POST", path, auth, body("q")).status == 404)
    }
    val unconfigured = new ApiApplication(queries(), config, () => true, _ => (), "query-api", None)
    assert(unconfigured.handle("POST", path, auth, body("q")).status == 404)
    assert(counter.get == 0)
  }

  test("public limit and rate settings refuse impossible values") {
    assertThrows[IllegalArgumentException](PublicSemanticLimits(maxTopK = 0))
    assertThrows[IllegalArgumentException](PublicSemanticLimits(defaultTopK = 21))
    assertThrows[IllegalArgumentException](RateLimitSettings(0, 100))
    assertThrows[IllegalArgumentException](RateLimitSettings(50, 0))
    assertThrows[IllegalArgumentException](RateLimitSettings(50, 100, 0))
    assert(PublicSemanticLimits() == PublicSemanticLimits(20, 20, 1000, 8192, 16))
    assert(RateLimitSettings() == RateLimitSettings(50, 100, 1024))
  }
}
