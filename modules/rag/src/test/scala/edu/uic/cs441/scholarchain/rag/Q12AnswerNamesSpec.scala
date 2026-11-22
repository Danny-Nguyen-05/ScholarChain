package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

/** Answer text must show researcher display names (from stored graph node labels) next to the ids
  * that remain the verification keys. The Q12 benchmark scorer checks names in the answer text.
  */
class Q12AnswerNamesSpec extends AnyFunSuite {
  import Runtime9BG1Fixture.*

  private val cfg = config
  private def g1Plan(op: QueryOperation, ns: String*) = Runtime9BG1Fixture.plan(op, ns*)
  private def label(n: String): String = s"Dr. $n Name"
  private val labels: Map[String, String] = names.map(n => id(n) -> label(n)).toMap

  /** The G1 graph with stored researcher nodes; `lookup` can fail or throw per id. */
  private final class NamedGraph(
      inner: GraphReader = graph(),
      lookup: String => StorageResult[GraphNode] = NamedGraph.stored
  ) extends GraphReader {
    private var asked = Vector.empty[String]
    def lookups: Vector[String] = synchronized(asked)
    def node(i: String): StorageResult[GraphNode] = { synchronized { asked :+= i }; lookup(i) }
    def neighbors(
        i: String,
        w: String,
        t: Set[String],
        l: Int,
        c: Option[String]
    ): StorageResult[GraphPage] = inner.neighbors(i, w, t, l, c)
    def directCoauthors(i: String, w: String, l: Int) = inner.directCoauthors(i, w, l)
    def shortestPaths(a: String, b: String, d: Int, w: String, l: Int) =
      inner.shortestPaths(a, b, d, w, l)
    def communityMembers(c: String, w: String, l: Int) = inner.communityMembers(c, w, l)
    def crossCommunityEdges(c: String, w: String, l: Int) = inner.crossCommunityEdges(c, w, l)
  }
  private object NamedGraph {
    def node(i: String, text: String): GraphNode =
      GraphNode(i, SchemaVersions.domain, GraphNodeClass.Researcher, text, Vector.empty, provenance)
    val stored: String => StorageResult[GraphNode] =
      i => labels.get(i).map(l => StorageResult.Found(node(i, l))).getOrElse(StorageResult.Missing)
  }

  private def assets = {
    val root = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .get
    RuntimePromptAssets.fromDirectory(root, cfg).toOption.get
  }
  private def runner(g: GraphReader) = new WorkflowRunner(
    new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), cfg, assets),
    new ResearcherResolverAgent(cache(), cfg),
    new CollaborationMetricsAgent(metricStore(), artifacts(), cfg),
    new PathFinderAgent(g, metricStore(), artifacts(), cfg),
    new CommunityAnalystAgent(g, metricStore(), artifacts(), cfg),
    new SemanticContextAgent(
      new InMemoryVectorStore,
      new InMemoryObjectStore,
      new DeterministicHashedEmbeddingClient(EmbeddingModel("synthetic-query", "v1", 8)),
      "synthetic-9b-index",
      cfg
    ),
    new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, cfg),
    cfg
  )

  /** Retrieval through the real runner; the names travel beside the result. */
  private def run(
      r: WorkflowRunner,
      plan: QueryPlan,
      queryId: String
  ): (QueryPlan, EvidenceBundle, Map[String, String]) = {
    val named = r.runPlanNamed(plan, queryId)
    named.result match {
      case WorkflowResult.Ready(p, b, _, _) => (p, b, named.displayNames)
      case other                            => fail(other.toString)
    }
  }
  private def verified(
      plan: QueryPlan,
      bundle: EvidenceBundle,
      names: Map[String, String],
      invented: String = "Plain prose"
  ): VerifiedAnswer = {
    val scaffold = ClaimScaffold.build(plan, bundle, ContextBudget.scaffoldBytes(plan, cfg))
    assert(scaffold.nonEmpty)
    val claims = scaffold.map(s =>
      AnswerClaim(
        s.claimId,
        SchemaVersions.domain,
        invented,
        s.evidenceIds,
        VerificationStatus.Unverified,
        None,
        provenance,
        Some(s.claim)
      )
    )
    val answer = new ClaimVerificationAgent(cfg)
      .verify(plan, bundle, SynthesisProposal(claims, claims.map(_.claimId), "", "u"), names)
    assert(answer.verification.overallStatus == VerificationStatus.Verified)
    assert(answer.answer.claims.size == claims.size)
    answer
  }

  test("a ranking answer names the rank-1 researcher and keeps the id") {
    val g = new NamedGraph()
    val r = runner(g)
    val (p, bundle, stored) = run(r, g1Plan(QueryOperation.ResearcherRanking), "names-rank")
    val answer = verified(p, bundle, stored)
    val first = answer.answer.claims
      .filter(_.runtime.exists(_.claimType == RuntimeClaimType.Ranking))
      .find(_.runtime.get.values.exists(v => v.field == "rank" && v.number.contains("1")))
      .get
    val topId = first.runtime.get.subjectIds.head
    assert(first.text.contains(labels(topId)), first.text)
    assert(first.text.contains(topId), "the id stays beside the name: " + first.text)
    assert(answer.answer.summary.contains(labels(topId)))
    assert(stored.nonEmpty && stored.forall((k, v) => labels(k) == v))
    assert(g.lookups.forall(RuntimeNames.isResearcherId))
  }

  test("a direct-coauthor answer lists the coauthor names") {
    val r = runner(new NamedGraph())
    val (p, bundle, stored) =
      run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-coauthors")
    val answer = verified(p, bundle, stored)
    val text = answer.answer.summary
    assert(text.contains(label("B")) && text.contains(label("C")), text)
    assert(text.contains(id("B")) && text.contains(id("C")), "ids stay traceable: " + text)
  }

  test("a path answer lists the endpoint and interior names joined by arrows") {
    val r = runner(new NamedGraph())
    val (p, bundle, stored) = run(r, g1Plan(QueryOperation.ShortestPath, "A", "G"), "names-path")
    val answer = verified(p, bundle, stored)
    val pathClaim = answer.answer.claims
      .find(_.runtime.exists(_.values.exists(_.field == "orderedResearcherIds")))
      .get
    val nodes = pathClaim.runtime.get.values.find(_.field == "orderedResearcherIds").get.ids.get
    assert(nodes.size >= 3, "needs an interior node: " + nodes)
    val rendered = pathClaim.text
    // Endpoints are the question's resolved candidates (their resolved display names); every step
    // keeps its id beside the name.
    def step(n: String) =
      (if (n == id("A")) "A" else if (n == id("G")) "G" else labels(n)) + s" ($n)"
    assert(rendered.contains(nodes.map(step).mkString(" → ")), rendered)
    nodes.drop(1).dropRight(1).foreach(n => assert(rendered.contains(labels(n)), rendered))
  }

  test("a failed, missing or throwing node lookup falls back to the id without failing") {
    val failing = Set(id("B"))
    val lookup: String => StorageResult[GraphNode] = i =>
      if (failing(i)) throw new IllegalStateException("graph-service down")
      else if (i == id("C")) StorageResult.Rejected("unavailable")
      else NamedGraph.stored(i)
    val r = runner(new NamedGraph(lookup = lookup))
    val (p, bundle, stored) =
      run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-fallback")
    assert(!stored.contains(id("B")) && !stored.contains(id("C")))
    val answer = verified(p, bundle, stored)
    assert(answer.answer.summary.contains(id("B")) && answer.answer.summary.contains(id("C")))
    assert(!answer.answer.summary.contains(label("B")))
    assert(!answer.answer.summary.contains(label("C")))
  }

  test("only stored node labels become names; blank or mismatched nodes are ignored") {
    val lookup: String => StorageResult[GraphNode] = i =>
      if (i == id("B")) StorageResult.Found(NamedGraph.node(i, "   "))
      else if (i == id("C")) StorageResult.Found(NamedGraph.node(id("D"), "Wrong Node"))
      else NamedGraph.stored(i)
    val r = runner(new NamedGraph(lookup = lookup))
    val (p, bundle, stored) =
      run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-ignored")
    assert(!stored.contains(id("B")) && !stored.contains(id("C")))
    assert(verified(p, bundle, stored).answer.summary.contains(id("C")))
  }

  test("model-supplied text never becomes a name and claim verification ignores names") {
    val r = runner(new NamedGraph())
    val (p, bundle, stored) =
      run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-model")
    val answer = verified(p, bundle, Map.empty, invented = "Mallory Impostor is the coauthor")
    assert(!answer.answer.summary.contains("Mallory Impostor"))
    // Without any name map the output keeps ids, exactly as before.
    assert(answer.answer.summary.contains(id("B")) && !answer.answer.summary.contains(label("B")))
    // A wrong name map cannot make a wrong value verify: values and ids are compared as before.
    val scaffold = ClaimScaffold.build(p, bundle, ContextBudget.scaffoldBytes(p, cfg)).head
    val tampered = scaffold.claim.copy(values = scaffold.claim.values.map { v =>
      if (v.field == "coauthorIds") v.copy(ids = Some(Vector(id("D")))) else v
    })
    val claim = AnswerClaim(
      scaffold.claimId,
      SchemaVersions.domain,
      "x",
      scaffold.evidenceIds,
      VerificationStatus.Unverified,
      None,
      provenance,
      Some(tampered)
    )
    val rejected = new ClaimVerificationAgent(cfg).verify(
      p,
      bundle,
      SynthesisProposal(Vector(claim), Vector(claim.claimId), "", "u"),
      Map(id("D") -> "Dr. D Name")
    )
    assert(rejected.answer.claims.isEmpty)
  }

  test(
    "labels that forge ids or path steps, or carry bidi and zero-width characters, are cleaned"
  ) {
    assert(RuntimeNames.clean("Dr.\u200B Ada\u202E Lovelace") == Some("Dr. Ada Lovelace"))
    assert(RuntimeNames.clean("Ada\n\tLovelace  ") == Some("Ada Lovelace"))
    assert(RuntimeNames.clean("Eve researcher:dblp:abcd").isEmpty)
    assert(RuntimeNames.clean("Eve RESEARCHER:x").isEmpty)
    assert(RuntimeNames.clean("Eve → Mallory").isEmpty)
    assert(RuntimeNames.clean("\u200B\u200B").isEmpty)
    assert(RuntimeNames.clean("x" * 201).isEmpty)
    val lookup: String => StorageResult[GraphNode] = i =>
      if (i == id("B")) StorageResult.Found(NamedGraph.node(i, "Eve → Mallory"))
      else if (i == id("C")) StorageResult.Found(NamedGraph.node(i, "Eve researcher:forged"))
      else NamedGraph.stored(i)
    val r = runner(new NamedGraph(lookup = lookup))
    val (p, bundle, stored) =
      run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-forged")
    assert(!stored.contains(id("B")) && !stored.contains(id("C")))
    val text = verified(p, bundle, stored).answer.summary
    assert(!text.contains("Mallory") && !text.contains("forged"), text)
  }

  test("a slow lookup hits the lookup deadline and the run still returns Ready with ids") {
    val slow = cfg.copy(deadlines = cfg.deadlines.copy(evidenceMs = 1500))
    val lookup: String => StorageResult[GraphNode] = i => {
      if (i == id("B")) Thread.sleep(30000)
      NamedGraph.stored(i)
    }
    val g = new NamedGraph(lookup = lookup)
    val r = new WorkflowRunner(
      new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), slow, assets),
      new ResearcherResolverAgent(cache(), slow),
      new CollaborationMetricsAgent(metricStore(), artifacts(), slow),
      new PathFinderAgent(g, metricStore(), artifacts(), slow),
      new CommunityAnalystAgent(g, metricStore(), artifacts(), slow),
      new SemanticContextAgent(
        new InMemoryVectorStore,
        new InMemoryObjectStore,
        new DeterministicHashedEmbeddingClient(EmbeddingModel("synthetic-query", "v1", 8)),
        "synthetic-9b-index",
        slow
      ),
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, slow),
      slow
    )
    val started = System.nanoTime()
    val (p, bundle, stored) = run(r, g1Plan(QueryOperation.DirectCoauthors, "A"), "names-slow")
    val seconds = (System.nanoTime() - started) / 1e9
    assert(seconds < 9.0, s"the slow lookup must not hold the run: $seconds s")
    assert(!stored.contains(id("B")) && stored.contains(id("C")))
    val text = verified(p, bundle, stored).answer.summary
    assert(text.contains(id("B")) && !text.contains(label("B")) && text.contains(label("C")))
  }

  test("the real answer workflow renders names from the graph with a scripted model") {
    val g = new NamedGraph()
    val retrieval = runner(g)
    val audit = new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeAuditStore
    val echo = new LlmClient {
      def complete(request: StructuredLlmRequest): LlmResult = {
        val scaffold = ujson.read(request.userData)("claimScaffold")
        val ids = ujson.Arr.from(scaffold.arr.map(_("claimId")))
        LlmResult.Output(
          ujson
            .Obj(
              "schemaVersion" -> cfg.synthesisSchemaVersion,
              "claims" -> ujson.Arr(),
              "selectedClaimIds" -> ids,
              "narrativeClaimIds" -> ids,
              "interpretation" -> "",
              "uncertainty" -> "Echo model."
            )
            .render(),
          LlmUsage(None, None),
          cfg.model.modelId,
          cfg.model.modelVersion
        )
      }
    }
    val workflow = new RuntimeAnswerWorkflow(
      retrieval,
      new AnswerSynthesisAgent(echo, cfg, assets),
      new ClaimVerificationAgent(cfg),
      audit,
      cfg
    )
    val p = g1Plan(QueryOperation.DirectCoauthors, "A")
    val full = p.copy(runtime = p.runtime.map(_.copy(evidenceOnly = false)))
    workflow.runPlan(full, "query:names-workflow") match {
      case AnswerWorkflowResult.Completed(answer, _) =>
        assert(answer.summary.contains(label("B")) && answer.summary.contains(label("C")))
        assert(answer.summary.contains(id("B")) && answer.summary.contains(id("C")))
      case other => fail(other.toString)
    }
  }

  test("lookups are bounded to rendered researcher ids and the evidence stage") {
    val g = new NamedGraph()
    val r = runner(g)
    run(r, g1Plan(QueryOperation.ResearcherRanking), "names-bound")
    assert(g.lookups.size <= cfg.retrieval.graphLimit * 2)
    assert(g.lookups.distinct == g.lookups)
    assert(g.lookups.forall(RuntimeNames.isResearcherId))
  }
}
