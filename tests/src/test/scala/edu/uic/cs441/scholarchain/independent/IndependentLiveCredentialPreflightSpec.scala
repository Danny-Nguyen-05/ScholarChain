package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

/** Every credential is synthetic. Invalid headers fail locally, before HTTP can be dispatched. */
class IndependentLiveCredentialPreflightSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*

  private val localFailures: Vector[(String, () => Option[String])] = Vector(
    "missing" -> (() => None),
    "empty" -> (() => Some("")),
    "CRLF" -> (() => Some("synthetic-secret-DO-NOT-LOG\r\ninvalid")),
    "NUL" -> (() => Some("synthetic-secret-DO-NOT-LOG\u0000invalid")),
    "DEL" -> (() => Some("synthetic-secret-DO-NOT-LOG\u007finvalid")),
    "non-Latin1" -> (() => Some("synthetic-secret-DO-NOT-LOG\u0100invalid")),
    "supplier exception" -> (() =>
      throw new IllegalArgumentException("synthetic-secret-DO-NOT-LOG")
    )
  )

  localFailures.foreach { (description, credential) =>
    test(s"$description local credential failure preserves the same approval ledger for recovery") {
      val c = config
      val r = request(c)
      val path = Files
        .createTempDirectory("scholarchain-independent-credential-preflight-")
        .toRealPath()
        .resolve("ledger.json")
      val reads = new AtomicInteger(0)
      val transport = new OpenAIHttpTransport(() => {
        reads.incrementAndGet()
        credential()
      })
      val firstLedger = new LiveBudgetLedger(c, path)
      val before = firstLedger.snapshot
      val (trace, afterFailure) =
        try {
          val result = new LiveAdjudicator(c, transport, firstLedger, None).adjudicate(r)
          (result, firstLedger.snapshot)
        } finally firstLedger.close()

      // Reopening the exact same approval path tests durable recovery, not a replacement budget.
      val recoveredLedger = new LiveBudgetLedger(c, path)
      val persisted = recoveredLedger.snapshot
      val calls = new AtomicInteger(0)
      val validInjected = new OpenAITransport {
        def post(body: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse = {
          calls.incrementAndGet()
          http(envelope(r))
        }
      }
      val (recovery, afterRecovery) =
        try {
          val result = new LiveAdjudicator(c, validInjected, recoveredLedger, None).adjudicate(r)
          (result, recoveredLedger.snapshot)
        } finally recoveredLedger.close()

      assert(reads.get() == 1, "local credential supplier should be inspected once")
      assert(trace.status == "CREDENTIAL_INVALID", s"unexpected safe status: ${trace.status}")
      assert(trace.error.contains("LIVE_CREDENTIAL_UNAVAILABLE_OR_INVALID"))
      assert(trace.attempts == 0 && trace.result.isEmpty && !trace.cacheHit)
      assert(!trace.toString.contains("DO-NOT-LOG"))
      assert(afterFailure == before, "local credential refusal changed the approval budget")
      assert(persisted == before, "local credential refusal changed the durable approval budget")
      assert(!persisted.fused && persisted.attempts == 0 && persisted.unknownUsageAttempts == 0)
      assert(persisted.reservedInputTokens == 0 && persisted.reservedOutputTokens == 0)
      assert(persisted.reservedSpendMicrousd == 0)
      assert(
        recovery.status == "VALIDATED_LIVE" && recovery.result.nonEmpty,
        s"same-ledger recovery failed: ${recovery.status}: ${recovery.error}"
      )
      assert(calls.get() == 1 && recovery.attempts == 1)
      assert(afterRecovery.attempts == 1 && afterRecovery.unknownUsageAttempts == 0)
      assert(!afterRecovery.fused && afterRecovery.observedInputTokens == 120)
      assert(afterRecovery.observedOutputTokens == 40 && afterRecovery.reservedSpendMicrousd > 0)
    }
  }
}
