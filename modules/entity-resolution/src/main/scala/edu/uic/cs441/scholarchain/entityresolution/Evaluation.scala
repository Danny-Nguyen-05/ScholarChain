package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import scala.util.Try
import upickle.default.ReadWriter

final case class EvaluationPrediction(
    pairId: String,
    entityType: String,
    pairEvidenceHash: String,
    outcome: String,
    path: String,
    score: Option[Double],
    provenance: String
) derives ReadWriter
final case class EvaluationPredictions(
    schemaVersion: String,
    binding: ReviewBinding,
    rows: Vector[EvaluationPrediction]
) derives ReadWriter
final case class EvaluationSlice(
    tasks: Int,
    binaryGold: Int,
    uncertain: Int,
    unlabeled: Int,
    missingPredictions: Int,
    invalidPredictions: Int,
    tp: Int,
    fp: Int,
    fn: Int,
    tn: Int,
    precision: Option[Double],
    recall: Option[Double],
    f1: Option[Double],
    accuracy: Option[Double],
    decisiveCoverage: Option[Double],
    decisiveAccuracy: Option[Double],
    decisivePrecision: Option[Double],
    decisiveRecall: Option[Double],
    decisiveF1: Option[Double],
    unresolvedRate: Option[Double],
    conflictRate: Option[Double],
    fourOutcomeTable: Map[String, Map[String, Int]]
) derives ReadWriter
final case class EvaluationError(
    pairId: String,
    kind: String,
    gold: String,
    outcome: String,
    path: String,
    evidenceHash: String,
    evidenceRefs: Vector[String],
    analysis: String
) derives ReadWriter

/** A separately retained analysis cohort; never mutates labels, tasks or predictions. */
final case class EvaluationExclusions(
    schemaVersion: String,
    queueHash: String,
    labelHash: String,
    reason: String,
    pairIds: Vector[String]
) derives ReadWriter
final case class EvaluationCohort(
    exclusionManifestHash: String,
    reason: String,
    excludedPairIds: Vector[String],
    originalInitialTasks: Int,
    excludedInPartition: Int
) derives ReadWriter
final case class EvaluationReport(
    schemaVersion: String,
    partition: String,
    binding: ReviewBinding,
    queueHash: String,
    splitHash: String,
    labelHash: String,
    predictionHash: String,
    overall: EvaluationSlice,
    byEntity: Map[String, EvaluationSlice],
    byPath: Map[String, EvaluationSlice],
    byProvenance: Map[String, EvaluationSlice],
    outsideQueuePredictions: Int,
    falsePositives: Vector[EvaluationError],
    falseNegatives: Vector[EvaluationError],
    additionalReviewsNeeded: Int,
    limitations: Vector[String],
    seed: String,
    command: Vector[String],
    toolchain: Map[String, String],
    evaluatedAtUtc: String,
    evaluationStatus: String,
    cohort: Option[EvaluationCohort] = None
) derives ReadWriter
final case class ThresholdSensitivity(threshold: Double, metrics: EvaluationSlice)
    derives ReadWriter

/** Candidate-pair classification only. Matching never imports this label-aware code. */
object Evaluation {
  val predictionVersion = "scholarchain.evaluation-predictions.v1"
  val reportVersion = "scholarchain.evaluation-report.v1"
  val cohortReportVersion = "scholarchain.evaluation-report.v2"
  val exclusionsVersion = "scholarchain.evaluation-exclusions.v1"
  val paths = Vector(
    "ExactIdentifier",
    "DeterministicBibliographic",
    "Scored",
    "HardConflict",
    "LlmAdjudicated",
    "MISSING",
    "INVALID"
  )
  val outcomes = Vector("ACCEPTED", "REJECTED", "UNRESOLVED", "CONFLICT", "MISSING", "INVALID")
  private case class Row(
      task: ReviewTask,
      label: String,
      prediction: Option[EvaluationPrediction],
      outcome: String,
      path: String
  )
  private def ratio(a: Int, b: Int): Option[Double] = Option.when(b != 0)(a.toDouble / b)
  private def metrics(rows: Vector[Row]): EvaluationSlice = {
    val binary = rows.filter(r => Set("same", "different")(r.label))
    def count(label: String, accepted: Boolean): Int =
      binary.count(r => r.label == label && (r.outcome == "ACCEPTED") == accepted)
    val tp = count("same", true); val fp = count("different", true); val fn = count("same", false);
    val tn = count("different", false)
    val decisive = binary.filter(r => Set("ACCEPTED", "REJECTED")(r.outcome))
    val dtp = decisive.count(r => r.label == "same" && r.outcome == "ACCEPTED")
    val dfp = decisive.count(r => r.label == "different" && r.outcome == "ACCEPTED")
    val dfn = decisive.count(r => r.label == "same" && r.outcome == "REJECTED")
    val dtn = decisive.count(r => r.label == "different" && r.outcome == "REJECTED")
    val table = Vector("same", "different", "uncertain", "unlabeled")
      .map(l => l -> outcomes.map(o => o -> rows.count(r => r.label == l && r.outcome == o)).toMap)
      .toMap
    EvaluationSlice(
      rows.size,
      binary.size,
      rows.count(_.label == "uncertain"),
      rows.count(_.label == "unlabeled"),
      rows.count(_.outcome == "MISSING"),
      rows.count(_.outcome == "INVALID"),
      tp,
      fp,
      fn,
      tn,
      ratio(tp, tp + fp),
      ratio(tp, tp + fn),
      ratio(2 * tp, 2 * tp + fp + fn),
      ratio(tp + tn, binary.size),
      ratio(decisive.size, binary.size),
      ratio(dtp + dtn, decisive.size),
      ratio(dtp, dtp + dfp),
      ratio(dtp, dtp + dfn),
      ratio(2 * dtp, 2 * dtp + dfp + dfn),
      ratio(binary.count(_.outcome == "UNRESOLVED"), binary.size),
      ratio(binary.count(_.outcome == "CONFLICT"), binary.size),
      table
    )
  }
  private def rows(
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      gold: ValidatedLabels,
      predictions: EvaluationPredictions,
      partition: String
  ): Vector[Row] = {
    ReviewQueue.validate(queue, split).fold(e => throw new IllegalArgumentException(e), identity)
    GoldLabels.verify(queue, gold).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      Set("development", "held-out")(partition),
      "explicit development or held-out partition required"
    )
    ReviewQueue.checkBinding(predictions.binding)
    require(
      predictions.schemaVersion == predictionVersion && ReviewQueue.populationBinding(
        predictions.binding
      ) == queue.binding,
      "predictions do not bind frozen label input/candidate population"
    )
    require(
      predictions.rows.map(_.pairId).distinct.size == predictions.rows.size,
      "duplicate prediction pair"
    )
    val byPair = predictions.rows.map(p => p.pairId -> p).toMap
    val labels = gold.current.map(a => a.pairId -> a.label).toMap
    queue.tasks.filter(t => t.partition == partition && t.role == "initial").map { task =>
      val p = byPair.get(task.pair.pairId)
      val valid = p.exists(p =>
        p.entityType == task.pair.entityType.toString && p.pairEvidenceHash == task.evidenceHash && outcomes
          .take(4)
          .contains(p.outcome) && paths.take(5).contains(p.path) && p.score.forall(s =>
          s.isFinite && s >= 0 && s <= 1
        ) && Set("disabled", "fake", "fake-cache", "live", "live-cache")(p.provenance)
      )
      Row(
        task,
        labels.getOrElse(task.pair.pairId, "unlabeled"),
        p,
        if (p.isEmpty) "MISSING" else if (!valid) "INVALID" else p.get.outcome,
        if (p.isEmpty) "MISSING" else if (!valid) "INVALID" else p.get.path
      )
    }
  }
  def evaluate(
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      gold: ValidatedLabels,
      predictions: EvaluationPredictions,
      partition: String,
      command: Vector[String] = Vector("Evaluation.evaluate (pure API)"),
      exclusions: Option[EvaluationExclusions] = None
  ): Either[String, EvaluationReport] = Try {
    val originalRows = rows(queue, split, gold, predictions, partition)
    val excludedIds = exclusions
      .map { manifest =>
        require(
          manifest.schemaVersion == exclusionsVersion && manifest.queueHash == queue.queueHash && manifest.labelHash == StrictJson
            .hash(gold),
          "exclusion manifest differs from frozen queue/labels"
        )
        require(
          manifest.reason.nonEmpty && manifest.reason == manifest.reason.trim && manifest.reason.length <= 2000 && !manifest.reason
            .exists(_.isControl),
          "bounded exclusion reason required"
        )
        val initial = queue.tasks.filter(_.role == "initial").map(_.pair.pairId).toSet
        require(
          manifest.pairIds.nonEmpty && manifest.pairIds.size <= initial.size && manifest.pairIds.distinct.size == manifest.pairIds.size && manifest.pairIds
            .forall(initial),
          "exclusions must be distinct initial queue pair IDs; unknown and reserve IDs forbidden"
        )
        manifest.pairIds.toSet
      }
      .getOrElse(Set.empty[String])
    val rs = originalRows.filterNot(r => excludedIds(r.task.pair.pairId))
    val cohort = exclusions.map { manifest =>
      EvaluationCohort(
        StrictJson.hash(manifest),
        manifest.reason,
        manifest.pairIds.sorted,
        originalRows.size,
        originalRows.size - rs.size
      )
    }
    def error(r: Row, kind: String) = EvaluationError(
      r.task.pair.pairId,
      kind,
      r.label,
      r.outcome,
      r.path,
      r.task.evidenceHash,
      (r.task.leftEvidence ++ r.task.rightEvidence).map(_.ref).distinct.sorted,
      if (kind == "false-positive")
        "Accepted despite human different label; inspect cited source observations."
      else
        "Human same label was not accepted; unresolved, conflict, missing and invalid predictions count as misses."
    )
    val all = metrics(rs)
    EvaluationReport(
      if (cohort.isDefined) cohortReportVersion else reportVersion,
      partition,
      predictions.binding,
      queue.queueHash,
      split.hash,
      StrictJson.hash(gold),
      StrictJson.hash(predictions),
      all,
      Vector("Work", "Researcher")
        .map(e => e -> metrics(rs.filter(_.task.pair.entityType.toString == e)))
        .toMap,
      paths.map(p => p -> metrics(rs.filter(_.path == p))).toMap,
      Vector("disabled", "fake", "fake-cache", "live", "live-cache", "MISSING", "INVALID")
        .map(p =>
          p -> metrics(
            rs.filter(r =>
              (if (Set("MISSING", "INVALID")(r.outcome)) r.outcome
               else r.prediction.get.provenance) == p
            )
          )
        )
        .toMap,
      predictions.rows.count(p => !queue.tasks.exists(_.pair.pairId == p.pairId)),
      rs.filter(r => r.label == "different" && r.outcome == "ACCEPTED")
        .take(10)
        .map(error(_, "false-positive")),
      rs.filter(r => r.label == "same" && r.outcome != "ACCEPTED")
        .take(10)
        .map(error(_, "false-negative")),
      all.uncertain + all.unlabeled,
      split.residualRisks ++ Vector(
        "Uncertain and unlabeled annotations are excluded from binary gold, never treated as negatives; additional review/adjudication is needed for those counts.",
        "Positive prediction is ACCEPTED; every other outcome including missing/invalid is nonacceptance. Decisive-only metrics are separate.",
        "Reserve tasks are not automatically substituted or included in initial-review metrics. Replacements require a separately recorded human decision.",
        "No accuracy target, calibration, global recall or final Phase 5 acceptance is implied by this report.",
        "Sensitivity is a hypothetical scored acceptance cutoff analysis, not replay of all evidence-sufficiency rules or production policy tuning."
      ),
      split.sampling.seed,
      command,
      Map(
        "javaVersion" -> System.getProperty("java.version"),
        "scalaStandardLibraryVersion" -> scala.util.Properties.versionNumberString
      ),
      java.time.Instant.now().toString,
      "READINESS_REPORT_NOT_FINAL_PHASE_5E_ACCEPTANCE",
      cohort
    )
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
  def sensitivity(
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      gold: ValidatedLabels,
      predictions: EvaluationPredictions,
      partition: String,
      thresholds: Vector[Double]
  ): Either[String, Vector[ThresholdSensitivity]] = Try {
    require(
      partition == "development",
      "threshold selection/sensitivity is development-only; held-out tuning forbidden"
    )
    require(
      thresholds.nonEmpty && thresholds.size <= 100 && thresholds.distinct.size == thresholds.size && thresholds
        .forall(t => t.isFinite && t >= 0 && t <= 1),
      "invalid sensitivity thresholds"
    )
    val baseline = rows(queue, split, gold, predictions, partition)
    thresholds.map { threshold =>
      val changed = baseline.map { r =>
        if (
          r.path == "Scored" && r.prediction
            .flatMap(_.score)
            .nonEmpty && Set("ACCEPTED", "REJECTED", "UNRESOLVED")(r.outcome)
        ) r.copy(outcome = if (r.prediction.get.score.get >= threshold) "ACCEPTED" else "REJECTED")
        else r
      }
      ThresholdSensitivity(threshold, metrics(changed))
    }
  }.toEither.left.map(_.getMessage)
  def fromDecisions(
      queue: ReviewQueueDocument,
      decisions: Vector[ResolutionDecision],
      runBinding: ReviewBinding
  ): Either[String, EvaluationPredictions] = Try {
    ReviewQueue.validateQueue(queue).fold(e => throw new IllegalArgumentException(e), identity)
    ReviewQueue.checkBinding(runBinding)
    require(
      ReviewQueue.populationBinding(runBinding) == queue.binding,
      "prediction run input/candidates differ from label population"
    )
    val tasks = queue.tasks.map(t => t.pair.pairId -> t).toMap
    require(decisions.map(_.pair.pairId).distinct.size == decisions.size, "duplicate decision pair")
    decisions.foreach(d =>
      require(
        d.inputEvidenceHash == runBinding.inputEvidenceHash && d.policyHash == runBinding.policyHash && d.configHash == runBinding.configHash,
        "decision/prediction run binding mismatch"
      )
    )
    val rows = decisions.filter(d => tasks.contains(d.pair.pairId)).map { d =>
      val task = tasks(d.pair.pairId)
      require(
        d.schemaVersion == ResolutionContracts.schemaVersion && d.pair == task.pair && d.decisionId == ResolutionIds
          .decisionId(d),
        "decision pair/audit identity differs from queued evidence"
      )
      require(
        d.evidenceRefs.toSet
          .intersect((task.leftEvidence ++ task.rightEvidence).map(_.ref).toSet)
          .nonEmpty,
        "decision lacks queued source evidence"
      )
      d.adjudication.foreach { a =>
        val identity = a.provider + "/" + a.model + "/" + a.modelVersion.getOrElse("")
        require(
          identity == runBinding.modelIdentity && a.promptHash == runBinding.promptHash && a.responseSchemaVersion == Adjudication.responseSchema && a.generationSettingsHash
            .matches("[0-9a-f]{64}"),
          "adjudication model/prompt/schema differs from prediction run freeze"
        )
      }
      val provenance = d.adjudication
        .map { a =>
          (if (a.mode == ResolutionAdjudicationMode.Live) "live" else "fake") + (if (a.cacheHit)
                                                                                   "-cache"
                                                                                 else "")
        }
        .getOrElse("disabled")
      EvaluationPrediction(
        d.pair.pairId,
        d.pair.entityType.toString,
        task.evidenceHash,
        d.decision.decision.wire,
        d.decisionPath.toString,
        if (d.scoreUnavailableReason.isEmpty) Some(d.decision.confidence) else None,
        provenance
      )
    }
    EvaluationPredictions(predictionVersion, runBinding, rows)
  }.toEither.left.map(_.getMessage)
}
