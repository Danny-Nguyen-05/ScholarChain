package edu.uic.cs441.scholarchain.core

import upickle.default.{ReadWriter, readwriter}

/** A bounded or unbounded time window. `comparisonOrder` is present only for the disjoint sequence
  * used by temporal deltas; all-years and cumulative windows leave it empty.
  */
final case class SparkWindow(
    windowId: String,
    startYear: Option[Int],
    endYear: Option[Int],
    comparisonOrder: Option[Int]
) derives ReadWriter

/** A stable pointer to upstream evidence. Empty work/mention lists mean the row references the
  * complete source run, not that the source has no evidence.
  */
final case class SparkLineage(
    hadoopRunId: String,
    hadoopSnapshot: String,
    entityResolutionRunId: String,
    entityResolutionPolicyVersion: String,
    entityResolutionPolicyHash: String,
    sourceWorkIds: Vector[String],
    sourceMentionIds: Vector[String]
) derives ReadWriter

/** Repeated on every Phase 6 analytics row, including integrity and load metadata. */
final case class SparkRecordContext(
    schemaVersion: String,
    runId: String,
    windowId: Option[String],
    lineage: SparkLineage
) derives ReadWriter

/** Companion to the frozen v1 ResearcherMetrics wire format. */
final case class ResearcherMetricsDetail(
    context: SparkRecordContext,
    researcherId: String,
    policyVersion: String,
    publicationCount: Long,
    distinctCoauthorCount: Long,
    totalCoauthorOccurrences: Long,
    averageCoauthorsPerPaper: Double,
    maximumCoauthorsOnOnePaper: Long,
    maxTeamWorkIds: Vector[String],
    maxTeamWorkTieCount: Long,
    weightedDegree: Long,
    componentId: String,
    communityId: Option[String],
    coreness: Option[Int]
) derives ReadWriter

final case class ResearcherBridgeMetrics(
    context: SparkRecordContext,
    researcherId: String,
    policyVersion: String,
    crossCommunityDegree: Long,
    crossCommunityWeight: Long,
    communitiesConnected: Long,
    participationCoefficient: Double
) derives ReadWriter

final case class ComponentMembership(
    context: SparkRecordContext,
    researcherId: String,
    componentId: String
) derives ReadWriter

final case class ComponentSummary(
    context: SparkRecordContext,
    componentId: String,
    minimumResearcherId: String,
    size: Long,
    isLargest: Boolean,
    largestComponentFraction: Double,
    singletonCount: Long
) derives ReadWriter

final case class CommunityMembership(
    context: SparkRecordContext,
    researcherId: String,
    communityId: String,
    iterations: Int,
    converged: Boolean
) derives ReadWriter

final case class CommunitySummary(
    context: SparkRecordContext,
    communityId: String,
    size: Long,
    iterations: Int,
    finalChangedCount: Long,
    converged: Boolean
) derives ReadWriter

final case class CrossCommunityEdge(
    context: SparkRecordContext,
    communityA: String,
    communityB: String,
    edgeCount: Long,
    summedWeight: Long
) derives ReadWriter

/** All-years includes works with unknown year. Its first/last years therefore remain optional. The
  * v1 numeric-window CoauthorEdge stays intact for existing consumers.
  */
final case class SparkCoauthorEdge(
    context: SparkRecordContext,
    edgeId: String,
    researcherA: String,
    researcherB: String,
    policyVersion: String,
    jointPublicationCount: Long,
    firstCollaborationYear: Option[Int],
    lastCollaborationYear: Option[Int],
    representativeWorkIds: Vector[String]
) derives ReadWriter

final case class CoauthorEdgeSupport(
    context: SparkRecordContext,
    edgeId: String,
    workId: String,
    year: Option[Int]
) derives ReadWriter

enum PathStatus(val wire: String) {
  case Found extends PathStatus("found")
  case NoPath extends PathStatus("no-path")
  case ExceededMaxHops extends PathStatus("exceeded-maxHops")
}

object PathStatus {
  given ReadWriter[PathStatus] = readwriter[String].bimap[PathStatus](
    _.wire,
    wire =>
      PathStatus.values
        .find(_.wire == wire)
        .getOrElse(throw new IllegalArgumentException(s"unsupported path status: $wire"))
  )
}

final case class PathHop(
    fromResearcherId: String,
    toResearcherId: String,
    edgeId: String,
    jointPublicationCount: Long,
    representativeWorkIds: Vector[String]
) derives ReadWriter

final case class PathEvidence(
    context: SparkRecordContext,
    pathEvidenceId: String,
    sourceResearcherId: String,
    targetResearcherId: String,
    status: PathStatus,
    hopCount: Option[Int],
    orderedResearcherIds: Vector[String],
    hops: Vector[PathHop],
    maxHops: Int
) derives ReadWriter

final case class PathLengthEstimate(
    context: SparkRecordContext,
    componentId: String,
    method: String,
    sampleSourceCount: Int,
    seed: Long,
    meanDistance: Double,
    effectiveDiameterP90: Double,
    reachedPairCount: Long
) derives ReadWriter

final case class TemporalChange(
    context: SparkRecordContext,
    researcherId: String,
    fromWindowId: String,
    toWindowId: String,
    fromPresent: Boolean,
    toPresent: Boolean,
    deltaDistinctCoauthors: Option[Long],
    deltaAverageCoauthorsPerPaper: Option[Double],
    deltaMaximumCoauthorsOnOnePaper: Option[Long],
    deltaComponentSize: Option[Long],
    enteredLargestComponent: Boolean,
    leftLargestComponent: Boolean,
    previousCommunityId: Option[String],
    currentCommunityId: Option[String],
    communityJaccardOverlap: Option[Double],
    deltaCrossCommunityDegree: Option[Long],
    deltaCrossCommunityWeight: Option[Long],
    deltaCommunitiesConnected: Option[Long],
    deltaParticipationCoefficient: Option[Double]
) derives ReadWriter

final case class SummarySourceRef(
    table: String,
    rowKey: String,
    field: String
) derives ReadWriter

final case class SemanticSummary(
    context: SparkRecordContext,
    summaryId: String,
    summaryType: String,
    entityId: String,
    policyVersion: String,
    text: String,
    sourceReferences: Vector[SummarySourceRef],
    abstractTextIds: Vector[String]
) derives ReadWriter

final case class IntegrityViolation(
    context: SparkRecordContext,
    code: String,
    entityId: Option[String],
    detail: String,
    hardFailure: Boolean,
    evidenceRefs: Vector[SummarySourceRef]
) derives ReadWriter

final case class LoadManifest(
    context: SparkRecordContext,
    targetStore: String,
    logicalDataset: String,
    paths: Vector[String],
    format: String,
    rowCount: Long,
    keyColumns: Vector[String],
    partitionColumns: Vector[String],
    sortedRowsSha256: String,
    windows: Vector[String],
    intendedLoaderOwner: String,
    targetMapping: Vector[NamedText]
) derives ReadWriter

final case class SparkCounter(
    context: SparkRecordContext,
    name: String,
    value: Long,
    detail: Option[String]
) derives ReadWriter
