package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Independent denominator checks for explicitly disclosed label-assistance exclusions. */
class IndependentEvaluationCohortSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*

  private lazy val artifacts = {
    val population = mixed(64)
    ReviewQueue
      .build(
        population.input,
        population.candidates,
        ReviewSampling.standard
          .copy(development = 6, heldOut = 6, developmentReserve = 2, heldOutReserve = 2),
        binding(population)
      )
      .toOption
      .get
  }
  private lazy val queue = artifacts.queue
  private lazy val development =
    queue.tasks.filter(t => t.role == "initial" && t.partition == "development")
  private lazy val heldOut =
    queue.tasks.filter(t => t.role == "initial" && t.partition == "held-out")
  private lazy val annotations = queue.tasks.filter(_.role == "initial").map { task =>
    annotation(task, if (task == development.head) "different" else "same")
  }
  private lazy val gold =
    GoldLabels.parse(queue, write(checkpoint(queue, annotations))).toOption.get
  private lazy val predictions = EvaluationPredictions(
    Evaluation.predictionVersion,
    artifacts.generationBinding.get,
    queue.tasks.map(t =>
      EvaluationPrediction(
        t.pair.pairId,
        t.pair.entityType.toString,
        t.evidenceHash,
        "ACCEPTED",
        "ExactIdentifier",
        Some(1.0),
        "disabled"
      )
    )
  )
  private lazy val exclusions = EvaluationExclusions(
    "scholarchain.evaluation-exclusions.v1",
    queue.queueHash,
    StrictJson.hash(gold),
    "Synthetic test cohort: omit two explicitly attributed source-assisted reviews.",
    Vector(development.head.pair.pairId, heldOut.head.pair.pairId)
  )
  private def evaluate(excluded: Option[EvaluationExclusions], partition: String = "development") =
    Evaluation.evaluate(queue, artifacts.split, gold, predictions, partition, exclusions = excluded)

  test(
    "excluding an attributed review changes only that cohort denominator and preserves source labels"
  ) {
    val beforeQueue = write(queue)
    val beforeGold = write(gold)
    val beforePredictions = write(predictions)
    val baseline = evaluate(None).toOption.get
    val cohort = evaluate(Some(exclusions)).toOption.get
    assert((baseline.overall.tasks, baseline.overall.tp, baseline.overall.fp) == (6, 5, 1))
    assert(
      (cohort.overall.tasks, cohort.overall.binaryGold, cohort.overall.tp, cohort.overall.fp) == (
        5,
        5,
        5,
        0
      )
    )
    assert(cohort.overall.precision.contains(1.0) && cohort.overall.recall.contains(1.0))
    assert(cohort.queueHash == baseline.queueHash && cohort.labelHash == baseline.labelHash)
    assert(cohort.predictionHash == baseline.predictionHash && cohort.binding == baseline.binding)
    assert(cohort.schemaVersion != baseline.schemaVersion)
    assert(
      cohort.cohort.exists(c =>
        c.excludedInPartition == 1 && c.originalInitialTasks == 6 &&
          c.exclusionManifestHash == StrictJson.hash(
            exclusions
          ) && c.excludedPairIds.toSet == exclusions.pairIds.toSet
      )
    )
    assert(
      write(queue) == beforeQueue && write(gold) == beforeGold && write(
        predictions
      ) == beforePredictions
    )
    val held = evaluate(Some(exclusions), "held-out").toOption.get
    assert((held.overall.tasks, held.overall.tp, held.overall.fp) == (5, 5, 0))
  }

  test(
    "cohort exclusions must bind the exact queue and labels and contain only unique initial pairs"
  ) {
    val reserve = queue.tasks.find(_.role == "reserve").get.pair.pairId
    val invalid = Vector(
      exclusions.copy(schemaVersion = "unknown"),
      exclusions.copy(queueHash = "0" * 64),
      exclusions.copy(labelHash = "0" * 64),
      exclusions.copy(reason = ""),
      exclusions.copy(pairIds = Vector.empty),
      exclusions.copy(pairIds = Vector(exclusions.pairIds.head, exclusions.pairIds.head)),
      exclusions.copy(pairIds = Vector(reserve)),
      exclusions.copy(pairIds = Vector("resolution-pair:not-in-queue"))
    )
    invalid.foreach(e => assert(evaluate(Some(e)).isLeft, e.toString))
  }
}
