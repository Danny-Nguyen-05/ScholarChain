package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.StorageResult
import java.util.concurrent.{
  ExecutionException,
  Future,
  RejectedExecutionException,
  SynchronousQueue,
  ThreadPoolExecutor,
  TimeUnit,
  TimeoutException
}
import scala.util.control.NonFatal

/** One named dependency check. The probe must go through an adapter port and must report only
  * "reachable and authorized"; it must not require loaded data.
  */
final case class ReadinessCheck(name: String, probe: () => Boolean)

object ReadinessProbes {

  /** An identifier that no loader ever writes; a lookup for it must be a clean miss. */
  val probeKey = "readiness-probe"

  /** A found or cleanly missing record both prove the dependency answered and authorized the read.
    * Any rejection (denied, throttled, malformed, unreachable) is not ready.
    */
  def answered(result: StorageResult[?]): Boolean = result match {
    case StorageResult.Found(_) | StorageResult.Written(_) | StorageResult.Unchanged(_) => true
    case StorageResult.Missing                                                          => true
    case StorageResult.Retried(_, inner) => answered(inner)
    case StorageResult.Rejected(_)       => false
  }
  def check(name: String)(read: => StorageResult[?]): ReadinessCheck =
    ReadinessCheck(name, () => answered(read))
}

/** Readiness for aws mode. All checks run concurrently, the whole evaluation is bounded by
  * timeoutMs, and the verdict (pass or fail) is cached for cacheMs so repeated load-balancer or
  * peer probes do not reach the dependencies each time. Concurrent callers share one evaluation.
  * Only check names are logged, never provider messages, endpoints or identifiers.
  */
final class ReadinessGate(
    checks: Vector[ReadinessCheck],
    cacheMs: Long,
    timeoutMs: Long,
    nowNanos: () => Long = () => System.nanoTime(),
    log: String => Unit = s => org.slf4j.LoggerFactory.getLogger("scholarchain.readiness").warn(s)
) extends AutoCloseable {
  require(cacheMs > 0 && timeoutMs > 0)
  private val pool = new ThreadPoolExecutor(
    math.max(1, checks.size),
    math.max(2, checks.size * 2),
    30L,
    TimeUnit.SECONDS,
    new SynchronousQueue[Runnable](),
    ServiceThreads.daemon("readiness-check")
  )
  private var verdict: Option[(Long, Boolean)] = None
  private var lastFailures = Vector.empty[String]

  /** The names of the checks that failed in the most recent evaluation. */
  def failing: Vector[String] = synchronized(lastFailures)

  def ready: Boolean = synchronized {
    val now = nowNanos()
    verdict.filter((at, _) => now - at < cacheMs * 1000000L) match {
      case Some((_, value)) => value
      case None =>
        val value = evaluate()
        verdict = Some((nowNanos(), value))
        value
    }
  }

  private def evaluate(): Boolean = {
    val started = nowNanos()
    val running: Vector[(String, Option[Future[Boolean]])] = checks.map { check =>
      check.name -> (try Some(pool.submit(() => check.probe()))
      catch { case _: RejectedExecutionException => None })
    }
    val failures = running
      .filterNot { (_, future) =>
        future.exists { f =>
          val remaining = timeoutMs * 1000000L - (nowNanos() - started)
          try f.get(math.max(0L, remaining), TimeUnit.NANOSECONDS)
          catch {
            case _: TimeoutException => f.cancel(true); false
            case _: InterruptedException =>
              Thread.currentThread().interrupt(); f.cancel(true); false
            case _: ExecutionException => false
            case NonFatal(_)           => f.cancel(true); false
          }
        }
      }
      .map(_._1)
    lastFailures = failures
    if (failures.nonEmpty) log("readiness-failed:" + failures.mkString(","))
    failures.isEmpty
  }
  def close(): Unit = { pool.shutdownNow(); () }
}
