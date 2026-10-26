package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*

/** Community qualifications travel with each result rather than being inferred from a score. */
final class CommunityAnalystAgent(
    graph: GraphReader,
    metrics: ResearcherMetricStore,
    artifacts: RuntimeArtifactStore,
    config: RuntimeConfig
) {
  import RuntimeEvidenceItems.*
  require(RuntimeConfigValidation.check(config).isEmpty)
  def run(input: RetrievalInput): RetrievalResult = RuntimeRead.stage("community", input) {
    val plan = input.plan
    val window = RuntimeRead.window(input, config)
    val limit = math.min(plan.graphLimit, config.retrieval.graphLimit)
    if (plan.operations.contains(QueryOperation.BridgeRanking)) {
      val measure = plan.runtime.flatMap(_.rankingMeasure).getOrElse(config.defaultRankingMeasure)
      val selected = RuntimeRankingMetric.values
        .find(_.wire == measure)
        .filter(m =>
          Set(
            RuntimeRankingMetric.CrossCommunityDegree,
            RuntimeRankingMetric.CrossCommunityWeight,
            RuntimeRankingMetric.CommunitiesConnected,
            RuntimeRankingMetric.ParticipationCoefficient
          )(m)
        )
        .getOrElse(throw RetrievalProblem("unsupported", "bridge-measure-not-stored"))
      val page =
        RuntimeRead.value(artifacts.rank(window, selected, RuntimeRead.filters(plan), limit))
      RuntimeRead.check(
        page.metric == selected && page.windowId == window && page.filters == RuntimeRead.filters(
          plan
        ) && page.items.size <= limit,
        "bridge-ranking-source-mismatch"
      )
      if (page.items.isEmpty) throw RetrievalProblem("missing", "bridge-population-empty")
      val scope =
        s"Stored $window ${selected.wire}; authoritative population filters=${CoreJson.compact(page.filters)}; population=${page.populationCount}; matched=${page.matchedCount}; returned=${page.items.size}; top-K truncated=${page.truncated}."
      val items = page.items.zipWithIndex.map { (entry, index) =>
        val b = entry.bridge.getOrElse(throw RetrievalProblem("missing", "bridge-row-missing"))
        val membership = entry.membership.getOrElse(
          throw RetrievalProblem("missing", "community-qualification-missing")
        )
        RuntimeRead.check(
          b.context.runId == page.sourceRunId && entry.metric.context.runId == page.sourceRunId &&
            b.researcherId == entry.metric.researcherId && b.context.windowId.contains(window) &&
            entry.metric.context.windowId
              .contains(window) && SparkAnalyticsValidation.check(entry.metric).isRight,
          "bridge-ranking-run-mismatch"
        )
        bridge(
          input,
          RuntimeBridgeRecord(b, membership, entry.metric.distinctCoauthorCount),
          window,
          Vector(
            number("rank", index.toLong + 1),
            RuntimeClaimValue("rankingValue", number = Some(entry.rankingValue)),
            text("rankingMeasure", selected.wire),
            text("sourceRankingScope", scope)
          )
        )
      }
      RetrievalOutput("community", items, Some(scope), page.truncated)
    } else if (plan.operations.contains(QueryOperation.TemporalComparison)) {
      if (
        plan.topicFilters.nonEmpty || plan.institutionFilters.nonEmpty || plan.venueFilters.nonEmpty
      )
        throw RetrievalProblem("unsupported", "filtered-temporal-metric-not-stored")
      val windows = plan.runtime.get.comparisonWindowIds
      if (windows.size != 2 || !windows.forall(config.windowIds.contains))
        throw RetrievalProblem("unsupported", "temporal-comparison-requires-two-stored-windows")
      val items = input.candidates.map { candidate =>
        val record = RuntimeRead.value(
          artifacts.temporalChange(candidate.researcherId, windows.head, windows(1))
        )
        val change = record.change
        RuntimeRead.check(
          change.researcherId == candidate.researcherId && change.fromWindowId == windows.head && change.toWindowId == windows(
            1
          ) && SparkAnalyticsValidation.check(change).isRight,
          "temporal-source-mismatch"
        )
        if (
          change.previousCommunityId.nonEmpty && record.fromMembership.isEmpty || change.currentCommunityId.nonEmpty && record.toMembership.isEmpty
        )
          throw RetrievalProblem("missing", "temporal-community-qualification-missing")
        RuntimeRead.check(
          record.fromMembership.forall(m =>
            m.context.windowId.contains(windows.head) && change.previousCommunityId.contains(
              m.communityId
            )
          ) &&
            record.toMembership.forall(m =>
              m.context.windowId.contains(windows(1)) && change.currentCommunityId.contains(
                m.communityId
              )
            ),
          "temporal-community-binding-mismatch"
        )
        val memberships = record.fromMembership.toVector ++ record.toMembership.toVector
        RuntimeRead.check(
          memberships.forall(m =>
            m.researcherId == change.researcherId && m.context.runId == change.context.runId && windows
              .contains(m.context.windowId.getOrElse("")) && SparkAnalyticsValidation
              .check(m)
              .isRight
          ),
          "temporal-membership-mismatch"
        )
        val values = Vector(
          flag("fromPresent", change.fromPresent),
          flag("toPresent", change.toPresent),
          flag("enteredLargestComponent", change.enteredLargestComponent),
          flag("leftLargestComponent", change.leftLargestComponent)
        ) ++
          change.deltaDistinctCoauthors.map(number("deltaDistinctCoauthors", _)) ++
          change.deltaAverageCoauthorsPerPaper.map(decimal("deltaAverageCoauthorsPerPaper", _)) ++
          change.deltaMaximumCoauthorsOnOnePaper.map(
            number("deltaMaximumCoauthorsOnOnePaper", _)
          ) ++
          change.deltaComponentSize.map(number("deltaComponentSize", _)) ++
          change.deltaCrossCommunityDegree.map(number("deltaCrossCommunityDegree", _)) ++
          change.deltaCrossCommunityWeight.map(number("deltaCrossCommunityWeight", _)) ++
          change.deltaCommunitiesConnected.map(number("deltaCommunitiesConnected", _)) ++
          change.deltaParticipationCoefficient.map(decimal("deltaParticipationCoefficient", _)) ++
          change.communityJaccardOverlap.map(decimal("communityJaccardOverlap", _)) ++
          change.previousCommunityId.map(
            text("previousCommunityId", _)
          ) ++ change.currentCommunityId.map(text("currentCommunityId", _)) ++
          memberships.flatMap(m =>
            Vector(
              flag(s"converged:${m.context.windowId.get}", m.converged),
              number(s"iterations:${m.context.windowId.get}", m.iterations)
            )
          )
        make(
          input,
          "temporal",
          Vector(change.researcherId),
          windows,
          change.context.runId,
          values,
          Vector(
            ref(
              "metrics/type=temporal_changes",
              StorageKeys.composite(change.researcherId, windows.head, windows(1))
            )
          ),
          converged = Option.when(memberships.nonEmpty)(memberships.forall(_.converged)),
          iterations = memberships.map(_.iterations).maxOption
        )
      }
      if (items.isEmpty) throw RetrievalProblem("missing", "researcher-required")
      RetrievalOutput("community", items)
    } else {
      if (
        plan.topicFilters.nonEmpty || plan.institutionFilters.nonEmpty || plan.venueFilters.nonEmpty
      )
        throw RetrievalProblem("unsupported", "filtered-community-metric-not-stored")
      if (input.candidates.isEmpty) throw RetrievalProblem("missing", "researcher-required")
      val all = input.candidates.flatMap { candidate =>
        val m = RuntimeRead.metric(metrics, candidate.researcherId, window)
        val record = RuntimeRead.value(artifacts.bridgeMetrics(candidate.researcherId, window))
        val bridgeItem = bridge(input, record, window)
        RuntimeRead.check(
          record.metrics.context.runId == m.record.runId && m.detail.communityId
            .contains(record.membership.communityId),
          "metric-community-mismatch"
        )
        val id = record.membership.communityId
        val summary = RuntimeRead.value(artifacts.communitySummary(id, window))
        RuntimeRead.check(
          summary.communityId == id && summary.context.windowId
            .contains(window) && summary.context.runId == m.record.runId &&
            summary.converged == record.membership.converged && summary.iterations == record.membership.iterations && SparkAnalyticsValidation
              .check(summary)
              .isRight,
          "community-summary-mismatch"
        )
        val members = RuntimeRead.value(graph.communityMembers(id, window, limit))
        val cross = RuntimeRead.value(graph.crossCommunityEdges(id, window, limit))
        RuntimeRead.check(
          members.size <= limit && members.distinct == members && members.forall(
            StableIds.parseResearcherId(_).isRight
          ) && cross.items.size <= limit,
          "community-result-limit"
        )
        members.foreach { member =>
          val stored = RuntimeRead.metric(metrics, member, window)
          RuntimeRead.check(
            stored.record.runId == m.record.runId && stored.detail.communityId.contains(id),
            "community-member-source-mismatch"
          )
        }
        val crossRecords = cross.items.map { neighbor =>
          RuntimeRead.check(
            neighbor.edgeType == "COAUTHORED_WITH",
            "cross-community-edge-type-mismatch"
          )
          val record = RuntimeRead.value(artifacts.edgeSupport(neighbor.edgeId, window))
          val edgeRow = record.edge
          RuntimeRead.check(
            edgeRow.context.windowId.contains(window) && edgeRow.context.runId == m.record.runId &&
              Set(edgeRow.researcherA, edgeRow.researcherB)(neighbor.nodeId),
            "cross-community-edge-source-mismatch"
          )
          val inside =
            if (edgeRow.researcherA == neighbor.nodeId) edgeRow.researcherB else edgeRow.researcherA
          val insideMetric = RuntimeRead.metric(metrics, inside, window)
          val outsideMetric = RuntimeRead.metric(metrics, neighbor.nodeId, window)
          RuntimeRead.check(
            insideMetric.record.runId == m.record.runId && outsideMetric.record.runId == m.record.runId &&
              insideMetric.detail.communityId.contains(id) && outsideMetric.detail.communityId
                .exists(_ != id),
            "cross-community-membership-mismatch"
          )
          edge(input, record) // Validate exact support binding, work count and source windows.
          record
        }
        RuntimeRead.check(
          cross.items.map(_.edgeId).distinct.size == cross.items.size,
          "duplicate-cross-community-edge"
        )
        val neighbors = cross.items.map(_.nodeId).distinct
        val neighborCommunities = neighbors
          .map(n => RuntimeRead.metric(metrics, n, window))
          .flatMap(_.detail.communityId)
          .filterNot(_ == id)
          .distinct
          .sorted
        val truncated =
          members.size.toLong < summary.size || cross.cursor.nonEmpty || cross.items.size == limit
        val item = make(
          input,
          "community",
          Vector(candidate.researcherId),
          Vector(window),
          summary.context.runId,
          Vector(
            text("communityId", id),
            number("size", summary.size),
            ids("selectedMemberIds", members),
            number("selectedCrossCommunityEdgeCount", cross.items.size),
            ids("neighborCommunityIds", neighborCommunities),
            flag("truncated", truncated),
            text(
              "communityQualification",
              if (summary.converged) "converged" else "iteration-limited"
            )
          ),
          Vector(
            ref("metrics/type=community_summaries", id),
            ref("metrics/type=communities", candidate.researcherId)
          ) ++ crossRecords.flatMap(r =>
            Vector(ref("edges/type=coauthored_with", r.edge.edgeId)) ++
              r.support.map(s =>
                ref("edges/type=coauthored_with_support", StorageKeys.support(s.edgeId, s.workId))
              )
          ),
          converged = Some(summary.converged),
          iterations = Some(summary.iterations)
        )
        Vector(item, bridgeItem)
      }
      RetrievalOutput(
        "community",
        all,
        truncated = all.exists(
          _.runtime.get.values.exists(v => v.field == "truncated" && v.flag.contains(true))
        )
      )
    }
  }
  private def bridge(
      input: RetrievalInput,
      record: RuntimeBridgeRecord,
      window: String,
      extra: Vector[RuntimeClaimValue] = Vector.empty
  ): EvidenceItem = {
    val b = record.metrics; val m = record.membership
    RuntimeRead.check(
      b.researcherId == m.researcherId && b.context.windowId.contains(window) && m.context.windowId
        .contains(window) &&
        b.context.runId == m.context.runId && SparkAnalyticsValidation
          .check(b)
          .isRight && SparkAnalyticsValidation.check(m).isRight,
      "bridge-source-mismatch"
    )
    make(
      input,
      "bridge",
      Vector(b.researcherId),
      Vector(window),
      b.context.runId,
      Vector(
        number("crossCommunityDegree", b.crossCommunityDegree),
        number("crossCommunityWeight", b.crossCommunityWeight),
        number("communitiesConnected", b.communitiesConnected),
        decimal("participationCoefficient", b.participationCoefficient),
        number("distinctCoauthorCount", record.distinctCoauthorCount),
        text("communityId", m.communityId),
        text("communityQualification", if (m.converged) "converged" else "iteration-limited")
      ) ++ extra,
      Vector(
        ref("metrics/type=bridges", b.researcherId),
        ref("metrics/type=communities", m.researcherId)
      ),
      Some(b.policyVersion),
      Some(m.converged),
      Some(m.iterations)
    )
  }
}
