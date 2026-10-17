package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import scala.util.Try
import upickle.default.{ReadWriter, write}

object ReviewTool {
  def exportNew(output: Path): Either[String, Unit] = Try {
    LinkExporter.ensureNew(output).fold(e => throw new IllegalArgumentException(e), identity)
    Files.createDirectories(output)
    Vector("index.html", "guide.txt", "sampling.v1.json").foreach { name =>
      Files.writeString(
        output.resolve(name),
        ResourceText.read("review/" + name),
        UTF_8,
        StandardOpenOption.CREATE_NEW
      )
    }
    ()
  }.toEither.left.map(_.getMessage)
}

/** Explicit offline commands. No command invokes a provider or acquires data. */
object ReviewCommands {
  val help = """Phase 5C review and evaluation readiness:
  build-review-queue --input COMPLETED_PHASE4_RUN --policy POLICY_JSON --config CONFIG_JSON --sampling SAMPLING_JSON --code-revision GIT_SHA40 --source-hash FROZEN_SOURCE_SHA256 --output NEW_DIRECTORY
  export-review-tool --output NEW_DIRECTORY
  import-labels --queue QUEUE_JSON --labels ORIGINAL_CHECKPOINT_JSON --output NEW_DURABLE_VALIDATED_JSON
  prepare-evaluation-predictions --input COMPLETED_PHASE4_RUN --config CONFIG_JSON --queue QUEUE_JSON --predictions COMPLETED_RESOLUTION_RUN --binding PREDICTION_RUN_BINDING_JSON --code-revision GIT_SHA40 --source-hash FROZEN_SOURCE_SHA256 --output NEW_JSON
  evaluate --queue QUEUE_JSON --split SPLIT_JSON --gold VALIDATED_LABELS_JSON --predictions EVALUATION_PREDICTIONS_JSON --partition development|held-out --output NEW_DIRECTORY
  sensitivity --queue QUEUE_JSON --split SPLIT_JSON --gold VALIDATED_LABELS_JSON --predictions EVALUATION_PREDICTIONS_JSON --partition development --thresholds 0.8,0.9 --output NEW_JSON
Standard sampling: 40 development + 200 held-out initial reviews, 10 + 50 reserves.
Code/source hashes are explicit declared freeze metadata; the coordinator must verify them.
Uncertain and missing annotations require additional review, never negative labels.
No labels, accuracy, live provider evidence or final Phase 5E acceptance is created by queue generation.
"""
  private def get[A: ReadWriter](path: String): A = StrictJson
    .file(Path.of(path), 67108864L)
    .flatMap(StrictJson.parse[A])
    .fold(e => throw new IllegalArgumentException(e), identity)
  private def queue(path: String): ReviewQueueDocument = StrictJson
    .file(Path.of(path), 67108864L)
    .flatMap(ReviewQueue.parseQueue)
    .fold(e => throw new IllegalArgumentException(e), identity)
  private def value[A](result: Either[String, A]): A =
    result.fold(e => throw new IllegalArgumentException(e), identity)
  private def safe(inputs: Vector[String], output: Path): Unit =
    inputs.foreach(p => value(PathIsolation.disjoint(Path.of(p), output)))
  private def jsonNew[A: ReadWriter](path: Path, data: A): Unit = {
    value(LinkExporter.ensureNew(path))
    Option(path.toAbsolutePath.getParent).foreach(Files.createDirectories(_))
    Files.writeString(path, write(data, indent = 2) + "\n", UTF_8, StandardOpenOption.CREATE_NEW)
  }
  def run(args: Array[String]): Either[String, String] = Try {
    require(args.nonEmpty, "subcommand required")
    val command = args.head
    val required = command match {
      case "build-review-queue" =>
        Set(
          "--input",
          "--policy",
          "--config",
          "--sampling",
          "--code-revision",
          "--source-hash",
          "--output"
        )
      case "export-review-tool" => Set("--output")
      case "import-labels"      => Set("--queue", "--labels", "--output")
      case "prepare-evaluation-predictions" =>
        Set(
          "--input",
          "--config",
          "--queue",
          "--predictions",
          "--binding",
          "--code-revision",
          "--source-hash",
          "--output"
        )
      case "evaluate" =>
        Set("--queue", "--split", "--gold", "--predictions", "--partition", "--output")
      case "sensitivity" =>
        Set(
          "--queue",
          "--split",
          "--gold",
          "--predictions",
          "--partition",
          "--thresholds",
          "--output"
        )
      case _ => throw new IllegalArgumentException("unsupported subcommand; use --help")
    }
    val rest = args.drop(1).toVector
    require(rest.size % 2 == 0, "each option requires one value")
    val pairs = rest.grouped(2).map(v => v.head -> v(1)).toVector
    require(
      pairs.map(_._1).distinct.size == pairs.size && pairs.map(_._1).toSet == required,
      "unknown, duplicate or missing CLI options; use --help"
    )
    val options = pairs.toMap; val output = Path.of(options("--output"))
    safe(
      options.toVector
        .filter((k, _) =>
          Set(
            "--input",
            "--policy",
            "--config",
            "--sampling",
            "--queue",
            "--labels",
            "--split",
            "--gold",
            "--predictions",
            "--binding"
          )(k)
        )
        .map(_._2),
      output
    )
    value(LinkExporter.ensureNew(output))
    command match {
      case "export-review-tool" =>
        value(ReviewTool.exportNew(output));
        s"Offline tool exported to ${output.resolve("index.html")}. No human reviews were performed."
      case "build-review-queue" =>
        val config = value(ResolutionConfig.load(Path.of(options("--config"))))
        val policy = value(ResolutionPolicy.load(Path.of(options("--policy"))))
        val input = value(InputLoader.load(Path.of(options("--input")), config))
        val population = value(CandidateBuilder.build(input, config))
        val sampling = get[ReviewSampling](options("--sampling"))
        val binding = ReviewBinding(
          input.inputEvidenceHash,
          ReviewQueue.populationHash(population),
          policy.fingerprint,
          config.fingerprint,
          StableIds.sha256Hex(Adjudication.prompt),
          StableIds.sha256Hex(Adjudication.schemaText),
          config.adjudication.provider + "/" + config.adjudication.model + "/" + config.adjudication.modelVersion,
          options("--code-revision"),
          options("--source-hash")
        )
        val artifacts = value(ReviewQueue.build(input, population, sampling, binding))
        value(ReviewQueue.writeNew(output, artifacts))
        s"Blind queue exported: ${artifacts.queue.tasks.count(_.role == "initial")} initial reviews pending; ${artifacts.queue.tasks.count(_.role == "reserve")} reserves; ${artifacts.split.excludedCrossPartition} cross-partition candidates excluded. No labels or predictions were read."
      case "import-labels" =>
        val q = queue(options("--queue"));
        val text = value(StrictJson.file(Path.of(options("--labels")), 67108864L))
        val labels = value(GoldLabels.parse(q, text)); value(GoldLabels.writeNew(output, labels))
        s"Derived validated labels saved; original export unchanged. Counts=${labels.counts}. Uncertain and missing labels require review."
      case "prepare-evaluation-predictions" =>
        val q = queue(options("--queue"));
        val config = value(ResolutionConfig.load(Path.of(options("--config"))))
        val runBinding = get[ReviewBinding](options("--binding"))
        ReviewQueue.checkBinding(runBinding)
        require(
          config.fingerprint == runBinding.configHash && options(
            "--code-revision"
          ) == runBinding.codeRevision && options("--source-hash") == runBinding.sourceTreeHash,
          "prediction code/source/config differs from explicit run binding"
        )
        require(
          ReviewQueue.populationBinding(runBinding) == q.binding,
          "prediction run differs from frozen label population"
        )
        val input = value(InputLoader.load(Path.of(options("--input")), config))
        require(
          input.inputEvidenceHash == q.binding.inputEvidenceHash,
          "prediction source differs from label population"
        )
        val actualPopulation = value(CandidateBuilder.build(input, config))
        require(
          ReviewQueue.populationHash(actualPopulation) == q.binding.candidatePopulationHash,
          "recomputed candidates differ from frozen label population"
        )
        val configuredModel =
          config.adjudication.provider + "/" + config.adjudication.model + "/" + config.adjudication.modelVersion
        require(
          configuredModel == runBinding.modelIdentity,
          "configured model differs from explicit prediction run binding"
        )
        val root = Path.of(options("--predictions"))
        val manifestText = value(StrictJson.file(root.resolve(LinkExporter.manifestName), 1048576))
        val marker = value(StrictJson.file(root.resolve(LinkExporter.markerName), 1024))
        val manifest = value(StrictJson.parse[ResolutionExportManifest](manifestText))
        require(
          marker == StableIds.sha256Hex(
            manifestText
          ) + "\n" && manifest.complete && manifest.schemaVersion == "scholarchain.resolution-export.v1",
          "resolution completion mismatch"
        )
        require(
          manifest.inputEvidenceHash == runBinding.inputEvidenceHash && manifest.policyHash == runBinding.policyHash && manifest.configHash == runBinding.configHash && manifest.promptHash == runBinding.promptHash && manifest.responseSchemaHash == runBinding.responseSchemaHash,
          "resolution manifest differs from explicit prediction run binding"
        )
        require(
          manifest.files.map(_.path).distinct.size == manifest.files.size,
          "duplicate manifest file"
        )
        val contents = manifest.files.map { part =>
          val path = root.resolve(part.path).normalize
          require(
            !Path.of(part.path).isAbsolute && !part.path.split('/').contains("..") && path
              .startsWith(root.normalize),
            "unsafe resolution part path"
          )
          val text = value(StrictJson.file(path, config.maxOutputBytes))
          require(
            text.getBytes(UTF_8).length.toLong == part.bytes && StableIds.sha256Hex(
              text
            ) == part.sha256,
            "resolution part hash mismatch"
          )
          part.path -> text
        }.toMap
        val decisionPaths = (for (
          e <- Vector("work", "researcher");
          o <- Vector("accepted", "rejected", "unresolved", "conflict")
        ) yield s"$e/$o.jsonl")
        val decisions = decisionPaths.flatMap { name =>
          val text = contents.getOrElse(
            name,
            throw new IllegalArgumentException("missing decision partition")
          )
          require(text.isEmpty || text.endsWith("\n"), "incomplete prediction JSONL")
          text.linesIterator.map(line => value(StrictJson.parse[ResolutionDecision](line))).toVector
        }
        decisions.foreach(d =>
          require(
            ResolutionValidation.check(d, input.context).isRight,
            "invalid source-bound prediction"
          )
        )
        val data = value(Evaluation.fromDecisions(q, decisions, runBinding)); jsonNew(output, data)
        s"Prepared ${data.rows.size} frozen queue predictions; no labels read."
      case "evaluate" | "sensitivity" =>
        val q = queue(options("--queue")); val split = get[ReviewSplit](options("--split"));
        val gold = get[ValidatedLabels](options("--gold"));
        val predictions = get[EvaluationPredictions](options("--predictions"))
        if (command == "evaluate") {
          val report = value(
            Evaluation.evaluate(q, split, gold, predictions, options("--partition"), args.toVector)
          )
          Files.createDirectories(output); jsonNew(output.resolve("evaluation.json"), report)
          s"Evaluation readiness report saved. Binary gold=${report.overall.binaryGold}; uncertain/unlabeled requiring review=${report.additionalReviewsNeeded}. This does not establish final Phase 5E acceptance."
        } else {
          val thresholds = options("--thresholds").split(",", -1).toVector.map(_.toDouble)
          val report = value(
            Evaluation.sensitivity(q, split, gold, predictions, options("--partition"), thresholds)
          ); jsonNew(output, report)
          "Development-only hypothetical score-cutoff sensitivity saved; no held-out tuning or provider calls."
        }
    }
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
}
