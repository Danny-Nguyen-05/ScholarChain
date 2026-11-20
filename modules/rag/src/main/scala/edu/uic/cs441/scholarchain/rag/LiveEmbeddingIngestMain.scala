package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import upickle.default.{ReadWriter, read}
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import java.time.{Duration, Instant}
import scala.util.control.NonFatal
import scala.jdk.CollectionConverters.*
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.core.retry.RetryPolicy
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.GetIndexRequest
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient

final case class LiveEmbeddingConfig(
    environment: String,
    region: String,
    profile: String,
    model: EmbeddingModel,
    textBucket: String,
    textPrefix: String,
    vectorBucket: String,
    tables: DynamoTables,
    indexNames: Map[String, String],
    metric: String,
    maxVectors: Int,
    maxConcurrentCalls: Int,
    maxEmbeddingAttempts: Int,
    maxEmbeddingCalls: Long,
    dollarCapUsd: Double,
    assumedMaxDollarsPerEmbeddingAttempt: Double,
    assumedMaxStorageDollarsPerVector: Double,
    fixedOverheadUsd: Double,
    schemaVersion: String = "scholarchain.embedding-live.v1",
    requestTimeoutMillis: Long = 30000,
    maxManifestBytes: Int = 16 * 1024 * 1024,
    batchSize: Int = 100,
    nonFilterableKeys: Vector[String] = Vector("textS3Uri"),
    assumedUsdPerMillionEmbeddingTokens: Double = VoyageDefaults.UsdPerMillionTokens.toDouble,
    minBytesPerEmbeddingToken: Int = 1,
    embeddingProvider: String = "",
    embeddingCapUsd: Double = VoyageDefaults.CapUsd.toDouble,
    // Session-2 plan P26 (b): work items the storage runner processes at once (1 = sequential).
    // Bound by the approval's concurrencyCap in preflight.
    ingestConcurrency: Int = 1
) {
  require(schemaVersion == "scholarchain.embedding-live.v1")
  require(embeddingCapUsd.isFinite && embeddingCapUsd > 0)
  require(
    assumedUsdPerMillionEmbeddingTokens.isFinite && assumedUsdPerMillionEmbeddingTokens > 0 &&
      minBytesPerEmbeddingToken >= 1 && minBytesPerEmbeddingToken <= 4
  )
  require(
    Vector(environment, region, profile, textBucket, textPrefix, vectorBucket).forall(
      _.trim.nonEmpty
    )
  )
  // `tables.idempotencyIndex` is the QuerySession global secondary index NAME (Terraform
  // `query_session_gsi_name`, default `by-idempotency-key`), never a table name. A blank, malformed
  // or table-equal value is refused before any request.
  require(
    LiveEmbeddingConfig.IndexNamePattern.matches(tables.idempotencyIndex) &&
      !Set(
        tables.runLedger,
        tables.entityLinks,
        tables.querySessions,
        tables.evidence,
        tables.artifacts,
        tables.metrics
      ).contains(tables.idempotencyIndex)
  )
  require(indexNames == EmbeddingContracts.indexes && Set("cosine", "euclidean")(metric))
  require(
    maxVectors > 0 && maxConcurrentCalls > 0 && maxEmbeddingAttempts > 0 && maxEmbeddingCalls > 0
  )
  require(
    requestTimeoutMillis > 0 && maxManifestBytes > 0 &&
      maxManifestBytes <= LiveEmbeddingConfig.MaxManifestBytesCeiling
  )
  // `batchSize` (1..500) is both the vectors per S3 Vectors put and, since session-2 plan P26, the
  // texts per embedding request of the ingest lookahead batcher; 500 is below Voyage's documented
  // 1,000-text request limit (`VoyageDefaults.MaxTextsPerRequest`).
  require(batchSize > 0 && batchSize <= 500)
  require(
    ingestConcurrency >= 1 && ingestConcurrency <= EmbeddingIngestConfig.MaxIngestConcurrency,
    "invalid-ingest-concurrency"
  )
  require(
    Vector(dollarCapUsd, assumedMaxDollarsPerEmbeddingAttempt, assumedMaxStorageDollarsPerVector)
      .forall(v => v.isFinite && v > 0) && fixedOverheadUsd.isFinite && fixedOverheadUsd >= 0
  )
  require(
    nonFilterableKeys.distinct.size == nonFilterableKeys.size && nonFilterableKeys.size <= 10 &&
      !nonFilterableKeys.contains("runId") && !nonFilterableKeys.contains("textHash")
  )

  /** Provider of the stored vectors: the explicit `embeddingProvider` (`voyage` or `bedrock`), or,
    * when it is empty, the provider that owns `model`. An unknown name is a closed code.
    */
  def provider: Either[String, EmbeddingProvider] =
    if (embeddingProvider.trim.isEmpty) Right(EmbeddingProviders.infer(model))
    else
      EmbeddingProvider.parse(Some(embeddingProvider)).left.map(_ => "invalid-embedding-provider")

  /** Retry, timeout and attempt parameters shared by both providers' clients. */
  def voyage(inputType: EmbeddingInputType): VoyageEmbeddingConfig = VoyageEmbeddingConfig(
    inputType,
    model = model,
    maxAttempts = maxEmbeddingAttempts,
    requestTimeoutMillis = requestTimeoutMillis
  )
  def embedding: BedrockEmbeddingConfig = BedrockEmbeddingConfig(
    model,
    region,
    maxConcurrentCalls,
    maxEmbeddingAttempts,
    requestTimeoutMillis = requestTimeoutMillis
  )
  def ingest: EmbeddingIngestConfig = EmbeddingIngestConfig(
    textBucket,
    textPrefix,
    model.dimension,
    metric,
    maxManifestItems = maxVectors,
    maxManifestBytes = maxManifestBytes,
    batchSize = batchSize,
    ingestConcurrency = ingestConcurrency
  )

  /** Storage adapter settings of the live ingest. One SDK attempt (the runner owns retries). The
    * run ledger reads a run back as one DynamoDB Query (root row plus one stage row per item), so
    * the page size times the page limit must hold `maxVectors + 1` rows: at the storage default of
    * 100 x 100 a 10,000-item run failed `completeRun` with `query-page-limit`. 1,000 rows per page
    * (each page also stays under DynamoDB's 1 MB page cap at these row sizes) gives 100,000 rows.
    */
  def storageSettings: edu.uic.cs441.scholarchain.storage.StorageConfig =
    edu.uic.cs441.scholarchain.storage.StorageConfig(
      textBucket,
      tables,
      retry = RetryConfig(maxAttempts = 1),
      queryPageSize = LiveEmbeddingConfig.LedgerQueryPageSize
    )

  /** Rows one ledger read must return for this run: the root plus one stage per manifest item. */
  def ledgerRowsFit(items: Int): Boolean =
    BigInt(items) + 1 <= BigInt(storageSettings.queryPageSize) * BigInt(
      storageSettings.maxQueryPages
    )
}
object LiveEmbeddingConfig {
  // Reader and writer are derived separately and joined: one `derives ReadWriter` over 29 fields
  // exceeds Scala 3's 32 successive inlines. Same field names, defaults and omission rules.
  implicit val readWriter: ReadWriter[LiveEmbeddingConfig] =
    ReadWriter.join(
      upickle.default.macroR[LiveEmbeddingConfig],
      upickle.default.macroW[LiveEmbeddingConfig]
    )

  /** DynamoDB index-name rule: 3 to 255 characters from letters, digits, underscore, dot, hyphen.
    */
  val IndexNamePattern: scala.util.matching.Regex = "[A-Za-z0-9_.-]{3,255}".r

  /** Hard ceiling for `maxManifestBytes` and for the manifest file read by both live mains. The
    * default stays 16 MiB; about 10,000 Phase 6 items render to about 20.5 MB (session-2 plan P26,
    * `Phase15VectorScaleSpec`), so a 10,000-item run sets `maxManifestBytes` explicitly.
    */
  val MaxManifestBytesCeiling: Int = 64 * 1024 * 1024

  /** DynamoDB Query page size of the live ingest's storage adapters (see `storageSettings`). */
  val LedgerQueryPageSize: Int = 1000
}
final case class LiveEmbeddingApproval(
    executionApproved: Boolean,
    environment: String,
    runId: String,
    configSha256: String,
    manifestSha256: String,
    phase14GateReference: String,
    phase14GateSha256: String,
    vectorCap: Int,
    concurrencyCap: Int,
    embeddingCallCap: Long,
    dollarCapUsd: Double,
    pricingValidated: Boolean,
    budgetValidated: Boolean,
    expiresAtEpochSeconds: Long,
    schemaVersion: String = "scholarchain.embedding-live-approval.v1",
    operation: String = "ingest",
    queryRequestCap: Long = 0,
    queryEmbeddingCallCap: Long = 0,
    queryObjectReadCap: Long = 0
) derives ReadWriter
final case class LiveEmbeddingPlan(
    config: LiveEmbeddingConfig,
    manifest: EmbeddingManifest,
    approval: LiveEmbeddingApproval,
    maxEmbeddingRequests: Long,
    assumedUpperBoundUsd: BigDecimal,
    plannedEmbeddingTokens: BigInt = BigInt(0)
)
trait LiveEmbeddingPorts extends AutoCloseable {
  def objects: ObjectStore
  def vectors: VectorStore
  def registry: ArtifactRegistry
  def ledger: RunLedger
  def embedder: EmbeddingClient
  def indexesReady(): StorageResult[Unit]
}

/** Authored for a future approved 8C run. Normal tests only exercise refusal or pure preflight; no
  * client or credential provider is constructed before every approval/content/cap check passes.
  */
object LiveEmbeddingIngestMain {
  private val flags = Set("--config", "--manifest", "--approval", "--report", "--run-id")
  private def value[A](r: StorageResult[A]): Either[String, A] = r match {
    case StorageResult.Rejected(code) => Left(code)
    case other                        => StorageResult.value(other).toRight("live-port-unavailable")
  }

  /** Conservative token bound for one embedding pass: every token is at least
    * `minBytesPerEmbeddingToken` UTF-8 bytes (1 by default, a strict upper bound on tokens).
    */
  private[rag] def tokenBound(texts: Iterable[String], minBytes: Int): BigInt =
    texts.foldLeft(BigInt(0))((sum, text) =>
      sum + BigInt((text.getBytes(UTF_8).length + minBytes - 1) / minBytes)
    )

  /** Exact decimal dollars for a token count at the configured price per million tokens. */
  private[rag] def tokenUsd(tokens: BigInt, config: LiveEmbeddingConfig): BigDecimal =
    BigDecimal(tokens.toString) * BigDecimal(config.assumedUsdPerMillionEmbeddingTokens.toString) /
      BigDecimal(1000000)

  /** Provider-aware identity check: the configured model must belong to the provider by naming
    * family (`voyage-*` is Voyage). The model id, version tag, dimension and the assumed price per
    * million tokens all come from the config, which the human approval hash binds.
    */
  private[rag] def providerCheck(config: LiveEmbeddingConfig): Either[String, EmbeddingProvider] =
    config.provider.flatMap { provider =>
      if (!EmbeddingProviders.modelMatchesProvider(provider, config.model))
        Left("embedding-provider-model-mismatch")
      else Right(provider)
    }

  /** The single code path both live mains use to build their embedder. Only the selected provider's
    * config is built (Voyage config on the Voyage branch, Bedrock config on the Bedrock branch) and
    * the `bedrock` thunk is called only on the Bedrock branch. The Voyage key is an argument; no
    * key is read here. Ingest passes `Document`, the query smoke passes `Query`.
    */
  private[rag] def embeddingClientFor(
      config: LiveEmbeddingConfig,
      inputType: EmbeddingInputType,
      voyageKey: Option[String],
      bedrock: () => BedrockRuntimeClient
  ): Either[String, ProviderEmbeddingClient] = config.provider.flatMap { provider =>
    EmbeddingClientFactory.create(
      provider,
      inputType,
      voyageKey,
      bedrock,
      Some(config.embedding),
      new EmbeddingSpendCounter(
        BigDecimal(config.embeddingCapUsd.toString),
        BigDecimal(config.assumedUsdPerMillionEmbeddingTokens.toString)
      ),
      Some(config.voyage(inputType))
    )
  }

  /** Stored (configured) and query/ingest embedder identity must agree: provider, model, version
    * tag and dimension. Returns the typed closed code on a mismatch.
    */
  private[rag] def consistency(
      config: LiveEmbeddingConfig,
      embedder: EmbeddingClient
  ): Either[String, Unit] =
    config.provider.flatMap(provider =>
      VectorConsistency.checkClient(provider, config.model, embedder).left.map(_.code)
    )

  /** Refuses when the token-derived embedding spend exceeds the embedding cap (USD 0.30 default).
    */
  private[rag] def embeddingCapExceeded(tokens: BigInt, config: LiveEmbeddingConfig): Boolean =
    tokenUsd(tokens, config) > BigDecimal(config.embeddingCapUsd.toString)

  /** Shared manifest/resource validation (identity, model, pointers, complete chunk groups). It
    * applies no approval caps, so the query smoke can reuse it without ingest-sized caps.
    */
  private[rag] def validateManifest(
      config: LiveEmbeddingConfig,
      manifestText: String
  ): Either[String, EmbeddingManifest] =
    providerCheck(config)
      .flatMap(_ => value(EmbeddingManifests.parse(manifestText, config.ingest)))
      .flatMap { manifest =>
        val items = manifest.items
        val validItems = items.nonEmpty && items.size <= config.maxVectors && items.forall { item =>
          EmbeddingValidation.workItem(item).isEmpty && item.embeddingModel == config.model &&
          config.indexNames.get(item.document.documentType).contains(item.indexName) &&
          item.textS3Uri.startsWith(s"s3://${config.textBucket}/${config.textPrefix}/versions/")
        } && items.map(i => (i.indexName, i.vectorKey)).distinct.size == items.size
        val validGroups = items
          .groupBy(i => EmbeddingContracts.groupKey(i.document, i.embeddingModel))
          .values
          .forall { group =>
            val document = group.head.document
            group.map(_.document.chunkCount).distinct == Vector(document.chunkCount) &&
            group.map(i => EmbeddingContracts.wholeTextHash(i.document)).distinct.size == 1 &&
            group.size == document.chunkCount &&
            group
              .map(_.document.chunkOrdinal)
              .sorted
              .zipWithIndex
              .forall((ordinal, index) => ordinal == index)
          }
        if (!validItems || !validGroups) Left("live-manifest-invalid-or-partial-group")
        else if (!config.ledgerRowsFit(items.size)) Left("live-ledger-page-capacity")
        else Right(manifest)
      }

  def preflight(
      configText: String,
      manifestText: String,
      approvalText: String,
      gateText: String,
      runId: String,
      nowEpochSeconds: Long
  ): Either[String, LiveEmbeddingPlan] = try {
    val approval = read[LiveEmbeddingApproval](approvalText)
    if (
      approval.schemaVersion != "scholarchain.embedding-live-approval.v1" ||
      approval.operation != "ingest" || !approval.executionApproved || !approval.pricingValidated || !approval.budgetValidated
    )
      Left("live-approval-required")
    else if (
      approval.runId != runId || runId.trim.isEmpty || approval.environment.trim.isEmpty ||
      approval.phase14GateReference.trim.isEmpty || approval.expiresAtEpochSeconds <= nowEpochSeconds
    )
      Left("live-approval-identity-or-expiry")
    else if (
      approval.configSha256 != StableIds.sha256Hex(configText) ||
      approval.manifestSha256 != StableIds.sha256Hex(manifestText) ||
      approval.phase14GateSha256 != StableIds.sha256Hex(gateText) || gateText.trim.isEmpty
    )
      Left("live-approval-content-mismatch")
    else {
      val config = read[LiveEmbeddingConfig](configText)
      val embedding = config.embedding
      if (config.ingestConcurrency > approval.concurrencyCap)
        Left("live-approval-ingest-concurrency-cap")
      else if (
        config.environment != approval.environment || approval.vectorCap < 1 || approval.concurrencyCap < 1 ||
        approval.embeddingCallCap < 1 || !approval.dollarCapUsd.isFinite || approval.dollarCapUsd <= 0 ||
        config.maxVectors > approval.vectorCap || config.maxConcurrentCalls > approval.concurrencyCap ||
        config.maxEmbeddingCalls > approval.embeddingCallCap || config.dollarCapUsd > approval.dollarCapUsd
      )
        Left("live-approval-cap-mismatch")
      else
        validateManifest(config, manifestText).flatMap { manifest =>
          val items = manifest.items
          val calls = BigInt(items.size) * BigInt(embedding.maxAttempts)
          // Content-derived bound: tokens x attempts x configured USD per million tokens. The
          // dollar estimate takes the larger of it and the configured per-attempt bound.
          val tokens = tokenBound(items.map(_.document.text), config.minBytesPerEmbeddingToken) *
            BigInt(embedding.maxAttempts)
          val perAttempt = BigDecimal(items.size) * BigDecimal(
            config.assumedMaxDollarsPerEmbeddingAttempt.toString
          ) * embedding.maxAttempts
          val embeddingUsd = perAttempt.max(tokenUsd(tokens, config))
          val capExceeded = embeddingCapExceeded(tokens, config)
          val estimate = embeddingUsd +
            BigDecimal(items.size) * BigDecimal(config.assumedMaxStorageDollarsPerVector.toString) +
            BigDecimal(config.fixedOverheadUsd.toString)
          if (
            capExceeded || calls > config.maxEmbeddingCalls || calls > approval.embeddingCallCap ||
            estimate > BigDecimal(config.dollarCapUsd.toString) || estimate > BigDecimal(
              approval.dollarCapUsd.toString
            )
          )
            Left("live-assumed-cost-or-request-bound")
          else
            Right(LiveEmbeddingPlan(config, manifest, approval, calls.toLong, estimate, tokens))
        }
    }
  } catch { case NonFatal(_) => Left("invalid-live-config-manifest-or-approval") }

  /** The ingest embedder: the ports' client behind the lookahead batcher (session-2 plan P26 (b)).
    * Texts per call are the config's `batchSize`, in manifest order.
    */
  private[rag] def batchingEmbedder(
      plan: LiveEmbeddingPlan,
      embedder: EmbeddingClient
  ): LookaheadBatchingEmbeddingClient =
    new LookaheadBatchingEmbeddingClient(
      embedder,
      plan.manifest.items.map(_.document.text),
      plan.config.batchSize
    )

  /** Pure formatting seam; it neither executes ingestion nor constructs providers. `batch` adds the
    * ingest batcher's counters; `embeddingCalls` stays the runner's per-item attempt sum.
    */
  def report(
      plan: LiveEmbeddingPlan,
      result: EmbeddingIngestReport,
      runId: String,
      configSha256: String,
      manifestSha256: String,
      approvalSha256: String,
      batch: Option[EmbeddingBatchStats] = None
  ): ujson.Value = {
    val base = baseReport(plan, result, runId, configSha256, manifestSha256, approvalSha256)
    batch.foreach { b =>
      base("embeddingBatch") = ujson.Obj(
        "batchSize" -> b.batchSize,
        "underlyingCalls" -> b.underlyingCalls.toString,
        "textsSent" -> b.textsSent.toString,
        "servedFromBatch" -> b.servedFromBatch.toString,
        "passThrough" -> b.passThrough.toString,
        "unusedPrefetched" -> b.unusedPrefetched.toString
      )
    }
    base
  }
  private def baseReport(
      plan: LiveEmbeddingPlan,
      result: EmbeddingIngestReport,
      runId: String,
      configSha256: String,
      manifestSha256: String,
      approvalSha256: String
  ): ujson.Obj = ujson.Obj(
    "schemaVersion" -> "scholarchain.embedding-live-report.v1",
    "mode" -> "approved-live",
    "runId" -> runId,
    "region" -> plan.config.region,
    "approvalSha256" -> approvalSha256,
    "configSha256" -> configSha256,
    "manifestSha256" -> manifestSha256,
    "model" -> upickle.default.writeJs(plan.config.model),
    "embeddingProvider" -> plan.config.provider.toOption.map(_.wire).getOrElse("invalid"),
    "embeddingModelId" -> plan.config.model.modelId,
    "embeddingModelVersion" -> plan.config.model.version,
    "dimension" -> plan.config.model.dimension,
    "selectedVectors" -> plan.manifest.items.size,
    "ingestConcurrency" -> plan.config.ingestConcurrency,
    "maxEmbeddingRequests" -> plan.maxEmbeddingRequests.toString,
    "embeddingTokenBound" -> plan.plannedEmbeddingTokens.toString,
    "assumedUpperBoundUsd" -> plan.assumedUpperBoundUsd.toString,
    "billingGuarantee" -> false,
    "written" -> result.written,
    "unchanged" -> result.unchanged,
    "conflicts" -> result.vectorKeyTextConflict,
    "rejected" -> result.rejected,
    "retried" -> result.retried,
    "embeddingCalls" -> result.embeddingCalls,
    "perIndex" -> ujson.Obj.from(
      result.perIndex.toVector.sortBy(_._1).map((k, v) => k -> ujson.Num(v))
    ),
    "rejections" -> ujson.Arr.from(
      result.rejections.map(r => ujson.Obj("key" -> r.key, "reason" -> r.reason))
    ),
    "rejectedReportUri" -> result.rejectedReportUri.map(ujson.Str(_)).getOrElse(ujson.Null),
    "vectorsPerSecond" -> result.vectorsPerSecond,
    "elapsedNanos" -> result.elapsedNanos.toString
  )

  private def awsPorts(config: LiveEmbeddingConfig): LiveEmbeddingPorts = {
    val credentials = ProfileCredentialsProvider.create(config.profile)
    val region = Region.of(config.region)
    val overrideConfig = ClientOverrideConfiguration
      .builder()
      .retryPolicy(RetryPolicy.none())
      .apiCallTimeout(Duration.ofMillis(config.requestTimeoutMillis))
      .build()
    val s3 = S3Client
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrideConfig)
      .build()
    val dynamo = DynamoDbClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrideConfig)
      .build()
    val vectorClient = S3VectorsClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrideConfig)
      .build()
    val provider =
      config.provider.fold(code => throw new ProviderConfigurationError(code), identity)
    // The Bedrock SDK client exists only when Bedrock embeddings are selected. Voyage reads the key
    // from the environment, never from a file, and the key is never printed or stored.
    lazy val bedrock = BedrockRuntimeClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrideConfig)
      .build()
    val embeddingClient = embeddingClientFor(
      config,
      EmbeddingInputType.Document,
      sys.env.get(EmbeddingClientFactory.VoyageKeyEnvName),
      () => bedrock
    ).fold(code => throw new ProviderConfigurationError(code), identity)
    val storageConfig = config.storageSettings
    val objectStore = new S3ObjectStore(s3, storageConfig)
    val artifacts = new DynamoArtifactRegistry(dynamo, storageConfig)
    val vectorConfig = VectorAdapterConfig(
      config.vectorBucket,
      config.model.dimension,
      config.metric,
      putBatchSize = config.batchSize,
      nonFilterableKeys = config.nonFilterableKeys.toSet,
      requestTimeoutMillis = config.requestTimeoutMillis,
      retry = RetryConfig(maxAttempts = 1)
    )
    new LiveEmbeddingPorts {
      val objects: ObjectStore = objectStore
      val registry: ArtifactRegistry = artifacts
      val ledger: RunLedger = new DynamoRunLedger(dynamo, storageConfig)
      val vectors: VectorStore =
        new S3VectorStore(vectorClient, artifacts, vectorConfig, objectStore)
      val embedder: EmbeddingClient = embeddingClient
      def indexesReady(): StorageResult[Unit] = try {
        val matches = config.indexNames.values.toVector.distinct.sorted.forall { name =>
          val existing = vectorClient
            .getIndex(
              GetIndexRequest
                .builder()
                .vectorBucketName(config.vectorBucket)
                .indexName(name)
                .build()
            )
            .index()
          existing.dimension() == config.model.dimension && existing
            .distanceMetricAsString() == config.metric &&
          existing.dataTypeAsString() == "float32" &&
          existing
            .metadataConfiguration()
            .nonFilterableMetadataKeys()
            .asScala
            .toSet == config.nonFilterableKeys.toSet
        }
        if (matches) StorageResult.Found(())
        else StorageResult.Rejected("live-index-configuration-mismatch")
      } catch { case NonFatal(_) => StorageResult.Rejected("live-index-unavailable") }
      def close(): Unit = {
        if (provider == EmbeddingProvider.Bedrock) bedrock.close()
        vectorClient.close(); dynamo.close(); s3.close(); credentials.close()
      }
    }
  }
  def run(
      args: Seq[String],
      factory: LiveEmbeddingConfig => LiveEmbeddingPorts = awsPorts,
      nowEpochSeconds: Long = Instant.now().getEpochSecond
  ): Either[String, ujson.Value] = try {
    val pairs = args.grouped(2).toVector
    if (
      pairs.exists(_.size != 2) || pairs.size != flags.size ||
      pairs.map(_.head).toSet != flags || pairs.map(_.head).distinct.size != flags.size
    )
      Left("invalid-live-arguments")
    else {
      val input = pairs.map(p => p(0) -> p(1)).toMap
      def bounded(path: String, max: Long): String = {
        val p = Path.of(path); require(Files.size(p) <= max); Files.readString(p, UTF_8)
      }
      val configText = bounded(input("--config"), 65536)
      val manifestText =
        bounded(input("--manifest"), LiveEmbeddingConfig.MaxManifestBytesCeiling.toLong)
      val approvalText = bounded(input("--approval"), 65536)
      val approval = read[LiveEmbeddingApproval](approvalText)
      if (!approval.executionApproved || !approval.pricingValidated || !approval.budgetValidated)
        Left("live-approval-required")
      else {
        val gateText = bounded(approval.phase14GateReference, 65536)
        preflight(
          configText,
          manifestText,
          approvalText,
          gateText,
          input("--run-id"),
          nowEpochSeconds
        ).flatMap { plan =>
          val ports = factory(plan.config)
          try {
            val embedder = batchingEmbedder(plan, ports.embedder)
            consistency(plan.config, ports.embedder)
              .flatMap(_ => value(ports.indexesReady()))
              .flatMap { _ =>
                value(
                  new EmbeddingManifestRunner(
                    plan.config.ingest,
                    ports.objects,
                    ports.vectors,
                    ports.registry,
                    ports.ledger,
                    embedder
                  ).run(plan.manifest, input("--run-id"))
                ).flatMap { result =>
                  val report = this.report(
                    plan,
                    result,
                    input("--run-id"),
                    StableIds.sha256Hex(configText),
                    StableIds.sha256Hex(manifestText),
                    StableIds.sha256Hex(approvalText),
                    Some(embedder.stats)
                  )
                  val path = Path.of(input("--report"));
                  Option(path.toAbsolutePath.getParent).foreach(Files.createDirectories(_))
                  Files.writeString(path, report.render(), UTF_8)
                  if (result.rejected > 0 || result.vectorKeyTextConflict > 0)
                    Left("live-ingestion-rejected-items")
                  else Right(report)
                }
              }
          } finally ports.close()
        }
      }
    }
  } catch {
    case e: ProviderConfigurationError => Left(e.code)
    case NonFatal(_)                   => Left("live-input-or-execution-failed")
  }
  // P38: storage's ToolLogging selects the packaged tool logging (root INFO; AWS SDK, Apache HTTP
  // and Netty at WARN) before any logger exists, unless the operator set logback.configurationFile.
  def main(args: Array[String]): Unit = {
    ToolLogging.install()
    run(args.toSeq) match {
      case Right(report) => println(report.render())
      case Left(code)    => throw new IllegalArgumentException(code)
    }
  }
}
