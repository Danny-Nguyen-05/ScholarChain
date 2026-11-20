package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.EmbeddingModel
import edu.uic.cs441.scholarchain.rag.CachingEmbeddingClient
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

/** Public limits of `POST /v1/semantic/retrieve` (session-2 plan P40, accepted default (a)). They
  * are narrower than the internal route's [[SemanticApiConfig]], which keeps its own limits; every
  * body accepted here is therefore also accepted by the internal route. Question and filter-value
  * lengths count Unicode code points; the body bound counts UTF-8 bytes of the raw request.
  */
final case class PublicSemanticLimits(
    maxTopK: Int = 20,
    defaultTopK: Int = 20,
    maxQuestionChars: Int = 1000,
    maxBodyBytes: Int = 8192,
    maxFilters: Int = 16
) {
  require(
    maxTopK > 0 && defaultTopK >= 1 && defaultTopK <= maxTopK && maxQuestionChars > 0 &&
      maxBodyBytes > 0 && maxFilters > 0,
    "invalid-public-semantic-limits"
  )
}

/** Token-bucket parameters for the public semantic route, one bucket per API-key hash in each
  * query-api process. `maxKeys` bounds the number of buckets held in memory.
  */
final case class RateLimitSettings(
    requestsPerSecond: Long = RateLimitSettings.DefaultRequestsPerSecond,
    burst: Long = RateLimitSettings.DefaultBurst,
    maxKeys: Int = RateLimitSettings.DefaultMaxKeys
) {
  require(
    requestsPerSecond >= 1 && requestsPerSecond <= RateLimitSettings.MaxRequestsPerSecond &&
      burst >= 1 && burst <= RateLimitSettings.MaxBurst && maxKeys >= 1,
    "invalid-rate-limit-settings"
  )
}
object RateLimitSettings {
  val RateEnv = "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND"
  val BurstEnv = "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST"
  val DefaultRequestsPerSecond = 50L
  val DefaultBurst = 100L
  val DefaultMaxKeys = 1024
  val MaxRequestsPerSecond = 100000L
  val MaxBurst = 1000000L

  /** A refusal is a closed code naming only the variable, never its value. Blank means unset. */
  def fromEnvironment(env: Map[String, String]): Either[String, RateLimitSettings] = for {
    rate <- EnvironmentBounds.long(env, RateEnv, DefaultRequestsPerSecond, 1, MaxRequestsPerSecond)
    burst <- EnvironmentBounds.long(env, BurstEnv, DefaultBurst, 1, MaxBurst)
  } yield RateLimitSettings(rate, burst)
}

/** Size of the semantic-service query-embedding cache (P40 accepted default (c)). */
object EmbeddingCacheSettings {
  val EnvName = "SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES"
  val MaxEntries = 100000L
  def default: Int = CachingEmbeddingClient.DefaultMaxEntries

  /** Used by the offline-synthetic composition; aws mode reads the same variable and bounds through
    * `AwsServiceConfig` with the aws refusal convention.
    */
  def fromEnvironment(env: Map[String, String]): Either[String, Int] =
    EnvironmentBounds.long(env, EnvName, default.toLong, 1, MaxEntries).map(_.toInt)
}

private[services] object EnvironmentBounds {
  def refusal(name: String): String = "invalid-service-configuration:" + name
  def long(
      env: Map[String, String],
      name: String,
      default: Long,
      min: Long,
      max: Long
  ): Either[String, Long] = env.get(name).map(_.trim).filter(_.nonEmpty) match {
    case None => Right(default)
    case Some(text) =>
      try {
        val n = text.toLong
        if (n < min || n > max) Left(refusal(name)) else Right(n)
      } catch { case _: NumberFormatException => Left(refusal(name)) }
  }
}

sealed trait RateDecision
object RateDecision {
  case object Allowed extends RateDecision
  final case class Limited(retryAfterSeconds: Long) extends RateDecision
}

/** In-memory token bucket per key. Keys must already be hashes (the route passes the SHA-256 of the
  * presented API key); a raw key is never held. Integer arithmetic in units of 1e-9 token keeps
  * refill exact for an injected clock. When `maxKeys` buckets exist, buckets that have refilled to
  * the burst (indistinguishable from a new bucket) are dropped first, then the least recently used.
  */
final class TokenBucketRateLimiter(
    val settings: RateLimitSettings = RateLimitSettings(),
    nowNanos: () => Long = () => System.nanoTime()
) {
  private val Scale = 1000000000L
  private val rate = settings.requestsPerSecond
  private val capacity = settings.burst * Scale
  private final class Bucket(var units: Long, var at: Long)
  private val buckets = new java.util.LinkedHashMap[String, Bucket](16, 0.75f, true)

  private def ceilDiv(a: Long, b: Long): Long = (a + b - 1) / b
  private def refill(bucket: Bucket, now: Long): Unit = {
    val elapsed = now - bucket.at
    if (elapsed > 0) {
      val missing = capacity - bucket.units
      val toFull = ceilDiv(missing, rate)
      bucket.units = if (elapsed >= toFull) capacity else bucket.units + elapsed * rate
      bucket.at = now
    }
  }
  private def makeRoom(now: Long): Unit = if (buckets.size >= settings.maxKeys) {
    val it = buckets.values().iterator()
    while (it.hasNext) {
      val b = it.next(); refill(b, now); if (b.units >= capacity) it.remove()
    }
    if (buckets.size >= settings.maxKeys) {
      val eldest = buckets.keySet().iterator(); eldest.next(); eldest.remove()
    }
  }

  def acquire(keyHash: String): RateDecision = synchronized {
    val now = nowNanos()
    val bucket = Option(buckets.get(keyHash)).getOrElse {
      makeRoom(now)
      val created = new Bucket(capacity, now); buckets.put(keyHash, created); created
    }
    refill(bucket, now)
    if (bucket.units >= Scale) { bucket.units -= Scale; RateDecision.Allowed }
    else {
      val waitNanos = ceilDiv(Scale - bucket.units, rate)
      RateDecision.Limited(math.max(1L, ceilDiv(waitNanos, Scale)))
    }
  }
  def bucketCount: Int = synchronized(buckets.size)

  /** The bucket keys currently held (hashes only); for tests. */
  private[services] def heldKeys: Set[String] = synchronized {
    val out = Set.newBuilder[String]; buckets.keySet().forEach(k => out += k); out.result()
  }
}

/** `POST /v1/semantic/retrieve` on query-api: public limits, the per-key rate limit, and a response
  * projected to exactly the internal route's fields. The question is never logged or placed in a
  * metric label; only the forwarded body carries it to semantic-service.
  */
final class PublicSemanticRoute(
    val limits: PublicSemanticLimits = PublicSemanticLimits(),
    val limiter: TokenBucketRateLimiter = new TokenBucketRateLimiter()
) {
  private def codePoints(s: String): Int = s.codePointCount(0, s.length)

  /** Returns the canonical body to forward with its topK, or a typed 400. Nesting deeper than
    * [[RequestJson.MaxNestingDepth]] is refused on the raw text before ujson parses it.
    */
  def validate(body: String): Either[ApiError, ForwardedSemanticRequest] = try {
    if (body.getBytes(UTF_8).length > limits.maxBodyBytes || !RequestJson.withinDepth(body))
      Left(ApiError.invalid)
    else {
      val json = ujson.read(body)
      val obj = json.obj
      if (!obj.keySet.subsetOf(Set("question", "topK", "filters"))) Left(ApiError.invalid)
      else {
        val question = obj("question").str
        val topK = obj.get("topK").map(_.num).getOrElse(limits.defaultTopK.toDouble)
        val filters = obj.get("filters").map(_.obj.toVector.map((k, v) => k -> v.str))
        val validQuestion =
          question.trim.nonEmpty && codePoints(question) <= limits.maxQuestionChars
        val validTopK = topK.isWhole && topK >= 1 && topK <= limits.maxTopK
        val validFilters = filters.forall(fs =>
          fs.size <= limits.maxFilters &&
            fs.forall((k, v) => k.nonEmpty && codePoints(v) <= limits.maxQuestionChars)
        )
        if (!validQuestion || !validTopK || !validFilters) Left(ApiError.invalid)
        else {
          val forwarded = ujson.Obj("question" -> question, "topK" -> topK.toInt)
          filters.foreach(fs =>
            forwarded("filters") = ujson.Obj.from(fs.map((k, v) => k -> ujson.Str(v)))
          )
          Right(ForwardedSemanticRequest(forwarded.render(), topK.toInt))
        }
      }
    }
  } catch { case NonFatal(_) => Left(ApiError.invalid) }

  /** Rebuilds the reply from exactly `hits[].{key, distance, metadata}` and `model`, keeping at
    * most the first `topK` hits in downstream order. A downstream body of another shape is a 502,
    * never forwarded.
    */
  def project(reply: ApiReply, topK: Int): Either[ApiError, ApiReply] = try {
    val body = reply.body
    val hits = body("hits").arr.toVector.take(topK).map { h =>
      ujson.Obj(
        "key" -> h("key").str,
        "distance" -> h("distance").num,
        "metadata" -> ujson.Obj.from(
          h("metadata").obj.toVector.map((k, v) => k -> ujson.Str(v.str))
        )
      )
    }
    val model = upickle.default.read[EmbeddingModel](body("model"))
    Right(
      ApiReply(
        200,
        ujson.Obj("hits" -> ujson.Arr.from(hits), "model" -> upickle.default.writeJs(model))
      )
    )
  } catch { case NonFatal(_) => Left(ApiError.downstream) }
}

/** The canonical body forwarded to the internal route and the topK it carries. */
final case class ForwardedSemanticRequest(body: String, topK: Int)

object PublicSemanticRoute {
  val Path = "/v1/semantic/retrieve"
  val rateLimited = ApiError(
    429,
    "RATE_LIMITED",
    "The request rate for this API key is above the configured limit.",
    true
  )
}
