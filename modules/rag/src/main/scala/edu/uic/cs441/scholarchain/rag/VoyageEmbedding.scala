package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets.UTF_8
import java.time.Duration
import java.util.concurrent.{CompletableFuture, ExecutionException, TimeUnit}
import scala.collection.mutable.ArrayBuffer
import scala.util.control.NonFatal

/** Secret value object for the Voyage AI key. The value is reachable only inside this module and
  * never rendered: toString is redacted, equality is by identity, and a rejected input is reported
  * with a closed code that echoes no part of it.
  */
final class VoyageApiKey private (private val value: String) {
  private[rag] def reveal: String = value
  override def toString: String = "VoyageApiKey(REDACTED)"
}
object VoyageApiKey {
  def fromValue(raw: String): Either[String, VoyageApiKey] =
    if (raw == null || raw.isEmpty || raw.length > 512 || !raw.forall(c => c >= '!' && c <= '~'))
      Left("invalid-voyage-api-key")
    else Right(new VoyageApiKey(raw))
}

/** Voyage `input_type`: `document` for ingest, `query` for queries. */
enum EmbeddingInputType(val wire: String) {
  case Document extends EmbeddingInputType("document")
  case Query extends EmbeddingInputType("query")
}

/** An embedding client that also states which provider produced its vectors. */
trait ProviderEmbeddingClient extends EmbeddingClient {
  def provider: EmbeddingProvider
}

/** Token counter and cap for embedding spend. Provider-reported usage is added after each
  * successful request; an estimate is reserved before each request and a request that would pass
  * the cap is refused before it is sent. The first 200M Voyage tokens per account are free, but
  * this counter still applies in full: it prices every token at `usdPerMillionTokens`. It is a
  * local control, not the provider's invoice.
  */
final class EmbeddingSpendCounter(val capUsd: BigDecimal, val usdPerMillionTokens: BigDecimal) {
  require(capUsd > 0 && usdPerMillionTokens > 0, "invalid-embedding-spend-counter")

  /** Largest whole token count whose price does not exceed the cap. */
  val capTokens: BigInt = (capUsd / usdPerMillionTokens * BigDecimal(1000000)).toBigInt
  private var used = BigInt(0)
  private var reserved = BigInt(0)
  def tokensUsed: BigInt = synchronized(used)
  def usdUsed: BigDecimal = synchronized(BigDecimal(used) * usdPerMillionTokens / 1000000)
  private[rag] def tryReserve(tokens: Long): Boolean = synchronized {
    if (used + reserved + BigInt(tokens) > capTokens) false
    else { reserved += BigInt(tokens); true }
  }
  private[rag] def settle(reservedTokens: Long, actualTokens: Long): Unit = synchronized {
    reserved -= BigInt(reservedTokens)
    used += BigInt(actualTokens)
  }
  private[rag] def release(reservedTokens: Long): Unit = synchronized {
    reserved -= BigInt(reservedTokens)
  }
}

/** Voyage model identity, endpoint and limits. Every default comes from [[VoyageDefaults]]; the
  * model (id, version tag, output dimension) is the stored-vector identity and must be the one the
  * index was built with.
  */
final case class VoyageEmbeddingConfig(
    inputType: EmbeddingInputType,
    model: EmbeddingModel = VoyageDefaults.Model,
    baseUri: String = VoyageDefaults.BaseUri,
    maxAttempts: Int = VoyageDefaults.MaxAttempts,
    baseDelayMillis: Long = VoyageDefaults.BaseDelayMillis,
    maxDelayMillis: Long = VoyageDefaults.MaxDelayMillis,
    requestTimeoutMillis: Long = VoyageDefaults.RequestTimeoutMillis,
    maxTextsPerRequest: Int = VoyageDefaults.MaxTextsPerRequest,
    maxTokensPerRequest: Int = VoyageDefaults.MaxTokensPerRequest,
    maxInputTokens: Int = VoyageDefaults.MaxInputTokens,
    maxResponseBytes: Int = VoyageDefaults.MaxResponseBytes,
    supportedDimensions: Set[Int] = VoyageDefaults.SupportedDimensions
) {
  require(EmbeddingValidation.model(model).isEmpty, "invalid-voyage-model")
  require(model.modelId.startsWith("voyage-"), "invalid-voyage-model")
  require(supportedDimensions.contains(model.dimension), "invalid-voyage-dimension")
  require(maxAttempts > 0 && baseDelayMillis >= 0 && maxDelayMillis >= baseDelayMillis)
  require(requestTimeoutMillis > 0)
  require(maxTextsPerRequest > 0 && maxTokensPerRequest > 0 && maxInputTokens > 0)
  require(maxResponseBytes > 0)
}

object VoyageEmbeddingClient {

  /** Aliases of the defaults, kept for callers. They are defaults, never a pin: the client uses
    * `VoyageEmbeddingConfig.model`.
    */
  val DefaultBaseUri: String = VoyageDefaults.BaseUri
  val ModelId: String = VoyageDefaults.ModelId
  val OutputDimension: Int = VoyageDefaults.Dimension
  val Model: EmbeddingModel = VoyageDefaults.Model
  val MaxTextsPerRequest: Int = VoyageDefaults.MaxTextsPerRequest
  val MaxTokensPerRequest: Int = VoyageDefaults.MaxTokensPerRequest
  val MaxInputTokens: Int = VoyageDefaults.MaxInputTokens
  private val loopbackHosts = Set("127.0.0.1", "localhost", "[::1]")
  private[rag] def embeddingsUri(baseUri: String): URI = {
    val uri = URI.create(baseUri.stripSuffix("/"))
    val secure = uri.getScheme == "https"
    val loopback = uri.getScheme == "http" && loopbackHosts.contains(uri.getHost)
    require(
      (secure || loopback) && uri.getHost != null && uri.getUserInfo == null &&
        uri.getQuery == null && uri.getFragment == null &&
        (uri.getPath == null || uri.getPath.isEmpty),
      "invalid-voyage-base-uri"
    )
    URI.create(uri.toString + "/v1/embeddings")
  }

  /** Strict upper bound: a token is at least one UTF-8 byte, so bytes bound tokens from above. */
  private[rag] def estimateTokens(text: String): Long = text.getBytes(UTF_8).length.toLong
}

/** Direct Voyage AI embeddings adapter for the configured model and output dimension (default
  * `voyage-4-lite`, 256). It uses only the JDK HttpClient and sends `input_type` `document` or
  * `query` per the config. A request carries at most `maxTextsPerRequest` texts and
  * `maxTokensPerRequest` estimated tokens; larger inputs are split into several requests in order.
  * The estimate counts one token per UTF-8 byte (a strict upper bound), so a single text must be at
  * most `maxInputTokens` bytes. Truncation is disabled so an over-long text is a typed failure and
  * never a silently shortened vector. Transient failures (HTTP 429/5xx, transport) retry up to
  * `maxAttempts` with exponential backoff; other statuses are permanent. The key, response bodies
  * and headers never appear in a result, message or log: only closed codes leave this class. Plain
  * http is accepted only for loopback hosts. Live compatibility, price and latency are unverified.
  * Question text and document text leave AWS on this path.
  */
final class VoyageEmbeddingClient(
    apiKey: VoyageApiKey,
    config: VoyageEmbeddingConfig,
    counter: EmbeddingSpendCounter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage),
    sleep: Long => Unit = millis => Thread.sleep(millis)
) extends ProviderEmbeddingClient {
  val model: EmbeddingModel = config.model
  val provider: EmbeddingProvider = EmbeddingProvider.Voyage
  private val endpoint = VoyageEmbeddingClient.embeddingsUri(config.baseUri)
  private lazy val http = HttpClient
    .newBuilder()
    .version(HttpClient.Version.HTTP_1_1)
    .followRedirects(HttpClient.Redirect.NEVER)
    .connectTimeout(Duration.ofSeconds(10))
    .build()

  def tokenCounter: EmbeddingSpendCounter = counter

  private def failure(code: String, retryable: Boolean, attempts: Int): EmbeddingFailure =
    EmbeddingFailure(code, retryable, model, attempts)

  def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
    val input = texts.toVector
    val results = Array.fill[EmbeddingResult](input.size)(null)
    val eligible = ArrayBuffer.empty[(Int, String, Long)]
    input.zipWithIndex.foreach { (text, position) =>
      if (text == null || text.trim.isEmpty)
        results(position) = failure("empty-document-text", false, 0)
      else {
        val estimate = VoyageEmbeddingClient.estimateTokens(text)
        if (estimate > config.maxInputTokens)
          results(position) = failure("embedding-input-limit", false, 0)
        else eligible += ((position, text, estimate))
      }
    }
    var batch = Vector.empty[(Int, String, Long)]
    var batchTokens = 0L
    def flush(): Unit = if (batch.nonEmpty) {
      send(batch).foreach((position, result) => results(position) = result)
      batch = Vector.empty
      batchTokens = 0L
    }
    eligible.foreach { item =>
      if (
        batch.size >= config.maxTextsPerRequest || batchTokens + item._3 > config.maxTokensPerRequest
      )
        flush()
      batch :+= item
      batchTokens += item._3
    }
    flush()
    results.toVector
  }

  private def send(batch: Vector[(Int, String, Long)]): Vector[(Int, EmbeddingResult)] = {
    val estimate = batch.map(_._3).sum
    def all(result: EmbeddingResult): Vector[(Int, EmbeddingResult)] =
      batch.map(item => item._1 -> result)
    val body = ujson.Obj(
      "input" -> ujson.Arr.from(batch.map(item => ujson.Str(item._2))),
      "model" -> model.modelId,
      "input_type" -> config.inputType.wire,
      "output_dimension" -> model.dimension,
      "output_dtype" -> "float",
      "truncation" -> false
    )
    val payload = body.render()
    var attempt = 0
    var delay = config.baseDelayMillis
    while (attempt < config.maxAttempts) {
      attempt += 1
      if (!counter.tryReserve(estimate))
        return all(failure("embedding-token-cap", false, attempt - 1))
      var settled = false
      try {
        val outcome = exchange(payload)
        outcome match {
          case Left((code, retryable)) =>
            counter.release(estimate); settled = true
            if (!retryable) return all(failure(code, false, attempt))
            if (attempt == config.maxAttempts)
              return all(failure("embedding-retries-exhausted", true, attempt))
          case Right(bytes) =>
            interpret(batch, bytes, attempt) match {
              case Left(code) =>
                counter.release(estimate); settled = true
                return all(failure(code, false, attempt))
              case Right((vectors, tokens)) =>
                counter.settle(estimate, tokens.getOrElse(estimate)); settled = true
                return batch.zip(vectors).map { (item, values) =>
                  item._1 -> EmbeddingSuccess(values, model, attempt)
                }
            }
        }
      } catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt()
          if (!settled) counter.release(estimate)
          return all(failure("embedding-interrupted", false, attempt))
        case NonFatal(_) =>
          if (!settled) counter.release(estimate)
          return all(failure("embedding-invalid-response", false, attempt))
      }
      try sleep(delay)
      catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt()
          return all(failure("embedding-interrupted", false, attempt))
        case NonFatal(_) => return all(failure("embedding-backoff-failure", false, attempt))
      }
      delay =
        math.min(config.maxDelayMillis, if (delay > Long.MaxValue / 2) Long.MaxValue else delay * 2)
    }
    all(failure("embedding-retries-exhausted", true, attempt))
  }

  /** Left is a closed (code, retryable) pair; Right is the bounded 200 response body. */
  private def exchange(payload: String): Either[(String, Boolean), Array[Byte]] = {
    var future: CompletableFuture[HttpResponse[Array[Byte]]] = null
    try {
      val call = HttpRequest
        .newBuilder(endpoint)
        .timeout(Duration.ofMillis(config.requestTimeoutMillis))
        .header("Authorization", "Bearer " + apiKey.reveal)
        .header("content-type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(payload, UTF_8))
        .build()
      future = http.sendAsync(
        call,
        new HttpResponse.BodyHandler[Array[Byte]] {
          def apply(info: HttpResponse.ResponseInfo): HttpResponse.BodySubscriber[Array[Byte]] =
            if (info.statusCode() == 200)
              new BoundedBodySubscriber(config.maxResponseBytes)
            else HttpResponse.BodySubscribers.replacing(Array.emptyByteArray)
        }
      )
      val response = future.get(config.requestTimeoutMillis, TimeUnit.MILLISECONDS)
      val status = response.statusCode()
      if (status == 200) Right(response.body())
      else if (status == 429 || status >= 500) Left(("embedding-provider-transient", true))
      else Left(("embedding-provider-rejected", false))
    } catch {
      case e: InterruptedException => throw e
      case e: ExecutionException if e.getCause.isInstanceOf[ProviderBodyBoundExceeded] =>
        Left(("embedding-invalid-response", false))
      case NonFatal(_) => Left(("embedding-provider-transient", true))
    } finally if (future != null && !future.isDone) future.cancel(true)
  }

  /** Strict response check: model echo, one finite vector of the stored dimension per input, each
    * index used exactly once. Returns vectors in input order and the provider-reported tokens.
    */
  private def interpret(
      batch: Vector[(Int, String, Long)],
      bytes: Array[Byte],
      attempt: Int
  ): Either[String, (Vector[Vector[Float]], Option[Long])] = try {
    val text = UTF_8
      .newDecoder()
      .onMalformedInput(CodingErrorAction.REPORT)
      .onUnmappableCharacter(CodingErrorAction.REPORT)
      .decode(ByteBuffer.wrap(bytes))
      .toString
    val root = ujson.read(text).obj
    if (!root.get("model").flatMap(_.strOpt).contains(model.modelId))
      Left("embedding-model-mismatch")
    else {
      val data = root("data").arr.toVector
      val indexed = data.zipWithIndex.map { (row, position) =>
        val index = row.obj.get("index").flatMap(_.numOpt).map(_.toInt).getOrElse(position)
        index -> row("embedding").arr.map(_.num.toFloat).toVector
      }
      val ordered = indexed.sortBy(_._1)
      if (
        data.size != batch.size || ordered.map(_._1) != batch.indices.toVector ||
        ordered.exists((_, v) => v.size != model.dimension || v.exists(x => !x.isFinite))
      ) Left("embedding-dimension-or-value-mismatch")
      else {
        val tokens = root
          .get("usage")
          .flatMap(_.objOpt)
          .flatMap(_.get("total_tokens"))
          .flatMap(
            _.numOpt
          )
          .filter(n => n >= 0 && n == math.rint(n))
          .map(_.toLong)
        Right((ordered.map(_._2), tokens))
      }
    }
  } catch { case NonFatal(_) => Left("embedding-invalid-response") }
}
