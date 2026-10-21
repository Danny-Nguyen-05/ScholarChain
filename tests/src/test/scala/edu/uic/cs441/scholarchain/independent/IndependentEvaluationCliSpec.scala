package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}

/** Synthetic end-to-end CLI inputs; these annotations are never human-review evidence. */
class IndependentEvaluationCliSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  import IndependentReviewFixtures.{annotation, checkpoint}

  private final case class Fixture(
      root: Path,
      input: Path,
      resolution: Path,
      config: Path,
      queue: Path,
      binding: Path,
      artifacts: ReviewArtifacts,
      predictions: EvaluationPredictions,
      gold: ValidatedLabels
  ) {
    def prepare(out: Path): Either[String, String] = ReviewCommands.run(
      Array(
        "prepare-evaluation-predictions",
        "--input",
        input.toString,
        "--config",
        config.toString,
        "--queue",
        queue.toString,
        "--predictions",
        resolution.toString,
        "--binding",
        binding.toString,
        "--code-revision",
        "e" * 40,
        "--source-hash",
        "f" * 64,
        "--output",
        out.toString
      )
    )
  }

  private def fixture(): Fixture = {
    val root = Files.createTempDirectory("scholarchain-independent-evaluation-cli-").toRealPath()
    val works = (0 until 24).toVector.flatMap { i =>
      val name = s"Ari Unique${('a' + i).toChar}"
      Vector("Left", "Right").map(side =>
        work(
          s"conf/independent/evaluation/$i$side",
          title = s"Synthetic evaluation pair $i",
          names = Vector(name),
          doi = Some(s"10.5555/independent-evaluation-$i")
        )
      )
    }
    val candidates = works
      .grouped(2)
      .zipWithIndex
      .map { (w, i) =>
        val c = candidate(w.head, w(1), s"independent:$i")
        c.copy(provenance = c.provenance.copy(datasetSnapshot = "hadoop-prep"))
      }
      .toVector
    val prep = IndependentCompletedPrepFixture.create(works, candidates)
    val config = ResolutionConfig.example
    val policy = ResolutionPolicy.example
    val input = InputLoader.load(prep, config).fold(e => fail(e), identity)
    // Each pair shares its own DOI/title, while every cross-pair leakage anchor is disjoint.
    // Four title tokens deliberately stay below the six-token near-title anchor threshold.
    val pairAnchors = input.works
      .groupBy(_.doi)
      .values
      .map { pairWorks =>
        val refs = pairWorks.map(w => ResolutionInput.ref(w.provenance)).toSet
        input.endpoints
          .filter(e => refs(ResolutionIds.observation(e)))
          .flatMap(e => ReviewQueue.leakageAnchors(e, input))
          .toSet
      }
      .toVector
    for (i <- pairAnchors.indices; j <- (i + 1) until pairAnchors.size)
      assert(
        pairAnchors(i).intersect(pairAnchors(j)).isEmpty,
        "synthetic pairs must be independent leakage groups"
      )
    val population = CandidateBuilder.build(input, config).fold(e => fail(e), identity)
    val binding = ReviewBinding(
      input.inputEvidenceHash,
      ReviewQueue.populationHash(population),
      policy.fingerprint,
      config.fingerprint,
      StableIds.sha256Hex(Adjudication.prompt),
      StableIds.sha256Hex(Adjudication.schemaText),
      s"${config.adjudication.provider}/${config.adjudication.model}/${config.adjudication.modelVersion}",
      "e" * 40,
      "f" * 64
    )
    val artifacts = ReviewQueue
      .build(
        input,
        population,
        ReviewSampling.standard
          .copy(development = 4, heldOut = 4, developmentReserve = 2, heldOutReserve = 2),
        binding
      )
      .fold(e => fail(e), identity)
    val run = ResolutionEngine
      .resolve(input, population, policy, config, "disabled", None, runId, instant)
      .fold(e => fail(e), identity)
    val resolution = root.resolve("resolution")
    assert(LinkExporter.writeNew(resolution, run, input, policy, config).isRight)
    val predictions = Evaluation.fromDecisions(artifacts.queue, run.decisions, binding).toOption.get
    val annotations =
      artifacts.queue.tasks.filter(_.role == "initial").map(t => annotation(t, "same"))
    val gold = GoldLabels
      .parse(artifacts.queue, write(checkpoint(artifacts.queue, annotations)))
      .toOption
      .get
    val configPath = root.resolve("config.json")
    val queuePath = root.resolve("queue.json")
    val bindingPath = root.resolve("binding.json")
    Files.writeString(configPath, write(config), UTF_8)
    Files.writeString(queuePath, write(artifacts.queue), UTF_8)
    Files.writeString(bindingPath, write(binding), UTF_8)
    Fixture(
      root,
      prep,
      resolution,
      configPath,
      queuePath,
      bindingPath,
      artifacts,
      predictions,
      gold
    )
  }

  private def mutateManifest(f: Fixture)(change: ujson.Value => Unit): Unit = {
    val path = f.resolution.resolve(LinkExporter.manifestName)
    val json = ujson.read(Files.readString(path, UTF_8))
    change(json)
    val text = json.render() + "\n"
    Files.writeString(path, text, UTF_8)
    Files.writeString(
      f.resolution.resolve(LinkExporter.markerName),
      StableIds.sha256Hex(text) + "\n",
      UTF_8
    )
  }

  test("prediction preparation CLI consumes a completed export without reading labels") {
    val f = fixture()
    val out = f.root.resolve("predictions.json")
    val result = f.prepare(out)
    assert(result.isRight, result.toString)
    val actual = read[EvaluationPredictions](Files.readString(out, UTF_8))
    assert(
      actual.schemaVersion == f.predictions.schemaVersion && actual.binding == f.predictions.binding
    )
    assert(actual.rows.size == f.predictions.rows.size)
    assert(actual.rows.map(_.pairId).distinct.size == actual.rows.size)
    assert(actual.rows.sortBy(_.pairId) == f.predictions.rows.sortBy(_.pairId))
    assert(!Files.exists(f.root.resolve("gold.json")))
  }

  test("prediction preparation CLI refuses incomplete and corrupted exports before publishing") {
    val noMarker = fixture()
    Files.delete(noMarker.resolution.resolve(LinkExporter.markerName))
    val partialOut = noMarker.root.resolve("refused.json")
    assert(noMarker.prepare(partialOut).isLeft && !Files.exists(partialOut))
    val corrupt = fixture()
    Files.writeString(corrupt.resolution.resolve("work/accepted.jsonl"), "corrupt\n", UTF_8)
    val corruptOut = corrupt.root.resolve("refused.json")
    val result = corrupt.prepare(corruptOut)
    assert(result.left.toOption.exists(_.contains("hash mismatch")), result.toString)
    assert(!Files.exists(corruptOut))
  }

  test("prediction preparation CLI rejects a self-consistent manifest with parent traversal") {
    val f = fixture()
    mutateManifest(f)(j => j("files")(0)("path") = "../outside.jsonl")
    val out = f.root.resolve("refused.json")
    val result = f.prepare(out)
    assert(result.left.toOption.exists(_.contains("unsafe resolution part path")), result.toString)
    assert(!Files.exists(out))
  }

  test(
    "sensitivity CLI is development only and leaves reserve labels outside metric denominators"
  ) {
    val f = fixture()
    val split = f.root.resolve("split.json")
    val gold = f.root.resolve("gold.json")
    val predictions = f.root.resolve("predictions.json")
    Files.writeString(split, write(f.artifacts.split), UTF_8)
    Files.writeString(gold, write(f.gold), UTF_8)
    Files.writeString(predictions, write(f.predictions), UTF_8)
    def run(partition: String, out: Path) = ReviewCommands.run(
      Array(
        "sensitivity",
        "--queue",
        f.queue.toString,
        "--split",
        split.toString,
        "--gold",
        gold.toString,
        "--predictions",
        predictions.toString,
        "--partition",
        partition,
        "--thresholds",
        "0.5,0.99",
        "--output",
        out.toString
      )
    )
    val out = f.root.resolve("sensitivity.json")
    assert(run("development", out).isRight)
    val rows = read[Vector[ThresholdSensitivity]](Files.readString(out, UTF_8))
    assert(rows.map(_.threshold) == Vector(0.5, 0.99))
    assert(
      rows.forall(r =>
        r.metrics.tasks == 4 && r.metrics.binaryGold == 4 && r.metrics.unlabeled == 0
      )
    )
    val held = f.root.resolve("held-out-sensitivity.json")
    assert(run("held-out", held).isLeft && !Files.exists(held))
    val report = Evaluation
      .evaluate(f.artifacts.queue, f.artifacts.split, f.gold, f.predictions, "development")
      .toOption
      .get
    assert(report.overall.tasks == 4 && report.additionalReviewsNeeded == 0)
    assert(f.gold.counts("missing") == 4, "only untouched reserves remain unlabelled")
  }
}
