package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.bedrockruntime.model.*
import java.nio.charset.StandardCharsets.UTF_8
import java.time.Duration
import java.util.concurrent.{Semaphore, TimeUnit}
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal

final case class StructuredLlmRequest(
    toolName: String,
    systemPrompt: String,
    userData: String,
    schemaJson: String,
    promptVersion: String,
    schemaVersion: String,
    timeoutMillis: Long
)
final case class LlmUsage(inputTokens: Option[Long], outputTokens: Option[Long])
enum LlmResult {
  case Output(json: String, usage: LlmUsage, modelId: String, modelVersion: String)
  case Failure(code: String)
}
trait LlmClient {
  def complete(request: StructuredLlmRequest): LlmResult
}

/** Only bounded correlation tokens and closed outcome labels are logged, never source payloads. */
private[rag] object RuntimeStageLog {
  private val logger = org.slf4j.LoggerFactory.getLogger("scholarchain.runtime.stage")
  private def correlation(value: String): String =
    if (value.matches("[A-Za-z0-9:_-]{1,128}")) value else StableIds.sha256Hex(value)
  def outcome(
      stage: String,
      traceId: String,
      runId: String,
      status: String,
      planId: Option[String]
  ): Unit = {
    val event = ujson.Obj(
      "event" -> "runtime-stage-outcome",
      "stage" -> stage,
      "traceId" -> correlation(traceId),
      "runId" -> correlation(runId),
      "outcome" -> status
    )
    planId.foreach(id => event("planId") = correlation(id))
    logger.info(event.render())
  }
}

/** Scripted offline outputs are observable and deterministic; exhaustion never calls a provider. */
final class ScriptedLlmClient(script: Vector[LlmResult]) extends LlmClient {
  private var requests = Vector.empty[StructuredLlmRequest]
  def calls: Vector[StructuredLlmRequest] = synchronized(requests)
  def complete(request: StructuredLlmRequest): LlmResult = synchronized {
    val position = requests.size
    requests :+= request
    script.lift(position).getOrElse(LlmResult.Failure("script-exhausted"))
  }
}

/** Caller injects and owns the SDK client, region/IAM setup and disabled SDK retries. No SDK client
  * is constructed here. Tool support for a configured deployed model is a future live gate. Exactly
  * one named tool-use block is accepted; text is never parsed as a substitute.
  */
final class BedrockConverseLlmClient(client: BedrockRuntimeClient, config: RuntimeConfig)
    extends LlmClient {
  require(RuntimeConfigValidation.check(config).isEmpty)
  private val permits = new Semaphore(config.operations.maxConcurrentLlmCalls)
  def complete(request: StructuredLlmRequest): LlmResult = {
    val started = System.nanoTime()
    if (
      request.timeoutMillis <= 0 || request.toolName.trim.isEmpty ||
      request.systemPrompt.trim.isEmpty || request.userData.trim.isEmpty ||
      Vector(request.systemPrompt, request.userData, request.schemaJson)
        .map(_.getBytes(UTF_8).length.toLong)
        .sum > config.maxInputBytes
    ) return LlmResult.Failure("llm-input-bound")
    var acquired = false
    try {
      acquired = permits.tryAcquire(request.timeoutMillis, TimeUnit.MILLISECONDS)
      if (!acquired) return LlmResult.Failure("llm-concurrency-deadline")
      val remaining = request.timeoutMillis - (System.nanoTime() - started) / 1000000
      if (remaining <= 0) return LlmResult.Failure("llm-deadline")
      val tool = ToolSpecification
        .builder()
        .name(request.toolName)
        .description("Return the requested validated structured output")
        .inputSchema(
          ToolInputSchema
            .builder()
            .json(LlmDocuments.toDocument(ujson.read(request.schemaJson)))
            .build()
        )
        .build()
      val call = ConverseRequest
        .builder()
        .modelId(config.model.modelId)
        .system(SystemContentBlock.builder().text(request.systemPrompt).build())
        .messages(
          Message
            .builder()
            .role(ConversationRole.USER)
            .content(ContentBlock.builder().text(request.userData).build())
            .build()
        )
        .inferenceConfig(
          InferenceConfiguration
            .builder()
            .temperature(config.model.temperature.toFloat)
            .maxTokens(config.maxOutputTokens)
            .build()
        )
        .toolConfig(
          ToolConfiguration
            .builder()
            .tools(Tool.builder().toolSpec(tool).build())
            .toolChoice(
              ToolChoice
                .builder()
                .tool(SpecificToolChoice.builder().name(request.toolName).build())
                .build()
            )
            .build()
        )
        .overrideConfiguration(c => c.apiCallTimeout(Duration.ofMillis(remaining)))
        .build()
      val response = client.converse(call)
      if (
        response.output() == null || response.output().message() == null ||
        response.output().message().role() != ConversationRole.ASSISTANT || response
          .stopReason() != StopReason.TOOL_USE
      )
        return LlmResult.Failure("llm-invalid-tool-output")
      val blocks = response.output().message().content().asScala.toVector
      if (
        blocks.size != 1 || blocks.head
          .toolUse() == null || blocks.head.toolUse().name() != request.toolName
      )
        return LlmResult.Failure("llm-invalid-tool-output")
      val json = LlmDocuments.fromDocument(blocks.head.toolUse().input()).render()
      if (json.getBytes(UTF_8).length > config.maxInputBytes)
        return LlmResult.Failure("llm-output-bound")
      val usage = Option(response.usage())
      LlmResult.Output(
        json,
        LlmUsage(
          usage.flatMap(u => Option(u.inputTokens()).map(_.longValue())),
          usage.flatMap(u => Option(u.outputTokens()).map(_.longValue()))
        ),
        config.model.modelId,
        config.model.modelVersion
      )
    } catch {
      case _: InterruptedException =>
        Thread.currentThread().interrupt()
        LlmResult.Failure("llm-interrupted")
      case _: BedrockRuntimeException => LlmResult.Failure("llm-provider-rejected")
      case NonFatal(_)                => LlmResult.Failure("llm-client-or-response-failure")
    } finally if (acquired) permits.release()
  }
}

private[rag] object LlmDocuments {
  def toDocument(value: ujson.Value): Document = value match {
    case ujson.Null    => Document.fromNull()
    case ujson.Str(v)  => Document.fromString(v)
    case ujson.Bool(v) => Document.fromBoolean(v)
    case ujson.Num(v)  => Document.fromNumber(java.math.BigDecimal.valueOf(v))
    case v: ujson.Arr  => Document.fromList(v.value.map(toDocument).asJava)
    case v: ujson.Obj =>
      Document.fromMap(v.value.iterator.map((k, v) => k -> toDocument(v)).toMap.asJava)
  }
  def fromDocument(value: Document): ujson.Value = {
    if (value == null || value.isNull) ujson.Null
    else if (value.isString) ujson.Str(value.asString())
    else if (value.isBoolean) ujson.Bool(value.asBoolean())
    else if (value.isNumber) {
      val exact = value.asNumber().bigDecimalValue()
      val number = exact.doubleValue()
      if (
        !number.isFinite || java.math.BigDecimal.valueOf(number).compareTo(exact) != 0 ||
        exact.abs().compareTo(new java.math.BigDecimal("9007199254740991")) > 0
      )
        throw new IllegalArgumentException("inexact-or-unsafe-json-number")
      ujson.Num(number)
    } else if (value.isList) ujson.Arr.from(value.asList().asScala.map(fromDocument))
    else if (value.isMap)
      ujson.Obj.from(value.asMap().asScala.iterator.map((k, v) => k -> fromDocument(v)))
    else throw new IllegalArgumentException("unsupported-document-kind")
  }
}
