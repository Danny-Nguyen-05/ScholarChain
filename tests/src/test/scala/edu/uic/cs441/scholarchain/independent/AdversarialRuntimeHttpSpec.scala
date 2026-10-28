package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.{AtomicBoolean, AtomicInteger}
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class AdversarialRuntimeHttpSpec extends AnyFunSuite {
  import AdversarialRuntimeFixture.*
  private val external = "synthetic-adversarial-external-secret"
  private val internal = "synthetic-adversarial-internal-secret"
  private val cfg = ServiceConfig(
    Auth.sha256(external),
    Auth.sha256(internal),
    synchronousDeadlineMs = 3000,
    workflowTimeoutMs = 10000,
    maxWorkflowRetries = 0,
    downstreamTimeoutMs = 100
  )
  private val client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build()
  private val body = ujson
    .Obj("question" -> fusedPlan.question, "output" -> ujson.Obj("includeScores" -> false))
    .render()
  private def post(
      port: Int,
      content: String = body,
      key: String = "adversarial-http-replay",
      auth: String = external,
      privateHeader: String = "synthetic-private-header-canary"
  ): HttpResponse[String] = {
    val request = HttpRequest
      .newBuilder(URI.create(s"http://127.0.0.1:$port/v1/query"))
      .timeout(Duration.ofSeconds(10))
      .header("Content-Type", "application/json")
      .header("Authorization", "Bearer " + auth)
      .header("Idempotency-Key", key)
      .header("X-Private-Canary", privateHeader)
      .header("X-Trace-Id", "adversarial-http-trace")
      .POST(HttpRequest.BodyPublishers.ofString(content))
      .build()
    client.send(request, HttpResponse.BodyHandlers.ofString())
  }
  private def withServer(
      runtime: Runtime,
      store: QuerySessionStore = new InMemoryQuerySessionStore,
      log: String => Unit = _ => (),
      workflowCalls: Option[AtomicInteger] = None
  )(check: Int => Unit): Unit = {
    val delegate = runtime.adapter()
    val observed = new QueryWorkflow {
      def run(
          request: QueryRequest,
          context: RequestContext,
          stage: String => Unit
      ): Either[ApiError, WorkflowOutput] = {
        workflowCalls.foreach(_.incrementAndGet())
        delegate.run(request, context, stage)
      }
    }
    val queries = new QueryService(store, observed, cfg)
    val app = new ApiApplication(queries, cfg, logSink = log)
    val server = ApiServer.start(app, port = 0)
    try check(server.port)
    finally { server.close(); app.close() }
  }

  private def completed(port: Int, initial: HttpResponse[String]): ujson.Value = {
    assert(Set(200, 202)(initial.statusCode()), initial.body())
    if (initial.statusCode() == 200) ujson.read(initial.body())
    else {
      val job = ujson.read(initial.body())("jobId").str
      val until = System.nanoTime() + Duration.ofSeconds(10).toNanos
      var current = initial
      while (current.statusCode() == 202 && System.nanoTime() < until) {
        val request = HttpRequest
          .newBuilder(URI.create(s"http://127.0.0.1:$port/v1/jobs/$job/result"))
          .timeout(Duration.ofSeconds(3))
          .header("Authorization", "Bearer " + external)
          .GET()
          .build()
        current = client.send(request, HttpResponse.BodyHandlers.ofString())
        if (current.statusCode() == 202) Thread.sleep(10)
      }
      assert(
        current.statusCode() == 200,
        s"job must complete rather than stay QUEUED: ${current.body()}"
      )
      ujson.read(current.body())
    }
  }

  private def assertRecoveredAnswer(
      port: Int,
      initial: HttpResponse[String],
      key: String,
      runtime: Runtime,
      backing: QuerySessionStore,
      calls: AtomicInteger
  ): Unit = {
    val terminal = completed(port, initial)
    val claims = terminal("claims").arr.toVector.map(upickle.default.read[AnswerClaim](_))
    assert(claims.size == 1 && claims.head.verificationStatus == VerificationStatus.Verified)
    assert(
      claims.head.runtime.get.values == Vector(
        IndependentRuntime9CFixture.n("publicationCount", "3")
      )
    )
    val query = terminal("queryId").str
    val audit = runtime.audit(query)
    assert(audit.outcome == "ANSWERED")
    val stored = StorageResult.value(backing.get(query)).get
    assert(stored.state == "SUCCEEDED")
    assert(ujson.read(stored.payload)("result") == terminal)
    val replay = post(port, key = key)
    assert(replay.statusCode() == 200 && ujson.read(replay.body()) == terminal, replay.body())
    assert(runtime.audit(query) == audit)
    val changed = ujson.read(body)
    changed("question") = "A different synthetic recovery question"
    val conflict = post(port, content = changed.render(), key = key)
    assert(conflict.statusCode() == 409, conflict.body())
    assert(ujson.read(conflict.body())("error").str == "IDEMPOTENCY_CONFLICT")
    assert(calls.get() == 1 && runtime.llm.calls.size == 1)
  }

  test(
    "healthy control accepts the exact stored count through the same real HTTP and runtime composition"
  ) {
    val runtime = new Runtime(llm = new AttackLlm("correct"))
    withServer(runtime) { port =>
      val response = post(port, key = "adversarial-healthy-control")
      assert(response.statusCode() == 200, response.body())
      val json = ujson.read(response.body())
      val claims = json("claims").arr.toVector.map(upickle.default.read[AnswerClaim](_))
      assert(claims.size == 1 && claims.head.verificationStatus == VerificationStatus.Verified)
      assert(
        claims.head.runtime.get.values == Vector(
          IndependentRuntime9CFixture.n("publicationCount", "3")
        )
      )
      assert(json("answer")("summary").str.contains("3"))
      assert(runtime.audit(json("queryId").str).outcome == "ANSWERED")
      assert(runtime.llm.calls.size == 1)
    }
  }

  for ((field, attack) <- attacks) {
    test(
      s"HTTP $field injection reaches real retrieval and verifier and replay preserves the audited abstention"
    ) {
      val runtime = new Runtime(new Corpus(field, attack))
      withServer(runtime) { port =>
        assert(post(port, auth = internal).statusCode() == 401)
        assert(runtime.llm.calls.isEmpty)
        val first = post(port)
        assert(first.statusCode() == 200, first.body())
        val response = ujson.read(first.body())
        assert(response("claims").arr.isEmpty)
        assert(!response("answer")("summary").str.contains("999"))
        val query = response("queryId").str
        val audit = runtime.audit(query)
        assert(
          audit.outcome == "ABSTAINED" && audit.record.get.verification.rejectedClaims.size == 1
        )
        val bundleId = response("answer")("evidenceBundleId").str
        val bundle = StorageResult.value(runtime.evidence.get(bundleId)).get
        assert(bundle.items.flatMap(_.text).exists(_.contains(attack)))
        val replay = post(port)
        assert(replay.statusCode() == 200 && ujson.read(replay.body()) == response)
        assert(runtime.llm.calls.size == 1)
        assert(runtime.audit(query) == audit)
        val changed = ujson.read(body)
        changed("question") = "A different synthetic question"
        val conflict = post(port, content = changed.render())
        assert(conflict.statusCode() == 409)
        assert(ujson.read(conflict.body())("error").str == "IDEMPOTENCY_CONFLICT")
        assert(runtime.llm.calls.size == 1)
      }
    }
  }

  test(
    "one rejected Dynamo body bind recovers through same-key HTTP replay and executes exactly once"
  ) {
    val backing = new InMemoryQuerySessionStore
    val rejectFirst = new AtomicBoolean(true)
    val bindingAttempts = new AtomicInteger
    val appliedBindings = new AtomicInteger
    val calls = new AtomicInteger
    val store = new QuerySessionStore {
      def createIfAbsent(q: String, k: String): StorageResult[QuerySession] =
        backing.createIfAbsent(q, k)
      def get(q: String) = backing.get(q)
      def lookupByIdempotencyKey(k: String) = backing.lookupByIdempotencyKey(k)
      def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        if (expected == 0) {
          bindingAttempts.incrementAndGet()
          if (rejectFirst.compareAndSet(true, false))
            return StorageResult.Rejected("synthetic-dynamo-conditional-conflict")
        }
        val result = backing.update(s, expected)
        if (expected == 0 && StorageResult.successful(result)) appliedBindings.incrementAndGet()
        result
      }
    }
    val runtime = new Runtime(llm = new AttackLlm("correct"))
    withServer(runtime, store, workflowCalls = Some(calls)) { port =>
      val key = "adversarial-cas-conflict"
      val failed = post(port, key = key)
      assert(failed.statusCode() == 503, failed.body())
      assert(ujson.read(failed.body())("error").str == "SERVICE_UNAVAILABLE")
      assert(bindingAttempts.get() == 1 && appliedBindings.get() == 0)
      assert(calls.get() == 0 && runtime.llm.calls.isEmpty)
      assert(!failed.body().contains("conditional-conflict"))
      assertRecoveredAnswer(port, post(port, key = key), key, runtime, backing, calls)
      assert(bindingAttempts.get() == 2 && appliedBindings.get() == 1)
    }
  }

  test(
    "an applied Dynamo body bind with a lost reply completes through HTTP and stored replay without rerunning"
  ) {
    val backing = new InMemoryQuerySessionStore
    val bindingAttempts = new AtomicInteger
    val appliedBindings = new AtomicInteger
    val calls = new AtomicInteger
    val store = new QuerySessionStore {
      def createIfAbsent(q: String, k: String): StorageResult[QuerySession] =
        backing.createIfAbsent(q, k)
      def get(q: String) = backing.get(q)
      def lookupByIdempotencyKey(k: String) = backing.lookupByIdempotencyKey(k)
      def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        val result = backing.update(s, expected)
        if (expected == 0) {
          bindingAttempts.incrementAndGet()
          assert(
            StorageResult.successful(result),
            "the injected reply loss must follow an applied bind"
          )
          appliedBindings.incrementAndGet()
          StorageResult.Retried(1, StorageResult.Rejected("conditional-conflict"))
        } else result
      }
    }
    val runtime = new Runtime(llm = new AttackLlm("correct"))
    withServer(runtime, store, workflowCalls = Some(calls)) { port =>
      val key = "adversarial-applied-bind-lost-reply"
      assertRecoveredAnswer(port, post(port, key = key), key, runtime, backing, calls)
      assert(bindingAttempts.get() == 1 && appliedBindings.get() == 1)
    }
  }

  test(
    "synthetic config credentials header and thrown provider canaries stay absent from HTTP responses and observed logs"
  ) {
    val exceptionSecret = "synthetic-provider-exception-secret"
    val privateSecret = "synthetic-private-header-canary"
    val calls = new AtomicInteger
    val failing = new ResearcherMetricStore {
      def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] =
        StorageResult.Rejected("unused")
      def get(id: String, w: String): StorageResult[ResearcherMetricRecord] = {
        calls.incrementAndGet(); throw new IllegalStateException(exceptionSecret)
      }
      def batchGet(
          keys: Vector[(String, String)]
      ): StorageResult[Vector[ResearcherMetricRecord]] = {
        calls.incrementAndGet(); throw new IllegalStateException(exceptionSecret)
      }
    }
    val requestLogs = new ConcurrentLinkedQueue[String]
    val runtimeLogs = new ConcurrentLinkedQueue[String]
    val logging = org.apache.logging.log4j.LogManager
      .getContext(false)
      .asInstanceOf[org.apache.logging.log4j.core.LoggerContext]
    val logger = logging.getLogger("scholarchain.runtime.stage")
    val priorLevel = logger.getLevel
    val appender = new org.apache.logging.log4j.core.appender.AbstractAppender(
      "adversarial-canary-capture",
      null,
      org.apache.logging.log4j.core.layout.PatternLayout.createDefaultLayout(),
      false,
      Array.empty[org.apache.logging.log4j.core.config.Property]
    ) {
      def append(event: org.apache.logging.log4j.core.LogEvent): Unit = {
        runtimeLogs.add(event.getMessage.getFormattedMessage)
        Option(event.getThrown).foreach(error => runtimeLogs.add(error.toString))
        ()
      }
    }
    appender.start(); logger.addAppender(appender)
    logger.setLevel(org.apache.logging.log4j.Level.INFO)
    try {
      val runtime = new Runtime(metricPort = failing)
      withServer(runtime, log = line => { requestLogs.add(line); () }) { port =>
        val response = post(port, key = "adversarial-secret-failure", privateHeader = privateSecret)
        assert(response.statusCode() == 200, response.body())
        assert(ujson.read(response.body())("claims").arr.isEmpty)
        assert(calls.get == 1 && runtime.llm.calls.isEmpty)
        assert(requestLogs.size() == 1)
        assert(ujson.read(requestLogs.peek())("event").str == "http_request")
        assert(!runtimeLogs.isEmpty, "Runtime stage log capture must observe actual events")
        val logs = requestLogs.iterator().asScala.mkString("\n") + runtimeLogs
          .iterator()
          .asScala
          .mkString("\n")
        val observed = logs + response.body() + response.headers().map().toString
        for (
          secret <- Vector(
            external,
            internal,
            cfg.apiKeySha256,
            cfg.internalTokenSha256,
            privateSecret,
            exceptionSecret
          )
        )
          assert(!observed.contains(secret), "A synthetic secret escaped its boundary")
        assert(runtime.audit(ujson.read(response.body())("queryId").str).stageFailures.nonEmpty)
      }
    } finally { logger.removeAppender(appender); logger.setLevel(priorLevel); appender.stop() }
  }
}
