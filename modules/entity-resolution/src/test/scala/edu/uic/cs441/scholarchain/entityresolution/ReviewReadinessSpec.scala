package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Synthetic readiness checks only: these annotations are never human gold. */
class ReviewReadinessSpec extends AnyFunSuite {
  private lazy val artifacts = {
    val works = (0 until 8).toVector.map(i =>
      ErTestData.work(
        s"conf/review/owner/$i",
        title = s"Independent owner example $i",
        names = Vector.empty
      )
    )
    val input = ResolutionInput.create(works, Vector.empty, Vector.empty, Vector.empty).toOption.get
    val pairs = works
      .grouped(2)
      .map { ws =>
        val p = ResolutionIds
          .pair(ResolutionEntityType.Work, ErTestData.endpoint(ws.head), ErTestData.endpoint(ws(1)))
          .toOption
          .get
        DerivedPair(p, Vector.empty, (input.refs(p.left) ++ input.refs(p.right)).distinct.sorted)
      }
      .toVector
    val population = CandidatePopulation(pairs, Vector.empty, Vector.empty)
    val binding = ReviewBinding(
      input.inputEvidenceHash,
      ReviewQueue.populationHash(population),
      "a" * 64,
      "b" * 64,
      "c" * 64,
      "d" * 64,
      "disabled/no-provider",
      "e" * 40,
      "f" * 64
    )
    ReviewQueue
      .build(
        input,
        population,
        ReviewSampling.standard
          .copy(development = 2, heldOut = 2, developmentReserve = 0, heldOutReserve = 0),
        binding
      )
      .toOption
      .get
  }
  private def checkpoint = ReviewCheckpoint(
    GoldLabels.checkpointVersion,
    artifacts.queue.queueId,
    artifacts.queue.schemaVersion,
    artifacts.queue.queueHash,
    artifacts.queue.sourcePopulationHash,
    artifacts.queue.splitHash,
    "2026-10-16T18:00:00Z",
    Vector.empty
  )
  private def temp = Files.createTempDirectory("scholarchain-review-owner-").toRealPath()

  test(
    "CLI help exposes implemented readiness commands and strict argument failures do not create output"
  ) {
    val text = Phase5Main.run(Array("--help")).toOption.get
    Vector(
      "build-review-queue",
      "export-review-tool",
      "import-labels",
      "prepare-evaluation-predictions",
      "evaluate",
      "sensitivity"
    ).foreach(c => assert(text.contains(c)))
    val output = temp.resolve("invalid")
    assert(
      Phase5Main
        .run(Array("export-review-tool", "--output", output.toString, "--unknown", "x"))
        .isLeft
    )
    assert(!Files.exists(output))
    assert(
      Phase5Main
        .run(Array("export-review-tool", "--output", output.toString, "--output", output.toString))
        .isLeft
    )
  }
  test(
    "tool export creates a self-contained page and guide and refuses to overwrite an existing export"
  ) {
    val output = temp.resolve("tool")
    assert(Phase5Main.run(Array("export-review-tool", "--output", output.toString)).isRight)
    val html = Files.readString(output.resolve("index.html"))
    assert(
      html.contains("connect-src 'none'") && html.contains("textContent") && !html.contains(
        "innerHTML"
      )
    )
    assert(Files.readString(output.resolve("guide.txt")).contains("Uncertain"))
    assert(Phase5Main.run(Array("export-review-tool", "--output", output.toString)).isLeft)
  }
  test(
    "label CLI preserves the original checkpoint byte-for-byte and writes a separate durable derivation"
  ) {
    val root = temp
    val queuePath = root.resolve("queue.json"); val original = root.resolve("original.json");
    val output = root.resolve("validated.json")
    Files.writeString(queuePath, write(artifacts.queue), UTF_8)
    val bytes = (write(checkpoint, indent = 2) + "\n").getBytes(UTF_8)
    Files.write(original, bytes)
    val result = Phase5Main.run(
      Array(
        "import-labels",
        "--queue",
        queuePath.toString,
        "--labels",
        original.toString,
        "--output",
        output.toString
      )
    )
    assert(result.isRight, result.toString)
    assert(Files.readAllBytes(original).toVector == bytes.toVector)
    val labels = StrictJson.parse[ValidatedLabels](Files.readString(output)).toOption.get
    assert(labels.originalExportSha256 == StableIds.sha256Hex(new String(bytes, UTF_8)))
    assert(labels.current.isEmpty && labels.counts("missing") == 4)
    assert(
      Phase5Main
        .run(
          Array(
            "import-labels",
            "--queue",
            queuePath.toString,
            "--labels",
            original.toString,
            "--output",
            original.toString
          )
        )
        .isLeft
    )
  }
  test("validated human exports cannot be placed under target or through a symlink alias") {
    val root = temp
    val labels = GoldLabels.parse(artifacts.queue, write(checkpoint)).toOption.get
    assert(GoldLabels.writeNew(root.resolve("target/validated.json"), labels).isLeft)
    val actual = root.resolve("actual"); Files.createDirectory(actual)
    val alias = root.resolve("alias"); Files.createSymbolicLink(alias, actual)
    assert(GoldLabels.writeNew(alias.resolve("validated.json"), labels).isLeft)
    assert(!Files.exists(actual.resolve("validated.json")))
  }
  test("unlabeled undo preserves revision history and does not become a binary negative") {
    val task = artifacts.queue.tasks.head
    val first = ReviewAnnotation(
      task.pair.pairId,
      "Work",
      task.evidenceHash,
      "synthetic-owner-only",
      "owner-revision-1",
      1,
      None,
      "same",
      "original synthetic note",
      "2026-10-16T17:00:00Z"
    )
    val undo = first.copy(
      revisionId = "owner-revision-2",
      revision = 2,
      supersedesRevisionId = Some(first.revisionId),
      label = "unlabeled",
      annotatedAtUtc = "2026-10-16T17:01:00Z"
    )
    val labels = GoldLabels
      .parse(artifacts.queue, write(checkpoint.copy(annotations = Vector(first, undo))))
      .toOption
      .get
    assert(labels.checkpoint.annotations == Vector(first, undo) && labels.current == Vector(undo))
    assert(labels.counts("same") == 0 && labels.counts("unlabeled") == 1)
    val predictions =
      EvaluationPredictions(
        Evaluation.predictionVersion,
        artifacts.generationBinding.get,
        Vector.empty
      )
    val report = Evaluation
      .evaluate(artifacts.queue, artifacts.split, labels, predictions, task.partition)
      .toOption
      .get
    assert(
      report.overall.binaryGold == 0 && report.overall.tn == 0 && report.overall.accuracy.isEmpty
    )
  }
  test(
    "evaluation CLI writes explicit no-data denominators and frozen provenance without inventing labels"
  ) {
    val root = temp
    val files = Map(
      "queue" -> write(artifacts.queue),
      "split" -> write(artifacts.split),
      "gold" -> write(GoldLabels.parse(artifacts.queue, write(checkpoint)).toOption.get),
      "predictions" -> write(
        EvaluationPredictions(
          Evaluation.predictionVersion,
          artifacts.generationBinding.get,
          Vector.empty
        )
      )
    )
    files.foreach((name, data) => Files.writeString(root.resolve(name + ".json"), data))
    val output = root.resolve("evaluation")
    val args = Array(
      "evaluate",
      "--queue",
      root.resolve("queue.json").toString,
      "--split",
      root.resolve("split.json").toString,
      "--gold",
      root.resolve("gold.json").toString,
      "--predictions",
      root.resolve("predictions.json").toString,
      "--partition",
      "development",
      "--output",
      output.toString
    )
    val result = Phase5Main.run(args)
    assert(result.isRight, result.toString)
    val report = StrictJson
      .parse[EvaluationReport](Files.readString(output.resolve("evaluation.json")))
      .toOption
      .get
    assert(
      report.overall.binaryGold == 0 && report.overall.precision.isEmpty && report.command == args.toVector
    )
    assert(
      report.binding == artifacts.generationBinding.get && report.seed == artifacts.split.sampling.seed && report
        .toolchain("javaVersion")
        .nonEmpty
    )
    assert(report.evaluationStatus == "READINESS_REPORT_NOT_FINAL_PHASE_5E_ACCEPTANCE")
  }
}
