package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.LoadManifest
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8
import org.scalatest.funsuite.AnyFunSuite

/** Phase 14B replan, 14C decision 4 (user, 2026-11-08): the bounded runtime artifact stays within
  * 10,000 rows and 16 MiB, the caps are "never raised", the include list is validated and
  * order-independent, and a source that is not a complete, consistent export refuses the whole run
  * and writes no artifact. Written from those requirements through the public API only: the
  * module's own 18 + 9 specs build full exports with module-private hashing helpers, which a
  * cross-module test cannot (and should not) re-implement, so this spec pins the contract values
  * and the refusal path that need no export.
  */
class IndependentRuntimeSubsetPinsSpec extends AnyFunSuite {
  private def parse(text: String) = IncludeList.parse(text.getBytes(UTF_8))
  private val a = "researcher:dblp:" + "a" * 64
  private val b = "researcher:dblp:" + "b" * 64
  private val work = "work:dblp:synthetic/ab"

  test("the default caps are 10,000 rows and 16 MiB and the other bounds are finite") {
    val config = RuntimeArtifactConfig()
    assert(config.maxRows == 10000)
    assert(config.maxBytes == 16 * 1024 * 1024)
    assert(config.maxRowBytes == 1024 * 1024)
    assert(config.maxMetadataBytes == 4 * 1024 * 1024)
    assert(config.maxResults == 100)
  }

  test("a cap of zero or less is not constructible") {
    Seq(
      () => RuntimeArtifactConfig(maxRows = 0),
      () => RuntimeArtifactConfig(maxBytes = 0),
      () => RuntimeArtifactConfig(maxRows = -1)
    ).foreach(make => assertThrows[IllegalArgumentException](make()))
  }

  test("the include list accepts researcher and work IDs, ignores blanks and comments") {
    val parsed = parse(s"# first\n\n$b\n  $a  \n$work\n")
    assert(parsed.isRight)
    val list = parsed.toOption.get
    assert(list.ids == Vector(a, b, work).sorted)
    assert(list.researchers == Vector(a, b) && list.works == Vector(work))
    assert(list.duplicateLines == 0)
  }

  test("the include list is normalized: order, duplicates and comments do not change the hash") {
    val one = parse(s"$a\n$b\n$work\n").toOption.get
    val two = parse(s"# note\n$work\n$b\n$a\n$a\n\n$b\n").toOption.get
    assert(one.ids == two.ids)
    assert(one.normalizedSha256 == two.normalizedSha256)
    assert(two.duplicateLines == 2)
    assert(one.fileSha256 != two.fileSha256, "the raw file hash still tells the files apart")
    val other = parse(s"$a\n$work\n").toOption.get
    assert(other.normalizedSha256 != one.normalizedSha256)
  }

  test("an empty, malformed or unsupported include list is refused with a stated reason") {
    assert(parse("") == Left("include-list-empty"))
    assert(parse("# only a comment\n\n") == Left("include-list-empty"))
    Seq(
      "topic:openalex:T1",
      "researcher",
      "researcher:",
      "researcher:has space",
      "work:x y",
      "RESEARCHER:dblp:a"
    )
      .foreach(bad => assert(parse(s"$a\n$bad\n") == Left("include-list-invalid-id"), bad))
  }

  test("the include list is bounded in count and in bytes") {
    val many = (1 to IncludeList.maxIds + 1).map(i => s"researcher:dblp:$i").mkString("\n")
    assert(parse(many) == Left("include-list-too-many-ids"))
    val atLimit = (1 to IncludeList.maxIds).map(i => s"researcher:dblp:$i").mkString("\n")
    assert(parse(atLimit).isRight)
    assert(
      IncludeList.parse(Array.fill(IncludeList.maxBytes + 1)('x'.toByte)) == Left(
        "include-list-too-large"
      )
    )
  }

  test(
    "a source with no manifests refuses the whole run: no artifact, a report, the reader untouched"
  ) {
    var reads = 0
    val reader = new ManifestRowReader {
      def open(manifest: LoadManifest): StorageResult[CloseableRowIterator] = {
        reads += 1; StorageResult.Rejected("unused")
      }
      def qualifications(runId: String): StorageResult[String] = {
        reads += 1; StorageResult.Rejected("unused")
      }
    }
    val include = parse(s"$a\n").toOption.get
    val outcome = RuntimeArtifactSubset.build(Vector.empty, reader, include)
    assert(outcome.result.isLeft)
    assert(outcome.result.left.toOption.get.code == "invalid-runtime-source-manifests")
    assert(reads == 0, "nothing may be read before the source manifests are accepted")
    assert(outcome.report("status").str == "refused")
    assert(outcome.report("refusal")("code").str == "invalid-runtime-source-manifests")
    assert(
      outcome.report("caps")("maxRows").num == 10000 && outcome
        .report("caps")("maxBytes")
        .num == 16.0 * 1024 * 1024
    )
    assert(outcome.report("includeList")("ids").num == 1)
  }

  test("the refusal report states the rule and never contains the include list's IDs") {
    val reader = new ManifestRowReader {
      def open(manifest: LoadManifest): StorageResult[CloseableRowIterator] =
        StorageResult.Rejected("unused")
      def qualifications(runId: String): StorageResult[String] = StorageResult.Rejected("unused")
    }
    val outcome =
      RuntimeArtifactSubset.build(Vector.empty, reader, parse(s"$a\n$b\n$work\n").toOption.get)
    val text = outcome.report.render()
    assert(outcome.report("rule").str == RuntimeArtifactSubset.ruleId)
    assert(text.contains("no half entities") || text.contains("whole or not at all"))
    assert(!text.contains(a) && !text.contains(b) && !text.contains(work))
  }
}
