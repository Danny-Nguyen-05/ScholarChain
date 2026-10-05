package scholarchain.build

import java.io.File
import java.nio.file.Files
import java.time.Instant

object TestRunMarker {
  val relativeMarkerPath = ".claude/.last-test-run"

  def write(repoRoot: File): Unit = {
    require(
      !TestRunMarkerPolicy.shouldSkipWriteAfterFailedChecks,
      "markTestRun must not run when prior checks failed"
    )
    val markerFile = new File(repoRoot, relativeMarkerPath)
    Files.createDirectories(markerFile.getParentFile.toPath)
    val content =
      s"""success=true
         |timestamp=${Instant.now.toEpochMilli}
         |""".stripMargin
    Files.writeString(markerFile.toPath, content)
  }

  def main(args: Array[String]): Unit =
    if (args.length != 1) {
      sys.error("usage: TestRunMarker <repoRoot>")
    } else {
      write(new File(args(0)))
    }
}
