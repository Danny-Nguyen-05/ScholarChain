package edu.uic.cs441.scholarchain.spark

import com.univocity.parsers.csv.{CsvParser, CsvParserSettings}
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class Phase7NeptuneExportSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  private var root: Path = _
  private val runId = "run:00112233-4455-4677-8899-aabbccddeeff"
  private val a = "researcher:dblp:5f3ebef46438fe4e2ea69c2c4bc567b53dbb1cfcf8a0e80dd1cfe797b801a589"
  private val b = "researcher:dblp:c30b1a101927dc74d54cb42f5d54ccb9d98168c0372de03105e7ac26ae144e8d"
  private val w1 = "work:dblp:conf/example/w1"
  private val w2 = "work:dblp:conf/example/w2"
  private val edgeId =
    "spark-coauthor-edge:6b0408eec32196b6e292d2fc0eaacd44baf6713bf625d37e08b54128b3c50099"
  private val graphId =
    "graph-edge:63a2d36298614af15453508d8dee19cb9fdd8e8e647cb01bc0d85fb0b10f00a1"
  private val label = "Alpha, \"β\"\r\nSecond line"
  private val named = ArrayType(new StructType().add("name", StringType).add("value", StringType))
  private val provenance = new StructType().add("runId", StringType)
  private val context = new StructType().add("runId", StringType).add("windowId", StringType)
  override protected def beforeAll(): Unit = {
    root = Files.createTempDirectory("scholarchain-neptune-csv-")
    spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Phase7 Neptune CSV fixture")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
  }
  override protected def afterAll(): Unit = {
    try { if (spark != null) spark.stop() }
    finally {
      if (root != null) {
        val walk = Files.walk(root)
        try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
        finally walk.close()
      }
      super.afterAll()
    }
  }
  private def frame(schema: StructType, rows: Vector[Row]): DataFrame =
    spark.createDataFrame(rows.asJava, schema)
  private def ctx = Row(runId, "all-years")
  private lazy val nodes = frame(
    new StructType()
      .add("nodeId", StringType)
      .add("nodeClass", StringType)
      .add("label", StringType)
      .add("schemaVersion", StringType)
      .add("properties", named)
      .add("provenance", provenance)
      .add("context", context),
    Vector((a, "RESEARCHER", label), (b, "RESEARCHER", "B"), (w1, "WORK", "W1"), (w2, "WORK", "W2"))
      .map { case (id, kind, text) =>
        Row(
          id,
          kind,
          text,
          "scholarchain.domain.v1",
          Vector(Row("source", "fixture")),
          Row(runId),
          ctx
        )
      }
  )
  private lazy val graphEdges = frame(
    new StructType()
      .add("edgeId", StringType)
      .add("fromId", StringType)
      .add("toId", StringType)
      .add("edgeType", StringType)
      .add("schemaVersion", StringType)
      .add("policyVersion", StringType)
      .add("sourceEvidence", new StructType().add("workId", StringType))
      .add("properties", named)
      .add("provenance", provenance)
      .add("context", context),
    Vector(
      Row(
        graphId,
        a,
        w1,
        "AUTHORED",
        "scholarchain.domain.v1",
        "graph-v1",
        Row(w1),
        Vector.empty[Row],
        Row(runId),
        ctx
      )
    )
  )
  private lazy val coauthors = frame(
    new StructType()
      .add("edgeId", StringType)
      .add("researcherA", StringType)
      .add("researcherB", StringType)
      .add("policyVersion", StringType)
      .add("jointPublicationCount", LongType)
      .add("firstCollaborationYear", IntegerType)
      .add("lastCollaborationYear", IntegerType)
      .add("windowStartYear", IntegerType)
      .add("windowEndYear", IntegerType)
      .add("representativeWorkIds", ArrayType(StringType))
      .add("context", context),
    Vector(Row(edgeId, a, b, "graph-v1", 2L, null, null, null, null, Vector(w1, w2), ctx))
  )
  private lazy val support = frame(
    new StructType()
      .add("edgeId", StringType)
      .add("workId", StringType)
      .add("year", IntegerType)
      .add("context", context),
    Vector(Row(edgeId, w1, null, ctx), Row(edgeId, w2, null, ctx))
  )

  test(
    "CSV preserves exact node and edge ID sets, RFC4180 text, yearless values and support provenance"
  ) {
    val out = root.resolve("export")
    val sources = Vector(
      Phase6PublishedTable(
        Phase7NeptuneExport.supportPath,
        Phase7NeptuneExport.supportPath,
        2L,
        "a" * 64,
        Vector("edgeId", "workId"),
        Vector("run_id")
      )
    )
    Phase7NeptuneExport.publish(out, nodes, graphEdges, coauthors, support, sources, runId)
    def read(kind: String): Vector[Map[String, String]] = {
      val files = Files.list(out.resolve(s"${Phase7NeptuneExport.loaderPrefix}/$kind"))
      val csv =
        try files.iterator().asScala.filter(_.toString.endsWith(".csv")).toVector
        finally files.close()
      csv.flatMap { file =>
        val settings = new CsvParserSettings()
        settings.getFormat.setLineSeparator("\r\n")
        settings.setHeaderExtractionEnabled(true)
        settings.setNormalizeLineEndingsWithinQuotes(false)
        val reader = Files.newBufferedReader(file, UTF_8)
        try
          new CsvParser(settings)
            .parseAllRecords(reader)
            .asScala
            .toVector
            .map(_.toFieldMap().asScala.toMap)
        finally reader.close()
      }
    }
    val nodeRows = read("nodes")
    val nodeIds = nodeRows.map(_(":ID")).toSet
    assert(nodeIds == Set(a, b, w1, w2))
    assert(Set(a, b, w1, w2).diff(nodeIds).isEmpty)
    assert(nodeRows.find(_(":ID") == a).get("label:String") == label)
    val relationships = read("graph-edges") ++ read("coauthor-edges")
    val edgeIds = relationships.map(_(":ID")).toSet
    assert(edgeIds == Set(graphId, edgeId))
    assert(Set(graphId, edgeId).diff(edgeIds).isEmpty)
    val coauthor = relationships.find(_(":ID") == edgeId).get
    assert(coauthor(":START_ID") == a)
    assert(coauthor(":END_ID") == b)
    assert(coauthor(":TYPE") == "COAUTHORED_WITH")
    Vector(
      "firstCollaborationYear:Int",
      "lastCollaborationYear:Int",
      "windowStartYear:Int",
      "windowEndYear:Int"
    ).foreach(k => assert(coauthor(k) == null))
    assert(coauthor("jointPublicationCount:Long") == "2")
    assert(coauthor("evidenceTable:String") == "edges/type=coauthored_with_support")
    assert(coauthor("evidenceEdgeId:String") == edgeId)
    assert(ujson.read(coauthor("contextJson:String"))("runId").str == runId)
    val sidecar = ujson.read(Files.readString(out.resolve(Phase7NeptuneExport.sidecarPath), UTF_8))
    assert(
      sidecar("supportTable")("keyColumns").arr.map(_.str).toVector == Vector("edgeId", "workId")
    )
    assert(sidecar("sourceTables")(0)("rowCount").str == "2")
    val walk = Files.walk(out.resolve(Phase7NeptuneExport.loaderPrefix))
    val files =
      try walk.iterator().asScala.filter(Files.isRegularFile(_)).toVector
      finally walk.close()
    assert(files.nonEmpty && files.forall(_.toString.endsWith(".csv")))
    val nodeBytes = files
      .filter(_.getParent.getFileName.toString == "nodes")
      .map(p => Files.readString(p, UTF_8))
      .mkString
    assert(nodeBytes.contains("\"Alpha, \"\"β\"\"\r\nSecond line\""))
    assert(nodeBytes.contains("\r\n"))
  }

  test("empty datasets retain a CSV header in every loader file") {
    val out = root.resolve("empty-export")
    Phase7NeptuneExport.publish(
      out,
      nodes.limit(0),
      graphEdges.limit(0),
      coauthors.limit(0),
      support.limit(0),
      Vector.empty,
      runId
    )
    val walk = Files.walk(out.resolve(Phase7NeptuneExport.loaderPrefix))
    val files =
      try walk.iterator().asScala.filter(Files.isRegularFile(_)).toVector
      finally walk.close()
    assert(files.nonEmpty && files.forall(_.toString.endsWith(".csv")))
    assert(
      files.map(_.getParent.getFileName.toString).toSet ==
        Set("nodes", "graph-edges", "coauthor-edges")
    )
    files.foreach { file =>
      val text = Files.readString(file, UTF_8)
      assert(text.startsWith(":ID,") && text.endsWith("\r\n"))
      assert(text.count(_ == '\n') == 1)
    }
  }

  test("missing endpoints or support works fail before publication") {
    val missingEndpoint = intercept[IllegalArgumentException] {
      Phase7NeptuneExport.frames(nodes.filter(col("nodeId") =!= b), graphEdges, coauthors, support)
    }
    assert(missingEndpoint.getMessage.contains("endpoint missing"))
    val missingWork = intercept[IllegalArgumentException] {
      Phase7NeptuneExport.frames(nodes.filter(col("nodeId") =!= w2), graphEdges, coauthors, support)
    }
    assert(missingWork.getMessage.contains("support work missing"))
  }

  test(
    "support composite keys cannot duplicate or lose evidence, and orphan evidence is rejected"
  ) {
    val duplicate = intercept[IllegalArgumentException] {
      Phase7NeptuneExport.frames(nodes, graphEdges, coauthors, support.unionByName(support))
    }
    assert(duplicate.getMessage.contains("edgeId,workId"))
    val missing = intercept[IllegalArgumentException] {
      Phase7NeptuneExport.frames(nodes, graphEdges, coauthors, support.limit(0))
    }
    assert(missing.getMessage.contains("support count"))
    val orphan = intercept[IllegalArgumentException] {
      Phase7NeptuneExport.frames(
        nodes,
        graphEdges,
        coauthors,
        support.withColumn("edgeId", lit("spark-coauthor-edge:" + "b" * 64))
      )
    }
    assert(orphan.getMessage.contains("orphan coauthor support"))
  }
}
