package scholarchain.build

import org.scalatest.funsuite.AnyFunSuite

import java.io.File
import java.nio.file.Files

class TestRunMarkerSpec extends AnyFunSuite {

  test("write creates gitignored marker path with success and timestamp") {
    val repo = Files.createTempDirectory("scholarchain-marker").toFile
    try {
      TestRunMarker.write(repo)
      val marker = new File(repo, TestRunMarker.relativeMarkerPath)
      assert(marker.isFile)
      val text = Files.readString(marker.toPath)
      assert(text.contains("success=true"))
      assert(text.contains("timestamp="))
    } finally deleteRecursively(repo)
  }

  private def deleteRecursively(file: File): Unit =
    if (file.isDirectory) file.listFiles().foreach(deleteRecursively)
    file.delete()
}
