package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import java.util.concurrent.atomic.AtomicInteger

/** Reuses hand-transcribed G1 facts; every provider and backing store is an offline fake. */
private[independent] object IndependentServices10BFixture {
  val externalKey = "synthetic-public-10b"
  val internalKey = "synthetic-internal-10b"
  val config = ServiceConfig(
    apiKeySha256 = Auth.sha256(externalKey),
    internalTokenSha256 = Auth.sha256(internalKey),
    synchronousDeadlineMs = 3000,
    workflowTimeoutMs = 10000,
    maxWorkflowRetries = 0
  )
  val question = IndependentRuntime9CFixture.plan.question
  val body =
    ujson.Obj("question" -> question, "output" -> ujson.Obj("includeScores" -> false)).render()
  private val client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build()
  val a = IndependentRuntime9BFixture.id("A")
  val b = IndependentRuntime9BFixture.id("B")
  val work1 = IndependentPhase6G1.canonicalWorkId("w1")
  val work2 = IndependentPhase6G1.canonicalWorkId("w2")
  val topic = IndependentRuntime9BFixture.topic
  private val provenance = IndependentRuntime9BFixture.provenance
  val graphNodes = Vector(
    (a, GraphNodeClass.Researcher),
    (b, GraphNodeClass.Researcher),
    (work1, GraphNodeClass.Work),
    (work2, GraphNodeClass.Work),
    (topic, GraphNodeClass.Topic)
  ).map { (id, kind) =>
    GraphNode(id, SchemaVersions.domain, kind, "Synthetic fixture node", Vector.empty, provenance)
  }
  private def edge(from: String, kind: GraphEdgeType, to: String, source: String): GraphEdge = {
    val evidence = GraphSourceEvidence.Work(source)
    GraphEdge(
      StableIds.graphEdgeId(kind, from, to, "independent-10b", evidence).toOption.get,
      SchemaVersions.domain,
      from,
      kind,
      to,
      "independent-10b",
      evidence,
      Vector.empty,
      None,
      provenance
    )
  }
  val graphEdges = Vector(
    edge(a, GraphEdgeType.Authored, work1, work1),
    edge(a, GraphEdgeType.Authored, work2, work2),
    edge(b, GraphEdgeType.Authored, work1, work1),
    edge(work1, GraphEdgeType.HasTopic, topic, work1)
  )
  def snapshot(id: String = "synthetic-10b-snapshot-v1"): InMemoryGraphSnapshot =
    new InMemoryGraphSnapshot(id, graphNodes, graphEdges)

  def request(
      port: Int,
      path: String,
      content: Option[String] = None,
      auth: Option[String] = Some(externalKey),
      key: Option[String] = None,
      trace: String = "trace-independent-10b"
  ): HttpResponse[String] = {
    val builder = HttpRequest
      .newBuilder(URI.create(s"http://127.0.0.1:$port$path"))
      .timeout(Duration.ofSeconds(12))
      .header("X-Trace-Id", trace)
      .header("X-Request-Id", "request-independent-10b")
    auth.foreach(k => builder.header("Authorization", s"Bearer $k"))
    key.foreach(k => builder.header("Idempotency-Key", k))
    content match {
      case Some(value) =>
        builder
          .header("Content-Type", "application/json")
          .POST(HttpRequest.BodyPublishers.ofString(value))
      case None => builder.GET()
    }
    client.send(builder.build(), HttpResponse.BodyHandlers.ofString())
  }

  final class Runtime(questionText: String = question) {
    import IndependentRuntime9CFixture.{config as runtimeConfig, *}
    val evidence = new InMemoryIndexedEvidenceBundleStore
    val audits = new InMemoryRuntimeAuditStore
    val modelCalls = new AtomicInteger
    private val assets = RuntimePromptAssets
      .fromDirectory(
        IndependentRuntime9AFixture.root.resolve("prompts"),
        runtimeConfig
      )
      .toOption
      .get
    private val llm = new LlmClient {
      def complete(request: StructuredLlmRequest): LlmResult = {
        modelCalls.incrementAndGet()
        val data = ujson.read(request.userData)
        val context = ujson.read(
          data("evidenceData").str
            .stripPrefix("<untrusted_evidence_json>\n")
            .stripSuffix("\n</untrusted_evidence_json>")
        )
        val id = context("items").arr
          .find(
            _.obj
              .get("values")
              .exists(_.obj.contains("publicationCount"))
          )
          .get("evidenceId")
          .str
        model(output(Vector(claim(Vector(n("publicationCount", "3")), Vector(id)))))
      }
    }
    private val source = IndependentRuntime9BFixture.artifacts()
    private val metric = IndependentRuntime9BFixture.metricStore()
    private val graph = new IndependentRuntime9BFixture.Graph
    private val corpus = new IndependentRuntime9BSemanticFixture.Corpus
    private val retrieval = new WorkflowRunner(
      new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), runtimeConfig, assets),
      new ResearcherResolverAgent(IndependentRuntime9BFixture.cache(), runtimeConfig),
      new CollaborationMetricsAgent(metric, source, runtimeConfig),
      new PathFinderAgent(graph, metric, source, runtimeConfig),
      new CommunityAnalystAgent(graph, metric, source, runtimeConfig),
      new SemanticContextAgent(
        corpus.vectors,
        corpus.objects,
        corpus.embeddings,
        corpus.index,
        runtimeConfig
      ),
      new EvidenceBuilderAgent(evidence, runtimeConfig),
      runtimeConfig
    )
    val workflow = new RuntimeWorkflowAdapter(
      new RuntimeAnswerWorkflow(
        retrieval,
        new AnswerSynthesisAgent(llm, runtimeConfig, assets),
        new ClaimVerificationAgent(runtimeConfig),
        audits,
        runtimeConfig
      ),
      (_, _) => Right(plan.copy(question = questionText))
    )
  }
}
