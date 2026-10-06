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
  * inside `authors` are mentions, not confirmed researchers.
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
    provenance: Provenance
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

final case class Institution(
    institutionId: String,
    schemaVersion: String,
    name: String,
    ror: Option[String],
    ringgold: Option[String],
    uncertainty: String,
    provenance: Provenance
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
    provenance: Provenance
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
    provenance: Provenance
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
    provenance: Provenance
) derives ReadWriter

final case class AnswerClaim(
    claimId: String,
    schemaVersion: String,
    text: String,
    evidenceIds: Vector[String],
    verificationStatus: VerificationStatus,
    uncertainty: Option[String],
    provenance: Provenance
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
