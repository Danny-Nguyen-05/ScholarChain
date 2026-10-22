package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.spark.{Phase6CInput, Phase6CJobs}
import org.apache.spark.sql.{DataFrame, Row, SparkSession}
import org.apache.spark.sql.types.*
import org.scalatest.BeforeAndAfterEach
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Black-box checks of the public jobs 1–2 DataFrame interface using separately authored G1. */
class IndependentPhase6CGraphSpec extends AnyFunSuite with BeforeAndAfterEach {
  import IndependentPhase6G1.*

  private var spark: SparkSession = _
  private var temp: Path = _

  override def beforeEach(): Unit = {
    super.beforeEach()
    temp = Files.createTempDirectory("scholarchain-independent-6c-")
    spark = SparkSession
      .builder()
      .appName("ScholarChain independent 6C graph")
      .master("local[2]")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "4")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.warehouse.dir", temp.resolve("warehouse").toString)
      .getOrCreate()
    spark.sparkContext.setCheckpointDir(temp.resolve("checkpoints").toString)
  }

  override def afterEach(): Unit = {
    try {
      if (spark != null) spark.stop()
      if (temp != null) {
        val stream = Files.walk(temp)
        try stream.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists)
        finally stream.close()
      }
    } finally super.afterEach()
  }

  private val string = StringType
  private val integer = IntegerType
  private val stringArray = ArrayType(StringType, containsNull = false)

  private def frame(columns: Seq[(String, DataType)], records: Seq[Seq[Any]]): DataFrame = {
    val schema = StructType(columns.map { case (name, dataType) =>
      StructField(name, dataType, nullable = true)
    })
    spark.createDataFrame(records.map(Row.fromSeq).asJava, schema)
  }

  private def input(works: Vector[WorkRecord] = allWorks): Phase6CInput = {
    val dblpW1 = dblpWorks.head
    val crossref = works.find(_.source == SourceType.Crossref)
    val workLinks = crossref.toVector.map(w => Seq(dblpW1.workId, w.workId))
    val researcherLinks = crossref.toVector.flatMap(w =>
      dblpW1.authors.zip(w.authors).map((a, b) => Seq(a.mentionId, b.mentionId))
    )
    val inputTeams = works.map(w =>
      Seq(w.workId, w.source.wire, w.sourceRecordId, w.authors.map(_.mentionId).asJava)
    )
    val inputPairs = works.flatMap { w =>
      for {
        left <- w.authors.indices
        right <- (left + 1) until w.authors.size
      } yield Seq(
        w.workId,
        w.source.wire,
        w.sourceRecordId,
        w.authors(left).mentionId,
        w.authors(right).mentionId,
        w.year.map(Int.box).orNull
      )
    }
    Phase6CInput(
      works = frame(
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "year" -> integer,
          "title" -> string,
          "doi" -> string,
          "arxivId" -> string,
          "venueId" -> string,
          "snapshot" -> string
        ),
        works.map(w =>
          Seq(
            w.workId,
            w.source.wire,
            w.sourceRecordId,
            w.year.map(Int.box).orNull,
            w.title,
            w.doi.orNull,
            w.arxivId.orNull,
            w.venueId.orNull,
            w.provenance.datasetSnapshot
          )
        )
      ),
      mentions = frame(
        Seq(
          "mentionId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "nameText" -> string,
          "observedOrcid" -> string,
          "snapshot" -> string
        ),
        works.flatMap(w =>
          w.authors.map(m =>
            Seq(
              m.mentionId,
              m.source.wire,
              m.sourceRecordId,
              m.nameText,
              m.observedOrcid.orNull,
              m.provenance.datasetSnapshot
            )
          )
        )
      ),
      teams = frame(
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "memberMentionIds" -> stringArray
        ),
        inputTeams
      ),
      pairs = frame(
        Seq(
          "workId" -> string,
          "source" -> string,
          "sourceRecordId" -> string,
          "leftMentionId" -> string,
          "rightMentionId" -> string,
          "year" -> integer
        ),
        inputPairs
      ),
      researcherLinks = frame(Seq("leftId" -> string, "rightId" -> string), researcherLinks),
      workLinks = frame(Seq("leftId" -> string, "rightId" -> string), workLinks),
      researcherCannotLinks = frame(Seq("leftId" -> string, "rightId" -> string), Seq.empty),
      workCannotLinks = frame(Seq("leftId" -> string, "rightId" -> string), Seq.empty),
      researcherAuthority = frame(
        Seq("endpointId" -> string, "namespace" -> string, "value" -> string),
        Seq.empty
      ),
      workAuthority = frame(
        Seq("endpointId" -> string, "namespace" -> string, "value" -> string),
        Seq.empty
      )
    )
  }

  private def config: SparkAnalyticsConfig = {
    val stream = getClass.getResourceAsStream("/scholarchain.spark-analytics-config.v1.json")
    assert(stream != null)
    val text =
      try new String(stream.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8)
      finally stream.close()
    SparkAnalyticsConfigLoader
      .loadText(text)
      .toOption
      .get
      .copy(
        windows = windows,
        identityPolicyVersion = identityPolicy,
        representativePolicyVersion = representativePolicy,
        graphPolicyVersion = graphPolicy,
        checkpointDirectory = temp.resolve("checkpoints").toString,
        outputRoot = temp.resolve("output").toString,
        shufflePartitions = 4
      )
  }

  private def lineage: SparkLineage = SparkLineage(
    hadoopRunId,
    snapshot,
    erRunId,
    erPolicy,
    erPolicyHash,
    Vector.empty,
    Vector.empty
  )

  private def counter(rows: DataFrame, name: String): Long =
    rows.filter(rows("name") === name).select("value").collect().map(_.getLong(0)).sum

  test("G1 has the exact all-years and split-window weighted edges and support") {
    val result = Phase6CJobs.build(spark, config, input(), lineage, sparkRunId)
    val actual = result.edges
      .collect()
      .toVector
      .map { row =>
        val window = row.getAs[String]("windowId")
        val a = row.getAs[String]("researcherA")
        val b = row.getAs[String]("researcherB")
        val years = (
          Option(row.getAs[Integer]("firstCollaborationYear")).map(_.intValue()),
          Option(row.getAs[Integer]("lastCollaborationYear")).map(_.intValue())
        )
        (
          (window, Set(a, b)),
          (row.getAs[Long]("jointPublicationCount"), years, row.getAs[String]("edgeId"))
        )
      }
      .toMap
    assert(actual.size == 18)
    expectedEdges.foreach { expected =>
      val a = researcherId(expected.left)
      val b = researcherId(expected.right)
      val key = (expected.windowId, Set(a, b))
      assert(actual.contains(key), s"missing G1 edge $expected")
      val (weight, years, edgeId) = actual(key)
      assert(weight == expected.weight, s"weight of $expected")
      assert(years == (Some(expected.first), Some(expected.last)), s"years of $expected")
      assert(
        edgeId == StableIds
          .sparkCoauthorEdgeId(
            a,
            b,
            windows.find(_.windowId == expected.windowId).get,
            graphPolicy
          )
          .toOption
          .get
      )
      val supports = result.support
        .filter(result.support("edgeId") === edgeId)
        .select("workId")
        .collect()
        .map(_.getString(0))
        .toVector
      assert(
        supports.toSet == expected.supportingWorks.map(canonicalWorkId),
        s"support of $expected"
      )
      assert(supports.size == expected.supportingWorks.size, s"duplicate support of $expected")
    }
    assert(counter(result.counters, "selfPairsDropped") == 1L)
    assert(counter(result.counters, "duplicateTeamMembersCollapsed") == 1L)
    assert(counter(result.counters, "crossDblpNameLinksNotApplied") == 0L)
    assert(counter(result.counters, "enrichmentOnlyWorksExcluded") == 0L)
    assert(counter(result.counters, "unmappedPairsDropped") == 0L)
    assert(counter(result.counters, "pairCountMismatches") == 0L)
    assert(result.researchers.count() == 10L)
    assert(result.canonicalWorks.count() == 10L)
    assert(result.canonicalWorks.select("canonicalWorkId").distinct().count() == 9L)
    assert(result.integrity.count() == 0L)
    val nodeIds = result.graphNodes.select("nodeId").collect().map(_.getString(0)).toSet
    result.graphEdges.select("fromId", "toId").collect().foreach { edge =>
      assert(nodeIds.contains(edge.getString(0)), s"missing graph source ${edge.getString(0)}")
      assert(nodeIds.contains(edge.getString(1)), s"missing graph target ${edge.getString(1)}")
    }
    val (abLeft, abRight) =
      StableIds.canonicalPair(researcherId("A"), researcherId("B")).toOption.get
    val ab = result.edges
      .filter(
        result.edges("windowId") === "all-years" &&
          result.edges("researcherA") === abLeft &&
          result.edges("researcherB") === abRight
      )
      .select("representativeWorkIds")
      .head()
    assert(ab.getSeq[String](0) == Seq(workId("w2"), workId("w9"), canonicalWorkId("w1")))
  }

  test("a cross-DBLP accepted link does not collapse two exact DBLP names") {
    val base = input()
    val a = dblpWorks.find(_.sourceRecordId.endsWith("/w2")).get.authors.head.mentionId
    val b = dblpWorks.find(_.sourceRecordId.endsWith("/w2")).get.authors(1).mentionId
    val crossed = base.copy(researcherLinks =
      base.researcherLinks.unionByName(
        frame(Seq("leftId" -> string, "rightId" -> string), Seq(Seq(a, b)))
      )
    )
    val result = Phase6CJobs.build(spark, config, crossed, lineage, sparkRunId)
    assert(counter(result.counters, "crossDblpNameLinksNotApplied") == 1L)
    val ab = result.edges.filter(
      result.edges("windowId") === "all-years" &&
        ((result.edges("researcherA") === researcherId("A") &&
          result.edges("researcherB") === researcherId("B")) ||
          (result.edges("researcherA") === researcherId("B") &&
            result.edges("researcherB") === researcherId("A")))
    )
    assert(ab.count() == 1L)
    assert(ab.select("jointPublicationCount").head().getLong(0) == 3L)
  }

  test("a work cannot-link prevents the linked Crossref observation from merging") {
    val base = input()
    val left = dblpWorks.head.workId
    val right = crossrefW1.workId
    val constrained = base.copy(workCannotLinks =
      frame(
        Seq("leftId" -> string, "rightId" -> string),
        Seq(Seq(left, right))
      )
    )
    val result = Phase6CJobs.build(spark, config, constrained, lineage, sparkRunId)
    val selected = result.canonicalWorks
      .filter(result.canonicalWorks("workId").isin(left, right))
      .select("canonicalWorkId")
      .collect()
      .map(_.getString(0))
      .toSet
    assert(selected.size == 2)
    assert(counter(result.counters, "enrichmentOnlyWorksExcluded") == 1L)
  }

  test("yearless and 2027 DBLP works enter only all-years; enrichment-only pair is excluded") {
    val yearless = work("w-yearless", None, Vector("K", "L"))
    val future = work("w-future", Some(2027), Vector("U", "V"))
    val enrichment = work("w-enrichment", Some(2018), Vector("M", "N"), SourceType.OpenAlex)
    val result = Phase6CJobs.build(
      spark,
      config,
      input(allWorks ++ Vector(yearless, future, enrichment)),
      lineage,
      sparkRunId
    )
    val edges = result.edges
      .select(
        "windowId",
        "researcherA",
        "researcherB",
        "firstCollaborationYear",
        "lastCollaborationYear"
      )
      .collect()
      .toVector
    def onlyAllYears(left: String, right: String): Vector[Row] = {
      val ends = Set(researcherId(left), researcherId(right))
      edges.filter(row => Set(row.getString(1), row.getString(2)) == ends)
    }
    val unknownYear = onlyAllYears("K", "L")
    assert(unknownYear.size == 1 && unknownYear.head.getString(0) == "all-years")
    assert(unknownYear.head.isNullAt(3) && unknownYear.head.isNullAt(4))
    val afterBounds = onlyAllYears("U", "V")
    assert(afterBounds.size == 1 && afterBounds.head.getString(0) == "all-years")
    assert(afterBounds.head.getInt(3) == 2027 && afterBounds.head.getInt(4) == 2027)
    assert(counter(result.counters, "enrichmentOnlyWorksExcluded") == 1L)
    assert(result.researchers.count() == 14L)
  }

  test("linked DBLP observations use only the lexical authoritative team and pair") {
    val chosen = work("w-authority-a", Some(2017), Vector("P", "Q"))
    val discarded = work("w-authority-z", Some(2017), Vector("P", "R"))
    val base = input(Vector(chosen, discarded))
    val linked = base.copy(workLinks =
      frame(
        Seq("leftId" -> string, "rightId" -> string),
        Seq(Seq(chosen.workId, discarded.workId))
      )
    )
    val result = Phase6CJobs.build(spark, config, linked, lineage, sparkRunId)

    val canonical = result.canonicalWorks
      .select("canonicalWorkId", "authoritativeSourceRecordId")
      .collect()
      .toVector
    assert(canonical.size == 2)
    assert(canonical.map(_.getString(0)).distinct.size == 1)
    assert(canonical.map(_.getString(1)).toSet == Set(chosen.sourceRecordId))

    val members = result.memberships.select("researcherId").collect().map(_.getString(0)).toSet
    assert(members == Set(researcherId("P"), researcherId("Q")))
    assert(!members.contains(researcherId("R")))
    val allYears = result.edges
      .filter(result.edges("windowId") === "all-years")
      .select("researcherA", "researcherB", "jointPublicationCount")
      .collect()
      .toVector
    assert(allYears.size == 1)
    assert(
      Set(allYears.head.getString(0), allYears.head.getString(1)) ==
        Set(researcherId("P"), researcherId("Q"))
    )
    assert(allYears.head.getLong(2) == 1L)
    assert(counter(result.counters, "nonAuthoritativeDblpObservationsDropped") == 1L)
    assert(counter(result.counters, "pairCountMismatches") == 0L)
  }

  test("conflicting ORCIDs for one exact DBLP name retain identity and emit one warning") {
    val originalFirst = work("w-orcid-a", Some(2015), Vector("Shared Name", "B"))
    val originalSecond = work("w-orcid-b", Some(2016), Vector("Shared Name", "C"))
    val orcidOne = "0000-0002-1825-0097"
    val orcidTwo = "0000-0001-5109-3700"
    val observedFirst = originalFirst.copy(authors =
      originalFirst.authors.updated(
        0,
        originalFirst.authors.head.copy(
          observedOrcid = Some(orcidOne),
          identityStatus = MentionIdentityStatus.ExternalIdentifierObserved
        )
      )
    )
    val observedSecond = originalSecond.copy(authors =
      originalSecond.authors.updated(
        0,
        originalSecond.authors.head.copy(
          observedOrcid = Some(orcidTwo),
          identityStatus = MentionIdentityStatus.ExternalIdentifierObserved
        )
      )
    )
    val result = Phase6CJobs.build(
      spark,
      config,
      input(Vector(observedFirst, observedSecond)),
      lineage,
      sparkRunId
    )

    val sharedId = researcherId("Shared Name")
    val people = result.researchers
      .filter(result.researchers("researcherId") === sharedId)
      .select("externalOrcids")
      .collect()
      .toVector
    assert(people.size == 1)
    assert(people.head.getSeq[String](0).toSet == Set(orcidOne, orcidTwo))
    assert(
      result.memberships
        .filter(result.memberships("researcherId") === sharedId)
        .select("canonicalWorkId")
        .distinct()
        .count() == 2L
    )

    val warnings = result.integrity
      .filter(
        result.integrity("code") ===
          "conflicting-dblp-orcid"
      )
      .select("entityId", "hardFailure")
      .collect()
      .toVector
    assert(result.integrity.count() == 1L)
    assert(warnings.size == 1)
    assert(warnings.head.getString(0) == sharedId)
    assert(!warnings.head.getBoolean(1))
    assert(counter(result.counters, "conflictingDblpOrcidGroups") == 1L)
  }
}
