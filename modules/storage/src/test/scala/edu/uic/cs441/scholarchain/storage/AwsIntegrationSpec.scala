package edu.uic.cs441.scholarchain.storage

import org.scalatest.{Tag}
import org.scalatest.funsuite.AnyFunSuite

object AwsIntegration extends Tag("edu.uic.cs441.scholarchain.storage.AwsIntegration")

/** Discovery only registers the tagged body. All opt-in/configuration/provider access is inside it.
  */
class AwsIntegrationSpec extends AnyFunSuite {
  test("provisioned AWS storage ports round-trip one bounded synthetic run", AwsIntegration) {
    val settings =
      try AwsLiveSettings.load(sys.env)
      catch {
        case _: Exception =>
          fail(
            "Live integration refused: explicit Phase 14C opt-in, approved configuration and validated budget are required."
          )
      }
    // This is the only call site that can construct live clients or mutate remote fixture data.
    try AwsLiveRun.execute(settings)
    catch {
      case _: Exception =>
        fail(
          "Live integration failed; inspect its local owned-data manifest and approved AWS diagnostics. Provider/configuration payloads are suppressed."
        )
    }
  }
}
