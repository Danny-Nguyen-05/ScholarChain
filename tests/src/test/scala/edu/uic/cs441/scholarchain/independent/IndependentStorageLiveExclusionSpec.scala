package edu.uic.cs441.scholarchain.independent

import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files

/** Source-only safety checks: never loads, instantiates, discovers or executes a live Suite. */
class IndependentStorageLiveExclusionSpec extends AnyFunSuite {
  private val root = IndependentTestSupport.repoRoot
  private def source(path: String): String = Files.readString(root.resolve(path), UTF_8)

  private def registrationIsOffline(text: String): Boolean = {
    val code = RuntimeGraphFence.code(text)
    val start = "\\btest\\s*\\(".r.findFirstMatchIn(code).map(_.start).getOrElse(code.length)
    val prefix = code.take(start)
    !Vector(
      "sys.env",
      "System.getenv",
      "Files.",
      "ProfileCredentialsProvider",
      "S3Client",
      "DynamoDbClient",
      "NeptunedataClient",
      "S3VectorsClient",
      "AwsLiveSettings.load",
      "AwsLiveRun.execute"
    )
      .exists(prefix.contains)
  }

  test(
    "live suite source registers one exact-tagged body and enters the opt-in gate before execution"
  ) {
    val text = source(
      "modules/storage/src/test/scala/edu/uic/cs441/scholarchain/storage/AwsIntegrationSpec.scala"
    )
    val code = RuntimeGraphFence.code(text)
    assert(text.contains("Tag(\"edu.uic.cs441.scholarchain.storage.AwsIntegration\")"))
    assert("\\btest\\s*\\(".r.findAllMatchIn(code).size == 1)
    assert("(?s)test\\s*\\([^)]*,\\s*AwsIntegration\\s*\\)\\s*\\{".r.findFirstIn(code).nonEmpty)
    assert(registrationIsOffline(text))
    val gate = code.indexOf("AwsLiveSettings.load(sys.env)")
    val execute = code.indexOf("AwsLiveRun.execute(settings)")
    assert(gate >= 0 && execute > gate)
    info("Checked tagged suite source only; no live test class was loaded or executed.")
  }

  test("live initialization check detects provider or environment access outside a tagged body") {
    val good =
      "class Fixture extends AnyFunSuite { test(\"bounded\", AwsIntegration) { AwsLiveSettings.load(sys.env) } }"
    assert(registrationIsOffline(good))
    Vector(
      "val env = sys.env",
      "val c = S3Client.builder().build()",
      "val c = AwsLiveSettings.load(sys.env)"
    ).foreach { eager =>
      assert(
        !registrationIsOffline(
          s"class Fixture extends AnyFunSuite { $eager; test(\"bounded\", AwsIntegration) {} }"
        )
      )
    }
  }

  test(
    "normal Test configuration excludes the exact live tag while the separate profile selects it"
  ) {
    val build = source("project/ScholarChainBuild.scala")
    val policy = source("project/AwsIntegrationPolicy.scala")
    assert(policy.contains("edu.uic.cs441.scholarchain.storage.AwsIntegration"))
    assert(
      "(?s)Test / testOptions \\+= Tests.Argument\\(\\s*TestFrameworks.ScalaTest,\\s*\"-l\",\\s*scholarchain.build.AwsIntegrationPolicy.tag".r
        .findFirstIn(build)
        .nonEmpty
    )
    assert(
      "(?s)AwsIntegration / testOptions := Seq\\(\\s*Tests.Argument\\(TestFrameworks.ScalaTest, \"-n\", scholarchain.build.AwsIntegrationPolicy.tag".r
        .findFirstIn(build)
        .nonEmpty
    )
    assert(build.contains(".dependsOn(AwsIntegration / requireAwsIntegration)"))
    assert(policy.contains("SCHOLARCHAIN_AWS_ITEST") && policy.contains("AWS_PROFILE"))
  }
}
