package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.File
import java.nio.file.Files
import scala.sys.process._

class CheckFailurePathSpec extends AnyFunSuite {

  test("checkTask aborts before markTestRun when an earlier step fails") {
    val repoRoot = locateRepoRoot()
    val marker = new File(repoRoot, TestRunMarker.relativeMarkerPath)
    val beforeExists = marker.isFile
    val beforeContent =
      if (beforeExists) Some(Files.readString(marker.toPath)) else None
    val beforeModified = if (beforeExists) marker.lastModified() else 0L

    val exitCode =
      Process(
        Seq("sbt", "-Dscholarchain.checkProbe.fail=true", "checkTask"),
        repoRoot
      ).!

    assert(
      exitCode != 0,
      s"expected checkTask to fail with injected probe, got exit code $exitCode"
    )

    if (beforeExists) {
      assert(marker.isFile, "marker file should remain present")
      assert(Files.readString(marker.toPath) == beforeContent.get)
      assert(
        marker.lastModified() == beforeModified,
        "marker must not be rewritten after a failed checkTask"
      )
    } else {
      assert(!marker.exists(), "marker must not be created when checkTask fails")
    }
  }

  private def locateRepoRoot(): File = {
    var dir = new File(sys.props.getOrElse("user.dir", ".")).getCanonicalFile
    while (dir != null && !new File(dir, "build.sbt").isFile)
      dir = dir.getParentFile
    require(
      dir != null && new File(dir, "build.sbt").isFile,
      "could not locate ScholarChain repo root from user.dir"
    )
    dir
  }
}
