package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import software.amazon.awssdk.services.bedrockruntime.model.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.file.{Files, Path}
import java.util.UUID

class Runtime9ASpec extends AnyFunSuite {
  private def resource(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    try new String(stream.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8)
    finally stream.close()
  }
  private val config =
    RuntimeConfigLoader.fromJson(resource("/scholarchain.runtime-config.v1.json")).toOption.get
  private val promptRoot = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("prompts"))
    .find(Files.isDirectory(_))
    .get
  private val assets = RuntimePromptAssets.fromDirectory(promptRoot, config).toOption.get
  private val run =
    StableIds.newRunId(UUID.fromString("00112233-4455-4677-8899-aabbccddeeff")).toOption.get
  private val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "synthetic-runtime-question",
    None,
    "synthetic-phase9",
    Some("2026-10-25"),
    None,
    run,
    Vector("Synthetic offline fixture; no observed researcher facts")
  )
  private def output(json: String) =
    LlmResult.Output(json, LlmUsage(Some(10), Some(20)), "scripted-model", "fixture-v1")
  private def planJson(
      names: Vector[String] = Vector.empty,
      operation: String = "RESEARCHER_RANKING"
  ): ujson.Obj =
    ujson.Obj(
      "schemaVersion" -> config.plannerSchemaVersion,
      "status" -> "SUPPORTED",
      "operations" -> ujson.Arr(operation),
      "researcherNames" -> ujson.Arr.from(names),
      "windowIds" -> ujson.Arr("all-years"),
      "comparisonWindowIds" -> ujson.Arr(),
      "topicFilters" -> ujson.Arr(),
      "institutionFilters" -> ujson.Arr(),
      "venueFilters" -> ujson.Arr(),
      "rankingMetric" -> "DISTINCT_COAUTHOR_COUNT",
      "rankingMeasure" -> ujson.Null,
      "authorCountConversion" -> false,
      "unsupportedReason" -> ujson.Null
    )
  private def planned(result: PlannerResult): QueryPlan = result match {
    case PlannerResult.Planned(plan, _, _) => plan
    case other                             => fail(s"Expected plan, got $other")
  }
  private val ranking = "Which researchers have the most distinct coauthors?"
  private def agent(script: Vector[LlmResult]) =
    new QueryPlannerAgent(new ScriptedLlmClient(script), config, assets)

  test("versioned assets load and planner schema rejects missing, unknown and fabricated fields") {
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, planJson()).isRight)
    val missing = planJson(); missing.obj.remove("windowIds")
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, missing).isLeft)
    val extra = planJson(); extra("cypher") = "MATCH (n) RETURN n"
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, extra).isLeft)
    val op = planJson(operation = "DROP_DATABASE")
    assert(RuntimeJsonSchema.validate(assets.plannerSchema, op).isLeft)
    assert(
      RuntimeJsonSchema
        .validate(ujson.Obj("type" -> "string", "pattern" -> "x"), ujson.Str("x"))
        .isLeft
    )
    assert(
      RuntimePromptAssets
        .fromDirectory(promptRoot, config.copy(plannerPromptVersion = "unknown"))
        .isLeft
    )
  }
  test("structured stage logs contain correlation and outcome without question or names") {
    var plan: QueryPlan = null
    val events = LogbackTestSupport.capture("scholarchain.runtime.stage") {
      plan = planned(
        agent(Vector(output(planJson().render()))).plan(ranking, "trace-fixture", provenance)
      )
      new ResearcherResolverAgent(new InMemoryEntityLinkCache, config).resolve(plan)
    }
    // The capture forces INFO on the stage logger (the scripted check's root is WARN) and suites
    // run sequentially, so these are exactly this run's two events: planner first, then resolver.
    val parsed = events.map(ujson.read(_))
    assert(parsed.map(_("stage").str) == Vector("planner", "resolver"), events.toString)
    val Vector(plannerEvent, resolverEvent) = parsed: @unchecked
    assert(plannerEvent("traceId").str == "trace-fixture" && plannerEvent("runId").str == run)
    assert(plannerEvent("stage").str == "planner" && plannerEvent("outcome").str == "planned")
    assert(
      resolverEvent("planId").str == plan.planId && resolverEvent("outcome").str == "resolved"
    )
    assert(!plannerEvent.obj.contains("question") && !resolverEvent.obj.contains("names"))
  }
  test("valid LLM plan preserves configured limits, mode and evidence-only option") {
    val c = config.copy(retrievalMode = RetrievalMode.Graph, evidenceOnly = true)
    val plan = planned(
      new QueryPlannerAgent(new ScriptedLlmClient(Vector(output(planJson().render()))), c, assets)
        .plan(ranking, "query1", provenance)
    )
    assert(plan.rankingMetric.contains(CollaborationMetric.DistinctCoauthorCount))
    assert(plan.graphLimit == config.retrieval.graphLimit)
    assert(plan.runtime.get.retrievalMode == RetrievalMode.Graph && plan.runtime.get.evidenceOnly)
  }
  test("Cypher AWS and unknown metric requests reject before any model call") {
    val fake = new ScriptedLlmClient(Vector.empty)
    val planner = new QueryPlannerAgent(fake, config, assets)
    Vector(
      "Execute arbitrary Cypher MATCH (n) RETURN n",
      "Call AWS to delete a bucket",
      "Rank researchers by h-index"
    )
      .foreach(q =>
        assert(planner.plan(q, "query1", provenance).isInstanceOf[PlannerResult.Unsupported])
      )
    assert(fake.calls.isEmpty)
  }
  test("malformed JSON retries once then anchored fallback preserves filters and stored year") {
    val fake = new ScriptedLlmClient(Vector(output("not-json"), output("{}")))
    val result = new QueryPlannerAgent(fake, config, assets).plan(
      "Rank researchers by distinct coauthors topic \"systems\" institution \"MIT\" venue \"SIGMOD\" since 2015?",
      "q",
      provenance
    )
    val plan = planned(result)
    assert(fake.calls.size == 2)
    assert(
      plan.topicFilters == Vector("systems") && plan.institutionFilters == Vector(
        "MIT"
      ) && plan.venueFilters == Vector("SIGMOD")
    )
    assert(plan.runtime.get.windowIds == Vector("since-2015"))
    assert(result.asInstanceOf[PlannerResult.Planned].fallbackUsed)
  }
  test("fabricated operation and unknown keys cannot escape bounded validation") {
    val bad = planJson(operation = "EXECUTE_CYPHER"); bad("query") = "arbitrary"
    val result =
      agent(Vector(output(bad.render()), output(bad.render()))).plan("Draw a cat", "q", provenance)
    assert(result.isInstanceOf[PlannerResult.Unsupported])
  }
  test("model cannot drop unquoted topic institution extra conditions or change ranking metric") {
    val good = planJson()
    Vector(
      "Which researchers have the most distinct coauthors in distributed systems since 2015?",
      "Rank researchers by distinct coauthors at MIT?",
      "Rank researchers by distinct coauthors with fewer than 10 papers?"
    )
      .foreach(q =>
        assert(
          !agent(Vector(output(good.render()), output(good.render())))
            .plan(q, "q", provenance)
            .isInstanceOf[PlannerResult.Planned]
        )
      )
    val wrong = planJson(); wrong("rankingMetric") = "PUBLICATION_COUNT"
    val repaired = planned(
      agent(Vector(output(wrong.render()), output(wrong.render()))).plan(ranking, "q", provenance)
    )
    assert(repaired.rankingMetric.contains(CollaborationMetric.DistinctCoauthorCount))
  }
  test("a proposed filter or name cannot hide an unknown metric or named ranking scope") {
    val relabeled = planJson(); relabeled("topicFilters") = ujson.Arr("PageRank")
    assert(
      !agent(Vector(output(relabeled.render()), output(relabeled.render())))
        .plan("Rank researchers by PageRank?", "q", provenance)
        .isInstanceOf[PlannerResult.Planned]
    )
    val named = planJson(Vector("Alice", "Bob"))
    assert(
      !agent(Vector(output(named.render()), output(named.render())))
        .plan("Rank researchers by distinct coauthors among Alice and Bob?", "q", provenance)
        .isInstanceOf[PlannerResult.Planned]
    )
  }
  test("model cannot invent a name filter window or silently drop a quoted constraint") {
    val invented = planJson(); invented("institutionFilters") = ujson.Arr("Harvard")
    val unknownWindow = planJson(); unknownWindow("windowIds") = ujson.Arr("1900-1901")
    Vector(invented, unknownWindow).foreach(bad => {
      val plan = planned(
        agent(Vector(output(bad.render()), output(bad.render()))).plan(ranking, "q", provenance)
      )
      assert(plan.institutionFilters.isEmpty && plan.runtime.get.windowIds == Vector("all-years"))
    })
    val fallback = planned(
      agent(Vector(output(planJson().render()), output(planJson().render())))
        .plan("Rank researchers by distinct coauthors topic \"systems\"?", "q", provenance)
    )
    assert(fallback.topicFilters == Vector("systems"))
    assert(
      agent(Vector(output(planJson().render()), output(planJson().render())))
        .plan("Rank researchers by distinct coauthors since 1900?", "q", provenance)
        .isInstanceOf[PlannerResult.Unsupported]
    )
  }
  test("unsupported and exhausted scripted model fail safely without network") {
    val unsupported = planJson(); unsupported("status") = "UNSUPPORTED";
    unsupported("unsupportedReason") = "not-stored"
    assert(
      agent(Vector(output(unsupported.render()))).plan(ranking, "q", provenance) == PlannerResult
        .Unsupported("not-stored", 1)
    )
    assert(
      agent(Vector.empty)
        .plan("Find a cure for cancer", "q", provenance)
        .isInstanceOf[PlannerResult.Unsupported]
    )
  }
  test("late model and cache responses fail with deterministic stage deadlines") {
    var now = 0L
    val lateModel = new LlmClient {
      def complete(request: StructuredLlmRequest): LlmResult = {
        now = config.deadlines.plannerMs * 1000000L
        output(planJson().render())
      }
    }
    assert(
      new QueryPlannerAgent(lateModel, config, assets, () => now).plan(ranking, "q", provenance) ==
        PlannerResult.Failed("planner-deadline")
    )
    now = 0L
    val lateCache = new EntityLinkCache {
      def putLink(link: EntityLink): StorageResult[EntityLink] = StorageResult.Rejected("unused")
      def lookupByExternalId(namespace: String, id: String): StorageResult[Vector[EntityLink]] =
        StorageResult.Missing
      def lookupByNormalizedName(name: String): StorageResult[Vector[EntityLink]] = {
        now = config.deadlines.resolverMs * 1000000L
        StorageResult.Missing
      }
    }
    val plan = resolverPlan(Vector("Nobody"))
    assert(
      new ResearcherResolverAgent(lateCache, config, None, () => now)
        .resolve(plan) == ResolverResult.Failed("resolver-deadline")
    )
  }
  test("a model plan may preserve an unquoted topic and exact stored since window") {
    val value = planJson(); value("topicFilters") = ujson.Arr("distributed systems");
    value("windowIds") = ujson.Arr("since-2015")
    val plan = planned(
      agent(Vector(output(value.render())))
        .plan(
          "Which researchers have the most distinct coauthors in distributed systems since 2015?",
          "q",
          provenance
        )
    )
    assert(
      plan.topicFilters == Vector("distributed systems") && plan.runtime.get.windowIds == Vector(
        "since-2015"
      )
    )
  }

  private def resolverPlan(names: Vector[String]): QueryPlan = planned(
    agent(Vector(output(planJson(names, "DIRECT_COAUTHORS").render())))
      .plan(s"Direct coauthors of \"${names.headOption.getOrElse("Unknown")}\"?", "q", provenance)
  )
  private def researcher(name: String): String =
    StableIds.researcherIdFromDblpName("identity-fixture", name).toOption.get
  private def link(
      cache: InMemoryEntityLinkCache,
      name: String,
      id: String,
      confidence: Option[Double],
      source: String = "source-1"
  ): Unit = {
    val result = cache.putLink(
      EntityLink(
        "name",
        TextNorm.personName(name),
        "fixture-policy",
        source,
        id,
        name,
        Vector("fixture-institution"),
        confidence,
        run,
        Vector("fixture-source-pointer")
      )
    )
    assert(StorageResult.successful(result))
  }
  test("unique canonical ID groups source aliases and preserves absent confidence") {
    val cache = new InMemoryEntityLinkCache
    val id = researcher("Alice")
    link(cache, "Alice", id, None); link(cache, "Alice", id, None, "source-2")
    val result = new ResearcherResolverAgent(cache, config).resolve(resolverPlan(Vector("Alice")))
    result match {
      case ResolverResult.Resolved(Vector(c)) =>
        assert(c.researcherId == id && c.sourceIds == Vector("source-1", "source-2"))
        assert(c.confidence.isEmpty && c.affiliations == Vector("fixture-institution"))
        assert(c.runIds == Vector(run) && c.coauthorContext.isEmpty)
      case other => fail(s"Expected unique candidate, got $other")
    }
  }
  test("common-name candidates abstain even with different confidence values") {
    val cache = new InMemoryEntityLinkCache
    link(cache, "Wei Wang", researcher("Wei Wang 0001"), Some(0.99))
    link(cache, "Wei Wang", researcher("Wei Wang 0002"), Some(0.60), "source-2")
    new ResearcherResolverAgent(cache, config).resolve(resolverPlan(Vector("Wei Wang"))) match {
      case ResolverResult.Ambiguous("Wei Wang", cs, totalCandidateCount, truncated) =>
        assert(cs.size == 2 && cs.flatMap(_.confidence).toSet == Set(0.99, 0.60))
        assert(totalCandidateCount == 2 && !truncated)
      case other => fail(s"Expected ambiguity, got $other")
    }
  }
  test("source-backed coauthor context retains truncation and provenance") {
    val cache = new InMemoryEntityLinkCache
    val id = researcher("Alice"); val coauthor = researcher("Bob")
    link(cache, "Alice", id, None)
    val ref = SummarySourceRef("edges/type=coauthored_with", "source-edge", "researcherB")
    val artifact = new RuntimeArtifactStore {
      def rank(
          w: String,
          m: RuntimeRankingMetric,
          f: RuntimePopulationFilter,
          l: Int
      ): StorageResult[RuntimeRankingPage] = StorageResult.Missing
      def communitySummary(id: String, w: String): StorageResult[CommunitySummary] =
        StorageResult.Missing
      def bridgeMetrics(id: String, w: String): StorageResult[RuntimeBridgeRecord] =
        StorageResult.Missing
      def temporalChange(id: String, f: String, t: String): StorageResult[RuntimeTemporalRecord] =
        StorageResult.Missing
      def edgeSupport(id: String, w: String): StorageResult[RuntimeEdgeRecord] =
        StorageResult.Missing
      def researcherContext(r: String, w: String, l: Int): StorageResult[RuntimeResearcherContext] =
        StorageResult.Found(
          RuntimeResearcherContext(r, w, None, None, None, Vector(coauthor), true, Vector(ref), run)
        )
    }
    new ResearcherResolverAgent(cache, config, Some(artifact))
      .resolve(resolverPlan(Vector("Alice"))) match {
      case ResolverResult.Resolved(Vector(c)) =>
        assert(c.coauthorContext == Vector(coauthor) && c.coauthorContextTruncated.contains(true))
        assert(c.evidenceRefs.contains("edges/type=coauthored_with:source-edge:researcherB"))
        assert(c.runIds.contains(run) && c.confidence.isEmpty)
      case other => fail(s"Expected source-backed candidate, got $other")
    }
  }
  test("DBLP exact suffixes stay separate and base-name alias rows remain ambiguous") {
    val cache = new InMemoryEntityLinkCache
    val one = researcher("Name 0001"); val two = researcher("Name 0002")
    link(cache, "Name 0001", one, None); link(cache, "Name 0002", two, None)
    link(cache, "Name", one, None, "base-1"); link(cache, "Name", two, None, "base-2")
    val resolver = new ResearcherResolverAgent(cache, config)
    assert(
      resolver
        .resolve(resolverPlan(Vector("Name 0001")))
        .asInstanceOf[ResolverResult.Resolved]
        .candidates
        .head
        .researcherId == one
    )
    assert(
      resolver
        .resolve(resolverPlan(Vector("Name 0002")))
        .asInstanceOf[ResolverResult.Resolved]
        .candidates
        .head
        .researcherId == two
    )
    assert(
      resolver
        .resolve(resolverPlan(Vector("Name")))
        .asInstanceOf[ResolverResult.Ambiguous]
        .candidates
        .size == 2
    )
    assert(resolver.resolve(resolverPlan(Vector("Nobody"))) == ResolverResult.NotFound("Nobody"))
  }

  private def sdk(handler: ConverseRequest => ConverseResponse): BedrockRuntimeClient = Proxy
    .newProxyInstance(
      classOf[BedrockRuntimeClient].getClassLoader,
      Array(classOf[BedrockRuntimeClient]),
      new InvocationHandler {
        def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = method.getName match {
          case "converse"    => handler(args(0).asInstanceOf[ConverseRequest])
          case "serviceName" => "offline-fixture"
          case "close"       => null
          case other         => throw new UnsupportedOperationException(other)
        }
      }
    )
    .asInstanceOf[BedrockRuntimeClient]
  private def tool(
      name: String = "submit_query_plan",
      input: Document = LlmDocuments.toDocument(planJson())
  ) =
    ContentBlock
      .builder()
      .toolUse(ToolUseBlock.builder().name(name).toolUseId("fixture-tool-id").input(input).build())
      .build()
  private def response(blocks: ContentBlock*): ConverseResponse = ConverseResponse
    .builder()
    .output(
      ConverseOutput
        .builder()
        .message(Message.builder().role(ConversationRole.ASSISTANT).content(blocks*).build())
        .build()
    )
    .stopReason(StopReason.TOOL_USE)
    .usage(TokenUsage.builder().inputTokens(12).outputTokens(15).totalTokens(27).build())
    .build()
  private def request = StructuredLlmRequest(
    "submit_query_plan",
    assets.plannerPrompt,
    "{\"question\":\"fixture\"}",
    assets.plannerSchema.render(),
    config.plannerPromptVersion,
    config.plannerSchemaVersion,
    config.deadlines.plannerMs
  )
  test(
    "Bedrock adapter forces configured tool and model, preserves schema and usage, no client construction"
  ) {
    var seen = false
    val client = sdk { call =>
      seen = true
      assert(call.modelId() == config.model.modelId)
      assert(call.toolConfig().toolChoice().tool().name() == "submit_query_plan")
      assert(call.toolConfig().tools().get(0).toolSpec().inputSchema().json().isMap)
      assert(call.inferenceConfig().temperature().doubleValue() == config.model.temperature)
      assert(call.overrideConfiguration().get().apiCallTimeout().isPresent)
      response(tool())
    }
    new BedrockConverseLlmClient(client, config).complete(request) match {
      case LlmResult.Output(json, usage, model, version) =>
        assert(seen && ujson.read(json) == planJson())
        assert(
          usage == LlmUsage(
            Some(12),
            Some(15)
          ) && model == config.model.modelId && version == config.model.modelVersion
        )
      case other => fail(s"Expected tool output, got $other")
    }
  }
  test("Bedrock adapter rejects text substitutes wrong tools multiple blocks and unsafe numbers") {
    val unsafe = Document.fromMap(
      java.util.Map.of("count", Document.fromNumber(new java.math.BigDecimal("9007199254740993")))
    )
    val outputs = Vector(
      response(ContentBlock.builder().text("{json-looking-text}").build()),
      response(tool("wrong_tool")),
      response(tool(), tool()),
      response(tool(input = unsafe))
    )
    outputs.foreach(r =>
      assert(
        new BedrockConverseLlmClient(sdk(_ => r), config)
          .complete(request)
          .isInstanceOf[LlmResult.Failure]
      )
    )
  }
  test("Bedrock provider exception messages never escape typed failure") {
    val client = sdk(_ =>
      throw BedrockRuntimeException
        .builder()
        .statusCode(400)
        .message("sensitive-fixture-payload")
        .build()
    )
    val result = new BedrockConverseLlmClient(client, config).complete(request)
    assert(
      result == LlmResult.Failure("llm-provider-rejected") && !result.toString.contains("sensitive")
    )
  }
  test(
    "synthesis proposal schema requires typed evidence-backed claims and forbids raw narrative or verdict"
  ) {
    val minimal = ujson.Obj(
      "schemaVersion" -> config.synthesisSchemaVersion,
      "claims" -> ujson.Arr(),
      "narrativeClaimIds" -> ujson.Arr(),
      "interpretation" -> "",
      "uncertainty" -> "Missing evidence; abstain"
    )
    assert(RuntimeJsonSchema.validate(assets.synthesisSchema, minimal).isRight)
    minimal("narrative") = "Alice has 500 collaborators"
    assert(RuntimeJsonSchema.validate(assets.synthesisSchema, minimal).isLeft)
  }
}
