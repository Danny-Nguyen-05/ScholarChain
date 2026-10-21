package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Synthetic regression for external 5C blocker B1. No real human labels or provider calls. */
class IndependentReviewBindingRepairSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*
  private lazy val population = mixed(20)
  private lazy val sampling = ReviewSampling.standard.copy(
    development = 2,
    heldOut = 4,
    developmentReserve = 0,
    heldOutReserve = 0
  )
  private lazy val p0 = binding(population)
  private lazy val p1 = p0.copy(
    policyHash = "1" * 64,
    configHash = "2" * 64,
    promptHash = "3" * 64,
    responseSchemaHash = "4" * 64,
    modelIdentity = "synthetic-new-provider/new-model/v2",
    codeRevision = "5" * 40,
    sourceTreeHash = "6" * 64
  )
  private def build(run: ReviewBinding) =
    ReviewQueue.build(population.input, population.candidates, sampling, run).toOption.get

  test(
    "B1 identical population sampling and evidence retain queue identity across matcher and code changes"
  ) {
    val original = build(p0)
    val revised = build(p1)
    assert(revised.split == original.split)
    assert(revised.queue.tasks == original.queue.tasks)
    assert(
      revised.queue == original.queue,
      "human labels must bind immutable source/candidate/split/task evidence, not the mutable matcher run"
    )
    val text =
      write(checkpoint(original.queue, Vector(annotation(original.queue.tasks.head, "uncertain"))))
    assert(GoldLabels.parse(revised.queue, text).isRight)
  }

  test(
    "B1 original synthetic labels evaluate predictions from a later run and report that later binding"
  ) {
    val original = build(p0)
    val task = original.queue.tasks.find(_.partition == "development").get
    val gold = GoldLabels
      .parse(original.queue, write(checkpoint(original.queue, Vector(annotation(task, "same")))))
      .toOption
      .get
    val prediction = EvaluationPrediction(
      task.pair.pairId,
      task.pair.entityType.toString,
      task.evidenceHash,
      "ACCEPTED",
      "Scored",
      Some(0.99),
      "disabled"
    )
    val result = Evaluation.evaluate(
      original.queue,
      original.split,
      gold,
      EvaluationPredictions(Evaluation.predictionVersion, p1, Vector(prediction)),
      "development"
    )
    assert(
      result.isRight,
      s"unchanged annotation evidence must survive P0-to-P1 matcher transition: $result"
    )
    assert(result.toOption.get.binding == p1)
    assert(result.toOption.get.overall.tp == 1)
  }
  test(
    "B1 changed input or candidate populations remain invalid despite allowing later matcher settings"
  ) {
    val original = build(p0)
    val task = original.queue.tasks.find(_.partition == "development").get
    val gold = GoldLabels
      .parse(original.queue, write(checkpoint(original.queue, Vector(annotation(task, "same")))))
      .toOption
      .get
    val row = EvaluationPrediction(
      task.pair.pairId,
      task.pair.entityType.toString,
      task.evidenceHash,
      "ACCEPTED",
      "Scored",
      Some(0.99),
      "disabled"
    )
    Vector(p1.copy(inputEvidenceHash = "0" * 64), p1.copy(candidatePopulationHash = "0" * 64))
      .foreach { wrong =>
        assert(
          Evaluation
            .evaluate(
              original.queue,
              original.split,
              gold,
              EvaluationPredictions(Evaluation.predictionVersion, wrong, Vector(row)),
              "development"
            )
            .isLeft
        )
      }
    val alteredEvidence = row.copy(pairEvidenceHash = "0" * 64)
    val invalid = Evaluation
      .evaluate(
        original.queue,
        original.split,
        gold,
        EvaluationPredictions(Evaluation.predictionVersion, p1, Vector(alteredEvidence)),
        "development"
      )
      .toOption
      .get
    assert(
      invalid.overall.invalidPredictions == 1 && invalid.overall.tp == 0 && invalid.overall.fn == 1
    )
    val alteredExport =
      checkpoint(original.queue, Vector(annotation(task, "same").copy(pairEvidenceHash = "0" * 64)))
    assert(GoldLabels.parse(original.queue, write(alteredExport)).isLeft)
    val reordered = population.copy(candidates =
      population.candidates.copy(pairs = population.candidates.pairs.reverse)
    )
    val changed = ReviewQueue
      .build(reordered.input, reordered.candidates, sampling, binding(reordered))
      .toOption
      .get
    assert(
      changed.queue.binding.candidatePopulationHash != original.queue.binding.candidatePopulationHash
    )
    assert(changed.queue.queueHash != original.queue.queueHash)
    assert(GoldLabels.parse(changed.queue, write(gold.checkpoint)).isLeft)
  }

}
