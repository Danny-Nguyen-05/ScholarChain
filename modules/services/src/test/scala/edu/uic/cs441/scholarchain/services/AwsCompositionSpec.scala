package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.RuntimePromptAssets
import edu.uic.cs441.scholarchain.storage.{
  InMemoryQuerySessionStore,
  RuntimeArtifactPointer,
  StorageResult,
  GraphPage,
  GraphPath,
  VectorHit
}
import java.util.concurrent.atomic.AtomicBoolean
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.auth.credentials.{AwsBasicCredentials, StaticCredentialsProvider}

class AwsCompositionSpec extends AnyFunSuite {
  import AwsTestEnv.*
  private val fastReadiness =
    Map("SCHOLARCHAIN_READINESS_CACHE_MS" -> "1", "SCHOLARCHAIN_READINESS_TIMEOUT_MS" -> "500")
  private val context = RequestContext("req-aws", "trace-aws", "qry-aws")

  private def compose(role: String, env: Map[String, String], factory: FakeFactory) = {
    val merged = env ++ fastReadiness
    val config = parse(role, merged).toOption.get
    AwsComposition.build(service(merged), config, merged, factory)
  }
  private def eventually(check: => Boolean): Boolean = { Thread.sleep(5); check }

  private def stubService(role: String, ready: AtomicBoolean): ApiServer.RunningServer = {
    val config = service(common)
    val queries = new QueryService(
      new InMemoryQuerySessionStore,
      (_, _, _) => Left(ApiError.unavailable),
      config
    )
    ApiServer.start(
      new ApiApplication(queries, config, () => ready.get, _ => (), role),
      "127.0.0.1",
      0
    )
  }

  test("graph-service readiness is reachable-and-authorized through its ports, not loaded data") {
    val factory = new FakeFactory
    val comp = compose("graph-service", graph, factory).toOption.get
    try {
      // Every dependency answers "no such record": an empty, unloaded graph is still ready.
      assert(comp.ready)
      assert(factory.d.calls("neptune") == 1 && factory.d.calls("metrics") == 1)
      assert(factory.d.total == 2, "only the two port probes ran")
      factory.d.failing = Set("neptune")
      assert(eventually(!comp.ready) && comp.readiness.failing == Vector("neptune"))
      factory.d.failing = Set("metrics")
      assert(eventually(!comp.ready) && comp.readiness.failing == Vector("dynamodb-metrics"))
      factory.d.failing = Set.empty
      assert(eventually(comp.ready))
    } finally comp.close()
    assert(factory.closed.get == 1)
  }

  test("graph-service serves node and metric reads from its ports") {
    val factory = new FakeFactory
    val comp = compose("graph-service", graph, factory).toOption.get
    try {
      val api = comp.extended.get.graph
      assert(api.node("any-id", context).left.toOption.get.status == 404)
      assert(api.metrics("any-id", "all-years", context).left.toOption.get.status == 404)
      assert(factory.d.calls("neptune") == 1 && factory.d.calls("metrics") == 1)
      val snapshot =
        new LiveGraphSnapshot(
          LiveGraphSnapshot.unpinnedId,
          new FakeReader(factory.d),
          new FakeMetrics(factory.d)
        )
      assert(
        snapshot.edges("a", "all-years") ==
          StorageResult.Rejected(LiveGraphSnapshot.coreEdgesUnavailable)
      )
      assert(comp.extended.get.semantic.retrieve("{}", context).left.toOption.get.status == 503)
    } finally comp.close()
  }

  test(
    "semantic-service readiness probes only the vector index and embeds through the injected client"
  ) {
    val factory = new FakeFactory
    val comp = compose("semantic-service", semantic, factory).toOption.get
    try {
      assert(comp.ready && factory.d.total == 1 && factory.d.calls("vectors") == 1)
      factory.d.failing = Set("vectors")
      assert(eventually(!comp.ready))
      val body = """{"question":"synthetic semantic question","topK":3}"""
      val reply = comp.extended.get.semantic.retrieve(body, context)
      assert(reply.left.toOption.get.status == 502)
      assert(factory.d.calls("embed") == 1, "the injected embedding client is the only embedder")
      assert(comp.extended.get.graph.node("x", context).left.toOption.get.status == 503)
    } finally comp.close()
  }

  test("embedding-worker readiness needs queue, vectors, ledger, registry and the session table") {
    val factory = new FakeFactory
    val comp = compose("embedding-worker", worker, factory).toOption.get
    try {
      assert(comp.worker.nonEmpty && comp.extended.isEmpty)
      assert(comp.ready)
      assert(
        Set("queue", "vectors", "ledger", "registry", "sessions").forall(factory.d.calls(_) == 1)
      )
      // A task role without the session-table grant is visible as not-ready rather than silent.
      factory.d.failing = Set("sessions")
      assert(eventually(!comp.ready) && comp.readiness.failing == Vector("dynamodb-query-session"))
      factory.d.failing = Set("queue")
      assert(eventually(!comp.ready) && comp.readiness.failing == Vector("sqs-queue"))
    } finally comp.close()
  }

  test("query-api readiness needs its own stores and both peer services") {
    val graphReady = new AtomicBoolean(true)
    val semanticReady = new AtomicBoolean(true)
    val graphServer = stubService("graph-service", graphReady)
    val semanticServer = stubService("semantic-service", semanticReady)
    val factory = new FakeFactory
    // A short breaker reset lets the test observe recovery after a peer outage.
    val env = query(
      s"http://127.0.0.1:${graphServer.port}",
      s"http://127.0.0.1:${semanticServer.port}"
    ) ++ shortBreaker
    val comp = compose("query-api", env, factory).toOption.get
    try {
      assert(comp.ready)
      assert(Set("sessions", "evidence", "metrics", "links").forall(factory.d.calls(_) == 1))
      graphReady.set(false)
      assert(settle(false)(comp.ready) && comp.readiness.failing == Vector("graph-service"))
      graphReady.set(true)
      assert(settle(true)(comp.ready))
      semanticReady.set(false)
      assert(settle(false)(comp.ready) && comp.readiness.failing == Vector("semantic-service"))
      semanticReady.set(true)
      assert(settle(true)(comp.ready))
      factory.d.failing = Set("evidence")
      assert(
        settle(false)(comp.ready) && comp.readiness.failing == Vector("dynamodb-evidence-bundle")
      )
      factory.d.failing = Set.empty
      assert(settle(true)(comp.ready))
      factory.d.hanging = Set("links")
      val started = System.nanoTime()
      assert(eventually(!comp.ready))
      assert((System.nanoTime() - started) / 1000000 < 3000, "bounded by the readiness timeout")
    } finally { comp.close(); graphServer.close(); semanticServer.close() }
  }

  test("a role cannot be composed from another role's configuration") {
    val factory = new FakeFactory
    assert(compose("graph-service", graph, factory).isRight)
    val mismatch = AwsServiceConfig.fromEnvironment("graph-service", semantic, service(semantic))
    assert(mismatch.isLeft)
  }

  test("every refused or failed port creation is a closed code") {
    val factory = new FakeFactory
    factory.refuse = Some("graph-reader-connect-failed")
    assert(compose("graph-service", graph, factory) == Left("graph-reader-connect-failed"))
    factory.refuse = None; factory.explode = true
    assert(compose("graph-service", graph, factory) == Left("invalid-aws-composition"))
  }

  test("query workflow plans through the injected model and refuses unsafe questions first") {
    val factory = new FakeFactory
    val config = parse("query-api", forRole("query-api")).toOption.get.asInstanceOf[QueryRoleConfig]
    val runtime = AwsComposition.runtimeConfig(config).toOption.get
    val prompts = RuntimePromptAssets.fromDirectory(promptsDirectory, runtime).toOption.get
    val ports = factory.query(config, runtime).toOption.get
    val workflow = new AwsComposition.LiveQueryWorkflow(
      config,
      runtime,
      prompts,
      ports,
      UnservedGraphEndpoints,
      UnservedSemanticEndpoints,
      today = () => "2026-11-07"
    )
    def request(q: String) =
      QueryRequest.parse(ujson.Obj("question" -> q).render(), service(common)).toOption.get
    val unsafe = workflow.run(request("execute delete everything"), context, _ => ())
    assert(unsafe == Left(ApiError.unsupported) && factory.llm.requests.isEmpty)
    workflow.run(request("Who are the most connected researchers?"), context, _ => ())
    assert(!factory.llm.requests.isEmpty, "the planner used the injected model client")
    assert(factory.llm.requests.peek().toolName == "submit_query_plan")
    // The run identity is deterministic per query and satisfies the domain run-id contract.
    val run = AwsComposition.runId("qry-" + "0" * 64)
    assert(StableIds.parseRunId(run) == Right(run))
    assert(AwsComposition.runId("qry-" + "0" * 64) == run)
    assert(AwsComposition.runId("qry-" + "1" * 64) != run)
  }

  test("remote graph reader answers port calls from the graph-service routes only") {
    val seen = new java.util.concurrent.ConcurrentLinkedQueue[String]()
    val graphApi = new GraphEndpoints {
      def node(id: String, c: RequestContext) = Left(ApiError(404, "NOT_FOUND", "x"))
      def neighbors(id: String, p: Map[String, String], c: RequestContext) = {
        seen.add("neighbors:" + p.toVector.sortBy(_._1).mkString(","))
        Right(
          ApiReply(
            200,
            ujson.Obj(
              "items" -> ujson.Arr(
                ujson.Obj(
                  "nodeId" -> "n2",
                  "edgeId" -> "e1",
                  "edgeType" -> "COAUTHORED_WITH",
                  "fromId" -> "n1",
                  "toId" -> "n2"
                )
              ),
              "cursor" -> "next-cursor"
            )
          )
        )
      }
      def metrics(id: String, w: String, c: RequestContext) = Left(ApiError.unavailable)
      def paths(p: Map[String, String], c: RequestContext) = {
        seen.add("paths:" + p.toVector.sortBy(_._1).mkString(","))
        Right(
          ApiReply(
            200,
            ujson.Obj(
              "paths" -> ujson.Arr(
                ujson.Obj("nodeIds" -> ujson.Arr("a", "b"), "edgeIds" -> ujson.Arr("e1"))
              )
            )
          )
        )
      }
      def close(): Unit = ()
    }
    val reader = new RemoteGraphReader(graphApi, context)
    val page = reader.neighbors("n1", "all-years", Set("COAUTHORED_WITH"), 5, Some("c0"))
    assert(
      StorageResult.value(page).get ==
        GraphPage(
          Vector(
            edu.uic.cs441.scholarchain.storage
              .GraphNeighbor("n2", "e1", "COAUTHORED_WITH", Map("fromId" -> "n1", "toId" -> "n2"))
          ),
          Some("next-cursor")
        )
    )
    assert(
      seen.peek().contains("(cursor,c0)") && seen.peek().contains("(edgeTypes,COAUTHORED_WITH)")
    )
    assert(
      StorageResult.value(reader.shortestPaths("a", "b", 2, "all-years", 3)).get ==
        Vector(GraphPath(Vector("a", "b"), Vector("e1")))
    )
    assert(reader.node("missing") == StorageResult.Missing)
    assert(
      reader
        .neighbors("n1", "all-years", Set("RESOLVES_TO"), 5, None)
        .isInstanceOf[StorageResult.Rejected[?]]
    )
    assert(
      reader.communityMembers("c", "all-years", 5) == StorageResult.Rejected(
        "remote-graph-operation-unsupported"
      )
    )
    assert(reader.crossCommunityEdges("c", "all-years", 5).isInstanceOf[StorageResult.Rejected[?]])
  }

  test("remote vector store sends the question, never the query vector, and returns actual hits") {
    val bodies = new java.util.concurrent.ConcurrentLinkedQueue[String]()
    val semanticApi = new SemanticEndpoints {
      def retrieve(body: String, c: RequestContext) = {
        bodies.add(body)
        Right(
          ApiReply(
            200,
            ujson.Obj(
              "hits" -> ujson.Arr(
                ujson.Obj(
                  "key" -> "k1",
                  "distance" -> 0.25,
                  "metadata" -> ujson.Obj("windowId" -> "all-years")
                )
              )
            )
          )
        )
      }
      def close(): Unit = ()
    }
    val store = new RemoteVectorStore(semanticApi, "synthetic question", context)
    val carrier = new RemoteQueryEmbeddingCarrier(EmbeddingModel("m", "v", 256))
    val vector = carrier.embed(Seq("synthetic question")).head.asInstanceOf[EmbeddingSuccess].values
    val hits = StorageResult.value(store.query("ignored", vector, 4, Map("entityId" -> "e"))).get
    assert(hits == Vector(VectorHit("k1", 0.25, Map("windowId" -> "all-years"))))
    val sent = ujson.read(bodies.peek())
    assert(sent.obj.keySet == Set("question", "topK", "filters"))
    assert(sent("topK").num == 4 && sent("filters")("entityId").str == "e")
    assert(!bodies.peek().contains("0.0625"), "the carried shape is never transmitted")
    assert(store.putBatch("i", Vector.empty).isInstanceOf[StorageResult.Rejected[?]])
    assert(carrier.embed(Seq(" ")).head.isInstanceOf[EmbeddingFailure])
  }

  test("an unconfigured artifact pointer refuses every artifact read") {
    val a = UnconfiguredRuntimeArtifacts
    val refused = StorageResult.Rejected(UnconfiguredRuntimeArtifacts.code)
    assert(a.communitySummary("c", "w") == refused && a.edgeSupport("e", "w") == refused)
    assert(a.researcherContext("r", "w", 1) == refused && a.bridgeMetrics("r", "w") == refused)
  }

  test("the SDK port factory builds its clients offline and releases them") {
    val creds = () => StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test"))
    val provider = new GraphReaderProvider {
      def open(
          endpoint: java.net.URI,
          region: String,
          credentials: software.amazon.awssdk.auth.credentials.AwsCredentialsProvider,
          timeoutMs: Long
      ) = Right(OpenedGraphReader(new FakeReader(new Dependencies), () => ()))
    }
    val factory = new AwsSdkPortFactory(creds, provider)
    val roles = Vector("graph-service", "semantic-service", "embedding-worker", "query-api")
    roles.foreach { role =>
      val env = forRole(role)
      val config = parse(role, env).toOption.get
      val opened: Either[String, PortBundle] = config match {
        case c: GraphRoleConfig    => factory.graph(c)
        case c: SemanticRoleConfig => factory.semantic(c)
        case c: WorkerRoleConfig   => factory.worker(c)
        case c: QueryRoleConfig =>
          factory.query(c, AwsComposition.runtimeConfig(c).toOption.get)
      }
      assert(opened.isRight, role)
      opened.toOption.get.close()
    }
    // The default provider is the storage-owned connect; building it makes no network call.
    val graphConfig = parse("graph-service", graph).toOption.get.asInstanceOf[GraphRoleConfig]
    val defaultGraph = new AwsSdkPortFactory(creds).graph(graphConfig)
    assert(defaultGraph.isRight)
    defaultGraph.toOption.get.close()
  }

  test("artifact pointer configuration reaches the runtime artifact adapter") {
    val env = forRole("query-api") ++ Map(
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY" -> "runtime/versions/v1/artifacts.json",
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256" -> ("b" * 64),
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID" -> "run:fixture"
    )
    val config = parse("query-api", env).toOption.get.asInstanceOf[QueryRoleConfig]
    assert(
      config.artifact.contains(
        RuntimeArtifactSettings("runtime/versions/v1/artifacts.json", "b" * 64, "run:fixture")
      )
    )
    assert(RuntimeArtifactPointer("k", "s", "r").key == "k")
  }
}
