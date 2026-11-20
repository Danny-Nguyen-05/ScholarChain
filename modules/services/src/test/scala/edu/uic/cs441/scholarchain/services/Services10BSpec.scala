package edu.uic.cs441.scholarchain.services

import org.scalatest.funsuite.AnyFunSuite
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.core.*
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong}

class Services10BSpec extends AnyFunSuite {
  private def config = ServiceConfig(
    Auth.sha256("synthetic-10b-public"),
    Auth.sha256("synthetic-10b-internal"),
    synchronousDeadlineMs = 10,
    workflowTimeoutMs = 2000,
    maxWorkflowRetries = 0,
    workerThreads = 1,
    queueCapacity = 1,
    sessionPollMs = 1
  )
  private val request =
    QueryRequest.parse("{\"question\":\"Synthetic queue question\"}", config).toOption.get
  private val context = RequestContext("req-synthetic", "trace-synthetic")
  test("failed half-open probe reopens the dependency circuit and rejects the next read") {
    val time = new AtomicLong(0)
    val breaker = new CircuitBreaker(1, 10, () => time.get())
    val client = new DownstreamClient(config.copy(downstreamMaxAttempts = 1), breaker)
    val calls = new AtomicInteger
    try {
      def fail = client.call[String]("GET", context)(_ => {
        calls.incrementAndGet(); Left(ApiError.downstream)
      })
      assert(fail.isLeft); assert(breaker.state == "OPEN")
      time.set(10000000L)
      assert(fail.isLeft); assert(breaker.state == "OPEN")
      assert(fail.left.toOption.get.code == "CIRCUIT_OPEN")
      assert(calls.get() == 2)
    } finally client.close()
  }
  test("full local queue persists a terminal nonretryable429 and never executes the refused work") {
    val release = new CountDownLatch(1); val entered = new CountDownLatch(1);
    val calls = new AtomicInteger
    val workflow = new QueryWorkflow {
      def run(
          r: QueryRequest,
          c: RequestContext,
          s: String => Unit
      ): Either[ApiError, WorkflowOutput] = {
        calls.incrementAndGet(); entered.countDown(); release.await(2, TimeUnit.SECONDS);
        Right(WorkflowOutput(ujson.Obj("summary" -> "synthetic")))
      }
    }
    val service = new QueryService(new InMemoryQuerySessionStore, workflow, config)
    try {
      assert(service.submit(request, "first", context).toOption.get.status == 202)
      assert(entered.await(1, TimeUnit.SECONDS))
      assert(service.submit(request, "second", context).toOption.get.status == 202)
      val rejected = service.submit(request, "third", context).left.toOption.get
      assert(rejected.status == 429 && !rejected.retryable)
      assert(service.submit(request, "third", context).left.toOption.get == rejected)
      assert(calls.get() == 1)
    } finally { release.countDown(); service.close() }
  }
  test("oversized workflow result is a persisted nonretryable502") {
    val cfg = config.copy(synchronousDeadlineMs = 500, maxResultBytes = 100)
    val calls = new AtomicInteger
    val workflow = new QueryWorkflow {
      def run(r: QueryRequest, c: RequestContext, s: String => Unit) = {
        calls.incrementAndGet(); Right(WorkflowOutput(ujson.Obj("summary" -> ("x" * 200))))
      }
    }
    val service = new QueryService(new InMemoryQuerySessionStore, workflow, cfg)
    try {
      val result = service.submit(request, "oversize", context).left.toOption.get
      assert(result.status == 502 && result.code == "RESULT_TOO_LARGE" && !result.retryable)
      assert(service.submit(request, "oversize", context).left.toOption.get == result)
      assert(calls.get() == 1)
    } finally service.close()
  }
  test("202 reference reports actual persisted RUNNING state") {
    val release = new CountDownLatch(1); val entered = new CountDownLatch(1)
    val workflow = new QueryWorkflow {
      def run(r: QueryRequest, c: RequestContext, s: String => Unit) = {
        entered.countDown(); release.await(2, TimeUnit.SECONDS);
        Right(WorkflowOutput(ujson.Obj("summary" -> "synthetic")))
      }
    }
    val service = new QueryService(new InMemoryQuerySessionStore, workflow, config)
    try {
      val first = service.submit(request, "running-state", context).toOption.get
      assert(entered.await(1, TimeUnit.SECONDS))
      val replay = service.submit(request, "running-state", context).toOption.get
      assert(first.status == 202 && replay.body("status").str == "RUNNING")
    } finally { release.countDown(); service.close() }
  }
  test("graph aggregate requested deadline interrupts a slow snapshot read") {
    val graph = new GraphApi(
      new GraphSnapshot {
        def snapshotId = "synthetic-slow"
        def node(id: String): StorageResult[GraphNode] = {
          Thread.sleep(1000); StorageResult.Missing
        }
        def edges(id: String, w: String) = StorageResult.Found(Vector.empty)
        def metrics(id: String, w: String) = StorageResult.Missing
      },
      GraphApiConfig(timeoutMs = 500)
    )
    try {
      val begin = System.nanoTime()
      assert(
        graph
          .neighbors("synthetic", Map("timeoutMs" -> "20"), context)
          .left
          .toOption
          .get
          .status == 504
      )
      assert(System.nanoTime() - begin < 500000000L)
    } finally graph.close()
  }
  test(
    "explicit offline composition produces only verified synthetic claims with stored evidence"
  ) {
    val composition =
      new OfflineComposition(config.copy(synchronousDeadlineMs = 3000, workflowTimeoutMs = 10000))
    try {
      val r = QueryRequest
        .parse("{\"question\":\"Synthetic fixture: publication count for A\"}", config)
        .toOption
        .get
      val reply = composition.queries.submit(r, "offline-lifecycle", context).toOption.get
      assert(reply.status == 200)
      assert(reply.body("claims").arr.nonEmpty)
      assert(reply.body("claims").arr.forall(_("verificationStatus").str == "VERIFIED"))
      val id = reply.body("claims")(0)("evidenceIds")(0).str
      assert(composition.extended.evidence.evidence(id).isRight)
      val explain = composition.extended.evidence.explain(reply.body("queryId").str).toOption.get
      assert(explain.body("outcome").str == "ANSWERED")
      // The synthesis label of the pinned runtime config: the retired v1 label never answers.
      val versions = explain.body("promptVersions").arr.map(_.str)
      assert(versions.contains("synthesis-v2") && !versions.contains("synthesis-v1"))
    } finally { composition.queries.close(); composition.extended.close() }
  }
  test("shortest graph paths respect the requested hop cap and expose only actual edges") {
    val fixture = edu.uic.cs441.scholarchain.rag.RuntimeOfflineFixture
    val nodes = fixture.names.map(n =>
      GraphNode(
        fixture.id(n),
        SchemaVersions.domain,
        GraphNodeClass.Researcher,
        n,
        Vector.empty,
        fixture.provenance
      )
    )
    val edges = fixture.edges.map(e =>
      GraphEdge(
        e.edgeId,
        SchemaVersions.domain,
        e.researcherA,
        GraphEdgeType.CoauthoredWith,
        e.researcherB,
        fixture.policy,
        GraphSourceEvidence.Work(e.representativeWorkIds.head),
        Vector.empty,
        None,
        fixture.provenance
      )
    )
    val graph = new GraphApi(new InMemoryGraphSnapshot("synthetic-paths", nodes, edges))
    try {
      val params = Map("from" -> fixture.id("A"), "to" -> fixture.id("D"))
      val shallow = graph.paths(params.updated("maxDepth", "1"), context).toOption.get
      assert(shallow.body("paths").arr.isEmpty)
      val result =
        graph.paths(params.updated("maxDepth", "2"), context).toOption.get.body("paths")(0)
      assert(
        result("nodeIds").arr.toVector
          .map(_.str) == Vector(fixture.id("A"), fixture.id("C"), fixture.id("D"))
      )
      assert(result("edgeIds").arr.size == 2)
      assert(result("edgeIds").arr.forall(e => edges.exists(_.edgeId == e.str)))
    } finally graph.close()
  }

}
