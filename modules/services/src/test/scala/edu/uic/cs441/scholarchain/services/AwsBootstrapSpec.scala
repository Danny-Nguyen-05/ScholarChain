package edu.uic.cs441.scholarchain.services

import java.io.{ByteArrayOutputStream, PrintStream}
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.concurrent.atomic.AtomicBoolean
import org.scalatest.funsuite.AnyFunSuite

class AwsBootstrapSpec extends AnyFunSuite {
  import AwsTestEnv.*
  private val roles = Vector("query-api", "graph-service", "semantic-service", "embedding-worker")
  private val fast =
    Map("SCHOLARCHAIN_READINESS_CACHE_MS" -> "1", "SCHOLARCHAIN_READINESS_TIMEOUT_MS" -> "500")

  private def captured[A](body: => A): (A, String) = {
    val original = System.err
    val buffer = new ByteArrayOutputStream
    System.setErr(new PrintStream(buffer, true, UTF_8))
    try { val result = body; (result, buffer.toString(UTF_8)) }
    finally System.setErr(original)
  }
  private val apiHeaders = Map("Authorization" -> ("Bearer " + apiKey), "Idempotency-Key" -> "k-1")
  private def local(mode: Option[String]): Map[String, String] =
    Map(
      "SCHOLARCHAIN_API_KEY_SHA256" -> common("SCHOLARCHAIN_API_KEY_SHA256"),
      "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> common("SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"),
      "SCHOLARCHAIN_HTTP_PORT" -> "0"
    ) ++ mode.map("SCHOLARCHAIN_SERVICE_MODE" -> _)

  test("mode selection accepts the three explicit modes and refuses anything else") {
    assert(ServiceBootstrap.modes == Set("unconfigured", "offline-synthetic", "aws"))
    val factory = new FakeFactory
    val (result, err) = captured(
      ServiceBootstrap.launch("query-api", local(Some("live")), factory)
    )
    assert(result.left.toOption.contains(2) && err.trim == "unsupported-service-mode")
    assert(factory.opened.isEmpty)
    val (blank, _) = captured(ServiceBootstrap.launch("query-api", local(Some("AWS")), factory))
    assert(blank.left.toOption.contains(2), "mode names are exact")
  }

  test("aws mode refuses with exit 2 before creating any client, naming only the variable") {
    for (role <- roles) {
      val factory = new FakeFactory
      val bare = Map("SCHOLARCHAIN_SERVICE_MODE" -> "aws") ++ local(None)
      val (result, err) = captured(ServiceBootstrap.launch(role, bare, factory))
      assert(result.left.toOption.contains(2), role)
      assert(err.trim.startsWith("missing-aws-configuration:"), s"$role: $err")
      assert(factory.opened.isEmpty, s"$role created ports before validation")
      assert(!err.contains("\tat "), "no stack trace")
    }
  }

  test("aws mode refuses an invalid value without echoing it") {
    val factory = new FakeFactory
    val bad = graph.updated("SCHOLARCHAIN_NEPTUNE_ENDPOINT", "http://leaky-host.example:8182")
    val (result, err) = captured(ServiceBootstrap.launch("graph-service", bad, factory))
    assert(result.left.toOption.contains(2))
    assert(err.trim == "invalid-aws-configuration:SCHOLARCHAIN_NEPTUNE_ENDPOINT")
    assert(!err.contains("leaky-host"))
  }

  test("a port factory refusal or exception exits 2 with a closed message") {
    val factory = new FakeFactory
    factory.refuse = Some("graph-reader-connect-failed")
    val (refused, refusedErr) = captured(ServiceBootstrap.launch("graph-service", graph, factory))
    assert(
      refused.left.toOption.contains(2) && refusedErr.trim == "graph-reader-connect-failed"
    )
    val exploding = new FakeFactory
    exploding.explode = true
    val (exploded, explodedErr) =
      captured(ServiceBootstrap.launch("semantic-service", semantic, exploding))
    assert(exploded.left.toOption.contains(2))
    assert(
      explodedErr.trim == "invalid-aws-composition" && !explodedErr.contains("provider-detail")
    )
  }

  test(
    "each role starts in aws mode, serves liveness without touching dependencies, and reports readiness"
  ) {
    for (role <- roles.filterNot(_ == "query-api")) {
      val factory = new FakeFactory
      val env = forRole(role) ++ fast
      val running = ServiceBootstrap.launch(role, env, factory).toOption.get
      try {
        assert(factory.opened.toArray.toVector == Vector(role))
        assert(Http.get(running.port, "/healthz")._1 == 200)
        assert(factory.d.total == 0, "liveness is process-only")
        val before = factory.d.total
        (1 to 5).foreach(_ => assert(Http.get(running.port, "/healthz")._1 == 200))
        assert(factory.d.total == before)
        assert(Http.get(running.port, "/readyz")._1 == 200)
        factory.d.failing = Set("metrics", "vectors", "queue")
        Thread.sleep(10)
        assert(Http.get(running.port, "/readyz")._1 == 503)
        assert(Http.get(running.port, "/healthz")._1 == 200, "liveness never depends on AWS")
      } finally running.close()
      assert(factory.closed.get == 1, s"$role ports released on close")
    }
  }

  test("query-api starts in aws mode and its readiness follows both peers") {
    val graphReady = new AtomicBoolean(true)
    val semanticReady = new AtomicBoolean(true)
    val config = service(common)
    def stub(role: String, flag: AtomicBoolean) = ApiServer.start(
      new ApiApplication(
        new QueryService(
          new edu.uic.cs441.scholarchain.storage.InMemoryQuerySessionStore,
          (_, _, _) => Left(ApiError.unavailable),
          config
        ),
        config,
        () => flag.get,
        _ => (),
        role
      ),
      "127.0.0.1",
      0
    )
    val graphServer = stub("graph-service", graphReady)
    val semanticServer = stub("semantic-service", semanticReady)
    val factory = new FakeFactory
    factory.functionalSessions = true
    val env = query(
      s"http://127.0.0.1:${graphServer.port}",
      s"http://127.0.0.1:${semanticServer.port}"
    ) ++ fast ++ shortBreaker
    val running = ServiceBootstrap.launch("query-api", env, factory).toOption.get
    try {
      assert(Http.get(running.port, "/readyz")._1 == 200)
      graphReady.set(false)
      assert(settle(true)(Http.get(running.port, "/readyz")._1 == 503))
      assert(Http.get(running.port, "/healthz")._1 == 200)
      graphReady.set(true)
      assert(settle(true)(Http.get(running.port, "/readyz")._1 == 200))
      // A query reaches the injected model, not a scripted answer; the recording model returns no output.
      val body = """{"question":"Who are the most connected researchers?"}"""
      val (status, reply) = Http.post(running.port, "/v1/query", body, apiHeaders)
      assert(status != 200, "no fabricated answer when the model yields nothing")
      assert(!factory.llm.requests.isEmpty, s"$status $reply")
    } finally { running.close(); graphServer.close(); semanticServer.close() }
    assert(factory.closed.get == 1)
  }

  test("unconfigured mode is unchanged: alive, never ready, refuses query work") {
    for (mode <- Vector(None, Some("unconfigured"))) {
      val factory = new FakeFactory
      val running = ServiceBootstrap.launch("query-api", local(mode), factory).toOption.get
      try {
        assert(Http.get(running.port, "/healthz")._1 == 200)
        assert(Http.get(running.port, "/readyz")._1 == 503)
        val body = """{"question":"Synthetic fixture: publication count for A"}"""
        assert(Http.post(running.port, "/v1/query", body, apiHeaders)._1 == 503)
        assert(factory.opened.isEmpty, "no port or client is created outside aws mode")
      } finally running.close()
    }
  }

  test("offline-synthetic mode is unchanged: the declared fixture question is answered") {
    val factory = new FakeFactory
    val running =
      ServiceBootstrap.launch("query-api", local(Some("offline-synthetic")), factory).toOption.get
    try {
      assert(Http.get(running.port, "/healthz")._1 == 200)
      assert(Http.get(running.port, "/readyz")._1 == 200)
      val body =
        """{"question":"Synthetic fixture: publication count for A","output":{"includeScores":false}}"""
      val (status, reply) = Http.post(running.port, "/v1/query", body, apiHeaders)
      assert(status == 200, reply)
      assert(reply.contains("researchers") && reply.contains("publicationCount"))
      val other = """{"question":"Some other question"}"""
      assert(
        Http
          .post(running.port, "/v1/query", other, apiHeaders.updated("Idempotency-Key", "k-2"))
          ._1 == 422
      )
      assert(factory.opened.isEmpty)
    } finally running.close()
  }

  test("aws composition source selects no stand-in store, embedder, model or fixture") {
    val directory = Path.of("modules/services/src/main/scala/edu/uic/cs441/scholarchain/services")
    val base = if (Files.isDirectory(directory)) directory else locate()
    val forbidden =
      Vector("InMemory", "Deterministic", "Offline", "Scripted", "fakes.", "Fixture", "Synthetic")
    for (
      name <- Vector("AwsConfig", "AwsPorts", "AwsComposition", "LiveAdapters", "ReadinessGate")
    ) {
      val text = Files.readString(base.resolve(name + ".scala"), UTF_8)
      forbidden.foreach(word => assert(!text.contains(word), s"$name.scala mentions $word"))
    }
    val mains = Files.readString(base.resolve("ServiceMains.scala"), UTF_8)
    val start = mains.indexOf("private def launchAws")
    val end = mains.indexOf("private def launchLocal")
    val aws = mains.substring(start, end)
    forbidden.foreach(word => assert(!aws.contains(word), s"aws launch path mentions $word"))
    assert(aws.contains("AwsComposition.build"))
  }

  private def locate(): Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("modules/services/src/main/scala/edu/uic/cs441/scholarchain/services"))
    .find(Files.isDirectory(_))
    .get
}
