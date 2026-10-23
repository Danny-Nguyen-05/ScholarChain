package edu.uic.cs441.scholarchain.storage

import org.scalatest.funsuite.AnyFunSuite
import java.io.StringReader
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import StorageResult.*

class Phase7BFeaturesSpec extends AnyFunSuite {
  test("RFC4180 preserves CR/LF quotes and distinguishes unknown numeric cells from quoted text") {
    val csv = new CsvRecords(
      new StringReader("id,year,text\r\na,,\"line1\r\nline2 \"\"quoted\"\"\"\r\nb,2020,\"\"\r\n"),
      1000
    )
    try {
      assert(csv.next().get.map(_.text) == Vector("id", "year", "text"))
      assert(
        csv.next().get == Vector(
          CsvCell("a", false),
          CsvCell("", false),
          CsvCell("line1\r\nline2 \"quoted\"", true)
        )
      )
      assert(
        csv.next().get == Vector(CsvCell("b", false), CsvCell("2020", false), CsvCell("", true))
      )
      assert(csv.next().isEmpty)
    } finally csv.close()
    val invalid = new CsvRecords(new StringReader("\"unfinished"), 100)
    try assert(intercept[SourceRejected](invalid.next()).code == "malformed-csv")
    finally invalid.close()
  }
  test("CSV bounds reject oversized cells and maliciously wide records") {
    val wide = new CsvRecords(new StringReader(Vector.fill(33)("a").mkString(",")), 100)
    try assert(intercept[SourceRejected](wide.next()).code == "csv-column-limit")
    finally wide.close()
    val long = new CsvRecords(new StringReader("12345"), 4)
    try assert(intercept[SourceRejected](long.next()).code == "csv-cell-limit")
    finally long.close()
  }
  test("spilled logical hashes are independent of order chunk size and retain duplicate rows") {
    val root = Files.createTempDirectory("storage-spill-feature-")
    try {
      val a = ujson.Obj("x" -> "a"); val b = ujson.Obj("x" -> "b")
      val first = new SpillDigest(root.resolve("one"), 1); Vector(a, b, a).foreach(first.add)
      val second = new SpillDigest(root.resolve("two"), 2); Vector(b, a, a).foreach(second.add)
      val one = first.finish(); assert(one == second.finish()); assert(first.rowCount == 3)
      val fewer = new SpillDigest(root.resolve("fewer"), 1); Vector(a, b).foreach(fewer.add)
      assert(one != fewer.finish())
      // Empty logical-table digest is exactly the method tag followed by a single LF.
      val empty = new SpillDigest(root.resolve("empty"), 1)
      assert(
        empty.finish() == ExportFiles.hash("sha256-fixed-256-shard-sorted-row-json-merkle-v1\n")
      )
    } finally ExportFiles.deleteTree(root)
  }
  test("full source qualifications are stored once and remain retrievable by verified pointer") {
    val objects = new InMemoryObjectStore; val registry = new InMemoryArtifactRegistry
    val qualifications =
      "{\"runId\":\"synthetic\",\"converged\":false,\"distanceP90\":\"approximate\",\"largeDetails\":\"" + ("x" * 500000) + "\"}"
    val first = StorageResult
      .value(SourceQualifications.put("synthetic", qualifications, objects, registry))
      .get
    val second = StorageResult
      .value(SourceQualifications.put("synthetic", qualifications, objects, registry))
      .get
    assert(first == second)
    assert(objects.writeOrder.size == 1)
    assert(SourceQualifications.get(first, objects, registry) == Found(qualifications))
    assert(upickle.default.write(first).getBytes(UTF_8).length < 512)
    assert(SourceQualifications.get(first.copy(sha256 = "0" * 64), objects, registry) == Missing)
  }
  test("community lookup tokens bind exact source window and community without adding identities") {
    val token = CommunityLookup.membership("2015-2019", "community:synthetic")
    assert(token.matches("\\|[0-9a-f]{64}\\|"))
    assert(token != CommunityLookup.membership("2020-2026", "community:synthetic"))
    assert(token != CommunityLookup.membership("2015-2019", "community:other"))
    assert(CommunityLookup.window("all-years").matches("\\|[0-9a-f]{64}\\|"))
  }
  test("reader rejects responses exceeding the caller's requested bound") {
    import java.lang.reflect.{InvocationHandler, Method, Proxy}
    import software.amazon.awssdk.services.neptunedata.NeptunedataClient
    import software.amazon.awssdk.services.neptunedata.model.ExecuteOpenCypherQueryResponse
    import software.amazon.awssdk.core.document.Document
    import scala.jdk.CollectionConverters.*
    var calls = 0
    val client = Proxy
      .newProxyInstance(
        classOf[NeptunedataClient].getClassLoader,
        Array(classOf[NeptunedataClient]),
        new InvocationHandler {
          def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = {
            assert(method.getName == "executeOpenCypherQuery"); calls += 1
            val rows = Vector("one", "two").map(id =>
              Document.fromMap(Map("nodeId" -> Document.fromString(id)).asJava)
            )
            ExecuteOpenCypherQueryResponse.builder().results(Document.fromList(rows.asJava)).build()
          }
        }
      )
      .asInstanceOf[NeptunedataClient]
    val reader = new NeptuneGraphReader(client, GraphReaderConfig(maxLimit = 10))
    assert(
      reader.communityMembers("synthetic-community", "all-years", 1) == Rejected(
        "graph-response-limit"
      )
    )
    assert(calls == 1)
  }

}
