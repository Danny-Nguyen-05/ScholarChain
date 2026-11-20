package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.util.{LinkedHashMap => JLinkedHashMap, Map => JMap}
import scala.collection.mutable

/** Point-in-time counters of a [[CachingEmbeddingClient]]. `hits`, `misses` and `evictions` never
  * decrease. `misses` is exactly the number of texts sent to the underlying client; `hits` is the
  * number of input texts answered without their own underlying request (a cache entry, or an
  * earlier identical text in the same successful call). `size` is the current entry count, at most
  * `capacity`. The values are numbers only; no text or hash is held here.
  */
final case class EmbeddingCacheStats(
    hits: Long,
    misses: Long,
    evictions: Long,
    size: Int,
    capacity: Int
)

object CachingEmbeddingClient {

  /** Default bound (entries) when no size is configured. */
  val DefaultMaxEntries: Int = 1024

  /** Closed code thrown when the underlying result count differs from the request count. */
  val ResultCountMismatch: String = "embedding-cache-result-count-mismatch"

  /** Closed code thrown when the underlying result holds a null element. */
  val NullResult: String = "embedding-cache-null-result"

  /** Keys are (provider and model identity, SHA-256 hex of the exact UTF-8 text). The clear text is
    * never stored.
    */
  private final case class Key(identity: String, textSha256: String)
}

/** Bounded in-memory LRU cache of query embeddings (session-2 plan P40, finding F25). It wraps one
  * embedding client and reports that client's identity unchanged: the same `model` (id, version,
  * dimension) and the same `provider` (the underlying's own provider, or the provider inferred from
  * its model id exactly as `VectorConsistency.checkClient` infers it), so the consistency check
  * gives the same answer with or without the cache.
  *
  * Keying: the underlying provider and model tag, plus the SHA-256 of the exact text (no trimming
  * or case folding). The `EmbeddingClient` interface does not distinguish query and document input:
  * the input type is fixed when the underlying client is built, and one cache wraps exactly one
  * underlying client, so the cache never mixes input types. Wrap the query client only.
  *
  * Bounds: at most `maxEntries` entries (must be positive), least recently used evicted first; no
  * TTL. Each call sends the underlying client, at most once, only the distinct texts that are not
  * cached, in first-occurrence order; a call with no miss makes no underlying call.
  *
  * Caching: only `EmbeddingSuccess` values with this model, its dimension and finite values are
  * cached; `EmbeddingFailure` values are returned and not cached. If the underlying client throws,
  * the exception propagates unchanged and nothing is cached. If it returns a result of the wrong
  * length or with a null element, nothing is cached and an `IllegalStateException` with a closed
  * code is thrown. If any success in a response is malformed (other model, wrong dimension, non
  * finite value), nothing from that response is cached and the response is returned unchanged.
  * Cached results are returned as stored, so `attempts` is that of the original provider call.
  *
  * Concurrency: all map and counter access is under one lock; the underlying call runs outside it.
  * Concurrent misses for the same text are not coalesced: two threads may both call the underlying
  * client for it (both count as misses) and the later insert replaces the earlier one. Null texts
  * are passed through to the underlying client and never cached. Nothing here logs text, and
  * `toString` shows identity and counters only.
  */
final class CachingEmbeddingClient(
    underlying: EmbeddingClient,
    maxEntries: Int = CachingEmbeddingClient.DefaultMaxEntries
) extends ProviderEmbeddingClient {
  import CachingEmbeddingClient.*

  require(underlying != null, "invalid-embedding-cache-underlying")
  require(maxEntries > 0, "invalid-embedding-cache-size")

  val model: EmbeddingModel = underlying.model
  val provider: EmbeddingProvider = underlying match {
    case p: ProviderEmbeddingClient => p.provider
    case other                      => EmbeddingProviders.infer(other.model)
  }
  val capacity: Int = maxEntries

  private val identity: String = s"${provider.wire}|${model.tag}"
  private val lock = new Object
  private var hits = 0L
  private var misses = 0L
  private var evictions = 0L
  private val entries = new JLinkedHashMap[Key, EmbeddingSuccess](16, 0.75f, true) {
    override def removeEldestEntry(eldest: JMap.Entry[Key, EmbeddingSuccess]): Boolean =
      if (size() > maxEntries) { evictions += 1; true }
      else false
  }

  def stats: EmbeddingCacheStats = lock.synchronized {
    EmbeddingCacheStats(hits, misses, evictions, entries.size(), maxEntries)
  }

  /** Rendered keys, least recently used first, for tests that check no clear text is held. */
  private[rag] def keyFingerprints: Vector[String] = lock.synchronized {
    val out = Vector.newBuilder[String]
    entries.keySet().forEach(key => out += key.toString)
    out.result()
  }

  private def keyOf(text: String): Key = Key(identity, StableIds.sha256Hex(text))

  private def cacheable(result: EmbeddingSuccess): Boolean =
    result.model == model && result.values != null &&
      result.values.size == model.dimension && result.values.forall(_.isFinite)

  def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
    val input = texts.toVector
    if (input.isEmpty) return Vector.empty
    val keys: Vector[Option[Key]] = input.map(text => Option(text).map(keyOf))
    val results = Array.fill[EmbeddingResult](input.size)(null)

    lock.synchronized {
      keys.zipWithIndex.foreach {
        case (Some(key), position) =>
          val cached = entries.get(key)
          if (cached != null) { results(position) = cached; hits += 1 }
        case (None, _) => ()
      }
    }

    // Distinct misses in first-occurrence order; all null texts share one pass-through slot.
    val slots = mutable.LinkedHashMap.empty[Option[Key], (String, mutable.ArrayBuffer[Int])]
    input.indices.foreach { position =>
      if (results(position) == null)
        slots.getOrElseUpdate(
          keys(position),
          (input(position), mutable.ArrayBuffer.empty[Int])
        ) match {
          case (_, positions) => positions += position
        }
    }
    if (slots.isEmpty) return results.toVector

    val missing = slots.toVector
    lock.synchronized { misses += missing.size }
    val fetched = underlying.embed(missing.map(_._2._1)).toVector
    if (fetched.size != missing.size) throw new IllegalStateException(ResultCountMismatch)
    if (fetched.contains(null)) throw new IllegalStateException(NullResult)

    val wellFormed = fetched.forall {
      case success: EmbeddingSuccess => cacheable(success)
      case _                         => true
    }
    var duplicates = 0L
    missing.zip(fetched).foreach { case ((_, (_, positions)), result) =>
      positions.foreach(position => results(position) = result)
      duplicates += positions.size - 1
    }
    lock.synchronized {
      hits += duplicates
      if (wellFormed)
        missing.zip(fetched).foreach {
          case ((Some(key), _), success: EmbeddingSuccess) => entries.put(key, success)
          case _                                           => ()
        }
    }
    results.toVector
  }

  override def toString: String = {
    val s = stats
    s"CachingEmbeddingClient(provider=${provider.wire}, model=${model.modelId}, " +
      s"capacity=${s.capacity}, size=${s.size}, hits=${s.hits}, misses=${s.misses}, " +
      s"evictions=${s.evictions})"
  }
}
