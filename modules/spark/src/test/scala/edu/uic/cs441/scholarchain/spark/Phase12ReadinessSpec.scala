package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.StableIds
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{Row, SparkSession}
import org.apache.spark.api.java.JavaSparkContext
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class Phase12ReadinessSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  private var root: Path = _
  override protected def beforeAll(): Unit = {
    root = Files.createTempDirectory("scholarchain-phase12-readiness-").toRealPath()
    spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Phase12 readiness feature tests")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
  }
  override protected def afterAll(): Unit = {
    try if (spark != null) spark.stop()
    finally {
      if (root != null) {
        val walk = Files.walk(root)
        try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
        finally walk.close()
      }
      super.afterAll()
    }
  }
  private def process(host: String, pid: String, executor: String) =
    ujson.Obj("host" -> host, "pid" -> pid, "executorId" -> executor)
  private def frame(values: Vector[String]) = spark.createDataFrame(
    values.map(v => Row(v, "run:unchanged")).asJava,
    new StructType().add("value", StringType).add("run_id", StringType)
  )
  private def expected(df: org.apache.spark.sql.DataFrame) = ujson.Obj(
    "rowCount" -> df.count().toString,
    "contentHash" -> Phase6Export.logicalTableHash(df)
  )
  private def metadata: ujson.Obj = ujson.Obj(
    "runId" -> "run:11111111-1111-4111-8111-111111111111",
    "codeVersion" -> ("a" * 64),
    "hadoopRunId" -> "run:hadoop",
    "hadoopManifestHash" -> ("b" * 64),
    "entityResolutionRunId" -> "run:er",
    "entityResolutionManifestHash" -> ("c" * 64),
    "entityResolutionPolicyVersion" -> "policy",
    "entityResolutionPolicyHash" -> ("d" * 64),
    "logicalConfigFingerprint" -> ("e" * 64),
    "identityPolicyVersion" -> "identity",
    "representativePolicyVersion" -> "representative",
    "graphPolicyVersion" -> "graph",
    "windows" -> ujson.Arr(ujson.Obj("windowId" -> "all-years")),
    "seed" -> "7",
    "contentHashMethod" -> Phase6Export.hashMethod,
    "tables" -> ujson.Arr.from(
      Phase12Readiness.datasets.toVector.sorted.map(name =>
        ujson.Obj("dataset" -> name, "path" -> name, "rowCount" -> "0", "contentHash" -> ("f" * 64))
      )
    )
  )

  test("distributed proof rejects local tasks and executor-ID-only masquerading") {
    val driver = process("machine", "100", "driver")
    intercept[IllegalArgumentException](
      Phase12Readiness.requireExternal(driver, process("machine", "100", "driver"))
    )
    intercept[IllegalArgumentException](
      Phase12Readiness.requireExternal(driver, process("machine", "100", "1"))
    )
    intercept[IllegalArgumentException](
      Phase12Readiness.requireExternal(driver, process("other", "200", "unavailable"))
    )
    Phase12Readiness.requireExternal(driver, process("machine", "101", "1"))
    Phase12Readiness.requireExternal(driver, process("other", "100", "1"))
  }

  test("bounded Java results retain the cap and reject excess rows or overflowing bounds") {
    val context = JavaSparkContext.fromSparkContext(spark.sparkContext)
    val two = context.parallelize(Vector("one", "two").asJava, 2)
    assert(BoundedActions.cappedJava(two, 2) == Vector("one", "two"))
    assert(
      BoundedActions.cappedJava(context.parallelize(Vector.empty[String].asJava, 1), 1).isEmpty
    )
    assert(
      intercept[IllegalArgumentException](BoundedActions.cappedJava(two, 1)).getMessage
        .contains("exceeds limit 1")
    )
    Vector(-1, 0, Int.MaxValue).foreach { invalid =>
      assert(
        intercept[IllegalArgumentException](BoundedActions.cappedJava(two, invalid)).getMessage
          .contains("non-overflowing")
      )
    }
  }

  test("actual snapshots expose loaded class origins and hashes without invented versions") {
    val observed = Phase12Readiness.processSnapshot("test")
    assert(observed("pid").str == ProcessHandle.current().pid().toString)
    val libraries = observed("libraries").arr.map(row => row("component").str -> row).toMap
    assert(libraries.keySet == Set("spark", "scala-library", "scala-reflect", "scala3-library"))
    libraries.values.foreach { row =>
      assert(row("origin").str.nonEmpty)
      assert(row("classSha256").str.matches("[0-9a-f]{64}"))
    }
    assert(libraries("spark")("runtimeVersion").str == spark.version)
    assert(libraries("scala-library")("runtimeVersion").str.startsWith("2.13."))
    assert(libraries("scala-reflect")("runtimeVersion") == ujson.Null)
    assert(libraries("scala3-library")("runtimeVersion") == ujson.Null)
  }

  test("exclusive output rejects overwrite, relative destinations and symlink parents") {
    val file = root.resolve("exclusive.json")
    Phase12Readiness.writeNew(file, ujson.Obj("fresh" -> true))
    intercept[IllegalArgumentException](
      Phase12Readiness.writeNew(file, ujson.Obj("fresh" -> false))
    )
    assert(ujson.read(Files.readString(file))("fresh").bool)
    intercept[IllegalArgumentException](
      Phase12Readiness.writeNew(Path.of("relative/file.json"), ujson.Obj())
    )
    val link = root.resolve("linked-directory")
    Files.createSymbolicLink(link, root)
    intercept[IllegalArgumentException](
      Phase12Readiness.writeNew(link.resolve("refused.json"), ujson.Obj())
    )
    Files.delete(link)
  }

  test("completion requires exact manifest and metadata bytes") {
    val directory = Files.createDirectory(root.resolve("complete"))
    val meta = metadata.render() + "\n"
    val manifest = ujson.Obj("runId" -> metadata("runId")).render() + "\n"
    Files.writeString(directory.resolve("run-manifest.json"), manifest, UTF_8)
    Files.writeString(directory.resolve("run-metadata.json"), meta, UTF_8)
    Files.writeString(
      directory.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
      StableIds.sha256Hex(manifest + "\n" + meta) + "\n",
      UTF_8
    )
    assert(Phase12Readiness.completedMetadata(directory)("runId") == metadata("runId"))
    Files.writeString(directory.resolve("run-metadata.json"), meta + " ", UTF_8)
    intercept[IllegalArgumentException](Phase12Readiness.completedMetadata(directory))
  }

  test("semantic bindings and nested windows must match without normalization") {
    val left = metadata; val right = ujson.read(left.render())
    right("physicalConfigFingerprint") = ujson.Str("different-placement")
    Phase12Readiness.requireSameSemantics(left, right)
    Vector(
      "runId",
      "codeVersion",
      "hadoopManifestHash",
      "entityResolutionManifestHash",
      "logicalConfigFingerprint"
    ).foreach { field =>
      val changed = ujson.read(left.render()); changed(field) = ujson.Str("different")
      intercept[IllegalArgumentException](Phase12Readiness.requireSameSemantics(left, changed))
    }
    val changedWindow = ujson.read(left.render())
    changedWindow("windows")(0)("windowId") = ujson.Str("changed")
    intercept[IllegalArgumentException](Phase12Readiness.requireSameSemantics(left, changedWindow))
  }

  test("table inventory rejects missing, duplicate and redirected datasets") {
    assert(Phase12Readiness.tableInventory(metadata).size == 28)
    val omitted = metadata; omitted("tables").arr.remove(0)
    intercept[IllegalArgumentException](Phase12Readiness.tableInventory(omitted))
    val duplicate = metadata; duplicate("tables").arr += duplicate("tables")(0)
    intercept[IllegalArgumentException](Phase12Readiness.tableInventory(duplicate))
    val redirected = metadata; redirected("tables")(0)("path") = ujson.Str("../elsewhere")
    intercept[IllegalArgumentException](Phase12Readiness.tableInventory(redirected))
  }

  test("comparison recomputes counts and hashes instead of trusting metadata") {
    val left = frame(Vector("a", "b")); val right = frame(Vector("b", "a"))
    val expectedLeft = expected(left)
    assert(
      Phase12Readiness
        .compareTable("fixture", left, right, expectedLeft, expected(right))(
          "exactSchemaAndRowsMatch"
        )
        .bool
    )
    val corrupt = frame(Vector("a", "corrupt"))
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable("fixture", left, corrupt, expectedLeft, expectedLeft)
    )
    val falseCount = ujson.Obj("rowCount" -> "999", "contentHash" -> expectedLeft("contentHash"))
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable("fixture", left, right, falseCount, expected(right))
    )
  }

  test("comparison rejects schemas, duplicates and physical run-ID drift") {
    val left = frame(Vector("a", "b")); val duplicate = frame(Vector("a", "b", "b"))
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable("fixture", left, duplicate, expected(left), expected(duplicate))
    )
    val changedSchema = left.withColumnRenamed("value", "another")
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable(
        "fixture",
        left,
        changedSchema,
        expected(left),
        expected(changedSchema)
      )
    )
    val changedRun = left.withColumn("run_id", org.apache.spark.sql.functions.lit("run:changed"))
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable(
        "fixture",
        left,
        changedRun,
        expected(left),
        expected(changedRun)
      )
    )
  }

  test("nested provenance run IDs are never discarded") {
    val shape = new StructType()
      .add("value", StringType)
      .add("context", new StructType().add("runId", StringType))
    val left = spark.createDataFrame(Vector(Row("x", Row("run:left"))).asJava, shape)
    val right = spark.createDataFrame(Vector(Row("x", Row("run:right"))).asJava, shape)
    intercept[IllegalArgumentException](
      Phase12Readiness.compareTable("fixture", left, right, expected(left), expected(right))
    )
  }

  test("portable synthetic G1 preserves nine works, duplicate authors and literal edge weights") {
    val stream = getClass.getResourceAsStream("/phase12/g1-dblp.xml"); assert(stream != null)
    val xml =
      try new String(stream.readAllBytes(), UTF_8)
      finally stream.close()
    assert(xml.contains("Synthetic G1 readiness fixture"))
    val works =
      "(?s)<inproceedings key=\"conf/phase12-synthetic-g1/(w[0-9]+)\">(.*?)</inproceedings>".r
        .findAllMatchIn(xml)
        .map(m =>
          m.group(1) -> "<author>(.*?)</author>".r
            .findAllMatchIn(m.group(2))
            .map(_.group(1))
            .toVector
        )
        .toMap
    assert(
      works == Map(
        "w1" -> Vector("A", "B", "C"),
        "w2" -> Vector("A", "B"),
        "w9" -> Vector("A", "A", "B"),
        "w3" -> Vector("C", "D"),
        "w4" -> Vector("D", "E", "F"),
        "w5" -> Vector("E", "F"),
        "w6" -> Vector("F", "G"),
        "w7" -> Vector("H", "I"),
        "w8" -> Vector("J")
      )
    )
    val weights = works.values.toVector
      .flatMap(_.distinct.sorted.combinations(2).map(_.mkString("-")))
      .groupMapReduce(identity)(_ => 1)(_ + _)
    assert(
      weights == Map(
        "A-B" -> 3,
        "A-C" -> 1,
        "B-C" -> 1,
        "C-D" -> 1,
        "D-E" -> 1,
        "D-F" -> 1,
        "E-F" -> 2,
        "F-G" -> 1,
        "H-I" -> 1
      )
    )
    val empty = getClass.getResourceAsStream("/phase12/empty.jsonl"); assert(empty != null)
    try assert(empty.readAllBytes().isEmpty)
    finally empty.close()
  }

  test("CLI refuses unknown modes without writing evidence") {
    assert(Phase12Readiness.run(Array("unknown")).isLeft)
    assert(
      Phase12Readiness
        .run(Array("probe", root.toString, root.resolve("no.json").toString, "pretend"))
        .isLeft
    )
    assert(!Files.exists(root.resolve("no.json")))
  }
}
