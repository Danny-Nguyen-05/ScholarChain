package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Path

/** Read-only actual-input B2 retention probe. Coordinator owns captured evidence and copied inputs.
  */
object IndependentRetainedReviewInputMain {
  def main(args: Array[String]): Unit = {
    require(
      args.length == 3,
      "original completed input, retained completed input, config JSON required"
    )
    val original = Path.of(args(0)).toRealPath()
    val retained = Path.of(args(1)).toRealPath()
    require(original != retained, "independent source and retained roots required")
    val config = ResolutionConfig
      .load(Path.of(args(2)))
      .fold(e => throw new IllegalArgumentException(e), identity)
    val sourceInput =
      InputLoader.load(original, config).fold(e => throw new IllegalArgumentException(e), identity)
    val retainedInput =
      InputLoader.load(retained, config).fold(e => throw new IllegalArgumentException(e), identity)
    val sourceCandidates = CandidateBuilder
      .build(sourceInput, config)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val retainedCandidates = CandidateBuilder
      .build(retainedInput, config)
      .fold(e => throw new IllegalArgumentException(e), identity)
    require(
      sourceInput.inputEvidenceHash == retainedInput.inputEvidenceHash,
      "retention changed input evidence hash"
    )
    require(
      ReviewQueue.populationHash(sourceCandidates) == ReviewQueue.populationHash(
        retainedCandidates
      ),
      "retention changed candidate population hash"
    )
    require(
      sourceCandidates == retainedCandidates,
      "retention changed candidate rows, diagnostics or derived evidence"
    )
    require(
      sourceInput.works == retainedInput.works && sourceInput.profiles == retainedInput.profiles && sourceInput.activities == retainedInput.activities,
      "retention changed typed observations"
    )
    println(
      ujson
        .Obj(
          "probe" -> "independent-5c-b2-exact-retention",
          "original" -> original.toString,
          "retained" -> retained.toString,
          "inputEvidenceHash" -> retainedInput.inputEvidenceHash,
          "candidatePopulationHash" -> ReviewQueue.populationHash(retainedCandidates),
          "pairs" -> retainedCandidates.pairs.size,
          "works" -> retainedInput.works.size,
          "profiles" -> retainedInput.profiles.size,
          "activities" -> retainedInput.activities.size,
          "allAssertionsPassed" -> true,
          "humanLabelsRead" -> false
        )
        .render(indent = 2)
    )
  }
}
