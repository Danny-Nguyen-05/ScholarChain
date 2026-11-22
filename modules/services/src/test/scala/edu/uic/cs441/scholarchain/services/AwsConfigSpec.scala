package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.RetrievalMode
import org.scalatest.funsuite.AnyFunSuite

class AwsConfigSpec extends AnyFunSuite {
  import AwsTestEnv.*
  private val roles = Vector("query-api", "graph-service", "semantic-service", "embedding-worker")

  // Required variables beyond the shared service configuration, per role.
  private val tables = Vector(
    "SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER",
    "SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE",
    "SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION",
    "SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE",
    "SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY",
    "SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE",
    "SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX",
    "AWS_REGION"
  )
  private val embedding = Vector(
    "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL",
    "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION",
    "SCHOLARCHAIN_EMBEDDING_DIMENSION"
  )
  private val required: Map[String, Vector[String]] = Map(
    "graph-service" -> (tables ++ Vector(
      "SCHOLARCHAIN_STORAGE_GRAPH_BUCKET",
      "SCHOLARCHAIN_NEPTUNE_ENDPOINT",
      "SCHOLARCHAIN_GRAPH_CURSOR_KEY"
    )),
    "semantic-service" -> (tables ++ embedding ++ Vector(
      "SCHOLARCHAIN_STORAGE_RAG_BUCKET",
      "SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET",
      "SCHOLARCHAIN_SEMANTIC_INDEX"
    )),
    "embedding-worker" -> (tables ++ embedding ++ Vector(
      "SCHOLARCHAIN_STORAGE_RAG_BUCKET",
      "SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET",
      "SCHOLARCHAIN_SEMANTIC_INDEX",
      "SCHOLARCHAIN_SQS_QUEUE_URL",
      "SCHOLARCHAIN_SQS_DLQ_URL",
      "SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX"
    )),
    "query-api" -> (tables ++ embedding ++ Vector(
      "SCHOLARCHAIN_STORAGE_RAG_BUCKET",
      "SCHOLARCHAIN_GRAPH_BASE_URI",
      "SCHOLARCHAIN_SEMANTIC_BASE_URI",
      "SCHOLARCHAIN_INTERNAL_TOKEN",
      "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL",
      "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION"
    ))
  )

  test("a complete environment parses for every role") {
    roles.foreach(role => assert(parse(role, forRole(role)).isRight, role))
  }

  test("every required variable is refused by name when missing or blank") {
    for (role <- roles; name <- required(role)) {
      val without = forRole(role) - name
      assert(
        ServiceConfig.fromEnvironment(without).isRight &&
          parse(role, without) == Left("missing-aws-configuration:" + name),
        s"$role $name"
      )
      assert(
        parse(role, forRole(role).updated(name, "  ")) == Left("missing-aws-configuration:" + name)
      )
    }
  }

  test("invalid values are refused by variable name and never echoed") {
    val secret = "UPPER secret value/with space"
    val cases: Vector[(String, String, String)] = Vector(
      ("graph-service", "AWS_REGION", "mars"),
      ("graph-service", "SCHOLARCHAIN_APPLICATION_REGION", "us-west-2"),
      ("graph-service", "SCHOLARCHAIN_STORAGE_GRAPH_BUCKET", secret),
      ("graph-service", "SCHOLARCHAIN_NEPTUNE_ENDPOINT", "http://host.example:8182"),
      ("graph-service", "SCHOLARCHAIN_NEPTUNE_ENDPOINT", "https://host.example"),
      ("graph-service", "SCHOLARCHAIN_NEPTUNE_ENDPOINT", "https://user:pw@host.example:8182"),
      ("graph-service", "SCHOLARCHAIN_NEPTUNE_ENDPOINT", "https://host.example:8182/path?x=1"),
      ("graph-service", "SCHOLARCHAIN_NEPTUNE_QUERY_TIMEOUT_MS", "0"),
      ("graph-service", "SCHOLARCHAIN_GRAPH_CURSOR_KEY", "short"),
      ("graph-service", "SCHOLARCHAIN_GRAPH_SNAPSHOT_ID", secret),
      ("graph-service", "SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION", "sc-RunLedger"),
      ("graph-service", "SCHOLARCHAIN_READINESS_CACHE_MS", "0"),
      ("graph-service", "SCHOLARCHAIN_READINESS_TIMEOUT_MS", "99"),
      ("graph-service", "SCHOLARCHAIN_READINESS_TIMEOUT_MS", "not-a-number"),
      ("semantic-service", "SCHOLARCHAIN_SEMANTIC_INDEX", "not-an-index"),
      ("semantic-service", "SCHOLARCHAIN_EMBEDDING_DIMENSION", "300"),
      ("semantic-service", "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", secret),
      ("semantic-service", "SCHOLARCHAIN_S3_VECTORS_METRIC", "dot"),
      ("embedding-worker", "SCHOLARCHAIN_SQS_QUEUE_URL", "http://sqs.example/q"),
      ("embedding-worker", "SCHOLARCHAIN_SQS_DLQ_URL", "not a url"),
      ("embedding-worker", "SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX", "/absolute"),
      ("embedding-worker", "SCHOLARCHAIN_WORKER_WAIT_SECONDS", "21"),
      ("query-api", "SCHOLARCHAIN_INTERNAL_TOKEN", "a-token-whose-hash-differs"),
      ("query-api", "SCHOLARCHAIN_GRAPH_BASE_URI", "ftp://graph.example"),
      ("query-api", "SCHOLARCHAIN_SEMANTIC_BASE_URI", "http://u:p@semantic.example"),
      (
        "query-api",
        "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL",
        "arn:aws:bedrock:us-east-2:1:inference-profile/x"
      ),
      ("query-api", "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION", secret),
      ("query-api", "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY", "only-the-key"),
      ("query-api", "SCHOLARCHAIN_QUERY_SESSION_TTL_SECONDS", "-5"),
      ("query-api", "SCHOLARCHAIN_RUNTIME_PLANNER_DEADLINE_MS", "0")
    )
    for ((role, name, value) <- cases) {
      val result = parse(role, forRole(role).updated(name, value))
      assert(result.isLeft, s"$role $name=$value")
      val message = result.left.toOption.get
      assert(message.startsWith("invalid-aws-configuration"), s"$role $name -> $message")
      assert(!message.contains(value) || value.length < 4, s"value echoed for $name")
    }
    assert(
      parse("graph-service", graph.updated("SCHOLARCHAIN_NEPTUNE_ENDPOINT", "http://h:1")) ==
        Left("invalid-aws-configuration:SCHOLARCHAIN_NEPTUNE_ENDPOINT")
    )
  }

  test("a partial runtime artifact pointer is refused and a complete one is accepted") {
    val base = forRole("query-api")
    val sha = "a" * 64
    val complete = base ++ Map(
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY" -> "runtime/versions/v1/artifacts.json",
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256" -> sha,
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID" -> "run:1"
    )
    assert(
      parse("query-api", complete).toOption.get.asInstanceOf[QueryRoleConfig].artifact.nonEmpty
    )
    assert(
      parse("query-api", complete - "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID") ==
        Left("invalid-aws-configuration:SCHOLARCHAIN_RUNTIME_ARTIFACT_*")
    )
    assert(
      parse("query-api", complete.updated("SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256", "xyz")) ==
        Left("invalid-aws-configuration:SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256")
    )
  }

  test(
    "an inference-profile id is accepted as the synthesis model and reaches the Converse model id"
  ) {
    val cfg = parse("query-api", forRole("query-api")).toOption.get.asInstanceOf[QueryRoleConfig]
    assert(cfg.synthesisModelId == profile)
    val runtime = AwsComposition.runtimeConfig(cfg).toOption.get
    assert(runtime.model.modelId == profile)
    assert(runtime.model.modelVersion == foundation && runtime.model.region == "us-east-2")
    // Behavior pinned by finding P14-1 stays as packaged.
    assert(runtime.model.temperature == 0.0)
    val foundationOnly = forRole("query-api")
      .updated("SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL", foundation)
    val plain = parse("query-api", foundationOnly).toOption.get.asInstanceOf[QueryRoleConfig]
    assert(AwsComposition.runtimeConfig(plain).toOption.get.model.modelId == foundation)
  }

  test("runtime deadline overrides are validated against the synchronous budget") {
    val ok = forRole("query-api") ++ Map(
      "SCHOLARCHAIN_RUNTIME_SYNTHESIS_DEADLINE_MS" -> "9000",
      "SCHOLARCHAIN_RUNTIME_SYNCHRONOUS_DEADLINE_MS" -> "40000"
    )
    val config = parse("query-api", ok).toOption.get.asInstanceOf[QueryRoleConfig]
    val runtime = AwsComposition.runtimeConfig(config).toOption.get
    assert(
      runtime.deadlines.synthesisMs == 9000 && runtime.operations.synchronousDeadlineMs == 40000
    )
    val tooTight =
      forRole("query-api").updated("SCHOLARCHAIN_RUNTIME_SYNCHRONOUS_DEADLINE_MS", "1000")
    val bad = parse("query-api", tooTight).toOption.get.asInstanceOf[QueryRoleConfig]
    assert(AwsComposition.runtimeConfig(bad) == Left("runtime-config-invalid"))
  }

  test("the runtime retrieval mode override is optional, graph or fused, and never echoed") {
    val name = "SCHOLARCHAIN_RUNTIME_RETRIEVAL_MODE"
    def config(env: Map[String, String]) =
      parse("query-api", env).toOption.get.asInstanceOf[QueryRoleConfig]
    // Unset: no override, the packaged mode (fused) is kept.
    val unset = config(forRole("query-api"))
    assert(unset.overrides.retrievalMode.isEmpty)
    assert(AwsComposition.runtimeConfig(unset).toOption.get.retrievalMode == RetrievalMode.Fused)
    for ((wire, mode) <- Seq("graph" -> RetrievalMode.Graph, "fused" -> RetrievalMode.Fused)) {
      val c = config(forRole("query-api").updated(name, wire))
      assert(c.overrides.retrievalMode.contains(mode))
      assert(AwsComposition.runtimeConfig(c).toOption.get.retrievalMode == mode)
    }
    for (value <- Seq("vector", "Graph", "unknown-mode-value", "")) {
      val result = parse("query-api", forRole("query-api").updated(name, value))
      if (value.isEmpty) assert(result.isRight, "a blank value is an unset value")
      else {
        assert(result == Left("invalid-aws-configuration:" + name))
        assert(!result.left.toOption.get.contains(value))
      }
    }
  }

  test("the internal token never appears when a role configuration is rendered") {
    val rendered = parse("query-api", forRole("query-api")).toOption.get.toString
    assert(!rendered.contains(internalToken) && rendered.contains("<redacted>"))
  }

  test("an unknown role is refused") {
    assert(
      AwsServiceConfig.fromEnvironment("other", graph, service(graph)) ==
        Left("invalid-aws-configuration:role")
    )
  }

  test("optional values take their documented defaults") {
    val g = parse("graph-service", graph).toOption.get.asInstanceOf[GraphRoleConfig]
    assert(g.snapshotId == LiveGraphSnapshot.unpinnedId && g.neptuneTimeoutMs == 5000)
    assert(g.common.readiness == AwsReadinessSettings(5000, 2000))
    val q = parse("query-api", forRole("query-api")).toOption.get.asInstanceOf[QueryRoleConfig]
    assert(
      q.artifact.isEmpty && q.sessionTtlSeconds.isEmpty && q.evidenceIndexPrefix == "evidence-index"
    )
    assert(q.datasetSnapshot == "runtime-live-unpinned")
    val w = parse("embedding-worker", worker).toOption.get.asInstanceOf[WorkerRoleConfig]
    assert(w.queue.visibilitySeconds == 30 && w.queue.waitSeconds == 0 && w.metric == "cosine")
  }
}
