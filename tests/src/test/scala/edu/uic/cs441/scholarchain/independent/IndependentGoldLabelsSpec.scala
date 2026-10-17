package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Automated annotations are synthetic test input and must never be counted as real human review.
  */
class IndependentGoldLabelsSpec extends AnyFunSuite {
  import IndependentReviewFixtures.*
  private lazy val queue = artifacts(
    40,
    ReviewSampling.standard.copy(
      development = 2,
      heldOut = 4,
      developmentReserve = 0,
      heldOutReserve = 0
    )
  ).queue
  private def validate(rows: Vector[ReviewAnnotation]) =
    GoldLabels.parse(queue, write(checkpoint(queue, rows)))

  test("same different uncertain remain separate and missing pairs are counted") {
    val rows = queue.tasks
      .take(3)
      .zip(Vector("same", "different", "uncertain"))
      .map((t, label) => annotation(t, label))
    val validated = validate(rows).toOption.get
    assert(
      validated.counts == Map(
        "same" -> 1,
        "different" -> 1,
        "uncertain" -> 1,
        "unlabeled" -> 0,
        "missing" -> 3
      )
    )
    assert(validated.checkpoint.annotations == rows)
    assert(validated.provenanceLimitation.toLowerCase.contains("not authentication"))
    assert(GoldLabels.verify(queue, validated).isRight)
  }

  test("revision and undo preserve history rather than silently editing the original annotation") {
    val t = queue.tasks.head
    val one = annotation(t, "same")
    val two = annotation(t, "different", 2, Some(one.revisionId))
    val three = annotation(t, "uncertain", 3, Some(two.revisionId))
    val undo = annotation(t, "unlabeled", 4, Some(three.revisionId))
    val original = checkpoint(queue, Vector(one, two, three, undo))
    val bytes = write(original)
    val validated = GoldLabels.parse(queue, bytes).toOption.get
    assert(validated.current == Vector(undo))
    assert(validated.checkpoint == original)
    assert(validated.originalExportSha256 == sha256(bytes))
    assert(validated.counts("unlabeled") == 1 && validated.counts("same") == 0)
  }

  test("duplicate revisions branches gaps and reversed timestamps are rejected") {
    val one = annotation(queue.tasks.head, "same")
    val two = annotation(queue.tasks.head, "different", 2, Some(one.revisionId))
    val bad = Vector(
      Vector(one, one),
      Vector(one, two, two.copy(revisionId = "conflicting-branch")),
      Vector(one, two.copy(revision = 3)),
      Vector(one, two.copy(supersedesRevisionId = None)),
      Vector(one, two.copy(annotatedAtUtc = "2026-10-16T15:59:59Z"))
    )
    bad.foreach(rows => assert(validate(rows).isLeft))
  }

  test("wrong queue source split entity pair and evidence cannot be imported") {
    val one = annotation(queue.tasks.head, "same")
    val original = checkpoint(queue, Vector(one))
    Vector(
      original.copy(queueId = "review-queue:" + "0" * 64),
      original.copy(queueHash = "0" * 64),
      original.copy(sourcePopulationHash = "0" * 64),
      original.copy(splitHash = "0" * 64),
      original.copy(queueSchemaVersion = "scholarchain.review-queue.v999")
    ).foreach(c => assert(GoldLabels.parse(queue, write(c)).isLeft))
    Vector(
      one.copy(pairId = "pair:unknown"),
      one.copy(entityType = "Researcher"),
      one.copy(pairEvidenceHash = "0" * 64)
    ).foreach(a => assert(validate(Vector(a)).isLeft))
  }

  test("unknown keys and unsupported automatic or binary aliases are rejected") {
    val original =
      ujson.read(write(checkpoint(queue, Vector(annotation(queue.tasks.head, "same")))))
    val rootUnknown = mutate(original)(_("extra") = true)
    val nestedUnknown = mutate(original)(_("annotations")(0)("modelSuggested") = "same")
    Vector(rootUnknown, nestedUnknown).foreach(v =>
      assert(GoldLabels.parse(queue, v.render()).isLeft)
    )
    Vector("accepted", "yes", "negative", "UNSURE", "", "0").foreach(label =>
      assert(validate(Vector(annotation(queue.tasks.head, label))).isLeft)
    )
  }

  test("human-entered reviewer provenance notes timestamps and derived counts are validated") {
    val one = annotation(queue.tasks.head, "same")
    Vector(
      one.copy(reviewerId = ""),
      one.copy(reviewerId = " reviewer "),
      one.copy(reviewerId = "name\nheader"),
      one.copy(note = "x" * 2001),
      one.copy(annotatedAtUtc = "2026-10-16T16:00:00-05:00"),
      one.copy(annotatedAtUtc = "2026-10-17T00:00:00Z")
    ).foreach(a => assert(validate(Vector(a)).isLeft))
    val valid = validate(Vector(one)).toOption.get
    assert(GoldLabels.verify(queue, valid.copy(counts = valid.counts.updated("same", 200))).isLeft)
    assert(
      GoldLabels.verify(queue, valid.copy(current = Vector(one.copy(label = "different")))).isLeft
    )
  }
}
