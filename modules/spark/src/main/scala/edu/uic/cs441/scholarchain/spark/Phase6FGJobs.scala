package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import org.apache.spark.sql.{DataFrame, SparkSession, RowFactory}
import scala.jdk.CollectionConverters.*
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.types.*
import org.apache.spark.sql.api.java.UDF5

final case class Phase6FGResult(temporalChanges: DataFrame, summaries: DataFrame)

/** Jobs 9–10. All comparisons and source-reference construction execute on distributed rows. */
object Phase6FGJobs {
  def build(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      canonical: Phase6CResult,
      analytics: Phase6DEResult,
      lineage: SparkLineage,
      runId: String
  ): Phase6FGResult =
    Phase6FGResult(
      temporalFromTables(
        config,
        analytics.metrics,
        analytics.componentSummaries,
        analytics.communities,
        analytics.bridges,
        lineage,
        runId
      ),
      semanticSummaries(spark, config, canonical, analytics, lineage, runId)
    )

  def temporalFromTables(
      config: SparkAnalyticsConfig,
      metrics: DataFrame,
      componentSummaries: DataFrame,
      communities: DataFrame,
      bridges: DataFrame,
      lineage: SparkLineage,
      runId: String
  ): DataFrame = {
    val enriched = metrics
      .drop("communityId")
      .join(
        componentSummaries.select("windowId", "componentId", "size", "isLargest"),
        Seq("windowId", "componentId")
      )
      .join(
        communities.select("windowId", "researcherId", "communityId"),
        Seq("windowId", "researcherId")
      )
      .join(bridges.drop("context", "policyVersion"), Seq("windowId", "researcherId"))
    val fields = Seq(
      "distinctCoauthorCount",
      "averageCoauthorsPerPaper",
      "maximumCoauthorsOnOnePaper",
      "size",
      "crossCommunityDegree",
      "crossCommunityWeight",
      "communitiesConnected",
      "participationCoefficient"
    )
    val deltaNames = Seq(
      "deltaDistinctCoauthors",
      "deltaAverageCoauthorsPerPaper",
      "deltaMaximumCoauthorsOnOnePaper",
      "deltaComponentSize",
      "deltaCrossCommunityDegree",
      "deltaCrossCommunityWeight",
      "deltaCommunitiesConnected",
      "deltaParticipationCoefficient"
    )
    val pairs = config.windows
      .filter(_.comparisonOrder.nonEmpty)
      .sortBy(_.comparisonOrder.get)
      .sliding(2)
      .filter(_.size == 2)
      .toVector
    val emptySchema = new StructType()
      .add("windowId", StringType)
      .add("researcherId", StringType)
      .add("fromWindowId", StringType)
      .add("toWindowId", StringType)
      .add("fromPresent", BooleanType)
      .add("toPresent", BooleanType)
      .add("deltaDistinctCoauthors", LongType)
      .add("deltaAverageCoauthorsPerPaper", DoubleType)
      .add("deltaMaximumCoauthorsOnOnePaper", LongType)
      .add("deltaComponentSize", LongType)
      .add("enteredLargestComponent", BooleanType)
      .add("leftLargestComponent", BooleanType)
      .add("previousCommunityId", StringType)
      .add("currentCommunityId", StringType)
      .add("communityJaccardOverlap", DoubleType)
      .add("deltaCrossCommunityDegree", LongType)
      .add("deltaCrossCommunityWeight", LongType)
      .add("deltaCommunitiesConnected", LongType)
      .add("deltaParticipationCoefficient", DoubleType)
    val empty = metrics.sparkSession.createDataFrame(
      java.util.Collections.emptyList[org.apache.spark.sql.Row](),
      emptySchema
    )
    val outputs = pairs.map { pair =>
      val from = pair(0).windowId; val to = pair(1).windowId
      def side(window: String, prefix: String): DataFrame = enriched
        .filter(col("windowId") === window)
        .select(
          (Seq(
            col("researcherId"),
            lit(true).as(prefix + "Present"),
            col("communityId").as(prefix + "Community"),
            col("isLargest").as(prefix + "Largest")
          ) ++ fields.map(f => col(f).as(prefix + f)))*
        )
      val oldMembers = communities
        .filter(col("windowId") === from)
        .select(col("researcherId"), col("communityId").as("previousCommunityId"))
      val newMembers = communities
        .filter(col("windowId") === to)
        .select(col("researcherId"), col("communityId").as("currentCommunityId"))
      val oldSizes = oldMembers.groupBy("previousCommunityId").agg(count("*").as("oldSize"))
      val newSizes = newMembers.groupBy("currentCommunityId").agg(count("*").as("newSize"))
      val bestMatch = oldMembers
        .join(newMembers, Seq("researcherId"))
        .groupBy("previousCommunityId", "currentCommunityId")
        .agg(count("*").as("intersection"))
        .join(oldSizes, Seq("previousCommunityId"))
        .join(newSizes, Seq("currentCommunityId"))
        .withColumn(
          "communityJaccardOverlap",
          col("intersection").cast(DoubleType) / (col("oldSize") + col("newSize") - col(
            "intersection"
          ))
        )
        .withColumn(
          "rank",
          row_number().over(
            Window
              .partitionBy("previousCommunityId")
              .orderBy(col("communityJaccardOverlap").desc, col("currentCommunityId"))
          )
        )
        .filter(col("rank") === 1)
        .select("previousCommunityId", "communityJaccardOverlap")
      var rows = side(from, "from")
        .join(side(to, "to"), Seq("researcherId"), "full")
        .na
        .fill(false, Seq("fromPresent", "toPresent"))
        .withColumn("previousCommunityId", col("fromCommunity"))
        .withColumn("currentCommunityId", col("toCommunity"))
        .join(bestMatch, Seq("previousCommunityId"), "left")
        .withColumn(
          "communityJaccardOverlap",
          when(
            col("fromPresent") && col("toPresent"),
            coalesce(col("communityJaccardOverlap"), lit(0.0))
          )
        )
        .withColumn(
          "enteredLargestComponent",
          coalesce(col("toLargest"), lit(false)) && !coalesce(col("fromLargest"), lit(false))
        )
        .withColumn(
          "leftLargestComponent",
          coalesce(col("fromLargest"), lit(false)) && !coalesce(col("toLargest"), lit(false))
        )
        .withColumn("fromWindowId", lit(from))
        .withColumn("toWindowId", lit(to))
        .withColumn("windowId", lit(to))
      fields.zip(deltaNames).foreach { case (field, delta) =>
        rows = rows.withColumn(
          delta,
          when(col("fromPresent") && col("toPresent"), col("to" + field) - col("from" + field))
        )
      }
      rows.select(emptySchema.fieldNames.map(col)*)
    }
    Phase6Context.add(
      outputs.foldLeft(empty)((a, b) => a.unionByName(b)),
      lineage,
      runId,
      col("windowId")
    )
  }

  val sourceRefSchema: StructType =
    new StructType().add("table", StringType).add("rowKey", StringType).add("field", StringType)
  val summarySchema: StructType = new StructType()
    .add("context", Phase6Context.schema)
    .add("summaryId", StringType)
    .add("summaryType", StringType)
    .add("entityId", StringType)
    .add("policyVersion", StringType)
    .add("text", StringType)
    .add("sourceReferences", ArrayType(sourceRefSchema))
    .add("abstractTextIds", ArrayType(StringType))

  def semanticSummaries(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      canonical: Phase6CResult,
      analytics: Phase6DEResult,
      lineage: SparkLineage,
      runId: String
  ): DataFrame = {
    spark.udf.register(
      "phase6SummaryId",
      new UDF5[String, String, String, String, String, String] {
        def call(
            entity: String,
            policy: String,
            window: String,
            kind: String,
            text: String
        ): String =
          StableIds
            .sparkSemanticSummaryId(entity, policy, window, kind, text)
            .fold(e => throw new IllegalArgumentException(e.toString), identity)
      },
      StringType
    )
    def ref(table: String, key: org.apache.spark.sql.Column, field: String) =
      struct(lit(table).as("table"), key.as("rowKey"), lit(field).as("field"))
    def finish(df: DataFrame, kind: String): DataFrame = {
      val out = Phase6Context
        .add(
          df.withColumn("summaryType", lit(kind))
            .withColumn("policyVersion", lit(config.graphPolicyVersion)),
          lineage,
          runId,
          col("windowId")
        )
        .withColumn(
          "summaryId",
          expr("phase6SummaryId(entityId,policyVersion,windowId,summaryType,text)")
        )
      require(
        !BoundedActions.exists(out.filter(length(col("text")) >= 1200)),
        "summary exceeds approved limit"
      )
      out.select((Seq(col("windowId")) ++ summarySchema.fieldNames.map(col))*)
    }
    val m = analytics.metrics
    val researcher = finish(
      m.select(
        col("windowId"),
        col("researcherId").as("entityId"),
        concat(
          lit("Publications: "),
          col("publicationCount"),
          lit(". Distinct coauthors: "),
          col("distinctCoauthorCount"),
          lit(". Coauthor occurrences: "),
          col("totalCoauthorOccurrences"),
          lit(". Average coauthors per paper: "),
          col("averageCoauthorsPerPaper"),
          lit(". Maximum coauthors on one paper: "),
          col("maximumCoauthorsOnOnePaper"),
          lit(". Weighted degree: "),
          col("weightedDegree"),
          lit(".")
        ).as("text"),
        array(
          Seq(
            "publicationCount",
            "distinctCoauthorCount",
            "totalCoauthorOccurrences",
            "averageCoauthorsPerPaper",
            "maximumCoauthorsOnOnePaper",
            "weightedDegree"
          ).map(f =>
            ref(
              "metrics/type=researcher_collaboration",
              concat_ws("/", col("windowId"), col("researcherId")),
              f
            )
          )*
        ).as("sourceReferences"),
        array().cast(ArrayType(StringType)).as("abstractTextIds")
      ),
      "researcher-profile"
    )
    val community = finish(
      analytics.communitySummaries.select(
        col("windowId"),
        col("communityId").as("entityId"),
        concat(
          lit("Community size: "),
          col("size"),
          lit(". Label propagation iterations: "),
          col("iterations"),
          lit(". Changed labels in final iteration: "),
          col("finalChangedCount"),
          lit(". Converged: "),
          col("converged"),
          lit(".")
        ).as("text"),
        array(
          Seq("size", "iterations", "finalChangedCount", "converged").map(f =>
            ref(
              "metrics/type=community_summaries",
              concat_ws("/", col("windowId"), col("communityId")),
              f
            )
          )*
        ).as("sourceReferences"),
        array().cast(ArrayType(StringType)).as("abstractTextIds")
      ),
      "community"
    )
    val path = finish(
      analytics.paths.select(
        col("windowId"),
        col("pathEvidenceId").as("entityId"),
        concat(
          lit("Selected collaboration path status: "),
          col("status"),
          lit(". Hop count: "),
          coalesce(col("hopCount").cast(StringType), lit("absent")),
          lit(". Maximum search hops: "),
          col("maxHops"),
          lit(".")
        ).as("text"),
        array(
          Seq("status", "hopCount", "maxHops").map(f =>
            ref("path-evidence", concat_ws("/", col("windowId"), col("pathEvidenceId")), f)
          )*
        ).as("sourceReferences"),
        array().cast(ArrayType(StringType)).as("abstractTextIds")
      ),
      "collaboration-path"
    )
    val observations = workSources(canonical)
    val windows = spark.createDataFrame(
      config.windows
        .map(w =>
          RowFactory
            .create(w.windowId, w.startYear.map(Int.box).orNull, w.endYear.map(Int.box).orNull)
        )
        .asJava,
      new StructType()
        .add("windowId", StringType)
        .add("startYear", IntegerType)
        .add("endYear", IntegerType)
    )
    val paper = finish(
      observations
        .crossJoin(broadcast(windows))
        .filter(
          (col("startYear").isNull && col("endYear").isNull) || (col("year").isNotNull && (col(
            "startYear"
          ).isNull || col("year") >= col("startYear")) && (col("endYear").isNull || col(
            "year"
          ) <= col("endYear")))
        )
        .select(
          col("windowId"),
          col("workId").as("entityId"),
          concat(
            lit("Paper title: "),
            substring(coalesce(col("title"), lit("unavailable")), 1, 900),
            lit(". Publication year: "),
            coalesce(col("year").cast(StringType), lit("unknown")),
            lit(".")
          ).as("text"),
          array(
            ref("nodes/type=work_sources", col("workId"), "title"),
            ref("nodes/type=work_sources", col("workId"), "year")
          ).as("sourceReferences"),
          when(col("abstractTextRef").isNotNull, array(col("abstractTextRef")))
            .otherwise(array().cast(ArrayType(StringType)))
            .as("abstractTextIds")
        ),
      "paper"
    )
    researcher.unionByName(community).unionByName(path).unionByName(paper)
  }
  def workSources(canonical: Phase6CResult): DataFrame = {
    val works =
      if (canonical.works.columns.contains("abstractTextRef")) canonical.works
      else canonical.works.withColumn("abstractTextRef", lit(null).cast(StringType))
    works
      .withColumn(
        "sourceRank",
        row_number().over(
          Window
            .partitionBy("workId")
            .orderBy(
              col("sourceRecordId"),
              col("source"),
              col("title"),
              col("year"),
              col("abstractTextRef")
            )
        )
      )
      .filter(col("sourceRank") === 1)
      .drop("sourceRank")
  }

}
