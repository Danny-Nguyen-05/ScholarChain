package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*

/** Parameterized GraphReader templates only. An empty bounded search never proves disconnection. */
final class PathFinderAgent(
    graph: GraphReader,
    metrics: ResearcherMetricStore,
    artifacts: RuntimeArtifactStore,
    config: RuntimeConfig
) {
  import RuntimeEvidenceItems.*
  require(RuntimeConfigValidation.check(config).isEmpty)
  def run(input: RetrievalInput): RetrievalResult = RuntimeRead.stage("path", input) {
    val window = RuntimeRead.window(input, config)
    val plan = input.plan
    val depth = math.min(plan.maxPathDepth, config.retrieval.maxPathDepth)
    val limit = math.min(plan.graphLimit, config.retrieval.graphLimit)
    if (
      plan.topicFilters.nonEmpty || plan.institutionFilters.nonEmpty || plan.venueFilters.nonEmpty
    )
      throw RetrievalProblem("unsupported", "filtered-path-not-stored")
    if (input.candidates.isEmpty) throw RetrievalProblem("missing", "researcher-required")
    val a = input.candidates.head.researcherId
    val first = RuntimeRead.metric(metrics, a, window)
    if (plan.operations.contains(QueryOperation.DirectCoauthors)) {
      val page = RuntimeRead.value(graph.directCoauthors(a, window, limit))
      RuntimeRead.check(
        page.items.size <= limit && page.items.map(_.nodeId).distinct.size == page.items.size,
        "invalid-neighbor-page"
      )
      val edges = page.items.map { n =>
        RuntimeRead.check(n.edgeType == "COAUTHORED_WITH", "unexpected-edge-type")
        val record = RuntimeRead.value(artifacts.edgeSupport(n.edgeId, window))
        validateEndpoints(record, a, n.nodeId, window, first.record.runId)
        edge(input, record)
      }
      val item = make(
        input,
        "direct-coauthors",
        Vector(a),
        Vector(window),
        first.record.runId,
        Vector(
          ids("coauthorIds", page.items.map(_.nodeId)),
          number("returnedCount", page.items.size),
          flag("truncated", page.cursor.nonEmpty),
          // The stored window total makes a truncated page verifiable as "showing N of M".
          number("distinctCoauthorCount", first.detail.distinctCoauthorCount)
        ),
        Vector(
          ref("nodes/type=researcher", a),
          ref("metrics/type=researcher_collaboration", a, "distinctCoauthorCount")
        ),
        sourceContext = Some(first.detail.context)
      )
      RetrievalOutput("path", Vector(item) ++ edges, truncated = page.cursor.nonEmpty)
    } else {
      if (input.candidates.size != 2)
        throw RetrievalProblem("unsupported", "path-requires-two-researchers")
      val b = input.candidates(1).researcherId
      val second = RuntimeRead.metric(metrics, b, window)
      RuntimeRead.check(first.record.runId == second.record.runId, "path-run-mismatch")
      val componentValues = Vector(
        text("sourceComponentId", first.detail.componentId),
        text("targetComponentId", second.detail.componentId)
      )
      val componentRefs =
        Vector(
          ref("metrics/type=researcher_collaboration", a, "componentId"),
          ref("metrics/type=researcher_collaboration", b, "componentId")
        )
      if (first.detail.componentId != second.detail.componentId) {
        val item = make(
          input,
          "path",
          Vector(a, b),
          Vector(window),
          first.record.runId,
          Vector(text("pathStatus", "Disconnected"), number("maxHops", depth)) ++ componentValues,
          componentRefs,
          sourceContext = Some(first.detail.context)
        )
        RetrievalOutput("path", Vector(item))
      } else {
        val raw = graph.shortestPaths(a, b, depth, window, limit)
        val exceeded = raw match {
          case StorageResult.Rejected("exceeded-maxHops") => true; case _ => false
        }
        val paths = if (exceeded) Vector.empty else RuntimeRead.value(raw)
        RuntimeRead.check(paths.size <= limit, "path-result-limit")
        if (paths.isEmpty) {
          val status = if (exceeded) "ExceededMaxHops" else "NoPathWithinLimit"
          RetrievalOutput(
            "path",
            Vector(
              make(
                input,
                "path",
                Vector(a, b),
                Vector(window),
                first.record.runId,
                Vector(text("pathStatus", status), number("maxHops", depth)) ++ componentValues,
                componentRefs,
                sourceContext = Some(first.detail.context)
              )
            )
          )
        } else {
          val items = paths.flatMap { p =>
            RuntimeRead.check(
              p.nodeIds.headOption.contains(a) && p.nodeIds.lastOption.contains(b) &&
                p.nodeIds.distinct.size == p.nodeIds.size && p.edgeIds.size == p.nodeIds.size - 1 && p.edgeIds.size <= depth,
              "path-shape-mismatch"
            )
            val hops = p.edgeIds.zipWithIndex.map { (id, index) =>
              val record = RuntimeRead.value(artifacts.edgeSupport(id, window))
              validateEndpoints(
                record,
                p.nodeIds(index),
                p.nodeIds(index + 1),
                window,
                first.record.runId
              )
              edge(input, record)
            }
            val path = make(
              input,
              "path",
              p.nodeIds,
              Vector(window),
              first.record.runId,
              Vector(
                text("pathStatus", "Found"),
                ids("orderedResearcherIds", p.nodeIds),
                ids("edgeIds", p.edgeIds),
                ids("hopEvidenceIds", hops.map(_.evidenceId)),
                number("hopCount", p.edgeIds.size),
                number("maxHops", depth)
              ),
              componentRefs ++ p.edgeIds.map(ref("edges/type=coauthored_with", _)),
              evidenceType = EvidenceType.GraphPath,
              graphPath = Some(p.nodeIds),
              sourceContext = Some(first.detail.context)
            )
            Vector(path) ++ hops
          }
          RetrievalOutput("path", items)
        }
      }
    }
  }
  private def validateEndpoints(
      record: RuntimeEdgeRecord,
      a: String,
      b: String,
      window: String,
      run: String
  ): Unit = {
    val e = record.edge
    RuntimeRead.check(
      Set(e.researcherA, e.researcherB) == Set(a, b) && e.context.windowId
        .contains(window) && e.context.runId == run,
      "path-edge-source-mismatch"
    )
  }
}
