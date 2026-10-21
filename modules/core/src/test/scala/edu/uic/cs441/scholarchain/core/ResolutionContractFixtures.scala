package edu.uic.cs441.scholarchain.core

/** Contract examples reuse source facts from Fixtures; decisions and scores are SYNTHETIC, not
  * matching results, human labels or evaluation evidence.
  */
object ResolutionContractFixtures {
  val schema: String = ResolutionContracts.schemaVersion
  val hash: String = StableIds.sha256Hex("synthetic-contract-policy")
  def ref(p: Provenance): ResolutionObservationRef =
    ResolutionObservationRef(p.source, p.sourceRecordId, p.datasetSnapshot)

  val crossref: WorkRecord =
    Fixtures.sourceWork(SourceType.Crossref, Fixtures.doi, 2013, "book-chapter")
  val profile: OrcidProfileRecord = OrcidProfileRecord(
    SchemaVersions.domain,
    Fixtures.riceOrcid,
    Some("Charles Claiborne Rice"),
    Vector.empty,
    Vector(
      ObservedIdentifier("orcid", Fixtures.riceOrcid, IdentifierInterpretation.ValidatedExternal)
    ),
    "Source profile does not itself decide an identity merge.",
    Fixtures.orcidResearcher.provenance
  )
  val employment: OrcidActivityRecord = OrcidActivityRecord(
    SchemaVersions.domain,
    Fixtures.riceOrcid,
    OrcidActivityKind.Employment,
    s"/${Fixtures.riceOrcid}/employment/19198978",
    Some("Associate Professor"),
    Some(2010),
    None,
    Some("University of Louisiana at Lafayette"),
    None,
    Some("4365"),
    Some(Fixtures.ringgoldInstitutionId),
    None,
    None,
    "Public ORCID employment observation; no identity decision.",
    Fixtures.orcidEmploymentEdge.provenance
  )
  val activity: OrcidActivityRecord = employment.copy(
    activityKind = OrcidActivityKind.Work,
    sourceRecordId = s"/${Fixtures.riceOrcid}/work/123",
    title = Some(Fixtures.title),
    startYear = None,
    publicationYear = Some(2013),
    organizationName = None,
    ror = None,
    ringgold = None,
    institutionId = None,
    observedDoi = Some(Fixtures.doi),
    observedWorkId = Some(Fixtures.workId),
    uncertainty = "Synthetic ORCID work activity fixture, no author list.",
    provenance = employment.provenance.copy(sourceRecordId = s"/${Fixtures.riceOrcid}/work/123")
  )
  val workEndpoint: ResolutionEndpoint =
    ResolutionEndpoint.Work(ref(Fixtures.work.provenance), Fixtures.workId)
  val crossrefEndpoint: ResolutionEndpoint =
    ResolutionEndpoint.Work(ref(crossref.provenance), crossref.workId)
  val mentionEndpoint: ResolutionEndpoint =
    ResolutionEndpoint.Mention(ref(Fixtures.work.provenance), Fixtures.riceMentionId)
  val profileEndpoint: ResolutionEndpoint =
    ResolutionEndpoint.OrcidProfile(ref(profile.provenance), profile.orcid)
  val activityEndpoint: ResolutionEndpoint =
    ResolutionEndpoint.OrcidWorkActivity(ref(activity.provenance), activity.observedWorkId)

  val context: ResolutionValidationContext = ResolutionValidationContext
    .create(
      Vector(Fixtures.work, crossref),
      Vector(profile),
      Vector(activity, employment)
    )
    .toOption
    .get
  val workPair: ResolutionPair =
    ResolutionIds.pair(ResolutionEntityType.Work, workEndpoint, crossrefEndpoint).toOption.get
  val researcherPair: ResolutionPair = ResolutionIds
    .pair(ResolutionEntityType.Researcher, mentionEndpoint, profileEndpoint)
    .toOption
    .get

  def audit(pair: ResolutionPair, outcome: MatchOutcome): ResolutionDecision = {
    val provenance = Fixtures.dblpProvenance.copy(
      source = SourceType.ScholarChain,
      sourceRecordId = pair.pairId,
      sourceUri = None,
      datasetSnapshot = "synthetic-contract-2026-10-15",
      uncertaintyNotes =
        Vector("Synthetic contract example; not a model result or human annotation.")
    )
    val value = ResolutionDecision(
      schema,
      "",
      pair,
      MatchDecision(
        SchemaVersions.domain,
        ResolutionIds.endpointId(pair.left),
        ResolutionIds.endpointId(pair.right),
        Vector(NamedNumber("synthetic_similarity", 0.8)),
        outcome,
        0.8,
        Vector("SYNTHETIC_CONTRACT_EXAMPLE"),
        "synthetic-contract-v1",
        Fixtures.runId,
        "Synthetic contract example; no identity decision has been run.",
        provenance
      ),
      Vector.empty,
      "synthetic-features-v1",
      Vector(
        ResolutionFeature("synthetic_similarity", Some(0.8), None, Vector("source:fixture")),
        ResolutionFeature(
          "year_distance",
          None,
          Some("NOT_COMPUTED_IN_CONTRACT_EXAMPLE"),
          Vector.empty
        )
      ),
      ResolutionDecisionPath.Scored,
      ResolutionConfidenceSemantics.UncalibratedScore,
      None,
      hash,
      hash,
      hash,
      Vector("source:fixture"),
      "2026-10-15T12:00:00Z",
      None
    )
    reidentify(value)
  }
  def reidentify(value: ResolutionDecision): ResolutionDecision =
    value.copy(decisionId = ResolutionIds.decisionId(value))
  val workDecision: ResolutionDecision = audit(workPair, MatchOutcome.Accepted)
  val researcherDecision: ResolutionDecision = audit(researcherPair, MatchOutcome.Unresolved)
  def link(audit: ResolutionDecision): ResolutionAcceptedLink = ResolutionAcceptedLink(
    schema,
    audit.pair,
    audit.decisionId,
    audit.decision.policyVersion,
    audit.policyHash,
    audit.decision.runId,
    audit.decision.provenance
  )
  val acceptedLink: ResolutionAcceptedLink = link(workDecision)
  val grouping: ResolutionGroupingConstraints = ResolutionGroupingConstraints(
    schema,
    ResolutionEntityType.Work,
    "synthetic-contract-v1",
    hash,
    Vector(workEndpoint, crossrefEndpoint),
    Vector.empty,
    Vector(workEndpoint, crossrefEndpoint).map(e =>
      ResolutionIdentifierAssertion(
        e,
        ResolutionAuthorityNamespace.Doi,
        Fixtures.doi,
        Vector("source:fixture")
      )
    )
  )
}
