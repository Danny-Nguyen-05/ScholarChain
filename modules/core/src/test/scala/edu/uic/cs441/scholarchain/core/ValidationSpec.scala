package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite

class ValidationSpec extends AnyFunSuite {
  test("sample fixtures validate") {
    assert(DomainValidation.check(Fixtures.work).isRight)
    assert(DomainValidation.check(Fixtures.orcidResearcher).isRight)
    assert(DomainValidation.check(Fixtures.unresolvedMatch).isRight)
    assert(DomainValidation.check(Fixtures.conflictMatch).isRight)
    assert(DomainValidation.check(Fixtures.authorship, Fixtures.work).isRight)
    assert(DomainValidation.check(Fixtures.team, Fixtures.work).isRight)
    assert(DomainValidation.check(Fixtures.pair, Fixtures.work).isRight)
    assert(DomainValidation.check(Fixtures.edge).isRight)
    assert(DomainValidation.check(Fixtures.metrics).isRight)
    assert(DomainValidation.check(Fixtures.venue).isRight)
    assert(DomainValidation.check(Fixtures.openAlexInstitution).isRight)
    assert(DomainValidation.check(Fixtures.orcidEmployment).isRight)
    assert(DomainValidation.check(Fixtures.topic).isRight)
    assert(DomainValidation.check(Fixtures.workNode).isRight)
    assert(DomainValidation.check(Fixtures.graphEdge).isRight)
    assert(DomainValidation.check(Fixtures.evidence).isRight)
    assert(DomainValidation.check(Fixtures.graphPathEvidence).isRight)
    assert(DomainValidation.check(Fixtures.metricEvidence).isRight)
    assert(DomainValidation.check(Fixtures.edgeEvidence).isRight)
    assert(DomainValidation.check(Fixtures.bundle).isRight)
    assert(DomainValidation.check(Fixtures.plan).isRight)
    assert(DomainValidation.check(Fixtures.claim).isRight)
    assert(DomainValidation.check(Fixtures.graphPathClaim).isRight)
    assert(DomainValidation.check(Fixtures.response).isRight)
    assert(DomainValidation.check(Fixtures.manifest).isRight)
  }

  test("source years for the shared DOI stay on their own records") {
    val dblp = Fixtures.sourceWork(SourceType.Dblp, Fixtures.dblpKey, 2011, "inproceedings")
    val openAlex = Fixtures.sourceWork(
      SourceType.OpenAlex,
      "https://openalex.org/W4254447616",
      2012,
      "book-chapter"
    )
    val crossref = Fixtures.sourceWork(SourceType.Crossref, Fixtures.doi, 2013, "book-chapter")
    assert(DomainValidation.check(dblp).isRight)
    assert(DomainValidation.check(openAlex).isRight)
    assert(DomainValidation.check(crossref).isRight)
    assert(dblp.workId == openAlex.workId && openAlex.workId == crossref.workId)
    assert(dblp.year.contains(2011) && openAlex.year.contains(2012) && crossref.year.contains(2013))
  }

  test("missing provenance and blank provenance fields are rejected") {
    val json = """{"schemaVersion":"scholarchain.domain.v1","source":"DBLP"}"""
    val parsed = CoreJson.parseAndValidate(json)(DomainValidation.checkProvenance)
    assert(parsed.left.exists(_.exists(_.code == ViolationCode.MalformedInput)))
    val blank = Fixtures.dblpProvenance.copy(sourceRecordId = " ")
    assert(
      DomainValidation
        .checkProvenance(blank)
        .left
        .exists(_.exists(_.code == ViolationCode.MissingProvenance))
    )
  }

  test("unsupported schema versions are rejected") {
    val stale = Fixtures.venue.copy(
      schemaVersion = "scholarchain.domain.v0",
      provenance = Fixtures.dblpProvenance.copy(schemaVersion = "scholarchain.domain.v0")
    )
    val result = DomainValidation.check(stale)
    assert(result.left.exists(_.exists(_.code == ViolationCode.UnsupportedSchemaVersion)))
  }

  test("confidence outside 0 to 1 is rejected and endpoints of the range are accepted") {
    val high = Fixtures.unresolvedMatch.copy(confidence = 1.2)
    val low = Fixtures.unresolvedMatch.copy(confidence = -0.01)
    val nan = Fixtures.unresolvedMatch.copy(confidence = Double.NaN)
    assert(
      DomainValidation.check(high).left.exists(_.exists(_.code == ViolationCode.InvalidConfidence))
    )
    assert(
      DomainValidation.check(low).left.exists(_.exists(_.code == ViolationCode.InvalidConfidence))
    )
    assert(
      DomainValidation.check(nan).left.exists(_.exists(_.code == ViolationCode.InvalidConfidence))
    )
    assert(DomainValidation.check(Fixtures.unresolvedMatch.copy(confidence = 0.0)).isRight)
    assert(DomainValidation.check(Fixtures.unresolvedMatch.copy(confidence = 1.0)).isRight)
  }

  test("malformed stable ids are rejected") {
    assert(StableIds.parseWorkId("work:doi:not-a-doi").isLeft)
    assert(StableIds.parseResearcherId("researcher:openalex:A5101955953").isLeft)
    assert(StableIds.parseResearcherId("Claiborne Rice").isLeft)
    assert(StableIds.parseCoauthorEdgeId("coauthor-edge:abcd").isLeft)
    assert(StableIds.parseGraphEdgeId("graph-edge:123").isLeft)
    assert(StableIds.parseChunkOrProfileId("chunk:zz").isLeft)
    val badWork = Fixtures.work.copy(workId = "work:doi:not-a-doi", doi = None)
    assert(
      DomainValidation.check(badWork).left.exists(_.exists(_.code == ViolationCode.MalformedId))
    )
  }

  test("reversed undirected pairs and reversed windows are rejected") {
    val swapped = Fixtures.edge.copy(
      researcherA = Fixtures.riceProvisionalId,
      researcherB = Fixtures.berkeleyResearcherId
    )
    assert(
      DomainValidation
        .check(swapped)
        .left
        .exists(_.exists(_.code == ViolationCode.InvalidPairOrder))
    )
    val reversedGraph = Fixtures.graphEdge.copy(
      fromId = Fixtures.riceProvisionalId,
      toId = Fixtures.berkeleyResearcherId
    )
    assert(
      DomainValidation
        .check(reversedGraph)
        .left
        .exists(_.exists(_.code == ViolationCode.InvalidPairOrder))
    )
    val reversedWindow = Fixtures.metrics.copy(windowStartYear = 2012, windowEndYear = 2011)
    assert(
      DomainValidation
        .check(reversedWindow)
        .left
        .exists(_.exists(_.code == ViolationCode.ReversedTimeWindow))
    )
    val reversedPlan = Fixtures.plan.copy(window = YearWindow(2013, 2011))
    assert(
      DomainValidation
        .check(reversedPlan)
        .left
        .exists(_.exists(_.code == ViolationCode.ReversedTimeWindow))
    )
  }

  test("a name or an observed identifier is not itself a match decision") {
    val promoted = Fixtures.berkeleyMention.copy(
      identityStatus = MentionIdentityStatus.ResolvedToResearcher,
      resolvedResearcherId = Some(Fixtures.berkeleyResearcherId)
    )
    assert(DomainValidation.check(promoted).isRight)
    val nameOnlyWithOrcid = Fixtures.berkeleyMention.copy(observedOrcid = Some(Fixtures.riceOrcid))
    assert(
      DomainValidation
        .check(nameOnlyWithOrcid)
        .left
        .exists(_.exists(_.code == ViolationCode.UnconfirmedIdentity))
    )
    val observedButResolved = Fixtures.riceMention.copy(
      identityStatus = MentionIdentityStatus.ExternalIdentifierObserved,
      resolvedResearcherId = Some(Fixtures.riceOrcidResearcherId)
    )
    assert(
      DomainValidation
        .check(observedButResolved)
        .left
        .exists(_.exists(_.code == ViolationCode.UnconfirmedIdentity))
    )
  }

  test("CONFLICT is a match outcome and does not replace UNRESOLVED") {
    assert(Fixtures.unresolvedMatch.decision == MatchOutcome.Unresolved)
    assert(Fixtures.conflictMatch.decision == MatchOutcome.Conflict)
    assert(Fixtures.unresolvedMatch.decision != Fixtures.conflictMatch.decision)
    val parsed = CoreJson.parse[MatchDecision](CoreJson.compact(Fixtures.conflictMatch))
    assert(parsed.exists(_.decision == MatchOutcome.Conflict))
    val unresolved = CoreJson.parse[MatchDecision](CoreJson.compact(Fixtures.unresolvedMatch))
    assert(unresolved.exists(_.decision == MatchOutcome.Unresolved))
  }

  test("coauthor mentions from different works are rejected") {
    val otherWorkMention = StableIds.mentionId(SourceType.Dblp, "series/sapere/NasutoB13", 1)
    assert(Fixtures.riceMentionId.compareTo(otherWorkMention) < 0)
    val crossed = Fixtures.pair.copy(
      leftMentionId = Fixtures.riceMentionId,
      rightMentionId = otherWorkMention,
      leftOrdinal = 2,
      rightOrdinal = 1
    )
    val result = DomainValidation.check(crossed, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("same work")
        )
      )
    )
  }

  test("coauthor ordinals that disagree with the mention ids are rejected") {
    val mismatched = Fixtures.pair.copy(leftOrdinal = 2, rightOrdinal = 3)
    val result = DomainValidation.check(mismatched, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("Ordinal")
        )
      )
    )
  }

  test("coauthor mentions from another work than the pair workId and provenance are rejected") {
    val copied = Fixtures.pair.copy(
      leftMentionId = StableIds.mentionId(SourceType.Dblp, "series/sapere/NasutoB13", 1),
      rightMentionId = StableIds.mentionId(SourceType.Dblp, "series/sapere/NasutoB13", 2)
    )
    assert(copied.leftOrdinal == 1 && copied.rightOrdinal == 2)
    assert(copied.workId == Fixtures.workId)
    assert(copied.provenance.sourceRecordId == Fixtures.dblpKey)
    val result = DomainValidation.check(copied, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("source record")
        )
      )
    )
  }

  test("a coauthor pair cannot name a DOI work id unrelated to its source record") {
    val unrelatedDoi = "10.5555/unrelated"
    val mismatched = Fixtures.pair.copy(workId = s"work:doi:$unrelatedDoi")
    assert(mismatched.provenance.sourceRecordId == Fixtures.dblpKey)
    assert(mismatched.provenance.sourceUri.exists(_.contains(Fixtures.doi)))
    val result = DomainValidation.check(mismatched, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("workId")
        )
      )
    )
  }

  test(
    "a coauthor pair cannot retarget workId and provenance sourceUri while keeping the record doi"
  ) {
    val unrelatedDoi = "10.5555/unrelated"
    val mismatched = Fixtures.pair.copy(
      workId = s"work:doi:$unrelatedDoi",
      provenance = Fixtures.pair.provenance.copy(
        sourceUri = Some(s"https://doi.org/$unrelatedDoi")
      )
    )
    assert(mismatched.doi.contains(Fixtures.doi))
    assert(mismatched.leftMentionId == Fixtures.berkeleyMentionId)
    val result = DomainValidation.check(mismatched, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("workId")
        )
      )
    )
  }

  test("a coauthor pair with a DOI work id and no provenance sourceUri validates") {
    val pair = Fixtures.pair.copy(
      provenance = Fixtures.pair.provenance.copy(sourceUri = None)
    )
    assert(DomainValidation.check(pair, Fixtures.work).isRight)
  }

  test(
    "a coauthor pair cannot self-authorize a DOI work id without provenance sourceUri"
  ) {
    val unrelatedDoi = "10.5555/unrelated"
    val mismatched = Fixtures.pair.copy(
      workId = s"work:doi:$unrelatedDoi",
      doi = Some(unrelatedDoi),
      provenance = Fixtures.pair.provenance.copy(sourceUri = None)
    )
    assert(mismatched.provenance.sourceUri.isEmpty)
    val result = DomainValidation.check(mismatched, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("workId")
        )
      )
    )
  }

  test("Crossref coauthor pairs bind DOI work ids to the explicit Crossref WorkRecord") {
    val baseWork = Fixtures.sourceWork(SourceType.Crossref, Fixtures.doi, 2013, "book-chapter")
    val crossrefWork = baseWork.copy(authors =
      Fixtures.work.authors.map(m =>
        m.copy(
          source = SourceType.Crossref,
          sourceRecordId = Fixtures.doi,
          mentionId = StableIds.mentionId(SourceType.Crossref, Fixtures.doi, m.ordinal),
          provenance = baseWork.provenance
        )
      )
    )
    assert(DomainValidation.check(crossrefWork).isRight)
    val crossrefProvenance = crossrefWork.provenance
    val left = StableIds.mentionId(SourceType.Crossref, Fixtures.doi, 1)
    val right = StableIds.mentionId(SourceType.Crossref, Fixtures.doi, 2)
    val agreeing = Fixtures.pair.copy(
      year = Some(2013),
      leftMentionId = left,
      rightMentionId = right,
      provenance = crossrefProvenance.copy(sourceUri = None)
    )
    assert(DomainValidation.check(agreeing, crossrefWork).isRight)

    val unrelatedDoi = "10.5555/unrelated"
    val selfAuthorized = Fixtures.pair.copy(
      workId = s"work:doi:$unrelatedDoi",
      doi = Some(unrelatedDoi),
      provenance = crossrefProvenance.copy(sourceUri = None),
      leftMentionId = left,
      rightMentionId = right
    )
    val unauthorized = DomainValidation.check(selfAuthorized, crossrefWork)
    assert(
      unauthorized.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("workId")
        )
      )
    )

    val uriSpoofed = selfAuthorized.copy(
      provenance = crossrefProvenance.copy(sourceUri = Some(s"https://doi.org/$unrelatedDoi"))
    )
    val spoofResult = DomainValidation.check(uriSpoofed, crossrefWork)
    assert(
      spoofResult.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            (violation.message.contains("workId") || violation.message.contains("doi"))
        )
      )
    )
  }

  test("a coauthor pair with an arXiv work id validates without a provenance sourceUri") {
    val arxivId = "1706.03762"
    val arxivWorkId = StableIds.workIdFromArxiv(arxivId).toOption.get
    val arxivProvenance = Fixtures.dblpProvenance.copy(sourceUri = None)
    val work = Fixtures.work.copy(
      workId = arxivWorkId,
      doi = None,
      arxivId = Some(arxivId),
      externalUrl = None,
      provenance = arxivProvenance,
      authors = Fixtures.work.authors.map(_.copy(provenance = arxivProvenance))
    )
    assert(DomainValidation.check(work).isRight)
    val pair = Fixtures.pair.copy(
      workId = arxivWorkId,
      doi = None,
      arxivId = Some(arxivId),
      provenance = Fixtures.pair.provenance.copy(sourceUri = None)
    )
    assert(DomainValidation.check(pair, work).isRight)
  }

  test("authorship position must match the mention ordinal") {
    val mismatched = Fixtures.authorship.copy(position = 2, mentionId = Fixtures.berkeleyMentionId)
    val result = DomainValidation.check(mismatched, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("position")
        )
      )
    )
  }

  test("publication team mentions must belong to the team's work") {
    val nasuto = "series/sapere/NasutoB13"
    val crossed = Fixtures.team.copy(
      memberMentionIds = Vector(
        StableIds.mentionId(SourceType.Dblp, nasuto, 1),
        StableIds.mentionId(SourceType.Dblp, nasuto, 2)
      )
    )
    val result = DomainValidation.check(crossed, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            (violation.message.contains("workId") || violation.message.contains("provenance"))
        )
      )
    )
  }

  test(
    "coauthor provenance that names a different source record than workId and mentions is rejected"
  ) {
    val nasuto = "series/sapere/NasutoB13"
    val shifted = Fixtures.pair.copy(
      workId = StableIds.workIdFromDblpKey(nasuto).toOption.get,
      leftMentionId = StableIds.mentionId(SourceType.Dblp, nasuto, 1),
      rightMentionId = StableIds.mentionId(SourceType.Dblp, nasuto, 2)
    )
    assert(shifted.workId == s"work:dblp:$nasuto")
    assert(shifted.leftMentionId.contains(nasuto) && shifted.rightMentionId.contains(nasuto))
    assert(shifted.provenance.sourceRecordId == "series/sapere/BerkeleyR13")
    val result = DomainValidation.check(shifted, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("source record")
        )
      )
    )
  }

  test("an oversized mention ordinal is a validation failure") {
    val oversized = "mention:dblp:foo#2147483648"
    assert(StableIds.parseMentionId(oversized).isLeft)
    assert(StableIds.parseMentionIdParts(oversized).isLeft)
    val pair = Fixtures.pair.copy(
      leftMentionId = oversized,
      rightMentionId = "mention:dblp:foo#2147483649"
    )
    val result = DomainValidation.check(pair, Fixtures.work)
    assert(result.left.exists(_.exists(_.code == ViolationCode.MalformedId)))
  }

  test("a DBLP work record cannot carry another record's source-native work id") {
    val nasuto = "series/sapere/NasutoB13"
    val mislabeled = Fixtures.work.copy(
      workId = StableIds.workIdFromDblpKey(nasuto).toOption.get,
      doi = None,
      arxivId = None,
      externalUrl = None
    )
    assert(mislabeled.sourceRecordId == Fixtures.dblpKey)
    val result = DomainValidation.check(mislabeled)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("workId")
        )
      )
    )
  }

  test("a DBLP work with Crossref provenance is rejected") {
    val crossed = Fixtures.work.copy(
      provenance = Fixtures.dblpProvenance.copy(
        source = SourceType.Crossref,
        sourceRecordId = Fixtures.doi
      )
    )
    val result = DomainValidation.check(crossed)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("provenance source")
        )
      )
    )
    val mention = Fixtures.berkeleyMention.copy(
      provenance = Fixtures.berkeleyMention.provenance.copy(source = SourceType.Crossref)
    )
    assert(
      DomainValidation
        .check(mention)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
  }

  test("researcher metrics must agree with publication and coauthor counts") {
    val inflated = Fixtures.metrics.copy(
      averageCoauthorsPerPaper = 2.0,
      maximumCoauthorsOnOnePaper = 2
    )
    assert(
      DomainValidation
        .check(inflated)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
  }

  test("publication team duplicate mention ids are rejected") {
    val duplicated = Fixtures.team.copy(
      memberMentionIds = Vector(Fixtures.berkeleyMentionId, Fixtures.berkeleyMentionId)
    )
    val result = DomainValidation.check(duplicated, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("distinct")
        )
      )
    )
  }

  test("a coauthor pair cannot retarget both workId and doi away from the source observation") {
    val unrelatedDoi = "10.5555/unrelated"
    val retargeted = Fixtures.pair.copy(
      workId = s"work:doi:$unrelatedDoi",
      doi = Some(unrelatedDoi)
    )
    assert(retargeted.provenance.sourceUri.exists(_.contains(Fixtures.doi)))
    val result = DomainValidation.check(retargeted, Fixtures.work)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            (violation.message.contains("doi") || violation.message.contains("workId"))
        )
      )
    )
  }

  test("graph path evidence requires graphPath and a matching evidence id") {
    assert(
      DomainValidation
        .check(Fixtures.graphPathEvidence.copy(graphPath = None))
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
    val wrongPath = Fixtures.graphPathEvidence.copy(
      graphPath = Some(Vector(Fixtures.riceProvisionalId, Fixtures.berkeleyResearcherId))
    )
    assert(
      DomainValidation
        .check(wrongPath)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
    val missingMetric = Fixtures.metricEvidence.copy(metricLocator = None)
    assert(
      DomainValidation
        .check(missingMetric)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
    val missingEdge = Fixtures.edgeEvidence.copy(edgeLocatorId = None)
    assert(
      DomainValidation
        .check(missingEdge)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
  }

  test("graph edges reject malformed endpoints and property values") {
    val badEndpoints = Fixtures.graphEdge.copy(fromId = "abc", toId = "def")
    assert(
      DomainValidation
        .check(badEndpoints)
        .left
        .exists(_.exists(_.code == ViolationCode.MalformedId))
    )
    val badCount = Fixtures.graphEdge.copy(coauthorship =
      Some(Fixtures.graphEdge.coauthorship.get.copy(jointPublicationCount = 0))
    )
    assert(
      DomainValidation
        .check(badCount)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
  }

  test("Crossref sourceRecordId must match the work DOI") {
    val unrelatedDoi = "10.5555/unrelated"
    val crossref = Fixtures.sourceWork(SourceType.Crossref, unrelatedDoi, 2013, "book-chapter")
    val result = DomainValidation.check(crossref)
    assert(
      result.left.exists(
        _.exists(violation =>
          violation.code == ViolationCode.InconsistentRecord &&
            violation.message.contains("Crossref sourceRecordId")
        )
      )
    )
  }

  test("graph path, metric, and edge evidence ids are not text chunk ids") {
    val chunkPath = Fixtures.graphPathEvidence.copy(evidenceId = Fixtures.titleChunkId)
    assert(
      DomainValidation
        .check(chunkPath)
        .left
        .exists(_.exists(_.code == ViolationCode.MalformedId))
    )
    val metricOnPath = Fixtures.graphPathEvidence.copy(evidenceId = Fixtures.metricEvidenceId)
    assert(
      DomainValidation
        .check(metricOnPath)
        .left
        .exists(_.exists(_.code == ViolationCode.InconsistentRecord))
    )
    val textWithPathId = Fixtures.evidence.copy(evidenceId = Fixtures.graphPathEvidenceId)
    assert(DomainValidation.check(textWithPathId).isLeft)
    val claim = Fixtures.claim.copy(
      evidenceIds = Vector(Fixtures.metricEvidenceId, Fixtures.edgeEvidenceId)
    )
    assert(DomainValidation.check(claim).isRight)
  }
}
