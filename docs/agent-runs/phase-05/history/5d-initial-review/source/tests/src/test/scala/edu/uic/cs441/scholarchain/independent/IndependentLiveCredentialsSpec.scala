package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite

/** Missing or syntactically invalid synthetic credentials fail before any HTTP dispatch. */
class IndependentLiveCredentialsSpec extends AnyFunSuite {
  test(
    "constructing a live transport does not read credentials and missing credential fails locally"
  ) {
    val reads = new AtomicInteger(0)
    val transport = new OpenAIHttpTransport(() => { reads.incrementAndGet(); None })
    assert(reads.get() == 0)
    val error = intercept[IllegalArgumentException] { transport.post("{}", 100, 1000) }
    assert(reads.get() == 1)
    assert(error.getMessage.contains("unavailable"))
  }

  test(
    "invalid synthetic credential is rejected without exposing its value or making HTTP request"
  ) {
    val sentinel = "synthetic-secret-DO-NOT-LOG\ninvalid-header"
    val reads = new AtomicInteger(0)
    val transport = new OpenAIHttpTransport(() => { reads.incrementAndGet(); Some(sentinel) })
    val error = intercept[IllegalArgumentException] { transport.post("{}", 100, 1000) }
    assert(reads.get() == 1)
    assert(!error.toString.contains(sentinel) && !error.toString.contains("DO-NOT-LOG"))
  }
}
