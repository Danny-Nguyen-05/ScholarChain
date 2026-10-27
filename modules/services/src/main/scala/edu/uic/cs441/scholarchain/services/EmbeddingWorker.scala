package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import scala.util.control.NonFatal

trait EmbeddingProcessor {
  def process(item: EmbeddingWorkItem): Either[ApiError, Unit]
}
final class ManifestEmbeddingProcessor(runner: EmbeddingManifestRunner) extends EmbeddingProcessor {
  def process(item: EmbeddingWorkItem): Either[ApiError, Unit] = {
    val run = "run:" + java.util.UUID.randomUUID().toString
    PortResult.read(runner.run(EmbeddingManifest(Vector(item)), run)).flatMap { report =>
      if (report.rejected == 0 && report.vectorKeyTextConflict == 0) Right(())
      else Left(ApiError.downstream)
    }
  }
}
final case class WorkerConfig(maxAttempts: Int = 3, batchSize: Int = 1, pollMs: Long = 1000) {
  require(maxAttempts > 0 && batchSize > 0 && batchSize <= 10 && pollMs > 0)
}
final case class WorkerPoll(
    received: Int,
    completed: Int,
    duplicates: Int,
    deadLettered: Int,
    failed: Int
)

/** Durable per-payload reservation fences concurrent consumers. Receipt acknowledgement only
  * follows recorded success or successful DLQ publication. No queue/provider is constructed here.
  */
final class EmbeddingWorker(
    queue: EmbeddingWorkQueue,
    dlq: EmbeddingWorkQueue,
    sessions: QuerySessionStore,
    processor: EmbeddingProcessor,
    val config: WorkerConfig = WorkerConfig()
) extends AutoCloseable {
  @volatile private var active = true
  def pollOnce(): Either[ApiError, WorkerPoll] =
    PortResult.read(queue.receive(config.batchSize)).map { messages =>
      var done = 0; var duplicate = 0; var dead = 0; var failed = 0
      messages.foreach { message =>
        val hash = Auth.sha256(upickle.default.write(message.item))
        val id = "EMBEDDING_WORKER#" + hash
        val created = sessions.createIfAbsent(id, "embedding-worker:" + hash)
        val row = StorageResult.value(created).orElse(StorageResult.value(sessions.get(id)))
        row match {
          case None => failed += 1
          case Some(s) if s.state == "COMPLETE" || s.state == "DEAD" =>
            if (StorageResult.successful(queue.acknowledge(message.receipt))) duplicate += 1
            else failed += 1
          case Some(s) if s.state == "created" || s.state == "RETRY" =>
            val attempts = if (s.payload == "{}") 0 else ujson.read(s.payload)("attempts").num.toInt
            val claimed = s.copy(
              state = "PROCESSING",
              revision = s.revision + 1,
              payload = ujson.Obj("attempts" -> (attempts + 1)).render()
            )
            if (!StorageResult.successful(sessions.update(claimed, s.revision))) failed += 1
            else {
              val result =
                try processor.process(message.item)
                catch { case NonFatal(_) => Left(ApiError.downstream) }
              result match {
                case Right(_) =>
                  val saved = sessions.update(
                    claimed.copy(state = "COMPLETE", revision = claimed.revision + 1),
                    claimed.revision
                  )
                  if (
                    StorageResult.successful(saved) && StorageResult
                      .successful(queue.acknowledge(message.receipt))
                  ) done += 1
                  else failed += 1
                case Left(_) if attempts + 1 >= config.maxAttempts =>
                  val published = dlq.enqueue(Vector(message.item))
                  if (StorageResult.successful(published)) {
                    val saved = sessions.update(
                      claimed.copy(state = "DEAD", revision = claimed.revision + 1),
                      claimed.revision
                    )
                    if (
                      StorageResult.successful(saved) && StorageResult
                        .successful(queue.acknowledge(message.receipt))
                    ) dead += 1
                    else failed += 1
                  } else {
                    sessions.update(
                      claimed.copy(state = "RETRY", revision = claimed.revision + 1),
                      claimed.revision
                    )
                    failed += 1
                  }
                case Left(_) =>
                  sessions.update(
                    claimed.copy(state = "RETRY", revision = claimed.revision + 1),
                    claimed.revision
                  )
                  failed += 1
              }
            }
          case _ =>
            failed += 1 // Another live worker owns PROCESSING; leave the receipt unacknowledged.
        }
      }
      WorkerPoll(messages.size, done, duplicate, dead, failed)
    }
  def run(): Unit = while (active && !Thread.currentThread().isInterrupted) {
    pollOnce()
    try Thread.sleep(config.pollMs)
    catch { case _: InterruptedException => Thread.currentThread().interrupt() }
  }
  def close(): Unit = { active = false }
}
