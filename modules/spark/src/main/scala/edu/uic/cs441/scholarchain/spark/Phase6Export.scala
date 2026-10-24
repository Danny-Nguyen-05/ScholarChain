package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import org.apache.spark.sql.api.java.UDF1

final case class Phase6PublishedTable(
    name: String,
    path: String,
    rowCount: Long,
    contentHash: String,
    keys: Vector[String],
    partitions: Vector[String]
)

/** Job 11: deterministic logical hashes and a store-neutral, contract-backed Parquet handoff. */
object Phase6Export {
  val hashMethod = "sha256-fixed-256-shard-sorted-row-json-merkle-v1"

  /** Sort full row JSON in fixed content-addressed shards, hash each shard on executors, then fold
    * at most 256 shard digests on the driver. Physical partitions and file names are absent. Field
    * order is canonical (lexical names); explicit nulls are retained.
    */
  def logicalTableHash(table: DataFrame, keyColumns: Seq[String] = Seq.empty): String = {
    val logical = table.drop("run_id")
    val canonical = logical
      .select(
        to_json(struct(logical.columns.sorted.map(col)*), Map("ignoreNullFields" -> "false"))
          .as("row")
      )
      .withColumn("shard", substring(sha2(col("row"), 256), 1, 2))
    val shards = canonical
      .groupBy("shard")
      .agg(
        count("*").as("rows"),
        sha2(concat_ws("\n", sort_array(collect_list(col("row")))), 256).as("digest")
      )
      .orderBy("shard")
    val bounded = BoundedActions.capped(shards, 256)
    StableIds.sha256Hex(
      hashMethod + "\n" + bounded
        .map(r => s"${r.getString(0)}:${r.getLong(1)}:${r.getString(2)}")
        .mkString("\n")
    )
  }

  def contextIntegrity(
      canonical: Phase6CResult,
      lineage: SparkLineage,
      runId: String
  ): DataFrame = {
    val refs = ArrayType(Phase6FGJobs.sourceRefSchema)
    Phase6Context
      .add(canonical.integrity, lineage, runId, lit(null).cast(StringType))
      .withColumn("evidenceRefs", array().cast(refs))
  }

  def tables(
      canonical: Phase6CResult,
      analytics: Phase6DEResult,
      fg: Phase6FGResult,
      rejected: DataFrame,
      lineage: SparkLineage,
      runId: String
  ): Vector[(String, DataFrame, Vector[String], Boolean)] = {
    val nodes = Vector(
      "researcher" -> "RESEARCHER",
      "author_mention" -> "AUTHOR_MENTION",
      "work" -> "WORK",
      "venue" -> "VENUE",
      "institution" -> "INSTITUTION",
      "topic" -> "TOPIC"
    ).map { case (name, kind) =>
      (
        s"nodes/type=$name",
        canonical.graphNodes.filter(col("nodeClass") === kind),
        Vector("nodeId"),
        false
      )
    }
    val edges = Vector(
      "authored" -> "AUTHORED",
      "resolves_to" -> "RESOLVES_TO",
      "published_in" -> "PUBLISHED_IN",
      "affiliated_with" -> "AFFILIATED_WITH",
      "has_topic" -> "HAS_TOPIC"
    ).map { case (name, kind) =>
      (
        s"edges/type=$name",
        canonical.graphEdges.filter(col("edgeType") === kind),
        Vector("edgeId"),
        false
      )
    }
    nodes ++ edges ++ Vector(
      (
        "nodes/type=work_sources",
        Phase6Context
          .add(Phase6FGJobs.workSources(canonical), lineage, runId, lit(null).cast(StringType))
          .withColumn("schemaVersion", lit(SchemaVersions.sparkAnalytics)),
        Vector("workId"),
        false
      ),
      ("edges/type=coauthored_with", canonical.edges, Vector("edgeId"), false),
      ("edges/type=coauthored_with_support", canonical.support, Vector("edgeId", "workId"), false),
      ("metrics/type=researcher_collaboration", analytics.metrics, Vector("researcherId"), true),
      ("metrics/type=components", analytics.components, Vector("researcherId"), true),
      (
        "metrics/type=component_summaries",
        analytics.componentSummaries,
        Vector("componentId"),
        true
      ),
      ("metrics/type=communities", analytics.communities, Vector("researcherId"), true),
      (
        "metrics/type=community_summaries",
        analytics.communitySummaries,
        Vector("communityId"),
        true
      ),
      (
        "metrics/type=cross_community_edges",
        analytics.crossCommunityEdges,
        Vector("communityA", "communityB"),
        true
      ),
      ("metrics/type=bridges", analytics.bridges, Vector("researcherId"), true),
      ("metrics/type=kcore", analytics.coreness, Vector("researcherId"), true),
      (
        "metrics/type=temporal_changes",
        fg.temporalChanges,
        Vector("researcherId", "fromWindowId", "toWindowId"),
        true
      ),
      (
        "metrics/type=path_length_estimate",
        analytics.pathLengthEstimates,
        Vector("componentId"),
        true
      ),
      ("path-evidence", analytics.paths, Vector("pathEvidenceId"), true),
      ("semantic-summaries", fg.summaries, Vector("summaryId"), true),
      (
        "integrity/violations",
        contextIntegrity(canonical, lineage, runId),
        Vector("code", "entityId", "detail"),
        false
      ),
      (
        "integrity/rejects",
        Phase6CMain.publishRejects(rejected, runId, lineage),
        Vector("sourceKind", "sourcePath", "rawLine", "reason"),
        false
      )
    )
  }

  def publish(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      canonical: Phase6CResult,
      analytics: Phase6DEResult,
      fg: Phase6FGResult,
      rejected: DataFrame,
      lineage: SparkLineage,
      runId: String,
      metadata: ujson.Obj,
      root: Path
  ): Vector[Phase6PublishedTable] = {
    Files.createDirectories(root.resolve("plans"));
    Files.createDirectories(root.resolve("load-manifests"))
    val published = tables(canonical, analytics, fg, rejected, lineage, runId).map {
      case (name, raw, keys, windowed) =>
        validateTable(name, raw)
        val df = if (windowed) raw.withColumnRenamed("windowId", "window") else raw
        val existingKeys = keys.filter(df.columns.contains)
        val ordered = df.sortWithinPartitions(
          (existingKeys.map(col) :+ to_json(struct(df.columns.sorted.map(col)*)))*
        )
        val rowCount = BoundedActions.count(df)
        val hash = logicalTableHash(df, existingKeys)
        val partitionColumns = if (windowed) Vector("window", "run_id") else Vector("run_id")
        val out = ordered.withColumn("run_id", lit(runId))
        // Coauthorship is windowed; directory columns retain the exact approved names.
        val path = root.resolve(name)
        if (rowCount == 0L) out.write.mode("errorifexists").parquet(path.toString)
        else
          out
            .repartition((partitionColumns.map(col) ++ existingKeys.map(col))*)
            .sortWithinPartitions(
              (existingKeys.map(col) :+ to_json(struct(out.columns.sorted.map(col)*)))*
            )
            .write
            .mode("errorifexists")
            .partitionBy(partitionColumns*)
            .parquet(path.toString)
        Files.writeString(
          root.resolve("plans").resolve(name.replace('/', '_').replace('=', '_') + ".txt"),
          raw.queryExecution.explainString(
            org.apache.spark.sql.execution.ExplainMode.fromString("formatted")
          ) + "\n",
          UTF_8
        )
        Phase6PublishedTable(name, name, rowCount, hash, existingKeys, partitionColumns)
    }
    val manifests = Vector("neptune", "dynamodb", "s3vectors", "s3").map { target =>
      val selected = published.filter(t =>
        target match {
          case "neptune" =>
            (t.name.startsWith("nodes/") && t.name != "nodes/type=work_sources") || t.name
              .startsWith("edges/")
          case "dynamodb"  => t.name.startsWith("metrics/") || t.name == "path-evidence"
          case "s3vectors" => t.name == "semantic-summaries"
          case _           => true
        }
      )
      val proposals = selected.map { t =>
        val mapping = target match {
          case "neptune" =>
            Vector(
              NamedText("labelOrEdgeType", t.name.split("=").last.toUpperCase),
              NamedText("idProperty", t.keys.headOption.getOrElse("id")),
              NamedText(
                "yearlessEdgeMapping",
                "Phase 7 storage-engineer decision; no invented years"
              )
            )
          case "dynamodb" =>
            Vector(
              NamedText(
                "partitionKey",
                "researcherId or runId (dataset-dependent Phase 7 proposal)"
              ),
              NamedText("sortKey", "window#type#runId")
            )
          case "s3vectors" =>
            Vector(
              NamedText("documentId", "summaryId"),
              NamedText("text", "text"),
              NamedText(
                "metadataFields",
                "entityId,summaryType,context.windowId,context.runId,sourceReferences,abstractTextIds"
              )
            )
          case _ => Vector(NamedText("contentHashMethod", hashMethod))
        }
        LoadManifest(
          SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage),
          target,
          t.name,
          Vector(t.path),
          "parquet",
          t.rowCount,
          t.keys,
          t.partitions,
          t.contentHash,
          config.windows.map(_.windowId),
          "storage-engineer",
          mapping
        )
      }
      proposals.foreach(m =>
        SparkAnalyticsValidation
          .check(m)
          .fold(e => throw new IllegalArgumentException(e.toString), identity)
      )
      Files.writeString(
        root.resolve("load-manifests").resolve(target + ".json"),
        ujson.Arr.from(proposals.map(m => ujson.read(CoreJson.compact(m)))).render() + "\n",
        UTF_8
      )
      target -> proposals.size
    }
    Phase7NeptuneExport.publish(
      root,
      canonical.graphNodes,
      canonical.graphEdges,
      canonical.edges,
      canonical.support,
      published,
      runId
    )
    val counts = canonical.counters.unionByName(analytics.counters)
    val rejectCount = BoundedActions.count(rejected)
    val extras = Vector(
      "malformedJsonLines" -> rejectCount,
      "temporalChanges" -> BoundedActions.count(fg.temporalChanges),
      "semanticSummaries" -> BoundedActions.count(fg.summaries)
    ).map { case (name, value) =>
      ujson.read(
        CoreJson.compact(
          SparkCounter(
            SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage),
            name,
            value,
            None
          )
        )
      )
    }
    val counterRows = BoundedActions.capped(counts.orderBy("name"), 10000)
    val counters = ujson.Arr.from(counterRows.map(r => ujson.read(r.json)) ++ extras)
    Files.writeString(root.resolve("counters.json"), counters.render() + "\n", UTF_8)
    metadata("contentHashMethod") = hashMethod
    metadata("sourceProjection") = ujson.Obj(
      "table" -> "nodes/type=work_sources",
      "record" -> "SparkWorkSourceProjection.v1",
      "fields" -> "normalized source work columns, optional abstractTextRef, SparkRecordContext; not a GraphNode",
      "schemaVersion" -> SchemaVersions.sparkAnalytics
    )
    metadata("tables") = ujson.Arr.from(
      published.map(t =>
        ujson.Obj(
          "dataset" -> t.name,
          "path" -> t.path,
          "rowCount" -> t.rowCount,
          "contentHash" -> t.contentHash,
          "keys" -> ujson.Arr.from(t.keys),
          "partitions" -> ujson.Arr.from(t.partitions)
        )
      )
    )
    published
  }

  /** Validate serialized executor-side records against the same core contracts used by consumers.
    */
  def validateTable(name: String, table: DataFrame): Unit = {
    val validate = new UDF1[String, java.lang.Boolean] {
      def call(json: String): java.lang.Boolean = {
        def spark[T: upickle.default.ReadWriter](check: T => Either[ConfigError, T]): Boolean =
          CoreJson.parse[T](json).exists(v => check(v).isRight)
        def domain[T: upickle.default.ReadWriter](
            check: T => Either[Vector[DomainViolation], T]
        ): Boolean = CoreJson.parse[T](json).exists(v => check(v).isRight)
        val valid = name match {
          case "nodes/type=work_sources" =>
            val value = ujson.read(json);
            value("workId").str.nonEmpty && value("context")("runId").str.nonEmpty
          case n if n.startsWith("nodes/") => domain[GraphNode](DomainValidation.check)
          case "edges/type=coauthored_with" =>
            spark[SparkCoauthorEdge](SparkAnalyticsValidation.check)
          case "edges/type=coauthored_with_support" =>
            spark[CoauthorEdgeSupport](SparkAnalyticsValidation.check)
          case n if n.startsWith("edges/") => domain[GraphEdge](DomainValidation.check)
          case "metrics/type=researcher_collaboration" | "metrics/type=kcore" =>
            spark[ResearcherMetricsDetail](SparkAnalyticsValidation.check)
          case "metrics/type=components" =>
            spark[ComponentMembership](SparkAnalyticsValidation.check)
          case "metrics/type=component_summaries" =>
            spark[ComponentSummary](SparkAnalyticsValidation.check)
          case "metrics/type=communities" =>
            spark[CommunityMembership](SparkAnalyticsValidation.check)
          case "metrics/type=community_summaries" =>
            spark[CommunitySummary](SparkAnalyticsValidation.check)
          case "metrics/type=cross_community_edges" =>
            spark[CrossCommunityEdge](SparkAnalyticsValidation.check)
          case "metrics/type=bridges" =>
            spark[ResearcherBridgeMetrics](SparkAnalyticsValidation.check)
          case "metrics/type=temporal_changes" =>
            spark[TemporalChange](SparkAnalyticsValidation.check)
          case "metrics/type=path_length_estimate" =>
            spark[PathLengthEstimate](SparkAnalyticsValidation.check)
          case "path-evidence"        => spark[PathEvidence](SparkAnalyticsValidation.check)
          case "semantic-summaries"   => spark[SemanticSummary](SparkAnalyticsValidation.check)
          case "integrity/violations" => spark[IntegrityViolation](SparkAnalyticsValidation.check)
          case "integrity/rejects" =>
            true // Explicit reader reject schema, raw payload cannot be a domain record.
          case _ => false
        }
        java.lang.Boolean.valueOf(valid)
      }
    }
    val valid = udf(validate, BooleanType)
    require(
      !BoundedActions.exists(
        table.filter(
          !valid(to_json(struct(table.columns.map(col)*), Map("ignoreNullFields" -> "false")))
        )
      ),
      s"invalid core record in $name"
    )
  }

}
