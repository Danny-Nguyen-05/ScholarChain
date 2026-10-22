package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{Phase6CResult, Phase6DEJobs}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Black-box jobs 3–8 tests. Expectations below are literal calculations from phase6.md §8. */
class IndependentPhase6DEGraphSpec extends AnyFunSuite with BeforeAndAfterAll {
  import IndependentPhase6G1.*

  private var spark: SparkSession = _
  private var root: Path = _

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("scholarchain-independent-6de-")
    spark = SparkSession
      .builder()
      .appName("ScholarChain independent 6D+6E graphs")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
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

  private def frame(columns: Seq[(String, DataType)], values: Seq[Seq[Any]]): DataFrame =
    spark.createDataFrame(
      values.map(Row.fromSeq).asJava,
      StructType(columns.map { case (name, dataType) => StructField(name, dataType) })
    )

  private val str = StringType
  private val num = IntegerType
  private val arr = ArrayType(StringType, containsNull = false)

  private def config(
      maxHops: Int = 6,
      componentIterations: Int = 50,
      coreIterations: Int = 50,
      communityIterations: Int = 1,
      maxWorkLimit: Int = 10,
      pairs: Vector[BenchmarkPair] = Vector.empty
  ): SparkAnalyticsConfig = {
    val stream = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    assert(stream != null)
    val loaded =
      try
        SparkAnalyticsConfigLoader
          .loadText(new String(stream.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8))
          .toOption
          .get
      finally stream.close()
    loaded.copy(
      windows = Vector(windows.head),
      identityPolicyVersion = identityPolicy,
      representativePolicyVersion = representativePolicy,
      graphPolicyVersion = graphPolicy,
      componentMaxIterations = componentIterations,
      communityMaxIterations = communityIterations,
      kCoreMaxIterations = coreIterations,
      checkpointInterval = 5,
      checkpointDirectory = root.resolve("checkpoints").toString,
      outputRoot = root.resolve("output").toString,
      maxHops = maxHops,
      benchmarkPairs = pairs,
      sampledPathPairCount = 0,
      pathSampleSourceCount = 1,
      maxTeamWorkLimit = maxWorkLimit,
      shufflePartitions = 4
    )
  }

  private val lineage = SparkLineage(
    hadoopRunId,
    snapshot,
    erRunId,
    erPolicy,
    erPolicyHash,
    Vector.empty,
    Vector.empty
  )

  private def graph(
      names: Vector[String],
      works: Vector[(String, Option[Int], Vector[String])],
      links: Vector[(String, String, Long, Vector[String])]
  ): Phase6CResult = {
    val researchers = frame(
      Seq("researcherId" -> str, "displayName" -> str),
      names.map(name => Seq(researcherId(name), name))
    )
    val memberships = frame(
      Seq(
        "canonicalWorkId" -> str,
        "workId" -> str,
        "mentionId" -> str,
        "researcherId" -> str,
        "year" -> num
      ),
      works.flatMap { case (work, year, team) =>
        team.distinct.map(name =>
          Seq(
            work,
            work,
            s"synthetic:$work:$name",
            researcherId(name),
            year.map(Int.box).orNull
          )
        )
      }
    )
    val edges = frame(
      Seq(
        "windowId" -> str,
        "researcherA" -> str,
        "researcherB" -> str,
        "jointPublicationCount" -> LongType,
        "edgeId" -> str,
        "representativeWorkIds" -> arr,
        "firstCollaborationYear" -> num,
        "lastCollaborationYear" -> num
      ),
      links.map { case (left, right, weight, support) =>
        val a = researcherId(left)
        val b = researcherId(right)
        val (low, high) = StableIds.canonicalPair(a, b).toOption.get
        val years = support.flatMap(label => works.find(_._1 == label).flatMap(_._2))
        Seq(
          "all-years",
          low,
          high,
          weight,
          StableIds.sparkCoauthorEdgeId(low, high, windows.head, graphPolicy).toOption.get,
          support.asJava,
          if (years.isEmpty) null else Int.box(years.min),
          if (years.isEmpty) null else Int.box(years.max)
        )
      }
    )
    val support = frame(
      Seq("windowId" -> str, "edgeId" -> str, "workId" -> str, "year" -> num),
      links.flatMap { case (left, right, _, workIds) =>
        val edgeId = StableIds
          .sparkCoauthorEdgeId(researcherId(left), researcherId(right), windows.head, graphPolicy)
          .toOption
          .get
        workIds.map(work =>
          Seq("all-years", edgeId, work, works.find(_._1 == work).flatMap(_._2).map(Int.box).orNull)
        )
      }
    )
    val unused = frame(Seq("unused" -> str), Seq.empty)
    Phase6CResult(
      researchers,
      unused,
      unused,
      unused,
      memberships,
      edges,
      support,
      unused,
      unused,
      unused,
      unused
    )
  }

  private def g1: Phase6CResult = graph(
    ('A' to 'J').map(_.toString).toVector,
    papers.map(p => (canonicalWorkId(p.label), p.year, p.team)),
    expectedEdges
      .filter(_.windowId == "all-years")
      .map(e => (e.left, e.right, e.weight, e.supportingWorks.toVector.sorted.map(canonicalWorkId)))
  )

  private def counter(rows: DataFrame, name: String): Long =
    rows.filter(rows("name") === name).select("value").collect().map(_.getLong(0)).sum

  private def syntheticWork(label: String): String =
    StableIds.workIdFromDblpKey(s"conf/independent-6de/$label").toOption.get

  private def pairGraph(
      names: Vector[String],
      pairs: Vector[(String, String, Long)]
  ): Phase6CResult = {
    val linked = pairs.zipWithIndex.map { case ((left, right, weight), index) =>
      val support = (1L to weight).map(i => syntheticWork(s"$index-$i")).toVector
      (left, right, weight, support)
    }
    val pairedWorks = linked.flatMap { case (left, right, _, support) =>
      support.map(id => (id, Some(2020), Vector(left, right)))
    }
    val incident = pairs.flatMap { case (left, right, _) => Vector(left, right) }.toSet
    val works = pairedWorks ++ names
      .filterNot(incident)
      .map(name => (syntheticWork(s"solo-$name"), Some(2020), Vector(name)))
    graph(names, works, linked)
  }

  test("G1 full hand-computed metrics, components and coreness") {
    val result = Phase6DEJobs.build(spark, config(), g1, lineage, sparkRunId)
    val expected = Vector(
      ("A", 3L, 2L, 4L, 4.0 / 3.0, 2L, Set("w1"), 4L, 2),
      ("B", 3L, 2L, 4L, 4.0 / 3.0, 2L, Set("w1"), 4L, 2),
      ("C", 2L, 3L, 3L, 1.5, 2L, Set("w1"), 3L, 2),
      ("D", 2L, 3L, 3L, 1.5, 2L, Set("w4"), 3L, 2),
      ("E", 2L, 2L, 3L, 1.5, 2L, Set("w4"), 3L, 2),
      ("F", 3L, 3L, 4L, 4.0 / 3.0, 2L, Set("w4"), 4L, 2),
      ("G", 1L, 1L, 1L, 1.0, 1L, Set("w6"), 1L, 1),
      ("H", 1L, 1L, 1L, 1.0, 1L, Set("w7"), 1L, 1),
      ("I", 1L, 1L, 1L, 1.0, 1L, Set("w7"), 1L, 1),
      ("J", 1L, 0L, 0L, 0.0, 0L, Set("w8"), 0L, 0)
    )
    val rows = result.metrics.collect().map(r => r.getAs[String]("researcherId") -> r).toMap
    assert(rows.size == 10)
    expected.foreach { case (name, p, c, t, a, m, workIds, w, core) =>
      val row = rows(researcherId(name))
      assert(row.getAs[Long]("publicationCount") == p, name)
      assert(row.getAs[Long]("distinctCoauthorCount") == c, name)
      assert(row.getAs[Long]("totalCoauthorOccurrences") == t, name)
      assert(math.abs(row.getAs[Double]("averageCoauthorsPerPaper") - a) < 1e-12, name)
      assert(row.getAs[Long]("maximumCoauthorsOnOnePaper") == m, name)
      assert(
        row.getAs[scala.collection.Seq[String]]("maxTeamWorkIds").toSet == workIds.map(
          canonicalWorkId
        ),
        name
      )
      assert(row.getAs[Long]("maxTeamWorkTieCount") == 1L, name)
      assert(row.getAs[Long]("weightedDegree") == w, name)
      assert(
        result.coreness
          .filter(result.coreness("researcherId") === researcherId(name))
          .select("coreness")
          .head()
          .getInt(0) == core,
        name
      )
    }
    val byName = result.components
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r.getAs[String]("componentId"))
      .toMap
    assert(('A' to 'G').map(c => byName(researcherId(c.toString))).distinct.size == 1)
    assert(byName(researcherId("H")) == byName(researcherId("I")))
    assert(byName(researcherId("J")) != byName(researcherId("A")))
    assert(byName(researcherId("H")) != byName(researcherId("A")))
    val summaries = result.componentSummaries.collect().toVector
    assert(summaries.map(_.getAs[Long]("size")).sorted == Vector(1L, 2L, 7L))
    assert(summaries.map(_.getAs[Double]("largestComponentFraction")).toSet == Set(0.7))
    assert(summaries.map(_.getAs[Long]("singletonCount")).toSet == Set(1L))
    val groupedCommunities = result.communities.collect().groupBy(_.getAs[String]("communityId"))
    assert(
      groupedCommunities.values.forall(members =>
        members.map(row => byName(row.getAs[String]("researcherId"))).distinct.length == 1
      )
    )
  }

  test("G2 star, G3 K4, G4 path and isolated node have exact coreness") {
    val starNames = Vector("Hub", "Leaf1", "Leaf2", "Leaf3", "Leaf4", "Leaf5")
    val star = pairGraph(starNames, starNames.tail.map(name => ("Hub", name, 1L)))
    val starResult = Phase6DEJobs.build(spark, config(maxWorkLimit = 2), star, lineage, sparkRunId)
    val starMetrics =
      starResult.metrics.collect().map(r => r.getAs[String]("researcherId") -> r).toMap
    assert(starMetrics(researcherId("Hub")).getAs[Long]("distinctCoauthorCount") == 5L)
    assert(starMetrics(researcherId("Hub")).getAs[Long]("maxTeamWorkTieCount") == 5L)
    assert(
      starMetrics(researcherId("Hub"))
        .getAs[scala.collection.Seq[String]]("maxTeamWorkIds")
        .size == 2
    )
    assert(
      starNames.forall(name =>
        starResult.coreness
          .filter(starResult.coreness("researcherId") === researcherId(name))
          .select("coreness")
          .head()
          .getInt(0) == 1
      )
    )

    val cliqueNames = Vector("K1", "K2", "K3", "K4")
    val cliquePairs = for {
      a <- cliqueNames.indices
      b <- (a + 1) until cliqueNames.size
    } yield (cliqueNames(a), cliqueNames(b), 1L)
    val cliqueResult = Phase6DEJobs.build(
      spark,
      config(),
      pairGraph(cliqueNames, cliquePairs.toVector),
      lineage,
      sparkRunId
    )
    assert(
      cliqueResult.coreness.collect().toVector.map(_.getAs[Int]("coreness")) ==
        Vector.fill(4)(3)
    )

    val pathNames = Vector("P1", "P2", "P3", "P4", "Alone")
    val pathResult = Phase6DEJobs.build(
      spark,
      config(pairs =
        Vector(
          BenchmarkPair("P1", "P2", "dblp-name"),
          BenchmarkPair("P1", "P3", "dblp-name"),
          BenchmarkPair("P1", "P4", "dblp-name")
        )
      ),
      pairGraph(
        pathNames,
        Vector(("P1", "P2", 1L), ("P2", "P3", 1L), ("P3", "P4", 1L))
      ),
      lineage,
      sparkRunId
    )
    val pathCores = pathResult.coreness
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r.getAs[Int]("coreness"))
      .toMap
    assert(pathNames.init.forall(name => pathCores(researcherId(name)) == 1))
    assert(pathCores(researcherId("Alone")) == 0)
    assert(
      pathResult.componentSummaries.collect().map(_.getAs[Long]("size")).sorted.toVector ==
        Vector(1L, 4L)
    )
    val distances = pathResult.paths
      .collect()
      .map(row => row.getAs[String]("targetResearcherId") -> row.getAs[Int]("hopCount"))
      .toMap
    assert(
      distances == Map(
        researcherId("P2") -> 1,
        researcherId("P3") -> 2,
        researcherId("P4") -> 3
      )
    )
  }

  test("G1 selected paths have unique shortest route, no-path status and supported hop evidence") {
    val pairs = Vector(
      BenchmarkPair("A", "G", "dblp-name"),
      BenchmarkPair("A", "H", "dblp-name"),
      BenchmarkPair("A", "D", "dblp-name"),
      BenchmarkPair("B", "F", "dblp-name")
    )
    val result = Phase6DEJobs.build(spark, config(pairs = pairs), g1, lineage, sparkRunId)
    val paths = result.paths
      .collect()
      .map(r => (r.getAs[String]("sourceResearcherId"), r.getAs[String]("targetResearcherId")) -> r)
      .toMap
    val ag = paths((researcherId("A"), researcherId("G")))
    assert(ag.getAs[String]("status") == "found")
    assert(ag.getAs[Int]("hopCount") == 4)
    assert(
      ag.getAs[scala.collection.Seq[String]]("orderedResearcherIds") ==
        Seq("A", "C", "D", "F", "G").map(researcherId)
    )
    val validSupports = g1.support
      .select("edgeId", "workId")
      .collect()
      .map(r => (r.getString(0), r.getString(1)))
      .toSet
    ag.getAs[scala.collection.Seq[Row]]("hops").foreach { hop =>
      val edgeId = hop.getAs[String]("edgeId")
      assert(hop.getAs[scala.collection.Seq[String]]("representativeWorkIds").nonEmpty)
      assert(
        hop
          .getAs[scala.collection.Seq[String]]("representativeWorkIds")
          .forall(work => validSupports.contains((edgeId, work)))
      )
    }
    val ah = paths((researcherId("A"), researcherId("H")))
    assert(ah.getAs[String]("status") == "no-path")
    assert(ah.isNullAt(ah.fieldIndex("hopCount")))
    assert(paths((researcherId("A"), researcherId("D"))).getAs[Int]("hopCount") == 2)
    assert(paths((researcherId("B"), researcherId("F"))).getAs[Int]("hopCount") == 3)

    val limited = Phase6DEJobs.build(
      spark,
      config(maxHops = 2, pairs = Vector(BenchmarkPair("A", "G", "dblp-name"))),
      g1,
      lineage,
      sparkRunId
    )
    assert(limited.paths.head().getAs[String]("status") == "exceeded-maxHops")
  }

  test("equal-length BFS routes choose the smallest immediate predecessor") {
    val source = "TieSource"
    val target = "TieTarget"
    val first = Vector("First1", "First2").sortBy(researcherId)
    val predecessors = Vector("Prior1", "Prior2").sortBy(researcherId)
    val lowerFirst = first.head
    val higherFirst = first.last
    val lowerPredecessor = predecessors.head
    val higherPredecessor = predecessors.last
    // Both routes are length three. Whole-path lexical order prefers lowerFirst, whereas
    // §7.6's immediate-predecessor rule prefers lowerPredecessor on the other route.
    val input = pairGraph(
      Vector(source, target) ++ first ++ predecessors,
      Vector(
        (source, lowerFirst, 1L),
        (lowerFirst, higherPredecessor, 1L),
        (higherPredecessor, target, 1L),
        (source, higherFirst, 1L),
        (higherFirst, lowerPredecessor, 1L),
        (lowerPredecessor, target, 1L)
      )
    )
    val result = Phase6DEJobs.build(
      spark,
      config(pairs = Vector(BenchmarkPair(source, target, "dblp-name"))),
      input,
      lineage,
      sparkRunId
    )
    val path = result.paths.head()
    assert(path.getAs[String]("status") == "found")
    assert(path.getAs[Int]("hopCount") == 3)
    assert(
      path.getAs[scala.collection.Seq[String]]("orderedResearcherIds") ==
        Seq(source, higherFirst, lowerPredecessor, target).map(researcherId)
    )
    val finalHop = path.getAs[scala.collection.Seq[Row]]("hops").last
    assert(finalHop.getAs[String]("fromResearcherId") == researcherId(lowerPredecessor))
  }

  test("G1 bridges under the declared partition and G2 star leaves") {
    val partition = frame(
      Seq("windowId" -> str, "researcherId" -> str, "communityId" -> str),
      Vector(
        "A" -> "left",
        "B" -> "left",
        "C" -> "left",
        "D" -> "right",
        "E" -> "right",
        "F" -> "right",
        "G" -> "right",
        "H" -> "other",
        "I" -> "other",
        "J" -> "solo"
      ).map { case (name, community) => Seq("all-years", researcherId(name), community) }
    )
    val bridges = Phase6DEJobs
      .bridgeMeasures(config(), g1.edges, partition, lineage, sparkRunId)
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r)
      .toMap
    for (name <- Vector("C", "D")) {
      val row = bridges(researcherId(name))
      assert(row.getAs[Long]("crossCommunityDegree") == 1L)
      assert(row.getAs[Long]("crossCommunityWeight") == 1L)
      assert(row.getAs[Long]("communitiesConnected") == 1L)
      assert(math.abs(row.getAs[Double]("participationCoefficient") - 4.0 / 9.0) < 1e-12)
    }
    assert(bridges(researcherId("A")).getAs[Long]("crossCommunityDegree") == 0L)
    assert(bridges(researcherId("J")).getAs[Double]("participationCoefficient") == 0.0)

    val starNames = Vector("Hub", "Leaf1", "Leaf2", "Leaf3", "Leaf4", "Leaf5")
    val star = pairGraph(starNames, starNames.tail.map(name => ("Hub", name, 1L)))
    val starPartition = frame(
      Seq("windowId" -> str, "researcherId" -> str, "communityId" -> str),
      starNames.map(name => Seq("all-years", researcherId(name), name))
    )
    val starBridges = Phase6DEJobs
      .bridgeMeasures(config(), star.edges, starPartition, lineage, sparkRunId)
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r)
      .toMap
    assert(starBridges(researcherId("Hub")).getAs[Long]("crossCommunityDegree") == 5L)
    assert(starBridges(researcherId("Hub")).getAs[Long]("communitiesConnected") == 5L)
    assert(
      math.abs(
        starBridges(researcherId("Hub"))
          .getAs[Double]("participationCoefficient") - 0.8
      ) < 1e-12
    )
    assert(
      starNames.tail.forall(name =>
        starBridges(researcherId(name)).getAs[Double]("participationCoefficient") == 0.0
      )
    )
  }

  test("weighted synchronous LPA converges to the hand-traced two-clique partition") {
    val groupOne = Vector("L1", "L2", "L3", "L4")
    val groupTwo = Vector("R1", "R2", "R3", "R4")
    def internal(names: Vector[String]): Vector[(String, String, Long)] =
      (for {
        a <- names.indices
        b <- (a + 1) until names.size
      } yield (names(a), names(b), 2L)).toVector
    val graphInput = pairGraph(
      groupOne ++ groupTwo,
      internal(groupOne) ++ internal(groupTwo) :+ ("L1", "R1", 1L)
    )

    // Let p0<p1<p2<p3 be each clique's researcher IDs. At t0 every node has its own label.
    // Internal weights are 2; the only cross-clique vote has weight 1, so it cannot win at t1.
    // At t1 p0 adopts p1, while p1/p2/p3 adopt p0. At t2 every node adopts p0. At t3 no
    // label changes. Both cliques therefore converge separately, independent of row order.
    val result = Phase6DEJobs.build(
      spark,
      config(communityIterations = 4),
      graphInput,
      lineage,
      sparkRunId
    )
    val communityIds = result.communities
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r.getAs[String]("communityId"))
      .toMap
    assert(groupOne.map(name => communityIds(researcherId(name))).distinct.size == 1)
    assert(groupTwo.map(name => communityIds(researcherId(name))).distinct.size == 1)
    assert(communityIds(researcherId("L1")) != communityIds(researcherId("R1")))
    assert(
      result.communitySummaries.collect().map(_.getAs[Long]("size")).sorted.toVector ==
        Vector(4L, 4L)
    )
    assert(result.communitySummaries.collect().forall(_.getAs[Boolean]("converged")))
  }

  test("component iteration guard and weighted-degree invariant reject incorrect graphs") {
    val path = pairGraph(
      Vector("N1", "N2", "N3", "N4"),
      Vector(("N1", "N2", 1L), ("N2", "N3", 1L), ("N3", "N4", 1L))
    )
    val nonConverging = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(componentIterations = 1), path, lineage, sparkRunId)
    }
    assert(nonConverging.getMessage.contains("components did not converge"))

    val starNames = Vector("GuardHub", "Guard1", "Guard2", "Guard3", "Guard4")
    val star = pairGraph(starNames, starNames.tail.map(name => ("GuardHub", name, 1L)))
    val coreGuard = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(coreIterations = 1), star, lineage, sparkRunId)
    }
    assert(coreGuard.getMessage.contains("k-core did not converge"))

    val valid = g1
    val bad = valid.copy(edges =
      valid.edges.withColumn(
        "jointPublicationCount",
        org.apache.spark.sql.functions
          .when(
            valid.edges("researcherA") === researcherId("A") ||
              valid.edges("researcherB") === researcherId("A"),
            valid.edges("jointPublicationCount") + 1L
          )
          .otherwise(valid.edges("jointPublicationCount"))
      )
    )
    val mismatch = intercept[IllegalArgumentException] {
      Phase6DEJobs.build(spark, config(), bad, lineage, sparkRunId)
    }
    assert(mismatch.getMessage.contains("W_r != T_r"))
  }

  test("empty graph and one solo publication have no edges and finite measures") {
    val empty = Phase6DEJobs.build(
      spark,
      config(),
      graph(Vector.empty, Vector.empty, Vector.empty),
      lineage,
      sparkRunId
    )
    assert(empty.metrics.count() == 0L)
    assert(empty.components.count() == 0L)
    assert(empty.coreness.count() == 0L)

    val single = Phase6DEJobs.build(
      spark,
      config(),
      graph(Vector("Solo"), Vector((syntheticWork("solo"), None, Vector("Solo"))), Vector.empty),
      lineage,
      sparkRunId
    )
    val metric = single.metrics.head()
    assert(metric.getAs[Long]("publicationCount") == 1L)
    assert(metric.getAs[Long]("distinctCoauthorCount") == 0L)
    assert(metric.getAs[Long]("totalCoauthorOccurrences") == 0L)
    assert(metric.getAs[Double]("averageCoauthorsPerPaper") == 0.0)
    assert(single.coreness.head().getAs[Int]("coreness") == 0)
    assert(single.componentSummaries.head().getAs[Long]("size") == 1L)
  }

  test("a yearless edge stays in all-years and a disconnected pair has no path") {
    val yearlessWork = syntheticWork("yearless")
    val datedWork = syntheticWork("dated")
    val input = graph(
      Vector("YearA", "YearB", "DateA", "DateB"),
      Vector(
        (yearlessWork, None, Vector("YearA", "YearB")),
        (datedWork, Some(2020), Vector("DateA", "DateB"))
      ),
      Vector(
        ("YearA", "YearB", 1L, Vector(yearlessWork)),
        ("DateA", "DateB", 1L, Vector(datedWork))
      )
    )
    val result = Phase6DEJobs.build(
      spark,
      config(pairs = Vector(BenchmarkPair("YearA", "DateA", "dblp-name"))),
      input,
      lineage,
      sparkRunId
    )
    assert(result.metrics.count() == 4L)
    assert(result.componentSummaries.collect().map(_.getAs[Long]("size")).toSet == Set(2L))
    assert(result.paths.head().getAs[String]("status") == "no-path")
  }

  test("two runs on the same G4 graph produce identical metric, core and component rows") {
    val path = pairGraph(
      Vector("Replay1", "Replay2", "Replay3", "Replay4"),
      Vector(("Replay1", "Replay2", 1L), ("Replay2", "Replay3", 1L), ("Replay3", "Replay4", 1L))
    )
    val first = Phase6DEJobs.build(spark, config(), path, lineage, sparkRunId)
    val second = Phase6DEJobs.build(spark, config(), path, lineage, sparkRunId)
    def snapshot(rows: DataFrame): Vector[String] = rows.collect().toVector.map(_.toString).sorted
    assert(snapshot(first.metrics) == snapshot(second.metrics))
    assert(snapshot(first.coreness) == snapshot(second.coreness))
    assert(snapshot(first.components) == snapshot(second.components))
    assert(snapshot(first.componentSummaries) == snapshot(second.componentSummaries))
  }
}
