package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.*
import java.time.Instant
import java.util.UUID
import java.util.concurrent.{
  ArrayBlockingQueue,
  Callable,
  Executors,
  ExecutorService,
  ThreadPoolExecutor,
  ThreadFactory,
  TimeUnit,
  TimeoutException,
  RejectedExecutionException
}
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

object ServiceThreads {
  def daemon(name: String): ThreadFactory = (r: Runnable) => {
    val t = new Thread(r, name); t.setDaemon(true); t
  }
}
final case class ApiReply(status: Int, body: ujson.Value)

/** Application jobs are namespaced separately from RuntimeAuditStore sessions. The deterministic ID
  * makes the store's conditional reservation authoritative even if its GSI is lagging. Only the
  * caller that conditionally binds the body may start work; state/result changes use CAS revisions.
  */
final class QueryService(
    val store: QuerySessionStore,
    workflow: QueryWorkflow,
    config: ServiceConfig,
    val metrics: ServiceMetrics = new ServiceMetrics
) extends AutoCloseable {
  private val workers = new ThreadPoolExecutor(
    config.workerThreads,
    config.workerThreads,
    0L,
    TimeUnit.MILLISECONDS,
    new ArrayBlockingQueue[Runnable](config.queueCapacity),
    ServiceThreads.daemon("query-job")
  )
  private val calls = new ThreadPoolExecutor(
    config.workerThreads,
    config.workerThreads,
    0L,
    TimeUnit.MILLISECONDS,
    new ArrayBlockingQueue[Runnable](config.queueCapacity),
    ServiceThreads.daemon("query-workflow")
  )
  private def instant = Instant.now().toString
  private def queryId(key: String) = "qry-" + Auth.sha256("api-query:" + key)
  private def jobId(id: String) = "job-" + id.stripPrefix("qry-")
  private def fromJob(id: String): Option[String] =
    Option.when(id.matches("job-[0-9a-f]{64}"))("qry-" + id.stripPrefix("job-"))
  private def session(id: String): Either[ApiError, QuerySession] = store.get(id) match {
    case StorageResult.Missing =>
      Left(ApiError(404, "NOT_FOUND", "The requested job was not found."))
    case value => StorageResult.value(value).toRight(ApiError.unavailable)
  }
  private def read(s: QuerySession): ujson.Value = ujson.read(s.payload)
  private def mutate(id: String)(change: ujson.Value => Unit): Boolean = {
    var count = 0
    while (count < config.sessionCasAttempts) {
      count += 1
      session(id) match {
        case Right(s) if s.payload != "{}" =>
          val p = read(s)
          if (Set("SUCCEEDED", "FAILED")(p("state").str)) return false
          change(p); p("updatedAt") = instant
          val history = p.obj.get("observedStages").map(_.arr.toVector).getOrElse(Vector.empty)
          if (history.lastOption.forall(_ != p("stage")))
            p("observedStages") = ujson.Arr.from(history :+ p("stage"))
          if (
            StorageResult.successful(
              store.update(
                s.copy(state = p("state").str, revision = s.revision + 1, payload = p.render()),
                s.revision
              )
            )
          ) return true
        case _ => return false
      }
    }
    false
  }
  private def awaitBinding(id: String): Either[ApiError, QuerySession] = {
    val until = System.nanoTime() + config.downstreamTimeoutMs * 1000000L
    var current = session(id)
    while (current.exists(_.payload == "{}") && System.nanoTime() < until) {
      try
        Thread.sleep(
          math.min(config.sessionPollMs, math.max(1L, (until - System.nanoTime()) / 1000000L))
        )
      catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt(); return Left(ApiError.unavailable)
      }
      current = session(id)
    }
    // A failed binder may have left revision zero unbound. The caller may now compete for its CAS.
    current
  }
  private def errorFrom(p: ujson.Value): ApiError = {
    val e = p("failure")
    ApiError(e("status").num.toInt, e("code").str, e("message").str, e("retryable").bool)
  }
  private def reply(s: QuerySession): Either[ApiError, ApiReply] = {
    if (s.payload == "{}") return Left(ApiError.unavailable)
    val p = read(s)
    p("state").str match {
      case "SUCCEEDED" => Right(ApiReply(200, p("result")))
      case "FAILED"    => Left(errorFrom(p))
      case _           => Right(ApiReply(202, reference(s.queryId, s.state)))
    }
  }
  private def reference(id: String, state: String): ujson.Value = ujson.Obj(
    "queryId" -> id,
    "mode" -> "asynchronous",
    "jobId" -> jobId(id),
    "status" -> state,
    "statusUrl" -> s"/v1/jobs/${jobId(id)}"
  )
  private def replay(s: QuerySession, fingerprint: String): Either[ApiError, ApiReply] = {
    if (s.payload == "{}") Left(ApiError.unavailable)
    else if (read(s)("fingerprint").str != fingerprint)
      Left(
        ApiError(
          409,
          "IDEMPOTENCY_CONFLICT",
          "The idempotency key was already used with a different body."
        )
      )
    else reply(s)
  }
  private def dispatch(
      id: String,
      request: QueryRequest,
      context: RequestContext
  ): Either[ApiError, ApiReply] = {
    try workers.execute(() => execute(id, request, context.copy(queryId = id)))
    catch {
      case _: RejectedExecutionException =>
        fail(id, ApiError(429, "THROTTLED", "The local workflow queue is full.", true))
    }
    val until = System.nanoTime() + config.synchronousDeadlineMs * 1000000L
    var current = session(id)
    while (current.exists(s => !Set("SUCCEEDED", "FAILED")(s.state)) && System.nanoTime() < until) {
      try
        Thread.sleep(
          math.min(config.sessionPollMs, math.max(1L, (until - System.nanoTime()) / 1000000L))
        )
      catch {
        case _: InterruptedException =>
          Thread.currentThread().interrupt(); return Left(ApiError.unavailable)
      }
      current = session(id)
    }
    current.flatMap(reply)
  }
  private def bind(
      reservation: QuerySession,
      request: QueryRequest,
      fingerprint: String,
      context: RequestContext
  ): Either[ApiError, ApiReply] = {
    if (reservation.revision != 0 || reservation.payload != "{}")
      return replay(reservation, fingerprint)
    val now = instant
    val payload = ujson.Obj(
      "fingerprint" -> fingerprint,
      "observedStages" -> ujson.Arr("QUEUED"),
      "state" -> "QUEUED",
      "stage" -> "QUEUED",
      "createdAt" -> now,
      "updatedAt" -> now,
      "result" -> ujson.Null,
      "failure" -> ujson.Null,
      "attempts" -> 0,
      "requestId" -> context.requestId,
      "traceId" -> context.traceId,
      // Request/trace IDs are client-controlled and may be identical across concurrent binders.
      "bindingToken" -> UUID.randomUUID().toString
    )
    val intended = reservation.copy(
      state = "QUEUED",
      revision = reservation.revision + 1,
      payload = payload.render()
    )
    def written(result: StorageResult[QuerySession]): Boolean = result match {
      case StorageResult.Written(s)         => s == intended
      case StorageResult.Retried(_, nested) => written(nested)
      case _                                => false
    }
    val result = store.update(intended, reservation.revision)
    if (written(result)) dispatch(reservation.queryId, request, context)
    else {
      // The CAS may have applied before its reply was lost. Exact revision/payload equality also
      // checks fingerprint, request/trace IDs and this attempt's token; another binder cannot claim it.
      session(reservation.queryId).flatMap { current =>
        if (current == intended) dispatch(reservation.queryId, request, context)
        else replay(current, fingerprint)
      }
    }
  }
  def submit(
      request: QueryRequest,
      key: String,
      context: RequestContext
  ): Either[ApiError, ApiReply] = {
    val id = queryId(key); val fingerprint = QueryRequest.fingerprint(request)
    def reconcile(id: String): Either[ApiError, ApiReply] = awaitBinding(id).flatMap { current =>
      if (current.payload == "{}") bind(current, request, fingerprint, context)
      else replay(current, fingerprint)
    }
    // Creation owns only the reservation. The revision-zero body CAS chooses the one dispatcher,
    // including when a later request recovers a reservation left unbound by an earlier store failure.
    val creation = store.createIfAbsent(id, "api:" + Auth.sha256(key)) match {
      case StorageResult.Retried(_, StorageResult.Written(s)) => StorageResult.Written(s)
      case other                                              => other
    }
    creation match {
      case StorageResult.Written(s)    => bind(s, request, fingerprint, context)
      case StorageResult.Unchanged(s)  => reconcile(s.queryId)
      case StorageResult.Retried(_, _) => reconcile(id)
      case _                           => Left(ApiError.unavailable)
    }
  }
  private def fail(id: String, error: ApiError): Unit = {
    mutate(id) { p =>
      p("state") = "FAILED"; p("stage") = "FAILED"
      p("failure") = ujson.Obj(
        "status" -> error.status,
        "code" -> error.code,
        "message" -> error.message,
        "retryable" -> false
      )
    }
    ()
  }
  private def execute(id: String, request: QueryRequest, context: RequestContext): Unit = try {
    if (!mutate(id)(p => { p("state") = "RUNNING"; p("stage") = "WORKFLOW" })) return
    var attempt = 0
    var result: Either[ApiError, WorkflowOutput] = Left(ApiError.internal)
    val deadline = System.nanoTime() + config.workflowTimeoutMs * 1000000L
    var retry = true
    while (retry && attempt <= config.maxWorkflowRetries && System.nanoTime() < deadline) {
      attempt += 1
      mutate(id)(p => p("attempts") = attempt)
      val task = calls.submit(new Callable[Either[ApiError, WorkflowOutput]] {
        def call(): Either[ApiError, WorkflowOutput] = workflow.run(
          request,
          context,
          stage => {
            // Only bounded public stage labels are persisted, never arbitrary provider strings.
            if (Set("PLANNING", "RETRIEVAL", "SYNTHESIS", "CLAIM_VERIFICATION", "AUDIT")(stage))
              mutate(id)(p => p("stage") = stage)
            ()
          }
        )
      })
      result =
        try task.get(math.max(1L, deadline - System.nanoTime()), TimeUnit.NANOSECONDS)
        catch {
          case _: TimeoutException => task.cancel(true); Left(ApiError.timeout)
          case _: InterruptedException =>
            task.cancel(true); Thread.currentThread().interrupt(); Left(ApiError.unavailable)
          case NonFatal(_) => Left(ApiError.downstream)
        }
      retry = result.left.exists(e => e.retryable && Set(502, 503, 504)(e.status)) && !Thread
        .currentThread()
        .isInterrupted
    }
    result match {
      case Left(e) => fail(id, e)
      case Right(output) =>
        val response = ujson.Obj(
          "queryId" -> id,
          "mode" -> "synchronous",
          "answer" -> output.answer,
          "claims" -> ujson.Arr.from(output.claims),
          "links" -> ujson.Obj(
            "explain" -> s"/v1/explain/$id",
            "evidence" -> s"/v1/queries/$id/evidence",
            "result" -> s"/v1/jobs/${jobId(id)}/result"
          )
        )
        if (response.render().getBytes(UTF_8).length > config.maxResultBytes)
          fail(
            id,
            ApiError(502, "RESULT_TOO_LARGE", "The workflow result exceeds the configured bound.")
          )
        else if (
          mutate(id) { p =>
            p("state") = "SUCCEEDED"; p("stage") = "COMPLETE"; p("result") = response
          }
        )
          metrics.workflow(output.verificationStatus, output.abstained)
        else fail(id, ApiError.unavailable)
    }
  } catch { case NonFatal(_) => fail(id, ApiError.internal) }

  def job(id: String): Either[ApiError, ApiReply] = fromJob(id)
    .toRight(ApiError(404, "NOT_FOUND", "The requested job was not found."))
    .flatMap(session)
    .flatMap { s =>
      if (s.payload == "{}") Left(ApiError.unavailable)
      else {
        val p = read(s)
        Right(
          ApiReply(
            200,
            ujson.Obj(
              "jobId" -> id,
              "queryId" -> s.queryId,
              "state" -> p("state"),
              "stage" -> p("stage"),
              "createdAt" -> p("createdAt"),
              "updatedAt" -> p("updatedAt"),
              "resultUrl" -> (if (s.state == "SUCCEEDED") ujson.Str(s"/v1/jobs/$id/result")
                              else ujson.Null),
              "error" -> (if (s.state == "FAILED") errorFrom(p).json(p("traceId").str)
                          else ujson.Null)
            )
          )
        )
      }
    }
  def result(id: String): Either[ApiError, ApiReply] = fromJob(id)
    .toRight(ApiError(404, "NOT_FOUND", "The requested job was not found."))
    .flatMap(session)
    .flatMap(reply)
  def close(): Unit = {
    workers.shutdownNow(); calls.shutdownNow()
    workers.awaitTermination(config.workflowTimeoutMs, TimeUnit.MILLISECONDS)
    calls.awaitTermination(config.workflowTimeoutMs, TimeUnit.MILLISECONDS)
    ()
  }
}
