package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.{LlmClient, LlmResult, LlmUsage, StructuredLlmRequest}
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

/** The local stack runs graph-service, semantic-service and query-api in one process; the query
  * role reaches the graph only through `RemoteGraphReader` over the graph-service HTTP routes.
  * Shortest-path and community-comparison questions used to abstain with
  * `essential-evidence-unavailable` there (path depth above the service ceiling; unsupported
  * community reads). They must complete with verified claims.
  */
class LocalGraphQuestionsSpec extends AnyFunSuite {
  private val apiKey = "local-graph-questions-api-key"
  private val auth = Map("Authorization" -> ("Bearer " + apiKey))

  /** Scripted model: the planner tool returns the community plan the deterministic fallback grammar
    * cannot express; every other tool behaves as `ScriptedAnswerLlm`.
    */
  private final class PlanningLlm(runtime: RuntimeConfig, plan: ujson.Value)
      extends ScriptedAnswerLlm(runtime) {
    override def complete(request: StructuredLlmRequest): LlmResult =
      if (request.toolName == "submit_query_plan")
        LlmResult.Output(
          plan.render(),
          LlmUsage(None, None),
          runtime.model.modelId,
          runtime.model.modelVersion
        )
      else super.complete(request)
  }
  private final class PlanningProviders(plan: RuntimeConfig => ujson.Value)
      extends ProviderClients {
    def anthropic(key: Secret, runtime: RuntimeConfig): Either[String, LlmClient] =
      Right(new PlanningLlm(runtime, plan(runtime)))
    def voyage(
        key: Secret,
        model: EmbeddingModel,
        purpose: EmbeddingPurpose
    ): Either[String, EmbeddingClient] = Left("scripted-no-embedding")
  }
  private def communityPlan(runtime: RuntimeConfig): ujson.Value = ujson.Obj(
    "schemaVersion" -> runtime.plannerSchemaVersion,
    "status" -> "SUPPORTED",
    "operations" -> ujson.Arr("COMMUNITY_COMPARISON"),
    "researcherNames" -> ujson.Arr("Ada Alpha"),
    "windowIds" -> ujson.Arr("all-years"),
    "comparisonWindowIds" -> ujson.Arr(),
    "topicFilters" -> ujson.Arr(),
    "institutionFilters" -> ujson.Arr(),
    "venueFilters" -> ujson.Arr(),
    "rankingMetric" -> ujson.Null,
    "rankingMeasure" -> ujson.Null,
    "authorCountConversion" -> false,
    "unsupportedReason" -> ujson.Null
  )

  private def start(fixture: LocalExportFixture, providers: ProviderClients): RunningLocalStack =
    LocalQueryStack
      .start(
        fixture.stores(),
        Map(
          LocalQueryStack.apiKeyHashVariable -> Auth.sha256(apiKey),
          LocalQueryStack.portVariable -> "0",
          LocalQueryStack.anthropicKeyVariable -> "local-graph-questions-model-key",
          "SCHOLARCHAIN_PROMPTS_DIR" -> AwsTestEnv.promptsDirectory.toString
        ),
        providers,
        _ => ()
      )
      .fold(code => fail("stack refused with exit " + code), identity)

  private def answered(stack: RunningLocalStack, question: String, key: String) = {
    val (status, text) = Http.post(
      stack.port,
      "/v1/query",
      ujson.Obj("question" -> question).render(),
      auth ++ Map("Idempotency-Key" -> key, "Content-Type" -> "application/json")
    )
    val body = ujson.read(text)
    assert(status == 200, body.render())
    val explain = ujson.read(Http.get(stack.port, "/v1/explain/" + body("queryId").str, auth)._2)
    assert(
      explain("outcome").str == "ANSWERED",
      "outcome=" + explain("outcome").str + " reason=" + explain.obj.get("reason").map(_.render())
    )
    val claims = body("claims").arr
    assert(claims.nonEmpty && claims.forall(_("verificationStatus").str == "VERIFIED"))
    claims
  }
  private def subjects(claims: collection.Seq[ujson.Value]): Set[String] =
    claims.flatMap(_("runtime")("subjectIds").arr.map(_.str)).toSet

  test("a one-hop and a two-hop shortest-path question complete with verified claims") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val stack = start(fixture, new ScriptedProviders)
    try {
      val oneHop = answered(
        stack,
        "What is the shortest path between \"Ada Alpha\" and \"Collab Aa\"?",
        "paths-one-hop"
      )
      assert(Set(fixture.hub, fixture.id(1)).subsetOf(subjects(oneHop)))
      val twoHop = answered(
        stack,
        "What is the shortest path between \"Collab Aa\" and \"Collab Ab\"?",
        "paths-two-hop"
      )
      assert(Set(fixture.id(1), fixture.id(2)).subsetOf(subjects(twoHop)))
    } finally stack.close()
  }

  test("a community-comparison question completes with verified claims over the graph role") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val stack = start(fixture, new PlanningProviders(communityPlan))
    try {
      val claims = answered(stack, "Compare communities of \"Ada Alpha\"", "community-compare")
      assert(subjects(claims).contains(fixture.hub))
      // The graph role served both community routes (unmatched-route 200s of the graph role).
      val metrics = Http.get(stack.graphPort, "/metrics", auth)._2
      assert(metrics.contains("api_route_requests_total{route=\"unmatched\",status=\"200\"}"))
    } finally stack.close()
  }

  test("the internal graph routes, community routes included, refuse a call without the token") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 1)
    val stack = start(fixture, new ScriptedProviders)
    try {
      val community = "community:" + StableIds.sha256Hex(fixture.hub)
      for (
        path <- Vector(
          "/internal/v1/graph/communities/" + community + "/members",
          "/internal/v1/graph/communities/" + community + "/cross-edges",
          "/internal/v1/graph/paths?from=a&to=b"
        )
      ) {
        assert(Http.get(stack.graphPort, path)._1 == 401, path)
        // The public API key is not the internal credential.
        assert(Http.get(stack.graphPort, path, auth)._1 == 401, path)
      }
    } finally stack.close()
  }
}
