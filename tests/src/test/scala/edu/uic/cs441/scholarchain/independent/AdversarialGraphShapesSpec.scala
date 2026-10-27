package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{Phase6CResult, Phase6DEJobs}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Synthetic ring, barbell and clique with pendant nodes. Oracles are hand-counted below. */
class AdversarialGraphShapesSpec extends AnyFunSuite with BeforeAndAfterAll {
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

  private val names = Vector(
    "R1",
    "R2",
    "R3",
    "R4",
    "R5",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "K1",
    "K2",
    "K3",
    "K4",
    "P1",
    "P2",
    "I1"
  )
  private val links = Vector(
    ("R1", "R2", 1L),
    ("R2", "R3", 1L),
    ("R3", "R4", 1L),
    ("R4", "R5", 1L),
    ("R5", "R1", 1L),
    ("B1", "B2", 1L),
    ("B2", "B3", 1L),
    ("B3", "B1", 1L),
    ("B3", "B4", 3L),
    ("B4", "B5", 1L),
    ("B5", "B6", 1L),
    ("B6", "B4", 1L),
    ("K1", "K2", 1L),
    ("K1", "K3", 1L),
    ("K1", "K4", 1L),
    ("K2", "K3", 1L),
    ("K2", "K4", 1L),
    ("K3", "K4", 1L),
    ("K1", "P1", 1L),
    ("K1", "P2", 1L)
  )
  private lazy val shapedGraph = pairGraph(names, links)
  private lazy val analytics = Phase6DEJobs.build(
    spark,
    config(pairs =
      Vector(
        BenchmarkPair("R1", "R3", "dblp-name"),
        BenchmarkPair("B1", "B6", "dblp-name"),
        BenchmarkPair("P1", "P2", "dblp-name"),
        BenchmarkPair("R1", "B1", "dblp-name")
      )
    ),
    shapedGraph,
    lineage,
    sparkRunId
  )

  test(
    "ring barbell and clique-pendant graphs have exact degree weighted degree components and coreness"
  ) {
    val expected = Vector(
      ("R1", 2L, 2L, 2),
      ("R2", 2L, 2L, 2),
      ("R3", 2L, 2L, 2),
      ("R4", 2L, 2L, 2),
      ("R5", 2L, 2L, 2),
      ("B1", 2L, 2L, 2),
      ("B2", 2L, 2L, 2),
      ("B3", 3L, 5L, 2),
      ("B4", 3L, 5L, 2),
      ("B5", 2L, 2L, 2),
      ("B6", 2L, 2L, 2),
      ("K1", 5L, 5L, 3),
      ("K2", 3L, 3L, 3),
      ("K3", 3L, 3L, 3),
      ("K4", 3L, 3L, 3),
      ("P1", 1L, 1L, 1),
      ("P2", 1L, 1L, 1),
      ("I1", 0L, 0L, 0)
    )
    val metrics = analytics.metrics.collect().map(r => r.getAs[String]("researcherId") -> r).toMap
    val cores = analytics.coreness
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r.getAs[Int]("coreness"))
      .toMap
    assert(metrics.size == 18 && cores.size == 18)
    expected.foreach { case (name, degree, weight, core) =>
      val id = researcherId(name)
      assert(metrics(id).getAs[Long]("distinctCoauthorCount") == degree, name)
      assert(metrics(id).getAs[Long]("weightedDegree") == weight, name)
      assert(metrics(id).getAs[Long]("totalCoauthorOccurrences") == weight, name)
      assert(cores(id) == core, name)
    }
    assert(
      analytics.componentSummaries.collect().map(_.getAs[Long]("size")).sorted.toVector == Vector(
        1L,
        5L,
        6L,
        6L
      )
    )
    val components = analytics.components
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r.getAs[String]("componentId"))
      .toMap
    val groups = Vector(
      Vector("R1", "R2", "R3", "R4", "R5"),
      Vector("B1", "B2", "B3", "B4", "B5", "B6"),
      Vector("K1", "K2", "K3", "K4", "P1", "P2"),
      Vector("I1")
    )
    assert(groups.forall(group => group.map(n => components(researcherId(n))).distinct.size == 1))
    assert(groups.map(group => components(researcherId(group.head))).distinct.size == 4)
  }

  test("new graph shapes yield hand-derived shortest routes and disconnected no-path evidence") {
    val paths = analytics.paths
      .collect()
      .map(r => (r.getAs[String]("sourceResearcherId"), r.getAs[String]("targetResearcherId")) -> r)
      .toMap
    val expected = Vector(
      ("R1", "R3", 2, Vector("R1", "R2", "R3")),
      ("B1", "B6", 3, Vector("B1", "B3", "B4", "B6")),
      ("P1", "P2", 2, Vector("P1", "K1", "P2"))
    )
    assert(paths.size == 4)
    val supports = shapedGraph.support
      .select("edgeId", "workId")
      .collect()
      .map(r => (r.getString(0), r.getString(1)))
      .toSet
    expected.foreach { case (source, target, distance, route) =>
      val row = paths((researcherId(source), researcherId(target)))
      assert(row.getAs[String]("status") == "found")
      assert(row.getAs[Int]("hopCount") == distance)
      assert(
        row.getAs[scala.collection.Seq[String]]("orderedResearcherIds").toVector == route.map(
          researcherId
        )
      )
      val hops = row.getAs[scala.collection.Seq[Row]]("hops")
      assert(hops.size == distance)
      hops.foreach { hop =>
        val works = hop.getAs[scala.collection.Seq[String]]("representativeWorkIds")
        assert(
          works.nonEmpty && works.forall(work => supports((hop.getAs[String]("edgeId"), work)))
        )
      }
    }
    val disconnected = paths((researcherId("R1"), researcherId("B1")))
    assert(disconnected.getAs[String]("status") == "no-path")
    assert(disconnected.isNullAt(disconnected.fieldIndex("hopCount")))
  }

  test("declared barbell and pendant partitions have exact bridge measures for every node") {
    val partition = frame(
      Seq("windowId" -> str, "researcherId" -> str, "communityId" -> str),
      names.map { name =>
        val community =
          if (name.startsWith("R")) "ring"
          else if (Set("B1", "B2", "B3")(name)) "barbell-left"
          else if (name.startsWith("B")) "barbell-right"
          else if (name.startsWith("K")) "clique"
          else name
        Seq("all-years", researcherId(name), community)
      }
    )
    val rows = Phase6DEJobs
      .bridgeMeasures(config(), shapedGraph.edges, partition, lineage, sparkRunId)
      .collect()
      .map(r => r.getAs[String]("researcherId") -> r)
      .toMap
    assert(rows.size == 18)
    names.foreach { name =>
      val (degree, weight, communities, participation) = name match {
        case "B3" | "B4" => (1L, 3L, 1L, 4.0 / 9.0)
        case "K1"        => (2L, 2L, 2L, 14.0 / 25.0)
        case "P1" | "P2" => (1L, 1L, 1L, 0.0)
        case _           => (0L, 0L, 0L, 0.0)
      }
      val row = rows(researcherId(name))
      assert(row.getAs[Long]("crossCommunityDegree") == degree, name)
      assert(row.getAs[Long]("crossCommunityWeight") == weight, name)
      assert(row.getAs[Long]("communitiesConnected") == communities, name)
      assert(math.abs(row.getAs[Double]("participationCoefficient") - participation) < 1e-12, name)
    }
  }
}
