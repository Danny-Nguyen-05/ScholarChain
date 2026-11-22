package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.util.concurrent.{
  Callable,
  Executors,
  ExecutorService,
  Future,
  ThreadFactory,
  TimeUnit,
  TimeoutException
}
import scala.util.control.NonFatal

enum WorkflowResult {
  case Ready(
      plan: QueryPlan,
      bundle: EvidenceBundle,
      partial: Boolean,
      failures: Vector[StageFailure]
  )
  case Abstained(
      reason: String,
      candidates: Vector[ResearcherCandidate],
      failures: Vector[StageFailure]
  )
  case Unsupported(reason: String)
  case Failed(failure: StageFailure)
}

/** A workflow result with the runtime-only display names of its bundle's researcher ids. The names
  * travel beside the result (the evidence record is a core contract and stays unchanged) and are
  * empty for every result other than a Ready one that had names to look up.
  */
final case class NamedWorkflowResult(result: WorkflowResult, displayNames: Map[String, String])

/** Subphase9B terminates at persisted evidence for both evidenceOnly settings. Synthesis,
  * verification and audit are intentionally later stages. The caller receives no final answer.
  * Every blocking port call runs in an interruptible task bounded by its stage and overall
  * deadline. Cancellation cannot forcibly stop a port that ignores interruption; adapters must
  * honor it.
  */
final class WorkflowRunner(
    planner: QueryPlannerAgent,
    resolver: ResearcherResolverAgent,
    metrics: CollaborationMetricsAgent,
    path: PathFinderAgent,
    community: CommunityAnalystAgent,
    semantic: SemanticContextAgent,
    evidence: EvidenceBuilderAgent,
    config: RuntimeConfig
) {
  require(RuntimeConfigValidation.check(config).isEmpty)

  private case class Completed[A](value: A, finishedNanos: Long)
  private def completed[A](body: => A): Completed[A] = {
    val value = body; Completed(value, System.nanoTime())
  }
  private val deterministicOperations = Set(
    QueryOperation.ResearcherRanking,
    QueryOperation.MaximumTeamSize,
    QueryOperation.ComponentLookup,
    QueryOperation.DirectCoauthors,
    QueryOperation.ShortestPath,
    QueryOperation.CommunityComparison,
    QueryOperation.BridgeRanking,
    QueryOperation.TemporalComparison
  )
  private def executor(): ExecutorService = Executors.newFixedThreadPool(
    4,
    new ThreadFactory {
      def newThread(r: Runnable): Thread = {
        val t = new Thread(r, "scholarchain-runtime-worker")
        t.setDaemon(true); t
      }
    }
  )
  def run(question: String, queryId: String, provenance: Provenance): WorkflowResult =
    runUntil(
      question,
      queryId,
      provenance,
      System.nanoTime() + config.operations.synchronousDeadlineMs * 1000000L
    )
  def runUntil(
      question: String,
      queryId: String,
      provenance: Provenance,
      deadline: Long,
      planSink: QueryPlan => Unit = _ => (),
      usageSink: RuntimeModelUsage => Unit = _ => ()
  ): WorkflowResult =
    runUntilNamed(question, queryId, provenance, deadline, planSink, usageSink).result
  def runUntilNamed(
      question: String,
      queryId: String,
      provenance: Provenance,
      deadline: Long,
      planSink: QueryPlan => Unit = _ => (),
      usageSink: RuntimeModelUsage => Unit = _ => ()
  ): NamedWorkflowResult = {
    val pool = executor()
    var names = Map.empty[String, String]
    val result =
      try
        timed(pool, deadline, "planner", config.deadlines.plannerMs)(
          planner.plan(question, queryId, provenance, usageSink)
        ) match {
          case Left(failure) => WorkflowResult.Failed(failure)
          case Right(PlannerResult.Planned(plan, _, _)) =>
            planSink(plan); execute(plan, queryId, pool, deadline, n => names = n)
          case Right(PlannerResult.Unsupported(reason, _)) => WorkflowResult.Unsupported(reason)
          case Right(PlannerResult.Failed(reason)) =>
            WorkflowResult.Failed(StageFailure("planner", reason))
        }
      finally close(pool, deadline)
    NamedWorkflowResult(result, names)
  }
  def runPlan(plan: QueryPlan, queryId: String): WorkflowResult =
    runPlanUntil(
      plan,
      queryId,
      System.nanoTime() + config.operations.synchronousDeadlineMs * 1000000L
    )
  def runPlanUntil(plan: QueryPlan, queryId: String, deadline: Long): WorkflowResult =
    runPlanUntilNamed(plan, queryId, deadline).result
  def runPlanNamed(plan: QueryPlan, queryId: String): NamedWorkflowResult =
    runPlanUntilNamed(
      plan,
      queryId,
      System.nanoTime() + config.operations.synchronousDeadlineMs * 1000000L
    )
  def runPlanUntilNamed(plan: QueryPlan, queryId: String, deadline: Long): NamedWorkflowResult = {
    val pool = executor()
    var names = Map.empty[String, String]
    val result =
      try execute(plan, queryId, pool, deadline, n => names = n)
      finally close(pool, deadline)
    NamedWorkflowResult(result, names)
  }
  private def execute(
      plan: QueryPlan,
      queryId: String,
      pool: ExecutorService,
      deadline: Long,
      nameSink: Map[String, String] => Unit
  ): WorkflowResult = {
    if (DomainValidation.check(plan).isLeft || plan.runtime.isEmpty)
      return WorkflowResult.Unsupported("invalid-runtime-plan")
    val options = plan.runtime.get
    if (options.windowIds.isEmpty || !options.windowIds.forall(config.windowIds.contains))
      return WorkflowResult.Unsupported("window-not-stored")
    if (
      options.retrievalMode == RetrievalMode.Vector && plan.operations.exists(
        deterministicOperations
      )
    )
      return WorkflowResult.Abstained(
        "vector-mode-cannot-authorize-deterministic-claims",
        Vector.empty,
        Vector.empty
      )
    val candidates =
      timed(pool, deadline, "resolver", config.deadlines.resolverMs)(resolver.resolve(plan)) match {
        case Left(f)                            => return WorkflowResult.Failed(f)
        case Right(ResolverResult.Resolved(cs)) => cs
        case Right(ResolverResult.Ambiguous(_, cs, total, truncated)) =>
          return WorkflowResult.Abstained(
            s"ambiguous-researcher:returned=${cs.size}:total=$total:truncated=$truncated",
            cs,
            Vector.empty
          )
        case Right(ResolverResult.NotFound(_)) =>
          return WorkflowResult.Abstained("researcher-not-found", Vector.empty, Vector.empty)
        case Right(ResolverResult.Failed(reason)) =>
          return WorkflowResult.Failed(StageFailure("resolver", reason))
      }
    val input = RetrievalInput(plan, candidates)
    val jobs = Vector.newBuilder[(String, Long, () => RetrievalResult, Boolean)]
    if (options.retrievalMode != RetrievalMode.Vector) {
      if (
        plan.operations.exists(
          Set(
            QueryOperation.ResearcherRanking,
            QueryOperation.MaximumTeamSize,
            QueryOperation.ComponentLookup
          )
        )
      )
        jobs += (("metrics", config.deadlines.metricsMs, () => metrics.run(input), true))
      if (plan.operations.exists(Set(QueryOperation.DirectCoauthors, QueryOperation.ShortestPath)))
        jobs += (("path", config.deadlines.pathMs, () => path.run(input), true))
      if (
        plan.operations.exists(
          Set(
            QueryOperation.CommunityComparison,
            QueryOperation.BridgeRanking,
            QueryOperation.TemporalComparison
          )
        )
      )
        jobs += (("community", config.deadlines.communityMs, () => community.run(input), true))
    }
    if (options.retrievalMode != RetrievalMode.Graph)
      jobs += ((
        "semantic",
        config.deadlines.semanticMs,
        () => semantic.run(input),
        !plan.operations.exists(deterministicOperations)
      ))
    val active = jobs.result().map { (name, millis, fn, essential) =>
      val expires = math.min(deadline, System.nanoTime() + millis * 1000000L)
      (
        name,
        expires,
        pool.submit(new Callable[Completed[RetrievalResult]] {
          def call(): Completed[RetrievalResult] = completed(fn())
        }),
        essential
      )
    }
    var outputs = Vector.empty[RetrievalOutput]; var failures = Vector.empty[StageFailure]
    var essentialMissing = false; var unsupported: Option[String] = None
    active.foreach { (name, expires, task, essential) =>
      await(task, expires, name) match {
        case Right(RetrievalResult.Ready(output)) => outputs :+= output
        case Right(RetrievalResult.Unsupported(_, reason)) =>
          failures :+= StageFailure(name, reason)
          if (essential) { essentialMissing = true; unsupported = Some(reason) }
        case Right(RetrievalResult.Missing(_, reason)) =>
          failures :+= StageFailure(name, reason); if (essential) essentialMissing = true
        case Right(RetrievalResult.Failed(_, reason)) =>
          failures :+= StageFailure(name, reason); if (essential) essentialMissing = true
        case Left(f) => failures :+= f; if (essential) essentialMissing = true
      }
    }
    if (essentialMissing) {
      unsupported match {
        case Some(reason) => return WorkflowResult.Unsupported(reason)
        case None =>
          return WorkflowResult.Abstained("essential-evidence-unavailable", candidates, failures)
      }
    }
    timed(pool, deadline, "evidence", config.deadlines.evidenceMs)(
      evidence.build(queryId, input, outputs)
    ) match {
      case Left(f) => WorkflowResult.Failed(f)
      case Right(EvidenceBuildResult.Persisted(bundle)) =>
        nameSink(lookupNames(plan, bundle, pool, deadline))
        WorkflowResult.Ready(
          plan,
          bundle,
          failures.nonEmpty || bundle.runtime.exists(_.truncated),
          failures
        )
      case Right(EvidenceBuildResult.Missing(reason)) =>
        WorkflowResult.Abstained(reason, candidates, failures)
      case Right(EvidenceBuildResult.Failed(reason)) =>
        WorkflowResult.Failed(StageFailure("evidence", reason))
    }
  }

  /** Names come only from stored graph nodes (never from model output). Only researcher ids that
    * the deterministic evidence renders are looked up (none for a plan that renders none), at most
    * twice the plan's graph limit, in parallel. The lookups have their own budget of the evidence
    * stage deadline, started after the evidence is persisted and still capped by the overall
    * workflow deadline. A missing, failed or late lookup leaves that id without a name; it never
    * fails the workflow.
    */
  private def lookupNames(
      plan: QueryPlan,
      bundle: EvidenceBundle,
      pool: ExecutorService,
      deadline: Long
  ): Map[String, String] = {
    val resolved = bundle.runtime.toVector
      .flatMap(_.resolvedCandidates)
      .map(c => c.researcherId -> c.displayName)
      .toMap
    val wanted = RuntimeNames.renderedResearcherIds(bundle).filterNot(resolved.contains)
    val limited = wanted.take(2 * math.min(plan.graphLimit, config.retrieval.graphLimit))
    if (limited.isEmpty) return Map.empty
    val expires = math.min(deadline, System.nanoTime() + config.deadlines.evidenceMs * 1000000L)
    val tasks = limited.map { id =>
      id -> pool.submit(new Callable[Completed[Option[String]]] {
        def call(): Completed[Option[String]] = completed(RuntimeNames.read(path.graph, id))
      })
    }
    tasks.flatMap { (id, task) =>
      await(task, expires, "names").toOption.flatten.map(id -> _)
    }.toMap
  }
  private def timed[A](pool: ExecutorService, overall: Long, stage: String, millis: Long)(
      body: => A
  ): Either[StageFailure, A] = {
    val expires = math.min(overall, System.nanoTime() + millis * 1000000L)
    val task = pool.submit(new Callable[Completed[A]] {
      def call(): Completed[A] = completed(body)
    })
    await(task, expires, stage)
  }
  private def await[A](
      task: Future[Completed[A]],
      expires: Long,
      stage: String
  ): Either[StageFailure, A] = {
    val remaining = expires - System.nanoTime()
    if (remaining <= 0 && !task.isDone) {
      task.cancel(true); Left(StageFailure(stage, "stage-deadline"))
    } else
      try {
        val result = task.get(math.max(0L, remaining), TimeUnit.NANOSECONDS)
        if (result.finishedNanos <= expires) Right(result.value)
        else Left(StageFailure(stage, "stage-deadline"))
      } catch {
        case _: TimeoutException => task.cancel(true); Left(StageFailure(stage, "stage-deadline"))
        case _: InterruptedException =>
          task.cancel(true); Thread.currentThread().interrupt();
          Left(StageFailure(stage, "stage-interrupted"))
        case NonFatal(_) => task.cancel(true); Left(StageFailure(stage, "stage-execution-failed"))
      }
  }
  private def close(pool: ExecutorService, deadline: Long): Unit = {
    pool.shutdownNow()
    val remaining = math.max(0L, deadline - System.nanoTime())
    try
      pool.awaitTermination(
        math.min(config.deadlines.all.min * 1000000L, remaining),
        TimeUnit.NANOSECONDS
      )
    catch { case _: InterruptedException => Thread.currentThread().interrupt() }
  }
}
