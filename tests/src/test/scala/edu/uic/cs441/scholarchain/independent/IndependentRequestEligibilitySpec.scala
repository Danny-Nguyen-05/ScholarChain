package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write, writeJs}

/** Synthetic evidence only. No gold labels, public acquisition, real credentials or HTTP. */
class IndependentRequestEligibilitySpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*

  private val base = ResolutionPolicy.example
  private val profile = RequestEligibilityPolicy.example
  private def bound = RequestEligibilityPolicy.bind(base, profile).toOption.get
  private final case class Example(input: ResolutionInput, candidate: DerivedPair)

  private def sample(
      key: String,
      leftCoauthors: Vector[String] = Vector("Shared Colleague", "Left First", "Left Second"),
      rightCoauthors: Vector[String] = Vector("Shared Colleague", "Right First", "Right Second"),
      affiliations: String = "same",
      leftName: String = "Alex Example",
      rightName: String = "Alex Example",
      leftOrcid: Option[String] = None,
      rightOrcid: Option[String] = None,
      samePublication: Boolean = false
  ): Example = {
    val a = work(
      s"conf/independent/request/$key/left",
      title = "Synthetic transaction log evidence left",
      names = Vector(leftName) ++ leftCoauthors,
      doi = if (samePublication) Some("10.5555/request-same-publication") else None,
      orcids = leftOrcid.map(1 -> _).toMap
    )
    val b = work(
      s"conf/independent/request/$key/right",
      title = "Synthetic transaction log evidence right",
      names = Vector(rightName) ++ rightCoauthors,
      doi = a.doi,
      orcids = rightOrcid.map(1 -> _).toMap
    )
    def affiliation(w: WorkRecord, ror: Option[String], name: Option[String]) =
      MentionAffiliation(
        SchemaVersions.domain,
        w.authors.head.mentionId,
        w.source,
        w.sourceRecordId,
        w.provenance.datasetSnapshot,
        name,
        ror,
        None,
        ror.map("institution:ror:" + _),
        IndependentResolutionFixtures.note,
        w.provenance
      )
    val af = affiliations match {
      case "same" => Vector(a, b).map(w => affiliation(w, Some("03yrm5c26"), None))
      case "different" =>
        Vector(
          affiliation(a, Some("03yrm5c26"), None),
          affiliation(b, Some("01an7q238"), None)
        )
      case "incomparable" =>
        Vector(
          affiliation(a, Some("03yrm5c26"), None),
          affiliation(b, None, Some("Synthetic Independent Lab"))
        )
      case "missing" => Vector.empty
    }
    val in = ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty, af)
    assert(in.isRight, in.toString)
    val input = in.toOption.get
    val p = pair(mention(a), mention(b))
    Example(
      input,
      DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
    )
  }

  private def classified(example: Example, policy: ResolutionPolicy = bound): ClassifiedPair = {
    val result = ResolutionEngine.classify(example.candidate, example.input, policy)
    assert(result.isRight, result.toString)
    result.toOption.get
  }
  private def eligible(example: Example): Boolean = RequestEligibilityPolicy.eligible(
    classified(example),
    ResolutionEntityType.Researcher,
    bound,
    Some(profile)
  )
  private def population(example: Example) =
    CandidatePopulation(Vector(example.candidate), Vector.empty, Vector.empty)
  private def response(request: AdjudicationRequest, outcome: String): AdjudicationResponse = {
    val original = IndependentLiveFixtures.response(request, outcome)
    val work = request.evidence.find(_.kind == "work").get
    original.copy(fieldRefs =
      if (outcome == "abstain") Vector.empty else Vector(work.ref + "#/title")
    )
  }
  private def resolve(example: Example, mode: String, outcome: String) = {
    val calls = new AtomicInteger(0)
    val cfg = ResolutionConfig.example
    val adapter = new AdjudicationAdapter {
      val provider = cfg.adjudication.provider
      val model = cfg.adjudication.model
      val modelVersion = cfg.adjudication.modelVersion
      def respond(request: AdjudicationRequest): String = {
        calls.incrementAndGet()
        write(response(request, outcome))
      }
    }
    val result = ResolutionEngine.resolve(
      example.input,
      population(example),
      bound,
      cfg,
      mode,
      None,
      runId,
      instant,
      Some(adapter),
      Some(profile)
    )
    assert(result.isRight, result.toString)
    (result.toOption.get, calls.get())
  }

  test("legacy policy fingerprint and strict acceptance thresholds remain frozen") {
    assert(base.fingerprint == "ad8c520fd8ff2e3697e15b2895852ca23e04c8d93f677acea3b366fcc101ef9f")
    assert(base.researcher.supportiveFeatureMin == 0.8)
    assert(base.researcher.minimumIndependentGroupsForAccept == 3)
    assert(base.researcher.llmBandMin == 0.65 && base.researcher.llmBandMax == 0.88)
    assert(bound.researcher == base.researcher && bound.work == base.work)
    assert(bound.fingerprint != base.fingerprint)
    assert(RequestEligibilityPolicy.validateBinding(bound, Some(profile)).isRight)
    assert(RequestEligibilityPolicy.validateBinding(base, Some(profile)).isLeft)
    assert(RequestEligibilityPolicy.bind(bound, profile).isLeft)
    val raw = writeJs(profile)
    raw("unrecordedOverride") = ujson.Num(0.01)
    assert(RequestEligibilityPolicy.parse(raw.render()).isLeft)
    assert(RequestEligibilityPolicy.validate(profile.copy(researcherNameMin = 0.79)).isLeft)
    assert(RequestEligibilityPolicy.validate(profile.copy(researcherAffiliationMin = 0.79)).isLeft)
    assert(
      RequestEligibilityPolicy.validate(profile.copy(requirePositiveCoauthorOverlap = false)).isLeft
    )
    assert(
      RequestEligibilityPolicy
        .validate(profile.copy(requireAutomaticSufficiencyForModelAccept = false))
        .isLeft
    )
    val stricter = profile.copy(researcherNameMin = 0.9)
    assert(stricter.fingerprint != profile.fingerprint)
    assert(
      RequestEligibilityPolicy.bind(base, stricter).toOption.get.fingerprint != bound.fingerprint
    )
    assert(RequestEligibilityPolicy.validateBinding(bound, Some(stricter)).isLeft)
  }

  test("positive independent coauthor and affiliation context permits a request, not acceptance") {
    val example = sample("positive")
    val d = classified(example)
    val features = d.features.map(f => f.name -> f.value).toMap
    assert(features("name").contains(1.0) && features("initials").contains(1.0))
    assert(features("affiliation").contains(1.0))
    assert(features("coauthorOverlap").contains(0.2))
    // Shared/union coauthors = 1/5; .35+.05+.3*(1/5)+.2+.1 = .76.
    assert(d.score.exists(s => math.abs(s - 0.76) < 1e-12))
    assert(d.outcome == MatchOutcome.Unresolved && !d.sufficient)
    assert(!RequestEligibilityPolicy.eligible(d, ResolutionEntityType.Researcher, base))
    assert(eligible(example))
    assert(
      classified(example, base) == d,
      "request binding cannot change classifier evidence or outcome"
    )
  }

  test("zero, absent and duplicated-publication coauthor context cannot become a request") {
    val examples = Vector(
      sample(
        "zero-context",
        rightCoauthors = Vector("Other Colleague", "Right First", "Right Second")
      ),
      sample("no-context", leftCoauthors = Vector.empty, rightCoauthors = Vector.empty),
      sample("same-publication", samePublication = true)
    )
    examples.foreach(e => assert(!eligible(e), e.candidate.pair.pairId))
    val zero = classified(examples.head)
    assert(zero.features.find(_.name == "coauthorOverlap").get.value.contains(0.0))
    assert(
      zero.score.exists(s => math.abs(s - 0.7) < 1e-12),
      "zero-context negative is still in-band"
    )
    assert(classified(examples.last).features.find(_.name == "coauthorOverlap").get.value.isEmpty)
  }

  test("missing, incomparable and conflicting affiliation evidence cannot become a request") {
    Vector("missing", "incomparable", "different").foreach { kind =>
      val e = sample("affiliation-" + kind, affiliations = kind)
      assert(!eligible(e), kind)
    }
    val inBand = classified(sample("missing-in-band", affiliations = "missing"))
    assert(inBand.score.exists(s => math.abs(s - 0.7) < 1e-12))
  }

  test(
    "name-only, incompatible names, exact identifiers, hard conflicts and out-of-band pairs are excluded"
  ) {
    val same = Vector("Shared Colleague", "Shared Second", "Shared Third")
    val excluded = Vector(
      sample(
        "name-only",
        leftCoauthors = Vector.empty,
        rightCoauthors = Vector.empty,
        affiliations = "missing"
      ),
      sample("names-differ", rightName = "Different Person"),
      sample("exact", leftOrcid = Some(orcidA), rightOrcid = Some(orcidA)),
      sample("conflict", leftOrcid = Some(orcidA), rightOrcid = Some(orcidB)),
      sample("above-band", leftCoauthors = same, rightCoauthors = same)
    )
    excluded.foreach(e => assert(!eligible(e), e.candidate.pair.pairId))
    assert(classified(excluded(2)).path == ResolutionDecisionPath.ExactIdentifier)
    assert(classified(excluded(3)).outcome == MatchOutcome.Conflict)
    assert(classified(excluded.last).score.exists(_ > base.researcher.llmBandMax))
  }

  test(
    "fake acceptance is retained as an audited judgment but cannot export an unsafe accepted link"
  ) {
    val (result, calls) = resolve(sample("fake-accept"), "fake", "accept")
    assert(calls == 1 && result.fakeCalls == 1)
    assert(result.decisions.size == 1 && result.links.isEmpty)
    val decision = result.decisions.head
    assert(decision.decision.decision == MatchOutcome.Unresolved)
    assert(
      decision.decision.reasonCodes.contains("LLM_ACCEPT_BLOCKED_INSUFFICIENT_ACCEPTANCE_EVIDENCE")
    )
    assert(decision.decisionPath == ResolutionDecisionPath.LlmAdjudicated)
    assert(decision.adjudication.exists(_.preAdjudication.outcome == MatchOutcome.Unresolved))
    assert(result.details.head.adjudication.flatMap(_.response).exists(_.outcome == "accept"))
  }

  test("fake rejection and abstention remain audited while disabled mode never dispatches") {
    Vector("reject" -> MatchOutcome.Rejected, "abstain" -> MatchOutcome.Unresolved).foreach {
      case (outcome, expected) =>
        val (result, calls) = resolve(sample("fake-" + outcome), "fake", outcome)
        assert(calls == 1 && result.decisions.head.decision.decision == expected)
        assert(result.links.isEmpty)
        assert(result.details.head.adjudication.flatMap(_.response).exists(_.outcome == outcome))
    }
    val (disabled, calls) = resolve(sample("disabled"), "disabled", "accept")
    assert(calls == 0 && disabled.fakeCalls == 0 && disabled.links.isEmpty)
    assert(disabled.decisions.head.decision.decision == MatchOutcome.Unresolved)
  }

  test("effective request policy invalidates both offline and live cache identities") {
    val example = sample("cache-binding")
    val features = classified(example).features
    def offline(policy: ResolutionPolicy) = Adjudication
      .request(
        example.candidate,
        example.input,
        policy,
        ResolutionConfig.example,
        features,
        example.input.evidence
      )
      .toOption
      .get
    def live(policy: ResolutionPolicy) = OpenAIResponses
      .request(
        example.candidate,
        example.input,
        policy,
        ResolutionConfig.example,
        IndependentLiveFixtures.config,
        features,
        example.input.evidence
      )
      .toOption
      .get
    val oldRequest = offline(base)
    val revised = offline(bound)
    assert(oldRequest.policyHash == base.fingerprint && revised.policyHash == bound.fingerprint)
    assert(oldRequest.requestHash != revised.requestHash)
    assert(AdjudicationCache.key(oldRequest) != AdjudicationCache.key(revised))
    assert(LiveAdjudicationCache.key(live(base)) != LiveAdjudicationCache.key(live(bound)))
    assert(oldRequest.inputEvidenceHash == revised.inputEvidenceHash)
    assert(oldRequest.responseSchemaHash == revised.responseSchemaHash)
  }

  test("the researcher request revision preserves the existing work eligibility rule") {
    val authors = Vector("Alex Example", "Blair Example", "Casey Example", "Dana Example")
    val a = work("conf/independent/request/work-left", "alpha beta gamma delta", names = authors)
    val b = work(
      "conf/independent/request/work-right",
      "alpha beta gamma delta epsilon",
      names = authors :+ "Emery Example"
    )
    val in =
      ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty).toOption.get
    val p = pair(endpoint(a), endpoint(b))
    val derived =
      DerivedPair(p, Vector.empty, (in.refs(p.left) ++ in.refs(p.right)).distinct.sorted)
    val d = ResolutionEngine.classify(derived, in, base).toOption.get
    // Title 4/5, authors 4/5, year 1, unavailable venue: (.4+.24+.1)/.9.
    assert(d.score.exists(s => math.abs(s - 0.74 / 0.9) < 1e-12))
    assert(d.outcome == MatchOutcome.Unresolved && d.sufficient)
    assert(RequestEligibilityPolicy.eligible(d, ResolutionEntityType.Work, base))
    assert(RequestEligibilityPolicy.eligible(d, ResolutionEntityType.Work, bound, Some(profile)))
  }

  test("canonical held-out overlap is excluded before even an invalid pair could be classified") {
    val frozen = IndependentReviewFixtures.artifacts(
      4,
      ReviewSampling.standard
        .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0)
    )
    val frozenInput = IndependentReviewFixtures.isolated(4).input
    val held = frozen.queue.tasks.find(_.partition == "held-out").get
    val heldDoi = frozenInput.parentWork(held.pair.left).get.doi
    val a = work("conf/independent/request/held-bridge", doi = heldDoi)
    val b = work("conf/independent/request/held-peer")
    val in =
      ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty).toOption.get
    val valid = pair(endpoint(a), endpoint(b))
    val invalid = valid.copy(entityType = ResolutionEntityType.Researcher)
    val candidate = DerivedPair(
      invalid,
      Vector.empty,
      (in.refs(valid.left) ++ in.refs(valid.right)).distinct.sorted
    )
    assert(ResolutionEngine.classify(candidate, in, bound).isLeft)
    val selected = LiveDemo.selectSupplement(
      in,
      CandidatePopulation(Vector(candidate), Vector.empty, Vector.empty),
      frozenInput,
      frozen.queue,
      frozen.split,
      bound,
      Some(profile)
    )
    assert(selected.isRight, selected.toString)
    assert(
      selected.toOption.get.admittedPairs.isEmpty && selected.toOption.get.eligiblePairs.isEmpty
    )
    assert(selected.toOption.get.admission.excludedPairIds == Vector(invalid.pairId))
  }

  test(
    "live synthetic outcomes respect the separate acceptance gate and preserve budget accounting"
  ) {
    val frozen = IndependentReviewFixtures.artifacts(
      4,
      ReviewSampling.standard
        .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0)
    )
    val frozenInput = IndependentReviewFixtures.isolated(4).input
    Vector("accept", "reject", "abstain").foreach { outcome =>
      val example = sample("live-" + outcome)
      val calls = new AtomicInteger(0)
      val cfg = IndependentLiveFixtures.config
      val factory = () =>
        new OpenAITransport {
          def post(body: String, timeoutMs: Int, maxBytes: Int): ProviderHttpResponse = {
            calls.incrementAndGet()
            val request = read[AdjudicationRequest](ujson.read(body)("input").str)
            IndependentLiveFixtures.http(
              IndependentLiveFixtures.envelope(request, Some(response(request, outcome)))
            )
          }
        }
      val ledger = Files
        .createTempDirectory("scholarchain-independent-request-policy-")
        .toRealPath()
        .resolve("budget.json")
      val run = LiveDemo.run(
        example.input,
        population(example),
        frozenInput,
        frozen.queue,
        frozen.split,
        bound,
        ResolutionConfig.example,
        cfg,
        ledger,
        None,
        runId,
        true,
        cfg.approvalId,
        factory,
        true,
        Some(profile)
      )
      assert(run.isRight, run.toString)
      val result = run.toOption.get
      assert(calls.get() == 1 && result.eligiblePairs == 1 && result.traces.size == 1)
      assert(result.traces.head.status == "VALIDATED_LIVE")
      assert(result.budget.exists(_.attempts == 1))
      assert(result.links.isEmpty)
      val expected = if (outcome == "reject") MatchOutcome.Rejected else MatchOutcome.Unresolved
      assert(result.decisions.head.decision.decision == expected)
      assert(result.decisions.head.adjudication.nonEmpty)
      if (outcome == "accept")
        assert(
          result.decisions.head.decision.reasonCodes
            .contains("LLM_ACCEPT_BLOCKED_INSUFFICIENT_ACCEPTANCE_EVIDENCE")
        )
      assert(
        cfg == IndependentLiveFixtures.config,
        "request policy cannot alter approval or budget configuration"
      )
    }
  }

  test(
    "binding mismatches fail before dispatch and missing profile cannot enable revised requests"
  ) {
    val example = sample("binding-refusal")
    val cfg = ResolutionConfig.example
    val mismatch = ResolutionEngine.resolve(
      example.input,
      population(example),
      base,
      cfg,
      "fake",
      None,
      runId,
      instant,
      None,
      Some(profile)
    )
    assert(mismatch.isLeft)
    intercept[IllegalArgumentException] {
      RequestEligibilityPolicy.eligible(
        classified(example),
        ResolutionEntityType.Researcher,
        bound,
        None
      )
    }
    val omitted = ResolutionEngine.resolve(
      example.input,
      population(example),
      bound,
      cfg,
      "fake",
      None,
      runId,
      instant
    )
    assert(omitted.isLeft)
  }

  test(
    "an explicit one-pair pilot cap preserves approval and charges only one of two eligible pairs"
  ) {
    val frozen = IndependentReviewFixtures.artifacts(
      4,
      ReviewSampling.standard
        .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0)
    )
    val frozenInput = IndependentReviewFixtures.isolated(4).input
    val examples = Vector(sample("cap-first"), sample("cap-second"))
    val input = ResolutionInput
      .create(
        examples.flatMap(_.input.works),
        Vector.empty,
        Vector.empty,
        Vector.empty,
        examples.flatMap(_.input.affiliations)
      )
      .toOption
      .get
    val candidates = CandidatePopulation(
      examples.map { e =>
        val p = e.candidate.pair
        DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
      },
      Vector.empty,
      Vector.empty
    )
    val cfg = IndependentLiveFixtures.config
    val calls = new AtomicInteger(0)
    val factoryCalls = new AtomicInteger(0)
    val factory = () => {
      factoryCalls.incrementAndGet()
      new OpenAITransport {
        def post(body: String, timeoutMs: Int, maxBytes: Int): ProviderHttpResponse = {
          calls.incrementAndGet()
          val request = read[AdjudicationRequest](ujson.read(body)("input").str)
          IndependentLiveFixtures.http(
            IndependentLiveFixtures.envelope(request, Some(response(request, "abstain")))
          )
        }
      }
    }
    val directory = Files.createTempDirectory("scholarchain-independent-pilot-cap-").toRealPath()
    val ledger = directory.resolve("budget.json")
    val selected = LiveDemo.selectSupplement(
      input,
      candidates,
      frozenInput,
      frozen.queue,
      frozen.split,
      bound,
      Some(profile)
    )
    assert(selected.isRight && selected.toOption.get.eligiblePairs.size == 2)
    val run = LiveDemo.run(
      input,
      candidates,
      frozenInput,
      frozen.queue,
      frozen.split,
      bound,
      ResolutionConfig.example,
      cfg,
      ledger,
      None,
      runId,
      true,
      cfg.approvalId,
      factory,
      true,
      Some(profile),
      Some(1)
    )
    assert(run.isRight, run.toString)
    assert(calls.get() == 1 && factoryCalls.get() == 1)
    assert(run.toOption.get.traces.size == 1 && run.toOption.get.budget.exists(_.attempts == 1))
    assert(run.toOption.get.links.isEmpty)
    assert(cfg.fingerprint == IndependentLiveFixtures.config.fingerprint)
    val invalidLedger = directory.resolve("invalid-budget.json")
    val invalid = LiveDemo.run(
      input,
      candidates,
      frozenInput,
      frozen.queue,
      frozen.split,
      bound,
      ResolutionConfig.example,
      cfg,
      invalidLedger,
      None,
      runId,
      true,
      cfg.approvalId,
      factory,
      true,
      Some(profile),
      Some(0)
    )
    assert(invalid.isLeft && !Files.exists(invalidLedger))
    assert(calls.get() == 1 && factoryCalls.get() == 1)
  }

  test(
    "live preview CLI rejects zero oversized and noninteger pair caps before input loading or writes"
  ) {
    val directory =
      Files.createTempDirectory("scholarchain-independent-pilot-cli-cap-").toRealPath()
    val source = directory.resolve("source-config.json")
    val live = directory.resolve("live-config.json")
    Files.writeString(source, write(ResolutionConfig.example))
    Files.writeString(live, write(IndependentLiveFixtures.config))
    val output = directory.resolve("never-created-output")
    val required = Vector(
      "--input" -> directory.resolve("missing-input").toString,
      "--frozen-input" -> directory.resolve("missing-frozen").toString,
      "--queue" -> directory.resolve("missing-queue.json").toString,
      "--split" -> directory.resolve("missing-split.json").toString,
      "--policy" -> directory.resolve("missing-policy.json").toString,
      "--config" -> source.toString,
      "--live-config" -> live.toString,
      "--scope" -> "supplement",
      "--code-revision" -> ("a" * 40),
      "--source-hash" -> ("b" * 64),
      "--output" -> output.toString
    )
    Vector("0", "11", "notinteger").foreach { cap =>
      val args = Array("prepare-live-demo") ++ (required :+ ("--max-pairs" -> cap)).flatMap {
        case (key, value) => Vector(key, value)
      }
      val result = LiveDemoCommands.run(args)
      assert(result.isLeft, cap)
      val error = result.left.toOption.get
      assert(error.contains(if (cap == "notinteger") "notinteger" else "live pair cap"), error)
      assert(!Files.exists(output))
    }
  }
}
