package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*

/** Reads exact stored metrics. Population filters never become semantic nearest-neighbor filters.
  */
final class CollaborationMetricsAgent(
    metrics: ResearcherMetricStore,
    artifacts: RuntimeArtifactStore,
    config: RuntimeConfig
) {
  import RuntimeEvidenceItems.*
  require(RuntimeConfigValidation.check(config).isEmpty)
  def run(input: RetrievalInput): RetrievalResult = RuntimeRead.stage("metrics", input) {
    val plan = input.plan
    val window = RuntimeRead.window(input, config)
    val options = plan.runtime.get
    val ranking = plan.operations.exists(
      Set(QueryOperation.ResearcherRanking, QueryOperation.MaximumTeamSize)
    ) && input.candidates.isEmpty
    if (ranking) {
      val selected = plan.rankingMetric.getOrElse(
        throw RetrievalProblem("unsupported", "ranking-metric-missing")
      )
      val metric = RuntimeRankingMetric.values
        .find(_.wire == selected.wire)
        .getOrElse(throw RetrievalProblem("unsupported", "ranking-metric-not-stored"))
      val page = RuntimeRead.value(
        artifacts.rank(
          window,
          metric,
          RuntimeRead.filters(plan),
          math.min(plan.graphLimit, config.retrieval.graphLimit)
        )
      )
      RuntimeRead.check(
        page.windowId == window && page.metric == metric && page.filters == RuntimeRead.filters(
          plan
        ) &&
          page.items.size <= math.min(plan.graphLimit, config.retrieval.graphLimit) && page.items
            .forall(e =>
              e.metric.context.windowId.contains(
                window
              ) && e.metric.context.runId == page.sourceRunId && SparkAnalyticsValidation
                .check(e.metric)
                .isRight
            ),
        "ranking-source-mismatch"
      )
      if (page.items.isEmpty) throw RetrievalProblem("missing", "ranking-population-empty")
      val scope =
        s"Stored $window ${metric.wire}; authoritative population filters=${CoreJson.compact(page.filters)}; population=${page.populationCount}; matched=${page.matchedCount}; returned=${page.items.size}; top-K truncated=${page.truncated}."
      val items = page.items.zipWithIndex.map { (entry, index) =>
        val extra = Vector(
          number("rank", index.toLong + 1),
          RuntimeClaimValue("rankingValue", number = Some(entry.rankingValue)),
          text("rankingMetric", metric.wire),
          text("sourceRankingScope", scope)
        ) ++ conversion(input, entry.metric)
        RuntimeEvidenceItems.metric(
          input,
          entry.metric,
          config,
          metricValues(entry.metric) ++ extra,
          "ranking",
          entry.membership
        )
      }
      RetrievalOutput("metrics", items, Some(scope), page.truncated)
    } else {
      if (
        plan.topicFilters.nonEmpty || plan.institutionFilters.nonEmpty || plan.venueFilters.nonEmpty
      )
        throw RetrievalProblem("unsupported", "filtered-researcher-metric-not-stored")
      if (input.candidates.isEmpty) throw RetrievalProblem("missing", "researcher-required")
      val items = input.candidates.flatMap { candidate =>
        val m = RuntimeRead.metric(metrics, candidate.researcherId, window)
        val membership = m.qualifications.obj
          .get("communityMembership")
          .filter(_ != ujson.Null)
          .map(upickle.default.read[CommunityMembership](_))
        membership.foreach(c =>
          RuntimeRead.check(
            c.researcherId == candidate.researcherId && c.context.windowId.contains(
              window
            ) && c.context.runId == m.record.runId && SparkAnalyticsValidation.check(c).isRight,
            "community-source-mismatch"
          )
        )
        val estimate = m.qualifications.obj
          .get("pathLengthEstimate")
          .filter(_ != ujson.Null)
          .map(upickle.default.read[PathLengthEstimate](_))
        estimate.foreach(e =>
          RuntimeRead.check(
            e.componentId == m.detail.componentId && e.context.windowId.contains(
              window
            ) && e.context.runId == m.record.runId && SparkAnalyticsValidation.check(e).isRight,
            "distance-estimate-source-mismatch"
          )
        )
        val item = RuntimeEvidenceItems.metric(
          input,
          m.detail,
          config,
          metricValues(m.detail) ++ conversion(input, m.detail),
          membership = membership
        )
        // Component distance estimates qualify only their own evidence item. Exact researcher
        // metrics remain byte-for-byte unchanged when this optional source estimate is present.
        Vector(item) ++ estimate.toVector.map { e =>
          make(
            input,
            "distance-estimate",
            Vector(e.componentId),
            Vector(window),
            e.context.runId,
            Vector(
              text("componentId", e.componentId),
              decimal("effectiveDiameterP90", e.effectiveDiameterP90),
              text("distanceMethod", e.method),
              flag("distanceP90Approximate", true)
            ),
            Vector(
              ref("metrics/type=path_length_estimate", e.componentId, "effectiveDiameterP90"),
              ref("metrics/type=path_length_estimate", e.componentId, "method")
            ),
            approximate = true
          )
        }
      }
      RetrievalOutput("metrics", items)
    }
  }
  private def conversion(
      input: RetrievalInput,
      metric: ResearcherMetricsDetail
  ): Vector[RuntimeClaimValue] =
    if (input.plan.runtime.exists(_.authorCountConversion))
      Vector(
        RuntimeClaimValue(
          "maximumTotalAuthors",
          number = Some((BigInt(metric.maximumCoauthorsOnOnePaper) + 1).toString)
        ),
        text("authorCountConversion", "stored maximum coauthors + 1")
      )
    else Vector.empty
}
