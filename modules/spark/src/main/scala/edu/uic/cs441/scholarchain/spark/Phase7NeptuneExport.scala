package edu.uic.cs441.scholarchain.spark

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.api.java.UDF1
import org.apache.spark.sql.catalyst.InternalRow
import org.apache.spark.sql.execution.datasources.{OutputWriter, OutputWriterFactory}
import org.apache.spark.sql.execution.datasources.text.TextFileFormat
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.{StringType, StructType}
import org.apache.hadoop.mapreduce.{Job, TaskAttemptContext}
import org.apache.spark.unsafe.types.UTF8String
import scala.jdk.CollectionConverters.*

/** Additional openCypher handoff. The original Parquet datasets and IDs remain authoritative. */
object Phase7NeptuneExport {
  val loaderPrefix = "neptune-opencypher-csv/data"
  val sidecarPath = "load-manifests/neptune-opencypher-csv.json"
  val supportPath = "edges/type=coauthored_with_support"

  /** Storage's `NeptuneLoaderConfig.maxUploadBytes` default; each uploaded edge part must fit. */
  val defaultMaxPartBytes: Long = 16L * 1024 * 1024

  /** Half the cap leaves headroom for hash-partition skew. */
  val defaultTargetPartBytes: Long = 8L * 1024 * 1024
  private val jsonOptions = Map("ignoreNullFields" -> "false")

  private def csvCell(value: String): String =
    if (value.length == 0 || value.exists(c => c == ',' || c == '"' || c == '\r' || c == '\n'))
      "\"" + value.replace("\"", "\"\"") + "\""
    else value

  private def csvRows(data: DataFrame): DataFrame = {
    val encode = udf(
      new UDF1[Row, String] {
        def call(row: Row): String = row.toSeq
          .map {
            case null  => ""
            case value => csvCell(value.toString)
          }
          .mkString(",")
      },
      StringType
    )
    data.select(encode(struct(data.columns.map(col)*)).as("value"))
  }

  private def requireEmpty(rows: DataFrame, message: String): Unit =
    require(!BoundedActions.exists(rows), message)

  private def unique(rows: DataFrame, keys: String*): Unit =
    requireEmpty(
      rows.groupBy(keys.map(col)*).agg(count(lit(1)).as("count")).filter(col("count") > 1),
      s"duplicate Neptune source key: ${keys.mkString(",")}"
    )

  /** All validation is executor-side joins/aggregations followed by a one-row existence action. */
  def frames(
      nodes: DataFrame,
      graphEdges: DataFrame,
      coauthors: DataFrame,
      support: DataFrame
  ): Vector[(String, DataFrame)] = {
    unique(nodes, "nodeId")
    unique(graphEdges.select("edgeId").unionByName(coauthors.select("edgeId")), "edgeId")
    unique(support, "edgeId", "workId")
    val nodeIds = nodes.select(col("nodeId").as("id"))
    val endpoints = graphEdges
      .select(col("fromId").as("id"))
      .unionByName(graphEdges.select(col("toId").as("id")))
      .unionByName(coauthors.select(col("researcherA").as("id")))
      .unionByName(coauthors.select(col("researcherB").as("id")))
    requireEmpty(endpoints.join(nodeIds, Seq("id"), "left_anti"), "Neptune edge endpoint missing")
    requireEmpty(
      support.join(coauthors.select("edgeId"), Seq("edgeId"), "left_anti"),
      "orphan coauthor support"
    )
    val works = nodes.filter(col("nodeClass") === "WORK").select("nodeId")
    requireEmpty(
      support.join(works, col("workId") === col("nodeId"), "left_anti"),
      "coauthor support work missing"
    )
    requireEmpty(
      coauthors
        .join(support.groupBy("edgeId").agg(count(lit(1)).as("count")), Seq("edgeId"), "left")
        .filter(col("count").isNull || col("count") =!= col("jointPublicationCount")),
      "coauthor support count differs from jointPublicationCount"
    )

    val nodeCsv = nodes.select(
      col("nodeId").as(":ID"),
      col("nodeClass").as(":LABEL"),
      col("label").as("label:String"),
      col("schemaVersion").as("schemaVersion:String"),
      to_json(col("properties"), jsonOptions).as("propertiesJson:String"),
      to_json(col("provenance"), jsonOptions).as("provenanceJson:String"),
      to_json(col("context"), jsonOptions).as("contextJson:String")
    )
    val edgeCsv = graphEdges.select(
      col("edgeId").as(":ID"),
      col("fromId").as(":START_ID"),
      col("toId").as(":END_ID"),
      col("edgeType").as(":TYPE"),
      col("schemaVersion").as("schemaVersion:String"),
      col("policyVersion").as("policyVersion:String"),
      to_json(col("sourceEvidence"), jsonOptions).as("sourceEvidenceJson:String"),
      to_json(col("properties"), jsonOptions).as("propertiesJson:String"),
      to_json(col("provenance"), jsonOptions).as("provenanceJson:String"),
      to_json(col("context"), jsonOptions).as("contextJson:String")
    )
    val coauthorCsv = coauthors.select(
      col("edgeId").as(":ID"),
      col("researcherA").as(":START_ID"),
      col("researcherB").as(":END_ID"),
      lit("COAUTHORED_WITH").as(":TYPE"),
      col("policyVersion").as("policyVersion:String"),
      col("jointPublicationCount").as("jointPublicationCount:Long"),
      col("firstCollaborationYear").as("firstCollaborationYear:Int"),
      col("lastCollaborationYear").as("lastCollaborationYear:Int"),
      col("windowStartYear").as("windowStartYear:Int"),
      col("windowEndYear").as("windowEndYear:Int"),
      col("context.windowId").as("windowId:String"),
      to_json(col("representativeWorkIds"), jsonOptions).as("representativeWorkIdsJson:String"),
      lit(supportPath).as("evidenceTable:String"),
      col("edgeId").as("evidenceEdgeId:String"),
      to_json(col("context"), jsonOptions).as("contextJson:String")
    )
    Vector("nodes" -> nodeCsv, "graph-edges" -> edgeCsv, "coauthor-edges" -> coauthorCsv)
  }

  def publish(
      root: Path,
      nodes: DataFrame,
      graphEdges: DataFrame,
      coauthors: DataFrame,
      support: DataFrame,
      published: Vector[Phase6PublishedTable],
      runId: String,
      targetPartBytes: Long = defaultTargetPartBytes,
      maxPartBytes: Long = defaultMaxPartBytes
  ): Unit = {
    require(
      targetPartBytes > 0 && targetPartBytes <= maxPartBytes,
      "positive target part size not above the maximum required"
    )
    val outputs = frames(nodes, graphEdges, coauthors, support)
    val datasets = outputs.map { case (kind, data) =>
      val path = s"$loaderPrefix/$kind"
      // The storage loader uploads each edge part as one object bounded at 16 MiB, so the part
      // count is derived from the encoded size (including the CRLF row separator) and not from
      // the shuffle width or AQE coalescing. An explicit repartition count is never coalesced.
      val encodedBytes = BoundedActions.scalarLong(
        csvRows(data).agg(coalesce(sum(octet_length(col("value")) + 2L), lit(0L)).as("bytes")),
        "bytes"
      )
      val partCount = math.max(1L, (encodedBytes + targetPartBytes - 1) / targetPartBytes)
      require(partCount <= Int.MaxValue, "CSV part count overflow")
      // Encoding is executor-side and preserves embedded CR/LF verbatim. Spark's CSV writer
      // normalizes an embedded LF to CRLF while retaining a preceding CR (yielding CRCRLF).
      // Text output plus a per-partition header avoids that transformation.
      csvRows(data.repartition(partCount.toInt, col(":ID")).sortWithinPartitions(col(":ID"))).write
        .mode("errorifexists")
        .format(classOf[Phase7CsvFileFormat].getName)
        .option("csvheader", data.columns.map(csvCell).mkString(","))
        .option("lineSep", "\r\n")
        .save(root.resolve(path).toString)
      // Neptune consumes every file under source. Remove only this writer's generated metadata;
      // neither success markers nor local Hadoop checksum files belong in a CSV loader prefix.
      val files = Files.list(root.resolve(path))
      try
        files
          .iterator()
          .asScala
          .filter(p =>
            p.getFileName.toString == "_SUCCESS" ||
              p.getFileName.toString.endsWith(".crc")
          )
          .foreach(Files.delete)
      finally files.close()
      val parts = Files.list(root.resolve(path))
      try
        parts.iterator().asScala.foreach { p =>
          val size = Files.size(p)
          require(
            size <= maxPartBytes,
            s"Neptune CSV part ${p.getFileName} has $size bytes > $maxPartBytes"
          )
        }
      finally parts.close()
      ujson.Obj(
        "path" -> path,
        "rowCount" -> BoundedActions.count(data),
        "contentHash" -> Phase6Export.logicalTableHash(data),
        "columns" -> ujson.Arr.from(data.columns.toVector)
      )
    }
    val sources = published.filter(t =>
      (t.name.startsWith("nodes/") && t.name != "nodes/type=work_sources") || t.name.startsWith(
        "edges/"
      )
    )
    val sidecar = ujson.Obj(
      "schemaVersion" -> "scholarchain.neptune-opencypher-export.v1",
      "runId" -> runId,
      "format" -> "opencypher",
      "userProvidedEdgeIds" -> true,
      "loaderPrefix" -> loaderPrefix,
      "contentHashMethod" -> Phase6Export.hashMethod,
      "datasets" -> ujson.Arr.from(datasets),
      "sourceTables" -> ujson.Arr.from(
        sources.map(t =>
          ujson.Obj(
            "path" -> t.path,
            "rowCount" -> t.rowCount,
            "contentHash" -> t.contentHash,
            "keyColumns" -> ujson.Arr.from(t.keys)
          )
        )
      ),
      "supportTable" -> ujson.Obj(
        "path" -> supportPath,
        "keyColumns" -> ujson.Arr("edgeId", "workId"),
        "edgeLookup" -> "evidenceTable + evidenceEdgeId; all matching support rows",
        "location" -> "ordinary S3 dataset relative to export root; outside loaderPrefix"
      ),
      "mapping" -> ujson.Obj(
        "nodeId" -> "nodeId -> :ID",
        "nodeLabel" -> "nodeClass -> :LABEL",
        "edgeId" -> "edgeId -> :ID",
        "endpoints" -> "fromId/toId or researcherA/researcherB",
        "properties" -> "NamedText properties as propertiesJson; coauthor numeric fields typed",
        "provenance" -> "provenanceJson and/or contextJson retain source provenance and lineage",
        "unknownYears" -> "empty numeric cells; no invented years",
        "support" -> "ordinary support table; no synthetic SUPPORTED_BY relationships"
      )
    )
    Files.createDirectories(root.resolve("load-manifests"))
    Files.writeString(root.resolve(sidecarPath), sidecar.render() + "\n", UTF_8)
  }
}

/** Spark's UTF-8 text writer with exactly one CSV header per physical output file. */
class Phase7CsvFileFormat extends TextFileFormat {
  override def shortName(): String = "scholarchain-neptune-csv"

  override def prepareWrite(
      spark: SparkSession,
      job: Job,
      options: Map[String, String],
      dataSchema: StructType
  ): OutputWriterFactory = {
    val text = super.prepareWrite(spark, job, options, dataSchema)
    val header = options("csvheader")
    new OutputWriterFactory {
      def getFileExtension(context: TaskAttemptContext): String = ".csv"
      def newInstance(
          path: String,
          schema: StructType,
          context: TaskAttemptContext
      ): OutputWriter = {
        val writer = text.newInstance(path, schema, context)
        writer.write(InternalRow(UTF8String.fromString(header)))
        writer
      }
    }
  }
}
