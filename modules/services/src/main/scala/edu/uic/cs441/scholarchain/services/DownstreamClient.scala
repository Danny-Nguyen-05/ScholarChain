package edu.uic.cs441.scholarchain.services

import java.util.concurrent.{
  ArrayBlockingQueue,
  Callable,
  ThreadPoolExecutor,
  TimeUnit,
  TimeoutException,
  RejectedExecutionException
}
import scala.util.control.NonFatal

/** One breaker instance per dependency. Exactly one half-open probe may execute. */
final class CircuitBreaker(
    failureThreshold: Int,
    resetMs: Long,
    nowNanos: () => Long = () => System.nanoTime()
) {
  require(failureThreshold > 0 && resetMs > 0)
  private var failures = 0
  private var openedAt = 0L
  private var current = "CLOSED"
  def state: String = synchronized {
    if (current == "OPEN" && nowNanos() - openedAt >= resetMs * 1000000L) "HALF_OPEN" else current
  }
  private[services] def acquire(): Boolean = synchronized {
    if (current == "CLOSED") true
    else if (current == "OPEN" && nowNanos() - openedAt >= resetMs * 1000000L) {
      current = "HALF_OPEN"; true
    } else false
  }
  private[services] def success(): Unit = synchronized { failures = 0; current = "CLOSED" }
  private[services] def failure(): Unit = synchronized {
    failures += 1
    if (current == "HALF_OPEN" || failures >= failureThreshold) {
      current = "OPEN"; openedAt = nowNanos()
    }
  }
}

/** Only idempotent reads retry transient typed failures; writes are attempted once. A timeout
  * cancels its task. The bounded executor prevents adapters ignoring interruption from creating an
  * unbounded population of blocked calls. Such adapters can still occupy their bounded slot.
  */
final class DownstreamClient(
    config: ServiceConfig,
    breaker: CircuitBreaker,
    metrics: ServiceMetrics = new ServiceMetrics,
    dependencyName: String = "dependency"
) extends AutoCloseable {
  metrics.registerBreaker(dependencyName, () => breaker.state)
  private val pool = new ThreadPoolExecutor(
    config.workerThreads,
    config.workerThreads,
    0L,
    TimeUnit.MILLISECONDS,
    new ArrayBlockingQueue[Runnable](config.queueCapacity),
    ServiceThreads.daemon("downstream-call")
  )
  def call[A](method: String, context: RequestContext)(
      operation: Map[String, String] => Either[ApiError, A]
  ): Either[ApiError, A] = {
    callWithin(method, context, config.downstreamTimeoutMs)(operation)
  }
  def callWithin[A](method: String, context: RequestContext, timeoutMs: Long)(
      operation: Map[String, String] => Either[ApiError, A]
  ): Either[ApiError, A] = {
    require(timeoutMs > 0 && timeoutMs <= config.downstreamTimeoutMs)
    val attempts =
      if (Set("GET", "HEAD")(method.toUpperCase(java.util.Locale.ROOT)))
        config.downstreamMaxAttempts
      else 1
    var count = 0
    var result: Either[ApiError, A] = Left(ApiError.unavailable)
    while (count < attempts) {
      if (!breaker.acquire())
        return Left(ApiError(503, "CIRCUIT_OPEN", "The downstream circuit is open.", true))
      count += 1
      result =
        try {
          val task = pool.submit(new Callable[Either[ApiError, A]] {
            def call(): Either[ApiError, A] = operation(context.downstreamHeaders)
          })
          try task.get(timeoutMs, TimeUnit.MILLISECONDS)
          catch {
            case _: TimeoutException => task.cancel(true); Left(ApiError.timeout)
            case _: InterruptedException =>
              task.cancel(true); Thread.currentThread().interrupt(); Left(ApiError.unavailable)
            case NonFatal(_) => Left(ApiError.downstream)
          }
        } catch { case _: RejectedExecutionException => Left(ApiError.unavailable) }
      result.left.foreach { error =>
        if (ApiError.isGraphDeadline(error)) metrics.graphRequestDeadline()
        else metrics.downstream(error.status)
      }
      result match {
        case Right(_)                                => breaker.success(); return result
        case Left(e) if ApiError.isGraphDeadline(e)  => breaker.success(); return result
        case Left(e) if Set(502, 503, 504)(e.status) => breaker.failure()
        case Left(_)                                 => breaker.success(); return result
      }
      if (!result.left.exists(_.retryable) || Thread.currentThread().isInterrupted) return result
    }
    result
  }
  def close(): Unit = {
    pool.shutdownNow(); pool.awaitTermination(config.downstreamTimeoutMs, TimeUnit.MILLISECONDS); ()
  }
}
