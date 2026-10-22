package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.*
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.functions.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Independent public-interface acceptance tests; every expected graph value is hand computed. */
class IndependentPhase6FGSpec extends AnyFunSuite with BeforeAndAfterAll {
  import IndependentPhase6G1.*
  private var spark: SparkSession = _
  private var root: Path = _

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("scholarchain-independent-6fg-")
    spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("ScholarChain independent jobs 9–11")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
      .config("spark.ui.retainedTasks", "100")
      .config("spark.sql.maxPlanStringLength", "65536")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
    spark.sparkContext.setCheckpointDir(root.resolve("checkpoints").toString)
  }
  override protected def afterAll(): Unit = {
    try {
      if (spark != null) spark.stop()
      if (root != null) {
        val files = Files.walk(root)
        try files.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
        finally files.close()
      }
    } finally super.afterAll()
  }

  private def config: SparkAnalyticsConfig = {
    val resource = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    require(resource != null)
    val text =
      try new String(resource.readAllBytes(), UTF_8)
      finally resource.close()
    SparkAnalyticsConfigLoader
      .loadText(text)
      .toOption
      .get
      .copy(
        windows = windows,
        identityPolicyVersion = identityPolicy,
        graphPolicyVersion = graphPolicy,
        representativePolicyVersion = representativePolicy,
        communityMaxIterations = 3,
        sampledPathPairCount = 2,
        pathSampleSourceCount = 32,
        benchmarkPairs =
          Vector(BenchmarkPair("A", "G", "dblp-name"), BenchmarkPair("A", "H", "dblp-name")),
        checkpointDirectory = root.resolve("checkpoints").toString,
        outputRoot = root.resolve("output").toString
      )
  }
  private val lineage =
    SparkLineage(hadoopRunId, snapshot, erRunId, erPolicy, erPolicyHash, Vector.empty, Vector.empty)
  private lazy val canonical =
    Phase6CJobs.build(spark, config, IndependentPhase6FGFixtures.input(spark), lineage, sparkRunId)
  private lazy val analytics = Phase6DEJobs.build(spark, config, canonical, lineage, sparkRunId)
  private lazy val finalJobs =
    Phase6FGJobs.build(spark, config, canonical, analytics, lineage, sparkRunId)

  private def temporalRows: Vector[TemporalChange] =
    finalJobs.temporalChanges.toJSON.collect().toVector.map { text =>
      val value = CoreJson.parse[TemporalChange](text).toOption.get
      assert(SparkAnalyticsValidation.check(value).isRight, text)
      value
    }

  test("G1 disjoint-window recomputation gives exact D deltas and explicit entry/exit rows") {
    val rows = temporalRows
    assert(rows.size == 10)
    assert(rows.forall(r => r.fromWindowId == "2015-2017" && r.toWindowId == "2018-2021"))
    val d = rows.find(_.researcherId == researcherId("D")).get
    assert(d.fromPresent && d.toPresent)
    // Early D has only C; later D has E,F. Its component contains four vertices in both windows.
    assert(d.deltaDistinctCoauthors.contains(1L))
    assert(d.deltaAverageCoauthorsPerPaper.contains(1.0))
    assert(d.deltaMaximumCoauthorsOnOnePaper.contains(1L))
    assert(d.deltaComponentSize.contains(0L))
    assert(!d.enteredLargestComponent && !d.leftLargestComponent)
    val a = rows.find(_.researcherId == researcherId("A")).get
    assert(a.fromPresent && !a.toPresent)
    assert(a.deltaDistinctCoauthors.isEmpty && a.deltaAverageCoauthorsPerPaper.isEmpty)
    assert(a.deltaMaximumCoauthorsOnOnePaper.isEmpty && a.deltaComponentSize.isEmpty)
    assert(a.deltaCrossCommunityWeight.isEmpty && a.communityJaccardOverlap.isEmpty)
    assert(a.leftLargestComponent && !a.enteredLargestComponent)
    val j = rows.find(_.researcherId == researcherId("J")).get
    assert(!j.fromPresent && j.toPresent)
    assert(j.deltaDistinctCoauthors.isEmpty && j.deltaComponentSize.isEmpty)
    assert(j.deltaParticipationCoefficient.isEmpty && j.previousCommunityId.isEmpty)
    assert(!j.enteredLargestComponent && !j.leftLargestComponent)
    val g = rows.find(_.researcherId == researcherId("G")).get
    assert(g.enteredLargestComponent && !g.leftLargestComponent)
    assert(!rows.exists(r => r.fromWindowId == "all-years" || r.toWindowId == "all-years"))
    val missingEndpoints = analytics.counters
      .filter(col("name") === "pathMissingBenchmarkEndpoints")
      .select("value")
      .collect()
    assert(missingEndpoints.length == 1 && missingEndpoints.head.getLong(0) == 4L)
    val metrics = analytics.metrics.toJSON
      .collect()
      .toVector
      .map(CoreJson.parse[ResearcherMetricsDetail](_).toOption.get)
    val early = metrics
      .find(r => r.context.windowId.contains("2015-2017") && r.researcherId == researcherId("D"))
      .get
    val late = metrics
      .find(r => r.context.windowId.contains("2018-2021") && r.researcherId == researcherId("D"))
      .get
    assert(
      (
        early.publicationCount,
        early.distinctCoauthorCount,
        early.totalCoauthorOccurrences,
        early.averageCoauthorsPerPaper,
        early.maximumCoauthorsOnOnePaper
      ) == (1L, 1L, 1L, 1.0, 1L)
    )
    assert(
      (
        late.publicationCount,
        late.distinctCoauthorCount,
        late.totalCoauthorOccurrences,
        late.averageCoauthorsPerPaper,
        late.maximumCoauthorsOnOnePaper
      ) == (1L, 2L, 2L, 2.0, 2L)
    )
  }

  test("S-source estimate on a three-node chain has exact ordered-pair mean and P90") {
    val works = Vector(
      work("estimate-xy", Some(2020), Vector("X", "Y")),
      work("estimate-yz", Some(2020), Vector("Y", "Z"))
    )
    val c = config.copy(
      windows = Vector(windows.head),
      benchmarkPairs = Vector.empty,
      sampledPathPairCount = 0
    )
    val graph = Phase6CJobs.build(
      spark,
      c,
      IndependentPhase6FGFixtures.input(spark, works),
      lineage,
      sparkRunId
    )
    val de = Phase6DEJobs.build(spark, c, graph, lineage, sparkRunId)
    val rows = de.pathLengthEstimates.toJSON
      .collect()
      .map(CoreJson.parse[PathLengthEstimate](_).toOption.get)
    assert(rows.length == 1)
    val estimate = rows.head
    assert(SparkAnalyticsValidation.check(estimate).isRight)
    assert(estimate.sampleSourceCount == 3)
    assert(estimate.reachedPairCount == 6L)
    // Ordered distances are 1,2,1,1,2,1: mean 8/6, nearest-rank 90th percentile 2.
    assert(math.abs(estimate.meanDistance - 4.0 / 3.0) < 1e-12)
    assert(estimate.effectiveDiameterP90 == 2.0)
    assert(estimate.seed == 441L)
  }

  test("empty configured window produces no invented metrics, paths, summaries or estimates") {
    val emptyWindow = SparkWindow("empty-2100", Some(2100), Some(2100), None)
    val c = config.copy(
      windows = Vector(emptyWindow),
      benchmarkPairs = Vector.empty,
      sampledPathPairCount = 0
    )
    val graph =
      Phase6CJobs.build(spark, c, IndependentPhase6FGFixtures.input(spark), lineage, sparkRunId)
    val de = Phase6DEJobs.build(spark, c, graph, lineage, sparkRunId)
    val fg = Phase6FGJobs.build(spark, c, graph, de, lineage, sparkRunId)
    assert(de.metrics.count() == 0 && de.components.count() == 0 && de.communities.count() == 0)
    assert(de.paths.count() == 0 && de.pathLengthEstimates.count() == 0)
    assert(fg.temporalChanges.count() == 0 && fg.summaries.count() == 0)
  }

  test(
    "near-Hadoop-limit team preserves every distinct pair and reports ORCID conflict without splitting"
  ) {
    // The checked-in Hadoop maxAuthorTeamSize is 16. Fifteen names yield 15*14/2=105 pairs.
    val names = (1 to 15).map(i => s"Team member $i").toVector
    val first = work("large-team", Some(2020), names)
    val second0 = work("orcid-observation", Some(2020), Vector(names.head))
    val firstWithOrcid = first.copy(authors =
      first.authors.updated(0, first.authors.head.copy(observedOrcid = Some("0000-0002-1825-0097")))
    )
    val second = second0.copy(authors =
      second0.authors.map(_.copy(observedOrcid = Some("0000-0001-5109-3700")))
    )
    val c = config.copy(
      windows = Vector(windows.head),
      benchmarkPairs = Vector.empty,
      sampledPathPairCount = 0
    )
    val graph = Phase6CJobs.build(
      spark,
      c,
      IndependentPhase6FGFixtures.input(spark, Vector(firstWithOrcid, second)),
      lineage,
      sparkRunId
    )
    assert(graph.researchers.count() == 15L)
    assert(graph.edges.count() == 105L)
    assert(graph.edges.filter(col("researcherA") === col("researcherB")).count() == 0L)
    assert(graph.edges.filter(col("jointPublicationCount") =!= lit(1L)).count() == 0L)
    assert(graph.integrity.filter(col("code") === "conflicting-dblp-orcid").count() == 1L)
    assert(graph.integrity.filter(col("hardFailure") === true).count() == 0L)
  }

  test("community continuity uses best Jaccard and handles tied candidate communities") {
    val early = "2015-2017"; val late = "2018-2021"
    val ids = Vector("A", "B", "C", "D").map(researcherId)
    def cid(window: String, name: String): String = StableIds
      .sparkAnalyticsId("community", graphPolicy, window, Seq(researcherId(name)))
      .toOption
      .get
    val previous = cid(early, "A")
    val candidates = Vector(cid(late, "A"), cid(late, "C")).sorted
    val baseMetrics =
      analytics.metrics.filter(col("windowId") === "all-years" && col("researcherId").isin(ids*))
    val comp =
      StableIds.sparkAnalyticsId("component", graphPolicy, "all-years", Seq(ids.min)).toOption.get
    def windowed(df: DataFrame): DataFrame =
      df.withColumn("windowId", lit(early)).unionByName(df.withColumn("windowId", lit(late)))
    val m = windowed(baseMetrics.withColumn("componentId", lit(comp)))
    val summaries = windowed(
      analytics.componentSummaries
        .filter(col("windowId") === "all-years" && col("isLargest"))
        .withColumn("componentId", lit(comp))
        .withColumn("size", lit(4L))
    )
    val baseCommunity = analytics.communities.filter(
      col("windowId") === "all-years" && col("researcherId").isin(ids*)
    )
    val communities = baseCommunity
      .withColumn("windowId", lit(early))
      .withColumn("communityId", lit(previous))
      .unionByName(
        baseCommunity
          .withColumn("windowId", lit(late))
          .withColumn(
            "communityId",
            when(col("researcherId").isin(ids.take(2)*), lit(candidates.head))
              .otherwise(lit(candidates.last))
          )
      )
    val bridges = windowed(
      analytics.bridges.filter(col("windowId") === "all-years" && col("researcherId").isin(ids*))
    )
    val output = Phase6FGJobs
      .temporalFromTables(config, m, summaries, communities, bridges, lineage, sparkRunId)
      .toJSON
      .collect()
      .map(CoreJson.parse[TemporalChange](_).toOption.get)
    assert(output.length == 4)
    // Old set is {A,B,C,D}; each new set has two members. Intersection2/union4 = 1/2.
    assert(output.forall(_.communityJaccardOverlap.contains(0.5)))
    output.foreach(r => assert(SparkAnalyticsValidation.check(r).isRight))
    // currentCommunityId records each researcher's actual new group; the core record has no
    // separate best-match-ID field, so equal-overlap candidate ordering is not wire-observable.
    assert(
      output
        .filter(r => ids.take(2).contains(r.researcherId))
        .forall(_.currentCommunityId.contains(candidates.head))
    )
  }

  private def sourceTables: Map[String, DataFrame] = Map(
    "metrics/type=researcher_collaboration" -> analytics.metrics,
    "metrics/type=community_summaries" -> analytics.communitySummaries,
    "path-evidence" -> analytics.paths,
    "nodes/type=work_sources" -> Phase6FGJobs.workSources(canonical)
  )

  test(
    "all four factual summary templates trace every number and fact to the exact source row/field"
  ) {
    val summaries = finalJobs.summaries.toJSON
      .collect()
      .toVector
      .map(CoreJson.parse[SemanticSummary](_).toOption.get)
    assert(
      summaries.map(_.summaryType).toSet == Set(
        "researcher-profile",
        "community",
        "collaboration-path",
        "paper"
      )
    )
    val number = "(?<![A-Za-z0-9])[-]?[0-9]+(?:\\.[0-9]+)?".r
    summaries.foreach { summary =>
      assert(SparkAnalyticsValidation.check(summary).isRight, CoreJson.compact(summary))
      assert(summary.text.length < 1200)
      assert(summary.context.runId == sparkRunId && summary.context.lineage == lineage)
      val numericReferences = summary.sourceReferences.flatMap { ref =>
        val table = sourceTables.getOrElse(ref.table, fail(s"unknown reference table ${ref.table}"))
        val keyColumn = ref.table match {
          case "metrics/type=researcher_collaboration" | "metrics/type=kcore" => "researcherId"
          case "metrics/type=community_summaries"                             => "communityId"
          case "path-evidence"                                                => "pathEvidenceId"
          case "nodes/type=work_sources"                                      => "workId"
        }
        val windowed = table.columns.contains("windowId")
        val expectedKey =
          if (windowed) s"${summary.context.windowId.get}/${summary.entityId}" else summary.entityId
        assert(ref.rowKey == expectedKey, ref.toString)
        val candidates = table.filter(col(keyColumn) === summary.entityId)
        val selected =
          if (windowed) candidates.filter(col("windowId") === summary.context.windowId.get)
          else candidates
        val values = selected.select(col(ref.field)).distinct().collect().map(_.get(0)).toVector
        assert(values.size == 1, s"reference must resolve to one field value: $ref -> $values")
        values.head match {
          case n: java.lang.Number  => Vector(BigDecimal(n.toString))
          case b: java.lang.Boolean => assert(summary.text.contains(b.toString)); Vector.empty
          case text: String =>
            assert(summary.text.contains(text)); number.findAllIn(text).map(BigDecimal(_)).toVector
          case null =>
            assert(summary.text.contains("absent") || summary.text.contains("unknown"));
            Vector.empty
          case value => fail(s"unexpected summary reference value $value")
        }
      }
      val stated = number.findAllIn(summary.text).map(BigDecimal(_)).toVector
      assert(
        stated.sorted == numericReferences.sorted,
        s"unreferenced numeric claim: ${summary.text} vs $numericReferences"
      )
      assert(!"(?i)best|leading|top ranked|world.class".r.findFirstIn(summary.text).isDefined)
    }
  }

  private def rejected: DataFrame = spark.createDataFrame(
    java.util.Collections.emptyList[org.apache.spark.sql.Row](),
    new org.apache.spark.sql.types.StructType()
      .add("sourceKind", "string")
      .add("sourcePath", "string")
      .add("rawLine", "string")
      .add("reason", "string")
  )

  private def validatePublished(name: String, table: DataFrame): Unit = {
    table.toJSON.collect().foreach { json =>
      def check[A: upickle.default.ReadWriter](validation: A => Either[?, A]): Unit = {
        val parsed = CoreJson.parse[A](json)
        assert(parsed.isRight, s"$name: $parsed; $json")
        assert(
          validation(parsed.toOption.get).isRight,
          s"$name: ${validation(parsed.toOption.get)}; $json"
        )
      }
      name match {
        case "nodes/type=work_sources" =>
          val row = ujson.read(json)
          assert(StableIds.parseWorkId(row("workId").str).isRight)
          assert(row("title").str.nonEmpty)
          assert(row("schemaVersion").str == SchemaVersions.sparkAnalytics)
          assert(
            CoreJson
              .parse[SparkRecordContext](row("context").render())
              .toOption
              .get
              .runId == sparkRunId
          )
        case n if n.startsWith("nodes/") => check[GraphNode](DomainValidation.check)
        case n if n.startsWith("edges/") && !n.contains("coauthored_with") =>
          check[GraphEdge](DomainValidation.check)
        case "edges/type=coauthored_with" =>
          check[SparkCoauthorEdge](SparkAnalyticsValidation.check)
        case "edges/type=coauthored_with_support" =>
          check[CoauthorEdgeSupport](SparkAnalyticsValidation.check)
        case "metrics/type=researcher_collaboration" | "metrics/type=kcore" =>
          check[ResearcherMetricsDetail](SparkAnalyticsValidation.check)
        case "metrics/type=components" => check[ComponentMembership](SparkAnalyticsValidation.check)
        case "metrics/type=component_summaries" =>
          check[ComponentSummary](SparkAnalyticsValidation.check)
        case "metrics/type=communities" =>
          check[CommunityMembership](SparkAnalyticsValidation.check)
        case "metrics/type=community_summaries" =>
          check[CommunitySummary](SparkAnalyticsValidation.check)
        case "metrics/type=cross_community_edges" =>
          check[CrossCommunityEdge](SparkAnalyticsValidation.check)
        case "metrics/type=bridges" =>
          check[ResearcherBridgeMetrics](SparkAnalyticsValidation.check)
        case "metrics/type=temporal_changes" =>
          check[TemporalChange](SparkAnalyticsValidation.check)
        case "metrics/type=path_length_estimate" =>
          check[PathLengthEstimate](SparkAnalyticsValidation.check)
        case "path-evidence"        => check[PathEvidence](SparkAnalyticsValidation.check)
        case "semantic-summaries"   => check[SemanticSummary](SparkAnalyticsValidation.check)
        case "integrity/violations" => check[IntegrityViolation](SparkAnalyticsValidation.check)
        case "integrity/rejects"    => fail("synthetic G1 input must not reject rows")
        case other                  => fail(s"unvalidated exported dataset: $other")
      }
    }
  }

  private def exportRoot: Path = root.resolve("complete-export")
  private lazy val exported = Phase6Export.publish(
    spark,
    config,
    canonical,
    analytics,
    finalJobs,
    rejected,
    lineage,
    sparkRunId,
    ujson.Obj(),
    exportRoot
  )

  test(
    "complete export rereads every table, validates declared core records and binds four manifests to paths counts and hashes"
  ) {
    val out = exportRoot
    val inputs = Phase6Export
      .tables(canonical, analytics, finalJobs, rejected, lineage, sparkRunId)
      .map { case (name, frame, _, windowed) =>
        name -> (if (windowed) frame.withColumnRenamed("windowId", "window") else frame)
      }
      .toMap
    val expectedNames =
      Set("researcher", "author_mention", "work", "venue", "institution", "topic", "work_sources")
        .map("nodes/type=" + _) ++
        Set(
          "authored",
          "resolves_to",
          "published_in",
          "affiliated_with",
          "has_topic",
          "coauthored_with",
          "coauthored_with_support"
        ).map("edges/type=" + _) ++
        Set(
          "researcher_collaboration",
          "components",
          "component_summaries",
          "communities",
          "community_summaries",
          "cross_community_edges",
          "bridges",
          "kcore",
          "temporal_changes",
          "path_length_estimate"
        ).map("metrics/type=" + _) ++
        Set("path-evidence", "semantic-summaries", "integrity/violations", "integrity/rejects")
    assert(exported.map(_.name).toSet == expectedNames)
    exported.foreach { item =>
      val path = out.resolve(item.path)
      assert(Files.isDirectory(path), item.toString)
      val windowed =
        item.name.startsWith("metrics/") || Set("path-evidence", "semantic-summaries").contains(
          item.name
        )
      assert(
        item.partitions == (if (windowed) Vector("window", "run_id") else Vector("run_id")),
        item.name
      )
      val read = spark.read.parquet(path.toString).drop("run_id")
      assert(read.count() == item.rowCount, item.name)
      assert(Phase6Export.logicalTableHash(read) == item.contentHash, item.name)
      assert(read.columns.toSet == inputs(item.name).columns.toSet, item.name)
      assert(
        read.select(inputs(item.name).columns.map(col)*).exceptAll(inputs(item.name)).count() == 0L,
        item.name
      )
      assert(
        inputs(item.name).exceptAll(read.select(inputs(item.name).columns.map(col)*)).count() == 0L,
        item.name
      )
      validatePublished(item.name, read)
    }
    val counterRows = ujson.read(Files.readString(out.resolve("counters.json"), UTF_8)).arr
    assert(counterRows.nonEmpty)
    counterRows.foreach { raw =>
      val parsed = CoreJson.parse[SparkCounter](raw.render())
      assert(parsed.isRight, parsed.toString)
      val counter = parsed.toOption.get
      assert(SparkAnalyticsValidation.check(counter).isRight)
      assert(counter.context.runId == sparkRunId && counter.context.lineage == lineage)
    }
    Vector("neptune", "dynamodb", "s3vectors", "s3").foreach { target =>
      val json = ujson.read(Files.readString(out.resolve(s"load-manifests/$target.json"), UTF_8))
      assert(json.arr.nonEmpty)
      json.arr.foreach { raw =>
        val manifest = CoreJson.parse[LoadManifest](raw.render()).toOption.get
        assert(SparkAnalyticsValidation.check(manifest).isRight)
        assert(manifest.targetStore == target && manifest.intendedLoaderOwner == "storage-engineer")
        if (target == "neptune") assert(manifest.logicalDataset != "nodes/type=work_sources")
        val table = exported.find(_.name == manifest.logicalDataset).get
        assert(
          manifest.rowCount == table.rowCount && manifest.sortedRowsSha256 == table.contentHash
        )
        assert(manifest.paths.forall(p => Files.isDirectory(out.resolve(p))))
        assert(manifest.partitionColumns == table.partitions && manifest.keyColumns == table.keys)
      }
    }
  }

  test(
    "replay changes physical partition count and output root while every logical table hash stays identical"
  ) {
    val replayConfig =
      config.copy(outputRoot = root.resolve("replay-export").toString, shufflePartitions = 2)
    assert(config.logicalFingerprint == replayConfig.logicalFingerprint)
    spark.conf.set("spark.sql.shuffle.partitions", "2")
    try {
      val c = Phase6CJobs.build(
        spark,
        replayConfig,
        IndependentPhase6FGFixtures.input(spark),
        lineage,
        sparkRunId
      )
      val de = Phase6DEJobs.build(spark, replayConfig, c, lineage, sparkRunId)
      val fg = Phase6FGJobs.build(spark, replayConfig, c, de, lineage, sparkRunId)
      val replay = Phase6Export.publish(
        spark,
        replayConfig,
        c,
        de,
        fg,
        rejected,
        lineage,
        sparkRunId,
        ujson.Obj(),
        Path.of(replayConfig.outputRoot)
      )
      val before = exported.map(t => t.name -> t).toMap
      assert(before.keySet == replay.map(_.name).toSet)
      replay.foreach { table =>
        assert(before(table.name).rowCount == table.rowCount, table.name)
        assert(before(table.name).contentHash == table.contentHash, table.name)
        assert(Files.isDirectory(Path.of(replayConfig.outputRoot).resolve(table.path)))
      }
    } finally spark.conf.set("spark.sql.shuffle.partitions", "4")
  }
}
