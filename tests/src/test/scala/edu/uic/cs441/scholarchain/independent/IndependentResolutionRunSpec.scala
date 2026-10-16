package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import upickle.default.{write, writeJs}

class IndependentResolutionRunSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  private val config = ResolutionConfig.example
  private val basePolicy = ResolutionPolicy.example

  private def scorePolicy: ResolutionPolicy = basePolicy.copy(work =
    basePolicy.work.copy(
      weights = Map("title" -> 1.0, "yearCompatibility" -> 1.0),
      featureGroups = Map("title" -> "bibliography", "yearCompatibility" -> "chronology"),
      requiredGroups = Vector("bibliography", "chronology"),
      minimumIndependentGroupsForAccept = 2,
      supportiveFeatureMin = 0.3,
      bibliographicEnabled = false,
      rejectThreshold = 0.5,
      acceptThreshold = 0.9,
      llmBandMin = 0.6,
      llmBandMax = 0.8
    )
  )

  private def uncertain() = {
    val a = work("conf/independent/RunA", title = "alpha beta", names = Vector.empty)
    val b = work("conf/independent/RunB", title = "alpha gamma", names = Vector.empty)
    val in =
      ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty).toOption.get
    val comparison = DerivedPair(
      pair(endpoint(a), endpoint(b)),
      Vector.empty,
      (in.refs(endpoint(a)) ++ in.refs(endpoint(b))).distinct.sorted
    )
    (in, CandidatePopulation(Vector(comparison), Vector.empty, Vector.empty))
  }

  private class Scripted(outcome: String) extends AdjudicationAdapter {
    val count = new AtomicInteger(0)
    val provider = config.adjudication.provider
    val model = config.adjudication.model
    val modelVersion = config.adjudication.modelVersion
    def respond(r: AdjudicationRequest): String = {
      count.incrementAndGet()
      write(
        AdjudicationResponse(
          Adjudication.responseSchema,
          r.requestHash,
          r.pairId,
          r.sourceId,
          r.targetId,
          r.inputEvidenceHash,
          r.policyHash,
          outcome,
          Vector(
            if (outcome == "accept") "SUPPORTED_SAME_IDENTITY"
            else if (outcome == "reject") "SUPPORTED_DIFFERENT_IDENTITY"
            else "INSUFFICIENT_EVIDENCE"
          ),
          r.evidence.map(_.ref),
          "Scripted offline evidence; no actual model call.",
          0.82,
          if (outcome == "abstain") Vector.empty else Vector(r.evidence.head.ref + "#/title")
        )
      )
    }
  }

  test("disabled mode makes zero adapter calls and eligible pairs remain auditable unresolved") {
    val (input, population) = uncertain()
    val adapter = new Scripted("accept")
    val run = ResolutionEngine.resolve(
      input,
      population,
      scorePolicy,
      config,
      "disabled",
      None,
      runId,
      instant,
      Some(adapter)
    )
    assert(run.isRight, run.toString)
    val actual = run.toOption.get
    assert(actual.fakeCalls == 0 && adapter.count.get() == 0)
    assert(actual.decisions.head.decision.decision == MatchOutcome.Unresolved)
    assert(actual.decisions.head.decision.reasonCodes.contains("LLM_DISABLED"))
    assert(actual.decisions.head.adjudication.isEmpty && actual.links.isEmpty)
    assert(
      actual.decisions.head.confidenceSemantics == ResolutionConfidenceSemantics.UncalibratedScore
    )
  }

  test("fake accept reject and abstain keep pre-adjudication score and model confidence separate") {
    Vector(
      "accept" -> MatchOutcome.Accepted,
      "reject" -> MatchOutcome.Rejected,
      "abstain" -> MatchOutcome.Unresolved
    ).foreach { case (outcome, expected) =>
      val (input, population) = uncertain()
      val adapter = new Scripted(outcome)
      val run = ResolutionEngine.resolve(
        input,
        population,
        scorePolicy,
        config,
        "fake",
        None,
        runId,
        instant,
        Some(adapter)
      )
      assert(run.isRight, run.toString)
      val actual = run.toOption.get
      val decision = actual.decisions.head
      assert(
        decision.decision.decision == expected && actual.fakeCalls == 1 && adapter.count.get() == 1
      )
      assert(decision.decisionPath == ResolutionDecisionPath.LlmAdjudicated)
      val metadata = decision.adjudication.get
      assert(
        metadata.mode == ResolutionAdjudicationMode.Fake && metadata.reportedConfidence == 0.82
      )
      assert(metadata.preAdjudication.outcome == MatchOutcome.Unresolved)
      assert(metadata.preAdjudication.score.exists(s => math.abs(s - 2.0 / 3.0) < 1e-12))
      assert(math.abs(decision.decision.confidence - 2.0 / 3.0) < 1e-12)
      assert(actual.links.size == (if (expected == MatchOutcome.Accepted) 1 else 0))
      assert(actual.details.head.adjudication.flatMap(_.response).exists(_.rationale.nonEmpty))
    }
  }

  test("out-of-band and insufficient independent evidence cannot reach the adapter") {
    val (input, population) = uncertain()
    val adapter = new Scripted("accept")
    val outOfBand =
      scorePolicy.copy(work = scorePolicy.work.copy(llmBandMin = 0.7, llmBandMax = 0.8))
    val result = ResolutionEngine
      .resolve(input, population, outOfBand, config, "fake", None, runId, instant, Some(adapter))
      .toOption
      .get
    assert(
      result.fakeCalls == 0 && adapter.count
        .get() == 0 && result.decisions.head.decision.decision == MatchOutcome.Unresolved
    )
    val insufficient = scorePolicy.copy(work = scorePolicy.work.copy(supportiveFeatureMin = 0.8))
    val noEvidence = ResolutionEngine
      .resolve(input, population, insufficient, config, "fake", None, runId, instant, Some(adapter))
      .toOption
      .get
    assert(noEvidence.fakeCalls == 0 && adapter.count.get() == 0)
    assert(noEvidence.decisions.head.decision.decision == MatchOutcome.Unresolved)
  }

  test("hard identifier conflicts never call the adapter and every known source fact is exported") {
    val a = work("conf/independent/RunConflictA", orcids = Map(1 -> orcidA))
    val b = work("conf/independent/RunConflictB", orcids = Map(1 -> orcidB))
    val input = ResolutionInput
      .create(Vector(a, b), Vector(profile(orcidA), profile(orcidB)), Vector.empty, Vector.empty)
      .toOption
      .get
    val p = DerivedPair(
      pair(mention(a), mention(b)),
      Vector.empty,
      (input.refs(mention(a)) ++ input.refs(mention(b))).distinct.sorted
    )
    val adapter = new Scripted("accept")
    val run = ResolutionEngine
      .resolve(
        input,
        CandidatePopulation(Vector(p), Vector.empty, Vector.empty),
        basePolicy,
        config,
        "fake",
        None,
        runId,
        instant,
        Some(adapter)
      )
      .toOption
      .get
    assert(run.fakeCalls == 0 && adapter.count.get() == 0 && run.links.isEmpty)
    assert(run.decisions.head.decision.decision == MatchOutcome.Conflict)
    val constraints = run.constraints.find(_.entityType == ResolutionEntityType.Researcher).get
    assert(
      constraints.authoritativeIdentifiers.size == 4,
      "two mentions and both profiles retain their ORCIDs"
    )
    assert(constraints.authoritativeIdentifiers.map(_.value).toSet == Set(orcidA, orcidB))
    assert(constraints.cannotLinks.map(_.pair.pairId).contains(p.pair.pairId))
    assert(run.constraints.flatMap(_.coveredEndpoints).toSet == input.endpoints.toSet)
    run.constraints.foreach(c => assert(ResolutionValidation.check(c, input.context).isRight))
  }

  test("fake replay reuses only a verified cache while preserving substantive decisions") {
    val (input, population) = uncertain()
    val adapter = new Scripted("accept")
    val dir = Files.createTempDirectory("scholarchain-independent-run-cache-").toRealPath()
    val one = ResolutionEngine
      .resolve(
        input,
        population,
        scorePolicy,
        config,
        "fake",
        Some(dir),
        runId,
        instant,
        Some(adapter)
      )
      .toOption
      .get
    val two = ResolutionEngine
      .resolve(
        input,
        population,
        scorePolicy,
        config,
        "fake",
        Some(dir),
        runId,
        instant,
        Some(adapter)
      )
      .toOption
      .get
    assert(one.fakeCalls == 1 && two.fakeCalls == 0 && adapter.count.get() == 1)
    assert(
      !one.decisions.head.adjudication.get.cacheHit && two.decisions.head.adjudication.get.cacheHit
    )
    val firstDecision = one.decisions.head.decision
    val replayedDecision = two.decisions.head.decision
    assert(firstDecision.reasonCodes.contains("VALIDATED_FAKE"))
    assert(!firstDecision.reasonCodes.contains("CACHE_HIT"))
    assert(replayedDecision.reasonCodes.contains("CACHE_HIT"))
    assert(!replayedDecision.reasonCodes.contains("VALIDATED_FAKE"))
    val transportCodes = Set("VALIDATED_FAKE", "CACHE_HIT")
    assert(
      firstDecision.copy(reasonCodes = firstDecision.reasonCodes.filterNot(transportCodes)) ==
        replayedDecision.copy(reasonCodes = replayedDecision.reasonCodes.filterNot(transportCodes))
    )
    assert(one.constraints == two.constraints)
  }

  test("missing forged or wrong-pair block evidence fails before adapter calls") {
    val a = work("conf/independent/EvidenceA")
    val b = work("conf/independent/EvidenceB")
    val c = work("conf/independent/EvidenceC")
    val actual = candidate(a, c)
    val input = ResolutionInput
      .create(Vector(a, b, c), Vector.empty, Vector.empty, Vector(actual))
      .toOption
      .get
    val correctSourceRefs = (input.refs(endpoint(a)) ++ input.refs(endpoint(b))).distinct.sorted
    val forgedPair = DerivedPair(
      pair(endpoint(a), endpoint(b)),
      Vector(CandidateBlockRef(actual.candidateId, actual.blockKey)),
      (correctSourceRefs :+ ResolutionInput.evidenceFor("match-candidate", writeJs(actual))).sorted
    )
    val adapter = new Scripted("accept")
    Vector(
      forgedPair,
      forgedPair.copy(evidenceRefs = Vector("er-evidence:missing")),
      forgedPair.copy(evidenceRefs = input.refs(endpoint(a)))
    ).foreach { p =>
      val result = ResolutionEngine.resolve(
        input,
        CandidatePopulation(Vector(p), Vector.empty, Vector.empty),
        basePolicy,
        config,
        "fake",
        None,
        runId,
        instant,
        Some(adapter)
      )
      assert(result.isLeft, "invalid provenance cannot produce a decision")
    }
    assert(adapter.count.get() == 0)
  }
}
