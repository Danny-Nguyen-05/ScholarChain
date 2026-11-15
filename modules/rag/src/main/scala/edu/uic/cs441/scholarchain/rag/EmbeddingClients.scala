package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import software.amazon.awssdk.core.SdkBytes
import software.amazon.awssdk.core.exception.SdkClientException
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.bedrockruntime.model.{
  BedrockRuntimeException,
  InvokeModelRequest
}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.Locale
import java.util.concurrent.{Callable, Executors, Semaphore}
import scala.util.control.NonFatal

/** Predictable lexical fixture embedder; it makes no claim about a real model's retrieval quality.
  */
final class DeterministicHashedEmbeddingClient(val model: EmbeddingModel) extends EmbeddingClient {
  require(EmbeddingValidation.model(model).isEmpty)
  def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
    val words = "[\\p{L}\\p{N}]+".r.findAllIn(text.toLowerCase(Locale.ROOT)).toVector
    if (words.isEmpty) EmbeddingFailure("empty-embedding-tokens", false, model, 0)
    else {
      val values = Array.fill[Double](model.dimension)(0.0)
      words.sorted.foreach { word =>
        val slot = (java.lang.Long.parseUnsignedLong(
          StableIds.sha256Hex(word).take(8),
          16
        ) % model.dimension).toInt
        values(slot) += 1.0
      }
      val norm = math.sqrt(values.map(v => v * v).sum)
      EmbeddingSuccess(values.map(v => (v / norm).toFloat).toVector, model, 1)
    }
  }
}

/** Configuration carries provider/model/region decisions. The byte limit is a deliberately
  * conservative local token budget, not an exact Titan tokenizer or a measured billing control.
  * Provider-side token-limit errors remain typed permanent failures.
  */
final case class BedrockEmbeddingConfig(
    model: EmbeddingModel,
    region: String,
    maxConcurrentCalls: Int = 2,
    maxAttempts: Int = 3,
    baseDelayMillis: Long = 25,
    maxDelayMillis: Long = 1000,
    maxInputCharacters: Int = 50000,
    maxInputTokens: Int = 8192,
    maxBatchItems: Int = 500,
    requestTimeoutMillis: Long = 30000
) {
  require(EmbeddingValidation.model(model).isEmpty && Set(256, 512, 1024)(model.dimension))
  require(region.trim.nonEmpty && maxConcurrentCalls > 0 && maxAttempts > 0)
  require(baseDelayMillis >= 0 && maxDelayMillis >= baseDelayMillis)
  require(maxInputCharacters > 0 && maxInputCharacters <= 50000)
  require(
    maxInputTokens > 0 && maxInputTokens <= 8192 && maxBatchItems > 0 && requestTimeoutMillis > 0
  )
}

/** The caller owns SDK lifecycle and region/IAM construction. SDK transport retries should be
  * disabled by that composition so maxAttempts counts actual InvokeModel requests exactly.
  */
final class BedrockEmbeddingClient(
    client: BedrockRuntimeClient,
    config: BedrockEmbeddingConfig,
    sleep: Long => Unit = millis => Thread.sleep(millis)
) extends ProviderEmbeddingClient {
  val model: EmbeddingModel = config.model
  val provider: EmbeddingProvider = EmbeddingProvider.Bedrock
  private val permits = new Semaphore(config.maxConcurrentCalls)
  def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
    val input = texts.toVector
    if (input.size > config.maxBatchItems)
      input.map(_ => EmbeddingFailure("embedding-batch-limit", false, model, 0))
    else if (input.isEmpty) Vector.empty
    else {
      val executor = Executors.newFixedThreadPool(math.min(config.maxConcurrentCalls, input.size))
      try {
        val tasks = input.map(text =>
          executor.submit(new Callable[EmbeddingResult] {
            def call(): EmbeddingResult = {
              try permits.acquire()
              catch {
                case _: InterruptedException =>
                  Thread.currentThread().interrupt()
                  return EmbeddingFailure("embedding-interrupted", false, model, 0)
              }
              try one(text)
              finally permits.release()
            }
          })
        )
        tasks.map { task =>
          try task.get()
          catch {
            case _: InterruptedException =>
              Thread.currentThread().interrupt()
              EmbeddingFailure("embedding-interrupted", false, model, 0)
            case NonFatal(_) => EmbeddingFailure("embedding-client-failure", false, model, 0)
          }
        }
      } finally executor.shutdownNow()
    }
  }
  private def one(text: String): EmbeddingResult = {
    if (text.trim.isEmpty) return EmbeddingFailure("empty-document-text", false, model, 0)
    if (
      text.codePointCount(0, text.length) > config.maxInputCharacters ||
      text.getBytes(UTF_8).length > config.maxInputTokens
    )
      return EmbeddingFailure("embedding-input-limit", false, model, 0)
    var attempt = 0
    var delay = config.baseDelayMillis
    while (attempt < config.maxAttempts) {
      attempt += 1
      try {
        val body =
          ujson.Obj("inputText" -> text, "dimensions" -> model.dimension, "normalize" -> true)
        val request = InvokeModelRequest
          .builder()
          .modelId(model.modelId)
          .contentType("application/json")
          .accept("application/json")
          .body(SdkBytes.fromUtf8String(body.render()))
          .overrideConfiguration(c =>
            c.apiCallTimeout(java.time.Duration.ofMillis(config.requestTimeoutMillis))
          )
          .build()
        val json = ujson.read(client.invokeModel(request).body().asUtf8String())
        val values = json("embedding").arr.map(_.num.toFloat).toVector
        if (values.size != model.dimension || values.exists(v => !v.isFinite))
          return EmbeddingFailure("embedding-dimension-or-value-mismatch", false, model, attempt)
        return EmbeddingSuccess(values, model, attempt)
      } catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt()
          return EmbeddingFailure("embedding-interrupted", false, model, attempt)
        case e: BedrockRuntimeException =>
          val transient = e.statusCode() == 429 || e.statusCode() >= 500
          if (!transient)
            return EmbeddingFailure("embedding-provider-rejected", false, model, attempt)
          if (attempt == config.maxAttempts)
            return EmbeddingFailure("embedding-retries-exhausted", true, model, attempt)
        case _: SdkClientException =>
          if (attempt == config.maxAttempts)
            return EmbeddingFailure("embedding-retries-exhausted", true, model, attempt)
        case NonFatal(_) =>
          return EmbeddingFailure("embedding-invalid-response", false, model, attempt)
      }
      try sleep(delay)
      catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt()
          return EmbeddingFailure("embedding-interrupted", false, model, attempt)
        case NonFatal(_) =>
          return EmbeddingFailure("embedding-backoff-failure", false, model, attempt)
      }
      delay =
        math.min(config.maxDelayMillis, if (delay > Long.MaxValue / 2) Long.MaxValue else delay * 2)
    }
    EmbeddingFailure("embedding-retries-exhausted", true, model, attempt)
  }
}
