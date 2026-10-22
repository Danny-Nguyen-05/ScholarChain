package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

class Java17GuardSpec extends AnyFunSuite {
  test("Java 17 passes and other specification versions fail with repair guidance") {
    Java17Guard.requireJava17("17")
    Seq("11", "21", "25").foreach { version =>
      val failure = intercept[IllegalArgumentException](Java17Guard.requireJava17(version))
      assert(failure.getMessage.contains("requires Java 17"))
      assert(failure.getMessage.contains(s"found Java $version"))
      assert(failure.getMessage.contains("JAVA_HOME"))
    }
  }
}
