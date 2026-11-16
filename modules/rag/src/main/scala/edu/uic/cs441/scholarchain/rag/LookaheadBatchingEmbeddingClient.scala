package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import scala.collection.mutable

/** Point-in-time counters of a [[LookaheadBatchingEmbeddingClient]]. `underlyingCalls` is the
  * number of `embed` calls made on the wrapped client (each one is split into provider requests by
  * that client: at most 1,000 texts and 1,000,000 estimated tokens per Voyage request). `textsSent`
  * is the number of texts in those calls; `servedFromBatch` is the number of single-text requests
  * answered from an earlier call; `unusedPrefetched` is the number of texts embedded ahead that no
  * caller has asked for (yet). Numbers only; no text is held here.
  */
final case class EmbeddingBatchStats(
    underlyingCalls: Long,
    textsSent: Long,
    servedFromBatch: Long,
    passThrough: Long,
    unusedPrefetched: Long,
    batchSize: Int
)

/** Ingest-side embedding batcher (session-2 plan P26 (b), decision Q8: batched ingest preferred).
  *
  * The storage `EmbeddingManifestRunner` asks for one text per item, in manifest order, and only
  * for items that still need a vector (not complete and not prepared). This wrapper knows the
  * manifest's texts in that same order. When asked for a text it has not embedded yet, it sends
  * that text together with up to `batchSize - 1` of the next not-yet-sent manifest texts in one
  * call to the wrapped client and keeps the other results for the requests that follow. It is a
  * plain [[EmbeddingClient]] decorator; the runner, its checkpoints, the retry and backoff of the
  * wrapped client and the query-path cache (P40) are unchanged.
  *
  * Bounds and accounting:
  *   - every distinct manifest text is sent to the wrapped client at most once per wrapper (except
  *     after a call that throws or returns the wrong count, below), so the tokens sent stay within
  *     one pass over the manifest texts (the preflight token bound covers every item times
  *     `maxEmbeddingAttempts`), and the wrapped client's token cap still refuses any excess;
  *   - a text embedded ahead that the runner then skips (already complete or prepared from an
  *     earlier run) is sent but unused; [[stats]] reports it;
  *   - each result is returned exactly as the wrapped client produced it, failure or success, with
  *     the attempts of the request that carried it. A failed request therefore fails every text in
  *     it (as the Voyage client already does for its own multi-text requests); the runner records
  *     those items as rejected and a fresh run re-embeds them;
  *   - a result is dropped once it has been returned, so memory holds at most one batch ahead;
  *   - a text that is not in the manifest, or asked for again after its result was returned, goes
  *     to the wrapped client alone (`passThrough`);
  *   - if the wrapped client returns the wrong number of results or throws, the requested text gets
  *     a typed failure (`embedding-batch-result-count`, `embedding-client-exception`), nothing from
  *     that call is kept, and its other texts can be sent again in a later batch.
  *
  * The identity (`model`, `provider`) is the wrapped client's, so the vector consistency check
  * gives the same answer with or without this wrapper.
  *
  * Thread safety: the storage runner calls from up to `ingestConcurrency` worker threads, in
  * roughly (not exactly) manifest order. Every `embed` call, including the wrapped client's
  * request, runs under one lock, so the sent/ready bookkeeping is consistent and each text is still
  * sent at most once: a worker that asks for a text while the batch carrying it is in flight waits
  * for that batch and is then served from it. Embedding requests are therefore never concurrent
  * with each other; with batching that is one request per `batchSize` items, and the other ingest
  * work of the workers (S3, DynamoDB, S3 Vectors) still overlaps. A text asked for before the
  * lookahead position starts its own batch from its own manifest position.
  */
final class LookaheadBatchingEmbeddingClient(
    underlying: EmbeddingClient,
    manifestTexts: Seq[String],
    val batchSize: Int
) extends ProviderEmbeddingClient {
  require(underlying != null, "invalid-embedding-batch-underlying")
  require(batchSize >= 1, "invalid-embedding-batch-size")

  val model: EmbeddingModel = underlying.model
  val provider: EmbeddingProvider = underlying match {
    case p: ProviderEmbeddingClient => p.provider
    case other                      => EmbeddingProviders.infer(other.model)
  }

  private val order: Vector[String] = manifestTexts.toVector
  // Manifest positions of each distinct text, first occurrence first.
  private val positions: Map[String, Vector[Int]] =
    order.zipWithIndex.groupMap(_._1)(_._2)
  private val sent = mutable.HashSet.empty[String]
  private val ready = mutable.HashMap.empty[String, EmbeddingResult]
  private var underlyingCalls = 0L
  private var textsSent = 0L
  private var servedFromBatch = 0L
  private var passThrough = 0L
  private var cursor = 0

  def stats: EmbeddingBatchStats = synchronized {
    EmbeddingBatchStats(
      underlyingCalls,
      textsSent,
      servedFromBatch,
      passThrough,
      ready.size.toLong,
      batchSize
    )
  }

  private def failure(code: String): EmbeddingFailure = EmbeddingFailure(code, false, model, 0)

  /** One call to the wrapped client; Left is a typed code for every text of the call. */
  private def call(texts: Vector[String]): Either[String, Vector[EmbeddingResult]] = {
    underlyingCalls += 1
    textsSent += texts.size
    try {
      val results = underlying.embed(texts)
      if (results == null || results.size != texts.size || results.exists(_ == null))
        Left("embedding-batch-result-count")
      else Right(results.toVector)
    } catch { case scala.util.control.NonFatal(_) => Left("embedding-client-exception") }
  }

  private def one(text: String): EmbeddingResult =
    if (text == null) {
      passThrough += 1
      call(Vector(text)).fold(failure, _.head)
    } else
      ready.remove(text) match {
        case Some(result) =>
          servedFromBatch += 1
          result
        case None if sent.contains(text) || !positions.contains(text) =>
          passThrough += 1
          call(Vector(text)).fold(failure, _.head)
        case None =>
          // The runner moves forward through the manifest; look ahead from its position.
          val start = positions(text).find(_ >= cursor).getOrElse(positions(text).head)
          cursor = math.max(cursor, start)
          val batch = mutable.LinkedHashSet(text)
          var at = start + 1
          while (batch.size < batchSize && at < order.size) {
            val next = order(at)
            if (next != null && !sent.contains(next)) batch += next
            at += 1
          }
          val texts = batch.toVector
          texts.foreach(sent += _)
          call(texts) match {
            case Left(code) =>
              // Malformed or thrown call: the other texts may be asked for again in a later batch.
              texts.tail.foreach(sent -= _)
              failure(code)
            case Right(results) =>
              texts.zip(results).tail.foreach((t, r) => ready(t) = r)
              results.head
          }
      }

  def embed(texts: Seq[String]): Seq[EmbeddingResult] = synchronized {
    texts.toVector.map(one)
  }

  override def toString: String =
    s"LookaheadBatchingEmbeddingClient(${model.modelId}, batchSize=$batchSize)"
}
