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
    nonFilterableKeys: Vector[String] = Vector("textS3Uri")
) derives ReadWriter {
  require(schemaVersion == "scholarchain.embedding-live.v1")
  require(
    Vector(environment, region, profile, textBucket, textPrefix, vectorBucket).forall(
      _.trim.nonEmpty
    )
  )
  require(indexNames == EmbeddingContracts.indexes && Set("cosine", "euclidean")(metric))
  require(
    maxVectors > 0 && maxConcurrentCalls > 0 && maxEmbeddingAttempts > 0 && maxEmbeddingCalls > 0
  )
  require(requestTimeoutMillis > 0 && maxManifestBytes > 0 && maxManifestBytes <= 16 * 1024 * 1024)
  require(batchSize > 0 && batchSize <= 500)
  require(
    Vector(dollarCapUsd, assumedMaxDollarsPerEmbeddingAttempt, assumedMaxStorageDollarsPerVector)
      .forall(v => v.isFinite && v > 0) && fixedOverheadUsd.isFinite && fixedOverheadUsd >= 0
  )
  require(
    nonFilterableKeys.distinct.size == nonFilterableKeys.size && nonFilterableKeys.size <= 10 &&
      !nonFilterableKeys.contains("runId") && !nonFilterableKeys.contains("textHash")
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
    batchSize = batchSize
  )
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
    assumedUpperBoundUsd: BigDecimal
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
      val ingest = config.ingest
      val embedding = config.embedding
      if (
        config.environment != approval.environment || approval.vectorCap < 1 || approval.concurrencyCap < 1 ||
        approval.embeddingCallCap < 1 || !approval.dollarCapUsd.isFinite || approval.dollarCapUsd <= 0 ||
        config.maxVectors > approval.vectorCap || config.maxConcurrentCalls > approval.concurrencyCap ||
        config.maxEmbeddingCalls > approval.embeddingCallCap || config.dollarCapUsd > approval.dollarCapUsd
      )
        Left("live-approval-cap-mismatch")
      else
        value(EmbeddingManifests.parse(manifestText, ingest)).flatMap { manifest =>
          val items = manifest.items
          val calls = BigInt(items.size) * BigInt(embedding.maxAttempts)
          val estimate = BigDecimal(items.size) *
            (BigDecimal(
              config.assumedMaxDollarsPerEmbeddingAttempt.toString
            ) * embedding.maxAttempts +
              BigDecimal(config.assumedMaxStorageDollarsPerVector.toString)) + BigDecimal(
              config.fixedOverheadUsd.toString
            )
          val validItems = items.nonEmpty && items.size <= config.maxVectors && items.forall {
            item =>
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
          else if (
            calls > config.maxEmbeddingCalls || calls > approval.embeddingCallCap ||
            estimate > BigDecimal(config.dollarCapUsd.toString) || estimate > BigDecimal(
              approval.dollarCapUsd.toString
            )
          )
            Left("live-assumed-cost-or-request-bound")
          else Right(LiveEmbeddingPlan(config, manifest, approval, calls.toLong, estimate))
        }
    }
  } catch { case NonFatal(_) => Left("invalid-live-config-manifest-or-approval") }

  /** Pure formatting seam; it neither executes ingestion nor constructs providers. */
  def report(
      plan: LiveEmbeddingPlan,
      result: EmbeddingIngestReport,
      runId: String,
      configSha256: String,
      manifestSha256: String,
      approvalSha256: String
  ): ujson.Value = ujson.Obj(
    "schemaVersion" -> "scholarchain.embedding-live-report.v1",
    "mode" -> "approved-live",
    "runId" -> runId,
    "region" -> plan.config.region,
    "approvalSha256" -> approvalSha256,
    "configSha256" -> configSha256,
    "manifestSha256" -> manifestSha256,
    "model" -> upickle.default.writeJs(plan.config.model),
    "embeddingModelId" -> plan.config.model.modelId,
    "embeddingModelVersion" -> plan.config.model.version,
    "dimension" -> plan.config.model.dimension,
    "selectedVectors" -> plan.manifest.items.size,
    "maxEmbeddingRequests" -> plan.maxEmbeddingRequests.toString,
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
    val bedrock = BedrockRuntimeClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrideConfig)
      .build()
    val storageConfig =
      edu.uic.cs441.scholarchain.storage
        .StorageConfig(config.textBucket, config.tables, retry = RetryConfig(maxAttempts = 1))
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
      val embedder: EmbeddingClient = new BedrockEmbeddingClient(bedrock, config.embedding)
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
        bedrock.close(); vectorClient.close(); dynamo.close(); s3.close(); credentials.close()
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
      val manifestText = bounded(input("--manifest"), 16L * 1024 * 1024)
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
            value(ports.indexesReady()).flatMap { _ =>
              value(
                new EmbeddingManifestRunner(
                  plan.config.ingest,
                  ports.objects,
                  ports.vectors,
                  ports.registry,
                  ports.ledger,
                  ports.embedder
                ).run(plan.manifest, input("--run-id"))
              ).flatMap { result =>
                val report = this.report(
                  plan,
                  result,
                  input("--run-id"),
                  StableIds.sha256Hex(configText),
                  StableIds.sha256Hex(manifestText),
                  StableIds.sha256Hex(approvalText)
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
  } catch { case NonFatal(_) => Left("live-input-or-execution-failed") }
  def main(args: Array[String]): Unit = run(args.toSeq) match {
    case Right(report) => println(report.render())
    case Left(code)    => throw new IllegalArgumentException(code)
  }
}
