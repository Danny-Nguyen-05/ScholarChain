package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.charset.StandardCharsets.UTF_8
import java.time.Duration
import scala.util.Try
import upickle.default.{write, writeJs}

/** Credentials are resolved by preflight before reservation, never stored in requests, cache or
  * reports.
  */
final class OpenAIHttpTransport(credential: () => Option[String]) extends OpenAITransport {
  override def prepare(): Either[String, OpenAITransport] = Try {
    val key = credential()
      .filter(_.nonEmpty)
      .getOrElse(throw new IllegalArgumentException("missing runtime credential"))
    // Use the JDK's complete header-value validation before any durable reservation or HTTP call.
    // Its exceptions can contain the header value, so only the constant error below escapes.
    HttpRequest
      .newBuilder(URI.create(OpenAIResponses.endpoint))
      .header("Authorization", "Bearer " + key)
      .build()
    new OpenAITransport {
      def post(body: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse =
        dispatch(key, body, timeoutMs, maxResponseBytes)
    }
  }.toEither.left.map(_ => "LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID")

  def post(requestBody: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse =
    prepare().fold(
      e => throw new IllegalArgumentException(e),
      _.post(requestBody, timeoutMs, maxResponseBytes)
    )

  private def dispatch(
      key: String,
      requestBody: String,
      timeoutMs: Int,
      maxResponseBytes: Int
  ): ProviderHttpResponse = {
    val client = HttpClient
      .newBuilder()
      .followRedirects(HttpClient.Redirect.NEVER)
      .connectTimeout(Duration.ofMillis(timeoutMs))
      .build()
    val request = HttpRequest
      .newBuilder(URI.create(OpenAIResponses.endpoint))
      .timeout(Duration.ofMillis(timeoutMs))
      .header("Authorization", "Bearer " + key)
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(requestBody, UTF_8))
      .build()
    try {
      val future = client.sendAsync(
        request,
        new HttpResponse.BodyHandler[Array[Byte]] {
          def apply(info: HttpResponse.ResponseInfo): HttpResponse.BodySubscriber[Array[Byte]] =
            new OpenAIResponses.BoundedBodySubscriber(maxResponseBytes)
        }
      )
      val response =
        try future.get(timeoutMs.toLong, java.util.concurrent.TimeUnit.MILLISECONDS)
        finally { if (!future.isDone) future.cancel(true) }
      val bytes = response.body()
      val decoder = UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
      val text = decoder.decode(java.nio.ByteBuffer.wrap(bytes)).toString
      val id = response.headers().firstValue("x-request-id")
      ProviderHttpResponse(
        response.statusCode(),
        text,
        if (id.isPresent && id.get().matches("[A-Za-z0-9_.:-]{1,128}")) Some(id.get()) else None
      )
    } catch {
      case _: Exception =>
        throw new IllegalArgumentException("PROVIDER_TRANSPORT_FAILED_OR_TIMED_OUT")
    }
  }
}

object OpenAIResponses {
  val endpoint = "https://api.openai.com/v1/responses"
  private[entityresolution] final class BoundedBodySubscriber(limit: Int)
      extends HttpResponse.BodySubscriber[Array[Byte]] {
    private val result = new java.util.concurrent.CompletableFuture[Array[Byte]]()
    private val output = new java.io.ByteArrayOutputStream()
    private var subscription: java.util.concurrent.Flow.Subscription = null
    def getBody(): java.util.concurrent.CompletionStage[Array[Byte]] = result
    def onSubscribe(s: java.util.concurrent.Flow.Subscription): Unit = {
      subscription = s; s.request(1)
    }
    def onNext(buffers: java.util.List[java.nio.ByteBuffer]): Unit = {
      val it = buffers.iterator()
      while (it.hasNext && !result.isDone) {
        val buffer = it.next()
        if (output.size().toLong + buffer.remaining() > limit) {
          subscription.cancel();
          result.completeExceptionally(new IllegalArgumentException("PROVIDER_RESPONSE_BYTE_BOUND"))
        } else {
          val bytes = new Array[Byte](buffer.remaining()); buffer.get(bytes); output.write(bytes)
        }
      }
      if (!result.isDone) subscription.request(1)
    }
    def onError(error: Throwable): Unit = {
      result.completeExceptionally(new IllegalArgumentException("PROVIDER_BODY_READ_FAILED")); ()
    }
    def onComplete(): Unit = { result.complete(output.toByteArray); () }
  }
  val promptVersion = "er-adjudication-live-v1"
  def prompt: String = ResourceText.read("adjudication/live-prompt.v1.txt")
  def schemaText: String = ResourceText.read("adjudication/openai-response.schema.v1.json")
  def effectiveConfigHash(source: ResolutionConfig, live: LiveProviderConfig): String =
    StrictJson.hash(Vector(source.fingerprint, live.fingerprint))
  private def liveRequestCheck(request: AdjudicationRequest, config: LiveProviderConfig): Unit = {
    LiveProviderConfig.validate(config).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      request.schemaVersion == Adjudication.requestSchema && request.mode == "live" && request.provider == config.provider && request.model == config.model && request.modelVersion == config.modelVersion,
      "live request/provider mismatch"
    )
    require(
      request.requestHash == StrictJson.hash(request.copy(requestHash = "")),
      "live request hash mismatch"
    )
    require(
      request.promptVersion == promptVersion && request.promptHash == StableIds.sha256Hex(
        prompt
      ) && request.responseSchemaVersion == Adjudication.responseSchema && request.responseSchemaHash == StableIds
        .sha256Hex(schemaText),
      "live request prompt/schema mismatch"
    )
    require(
      request.generationSettings == Map(
        "reasoning.effort" -> config.reasoningEffort,
        "max_output_tokens" -> config.budget.maxOutputTokensPerCall.toString,
        "service_tier" -> "default",
        "store" -> "false"
      ),
      "live generation settings mismatch"
    )
    require(
      request.pairId.matches("resolution-pair:[0-9a-f]{64}") && Vector(
        request.sourceId,
        request.targetId
      ).forall(
        _.matches("resolution-endpoint:[0-9a-f]{64}")
      ) && request.sourceId != request.targetId,
      "invalid live request pair/endpoints"
    )
    require(
      Vector(request.inputEvidenceHash, request.policyHash, request.configHash)
        .forall(_.matches("[0-9a-f]{64}")),
      "invalid live request binding"
    )
    require(
      request.evidence.nonEmpty && request.evidence
        .map(_.ref)
        .distinct
        .size == request.evidence.size && request.evidence.forall(e =>
        e.ref == ResolutionInput.evidenceFor(e.kind, e.payload) && e.sha256 == StableIds.sha256Hex(
          StrictJson.canonical(e.payload)
        )
      ),
      "live evidence hash mismatch"
    )
    require(
      request.features.map(_.name).distinct.size == request.features.size && request.features
        .forall(f =>
          f.value.isDefined != f.missingReason.isDefined && f.value.forall(
            _.isFinite
          ) && f.evidenceRefs.forall(request.evidence.map(_.ref).toSet)
        ),
      "invalid live request features"
    )
  }
  def request(
      candidate: DerivedPair,
      input: ResolutionInput,
      policy: ResolutionPolicy,
      source: ResolutionConfig,
      live: LiveProviderConfig,
      features: Vector[ResolutionFeature],
      evidence: Map[String, EvidenceRecord]
  ): Either[String, AdjudicationRequest] = Try {
    require(
      LiveResponseLimits.from(source) == live.responseLimits,
      "live response limits must bind actual source config limits"
    )
    val base = Adjudication
      .request(candidate, input, policy, source, features, evidence)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val raw = base.copy(
      requestHash = "",
      configHash = effectiveConfigHash(source, live),
      promptVersion = promptVersion,
      promptHash = StableIds.sha256Hex(prompt),
      responseSchemaHash = StableIds.sha256Hex(schemaText),
      provider = live.provider,
      model = live.model,
      modelVersion = live.modelVersion,
      generationSettings = Map(
        "reasoning.effort" -> live.reasoningEffort,
        "max_output_tokens" -> live.budget.maxOutputTokensPerCall.toString,
        "service_tier" -> "default",
        "store" -> "false"
      ),
      mode = "live"
    )
    val result = raw.copy(requestHash = StrictJson.hash(raw))
    liveRequestCheck(result, live)
    result
  }.toEither.left.map(_.getMessage)
  def renderRequest(
      request: AdjudicationRequest,
      config: LiveProviderConfig
  ): Either[String, String] = Try {
    liveRequestCheck(request, config)
    val body = ujson.Obj(
      "model" -> config.model,
      "instructions" -> prompt,
      "input" -> write(request),
      "reasoning" -> ujson.Obj("effort" -> config.reasoningEffort),
      "max_output_tokens" -> config.budget.maxOutputTokensPerCall,
      "store" -> false,
      "stream" -> false,
      "service_tier" -> "default",
      "truncation" -> "disabled",
      "tools" -> ujson.Arr(),
      "text" -> ujson.Obj(
        "format" -> ujson.Obj(
          "type" -> "json_schema",
          "name" -> "scholarchain_adjudication",
          "strict" -> true,
          "schema" -> ujson.read(schemaText)
        )
      )
    )
    val text = body.render()
    require(
      text.getBytes(UTF_8).length <= config.budget.maxRequestBytes,
      "wire request exceeds byte bound"
    )
    text
  }.toEither.left.map(_.getMessage)
  private def json(http: ProviderHttpResponse): ujson.Value = {
    require(http.status >= 200 && http.status < 300, "PROVIDER_HTTP_" + http.status)
    StrictJson
      .parse[ujson.Value](http.body)
      .fold(_ => throw new IllegalArgumentException("PROVIDER_INVALID_JSON"), identity)
  }
  private def number(v: ujson.Value, name: String): Long = {
    val n = v(name).num
    require(
      n.isFinite && n >= 0 && n <= 9007199254740991L.toDouble && n == math.floor(n),
      "PROVIDER_INVALID_USAGE"
    )
    n.toLong
  }
  def usage(http: ProviderHttpResponse): Either[String, ProviderUsage] = Try {
    val u = json(http)("usage")
    val in = number(u, "input_tokens"); val out = number(u, "output_tokens");
    val total = number(u, "total_tokens")
    val cached = number(u("input_tokens_details"), "cached_tokens")
    val writes = u("input_tokens_details").obj
      .get("cache_write_tokens")
      .map(_ => number(u("input_tokens_details"), "cache_write_tokens"))
      .getOrElse(0L)
    val reasoning = number(u("output_tokens_details"), "reasoning_tokens")
    require(
      total == in + out && cached <= in && writes <= in && cached + writes <= in && reasoning <= out,
      "PROVIDER_INVALID_USAGE"
    )
    ProviderUsage(in, out, total, reasoning, cached, writes)
  }.toEither.left.map(_ => "PROVIDER_USAGE_UNAVAILABLE_OR_INVALID")
  def parseResponse(
      http: ProviderHttpResponse,
      request: AdjudicationRequest,
      config: LiveProviderConfig
  ): Either[String, ProviderResult] = Try {
    liveRequestCheck(request, config)
    require(
      http.body.getBytes(UTF_8).length <= config.budget.maxResponseBytes,
      "PROVIDER_RESPONSE_BYTE_BOUND"
    )
    val root = json(http)
    require(
      root("status").str == "completed" && root.obj.get("error").forall(_ == ujson.Null) && root.obj
        .get("incomplete_details")
        .forall(_ == ujson.Null),
      "PROVIDER_INCOMPLETE_OR_FAILED"
    )
    val model = root("model").str
    require(
      model == config.model || (model.startsWith(config.model + "-") && model.matches(
        "[A-Za-z0-9._-]{1,128}"
      )),
      "PROVIDER_MODEL_MISMATCH"
    )
    val id = root("id").str
    require(id.matches("resp_[A-Za-z0-9_-]{1,200}"), "PROVIDER_RESPONSE_ID_INVALID")
    val messages = root("output").arr.toVector.filter { item =>
      val kind = item("type").str
      require(Set("message", "reasoning")(kind), "PROVIDER_UNEXPECTED_TOOL_OR_OUTPUT")
      kind == "message"
    }
    require(
      messages.size == 1 && messages.head.obj.get("role").forall(_ == ujson.Str("assistant")),
      "PROVIDER_MESSAGE_INVALID"
    )
    val content = messages.head("content").arr.toVector
    require(!content.exists(v => v("type").str == "refusal"), "PROVIDER_REFUSAL")
    require(
      content.size == 1 && content.head("type").str == "output_text",
      "PROVIDER_OUTPUT_INVALID"
    )
    val text = content.head("text").str
    val source = ResolutionConfig.example
    val bounds = source.copy(adjudication =
      source.adjudication.copy(
        maxResponseBytes = config.budget.maxResponseBytes,
        maxRationaleCharacters = config.responseLimits.maxRationaleCharacters,
        maxReasonCodes = config.responseLimits.maxReasonCodes,
        maxFieldRefs = config.responseLimits.maxFieldRefs
      )
    )
    val result = Adjudication
      .validateResponse(text, request, bounds)
      .fold(
        e =>
          throw new IllegalArgumentException(
            "PROVIDER_ADJUDICATION_" + Adjudication.safeResponseFailureCode(e)
          ),
        identity
      )
    val observed = usage(http).fold(e => throw new IllegalArgumentException(e), identity)
    ProviderResult(
      result,
      observed,
      id,
      model,
      http.requestId.filter(_.matches("[A-Za-z0-9_.:-]{1,128}"))
    )
  }.toEither.left.map(e => {
    val message = Option(e.getMessage).getOrElse("").stripPrefix("requirement failed: ")
    if (message.startsWith("PROVIDER_") && message.matches("[A-Z_0-9]+")) message
    else "PROVIDER_RESPONSE_INVALID"
  })

  /** Diagnose a rejected response without retaining output, rationale, refs, error bodies or
    * arbitrary exception text. Extraction only considers a bounded successful completed envelope.
    */
  def responseDiagnostic(
      http: ProviderHttpResponse,
      request: AdjudicationRequest,
      config: LiveProviderConfig
  ): ProviderResponseDiagnostic = {
    val bytes = http.body.getBytes(UTF_8)
    val validationCode =
      parseResponse(http, request, config).fold(identity, _ => "PROVIDER_RESPONSE_VALID")
    val text =
      if (bytes.length <= config.budget.maxResponseBytes && http.status >= 200 && http.status < 300)
        Try {
          val root = json(http)
          require(
            root("status").str == "completed" && root.obj
              .get("error")
              .forall(_ == ujson.Null) && root.obj.get("incomplete_details").forall(_ == ujson.Null)
          )
          val items = root("output").arr.toVector
          require(items.forall(v => Set("message", "reasoning")(v("type").str)))
          val messages = items.filter(_("type").str == "message")
          require(
            messages.size == 1 && messages.head.obj.get("role").forall(_ == ujson.Str("assistant"))
          )
          val content = messages.head("content").arr.toVector
          require(content.size == 1 && content.head("type").str == "output_text")
          content.head("text").str
        }.toOption
      else None
    val model = text.flatMap(t => StrictJson.parse[ujson.Value](t).toOption).collect {
      case o: ujson.Obj => o
    }
    val expected = Map(
      "schemaVersion" -> Adjudication.responseSchema,
      "requestHash" -> request.requestHash,
      "pairId" -> request.pairId,
      "sourceId" -> request.sourceId,
      "targetId" -> request.targetId,
      "inputEvidenceHash" -> request.inputEvidenceHash,
      "policyHash" -> request.policyHash
    )
    def count(field: String): Option[Int] =
      model.flatMap(_.obj.get(field)).collect { case a: ujson.Arr => a.value.size }
    ProviderResponseDiagnostic(
      "scholarchain.provider-response-diagnostic.v1",
      validationCode,
      bytes.length,
      StableIds.sha256Hex(http.body),
      text.map(_.getBytes(UTF_8).length),
      text.map(StableIds.sha256Hex),
      model
        .map(o =>
          expected.map((field, value) => field -> o.obj.get(field).contains(ujson.Str(value)))
        )
        .getOrElse(Map.empty),
      model.flatMap(_.obj.get("outcome")).collect {
        case ujson.Str(value) if Set("accept", "reject", "abstain")(value) => value
      },
      count("evidenceRefs"),
      count("fieldRefs"),
      count("reasonCodes"),
      model.flatMap(_.obj.get("rationale")).collect { case ujson.Str(value) => value.length }
    )
  }
}
