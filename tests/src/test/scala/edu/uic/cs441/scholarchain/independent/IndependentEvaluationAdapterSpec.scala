package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite

/** New 5C evaluation adapter tests; existing 5B matching behavior is not changed. */
class IndependentEvaluationAdapterSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  import IndependentReviewFixtures.{Population, binding}
  private lazy val setup = {
    val works = (0 until 4).toVector.flatMap(i =>
      Vector(
        work(
          s"conf/independent/evaluation-cache/${i}L",
          title = s"alpha beta $i",
          names = Vector.empty
        ),
        work(
          s"conf/independent/evaluation-cache/${i}R",
          title = s"alpha gamma $i",
          names = Vector.empty
        )
      )
    )
    val input = ResolutionInput.create(works, Vector.empty, Vector.empty, Vector.empty).toOption.get
    val pairs = works
      .grouped(2)
      .map { ws =>
        val p = pair(endpoint(ws.head), endpoint(ws(1)))
        DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
      }
      .toVector
    val population = Population(input, CandidatePopulation(pairs, Vector.empty, Vector.empty))
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
    val config = ResolutionConfig.example
    val frozenBinding = binding(population).copy(
      policyHash = policy.fingerprint,
      configHash = config.fingerprint,
      promptHash = sha(Adjudication.prompt),
      responseSchemaHash = sha(Adjudication.schemaText),
      modelIdentity =
        s"${config.adjudication.provider}/${config.adjudication.model}/${config.adjudication.modelVersion}"
    )
    val artifacts = ReviewQueue
      .build(
        input,
        population.candidates,
        ReviewSampling.standard
          .copy(development = 1, heldOut = 1, developmentReserve = 0, heldOutReserve = 0),
        frozenBinding
      )
      .toOption
      .get
    val cache = Files.createTempDirectory("scholarchain-independent-review-adapter-").toRealPath()
    val first = ResolutionEngine
      .resolve(input, population.candidates, policy, config, "fake", Some(cache), runId, instant)
      .toOption
      .get
    val second = ResolutionEngine
      .resolve(input, population.candidates, policy, config, "fake", Some(cache), runId, instant)
      .toOption
      .get
    (input, population, artifacts, first, second)
  }
  private def sha(text: String) = IndependentReviewFixtures.sha256(text)
  private def rebound(d: ResolutionDecision): ResolutionDecision =
    d.copy(decisionId = ResolutionIds.decisionId(d))

  test("evaluation retains genuine offline adapter versus verified cache provenance") {
    val (_, _, artifacts, first, second) = setup
    assert(first.decisions.forall(_.adjudication.exists(a => !a.cacheHit)))
    assert(second.decisions.forall(_.adjudication.exists(_.cacheHit)))
    val fresh =
      Evaluation.fromDecisions(artifacts.queue, first.decisions, artifacts.generationBinding.get)
    val cached =
      Evaluation.fromDecisions(artifacts.queue, second.decisions, artifacts.generationBinding.get)
    assert(fresh.isRight && cached.isRight, s"$fresh $cached")
    assert(fresh.toOption.get.rows.map(_.provenance).toSet == Set("fake"))
    assert(cached.toOption.get.rows.map(_.provenance).toSet == Set("fake-cache"))
  }

  test(
    "evaluation adapter refuses a decision whose endpoints or entity no longer match its frozen pair"
  ) {
    val (input, _, artifacts, first, _) = setup
    val d =
      first.decisions.find(x => artifacts.queue.tasks.exists(_.pair.pairId == x.pair.pairId)).get
    val other = input.endpoints
      .find(e =>
        e != d.pair.left && e != d.pair.right && ResolutionIds.entityType(
          e
        ) == ResolutionEntityType.Work
      )
      .get
    val wrongEndpoint = rebound(d.copy(pair = d.pair.copy(left = other)))
    val wrongEntity =
      rebound(d.copy(pair = d.pair.copy(entityType = ResolutionEntityType.Researcher)))
    Vector(wrongEndpoint, wrongEntity).foreach(changed =>
      assert(
        Evaluation
          .fromDecisions(artifacts.queue, Vector(changed), artifacts.generationBinding.get)
          .isLeft
      )
    )
  }

  test("evaluation adapter refuses prompt or model inconsistent with the declared prediction run") {
    val (_, population, artifacts, first, _) = setup
    val d =
      first.decisions.find(x => artifacts.queue.tasks.exists(_.pair.pairId == x.pair.pairId)).get
    val wrongPrompt =
      rebound(d.copy(adjudication = d.adjudication.map(_.copy(promptHash = "0" * 64))))
    assert(
      Evaluation
        .fromDecisions(artifacts.queue, Vector(wrongPrompt), artifacts.generationBinding.get)
        .isLeft
    )
    val changed = ReviewQueue
      .build(
        population.input,
        population.candidates,
        artifacts.split.sampling,
        artifacts.generationBinding.get
          .copy(modelIdentity = "another-provider/another-model/another-version")
      )
      .toOption
      .get
    assert(
      Evaluation.fromDecisions(changed.queue, first.decisions, changed.generationBinding.get).isLeft
    )
  }
  test(
    "B1 actual later offline matcher and adjudication configuration reuse P0 labels and immutable queue"
  ) {
    val (input, population, original, _, _) = setup
    val oldBinding = original.generationBinding.get
    val base = ResolutionPolicy.example
    val p1Policy = base.copy(work =
      base.work.copy(
        weights = Map("title" -> 1.0, "yearCompatibility" -> 1.0),
        featureGroups = Map("title" -> "bibliography", "yearCompatibility" -> "chronology"),
        requiredGroups = Vector("bibliography", "chronology"),
        minimumIndependentGroupsForAccept = 2,
        supportiveFeatureMin = 0.3,
        bibliographicEnabled = false,
        rejectThreshold = 0.45,
        acceptThreshold = 0.95,
        llmBandMin = 0.6,
        llmBandMax = 0.8
      )
    )
    val baseConfig = ResolutionConfig.example
    val p1Config = baseConfig.copy(adjudication =
      baseConfig.adjudication.copy(
        model = "independent-later-offline-model",
        modelVersion = "v2",
        timeoutMs = baseConfig.adjudication.timeoutMs + 1
      )
    )
    assert(
      ResolutionPolicy.validate(p1Policy).isRight && ResolutionConfig.validate(p1Config).isRight
    )
    val p1Binding = oldBinding.copy(
      policyHash = p1Policy.fingerprint,
      configHash = p1Config.fingerprint,
      modelIdentity =
        s"${p1Config.adjudication.provider}/${p1Config.adjudication.model}/${p1Config.adjudication.modelVersion}",
      codeRevision = "1" * 40,
      sourceTreeHash = "2" * 64
    )
    assert(
      p1Binding.policyHash != oldBinding.policyHash && p1Binding.configHash != oldBinding.configHash
    )
    val later = ReviewQueue
      .build(input, population.candidates, original.split.sampling, p1Binding)
      .toOption
      .get
    assert(later.queue == original.queue && later.split == original.split)
    val labels = original.queue.tasks.map(t => IndependentReviewFixtures.annotation(t, "uncertain"))
    val originalExport =
      upickle.default.write(IndependentReviewFixtures.checkpoint(original.queue, labels))
    val gold = GoldLabels.parse(later.queue, originalExport).toOption.get
    val run = ResolutionEngine
      .resolve(input, population.candidates, p1Policy, p1Config, "fake", None, runId, instant)
      .toOption
      .get
    assert(run.decisions.forall(_.adjudication.exists(_.model == p1Config.adjudication.model)))
    val predictions = Evaluation.fromDecisions(original.queue, run.decisions, p1Binding)
    assert(predictions.isRight, predictions.toString)
    val report = Evaluation.evaluate(
      original.queue,
      original.split,
      gold,
      predictions.toOption.get,
      "development"
    )
    assert(report.isRight, report.toString)
    assert(report.toOption.get.binding == p1Binding)
    assert(gold.originalExportSha256 == IndependentReviewFixtures.sha256(originalExport))
    assert(Evaluation.fromDecisions(original.queue, run.decisions, oldBinding).isLeft)
  }

}
