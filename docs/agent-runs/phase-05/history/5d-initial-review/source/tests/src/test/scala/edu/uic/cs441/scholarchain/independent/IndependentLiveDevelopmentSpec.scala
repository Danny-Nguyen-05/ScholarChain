package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

/** Development/demo admission is evidence-only; no gold labels, transport or real credentials. */
class IndependentLiveDevelopmentSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*
  private lazy val population = mixed(20)
  private lazy val frozen = ReviewQueue
    .build(
      population.input,
      population.candidates,
      ReviewSampling.standard
        .copy(development = 2, heldOut = 4, developmentReserve = 0, heldOutReserve = 0),
      binding(population)
    )
    .toOption
    .get

  test("live demo admission excludes every held-out group before eligibility classification") {
    val selected = LiveDemo.select(
      population.input,
      population.candidates,
      frozen.queue,
      frozen.split,
      ResolutionPolicy.example
    )
    assert(selected.isRight, selected.toString)
    val admitted = selected.toOption.get.admittedPairs
    val held = frozen.queue.tasks.filter(_.partition == "held-out").map(_.pair.pairId).toSet
    assert(held.nonEmpty && admitted.map(_.pair.pairId).toSet.intersect(held).isEmpty)
    admitted.foreach { d =>
      assert(
        frozen.split
          .pairGroups(d.pair.pairId)
          .forall(g => frozen.split.partitions(g) == "development")
      )
    }
    assert(
      selected.toOption.get.eligiblePairs.forall(p =>
        admitted.exists(_.pair.pairId == p.pair.pairId)
      )
    )
  }

  test(
    "a changed or held-out-only candidate population is refused rather than admitted as a demo"
  ) {
    val held = frozen.queue.tasks.filter(_.partition == "held-out").map(_.pair.pairId).toSet
    val changed = population.candidates.copy(pairs =
      population.candidates.pairs.filter(p => held(p.pair.pairId))
    )
    assert(changed.pairs.nonEmpty)
    assert(
      LiveDemo
        .select(population.input, changed, frozen.queue, frozen.split, ResolutionPolicy.example)
        .isLeft
    )
  }

  test(
    "zero eligible and explicitly disabled demo runs do not create ledger or inspect credentials"
  ) {
    val factoryCalls = new AtomicInteger(0)
    val reads = new AtomicInteger(0)
    val factory = () => {
      factoryCalls.incrementAndGet();
      new OpenAIHttpTransport(() => { reads.incrementAndGet(); None })
    }
    val directory = Files.createTempDirectory("scholarchain-independent-no-live-demo-").toRealPath()
    Vector(false, true).foreach { enabled =>
      val ledger = directory.resolve(s"ledger-$enabled.json")
      val run = LiveDemo.run(
        population.input,
        population.candidates,
        population.input,
        frozen.queue,
        frozen.split,
        ResolutionPolicy.example,
        ResolutionConfig.example,
        IndependentLiveFixtures.config.copy(approved = false),
        ledger,
        None,
        IndependentResolutionFixtures.runId,
        enabled,
        "not-approved",
        factory
      )
      assert(run.isRight, run.toString)
      assert(
        run.toOption.get.eligiblePairs == 0 && run.toOption.get.traces.isEmpty && run.toOption.get.budget.isEmpty
      )
      assert(!Files.exists(ledger))
    }
    assert(factoryCalls.get() == 0 && reads.get() == 0)
  }

  test(
    "supplemental admission excludes a whole transitive identity component linked to held-out evidence"
  ) {
    import IndependentResolutionFixtures.*
    val held = frozen.queue.tasks
      .find(t => t.partition == "held-out" && t.pair.entityType == ResolutionEntityType.Work)
      .get
    val heldDoi = population.input.parentWork(held.pair.left).get.doi
    val bridge = work(
      "conf/independent/live-supplement/HeldBridge",
      title = "Supplemental held-out bridge",
      doi = heldDoi,
      orcids = Map(1 -> orcidA)
    )
    val friend = work(
      "conf/independent/live-supplement/TransitiveFriend",
      title = "Supplemental transitive identity",
      orcids = Map(1 -> orcidA)
    )
    val other = work(
      "conf/independent/live-supplement/SafeA",
      title = "Safe independent supplemental evidence A"
    )
    val safe = work(
      "conf/independent/live-supplement/SafeB",
      title = "Safe independent supplemental evidence B"
    )
    val in = ResolutionInput
      .create(Vector(bridge, friend, other, safe), Vector.empty, Vector.empty, Vector.empty)
      .toOption
      .get
    def candidate(a: WorkRecord, b: WorkRecord) = {
      val p = pair(endpoint(a), endpoint(b))
      DerivedPair(p, Vector.empty, (in.refs(p.left) ++ in.refs(p.right)).distinct.sorted)
    }
    val forbidden = candidate(friend, other)
    val allowed = candidate(other, safe)
    val pop = CandidatePopulation(Vector(forbidden, allowed), Vector.empty, Vector.empty)
    val selected = LiveDemo.selectSupplement(
      in,
      pop,
      population.input,
      frozen.queue,
      frozen.split,
      ResolutionPolicy.example
    )
    assert(selected.isRight, selected.toString)
    assert(selected.toOption.get.admittedPairs.map(_.pair.pairId) == Vector(allowed.pair.pairId))
    assert(selected.toOption.get.admission.excludedPairIds.contains(forbidden.pair.pairId))
    assert(selected.toOption.get.admission.supplemental)
    assert(selected.toOption.get.admission.frozenInputHash == population.input.inputEvidenceHash)
  }
  private def eligibleFixture() = {
    import IndependentResolutionFixtures.*
    val works = (0 until 4).toVector.flatMap(i =>
      Vector(
        work(
          s"conf/independent/live-entry/$i/left",
          title = s"alpha beta $i",
          names = Vector.empty
        ),
        work(
          s"conf/independent/live-entry/$i/right",
          title = s"alpha gamma $i",
          names = Vector.empty
        )
      )
    )
    val in = ResolutionInput.create(works, Vector.empty, Vector.empty, Vector.empty).toOption.get
    val pairs = works
      .grouped(2)
      .map { ws =>
        val p = pair(endpoint(ws.head), endpoint(ws(1)))
        DerivedPair(p, Vector.empty, (in.refs(p.left) ++ in.refs(p.right)).distinct.sorted)
      }
      .toVector
    val pop = CandidatePopulation(pairs, Vector.empty, Vector.empty)
    val base = ResolutionPolicy.example
    val policy = base.copy(work =
      base.work.copy(
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
    val synthetic = Population(in, pop)
    val queue = ReviewQueue
      .build(
        in,
        pop,
        ReviewSampling.standard
          .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0),
        binding(synthetic).copy(policyHash = policy.fingerprint)
      )
      .toOption
      .get
    (in, pop, policy, queue)
  }

  test(
    "enabled synthetic demo dispatches only eligible development pairs and preserves independent pre-model scores"
  ) {
    val (in, pop, policy, q) = eligibleFixture()
    val cfg = IndependentLiveFixtures.config
    val factoryCalls = new AtomicInteger(0)
    val calls = new AtomicInteger(0)
    val requested = scala.collection.mutable.ArrayBuffer.empty[String]
    val factory = () => {
      factoryCalls.incrementAndGet()
      new OpenAITransport {
        def post(body: String, timeout: Int, maxBytes: Int): ProviderHttpResponse = {
          calls.incrementAndGet()
          val request = upickle.default.read[AdjudicationRequest](ujson.read(body)("input").str)
          requested.synchronized { requested += request.pairId }
          IndependentLiveFixtures.http(IndependentLiveFixtures.envelope(request))
        }
      }
    }
    val ledger = Files
      .createTempDirectory("scholarchain-independent-enabled-demo-")
      .toRealPath()
      .resolve("ledger.json")
    val result = LiveDemo.run(
      in,
      pop,
      in,
      q.queue,
      q.split,
      policy,
      ResolutionConfig.example,
      cfg,
      ledger,
      None,
      IndependentResolutionFixtures.runId,
      true,
      cfg.approvalId,
      factory
    )
    assert(result.isRight, result.toString)
    val actual = result.toOption.get
    val held = q.queue.tasks.filter(_.partition == "held-out").map(_.pair.pairId).toSet
    assert(actual.eligiblePairs == 1 && calls.get() == 1 && factoryCalls.get() == 1)
    assert(requested.toSet.intersect(held).isEmpty)
    assert(
      actual.decisions.size == 1 && actual.decisions.head.decision.decision == MatchOutcome.Accepted
    )
    val audit = actual.decisions.head
    assert(math.abs(audit.decision.confidence - 0.75) < 1e-12)
    assert(
      audit.adjudication.exists(a =>
        a.mode == ResolutionAdjudicationMode.Live && a.reportedConfidence == 0.7 && a.preAdjudication.score
          .contains(0.75)
      )
    )
    assert(
      actual.budget.exists(b =>
        b.attempts == 1 && b.observedInputTokens == 120 && b.unknownUsageAttempts == 0
      )
    )
    assert(
      actual.admission.queueHash == q.queue.queueHash && actual.admission.excludedPairIds.toSet
        .intersect(held) == held
    )
  }

  test(
    "disabled or wrong-approval enabled demo with eligible evidence never initializes transport"
  ) {
    val (in, pop, policy, q) = eligibleFixture()
    val cfg = IndependentLiveFixtures.config
    val calls = new AtomicInteger(0)
    val factory = () => {
      calls.incrementAndGet(); throw new IllegalStateException("must never construct transport")
    }
    val root = Files.createTempDirectory("scholarchain-independent-demo-admission-").toRealPath()
    val disabled = LiveDemo.run(
      in,
      pop,
      in,
      q.queue,
      q.split,
      policy,
      ResolutionConfig.example,
      cfg.copy(approved = false),
      root.resolve("disabled.json"),
      None,
      IndependentResolutionFixtures.runId,
      false,
      "not-approved",
      factory
    )
    assert(
      disabled.isRight && disabled.toOption.get.eligiblePairs == 1 && disabled.toOption.get.traces.isEmpty
    )
    val wrongApproval = LiveDemo.run(
      in,
      pop,
      in,
      q.queue,
      q.split,
      policy,
      ResolutionConfig.example,
      cfg,
      root.resolve("wrong-approval.json"),
      None,
      IndependentResolutionFixtures.runId,
      true,
      "not-the-recorded-approval",
      factory
    )
    assert(wrongApproval.isLeft && calls.get() == 0)
    assert(
      !Files.exists(root.resolve("disabled.json")) && !Files.exists(
        root.resolve("wrong-approval.json")
      )
    )
  }

}
