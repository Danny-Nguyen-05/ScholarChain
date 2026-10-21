package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.util.Try
import upickle.default.{ReadWriter, read, writeJs}

/** Closed JSON at the module boundary, including nested source records. */
object StrictJson {
  def parse[A: ReadWriter](text: String): Either[String, A] =
    Try {
      // ujson keeps the last duplicate key. Detect duplicates before that information is lost.
      val frames =
        scala.collection.mutable.ArrayBuffer.empty[Option[scala.collection.mutable.Set[String]]]
      var pos = 0
      while (pos < text.length) {
        text(pos) match {
          case '{'       => frames += Some(scala.collection.mutable.Set.empty[String])
          case '['       => frames += None
          case '}' | ']' => if (frames.nonEmpty) frames.remove(frames.size - 1)
          case '"' =>
            val start = pos; pos += 1; var escaped = false
            while (pos < text.length && (escaped || text(pos) != '"')) {
              if (escaped) escaped = false else if (text(pos) == '\\') escaped = true
              pos += 1
            }
            require(pos < text.length, "unterminated JSON string")
            var next = pos + 1; while (next < text.length && text(next).isWhitespace) next += 1
            if (next < text.length && text(next) == ':') {
              val key = ujson.read(text.substring(start, pos + 1)).str
              val seen = frames.lastOption.flatten.getOrElse(
                throw new IllegalArgumentException("JSON key outside object")
              )
              require(!seen(key), "duplicate JSON key: " + key); seen += key
            }
          case _ => ()
        }
        pos += 1
      }
      val raw = ujson.read(text)
      val value = read[A](raw)
      def keys(input: ujson.Value, encoded: ujson.Value, at: String): Unit =
        (input, encoded) match {
          case (a: ujson.Obj, b: ujson.Obj) =>
            require(a.value.keySet.subsetOf(b.value.keySet), s"unknown JSON key at $at")
            a.value.foreach { case (k, v) => keys(v, b(k), s"$at.$k") }
          case (a: ujson.Arr, b: ujson.Arr) =>
            require(a.value.size == b.value.size, s"JSON array cardinality changed at $at")
            a.value.zip(b.value).zipWithIndex.foreach { case ((x, y), i) => keys(x, y, s"$at[$i]") }
          case _ => require(input == encoded, s"JSON value/type changed while decoding at $at")
        }
      keys(raw, writeJs(value), "$")
      value
    }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))

  def canonical(value: ujson.Value): String = {
    def sorted(v: ujson.Value): ujson.Value = v match {
      case o: ujson.Obj =>
        ujson.Obj.from(o.value.toVector.sortBy(_._1).map((k, x) => k -> sorted(x)))
      case a: ujson.Arr => ujson.Arr.from(a.value.map(sorted))
      case x            => x
    }
    sorted(value).render()
  }
  def hash[A: ReadWriter](value: A): String = StableIds.sha256Hex(canonical(writeJs(value)))
  def file(path: Path, maxBytes: Long): Either[String, String] = Try {
    require(
      Files.isRegularFile(path) && !Files.isSymbolicLink(path),
      "regular nonsymlink file required"
    )
    require(Files.size(path) <= maxBytes, "file byte bound exceeded")
    val decoder = UTF_8.newDecoder().onMalformedInput(java.nio.charset.CodingErrorAction.REPORT)
    decoder.decode(java.nio.ByteBuffer.wrap(Files.readAllBytes(path))).toString
  }.toEither.left.map(_.getMessage)
}

final case class EntityPolicy(
    rejectThreshold: Double,
    acceptThreshold: Double,
    llmBandMin: Double,
    llmBandMax: Double,
    yearToleranceYears: Int,
    minimumIndependentGroupsForAccept: Int,
    supportiveFeatureMin: Double,
    requiredGroups: Vector[String],
    weights: Map[String, Double],
    featureGroups: Map[String, String],
    bibliographicEnabled: Boolean,
    bibliographicMinTitle: Double,
    bibliographicMinAuthors: Double,
    bibliographicMaxYearDistance: Int
) derives ReadWriter

final case class ResolutionPolicy(
    schemaVersion: String,
    policyVersion: String,
    featurePolicyVersion: String,
    normalizationVersion: String,
    supersedes: String,
    scoreSemantics: String,
    work: EntityPolicy,
    researcher: EntityPolicy,
    sourceReliability: Map[String, Double]
) derives ReadWriter {
  def fingerprint: String = StrictJson.hash(this)
  def forEntity(kind: ResolutionEntityType): EntityPolicy =
    if (kind == ResolutionEntityType.Work) work else researcher
}

object ResolutionPolicy {
  val schema = "scholarchain.er-policy.v1"
  val featureNames: Set[String] = Set(
    "title",
    "name",
    "initials",
    "authorOverlap",
    "coauthorOverlap",
    "authorOrder",
    "affiliation",
    "yearCompatibility",
    "venue",
    "identifier",
    "citationNeighborhood",
    "sourceReliability"
  )
  def parse(text: String): Either[String, ResolutionPolicy] =
    StrictJson.parse[ResolutionPolicy](text).flatMap(validate)
  def load(path: Path): Either[String, ResolutionPolicy] =
    StrictJson.file(path, 1048576).flatMap(parse)
  def example: ResolutionPolicy = parse(ResourceText.read("phase5-policy.v1.json"))
    .fold(e => throw new IllegalStateException(e), identity)
  def validate(p: ResolutionPolicy): Either[String, ResolutionPolicy] = Try {
    require(
      p.schemaVersion == schema && p.policyVersion.nonEmpty && p.featurePolicyVersion == "er-features-v2" && p.normalizationVersion == Normalization.version,
      "unsupported policy/feature/normalization version"
    )
    require(
      p.supersedes == "ScholarChainConfig.entityResolution",
      "legacy settings must be explicitly superseded"
    )
    require(
      p.scoreSemantics == "UNCALIBRATED_AVAILABLE_WEIGHTED_AVERAGE_TIMES_SOURCE_RELIABILITY",
      "unsupported score semantics"
    )
    require(
      p.sourceReliability.keySet == Set("DBLP", "OPENALEX", "CROSSREF", "ORCID"),
      "complete source reliability map required"
    )
    def unit(n: Double): Boolean = n.isFinite && n >= 0 && n <= 1
    require(
      p.sourceReliability.values.forall(n => unit(n) && n > 0),
      "source reliability must be in (0,1]"
    )
    Vector(p.work, p.researcher).foreach { e =>
      require(
        Vector(
          e.rejectThreshold,
          e.acceptThreshold,
          e.llmBandMin,
          e.llmBandMax,
          e.supportiveFeatureMin,
          e.bibliographicMinTitle,
          e.bibliographicMinAuthors
        ).forall(unit),
        "policy values must be finite in [0,1]"
      )
      require(
        e.rejectThreshold < e.llmBandMin && e.llmBandMin <= e.llmBandMax && e.llmBandMax < e.acceptThreshold,
        "LLM band must lie strictly inside reject/accept gap"
      )
      require(
        e.yearToleranceYears > 0 && e.bibliographicMaxYearDistance >= 0 && e.minimumIndependentGroupsForAccept >= 2 && e.supportiveFeatureMin > 0,
        "invalid evidence bounds"
      )
      require(
        e.weights.nonEmpty && e.weights.keySet.subsetOf(
          featureNames -- Set("sourceReliability", "citationNeighborhood")
        ),
        "unsupported scoring feature"
      )
      require(
        e.weights.values.forall(n => n.isFinite && n > 0) && e.weights.values.sum.isFinite,
        "positive finite feature weights required"
      )
      require(
        e.featureGroups.keySet == e.weights.keySet && e.featureGroups.values.forall(_.nonEmpty),
        "every scored feature needs an explicit evidence group"
      )
      require(
        e.requiredGroups.distinct == e.requiredGroups && e.requiredGroups.forall(
          e.featureGroups.values.toSet
        ),
        "invalid required evidence groups"
      )
      require(
        e.minimumIndependentGroupsForAccept <= e.featureGroups.values.toSet.size,
        "impossible evidence sufficiency"
      )
    }
    require(
      p.work.weights.keySet.subsetOf(
        Set("title", "authorOverlap", "yearCompatibility", "venue", "identifier")
      ),
      "researcher feature in work policy"
    )
    require(
      p.researcher.weights.keySet.subsetOf(
        Set(
          "name",
          "initials",
          "coauthorOverlap",
          "authorOrder",
          "affiliation",
          "yearCompatibility",
          "venue",
          "identifier"
        )
      ),
      "work feature in researcher policy"
    )
    require(
      p.researcher.featureGroups.get("name").forall(_ == "name") && p.researcher.featureGroups
        .get("initials")
        .forall(_ == "name") && p.researcher.featureGroups.get("authorOrder").forall(_ == "name"),
      "correlated name/order evidence must share name group"
    )
    require(
      p.work.featureGroups.get("title").forall(_ == "bibliography") && p.work.featureGroups
        .get("venue")
        .forall(_ == "bibliography"),
      "correlated title/venue evidence must share bibliography group"
    )
    require(!p.researcher.bibliographicEnabled, "bibliographic rule is work-only")
    p
  }.toEither.left.map(_.getMessage)
}

final case class InputBounds(
    maxInputBytes: Long,
    maxInputRecords: Int,
    maxRecordBytes: Int,
    maxLookupObservations: Int,
    maxExportParts: Int
) derives ReadWriter
final case class BlockingBounds(
    maxMembersPerBlock: Int,
    maxPairsPerBlock: Int,
    maxPairsPerRun: Int,
    maxCrossPublicationPairsPerMention: Int,
    maxEvidenceBytesPerPair: Int,
    maxBlockMemberships: Int,
    maxPairAttempts: Int
) derives ReadWriter
final case class AdjudicationBounds(
    maxRequestBytes: Int,
    maxResponseBytes: Int,
    timeoutMs: Int,
    maxRetries: Int,
    maxConcurrentCalls: Int,
    maxRequests: Int,
    maxInputTokens: Int,
    maxOutputTokens: Int,
    maxSpendUsd: Double,
    provider: String,
    model: String,
    modelVersion: String,
    generationSettings: Map[String, String],
    maxRationaleCharacters: Int,
    maxReasonCodes: Int,
    maxFieldRefs: Int
) derives ReadWriter
final case class ResolutionConfig(
    schemaVersion: String,
    legacySettings: String,
    input: InputBounds,
    blocking: BlockingBounds,
    adjudication: AdjudicationBounds,
    maxConstraintEntries: Int,
    maxOutputBytes: Long
) derives ReadWriter {
  def fingerprint: String = StrictJson.hash(this)
}
object ResolutionConfig {
  def parse(text: String): Either[String, ResolutionConfig] =
    StrictJson.parse[ResolutionConfig](text).flatMap(validate)
  def load(path: Path): Either[String, ResolutionConfig] =
    StrictJson.file(path, 1048576).flatMap(parse)
  def example: ResolutionConfig = parse(ResourceText.read("phase5-config.v1.json"))
    .fold(e => throw new IllegalStateException(e), identity)
  def validate(c: ResolutionConfig): Either[String, ResolutionConfig] = Try {
    require(
      c.schemaVersion == "scholarchain.er-config.v1" && c.legacySettings == "SUPERSEDED_NO_SIMULTANEOUS_LEGACY_SETTINGS",
      "unsupported config or competing legacy settings"
    )
    val i = c.input; val b = c.blocking; val a = c.adjudication
    require(
      Vector(
        i.maxInputRecords,
        i.maxRecordBytes,
        i.maxLookupObservations,
        i.maxExportParts,
        b.maxMembersPerBlock,
        b.maxPairsPerBlock,
        b.maxPairsPerRun,
        b.maxCrossPublicationPairsPerMention,
        b.maxEvidenceBytesPerPair,
        b.maxBlockMemberships,
        b.maxPairAttempts,
        c.maxConstraintEntries,
        a.maxRequestBytes,
        a.maxResponseBytes,
        a.timeoutMs,
        a.maxConcurrentCalls,
        a.maxRationaleCharacters,
        a.maxReasonCodes,
        a.maxFieldRefs
      ).forall(_ > 0) && i.maxInputBytes > 0 && c.maxOutputBytes > 0,
      "positive finite bounds required"
    )
    require(
      i.maxRecordBytes <= i.maxInputBytes && b.maxEvidenceBytesPerPair <= a.maxRequestBytes,
      "inconsistent byte bounds"
    )
    require(
      a.maxConcurrentCalls == 1 && a.maxRetries >= 0 && a.maxRetries <= 3 && a.maxRequests >= 0 && a.maxInputTokens >= 0 && a.maxOutputTokens >= 0 && a.maxSpendUsd == 0,
      "offline mode requires sequential bounded retries and zero monetary allowance"
    )
    require(
      a.provider == "deterministic-fake" && a.model.nonEmpty && a.modelVersion.nonEmpty,
      "5B provider must be explicitly fake"
    )
    c
  }.toEither.left.map(_.getMessage)
}
object ResourceText {
  def read(name: String): String = {
    val in = Option(getClass.getClassLoader.getResourceAsStream(name))
      .getOrElse(throw new IllegalArgumentException("missing resource " + name))
    try new String(in.readAllBytes(), UTF_8)
    finally in.close()
  }
}
