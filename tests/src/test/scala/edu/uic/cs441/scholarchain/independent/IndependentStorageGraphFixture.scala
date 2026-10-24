package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{
  Phase6Context,
  Phase6Export,
  Phase6PublishedTable,
  Phase7NeptuneExport
}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions.{col, lit}
import org.apache.spark.sql.types.*

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Independently specified three-node, one-edge, yearless graph. All source claims are synthetic.
  */
object IndependentStorageGraphFixture {
  import IndependentStorageFixtures.*
  val work = "work:dblp:independent/synthetic/storage"
  // Independently SHA-256 precomputed from the documented core ID input, not from a job output.
  val edge = "spark-coauthor-edge:1bb28e3d6ee73bdd1d603f6ffa42a25777e9be76ee4e9b6745e652311c4b05e7"
  val expectedNodes = Set(researcherId, secondResearcherId, work)
  val expectedEdges = Set(edge)

  def publish(
      spark: SparkSession,
      root: Path,
      missingEndpoint: Boolean = false,
      missingSupport: Boolean = false
  ): Path = {
    val named = ArrayType(new StructType().add("name", StringType).add("value", StringType))
    val provenanceSchema = new StructType()
      .add("schemaVersion", StringType)
      .add("source", StringType)
      .add("sourceRecordId", StringType)
      .add("sourceUri", StringType)
      .add("datasetSnapshot", StringType)
      .add("retrievalDate", StringType)
      .add("licenseEvidenceUri", StringType)
      .add("runId", StringType)
      .add("uncertaintyNotes", ArrayType(StringType))
    val p = Row(
      SchemaVersions.domain,
      "DBLP",
      provenance.sourceRecordId,
      null,
      provenance.datasetSnapshot,
      null,
      null,
      runId,
      provenance.uncertaintyNotes.asJava
    )
    def c(window: String): Row = Row(
      SchemaVersions.sparkAnalytics,
      runId,
      window,
      Row(
        context.lineage.hadoopRunId,
        context.lineage.hadoopSnapshot,
        context.lineage.entityResolutionRunId,
        context.lineage.entityResolutionPolicyVersion,
        context.lineage.entityResolutionPolicyHash,
        context.lineage.sourceWorkIds.asJava,
        context.lineage.sourceMentionIds.asJava
      )
    )
    def frame(schema: StructType, rows: Vector[Row]): DataFrame =
      spark.createDataFrame(rows.asJava, schema)
    val nodes = frame(
      new StructType()
        .add("nodeId", StringType)
        .add("schemaVersion", StringType)
        .add("nodeClass", StringType)
        .add("label", StringType)
        .add("properties", named)
        .add("provenance", provenanceSchema)
        .add("context", Phase6Context.schema),
      Vector(
        (researcherId, "RESEARCHER", "Synthetic A, \"quoted\"\r\nsecond line"),
        (secondResearcherId, "RESEARCHER", "Synthetic B"),
        (work, "WORK", "Synthetic work")
      )
        .map((id, kind, label) =>
          Row(id, SchemaVersions.domain, kind, label, Vector.empty[Row].asJava, p, c(null))
        )
    )
    val graphEdges = frame(
      new StructType()
        .add("edgeId", StringType)
        .add("fromId", StringType)
        .add("toId", StringType)
        .add("edgeType", StringType)
        .add("schemaVersion", StringType)
        .add("policyVersion", StringType)
        .add("sourceEvidence", new StructType().add("workId", StringType))
        .add("properties", named)
        .add("provenance", provenanceSchema)
        .add("context", Phase6Context.schema),
      Vector.empty
    )
    val coauthors = frame(
      new StructType()
        .add("edgeId", StringType)
        .add("researcherA", StringType)
        .add("researcherB", StringType)
        .add("policyVersion", StringType)
        .add("jointPublicationCount", LongType)
        .add("firstCollaborationYear", IntegerType)
        .add("lastCollaborationYear", IntegerType)
        .add("representativeWorkIds", ArrayType(StringType))
        .add("windowStartYear", IntegerType)
        .add("windowEndYear", IntegerType)
        .add("context", Phase6Context.schema),
      Vector(
        Row(
          edge,
          researcherId,
          secondResearcherId,
          policyVersion,
          1L,
          null,
          null,
          Vector(work).asJava,
          null,
          null,
          c("all-years")
        )
      )
    )
    val support = frame(
      new StructType()
        .add("edgeId", StringType)
        .add("workId", StringType)
        .add("year", IntegerType)
        .add("context", Phase6Context.schema),
      Vector(Row(edge, work, null, c("all-years")))
    )
    val researchers = nodes.filter(col("nodeClass") === "RESEARCHER")
    val sourceResearchers =
      if (missingEndpoint) researchers.filter(col("nodeId") =!= secondResearcherId) else researchers
    val sourceSupport = if (missingSupport) support.limit(0) else support
    // Negative variants bind honest hashes/counts for malformed authoritative source tables;
    // the independent validator must reject their endpoints/support before any upload.
    val sources = Vector(
      ("nodes/type=researcher", sourceResearchers, Vector("nodeId")),
      ("nodes/type=work", nodes.filter(col("nodeClass") === "WORK"), Vector("nodeId")),
      ("edges/type=coauthored_with", coauthors, Vector("edgeId")),
      (Phase7NeptuneExport.supportPath, sourceSupport, Vector("edgeId", "workId"))
    )
    val published = sources.map { (name, data, keys) =>
      data.withColumn("run_id", lit(runId)).write.parquet(root.resolve(name).toString)
      val count = if (name == "nodes/type=researcher") { if (missingEndpoint) 1L else 2L }
      else if (name == Phase7NeptuneExport.supportPath && missingSupport) 0L
      else 1L
      Phase6PublishedTable(
        name,
        name,
        count,
        Phase6Export.logicalTableHash(data),
        keys,
        Vector("run_id")
      )
    }
    Phase7NeptuneExport.publish(root, nodes, graphEdges, coauthors, support, published, runId)
    val run = RunManifest(
      runId,
      SchemaVersions.domain,
      "independent-synthetic-storage",
      Vector(DatasetSnapshotRef(SourceType.Dblp, provenance.datasetSnapshot, None)),
      SchemaVersions.sparkAnalyticsConfig,
      "a" * 64,
      provenance
    )
    val runJson = CoreJson.compact(run) + "\n"
    val metadata = ujson
      .Obj(
        "runId" -> runId,
        "hadoopRunId" -> context.lineage.hadoopRunId,
        "entityResolutionRunId" -> context.lineage.entityResolutionRunId,
        "entityResolutionPolicyVersion" -> context.lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> context.lineage.entityResolutionPolicyHash,
        "tables" -> ujson.Arr.from(
          published.map(t =>
            ujson.Obj(
              "dataset" -> t.name,
              "path" -> t.path,
              "rowCount" -> t.rowCount,
              "contentHash" -> t.contentHash
            )
          )
        )
      )
      .render() + "\n"
    Files.writeString(root.resolve("run-manifest.json"), runJson, UTF_8)
    Files.writeString(root.resolve("run-metadata.json"), metadata, UTF_8)
    Files.writeString(root.resolve("counters.json"), "[]", UTF_8)
    Files.writeString(
      root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
      StableIds.sha256Hex(runJson + "\n" + metadata) + "\n",
      UTF_8
    )
    val manifests = published.map(t =>
      LoadManifest(
        context.copy(windowId = None),
        "s3",
        t.name,
        Vector(t.path),
        "parquet",
        t.rowCount,
        t.keys,
        t.partitions,
        t.contentHash,
        Vector("all-years"),
        "storage-engineer",
        Vector.empty
      )
    )
    Files.writeString(root.resolve("load-manifests/s3.json"), CoreJson.compact(manifests), UTF_8)
    Files.writeString(root.resolve("load-manifests/dynamodb.json"), "[]", UTF_8)
    root
  }
}
