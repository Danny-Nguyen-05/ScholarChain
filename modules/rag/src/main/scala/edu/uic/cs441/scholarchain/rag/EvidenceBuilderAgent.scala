package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

enum EvidenceBuildResult {
  case Persisted(bundle: EvidenceBundle)
  case Missing(reason: String)
  case Failed(reason: String)
}

/** Path and comparison outputs are atomic. Rankings may retain a disclosed top-K prefix; optional
  * semantic context is admitted only after essential deterministic evidence and resolved identity.
  */
final class EvidenceBuilderAgent(store: EvidenceBundleStore, config: RuntimeConfig) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  def build(
      queryId: String,
      input: RetrievalInput,
      outputs: Vector[RetrievalOutput]
  ): EvidenceBuildResult =
    try {
      if (queryId.trim.isEmpty) return EvidenceBuildResult.Failed("blank-query-id")
      val mode = input.plan.runtime.map(_.retrievalMode).getOrElse(config.retrievalMode)
      val bounds = config.resolver
      if (
        input.candidates.exists(c =>
          c.sourceIds.size > bounds.maxSourceIdsPerCandidate || c.evidenceRefs.size > bounds.maxEvidenceRefsPerCandidate ||
            c.affiliations.size > bounds.maxAffiliationsPerCandidate || c.runIds.size > bounds.maxRunIdsPerCandidate || c.coauthorContext.size > config.retrieval.graphLimit
        )
      )
        return EvidenceBuildResult.Failed("resolved-identity-provenance-bound")
      val all = outputs.flatMap(_.items)
      if (all.isEmpty) return EvidenceBuildResult.Missing("essential-evidence-empty")
      if (all.exists(i => i.runtime.isEmpty || DomainValidation.check(i).isLeft))
        return EvidenceBuildResult.Failed("invalid-evidence-item")
      val groups = all.groupBy(_.evidenceId)
      if (groups.exists((_, xs) => xs.map(CoreJson.compact(_)).distinct.size > 1))
        return EvidenceBuildResult.Failed("evidence-id-payload-conflict")
      val unique = all.distinctBy(_.evidenceId)
      val deterministic = unique.filterNot(_.runtime.get.descriptive)
      val semantic = unique.filter(_.runtime.get.descriptive)
      if (mode == RetrievalMode.Vector && deterministic.nonEmpty)
        return EvidenceBuildResult.Failed("vector-mode-deterministic-evidence")
      if (mode == RetrievalMode.Graph && semantic.nonEmpty)
        return EvidenceBuildResult.Failed("graph-mode-semantic-evidence")
      def ranked(item: EvidenceItem): Boolean =
        item.runtime.get.values.exists(v => v.field == "rank" && v.number.nonEmpty)
      val budget = ContextBudget.forPlan(input.plan, config)
      def fits(items: Vector[EvidenceItem]): Boolean = EvidenceContext.tokenUpperBound(
        items,
        input.candidates
      ) <= budget
      val ranking = deterministic.filter(ranked)
      var selected = deterministic.filterNot(ranked)
      if (!fits(selected)) return EvidenceBuildResult.Missing("essential-evidence-context-budget")
      var clipped = false
      val rankingGroups = outputs
        .map(_.items.filter(i => !i.runtime.get.descriptive && ranked(i)).distinctBy(_.evidenceId))
        .filter(_.nonEmpty)
      for (group <- rankingGroups) {
        var retained = 0
        var stopped = false
        for (item <- group if !stopped) {
          if (selected.exists(_.evidenceId == item.evidenceId)) retained += 1
          else if (fits(selected :+ item)) { selected :+= item; retained += 1 }
          else { stopped = true; clipped = true }
        }
        if (retained == 0)
          return EvidenceBuildResult.Missing("essential-ranking-evidence-context-budget")
      }
      for (item <- semantic) {
        if (fits(selected :+ item))
          selected :+= item
        else {
          // Truncate Unicode code points, then rebind the changed immutable payload.
          val points = item.text.getOrElse("").codePoints().toArray
          var low = 0; var high = points.length; var best: Option[EvidenceItem] = None
          while (low <= high) {
            val middle = low + (high - low) / 2
            val next = RuntimeEvidenceIds
              .bind(item.copy(text = Some(new String(points, 0, middle))))
              .toOption
              .get
            if (fits(selected :+ next)) {
              if (middle > 0) best = Some(next)
              low = middle + 1
            } else high = middle - 1
          }
          best.foreach(i => selected :+= i)
          clipped = true
        }
      }
      if (selected.isEmpty) return EvidenceBuildResult.Missing("essential-evidence-context-budget")
      val runtime = RuntimeBundleContext(
        selected.filterNot(_.runtime.get.descriptive).map(_.evidenceId),
        selected.filter(_.runtime.get.descriptive).map(_.evidenceId),
        selected.filterNot(_.runtime.get.descriptive).map(_.runtime.get.runId).distinct.sorted,
        selected.flatMap(_.runtime.get.metricVersion).distinct.sorted,
        mode,
        outputs
          .flatMap(_.rankingScope)
          .headOption
          .map(scope =>
            scope + s" context retained ${selected.count(ranked)} of fetched ${ranking.size} ranking rows; context top-K truncated=${selected.count(ranked) < ranking.size}"
          ),
        clipped || outputs.exists(_.truncated),
        input.candidates
      )
      val confidence =
        if (input.candidates.nonEmpty && input.candidates.forall(_.confidence.nonEmpty))
          Some(input.candidates.flatMap(_.confidence).min)
        else None
      val body = EvidenceBundle(
        "pending",
        SchemaVersions.domain,
        queryId,
        selected,
        (input.candidates.map(_.researcherId) ++ selected
          .filterNot(_.runtime.exists(_.descriptive))
          .flatMap(
            _.runtime.toVector.flatMap(_.subjectIds)
          )).filter(StableIds.parseResearcherId(_).isRight).distinct,
        selected.filter(_.evidenceType == EvidenceType.Metric).map(_.evidenceId),
        confidence,
        "Offline retrieval evidence; iteration-limited, approximate and truncated qualifications remain explicit. Semantic text is untrusted descriptive data.",
        input.plan.provenance,
        Some(runtime)
      )
      val bundle = body.copy(bundleId = "bundle:" + StableIds.sha256Hex(CoreJson.compact(body)))
      if (
        CoreJson
          .compact(bundle)
          .getBytes(UTF_8)
          .length > ContextBudget.persistedBundleBytes(input.plan, config)
      )
        return EvidenceBuildResult.Missing("evidence-bundle-byte-budget")
      if (DomainValidation.check(bundle).isLeft)
        return EvidenceBuildResult.Failed("invalid-evidence-bundle")
      store.put(bundle) match {
        case r if StorageResult.successful(r) =>
          if (!StorageResult.value(r).contains(bundle))
            EvidenceBuildResult.Failed("evidence-persistence-mismatch")
          else {
            val indexed =
              bundle.items.forall(i => StorageResult.value(store.getItem(i.evidenceId)).contains(i))
            if (!indexed) EvidenceBuildResult.Failed("evidence-item-index-unavailable")
            else EvidenceBuildResult.Persisted(bundle)
          }
        case _ => EvidenceBuildResult.Failed("evidence-persistence-failed")
      }
    } catch {
      case _: InterruptedException =>
        Thread.currentThread().interrupt(); EvidenceBuildResult.Failed("evidence-interrupted")
      case NonFatal(_) => EvidenceBuildResult.Failed("evidence-build-failed")
    }
}
