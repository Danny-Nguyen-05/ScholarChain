package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong}
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable.ArrayBuffer

class IndependentServices10BWorkerSpec extends AnyFunSuite {
  private def item: EmbeddingWorkItem = {
    val corpus = new IndependentRuntime9BSemanticFixture.Corpus
    EmbeddingManifests.item(corpus.document, corpus.embeddings.model, corpus.ingest)
  }
  private def poll(worker: EmbeddingWorker): WorkerPoll =
    worker.pollOnce().fold(e => fail(e.code), identity)
  private def processor(f: EmbeddingWorkItem => Either[ApiError, Unit]): EmbeddingProcessor =
    new EmbeddingProcessor { def process(i: EmbeddingWorkItem) = f(i) }

  test(
    "duplicate queue payloads execute once across worker instances and acknowledge both receipts"
  ) {
    val queue = new InMemoryEmbeddingWorkQueue
    val dlq = new InMemoryEmbeddingWorkQueue
    val sessions = new InMemoryQuerySessionStore
    val calls = new AtomicInteger
    val work = item
    assert(StorageResult.successful(queue.enqueue(Vector(work, work))))
    val process = processor { _ =>
      calls.incrementAndGet(); Right(())
    }
    val first = new EmbeddingWorker(queue, dlq, sessions, process)
    val second = new EmbeddingWorker(queue, dlq, sessions, process)
    try {
      assert(poll(first).completed == 1)
      assert(poll(second).duplicates == 1)
      assert(calls.get == 1)
      assert(StorageResult.value(queue.backlog).contains(0L))
      assert(StorageResult.value(dlq.backlog).contains(0L))
    } finally { first.close(); second.close() }
  }

  test("three failed deliveries publish the exact poison payload to DLQ before acknowledgement") {
    val now = new AtomicLong(1000)
    val backing =
      new InMemoryEmbeddingWorkQueue(visibilityTimeoutMillis = 20, nowMillis = () => now.get)
    val events = ArrayBuffer.empty[String]
    val calls = new AtomicInteger
    val work = item
    var deadItems = Vector.empty[EmbeddingWorkItem]
    val queue = new EmbeddingWorkQueue {
      def enqueue(items: Vector[EmbeddingWorkItem]) = backing.enqueue(items)
      def receive(max: Int) = backing.receive(max)
      def acknowledge(receipt: String) = { events += "ack"; backing.acknowledge(receipt) }
      def backlog = backing.backlog
    }
    val dlq = new EmbeddingWorkQueue {
      def enqueue(items: Vector[EmbeddingWorkItem]) = {
        events += "dead-letter"; deadItems ++= items; StorageResult.Written(items.size)
      }
      def receive(max: Int) = StorageResult.Found(Vector.empty[EmbeddingQueueMessage])
      def acknowledge(receipt: String) = StorageResult.Rejected("unused")
      def backlog = StorageResult.Found(deadItems.size.toLong)
    }
    assert(StorageResult.successful(queue.enqueue(Vector(work))))
    val sessions = new InMemoryQuerySessionStore
    val process = processor { _ =>
      calls.incrementAndGet(); Left(ApiError.downstream)
    }
    for (attempt <- 1 to 3) {
      // A new worker for every delivery proves that retry counts are persisted, not process-local.
      val worker = new EmbeddingWorker(queue, dlq, sessions, process, WorkerConfig(maxAttempts = 3))
      try {
        val result = poll(worker)
        if (attempt < 3) {
          assert(result.failed == 1 && result.deadLettered == 0)
          assert(events.isEmpty)
          assert(StorageResult.value(queue.backlog).contains(1L))
        } else assert(result.deadLettered == 1)
      } finally worker.close()
      now.addAndGet(21)
    }
    assert(calls.get == 3)
    assert(deadItems == Vector(work))
    assert(events.toVector == Vector("dead-letter", "ack"))
    assert(StorageResult.value(queue.backlog).contains(0L))
  }

  test("failed DLQ publication leaves the source message unacknowledged for redelivery") {
    val now = new AtomicLong(1000)
    val queue =
      new InMemoryEmbeddingWorkQueue(visibilityTimeoutMillis = 20, nowMillis = () => now.get)
    val dlqCalls = new AtomicInteger
    val dlq = new EmbeddingWorkQueue {
      def enqueue(items: Vector[EmbeddingWorkItem]): StorageResult[Int] = {
        dlqCalls.incrementAndGet(); StorageResult.Rejected("synthetic-dlq-down")
      }
      def receive(max: Int) = StorageResult.Found(Vector.empty[EmbeddingQueueMessage])
      def acknowledge(receipt: String) = StorageResult.Rejected("unused")
      def backlog = StorageResult.Found(0L)
    }
    val work = item
    assert(StorageResult.successful(queue.enqueue(Vector(work))))
    val worker = new EmbeddingWorker(
      queue,
      dlq,
      new InMemoryQuerySessionStore,
      processor(_ => Left(ApiError.downstream)),
      WorkerConfig(maxAttempts = 1)
    )
    try {
      assert(poll(worker).failed == 1)
      assert(dlqCalls.get == 1)
      assert(StorageResult.value(queue.backlog).contains(1L))
      now.addAndGet(21)
      val redelivered = StorageResult.value(queue.receive(1)).get
      assert(redelivered.size == 1 && redelivered.head.item == work)
    } finally worker.close()
  }
}
