package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

final case class SynthesisProposal(
    claims: Vector[AnswerClaim],
    narrativeClaimIds: Vector[String],
    interpretation: String,
    uncertainty: String,
    usage: Vector[RuntimeModelUsage] = Vector.empty,
    /** Count of selectedClaimIds that named no claim of the request's scaffold; never a claim. */
    ignoredSelectedIds: Int = 0
)
enum SynthesisResult {
  case Proposed(proposal: SynthesisProposal)
  case Abstained(reason: String, usage: Vector[RuntimeModelUsage])
  case Failed(reason: String)
}

/** A model proposes fields only. Its prose, status and identity guesses never become facts. */
final class AnswerSynthesisAgent(
    llm: LlmClient,
    config: RuntimeConfig,
    assets: RuntimePromptAssets,
    clockNanos: () => Long = () => System.nanoTime()
) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  private val ScaffoldKeyOverheadBytes = 64
  def synthesize(plan: QueryPlan, bundle: EvidenceBundle): SynthesisResult = {
    if (DomainValidation.check(plan).isLeft) return SynthesisResult.Failed("invalid-runtime-plan")
    if (plan.question.getBytes(UTF_8).length > config.effectiveByteLimits.questionBytes)
      return SynthesisResult.Abstained("synthesis-question-bound", Vector.empty)
    if (
      assets.synthesisPrompt.getBytes(UTF_8).length > config.effectiveByteLimits.promptBytes ||
      assets.synthesisSchema
        .render()
        .getBytes(UTF_8)
        .length > config.effectiveByteLimits.promptBytes
    )
      return SynthesisResult.Abstained("synthesis-prompt-bound", Vector.empty)
    if (DomainValidation.check(bundle).isLeft)
      return SynthesisResult.Failed("invalid-evidence-bundle")
    val context = EvidenceContext.render(bundle)
    if (context.getBytes(UTF_8).length > config.retrieval.contextTokenBudget)
      return SynthesisResult.Abstained("synthesis-context-bound", Vector.empty)
    val base = ujson.Obj(
      "question" -> plan.question,
      "plan" -> upickle.default.writeJs(plan),
      "evidenceData" -> context
    )
    val fixedBytes = base.render().getBytes(UTF_8).length + assets.synthesisPrompt
      .getBytes(UTF_8)
      .length + assets.synthesisSchema.render().getBytes(UTF_8).length
    if (fixedBytes > config.effectiveByteLimits.requestBytes)
      return SynthesisResult.Abstained("synthesis-request-bound", Vector.empty)
    // The scaffold is bounded separately from the evidence context (same size as that budget) and
    // never by more than the room left in the request, so it cannot push a request over its limit.
    val scaffoldBudget = math.min(
      config.retrieval.contextTokenBudget,
      config.effectiveByteLimits.requestBytes - fixedBytes - ScaffoldKeyOverheadBytes
    )
    val scaffold = ClaimScaffold.build(plan, bundle, scaffoldBudget)
    base("claimScaffold") = ClaimScaffold.toJson(scaffold)
    val data = base.render()
    if (
      data.getBytes(UTF_8).length + assets.synthesisPrompt.getBytes(UTF_8).length +
        assets.synthesisSchema
          .render()
          .getBytes(UTF_8)
          .length > config.effectiveByteLimits.requestBytes
    )
      return SynthesisResult.Abstained("synthesis-request-bound", Vector.empty)
    val started = clockNanos()
    var usage = Vector.empty[RuntimeModelUsage]
    for (_ <- 0 to config.malformedRetries) {
      val remaining = config.deadlines.synthesisMs - (clockNanos() - started) / 1000000L
      if (remaining <= 0) return SynthesisResult.Abstained("synthesis-deadline", usage)
      val request = StructuredLlmRequest(
        "submit_answer",
        assets.synthesisPrompt,
        data,
        assets.synthesisSchema.render(),
        config.synthesisPromptVersion,
        config.synthesisSchemaVersion,
        remaining
      )
      val result =
        try llm.complete(request)
        catch {
          case _: InterruptedException =>
            Thread.currentThread().interrupt();
            return SynthesisResult.Failed("synthesis-interrupted")
          case NonFatal(_) => return SynthesisResult.Failed("synthesis-client-failure")
        }
      result match {
        case LlmResult.Failure(_) =>
          return SynthesisResult.Abstained("synthesis-unavailable", usage)
        case LlmResult.Output(json, tokens, model, version) =>
          usage :+= RuntimeModelUsage(
            model,
            version,
            config.synthesisPromptVersion,
            config.synthesisSchemaVersion,
            tokens.inputTokens,
            tokens.outputTokens,
            Some(config.model.region)
          )
          if (model != config.model.modelId || version != config.model.modelVersion)
            return SynthesisResult.Abstained("synthesis-model-mismatch", usage)
          if (json.getBytes(UTF_8).length <= config.effectiveByteLimits.outputBytes) {
            decode(json, plan, scaffold, usage) match {
              case Some(proposal) =>
                if ((clockNanos() - started) / 1000000L >= config.deadlines.synthesisMs)
                  return SynthesisResult.Abstained("synthesis-deadline", usage)
                return SynthesisResult.Proposed(proposal)
              case None => ()
            }
          }
      }
    }
    SynthesisResult.Abstained("synthesis-invalid-output", usage)
  }
  private def proposalClaim(
      plan: QueryPlan,
      claimId: String,
      evidenceIds: Vector[String],
      typed: TypedAnswerClaim
  ): AnswerClaim = AnswerClaim(
    claimId,
    SchemaVersions.domain,
    "Structured claim proposal.",
    evidenceIds,
    VerificationStatus.Unverified,
    Some("Unverified structured proposal."),
    plan.provenance,
    Some(typed)
  )

  /** Effective claims are the model's own claims plus the scaffold claims it selected by id. The
    * scaffold is the exact one sent in this request, and its version wins when a claim is both
    * copied and selected (an unselected copy is left for the verifier, so a tampered copy is
    * rejected). The verifier then checks the expanded claims unchanged.
    */
  private def decode(
      json: String,
      plan: QueryPlan,
      scaffold: Vector[ScaffoldClaim],
      usage: Vector[RuntimeModelUsage]
  ): Option[SynthesisProposal] = try {
    val tree = ujson.read(json)
    if (RuntimeJsonSchema.validate(assets.synthesisSchema, tree).isLeft) return None
    val byId = scaffold.map(c => c.claimId -> c).toMap
    val selected =
      tree.obj.get("selectedClaimIds").map(_.arr.toVector.map(_.str)).getOrElse(Vector.empty)
    val known = selected.filter(byId.contains)
    val unknown = selected.filterNot(byId.contains).toSet
    val own =
      tree("claims").arr.toVector.filterNot(c => known.contains(c("claimId").str)).map { c =>
        val typed = TypedAnswerClaim(
          upickle.default.read[RuntimeClaimType](c("claimType")),
          c("subjectIds").arr.toVector.map(_.str),
          upickle.default.read[Vector[RuntimeClaimValue]](c("values")),
          c("windowIds").arr.toVector.map(_.str),
          c("templateId").str
        )
        if (RuntimeContractValidation.claim(typed).nonEmpty) return None
        proposalClaim(plan, c("claimId").str, c("evidenceIds").arr.toVector.map(_.str), typed)
      }
    if (own.map(_.claimId).distinct.size != own.size) return None
    def expand(c: ScaffoldClaim) = proposalClaim(plan, c.claimId, c.evidenceIds, c.claim)
    val claims = own ++ known.distinct.map(id => expand(byId(id)))
    val narrativeGiven = tree("narrativeClaimIds").arr.toVector.map(_.str).filterNot(unknown)
    val narrative = if (narrativeGiven.isEmpty) known else narrativeGiven
    if (!narrative.forall(id => claims.exists(_.claimId == id))) None
    else
      Some(
        SynthesisProposal(
          claims,
          narrative,
          tree("interpretation").str,
          tree("uncertainty").str,
          usage,
          unknown.size
        )
      )
  } catch { case NonFatal(_) => None }
}
