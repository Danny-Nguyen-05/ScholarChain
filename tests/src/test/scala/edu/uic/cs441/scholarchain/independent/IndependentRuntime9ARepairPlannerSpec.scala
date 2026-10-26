package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import org.scalatest.funsuite.AnyFunSuite

/** B1 regressions transcribe question semantics directly; no production intent helper supplies
  * expected metrics, operations, windows or conversion flags.
  */
class IndependentRuntime9ARepairPlannerSpec extends AnyFunSuite {
  import IndependentRuntime9AFixture.*

  private case class Intent(
      question: String,
      metric: Option[String],
      operation: String,
      measure: Option[String] = None,
      conversion: Boolean = false
  )
  private val metricIntents = Vector(
    Intent(
      "Rank researchers by publication count",
      Some("PUBLICATION_COUNT"),
      "RESEARCHER_RANKING"
    ),
    Intent(
      "Rank researchers by distinct coauthors",
      Some("DISTINCT_COAUTHOR_COUNT"),
      "RESEARCHER_RANKING"
    ),
    Intent(
      "Rank researchers by total coauthor occurrences",
      Some("TOTAL_COAUTHOR_OCCURRENCES"),
      "RESEARCHER_RANKING"
    ),
    Intent(
      "Rank researchers by average coauthors per paper",
      Some("AVERAGE_COAUTHORS_PER_PAPER"),
      "RESEARCHER_RANKING"
    ),
    Intent(
      "Rank researchers by maximum coauthors on one paper",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE"
    ),
    Intent(
      "Which researchers have the largest team size?",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE"
    ),
    Intent("Rank researchers by weighted degree", Some("WEIGHTED_DEGREE"), "RESEARCHER_RANKING"),
    Intent("Rank researchers by coreness", Some("CORENESS"), "RESEARCHER_RANKING")
  )
  private val bridgeIntents = Vector(
    Intent(
      "Rank bridge researchers by cross-community degree",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_DEGREE")
    ),
    Intent(
      "Rank bridge researchers by cross-community weight",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_WEIGHT")
    ),
    Intent(
      "Rank bridge researchers by communities connected",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("COMMUNITIES_CONNECTED")
    ),
    Intent(
      "Rank bridge researchers by participation coefficient",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("PARTICIPATION_COEFFICIENT")
    ),
    Intent(
      "Which researchers are the strongest bridges?",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_DEGREE")
    ),
    Intent(
      "Show strongest repeated collaborations",
      None,
      "RESEARCHER_RANKING",
      Some("JOINT_PUBLICATION_COUNT")
    )
  )
  private def json(intent: Intent, window: String = config.defaultWindowId): ujson.Obj = {
    val value = output(window = window, operation = intent.operation)
    value("rankingMetric") = intent.metric.map(ujson.Str(_)).getOrElse(ujson.Null)
    value("rankingMeasure") = intent.measure.map(ujson.Str(_)).getOrElse(ujson.Null)
    value("authorCountConversion") = intent.conversion
    value
  }
  private def assertIntent(
      value: QueryPlan,
      intent: Intent,
      window: String = config.defaultWindowId
  ): Unit = {
    assert(value.rankingMetric.map(_.wire) == intent.metric)
    assert(value.operations.contains(QueryOperation.values.find(_.wire == intent.operation).get))
    assert(value.runtime.get.rankingMeasure == intent.measure)
    assert(value.runtime.get.windowIds == Vector(window))
    assert(value.runtime.get.authorCountConversion == intent.conversion)
  }
  private def execute(question: String, value: ujson.Obj): PlannerResult =
    new QueryPlannerAgent(script(value.render()), config, assets)
      .plan(question, "independent-b1", provenance)

  (metricIntents ++ bridgeIntents).foreach { intent =>
    test(s"B1 correct schema-shaped output preserves ${intent.question}") {
      execute(intent.question, json(intent)) match {
        case PlannerResult.Planned(value, attempts, fallbackUsed) =>
          assert(attempts == 1 && !fallbackUsed)
          assertIntent(value, intent)
        case other => fail(s"Correct explicit question must remain supported: $other")
      }
    }
    test(s"B1 substituted metric or measure cannot change ${intent.question}") {
      val wrong = json(intent)
      if (intent.measure.nonEmpty) {
        wrong("rankingMeasure") =
          if (intent.measure.contains("PARTICIPATION_COEFFICIENT"))
            ujson.Str("CROSS_COMMUNITY_DEGREE")
          else ujson.Str("PARTICIPATION_COEFFICIENT")
      } else {
        wrong("rankingMetric") =
          if (intent.metric.contains("DISTINCT_COAUTHOR_COUNT"))
            ujson.Str("PUBLICATION_COUNT")
          else ujson.Str("DISTINCT_COAUTHOR_COUNT")
        wrong("operations") = ujson.Arr("RESEARCHER_RANKING")
      }
      execute(intent.question, wrong) match {
        case PlannerResult.Planned(value, attempts, fallbackUsed) =>
          assert(attempts == 2 && fallbackUsed)
          assertIntent(value, intent)
        case _: PlannerResult.Unsupported => succeed
        case other => fail(s"Wrong model intent must retry then fall back or abstain: $other")
      }
    }
  }

  test("B1 explicit bridge measure cannot silently become the configured default") {
    val intent = bridgeIntents(3)
    val value = json(intent); value("rankingMeasure") = ujson.Null
    execute(intent.question, value) match {
      case PlannerResult.Planned(plan, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(plan, intent)
      case _: PlannerResult.Unsupported => succeed
      case other => fail(s"Explicit participation measure was not preserved: $other")
    }
  }

  test("B1 since-2015 cannot narrow to the stored 2015-2019 period") {
    val intent = metricIntents(1)
    execute(intent.question + " since 2015", json(intent, "2015-2019")) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(value, intent, "since-2015")
      case _: PlannerResult.Unsupported => succeed
      case other => fail(s"Cumulative since phrase became an early period: $other")
    }
  }

  test("B1 correct cumulative since-2015 output remains supported") {
    val intent = metricIntents(1)
    execute(intent.question + " since 2015", json(intent, "since-2015")) match {
      case PlannerResult.Planned(value, 1, false) => assertIntent(value, intent, "since-2015")
      case other => fail(s"Correct since phrase must remain supported: $other")
    }
  }

  test("B1 a question naming no window uses the configured default") {
    val intent = metricIntents(1)
    execute(intent.question, json(intent, "2020-2026")) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(value, intent)
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Model invented a narrowed window: $other")
    }
  }

  test("B1 exact stored window names remain supported and cannot be replaced") {
    val intent = metricIntents(1)
    val question = intent.question + " window 2020-2026"
    execute(question, json(intent, "2020-2026")) match {
      case PlannerResult.Planned(value, 1, false) => assertIntent(value, intent, "2020-2026")
      case other => fail(s"Correct explicit stored window must remain supported: $other")
    }
    execute(question, json(intent, "since-2015")) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(value, intent, "2020-2026")
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Explicit window was replaced: $other")
    }
  }

  test("B1 total-author conversion is rejected when the question asks only for coauthors") {
    val intent = metricIntents(4)
    val value = json(intent); value("authorCountConversion") = true
    execute(intent.question, value) match {
      case PlannerResult.Planned(plan, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(plan, intent)
      case _: PlannerResult.Unsupported => succeed
      case other => fail(s"Unrequested total-author conversion survived: $other")
    }
  }

  test("B1 explicit total-author request requires its labeled conversion") {
    val intent = Intent(
      "Rank researchers by maximum total authors on one paper",
      Some("MAXIMUM_COAUTHORS_ON_ONE_PAPER"),
      "MAXIMUM_TEAM_SIZE",
      conversion = true
    )
    execute(intent.question, json(intent)) match {
      case PlannerResult.Planned(value, 1, false) => assertIntent(value, intent)
      case other => fail(s"Explicit total-author request must remain supported: $other")
    }
    val missing = json(intent); missing("authorCountConversion") = false
    execute(intent.question, missing) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(value, intent)
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Total-author request lost conversion: $other")
    }
  }

  test("B1 an alternate configured default bridge measure controls unspecified bridge requests") {
    val changed = config.copy(defaultRankingMeasure = "CROSS_COMMUNITY_WEIGHT")
    val intent = Intent(
      "Which researchers are the strongest bridges?",
      Some("BRIDGE_SCORE"),
      "BRIDGE_RANKING",
      Some("CROSS_COMMUNITY_WEIGHT")
    )
    def run(value: ujson.Obj): PlannerResult =
      new QueryPlannerAgent(script(value.render()), changed, assets)
        .plan(intent.question, "independent-b1-config-measure", provenance)
    run(json(intent)) match {
      case PlannerResult.Planned(value, 1, false) => assertIntent(value, intent)
      case other => fail(s"Correct configured bridge default must remain supported: $other")
    }
    Vector("CROSS_COMMUNITY_DEGREE", "PARTICIPATION_COEFFICIENT").foreach { wrongMeasure =>
      val wrong = json(intent); wrong("rankingMeasure") = wrongMeasure
      run(wrong) match {
        case PlannerResult.Planned(value, attempts, fallbackUsed) =>
          assert(attempts == 2 && fallbackUsed)
          assertIntent(value, intent)
        case _: PlannerResult.Unsupported => succeed
        case other => fail(s"Model overrode configured default bridge measure: $other")
      }
    }
  }

  test("B1 an alternate configured default window controls questions naming no window") {
    val changed = config.copy(defaultWindowId = "2020-2026")
    val intent = metricIntents(1)
    def run(value: ujson.Obj): PlannerResult =
      new QueryPlannerAgent(script(value.render()), changed, assets)
        .plan(intent.question, "independent-b1-config-window", provenance)
    run(json(intent, "2020-2026")) match {
      case PlannerResult.Planned(value, 1, false) => assertIntent(value, intent, "2020-2026")
      case other => fail(s"Correct configured default window must remain supported: $other")
    }
    run(json(intent, "all-years")) match {
      case PlannerResult.Planned(value, attempts, fallbackUsed) =>
        assert(attempts == 2 && fallbackUsed)
        assertIntent(value, intent, "2020-2026")
      case _: PlannerResult.Unsupported => succeed
      case other                        => fail(s"Model overrode configured default window: $other")
    }
  }
}
