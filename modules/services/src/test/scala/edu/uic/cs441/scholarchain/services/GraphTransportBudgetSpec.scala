package edu.uic.cs441.scholarchain.services

import com.sun.net.httpserver.HttpServer
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import edu.uic.cs441.scholarchain.core.{GraphNode, GraphEdge}
import java.net.{InetSocketAddress, URI}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{Executors, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class GraphTransportBudgetSpec extends AnyFunSuite {
  private val context = RequestContext("synthetic-budget-request", "synthetic-budget-trace")
  private def config = ServiceConfig(
    Auth.sha256("synthetic-budget-public"),
    Auth.sha256("synthetic-budget-internal"),
    downstreamTimeoutMs = 300,
    downstreamMaxAttempts = 3,
    breakerFailureThreshold = 3
  )
  private val operations = Vector(
    "/internal/v1/graph/nodes/synthetic-node",
    "/internal/v1/graph/nodes/synthetic-node/neighbors",
    "/internal/v1/graph/metrics/synthetic-node",
    "/internal/v1/graph/paths"
  )
  private def withStub[A](body: (URI, () => Vector[Map[String, String]]) => A): A = {
    var seen = Vector.empty[Map[String, String]]
    val server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    val executor = Executors.newSingleThreadExecutor()
    server.setExecutor(executor)
    server.createContext(
      "/",
      exchange => {
        val params = QueryParameters.parse(exchange.getRequestURI.toString).toOption.get
        synchronized { seen :+= params }
        val bytes = "{}".getBytes(UTF_8)
        try {
          exchange.sendResponseHeaders(200, bytes.length); exchange.getResponseBody.write(bytes)
        } finally exchange.close()
      }
    )
    server.start()
    try
      body(URI.create("http://127.0.0.1:" + server.getAddress.getPort), () => synchronized { seen })
    finally {
      server.stop(0); executor.shutdownNow(); executor.awaitTermination(2, TimeUnit.SECONDS)
    }
  }
  test(
    "every graph operation forwards a deterministic budget below transport for absent and near-cap requests"
  ) {
    withStub { (uri, seen) =>
      val remote =
        new RemoteService(uri, "synthetic-budget-token", config, new ServiceMetrics, "graph")
      try {
        for (
          path <- operations;
          caller <- Vector(
            Map.empty[String, String],
            Map("timeoutMs" -> "300"),
            Map("timeoutMs" -> "1")
          )
        ) {
          assert(remote.call("GET", path, caller, None, context).isRight)
          val forwarded = seen().last
            .getOrElse("timeoutMs", fail(s"No explicit execution budget on $path"))
            .toLong
          assert(forwarded == (if (caller.get("timeoutMs").contains("1")) 1L else 225L))
          assert(forwarded > 0 && forwarded < config.downstreamTimeoutMs)
        }
        val original = Map("timeoutMs" -> "300", "cursor" -> "synthetic-cursor", "depth" -> "2")
        assert(remote.call("GET", operations(1), original, None, context).isRight)
        val first = seen().last
        assert(remote.call("GET", operations(1), original, None, context).isRight)
        assert(seen().last == first)
        assert(first("cursor") == "synthetic-cursor" && first("depth") == "2")
      } finally remote.close()
    }
  }
  test(
    "graph budget configuration rejects invalid reserves or caps and impossible tiny transports"
  ) {
    val base = Map(
      "SCHOLARCHAIN_API_KEY_SHA256" -> config.apiKeySha256,
      "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> config.internalTokenSha256
    )
    for (
      extra <- Vector(
        Map("SCHOLARCHAIN_GRAPH_DEADLINE_RESERVE_PERCENT" -> "0"),
        Map("SCHOLARCHAIN_GRAPH_DEADLINE_RESERVE_PERCENT" -> "100"),
        Map("SCHOLARCHAIN_GRAPH_TIMEOUT_MS" -> "0")
      )
    ) {
      assert(ServiceConfig.fromEnvironment(base ++ extra).isLeft)
    }
    intercept[IllegalArgumentException] {
      new RemoteService(
        URI.create("http://127.0.0.1:1"),
        "synthetic-budget-token",
        config.copy(downstreamTimeoutMs = 1),
        new ServiceMetrics,
        "graph"
      )
    }
  }
  test("malformed and out-of-cap caller budgets reject before any backend call") {
    withStub { (uri, seen) =>
      val remote =
        new RemoteService(uri, "synthetic-budget-token", config, new ServiceMetrics, "graph")
      try {
        for (value <- Vector("0", "-1", "not-a-number", "5001")) {
          assert(
            remote
              .call("GET", operations(1), Map("timeoutMs" -> value), None, context)
              .left
              .toOption
              .exists(_.status == 400)
          )
        }
        assert(seen().isEmpty)
      } finally remote.close()
    }
  }
  test("equal graph and transport caps yield a graph marker with no retries or readiness loss") {
    val cfg = config.copy(downstreamTimeoutMs = 300)
    val calls = new AtomicInteger
    val graph = new GraphApi(
      new GraphSnapshot {
        def snapshotId = "synthetic-equal-budget"
        def node(id: String): StorageResult[GraphNode] = {
          calls.incrementAndGet(); Thread.sleep(10000); StorageResult.Missing
        }
        def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] =
          StorageResult.Found(Vector.empty)
        def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord] = {
          calls.incrementAndGet(); Thread.sleep(10000); StorageResult.Missing
        }
      },
      GraphApiConfig(timeoutMs = 300)
    )
    val workflow = new QueryWorkflow {
      def run(
          r: QueryRequest,
          c: RequestContext,
          s: String => Unit
      ): Either[ApiError, WorkflowOutput] = Left(ApiError.unsupported)
    }
    val queries = new QueryService(new InMemoryQuerySessionStore, workflow, cfg)
    val app = new ApiApplication(
      queries,
      cfg,
      logSink = _ => (),
      serviceRole = "graph-service",
      extended = Some(
        ExtendedApi(
          new EvidenceApi(new InMemoryIndexedEvidenceBundleStore, new InMemoryRuntimeAuditStore),
          graph,
          new SemanticApi((_, _) => Right(ujson.Obj("hits" -> ujson.Arr())))
        )
      )
    )
    val server = ApiServer.start(app)
    val metrics = new ServiceMetrics
    val remote = new RemoteService(
      URI.create("http://127.0.0.1:" + server.port),
      "synthetic-budget-internal",
      cfg,
      metrics,
      "graph"
    )
    try {
      for (_ <- 1 to 4) {
        val error = remote.call("GET", operations(1), Map.empty, None, context).left.toOption.get
        assert(error.status == 504 && error.code == "GRAPH_DEADLINE_EXCEEDED" && !error.retryable)
      }
      assert(calls.get() == 4)
      assert(
        metrics.render.contains("downstream_circuit_state{dependency=\"graph\",state=\"CLOSED\"} 1")
      )
      assert(new RemoteGraphApi(remote).ready(context))
      for (
        (operation, params) <- Vector(
          operations.head -> Map.empty[String, String],
          operations(2) -> Map("window" -> "all-years"),
          operations(3) -> Map(
            "from" -> "synthetic-node",
            "to" -> "synthetic-other",
            "maxDepth" -> "1"
          )
        )
      ) {
        val error = remote.call("GET", operation, params, None, context).left.toOption.get
        assert(error.status == 504 && error.code == "GRAPH_DEADLINE_EXCEEDED" && !error.retryable)
      }
      assert(calls.get() == 7)
    } finally { remote.close(); server.close() }
  }
  test("configured reserve and graph cap are applied rather than a hardcoded default") {
    val env = Map(
      "SCHOLARCHAIN_API_KEY_SHA256" -> config.apiKeySha256,
      "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> config.internalTokenSha256,
      "SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS" -> "400",
      "SCHOLARCHAIN_GRAPH_DEADLINE_RESERVE_PERCENT" -> "50",
      "SCHOLARCHAIN_GRAPH_TIMEOUT_MS" -> "100"
    )
    withStub { (uri, seen) =>
      val capped = ServiceConfig.fromEnvironment(env).toOption.get
      val remote =
        new RemoteService(uri, "synthetic-budget-token", capped, new ServiceMetrics, "graph")
      try {
        assert(remote.call("GET", operations.head, Map.empty, None, context).isRight)
        assert(seen().last("timeoutMs") == "100")
        assert(
          remote
            .call("GET", operations.head, Map("timeoutMs" -> "101"), None, context)
            .left
            .toOption
            .exists(_.status == 400)
        )
      } finally remote.close()
      val reserved = ServiceConfig
        .fromEnvironment(env.updated("SCHOLARCHAIN_GRAPH_TIMEOUT_MS", "500"))
        .toOption
        .get
      val second =
        new RemoteService(uri, "synthetic-budget-token", reserved, new ServiceMetrics, "graph")
      try {
        assert(second.call("GET", operations.head, Map.empty, None, context).isRight)
        assert(seen().last("timeoutMs") == "200")
      } finally second.close()
      val tiny = new RemoteService(
        uri,
        "synthetic-budget-token",
        config.copy(downstreamTimeoutMs = 2),
        new ServiceMetrics,
        "graph"
      )
      tiny.close()
      intercept[IllegalArgumentException] {
        new RemoteService(
          uri,
          "synthetic-budget-token",
          config.copy(downstreamTimeoutMs = 2, graphDeadlineReservePercent = 99),
          new ServiceMetrics,
          "graph"
        )
      }
      val large = new RemoteService(
        uri,
        "synthetic-budget-token",
        config.copy(downstreamTimeoutMs = Long.MaxValue),
        new ServiceMetrics,
        "graph"
      )
      large.close()
    }
  }

}
