package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.CachingEmbeddingClient
import edu.uic.cs441.scholarchain.storage.*
import java.io.{ByteArrayOutputStream, PrintStream}
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

/** P40 acceptance (6) and the configuration refusals: the semantic-service query client is wrapped
  * in the rag-owned cache, both in aws composition (through fake ports) and in offline-synthetic
  * mode; `/metrics` reports the cache counters; invalid sizes and rates refuse startup with a
  * closed code. No AWS, Voyage or Anthropic call is made; all keys are synthetic placeholders.
  */
class SemanticCacheWiringSpec extends AnyFunSuite {
  import AwsTestEnv.*
  private val context = RequestContext("req-cache", "trace-cache")
  private val authorization = Map("Authorization" -> s"Bearer $apiKey")
  private val internal = Map("Authorization" -> s"Bearer $internalToken")
  private val cacheVar = "SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES"
  private val rateVar = "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND"
  private val burstVar = "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST"

  /** Successful query embedder that counts every text it is asked to embed (a Voyage call). */
  private final class CountingEmbedder(val model: EmbeddingModel) extends EmbeddingClient {
    val texts = new AtomicInteger
    val calls = new AtomicInteger
    def embed(input: Seq[String]): Seq[EmbeddingResult] = {
      calls.incrementAndGet(); texts.addAndGet(input.size)
      input.map(_ => EmbeddingSuccess(Vector.fill(model.dimension)(0.5f), model, 1))
    }
  }
  private final class OneHitVectors extends VectorStore {
    def ensureIndex(name: String, dimension: Int, metric: String) = StorageResult.Rejected("unused")
    def putBatch(index: String, documents: Vector[VectorDocument]) =
      StorageResult.Rejected("unused")
    def query(index: String, vector: Vector[Float], topK: Int, filter: Map[String, String]) =
      StorageResult.Found(Vector(VectorHit("doc-1", 0.1, Map("kind" -> "synthetic"))))
    def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
      StorageResult.Found(Vector.empty)
  }

  /** The shared fake factory, except that semantic ports carry a counting successful embedder. */
  private final class CachingFactory extends AwsPortFactory {
    val base = new FakeFactory
    @volatile var embedder: Option[CountingEmbedder] = None
    @volatile var workerPorts: Option[WorkerPorts] = None
    def graph(config: GraphRoleConfig) = base.graph(config)
    def semantic(config: SemanticRoleConfig) = {
      val e = new CountingEmbedder(config.embedding); embedder = Some(e)
      Right(new SemanticPorts(e, new OneHitVectors))
    }
    def query(config: QueryRoleConfig, runtime: RuntimeConfig) = base.query(config, runtime)
    def worker(config: WorkerRoleConfig) = {
      val built = base.worker(config); workerPorts = built.toOption; built
    }
  }

  private def semanticApp(env: Map[String, String], factory: AwsPortFactory) = {
    val config = parse("semantic-service", env).toOption.get
    val comp = AwsComposition.build(service(env), config, env, factory).toOption.get
    val app = new ApiApplication(
      comp.queries,
      service(env),
      () => true,
      _ => (),
      "semantic-service",
      comp.extended
    )
    (comp, app)
  }
  private def retrieve(app: ApiApplication, question: String): HttpReply = app.handle(
    "POST",
    "/internal/v1/semantic/retrieve",
    internal,
    ujson.Obj("question" -> question, "topK" -> 3).render()
  )
  private def metricValue(metrics: String, name: String): Option[String] =
    metrics.linesIterator.collectFirst {
      case l if l.startsWith(name + " ") => l.drop(name.length + 1)
    }

  test("(6) aws semantic-service: repeated identical questions make one underlying embed call") {
    val factory = new CachingFactory
    val (comp, app) = semanticApp(semantic ++ Map(cacheVar -> "7"), factory)
    try {
      Vector("question one", "question one", "question two", "question one").foreach { q =>
        val r = retrieve(app, q)
        assert(r.status == 200, r.body)
        assert(ujson.read(r.body).obj.keySet == Set("hits", "model"))
      }
      // Hand-derived: two distinct questions, so two misses (embed calls) and two hits.
      val embedder = factory.embedder.get
      assert(embedder.texts.get == 2 && embedder.calls.get == 2)
      val m = app.handle("GET", "/metrics", authorization, "").body
      assert(metricValue(m, "embedding_cache_hits_total").contains("2"))
      assert(metricValue(m, "embedding_cache_misses_total").contains("2"))
      assert(metricValue(m, "embedding_cache_evictions_total").contains("0"))
      assert(metricValue(m, "embedding_cache_size").contains("2"))
      assert(metricValue(m, "embedding_cache_capacity").contains("7"))
      assert(!m.contains("question one") && !m.contains("question two"))
    } finally comp.close()
  }

  test("(6) the cache bound evicts least recently used entries and counts the evictions") {
    val factory = new CachingFactory
    val (comp, app) = semanticApp(semantic ++ Map(cacheVar -> "1"), factory)
    try {
      // Capacity 1: a, b, a, a -> miss, miss (evicts a), miss (evicts b), hit.
      Vector("a question", "b question", "a question", "a question")
        .foreach(q => assert(retrieve(app, q).status == 200))
      assert(factory.embedder.get.texts.get == 3)
      val m = app.handle("GET", "/metrics", authorization, "").body
      assert(metricValue(m, "embedding_cache_misses_total").contains("3"))
      assert(metricValue(m, "embedding_cache_hits_total").contains("1"))
      assert(metricValue(m, "embedding_cache_evictions_total").contains("2"))
      assert(metricValue(m, "embedding_cache_size").contains("1"))
      assert(metricValue(m, "embedding_cache_capacity").contains("1"))
    } finally comp.close()
  }

  test("(6) an unset cache size uses the decorator default of 1,024 entries") {
    val factory = new CachingFactory
    val (comp, app) = semanticApp(semantic, factory)
    try {
      val m = app.handle("GET", "/metrics", authorization, "").body
      assert(CachingEmbeddingClient.DefaultMaxEntries == 1024)
      assert(metricValue(m, "embedding_cache_capacity").contains("1024"))
      assert(metricValue(m, "embedding_cache_misses_total").contains("0"))
    } finally comp.close()
  }

  test("failed embeddings are not cached: each retry reaches the underlying client") {
    // The shared fake embedder answers EmbeddingFailure; the route answers 502 each time.
    val factory = new FakeFactory
    val (comp, app) = semanticApp(semantic, factory)
    try {
      (1 to 3).foreach(_ => assert(retrieve(app, "same failing question").status == 502))
      assert(factory.d.calls("embed") == 3)
      val m = app.handle("GET", "/metrics", authorization, "").body
      assert(metricValue(m, "embedding_cache_misses_total").contains("3"))
      assert(metricValue(m, "embedding_cache_size").contains("0"))
    } finally comp.close()
  }

  test("the vector-identity check still refuses a mismatched provider through the cache") {
    // A Voyage-named model from the port while the stored identity is Bedrock.
    val factory = new AwsPortFactory {
      val base = new FakeFactory
      def graph(c: GraphRoleConfig) = base.graph(c)
      def semantic(c: SemanticRoleConfig) = Right(
        new SemanticPorts(
          new CountingEmbedder(c.embedding.copy(modelId = "voyage-synthetic")),
          new OneHitVectors
        )
      )
      def query(c: QueryRoleConfig, r: RuntimeConfig) = base.query(c, r)
      def worker(c: WorkerRoleConfig) = base.worker(c)
    }
    val config = parse("semantic-service", semantic).toOption.get
    val refused = AwsComposition.build(service(semantic), config, semantic, factory)
    assert(refused.left.toOption.exists(_.startsWith("vector-consistency-")))
  }

  test("only semantic-service registers cache counters; worker and query roles do not") {
    val factory = new CachingFactory
    val workerComp = AwsComposition
      .build(service(worker), parse("embedding-worker", worker).toOption.get, worker, factory)
      .toOption
      .get
    try {
      assert(!workerComp.queries.metrics.render.contains("embedding_cache_"))
      // The document/ingest client is exactly the port's embedder, not a cache.
      assert(!factory.workerPorts.get.embedder.isInstanceOf[CachingEmbeddingClient])
    } finally workerComp.close()
    val graphComp = AwsComposition
      .build(service(graph), parse("graph-service", graph).toOption.get, graph, factory)
      .toOption
      .get
    try assert(!graphComp.queries.metrics.render.contains("embedding_cache_"))
    finally graphComp.close()
  }

  test("aws cache size: absent or blank is 1024; 1..100000 accepted; others refused by name") {
    def size(v: Option[String]) =
      parse("semantic-service", v.fold(semantic)(x => semantic + (cacheVar -> x)))
        .map(_.asInstanceOf[SemanticRoleConfig].embeddingCacheMaxEntries)
    assert(size(None) == Right(1024))
    assert(size(Some("  ")) == Right(1024))
    assert(size(Some("1")) == Right(1))
    assert(size(Some("100000")) == Right(100000))
    Vector("0", "-1", "100001", "abc", "1.5", "99999999999999999999").foreach { bad =>
      assert(size(Some(bad)) == Left(s"invalid-aws-configuration:$cacheVar"), bad)
    }
  }

  test("rate and offline cache settings: defaults, bounds and closed refusal codes") {
    assert(RateLimitSettings.fromEnvironment(Map.empty) == Right(RateLimitSettings(50, 100)))
    assert(
      RateLimitSettings.fromEnvironment(Map(rateVar -> "7", burstVar -> " 9 ")) ==
        Right(RateLimitSettings(7, 9))
    )
    Vector("0", "-5", "100001", "fifty", "50.0").foreach { bad =>
      assert(
        RateLimitSettings.fromEnvironment(Map(rateVar -> bad)) ==
          Left(s"invalid-service-configuration:$rateVar")
      )
    }
    Vector("0", "1000001", "x").foreach { bad =>
      assert(
        RateLimitSettings.fromEnvironment(Map(burstVar -> bad)) ==
          Left(s"invalid-service-configuration:$burstVar")
      )
    }
    assert(EmbeddingCacheSettings.fromEnvironment(Map.empty) == Right(1024))
    assert(EmbeddingCacheSettings.fromEnvironment(Map(cacheVar -> "3")) == Right(3))
    assert(
      EmbeddingCacheSettings.fromEnvironment(Map(cacheVar -> "0")) ==
        Left(s"invalid-service-configuration:$cacheVar")
    )
  }

  private val offline: Map[String, String] = Map(
    "SCHOLARCHAIN_SERVICE_MODE" -> "offline-synthetic",
    "SCHOLARCHAIN_API_KEY_SHA256" -> Auth.sha256(apiKey),
    "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> Auth.sha256(internalToken),
    "SCHOLARCHAIN_HTTP_HOST" -> "127.0.0.1",
    "SCHOLARCHAIN_HTTP_PORT" -> "0"
  )
  private def launchCapturingStderr(
      role: String,
      env: Map[String, String]
  ): (Either[Int, RunningService], String) = {
    val err = new ByteArrayOutputStream
    val old = System.err
    System.setErr(new PrintStream(err, true, "UTF-8"))
    try (ServiceBootstrap.launch(role, env, new FakeFactory), err.toString("UTF-8").trim)
    finally System.setErr(old)
  }

  test("invalid rate or cache variables refuse startup with exit 2 and only the variable name") {
    val cases = Vector(
      ("query-api", offline + (rateVar -> "0"), s"invalid-service-configuration:$rateVar"),
      ("query-api", offline + (burstVar -> "lots"), s"invalid-service-configuration:$burstVar"),
      ("query-api", offline + (cacheVar -> "0"), s"invalid-service-configuration:$cacheVar"),
      (
        "semantic-service",
        offline + (cacheVar -> "100001"),
        s"invalid-service-configuration:$cacheVar"
      ),
      (
        "semantic-service",
        semantic + (cacheVar -> "-3"),
        s"invalid-aws-configuration:$cacheVar"
      ),
      (
        "query-api",
        forRole("query-api") + (rateVar -> "x"),
        s"invalid-service-configuration:$rateVar"
      )
    )
    cases.foreach { (role, env, code) =>
      val (result, stderr) = launchCapturingStderr(role, env)
      assert(result == Left(2), code)
      assert(stderr == code)
    }
  }

  private val http = HttpClient.newHttpClient()
  private def post(port: Int, body: String, headers: Map[String, String]) = {
    val b = HttpRequest.newBuilder(URI.create(s"http://127.0.0.1:$port/v1/semantic/retrieve"))
    headers.foreach((k, v) => b.header(k, v))
    http.send(
      b.POST(HttpRequest.BodyPublishers.ofString(body)).build(),
      HttpResponse.BodyHandlers.ofString()
    )
  }

  test("(9) offline-synthetic query-api serves the route and reports cache counters") {
    val (started, _) = launchCapturingStderr("query-api", offline)
    val running = started.toOption.get
    try {
      val body = ujson.Obj("question" -> "synthetic offline question", "topK" -> 5).render()
      assert(post(running.port, body, Map.empty).statusCode == 401)
      val first = post(running.port, body, authorization)
      val second = post(running.port, body, authorization)
      Vector(first, second).foreach { r =>
        assert(r.statusCode == 200, r.body)
        val json = ujson.read(r.body)
        assert(json.obj.keySet == Set("hits", "model"))
        assert(
          json("model") ==
            ujson.Obj(
              "modelId" -> "synthetic-offline-services",
              "version" -> "v1",
              "dimension" -> 8
            )
        )
      }
      val (status, metrics) = Http.get(running.port, "/metrics", authorization)
      assert(status == 200)
      assert(metricValue(metrics, "embedding_cache_misses_total").contains("1"))
      assert(metricValue(metrics, "embedding_cache_hits_total").contains("1"))
      assert(metricValue(metrics, "embedding_cache_capacity").contains("1024"))
      assert(metricValue(metrics, "api_rate_limited_total").contains("0"))
      assert(
        metrics.contains(
          "api_route_requests_total{route=\"/v1/semantic/retrieve\",status=\"200\"} 2"
        )
      )
      assert(
        metrics.contains(
          "api_route_requests_total{route=\"/v1/semantic/retrieve\",status=\"401\"} 1"
        )
      )
    } finally running.close()
  }

  test("(3) offline-synthetic rate override: burst 2 at 1/s gives a 429 with Retry-After") {
    val (started, _) =
      launchCapturingStderr("query-api", offline ++ Map(rateVar -> "1", burstVar -> "2"))
    val running = started.toOption.get
    try {
      val body = ujson.Obj("question" -> "synthetic offline question").render()
      val replies = (1 to 5).map(_ => post(running.port, body, authorization))
      assert(replies.take(2).forall(_.statusCode == 200))
      val limited = replies.drop(2).filter(_.statusCode == 429)
      assert(limited.nonEmpty, "five back-to-back requests exceed a burst of two at 1/s")
      limited.foreach { r =>
        assert(ujson.read(r.body)("error").str == "RATE_LIMITED")
        assert(ujson.read(r.body)("retryable").bool)
        assert(r.headers.firstValue("Retry-After").orElse("") == "1")
      }
      val (_, metrics) = Http.get(running.port, "/metrics", authorization)
      assert(metricValue(metrics, "api_rate_limited_total").contains(limited.size.toString))
    } finally running.close()
  }

  test("offline query-api with remote services registers no local cache counters") {
    val semanticServer = {
      val config = service(offline)
      val queries =
        new QueryService(
          new InMemoryQuerySessionStore,
          (_, _, _) => Left(ApiError.unavailable),
          config
        )
      ApiServer.start(new ApiApplication(queries, config, () => true, _ => (), "semantic-service"))
    }
    val base = s"http://127.0.0.1:${semanticServer.port}"
    val (started, _) = launchCapturingStderr(
      "query-api",
      offline ++ Map(
        "SCHOLARCHAIN_GRAPH_BASE_URI" -> base,
        "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> base,
        "SCHOLARCHAIN_INTERNAL_TOKEN" -> internalToken
      )
    )
    val running = started.toOption.get
    try {
      val (_, metrics) = Http.get(running.port, "/metrics", authorization)
      assert(!metrics.contains("embedding_cache_"))
    } finally { running.close(); semanticServer.close() }
  }
}
