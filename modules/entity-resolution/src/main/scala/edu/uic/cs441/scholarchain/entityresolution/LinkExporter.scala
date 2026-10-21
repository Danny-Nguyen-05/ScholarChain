package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardCopyOption, StandardOpenOption}
import java.util.UUID
import scala.jdk.CollectionConverters.*
import scala.util.Try
import upickle.default.{ReadWriter, write}

final case class ResolutionExportFile(path: String, bytes: Long, sha256: String, records: Int)
    derives ReadWriter
final case class ConstraintBinding(
    entityType: ResolutionEntityType,
    path: String,
    sha256: String,
    coveredEndpoints: Int,
    assertions: Int,
    cannotLinks: Int
) derives ReadWriter
final case class ResolutionExportManifest(
    schemaVersion: String,
    complete: Boolean,
    implementationVersion: String,
    runId: String,
    decidedAtUtc: String,
    inputEvidenceHash: String,
    prepCompletionHash: Option[String],
    policyVersion: String,
    policyHash: String,
    configHash: String,
    promptHash: String,
    responseSchemaHash: String,
    llmMode: String,
    fakeCalls: Int,
    liveCalls: Int,
    files: Vector[ResolutionExportFile],
    constraints: Vector[ConstraintBinding],
    outcomeCounts: Map[String, Int]
) derives ReadWriter

object LinkExporter {
  val manifestName = "resolution-manifest.json"
  val markerName = "_SCHOLARCHAIN_RESOLUTION_COMPLETE"
  def ensureNew(output: Path): Either[String, Unit] = Try {
    val abs = output.toAbsolutePath.normalize
    require(!Files.exists(abs), "output already exists; choose a new directory")
    var p = abs.getParent
    while (p != null) {
      require(!Files.isSymbolicLink(p), "symlink in output path"); p = p.getParent
    }
    ()
  }.toEither.left.map(_.getMessage)

  def writeNew(
      output: Path,
      run: ResolutionRun,
      input: ResolutionInput,
      policy: ResolutionPolicy,
      config: ResolutionConfig,
      requestPolicy: Option[RequestEligibilityPolicy] = None
  ): Either[String, ResolutionExportManifest] = Try {
    ensureNew(output).fold(e => throw new IllegalArgumentException(e), identity)
    RequestEligibilityPolicy
      .validateBinding(policy, requestPolicy)
      .fold(e => throw new IllegalArgumentException(e), identity)
    input.sourceRootPath.foreach(source =>
      PathIsolation
        .disjoint(source, output)
        .fold(e => throw new IllegalArgumentException(e), identity)
    )
    require(
      ResolutionPolicy.validate(policy).isRight && ResolutionConfig.validate(config).isRight,
      "invalid export policy/config"
    )
    require(
      run.decisions.forall(d =>
        d.policyHash == policy.fingerprint && d.configHash == config.fingerprint && d.inputEvidenceHash == input.inputEvidenceHash && d.decision.runId == run.runId
      ),
      "run metadata disagrees with export inputs"
    )
    require(
      run.decisions.map(_.decisionId).distinct.size == run.decisions.size && run.decisions
        .map(_.pair.pairId)
        .distinct
        .size == run.decisions.size,
      "duplicate export decisions"
    )
    run.decisions.foreach(d =>
      require(ResolutionValidation.check(d, input.context).isRight, "invalid export decision audit")
    )
    val byDecision = run.decisions.map(d => d.decisionId -> d).toMap
    require(
      run.links.map(_.decisionId).distinct.size == run.links.size && run.links
        .map(_.decisionId)
        .toSet == run.decisions
        .filter(_.decision.decision == MatchOutcome.Accepted)
        .map(_.decisionId)
        .toSet,
      "accepted decision/link inventory mismatch"
    )
    run.links.foreach(l =>
      require(
        byDecision
          .get(l.decisionId)
          .exists(d => ResolutionValidation.check(l, d, input.context).isRight),
        "link does not bind an accepted audit"
      )
    )
    val evidence = run.evidence.map(e => e.ref -> e).toMap
    require(
      evidence.size == run.evidence.size && run.evidence.forall(e =>
        e.ref == ResolutionInput.evidenceFor(e.kind, e.payload) && e.sha256 == StableIds.sha256Hex(
          StrictJson.canonical(e.payload)
        )
      ),
      "invalid exported evidence"
    )
    require(
      input.evidence.forall((ref, e) =>
        evidence.get(ref).exists(_.payload == e.payload)
      ) && run.decisions.forall(_.evidenceRefs.forall(evidence.contains)),
      "missing source/decision evidence"
    )
    require(
      run.constraints
        .map(_.entityType)
        .toSet == ResolutionEntityType.values.toSet && run.constraints.size == 2,
      "both complete constraint bundles required"
    )
    run.constraints.foreach { c =>
      require(
        c.policyHash == policy.fingerprint && c.policyVersion == policy.policyVersion && c.coveredEndpoints.toSet == input.endpoints
          .filter(ResolutionIds.entityType(_) == c.entityType)
          .toSet,
        "incomplete/mismatched constraint coverage"
      )
      val actual = c.authoritativeIdentifiers.map(a => (a.endpoint, a.namespace, a.value)).toSet
      val expected =
        c.coveredEndpoints.flatMap(e => input.authority(e).map((ns, value) => (e, ns, value))).toSet
      require(actual == expected, "incomplete/mismatched source authority assertions")
      val expectedConflicts = run.decisions
        .filter(d =>
          d.pair.entityType == c.entityType && d.decision.decision == MatchOutcome.Conflict
        )
        .map(_.pair.pairId)
        .toSet
      require(
        c.cannotLinks.map(_.pair.pairId).toSet == expectedConflicts && c.cannotLinks.forall(
          _.evidenceRefs.forall(evidence.contains)
        ) && c.authoritativeIdentifiers.forall(a =>
          a.evidenceRefs.nonEmpty && a.evidenceRefs.forall(input.refs(a.endpoint).contains)
        ),
        "incomplete/mismatched conflict/evidence constraints"
      )
    }
    val files = Vector.newBuilder[(String, String, Int)]
    def jsonl[A: ReadWriter](name: String, values: Vector[A]): Unit = files += ((
      name,
      values.map(write(_)).mkString("", "\n", if (values.isEmpty) "" else "\n"),
      values.size
    ))
    ResolutionEntityType.values.toVector.foreach { entity =>
      val name = if (entity == ResolutionEntityType.Work) "work" else "researcher"
      MatchOutcome.values.toVector.foreach { outcome =>
        jsonl(
          name + "/" + outcome.wire.toLowerCase(java.util.Locale.ROOT) + ".jsonl",
          run.decisions.filter(d => d.pair.entityType == entity && d.decision.decision == outcome)
        )
      }
      jsonl(name + "/accepted-links.jsonl", run.links.filter(_.pair.entityType == entity))
      files += ((
        name + "/grouping-constraints.json",
        write(run.constraints.find(_.entityType == entity).get) + "\n",
        1
      ))
    }
    jsonl("audit-details.jsonl", run.details)
    jsonl("diagnostics.jsonl", run.diagnostics)
    jsonl("evidence.jsonl", run.evidence)
    files += (("effective-policy.json", write(policy) + "\n", 1))
    requestPolicy.foreach(p => files += (("request-eligibility-policy.json", write(p) + "\n", 1)))
    files += (("effective-config.json", write(config) + "\n", 1))
    val built = files.result().sortBy(_._1)
    val encoded = built.map { case (name, text, count) =>
      ResolutionExportFile(
        name,
        text.getBytes(UTF_8).length.toLong,
        StableIds.sha256Hex(text),
        count
      )
    }
    require(encoded.map(_.bytes).sum <= config.maxOutputBytes, "output byte bound exceeded")
    val bindings = run.constraints.map { c =>
      val name = (if (c.entityType == ResolutionEntityType.Work) "work"
                  else "researcher") + "/grouping-constraints.json"
      ConstraintBinding(
        c.entityType,
        name,
        encoded.find(_.path == name).get.sha256,
        c.coveredEndpoints.size,
        c.authoritativeIdentifiers.size,
        c.cannotLinks.size
      )
    }
    val mode = run.llmMode
    require(
      Set("disabled", "fake")(mode) && (mode != "disabled" || run.fakeCalls == 0),
      "invalid run mode/call metadata"
    )
    val counts = (for (e <- ResolutionEntityType.values.toVector; o <- MatchOutcome.values.toVector)
      yield (e.toString + ":" + o.wire) -> run.decisions.count(d =>
        d.pair.entityType == e && d.decision.decision == o
      )).toMap
    val manifest = ResolutionExportManifest(
      "scholarchain.resolution-export.v1",
      true,
      "er-5b-v1",
      run.runId,
      run.decidedAtUtc,
      input.inputEvidenceHash,
      input.completionHash,
      policy.policyVersion,
      policy.fingerprint,
      config.fingerprint,
      StableIds.sha256Hex(Adjudication.prompt),
      StableIds.sha256Hex(Adjudication.schemaText),
      mode,
      run.fakeCalls,
      0,
      encoded,
      bindings,
      counts
    )
    val abs = output.toAbsolutePath.normalize; Files.createDirectories(abs.getParent)
    val staging = abs.resolveSibling("." + abs.getFileName + ".partial-" + UUID.randomUUID())
    Files.createDirectory(staging)
    built.foreach { case (name, text, _) =>
      val path = staging.resolve(name); Files.createDirectories(path.getParent);
      Files.writeString(path, text, UTF_8, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)
    }
    val manifestText = write(manifest) + "\n"
    Files.writeString(
      staging.resolve(manifestName),
      manifestText,
      UTF_8,
      StandardOpenOption.CREATE_NEW,
      StandardOpenOption.WRITE
    )
    Files.writeString(
      staging.resolve(markerName),
      StableIds.sha256Hex(manifestText) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW,
      StandardOpenOption.WRITE
    )
    ensureNew(abs).fold(e => throw new IllegalArgumentException(e), identity)
    Files.move(staging, abs, StandardCopyOption.ATOMIC_MOVE)
    manifest
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))

  /** Validate bytes and complete file inventory before downstream use. Does not group identities.
    */
  def verify(output: Path, config: ResolutionConfig): Either[String, ResolutionExportManifest] =
    Try {
      val manifestText = StrictJson
        .file(output.resolve(manifestName), config.input.maxRecordBytes)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val marker = StrictJson
        .file(output.resolve(markerName), 1024)
        .fold(e => throw new IllegalArgumentException(e), identity)
      require(
        marker == StableIds.sha256Hex(manifestText) + "\n",
        "resolution completion hash mismatch"
      )
      val manifest = StrictJson
        .parse[ResolutionExportManifest](manifestText)
        .fold(e => throw new IllegalArgumentException(e), identity)
      require(
        manifest.schemaVersion == "scholarchain.resolution-export.v1" && manifest.complete && manifest.liveCalls == 0 && Set(
          "fake",
          "disabled"
        )(manifest.llmMode),
        "unsupported/incomplete export"
      )
      require(
        manifest.files.map(_.path).distinct.size == manifest.files.size && manifest.files
          .map(_.bytes)
          .sum <= config.maxOutputBytes,
        "invalid output inventory"
      )
      require(
        manifest.constraints.size == 2 && manifest.constraints
          .map(_.entityType)
          .toSet == ResolutionEntityType.values.toSet,
        "complete typed constraint bindings required"
      )
      val walk = Files.walk(output)
      val actual =
        try
          walk.iterator.asScala.toVector
            .filter { p =>
              require(!Files.isSymbolicLink(p), "symlink in resolution export");
              Files.isRegularFile(p)
            }
            .map(p => output.relativize(p).toString)
            .sorted
        finally walk.close()
      require(
        actual == (manifest.files.map(_.path) ++ Vector(manifestName, markerName)).sorted,
        "resolution export inventory mismatch"
      )
      manifest.files.foreach { f =>
        val path = output.resolve(f.path).normalize
        require(
          !Path.of(f.path).isAbsolute && !f.path.split('/').contains("..") && path.startsWith(
            output.normalize
          ),
          "unsafe export inventory path"
        )
        val text = StrictJson
          .file(path, config.maxOutputBytes)
          .fold(e => throw new IllegalArgumentException(e), identity)
        require(
          text.getBytes(UTF_8).length == f.bytes && StableIds.sha256Hex(text) == f.sha256,
          "resolution export hash/length mismatch"
        )
      }
      val policyText = StrictJson
        .file(output.resolve("effective-policy.json"), config.input.maxRecordBytes)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val effectivePolicy = ResolutionPolicy
        .parse(policyText)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val requestPolicy =
        if (manifest.files.exists(_.path == "request-eligibility-policy.json"))
          Some(
            RequestEligibilityPolicy
              .load(output.resolve("request-eligibility-policy.json"))
              .fold(e => throw new IllegalArgumentException(e), identity)
          )
        else None
      RequestEligibilityPolicy
        .validateBinding(effectivePolicy, requestPolicy)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val configText = StrictJson
        .file(output.resolve("effective-config.json"), config.input.maxRecordBytes)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val effectiveConfig = ResolutionConfig
        .parse(configText)
        .fold(e => throw new IllegalArgumentException(e), identity)
      require(
        effectivePolicy.fingerprint == manifest.policyHash && effectivePolicy.policyVersion == manifest.policyVersion && effectiveConfig.fingerprint == manifest.configHash,
        "effective settings do not bind manifest"
      )
      manifest.constraints.foreach { c =>
        require(
          manifest.files.exists(f => f.path == c.path && f.sha256 == c.sha256),
          "constraint bundle is not bound to export inventory"
        )
        val text = StrictJson
          .file(output.resolve(c.path), config.maxOutputBytes)
          .fold(e => throw new IllegalArgumentException(e), identity)
        val bundle = StrictJson
          .parse[ResolutionGroupingConstraints](text)
          .fold(e => throw new IllegalArgumentException(e), identity)
        require(
          bundle.schemaVersion == ResolutionContracts.schemaVersion && bundle.entityType == c.entityType && bundle.policyVersion == manifest.policyVersion && bundle.policyHash == manifest.policyHash && bundle.coveredEndpoints.size == c.coveredEndpoints && bundle.authoritativeIdentifiers.size == c.assertions && bundle.cannotLinks.size == c.cannotLinks,
          "constraint contents disagree with complete manifest binding"
        )
      }
      manifest
    }.toEither.left.map(_.getMessage)
}
