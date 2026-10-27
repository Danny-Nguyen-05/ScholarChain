package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.services.*
import java.util.concurrent.{Callable, CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong}
import org.scalatest.funsuite.AnyFunSuite

class IndependentServices10AResilienceSpec extends AnyFunSuite {
  private val config = ServiceConfig(
    Auth.sha256("synthetic-external-resilience-key"),
    Auth.sha256("synthetic-internal-resilience-key"),
    downstreamTimeoutMs = 500,
    downstreamMaxAttempts = 3
  )
  private val context =
    RequestContext("independent-request", "independent-trace", "synthetic-query")

  test("GET retries transient reads to configured bound and propagates both request identifiers") {
    val attempts = new AtomicInteger()
    val metrics = new ServiceMetrics
    val client = new DownstreamClient(config, new CircuitBreaker(10, 100), metrics)
    try {
      val result = client.call[String]("GET", context) { headers =>
        assert(headers("X-Request-Id") == "independent-request")
        assert(headers("X-Trace-Id") == "independent-trace")
        attempts.incrementAndGet()
        Left(ApiError(502, "INJECTED_FAILURE", "Synthetic dependency failed", retryable = true))
      }
      assert(result.left.toOption.exists(_.status == 502))
      assert(attempts.get() == 3)
      assert(metrics.render.contains("api_downstream_errors_total 3"))
      assert(metrics.render.contains("api_requests_total 0"))
    } finally client.close()
  }

  test("non-read methods attempt transient failures once and nonretryable GET fails once") {
    for (method <- Vector("POST", "PUT", "PATCH", "DELETE")) {
      val attempts = new AtomicInteger()
      val client = new DownstreamClient(config, new CircuitBreaker(10, 100))
      try {
        assert(
          client
            .call[String](method, context) { _ =>
              attempts.incrementAndGet()
              Left(
                ApiError(502, "INJECTED_FAILURE", "Synthetic dependency failed", retryable = true)
              )
            }
            .isLeft
        )
        assert(attempts.get() == 1, method)
      } finally client.close()
    }
    val attempts = new AtomicInteger()
    val client = new DownstreamClient(config, new CircuitBreaker(10, 100))
    try {
      assert(
        client
          .call[String]("GET", context) { _ =>
            attempts.incrementAndGet()
            Left(ApiError(404, "MISSING", "Synthetic missing object"))
          }
          .left
          .toOption
          .exists(_.status == 404)
      )
      assert(attempts.get() == 1)
    } finally client.close()
  }

  test("actual blocked dependency is bounded by timeout and its task is interrupted") {
    val entered = new CountDownLatch(1)
    val interrupted = new CountDownLatch(1)
    val neverRelease = new CountDownLatch(1)
    val client = new DownstreamClient(
      config.copy(downstreamTimeoutMs = 100, downstreamMaxAttempts = 1),
      new CircuitBreaker(1, 100)
    )
    try {
      val started = System.nanoTime()
      val result = client.call[String]("GET", context) { _ =>
        entered.countDown()
        try {
          neverRelease.await(5, TimeUnit.SECONDS)
          Right("late")
        } catch {
          case _: InterruptedException =>
            interrupted.countDown()
            throw new InterruptedException("Synthetic interrupted dependency")
        }
      }
      assert(entered.getCount == 0)
      assert(result.left.toOption.exists(_.status == 504))
      assert(System.nanoTime() - started < TimeUnit.SECONDS.toNanos(3))
      assert(interrupted.await(2, TimeUnit.SECONDS))
    } finally {
      neverRelease.countDown()
      client.close()
    }
  }

  test("open circuit rejects calls, permits one half-open probe, and closes on success") {
    val now = new AtomicLong(0)
    val breaker = new CircuitBreaker(1, 10, () => now.get())
    val client = new DownstreamClient(config.copy(downstreamMaxAttempts = 1), breaker)
    val caller = Executors.newSingleThreadExecutor()
    val entered = new CountDownLatch(1)
    val finish = new CountDownLatch(1)
    val attempts = new AtomicInteger()
    try {
      assert(breaker.state == "CLOSED")
      assert(
        client
          .call[String]("GET", context) { _ =>
            attempts.incrementAndGet()
            Left(ApiError(502, "INJECTED_FAILURE", "Synthetic failure", retryable = true))
          }
          .isLeft
      )
      assert(breaker.state == "OPEN")
      assert(
        client
          .call[String]("GET", context) { _ =>
            attempts.incrementAndGet(); Right("should-not-run")
          }
          .left
          .toOption
          .exists(_.code == "CIRCUIT_OPEN")
      )
      assert(attempts.get() == 1)
      now.set(TimeUnit.MILLISECONDS.toNanos(10))
      val probe = caller.submit(new Callable[Either[ApiError, String]] {
        def call() = client.call[String]("GET", context) { _ =>
          attempts.incrementAndGet()
          entered.countDown()
          assert(finish.await(2, TimeUnit.SECONDS))
          Right("recovered")
        }
      })
      assert(entered.await(2, TimeUnit.SECONDS))
      assert(breaker.state == "HALF_OPEN")
      assert(
        client
          .call[String]("GET", context) { _ =>
            attempts.incrementAndGet(); Right("should-not-run")
          }
          .left
          .toOption
          .exists(_.code == "CIRCUIT_OPEN")
      )
      assert(attempts.get() == 2)
      finish.countDown()
      assert(probe.get(2, TimeUnit.SECONDS) == Right("recovered"))
      assert(breaker.state == "CLOSED")
    } finally {
      finish.countDown()
      caller.shutdownNow()
      client.close()
    }
  }
}
