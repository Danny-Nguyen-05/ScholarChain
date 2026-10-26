package edu.uic.cs441.scholarchain.core

import scala.collection.mutable.ArrayBuffer

/** Validation of the versioned Phase 6 wire records. Cross-row invariants such as edge support
  * counts and endpoint existence remain Spark run gates.
  */
object SparkAnalyticsValidation {
  private type Errors = ArrayBuffer[String]

  private def evaluate[A](value: A)(body: Errors => Unit): Either[ConfigError, A] = {
    val errors = ArrayBuffer.empty[String]
    body(errors)
    if (errors.isEmpty) Right(value) else Left(ConfigError(errors.toVector))
  }

  private def nonBlank(value: String, field: String, errors: Errors): Unit =
    if (value.trim.isEmpty) errors += s"$field must be non-blank"

  private def nonNegative(value: Long, field: String, errors: Errors): Unit =
    if (value < 0) errors += s"$field must be >= 0"

  private def fraction(value: Double, field: String, errors: Errors): Unit =
    if (!value.isFinite || value < 0 || value > 1) errors += s"$field must be in [0,1]"

  private def finite(value: Double, field: String, errors: Errors): Unit =
    if (!value.isFinite) errors += s"$field must be finite"

  private def researcher(value: String, errors: Errors): Unit =
    if (StableIds.parseResearcherId(value).isLeft) errors += s"invalid researcher ID: $value"

  private def id(value: String, prefix: String, errors: Errors): Unit =
    if (!value.matches(java.util.regex.Pattern.quote(prefix) + ":[0-9a-f]{64}"))
      errors += s"invalid $prefix ID: $value"

  private def context(value: SparkRecordContext, errors: Errors): Unit = {
    if (!SchemaVersions.supportedSparkAnalytics.contains(value.schemaVersion))
      errors += s"unsupported Spark analytics schema: ${value.schemaVersion}"
    if (StableIds.parseRunId(value.runId).isLeft) errors += "invalid runId"
    value.windowId.foreach { window =>
      if (!window.matches("[a-z0-9][a-z0-9._-]*")) errors += s"invalid windowId: $window"
    }
    val lineage = value.lineage
    if (StableIds.parseRunId(lineage.hadoopRunId).isLeft) errors += "invalid Hadoop run ID"
    if (StableIds.parseRunId(lineage.entityResolutionRunId).isLeft)
      errors += "invalid entity-resolution run ID"
    nonBlank(lineage.hadoopSnapshot, "hadoopSnapshot", errors)
    nonBlank(lineage.entityResolutionPolicyVersion, "entityResolutionPolicyVersion", errors)
    if (!lineage.entityResolutionPolicyHash.matches("[0-9a-f]{64}"))
      errors += "entityResolutionPolicyHash must be SHA-256 hex"
    lineage.sourceWorkIds.foreach { work =>
      if (StableIds.parseWorkId(work).isLeft) errors += s"invalid source work ID: $work"
    }
    lineage.sourceMentionIds.foreach { mention =>
      if (StableIds.parseMentionId(mention).isLeft) errors += s"invalid source mention ID: $mention"
    }
  }

  private def windowed(value: SparkRecordContext, errors: Errors): Unit = {
    context(value, errors)
    if (value.windowId.isEmpty) errors += "windowId is required"
  }

  /** Runtime evidence can retain an original source context without manufacturing another row. */
  def check(value: SparkRecordContext): Either[ConfigError, SparkRecordContext] =
    evaluate(value)(errors => context(value, errors))

  def check(value: ResearcherMetricsDetail): Either[ConfigError, ResearcherMetricsDetail] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherId, errors)
      nonBlank(value.policyVersion, "policyVersion", errors)
      Vector(
        "publicationCount" -> value.publicationCount,
        "distinctCoauthorCount" -> value.distinctCoauthorCount,
        "totalCoauthorOccurrences" -> value.totalCoauthorOccurrences,
        "maximumCoauthorsOnOnePaper" -> value.maximumCoauthorsOnOnePaper,
        "maxTeamWorkTieCount" -> value.maxTeamWorkTieCount,
        "weightedDegree" -> value.weightedDegree
      ).foreach((field, number) => nonNegative(number, field, errors))
      finite(value.averageCoauthorsPerPaper, "averageCoauthorsPerPaper", errors)
      if (value.averageCoauthorsPerPaper < 0)
        errors += "averageCoauthorsPerPaper must be >= 0"
      val publications = value.publicationCount
      val distinct = value.distinctCoauthorCount
      val total = value.totalCoauthorOccurrences
      val maximum = value.maximumCoauthorsOnOnePaper
      if (distinct > total)
        errors += "distinctCoauthorCount cannot exceed totalCoauthorOccurrences"
      if (maximum > distinct)
        errors += "maximumCoauthorsOnOnePaper cannot exceed distinctCoauthorCount"
      if (maximum > total)
        errors += "maximumCoauthorsOnOnePaper cannot exceed totalCoauthorOccurrences"
      if ((total == 0) != (distinct == 0))
        errors += "zero occurrences and zero distinct coauthors must agree"
      if ((total == 0) != (maximum == 0))
        errors += "zero occurrences and zero maximum must agree"
      if (total == 0 && value.averageCoauthorsPerPaper != 0.0)
        errors += "zero occurrences require exactly zero averageCoauthorsPerPaper"
      if (publications > 0) {
        val expected = total.toDouble / publications.toDouble
        if (
          !value.averageCoauthorsPerPaper.isFinite ||
          math.abs(value.averageCoauthorsPerPaper - expected) >
            math.max(1e-12, 4 * math.ulp(expected))
        ) errors += "averageCoauthorsPerPaper must equal totalCoauthorOccurrences / publicationCount"
        if (BigInt(total) > BigInt(publications) * BigInt(maximum))
          errors += "totalCoauthorOccurrences cannot exceed publicationCount times maximumCoauthorsOnOnePaper"
        if (value.maxTeamWorkIds.isEmpty)
          errors += "positive publications require maxTeamWorkIds"
        if (value.maxTeamWorkTieCount < 1 || value.maxTeamWorkTieCount > publications)
          errors += "maxTeamWorkTieCount must be between 1 and publicationCount"
      } else if (value.maxTeamWorkIds.nonEmpty || value.maxTeamWorkTieCount != 0)
        errors += "zero publications require no max-team work IDs or ties"
      if (value.weightedDegree != value.totalCoauthorOccurrences)
        errors += "weightedDegree must equal totalCoauthorOccurrences"
      if (
        publications == 0 &&
        (total != 0 || distinct != 0 || maximum != 0 ||
          value.averageCoauthorsPerPaper != 0.0 || value.weightedDegree != 0)
      )
        errors += "zero publications require zero collaboration values"
      if (value.maxTeamWorkIds.size > value.maxTeamWorkTieCount)
        errors += "maxTeamWorkTieCount must cover retained work IDs"
      if (value.maxTeamWorkIds != value.maxTeamWorkIds.distinct.sorted)
        errors += "maxTeamWorkIds must be sorted and unique"
      value.maxTeamWorkIds.foreach(work =>
        if (StableIds.parseWorkId(work).isLeft) errors += s"invalid max-team work ID: $work"
      )
      id(value.componentId, "component", errors)
      value.communityId.foreach(id(_, "community", errors))
      value.coreness.foreach { number =>
        if (number < 0) errors += "coreness must be >= 0"
        if (number.toLong > distinct) errors += "coreness cannot exceed distinctCoauthorCount"
      }
    }

  def check(value: ResearcherBridgeMetrics): Either[ConfigError, ResearcherBridgeMetrics] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherId, errors)
      nonBlank(value.policyVersion, "policyVersion", errors)
      nonNegative(value.crossCommunityDegree, "crossCommunityDegree", errors)
      nonNegative(value.crossCommunityWeight, "crossCommunityWeight", errors)
      nonNegative(value.communitiesConnected, "communitiesConnected", errors)
      fraction(value.participationCoefficient, "participationCoefficient", errors)
      if (value.communitiesConnected > value.crossCommunityDegree)
        errors += "communitiesConnected exceeds crossCommunityDegree"
      if (value.crossCommunityWeight < value.crossCommunityDegree)
        errors += "crossCommunityWeight cannot be less than crossCommunityDegree"
      if (value.crossCommunityDegree == 0 && value.participationCoefficient != 0.0)
        errors += "zero crossCommunityDegree requires zero participationCoefficient"
    }

  def check(value: ComponentMembership): Either[ConfigError, ComponentMembership] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherId, errors)
      id(value.componentId, "component", errors)
    }

  def check(value: ComponentSummary): Either[ConfigError, ComponentSummary] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      id(value.componentId, "component", errors)
      researcher(value.minimumResearcherId, errors)
      if (value.size < 1) errors += "component size must be >= 1"
      fraction(value.largestComponentFraction, "largestComponentFraction", errors)
      nonNegative(value.singletonCount, "singletonCount", errors)
    }

  def check(value: CommunityMembership): Either[ConfigError, CommunityMembership] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherId, errors)
      id(value.communityId, "community", errors)
      nonNegative(value.iterations, "iterations", errors)
    }

  def check(value: CommunitySummary): Either[ConfigError, CommunitySummary] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      id(value.communityId, "community", errors)
      if (value.size < 1) errors += "community size must be >= 1"
      nonNegative(value.iterations, "iterations", errors)
      nonNegative(value.finalChangedCount, "finalChangedCount", errors)
      if (value.converged && value.finalChangedCount != 0)
        errors += "converged community requires zero finalChangedCount"
    }

  def check(value: CrossCommunityEdge): Either[ConfigError, CrossCommunityEdge] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      id(value.communityA, "community", errors)
      id(value.communityB, "community", errors)
      if (value.communityA >= value.communityB) errors += "communities must be ordered and distinct"
      if (value.edgeCount < 1 || value.summedWeight < 1)
        errors += "cross-community edge count and weight must be positive"
      if (value.summedWeight < value.edgeCount)
        errors += "summedWeight cannot be less than edgeCount"
    }

  def check(value: CoauthorEdgeSupport): Either[ConfigError, CoauthorEdgeSupport] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      if (
        StableIds.parseSparkCoauthorEdgeId(value.edgeId).isLeft &&
        StableIds.parseCoauthorEdgeId(value.edgeId).isLeft
      ) errors += "invalid edgeId"
      if (StableIds.parseWorkId(value.workId).isLeft) errors += "invalid workId"
      value.year.foreach(year => if (year < 1 || year > 9999) errors += "year outside 1..9999")
    }

  def check(value: SparkCoauthorEdge): Either[ConfigError, SparkCoauthorEdge] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherA, errors)
      researcher(value.researcherB, errors)
      if (value.researcherA >= value.researcherB) errors += "edge researchers must be ordered"
      val expected = value.context.windowId.flatMap(window =>
        StableIds
          .sparkCoauthorEdgeId(
            value.researcherA,
            value.researcherB,
            SparkWindow(window, value.windowStartYear, value.windowEndYear, None),
            value.policyVersion
          )
          .toOption
      )
      if (!expected.contains(value.edgeId))
        errors += "edgeId does not match endpoints and window bounds"
      if (value.jointPublicationCount < 1) errors += "jointPublicationCount must be >= 1"
      if (
        value.firstCollaborationYear
          .zip(value.lastCollaborationYear)
          .exists((first, last) => first > last)
      ) errors += "reversed collaboration years"
      if (value.firstCollaborationYear.isEmpty != value.lastCollaborationYear.isEmpty)
        errors += "first and last years must both be present or absent"
      if (
        value.representativeWorkIds.isEmpty ||
        value.representativeWorkIds.distinct.size != value.representativeWorkIds.size ||
        value.representativeWorkIds.size.toLong > value.jointPublicationCount
      )
        errors += "representativeWorkIds must be distinct, nonempty and bounded by count"
      value.representativeWorkIds.foreach(work =>
        if (StableIds.parseWorkId(work).isLeft) errors += "invalid representative work ID"
      )
    }

  def check(value: PathEvidence): Either[ConfigError, PathEvidence] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      id(value.pathEvidenceId, "path-evidence", errors)
      researcher(value.sourceResearcherId, errors)
      researcher(value.targetResearcherId, errors)
      if (value.maxHops < 1) errors += "maxHops must be >= 1"
      value.orderedResearcherIds.foreach(researcher(_, errors))
      value.hops.foreach { hop =>
        researcher(hop.fromResearcherId, errors)
        researcher(hop.toResearcherId, errors)
        if (
          StableIds.parseSparkCoauthorEdgeId(hop.edgeId).isLeft &&
          StableIds.parseCoauthorEdgeId(hop.edgeId).isLeft
        ) errors += "invalid path edgeId"
        if (hop.jointPublicationCount < 1) errors += "path hop weight must be >= 1"
        hop.representativeWorkIds.foreach(work =>
          if (StableIds.parseWorkId(work).isLeft) errors += "invalid path work ID"
        )
      }
      value.status match {
        case PathStatus.Found =>
          if (value.hopCount.exists(_ > value.maxHops))
            errors += "found path hopCount cannot exceed maxHops"
          if (value.sourceResearcherId == value.targetResearcherId)
            errors += "found path endpoints must differ"
          if (value.orderedResearcherIds.distinct.size != value.orderedResearcherIds.size)
            errors += "found path cannot repeat researchers"
          if (
            value.hopCount != Some(value.hops.size) ||
            value.orderedResearcherIds.size != value.hops.size + 1 ||
            value.orderedResearcherIds.headOption != Some(value.sourceResearcherId) ||
            value.orderedResearcherIds.lastOption != Some(value.targetResearcherId)
          )
            errors += "found path shape is inconsistent"
          value.hops.zipWithIndex.foreach { case (hop, index) =>
            if (
              value.orderedResearcherIds.lift(index) != Some(hop.fromResearcherId) ||
              value.orderedResearcherIds.lift(index + 1) != Some(hop.toResearcherId)
            )
              errors += "path hop endpoints do not follow ordered nodes"
          }
        case _ =>
          if (
            value.hopCount.nonEmpty || value.hops.nonEmpty ||
            value.orderedResearcherIds.nonEmpty
          )
            errors += "unfound path must have no hop evidence"
      }
    }

  def check(value: PathLengthEstimate): Either[ConfigError, PathLengthEstimate] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      id(value.componentId, "component", errors)
      nonBlank(value.method, "method", errors)
      if (value.sampleSourceCount < 1) errors += "sampleSourceCount must be >= 1"
      nonNegative(value.reachedPairCount, "reachedPairCount", errors)
      if (!value.meanDistance.isFinite || value.meanDistance < 0) errors += "invalid meanDistance"
      if (!value.effectiveDiameterP90.isFinite || value.effectiveDiameterP90 < 0)
        errors += "invalid effectiveDiameterP90"
    }

  def check(value: TemporalChange): Either[ConfigError, TemporalChange] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      researcher(value.researcherId, errors)
      nonBlank(value.fromWindowId, "fromWindowId", errors)
      nonBlank(value.toWindowId, "toWindowId", errors)
      if (
        value.fromWindowId == value.toWindowId ||
        value.context.windowId != Some(value.toWindowId)
      ) errors += "invalid temporal window pair"
      if (!value.fromPresent && !value.toPresent)
        errors += "temporal change requires a researcher in at least one window"
      val deltas = Vector(
        value.deltaDistinctCoauthors,
        value.deltaAverageCoauthorsPerPaper,
        value.deltaMaximumCoauthorsOnOnePaper,
        value.deltaComponentSize,
        value.deltaCrossCommunityDegree,
        value.deltaCrossCommunityWeight,
        value.deltaCommunitiesConnected,
        value.deltaParticipationCoefficient
      )
      if (value.fromPresent && value.toPresent && deltas.exists(_.isEmpty))
        errors += "both-present temporal change requires every delta"
      if ((!value.fromPresent || !value.toPresent) && deltas.exists(_.nonEmpty))
        errors += "entry or exit temporal change must leave deltas absent"
      value.deltaAverageCoauthorsPerPaper.foreach(
        finite(_, "deltaAverageCoauthorsPerPaper", errors)
      )
      value.deltaParticipationCoefficient.foreach(
        finite(_, "deltaParticipationCoefficient", errors)
      )
      value.communityJaccardOverlap.foreach(fraction(_, "communityJaccardOverlap", errors))
      value.previousCommunityId.foreach(id(_, "community", errors))
      value.currentCommunityId.foreach(id(_, "community", errors))
      if (!value.fromPresent && value.previousCommunityId.nonEmpty)
        errors += "previousCommunityId requires fromPresent"
      if (!value.toPresent && value.currentCommunityId.nonEmpty)
        errors += "currentCommunityId requires toPresent"
      if ((!value.fromPresent || !value.toPresent) && value.communityJaccardOverlap.nonEmpty)
        errors += "community overlap requires presence in both windows"
      if (value.enteredLargestComponent && value.leftLargestComponent)
        errors += "cannot enter and leave largest component together"
    }

  private def refs(value: Vector[SummarySourceRef], errors: Errors): Unit =
    value.foreach { ref =>
      nonBlank(ref.table, "source table", errors)
      nonBlank(ref.rowKey, "source rowKey", errors)
      nonBlank(ref.field, "source field", errors)
    }

  def check(value: SemanticSummary): Either[ConfigError, SemanticSummary] =
    evaluate(value) { errors =>
      windowed(value.context, errors)
      val expected = value.context.windowId.flatMap(window =>
        StableIds
          .sparkSemanticSummaryId(
            value.entityId,
            value.policyVersion,
            window,
            value.summaryType,
            value.text
          )
          .toOption
      )
      if (!expected.contains(value.summaryId))
        errors += "summaryId does not match entity, policy, window, type and text"
      if (
        !Set("researcher-profile", "community", "collaboration-path", "paper")
          .contains(value.summaryType)
      ) errors += "unsupported summaryType"
      nonBlank(value.entityId, "entityId", errors)
      value.summaryType match {
        case "researcher-profile" => researcher(value.entityId, errors)
        case "community"          => id(value.entityId, "community", errors)
        case "collaboration-path" => id(value.entityId, "path-evidence", errors)
        case "paper" =>
          if (StableIds.parseWorkId(value.entityId).isLeft) errors += "invalid paper work ID"
        case _ => ()
      }
      nonBlank(value.text, "text", errors)
      if (value.sourceReferences.isEmpty) errors += "summary requires source references"
      refs(value.sourceReferences, errors)
      value.abstractTextIds.foreach(id =>
        if (StableIds.parseChunkOrProfileId(id).isLeft) errors += "invalid abstractTextId"
      )
    }

  def check(value: IntegrityViolation): Either[ConfigError, IntegrityViolation] =
    evaluate(value) { errors =>
      context(value.context, errors)
      nonBlank(value.code, "code", errors)
      nonBlank(value.detail, "detail", errors)
      refs(value.evidenceRefs, errors)
    }

  def check(value: LoadManifest): Either[ConfigError, LoadManifest] =
    evaluate(value) { errors =>
      context(value.context, errors)
      if (!Set("neptune", "dynamodb", "s3vectors", "s3").contains(value.targetStore))
        errors += "unsupported targetStore"
      nonBlank(value.logicalDataset, "logicalDataset", errors)
      if (value.paths.isEmpty || value.paths.exists(_.trim.isEmpty))
        errors += "load paths must be nonempty"
      if (value.format != "parquet") errors += "load format must be parquet"
      nonNegative(value.rowCount, "rowCount", errors)
      if (value.keyColumns.isEmpty || value.keyColumns.exists(_.trim.isEmpty))
        errors += "keyColumns must be nonempty"
      if (!value.sortedRowsSha256.matches("[0-9a-f]{64}"))
        errors += "sortedRowsSha256 must be SHA-256 hex"
      if (value.windows.isEmpty) errors += "windows must be nonempty"
      nonBlank(value.intendedLoaderOwner, "intendedLoaderOwner", errors)
    }

  def check(value: SparkCounter): Either[ConfigError, SparkCounter] =
    evaluate(value) { errors =>
      context(value.context, errors)
      nonBlank(value.name, "name", errors)
      nonNegative(value.value, "value", errors)
    }
}
