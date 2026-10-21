package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.security.MessageDigest
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import scala.util.Try
import upickle.default.{ReadWriter, writeJs}

final case class EvidenceRecord(
    ref: String,
    kind: String,
    sha256: String,
    payload: ujson.Value,
    locator: String
) derives ReadWriter
final case class InputDiagnostic(code: String, count: Long, details: Vector[String])
    derives ReadWriter

/** Immutable source observations. The private constructor prevents unchecked synthetic input. */
final class ResolutionInput private[entityresolution] (
    val works: Vector[WorkRecord],
    val profiles: Vector[OrcidProfileRecord],
    val activities: Vector[OrcidActivityRecord],
    val candidates: Vector[MatchCandidate],
    val affiliations: Vector[MentionAffiliation],
    val enrichments: Vector[EnrichmentLink],
    val evidence: Map[String, EvidenceRecord],
    val inputEvidenceHash: String,
    val context: ResolutionValidationContext,
    val completionHash: Option[String],
    val sourceRootPath: Option[Path]
) {
  val workByRef: Map[ResolutionObservationRef, WorkRecord] =
    works.map(w => ResolutionInput.ref(w.provenance) -> w).toMap
  val profileByRef: Map[ResolutionObservationRef, OrcidProfileRecord] =
    profiles.map(p => ResolutionInput.ref(p.provenance) -> p).toMap
  val activityByRef: Map[ResolutionObservationRef, OrcidActivityRecord] =
    activities.map(a => ResolutionInput.ref(a.provenance) -> a).toMap
  val endpoints: Vector[ResolutionEndpoint] = (
    works.flatMap(w =>
      Vector(ResolutionEndpoint.Work(ResolutionInput.ref(w.provenance), w.workId)) ++ w.authors.map(
        m => ResolutionEndpoint.Mention(ResolutionInput.ref(w.provenance), m.mentionId)
      )
    ) ++
      profiles.map(p =>
        ResolutionEndpoint.OrcidProfile(ResolutionInput.ref(p.provenance), p.orcid)
      ) ++
      activities
        .filter(_.activityKind == OrcidActivityKind.Work)
        .map(a =>
          ResolutionEndpoint.OrcidWorkActivity(ResolutionInput.ref(a.provenance), a.observedWorkId)
        )
  ).distinct.sortBy(ResolutionIds.endpointKey)
  val authority: Map[ResolutionEndpoint, Set[(ResolutionAuthorityNamespace, String)]] = endpoints
    .map(e =>
      e -> context
        .groundedAuthority(e)
        .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
    )
    .toMap
  def refs(endpoint: ResolutionEndpoint): Vector[String] = {
    val ref = ResolutionIds.observation(endpoint)
    val primary = endpoint match {
      case ResolutionEndpoint.Work(_, _) | ResolutionEndpoint.Mention(_, _) =>
        ResolutionInput.evidenceFor("work", writeJs(workByRef(ref)))
      case ResolutionEndpoint.OrcidProfile(_, _) =>
        ResolutionInput.evidenceFor("orcid-profile", writeJs(profileByRef(ref)))
      case ResolutionEndpoint.OrcidWorkActivity(_, _) =>
        ResolutionInput.evidenceFor("orcid-activity", writeJs(activityByRef(ref)))
    }
    val extra = endpoint match {
      case ResolutionEndpoint.Mention(_, id) =>
        affiliations
          .filter(a => a.mentionId == id && ResolutionInput.ref(a.provenance) == ref)
          .map(a => ResolutionInput.evidenceFor("mention-affiliation", writeJs(a))) ++ enrichments
          .filter(a => a.mentionId.contains(id) && ResolutionInput.ref(a.provenance) == ref)
          .map(a => ResolutionInput.evidenceFor("enrichment", writeJs(a)))
      case _ => Vector.empty
    }
    (Vector(primary) ++ extra).distinct.sorted
  }
  def mention(endpoint: ResolutionEndpoint): Option[AuthorMention] = endpoint match {
    case ResolutionEndpoint.Mention(ref, id) =>
      workByRef.get(ref).flatMap(_.authors.find(_.mentionId == id))
    case _ => None
  }
  def parentWork(endpoint: ResolutionEndpoint): Option[WorkRecord] = endpoint match {
    case ResolutionEndpoint.Work(ref, _)    => workByRef.get(ref)
    case ResolutionEndpoint.Mention(ref, _) => workByRef.get(ref)
    case _                                  => None
  }
}

object ResolutionInput {
  def ref(p: Provenance): ResolutionObservationRef =
    ResolutionObservationRef(p.source, p.sourceRecordId, p.datasetSnapshot)
  def evidenceFor(kind: String, payload: ujson.Value): String =
    "er-evidence:" + StableIds.sha256Hex(kind + "\n" + StrictJson.canonical(payload))
  private[entityresolution] def record(
      kind: String,
      payload: ujson.Value,
      locator: String
  ): EvidenceRecord = {
    val hash = StableIds.sha256Hex(StrictJson.canonical(payload))
    EvidenceRecord(evidenceFor(kind, payload), kind, hash, payload, locator)
  }

  /** For deterministic tests/adapters. All supplied source records and references are validated. */
  def create(
      works: Vector[WorkRecord],
      profiles: Vector[OrcidProfileRecord],
      activities: Vector[OrcidActivityRecord],
      candidates: Vector[MatchCandidate],
      affiliations: Vector[MentionAffiliation] = Vector.empty,
      enrichments: Vector[EnrichmentLink] = Vector.empty
  ): Either[String, ResolutionInput] =
    assemble(works, profiles, activities, candidates, affiliations, enrichments, Vector.empty, None)

  private[entityresolution] def assemble(
      works: Vector[WorkRecord],
      profiles: Vector[OrcidProfileRecord],
      activities: Vector[OrcidActivityRecord],
      candidates: Vector[MatchCandidate],
      affiliations: Vector[MentionAffiliation],
      enrichments: Vector[EnrichmentLink],
      other: Vector[EvidenceRecord],
      completion: Option[String],
      sourceRootPath: Option[Path] = None
  ): Either[String, ResolutionInput] = Try {
    def valid[A](v: Either[Vector[DomainViolation], A]): Unit =
      require(v.isRight, v.left.toOption.toVector.flatten.map(_.message).mkString("; "))
    candidates.foreach(c => valid(DomainValidation.check(c)))
    affiliations.foreach(a => valid(DomainValidation.check(a)))
    enrichments.foreach(a => valid(DomainValidation.check(a)))
    val context = ResolutionValidationContext
      .create(works, profiles, activities)
      .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
    def canonical(p: Provenance): Unit = {
      val id = p.sourceRecordId
      val expected = p.source match {
        case SourceType.Orcid    => id.stripPrefix("/")
        case SourceType.OpenAlex => id.replaceFirst("(?i)^https://openalex\\.org/", "")
        case SourceType.Crossref => StableIds.normalizeDoi(id).getOrElse(id)
        case _                   => id
      }
      require(id == expected, "noncanonical sourceRecordId spelling: " + id)
    }
    (works.map(_.provenance) ++ profiles.map(_.provenance) ++ activities.map(_.provenance)).foreach(
      canonical
    )
    val observations = works.map(w => ref(w.provenance) -> Some(w.workId)).toMap ++ profiles
      .map(p => ref(p.provenance) -> None)
      .toMap ++ activities.map(a => ref(a.provenance) -> a.observedWorkId).toMap
    val texts = other.filter(_.kind == "text").map { e =>
      val text = StrictJson
        .parse[EmittedTextDocument](e.payload.render())
        .fold(message => throw new IllegalArgumentException(message), identity)
      valid(DomainValidation.check(text))
      require(observations.contains(ref(text.provenance)), "text has missing source observation")
      require(
        text.sourceVersion == text.provenance.datasetSnapshot,
        "text source version differs from observation snapshot"
      )
      text
    }
    other.filter(_.kind == "index").foreach { e =>
      val index = StrictJson
        .parse[IdentifierIndexEntry](e.payload.render())
        .fold(message => throw new IllegalArgumentException(message), identity)
      valid(DomainValidation.check(index))
      require(
        observations.contains(
          ResolutionObservationRef(index.source, index.sourceRecordId, index.datasetSnapshot)
        ),
        "identifier index has missing source observation"
      )
    }
    works.foreach { work =>
      work.abstractTextRef.foreach { textId =>
        require(
          texts.exists(text =>
            text.textId == textId && text.documentType == EmittedTextDocument.abstractDocumentType && text.entityId == work.workId && text.sourceVersion == work.provenance.datasetSnapshot && ref(
              text.provenance
            ) == ref(work.provenance)
          ),
          "work abstractTextRef has missing or mismatched text evidence"
        )
      }
    }
    candidates.foreach { c =>
      Vector(c.left, c.right).foreach { o =>
        val r = ResolutionObservationRef(o.source, o.sourceRecordId, o.datasetSnapshot)
        require(observations.contains(r), "candidate has missing source observation")
        // Phase 4 deliberately leaves workId absent on ORCID activity bibliography rows,
        // even when the source activity carries observedWorkId. Absence asserts nothing.
        o.workId.foreach { id =>
          require(
            observations(r).contains(id),
            "candidate carried workId differs from source observation"
          )
        }
      }
    }
    def mentionExists(p: Provenance, id: String): Boolean =
      works.exists(w => ref(w.provenance) == ref(p) && w.authors.exists(_.mentionId == id))
    affiliations.foreach(a =>
      require(mentionExists(a.provenance, a.mentionId), "dangling affiliation mention")
    )
    enrichments.foreach { a =>
      a.mentionId.foreach(id =>
        require(mentionExists(a.provenance, id), "dangling enrichment mention")
      )
      a.workId.foreach(id =>
        require(
          works.exists(w => ref(w.provenance) == ref(a.provenance) && w.workId == id),
          "dangling enrichment work"
        )
      )
    }
    def unique[A](items: Vector[A], key: A => String): Unit = items
      .groupBy(key)
      .values
      .foreach(v => require(v.distinct.size == 1, "conflicting duplicate source record"))
    unique(candidates, (c: MatchCandidate) => c.candidateId)
    val records = works.map(w => record("work", writeJs(w), "in-memory")) ++ profiles.map(p =>
      record("orcid-profile", writeJs(p), "in-memory")
    ) ++ activities.map(a => record("orcid-activity", writeJs(a), "in-memory")) ++ candidates.map(
      c => record("match-candidate", writeJs(c), "in-memory")
    ) ++ affiliations.map(a =>
      record("mention-affiliation", writeJs(a), "in-memory")
    ) ++ enrichments.map(a => record("enrichment", writeJs(a), "in-memory")) ++ other
    val evidence = records.groupBy(_.ref).map { case (key, rs) => key -> rs.last }
    val hash = StableIds.sha256Hex(
      ujson
        .Arr(
          completion.map(ujson.Str(_)).getOrElse(ujson.Null),
          ujson.Arr.from(evidence.toVector.sortBy(_._1).map { case (k, r) =>
            ujson.Arr(k, r.sha256)
          })
        )
        .render()
    )
    new ResolutionInput(
      works.distinct,
      profiles.distinct,
      activities.distinct,
      candidates.distinct,
      affiliations.distinct,
      enrichments.distinct,
      evidence,
      hash,
      context,
      completion,
      sourceRootPath
    )
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
}

final case class PrepExportPart(path: String, bytes: Long, sha256: String) derives ReadWriter
final case class PrepCompletion(
    complete: Boolean,
    runId: String,
    configFingerprint: String,
    inputChecksums: Map[String, String],
    snapshots: Map[String, String],
    retrievalDates: Map[String, String],
    partitions: Vector[String],
    exportParts: Vector[PrepExportPart],
    schemaVersion: String,
    hadoopPrepSchema: String,
    transformationVersion: String
) derives ReadWriter

object InputLoader {
  private def digest(path: Path): String = {
    val md = MessageDigest.getInstance("SHA-256"); val in = Files.newInputStream(path);
    val buf = new Array[Byte](65536)
    try { var n = in.read(buf); while (n != -1) { md.update(buf, 0, n); n = in.read(buf) } }
    finally in.close()
    java.util.HexFormat.of().formatHex(md.digest())
  }
  def load(path: Path, config: ResolutionConfig): Either[String, ResolutionInput] = Try {
    ResolutionConfig.validate(config).fold(e => throw new IllegalArgumentException(e), identity)
    val root = path.toAbsolutePath.normalize;
    require(
      Files.isDirectory(root) && !Files.isSymbolicLink(root),
      "completed local run directory required"
    )
    val markerText = StrictJson
      .file(root.resolve("_SCHOLARCHAIN_COMPLETE"), config.input.maxRecordBytes)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val marker = StrictJson
      .parse[PrepCompletion](markerText)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val manifestText = StrictJson
      .file(root.resolve("run-manifest.json"), config.input.maxRecordBytes)
      .fold(e => throw new IllegalArgumentException(e), identity)
    val manifest = StrictJson
      .parse[RunManifest](manifestText)
      .fold(e => throw new IllegalArgumentException(e), identity)
    require(DomainValidation.check(manifest).isRight, "invalid prep run manifest")
    require(
      marker.complete && marker.schemaVersion == SchemaVersions.domain && marker.hadoopPrepSchema == SchemaVersions.hadoopPrep && marker.transformationVersion == "hadoop-prep-j01-j09-v3-stable-overflow-lineage",
      "unsupported/incomplete prep completion"
    )
    require(
      marker.runId == manifest.runId && marker.configFingerprint == manifest.configFingerprint && manifest.configSchemaVersion == marker.hadoopPrepSchema && manifest.pipelineName == "hadoop-prep",
      "completion/manifest identity mismatch"
    )
    require(
      marker.configFingerprint.matches(
        "[0-9a-f]{64}"
      ) && marker.inputChecksums.nonEmpty && marker.inputChecksums.values.forall(
        _.matches("[0-9a-f]{64}")
      ),
      "invalid completion input hashes"
    )
    require(
      manifest.datasetSnapshots
        .map(s => s.source.wire -> s.snapshot)
        .toMap == marker.snapshots && manifest.datasetSnapshots
        .flatMap(s => s.retrievalDate.map(s.source.wire -> _))
        .toMap == marker.retrievalDates && marker.inputChecksums.keySet == marker.snapshots.keySet,
      "completion/manifest snapshot mismatch"
    )
    marker.inputChecksums.foreach((s, h) =>
      require(
        manifest.provenance.uncertaintyNotes.contains("inputChecksum:" + s + "=" + h),
        "manifest input checksum missing/disagrees"
      )
    )
    require(
      manifest.provenance.uncertaintyNotes.contains(
        "transformationVersion=" + marker.transformationVersion
      ),
      "manifest transformation mismatch"
    )
    (Vector("export/_SUCCESS") ++ (1 to 8).map(n => f"intermediate/j$n%02d/_SUCCESS")).foreach(p =>
      require(
        Files.isRegularFile(root.resolve(p)) && !Files.isSymbolicLink(root.resolve(p)),
        "missing prep stage success: " + p
      )
    )
    require(
      marker.exportParts.nonEmpty && marker.exportParts.size <= config.input.maxExportParts && marker.exportParts
        .map(_.path)
        .distinct
        .size == marker.exportParts.size,
      "invalid export inventory"
    )
    val exportRoot = root.resolve("export"); val walk = Files.walk(exportRoot)
    val actual =
      try
        walk.iterator.asScala.toVector
          .filter { p =>
            require(!Files.isSymbolicLink(p), "symlink in export")
            Files.isRegularFile(p) && !p.getFileName.toString.startsWith(
              "_"
            ) && !p.getFileName.toString.startsWith(".") && !p.getFileName.toString.endsWith(".crc")
          }
          .map(p => exportRoot.relativize(p).toString)
          .sorted
      finally walk.close()
    require(
      actual == marker.exportParts.map(_.path).sorted,
      "export inventory does not cover exact actual file set"
    )
    require(
      marker.partitions.distinct.size == marker.partitions.size && marker.partitions.sorted == actual
        .map(p => Option(Path.of(p).getParent).map(_.toString).getOrElse(""))
        .filter(_.nonEmpty)
        .distinct
        .sorted,
      "partition inventory mismatch"
    )
    require(
      marker.exportParts.forall(p =>
        p.bytes >= 0 && p.sha256.matches("[0-9a-f]{64}")
      ) && marker.exportParts.map(_.bytes).sum <= config.input.maxInputBytes,
      "input byte bound exceeded/invalid inventory"
    )
    val works = mutable.ArrayBuffer.empty[WorkRecord];
    val profiles = mutable.ArrayBuffer.empty[OrcidProfileRecord];
    val activities = mutable.ArrayBuffer.empty[OrcidActivityRecord];
    val candidates = mutable.ArrayBuffer.empty[MatchCandidate];
    val affiliations = mutable.ArrayBuffer.empty[MentionAffiliation];
    val enrichments = mutable.ArrayBuffer.empty[EnrichmentLink];
    val mentions = mutable.ArrayBuffer.empty[AuthorMention];
    val other = mutable.ArrayBuffer.empty[EvidenceRecord]
    val authorships = mutable.ArrayBuffer.empty[AuthorshipRecord];
    val teams = mutable.ArrayBuffer.empty[PublicationTeam];
    val coauthorPairs = mutable.ArrayBuffer.empty[CoauthorPairCandidate]
    var count = 0
    marker.exportParts.sortBy(_.path).foreach { part =>
      val file = exportRoot.resolve(part.path).normalize
      require(
        file.startsWith(exportRoot) && !Path
          .of(part.path)
          .isAbsolute && !part.path.split('/').contains(".."),
        "unsafe export path"
      )
      require(
        Files.size(file) == part.bytes && digest(file) == part.sha256,
        "export digest/length mismatch: " + part.path
      )
      val text = StrictJson
        .file(file, config.input.maxInputBytes)
        .fold(e => throw new IllegalArgumentException(e), identity)
      if (text.nonEmpty) require(text.endsWith("\n"), "incomplete JSONL framing")
      val kind = Option(Path.of(part.path).getParent).map(_.getFileName.toString).getOrElse("")
      text.linesIterator.zipWithIndex.foreach { (line, index) =>
        require(
          line.nonEmpty && !line
            .contains('\t') && line.getBytes(UTF_8).length <= config.input.maxRecordBytes,
          "invalid or oversized export JSONL line"
        )
        count += 1; require(count <= config.input.maxInputRecords, "input record bound exceeded")
        val payload = ujson.read(line);
        require(payload.objOpt.nonEmpty, "object export row required")
        require(
          payload.obj.get("schemaVersion").contains(ujson.Str(SchemaVersions.domain)),
          "unknown source row schema"
        )
        val prov = payload.obj.get("provenance")
        prov.foreach { p =>
          require(p("runId").str == marker.runId, "source record prep run mismatch")
          val s = p("source").str
          if (s != "SCHOLARCHAIN")
            require(
              marker.snapshots.get(s).contains(p("datasetSnapshot").str) && marker.retrievalDates
                .get(s) == p("retrievalDate").strOpt,
              "source provenance differs from manifest"
            )
          val parent = Path.of(part.path).getParent.getParent
          require(
            parent.getFileName.toString == "run=" + marker.runId.stripPrefix(
              "run:"
            ) && parent.getParent.getFileName.toString == "snapshot=" + p("datasetSnapshot").str,
            "row partition does not bind provenance"
          )
        }
        def row[A: ReadWriter](check: A => Either[Vector[DomainViolation], A]): A = {
          val a =
            StrictJson.parse[A](line).fold(e => throw new IllegalArgumentException(e), identity);
          require(check(a).isRight, "invalid " + kind + " domain row"); a
        }
        kind match {
          case "work"            => works += row[WorkRecord](DomainValidation.check)
          case "orcid-profile"   => profiles += row[OrcidProfileRecord](DomainValidation.check)
          case "orcid-activity"  => activities += row[OrcidActivityRecord](DomainValidation.check)
          case "match-candidate" => candidates += row[MatchCandidate](DomainValidation.check)
          case "author-mention"  => mentions += row[AuthorMention](DomainValidation.check)
          case "mention-affiliation" =>
            affiliations += row[MentionAffiliation](DomainValidation.check)
          case "enrichment" => enrichments += row[EnrichmentLink](DomainValidation.check)
          case "index"      => row[IdentifierIndexEntry](DomainValidation.check)
          case "text"       => row[EmittedTextDocument](DomainValidation.check)
          case "authorship" => authorships += row[AuthorshipRecord](DomainValidation.checkStructure)
          case "team"       => teams += row[PublicationTeam](DomainValidation.checkStructure)
          case "pair" =>
            coauthorPairs += row[CoauthorPairCandidate](DomainValidation.checkStructure)
          case "venue"       => row[Venue](DomainValidation.check)
          case "institution" => row[Institution](DomainValidation.check)
          case "topic"       => row[Topic](DomainValidation.check)
          case "graph-edge"  => row[GraphEdge](DomainValidation.check)
          case "reject"      => row[RejectRecord](DomainValidation.check)
          case _ => throw new IllegalArgumentException("unsupported export kind: " + kind)
        }
        other += ResolutionInput.record(kind, payload, part.path + ":" + (index + 1))
      }
    }
    require(
      works.size + profiles.size + activities.size <= config.input.maxLookupObservations,
      "lookup observation bound exceeded"
    )
    val expected = works.toVector.flatMap(_.authors).toSet
    require(
      expected == mentions.toSet && mentions.distinct.size == mentions.size,
      "standalone/nested author mentions mismatch or duplicates"
    )
    val workContext = WorkValidationContext
      .create(works.toVector)
      .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
    authorships.foreach(a =>
      require(
        DomainValidation.check(a, workContext).isRight,
        "authorship has invalid source work binding"
      )
    )
    teams.foreach(a =>
      require(
        DomainValidation.check(a, workContext).isRight,
        "team has invalid source work binding"
      )
    )
    coauthorPairs.foreach(a =>
      require(
        DomainValidation.check(a, workContext).isRight,
        "pair has invalid source work binding"
      )
    )
    ResolutionInput
      .assemble(
        works.toVector,
        profiles.toVector,
        activities.toVector,
        candidates.toVector,
        affiliations.toVector,
        enrichments.toVector,
        other.toVector,
        Some(StableIds.sha256Hex(markerText + "\n" + manifestText)),
        Some(root.toRealPath())
      )
      .fold(e => throw new IllegalArgumentException(e), identity)
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
}
