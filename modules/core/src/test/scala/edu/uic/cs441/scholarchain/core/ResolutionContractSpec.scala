package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.ReadWriter
import scala.io.Source

class ResolutionContractSpec extends AnyFunSuite {
  import ResolutionContractFixtures.*

  private def roundTrip[A: ReadWriter](name: String, value: A)(
      validate: A => Either[Vector[DomainViolation], A]
  ): Unit = {
    assert(validate(value).isRight, validate(value).toString)
    val stream = getClass.getClassLoader.getResourceAsStream(s"wire/$name")
    assert(stream != null, s"missing $name")
    val source = Source.fromInputStream(stream, "UTF-8")
    val json =
      try source.mkString
      finally source.close()
    assert(ujson.read(json) == ujson.read(CoreJson.compact(value)))
    assert(CoreJson.parseAndValidate[A](json)(validate).contains(value))
  }

  test("versioned work/researcher pairs, audits and accepted link freeze concrete wire contracts") {
    roundTrip("resolution-work-pair.json", workPair)(p => ResolutionValidation.check(p, context))
    roundTrip("resolution-researcher-pair.json", researcherPair)(p =>
      ResolutionValidation.check(p, context)
    )
    roundTrip("resolution-work-decision.json", workDecision)(d =>
      ResolutionValidation.check(d, context)
    )
    roundTrip("resolution-researcher-decision.json", researcherDecision)(d =>
      ResolutionValidation.check(d, context)
    )
    roundTrip("resolution-accepted-link.json", acceptedLink)(l =>
      ResolutionValidation.check(l, workDecision, context)
    )
    roundTrip("resolution-grouping-constraints.json", grouping)(c =>
      ResolutionValidation.check(c, context)
    )
  }

  test(
    "canonical pair identity ignores order and block but binds type, source, snapshot and mention"
  ) {
    assert(
      ResolutionIds
        .pair(ResolutionEntityType.Work, crossrefEndpoint, workEndpoint)
        .contains(workPair)
    )
    assert(ResolutionIds.pair(ResolutionEntityType.Work, workEndpoint, workEndpoint).isLeft)
    assert(ResolutionIds.pair(ResolutionEntityType.Work, mentionEndpoint, workEndpoint).isLeft)
    val changed = ResolutionEndpoint.Work(
      ref(Fixtures.work.provenance).copy(datasetSnapshot = "later-snapshot"),
      Fixtures.workId
    )
    val pair = ResolutionIds.pair(ResolutionEntityType.Work, changed, crossrefEndpoint).toOption.get
    assert(pair.pairId != workPair.pairId)
    assert(ResolutionValidation.check(pair, context).isLeft)
    assert(
      ResolutionValidation
        .check(workPair.copy(left = workPair.right, right = workPair.left), context)
        .isLeft
    )
    assert(ResolutionValidation.check(workPair.copy(schemaVersion = "unsupported"), context).isLeft)
    assert(ResolutionIds.endpointId(workEndpoint) != ResolutionIds.endpointId(crossrefEndpoint))
  }

  test(
    "context rejects conflicting duplicate keys while allowing identical duplicates and separate snapshots"
  ) {
    assert(
      ResolutionValidationContext
        .create(Vector(Fixtures.work, Fixtures.work), Vector(profile), Vector.empty)
        .isRight
    )
    assert(
      ResolutionValidationContext
        .create(
          Vector(Fixtures.work, Fixtures.work.copy(year = Some(2010))),
          Vector.empty,
          Vector.empty
        )
        .isLeft
    )
    val nextProvenance = Fixtures.work.provenance.copy(datasetSnapshot = "later-snapshot")
    val next = Fixtures.work.copy(
      provenance = nextProvenance,
      authors = Fixtures.work.authors.map(_.copy(provenance = nextProvenance))
    )
    val ctx = ResolutionValidationContext
      .create(Vector(Fixtures.work, next, crossref), Vector.empty, Vector.empty)
      .toOption
      .get
    val endpoint = ResolutionEndpoint.Work(ref(next.provenance), next.workId)
    assert(
      ResolutionValidation
        .check(
          ResolutionIds.pair(ResolutionEntityType.Work, endpoint, crossrefEndpoint).toOption.get,
          ctx
        )
        .isRight
    )
    val wrong = ResolutionEndpoint.Mention(ref(crossref.provenance), Fixtures.riceMentionId)
    assert(ResolutionIds.pair(ResolutionEntityType.Researcher, wrong, profileEndpoint).isLeft)
  }

  test(
    "ORCID work activity is eligible without authors, other activities cannot masquerade as work"
  ) {
    val pair =
      ResolutionIds.pair(ResolutionEntityType.Work, activityEndpoint, workEndpoint).toOption.get
    assert(ResolutionValidation.check(pair, context).isRight)
    val wrong = ResolutionEndpoint.OrcidWorkActivity(ref(employment.provenance), None)
    assert(ResolutionIds.pair(ResolutionEntityType.Work, wrong, workEndpoint).isLeft)
    val wrongBinding = ResolutionEndpoint.OrcidWorkActivity(ref(activity.provenance), None)
    assert(
      ResolutionValidation
        .check(
          ResolutionIds.pair(ResolutionEntityType.Work, wrongBinding, workEndpoint).toOption.get,
          context
        )
        .isLeft
    )
  }

  test("audit validates timestamps, provenance, hashes, feature availability and finite values") {
    val invalids = Vector(
      workDecision.copy(decidedAtUtc = "2026-10-15T12:00:00+00:00"),
      workDecision.copy(policyHash = "not-a-hash"),
      workDecision.copy(decision = workDecision.decision.copy(sourceId = Fixtures.workId)),
      workDecision.copy(featureEvidence = Vector(ResolutionFeature("x", None, None, Vector.empty))),
      workDecision.copy(featureEvidence =
        Vector(ResolutionFeature("x", Some(1), Some("missing"), Vector.empty))
      ),
      workDecision.copy(featureEvidence =
        Vector(ResolutionFeature("x", Some(Double.NaN), None, Vector.empty))
      ),
      workDecision.copy(featureEvidence =
        Vector(ResolutionFeature("x", Some(1), None, Vector("invented")))
      ),
      workDecision.copy(confidenceSemantics = ResolutionConfidenceSemantics.Unavailable)
    )
    invalids.foreach(d => assert(ResolutionValidation.check(reidentify(d), context).isLeft))
    val missing = reidentify(
      workDecision.copy(
        decision = workDecision.decision.copy(confidence = 0),
        confidenceSemantics = ResolutionConfidenceSemantics.Unavailable,
        scoreUnavailableReason = Some("NOT_SCORED")
      )
    )
    assert(ResolutionValidation.check(missing, context).isRight)
    assert(
      ResolutionValidation
        .check(workDecision.copy(decidedAtUtc = "2026-10-15T13:00:00Z"), context)
        .isLeft
    )
  }

  test("LLM audit retains pre-decision score and model confidence as separate values") {
    val metadata = ResolutionAdjudication(
      hash,
      "synthetic-prompt-v1",
      hash,
      "synthetic-response-v1",
      "fake",
      "fixture-model",
      None,
      hash,
      hash,
      ResolutionAdjudicationMode.Fake,
      false,
      0.6,
      Vector("source:fixture"),
      ResolutionPreAdjudication(Some(0.8), MatchOutcome.Unresolved, ResolutionDecisionPath.Scored)
    )
    val llm = reidentify(
      researcherDecision.copy(
        decisionPath = ResolutionDecisionPath.LlmAdjudicated,
        adjudication = Some(metadata)
      )
    )
    assert(ResolutionValidation.check(llm, context).isRight)
    assert(llm.decision.confidence != llm.adjudication.get.reportedConfidence)
    assert(ResolutionValidation.check(reidentify(llm.copy(adjudication = None)), context).isLeft)
    assert(
      ResolutionValidation
        .check(
          reidentify(
            llm.copy(adjudication =
              Some(metadata.copy(reportedConfidence = Double.PositiveInfinity))
            )
          ),
          context
        )
        .isLeft
    )
    assert(
      ResolutionValidation
        .check(
          reidentify(
            llm.copy(adjudication =
              Some(
                metadata.copy(preAdjudication =
                  metadata.preAdjudication.copy(outcome = MatchOutcome.Conflict)
                )
              )
            )
          ),
          context
        )
        .isLeft
    )
    val json = ujson.read(CoreJson.compact(llm))
    json("adjudication").obj.remove("reportedConfidence")
    assert(CoreJson.parse[ResolutionDecision](json.render()).isLeft)
  }

  test("a single final LLM path requires metadata and cannot report conflict") {
    val metadata = ResolutionAdjudication(
      hash,
      "synthetic-prompt-v1",
      hash,
      "synthetic-response-v1",
      "fake",
      "fixture-model",
      None,
      hash,
      hash,
      ResolutionAdjudicationMode.Fake,
      false,
      0.6,
      Vector("source:fixture"),
      ResolutionPreAdjudication(Some(0.8), MatchOutcome.Unresolved, ResolutionDecisionPath.Scored)
    )
    val llm = researcherDecision.copy(
      decisionPath = ResolutionDecisionPath.LlmAdjudicated,
      adjudication = Some(metadata)
    )
    Vector(
      ResolutionDecisionPath.Scored,
      ResolutionDecisionPath.ExactIdentifier,
      ResolutionDecisionPath.HardConflict
    ).foreach { path =>
      val outcome =
        if (path == ResolutionDecisionPath.HardConflict) MatchOutcome.Conflict
        else MatchOutcome.Unresolved
      val wrongPath =
        reidentify(llm.copy(decisionPath = path, decision = llm.decision.copy(decision = outcome)))
      assert(ResolutionValidation.check(wrongPath, context).isLeft)
    }
    val conflict =
      reidentify(llm.copy(decision = llm.decision.copy(decision = MatchOutcome.Conflict)))
    assert(ResolutionValidation.check(conflict, context).isLeft)
    Vector(MatchOutcome.Accepted, MatchOutcome.Rejected, MatchOutcome.Unresolved).foreach {
      outcome =>
        assert(
          ResolutionValidation
            .check(reidentify(llm.copy(decision = llm.decision.copy(decision = outcome))), context)
            .isRight
        )
    }
  }

  test("links require actual accepted audit, matching run/policy/provenance and endpoints") {
    assert(ResolutionValidation.check(acceptedLink, workDecision, context).isRight)
    val rejected = audit(workPair, MatchOutcome.Rejected)
    assert(ResolutionValidation.check(link(rejected), rejected, context).isLeft)
    assert(
      ResolutionValidation
        .check(acceptedLink.copy(policyHash = "0" * 64), workDecision, context)
        .isLeft
    )
    assert(
      ResolutionValidation
        .check(acceptedLink.copy(pair = researcherPair), workDecision, context)
        .isLeft
    )
  }

  test(
    "component guard rejects transitive conflicts, missing coverage and explicit caller bounds"
  ) {
    val endpoints = Vector(workEndpoint, crossrefEndpoint, activityEndpoint)
    val ac =
      ResolutionIds.pair(ResolutionEntityType.Work, workEndpoint, activityEndpoint).toOption.get
    val base = grouping.copy(
      coveredEndpoints = endpoints,
      authoritativeIdentifiers = grouping.authoritativeIdentifiers :+ ResolutionIdentifierAssertion(
        activityEndpoint,
        ResolutionAuthorityNamespace.Doi,
        Fixtures.doi,
        Vector("source:fixture")
      ),
      cannotLinks =
        Vector(ResolutionCannotLink(ac, "AUTHORITATIVE_CONFLICT", Vector("source:fixture")))
    )
    assert(
      ResolutionValidation
        .checkComponent(Vector(workEndpoint, crossrefEndpoint), base, context, 3, 20)
        .isRight
    )
    assert(ResolutionValidation.checkComponent(endpoints, base, context, 3, 20).isLeft)
    val different = base.copy(
      cannotLinks = Vector.empty,
      authoritativeIdentifiers = base.authoritativeIdentifiers :+ ResolutionIdentifierAssertion(
        activityEndpoint,
        ResolutionAuthorityNamespace.Doi,
        "10.9999/different",
        Vector("source:fixture")
      )
    )
    assert(ResolutionValidation.checkComponent(endpoints, different, context, 3, 20).isLeft)
    assert(ResolutionValidation.checkComponent(endpoints, grouping, context, 3, 20).isLeft)
    assert(
      ResolutionValidation.checkComponent(Vector(workEndpoint), grouping, context, 0, 20).isLeft
    )
    assert(
      ResolutionValidation.checkComponent(Vector(workEndpoint), grouping, context, 3, 1).isLeft
    )
    val noIds = grouping.copy(authoritativeIdentifiers = Vector.empty)
    assert(
      ResolutionValidation
        .checkComponent(Vector(workEndpoint, crossrefEndpoint), noIds, context, 3, 20)
        .isLeft
    )
  }
}
