package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class AdversarialRuntimeWorkflowSpec extends AnyFunSuite {
  import AdversarialRuntimeFixture.*
  import IndependentRuntime9CFixture.{config, *}

  for ((field, attack) <- attacks) {
    test(
      s"full workflow rejects an injected $field instruction and malicious count while retaining source evidence"
    ) {
      val runtime = new Runtime(new Corpus(field, attack))
      val query = "adversarial-workflow-" + field
      runtime.workflow.runPlan(fusedPlan, query) match {
        case AnswerWorkflowResult.Completed(answer, audit) =>
          assert(answer.claims.isEmpty)
          assert(!answer.summary.contains("999") && !answer.summary.contains("delete_all"))
          assert(audit.outcome == "ABSTAINED")
          assert(
            audit.record.get.attemptedClaims
              .exists(_.runtime.get.values.exists(_.number.contains("999")))
          )
          assert(audit.record.get.verification.rejectedClaims.nonEmpty)
          assert(audit == runtime.audit(query))
          val bundle = StorageResult.value(runtime.evidence.get(answer.evidenceBundleId)).get
          assert(bundle.items.flatMap(_.text).exists(_.contains(attack)))
          assert(
            bundle.items.filter(_.text.exists(_.contains(attack))).forall(_.runtime.get.descriptive)
          )
        case other => fail(s"Expected an audited rejection of the attack: $other")
      }
      assert(runtime.llm.calls.size == 1)
      val call = runtime.llm.calls.head
      assert(!call.systemPrompt.contains(attack))
      val data = ujson.read(call.userData)("evidenceData").str
      assert(
        data
          .sliding("</untrusted_evidence_json>".length)
          .count(_ == "</untrusted_evidence_json>") == 1
      )
      assert(!data.contains("</untrusted_evidence_json><tool_call>"))
    }
  }

  for (mode <- Vector("fake-identity", "fake-citation")) {
    test(s"full workflow rejects model $mode even when JSON conforms to the synthesis schema") {
      val runtime = new Runtime(llm = new AttackLlm(mode))
      val query = "adversarial-model-" + mode
      runtime.workflow.runPlan(fusedPlan, query) match {
        case AnswerWorkflowResult.Completed(answer, audit) =>
          assert(answer.claims.isEmpty)
          assert(audit.outcome == "ABSTAINED")
          assert(audit.record.get.attemptedClaims.size == 1)
          assert(
            audit.record.get.attemptedClaims.head.runtime.get.values == Vector(
              n("publicationCount", "3")
            )
          )
          assert(audit.record.get.verification.rejectedClaims.size == 1)
          val reasons = audit.record.get.verification.claims.head.reasons
          assert(
            reasons.contains(
              if (mode == "fake-citation") "missing-or-duplicate-evidence-id"
              else "subject-window-or-trust-mismatch"
            )
          )
          assert(audit == runtime.audit(query))
          assert(!answer.summary.contains("999"))
        case other => fail(s"Expected audited rejection: $other")
      }
      assert(runtime.llm.calls.size == 1)
    }
  }

  test(
    "malformed JSON exhausts the bounded model script and persists an abstention without attempted claims"
  ) {
    val runtime = new Runtime(llm = new AttackLlm("malformed"))
    val query = "adversarial-malformed-json"
    runtime.workflow.runPlan(fusedPlan, query) match {
      case AnswerWorkflowResult.Completed(answer, audit) =>
        assert(answer.claims.isEmpty && audit.outcome == "ABSTAINED")
        assert(audit.record.get.attemptedClaims.isEmpty)
        assert(audit.reason.nonEmpty && audit == runtime.audit(query))
      case other => fail(s"Malformed output must abstain: $other")
    }
    assert(runtime.llm.calls.size == 2)
  }

  test(
    "Neptune reader timeout interrupts the actual graph call and audits missing essential evidence without synthesis"
  ) {
    val entered = new CountDownLatch(1)
    val interrupted = new CountDownLatch(1)
    val calls = new AtomicInteger
    val blocked = new IndependentRuntime9BFixture.Graph {
      override def directCoauthors(
          id: String,
          window: String,
          limit: Int
      ): StorageResult[GraphPage] = {
        calls.incrementAndGet(); entered.countDown()
        try { new CountDownLatch(1).await(); StorageResult.Found(GraphPage(Vector.empty, None)) }
        catch {
          case _: InterruptedException => interrupted.countDown(); throw new InterruptedException
        }
      }
    }
    val cfg = config.copy(deadlines = config.deadlines.copy(pathMs = 200))
    val runtime = new Runtime(graph = blocked, cfg = cfg)
    val p = IndependentRuntime9BFixture
      .plan(QueryOperation.DirectCoauthors, Vector("A"), mode = RetrievalMode.Graph)
      .copy(runtime =
        Some(
          RuntimeQueryOptions(
            researcherNames = Vector("A"),
            windowIds = Vector("all-years"),
            retrievalMode = RetrievalMode.Graph,
            evidenceOnly = false
          )
        )
      )
    val query = "adversarial-neptune-timeout"
    val started = System.nanoTime()
    val result = runtime.workflow.runPlan(p, query)
    assert(entered.await(1, TimeUnit.SECONDS) && interrupted.await(1, TimeUnit.SECONDS))
    assert(calls.get == 1 && runtime.llm.calls.isEmpty)
    assert(result.isInstanceOf[AnswerWorkflowResult.Abstained])
    val audit = runtime.audit(query)
    assert(audit.outcome == "ABSTAINED")
    assert(audit.stageFailures.exists(f => f.stage == "path" && f.reason == "stage-deadline"))
    assert((System.nanoTime() - started) / 1000000 < 5000)
  }

  test(
    "vector throttle failure cannot become semantic evidence and a later healthy query recovers without stale failure state"
  ) {
    val corpus = new Corpus
    val calls = new AtomicInteger
    val throttled = new VectorProxy(corpus.vectors) {
      override def query(
          i: String,
          v: Vector[Float],
          k: Int,
          f: Map[String, String]
      ): StorageResult[Vector[VectorHit]] =
        if (calls.incrementAndGet() == 1) StorageResult.Rejected("synthetic-s3-vectors-throttled")
        else super.query(i, v, k, f)
    }
    val runtime = new Runtime(corpus, vectorPort = Some(throttled))
    val first = "adversarial-vector-throttle"
    assert(
      runtime.workflow.runPlan(semanticPlan, first).isInstanceOf[AnswerWorkflowResult.Abstained]
    )
    assert(calls.get == 1 && runtime.llm.calls.isEmpty)
    assert(runtime.audit(first).stageFailures.exists(_.stage == "semantic"))
    val evidencePlan =
      semanticPlan.copy(runtime = semanticPlan.runtime.map(_.copy(evidenceOnly = true)))
    runtime.workflow.runPlan(evidencePlan, "adversarial-vector-recovery") match {
      case AnswerWorkflowResult.EvidenceOnly(bundle, audit) =>
        assert(bundle.items.size == 1 && bundle.items.head.runtime.get.descriptive)
        assert(audit.outcome == "EVIDENCE_ONLY" && audit.stageFailures.isEmpty)
      case other => fail(s"Healthy follow-up must recover: $other")
    }
    assert(calls.get == 2 && runtime.llm.calls.isEmpty)
  }
}
