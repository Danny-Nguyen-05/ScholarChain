package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.StorageResult
import java.util.concurrent.{CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.{AtomicInteger, AtomicLong}
import org.scalatest.funsuite.AnyFunSuite

class ReadinessGateSpec extends AnyFunSuite {
  private def passing(name: String, calls: AtomicInteger = new AtomicInteger) =
    ReadinessCheck(name, () => { calls.incrementAndGet(); true })

  test("only a found or cleanly missing answer counts as reachable and authorized") {
    import StorageResult.*
    assert(ReadinessProbes.answered(Missing))
    assert(ReadinessProbes.answered(Found(1)))
    assert(ReadinessProbes.answered(Written(1)) && ReadinessProbes.answered(Unchanged(1)))
    assert(ReadinessProbes.answered(Retried(2, Missing)))
    assert(!ReadinessProbes.answered(Rejected("provider-rejected")))
    assert(!ReadinessProbes.answered(Retried(2, Rejected("retry-exhausted"))))
  }

  test("ready only when every check passes, naming the failing checks") {
    val gate = new ReadinessGate(
      Vector(passing("a"), passing("b")),
      cacheMs = 10,
      timeoutMs = 1000,
      log = _ => ()
    )
    try { assert(gate.ready); assert(gate.failing.isEmpty) }
    finally gate.close()
    val failing = new ReadinessGate(
      Vector(passing("a"), ReadinessCheck("b", () => false), passing("c")),
      10,
      1000,
      log = _ => ()
    )
    try { assert(!failing.ready); assert(failing.failing == Vector("b")) }
    finally failing.close()
  }

  test("a throwing check is not ready and the gate stays usable") {
    val gate = new ReadinessGate(
      Vector(ReadinessCheck("boom", () => throw new IllegalStateException("provider-detail"))),
      10,
      1000,
      log = _ => ()
    )
    try assert(!gate.ready)
    finally gate.close()
  }

  test("a hanging check fails within the timeout instead of blocking the caller") {
    val interrupted = new CountDownLatch(1)
    val hang = ReadinessCheck(
      "hang",
      () =>
        try { Thread.sleep(60000); true }
        catch { case _: InterruptedException => interrupted.countDown(); false }
    )
    val gate = new ReadinessGate(Vector(passing("ok"), hang), 10, 150, log = _ => ())
    try {
      val started = System.nanoTime()
      assert(!gate.ready)
      val elapsedMs = (System.nanoTime() - started) / 1000000
      assert(elapsedMs < 2000, s"elapsed $elapsedMs ms")
      assert(gate.failing == Vector("hang"))
      assert(interrupted.await(2, TimeUnit.SECONDS), "the timed-out probe is cancelled")
    } finally gate.close()
  }

  test("the verdict is cached for the configured time, pass or fail, then evaluated again") {
    val now = new AtomicLong(0)
    val calls = new AtomicInteger
    val gate = new ReadinessGate(
      Vector(passing("a", calls)),
      cacheMs = 1000,
      timeoutMs = 1000,
      nowNanos = () => now.get,
      log = _ => ()
    )
    try {
      assert(gate.ready && gate.ready && gate.ready)
      assert(calls.get == 1)
      now.set(999L * 1000000L)
      assert(gate.ready && calls.get == 1)
      now.set(1001L * 1000000L)
      assert(gate.ready && calls.get == 2)
    } finally gate.close()
    val failures = new AtomicInteger
    val failingGate = new ReadinessGate(
      Vector(ReadinessCheck("f", () => { failures.incrementAndGet(); false })),
      1000,
      1000,
      nowNanos = () => now.get,
      log = _ => ()
    )
    try {
      assert(!failingGate.ready && !failingGate.ready)
      assert(failures.get == 1, "a failing verdict is cached too, so peers do not hammer")
    } finally failingGate.close()
  }

  test("concurrent callers share a single evaluation") {
    val calls = new AtomicInteger
    val release = new CountDownLatch(1)
    val slow = ReadinessCheck(
      "slow",
      () => { calls.incrementAndGet(); release.await(2, TimeUnit.SECONDS); true }
    )
    val gate = new ReadinessGate(Vector(slow), 5000, 3000, log = _ => ())
    val pool = Executors.newFixedThreadPool(8)
    try {
      val results = (1 to 8).map(_ => pool.submit(() => gate.ready))
      Thread.sleep(100)
      release.countDown()
      assert(results.forall(_.get(5, TimeUnit.SECONDS)))
      assert(calls.get == 1)
    } finally { pool.shutdownNow(); gate.close() }
  }

  test("only check names are logged, never details") {
    val logged = new java.util.concurrent.ConcurrentLinkedQueue[String]()
    val gate = new ReadinessGate(
      Vector(ReadinessCheck("neptune", () => throw new IllegalStateException("secret-endpoint"))),
      10,
      1000,
      log = logged.add(_)
    )
    try {
      assert(!gate.ready)
      assert(logged.toArray.toVector == Vector("readiness-failed:neptune"))
    } finally gate.close()
  }
}
