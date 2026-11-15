package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets.UTF_8
import java.time.Duration
import java.util.concurrent.{CompletableFuture, ExecutionException, Semaphore, TimeUnit}
import scala.util.control.NonFatal

/** Secret value object. The value is reachable only inside this module and never rendered: toString
  * is redacted, and equality is by identity so that a key cannot be probed through comparison.
  */
final class AnthropicApiKey private (private val value: String) {
  private[rag] def reveal: String = value
  override def toString: String = "AnthropicApiKey(REDACTED)"
}
object AnthropicApiKey {

  /** Visible ASCII only (no whitespace or control characters), so a value cannot inject headers.
    * The Left value is a closed code and never echoes any part of the input.
    */
  def fromValue(raw: String): Either[String, AnthropicApiKey] =
    if (raw == null || raw.isEmpty || raw.length > 512 || !raw.forall(c => c >= '!' && c <= '~'))
      Left("invalid-anthropic-api-key")
    else Right(new AnthropicApiKey(raw))
}

/** Raised by the bounded body subscriber; carries no response content. */
private[rag] final class ProviderBodyBoundExceeded extends RuntimeException("response-byte-bound")

/** Accumulates at most `limit` bytes and cancels the stream as soon as the bound would be passed.
  */
private[rag] final class BoundedBodySubscriber(limit: Int)
    extends HttpResponse.BodySubscriber[Array[Byte]] {
  private val result = new CompletableFuture[Array[Byte]]()
  private val output = new java.io.ByteArrayOutputStream()
  private var subscription: java.util.concurrent.Flow.Subscription = null
  def getBody(): java.util.concurrent.CompletionStage[Array[Byte]] = result
  def onSubscribe(s: java.util.concurrent.Flow.Subscription): Unit = {
    subscription = s
    s.request(1)
  }
  def onNext(buffers: java.util.List[ByteBuffer]): Unit = {
    val it = buffers.iterator()
    while (it.hasNext && !result.isDone) {
      val buffer = it.next()
      if (output.size().toLong + buffer.remaining() > limit) {
        subscription.cancel()
        result.completeExceptionally(new ProviderBodyBoundExceeded)
      } else {
        val bytes = new Array[Byte](buffer.remaining())
        buffer.get(bytes)
        output.write(bytes)
      }
    }
    if (!result.isDone) subscription.request(1)
  }
  def onError(error: Throwable): Unit = {
    result.completeExceptionally(new IllegalStateException("response-body-read-failed"))
    ()
  }
  def onComplete(): Unit = {
    result.complete(output.toByteArray)
    ()
  }
}

/** Number and nesting rules applied to the raw response text, after it parsed as JSON. ujson reads
  * numbers as doubles, so exactness is judged on each numeric token, using the same rule as the
  * Bedrock document conversion: finite, exactly representable, and at most 2^53 - 1 in magnitude.
  */
private[rag] object ProviderJsonRules {
  val maxDepth = 64
  private val maxSafe = java.math.BigDecimal.valueOf(2).pow(53).subtract(java.math.BigDecimal.ONE)
  private def numberChar(c: Char): Boolean =
    (c >= '0' && c <= '9') || c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E'
  def requireBoundedExact(text: String): Unit = {
    var i = 0
    var depth = 0
    while (i < text.length) {
      val c = text.charAt(i)
      if (c == '"') {
        i += 1
        while (i < text.length && text.charAt(i) != '"') i += (if (text.charAt(i) == '\\') 2 else 1)
        i += 1
      } else if (c == '[' || c == '{') {
        depth += 1
        if (depth > maxDepth) throw new IllegalArgumentException("json-depth-bound")
        i += 1
      } else if (c == ']' || c == '}') {
        depth -= 1
        i += 1
      } else if (c == '-' || (c >= '0' && c <= '9')) {
        val start = i
        while (i < text.length && numberChar(text.charAt(i))) i += 1
        val exact = new java.math.BigDecimal(text.substring(start, i))
        val number = exact.doubleValue()
        if (
          !number.isFinite || java.math.BigDecimal.valueOf(number).compareTo(exact) != 0 ||
          exact.abs().compareTo(maxSafe) > 0
        ) throw new IllegalArgumentException("inexact-or-unsafe-json-number")
      } else i += 1
    }
  }
}

object AnthropicMessagesLlmClient {

  /** Aliases of the defaults, kept for callers. They are defaults, never a pin: the model id used
    * is `RuntimeConfig.model.modelId`, and endpoint and limits come from [[AnthropicSettings]].
    */
  val ModelId: String = AnthropicDefaults.ModelId
  val DefaultBaseUri: String = AnthropicDefaults.BaseUri
  val DefaultAnthropicVersion: String = AnthropicDefaults.Version
  val PromptTokenLimit: Long = AnthropicDefaults.PromptTokenLimit
  val TokenizerGrowth: Double = AnthropicDefaults.MaxTokensFactor

  /** Closed failure codes added by this adapter (all others are shared with the Bedrock client). */
  val RefusalCode: String = "llm-refusal"
  val PromptTooLargeCode: String = "llm-prompt-too-large"

  /** Provider max_tokens for a configured output budget: ceil(budget x factor). */
  private[rag] def maxTokensFor(configured: Int, factor: Double): Int =
    math.ceil(configured.toDouble * factor).toInt

  /** Estimate: one token per `bytesPerToken` UTF-8 bytes of system prompt, data and tool schema,
    * rounded up. It is an estimate and never a billing figure.
    */
  private[rag] def estimatePromptTokens(request: StructuredLlmRequest, bytesPerToken: Int): Long = {
    val bytes = Vector(request.systemPrompt, request.userData, request.schemaJson)
      .map(_.getBytes(UTF_8).length.toLong)
      .sum
    (bytes + bytesPerToken - 1L) / bytesPerToken
  }
  private val loopbackHosts = Set("127.0.0.1", "localhost", "[::1]")
  private val removedSchemaKeys = Vector("$schema", "$id", "title")
  private[rag] def messagesUri(baseUri: String): URI = {
    val uri = URI.create(baseUri.stripSuffix("/"))
    val secure = uri.getScheme == "https"
    val loopback = uri.getScheme == "http" && loopbackHosts.contains(uri.getHost)
    require(
      (secure || loopback) && uri.getHost != null && uri.getUserInfo == null &&
        uri.getQuery == null && uri.getFragment == null &&
        (uri.getPath == null || uri.getPath.isEmpty),
      "invalid-anthropic-base-uri"
    )
    URI.create(uri.toString + "/v1/messages")
  }
  private[rag] def trimSchema(schema: ujson.Value): ujson.Value = schema match {
    case obj: ujson.Obj =>
      val copy = ujson.Obj.from(obj.value.iterator)
      removedSchemaKeys.foreach(copy.value.remove)
      copy
    case other => other
  }
}

/** Direct Anthropic Messages API adapter for the configured model (`RuntimeConfig.model.modelId`,
  * default `claude-haiku-5-5`). Endpoint, API version, prompt-token limit, max_tokens factor and
  * the bytes-per-token estimate come from [[AnthropicSettings]]. Uses only the JDK HttpClient,
  * forces the single named tool, performs no retries and reads no response body unless the status
  * is 200. The response body, headers and the API key never appear in a result, message or log:
  * only closed failure codes leave this class. Plain http is accepted only for loopback hosts, so
  * the key cannot travel in cleartext remotely.
  *
  * Model rules enforced here: the request never carries `temperature`, `top_p`, `top_k`, prefill or
  * `strict` (the runtime config temperature is ignored); `max_tokens` is the configured budget
  * times the configured factor; content blocks are read by `type`; `stop_reason` `refusal` is the
  * non-retried `llm-refusal`; a prompt estimated at the configured limit or more is refused before
  * any call with `llm-prompt-too-large`. These are the Haiku 5.5 request rules and apply to
  * whichever Anthropic model is configured. Question text and evidence snippets leave AWS on this
  * path. Live compatibility, price and latency are unverified.
  */
final class AnthropicMessagesLlmClient(
    apiKey: AnthropicApiKey,
    config: RuntimeConfig,
    settings: AnthropicSettings = AnthropicSettings()
) extends LlmClient {
  require(RuntimeConfigValidation.check(config).isEmpty)
  private val endpoint = AnthropicMessagesLlmClient.messagesUri(settings.baseUri)
  private val permits = new Semaphore(config.operations.maxConcurrentLlmCalls)
  private val bodyLimit: Int =
    math.min(config.effectiveByteLimits.outputBytes.toLong * 2 + 16384L, Int.MaxValue - 8).toInt
  private lazy val http = HttpClient
    .newBuilder()
    .version(HttpClient.Version.HTTP_1_1)
    .followRedirects(HttpClient.Redirect.NEVER)
    .connectTimeout(Duration.ofSeconds(10))
    .build()

  def complete(request: StructuredLlmRequest): LlmResult = {
    val started = System.nanoTime()
    if (
      request.timeoutMillis <= 0 || request.toolName.trim.isEmpty ||
      request.systemPrompt.trim.isEmpty || request.userData.trim.isEmpty ||
      request.systemPrompt.getBytes(UTF_8).length > config.effectiveByteLimits.promptBytes ||
      request.schemaJson.getBytes(UTF_8).length > config.effectiveByteLimits.promptBytes ||
      Vector(request.systemPrompt, request.userData, request.schemaJson)
        .map(_.getBytes(UTF_8).length.toLong)
        .sum > config.effectiveByteLimits.requestBytes
    ) return LlmResult.Failure("llm-input-bound")
    if (
      AnthropicMessagesLlmClient.estimatePromptTokens(request, settings.bytesPerEstimatedToken) >=
        settings.promptTokenLimit
    ) return LlmResult.Failure(AnthropicMessagesLlmClient.PromptTooLargeCode)
    var acquired = false
    var future: CompletableFuture[HttpResponse[Array[Byte]]] = null
    try {
      acquired = permits.tryAcquire(request.timeoutMillis, TimeUnit.MILLISECONDS)
      if (!acquired) return LlmResult.Failure("llm-concurrency-deadline")
      val remaining = request.timeoutMillis - (System.nanoTime() - started) / 1000000
      if (remaining <= 0) return LlmResult.Failure("llm-deadline")
      val body = ujson.Obj(
        "model" -> config.model.modelId,
        "max_tokens" -> AnthropicMessagesLlmClient
          .maxTokensFor(config.maxOutputTokens, settings.maxTokensFactor),
        "system" -> request.systemPrompt,
        "messages" -> ujson.Arr(ujson.Obj("role" -> "user", "content" -> request.userData)),
        "tools" -> ujson.Arr(
          ujson.Obj(
            "name" -> request.toolName,
            "description" -> "Return the requested validated structured output",
            "input_schema" -> AnthropicMessagesLlmClient.trimSchema(ujson.read(request.schemaJson))
          )
        ),
        "tool_choice" -> ujson.Obj("type" -> "tool", "name" -> request.toolName)
      )
      val call = HttpRequest
        .newBuilder(endpoint)
        .timeout(Duration.ofMillis(remaining))
        .header("x-api-key", apiKey.reveal)
        .header("anthropic-version", settings.anthropicVersion)
        .header("content-type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(body.render(), UTF_8))
        .build()
      future = http.sendAsync(
        call,
        new HttpResponse.BodyHandler[Array[Byte]] {
          def apply(info: HttpResponse.ResponseInfo): HttpResponse.BodySubscriber[Array[Byte]] =
            if (info.statusCode() == 200) new BoundedBodySubscriber(bodyLimit)
            else HttpResponse.BodySubscribers.replacing(Array.emptyByteArray)
        }
      )
      val response = future.get(remaining, TimeUnit.MILLISECONDS)
      if (response.statusCode() != 200) return LlmResult.Failure("llm-provider-rejected")
      interpret(request, response.body())
    } catch {
      case _: InterruptedException =>
        Thread.currentThread().interrupt()
        LlmResult.Failure("llm-interrupted")
      case e: ExecutionException if causedByBound(e) => LlmResult.Failure("llm-output-bound")
      case NonFatal(_) => LlmResult.Failure("llm-client-or-response-failure")
    } finally {
      if (future != null && !future.isDone) future.cancel(true)
      if (acquired) permits.release()
    }
  }

  private def causedByBound(error: Throwable): Boolean = {
    var current = error
    var depth = 0
    while (current != null && depth < 8) {
      if (current.isInstanceOf[ProviderBodyBoundExceeded]) return true
      current = current.getCause
      depth += 1
    }
    false
  }

  private def interpret(request: StructuredLlmRequest, bytes: Array[Byte]): LlmResult = {
    val text = UTF_8
      .newDecoder()
      .onMalformedInput(CodingErrorAction.REPORT)
      .onUnmappableCharacter(CodingErrorAction.REPORT)
      .decode(ByteBuffer.wrap(bytes))
      .toString
    val invalid = LlmResult.Failure("llm-invalid-tool-output")
    val parsed = ujson.read(text)
    try ProviderJsonRules.requireBoundedExact(text)
    catch { case _: IllegalArgumentException => return invalid }
    val root = parsed match {
      case obj: ujson.Obj => obj
      case _              => return invalid
    }
    def str(value: ujson.Obj, key: String): Option[String] =
      value.value.get(key).flatMap(_.strOpt)
    if (!str(root, "model").contains(config.model.modelId))
      return LlmResult.Failure("llm-model-mismatch")
    if (!str(root, "role").contains("assistant")) return invalid
    val stop = str(root, "stop_reason")
    if (stop.contains("refusal")) return LlmResult.Failure(AnthropicMessagesLlmClient.RefusalCode)
    if (!stop.contains("tool_use")) return invalid
    val blocks = root.value.get("content").flatMap(_.arrOpt).map(_.toVector).getOrElse(Vector.empty)
    val typed = blocks.flatMap(_.objOpt)
    if (typed.size != blocks.size) return invalid
    // Blocks are read by type. Thinking and text blocks are never a substitute for the tool call
    // and are ignored; any other block type is refused. Exactly one tool_use block is accepted.
    val ignorable = Set("thinking", "redacted_thinking", "text")
    if (typed.exists(b => !str(b, "type").exists(t => t == "tool_use" || ignorable(t))))
      return invalid
    val toolBlocks = typed.filter(b => str(b, "type").contains("tool_use"))
    if (toolBlocks.size != 1) return invalid
    val block = toolBlocks.head
    if (!str(block, "name").contains(request.toolName)) return invalid
    val input = block.value.get("input").flatMap(_.objOpt) match {
      case Some(obj) => obj
      case None      => return invalid
    }
    val json = input.render()
    if (json.getBytes(UTF_8).length > config.effectiveByteLimits.outputBytes)
      return LlmResult.Failure("llm-output-bound")
    val usage = root.value.get("usage").flatMap(_.objOpt)
    def tokens(name: String): Option[Long] = usage
      .flatMap(_.value.get(name))
      .flatMap(_.numOpt)
      .filter(n => n >= 0 && n == math.rint(n))
      .map(_.toLong)
    LlmResult.Output(
      json,
      LlmUsage(tokens("input_tokens"), tokens("output_tokens")),
      config.model.modelId,
      config.model.modelVersion
    )
  }
}
