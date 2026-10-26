package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import scala.util.control.NonFatal

enum ResolverResult {
  case Resolved(candidates: Vector[ResearcherCandidate])
  case Ambiguous(
      name: String,
      candidates: Vector[ResearcherCandidate],
      totalCandidateCount: Int,
      truncated: Boolean
  )
  case NotFound(name: String)
  case Failed(reason: String)
}

/** Cache rows, including explicitly published homonym base aliases, authorize candidates. Distinct
  * canonical IDs remain distinct; neither name similarity nor confidence chooses one.
  */
final class ResearcherResolverAgent(
    cache: EntityLinkCache,
    config: RuntimeConfig,
    artifacts: Option[RuntimeArtifactStore] = None,
    clockNanos: () => Long = () => System.nanoTime()
) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  def resolve(plan: QueryPlan): ResolverResult = {
    val result = resolveInternal(plan)
    val outcome = result match {
      case ResolverResult.Resolved(_)           => "resolved"
      case ResolverResult.Ambiguous(_, _, _, _) => "ambiguous"
      case ResolverResult.NotFound(_)           => "not-found"
      case ResolverResult.Failed(_)             => "failed"
    }
    RuntimeStageLog.outcome(
      "resolver",
      plan.planId,
      plan.provenance.runId,
      outcome,
      Some(plan.planId)
    )
    result
  }
  private def resolveInternal(plan: QueryPlan): ResolverResult = {
    val started = clockNanos()
    val options =
      plan.runtime.getOrElse(return ResolverResult.Failed("missing-runtime-query-options"))
    val window = options.windowIds.headOption.getOrElse(config.defaultWindowId)
    if (!config.windowIds.contains(window))
      return ResolverResult.Failed("resolver-window-not-stored")
    var resolved = Vector.empty[ResearcherCandidate]
    for (name <- options.researcherNames.distinct) {
      if ((clockNanos() - started) / 1000000 >= config.deadlines.resolverMs)
        return ResolverResult.Failed("resolver-deadline")
      val links =
        try cache.lookupByNormalizedName(TextNorm.personName(name))
        catch { case NonFatal(_) => return ResolverResult.Failed("resolver-cache-failure") }
      if ((clockNanos() - started) / 1000000 >= config.deadlines.resolverMs)
        return ResolverResult.Failed("resolver-deadline")
      val rows = StorageResult.value(links) match {
        case Some(v)                                => v
        case None if links == StorageResult.Missing => Vector.empty
        case None => return ResolverResult.Failed("resolver-cache-unavailable")
      }
      if (
        rows.exists(r =>
          StableIds.parseResearcherId(r.researcherId).isLeft ||
            r.entityType != "name" || r.normalizedKey != TextNorm
              .personName(name) || r.policyVersion.trim.isEmpty ||
            r.sourceId.trim.isEmpty || r.displayName.trim.isEmpty || r.evidenceRefs.isEmpty || r.evidenceRefs
              .exists(_.trim.isEmpty) ||
            StableIds.parseRunId(r.runId).isLeft || r.confidence
              .exists(c => !c.isFinite || c < 0 || c > 1)
        )
      )
        return ResolverResult.Failed("resolver-invalid-source-row")
      val groups = rows.groupBy(_.researcherId).toVector.sortBy(_._1)
      val totalCandidateCount = groups.size
      val selectedGroups = groups.take(config.resolver.maxDistinctCandidates)
      val candidates = Vector.newBuilder[ResearcherCandidate]
      for ((id, group) <- selectedGroups) {
        var coauthors = Vector.empty[String]
        var contextRefs = Vector.empty[String]
        var contextRuns = Vector.empty[String]
        var coauthorsTruncated: Option[Boolean] = None
        if (artifacts.nonEmpty) {
          val context =
            try artifacts.get.researcherContext(id, window, config.retrieval.graphLimit)
            catch { case NonFatal(_) => return ResolverResult.Failed("resolver-context-failure") }
          if ((clockNanos() - started) / 1000000 >= config.deadlines.resolverMs)
            return ResolverResult.Failed("resolver-deadline")
          StorageResult.value(context) match {
            case Some(c)
                if c.researcherId == id && c.windowId == window &&
                  StableIds
                    .parseRunId(c.sourceRunId)
                    .isRight && c.coauthorIds.size <= config.retrieval.graphLimit &&
                  c.coauthorIds.forall(
                    StableIds.parseResearcherId(_).isRight
                  ) && c.sourceRefs.nonEmpty &&
                  c.sourceRefs
                    .forall(r => Vector(r.table, r.rowKey, r.field).forall(_.trim.nonEmpty)) =>
              coauthors = c.coauthorIds
              coauthorsTruncated = Some(c.coauthorsTruncated)
              contextRefs = c.sourceRefs.map(r => s"${r.table}:${r.rowKey}:${r.field}")
              contextRuns = Vector(c.sourceRunId)
            case None if context == StorageResult.Missing => ()
            case _ => return ResolverResult.Failed("resolver-context-unavailable")
          }
        }
        val confidence = group.map(_.confidence).distinct match {
          case Vector(value) => value
          case _             => None
        }
        val sources = group.map(_.sourceId).distinct.sorted
        val affiliations = group.flatMap(_.affiliations).distinct.sorted
        val refs = (group.flatMap(_.evidenceRefs) ++ contextRefs).distinct.sorted
        val runs = (group.map(_.runId) ++ contextRuns).distinct.sorted
        val bounds = config.resolver
        val summary = ResearcherCandidateProvenanceSummary(
          sources.size,
          refs.size,
          affiliations.size,
          runs.size,
          sources.size > bounds.maxSourceIdsPerCandidate || refs.size > bounds.maxEvidenceRefsPerCandidate ||
            affiliations.size > bounds.maxAffiliationsPerCandidate || runs.size > bounds.maxRunIdsPerCandidate
        )
        val candidate = ResearcherCandidate(
          id,
          group.map(_.displayName).sorted.head,
          sources.take(bounds.maxSourceIdsPerCandidate),
          affiliations.take(bounds.maxAffiliationsPerCandidate),
          confidence,
          coauthors.distinct.sorted,
          refs.take(bounds.maxEvidenceRefsPerCandidate),
          runs.take(bounds.maxRunIdsPerCandidate),
          coauthorsTruncated,
          Some(summary)
        )
        if (RuntimeContractValidation.candidate(candidate).nonEmpty)
          return ResolverResult.Failed("resolver-invalid-candidate-summary")
        candidates += candidate
      }
      val found = candidates.result()
      if (found.isEmpty) return ResolverResult.NotFound(name)
      if (totalCandidateCount > 1)
        return ResolverResult.Ambiguous(
          name,
          found,
          totalCandidateCount,
          totalCandidateCount > found.size
        )
      resolved ++= found
    }
    if ((clockNanos() - started) / 1000000 >= config.deadlines.resolverMs)
      ResolverResult.Failed("resolver-deadline")
    else ResolverResult.Resolved(resolved.distinct)
  }
}
