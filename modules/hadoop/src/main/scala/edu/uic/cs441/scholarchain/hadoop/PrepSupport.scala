package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.io.Text
import org.apache.hadoop.mapreduce.{TaskAttemptContext, TaskInputOutputContext}
import upickle.default.ReadWriter

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.collection.mutable.ArrayBuffer
import scala.jdk.CollectionConverters.*

/** Hadoop counter group written into the run directory after every successful job. */
object PrepCounters {
  val Group = "SCHOLARCHAIN"
  val Input = "INPUT"
  val Accepted = "ACCEPTED"
  val Rejected = "REJECTED"
  val Duplicate = "DUPLICATE"
  val Conflict = "CONFLICT"
  val OversizeBlock = "OVERSIZE_BLOCK"
  val OversizeTeam = "OVERSIZE_TEAM"
  val OversizeTeamPairStep = "OVERSIZE_TEAM_PAIR_STEP"
  val EmittedPair = "EMITTED_PAIR"
  val MissingKey = "MISSING_KEY"
  val SchemaFailure = "SCHEMA_FAILURE"

  val All: Vector[String] = Vector(
    Input,
    Accepted,
    Rejected,
    Duplicate,
    Conflict,
    OversizeBlock,
    OversizeTeam,
    OversizeTeamPairStep,
    EmittedPair,
    MissingKey,
    SchemaFailure
  )
}

object PrepLimits {
  val FeaturePolicy = "prep-features-v1"
  val MatchFeaturePolicy: String = PreparationFeatures.policyV2
  val TransformationVersion = "hadoop-prep-j01-j09-v3-stable-overflow-lineage"
  val DerivedSnapshot = "hadoop-prep"

  def pairCount(n: Int): Long =
    if (n < 2) 0L
    else {
      val a = n.toLong
      val b = a - 1L
      java.lang.Math.multiplyExact(a, b) / 2L
    }
}

/** Intermediate JSON cap for J03–J09. At least 1 MiB, never above 16 MiB, and never below the
  * source `maxRecordBytes`. This is Hadoop-owned and is not a core config field.
  */
object IntermediateBytes {
  val Floor: Long = 1024L * 1024L
  val Ceiling: Long = 16L * 1024L * 1024L

  def cap(sourceMaxRecordBytes: Long): Long =
    math.min(Ceiling, math.max(Floor, sourceMaxRecordBytes))
}

object ConfKeys {
  val RunId = "scholarchain.run.id"
  val MaxRecordBytes = "scholarchain.max.record.bytes"
  val MaxIntermediateBytes = "scholarchain.max.intermediate.bytes"
  val BoundedLineBytes = "scholarchain.bounded.line.bytes"
  val MaxXmlEntityExpansion = "scholarchain.max.xml.entity.expansion"
  val MaxBlock = "scholarchain.max.block"
  val MaxPairs = "scholarchain.max.pairs"
  val MaxTeam = "scholarchain.max.team"
  val MaxSample = "scholarchain.max.sample"
  val SnapshotDblp = "scholarchain.snapshot.dblp"
  val SnapshotOpenAlex = "scholarchain.snapshot.openalex"
  val SnapshotCrossref = "scholarchain.snapshot.crossref"
  val SnapshotOrcid = "scholarchain.snapshot.orcid"
  val RetrievalDblp = "scholarchain.retrieval.dblp"
  val RetrievalOpenAlex = "scholarchain.retrieval.openalex"
  val RetrievalCrossref = "scholarchain.retrieval.crossref"
  val RetrievalOrcid = "scholarchain.retrieval.orcid"
  val StatsDir = "scholarchain.stats.dir"
  val FailJob = "scholarchain.fail.job"
  val ExecutionMode = "scholarchain.execution.mode"
  val IntermediateCompression = "scholarchain.intermediate.compression"
  val CompressionCodec = "scholarchain.compression.codec"
  val SampleReady = "scholarchain.sample.ready"
  val SampleCount = "scholarchain.sample.count"

  def samplePath(index: Int): String = s"scholarchain.sample.path.$index"
  def sampleCutoff(index: Int): String = s"scholarchain.sample.cutoff.$index"
}

object Kinds {
  val Work = "work"
  val Venue = "venue"
  val Institution = "institution"
  val Topic = "topic"
  val Enrichment = "enrichment"
  val Text = "text"
  val Reject = "reject"
  val Profile = "orcid-profile"
  val Activity = "orcid-activity"
  val Index = "index"
  val BlockMember = "block-member"
  val MatchCandidate = "match-candidate"
  val Team = "team"
  val Authorship = "authorship"
  val Pair = "pair"
  val GraphEdge = "graph-edge"
  val AuthorMention = "author-mention"
  val MentionAffiliation = "mention-affiliation"
  val Bibliography = "bibliography"
}

/** Coproduct of domain records this module emits. Not a second domain model. */
enum EmittedRecord {
  case Work(value: WorkRecord)
  case VenueRec(value: Venue)
  case InstitutionRec(value: Institution)
  case TopicRec(value: Topic)
  case Link(value: EnrichmentLink)
  case TextDoc(value: EmittedTextDocument)
  case Profile(value: OrcidProfileRecord)
  case Activity(value: OrcidActivityRecord)
  case Rejected(value: RejectRecord)
  case Indexed(value: IndexRow)
  case Member(value: BlockMember)
  case Candidate(value: MatchCandidate)
  case TeamRec(value: PublicationTeam)
  case AuthorshipRec(value: AuthorshipRecord)
  case PairRec(value: CoauthorPairCandidate)
  case Edge(value: GraphEdge)
  case Affiliation(value: MentionAffiliation)

  def kind: String = this match {
    case _: Work           => Kinds.Work
    case _: VenueRec       => Kinds.Venue
    case _: InstitutionRec => Kinds.Institution
    case _: TopicRec       => Kinds.Topic
    case _: Link           => Kinds.Enrichment
    case _: TextDoc        => Kinds.Text
    case _: Rejected       => Kinds.Reject
    case _: Profile        => Kinds.Profile
    case _: Activity       => Kinds.Activity
    case _: Indexed        => Kinds.Index
    case _: Member         => Kinds.BlockMember
    case _: Candidate      => Kinds.MatchCandidate
    case _: TeamRec        => Kinds.Team
    case _: AuthorshipRec  => Kinds.Authorship
    case _: PairRec        => Kinds.Pair
    case _: Edge           => Kinds.GraphEdge
    case _: Affiliation    => Kinds.MentionAffiliation
  }

  def json: String = this match {
    case Work(value)           => CoreJson.compact(value)
    case VenueRec(value)       => CoreJson.compact(value)
    case InstitutionRec(value) => CoreJson.compact(value)
    case TopicRec(value)       => CoreJson.compact(value)
    case Link(value)           => CoreJson.compact(value)
    case TextDoc(value)        => CoreJson.compact(value)
    case Rejected(value)       => CoreJson.compact(value)
    case Profile(value)        => CoreJson.compact(value)
    case Activity(value)       => CoreJson.compact(value)
    case Indexed(value)        => CoreJson.compact(value)
    case Member(value)         => CoreJson.compact(value)
    case Candidate(value)      => CoreJson.compact(value)
    case TeamRec(value)        => CoreJson.compact(value)
    case AuthorshipRec(value)  => CoreJson.compact(value)
    case PairRec(value)        => CoreJson.compact(value)
    case Edge(value)           => CoreJson.compact(value)
    case Affiliation(value)    => CoreJson.compact(value)
  }

  def snapshot: String = this match {
    case Work(value)           => value.provenance.datasetSnapshot
    case VenueRec(value)       => value.provenance.datasetSnapshot
    case InstitutionRec(value) => value.provenance.datasetSnapshot
    case TopicRec(value)       => value.provenance.datasetSnapshot
    case Link(value)           => value.datasetSnapshot
    case TextDoc(value)        => value.provenance.datasetSnapshot
    case Rejected(value)       => value.datasetSnapshot.getOrElse(PrepLimits.DerivedSnapshot)
    case Profile(value)        => value.provenance.datasetSnapshot
    case Activity(value)       => value.provenance.datasetSnapshot
    case Indexed(value)        => value.entry.datasetSnapshot
    case Member(value)         => value.datasetSnapshot
    case Candidate(_)          => PrepLimits.DerivedSnapshot
    case TeamRec(value)        => value.provenance.datasetSnapshot
    case AuthorshipRec(value)  => value.provenance.datasetSnapshot
    case PairRec(value)        => value.provenance.datasetSnapshot
    case Edge(value)           => value.provenance.datasetSnapshot
    case Affiliation(value)    => value.datasetSnapshot
  }
}

final case class IndexRow(entry: IdentifierIndexEntry, payloadHash: String) derives ReadWriter

/** Private intermediate framing. Identity precedes potentially large domain JSON so a capped reader
  * can preserve lineage without parsing or retaining the rest of an oversized line.
  */
final case class Lineage(source: Option[SourceType], snapshot: Option[String], record: String)
    derives ReadWriter

object Lineage {
  val Separator = '\u0002'
  val MaxPrefixBytes = 8192
  val MaxSnapshotBytes = 1024
  private val MaxField = 256

  def snapshotFits(value: String): Boolean =
    value.getBytes(StandardCharsets.UTF_8).length <= MaxSnapshotBytes

  def fromProvenance(value: Provenance): Lineage =
    Lineage(Some(value.source), Some(value.datasetSnapshot), value.sourceRecordId)

  def fromJson(json: String): Option[Lineage] =
    try {
      val root = ujson.read(json).obj
      val nested = root.get("provenance").orElse(root.get("entry")).flatMap(_.objOpt)
      val row = nested.map(_.value).getOrElse(root)
      def text(name: String): Option[String] = row.get(name).collect { case ujson.Str(v) => v }
      val source = text("source").flatMap(v => SourceType.values.find(_.wire == v))
      val snapshot = text("datasetSnapshot")
      val record = text("sourceRecordId").orElse(text("sourceLocator"))
      record.map(id => Lineage(source, snapshot, id))
    } catch { case _: Exception => None }

  def key(raw: String, lineage: Option[Lineage]): String =
    lineage match {
      case Some(value) =>
        // Source record ids can be referenced by digest when they exceed reject-locator bounds.
        // Snapshot values stay exact; an unrepresentable envelope fails rather than losing them.
        val bounded = value.copy(
          record = boundedIdentity(value.record)
        )
        val bytes = CoreJson.compact(bounded).getBytes(StandardCharsets.UTF_8)
        val encoded = java.util.Base64.getUrlEncoder.withoutPadding().encodeToString(bytes)
        require(
          raw.getBytes(StandardCharsets.UTF_8).length + encoded.length + 1 < MaxPrefixBytes,
          "source lineage exceeds bounded intermediate envelope"
        )
        raw + Separator + encoded
      case None => raw
    }

  def boundedIdentity(value: String): String =
    if (value.length <= MaxField) value
    else value.take(160) + "#sha256=" + Digests.sha256Text(value)

  def prefix(raw: String): Option[Lineage] = {
    val at = raw.indexOf(Separator)
    if (at < 0 || raw.length > MaxPrefixBytes) None
    else
      try {
        val json = new String(
          java.util.Base64.getUrlDecoder.decode(raw.substring(at + 1)),
          StandardCharsets.UTF_8
        )
        CoreJson
          .parse[Lineage](json)
          .toOption
          .filter(value => value.snapshot.forall(snapshotFits))
          .map(value => value.copy(record = boundedIdentity(value.record)))
      } catch { case _: IllegalArgumentException => None }
  }

  /** Only this invocation's terminal, generated intermediate directory is processing metadata.
    * Identical UUID text elsewhere in the genuine root is preserved.
    */
  def canonicalProcessingFile(path: String, runId: String): Option[String] = {
    val qualified = Vector("file:", "s3://", "s3a://", "s3n://", "hdfs://").exists(path.startsWith)
    if (!qualified || StableIds.parseRunId(runId).isLeft) None
    else {
      val uuid = java.util.regex.Pattern.quote(HadoopPrepPipeline.directoryName(runId))
      val pattern =
        ("^(.*)/" + uuid + "(/intermediate/j0[1-8]/part-[mr]-[0-9]+(?:[.][A-Za-z0-9_-]+)*)$").r
      path match {
        case pattern(root, suffix) => Some(root + "/RUN" + suffix)
        case _                     => None
      }
    }
  }

  def overflowLocator(
      path: String,
      offset: Long,
      lineage: Option[Lineage],
      runId: String
  ): String = {
    val file = canonicalProcessingFile(path, runId) match {
      case Some(stable) =>
        path.take(500) + "#processing-file-sha256=" + Digests.sha256Text(path) +
          "#processing-file-stable-sha256=" + Digests.sha256Text(stable)
      case None =>
        if (path.length <= 700) path else path.take(500) + "#sha256=" + Digests.sha256Text(path)
    }
    val record = lineage.map(value => "#record=" + boundedIdentity(value.record)).getOrElse("")
    file + "@" + offset + record
  }

  /** Comparison only: keep stable root/part identity, offset, and native record reference. The raw
    * exported locator still records the full processing-file digest and bounded display.
    */
  def logicalOverflowLocator(locator: String): String = {
    val pattern =
      "^.{1,500}#processing-file-sha256=[0-9a-f]{64}#processing-file-stable-sha256=([0-9a-f]{64})@([0-9]+)(#record=.+)$".r
    locator match {
      case pattern(stable, offset, record) =>
        "processing-file-sha256=" + stable + "@" + offset + record
      case _ => locator
    }
  }
}

final case class BlockMember(
    blockKey: String,
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    workId: Option[String],
    normalizedTitle: String,
    year: Option[Int],
    venue: String,
    authorNames: Vector[String],
    authorInitials: Vector[String],
    affiliationNames: Vector[String],
    coauthorNames: Vector[String]
) derives ReadWriter

/** One surviving observation, ready to fan out into block keys. Not a domain record. */
final case class Bibliography(
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    workId: Option[String],
    normalizedTitle: String,
    year: Option[Int],
    venue: String,
    authorNames: Vector[String],
    authorInitials: Vector[String],
    affiliationNames: Vector[String],
    coauthorNames: Vector[String],
    exactKeys: Vector[String]
) derives ReadWriter

/** Sentinel written by [[BoundedLineRecordReader]] when a line exceeds its cap. Mappers turn it
  * into an [[RejectReasonCode.OversizeRecord]] reject. They do not drop it.
  */
object OverflowLines {
  val Marker = "\u0000OVERSIZE"
  val PassKey = "\u0000oversize"

  def isMarker(line: String): Boolean = line.startsWith(Marker)

  def diagnostic(line: String): String = {
    envelope(line).flatMap(_.get("preview")).collect { case ujson.Str(v) => v } match {
      case Some(value) => value.take(180)
      case None =>
        val rest = line.drop(Marker.length).dropWhile(ch => ch == '\t' || ch == ' ')
        val flat = rest.replace('\n', ' ').replace('\r', ' ').trim
        if (flat.isEmpty) RejectReasonCode.OversizeRecord.wire else flat.take(180)
    }
  }

  def encode(total: Long, preview: String, lineage: Option[Lineage], locator: String): String =
    Marker + "\t" + ujson.write(
      ujson.Obj(
        "bytes" -> total.toString,
        "preview" -> preview.take(180),
        "locator" -> locator,
        "lineage" -> lineage.map(value => ujson.read(CoreJson.compact(value))).getOrElse(ujson.Null)
      )
    )

  private def envelope(line: String): Option[collection.Map[String, ujson.Value]] =
    try ujson.read(line.drop(Marker.length).stripPrefix("\t")).objOpt.map(_.value)
    catch { case _: Exception => None }

  def record(
      line: String,
      runId: String,
      stage: PreparationStage,
      locator: String
  ): RejectRecord = {
    val meta = envelope(line)
    val lineage = meta
      .flatMap(_.get("lineage"))
      .filterNot(_.isNull)
      .flatMap(value => CoreJson.parse[Lineage](ujson.write(value)).toOption)
    val located =
      meta.flatMap(_.get("locator")).collect { case ujson.Str(v) => v }.getOrElse(locator)
    Rejects.record(
      lineage.flatMap(_.source),
      located,
      lineage.flatMap(_.snapshot),
      runId,
      stage,
      RejectReasonCode.OversizeRecord,
      diagnostic(line)
    )
  }

  /** Final job output for a pass-through reducer. */
  def emit(
      context: org.apache.hadoop.mapreduce.TaskInputOutputContext[?, ?, Text, Text],
      line: String,
      stage: PreparationStage,
      locator: String
  ): Unit = {
    val sink = TaskSink.from(context, TaskSink.runId(context))
    sink.emit(EmittedRecord.Rejected(record(line, sink.runId, stage, locator)))
  }

  /** Map output a custom reducer must copy. A pass-through reducer would publish the private key.
    */
  def defer(
      context: org.apache.hadoop.mapreduce.TaskInputOutputContext[?, ?, Text, Text],
      line: String,
      stage: PreparationStage,
      locator: String
  ): Unit = {
    val json = CoreJson.compact(record(line, TaskSink.runId(context), stage, locator))
    context.write(new Text(PassKey), new Text(json))
  }

  def release(
      context: org.apache.hadoop.mapreduce.TaskInputOutputContext[?, ?, Text, Text],
      values: java.lang.Iterable[Text]
  ): Unit = {
    val sink = TaskSink.from(context, TaskSink.runId(context))
    values.forEach { value =>
      CoreJson.parse[RejectRecord](value.toString) match {
        case Right(reject) => sink.emit(EmittedRecord.Rejected(reject))
        case Left(_) =>
          sink.reject(
            None,
            "oversize",
            None,
            PreparationStage.Export,
            RejectReasonCode.OversizeRecord,
            value.toString.take(180)
          )
      }
    }
  }
}

object Lines {
  def pack(kind: String, json: String): String = kind + "\t" + json

  def unpack(line: String): Option[(String, String)] =
    tag(line).map { case (kind, _, json) => (kind, json) }

  /** `kind`, observation instance, and JSON. The instance is empty when the line has none. */
  def tag(line: String): Option[(String, String, String)] = {
    val tab = line.indexOf('\t')
    if (tab <= 0) None
    else {
      val raw = line.substring(0, tab).takeWhile(_ != Lineage.Separator)
      val cut = raw.indexOf('\u0001')
      val kind = if (cut < 0) raw else raw.substring(0, cut)
      val instance = if (cut < 0) "" else raw.substring(cut + 1)
      Some((kind, instance, line.substring(tab + 1)))
    }
  }
}

object Rejects {
  def record(
      source: Option[SourceType],
      locator: String,
      snapshot: Option[String],
      runId: String,
      stage: PreparationStage,
      reason: RejectReasonCode,
      raw: String
  ): RejectRecord = {
    val flat = raw.replace('\n', ' ').replace('\r', ' ').trim
    val excerpt =
      if (flat.isEmpty) None
      else Some(flat.substring(0, math.min(RejectRecord.maxDiagnosticExcerptLength, flat.length)))
    val hash = Some(StableIds.sha256Hex(if (raw.isEmpty) reason.wire else raw))
    val loc = {
      val trimmed = locator.replace('\n', ' ').replace('\r', ' ').trim
      val safe = if (trimmed.isEmpty) "unknown" else trimmed
      safe.substring(0, math.min(RejectRecord.maxSourceLocatorLength, safe.length))
    }
    RejectRecord(
      SchemaVersions.domain,
      source,
      loc,
      snapshot.filter(_.nonEmpty),
      runId,
      stage,
      reason,
      excerpt.orElse(Some(reason.wire)),
      hash
    )
  }
}

object ProvenanceFactory {
  def apply(
      source: SourceType,
      sourceRecordId: String,
      sourceUri: Option[String],
      snapshot: String,
      runId: String,
      notes: Vector[String] = Vector.empty,
      retrievalDate: Option[String] = None
  ): Provenance =
    Provenance(
      SchemaVersions.domain,
      source,
      sourceRecordId,
      sourceUri,
      snapshot,
      retrievalDate.filter(_.nonEmpty),
      None,
      runId,
      notes
    )

  /** Source, source record, and snapshot must travel together onto a derived record. */
  def mismatches(derived: Provenance, observed: Provenance): Boolean =
    derived.source != observed.source ||
      derived.sourceRecordId != observed.sourceRecordId ||
      derived.datasetSnapshot != observed.datasetSnapshot
}

object TextRefs {
  def unresolved(works: Seq[WorkRecord], docs: Seq[EmittedTextDocument]): Vector[String] = {
    val ids = docs.map(_.textId).toSet
    works.flatMap { work =>
      work.abstractTextRef.filter { ref =>
        StableIds.parseChunkOrProfileId(ref).isLeft || !ids.contains(ref) ||
        !docs.exists(doc =>
          doc.textId == ref &&
            doc.documentType == EmittedTextDocument.abstractDocumentType &&
            doc.entityId == work.workId &&
            ref.startsWith("chunk:") &&
            StableIds
              .chunkOrProfileId(
                doc.entityId,
                doc.sourceVersion,
                doc.documentType,
                doc.ordinal,
                doc.text
              )
              .contains(doc.textId)
        )
      }
    }.toVector
  }
}

final class TaskSink(
    val writeLine: (String, String) => Unit,
    val count: (String, Long) => Unit,
    val runId: String
) {
  def emit(record: EmittedRecord): Unit = emit(record, "")

  def emit(record: EmittedRecord, instance: String): Unit = {
    val key = if (instance.isEmpty) record.kind else record.kind + "\u0001" + instance
    val json = record.json
    writeLine(Lineage.key(key, Lineage.fromJson(json)), json)
    record match {
      case EmittedRecord.Rejected(reject) =>
        count(PrepCounters.Rejected, 1)
        reject.reasonCode match {
          case RejectReasonCode.DuplicateIdenticalObservation =>
            count(PrepCounters.Duplicate, 1)
          case RejectReasonCode.ConflictingObservation =>
            count(PrepCounters.Conflict, 1)
          case RejectReasonCode.OversizeBlock =>
            count(PrepCounters.OversizeBlock, 1)
          case RejectReasonCode.OversizeTeam =>
            // J07 and J08 both skip an oversize team. A separate counter keeps the run totals
            // from counting one team twice under the team counter (REJECTED counts both).
            if (reject.stage == PreparationStage.CoauthorPair)
              count(PrepCounters.OversizeTeamPairStep, 1)
            else count(PrepCounters.OversizeTeam, 1)
          case RejectReasonCode.SchemaFailure =>
            count(PrepCounters.SchemaFailure, 1)
          case _ => ()
        }
      case EmittedRecord.PairRec(_) | EmittedRecord.Candidate(_) =>
        count(PrepCounters.Accepted, 1)
        count(PrepCounters.EmittedPair, 1)
      case _ =>
        count(PrepCounters.Accepted, 1)
    }
  }

  def reject(
      source: Option[SourceType],
      locator: String,
      snapshot: Option[String],
      stage: PreparationStage,
      reason: RejectReasonCode,
      raw: String,
      instance: String = ""
  ): Unit =
    emit(
      EmittedRecord.Rejected(
        Rejects.record(source, locator, snapshot, runId, stage, reason, raw)
      ),
      instance
    )

  def checked[T](
      kind: T => EmittedRecord,
      value: T,
      stage: PreparationStage,
      locator: String,
      source: Option[SourceType],
      snapshot: Option[String],
      validate: T => Either[Vector[DomainViolation], T]
  ): Unit =
    validate(value) match {
      case Right(_) => emit(kind(value))
      case Left(errors) =>
        reject(
          source,
          locator,
          snapshot,
          stage,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
    }
}

object TaskSink {
  def from[K, V](
      context: TaskInputOutputContext[?, ?, Text, Text],
      runId: String
  ): TaskSink =
    new TaskSink(
      (kind, json) => context.write(new Text(kind), new Text(json)),
      (name, n) => context.getCounter(PrepCounters.Group, name).increment(n),
      runId
    )

  def guard(context: TaskAttemptContext, job: String): Unit = {
    val flag = context.getConfiguration.get(ConfKeys.FailJob)
    if (flag != null && flag == job)
      throw new IllegalStateException(s"injected failure in $job")
  }

  def runId(context: TaskAttemptContext): String =
    context.getConfiguration.get(ConfKeys.RunId)

  def limits(context: TaskAttemptContext): HadoopPrepConfig = {
    val conf = context.getConfiguration
    HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      conf.getLong(ConfKeys.MaxRecordBytes, 1L),
      conf.getLong(ConfKeys.MaxXmlEntityExpansion, 1L),
      math.max(1, conf.getInt("mapreduce.job.reduces", 1)),
      conf.getInt(ConfKeys.MaxBlock, 1),
      conf.getInt(ConfKeys.MaxPairs, 1),
      conf.getInt(ConfKeys.MaxTeam, 1),
      conf.getInt(ConfKeys.MaxSample, 1),
      "local-task",
      "none",
      false,
      executionMode(conf)
    )
  }

  def executionMode(conf: org.apache.hadoop.conf.Configuration): HadoopExecutionMode =
    if (conf.get(ConfKeys.ExecutionMode) == HadoopExecutionMode.Cluster.wire)
      HadoopExecutionMode.Cluster
    else HadoopExecutionMode.Local
}

object Digests {
  def sha256(path: Path): String = {
    val digest = java.security.MessageDigest.getInstance("SHA-256")
    val buffer = new Array[Byte](8192)
    val in = Files.newInputStream(path)
    try {
      var n = in.read(buffer)
      while (n >= 0) {
        if (n > 0) digest.update(buffer, 0, n)
        n = in.read(buffer)
      }
    } finally in.close()
    digest.digest().map(byte => f"${byte & 0xff}%02x").mkString
  }

  def sha256Text(text: String): String = StableIds.sha256Hex(text)

  def bytesOf(text: String): Long = text.getBytes(StandardCharsets.UTF_8).length.toLong
}

final case class OutputIdentity(
    runId: String,
    fingerprint: String,
    checksums: Map[String, String],
    snapshots: Map[String, String],
    retrievalDates: Map[String, String],
    partitions: Vector[String]
)

/** One non-metadata export file. Reuse compares path, length, and SHA-256. */
final case class ExportPart(path: String, bytes: Long, sha256: String)

object OutputGate {
  val MarkerName = "_SCHOLARCHAIN_COMPLETE"
  val ManifestName = "run-manifest.json"

  sealed trait Claim
  case object Proceed extends Claim
  case object Reuse extends Claim
  final case class Refuse(message: String) extends Claim

  def claim(dir: Path, identity: OutputIdentity): Claim =
    claim(new org.apache.hadoop.fs.Path(dir.toUri), identity, FsIO.configuration())

  def claim(dir: org.apache.hadoop.fs.Path, identity: OutputIdentity): Claim =
    claim(dir, identity, FsIO.configuration())

  def claim(
      dir: org.apache.hadoop.fs.Path,
      identity: OutputIdentity,
      conf: org.apache.hadoop.conf.Configuration
  ): Claim = {
    val fs =
      try dir.getFileSystem(conf)
      catch {
        case error: Exception =>
          return Refuse(filesystemMessage(dir, error))
      }
    if (!fs.exists(dir)) {
      fs.mkdirs(dir)
      Proceed
    } else if (matches(dir, identity, conf)) Reuse
    else
      Refuse(
        s"output path $dir exists without a matching completion marker; choose a new path"
      )
  }

  def write(dir: Path, identity: OutputIdentity): Unit =
    write(new org.apache.hadoop.fs.Path(dir.toUri), identity, FsIO.configuration())

  def write(dir: org.apache.hadoop.fs.Path, identity: OutputIdentity): Unit =
    write(dir, identity, FsIO.configuration())

  def write(
      dir: org.apache.hadoop.fs.Path,
      identity: OutputIdentity,
      conf: org.apache.hadoop.conf.Configuration
  ): Unit = {
    val parts = listExportParts(new org.apache.hadoop.fs.Path(dir, "export"), conf)
    FsIO.writeUtf8(
      new org.apache.hadoop.fs.Path(dir, MarkerName),
      markerJson(identity, parts),
      conf
    )
  }

  def listPartitions(exportDir: Path): Vector[String] =
    listPartitions(new org.apache.hadoop.fs.Path(exportDir.toUri), FsIO.configuration())

  def listPartitions(exportDir: org.apache.hadoop.fs.Path): Vector[String] =
    listPartitions(exportDir, FsIO.configuration())

  def listPartitions(
      exportDir: org.apache.hadoop.fs.Path,
      conf: org.apache.hadoop.conf.Configuration
  ): Vector[String] = {
    if (!FsIO.exists(exportDir, conf)) Vector.empty
    else {
      val root = exportDir.toUri.getPath.stripSuffix("/")
      FsIO
        .listFiles(exportDir, conf)
        .filter { file =>
          val name = file.getName
          !name.startsWith("_") && !name.startsWith(".") && !name.endsWith(".crc")
        }
        .map { file =>
          val child = file.toUri.getPath
          val rel =
            if (child.startsWith(root + "/")) child.drop(root.length + 1) else file.getName
          rel.split('/').dropRight(1).mkString("/")
        }
        .filter(_.nonEmpty)
        .distinct
        .sorted
    }
  }

  def matches(dir: Path, identity: OutputIdentity): Boolean =
    matches(new org.apache.hadoop.fs.Path(dir.toUri), identity, FsIO.configuration())

  def matches(dir: org.apache.hadoop.fs.Path, identity: OutputIdentity): Boolean =
    matches(dir, identity, FsIO.configuration())

  def matches(
      dir: org.apache.hadoop.fs.Path,
      identity: OutputIdentity,
      conf: org.apache.hadoop.conf.Configuration
  ): Boolean = {
    val marker = new org.apache.hadoop.fs.Path(dir, MarkerName)
    val manifest = new org.apache.hadoop.fs.Path(dir, ManifestName)
    if (!FsIO.isFile(marker, conf) || !FsIO.isFile(manifest, conf)) false
    else {
      val parsed =
        try Right(ujson.read(FsIO.readUtf8(marker, conf)))
        catch { case _: Throwable => Left(()) }
      parsed match {
        case Right(obj: ujson.Obj) if markerMatches(obj, identity) =>
          val recorded = recordedPartitions(obj)
          val agreed =
            identity.partitions.isEmpty || recorded.sorted == identity.partitions.sorted
          val recordedParts = recordedExportParts(obj)
          val actualParts = listExportParts(new org.apache.hadoop.fs.Path(dir, "export"), conf)
          recorded.nonEmpty && agreed &&
          recordedParts.nonEmpty && recordedParts == actualParts &&
          manifestMatches(manifest, identity, conf) && partitionsPresent(dir, recorded, conf)
        case _ => false
      }
    }
  }

  private def filesystemMessage(dir: org.apache.hadoop.fs.Path, error: Exception): String =
    s"${dir.toString} requires a Hadoop FileSystem implementation: ${Option(error.getMessage).getOrElse(error.toString)}"

  private def recordedPartitions(obj: ujson.Obj): Vector[String] =
    obj.value
      .get("partitions")
      .flatMap(_.arrOpt)
      .map(_.flatMap(_.strOpt).toVector)
      .getOrElse(Vector.empty)

  private def markerMatches(obj: ujson.Obj, identity: OutputIdentity): Boolean = {
    val fields = obj.value
    def strings(name: String, expected: Map[String, String]): Boolean =
      fields.get(name) match {
        case Some(value) =>
          value.objOpt.exists { found =>
            expected.forall { case (key, item) => found.get(key).contains(ujson.Str(item)) } &&
            found.size == expected.size
          }
        case None => false
      }
    fields.get("complete").contains(ujson.True) &&
    fields.get("runId").contains(ujson.Str(identity.runId)) &&
    fields.get("configFingerprint").contains(ujson.Str(identity.fingerprint)) &&
    fields.get("schemaVersion").contains(ujson.Str(SchemaVersions.domain)) &&
    fields.get("hadoopPrepSchema").contains(ujson.Str(SchemaVersions.hadoopPrep)) &&
    fields.get("transformationVersion").contains(ujson.Str(PrepLimits.TransformationVersion)) &&
    strings("inputChecksums", identity.checksums) &&
    strings("snapshots", identity.snapshots) &&
    strings("retrievalDates", identity.retrievalDates)
  }

  private def manifestMatches(
      path: org.apache.hadoop.fs.Path,
      identity: OutputIdentity,
      conf: org.apache.hadoop.conf.Configuration
  ): Boolean =
    try {
      val manifest = CoreJson.parse[RunManifest](FsIO.readUtf8(path, conf)).toOption
      manifest.exists { value =>
        value.runId == identity.runId &&
        value.configFingerprint == identity.fingerprint &&
        value.configSchemaVersion == SchemaVersions.hadoopPrep &&
        value.schemaVersion == SchemaVersions.domain &&
        value.datasetSnapshots
          .map(ref => ref.source.wire -> ref.snapshot)
          .toMap == identity.snapshots &&
        value.datasetSnapshots.flatMap(ref => ref.retrievalDate.map(ref.source.wire -> _)).toMap ==
          identity.retrievalDates
      }
    } catch { case _: Throwable => false }

  private def recordedExportParts(obj: ujson.Obj): Vector[ExportPart] =
    obj.value
      .get("exportParts")
      .flatMap(_.arrOpt)
      .map(_.flatMap {
        case item: ujson.Obj =>
          val path = item.value.get("path").flatMap(_.strOpt)
          val bytes = item.value.get("bytes").flatMap(_.numOpt).map(_.toLong)
          val hash = item.value.get("sha256").flatMap(_.strOpt)
          path.zip(bytes).zip(hash).map { case ((name, length), digest) =>
            ExportPart(name, length, digest)
          }
        case _ => None
      }.toVector)
      .getOrElse(Vector.empty)
      .sortBy(_.path)

  def listExportParts(
      exportDir: org.apache.hadoop.fs.Path,
      conf: org.apache.hadoop.conf.Configuration
  ): Vector[ExportPart] =
    if (!FsIO.exists(exportDir, conf)) Vector.empty
    else {
      val root = exportDir.toUri.getPath.stripSuffix("/")
      FsIO
        .listFiles(exportDir, conf)
        .flatMap { file =>
          val name = file.getName
          if (name.startsWith("_") || name.startsWith(".") || name.endsWith(".crc")) None
          else {
            val child = file.toUri.getPath
            val relative =
              if (child.startsWith(root + "/")) child.drop(root.length + 1) else name
            Some(
              ExportPart(
                relative,
                FsIO.length(file, conf),
                FsIO.sha256(file, conf)
              )
            )
          }
        }
        .sortBy(_.path)
    }

  private def partitionsPresent(
      dir: org.apache.hadoop.fs.Path,
      partitions: Vector[String],
      conf: org.apache.hadoop.conf.Configuration
  ): Boolean = {
    if (partitions.isEmpty) false
    else {
      val exportRoot = new org.apache.hadoop.fs.Path(dir, "export")
      partitions.forall { relative =>
        val folder = new org.apache.hadoop.fs.Path(exportRoot, relative)
        FsIO.exists(folder, conf) &&
        FsIO.listFiles(folder, conf).exists { file =>
          val name = file.getName
          !name.startsWith("_") && !name.startsWith(".") && !name.endsWith(".crc")
        }
      }
    }
  }

  def markerJson(identity: OutputIdentity): String = markerJson(identity, Vector.empty)

  def markerJson(identity: OutputIdentity, parts: Vector[ExportPart]): String = {
    def obj(values: Map[String, String]): ujson.Obj =
      ujson.Obj.from(values.toVector.sortBy(_._1).map { case (name, hash) =>
        name -> ujson.Str(hash)
      })
    ujson.write(
      ujson.Obj(
        "complete" -> true,
        "runId" -> identity.runId,
        "configFingerprint" -> identity.fingerprint,
        "inputChecksums" -> obj(identity.checksums),
        "snapshots" -> obj(identity.snapshots),
        "retrievalDates" -> obj(identity.retrievalDates),
        "partitions" -> ujson.Arr.from(identity.partitions.sorted.map(ujson.Str(_))),
        "exportParts" -> ujson.Arr.from(parts.sortBy(_.path).map { part =>
          ujson.Obj(
            "path" -> part.path,
            "bytes" -> ujson.Num(part.bytes.toDouble),
            "sha256" -> part.sha256
          )
        }),
        "schemaVersion" -> SchemaVersions.domain,
        "hadoopPrepSchema" -> SchemaVersions.hadoopPrep,
        "transformationVersion" -> PrepLimits.TransformationVersion
      )
    )
  }
}

object LogicalRecords {
  def lines(dir: Path): Vector[String] = {
    if (!Files.exists(dir)) Vector.empty
    else {
      val out = ArrayBuffer.empty[String]
      val walk = Files.walk(dir)
      try {
        walk.forEach { path =>
          val name = path.getFileName.toString
          if (
            Files.isRegularFile(path) && !name.startsWith("_") && !name.startsWith(".") &&
            !name.endsWith(".crc")
          ) {
            val text = Files.readString(path)
            text.split('\n').iterator.map(_.trim).filter(_.startsWith("{")).foreach(out += _)
          }
        }
      } finally walk.close()
      out.toVector
    }
  }

  def normalize(json: String, runId: String): String = {
    val parsed = ujson.read(json)
    ujson.write(walk(parsed, runId), indent = 0)
  }

  def equivalent(leftDir: Path, rightDir: Path, leftRun: String, rightRun: String): Boolean = {
    val left = lines(leftDir).map(line => normalize(line, leftRun)).sorted
    val right = lines(rightDir).map(line => normalize(line, rightRun)).sorted
    left == right
  }

  private def walk(
      value: ujson.Value,
      runId: String,
      processingObject: Boolean = true
  ): ujson.Value = value match {
    case obj: ujson.Obj =>
      val overflow =
        obj.value.get("reasonCode").contains(ujson.Str(RejectReasonCode.OversizeRecord.wire)) &&
          obj.value.get("source").exists {
            case ujson.Str(wire) => SourceType.values.exists(_.wire == wire)
            case _               => false
          } &&
          obj.value.get("datasetSnapshot").exists {
            case ujson.Str(snapshot) => snapshot.nonEmpty && Lineage.snapshotFits(snapshot)
            case _                   => false
          } &&
          obj.value.get("stage").exists {
            case ujson.Str(stage) =>
              PreparationStage.values.exists(value =>
                value != PreparationStage.Parse && value != PreparationStage.Normalize && value.wire == stage
              )
            case _ => false
          } &&
          obj.value.get("runId").contains(ujson.Str(runId))
      ujson.Obj.from(obj.value.toVector.sortBy(_._1).map { case (key, child) =>
        val next =
          if (key == "payloadHash") ujson.Str("HASH")
          else if (key == "runId" && processingObject && child == ujson.Str(runId)) ujson.Str("RUN")
          else if (key == "sourceLocator" && overflow) child match {
            case ujson.Str(locator) => ujson.Str(Lineage.logicalOverflowLocator(locator))
            case _                  => walk(child, runId, processingObject = false)
          }
          else
            walk(
              child,
              runId,
              processingObject =
                key == "provenance" || (key == "entry" && obj.value.contains("payloadHash"))
            )
        key -> next
      })
    case arr: ujson.Arr =>
      ujson.Arr.from(arr.value.map(child => walk(child, runId, processingObject = false)))
    case other => other
  }
}

object StatsFiles {
  def write(dir: String, task: String, values: Map[String, Long]): Unit =
    write(dir, task, values, FsIO.configuration())

  def write(
      dir: String,
      task: String,
      values: Map[String, Long],
      conf: org.apache.hadoop.conf.Configuration
  ): Unit = {
    val folder = FsPaths.file(dir)
    FsIO.mkdirs(folder, conf)
    val safe = task.replaceAll("[^A-Za-z0-9._-]", "_")
    val body = values.toVector.sortBy(_._1).map { case (k, v) => s"$k=$v" }.mkString("\n")
    FsIO.writeUtf8(new org.apache.hadoop.fs.Path(folder, safe + ".txt"), body + "\n", conf)
  }

  def max(dir: String, key: String): Long = max(dir, key, FsIO.configuration())

  def max(dir: String, key: String, conf: org.apache.hadoop.conf.Configuration): Long = {
    val folder = FsPaths.file(dir)
    if (!FsIO.exists(folder, conf)) 0L
    else {
      FsIO.listFiles(folder, conf).foldLeft(0L) { (best, file) =>
        val text =
          try FsIO.readUtf8(file, conf)
          catch { case _: Exception => "" }
        text.split('\n').foldLeft(best) { (current, line) =>
          val parts = line.split("=", 2)
          if (parts.length == 2 && parts(0) == key) math.max(current, parts(1).toLong)
          else current
        }
      }
    }
  }
}
