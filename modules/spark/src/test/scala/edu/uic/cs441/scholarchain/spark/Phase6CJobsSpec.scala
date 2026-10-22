package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.functions.*
import org.apache.spark.sql.types.*
import org.scalatest.{BeforeAndAfterAll, BeforeAndAfterEach}
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable.ArrayBuffer
import scala.jdk.CollectionConverters.*

class Phase6CJobsSpec extends AnyFunSuite with BeforeAndAfterAll with BeforeAndAfterEach {
  private var spark: SparkSession = _
  private var root: Path = _
  private val run = "run:66666666-6666-4666-8666-666666666666"
  private val hadoop = "run:77777777-7777-4777-8777-777777777777"
  private val er = "run:88888888-8888-4888-8888-888888888888"
  private val policy = "module-g1-identity-v1"
  private val graphPolicy = "module-g1-graph-v1"
  private val snapshot = "module-g1-synthetic"

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("scholarchain-spark-6c-")
    spark = SparkSession
      .builder()
      .appName("ScholarChain 6C module fixture")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
      .config("spark.ui.retainedTasks", "100")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
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

  private def frame(fields: Seq[(String, DataType)], values: Seq[Seq[Any]]): DataFrame =
    spark.createDataFrame(
      values.map(Row.fromSeq).asJava,
      StructType(fields.map((name, dataType) => StructField(name, dataType)))
    )
  private def append(table: DataFrame, values: Seq[Any]): DataFrame =
    table.unionByName(spark.createDataFrame(Vector(Row.fromSeq(values)).asJava, table.schema))
  private def lineage: SparkLineage =
    SparkLineage(hadoop, snapshot, er, "module-er-v1", "a" * 64, Vector.empty, Vector.empty)
  private def counter(result: Phase6CResult, name: String): Long = result.counters
    .filter(col("name") === name)
    .select("value")
    .head()
    .getLong(0)

  private case class Paper(label: String, year: Option[Int], members: Vector[String])
  private val papers = Vector(
    Paper("w1", Some(2015), Vector("A", "B", "C")),
    Paper("w2", Some(2016), Vector("A", "B")),
    Paper("w9", Some(2016), Vector("A", "A", "B")),
    Paper("w3", Some(2017), Vector("C", "D")),
    Paper("w4", Some(2018), Vector("D", "E", "F")),
    Paper("w5", Some(2019), Vector("E", "F")),
    Paper("w6", Some(2020), Vector("F", "G")),
    Paper("w7", Some(2020), Vector("H", "I")),
    Paper("w8", Some(2021), Vector("J"))
  )
  private def workId(label: String): String =
    StableIds.workIdFromDblpKey(s"conf/module-g1/$label").toOption.get
  private def mention(label: String, ordinal: Int): String =
    StableIds.mentionId(SourceType.Dblp, s"conf/module-g1/$label", ordinal)
  private def researcher(name: String): String =
    StableIds.researcherIdFromDblpName(policy, name).toOption.get

  private def input: Phase6CInput = {
    val crossrefId = StableIds.workIdFromDoi("10.5555/module-g1-w1").toOption.get
    val crossrefRecord = "10.5555/module-g1-w1"
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
        "snapshot" -> StringType
      ),
      papers.map(p =>
        Seq(
          workId(p.label),
          "DBLP",
          s"conf/module-g1/${p.label}",
          p.year.map(Int.box).orNull,
          p.label,
          null,
          null,
          null,
          snapshot
        )
      ) :+
        Seq(
          crossrefId,
          "CROSSREF",
          crossrefRecord,
          Int.box(2015),
          "w1 duplicate",
          crossrefRecord,
          null,
          null,
          snapshot
        )
    )
    val dblpMentions = papers.flatMap(p =>
      p.members.zipWithIndex.map((name, index) =>
        Seq(mention(p.label, index + 1), "DBLP", s"conf/module-g1/${p.label}", name, null, snapshot)
      )
    )
    val crossrefMentions = Vector("A", "B", "C").zipWithIndex.map((name, index) =>
      Seq(
        StableIds.mentionId(SourceType.Crossref, crossrefRecord, index + 1),
        "CROSSREF",
        crossrefRecord,
        name,
        null,
        snapshot
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
      dblpMentions ++ crossrefMentions
    )
    val teams = frame(
      Seq(
        "workId" -> StringType,
        "source" -> StringType,
        "sourceRecordId" -> StringType,
        "memberMentionIds" -> ArrayType(StringType, containsNull = false)
      ),
      papers.map(p =>
        Seq(
          workId(p.label),
          "DBLP",
          s"conf/module-g1/${p.label}",
          p.members.indices.map(index => mention(p.label, index + 1)).asJava
        )
      ) :+
        Seq(
          crossrefId,
          "CROSSREF",
          crossrefRecord,
          (1 to 3).map(i => StableIds.mentionId(SourceType.Crossref, crossrefRecord, i)).asJava
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
      papers.flatMap(p =>
        for (
          left <- p.members.indices;
          right <- (left + 1) until p.members.size
        )
          yield Seq(
            workId(p.label),
            "DBLP",
            s"conf/module-g1/${p.label}",
            mention(p.label, left + 1),
            mention(p.label, right + 1),
            p.year.map(Int.box).orNull
          )
      )
    )
    val pairShape = Seq("leftId" -> StringType, "rightId" -> StringType)
    val authorityShape =
      Seq("endpointId" -> StringType, "namespace" -> StringType, "value" -> StringType)
    Phase6CInput(
      works,
      mentions,
      teams,
      pairs,
      frame(
        pairShape,
        (1 to 3).map(i =>
          Seq(mention("w1", i), StableIds.mentionId(SourceType.Crossref, crossrefRecord, i))
        )
      ),
      frame(pairShape, Seq(Seq(workId("w1"), crossrefId))),
      frame(pairShape, Seq.empty),
      frame(pairShape, Seq.empty),
      frame(authorityShape, Seq.empty),
      frame(authorityShape, Seq.empty)
    )
  }

  private def config: SparkAnalyticsConfig = {
    val stream = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    val text =
      try new String(stream.readAllBytes(), UTF_8)
      finally stream.close()
    SparkAnalyticsConfigLoader
      .loadText(text)
      .toOption
      .get
      .copy(
        windows = Vector(
          SparkWindow("all-years", None, None, None),
          SparkWindow("2015-2017", Some(2015), Some(2017), Some(0)),
          SparkWindow("2018-2021", Some(2018), Some(2021), Some(1))
        ),
        identityPolicyVersion = policy,
        graphPolicyVersion = graphPolicy,
        checkpointDirectory = root.resolve("checkpoint").toString,
        outputRoot = root.resolve("output").toString,
        shufflePartitions = 4
      )
  }

  test("module G1 has nine all-years edges, exact A-B weight and no duplicate source weight") {
    val lineage =
      SparkLineage(hadoop, snapshot, er, "module-er-v1", "a" * 64, Vector.empty, Vector.empty)
    val result = Phase6CJobs.build(spark, config, input, lineage, run)
    Vector(
      result.works,
      result.mentions,
      result.canonicalWorks,
      result.memberships,
      result.edges,
      result.support,
      result.integrity,
      result.counters,
      result.graphNodes,
      result.graphEdges
    ).foreach { table =>
      val published = Phase6CMain.publishTable(table, run)
      assert(published.columns.contains("runId"))
      assert(published.columns.contains("schemaVersion"))
    }
    val publishedWork = Phase6CMain.publishTable(result.works, run).head()
    assert(publishedWork.getAs[String]("runId") == run)
    assert(publishedWork.getAs[String]("schemaVersion") == SchemaVersions.sparkAnalytics)
    val publishedGraphNode = Phase6CMain.publishTable(result.graphNodes, run).head()
    assert(publishedGraphNode.getAs[String]("schemaVersion") == SchemaVersions.domain)
    val all = result.edges.filter("windowId = 'all-years'")
    assert(all.count() == 9L)
    assert(result.edges.count() == 18L)
    // Hand-computed literal G1 table: (window, left, right, weight, first year, last year).
    val literal = Vector(
      ("all-years", "A", "B", 3L, 2015, 2016),
      ("all-years", "A", "C", 1L, 2015, 2015),
      ("all-years", "B", "C", 1L, 2015, 2015),
      ("all-years", "C", "D", 1L, 2017, 2017),
      ("all-years", "D", "E", 1L, 2018, 2018),
      ("all-years", "D", "F", 1L, 2018, 2018),
      ("all-years", "E", "F", 2L, 2018, 2019),
      ("all-years", "F", "G", 1L, 2020, 2020),
      ("all-years", "H", "I", 1L, 2020, 2020),
      ("2015-2017", "A", "B", 3L, 2015, 2016),
      ("2015-2017", "A", "C", 1L, 2015, 2015),
      ("2015-2017", "B", "C", 1L, 2015, 2015),
      ("2015-2017", "C", "D", 1L, 2017, 2017),
      ("2018-2021", "D", "E", 1L, 2018, 2018),
      ("2018-2021", "D", "F", 1L, 2018, 2018),
      ("2018-2021", "E", "F", 2L, 2018, 2019),
      ("2018-2021", "F", "G", 1L, 2020, 2020),
      ("2018-2021", "H", "I", 1L, 2020, 2020)
    )
    val expected = literal.map { (window, left, right, weight, first, last) =>
      val ids = Vector(researcher(left), researcher(right)).sorted
      (window, ids(0), ids(1)) -> (weight, first, last)
    }
    assert(expected.size == 18 && expected.map(_._1).toSet.size == 18)
    val observedEdges = result.edges
      .select(
        "windowId",
        "researcherA",
        "researcherB",
        "jointPublicationCount",
        "firstCollaborationYear",
        "lastCollaborationYear"
      )
      .collect()
      .toVector
      .map(row =>
        (row.getString(0), row.getString(1), row.getString(2)) ->
          (row.getLong(3), row.getInt(4), row.getInt(5))
      )
    assert(observedEdges.size == 18)
    assert(observedEdges.toMap == expected.toMap)
    val a = researcher("A"); val b = researcher("B")
    val ab = all
      .filter(
        (all("researcherA") === a && all("researcherB") === b) ||
          (all("researcherA") === b && all("researcherB") === a)
      )
      .head()
    assert(ab.getAs[Long]("jointPublicationCount") == 3L)
    assert(
      result.support
        .filter(result.support("edgeId") === ab.getAs[String]("edgeId"))
        .count() == 3L
    )
    def counter(name: String): Long = result.counters
      .filter(result.counters("name") === name)
      .select("value")
      .head()
      .getLong(0)
    assert(counter("selfPairsDropped") == 1L)
    assert(counter("duplicateTeamMembersCollapsed") == 1L)
    assert(counter("pairCountMismatches") == 0L)
    assert(result.integrity.count() == 0L)
    assert(result.researchers.count() == 10L)
    val nodeJson = result.graphNodes
      .select(
        to_json(
          struct(
            col("nodeId"),
            col("schemaVersion"),
            col("nodeClass"),
            col("label"),
            col("properties"),
            col("provenance")
          ),
          Map("ignoreNullFields" -> "false")
        ).as("json")
      )
      .collect()
      .toVector
      .map(_.getString(0))
    assert(nodeJson.nonEmpty)
    nodeJson.foreach { text =>
      val node = CoreJson
        .parse[GraphNode](text)
        .fold(error => fail(s"GraphNode: $error json=$text"), identity)
      assert(DomainValidation.check(node).isRight)
    }
    val edgeJson = result.graphEdges
      .select(
        to_json(
          struct(
            col("edgeId"),
            col("schemaVersion"),
            col("fromId"),
            col("edgeType"),
            col("toId"),
            col("policyVersion"),
            col("sourceEvidence"),
            col("properties"),
            col("coauthorship"),
            col("provenance")
          ),
          Map("ignoreNullFields" -> "false")
        ).as("json")
      )
      .collect()
      .toVector
      .map(_.getString(0))
    assert(edgeJson.nonEmpty)
    edgeJson.foreach { text =>
      val edge = CoreJson
        .parse[GraphEdge](text)
        .fold(error => fail(s"GraphEdge: $error json=$text"), identity)
      assert(DomainValidation.check(edge).isRight)
    }
  }

  test("yearless and post-2026 DBLP works contribute only to all-years") {
    val base = input
    def extra(label: String, year: Option[Int]): (DataFrame, DataFrame, DataFrame, DataFrame) = {
      val work = workId(label)
      val native = s"conf/module-g1/$label"
      val people = Vector("A", "B")
      val workRow = frame(
        Seq(
          "workId" -> StringType,
          "source" -> StringType,
          "sourceRecordId" -> StringType,
          "year" -> IntegerType,
          "title" -> StringType,
          "doi" -> StringType,
          "arxivId" -> StringType,
          "venueId" -> StringType,
          "snapshot" -> StringType
        ),
        Seq(Seq(work, "DBLP", native, year.map(Int.box).orNull, label, null, null, null, snapshot))
      )
      val mentionRows = frame(
        Seq(
          "mentionId" -> StringType,
          "source" -> StringType,
          "sourceRecordId" -> StringType,
          "nameText" -> StringType,
          "observedOrcid" -> StringType,
          "snapshot" -> StringType
        ),
        people.zipWithIndex.map((name, i) =>
          Seq(mention(label, i + 1), "DBLP", native, name, null, snapshot)
        )
      )
      val teamRow = frame(
        Seq(
          "workId" -> StringType,
          "source" -> StringType,
          "sourceRecordId" -> StringType,
          "memberMentionIds" -> ArrayType(StringType, containsNull = false)
        ),
        Seq(Seq(work, "DBLP", native, Vector(mention(label, 1), mention(label, 2)).asJava))
      )
      val pairRow = frame(
        Seq(
          "workId" -> StringType,
          "source" -> StringType,
          "sourceRecordId" -> StringType,
          "leftMentionId" -> StringType,
          "rightMentionId" -> StringType,
          "year" -> IntegerType
        ),
        Seq(
          Seq(work, "DBLP", native, mention(label, 1), mention(label, 2), year.map(Int.box).orNull)
        )
      )
      (workRow, mentionRows, teamRow, pairRow)
    }
    val unknown = extra("yearless", None)
    val future = extra("future-2027", Some(2027))
    val augmented = base.copy(
      works = base.works
        .unionByName(unknown._1)
        .unionByName(future._1)
        .withColumn(
          "year",
          when(col("workId") === workId("w8"), lit(null).cast(IntegerType)).otherwise(col("year"))
        ),
      mentions = base.mentions.unionByName(unknown._2).unionByName(future._2),
      teams = base.teams.unionByName(unknown._3).unionByName(future._3),
      pairs = base.pairs.unionByName(unknown._4).unionByName(future._4)
    )
    val lineage =
      SparkLineage(hadoop, snapshot, er, "module-er-v1", "a" * 64, Vector.empty, Vector.empty)
    val result = Phase6CJobs.build(spark, config, augmented, lineage, run)
    val ab = result.edges.filter(
      result.edges("windowId") === "all-years" &&
        result.edges("researcherA") === least(lit(researcher("A")), lit(researcher("B"))) &&
        result.edges("researcherB") === greatest(lit(researcher("A")), lit(researcher("B")))
    )
    assert(ab.select("jointPublicationCount").head().getLong(0) == 5L)
    assert(
      result.edges
        .filter(
          result.edges("windowId") === "2015-2017" &&
            result.edges("researcherA") === least(lit(researcher("A")), lit(researcher("B"))) &&
            result.edges("researcherB") === greatest(lit(researcher("A")), lit(researcher("B")))
        )
        .select("jointPublicationCount")
        .head()
        .getLong(0) == 3L
    )
    def counter(name: String): Long = result.counters
      .filter(result.counters("name") === name)
      .select("value")
      .head()
      .getLong(0)
    assert(counter("yearlessWorksExcluded.2015-2017") == 2L)
    assert(counter("yearlessWorksExcluded.2018-2021") == 2L)
    assert(counter("worksBeyondLastBoundedYear") == 1L)
    assert(
      result.support
        .filter(
          result.support("windowId") === "all-years" &&
            result.support("workId") === workId("yearless")
        )
        .count() == 1L
    )
  }

  test("one rank-one DBLP observation supplies a merged work's team and pairs") {
    val base = input
    val alternate = workId("w1-z")
    val native = "conf/module-g1/w1-z"
    val left = mention("w1-z", 1)
    val right = mention("w1-z", 2)
    val augmented = base.copy(
      works = append(
        base.works,
        Seq(alternate, "DBLP", native, Int.box(2015), "alternate team", null, null, null, snapshot)
      ),
      mentions = append(
        append(base.mentions, Seq(left, "DBLP", native, "A", null, snapshot)),
        Seq(right, "DBLP", native, "D", null, snapshot)
      ),
      teams = append(
        base.teams,
        Seq(alternate, "DBLP", native, Vector(left, right).asJava)
      ),
      pairs = append(
        base.pairs,
        Seq(alternate, "DBLP", native, left, right, Int.box(2015))
      ),
      workLinks = append(base.workLinks, Seq(workId("w1"), alternate))
    )
    val result = Phase6CJobs.build(spark, config, augmented, lineage, run)
    assert(counter(result, "nonAuthoritativeDblpObservationsDropped") == 1L)
    assert(counter(result, "pairCountMismatches") == 0L)
    assert(result.edges.filter(col("windowId") === "all-years").count() == 9L)
    assert(result.support.filter(col("workId") === alternate).count() == 0L)
    assert(result.memberships.filter(col("workId") === alternate).count() == 0L)
    val merged = StableIds.workIdFromDoi("10.5555/module-g1-w1").toOption.get
    val members = result.memberships
      .filter(col("canonicalWorkId") === merged)
      .select("researcherId")
      .collect()
      .map(_.getString(0))
      .toSet
    assert(members == Set(researcher("A"), researcher("B"), researcher("C")))
  }

  test("conflicting DBLP ORCIDs are reported without splitting the exact-name researcher") {
    val base = input
    val withOrcids = base.mentions.withColumn(
      "observedOrcid",
      when(col("mentionId") === mention("w1", 1), lit("0000-0002-1825-0097"))
        .when(col("mentionId") === mention("w2", 1), lit("0000-0001-5109-3700"))
        .otherwise(col("observedOrcid"))
    )
    val result = Phase6CJobs.build(spark, config, base.copy(mentions = withOrcids), lineage, run)
    assert(counter(result, "conflictingDblpOrcidGroups") == 1L)
    val warning = result.integrity.filter(col("code") === "conflicting-dblp-orcid")
    assert(warning.count() == 1L)
    assert(warning.select("entityId").head().getString(0) == researcher("A"))
    assert(!warning.select("hardFailure").head().getBoolean(0))
    val a = result.researchers.filter(col("researcherId") === researcher("A"))
    assert(a.count() == 1L)
    assert(a.select(size(col("externalOrcids"))).head().getInt(0) == 2)
  }

  test("orphan graph endpoints appear as hard integrity rows and obey the failure flag") {
    val base = input
    val orphanVenue = StableIds.venueIdFromDblpBooktitle("Missing G1 Venue").toOption.get
    val withOrphan = base.copy(
      works = base.works.withColumn(
        "venueId",
        when(col("workId") === workId("w1"), lit(orphanVenue)).otherwise(col("venueId"))
      )
    )
    val result = Phase6CJobs.build(
      spark,
      config.copy(failOnHardInvariant = false),
      withOrphan,
      lineage,
      run
    )
    assert(counter(result, "missingGraphEndpoints") == 1L)
    val violations = result.integrity.filter(col("code") === "missing-graph-endpoint")
    assert(violations.count() == 1L)
    assert(violations.select("hardFailure").head().getBoolean(0))
    assert(violations.select("detail").head().getString(0).contains(orphanVenue))
    intercept[IllegalStateException] {
      Phase6CJobs.build(spark, config, withOrphan, lineage, run)
    }
  }

  test("cannot-link and authority-conflict work groups stay separate") {
    val base = input
    val links = append(
      append(base.workLinks, Seq(workId("w1"), workId("w2"))),
      Seq(workId("w3"), workId("w4"))
    )
    val cannot = append(base.workCannotLinks, Seq(workId("w1"), workId("w2")))
    val authority = append(
      append(base.workAuthority, Seq(workId("w3"), "DOI", "10.5555/w3")),
      Seq(workId("w4"), "DOI", "10.5555/w4")
    )
    val result = Phase6CJobs.build(
      spark,
      config,
      base.copy(workLinks = links, workCannotLinks = cannot, workAuthority = authority),
      lineage,
      run
    )
    assert(counter(result, "constraintBlockedWorkGroups") == 2L)
    // Three accepted-link rows fall within those two blocked groups.
    assert(counter(result, "constraintBlockedWorkLinks") == 3L)
    def canonical(label: String): String = result.canonicalWorks
      .filter(col("workId") === workId(label))
      .select("canonicalWorkId")
      .head()
      .getString(0)
    assert(canonical("w1") != canonical("w2"))
    assert(canonical("w3") != canonical("w4"))
    assert(result.integrity.filter(col("code") === "constraint-blocked-work-group").count() == 2L)
  }

  test("cross-DBLP links are counted and ambiguous non-DBLP mentions stay unresolved") {
    val base = input
    val cross = base.copy(
      researcherLinks = append(base.researcherLinks, Seq(mention("w1", 1), mention("w1", 2)))
    )
    val crossResult = Phase6CJobs.build(spark, config, cross, lineage, run)
    assert(counter(crossResult, "crossDblpNameLinksNotApplied") == 1L)
    assert(crossResult.researchers.count() == 10L)

    val crossrefA = StableIds.mentionId(SourceType.Crossref, "10.5555/module-g1-w1", 1)
    val twoTargets = frame(
      Seq("leftId" -> StringType, "rightId" -> StringType),
      Seq(Seq(crossrefA, mention("w1", 1)), Seq(crossrefA, mention("w1", 2)))
    )
    val ambiguousResult = Phase6CJobs.build(
      spark,
      config,
      base.copy(researcherLinks = twoTargets),
      lineage,
      run
    )
    assert(counter(ambiguousResult, "ambiguousNonDblpMentions") == 1L)
    assert(
      ambiguousResult.graphEdges
        .filter(col("edgeType") === "RESOLVES_TO" && col("fromId") === crossrefA)
        .count() == 0L
    )
  }

  test("ER unresolved and conflict decisions use explicit wire schemas and named counters") {
    val rejected = ArrayBuffer.empty[DataFrame]
    def decision(entity: String, outcome: String): DataFrame = {
      val wire =
        if (entity == "Researcher") "resolution-researcher-decision.json"
        else "resolution-work-decision.json"
      val source = Path.of("modules/core/src/test/resources/wire").resolve(wire)
      val value = ujson.read(Files.readString(source, UTF_8))
      value("decision")("decision") = ujson.Str(outcome)
      val path = root.resolve(s"$entity-$outcome.jsonl")
      val malformed = if (entity == "Work" && outcome == "CONFLICT") "{bad json\n" else ""
      Files.writeString(path, value.render() + "\n" + malformed, UTF_8)
      Phase6CReaders.readErDecision(spark, path, entity, outcome, rejected)
    }
    val researcherUnresolved = decision("Researcher", "UNRESOLVED")
    val researcherConflicts = decision("Researcher", "CONFLICT")
    val workUnresolved = decision("Work", "UNRESOLVED")
    val workConflicts = decision("Work", "CONFLICT")
    assert(rejected.map(_.count()).sum == 1L)
    val result = Phase6CJobs.build(
      spark,
      config,
      input.copy(
        researcherUnresolved = researcherUnresolved,
        researcherConflicts = researcherConflicts,
        workUnresolved = workUnresolved,
        workConflicts = workConflicts
      ),
      lineage,
      run
    )
    assert(counter(result, "erResearcherUnresolved") == 1L)
    assert(counter(result, "erResearcherConflicts") == 1L)
    assert(counter(result, "erWorkUnresolved") == 1L)
    assert(counter(result, "erWorkConflicts") == 1L)
  }

  test("explicit JSON schema rejects a malformed line and a mismatched version") {
    val schema = new StructType().add("schemaVersion", StringType).add("id", StringType)
    val corrupt = root.resolve("corrupt.jsonl")
    Files.writeString(
      corrupt,
      "{bad json\n{\"schemaVersion\":\"scholarchain.domain.v1\",\"id\":\"good\"}\n",
      UTF_8
    )
    val rejected = ArrayBuffer.empty[DataFrame]
    val valid = Phase6CReaders.read(
      spark,
      Vector(corrupt),
      schema,
      SchemaVersions.domain,
      Seq("id"),
      Some(rejected),
      "fixture/work"
    )
    assert(valid.count() == 1L)
    assert(valid.select("id").head().getString(0) == "good")
    assert(rejected.size == 1)
    assert(rejected.head.count() == 1L)
    assert(rejected.head.select("sourceKind").head().getString(0) == "fixture/work")
    assert(rejected.head.select("rawLine").head().getString(0) == "{bad json")
    val lineage =
      SparkLineage(hadoop, snapshot, er, "module-er-v1", "a" * 64, Vector.empty, Vector.empty)
    val publishedReject = Phase6CMain.publishRejects(rejected.head, run, lineage).head()
    assert(publishedReject.getAs[String]("runId") == run)
    assert(publishedReject.getAs[String]("schemaVersion") == SchemaVersions.sparkAnalytics)
    assert(publishedReject.getAs[String]("hadoopRunId") == hadoop)
    assert(publishedReject.getAs[String]("entityResolutionRunId") == er)
    assert(publishedReject.getAs[String]("sourcePath").endsWith("corrupt.jsonl"))
    val wrong = root.resolve("wrong-version.jsonl")
    Files.writeString(wrong, "{\"schemaVersion\":\"other\",\"id\":\"x\"}\n", UTF_8)
    intercept[IllegalArgumentException] {
      Phase6CReaders.read(spark, Vector(wrong), schema, "scholarchain.domain.v1", Seq("id"))
    }
  }

  test("Hadoop and ER frozen wire examples survive explicit Spark schemas") {
    def example(name: String): (String, Path) = {
      val raw = Files.readString(
        Path.of("modules/core/src/test/resources/wire").resolve(name),
        UTF_8
      )
      val file = root.resolve(name + ".jsonl")
      Files.writeString(file, ujson.read(raw).render() + "\n", UTF_8)
      (raw, file)
    }
    val (workJson, workFile) = example("work-record.json")
    val coreWork = CoreJson.parse[WorkRecord](workJson).toOption.get
    val sparkWork = Phase6CReaders.read(
      spark,
      Vector(workFile),
      Phase6CReaders.work,
      SchemaVersions.domain,
      Seq("workId", "source", "sourceRecordId", "provenance")
    )
    assert(sparkWork.count() == 1L)
    assert(sparkWork.select("workId").head().getString(0) == coreWork.workId)
    assert(sparkWork.select("sourceRecordId").head().getString(0) == coreWork.sourceRecordId)

    val (linkJson, linkFile) = example("resolution-accepted-link.json")
    val coreLink = CoreJson.parse[ResolutionAcceptedLink](linkJson).toOption.get
    val sparkLink = Phase6CReaders.read(
      spark,
      Vector(linkFile),
      Phase6CReaders.link,
      "scholarchain.resolution.v1",
      Seq("pair", "decisionId", "policyHash")
    )
    assert(sparkLink.count() == 1L)
    assert(sparkLink.select("pair.pairId").head().getString(0) == coreLink.pair.pairId)

    val (constraintsJson, constraintsFile) = example("resolution-grouping-constraints.json")
    val coreConstraints =
      CoreJson.parse[ResolutionGroupingConstraints](constraintsJson).toOption.get
    val sparkConstraints = Phase6CReaders.read(
      spark,
      Vector(constraintsFile),
      Phase6CReaders.constraints,
      "scholarchain.resolution.v1",
      Seq("coveredEndpoints", "cannotLinks", "authoritativeIdentifiers")
    )
    assert(sparkConstraints.count() == 1L)
    assert(
      sparkConstraints.select(size(col("coveredEndpoints"))).head().getInt(0) ==
        coreConstraints.coveredEndpoints.size
    )
  }

  test("ER export must bind the selected Hadoop completion and manifest bytes") {
    val markerText = "{\"runId\":\"one\"}\n"
    val manifestText = "{\"runId\":\"one\",\"complete\":true}\n"
    val expected = "aace064b7c951bd5cdd503ad5de082d33d768806b32c33abd7dddc8f84d1e309"
    assert(Phase6CReaders.prepCompletionHash(markerText, manifestText) == expected)
    Phase6CReaders.requireErPrepBinding(
      expected,
      ujson.Obj("prepCompletionHash" -> expected)
    )
    val mismatch = intercept[IllegalArgumentException] {
      Phase6CReaders.requireErPrepBinding(
        expected,
        ujson.Obj("prepCompletionHash" -> ("0" * 64))
      )
    }
    assert(mismatch.getMessage.contains("prepCompletionHash"))
    intercept[IllegalArgumentException] {
      Phase6CReaders.requireErPrepBinding(expected, ujson.Obj())
    }
  }

  test("Hadoop completion marker, inventory and file hash are required") {
    val prepared = root.resolve("invalid-prep-fixture")
    val exportRoot = prepared.resolve("export")
    Files.createDirectories(exportRoot)
    Files.writeString(exportRoot.resolve("_SUCCESS"), "", UTF_8)
    val missingMarker = intercept[IllegalArgumentException] {
      Phase6CReaders.verifyHadoop(prepared)
    }
    assert(missingMarker.getMessage.contains("_SCHOLARCHAIN_COMPLETE"))
    Files.writeString(
      prepared.resolve("run-manifest.json"),
      ujson.Obj("runId" -> hadoop, "configFingerprint" -> ("a" * 64)).render(),
      UTF_8
    )
    val part = "snapshot=fixture/run=fixture/work/part-r-00000"
    val marker = ujson.Obj(
      "complete" -> true,
      "runId" -> hadoop,
      "schemaVersion" -> SchemaVersions.domain,
      "hadoopPrepSchema" -> SchemaVersions.hadoopPrep,
      "configFingerprint" -> ("a" * 64),
      "exportParts" -> ujson.Arr(
        ujson.Obj("path" -> part, "bytes" -> 5, "sha256" -> ("0" * 64))
      )
    )
    Files.writeString(prepared.resolve("_SCHOLARCHAIN_COMPLETE"), marker.render(), UTF_8)
    val inventory = intercept[IllegalArgumentException] {
      Phase6CReaders.verifyHadoop(prepared)
    }
    assert(inventory.getMessage.contains("inventory mismatch"))
    val partPath = exportRoot.resolve(part)
    Files.createDirectories(partPath.getParent)
    Files.writeString(partPath, "line\n", UTF_8)
    val wrongHash = intercept[IllegalArgumentException] {
      Phase6CReaders.verifyHadoop(prepared)
    }
    assert(wrongHash.getMessage.contains("byte/hash mismatch"))
  }

  test("ER completion marker must match the manifest and its schema") {
    val erRoot = root.resolve("invalid-er-fixture")
    Files.createDirectories(erRoot)
    val manifestPath = erRoot.resolve("resolution-manifest.json")
    val markerPath = erRoot.resolve("_SCHOLARCHAIN_RESOLUTION_COMPLETE")
    val manifest = ujson.Obj(
      "complete" -> true,
      "schemaVersion" -> "scholarchain.resolution-export.v1",
      "runId" -> er,
      "files" -> ujson.Arr(),
      "constraints" -> ujson.Arr(ujson.Obj(), ujson.Obj())
    )
    val text = manifest.render() + "\n"
    Files.writeString(manifestPath, text, UTF_8)
    Files.writeString(markerPath, "wrong\n", UTF_8)
    val wrongMarker = intercept[IllegalArgumentException] {
      Phase6CReaders.verifyEr(erRoot)
    }
    assert(wrongMarker.getMessage.contains("completion hash mismatch"))
    Files.writeString(markerPath, StableIds.sha256Hex(text) + "\n", UTF_8)
    Phase6CReaders.verifyEr(erRoot)
    manifest("schemaVersion") = ujson.Str("other")
    val wrongSchema = manifest.render() + "\n"
    Files.writeString(manifestPath, wrongSchema, UTF_8)
    Files.writeString(markerPath, StableIds.sha256Hex(wrongSchema) + "\n", UTF_8)
    val badManifest = intercept[IllegalArgumentException] {
      Phase6CReaders.verifyEr(erRoot)
    }
    assert(badManifest.getMessage.contains("unsupported ER manifest"))
  }

  test("completed output reuses matching logical identity and rejects mismatch or broken marker") {
    val oldRunId = StableIds
      .sparkAnalyticsRunId(
        hadoop,
        "a" * 64,
        er,
        "b" * 64,
        "module-er-v1",
        "c" * 64,
        "d" * 64,
        "spark-phase6c-jobs1-2-v1"
      )
      .toOption
      .get
    val repairedRunId = StableIds
      .sparkAnalyticsRunId(
        hadoop,
        "a" * 64,
        er,
        "b" * 64,
        "module-er-v1",
        "c" * 64,
        "d" * 64,
        Phase6CMain.codeVersion
      )
      .toOption
      .get
    assert(oldRunId != repairedRunId)

    val output = root.resolve("output-gate")
    Files.createDirectory(output)
    val logical = ujson.Obj(
      "schemaVersion" -> SchemaVersions.sparkAnalytics,
      "runId" -> run,
      "codeVersion" -> Phase6CMain.codeVersion,
      "hadoopRunId" -> hadoop,
      "hadoopManifestHash" -> ("a" * 64),
      "entityResolutionRunId" -> er,
      "entityResolutionManifestHash" -> ("b" * 64),
      "entityResolutionPolicyVersion" -> "module-er-v1",
      "entityResolutionPolicyHash" -> ("c" * 64),
      "logicalConfigFingerprint" -> ("d" * 64),
      "physicalConfigFingerprint" -> ("e" * 64)
    )
    val text = logical.render() + "\n"
    Files.writeString(output.resolve("run-manifest.json"), text, UTF_8)
    Files.writeString(
      output.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
      StableIds.sha256Hex(text) + "\n",
      UTF_8
    )
    val relocated = ujson.read(text).obj
    relocated("physicalConfigFingerprint") = ujson.Str("f" * 64)
    Phase6CMain.requireReusable(output, ujson.Obj.from(relocated))
    relocated("logicalConfigFingerprint") = ujson.Str("0" * 64)
    intercept[IllegalArgumentException] {
      Phase6CMain.requireReusable(output, ujson.Obj.from(relocated))
    }
    relocated("logicalConfigFingerprint") = ujson.Str("d" * 64)
    relocated("codeVersion") = ujson.Str("spark-phase6c-jobs1-2-v1")
    intercept[IllegalArgumentException] {
      Phase6CMain.requireReusable(output, ujson.Obj.from(relocated))
    }
    Files.writeString(output.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), "bad\n", UTF_8)
    intercept[IllegalArgumentException] {
      Phase6CMain.requireReusable(output, logical)
    }
  }
  test(
    "representative ID authority survives absent DOI columns and normalized ORCIDs do not conflict"
  ) {
    val base = input
    val lineage =
      SparkLineage(hadoop, snapshot, er, "module-er-v1", "a" * 64, Vector.empty, Vector.empty)
    val absentDoi = base.works.withColumn("doi", lit(null).cast(StringType))
    val paddedOrcids = base.mentions.withColumn(
      "observedOrcid",
      when(
        col("nameText") === "A",
        when(col("sourceRecordId").endsWith("w1"), lit(" 0000-0002-1825-0097 "))
          .otherwise(lit("0000-0002-1825-0097"))
      ).otherwise(col("observedOrcid"))
    )
    val nullLink =
      frame(Seq("leftId" -> StringType, "rightId" -> StringType), Vector(Seq(null, null)))
    val result = Phase6CJobs.build(
      spark,
      config,
      base.copy(
        works = absentDoi,
        mentions = paddedOrcids,
        researcherLinks = base.researcherLinks.unionByName(nullLink)
      ),
      lineage,
      run
    )
    val doi = StableIds.workIdFromDoi("10.5555/module-g1-w1").toOption.get
    assert(
      result.canonicalWorks
        .filter(col("workId") === workId("w1"))
        .select("canonicalWorkId")
        .first()
        .getString(0) == doi
    )
    assert(counter(result, "conflictingDblpOrcidGroups") == 0L)
    assert(counter(result, "acceptedResearcherLinksMissingEndpoint") == 1L)
    val published = result.graphNodes
      .filter(col("nodeId") === researcher("A"))
      .toJSON
      .collect()
      .map(j => CoreJson.parse[GraphNode](j).toOption.get)
    assert(published.length == 1)
    assert(published(0).properties == Vector(NamedText("orcid.0", "0000-0002-1825-0097")))
    assert(DomainValidation.check(published(0)).isRight)
    assert(
      result.researchers
        .filter(col("researcherId") === researcher("A"))
        .select("externalOrcids")
        .first()
        .getSeq[String](0) == Seq("0000-0002-1825-0097")
    )
  }

}
