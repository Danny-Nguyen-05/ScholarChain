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
    batchSize: Int = 100,
    // S3 Vectors per-vector metadata limits, mirrored from VectorAdapterConfig defaults so the
    // budget is enforced before any embedding call (Phase 8 finding R3).
    maxMetadataKeys: Int = 50,
    maxMetadataBytes: Int = 40 * 1024,
    maxFilterableBytes: Int = 2 * 1024,
    nonFilterableKeys: Set[String] = Set("textS3Uri"),
    // Session 2 plan P26 (b): work items processed at once by `EmbeddingManifestRunner`. 1 (the
    // default) is the sequential path, unchanged. Above 1, registry, text-store, embedder and
    // vector-store calls of different items overlap; run-ledger calls stay serialized.
    ingestConcurrency: Int = 1
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
  require(
    maxMetadataKeys > 0 && maxMetadataKeys <= 50 && maxMetadataBytes > 0 && maxMetadataBytes <= 40 * 1024 &&
      maxFilterableBytes > 0 && maxFilterableBytes <= 2 * 1024 && nonFilterableKeys.size <= 10
  )
  require(
    ingestConcurrency >= 1 && ingestConcurrency <= EmbeddingIngestConfig.MaxIngestConcurrency,
    "invalid-ingest-concurrency"
  )
}
object EmbeddingIngestConfig {

  /** Upper bound for `ingestConcurrency`. Ledger calls are serialized, so a 10,000-item run is
    * ledger-bound from about 4 workers on (see `IngestThroughputSpec`); 16 leaves headroom without
    * letting a config raise S3, DynamoDB or embedder request concurrency without limit.
    */
  val MaxIngestConcurrency: Int = 16
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
  *
  * Concurrency (`config.ingestConcurrency` above 1, session-2 plan P26 (b)): work items run on a
  * bounded set of worker threads. Every run-ledger call is serialized by one lock, because each
  * ledger transition rewrites the run root row under an optimistic revision condition, so two
  * concurrent transitions of one run would conflict. Each (index, vector key) identity is prepared
  * by exactly one worker; later manifest duplicates of an identity are settled after all first
  * occurrences, exactly as the sequential path settles them after a flush. Vector writes are
  * batched per index by `batchSize`. Per-item outcomes do not depend on scheduling, and rejections
  * are reported in manifest order. The embedder and the ports must be thread-safe when concurrency
  * is above 1 (the AWS adapters, the in-memory fakes and rag's lookahead batcher are).
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
  import EmbeddingManifestRunner.*
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

  /** Embeds one item and checkpoints the vector. Returns the vector result, the provider attempts
    * and the retries to record on the item's ledger stage.
    */
  private def embedAndSave(i: EmbeddingWorkItem): (StorageResult[VectorDocument], Int, Int) = {
    val results =
      try embedder.embed(Seq(i.document.text))
      catch {
        case NonFatal(_) =>
          Seq(EmbeddingFailure("embedding-client-exception", false, embedder.model, 0))
      }
    val calls = results.map(_.attempts).sum
    if (results.size != 1) (Rejected("embedding-result-cardinality"), calls, 0)
    else {
      val result = results.head
      val retries = math.max(0, result.attempts - 1)
      val vector =
        if (EmbeddingValidation.result(result).nonEmpty || result.model != i.embeddingModel)
          Rejected("embedding-dimension-or-model-mismatch")
        else
          result match {
            case EmbeddingSuccess(values, _, _)
                if config.metric == "cosine" && values.forall(_ == 0f) =>
              Rejected("zero-cosine-vector")
            case EmbeddingSuccess(values, _, _) =>
              savePrepared(i, VectorDocument(i.vectorKey, values, metadata(i), i.textHash))
            case EmbeddingFailure(code, _, _, _) => Rejected(code)
          }
      (vector, calls, retries)
    }
  }

  /** Registry, text-store and embedder steps for the first occurrence of an (index, vector key)
    * identity in a manifest. No ledger call and no shared mutable state: the caller records the
    * outcome, so concurrent calls for distinct identities are independent.
    */
  private def prepareItem(i: EmbeddingWorkItem): Preparation = {
    def settled(outcome: ItemOutcome) = Preparation(outcome, 0, 0)
    registry.get(artifact(i), "binding") match {
      case r if StorageResult.value(r).exists(_.hash != i.textHash) =>
        settled(ItemOutcome.Refused("vectorKeyTextConflict"))
      case r if r != Missing && !StorageResult.successful(r) =>
        settled(ItemOutcome.Refused("embedding-registry-unavailable"))
      case r if StorageResult.value(r).exists(_.uri != i.textS3Uri) =>
        val original = StorageResult.value(r).get
        registry.get(artifact(i), "complete") match {
          case done
              if StorageResult
                .value(done)
                .exists(v => v.hash == i.textHash && v.uri == original.uri) =>
            settled(ItemOutcome.Done)
          case _ => settled(ItemOutcome.Refused("text-pointer-conflict"))
        }
      case _ =>
        val binding = registry.register(artifact(i), "binding", i.textS3Uri, i.textHash)
        if (!StorageResult.successful(binding))
          settled(ItemOutcome.Refused("embedding-binding-failed"))
        else
          registry.get(artifact(i), "complete") match {
            case r
                if StorageResult
                  .value(r)
                  .exists(v => v.hash == i.textHash && v.uri == i.textS3Uri) =>
              settled(ItemOutcome.Done)
            case r if r != Missing =>
              settled(ItemOutcome.Refused("embedding-completion-unavailable"))
            case Missing =>
              val body = bytes(EmbeddingManifests.textJson(i))
              if (
                !StorageResult.successful(
                  objects.put(objectKey(i.textS3Uri).get, body, "application/json", Map.empty)
                )
              ) settled(ItemOutcome.Refused("text-store-write-failed"))
              else {
                val (vector, calls, retries) = prepared(i) match {
                  case Missing => embedAndSave(i)
                  case other   => (other, 0, 0)
                }
                val outcome = vector match {
                  case r if StorageResult.successful(r) =>
                    ItemOutcome.Ready(StorageResult.value(r).get)
                  case Rejected(reason) => ItemOutcome.Refused(reason)
                  case _                => ItemOutcome.Refused("prepared-vector-unavailable")
                }
                Preparation(outcome, calls, retries)
              }
            case _ => settled(ItemOutcome.Refused("embedding-completion-unavailable"))
          }
    }
  }

  /** Binds one rendered document (all its chunks) before any chunk is processed. The binding
    * excludes source runs and ordinals, so shrinking/growing text cannot leave a mixed set. Returns
    * the group error, if any. Groups touch disjoint registry rows.
    */
  private def bindGroup(key: String, items: Vector[EmbeddingWorkItem]): Option[String] = {
    val descriptors = items
      .map(i => i.document.chunkCount -> EmbeddingContracts.wholeTextHash(i.document))
      .distinct
    val invalid = items.iterator
      .flatMap { i =>
        EmbeddingValidation.workItem(i) ++
          Option.when(
            i.embeddingModel != embedder.model || i.embeddingModel.dimension != config.dimension
          )("embedding-model-mismatch") ++
          Option.when(i.document.text.getBytes(UTF_8).length > config.maxTextBytes)(
            "text-byte-limit"
          ) ++
          Option.when(objectKey(i.textS3Uri).isEmpty)("text-pointer-outside-config") ++
          // Pre-embedding budget check: the metadata is fully determined by the work item, so
          // an item the vector adapter would refuse never reaches the embedder.
          Option.when(
            VectorMetadataBudget.exceeds(
              metadata(i),
              config.maxMetadataKeys,
              config.maxMetadataBytes,
              config.maxFilterableBytes,
              config.nonFilterableKeys
            )
          )("metadata-limit")
      }
      .take(1)
      .toVector
      .headOption
    val ordinals = items.map(_.document.chunkOrdinal).sorted
    if (invalid.nonEmpty) invalid
    else if (descriptors.size != 1) Some("vectorKeyTextConflict")
    else if (
      ordinals.size != descriptors.head._1 || !ordinals.zipWithIndex
        .forall((ordinal, index) => ordinal == index)
    ) Some("incomplete-embedding-group")
    else {
      val (count, wholeHash) = descriptors.head
      val hash = StableIds.sha256Hex(
        ujson.Obj("chunkCount" -> count, "wholeTextHash" -> wholeHash).render()
      )
      val id = "embedding-group:" + key
      val uri = "embedding-group://" + StableIds.sha256Hex(key)
      registry.get(id, "v1") match {
        case r
            if StorageResult
              .value(r)
              .exists(record => record.hash == hash && record.uri == uri) =>
          None
        case r if StorageResult.successful(r) => Some("vectorKeyTextConflict")
        case Missing =>
          val legacy = items.map(i => registry.get(artifact(i), "binding"))
          if (legacy.exists(StorageResult.successful)) Some("group-binding-missing")
          else if (legacy.exists(_ != Missing)) Some("embedding-group-registry-unavailable")
          else if (!StorageResult.successful(registry.register(id, "v1", uri, hash))) {
            registry.get(id, "v1") match {
              case r
                  if StorageResult
                    .value(r)
                    .exists(record => record.hash == hash && record.uri == uri) =>
                None
              case r if StorageResult.successful(r) => Some("vectorKeyTextConflict")
              case _                                => Some("embedding-group-registry-unavailable")
            }
          } else None
        case _ => Some("embedding-group-registry-unavailable")
      }
    }
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
    val workers = config.ingestConcurrency
    val start = clockNanos()
    // `lock` guards every counter below and serializes every run-ledger call (see class comment).
    // With one worker it is uncontended and the order of all calls is the sequential order.
    val lock = new Object
    var written = 0; var unchanged = 0; var conflicts = 0; var retries = 0; var calls = 0
    val perIndex = scala.collection.mutable.Map.empty[String, Int].withDefaultValue(0)
    val rejects = scala.collection.mutable.ArrayBuffer.empty[(Int, VectorReject)]
    val stageRetries = scala.collection.mutable.Map.empty[String, Int]
    val pending = scala.collection.mutable.ArrayBuffer.empty[Row]
    var ledgerFailed = false
    if (!StorageResult.successful(ledger.startRun(runId))) return Rejected("run-ledger-unavailable")
    // A completed execution ID is immutable. Use a fresh execution ID for replay observations.
    if (StorageResult.value(ledger.getRun(runId)).exists(_.state == "complete"))
      return Rejected("completed-ingestion-run")
    def ledgerBroken: Boolean = lock.synchronized(ledgerFailed)
    def checked(r: => StorageResult[?]): Unit = lock.synchronized {
      if (!StorageResult.successful(r)) ledgerFailed = true
    }
    def failure(stage: String, reason: String, resume: Boolean): Unit = lock.synchronized {
      val count = stageRetries.getOrElse(stage, 0) + 1
      checked(ledger.recordFailure(runId, stage, count, reason))
      stageRetries(stage) = count
      if (resume) checked(ledger.recordStage(runId, stage))
    }
    def reject(ordinal: Int, i: EmbeddingWorkItem, stage: String, reason: String): Unit =
      lock.synchronized {
        rejects += ordinal -> VectorReject(i.vectorKey, reason)
        if (reason == "vectorKeyTextConflict") conflicts += 1
        failure(stage, reason, false)
      }
    def observeRetries(stage: String, n: Int, code: String): Unit = lock.synchronized {
      retries += n
      (0 until n).foreach(_ => failure(stage, code, true))
    }
    def enterStage(stage: String): Boolean = lock.synchronized {
      val previous = StorageResult.value(ledger.recordStage(runId, stage))
      if (previous.isEmpty) ledgerFailed = true
      stageRetries(stage) = previous.map(_.retryCount).getOrElse(0)
      !ledgerFailed
    }
    def completeUnchanged(stage: String): Unit = lock.synchronized {
      unchanged += 1; checked(ledger.completeStage(runId, stage))
    }
    // One bounded homogeneous index batch.
    def writeBatch(index: String, rows: Vector[Row]): Unit = {
      val result =
        try vectors.putBatch(index, rows.map(_.document))
        catch { case NonFatal(_) => Rejected("vector-write-exception") }
      val retryCount = result match { case Retried(n, _) => n; case _ => 0 }
      lock.synchronized {
        retries += retryCount
        rows.headOption.foreach { row =>
          (0 until retryCount).foreach(_ => failure(row.stage, "vector-write-retry", true))
        }
      }
      StorageResult.value(result) match {
        case None => rows.foreach(r => reject(r.ordinal, r.item, r.stage, "vector-write-failed"))
        case Some(report) =>
          val rejectedByKey = report.rejected.map(r => r.key -> r.reason).toMap
          val accepted = rows.filterNot(row => rejectedByKey.contains(row.item.vectorKey))
          if (
            report.written < 0 || report.unchanged < 0 || report.written + report.unchanged != accepted.size || report.rejected
              .exists(r => !rows.exists(_.item.vectorKey == r.key))
          ) rows.foreach(r => reject(r.ordinal, r.item, r.stage, "vector-result-cardinality"))
          else {
            accepted.foreach { r =>
              if (
                !StorageResult.successful(
                  registry.register(artifact(r.item), "complete", r.item.textS3Uri, r.item.textHash)
                )
              ) reject(r.ordinal, r.item, r.stage, "completion-registry-failed")
              else checked(ledger.completeStage(runId, r.stage))
            }
            // Counts describe the observed vector operation; a later completion failure also
            // appears in rejected, and replay reconciles the durable prepared payload.
            lock.synchronized {
              written += report.written; unchanged += report.unchanged
              perIndex(index) += report.written
            }
            rows.filter(row => rejectedByKey.contains(row.item.vectorKey)).foreach { r =>
              val reason = rejectedByKey(r.item.vectorKey)
              reject(
                r.ordinal,
                r.item,
                r.stage,
                if (reason == "text-hash-conflict") "vectorKeyTextConflict" else reason
              )
            }
          }
      }
    }
    // Sequential flush: grouping is stable in encounter order.
    def flush(): Unit = if (pending.nonEmpty) {
      val batch = pending.toVector; pending.clear()
      batch
        .groupBy(_.item.indexName)
        .toVector
        .sortBy(_._1)
        .foreach((index, rows) => writeBatch(index, rows))
    }
    def settleDuplicate(ordinal: Int, i: EmbeddingWorkItem, stage: String): Unit =
      registry.get(artifact(i), "complete") match {
        case r if StorageResult.value(r).exists(_.hash == i.textHash) => completeUnchanged(stage)
        case _ => reject(ordinal, i, stage, "duplicate-incomplete-work-item")
      }
    def stageKey(i: EmbeddingWorkItem, ordinal: Int): String =
      "embedding-" + ordinal + "-" + StableIds.sha256Hex(i.indexName + "\n" + i.vectorKey).take(24)
    // Bind a complete rendered document before processing any of its chunks.
    val groups = manifest.items
      .groupBy(i => EmbeddingContracts.groupKey(i.document, i.embeddingModel))
      .toVector
      .sortBy(_._1)
    val groupResults = new Array[Option[String]](groups.size)
    parallel(workers, groups.size)(k => groupResults(k) = bindGroup(groups(k)._1, groups(k)._2))
    val groupErrors = groups.indices.flatMap(k => groupResults(k).map(groups(k)._1 -> _)).toMap
    // Item checks that need no I/O, in the sequential order of the original loop.
    def precheck(i: EmbeddingWorkItem): Option[String] = {
      val invalid = EmbeddingValidation.workItem(i)
      groupErrors
        .get(EmbeddingContracts.groupKey(i.document, i.embeddingModel))
        .orElse(invalid.headOption)
        .orElse(
          Option.when(
            i.embeddingModel != embedder.model || i.embeddingModel.dimension != config.dimension
          )("embedding-model-mismatch")
        )
        .orElse(
          Option.when(i.document.text.getBytes(UTF_8).length > config.maxTextBytes)(
            "text-byte-limit"
          )
        )
        .orElse(Option.when(objectKey(i.textS3Uri).isEmpty)("text-pointer-outside-config"))
    }
    def prepareAndRecord(ordinal: Int, i: EmbeddingWorkItem, stage: String): Option[Row] = {
      val p = prepareItem(i)
      lock.synchronized {
        calls += p.embeddingCalls
        observeRetries(stage, p.embeddingRetries, "embedding-retry")
      }
      p.outcome match {
        case ItemOutcome.Done            => completeUnchanged(stage); None
        case ItemOutcome.Refused(reason) => reject(ordinal, i, stage, reason); None
        case ItemOutcome.Ready(document) => Some(Row(ordinal, i, document, stage))
      }
    }
    val seen = scala.collection.mutable.Map.empty[(String, String), String]
    if (workers == 1) {
      manifest.items.zipWithIndex.foreach { (i, ordinal) =>
        val stage = stageKey(i, ordinal)
        val identity = i.indexName -> i.vectorKey
        if (!enterStage(stage)) ()
        else
          precheck(i) match {
            case Some(reason) => reject(ordinal, i, stage, reason)
            case None if seen.get(identity).exists(_ != i.textHash) =>
              reject(ordinal, i, stage, "vectorKeyTextConflict")
            case None if seen.contains(identity) =>
              flush(); settleDuplicate(ordinal, i, stage)
            case None =>
              seen(identity) = i.textHash
              prepareAndRecord(ordinal, i, stage).foreach { row =>
                pending += row; if (pending.size >= config.batchSize) flush()
              }
          }
      }
      flush()
    } else {
      // The same classification as the sequential loop, decided up front without I/O: an early
      // rejection reason, a first occurrence (prepared by one worker) or a later duplicate.
      val plan: Vector[Plan] = manifest.items.map { i =>
        val identity = i.indexName -> i.vectorKey
        precheck(i) match {
          case Some(reason) => Plan.Refuse(reason)
          case None if seen.get(identity).exists(_ != i.textHash) =>
            Plan.Refuse("vectorKeyTextConflict")
          case None if seen.contains(identity) => Plan.Duplicate
          case None                            => seen(identity) = i.textHash; Plan.First
        }
      }
      val buffers = scala.collection.mutable.Map.empty[String, Vector[Row]]
      val bufferLock = new Object
      def enqueue(row: Row): Unit = {
        val full = bufferLock.synchronized {
          val rows = buffers.getOrElse(row.item.indexName, Vector.empty) :+ row
          if (rows.size >= config.batchSize) { buffers -= row.item.indexName; Some(rows) }
          else { buffers(row.item.indexName) = rows; None }
        }
        full.foreach(rows => writeBatch(row.item.indexName, rows))
      }
      val active = plan.indices.filter(plan(_) != Plan.Duplicate).toVector
      parallel(workers, active.size) { k =>
        val ordinal = active(k)
        val i = manifest.items(ordinal)
        val stage = stageKey(i, ordinal)
        if (!ledgerBroken && enterStage(stage)) plan(ordinal) match {
          case Plan.Refuse(reason) => reject(ordinal, i, stage, reason)
          case _                   => prepareAndRecord(ordinal, i, stage).foreach(enqueue)
        }
      }
      val remaining = bufferLock.synchronized(buffers.toVector.sortBy(_._1))
      parallel(workers, remaining.size)(k => writeBatch(remaining(k)._1, remaining(k)._2))
      plan.indices.filter(plan(_) == Plan.Duplicate).foreach { ordinal =>
        val i = manifest.items(ordinal)
        val stage = stageKey(i, ordinal)
        if (!ledgerBroken && enterStage(stage)) settleDuplicate(ordinal, i, stage)
      }
    }
    if (ledgerFailed) return Rejected("run-ledger-unavailable")
    // Manifest order when items ran concurrently, so the report and its S3 key are deterministic.
    val rejections =
      (if (workers == 1) rejects.toVector else rejects.toVector.sortBy(_._1)).map(_._2)
    var reportUri: Option[String] = None
    if (rejections.nonEmpty) {
      val body = bytes(
        ujson
          .Obj(
            "runId" -> runId,
            "rejected" -> ujson.Arr
              .from(rejections.map(r => ujson.Obj("key" -> r.key, "reason" -> r.reason)))
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
      rejections.size,
      retries,
      perIndex.toMap,
      calls,
      math.max(0, clockNanos() - start),
      rejections,
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
private[storage] object EmbeddingManifestRunner {
  enum ItemOutcome {
    case Done
    case Refused(reason: String)
    case Ready(document: VectorDocument)
  }
  final case class Preparation(outcome: ItemOutcome, embeddingCalls: Int, embeddingRetries: Int)
  final case class Row(
      ordinal: Int,
      item: EmbeddingWorkItem,
      document: VectorDocument,
      stage: String
  )
  enum Plan {
    case Refuse(reason: String)
    case First
    case Duplicate
  }

  /** Runs `task(0 until count)` on at most `threads` daemon threads, each taking the next index in
    * order. One thread runs everything inline. The first exception stops further tasks and is
    * rethrown after every started task has finished, as the sequential loop would have thrown it.
    */
  def parallel(threads: Int, count: Int)(task: Int => Unit): Unit =
    if (threads <= 1 || count <= 1) (0 until count).foreach(task)
    else {
      val next = new java.util.concurrent.atomic.AtomicInteger(0)
      val failed = new java.util.concurrent.atomic.AtomicReference[Throwable](null)
      val pool = (0 until math.min(threads, count)).map { n =>
        val t = new Thread(
          () => {
            var k = next.getAndIncrement()
            while (k < count && failed.get == null) {
              try task(k)
              catch { case e: Throwable => failed.compareAndSet(null, e) }
              k = next.getAndIncrement()
            }
          },
          s"embedding-ingest-$n"
        )
        t.setDaemon(true); t
      }
      pool.foreach(_.start())
      try pool.foreach(_.join())
      catch {
        case e: InterruptedException =>
          failed.compareAndSet(null, e); pool.foreach(_.interrupt()); pool.foreach(_.join())
          Thread.currentThread().interrupt()
      }
      Option(failed.get).foreach(e => throw e)
    }
}
