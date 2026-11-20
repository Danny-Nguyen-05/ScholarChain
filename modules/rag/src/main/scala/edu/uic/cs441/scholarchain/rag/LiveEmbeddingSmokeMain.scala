package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import java.time.{Duration, Instant}
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal
import upickle.default.{ReadWriter, read, write}
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.core.retry.RetryPolicy
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.GetIndexRequest
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient

final case class LiveSmokeQuery(
    queryId: String,
    indexName: String,
    text: String,
    expectedVectorKeys: Vector[String],
    topK: Int
) derives ReadWriter
final case class LiveEmbeddingSmokeConfig(
    live: LiveEmbeddingConfig,
    queries: Vector[LiveSmokeQuery],
    samplesPerQuery: Int,
    maxQueryRequests: Long,
    maxQueryEmbeddingCalls: Long,
    maxTopK: Int,
    maxObjectReads: Long,
    assumedMaxDollarsPerQuery: Double,
    assumedMaxDollarsPerObjectRead: Double,
    dollarCapUsd: Double,
    maxObjectBytes: Int = 1024 * 1024,
    schemaVersion: String = "scholarchain.embedding-live-smoke.v1"
) derives ReadWriter
final case class LiveEmbeddingSmokePlan(
    config: LiveEmbeddingSmokeConfig,
    manifest: EmbeddingManifest,
    approval: LiveEmbeddingApproval,
    queryRequests: Long,
    queryEmbeddingRequests: Long,
    objectReadBound: Long,
    assumedUpperBoundUsd: BigDecimal,
    queryEmbeddingTokenBound: BigInt = BigInt(0)
)
final case class LiveSmokeSample(
    queryId: String,
    indexName: String,
    latencyNanos: Long,
    neighborMatched: Boolean,
    verifiedPointers: Int
)
trait LiveEmbeddingSmokePorts extends AutoCloseable {
  def objects: ObjectStore
  def vectors: VectorStore
  def embedder: EmbeddingClient
  def indexesReady(): StorageResult[Unit]
}

/** Future read/query smoke execution only, guarded separately from ingestion. No AWS factory or
  * approved execution route is called in offline tests; only pure planning/reporting and refusal.
  */
object LiveEmbeddingSmokeMain {
  private val flags = Set("--config", "--manifest", "--approval", "--report", "--run-id")
  private def value[A](r: StorageResult[A]): Either[String, A] = r match {
    case StorageResult.Rejected(code) => Left(code)
    case other => StorageResult.value(other).toRight("smoke-port-unavailable")
  }
  def preflight(
      configText: String,
      manifestText: String,
      approvalText: String,
      gateText: String,
      runId: String,
      nowEpochSeconds: Long
  ): Either[String, LiveEmbeddingSmokePlan] = try {
    val approval = read[LiveEmbeddingApproval](approvalText)
    if (
      approval.operation != "query-smoke" || !approval.executionApproved ||
      !approval.pricingValidated || !approval.budgetValidated
    ) Left("smoke-approval-required")
    else if (
      approval.configSha256 != StableIds.sha256Hex(configText) ||
      approval.manifestSha256 != StableIds.sha256Hex(manifestText) ||
      approval.phase14GateSha256 != StableIds.sha256Hex(gateText)
    ) Left("smoke-approval-content-mismatch")
    else if (
      approval.runId != runId || runId.trim.isEmpty || approval.environment.trim.isEmpty ||
      approval.phase14GateReference.trim.isEmpty || gateText.trim.isEmpty ||
      approval.expiresAtEpochSeconds <= nowEpochSeconds
    ) Left("smoke-approval-identity-or-expiry")
    else {
      val config = read[LiveEmbeddingSmokeConfig](configText)
      // N15: a query-smoke approval authorizes only the query* caps and the smoke dollar cap. The
      // shared `live` block is used for model/resource/manifest validation only; the ingest-sized
      // vector/concurrency/embedding-call/dollar caps are neither required of nor compared with
      // the approval, so a person approving a smoke never signs ingest-sized limits.
      val common =
        if (
          config.live.environment != approval.environment || approval.vectorCap < 0 ||
          approval.concurrencyCap < 0 || approval.embeddingCallCap < 0
        ) Left("invalid-smoke-config-or-approval-caps")
        else LiveEmbeddingIngestMain.validateManifest(config.live, manifestText)
      common.flatMap { manifest =>
        val queries = config.queries
        val capsValid = config.schemaVersion == "scholarchain.embedding-live-smoke.v1" &&
          !config.live.nonFilterableKeys.contains("embeddingModel") &&
          config.samplesPerQuery > 0 && config.maxQueryRequests > 0 && config.maxQueryEmbeddingCalls > 0 &&
          config.maxObjectReads > 0 && config.maxTopK > 0 && config.maxTopK <= 100 &&
          config.maxObjectBytes > 0 && config.maxObjectBytes <= 16 * 1024 * 1024 &&
          Vector(
            config.assumedMaxDollarsPerQuery,
            config.assumedMaxDollarsPerObjectRead,
            config.dollarCapUsd
          )
            .forall(v => v.isFinite && v > 0) &&
          approval.dollarCapUsd.isFinite && config.dollarCapUsd <= approval.dollarCapUsd &&
          config.maxQueryRequests <= approval.queryRequestCap &&
          config.maxQueryEmbeddingCalls <= approval.queryEmbeddingCallCap &&
          config.maxObjectReads <= approval.queryObjectReadCap
        val keys = manifest.items.map(i => i.vectorKey -> i.indexName).toMap
        val queriesValid =
          queries.size >= 5 && queries.map(_.queryId).distinct.size == queries.size &&
            queries
              .map(_.indexName)
              .toSet == config.live.indexNames.values.toSet && queries.forall(q =>
              q.queryId.trim.nonEmpty && q.text.trim.nonEmpty &&
                q.text.getBytes(UTF_8).length <= config.live.embedding.maxInputTokens &&
                q.topK > 0 && q.topK <= config.maxTopK && q.expectedVectorKeys.nonEmpty &&
                q.expectedVectorKeys.distinct.size == q.expectedVectorKeys.size && q.expectedVectorKeys.size <= q.topK &&
                q.expectedVectorKeys.forall(key => keys.get(key).contains(q.indexName))
            )
        val queryRequests = BigInt(queries.size) * config.samplesPerQuery
        val embeddings = BigInt(queries.size) * config.live.maxEmbeddingAttempts
        val reads =
          queries.foldLeft(BigInt(0))((sum, q) => sum + BigInt(q.topK) * config.samplesPerQuery)
        // Token-derived bound over the query texts only (no ingest items): tokens x attempts at
        // the configured USD per million tokens; the larger of it and the per-attempt bound.
        val tokens = LiveEmbeddingIngestMain.tokenBound(
          queries.map(_.text),
          config.live.minBytesPerEmbeddingToken
        ) * BigInt(config.live.maxEmbeddingAttempts)
        val embeddingUsd = (BigDecimal(embeddings.toString) * BigDecimal(
          config.live.assumedMaxDollarsPerEmbeddingAttempt.toString
        )).max(LiveEmbeddingIngestMain.tokenUsd(tokens, config.live))
        val dollars = embeddingUsd +
          BigDecimal(queryRequests.toString) * BigDecimal(
            config.assumedMaxDollarsPerQuery.toString
          ) +
          BigDecimal(reads.toString) * BigDecimal(
            config.assumedMaxDollarsPerObjectRead.toString
          ) +
          BigDecimal(config.live.fixedOverheadUsd.toString)
        if (!capsValid || !queriesValid) Left("invalid-smoke-config-or-approval-caps")
        else if (LiveEmbeddingIngestMain.embeddingCapExceeded(tokens, config.live))
          Left("smoke-request-or-assumed-cost-bound")
        else if (
          queryRequests > config.maxQueryRequests || embeddings > config.maxQueryEmbeddingCalls ||
          reads > config.maxObjectReads ||
          dollars > BigDecimal(config.dollarCapUsd.toString)
        ) Left("smoke-request-or-assumed-cost-bound")
        else
          Right(
            LiveEmbeddingSmokePlan(
              config,
              manifest,
              approval,
              queryRequests.toLong,
              embeddings.toLong,
              reads.toLong,
              dollars,
              tokens
            )
          )
      }
    }
  } catch { case NonFatal(_) => Left("invalid-smoke-input") }

  /** Nearest-rank quantiles over measured query SDK durations only, excluding embedding and pointer
    * reads. Fixed sample counts and scope are emitted so latency cannot be misinterpreted.
    */
  def report(
      plan: LiveEmbeddingSmokePlan,
      samples: Vector[LiveSmokeSample],
      runId: String,
      configSha256: String,
      manifestSha256: String,
      approvalSha256: String
  ): ujson.Value = {
    val perIndex = samples.groupBy(_.indexName).toVector.sortBy(_._1).map { (index, rows) =>
      val values = rows.map(_.latencyNanos).sorted
      def quantile(p: Double): ujson.Value = if (values.isEmpty) ujson.Null
      else ujson.Num(values(math.max(0, math.ceil(p * values.size).toInt - 1)).toDouble / 1000000.0)
      index -> ujson.Obj(
        "samples" -> rows.size,
        "p50Millis" -> quantile(.50),
        "p95Millis" -> quantile(.95),
        "neighborMatched" -> rows.count(_.neighborMatched),
        "verifiedPointers" -> rows.map(_.verifiedPointers).sum
      )
    }
    ujson.Obj(
      "schemaVersion" -> "scholarchain.embedding-live-smoke-report.v1",
      "mode" -> "approved-query-smoke",
      "runId" -> runId,
      "region" -> plan.config.live.region,
      "embeddingProvider" -> plan.config.live.provider.toOption.map(_.wire).getOrElse("invalid"),
      "model" -> upickle.default.writeJs(plan.config.live.model),
      "configSha256" -> configSha256,
      "manifestSha256" -> manifestSha256,
      "approvalSha256" -> approvalSha256,
      "queryRequestBound" -> plan.queryRequests.toString,
      "embeddingRequestBound" -> plan.queryEmbeddingRequests.toString,
      "embeddingTokenBound" -> plan.queryEmbeddingTokenBound.toString,
      "objectReadBound" -> plan.objectReadBound.toString,
      "assumedUpperBoundUsd" -> plan.assumedUpperBoundUsd.toString,
      "billingGuarantee" -> false,
      "latencyScope" -> "query SDK call only; nearest-rank p50/p95",
      "sampleCount" -> samples.size,
      "expectedSampleCount" -> plan.queryRequests.toString,
      "allNeighborsMatched" -> samples.forall(_.neighborMatched),
      "allSamplesPresent" -> (samples.size.toLong == plan.queryRequests),
      "verifiedPointers" -> samples.map(_.verifiedPointers).sum,
      "perIndex" -> ujson.Obj.from(perIndex),
      "samples" -> ujson.Arr.from(
        samples.map(s =>
          ujson.Obj(
            "queryId" -> s.queryId,
            "indexName" -> s.indexName,
            "queryLatencyNanos" -> s.latencyNanos.toString,
            "neighborMatched" -> s.neighborMatched,
            "verifiedPointers" -> s.verifiedPointers
          )
        )
      )
    )
  }
  private def awsPorts(config: LiveEmbeddingSmokeConfig): LiveEmbeddingSmokePorts = {
    val live = config.live
    val credentials = ProfileCredentialsProvider.create(live.profile)
    val region = Region.of(live.region)
    val overrides = ClientOverrideConfiguration
      .builder()
      .retryPolicy(RetryPolicy.none())
      .apiCallTimeout(Duration.ofMillis(live.requestTimeoutMillis))
      .build()
    val s3 = S3Client
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrides)
      .build()
    val vectorClient = S3VectorsClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrides)
      .build()
    val provider = live.provider.fold(code => throw new ProviderConfigurationError(code), identity)
    lazy val bedrock = BedrockRuntimeClient
      .builder()
      .region(region)
      .credentialsProvider(credentials)
      .overrideConfiguration(overrides)
      .build()
    // Queries use the Voyage `query` input type with the same model, version tag and dimension as
    // the stored `document` vectors; the consistency check in `run` refuses any difference.
    val embeddingClient = LiveEmbeddingIngestMain
      .embeddingClientFor(
        live,
        EmbeddingInputType.Query,
        sys.env.get(EmbeddingClientFactory.VoyageKeyEnvName),
        () => bedrock
      )
      .fold(code => throw new ProviderConfigurationError(code), identity)
    val storageConfig = edu.uic.cs441.scholarchain.storage.StorageConfig(
      live.textBucket,
      live.tables,
      retry = RetryConfig(maxAttempts = 1),
      maxObjectBytes = config.maxObjectBytes
    )
    val objectsPort = new S3ObjectStore(s3, storageConfig)
    val vectorConfig = VectorAdapterConfig(
      live.vectorBucket,
      live.model.dimension,
      live.metric,
      maxTopK = config.maxTopK,
      maxQueryPages = 1,
      nonFilterableKeys = live.nonFilterableKeys.toSet,
      requestTimeoutMillis = live.requestTimeoutMillis,
      retry = RetryConfig(maxAttempts = 1)
    )
    new LiveEmbeddingSmokePorts {
      val objects: ObjectStore = objectsPort
      // Registry is never used on query; this composition exposes no ingestion or registry writes.
      val vectors: VectorStore =
        new S3VectorStore(vectorClient, new InMemoryArtifactRegistry, vectorConfig, objectsPort)
      val embedder: EmbeddingClient = embeddingClient
      def indexesReady(): StorageResult[Unit] = try {
        val valid = live.indexNames.values.toVector.distinct.sorted.forall { name =>
          val index = vectorClient
            .getIndex(
              GetIndexRequest.builder().vectorBucketName(live.vectorBucket).indexName(name).build()
            )
            .index()
          index.dimension() == live.model.dimension && index
            .distanceMetricAsString() == live.metric &&
          index.dataTypeAsString() == "float32" &&
          index
            .metadataConfiguration()
            .nonFilterableMetadataKeys()
            .asScala
            .toSet == live.nonFilterableKeys.toSet
        }
        if (valid) StorageResult.Found(()) else StorageResult.Rejected("smoke-index-mismatch")
      } catch { case NonFatal(_) => StorageResult.Rejected("smoke-index-unavailable") }
      def close(): Unit = {
        if (provider == EmbeddingProvider.Bedrock) bedrock.close()
        vectorClient.close(); s3.close(); credentials.close()
      }
    }
  }
  private[rag] def pointerKey(uri: String, config: LiveEmbeddingConfig): Either[String, String] =
    try {
      val parsed = java.net.URI.create(uri)
      val key = Option(parsed.getPath).getOrElse("").stripPrefix("/")
      if (
        parsed.getScheme != "s3" || parsed.getHost != config.textBucket || parsed.getUserInfo != null ||
        parsed.getPort != -1 || parsed.getRawQuery != null || parsed.getRawFragment != null ||
        !key.startsWith(config.textPrefix + "/versions/") || key.split('/').contains("..")
      ) Left("smoke-unapproved-text-pointer")
      else Right(key)
    } catch { case NonFatal(_) => Left("smoke-invalid-text-pointer") }
  def run(
      args: Seq[String],
      factory: LiveEmbeddingSmokeConfig => LiveEmbeddingSmokePorts = awsPorts,
      nowEpochSeconds: Long = Instant.now().getEpochSecond
  ): Either[String, ujson.Value] = try {
    val pairs = args.grouped(2).toVector
    if (
      pairs.size != flags.size || pairs.exists(_.size != 2) || pairs.map(_.head).toSet != flags ||
      pairs.map(_.head).distinct.size != flags.size
    ) Left("invalid-smoke-arguments")
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
      if (
        approval.operation != "query-smoke" || !approval.executionApproved ||
        !approval.pricingValidated || !approval.budgetValidated
      ) Left("smoke-approval-required")
      else
        preflight(
          configText,
          manifestText,
          approvalText,
          bounded(approval.phase14GateReference, 65536),
          input("--run-id"),
          nowEpochSeconds
        ).flatMap { plan =>
          val ports = factory(plan.config)
          try
            LiveEmbeddingIngestMain
              .consistency(plan.config.live, ports.embedder)
              .flatMap(_ => value(ports.indexesReady()))
              .flatMap { _ =>
                val samples = Vector.newBuilder[LiveSmokeSample]
                var failure: Option[String] = None
                plan.config.queries.foreach { query =>
                  if (failure.isEmpty) {
                    val embedded = ports.embedder.embed(Seq(query.text))
                    embedded.headOption match {
                      case Some(EmbeddingSuccess(vector, actualModel, _))
                          if embedded.size == 1 && actualModel == plan.config.live.model &&
                            vector.size == actualModel.dimension && vector.forall(_.isFinite) =>
                        var sample = 0
                        while (sample < plan.config.samplesPerQuery && failure.isEmpty) {
                          val started = System.nanoTime()
                          val hitsResult = ports.vectors.query(
                            query.indexName,
                            vector,
                            query.topK,
                            Map("embeddingModel" -> plan.config.live.model.tag)
                          )
                          val nanos = System.nanoTime() - started
                          value(hitsResult) match {
                            case Left(code) => failure = Some(code)
                            case Right(hits) =>
                              if (hits.size > query.topK) failure = Some("smoke-hit-bound")
                              var verified = 0
                              hits.foreach { hit =>
                                if (failure.isEmpty)
                                  pointerKey(
                                    hit.metadata.getOrElse("textS3Uri", ""),
                                    plan.config.live
                                  )
                                    .flatMap(key => value(ports.objects.get(key)))
                                    .flatMap { stored =>
                                      if (stored.bytes.size > plan.config.maxObjectBytes)
                                        Left("smoke-object-byte-bound")
                                      else
                                        SemanticContexts.fromStoredObject(hit, stored).map(_ => ())
                                    } match {
                                    case Left(code) => failure = Some(code)
                                    case Right(_)   => verified += 1
                                  }
                              }
                              if (failure.isEmpty)
                                samples += LiveSmokeSample(
                                  query.queryId,
                                  query.indexName,
                                  nanos,
                                  query.expectedVectorKeys.forall(key => hits.exists(_.key == key)),
                                  verified
                                )
                          }
                          sample += 1
                        }
                      case _ => failure = Some("smoke-query-embedding-failed")
                    }
                  }
                }
                val result = report(
                  plan,
                  samples.result(),
                  input("--run-id"),
                  StableIds.sha256Hex(configText),
                  StableIds.sha256Hex(manifestText),
                  StableIds.sha256Hex(approvalText)
                )
                result.obj("failure") = failure.map(ujson.Str(_)).getOrElse(ujson.Null)
                val rp = Path.of(input("--report"));
                Option(rp.toAbsolutePath.getParent).foreach(Files.createDirectories(_))
                Files.writeString(rp, result.render(), UTF_8)
                if (failure.nonEmpty) Left(failure.get)
                else if (!result("allNeighborsMatched").bool)
                  Left("smoke-expected-neighbor-missing")
                else Right(result)
              }
          finally ports.close()
        }
    }
  } catch {
    case e: ProviderConfigurationError => Left(e.code)
    case NonFatal(_)                   => Left("smoke-input-or-execution-failed")
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
