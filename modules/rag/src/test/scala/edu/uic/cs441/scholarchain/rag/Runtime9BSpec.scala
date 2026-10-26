package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.{Files, Path}

class Runtime9BSpec extends AnyFunSuite {
  import Runtime9BG1Fixture.*
  def ready(r: RetrievalResult): RetrievalOutput = r match {
    case RetrievalResult.Ready(o) => o
    case other                    => fail(s"Expected retrieval evidence, got $other")
  }
  def value(item: EvidenceItem, field: String): RuntimeClaimValue =
    item.runtime.get.values.find(_.field == field).get
  def metricAgent = new CollaborationMetricsAgent(metricStore(), artifacts(), config)
  def metricAgentWithDistanceEstimate: CollaborationMetricsAgent = {
    val original = StorageResult.value(metricStore().get(id("A"), "all-years")).get
    val estimate = PathLengthEstimate(context, component("A"), "sampled-bfs", 2, 7L, 2.1, 4.0, 12L)
    val qualifications = ujson.read(original.qualificationsJson)
    qualifications("pathLengthEstimate") = upickle.default.writeJs(estimate)
    val store = new InMemoryResearcherMetricStore
    assert(
      StorageResult.successful(
        store.put(original.copy(qualificationsJson = qualifications.render()))
      )
    )
    new CollaborationMetricsAgent(store, artifacts(), config)
  }
  def pathAgent = new PathFinderAgent(graph(), metricStore(), artifacts(), config)
  def communityAgent = new CommunityAnalystAgent(graph(), metricStore(), artifacts(), config)
  def emptySemantic(c: RuntimeConfig = config) = new SemanticContextAgent(
    new InMemoryVectorStore,
    new InMemoryObjectStore,
    new DeterministicHashedEmbeddingClient(EmbeddingModel("synthetic-query", "v1", 8)),
    "synthetic-9b-index",
    c
  )
  def runner(c: RuntimeConfig = config): WorkflowRunner = {
    val root = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .get
    val assets = RuntimePromptAssets.fromDirectory(root, c).toOption.get
    new WorkflowRunner(
      new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), c, assets),
      new ResearcherResolverAgent(cache(), c),
      new CollaborationMetricsAgent(metricStore(), artifacts(), c),
      new PathFinderAgent(graph(), metricStore(), artifacts(), c),
      new CommunityAnalystAgent(graph(), metricStore(), artifacts(), c),
      emptySemantic(c),
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, c),
      c
    )
  }
  test("G1 fixture preserves ten original researchers nine works and exact A metrics") {
    assert(names.size == 10 && papers.size == 9 && edges.size == 9)
    val item = ready(metricAgent.run(input(QueryOperation.ComponentLookup, "A"))).items.head
    assert(value(item, "publicationCount").number.contains("3"))
    assert(value(item, "distinctCoauthorCount").number.contains("2"))
    assert(value(item, "totalCoauthorOccurrences").number.contains("4"))
    assert(value(item, "weightedDegree").number.contains("4"))
    assert(value(item, "maximumCoauthorsOnOnePaper").number.contains("2"))
    assert(
      item.runtime.get.windowIds == Vector(
        "all-years"
      ) && item.runtime.get.runId == Runtime9BG1Fixture.run
    )
  }
  test("stored approximate P90 has separate component evidence and never qualifies exact metrics") {
    val request = input(QueryOperation.ComponentLookup, "A")
    val withoutEstimate = ready(metricAgent.run(request)).items.head
    val output = ready(metricAgentWithDistanceEstimate.run(request))
    assert(output.items.size == 2)
    val exact = output.items.find(_.evidenceType == EvidenceType.Metric).get
    val estimate = output.items.find(i => value(i, "kind").text.contains("distance-estimate")).get
    assert(exact == withoutEstimate)
    assert(!exact.runtime.get.approximate && !exact.runtime.get.descriptive)
    Vector(
      "publicationCount" -> "3",
      "distinctCoauthorCount" -> "2",
      "totalCoauthorOccurrences" -> "4",
      "weightedDegree" -> "4",
      "maximumCoauthorsOnOnePaper" -> "2",
      "coreness" -> "2"
    ).foreach { (field, expected) => assert(value(exact, field).number.contains(expected)) }
    assert(!exact.runtime.get.values.exists(_.field == "effectiveDiameterP90"))
    assert(exact.runtime.get.converged.contains(false) && exact.runtime.get.iterations.contains(3))
    val ranked = ready(metricAgent.run(input(QueryOperation.ResearcherRanking))).items
      .find(_.runtime.get.subjectIds == Vector(id("A")))
      .get
    assert(!ranked.runtime.get.approximate)
    exact.runtime.get.values.filterNot(_.field == "kind").foreach { field =>
      assert(value(ranked, field.field) == field)
    }
    assert(estimate.runtime.get.approximate && !estimate.runtime.get.descriptive)
    assert(estimate.runtime.get.subjectIds == Vector(component("A")))
    assert(estimate.runtime.get.windowIds == Vector("all-years"))
    assert(estimate.runtime.get.runId == Runtime9BG1Fixture.run)
    assert(value(estimate, "componentId").text.contains(component("A")))
    assert(value(estimate, "effectiveDiameterP90").number.contains("4.0"))
    assert(value(estimate, "distanceMethod").text.contains("sampled-bfs"))
    assert(value(estimate, "distanceP90Approximate").flag.contains(true))
    assert(
      estimate.runtime.get.sourceRefs.contains(
        SummarySourceRef(
          "metrics/type=path_length_estimate",
          component("A"),
          "effectiveDiameterP90"
        )
      )
    )
    assert(
      estimate.runtime.get.sourceRefs
        .contains(SummarySourceRef("metrics/type=path_length_estimate", component("A"), "method"))
    )
    assert(RuntimeEvidenceIds.expectedId(estimate).contains(estimate.evidenceId))
    assert(DomainValidation.check(estimate).isRight)
  }
  test("exact metric and approximate component estimate are admitted atomically") {
    val request = input(QueryOperation.ComponentLookup, "A")
    val output = ready(metricAgentWithDistanceEstimate.run(request))
    val exact = output.items.find(_.evidenceType == EvidenceType.Metric).get
    val exactCost = EvidenceContext.tokenUpperBound(Vector(exact), request.candidates)
    assert(EvidenceContext.tokenUpperBound(output.items, request.candidates) > exactCost)
    val bounded = config.copy(retrieval = config.retrieval.copy(contextTokenBudget = exactCost))
    val store = new InMemoryIndexedEvidenceBundleStore
    assert(
      new EvidenceBuilderAgent(store, bounded).build("atomic-p90", request, Vector(output)) ==
        EvidenceBuildResult.Missing("essential-evidence-context-budget")
    )
    assert(store.getItem(exact.evidenceId) == StorageResult.Missing)
    val complete =
      new EvidenceBuilderAgent(store, config).build("complete-p90", request, Vector(output))
    val bundle = complete match {
      case EvidenceBuildResult.Persisted(value) => value
      case other => fail(s"Expected complete exact/estimate pair, got $other")
    }
    assert(bundle.items == output.items)
    assert(bundle.runtime.get.deterministicEvidenceIds == output.items.map(_.evidenceId))
    assert(bundle.runtime.get.semanticEvidenceIds.isEmpty)
    assert(
      bundle.items.forall(item =>
        StorageResult.value(store.getItem(item.evidenceId)).contains(item)
      )
    )
  }
  test("solo researcher retains zero coauthors and no invented confidence") {
    val item = ready(metricAgent.run(input(QueryOperation.ComponentLookup, "J"))).items.head
    assert(value(item, "publicationCount").number.contains("1"))
    assert(value(item, "distinctCoauthorCount").number.contains("0"))
    assert(value(item, "maximumCoauthorsOnOnePaper").number.contains("0"))
    assert(candidates("J").head.confidence.isEmpty)
  }
  test("explicit total-author conversion is labeled and absent otherwise") {
    val i = input(QueryOperation.MaximumTeamSize, "A")
    assert(
      !ready(metricAgent.run(i)).items.head.runtime.get.values
        .exists(_.field == "maximumTotalAuthors")
    )
    val converted =
      i.copy(plan = i.plan.copy(runtime = i.plan.runtime.map(_.copy(authorCountConversion = true))))
    val item = ready(metricAgent.run(converted)).items.head
    assert(value(item, "maximumTotalAuthors").number.contains("3"))
    assert(value(item, "authorCountConversion").text.contains("stored maximum coauthors + 1"))
  }
  test("ranking is stored metric order and discloses top K") {
    val i = input(QueryOperation.ResearcherRanking)
      .copy(plan = plan(QueryOperation.ResearcherRanking).copy(graphLimit = 2))
    val o = ready(metricAgent.run(i))
    assert(o.items.size == 2 && o.truncated)
    assert(o.items.forall(i => value(i, "distinctCoauthorCount").number.contains("3")))
    assert(o.rankingScope.exists(_.contains("top-K truncated=true")))
  }
  test("missing stored window is Unsupported and filters on named metrics are never discarded") {
    val i = input(QueryOperation.ComponentLookup, "A")
    assert(
      metricAgent
        .run(
          i.copy(plan =
            i.plan.copy(runtime = i.plan.runtime.map(_.copy(windowIds = Vector("invented"))))
          )
        )
        .isInstanceOf[RetrievalResult.Unsupported]
    )
    assert(
      metricAgent
        .run(i.copy(plan = i.plan.copy(topicFilters = Vector("systems"))))
        .isInstanceOf[RetrievalResult.Unsupported]
    )
  }
  test("A to G four hops retains exact supporting works and collaboration years") {
    val o = ready(pathAgent.run(input(QueryOperation.ShortestPath, "A", "G")))
    val p = o.items.find(_.evidenceType == EvidenceType.GraphPath).get
    assert(value(p, "hopCount").number.contains("4"))
    assert(value(p, "orderedResearcherIds").ids.contains(Vector("A", "C", "D", "F", "G").map(id)))
    val hops = o.items.filter(_.evidenceType == EvidenceType.CoauthorEdge)
    assert(hops.size == 4)
    assert(
      hops.map(value(_, "workIds").ids.get.head).toSet == Set("w1", "w3", "w4", "w6").map(work)
    )
    assert(
      hops
        .flatMap(_.runtime.get.values.filter(_.field.startsWith("year:")).flatMap(_.number))
        .toSet == Set("2015", "2017", "2018", "2020")
    )
  }
  test(
    "different component IDs prove Disconnected; empty bounded search remains NoPathWithinLimit"
  ) {
    val disconnected = ready(pathAgent.run(input(QueryOperation.ShortestPath, "A", "H"))).items.head
    assert(value(disconnected, "pathStatus").text.contains("Disconnected"))
    assert(
      value(disconnected, "sourceComponentId").text != value(disconnected, "targetComponentId").text
    )
    val bounded = input(QueryOperation.ShortestPath, "A", "G")
    val item =
      ready(pathAgent.run(bounded.copy(plan = bounded.plan.copy(maxPathDepth = 2)))).items.head
    assert(value(item, "pathStatus").text.contains("NoPathWithinLimit"))
  }
  test("direct coauthors retain per-edge jointPublicationCount for repeated collaboration") {
    val o = ready(pathAgent.run(input(QueryOperation.DirectCoauthors, "A")))
    assert(value(o.items.head, "coauthorIds").ids.get.toSet == Set(id("B"), id("C")))
    assert(
      o.items
        .filter(_.evidenceType == EvidenceType.CoauthorEdge)
        .map(value(_, "jointPublicationCount").number.get)
        .toSet == Set("3", "1")
    )
  }
  test("community evidence is iteration-limited and distinguishes degree from bridge importance") {
    val o = ready(communityAgent.run(input(QueryOperation.CommunityComparison, "C", "D")))
    assert(
      o.items.forall(i =>
        i.runtime.get.converged.contains(false) && i.runtime.get.iterations.contains(3)
      )
    )
    val b = o.items.find(i => value(i, "kind").text.contains("bridge")).get
    assert(value(b, "crossCommunityDegree").number.contains("1"))
    assert(value(b, "distinctCoauthorCount").number.contains("3"))
    assert(value(b, "communityQualification").text.contains("iteration-limited"))
  }
  test("bundle stable content IDs resolve individually and budget preserves entire G1 path") {
    val i = input(QueryOperation.ShortestPath, "A", "G"); val o = ready(pathAgent.run(i))
    val store = new InMemoryIndexedEvidenceBundleStore
    val builder = new EvidenceBuilderAgent(store, config)
    val result = builder.build("g1-path", i, Vector(o))
    val bundle = result match {
      case EvidenceBuildResult.Persisted(b) => b;
      case other =>
        fail(
          s"default path budget: $other, context=${EvidenceContext.tokenUpperBound(o.items)} bytes=${CoreJson.compact(o.items).length}"
        )
    }
    assert(
      bundle.items.size == 5 && EvidenceContext
        .render(bundle)
        .getBytes(java.nio.charset.StandardCharsets.UTF_8)
        .length <= 4096
    )
    assert(bundle.items.forall(x => StorageResult.value(store.getItem(x.evidenceId)).contains(x)))
    assert(builder.build("g1-path", i, Vector(o)) == EvidenceBuildResult.Persisted(bundle))
  }
  test("tiny evidence budget abstains without partial path persistence") {
    val i = input(QueryOperation.ShortestPath, "A", "G"); val o = ready(pathAgent.run(i))
    val tiny = config.copy(retrieval = config.retrieval.copy(contextTokenBudget = 30))
    assert(
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, tiny).build(
        "small",
        i,
        Vector(o)
      ) == EvidenceBuildResult.Missing("essential-evidence-context-budget")
    )
  }
  test("graph evidence-only runner reaches persisted evidence with no semantic calls") {
    val result = runner().runPlan(plan(QueryOperation.ShortestPath, "A", "G"), "workflow-g1")
    assert(result.isInstanceOf[WorkflowResult.Ready], result.toString)
    val WorkflowResult.Ready(_, bundle, partial, failures) = result: @unchecked
    assert(bundle.items.size == 5 && !partial && failures.isEmpty)
    assert(bundle.runtime.get.resolvedCandidates.map(_.displayName) == Vector("A", "G"))
    assert(bundle.runtime.get.resolvedCandidates.forall(_.sourceIds.nonEmpty))
  }
  test("vector mode abstains on deterministic path requests") {
    val p = plan(QueryOperation.ShortestPath, "A", "G")
    assert(
      runner()
        .runPlan(
          p.copy(runtime = p.runtime.map(_.copy(retrievalMode = RetrievalMode.Vector))),
          "vector"
        )
        .isInstanceOf[WorkflowResult.Abstained]
    )
  }
  test(
    "default ranking retains an explicit bounded prefix instead of losing the whole population"
  ) {
    val result = runner().runPlan(plan(QueryOperation.ResearcherRanking), "default-ranking")
    val WorkflowResult.Ready(_, bundle, partial, _) = result: @unchecked
    assert(
      bundle.items.nonEmpty && bundle.items.size < 10 && partial && bundle.runtime.get.truncated
    )
    assert(
      bundle.runtime.get.rankingScope
        .exists(_.contains(s"context retained ${bundle.items.size} of fetched 10"))
    )
    assert(
      bundle.items.zipWithIndex.forall((item, index) =>
        value(item, "rank").number.contains((index + 1).toString)
      )
    )
  }
  test("homonym overlays expose both candidates without adding graph nodes") {
    val result = runner().runPlan(plan(QueryOperation.ComponentLookup, "Name"), "homonyms")
    val WorkflowResult.Abstained(_, cs, _) = result: @unchecked
    assert(cs.map(_.displayName).toSet == Set("Name 0001", "Name 0002"))
    assert(names.size == 10 && details.size == 10)
  }
}
