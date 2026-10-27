package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

class RetriedSessionCreationSpec extends AnyFunSuite {
  private val config = ServiceConfig(
    Auth.sha256("synthetic-retry-external"),
    Auth.sha256("synthetic-retry-internal"),
    synchronousDeadlineMs = 100,
    workflowTimeoutMs = 500,
    maxWorkflowRetries = 0,
    downstreamTimeoutMs = 50,
    sessionPollMs = 1
  )
  private val request =
    QueryRequest.parse("{\"question\":\"Synthetic retry question\"}", config).toOption.get
  private val changed =
    QueryRequest.parse("{\"question\":\"Different synthetic question\"}", config).toOption.get
  private val context = RequestContext("synthetic-request", "synthetic-trace")
  private val answer = WorkflowOutput(
    ujson.Obj("summary" -> "Synthetic retry fixture", "researchers" -> ujson.Arr())
  )

  private def workflow(calls: AtomicInteger): QueryWorkflow = new QueryWorkflow {
    def run(
        r: QueryRequest,
        c: RequestContext,
        stage: String => Unit
    ): Either[ApiError, WorkflowOutput] = {
      calls.incrementAndGet()
      Right(answer)
    }
  }
  private class RetriedStore(
      delegate: QuerySessionStore,
      wrap: StorageResult[QuerySession] => StorageResult[QuerySession]
  ) extends QuerySessionStore {
    def createIfAbsent(id: String, key: String): StorageResult[QuerySession] = wrap(
      delegate.createIfAbsent(id, key)
    )
    def get(id: String): StorageResult[QuerySession] = delegate.get(id)
    def lookupByIdempotencyKey(key: String): StorageResult[QuerySession] =
      delegate.lookupByIdempotencyKey(key)
    def update(session: QuerySession, expectedRevision: Long): StorageResult[QuerySession] =
      delegate.update(session, expectedRevision)
  }
  private def completed(service: QueryService, first: ApiReply): ApiReply = {
    assert(Set(200, 202)(first.status))
    if (first.status == 200) first
    else {
      val id = first.body("jobId").str
      assert(id.matches("job-[0-9a-f]{64}"))
      assert(service.job(id).isRight)
      val until = System.nanoTime() + 2000000000L
      var result = service.result(id)
      while (result.exists(_.status == 202) && System.nanoTime() < until) {
        Thread.sleep(1)
        result = service.result(id)
      }
      val terminal = result.toOption.get
      assert(terminal.status == 200)
      terminal
    }
  }

  test("Retried Written owns creation, binds the body and executes exactly once across replay") {
    val backing = new InMemoryQuerySessionStore
    val store = new RetriedStore(backing, r => StorageResult.Retried(1, r))
    val calls = new AtomicInteger
    val service = new QueryService(store, workflow(calls), config)
    try {
      val first = service.submit(request, "retried-written", context)
      assert(first.isRight, s"retried creator must receive an answer or valid job: $first")
      val terminal = completed(service, first.toOption.get)
      assert(terminal.body("answer") == answer.answer)
      val replay = service.submit(request, "retried-written", context).toOption.get
      assert(replay.status == 200 && replay.body == terminal.body)
      assert(calls.get() == 1)
      assert(
        service.submit(changed, "retried-written", context).left.toOption.exists(_.status == 409)
      )
      assert(calls.get() == 1)
      val persisted = StorageResult.value(backing.get(terminal.body("queryId").str)).get
      assert(persisted.state == "SUCCEEDED")
      assert(ujson.read(persisted.payload)("result") == terminal.body)
    } finally service.close()
  }

  for (outcome <- Vector("Unchanged", "Rejected")) {
    test(s"Retried $outcome reconciles the existing outcome without executing workflow") {
      val backing = new InMemoryQuerySessionStore
      val originalCalls = new AtomicInteger
      val seed = new QueryService(backing, workflow(originalCalls), config)
      val key = "retried-" + outcome
      val stored =
        try completed(seed, seed.submit(request, key, context).toOption.get)
        finally seed.close()
      assert(originalCalls.get() == 1)
      val store = new RetriedStore(
        backing,
        {
          case StorageResult.Unchanged(s) if outcome == "Unchanged" =>
            StorageResult.Retried(1, StorageResult.Unchanged(s))
          case _ if outcome == "Rejected" =>
            StorageResult.Retried(1, StorageResult.Rejected("synthetic-ambiguous-reply"))
          case other => fail(s"expected an existing session, received $other")
        }
      )
      val newCalls = new AtomicInteger
      val replayService = new QueryService(store, workflow(newCalls), config)
      try {
        val replay = replayService.submit(request, key, context).toOption.get
        assert(replay.status == 200 && replay.body == stored.body)
        assert(replayService.submit(changed, key, context).left.toOption.exists(_.status == 409))
        assert(newCalls.get() == 0)
        assert(originalCalls.get() == 1)
      } finally replayService.close()
    }
  }
}
