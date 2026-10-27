package edu.uic.cs441.scholarchain.independent

import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite

class IndependentServices10BStructureSpec extends AnyFunSuite {
  private val root = IndependentRuntime9AFixture.root
  private val directory =
    root.resolve("modules/services/src/main/scala/edu/uic/cs441/scholarchain/services")

  test("HTTP adapters delegate and contain no graph, vector, planner or synthesis implementation") {
    val forbidden = Set(
      "GraphReader",
      "VectorStore",
      "EmbeddingClient",
      "LlmClient",
      "RuntimeAnswerWorkflow",
      "WorkflowRunner",
      "QueryPlannerAgent",
      "AnswerSynthesisAgent",
      "ClaimVerificationAgent",
      "executeGremlinQuery",
      "executeOpenCypherQuery",
      "shortestPaths",
      "cosineSimilarity"
    )
    for (name <- Vector("ApiServer.scala", "ApiApplication.scala")) {
      val code = RuntimeGraphFence.code(Files.readString(directory.resolve(name)))
      val tokens = "[A-Za-z_$][A-Za-z0-9_$]*".r.findAllIn(code).toSet
      assert(
        tokens.intersect(forbidden).isEmpty,
        s"$name contains retrieval capability: ${tokens.intersect(forbidden)}"
      )
    }
    val adapter = RuntimeGraphFence.code(Files.readString(directory.resolve("ApiServer.scala")))
    assert(adapter.contains("app.handle"))
    val application =
      RuntimeGraphFence.code(Files.readString(directory.resolve("ApiApplication.scala")))
    assert(application.contains("queries.submit"))
  }

  test("committed OpenAPI declares the complete public and internal HTTP surface") {
    val spec = Files.readString(
      root.resolve("modules/services/src/main/resources/openapi/scholarchain.v1.yaml")
    )
    val declared = "(?m)^  (/[^:\\n]*):\\s*$".r.findAllMatchIn(spec).map(_.group(1)).toSet
    val required = Set(
      "/v1/query",
      "/v1/jobs/{jobId}",
      "/v1/jobs/{jobId}/result",
      "/v1/evidence/{evidenceId}",
      "/v1/explain/{queryId}",
      "/v1/graph/nodes/{nodeId}",
      "/v1/graph/nodes/{nodeId}/neighbors",
      "/healthz",
      "/readyz",
      "/metrics"
    )
    assert(required.subsetOf(declared), s"Undocumented routes: ${required -- declared}")
    assert(declared.exists(_.startsWith("/internal/v1/semantic/")))
    assert(declared.exists(p => p.startsWith("/internal/v1/") && p.contains("metric")))
    assert(declared.exists(p => p.startsWith("/internal/v1/") && p.contains("path")))
    assert(spec.contains("InternalBearer") && spec.contains("ExternalBearer"))
    assert(spec.contains("traceId") && spec.contains("Idempotency-Key"))
  }
}
