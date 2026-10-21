package edu.uic.cs441.scholarchain.entityresolution

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import java.time.Instant
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class ReviewAnnotation(
    pairId: String,
    entityType: String,
    pairEvidenceHash: String,
    reviewerId: String,
    revisionId: String,
    revision: Int,
    supersedesRevisionId: Option[String],
    label: String,
    note: String,
    annotatedAtUtc: String
) derives ReadWriter
final case class ReviewCheckpoint(
    schemaVersion: String,
    queueId: String,
    queueSchemaVersion: String,
    queueHash: String,
    sourcePopulationHash: String,
    splitHash: String,
    exportedAtUtc: String,
    annotations: Vector[ReviewAnnotation]
) derives ReadWriter
final case class ValidatedLabels(
    schemaVersion: String,
    queueId: String,
    queueHash: String,
    sourcePopulationHash: String,
    splitHash: String,
    originalExportSha256: String,
    checkpoint: ReviewCheckpoint,
    current: Vector[ReviewAnnotation],
    counts: Map[String, Int],
    provenanceLimitation: String
) derives ReadWriter

object GoldLabels {
  val checkpointVersion = "scholarchain.review-checkpoint.v1"
  val validatedVersion = "scholarchain.validated-labels.v1"
  def utc(value: String): Instant = {
    require(value.endsWith("Z"), "UTC timestamp required"); Instant.parse(value)
  }
  def validate(
      queue: ReviewQueueDocument,
      checkpoint: ReviewCheckpoint,
      originalSha256: String
  ): Either[String, ValidatedLabels] = Try {
    ReviewQueue.validateQueue(queue).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      checkpoint.schemaVersion == checkpointVersion && checkpoint.queueId == queue.queueId && checkpoint.queueSchemaVersion == queue.schemaVersion && checkpoint.queueHash == queue.queueHash && checkpoint.sourcePopulationHash == queue.sourcePopulationHash && checkpoint.splitHash == queue.splitHash,
      "mixed or stale queue/checkpoint"
    )
    require(originalSha256.matches("[0-9a-f]{64}"), "original export hash required")
    val exported = utc(checkpoint.exportedAtUtc)
    require(checkpoint.annotations.size <= queue.tasks.size * 100, "revision count bound exceeded")
    require(
      checkpoint.annotations.map(_.revisionId).distinct.size == checkpoint.annotations.size,
      "duplicate revision ID"
    )
    val tasks = queue.tasks.map(t => t.pair.pairId -> t).toMap
    checkpoint.annotations.foreach { a =>
      val t =
        tasks.getOrElse(a.pairId, throw new IllegalArgumentException("unknown annotation pair"))
      require(
        a.entityType == t.pair.entityType.toString && a.pairEvidenceHash == t.evidenceHash,
        "annotation pair/entity/evidence mismatch"
      )
      require(
        a.reviewerId.nonEmpty && a.reviewerId == a.reviewerId.trim && a.reviewerId.length <= 128 && !a.reviewerId
          .exists(_.isControl),
        "human-entered reviewer ID required"
      )
      require(
        a.revisionId.matches("[A-Za-z0-9_-]{1,128}") && a.revision >= 1 && a.revision <= 100,
        "invalid revision identity"
      )
      require(Set("same", "different", "uncertain", "unlabeled")(a.label), "unsupported label")
      require(
        a.note.length <= 2000 && !utc(a.annotatedAtUtc).isAfter(exported),
        "invalid note or timestamp"
      )
    }
    val current = checkpoint.annotations.groupBy(_.pairId).toVector.sortBy(_._1).map { (_, rows) =>
      val history = rows.sortBy(_.revision)
      history.zipWithIndex.foreach { (a, index) =>
        require(
          a.revision == index + 1 && a.supersedesRevisionId == history
            .lift(index - 1)
            .map(_.revisionId),
          "nonlinear, missing or conflicting revision history"
        )
        if (index > 0)
          require(
            !utc(a.annotatedAtUtc).isBefore(utc(history(index - 1).annotatedAtUtc)),
            "revision timestamp goes backwards"
          )
      }
      history.last
    }
    val counts = Vector("same", "different", "uncertain", "unlabeled")
      .map(l => l -> current.count(_.label == l))
      .toMap + ("missing" -> (queue.tasks.size - current.size))
    ValidatedLabels(
      validatedVersion,
      queue.queueId,
      queue.queueHash,
      queue.sourcePopulationHash,
      queue.splitHash,
      originalSha256,
      checkpoint,
      current,
      counts,
      "Reviewer IDs are self-entered provenance, not authentication. Original human exports must be retained and backed up; uncertain is not a negative label."
    )
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
  def parse(queue: ReviewQueueDocument, text: String): Either[String, ValidatedLabels] = StrictJson
    .parse[ReviewCheckpoint](text)
    .flatMap(c => validate(queue, c, edu.uic.cs441.scholarchain.core.StableIds.sha256Hex(text)))
  def verify(queue: ReviewQueueDocument, labels: ValidatedLabels): Either[String, ValidatedLabels] =
    validate(queue, labels.checkpoint, labels.originalExportSha256).flatMap(expected =>
      Either.cond(expected == labels, labels, "validated label derivation changed")
    )
  def writeNew(path: Path, labels: ValidatedLabels): Either[String, Unit] = Try {
    val abs = path.toAbsolutePath.normalize
    require(
      !abs.startsWith(Path.of("target").toAbsolutePath.normalize) && !abs.toString
        .split(java.io.File.separatorChar)
        .contains("target"),
      "labels need a durable path outside target"
    )
    require(!Files.exists(abs), "validated output already exists")
    var ancestor = abs.getParent
    while (ancestor != null) {
      require(!Files.isSymbolicLink(ancestor), "symlink in durable label output path");
      ancestor = ancestor.getParent
    }
    Option(abs.getParent).foreach(Files.createDirectories(_))
    Files.writeString(abs, write(labels, indent = 2) + "\n", UTF_8, StandardOpenOption.CREATE_NEW)
    ()
  }.toEither.left.map(_.getMessage)
}
