package edu.uic.cs441.scholarchain.services

import org.scalatest.funsuite.AnyFunSuite
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.AtomicInteger

class ServiceFoundationSpec extends AnyFunSuite {
  private def config = ServiceConfig(
    Auth.sha256("synthetic-api-key"),
    Auth.sha256("synthetic-service-token"),
    synchronousDeadlineMs = 100,
    workflowTimeoutMs = 500,
    maxWorkflowRetries = 0
  )
  private val headers =
    Map("Authorization" -> "Bearer synthetic-api-key", "Idempotency-Key" -> "synthetic-key")
  private def workflow(
      body: (QueryRequest, RequestContext, String => Unit) => Either[ApiError, WorkflowOutput]
  ) = new QueryWorkflow {
    def run(r: QueryRequest, c: RequestContext, s: String => Unit) = body(r, c, s)
  }
  private def withApp(f: ApiApplication => Unit): Unit = {
    val q = new QueryService(
      new InMemoryQuerySessionStore,
      workflow((_, _, _) =>
        Right(
          WorkflowOutput(
            ujson.Obj("summary" -> "Synthetic fixture answer", "researchers" -> ujson.Arr())
          )
        )
      ),
      config
    )
    val app = new ApiApplication(q, config, logSink = _ => ())
    try f(app)
    finally app.close()
  }
  test("request validation rejects malformed JSON and wrong field types") {
    assert(QueryRequest.parse("{", config).left.toOption.get.status == 400)
    assert(QueryRequest.parse("{\"question\":17}", config).left.toOption.get.status == 400)
    assert(
      QueryRequest
        .parse("{\"question\":\"x\",\"analysis\":{\"includePaths\":\"true\"}}", config)
        .left
        .toOption
        .get
        .status == 400
    )
  }
  test("request validation rejects unsupported fields, bounds and ranking metric") {
    for (
      s <- Vector(
        "{\"constraints\":{\"language\":\"en\"}}",
        "{\"retrieval\":{\"graphLimit\":101}}",
        "{\"analysis\":{\"rankingMetric\":\"INVENTED\"}}"
      )
    ) {
      val obj = ujson.read(s); obj("question") = "x"
      assert(QueryRequest.parse(obj.render(), config).left.toOption.get.status == 422)
    }
  }
  test("canonical fingerprints ignore object key order but bind field values") {
    val a = QueryRequest
      .parse("{\"question\":\"x\",\"retrieval\":{\"graphLimit\":1,\"vectorLimit\":2}}", config)
      .toOption
      .get
    val b = QueryRequest
      .parse("{\"retrieval\":{\"vectorLimit\":2,\"graphLimit\":1},\"question\":\"x\"}", config)
      .toOption
      .get
    val c = QueryRequest
      .parse("{\"question\":\"y\",\"retrieval\":{\"graphLimit\":1,\"vectorLimit\":2}}", config)
      .toOption
      .get
    assert(QueryRequest.fingerprint(a) == QueryRequest.fingerprint(b))
    assert(QueryRequest.fingerprint(a) != QueryRequest.fingerprint(c))
  }
  test("authentication domains are separate with no usable default credentials") {
    assert(ServiceConfig.fromEnvironment(Map.empty).isLeft)
    assert(Auth.authorized(Some("Bearer synthetic-api-key"), config.apiKeySha256))
    assert(!Auth.authorized(Some("Bearer synthetic-api-key"), config.internalTokenSha256))
    assert(!Auth.authorized(None, config.apiKeySha256))
  }
  test("safe IDs replace control characters and all error paths carry a trace") {
    withApp { app =>
      val r = app.handle("GET", "/unknown/private", Map("X-Trace-Id" -> "secret\r\nattack"), "")
      assert(r.status == 401)
      val json = ujson.read(r.body)
      assert(json("traceId").str.startsWith("trace-"))
      assert(!r.body.contains("secret"))
      assert(r.headers("X-Trace-Id") == json("traceId").str)
    }
  }
  test("metrics require authentication and have derivable latency histogram") {
    withApp { app =>
      assert(app.handle("GET", "/metrics", Map.empty, "").status == 401)
      val r = app.handle("GET", "/metrics", headers, "")
      assert(r.status == 200)
      assert(r.body.contains("api_latency_seconds_bucket{le=\"+Inf\"}"))
      assert(r.body.contains("api_status_total{status=\"401\"} 1"))
    }
  }
  test("safe log construction excludes headers, body and raw route IDs") {
    var lines = Vector.empty[String]
    val q = new QueryService(
      new InMemoryQuerySessionStore,
      workflow((_, _, _) => Left(ApiError.unsupported)),
      config
    )
    val app = new ApiApplication(q, config, logSink = s => lines :+= s)
    try {
      app.handle("POST", "/v1/query", headers, "{\"question\":\"sensitive raw question\"}")
      app.handle("GET", "/unknown/sensitive-node", headers, "")
      assert(lines.size == 2)
      assert(!lines.mkString.contains("synthetic-api-key"))
      assert(!lines.mkString.contains("sensitive"))
      assert(
        lines.forall(s =>
          ujson.read(s).obj.keySet == Set(
            "event",
            "requestId",
            "traceId",
            "route",
            "status",
            "elapsedMs"
          )
        )
      )
    } finally app.close()
  }
  test("completed query replay survives a second service instance and never reruns workflow") {
    val store = new InMemoryQuerySessionStore
    val calls = new AtomicInteger
    val wf = workflow((_, _, _) => {
      calls.incrementAndGet(); Right(WorkflowOutput(ujson.Obj("summary" -> "synthetic")))
    })
    val request = QueryRequest.parse("{\"question\":\"x\"}", config).toOption.get
    val first = new QueryService(store, wf, config)
    val original =
      try first.submit(request, "durable-key", RequestContext("req", "trace")).toOption.get
      finally first.close()
    val second = new QueryService(store, wf, config)
    try {
      val replay =
        second.submit(request, "durable-key", RequestContext("req2", "trace2")).toOption.get
      assert(replay.status == 200 && original.body == replay.body)
      assert(calls.get() == 1)
    } finally second.close()
  }
  test("workflow wall clock timeout is enforced and persisted as a typed terminal failure") {
    val cfg = config.copy(synchronousDeadlineMs = 10, workflowTimeoutMs = 50)
    val q = new QueryService(
      new InMemoryQuerySessionStore,
      workflow((_, _, _) => { Thread.sleep(10000); Right(WorkflowOutput(ujson.Obj())) }),
      cfg
    )
    try {
      val request = QueryRequest.parse("{\"question\":\"x\"}", cfg).toOption.get
      val initial = q.submit(request, "timeout-key", RequestContext("req", "trace")).toOption.get
      assert(initial.status == 202)
      val until = System.nanoTime() + 1000000000L
      var r = q.result(initial.body("jobId").str)
      while (r.exists(_.status == 202) && System.nanoTime() < until) {
        Thread.sleep(5); r = q.result(initial.body("jobId").str)
      }
      assert(r.left.toOption.get.status == 504)
      assert(q.job(initial.body("jobId").str).toOption.get.body("state").str == "FAILED")
    } finally q.close()
  }
  test("workflow retry is bounded and terminal replay cannot trigger another attempt") {
    val calls = new AtomicInteger
    val cfg = config.copy(maxWorkflowRetries = 2)
    val q = new QueryService(
      new InMemoryQuerySessionStore,
      workflow((_, _, _) => { calls.incrementAndGet(); Left(ApiError.downstream) }),
      cfg
    )
    try {
      val req = QueryRequest.parse("{\"question\":\"x\"}", cfg).toOption.get
      assert(q.submit(req, "failed-key", RequestContext("r", "t")).left.toOption.get.status == 502)
      assert(q.submit(req, "failed-key", RequestContext("r2", "t2")).isLeft)
      assert(calls.get() == 3)
    } finally q.close()
  }
  test("verification and abstention metrics preserve closed labels") {
    val m = new ServiceMetrics
    m.workflow("ABSTAINED", true); m.workflow("untrusted-label", false)
    assert(m.render.contains("workflow_abstentions_total 1"))
    assert(m.render.contains("workflow_verification_total{status=\"ABSTAINED\"} 1"))
    assert(!m.render.contains("untrusted-label"))
  }
  test("configuration rejects identical auth domains and externalizes application bounds") {
    intercept[IllegalArgumentException](config.copy(internalTokenSha256 = config.apiKeySha256))
    val env = Map(
      "SCHOLARCHAIN_API_KEY_SHA256" -> config.apiKeySha256,
      "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> config.internalTokenSha256,
      "SCHOLARCHAIN_MAX_GRAPH_LIMIT" -> "7"
    )
    assert(ServiceConfig.fromEnvironment(env).toOption.get.maxGraphLimit == 7)
  }
}
