package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

class IndependentResolutionExportSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  private val config = ResolutionConfig.example
  private val policy = ResolutionPolicy.example

  private def resolved() = {
    val a = work("conf/independent/ExportA", doi = Some("10.5555/independent-export"))
    val b = work("conf/independent/ExportB", doi = a.doi)
    val input = ResolutionInput
      .create(Vector(a, b), Vector.empty, Vector.empty, Vector(candidate(a, b)))
      .toOption
      .get
    val population = CandidateBuilder.build(input, config).toOption.get
    val run = ResolutionEngine
      .resolve(input, population, policy, config, "disabled", None, runId, instant)
      .toOption
      .get
    (input, run)
  }
  private def output(): Path =
    Files.createTempDirectory("scholarchain-independent-export-").toRealPath().resolve("completed")
  private def mutateManifest(path: Path)(f: ujson.Value => Unit): Unit = {
    val manifestPath = path.resolve(LinkExporter.manifestName)
    val value = ujson.read(Files.readString(manifestPath, UTF_8))
    f(value)
    val text = value.render() + "\n"
    Files.writeString(manifestPath, text, UTF_8)
    Files.writeString(
      path.resolve(LinkExporter.markerName),
      StableIds.sha256Hex(text) + "\n",
      UTF_8
    )
  }

  test("typed exports bind all outcome files complete constraints run input and effective policy") {
    val (input, run) = resolved()
    val dir = output()
    val written = LinkExporter.writeNew(dir, run, input, policy, config)
    assert(written.isRight, written.toString)
    val manifest = written.toOption.get
    assert(LinkExporter.verify(dir, config).contains(manifest))
    assert(manifest.runId == runId && manifest.inputEvidenceHash == input.inputEvidenceHash)
    assert(manifest.policyHash == policy.fingerprint && manifest.configHash == config.fingerprint)
    assert(manifest.liveCalls == 0 && manifest.fakeCalls == 0 && manifest.llmMode == "disabled")
    assert(manifest.constraints.map(_.entityType).toSet == ResolutionEntityType.values.toSet)
    ResolutionEntityType.values.foreach { entity =>
      val prefix = if (entity == ResolutionEntityType.Work) "work" else "researcher"
      MatchOutcome.values.foreach(o =>
        assert(
          Files.isRegularFile(
            dir.resolve(s"$prefix/${o.wire.toLowerCase(java.util.Locale.ROOT)}.jsonl")
          )
        )
      )
      val binding = manifest.constraints.find(_.entityType == entity).get
      val text = Files.readString(dir.resolve(binding.path), UTF_8)
      assert(StableIds.sha256Hex(text) == binding.sha256)
      val bundle = CoreJson.parse[ResolutionGroupingConstraints](text).toOption.get
      assert(ResolutionValidation.check(bundle, input.context).isRight)
      assert(
        bundle.coveredEndpoints.toSet == input.endpoints
          .filter(ResolutionIds.entityType(_) == entity)
          .toSet
      )
    }
    assert(run.links.nonEmpty)
    run.links.foreach(l =>
      assert(
        run.decisions.exists(d =>
          d.decisionId == l.decisionId && d.decision.decision == MatchOutcome.Accepted
        )
      )
    )
  }

  test(
    "existing output is rejected without overwriting files and invalid CLI stops before input or cache access"
  ) {
    val (input, run) = resolved()
    val dir = output()
    Files.createDirectory(dir)
    val sentinel = dir.resolve("human-file.txt")
    Files.writeString(sentinel, "preserve me", UTF_8)
    assert(LinkExporter.writeNew(dir, run, input, policy, config).isLeft)
    val cache = dir.resolveSibling("unused-cache")
    val result = Phase5Main.run(
      Array(
        "resolve",
        "--input",
        "/does-not-exist",
        "--policy",
        "/missing-policy",
        "--config",
        "/missing-config",
        "--llm-mode",
        "fake",
        "--cache",
        cache.toString,
        "--output",
        dir.toString
      )
    )
    assert(result.left.toOption.exists(_.contains("output already exists")))
    assert(Files.readString(sentinel, UTF_8) == "preserve me" && !Files.exists(cache))
    val listing = Files.list(dir)
    try assert(listing.count() == 1)
    finally listing.close()
  }

  test(
    "export corruption extra files and omitted constraint bindings cannot pass downstream verification"
  ) {
    val (input, run) = resolved()
    val dir = output()
    assert(LinkExporter.writeNew(dir, run, input, policy, config).isRight)
    Files.writeString(dir.resolve("work/accepted.jsonl"), "corrupt\n", UTF_8)
    assert(LinkExporter.verify(dir, config).isLeft)
    val extra = output()
    assert(LinkExporter.writeNew(extra, run, input, policy, config).isRight)
    Files.writeString(extra.resolve("unknown-extra.json"), "{}", UTF_8)
    assert(LinkExporter.verify(extra, config).isLeft)
    val omitted = output()
    assert(LinkExporter.writeNew(omitted, run, input, policy, config).isRight)
    mutateManifest(omitted)(j => j("constraints") = ujson.Arr())
    assert(
      LinkExporter.verify(omitted, config).isLeft,
      "a self-consistent completion hash cannot replace required complete constraint bindings"
    )
    val duplicate = output()
    assert(LinkExporter.writeNew(duplicate, run, input, policy, config).isRight)
    mutateManifest(duplicate) { j =>
      j("constraints").arr += ujson.read(j("constraints")(0).render())
    }
    assert(LinkExporter.verify(duplicate, config).isLeft)
  }

  test("export boundary rejects an unaccepted link and incomplete or misgrounded constraints") {
    val (input, run) = resolved()
    val unresolved = run.decisions.find(_.decision.decision != MatchOutcome.Accepted).get
    val forged = ResolutionAcceptedLink(
      ResolutionContracts.schemaVersion,
      unresolved.pair,
      unresolved.decisionId,
      policy.policyVersion,
      policy.fingerprint,
      runId,
      unresolved.decision.provenance
    )
    assert(
      LinkExporter
        .writeNew(output(), run.copy(links = run.links :+ forged), input, policy, config)
        .isLeft
    )
    val workConstraints = run.constraints.find(_.entityType == ResolutionEntityType.Work).get
    val partial = run.constraints.map(c =>
      if (c.entityType == ResolutionEntityType.Work)
        workConstraints.copy(authoritativeIdentifiers = Vector.empty)
      else c
    )
    assert(
      LinkExporter.writeNew(output(), run.copy(constraints = partial), input, policy, config).isLeft
    )
    val noLinks = run.copy(links = Vector.empty)
    assert(
      LinkExporter.writeNew(output(), noLinks, input, policy, config).isLeft,
      "every accepted decision requires exactly its accepted link"
    )
    val a = work("conf/independent/ExportConflictA", doi = Some("10.5555/export-conflict-a"))
    val b = work("conf/independent/ExportConflictB", doi = Some("10.5555/export-conflict-b"))
    val conflictInput = ResolutionInput
      .create(Vector(a, b), Vector.empty, Vector.empty, Vector(candidate(a, b)))
      .toOption
      .get
    val conflictPopulation = CandidateBuilder.build(conflictInput, config).toOption.get
    val conflictRun = ResolutionEngine
      .resolve(conflictInput, conflictPopulation, policy, config, "disabled", None, runId, instant)
      .toOption
      .get
    assert(conflictRun.constraints.exists(_.cannotLinks.nonEmpty))
    val omittedConflicts = conflictRun.copy(constraints =
      conflictRun.constraints.map(_.copy(cannotLinks = Vector.empty))
    )
    assert(
      LinkExporter.writeNew(output(), omittedConflicts, conflictInput, policy, config).isLeft,
      "the complete constraint bundle cannot omit an emitted conflict decision"
    )
  }

  test("equivalent disabled reruns preserve substantive typed decisions and constraint bytes") {
    val (input, first) = resolved()
    val population = CandidateBuilder.build(input, config).toOption.get
    val second = ResolutionEngine
      .resolve(input, population, policy, config, "disabled", None, runId, instant)
      .toOption
      .get
    assert(first == second)
    val a = output(); val b = output()
    val ma = LinkExporter.writeNew(a, first, input, policy, config).toOption.get
    val mb = LinkExporter.writeNew(b, second, input, policy, config).toOption.get
    assert(ma == mb)
    ma.files.foreach(f =>
      assert(
        Files.readString(a.resolve(f.path), UTF_8) == Files.readString(b.resolve(f.path), UTF_8)
      )
    )
  }

  test("N3 CLI rejects nested input output and cache paths before creating or changing anything") {
    val dir = Files.createTempDirectory("scholarchain-independent-path-isolation-").toRealPath()
    val input = dir.resolve("input")
    Files.createDirectory(input)
    Files.writeString(input.resolve("source.txt"), "immutable input", UTF_8)
    val output = dir.resolve("output")
    val policyFile = dir.resolve("policy.json")
    val configFile = dir.resolve("config.json")
    Files.writeString(policyFile, upickle.default.write(policy), UTF_8)
    Files.writeString(configFile, upickle.default.write(config), UTF_8)
    def invoke(in: Path, out: Path, cache: Path) = Phase5Main.run(
      Array(
        "resolve",
        "--input",
        in.toString,
        "--policy",
        policyFile.toString,
        "--config",
        configFile.toString,
        "--llm-mode",
        "fake",
        "--output",
        out.toString,
        "--cache",
        cache.toString
      )
    )
    val cases = Vector(
      (input, input.resolve("nested-output"), dir.resolve("cache-a")),
      (input, output, input.resolve("nested-cache")),
      (input, output, output.resolve("nested-cache")),
      (
        input,
        input.resolveSibling("cache-root").resolve("nested-output"),
        dir.resolve("cache-root")
      )
    )
    cases.foreach { case (in, out, cache) =>
      val result = invoke(in, out, cache)
      assert(result.isLeft)
      assert(
        result.left.toOption.exists(e =>
          e.toLowerCase(java.util.Locale.ROOT).contains("overlap") ||
            e.toLowerCase(java.util.Locale.ROOT).contains("disjoint")
        ),
        result.toString
      )
      assert(!Files.exists(out) && !Files.exists(cache))
      assert(Files.readString(input.resolve("source.txt"), UTF_8) == "immutable input")
    }
  }
}
