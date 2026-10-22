package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import org.apache.spark.sql.{DataFrame, Row, RowFactory, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.expressions.Window
import org.apache.spark.sql.types.*
import org.apache.spark.sql.api.java.UDF4
import scala.jdk.CollectionConverters.*

/** Distributed jobs 3–8 over the canonical Job 1–2 tables. No graph rows are collected. */
final case class Phase6DEResult(
    metrics: DataFrame,
    components: DataFrame,
    componentSummaries: DataFrame,
    coreness: DataFrame,
    paths: DataFrame,
    communities: DataFrame,
    communitySummaries: DataFrame,
    crossCommunityEdges: DataFrame,
    bridges: DataFrame,
    pathLengthEstimates: DataFrame,
    counters: DataFrame
)

object Phase6DEJobs {
  private def windows(spark: SparkSession, config: SparkAnalyticsConfig): DataFrame = {
    val schema = new StructType()
      .add("windowId", StringType)
      .add("startYear", IntegerType)
      .add("endYear", IntegerType)
    spark.createDataFrame(
      config.windows
        .map(w =>
          RowFactory.create(
            w.windowId,
            w.startYear.map(Int.box).orNull,
            w.endYear.map(Int.box).orNull
          )
        )
        .asJava,
      schema
    )
  }

  private def withContext(df: DataFrame, lineage: SparkLineage, runId: String): DataFrame = {
    val sample = CoreJson.compact(
      SparkRecordContext(
        SchemaVersions.sparkAnalytics,
        runId,
        Some("all-years"),
        lineage
      )
    )
    val context = struct(
      lit(SchemaVersions.sparkAnalytics).as("schemaVersion"),
      lit(runId).as("runId"),
      col("windowId").as("windowId"),
      from_json(lit(CoreJson.compact(lineage)), schema_of_json(lit(CoreJson.compact(lineage))))
        .as("lineage")
    )
    // Parse against the wire shape so the nested field order and nullability match core examples.
    df.withColumn("context", from_json(to_json(context), schema_of_json(lit(sample))))
  }

  private def idUdf(spark: SparkSession, config: SparkAnalyticsConfig): Unit = {
    spark.udf.register(
      "phase6DEId",
      new UDF4[String, String, String, String, String] {
        def call(kind: String, window: String, first: String, second: String): String =
          StableIds
            .sparkAnalyticsId(
              kind,
              config.graphPolicyVersion,
              window,
              if (second == null) Seq(first) else Seq(first, second)
            )
            .fold(e => throw new IllegalArgumentException(e.toString), identity)
      },
      StringType
    )
  }

  private def arcs(edges: DataFrame): DataFrame = edges
    .select(
      col("windowId"),
      col("researcherA").as("src"),
      col("researcherB").as("dst"),
      col("edgeId"),
      col("jointPublicationCount").as("weight"),
      col("representativeWorkIds")
    )
    .unionByName(
      edges.select(
        col("windowId"),
        col("researcherB").as("src"),
        col("researcherA").as("dst"),
        col("edgeId"),
        col("jointPublicationCount").as("weight"),
        col("representativeWorkIds")
      )
    )
    .dropDuplicates("windowId", "src", "dst")

  private def activeMemberships(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      memberships: DataFrame
  ): DataFrame = {
    val w = broadcast(windows(spark, config))
    memberships
      .select("canonicalWorkId", "researcherId", "year")
      .dropDuplicates("canonicalWorkId", "researcherId")
      .crossJoin(w)
      .filter(
        (col("startYear").isNull && col("endYear").isNull) ||
          (col("year").isNotNull &&
            (col("startYear").isNull || col("year") >= col("startYear")) &&
            (col("endYear").isNull || col("year") <= col("endYear")))
      )
      .select("windowId", "canonicalWorkId", "researcherId")
  }

  private[spark] def metricsBase(
      active: DataFrame,
      edges: DataFrame,
      config: SparkAnalyticsConfig
  ): DataFrame = {
    val team = active
      .groupBy("windowId", "canonicalWorkId")
      .agg(countDistinct("researcherId").as("teamSize"))
    val perWork = active
      .join(team, Seq("windowId", "canonicalWorkId"))
      .withColumn("coauthors", col("teamSize") - lit(1L))
    val totals = perWork
      .groupBy("windowId", "researcherId")
      .agg(
        countDistinct("canonicalWorkId").as("publicationCount"),
        sum("coauthors").as("totalCoauthorOccurrences"),
        max("coauthors").as("maximumCoauthorsOnOnePaper")
      )
    val maxWorks = perWork
      .join(
        totals.select("windowId", "researcherId", "maximumCoauthorsOnOnePaper"),
        Seq("windowId", "researcherId")
      )
      .filter(col("coauthors") === col("maximumCoauthorsOnOnePaper"))
      .groupBy("windowId", "researcherId")
      .agg(
        sort_array(collect_set("canonicalWorkId")).as("allMaxTeamWorkIds"),
        countDistinct("canonicalWorkId").as("maxTeamWorkTieCount")
      )
      .withColumn("maxTeamWorkIds", slice(col("allMaxTeamWorkIds"), 1, config.maxTeamWorkLimit))
      .drop("allMaxTeamWorkIds")
    val adjacency = arcs(edges)
      .groupBy("windowId", "src")
      .agg(
        countDistinct("dst").as("distinctCoauthorCount"),
        sum("weight").as("weightedDegree")
      )
      .withColumnRenamed("src", "researcherId")
    totals
      .join(maxWorks, Seq("windowId", "researcherId"))
      .join(adjacency, Seq("windowId", "researcherId"), "left")
      .na
      .fill(0L, Seq("distinctCoauthorCount", "weightedDegree"))
      .withColumn(
        "averageCoauthorsPerPaper",
        col("totalCoauthorOccurrences").cast(DoubleType) / col("publicationCount")
      )
  }

  private def connected(
      vertices: DataFrame,
      adjacency: DataFrame,
      config: SparkAnalyticsConfig
  ): (DataFrame, Int, Long) = {
    var labels = vertices
      .select("windowId", "researcherId")
      .withColumn("label", col("researcherId"))
      .repartition(col("windowId"), col("researcherId"))
      .checkpoint(eager = true)
      .cache()
    var changed = true
    var iteration = 0
    var totalChanges = 0L
    while (changed && iteration < config.componentMaxIterations) {
      val offered = adjacency
        .join(
          labels.select(col("windowId"), col("researcherId").as("src"), col("label")),
          Seq("windowId", "src")
        )
        .select(col("windowId"), col("dst").as("researcherId"), col("label"))
      var next = labels
        .unionByName(offered)
        .groupBy("windowId", "researcherId")
        .agg(min("label").as("label"))
      if ((iteration + 1) % config.checkpointInterval == 0)
        next = next.checkpoint(eager = true)
      next = next.cache()
      val changes = BoundedActions.count(
        labels
          .as("old")
          .join(next.as("new"), Seq("windowId", "researcherId"))
          .filter(col("old.label") =!= col("new.label"))
      )
      changed = changes > 0L
      totalChanges += changes
      labels.unpersist()
      labels = next
      iteration += 1
    }
    require(!changed, s"components did not converge in ${config.componentMaxIterations} iterations")
    (
      labels.withColumn("componentId", expr("phase6DEId('component',windowId,label,null)")),
      iteration,
      totalChanges
    )
  }

  private def componentSummary(
      members: DataFrame,
      lineage: SparkLineage,
      runId: String
  ): DataFrame = {
    val sizes = members
      .groupBy("windowId", "componentId", "label")
      .agg(count("*").as("size"))
    val totals = sizes
      .groupBy("windowId")
      .agg(
        sum("size").as("allResearchers"),
        sum(when(col("size") === 1L, lit(1L)).otherwise(lit(0L))).as("singletonCount")
      )
    val rank = Window.partitionBy("windowId").orderBy(col("size").desc, col("componentId"))
    withContext(
      sizes
        .join(totals, Seq("windowId"))
        .withColumn("isLargest", row_number().over(rank) === 1)
        .withColumn(
          "largestComponentFraction",
          max("size").over(Window.partitionBy("windowId")).cast(DoubleType) /
            col("allResearchers")
        )
        .withColumnRenamed("label", "minimumResearcherId")
        .drop("allResearchers"),
      lineage,
      runId
    )
  }

  private def kCore(
      vertices: DataFrame,
      adjacency: DataFrame,
      config: SparkAnalyticsConfig
  ): (DataFrame, Int, Long) = {
    val degree = adjacency
      .groupBy("windowId", "src")
      .agg(countDistinct("dst").cast(IntegerType).as("degree"))
      .withColumnRenamed("src", "researcherId")
    var scores = vertices
      .join(degree, Seq("windowId", "researcherId"), "left")
      .na
      .fill(0, Seq("degree"))
      .withColumn("coreness", col("degree"))
      .repartition(col("windowId"), col("researcherId"))
      .checkpoint(eager = true)
      .cache()
    var changed = true
    var iteration = 0
    var totalChanges = 0L
    while (changed && iteration < config.kCoreMaxIterations) {
      val candidate = adjacency
        .join(
          scores.select(
            col("windowId"),
            col("researcherId").as("dst"),
            col("coreness").as("neighborCore")
          ),
          Seq("windowId", "dst")
        )
        .withColumn(
          "rank",
          row_number().over(
            Window
              .partitionBy("windowId", "src")
              .orderBy(col("neighborCore").desc, col("dst"))
          )
        )
        .groupBy("windowId", "src")
        .agg(
          max(
            when(col("neighborCore") >= col("rank"), col("rank"))
              .otherwise(lit(0))
          ).as("h")
        )
        .withColumnRenamed("src", "researcherId")
      var next = scores
        .join(candidate, Seq("windowId", "researcherId"), "left")
        .withColumn("coreness", least(col("coreness"), coalesce(col("h"), lit(0))))
        .drop("h")
      if ((iteration + 1) % config.checkpointInterval == 0)
        next = next.checkpoint(eager = true)
      next = next.cache()
      val changes = BoundedActions.count(
        scores
          .as("old")
          .join(next.as("new"), Seq("windowId", "researcherId"))
          .filter(col("old.coreness") =!= col("new.coreness"))
      )
      changed = changes > 0L
      totalChanges += changes
      scores.unpersist()
      scores = next
      iteration += 1
    }
    require(!changed, s"k-core did not converge in ${config.kCoreMaxIterations} iterations")
    require(
      !BoundedActions.exists(
        scores.filter(
          col("coreness") < 0 ||
            col("coreness") > col("degree")
        )
      ),
      "invalid coreness"
    )
    (scores, iteration, totalChanges)
  }

  private def community(
      vertices: DataFrame,
      adjacency: DataFrame,
      config: SparkAnalyticsConfig
  ): (DataFrame, Int, DataFrame) = {
    var labels = vertices
      .select("windowId", "researcherId")
      .withColumn("label", col("researcherId"))
      .repartition(col("windowId"), col("researcherId"))
      .checkpoint(eager = true)
      .cache()
    var iteration = 0
    var changed = 1L
    var changes = vertices
      .select("windowId")
      .distinct()
      .withColumn("finalChangedCount", lit(0L))
    while (changed > 0 && iteration < config.communityMaxIterations) {
      val vote = adjacency
        .join(
          labels.select(col("windowId"), col("researcherId").as("dst"), col("label")),
          Seq("windowId", "dst")
        )
        .groupBy("windowId", "src", "label")
        .agg(sum("weight").as("voteWeight"))
        .withColumn(
          "rank",
          row_number().over(
            Window
              .partitionBy("windowId", "src")
              .orderBy(col("voteWeight").desc, col("label"))
          )
        )
        .filter(col("rank") === 1)
        .select(col("windowId"), col("src").as("researcherId"), col("label"))
      var next = labels
        .select("windowId", "researcherId")
        .join(vote, Seq("windowId", "researcherId"), "left")
        .withColumn("label", coalesce(col("label"), col("researcherId")))
      if ((iteration + 1) % config.checkpointInterval == 0)
        next = next.checkpoint(eager = true)
      val differences = labels
        .as("old")
        .join(next.as("new"), Seq("windowId", "researcherId"))
        .filter(col("old.label") =!= col("new.label"))
      changes = vertices
        .select("windowId")
        .distinct()
        .join(
          differences
            .groupBy("windowId")
            .agg(count("*").as("finalChangedCount")),
          Seq("windowId"),
          "left"
        )
        .na
        .fill(0L, Seq("finalChangedCount"))
        .checkpoint(eager = true)
      next = next.cache()
      changed = BoundedActions.scalarLong(
        changes.select(
          coalesce(sum("finalChangedCount"), lit(0L))
            .as("finalChangedCount")
        ),
        "finalChangedCount"
      )
      labels.unpersist()
      labels = next
      iteration += 1
    }
    (
      labels.withColumn("communityId", expr("phase6DEId('community',windowId,label,null)")),
      iteration,
      changes
    )
  }

  /** Required bridge measures; `communities` may be an injected test partition. */
  def bridgeMeasures(
      config: SparkAnalyticsConfig,
      edges: DataFrame,
      communities: DataFrame,
      lineage: SparkLineage,
      runId: String
  ): DataFrame = {
    val a = arcs(edges)
    val source = communities.select(
      col("windowId"),
      col("researcherId").as("src"),
      col("communityId").as("srcCommunity")
    )
    val dest = communities.select(
      col("windowId"),
      col("researcherId").as("dst"),
      col("communityId").as("dstCommunity")
    )
    val neighbors = a
      .join(source, Seq("windowId", "src"))
      .join(dest, Seq("windowId", "dst"))
    val byCommunity = neighbors
      .groupBy("windowId", "src", "srcCommunity", "dstCommunity")
      .agg(countDistinct("dst").as("neighborCount"), sum("weight").as("neighborWeight"))
    val output = byCommunity
      .groupBy("windowId", "src", "srcCommunity")
      .agg(
        sum(
          when(col("dstCommunity") =!= col("srcCommunity"), col("neighborCount"))
            .otherwise(lit(0L))
        ).as("crossCommunityDegree"),
        sum(
          when(col("dstCommunity") =!= col("srcCommunity"), col("neighborWeight"))
            .otherwise(lit(0L))
        ).as("crossCommunityWeight"),
        sum(
          when(col("dstCommunity") =!= col("srcCommunity"), lit(1L))
            .otherwise(lit(0L))
        ).as("communitiesConnected"),
        sum("neighborCount").as("degree"),
        sum(
          col("neighborCount").cast(DoubleType) *
            col("neighborCount").cast(DoubleType)
        ).as("sumSquares")
      )
      .withColumn(
        "participationCoefficient",
        lit(1.0) -
          col("sumSquares").cast(DoubleType) /
          (col("degree").cast(DoubleType) * col("degree").cast(DoubleType))
      )
      .withColumnRenamed("src", "researcherId")
    require(
      !BoundedActions.exists(
        output.filter(
          col("crossCommunityDegree") > col("degree") ||
            col("crossCommunityWeight") < col("crossCommunityDegree") ||
            col("participationCoefficient") < lit(-1e-12) ||
            col("participationCoefficient") > lit(1.0 + 1e-12)
        )
      ),
      "invalid bridge measure"
    )
    withContext(
      communities
        .select("windowId", "researcherId")
        .join(
          output.drop("srcCommunity", "degree", "sumSquares"),
          Seq("windowId", "researcherId"),
          "left"
        )
        .na
        .fill(0L, Seq("crossCommunityDegree", "crossCommunityWeight", "communitiesConnected"))
        .na
        .fill(0.0, Seq("participationCoefficient"))
        .withColumn("policyVersion", lit(config.graphPolicyVersion)),
      lineage,
      runId
    )
  }

  def build(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      input: Phase6CResult,
      lineage: SparkLineage,
      runId: String
  ): Phase6DEResult = {
    SparkAnalyticsConfigLoader
      .validate(config)
      .fold(e => throw new IllegalArgumentException(e.toString), identity)
    idUdf(spark, config)
    spark.sparkContext.setCheckpointDir(config.checkpointDirectory)
    val active = activeMemberships(spark, config, input.memberships)
      .repartition(col("windowId"), col("researcherId"))
      .checkpoint(eager = true)
    val vertices = active
      .select("windowId", "researcherId")
      .distinct()
      .checkpoint(eager = true)
    val edges = input.edges
      .select(
        "windowId",
        "researcherA",
        "researcherB",
        "edgeId",
        "jointPublicationCount",
        "representativeWorkIds"
      )
      .repartition(col("windowId"), col("researcherA"), col("researcherB"))
      .checkpoint(eager = true)
    val adjacency = arcs(edges)
      .repartition(col("windowId"), col("src"))
      .checkpoint(eager = true)
    val (componentsRaw, componentIterations, componentLabelChanges) =
      connected(vertices, adjacency, config)
    val components =
      withContext(componentsRaw.select("windowId", "researcherId", "componentId"), lineage, runId)
        .checkpoint(eager = true)
    val summaries = componentSummary(componentsRaw, lineage, runId).checkpoint(eager = true)
    val (cores, coreIterations, coreChanges) = kCore(vertices, adjacency, config)
    val metricBase = metricsBase(active, edges, config)
    val badWeightedDegree = metricBase.filter(
      col("weightedDegree") =!=
        col("totalCoauthorOccurrences")
    )
    if (BoundedActions.exists(badWeightedDegree)) {
      val keys = BoundedActions.capped(
        badWeightedDegree
          .select("windowId", "researcherId", "weightedDegree", "totalCoauthorOccurrences")
          .orderBy("windowId", "researcherId")
          .limit(5),
        5
      )
      throw new IllegalArgumentException(s"W_r != T_r for ${keys.mkString(", ")}")
    }
    val (communitiesRaw, communityIterations, communityChanges) =
      community(vertices, adjacency, config)
    val communityChanged = BoundedActions.scalarLong(
      communityChanges
        .select(
          coalesce(sum("finalChangedCount"), lit(0L))
            .as("finalChangedCount")
        ),
      "finalChangedCount"
    )
    val communityConverged = communityChanged == 0L
    val communities = withContext(
      communitiesRaw
        .select("windowId", "researcherId", "communityId")
        .join(communityChanges, Seq("windowId"))
        .withColumn("iterations", lit(communityIterations))
        .withColumn("converged", col("finalChangedCount") === 0L)
        .drop("finalChangedCount"),
      lineage,
      runId
    )
      .checkpoint(eager = true)
    val communitySummaries = withContext(
      communitiesRaw
        .groupBy("windowId", "communityId")
        .agg(count("*").as("size"))
        .join(communityChanges, Seq("windowId"))
        .withColumn("iterations", lit(communityIterations))
        .withColumn("converged", col("finalChangedCount") === 0L),
      lineage,
      runId
    )
      .checkpoint(eager = true)
    val communityA = communities.select(
      col("windowId"),
      col("researcherId").as("researcherA"),
      col("communityId").as("ca")
    )
    val communityB = communities.select(
      col("windowId"),
      col("researcherId").as("researcherB"),
      col("communityId").as("cb")
    )
    val cross = withContext(
      edges
        .join(communityA, Seq("windowId", "researcherA"))
        .join(communityB, Seq("windowId", "researcherB"))
        .filter(col("ca") =!= col("cb"))
        .withColumn("communityA", least(col("ca"), col("cb")))
        .withColumn("communityB", greatest(col("ca"), col("cb")))
        .groupBy("windowId", "communityA", "communityB")
        .agg(count("*").as("edgeCount"), sum("jointPublicationCount").as("summedWeight")),
      lineage,
      runId
    ).checkpoint(eager = true)
    val bridges = bridgeMeasures(config, edges, communities, lineage, runId)
      .checkpoint(eager = true)
    val metrics = withContext(
      metricBase
        .join(
          components.select("windowId", "researcherId", "componentId"),
          Seq("windowId", "researcherId")
        )
        .join(cores.select("windowId", "researcherId", "coreness"), Seq("windowId", "researcherId"))
        .join(
          communities.select("windowId", "researcherId", "communityId"),
          Seq("windowId", "researcherId")
        )
        .withColumn("policyVersion", lit(config.graphPolicyVersion)),
      lineage,
      runId
    )
      .checkpoint(eager = true)
    val (paths, estimates, sampledPairs) =
      selectedPaths(spark, config, vertices, adjacency, components, summaries, lineage, runId)
    val missingCommunityMembership = BoundedActions.count(
      adjacency
        .join(
          communities.select(col("windowId"), col("researcherId").as("src")),
          Seq("windowId", "src"),
          "left_anti"
        )
    )
    require(missingCommunityMembership == 0L, "edge endpoint lacks community membership")
    if (input.support != null) {
      val pathWorks = paths
        .filter(col("status") === "found")
        .select(explode(col("hops")).as("hop"))
        .select(
          col("hop.edgeId").as("edgeId"),
          explode(col("hop.representativeWorkIds")).as("workId")
        )
        .distinct()
      require(
        !BoundedActions.exists(
          pathWorks.join(
            input.support
              .select("edgeId", "workId")
              .distinct(),
            Seq("edgeId", "workId"),
            "left_anti"
          )
        ),
        "path representative work missing from edge support"
      )
    }
    val counterPairs = Vector(
      "componentIterations" -> componentIterations.toLong,
      "componentLabelChanges" -> componentLabelChanges,
      "kCoreIterations" -> coreIterations.toLong,
      "kCoreChanges" -> coreChanges,
      "communityIterations" -> communityIterations.toLong,
      "communityFinalChangedCount" -> communityChanged,
      "communityConverged" -> (if (communityConverged) 1L else 0L),
      "activeResearchers" -> BoundedActions.count(vertices),
      "metricsRows" -> BoundedActions.count(metrics),
      "soloResearchers" -> BoundedActions.count(
        metrics.filter(col("distinctCoauthorCount") === 0L)
      ),
      "soloPublications" -> BoundedActions.count(
        active
          .groupBy("windowId", "canonicalWorkId")
          .agg(countDistinct("researcherId").as("teamSize"))
          .filter(col("teamSize") === 1L)
      ),
      "maxTeamTieRows" -> BoundedActions.count(metrics.filter(col("maxTeamWorkTieCount") > 1L)),
      "maxTeamCappedRows" -> BoundedActions.count(
        metrics.filter(col("maxTeamWorkTieCount") > config.maxTeamWorkLimit)
      ),
      "components" -> BoundedActions.count(summaries),
      "singletonComponents" -> BoundedActions.count(summaries.filter(col("size") === 1L)),
      "pathFound" -> BoundedActions.count(paths.filter(col("status") === "found")),
      "pathNoPath" -> BoundedActions.count(paths.filter(col("status") === "no-path")),
      "pathExceededMaxHops" -> BoundedActions.count(
        paths.filter(col("status") === "exceeded-maxHops")
      ),
      "pathSelectedPairs" -> BoundedActions.count(paths),
      "pathSeededSamplePairs" -> sampledPairs,
      "foundPathHops" -> BoundedActions
        .scalarLong(paths.select(coalesce(sum("hopCount"), lit(0L)).as("hopCount")), "hopCount"),
      "crossCommunityEdges" -> BoundedActions.count(cross),
      "bridgeResearchers" -> BoundedActions.count(bridges),
      "missingCommunityMembership" -> missingCommunityMembership
    )
    val counterSchema = new StructType()
      .add("name", StringType)
      .add("value", LongType)
      .add("detail", StringType)
    val counters = withContext(
      spark
        .createDataFrame(
          counterPairs.map { case (name, value) =>
            RowFactory.create(name, Long.box(value), "jobs 3–8")
          }.asJava,
          counterSchema
        )
        .withColumn("windowId", lit(null).cast(StringType)),
      lineage,
      runId
    ).drop("windowId")
    // The k-core table is a materialized view of the complete metrics-detail record.
    Phase6DEResult(
      metrics,
      components,
      summaries,
      metrics,
      paths,
      communities,
      communitySummaries,
      cross,
      bridges,
      estimates,
      counters
    )
  }

  private def selectedPaths(
      spark: SparkSession,
      config: SparkAnalyticsConfig,
      vertices: DataFrame,
      adjacency: DataFrame,
      components: DataFrame,
      summaries: DataFrame,
      lineage: SparkLineage,
      runId: String
  ): (DataFrame, DataFrame, Long) = {
    val pairSchema = new StructType()
      .add("sourceResearcherId", StringType)
      .add("targetResearcherId", StringType)
      .add("selection", StringType)
    val benchmark = spark
      .createDataFrame(
        config.benchmarkPairs.map { pair =>
          def researcher(value: String): String =
            if (pair.endpointKind == "researcher-id") value
            else
              StableIds
                .researcherIdFromDblpName(config.identityPolicyVersion, value)
                .fold(e => throw new IllegalArgumentException(e.toString), identity)
          RowFactory.create(researcher(pair.left), researcher(pair.right), "benchmark")
        }.asJava,
        pairSchema
      )
      .crossJoin(broadcast(windows(spark, config).select("windowId")))
    // At most 2K nodes per window enter this seeded cross product. The graph itself stays
    // distributed; only the explicitly bounded selected-pair frontier is multiplied.
    val sampled =
      if (config.sampledPathPairCount == 0) benchmark.limit(0)
      else {
        val largest = summaries
          .filter(col("isLargest"))
          .select("windowId", "componentId")
        val seed = config.samplingSeed.toString
        val candidates = components
          .join(largest, Seq("windowId", "componentId"))
          .withColumn(
            "pickRank",
            row_number().over(
              Window
                .partitionBy("windowId")
                .orderBy(xxhash64(col("researcherId"), lit(seed)), col("researcherId"))
            )
          )
          .filter(col("pickRank") <= config.sampledPathPairCount * 2 + 1)
        candidates
          .select(col("windowId"), col("researcherId").as("sourceResearcherId"))
          .join(
            candidates.select(col("windowId"), col("researcherId").as("targetResearcherId")),
            Seq("windowId")
          )
          .filter(col("sourceResearcherId") < col("targetResearcherId"))
          .withColumn(
            "sampleRank",
            row_number().over(
              Window
                .partitionBy("windowId")
                .orderBy(
                  xxhash64(col("sourceResearcherId"), col("targetResearcherId"), lit(seed)),
                  col("sourceResearcherId"),
                  col("targetResearcherId")
                )
            )
          )
          .filter(col("sampleRank") <= config.sampledPathPairCount)
          .select("windowId", "sourceResearcherId", "targetResearcherId")
          .withColumn("selection", lit("seeded-sample"))
      }
    val sampledPairs = BoundedActions.count(sampled)
    val pairs = benchmark
      .unionByName(sampled)
      .dropDuplicates("windowId", "sourceResearcherId", "targetResearcherId")
      .checkpoint(eager = true)
    val sourceComponents = components.select(
      col("windowId"),
      col("researcherId").as("sourceResearcherId"),
      col("componentId").as("sourceComponentId")
    )
    val targetComponents = components.select(
      col("windowId"),
      col("researcherId").as("targetResearcherId"),
      col("componentId").as("targetComponentId")
    )
    val classified = pairs
      .join(sourceComponents, Seq("windowId", "sourceResearcherId"), "left")
      .join(targetComponents, Seq("windowId", "targetResearcherId"), "left")
      .withColumn(
        "sameComponent",
        col("sourceComponentId").isNotNull &&
          col("sourceComponentId") === col("targetComponentId")
      )
      .checkpoint(eager = true)
    val pairKeys = Seq("windowId", "sourceResearcherId", "targetResearcherId")
    val same = classified
      .filter(col("sameComponent"))
      .select(pairKeys.map(col)*)
      .checkpoint(eager = true)
    val hopSchema = new StructType()
      .add("fromResearcherId", StringType)
      .add("toResearcherId", StringType)
      .add("edgeId", StringType)
      .add("jointPublicationCount", LongType)
      .add("representativeWorkIds", ArrayType(StringType))
    val emptyHops = array().cast(ArrayType(hopSchema))
    var frontier = same
      .withColumn("node", col("sourceResearcherId"))
      .withColumn("orderedResearcherIds", array(col("sourceResearcherId")))
      .withColumn("hops", emptyHops)
      .checkpoint(eager = true)
    var visited = frontier.select((pairKeys.map(col) :+ col("node"))*).checkpoint(eager = true)
    var found = frontier.limit(0).withColumn("distance", lit(0))
    var distance = 0
    while (distance < config.maxHops && BoundedActions.exists(frontier)) {
      val candidate = frontier
        .as("f")
        .join(
          adjacency.as("a"),
          col("f.windowId") === col("a.windowId") && col("f.node") === col("a.src")
        )
        .select(
          col("f.windowId").as("windowId"),
          col("f.sourceResearcherId").as("sourceResearcherId"),
          col("f.targetResearcherId").as("targetResearcherId"),
          col("a.dst").as("node"),
          col("a.src").as("predecessor"),
          concat(col("f.orderedResearcherIds"), array(col("a.dst")))
            .as("orderedResearcherIds"),
          concat(
            col("f.hops"),
            array(
              struct(
                col("a.src").as("fromResearcherId"),
                col("a.dst").as("toResearcherId"),
                col("a.edgeId"),
                col("a.weight").as("jointPublicationCount"),
                col("a.representativeWorkIds")
              )
            )
          ).as("hops")
        )
        .join(visited, pairKeys :+ "node", "left_anti")
      val rank = Window
        .partitionBy((pairKeys.map(col) :+ col("node"))*)
        .orderBy(col("predecessor"), to_json(col("orderedResearcherIds")))
      val next = candidate
        .withColumn("rank", row_number().over(rank))
        .filter(col("rank") === 1)
        .drop("rank", "predecessor")
        .checkpoint(eager = true)
      distance += 1
      found = found.unionByName(
        next
          .filter(col("node") === col("targetResearcherId"))
          .withColumn("distance", lit(distance))
      )
      visited = visited
        .unionByName(next.select((pairKeys.map(col) :+ col("node"))*))
        .dropDuplicates(pairKeys :+ "node")
        .checkpoint(eager = true)
      frontier = next.filter(col("node") =!= col("targetResearcherId"))
    }
    val foundRank = Window
      .partitionBy(pairKeys.map(col)*)
      .orderBy(col("distance"), to_json(col("orderedResearcherIds")))
    val best = found
      .withColumn("rank", row_number().over(foundRank))
      .filter(col("rank") === 1)
      .select(
        (pairKeys.map(col) ++ Seq(
          col("distance").as("hopCount"),
          col("orderedResearcherIds"),
          col("hops")
        ))*
      )
    val paths = withContext(
      classified
        .join(best, pairKeys, "left")
        .withColumn(
          "status",
          when(col("hopCount").isNotNull, lit("found"))
            .when(!col("sameComponent"), lit("no-path"))
            .otherwise(lit("exceeded-maxHops"))
        )
        .withColumn(
          "orderedResearcherIds",
          coalesce(col("orderedResearcherIds"), array().cast(ArrayType(StringType)))
        )
        .withColumn("hops", coalesce(col("hops"), emptyHops))
        .withColumn("maxHops", lit(config.maxHops))
        .withColumn(
          "pathEvidenceId",
          expr("phase6DEId('path-evidence',windowId,sourceResearcherId,targetResearcherId)")
        )
        .select(
          "windowId",
          "pathEvidenceId",
          "sourceResearcherId",
          "targetResearcherId",
          "status",
          "hopCount",
          "orderedResearcherIds",
          "hops",
          "maxHops"
        ),
      lineage,
      runId
    ).checkpoint(eager = true)
    // The S-source effective-diameter estimate is deferred by the approved schedule choice.
    val estimateSchema = new StructType()
      .add("windowId", StringType)
      .add("componentId", StringType)
      .add("method", StringType)
      .add("sampleSourceCount", IntegerType)
      .add("seed", LongType)
      .add("meanDistance", DoubleType)
      .add("effectiveDiameterP90", DoubleType)
      .add("reachedPairCount", LongType)
    val estimates = withContext(
      spark.createDataFrame(java.util.Collections.emptyList[Row](), estimateSchema),
      lineage,
      runId
    )
    (paths, estimates, sampledPairs)
  }
}
