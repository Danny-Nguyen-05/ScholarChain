package edu.uic.cs441.scholarchain.independent

import java.nio.charset.StandardCharsets.UTF_8
import org.scalatest.funsuite.AnyFunSuite

/** Literal-source checks supplement mock-plan assertions and manual IAM review. */
class IndependentTerraformSourceSpec extends AnyFunSuite {
  private def check(arguments: String*): Unit = {
    val root = IndependentTestSupport.repoRoot
    val command = Vector("python3", "-I", "tests/infra/terraform_source_guard.py") ++ arguments
    val process = new ProcessBuilder(command*)
      .directory(root.toFile)
      .redirectErrorStream(true)
      .start()
    val output = new String(process.getInputStream.readAllBytes(), UTF_8)
    assert(process.waitFor() == 0, output)
  }

  test("Terraform source guard detects synthetic unsafe permissions, public access and secrets") {
    check("--self-test")
  }

  test("Git-visible authored Terraform passes the bounded literal-source guard") {
    check("--repo-root", IndependentTestSupport.repoRoot.toString)
  }
}
