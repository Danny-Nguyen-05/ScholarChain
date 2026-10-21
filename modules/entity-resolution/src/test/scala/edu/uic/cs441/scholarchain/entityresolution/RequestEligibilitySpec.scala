package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.writeJs

class RequestEligibilitySpec extends AnyFunSuite {
  private val profile = RequestEligibilityPolicy.example
  private val legacy = ResolutionPolicy.example
  private val policy = RequestEligibilityPolicy.bind(legacy, profile).toOption.get
  private def classified(
      coauthor: Option[Double] = Some(0.2),
      affiliation: Option[Double] = Some(1.0),
      score: Double = 0.76,
      sufficient: Boolean = false,
      outcome: MatchOutcome = MatchOutcome.Unresolved,
      name: Option[Double] = Some(1.0),
      initials: Option[Double] = Some(1.0)
  ): ClassifiedPair = {
    val features = Vector(
      "name" -> name,
      "initials" -> initials,
      "affiliation" -> affiliation,
      "coauthorOverlap" -> coauthor
    ).map { (n, v) =>
      ResolutionFeature(n, v, if (v.isDefined) None else Some("SYNTHETIC_MISSING"), Vector.empty)
    }
    ClassifiedPair(
      outcome,
      ResolutionDecisionPath.Scored,
      Some(score),
      features,
      Vector("SCORE_IN_UNRESOLVED_GAP"),
      Vector("name", "affiliation"),
      sufficient
    )
  }
  private def eligible(
      c: ClassifiedPair,
      entity: ResolutionEntityType = ResolutionEntityType.Researcher
  ): Boolean =
    RequestEligibilityPolicy.eligible(c, entity, policy, Some(profile))

  test(
    "legacy policy bytes and fingerprint remain unchanged; explicit profile binds its complete hash"
  ) {
    assert(legacy.fingerprint == "ad8c520fd8ff2e3697e15b2895852ca23e04c8d93f677acea3b366fcc101ef9f")
    assert(!writeJs(legacy).obj.contains("requestEligibility"))
    assert(policy.copy(policyVersion = legacy.policyVersion) == legacy)
    assert(policy.policyVersion.endsWith(profile.fingerprint))
    assert(policy.fingerprint != legacy.fingerprint)
    val stricter = profile.copy(researcherAffiliationMin = 0.9)
    assert(
      RequestEligibilityPolicy.bind(legacy, stricter).toOption.get.fingerprint != policy.fingerprint
    )
    assert(RequestEligibilityPolicy.validateBinding(policy, Some(profile)).isRight)
    assert(RequestEligibilityPolicy.validateBinding(policy, None).isLeft)
    assert(RequestEligibilityPolicy.validateBinding(legacy, Some(profile)).isLeft)
    assert(RequestEligibilityPolicy.validateBinding(policy, Some(stricter)).isLeft)
    assert(RequestEligibilityPolicy.bind(policy, profile).isLeft)
  }
  test(
    "request evidence permits positive observed context without changing automatic sufficiency"
  ) {
    val c = classified()
    assert(!c.sufficient)
    assert(eligible(c))
    assert(!RequestEligibilityPolicy.eligible(c, ResolutionEntityType.Researcher, legacy))
    assert(
      RequestEligibilityPolicy.eligible(
        c.copy(sufficient = true),
        ResolutionEntityType.Researcher,
        legacy
      )
    )
    assert(!eligible(c, ResolutionEntityType.Work))
  }
  test(
    "missing or disagreeing name affiliation and contextual evidence cannot request adjudication"
  ) {
    assert(!eligible(classified(coauthor = None)))
    assert(!eligible(classified(coauthor = Some(0))))
    assert(!eligible(classified(affiliation = None)))
    assert(!eligible(classified(affiliation = Some(0.79))))
    assert(!eligible(classified(name = None)))
    assert(!eligible(classified(name = Some(0.79))))
    assert(!eligible(classified(initials = None)))
    assert(!eligible(classified(initials = Some(0))))
  }
  test("score bands remain inclusive and exact conflict rejected outcomes stay out") {
    assert(eligible(classified(score = legacy.researcher.llmBandMin)))
    assert(eligible(classified(score = legacy.researcher.llmBandMax)))
    assert(!eligible(classified(score = legacy.researcher.llmBandMin - 0.0001)))
    assert(!eligible(classified(score = legacy.researcher.llmBandMax + 0.0001)))
    Vector(MatchOutcome.Accepted, MatchOutcome.Rejected, MatchOutcome.Conflict).foreach(o =>
      assert(!eligible(classified(outcome = o)))
    )
  }
  test("closed request profile rejects unknown duplicate weakening and unsupported fields") {
    val json = writeJs(profile)
    json.obj("unknown") = ujson.Bool(true)
    assert(RequestEligibilityPolicy.parse(json.render()).isLeft)
    assert(
      RequestEligibilityPolicy
        .parse(
          upickle.default.write(profile).replaceFirst("\\{", "{\"schemaVersion\":\"ignored\",")
        )
        .isLeft
    )
    assert(RequestEligibilityPolicy.validate(profile.copy(researcherNameMin = 0.79)).isLeft)
    assert(
      RequestEligibilityPolicy.validate(profile.copy(researcherAffiliationMin = Double.NaN)).isLeft
    )
    assert(
      RequestEligibilityPolicy
        .validate(profile.copy(requireAutomaticSufficiencyForModelAccept = false))
        .isLeft
    )
    assert(
      RequestEligibilityPolicy.validate(profile.copy(requireCompatibleInitials = false)).isLeft
    )
    assert(
      RequestEligibilityPolicy.validate(profile.copy(requirePositiveCoauthorOverlap = false)).isLeft
    )
  }
}
