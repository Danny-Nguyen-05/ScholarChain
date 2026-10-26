package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class IndependentRuntime9BWorkflowSpec extends AnyFunSuite {
  import IndependentRuntime9BFixture.*
  private def runner(
      cfg: RuntimeConfig = config,
      graph: GraphReader = new Graph,
      metricPort: ResearcherMetricStore = metricStore(),
      pathMetricPort: Option[ResearcherMetricStore] = None,
      links: EntityLinkCache = cache(),
      vectorPort: Option[VectorStore] = None,
      evidencePort: EvidenceBundleStore =
        new edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore()
  ): WorkflowRunner = {
    val corpus = new IndependentRuntime9BSemanticFixture.Corpus
    val planner = new QueryPlannerAgent(
      new ScriptedLlmClient(Vector.empty),
      cfg,
      RuntimePromptAssets
        .fromDirectory(IndependentRuntime9AFixture.root.resolve("prompts"), cfg)
        .toOption
        .get
    )
    new WorkflowRunner(
      planner,
      new ResearcherResolverAgent(links, cfg),
      new CollaborationMetricsAgent(metricPort, artifacts(), cfg),
      new PathFinderAgent(graph, pathMetricPort.getOrElse(metricPort), artifacts(), cfg),
      new CommunityAnalystAgent(graph, metricPort, artifacts(), cfg),
      new SemanticContextAgent(
        vectorPort.getOrElse(corpus.vectors),
        corpus.objects,
        corpus.embeddings,
        corpus.index,
        cfg
      ),
      new EvidenceBuilderAgent(evidencePort, cfg),
      cfg
    )
  }
  private val noVectors = new VectorStore {
    def ensureIndex(n: String, d: Int, m: String): StorageResult[String] =
      StorageResult.Rejected("unused")
    def putBatch(i: String, ds: Vector[VectorDocument]): StorageResult[VectorBatchResult] =
      StorageResult.Rejected("unused")
    def get(i: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
      StorageResult.Missing
    def query(
        i: String,
        v: Vector[Float],
        k: Int,
        f: Map[String, String]
    ): StorageResult[Vector[VectorHit]] = StorageResult.Rejected("injected-semantic-unavailable")
  }

  test("graph mode and evidence-only workflow stop at persisted deterministic evidence") {
    val p = plan(QueryOperation.ComponentLookup, Vector("A"), mode = RetrievalMode.Graph)
    runner(vectorPort = Some(noVectors)).runPlan(p, "query:9b-graph") match {
      case WorkflowResult.Ready(returned, bundle, partial, failures) =>
        assert(returned == p)
        assert(!partial && failures.isEmpty)
        assert(bundle.items.nonEmpty && bundle.items.forall(_.runtime.exists(!_.descriptive)))
        assert(bundle.runtime.get.retrievalMode == RetrievalMode.Graph)
        assert(bundle.runtime.get.semanticEvidenceIds.isEmpty)
        val identities = bundle.runtime.get.resolvedCandidates
        assert(identities.size == 1 && identities.head.researcherId == id("A"))
        assert(identities.head.displayName == "A")
        assert(identities.head.sourceIds == Vector("synthetic:A"))
        assert(identities.head.confidence.isEmpty)
        assert(identities.head.evidenceRefs == Vector("synthetic-evidence:A"))
        assert(identities.head.provenanceSummary.exists(_.sourceIdCount == 1))
        assert(p.runtime.get.evidenceOnly)
      case other => fail(s"Graph-only evidence run should succeed: $other")
    }
  }

  test("fused workflow combines descriptive and stored deterministic evidence within its budget") {
    val p = plan(QueryOperation.ComponentLookup, Vector("A"))
    runner().runPlan(p, "query:9b-fused") match {
      case WorkflowResult.Ready(_, bundle, _, _) =>
        assert(bundle.runtime.get.retrievalMode == RetrievalMode.Fused)
        assert(bundle.runtime.get.deterministicEvidenceIds.nonEmpty)
        assert(bundle.runtime.get.semanticEvidenceIds.nonEmpty)
        assert(
          EvidenceContext
            .render(bundle)
            .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            .length <= config.retrieval.contextTokenBudget
        )
      case other => fail(s"Fused evidence should preserve both authorities: $other")
    }
  }

  test("default budgets persist G1 A to G and all four hop evidence items atomically") {
    val p = plan(QueryOperation.ShortestPath, Vector("A", "G"), mode = RetrievalMode.Graph)
    runner().runPlan(p, "query:9b-full-path") match {
      case WorkflowResult.Ready(_, bundle, _, _) =>
        assert(bundle.items.count(_.evidenceType == EvidenceType.GraphPath) == 1)
        assert(bundle.items.count(_.evidenceType == EvidenceType.CoauthorEdge) == 4)
        val route = bundle.items.find(_.evidenceType == EvidenceType.GraphPath).get
        assert(route.graphPath.contains(Vector("A", "C", "D", "F", "G").map(id)))
        assert(
          EvidenceContext
            .render(bundle)
            .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            .length <= config.retrieval.contextTokenBudget
        )
        assert(
          CoreJson
            .compact(bundle)
            .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            .length <= config.effectiveByteLimits.persistedBundleBytes
        )
      case other =>
        fail(s"Required four-hop evidence must fit the configured default budgets: $other")
    }
  }

  test("default ranking budget retains a disclosed nonempty prefix of the exact stored order") {
    val p = plan(
      QueryOperation.ResearcherRanking,
      metric = Some(CollaborationMetric.DistinctCoauthorCount),
      mode = RetrievalMode.Graph
    )
    runner().runPlan(p, "query:9b-ranking-prefix") match {
      case WorkflowResult.Ready(_, bundle, partial, _) =>
        val ranked = bundle.items.filter(
          _.runtime.get.values.exists(v => v.field == "kind" && v.text.contains("ranking"))
        )
        assert(ranked.nonEmpty && ranked.size < 10)
        val literalOrder =
          Vector(Vector("C", "D", "F"), Vector("A", "B", "E"), Vector("G", "H", "I"), Vector("J"))
            .flatMap(_.map(id).sorted)
        assert(ranked.map(_.runtime.get.subjectIds.head) == literalOrder.take(ranked.size))
        assert(bundle.runtime.get.truncated && partial)
        assert(
          bundle.runtime.get.rankingScope
            .exists(_.contains(s"context retained ${ranked.size} of fetched 10 ranking rows"))
        )
        assert(
          EvidenceContext
            .render(bundle)
            .getBytes(java.nio.charset.StandardCharsets.UTF_8)
            .length <= config.retrieval.contextTokenBudget
        )
        assert(bundle.researcherIds.toSet == ranked.flatMap(_.runtime.get.subjectIds).toSet)
      case other => fail(s"Default ranking must retain and qualify stored top results: $other")
    }
  }

  test("vector-only workflow cannot produce deterministic graph or numeric evidence") {
    val p = plan(QueryOperation.SemanticExplanation, mode = RetrievalMode.Vector)
    runner().runPlan(p, "query:9b-vector") match {
      case WorkflowResult.Ready(_, bundle, _, _) =>
        assert(bundle.runtime.get.deterministicEvidenceIds.isEmpty)
        assert(bundle.items.nonEmpty && bundle.items.forall(_.runtime.get.descriptive))
        assert(
          bundle.items.forall(
            _.runtime.get.values.forall(v => v.number.isEmpty && v.flag.isEmpty && v.ids.isEmpty)
          )
        )
      case other => fail(s"Vector semantic evidence should be available: $other")
    }
    val numeric = plan(QueryOperation.ComponentLookup, Vector("A"), mode = RetrievalMode.Vector)
    assert(!runner().runPlan(numeric, "query:9b-vector-numeric").isInstanceOf[WorkflowResult.Ready])
  }

  test("ambiguous DBLP base name abstains with both suffixed identities before retrieval") {
    val p = plan(QueryOperation.DirectCoauthors, Vector("Name"))
    val graph = new Graph
    runner(graph = graph, links = cache(homonyms = true)).runPlan(p, "query:9b-homonym") match {
      case WorkflowResult.Abstained(_, alternatives, _) =>
        assert(alternatives.map(_.displayName).toSet == Set("Name 0001", "Name 0002"))
        assert(alternatives.map(_.researcherId).toSet == Set(id("Name 0001"), id("Name 0002")))
        assert(graph.neighborCalls.get == 0 && graph.shortestCalls.get == 0)
      case other => fail(s"Ambiguous name must retain candidate list: $other")
    }
  }

  test("not-found identity abstains before any graph search") {
    val graph = new Graph
    val p = plan(QueryOperation.DirectCoauthors, Vector("Unknown Person"))
    assert(
      runner(graph = graph).runPlan(p, "query:9b-notfound").isInstanceOf[WorkflowResult.Abstained]
    )
    assert(graph.neighborCalls.get == 0 && graph.shortestCalls.get == 0)
  }

  test("missing optional semantic context gives a qualified partial result when metrics survive") {
    val p = plan(QueryOperation.ComponentLookup, Vector("A"))
    runner(vectorPort = Some(noVectors)).runPlan(p, "query:9b-partial") match {
      case WorkflowResult.Ready(_, bundle, partial, failures) =>
        assert(partial)
        assert(failures.exists(_.stage == "semantic"))
        assert(bundle.runtime.get.deterministicEvidenceIds.nonEmpty)
      case other => fail(s"Essential metrics survive optional semantic failure: $other")
    }
  }

  test("missing essential metrics abstains even when descriptive context survives") {
    val absent = new ResearcherMetricStore {
      def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] =
        StorageResult.Rejected("unused")
      def get(id: String, window: String): StorageResult[ResearcherMetricRecord] =
        StorageResult.Missing
      def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]] =
        StorageResult.Found(Vector.empty)
    }
    val result = runner(metricPort = absent)
      .runPlan(plan(QueryOperation.ComponentLookup, Vector("A")), "query:9b-essential")
    assert(result.isInstanceOf[WorkflowResult.Abstained])
  }

  test("a blocking path port is interrupted at its stage deadline and leaves no active call") {
    val cfg = config.copy(deadlines = config.deadlines.copy(pathMs = 40))
    val active = new AtomicInteger
    val interrupted = new AtomicInteger
    val graph = new Graph {
      override def shortestPaths(
          a: String,
          b: String,
          maxDepth: Int,
          window: String,
          limit: Int
      ): StorageResult[Vector[GraphPath]] = {
        active.incrementAndGet()
        try { Thread.sleep(10000); StorageResult.Found(Vector.empty) }
        catch {
          case _: InterruptedException =>
            interrupted.incrementAndGet(); throw new InterruptedException
        } finally active.decrementAndGet()
      }
    }
    val started = System.nanoTime()
    val result = runner(cfg, graph).runPlan(
      plan(QueryOperation.ShortestPath, Vector("A", "G"), mode = RetrievalMode.Graph),
      "query:9b-timeout"
    )
    assert(
      result.isInstanceOf[WorkflowResult.Abstained] || result.isInstanceOf[WorkflowResult.Failed]
    )
    assert((System.nanoTime() - started) / 1000000 < 3000)
    assert(interrupted.get == 1)
    assert(active.get == 0)
  }

  test("metrics and semantic retrieval fan out concurrently rather than serially") {
    val enteredMetric = new CountDownLatch(1)
    val enteredSemantic = new CountDownLatch(1)
    val delegate = metricStore()
    val overlappingMetrics = new ResearcherMetricStore {
      def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] = delegate.put(r)
      def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]] =
        delegate.batchGet(keys)
      def get(id: String, window: String): StorageResult[ResearcherMetricRecord] = {
        enteredMetric.countDown()
        if (!enteredSemantic.await(1, TimeUnit.SECONDS))
          StorageResult.Rejected("serial-metrics-probe")
        else delegate.get(id, window)
      }
    }
    val overlappingVector = new VectorStore {
      def ensureIndex(n: String, d: Int, m: String): StorageResult[String] =
        noVectors.ensureIndex(n, d, m)
      def putBatch(i: String, ds: Vector[VectorDocument]): StorageResult[VectorBatchResult] =
        noVectors.putBatch(i, ds)
      def get(i: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
        noVectors.get(i, keys)
      def query(
          i: String,
          v: Vector[Float],
          k: Int,
          f: Map[String, String]
      ): StorageResult[Vector[VectorHit]] = {
        enteredSemantic.countDown()
        if (!enteredMetric.await(1, TimeUnit.SECONDS))
          StorageResult.Rejected("serial-semantic-probe")
        else StorageResult.Found(Vector.empty)
      }
    }
    runner(metricPort = overlappingMetrics, vectorPort = Some(overlappingVector))
      .runPlan(plan(QueryOperation.ComponentLookup, Vector("A")), "query:9b-parallel") match {
      case WorkflowResult.Ready(_, _, partial, failures) =>
        assert(partial && failures.exists(_.stage == "semantic"))
        assert(enteredMetric.getCount == 0 && enteredSemantic.getCount == 0)
      case other => fail(s"Parallel stage rendezvous should retain required metrics: $other")
    }
  }

  test(
    "completed path stage is not timed out while an earlier metrics future consumes its deadline"
  ) {
    val cfg = config.copy(deadlines = config.deadlines.copy(metricsMs = 300, pathMs = 150))
    val slow = new ResearcherMetricStore {
      def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] =
        StorageResult.Rejected("unused")
      def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]] =
        StorageResult.Found(Vector.empty)
      def get(id: String, window: String): StorageResult[ResearcherMetricRecord] = {
        Thread.sleep(10000)
        StorageResult.Missing
      }
    }
    val p = plan(QueryOperation.ComponentLookup, Vector("A", "G"), mode = RetrievalMode.Graph)
      .copy(operations = Vector(QueryOperation.ComponentLookup, QueryOperation.ShortestPath))
    runner(cfg = cfg, metricPort = slow, pathMetricPort = Some(metricStore()))
      .runPlan(p, "query:9b-completed-path") match {
      case WorkflowResult.Abstained(_, _, failures) =>
        assert(failures.exists(f => f.stage == "metrics" && f.reason == "stage-deadline"))
        assert(!failures.exists(_.stage == "path"))
      case other => fail(s"Only the incomplete metrics stage should time out: $other")
    }
  }

  test(
    "failed evidence persistence fails the workflow rather than returning unpersisted evidence"
  ) {
    val reject = new EvidenceBundleStore {
      def put(b: EvidenceBundle): StorageResult[EvidenceBundle] =
        StorageResult.Rejected("injected-evidence-write")
      def get(id: String): StorageResult[EvidenceBundle] = StorageResult.Missing
    }
    val result = runner(evidencePort = reject).runPlan(
      plan(QueryOperation.ComponentLookup, Vector("A"), mode = RetrievalMode.Graph),
      "query:9b-write"
    )
    assert(result.isInstanceOf[WorkflowResult.Failed])
  }
}
