package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import org.scalatest.funsuite.AnyFunSuite
import StorageResult.*
import SubsetFixture.*

/** Expected counts are derived by hand in [[SubsetFixture]]; they are not read back from the
  * implementation under test.
  */
class RuntimeArtifactSubsetSpec extends AnyFunSuite {
  private def list(lines: String*): IncludeList =
    IncludeList.parse(lines.mkString("\n").getBytes(UTF_8)).toOption.get

  private def build(
      include: IncludeList,
      config: RuntimeArtifactConfig = RuntimeArtifactConfig(),
      rows: Map[String, Vector[ujson.Obj]] = source,
      reverse: Boolean = false,
      maxSourceRows: Long = 3000000L
  ): SubsetOutcome =
    RuntimeArtifactSubset.build(
      manifests(),
      new Reader(rows, reverse),
      include,
      config,
      maxSourceRows = maxSourceRows
    )

  private def artifact(o: SubsetOutcome): SubsetArtifact = o.result match {
    case Right(a) => a
    case Left(r)  => fail("refused: " + r)
  }
  private def refusal(o: SubsetOutcome): SubsetRefusal = o.result match {
    case Left(r)  => r
    case Right(_) => fail("expected a refusal")
  }
  private def snapshot(a: SubsetArtifact): RuntimeArtifactSnapshot =
    upickle.default.read[RuntimeArtifactSnapshot](new String(a.bytes, UTF_8))
  private def rowsOf(s: RuntimeArtifactSnapshot, table: String): Vector[ujson.Value] =
    s.tables.find(_.manifest.logicalDataset == table).map(_.rows).getOrElse(Vector.empty)
  private def count(s: RuntimeArtifactSnapshot): Int = s.tables.map(_.rows.size).sum
  private def researchersWithMetrics(s: RuntimeArtifactSnapshot): Set[String] =
    rowsOf(s, "metrics/type=researcher_collaboration").map(_("researcherId").str).toSet
  private def store(a: SubsetArtifact): ObjectStoreRuntimeArtifactStore = {
    val objects = new InMemoryObjectStore
    val key = "runtime/versions/test/snapshot.json"
    assert(
      StorageResult.successful(objects.put(key, a.bytes.toVector, "application/json", Map.empty))
    )
    new ObjectStoreRuntimeArtifactStore(objects, RuntimeArtifactPointer(key, a.sha256, a.runId))
  }

  test(
    "include list parsing ignores comments, blanks and duplicates and hashes the normalized set"
  ) {
    val parsed = IncludeList
      .parse(s"# smoke\n\n  $b \n$a\n$a\n$wab\n".getBytes(UTF_8))
      .toOption
      .get
    assert(parsed.ids == Vector(a, b, wab).sorted)
    assert(parsed.duplicateLines == 1)
    assert(parsed.researchers == Vector(a, b) && parsed.works == Vector(wab))
    val reordered = list(wab, a, b)
    assert(parsed.normalizedSha256 == reordered.normalizedSha256)
    assert(parsed.fileSha256 != reordered.fileSha256)
    assert(parsed.normalizedSha256 == StableIds.sha256Hex(Vector(a, b, wab).sorted.mkString("\n")))
    Vector("", "# only a comment", "   \n\n").foreach(text =>
      assert(IncludeList.parse(text.getBytes(UTF_8)) == Left("include-list-empty"))
    )
    Vector("topic:openalex:T1", "researcher:", "researcher:has space", "a,b").foreach(text =>
      assert(IncludeList.parse(text.getBytes(UTF_8)) == Left("include-list-invalid-id"), text)
    )
    assert(
      IncludeList.parse(Array.fill(IncludeList.maxBytes + 1)('a'.toByte)) ==
        Left("include-list-too-large")
    )
    val many = (0 to IncludeList.maxIds).map(n => s"researcher:$n").mkString("\n")
    assert(IncludeList.parse(many.getBytes(UTF_8)) == Left("include-list-too-many-ids"))
  }

  test("the documented example include file parses and every ID uses a supported prefix") {
    val stream = getClass.getResourceAsStream("/runtime-subset-include.example.txt")
    assert(stream != null)
    val bytes =
      try stream.readAllBytes()
      finally stream.close()
    val parsed = IncludeList.parse(bytes).toOption.get
    assert(parsed.ids.nonEmpty && parsed.duplicateLines == 0)
  }

  test("when everything fits the artifact carries the whole source and answers from it") {
    val a1 = artifact(build(list(e)))
    val s = snapshot(a1)
    assert(count(s) == sourceRowTotal)
    assert(researchersWithMetrics(s) == people.toSet)
    assert(a1.runId == runId && a1.sha256.matches("[0-9a-f]{64}"))
    val reader = store(a1)
    val context = StorageResult.value(reader.researcherContext(a, "all-years", 10)).get
    assert(context.coauthorIds == Vector(b, c, d))
    assert(context.topicIds.contains(Vector(topic1)) && context.venueIds.contains(Vector(venue)))
    assert(context.institutionIds.contains(Vector(institution1)))
    val ranking = StorageResult
      .value(
        reader.rank(
          "all-years",
          RuntimeRankingMetric.DistinctCoauthorCount,
          RuntimePopulationFilter(),
          2
        )
      )
      .get
    assert(ranking.populationCount == 6 && ranking.items.map(_.metric.researcherId) == Vector(a, b))
  }

  test("include list is honored first and the fill adds the highest degree that fits, whole") {
    // f alone is 11 rows; a adds 24 (disjoint) = 35; b would add 8 = 43 > 40 and stops the fill.
    val outcome = build(list(f), RuntimeArtifactConfig(maxRows = 40))
    val s = snapshot(artifact(outcome))
    assert(count(s) == 35)
    assert(researchersWithMetrics(s) == Set(f, a))
    val entities = outcome.report("entities")
    assert(entities("fromIncludeList").num == 1 && entities("fromDegreeFill").num == 1)
    assert(entities("included").arr.map(_("id").str) == Vector(f, a))
    assert(entities("included").arr.map(_("reason").str) == Vector("include-list", "degree-fill"))
    assert(entities("included").arr.map(_("closureRows").num.toInt) == Vector(11, 24))
    val stop = entities("fillStoppedAt")
    assert(
      stop("id").str == b && stop("neededNewRows").num == 8 && stop("wouldBeTotalRows").num == 43
    )
    assert(stop("reasons").arr.map(_.str) == Vector("row-cap"))
    assert(entities("candidatesNotReached").num == 3) // c, d, e
    assert(outcome.report("selected")("totalRows").num == 35)
  }

  test("an exactly fitting include list is accepted and the fill cannot add anything") {
    val outcome = build(list(e), RuntimeArtifactConfig(maxRows = 13))
    val s = snapshot(artifact(outcome))
    assert(count(s) == 13 && researchersWithMetrics(s) == Set(e))
    assert(outcome.report("entities")("fillStoppedAt")("id").str == a)
  }

  test("no half entities: every included researcher is complete and others carry no metrics") {
    val s = snapshot(artifact(build(list(f), RuntimeArtifactConfig(maxRows = 40))))
    val included = researchersWithMetrics(s)
    def sourceRows(table: String) = source(table)
    included.foreach { who =>
      Vector(
        "metrics/type=researcher_collaboration",
        "metrics/type=communities",
        "metrics/type=bridges",
        "metrics/type=temporal_changes"
      ).foreach { table =>
        val expected = sourceRows(table).filter(_("researcherId").str == who).map(_.render())
        assert(rowsOf(s, table).filter(_("researcherId").str == who).map(_.render()) == expected)
      }
      val edgeRows = sourceRows("edges/type=coauthored_with")
        .filter(r => r("researcherA").str == who || r("researcherB").str == who)
      val present = rowsOf(s, "edges/type=coauthored_with").map(_.render()).toSet
      assert(edgeRows.forall(r => present(r.render())))
      val edgeIds = edgeRows.map(_("edgeId").str).toSet
      val supportExpected =
        sourceRows("edges/type=coauthored_with_support").filter(r => edgeIds(r("edgeId").str))
      val supportPresent = rowsOf(s, "edges/type=coauthored_with_support").map(_.render()).toSet
      assert(supportExpected.nonEmpty && supportExpected.forall(r => supportPresent(r.render())))
      val authored = sourceRows("edges/type=authored").filter(_("fromId").str == who)
      val authoredPresent = rowsOf(s, "edges/type=authored").map(_.render()).toSet
      assert(authored.forall(r => authoredPresent(r.render())))
    }
    // The excluded researchers have no per-researcher rows at all; they may exist only as nodes.
    val others = people.toSet -- included
    assert(others.nonEmpty)
    Vector(
      "metrics/type=researcher_collaboration",
      "metrics/type=communities",
      "metrics/type=bridges",
      "metrics/type=temporal_changes"
    ).foreach(table => assert(rowsOf(s, table).forall(r => !others(r("researcherId").str)), table))
    assert(rowsOf(s, "edges/type=authored").forall(r => !others(r("fromId").str)))
    // The reader treats a node-only neighbor as unknown rather than answering partially.
    val reader = store(artifact(build(list(f), RuntimeArtifactConfig(maxRows = 40))))
    assert(reader.researcherContext(e, "all-years", 5) == Missing)
    assert(
      StorageResult.value(reader.researcherContext(f, "all-years", 5)).get.coauthorIds == Vector(e)
    )
  }

  test("the same inputs give identical bytes regardless of list order, comments or source order") {
    val config = RuntimeArtifactConfig(maxRows = 40)
    val one = artifact(build(list(f, a), config))
    val two = artifact(
      RuntimeArtifactSubset.build(
        manifests(),
        new Reader(source, reverse = true),
        IncludeList.parse(s"# order\n$a\n\n$f\n$a\n".getBytes(UTF_8)).toOption.get,
        config
      )
    )
    assert(one.sha256 == two.sha256 && java.util.Arrays.equals(one.bytes, two.bytes))
    assert(one.sha256 == StorageKeys.sha256(one.bytes.toVector))
    val different = artifact(build(list(e), config))
    assert(different.sha256 != one.sha256)
  }

  test("the artifact records its subset provenance in every table manifest") {
    val s = snapshot(artifact(build(list(f), RuntimeArtifactConfig(maxRows = 40))))
    s.tables.foreach { t =>
      val mapping = t.manifest.targetMapping.map(m => m.name -> m.value).toMap
      assert(mapping("subset.rule") == RuntimeArtifactSubset.ruleId)
      assert(mapping("subset.sourceRowCount") == source(t.manifest.logicalDataset).size.toString)
      assert(
        mapping("subset.sourceSortedRowsSha256") ==
          manifests().find(_.logicalDataset == t.manifest.logicalDataset).get.sortedRowsSha256
      )
      assert(mapping("subset.includeListSha256") == list(f).normalizedSha256)
      assert(t.manifest.rowCount == t.rows.size)
    }
  }

  test("an entity whose closure alone exceeds a cap refuses the whole run explicitly") {
    val rows = build(list(a), RuntimeArtifactConfig(maxRows = 12))
    val r = refusal(rows)
    assert(r.code == "include-entity-alone-exceeds-cap")
    assert(r.detail.contains(a) && r.detail.contains("24 rows") && r.detail.contains("row-cap"))
    assert(rows.report("status").str == "refused")
    // A single oversized row is also an entity-level refusal, never a silent drop.
    val wide = refusal(build(list(f), RuntimeArtifactConfig(maxRowBytes = 10)))
    assert(wide.code == "include-entity-alone-exceeds-cap" && wide.detail.contains("row-byte-cap"))
  }

  test("entries that fit alone but not together refuse naming the entry that overflows") {
    // a (24) then e (13) = 37 > 30. IDs are processed in sorted order.
    val r = refusal(build(list(e, a), RuntimeArtifactConfig(maxRows = 30)))
    assert(r.code == "include-list-exceeds-cap" && r.detail.contains(e))
    // The same list is accepted when the cap equals the hand-derived union.
    assert(count(snapshot(artifact(build(list(e, a), RuntimeArtifactConfig(maxRows = 37))))) == 37)
  }

  test("a listed work is expanded to all of its authors and is all-or-nothing") {
    val outcome = build(list(wef), RuntimeArtifactConfig(maxRows = 18))
    val s = snapshot(artifact(outcome))
    // e (13) plus the 5 f rows e's closure lacks: metrics, community, bridge, summary, authored.
    assert(count(s) == 18 && researchersWithMetrics(s) == Set(e, f))
    val reasons = outcome.report("entities")("included").arr.map(_("reason").str)
    assert(reasons == Vector(s"work-author:$wef", s"work-author:$wef"))
    assert(
      outcome.report("entities")("includeListWorks")(0)("authors").arr.map(_.str) == Vector(e, f)
    )
    val tooSmall = refusal(build(list(wef), RuntimeArtifactConfig(maxRows = 17)))
    assert(tooSmall.code == "include-entity-alone-exceeds-cap" && tooSmall.detail.contains(wef))
  }

  test("unknown researchers and works are refused rather than ignored") {
    val missing = refusal(build(list(unknownResearcher)))
    assert(missing.code == "include-id-not-found" && missing.detail.contains(unknownResearcher))
    val work = refusal(build(list("work:dblp:synthetic/none")))
    assert(work.code == "include-id-not-found")
  }

  test("byte caps are never exceeded and a cap below the estimate refuses") {
    val full = artifact(build(list(e)))
    val sized = build(list(e), RuntimeArtifactConfig(maxRows = 13))
    val exact = artifact(sized)
    val bound = sized.report("selected")("estimatedBytesBound").num.toInt
    assert(exact.bytes.length <= bound)
    Vector(0.2, 0.4, 0.6, 0.8, 1.0).foreach { fraction =>
      val cap = (full.bytes.length * fraction).toInt
      val o = build(list(e), RuntimeArtifactConfig(maxBytes = cap))
      o.result match {
        case Right(art) => assert(art.bytes.length <= cap, s"fraction $fraction")
        case Left(r) =>
          assert(
            Set("include-entity-alone-exceeds-cap", "include-list-exceeds-cap")(r.code),
            r.toString
          )
      }
    }
    // With a byte budget equal to the e-only estimate the fill cannot add anything else.
    val atBound = build(list(e), RuntimeArtifactConfig(maxBytes = bound))
    assert(count(snapshot(artifact(atBound))) == 13)
    assert(artifact(atBound).bytes.length <= bound)
    val below = refusal(build(list(e), RuntimeArtifactConfig(maxBytes = exact.bytes.length - 1)))
    assert(below.code == "include-entity-alone-exceeds-cap" && below.detail.contains("byte-cap"))
  }

  test("the fill stops at the byte cap and records it as the reason") {
    val sized = build(list(f), RuntimeArtifactConfig(maxRows = 40))
    val bound = sized.report("selected")("estimatedBytesBound").num.toInt
    // Room for f and a, but not for b: its 8 more rows need far more than 50 further bytes.
    val cap = bound + 50
    val o = build(list(f), RuntimeArtifactConfig(maxBytes = cap))
    val s = snapshot(artifact(o))
    assert(researchersWithMetrics(s) == Set(f, a))
    assert(o.report("entities")("fillStoppedAt")("id").str == b)
    assert(o.report("entities")("fillStoppedAt")("reasons").arr.map(_.str) == Vector("byte-cap"))
    assert(artifact(o).bytes.length <= cap)
  }

  test("the source must verify against its manifest hashes before anything is selected") {
    val table = "metrics/type=researcher_collaboration"
    val changed = source.updated(
      table,
      source(table).map { row =>
        val copy = ujson.read(row.render()).obj
        if (copy("researcherId").str == b) copy("publicationCount") = 99
        ujson.Obj.from(copy)
      }
    )
    val r = refusal(build(list(e), rows = changed))
    assert(r.code == "runtime-source-logical-hash-mismatch")
    val shorter = source.updated("edges/type=authored", source("edges/type=authored").drop(1))
    assert(refusal(build(list(e), rows = shorter)).code == "runtime-source-logical-hash-mismatch")
  }

  test("the reader bound refuses before any source row is read") {
    val r = refusal(build(list(e), maxSourceRows = 60))
    assert(r.code == "source-too-large-for-subset-reader")
  }

  test("the report states rule, caps, include-list hash and per-table counts") {
    val outcome = build(list(f), RuntimeArtifactConfig(maxRows = 40))
    val report = outcome.report
    assert(report("rule").str == "scholarchain.runtime-subset.v1")
    assert(report("ruleText").str.contains("ties by stable researcher ID ascending"))
    assert(report("caps")("maxRows").num == 40)
    assert(report("includeList")("normalizedSha256").str == list(f).normalizedSha256)
    assert(report("includeList")("fileSha256").str == list(f).fileSha256)
    assert(report("source")("totalRows").num == sourceRowTotal)
    val perTable =
      report("selected")("tables").arr.map(t => t("table").str -> t("rows").num.toInt).toMap
    assert(perTable.values.sum == 35)
    assert(perTable("metrics/type=researcher_collaboration") == 2)
    assert(perTable("edges/type=coauthored_with") == 4) // e-f, a-b, a-c, a-d
    assert(report("selected")("artifactSha256").str == artifact(outcome).sha256)
    assert(report("sourceRunId").str == runId)
  }

  test("default caps hold on a source larger than the artifact and the stop point is exact") {
    val n = 1400 // 8n - 2 = 11198 source rows, more than the 10000-row cap
    val big = pathSource(n)
    assert(big.values.map(_.size).sum == 8 * n - 2)
    val outcome = RuntimeArtifactSubset.build(
      manifests(big),
      new Reader(big),
      list(pathId(0))
    )
    val art = artifact(outcome)
    val s = snapshot(art)
    // Researcher 0 (an end) closes over 9 rows; each further path researcher adds 8 more rows
    // (its 4 own rows, the next edge, its support, the next node and its authored edge). The
    // largest k with 9 + 8k <= 10000 is 1248, i.e. 9993 rows and researchers 0..1248.
    assert(count(s) == 9993)
    assert(art.bytes.length <= RuntimeArtifactConfig().maxBytes)
    assert(researchersWithMetrics(s) == (0 to 1248).map(pathId).toSet)
    val stop = outcome.report("entities")("fillStoppedAt")
    assert(stop("id").str == pathId(1249) && stop("neededNewRows").num == 8)
    assert(
      stop("wouldBeTotalRows").num == 10001 && stop("reasons").arr.map(_.str) == Vector("row-cap")
    )
    assert(outcome.report("entities")("fromDegreeFill").num == 1248)
    assert(outcome.report("selected")("totalRows").num == 9993)
    // The last included researcher is complete; its right neighbor is only an endpoint node.
    val reader = store(art)
    assert(
      StorageResult.value(reader.researcherContext(pathId(1248), "all-years", 5)).get.coauthorIds ==
        Vector(pathId(1247), pathId(1249))
    )
    assert(reader.researcherContext(pathId(1249), "all-years", 5) == Missing)
  }
}
