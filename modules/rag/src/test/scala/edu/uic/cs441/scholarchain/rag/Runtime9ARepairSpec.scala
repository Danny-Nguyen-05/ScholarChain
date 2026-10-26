package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.{Files, Path}

/** Repair expectations are hand-transcribed from requested metrics and a two-person fixture. */
class Runtime9ARepairSpec extends AnyFunSuite {
  private val config = {
    val input = getClass.getResourceAsStream("/scholarchain.runtime-config.v1.json")
    try
      RuntimeConfigLoader
        .fromJson(new String(input.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8))
        .toOption
        .get
    finally input.close()
  }
  private val root = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("prompts"))
    .find(Files.isDirectory(_))
    .get
  private val assets = RuntimePromptAssets.fromDirectory(root, config).toOption.get
  private val run = "run:00112233-4455-4677-8899-aabbccddeeff"
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-repair",
    None,
    "synthetic-repair-snapshot",
    None,
    None,
    run,
    Vector("Synthetic offline repair fixture")
  )
  private val a = StableIds.researcherIdFromDblpName("repair-policy", "Name 0001").toOption.get
  private val b = StableIds.researcherIdFromDblpName("repair-policy", "Name 0002").toOption.get
  private case class Expected(
      question: String,
      metric: Option[String],
      operation: String,
      measure: Option[String] = None,
      conversion: Boolean = false
  )
  private val requests = Vector(
    Expected(
      "Rank researchers by publication count",
      Some("PUBLICATION_COUNT"),
      "RESEARCHER_RANKING"
    ),
    Expected(
      "Rank researchers by distinct coauthors",
      Some("DISTINCT_COAUTHOR_COUNT"),
      "RESEARCHER_RANKING"
    ),
    Expected(
      "Rank researchers by total coauthor occurrences",
      Some("TOTAL_COAUTHOR_OCCURRENCES"),
      "RESEARCHER_RANKING"
    ),
    Expected(
      "Rank researchers by average coauthors per paper",
      Some("AVERAGE_COAUTHORS_PER_PAPER"),
      "RESEARCHER_RANKING"
    ),
    Expected(
      "Rank researchers by maximum coauthors on one paper",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE"
    ),
    Expected(
      "Which researchers have the largest team size?",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE"
    ),
    Expected("Rank researchers by weighted degree", Some("WEIGHTED_DEGREE"), "RESEARCHER_RANKING"),
    Expected("Rank researchers by coreness", Some("CORENESS"), "RESEARCHER_RANKING"),
    Expected(
      "Rank bridge researchers by cross-community degree",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_DEGREE")
    ),
    Expected(
      "Rank bridge researchers by cross-community weight",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_WEIGHT")
    ),
    Expected(
      "Rank bridge researchers by communities connected",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("COMMUNITIES_CONNECTED")
    ),
    Expected(
      "Rank bridge researchers by participation coefficient",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("PARTICIPATION_COEFFICIENT")
    ),
    Expected(
      "Which researchers are the strongest bridges?",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_DEGREE")
    ),
    Expected(
      "Show strongest repeated collaborations",
      None,
      "RESEARCHER_RANKING",
      Some("JOINT_PUBLICATION_COUNT")
    ),
    Expected(
      "Rank researchers by maximum total authors on one paper",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE",
      None,
      true
    )
  )
  private def json(e: Expected, window: String = config.defaultWindowId): ujson.Obj = ujson.Obj(
    "schemaVersion" -> config.plannerSchemaVersion,
    "status" -> "SUPPORTED",
    "operations" -> ujson.Arr(e.operation),
    "researcherNames" -> ujson.Arr(),
    "windowIds" -> ujson.Arr(window),
    "comparisonWindowIds" -> ujson.Arr(),
    "topicFilters" -> ujson.Arr(),
    "institutionFilters" -> ujson.Arr(),
    "venueFilters" -> ujson.Arr(),
    "rankingMetric" -> e.metric.map(ujson.Str(_)).getOrElse(ujson.Null),
    "rankingMeasure" -> e.measure.map(ujson.Str(_)).getOrElse(ujson.Null),
    "authorCountConversion" -> e.conversion,
    "unsupportedReason" -> ujson.Null
  )
  private def planOutput(q: String, value: ujson.Obj, c: RuntimeConfig = config): PlannerResult = {
    val reply =
      LlmResult.Output(value.render(), LlmUsage(None, None), "offline-fixture", "fixture-v1")
    new QueryPlannerAgent(new ScriptedLlmClient(Vector(reply, reply)), c, assets)
      .plan(q, "repair-query", provenance)
  }
  private def assertFields(
      p: QueryPlan,
      e: Expected,
      window: String = config.defaultWindowId
  ): Unit = {
    assert(p.rankingMetric.map(_.wire) == e.metric)
    assert(p.operations.map(_.wire) == Vector(e.operation))
    assert(p.runtime.get.rankingMeasure == e.measure)
    assert(p.runtime.get.windowIds == Vector(window) && p.runtime.get.comparisonWindowIds.isEmpty)
    assert(p.runtime.get.authorCountConversion == e.conversion)
  }
  requests.foreach { e =>
    test(s"B1 ground complete explicit intent: ${e.question}") {
      planOutput(e.question, json(e)) match {
        case PlannerResult.Planned(p, 1, false) => assertFields(p, e)
        case other => fail(s"Expected first-call exact intent, got $other")
      }
      val wrong = json(e)
      if (e.measure.nonEmpty)
        wrong("rankingMeasure") =
          (if (e.measure.contains("PARTICIPATION_COEFFICIENT")) ujson.Str("CROSS_COMMUNITY_DEGREE")
           else ujson.Str("PARTICIPATION_COEFFICIENT"))
      else
        wrong("rankingMetric") =
          (if (e.metric.contains("DISTINCT_COAUTHOR_COUNT")) ujson.Str("PUBLICATION_COUNT")
           else ujson.Str("DISTINCT_COAUTHOR_COUNT"))
      planOutput(e.question, wrong) match {
        case PlannerResult.Planned(p, 2, true) => assertFields(p, e)
        case _: PlannerResult.Unsupported      => succeed
        case other => fail(s"Disagreement must retry and preserve intent or abstain, got $other")
      }
    }
  }
  test(
    "B1 exact cumulative explicit and default windows cannot narrow or acquire extra comparisons"
  ) {
    val e = requests(1)
    val cases = Vector(
      (e.question, "all-years"),
      (e.question + " since 2015", "since-2015"),
      (e.question + " window 2020-2026", "2020-2026")
    )
    cases.foreach { (q, window) =>
      planOutput(q, json(e, window)) match {
        case PlannerResult.Planned(p, 1, false) => assertFields(p, e, window)
        case other => fail(s"Correct stored window must remain supported: $other")
      }
      val wrong = json(e, if (window == "all-years") "2020-2026" else "2015-2019")
      wrong("comparisonWindowIds") = ujson.Arr("2010-2014", "2015-2019")
      planOutput(q, wrong) match {
        case PlannerResult.Planned(p, 2, true) => assertFields(p, e, window)
        case _: PlannerResult.Unsupported      => succeed
        case other                             => fail(s"Wrong window must not survive: $other")
      }
    }
  }
  test("B1 operation measure conversion and configurable defaults cannot be model overrides") {
    val max = requests(5); val wrongOp = json(max);
    wrongOp("operations") = ujson.Arr("RESEARCHER_RANKING")
    val cases = Vector(
      (max, wrongOp),
      (requests(3), { val v = json(requests(3)); v("authorCountConversion") = true; v }),
      (requests.last, { val v = json(requests.last); v("authorCountConversion") = false; v }),
      (
        requests(1),
        { val v = json(requests(1)); v("rankingMeasure") = "PARTICIPATION_COEFFICIENT"; v }
      )
    )
    cases.foreach { (e, v) =>
      planOutput(e.question, v) match {
        case PlannerResult.Planned(p, 2, true) => assertFields(p, e)
        case _: PlannerResult.Unsupported      => succeed
        case other => fail(s"Unrequested operation/measure/conversion: $other")
      }
    }
    val c =
      config.copy(defaultRankingMeasure = "CROSS_COMMUNITY_WEIGHT", defaultWindowId = "2020-2026")
    val bridge = requests(12).copy(measure = Some("CROSS_COMMUNITY_WEIGHT"))
    planOutput(bridge.question, json(bridge, "2020-2026"), c) match {
      case PlannerResult.Planned(p, 1, false) => assertFields(p, bridge, "2020-2026")
      case other                              => fail(s"Defaults must come from config: $other")
    }
  }

  private def resolutionPlan(name: String, window: String = "since-2015"): QueryPlan = QueryPlan(
    "plan:" + StableIds.sha256Hex("resolver-repair"),
    SchemaVersions.domain,
    "Synthetic resolver request",
    Vector(QueryOperation.DirectCoauthors),
    YearWindow(2015, 2026),
    Vector.empty,
    Vector.empty,
    Vector.empty,
    None,
    config.retrieval.graphLimit,
    config.retrieval.vectorLimit,
    config.retrieval.maxPathDepth,
    provenance,
    Some(RuntimeQueryOptions(researcherNames = Vector(name), windowIds = Vector(window)))
  )
  private def row(name: String, id: String, source: String): EntityLink = EntityLink(
    "name",
    TextNorm.personName(name),
    "repair-policy",
    source,
    id,
    name,
    Vector.empty,
    None,
    run,
    Vector("source-ref:" + source)
  )
  test(
    "B2 many observations for one identity resolve and provenance lists disclose their distinct totals"
  ) {
    val cache = new InMemoryEntityLinkCache
    (0 until 30).foreach { i =>
      assert(
        StorageResult.successful(
          cache.putLink(
            row("Name 0001", a, s"source-$i").copy(
              affiliations = Vector(s"institution-$i"),
              evidenceRefs = Vector(s"ref-$i", "shared-ref")
            )
          )
        )
      )
    }
    val c = config.copy(resolver = RuntimeResolverConfig(2, 3, 4, 2, 1))
    new ResearcherResolverAgent(cache, c).resolve(resolutionPlan("Name 0001")) match {
      case ResolverResult.Resolved(Vector(person)) =>
        assert(
          person.sourceIds.size == 3 && person.evidenceRefs.size == 4 && person.affiliations.size == 2
        )
        assert(
          person.provenanceSummary.contains(
            ResearcherCandidateProvenanceSummary(30, 31, 30, 1, true)
          )
        )
        assert(person.confidence.isEmpty)
      case other => fail(s"Raw observations are not distinct identities: $other")
    }
  }
  test("B2 overflow returns bounded Ambiguous candidates with exact total instead of failure") {
    val cache = new InMemoryEntityLinkCache
    val ids = (1 to 5).map(i => "researcher:dblp:" + f"$i%064x").toVector
    ids.zipWithIndex.foreach((id, i) =>
      assert(StorageResult.successful(cache.putLink(row("Name", id, s"source-$i"))))
    )
    val c = config.copy(
      resolver = RuntimeResolverConfig(maxDistinctCandidates = 2),
      retrieval = config.retrieval.copy(graphLimit = 1)
    )
    new ResearcherResolverAgent(cache, c).resolve(resolutionPlan("Name")) match {
      case ResolverResult.Ambiguous("Name", people, 5, true) =>
        assert(people.map(_.researcherId) == ids.sorted.take(2))
      case other => fail(s"Overflow must preserve ambiguity with disclosure: $other")
    }
  }
  test("B3 actual artifact composition preserves absent identities and rejects unknown windows") {
    val lineage = SparkLineage(
      run,
      "synthetic-repair-snapshot",
      run,
      "repair-policy",
      "e" * 64,
      Vector.empty,
      Vector.empty
    )
    val context = SparkRecordContext(SchemaVersions.sparkAnalytics, run, None, lineage)
    def node(id: String, label: String) = GraphNode(
      id,
      SchemaVersions.domain,
      GraphNodeClass.Researcher,
      label,
      Vector.empty,
      provenance
    )
    def metric(id: String, window: String) = ResearcherMetricsDetail(
      context.copy(windowId = Some(window)),
      id,
      "repair-metrics",
      1,
      0,
      0,
      0.0,
      0,
      Vector("work:dblp:synthetic/solo"),
      1,
      0,
      "component:" + "f" * 64,
      None,
      Some(0)
    )
    def obj[A: upickle.default.Writer](v: A): ujson.Obj =
      ujson.Obj.from(upickle.default.writeJs(v).obj)
    val rows: Map[String, Vector[ujson.Obj]] = Map(
      "nodes/type=researcher" -> Vector(obj(node(a, "Name 0001")), obj(node(b, "Name 0002"))),
      "metrics/type=researcher_collaboration" -> Vector(
        obj(metric(a, "all-years")),
        obj(metric(b, "since-2015"))
      ),
      "metrics/type=communities" -> Vector.empty,
      "metrics/type=community_summaries" -> Vector.empty,
      "metrics/type=bridges" -> Vector.empty,
      "metrics/type=temporal_changes" -> Vector.empty,
      "edges/type=coauthored_with" -> Vector.empty,
      "edges/type=coauthored_with_support" -> Vector.empty
    )
    val artifacts = new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeArtifactStore(
      context,
      rows,
      Vector("all-years", "since-2015")
    )
    assert(artifacts.researcherContext(a, "since-2015", 10) == StorageResult.Missing)
    val cache = new InMemoryEntityLinkCache
    cache.putLink(row("Name 0001", a, "exact-a")); cache.putLink(row("Name", a, "base-a"));
    cache.putLink(row("Name", b, "base-b"))
    val resolver = new ResearcherResolverAgent(cache, config, Some(artifacts))
    resolver.resolve(resolutionPlan("Name 0001")) match {
      case ResolverResult.Resolved(Vector(person)) =>
        assert(
          person.researcherId == a && person.coauthorContext.isEmpty && person.coauthorContextTruncated.isEmpty
        )
      case other => fail(s"Absence from a period cannot remove identity: $other")
    }
    resolver.resolve(resolutionPlan("Name")) match {
      case ResolverResult.Ambiguous("Name", people, 2, false) =>
        assert(people.map(_.researcherId).toSet == Set(a, b))
      case other => fail(s"Absent homonym must remain plausible: $other")
    }
    assert(
      resolver.resolve(resolutionPlan("Name 0001", "unknown-window")) == ResolverResult.Failed(
        "resolver-window-not-stored"
      )
    )
  }
}
