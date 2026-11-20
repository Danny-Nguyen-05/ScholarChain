package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.util.Locale
import scala.util.control.NonFatal

enum PlannerResult {
  case Planned(plan: QueryPlan, attempts: Int, fallbackUsed: Boolean)
  case Unsupported(reason: String, attempts: Int)
  case Failed(reason: String)
}

/** An LLM proposes only allowlisted operations and extracted data. Validation and the fallback are
  * deterministic. The fallback recognizes a small anchored grammar, never approximate NLP.
  */
final class QueryPlannerAgent(
    llm: LlmClient,
    config: RuntimeConfig,
    assets: RuntimePromptAssets,
    clockNanos: () => Long = () => System.nanoTime()
) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  private val unsafe =
    "(?i)\\b(cypher|sql|terraform|aws|execute|delete|drop|ignore previous|ignore all)\\b".r
  private val unavailableMetric = "(?i)\\b(citations?|h[- ]index|impact factor|betweenness)\\b".r
  private val quotedFilter = "(?i)\\b(topic|institution|venue)\\s+\"([^\"]+)\"".r
  private val yearPattern = "\\b(?:18|19|20|21)[0-9]{2}\\b".r
  private def norm(value: String): String =
    value.trim.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ")
  private def strings(value: ujson.Value, key: String): Vector[String] =
    value(key).arr.map(_.str).toVector
  private def nullable(value: ujson.Value, key: String): Option[String] =
    if (value(key) == ujson.Null) None else Some(value(key).str)

  private case class Intent(
      metric: Option[CollaborationMetric],
      measure: Option[String],
      operations: Set[QueryOperation],
      windows: Vector[String],
      comparisons: Vector[String],
      authorCountConversion: Boolean
  )

  /** Request semantics are independent of model fields. In particular a year being present in some
    * stored window is insufficient: the complete requested period must match exactly.
    */
  private def intent(question: String): Either[String, Intent] = {
    val source = norm(question).replaceAll("\"[^\"]*\"", "\"\"")
    var requested = Vector.empty[String]
    var selectedPositions = Vector.empty[(Int, String)]
    var consumed = Vector.empty[(Int, Int)]
    var windowError = false
    def select(matches: Vector[RuntimeWindow], start: Int, end: Int): Unit = {
      if (matches.size != 1) windowError = true
      else selectedPositions :+= (start -> matches.head.windowId)
      consumed :+= (start -> end)
    }
    "\\b(?:in window|window)\\s+([a-z0-9-]+)".r.findAllMatchIn(source).foreach { m =>
      select(config.windows.filter(_.windowId == m.group(1)), m.start, m.end)
    }
    val latestEnd = config.windows.flatMap(_.endYear).maxOption
    "\\bsince\\s+([0-9]{4})\\b".r.findAllMatchIn(source).foreach { m =>
      select(
        config.windows
          .filter(w => w.startYear.contains(m.group(1).toInt) && w.endYear == latestEnd),
        m.start,
        m.end
      )
    }
    "\\bthrough\\s+([0-9]{4})\\b".r.findAllMatchIn(source).foreach { m =>
      select(
        config.windows.filter(w => w.startYear.isEmpty && w.endYear.contains(m.group(1).toInt)),
        m.start,
        m.end
      )
    }
    "\\b(?:from|between|in)\\s+([0-9]{4})\\s*(?:to|and|-)\\s*([0-9]{4})\\b".r
      .findAllMatchIn(source)
      .foreach { m =>
        select(
          config.windows.filter(w =>
            w.startYear.contains(m.group(1).toInt) && w.endYear.contains(m.group(2).toInt)
          ),
          m.start,
          m.end
        )
      }
    config.windows.foreach { window =>
      ("(?<![a-z0-9-])" + java.util.regex.Pattern.quote(window.windowId) + "(?![a-z0-9-])").r
        .findAllMatchIn(source)
        .foreach(m => select(Vector(window), m.start, m.end))
    }
    "\\ball years\\b".r
      .findAllMatchIn(source)
      .foreach(m =>
        select(config.windows.filter(w => w.startYear.isEmpty && w.endYear.isEmpty), m.start, m.end)
      )
    val residual = source.indices
      .map(i => if (consumed.exists((a, b) => i >= a && i < b)) ' ' else source(i))
      .mkString
    if (windowError || yearPattern.findFirstIn(residual).nonEmpty)
      return Left("unrepresentable-window-intent")
    requested = selectedPositions.sortBy(_._1).map(_._2).distinct
    val temporal =
      source.contains("temporal") || (source.contains("change") && requested.size == 2) ||
        (requested.size == 2 && (source.contains("compare") || source.contains("comparison")))
    if ((temporal && requested.size != 2) || (!temporal && requested.size > 1))
      return Left("unrepresentable-window-comparison")
    val windows = if (requested.isEmpty) Vector(config.defaultWindowId) else requested
    val conversion = "\\b(?:total authors|total number of authors|total author count)\\b".r
      .findFirstIn(source)
      .nonEmpty
    val metricPhrases = Vector(
      "\\b(?:distinct coauthors|distinct coauthor count)\\b" -> CollaborationMetric.DistinctCoauthorCount,
      "\\b(?:publication count|most publications)\\b" -> CollaborationMetric.PublicationCount,
      "\\btotal coauthor occurrences\\b" -> CollaborationMetric.TotalCoauthorOccurrences,
      "\\b(?:average coauthors|average team size)\\b" -> CollaborationMetric.AverageCoauthorsPerPaper,
      "\\b(?:(?:maximum|largest) (?:author )?team size|maximum coauthors|maximum total authors)\\b" -> CollaborationMetric.MaximumCoauthorsOnOnePaper,
      "\\bweighted degree\\b" -> CollaborationMetric.WeightedDegree,
      "\\bcoreness\\b" -> CollaborationMetric.Coreness
    )
    val measures = Vector(
      "\\bcross[- ]community degree\\b" -> "CROSS_COMMUNITY_DEGREE",
      "\\bcross[- ]community weight\\b" -> "CROSS_COMMUNITY_WEIGHT",
      "\\bcommunities connected\\b" -> "COMMUNITIES_CONNECTED",
      "\\bparticipation coefficient\\b" -> "PARTICIPATION_COEFFICIENT"
    ).collect { case (phrase, value) if phrase.r.findFirstIn(source).nonEmpty => value }.distinct
    val repeated = "\\brepeated collaborations?\\b".r.findFirstIn(source).nonEmpty
    val bridge = "\\bbridges?\\b".r.findFirstIn(source).nonEmpty || measures.nonEmpty
    val metrics = metricPhrases.collect {
      case (phrase, value) if phrase.r.findFirstIn(source).nonEmpty => value
    }.distinct
    if (
      metrics.size > 1 || measures.size > 1 || (bridge && (metrics.nonEmpty || repeated)) || (repeated && metrics.nonEmpty)
    )
      return Left("unrepresentable-multiple-ranking-intents")
    val metric = if (bridge) Some(CollaborationMetric.BridgeScore) else metrics.headOption
    val measure =
      if (bridge) Some(measures.headOption.getOrElse(config.defaultRankingMeasure))
      else if (repeated) Some("JOINT_PUBLICATION_COUNT")
      else None
    if (
      conversion && !metric.exists(m =>
        m == CollaborationMetric.MaximumCoauthorsOnOnePaper || m == CollaborationMetric.AverageCoauthorsPerPaper
      )
    )
      return Left("unrepresentable-author-conversion")
    var operations = Set.empty[QueryOperation]
    if (temporal) operations += QueryOperation.TemporalComparison
    else if (bridge) operations += QueryOperation.BridgeRanking
    else if (metric.contains(CollaborationMetric.MaximumCoauthorsOnOnePaper))
      operations += QueryOperation.MaximumTeamSize
    else if (metric.nonEmpty || repeated) operations += QueryOperation.ResearcherRanking
    if (source.contains("shortest")) operations += QueryOperation.ShortestPath
    if (source.contains("direct coauthors")) operations += QueryOperation.DirectCoauthors
    if (source.contains("component")) operations += QueryOperation.ComponentLookup
    if (
      source.contains("community comparison") || source.contains("compare communities") || source
        .contains("communities compare") || source.contains("compare community")
    )
      operations += QueryOperation.CommunityComparison
    if (source.contains("explain")) operations += QueryOperation.SemanticExplanation
    if (operations.isEmpty) Left("unrecognized-operation-intent")
    else
      Right(
        Intent(
          metric,
          measure,
          operations,
          windows,
          if (temporal) windows else Vector.empty,
          conversion
        )
      )
  }

  def plan(
      question: String,
      queryId: String,
      provenance: Provenance,
      usageSink: RuntimeModelUsage => Unit = _ => ()
  ): PlannerResult = {
    val result = planInternal(question, queryId, provenance, usageSink)
    val (outcome, planId) = result match {
      case PlannerResult.Planned(p, _, _)  => ("planned", Some(p.planId))
      case PlannerResult.Unsupported(_, _) => ("unsupported", None)
      case PlannerResult.Failed(_)         => ("failed", None)
    }
    RuntimeStageLog.outcome("planner", queryId, provenance.runId, outcome, planId)
    result
  }
  private def planInternal(
      question: String,
      queryId: String,
      provenance: Provenance,
      usageSink: RuntimeModelUsage => Unit
  ): PlannerResult = {
    val started = clockNanos()
    if (
      question.trim.isEmpty || queryId.trim.isEmpty || question
        .getBytes(UTF_8)
        .length > config.effectiveByteLimits.questionBytes
    )
      return PlannerResult.Failed("planner-input-bound")
    if (unsafe.findFirstIn(question).nonEmpty)
      return PlannerResult.Unsupported("unsafe-operation-request", 0)
    if (unavailableMetric.findFirstIn(question).nonEmpty)
      return PlannerResult.Unsupported("metric-not-stored", 0)
    if (
      "(?i)\\b(only (papers|publications|collaborations)|recalculate|recompute)\\b".r
        .findFirstIn(question)
        .nonEmpty
    )
      return PlannerResult.Unsupported("filtered-metric-not-stored", 0)
    val request = StructuredLlmRequest(
      "submit_query_plan",
      assets.plannerPrompt,
      ujson
        .Obj(
          "question" -> question,
          "storedWindows" -> ujson.Arr.from(
            config.windows.map(w =>
              ujson.Obj(
                "windowId" -> w.windowId,
                "startYear" -> w.startYear.map(ujson.Num(_)).getOrElse(ujson.Null),
                "endYear" -> w.endYear.map(ujson.Num(_)).getOrElse(ujson.Null)
              )
            )
          ),
          "defaultWindowId" -> config.defaultWindowId,
          "defaultRankingMeasure" -> config.defaultRankingMeasure
        )
        .render(),
      assets.plannerSchema.render(),
      config.plannerPromptVersion,
      config.plannerSchemaVersion,
      config.deadlines.plannerMs
    )
    var attempt = 0
    while (attempt <= config.malformedRetries) {
      val remaining = config.deadlines.plannerMs - (clockNanos() - started) / 1000000
      if (remaining <= 0) return PlannerResult.Failed("planner-deadline")
      attempt += 1
      val result =
        try llm.complete(request.copy(timeoutMillis = remaining))
        catch { case NonFatal(_) => LlmResult.Failure("llm-client-failure") }
      if ((clockNanos() - started) / 1000000 >= config.deadlines.plannerMs)
        return PlannerResult.Failed("planner-deadline")
      result match {
        case LlmResult.Output(json, tokens, model, version) =>
          usageSink(
            RuntimeModelUsage(
              model,
              version,
              config.plannerPromptVersion,
              config.plannerSchemaVersion,
              tokens.inputTokens,
              tokens.outputTokens,
              Some(config.model.region)
            )
          )
          decode(json, question, queryId, provenance, attempt, false) match {
            case Right(result) => return result
            case Left(_)       => ()
          }
        case LlmResult.Failure(code)
            if code == "llm-invalid-tool-output" || code == "llm-output-bound" =>
          ()
        case LlmResult.Failure(_) => return fallback(question, queryId, provenance, attempt)
      }
    }
    fallback(question, queryId, provenance, attempt)
  }

  private def decode(
      json: String,
      question: String,
      queryId: String,
      provenance: Provenance,
      attempts: Int,
      fallbackUsed: Boolean
  ): Either[String, PlannerResult] = try {
    if (json.getBytes(UTF_8).length > config.effectiveByteLimits.questionBytes)
      return Left("planner-output-bound")
    val value = ujson.read(json)
    if (RuntimeJsonSchema.validate(assets.plannerSchema, value).isLeft)
      return Left("planner-schema")
    if (value("status").str == "UNSUPPORTED")
      return Right(
        PlannerResult.Unsupported(
          nullable(value, "unsupportedReason").getOrElse("unsupported-query"),
          attempts
        )
      )
    if (nullable(value, "unsupportedReason").nonEmpty) return Left("contradictory-plan-status")
    val operations =
      strings(value, "operations").map(w => QueryOperation.values.find(_.wire == w).get)
    val windows = strings(value, "windowIds")
    val comparison = strings(value, "comparisonWindowIds")
    val names = strings(value, "researcherNames")
    val topics = strings(value, "topicFilters")
    val institutions = strings(value, "institutionFilters")
    val venues = strings(value, "venueFilters")
    val expected = intent(question) match {
      case Left(reason) => return Left(reason)
      case Right(v)     => v
    }
    if (
      operations.isEmpty || windows.isEmpty || (windows ++ comparison)
        .exists(w => !config.windowIds.contains(w))
    )
      return Left("unsupported-operation-or-window")
    if ((names ++ topics ++ institutions ++ venues).exists(t => !norm(question).contains(norm(t))))
      return Left("invented-extracted-value")
    def filterAnchored(values: Vector[String], markers: String): Boolean = values.forall { v =>
      ("\\b(?:" + markers + ")\\s+\"?" + java.util.regex.Pattern.quote(
        norm(v)
      ) + "(?=$|[\\s\\p{Punct}])").r.findFirstIn(norm(question)).nonEmpty
    }
    if (
      !filterAnchored(topics, "topic|in") || !filterAnchored(
        institutions,
        "institution|at"
      ) || !filterAnchored(venues, "venue")
    )
      return Left("filter-not-grounded-in-request")
    val namedOperations = Set(
      QueryOperation.DirectCoauthors,
      QueryOperation.ShortestPath,
      QueryOperation.ComponentLookup,
      QueryOperation.CommunityComparison,
      QueryOperation.SemanticExplanation,
      QueryOperation.TemporalComparison
    )
    if (names.nonEmpty && !operations.exists(namedOperations.contains))
      return Left("named-ranking-population-not-supported")
    val namedRequest = Vector(
      "shortest",
      "direct coauthors",
      "component",
      "membership",
      "community",
      "communities",
      "change",
      "changed",
      "did",
      "from",
      "temporal",
      "explain"
    )
      .exists(norm(question).contains)
    if (names.nonEmpty && !namedRequest) return Left("name-not-grounded-in-named-operation")
    if (!coveredQuestion(question, names, topics, institutions, venues, windows ++ comparison))
      return Left("unrepresented-question-constraint")
    val requiredFilters = quotedFilter.findAllMatchIn(question).toVector
    if (
      requiredFilters.exists(m =>
        !(m.group(1).toLowerCase(Locale.ROOT) match {
          case "topic" => topics; case "institution" => institutions; case _ => venues
        }).exists(t => norm(t) == norm(m.group(2)))
      )
    ) return Left("dropped-filter")
    if (windows != expected.windows || comparison != expected.comparisons)
      return Left("requested-window-intent-changed")
    if (operations.contains(QueryOperation.ShortestPath) && names.size != 2)
      return Left("path-needs-two-names")
    if (
      operations.exists(o =>
        Set(
          QueryOperation.DirectCoauthors,
          QueryOperation.ComponentLookup,
          QueryOperation.CommunityComparison
        ).contains(o)
      ) && names.isEmpty
    )
      return Left("operation-needs-name")
    if (operations.contains(QueryOperation.TemporalComparison) && comparison.size != 2)
      return Left("temporal-needs-two-windows")
    val metric =
      nullable(value, "rankingMetric").map(w => CollaborationMetric.values.find(_.wire == w).get)
    val measure = nullable(value, "rankingMeasure")
    val filterOperations = Set.empty[QueryOperation] ++
      Option.when(topics.nonEmpty)(QueryOperation.TopicFilter) ++
      Option.when(institutions.nonEmpty)(QueryOperation.InstitutionFilter)
    if (
      metric != expected.metric || measure != expected.measure ||
      !expected.operations.subsetOf(operations.toSet) ||
      !operations.toSet.subsetOf(expected.operations ++ filterOperations)
    )
      return Left("requested-metric-measure-or-operation-changed")
    if (value("authorCountConversion").bool != expected.authorCountConversion)
      return Left("requested-author-conversion-changed")
    val window = config.windows.find(_.windowId == windows.head).get.legacyWindow
    val runtime = RuntimeQueryOptions(
      names,
      windows,
      comparison,
      config.retrievalMode,
      config.evidenceOnly,
      measure,
      None,
      value("authorCountConversion").bool
    )
    val plan = QueryPlan(
      "plan:" + StableIds.sha256Hex(queryId + ":" + question + ":" + value.render()),
      provenance.schemaVersion,
      question,
      operations,
      window,
      topics,
      institutions,
      venues,
      metric,
      config.retrieval.graphLimit,
      config.retrieval.vectorLimit,
      config.retrieval.maxPathDepth,
      provenance,
      Some(runtime)
    )
    if (DomainValidation.check(plan).isLeft) Left("invalid-core-plan")
    else Right(PlannerResult.Planned(plan, attempts, fallbackUsed))
  } catch { case NonFatal(_) => Left("malformed-plan-output") }

  /** Conservative coverage guard: data values must be copied from the question and all residual
    * words must belong to the supported request grammar. Unknown clauses never disappear into a
    * schema-valid model plan. This intentionally rejects novel phrasing until explicitly added.
    */
  private def coveredQuestion(
      question: String,
      names: Vector[String],
      topics: Vector[String],
      institutions: Vector[String],
      venues: Vector[String],
      windows: Vector[String]
  ): Boolean = {
    var residual = norm(question)
    def remove(value: String): Unit = residual = residual.replaceAll(
      "(?<![a-z0-9])" + java.util.regex.Pattern.quote(norm(value)) + "(?![a-z0-9])",
      " "
    )
    (names ++ topics ++ institutions ++ venues).sortBy(-_.length).foreach(remove)
    windows.foreach { id =>
      remove(id)
      config.windows
        .find(_.windowId == id)
        .foreach(w => (w.startYear.toVector ++ w.endYear.toVector).foreach(y => remove(y.toString)))
    }
    val vocabulary = Set(
      "how",
      "which",
      "who",
      "what",
      "are",
      "is",
      "the",
      "a",
      "an",
      "researcher",
      "researchers",
      "have",
      "has",
      "with",
      "most",
      "rank",
      "by",
      "distinct",
      "coauthor",
      "coauthors",
      "maximum",
      "largest",
      "author",
      "authors",
      "team",
      "size",
      "direct",
      "of",
      "shortest",
      "path",
      "between",
      "and",
      "component",
      "lookup",
      "membership",
      "community",
      "communities",
      "compare",
      "comparison",
      "bridge",
      "bridges",
      "strongest",
      "change",
      "changed",
      "did",
      "from",
      "temporal",
      "change",
      "changes",
      "from",
      "to",
      "since",
      "through",
      "window",
      "topic",
      "institution",
      "venue",
      "at",
      "in",
      "explain",
      "research",
      "collaboration",
      "collaborations",
      "repeated",
      "publication",
      "publications",
      "count",
      "average",
      "per",
      "paper",
      "weighted",
      "degree",
      "coreness",
      "connected",
      "coefficient",
      "participation",
      "cross",
      "during",
      "for",
      "show",
      "their",
      "them",
      "how",
      "many",
      "total",
      "occurrences",
      "on",
      "one",
      "weight",
      "number",
      "all",
      "years"
    )
    val tokens = "[\\p{L}\\p{N}]+".r.findAllIn(residual).toVector
    if (tokens.exists(t => !vocabulary(t))) return false
    // Common unquoted filters have fixed meaning, independent of the model's chosen field.
    val lower = norm(question).stripSuffix("?")
    val unquoted =
      "(?i)\\b(topic|institution|venue|at|in)\\s+([^\"]+?)(?=\\s+(?:since|during|window|at|topic|institution|venue)\\b|$)".r
    unquoted.findAllMatchIn(lower).forall { m =>
      val text = m.group(2).trim
      val windowPhrase = config.windowIds.contains(text.stripPrefix("window ")) || text
        .matches("[0-9]{4}(?:-[0-9]{4})?")
      if (windowPhrase) true
      else {
        val actual = m.group(1).toLowerCase(Locale.ROOT) match {
          case "institution" | "at" => institutions
          case "venue"              => venues
          case _                    => topics
        }
        actual.exists(v => norm(v) == text)
      }
    }
  }

  private def fallback(
      question: String,
      queryId: String,
      provenance: Provenance,
      attempts: Int
  ): PlannerResult = {
    var remaining = question.trim.stripSuffix("?").trim
    val filters = quotedFilter.findAllMatchIn(remaining).toVector
    remaining = quotedFilter.replaceAllIn(remaining, "").trim.replaceAll("\\s+", " ")
    var selectedWindow = config.defaultWindowId
    val since = "(?i)\\s+since ([0-9]{4})$".r
    since.findFirstMatchIn(remaining).foreach { m =>
      val candidates = config.windows.filter(_.startYear.contains(m.group(1).toInt))
      val cumulative = candidates.filter(_.endYear == config.windows.flatMap(_.endYear).maxOption)
      if (cumulative.size == 1) {
        selectedWindow = cumulative.head.windowId; remaining = remaining.substring(0, m.start).trim
      }
    }
    val windowSuffix = "(?i)\\s+(?:in window|window) ([a-z0-9-]+)$".r
    windowSuffix.findFirstMatchIn(remaining).foreach { m =>
      selectedWindow = m.group(1); remaining = remaining.substring(0, m.start).trim
    }
    val path =
      "(?i)(?:what is the )?shortest (?:coauthor )?path between \"([^\"]+)\" and \"([^\"]+)\"".r
    val coauthors = "(?i)(?:who are the )?direct coauthors of \"([^\"]+)\"".r
    val component = "(?i)(?:what is the )?component (?:of|for) \"([^\"]+)\"".r
    // The quoted `topic "..."` clause is removed from `remaining` above, so the explanation form is
    // what is left of "explain the (research) topic "X"": the verb phrase plus exactly one quoted
    // filter, which is a topic. Extra topics, venues or institutions are not representable here.
    val semantic = "(?i)explain the(?: research)?".r
    val topicFilters = filters.filter(_.group(1).equalsIgnoreCase("topic"))
    val repeated = "(?i)(?:show|rank) (?:the )?strongest repeated collaboration(?:s)?".r
    val parsed: Option[
      (Vector[QueryOperation], Vector[String], Option[CollaborationMetric], Option[String])
    ] = remaining match {
      case path(a, b)   => Some((Vector(QueryOperation.ShortestPath), Vector(a, b), None, None))
      case coauthors(a) => Some((Vector(QueryOperation.DirectCoauthors), Vector(a), None, None))
      case component(a) => Some((Vector(QueryOperation.ComponentLookup), Vector(a), None, None))
      case semantic() if filters.size == 1 && topicFilters.size == 1 =>
        Some((Vector(QueryOperation.SemanticExplanation), Vector.empty, None, None))
      case repeated() =>
        Some(
          (
            Vector(QueryOperation.ResearcherRanking),
            Vector.empty,
            None,
            Some("JOINT_PUBLICATION_COUNT")
          )
        )
      case s
          if norm(s).matches(
            "(?:which researchers have the most|rank researchers by|researchers with the most) distinct coauthors"
          ) =>
        Some(
          (
            Vector(QueryOperation.ResearcherRanking),
            Vector.empty,
            Some(CollaborationMetric.DistinctCoauthorCount),
            None
          )
        )
      case s
          if norm(s).matches(
            "(?:which researchers have the|rank researchers by) (?:largest|maximum) (?:author )?team size"
          ) =>
        Some(
          (
            Vector(QueryOperation.MaximumTeamSize),
            Vector.empty,
            Some(CollaborationMetric.MaximumCoauthorsOnOnePaper),
            None
          )
        )
      case s
          if norm(s).matches(
            "(?:which researchers are the strongest bridges|rank bridge researchers)"
          ) =>
        Some(
          (
            Vector(QueryOperation.BridgeRanking),
            Vector.empty,
            Some(CollaborationMetric.BridgeScore),
            Some(config.defaultRankingMeasure)
          )
        )
      case _ => None
    }
    parsed match {
      case None =>
        PlannerResult.Unsupported("fallback-unrecognized-or-unrepresentable-constraint", attempts)
      case Some((ops, names, metric, measure)) =>
        def filter(kind: String) = filters.filter(_.group(1).equalsIgnoreCase(kind)).map(_.group(2))
        val topics = filter("topic")
        val value = ujson.Obj(
          "schemaVersion" -> config.plannerSchemaVersion,
          "status" -> "SUPPORTED",
          "operations" -> ujson.Arr.from(ops.map(_.wire)),
          "researcherNames" -> ujson.Arr.from(names),
          "windowIds" -> ujson.Arr(selectedWindow),
          "comparisonWindowIds" -> ujson.Arr(),
          "topicFilters" -> ujson.Arr.from(topics.distinct),
          "institutionFilters" -> ujson.Arr.from(filter("institution")),
          "venueFilters" -> ujson.Arr.from(filter("venue")),
          "rankingMetric" -> metric.map(m => ujson.Str(m.wire)).getOrElse(ujson.Null),
          "rankingMeasure" -> measure.map(ujson.Str(_)).getOrElse(ujson.Null),
          "authorCountConversion" -> false,
          "unsupportedReason" -> ujson.Null
        )
        decode(value.render(), question, queryId, provenance, attempts, true).getOrElse(
          PlannerResult.Unsupported("fallback-unrecognized-or-unrepresentable-constraint", attempts)
        )
    }
  }
}
