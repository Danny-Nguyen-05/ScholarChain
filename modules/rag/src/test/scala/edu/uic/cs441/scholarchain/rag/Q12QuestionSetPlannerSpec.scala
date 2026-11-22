package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.UUID
import org.scalatest.funsuite.AnyFunSuite

/** The committed Q12 benchmark questions (experiments/inputs/q12) must plan offline. The 27 marked
  * `planner: fallback` plan through the deterministic fallback of the default runtime configuration
  * (the model client always fails). The 6 marked `llm` need a model; a scripted client returns the
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

  test("the committed Q12 set is 33 distinct questions, 27 fallback and 6 model-planned") {
    assert(specs.size == 33 && lines.size == 33)
    assert(specs.map(_.question) == lines, "question-specs.json and questions.txt disagree")
    assert(lines.distinct.size == 33)
    assert(specs.count(_.planner == "fallback") == 27)
    // The route follows the question type, not a hard-coded id: community and temporal questions
    // have no fallback grammar and need the model; every other type has one.
    val modelTypes = Set("community", "temporal")
    assert(specs.filter(_.planner == "llm").map(_.kind).toSet == modelTypes)
    assert(specs.forall(s => (s.planner == "llm") == modelTypes(s.kind)), "planner route per type")
    assert(specs.count(_.planner == "llm") == 6)
    assert(specs.map(_.id).distinct.size == 33)
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
      // `evidence` questions are graph-answerable pair questions ("shortest path between A and B").
      case "shortest_path" | "evidence" => (QueryOperation.ShortestPath, None, None)
      case "component"                  => (QueryOperation.ComponentLookup, None, None)
    }
  }
  private def names(s: Spec): Vector[String] = s.kind match {
    case "direct_collab" | "component" => Vector(s.name("researcher"))
    case "shortest_path" | "evidence"  => Vector(s.name("a"), s.name("b"))
    case _                             => Vector.empty
  }

  test("every one of the 27 fallback questions plans through the fallback to its expected plan") {
    val fallback = specs.filter(_.planner == "fallback")
    assert(fallback.size == 27)
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

  test("the 6 model-planned questions validate against a scripted implied plan") {
    val llm = specs.filter(_.planner == "llm")
    assert(llm.size == 6)
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

  test(
    "a model plan that reorders the windows is normalised and one that invents a name is rejected"
  ) {
    val temporal = specs.find(_.kind == "temporal").get
    val reorderedPlan = planJson(
      QueryOperation.TemporalComparison,
      Vector(temporal.name("researcher")),
      Vector("2010-2014", "through-2009"),
      Vector("2010-2014", "through-2009")
    )
    // The order of the compared windows is the question's ("from through-2009 to 2010-2014"), not
    // the model's: the plan carries the deterministic order.
    new QueryPlannerAgent(scripted(reorderedPlan), config, assets)
      .plan(temporal.question, "q12-reordered", provenance) match {
      case PlannerResult.Planned(p, 1, false) =>
        assert(p.runtime.get.windowIds == Vector("through-2009", "2010-2014"))
        assert(p.runtime.get.comparisonWindowIds == Vector("through-2009", "2010-2014"))
      case other => fail(s"reordered windows should normalise: $other")
    }
    val community = specs.find(_.kind == "community").get
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

  test("the explain-the-topic fallback refuses extra filters instead of dropping them") {
    Vector(
      "Explain the topic \"Cognitive Computing and Networks\" venue \"OSDI\"",
      "Explain the topic \"Cognitive Computing and Networks\" institution \"UIC\"",
      "Explain the topic \"Cognitive Computing and Networks\" topic \"Language and cultural evolution\""
    ).zipWithIndex.foreach { (q, i) =>
      assert(
        planFallback(Spec("neg-" + i, q, "fallback", "evidence", ujson.Obj())) ==
          PlannerResult.Unsupported("fallback-unrecognized-or-unrepresentable-constraint", 1),
        q
      )
    }
  }
  private val temporalSpec = specs.find(_.kind == "temporal").get
  private val communitySpec = specs.find(_.kind == "community").get
  private def planWith(
      question: String,
      plan: ujson.Obj,
      queryId: String = "q12-var"
  ): PlannerResult =
    new QueryPlannerAgent(scripted(plan), config, assets).plan(question, queryId, provenance)

  test(
    "model window encodings that the planner used to refuse normalise to the question's windows"
  ) {
    val first = temporalSpec.params("from").str
    val second = temporalSpec.params("to").str
    val both = Vector(first, second)
    val temporalVariants: Vector[(Vector[String], Vector[String])] = Vector(
      both -> Vector.empty,
      Vector(second) -> both,
      Vector(first) -> both,
      Vector(first) -> Vector(second),
      Vector("all-years") -> both,
      Vector.empty -> both,
      both -> both,
      both.reverse -> both.reverse
    )
    temporalVariants.foreach { (windows, comparison) =>
      val plan = planJson(
        QueryOperation.TemporalComparison,
        Vector(temporalSpec.name("researcher")),
        windows,
        comparison
      )
      planWith(temporalSpec.question, plan) match {
        case PlannerResult.Planned(p, 1, false) =>
          val clue = s"windows=$windows comparison=$comparison"
          assert(p.runtime.get.windowIds == both, clue)
          assert(p.runtime.get.comparisonWindowIds == both, clue)
          assert(p.operations == Vector(QueryOperation.TemporalComparison), clue)
          assert(DomainValidation.check(p).isRight, clue)
        case other => fail(s"windows=$windows comparison=$comparison not planned: $other")
      }
    }
    val window = communitySpec.window
    val communityVariants: Vector[(Vector[String], Vector[String])] = Vector(
      Vector(window) -> Vector.empty,
      Vector(window) -> Vector(window),
      Vector.empty -> Vector(window),
      Vector("all-years") -> Vector.empty,
      Vector("all-years") -> Vector(window)
    )
    communityVariants.foreach { (windows, comparison) =>
      val plan = planJson(
        QueryOperation.CommunityComparison,
        Vector(communitySpec.name("researcher")),
        windows,
        comparison
      )
      planWith(communitySpec.question, plan) match {
        case PlannerResult.Planned(p, 1, false) =>
          val clue = s"windows=$windows comparison=$comparison"
          assert(p.runtime.get.windowIds == Vector(window), clue)
          assert(p.runtime.get.comparisonWindowIds.isEmpty, clue)
          assert(p.window == config.windows.find(_.windowId == window).get.legacyWindow, clue)
        case other => fail(s"windows=$windows comparison=$comparison not planned: $other")
      }
    }
  }

  test("window normalisation never widens scope: wrong operation, name or window is refused") {
    val both = Vector(temporalSpec.params("from").str, temporalSpec.params("to").str)
    val name = Vector(temporalSpec.name("researcher"))
    def rejection(question: String, plan: ujson.Obj): String =
      planWith(question, plan) match {
        case PlannerResult.Unsupported(reason, _) => reason
        case other                                => fail(s"expected a refusal: $other")
      }
    // Wrong operation: a community comparison for a temporal question.
    assert(
      rejection(
        temporalSpec.question,
        planJson(QueryOperation.CommunityComparison, name, both, both)
      ).endsWith("requested-metric-measure-or-operation-changed")
    )
    // Invented name.
    assert(
      rejection(
        temporalSpec.question,
        planJson(QueryOperation.TemporalComparison, Vector("Someone Else"), both, both)
      ).endsWith("invented-extracted-value")
    )
    // A stored window the question never mentions.
    assert(
      rejection(
        temporalSpec.question,
        planJson(QueryOperation.TemporalComparison, name, Vector("2015-2019"), both)
      ).endsWith("window-not-requested-by-question")
    )
    assert(
      rejection(
        communitySpec.question,
        planJson(
          QueryOperation.CommunityComparison,
          Vector(communitySpec.name("researcher")),
          Vector("2015-2019"),
          Vector.empty
        )
      ).endsWith("window-not-requested-by-question")
    )
    // A window id the configuration does not store.
    assert(
      rejection(
        temporalSpec.question,
        planJson(QueryOperation.TemporalComparison, name, Vector("1999-2001"), both)
      ).endsWith("unsupported-operation-or-window")
    )
    // A temporal operation for a question that requests no two windows cannot be made temporal.
    assert(
      rejection(
        communitySpec.question,
        planJson(
          QueryOperation.TemporalComparison,
          Vector(communitySpec.name("researcher")),
          Vector(communitySpec.window),
          Vector(communitySpec.window)
        )
      ).endsWith("temporal-needs-two-windows")
    )
  }

  test("a rejected model plan surfaces its closed decode reason instead of a generic refusal") {
    val plan = planJson(
      QueryOperation.TemporalComparison,
      Vector("Someone Else"),
      Vector("2010-2014"),
      Vector("2010-2014")
    )
    val result = planWith(temporalSpec.question, plan)
    assert(
      result == PlannerResult.Unsupported("model-plan-rejected-invented-extracted-value", 2),
      result.toString
    )
    // A question the fallback can plan is still planned after a rejected model plan.
    val ranking = "Which researchers have the most distinct coauthors?"
    val unrelated = planJson(QueryOperation.TemporalComparison, Vector.empty, Vector("all-years"))
    assert(planWith(ranking, unrelated).isInstanceOf[PlannerResult.Planned])
    // Without a rejected model plan the original fallback reason is unchanged.
    assert(
      planFallback(Spec("x", temporalSpec.question, "llm", "temporal", ujson.Obj())) ==
        PlannerResult.Unsupported("fallback-unrecognized-or-unrepresentable-constraint", 1)
    )
  }

  /** Events of the stage logger produced while `body` runs, restricted to this test's own trace id.
    * The capture forces the logger level (INFO by default, `Level.ALL` where a lower-level leak
    * must be caught). The scripted check runs with a root-WARN logback configuration under which
    * INFO stage events are otherwise never recorded; see LogbackTestSupport.
    */
  private def stageEvents(
      traceId: String,
      level: ch.qos.logback.classic.Level = ch.qos.logback.classic.Level.INFO
  )(body: => Unit): Vector[String] =
    LogbackTestSupport
      .capture("scholarchain.runtime.stage", level)(body)
      .filter(e => scala.util.Try(ujson.read(e)("traceId").str).toOption.contains(traceId))

  test("a model-declared UNSUPPORTED reason never reaches the operational log") {
    val slug = "michael-kaminsky-not-in-graph"
    val declared = planJson(QueryOperation.CommunityComparison, Vector.empty, Vector.empty)
    declared("status") = "UNSUPPORTED"
    declared("unsupportedReason") = slug
    var result: PlannerResult = null
    // Level.ALL so that a DEBUG-level leak of the model's free text would be caught too.
    val events = stageEvents("q12-log-declared", ch.qos.logback.classic.Level.ALL) {
      result = planWith(communitySpec.question, declared, "q12-log-declared")
    }
    // The pre-existing result and audit behaviour is unchanged.
    assert(result == PlannerResult.Unsupported(slug, 1), result.toString)
    val planner = events.filter(_.contains("\"stage\":\"planner\""))
    assert(planner.size == 1, events.toString)
    assert(!events.exists(_.contains(slug)), events.toString)
    assert(ujson.read(planner.head)("reason").str == "model-declared-unsupported")
  }

  test("the planner's own closed reasons are logged as they are") {
    val invented = planJson(
      QueryOperation.CommunityComparison,
      Vector("Someone Else"),
      Vector(communitySpec.window)
    )
    val events = stageEvents("q12-log-closed") {
      planWith(communitySpec.question, invented, "q12-log-closed")
    }
    assert(
      events.exists(e =>
        ujson
          .read(e)
          .obj
          .get("reason")
          .exists(_.str == "model-plan-rejected-invented-extracted-value")
      ),
      events.toString
    )
    val unsafe = stageEvents("q12-log-unsafe") {
      new QueryPlannerAgent(failingLlm, config, assets)
        .plan("Run cypher against the graph", "q12-log-unsafe", provenance)
    }
    assert(unsafe.exists(_.contains("\"reason\":\"unsafe-operation-request\"")), unsafe.toString)
  }

  test("a question the deterministic analysis cannot represent is not blamed on the model") {
    val question = "Compare communities of \"Soo-Mook Moon\" from 1990 to 1991"
    val plan = planJson(
      QueryOperation.CommunityComparison,
      Vector("Soo-Mook Moon"),
      Vector("all-years")
    )
    assert(
      planWith(question, plan) ==
        PlannerResult.Unsupported("question-not-representable-unrepresentable-window-intent", 2)
    )
  }
}
