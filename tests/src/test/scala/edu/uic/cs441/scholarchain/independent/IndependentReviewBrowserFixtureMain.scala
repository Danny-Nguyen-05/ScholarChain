package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import upickle.default.write

/** Creates synthetic browser test queues only, never real-review or evaluation evidence. */
object IndependentReviewBrowserFixtureMain {
  def main(args: Array[String]): Unit = {
    require(args.length == 1, "one new ignored target output path required")
    val output = Path.of(args(0)).toAbsolutePath.normalize
    require(
      output.startsWith(
        IndependentResolutionFixtures.root.resolve("target").toAbsolutePath.normalize
      ),
      "synthetic browser output must stay under ignored target"
    )
    val base = IndependentReviewFixtures.mixed(20)
    val observed = base.input.works.zipWithIndex.map { (w, index) =>
      val title =
        s"Synthetic browser observation $index <img src=x onerror=alert('SOURCE_HTML_MUST_NOT_EXECUTE')>"
      w.copy(title = title, normalizedTitle = TextNorm.title(title))
    }
    val input =
      ResolutionInput.create(observed, Vector.empty, Vector.empty, Vector.empty).toOption.get
    val candidates = base.candidates.copy(pairs =
      base.candidates.pairs.map(p =>
        p.copy(evidenceRefs = (input.refs(p.pair.left) ++ input.refs(p.pair.right)).distinct.sorted)
      )
    )
    val population = IndependentReviewFixtures.Population(input, candidates)
    val sampling = ReviewSampling.standard.copy(
      development = 2,
      heldOut = 4,
      developmentReserve = 0,
      heldOutReserve = 0
    )
    val artifacts = ReviewQueue
      .build(input, candidates, sampling, IndependentReviewFixtures.binding(population))
      .fold(e => throw new IllegalArgumentException(e), identity)
    ReviewQueue
      .writeNew(output, artifacts)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val other = ReviewQueue
      .build(
        input,
        candidates,
        sampling.copy(seed = "independent-browser-other-queue"),
        IndependentReviewFixtures.binding(population)
      )
      .toOption
      .get
    val checkpoint = IndependentReviewFixtures.checkpoint(other.queue, Vector.empty)
    Files.writeString(
      output.resolve("other-queue.json"),
      write(other.queue, indent = 2) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    Files.writeString(
      output.resolve("other-queue-checkpoint.json"),
      write(checkpoint, indent = 2) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW
    )
    println(
      s"Synthetic browser fixture: ${artifacts.queue.tasks.size} tasks; no real human labels. Queue: ${output.resolve("queue.json")}"
    )
  }
}
