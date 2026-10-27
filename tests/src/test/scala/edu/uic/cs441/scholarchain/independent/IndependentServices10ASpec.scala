package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.{
  InMemoryQuerySessionStore,
  QuerySession,
  QuerySessionStore,
  StorageResult
}
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import java.util.concurrent.{Callable, ConcurrentLinkedQueue, CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

/** Wire-level requirements, with deliberately synthetic output and no production fixtures. */
class IndependentServices10ASpec extends AnyFunSuite {
  private val externalKey = "synthetic-external-api-key-10a"
  private val internalKey = "synthetic-internal-service-key-10a"
  private val client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build()
  private val config = ServiceConfig(
    apiKeySha256 = Auth.sha256(externalKey),
    internalTokenSha256 = Auth.sha256(internalKey),
    synchronousDeadlineMs = 1000,
    workflowTimeoutMs = 5000,
    maxWorkflowRetries = 0
  )
  private val body = """{
    "question":"Show collaboration counts for the synthetic fixture",
    "constraints":{"yearFrom":2015,"yearTo":2026,"topics":[],"institutions":[],"venues":[]},
    "analysis":{"rankingMetric":"DISTINCT_COAUTHOR_COUNT","includeTeamSize":true,
      "includeBridgeMetrics":true,"includeCommunities":true,"includePaths":true},
    "retrieval":{"graphLimit":10,"vectorLimit":3,"maxPathDepth":2},
    "output":{"includeEvidence":true,"includeScores":true,"includeUncertainty":true}
  }"""
  private def output = WorkflowOutput(
    answer = ujson.Obj(
      "summary" -> "Synthetic workflow completed without researcher claims.",
      "researchers" -> ujson.Arr()
    )
  )
  private def workflow(
      f: (QueryRequest, RequestContext, String => Unit) => Either[ApiError, WorkflowOutput]
  ): QueryWorkflow = new QueryWorkflow {
    def run(r: QueryRequest, c: RequestContext, stage: String => Unit) = f(r, c, stage)
  }
  private def withServer(
      w: QueryWorkflow,
      cfg: ServiceConfig = config,
      ready: () => Boolean = () => true,
      store: QuerySessionStore = new InMemoryQuerySessionStore,
      log: String => Unit = _ => ()
  )(check: Int => Unit): Unit = {
    val service = new QueryService(store, w, cfg)
    val server = ApiServer.start(new ApiApplication(service, cfg, ready, log), port = 0)
    try check(server.port)
    finally {
      server.close()
      service.close()
    }
  }
  private def request(
      port: Int,
      path: String,
      content: Option[String] = None,
      auth: Option[String] = Some(externalKey),
      idempotency: Option[String] = None,
      headers: Map[String, String] = Map.empty
  ): HttpResponse[String] = {
    val builder = HttpRequest
      .newBuilder(URI.create(s"http://127.0.0.1:$port$path"))
      .timeout(Duration.ofSeconds(8))
    auth.foreach(k => builder.header("Authorization", s"Bearer $k"))
    idempotency.foreach(k => builder.header("Idempotency-Key", k))
    headers.foreach { case (k, v) => builder.header(k, v) }
    content match {
      case Some(value) =>
        builder.header("Content-Type", "application/json")
        builder.POST(HttpRequest.BodyPublishers.ofString(value))
      case None => builder.GET()
    }
    client.send(builder.build(), HttpResponse.BodyHandlers.ofString())
  }
  private def json(response: HttpResponse[String]): ujson.Value = ujson.read(response.body())
  private def error(response: HttpResponse[String], status: Int): Unit = {
    assert(response.statusCode() == status, response.body())
    val value = json(response)
    assert(response.headers().firstValue("X-Trace-Id").isPresent)
    val text = response.body()
    assert(value("traceId").str.nonEmpty && value("error").str.nonEmpty)
    assert(!text.contains(externalKey) && !text.contains(internalKey))
    assert(!text.contains("java.lang.") && !text.contains("Exception:"))
    assert(value.isInstanceOf[ujson.Obj])
  }

  test("synchronous HTTP query returns course response shape and propagates request identifiers") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, context, stage) =>
      runs.incrementAndGet()
      assert(context.requestId == "request-independent-10a")
      assert(context.traceId == "trace-independent-10a")
      assert(context.queryId.nonEmpty)
      stage("CLAIM_VERIFICATION")
      Right(output)
    }) { port =>
      val response = request(
        port,
        "/v1/query",
        Some(body),
        idempotency = Some("independent-sync"),
        headers = Map(
          "X-Request-Id" -> "request-independent-10a",
          "X-Trace-Id" -> "trace-independent-10a"
        )
      )
      assert(response.statusCode() == 200, response.body())
      val value = json(response)
      assert(value("queryId").str.nonEmpty)
      assert(value("mode").str == "synchronous")
      assert(value("answer")("summary").str == output.answer("summary").str)
      assert(value("answer")("researchers").arr.isEmpty)
      assert(value("claims").arr.isEmpty)
      assert(response.headers().firstValue("X-Request-Id").orElse("") == "request-independent-10a")
      assert(response.headers().firstValue("X-Trace-Id").orElse("") == "trace-independent-10a")
      assert(runs.get() == 1)
    }
  }

  test("same idempotency key replays stored answer without a second workflow execution") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      val first = request(port, "/v1/query", Some(body), idempotency = Some("replay"))
      val again = request(port, "/v1/query", Some(body), idempotency = Some("replay"))
      assert(first.statusCode() == 200 && again.statusCode() == 200)
      assert(json(first)("queryId") == json(again)("queryId"))
      assert(json(first)("answer") == json(again)("answer"))
      assert(runs.get() == 1)
    }
  }

  test("same idempotency key with a different question gives typed conflict") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      assert(
        request(port, "/v1/query", Some(body), idempotency = Some("conflict")).statusCode() == 200
      )
      val changed = body.replace("Show collaboration counts", "Show different collaboration counts")
      error(request(port, "/v1/query", Some(changed), idempotency = Some("conflict")), 409)
      assert(runs.get() == 1)
    }
  }

  test(
    "stored replay and body conflict survive a fresh service instance sharing the session store"
  ) {
    val sessions = new InMemoryQuerySessionStore
    val runs = new AtomicInteger()
    val fake = workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }
    var queryId = ""
    withServer(fake, store = sessions) { port =>
      val first = request(port, "/v1/query", Some(body), idempotency = Some("persisted"))
      assert(first.statusCode() == 200, first.body())
      queryId = json(first)("queryId").str
    }
    withServer(fake, store = sessions) { port =>
      val replay = request(port, "/v1/query", Some(body), idempotency = Some("persisted"))
      assert(replay.statusCode() == 200, replay.body())
      assert(json(replay)("queryId").str == queryId)
      assert(json(replay)("answer")("researchers").arr.isEmpty)
      val changed = body.replace("Show collaboration counts", "Show different collaboration counts")
      error(request(port, "/v1/query", Some(changed), idempotency = Some("persisted")), 409)
      assert(runs.get() == 1)
    }
  }

  test("concurrent service instances sharing an idempotency key claim one workflow and one job") {
    val runs = new AtomicInteger()
    val finish = new CountDownLatch(1)
    val clients = Executors.newFixedThreadPool(2)
    val sessions = new InMemoryQuerySessionStore
    val fake = workflow { (_, _, _) =>
      runs.incrementAndGet()
      if (finish.await(6, TimeUnit.SECONDS)) Right(output)
      else Left(ApiError(504, "TEST_TIMEOUT", "Synthetic test timed out"))
    }
    val cfg = config.copy(synchronousDeadlineMs = 25)
    try
      withServer(fake, cfg, store = sessions) { firstPort =>
        withServer(fake, cfg, store = sessions) { secondPort =>
          val start = new CountDownLatch(1)
          val requests = Vector(firstPort, secondPort).map { port =>
            clients.submit(new Callable[HttpResponse[String]] {
              def call(): HttpResponse[String] = {
                assert(start.await(2, TimeUnit.SECONDS))
                request(port, "/v1/query", Some(body), idempotency = Some("concurrent"))
              }
            })
          }
          start.countDown()
          val responses = requests.map(_.get(4, TimeUnit.SECONDS))
          responses.foreach(r => assert(r.statusCode() == 202, r.body()))
          assert(responses.map(r => json(r)("jobId").str).distinct.size == 1)
          assert(responses.map(r => json(r)("queryId").str).distinct.size == 1)
          assert(runs.get() == 1)
          finish.countDown()
        }
      }
    finally {
      finish.countDown()
      clients.shutdownNow()
    }
  }

  test(
    "replay waits for conditional reservation body binding before resolving replay or conflict"
  ) {
    for (differentBody <- Vector(false, true)) {
      val bound = new CountDownLatch(1)
      val release = new CountDownLatch(1)
      val observedBlank = new CountDownLatch(1)
      val delegate = new InMemoryQuerySessionStore
      val sessions = new QuerySessionStore {
        def createIfAbsent(q: String, k: String): StorageResult[QuerySession] =
          delegate.createIfAbsent(q, k)
        def get(q: String): StorageResult[QuerySession] = {
          val result = delegate.get(q)
          if (StorageResult.value(result).exists(_.payload == "{}")) observedBlank.countDown()
          result
        }
        def lookupByIdempotencyKey(k: String): StorageResult[QuerySession] =
          delegate.lookupByIdempotencyKey(k)
        def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
          if (expected == 0) {
            bound.countDown()
            assert(release.await(6, TimeUnit.SECONDS))
          }
          delegate.update(s, expected)
        }
      }
      val runs = new AtomicInteger()
      val callers = Executors.newFixedThreadPool(2)
      val fake = workflow { (_, _, _) =>
        runs.incrementAndGet(); Right(output)
      }
      try
        withServer(fake, store = sessions) { firstPort =>
          withServer(fake, store = sessions) { secondPort =>
            val first = callers.submit(new Callable[HttpResponse[String]] {
              def call() =
                request(firstPort, "/v1/query", Some(body), idempotency = Some("binding"))
            })
            assert(bound.await(2, TimeUnit.SECONDS))
            val second = callers.submit(new Callable[HttpResponse[String]] {
              def call() = request(
                secondPort,
                "/v1/query",
                Some(
                  if (differentBody) body.replace("Show collaboration", "Show other collaboration")
                  else body
                ),
                idempotency = Some("binding")
              )
            })
            assert(observedBlank.await(2, TimeUnit.SECONDS))
            release.countDown()
            val original = first.get(4, TimeUnit.SECONDS)
            val replay = second.get(4, TimeUnit.SECONDS)
            assert(original.statusCode() == 200, original.body())
            if (differentBody) error(replay, 409)
            else {
              assert(Set(200, 202)(replay.statusCode()), replay.body())
              assert(json(replay)("queryId") == json(original)("queryId"))
            }
            assert(runs.get() == 1)
          }
        }
      finally {
        release.countDown()
        callers.shutdownNow()
      }
    }
  }

  test("asynchronous query keeps its job reference and exposes final result after completion") {
    val entered = new CountDownLatch(1)
    val finish = new CountDownLatch(1)
    val runs = new AtomicInteger()
    try
      withServer(
        workflow { (_, _, stage) =>
          runs.incrementAndGet()
          stage("CLAIM_VERIFICATION")
          entered.countDown()
          if (!finish.await(6, TimeUnit.SECONDS)) Left(ApiError(504, "TEST_TIMEOUT", "Timed out"))
          else Right(output)
        },
        config.copy(synchronousDeadlineMs = 25)
      ) { port =>
        val response = request(port, "/v1/query", Some(body), idempotency = Some("async"))
        assert(entered.await(2, TimeUnit.SECONDS))
        assert(response.statusCode() == 202, response.body())
        val accepted = json(response)
        assert(accepted("mode").str == "asynchronous")
        val jobId = accepted("jobId").str
        assert(accepted("statusUrl").str == s"/v1/jobs/$jobId")
        val replay = request(port, "/v1/query", Some(body), idempotency = Some("async"))
        assert(replay.statusCode() == 202)
        assert(json(replay)("jobId").str == jobId)
        val running = request(port, s"/v1/jobs/$jobId")
        assert(running.statusCode() == 200)
        val status = json(running)
        assert(status("jobId").str == jobId)
        assert(status("queryId").str == accepted("queryId").str)
        assert(status("stage").str == "CLAIM_VERIFICATION")
        assert(status("createdAt").str.nonEmpty && status("updatedAt").str.nonEmpty)
        finish.countDown()
        val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(4)
        var result = request(port, s"/v1/jobs/$jobId/result")
        while (result.statusCode() == 202 && System.nanoTime() < deadline) {
          Thread.sleep(10)
          result = request(port, s"/v1/jobs/$jobId/result")
        }
        assert(result.statusCode() == 200, result.body())
        assert(json(result)("answer")("summary").str == output.answer("summary").str)
        assert(runs.get() == 1)
      }
    finally finish.countDown()
  }

  test("missing and incorrect bearer credentials reject query and jobs before workflow") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      error(request(port, "/v1/query", Some(body), auth = None, idempotency = Some("noauth")), 401)
      error(
        request(port, "/v1/query", Some(body), auth = Some("incorrect"), idempotency = Some("bad")),
        401
      )
      error(request(port, "/v1/jobs/nonexistent", auth = None), 401)
      error(request(port, "/metrics", auth = None), 401)
      assert(runs.get() == 0)
    }
  }

  test("liveness remains healthy while failed readiness reveals no dependency address") {
    withServer(workflow { (_, _, _) => Right(output) }, ready = () => false) { port =>
      val alive = request(port, "/healthz", auth = None)
      val ready = request(port, "/readyz", auth = None)
      assert(alive.statusCode() == 200)
      assert(ready.statusCode() == 503)
      assert(!alive.body().contains("127.0.0.1") && !ready.body().contains("127.0.0.1"))
      assert(!ready.body().contains(externalKey) && !ready.body().contains(internalKey))
    }
  }

  test(
    "external bearer cannot authorize internal routes and internal token cannot authorize queries"
  ) {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      error(request(port, "/internal/v1/not-implemented"), 401)
      error(request(port, "/internal/v1/not-implemented", auth = None), 401)
      error(request(port, "/internal/v1/not-implemented", auth = Some(internalKey)), 404)
      error(
        request(
          port,
          "/v1/query",
          Some(body),
          auth = Some(internalKey),
          idempotency = Some("internal")
        ),
        401
      )
      assert(runs.get() == 0)
    }
  }

  test("malformed JSON and invalid constraint types are rejected before workflow") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      error(request(port, "/v1/query", Some("{broken"), idempotency = Some("json")), 400)
      val invalid = body.replace("\"yearFrom\":2015", "\"yearFrom\":\"yesterday\"")
      error(request(port, "/v1/query", Some(invalid), idempotency = Some("type")), 400)
      assert(runs.get() == 0)
    }
  }

  test("unsupported constraint gets 422 and missing idempotency key gets 400") {
    val runs = new AtomicInteger()
    withServer(workflow { (_, _, _) =>
      runs.incrementAndGet(); Right(output)
    }) { port =>
      val unsupported =
        body.replace("\"yearFrom\":2015", "\"unknownConstraint\":true,\"yearFrom\":2015")
      error(request(port, "/v1/query", Some(unsupported), idempotency = Some("unsupported")), 422)
      error(request(port, "/v1/query", Some(body)), 400)
      assert(runs.get() == 0)
    }
  }

  test("workflow downstream error and timeout preserve typed HTTP mapping with trace ID") {
    for ((status, code) <- Vector(502 -> "DOWNSTREAM_FAILURE", 504 -> "DOWNSTREAM_TIMEOUT")) {
      withServer(workflow { (_, _, _) =>
        Left(ApiError(status, code, "Synthetic dependency failure"))
      }) { port =>
        error(request(port, "/v1/query", Some(body), idempotency = Some(s"error-$status")), status)
      }
    }
  }

  test("missing jobs produce typed 404 for status and result") {
    withServer(workflow { (_, _, _) => Right(output) }) { port =>
      error(request(port, "/v1/jobs/job-missing"), 404)
      error(request(port, "/v1/jobs/job-missing/result"), 404)
    }
  }

  test(
    "structured request logs exclude authorization, extra headers, and malformed request content"
  ) {
    val logs = new ConcurrentLinkedQueue[String]()
    val sensitiveBody = "synthetic-sensitive-request-content"
    val sensitiveHeader = "synthetic-private-extra-header"
    withServer(workflow { (_, _, _) => Right(output) }, log = line => { logs.add(line); () }) {
      port =>
        error(
          request(
            port,
            "/v1/query",
            Some(sensitiveBody),
            idempotency = Some("log-redaction"),
            headers = Map("X-Private-Extra" -> sensitiveHeader)
          ),
          400
        )
        assert(logs.size() == 1)
        val line = logs.peek()
        assert(!line.contains(externalKey) && !line.contains(internalKey))
        assert(!line.contains(sensitiveBody) && !line.contains(sensitiveHeader))
        val event = ujson.read(line)
        assert(event("event").str == "http_request")
        assert(event("route").str == "/v1/query")
        assert(event("status").num == 400)
        assert(event("requestId").str.nonEmpty && event("traceId").str.nonEmpty)
    }
  }

  test("authenticated metrics expose status counts, timeout counts, and histogram buckets") {
    withServer(workflow { (_, _, _) =>
      Left(ApiError(504, "INJECTED_TIMEOUT", "Synthetic timeout"))
    }) { port =>
      error(request(port, "/v1/query", Some(body), idempotency = Some("metrics")), 504)
      val metrics = request(port, "/metrics")
      assert(metrics.statusCode() == 200)
      assert(metrics.headers().firstValue("Content-Type").orElse("").startsWith("text/plain"))
      assert(metrics.body().contains("api_status_total{status=\"504\"} 1"))
      assert(metrics.body().contains("api_timeouts_total 1"))
      assert(metrics.body().contains("api_latency_seconds_bucket{le=\"+Inf\"}"))
      assert(metrics.body().contains("api_latency_seconds_count"))
      assert(metrics.body().contains("api_latency_seconds_sum"))
      assert(!metrics.body().contains(externalKey) && !metrics.body().contains(internalKey))
    }
  }
}
