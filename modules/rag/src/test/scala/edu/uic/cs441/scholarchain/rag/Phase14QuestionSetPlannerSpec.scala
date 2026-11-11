package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.UUID

/** The committed 14C live question set must plan through the deterministic fallback of the default
  * runtime configuration. Offline: the model client always fails, so every line takes the fallback
  * and decode path (including coveredQuestion); no network or credential is used.
  */
class Phase14QuestionSetPlannerSpec extends AnyFunSuite {
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
  private val questionsFile = repoRoot.resolve("experiments/inputs/14c/questions.txt")
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-phase14-question-set",
    None,
    "synthetic-phase14",
    Some("2026-11-10"),
    None,
    StableIds.newRunId(UUID.fromString("00112233-4455-4677-8899-aabbccddeeff")).toOption.get,
    Vector("Synthetic offline fixture; no observed researcher facts")
  )
  private val failingLlm = new LlmClient {
    def complete(request: StructuredLlmRequest): LlmResult = LlmResult.Failure("llm-client-failure")
  }
  private val planner = new QueryPlannerAgent(failingLlm, config, assets)
  private def plan(question: String, id: String): PlannerResult =
    planner.plan(question, id, provenance)

  private def lines: Vector[String] = {
    assert(
      Files.isRegularFile(questionsFile),
      s"missing committed question set: experiments/inputs/14c/questions.txt under $repoRoot"
    )
    Files
      .readAllLines(questionsFile, UTF_8)
      .toArray
      .toVector
      .map(_.toString)
      .filter(_.trim.nonEmpty)
  }

  test("the committed 14C question set has exactly 40 non-blank lines") {
    assert(lines.size == 40)
    assert(lines.distinct.size == 40)
  }

  test("every one of the 40 lines is Planned through the fallback path") {
    lines.zipWithIndex.foreach { (question, index) =>
      plan(question, "q14c-" + index) match {
        case PlannerResult.Planned(_, attempts, fallbackUsed) =>
          assert(attempts == 1 && fallbackUsed, s"line ${index + 1} not planned via fallback")
        case other => fail(s"line ${index + 1} '$question' was not Planned: $other")
      }
    }
  }

  /** Hand-derived from QueryPlannerAgent.fallback and intent: question, operation, ranking metric,
    * ranking measure, window id.
    */
  private val rankingExpectations = Vector(
    (
      4,
      "Which researchers have the most distinct coauthors?",
      QueryOperation.ResearcherRanking,
      Some(CollaborationMetric.DistinctCoauthorCount),
      None,
      "all-years"
    ),
    (
      8,
      "Which researchers have the most distinct coauthors since 2015?",
      QueryOperation.ResearcherRanking,
      Some(CollaborationMetric.DistinctCoauthorCount),
      None,
      "since-2015"
    ),
    (
      12,
      "Which researchers have the most distinct coauthors in window 2020-2026?",
      QueryOperation.ResearcherRanking,
      Some(CollaborationMetric.DistinctCoauthorCount),
      None,
      "2020-2026"
    ),
    (
      16,
      "Which researchers have the most distinct coauthors in window through-2009?",
      QueryOperation.ResearcherRanking,
      Some(CollaborationMetric.DistinctCoauthorCount),
      None,
      "through-2009"
    ),
    (
      20,
      "Which researchers have the largest team size?",
      QueryOperation.MaximumTeamSize,
      Some(CollaborationMetric.MaximumCoauthorsOnOnePaper),
      None,
      "all-years"
    ),
    (
      24,
      "Which researchers are the strongest bridges?",
      QueryOperation.BridgeRanking,
      Some(CollaborationMetric.BridgeScore),
      Some("CROSS_COMMUNITY_DEGREE"),
      "all-years"
    ),
    (
      28,
      "Which researchers are the strongest bridges since 2015?",
      QueryOperation.BridgeRanking,
      Some(CollaborationMetric.BridgeScore),
      Some("CROSS_COMMUNITY_DEGREE"),
      "since-2015"
    ),
    (
      32,
      "Show the strongest repeated collaborations",
      QueryOperation.ResearcherRanking,
      None,
      Some("JOINT_PUBLICATION_COUNT"),
      "all-years"
    )
  )

  test("the 8 global ranking lines sit at their line numbers with the expected plans") {
    val all = lines
    assert(rankingExpectations.size == 8)
    rankingExpectations.foreach { (number, question, operation, metric, measure, window) =>
      assert(all(number - 1) == question, s"line $number text changed")
      plan(question, "rank14c-" + number) match {
        case PlannerResult.Planned(p, _, true) =>
          assert(p.operations == Vector(operation), s"line $number operations")
          assert(p.rankingMetric == metric, s"line $number metric")
          assert(p.runtime.get.rankingMeasure == measure, s"line $number measure")
          assert(p.runtime.get.windowIds == Vector(window), s"line $number window")
          assert(p.runtime.get.comparisonWindowIds.isEmpty && p.runtime.get.researcherNames.isEmpty)
          assert(p.topicFilters.isEmpty && p.institutionFilters.isEmpty && p.venueFilters.isEmpty)
        case other => fail(s"line $number '$question' was not Planned via fallback: $other")
      }
    }
  }

  test("regression (N4): the old phrasing 'in window since-2015' is not planned") {
    // The unquoted-filter lookahead stops at `since`, leaving the filter text `window`. The planner
    // is deliberately unchanged here; accepting this phrasing is future scope.
    val old = "Which researchers are the strongest bridges in window since-2015?"
    assert(
      plan(old, "n4-old") ==
        PlannerResult.Unsupported("fallback-unrecognized-or-unrepresentable-constraint", 1)
    )
  }
}
