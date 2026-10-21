package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Path
import scala.util.Try
import upickle.default.ReadWriter

/** Evidence needed to ask for a judgment is distinct from evidence needed to merge identities. This
  * opt-in profile never changes scoring, automatic acceptance, or identifier protection.
  */
final case class RequestEligibilityPolicy(
    schemaVersion: String,
    policyVersion: String,
    researcherNameMin: Double,
    researcherAffiliationMin: Double,
    requireCompatibleInitials: Boolean,
    requirePositiveCoauthorOverlap: Boolean,
    requireAutomaticSufficiencyForModelAccept: Boolean
) derives ReadWriter {
  def fingerprint: String = StrictJson.hash(this)
}

object RequestEligibilityPolicy {
  private val separator = "+request-eligibility:"
  val blockedAcceptReason = "LLM_ACCEPT_BLOCKED_INSUFFICIENT_ACCEPTANCE_EVIDENCE"
  def parse(text: String): Either[String, RequestEligibilityPolicy] =
    StrictJson.parse[RequestEligibilityPolicy](text).flatMap(validate)
  def load(path: Path): Either[String, RequestEligibilityPolicy] =
    StrictJson.file(path, 1048576).flatMap(parse)
  def example: RequestEligibilityPolicy =
    parse(ResourceText.read("adjudication/request-eligibility.v1.json"))
      .fold(e => throw new IllegalStateException(e), identity)
  def validate(p: RequestEligibilityPolicy): Either[String, RequestEligibilityPolicy] = Try {
    require(
      p.schemaVersion == "scholarchain.request-eligibility.v1",
      "unsupported request eligibility schema"
    )
    require(
      p.policyVersion.matches("[a-z0-9][a-z0-9.-]{0,95}"),
      "invalid request eligibility version"
    )
    require(
      Vector(p.researcherNameMin, p.researcherAffiliationMin).forall(v =>
        v.isFinite && v >= 0.8 && v <= 1
      ),
      "request name and affiliation thresholds must be in [0.8,1]"
    )
    require(
      p.requireCompatibleInitials && p.requirePositiveCoauthorOverlap && p.requireAutomaticSufficiencyForModelAccept,
      "request evidence and automatic acceptance protections are mandatory"
    )
    p
  }.toEither.left.map(_.getMessage)

  /** The legacy case class and its serialization remain unchanged. The effective version contains
    * the complete profile hash, so requests, caches, decisions and exports bind the opt-in rule.
    */
  def bind(
      base: ResolutionPolicy,
      profile: RequestEligibilityPolicy
  ): Either[String, ResolutionPolicy] =
    for {
      _ <- ResolutionPolicy.validate(base)
      _ <- validate(profile)
      policy <- Try {
        require(!base.policyVersion.contains(separator), "request policy already bound")
        base.copy(policyVersion =
          base.policyVersion + separator + profile.policyVersion + ":" + profile.fingerprint
        )
      }.toEither.left.map(_.getMessage)
    } yield policy

  def validateBinding(
      policy: ResolutionPolicy,
      profile: Option[RequestEligibilityPolicy]
  ): Either[String, Unit] = Try {
    profile match {
      case None =>
        require(!policy.policyVersion.contains(separator), "bound request policy artifact required")
      case Some(p) =>
        validate(p).fold(e => throw new IllegalArgumentException(e), identity)
        val marker = separator + p.policyVersion + ":" + p.fingerprint
        require(
          policy.policyVersion.length > marker.length && policy.policyVersion.endsWith(
            marker
          ) && policy.policyVersion.indexOf(
            separator
          ) == policy.policyVersion.length - marker.length,
          "request policy/effective policy binding mismatch"
        )
    }
    ()
  }.toEither.left.map(_.getMessage)

  def eligible(
      classified: ClassifiedPair,
      entity: ResolutionEntityType,
      policy: ResolutionPolicy,
      requestPolicy: Option[RequestEligibilityPolicy] = None
  ): Boolean = {
    validateBinding(policy, requestPolicy).fold(
      e => throw new IllegalArgumentException(e),
      identity
    )
    val p = policy.forEntity(entity)
    val unresolvedInBand =
      classified.outcome == MatchOutcome.Unresolved && classified.score.exists(s =>
        s >= p.llmBandMin && s <= p.llmBandMax
      )
    val requestEvidence =
      requestPolicy.filter(_ => entity == ResolutionEntityType.Researcher).exists { profile =>
        val features = classified.features.flatMap(f => f.value.map(f.name -> _)).toMap
        features.get("name").exists(_ >= profile.researcherNameMin) &&
        features.get("initials").contains(1.0) &&
        features.get("affiliation").exists(_ >= profile.researcherAffiliationMin) &&
        features.get("coauthorOverlap").exists(_ > 0.0)
      }
    unresolvedInBand && (classified.sufficient || requestEvidence)
  }
}
