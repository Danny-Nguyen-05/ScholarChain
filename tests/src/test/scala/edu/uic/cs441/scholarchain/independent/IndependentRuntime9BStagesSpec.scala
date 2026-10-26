package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

/** Expected numbers and routes are literal requirements, independent of retrieval implementation.
  */
class IndependentRuntime9BStagesSpec extends AnyFunSuite {
  import IndependentRuntime9BFixture.*
  private def ready(result: RetrievalResult): RetrievalOutput = result match {
    case RetrievalResult.Ready(output) => output
    case other                         => fail(s"Expected stored evidence, got $other")
  }
  private def values(item: EvidenceItem): Map[String, RuntimeClaimValue] =
    item.runtime.get.values.map(v => v.field -> v).toMap
  private def kind(item: EvidenceItem, expected: String): Boolean =
    values(item).get("kind").flatMap(_.text).contains(expected)
  private def metrics = new CollaborationMetricsAgent(metricStore(), artifacts(), config)
  private def paths(graph: Graph = new Graph) =
    new PathFinderAgent(graph, metricStore(), artifacts(), config)
  private def communities = new CommunityAnalystAgent(new Graph, metricStore(), artifacts(), config)
  private val p90Estimate =
    PathLengthEstimate(context, component("A"), "sampled-bfs", 2, 7L, 2.1, 4.0, 12L)
  private def p90MetricStore(includeEstimate: Boolean): InMemoryResearcherMetricStore = {
    val store = new InMemoryResearcherMetricStore
    val metric = details.find(_.researcherId == id("A")).get
    val membership = memberships.find(_.researcherId == id("A")).get
    val qualifications = ujson.Obj("communityMembership" -> upickle.default.writeJs(membership))
    if (includeEstimate)
      qualifications("pathLengthEstimate") = upickle.default.writeJs(p90Estimate)
    assert(
      StorageResult.successful(
        store.put(
          ResearcherMetricRecord(
            id("A"),
            "all-years",
            policy,
            runId,
            CoreJson.compact(metric),
            qualifications.render()
          )
        )
      )
    )
    store
  }

  Vector(
    "publicationCount" -> "3",
    "distinctCoauthorCount" -> "2",
    "totalCoauthorOccurrences" -> "4",
    "averageCoauthorsPerPaper" -> "1.3333333333333333",
    "maximumCoauthorsOnOnePaper" -> "2",
    "weightedDegree" -> "4",
    "maxTeamWorkTieCount" -> "1",
    "coreness" -> "2"
  ).foreach { (field, expected) =>
    test(s"G1 A exact stored $field retains window, policy and source run") {
      val output = ready(metrics.run(input(QueryOperation.ComponentLookup, "A")))
      val item = output.items.find(i => kind(i, "metrics")).get
      assert(values(item)(field).number.contains(expected))
      assert(item.runtime.get.subjectIds.contains(id("A")))
      assert(item.runtime.get.windowIds == Vector("all-years"))
      assert(item.runtime.get.metricVersion.contains(policy))
      assert(item.runtime.get.runId == runId)
      assert(item.runtime.get.sourceRefs.nonEmpty)
      assert(!item.runtime.get.descriptive)
    }
  }

  test("every G1 researcher's literal count table survives retrieval without recomputation") {
    val output = ready(metrics.run(input(QueryOperation.ComponentLookup, names*)))
    val byId = output.items
      .filter(i => kind(i, "metrics"))
      .map(i => i.runtime.get.subjectIds.head -> i)
      .toMap
    assert(byId.keySet == names.map(id).toSet)
    expected.foreach { (n, p, c, t, a, m, work, core) =>
      val v = values(byId(id(n)))
      assert(v("publicationCount").number.contains(p.toString), n)
      assert(v("distinctCoauthorCount").number.contains(c.toString), n)
      assert(v("totalCoauthorOccurrences").number.contains(t.toString), n)
      assert(v("maximumCoauthorsOnOnePaper").number.contains(m.toString), n)
      assert(v("weightedDegree").number.contains(t.toString), n)
      assert(v("coreness").number.contains(core.toString), n)
      assert(v("maxTeamWorkIds").ids.get == Vector(IndependentPhase6G1.canonicalWorkId(work)), n)
    }
  }

  test("maximum coauthors keeps its label and total authors needs explicit conversion") {
    val original = input(QueryOperation.MaximumTeamSize, "A")
    val unchanged = ready(metrics.run(original)).items.find(i => kind(i, "metrics")).get
    assert(values(unchanged)("maximumCoauthorsOnOnePaper").number.contains("2"))
    assert(!values(unchanged).contains("maximumTotalAuthors"))
    val converted = original.copy(plan =
      original.plan.copy(runtime = original.plan.runtime.map(_.copy(authorCountConversion = true)))
    )
    val item = ready(metrics.run(converted)).items.find(i => kind(i, "metrics")).get
    assert(values(item)("maximumCoauthorsOnOnePaper").number.contains("2"))
    assert(values(item)("maximumTotalAuthors").number.contains("3"))
    assert(values(item)("authorCountConversion").text.contains("stored maximum coauthors + 1"))
  }

  test("unknown metric window is rejected instead of reading all years") {
    val in = input(QueryOperation.ComponentLookup, "A")
    val result = metrics.run(
      in.copy(plan =
        in.plan.copy(runtime = in.plan.runtime.map(_.copy(windowIds = Vector("not-stored"))))
      )
    )
    assert(!result.isInstanceOf[RetrievalResult.Ready])
  }

  test(
    "stored P90 is separate approximate evidence and never qualifies exact named or ranked metrics"
  ) {
    val in = input(QueryOperation.ComponentLookup, "A")
    val output = ready(
      new CollaborationMetricsAgent(p90MetricStore(includeEstimate = true), artifacts(), config)
        .run(in)
    )
    val baseline = ready(
      new CollaborationMetricsAgent(p90MetricStore(includeEstimate = false), artifacts(), config)
        .run(in)
    ).items.find(i => kind(i, "metrics")).get
    val exact = output.items.find(i => kind(i, "metrics")).get
    val estimate = output.items.find(i => kind(i, "distance-estimate")).get
    assert(output.items.size == 2)
    assert(exact == baseline)
    assert(!exact.runtime.get.approximate && !exact.runtime.get.descriptive)
    assert(exact.runtime.get.converged.contains(false))
    assert(exact.runtime.get.iterations.contains(3))
    Vector(
      "publicationCount" -> "3",
      "distinctCoauthorCount" -> "2",
      "totalCoauthorOccurrences" -> "4",
      "averageCoauthorsPerPaper" -> "1.3333333333333333",
      "maximumCoauthorsOnOnePaper" -> "2",
      "weightedDegree" -> "4",
      "coreness" -> "2"
    ).foreach { (field, expected) => assert(values(exact)(field).number.contains(expected)) }
    assert(!values(exact).contains("effectiveDiameterP90"))
    assert(!values(exact).contains("distanceP90Approximate"))

    val rankedPlan = plan(
      QueryOperation.ResearcherRanking,
      metric = Some(CollaborationMetric.DistinctCoauthorCount)
    )
    val ranked = ready(
      new CollaborationMetricsAgent(p90MetricStore(includeEstimate = true), artifacts(), config)
        .run(RetrievalInput(rankedPlan, Vector.empty))
    ).items.find(_.runtime.get.subjectIds.contains(id("A"))).get
    assert(!ranked.runtime.get.approximate)
    assert(ranked.runtime.get.windowIds == exact.runtime.get.windowIds)
    assert(ranked.runtime.get.runId == exact.runtime.get.runId)
    assert(ranked.runtime.get.converged == exact.runtime.get.converged)
    assert(ranked.runtime.get.iterations == exact.runtime.get.iterations)
    (values(exact) - "kind").foreach { (field, expected) =>
      assert(values(ranked)(field) == expected, field)
    }

    assert(estimate.runtime.get.approximate && !estimate.runtime.get.descriptive)
    assert(estimate.runtime.get.subjectIds == Vector(component("A")))
    assert(estimate.runtime.get.windowIds == Vector("all-years"))
    assert(estimate.runtime.get.runId == runId)
    assert(values(estimate)("componentId").text.contains(component("A")))
    assert(values(estimate)("effectiveDiameterP90").number.contains("4.0"))
    assert(values(estimate)("distanceMethod").text.contains("sampled-bfs"))
    assert(values(estimate)("distanceP90Approximate").flag.contains(true))
    assert(
      estimate.runtime.get.sourceRefs.contains(
        SummarySourceRef(
          "metrics/type=path_length_estimate",
          component("A"),
          "effectiveDiameterP90"
        )
      )
    )
    assert(estimate.runtime.get.contentBindingVersion.contains(RuntimeEvidenceIds.version))
    assert(RuntimeEvidenceIds.bind(estimate).toOption.contains(estimate))
    assert(DomainValidation.check(estimate).isRight)
    val contextJson = ujson.read(
      EvidenceContext
        .render(output.items)
        .stripPrefix("<untrusted_evidence_json>\n")
        .stripSuffix("\n</untrusted_evidence_json>")
    )
    val contexts = contextJson("items").arr.map(v => v("evidenceId").str -> v).toMap
    assert(!contexts(exact.evidenceId).obj.get("approximate").exists(_.bool))
    assert(contexts(estimate.evidenceId)("approximate").bool)
  }

  test("exact metric and its separate stored P90 remain atomic when only the metric fits") {
    val in = input(QueryOperation.ComponentLookup, "A")
    val output = ready(
      new CollaborationMetricsAgent(p90MetricStore(includeEstimate = true), artifacts(), config)
        .run(in)
    )
    val exact = output.items.find(i => kind(i, "metrics")).get
    val limit = EvidenceContext.tokenUpperBound(Vector(exact), in.candidates)
    assert(EvidenceContext.tokenUpperBound(output.items, in.candidates) > limit)
    val limited = config.copy(retrieval = config.retrieval.copy(contextTokenBudget = limit))
    val underlying =
      new edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore()
    var writes = 0
    val store = new EvidenceBundleStore {
      def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle] = {
        writes += 1
        underlying.put(bundle)
      }
      def get(id: String): StorageResult[EvidenceBundle] = underlying.get(id)
      override def getItem(id: String): StorageResult[EvidenceItem] = underlying.getItem(id)
    }
    val builder = new EvidenceBuilderAgent(store, limited)
    assert(
      builder
        .build("query:9b-p90-metric-fits", in, Vector(output.copy(items = Vector(exact))))
        .isInstanceOf[EvidenceBuildResult.Persisted]
    )
    writes = 0
    assert(
      builder.build("query:9b-p90-atomic", in, Vector(output)) ==
        EvidenceBuildResult.Missing("essential-evidence-context-budget")
    )
    assert(writes == 0)
  }

  test("distinct-coauthor ranking has exact G1 leaders and discloses top-K truncation") {
    val p = plan(
      QueryOperation.ResearcherRanking,
      metric = Some(CollaborationMetric.DistinctCoauthorCount),
      limit = 2
    )
    val output = ready(metrics.run(RetrievalInput(p, Vector.empty)))
    assert(output.truncated)
    assert(output.rankingScope.exists(_.nonEmpty))
    val ranked = output.items.filter(i =>
      i.runtime.exists(_.values.exists(v => v.field == "distinctCoauthorCount"))
    )
    assert(ranked.size == 2)
    assert(ranked.forall(i => values(i)("distinctCoauthorCount").number.contains("3")))
    assert(ranked.flatMap(_.runtime.get.subjectIds).toSet.subsetOf(Set(id("C"), id("D"), id("F"))))
  }

  Vector("institution", "topic", "venue").foreach { field =>
    test(s"$field population filter uses authoritative overlay before exact stored ranking") {
      val p = plan(
        QueryOperation.ResearcherRanking,
        metric = Some(CollaborationMetric.DistinctCoauthorCount)
      )
      val filtered = field match {
        case "institution" => p.copy(institutionFilters = Vector(institution))
        case "topic"       => p.copy(topicFilters = Vector(topic))
        case _             => p.copy(venueFilters = Vector(venue))
      }
      val output = ready(metrics.run(RetrievalInput(filtered, Vector.empty)))
      val ids = output.items.flatMap(_.runtime.toVector.flatMap(_.subjectIds)).toSet
      assert(ids == Set(id("A"), id("B")))
      assert(output.rankingScope.exists(_.nonEmpty))
      assert(output.items.forall(i => values(i)("distinctCoauthorCount").number.contains("2")))
    }
  }

  test(
    "missing authoritative filter metadata is Unsupported, never replaced by semantic neighbors"
  ) {
    val p = plan(
      QueryOperation.ResearcherRanking,
      metric = Some(CollaborationMetric.DistinctCoauthorCount)
    ).copy(topicFilters = Vector(topic))
    val result = new CollaborationMetricsAgent(metricStore(), artifacts(enriched = false), config)
      .run(RetrievalInput(p, Vector.empty))
    assert(result.isInstanceOf[RetrievalResult.Unsupported])
  }

  Vector(QueryOperation.ComponentLookup, QueryOperation.CommunityComparison).foreach { operation =>
    test(s"named researcher $operation cannot silently discard an institution filter") {
      val in = input(operation, "A")
      val filtered = in.copy(plan = in.plan.copy(institutionFilters = Vector(otherInstitution)))
      val result =
        if (operation == QueryOperation.ComponentLookup) metrics.run(filtered)
        else communities.run(filtered)
      assert(!result.isInstanceOf[RetrievalResult.Ready])
    }
  }

  test("G1 A to G returns the literal four-hop route and all supporting work years") {
    val output = ready(paths().run(input(QueryOperation.ShortestPath, "A", "G")))
    val path = output.items.find(i => kind(i, "path")).get
    assert(values(path)("pathStatus").text.contains("Found"))
    assert(values(path)("hopCount").number.contains("4"))
    assert(
      values(path)("orderedResearcherIds").ids.contains(Vector("A", "C", "D", "F", "G").map(id))
    )
    val hops = output.items.filter(_.evidenceType == EvidenceType.CoauthorEdge)
    assert(hops.size == 4)
    val works = hops.flatMap(i => values(i)("workIds").ids.get).toSet
    assert(works == Set("w1", "w3", "w4", "w6").map(IndependentPhase6G1.canonicalWorkId))
    val years = hops
      .flatMap(i => values(i).values.filter(_.field.startsWith("year:")).flatMap(_.number))
      .toSet
    assert(years == Set("2015", "2017", "2018", "2020"))
    assert(hops.forall(i => values(i)("jointPublicationCount").number.contains("1")))
    assert(output.items.forall(_.runtime.get.sourceRefs.nonEmpty))
  }

  test("G1 A to H is Disconnected only from differing stored component IDs") {
    val graph = new Graph
    val output = ready(paths(graph).run(input(QueryOperation.ShortestPath, "A", "H")))
    val path = output.items.find(i => kind(i, "path")).get
    assert(values(path)("pathStatus").text.contains("Disconnected"))
    assert(graph.shortestCalls.get == 0)
    val componentValues = output.items
      .flatMap(_.runtime.get.values)
      .filter(v => Set("sourceComponentId", "targetComponentId")(v.field))
      .flatMap(_.text)
      .toSet
    assert(componentValues == Set(component("A"), component("H")))
  }

  test("same-component empty bounded search never asserts disconnection") {
    val graph = new Graph
    graph.pathOverride = Some(StorageResult.Found(Vector.empty))
    val output = ready(paths(graph).run(input(QueryOperation.ShortestPath, "A", "G")))
    val status =
      output.items.flatMap(_.runtime.get.values).find(_.field == "pathStatus").get.text.get
    assert(Set("NoPathWithinLimit", "ExceededMaxHops")(status))
    assert(status != "Disconnected")
    assert(graph.shortestCalls.get == 1)
  }

  test("max depth below the four-hop route yields a bounded status, never an invented path") {
    val p = plan(QueryOperation.ShortestPath, Vector("A", "G"), depth = 3)
    val output = ready(paths().run(RetrievalInput(p, candidates("A", "G"))))
    val status =
      output.items.flatMap(_.runtime.get.values).find(_.field == "pathStatus").get.text.get
    assert(Set("NoPathWithinLimit", "ExceededMaxHops")(status))
    assert(!output.items.exists(i => values(i).get("pathStatus").flatMap(_.text).contains("Found")))
  }

  test("a graph path with missing supporting edge is not accepted as a found path") {
    val graph = new Graph
    graph.pathOverride = Some(
      StorageResult.Found(Vector(GraphPath(Vector(id("A"), id("G")), Vector("edge:" + "0" * 64))))
    )
    assert(
      !paths(graph)
        .run(input(QueryOperation.ShortestPath, "A", "G"))
        .isInstanceOf[RetrievalResult.Ready]
    )
  }

  test("a graph adapter exceeding the requested path result cap is rejected") {
    val graph = new Graph
    val route = GraphPath(
      Vector("A", "C", "D", "F", "G").map(id),
      Vector(
        edge("A", "C").edgeId,
        edge("C", "D").edgeId,
        edge("D", "F").edgeId,
        edge("F", "G").edgeId
      )
    )
    graph.pathOverride = Some(StorageResult.Found(Vector(route, route)))
    val p = plan(QueryOperation.ShortestPath, Vector("A", "G"), limit = 1)
    assert(
      paths(graph).run(RetrievalInput(p, candidates("A", "G"))).isInstanceOf[RetrievalResult.Failed]
    )
  }

  test("an explicit graph ExceededMaxHops status is preserved independently of disconnection") {
    val graph = new Graph
    graph.pathOverride = Some(StorageResult.Rejected("exceeded-maxHops"))
    val output = ready(paths(graph).run(input(QueryOperation.ShortestPath, "A", "G")))
    assert(
      output.items
        .flatMap(_.runtime.get.values)
        .exists(v => v.field == "pathStatus" && v.text.contains("ExceededMaxHops"))
    )
  }

  test("direct coauthor result cap is disclosed instead of presenting a complete neighbor list") {
    val p = plan(QueryOperation.DirectCoauthors, Vector("A"), limit = 1)
    val output = ready(paths().run(RetrievalInput(p, candidates("A"))))
    assert(output.truncated)
    assert(output.items.count(_.evidenceType == EvidenceType.CoauthorEdge) == 1)
    assert(
      output.items
        .flatMap(_.runtime.get.values)
        .exists(v => v.field == "truncated" && v.flag.contains(true))
    )
  }

  test("direct A-B repeated collaboration uses per-edge jointPublicationCount and three works") {
    val output = ready(paths().run(input(QueryOperation.DirectCoauthors, "A")))
    val ab = output.items.find(i => i.edgeLocatorId.contains(edge("A", "B").edgeId)).get
    assert(values(ab)("jointPublicationCount").number.contains("3"))
    assert(
      values(ab)("workIds").ids.get.toSet == Set("w1", "w2", "w9").map(
        IndependentPhase6G1.canonicalWorkId
      )
    )
  }

  test("community comparison retains declared sizes, neighboring communities and iteration limit") {
    val output = ready(communities.run(input(QueryOperation.CommunityComparison, "C", "D")))
    val summaries = output.items.filter(i => kind(i, "community"))
    assert(summaries.size == 2)
    assert(summaries.flatMap(i => values(i)("size").number).toSet == Set("3", "4"))
    assert(summaries.forall(_.runtime.get.converged.contains(false)))
    assert(summaries.forall(_.runtime.get.iterations.contains(3)))
    assert(summaries.forall(i => values(i)("selectedCrossCommunityEdgeCount").number.contains("1")))
    assert(summaries.forall(i => values(i)("neighborCommunityIds").ids.exists(_.nonEmpty)))
  }

  test("a cross-community graph row cannot cite an unrelated stored collaboration edge") {
    val forged = new Graph {
      override def crossCommunityEdges(
          communityId: String,
          window: String,
          limit: Int
      ): StorageResult[GraphPage] =
        StorageResult.Found(
          GraphPage(
            Vector(GraphNeighbor(id("D"), edge("A", "B").edgeId, "COAUTHORED_WITH", Map.empty)),
            None
          )
        )
    }
    val agent = new CommunityAnalystAgent(forged, metricStore(), artifacts(), config)
    assert(
      agent.run(input(QueryOperation.CommunityComparison, "C")).isInstanceOf[RetrievalResult.Failed]
    )
  }

  test(
    "bridge evidence preserves breadth and all selected bridge measures without conflating them"
  ) {
    val output = ready(communities.run(input(QueryOperation.BridgeRanking)))
    val bridgeRows = output.items.filter(i => values(i).contains("crossCommunityDegree"))
    val cd = bridgeRows.filter(i => i.runtime.get.subjectIds.exists(Set(id("C"), id("D"))))
    assert(cd.size == 2)
    cd.foreach { item =>
      val v = values(item)
      assert(v("crossCommunityDegree").number.contains("1"))
      assert(v("crossCommunityWeight").number.contains("1"))
      assert(v("communitiesConnected").number.contains("1"))
      assert(v("participationCoefficient").number.contains("0.4444444444444444"))
      assert(v("distinctCoauthorCount").number.contains("3"))
      assert(item.runtime.get.converged.contains(false) && item.runtime.get.iterations.contains(3))
    }
  }

  test("temporal D comparison preserves hand-derived deltas and both iteration-limited windows") {
    val p = plan(QueryOperation.TemporalComparison, Vector("D")).copy(runtime =
      Some(
        RuntimeQueryOptions(
          researcherNames = Vector("D"),
          windowIds = Vector("2015-2017", "2018-2021"),
          comparisonWindowIds = Vector("2015-2017", "2018-2021"),
          evidenceOnly = true
        )
      )
    )
    assert(SparkAnalyticsValidation.check(temporalD).isRight)
    val source = artifacts(temporal = true)
    val stored = source.temporalChange(id("D"), "2015-2017", "2018-2021")
    assert(
      StorageResult.successful(stored),
      s"Independent temporal source must pass actual artifact integrity: $stored"
    )
    val agent = new CommunityAnalystAgent(new Graph, metricStore(), source, config)
    val output = ready(agent.run(RetrievalInput(p, candidates("D"))))
    assert(output.items.size == 1)
    val item = output.items.head
    assert(item.runtime.get.windowIds == Vector("2015-2017", "2018-2021"))
    assert(item.runtime.get.converged.contains(false) && item.runtime.get.iterations.contains(3))
    val v = values(item)
    assert(v("fromPresent").flag.contains(true) && v("toPresent").flag.contains(true))
    assert(v("deltaDistinctCoauthors").number.contains("1"))
    assert(v("deltaAverageCoauthorsPerPaper").number.contains("1.0"))
    assert(v("deltaMaximumCoauthorsOnOnePaper").number.contains("1"))
    assert(v("deltaComponentSize").number.contains("0"))
    assert(v("deltaCrossCommunityDegree").number.contains("-1"))
    assert(v("deltaCrossCommunityWeight").number.contains("-1"))
    assert(v("deltaCommunitiesConnected").number.contains("-1"))
    assert(v("deltaParticipationCoefficient").number.contains("0.0"))
    assert(v("communityJaccardOverlap").number.contains("0.25"))
    assert(v("converged:2015-2017").flag.contains(false))
    assert(v("converged:2018-2021").flag.contains(false))
    val filtered = p.copy(institutionFilters = Vector(institution))
    assert(
      agent.run(RetrievalInput(filtered, candidates("D"))).isInstanceOf[RetrievalResult.Unsupported]
    )
  }
}
