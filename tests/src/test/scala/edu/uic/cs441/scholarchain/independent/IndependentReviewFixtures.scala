package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.security.MessageDigest

/** Synthetic review-tool test data only. These observations and annotations are never human
  * evidence.
  */
private[independent] object IndependentReviewFixtures {
  import IndependentResolutionFixtures.*

  final case class Population(input: ResolutionInput, candidates: CandidatePopulation)

  /** Disjoint records, identifiers and names let the test calculate group and partition counts
    * independently.
    */
  def isolated(count: Int): Population = {
    val works = (0 until count).toVector.flatMap { i =>
      Vector(
        work(
          s"conf/independent/review/${i}Left",
          title = s"Independent synthetic distributed system $i",
          names = Vector(s"Independent Person $i"),
          doi = Some(s"10.5555/review-left-$i")
        ),
        work(
          s"conf/independent/review/${i}Right",
          title = s"Independent synthetic database method $i",
          names = Vector(s"Different Person $i"),
          doi = Some(s"10.5555/review-right-$i")
        )
      )
    }
    val input = ResolutionInput
      .create(works, Vector.empty, Vector.empty, Vector.empty)
      .fold(error => throw new IllegalArgumentException(error), identity)
    val pairs = works
      .grouped(2)
      .map { members =>
        val p = pair(endpoint(members.head), endpoint(members(1)))
        DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
      }
      .toVector
    Population(input, CandidatePopulation(pairs, Vector.empty, Vector.empty))
  }

  def mixed(count: Int): Population = {
    val base = isolated(count)
    val mentions = base.input.works
      .grouped(2)
      .map { members =>
        val p = pair(mention(members.head), mention(members(1)))
        DerivedPair(
          p,
          Vector.empty,
          (base.input.refs(p.left) ++ base.input.refs(p.right)).distinct.sorted
        )
      }
      .toVector
    base.copy(candidates = base.candidates.copy(pairs = base.candidates.pairs ++ mentions))
  }

  def binding(population: Population): ReviewBinding = ReviewBinding(
    population.input.inputEvidenceHash,
    ReviewQueue.populationHash(population.candidates),
    "a" * 64,
    "b" * 64,
    "c" * 64,
    "d" * 64,
    "disabled/no-provider",
    "e" * 40,
    "f" * 64
  )

  def artifacts(
      count: Int = 640,
      sampling: ReviewSampling = ReviewSampling.standard
  ): ReviewArtifacts = {
    val population = isolated(count)
    ReviewQueue
      .build(population.input, population.candidates, sampling, binding(population))
      .fold(error => throw new IllegalArgumentException(error), identity)
  }

  def annotation(
      task: ReviewTask,
      label: String,
      revision: Int = 1,
      previous: Option[String] = None
  ): ReviewAnnotation =
    ReviewAnnotation(
      task.pair.pairId,
      task.pair.entityType.toString,
      task.evidenceHash,
      "synthetic-automated-test-only",
      s"test-${task.pair.pairId.takeRight(16)}-$revision",
      revision,
      previous,
      label,
      "Synthetic test annotation; not a real human label.",
      "2026-10-16T16:00:00Z"
    )

  def checkpoint(queue: ReviewQueueDocument, rows: Vector[ReviewAnnotation]): ReviewCheckpoint =
    ReviewCheckpoint(
      GoldLabels.checkpointVersion,
      queue.queueId,
      queue.schemaVersion,
      queue.queueHash,
      queue.sourcePopulationHash,
      queue.splitHash,
      "2026-10-16T17:00:00Z",
      rows
    )

  def sha256(value: String): String =
    MessageDigest
      .getInstance("SHA-256")
      .digest(value.getBytes(UTF_8))
      .map(b => f"${b & 255}%02x")
      .mkString

  def mutate(value: ujson.Value)(f: ujson.Value => Unit): ujson.Value = {
    val copied = ujson.read(value.render())
    f(copied)
    copied
  }
}
