package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{Phase6Context, Phase6Export}
import edu.uic.cs441.scholarchain.storage.*
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.sql.functions.lit
import org.apache.spark.sql.types.*
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** A real local Spark-to-Parquet handoff, with no AWS, Docker, or previously retained dataset. */
class IndependentStorageParquetSpec extends AnyFunSuite {
  import IndependentStorageFixtures.*
  import StorageResult.*

  test(
    "Spark Parquet metrics load with integral doubles, nested lineage, nulls and physical partitions"
  ) {
    val root = Files.createTempDirectory("independent-storage-spark-parquet-")
    var spark: SparkSession = null
    try {
      spark = SparkSession
        .builder()
        .master("local[2]")
        .appName("Independent Phase7A storage Parquet compatibility")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
        .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
        .getOrCreate()
      val schema = new StructType()
        .add("context", Phase6Context.schema)
        .add("researcherId", StringType)
        .add("policyVersion", StringType)
        .add("publicationCount", LongType)
        .add("distinctCoauthorCount", LongType)
        .add("totalCoauthorOccurrences", LongType)
        .add("averageCoauthorsPerPaper", DoubleType)
        .add("maximumCoauthorsOnOnePaper", LongType)
        .add("maxTeamWorkIds", ArrayType(StringType))
        .add("maxTeamWorkTieCount", LongType)
        .add("weightedDegree", LongType)
        .add("componentId", StringType)
        .add("communityId", StringType)
        .add("coreness", IntegerType)
      val lineage = context.lineage
      val nested = Row(
        context.schemaVersion,
        runId,
        "all-years",
        Row(
          lineage.hadoopRunId,
          lineage.hadoopSnapshot,
          lineage.entityResolutionRunId,
          lineage.entityResolutionPolicyVersion,
          lineage.entityResolutionPolicyHash,
          lineage.sourceWorkIds.asJava,
          lineage.sourceMentionIds.asJava
        )
      )
      val workIds = Vector("work:dblp:independent/synthetic/storage").asJava
      val rows = Vector(
        Row(
          nested,
          researcherId,
          policyVersion,
          2L,
          2L,
          2L,
          1.0,
          2L,
          workIds,
          1L,
          2L,
          "component:" + "d" * 64,
          null,
          Integer.valueOf(1)
        ),
        Row(
          nested,
          secondResearcherId,
          policyVersion,
          1L,
          0L,
          0L,
          0.0,
          0L,
          workIds,
          1L,
          0L,
          "component:" + "e" * 64,
          null,
          Integer.valueOf(0)
        )
      )
      val table = spark
        .createDataFrame(rows.asJava, schema)
        .withColumn("window", lit("all-years"))
        .withColumn("run_id", lit(runId))
      val dataset = "metrics/type=researcher_collaboration"
      // The producer supplies the hash. Literal stored-value expectations below independently
      // check this cross-module handoff rather than deriving metric expectations from its code.
      val contentHash = Phase6Export.logicalTableHash(table)
      table.write.partitionBy("window", "run_id").parquet(root.resolve(dataset).toString)
      val source = manifest(dataset, 2, Vector("researcherId"))
        .copy(
          paths = Vector(dataset),
          partitionColumns = Vector("window", "run_id"),
          sortedRowsSha256 = contentHash
        )
      val runJson = ujson.Obj("runId" -> runId).render() + "\n"
      val metadata = ujson
        .Obj(
          "runId" -> runId,
          "hadoopRunId" -> lineage.hadoopRunId,
          "entityResolutionRunId" -> lineage.entityResolutionRunId,
          "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
          "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
          "tables" -> ujson.Arr(
            ujson.Obj(
              "dataset" -> dataset,
              "path" -> dataset,
              "rowCount" -> 2L,
              "contentHash" -> contentHash
            )
          )
        )
        .render() + "\n"
      // Phase6Export publishes its Long row count through ujson's string encoding. This is a
      // producer-shaped metadata fixture, not a complete Phase6Export.publish invocation.
      assert(ujson.read(metadata)("tables")(0)("rowCount") == ujson.Str("2"))
      Files.writeString(root.resolve("run-manifest.json"), runJson, UTF_8)
      Files.writeString(root.resolve("run-metadata.json"), metadata, UTF_8)
      Files.writeString(root.resolve("counters.json"), "[]", UTF_8)
      Files.writeString(
        root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
        StableIds.sha256Hex(runJson + "\n" + metadata) + "\n",
        UTF_8
      )
      val store = new InMemoryResearcherMetricStore()
      val reader = new LocalParquetManifestReader(root)
      val loader = new Phase6CacheLoader(
        new InMemoryEntityLinkCache(),
        store,
        reader,
        CacheLoaderConfig(sortChunkRows = 1)
      )
      val first = loader.load(Vector(source))
      assert(first == Written(CacheLoadReport(2, 0, 0, 2)), first.toString)
      val positive = CoreJson
        .parse[ResearcherMetricsDetail](
          StorageResult.value(store.get(researcherId, "all-years")).get.payloadJson
        )
        .toOption
        .get
      val solo = CoreJson
        .parse[ResearcherMetricsDetail](
          StorageResult.value(store.get(secondResearcherId, "all-years")).get.payloadJson
        )
        .toOption
        .get
      assert(positive.averageCoauthorsPerPaper == 1.0 && positive.publicationCount == 2L)
      assert(solo.averageCoauthorsPerPaper == 0.0 && solo.publicationCount == 1L)
      assert(positive.communityId.isEmpty && solo.communityId.isEmpty)
      assert(positive.context.lineage == lineage && solo.context.lineage == lineage)
      assert(positive.maxTeamWorkIds == Vector("work:dblp:independent/synthetic/storage"))
      assert(loader.load(Vector(source)) == Unchanged(CacheLoadReport(0, 2, 0, 2)))
    } finally {
      if (spark != null) spark.stop()
      val walk = Files.walk(root)
      try
        walk
          .sorted(java.util.Comparator.reverseOrder[Path]())
          .iterator()
          .asScala
          .foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }

  test("completed source metadata rejects malformed row counts before opening Parquet") {
    val root = Files.createTempDirectory("independent-storage-invalid-count-")
    try {
      val dataset = "metrics/type=researcher_collaboration"
      val source = manifest(dataset, 2, Vector("researcherId")).copy(paths = Vector(dataset))
      val lineage = context.lineage
      val runJson = ujson.Obj("runId" -> runId).render() + "\n"
      val metadata = ujson.Obj(
        "runId" -> runId,
        "hadoopRunId" -> lineage.hadoopRunId,
        "entityResolutionRunId" -> lineage.entityResolutionRunId,
        "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
        "tables" -> ujson.Arr(
          ujson.Obj(
            "dataset" -> dataset,
            "path" -> dataset,
            "rowCount" -> 2L,
            "contentHash" -> source.sortedRowsSha256
          )
        )
      )
      Files.writeString(root.resolve("run-manifest.json"), runJson, UTF_8)
      val invalid = Vector[ujson.Value](
        ujson.Num(2),
        ujson.Num(2.5),
        ujson.Str("2.0"),
        ujson.Str("2e0"),
        ujson.Str("+2"),
        ujson.Str("-2"),
        ujson.Str(" 2"),
        ujson.Str("2 "),
        ujson.Str(""),
        ujson.Str("9223372036854775808"),
        ujson.Null,
        ujson.Bool(true)
      )
      invalid.foreach { count =>
        metadata("tables")(0)("rowCount") = count
        val text = metadata.render() + "\n"
        Files.writeString(root.resolve("run-metadata.json"), text, UTF_8)
        // Refresh the completion binding so rejection tests the count, not a stale marker.
        Files.writeString(
          root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
          StableIds.sha256Hex(runJson + "\n" + text) + "\n",
          UTF_8
        )
        val result = new LocalParquetManifestReader(root).open(source)
        assert(result == Rejected("invalid-manifest-source"), s"count=$count result=$result")
      }
    } finally {
      val walk = Files.walk(root)
      try
        walk
          .sorted(java.util.Comparator.reverseOrder[Path]())
          .iterator()
          .asScala
          .foreach(Files.deleteIfExists)
      finally walk.close()
    }
  }
}
