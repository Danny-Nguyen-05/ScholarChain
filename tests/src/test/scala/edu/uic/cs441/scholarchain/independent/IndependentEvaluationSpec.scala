package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Hand-computable synthetic matrices; no measured identity accuracy or real human labels are
  * claimed.
  */
class IndependentEvaluationSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*
  private lazy val population = mixed(64)
  private lazy val artifacts = ReviewQueue
    .build(
      population.input,
      population.candidates,
      ReviewSampling.standard
        .copy(development = 20, heldOut = 20, developmentReserve = 0, heldOutReserve = 0),
      binding(population)
    )
    .toOption
    .get
  private def queue = artifacts.queue
  private def split = artifacts.split
  private lazy val groups = queue.tasks
    .filter(_.partition == "development")
    .groupBy(_.pair.entityType.toString)
    .view
    .mapValues(_.sortBy(_.pair.pairId))
    .toMap
  private val outcomes = Vector(
    "ACCEPTED",
    "REJECTED",
    "UNRESOLVED",
    "CONFLICT",
    "ACCEPTED",
    "REJECTED",
    "UNRESOLVED",
    "CONFLICT",
    "MISSING",
    "ACCEPTED"
  )
  private lazy val annotations = groups.toVector.sortBy(_._1).flatMap { (_, tasks) =>
    assert(tasks.size == 10)
    tasks.zipWithIndex.map { (t, i) =>
      annotation(t, if (i < 4 || i == 8) "same" else if (i == 9) "uncertain" else "different")
    }
  }
  private lazy val gold =
    GoldLabels.parse(queue, write(checkpoint(queue, annotations))).toOption.get
  private lazy val predictions = EvaluationPredictions(
    Evaluation.predictionVersion,
    artifacts.generationBinding.get,
    groups.toVector.sortBy(_._1).flatMap { (_, tasks) =>
      tasks.zipWithIndex.filter(_._2 != 8).map { (t, i) =>
        val path =
          if (outcomes(i) == "CONFLICT") "HardConflict"
          else if (i == 0) "ExactIdentifier"
          else if (i == 4) "LlmAdjudicated"
          else "Scored"
        EvaluationPrediction(
          t.pair.pairId,
          t.pair.entityType.toString,
          t.evidenceHash,
          outcomes(i),
          path,
          if (path == "HardConflict") None else Some(0.8),
          if (path == "LlmAdjudicated") "fake-cache" else "disabled"
        )
      }
    }
  )
  private def evaluated(p: EvaluationPredictions = predictions) =
    Evaluation.evaluate(queue, split, gold, p, "development").toOption.get
  private def close(value: Option[Double], expected: Double): Unit =
    assert(value.exists(v => math.abs(v - expected) < 1e-12), s"$value != $expected")

  test(
    "binary acceptance metrics include unresolved conflicts and missing predictions as nonacceptance"
  ) {
    val report = evaluated()
    Vector("Work", "Researcher").foreach { entity =>
      val s = report.byEntity(entity)
      assert((s.tasks, s.binaryGold, s.uncertain, s.unlabeled) == (10, 9, 1, 0))
      assert((s.tp, s.fp, s.fn, s.tn) == (1, 1, 4, 3))
      assert((s.missingPredictions, s.invalidPredictions) == (1, 0))
      close(s.precision, 0.5); close(s.recall, 0.2); close(s.f1, 2.0 / 7)
      close(s.accuracy, 4.0 / 9); close(s.decisiveCoverage, 4.0 / 9)
      close(s.decisiveAccuracy, 0.5); close(s.decisivePrecision, 0.5); close(s.decisiveRecall, 0.5);
      close(s.decisiveF1, 0.5)
      close(s.unresolvedRate, 2.0 / 9); close(s.conflictRate, 2.0 / 9)
    }
    assert(
      (report.overall.tp, report.overall.fp, report.overall.fn, report.overall.tn) == (2, 2, 8, 6)
    )
    assert(report.additionalReviewsNeeded == 2)
    assert(report.falsePositives.size == 2 && report.falseNegatives.size == 8)
    assert(report.falseNegatives.forall(_.evidenceRefs.nonEmpty))
  }

  test("gold by four-outcome tables preserve uncertain missing conflict and exact denominators") {
    val s = evaluated().byEntity("Work")
    Vector("ACCEPTED", "REJECTED", "UNRESOLVED", "CONFLICT", "MISSING").foreach(o =>
      assert(s.fourOutcomeTable("same")(o) == 1)
    )
    Vector("ACCEPTED", "REJECTED", "UNRESOLVED", "CONFLICT").foreach(o =>
      assert(s.fourOutcomeTable("different")(o) == 1)
    )
    assert(s.fourOutcomeTable("different")("MISSING") == 0)
    assert(s.fourOutcomeTable("uncertain")("ACCEPTED") == 1)
    val report = evaluated()
    assert(report.byPath("ExactIdentifier").tp == 2)
    assert(report.byPath("HardConflict").tasks == 4)
    assert(report.byPath("MISSING").fn == 2)
    assert(report.byProvenance("fake-cache").fp == 2)
  }

  test("no-data paths and unlabeled held-out metrics are null instead of manufactured accuracy") {
    val report = evaluated()
    val empty = report.byPath("DeterministicBibliographic")
    assert(empty.tasks == 0 && empty.binaryGold == 0)
    assert(
      Vector(
        empty.precision,
        empty.recall,
        empty.f1,
        empty.accuracy,
        empty.decisiveCoverage,
        empty.decisiveAccuracy
      ).forall(_.isEmpty)
    )
    val held = Evaluation.evaluate(queue, split, gold, predictions, "held-out").toOption.get
    assert(
      held.overall.binaryGold == 0 && held.overall.unlabeled == 20 && held.additionalReviewsNeeded == 20
    )
    assert(held.overall.precision.isEmpty && held.overall.recall.isEmpty)
    assert(ujson.read(write(held))("overall")("precision") == ujson.Null)
  }

  test(
    "invalid predictions stay in denominators and duplicate pairs or foreign bindings are refused"
  ) {
    val first = predictions.rows.find(p => p.outcome == "REJECTED").get
    val invalid = first.copy(pairEvidenceHash = "0" * 64)
    val report = evaluated(
      predictions.copy(rows =
        predictions.rows.map(p => if (p.pairId == first.pairId) invalid else p)
      )
    )
    assert(report.overall.invalidPredictions == 1 && report.overall.binaryGold == 18)
    assert(
      (report.overall.tp, report.overall.fp, report.overall.fn, report.overall.tn) == (2, 2, 8, 6)
    )
    assert(
      Evaluation
        .evaluate(
          queue,
          split,
          gold,
          predictions.copy(rows = predictions.rows :+ predictions.rows.head),
          "development"
        )
        .isLeft
    )
    assert(
      Evaluation
        .evaluate(
          queue,
          split,
          gold,
          predictions.copy(binding = predictions.binding.copy(inputEvidenceHash = "0" * 64)),
          "development"
        )
        .isLeft
    )
  }

  test("development threshold sensitivity is hand-computable and held-out tuning is rejected") {
    val result = Evaluation
      .sensitivity(queue, split, gold, predictions, "development", Vector(0.5, 0.9))
      .toOption
      .get
    // Only scored rows move. Exact-ID accepts, hard conflicts, fake-cache LLM accepts and missing rows stay fixed.
    assert(
      (result(0).metrics.tp, result(0).metrics.fp, result(0).metrics.fn, result(0).metrics.tn) == (
        6,
        6,
        4,
        2
      )
    )
    assert(
      (result(1).metrics.tp, result(1).metrics.fp, result(1).metrics.fn, result(1).metrics.tn) == (
        2,
        2,
        8,
        6
      )
    )
    assert(Evaluation.sensitivity(queue, split, gold, predictions, "held-out", Vector(0.5)).isLeft)
    Vector(Vector(Double.NaN), Vector(-0.1), Vector(1.1), Vector(0.5, 0.5), Vector.empty[Double])
      .foreach(ts =>
        assert(Evaluation.sensitivity(queue, split, gold, predictions, "development", ts).isLeft)
      )
  }
}
