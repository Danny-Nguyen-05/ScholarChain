package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import java.net.URI
import java.nio.file.{Files, Path}
import java.time.{LocalDate, ZoneOffset}
import scala.util.control.NonFatal

/** The composed role: HTTP application parts, bounded dependency readiness and owned ports. */
final class AwsComposition private (
    val queries: QueryService,
    val extended: Option[ExtendedApi],
    val readiness: ReadinessGate,
    val worker: Option[EmbeddingWorker],
    ports: PortBundle
) extends AutoCloseable {
  def ready: Boolean = readiness.ready
  def close(): Unit = { readiness.close(); ports.close() }
}

object AwsComposition {
  private val readinessContext = RequestContext("readiness", "readiness")
  private val packagedRuntimeConfig = "/scholarchain.runtime-config.v1.json"

  private object RefusingWorkflow extends QueryWorkflow {
    def run(
        request: QueryRequest,
        context: RequestContext,
        stage: String => Unit
    ): Either[ApiError, WorkflowOutput] = Left(ApiError.unavailable)
  }
  private object RefusingSessions extends QuerySessionStore {
    private val refused = StorageResult.Rejected("role-does-not-serve-queries")
    def createIfAbsent(queryId: String, idempotencyKey: String) = refused
    def get(queryId: String) = refused
    def lookupByIdempotencyKey(key: String) = refused
    def update(session: QuerySession, expectedRevision: Long) = refused
  }

  /** Stable run identity for one query, shaped as the domain's run-id contract. */
  private[services] def runId(queryId: String): String = {
    val h = StableIds.sha256Hex("runtime-query:" + queryId)
    val variant = "89ab" (Integer.parseInt(h.substring(16, 17), 16) % 4)
    "run:" + h.substring(0, 8) + "-" + h.substring(8, 12) + "-4" + h.substring(13, 16) + "-" +
      variant + h.substring(17, 20) + "-" + h.substring(20, 32)
  }

  /** The packaged runtime contract with only deployment values replaced. The temperature, prompt
    * versions, retrieval bounds and tool-use behavior stay exactly as packaged.
    */
  private[services] def runtimeConfig(config: QueryRoleConfig): Either[String, RuntimeConfig] = {
    val in = classOf[RuntimeConfig].getResourceAsStream(packagedRuntimeConfig)
    if (in == null) Left("runtime-config-resource-unavailable")
    else {
      val text =
        try new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8)
        finally in.close()
      RuntimeConfigLoader.fromJson(text) match {
        case Left(_) => Left("runtime-config-invalid")
        case Right(base) =>
          val o = config.overrides
          val updated = base.copy(
            retrievalMode = o.retrievalMode.getOrElse(base.retrievalMode),
            model = base.model.copy(
              modelId = config.synthesisModelId,
              modelVersion = config.synthesisModelVersion,
              region = config.region
            ),
            deadlines = base.deadlines.copy(
              plannerMs = o.plannerMs.getOrElse(base.deadlines.plannerMs),
              synthesisMs = o.synthesisMs.getOrElse(base.deadlines.synthesisMs)
            ),
            operations = base.operations.copy(
              synchronousDeadlineMs =
                o.synchronousMs.map(_.toInt).getOrElse(base.operations.synchronousDeadlineMs)
            )
          )
          // The provider decides the model id the client and every agent must agree on.
          val forProvider = SynthesisClients.runtimeConfigFor(
            config.synthesisProvider,
            updated,
            config.synthesisModelId
          )
          if (RuntimeConfigValidation.check(forProvider).isEmpty) Right(forProvider)
          else Left("runtime-config-invalid")
      }
    }
  }

  private def assets(
      config: QueryRoleConfig,
      runtime: RuntimeConfig
  ): Either[String, RuntimePromptAssets] = {
    val root = config.promptsDirectory
      .map(Path.of(_))
      .orElse(
        Iterator
          .iterate(Path.of("").toAbsolutePath)(_.getParent)
          .takeWhile(_ != null)
          .map(_.resolve("prompts"))
          .find(Files.isDirectory(_))
      )
    root
      .toRight("runtime-assets-unavailable")
      .flatMap(RuntimePromptAssets.fromDirectory(_, runtime))
  }

  /** Per-request retrieval stack over long-lived, injected ports. Every stage reads the injected
    * port; nothing here selects a stand-in store, model or embedder.
    */
  private[services] final class LiveQueryWorkflow(
      config: QueryRoleConfig,
      runtime: RuntimeConfig,
      prompts: RuntimePromptAssets,
      ports: QueryPorts,
      graph: GraphEndpoints,
      semantic: SemanticEndpoints,
      today: () => String = () => LocalDate.now(ZoneOffset.UTC).toString
  ) extends QueryWorkflow {
    private val planner = new QueryPlannerAgent(ports.llm, runtime, prompts)
    private val resolver = new ResearcherResolverAgent(ports.links, runtime)
    private val metricsAgent =
      new CollaborationMetricsAgent(ports.metrics, ports.artifacts, runtime)
    private val synthesis = new AnswerSynthesisAgent(ports.llm, runtime, prompts)
    private val verifier = new ClaimVerificationAgent(runtime)
    private val evidenceAgent = new EvidenceBuilderAgent(ports.evidence, runtime)
    private val carrier = new RemoteQueryEmbeddingCarrier(config.embedding)

    private def provenance(queryId: String): Provenance = Provenance(
      SchemaVersions.domain,
      SourceType.ScholarChain,
      queryId,
      None,
      config.datasetSnapshot,
      Some(today()),
      None,
      runId(queryId),
      Vector("Live runtime query. The dataset snapshot is as configured and is not pinned here.")
    )
    private[services] def resolvePlan(
        request: QueryRequest,
        context: RequestContext
    ): Either[ApiError, QueryPlan] =
      planner.plan(request.question, context.queryId, provenance(context.queryId)) match {
        case PlannerResult.Planned(plan, _, _) => Right(plan)
        case PlannerResult.Unsupported(_, _)   => Left(ApiError.unsupported)
        case PlannerResult.Failed(reason) =>
          Left(
            (if (reason.contains("deadline")) ApiError.timeout else ApiError.downstream)
              .copy(retryable = false)
          )
      }
    def run(
        request: QueryRequest,
        context: RequestContext,
        stage: String => Unit
    ): Either[ApiError, WorkflowOutput] = {
      val reader = new RemoteGraphReader(graph, context)
      val vectors = new RemoteVectorStore(semantic, request.question, context)
      val retrieval = new WorkflowRunner(
        planner,
        resolver,
        metricsAgent,
        new PathFinderAgent(reader, ports.metrics, ports.artifacts, runtime),
        new CommunityAnalystAgent(reader, ports.metrics, ports.artifacts, runtime),
        new SemanticContextAgent(
          vectors,
          ports.objects,
          carrier,
          "remote-semantic-service",
          runtime
        ),
        evidenceAgent,
        runtime
      )
      val workflow =
        new RuntimeAnswerWorkflow(retrieval, synthesis, verifier, ports.audits, runtime)
      new RuntimeWorkflowAdapter(workflow, resolvePlan, Some(ports.evidence))
        .run(request, context, stage)
    }
  }

  /** The configured stored-vector identity must match the client that will embed queries or
    * documents: provider, model, version tag and dimension. A mismatch refuses startup with a
    * closed code (no value) and releases the ports already opened.
    */
  private def consistent[P <: PortBundle](
      provider: EmbeddingProvider,
      stored: EmbeddingModel,
      client: EmbeddingClient,
      ports: P
  ): Either[String, P] = VectorConsistency.checkClient(provider, stored, client) match {
    case Right(_)    => Right(ports)
    case Left(error) => ports.close(); Left(error.code)
  }

  private def gate(common: AwsCommon, checks: Vector[ReadinessCheck]): ReadinessGate =
    new ReadinessGate(checks, common.readiness.cacheMs, common.readiness.timeoutMs)

  private def refusing(service: ServiceConfig, metrics: ServiceMetrics): QueryService =
    new QueryService(RefusingSessions, RefusingWorkflow, service, metrics)

  private def graphRole(
      service: ServiceConfig,
      config: GraphRoleConfig,
      env: Map[String, String],
      factory: AwsPortFactory
  ): Either[String, AwsComposition] = factory.graph(config).map { ports =>
    val graphConfig = BootstrapConfig.graph(env)
    val snapshot = new LiveGraphSnapshot(
      config.snapshotId,
      ports.reader,
      ports.metrics,
      scanLimit = graphConfig.maxScannedEdges
    )
    val api = new GraphApi(snapshot, graphConfig)
    val metrics = new ServiceMetrics
    new AwsComposition(
      refusing(service, metrics),
      Some(
        ExtendedApi(
          new EvidenceApi(UnservedEvidenceStore, UnservedAuditStore),
          api,
          UnservedSemanticEndpoints
        )
      ),
      gate(
        config.common,
        Vector(
          ReadinessProbes.check("neptune")(ports.reader.node(ReadinessProbes.probeKey)),
          ReadinessProbes.check("dynamodb-metrics")(
            ports.metrics.get(ReadinessProbes.probeKey, ReadinessProbes.probeKey)
          )
        )
      ),
      None,
      ports
    )
  }

  private def semanticRole(
      service: ServiceConfig,
      config: SemanticRoleConfig,
      factory: AwsPortFactory
  ): Either[String, AwsComposition] = factory
    .semantic(config)
    .flatMap { ports =>
      // Only the query-type client is wrapped (P40): the cache reports the underlying identity,
      // so the consistency check sees the same provider, model, version and dimension.
      val cached = new CachingEmbeddingClient(ports.embedding, config.embeddingCacheMaxEntries)
      consistent(config.embeddingProvider, config.embedding, cached, ports).map(p => (p, cached))
    }
    .map { (ports, cached) =>
      val api = SemanticApi.fromPorts(cached, config.embedding, ports.vectors, config.index)
      val metrics = new ServiceMetrics
      metrics.registerEmbeddingCache(() => cached.stats)
      new AwsComposition(
        refusing(service, metrics),
        Some(
          ExtendedApi(
            new EvidenceApi(UnservedEvidenceStore, UnservedAuditStore),
            UnservedGraphEndpoints,
            api
          )
        ),
        gate(
          config.common,
          Vector(
            ReadinessProbes.check("s3-vectors")(
              ports.vectors.get(config.index, Vector(ReadinessProbes.probeKey))
            )
          )
        ),
        None,
        ports
      )
    }

  private def workerRole(
      service: ServiceConfig,
      config: WorkerRoleConfig,
      workerConfig: WorkerConfig,
      factory: AwsPortFactory
  ): Either[String, AwsComposition] = factory
    .worker(config)
    .flatMap { ports =>
      consistent(config.embeddingProvider, config.embedding, ports.embedder, ports)
    }
    .map { ports =>
      val runner = new EmbeddingManifestRunner(
        EmbeddingIngestConfig(
          config.ragBucket,
          config.textPrefix,
          config.embedding.dimension,
          config.metric
        ),
        ports.objects,
        ports.vectors,
        ports.registry,
        ports.ledger,
        ports.embedder
      )
      val worker = new EmbeddingWorker(
        ports.queue,
        ports.dlq,
        ports.sessions,
        new ManifestEmbeddingProcessor(runner),
        workerConfig
      )
      val key = ReadinessProbes.probeKey
      new AwsComposition(
        refusing(service, new ServiceMetrics),
        None,
        gate(
          config.common,
          Vector(
            ReadinessProbes.check("sqs-queue")(ports.queue.backlog),
            ReadinessProbes.check("s3-vectors")(ports.vectors.get(config.index, Vector(key))),
            ReadinessProbes.check("dynamodb-run-ledger")(ports.ledger.getRun(key)),
            ReadinessProbes.check("dynamodb-artifact-registry")(ports.registry.get(key, key)),
            ReadinessProbes.check("dynamodb-query-session")(ports.sessions.get(key))
          )
        ),
        Some(worker),
        ports
      )
    }

  private def queryRole(
      service: ServiceConfig,
      config: QueryRoleConfig,
      factory: AwsPortFactory
  ): Either[String, AwsComposition] = for {
    runtime <- runtimeConfig(config)
    prompts <- assets(config, runtime)
    ports <- factory.query(config, runtime)
  } yield {
    val metrics = new ServiceMetrics
    val token = config.internalToken.value
    val graph = new RemoteGraphApi(
      new RemoteService(config.graphBaseUri, token, service, metrics, "graph")
    )
    val semantic = new RemoteSemanticApi(
      new RemoteService(config.semanticBaseUri, token, service, metrics, "semantic")
    )
    // A local stack started without a model key answers queries with one explicit refusal instead
    // of letting the planner fallback and an abstaining synthesis mask the missing key.
    val workflow: QueryWorkflow =
      if (ports.llm eq MissingKeyLlm) MissingKeyLlm.workflow
      else new LiveQueryWorkflow(config, runtime, prompts, ports, graph, semantic)
    val key = ReadinessProbes.probeKey
    new AwsComposition(
      new QueryService(ports.sessions, workflow, service, metrics),
      Some(
        ExtendedApi(
          new EvidenceApi(ports.evidence, ports.audits, Some(ports.sessions)),
          graph,
          semantic
        )
      ),
      gate(
        config.common,
        Vector(
          ReadinessProbes.check("dynamodb-query-session")(ports.sessions.get(key)),
          ReadinessProbes.check("dynamodb-evidence-bundle")(ports.evidence.get(key)),
          ReadinessProbes.check("dynamodb-metrics")(ports.metrics.get(key, key)),
          ReadinessProbes.check("dynamodb-entity-links")(ports.links.lookupByNormalizedName(key)),
          ReadinessCheck("graph-service", () => graph.ready(readinessContext)),
          ReadinessCheck("semantic-service", () => semantic.ready(readinessContext))
        )
      ),
      None,
      ports
    )
  }

  /** The only place an aws-mode role is assembled. A refusal is a closed code. */
  def build(
      service: ServiceConfig,
      config: AwsRoleConfig,
      env: Map[String, String],
      factory: AwsPortFactory
  ): Either[String, AwsComposition] = try
    config match {
      case c: GraphRoleConfig    => graphRole(service, c, env, factory)
      case c: SemanticRoleConfig => semanticRole(service, c, factory)
      case c: WorkerRoleConfig   => workerRole(service, c, BootstrapConfig.worker(env), factory)
      case c: QueryRoleConfig    => queryRole(service, c, factory)
    }
  catch { case NonFatal(_) => Left("invalid-aws-composition") }
}
