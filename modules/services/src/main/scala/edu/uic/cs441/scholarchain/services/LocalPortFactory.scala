package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.{
  EmbeddingClient,
  EmbeddingFailure,
  EmbeddingModel,
  EmbeddingResult,
  RuntimeConfig
}
import edu.uic.cs441.scholarchain.rag.{
  LlmClient,
  LlmResult,
  StructuredLlmRequest,
  SynthesisProvider
}
import edu.uic.cs441.scholarchain.storage.{
  EvidenceBundleStore,
  InMemoryVectorStore,
  LocalExportStores,
  QuerySessionStore,
  RuntimeAuditStore
}
import scala.util.control.NonFatal

/** The query role's model when no Anthropic key was supplied. Every call is a closed failure, so a
  * request fails cleanly (the planner or the synthesis stage reports a provider failure) and no
  * request ever leaves the process.
  */
private[services] object MissingKeyLlm extends LlmClient {
  val code = "anthropic-api-key-missing"
  val refusal: ApiError = ApiError(
    503,
    "MODEL_NOT_CONFIGURED",
    "No model provider key is configured for this local stack."
  )
  def complete(request: StructuredLlmRequest): LlmResult = LlmResult.Failure(code)

  /** What the query role runs instead of the retrieval workflow while no key is configured. */
  object workflow extends QueryWorkflow {
    def run(
        request: QueryRequest,
        context: RequestContext,
        stage: String => Unit
    ): Either[ApiError, WorkflowOutput] = Left(refusal)
  }
}

/** Semantic retrieval is not served by a local stack: there are no stored vectors and no embedding
  * provider is called. Every embed is a closed, non-retryable failure.
  */
private[services] final class UnservedEmbeddingClient(val model: EmbeddingModel)
    extends EmbeddingClient {
  def embed(texts: Seq[String]): Seq[EmbeddingResult] =
    texts.map(_ => EmbeddingFailure(UnservedEmbeddingClient.code, false, model, 1))
}
private[services] object UnservedEmbeddingClient {
  val code = "local-semantic-not-served"
}

/** Ports for a local, offline query stack: the graph, metric, entity-link and runtime-artifact
  * reads come from one completed Phase 6 export held in memory (`LocalExportStores`), the
  * query-time state (sessions, evidence bundles, audit envelopes) is fresh in-memory state, and the
  * only outward path is the injected Anthropic client.
  *
  * No AWS SDK client is created anywhere here: this class never touches a credentials provider, a
  * region or an endpoint. Retrieval of stored vectors is not served: the semantic role gets an
  * empty vector store and an embedder that always refuses, so a stack that must not call a provider
  * runs graph retrieval only (`SCHOLARCHAIN_RUNTIME_RETRIEVAL_MODE=graph`). The embedding worker is
  * not served. The key arrives as a constructor argument (never read from the role configuration)
  * and is handed only to the provider seam, which never keeps, logs or returns it. A missing key
  * leaves the stack up with a model that refuses every request.
  *
  * @param stores
  *   the loaded export and its fresh query-time ports
  * @param anthropicApiKey
  *   the real key, if any
  * @param providers
  *   the seam that builds the Anthropic client (the real one by default; tests inject a scripted
  *   one)
  */
final class LocalPortFactory(
    stores: LocalExportStores,
    anthropicApiKey: Option[Secret] = None,
    providers: ProviderClients = new RagProviderClients()
) extends AwsPortFactory {
  val sessions: QuerySessionStore = stores.newQuerySessionStore()
  val evidence: EvidenceBundleStore = stores.newEvidenceStore()
  val audits: RuntimeAuditStore = stores.newAuditStore()

  /** True when a key was supplied and handed to the provider seam. */
  def llmConfigured: Boolean = anthropicApiKey.nonEmpty

  def graph(config: GraphRoleConfig): Either[String, GraphPorts] =
    Right(new GraphPorts(stores.graphReader, stores.metrics))

  def semantic(config: SemanticRoleConfig): Either[String, SemanticPorts] = {
    val vectors = new InMemoryVectorStore
    vectors.ensureIndex(config.index, config.embedding.dimension, config.metric)
    Right(new SemanticPorts(new UnservedEmbeddingClient(config.embedding), vectors))
  }

  def query(config: QueryRoleConfig, runtime: RuntimeConfig): Either[String, QueryPorts] =
    if (config.synthesisProvider != SynthesisProvider.Anthropic)
      Left("local-stack-requires-anthropic-provider")
    else
      llm(runtime).map(model =>
        new QueryPorts(
          sessions,
          evidence,
          audits,
          stores.entityLinks,
          stores.metrics,
          stores.objects,
          stores.runtimeArtifacts,
          model,
          () => close(model)
        )
      )

  def worker(config: WorkerRoleConfig): Either[String, WorkerPorts] =
    Left("local-stack-has-no-embedding-worker")

  /** The provider client may hold an HTTP client: release it with the role, never failing. */
  private def close(model: LlmClient): Unit = model match {
    case c: AutoCloseable =>
      try c.close()
      catch { case NonFatal(_) => () }
    case _ => ()
  }

  private def llm(runtime: RuntimeConfig): Either[String, LlmClient] = anthropicApiKey match {
    case None => Right(MissingKeyLlm)
    case Some(key) =>
      try providers.anthropic(key, runtime)
      catch { case NonFatal(_) => Left("provider-client-failed") }
  }
}
