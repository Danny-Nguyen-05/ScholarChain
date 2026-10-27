package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import java.net.{URI, URLEncoder}
import java.net.http.HttpResponse
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class IndependentServices10BLifecycleSpec extends AnyFunSuite {
  import IndependentServices10BFixture.*
  private def json(r: HttpResponse[String]) = ujson.read(r.body())
  private def encoded(value: String) = URLEncoder.encode(value, "UTF-8")
  private def error(response: HttpResponse[String], status: Int): Unit = {
    assert(response.statusCode() == status, response.body())
    val value = json(response)
    assert(value("traceId").str == "trace-independent-10b")
    assert(value("error").str.nonEmpty && value("message").str.nonEmpty)
    assert(response.headers().firstValue("X-Trace-Id").orElse("") == "trace-independent-10b")
    assert(!response.body().contains(externalKey) && !response.body().contains(internalKey))
    assert(!response.body().contains("java.lang.") && !response.body().contains("Exception:"))
  }
  private def withServer(
      runtime: Runtime,
      graph: GraphEndpoints = new GraphApi(snapshot()),
      semantic: SemanticEndpoints =
        new SemanticApi((_, _) => Right(ujson.Obj("hits" -> ujson.Arr()))),
      role: String = "query-api",
      metrics: ServiceMetrics = new ServiceMetrics
  )(check: Int => Unit): Unit = {
    val sessions = new InMemoryQuerySessionStore
    val queries = new QueryService(sessions, runtime.workflow, config, metrics)
    val extension = ExtendedApi(
      new EvidenceApi(runtime.evidence, runtime.audits, Some(sessions)),
      graph,
      semantic
    )
    val app = new ApiApplication(
      queries,
      config,
      logSink = _ => (),
      serviceRole = role,
      extended = Some(extension)
    )
    val server = ApiServer.start(app, port = 0)
    try check(server.port)
    finally server.close()
  }

  test(
    "HTTP lifecycle runs real retrieval, verifies count three, fetches backing evidence and explains the audited answer"
  ) {
    val runtime = new Runtime
    withServer(runtime) { port =>
      val response = request(port, "/v1/query", Some(body), key = Some("independent-10b-lifecycle"))
      assert(response.statusCode() == 200, response.body())
      val answer = json(response)
      val queryId = answer("queryId").str
      assert(answer("answer")("summary").str.contains("3"))
      val claims = answer("claims").arr.toVector
      assert(claims.nonEmpty)
      assert(claims.forall(_("verificationStatus").str == "VERIFIED"))
      val typedClaims = claims.map(upickle.default.read[AnswerClaim](_))
      assert(
        typedClaims.exists(
          _.runtime.exists(
            _.values.exists(v => v.field == "publicationCount" && v.number.contains("3"))
          )
        )
      )
      val referenced = claims.flatMap(_("evidenceIds").arr.map(_.str)).distinct
      assert(referenced.nonEmpty)
      for (id <- referenced) {
        val stored = StorageResult
          .value(runtime.evidence.getItem(id))
          .getOrElse(fail("Claim lacks stored source evidence"))
        val fetched = request(port, "/v1/evidence/" + encoded(id))
        assert(fetched.statusCode() == 200, fetched.body())
        val evidence = json(fetched)
        assert(evidence("evidenceId").str == id)
        assert(evidence("sourceUri").str == stored.sourceUri && stored.sourceUri.nonEmpty)
        assert(evidence("sourceRecordId").str == stored.provenance.sourceRecordId)
        assert(evidence("snapshot").str == stored.provenance.datasetSnapshot)
        assert(evidence("provenance") == upickle.default.writeJs(stored.provenance))
        assert(evidence("supportingContent") == upickle.default.writeJs(stored.runtime.get))
        assert(
          stored.runtime.get.values.exists(v =>
            v.field == "publicationCount" && v.number.contains("3")
          )
        )
      }
      val evidenceList = request(port, answer("links")("evidence").str)
      assert(evidenceList.statusCode() == 200, evidenceList.body())
      assert(referenced.toSet.subsetOf(json(evidenceList)("evidenceIds").arr.map(_.str).toSet))
      val explain = request(port, answer("links")("explain").str)
      assert(explain.statusCode() == 200, explain.body())
      val explanation = json(explain)
      val audit = StorageResult.value(runtime.audits.get(queryId)).get
      assert(explanation("queryPlan") == upickle.default.writeJs(IndependentRuntime9CFixture.plan))
      assert(explanation("verificationStatus").str == "VERIFIED")
      assert(explanation("evidenceIds").arr.map(_.str).toSet == audit.record.get.evidenceIds.toSet)
      assert(
        explanation("promptVersions").arr
          .map(_.str)
          .contains(IndependentRuntime9CFixture.config.synthesisPromptVersion)
      )
      assert(
        explanation("modelVersions").arr.exists(
          _("modelId").str == IndependentRuntime9CFixture.config.model.modelId
        )
      )
      assert(explanation("counters")("verifiedClaims").num >= 1)
      assert(explanation("counters")("rejectedClaims").num == 0)
      val stages = explanation("stagesExecuted").arr.map(_.str).toSet
      assert(Set("PLANNING", "RETRIEVAL", "AUDIT").subsetOf(stages))
      assert(explanation.obj.contains("scoreComponents"))
      assert(
        !explanation.obj.keySet.exists(k =>
          Set("chainOfThought", "reasoning", "hiddenReasoning", "promptText")(k)
        )
      )
      val replay = request(port, "/v1/query", Some(body), key = Some("independent-10b-lifecycle"))
      assert(replay.statusCode() == 200 && json(replay) == answer)
      assert(runtime.modelCalls.get == 1)
    }
  }

  test(
    "new evidence, explain and graph HTTP routes require external authentication and return traced missing records"
  ) {
    withServer(new Runtime) { port =>
      for (
        path <- Vector(
          "/v1/evidence/missing",
          "/v1/explain/missing",
          "/v1/queries/missing/evidence",
          s"/v1/graph/nodes/$a",
          s"/v1/graph/nodes/$a/neighbors"
        )
      ) {
        error(request(port, path, auth = None), 401)
        error(request(port, path, auth = Some(internalKey)), 401)
      }
      error(request(port, "/v1/evidence/missing"), 404)
      error(request(port, "/v1/explain/missing"), 404)
      error(request(port, "/v1/query", Some("{broken"), key = Some("malformed-10b")), 400)
    }
  }

  test(
    "HTTP graph query strings enforce requested direction, pagination, caps and duplicate parameter rejection"
  ) {
    withServer(new Runtime) { port =>
      val path = s"/v1/graph/nodes/$a/neighbors"
      val first = request(port, path + "?direction=out&limit=1&edgeTypes=AUTHORED")
      assert(first.statusCode() == 200, first.body())
      assert(json(first)("items").arr.size == 1)
      val cursor = encoded(json(first)("cursor").str)
      val second = request(port, path + s"?direction=out&limit=1&edgeTypes=AUTHORED&cursor=$cursor")
      assert(second.statusCode() == 200, second.body())
      assert(
        (json(first)("items").arr ++ json(second)("items").arr).map(_("nodeId").str).toSet == Set(
          work1,
          work2
        )
      )
      val incoming = request(port, path + "?direction=in")
      assert(incoming.statusCode() == 200 && json(incoming)("items").arr.isEmpty)
      for (
        query <- Vector(
          "depth=4",
          "limit=201",
          "edgeTypes=UNKNOWN",
          "timeoutMs=5001",
          "limit=1&limit=2"
        )
      )
        error(request(port, path + "?" + query), 400)
    }
  }

  test(
    "internal semantic HTTP routes enforce separate auth and reject malformed or over-cap payloads before retrieval"
  ) {
    val calls = new AtomicInteger
    val semantic = new SemanticApi((value, context) => {
      calls.incrementAndGet()
      assert(context.traceId == "trace-independent-10b")
      assert(value("question").str == "synthetic context")
      Right(ujson.Obj("hits" -> ujson.Arr()))
    })
    withServer(new Runtime, semantic = semantic, role = "semantic-service") { port =>
      val path = "/internal/v1/semantic/retrieve"
      val valid = """{"question":"synthetic context","topK":1}"""
      error(request(port, path, Some(valid), auth = None), 401)
      error(request(port, path, Some(valid)), 401)
      for (
        invalid <- Vector(
          "{broken",
          """{"question":"synthetic context","topK":51}""",
          """{"question":"synthetic context","topK":1.5}""",
          """{"question":"synthetic context","filters":[]}"""
        )
      )
        error(request(port, path, Some(invalid), auth = Some(internalKey)), 400)
      val result = request(port, path, Some(valid), auth = Some(internalKey))
      assert(result.statusCode() == 200 && json(result)("hits").arr.isEmpty)
      assert(calls.get == 1)
      assert(request(port, "/healthz", auth = None).statusCode() == 200)
    }
  }

  test("wire graph dependency timeout returns typed 504 with the requesting trace") {
    val delegate = snapshot()
    val slow = new GraphSnapshot {
      def snapshotId = delegate.snapshotId
      def node(id: String): StorageResult[GraphNode] = { Thread.sleep(10000); delegate.node(id) }
      def edges(id: String, window: String) = delegate.edges(id, window)
      def metrics(id: String, window: String) = delegate.metrics(id, window)
    }
    withServer(new Runtime, graph = new GraphApi(slow, GraphApiConfig(timeoutMs = 40))) { port =>
      error(request(port, s"/v1/graph/nodes/$a"), 504)
      assert(request(port, "/healthz", auth = None).statusCode() == 200)
    }
  }

  test(
    "query API proxies graph HTTP through retry and breaker helpers with correlation and metrics"
  ) {
    val attempts = new AtomicInteger
    val local = new GraphApi(snapshot())
    val observing = new GraphEndpoints {
      def node(id: String, context: RequestContext): Either[ApiError, ApiReply] =
        node(id, Map.empty, context)
      override def node(
          id: String,
          params: Map[String, String],
          context: RequestContext
      ): Either[ApiError, ApiReply] = {
        assert(
          context.requestId == "request-independent-10b" && context.traceId == "trace-independent-10b"
        )
        if (attempts.incrementAndGet() < 3) Left(ApiError.downstream)
        else local.node(id, params, context)
      }
      def neighbors(id: String, p: Map[String, String], c: RequestContext) =
        local.neighbors(id, p, c)
      def metrics(id: String, window: String, c: RequestContext) = local.metrics(id, window, c)
      override def metrics(
          id: String,
          window: String,
          params: Map[String, String],
          c: RequestContext
      ) =
        local.metrics(id, window, params, c)
      def paths(p: Map[String, String], c: RequestContext) = local.paths(p, c)
      def close(): Unit = local.close()
    }
    withServer(new Runtime, graph = observing, role = "graph-service") { graphPort =>
      val metrics = new ServiceMetrics
      val remote = new RemoteGraphApi(
        new RemoteService(
          URI.create(s"http://127.0.0.1:$graphPort"),
          internalKey,
          config,
          metrics,
          "graph"
        )
      )
      withServer(new Runtime, graph = remote, metrics = metrics) { queryPort =>
        val result = request(queryPort, s"/v1/graph/nodes/$a")
        assert(result.statusCode() == 200, result.body())
        assert(json(result)("nodeId").str == a)
        assert(attempts.get == 3)
        val page = request(queryPort, s"/v1/graph/nodes/$a/neighbors?direction=out&limit=1")
        assert(page.statusCode() == 200 && json(page)("items").arr.size == 1)
        val measured = request(queryPort, "/metrics")
        assert(measured.statusCode() == 200)
        assert(
          measured
            .body()
            .contains("downstream_circuit_state{dependency=\"graph\",state=\"CLOSED\"} 1")
        )
        assert(measured.body().contains("api_downstream_errors_total 2"))
      }
    }
  }

  test(
    "remote semantic POST forwards correlation, attempts once and exposes its registered breaker"
  ) {
    val attempts = new AtomicInteger
    val failing = new SemanticApi((_, context) => {
      attempts.incrementAndGet()
      assert(
        context.requestId == "request-independent-10b" && context.traceId == "trace-independent-10b"
      )
      Left(ApiError.downstream)
    })
    withServer(new Runtime, semantic = failing, role = "semantic-service") { semanticPort =>
      val metrics = new ServiceMetrics
      val remote = new RemoteSemanticApi(
        new RemoteService(
          URI.create(s"http://127.0.0.1:$semanticPort"),
          internalKey,
          config,
          metrics,
          "semantic"
        )
      )
      withServer(new Runtime, semantic = remote, metrics = metrics) { queryPort =>
        error(
          request(
            queryPort,
            "/internal/v1/semantic/retrieve",
            Some("""{"question":"synthetic context","topK":1}"""),
            auth = Some(internalKey)
          ),
          502
        )
        assert(attempts.get == 1)
        val measured = request(queryPort, "/metrics")
        assert(measured.statusCode() == 200)
        assert(
          measured
            .body()
            .contains("downstream_circuit_state{dependency=\"semantic\",state=\"CLOSED\"} 1")
        )
        assert(measured.body().contains("api_downstream_errors_total 1"))
      }
    }
  }

  test("committed JSON request and response examples agree with actual HTTP contracts") {
    def example(name: String): ujson.Value = ujson.read(
      Files.readString(
        IndependentRuntime9AFixture.root.resolve(
          s"modules/services/src/main/resources/openapi/examples/$name.json"
        )
      )
    )
    val queryExample = example("query-request")
    val semanticExample = example("semantic-request")
    val errorExample = example("error")
    val graphExample = example("graph-page")
    val jobExample = example("job-reference")
    assert(jobExample("queryId").str.matches("qry-[0-9a-f]{64}"))
    assert(jobExample("jobId").str.matches("job-[0-9a-f]{64}"))
    assert(jobExample("statusUrl").str == "/v1/jobs/" + jobExample("jobId").str)
    assert(Set("QUEUED", "RUNNING")(jobExample("status").str))
    assert(jobExample("mode").str == "asynchronous")
    val calls = new AtomicInteger
    val semantic = new SemanticApi((value, _) => {
      calls.incrementAndGet()
      assert(value == semanticExample)
      Right(ujson.Obj("hits" -> ujson.Arr()))
    })
    val runtime = new Runtime(queryExample("question").str)
    withServer(runtime, semantic = semantic) { port =>
      val query =
        request(port, "/v1/query", Some(queryExample.render()), key = Some("example-query-10b"))
      assert(query.statusCode() == 200, query.body())
      assert(json(query)("claims").arr.nonEmpty)
      assert(json(query)("answer")("summary").str.contains("3"))
      val result = request(
        port,
        "/internal/v1/semantic/retrieve",
        Some(semanticExample.render()),
        auth = Some(internalKey)
      )
      assert(result.statusCode() == 200 && json(result)("hits").arr.isEmpty)
      assert(calls.get == 1 && runtime.modelCalls.get == 1)
      val missing = request(port, "/v1/evidence/missing")
      error(missing, 404)
      errorExample("traceId") = "trace-independent-10b"
      assert(json(missing) == errorExample)
      val incoming = request(port, s"/v1/graph/nodes/$a/neighbors?direction=in")
      assert(incoming.statusCode() == 200, incoming.body())
      val actual = json(incoming)
      assert(actual.obj.keySet == graphExample.obj.keySet)
      assert(actual("nodeId").str == a && actual("snapshot").str == snapshot().snapshotId)
      assert(actual("items") == graphExample("items") && actual("cursor") == graphExample("cursor"))
      assert(actual("depth") == graphExample("depth"))
      assert(actual("direction").str == "in")
    }
  }
}
