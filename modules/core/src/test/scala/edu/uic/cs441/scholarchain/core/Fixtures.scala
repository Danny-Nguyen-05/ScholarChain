package edu.uic.cs441.scholarchain.core

import java.util.UUID

/** Contract fixtures from the committed samples. Counts below are hand counts of that sample. */
object Fixtures {
  val runId: String =
    StableIds.newRunId(UUID.fromString("00112233-4455-4677-8899-aabbccddeeff")).toOption.get

  val doi = "10.1007/978-3-642-31674-6_1"
  val workId: String = StableIds.workIdFromDoi(doi).toOption.get
  val dblpKey = "series/sapere/BerkeleyR13"
  val identityPolicy = "identity-v1"
  val graphPolicy = "graph-policy-v1"
  val title = "Machine Mentality?"

  val berkeleyName = "istvan s. n. berkeley"
  val riceName = "claiborne rice"

  val berkeleyResearcherId: String =
    StableIds
      .provisionalResearcherId(identityPolicy, SourceType.Dblp, dblpKey, 1, berkeleyName)
      .toOption
      .get

  val riceProvisionalId: String =
    StableIds
      .provisionalResearcherId(identityPolicy, SourceType.Dblp, dblpKey, 2, riceName)
      .toOption
      .get

  val riceOrcid = "0000-0002-4414-6920"
  val riceOrcidResearcherId: String =
    StableIds.researcherIdFromValidatedOrcid(riceOrcid).toOption.get

  val berkeleyMentionId: String = StableIds.mentionId(SourceType.Dblp, dblpKey, 1)
  val riceMentionId: String = StableIds.mentionId(SourceType.Dblp, dblpKey, 2)

  val venueId: String = StableIds.venueIdFromDblpBooktitle("PT-AI").toOption.get
  val openAlexInstitutionId: String =
    StableIds.institutionIdFromRor("https://ror.org/01x8rc503").toOption.get
  val ringgoldInstitutionId: String = StableIds.institutionIdFromRinggold("4365").toOption.get
  val topicId: String = StableIds.topicIdFromOpenAlex("https://openalex.org/T12090").toOption.get

  val titleChunkId: String =
    StableIds
      .chunkOrProfileId(workId, "dblp-2026-10-03", "title", None, title)
      .toOption
      .get

  val profileId: String =
    StableIds
      .chunkOrProfileId(
        riceOrcidResearcherId,
        "unknown",
        "researcher-profile",
        None,
        "Charles Claiborne Rice"
      )
      .toOption
      .get

  val coauthorEdgeId: String =
    StableIds
      .coauthorEdgeId(berkeleyResearcherId, riceProvisionalId, 2011, 2011, graphPolicy)
      .toOption
      .get

  val graphEdgeId: String =
    StableIds
      .graphEdgeId(
        GraphEdgeType.CoauthoredWith,
        berkeleyResearcherId,
        riceProvisionalId,
        graphPolicy,
        workId
      )
      .toOption
      .get

  val graphPathEvidenceId: String =
    StableIds
      .nonTextEvidenceId("graph-path", Seq(berkeleyResearcherId, riceProvisionalId))
      .toOption
      .get

  val metricEvidenceId: String =
    StableIds
      .nonTextEvidenceId(
        "metric",
        Seq(berkeleyResearcherId, "PUBLICATION_COUNT", "2011", "2011", graphPolicy)
      )
      .toOption
      .get

  val edgeEvidenceId: String =
    StableIds.nonTextEvidenceId("edge", Seq(graphEdgeId)).toOption.get

  val planId: String = "plan:" + StableIds.sha256Hex("phase3-query-plan-fixture")

  def provenance(
      source: SourceType,
      sourceRecordId: String,
      snapshot: String,
      sourceUri: Option[String],
      license: Option[String],
      notes: Vector[String]
  ): Provenance =
    Provenance(
      schemaVersion = SchemaVersions.domain,
      source = source,
      sourceRecordId = sourceRecordId,
      sourceUri = sourceUri,
      datasetSnapshot = snapshot,
      retrievalDate = Some("2026-10-05"),
      licenseEvidenceUri = license,
      runId = runId,
      uncertaintyNotes = notes
    )

  val dblpLicense: Option[String] = Some(
    "https://dblp.org/faq/Under+what+license+is+the+data+from+dblp+released"
  )

  val yearDisagreement: String =
    "DBLP year is 2011, OpenAlex publication_year is 2012, and Crossref published-print " +
      "date-parts is 2013 for DOI 10.1007/978-3-642-31674-6_1. This record keeps its source year."

  val dblpProvenance: Provenance = provenance(
    SourceType.Dblp,
    dblpKey,
    "dblp-2026-10-03",
    Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
    dblpLicense,
    Vector(
      "Author name text is a mention, not a confirmed researcher identity.",
      "ORCID 0000-0002-4414-6920 on the second author is observed, not a match decision.",
      yearDisagreement
    )
  )

  val berkeleyMention: AuthorMention = AuthorMention(
    mentionId = berkeleyMentionId,
    schemaVersion = SchemaVersions.domain,
    source = SourceType.Dblp,
    sourceRecordId = dblpKey,
    ordinal = 1,
    nameText = "Istvan S. N. Berkeley",
    normalizedName = berkeleyName,
    observedOrcid = None,
    observedOpenAlexAuthorId = None,
    identityStatus = MentionIdentityStatus.NameOnlyUnconfirmed,
    resolvedResearcherId = None,
    uncertainty = "The author string is not a confirmed researcher identity.",
    provenance = dblpProvenance
  )

  val riceMention: AuthorMention = AuthorMention(
    mentionId = riceMentionId,
    schemaVersion = SchemaVersions.domain,
    source = SourceType.Dblp,
    sourceRecordId = dblpKey,
    ordinal = 2,
    nameText = "Claiborne Rice",
    normalizedName = riceName,
    observedOrcid = Some(riceOrcid),
    observedOpenAlexAuthorId = None,
    identityStatus = MentionIdentityStatus.ExternalIdentifierObserved,
    resolvedResearcherId = None,
    uncertainty =
      "The ORCID is present on the dblp author tag and is not a ScholarChain match decision.",
    provenance = dblpProvenance
  )

  val work: WorkRecord = WorkRecord(
    schemaVersion = SchemaVersions.domain,
    workId = workId,
    source = SourceType.Dblp,
    sourceRecordId = dblpKey,
    sourceRecordType = Some("inproceedings"),
    title = title,
    normalizedTitle = TextNorm.title(title),
    year = Some(2011),
    venueId = Some(venueId),
    doi = Some(doi),
    arxivId = None,
    pages = Some("1-15"),
    externalUrl = Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
    authors = Vector(berkeleyMention, riceMention),
    abstractTextRef = None,
    provenance = dblpProvenance
  )

  val orcidResearcher: CanonicalResearcher = CanonicalResearcher(
    researcherId = riceOrcidResearcherId,
    schemaVersion = SchemaVersions.domain,
    displayName = Some("Charles Claiborne Rice"),
    externalIds = Vector(
      ObservedIdentifier("orcid", riceOrcid, IdentifierInterpretation.ValidatedExternal)
    ),
    identityConfidence = None,
    uncertainty =
      "Display name concatenates ORCID given-names 'Charles Claiborne' and family-name 'Rice'. " +
        "It is not a merge with the dblp author string 'Claiborne Rice'. " +
        "The public ORCID record lists DOI 10.1007/978-3-642-31674-6_1, and that co-occurrence " +
        "is not an accepted match decision.",
    provenance = provenance(
      SourceType.Orcid,
      riceOrcid,
      "unknown",
      Some("https://orcid.org/0000-0002-4414-6920"),
      Some("https://info.orcid.org/public-data-file-use-policy/"),
      Vector("Bulk public-data-file version is unknown. Retrieval date is 2026-10-05.")
    )
  )

  val unresolvedMatch: MatchDecision = MatchDecision(
    schemaVersion = SchemaVersions.domain,
    sourceId = riceMentionId,
    targetId = riceOrcidResearcherId,
    features = Vector.empty,
    decision = MatchOutcome.Unresolved,
    confidence = 0.0,
    reasonCodes = Vector("observed-orcid-and-doi-cooccurrence-is-not-a-match-decision"),
    policyVersion = "er-v1",
    runId = runId,
    uncertainty =
      "confidence 0.0 means no calibrated score was produced. The sample alignment is unresolved.",
    provenance = dblpProvenance
  )

  val conflictMatch: MatchDecision = unresolvedMatch.copy(
    decision = MatchOutcome.Conflict,
    reasonCodes = Vector("bibliographic-records-conflict"),
    uncertainty =
      "confidence 0.0 means no calibrated score was produced. DBLP, OpenAlex, and Crossref " +
        "disagree on year, and the ORCID display name is not merged with the dblp author string. " +
        "The alignment is a conflict."
  )

  val authorship: AuthorshipRecord = AuthorshipRecord(
    schemaVersion = SchemaVersions.domain,
    workId = workId,
    mentionId = riceMentionId,
    position = 2,
    resolvedResearcherId = None,
    uncertainty = "Position 2 is the dblp author order. The mention is not resolved.",
    provenance = dblpProvenance
  )

  val team: PublicationTeam = PublicationTeam(
    schemaVersion = SchemaVersions.domain,
    workId = workId,
    memberMentionIds = Vector(berkeleyMentionId, riceMentionId),
    teamSize = 2,
    uncertainty = "Order is the dblp author sequence, not canonical pair order.",
    provenance = dblpProvenance
  )

  val pair: CoauthorPairCandidate = CoauthorPairCandidate(
    schemaVersion = SchemaVersions.domain,
    workId = workId,
    doi = Some(doi),
    arxivId = None,
    leftMentionId = berkeleyMentionId,
    rightMentionId = riceMentionId,
    leftOrdinal = 1,
    rightOrdinal = 2,
    year = Some(2011),
    uncertainty = "Endpoints are author mentions. The year is the DBLP year only.",
    provenance = dblpProvenance
  )

  val edge: CoauthorEdge = CoauthorEdge(
    edgeId = coauthorEdgeId,
    schemaVersion = SchemaVersions.domain,
    researcherA = berkeleyResearcherId,
    researcherB = riceProvisionalId,
    windowStartYear = 2011,
    windowEndYear = 2011,
    policyVersion = graphPolicy,
    jointPublicationCount = 1,
    firstCollaborationYear = 2011,
    lastCollaborationYear = 2011,
    representativeWorkIds = Vector(workId),
    uncertainty =
      "Endpoints are provisional mention-scoped ids for one DBLP paper, not confirmed researchers. " +
        "The count is a hand count of series/sapere/BerkeleyR13, not a Spark aggregation.",
    provenance = dblpProvenance
  )

  val metrics: ResearcherMetrics = ResearcherMetrics(
    researcherId = berkeleyResearcherId,
    schemaVersion = SchemaVersions.domain,
    policyVersion = graphPolicy,
    publicationCount = 1,
    distinctCoauthorCount = 1,
    totalCoauthorOccurrences = 1,
    averageCoauthorsPerPaper = 1.0,
    maximumCoauthorsOnOnePaper = 1,
    weightedDegree = 1.0,
    componentId = "unassigned",
    communityId = None,
    bridgeScore = None,
    coreness = None,
    windowStartYear = 2011,
    windowEndYear = 2011,
    uncertainty =
      "Hand count of committed DBLP sample series/sapere/BerkeleyR13 for a provisional id. " +
        "component, community, bridge, and coreness were not computed. componentId 'unassigned' " +
        "is an explicit unknown, not a component identifier from Spark.",
    provenance = dblpProvenance
  )

  val venue: Venue = Venue(
    venueId = venueId,
    schemaVersion = SchemaVersions.domain,
    name = "PT-AI",
    sourceLabel = "PT-AI",
    issn = None,
    uncertainty =
      "Label is the dblp booktitle. Crossref container-title has two strings and is not merged here.",
    provenance = dblpProvenance
  )

  val openAlexInstitution: Institution = Institution(
    institutionId = openAlexInstitutionId,
    schemaVersion = SchemaVersions.domain,
    name = "University of Louisiana at Lafayette",
    ror = Some("https://ror.org/01x8rc503"),
    ringgold = None,
    uncertainty =
      "ROR is the OpenAlex institution ror on the sample authorship. It is not merged with ORCID " +
        "employment disambiguation RINGGOLD 4365.",
    provenance = provenance(
      SourceType.OpenAlex,
      "https://openalex.org/I79516672",
      "unknown",
      Some("https://ror.org/01x8rc503"),
      Some("https://github.com/ourresearch/openalex-docs/blob/main/license.md"),
      Vector("OpenAlex bulk snapshot date is unknown. Retrieval date is 2026-10-05.")
    ),
    observedSourceIds = Vector(
      ObservedIdentifier(
        IdentifierNamespace.OpenAlexInstitution.wire,
        "https://openalex.org/I79516672",
        IdentifierInterpretation.SourceObservation
      )
    )
  )

  val orcidEmployment: Institution = Institution(
    institutionId = ringgoldInstitutionId,
    schemaVersion = SchemaVersions.domain,
    name = "University of Louisiana at Lafayette",
    ror = None,
    ringgold = Some("4365"),
    uncertainty =
      "ORCID employment disambiguation-source is RINGGOLD 4365. No ROR is present on that summary.",
    provenance = provenance(
      SourceType.Orcid,
      riceOrcid,
      "unknown",
      None,
      Some("https://info.orcid.org/public-data-file-use-policy/"),
      Vector("Bulk public-data-file version is unknown.")
    )
  )

  val topic: Topic = Topic(
    topicId = topicId,
    schemaVersion = SchemaVersions.domain,
    name = "Language and cultural evolution",
    sourceTopicId = Some("https://openalex.org/T12090"),
    sourceScore = Some(0.9937000274658203),
    uncertainty = "sourceScore is the OpenAlex topic score, not a ScholarChain confidence.",
    provenance = provenance(
      SourceType.OpenAlex,
      "https://openalex.org/T12090",
      "unknown",
      Some("https://openalex.org/T12090"),
      Some("https://github.com/ourresearch/openalex-docs/blob/main/license.md"),
      Vector("OpenAlex bulk snapshot date is unknown.")
    )
  )

  val workNode: GraphNode = GraphNode(
    nodeId = workId,
    schemaVersion = SchemaVersions.domain,
    nodeClass = GraphNodeClass.Work,
    label = title,
    properties = Vector(NamedText("dblpKey", dblpKey)),
    provenance = dblpProvenance
  )

  val graphEdge: GraphEdge = GraphEdge(
    edgeId = graphEdgeId,
    schemaVersion = SchemaVersions.domain,
    fromId = berkeleyResearcherId,
    edgeType = GraphEdgeType.CoauthoredWith,
    toId = riceProvisionalId,
    policyVersion = graphPolicy,
    sourceEvidence = GraphSourceEvidence.Work(workId),
    properties = Vector.empty,
    coauthorship = Some(CoauthorshipProperties(1, 2011, 2011, Vector(workId))),
    provenance = dblpProvenance
  )

  val orcidEmploymentEdge: GraphEdge = {
    val sourceRecordId = "/0000-0002-4414-6920/employment/19198978"
    val evidence = GraphSourceEvidence.SourceRecord(SourceType.Orcid, sourceRecordId, "unknown")
    GraphEdge(
      edgeId = StableIds
        .graphEdgeId(
          GraphEdgeType.AffiliatedWith,
          riceOrcidResearcherId,
          ringgoldInstitutionId,
          graphPolicy,
          evidence
        )
        .toOption
        .get,
      schemaVersion = SchemaVersions.domain,
      fromId = riceOrcidResearcherId,
      edgeType = GraphEdgeType.AffiliatedWith,
      toId = ringgoldInstitutionId,
      policyVersion = graphPolicy,
      sourceEvidence = evidence,
      properties = Vector.empty,
      coauthorship = None,
      provenance = orcidEmployment.provenance.copy(sourceRecordId = sourceRecordId)
    )
  }

  val evidence: EvidenceItem = EvidenceItem(
    evidenceId = titleChunkId,
    schemaVersion = SchemaVersions.domain,
    evidenceType = EvidenceType.WorkMetadata,
    workId = Some(workId),
    sourceUri = "https://doi.org/10.1007/978-3-642-31674-6_1",
    chunkId = Some(titleChunkId),
    graphPath = None,
    score = 0.0,
    text = Some(title),
    provenance = dblpProvenance.copy(uncertaintyNotes =
      dblpProvenance.uncertaintyNotes :+ "score 0.0 is not a calibrated retrieval score."
    )
  )

  val graphPathEvidence: EvidenceItem = EvidenceItem(
    evidenceId = graphPathEvidenceId,
    schemaVersion = SchemaVersions.domain,
    evidenceType = EvidenceType.GraphPath,
    workId = Some(workId),
    sourceUri = "https://doi.org/10.1007/978-3-642-31674-6_1",
    chunkId = None,
    graphPath = Some(Vector(berkeleyResearcherId, riceProvisionalId)),
    score = 0.0,
    text = None,
    provenance = evidence.provenance
  )

  val metricEvidence: EvidenceItem = EvidenceItem(
    evidenceId = metricEvidenceId,
    schemaVersion = SchemaVersions.domain,
    evidenceType = EvidenceType.Metric,
    workId = None,
    sourceUri = "https://doi.org/10.1007/978-3-642-31674-6_1",
    chunkId = None,
    graphPath = None,
    metricLocator = Some(
      MetricEvidenceLocator(
        berkeleyResearcherId,
        CollaborationMetric.PublicationCount,
        2011,
        2011,
        graphPolicy
      )
    ),
    score = 0.0,
    text = None,
    provenance = evidence.provenance
  )

  val edgeEvidence: EvidenceItem = EvidenceItem(
    evidenceId = edgeEvidenceId,
    schemaVersion = SchemaVersions.domain,
    evidenceType = EvidenceType.CoauthorEdge,
    workId = Some(workId),
    sourceUri = "https://doi.org/10.1007/978-3-642-31674-6_1",
    chunkId = None,
    graphPath = None,
    edgeLocatorId = Some(graphEdgeId),
    score = 0.0,
    text = None,
    provenance = evidence.provenance
  )

  val bundle: EvidenceBundle = EvidenceBundle(
    bundleId = "bundle:phase3-berkeley-r13",
    schemaVersion = SchemaVersions.domain,
    queryId = planId,
    items = Vector(evidence),
    researcherIds = Vector(berkeleyResearcherId, riceProvisionalId),
    metricRecordIds = Vector.empty,
    identityConfidence = None,
    uncertainty = "Bundle cites provisional mention ids. The ORCID alignment is unresolved.",
    provenance = dblpProvenance
  )

  val plan: QueryPlan = QueryPlan(
    planId = planId,
    schemaVersion = SchemaVersions.domain,
    question = "Which author mentions are listed on DBLP series/sapere/BerkeleyR13?",
    operations = Vector(QueryOperation.DirectCoauthors),
    window = YearWindow(2011, 2011),
    topicFilters = Vector.empty,
    institutionFilters = Vector.empty,
    venueFilters = Vector("PT-AI"),
    rankingMetric = None,
    graphLimit = 2,
    vectorLimit = 1,
    maxPathDepth = 1,
    provenance = dblpProvenance.copy(uncertaintyNotes =
      Vector(
        "graphLimit, vectorLimit, and maxPathDepth were supplied by the caller for this fixture."
      )
    )
  )

  val claim: AnswerClaim = AnswerClaim(
    claimId = "claim:berkeley-r13-author-mentions",
    schemaVersion = SchemaVersions.domain,
    text =
      "DBLP series/sapere/BerkeleyR13 lists author mentions Istvan S. N. Berkeley and Claiborne Rice.",
    evidenceIds = Vector(titleChunkId),
    verificationStatus = VerificationStatus.PartiallyVerified,
    uncertainty = Some(
      "The mention strings are on the committed DBLP record. They are not confirmed researcher ids."
    ),
    provenance = dblpProvenance
  )

  val graphPathClaim: AnswerClaim = AnswerClaim(
    claimId = "claim:berkeley-r13-provisional-path",
    schemaVersion = SchemaVersions.domain,
    text = "The fixture graph path connects the two provisional mention-scoped researcher ids " +
      "from DBLP series/sapere/BerkeleyR13.",
    evidenceIds = Vector(graphPathEvidenceId),
    verificationStatus = VerificationStatus.PartiallyVerified,
    uncertainty = Some(
      "The endpoints are provisional ids for author strings. They are not confirmed researchers."
    ),
    provenance = dblpProvenance
  )

  val response: AnswerResponse = AnswerResponse(
    schemaVersion = SchemaVersions.domain,
    responseId = "response:phase3-berkeley-r13",
    queryPlanId = planId,
    runId = runId,
    summary =
      "The committed DBLP record lists two author mentions. The ORCID on the second mention is unresolved.",
    claims = Vector(claim),
    evidenceBundleId = bundle.bundleId,
    uncertainty = "No Spark metric or accepted identity match is claimed.",
    provenance = dblpProvenance
  )

  val manifest: RunManifest = RunManifest(
    runId = runId,
    schemaVersion = SchemaVersions.domain,
    pipelineName = "phase3-contract-fixture",
    datasetSnapshots = Vector(
      DatasetSnapshotRef(SourceType.Dblp, "dblp-2026-10-03", Some("2026-10-05")),
      DatasetSnapshotRef(SourceType.OpenAlex, "unknown", Some("2026-10-05")),
      DatasetSnapshotRef(SourceType.Orcid, "unknown", Some("2026-10-05")),
      DatasetSnapshotRef(SourceType.Crossref, "unknown", Some("2026-10-05"))
    ),
    configSchemaVersion = SchemaVersions.config,
    configFingerprint = StableIds.sha256Hex("phase3-config-fixture"),
    provenance = provenance(
      SourceType.ScholarChain,
      runId,
      "dblp-2026-10-03",
      None,
      None,
      Vector("OpenAlex, ORCID, and Crossref bulk snapshot dates are unknown.")
    )
  )

  def sourceWork(
      source: SourceType,
      sourceRecordId: String,
      year: Int,
      recordType: String
  ): WorkRecord = {
    val snapshot = if (source == SourceType.Dblp) "dblp-2026-10-03" else "unknown"
    val note = provenance(
      source,
      sourceRecordId,
      snapshot,
      Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
      None,
      Vector(yearDisagreement)
    )
    WorkRecord(
      schemaVersion = SchemaVersions.domain,
      workId = workId,
      source = source,
      sourceRecordId = sourceRecordId,
      sourceRecordType = Some(recordType),
      title = title,
      normalizedTitle = TextNorm.title(title),
      year = Some(year),
      venueId = None,
      doi = Some(doi),
      arxivId = None,
      pages = None,
      externalUrl = Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
      authors = Vector.empty,
      abstractTextRef = None,
      provenance = note
    )
  }
}
