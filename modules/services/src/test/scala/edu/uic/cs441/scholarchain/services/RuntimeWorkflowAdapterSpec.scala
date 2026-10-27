package edu.uic.cs441.scholarchain.services

import org.scalatest.funsuite.AnyFunSuite
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.nio.file.{Files, Path}

class RuntimeWorkflowAdapterSpec extends AnyFunSuite {
  private val cfg = ServiceConfig(Auth.sha256("synthetic-api"), Auth.sha256("synthetic-internal"))
  private val runtimeConfig = RuntimeOfflineFixture.config
  private def fixture(): (RuntimeAnswerWorkflow, InMemoryRuntimeAuditStore) = {
    val assetsRoot = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .get
    val assets = RuntimePromptAssets.fromDirectory(assetsRoot, runtimeConfig).toOption.get
    // This scripted client makes synthesis unavailable; genuine retrieval/verification must
    // abstain without inventing an answer. No provider or SDK client is constructed.
    val model = new ScriptedLlmClient(Vector.empty)
    val graph = RuntimeOfflineFixture.graph()
    val metrics = RuntimeOfflineFixture.metricStore()
    val artifacts = RuntimeOfflineFixture.artifacts()
    val retrieval = new WorkflowRunner(
      new QueryPlannerAgent(model, runtimeConfig, assets),
      new ResearcherResolverAgent(RuntimeOfflineFixture.cache(), runtimeConfig),
      new CollaborationMetricsAgent(metrics, artifacts, runtimeConfig),
      new PathFinderAgent(graph, metrics, artifacts, runtimeConfig),
      new CommunityAnalystAgent(graph, metrics, artifacts, runtimeConfig),
      new SemanticContextAgent(
        new InMemoryVectorStore,
        new InMemoryObjectStore,
        new DeterministicHashedEmbeddingClient(EmbeddingModel("synthetic-service-test", "v1", 8)),
        "synthetic-service-test-index",
        runtimeConfig
      ),
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, runtimeConfig),
      runtimeConfig
    )
    val audit = new InMemoryRuntimeAuditStore
    (
      new RuntimeAnswerWorkflow(
        retrieval,
        new AnswerSynthesisAgent(model, runtimeConfig, assets),
        new ClaimVerificationAgent(runtimeConfig),
        audit,
        runtimeConfig
      ),
      audit
    )
  }
  private def plan(request: QueryRequest): QueryPlan = {
    val p = RuntimeOfflineFixture.plan(QueryOperation.DirectCoauthors, "A")
    p.copy(question = request.question, runtime = p.runtime.map(_.copy(evidenceOnly = false)))
  }
  test("real full runtime adapter persists a truthful abstention when synthesis is unavailable") {
    val (workflow, audit) = fixture()
    val adapter = new RuntimeWorkflowAdapter(workflow, (r, _) => Right(plan(r)))
    val request =
      QueryRequest.parse("{\"question\":\"Synthetic G1 direct coauthors of A\"}", cfg).toOption.get
    val context =
      RequestContext("req-synthetic", "trace-synthetic", "qry-synthetic-runtime-abstention")
    val output = adapter.run(request, context, _ => ()).toOption.get
    assert(output.abstained && output.verificationStatus == "ABSTAINED")
    assert(output.claims.isEmpty)
    assert(StorageResult.value(audit.get(context.queryId)).exists(_.outcome == "ABSTAINED"))
  }
  test("explicit filters cannot be discarded by a runtime plan resolver") {
    val (workflow, audit) = fixture()
    val adapter = new RuntimeWorkflowAdapter(workflow, (r, _) => Right(plan(r)))
    val request = QueryRequest
      .parse(
        "{\"question\":\"Synthetic question\",\"constraints\":{\"topics\":[\"different topic\"]}}",
        cfg
      )
      .toOption
      .get
    val context = RequestContext("r", "t", "qry-filter-rejected")
    assert(adapter.run(request, context, _ => ()).left.toOption.get.status == 422)
    assert(audit.get(context.queryId) == StorageResult.Missing)
  }
  test("explicit inclusion flags and retrieval caps cannot be silently dropped") {
    val (workflow, _) = fixture()
    val adapter = new RuntimeWorkflowAdapter(workflow, (r, _) => Right(plan(r)))
    for (
      extra <- Vector(
        "\"analysis\":{\"includeBridgeMetrics\":true}",
        "\"retrieval\":{\"graphLimit\":1}",
        "\"constraints\":{\"yearFrom\":2015}"
      )
    ) {
      val request =
        QueryRequest.parse("{\"question\":\"Synthetic question\"," + extra + "}", cfg).toOption.get
      assert(
        adapter
          .run(request, RequestContext("r", "t", "qry-caps"), _ => ())
          .left
          .toOption
          .get
          .status == 422
      )
    }
  }
  test(
    "verification metrics distinguish partial, rejected and empty verification from fully verified"
  ) {
    def verdict(id: String, v: ClaimVerdict) = ClaimVerificationResult(id, v, Vector.empty)
    val mixed = VerificationResult(
      Vector(
        verdict("synthetic-accepted", ClaimVerdict.Verified),
        verdict("synthetic-rejected", ClaimVerdict.Unsupported)
      ),
      Vector.empty,
      false
    )
    val rejected = VerificationResult(
      Vector(verdict("synthetic-rejected", ClaimVerdict.Unsupported)),
      Vector.empty,
      false
    )
    assert(RuntimeWorkflowAdapter.verificationLabel(mixed) == "PARTIAL")
    assert(RuntimeWorkflowAdapter.verificationLabel(rejected) == "REJECTED")
    assert(
      RuntimeWorkflowAdapter.verificationLabel(
        VerificationResult(Vector.empty, Vector.empty, false)
      ) == "UNVERIFIED"
    )
    val metrics = new ServiceMetrics
    metrics.workflow(RuntimeWorkflowAdapter.verificationLabel(mixed), false)
    assert(metrics.render.contains("workflow_verification_total{status=\"PARTIAL\"} 1"))
    assert(!metrics.render.contains("status=\"VERIFIED\""))
  }

}
