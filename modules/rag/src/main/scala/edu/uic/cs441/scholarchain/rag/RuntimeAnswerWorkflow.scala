package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.{
  Callable,
  Executors,
  ExecutorService,
  ThreadFactory,
  TimeUnit,
  TimeoutException
}
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal

enum AnswerWorkflowResult {
  case Completed(answer: AnswerResponse, audit: RuntimeAuditEnvelope)
  case EvidenceOnly(bundle: EvidenceBundle, audit: RuntimeAuditEnvelope)
  case Abstained(
      reason: String,
      audit: RuntimeAuditEnvelope,
      candidates: Vector[ResearcherCandidate] = Vector.empty
  )
  case Unsupported(reason: String, audit: RuntimeAuditEnvelope)
  case Failed(failure: StageFailure)
}

/** Full terminal workflow. Audit time is reserved inside the synchronous deadline. No answer or
  * evidence-only result is released before its required immutable audit is durably readable.
  */
final class RuntimeAnswerWorkflow(
    retrieval: WorkflowRunner,
    synthesis: AnswerSynthesisAgent,
    verifier: ClaimVerificationAgent,
    audit: RuntimeAuditStore,
    config: RuntimeConfig
) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  def run(question: String, queryId: String, provenance: Provenance): AnswerWorkflowResult =
    execute(question, queryId, provenance, None)
  def runPlan(plan: QueryPlan, queryId: String): AnswerWorkflowResult =
    execute(plan.question, queryId, plan.provenance, Some(plan))

  private def execute(
      question: String,
      queryId: String,
      provenance: Provenance,
      supplied: Option[QueryPlan]
  ): AnswerWorkflowResult = {
    val started = System.nanoTime()
    val deadline = started + config.operations.synchronousDeadlineMs * 1000000L
    val workDeadline = deadline - config.deadlines.auditMs * 1000000L
    val pool = Executors.newSingleThreadExecutor(new ThreadFactory {
      def newThread(r: Runnable): Thread = {
        val t = new Thread(r, "scholarchain-answer-stage"); t.setDaemon(true); t
      }
    })
    var plan = supplied
    var bundle: Option[EvidenceBundle] = None
    var abstentionCandidates = Vector.empty[ResearcherCandidate]
    var answer: Option[AnswerResponse] = None
    var verification = VerificationResult(Vector.empty, Vector.empty, abstained = true)
    var attempted = Vector.empty[AnswerClaim]
    val plannerUsage = new java.util.concurrent.ConcurrentLinkedQueue[RuntimeModelUsage]()
    var modelUsage = Vector.empty[RuntimeModelUsage]
    var failures = Vector.empty[StageFailure]
    var outcome = "FAILED"
    var reason: Option[String] = None
    var evidenceOnly =
      supplied.flatMap(_.runtime).map(_.evidenceOnly).getOrElse(config.evidenceOnly)
    try {
      val retrievedNamed = timed(pool, workDeadline, "retrieval") {
        supplied match {
          case Some(p) => retrieval.runPlanUntilNamed(p, queryId, workDeadline)
          case None =>
            retrieval.runUntilNamed(
              question,
              queryId,
              provenance,
              workDeadline,
              p => plan = Some(p),
              u => plannerUsage.add(u)
            )
        }
      }
      // Display names are rendering input only; they travel beside the result, not in the bundle.
      val displayNames = retrievedNamed.toOption.map(_.displayNames).getOrElse(Map.empty)
      val retrieved = retrievedNamed.map(_.result)
      retrieved match {
        case Left(f)                                 => failures :+= f; reason = Some(f.reason)
        case Right(WorkflowResult.Unsupported(code)) => outcome = "UNSUPPORTED"; reason = Some(code)
        case Right(WorkflowResult.Abstained(code, candidates, fs)) =>
          outcome = "ABSTAINED"; reason = Some(code); failures ++= fs
          abstentionCandidates = candidates
        case Right(WorkflowResult.Failed(f)) => failures :+= f; reason = Some(f.reason)
        case Right(WorkflowResult.Ready(p, b, partial, fs)) =>
          plan = Some(p); bundle = Some(b); failures ++= fs
          evidenceOnly = p.runtime.exists(_.evidenceOnly)
          if (evidenceOnly) {
            outcome = "EVIDENCE_ONLY"; verification = verification.copy(abstained = false)
          } else {
            val synthesisDeadline = math.min(
              workDeadline - config.deadlines.verificationMs * 1000000L,
              System.nanoTime() + config.deadlines.synthesisMs * 1000000L
            )
            val proposed = timed(pool, synthesisDeadline, "synthesis")(synthesis.synthesize(p, b))
            val proposal = proposed match {
              case Left(f) =>
                failures :+= f; reason = Some(f.reason);
                SynthesisProposal(Vector.empty, Vector.empty, "", "Synthesis unavailable.")
              case Right(SynthesisResult.Proposed(value)) => value
              case Right(SynthesisResult.Abstained(code, usage)) =>
                reason = Some(code);
                SynthesisProposal(Vector.empty, Vector.empty, "", "Synthesis abstained.", usage)
              case Right(SynthesisResult.Failed(code)) =>
                reason = Some(code);
                SynthesisProposal(Vector.empty, Vector.empty, "", "Synthesis failed.")
            }
            modelUsage = proposal.usage; attempted = proposal.claims
            val verified = timed(
              pool,
              math
                .min(workDeadline, System.nanoTime() + config.deadlines.verificationMs * 1000000L),
              "verification"
            ) {
              verifier.verify(p, b, proposal, displayNames)
            }
            verified match {
              case Left(f) => failures :+= f; reason = Some(f.reason)
              case Right(v) =>
                answer = Some(v.answer); verification = v.verification
                outcome = if (verification.abstained) "ABSTAINED" else "ANSWERED"
                if (!v.interpretationAccepted && proposal.interpretation.trim.nonEmpty)
                  failures :+= StageFailure("interpretation", "interpretation-rejected")
                if (partial && reason.isEmpty) reason = Some("partial-retrieval")
            }
          }
      }
      modelUsage = plannerUsage.iterator().asScala.toVector ++ modelUsage
      val answerHash = answer
        .map(a => StableIds.sha256Hex(CoreJson.compact(a)))
        .orElse(bundle.filter(_ => evidenceOnly).map(b => StableIds.sha256Hex(CoreJson.compact(b))))
        .getOrElse {
          if (outcome == "ABSTAINED")
            StableIds.sha256Hex(
              ujson
                .Obj(
                  "reason" -> reason.getOrElse("insufficient-evidence"),
                  "candidates" -> upickle.default.writeJs(abstentionCandidates)
                )
                .render()
            )
          else StableIds.sha256Hex(CoreJson.compact((outcome, reason)))
        }
      val record = plan.map { p =>
        val deterministicSubjects = bundle.toVector
          .flatMap(_.items)
          .filterNot(_.runtime.exists(_.descriptive))
          .flatMap(_.runtime.toVector.flatMap(_.subjectIds))
        val resolved = bundle.toVector.flatMap(
          _.runtime.toVector.flatMap(_.resolvedCandidates).map(_.researcherId)
        )
        AuditRecord(
          queryId,
          queryId,
          p,
          (resolved ++ deterministicSubjects)
            .filter(StableIds.parseResearcherId(_).isRight)
            .distinct,
          bundle.toVector.flatMap(_.items.map(_.evidenceId)),
          bundle.toVector.flatMap(_.runtime.toVector.flatMap(_.metricVersions)),
          bundle.toVector.flatMap(_.runtime.toVector.flatMap(_.graphRunIds)),
          modelUsage,
          (System.nanoTime() - started) / 1000000L,
          attempted,
          verification,
          answerHash
        )
      }
      val envelope = RuntimeAuditEnvelope(
        queryId,
        queryId,
        question,
        outcome,
        reason,
        record,
        failures.map(f => RuntimeAuditFailure(f.stage, f.reason)),
        (System.nanoTime() - started) / 1000000L,
        answerHash,
        modelUsage,
        evidenceOnly
      )
      val persisted = timed(
        pool,
        math.min(deadline, System.nanoTime() + config.deadlines.auditMs * 1000000L),
        "audit"
      ) {
        val stored = audit.put(envelope)
        StorageResult.successful(stored) && StorageResult.value(stored).contains(envelope) &&
        StorageResult.value(audit.get(queryId)).contains(envelope)
      }
      persisted match {
        case Left(f) => AnswerWorkflowResult.Failed(f)
        case Right(false) =>
          AnswerWorkflowResult.Failed(StageFailure("audit", "audit-persistence-failed"))
        case Right(true) =>
          if (outcome == "EVIDENCE_ONLY") AnswerWorkflowResult.EvidenceOnly(bundle.get, envelope)
          else if (answer.nonEmpty) AnswerWorkflowResult.Completed(answer.get, envelope)
          else if (outcome == "UNSUPPORTED")
            AnswerWorkflowResult.Unsupported(reason.getOrElse("unsupported-query"), envelope)
          else if (outcome == "ABSTAINED")
            AnswerWorkflowResult.Abstained(
              reason.getOrElse("insufficient-evidence"),
              envelope,
              abstentionCandidates
            )
          else
            AnswerWorkflowResult.Failed(
              failures.headOption.getOrElse(
                StageFailure("workflow", reason.getOrElse("workflow-failed"))
              )
            )
      }
    } catch {
      case _: InterruptedException =>
        Thread.currentThread().interrupt()
        AnswerWorkflowResult.Failed(StageFailure("workflow", "workflow-interrupted"))
      case NonFatal(_) =>
        val failure = StageFailure("workflow", "workflow-execution-failed")
        val fallback = RuntimeAuditEnvelope(
          queryId,
          queryId,
          question,
          "FAILED",
          Some(failure.reason),
          None,
          Vector(RuntimeAuditFailure(failure.stage, failure.reason)),
          (System.nanoTime() - started) / 1000000L,
          StableIds.sha256Hex("workflow-execution-failed"),
          plannerUsage.iterator().asScala.toVector ++ modelUsage,
          evidenceOnly
        )
        timed(pool, deadline, "audit") {
          StorageResult.value(audit.put(fallback)).contains(fallback) && StorageResult
            .value(audit.get(queryId))
            .contains(fallback)
        } match {
          case Right(true) => AnswerWorkflowResult.Failed(failure)
          case _ => AnswerWorkflowResult.Failed(StageFailure("audit", "audit-persistence-failed"))
        }
    } finally {
      pool.shutdownNow()
      try pool.awaitTermination(math.max(0L, deadline - System.nanoTime()), TimeUnit.NANOSECONDS)
      catch { case _: InterruptedException => Thread.currentThread().interrupt() }
    }
  }
  private def timed[A](pool: ExecutorService, deadline: Long, stage: String)(
      body: => A
  ): Either[StageFailure, A] = {
    val remaining = deadline - System.nanoTime()
    if (remaining <= 0) return Left(StageFailure(stage, "stage-deadline"))
    val future = pool.submit(new Callable[A] { def call(): A = body })
    try Right(future.get(remaining, TimeUnit.NANOSECONDS))
    catch {
      case _: TimeoutException => future.cancel(true); Left(StageFailure(stage, "stage-deadline"))
      case _: InterruptedException =>
        future.cancel(true); Thread.currentThread().interrupt();
        Left(StageFailure(stage, "stage-interrupted"))
      case NonFatal(_) => future.cancel(true); Left(StageFailure(stage, "stage-execution-failed"))
    }
  }
}
