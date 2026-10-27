package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.nio.file.{Path, Files}

/** Explicit synthetic offline composition, never selected as an implicit production fallback. It
  * runs the real retrieval/synthesis/verification/audit path against the declared Phase9 G1
  * snapshot. Its scripted synthesis copies only a retrieved publication count for verification.
  */
final class OfflineComposition(
    config: ServiceConfig,
    remoteGraph: Option[GraphEndpoints] = None,
    remoteSemantic: Option[SemanticEndpoints] = None,
    sharedMetrics: Option[ServiceMetrics] = None
) {
  val sessions = new InMemoryQuerySessionStore
  val evidence = new InMemoryIndexedEvidenceBundleStore
  val audits = new InMemoryRuntimeAuditStore
  val metrics = sharedMetrics.getOrElse(new ServiceMetrics)
  private val fixture = RuntimeOfflineFixture
  private val runtimeConfig = fixture.config.copy(retrievalMode = RetrievalMode.Fused)
  private val assetsRoot = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("prompts"))
    .find(Files.isDirectory(_))
  private val localMetrics = fixture.metricStore()
  private val graphNodes = fixture.names.map(n =>
    GraphNode(
      fixture.id(n),
      SchemaVersions.domain,
      GraphNodeClass.Researcher,
      n,
      Vector.empty,
      fixture.provenance
    )
  )
  private val graphEdges = fixture.edges.map { e =>
    val source = GraphSourceEvidence.Work(e.representativeWorkIds.head)
    GraphEdge(
      e.edgeId,
      SchemaVersions.domain,
      e.researcherA,
      GraphEdgeType.CoauthoredWith,
      e.researcherB,
      fixture.policy,
      source,
      Vector(NamedText("windowId", "all-years")),
      None,
      fixture.provenance
    )
  }
  val graph: GraphEndpoints = remoteGraph.getOrElse(
    new GraphApi(
      new InMemoryGraphSnapshot("synthetic-phase9-g1-v1", graphNodes, graphEdges, localMetrics),
      BootstrapConfig.graph(sys.env)
    )
  )
  private val embedding = new DeterministicHashedEmbeddingClient(
    EmbeddingModel("synthetic-offline-services", "v1", 8)
  )
  private val vectors = new InMemoryVectorStore
  private val index = "synthetic-offline-services-v1"
  vectors.ensureIndex(index, 8, "cosine")
  val semantic: SemanticEndpoints =
    remoteSemantic.getOrElse(SemanticApi.fromPorts(embedding, embedding.model, vectors, index))
  val extended = ExtendedApi(new EvidenceApi(evidence, audits, Some(sessions)), graph, semantic)

  val workflow: QueryWorkflow = new QueryWorkflow {
    def run(
        request: QueryRequest,
        context: RequestContext,
        stage: String => Unit
    ): Either[ApiError, WorkflowOutput] = {
      if (request.question != "Synthetic fixture: publication count for A")
        return Left(ApiError.unsupported)
      val assets = assetsRoot
        .toRight(ApiError.unavailable)
        .flatMap(p =>
          RuntimePromptAssets.fromDirectory(p, runtimeConfig).left.map(_ => ApiError.unavailable)
        )
      assets.flatMap { prompts =>
        val metricPort = new ResearcherMetricStore {
          def put(r: ResearcherMetricRecord) = StorageResult.Rejected("read-only-runtime")
          def get(id: String, window: String): StorageResult[ResearcherMetricRecord] =
            remoteGraph match {
              case None => localMetrics.get(id, window)
              case Some(g) =>
                g.metrics(id, window, context) match {
                  case Left(_) => StorageResult.Rejected("remote-metrics-unavailable")
                  case Right(reply) =>
                    val body = reply.body
                    StorageResult.Found(
                      ResearcherMetricRecord(
                        id,
                        window,
                        body("metricVersion").str,
                        body("runId").str,
                        body("record").render(),
                        body("qualifications").render()
                      )
                    )
                }
            }
          def batchGet(
              keys: Vector[(String, String)]
          ): StorageResult[Vector[ResearcherMetricRecord]] = {
            val values = keys.map((id, w) => get(id, w))
            if (values.forall(StorageResult.successful))
              StorageResult.Found(values.flatMap(StorageResult.value))
            else StorageResult.Rejected("remote-metrics-unavailable")
          }
        }
        val semanticVectors: VectorStore = remoteSemantic
          .map { remote =>
            new VectorStore {
              def ensureIndex(n: String, d: Int, m: String) =
                StorageResult.Rejected("read-only-runtime")
              def putBatch(n: String, ds: Vector[VectorDocument]) =
                StorageResult.Rejected("read-only-runtime")
              def get(n: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
                StorageResult.Found(Vector.empty)
              def query(n: String, v: Vector[Float], k: Int, f: Map[String, String])
                  : StorageResult[Vector[VectorHit]] = remote.retrieve(
                ujson
                  .Obj(
                    "question" -> request.question,
                    "topK" -> k,
                    "filters" -> ujson.Obj.from(f.map((key, value) => key -> ujson.Str(value)))
                  )
                  .render(),
                context
              ) match {
                case Left(_) => StorageResult.Rejected("remote-semantic-unavailable")
                case Right(reply) =>
                  StorageResult.Found(
                    reply
                      .body("hits")
                      .arr
                      .toVector
                      .map(h =>
                        VectorHit(
                          h("key").str,
                          h("distance").num,
                          h("metadata").obj.toMap.map((key, value) => key -> value.str)
                        )
                      )
                  )
              }
            }
          }
          .getOrElse(vectors)
        val model = new LlmClient {
          def complete(r: StructuredLlmRequest): LlmResult = {
            val body = ujson.read(r.userData)
            val contextJson = ujson.read(
              body("evidenceData").str
                .stripPrefix("<untrusted_evidence_json>\n")
                .stripSuffix("\n</untrusted_evidence_json>")
            )
            val item = contextJson("items").arr.find(
              _.obj.get("values").exists(_.obj.contains("publicationCount"))
            )
            item match {
              case None => LlmResult.Failure("synthetic-count-evidence-unavailable")
              case Some(ev) =>
                val raw = ev("values")("publicationCount")
                val value = raw.strOpt.getOrElse(raw.render())
                val claim = ujson.Obj(
                  "claimId" -> "synthetic-publication-count",
                  "claimType" -> "METRIC",
                  "subjectIds" -> ujson.Arr(fixture.id("A")),
                  "values" -> ujson.Arr(
                    ujson.Obj(
                      "field" -> "publicationCount",
                      "number" -> value,
                      "text" -> ujson.Null,
                      "ids" -> ujson.Null,
                      "flag" -> ujson.Null
                    )
                  ),
                  "evidenceIds" -> ujson.Arr(ev("evidenceId")),
                  "windowIds" -> ujson.Arr("all-years"),
                  "templateId" -> "metric-v1"
                )
                LlmResult.Output(
                  ujson
                    .Obj(
                      "schemaVersion" -> runtimeConfig.synthesisSchemaVersion,
                      "claims" -> ujson.Arr(claim),
                      "narrativeClaimIds" -> ujson.Arr("synthetic-publication-count"),
                      "interpretation" -> "",
                      "uncertainty" -> "Declared synthetic offline G1 fixture only."
                    )
                    .render(),
                  LlmUsage(None, None),
                  runtimeConfig.model.modelId,
                  runtimeConfig.model.modelVersion
                )
            }
          }
        }
        val retrieval = new WorkflowRunner(
          new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), runtimeConfig, prompts),
          new ResearcherResolverAgent(fixture.cache(), runtimeConfig),
          new CollaborationMetricsAgent(metricPort, fixture.artifacts(), runtimeConfig),
          new PathFinderAgent(fixture.graph(), metricPort, fixture.artifacts(), runtimeConfig),
          new CommunityAnalystAgent(
            fixture.graph(),
            metricPort,
            fixture.artifacts(),
            runtimeConfig
          ),
          new SemanticContextAgent(
            semanticVectors,
            new InMemoryObjectStore,
            embedding,
            index,
            runtimeConfig
          ),
          new EvidenceBuilderAgent(evidence, runtimeConfig),
          runtimeConfig
        )
        val full = new RuntimeAnswerWorkflow(
          retrieval,
          new AnswerSynthesisAgent(model, runtimeConfig, prompts),
          new ClaimVerificationAgent(runtimeConfig),
          audits,
          runtimeConfig
        )
        val adapter = new RuntimeWorkflowAdapter(
          full,
          (req, _) =>
            Right(
              fixture
                .plan(QueryOperation.MaximumTeamSize, "A")
                .copy(
                  question = req.question,
                  runtime = Some(
                    RuntimeQueryOptions(
                      researcherNames = Vector("A"),
                      windowIds = Vector("all-years"),
                      retrievalMode = RetrievalMode.Fused,
                      evidenceOnly = false
                    )
                  )
                )
            ),
          Some(evidence)
        )
        adapter.run(request, context, stage)
      }
    }
  }
  def ready: Boolean =
    assetsRoot.nonEmpty && graph.ready(RequestContext("readiness", "readiness")) && semantic.ready(
      RequestContext("readiness", "readiness")
    )
  val queries = new QueryService(sessions, workflow, config, metrics)
}
