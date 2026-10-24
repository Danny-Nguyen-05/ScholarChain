package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import software.amazon.awssdk.services.sqs.SqsClient
import software.amazon.awssdk.services.sqs.model.*
import scala.jdk.CollectionConverters.*
import StorageResult.*

class EmbeddingStorageSpec extends AnyFunSuite {
  private val model = EmbeddingModel("fixture-embedding", "v1", 2)
  private val config = EmbeddingIngestConfig("fixture-text", "rag", 2, batchSize = 2)
  private def doc(text: String = "distributed graph", ordinal: Int = 0): EmbeddingDocument = {
    val id =
      StableIds.chunkOrProfileId("fixture-entity", "v1", "paper", Some(ordinal), text).toOption.get
    EmbeddingDocument(
      id,
      "paper",
      "fixture-entity",
      "fixture-window",
      "fixture-source-run",
      "fixture-template-v1",
      text,
      Vector(SummarySourceRef("works", "fixture-work", "title")),
      "paper-summary-fallback",
      identityFields = Map("sourceDataset" -> "synthetic-fixture"),
      chunkPolicyVersion = "fixture-chunk-policy-v1",
      chunkOrdinal = ordinal
    )
  }
  private class Embed extends EmbeddingClient {
    val model = EmbeddingStorageSpec.this.model
    var calls = 0
    var response: EmbeddingResult = EmbeddingSuccess(Vector(1f, 0f), model, 1)
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      calls += texts.size; texts.map(_ => response)
    }
  }
  private class RecordingVectors extends VectorStore {
    private val underlying = new InMemoryVectorStore
    var putCalls = 0
    def ensureIndex(name: String, dimension: Int, metric: String) =
      underlying.ensureIndex(name, dimension, metric)
    def get(index: String, keys: Vector[String]) = underlying.get(index, keys)
    def query(index: String, vector: Vector[Float], topK: Int, filter: Map[String, String]) =
      underlying.query(index, vector, topK, filter)
    def putBatch(index: String, documents: Vector[VectorDocument]) = {
      putCalls += 1
      underlying.putBatch(index, documents)
    }
  }
  private def fixture() = {
    val objects = new InMemoryObjectStore
    val registry = new InMemoryArtifactRegistry
    val ledger = new InMemoryRunLedger
    val vectors = new RecordingVectors
    vectors.ensureIndex("paper-abstract-v1", 2, "cosine")
    val embed = new Embed
    val runner = new EmbeddingManifestRunner(config, objects, vectors, registry, ledger, embed)
    (objects, registry, ledger, vectors, embed, runner)
  }
  test(
    "manifest ingestion stores authoritative JSON and compact vector metadata; replay skips embedding"
  ) {
    val (objects, _, ledger, vectors, embed, runner) = fixture()
    val item = EmbeddingManifests.item(doc(), model, config)
    val manifest = EmbeddingManifest(Vector(item))
    val first = StorageResult.value(runner.run(manifest, "fixture-ingestion-1")).get
    assert(first.written == 1 && first.unchanged == 0 && first.rejected == 0)
    assert(first.perIndex == Map("paper-abstract-v1" -> 1) && first.embeddingCalls == 1)
    val textObject =
      StorageResult.value(objects.get(item.textS3Uri.stripPrefix("s3://fixture-text/"))).get
    val body = ujson.read(new String(textObject.bytes.toArray, UTF_8))
    assert(body("document")("text").str == "distributed graph")
    assert(body("textHash").str == StableIds.sha256Hex("distributed graph"))
    val vector = StorageResult.value(vectors.get(item.indexName, Vector(item.vectorKey))).get.head
    assert(vector.metadata("sourceDataset") == "synthetic-fixture")
    assert(vector.metadata("documentId") == item.document.documentId)
    assert(vector.metadata("chunkPolicyVersion") == "fixture-chunk-policy-v1")
    assert(vector.metadata("chunkOrdinal") == "0")
    assert(!vector.metadata.keySet.exists(Set("text", "abstract", "content")))
    val writes = objects.writeOrder.size
    val replay = StorageResult.value(runner.run(manifest, "fixture-ingestion-2")).get
    assert(replay.written == 0 && replay.unchanged == 1 && replay.embeddingCalls == 0)
    assert(embed.calls == 1 && objects.writeOrder.size == writes)
    assert(StorageResult.value(ledger.getRun("fixture-ingestion-2")).get.state == "complete")
  }
  test(
    "text pointers address canonical full provenance and new model ingestion preserves both source documents"
  ) {
    val (objects, registry, ledger, vectors, embed, runner) = fixture()
    val original = EmbeddingManifests.item(doc(), model, config)
    assert(
      StorageResult
        .value(runner.run(EmbeddingManifest(Vector(original)), "provenance-first"))
        .get
        .written == 1
    )
    val moved = doc().copy(
      runId = "other-source-run",
      identityFields = Map("sourceDataset" -> "other-fixture")
    )
    val sameModel = EmbeddingManifests.item(moved, model, config)
    assert(sameModel.textS3Uri != original.textS3Uri)
    val skipped =
      StorageResult.value(runner.run(EmbeddingManifest(Vector(sameModel)), "provenance-skip")).get
    assert(skipped.unchanged == 1 && skipped.embeddingCalls == 0)
    val nextModel = model.copy(version = "v2")
    val nextEmbed = new EmbeddingClient {
      val model = nextModel
      def embed(texts: Seq[String]): Seq[EmbeddingResult] =
        texts.map(_ => EmbeddingSuccess(Vector(0f, 1f), model, 1))
    }
    val next = EmbeddingManifests.item(moved, nextModel, config)
    assert(next.vectorKey != original.vectorKey)
    assert(
      sameModel.vectorKey == original.vectorKey
    ) // Source run is provenance, not slot identity.
    val nextRunner =
      new EmbeddingManifestRunner(config, objects, vectors, registry, ledger, nextEmbed)
    assert(
      StorageResult
        .value(nextRunner.run(EmbeddingManifest(Vector(next)), "provenance-new-model"))
        .get
        .written == 1
    )
    val oldBody =
      StorageResult.value(objects.get(original.textS3Uri.stripPrefix("s3://fixture-text/"))).get
    val newBody =
      StorageResult.value(objects.get(next.textS3Uri.stripPrefix("s3://fixture-text/"))).get
    assert(
      ujson
        .read(new String(oldBody.bytes.toArray, UTF_8))("document")("runId")
        .str == "fixture-source-run"
    )
    assert(
      ujson
        .read(new String(newBody.bytes.toArray, UTF_8))("document")("runId")
        .str == "other-source-run"
    )
    val a = doc().copy(identityFields =
      scala.collection.immutable.ListMap("sourceDataset" -> "fixture", "topicId" -> "topic-fixture")
    )
    val b = a.copy(identityFields =
      scala.collection.immutable.ListMap("topicId" -> "topic-fixture", "sourceDataset" -> "fixture")
    )
    assert(EmbeddingManifests.textJson(a) == EmbeddingManifests.textJson(b))
    assert(
      EmbeddingManifests.item(a, model, config).textS3Uri == EmbeddingManifests
        .item(b, model, config)
        .textS3Uri
    )
  }
  test(
    "changed text with a new genuine document ID conflicts in its stable slot before embedding or payload writes"
  ) {
    val (objects, _, _, vectors, embed, runner) = fixture()
    val original = EmbeddingManifests.item(doc(), model, config)
    val changed = EmbeddingManifests.item(doc("different text"), model, config)
    assert(
      EmbeddingValidation.workItem(original).isEmpty && EmbeddingValidation
        .workItem(changed)
        .isEmpty
    )
    assert(original.document.documentId != changed.document.documentId)
    assert(original.textHash != changed.textHash && original.textS3Uri != changed.textS3Uri)
    assert(original.vectorKey == changed.vectorKey)
    assert(
      StorageResult.value(runner.run(EmbeddingManifest(Vector(original)), "first")).get.written == 1
    )
    val writes = objects.writeOrder.toVector
    val putCalls = vectors.putCalls
    val report = StorageResult.value(runner.run(EmbeddingManifest(Vector(changed)), "conflict")).get
    assert(
      report.vectorKeyTextConflict == 1 && report.rejected == 1 && report.written == 0 && report.embeddingCalls == 0
    )
    assert(report.rejections == Vector(VectorReject(original.vectorKey, "vectorKeyTextConflict")))
    assert(embed.calls == 1 && vectors.putCalls == putCalls)
    val newObjectWrites = objects.writeOrder.toVector.drop(writes.size)
    assert(newObjectWrites.size == 1 && newObjectWrites.head.startsWith("rag/rejected/versions/"))
    assert(objects.get(changed.textS3Uri.stripPrefix("s3://fixture-text/")) == Missing)
    val stored =
      StorageResult.value(vectors.get(original.indexName, Vector(original.vectorKey))).get
    assert(stored.size == 1 && stored.head.textHash == original.textHash)
    assert(stored.head.metadata("documentId") == original.document.documentId)
  }
  test("distinct stable chunk ordinals write distinct keys while unchanged replay skips both") {
    val (_, _, _, vectors, embed, runner) = fixture()
    val first = EmbeddingManifests.item(doc("first chunk", 0), model, config)
    val second = EmbeddingManifests.item(doc("second chunk", 1), model, config)
    assert(first.vectorKey != second.vectorKey)
    val manifest = EmbeddingManifest(Vector(first, second))
    val written = StorageResult.value(runner.run(manifest, "two-chunks")).get
    assert(written.written == 2 && written.rejected == 0 && written.embeddingCalls == 2)
    val putCalls = vectors.putCalls
    val skipped = StorageResult.value(runner.run(manifest, "two-chunks-replay")).get
    assert(skipped.unchanged == 2 && skipped.written == 0 && skipped.embeddingCalls == 0)
    assert(embed.calls == 2 && vectors.putCalls == putCalls)
  }
  test("retry counts and permanent failures are retained in RunLedger and rejected JSON") {
    val (objects, _, ledger, _, embed, runner) = fixture()
    embed.response = EmbeddingFailure("fixture-throttled", true, model, 3)
    val item = EmbeddingManifests.item(doc(), model, config)
    val report = StorageResult.value(runner.run(EmbeddingManifest(Vector(item)), "failed")).get
    assert(
      report.written == 0 && report.rejected == 1 && report.retried == 2 && report.embeddingCalls == 3
    )
    val record = StorageResult.value(ledger.getRun("failed")).get
    assert(
      record.failures
        .map(_.detail.get) == Vector("embedding-retry", "embedding-retry", "fixture-throttled")
    )
    assert(record.stages.head.retryCount == 3 && record.stages.head.state == "failed")
    val rejected = StorageResult
      .value(objects.get(report.rejectedReportUri.get.stripPrefix("s3://fixture-text/")))
      .get
    assert(
      ujson
        .read(new String(rejected.bytes.toArray, UTF_8))("rejected")(0)("reason")
        .str == "fixture-throttled"
    )
  }
  test("dimension mismatch rejects before vector writes and invalid manifest is bounded") {
    val (_, _, _, vectors, embed, runner) = fixture()
    embed.response = EmbeddingSuccess(Vector(1f), model, 1)
    val item = EmbeddingManifests.item(doc(), model, config)
    val report = StorageResult.value(runner.run(EmbeddingManifest(Vector(item)), "dimension")).get
    assert(report.rejected == 1 && report.written == 0)
    assert(StorageResult.value(vectors.get(item.indexName, Vector(item.vectorKey))).get.isEmpty)
    assert(EmbeddingManifests.parse("{}", config) == Rejected("malformed-embedding-manifest"))
    assert(
      EmbeddingManifests.parse(" " * 11, config.copy(maxManifestBytes = 10)) == Rejected(
        "manifest-byte-limit"
      )
    )
  }
  test("prepared checkpoint replays an ambiguous vector write without another embedding") {
    val objects = new InMemoryObjectStore; val registry = new InMemoryArtifactRegistry;
    val ledger = new InMemoryRunLedger; val embed = new Embed
    val underlying = new InMemoryVectorStore;
    underlying.ensureIndex("paper-abstract-v1", 2, "cosine")
    var fail = true
    val vectorPort = new VectorStore {
      def ensureIndex(n: String, d: Int, m: String) = underlying.ensureIndex(n, d, m)
      def get(n: String, k: Vector[String]) = underlying.get(n, k)
      def query(n: String, v: Vector[Float], k: Int, f: Map[String, String]) =
        underlying.query(n, v, k, f)
      def putBatch(n: String, ds: Vector[VectorDocument]): StorageResult[VectorBatchResult] = {
        val result = underlying.putBatch(n, ds)
        if (fail) { fail = false; Rejected("ambiguous-reply") }
        else result
      }
    }
    val runner = new EmbeddingManifestRunner(config, objects, vectorPort, registry, ledger, embed)
    val manifest = EmbeddingManifest(Vector(EmbeddingManifests.item(doc(), model, config)))
    assert(StorageResult.value(runner.run(manifest, "ambiguous")).get.rejected == 1)
    val replay = StorageResult.value(runner.run(manifest, "recover")).get
    assert(
      replay.unchanged == 1 && replay.rejected == 0 && replay.embeddingCalls == 0 && embed.calls == 1
    )
  }
  test("completion registry failure replays prepared vectors and summary JSON omits payloads") {
    val objects = new InMemoryObjectStore
    val underlyingRegistry = new InMemoryArtifactRegistry
    var failCompletion = true
    val registry = new ArtifactRegistry {
      def get(id: String, version: String) = underlyingRegistry.get(id, version)
      def latest(id: String) = underlyingRegistry.latest(id)
      def register(
          id: String,
          version: String,
          uri: String,
          hash: String
      ): StorageResult[ArtifactRecord] =
        if (version == "complete" && failCompletion) {
          failCompletion = false; Rejected("fixture-completion-failed")
        } else underlyingRegistry.register(id, version, uri, hash)
    }
    val ledger = new InMemoryRunLedger
    val vectors = new InMemoryVectorStore
    vectors.ensureIndex("paper-abstract-v1", 2, "cosine")
    val embed = new Embed
    val events = scala.collection.mutable.ArrayBuffer.empty[String]
    val runner = new EmbeddingManifestRunner(
      config,
      objects,
      vectors,
      registry,
      ledger,
      embed,
      logEvent = event => { events += event; () }
    )
    val manifest = EmbeddingManifest(Vector(EmbeddingManifests.item(doc(), model, config)))
    val first = StorageResult.value(runner.run(manifest, "marker-failed")).get
    assert(
      first.written == 1 && first.rejected == 1 && first.rejections.head.reason == "completion-registry-failed"
    )
    val replay = StorageResult.value(runner.run(manifest, "marker-replay")).get
    assert(
      replay.written == 0 && replay.unchanged == 1 && replay.rejected == 0 && replay.embeddingCalls == 0
    )
    assert(
      embed.calls == 1 && StorageResult
        .value(ledger.getRun("marker-replay"))
        .get
        .state == "complete"
    )
    val event = ujson.read(events.last)
    assert(event("event").str == "embedding_ingest" && event("runId").str == "marker-replay")
    assert(event("unchanged").num == 1 && event("perIndex").obj.get("paper-abstract-v1").isDefined)
    assert(
      !events.mkString.contains("distributed graph") && !events.mkString.contains("fixture-entity")
    )
  }
  test("duplicate items batch once and unchanged duplicates are counted") {
    val (_, _, _, _, embed, runner) = fixture()
    val item = EmbeddingManifests.item(doc(), model, config)
    val result =
      StorageResult.value(runner.run(EmbeddingManifest(Vector(item, item)), "duplicate")).get
    assert(result.written == 1 && result.unchanged == 1 && result.rejected == 0 && embed.calls == 1)
  }
  test("in-memory queue enforces capacity and visibility, rotates receipts on redelivery") {
    var now = 0L
    val queue = new InMemoryEmbeddingWorkQueue(1, 100, nowMillis = () => now)
    val item = EmbeddingManifests.item(doc(), model, config)
    assert(queue.enqueue(Vector(item)) == Written(1))
    assert(queue.enqueue(Vector(item)) == Rejected("queue-capacity"))
    val first = StorageResult.value(queue.receive(1)).get.head
    assert(queue.backlog == Found(1L) && queue.receive(1) == Found(Vector.empty))
    now = 100
    val second = StorageResult.value(queue.receive(1)).get.head
    assert(second.receipt != first.receipt)
    assert(queue.acknowledge(first.receipt) == Rejected("invalid-queue-receipt"))
    assert(queue.acknowledge(second.receipt) == Written(()) && queue.backlog == Found(0L))
  }
  private def sqs(handler: (Method, Array[AnyRef]) => AnyRef): SqsClient = Proxy
    .newProxyInstance(
      classOf[SqsClient].getClassLoader,
      Array(classOf[SqsClient]),
      new InvocationHandler {
        def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = handler(method, args)
      }
    )
    .asInstanceOf[SqsClient]
  test(
    "SQS adapter sends bounded serialized items and exact receive/delete/backlog request shapes"
  ) {
    val item = EmbeddingManifests.item(doc(), model, config)
    val client = sqs { (method, args) =>
      method.getName match {
        case "sendMessageBatch" =>
          val r = args(0).asInstanceOf[SendMessageBatchRequest]
          assert(r.queueUrl() == "https://fixture.invalid/queue" && r.entries().size() == 1)
          assert(upickle.default.read[EmbeddingWorkItem](r.entries().get(0).messageBody()) == item)
          SendMessageBatchResponse
            .builder()
            .successful(SendMessageBatchResultEntry.builder().id("0").messageId("fixture").build())
            .build()
        case "receiveMessage" =>
          val r = args(0).asInstanceOf[ReceiveMessageRequest]
          assert(
            r.maxNumberOfMessages() == 1 && r.visibilityTimeout() == 45 && r.waitTimeSeconds() == 2
          )
          ReceiveMessageResponse
            .builder()
            .messages(
              Message
                .builder()
                .body(upickle.default.write(item))
                .receiptHandle("fixture-receipt")
                .build()
            )
            .build()
        case "deleteMessage" =>
          assert(args(0).asInstanceOf[DeleteMessageRequest].receiptHandle() == "fixture-receipt")
          DeleteMessageResponse.builder().build()
        case "getQueueAttributes" =>
          GetQueueAttributesResponse
            .builder()
            .attributes(
              Map(
                QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES -> "2",
                QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_NOT_VISIBLE -> "3",
                QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_DELAYED -> "4"
              ).asJava
            )
            .build()
        case other => throw new IllegalStateException(other)
      }
    }
    val queue = new SqsEmbeddingWorkQueue(
      client,
      EmbeddingQueueConfig(
        "https://fixture.invalid/queue",
        visibilityTimeoutSeconds = 45,
        waitTimeSeconds = 2
      )
    )
    assert(queue.enqueue(Vector(item)) == Written(1))
    assert(queue.receive(1) == Found(Vector(EmbeddingQueueMessage("fixture-receipt", item))))
    assert(queue.acknowledge("fixture-receipt") == Written(()))
    assert(queue.backlog == Found(9L))
    assert(queue.receive(11) == Rejected("invalid-queue-receive-bound"))
  }
  test("SQS aggregate batch bytes reject before any SDK call") {
    var calls = 0
    val client = sqs { (_, _) =>
      calls += 1; throw new IllegalStateException("unexpected SDK")
    }
    val item = EmbeddingManifests.item(doc("x" * 600), model, config)
    val oneItemBytes = upickle.default.write(item).getBytes(UTF_8).length
    val queue = new SqsEmbeddingWorkQueue(
      client,
      EmbeddingQueueConfig("https://fixture.invalid/queue", maxBatchBytes = oneItemBytes)
    )
    assert(queue.enqueue(Vector(item, item)) == Rejected("queue-batch-byte-limit"))
    assert(calls == 0)
  }
  test("SQS partial enqueue and malformed receive fail visibly without deleting poison messages") {
    var calls = 0
    val client = sqs { (method, _) =>
      calls += 1;
      method.getName match {
        case "sendMessageBatch" =>
          SendMessageBatchResponse
            .builder()
            .failed(
              BatchResultErrorEntry
                .builder()
                .id("0")
                .code("fixture-permanent")
                .senderFault(true)
                .build()
            )
            .build()
        case "receiveMessage" =>
          ReceiveMessageResponse
            .builder()
            .messages(Message.builder().body("{}").receiptHandle("poison").build())
            .build()
        case other => throw new IllegalStateException(other)
      }
    }
    val queue =
      new SqsEmbeddingWorkQueue(client, EmbeddingQueueConfig("https://fixture.invalid/queue"))
    assert(
      queue.enqueue(Vector(EmbeddingManifests.item(doc(), model, config))) == Rejected(
        "queue-batch-partial-failure"
      )
    )
    assert(queue.receive(1) == Rejected("malformed-queue-message"))
    assert(calls == 2)
  }
}
