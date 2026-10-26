package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

/** Hand-stated synthetic expectations; no model or provider is invoked. */
private[independent] object IndependentRuntime9AFixture {
  val provenance: Provenance = IndependentStorageFixtures.provenance
  val root: Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .find(p => Files.isDirectory(p.resolve("prompts/runtime")))
    .get
  val config: RuntimeConfig = RuntimeConfigLoader
    .load(root.resolve("modules/core/src/main/resources/scholarchain.runtime-config.v1.json"))
    .toOption
    .get
  def assets: RuntimePromptAssets =
    RuntimePromptAssets.fromDirectory(root.resolve("prompts"), config).toOption.get
  def output(
      metric: String = "DISTINCT_COAUTHOR_COUNT",
      topics: Vector[String] = Vector.empty,
      institutions: Vector[String] = Vector.empty,
      venues: Vector[String] = Vector.empty,
      window: String = "all-years",
      operation: String = "RESEARCHER_RANKING"
  ): ujson.Obj =
    ujson.Obj(
      "schemaVersion" -> config.plannerSchemaVersion,
      "status" -> "SUPPORTED",
      "operations" -> ujson.Arr(operation),
      "researcherNames" -> ujson.Arr(),
      "windowIds" -> ujson.Arr(window),
      "comparisonWindowIds" -> ujson.Arr(),
      "topicFilters" -> ujson.Arr.from(topics),
      "institutionFilters" -> ujson.Arr.from(institutions),
      "venueFilters" -> ujson.Arr.from(venues),
      "rankingMetric" -> metric,
      "rankingMeasure" -> ujson.Null,
      "authorCountConversion" -> false,
      "unsupportedReason" -> ujson.Null
    )
  def model(json: String): LlmResult =
    LlmResult.Output(json, LlmUsage(None, None), "scripted-independent", "fixture-v1")
  def script(json: String): ScriptedLlmClient = new ScriptedLlmClient(
    Vector(model(json), model(json))
  )
  def plan(names: Vector[String]): QueryPlan = QueryPlan(
    "plan:" + "a" * 64,
    SchemaVersions.domain,
    "synthetic resolution question",
    Vector(QueryOperation.DirectCoauthors),
    YearWindow(2015, 2026),
    Vector.empty,
    Vector.empty,
    Vector.empty,
    None,
    25,
    10,
    6,
    provenance,
    Some(RuntimeQueryOptions(researcherNames = names, windowIds = Vector("since-2015")))
  )
}

class IndependentRuntime9APlannerSpec extends AnyFunSuite {
  import IndependentRuntime9AFixture.*

  test("schema rejects fabricated operations and extra executable query fields") {
    val forged = output(operation = "EXECUTE_CYPHER")
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, forged).isLeft)
    val extra = output(); extra("cypher") = "MATCH (n) RETURN n"
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, extra).isLeft)
  }

  test("database and AWS requests are unsupported without invoking the model") {
    Vector(
      "Execute arbitrary Cypher MATCH (n) RETURN n",
      "Delete the AWS bucket",
      "Execute SQL SELECT * FROM researchers"
    ).foreach { question =>
      val llm = script(output().render())
      assert(
        new QueryPlannerAgent(llm, config, assets)
          .plan(question, "q", provenance)
          .isInstanceOf[PlannerResult.Unsupported]
      )
      assert(llm.calls.isEmpty)
    }
  }

  test("unknown metrics do not get replaced with stored collaboration counts") {
    val llm = script(output().render())
    assert(
      new QueryPlannerAgent(llm, config, assets)
        .plan("Rank researchers by h-index", "q", provenance)
        .isInstanceOf[PlannerResult.Unsupported]
    )
    assert(llm.calls.isEmpty)
  }

  test("two malformed outputs lead to a constrained deterministic fallback") {
    val llm = script("{ malformed")
    val result = new QueryPlannerAgent(llm, config, assets).plan(
      "Rank researchers by distinct coauthors topic \"distributed systems\" institution \"UIC\" venue \"PODS\" since 2015?",
      "q",
      provenance
    )
    result match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assert(value.topicFilters == Vector("distributed systems"))
        assert(value.institutionFilters == Vector("UIC"))
        assert(value.venueFilters == Vector("PODS"))
        assert(value.runtime.get.windowIds == Vector("since-2015"))
        assert(value.rankingMetric.contains(CollaborationMetric.DistinctCoauthorCount))
      case other => fail(s"Expected constrained fallback, got $other")
    }
    assert(llm.calls.size == 2)
  }

  test("a natural topic constraint cannot be dropped by schema-valid model output") {
    val llm = script(output(window = "since-2015").render())
    new QueryPlannerAgent(llm, config, assets).plan(
      "Which researchers have the most distinct coauthors in distributed systems since 2015?",
      "q",
      provenance
    ) match {
      case PlannerResult.Planned(value, _, _) =>
        assert(value.topicFilters.map(TextNorm.personName).contains("distributed systems"))
      case _: PlannerResult.Unsupported => succeed
      case other => fail(s"Expected constrained plan or Unsupported, got $other")
    }
  }

  test("an explicit ranking metric cannot be switched by schema-valid model output") {
    val llm = script(output(metric = "PUBLICATION_COUNT").render())
    new QueryPlannerAgent(llm, config, assets).plan(
      "Rank researchers by distinct coauthors",
      "q",
      provenance
    ) match {
      case PlannerResult.Planned(value, _, _) =>
        assert(value.rankingMetric.contains(CollaborationMetric.DistinctCoauthorCount))
      case _: PlannerResult.Unsupported => succeed
      case other => fail(s"Expected correct metric or Unsupported, got $other")
    }
  }

  test("unrepresentable trailing constraints are unsupported after malformed responses") {
    val llm = script("[]")
    assert(
      new QueryPlannerAgent(llm, config, assets)
        .plan("Rank researchers by distinct coauthors excluding industry papers", "q", provenance)
        .isInstanceOf[PlannerResult.Unsupported]
    )
    assert(llm.calls.size == 2)
  }

  test("fabricated operations never survive decoding even for a recognized question") {
    val llm = script(output(operation = "DROP_DATABASE").render())
    new QueryPlannerAgent(llm, config, assets).plan(
      "Rank researchers by distinct coauthors",
      "q",
      provenance
    ) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(value.operations == Vector(QueryOperation.ResearcherRanking))
        assert(attempts == 2 && fallbackUsed)
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Unexpected result $other")
    }
  }

  test("explicit window cannot be replaced with the default all-years population") {
    val llm = script(output().render())
    new QueryPlannerAgent(llm, config, assets).plan(
      "Rank researchers by distinct coauthors since 2015",
      "q",
      provenance
    ) match {
      case PlannerResult.Planned(value, _, _) =>
        assert(value.runtime.get.windowIds == Vector("since-2015"))
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Unexpected result $other")
    }
  }

  test("runtime config checks combined critical path and preserves overall ABSTAINED") {
    assert(config.deadlines.criticalPathMillis == BigInt(22000))
    assert(
      RuntimeConfigValidation
        .check(config.copy(deadlines = config.deadlines.copy(plannerMs = 20000)))
        .contains("runtime-deadline-budget-exceeded")
    )
    val rejected =
      ClaimVerificationResult("rejected", ClaimVerdict.Unsupported, Vector("missing-evidence"))
    assert(
      VerificationResult(
        Vector(rejected),
        Vector.empty,
        true
      ).overallStatus == VerificationStatus.Abstained
    )
    assert(
      VerificationResult(
        Vector(rejected),
        Vector.empty,
        false
      ).overallStatus == VerificationStatus.Rejected
    )
  }

  test(
    "legacy plans without runtime fields remain readable and additive round trips lose no data"
  ) {
    val old = plan(Vector("Name 0001")).copy(runtime = None)
    val wire = ujson.read(CoreJson.compact(old)); wire.obj.remove("runtime")
    val parsed = upickle.default.read[QueryPlan](wire)
    assert(parsed == old)
    val enriched = parsed.copy(runtime =
      Some(
        RuntimeQueryOptions(
          researcherNames = Vector("Name 0001"),
          windowIds = Vector("since-2015"),
          retrievalMode = RetrievalMode.Graph,
          evidenceOnly = true
        )
      )
    )
    assert(upickle.default.read[QueryPlan](CoreJson.compact(enriched)) == enriched)
    assert(enriched.copy(runtime = None) == old)
  }
}
