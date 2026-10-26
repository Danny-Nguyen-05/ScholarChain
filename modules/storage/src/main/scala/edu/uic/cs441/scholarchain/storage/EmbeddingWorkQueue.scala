package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.time.Duration
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal
import software.amazon.awssdk.services.sqs.SqsClient
import software.amazon.awssdk.services.sqs.model.*
import software.amazon.awssdk.awscore.AwsRequestOverrideConfiguration
import upickle.default.{read, write}
import StorageResult.*

final case class EmbeddingQueueMessage(receipt: String, item: EmbeddingWorkItem)
trait EmbeddingWorkQueue {
  def enqueue(items: Vector[EmbeddingWorkItem]): StorageResult[Int]
  def receive(maxItems: Int): StorageResult[Vector[EmbeddingQueueMessage]]
  def acknowledge(receipt: String): StorageResult[Unit]
  def backlog: StorageResult[Long]
}
final case class EmbeddingQueueConfig(
    queueUrl: String,
    maxMessageBytes: Int = 256 * 1024,
    maxBatchBytes: Int = 1024 * 1024,
    visibilityTimeoutSeconds: Int = 30,
    waitTimeSeconds: Int = 0,
    requestTimeoutMillis: Long = 30000,
    retry: RetryConfig = RetryConfig()
) {
  require(queueUrl.nonEmpty && maxMessageBytes > 0 && maxMessageBytes <= 1024 * 1024)
  require(maxBatchBytes > 0 && maxBatchBytes <= 1024 * 1024)
  require(visibilityTimeoutSeconds >= 1 && visibilityTimeoutSeconds <= 43200)
  require(
    waitTimeSeconds >= 0 && waitTimeSeconds <= 20 && requestTimeoutMillis > waitTimeSeconds * 1000L
  )
}

/** Bounded at-least-once local queue. Receipt handles rotate on redelivery after visibility expiry.
  */
final class InMemoryEmbeddingWorkQueue(
    capacity: Int = 1000,
    visibilityTimeoutMillis: Long = 30000,
    maxMessageBytes: Int = 256 * 1024,
    nowMillis: () => Long = () => System.currentTimeMillis()
) extends EmbeddingWorkQueue {
  require(capacity > 0 && visibilityTimeoutMillis > 0 && maxMessageBytes > 0)
  private case class Entry(item: EmbeddingWorkItem, var visibleAt: Long, var receipt: String)
  private val entries = mutable.ArrayBuffer.empty[Entry]
  private var sequence = 0L
  def enqueue(items: Vector[EmbeddingWorkItem]): StorageResult[Int] = synchronized {
    if (
      items.size > 10 || items.exists(i =>
        EmbeddingValidation
          .workItem(i)
          .nonEmpty || write(i).getBytes(UTF_8).length > maxMessageBytes
      )
    ) Rejected("invalid-queue-items")
    else if (entries.size + items.size > capacity) Rejected("queue-capacity")
    else { items.foreach(i => entries += Entry(i, nowMillis(), "")); Written(items.size) }
  }
  def receive(maxItems: Int): StorageResult[Vector[EmbeddingQueueMessage]] = synchronized {
    if (maxItems < 1 || maxItems > 10) Rejected("invalid-queue-receive-bound")
    else {
      val now = nowMillis()
      val messages = entries
        .filter(_.visibleAt <= now)
        .take(maxItems)
        .map { e =>
          sequence += 1; e.receipt = "receipt-" + sequence;
          e.visibleAt = now + visibilityTimeoutMillis
          EmbeddingQueueMessage(e.receipt, e.item)
        }
        .toVector
      Found(messages)
    }
  }
  def acknowledge(receipt: String): StorageResult[Unit] = synchronized {
    val index = entries.indexWhere(e => e.receipt == receipt && e.visibleAt > nowMillis())
    if (receipt.isEmpty || index < 0) Rejected("invalid-queue-receipt")
    else { entries.remove(index); Written(()) }
  }
  def backlog: StorageResult[Long] = synchronized { Found(entries.size.toLong) }
}

/** Client injection only: no credential discovery, queue provisioning or background worker. */
final class SqsEmbeddingWorkQueue(client: SqsClient, config: EmbeddingQueueConfig)
    extends EmbeddingWorkQueue {
  private val retry = new StorageRetry(config.retry)
  private def timeout = AwsRequestOverrideConfiguration
    .builder()
    .apiCallTimeout(Duration.ofMillis(config.requestTimeoutMillis))
    .build()
  def enqueue(items: Vector[EmbeddingWorkItem]): StorageResult[Int] = {
    if (
      items.size > 10 || items.exists(i =>
        EmbeddingValidation
          .workItem(i)
          .nonEmpty || write(i).getBytes(UTF_8).length > config.maxMessageBytes
      )
    ) return Rejected("invalid-queue-items")
    if (items.iterator.map(i => write(i).getBytes(UTF_8).length.toLong).sum > config.maxBatchBytes)
      return Rejected("queue-batch-byte-limit")
    if (items.isEmpty) return Unchanged(0)
    retry {
      val entries = items.zipWithIndex.map { (item, index) =>
        SendMessageBatchRequestEntry.builder().id(index.toString).messageBody(write(item)).build()
      }
      val response = client.sendMessageBatch(
        SendMessageBatchRequest
          .builder()
          .queueUrl(config.queueUrl)
          .entries(entries.asJava)
          .overrideConfiguration(timeout)
          .build()
      )
      val expected = entries.map(_.id()).toSet
      if (
        response
          .failed()
          .isEmpty && response.successful().asScala.map(_.id()).toSet == expected && response
          .successful()
          .size() == items.size
      ) Written(items.size)
      else Rejected("queue-batch-partial-failure") // Caller may replay; ingestion is idempotent.
    }
  }
  def receive(maxItems: Int): StorageResult[Vector[EmbeddingQueueMessage]] = {
    if (maxItems < 1 || maxItems > 10) return Rejected("invalid-queue-receive-bound")
    retry {
      val response = client.receiveMessage(
        ReceiveMessageRequest
          .builder()
          .queueUrl(config.queueUrl)
          .maxNumberOfMessages(maxItems)
          .visibilityTimeout(config.visibilityTimeoutSeconds)
          .waitTimeSeconds(config.waitTimeSeconds)
          .overrideConfiguration(timeout)
          .build()
      )
      if (response.messages().size() > maxItems) Rejected("queue-receive-bound-exceeded")
      else
        try {
          val messages = response.messages().asScala.toVector.map { m =>
            if (
              m.body() == null || m.receiptHandle() == null || m
                .receiptHandle()
                .isEmpty || m.body().getBytes(UTF_8).length > config.maxMessageBytes
            ) throw new IllegalArgumentException("invalid")
            val item = read[EmbeddingWorkItem](m.body())
            if (EmbeddingValidation.workItem(item).nonEmpty)
              throw new IllegalArgumentException("invalid")
            EmbeddingQueueMessage(m.receiptHandle(), item)
          }
          Found(messages)
        } catch { case NonFatal(_) => Rejected("malformed-queue-message") }
    }
  }
  def acknowledge(receipt: String): StorageResult[Unit] = {
    if (receipt.isEmpty) return Rejected("invalid-queue-receipt")
    retry {
      client.deleteMessage(
        DeleteMessageRequest
          .builder()
          .queueUrl(config.queueUrl)
          .receiptHandle(receipt)
          .overrideConfiguration(timeout)
          .build()
      ); Written(())
    }
  }
  def backlog: StorageResult[Long] = retry {
    val response = client.getQueueAttributes(
      GetQueueAttributesRequest
        .builder()
        .queueUrl(config.queueUrl)
        .attributeNames(
          QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES,
          QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_NOT_VISIBLE,
          QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_DELAYED
        )
        .overrideConfiguration(timeout)
        .build()
    )
    try {
      val attributes = response.attributes()
      val counts = Vector(
        QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES,
        QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_NOT_VISIBLE,
        QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES_DELAYED
      ).map(k => Option(attributes.get(k)).filter(_.matches("[0-9]+")).get.toLong)
      Found(counts.foldLeft(0L)(Math.addExact))
    } catch { case NonFatal(_) => Rejected("invalid-queue-backlog") }
  }
}
