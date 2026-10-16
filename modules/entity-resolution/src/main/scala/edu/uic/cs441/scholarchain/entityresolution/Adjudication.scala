package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{Callable, Executors, ThreadFactory, TimeUnit, TimeoutException}
import scala.util.Try
import upickle.default.{ReadWriter, write, writeJs}

final case class AdjudicationRequest(
    schemaVersion: String,
    requestHash: String,
    pairId: String,
    entityType: ResolutionEntityType,
    sourceId: String,
    targetId: String,
    inputEvidenceHash: String,
    policyHash: String,
    configHash: String,
    promptVersion: String,
    promptHash: String,
    responseSchemaVersion: String,
    responseSchemaHash: String,
    provider: String,
    model: String,
    modelVersion: String,
    generationSettings: Map[String, String],
    mode: String,
    evidence: Vector[EvidenceRecord],
    features: Vector[ResolutionFeature],
    identifiers: Vector[IdentifierEvidence]
) derives ReadWriter
final case class AdjudicationResponse(
    schemaVersion: String,
    requestHash: String,
    pairId: String,
    sourceId: String,
    targetId: String,
    inputEvidenceHash: String,
    policyHash: String,
    outcome: String,
    reasonCodes: Vector[String],
    evidenceRefs: Vector[String],
    rationale: String,
    reportedConfidence: Double,
    fieldRefs: Vector[String]
) derives ReadWriter
final case class AdjudicationTrace(
    pairId: String,
    status: String,
    attempts: Int,
    cacheHit: Boolean,
    request: Option[AdjudicationRequest],
    response: Option[AdjudicationResponse],
    error: Option[String]
) derives ReadWriter

/** No network implementation is supplied or selectable in 5B. Tests inject bounded fake adapters.
  */
trait AdjudicationAdapter {
  def provider: String
  def model: String
  def modelVersion: String
  def respond(request: AdjudicationRequest): String
}
final class DeterministicFakeAdapter(val model: String, val modelVersion: String)
    extends AdjudicationAdapter {
  val provider = "deterministic-fake"
  var calls: Int = 0
  def respond(request: AdjudicationRequest): String = {
    calls += 1
    write(
      AdjudicationResponse(
        Adjudication.responseSchema,
        request.requestHash,
        request.pairId,
        request.sourceId,
        request.targetId,
        request.inputEvidenceHash,
        request.policyHash,
        "abstain",
        Vector("INSUFFICIENT_EVIDENCE"),
        Vector.empty,
        "Deterministic fake fixture abstains; no model ran.",
        0.0,
        Vector.empty
      )
    )
  }
}
object Adjudication {
  val requestSchema = "scholarchain.adjudication-request.v1"
  val responseSchema = "scholarchain.adjudication-response.v1"
  val promptVersion = "er-adjudication-offline-v1"
  def prompt: String = ResourceText.read("adjudication/prompt.v1.txt")
  def schemaText: String = ResourceText.read("adjudication/response.schema.v1.json")
  def validateRequest(
      request: AdjudicationRequest,
      config: ResolutionConfig
  ): Either[String, AdjudicationRequest] = Try {
    ResolutionConfig.validate(config).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      request.schemaVersion == requestSchema && request.mode == "fake",
      "unsupported request schema or mode"
    )
    require(
      request.requestHash == StrictJson.hash(request.copy(requestHash = "")),
      "request hash mismatch"
    )
    require(
      request.configHash == config.fingerprint && request.provider == config.adjudication.provider && request.model == config.adjudication.model && request.modelVersion == config.adjudication.modelVersion && request.generationSettings == config.adjudication.generationSettings,
      "request effective config/provider mismatch"
    )
    require(
      request.promptVersion == promptVersion && request.promptHash == StableIds.sha256Hex(
        prompt
      ) && request.responseSchemaVersion == responseSchema && request.responseSchemaHash == StableIds
        .sha256Hex(schemaText),
      "request prompt/schema mismatch"
    )
    require(
      request.pairId.matches("resolution-pair:[0-9a-f]{64}") && Vector(
        request.sourceId,
        request.targetId
      ).forall(
        _.matches("resolution-endpoint:[0-9a-f]{64}")
      ) && request.sourceId != request.targetId && Vector(
        request.inputEvidenceHash,
        request.policyHash
      ).forall(_.matches("[0-9a-f]{64}")),
      "invalid request IDs/hashes"
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
      "invalid request evidence hashes"
    )
    require(
      request.features.map(_.name).distinct.size == request.features.size && request.features
        .forall(f =>
          f.value.isDefined != f.missingReason.isDefined && f.value.forall(
            _.isFinite
          ) && f.evidenceRefs.forall(request.evidence.map(_.ref).toSet)
        ),
      "invalid request feature evidence"
    )
    require(
      write(request).getBytes(UTF_8).length.toLong + prompt
        .getBytes(UTF_8)
        .length <= config.adjudication.maxRequestBytes,
      "request byte bound exceeded"
    )
    request
  }.toEither.left.map(_.getMessage)
  def request(
      candidate: DerivedPair,
      input: ResolutionInput,
      policy: ResolutionPolicy,
      config: ResolutionConfig,
      features: Vector[ResolutionFeature],
      evidence: Map[String, EvidenceRecord]
  ): Either[String, AdjudicationRequest] = Try {
    val pair = candidate.pair
    val raw = AdjudicationRequest(
      requestSchema,
      "",
      pair.pairId,
      pair.entityType,
      ResolutionIds.endpointId(pair.left),
      ResolutionIds.endpointId(pair.right),
      input.inputEvidenceHash,
      policy.fingerprint,
      config.fingerprint,
      promptVersion,
      StableIds.sha256Hex(prompt),
      responseSchema,
      StableIds.sha256Hex(schemaText),
      config.adjudication.provider,
      config.adjudication.model,
      config.adjudication.modelVersion,
      config.adjudication.generationSettings,
      "fake",
      candidate.evidenceRefs.sorted.map(r =>
        evidence.getOrElse(r, throw new IllegalArgumentException("missing request evidence"))
      ),
      features,
      FeatureExtractor.identifiers(pair.left, input) ++ FeatureExtractor.identifiers(
        pair.right,
        input
      )
    )
    val req = raw.copy(requestHash = StrictJson.hash(raw))
    require(
      write(req)
        .getBytes(UTF_8)
        .length + prompt.getBytes(UTF_8).length <= config.adjudication.maxRequestBytes,
      "request byte bound exceeded"
    )
    req
  }.toEither.left.map(_.getMessage)
  def validateResponse(
      text: String,
      request: AdjudicationRequest,
      config: ResolutionConfig
  ): Either[String, AdjudicationResponse] =
    if (text.getBytes(UTF_8).length > config.adjudication.maxResponseBytes)
      Left("response byte bound exceeded")
    else
      StrictJson.parse[AdjudicationResponse](text).flatMap { r =>
        Try {
          require(
            r.schemaVersion == responseSchema && r.requestHash == request.requestHash && r.pairId == request.pairId && r.sourceId == request.sourceId && r.targetId == request.targetId && r.inputEvidenceHash == request.inputEvidenceHash && r.policyHash == request.policyHash,
            "response request identity mismatch"
          )
          require(Set("accept", "reject", "abstain")(r.outcome), "invalid response outcome")
          require(
            r.reasonCodes.nonEmpty && r.reasonCodes.distinct == r.reasonCodes && r.reasonCodes.size <= config.adjudication.maxReasonCodes && r.reasonCodes
              .forall(
                Set(
                  "SUPPORTED_SAME_IDENTITY",
                  "SUPPORTED_DIFFERENT_IDENTITY",
                  "INSUFFICIENT_EVIDENCE"
                )
              ),
            "invalid model reason codes"
          )
          val requiredReason = r.outcome match {
            case "accept"  => "SUPPORTED_SAME_IDENTITY"
            case "reject"  => "SUPPORTED_DIFFERENT_IDENTITY"
            case "abstain" => "INSUFFICIENT_EVIDENCE"
          }
          require(
            r.reasonCodes == Vector(requiredReason),
            "model reason codes contradict the selected outcome"
          )
          require(
            r.evidenceRefs.distinct == r.evidenceRefs && r.evidenceRefs.forall(
              request.evidence.map(_.ref).toSet
            ),
            "fabricated response evidence refs"
          )
          require(
            r.outcome == "abstain" || r.evidenceRefs.nonEmpty,
            "decisive response requires cited evidence"
          )
          require(
            r.fieldRefs.distinct == r.fieldRefs && r.fieldRefs.size <= config.adjudication.maxFieldRefs,
            "invalid cited field count"
          )
          require(
            r.outcome == "abstain" || r.fieldRefs.nonEmpty,
            "decisive response requires cited input fields"
          )
          r.fieldRefs.foreach { citation =>
            val parts = citation.split("#", -1)
            require(
              parts.length == 2 && parts(1).startsWith("/") && r.evidenceRefs.contains(parts(0)),
              "field citation must identify a cited evidence record and JSON pointer"
            )
            var value = request.evidence.find(_.ref == parts(0)).get.payload
            parts(1).drop(1).split("/", -1).foreach { raw =>
              require(!raw.matches(".*~(?![01]).*"), "invalid JSON pointer escape")
              val token = raw.replace("~1", "/").replace("~0", "~")
              value = value match {
                case o: ujson.Obj =>
                  o.value
                    .getOrElse(token, throw new IllegalArgumentException("fabricated input field"))
                case a: ujson.Arr =>
                  require(token.matches("0|[1-9][0-9]*"), "invalid input field array index");
                  val i = token.toInt;
                  require(i < a.value.size, "input field array index out of range"); a(i)
                case _ => throw new IllegalArgumentException("input field pointer traverses scalar")
              }
            }
            require(value != ujson.Null, "missing input field cannot be cited as evidence")
          }
          require(
            r.rationale.nonEmpty && r.rationale.length <= config.adjudication.maxRationaleCharacters && !r.rationale
              .exists(c => c < ' ' && c != '\n' && c != '\t'),
            "invalid rationale length/control characters"
          )
          require(
            r.reportedConfidence.isFinite && r.reportedConfidence >= 0 && r.reportedConfidence <= 1,
            "model confidence must be in [0,1]"
          )
          r
        }.toEither.left.map(_.getMessage)
      }
}

/** One per run. Budgets include failed attempts; disabled never invokes or consults an adapter. */
final class OfflineAdjudicator(
    config: ResolutionConfig,
    adapter: AdjudicationAdapter,
    cache: Option[java.nio.file.Path]
) {
  private var attempts = 0
  private var inputAllowance = 0L
  private var outputAllowance = 0L
  private var fused = false
  def calls: Int = attempts
  def adjudicate(request: AdjudicationRequest): AdjudicationTrace = {
    Adjudication.validateRequest(request, config) match {
      case Left(error) =>
        return AdjudicationTrace(
          request.pairId,
          "REQUEST_INVALID",
          0,
          false,
          Some(request),
          None,
          Some(error)
        )
      case Right(_) => ()
    }
    if (fused)
      return AdjudicationTrace(
        request.pairId,
        "ADAPTER_NOT_TERMINATED",
        0,
        false,
        Some(request),
        None,
        Some("prior adapter ignored cancellation; no further calls allowed")
      )
    if (
      adapter.provider != config.adjudication.provider || adapter.model != config.adjudication.model || adapter.modelVersion != config.adjudication.modelVersion
    )
      return AdjudicationTrace(
        request.pairId,
        "ADAPTER_CONFIG_MISMATCH",
        0,
        false,
        Some(request),
        None,
        Some("adapter identity differs from explicit config")
      )
    val cached =
      cache.map(dir => AdjudicationCache.read(dir, request, config)).getOrElse(Right(None))
    cached match {
      case Left(e) =>
        return AdjudicationTrace(
          request.pairId,
          "CACHE_INVALID",
          0,
          false,
          Some(request),
          None,
          Some(e)
        )
      case Right(Some(r)) =>
        return AdjudicationTrace(request.pairId, "CACHE_HIT", 0, true, Some(request), Some(r), None)
      case _ => ()
    }
    val requestBytes =
      write(request).getBytes(UTF_8).length + Adjudication.prompt.getBytes(UTF_8).length
    var lastError = "provider failure"; var localAttempts = 0
    while (localAttempts <= config.adjudication.maxRetries) {
      // UTF-8 byte counts are conservative token reservations, not measured usage.
      if (
        attempts >= config.adjudication.maxRequests || inputAllowance + requestBytes > config.adjudication.maxInputTokens || outputAllowance + config.adjudication.maxResponseBytes > config.adjudication.maxOutputTokens
      )
        return AdjudicationTrace(
          request.pairId,
          "BUDGET_EXHAUSTED",
          localAttempts,
          false,
          Some(request),
          None,
          Some("offline request/token reservation budget exhausted")
        )
      attempts += 1; localAttempts += 1; inputAllowance += requestBytes;
      outputAllowance += config.adjudication.maxResponseBytes
      val executor = Executors.newSingleThreadExecutor(new ThreadFactory {
        def newThread(r: Runnable): Thread = {
          val t = new Thread(r, "er-offline-fake"); t.setDaemon(true); t
        }
      })
      val task = executor.submit(new Callable[String] {
        def call(): String = adapter.respond(request)
      })
      var terminated = true
      val result =
        try
          Adjudication.validateResponse(
            task.get(config.adjudication.timeoutMs.toLong, TimeUnit.MILLISECONDS),
            request,
            config
          )
        catch {
          case _: TimeoutException => task.cancel(true); Left("ADAPTER_TIMEOUT")
          case e: Exception        => Left(Option(e.getMessage).getOrElse("ADAPTER_FAILURE"))
        } finally {
          executor.shutdownNow();
          terminated =
            executor.awaitTermination(config.adjudication.timeoutMs.toLong, TimeUnit.MILLISECONDS)
        }
      if (!terminated) {
        fused = true;
        return AdjudicationTrace(
          request.pairId,
          "ADAPTER_NOT_TERMINATED",
          localAttempts,
          false,
          Some(request),
          None,
          Some("adapter ignored cancellation; retries and subsequent calls disabled")
        )
      }
      result match {
        case Right(response) =>
          val cacheResult = cache
            .map(dir => AdjudicationCache.write(dir, request, response, config))
            .getOrElse(Right(()))
          return AdjudicationTrace(
            request.pairId,
            if (cacheResult.isRight) "VALIDATED_FAKE" else "CACHE_WRITE_FAILED",
            localAttempts,
            false,
            Some(request),
            Some(response),
            cacheResult.left.toOption
          )
        case Left(error) => lastError = error
      }
    }
    AdjudicationTrace(
      request.pairId,
      "ADJUDICATION_FAILED",
      localAttempts,
      false,
      Some(request),
      None,
      Some(lastError)
    )
  }
}
