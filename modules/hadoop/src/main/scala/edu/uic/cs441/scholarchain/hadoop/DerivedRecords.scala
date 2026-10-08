package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*

import scala.collection.mutable.ArrayBuffer

object DerivedRecords {
  def teams(
      work: WorkRecord,
      maxTeam: Int,
      locator: String
  ): Vector[EmittedRecord] = {
    val ordered = work.authors.sortBy(_.ordinal)
    if (ordered.size > maxTeam)
      Vector(
        EmittedRecord.Rejected(
          Rejects.record(
            Some(work.source),
            locator,
            Some(work.provenance.datasetSnapshot),
            work.provenance.runId,
            PreparationStage.PublicationTeam,
            RejectReasonCode.OversizeTeam,
            s"team ${ordered.size} exceeds $maxTeam"
          )
        )
      )
    else {
      val team = PublicationTeam(
        SchemaVersions.domain,
        work.workId,
        ordered.map(_.mentionId),
        ordered.size,
        "team lists every source mention; size 1 is complete",
        work.provenance
      )
      val checkedTeam = checked(team, work, locator, PreparationStage.PublicationTeam)(
        DomainValidation.check(team, work)
      )
      val authorships = ordered.map { mention =>
        val record = AuthorshipRecord(
          SchemaVersions.domain,
          work.workId,
          mention.mentionId,
          mention.ordinal,
          None,
          "authorship position follows the source mention and is not a researcher id",
          work.provenance
        )
        checked(record, work, locator, PreparationStage.Authorship)(
          DomainValidation.check(record, work)
        )
      }
      checkedTeam +: authorships.toVector
    }
  }

  def pairs(
      work: WorkRecord,
      maxPairs: Int,
      maxTeam: Int,
      locator: String
  ): Vector[EmittedRecord] = {
    val authors = work.authors
    if (authors.size > maxTeam) Vector.empty
    else {
      val count =
        try PrepLimits.pairCount(authors.size)
        catch { case _: ArithmeticException => Long.MaxValue }
      if (count > maxPairs.toLong)
        Vector(
          EmittedRecord.Rejected(
            Rejects.record(
              Some(work.source),
              locator,
              Some(work.provenance.datasetSnapshot),
              work.provenance.runId,
              PreparationStage.CoauthorPair,
              RejectReasonCode.OversizeCandidatePairs,
              s"pair expansion $count exceeds $maxPairs"
            )
          )
        )
      else {
        val mentions = authors.sortBy(_.mentionId)
        val out = ArrayBuffer.empty[EmittedRecord]
        var i = 0
        while (i < mentions.length) {
          var j = i + 1
          while (j < mentions.length) {
            val left = mentions(i)
            val right = mentions(j)
            val record = CoauthorPairCandidate(
              SchemaVersions.domain,
              work.workId,
              work.doi,
              work.arxivId,
              left.mentionId,
              right.mentionId,
              left.ordinal,
              right.ordinal,
              work.year,
              "undirected pair from one work; mention order is String.compareTo",
              work.provenance
            )
            out += checked(record, work, locator, PreparationStage.CoauthorPair)(
              DomainValidation.check(record, work)
            )
            j += 1
          }
          i += 1
        }
        out.toVector
      }
    }
  }

  def orderedPair(left: AuthorMention, right: AuthorMention): (AuthorMention, AuthorMention) =
    if (left.mentionId.compareTo(right.mentionId) <= 0) (left, right) else (right, left)

  def provenanceGate(derived: Provenance, observed: Provenance): Option[RejectReasonCode] =
    if (ProvenanceFactory.mismatches(derived, observed)) Some(RejectReasonCode.ProvenanceMismatch)
    else None

  private def checked[T](
      value: T,
      work: WorkRecord,
      locator: String,
      stage: PreparationStage
  )(result: Either[Vector[DomainViolation], T]): EmittedRecord =
    provenanceGate(provenanceOf(value), work.provenance) match {
      case Some(code) =>
        EmittedRecord.Rejected(
          Rejects.record(
            Some(work.source),
            locator,
            Some(work.provenance.datasetSnapshot),
            work.provenance.runId,
            stage,
            code,
            "derived provenance does not match the work observation"
          )
        )
      case None =>
        result match {
          case Right(valid) => wrap(valid)
          case Left(errors) =>
            EmittedRecord.Rejected(
              Rejects.record(
                Some(work.source),
                locator,
                Some(work.provenance.datasetSnapshot),
                work.provenance.runId,
                stage,
                RejectReasonCode.SchemaFailure,
                errors.map(_.message).mkString("; ")
              )
            )
        }
    }

  private def provenanceOf[T](value: T): Provenance = value match {
    case record: PublicationTeam       => record.provenance
    case record: AuthorshipRecord      => record.provenance
    case record: CoauthorPairCandidate => record.provenance
    case _                             => throw new IllegalArgumentException(value.getClass.getName)
  }

  private def wrap[T](value: T): EmittedRecord = value match {
    case record: PublicationTeam       => EmittedRecord.TeamRec(record)
    case record: AuthorshipRecord      => EmittedRecord.AuthorshipRec(record)
    case record: CoauthorPairCandidate => EmittedRecord.PairRec(record)
    case _                             => throw new IllegalArgumentException(value.getClass.getName)
  }

  def indexRows(record: EmittedRecord, payloadHash: String): Vector[IndexRow] = record match {
    case EmittedRecord.Work(work)         => workRows(work, payloadHash)
    case EmittedRecord.Profile(profile)   => profileRows(profile, payloadHash)
    case EmittedRecord.Activity(activity) => activityRows(activity, payloadHash)
    case EmittedRecord.InstitutionRec(inst) if inst.provenance.source != SourceType.ScholarChain =>
      institutionRows(inst, payloadHash)
    case _ => Vector.empty
  }

  private def workRows(work: WorkRecord, payloadHash: String): Vector[IndexRow] = {
    val rows = ArrayBuffer.empty[IndexRow]
    def add(namespace: IdentifierNamespace, raw: String): Unit =
      identifier(namespace, raw, work.source, work.sourceRecordId, work.provenance, payloadHash)
        .foreach(rows += _)
    work.doi.foreach(value => add(IdentifierNamespace.Doi, value))
    work.arxivId.foreach(value => add(IdentifierNamespace.Arxiv, value))
    work.source match {
      case SourceType.Dblp     => add(IdentifierNamespace.Dblp, work.sourceRecordId)
      case SourceType.OpenAlex => add(IdentifierNamespace.OpenAlexWork, work.sourceRecordId)
      case _                   => ()
    }
    work.authors.foreach { mention =>
      mention.observedOrcid.foreach(value => add(IdentifierNamespace.Orcid, value))
      mention.observedOpenAlexAuthorId.foreach(value =>
        add(IdentifierNamespace.OpenAlexAuthor, value)
      )
    }
    rows.toVector.distinctBy(row => (row.entry.namespace, row.entry.normalizedValue))
  }

  private def profileRows(profile: OrcidProfileRecord, payloadHash: String): Vector[IndexRow] =
    identifier(
      IdentifierNamespace.Orcid,
      profile.orcid,
      SourceType.Orcid,
      profile.provenance.sourceRecordId,
      profile.provenance,
      payloadHash
    ).toVector

  private def activityRows(activity: OrcidActivityRecord, payloadHash: String): Vector[IndexRow] = {
    val rows = ArrayBuffer.empty[IndexRow]
    activity.observedDoi.foreach { doi =>
      identifier(
        IdentifierNamespace.Doi,
        doi,
        SourceType.Orcid,
        activity.sourceRecordId,
        activity.provenance,
        payloadHash
      ).foreach(rows += _)
    }
    activity.ror.foreach { ror =>
      identifier(
        IdentifierNamespace.Ror,
        ror,
        SourceType.Orcid,
        activity.sourceRecordId,
        activity.provenance,
        payloadHash
      ).foreach(rows += _)
    }
    activity.ringgold.foreach { ringgold =>
      identifier(
        IdentifierNamespace.Ringgold,
        ringgold,
        SourceType.Orcid,
        activity.sourceRecordId,
        activity.provenance,
        payloadHash
      ).foreach(rows += _)
    }
    rows.toVector
  }

  private def institutionRows(inst: Institution, payloadHash: String): Vector[IndexRow] = {
    val rows = ArrayBuffer.empty[IndexRow]
    inst.ror.foreach(value =>
      identifier(
        IdentifierNamespace.Ror,
        value,
        inst.provenance.source,
        inst.provenance.sourceRecordId,
        inst.provenance,
        payloadHash
      ).foreach(rows += _)
    )
    inst.ringgold.foreach(value =>
      identifier(
        IdentifierNamespace.Ringgold,
        value,
        inst.provenance.source,
        inst.provenance.sourceRecordId,
        inst.provenance,
        payloadHash
      ).foreach(rows += _)
    )
    inst.observedSourceIds.foreach { observed =>
      if (observed.namespace == IdentifierNamespace.OpenAlexInstitution.wire)
        identifier(
          IdentifierNamespace.OpenAlexInstitution,
          observed.value,
          inst.provenance.source,
          inst.provenance.sourceRecordId,
          inst.provenance,
          payloadHash
        ).foreach(rows += _)
    }
    rows.toVector
  }

  private def identifier(
      namespace: IdentifierNamespace,
      raw: String,
      source: SourceType,
      sourceRecordId: String,
      provenance: Provenance,
      payloadHash: String
  ): Option[IndexRow] =
    StableIds.normalizeIndexedIdentifier(namespace, raw).toOption.flatMap { normalized =>
      StableIds.identifierPreferredWorkId(namespace, normalized).toOption.map { preferred =>
        val entry = IdentifierIndexEntry(
          SchemaVersions.domain,
          namespace,
          normalized,
          preferred,
          source,
          sourceRecordId,
          provenance.datasetSnapshot,
          provenance.runId,
          provenance
        )
        IndexRow(entry, payloadHash)
      }
    }

  def exactKey(namespace: IdentifierNamespace, normalized: String): Option[String] =
    if (exactNamespaces.contains(namespace)) blockKey("exact", namespace.wire, normalized)
    else None

  val exactNamespaces: Set[IdentifierNamespace] =
    IdentifierNamespace.workNamespaces ++ Set(
      IdentifierNamespace.Orcid,
      IdentifierNamespace.OpenAlexAuthor
    )

  def blockKey(segments: String*): Option[String] = {
    val key =
      segments.map(segment => segment.replace("\r", " ").replace("\n", " ").trim).mkString(":")
    if (
      key.nonEmpty && key == key.trim && key.length <= 512 && !key
        .exists(ch => ch == '\n' || ch == '\r')
    )
      Some(key)
    else None
  }

  def initials(normalizedName: String): String =
    normalizedName.split(' ').filter(_.nonEmpty).map(_.take(1)).mkString(" ")

  def blockKeys(profile: Bibliography): Vector[String] = {
    val exact = profile.exactKeys.flatMap(key => blockKey(key.split(":", -1).toSeq*))
    val names = profile.authorNames.flatMap(name => blockKey("name", name))
    val initialKeys =
      profile.authorInitials.filter(_.nonEmpty).flatMap(value => blockKey("initial", value))
    val title =
      if (profile.normalizedTitle.nonEmpty)
        blockKey(
          "title-year",
          profile.normalizedTitle,
          profile.year.map(_.toString).getOrElse("unknown")
        ).toVector
      else Vector.empty
    val venue =
      if (profile.venue.nonEmpty) blockKey("venue", profile.venue).toVector else Vector.empty
    val affiliations = profile.affiliationNames.flatMap(name => blockKey("affiliation", name))
    val coauthors = profile.coauthorNames.flatMap(name => blockKey("coauthor", name))
    val keyed =
      (exact ++ names ++ initialKeys ++ title ++ venue ++ affiliations ++ coauthors).distinct.sorted
    if (keyed.nonEmpty) keyed
    else
      blockKey("fallback", profile.source.wire, profile.sourceRecordId).toVector
  }

  def bibliography(records: Seq[(String, String)], rows: Seq[IndexRow]): Option[Bibliography] = {
    val works = records.collect { case (Kinds.Work, json) =>
      CoreJson.parse[WorkRecord](json).toOption
    }.flatten
    val venues = records.collect { case (Kinds.Venue, json) =>
      CoreJson.parse[Venue](json).toOption
    }.flatten
    val institutions =
      records.collect { case (Kinds.Institution, json) =>
        CoreJson.parse[Institution](json).toOption
      }.flatten
    val affiliations = records.collect { case (Kinds.MentionAffiliation, json) =>
      CoreJson.parse[MentionAffiliation](json).toOption
    }.flatten
    val profiles =
      records.collect { case (Kinds.Profile, json) =>
        CoreJson.parse[OrcidProfileRecord](json).toOption
      }.flatten
    val activities =
      records.collect { case (Kinds.Activity, json) =>
        CoreJson.parse[OrcidActivityRecord](json).toOption
      }.flatten
    val anchor = works.headOption
      .map(work =>
        (
          work.source,
          work.sourceRecordId,
          work.provenance.datasetSnapshot,
          Some(work.workId)
        )
      )
      .orElse(profiles.headOption.map { profile =>
        (
          SourceType.Orcid,
          profile.provenance.sourceRecordId,
          profile.provenance.datasetSnapshot,
          Option.empty[String]
        )
      })
      .orElse(activities.headOption.map { activity =>
        (
          SourceType.Orcid,
          activity.sourceRecordId,
          activity.provenance.datasetSnapshot,
          Option.empty[String]
        )
      })
      .orElse(rows.headOption.map { row =>
        (
          row.entry.source,
          row.entry.sourceRecordId,
          row.entry.datasetSnapshot,
          Option.empty[String]
        )
      })
    anchor.map { case (source, sourceRecordId, snapshot, workId) =>
      val authorNames = (
        works.flatMap(_.authors.map(_.normalizedName)) ++
          profiles.flatMap(_.displayName.map(TextNorm.personName))
      ).filter(_.nonEmpty).distinct.sorted.toVector
      val authorInitials = authorNames.map(initials).filter(_.nonEmpty).distinct.sorted.toVector
      val affiliationNames = (
        institutions.map(inst => TextNorm.collapse(inst.name)) ++
          affiliations.flatMap(_.organizationName.map(TextNorm.collapse)) ++
          activities.flatMap(_.organizationName.map(TextNorm.collapse))
      ).filter(name => name.nonEmpty && name != MentionAffiliation.rejectedOrganizationName)
        .distinct
        .sorted
        .toVector
      val venue = venues.map(item => TextNorm.collapse(item.name)).find(_.nonEmpty).getOrElse("")
      val title = works.headOption
        .map(_.normalizedTitle)
        .orElse(activities.flatMap(_.title.map(TextNorm.title)).headOption)
        .getOrElse("")
      val year =
        works.flatMap(_.year).headOption.orElse(activities.flatMap(_.publicationYear).headOption)
      val exactKeys = rows
        .flatMap { row =>
          exactKey(row.entry.namespace, row.entry.normalizedValue)
        }
        .distinct
        .sorted
        .toVector
      Bibliography(
        source,
        sourceRecordId,
        snapshot,
        workId.filter(_ => works.nonEmpty),
        title,
        year,
        venue,
        authorNames,
        authorInitials,
        affiliationNames,
        if (works.exists(_.authors.size >= 2)) authorNames else Vector.empty,
        exactKeys
      )
    }
  }

  def member(profile: Bibliography, key: String): BlockMember =
    BlockMember(
      key,
      profile.source,
      profile.sourceRecordId,
      profile.datasetSnapshot,
      profile.workId,
      profile.normalizedTitle,
      profile.year,
      profile.venue,
      profile.authorNames,
      profile.authorInitials,
      profile.affiliationNames,
      profile.coauthorNames
    )

  def candidate(
      left: BlockMember,
      right: BlockMember,
      blockSize: Int,
      runId: String
  ): Either[DomainViolation, MatchCandidate] = {
    if (left.blockKey.startsWith("fallback:"))
      Left(DomainViolation(ViolationCode.MalformedId, "fallback block does not pair records"))
    else {
      val leftObs =
        CandidateObservation(left.source, left.sourceRecordId, left.datasetSnapshot, left.workId)
      val rightObs =
        CandidateObservation(
          right.source,
          right.sourceRecordId,
          right.datasetSnapshot,
          right.workId
        )
      StableIds.canonicalCandidateObservations(leftObs, rightObs).flatMap { case (first, second) =>
        val storedLeft =
          if (first.source == left.source && first.sourceRecordId == left.sourceRecordId) left
          else right
        val storedRight = if (storedLeft eq left) right else left
        StableIds.matchCandidateId(first, second, left.blockKey).map { id =>
          MatchCandidate(
            id,
            SchemaVersions.domain,
            left.blockKey,
            first,
            second,
            features(storedLeft, storedRight, blockSize, left.blockKey.startsWith("exact:")),
            PrepLimits.MatchFeaturePolicy,
            runId,
            "bibliographic block is not a match decision",
            ProvenanceFactory(SourceType.ScholarChain, id, None, PrepLimits.DerivedSnapshot, runId)
          )
        }
      }
    }
  }

  def features(
      left: BlockMember,
      right: BlockMember,
      blockSize: Int,
      exact: Boolean
  ): Vector[NamedNumber] = {
    def flag(value: Boolean): Double = if (value) 1.0 else 0.0
    val yearDelta = (left.year, right.year) match {
      case (Some(a), Some(b)) => math.abs(a - b).toDouble
      case _                  => -1.0
    }
    Vector(
      NamedNumber(PreparationFeatures.blockSize, blockSize.toDouble),
      NamedNumber(PreparationFeatures.exactSharedIdentifier, flag(exact)),
      NamedNumber(
        PreparationFeatures.sameWorkId,
        flag(left.workId.nonEmpty && left.workId == right.workId)
      ),
      NamedNumber(
        PreparationFeatures.sharedAffiliationNameCount,
        shared(left.affiliationNames, right.affiliationNames)
      ),
      NamedNumber(
        PreparationFeatures.sharedAuthorInitialCount,
        shared(left.authorInitials, right.authorInitials)
      ),
      NamedNumber(
        PreparationFeatures.sharedAuthorNameCount,
        shared(left.authorNames, right.authorNames)
      ),
      NamedNumber(
        PreparationFeatures.sharedCoauthorNameCount,
        shared(left.coauthorNames, right.coauthorNames)
      ),
      NamedNumber(
        PreparationFeatures.titleEqual,
        flag(left.normalizedTitle.nonEmpty && left.normalizedTitle == right.normalizedTitle)
      ),
      NamedNumber(
        PreparationFeatures.venueEqual,
        flag(left.venue.nonEmpty && left.venue == right.venue)
      ),
      NamedNumber(PreparationFeatures.yearAbsDelta, yearDelta),
      NamedNumber(
        PreparationFeatures.yearEqual,
        flag(left.year.nonEmpty && left.year == right.year)
      )
    )
  }

  private def shared(left: Vector[String], right: Vector[String]): Double =
    left.filter(_.nonEmpty).toSet.intersect(right.filter(_.nonEmpty).toSet).size.toDouble

  def edges(work: WorkRecord): Vector[GraphEdge] = {
    val authored = work.authors.flatMap { mention =>
      edge(
        GraphEdgeType.Authored,
        mention.mentionId,
        work.workId,
        GraphSourceEvidence.Work(work.workId),
        work.provenance
      )
    }
    val published = work.venueId.toVector.flatMap { venueId =>
      edge(
        GraphEdgeType.PublishedIn,
        work.workId,
        venueId,
        GraphSourceEvidence.Work(work.workId),
        work.provenance
      )
    }
    authored ++ published
  }

  def topicEdge(link: EnrichmentLink): Option[GraphEdge] =
    if (link.targetKind == EnrichmentTargetKind.Topic)
      link.workId.flatMap { workId =>
        edge(
          GraphEdgeType.HasTopic,
          workId,
          link.targetId,
          GraphSourceEvidence.Work(workId),
          link.provenance
        )
      }
    else None

  private def edge(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String,
      evidence: GraphSourceEvidence,
      provenance: Provenance
  ): Option[GraphEdge] =
    StableIds.graphEdgeId(edgeType, fromId, toId, PrepLimits.FeaturePolicy, evidence).toOption.map {
      id =>
        GraphEdge(
          id,
          SchemaVersions.domain,
          fromId,
          edgeType,
          toId,
          PrepLimits.FeaturePolicy,
          evidence,
          Vector.empty,
          None,
          provenance
        )
    }
}
