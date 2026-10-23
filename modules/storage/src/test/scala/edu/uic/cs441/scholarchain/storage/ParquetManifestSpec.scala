package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import org.apache.parquet.schema.MessageTypeParser
import org.apache.parquet.example.data.simple.SimpleGroupFactory
import org.apache.parquet.hadoop.example.ExampleParquetWriter
import org.apache.hadoop.conf.Configuration
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*
import StorageResult.*

class ParquetManifestSpec extends AnyFunSuite {
  private def temporary[A](f: Path => A): A = {
    val root = Files.createTempDirectory("storage-parquet-test-")
    try f(root)
    finally {
      val walk = Files.walk(root);
      try
        walk
          .sorted(java.util.Comparator.reverseOrder[Path]())
          .iterator()
          .asScala
          .foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }
  test("local completed Parquet export streams nested LIST records and restores partition window") {
    temporary { root =>
      val schema = MessageTypeParser.parseMessageType("""message fixture {
        required binary nodeId (UTF8);
        optional group context { required binary runId (UTF8); }
        optional group properties (LIST) { repeated group list { optional group element {
          required binary name (UTF8); required binary value (UTF8);
        } } }
        optional int64 publicationCount;
        optional binary absent (UTF8);
      }""")
      val factory = new SimpleGroupFactory(schema)
      val group =
        factory.newGroup().append("nodeId", "synthetic-node").append("publicationCount", 7L)
      group.addGroup("context").append("runId", "synthetic-run")
      group
        .addGroup("properties")
        .addGroup("list")
        .addGroup("element")
        .append("name", "observed")
        .append("value", "synthetic")
      val relative = "nodes/type=researcher"
      val directory = root.resolve(relative).resolve("window=all-years/run_id=synthetic-run")
      Files.createDirectories(directory)
      val conf = new Configuration(false);
      conf.set("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
      val writer = ExampleParquetWriter
        .builder(new org.apache.hadoop.fs.Path(directory.resolve("part-00000.parquet").toUri))
        .withConf(conf)
        .withType(schema)
        .build()
      try writer.write(group)
      finally writer.close()
      val lineage = SparkLineage(
        "synthetic-hadoop",
        "synthetic-snapshot",
        "synthetic-er",
        "synthetic-policy",
        "a" * 64,
        Vector.empty,
        Vector.empty
      )
      val context =
        SparkRecordContext(SchemaVersions.sparkAnalytics, "synthetic-run", None, lineage)
      val manifest = LoadManifest(
        context,
        "s3",
        relative,
        Vector(relative),
        "parquet",
        1,
        Vector("nodeId"),
        Vector("window", "run_id"),
        "b" * 64,
        Vector("all-years"),
        "storage-engineer",
        Vector.empty
      )
      val run = "{\"runId\":\"synthetic-run\"}\n"
      val metadata = ujson
        .Obj(
          "runId" -> "synthetic-run",
          "hadoopRunId" -> lineage.hadoopRunId,
          "entityResolutionRunId" -> lineage.entityResolutionRunId,
          "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
          "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
          "tables" -> ujson.Arr(
            ujson.Obj(
              "dataset" -> relative,
              "path" -> relative,
              "rowCount" -> 1L,
              "contentHash" -> ("b" * 64)
            )
          )
        )
        .render() + "\n"
      assert(ujson.read(metadata)("tables")(0)("rowCount") == ujson.Str("1"))
      Files.writeString(root.resolve("run-manifest.json"), run, UTF_8)
      Files.writeString(root.resolve("run-metadata.json"), metadata, UTF_8)
      Files.writeString(root.resolve("counters.json"), "[]", UTF_8)
      Files.writeString(
        root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
        StableIds.sha256Hex(run + "\n" + metadata) + "\n",
        UTF_8
      )
      val reader = new LocalParquetManifestReader(root)
      val iterator = StorageResult.value(reader.open(manifest)).get
      try {
        assert(iterator.hasNext)
        val row = iterator.next()
        assert(row("nodeId").str == "synthetic-node")
        assert(row("window").str == "all-years")
        assert(row("context")("runId").str == "synthetic-run")
        assert(
          row("properties").arr.toVector == Vector(
            ujson.Obj("name" -> "observed", "value" -> "synthetic")
          )
        )
        assert(row("publicationCount").num == 7)
        assert(row("absent") == ujson.Null)
        assert(!iterator.hasNext)
      } finally iterator.close()
      assert(
        reader.open(
          manifest.copy(context =
            context.copy(lineage = lineage.copy(entityResolutionPolicyHash = "c" * 64))
          )
        ) == Rejected("invalid-manifest-source")
      )
      // Even with a correctly recomputed completion marker, malformed or mismatched counts
      // cannot pass source binding. Numeric JSON is not the producer's Long wire encoding.
      val malformedCounts = Vector[ujson.Value](
        ujson.Num(1),
        ujson.Str("1.0"),
        ujson.Str("1e0"),
        ujson.Str("+1"),
        ujson.Str("-1"),
        ujson.Str(" 1"),
        ujson.Str("1 "),
        ujson.Str("9223372036854775808"),
        ujson.Str("2"),
        ujson.Null
      )
      malformedCounts.foreach { count =>
        val changed = ujson.read(metadata)
        changed("tables")(0)("rowCount") = count
        val changedText = changed.render() + "\n"
        Files.writeString(root.resolve("run-metadata.json"), changedText, UTF_8)
        Files.writeString(
          root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
          StableIds.sha256Hex(run + "\n" + changedText) + "\n",
          UTF_8
        )
        assert(reader.open(manifest) == Rejected("invalid-manifest-source"))
      }
      Files.writeString(root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), "invalid", UTF_8)
      assert(reader.qualifications("synthetic-run") == Rejected("incomplete-or-corrupt-source-run"))
    }
  }
  test("manifest counts use exact nonnegative decimal Long strings without Double rounding") {
    Vector(
      "0" -> 0L,
      "1" -> 1L,
      "0001" -> 1L,
      "9007199254740993" -> 9007199254740993L,
      "9223372036854775807" -> Long.MaxValue
    ).foreach { case (text, expected) =>
      assert(ManifestMetadata.rowCount(ujson.Str(text)).contains(expected))
    }
    val invalid = Vector[ujson.Value](
      ujson.Str(""),
      ujson.Str("1.5"),
      ujson.Str("1e3"),
      ujson.Str("+1"),
      ujson.Str("-0"),
      ujson.Str("-1"),
      ujson.Str(" 1"),
      ujson.Str("1\n"),
      ujson.Str("9223372036854775808"),
      ujson.Str("١"),
      ujson.Num(0),
      ujson.Num(1),
      ujson.Bool(true),
      ujson.Null,
      ujson.Arr(),
      ujson.Obj()
    )
    invalid.foreach(value => assert(ManifestMetadata.rowCount(value).isEmpty))
  }
  test("Parquet integer values outside exact JSON range reject instead of rounding") {
    val schema =
      MessageTypeParser.parseMessageType("message fixture { required int64 publicationCount; }")
    val group =
      new SimpleGroupFactory(schema).newGroup().append("publicationCount", 9007199254740993L)
    val error = intercept[SourceRejected](ParquetJson.group(group, schema))
    assert(error.code == "integer-outside-exact-json-range")
  }
}
