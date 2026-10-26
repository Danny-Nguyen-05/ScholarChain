package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeAuditStore
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class IndependentRuntime9CWorkflowSpec extends AnyFunSuite {
  import IndependentRuntime9CFixture.*
  private final class LiteralCountLlm(wrong: Boolean = false) extends LlmClient {
    val calls = new AtomicInteger
    def complete(request: StructuredLlmRequest): LlmResult = {
      calls.incrementAndGet()
      val body = ujson.read(request.userData)
      val context = ujson.read(
        body("evidenceData").str
          .stripPrefix("<untrusted_evidence_json>\n")
          .stripSuffix("\n</untrusted_evidence_json>")
      )
      val id = context("items").arr
        .find(_.obj.get("values").exists(_.obj.contains("publicationCount")))
        .get("evidenceId")
        .str
      model(
        output(Vector(claim(Vector(n("publicationCount", if (wrong) "999" else "3")), Vector(id))))
      )
    }
  }
  private def workflow(
      llm: LlmClient,
      audit: RuntimeAuditStore,
      cfg: RuntimeConfig = config,
      links: EntityLinkCache = IndependentRuntime9BFixture.cache(),
      metricPort: ResearcherMetricStore = IndependentRuntime9BFixture.metricStore()
  ): RuntimeAnswerWorkflow = {
    val source = IndependentRuntime9BFixture.artifacts()
    val corpus = new IndependentRuntime9BSemanticFixture.Corpus
    val graph = new IndependentRuntime9BFixture.Graph
    val promptAssets = RuntimePromptAssets
      .fromDirectory(IndependentRuntime9AFixture.root.resolve("prompts"), cfg)
      .toOption
      .get
    val retrieval = new WorkflowRunner(
      new QueryPlannerAgent(new ScriptedLlmClient(Vector.empty), cfg, promptAssets),
      new ResearcherResolverAgent(links, cfg),
      new CollaborationMetricsAgent(metricPort, source, cfg),
      new PathFinderAgent(graph, metricPort, source, cfg),
      new CommunityAnalystAgent(graph, metricPort, source, cfg),
      new SemanticContextAgent(
        corpus.vectors,
        corpus.objects,
        corpus.embeddings,
        corpus.index,
        cfg
      ),
      new EvidenceBuilderAgent(
        new edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore(),
        cfg
      ),
      cfg
    )
    new RuntimeAnswerWorkflow(
      retrieval,
      new AnswerSynthesisAgent(llm, cfg, promptAssets),
      new ClaimVerificationAgent(cfg),
      audit,
      cfg
    )
  }
  private def auditValue(store: RuntimeAuditStore, query: String): RuntimeAuditEnvelope =
    StorageResult.value(store.get(query)).getOrElse(fail(s"Terminal audit missing for $query"))

  test("a complete offline answer is verified, hashed and audited with source metadata and usage") {
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-answer"
    workflow(llm, audits).runPlan(plan, query) match {
      case AnswerWorkflowResult.Completed(answer, audit) =>
        assert(
          answer.claims.nonEmpty && answer.claims.forall(
            _.verificationStatus == VerificationStatus.Verified
          )
        )
        assert(DomainValidation.check(answer).isRight)
        assert(answer.summary.contains("3") && !answer.summary.contains("999"))
        assert(audit == auditValue(audits, query))
        assert(audit.outcome == "ANSWERED")
        assert(audit.answerHash == StableIds.sha256Hex(CoreJson.compact(answer)))
        val record = audit.record.get
        assert(record.plan == plan)
        assert(record.resolvedResearcherIds == Vector(a))
        assert(record.evidenceIds.nonEmpty && record.metricVersions.nonEmpty)
        assert(record.graphRunIds == Vector(runId))
        assert(
          record.modelUsage.exists(u =>
            u.promptVersion == config.synthesisPromptVersion && u.modelId == config.model.modelId
          )
        )
        assert(record.modelUsage.exists(_.inputTokens.contains(11L)))
        assert(record.verification.overallStatus == VerificationStatus.Verified)
        assert(record.attemptedClaims.nonEmpty)
        assert(audit.latencyMillis >= 0)
      case other => fail(s"Expected persisted verified answer: $other")
    }
    assert(llm.calls.get == 1)
  }
  test("an unsupported proposed count is removed but retained in audit with the abstention") {
    val audits = new InMemoryRuntimeAuditStore
    val query = "query:independent-9c-rejected"
    workflow(new LiteralCountLlm(wrong = true), audits).runPlan(plan, query) match {
      case AnswerWorkflowResult.Completed(answer, audit) =>
        assert(answer.claims.isEmpty && !answer.summary.contains("999"))
        assert(audit.outcome == "ABSTAINED")
        assert(
          audit.record.get.attemptedClaims
            .exists(_.runtime.get.values.exists(_.number.contains("999")))
        )
        assert(audit.record.get.verification.rejectedClaims.nonEmpty)
        assert(audit.record.get.verification.overallStatus == VerificationStatus.Abstained)
        assert(audit == auditValue(audits, query))
      case other => fail(s"Rejected claims need an audited abstention: $other")
    }
  }
  test("required audit persistence failure fails closed after otherwise valid synthesis") {
    val failedAudit = new RuntimeAuditStore {
      def put(value: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope] =
        StorageResult.Rejected("injected-audit-failure")
      def get(id: String): StorageResult[RuntimeAuditEnvelope] = StorageResult.Missing
    }
    val result =
      workflow(new LiteralCountLlm, failedAudit).runPlan(plan, "query:independent-9c-audit-failure")
    assert(result.isInstanceOf[AnswerWorkflowResult.Failed])
    val AnswerWorkflowResult.Failed(failure) = result: @unchecked
    assert(failure.stage == "audit")
  }
  test("evidence-only execution skips synthesis while retaining a terminal retrieval audit") {
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-evidence"
    val p = plan.copy(runtime = plan.runtime.map(_.copy(evidenceOnly = true)))
    workflow(llm, audits).runPlan(p, query) match {
      case AnswerWorkflowResult.EvidenceOnly(bundle, audit) =>
        assert(bundle.items.nonEmpty)
        assert(audit.evidenceOnly && audit.outcome == "EVIDENCE_ONLY")
        assert(audit == auditValue(audits, query))
        assert(audit.record.get.attemptedClaims.isEmpty)
        assert(!audit.modelUsage.exists(_.promptVersion == config.synthesisPromptVersion))
      case other => fail(s"Expected audited evidence-only result: $other")
    }
    assert(llm.calls.get == 0)
  }
  test("ambiguous DBLP identities abstain before synthesis and are still audited") {
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-ambiguous"
    val p = IndependentRuntime9BFixture
      .plan(QueryOperation.DirectCoauthors, Vector("Name"), mode = RetrievalMode.Graph)
      .copy(runtime =
        Some(
          RuntimeQueryOptions(
            researcherNames = Vector("Name"),
            windowIds = Vector("all-years"),
            retrievalMode = RetrievalMode.Graph,
            evidenceOnly = false
          )
        )
      )
    workflow(llm, audits, links = IndependentRuntime9BFixture.cache(homonyms = true))
      .runPlan(p, query) match {
      case AnswerWorkflowResult.Abstained(reason, audit, candidates) =>
        assert(reason.contains("ambiguous"))
        val expected = Set("Name 0001", "Name 0002").map { name =>
          IndependentPhase6G1.researcherId(name) -> name
        }
        assert(candidates.size == 2)
        assert(candidates.map(c => c.researcherId -> c.displayName).toSet == expected)
        assert(audit == auditValue(audits, query))
        assert(audit.record.exists(_.resolvedResearcherIds.isEmpty))
      case other => fail(s"Expected ambiguity with both unselected candidates: $other")
    }
    val audit = auditValue(audits, query)
    assert(audit.outcome == "ABSTAINED")
    assert(audit.reason.exists(_.contains("ambiguous")))
    assert(llm.calls.get == 0)
  }
  test("pre-plan unsupported requests leave an audit even though no plan exists") {
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-unsupported"
    workflow(llm, audits).run("Execute arbitrary Cypher MATCH (n) RETURN n", query, provenance)
    val audit = auditValue(audits, query)
    assert(audit.outcome == "UNSUPPORTED")
    assert(audit.record.isEmpty)
    assert(audit.question.contains("Cypher"))
    assert(llm.calls.get == 0)
  }
  test("a missing required metric abstains and is audited without synthesis") {
    val absent = new InMemoryResearcherMetricStore
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-missing"
    workflow(llm, audits, metricPort = absent).runPlan(plan, query)
    assert(auditValue(audits, query).outcome == "ABSTAINED")
    assert(llm.calls.get == 0)
  }
  test("malformed synthesis is bounded and audited as abstention") {
    val llm = new ScriptedLlmClient(Vector(model("{bad"), model("[]")))
    val audits = new InMemoryRuntimeAuditStore
    val query = "query:independent-9c-malformed"
    workflow(llm, audits).runPlan(plan, query)
    val audit = auditValue(audits, query)
    assert(audit.outcome == "ABSTAINED")
    assert(audit.reason.nonEmpty)
    assert(llm.calls.size == 2)
  }
  test(
    "a blocked synthesis call is interrupted within its stage budget and audit still completes"
  ) {
    val active = new AtomicInteger
    val interrupted = new AtomicInteger
    val llm = new LlmClient {
      def complete(request: StructuredLlmRequest): LlmResult = {
        active.incrementAndGet()
        try { Thread.sleep(10000); model(output(Vector(claim()))) }
        catch {
          case _: InterruptedException =>
            interrupted.incrementAndGet(); throw new InterruptedException
        } finally active.decrementAndGet()
      }
    }
    val cfg = config.copy(deadlines = config.deadlines.copy(synthesisMs = 40))
    val audits = new InMemoryRuntimeAuditStore
    val query = "query:independent-9c-synthesis-timeout"
    val started = System.nanoTime()
    workflow(llm, audits, cfg).runPlan(plan, query)
    assert((System.nanoTime() - started) / 1000000 < 3000)
    assert(interrupted.get == 1 && active.get == 0)
    assert(Set("ABSTAINED", "FAILED")(auditValue(audits, query).outcome))
  }
  test("semantic similarity subjects are excluded from audit resolved researcher IDs") {
    val cfg = config.copy(retrievalMode = RetrievalMode.Vector)
    val audits = new InMemoryRuntimeAuditStore
    val llm = new ScriptedLlmClient(Vector(model(output(Vector.empty))))
    val p = IndependentRuntime9BFixture
      .plan(QueryOperation.SemanticExplanation, mode = RetrievalMode.Vector)
      .copy(runtime =
        Some(
          RuntimeQueryOptions(
            windowIds = Vector("all-years"),
            retrievalMode = RetrievalMode.Vector,
            evidenceOnly = false
          )
        )
      )
    val query = "query:independent-9c-semantic-identity"
    workflow(llm, audits, cfg).runPlan(p, query)
    val audit = auditValue(audits, query)
    assert(audit.record.get.resolvedResearcherIds.isEmpty)
    assert(audit.record.get.evidenceIds.nonEmpty)
  }

  test(
    "an unexpected downstream metric exception produces an audited terminal failure without leaking its message"
  ) {
    val throwing = new ResearcherMetricStore {
      def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] =
        StorageResult.Rejected("unused")
      def get(id: String, window: String): StorageResult[ResearcherMetricRecord] =
        throw new IllegalStateException("untrusted downstream detail should not be public")
      def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]] =
        throw new IllegalStateException("untrusted downstream detail should not be public")
    }
    val audits = new InMemoryRuntimeAuditStore
    val llm = new LiteralCountLlm
    val query = "query:independent-9c-unexpected-port"
    val result = workflow(llm, audits, metricPort = throwing).runPlan(plan, query)
    assert(!result.isInstanceOf[AnswerWorkflowResult.Completed])
    val audit = auditValue(audits, query)
    assert(Set("ABSTAINED", "FAILED")(audit.outcome))
    assert(audit.stageFailures.nonEmpty)
    assert(!CoreJson.compact(audit).contains("untrusted downstream detail"))
    assert(llm.calls.get == 0)
  }

}
