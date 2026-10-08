package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*

import scala.collection.mutable.ArrayBuffer
import scala.util.control.NonFatal

object JsonSources {
  def parseLine(
      source: SourceType,
      line: String,
      runId: String,
      snapshot: String,
      locator: String,
      maxRecordBytes: Long,
      retrievalDate: Option[String] = None
  ): Vector[EmittedRecord] = {
    if (Digests.bytesOf(line) > maxRecordBytes)
      Vector(malformed(locator, snapshot, runId, RejectReasonCode.OversizeRecord, line.take(180)))
    else {
      val parsed =
        try Right(ujson.read(line))
        catch { case NonFatal(error) => Left(error.getMessage) }
      parsed match {
        case Left(message) =>
          Vector(malformed(locator, snapshot, runId, RejectReasonCode.MalformedRecord, message))
        case Right(json) =>
          source match {
            case SourceType.OpenAlex =>
              openAlex(json, runId, snapshot, locator, maxRecordBytes, retrievalDate)
            case SourceType.Crossref =>
              crossref(json, runId, snapshot, locator, maxRecordBytes, retrievalDate)
            case SourceType.Orcid => orcid(json, runId, snapshot, locator, retrievalDate)
            case _ =>
              Vector(
                malformed(
                  locator,
                  snapshot,
                  runId,
                  RejectReasonCode.UnsupportedRecordType,
                  source.wire
                )
              )
          }
      }
    }
  }

  private def malformed(
      locator: String,
      snapshot: String,
      runId: String,
      reason: RejectReasonCode,
      raw: String
  ): EmittedRecord =
    EmittedRecord.Rejected(
      Rejects.record(None, locator, Some(snapshot), runId, PreparationStage.Parse, reason, raw)
    )

  private def appendChecked[T](
      out: ArrayBuffer[EmittedRecord],
      value: T,
      wrap: T => EmittedRecord,
      source: SourceType,
      locator: String,
      snapshot: String,
      runId: String,
      validate: T => Either[Vector[DomainViolation], T]
  ): Unit =
    validate(value) match {
      case Right(valid) => out += wrap(valid)
      case Left(errors) =>
        out += fieldReject(
          source,
          locator,
          snapshot,
          runId,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
    }

  private def fieldReject(
      source: SourceType,
      locator: String,
      snapshot: String,
      runId: String,
      reason: RejectReasonCode,
      raw: String
  ): EmittedRecord =
    EmittedRecord.Rejected(
      Rejects.record(
        Some(source),
        locator,
        Some(snapshot),
        runId,
        PreparationStage.Normalize,
        reason,
        raw
      )
    )

  def openAlex(
      json: ujson.Value,
      runId: String,
      snapshot: String,
      locator: String,
      maxRecordBytes: Long = Long.MaxValue,
      retrievalDate: Option[String] = None
  ): Vector[EmittedRecord] = {
    val obj = json.objOpt.getOrElse(
      return Vector(malformed(locator, snapshot, runId, RejectReasonCode.MalformedRecord, "object"))
    )
    val token = str(obj, "id").flatMap(openAlexToken)
    if (token.isEmpty)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.MissingRequiredField,
          "openalex id"
        )
      )
    val id = token.get
    if (!id.startsWith("W"))
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.UnsupportedRecordType,
          id
        )
      )
    val title = str(obj, "title")
      .filter(_.trim.nonEmpty)
      .orElse(str(obj, "display_name").filter(_.trim.nonEmpty))
    if (title.isEmpty)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.MissingRequiredField,
          "title"
        )
      )
    val declaredFields = Vector(
      "openalex.doi" -> obj.get("doi"),
      "openalex.ids.doi" -> obj.get("ids").flatMap(_.objOpt).flatMap(_.value.get("doi"))
    )
    val badShape =
      declaredFields.flatMap(_._2).find(value => !value.isNull && !value.isInstanceOf[ujson.Str])
    if (badShape.nonEmpty)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.InvalidIdentifier,
          ujson.write(badShape.get).take(180)
        )
      )
    val declaredDois = declaredFields.flatMap { case (field, raw) =>
      raw.collect { case ujson.Str(value) if value.trim.nonEmpty => field -> value }
    }
    val malformedDoi = declaredDois.find { case (_, raw) => StableIds.normalizeDoi(raw).isLeft }
    if (malformedDoi.nonEmpty)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.InvalidIdentifier,
          malformedDoi.get._2
        )
      )
    val doi = declaredDois.headOption.flatMap { case (_, raw) =>
      StableIds.normalizeDoi(raw).toOption
    }
    val year = obj.get("publication_year").flatMap(intValue)
    if (obj.contains("publication_year") && year.isEmpty && !obj("publication_year").isNull)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.MalformedRecord,
          "publication_year"
        )
      )
    val workId = StableIds.authoritativeWorkIdForRecord(SourceType.OpenAlex, id, doi, None) match {
      case Right(value) => value
      case Left(error) =>
        return Vector(
          fieldReject(
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            RejectReasonCode.InvalidIdentifier,
            error.message
          )
        )
    }
    val provenance = ProvenanceFactory(
      SourceType.OpenAlex,
      id,
      Some(s"https://openalex.org/$id"),
      snapshot,
      runId,
      retrievalDate = retrievalDate
    )
    val authorships = obj.get("authorships").flatMap(_.arrOpt).getOrElse(Vector.empty)
    val mentions = ArrayBuffer.empty[AuthorMention]
    val links = ArrayBuffer.empty[EmittedRecord]
    var ordinal = 1
    authorships.foreach { item =>
      val author = item.objOpt
        .flatMap(_.get("author"))
        .flatMap(_.objOpt)
        .getOrElse(Map.empty[String, ujson.Value])
      val name = item.objOpt
        .flatMap(row => str(row, "raw_author_name"))
        .filter(_.trim.nonEmpty)
        .orElse(str(author, "display_name"))
        .map(_.trim)
        .getOrElse("")
      if (name.isEmpty)
        return Vector(
          fieldReject(
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            RejectReasonCode.MissingRequiredField,
            "author"
          )
        )
      val orcidRaw = str(author, "orcid").filter(_.trim.nonEmpty)
      val orcid =
        orcidRaw.flatMap(value => StableIds.researcherIdFromValidatedOrcid(value).toOption)
      if (orcidRaw.nonEmpty && orcid.isEmpty)
        return Vector(
          fieldReject(
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            RejectReasonCode.InvalidIdentifier,
            orcidRaw.get
          )
        )
      val authorIdRaw = str(author, "id").filter(_.trim.nonEmpty)
      val authorId = authorIdRaw.flatMap(value => StableIds.openAlexAuthorToken(value).toOption)
      if (authorIdRaw.nonEmpty && authorId.isEmpty)
        return Vector(
          fieldReject(
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            RejectReasonCode.InvalidIdentifier,
            authorIdRaw.get
          )
        )
      val status =
        if (orcid.nonEmpty || authorId.nonEmpty) MentionIdentityStatus.ExternalIdentifierObserved
        else MentionIdentityStatus.NameOnlyUnconfirmed
      val mention = AuthorMention(
        StableIds.mentionId(SourceType.OpenAlex, id, ordinal),
        SchemaVersions.domain,
        SourceType.OpenAlex,
        id,
        ordinal,
        name,
        TextNorm.personName(name),
        orcid.map(_.stripPrefix("researcher:orcid:")),
        authorId,
        status,
        None,
        "OpenAlex authorship is not a resolved researcher",
        provenance
      )
      mentions += mention
      institutionsOf(item).foreach { inst =>
        institutionRecords(inst, provenance, runId, snapshot, id, Some(mention.mentionId))
          .foreach(links += _)
      }
      ordinal += 1
    }
    val (venueBits, venueRejects) = venueRecords(obj, locator, snapshot, runId)
    val (topicBits, topicRejects) = topicRecords(obj, locator, snapshot, runId)
    val abstractText = obj.get("abstract_inverted_index") match {
      case None | Some(ujson.Null) => Right(None)
      case Some(value)             => reconstructAbstract(value, maxRecordBytes)
    }
    abstractText match {
      case Left(code) =>
        return venueRejects ++ topicRejects ++ Vector(
          fieldReject(
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            code,
            "abstract_inverted_index"
          )
        )
      case Right(_) => ()
    }
    val textDoc = abstractText.toOption.flatten.flatMap { text =>
      StableIds
        .chunkOrProfileId(workId, snapshot, EmittedTextDocument.abstractDocumentType, Some(0), text)
        .toOption
        .map { textId =>
          EmittedTextDocument(
            textId,
            SchemaVersions.domain,
            EmittedTextDocument.abstractDocumentType,
            workId,
            snapshot,
            Some(0),
            text,
            provenance
          )
        }
    }
    val pages = pagesOf(obj)
    val external =
      landing(obj).filter(url => doi.nonEmpty || StableIds.doiFromSourceUri(Some(url)).isEmpty)
    val work = WorkRecord(
      SchemaVersions.domain,
      workId,
      SourceType.OpenAlex,
      id,
      str(obj, "type"),
      title.get,
      TextNorm.title(title.get),
      year,
      venueBits.map(_._1),
      doi,
      None,
      pages,
      external,
      mentions.toVector,
      textDoc.map(_.textId),
      provenance,
      observedIdentifiers = declaredDois.map { case (field, raw) =>
        ObservedIdentifier(field, raw, IdentifierInterpretation.SourceObservation)
      }
    )
    val out = ArrayBuffer.empty[EmittedRecord]
    out ++= venueRejects
    out ++= topicRejects
    DomainValidation.check(work) match {
      case Left(errors) =>
        out += fieldReject(
          SourceType.OpenAlex,
          locator,
          snapshot,
          runId,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
      case Right(valid) =>
        out += EmittedRecord.Work(valid)
        textDoc.foreach { doc =>
          DomainValidation.check(doc) match {
            case Right(checked) => out += EmittedRecord.TextDoc(checked)
            case Left(errors) =>
              out += fieldReject(
                SourceType.OpenAlex,
                locator,
                snapshot,
                runId,
                RejectReasonCode.SchemaFailure,
                errors.map(_.message).mkString("; ")
              )
          }
        }
        venueBits.foreach { case (venueId, name, issn) =>
          val venue = Venue(
            venueId,
            SchemaVersions.domain,
            name,
            "openalex",
            issn,
            "OpenAlex source",
            provenance
          )
          appendChecked(
            out,
            venue,
            EmittedRecord.VenueRec.apply,
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            (item: Venue) => DomainValidation.check(item)
          )
          val link = EnrichmentLink(
            SchemaVersions.domain,
            SourceType.OpenAlex,
            id,
            snapshot,
            Some(valid.workId),
            None,
            EnrichmentTargetKind.Venue,
            venueId,
            None,
            None,
            None,
            "OpenAlex venue observation",
            runId,
            provenance
          )
          appendChecked(
            out,
            link,
            EmittedRecord.Link.apply,
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            (item: EnrichmentLink) => DomainValidation.check(item)
          )
        }
        topicBits.foreach { case (topicId, name, score, sourceId) =>
          val topic = Topic(
            topicId,
            SchemaVersions.domain,
            name,
            Some(sourceId),
            score,
            "OpenAlex topic",
            provenance
          )
          appendChecked(
            out,
            topic,
            EmittedRecord.TopicRec.apply,
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            (item: Topic) => DomainValidation.check(item)
          )
          val link = EnrichmentLink(
            SchemaVersions.domain,
            SourceType.OpenAlex,
            id,
            snapshot,
            Some(valid.workId),
            None,
            EnrichmentTargetKind.Topic,
            topicId,
            None,
            None,
            score,
            "OpenAlex topic observation",
            runId,
            provenance
          )
          appendChecked(
            out,
            link,
            EmittedRecord.Link.apply,
            SourceType.OpenAlex,
            locator,
            snapshot,
            runId,
            (item: EnrichmentLink) => DomainValidation.check(item)
          )
        }
        out ++= links
    }
    out.toVector
  }

  def crossref(
      json: ujson.Value,
      runId: String,
      snapshot: String,
      locator: String,
      maxRecordBytes: Long = Long.MaxValue,
      retrievalDate: Option[String] = None
  ): Vector[EmittedRecord] = {
    val root = json.objOpt.getOrElse(
      return Vector(malformed(locator, snapshot, runId, RejectReasonCode.MalformedRecord, "object"))
    )
    val message = root.get("message").flatMap(_.objOpt).getOrElse(root)
    val doiRaw = str(message, "DOI").orElse(str(message, "doi"))
    val doi = doiRaw.flatMap(value => StableIds.normalizeDoi(value).toOption)
    if (doiRaw.forall(_.trim.isEmpty))
      return Vector(
        fieldReject(
          SourceType.Crossref,
          locator,
          snapshot,
          runId,
          RejectReasonCode.MissingRequiredField,
          "DOI"
        )
      )
    if (doi.isEmpty)
      return Vector(
        fieldReject(
          SourceType.Crossref,
          locator,
          snapshot,
          runId,
          RejectReasonCode.InvalidIdentifier,
          doiRaw.getOrElse("")
        )
      )
    val titles = message.get("title").flatMap(_.arrOpt).getOrElse(Vector.empty).flatMap(_.strOpt)
    val title = titles.find(_.trim.nonEmpty)
    if (title.isEmpty)
      return Vector(
        fieldReject(
          SourceType.Crossref,
          locator,
          snapshot,
          runId,
          RejectReasonCode.MissingRequiredField,
          "title"
        )
      )
    val year = crossrefYear(message)
    val workId = s"work:doi:${doi.get}"
    val provenance = ProvenanceFactory(
      SourceType.Crossref,
      doi.get,
      Some(s"https://doi.org/${doi.get}"),
      snapshot,
      runId,
      retrievalDate = retrievalDate
    )
    val authors = message.get("author").flatMap(_.arrOpt).getOrElse(Vector.empty)
    val mentions = ArrayBuffer.empty[AuthorMention]
    val affiliations = ArrayBuffer.empty[MentionAffiliation]
    var ordinal = 1
    authors.foreach { author =>
      val row = author.objOpt.getOrElse(Map.empty[String, ujson.Value])
      val name = Seq(str(row, "given"), str(row, "family")).flatten.mkString(" ").trim
      if (name.isEmpty)
        return Vector(
          fieldReject(
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            RejectReasonCode.MissingRequiredField,
            "author"
          )
        )
      val orcidRaw = str(row, "ORCID").orElse(str(row, "orcid"))
      val orcid =
        orcidRaw.flatMap(value => StableIds.researcherIdFromValidatedOrcid(value).toOption)
      if (orcidRaw.exists(_.trim.nonEmpty) && orcid.isEmpty)
        return Vector(
          fieldReject(
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            RejectReasonCode.InvalidIdentifier,
            orcidRaw.getOrElse("")
          )
        )
      val status =
        if (orcid.nonEmpty) MentionIdentityStatus.ExternalIdentifierObserved
        else MentionIdentityStatus.NameOnlyUnconfirmed
      val mention = AuthorMention(
        StableIds.mentionId(SourceType.Crossref, doi.get, ordinal),
        SchemaVersions.domain,
        SourceType.Crossref,
        doi.get,
        ordinal,
        name,
        TextNorm.personName(name),
        orcid.map(_.stripPrefix("researcher:orcid:")),
        None,
        status,
        None,
        "Crossref author string is not a resolved researcher",
        provenance
      )
      mentions += mention
      crossrefAffiliations(row, mention.mentionId, provenance, snapshot) match {
        case Left(reject) => return Vector(reject)
        case Right(found) => affiliations ++= found
      }
      ordinal += 1
    }
    val issn = message
      .get("ISSN")
      .flatMap(_.arrOpt)
      .getOrElse(Vector.empty)
      .flatMap(_.strOpt)
      .find(value => StableIds.parseVenueId(s"venue:issn:$value").isRight)
    val container = message
      .get("container-title")
      .flatMap(_.arrOpt)
      .getOrElse(Vector.empty)
      .flatMap(_.strOpt)
      .find(_.trim.nonEmpty)
    val venueId = issn.map(value => s"venue:issn:$value")
    val pages = str(message, "page").filter(_.trim.nonEmpty)
    val external = str(message, "URL").filter { url =>
      StableIds.doiFromSourceUri(Some(url)).forall(doi.contains)
    }
    val abstractRaw = str(message, "abstract").map(_.trim).filter(_.nonEmpty)
    if (abstractRaw.exists(text => Digests.bytesOf(text) > maxRecordBytes))
      return Vector(
        fieldReject(
          SourceType.Crossref,
          locator,
          snapshot,
          runId,
          RejectReasonCode.OversizeRecord,
          "abstract"
        )
      )
    val textDoc = abstractRaw.flatMap { text =>
      StableIds
        .chunkOrProfileId(workId, snapshot, EmittedTextDocument.abstractDocumentType, Some(0), text)
        .toOption
        .map { textId =>
          EmittedTextDocument(
            textId,
            SchemaVersions.domain,
            EmittedTextDocument.abstractDocumentType,
            workId,
            snapshot,
            Some(0),
            text,
            provenance
          )
        }
    }
    val work = WorkRecord(
      SchemaVersions.domain,
      workId,
      SourceType.Crossref,
      doi.get,
      str(message, "type"),
      title.get,
      TextNorm.title(title.get),
      year,
      venueId,
      doi,
      None,
      pages,
      external,
      mentions.toVector,
      textDoc.map(_.textId),
      provenance
    )
    val out = ArrayBuffer.empty[EmittedRecord]
    DomainValidation.check(work) match {
      case Left(errors) =>
        out += fieldReject(
          SourceType.Crossref,
          locator,
          snapshot,
          runId,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
      case Right(valid) =>
        out += EmittedRecord.Work(valid)
        textDoc.foreach { doc =>
          appendChecked(
            out,
            doc,
            EmittedRecord.TextDoc.apply,
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            (item: EmittedTextDocument) => DomainValidation.check(item)
          )
        }
        affiliations.foreach { affiliation =>
          appendChecked(
            out,
            affiliation,
            EmittedRecord.Affiliation.apply,
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            (item: MentionAffiliation) => DomainValidation.check(item)
          )
        }
        venueId.zip(container.orElse(issn)).foreach { case (id, name) =>
          val venue = Venue(
            id,
            SchemaVersions.domain,
            name,
            "crossref",
            issn,
            "Crossref container",
            provenance
          )
          appendChecked(
            out,
            venue,
            EmittedRecord.VenueRec.apply,
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            (item: Venue) => DomainValidation.check(item)
          )
          val link = EnrichmentLink(
            SchemaVersions.domain,
            SourceType.Crossref,
            doi.get,
            snapshot,
            Some(valid.workId),
            None,
            EnrichmentTargetKind.Venue,
            id,
            None,
            None,
            None,
            "Crossref venue observation",
            runId,
            provenance
          )
          appendChecked(
            out,
            link,
            EmittedRecord.Link.apply,
            SourceType.Crossref,
            locator,
            snapshot,
            runId,
            (item: EnrichmentLink) => DomainValidation.check(item)
          )
        }
    }
    out.toVector
  }

  private def crossrefAffiliations(
      author: collection.Map[String, ujson.Value],
      mentionId: String,
      provenance: Provenance,
      snapshot: String
  ): Either[EmittedRecord, Vector[MentionAffiliation]] = {
    val rows = author.get("affiliation").flatMap(_.arrOpt).getOrElse(Vector.empty)
    val out = ArrayBuffer.empty[MentionAffiliation]
    rows.foreach { item =>
      val row = item.objOpt.map(_.value).getOrElse(Map.empty[String, ujson.Value])
      val name = str(row, "name").map(_.trim).filter(_.nonEmpty)
      if (name.contains(MentionAffiliation.rejectedOrganizationName))
        return Left(
          fieldReject(
            SourceType.Crossref,
            provenance.sourceRecordId,
            snapshot,
            provenance.runId,
            RejectReasonCode.SchemaFailure,
            MentionAffiliation.rejectedOrganizationName
          )
        )
      val rorRaw = affiliationId(row, "ROR")
      val ringRaw = affiliationId(row, "RINGGOLD")
      val ror = rorRaw.map(StableIds.institutionIdFromRor)
      val ring = ringRaw.map(StableIds.institutionIdFromRinggold)
      if (ror.exists(_.isLeft) || ring.exists(_.isLeft))
        return Left(
          fieldReject(
            SourceType.Crossref,
            provenance.sourceRecordId,
            snapshot,
            provenance.runId,
            RejectReasonCode.InvalidIdentifier,
            rorRaw.orElse(ringRaw).getOrElse("affiliation")
          )
        )
      val rorId = ror.flatMap(_.toOption)
      val ringId = ring.flatMap(_.toOption)
      if (name.nonEmpty || rorId.nonEmpty || ringId.nonEmpty)
        out += MentionAffiliation(
          SchemaVersions.domain,
          mentionId,
          SourceType.Crossref,
          provenance.sourceRecordId,
          snapshot,
          name,
          rorId.map(_.stripPrefix("institution:ror:")),
          ringId.map(_.stripPrefix("institution:ringgold:")),
          rorId.orElse(ringId),
          "Crossref affiliation name is not an invented institution id",
          provenance
        )
    }
    Right(out.toVector)
  }

  private def affiliationId(
      row: collection.Map[String, ujson.Value],
      kind: String
  ): Option[String] =
    row
      .get("id")
      .flatMap(_.arrOpt)
      .getOrElse(Vector.empty)
      .flatMap(_.objOpt)
      .find(item => str(item.value, "id-type").exists(_.equalsIgnoreCase(kind)))
      .flatMap(item => str(item.value, "id"))
      .filter(_.trim.nonEmpty)

  def orcid(
      json: ujson.Value,
      runId: String,
      snapshot: String,
      locator: String,
      retrievalDate: Option[String] = None
  ): Vector[EmittedRecord] = {
    val root = json.objOpt.getOrElse(
      return Vector(malformed(locator, snapshot, runId, RejectReasonCode.MalformedRecord, "object"))
    )
    val orcid = root
      .get("orcid-identifier")
      .flatMap(_.objOpt)
      .flatMap(row => str(row, "path"))
      .flatMap(value => StableIds.researcherIdFromValidatedOrcid(value).toOption)
      .map(_.stripPrefix("researcher:orcid:"))
    if (orcid.isEmpty)
      return Vector(
        fieldReject(
          SourceType.Orcid,
          locator,
          snapshot,
          runId,
          RejectReasonCode.InvalidIdentifier,
          "orcid"
        )
      )
    val id = orcid.get
    val provenance = ProvenanceFactory(
      SourceType.Orcid,
      id,
      Some(s"https://orcid.org/$id"),
      snapshot,
      runId,
      retrievalDate = retrievalDate
    )
    val person = root.get("person").flatMap(_.objOpt).getOrElse(Map.empty[String, ujson.Value])
    val name = person.get("name").flatMap(_.objOpt).getOrElse(Map.empty[String, ujson.Value])
    val display = nested(name, "credit-name")
      .orElse(
        Seq(nested(name, "given-names"), nested(name, "family-name")).flatten
          .mkString(" ")
          .trim match {
          case ""    => None
          case other => Some(other)
        }
      )
    val others = otherNames(person)
    val external =
      ObservedIdentifier("orcid", id, IdentifierInterpretation.ValidatedExternal) +: externalIds(
        person
      )
    val profile = OrcidProfileRecord(
      SchemaVersions.domain,
      id,
      display,
      others.distinct,
      external.distinctBy(item => (item.namespace, item.value)),
      "ORCID profile is not a canonical researcher identity",
      provenance
    )
    val out = ArrayBuffer.empty[EmittedRecord]
    DomainValidation.check(profile) match {
      case Left(errors) =>
        out += fieldReject(
          SourceType.Orcid,
          locator,
          snapshot,
          runId,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
      case Right(valid) =>
        out += EmittedRecord.Profile(valid)
        biography(person).foreach { text =>
          val researcherId = s"researcher:orcid:$id"
          StableIds
            .chunkOrProfileId(
              researcherId,
              snapshot,
              EmittedTextDocument.researcherProfileDocumentType,
              None,
              text
            )
            .foreach { textId =>
              val doc = EmittedTextDocument(
                textId,
                SchemaVersions.domain,
                EmittedTextDocument.researcherProfileDocumentType,
                researcherId,
                snapshot,
                None,
                text,
                provenance
              )
              appendChecked(
                out,
                doc,
                EmittedRecord.TextDoc.apply,
                SourceType.Orcid,
                locator,
                snapshot,
                runId,
                (item: EmittedTextDocument) => DomainValidation.check(item)
              )
            }
        }
    }
    activities(root).foreach { summary =>
      activityRecord(summary, id, runId, snapshot, retrievalDate).foreach {
        case Left(reject) => out += reject
        case Right(record) =>
          DomainValidation.check(record) match {
            case Right(valid) => out += EmittedRecord.Activity(valid)
            case Left(errors) =>
              out += fieldReject(
                SourceType.Orcid,
                locator,
                snapshot,
                runId,
                RejectReasonCode.SchemaFailure,
                errors.map(_.message).mkString("; ")
              )
          }
      }
    }
    out.toVector
  }

  private def activityRecord(
      summary: ujson.Obj,
      orcid: String,
      runId: String,
      snapshot: String,
      retrievalDate: Option[String]
  ): Option[Either[EmittedRecord, OrcidActivityRecord]] = {
    val path = str(summary.value, "path").map(_.stripPrefix("/"))
    val parts = path.map(_.split("/", -1)).getOrElse(Array.empty[String])
    if (parts.length != 3 || parts(0) != orcid) None
    else {
      val kind = OrcidActivityKind.values.find(_.wire == parts(1))
      kind.map { activityKind =>
        val sourceRecordId = parts.mkString("/")
        val provenance = ProvenanceFactory(
          SourceType.Orcid,
          sourceRecordId,
          Some(s"https://orcid.org/$sourceRecordId"),
          snapshot,
          runId,
          retrievalDate = retrievalDate
        )
        val org = summary.value.get("organization").flatMap(_.objOpt)
        val disambiguated = org.flatMap(_.get("disambiguated-organization")).flatMap(_.objOpt)
        val sourceName =
          disambiguated.flatMap(row => str(row, "disambiguation-source")).map(_.toUpperCase)
        val identifier =
          disambiguated.flatMap(row => str(row, "disambiguated-organization-identifier"))
        val rorParsed =
          if (sourceName.contains("ROR")) identifier.map(StableIds.institutionIdFromRor) else None
        val ringParsed =
          if (sourceName.contains("RINGGOLD")) identifier.map(StableIds.institutionIdFromRinggold)
          else None
        if (rorParsed.exists(_.isLeft) || ringParsed.exists(_.isLeft))
          Left(
            fieldReject(
              SourceType.Orcid,
              sourceRecordId,
              snapshot,
              runId,
              RejectReasonCode.InvalidIdentifier,
              identifier.getOrElse("")
            )
          )
        else {
          val ror = rorParsed.flatMap(_.toOption).map(_.stripPrefix("institution:ror:"))
          val ringgold = ringParsed.flatMap(_.toOption).map(_.stripPrefix("institution:ringgold:"))
          val doiParsed = externalDoi(summary)
          val references = workReferences(summary)
          val institutionId = ror
            .map(value => s"institution:ror:$value")
            .orElse(ringgold.map(value => s"institution:ringgold:$value"))
          val doi = doiParsed.toOption.flatten
          if (doiParsed.isLeft)
            return Some(
              Left(
                fieldReject(
                  SourceType.Orcid,
                  sourceRecordId,
                  snapshot,
                  runId,
                  RejectReasonCode.InvalidIdentifier,
                  "doi"
                )
              )
            )
          val workId = doi.map(value => s"work:doi:$value")
          val title =
            if (activityKind == OrcidActivityKind.Work) workTitle(summary)
            else str(summary.value, "role-title").orElse(str(summary.value, "department-name"))
          val start =
            if (activityKind == OrcidActivityKind.Work) None
            else yearAt(summary.value.get("start-date"))
          val published =
            if (activityKind == OrcidActivityKind.Work)
              yearAt(summary.value.get("publication-date"))
            else None
          Right(
            OrcidActivityRecord(
              SchemaVersions.domain,
              orcid,
              activityKind,
              sourceRecordId,
              title.filter(_.trim.nonEmpty),
              start,
              published,
              org.flatMap(row => str(row, "name")),
              ror,
              ringgold,
              institutionId,
              if (activityKind == OrcidActivityKind.Work) doi else None,
              if (activityKind == OrcidActivityKind.Work) workId else None,
              "ORCID activity is not a work record, authorship, or merge",
              provenance,
              workReferences = references
            )
          )
        }
      }
    }
  }

  private def activities(root: ujson.Obj): Vector[ujson.Obj] = {
    val found = ArrayBuffer.empty[ujson.Obj]
    def walk(value: ujson.Value): Unit = value match {
      case obj: ujson.Obj =>
        str(obj.value, "path").map(_.stripPrefix("/")).foreach { path =>
          val parts = path.split("/", -1)
          if (
            parts.length == 3 && OrcidActivityKind.values.exists(_.wire == parts(1)) && obj.value
              .contains("put-code")
          )
            found += obj
        }
        obj.value.values.foreach(walk)
      case arr: ujson.Arr => arr.value.foreach(walk)
      case _              => ()
    }
    walk(root)
    found.toVector
  }

  private def externalDoi(summary: ujson.Obj): Either[RejectReasonCode, Option[String]] = {
    val raw = externalIdRows(summary)
      .find(row => str(row.value, "external-id-type").exists(_.equalsIgnoreCase("doi")))
      .flatMap(row => str(row.value, "external-id-value"))
      .map(_.trim)
      .filter(_.nonEmpty)
    raw match {
      case None => Right(None)
      case Some(value) =>
        StableIds.normalizeDoi(value) match {
          case Right(doi) => Right(Some(doi))
          case Left(_)    => Left(RejectReasonCode.InvalidIdentifier)
        }
    }
  }

  /** Every `external-id` row, including DOI, `other-id`, ISBN, and ISSN. Not a work or a merge. */
  private def workReferences(summary: ujson.Obj): Vector[OrcidWorkReference] =
    externalIdRows(summary).flatMap { row =>
      val idType = str(row.value, "external-id-type").map(_.trim).filter(_.nonEmpty)
      val value = str(row.value, "external-id-value").map(_.trim).filter(_.nonEmpty)
      val relationship =
        str(row.value, "external-id-relationship").map(_.trim).filter(_.nonEmpty)
      idType.zip(value).map { case (kind, id) =>
        OrcidWorkReference(kind, id, relationship)
      }
    }

  private def externalIdRows(summary: ujson.Obj): Vector[ujson.Obj] =
    summary.value.get("external-ids").flatMap(_.objOpt).flatMap(_.get("external-id")) match {
      case Some(arr: ujson.Arr) =>
        arr.value.flatMap { case obj: ujson.Obj => Some(obj); case _ => None }.toVector
      case Some(obj: ujson.Obj) => Vector(obj)
      case _                    => Vector.empty
    }

  private def workTitle(summary: ujson.Obj): Option[String] =
    summary.value
      .get("title")
      .flatMap(_.objOpt)
      .flatMap(_.get("title"))
      .flatMap {
        case ujson.Str(text) => Some(text)
        case obj: ujson.Obj  => str(obj.value, "value")
        case _               => None
      }

  private def yearAt(value: Option[ujson.Value]): Option[Int] =
    value
      .flatMap(_.objOpt)
      .flatMap(_.get("year"))
      .flatMap(_.objOpt)
      .flatMap(row => str(row, "value"))
      .flatMap(_.toIntOption)
      .filter(year => year >= 1 && year <= 9999)

  private def otherNames(person: collection.Map[String, ujson.Value]): Vector[String] =
    person
      .get("other-names")
      .flatMap(_.objOpt)
      .flatMap(_.get("other-name"))
      .map {
        case arr: ujson.Arr =>
          arr.value.flatMap(_.objOpt).flatMap(row => str(row, "content")).toVector
        case obj: ujson.Obj => str(obj.value, "content").toVector
        case _              => Vector.empty
      }
      .getOrElse(Vector.empty)
      .map(_.trim)
      .filter(_.nonEmpty)

  private def externalIds(person: collection.Map[String, ujson.Value]): Vector[ObservedIdentifier] =
    person
      .get("external-identifiers")
      .flatMap(_.objOpt)
      .flatMap(_.get("external-identifier"))
      .flatMap(_.arrOpt)
      .getOrElse(Vector.empty)
      .flatMap { item =>
        val row = item.objOpt.map(_.value).getOrElse(Map.empty)
        val namespace = str(row, "external-id-type").map(_.trim).filter(_.nonEmpty)
        val value = str(row, "external-id-value").map(_.trim).filter(_.nonEmpty)
        namespace.zip(value).map { case (ns, id) =>
          val interpretation =
            if (ns.toLowerCase.contains("openalex"))
              IdentifierInterpretation.DisambiguationHypothesis
            else IdentifierInterpretation.SourceObservation
          ObservedIdentifier(ns, id, interpretation)
        }
      }
      .toVector

  private def biography(person: collection.Map[String, ujson.Value]): Option[String] =
    person.get("biography").flatMap {
      case ujson.Str(text) if text.trim.nonEmpty => Some(text.trim)
      case obj: ujson.Obj                        => nested(obj.value, "content")
      case _                                     => None
    }

  private def institutionsOf(item: ujson.Value): Vector[collection.Map[String, ujson.Value]] =
    item.objOpt
      .flatMap(_.get("institutions"))
      .flatMap(_.arrOpt)
      .getOrElse(Vector.empty)
      .flatMap(_.objOpt)
      .toVector

  private def institutionRecords(
      inst: collection.Map[String, ujson.Value],
      provenance: Provenance,
      runId: String,
      snapshot: String,
      sourceRecordId: String,
      mentionId: Option[String]
  ): Vector[EmittedRecord] = {
    val name = str(inst, "display_name").map(_.trim).filter(_.nonEmpty)
    if (name.isEmpty)
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          runId,
          RejectReasonCode.MissingRequiredField,
          "display_name"
        )
      )
    if (name.contains(MentionAffiliation.rejectedOrganizationName))
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          runId,
          RejectReasonCode.SchemaFailure,
          MentionAffiliation.rejectedOrganizationName
        )
      )
    val rorRaw = str(inst, "ror").map(_.trim).filter(_.nonEmpty)
    val ror = rorRaw.map(StableIds.institutionIdFromRor)
    if (ror.exists(_.isLeft))
      return Vector(
        fieldReject(
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          runId,
          RejectReasonCode.InvalidIdentifier,
          rorRaw.getOrElse("ror")
        )
      )
    val openAlexRaw = str(inst, "id").map(_.trim).filter(_.nonEmpty)
    val openAlex = openAlexRaw.map(StableIds.institutionIdFromOpenAlex)
    val invalidOpenAlex =
      if (openAlex.exists(_.isLeft))
        Vector(
          fieldReject(
            SourceType.OpenAlex,
            sourceRecordId,
            snapshot,
            runId,
            RejectReasonCode.InvalidIdentifier,
            openAlexRaw.getOrElse("institution")
          )
        )
      else Vector.empty
    if (invalidOpenAlex.nonEmpty && ror.forall(_.isLeft)) return invalidOpenAlex
    val rorId = ror.flatMap(_.toOption)
    val openAlexId = openAlex.flatMap(_.toOption)
    val observedSourceIds = openAlexId.toVector.map { id =>
      ObservedIdentifier(
        IdentifierNamespace.OpenAlexInstitution.wire,
        id.stripPrefix("institution:openalex:"),
        IdentifierInterpretation.SourceObservation
      )
    }
    val institutionId = rorId.orElse(openAlexId)
    institutionId match {
      case None =>
        invalidOpenAlex ++ mentionId.toVector.map { mention =>
          val affiliation = MentionAffiliation(
            SchemaVersions.domain,
            mention,
            SourceType.OpenAlex,
            sourceRecordId,
            snapshot,
            name,
            None,
            None,
            None,
            "OpenAlex affiliation name does not invent an institution id",
            provenance
          )
          DomainValidation.check(affiliation) match {
            case Right(valid) => EmittedRecord.Affiliation(valid)
            case Left(errors) =>
              fieldReject(
                SourceType.OpenAlex,
                sourceRecordId,
                snapshot,
                runId,
                RejectReasonCode.SchemaFailure,
                errors.map(_.message).mkString("; ")
              )
          }
        }
      case Some(id) =>
        val record = Institution(
          id,
          SchemaVersions.domain,
          name.get,
          rorId.map(_.stripPrefix("institution:ror:")),
          None,
          "OpenAlex institution observation; ROR is not Ringgold",
          provenance,
          observedSourceIds = observedSourceIds
        )
        val link = EnrichmentLink(
          SchemaVersions.domain,
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          None,
          mentionId,
          EnrichmentTargetKind.Institution,
          id,
          rorId.map(_.stripPrefix("institution:ror:")),
          None,
          None,
          "affiliation observed on an author mention",
          runId,
          provenance
        )
        val out = ArrayBuffer.empty[EmittedRecord]
        appendChecked(
          out,
          record,
          EmittedRecord.InstitutionRec.apply,
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          runId,
          (item: Institution) => DomainValidation.check(item)
        )
        appendChecked(
          out,
          link,
          EmittedRecord.Link.apply,
          SourceType.OpenAlex,
          sourceRecordId,
          snapshot,
          runId,
          (item: EnrichmentLink) => DomainValidation.check(item)
        )
        invalidOpenAlex ++ out.toVector
    }
  }

  private def venueRecords(
      obj: scala.collection.Map[String, ujson.Value],
      locator: String,
      snapshot: String,
      runId: String
  ): (Option[(String, String, Option[String])], Vector[EmittedRecord]) =
    obj.get("primary_location").flatMap(_.objOpt).flatMap(_.get("source")).flatMap(_.objOpt) match {
      case None => (None, Vector.empty)
      case Some(source) =>
        val rawId = str(source.value, "id").map(_.trim).filter(_.nonEmpty)
        val parsed = rawId.map(value => StableIds.parseVenueId(openAlexVenue(value)))
        val reject = parsed match {
          case Some(Left(_)) =>
            Vector(
              fieldReject(
                SourceType.OpenAlex,
                locator,
                snapshot,
                runId,
                RejectReasonCode.InvalidIdentifier,
                rawId.getOrElse("venue")
              )
            )
          case _ => Vector.empty
        }
        val name = str(source.value, "display_name").filter(_.trim.nonEmpty)
        val issn =
          str(source.value, "issn_l").filter(value => value.matches("[0-9]{4}-[0-9]{3}[0-9X]"))
        val bits =
          parsed.flatMap(_.toOption).zip(name).map { case (venueId, label) =>
            (venueId, label, issn)
          }
        (bits, reject)
    }

  private def openAlexVenue(raw: String): String = {
    val token = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    s"venue:openalex:$token"
  }

  private def topicRecords(
      obj: scala.collection.Map[String, ujson.Value],
      locator: String,
      snapshot: String,
      runId: String
  ): (Vector[(String, String, Option[Double], String)], Vector[EmittedRecord]) = {
    val values = obj.get("topics").flatMap(_.arrOpt).getOrElse(Vector.empty) ++ obj
      .get("primary_topic")
      .toVector
    val topics = ArrayBuffer.empty[(String, String, Option[Double], String)]
    val rejects = ArrayBuffer.empty[EmittedRecord]
    values.flatMap(_.objOpt).foreach { topic =>
      val raw = str(topic.value, "id").map(_.trim).filter(_.nonEmpty)
      val name = str(topic.value, "display_name").filter(_.trim.nonEmpty)
      val score = topic.value.get("score").flatMap {
        case ujson.Num(n) if n.isFinite => Some(n)
        case _                          => None
      }
      raw match {
        case Some(value) =>
          StableIds.topicIdFromOpenAlex(value) match {
            case Left(_) =>
              rejects += fieldReject(
                SourceType.OpenAlex,
                locator,
                snapshot,
                runId,
                RejectReasonCode.InvalidIdentifier,
                value
              )
            case Right(topicId) =>
              name.foreach(label => topics += ((topicId, label, score, value)))
          }
        case None => ()
      }
    }
    (topics.distinctBy(_._1).toVector, rejects.toVector)
  }

  private def pagesOf(obj: scala.collection.Map[String, ujson.Value]): Option[String] =
    obj.get("biblio").flatMap(_.objOpt).flatMap { biblio =>
      val first = str(biblio.value, "first_page")
      val last = str(biblio.value, "last_page")
      (first, last) match {
        case (Some(a), Some(b)) => Some(s"$a-$b")
        case (Some(a), None)    => Some(a)
        case _                  => None
      }
    }

  private def landing(obj: scala.collection.Map[String, ujson.Value]): Option[String] =
    obj.get("primary_location").flatMap(_.objOpt).flatMap(row => str(row.value, "landing_page_url"))

  private def reconstructAbstract(
      value: ujson.Value,
      maxRecordBytes: Long
  ): Either[RejectReasonCode, Option[String]] =
    value.objOpt match {
      case None => Right(None)
      case Some(index) =>
        val placed = ArrayBuffer.empty[(Int, String)]
        var failed = false
        index.value.foreach { case (word, positions) =>
          if (!failed)
            positions.arrOpt.getOrElse(Vector.empty).foreach {
              case ujson.Num(n) if n.isWhole && n >= 0 && n <= maxRecordBytes =>
                placed += (n.toInt -> word)
              case _ => failed = true
            }
        }
        if (failed || placed.size > maxRecordBytes) Left(RejectReasonCode.OversizeRecord)
        else if (placed.isEmpty) Right(None)
        else {
          val min = placed.map(_._1).min
          val max = placed.map(_._1).max
          val span = max.toLong - min.toLong + 1L
          val textBytes = placed.map { case (_, word) => Digests.bytesOf(word) }.sum + placed.size
          if (span > maxRecordBytes || textBytes > maxRecordBytes)
            Left(RejectReasonCode.OversizeRecord)
          else {
            val words = Array.fill(span.toInt)("")
            placed.foreach { case (position, word) =>
              val slot = position - min
              if (words(slot).nonEmpty) words(slot) = words(slot) + word
              else words(slot) = word
            }
            val text = words.mkString(" ").replaceAll(" +", " ").trim
            if (Digests.bytesOf(text) > maxRecordBytes) Left(RejectReasonCode.OversizeRecord)
            else Right(Option(text).filter(_.nonEmpty))
          }
        }
    }

  private def crossrefYear(message: scala.collection.Map[String, ujson.Value]): Option[Int] = {
    val keys = Seq("published-print", "published-online", "published", "issued", "created")
    keys.iterator.flatMap(key => message.get(key)).flatMap(yearParts).nextOption()
  }

  private def yearParts(value: ujson.Value): Option[Int] =
    value.objOpt
      .flatMap(_.get("date-parts"))
      .flatMap(_.arrOpt)
      .flatMap(_.headOption)
      .flatMap(_.arrOpt)
      .flatMap(_.headOption)
      .flatMap {
        case ujson.Num(n) if n.isWhole => Some(n.toInt)
        case ujson.Str(text)           => text.toIntOption
        case _                         => None
      }
      .filter(year => year >= 1 && year <= 9999)

  private def openAlexToken(raw: String): Option[String] = {
    val token = raw.trim.replaceFirst("(?i)^https?://openalex\\.org/", "")
    if (token.matches("[WAISTC][1-9]\\d*")) Some(token) else None
  }

  private def str(obj: ujson.Obj, name: String): Option[String] = str(obj.value, name)

  private def str(obj: scala.collection.Map[String, ujson.Value], name: String): Option[String] =
    obj.get(name).flatMap {
      case ujson.Str(text) => Some(text)
      case _               => None
    }

  private def nested(obj: scala.collection.Map[String, ujson.Value], name: String): Option[String] =
    obj.get(name).flatMap(_.objOpt).flatMap(row => str(row.value, "value")).filter(_.trim.nonEmpty)

  private def intValue(value: ujson.Value): Option[Int] = value match {
    case ujson.Num(n) if n.isWhole && n >= 1 && n <= 9999 => Some(n.toInt)
    case ujson.Str(text) => text.toIntOption.filter(year => year >= 1 && year <= 9999)
    case _               => None
  }

  extension (value: ujson.Value) {
    def objOpt: Option[ujson.Obj] = value match {
      case obj: ujson.Obj => Some(obj)
      case _              => None
    }
    def arrOpt: Option[ujson.Arr] = value match {
      case arr: ujson.Arr => Some(arr)
      case _              => None
    }
    def strOpt: Option[String] = value match {
      case ujson.Str(text) => Some(text)
      case _               => None
    }
  }
}
