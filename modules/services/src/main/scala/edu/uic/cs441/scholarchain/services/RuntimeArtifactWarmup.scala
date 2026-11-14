package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.{RuntimeArtifactStore, StorageResult}
import scala.util.control.NonFatal

/** Loads the runtime artifact snapshot in the background so the first real query finds it cached.
  *
  * The store loads lazily inside its first read (download, digest check, parse, validation and
  * indexing). On a small task that can outlast a request's per-stage budget, and a cancelled or
  * failed load is never cached, so without this every request would repeat the download. The
  * warm-up makes one cheap read that cannot match any record, which forces that load, and retries a
  * failed load a few times. It never throws, never blocks startup or readiness, never runs for an
  * unconfigured store, and logs only an outcome category and elapsed milliseconds: no keys,
  * digests, bucket names or credentials.
  */
object RuntimeArtifactWarmup {
  val ThreadName = "runtime-artifact-warm"
  val DefaultAttempts = 3
  val DefaultBackoffMs = 5000L
  val Loaded = "loaded"

  /** The probe asks for a zero-length context. A loaded store refuses that bound before it looks at
    * any record, while a store whose load failed answers with the load's own rejection code (or
    * Missing when the object is absent). A bound refusal is therefore the one proof of a loaded
    * snapshot that cannot be confused with an absent edge or researcher.
    */
  private val loadedProbeCode = "runtime-result-bound"

  def outcome(store: RuntimeArtifactStore): String =
    try
      store.researcherContext("", "", 0) match {
        case StorageResult.Rejected(`loadedProbeCode`) => Loaded
        case StorageResult.Rejected(code)              => code
        case StorageResult.Missing                     => "runtime-artifact-missing"
        case r if StorageResult.successful(r)          => Loaded
        case _                                         => "runtime-artifact-unavailable"
      }
    catch {
      case _: InterruptedException => Thread.currentThread().interrupt(); "warmup-interrupted"
      case NonFatal(_)             => "warmup-exception"
    }

  /** Synchronous warm-up. Returns true once the snapshot is loaded. */
  def run(
      store: RuntimeArtifactStore,
      attempts: Int = DefaultAttempts,
      backoffMs: Long = DefaultBackoffMs,
      sleep: Long => Unit = Thread.sleep(_),
      nowNanos: () => Long = () => System.nanoTime(),
      log: String => Unit = s => org.slf4j.LoggerFactory.getLogger("scholarchain.warmup").info(s)
  ): Boolean = {
    if (store eq UnconfiguredRuntimeArtifacts) return false
    var attempt = 1
    var done = false
    while (!done && attempt <= attempts && !Thread.currentThread().isInterrupted) {
      val started = nowNanos()
      val result = outcome(store)
      val elapsedMs = (nowNanos() - started) / 1000000L
      safely(
        log(
          s"runtime-artifact-warmup attempt=$attempt/$attempts outcome=$result elapsedMs=$elapsedMs"
        )
      )
      done = result == Loaded
      if (!done && attempt < attempts) {
        try sleep(backoffMs)
        catch { case _: InterruptedException => Thread.currentThread().interrupt() }
      }
      attempt += 1
    }
    done
  }

  /** Starts the daemon warm-up thread. Returns None when the store is unconfigured. */
  def start(
      store: RuntimeArtifactStore,
      attempts: Int = DefaultAttempts,
      backoffMs: Long = DefaultBackoffMs,
      sleep: Long => Unit = Thread.sleep(_),
      log: String => Unit = s => org.slf4j.LoggerFactory.getLogger("scholarchain.warmup").info(s)
  ): Option[Thread] =
    if (store eq UnconfiguredRuntimeArtifacts) None
    else {
      val task: Runnable = () =>
        try { run(store, attempts, backoffMs, sleep, () => System.nanoTime(), log); () }
        catch { case NonFatal(_) => () }
      val thread = new Thread(task, ThreadName)
      thread.setDaemon(true)
      try { thread.start(); Some(thread) }
      catch { case NonFatal(_) => None }
    }

  private def safely(f: => Unit): Unit = try f
  catch { case NonFatal(_) => () }
}
