package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Additive runtime fields use the existing domain wire records; old records remain readable. */
enum RetrievalMode(val wire: String) {
  case Graph extends RetrievalMode("graph")
  case Vector extends RetrievalMode("vector")
  case Fused extends RetrievalMode("fused")
}
object RetrievalMode {
  given ReadWriter[RetrievalMode] = EnumCodecs.wire(RetrievalMode.values, _.wire)
}

final case class RuntimeQueryOptions(
    researcherNames: Vector[String] = Vector.empty,
    windowIds: Vector[String] = Vector.empty,
    comparisonWindowIds: Vector[String] = Vector.empty,
    retrievalMode: RetrievalMode = RetrievalMode.Fused,
    evidenceOnly: Boolean = false,
    rankingMeasure: Option[String] = None,
    unsupportedReason: Option[String] = None,
    authorCountConversion: Boolean = false
) derives ReadWriter

/** Counts cover distinct merged cache/context values before truncation. Individual returned lists
  * reveal which count exceeds its retained size; coauthors retain their separate qualification.
  */
final case class ResearcherCandidateProvenanceSummary(
    sourceIdCount: Int,
    evidenceRefCount: Int,
    affiliationCount: Int,
    runIdCount: Int,
    truncated: Boolean
) derives ReadWriter

final case class ResearcherCandidate(
    researcherId: String,
    displayName: String,
    sourceIds: Vector[String],
    affiliations: Vector[String],
    confidence: Option[Double],
    coauthorContext: Vector[String],
    evidenceRefs: Vector[String],
    runIds: Vector[String],
    coauthorContextTruncated: Option[Boolean] = None,
    provenanceSummary: Option[ResearcherCandidateProvenanceSummary] = None
) derives ReadWriter

/** Decimal strings preserve exact stored Longs; a field has exactly one value representation. */
final case class RuntimeClaimValue(
    field: String,
    number: Option[String] = None,
    text: Option[String] = None,
    ids: Option[Vector[String]] = None,
    flag: Option[Boolean] = None
) derives ReadWriter

enum RuntimeClaimType(val wire: String) {
  case Metric extends RuntimeClaimType("METRIC")
  case Ranking extends RuntimeClaimType("RANKING")
  case Identity extends RuntimeClaimType("IDENTITY")
  case Publication extends RuntimeClaimType("PUBLICATION")
  case Path extends RuntimeClaimType("PATH")
  case Community extends RuntimeClaimType("COMMUNITY")
  case Bridge extends RuntimeClaimType("BRIDGE")
  case Temporal extends RuntimeClaimType("TEMPORAL")
  case Semantic extends RuntimeClaimType("SEMANTIC")
}
object RuntimeClaimType {
  given ReadWriter[RuntimeClaimType] = EnumCodecs.wire(RuntimeClaimType.values, _.wire)
}
final case class TypedAnswerClaim(
    claimType: RuntimeClaimType,
    subjectIds: Vector[String],
    values: Vector[RuntimeClaimValue],
    windowIds: Vector[String],
    templateId: String
) derives ReadWriter

/** Descriptive semantic evidence cannot authorize deterministic graph facts. Qualifications are
  * source observations, including false convergence and approximate distance estimates.
  */
final case class RuntimeEvidence(
    subjectIds: Vector[String],
    windowIds: Vector[String],
    metricVersion: Option[String],
    runId: String,
    values: Vector[RuntimeClaimValue],
    sourceRefs: Vector[SummarySourceRef],
    converged: Option[Boolean],
    iterations: Option[Int],
    approximate: Boolean,
    descriptive: Boolean
) derives ReadWriter
final case class RuntimeBundleContext(
    deterministicEvidenceIds: Vector[String],
    semanticEvidenceIds: Vector[String],
    graphRunIds: Vector[String],
    metricVersions: Vector[String],
    retrievalMode: RetrievalMode,
    rankingScope: Option[String],
    truncated: Boolean
) derives ReadWriter

enum ClaimVerdict(val wire: String) {
  case Verified extends ClaimVerdict("VERIFIED")
  case PartiallySupported extends ClaimVerdict("PARTIALLY_SUPPORTED")
  case Unsupported extends ClaimVerdict("UNSUPPORTED")
  case Conflicting extends ClaimVerdict("CONFLICTING")

  def verificationStatus: VerificationStatus = this match {
    case Verified           => VerificationStatus.Verified
    case PartiallySupported => VerificationStatus.PartiallyVerified
    case Unsupported        => VerificationStatus.Rejected
    case Conflicting        => VerificationStatus.Rejected
  }
}
object ClaimVerdict {
  given ReadWriter[ClaimVerdict] = EnumCodecs.wire(ClaimVerdict.values, _.wire)
}
final case class ClaimVerificationResult(
    claimId: String,
    verdict: ClaimVerdict,
    reasons: Vector[String]
) derives ReadWriter
final case class VerificationResult(
    claims: Vector[ClaimVerificationResult],
    rejectedClaims: Vector[AnswerClaim],
    abstained: Boolean
) derives ReadWriter {
  def overallStatus: VerificationStatus =
    if (abstained) VerificationStatus.Abstained
    else if (claims.isEmpty) VerificationStatus.Unverified
    else if (claims.forall(_.verdict == ClaimVerdict.Verified)) VerificationStatus.Verified
    else if (
      claims
        .forall(c => c.verdict == ClaimVerdict.Unsupported || c.verdict == ClaimVerdict.Conflicting)
    )
      VerificationStatus.Rejected
    else VerificationStatus.PartiallyVerified
}
final case class RuntimeModelUsage(
    modelId: String,
    modelVersion: String,
    promptVersion: String,
    schemaVersion: String,
    inputTokens: Option[Long],
    outputTokens: Option[Long]
) derives ReadWriter
final case class AuditRecord(
    queryId: String,
    traceId: String,
    plan: QueryPlan,
    resolvedResearcherIds: Vector[String],
    evidenceIds: Vector[String],
    metricVersions: Vector[String],
    graphRunIds: Vector[String],
    modelUsage: Vector[RuntimeModelUsage],
    latencyMillis: Long,
    attemptedClaims: Vector[AnswerClaim],
    verification: VerificationResult,
    answerHash: String
) derives ReadWriter

/** Stored artifact projections; no runtime recomputation or vector-derived population. */
enum RuntimeRankingMetric(val wire: String) {
  case PublicationCount extends RuntimeRankingMetric("PUBLICATION_COUNT")
  case DistinctCoauthorCount extends RuntimeRankingMetric("DISTINCT_COAUTHOR_COUNT")
  case TotalCoauthorOccurrences extends RuntimeRankingMetric("TOTAL_COAUTHOR_OCCURRENCES")
  case AverageCoauthorsPerPaper extends RuntimeRankingMetric("AVERAGE_COAUTHORS_PER_PAPER")
  case MaximumCoauthorsOnOnePaper extends RuntimeRankingMetric("MAXIMUM_COAUTHORS_ON_ONE_PAPER")
  case WeightedDegree extends RuntimeRankingMetric("WEIGHTED_DEGREE")
  case Coreness extends RuntimeRankingMetric("CORENESS")
  case CrossCommunityDegree extends RuntimeRankingMetric("CROSS_COMMUNITY_DEGREE")
  case CrossCommunityWeight extends RuntimeRankingMetric("CROSS_COMMUNITY_WEIGHT")
  case CommunitiesConnected extends RuntimeRankingMetric("COMMUNITIES_CONNECTED")
  case ParticipationCoefficient extends RuntimeRankingMetric("PARTICIPATION_COEFFICIENT")
}
object RuntimeRankingMetric {
  given ReadWriter[RuntimeRankingMetric] = EnumCodecs.wire(RuntimeRankingMetric.values, _.wire)
}
final case class RuntimePopulationFilter(
    topicIds: Vector[String] = Vector.empty,
    institutionIds: Vector[String] = Vector.empty,
    venueIds: Vector[String] = Vector.empty,
    metricScope: String = "population"
) derives ReadWriter
final case class RuntimeRankingEntry(
    metric: ResearcherMetricsDetail,
    bridge: Option[ResearcherBridgeMetrics],
    membership: Option[CommunityMembership],
    rankingValue: String
) derives ReadWriter
final case class RuntimeRankingPage(
    windowId: String,
    metric: RuntimeRankingMetric,
    filters: RuntimePopulationFilter,
    items: Vector[RuntimeRankingEntry],
    populationCount: Long,
    matchedCount: Long,
    truncated: Boolean,
    sourceRunId: String,
    sourceArtifactHash: String
) derives ReadWriter
final case class RuntimeBridgeRecord(
    metrics: ResearcherBridgeMetrics,
    membership: CommunityMembership,
    distinctCoauthorCount: Long
) derives ReadWriter
final case class RuntimeTemporalRecord(
    change: TemporalChange,
    fromMembership: Option[CommunityMembership],
    toMembership: Option[CommunityMembership]
) derives ReadWriter
final case class RuntimeEdgeRecord(edge: SparkCoauthorEdge, support: Vector[CoauthorEdgeSupport])
    derives ReadWriter
final case class RuntimeResearcherContext(
    researcherId: String,
    windowId: String,
    topicIds: Option[Vector[String]],
    institutionIds: Option[Vector[String]],
    venueIds: Option[Vector[String]],
    coauthorIds: Vector[String],
    coauthorsTruncated: Boolean,
    sourceRefs: Vector[SummarySourceRef],
    sourceRunId: String
) derives ReadWriter

/** Validation invoked by DomainValidation whenever an additive runtime payload is present. */
object RuntimeContractValidation {
  private def strings(xs: Vector[String]): Boolean = xs.forall(_.trim.nonEmpty) && xs.distinct == xs
  def candidate(v: ResearcherCandidate): Vector[String] = v.provenanceSummary.toVector.flatMap {
    s =>
      val counts = Vector(s.sourceIdCount, s.evidenceRefCount, s.affiliationCount, s.runIdCount)
      val lists = Vector(v.sourceIds, v.evidenceRefs, v.affiliations, v.runIds)
      Vector(
        Option.when(lists.exists(xs => !strings(xs)) || counts.zip(lists).exists { case (n, xs) =>
          n < xs.size
        })(
          "invalid-candidate-provenance-count"
        ),
        Option.when(s.truncated != counts.zip(lists).exists { case (n, xs) => n > xs.size })(
          "invalid-candidate-provenance-truncation"
        )
      ).flatten
  }
  def values(xs: Vector[RuntimeClaimValue]): Vector[String] = {
    val fields = xs.map(_.field)
    val duplicates =
      if (fields.distinct != fields) Vector("duplicate-runtime-value-field") else Vector.empty
    duplicates ++ xs.flatMap { v =>
      val forms = Vector(v.number.isDefined, v.text.isDefined, v.ids.isDefined, v.flag.isDefined)
        .count(identity)
      val numeric = v.number.forall(s =>
        try { BigDecimal(s); s.nonEmpty }
        catch { case _: NumberFormatException => false }
      )
      Vector(
        Option.when(v.field.trim.isEmpty || forms != 1)("invalid-runtime-value"),
        Option.when(!numeric)("invalid-runtime-decimal"),
        Option
          .when(v.text.exists(_.trim.isEmpty) || v.ids.exists(!strings(_)))("blank-runtime-value")
      ).flatten
    }
  }
  def query(v: RuntimeQueryOptions): Vector[String] = Vector(
    Option.when(
      !strings(v.researcherNames) || !strings(v.windowIds) || !strings(v.comparisonWindowIds)
    )("invalid-runtime-query-list"),
    Option.when(
      v.rankingMeasure.exists(_.trim.isEmpty) || v.unsupportedReason.exists(_.trim.isEmpty)
    )("blank-runtime-query-option")
  ).flatten
  def claim(v: TypedAnswerClaim): Vector[String] = values(v.values) ++ Vector(
    Option.when(v.templateId.trim.isEmpty || !strings(v.subjectIds) || !strings(v.windowIds))(
      "invalid-typed-claim"
    ),
    Option.when(v.values.isEmpty)("empty-typed-claim")
  ).flatten
  def evidence(v: RuntimeEvidence): Vector[String] = values(v.values) ++ Vector(
    Option.when(
      StableIds.parseRunId(v.runId).isLeft || !strings(v.subjectIds) || !strings(v.windowIds)
    )("invalid-runtime-evidence"),
    Option.when(v.iterations.exists(_ < 0) || v.converged.isDefined != v.iterations.isDefined)(
      "invalid-community-qualification"
    ),
    Option.when(v.metricVersion.exists(_.trim.isEmpty))("blank-metric-version")
  ).flatten
  def bundle(v: RuntimeBundleContext, itemIds: Vector[String]): Vector[String] = {
    val ids = v.deterministicEvidenceIds ++ v.semanticEvidenceIds
    Vector(
      Option.when(!strings(ids) || ids.toSet != itemIds.toSet)(
        "runtime-evidence-partition-mismatch"
      ),
      Option.when(
        v.graphRunIds.exists(StableIds.parseRunId(_).isLeft) || !strings(v.graphRunIds) || !strings(
          v.metricVersions
        )
      )("invalid-runtime-bundle-provenance"),
      Option.when(v.retrievalMode == RetrievalMode.Vector && v.deterministicEvidenceIds.nonEmpty)(
        "vector-mode-deterministic-evidence"
      )
    ).flatten
  }
}
