package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.UUID
import org.scalatest.funsuite.AnyFunSuite

/** The committed Q12 benchmark questions (experiments/inputs/q12) must plan offline. The 24 marked
  * `planner: fallback` plan through the deterministic fallback of the default runtime configuration
  * (the model client always fails). The 9 marked `llm` need a model; a scripted client returns the
  * implied plan, which must pass the planner's full validation. No network and no credential is
  * used.
  */
class Q12QuestionSetPlannerSpec extends AnyFunSuite {
  private def resource(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    try new String(stream.readAllBytes(), UTF_8)
    finally stream.close()
  }
  private val config =
    RuntimeConfigLoader.fromJson(resource("/scholarchain.runtime-config.v1.json")).toOption.get
  private val repoRoot: Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .find(dir => Files.isRegularFile(dir.resolve("build.sbt")))
    .getOrElse(fail("repository root (a directory with build.sbt) not found above the working dir"))
  private val assets =
    RuntimePromptAssets.fromDirectory(repoRoot.resolve("prompts"), config).toOption.get
  private val inputs = repoRoot.resolve("experiments/inputs/q12")
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-q12-question-set",
    None,
    "synthetic-q12",
    Some("2026-11-20"),
    None,
    StableIds.newRunId(UUID.fromString("00112233-4455-4677-8899-aabbccddeeff")).toOption.get,
    Vector("Synthetic offline fixture; no observed researcher facts")
  )

  private final case class Spec(
      id: String,
      question: String,
      planner: String,
      kind: String,
      params: ujson.Value
  ) {
    def name(key: String): String = params(key)("name").str
    def window: String = params.obj.get("window").map(_.str).getOrElse(config.defaultWindowId)
  }
  private val specs: Vector[Spec] = {
    assert(Files.isRegularFile(inputs.resolve("question-specs.json")), s"missing specs in $inputs")
    ujson
      .read(Files.readString(inputs.resolve("question-specs.json"), UTF_8))("questions")
      .arr
      .toVector
      .map(q => Spec(q("id").str, q("question").str, q("planner").str, q("type").str, q("params")))
  }
  private val lines: Vector[String] =
    Files
      .readAllLines(inputs.resolve("questions.txt"), UTF_8)
      .toArray
      .toVector
      .map(_.toString)
      .filter(_.trim.nonEmpty)

  private val failingLlm = new LlmClient {
    def complete(request: StructuredLlmRequest): LlmResult = LlmResult.Failure("llm-client-failure")
  }
  private def planFallback(s: Spec): PlannerResult =
    new QueryPlannerAgent(failingLlm, config, assets).plan(s.question, "q12-" + s.id, provenance)

  private def scripted(plan: ujson.Obj): LlmClient = new LlmClient {
    def complete(request: StructuredLlmRequest): LlmResult = LlmResult.Output(
      plan.render(),
      LlmUsage(None, None),
      config.model.modelId,
      config.model.modelVersion
    )
  }
  private def planJson(
      operation: QueryOperation,
      names: Vector[String],
      windows: Vector[String],
      comparison: Vector[String] = Vector.empty
  ): ujson.Obj = ujson.Obj(
    "schemaVersion" -> config.plannerSchemaVersion,
    "status" -> "SUPPORTED",
    "operations" -> ujson.Arr(operation.wire),
    "researcherNames" -> ujson.Arr.from(names),
    "windowIds" -> ujson.Arr.from(windows),
    "comparisonWindowIds" -> ujson.Arr.from(comparison),
    "topicFilters" -> ujson.Arr(),
    "institutionFilters" -> ujson.Arr(),
    "venueFilters" -> ujson.Arr(),
    "rankingMetric" -> ujson.Null,
    "rankingMeasure" -> ujson.Null,
    "authorCountConversion" -> false,
    "unsupportedReason" -> ujson.Null
  )

  test("the committed Q12 set is 33 distinct questions, 24 fallback and 9 model-planned") {
    assert(specs.size == 33 && lines.size == 33)
    assert(specs.map(_.question) == lines, "question-specs.json and questions.txt disagree")
    assert(lines.distinct.size == 33)
    assert(specs.count(_.planner == "fallback") == 24)
    assert(
      specs.filter(_.planner == "llm").map(_.id) ==
        Vector("q06", "q08", "q11", "q17", "q19", "q22", "q28", "q30", "q33")
    )
  }

  /** Expected operation, ranking metric and measure by question type and params. */
  private def expected(s: Spec): (QueryOperation, Option[CollaborationMetric], Option[String]) = {
    def byMetric(m: String) = m match {
      case "DISTINCT_COAUTHOR_COUNT" =>
        (QueryOperation.ResearcherRanking, Some(CollaborationMetric.DistinctCoauthorCount), None)
      case "MAXIMUM_COAUTHORS_ON_ONE_PAPER" =>
        (QueryOperation.MaximumTeamSize, Some(CollaborationMetric.MaximumCoauthorsOnOnePaper), None)
      case "CROSS_COMMUNITY_DEGREE" =>
        (
          QueryOperation.BridgeRanking,
          Some(CollaborationMetric.BridgeScore),
          Some("CROSS_COMMUNITY_DEGREE")
        )
    }
    s.kind match {
      case "coauthor_breadth" | "max_team_size" => byMetric(s.params("metric").str)
      case "bridge"                             => byMetric(s.params("measure").str)
      case "topic" =>
        byMetric(s.params.obj.get("metric").map(_.str).getOrElse("DISTINCT_COAUTHOR_COUNT"))
      case "institution"   => byMetric(s.params("metric").str)
      case "direct_collab" => (QueryOperation.DirectCoauthors, None, None)
      case "shortest_path" => (QueryOperation.ShortestPath, None, None)
      case "component"     => (QueryOperation.ComponentLookup, None, None)
    }
  }
  private def names(s: Spec): Vector[String] = s.kind match {
    case "direct_collab" | "component" => Vector(s.name("researcher"))
    case "shortest_path"               => Vector(s.name("a"), s.name("b"))
    case _                             => Vector.empty
  }

  test("every one of the 24 fallback questions plans through the fallback to its expected plan") {
    val fallback = specs.filter(_.planner == "fallback")
    assert(fallback.size == 24)
    fallback.foreach { s =>
      val (operation, metric, measure) = expected(s)
      planFallback(s) match {
        case PlannerResult.Planned(p, attempts, true) =>
          val clue = s"${s.id} '${s.question}'"
          assert(attempts == 1, clue)
          assert(p.operations == Vector(operation), s"$clue operations ${p.operations}")
          assert(p.rankingMetric == metric, s"$clue metric ${p.rankingMetric}")
          assert(p.runtime.get.rankingMeasure == measure, s"$clue measure")
          assert(p.runtime.get.researcherNames == names(s), s"$clue names")
          assert(p.runtime.get.windowIds == Vector(s.window), s"$clue window")
          assert(p.runtime.get.comparisonWindowIds.isEmpty, s"$clue comparison")
          assert(p.topicFilters == s.params.obj.get("topic").map(_.str).toVector, s"$clue topic")
          assert(
            p.institutionFilters == s.params.obj.get("institution").map(_.str).toVector,
            s"$clue institution"
          )
          assert(p.venueFilters.isEmpty, s"$clue venue")
        case other => fail(s"${s.id} '${s.question}' was not Planned via fallback: $other")
      }
    }
  }

  test("the 9 model-planned questions validate against a scripted implied plan") {
    val llm = specs.filter(_.planner == "llm")
    assert(llm.size == 9)
    llm.foreach { s =>
      val implied = s.kind match {
        case "community" =>
          planJson(
            QueryOperation.CommunityComparison,
            Vector(s.name("researcher")),
            Vector(s.window)
          )
        case "temporal" =>
          val windows = Vector(s.params("from").str, s.params("to").str)
          planJson(
            QueryOperation.TemporalComparison,
            Vector(s.name("researcher")),
            windows,
            windows
          )
        case "evidence" =>
          planJson(
            QueryOperation.SemanticExplanation,
            Vector(s.name("researcher")),
            Vector(s.window)
          )
      }
      val result =
        new QueryPlannerAgent(scripted(implied), config, assets)
          .plan(s.question, "q12-" + s.id, provenance)
      result match {
        case PlannerResult.Planned(p, 1, false) =>
          val op = implied("operations")(0).str
          assert(p.operations.map(_.wire) == Vector(op), s"${s.id} operations")
          assert(p.runtime.get.researcherNames == Vector(s.name("researcher")), s"${s.id} names")
          assert(p.runtime.get.windowIds == implied("windowIds").arr.map(_.str).toVector, s.id)
          assert(
            p.runtime.get.comparisonWindowIds == implied("comparisonWindowIds").arr
              .map(_.str)
              .toVector,
            s"${s.id} comparison windows"
          )
          assert(DomainValidation.check(p).isRight, s.id)
        case other => fail(s"${s.id} '${s.question}': scripted plan was not accepted: $other")
      }
    }
  }

  test("a model plan that changes the requested windows or invents a name is rejected") {
    val temporal = specs.find(_.id == "q08").get
    val wrong = planJson(
      QueryOperation.TemporalComparison,
      Vector(temporal.name("researcher")),
      Vector("2010-2014", "through-2009"),
      Vector("2010-2014", "through-2009")
    )
    // A reordered pair is a different request: the plan is refused and the fallback (which has no
    // temporal grammar) cannot plan it either, so it is never a model-planned success.
    val reordered = new QueryPlannerAgent(scripted(wrong), config, assets)
      .plan(temporal.question, "q12-wrong", provenance)
    assert(reordered.isInstanceOf[PlannerResult.Unsupported], reordered.toString)
    val community = specs.find(_.id == "q06").get
    val invented =
      planJson(QueryOperation.CommunityComparison, Vector("Someone Else"), Vector("all-years"))
    val rejected = new QueryPlannerAgent(scripted(invented), config, assets)
      .plan(community.question, "q12-invented", provenance)
    assert(rejected.isInstanceOf[PlannerResult.Unsupported], rejected.toString)
  }

  test("the fallback plans 'explain the topic' (the quoted filter must not hide the pattern)") {
    val q = "Explain the topic \"Cognitive Computing and Networks\""
    planFallback(Spec("topic-x", q, "fallback", "evidence", ujson.Obj())) match {
      case PlannerResult.Planned(p, _, true) =>
        assert(p.operations == Vector(QueryOperation.SemanticExplanation))
        assert(p.topicFilters == Vector("Cognitive Computing and Networks"))
        assert(p.runtime.get.researcherNames.isEmpty)
      case other => fail(s"not planned: $other")
    }
    val research = "Explain the research topic \"Cognitive Computing and Networks\""
    assert(
      planFallback(Spec("topic-y", research, "fallback", "evidence", ujson.Obj()))
        .isInstanceOf[PlannerResult.Planned]
    )
  }
}
