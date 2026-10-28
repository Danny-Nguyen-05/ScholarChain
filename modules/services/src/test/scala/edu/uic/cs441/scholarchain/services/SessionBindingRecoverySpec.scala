package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.{Callable, CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.{AtomicBoolean, AtomicInteger}
import org.scalatest.funsuite.AnyFunSuite

class SessionBindingRecoverySpec extends AnyFunSuite {
  private val config = ServiceConfig(
    Auth.sha256("synthetic-binding-external"),
    Auth.sha256("synthetic-binding-internal"),
    synchronousDeadlineMs = 40,
    workflowTimeoutMs = 3000,
    maxWorkflowRetries = 0,
    downstreamTimeoutMs = 25,
    sessionPollMs = 1
  )
  private val request =
    QueryRequest.parse("{\"question\":\"Synthetic binding question\"}", config).toOption.get
  private val changed =
    QueryRequest.parse("{\"question\":\"Changed binding question\"}", config).toOption.get
  // These are client-supplied identifiers, so every contender intentionally reuses them.
  private val context = RequestContext("synthetic-reused-request", "synthetic-reused-trace")
  private val output = WorkflowOutput(
    ujson.Obj("summary" -> "Synthetic recovered answer", "researchers" -> ujson.Arr())
  )

  private def workflow(
      calls: AtomicInteger,
      release: Option[CountDownLatch] = None
  ): QueryWorkflow =
    new QueryWorkflow {
      def run(
          r: QueryRequest,
          c: RequestContext,
          stage: String => Unit
      ): Either[ApiError, WorkflowOutput] = {
        calls.incrementAndGet()
        release.foreach(latch =>
          assert(latch.await(2, TimeUnit.SECONDS), "workflow release timed out")
        )
        Right(output)
      }
    }

  private abstract class DelegatingStore(val delegate: QuerySessionStore)
      extends QuerySessionStore {
    def createIfAbsent(id: String, key: String): StorageResult[QuerySession] =
      delegate.createIfAbsent(id, key)
    def get(id: String): StorageResult[QuerySession] = delegate.get(id)
    def lookupByIdempotencyKey(key: String): StorageResult[QuerySession] =
      delegate.lookupByIdempotencyKey(key)
  }

  private def completed(service: QueryService, initial: Either[ApiError, ApiReply]): ApiReply = {
    assert(initial.isRight, s"must return an answer or a job that completes: $initial")
    val first = initial.toOption.get
    assert(Set(200, 202)(first.status))
    if (first.status == 200) first
    else {
      val job = first.body("jobId").str
      val until = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
      var current = service.result(job)
      while (current.exists(_.status == 202) && System.nanoTime() < until) {
        Thread.sleep(1)
        current = service.result(job)
      }
      assert(current.exists(_.status == 200), s"job must complete, not stay QUEUED: $current")
      current.toOption.get
    }
  }

  private def assertReplay(
      service: QueryService,
      key: String,
      terminal: ApiReply,
      calls: AtomicInteger
  ): Unit = {
    val replay = service.submit(request, key, context).toOption.get
    assert(replay.status == 200 && replay.body == terminal.body)
    assert(service.submit(changed, key, context).left.toOption.exists(_.status == 409))
    assert(calls.get() == 1)
  }

  test(
    "an applied body-binding write with a lost reply completes exactly once and replays its stored result"
  ) {
    val calls = new AtomicInteger
    val appliedBindings = new AtomicInteger
    val backing = new InMemoryQuerySessionStore
    val store = new DelegatingStore(backing) {
      def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        val result = backing.update(s, expected)
        if (expected == 0) {
          assert(
            StorageResult.successful(result),
            "the fault must occur after the bind was applied"
          )
          appliedBindings.incrementAndGet()
          StorageResult.Retried(1, StorageResult.Rejected("conditional-conflict"))
        } else result
      }
    }
    val service = new QueryService(store, workflow(calls), config)
    val replayService = new QueryService(store, workflow(calls), config)
    try {
      val terminal = completed(service, service.submit(request, "binding-lost-reply", context))
      assert(terminal.body("answer") == output.answer)
      assert(appliedBindings.get() == 1 && calls.get() == 1)
      val persisted = StorageResult.value(backing.get(terminal.body("queryId").str)).get
      assert(persisted.state == "SUCCEEDED")
      assert(ujson.read(persisted.payload)("result") == terminal.body)
      assertReplay(replayService, "binding-lost-reply", terminal, calls)
      assert(appliedBindings.get() == 1)
    } finally { replayService.close(); service.close() }
  }

  test(
    "one clean binding rejection leaves the same key recoverable by a replay rather than permanently retryable"
  ) {
    val calls = new AtomicInteger
    val rejectFirst = new AtomicBoolean(true)
    val bindingAttempts = new AtomicInteger
    val backing = new InMemoryQuerySessionStore
    val store = new DelegatingStore(backing) {
      def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        if (expected == 0) {
          bindingAttempts.incrementAndGet()
          if (rejectFirst.compareAndSet(true, false))
            return StorageResult.Rejected("conditional-conflict")
        }
        backing.update(s, expected)
      }
    }
    val service = new QueryService(store, workflow(calls), config)
    try {
      val first = service.submit(request, "binding-clean-rejection", context)
      assert(first.left.toOption.exists(_.status == 503))
      assert(calls.get() == 0 && bindingAttempts.get() == 1)
      val terminal = completed(service, service.submit(request, "binding-clean-rejection", context))
      assert(terminal.body("answer") == output.answer)
      assertReplay(service, "binding-clean-rejection", terminal, calls)
      assert(bindingAttempts.get() == 2)
    } finally service.close()
  }

  for (lostWinnerReply <- Vector(false, true)) {
    test(
      s"concurrent cross-instance replays with reused client IDs bind and execute once when winner reply is lost=$lostWinnerReply"
    ) {
      val calls = new AtomicInteger
      val releaseWorkflow = new CountDownLatch(1)
      val rejectFirst = new AtomicBoolean(true)
      val bothBinders = new CountDownLatch(2)
      val loserRead = new CountDownLatch(1)
      val loser = new ThreadLocal[Boolean] { override def initialValue(): Boolean = false }
      val bindingAttempts = new AtomicInteger
      val appliedBindings = new AtomicInteger
      val backing = new InMemoryQuerySessionStore
      val store = new DelegatingStore(backing) {
        override def get(id: String): StorageResult[QuerySession] = {
          val snapshot = backing.get(id)
          if (loser.get()) { loserRead.countDown(); loser.remove() }
          snapshot
        }
        def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
          if (expected != 0) backing.update(s, expected)
          else {
            bindingAttempts.incrementAndGet()
            if (rejectFirst.compareAndSet(true, false))
              StorageResult.Rejected("conditional-conflict")
            else {
              bothBinders.countDown()
              assert(
                bothBinders.await(2, TimeUnit.SECONDS),
                "both replays must reach revision-zero CAS"
              )
              val result = backing.update(s, expected)
              if (StorageResult.successful(result)) {
                appliedBindings.incrementAndGet()
                // Keep QUEUED until the loser has read the exact winning snapshot.
                assert(
                  loserRead.await(2, TimeUnit.SECONDS),
                  "losing binder must reconcile the primary row"
                )
                if (lostWinnerReply)
                  StorageResult.Retried(1, StorageResult.Rejected("conditional-conflict"))
                else result
              } else {
                loser.set(true)
                StorageResult.Retried(1, StorageResult.Rejected("conditional-conflict"))
              }
            }
          }
        }
      }
      val firstService = new QueryService(store, workflow(calls, Some(releaseWorkflow)), config)
      val secondService = new QueryService(store, workflow(calls, Some(releaseWorkflow)), config)
      val callers = Executors.newFixedThreadPool(2)
      val key = "binding-concurrent-" + lostWinnerReply
      try {
        assert(firstService.submit(request, key, context).left.toOption.exists(_.status == 503))
        assert(calls.get() == 0)
        val first = callers.submit(new Callable[Either[ApiError, ApiReply]] {
          def call() = firstService.submit(request, key, context)
        })
        val second = callers.submit(new Callable[Either[ApiError, ApiReply]] {
          def call() = secondService.submit(request, key, context)
        })
        val responses = Vector(first.get(3, TimeUnit.SECONDS), second.get(3, TimeUnit.SECONDS))
        assert(responses.forall(_.exists(r => Set(200, 202)(r.status))), s"$responses")
        assert(bindingAttempts.get() == 3 && appliedBindings.get() == 1)
        releaseWorkflow.countDown()
        val terminal = completed(firstService, responses.head)
        assert(terminal.body("answer") == output.answer)
        assertReplay(secondService, key, terminal, calls)
        assert(calls.get() == 1 && appliedBindings.get() == 1)
      } finally {
        releaseWorkflow.countDown()
        callers.shutdownNow()
        callers.awaitTermination(2, TimeUnit.SECONDS)
        secondService.close(); firstService.close()
      }
    }
  }
}
