package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

class IndependentPrepReaderSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  import IndependentCompletedPrepFixture.{create, marker, saveMarker, refreshParts, runToken}
  private def fixture(): Path = create(Vector(work("conf/independent/Reader")))
  private def load(path: Path) = InputLoader.load(path, ResolutionConfig.example)
  private def workPart(path: Path): Path =
    path.resolve(s"export/snapshot=$snapshot/run=$runToken/work/part-r-00000")
  private def mutateRow(path: Path)(f: ujson.Value => Unit): Unit = {
    val file = workPart(path)
    val json = ujson.read(Files.readString(file, UTF_8).trim)
    f(json)
    Files.writeString(file, json.render() + "\n", UTF_8)
    refreshParts(path)
  }

  test("independently framed completed run loads and partial stage or completion fails") {
    val valid = fixture()
    val loaded = load(valid)
    assert(loaded.isRight, loaded.toString)
    assert(loaded.toOption.get.works.size == 1)
    val partial = fixture()
    Files.delete(partial.resolve("intermediate/j07/_SUCCESS"))
    assert(load(partial).isLeft)
    val noMarker = fixture()
    Files.delete(noMarker.resolve("_SCHOLARCHAIN_COMPLETE"))
    assert(load(noMarker).isLeft)
  }

  test("digest length and exact inventory are independently enforced") {
    val corrupt = fixture()
    Files.writeString(workPart(corrupt), " ", UTF_8, java.nio.file.StandardOpenOption.APPEND)
    assert(load(corrupt).isLeft)
    val extra = fixture()
    Files.writeString(extra.resolve("export/uninventoried.jsonl"), "{}\n", UTF_8)
    assert(load(extra).isLeft)
    val absent = fixture()
    Files.delete(workPart(absent))
    assert(load(absent).isLeft)
    val wrongHash = fixture()
    val value = marker(wrongHash)
    value("exportParts")(0)("sha256") = ujson.Str("0" * 64)
    saveMarker(wrongHash, value)
    assert(load(wrongHash).isLeft)
  }

  test("completion traversal symlink duplicate inventory and mismatched provenance fail closed") {
    val traversal = fixture()
    val value = marker(traversal)
    value("exportParts")(0)("path") = ujson.Str("../outside.jsonl")
    saveMarker(traversal, value)
    assert(load(traversal).isLeft)
    val duplicate = fixture()
    val dup = marker(duplicate)
    dup("exportParts").arr += ujson.read(dup("exportParts")(0).render())
    saveMarker(duplicate, dup)
    assert(load(duplicate).isLeft)
    val symlink = fixture()
    val file = workPart(symlink)
    val external = Files.createTempFile("scholarchain-independent-link-", ".jsonl").toRealPath()
    Files.copy(file, external, java.nio.file.StandardCopyOption.REPLACE_EXISTING)
    Files.delete(file)
    Files.createSymbolicLink(file, external)
    assert(load(symlink).isLeft)
    val wrongRun = fixture()
    mutateRow(wrongRun)(j =>
      j("provenance")("runId") = ujson.Str("run:33333333-3333-4333-8333-333333333333")
    )
    assert(load(wrongRun).isLeft)
  }

  test("digest-valid unknown schema nested keys and incomplete JSONL remain invalid") {
    val schema = fixture()
    mutateRow(schema)(j => j("schemaVersion") = ujson.Str("scholarchain.domain.v99"))
    assert(load(schema).isLeft)
    val unknown = fixture()
    mutateRow(unknown)(j => j("authors")(0)("inventedIdentity") = ujson.Str("researcher:invented"))
    assert(load(unknown).isLeft)
    val option = fixture()
    mutateRow(option)(j => j("year") = ujson.Arr(2020, 2021))
    assert(load(option).isLeft, "an Option must not silently take the first of several values")
    val truncated = fixture()
    val text = Files.readString(workPart(truncated), UTF_8)
    Files.writeString(workPart(truncated), text.stripSuffix("\n"), UTF_8)
    refreshParts(truncated)
    assert(load(truncated).isLeft)
  }

  test("standalone author rows cannot borrow or omit members from a nested source observation") {
    val missing = fixture()
    val authors =
      missing.resolve(s"export/snapshot=$snapshot/run=$runToken/author-mention/part-r-00000")
    Files.writeString(authors, "", UTF_8)
    refreshParts(missing)
    assert(load(missing).isLeft)
    val duplicate = fixture()
    val dup =
      duplicate.resolve(s"export/snapshot=$snapshot/run=$runToken/author-mention/part-r-00000")
    Files.writeString(
      dup,
      Files.readString(dup, UTF_8),
      UTF_8,
      java.nio.file.StandardOpenOption.APPEND
    )
    refreshParts(duplicate)
    assert(load(duplicate).isLeft)
  }

  test("input byte record and lookup bounds reject before trusting a population") {
    val dir = fixture()
    val config = ResolutionConfig.example
    assert(
      InputLoader.load(dir, config.copy(input = config.input.copy(maxInputRecords = 1))).isLeft
    )
    val two = create(Vector(work("conf/independent/LimitA"), work("conf/independent/LimitB")))
    assert(
      InputLoader
        .load(two, config.copy(input = config.input.copy(maxLookupObservations = 1)))
        .isLeft
    )
    assert(
      InputLoader
        .load(dir, config.copy(input = config.input.copy(maxInputBytes = 16, maxRecordBytes = 16)))
        .isLeft
    )
  }
}
