package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryIndexedEvidenceBundleStore,
  InMemoryRuntimeAuditStore
}
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

/** A versioned, hand-derived benchmark uses scripted proposals and no provider construction. */
object RuntimeBenchmark {
  val resource = "/runtime-benchmark-v1.json"
  def load(): ujson.Value = {
    val in = getClass.getResourceAsStream(resource)
    require(in != null, "missing-runtime-benchmark")
    try ujson.read(new String(in.readAllBytes(), UTF_8))
    finally in.close()
  }
  def questionCases: Vector[ujson.Value] = load()("cases").arr.toVector
  private def expectedClaimsHold(c: ujson.Value, result: ujson.Value): Boolean = {
    val accepted = result.obj.get("answer").toVector.flatMap(_("claims").arr)
    val specs = c.obj.get("expectedClaims").map(_.arr.toVector).getOrElse(Vector(c))
    specs.forall { spec =>
      val expected = spec("expectedValues").obj
      val expectedIds = spec.obj.get("expectedIdNames").toVector.flatMap(_.obj.toVector)
      if (expected.isEmpty && expectedIds.isEmpty) true
      else
        accepted.exists { claim =>
          val t = claim("runtime")
          spec.obj
            .get("subjectName")
            .filter(_ != ujson.Null)
            .forall(n => t("subjectIds").arr.exists(_.str == RuntimeOfflineFixture.id(n.str))) &&
          expected.forall { (field, value) =>
            t("values").arr.exists(v =>
              v("field").str == field &&
                (v.obj.get("number").exists(x => x != ujson.Null && x.str == value.str) || v.obj
                  .get("text")
                  .exists(x => x != ujson.Null && x.str == value.str))
            )
          } &&
          expectedIds.forall { (field, names) =>
            val raw = names.arr.toVector.map(n => RuntimeOfflineFixture.id(n.str))
            val ids =
              if (spec.obj.get("sortExpectedIdFields").exists(_.arr.exists(_.str == field)))
                raw.sorted
              else raw
            t("values").arr.exists(v =>
              v("field").str == field && v.obj
                .get("ids")
                .exists(x => x != ujson.Null && x.arr.toVector.map(_.str) == ids)
            )
          }
        }
    }
  }
  def runAll(): Vector[ujson.Value] = questionCases.map { c =>
    val result = RuntimeWorkflowMain
      .execute(Vector("--question", c("question").str))
      .fold(reason => ujson.Obj("error" -> reason), ujson.read(_))
    val outcome = result.obj.get("audit").map(_("outcome").str).getOrElse("FAILED")
    ujson.Obj(
      "id" -> c("id"),
      "expectedOutcome" -> c("expectedOutcome"),
      "outcome" -> outcome,
      "passed" -> (outcome == c("expectedOutcome").str && expectedClaimsHold(c, result)),
      "result" -> result
    )
  }
}

/** Offline fake-store CLI. No credential, SDK client, remote endpoint or live mode is accepted. */
object RuntimeWorkflowMain {
  def main(args: Array[String]): Unit = execute(args.toVector) match {
    case Right(json)  => println(json)
    case Left(reason) => System.err.println(reason)
  }
  def execute(args: Vector[String]): Either[String, String] = try {
    if (args == Vector("--benchmark"))
      return Right(ujson.Arr.from(RuntimeBenchmark.runAll()).render())
    val evidenceOnly = args.contains("--evidence-only")
    val clean = args.filterNot(_ == "--evidence-only")
    if (clean.size != 2 || clean.head != "--question" || clean(1).trim.isEmpty)
      return Left("usage: --question <question> [--evidence-only] or --benchmark; offline only")
    val question = clean(1)
    val cfg = RuntimeOfflineFixture.config.copy(evidenceOnly = evidenceOnly)
    val entry = RuntimeBenchmark.questionCases.find(_("question").str == question)
    val assetsRoot = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .getOrElse(return Left("runtime-assets-unavailable"))
    val assets = RuntimePromptAssets
      .fromDirectory(assetsRoot, cfg)
      .fold(reason => return Left(reason), identity)
    val model = new OfflineProposalClient(entry, cfg)
    val artifacts = RuntimeOfflineFixture.artifacts()
    val metrics = RuntimeOfflineFixture.metricStore()
    val graph = RuntimeOfflineFixture.graph()
    val retrieval = new WorkflowRunner(
      new QueryPlannerAgent(model, cfg, assets),
      new ResearcherResolverAgent(RuntimeOfflineFixture.cache(), cfg),
      new CollaborationMetricsAgent(metrics, artifacts, cfg),
      new PathFinderAgent(graph, metrics, artifacts, cfg),
      new CommunityAnalystAgent(graph, metrics, artifacts, cfg),
      new SemanticContextAgent(
        new InMemoryVectorStore,
        new InMemoryObjectStore,
        new DeterministicHashedEmbeddingClient(EmbeddingModel("offline-synthetic-query", "v1", 8)),
        "offline-synthetic-index",
        cfg
      ),
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, cfg),
      cfg
    )
    val audit = new InMemoryRuntimeAuditStore
    val workflow = new RuntimeAnswerWorkflow(
      retrieval,
      new AnswerSynthesisAgent(model, cfg, assets),
      new ClaimVerificationAgent(cfg),
      audit,
      cfg
    )
    val queryId = "query:offline:" + StableIds.sha256Hex(question + evidenceOnly)
    val result = workflow.run(question, queryId, RuntimeOfflineFixture.provenance)
    val json = result match {
      case AnswerWorkflowResult.Completed(answer, a) =>
        ujson.Obj(
          "answer" -> upickle.default.writeJs(answer),
          "audit" -> upickle.default.writeJs(a)
        )
      case AnswerWorkflowResult.EvidenceOnly(bundle, a) =>
        ujson.Obj(
          "evidence" -> upickle.default.writeJs(bundle),
          "audit" -> upickle.default.writeJs(a)
        )
      case AnswerWorkflowResult.Abstained(reason, a, candidates) =>
        ujson.Obj(
          "reason" -> reason,
          "candidates" -> upickle.default.writeJs(candidates),
          "audit" -> upickle.default.writeJs(a)
        )
      case AnswerWorkflowResult.Unsupported(reason, a) =>
        ujson.Obj("reason" -> reason, "audit" -> upickle.default.writeJs(a))
      case AnswerWorkflowResult.Failed(f) => ujson.Obj("error" -> f.reason, "stage" -> f.stage)
    }
    Right(json.render())
  } catch { case NonFatal(_) => Left("offline-runtime-failed") }

  private class OfflineProposalClient(entry: Option[ujson.Value], config: RuntimeConfig)
      extends LlmClient {
    private def output(value: ujson.Value): LlmResult =
      LlmResult.Output(
        value.render(),
        LlmUsage(None, None),
        config.model.modelId,
        config.model.modelVersion
      )
    def complete(request: StructuredLlmRequest): LlmResult = entry match {
      case None => LlmResult.Failure("offline-script-unavailable")
      case Some(c) if request.toolName == "submit_query_plan" =>
        val op = c("operation").str
        if (op.isEmpty) return LlmResult.Failure("offline-unsupported")
        val comparisons = c("comparisonWindowIds").arr.toVector.map(_.str)
        val question = c("question").str
        def filter(name: String): Vector[String] = {
          val pattern = java.util.regex.Pattern.compile(
            "(?i)" + java.util.regex.Pattern.quote(name) + "[ ]+" + "\"" + "([^\"]+)" + "\""
          )
          val matcher = pattern.matcher(question)
          val values = Vector.newBuilder[String]
          while (matcher.find()) values += matcher.group(1)
          values.result()
        }
        val topics = filter("topic"); val institutions = filter("institution");
        val venues = filter("venue")
        output(
          ujson.Obj(
            "schemaVersion" -> config.plannerSchemaVersion,
            "status" -> "SUPPORTED",
            "operations" -> ujson.Arr.from(
              Vector(op) ++ Option.when(topics.nonEmpty)("TOPIC_FILTER") ++ Option.when(
                institutions.nonEmpty
              )("INSTITUTION_FILTER")
            ),
            "researcherNames" -> c("names"),
            "windowIds" -> ujson.Arr.from(
              if (comparisons.nonEmpty) comparisons else Vector("all-years")
            ),
            "comparisonWindowIds" -> c("comparisonWindowIds"),
            "topicFilters" -> ujson.Arr.from(topics),
            "institutionFilters" -> ujson.Arr.from(institutions),
            "venueFilters" -> ujson.Arr.from(venues),
            "rankingMetric" -> c("metric"),
            "rankingMeasure" -> (if (op == "BRIDGE_RANKING") ujson.Str(config.defaultRankingMeasure)
                                 else ujson.Null),
            "authorCountConversion" -> false,
            "unsupportedReason" -> ujson.Null
          )
        )
      case Some(c) =>
        val body = ujson.read(request.userData)
        val context = ujson.read(
          body("evidenceData").str
            .stripPrefix("<untrusted_evidence_json>\n")
            .stripSuffix("\n</untrusted_evidence_json>")
        )
        val specs = c.obj.get("expectedClaims").map(_.arr.toVector).getOrElse(Vector(c))
        val claims = specs
          .flatMap { spec =>
            val subjectName = spec.obj.get("subjectName").filter(_ != ujson.Null).map(_.str)
            val available = context("items").arr.toVector.filter { item =>
              item("values").obj.get("kind").exists(_.str == c("evidenceKind").str) &&
              subjectName.forall(name =>
                item.obj
                  .get("subjects")
                  .exists(_.arr.exists(_.str == RuntimeOfflineFixture.id(name)))
              )
            }
            val selected =
              if (c("evidenceKind").str == "ranking" && subjectName.isEmpty) available
              else available.take(1)
            selected.map { item =>
              val claimType = Map(
                "metrics" -> "METRIC",
                "ranking" -> "RANKING",
                "path" -> "PATH",
                "direct-coauthors" -> "PATH",
                "community" -> "COMMUNITY",
                "bridge" -> "BRIDGE",
                "temporal" -> "TEMPORAL"
              )(c("evidenceKind").str)
              val fallbackSubjects = subjectName
                .map(n => Vector(RuntimeOfflineFixture.id(n)))
                .getOrElse(c("names").arr.toVector.map(n => RuntimeOfflineFixture.id(n.str)))
              val sourceSubjects = item.obj
                .get("subjects")
                .map(_.arr.toVector.map(_.str))
                .getOrElse(
                  item("values").obj
                    .get("orderedResearcherIds")
                    .map(_.arr.toVector.map(_.str))
                    .getOrElse(fallbackSubjects)
                )
              val fields = spec("expectedValues").obj.toVector.map { (field, value) =>
                val numeric = value.str.matches("-?[0-9]+([.][0-9]+)?")
                ujson.Obj(
                  "field" -> field,
                  "number" -> (if (numeric) value else ujson.Null),
                  "text" -> (if (numeric) ujson.Null else value),
                  "ids" -> ujson.Null,
                  "flag" -> ujson.Null
                )
              } ++ spec.obj.get("expectedIdNames").toVector.flatMap(_.obj.toVector).map {
                (field, names) =>
                  val raw = names.arr.toVector.map(n => RuntimeOfflineFixture.id(n.str))
                  val ids =
                    if (spec.obj.get("sortExpectedIdFields").exists(_.arr.exists(_.str == field)))
                      raw.sorted
                    else raw
                  ujson.Obj(
                    "field" -> field,
                    "number" -> ujson.Null,
                    "text" -> ujson.Null,
                    "ids" -> ujson.Arr.from(ids),
                    "flag" -> ujson.Null
                  )
              }
              ujson.Obj(
                "claimType" -> claimType,
                "subjectIds" -> ujson.Arr.from(sourceSubjects),
                "values" -> ujson.Arr.from(fields),
                "evidenceIds" -> ujson.Arr(item("evidenceId")),
                "windowIds" -> ujson.Arr.from(
                  item("windows").arr.map(n => context("windowIds")(n.num.toInt))
                ),
                "templateId" -> (claimType.toLowerCase(java.util.Locale.ROOT) + "-v1")
              )
            }
          }
          .zipWithIndex
          .map { (claim, index) =>
            claim("claimId") = "benchmark-claim-" + index; claim
          }
        output(
          ujson.Obj(
            "schemaVersion" -> config.synthesisSchemaVersion,
            "claims" -> ujson.Arr.from(claims),
            "narrativeClaimIds" -> ujson.Arr.from(claims.map(_("claimId"))),
            "interpretation" -> "",
            "uncertainty" -> "Synthetic offline fixture only."
          )
        )
    }
  }
}
