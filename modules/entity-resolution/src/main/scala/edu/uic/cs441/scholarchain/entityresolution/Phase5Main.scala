package edu.uic.cs441.scholarchain.entityresolution

import java.nio.file.Path
import java.time.Instant
import java.util.UUID
import scala.util.Try

object Phase5Main {
  val help: String = """ScholarChain Phase 5B offline entity resolution and Phase 5C review readiness
Usage:
  resolve --input COMPLETED_PHASE4_RUN --policy POLICY_JSON --config CONFIG_JSON --llm-mode disabled|fake --output NEW_DIRECTORY [--cache CACHE_DIRECTORY] [--request-policy REQUEST_ELIGIBILITY_JSON]
  --help
Every policy/config argument is explicit. Runtime examples are uncalibrated, not evaluated thresholds.
Fake mode uses deterministic abstention fixtures; live adapters and network calls do not exist here.
No existing output directory is overwritten. Source observations are never modified.
""" + ReviewCommands.help + LiveDemoCommands.help
  def run(args: Array[String]): Either[String, String] =
    if (args.toVector == Vector("--help") || args.isEmpty) Right(help)
    else if (Set("prepare-live-demo", "adjudicate-demo")(args.head)) LiveDemoCommands.run(args)
    else if (args.head != "resolve") ReviewCommands.run(args)
    else
      Try {
        require(args.head == "resolve", "unsupported subcommand; use --help")
        val rest = args.drop(1).toVector
        require(rest.size % 2 == 0, "each option requires one value")
        val pairs = rest.grouped(2).map(v => v.head -> v(1)).toVector
        val allowed = Set(
          "--input",
          "--policy",
          "--config",
          "--llm-mode",
          "--output",
          "--cache",
          "--request-policy"
        )
        require(
          pairs.forall(p => allowed(p._1)) && pairs.map(_._1).distinct.size == pairs.size,
          "unknown/duplicate CLI option"
        )
        val options = pairs.toMap
        val required = allowed -- Set("--cache", "--request-policy")
        require(required.subsetOf(options.keySet), "missing required options; use --help")
        require(
          Set("disabled", "fake")(options("--llm-mode")),
          "only disabled and fake are available"
        )
        val output = Path.of(options("--output"))
        PathIsolation
          .validate(Path.of(options("--input")), output, options.get("--cache").map(Path.of(_)))
          .fold(e => throw new IllegalArgumentException(e), identity)
        // Refuse a collision before input work, cache access, fake calls or output creation.
        LinkExporter.ensureNew(output).fold(e => throw new IllegalArgumentException(e), identity)
        val basePolicy = ResolutionPolicy
          .load(Path.of(options("--policy")))
          .fold(e => throw new IllegalArgumentException(e), identity)
        val requestPolicy = options
          .get("--request-policy")
          .map(path =>
            RequestEligibilityPolicy
              .load(Path.of(path))
              .fold(e => throw new IllegalArgumentException(e), identity)
          )
        val policy = requestPolicy
          .map(p =>
            RequestEligibilityPolicy
              .bind(basePolicy, p)
              .fold(e => throw new IllegalArgumentException(e), identity)
          )
          .getOrElse(basePolicy)
        val config = ResolutionConfig
          .load(Path.of(options("--config")))
          .fold(e => throw new IllegalArgumentException(e), identity)
        val input = InputLoader
          .load(Path.of(options("--input")), config)
          .fold(e => throw new IllegalArgumentException(e), identity)
        val candidates = CandidateBuilder
          .build(input, config)
          .fold(e => throw new IllegalArgumentException(e), identity)
        val run = ResolutionEngine
          .resolve(
            input,
            candidates,
            policy,
            config,
            options("--llm-mode"),
            options.get("--cache").map(Path.of(_)),
            "run:" + UUID.randomUUID(),
            Instant.now().toString,
            requestPolicy = requestPolicy
          )
          .fold(e => throw new IllegalArgumentException(e), identity)
        val manifest = LinkExporter
          .writeNew(output, run, input, policy, config, requestPolicy)
          .fold(e => throw new IllegalArgumentException(e), identity)
        s"Resolved ${run.decisions.size} comparisons; fake calls=${manifest.fakeCalls}, live calls=0; output=$output; input=${manifest.inputEvidenceHash}. No human labels, accuracy or calibration is claimed."
      }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
  def main(args: Array[String]): Unit = run(args) match {
    case Right(message) => println(message)
    case Left(error)    => System.err.println("Resolution failed: " + error); sys.exit(2)
  }
}
