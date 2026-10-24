package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal
import upickle.default.{ReadWriter, read, write}
import StorageResult.*

final case class EmbeddingManifest(
    items: Vector[EmbeddingWorkItem],
    schemaVersion: String = "scholarchain.embedding-manifest.v1"
) derives ReadWriter
final case class EmbeddingIngestConfig(
    textBucket: String,
    textPrefix: String,
    dimension: Int,
    metric: String = "cosine",
    maxManifestItems: Int = 10000,
    maxManifestBytes: Int = 16 * 1024 * 1024,
    maxTextBytes: Int = 1024 * 1024,
    batchSize: Int = 100
) {
  require(textBucket.nonEmpty && !textBucket.contains('/') && !textBucket.exists(_.isWhitespace))
  require(
    textPrefix.nonEmpty && !textPrefix.startsWith("/") && !textPrefix
      .endsWith("/") && !textPrefix.split('/').contains("..")
  )
  require(dimension >= 1 && dimension <= 4096 && Set("cosine", "euclidean")(metric))
  require(
    maxManifestItems > 0 && maxManifestBytes > 0 && maxTextBytes > 0 && batchSize > 0 && batchSize <= 500
  )
}
final case class EmbeddingIngestReport(
    written: Int,
    unchanged: Int,
    vectorKeyTextConflict: Int,
    rejected: Int,
    retried: Int,
    perIndex: Map[String, Int],
    embeddingCalls: Int,
    elapsedNanos: Long,
    rejections: Vector[VectorReject],
    rejectedReportUri: Option[String]
) {
  def vectorsPerSecond: Double =
    if (elapsedNanos <= 0) 0.0 else written.toDouble * 1000000000.0 / elapsedNanos
}
object EmbeddingManifests {
  private def canonical(value: ujson.Value): ujson.Value = value match {
    case o: ujson.Obj =>
      ujson.Obj.from(o.obj.toVector.sortBy(_._1).map((k, v) => k -> canonical(v)))
    case a: ujson.Arr => ujson.Arr.from(a.arr.map(canonical))
    case other        => other
  }
  def textJson(item: EmbeddingWorkItem): String = textJson(item.document)
  def textJson(document: EmbeddingDocument): String = canonical(
    ujson.Obj(
      "document" -> upickle.default.writeJs(document),
      "textHash" -> EmbeddingContracts.textHash(document.text)
    )
  ).render()

  def item(
      document: EmbeddingDocument,
      model: EmbeddingModel,
      config: EmbeddingIngestConfig
  ): EmbeddingWorkItem = {
    val hash = EmbeddingContracts.textHash(document.text)
    val key = StorageKeys.versioned(
      config.textPrefix,
      StableIds.sha256Hex(textJson(document)),
      StableIds.sha256Hex(document.documentId) + ".json"
    )
    EmbeddingWorkItem(
      EmbeddingContracts.vectorKey(document, model),
      EmbeddingContracts.indexes(document.documentType),
      document,
      s"s3://${config.textBucket}/$key",
      hash,
      model
    )
  }
  def parse(json: String, config: EmbeddingIngestConfig): StorageResult[EmbeddingManifest] = {
    if (json.getBytes(UTF_8).length > config.maxManifestBytes) Rejected("manifest-byte-limit")
    else
      try {
        val manifest = read[EmbeddingManifest](json)
        if (manifest.schemaVersion != "scholarchain.embedding-manifest.v1")
          Rejected("unsupported-manifest-schema")
        else if (manifest.items.size > config.maxManifestItems) Rejected("manifest-item-limit")
        else Found(manifest)
      } catch { case NonFatal(_) => Rejected("malformed-embedding-manifest") }
  }
}

/** Bounded local composition, with injected ports only. Does not create indexes or SDK clients.
  * Prepared vectors are durable checkpoints: an ambiguous vector write replays the same payload,
  * rather than re-embedding text into a conflicting Phase 7 immutable payload reservation.
  */
final class EmbeddingManifestRunner(
    config: EmbeddingIngestConfig,
    objects: ObjectStore,
    vectors: VectorStore,
    registry: ArtifactRegistry,
    ledger: RunLedger,
    embedder: EmbeddingClient,
    clockNanos: () => Long = () => System.nanoTime(),
    logEvent: String => Unit = event =>
      org.slf4j.LoggerFactory.getLogger(classOf[EmbeddingManifestRunner]).info(event)
) {
  private def bytes(text: String) = text.getBytes(UTF_8).toVector
  private def artifact(item: EmbeddingWorkItem) =
    "embedding:" + StorageKeys.composite(item.indexName, item.vectorKey)
  private def objectKey(uri: String): Option[String] = {
    val start = s"s3://${config.textBucket}/"
    Option
      .when(uri.startsWith(start))(uri.substring(start.length))
      .filter(k =>
        k.startsWith(config.textPrefix + "/") && k.contains("/versions/") && !k
          .split('/')
          .contains("..") && !k.contains('?') && !k.contains('#')
      )
  }
  private def metadata(i: EmbeddingWorkItem): Map[String, String] = {
    val d = i.document
    EmbeddingVectorMetadata(
      d.documentType,
      d.entityId,
      d.windowId,
      d.runId,
      i.textS3Uri,
      i.textHash,
      i.embeddingModel,
      d.templateVersion,
      d.documentId,
      identityFields = d.identityFields,
      chunkPolicyVersion = d.chunkPolicyVersion,
      chunkOrdinal = d.chunkOrdinal
    ).compact
  }
  private def payload(d: VectorDocument): String = ujson
    .Obj(
      "key" -> d.key,
      "values" -> ujson.Arr.from(d.values.map(v => ujson.Num(v.toDouble))),
      "metadata" -> ujson.Obj
        .from(d.metadata.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v))),
      "textHash" -> d.textHash
    )
    .render()
  private def decode(text: String): VectorDocument = {
    val v = ujson.read(text)
    VectorDocument(
      v("key").str,
      v("values").arr.map(_.num.toFloat).toVector,
      v("metadata").obj.toMap.map((k, v) => k -> v.str),
      v("textHash").str
    )
  }
  private def prepared(i: EmbeddingWorkItem): StorageResult[VectorDocument] =
    registry.get(artifact(i), "prepared") match {
      case Missing => Missing
      case r if StorageResult.successful(r) =>
        val record = StorageResult.value(r).get
        objectKey(record.uri) match {
          case None => Rejected("prepared-vector-pointer-invalid")
          case Some(key) =>
            objects.get(key) match {
              case o if StorageResult.successful(o) =>
                val stored = StorageResult.value(o).get
                if (StorageKeys.sha256(stored.bytes) != record.hash)
                  Rejected("prepared-vector-hash-mismatch")
                else
                  try {
                    val d = decode(new String(stored.bytes.toArray, UTF_8))
                    if (
                      d.key != i.vectorKey || d.textHash != i.textHash || d.metadata != metadata(
                        i
                      ) || d.values.size != config.dimension || d.values.exists(v =>
                        !v.isFinite
                      ) || (config.metric == "cosine" && d.values.forall(_ == 0f))
                    ) Rejected("prepared-vector-conflict")
                    else Found(d)
                  } catch { case NonFatal(_) => Rejected("prepared-vector-malformed") }
              case _ => Rejected("prepared-vector-unavailable")
            }
        }
      case _ => Rejected("embedding-registry-unavailable")
    }
  private def savePrepared(
      i: EmbeddingWorkItem,
      d: VectorDocument
  ): StorageResult[VectorDocument] = {
    val body = bytes(payload(d)); val hash = StorageKeys.sha256(body)
    val key = StorageKeys.versioned(config.textPrefix + "/prepared", hash, "vector.json")
    val uri = s"s3://${config.textBucket}/$key"
    if (!StorageResult.successful(objects.put(key, body, "application/json", Map.empty)))
      Rejected("prepared-vector-write-failed")
    else if (StorageResult.successful(registry.register(artifact(i), "prepared", uri, hash)))
      Found(d)
    else prepared(i) // A concurrent identical-text worker may have won the immutable checkpoint.
  }

  def run(manifest: EmbeddingManifest, runId: String): StorageResult[EmbeddingIngestReport] = {
    if (manifest.schemaVersion != "scholarchain.embedding-manifest.v1")
      return Rejected("unsupported-manifest-schema")
    if (runId.trim.isEmpty) return Rejected("invalid-run-id")
    if (manifest.items.size > config.maxManifestItems) return Rejected("manifest-item-limit")
    if (write(manifest).getBytes(UTF_8).length > config.maxManifestBytes)
      return Rejected("manifest-byte-limit")
    if (
      EmbeddingValidation
        .model(embedder.model)
        .nonEmpty || embedder.model.dimension != config.dimension
    ) return Rejected("embedding-dimension-mismatch")
    val start = clockNanos()
    var written = 0; var unchanged = 0; var conflicts = 0; var retries = 0; var calls = 0
    val perIndex = scala.collection.mutable.Map.empty[String, Int].withDefaultValue(0)
    val rejects = scala.collection.mutable.ArrayBuffer.empty[VectorReject]
    val stageRetries = scala.collection.mutable.Map.empty[String, Int]
    val pending =
      scala.collection.mutable.ArrayBuffer.empty[(EmbeddingWorkItem, VectorDocument, String)]
    var ledgerFailed = false
    if (!StorageResult.successful(ledger.startRun(runId))) return Rejected("run-ledger-unavailable")
    // A completed execution ID is immutable. Use a fresh execution ID for replay observations.
    if (StorageResult.value(ledger.getRun(runId)).exists(_.state == "complete"))
      return Rejected("completed-ingestion-run")
    def checked(r: StorageResult[?]): Unit = if (!StorageResult.successful(r)) ledgerFailed = true
    def failure(stage: String, reason: String, resume: Boolean): Unit = {
      val count = stageRetries.getOrElse(stage, 0) + 1
      checked(ledger.recordFailure(runId, stage, count, reason))
      stageRetries(stage) = count
      if (resume) checked(ledger.recordStage(runId, stage))
    }
    def reject(i: EmbeddingWorkItem, stage: String, reason: String): Unit = {
      rejects += VectorReject(i.vectorKey, reason)
      if (reason == "vectorKeyTextConflict") conflicts += 1
      failure(stage, reason, false)
    }
    def observeRetries(stage: String, n: Int, code: String): Unit = {
      retries += n
      (0 until n).foreach(_ => failure(stage, code, true))
    }
    def flush(): Unit = if (pending.nonEmpty) {
      val batch = pending.toVector; pending.clear()
      // One bounded homogeneous index batch. Grouping is stable in encounter order.
      batch.groupBy(_._1.indexName).toVector.sortBy(_._1).foreach { (index, rows) =>
        val result =
          try vectors.putBatch(index, rows.map(_._2))
          catch { case NonFatal(_) => Rejected("vector-write-exception") }
        val retryCount = result match { case Retried(n, _) => n; case _ => 0 }
        retries += retryCount
        rows.headOption.foreach { (_, _, stage) =>
          (0 until retryCount).foreach(_ => failure(stage, "vector-write-retry", true))
        }
        StorageResult.value(result) match {
          case None => rows.foreach((i, _, s) => reject(i, s, "vector-write-failed"))
          case Some(report) =>
            val rejectedByKey = report.rejected.map(r => r.key -> r.reason).toMap
            val accepted = rows.filterNot(row => rejectedByKey.contains(row._1.vectorKey))
            if (
              report.written < 0 || report.unchanged < 0 || report.written + report.unchanged != accepted.size || report.rejected
                .exists(r => !rows.exists(_._1.vectorKey == r.key))
            ) rows.foreach((i, _, s) => reject(i, s, "vector-result-cardinality"))
            else {
              accepted.foreach { (i, _, s) =>
                if (
                  !StorageResult
                    .successful(registry.register(artifact(i), "complete", i.textS3Uri, i.textHash))
                ) reject(i, s, "completion-registry-failed")
                else checked(ledger.completeStage(runId, s))
              }
              // Counts describe the observed vector operation; a later completion failure also
              // appears in rejected, and replay reconciles the durable prepared payload.
              written += report.written; unchanged += report.unchanged
              perIndex(index) += report.written
              rows.filter(row => rejectedByKey.contains(row._1.vectorKey)).foreach { (i, _, s) =>
                val reason = rejectedByKey(i.vectorKey)
                reject(
                  i,
                  s,
                  if (reason == "text-hash-conflict") "vectorKeyTextConflict" else reason
                )
              }
            }
        }
      }
    }
    val seen = scala.collection.mutable.Map.empty[(String, String), String]
    manifest.items.zipWithIndex.foreach { (i, ordinal) =>
      val stage = "embedding-" + ordinal + "-" + StableIds
        .sha256Hex(i.indexName + "\n" + i.vectorKey)
        .take(24)
      val previous = StorageResult.value(ledger.recordStage(runId, stage))
      if (previous.isEmpty) ledgerFailed = true
      stageRetries(stage) = previous.map(_.retryCount).getOrElse(0)
      val invalid = EmbeddingValidation.workItem(i)
      val identity = i.indexName -> i.vectorKey
      if (ledgerFailed) ()
      else if (invalid.nonEmpty) reject(i, stage, invalid.head)
      else if (i.embeddingModel != embedder.model || i.embeddingModel.dimension != config.dimension)
        reject(i, stage, "embedding-model-mismatch")
      else if (i.document.text.getBytes(UTF_8).length > config.maxTextBytes)
        reject(i, stage, "text-byte-limit")
      else if (objectKey(i.textS3Uri).isEmpty) reject(i, stage, "text-pointer-outside-config")
      else if (seen.get(identity).exists(_ != i.textHash)) reject(i, stage, "vectorKeyTextConflict")
      else if (seen.contains(identity)) {
        flush();
        registry.get(artifact(i), "complete") match {
          case r if StorageResult.value(r).exists(_.hash == i.textHash) =>
            unchanged += 1; checked(ledger.completeStage(runId, stage))
          case _ => reject(i, stage, "duplicate-incomplete-work-item")
        }
      } else {
        seen(identity) = i.textHash
        registry.get(artifact(i), "binding") match {
          case r if StorageResult.value(r).exists(_.hash != i.textHash) =>
            reject(i, stage, "vectorKeyTextConflict")
          case r if r != Missing && !StorageResult.successful(r) =>
            reject(i, stage, "embedding-registry-unavailable")
          case r if StorageResult.value(r).exists(_.uri != i.textS3Uri) =>
            val original = StorageResult.value(r).get
            registry.get(artifact(i), "complete") match {
              case done
                  if StorageResult
                    .value(done)
                    .exists(v => v.hash == i.textHash && v.uri == original.uri) =>
                unchanged += 1; checked(ledger.completeStage(runId, stage))
              case _ => reject(i, stage, "text-pointer-conflict")
            }
          case _ =>
            val binding = registry.register(artifact(i), "binding", i.textS3Uri, i.textHash)
            if (!StorageResult.successful(binding)) reject(i, stage, "embedding-binding-failed")
            else
              registry.get(artifact(i), "complete") match {
                case r
                    if StorageResult
                      .value(r)
                      .exists(v => v.hash == i.textHash && v.uri == i.textS3Uri) =>
                  unchanged += 1; checked(ledger.completeStage(runId, stage))
                case r if r != Missing => reject(i, stage, "embedding-completion-unavailable")
                case Missing =>
                  val body = bytes(EmbeddingManifests.textJson(i))
                  if (
                    !StorageResult.successful(
                      objects.put(objectKey(i.textS3Uri).get, body, "application/json", Map.empty)
                    )
                  ) reject(i, stage, "text-store-write-failed")
                  else {
                    val cached = prepared(i)
                    val vector = cached match {
                      case Missing =>
                        val results =
                          try embedder.embed(Seq(i.document.text))
                          catch {
                            case NonFatal(_) =>
                              Seq(
                                EmbeddingFailure(
                                  "embedding-client-exception",
                                  false,
                                  embedder.model,
                                  0
                                )
                              )
                          }
                        calls += results.map(_.attempts).sum
                        if (results.size != 1) Rejected("embedding-result-cardinality")
                        else {
                          val result = results.head
                          observeRetries(stage, math.max(0, result.attempts - 1), "embedding-retry")
                          if (
                            EmbeddingValidation
                              .result(result)
                              .nonEmpty || result.model != i.embeddingModel
                          ) Rejected("embedding-dimension-or-model-mismatch")
                          else
                            result match {
                              case EmbeddingSuccess(values, _, _)
                                  if config.metric == "cosine" && values.forall(_ == 0f) =>
                                Rejected("zero-cosine-vector")
                              case EmbeddingSuccess(values, _, _) =>
                                savePrepared(
                                  i,
                                  VectorDocument(i.vectorKey, values, metadata(i), i.textHash)
                                )
                              case EmbeddingFailure(code, _, _, _) => Rejected(code)
                            }
                        }
                      case other => other
                    }
                    vector match {
                      case r if StorageResult.successful(r) =>
                        pending += ((i, StorageResult.value(r).get, stage));
                        if (pending.size >= config.batchSize) flush()
                      case Rejected(reason) => reject(i, stage, reason)
                      case _                => reject(i, stage, "prepared-vector-unavailable")
                    }
                  }
                case _ => reject(i, stage, "embedding-completion-unavailable")
              }
        }
      }
    }
    flush()
    if (ledgerFailed) return Rejected("run-ledger-unavailable")
    var reportUri: Option[String] = None
    if (rejects.nonEmpty) {
      val body = bytes(
        ujson
          .Obj(
            "runId" -> runId,
            "rejected" -> ujson.Arr
              .from(rejects.map(r => ujson.Obj("key" -> r.key, "reason" -> r.reason)))
          )
          .render()
      )
      val key = StorageKeys.versioned(
        config.textPrefix + "/rejected",
        StorageKeys.sha256(body),
        "report.json"
      )
      if (!StorageResult.successful(objects.put(key, body, "application/json", Map.empty)))
        return Rejected("rejected-report-write-failed")
      reportUri = Some(s"s3://${config.textBucket}/$key")
    } else if (!StorageResult.successful(ledger.completeRun(runId)))
      return Rejected("run-ledger-completion-failed")
    val report = EmbeddingIngestReport(
      written,
      unchanged,
      conflicts,
      rejects.size,
      retries,
      perIndex.toMap,
      calls,
      math.max(0, clockNanos() - start),
      rejects.toVector,
      reportUri
    )
    logEvent(
      ujson
        .Obj(
          "event" -> "embedding_ingest",
          "runId" -> runId,
          "written" -> report.written,
          "unchanged" -> report.unchanged,
          "rejected" -> report.rejected,
          "vectorKeyTextConflict" -> report.vectorKeyTextConflict,
          "retried" -> report.retried,
          "embeddingCalls" -> report.embeddingCalls,
          "perIndex" -> ujson.Obj
            .from(report.perIndex.toVector.sortBy(_._1).map((k, v) => k -> ujson.Num(v)))
        )
        .render()
    )
    Written(report)
  }
}
