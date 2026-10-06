package edu.uic.cs441.scholarchain.core

import java.time.LocalDate
import java.time.format.DateTimeParseException
import scala.collection.mutable.ArrayBuffer

object DomainValidation {
  def checkProvenance(value: Provenance): Either[Vector[DomainViolation], Provenance] = {
    val acc = Acc()
    validateProvenance(value, value.schemaVersion, acc)
    done(acc, value)
  }

  def check(value: WorkRecord): Either[Vector[DomainViolation], WorkRecord] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireRecordProvenance(value.source, value.sourceRecordId, value.provenance, acc)
    parse(StableIds.parseWorkId(value.workId), acc)
    requireNonBlank(value.sourceRecordId, "sourceRecordId", acc)
    parse(StableIds.parseSourceRecordId(value.source, value.sourceRecordId), acc)
    requireNonBlank(value.title, "title", acc)
    if (value.normalizedTitle != TextNorm.title(value.title))
      acc.add(ViolationCode.InconsistentRecord, "normalizedTitle does not match TextNorm.title")
    value.year.foreach(year => requireYear(year, "year", acc))
    value.doi.foreach { doi =>
      StableIds.normalizeDoi(doi) match {
        case Left(violation) => acc.add(violation)
        case Right(normalized) =>
          if (value.doi.contains(normalized) && value.workId != s"work:doi:$normalized")
            acc.add(
              ViolationCode.InconsistentRecord,
              "workId must be the DOI work id when doi is present"
            )
          if (doi != normalized)
            acc.add(ViolationCode.InconsistentRecord, "doi must be normalized")
      }
    }
    value.arxivId.foreach { arxiv =>
      parse(StableIds.workIdFromArxiv(arxiv), acc)
      if (StableIds.workIdFromArxiv(arxiv).toOption.exists(_ != s"work:arxiv:$arxiv"))
        acc.add(ViolationCode.InconsistentRecord, "arxivId must be normalized")
      if (
        value.doi.isEmpty && value.source != SourceType.Crossref && StableIds
          .workIdFromArxiv(arxiv)
          .toOption != Some(value.workId)
      )
        acc.add(
          ViolationCode.InconsistentRecord,
          "workId must be the arXiv work id when doi is absent and arxivId is present"
        )
    }
    StableIds.authoritativeWorkIdForWorkRecord(value) match {
      case Right(expected) if expected != value.workId =>
        acc.add(
          ViolationCode.InconsistentRecord,
          "workId must match the authoritative source observation"
        )
      case Left(error) => acc.add(error)
      case _           => ()
    }
    if (value.source == SourceType.Crossref)
      validateCrossrefSourceRecordId(value.doi, value.sourceRecordId, acc)
    requireWorkSourceLinks(value, acc)
    value.venueId.foreach(id => parse(StableIds.parseVenueId(id), acc))
    if (value.authors.map(_.ordinal).distinct.size != value.authors.size)
      acc.add(ViolationCode.InconsistentRecord, "author ordinals must be unique")
    value.authors.foreach { mention =>
      checkMention(mention, acc)
      if (mention.source != value.source || mention.sourceRecordId != value.sourceRecordId)
        acc.add(
          ViolationCode.InconsistentRecord,
          "nested author mention must cite the same source record"
        )
      if (mention.provenance.datasetSnapshot != value.provenance.datasetSnapshot)
        acc.add(
          ViolationCode.InconsistentRecord,
          "nested author mention snapshot must match the work"
        )
    }
    value.abstractTextRef.foreach(ref => parse(StableIds.parseChunkOrProfileId(ref), acc))
    done(acc, value)
  }

  def check(value: AuthorMention): Either[Vector[DomainViolation], AuthorMention] = {
    val acc = Acc()
    checkMention(value, acc)
    done(acc, value)
  }

  def check(value: CanonicalResearcher): Either[Vector[DomainViolation], CanonicalResearcher] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseResearcherId(value.researcherId), acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    value.identityConfidence.foreach(requireConfidence(_, "identityConfidence", acc))
    if (
      value.researcherId.startsWith("researcher:scholarchain:") && value.externalIds.exists(
        _.interpretation == IdentifierInterpretation.ValidatedExternal
      )
    )
      acc.add(
        ViolationCode.UnconfirmedIdentity,
        "a provisional ScholarChain researcher id cannot carry a validated external id"
      )
    if (
      value.researcherId.startsWith("researcher:orcid:") &&
      !value.externalIds.exists(id =>
        id.namespace == "orcid" &&
          value.researcherId == s"researcher:orcid:${id.value}" &&
          id.interpretation == IdentifierInterpretation.ValidatedExternal
      )
    )
      acc.add(
        ViolationCode.InconsistentRecord,
        "ORCID researcher id must repeat the ORCID as a validated external id"
      )
    value.externalIds.foreach { id =>
      if (id.namespace == "openalex" || id.namespace == "openalex-author")
        if (id.interpretation != IdentifierInterpretation.DisambiguationHypothesis)
          acc.add(
            ViolationCode.UnconfirmedIdentity,
            "OpenAlex author IDs must stay disambiguation hypotheses"
          )
    }
    done(acc, value)
  }

  /** Full validation of derived records requires independently validated source works. */
  def check(value: AuthorshipRecord): Either[Vector[DomainViolation], AuthorshipRecord] =
    missingWorkContext(checkStructure(value))
  def check(value: PublicationTeam): Either[Vector[DomainViolation], PublicationTeam] =
    missingWorkContext(checkStructure(value))
  def check(value: CoauthorPairCandidate): Either[Vector[DomainViolation], CoauthorPairCandidate] =
    missingWorkContext(checkStructure(value))

  def check(
      value: AuthorshipRecord,
      work: WorkRecord
  ): Either[Vector[DomainViolation], AuthorshipRecord] =
    WorkValidationContext.create(Vector(work)).flatMap(check(value, _))
  def check(
      value: PublicationTeam,
      work: WorkRecord
  ): Either[Vector[DomainViolation], PublicationTeam] =
    WorkValidationContext.create(Vector(work)).flatMap(check(value, _))
  def check(
      value: CoauthorPairCandidate,
      work: WorkRecord
  ): Either[Vector[DomainViolation], CoauthorPairCandidate] =
    WorkValidationContext.create(Vector(work)).flatMap(check(value, _))

  def check(
      value: AuthorshipRecord,
      context: WorkValidationContext
  ): Either[Vector[DomainViolation], AuthorshipRecord] =
    checkStructure(value).flatMap { record =>
      bindWork(record.workId, record.provenance, context).flatMap { work =>
        work.authors.find(_.mentionId == record.mentionId) match {
          case Some(mention) if mention.ordinal == record.position =>
            Right(record)
          case _ =>
            inconsistent(
              "authorship mention and position must match the validated work"
            )
        }
      }
    }

  def check(
      value: PublicationTeam,
      context: WorkValidationContext
  ): Either[Vector[DomainViolation], PublicationTeam] =
    checkStructure(value).flatMap { record =>
      bindWork(record.workId, record.provenance, context).flatMap { work =>
        if (record.memberMentionIds == work.authors.sortBy(_.ordinal).map(_.mentionId))
          Right(record)
        else
          inconsistent("publication team must contain all validated work mentions in author order")
      }
    }

  def check(
      value: CoauthorPairCandidate,
      context: WorkValidationContext
  ): Either[Vector[DomainViolation], CoauthorPairCandidate] =
    checkStructure(value).flatMap { record =>
      bindWork(record.workId, record.provenance, context).flatMap { work =>
        val ids = work.authors.map(_.mentionId).toSet
        if (record.doi != work.doi || record.arxivId != work.arxivId || record.year != work.year)
          inconsistent("pair doi, arxivId and year must match the validated work observation")
        else if (!ids.contains(record.leftMentionId) || !ids.contains(record.rightMentionId))
          inconsistent("pair mentions must occur in the validated work")
        else Right(record)
      }
    }

  private def missingWorkContext[T](
      result: Either[Vector[DomainViolation], T]
  ): Either[Vector[DomainViolation], T] =
    Left(
      result.left.toOption.getOrElse(Vector.empty) :+ DomainViolation(
        ViolationCode.MissingValidationContext,
        "full derived-record validation requires a WorkRecord or WorkValidationContext"
      )
    )

  private def inconsistent[T](message: String): Either[Vector[DomainViolation], T] =
    Left(Vector(DomainViolation(ViolationCode.InconsistentRecord, message)))

  /** The source snapshot binds the observation. runId names the producing run and may differ from
    * the acquisition run; it is validated syntactically but is not a bibliography key. Derived
    * sourceUri is only a locator; it must agree when carrying a DOI/arXiv identifier.
    */
  private def bindWork(
      workId: String,
      provenance: Provenance,
      context: WorkValidationContext
  ): Either[Vector[DomainViolation], WorkRecord] =
    context.lookup(provenance) match {
      case None =>
        Left(
          Vector(
            DomainViolation(
              ViolationCode.MissingValidationContext,
              "no validated work for source, sourceRecordId and datasetSnapshot"
            )
          )
        )
      case Some(work) if work.workId != workId =>
        inconsistent("workId must match the validated source record and snapshot")
      case Some(work) =>
        val acc = Acc()
        requireBibliographicLink(provenance.sourceUri, work, "derived provenance.sourceUri", acc)
        done(acc, work)
    }

  def checkStructure(value: AuthorshipRecord): Either[Vector[DomainViolation], AuthorshipRecord] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseWorkId(value.workId), acc)
    parse(StableIds.parseMentionId(value.mentionId), acc)
    if (value.position < 1) acc.add(ViolationCode.InconsistentRecord, "position must be >= 1")
    StableIds.parseMentionIdParts(value.mentionId) match {
      case Right(mention) if mention.ordinal != value.position =>
        acc.add(
          ViolationCode.InconsistentRecord,
          "authorship position must match the ordinal embedded in mentionId"
        )
      case Right(mention) =>
        SourceType.values.find(_.wire.equalsIgnoreCase(mention.sourceWire)) match {
          case Some(source) =>
            requireRecordProvenance(source, mention.sourceRecordId, value.provenance, acc)
          case None => ()
        }
      case _ => ()
    }
    value.resolvedResearcherId.foreach(id => parse(StableIds.parseResearcherId(id), acc))
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    if (value.resolvedResearcherId.isEmpty && value.uncertainty.trim.isEmpty)
      acc.add(ViolationCode.UnconfirmedIdentity, "unresolved authorship needs uncertainty")
    done(acc, value)
  }

  def checkStructure(value: PublicationTeam): Either[Vector[DomainViolation], PublicationTeam] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseWorkId(value.workId), acc)
    if (value.memberMentionIds.size != value.teamSize)
      acc.add(ViolationCode.InconsistentRecord, "teamSize must equal memberMentionIds length")
    requirePublicationTeamMentions(value, acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def checkStructure(
      value: CoauthorPairCandidate
  ): Either[Vector[DomainViolation], CoauthorPairCandidate] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseWorkId(value.workId), acc)
    validateCoauthorPairIdentifiers(value, acc)
    parse(StableIds.parseMentionId(value.leftMentionId), acc)
    parse(StableIds.parseMentionId(value.rightMentionId), acc)
    requireCoauthorMentions(value, acc)
    if (value.leftMentionId.compareTo(value.rightMentionId) >= 0)
      acc.add(
        ViolationCode.InvalidPairOrder,
        "coauthor pair mentions must be in canonical string order"
      )
    if (value.leftOrdinal < 1 || value.rightOrdinal < 1)
      acc.add(ViolationCode.InconsistentRecord, "pair ordinals must be >= 1")
    value.year.foreach(year => requireYear(year, "year", acc))
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: CoauthorEdge): Either[Vector[DomainViolation], CoauthorEdge] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseResearcherId(value.researcherA), acc)
    parse(StableIds.parseResearcherId(value.researcherB), acc)
    if (value.researcherA.compareTo(value.researcherB) >= 0)
      acc.add(
        ViolationCode.InvalidPairOrder,
        "coauthor edge researcherA must be strictly less than researcherB"
      )
    requireWindow(value.windowStartYear, value.windowEndYear, acc)
    StableIds.coauthorEdgeId(
      value.researcherA,
      value.researcherB,
      value.windowStartYear,
      value.windowEndYear,
      value.policyVersion
    ) match {
      case Right(expected) if expected != value.edgeId =>
        acc.add(ViolationCode.MalformedId, "coauthor edge id does not match the stable formula")
      case Left(violation) => acc.add(violation)
      case _               => ()
    }
    if (value.jointPublicationCount < 1)
      acc.add(ViolationCode.InconsistentRecord, "jointPublicationCount must be >= 1")
    requireYear(value.firstCollaborationYear, "firstCollaborationYear", acc)
    requireYear(value.lastCollaborationYear, "lastCollaborationYear", acc)
    if (value.firstCollaborationYear > value.lastCollaborationYear)
      acc.add(ViolationCode.ReversedTimeWindow, "collaboration years are reversed")
    if (
      value.firstCollaborationYear < value.windowStartYear ||
      value.lastCollaborationYear > value.windowEndYear
    )
      acc.add(
        ViolationCode.InconsistentRecord,
        "collaboration years fall outside the graph window"
      )
    requireRepresentativeWorks(value.representativeWorkIds, value.jointPublicationCount, acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: ResearcherMetrics): Either[Vector[DomainViolation], ResearcherMetrics] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseResearcherId(value.researcherId), acc)
    requireWindow(value.windowStartYear, value.windowEndYear, acc)
    requireNonNegative(value.publicationCount, "publicationCount", acc)
    requireNonNegative(value.distinctCoauthorCount, "distinctCoauthorCount", acc)
    requireNonNegative(value.totalCoauthorOccurrences, "totalCoauthorOccurrences", acc)
    requireNonNegative(value.maximumCoauthorsOnOnePaper, "maximumCoauthorsOnOnePaper", acc)
    requireFiniteNonNegative(value.averageCoauthorsPerPaper, "averageCoauthorsPerPaper", acc)
    requireResearcherMetricsCoauthorConsistency(value, acc)
    requireFiniteNonNegative(value.weightedDegree, "weightedDegree", acc)
    value.bridgeScore.foreach(requireFinite(_, "bridgeScore", acc))
    value.coreness.foreach { core =>
      if (core < 0) acc.add(ViolationCode.InconsistentRecord, "coreness must be >= 0")
    }
    requireNonBlank(value.componentId, "componentId", acc)
    requireNonBlank(value.policyVersion, "policyVersion", acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: Venue): Either[Vector[DomainViolation], Venue] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseVenueId(value.venueId), acc)
    requireNonBlank(value.name, "name", acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: Institution): Either[Vector[DomainViolation], Institution] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseInstitutionId(value.institutionId), acc)
    value.ror.foreach { ror =>
      if (
        StableIds.institutionIdFromRor(ror).toOption != Some(value.institutionId) &&
        value.institutionId.startsWith("institution:ror:")
      )
        acc.add(ViolationCode.InconsistentRecord, "institution id does not match ror")
    }
    value.ringgold.foreach { ringgold =>
      if (
        value.institutionId.startsWith("institution:ringgold:") && !StableIds
          .institutionIdFromRinggold(ringgold)
          .contains(value.institutionId)
      )
        acc.add(ViolationCode.InconsistentRecord, "institution id does not match ringgold")
    }
    requireNonBlank(value.name, "name", acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: Topic): Either[Vector[DomainViolation], Topic] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseTopicId(value.topicId), acc)
    value.sourceTopicId.foreach { sourceId =>
      if (!StableIds.topicIdFromOpenAlex(sourceId).contains(value.topicId))
        acc.add(ViolationCode.InconsistentRecord, "topicId must match sourceTopicId")
    }
    value.sourceScore.foreach(requireFinite(_, "sourceScore", acc))
    requireNonBlank(value.name, "name", acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: MatchDecision): Either[Vector[DomainViolation], MatchDecision] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireNonBlank(value.sourceId, "sourceId", acc)
    requireNonBlank(value.targetId, "targetId", acc)
    requireConfidence(value.confidence, "confidence", acc)
    if (value.reasonCodes.isEmpty || value.reasonCodes.exists(_.trim.isEmpty))
      acc.add(ViolationCode.InconsistentRecord, "reasonCodes must be non-empty")
    requireNonBlank(value.policyVersion, "policyVersion", acc)
    parse(StableIds.parseRunId(value.runId), acc)
    if (value.runId != value.provenance.runId)
      acc.add(ViolationCode.InconsistentRecord, "runId must match provenance.runId")
    value.features.foreach(feature => requireFinite(feature.value, feature.name, acc))
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    if (value.decision == MatchOutcome.Accepted && value.uncertainty.trim.isEmpty)
      acc.add(ViolationCode.UnconfirmedIdentity, "an accepted match still needs uncertainty text")
    done(acc, value)
  }

  def check(value: GraphNode): Either[Vector[DomainViolation], GraphNode] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireNodeId(value.nodeClass, value.nodeId, acc)
    requireDistinctProperties(value.properties, acc)
    requireNonBlank(value.label, "label", acc)
    done(acc, value)
  }

  def check(value: GraphEdge): Either[Vector[DomainViolation], GraphEdge] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    if (GraphEdgeType.isUndirected(value.edgeType) && value.fromId.compareTo(value.toId) >= 0)
      acc.add(
        ViolationCode.InvalidPairOrder,
        "undirected graph edge endpoints must be in canonical order"
      )
    requireGraphEdgeEndpoints(value.edgeType, value.fromId, value.toId, acc)
    parse(StableIds.graphEvidencePointer(value.sourceEvidence), acc)
    value.sourceEvidence match {
      case GraphSourceEvidence.SourceRecord(source, id, snapshot) =>
        if (
          source != value.provenance.source || id != value.provenance.sourceRecordId || snapshot != value.provenance.datasetSnapshot
        )
          acc.add(
            ViolationCode.InconsistentRecord,
            "source evidence must match provenance source, record and snapshot"
          )
      case GraphSourceEvidence.Work(workId) =>
        requireGraphWorkEvidence(value, workId, acc)
    }
    requireDistinctProperties(value.properties, acc)
    StableIds.graphEdgeId(
      value.edgeType,
      value.fromId,
      value.toId,
      value.policyVersion,
      value.sourceEvidence
    ) match {
      case Right(expected) if expected != value.edgeId =>
        acc.add(ViolationCode.MalformedId, "graph edge id does not match the stable formula")
      case Left(violation) => acc.add(violation)
      case _               => ()
    }
    val reserved = Set(
      "jointPublicationCount",
      "firstCollaborationYear",
      "lastCollaborationYear",
      "representativeWorkIds"
    )
    if (value.properties.exists(p => reserved.contains(p.name)))
      acc.add(
        ViolationCode.InconsistentRecord,
        "coauthorship properties must use the typed coauthorship field"
      )
    if (value.edgeType == GraphEdgeType.CoauthoredWith)
      value.coauthorship match {
        case Some(properties) => requireCoauthoredWithPropertyValues(properties, acc)
        case None =>
          acc.add(
            ViolationCode.InconsistentRecord,
            "COAUTHORED_WITH requires typed coauthorship properties"
          )
      }
    else if (value.coauthorship.nonEmpty)
      acc.add(
        ViolationCode.InconsistentRecord,
        "coauthorship properties are only valid on COAUTHORED_WITH"
      )
    done(acc, value)
  }

  def check(value: EvidenceItem): Either[Vector[DomainViolation], EvidenceItem] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(evidenceIdForType(value.evidenceType, value.evidenceId), acc)
    value.chunkId.foreach(id => parse(StableIds.parseChunkOrProfileId(id), acc))
    value.workId.foreach(id => parse(StableIds.parseWorkId(id), acc))
    requireNonBlank(value.sourceUri, "sourceUri", acc)
    requireFinite(value.score, "score", acc)
    requireEvidenceLocator(value, acc)
    done(acc, value)
  }

  def check(value: EvidenceBundle): Either[Vector[DomainViolation], EvidenceBundle] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireNonBlank(value.bundleId, "bundleId", acc)
    requireNonBlank(value.queryId, "queryId", acc)
    if (value.items.isEmpty)
      acc.add(ViolationCode.InconsistentRecord, "evidence bundle must contain an item")
    value.items.foreach(item => check(item).left.foreach(_.foreach(acc.add)))
    value.researcherIds.foreach(id => parse(StableIds.parseResearcherId(id), acc))
    value.identityConfidence.foreach(requireConfidence(_, "identityConfidence", acc))
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    done(acc, value)
  }

  def check(value: QueryPlan): Either[Vector[DomainViolation], QueryPlan] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    if (!value.planId.matches("plan:[0-9a-f]{64}"))
      acc.add(ViolationCode.MalformedId, s"malformed plan id: ${value.planId}")
    requireNonBlank(value.question, "question", acc)
    if (value.operations.isEmpty)
      acc.add(ViolationCode.InconsistentRecord, "query plan operations must be non-empty")
    requireWindow(value.window.startYear, value.window.endYear, acc)
    if (value.graphLimit < 1 || value.vectorLimit < 1 || value.maxPathDepth < 1)
      acc.add(ViolationCode.InconsistentRecord, "query limits must be positive")
    done(acc, value)
  }

  def check(value: AnswerClaim): Either[Vector[DomainViolation], AnswerClaim] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireNonBlank(value.claimId, "claimId", acc)
    requireNonBlank(value.text, "text", acc)
    if (value.evidenceIds.isEmpty)
      acc.add(ViolationCode.InconsistentRecord, "claim evidenceIds must be non-empty")
    value.evidenceIds.foreach(id => parse(StableIds.parseEvidenceId(id), acc))
    if (value.uncertainty.forall(_.trim.isEmpty))
      acc.add(ViolationCode.InconsistentRecord, "claim uncertainty must be present")
    done(acc, value)
  }

  def check(value: AnswerResponse): Either[Vector[DomainViolation], AnswerResponse] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireNonBlank(value.responseId, "responseId", acc)
    if (!value.queryPlanId.matches("plan:[0-9a-f]{64}"))
      acc.add(ViolationCode.MalformedId, s"malformed plan id: ${value.queryPlanId}")
    parse(StableIds.parseRunId(value.runId), acc)
    if (value.runId != value.provenance.runId)
      acc.add(ViolationCode.InconsistentRecord, "runId must match provenance.runId")
    requireNonBlank(value.summary, "summary", acc)
    requireNonBlank(value.evidenceBundleId, "evidenceBundleId", acc)
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    value.claims.foreach(claim => check(claim).left.foreach(_.foreach(acc.add)))
    done(acc, value)
  }

  def check(value: RunManifest): Either[Vector[DomainViolation], RunManifest] = {
    val acc = Acc()
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    parse(StableIds.parseRunId(value.runId), acc)
    if (value.runId != value.provenance.runId)
      acc.add(ViolationCode.InconsistentRecord, "runId must match provenance.runId")
    requireNonBlank(value.pipelineName, "pipelineName", acc)
    if (!SchemaVersions.supportedConfig.contains(value.configSchemaVersion))
      acc.add(
        ViolationCode.UnsupportedSchemaVersion,
        s"unsupported config schema ${value.configSchemaVersion}"
      )
    if (!value.configFingerprint.matches("[0-9a-f]{64}"))
      acc.add(ViolationCode.MalformedId, "config fingerprint must be sha256 hex")
    if (value.datasetSnapshots.isEmpty)
      acc.add(ViolationCode.MissingProvenance, "run manifest needs dataset snapshots")
    value.datasetSnapshots.foreach { snapshot =>
      requireNonBlank(snapshot.snapshot, "dataset snapshot", acc)
    }
    done(acc, value)
  }

  private def checkMention(value: AuthorMention, acc: Acc): Unit = {
    requireSchema(value.schemaVersion, acc)
    validateProvenance(value.provenance, value.schemaVersion, acc)
    requireRecordProvenance(value.source, value.sourceRecordId, value.provenance, acc)
    val expected = StableIds.mentionId(value.source, value.sourceRecordId, value.ordinal)
    if (value.mentionId != expected)
      acc.add(ViolationCode.MalformedId, "mention id does not match source, record, and ordinal")
    else parse(StableIds.parseMentionId(value.mentionId), acc)
    if (value.ordinal < 1) acc.add(ViolationCode.InconsistentRecord, "ordinal must be >= 1")
    requireNonBlank(value.nameText, "nameText", acc)
    if (value.normalizedName != TextNorm.personName(value.nameText))
      acc.add(ViolationCode.InconsistentRecord, "normalizedName does not match TextNorm.personName")
    requireNonBlank(value.uncertainty, "uncertainty", acc)
    value.observedOrcid.foreach { orcid =>
      if (StableIds.researcherIdFromValidatedOrcid(orcid).isLeft)
        acc.add(ViolationCode.MalformedId, s"malformed observed orcid: $orcid")
    }
    value.observedOpenAlexAuthorId.foreach { authorId =>
      if (StableIds.openAlexAuthorToken(authorId).isLeft)
        acc.add(ViolationCode.MalformedId, s"malformed OpenAlex author id: $authorId")
    }
    value.identityStatus match {
      case MentionIdentityStatus.NameOnlyUnconfirmed =>
        if (value.observedOrcid.nonEmpty || value.observedOpenAlexAuthorId.nonEmpty)
          acc.add(
            ViolationCode.UnconfirmedIdentity,
            "a name-only mention cannot carry an external identifier"
          )
        if (value.resolvedResearcherId.nonEmpty)
          acc.add(
            ViolationCode.UnconfirmedIdentity,
            "a name-only mention is not a resolved researcher"
          )
      case MentionIdentityStatus.ExternalIdentifierObserved =>
        if (value.observedOrcid.isEmpty && value.observedOpenAlexAuthorId.isEmpty)
          acc.add(
            ViolationCode.UnconfirmedIdentity,
            "external-identifier status requires an observed identifier"
          )
        if (value.resolvedResearcherId.nonEmpty)
          acc.add(
            ViolationCode.UnconfirmedIdentity,
            "an observed identifier is not a match decision"
          )
      case MentionIdentityStatus.ResolvedToResearcher =>
        value.resolvedResearcherId match {
          case Some(id) => parse(StableIds.parseResearcherId(id), acc)
          case None =>
            acc.add(
              ViolationCode.UnconfirmedIdentity,
              "resolved status requires a researcher id from a match decision"
            )
        }
    }
  }

  private def requireRecordProvenance(
      source: SourceType,
      sourceRecordId: String,
      provenance: Provenance,
      acc: Acc
  ): Unit =
    if (provenance.source != source || provenance.sourceRecordId != sourceRecordId)
      acc.add(
        ViolationCode.InconsistentRecord,
        "provenance source and sourceRecordId must match the record"
      )

  private def requireCoauthorMentions(value: CoauthorPairCandidate, acc: Acc): Unit = {
    (
      StableIds.parseMentionIdParts(value.leftMentionId),
      StableIds.parseMentionIdParts(value.rightMentionId)
    ) match {
      case (Right(left), Right(right)) =>
        if (left.sourceWire != right.sourceWire || left.sourceRecordId != right.sourceRecordId)
          acc.add(
            ViolationCode.InconsistentRecord,
            "coauthor pair mentions must belong to the same work"
          )
        if (left.ordinal != value.leftOrdinal)
          acc.add(
            ViolationCode.InconsistentRecord,
            "leftOrdinal must match the ordinal embedded in leftMentionId"
          )
        if (right.ordinal != value.rightOrdinal)
          acc.add(
            ViolationCode.InconsistentRecord,
            "rightOrdinal must match the ordinal embedded in rightMentionId"
          )
        val provenanceSource = provenancePairSource(value.provenance)
        val mentionsMatchProvenance =
          mentionCites(left, provenanceSource) && mentionCites(right, provenanceSource)
        val embeddedAgrees =
          if (value.workId.startsWith("work:dblp:") || value.workId.startsWith("work:openalex:"))
            StableIds
              .sourceNativeWorkId(value.provenance.source, value.provenance.sourceRecordId)
              .contains(value.workId)
          else true
        if (!mentionsMatchProvenance || !embeddedAgrees)
          acc.add(
            ViolationCode.InconsistentRecord,
            "coauthor pair mentions, provenance, and any source record " +
              "embedded in workId must agree"
          )
      case _ => ()
    }
  }

  private def validateCoauthorPairIdentifiers(value: CoauthorPairCandidate, acc: Acc): Unit = {
    value.doi.foreach { doi =>
      StableIds.normalizeDoi(doi) match {
        case Left(violation) => acc.add(violation)
        case Right(normalized) =>
          if (value.doi.contains(normalized) && value.workId != s"work:doi:$normalized")
            acc.add(
              ViolationCode.InconsistentRecord,
              "workId must be the DOI work id when doi is present on the pair"
            )
          if (doi != normalized)
            acc.add(ViolationCode.InconsistentRecord, "doi must be normalized")
      }
    }
    value.arxivId.foreach { arxiv =>
      parse(StableIds.workIdFromArxiv(arxiv), acc)
      if (StableIds.workIdFromArxiv(arxiv).toOption.exists(_ != s"work:arxiv:$arxiv"))
        acc.add(ViolationCode.InconsistentRecord, "arxivId must be normalized")
      if (
        value.doi.isEmpty && value.provenance.source != SourceType.Crossref && StableIds
          .workIdFromArxiv(arxiv)
          .toOption != Some(value.workId)
      )
        acc.add(
          ViolationCode.InconsistentRecord,
          "workId must be the arXiv work id when doi is absent and arxivId is present"
        )
    }
  }

  private def requirePublicationTeamMentions(value: PublicationTeam, acc: Acc): Unit = {
    val parsed = value.memberMentionIds.map { id =>
      parse(StableIds.parseMentionId(id), acc)
      StableIds.parseMentionIdParts(id)
    }
    if (parsed.exists(_.isLeft)) return
    val mentions = parsed.collect { case Right(mention) => mention }
    if (value.memberMentionIds.distinct.size != value.memberMentionIds.size)
      acc.add(ViolationCode.InconsistentRecord, "member mention ids must be distinct")
    if (mentions.map(_.ordinal).distinct.size != mentions.size)
      acc.add(ViolationCode.InconsistentRecord, "member mention ordinals must be distinct")
    if (value.teamSize != mentions.map(_.ordinal).distinct.size)
      acc.add(
        ViolationCode.InconsistentRecord,
        "teamSize must equal the number of distinct member mentions"
      )
    val distinctSources = mentions.map(m => (m.sourceWire, m.sourceRecordId)).distinct
    if (distinctSources.size != 1)
      acc.add(
        ViolationCode.InconsistentRecord,
        "publication team mentions must belong to the same work"
      )
    distinctSources.headOption.foreach { case (sourceWire, sourceRecordId) =>
      val provenanceSource = provenancePairSource(value.provenance)
      if (!mentionCites(mentions.head, provenanceSource))
        acc.add(
          ViolationCode.InconsistentRecord,
          "publication team provenance must match the member mention source record"
        )

    }
  }

  private def requireWorkSourceLinks(work: WorkRecord, acc: Acc): Unit = {
    requireBibliographicLink(work.provenance.sourceUri, work, "provenance.sourceUri", acc)
    requireBibliographicLink(work.externalUrl, work, "externalUrl", acc)
    work.authors.foreach(m =>
      requireBibliographicLink(m.provenance.sourceUri, work, "author provenance.sourceUri", acc)
    )
  }

  private def requireBibliographicLink(
      uri: Option[String],
      work: WorkRecord,
      field: String,
      acc: Acc
  ): Unit = {
    val authoritativeDoi = work.doi.orElse(
      if (work.source == SourceType.Crossref) StableIds.normalizeDoi(work.sourceRecordId).toOption
      else None
    )
    StableIds.doiFromSourceUri(uri).foreach { observed =>
      if (!authoritativeDoi.contains(observed))
        acc.add(
          ViolationCode.InconsistentRecord,
          s"$field DOI must match the authoritative work DOI"
        )
    }
    StableIds.arxivFromSourceUri(uri).foreach { observed =>
      if (!work.arxivId.contains(observed))
        acc.add(
          ViolationCode.InconsistentRecord,
          s"$field arXiv identifier must match the work arxivId"
        )
    }
    uri.foreach { raw =>
      if (
        raw.trim.matches("(?i)^(?:https?://(?:dx\\.)?doi\\.org/|doi:).*") && StableIds
          .normalizeDoi(raw)
          .isLeft
      )
        acc.add(ViolationCode.MalformedId, s"$field contains a malformed DOI link")
      if (
        raw.trim.matches("(?i)^(?:https?://arxiv\\.org/(?:abs|pdf)/|arxiv:).*") && StableIds
          .arxivFromSourceUri(Some(raw))
          .isEmpty
      )
        acc.add(ViolationCode.MalformedId, s"$field contains a malformed arXiv link")
    }
  }

  private def validateCrossrefSourceRecordId(
      doi: Option[String],
      sourceRecordId: String,
      acc: Acc
  ): Unit =
    StableIds.normalizeDoi(sourceRecordId) match {
      case Right(recordDoi) if doi.exists(_ != recordDoi) =>
        acc.add(
          ViolationCode.InconsistentRecord,
          "Crossref sourceRecordId must match the work DOI"
        )
      case Left(violation) => acc.add(violation)
      case _               => ()
    }

  private def approximatelyEqual(actual: Double, expected: Double): Boolean =
    java.lang.Double
      .isFinite(actual) && math.abs(actual - expected) <= math.max(1e-12, 4 * math.ulp(expected))

  private def requireResearcherMetricsCoauthorConsistency(
      value: ResearcherMetrics,
      acc: Acc
  ): Unit = {
    def require(condition: Boolean, message: String): Unit =
      if (!condition) acc.add(ViolationCode.InconsistentRecord, message)
    val total = value.totalCoauthorOccurrences
    val maximum = value.maximumCoauthorsOnOnePaper
    val distinct = value.distinctCoauthorCount
    require(distinct <= total, "distinctCoauthorCount cannot exceed totalCoauthorOccurrences")
    require(maximum <= distinct, "maximumCoauthorsOnOnePaper cannot exceed distinctCoauthorCount")
    require(maximum <= total, "maximumCoauthorsOnOnePaper cannot exceed totalCoauthorOccurrences")
    require(
      (total == 0) == (distinct == 0),
      "zero occurrences and zero distinct coauthors must agree"
    )
    require((total == 0) == (maximum == 0), "zero occurrences and zero maximum must agree")
    if (total == 0) {
      require(
        value.averageCoauthorsPerPaper == 0.0,
        "zero coauthor occurrences require exactly zero averageCoauthorsPerPaper"
      )
      require(
        value.weightedDegree == 0.0,
        "zero coauthor occurrences require exactly zero weightedDegree"
      )
    }
    if (value.publicationCount == 0) {
      require(
        total == 0 && distinct == 0 && maximum == 0 && value.averageCoauthorsPerPaper == 0.0 && value.weightedDegree == 0.0,
        "zero publications require zero collaboration counts, average and weighted degree"
      )
    } else if (value.publicationCount > 0) {
      require(
        approximatelyEqual(
          value.averageCoauthorsPerPaper,
          total.toDouble / value.publicationCount.toDouble
        ),
        "averageCoauthorsPerPaper must equal totalCoauthorOccurrences / publicationCount"
      )
      require(
        BigInt(total) <= BigInt(value.publicationCount) * BigInt(maximum),
        "totalCoauthorOccurrences cannot exceed publicationCount times maximumCoauthorsOnOnePaper"
      )
    }
    require(
      approximatelyEqual(value.weightedDegree, total.toDouble),
      "weightedDegree must equal totalCoauthorOccurrences for the complete canonical graph"
    )
    value.coreness.foreach(core =>
      require(core.toLong <= distinct, "coreness cannot exceed distinctCoauthorCount")
    )
  }

  /** Publication-specific relations cite the work whose facts they carry. Generic graph provenance
    * relations may cite a third supporting work and have no publication endpoint rule.
    */
  private def requireGraphWorkEvidence(edge: GraphEdge, workId: String, acc: Acc): Unit = {
    val agrees = edge.edgeType match {
      case GraphEdgeType.CoauthoredWith =>
        edge.coauthorship.exists(_.representativeWorkIds.contains(workId))
      case GraphEdgeType.Authored                             => workId == edge.toId
      case GraphEdgeType.PublishedIn | GraphEdgeType.HasTopic => workId == edge.fromId
      case _                                                  => true
    }
    if (!agrees)
      acc.add(
        ViolationCode.InconsistentRecord,
        "work source evidence must match the publication endpoint or a representative coauthorship work"
      )
  }

  private def requireGraphEdgeEndpoints(
      edgeType: GraphEdgeType,
      fromId: String,
      toId: String,
      acc: Acc
  ): Unit =
    edgeType match {
      case GraphEdgeType.CoauthoredWith =>
        parse(StableIds.parseResearcherId(fromId), acc)
        parse(StableIds.parseResearcherId(toId), acc)
      case GraphEdgeType.Authored =>
        if (StableIds.parseMentionId(fromId).isLeft && StableIds.parseResearcherId(fromId).isLeft)
          acc.add(ViolationCode.MalformedId, s"malformed author endpoint: $fromId")
        parse(StableIds.parseWorkId(toId), acc)
      case GraphEdgeType.ResolvesTo =>
        parse(StableIds.parseMentionId(fromId), acc)
        parse(StableIds.parseResearcherId(toId), acc)
      case GraphEdgeType.PublishedIn =>
        parse(StableIds.parseWorkId(fromId), acc)
        parse(StableIds.parseVenueId(toId), acc)
      case GraphEdgeType.AffiliatedWith =>
        parse(StableIds.parseResearcherId(fromId), acc)
        parse(StableIds.parseInstitutionId(toId), acc)
      case GraphEdgeType.HasTopic =>
        parse(StableIds.parseWorkId(fromId), acc)
        parse(StableIds.parseTopicId(toId), acc)
      case GraphEdgeType.DerivedFrom | GraphEdgeType.SupportedBy =>
        parse(StableIds.parseWorkId(fromId), acc)
        parse(StableIds.parseWorkId(toId), acc)
    }

  private def requireDistinctProperties(properties: Vector[NamedText], acc: Acc): Unit = {
    if (properties.map(_.name).distinct.size != properties.size)
      acc.add(ViolationCode.InconsistentRecord, "property names must be distinct")
    properties.foreach(p => requireNonBlank(p.name, "property name", acc))
  }

  private def requireCoauthoredWithPropertyValues(
      properties: CoauthorshipProperties,
      acc: Acc
  ): Unit = {
    if (properties.jointPublicationCount < 1)
      acc.add(ViolationCode.InconsistentRecord, "jointPublicationCount must be a positive integer")
    requireYear(properties.firstCollaborationYear, "firstCollaborationYear", acc)
    requireYear(properties.lastCollaborationYear, "lastCollaborationYear", acc)
    if (properties.firstCollaborationYear > properties.lastCollaborationYear)
      acc.add(ViolationCode.ReversedTimeWindow, "collaboration years are reversed")
    requireRepresentativeWorks(
      properties.representativeWorkIds,
      properties.jointPublicationCount,
      acc
    )
  }

  private def requireRepresentativeWorks(ids: Vector[String], count: Long, acc: Acc): Unit = {
    if (ids.isEmpty || ids.distinct.size != ids.size || ids.size.toLong > count)
      acc.add(
        ViolationCode.InconsistentRecord,
        "representativeWorkIds must be non-empty, distinct, and bounded by jointPublicationCount"
      )
    ids.foreach(id => parse(StableIds.parseWorkId(id), acc))
  }

  private def requireEvidenceLocator(value: EvidenceItem, acc: Acc): Unit =
    value.evidenceType match {
      case EvidenceType.GraphPath =>
        value.graphPath match {
          case Some(path) if path.nonEmpty =>
            StableIds.nonTextEvidenceId("graph-path", path) match {
              case Right(expected) if expected != value.evidenceId =>
                acc.add(
                  ViolationCode.InconsistentRecord,
                  "graph path evidence id does not match graphPath"
                )
              case Left(violation) => acc.add(violation)
              case _               => ()
            }
            path.foreach(id => parse(StableIds.parseResearcherId(id), acc))
          case _ =>
            acc.add(ViolationCode.InconsistentRecord, "graph path evidence requires graphPath")
        }
      case EvidenceType.Metric =>
        value.metricLocator match {
          case Some(locator) =>
            requireWindow(locator.windowStartYear, locator.windowEndYear, acc)
            parse(StableIds.parseResearcherId(locator.researcherId), acc)
            StableIds.nonTextEvidenceId(
              "metric",
              Seq(
                locator.researcherId,
                locator.metric.wire,
                locator.windowStartYear.toString,
                locator.windowEndYear.toString,
                locator.policyVersion
              )
            ) match {
              case Right(expected) if expected != value.evidenceId =>
                acc.add(
                  ViolationCode.InconsistentRecord,
                  "metric evidence id does not match metricLocator"
                )
              case Left(violation) => acc.add(violation)
              case _               => ()
            }
          case None =>
            acc.add(ViolationCode.InconsistentRecord, "metric evidence requires metricLocator")
        }
      case EvidenceType.CoauthorEdge =>
        value.edgeLocatorId match {
          case Some(edgeId) =>
            if (
              StableIds.parseGraphEdgeId(edgeId).isLeft &&
              StableIds.parseCoauthorEdgeId(edgeId).isLeft
            )
              acc.add(ViolationCode.MalformedId, s"malformed edge evidence locator: $edgeId")
            StableIds.nonTextEvidenceId("edge", Seq(edgeId)) match {
              case Right(expected) if expected != value.evidenceId =>
                acc.add(
                  ViolationCode.InconsistentRecord,
                  "edge evidence id does not match edgeLocatorId"
                )
              case Left(violation) => acc.add(violation)
              case _               => ()
            }
          case None =>
            acc.add(ViolationCode.InconsistentRecord, "edge evidence requires edgeLocatorId")
        }
      case _ => ()
    }

  private def provenancePairSource(provenance: Provenance): (String, String) =
    (
      provenance.source.wire.toLowerCase(java.util.Locale.ROOT),
      provenance.sourceRecordId
    )

  private def mentionCites(mention: ParsedMentionId, carried: (String, String)): Boolean =
    mention.sourceWire == carried._1 && mention.sourceRecordId == carried._2

  private def evidenceIdForType(
      evidenceType: EvidenceType,
      evidenceId: String
  ): Either[DomainViolation, String] =
    evidenceType match {
      case EvidenceType.GraphPath    => nonTextKind(evidenceId, "graph-path")
      case EvidenceType.Metric       => nonTextKind(evidenceId, "metric")
      case EvidenceType.CoauthorEdge => nonTextKind(evidenceId, "edge")
      case _                         => StableIds.parseChunkOrProfileId(evidenceId)
    }

  private def nonTextKind(evidenceId: String, kind: String): Either[DomainViolation, String] =
    StableIds.parseNonTextEvidenceId(evidenceId).flatMap { id =>
      if (id.startsWith(s"evidence:$kind:")) Right(id)
      else
        Left(
          DomainViolation(
            ViolationCode.InconsistentRecord,
            s"evidence id must use kind $kind"
          )
        )
    }

  private def validateProvenance(value: Provenance, recordSchema: String, acc: Acc): Unit = {
    if (!SchemaVersions.supportedDomain.contains(value.schemaVersion))
      acc.add(
        ViolationCode.UnsupportedSchemaVersion,
        s"unsupported schema version: ${value.schemaVersion}"
      )
    if (value.schemaVersion != recordSchema)
      acc.add(ViolationCode.UnsupportedSchemaVersion, "record schemaVersion must match provenance")
    if (value.sourceRecordId.trim.isEmpty || value.datasetSnapshot.trim.isEmpty)
      acc.add(ViolationCode.MissingProvenance, "provenance source record and snapshot are required")
    parse(StableIds.parseRunId(value.runId), acc)
    value.retrievalDate.foreach { date =>
      try LocalDate.parse(date)
      catch {
        case _: DateTimeParseException =>
          acc.add(ViolationCode.MissingProvenance, s"retrievalDate is not an ISO date: $date")
      }
    }
    value.uncertaintyNotes.foreach { note =>
      if (note.trim.isEmpty)
        acc.add(ViolationCode.MissingProvenance, "uncertainty notes must be non-blank when present")
    }
  }

  private def requireNodeId(nodeClass: GraphNodeClass, nodeId: String, acc: Acc): Unit = {
    val parsed = nodeClass match {
      case GraphNodeClass.Researcher    => StableIds.parseResearcherId(nodeId)
      case GraphNodeClass.AuthorMention => StableIds.parseMentionId(nodeId)
      case GraphNodeClass.Work          => StableIds.parseWorkId(nodeId)
      case GraphNodeClass.TextChunk     => StableIds.parseChunkOrProfileId(nodeId)
      case GraphNodeClass.DatasetSnapshot =>
        if (nodeId.matches("snapshot:(dblp|openalex|orcid|crossref):[A-Za-z0-9._:-]+"))
          Right(nodeId)
        else
          Left(DomainViolation(ViolationCode.MalformedId, s"malformed snapshot id: $nodeId"))
      case GraphNodeClass.Venue       => StableIds.parseVenueId(nodeId)
      case GraphNodeClass.Institution => StableIds.parseInstitutionId(nodeId)
      case GraphNodeClass.Topic       => StableIds.parseTopicId(nodeId)
    }
    parse(parsed, acc)
  }

  private def requireSchema(schemaVersion: String, acc: Acc): Unit =
    if (!SchemaVersions.supportedDomain.contains(schemaVersion))
      acc.add(
        ViolationCode.UnsupportedSchemaVersion,
        s"unsupported schema version: $schemaVersion"
      )

  private def requireWindow(startYear: Int, endYear: Int, acc: Acc): Unit = {
    requireYear(startYear, "windowStartYear", acc)
    requireYear(endYear, "windowEndYear", acc)
    if (startYear > endYear)
      acc.add(
        ViolationCode.ReversedTimeWindow,
        s"window start $startYear exceeds end $endYear"
      )
  }

  private def requireYear(year: Int, field: String, acc: Acc): Unit =
    if (year < 1 || year > 9999)
      acc.add(ViolationCode.InconsistentRecord, s"$field is outside 1..9999")

  private def requireConfidence(value: Double, field: String, acc: Acc): Unit =
    if (!java.lang.Double.isFinite(value) || value < 0.0 || value > 1.0)
      acc.add(ViolationCode.InvalidConfidence, s"$field must be finite and in [0, 1]")

  private def requireFinite(value: Double, field: String, acc: Acc): Unit =
    if (!java.lang.Double.isFinite(value))
      acc.add(ViolationCode.InvalidConfidence, s"$field must be finite")

  private def requireFiniteNonNegative(value: Double, field: String, acc: Acc): Unit = {
    requireFinite(value, field, acc)
    if (value < 0.0) acc.add(ViolationCode.InconsistentRecord, s"$field must be >= 0")
  }

  private def requireNonNegative(value: Long, field: String, acc: Acc): Unit =
    if (value < 0) acc.add(ViolationCode.InconsistentRecord, s"$field must be >= 0")

  private def requireNonBlank(value: String, field: String, acc: Acc): Unit =
    if (value.trim.isEmpty)
      acc.add(ViolationCode.MissingProvenance, s"$field must be non-blank")

  private def parse(result: Either[DomainViolation, ?], acc: Acc): Unit =
    result.left.foreach(acc.add)

  private def done[T](acc: Acc, value: T): Either[Vector[DomainViolation], T] = {
    val errors = acc.result()
    if (errors.isEmpty) Right(value) else Left(errors)
  }

  private final class Acc {
    private val buffer = ArrayBuffer.empty[DomainViolation]
    def add(code: ViolationCode, message: String): Unit =
      buffer += DomainViolation(code, message)
    def add(violation: DomainViolation): Unit = buffer += violation
    def result(): Vector[DomainViolation] = buffer.toVector
  }
}
