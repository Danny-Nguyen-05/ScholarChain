package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite

/** Hand-computed reservations on a synthetic approval-scoped ledger, never monetary authorization.
  */
class IndependentLiveBudgetSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*
  private def path = Files
    .createTempDirectory("scholarchain-independent-ledger-")
    .toRealPath()
    .resolve("ledger.json")
  private def use(c: LiveProviderConfig)(f: LiveBudgetLedger => Unit): Unit = {
    val l = new LiveBudgetLedger(c, path)
    try f(l)
    finally l.close()
  }

  test("zero attempts token or spend allowance reserves nothing") {
    Vector(
      config.budget.copy(maxAttempts = 0),
      config.budget.copy(maxInputTokens = 0),
      config.budget.copy(maxOutputTokens = 0),
      config.budget.copy(maxSpendMicrousd = 0)
    ).foreach { b =>
      use(config.copy(budget = b)) { l =>
        assert(l.reserve(100).isLeft)
        assert(l.snapshot.attempts == 0 && l.snapshot.reservedSpendMicrousd == 0)
      }
    }
  }

  test("exact token and microdollar boundary allows one reservation and refuses the next") {
    // 100 wire bytes + 4096 framing = 4196 reserved input tokens; output cap = 1024.
    // ceil((4196 * 125000 + 1024 * 500000) / 1000000) = 1037 microdollars.
    val c = config.copy(budget =
      config.budget.copy(maxInputTokens = 4196, maxOutputTokens = 1024, maxSpendMicrousd = 1037)
    )
    use(c) { l =>
      assert(l.reserve(100).contains((4196L, 1024L)))
      assert(l.snapshot.reservedSpendMicrousd == 1037 && l.snapshot.unknownUsageAttempts == 1)
      assert(l.reserve(100).isLeft && l.snapshot.attempts == 1)
    }
    use(c.copy(budget = c.budget.copy(maxSpendMicrousd = 1036))) { l =>
      assert(l.reserve(100).isLeft && l.snapshot.attempts == 0)
    }
  }

  test(
    "unknown usage remains charged across restart and observed usage never refunds reservations"
  ) {
    val file = path
    val c = config.copy(budget = config.budget.copy(maxAttempts = 1))
    val first = new LiveBudgetLedger(c, file)
    try assert(first.reserve(100).isRight)
    finally first.close()
    val resumed = new LiveBudgetLedger(c, file)
    try {
      assert(resumed.snapshot.attempts == 1 && resumed.snapshot.unknownUsageAttempts == 1)
      assert(resumed.reserve(100).isLeft)
      resumed.observe(ProviderUsage(120, 40, 160, 10, 20, 0), 4196, 1024)
      val observed = resumed.snapshot
      assert(observed.unknownUsageAttempts == 0)
      assert(observed.reservedInputTokens == 4196 && observed.reservedOutputTokens == 1024)
      assert(observed.observedInputTokens == 120 && observed.observedOutputTokens == 40)
      assert(observed.observedReasoningTokens == 10 && observed.observedCachedInputTokens == 20)
    } finally resumed.close()
  }

  test(
    "approval scoped ledger refuses simultaneous writers and a changed configuration on restart"
  ) {
    val file = path
    val first = new LiveBudgetLedger(config, file)
    try {
      assert(first.reserve(100).isRight)
      intercept[Exception] { val duplicate = new LiveBudgetLedger(config, file); duplicate.close() }
    } finally first.close()
    intercept[Exception] {
      val changed =
        new LiveBudgetLedger(config.copy(approvalId = "different-synthetic-approval"), file)
      changed.close()
    }
  }

  test(
    "provider usage above reservation fuses later attempts and invalid wire lengths do not reserve"
  ) {
    use(config) { l =>
      assert(l.reserve(0).isLeft && l.reserve(config.budget.maxRequestBytes + 1).isLeft)
      assert(l.snapshot.attempts == 0)
      assert(l.reserve(100).isRight)
      l.observe(ProviderUsage(4197, 40, 4237, 10, 0, 0), 4196, 1024)
      assert(l.snapshot.fused)
      assert(l.reserve(100).isLeft && l.snapshot.attempts == 1)
    }
  }
}
