package edu.uic.cs441.scholarchain.core

import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.UUID
import scala.util.matching.Regex

/** Source wire, source-record id, and author ordinal embedded in a mention id. */
final case class ParsedMentionId(sourceWire: String, sourceRecordId: String, ordinal: Int)

/** Stable identifier formulas. Hashes are SHA-256 over UTF-8, lowercase hex, with the listed fields
  * joined by a single LF and no trailing LF.
  *
  * Work ID: `work:{namespace}:{authoritativeSourceId}`. Prefer `doi` when a DOI is present,
  * otherwise `arxiv`, otherwise the source-native id (`dblp` or `openalex`).
  *
  * Researcher ID: `researcher:orcid:{orcid}` only for a checksum-valid ORCID supplied as a
  * validated external identifier. Otherwise
  * `researcher:scholarchain:{identityPolicyVersion}:{sha256}`. The hash covers policy version,
  * source, source record id, author ordinal, and normalized name. The same name on another record
  * or ordinal is a different provisional id. OpenAlex author IDs are rejected here; they are
  * disambiguation hypotheses.
  *
  * Coauthor edge ID: `coauthor-edge:{sha256}` of the canonical ordered researcher ids, window
  * start, window end, and policy version.
  *
  * Chunk or profile ID: `chunk:{sha256}` or `profile:{sha256}` of entity id, source version,
  * document type, ordinal (empty when omitted), and the SHA-256 hex of the text.
  *
  * Non-text evidence ID: `evidence:graph-path:{sha256}`, `evidence:metric:{sha256}`, or
  * `evidence:edge:{sha256}`. The hash covers the kind and that kind's fields, joined by a single LF
  * and no trailing LF. Graph-path fields are the node ids in path order. Metric fields are
  * researcher id, collaboration-metric wire name, window start, window end, and policy version. The
  * edge field is one `graph-edge:` or `coauthor-edge:` id. Text stays on `chunk:` and `profile:`.
  *
  * Graph edge ID: `graph-edge:{sha256}` of edge type, canonical endpoints, policy version, and
  * source-evidence pointer. `COAUTHORED_WITH` sorts endpoints; other types keep direction.
  *
  * Run ID: `run:{uuid version 4}` from a caller-supplied UUID. The id does not contain a timestamp.
  * Store it on an immutable [[RunManifest]].
  *
  * Undirected pair order: Scala `String.compareTo` (UTF-16 code units). The lesser id is endpoint
  * A. Equal ids are rejected.
  */
object StableIds {
  private val doiPattern: Regex = "^10\\.\\d{4,9}/\\S+$".r
  private val dblpKeyPattern: Regex = "^[A-Za-z0-9][A-Za-z0-9._:/-]*$".r
  private val openAlexWorkPattern: Regex = "^W\\d+$".r
  private val arxivPattern: Regex =
    "^(?:\\d{4}\\.\\d{4,5}(?:v\\d+)?|[a-z-]+(?:\\.[A-Z]{2})?/\\d{7})$".r
  private val orcidPattern: Regex = "^\\d{4}-\\d{4}-\\d{4}-\\d{3}[\\dX]$".r
  private val policyPattern: Regex = "^[a-z0-9][a-z0-9._-]{0,63}$".r
  private val hex64: Regex = "^[0-9a-f]{64}$".r
  private val runPattern: Regex =
    "^run:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$".r
  private val nonTextEvidenceIdPattern: Regex =
    "^evidence:(graph-path|metric|edge):[0-9a-f]{64}$".r
  private val nonTextEvidenceKinds: Set[String] = Set("graph-path", "metric", "edge")
  private val openAlexAuthorPattern: Regex = "^A\\d+$".r
  private val rorPattern: Regex = "^0[0-9a-hjkmnp-tv-z]{6}[0-9]{2}$".r

  def sha256Hex(text: String): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    digest
      .digest(text.getBytes(StandardCharsets.UTF_8))
      .map(byte => f"${byte & 0xff}%02x")
      .mkString
  }

  def workIdFromDoi(rawDoi: String): Either[DomainViolation, String] =
    normalizeDoi(rawDoi).map(doi => s"work:doi:$doi")

  def workIdFromDblpKey(key: String): Either[DomainViolation, String] =
    if (dblpKeyPattern.matches(key)) Right(s"work:dblp:$key")
    else Left(malformed("dblp key", key))

  def workIdFromOpenAlex(raw: String): Either[DomainViolation, String] =
    openAlexWorkToken(raw).map(token => s"work:openalex:$token")

  def workIdFromArxiv(raw: String): Either[DomainViolation, String] = {
    val token = raw.trim.stripPrefix("arXiv:").stripPrefix("arxiv:")
    if (arxivPattern.matches(token)) Right(s"work:arxiv:$token")
    else Left(malformed("arxiv id", raw))
  }

  /** Authoritative work id. DOI wins over arXiv, which wins over a source-native id. This does not
    * merge conflicting years or titles across sources.
    */
  def authoritativeWorkId(
      doi: Option[String],
      arxivId: Option[String],
      sourceNative: Either[DomainViolation, String]
  ): Either[DomainViolation, String] =
    doi.map(workIdFromDoi) match {
      case Some(fromDoi) => fromDoi
      case None =>
        arxivId.map(workIdFromArxiv) match {
          case Some(fromArxiv) => fromArxiv
          case None            => sourceNative
        }
    }

  /** DOI embedded in a provenance or external URI, when present and syntactically valid. */
  def doiFromSourceUri(sourceUri: Option[String]): Option[String] =
    sourceUri.flatMap(uri => normalizeDoi(uri).toOption)

  /** arXiv token embedded in a provenance or external URI, when present and syntactically valid. */
  def arxivFromSourceUri(sourceUri: Option[String]): Option[String] =
    sourceUri.flatMap { uri =>
      val trimmed = uri.trim
      val candidate =
        if (trimmed.matches("(?i)^https?://arxiv\\.org/(?:abs|pdf)/.*"))
          trimmed.replaceFirst("(?i)^https?://arxiv\\.org/(?:abs|pdf)/", "").stripSuffix(".pdf")
        else trimmed.replaceFirst("(?i)^arxiv:", "").trim
      workIdFromArxiv(candidate).toOption.map(_.stripPrefix("work:arxiv:"))
    }

  def doiFromWorkId(workId: String): Option[String] =
    workId.split(":", 3) match {
      case Array("work", "doi", rest) => Some(rest)
      case _                          => None
    }

  def arxivFromWorkId(workId: String): Option[String] =
    workId.split(":", 3) match {
      case Array("work", "arxiv", rest) => Some(rest)
      case _                            => None
    }

  def sourceNativeWorkId(
      source: SourceType,
      sourceRecordId: String
  ): Either[DomainViolation, String] =
    source match {
      case SourceType.Dblp     => workIdFromDblpKey(sourceRecordId)
      case SourceType.OpenAlex => workIdFromOpenAlex(sourceRecordId)
      case SourceType.Crossref => workIdFromDoi(sourceRecordId)
      case other =>
        Left(
          DomainViolation(
            ViolationCode.InconsistentRecord,
            s"source ${other.wire} has no native work id without doi or arxiv"
          )
        )
    }

  /** Authoritative work id for one source observation from record fields, not provenance URIs
    * alone.
    */
  def authoritativeWorkIdForRecord(
      source: SourceType,
      sourceRecordId: String,
      doi: Option[String],
      arxivId: Option[String]
  ): Either[DomainViolation, String] =
    if (source == SourceType.Crossref) workIdFromDoi(sourceRecordId)
    else authoritativeWorkId(doi, arxivId, sourceNativeWorkId(source, sourceRecordId))

  /** Authoritative work id for a validated [[WorkRecord]] observation. */
  def authoritativeWorkIdForWorkRecord(work: WorkRecord): Either[DomainViolation, String] =
    authoritativeWorkIdForRecord(work.source, work.sourceRecordId, work.doi, work.arxivId)

  def normalizeDoi(raw: String): Either[DomainViolation, String] = {
    val stripped = raw.trim
      .replaceFirst("(?i)^https?://(dx\\.)?doi\\.org/", "")
      .replaceFirst("(?i)^doi:", "")
      .trim
      .toLowerCase(java.util.Locale.ROOT)
    if (doiPattern.matches(stripped)) Right(stripped)
    else Left(malformed("doi", raw))
  }

  def researcherIdFromValidatedOrcid(raw: String): Either[DomainViolation, String] = {
    val orcid = raw.trim
      .replaceFirst("(?i)^https?://orcid\\.org/", "")
      .replaceFirst("(?i)^orcid:", "")
    if (!orcidPattern.matches(orcid) || !orcidChecksumValid(orcid))
      Left(malformed("orcid", raw))
    else Right(s"researcher:orcid:$orcid")
  }

  def researcherIdFromValidatedExternal(
      namespace: String,
      externalId: String
  ): Either[DomainViolation, String] =
    namespace.toLowerCase(java.util.Locale.ROOT) match {
      case "orcid" => researcherIdFromValidatedOrcid(externalId)
      case "openalex" | "openalex-author" =>
        Left(
          DomainViolation(
            ViolationCode.UnconfirmedIdentity,
            "OpenAlex author IDs are disambiguation hypotheses, not validated researcher IDs"
          )
        )
      case other =>
        Left(malformed("researcher namespace", other))
    }

  def provisionalResearcherId(
      identityPolicyVersion: String,
      source: SourceType,
      sourceRecordId: String,
      ordinal: Int,
      normalizedName: String
  ): Either[DomainViolation, String] =
    if (!policyPattern.matches(identityPolicyVersion))
      Left(malformed("identity policy version", identityPolicyVersion))
    else if (sourceRecordId.trim.isEmpty || ordinal < 1 || normalizedName.trim.isEmpty)
      Left(malformed("provisional researcher material", sourceRecordId))
    else {
      val hash = sha256Hex(
        Seq(
          identityPolicyVersion,
          source.wire,
          sourceRecordId.trim,
          ordinal.toString,
          normalizedName
        ).mkString("\n")
      )
      Right(s"researcher:scholarchain:$identityPolicyVersion:$hash")
    }

  def canonicalPair(left: String, right: String): Either[DomainViolation, (String, String)] =
    if (left == right)
      Left(
        DomainViolation(
          ViolationCode.InvalidPairOrder,
          "undirected pair endpoints must be distinct"
        )
      )
    else if (left.compareTo(right) < 0) Right((left, right))
    else if (right.compareTo(left) < 0) Right((right, left))
    else
      Left(DomainViolation(ViolationCode.InvalidPairOrder, "pair endpoints did not order"))

  def coauthorEdgeId(
      researcherA: String,
      researcherB: String,
      windowStartYear: Int,
      windowEndYear: Int,
      policyVersion: String
  ): Either[DomainViolation, String] =
    for {
      _ <- requirePolicy(policyVersion)
      _ <- requireWindow(windowStartYear, windowEndYear)
      _ <- parseResearcherId(researcherA)
      _ <- parseResearcherId(researcherB)
      ordered <- canonicalPair(researcherA, researcherB)
    } yield {
      val hash = sha256Hex(
        Seq(
          ordered._1,
          ordered._2,
          windowStartYear.toString,
          windowEndYear.toString,
          policyVersion
        ).mkString("\n")
      )
      s"coauthor-edge:$hash"
    }

  def chunkOrProfileId(
      entityId: String,
      sourceVersion: String,
      documentType: String,
      ordinal: Option[Int],
      text: String
  ): Either[DomainViolation, String] =
    if (entityId.trim.isEmpty || sourceVersion.trim.isEmpty || documentType.trim.isEmpty)
      Left(malformed("chunk material", documentType))
    else if (ordinal.exists(_ < 0))
      Left(malformed("chunk ordinal", ordinal.toString))
    else {
      val textHash = sha256Hex(text)
      val hash = sha256Hex(
        Seq(
          entityId.trim,
          sourceVersion.trim,
          documentType.trim,
          ordinal.map(_.toString).getOrElse(""),
          textHash
        ).mkString("\n")
      )
      val prefix = if (documentType.trim == "researcher-profile") "profile" else "chunk"
      Right(s"$prefix:$hash")
    }

  /** Stable id for graph-path, metric, and edge evidence. See the object comment for the fields
    * each kind hashes. `chunk:` and `profile:` are not produced here.
    */
  def nonTextEvidenceId(kind: String, fields: Seq[String]): Either[DomainViolation, String] = {
    val trimmed = fields.map(_.trim)
    val checked =
      if (!nonTextEvidenceKinds.contains(kind) || trimmed.isEmpty || trimmed.exists(_.isEmpty))
        Left(malformed("non-text evidence", kind))
      else
        kind match {
          case "graph-path" => validateGraphPath(trimmed)
          case "metric"     => validateMetricEvidence(trimmed)
          case "edge"       => validateEdgeEvidence(trimmed)
          case other        => Left(malformed("non-text evidence", other))
        }
    checked.map { _ =>
      val hash = sha256Hex((kind +: trimmed).mkString("\n"))
      s"evidence:$kind:$hash"
    }
  }

  /** Work evidence retains the original work-id hash field. SourceRecord evidence hashes a
    * canonical JSON array ["source-record", source wire, sourceRecordId, snapshot] as one field.
    * JSON escapes delimiters, so distinct source observations cannot alias the LF hash inputs.
    */
  def graphEvidencePointer(evidence: GraphSourceEvidence): Either[DomainViolation, String] =
    evidence match {
      case GraphSourceEvidence.Work(id) => parseWorkId(id)
      case GraphSourceEvidence.SourceRecord(source, id, snapshot) =>
        for {
          _ <- parseSourceRecordId(source, id)
          _ <- snapshotId(source, snapshot)
        } yield ujson.Arr("source-record", source.wire, id, snapshot).toString
    }

  def parseSourceRecordId(source: SourceType, id: String): Either[DomainViolation, String] =
    source match {
      case SourceType.Dblp     => workIdFromDblpKey(id).map(_ => id)
      case SourceType.Crossref => normalizeDoi(id).map(_ => id)
      case SourceType.OpenAlex =>
        val token = id.replaceFirst("^https://openalex\\.org/", "")
        if (token.matches("[WAISTC][1-9]\\d*")) Right(id)
        else Left(malformed("OpenAlex source record", id))
      case SourceType.Orcid =>
        val parts = id.stripPrefix("/").split("/", -1)
        researcherIdFromValidatedOrcid(parts.head).flatMap { _ =>
          if (
            parts.length == 1 || (parts.length == 3 && Set(
              "employment",
              "education",
              "work",
              "funding",
              "peer-review",
              "research-resource",
              "qualification",
              "membership",
              "service",
              "distinction",
              "invited-position"
            ).contains(parts(1)) && parts(2).matches("[1-9]\\d*"))
          ) Right(id)
          else Left(malformed("ORCID source record", id))
        }
      case SourceType.ScholarChain => Left(malformed("external source record", id))
    }

  def graphEdgeId(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String,
      policyVersion: String,
      sourceEvidence: GraphSourceEvidence
  ): Either[DomainViolation, String] =
    graphEvidencePointer(sourceEvidence).flatMap(pointer =>
      hashGraphEdge(edgeType, fromId, toId, policyVersion, pointer)
    )

  /** Compatibility constructor for a work evidence pointer; arbitrary text is rejected. */
  def graphEdgeId(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String,
      policyVersion: String,
      sourceEvidence: String
  ): Either[DomainViolation, String] =
    graphEdgeId(edgeType, fromId, toId, policyVersion, GraphSourceEvidence.Work(sourceEvidence))

  private def hashGraphEdge(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String,
      policyVersion: String,
      sourceEvidence: String
  ): Either[DomainViolation, String] =
    for {
      _ <- requirePolicy(policyVersion)
      _ <-
        if (sourceEvidence.trim.isEmpty) Left(malformed("graph edge evidence", sourceEvidence))
        else Right(())
      endpoints <- canonicalGraphEndpoints(edgeType, fromId, toId)
    } yield {
      val hash = sha256Hex(
        Seq(edgeType.wire, endpoints._1, endpoints._2, policyVersion, sourceEvidence.trim)
          .mkString("\n")
      )
      s"graph-edge:$hash"
    }

  def canonicalGraphEndpoints(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String
  ): Either[DomainViolation, (String, String)] =
    if (fromId.trim.isEmpty || toId.trim.isEmpty)
      Left(malformed("graph endpoint", fromId))
    else if (GraphEdgeType.isUndirected(edgeType)) canonicalPair(fromId, toId)
    else if (fromId == toId)
      Left(DomainViolation(ViolationCode.InvalidPairOrder, "graph edge endpoints must differ"))
    else Right((fromId, toId))

  /** Timestamp-independent run id. `uuid` must be version 4; the clock is not an input. */
  def newRunId(uuid: UUID): Either[DomainViolation, String] = {
    val rendered = s"run:${uuid.toString.toLowerCase(java.util.Locale.ROOT)}"
    parseRunId(rendered)
  }

  def mentionId(source: SourceType, sourceRecordId: String, ordinal: Int): String =
    s"mention:${source.wire.toLowerCase(java.util.Locale.ROOT)}:$sourceRecordId#$ordinal"

  def venueIdFromDblpBooktitle(booktitle: String): Either[DomainViolation, String] = {
    val slug = TextNorm
      .collapse(booktitle)
      .replaceAll("[^a-z0-9]+", "-")
      .replaceAll("(^-+|-+$)", "")
    if (slug.isEmpty) Left(malformed("venue label", booktitle))
    else Right(s"venue:dblp-booktitle:$slug")
  }

  def institutionIdFromRor(raw: String): Either[DomainViolation, String] = {
    val token = raw.trim
      .replaceFirst("(?i)^https?://ror\\.org/", "")
      .toLowerCase(java.util.Locale.ROOT)
    if (rorPattern.matches(token)) Right(s"institution:ror:$token")
    else Left(malformed("ror", raw))
  }

  def institutionIdFromRinggold(raw: String): Either[DomainViolation, String] =
    if (raw.matches("[1-9]\\d*")) Right(s"institution:ringgold:$raw")
    else Left(malformed("ringgold", raw))

  def institutionIdFromOpenAlex(raw: String): Either[DomainViolation, String] = {
    val token = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    if (token.matches("I[1-9]\\d*")) Right(s"institution:openalex:$token")
    else Left(malformed("openalex institution", raw))
  }

  def topicIdFromOpenAlex(raw: String): Either[DomainViolation, String] = {
    val token = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    if (token.matches("[TC][1-9]\\d*")) Right(s"topic:openalex:$token")
    else Left(malformed("openalex topic", raw))
  }

  def snapshotId(source: SourceType, snapshot: String): Either[DomainViolation, String] =
    if (snapshot.matches("[A-Za-z0-9._:-]+"))
      Right(s"snapshot:${source.wire.toLowerCase(java.util.Locale.ROOT)}:$snapshot")
    else Left(malformed("snapshot", snapshot))

  def parseVenueId(value: String): Either[DomainViolation, String] =
    value.split(":", 3) match {
      case Array("venue", "dblp-booktitle", slug) if slug.matches("[a-z0-9]+(?:-[a-z0-9]+)*") =>
        Right(value)
      case Array("venue", "openalex", token) if token.matches("S[1-9]\\d*")          => Right(value)
      case Array("venue", "issn", token) if token.matches("[0-9]{4}-[0-9]{3}[0-9X]") => Right(value)
      case _ => Left(malformed("venue id", value))
    }

  def parseInstitutionId(value: String): Either[DomainViolation, String] =
    value.split(":", 3) match {
      case Array("institution", "ror", token) if institutionIdFromRor(token).contains(value) =>
        Right(value)
      case Array("institution", "ringgold", token) if token.matches("[1-9]\\d*")  => Right(value)
      case Array("institution", "openalex", token) if token.matches("I[1-9]\\d*") => Right(value)
      case _ => Left(malformed("institution id", value))
    }

  def parseTopicId(value: String): Either[DomainViolation, String] =
    value.split(":", 3) match {
      case Array("topic", "openalex", token) if token.matches("[TC][1-9]\\d*") => Right(value)
      case _ => Left(malformed("topic id", value))
    }

  def parseWorkId(value: String): Either[DomainViolation, String] =
    value.split(":", 3) match {
      case Array("work", "doi", rest)
          if doiPattern.matches(rest) && normalizeDoi(rest).contains(rest) =>
        Right(value)
      case Array("work", "dblp", rest) if dblpKeyPattern.matches(rest)          => Right(value)
      case Array("work", "openalex", rest) if openAlexWorkPattern.matches(rest) => Right(value)
      case Array("work", "arxiv", rest) if arxivPattern.matches(rest)           => Right(value)
      case _ => Left(malformed("work id", value))
    }

  def parseResearcherId(value: String): Either[DomainViolation, String] =
    if (value.startsWith("researcher:orcid:")) {
      val orcid = value.stripPrefix("researcher:orcid:")
      if (orcidPattern.matches(orcid) && orcidChecksumValid(orcid)) Right(value)
      else Left(malformed("researcher id", value))
    } else if (value.startsWith("researcher:scholarchain:")) {
      value.split(":", 4) match {
        case Array("researcher", "scholarchain", policy, hash)
            if policyPattern.matches(policy) && hex64.matches(hash) =>
          Right(value)
        case _ => Left(malformed("researcher id", value))
      }
    } else Left(malformed("researcher id", value))

  def parseCoauthorEdgeId(value: String): Either[DomainViolation, String] =
    value.stripPrefix("coauthor-edge:") match {
      case hash if value.startsWith("coauthor-edge:") && hex64.matches(hash) => Right(value)
      case _ => Left(malformed("coauthor edge id", value))
    }

  def parseChunkOrProfileId(value: String): Either[DomainViolation, String] = {
    val hash = value.drop(value.indexOf(':') + 1)
    if (
      (value.startsWith("chunk:") || value.startsWith("profile:")) && hex64.matches(
        hash
      ) && value.count(_ == ':') == 1
    ) Right(value)
    else Left(malformed("chunk or profile id", value))
  }

  def parseNonTextEvidenceId(value: String): Either[DomainViolation, String] =
    if (nonTextEvidenceIdPattern.matches(value)) Right(value)
    else Left(malformed("non-text evidence id", value))

  /** Accepts a text chunk or profile id, or a graph-path, metric, or edge evidence id. */
  def parseEvidenceId(value: String): Either[DomainViolation, String] =
    if (value.startsWith("chunk:") || value.startsWith("profile:"))
      parseChunkOrProfileId(value)
    else if (value.startsWith("evidence:"))
      parseNonTextEvidenceId(value)
    else Left(malformed("evidence id", value))

  def parseGraphEdgeId(value: String): Either[DomainViolation, String] =
    value.stripPrefix("graph-edge:") match {
      case hash if value.startsWith("graph-edge:") && hex64.matches(hash) => Right(value)
      case _ => Left(malformed("graph edge id", value))
    }

  def parseRunId(value: String): Either[DomainViolation, String] =
    if (runPattern.matches(value)) Right(value)
    else Left(malformed("run id", value))

  def parseMentionId(value: String): Either[DomainViolation, String] = {
    val hashIndex = value.lastIndexOf('#')
    if (hashIndex <= 0) Left(malformed("mention id", value))
    else {
      val head = value.substring(0, hashIndex)
      val ordinal = value.substring(hashIndex + 1)
      val parts = head.split(":", 3)
      if (
        parts.length == 3 && parts(0) == "mention" &&
        Set("dblp", "openalex", "orcid", "crossref").contains(parts(1)) &&
        parts(2).nonEmpty && parseMentionOrdinal(ordinal).isRight &&
        SourceType.values
          .find(_.wire.equalsIgnoreCase(parts(1)))
          .exists(source => parseSourceRecordId(source, parts(2)).isRight)
      ) Right(value)
      else Left(malformed("mention id", value))
    }
  }

  def parseMentionIdParts(value: String): Either[DomainViolation, ParsedMentionId] =
    parseMentionId(value).flatMap { _ =>
      val hashIndex = value.lastIndexOf('#')
      val head = value.substring(0, hashIndex)
      val ordinalText = value.substring(hashIndex + 1)
      val parts = head.split(":", 3)
      parseMentionOrdinal(ordinalText).map { ordinal =>
        ParsedMentionId(parts(1), parts(2), ordinal)
      }
    }

  /** Positive ordinals that fit in a signed 32-bit int. Overflow is a domain error. */
  private def parseMentionOrdinal(ordinal: String): Either[DomainViolation, Int] =
    if (!ordinal.matches("[1-9]\\d*")) Left(malformed("mention ordinal", ordinal))
    else
      try Right(Integer.parseInt(ordinal))
      catch {
        case _: NumberFormatException =>
          Left(malformed("mention ordinal", ordinal))
      }

  def openAlexAuthorToken(raw: String): Either[DomainViolation, String] = {
    val author = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    if (openAlexAuthorPattern.matches(author)) Right(author)
    else Left(malformed("openalex author id", raw))
  }

  def orcidChecksumValid(orcid: String): Boolean = {
    val compact = orcid.replace("-", "")
    compact.length == 16 && compact.take(15).forall(_.isDigit) &&
    checksum(compact.take(15)) == compact.last
  }

  private def checksum(body: String): Char = {
    val total = body.foldLeft(0) { (acc, char) =>
      (acc + (char - '0')) * 2
    }
    val result = (12 - (total % 11)) % 11
    if (result == 10) 'X' else ('0' + result).toChar
  }

  private def openAlexWorkToken(raw: String): Either[DomainViolation, String] = {
    val token = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    if (openAlexWorkPattern.matches(token)) Right(token)
    else Left(malformed("openalex work id", raw))
  }

  private def validateGraphPath(fields: Seq[String]): Either[DomainViolation, Unit] =
    if (fields.length < 2) Left(malformed("graph path", fields.mkString(",")))
    else Right(())

  private def validateMetricEvidence(fields: Seq[String]): Either[DomainViolation, Unit] =
    if (fields.length != 5) Left(malformed("metric evidence", fields.mkString(",")))
    else {
      val researcherId = fields(0)
      val metric = fields(1)
      val start = fields(2)
      val end = fields(3)
      val policy = fields(4)
      for {
        _ <- parseResearcherId(researcherId)
        _ <-
          if (CollaborationMetric.values.exists(_.wire == metric)) Right(())
          else Left(malformed("collaboration metric", metric))
        startYear <- parseYear(start)
        endYear <- parseYear(end)
        _ <- requireWindow(startYear, endYear)
        _ <- requirePolicy(policy)
      } yield ()
    }

  private def validateEdgeEvidence(fields: Seq[String]): Either[DomainViolation, Unit] =
    if (fields.length != 1) Left(malformed("edge evidence", fields.mkString(",")))
    else {
      val edgeId = fields.head
      if (parseGraphEdgeId(edgeId).isRight || parseCoauthorEdgeId(edgeId).isRight) Right(())
      else Left(malformed("edge evidence locator", edgeId))
    }

  private def parseYear(text: String): Either[DomainViolation, Int] =
    if (text.matches("[1-9]\\d{0,3}")) Right(text.toInt)
    else Left(malformed("window year", text))

  private def requirePolicy(policyVersion: String): Either[DomainViolation, Unit] =
    if (policyPattern.matches(policyVersion)) Right(())
    else Left(malformed("policy version", policyVersion))

  private def requireWindow(startYear: Int, endYear: Int): Either[DomainViolation, Unit] =
    if (startYear > endYear)
      Left(
        DomainViolation(
          ViolationCode.ReversedTimeWindow,
          s"window start $startYear exceeds end $endYear"
        )
      )
    else if (startYear < 1 || endYear > 9999)
      Left(malformed("window year", s"$startYear-$endYear"))
    else Right(())

  private def malformed(kind: String, value: String): DomainViolation =
    DomainViolation(ViolationCode.MalformedId, s"malformed $kind: $value")
}
