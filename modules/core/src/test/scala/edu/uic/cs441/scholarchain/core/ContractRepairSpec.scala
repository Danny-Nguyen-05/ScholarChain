package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import scala.concurrent.{Await, ExecutionContext, Future}
import scala.concurrent.duration.*

/** Synthetic counterexamples exercise contract arithmetic and binding, not dataset claims. */
class ContractRepairSpec extends AnyFunSuite {
  private def context(works: WorkRecord*): WorkValidationContext = {
    val result = WorkValidationContext.create(works.toVector)
    assert(result.isRight, result.toString)
    result.toOption.get
  }

  private def observation(
      doi: Option[String] = Some(Fixtures.doi),
      arxiv: Option[String] = None,
      source: SourceType = SourceType.Dblp,
      recordId: String = Fixtures.dblpKey,
      snapshot: String = "synthetic-snapshot-1"
  ): WorkRecord = {
    val provenance = Fixtures.dblpProvenance.copy(
      source = source,
      sourceRecordId = recordId,
      datasetSnapshot = snapshot,
      sourceUri = None
    )
    Fixtures.work.copy(
      source = source,
      sourceRecordId = recordId,
      workId = StableIds.authoritativeWorkIdForRecord(source, recordId, doi, arxiv).toOption.get,
      doi = doi,
      arxivId = arxiv,
      externalUrl = None,
      provenance = provenance,
      authors = Fixtures.work.authors.map(m =>
        m.copy(
          source = source,
          sourceRecordId = recordId,
          mentionId = StableIds.mentionId(source, recordId, m.ordinal),
          provenance = provenance
        )
      )
    )
  }

  private def pair(work: WorkRecord): CoauthorPairCandidate = Fixtures.pair.copy(
    workId = work.workId,
    doi = work.doi,
    arxivId = work.arxivId,
    year = work.year,
    leftMentionId = work.authors(0).mentionId,
    rightMentionId = work.authors(1).mentionId,
    provenance = work.provenance
  )

  private def team(work: WorkRecord): PublicationTeam = Fixtures.team.copy(
    workId = work.workId,
    memberMentionIds = work.authors.map(_.mentionId),
    provenance = work.provenance
  )

  private def authorship(work: WorkRecord): AuthorshipRecord = Fixtures.authorship.copy(
    workId = work.workId,
    mentionId = work.authors(1).mentionId,
    provenance = work.provenance
  )

  private val multiMetrics = Fixtures.metrics.copy(
    publicationCount = 3,
    distinctCoauthorCount = 3,
    totalCoauthorOccurrences = 4,
    averageCoauthorsPerPaper = 4.0 / 3.0,
    maximumCoauthorsOnOnePaper = 3,
    weightedDegree = 4,
    uncertainty = "Synthetic canonical graph arithmetic fixture: paper coauthor counts are 0, 1, 3."
  )

  test("fresh independent contexts validate without global priming and ignore check order") {
    val work = observation()
    val first = context(work)
    val expected = DomainValidation.check(pair(work), first)
    assert(expected.isRight)
    assert(DomainValidation.check(team(work), first).isRight)
    assert(DomainValidation.check(authorship(work), first).isRight)
    val unrelated = observation(Some("10.5555/unrelated"), snapshot = "synthetic-snapshot-2")
    assert(DomainValidation.check(unrelated).isRight)
    assert(DomainValidation.check(pair(work), context(work)) == expected)
    assert(DomainValidation.check(pair(work), first) == expected)
  }

  test("full derived checks require context while structural checks make no binding claim") {
    assert(DomainValidation.checkStructure(Fixtures.pair).isRight)
    assert(DomainValidation.checkStructure(Fixtures.team).isRight)
    assert(DomainValidation.checkStructure(Fixtures.authorship).isRight)
    assert(
      DomainValidation
        .check(Fixtures.pair)
        .left
        .exists(_.exists(_.code == ViolationCode.MissingValidationContext))
    )
    assert(DomainValidation.check(Fixtures.team).isLeft)
    assert(DomainValidation.check(Fixtures.authorship).isLeft)
  }

  test("snapshot collisions cannot overwrite observations and missing snapshot cannot fall back") {
    val first = observation()
    val second = observation(Some("10.5555/second"), snapshot = "synthetic-snapshot-2")
    val scoped = context(first, second)
    assert(DomainValidation.check(pair(first), scoped).isRight)
    assert(DomainValidation.check(pair(second), scoped).isRight)
    assert(DomainValidation.check(pair(first).copy(provenance = second.provenance), scoped).isLeft)
    assert(DomainValidation.check(pair(first), context(second)).isLeft)
    val conflict = second.copy(
      provenance = second.provenance.copy(datasetSnapshot = first.provenance.datasetSnapshot),
      authors = second.authors.map(m =>
        m.copy(provenance = m.provenance.copy(datasetSnapshot = first.provenance.datasetSnapshot))
      )
    )
    val forward = WorkValidationContext.create(Vector(first, conflict))
    assert(forward.isLeft)
    assert(forward == WorkValidationContext.create(Vector(conflict, first)))
    assert(WorkValidationContext.create(Vector(first, first)).isRight)
  }

  test("parallel validation and context construction are deterministic") {
    given ExecutionContext = ExecutionContext.global
    val work = observation()
    val shared = context(work)
    val checks = Vector.tabulate(32) { i =>
      Future {
        val other = observation(Some(s"10.5555/parallel-$i"), snapshot = s"parallel-$i")
        assert(DomainValidation.check(pair(other), context(other)).isRight)
        DomainValidation.check(pair(work), shared)
      }
    }
    val results = Await.result(Future.sequence(checks), 10.seconds)
    assert(results.forall(_ == Right(pair(work))))
  }

  test("later derived runs may reuse source snapshots, but source and record must bind") {
    val work = observation()
    val later = work.provenance.copy(runId = "run:10112233-4455-4677-8899-aabbccddeeff")
    assert(DomainValidation.check(pair(work).copy(provenance = later), context(work)).isRight)
    assert(DomainValidation.check(team(work).copy(provenance = later), context(work)).isRight)
    assert(DomainValidation.check(authorship(work).copy(provenance = later), context(work)).isRight)
    assert(
      DomainValidation
        .check(
          pair(work).copy(provenance = later.copy(source = SourceType.Crossref)),
          context(work)
        )
        .isLeft
    )
    assert(
      DomainValidation
        .check(pair(work).copy(provenance = later.copy(sourceRecordId = "other")), context(work))
        .isLeft
    )
  }

  test("source observations sharing DOI do not merge author lists or years") {
    val dblp = observation()
    val crossref = observation(source = SourceType.Crossref, recordId = Fixtures.doi)
    val openalex =
      observation(source = SourceType.OpenAlex, recordId = "https://openalex.org/W4254447616")
    val scoped = context(dblp, crossref, openalex)
    Vector(dblp, crossref, openalex).foreach(w =>
      assert(DomainValidation.check(pair(w), scoped).isRight)
    )
    assert(DomainValidation.check(pair(dblp).copy(provenance = crossref.provenance), scoped).isLeft)
  }

  test("derived bibliography and own spoofed URI cannot authorize a different work") {
    val work = observation()
    val wrong = "work:doi:10.5555/unrelated"
    val spoofed = work.provenance.copy(sourceUri = Some("https://doi.org/10.5555/unrelated"))
    val scoped = context(work)
    assert(
      DomainValidation
        .check(
          pair(work).copy(workId = wrong, doi = Some("10.5555/unrelated"), provenance = spoofed),
          scoped
        )
        .isLeft
    )
    assert(
      DomainValidation.check(team(work).copy(workId = wrong, provenance = spoofed), scoped).isLeft
    )
    assert(
      DomainValidation
        .check(authorship(work).copy(workId = wrong, provenance = spoofed), scoped)
        .isLeft
    )
    assert(DomainValidation.check(team(work).copy(provenance = spoofed), scoped).isLeft)
    assert(DomainValidation.check(authorship(work).copy(provenance = spoofed), scoped).isLeft)
    assert(DomainValidation.check(pair(work).copy(doi = None), scoped).isLeft)
    assert(DomainValidation.check(pair(work).copy(year = Some(2012)), scoped).isLeft)
  }

  test("work links cannot register false DOI or arXiv bibliography") {
    val wrong =
      Fixtures.work.copy(workId = "work:doi:10.5555/unrelated", doi = Some("10.5555/unrelated"))
    assert(DomainValidation.check(wrong).isLeft)
    assert(WorkValidationContext.create(Vector(wrong)).isLeft)
    val work = observation(arxiv = Some("1706.03762"))
    assert(
      DomainValidation
        .check(work.copy(externalUrl = Some("https://arxiv.org/abs/1706.03762")))
        .isRight
    )
    assert(
      DomainValidation
        .check(work.copy(externalUrl = Some("https://arxiv.org/abs/1706.03763")))
        .isLeft
    )
    assert(
      DomainValidation
        .check(
          work.copy(provenance =
            work.provenance.copy(sourceUri = Some("https://doi.org/10.5555/false"))
          )
        )
        .isLeft
    )
    assert(DomainValidation.check(work.copy(arxivId = Some("invalid"))).isLeft)
  }

  test("direct resolver links validate while unrelated URLs carry no bibliographic authority") {
    val work = observation(None, Some("1706.03762"))
    assert(
      DomainValidation
        .check(work.copy(externalUrl = Some("https://arxiv.org/pdf/1706.03762.pdf")))
        .isRight
    )
    assert(
      DomainValidation
        .check(work.copy(externalUrl = Some("https://example.org/papers/1706.03763")))
        .isRight
    )
    Vector(
      "https://doi.org/not-a-doi",
      "https://arxiv.org/abs/bad",
      "https://arxiv.org/pdf/bad.pdf"
    ).foreach { uri =>
      assert(DomainValidation.check(work.copy(externalUrl = Some(uri))).isLeft)
    }
    val native = observation(None)
    assert(DomainValidation.check(pair(native), context(native)).isRight)
    assert(DomainValidation.check(team(work), context(work)).isRight)
    assert(DomainValidation.check(authorship(work), context(work)).isRight)
    assert(DomainValidation.check(pair(work), context(work)).isRight)
  }

  test("missing Crossref doi still binds from authoritative DOI sourceRecordId") {
    val work = observation(None, source = SourceType.Crossref, recordId = Fixtures.doi)
    assert(work.workId == Fixtures.workId)
    assert(DomainValidation.check(work).isRight)
    assert(DomainValidation.check(pair(work), context(work)).isRight)
    assert(DomainValidation.check(work.copy(workId = "work:dblp:any")).isLeft)
    assert(DomainValidation.check(work.copy(sourceRecordId = "not-a-doi")).isLeft)
  }

  test("contextual membership and complete ordered teams match the source authors") {
    val work = observation()
    val scoped = context(work)
    assert(
      DomainValidation
        .check(
          authorship(work).copy(
            mentionId = StableIds.mentionId(work.source, work.sourceRecordId, 3),
            position = 3
          ),
          scoped
        )
        .isLeft
    )
    assert(DomainValidation.check(authorship(work).copy(position = 1), scoped).isLeft)
    assert(
      DomainValidation
        .check(
          team(work).copy(memberMentionIds = work.authors.take(1).map(_.mentionId), teamSize = 1),
          scoped
        )
        .isLeft
    )
    assert(
      DomainValidation
        .check(team(work).copy(memberMentionIds = work.authors.reverse.map(_.mentionId)), scoped)
        .isLeft
    )
    val nestedMismatch = work.copy(authors =
      work.authors.map(m => m.copy(provenance = m.provenance.copy(datasetSnapshot = "wrong")))
    )
    assert(DomainValidation.check(nestedMismatch).isLeft)
  }

  test("positive multiple-paper metrics include solo papers and tolerate floating rounding") {
    assert(DomainValidation.check(multiMetrics).isRight)
    assert(
      DomainValidation
        .check(multiMetrics.copy(averageCoauthorsPerPaper = Math.nextUp(4.0 / 3)))
        .isRight
    )
    assert(DomainValidation.check(multiMetrics.copy(averageCoauthorsPerPaper = 1)).isLeft)
    assert(DomainValidation.check(multiMetrics.copy(weightedDegree = 0)).isLeft)
    assert(DomainValidation.check(multiMetrics.copy(averageCoauthorsPerPaper = Double.NaN)).isLeft)
    assert(
      DomainValidation.check(multiMetrics.copy(weightedDegree = Double.PositiveInfinity)).isLeft
    )
  }

  test("zero publications and solo publications have consistent zero collaboration values") {
    val zero = multiMetrics.copy(
      publicationCount = 0,
      distinctCoauthorCount = 0,
      totalCoauthorOccurrences = 0,
      averageCoauthorsPerPaper = 0,
      maximumCoauthorsOnOnePaper = 0,
      weightedDegree = 0
    )
    assert(DomainValidation.check(zero).isRight)
    assert(DomainValidation.check(zero.copy(publicationCount = 3)).isRight)
    Vector(
      zero.copy(distinctCoauthorCount = 1),
      zero.copy(totalCoauthorOccurrences = 1),
      zero.copy(maximumCoauthorsOnOnePaper = 1),
      zero.copy(averageCoauthorsPerPaper = 1),
      zero.copy(weightedDegree = 1)
    ).foreach(m => assert(DomainValidation.check(m).isLeft))
    assert(DomainValidation.check(multiMetrics.copy(publicationCount = 0)).isLeft)
  }

  test("metrics maximum and count bounds use overflow-safe arithmetic") {
    Vector(
      multiMetrics.copy(maximumCoauthorsOnOnePaper = 1),
      multiMetrics.copy(maximumCoauthorsOnOnePaper = 5),
      multiMetrics.copy(distinctCoauthorCount = 2),
      multiMetrics.copy(distinctCoauthorCount = 5),
      multiMetrics.copy(maximumCoauthorsOnOnePaper = 0),
      multiMetrics.copy(coreness = Some(4))
    ).foreach(m => assert(DomainValidation.check(m).isLeft))
    val large = multiMetrics.copy(
      publicationCount = Long.MaxValue,
      distinctCoauthorCount = 2,
      totalCoauthorOccurrences = Long.MaxValue,
      averageCoauthorsPerPaper = 1,
      maximumCoauthorsOnOnePaper = 2,
      weightedDegree = Long.MaxValue.toDouble
    )
    assert(DomainValidation.check(large).isRight)
  }

  test("typed multiple-work coauthorship is valid and malformed or conflicting properties fail") {
    val values =
      CoauthorshipProperties(2, 2011, 2012, Vector(Fixtures.workId, "work:doi:10.5555/second"))
    val edge = Fixtures.graphEdge.copy(coauthorship = Some(values))
    assert(DomainValidation.check(edge).isRight)
    assert(
      CoreJson
        .parseAndValidate[GraphEdge](CoreJson.compact(edge))(DomainValidation.check)
        .contains(edge)
    )
    Vector(
      values.copy(jointPublicationCount = 0),
      values.copy(firstCollaborationYear = 2013),
      values.copy(firstCollaborationYear = 0),
      values.copy(representativeWorkIds = Vector.empty),
      values.copy(representativeWorkIds = Vector(Fixtures.workId, Fixtures.workId)),
      values.copy(representativeWorkIds = Vector("garbage")),
      values.copy(jointPublicationCount = 1)
    ).foreach(v => assert(DomainValidation.check(edge.copy(coauthorship = Some(v))).isLeft))
    assert(
      DomainValidation
        .check(edge.copy(properties = Vector(NamedText("x", "1"), NamedText("x", "2"))))
        .isLeft
    )
    assert(
      DomainValidation
        .check(edge.copy(properties = Vector(NamedText("jointPublicationCount", "999"))))
        .isLeft
    )
    assert(DomainValidation.check(edge.copy(coauthorship = None)).isLeft)
    val wrongJson = CoreJson
      .compact(edge)
      .replace("\"representativeWorkIds\":[", "\"representativeWorkIds\":\"bad\",\"unused\":[")
    assert(CoreJson.parseAndValidate[GraphEdge](wrongJson)(DomainValidation.check).isLeft)
    val badCountJson = CoreJson
      .compact(edge)
      .replace("\"jointPublicationCount\":2", "\"jointPublicationCount\":\"bad\"")
    assert(CoreJson.parseAndValidate[GraphEdge](badCountJson)(DomainValidation.check).isLeft)
  }

  test("ORCID employment graph evidence binds actual source record and snapshot") {
    val id = "/0000-0002-4414-6920/employment/19198978"
    val evidence = GraphSourceEvidence.SourceRecord(SourceType.Orcid, id, "unknown")
    val provenance =
      Fixtures.orcidEmployment.provenance.copy(sourceRecordId = id, datasetSnapshot = "unknown")
    val edgeId = StableIds
      .graphEdgeId(
        GraphEdgeType.AffiliatedWith,
        Fixtures.riceOrcidResearcherId,
        Fixtures.ringgoldInstitutionId,
        Fixtures.graphPolicy,
        evidence
      )
      .toOption
      .get
    val edge = Fixtures.graphEdge.copy(
      edgeId = edgeId,
      edgeType = GraphEdgeType.AffiliatedWith,
      fromId = Fixtures.riceOrcidResearcherId,
      toId = Fixtures.ringgoldInstitutionId,
      sourceEvidence = evidence,
      coauthorship = None,
      provenance = provenance
    )
    assert(DomainValidation.check(edge).isRight)
    assert(
      CoreJson
        .parseAndValidate[GraphEdge](CoreJson.compact(edge))(DomainValidation.check)
        .contains(edge)
    )
    assert(
      DomainValidation
        .check(edge.copy(provenance = provenance.copy(datasetSnapshot = "wrong")))
        .isLeft
    )
    assert(
      DomainValidation
        .check(
          edge.copy(sourceEvidence =
            GraphSourceEvidence.SourceRecord(SourceType.Orcid, "arbitrary", "unknown")
          )
        )
        .isLeft
    )
    val changed = GraphSourceEvidence.SourceRecord(SourceType.Orcid, id, "other-snapshot")
    assert(
      StableIds
        .graphEdgeId(edge.edgeType, edge.fromId, edge.toId, edge.policyVersion, changed)
        .toOption
        .get != edgeId
    )
    val pointer = StableIds.graphEvidencePointer(evidence).toOption.get
    assert(
      edgeId == "graph-edge:" + StableIds.sha256Hex(
        Seq(edge.edgeType.wire, edge.fromId, edge.toId, edge.policyVersion, pointer).mkString("\n")
      )
    )
    assert(
      StableIds
        .graphEdgeId(edge.edgeType, edge.fromId, edge.toId, edge.policyVersion, "arbitrary")
        .isLeft
    )
  }

  test("graph source references support other portfolio records and reject malformed keys") {
    Vector(
      (SourceType.Dblp, Fixtures.dblpKey),
      (SourceType.Crossref, Fixtures.doi),
      (SourceType.OpenAlex, "https://openalex.org/I79516672"),
      (SourceType.Orcid, Fixtures.riceOrcid)
    ).foreach { case (source, id) =>
      assert(
        StableIds
          .graphEvidencePointer(GraphSourceEvidence.SourceRecord(source, id, "snapshot-1"))
          .isRight
      )
    }
    Vector(
      (SourceType.Crossref, "bad"),
      (SourceType.OpenAlex, "Ibad"),
      (SourceType.Orcid, "/0000-0002-4414-6920/employment/abc"),
      (SourceType.ScholarChain, "arbitrary")
    ).foreach { case (source, id) =>
      assert(
        StableIds
          .graphEvidencePointer(GraphSourceEvidence.SourceRecord(source, id, "snapshot-1"))
          .isLeft
      )
    }
  }

  test(
    "shared strict graph and concrete reference IDs reject bare prefixes and malformed namespaces"
  ) {
    val valid = Vector(
      (GraphNodeClass.Venue, Fixtures.venueId),
      (GraphNodeClass.Venue, "venue:openalex:S123"),
      (GraphNodeClass.Institution, Fixtures.ringgoldInstitutionId),
      (GraphNodeClass.Institution, Fixtures.openAlexInstitutionId),
      (GraphNodeClass.Topic, Fixtures.topicId)
    )
    valid.foreach { case (kind, id) =>
      assert(DomainValidation.check(Fixtures.workNode.copy(nodeClass = kind, nodeId = id)).isRight)
    }
    val bad = Vector(
      (GraphNodeClass.Venue, "venue:"),
      (GraphNodeClass.Venue, "venue:dblp-booktitle:"),
      (GraphNodeClass.Institution, "institution:"),
      (GraphNodeClass.Institution, "institution:ror:bad"),
      (GraphNodeClass.Institution, "institution:ringgold:abc"),
      (GraphNodeClass.Topic, "topic:"),
      (GraphNodeClass.Topic, "topic:openalex:bad"),
      (GraphNodeClass.Topic, "topic:unknown:T1")
    )
    bad.foreach { case (kind, id) =>
      assert(DomainValidation.check(Fixtures.workNode.copy(nodeClass = kind, nodeId = id)).isLeft)
    }
    assert(DomainValidation.check(Fixtures.venue.copy(venueId = "venue:dblp-booktitle:")).isLeft)
    assert(
      DomainValidation
        .check(Fixtures.openAlexInstitution.copy(institutionId = "institution:openalex:Ibad"))
        .isLeft
    )
    assert(DomainValidation.check(Fixtures.topic.copy(topicId = "topic:openalex:")).isLeft)
  }

  test(
    "AUTHORED accepts canonical researchers and unresolved mentions and rejects malformed targets"
  ) {
    Vector(Fixtures.berkeleyResearcherId, Fixtures.berkeleyMentionId).foreach { author =>
      val id = StableIds
        .graphEdgeId(
          GraphEdgeType.Authored,
          author,
          Fixtures.workId,
          Fixtures.graphPolicy,
          Fixtures.workId
        )
        .toOption
        .get
      val edge = Fixtures.graphEdge.copy(
        edgeId = id,
        edgeType = GraphEdgeType.Authored,
        fromId = author,
        toId = Fixtures.workId,
        coauthorship = None
      )
      assert(DomainValidation.check(edge).isRight)
      assert(DomainValidation.check(edge.copy(toId = "work:doi:bad")).isLeft)
    }
    Vector((GraphEdgeType.PublishedIn, "venue:"), (GraphEdgeType.HasTopic, "topic:")).foreach {
      case (kind, target) =>
        assert(
          DomainValidation
            .check(
              Fixtures.graphEdge
                .copy(edgeType = kind, fromId = Fixtures.workId, toId = target, coauthorship = None)
            )
            .isLeft
        )
    }
  }
  test("native OpenAlex and simultaneous DOI/arXiv source observations bind all derived records") {
    val native =
      observation(None, source = SourceType.OpenAlex, recordId = "https://openalex.org/W4254447616")
    val both = observation(arxiv = Some("1706.03762"))
    val crossref = observation(None, Some("1706.03762"), SourceType.Crossref, Fixtures.doi)
    Vector(native, both, crossref).foreach { work =>
      val scoped = context(work)
      assert(DomainValidation.check(pair(work), scoped).isRight)
      assert(DomainValidation.check(team(work), scoped).isRight)
      assert(DomainValidation.check(authorship(work), scoped).isRight)
    }
    assert(both.workId == Fixtures.workId)
    assert(crossref.workId == Fixtures.workId)
  }

  test("context input failures and lineage metadata collisions return deterministic errors") {
    val work = observation()
    val laterAcquisition = work.copy(provenance =
      work.provenance.copy(runId = "run:10112233-4455-4677-8899-aabbccddeeff")
    )
    assert(DomainValidation.check(pair(work), context(laterAcquisition)).isRight)
    val collision = WorkValidationContext.create(Vector(work, laterAcquisition))
    assert(collision.isLeft)
    assert(collision == WorkValidationContext.create(Vector(laterAcquisition, work)))
    val malformed = work.copy(arxivId = Some("bad"))
    assert(WorkValidationContext.create(Vector(malformed)).isLeft)
    assert(DomainValidation.check(pair(work), malformed).isLeft)
    assert(DomainValidation.check(pair(work), context()).isLeft)
    val parsed =
      CoreJson.parseAndValidate[CoauthorPairCandidate](CoreJson.compact(pair(work)))(value =>
        DomainValidation.check(value, context(work))
      )
    assert(parsed.contains(pair(work)))
  }

  test("reference record fields and mention source namespaces share strict parsing") {
    assert(DomainValidation.check(Fixtures.topic.copy(topicId = "topic:openalex:T123")).isLeft)
    assert(DomainValidation.check(Fixtures.orcidEmployment.copy(ringgold = Some("123"))).isLeft)
    Vector(
      "venue:unknown:label",
      "institution:ror:abcdefghi",
      "institution:ror:01x8rcl03",
      "institution:openalex:I0",
      "topic:openalex:T0"
    ).foreach { id =>
      val kind =
        if (id.startsWith("venue:")) GraphNodeClass.Venue
        else if (id.startsWith("institution:")) GraphNodeClass.Institution
        else GraphNodeClass.Topic
      assert(DomainValidation.check(Fixtures.workNode.copy(nodeClass = kind, nodeId = id)).isLeft)
    }
    Vector("mention:crossref:arbitrary#1", "mention:openalex:Wbad#1", "mention:orcid:bad#1")
      .foreach { id =>
        assert(StableIds.parseMentionId(id).isLeft)
        assert(
          DomainValidation
            .check(Fixtures.workNode.copy(nodeClass = GraphNodeClass.AuthorMention, nodeId = id))
            .isLeft
        )
      }
  }

  test("duplicate and malformed wire property arrays fail validation without exceptions") {
    val duplicate =
      Fixtures.graphEdge.copy(properties = Vector(NamedText("note", "a"), NamedText("note", "b")))
    assert(
      CoreJson
        .parseAndValidate[GraphEdge](CoreJson.compact(duplicate))(DomainValidation.check)
        .isLeft
    )
    val values = Fixtures.graphEdge.coauthorship.get.copy(
      representativeWorkIds = Vector(Fixtures.workId, Fixtures.workId),
      jointPublicationCount = 2
    )
    assert(
      CoreJson
        .parseAndValidate[GraphEdge](
          CoreJson.compact(Fixtures.graphEdge.copy(coauthorship = Some(values)))
        )(DomainValidation.check)
        .isLeft
    )
    val badSource =
      CoreJson.compact(Fixtures.graphEdge).replace("\"$type\":\"Work\"", "\"$type\":\"Arbitrary\"")
    assert(CoreJson.parseAndValidate[GraphEdge](badSource)(DomainValidation.check).isLeft)
  }

  test("multiple solo papers require exactly zero average and weighted degree") {
    val solo = Fixtures.metrics.copy(
      publicationCount = 3,
      distinctCoauthorCount = 0,
      totalCoauthorOccurrences = 0,
      maximumCoauthorsOnOnePaper = 0,
      averageCoauthorsPerPaper = 0.0,
      weightedDegree = 0.0
    )
    assert(DomainValidation.check(solo).isRight)
    Vector(
      solo.copy(averageCoauthorsPerPaper = 1e-13),
      solo.copy(weightedDegree = 1e-13),
      solo.copy(averageCoauthorsPerPaper = 1e-13, weightedDegree = 1e-13),
      solo.copy(averageCoauthorsPerPaper = Double.MinPositiveValue),
      solo.copy(weightedDegree = Double.MinPositiveValue)
    ).foreach(value => assert(DomainValidation.check(value).isLeft))
    assert(
      DomainValidation
        .check(multiMetrics.copy(averageCoauthorsPerPaper = Math.nextUp(4.0 / 3.0)))
        .isRight
    )
  }

  private def withWorkEvidence(edge: GraphEdge, workId: String): GraphEdge = {
    val evidence = GraphSourceEvidence.Work(workId)
    edge.copy(
      sourceEvidence = evidence,
      edgeId = StableIds
        .graphEdgeId(edge.edgeType, edge.fromId, edge.toId, edge.policyVersion, evidence)
        .toOption
        .get
    )
  }

  test("recomputed coauthorship edge IDs cannot authorize unrelated work evidence") {
    val unrelated = "work:doi:10.5555/unrelated"
    val wrong = withWorkEvidence(Fixtures.graphEdge, unrelated)
    assert(wrong.edgeId != Fixtures.graphEdge.edgeId)
    assert(wrong.provenance == Fixtures.graphEdge.provenance)
    assert(DomainValidation.check(wrong).isLeft)
    assert(
      CoreJson.parseAndValidate[GraphEdge](CoreJson.compact(wrong))(DomainValidation.check).isLeft
    )
    val multi = Fixtures.graphEdge.copy(coauthorship =
      Some(
        CoauthorshipProperties(2, 2011, 2012, Vector(Fixtures.workId, "work:doi:10.5555/second"))
      )
    )
    Vector(Fixtures.workId, "work:doi:10.5555/second").foreach { work =>
      assert(DomainValidation.check(withWorkEvidence(multi, work)).isRight)
    }
    assert(DomainValidation.check(withWorkEvidence(multi, unrelated)).isLeft)
  }

  test("work evidence on publication-derived relations matches the publication endpoint") {
    val endpoints = Vector(
      (GraphEdgeType.Authored, Fixtures.berkeleyMentionId, Fixtures.workId),
      (GraphEdgeType.Authored, Fixtures.berkeleyResearcherId, Fixtures.workId),
      (GraphEdgeType.PublishedIn, Fixtures.workId, Fixtures.venueId),
      (GraphEdgeType.HasTopic, Fixtures.workId, Fixtures.topicId)
    )
    endpoints.foreach { case (kind, from, to) =>
      val edge =
        Fixtures.graphEdge.copy(edgeType = kind, fromId = from, toId = to, coauthorship = None)
      assert(DomainValidation.check(withWorkEvidence(edge, Fixtures.workId)).isRight)
      assert(DomainValidation.check(withWorkEvidence(edge, "work:doi:10.5555/unrelated")).isLeft)
    }
  }

  test("generic provenance relations may cite a separate supporting work") {
    Vector(GraphEdgeType.DerivedFrom, GraphEdgeType.SupportedBy).foreach { kind =>
      val edge = Fixtures.graphEdge.copy(
        edgeType = kind,
        fromId = Fixtures.workId,
        toId = "work:doi:10.5555/related",
        coauthorship = None
      )
      assert(DomainValidation.check(withWorkEvidence(edge, "work:doi:10.5555/supporting")).isRight)
    }
    assert(DomainValidation.check(Fixtures.orcidEmploymentEdge).isRight)
  }

}
