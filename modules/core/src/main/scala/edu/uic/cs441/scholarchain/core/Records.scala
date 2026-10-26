package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Provenance required on every record that carries source or derived facts. */
final case class Provenance(
    schemaVersion: String,
    source: SourceType,
    sourceRecordId: String,
    sourceUri: Option[String],
    datasetSnapshot: String,
    retrievalDate: Option[String],
    licenseEvidenceUri: Option[String],
    runId: String,
    uncertaintyNotes: Vector[String]
) derives ReadWriter

final case class YearWindow(startYear: Int, endYear: Int) derives ReadWriter

final case class NamedNumber(name: String, value: Double) derives ReadWriter

final case class NamedText(name: String, value: String) derives ReadWriter

final case class ObservedIdentifier(
    namespace: String,
    value: String,
    interpretation: IdentifierInterpretation
) derives ReadWriter

/** One source's observation of a work. `year` is that source's year and is not reconciled when
  * DBLP, OpenAlex, and Crossref disagree. A DOI in `doi` makes `workId` the DOI id. Author names
  * inside `authors` are mentions, not confirmed researchers. This record has no affiliation field.
  * A name-only publisher affiliation is a [[MentionAffiliation]]. `abstractTextRef`, when present,
  * is a `chunk:` or `profile:` id produced by [[StableIds.chunkOrProfileId]] and must name an
  * [[EmittedTextDocument]] the pipeline emits, or a chunk or profile id already emitted for a
  * documented source version. A supplied Crossref or OpenAlex abstract is an
  * [[EmittedTextDocument]] with `documentType` `abstract`, `entityId` equal to this work id, and
  * `sourceVersion` equal to the dataset snapshot. `abstractTextRef` is that document's chunk id. A
  * URL, inverted index, or raw abstract is not a text reference. `observedIdentifiers` retains
  * declared field roles and raw source values independently of the preferred identifier.
  * `sourceLinks` retains supplied links with their source field names and within-field order,
  * including repetitions. Neither field resolves a disagreement.
  */
final case class WorkRecord(
    schemaVersion: String,
    workId: String,
    source: SourceType,
    sourceRecordId: String,
    sourceRecordType: Option[String],
    title: String,
    normalizedTitle: String,
    year: Option[Int],
    venueId: Option[String],
    doi: Option[String],
    arxivId: Option[String],
    pages: Option[String],
    externalUrl: Option[String],
    authors: Vector[AuthorMention],
    abstractTextRef: Option[String],
    provenance: Provenance,
    observedIdentifiers: Vector[ObservedIdentifier] = Vector.empty,
    sourceLinks: Vector[NamedText] = Vector.empty
) derives ReadWriter

final case class AuthorMention(
    mentionId: String,
    schemaVersion: String,
    source: SourceType,
    sourceRecordId: String,
    ordinal: Int,
    nameText: String,
    normalizedName: String,
    observedOrcid: Option[String],
    observedOpenAlexAuthorId: Option[String],
    identityStatus: MentionIdentityStatus,
    resolvedResearcherId: Option[String],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class CanonicalResearcher(
    researcherId: String,
    schemaVersion: String,
    displayName: Option[String],
    externalIds: Vector[ObservedIdentifier],
    identityConfidence: Option[Double],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class AuthorshipRecord(
    schemaVersion: String,
    workId: String,
    mentionId: String,
    position: Int,
    resolvedResearcherId: Option[String],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class PublicationTeam(
    schemaVersion: String,
    workId: String,
    memberMentionIds: Vector[String],
    teamSize: Int,
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** One undirected pair from a single work, before cross-paper consolidation. `doi` and `arxivId`
  * repeat the source observation's bibliographic identifiers and bind `workId` independently of
  * `provenance.sourceUri`.
  */
final case class CoauthorPairCandidate(
    schemaVersion: String,
    workId: String,
    doi: Option[String],
    arxivId: Option[String],
    leftMentionId: String,
    rightMentionId: String,
    leftOrdinal: Int,
    rightOrdinal: Int,
    year: Option[Int],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class CoauthorEdge(
    edgeId: String,
    schemaVersion: String,
    researcherA: String,
    researcherB: String,
    windowStartYear: Int,
    windowEndYear: Int,
    policyVersion: String,
    jointPublicationCount: Long,
    firstCollaborationYear: Int,
    lastCollaborationYear: Int,
    representativeWorkIds: Vector[String],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** weightedDegree is the sum of incident coauthor edge jointPublicationCounts in this window and
  * policy over the complete deduplicated canonical graph and publication population, equal to
  * totalCoauthorOccurrences. Average includes solo papers. Provisional fixture IDs illustrate the
  * arithmetic only; their uncertainty must not claim a computed canonical graph.
  */
final case class ResearcherMetrics(
    researcherId: String,
    schemaVersion: String,
    policyVersion: String,
    publicationCount: Long,
    distinctCoauthorCount: Long,
    totalCoauthorOccurrences: Long,
    averageCoauthorsPerPaper: Double,
    maximumCoauthorsOnOnePaper: Long,
    weightedDegree: Double,
    componentId: String,
    communityId: Option[String],
    bridgeScore: Option[Double],
    coreness: Option[Int],
    windowStartYear: Int,
    windowEndYear: Int,
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class Venue(
    venueId: String,
    schemaVersion: String,
    name: String,
    sourceLabel: String,
    issn: Option[String],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** Preferred `institutionId` may be a ROR id while `observedSourceIds` still carries another source
  * institution id, including `openalex-institution`. Those observations do not create a researcher
  * id or a work id.
  */
final case class Institution(
    institutionId: String,
    schemaVersion: String,
    name: String,
    ror: Option[String],
    ringgold: Option[String],
    uncertainty: String,
    provenance: Provenance,
    observedSourceIds: Vector[ObservedIdentifier] = Vector.empty
) derives ReadWriter

final case class Topic(
    topicId: String,
    schemaVersion: String,
    name: String,
    sourceTopicId: Option[String],
    sourceScore: Option[Double],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class MatchDecision(
    schemaVersion: String,
    sourceId: String,
    targetId: String,
    features: Vector[NamedNumber],
    decision: MatchOutcome,
    confidence: Double,
    reasonCodes: Vector[String],
    policyVersion: String,
    runId: String,
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

final case class GraphNode(
    nodeId: String,
    schemaVersion: String,
    nodeClass: GraphNodeClass,
    label: String,
    properties: Vector[NamedText],
    provenance: Provenance
) derives ReadWriter

/** Evidence is either a validated-form work id or a named source observation. SourceRecord carries
  * the snapshot and source-native record key, including ORCID activity paths.
  */
enum GraphSourceEvidence derives ReadWriter {
  case Work(workId: String)
  case SourceRecord(source: SourceType, sourceRecordId: String, datasetSnapshot: String)
}

/** Typed coauthorship values; representativeWorkIds is a distinct non-empty vector, bounded by
  * jointPublicationCount. Extra NamedText properties cannot repeat these reserved fields.
  */
final case class CoauthorshipProperties(
    jointPublicationCount: Long,
    firstCollaborationYear: Int,
    lastCollaborationYear: Int,
    representativeWorkIds: Vector[String]
) derives ReadWriter

final case class GraphEdge(
    edgeId: String,
    schemaVersion: String,
    fromId: String,
    edgeType: GraphEdgeType,
    toId: String,
    policyVersion: String,
    sourceEvidence: GraphSourceEvidence,
    properties: Vector[NamedText],
    coauthorship: Option[CoauthorshipProperties],
    provenance: Provenance
) derives ReadWriter

/** Locator fields hashed into a metric evidence id. */
final case class MetricEvidenceLocator(
    researcherId: String,
    metric: CollaborationMetric,
    windowStartYear: Int,
    windowEndYear: Int,
    policyVersion: String
) derives ReadWriter

final case class EvidenceItem(
    evidenceId: String,
    schemaVersion: String,
    evidenceType: EvidenceType,
    workId: Option[String],
    sourceUri: String,
    chunkId: Option[String],
    graphPath: Option[Vector[String]],
    metricLocator: Option[MetricEvidenceLocator] = None,
    edgeLocatorId: Option[String] = None,
    score: Double,
    text: Option[String],
    provenance: Provenance,
    runtime: Option[RuntimeEvidence] = None
) derives ReadWriter

final case class EvidenceBundle(
    bundleId: String,
    schemaVersion: String,
    queryId: String,
    items: Vector[EvidenceItem],
    researcherIds: Vector[String],
    metricRecordIds: Vector[String],
    identityConfidence: Option[Double],
    uncertainty: String,
    provenance: Provenance,
    runtime: Option[RuntimeBundleContext] = None
) derives ReadWriter

final case class QueryPlan(
    planId: String,
    schemaVersion: String,
    question: String,
    operations: Vector[QueryOperation],
    window: YearWindow,
    topicFilters: Vector[String],
    institutionFilters: Vector[String],
    venueFilters: Vector[String],
    rankingMetric: Option[CollaborationMetric],
    graphLimit: Int,
    vectorLimit: Int,
    maxPathDepth: Int,
    provenance: Provenance,
    runtime: Option[RuntimeQueryOptions] = None
) derives ReadWriter

final case class AnswerClaim(
    claimId: String,
    schemaVersion: String,
    text: String,
    evidenceIds: Vector[String],
    verificationStatus: VerificationStatus,
    uncertainty: Option[String],
    provenance: Provenance,
    runtime: Option[TypedAnswerClaim] = None
) derives ReadWriter

final case class AnswerResponse(
    schemaVersion: String,
    responseId: String,
    queryPlanId: String,
    runId: String,
    summary: String,
    claims: Vector[AnswerClaim],
    evidenceBundleId: String,
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** Pointer to one source snapshot. Fields stay `source`, `snapshot`, and `retrievalDate`.
  * Processing identity is this snapshot id, `retrievalDate`, and the checksum of the acquired
  * bytes. A live API retrieval date is not a bulk snapshot date.
  */
final case class DatasetSnapshotRef(
    source: SourceType,
    snapshot: String,
    retrievalDate: Option[String]
) derives ReadWriter

/** Immutable manifest stored with a timestamp-independent run id. */
final case class RunManifest(
    runId: String,
    schemaVersion: String,
    pipelineName: String,
    datasetSnapshots: Vector[DatasetSnapshotRef],
    configSchemaVersion: String,
    configFingerprint: String,
    provenance: Provenance
) derives ReadWriter

/** One side of a [[MatchCandidate]]. Identity is source, source record, and snapshot. `workId` is
  * present only when that observation already has a validated work id. It is not a merge key.
  */
final case class CandidateObservation(
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    workId: Option[String]
) derives ReadWriter

/** Phase 4 evidence that two observations fell in one block. This is not a [[MatchDecision]]: there
  * is no [[MatchOutcome]], threshold, or claimed identity merge. `candidateId` is
  * [[StableIds.matchCandidateId]]. Stored sides are already in that canonical order. Features stay
  * sorted distinct [[NamedNumber]] values. [[PreparationFeatures.policyV1]] keeps the previous
  * names. [[PreparationFeatures.policyV2]] uses only [[PreparationFeatures.names]].
  */
final case class MatchCandidate(
    candidateId: String,
    schemaVersion: String,
    blockKey: String,
    left: CandidateObservation,
    right: CandidateObservation,
    features: Vector[NamedNumber],
    featurePolicyVersion: String,
    runId: String,
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** A source row that did not become a valid domain record. `source` is empty when the failure is
  * byte-level and the source system is not known; validation does not invent one. At least one of
  * `diagnosticExcerpt` and `diagnosticHash` is required. The excerpt is at most
  * [[RejectRecord.maxDiagnosticExcerptLength]] UTF-16 code units.
  */
final case class RejectRecord(
    schemaVersion: String,
    source: Option[SourceType],
    sourceLocator: String,
    datasetSnapshot: Option[String],
    runId: String,
    stage: PreparationStage,
    reasonCode: RejectReasonCode,
    diagnosticExcerpt: Option[String],
    diagnosticHash: Option[String]
) derives ReadWriter

object RejectRecord {
  val maxDiagnosticExcerptLength: Int = 256
  val maxSourceLocatorLength: Int = 1024
}

/** One observation of one normalized identifier. Rows are not collapsed when several sources share
  * a value. `preferredWorkId` is set only for a work namespace whose value parsed. ORCID, ROR,
  * Ringgold, OpenAlex author ids, and OpenAlex institution ids parse to a row with
  * `preferredWorkId` empty. Malformed values are not rows; they are [[RejectRecord]]s with
  * [[RejectReasonCode.InvalidIdentifier]].
  */
final case class IdentifierIndexEntry(
    schemaVersion: String,
    namespace: IdentifierNamespace,
    normalizedValue: String,
    preferredWorkId: Option[String],
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    runId: String,
    provenance: Provenance
) derives ReadWriter

/** Text the pipeline emits so a work `abstractTextRef` or profile chunk id has a target.
  * `documentType` `abstract` uses a `chunk:` id. A supplied Crossref or OpenAlex abstract uses that
  * document type, `entityId` equal to the work id, and `sourceVersion` equal to the dataset
  * snapshot. `WorkRecord.abstractTextRef` is that chunk id. A URL is not a text reference.
  * `documentType` `researcher-profile` uses the existing `profile:` prefix. `textId` is
  * [[StableIds.chunkOrProfileId]] over `entityId`, `sourceVersion`, `documentType`, `ordinal`, and
  * `text`.
  */
final case class EmittedTextDocument(
    textId: String,
    schemaVersion: String,
    documentType: String,
    entityId: String,
    sourceVersion: String,
    ordinal: Option[Int],
    text: String,
    provenance: Provenance
) derives ReadWriter

object EmittedTextDocument {
  val abstractDocumentType: String = "abstract"
  val researcherProfileDocumentType: String = "researcher-profile"
}

/** Public ORCID person record. [[CanonicalResearcher]] is an identity record and has no place for
  * this profile's declared names and external ids without looking like a match decision.
  * [[WorkRecord]] would fabricate a publication. Activities are separate [[OrcidActivityRecord]]s.
  */
final case class OrcidProfileRecord(
    schemaVersion: String,
    orcid: String,
    displayName: Option[String],
    otherNames: Vector[String],
    externalIds: Vector[ObservedIdentifier],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

/** One declared ORCID external identifier. `externalIdType` and `value` are required.
  * `relationship` is the source `external-id-relationship` when the source supplied one. This is
  * evidence beside the preferred DOI fields. It is not a preferred work id and not a merge.
  */
final case class OrcidWorkReference(
    externalIdType: String,
    value: String,
    relationship: Option[String]
) derives ReadWriter

/** One ORCID activity path. A work summary is not a [[WorkRecord]]: it has no author list and a
  * linked DOI is not authorship or a cross-dataset merge. ROR and Ringgold stay in their own
  * fields. `institutionId`, when set, matches exactly one of those fields and does not copy one
  * namespace into the other. `observedDoi` and `observedWorkId` stay the preferred DOI fields.
  * `workReferences` keeps every declared external id, including the DOI, `other-id`, ISBN, and
  * ISSN, plus the relationship when the source supplied one.
  */
final case class OrcidActivityRecord(
    schemaVersion: String,
    orcid: String,
    activityKind: OrcidActivityKind,
    sourceRecordId: String,
    title: Option[String],
    startYear: Option[Int],
    publicationYear: Option[Int],
    organizationName: Option[String],
    ror: Option[String],
    ringgold: Option[String],
    institutionId: Option[String],
    observedDoi: Option[String],
    observedWorkId: Option[String],
    uncertainty: String,
    provenance: Provenance,
    workReferences: Vector[OrcidWorkReference] = Vector.empty
) derives ReadWriter

/** Venue, institution, or topic evidence attached to a work or an unresolved mention. [[GraphEdge]]
  * `AFFILIATED_WITH` requires a researcher id, so a mention-scoped affiliation cannot use it
  * without an identity decision. ROR and Ringgold remain distinct fields. `targetId` is required,
  * so a publisher affiliation name with no ROR or Ringgold is a [[MentionAffiliation]] instead.
  */
final case class EnrichmentLink(
    schemaVersion: String,
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    workId: Option[String],
    mentionId: Option[String],
    targetKind: EnrichmentTargetKind,
    targetId: String,
    ror: Option[String],
    ringgold: Option[String],
    score: Option[Double],
    uncertainty: String,
    runId: String,
    provenance: Provenance
) derives ReadWriter

/** Affiliation evidence for one [[AuthorMention]] when no institution target id exists.
  * [[AuthorMention]] has no affiliation field. An empty `organizationName` means the name is
  * absent; a blank string is invalid, and the literal placeholder `institution` is rejected.
  * `institutionId` is set only when it is exactly the ROR or Ringgold institution id of a populated
  * field. A name does not invent an institution id.
  */
final case class MentionAffiliation(
    schemaVersion: String,
    mentionId: String,
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String,
    organizationName: Option[String],
    ror: Option[String],
    ringgold: Option[String],
    institutionId: Option[String],
    uncertainty: String,
    provenance: Provenance
) derives ReadWriter

object MentionAffiliation {
  val rejectedOrganizationName: String = "institution"
}
