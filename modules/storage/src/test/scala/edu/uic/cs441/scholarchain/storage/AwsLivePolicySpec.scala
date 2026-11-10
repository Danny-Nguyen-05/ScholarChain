package edu.uic.cs441.scholarchain.storage

import org.scalatest.funsuite.AnyFunSuite
import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*

/** Offline tests of pure guard/config/fixture behavior. No live test body is invoked. */
class AwsLivePolicySpec extends AnyFunSuite {
  private def config(directory: String): ujson.Obj = ujson.Obj(
    "schemaVersion" -> "scholarchain.aws-integration.v1",
    "environment" -> "synthetic",
    "approvedEnvironment" -> "synthetic",
    "phase14cGateReference" -> "synthetic-test-only-not-an-approval",
    "executionApproved" -> true,
    "pricingValidated" -> true,
    "budgetValidated" -> true,
    "incrementalBudgetUsd" -> 5.0,
    "region" -> "synthetic-region",
    "readerProfile" -> "synthetic-reader",
    "loaderProfile" -> "synthetic-loader",
    "cleanupProfile" -> "synthetic-cleanup",
    "bucket" -> "synthetic-bucket",
    "tables" -> ujson.read(
      upickle.default.write(
        DynamoTables(
          "synthetic-runs",
          "synthetic-links",
          "synthetic-sessions",
          "synthetic-evidence",
          "synthetic-artifacts",
          "synthetic-metrics",
          "synthetic-idempotency"
        )
      )
    ),
    "vectorBucket" -> "synthetic-vectors",
    "vectorIndex" -> "researcher-profile-v1",
    "dimension" -> 256,
    "metric" -> "cosine",
    "neptuneEndpoint" -> "https://synthetic.invalid:8182",
    "neptuneRoleArn" -> "synthetic-loader-role",
    "fixturePrefix" -> "synthetic-live-tests",
    "manifestDirectory" -> directory,
    "cleanupAuthorized" -> false
  )
  test("live settings refuse before file reads unless opt-in and profile are explicit") {
    val missing = Map("SCHOLARCHAIN_AWS_ITEST_CONFIG" -> "/this/path/is-not-read-by-disabled-tests")
    Vector(
      missing,
      missing + ("SCHOLARCHAIN_AWS_ITEST" -> "1"),
      missing ++ Map("SCHOLARCHAIN_AWS_ITEST" -> "1", "AWS_PROFILE" -> " ")
    ).foreach { environment =>
      assert(!AwsLiveSettings.enabled(environment))
      val error = intercept[IllegalArgumentException](AwsLiveSettings.load(environment))
      assert(error.getMessage.contains("opt-in and profile"))
    }
  }
  test(
    "live configuration requires explicit approval pricing budget resource and endpoint bounds"
  ) {
    val valid = config("/synthetic/manifest-directory")
    assert(AwsLiveSettings.parse(valid, "synthetic-profile").budgetUsd == 5.0)
    assert(!AwsLiveSettings.parse(valid, "synthetic-profile").cleanupAuthorized)
    Vector("executionApproved", "pricingValidated", "budgetValidated").foreach { field =>
      val bad = ujson.read(valid.render()); bad(field) = false;
      intercept[IllegalArgumentException](AwsLiveSettings.parse(bad, "synthetic-profile"))
    }
    val badBudget = ujson.read(valid.render()); badBudget("incrementalBudgetUsd") = 5.01
    intercept[IllegalArgumentException](AwsLiveSettings.parse(badBudget, "synthetic-profile"))
    val badEndpoint = ujson.read(valid.render());
    badEndpoint("neptuneEndpoint") = "http://synthetic.invalid"
    intercept[IllegalArgumentException](AwsLiveSettings.parse(badEndpoint, "synthetic-profile"))
    val badEnvironment = ujson.read(valid.render());
    badEnvironment("approvedEnvironment") = "different"
    intercept[IllegalArgumentException](AwsLiveSettings.parse(badEnvironment, "synthetic-profile"))
  }
  test("live configuration accepts only Titan V2 widths and rejects the former template value 2") {
    val valid = config("/synthetic/manifest-directory")
    Vector(256, 512, 1024).foreach { width =>
      val ok = ujson.read(valid.render()); ok("dimension") = width
      assert(AwsLiveSettings.parse(ok, "synthetic-profile").dimension == width)
    }
    Vector(2.0, 255.0, 4096.0, 256.5, 0.0).foreach { width =>
      val bad = ujson.read(valid.render()); bad("dimension") = width
      val error =
        intercept[IllegalArgumentException](AwsLiveSettings.parse(bad, "synthetic-profile"))
      assert(error.getMessage.contains("invalid vector dimension"))
    }
  }
  test("synthetic live graph fixture has exact stable IDs support and unknown-year cells") {
    val run = "run:00112233-4455-4677-8899-aabbccddeeff"
    val fixture = LiveGraphFixture.create(run)
    assert(fixture.nodeIds.size == 3 && fixture.nodeIds.distinct.size == 3)
    assert(fixture.nodeIds.take(2).forall(_.matches("researcher:dblp:[0-9a-f]{64}")))
    assert(fixture.nodeIds(2) == "work:dblp:synthetic/live/00112233-4455-4677-8899-aabbccddeeff")
    assert(StableIds.parseSparkCoauthorEdgeId(fixture.edgeId).isRight)
    val csv = new CsvRecords(new java.io.StringReader(fixture.edgesCsv), 65536)
    try {
      val header = csv.next().get.map(_.text); val row = csv.next().get
      val map = header.zip(row).toMap
      assert(map("jointPublicationCount:Long").text == "1")
      Vector(
        "firstCollaborationYear:Int",
        "lastCollaborationYear:Int",
        "windowStartYear:Int",
        "windowEndYear:Int"
      ).foreach(h => assert(map(h) == CsvCell("", false)))
      assert(map("evidenceEdgeId:String").text == fixture.edgeId)
      assert(map("evidenceTable:String").text == "edges/type=coauthored_with_support")
      assert(
        map(":START_ID").text == fixture.nodeIds.head && map(":END_ID").text == fixture.nodeIds(1)
      )
      assert(csv.next().isEmpty)
    } finally csv.close()
    val handle = fixture.handle()
    try {
      assert(handle.nodeCount == 3 && handle.edgeCount == 1 && handle.supportCount == 1)
      val support = org.apache.parquet.hadoop.ParquetReader
        .builder[org.apache.parquet.example.data.Group](
          new org.apache.parquet.hadoop.example.GroupReadSupport,
          new org.apache.hadoop.fs.Path(
            handle.root.resolve("edges/type=coauthored_with_support/part-0.parquet").toUri
          )
        )
        .build()
      try {
        val row = support.read(); assert(row.getString("edgeId", 0) == fixture.edgeId);
        assert(row.getString("workId", 0) == fixture.nodeIds(2));
        assert(row.getFieldRepetitionCount("year") == 0); assert(support.read() == null)
      } finally support.close()
    } finally { handle.close(); ExportFiles.deleteTree(handle.root) }
  }
  test(
    "owned-data manifest records intentions before confirmations and retains per-run ownership"
  ) {
    val root = Files.createTempDirectory("live-policy-journal-")
    try {
      val settings = AwsLiveSettings.parse(config(root.toString), "synthetic-profile")
      val run = "run:00112233-4455-4677-8899-aabbccddeeff"
      val journal = new LiveRunManifest(root, run, settings)
      val item = OwnedLiveItem(
        "s3",
        settings.bucket,
        "synthetic/versions/unique/file",
        expectedHash = "a" * 64
      )
      intercept[IllegalArgumentException](journal.record(item.copy(state = "created")))
      journal.plan(item)
      assert(
        ujson.read(Files.readString(journal.path, UTF_8))("items")(0)("state").str == "planned"
      )
      journal.record(item.copy(state = "created")); journal.finish("passed-retained")
      val json = ujson.read(Files.readString(journal.path, UTF_8))
      assert(json("runId").str == run && json("items")(0)("state").str == "created")
      assert(!json.obj.contains("credentials"))
    } finally ExportFiles.deleteTree(root)
  }
}
