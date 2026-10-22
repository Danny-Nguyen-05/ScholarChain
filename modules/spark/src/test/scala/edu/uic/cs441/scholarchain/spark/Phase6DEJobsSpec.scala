package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import org.scalatest.{BeforeAndAfterAll, BeforeAndAfterEach}
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class Phase6DEJobsSpec extends AnyFunSuite with BeforeAndAfterAll with BeforeAndAfterEach {
  private var spark: SparkSession = _
  private var root: Path = _
  private val runId = "run:66666666-6666-4666-8666-666666666666"
  private val idPolicy = "module-de-identity-v1"
  private val graphPolicy = "module-de-graph-v1"
  private def researcher(name: String): String =
    StableIds.researcherIdFromDblpName(idPolicy, name).toOption.get
  private def work(name: String): String =
    StableIds.workIdFromDblpKey(s"conf/module-de/$name").toOption.get
  private val lineage = SparkLineage(
    "run:77777777-7777-4777-8777-777777777777",
    "module-de",
    "run:88888888-8888-4888-8888-888888888888",
    "module-er-v1",
    "a" * 64,
    Vector.empty,
    Vector.empty
  )
  private val names = Vector("A", "B", "C", "D", "E")
  private def nameOf(id: String): String = names.find(researcher(_) == id).get

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("scholarchain-spark-6de-")
    spark = SparkSession
      .builder()
      .appName("ScholarChain 6D+6E module fixture")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
    spark.sparkContext.setCheckpointDir(root.resolve("checkpoint").toString)
  }
  override protected def afterEach(): Unit = {
    try spark.catalog.clearCache()
    finally super.afterEach()
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

  private def frame(fields: Seq[(String, DataType)], rows: Seq[Seq[Any]]): DataFrame =
    spark.createDataFrame(
      rows.map(Row.fromSeq).asJava,
      StructType(fields.map((name, kind) => StructField(name, kind)))
    )

  private def config(
      pairs: Vector[BenchmarkPair] = Vector.empty,
      componentMax: Int = 50,
      kCoreMax: Int = 50,
      communityMax: Int = 4,
      maxTeamLimit: Int = 20,
      maxHops: Int = 6
  ): SparkAnalyticsConfig = {
    val source = SparkAnalyticsConfigLoader
      .load(
        Path.of(
          getClass.getResource("/scholarchain.spark-analytics-config.v1.json").toURI
        )
      )
      .toOption
      .get
    source.copy(
      windows = Vector(SparkWindow("all-years", None, None, None)),
      identityPolicyVersion = idPolicy,
      graphPolicyVersion = graphPolicy,
      componentMaxIterations = componentMax,
      kCoreMaxIterations = kCoreMax,
      communityMaxIterations = communityMax,
      checkpointInterval = 5,
      checkpointDirectory = root.resolve("checkpoint").toString,
      benchmarkPairs = pairs,
      sampledPathPairCount = 0,
      maxHops = maxHops,
      maxTeamWorkLimit = maxTeamLimit,
      shufflePartitions = 4
    )
  }

  private def input: Phase6CResult = {
    val memberships = frame(
      Seq(
        "canonicalWorkId" -> StringType,
        "researcherId" -> StringType,
        "year" -> IntegerType
      ),
      Vector(
        ("w1", Vector("A", "B", "C"), 2015),
        ("w2", Vector("C", "D"), 2016),
        ("w3", Vector("E"), 2017)
      ).flatMap { case (paper, members, year) =>
        members.map(name => Seq(work(paper), researcher(name), Int.box(year)))
      }
    )
    val window = SparkWindow("all-years", None, None, None)
    val edges = frame(
      Seq(
        "windowId" -> StringType,
        "researcherA" -> StringType,
        "researcherB" -> StringType,
        "edgeId" -> StringType,
        "jointPublicationCount" -> LongType,
        "representativeWorkIds" -> ArrayType(StringType)
      ),
      Vector(
        ("A", "B", "w1"),
        ("A", "C", "w1"),
        ("B", "C", "w1"),
        ("C", "D", "w2")
      ).map { case (left, right, paper) =>
        val (a, b) = StableIds.canonicalPair(researcher(left), researcher(right)).toOption.get
        Seq(
          "all-years",
          a,
          b,
          StableIds.sparkCoauthorEdgeId(a, b, window, graphPolicy).toOption.get,
          Long.box(1L),
          Vector(work(paper)).asJava
        )
      }
    )
    Phase6CResult(null, null, null, null, memberships, edges, null, null, null, null, null)
  }

  test("jobs 3, 4 and 8 compute numeric metrics, components and exact coreness") {
    val result = Phase6DEJobs.build(spark, config(), input, lineage, runId)
    val rows = BoundedActions
      .capped(
        result.metrics.select(
          "researcherId",
          "publicationCount",
          "distinctCoauthorCount",
          "totalCoauthorOccurrences",
          "weightedDegree",
          "coreness"
        ),
        5
      )
      .map(row => nameOf(row.getString(0)) -> row)
      .toMap
    assert(rows("A").getLong(1) == 1L)
    assert(rows("A").getLong(2) == 2L)
    assert(rows("A").getLong(3) == 2L)
    assert(rows("A").getLong(4) == 2L)
    assert(rows("A").getInt(5) == 2)
    assert(rows("C").getInt(5) == 2)
    assert(rows("D").getInt(5) == 1)
    assert(rows("E").getInt(5) == 0)
    val sizes = BoundedActions
      .capped(result.componentSummaries.select("size"), 2)
      .map(_.getLong(0))
      .sorted
    assert(sizes == Vector(1L, 4L))
    assert(BoundedActions.count(result.paths) == 0L)
    // Retain the uncheckpointed metric aggregation shape, not only a checkpoint scan.
    Phase6DEJobs
      .metricsBase(
        input.memberships.withColumn("windowId", lit("all-years")),
        input.edges,
        config()
      )
      .explain("formatted")
    result.metrics.explain("formatted")
    result.componentSummaries.explain("formatted")
    result.coreness.explain("formatted")
  }

  test("selected BFS returns canonical shortest path and different-component no-path") {
    val pairs = Vector(
      BenchmarkPair(researcher("A"), researcher("D"), "researcher-id"),
      BenchmarkPair(researcher("A"), researcher("E"), "researcher-id")
    )
    val result = Phase6DEJobs.build(spark, config(pairs), input, lineage, runId)
    val rows = BoundedActions
      .capped(
        result.paths
          .select("targetResearcherId", "status", "hopCount", "orderedResearcherIds", "hops"),
        2
      )
      .map(row => nameOf(row.getString(0)) -> row)
      .toMap
    assert(rows("D").getString(1) == "found")
    assert(rows("D").getInt(2) == 2)
    assert(rows("D").getSeq[String](3).map(nameOf) == Seq("A", "C", "D"))
    assert(rows("D").getSeq[Row](4).size == 2)
    assert(rows("E").getString(1) == "no-path")
    assert(rows("E").isNullAt(2))
    result.paths.explain("formatted")
  }

  test("solo average is zero, max-team ties retain full count after work-ID cap") {
    val original = input
    val extraWork = work("w4")
    val added = frame(
      Seq("canonicalWorkId" -> StringType, "researcherId" -> StringType, "year" -> IntegerType),
      Vector("A", "B", "C").map(name => Seq(extraWork, researcher(name), Int.box(2018)))
    )
    val extraEdges = original.edges
      .filter(
        col("researcherA") =!= researcher("D") &&
          col("researcherB") =!= researcher("D")
      )
      .withColumn("jointPublicationCount", lit(2L))
      .withColumn("representativeWorkIds", array(lit(work("w1")), lit(extraWork)))
    val retainedTail = original.edges.filter(
      col("researcherA") === researcher("D") ||
        col("researcherB") === researcher("D")
    )
    val revised = original.copy(
      memberships = original.memberships.unionByName(added),
      edges = extraEdges.unionByName(retainedTail)
    )
    val result = Phase6DEJobs.build(spark, config(maxTeamLimit = 1), revised, lineage, runId)
    val a = result.metrics
      .filter(col("researcherId") === researcher("A"))
      .select("publicationCount", "maxTeamWorkTieCount", "maxTeamWorkIds")
      .head()
    assert(a.getLong(0) == 2L)
    assert(a.getLong(1) == 2L)
    assert(a.getSeq[String](2) == Seq(work("w1"), extraWork).sorted.take(1))
    val e = result.metrics
      .filter(col("researcherId") === researcher("E"))
      .select(
        "publicationCount",
        "averageCoauthorsPerPaper",
        "maximumCoauthorsOnOnePaper",
        "weightedDegree"
      )
      .head()
    assert(e.getLong(0) == 1L)
    assert(e.getDouble(1) == 0.0)
    assert(e.getLong(2) == 0L)
    assert(e.getLong(3) == 0L)
  }

  test("a weighted-degree mismatch fails with the metric invariant") {
    val original = input
    val broken = original.copy(edges =
      original.edges.withColumn("jointPublicationCount", col("jointPublicationCount") + lit(1L))
    )
    val problem = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(), broken, lineage, runId)
    }
    assert(problem.getMessage.contains("W_r != T_r"))
  }

  test("component and k-core iteration limits reject an unfinished fixed point") {
    val component = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(componentMax = 1), input, lineage, runId)
    }
    assert(component.getMessage.contains("components did not converge"))
    val core = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(kCoreMax = 1), input, lineage, runId)
    }
    assert(core.getMessage.contains("k-core did not converge"))
  }

  test("synchronous triangle LPA converges to its minimum initial label") {
    // With IDs x < y < z, iteration 0 is (x,y,z), iteration 1 is (y,x,x),
    // and iteration 2 is (x,x,x). The third comparison reports zero changes.
    val original = input
    val triangle = original.copy(
      memberships = original.memberships.filter(col("canonicalWorkId") === work("w1")),
      edges = original.edges.filter(
        col("researcherA") =!= researcher("D") &&
          col("researcherB") =!= researcher("D")
      )
    )
    val result = Phase6DEJobs.build(spark, config(), triangle, lineage, runId)
    val smallest = Vector("A", "B", "C").map(researcher).min
    val expected =
      StableIds.sparkAnalyticsId("community", graphPolicy, "all-years", Seq(smallest)).toOption.get
    val ids = BoundedActions
      .capped(result.communities.select("communityId"), 3)
      .map(_.getString(0))
    assert(ids == Vector.fill(3)(expected))
    assert(
      BoundedActions
        .capped(
          result.communitySummaries
            .select("converged", "finalChangedCount"),
          1
        )
        .forall(row => row.getBoolean(0) && row.getLong(1) == 0L)
    )
  }

  test("two-person synchronous LPA records non-convergence in core community records") {
    val a = researcher("A")
    val b = researcher("B")
    val original = input
    val twoPerson = original.copy(
      memberships = original.memberships.filter(col("researcherId").isin(a, b)),
      edges = original.edges.filter(
        col("researcherA").isin(a, b) && col("researcherB").isin(a, b)
      )
    )
    // Initial labels (a,b) swap on every synchronous vote. After three rounds
    // both labels still change; the two final communities are singletons.
    val result = Phase6DEJobs.build(spark, config(communityMax = 3), twoPerson, lineage, runId)
    val memberships = result.communities
      .select("context", "researcherId", "communityId", "iterations", "converged")
      .toJSON
      .collect()
      .toVector
      .map(json => CoreJson.parse[CommunityMembership](json).toOption.get)
    assert(memberships.size == 2)
    assert(memberships.forall(row => row.iterations == 3 && !row.converged))
    assert(memberships.forall(row => SparkAnalyticsValidation.check(row).isRight))

    val summaries = result.communitySummaries
      .select("context", "communityId", "size", "iterations", "finalChangedCount", "converged")
      .toJSON
      .collect()
      .toVector
      .map(json => CoreJson.parse[CommunitySummary](json).toOption.get)
    assert(summaries.size == 2)
    assert(
      summaries.forall(row =>
        row.size == 1L && row.iterations == 3 &&
          row.finalChangedCount == 2L && !row.converged
      )
    )
    assert(summaries.forall(row => SparkAnalyticsValidation.check(row).isRight))

    val counters = BoundedActions
      .capped(
        result.counters
          .filter(col("name").isin("communityConverged", "communityFinalChangedCount"))
          .select("name", "value"),
        2
      )
      .map(row => row.getString(0) -> row.getLong(1))
      .toMap
    assert(counters == Map("communityConverged" -> 0L, "communityFinalChangedCount" -> 2L))
  }

  test("a reachable pair beyond maxHops reports exceeded-maxHops without hop evidence") {
    val pair = Vector(BenchmarkPair(researcher("A"), researcher("D"), "researcher-id"))
    val result = Phase6DEJobs.build(spark, config(pair, maxHops = 1), input, lineage, runId)
    val path = BoundedActions
      .capped(result.paths.select("status", "hopCount", "orderedResearcherIds", "hops"), 1)
      .head
    assert(path.getString(0) == "exceeded-maxHops")
    assert(path.isNullAt(1))
    assert(path.getSeq[String](2).isEmpty)
    assert(path.getSeq[Row](3).isEmpty)
  }

  test("seeded sampling chooses a bounded pair from the largest component") {
    val selected = config().copy(sampledPathPairCount = 1, samplingSeed = 441L)
    val result = Phase6DEJobs.build(spark, selected, input, lineage, runId)
    assert(BoundedActions.count(result.paths) == 1L)
    val path = result.paths.select("sourceResearcherId", "targetResearcherId", "status").head()
    assert(nameOf(path.getString(0)) != "E")
    assert(nameOf(path.getString(1)) != "E")
    assert(path.getString(2) == "found")
    val sampledCount = result.counters
      .filter(col("name") === "pathSeededSamplePairs")
      .select("value")
      .head()
      .getLong(0)
    assert(sampledCount == 1L)
  }

  test("equal-length BFS routes choose the smallest immediate predecessor") {
    val ids = Vector("A", "B", "C", "D", "E", "F").map(researcher).sorted
    val source = ids(0)
    val smallPredecessor = ids(1)
    val smallFirstHop = ids(2)
    val largeFirstHop = ids(3)
    val largePredecessor = ids(4)
    val target = ids(5)
    // Whole-path ordering favors smallFirstHop. The plan's predecessor rule instead
    // favors smallPredecessor at target, reached through largeFirstHop.
    val routes = Vector(
      source -> smallFirstHop,
      smallFirstHop -> largePredecessor,
      largePredecessor -> target,
      source -> largeFirstHop,
      largeFirstHop -> smallPredecessor,
      smallPredecessor -> target
    )
    val members = frame(
      Seq(
        "canonicalWorkId" -> StringType,
        "researcherId" -> StringType,
        "year" -> IntegerType
      ),
      routes.zipWithIndex.flatMap { case ((left, right), index) =>
        Vector(left, right).map(id => Seq(work(s"tie-$index"), id, Int.box(2015)))
      }
    )
    val window = SparkWindow("all-years", None, None, None)
    val edges = frame(
      Seq(
        "windowId" -> StringType,
        "researcherA" -> StringType,
        "researcherB" -> StringType,
        "edgeId" -> StringType,
        "jointPublicationCount" -> LongType,
        "representativeWorkIds" -> ArrayType(StringType)
      ),
      routes.zipWithIndex.map { case ((left, right), index) =>
        val (a, b) = StableIds.canonicalPair(left, right).toOption.get
        Seq(
          "all-years",
          a,
          b,
          StableIds.sparkCoauthorEdgeId(a, b, window, graphPolicy).toOption.get,
          Long.box(1L),
          Vector(work(s"tie-$index")).asJava
        )
      }
    )
    val graph = input.copy(memberships = members, edges = edges)
    val pair = BenchmarkPair(source, target, "researcher-id")
    val result = Phase6DEJobs.build(
      spark,
      config(pairs = Vector(pair), communityMax = 1),
      graph,
      lineage,
      runId
    )
    val path = result.paths
      .select("status", "hopCount", "orderedResearcherIds", "hops")
      .head()
    assert(path.getString(0) == "found")
    assert(path.getInt(1) == 3)
    assert(
      path.getSeq[String](2) ==
        Seq(source, largeFirstHop, smallPredecessor, target)
    )
    assert(path.getSeq[Row](3).last.getAs[String]("fromResearcherId") == smallPredecessor)
  }
}
