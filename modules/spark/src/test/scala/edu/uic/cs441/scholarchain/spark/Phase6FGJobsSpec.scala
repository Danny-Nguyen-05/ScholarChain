package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import org.apache.spark.sql.{SparkSession, DataFrame, Row}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class Phase6FGJobsSpec extends AnyFunSuite with BeforeAndAfterAll {
  private var spark: SparkSession = _
  private var root: Path = _
  private val runId = "run:66666666-6666-4666-8666-666666666666"
  private val lineage = SparkLineage(
    "run:77777777-7777-4777-8777-777777777777",
    "module-fg",
    "run:88888888-8888-4888-8888-888888888888",
    "module-er-v1",
    "a" * 64,
    Vector.empty,
    Vector.empty
  )
  private def researcher(name: String) =
    StableIds.researcherIdFromDblpName("identity-v1", name).toOption.get
  private def work(name: String) =
    StableIds.workIdFromDblpKey("conf/module-fg/" + name).toOption.get
  private def mention(name: String, paper: String) = StableIds.mentionId(
    SourceType.Dblp,
    "conf/module-fg/" + paper,
    Vector("A", "B", "C", "D").indexOf(name) + 1
  )
  override protected def beforeAll(): Unit = {
    root = Files.createTempDirectory("scholarchain-fg-")
    spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Phase 6FG module fixture")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.maxPlanStringLength", "65536")
      .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
    spark.sparkContext.setCheckpointDir(root.resolve("checkpoints").toString)
  }
  override protected def afterAll(): Unit = {
    try { if (spark != null) spark.stop() }
    finally {
      if (root != null) {
        val walk = Files.walk(root);
        try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
        finally walk.close()
      }
      super.afterAll()
    }
  }
  private def frame(fields: Seq[(String, DataType)], rows: Seq[Seq[Any]]): DataFrame =
    spark.createDataFrame(
      rows.map(Row.fromSeq).asJava,
      StructType(fields.map((name, kind) => StructField(name, kind)))
    )
  private lazy val config = SparkAnalyticsConfigLoader
    .load(Path.of(getClass.getResource("/scholarchain.spark-analytics-config.v1.json").toURI))
    .toOption
    .get
    .copy(
      windows = Vector(
        SparkWindow("all-years", None, None, None),
        SparkWindow("early", Some(2015), Some(2015), Some(0)),
        SparkWindow("late", Some(2016), Some(2016), Some(1))
      ),
      checkpointDirectory = root.resolve("checkpoints").toString,
      sampledPathPairCount = 0,
      pathSampleSourceCount = 32,
      communityMaxIterations = 3,
      benchmarkPairs = Vector(BenchmarkPair("A", "C", "dblp-name"))
    )
  private val papers = Vector(
    ("p1", 2015, Vector("A", "B")),
    ("p2", 2016, Vector("B", "C")),
    ("p3", 2016, Vector("D"))
  )
  private lazy val raw: Phase6CInput = {
    val works = frame(
      Seq(
        "workId" -> StringType,
        "source" -> StringType,
        "sourceRecordId" -> StringType,
        "year" -> IntegerType,
        "title" -> StringType,
        "doi" -> StringType,
        "arxivId" -> StringType,
        "venueId" -> StringType,
        "snapshot" -> StringType,
        "abstractTextRef" -> StringType
      ),
      papers.map((p, y, _) =>
        Seq(
          work(p),
          "DBLP",
          "conf/module-fg/" + p,
          Int.box(y),
          "Title " + p,
          null,
          null,
          null,
          "module-fg",
          null
        )
      )
    )
    val mentions = frame(
      Seq(
        "mentionId" -> StringType,
        "source" -> StringType,
        "sourceRecordId" -> StringType,
        "nameText" -> StringType,
        "observedOrcid" -> StringType,
        "snapshot" -> StringType
      ),
      papers.flatMap((p, _, names) =>
        names.map(n => Seq(mention(n, p), "DBLP", "conf/module-fg/" + p, n, null, "module-fg"))
      )
    )
    val teams = frame(
      Seq(
        "workId" -> StringType,
        "source" -> StringType,
        "sourceRecordId" -> StringType,
        "memberMentionIds" -> ArrayType(StringType)
      ),
      papers.map((p, _, names) =>
        Seq(work(p), "DBLP", "conf/module-fg/" + p, names.map(n => mention(n, p)).asJava)
      )
    )
    val pairs = frame(
      Seq(
        "workId" -> StringType,
        "source" -> StringType,
        "sourceRecordId" -> StringType,
        "leftMentionId" -> StringType,
        "rightMentionId" -> StringType,
        "year" -> IntegerType
      ),
      papers
        .filter(_._3.size == 2)
        .map((p, y, names) =>
          Seq(
            work(p),
            "DBLP",
            "conf/module-fg/" + p,
            mention(names(0), p),
            mention(names(1), p),
            Int.box(y)
          )
        )
    )
    val links = frame(Seq("leftId" -> StringType, "rightId" -> StringType), Vector.empty)
    val authority = frame(
      Seq("endpointId" -> StringType, "namespace" -> StringType, "value" -> StringType),
      Vector.empty
    )
    Phase6CInput(works, mentions, teams, pairs, links, links, links, links, authority, authority)
  }
  private lazy val canonical = Phase6CJobs.build(spark, config, raw, lineage, runId)
  private lazy val analytics = Phase6DEJobs.build(spark, config, canonical, lineage, runId)
  private lazy val fg = Phase6FGJobs.build(spark, config, canonical, analytics, lineage, runId)
  private lazy val rejects = frame(
    Seq(
      "sourceKind" -> StringType,
      "sourcePath" -> StringType,
      "rawLine" -> StringType,
      "reason" -> StringType
    ),
    Vector.empty
  )

  test("bounded-window temporal rows preserve entering and leaving researchers and exact deltas") {
    val rows = fg.temporalChanges.toJSON
      .collect()
      .toVector
      .map(json => CoreJson.parse[TemporalChange](json).toOption.get)
    rows.foreach(r => assert(SparkAnalyticsValidation.check(r).isRight))
    assert(rows.size == 4)
    val b = rows.find(_.researcherId == researcher("B")).get
    assert(b.fromPresent && b.toPresent)
    assert(b.deltaDistinctCoauthors.contains(0L)); assert(b.deltaComponentSize.contains(0L))
    assert(b.deltaAverageCoauthorsPerPaper.contains(0.0));
    assert(b.communityJaccardOverlap.nonEmpty)
    val a = rows.find(_.researcherId == researcher("A")).get
    assert(
      a.fromPresent && !a.toPresent && a.leftLargestComponent && a.deltaDistinctCoauthors.isEmpty
    )
    val c = rows.find(_.researcherId == researcher("C")).get
    assert(
      !c.fromPresent && c.toPresent && c.enteredLargestComponent && c.deltaComponentSize.isEmpty
    )
    assert(rows.forall(r => r.fromWindowId == "early" && r.toWindowId == "late"))
  }
  test("complete seeded-source estimate gives a three-node chain exact mean and empirical P90") {
    val estimate = analytics.pathLengthEstimates
      .filter(col("windowId") === "all-years")
      .toJSON
      .collect()
      .map(j => CoreJson.parse[PathLengthEstimate](j).toOption.get)
    assert(estimate.length == 1)
    assert(estimate(0).sampleSourceCount == 3); assert(estimate(0).reachedPairCount == 6)
    assert(math.abs(estimate(0).meanDistance - 4.0 / 3.0) < 1e-12);
    assert(estimate(0).effectiveDiameterP90 == 2.0)
    assert(SparkAnalyticsValidation.check(estimate(0)).isRight)
    val missing = analytics.counters
      .filter(col("name") === "pathMissingBenchmarkEndpoints")
      .first()
      .getAs[Long]("value")
    assert(missing == 2L)
  }
  test(
    "four factual template types carry resolvable fields, numeric values and core-validated IDs"
  ) {
    val summaries = fg.summaries.toJSON
      .collect()
      .toVector
      .map(j => CoreJson.parse[SemanticSummary](j).toOption.get)
    assert(
      summaries.map(_.summaryType).toSet == Set(
        "researcher-profile",
        "community",
        "collaboration-path",
        "paper"
      )
    )
    assert(summaries.forall(s => s.text.length < 1200 && SparkAnalyticsValidation.check(s).isRight))
    val sources = Map(
      "metrics/type=researcher_collaboration" -> analytics.metrics,
      "metrics/type=community_summaries" -> analytics.communitySummaries,
      "path-evidence" -> analytics.paths,
      "nodes/type=work_sources" -> Phase6FGJobs.workSources(canonical)
    )
    summaries.foreach { summary =>
      summary.sourceReferences.foreach { ref =>
        val table = sources(ref.table)
        val key =
          if (ref.table == "nodes/type=work_sources") col("workId")
          else {
            val id =
              if (ref.table == "path-evidence") "pathEvidenceId"
              else if (ref.table == "metrics/type=community_summaries") "communityId"
              else "researcherId"
            concat_ws("/", col("windowId"), col(id))
          }
        val matches = table.filter(key === ref.rowKey).select(ref.field).collect()
        assert(matches.length == 1, s"missing source reference $ref")
        if (!matches(0).isNullAt(0))
          assert(summary.text.contains(matches(0).get(0).toString), s"uncited rendered field: $ref")
      }
    }
    assert(summaries.filter(_.summaryType == "paper").forall(_.abstractTextIds.isEmpty))
  }
  test(
    "all published Parquet tables reread with stable logical hashes and four valid load manifests"
  ) {
    val output = root.resolve("published")
    val metadata = ujson.Obj()
    val tables = Phase6Export.publish(
      spark,
      config,
      canonical,
      analytics,
      fg,
      rejects,
      lineage,
      runId,
      metadata,
      output
    )
    assert(tables.size >= 25)
    tables.foreach { table =>
      val reread = spark.read.parquet(output.resolve(table.path).toString)
      assert(reread.count() == table.rowCount)
      assert(
        Phase6Export.logicalTableHash(reread.repartition(2), table.keys) == table.contentHash,
        table.name
      )
      val logical =
        if (reread.columns.contains("window"))
          reread.withColumnRenamed("window", "windowId").drop("run_id")
        else reread.drop("run_id")
      Phase6Export.validateTable(table.name, logical)
    }
    Vector("neptune", "dynamodb", "s3vectors", "s3").foreach { store =>
      val manifests = ujson
        .read(Files.readString(output.resolve("load-manifests").resolve(store + ".json"), UTF_8))
        .arr
        .toVector
      assert(manifests.nonEmpty)
      manifests.foreach { json =>
        val m = CoreJson.parse[LoadManifest](json.render()).toOption.get;
        assert(SparkAnalyticsValidation.check(m).isRight); assert(m.targetStore == store)
      }
    }
  }
  test("hard failures retain core violation rows and counters before throwing without completion") {
    val failed = root.resolve("failed")
    val source = root.resolve("bad-integrity.json")
    Files.writeString(
      source,
      CoreJson.compact(
        IntegrityViolation(
          SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, lineage),
          "fixture",
          None,
          "orphan endpoint",
          true,
          Vector.empty
        )
      ) + "\n",
      UTF_8
    )
    val bad = spark.read
      .schema(
        StructType(
          Seq(
            StructField("context", Phase6Context.schema),
            StructField("code", StringType),
            StructField("entityId", StringType),
            StructField("detail", StringType),
            StructField("hardFailure", BooleanType),
            StructField("evidenceRefs", ArrayType(Phase6FGJobs.sourceRefSchema))
          )
        )
      )
      .json(source.toString)
    intercept[IllegalStateException] {
      Phase6Main.failIfHardIntegrity(failed, bad, canonical.counters)
    }
    assert(spark.read.parquet(failed.resolve("integrity/violations").toString).count() == 1)
    assert(Files.isRegularFile(failed.resolve("counters.json")))
    assert(!Files.exists(failed.resolve("_SCHOLARCHAIN_SPARK_COMPLETE")))
  }
  test("JSON event summarizer aggregates stage tasks partitions durations shuffle and failures") {
    val dir = root.resolve("events"); Files.createDirectories(dir)
    val lines = Vector(
      ujson.Obj(
        "Event" -> "SparkListenerTaskEnd",
        "Stage ID" -> 1,
        "Stage Attempt ID" -> 0,
        "Task Info" -> ujson.Obj("Launch Time" -> 10, "Finish Time" -> 30),
        "Task End Reason" -> ujson.Obj("Reason" -> "Success"),
        "Task Metrics" -> ujson.Obj(
          "Executor Run Time" -> 15,
          "Shuffle Read Metrics" -> ujson
            .Obj("Remote Bytes Read" -> 3, "Local Bytes Read" -> 4, "Total Records Read" -> 2),
          "Shuffle Write Metrics" -> ujson
            .Obj("Shuffle Bytes Written" -> 5, "Shuffle Records Written" -> 1)
        )
      ),
      ujson.Obj(
        "Event" -> "SparkListenerStageCompleted",
        "Stage Info" -> ujson.Obj("Stage ID" -> 1, "Stage Attempt ID" -> 0, "Number of Tasks" -> 1)
      )
    )
    Files.writeString(dir.resolve("events"), lines.map(_.render()).mkString("\n") + "\n", UTF_8)
    val stage = Phase6EventLog.summarize(dir)("stages")(0)
    assert(
      stage("tasks").num == 1 && stage("partitionCount").num == 1 && stage("durationMs").num == 20
    )
    assert(
      stage("shuffleReadBytes").num == 7 && stage("shuffleWriteRecords").num == 1 && stage(
        "failedTasks"
      ).num == 0
    )
  }
}
