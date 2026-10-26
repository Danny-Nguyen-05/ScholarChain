package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import software.amazon.awssdk.services.sqs.SqsClient
import software.amazon.awssdk.services.sqs.model.*
import upickle.default.{read, write}

/** Independent bounded port tests. All identity, provenance and object names are synthetic. */
class IndependentEmbeddingStorageSpec extends AnyFunSuite {
  import StorageResult.*
  private val model = EmbeddingModel("independent-synthetic-model", "v1", 2)
  private val config = EmbeddingIngestConfig("synthetic-text", "graph", 2, batchSize = 2)
  private def document(letter: String, text: String) = EmbeddingDocument(
    StableIds
      .chunkOrProfileId("synthetic-" + letter, "template-v1", "researcher-profile", Some(0), text)
      .toOption
      .get,
    "researcher-profile",
    "synthetic-" + letter,
    "2020-2026",
    "source-run",
    "template-v1",
    text,
    Vector(SummarySourceRef("synthetic-source", "row-" + letter, "title")),
    "generated-summary",
    chunkPolicyVersion = "synthetic-policy-v1",
    chunkOrdinal = 0
  )
  private final class RecordingClient(
      val model: EmbeddingModel,
      answer: String => EmbeddingResult
  ) extends EmbeddingClient {
    val seen = mutable.Buffer.empty[String]
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
      seen += text
      answer(text)
    }
  }
  private final class Fixture(attempts: Int = 1) {
    val objects = new InMemoryObjectStore()
    val registry = new InMemoryArtifactRegistry()
    val ledger = new InMemoryRunLedger()
    val vectors = new InMemoryVectorStore()
    assert(StorageResult.successful(vectors.ensureIndex("researcher-profile-v1", 2, "cosine")))
    val client = new RecordingClient(model, _ => EmbeddingSuccess(Vector(1f, 0f), model, attempts))
    var tick = 0L
    val runner = new EmbeddingManifestRunner(
      config,
      objects,
      vectors,
      registry,
      ledger,
      client,
      () => { tick += 1000000000L; tick }
    )
  }
  private def value[A](result: StorageResult[A]): A =
    StorageResult.value(result).getOrElse(fail(result.toString))

  test(
    "first ingestion writes two documents; persistent replay skips embedding and preserves source text"
  ) {
    val f = new Fixture()
    val first = EmbeddingManifests.item(document("a", "hello"), model, config)
    val second = EmbeddingManifests.item(document("b", "synthetic graph context"), model, config)
    val manifest = EmbeddingManifest(Vector(first, second))
    val report = value(f.runner.run(manifest, "execution-one"))
    assert(
      (report.written, report.unchanged, report.rejected, report.embeddingCalls) == (2, 0, 0, 2)
    )
    assert(report.perIndex == Map("researcher-profile-v1" -> 2))
    assert(report.vectorsPerSecond == 2.0)
    assert(f.client.seen.toVector == Vector("hello", "synthetic graph context"))
    val replay = value(f.runner.run(manifest, "execution-two"))
    assert(
      (replay.written, replay.unchanged, replay.rejected, replay.embeddingCalls) == (0, 2, 0, 0)
    )
    assert(f.client.seen.size == 2)
    assert(
      value(
        f.vectors.get("researcher-profile-v1", Vector(first.vectorKey, second.vectorKey))
      ).size == 2
    )
    val key = first.textS3Uri.stripPrefix("s3://synthetic-text/")
    val source = ujson.read(new String(value(f.objects.get(key)).bytes.toArray, UTF_8))
    assert(source("document")("text").str == "hello")
    assert(
      source("textHash").str == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )
    assert(value(f.ledger.getRun("execution-two")).state == "complete")
  }

  test("a bound vector key rejects changed text before embedding and records the conflict") {
    val f = new Fixture()
    val original = document("a", "hello")
    val first = EmbeddingManifests.item(original, model, config)
    value(f.runner.run(EmbeddingManifest(Vector(first)), "conflict-first"))
    val changedDocument = document("a", "changed text")
    assert(changedDocument.documentId != original.documentId)
    val changed = EmbeddingManifests.item(changedDocument, model, config)
    assert(changed.vectorKey == first.vectorKey)
    val report = value(f.runner.run(EmbeddingManifest(Vector(changed)), "conflict-second"))
    assert(
      (
        report.written,
        report.unchanged,
        report.vectorKeyTextConflict,
        report.rejected,
        report.embeddingCalls
      ) == (0, 0, 1, 1, 0)
    )
    assert(f.client.seen.toVector == Vector("hello"))
    assert(report.rejections == Vector(VectorReject(first.vectorKey, "vectorKeyTextConflict")))
    val journal = value(f.ledger.getRun("conflict-second"))
    assert(journal.state != "complete")
    assert(journal.failures.exists(_.detail.contains("vectorKeyTextConflict")))
    val reportKey = report.rejectedReportUri.get.stripPrefix("s3://synthetic-text/")
    val rejection = ujson.read(new String(value(f.objects.get(reportKey)).bytes.toArray, UTF_8))
    assert(rejection("rejected")(0)("reason").str == "vectorKeyTextConflict")
  }

  test("observed embedding attempts create retry counters and ledger failure history") {
    val f = new Fixture(attempts = 3)
    val item = EmbeddingManifests.item(document("a", "hello"), model, config)
    val report = value(f.runner.run(EmbeddingManifest(Vector(item)), "retry-execution"))
    assert((report.written, report.retried, report.embeddingCalls) == (1, 2, 3))
    val journal = value(f.ledger.getRun("retry-execution"))
    assert(journal.state == "complete")
    assert(
      journal.failures.map(_.detail) == Vector(Some("embedding-retry"), Some("embedding-retry"))
    )
    assert(journal.failures.map(_.retryCount) == Vector(1, 2))
  }

  test("index/client dimension mismatch refuses ingestion before an embedding invocation") {
    val f = new Fixture()
    val wrong = model.copy(dimension = 3)
    val client = new RecordingClient(wrong, _ => EmbeddingSuccess(Vector(1f, 0f, 0f), wrong, 1))
    val runner =
      new EmbeddingManifestRunner(config, f.objects, f.vectors, f.registry, f.ledger, client)
    val item = EmbeddingManifests.item(document("a", "hello"), model, config)
    assert(
      runner.run(EmbeddingManifest(Vector(item)), "wrong-dimension") == Rejected(
        "embedding-dimension-mismatch"
      )
    )
    assert(client.seen.isEmpty)
    assert(value(f.vectors.get("researcher-profile-v1", Vector(item.vectorKey))).isEmpty)
  }

  test("fake queue redelivers after visibility expiry and refuses a stale receipt") {
    var now = 100L
    val queue = new InMemoryEmbeddingWorkQueue(visibilityTimeoutMillis = 10, nowMillis = () => now)
    val item = EmbeddingManifests.item(document("a", "hello"), model, config)
    assert(queue.enqueue(Vector(item)) == Written(1))
    val delivery = value(queue.receive(1)).head
    assert(value(queue.receive(1)).isEmpty)
    assert(queue.backlog == Found(1L))
    now = 110L
    val repeated = value(queue.receive(1)).head
    assert(repeated.item == item && repeated.receipt != delivery.receipt)
    assert(queue.acknowledge(delivery.receipt) == Rejected("invalid-queue-receipt"))
    assert(queue.acknowledge(repeated.receipt) == Written(()))
    assert(queue.backlog == Found(0L))
  }

  test("SQS adapter sends exact bounded configured requests through an injected stub") {
    val item = EmbeddingManifests.item(document("a", "hello"), model, config)
    val url = "https://sqs.us-east-2.amazonaws.com/000000000000/synthetic-offline"
    val seen = mutable.Buffer.empty[String]
    val client = IndependentStorage7BSupport.stub(classOf[SqsClient]) {
      case ("sendMessageBatch", Vector(r: SendMessageBatchRequest)) =>
        seen += "send"
        assert(r.queueUrl() == url && r.entries().size() == 1)
        assert(read[EmbeddingWorkItem](r.entries().get(0).messageBody()) == item)
        SendMessageBatchResponse
          .builder()
          .successful(
            SendMessageBatchResultEntry.builder().id("0").messageId("synthetic-id").build()
          )
          .build()
      case ("receiveMessage", Vector(r: ReceiveMessageRequest)) =>
        seen += "receive"
        assert(r.queueUrl() == url && r.maxNumberOfMessages() == 1)
        assert(r.visibilityTimeout() == 15 && r.waitTimeSeconds() == 0)
        ReceiveMessageResponse
          .builder()
          .messages(Message.builder().receiptHandle("synthetic-receipt").body(write(item)).build())
          .build()
      case ("deleteMessage", Vector(r: DeleteMessageRequest)) =>
        seen += "ack"
        assert(r.queueUrl() == url && r.receiptHandle() == "synthetic-receipt")
        DeleteMessageResponse.builder().build()
    }
    val queue = new SqsEmbeddingWorkQueue(
      client,
      EmbeddingQueueConfig(url, visibilityTimeoutSeconds = 15, retry = RetryConfig(1, 0, 0))
    )
    assert(queue.enqueue(Vector(item)) == Written(1))
    assert(value(queue.receive(1)) == Vector(EmbeddingQueueMessage("synthetic-receipt", item)))
    assert(queue.acknowledge("synthetic-receipt") == Written(()))
    assert(queue.receive(11) == Rejected("invalid-queue-receive-bound"))
    assert(seen.toVector == Vector("send", "receive", "ack"))
  }
}
