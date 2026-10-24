package edu.uic.cs441.scholarchain.storage

import java.nio.file.{Files, Path, StandardCopyOption}
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.util.control.NonFatal
import StorageResult.*

/** Explicit fake-only disk snapshot. All mutations still traverse the production port contracts;
  * this class constructs no SDK client and is not a cloud persistence adapter.
  */
final class LocalEmbeddingState private (config: EmbeddingIngestConfig) {
  private val objectMemory = new InMemoryObjectStore
  private val registryMemory = new InMemoryArtifactRegistry
  private val vectorMemory = new InMemoryVectorStore
  private val ledgerMemory = new InMemoryRunLedger
  private val storedObjects = mutable.Map.empty[String, StoredObject]
  private val artifacts = mutable.Map.empty[(String, String), ArtifactRecord]
  private val indexes = mutable.Map.empty[String, (Int, String)]
  private val documents = mutable.Map.empty[(String, String), VectorDocument]
  private val ledgerOperations = mutable.ArrayBuffer.empty[ujson.Obj]
  val objects: ObjectStore = new ObjectStore {
    def get(key: String) = objectMemory.get(key)
    def head(key: String) = objectMemory.head(key)
    def put(
        key: String,
        bytes: Vector[Byte],
        contentType: String,
        metadata: Map[String, String]
    ): StorageResult[ObjectHead] = {
      val result = objectMemory.put(key, bytes, contentType, metadata)
      if (StorageResult.successful(result))
        storedObjects(key) = StorageResult.value(objectMemory.get(key)).get
      result
    }
  }
  val registry: ArtifactRegistry = new ArtifactRegistry {
    def get(id: String, version: String) = registryMemory.get(id, version)
    def latest(id: String) = registryMemory.latest(id)
    def register(
        id: String,
        version: String,
        uri: String,
        hash: String
    ): StorageResult[ArtifactRecord] = {
      val result = registryMemory.register(id, version, uri, hash)
      StorageResult.value(result).foreach(record => artifacts(id -> version) = record)
      result
    }
  }
  val vectors: VectorStore = new VectorStore {
    def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String] = {
      if (dimension != config.dimension || metric != config.metric || !VectorIndexes.names(name))
        return Rejected("local-state-index-config-mismatch")
      val result = vectorMemory.ensureIndex(name, dimension, metric)
      if (StorageResult.successful(result)) indexes(name) = dimension -> metric
      result
    }
    def get(index: String, keys: Vector[String]) = vectorMemory.get(index, keys)
    def query(index: String, vector: Vector[Float], topK: Int, filter: Map[String, String]) =
      vectorMemory.query(index, vector, topK, filter)
    def putBatch(index: String, docs: Vector[VectorDocument]): StorageResult[VectorBatchResult] = {
      val result = vectorMemory.putBatch(index, docs)
      if (StorageResult.successful(result))
        StorageResult
          .value(vectorMemory.get(index, docs.map(_.key)))
          .get
          .foreach(d => documents(index -> d.key) = d)
      result
    }
  }
  private def record[A](event: ujson.Obj)(operation: => StorageResult[A]): StorageResult[A] = {
    val result = operation
    if (StorageResult.successful(result)) ledgerOperations += event
    result
  }
  val ledger: RunLedger = new RunLedger {
    def startRun(id: String) =
      record(ujson.Obj("op" -> "start", "runId" -> id))(ledgerMemory.startRun(id))
    def recordStage(id: String, stage: String) = record(
      ujson.Obj("op" -> "stage", "runId" -> id, "stage" -> stage)
    )(ledgerMemory.recordStage(id, stage))
    def recordFailure(id: String, stage: String, retryCount: Int, reason: String) = record(
      ujson.Obj(
        "op" -> "failure",
        "runId" -> id,
        "stage" -> stage,
        "retryCount" -> retryCount,
        "reason" -> reason
      )
    )(ledgerMemory.recordFailure(id, stage, retryCount, reason))
    def completeStage(id: String, stage: String) = record(
      ujson.Obj("op" -> "stage-complete", "runId" -> id, "stage" -> stage)
    )(ledgerMemory.completeStage(id, stage))
    def completeRun(id: String) =
      record(ujson.Obj("op" -> "complete", "runId" -> id))(ledgerMemory.completeRun(id))
    def getRun(id: String) = ledgerMemory.getRun(id)
  }
  private def pairs(values: Map[String, String]): ujson.Obj =
    ujson.Obj.from(values.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v)))
  private def configuration: ujson.Obj = ujson.Obj(
    "textBucket" -> config.textBucket,
    "textPrefix" -> config.textPrefix,
    "dimension" -> config.dimension,
    "metric" -> config.metric
  )
  private def snapshot: ujson.Obj = ujson.Obj(
    "schemaVersion" -> "scholarchain.embedding-local-state.v1",
    "config" -> configuration,
    "objects" -> ujson.Arr.from(storedObjects.toVector.sortBy(_._1).map { (_, obj) =>
      ujson.Obj(
        "key" -> obj.head.key,
        "bytesBase64" -> java.util.Base64.getEncoder.encodeToString(obj.bytes.toArray),
        "contentType" -> obj.head.contentType,
        "metadata" -> pairs(obj.head.metadata)
      )
    }),
    "artifacts" -> ujson.Arr.from(
      artifacts.toVector.sortBy(_._1).map((_, a) => upickle.default.writeJs(a))
    ),
    "indexes" -> ujson.Arr.from(
      indexes.toVector
        .sortBy(_._1)
        .map((name, v) => ujson.Obj("name" -> name, "dimension" -> v._1, "metric" -> v._2))
    ),
    "vectors" -> ujson.Arr.from(documents.toVector.sortBy(_._1).map { case ((index, _), d) =>
      ujson.Obj(
        "index" -> index,
        "key" -> d.key,
        "values" -> ujson.Arr.from(d.values.map(v => ujson.Num(v.toDouble))),
        "metadata" -> pairs(d.metadata),
        "textHash" -> d.textHash
      )
    }),
    "ledgerOperations" -> ujson.Arr.from(ledgerOperations)
  )
  def save(path: Path): StorageResult[String] = try {
    val absolute = path.toAbsolutePath.normalize()
    Option(absolute.getParent).foreach(Files.createDirectories(_))
    val body = snapshot.render()
    val envelope =
      ujson.Obj("sha256" -> ExportFiles.hash(body), "payload" -> ujson.read(body)).render()
    if (envelope.getBytes(UTF_8).length > LocalEmbeddingState.maxBytes)
      return Rejected("local-state-byte-limit")
    val temporary = Files.createTempFile(absolute.getParent, "embedding-state-", ".json")
    try {
      Files.writeString(temporary, envelope, UTF_8)
      Files.move(
        temporary,
        absolute,
        StandardCopyOption.ATOMIC_MOVE,
        StandardCopyOption.REPLACE_EXISTING
      )
    } finally Files.deleteIfExists(temporary)
    Written(ExportFiles.hash(envelope))
  } catch { case NonFatal(_) => Rejected("local-state-save-failed") }
  private[storage] def restore(payload: ujson.Value): Unit = {
    def requireSuccess(result: StorageResult[?]): Unit = if (!StorageResult.successful(result))
      throw new IllegalArgumentException("invalid fake snapshot")
    def map(value: ujson.Value) = value.obj.toMap.map((k, v) => k -> v.str)
    if (
      payload("schemaVersion").str != "scholarchain.embedding-local-state.v1" || payload(
        "config"
      ) != configuration
    ) throw new IllegalArgumentException("state config")
    payload("objects").arr.foreach { obj =>
      val data = java.util.Base64.getDecoder.decode(obj("bytesBase64").str).toVector
      requireSuccess(
        objects.put(obj("key").str, data, obj("contentType").str, map(obj("metadata")))
      )
    }
    payload("artifacts").arr.foreach { value =>
      val a = upickle.default.read[ArtifactRecord](value);
      requireSuccess(registry.register(a.artifactId, a.version, a.uri, a.hash))
    }
    payload("indexes").arr.foreach { value =>
      requireSuccess(
        vectors.ensureIndex(value("name").str, value("dimension").num.toInt, value("metric").str)
      )
    }
    payload("vectors").arr.foreach { value =>
      val d = VectorDocument(
        value("key").str,
        value("values").arr.map(_.num.toFloat).toVector,
        map(value("metadata")),
        value("textHash").str
      )
      val result = vectors.putBatch(value("index").str, Vector(d))
      requireSuccess(result)
      if (StorageResult.value(result).get.rejected.nonEmpty)
        throw new IllegalArgumentException("invalid vector snapshot")
    }
    payload("ledgerOperations").arr.foreach { e =>
      val id = e("runId").str
      val result: StorageResult[?] = e("op").str match {
        case "start" => ledger.startRun(id)
        case "stage" => ledger.recordStage(id, e("stage").str)
        case "failure" =>
          ledger.recordFailure(id, e("stage").str, e("retryCount").num.toInt, e("reason").str)
        case "stage-complete" => ledger.completeStage(id, e("stage").str)
        case "complete"       => ledger.completeRun(id)
        case _                => throw new IllegalArgumentException("invalid ledger operation")
      }
      requireSuccess(result)
    }
  }
}
object LocalEmbeddingState {
  private[storage] val maxBytes = 64 * 1024 * 1024
  def open(path: Path, config: EmbeddingIngestConfig): StorageResult[LocalEmbeddingState] = try {
    val state = new LocalEmbeddingState(config)
    if (!Files.exists(path)) Found(state)
    else {
      if (!Files.isRegularFile(path) || Files.size(path) > maxBytes)
        return Rejected("local-state-byte-limit")
      val envelope = ujson.read(Files.readString(path, UTF_8))
      val payload = envelope("payload")
      if (envelope("sha256").str != ExportFiles.hash(payload.render()))
        return Rejected("local-state-hash-mismatch")
      state.restore(payload)
      Found(state)
    }
  } catch { case NonFatal(_) => Rejected("invalid-local-embedding-state") }
}
