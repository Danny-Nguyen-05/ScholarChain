package scholarchain.build

import org.scalatest.Tag
import org.scalatest.funsuite.AnyFunSuite

class AwsIntegrationPolicySpec extends AnyFunSuite {
  test("live tests require the exact opt-in and an explicit profile together") {
    val disabled = Seq(
      Map.empty[String, String],
      Map("AWS_PROFILE" -> "approved-test"),
      Map("SCHOLARCHAIN_AWS_ITEST" -> "true", "AWS_PROFILE" -> "approved-test"),
      Map("SCHOLARCHAIN_AWS_ITEST" -> "1"),
      Map("SCHOLARCHAIN_AWS_ITEST" -> "1", "AWS_PROFILE" -> ""),
      Map("SCHOLARCHAIN_AWS_ITEST" -> "1", "AWS_PROFILE" -> "   ")
    )
    disabled.foreach(env =>
      intercept[IllegalArgumentException](AwsIntegrationPolicy.requireEnabled(env))
    )
    AwsIntegrationPolicy.requireEnabled(
      Map("SCHOLARCHAIN_AWS_ITEST" -> "1", "AWS_PROFILE" -> "approved-test")
    )
  }
}

// An offline sentinel. A successful default test run proves the live-test tag
// was excluded, since this body would fail immediately if it were selected.
class AwsIntegrationExclusionSentinelSpec extends AnyFunSuite {
  test("default test commands must exclude this sentinel", Tag(AwsIntegrationPolicy.tag)) {
    fail("awsIntegration exclusion sentinel was executed")
  }
}
