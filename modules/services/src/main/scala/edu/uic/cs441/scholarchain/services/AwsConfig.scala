package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.EmbeddingModel
import edu.uic.cs441.scholarchain.rag.{
  AnthropicDefaults,
  EmbeddingProvider,
  EmbeddingProviders,
  SynthesisProvider,
  VoyageDefaults
}
import edu.uic.cs441.scholarchain.storage.{DynamoTables, VectorIndexes}
import java.net.URI
import scala.util.control.NonFatal

/** Raw secret holder whose rendering never exposes the value. */
final class Secret(val value: String) {
  override def toString: String = "<redacted>"
}

final case class AwsReadinessSettings(cacheMs: Long, timeoutMs: Long) {
  require(cacheMs >= 1 && cacheMs <= 300000 && timeoutMs >= 100 && timeoutMs <= 30000)
}
final case class AwsCommon(region: String, tables: DynamoTables, readiness: AwsReadinessSettings)
final case class QueueSettings(
    queueUrl: String,
    dlqUrl: String,
    visibilitySeconds: Int,
    waitSeconds: Int
)
final case class RuntimeArtifactSettings(key: String, sha256: String, sourceRunId: String)
final case class RuntimeOverrides(
    plannerMs: Option[Long],
    synthesisMs: Option[Long],
    synchronousMs: Option[Long]
)

/** One closed, immutable description of what a role needs from AWS. Every value comes from the
  * process environment; none is compiled in. toString never contains the internal token.
  */
sealed trait AwsRoleConfig {
  def common: AwsCommon
  def region: String = common.region
}
final case class GraphRoleConfig(
    common: AwsCommon,
    graphBucket: String,
    neptuneEndpoint: URI,
    neptuneTimeoutMs: Long,
    snapshotId: String
) extends AwsRoleConfig
final case class SemanticRoleConfig(
    common: AwsCommon,
    ragBucket: String,
    vectorBucket: String,
    index: String,
    metric: String,
    embedding: EmbeddingModel,
    embeddingProvider: EmbeddingProvider,
    voyageApiKey: Option[Secret],
    embeddingCacheMaxEntries: Int = EmbeddingCacheSettings.default
) extends AwsRoleConfig
final case class QueryRoleConfig(
    common: AwsCommon,
    ragBucket: String,
    graphBaseUri: URI,
    semanticBaseUri: URI,
    internalToken: Secret,
    embedding: EmbeddingModel,
    embeddingProvider: EmbeddingProvider,
    synthesisProvider: SynthesisProvider,
    anthropicApiKey: Option[Secret],
    synthesisModelId: String,
    synthesisModelVersion: String,
    datasetSnapshot: String,
    artifactBucket: Option[String],
    artifact: Option[RuntimeArtifactSettings],
    sessionTtlSeconds: Option[Long],
    evidenceIndexPrefix: String,
    auditPrefix: String,
    promptsDirectory: Option[String],
    overrides: RuntimeOverrides
) extends AwsRoleConfig
final case class WorkerRoleConfig(
    common: AwsCommon,
    ragBucket: String,
    vectorBucket: String,
    index: String,
    metric: String,
    embedding: EmbeddingModel,
    embeddingProvider: EmbeddingProvider,
    voyageApiKey: Option[Secret],
    queue: QueueSettings,
    textPrefix: String
) extends AwsRoleConfig

/** A refusal names only the environment variable, never its value. */
final class AwsConfigRefusal(val code: String) extends RuntimeException(code, null, false, false)

object AwsServiceConfig {
  val roles: Set[String] = Set("query-api", "graph-service", "semantic-service", "embedding-worker")
  val tableVariables: Vector[(String, String)] = Vector(
    "RUN_LEDGER" -> "runLedger",
    "ENTITY_LINK_CACHE" -> "entityLinks",
    "QUERY_SESSION" -> "querySessions",
    "EVIDENCE_BUNDLE" -> "evidence",
    "ARTIFACT_REGISTRY" -> "artifacts",
    "RESEARCHER_METRIC_CACHE" -> "metrics"
  )
  private val bucket = "[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]".r
  private val tableName = "[A-Za-z0-9_.-]{3,255}".r
  private val modelId = "[A-Za-z0-9][A-Za-z0-9._:-]{0,255}".r
  private val tag = "[A-Za-z0-9][A-Za-z0-9._:-]{0,127}".r
  private val regionName = "[a-z]{2}(?:-[a-z]+)+-[0-9]+".r
  private val prefix = "[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*".r

  private final class Reader(env: Map[String, String]) {
    def optionalText(name: String): Option[String] =
      env.get(name).map(_.trim).filter(_.nonEmpty)
    def text(name: String): String =
      optionalText(name).getOrElse(throw new AwsConfigRefusal("missing-aws-configuration:" + name))
    def refuse(name: String): Nothing = throw new AwsConfigRefusal(
      "invalid-aws-configuration:" + name
    )
    def matching(name: String, pattern: scala.util.matching.Regex): String = {
      val value = text(name); if (pattern.matches(value)) value else refuse(name)
    }
    def optionalMatching(name: String, pattern: scala.util.matching.Regex): Option[String] =
      optionalText(name).map(v => if (pattern.matches(v)) v else refuse(name))

    /** A provider key is one printable ASCII token. Any violation names only the variable. */
    def apiKey(name: String): Secret = {
      val value = text(name)
      if (value.length >= 8 && value.length <= 512 && value.forall(c => c > ' ' && c < '\u007f'))
        new Secret(value)
      else refuse(name)
    }
    def long(name: String, default: Long, min: Long, max: Long): Long = optionalText(name) match {
      case None => default
      case Some(v) =>
        try {
          val n = v.toLong; if (n < min || n > max) refuse(name) else n
        } catch { case _: NumberFormatException => refuse(name) }
    }
    def optionalLong(name: String, min: Long, max: Long): Option[Long] =
      optionalText(name).map(_ => long(name, 0, min, max))
    def requiredLong(name: String, min: Long, max: Long): Long = {
      text(name); long(name, 0, min, max)
    }

    /** HTTP(S) location with a host and no user-info, query or fragment. */
    def uri(name: String, schemes: Set[String], explicitPort: Boolean = false): URI = {
      val value = text(name)
      try {
        val u = new URI(value)
        val ok = u.getScheme != null && schemes(u.getScheme.toLowerCase) && u.getHost != null &&
          u.getUserInfo == null && u.getRawQuery == null && u.getRawFragment == null &&
          (!explicitPort || u.getPort > 0)
        if (ok) u else refuse(name)
      } catch { case _: java.net.URISyntaxException => refuse(name) }
    }
  }

  /** The caller supplies the already validated ServiceConfig so the outgoing internal token can be
    * checked against its stored hash. A mismatch is a refusal, never a silent downgrade.
    */
  def fromEnvironment(
      role: String,
      env: Map[String, String],
      service: ServiceConfig
  ): Either[String, AwsRoleConfig] = try {
    if (!roles(role)) throw new AwsConfigRefusal("invalid-aws-configuration:role")
    val r = new Reader(env)
    val region = r.matching("AWS_REGION", regionName)
    r.optionalText("SCHOLARCHAIN_APPLICATION_REGION").foreach { v =>
      if (v != region) r.refuse("SCHOLARCHAIN_APPLICATION_REGION")
    }
    val tableValues = tableVariables.map((suffix, _) =>
      r.matching("SCHOLARCHAIN_DYNAMODB_TABLE_" + suffix, tableName)
    )
    if (tableValues.distinct.size != tableValues.size)
      r.refuse("SCHOLARCHAIN_DYNAMODB_TABLE_*")
    val byField = tableVariables.map(_._2).zip(tableValues).toMap
    val tables = DynamoTables(
      byField("runLedger"),
      byField("entityLinks"),
      byField("querySessions"),
      byField("evidence"),
      byField("artifacts"),
      byField("metrics"),
      r.matching("SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX", tableName)
    )
    val common = AwsCommon(
      region,
      tables,
      AwsReadinessSettings(
        r.long("SCHOLARCHAIN_READINESS_CACHE_MS", 5000, 1, 300000),
        r.long("SCHOLARCHAIN_READINESS_TIMEOUT_MS", 2000, 100, 30000)
      )
    )
    // The rag-owned parsers define the defaults and the accepted names. A refusal here names only
    // the variable, never the value.
    def embeddingProvider: EmbeddingProvider =
      EmbeddingProvider
        .parse(r.optionalText(EmbeddingProvider.EnvName))
        .fold(_ => r.refuse(EmbeddingProvider.EnvName), identity)
    def synthesisProvider: SynthesisProvider =
      SynthesisProvider
        .parse(r.optionalText(SynthesisProvider.EnvName))
        .fold(_ => r.refuse(SynthesisProvider.EnvName), identity)

    def embedding(provider: EmbeddingProvider): EmbeddingModel = provider match {
      case EmbeddingProvider.Bedrock =>
        val dimension = r.requiredLong("SCHOLARCHAIN_EMBEDDING_DIMENSION", 1, 4096).toInt
        // Titan Text Embeddings V2 supports exactly these output sizes.
        if (!Set(256, 512, 1024)(dimension)) r.refuse("SCHOLARCHAIN_EMBEDDING_DIMENSION")
        val model = EmbeddingModel(
          r.matching("SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", modelId),
          r.matching("SCHOLARCHAIN_EMBEDDING_MODEL_VERSION", tag),
          dimension
        )
        // Stored and query vectors must share one provider: a Voyage model id is not a Bedrock one.
        if (!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Bedrock, model))
          r.refuse("SCHOLARCHAIN_MODELS_EMBEDDING_MODEL")
        model
      case EmbeddingProvider.Voyage =>
        // Plan rule 6.7: the model id, version tag and dimension are configuration. Each default and
        // its rationale live in the rag-owned VoyageDefaults; nothing is pinned here.
        val dimension =
          r.long("SCHOLARCHAIN_EMBEDDING_DIMENSION", VoyageDefaults.Dimension, 1, 4096).toInt
        if (!VoyageDefaults.SupportedDimensions(dimension))
          r.refuse("SCHOLARCHAIN_EMBEDDING_DIMENSION")
        val model = EmbeddingModel(
          r.optionalMatching("SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", modelId)
            .getOrElse(VoyageDefaults.ModelId),
          r.optionalMatching("SCHOLARCHAIN_EMBEDDING_MODEL_VERSION", tag)
            .getOrElse(VoyageDefaults.ModelId),
          dimension
        )
        // The naming family decides the provider: a Voyage client needs a voyage-* model.
        if (!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Voyage, model))
          r.refuse("SCHOLARCHAIN_MODELS_EMBEDDING_MODEL")
        model
    }
    def voyageKey(provider: EmbeddingProvider): Option[Secret] =
      if (provider == EmbeddingProvider.Voyage) Some(r.apiKey("SCHOLARCHAIN_VOYAGE_API_KEY"))
      else None
    def metric: String = {
      val m = r.optionalText("SCHOLARCHAIN_S3_VECTORS_METRIC").getOrElse("cosine")
      if (Set("cosine", "euclidean")(m)) m else r.refuse("SCHOLARCHAIN_S3_VECTORS_METRIC")
    }
    def index: String = {
      val v = r.text("SCHOLARCHAIN_SEMANTIC_INDEX")
      if (VectorIndexes.names(v)) v else r.refuse("SCHOLARCHAIN_SEMANTIC_INDEX")
    }
    Right(role match {
      case "graph-service" =>
        val cursor = r.text("SCHOLARCHAIN_GRAPH_CURSOR_KEY")
        if (cursor.length < 16) r.refuse("SCHOLARCHAIN_GRAPH_CURSOR_KEY")
        GraphRoleConfig(
          common,
          r.matching("SCHOLARCHAIN_STORAGE_GRAPH_BUCKET", bucket),
          r.uri("SCHOLARCHAIN_NEPTUNE_ENDPOINT", Set("https"), explicitPort = true),
          r.long("SCHOLARCHAIN_NEPTUNE_QUERY_TIMEOUT_MS", 5000, 100, 60000),
          r.optionalMatching("SCHOLARCHAIN_GRAPH_SNAPSHOT_ID", tag)
            .getOrElse(LiveGraphSnapshot.unpinnedId)
        )
      case "semantic-service" =>
        val provider = embeddingProvider
        SemanticRoleConfig(
          common,
          r.matching("SCHOLARCHAIN_STORAGE_RAG_BUCKET", bucket),
          r.matching("SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET", bucket),
          index,
          metric,
          embedding(provider),
          provider,
          voyageKey(provider),
          r.long(
            EmbeddingCacheSettings.EnvName,
            EmbeddingCacheSettings.default.toLong,
            1,
            EmbeddingCacheSettings.MaxEntries
          ).toInt
        )
      case "embedding-worker" =>
        val wait = r.long("SCHOLARCHAIN_WORKER_WAIT_SECONDS", 0, 0, 20).toInt
        val provider = embeddingProvider
        WorkerRoleConfig(
          common,
          r.matching("SCHOLARCHAIN_STORAGE_RAG_BUCKET", bucket),
          r.matching("SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET", bucket),
          index,
          metric,
          embedding(provider),
          provider,
          voyageKey(provider),
          QueueSettings(
            r.uri("SCHOLARCHAIN_SQS_QUEUE_URL", Set("https")).toString,
            r.uri("SCHOLARCHAIN_SQS_DLQ_URL", Set("https")).toString,
            r.long("SCHOLARCHAIN_WORKER_VISIBILITY_TIMEOUT_SECONDS", 30, 1, 43200).toInt,
            wait
          ),
          r.matching("SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX", prefix)
        )
      case _ =>
        val token = r.text("SCHOLARCHAIN_INTERNAL_TOKEN")
        if (Auth.sha256(token) != service.internalTokenSha256)
          r.refuse("SCHOLARCHAIN_INTERNAL_TOKEN")
        val pointer = Vector(
          r.optionalText("SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY"),
          r.optionalText("SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256"),
          r.optionalText("SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID")
        )
        val artifact = pointer match {
          case Vector(None, None, None) => None
          case Vector(Some(key), Some(sha), Some(run)) =>
            if (!key.contains("/versions/") || key.split('/').contains(".."))
              r.refuse("SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY")
            if (!sha.matches("[0-9a-f]{64}")) r.refuse("SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256")
            Some(RuntimeArtifactSettings(key, sha, run))
          case _ => r.refuse("SCHOLARCHAIN_RUNTIME_ARTIFACT_*")
        }
        val embeddingChoice = embeddingProvider
        val synthesisChoice = synthesisProvider
        // The query role only carries the embedding description; it never calls the embedder, so
        // it neither needs nor reads the Voyage key.
        val queryEmbedding = embedding(embeddingChoice)
        val anthropicKey = synthesisChoice match {
          case SynthesisProvider.Anthropic => Some(r.apiKey("SCHOLARCHAIN_ANTHROPIC_API_KEY"))
          case SynthesisProvider.Bedrock   => None
        }
        val (synthesisModel, synthesisVersion) = synthesisChoice match {
          case SynthesisProvider.Anthropic =>
            (
              r.optionalMatching("SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL", modelId)
                .getOrElse(AnthropicDefaults.ModelId),
              r.optionalMatching("SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION", tag)
                .getOrElse(AnthropicDefaults.ModelId)
            )
          case SynthesisProvider.Bedrock =>
            (
              r.matching("SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL", modelId),
              r.matching("SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION", tag)
            )
        }
        QueryRoleConfig(
          common,
          r.matching("SCHOLARCHAIN_STORAGE_RAG_BUCKET", bucket),
          r.uri("SCHOLARCHAIN_GRAPH_BASE_URI", Set("http", "https")),
          r.uri("SCHOLARCHAIN_SEMANTIC_BASE_URI", Set("http", "https")),
          new Secret(token),
          queryEmbedding,
          embeddingChoice,
          synthesisChoice,
          anthropicKey,
          synthesisModel,
          synthesisVersion,
          r.optionalMatching("SCHOLARCHAIN_RUNTIME_DATASET_SNAPSHOT", tag)
            .getOrElse("runtime-live-unpinned"),
          r.optionalMatching("SCHOLARCHAIN_RUNTIME_ARTIFACT_BUCKET", bucket),
          artifact,
          r.optionalLong("SCHOLARCHAIN_QUERY_SESSION_TTL_SECONDS", 1, 31536000L),
          r.optionalMatching("SCHOLARCHAIN_EVIDENCE_INDEX_PREFIX", prefix)
            .getOrElse("evidence-index"),
          r.optionalMatching("SCHOLARCHAIN_AUDIT_PREFIX", prefix).getOrElse("runtime-audit"),
          r.optionalText("SCHOLARCHAIN_PROMPTS_DIR"),
          RuntimeOverrides(
            r.optionalLong("SCHOLARCHAIN_RUNTIME_PLANNER_DEADLINE_MS", 1, 600000L),
            r.optionalLong("SCHOLARCHAIN_RUNTIME_SYNTHESIS_DEADLINE_MS", 1, 600000L),
            r.optionalLong("SCHOLARCHAIN_RUNTIME_SYNCHRONOUS_DEADLINE_MS", 1, 600000L)
          )
        )
    })
  } catch {
    case refusal: AwsConfigRefusal => Left(refusal.code)
    case NonFatal(_)               => Left("invalid-aws-configuration")
  }
}
