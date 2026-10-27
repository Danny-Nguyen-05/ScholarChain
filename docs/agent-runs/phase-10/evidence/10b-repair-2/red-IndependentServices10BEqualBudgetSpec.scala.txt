package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.net.{URI, URLEncoder}
import java.net.http.HttpResponse
import java.util.concurrent.atomic.{AtomicBoolean, AtomicInteger}
import org.scalatest.funsuite.AnyFunSuite

/** Exercises the real graph execution timer and both HTTP layers, rather than a stub deadline
  * marker.
  */
class IndependentServices10BEqualBudgetSpec extends AnyFunSuite {
  import IndependentServices10BFixture.{config as baseConfig, *}
  private val config = baseConfig.copy(
    downstreamTimeoutMs = 300,
    downstreamMaxAttempts = 3,
    breakerFailureThreshold = 3,
    breakerResetMs = 30000
  )
  private val graphConfig =
    GraphApiConfig(timeoutMs = 300, cursorKey = "synthetic-equal-budget-cursor-key")
  private val readyContext =
    RequestContext("request-equal-budget-readiness", "trace-equal-budget-readiness")
  private def json(response: HttpResponse[String]): ujson.Value = ujson.read(response.body())
  private def closed(port: Int): Unit = {
    val response = request(port, "/metrics")
    assert(response.statusCode() == 200, response.body())
    assert(
      response.body().contains("downstream_circuit_state{dependency=\"graph\",state=\"CLOSED\"} 1"),
      response.body()
    )
  }
  private final class BlockingSnapshot extends GraphSnapshot {
    private val delegate = snapshot()
    val blocking = new AtomicBoolean(true)
    val executions = new AtomicInteger
    def snapshotId: String = delegate.snapshotId
    def node(id: String): StorageResult[GraphNode] = delegate.node(id)
    def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] = {
      executions.incrementAndGet()
      if (blocking.get) Thread.sleep(10000)
      delegate.edges(id, window)
    }
    def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord] =
      delegate.metrics(id, window)
  }
  private def start(
      graph: GraphEndpoints,
      role: String,
      ready: () => Boolean,
      metrics: ServiceMetrics
  ): ApiServer.RunningServer = {
    val unused = new QueryWorkflow {
      def run(
          r: QueryRequest,
          c: RequestContext,
          stage: String => Unit
      ): Either[ApiError, WorkflowOutput] =
        Left(ApiError.unavailable)
    }
    val queries = new QueryService(new InMemoryQuerySessionStore, unused, config, metrics)
    val extended = ExtendedApi(
      new EvidenceApi(new InMemoryIndexedEvidenceBundleStore, new InMemoryRuntimeAuditStore),
      graph,
      new SemanticApi((_, _) => Right(ujson.Obj("hits" -> ujson.Arr())))
    )
    ApiServer.start(
      new ApiApplication(
        queries,
        config,
        readiness = ready,
        logSink = _ => (),
        serviceRole = role,
        extended = Some(extended)
      ),
      port = 0
    )
  }
  private def withServers(source: GraphSnapshot)(check: Int => Unit): Unit = {
    val backend =
      start(new GraphApi(source, graphConfig), "graph-service", () => true, new ServiceMetrics)
    val metrics = new ServiceMetrics
    val remote = new RemoteGraphApi(
      new RemoteService(
        URI.create(s"http://127.0.0.1:${backend.port}"),
        internalKey,
        config,
        metrics,
        "graph"
      )
    )
    val proxy = start(remote, "query-api", () => remote.ready(readyContext), metrics)
    try check(proxy.port)
    finally { proxy.close(); backend.close() }
  }
  private def deadlineBurst(params: String): Unit = {
    val source = new BlockingSnapshot
    withServers(source) { port =>
      val responses = Vector.tabulate(config.breakerFailureThreshold + 1) { index =>
        val trace = s"trace-equal-budget-$index"
        (request(port, s"/v1/graph/nodes/$a/neighbors$params", trace = trace), trace)
      }
      // Readiness calls would reset consecutive failures, so do not probe until after this burst.
      assert(
        source.executions.get == responses.size,
        s"${responses.size} graph deadlines caused ${source.executions.get} snapshot executions"
      )
      responses.foreach { (response, trace) =>
        assert(response.statusCode() == 504, response.body())
        assert(json(response)("error").str == "GRAPH_DEADLINE_EXCEEDED", response.body())
        assert(!json(response)("retryable").bool)
        assert(json(response)("traceId").str == trace)
        assert(response.headers().firstValue("X-Trace-Id").orElse("") == trace)
      }
      closed(port)
      assert(request(port, "/readyz", auth = None).statusCode() == 200)
      source.blocking.set(false)
      val node = request(port, s"/v1/graph/nodes/$a")
      val normal = request(port, s"/v1/graph/nodes/$a/neighbors")
      assert(node.statusCode() == 200 && json(node)("nodeId").str == a, node.body())
      assert(normal.statusCode() == 200 && json(normal)("items").arr.nonEmpty, normal.body())
      assert(source.executions.get == responses.size + 1)
      closed(port)
      assert(request(port, "/readyz", auth = None).statusCode() == 200)
    }
  }

  test(
    "equal graph and transport budgets return graph deadlines once each when caller timeout is omitted"
  ) {
    deadlineBurst("")
  }

  test(
    "explicit graph timeout at the transport cap leaves enough response budget and never trips the breaker"
  ) {
    deadlineBurst("?timeoutMs=300")
  }

  test("deterministic forwarded graph budgets keep snapshot cursor replay stable") {
    withServers(snapshot()) { port =>
      for (extra <- Vector("", "&timeoutMs=300")) {
        val path = s"/v1/graph/nodes/$a/neighbors?direction=out&limit=1$extra"
        val first = request(port, path)
        assert(first.statusCode() == 200, first.body())
        assert(json(first)("items").arr.size == 1)
        val cursor = URLEncoder.encode(json(first)("cursor").str, "UTF-8")
        val next = request(port, path + "&cursor=" + cursor)
        val replay = request(port, path + "&cursor=" + cursor)
        assert(next.statusCode() == 200 && replay.statusCode() == 200, next.body() + replay.body())
        assert(json(next) == json(replay))
        assert(json(next)("cursor") == ujson.Null)
        assert(
          (json(first)("items").arr ++ json(next)("items").arr).map(_("nodeId").str).toSet == Set(
            work1,
            work2
          )
        )
      }
      closed(port)
      assert(request(port, "/readyz", auth = None).statusCode() == 200)
    }
  }
}
