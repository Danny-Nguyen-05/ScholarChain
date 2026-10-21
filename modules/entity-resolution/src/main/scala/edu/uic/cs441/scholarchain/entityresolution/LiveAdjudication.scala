package edu.uic.cs441.scholarchain.entityresolution

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardCopyOption, StandardOpenOption}
import java.util.UUID
import java.util.concurrent.{Callable, Executors, ThreadFactory, TimeUnit}
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class CachedLiveAdjudication(
    schemaVersion: String,
    cacheKey: String,
    request: AdjudicationRequest,
    result: ProviderResult,
    resultHash: String
) derives ReadWriter
object LiveAdjudicationCache {
  def key(request: AdjudicationRequest): String = StrictJson.hash(request)
  private def safe(path: Path): Unit = {
    var p = path.toAbsolutePath.normalize
    while (p != null) {
      require(!Files.isSymbolicLink(p), "symlink in live cache path"); p = p.getParent
    }
  }
  private def location(root: Path, request: AdjudicationRequest): Path = {
    require(
      request.mode == "live" && request.provider == "openai" && request.model == "gpt-6-luna",
      "live cache rejects fake or other provider requests"
    )
    root.resolve("live").resolve("openai").resolve("gpt-6-luna").resolve(key(request) + ".json")
  }
  private def validate(
      result: ProviderResult,
      request: AdjudicationRequest,
      config: LiveProviderConfig
  ): Unit = {
    val usage = result.usage
    require(
      Vector(
        usage.inputTokens,
        usage.outputTokens,
        usage.totalTokens,
        usage.cachedInputTokens,
        usage.cacheWriteTokens,
        usage.reasoningTokens
      ).forall(n => n >= 0L && n <= 9007199254740991L),
      "cached provider usage exceeds the exact JSON numeric range"
    )
    val envelope = ujson.Obj(
      "id" -> result.responseId,
      "model" -> result.resolvedModel,
      "status" -> "completed",
      "output" -> ujson.Arr(
        ujson.Obj(
          "type" -> "message",
          "role" -> "assistant",
          "content" -> ujson.Arr(
            ujson.Obj("type" -> "output_text", "text" -> upickle.default.write(result.response))
          )
        )
      ),
      "usage" -> ujson.Obj(
        "input_tokens" -> usage.inputTokens.toDouble,
        "output_tokens" -> usage.outputTokens.toDouble,
        "total_tokens" -> usage.totalTokens.toDouble,
        "input_tokens_details" -> ujson.Obj(
          "cached_tokens" -> usage.cachedInputTokens.toDouble,
          "cache_write_tokens" -> usage.cacheWriteTokens.toDouble
        ),
        "output_tokens_details" -> ujson.Obj("reasoning_tokens" -> usage.reasoningTokens.toDouble)
      )
    )
    val replay = OpenAIResponses
      .parseResponse(
        ProviderHttpResponse(200, envelope.render(), result.requestId),
        request,
        config
      )
      .fold(e => throw new IllegalArgumentException(e), identity)
    require(replay == result, "cached live provenance differs from validated result")
  }
  def read(
      root: Path,
      request: AdjudicationRequest,
      config: LiveProviderConfig
  ): Either[String, Option[ProviderResult]] = Try {
    val path = location(root, request); safe(path)
    if (!Files.exists(path)) None
    else {
      val c = StrictJson
        .file(path, config.budget.maxRequestBytes.toLong + config.budget.maxResponseBytes + 65536)
        .flatMap(StrictJson.parse[CachedLiveAdjudication])
        .fold(e => throw new IllegalArgumentException(e), identity)
      require(
        c.schemaVersion == "scholarchain.live-cache.v1" && c.cacheKey == key(
          request
        ) && c.request == request && c.resultHash == StrictJson.hash(c.result),
        "live cache identity/hash mismatch"
      )
      validate(c.result, request, config)
      Some(c.result)
    }
  }.toEither.left.map(_ => "LIVE_CACHE_INVALID")
  def write(
      root: Path,
      request: AdjudicationRequest,
      result: ProviderResult,
      config: LiveProviderConfig
  ): Either[String, Unit] = Try {
    val path = location(root, request); safe(path); validate(result, request, config)
    Files.createDirectories(path.getParent)
    if (Files.exists(path))
      require(
        read(root, request, config).contains(Some(result)),
        "existing live cache entry differs"
      )
    else {
      val temp = path.resolveSibling(path.getFileName.toString + ".partial-" + UUID.randomUUID())
      Files.writeString(
        temp,
        upickle.default.write(
          CachedLiveAdjudication(
            "scholarchain.live-cache.v1",
            key(request),
            request,
            result,
            StrictJson.hash(result)
          )
        ) + "\n",
        UTF_8,
        StandardOpenOption.CREATE_NEW
      )
      Files.move(temp, path, StandardCopyOption.ATOMIC_MOVE)
    }
    ()
  }.toEither.left.map(_ => "LIVE_CACHE_WRITE_FAILED")
}

/** Calls are explicit and sequential; each attempted dispatch has already reserved a durable
  * budget.
  */
final class LiveAdjudicator(
    config: LiveProviderConfig,
    transport: OpenAITransport,
    ledger: LiveBudgetLedger,
    cache: Option[Path]
) {
  LiveProviderConfig
    .validate(config, requireApproval = true)
    .fold(e => throw new IllegalArgumentException(e), identity)
  require(ledger.snapshot.configHash == config.fingerprint, "live ledger/config mismatch")
  def adjudicate(request: AdjudicationRequest): LiveAttemptTrace = synchronized {
    val wire = OpenAIResponses.renderRequest(request, config) match {
      case Left(_) =>
        return LiveAttemptTrace(
          request.pairId,
          "REQUEST_INVALID",
          0,
          false,
          request,
          None,
          Some("LIVE_REQUEST_INVALID")
        )
      case Right(text) => text
    }
    cache.map(LiveAdjudicationCache.read(_, request, config)).getOrElse(Right(None)) match {
      case Left(_) =>
        return LiveAttemptTrace(
          request.pairId,
          "CACHE_INVALID",
          0,
          false,
          request,
          None,
          Some("LIVE_CACHE_INVALID")
        )
      case Right(Some(result)) =>
        return LiveAttemptTrace(request.pairId, "CACHE_HIT", 0, true, request, Some(result), None)
      case _ => ()
    }
    val wireBytes = wire.getBytes(UTF_8).length
    if (ledger.checkReservation(wireBytes).isLeft)
      return LiveAttemptTrace(
        request.pairId,
        "BUDGET_EXHAUSTED",
        0,
        false,
        request,
        None,
        Some("LIVE_BUDGET_EXHAUSTED")
      )
    val prepared = Try(transport.prepare()).toEither match {
      case Right(Right(value)) if value != null => value
      case _ =>
        return LiveAttemptTrace(
          request.pairId,
          "CREDENTIAL_INVALID",
          0,
          false,
          request,
          None,
          Some("LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID")
        )
    }
    var localAttempts = 0
    var error = "PROVIDER_FAILED"
    while (localAttempts <= config.budget.maxRetries) {
      val reservation = ledger.reserve(wireBytes) match {
        case Left(_) =>
          return LiveAttemptTrace(
            request.pairId,
            "BUDGET_EXHAUSTED",
            localAttempts,
            false,
            request,
            None,
            Some("LIVE_BUDGET_EXHAUSTED")
          )
        case Right(value) => value
      }
      localAttempts += 1
      val executor = Executors.newSingleThreadExecutor(new ThreadFactory {
        def newThread(r: Runnable): Thread = {
          val t = new Thread(r, "scholarchain-openai-live"); t.setDaemon(true); t
        }
      })
      val task = executor.submit(new Callable[ProviderHttpResponse] {
        def call(): ProviderHttpResponse =
          prepared.post(wire, config.budget.timeoutMs, config.budget.maxResponseBytes)
      })
      var terminated = true
      val response =
        try Right(task.get(config.budget.timeoutMs.toLong, TimeUnit.MILLISECONDS))
        catch {
          case _: Exception => task.cancel(true); Left("PROVIDER_TRANSPORT_FAILED_OR_TIMED_OUT")
        } finally {
          executor.shutdownNow()
          terminated = executor.awaitTermination(
            math.min(config.budget.timeoutMs.toLong, 1000L),
            TimeUnit.MILLISECONDS
          )
        }
      if (!terminated) {
        ledger.fuse();
        return LiveAttemptTrace(
          request.pairId,
          "ADAPTER_NOT_TERMINATED",
          localAttempts,
          false,
          request,
          None,
          Some("PROVIDER_ADAPTER_DID_NOT_TERMINATE")
        )
      }
      response match {
        case Left(message) =>
          ledger.fuse();
          return LiveAttemptTrace(
            request.pairId,
            "TRANSPORT_FAILED",
            localAttempts,
            false,
            request,
            None,
            Some(message)
          )
        case Right(http) =>
          OpenAIResponses.usage(http).foreach(ledger.observe(_, reservation._1, reservation._2))
          if (ledger.snapshot.fused)
            return LiveAttemptTrace(
              request.pairId,
              "USAGE_RESERVATION_EXCEEDED",
              localAttempts,
              false,
              request,
              None,
              Some("OBSERVED_USAGE_EXCEEDED_RESERVATION")
            )
          OpenAIResponses.parseResponse(http, request, config) match {
            case Right(result) =>
              val stored = cache
                .map(LiveAdjudicationCache.write(_, request, result, config))
                .getOrElse(Right(()))
              return LiveAttemptTrace(
                request.pairId,
                if (stored.isRight) "VALIDATED_LIVE" else "CACHE_WRITE_FAILED",
                localAttempts,
                false,
                request,
                Some(result),
                stored.left.toOption
              )
            case Left(message) =>
              error = message
              if (http.status < 500 && http.status != 429)
                return LiveAttemptTrace(
                  request.pairId,
                  "ADJUDICATION_FAILED",
                  localAttempts,
                  false,
                  request,
                  None,
                  Some(message),
                  Try(OpenAIResponses.responseDiagnostic(http, request, config)).toOption
                )
          }
      }
    }
    LiveAttemptTrace(
      request.pairId,
      "ADJUDICATION_FAILED",
      localAttempts,
      false,
      request,
      None,
      Some(error)
    )
  }
}
