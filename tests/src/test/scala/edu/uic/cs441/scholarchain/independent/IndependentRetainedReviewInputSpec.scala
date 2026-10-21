package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.file.{Files, Path, StandardCopyOption}
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

/** B2 exact retention tests on disposable synthetic completed inputs, never source-population
  * edits.
  */
class IndependentRetainedReviewInputSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  private def original(): Path = {
    val a = work("conf/independent/retained/A", doi = Some("10.5555/retained-review"))
    val b = work("conf/independent/retained/B", doi = Some("10.5555/retained-review"))
    val block = candidate(a, b)
    val framed = block.copy(provenance = block.provenance.copy(datasetSnapshot = "hadoop-prep"))
    IndependentCompletedPrepFixture.create(Vector(a, b), Vector(framed))
  }
  private def loaded(path: Path): ResolutionInput = {
    val result = InputLoader.load(path, ResolutionConfig.example)
    assert(
      result.isRight,
      s"valid synthetic completed input must load before mutation: $path -> $result"
    )
    result.toOption.get
  }
  private def retainedCopy(source: Path): Path = {
    val root = Files.createTempDirectory("scholarchain-independent-retained-review-").toRealPath()
    val target = root.resolve("completed-phase4")
    val entries = Files.walk(source)
    try
      entries.iterator.asScala.toVector.sortBy(_.getNameCount).foreach { from =>
        val to = target.resolve(source.relativize(from))
        if (Files.isDirectory(from)) Files.createDirectories(to)
        else Files.copy(from, to, StandardCopyOption.COPY_ATTRIBUTES)
      }
    finally entries.close()
    target
  }
  private def exportPart(root: Path): Path = {
    val entries = Files.walk(root.resolve("export"))
    try
      entries.iterator.asScala
        .find(p =>
          Files.isRegularFile(p) && p.getFileName.toString.startsWith("part-") && Files.size(p) > 0
        )
        .get
    finally entries.close()
  }

  test(
    "B2 exact completed input retention reloads with identical evidence candidate hashes and pair population"
  ) {
    val source = original()
    val copy = retainedCopy(source)
    val config = ResolutionConfig.example
    val before = loaded(source)
    val after = loaded(copy)
    assert(before.inputEvidenceHash == after.inputEvidenceHash)
    val first = CandidateBuilder.build(before, config).toOption.get
    val replay = CandidateBuilder.build(after, config).toOption.get
    assert(first.pairs.nonEmpty)
    assert(ReviewQueue.populationHash(first) == ReviewQueue.populationHash(replay))
    assert(first == replay)
    assert(before.works == after.works && before.candidates == after.candidates)
  }

  test("B2 a missing retained export part cannot silently become a different replay population") {
    val source = original()
    loaded(source)
    val copy = retainedCopy(source)
    loaded(copy)
    Files.delete(exportPart(copy))
    assert(InputLoader.load(copy, ResolutionConfig.example).isLeft)
  }

  test("B2 corrupt retained observation bytes are rejected before queue reconstruction") {
    val source = original()
    loaded(source)
    val copy = retainedCopy(source)
    loaded(copy)
    val part = exportPart(copy)
    val before = Files.readString(part)
    val changed = before + " "
    assert(
      changed != before && changed.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > before
        .getBytes(java.nio.charset.StandardCharsets.UTF_8)
        .length
    )
    Files.writeString(part, changed)
    assert(InputLoader.load(copy, ResolutionConfig.example).isLeft)
  }
}
