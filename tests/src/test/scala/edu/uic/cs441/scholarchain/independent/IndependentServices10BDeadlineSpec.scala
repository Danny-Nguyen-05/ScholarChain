package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.net.{InetAddress, ServerSocket, Socket, SocketException, URI}
import java.net.http.HttpResponse
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.{AtomicBoolean, AtomicInteger}
import org.scalatest.funsuite.AnyFunSuite

/** Request-budget exhaustion is a completed application response from a healthy dependency.
  * Connection failures, silence and unavailable responses remain dependency failures.
  */
class IndependentServices10BDeadlineSpec extends AnyFunSuite {
  import IndependentServices10BFixture.{config as baseConfig, *}
  private val nodeId = "synthetic-deadline-node"
  private val cfg = baseConfig.copy(
    downstreamTimeoutMs = 1000,
    downstreamMaxAttempts = 3,
    breakerFailureThreshold = 3,
    breakerResetMs = 30000
  )
  private val context = RequestContext("request-readiness-10b", "trace-readiness-10b")
  private def json(response: HttpResponse[String]): ujson.Value = ujson.read(response.body())
  private def closed(metrics: String): Boolean =
    metrics.contains("downstream_circuit_state{dependency=\"graph\",state=\"CLOSED\"} 1")
  private def open(metrics: String): Boolean =
    metrics.contains("downstream_circuit_state{dependency=\"graph\",state=\"OPEN\"} 1")
  private def traced(response: HttpResponse[String], status: Int, trace: String): Unit = {
    assert(response.statusCode() == status, response.body())
    assert(json(response)("traceId").str == trace)
    assert(response.headers().firstValue("X-Trace-Id").orElse("") == trace)
    assert(json(response)("error").str.nonEmpty)
    assert(!response.body().contains(externalKey) && !response.body().contains(internalKey))
  }
  private def start(
      graph: GraphEndpoints,
      role: String,
      ready: () => Boolean,
      config: ServiceConfig = cfg,
      metrics: ServiceMetrics = new ServiceMetrics
  ): ApiServer.RunningServer = {
    val workflow = new QueryWorkflow {
      def run(
          r: QueryRequest,
          c: RequestContext,
          stage: String => Unit
      ): Either[ApiError, WorkflowOutput] =
        Left(ApiError.unavailable)
    }
    val queries = new QueryService(new InMemoryQuerySessionStore, workflow, config, metrics)
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
  private def withProxy(uri: URI, config: ServiceConfig = cfg)(check: Int => Unit): Unit = {
    val metrics = new ServiceMetrics
    val remote = new RemoteGraphApi(new RemoteService(uri, internalKey, config, metrics, "graph"))
    val server = start(remote, "query-api", () => remote.ready(context), config, metrics)
    try check(server.port)
    finally server.close()
  }
  private final class StubGraph(unavailable: Boolean = false) extends GraphEndpoints {
    val neighborCalls = new AtomicInteger
    val nodeCalls = new AtomicInteger
    def node(id: String, c: RequestContext): Either[ApiError, ApiReply] = {
      nodeCalls.incrementAndGet()
      if (unavailable) Left(ApiError.unavailable)
      else
        Right(ApiReply(200, ujson.Obj("nodeId" -> id, "snapshot" -> "synthetic-deadline-snapshot")))
    }
    override def node(
        id: String,
        params: Map[String, String],
        c: RequestContext
    ): Either[ApiError, ApiReply] =
      node(id, c)
    def neighbors(
        id: String,
        p: Map[String, String],
        c: RequestContext
    ): Either[ApiError, ApiReply] = {
      neighborCalls.incrementAndGet()
      if (unavailable) Left(ApiError.unavailable)
      else if (p.get("timeoutMs").contains("1"))
        Left(ApiError(504, "GRAPH_DEADLINE_EXCEEDED", "Graph request deadline exceeded.", false))
      else
        Right(
          ApiReply(200, ujson.Obj("nodeId" -> id, "items" -> ujson.Arr(), "cursor" -> ujson.Null))
        )
    }
    def metrics(id: String, window: String, c: RequestContext) = node(id, c)
    override def metrics(
        id: String,
        window: String,
        params: Map[String, String],
        c: RequestContext
    ) =
      node(id, c)
    def paths(p: Map[String, String], c: RequestContext) = node(nodeId, c)
    def close(): Unit = ()
  }

  test(
    "graph request deadline 504 never retries, opens the dependency breaker or fails query readiness"
  ) {
    val graph = new StubGraph
    val backend = start(graph, "graph-service", () => true)
    try
      withProxy(URI.create(s"http://127.0.0.1:${backend.port}")) { port =>
        val observed = Vector.tabulate(cfg.breakerFailureThreshold + 1) { index =>
          val trace = s"trace-graph-deadline-$index"
          val response =
            request(port, s"/v1/graph/nodes/$nodeId/neighbors?timeoutMs=1", trace = trace)
          (response, trace)
        }
        assert(
          graph.neighborCalls.get == observed.size,
          s"Each exhausted request must execute once; ${observed.size} requests caused ${graph.neighborCalls.get} backend calls"
        )
        observed.foreach { (response, trace) =>
          traced(response, 504, trace)
          assert(json(response)("error").str == "GRAPH_DEADLINE_EXCEEDED")
          assert(!json(response)("retryable").bool)
        }
        // No successful downstream/readiness call may reset the breaker between deadlines.
        assert(closed(request(port, "/metrics").body()))
        observed.foreach { _ =>
          val ready = request(port, "/readyz", auth = None)
          assert(ready.statusCode() == 200, ready.body())
        }
        val node = request(port, s"/v1/graph/nodes/$nodeId")
        val neighbors = request(port, s"/v1/graph/nodes/$nodeId/neighbors")
        assert(node.statusCode() == 200 && json(node)("nodeId").str == nodeId)
        assert(neighbors.statusCode() == 200 && json(neighbors)("items").arr.isEmpty)
        assert(graph.neighborCalls.get == observed.size + 1)
        assert(closed(request(port, "/metrics").body()))
        assert(request(port, "/readyz", auth = None).statusCode() == 200)
      }
    finally backend.close()
  }

  test(
    "connection refusal remains a dependency failure that opens the graph breaker and fails readiness"
  ) {
    val reserved = new ServerSocket(0, 1, InetAddress.getLoopbackAddress)
    val port = reserved.getLocalPort
    reserved.close()
    withProxy(URI.create(s"http://127.0.0.1:$port")) { queryPort =>
      val response = request(queryPort, s"/v1/graph/nodes/$nodeId", trace = "trace-refused-10b")
      traced(response, 502, "trace-refused-10b")
      assert(open(request(queryPort, "/metrics").body()))
      traced(request(queryPort, "/readyz", auth = None), 503, "trace-independent-10b")
      val refused = request(queryPort, s"/v1/graph/nodes/$nodeId")
      traced(refused, 503, "trace-independent-10b")
      assert(json(refused)("error").str == "CIRCUIT_OPEN")
    }
  }

  test("client timeout without any HTTP response remains a breaker failure and fails readiness") {
    val sockets = new ConcurrentLinkedQueue[Socket]
    val accepting = new AtomicBoolean(true)
    val listener = new ServerSocket(0, 10, InetAddress.getLoopbackAddress)
    val accepted = new AtomicInteger
    val thread = new Thread(
      () => {
        try
          while (accepting.get) {
            val socket = listener.accept()
            sockets.add(socket)
            accepted.incrementAndGet()
          }
        catch { case _: SocketException if !accepting.get => () }
      },
      "synthetic-silent-http-10b"
    )
    thread.setDaemon(true)
    thread.start()
    try
      withProxy(
        URI.create(s"http://127.0.0.1:${listener.getLocalPort}"),
        cfg.copy(downstreamTimeoutMs = 150)
      ) { port =>
        traced(
          request(port, s"/v1/graph/nodes/$nodeId", trace = "trace-silent-10b"),
          504,
          "trace-silent-10b"
        )
        assert(accepted.get >= 1)
        assert(open(request(port, "/metrics").body()))
        traced(request(port, "/readyz", auth = None), 503, "trace-independent-10b")
        val before = accepted.get
        traced(request(port, s"/v1/graph/nodes/$nodeId"), 503, "trace-independent-10b")
        assert(accepted.get == before)
      }
    finally {
      accepting.set(false)
      listener.close()
      val iterator = sockets.iterator()
      while (iterator.hasNext) iterator.next().close()
      thread.join(2000)
      assert(!thread.isAlive)
    }
  }

  test(
    "an unready graph service 503 is retried to threshold, opens the breaker and fails query readiness"
  ) {
    val graph = new StubGraph(unavailable = true)
    val backend = start(graph, "graph-service", () => false)
    try
      withProxy(URI.create(s"http://127.0.0.1:${backend.port}")) { port =>
        traced(
          request(port, s"/v1/graph/nodes/$nodeId/neighbors", trace = "trace-unready-10b"),
          503,
          "trace-unready-10b"
        )
        assert(graph.neighborCalls.get == cfg.breakerFailureThreshold)
        assert(open(request(port, "/metrics").body()))
        traced(request(port, "/readyz", auth = None), 503, "trace-independent-10b")
        val before = graph.neighborCalls.get
        val refused = request(port, s"/v1/graph/nodes/$nodeId/neighbors")
        traced(refused, 503, "trace-independent-10b")
        assert(json(refused)("error").str == "CIRCUIT_OPEN")
        assert(graph.neighborCalls.get == before)
      }
    finally backend.close()
  }
}
