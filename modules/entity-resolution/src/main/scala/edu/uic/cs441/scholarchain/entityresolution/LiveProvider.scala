package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class LiveBudget(
    maxAttempts: Int,
    maxInputTokens: Long,
    maxOutputTokens: Long,
    maxSpendMicrousd: Long,
    maxOutputTokensPerCall: Int,
    timeoutMs: Int,
    maxRetries: Int,
    maxConcurrentCalls: Int,
    maxRequestBytes: Int,
    maxResponseBytes: Int
) derives ReadWriter
final case class LiveRateCard(
    inputMicrousdPerMillionTokens: Long,
    cachedInputMicrousdPerMillionTokens: Long,
    cacheWriteMicrousdPerMillionTokens: Long,
    outputMicrousdPerMillionTokens: Long,
    checkedAtUtc: String,
    sourceUrl: String
) derives ReadWriter
final case class LiveResponseLimits(
    maxRationaleCharacters: Int,
    maxReasonCodes: Int,
    maxFieldRefs: Int
) derives ReadWriter
object LiveResponseLimits {
  def from(config: ResolutionConfig): LiveResponseLimits = LiveResponseLimits(
    config.adjudication.maxRationaleCharacters,
    config.adjudication.maxReasonCodes,
    config.adjudication.maxFieldRefs
  )
}
@upickle.implicits.serializeDefaults(true)
final case class LiveProviderConfig(
    schemaVersion: String,
    provider: String,
    model: String,
    modelVersion: String,
    reasoningEffort: String,
    apiKeyEnvironment: String,
    approved: Boolean,
    approvalId: String,
    budget: LiveBudget,
    rateCard: LiveRateCard,
    responseLimits: LiveResponseLimits = LiveResponseLimits(1000, 8, 16)
) derives ReadWriter {
  def fingerprint: String = StrictJson.hash(this)
}
object LiveProviderConfig {
  val schema = "scholarchain.live-provider.v1"
  def validate(
      c: LiveProviderConfig,
      requireApproval: Boolean = false
  ): Either[String, LiveProviderConfig] = Try {
    require(
      c.schemaVersion == schema && c.provider == "openai" && c.model == "gpt-6-luna" && c.modelVersion == "gpt-6-luna",
      "only explicitly selected OpenAI gpt-6-luna is supported; no fallback or invented snapshot"
    )
    require(
      Set("none", "low", "medium", "high", "xhigh", "max")(c.reasoningEffort),
      "unsupported reasoning effort"
    )
    require(
      c.apiKeyEnvironment == "OPENAI_API_KEY",
      "only named runtime OPENAI_API_KEY credential is supported"
    )
    require(
      c.approvalId.matches("[A-Za-z0-9_-]{1,128}") && (!requireApproval || c.approved),
      "explicit numerical live budget approval required"
    )
    require(
      c.responseLimits.maxRationaleCharacters > 0 && c.responseLimits.maxRationaleCharacters <= 10000 && c.responseLimits.maxReasonCodes > 0 && c.responseLimits.maxReasonCodes <= 32 && c.responseLimits.maxFieldRefs > 0 && c.responseLimits.maxFieldRefs <= 128,
      "invalid explicit live response limits"
    )
    val b = c.budget
    require(
      b.maxAttempts >= 0 && b.maxAttempts <= 100 && b.maxInputTokens >= 0 && b.maxOutputTokens >= 0 && b.maxSpendMicrousd >= 0 && b.maxSpendMicrousd <= 100000000L,
      "invalid bounded live allowances"
    )
    require(
      b.maxOutputTokensPerCall > 0 && b.maxOutputTokensPerCall <= 16384 && b.timeoutMs >= 100 && b.timeoutMs <= 120000 && b.maxRetries >= 0 && b.maxRetries <= 2 && b.maxConcurrentCalls == 1,
      "invalid per-call bound; live calls must be sequential"
    )
    require(
      b.maxRequestBytes > 0 && b.maxRequestBytes <= 65536 && b.maxResponseBytes > 0 && b.maxResponseBytes <= 1048576,
      "invalid request/response byte bound"
    )
    val r = c.rateCard
    require(
      r.inputMicrousdPerMillionTokens == 100000L && r.cachedInputMicrousdPerMillionTokens == 10000L && r.cacheWriteMicrousdPerMillionTokens == 125000L && r.outputMicrousdPerMillionTokens == 500000L,
      "rate card must match verified short-context standard GPT-6 Luna prices"
    )
    GoldLabels.utc(r.checkedAtUtc)
    require(
      r.sourceUrl == "https://developers.openai.com/api/docs/models/gpt-6-luna",
      "official rate-card source required"
    )
    c
  }.toEither.left.map(_.getMessage)
  def load(path: Path): Either[String, LiveProviderConfig] = StrictJson
    .file(path, 1048576)
    .flatMap(StrictJson.parse[LiveProviderConfig])
    .flatMap(validate(_))
}
final case class ProviderHttpResponse(status: Int, body: String, requestId: Option[String])
    derives ReadWriter
trait OpenAITransport {
  def prepare(): Either[String, OpenAITransport] = Right(this)
  def post(requestBody: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse
}
final case class ProviderUsage(
    inputTokens: Long,
    outputTokens: Long,
    totalTokens: Long,
    reasoningTokens: Long,
    cachedInputTokens: Long,
    cacheWriteTokens: Long
) derives ReadWriter
final case class ProviderResult(
    response: AdjudicationResponse,
    usage: ProviderUsage,
    responseId: String,
    resolvedModel: String,
    requestId: Option[String]
) derives ReadWriter
final case class LiveAttemptTrace(
    pairId: String,
    status: String,
    attempts: Int,
    cacheHit: Boolean,
    request: AdjudicationRequest,
    result: Option[ProviderResult],
    error: Option[String]
) derives ReadWriter
final case class LiveBudgetState(
    schemaVersion: String,
    approvalId: String,
    configHash: String,
    attempts: Int,
    reservedInputTokens: Long,
    reservedOutputTokens: Long,
    reservedSpendMicrousd: Long,
    observedInputTokens: Long,
    observedOutputTokens: Long,
    observedReasoningTokens: Long,
    observedCachedInputTokens: Long,
    observedCacheWriteTokens: Long,
    observedCostUpperBoundMicrousd: Long,
    unknownUsageAttempts: Int,
    fused: Boolean
) derives ReadWriter

/** Persistent approval-scoped ledger. Reservations are never refunded after uncertain failures. */
final class LiveBudgetLedger(config: LiveProviderConfig, path: Path) extends AutoCloseable {
  LiveProviderConfig
    .validate(config, requireApproval = true)
    .fold(e => throw new IllegalArgumentException(e), identity)
  private val absolute = path.toAbsolutePath.normalize
  private var ancestor = absolute.getParent
  while (ancestor != null) {
    require(!Files.isSymbolicLink(ancestor), "symlink in budget ledger path");
    ancestor = ancestor.getParent
  }
  require(
    !Files.isSymbolicLink(absolute) && !Files.isSymbolicLink(
      absolute.resolveSibling(absolute.getFileName.toString + ".lock")
    ),
    "symlink in budget ledger or lock"
  )
  Files.createDirectories(absolute.getParent)
  private val lockChannel = java.nio.channels.FileChannel.open(
    absolute.resolveSibling(absolute.getFileName.toString + ".lock"),
    StandardOpenOption.CREATE,
    StandardOpenOption.WRITE
  )
  private val lock =
    try {
      Option(lockChannel.tryLock()).getOrElse(
        throw new IllegalArgumentException("live budget is already locked by another process")
      )
    } catch {
      case e: Exception =>
        lockChannel.close();
        throw new IllegalArgumentException("live budget is already locked or unavailable")
    }
  private var closed = false
  def close(): Unit = synchronized {
    if (!closed) { closed = true; lock.release(); lockChannel.close() }
  }
  private def cost(input: Long, output: Long): Long = {
    val inputRate = math.max(
      config.rateCard.inputMicrousdPerMillionTokens,
      config.rateCard.cacheWriteMicrousdPerMillionTokens
    )
    ((BigInt(input) * inputRate + BigInt(
      output
    ) * config.rateCard.outputMicrousdPerMillionTokens + 999999) / 1000000).toLong
  }
  private val empty = LiveBudgetState(
    "scholarchain.live-budget.v1",
    config.approvalId,
    config.fingerprint,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    false
  )
  private var state =
    try {
      if (Files.exists(path)) {
        val s = StrictJson
          .file(path, 1048576)
          .flatMap(StrictJson.parse[LiveBudgetState])
          .fold(e => throw new IllegalArgumentException(e), identity)
        require(
          s.schemaVersion == empty.schemaVersion && s.approvalId == config.approvalId && s.configHash == config.fingerprint,
          "budget ledger approval/config mismatch"
        )
        require(
          s.attempts >= 0 && s.attempts <= config.budget.maxAttempts && s.reservedInputTokens >= 0 && s.reservedInputTokens <= config.budget.maxInputTokens && s.reservedOutputTokens >= 0 && s.reservedOutputTokens <= config.budget.maxOutputTokens && s.reservedSpendMicrousd >= 0 && s.reservedSpendMicrousd <= config.budget.maxSpendMicrousd && s.unknownUsageAttempts >= 0 && s.unknownUsageAttempts <= s.attempts,
          "invalid budget ledger"
        )
        require(
          Vector(
            s.observedInputTokens,
            s.observedOutputTokens,
            s.observedReasoningTokens,
            s.observedCachedInputTokens,
            s.observedCacheWriteTokens,
            s.observedCostUpperBoundMicrousd
          ).forall(_ >= 0),
          "invalid observed budget usage"
        )
        s
      } else empty
    } catch { case e: Exception => close(); throw e }
  private def save(): Unit = {
    val absolute = path.toAbsolutePath.normalize
    var parent = absolute.getParent
    while (parent != null) {
      require(!Files.isSymbolicLink(parent), "symlink in budget ledger path");
      parent = parent.getParent
    }
    Files.createDirectories(absolute.getParent)
    val partial = absolute.resolveSibling(
      absolute.getFileName.toString + ".partial-" + java.util.UUID.randomUUID()
    )
    Files.writeString(partial, write(state) + "\n", UTF_8, StandardOpenOption.CREATE_NEW)
    Files.move(
      partial,
      absolute,
      java.nio.file.StandardCopyOption.REPLACE_EXISTING,
      java.nio.file.StandardCopyOption.ATOMIC_MOVE
    )
  }
  def snapshot: LiveBudgetState = synchronized(state)
  private def reservation(wireBytes: Int): (Long, Long, Long) = {
    require(
      !closed && wireBytes > 0 && wireBytes <= config.budget.maxRequestBytes,
      "wire request exceeds byte bound"
    )
    // UTF-8 wire bytes plus fixed framing allowance are conservative reservations, not measured usage.
    val input = wireBytes.toLong + 4096L; val output = config.budget.maxOutputTokensPerCall.toLong
    val dollars = cost(input, output); val b = config.budget
    require(
      !state.fused && state.attempts < b.maxAttempts && state.reservedInputTokens + input <= b.maxInputTokens && state.reservedOutputTokens + output <= b.maxOutputTokens && state.reservedSpendMicrousd + dollars <= b.maxSpendMicrousd,
      "LIVE_BUDGET_EXHAUSTED"
    )
    (input, output, dollars)
  }
  def checkReservation(wireBytes: Int): Either[String, Unit] = synchronized {
    Try { reservation(wireBytes); () }.toEither.left.map(_.getMessage)
  }
  def reserve(wireBytes: Int): Either[String, (Long, Long)] = synchronized {
    Try {
      val (input, output, dollars) = reservation(wireBytes)
      state = state.copy(
        attempts = state.attempts + 1,
        reservedInputTokens = state.reservedInputTokens + input,
        reservedOutputTokens = state.reservedOutputTokens + output,
        reservedSpendMicrousd = state.reservedSpendMicrousd + dollars,
        unknownUsageAttempts = state.unknownUsageAttempts + 1
      )
      save(); input -> output
    }.toEither.left.map(_.getMessage)
  }
  def observe(usage: ProviderUsage, inputReservation: Long, outputReservation: Long): Unit =
    synchronized {
      val over = usage.inputTokens > inputReservation || usage.outputTokens > outputReservation
      state = state.copy(
        observedInputTokens = state.observedInputTokens + usage.inputTokens,
        observedOutputTokens = state.observedOutputTokens + usage.outputTokens,
        observedReasoningTokens = state.observedReasoningTokens + usage.reasoningTokens,
        observedCachedInputTokens = state.observedCachedInputTokens + usage.cachedInputTokens,
        observedCacheWriteTokens = state.observedCacheWriteTokens + usage.cacheWriteTokens,
        observedCostUpperBoundMicrousd =
          state.observedCostUpperBoundMicrousd + cost(usage.inputTokens, usage.outputTokens),
        unknownUsageAttempts = state.unknownUsageAttempts - 1,
        fused = state.fused || over
      )
      save()
    }
  def fuse(): Unit = synchronized { state = state.copy(fused = true); save() }
}
