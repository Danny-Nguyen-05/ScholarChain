package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.read

/** Recording transports never dispatch HTTP. All approvals, responses and usage are synthetic. */
class IndependentLiveAdjudicatorSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*
  private class Recording(f: (Int, AdjudicationRequest) => ProviderHttpResponse)
      extends OpenAITransport {
    val calls = new AtomicInteger(0)
    def post(body: String, timeout: Int, maxBytes: Int): ProviderHttpResponse = {
      val r = read[AdjudicationRequest](ujson.read(body)("input").str)
      f(calls.incrementAndGet(), r)
    }
  }

  test("budget exhaustion refuses dispatch before credential supplier access") {
    val c = config.copy(budget = config.budget.copy(maxAttempts = 0))
    val reads = new AtomicInteger(0)
    val transport = new OpenAIHttpTransport(() => { reads.incrementAndGet(); None })
    val l = ledger(c)
    try {
      val trace = new LiveAdjudicator(c, transport, l, None).adjudicate(request(c))
      assert(trace.status == "BUDGET_EXHAUSTED" && trace.result.isEmpty && trace.attempts == 0)
      assert(reads.get() == 0 && l.snapshot.attempts == 0)
    } finally l.close()
  }

  test("retries consume durable reservations and authentication errors are terminal") {
    Vector(429 -> 2, 503 -> 2, 401 -> 1, 400 -> 1).foreach { (status, expected) =>
      val l = ledger()
      val transport = new Recording((_, _) =>
        ProviderHttpResponse(status, "synthetic-sensitive-body-DO-NOT-LOG", None)
      )
      try {
        val trace = new LiveAdjudicator(config, transport, l, None).adjudicate(request())
        assert(trace.result.isEmpty && transport.calls.get() == expected)
        assert(l.snapshot.attempts == expected && l.snapshot.unknownUsageAttempts == expected)
        assert(!trace.toString.contains("DO-NOT-LOG"))
      } finally l.close()
    }
  }

  test(
    "a valid provider response records actual usage separately and replay never consumes another reservation"
  ) {
    val l = ledger()
    val cache =
      java.nio.file.Files.createTempDirectory("scholarchain-independent-live-cache-").toRealPath()
    val transport = new Recording((_, r) => http(envelope(r)))
    try {
      val runner = new LiveAdjudicator(config, transport, l, Some(cache))
      val fresh = runner.adjudicate(request())
      val replay = runner.adjudicate(request())
      assert(
        fresh.status == "VALIDATED_LIVE" && fresh.result.nonEmpty && !fresh.cacheHit,
        s"${fresh.status}: ${fresh.error}"
      )
      assert(replay.status == "CACHE_HIT" && replay.cacheHit && replay.result == fresh.result)
      assert(transport.calls.get() == 1 && l.snapshot.attempts == 1)
      assert(l.snapshot.observedInputTokens == 120 && l.snapshot.observedOutputTokens == 40)
      assert(l.snapshot.unknownUsageAttempts == 0 && l.snapshot.reservedInputTokens > 120)
    } finally l.close()
  }

  test(
    "missing usage and thrown transport details remain unknown charged failures without leaking contents"
  ) {
    val l = ledger()
    val noUsage = new Recording((_, r) => http(changed(envelope(r))(_.obj.remove("usage"))))
    try {
      val trace = new LiveAdjudicator(config, noUsage, l, None).adjudicate(request())
      assert(trace.result.isEmpty && l.snapshot.unknownUsageAttempts == 1)
      assert(l.snapshot.reservedSpendMicrousd > 0)
    } finally l.close()
    val failedLedger = ledger()
    val throwing =
      new Recording((_, _) => throw new RuntimeException("synthetic-secret-DO-NOT-LOG"))
    try {
      val trace = new LiveAdjudicator(config, throwing, failedLedger, None).adjudicate(request())
      assert(trace.result.isEmpty && !trace.toString.contains("DO-NOT-LOG"))
      assert(
        failedLedger.snapshot.attempts == 1 && failedLedger.snapshot.unknownUsageAttempts == 1 && failedLedger.snapshot.fused
      )
    } finally failedLedger.close()
  }

  test("interruption-resistant transport fuses later calls and never overlaps retries") {
    val release = new CountDownLatch(1)
    val done = new CountDownLatch(1)
    val active = new AtomicInteger(0)
    val maximum = new AtomicInteger(0)
    val transport = new Recording((_, r) => {
      val now = active.incrementAndGet(); maximum.accumulateAndGet(now, (a, b) => math.max(a, b))
      try {
        while (release.getCount > 0) {
          try release.await()
          catch { case _: InterruptedException => () }
        }
        http(envelope(r))
      } finally { active.decrementAndGet(); done.countDown() }
    })
    val l = ledger()
    try {
      val runner = new LiveAdjudicator(config, transport, l, None)
      val first = runner.adjudicate(request())
      assert(first.status == "ADAPTER_NOT_TERMINATED" && first.result.isEmpty)
      assert(l.snapshot.fused && l.snapshot.unknownUsageAttempts == 1)
      val second = runner.adjudicate(request())
      assert(second.result.isEmpty && transport.calls.get() == 1 && maximum.get() == 1)
    } finally { release.countDown(); assert(done.await(2, TimeUnit.SECONDS)); l.close() }
  }

  test(
    "unapproved numerical configuration cannot construct an active adjudicator or budget ledger"
  ) {
    val unapproved = config.copy(approved = false)
    assert(LiveProviderConfig.validate(unapproved, requireApproval = true).isLeft)
    intercept[IllegalArgumentException] {
      val l = ledger(unapproved)
      l.close()
    }
  }
}
