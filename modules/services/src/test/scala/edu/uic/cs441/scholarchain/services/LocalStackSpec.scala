package edu.uic.cs441.scholarchain.services

import ch.qos.logback.classic.Logger as LogbackLogger
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.core.read.ListAppender
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.{LlmClient, LlmResult, LlmUsage, StructuredLlmRequest}
import edu.uic.cs441.scholarchain.storage.*
import java.io.{ByteArrayOutputStream, PrintStream}
import java.nio.file.Files
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

/** Answers the planner with a closed failure (so the planner's deterministic fallback builds the
  * plan) and the synthesis with the verbatim claim scaffold it was sent, selected by id. It is the
  * model a real provider would be asked to imitate; it never leaves the process.
  */
class ScriptedAnswerLlm(runtime: RuntimeConfig) extends LlmClient {
  val requests = new ConcurrentLinkedQueue[StructuredLlmRequest]()
  def complete(request: StructuredLlmRequest): LlmResult = {
    requests.add(request)
    request.toolName match {
      case "submit_answer" =>
        val ids = ujson.read(request.userData)("claimScaffold").arr.map(_("claimId").str)
        LlmResult.Output(
          ujson
            .Obj(
              "schemaVersion" -> runtime.synthesisSchemaVersion,
              "claims" -> ujson.Arr(),
              "selectedClaimIds" -> ujson.Arr.from(ids),
              "narrativeClaimIds" -> ujson.Arr(),
              "interpretation" -> "",
              "uncertainty" -> "Scripted local test model."
            )
            .render(),
          LlmUsage(None, None),
          runtime.model.modelId,
          runtime.model.modelVersion
        )
      case _ => LlmResult.Failure("scripted-no-plan")
    }
  }
}

/** Provider seam for the local stack tests: records the key it was handed, builds scripted models.
  */
final class ScriptedProviders extends ProviderClients {
  val builds = new AtomicInteger
  @volatile var receivedKey: Option[String] = None
  @volatile var llm: Option[ScriptedAnswerLlm] = None
  def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient] = {
    builds.incrementAndGet(); receivedKey = Some(apiKey.value)
    val model = new ScriptedAnswerLlm(runtime); llm = Some(model); Right(model)
  }
  def voyage(
      apiKey: Secret,
      model: EmbeddingModel,
      purpose: EmbeddingPurpose
  ): Either[String, EmbeddingClient] = Left("scripted-no-embedding")
}

class LocalStackSpec extends AnyFunSuite {
  private val apiKey = "local-stack-test-api-key"
  private val canary = "CANARY-anthropic-key-7f3a91c2d8e04b55"
  private val auth = Map("Authorization" -> ("Bearer " + apiKey))
  private def env(extra: Map[String, String] = Map.empty): Map[String, String] = Map(
    LocalQueryStack.apiKeyHashVariable -> Auth.sha256(apiKey),
    LocalQueryStack.portVariable -> "0",
    "SCHOLARCHAIN_PROMPTS_DIR" -> AwsTestEnv.promptsDirectory.toString
  ) ++ extra
  private val quiet: String => Unit = _ => ()
  private val question = "Who are the direct coauthors of \"Ada Alpha\"?"

  private def start(
      stores: LocalExportStores,
      providers: ProviderClients,
      extra: Map[String, String] = Map.empty
  ): RunningLocalStack =
    LocalQueryStack
      .start(stores, env(extra), providers, quiet)
      .fold(code => fail("stack refused with exit " + code), identity)

  private def ask(
      stack: RunningLocalStack,
      q: String,
      key: String
  ): (Int, ujson.Value) = {
    val body = ujson.Obj("question" -> q).render()
    val (status, text) = Http.post(
      stack.port,
      "/v1/query",
      body,
      auth ++ Map("Idempotency-Key" -> key, "Content-Type" -> "application/json")
    )
    (status, ujson.read(text))
  }
  private def get(stack: RunningLocalStack, path: String): (Int, String) =
    Http.get(stack.port, path, auth)

  test("a query runs the real workflow on the loaded export and every claim is verified") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val providers = new ScriptedProviders
    val stack =
      start(fixture.stores(), providers, Map(LocalQueryStack.anthropicKeyVariable -> canary))
    try {
      assert(stack.llmConfigured && providers.receivedKey.contains(canary))
      val (status, body) = ask(stack, question, "local-1")
      assert(status == 200, body.render())
      val claims = body("claims").arr
      assert(claims.nonEmpty && claims.forall(_("verificationStatus").str == "VERIFIED"))
      val subjects = claims.flatMap(_("runtime")("subjectIds").arr.map(_.str)).toSet
      assert(subjects.contains(fixture.hub))
      val evidenceId = claims.head("evidenceIds")(0).str
      val (evidenceStatus, evidenceText) = get(stack, "/v1/evidence/" + evidenceId)
      assert(evidenceStatus == 200 && ujson.read(evidenceText)("evidenceId").str == evidenceId)
      val queryId = body("queryId").str
      val (explainStatus, explainText) = get(stack, "/v1/explain/" + queryId)
      assert(explainStatus == 200)
      val explain = ujson.read(explainText)
      assert(
        explain("outcome").str == "ANSWERED" && explain("verificationStatus").str == "VERIFIED"
      )
      val versions = explain("promptVersions").arr.map(_.str)
      assert(versions.contains("synthesis-v2") && !versions.contains("synthesis-v1"))
      assert(!explainText.contains("synthesis-v1"))
      val (queryEvidenceStatus, _) = get(stack, s"/v1/queries/$queryId/evidence")
      assert(queryEvidenceStatus == 200)
      // The model sees the graph mode the stack was started with: no semantic stage is planned.
      val sent = providers.llm.get.requests.asScala.toVector
      assert(sent.exists(_.toolName == "submit_answer"))
      val plan = ujson.read(sent.find(_.toolName == "submit_answer").get.userData)("plan")
      assert(plan.render().contains("\"graph\"") && stack.retrievalMode == "graph")
    } finally stack.close()
  }

  test("the workflow reads the graph through the graph role, never the local reader directly") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val stores = fixture.stores()
    val providers = new ScriptedProviders
    val stack =
      start(fixture.stores(), providers, Map(LocalQueryStack.anthropicKeyVariable -> canary))
    try {
      // Type level: the query ports carry no graph reader at all, so the workflow cannot hold one.
      assert(
        classOf[QueryPorts].getDeclaredFields.forall(f =>
          !classOf[DirectedGraphReader].isAssignableFrom(f.getType)
        )
      )
      // Only the graph ports hold the local reader.
      val factory = new LocalPortFactory(stores)
      val config =
        AwsTestEnv
          .parse("graph-service", AwsTestEnv.graph)
          .toOption
          .get
          .asInstanceOf[GraphRoleConfig]
      assert(factory.graph(config).toOption.get.reader eq stores.graphReader)
      // Behaviour: the graph role served internal graph requests for the query (they are the
      // unmatched-route 200s of the graph role; its health and readiness routes are labelled).
      def unmatched200(port: Int): Long = {
        val text = Http.get(port, "/metrics", auth)._2
        text.linesIterator
          .find(_.startsWith("api_route_requests_total{route=\"unmatched\",status=\"200\"}"))
          .map(_.split(' ').last.toLong)
          .getOrElse(0L)
      }
      val before = unmatched200(stack.graphPort)
      val (status, _) = ask(stack, question, "local-graph-role")
      assert(status == 200)
      assert(unmatched200(stack.graphPort) > before)
      // Graph retrieval launches no semantic query at all.
      assert(
        !Http
          .get(stack.semanticPort, "/metrics", auth)
          ._2
          .contains("/internal/v1/semantic/retrieve")
      )
    } finally stack.close()
  }

  test("the graph node route answers 200 for a present id and 404 for an absent one") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 1)
    val stack = start(fixture.stores(), new ScriptedProviders)
    try {
      assert(
        Http.get(stack.port, "/healthz")._1 == 200 && Http.get(stack.port, "/readyz")._1 == 200
      )
      val (found, text) = get(stack, "/v1/graph/nodes/" + fixture.hub)
      assert(found == 200 && text.contains(fixture.hub))
      assert(get(stack, "/v1/graph/nodes/" + fixture.absentResearcher)._1 == 404)
      assert(Http.get(stack.port, "/v1/graph/nodes/" + fixture.hub)._1 == 401)
    } finally stack.close()
  }

  test("without a model key the stack is ready and a query is refused explicitly without a call") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 1)
    val providers = new ScriptedProviders
    val stack = start(fixture.stores(), providers)
    try {
      assert(!stack.llmConfigured && Http.get(stack.port, "/readyz")._1 == 200)
      val (status, body) = ask(stack, question, "local-nokey")
      assert(status == 503 && body("error").str == "MODEL_NOT_CONFIGURED")
      assert(!body("retryable").bool && providers.builds.get == 0)
      assert(get(stack, "/v1/graph/nodes/" + fixture.hub)._1 == 200)
    } finally stack.close()
  }

  test("the semantic and worker ports are not served and the retrieval mode is configurable") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 1)
    val stores = fixture.stores()
    val factory = new LocalPortFactory(stores)
    val semanticConfig = AwsTestEnv
      .parse("semantic-service", AwsTestEnv.semantic)
      .toOption
      .get
      .asInstanceOf[SemanticRoleConfig]
    val semantic = factory.semantic(semanticConfig).toOption.get
    semantic.embedding.embed(Vector("anything")) match {
      case Seq(EmbeddingFailure(code, retryable, _, _)) =>
        assert(code == UnservedEmbeddingClient.code && !retryable)
      case other => fail("unexpected " + other)
    }
    assert(
      semantic.vectors.get(semanticConfig.index, Vector("k")) == StorageResult.Found(Vector.empty)
    )
    val workerConfig = AwsTestEnv.parse("embedding-worker", AwsTestEnv.worker).toOption.get
    assert(
      factory.worker(workerConfig.asInstanceOf[WorkerRoleConfig]) ==
        Left("local-stack-has-no-embedding-worker")
    )
    val bedrockQuery = AwsTestEnv
      .parse("query-api", AwsTestEnv.forRole("query-api"))
      .toOption
      .get
      .asInstanceOf[QueryRoleConfig]
    val runtime = AwsComposition.runtimeConfig(bedrockQuery).toOption.get
    assert(factory.query(bedrockQuery, runtime) == Left("local-stack-requires-anthropic-provider"))
    // The mode is a config value: graph by default for the local stack, fused when asked.
    val providers = new ScriptedProviders
    val fused = start(
      fixture.stores(),
      providers,
      Map(
        LocalQueryStack.anthropicKeyVariable -> canary,
        LocalQueryStack.retrievalModeVariable -> "fused"
      )
    )
    try {
      assert(fused.retrievalMode == "fused")
      val (status, _) = ask(fused, question, "local-fused")
      assert(status == 200 || status == 502)
      assert(
        Http.get(fused.semanticPort, "/metrics", auth)._2.contains("/internal/v1/semantic/retrieve")
      )
    } finally fused.close()
  }

  test(
    "the launcher refuses a non-loopback host, a missing key hash and bad values before loading"
  ) {
    val fixture = new LocalExportFixture(coauthors = 2, worksPerEdge = 1)
    val stores = fixture.stores()
    def refusal(e: Map[String, String]): (Either[Int, RunningLocalStack], Vector[String]) = {
      val errors = Vector.newBuilder[String]
      (LocalQueryStack.start(stores, e, new ScriptedProviders, errors += _), errors.result())
    }
    // `::1` and `localhost` are refused too: the peer URIs and readiness probe are IPv4 loopback.
    for (host <- Seq("0.0.0.0", "192.168.1.5", "example.com", "", "::1", "localhost", "[::1]"))
      assert(
        refusal(env(Map(LocalQueryStack.hostVariable -> host))) ==
          (Left(2), Vector("non-loopback-host-refused:" + LocalQueryStack.hostVariable))
      )
    val noHash = env() - LocalQueryStack.apiKeyHashVariable
    assert(
      refusal(noHash) ==
        (Left(2), Vector("missing-or-invalid-configuration:" + LocalQueryStack.apiKeyHashVariable))
    )
    assert(refusal(env(Map(LocalQueryStack.apiKeyHashVariable -> "abc")))._1 == Left(2))
    assert(refusal(env(Map(LocalQueryStack.anthropicKeyVariable -> "short")))._1 == Left(2))
    // The hash of the empty string (a failed no-echo read) is refused, as is a blank key variable.
    assert(
      LocalQueryStack.preflight(env(Map(LocalQueryStack.apiKeyHashVariable -> Auth.sha256("")))) ==
        Left("missing-or-invalid-configuration:" + LocalQueryStack.apiKeyHashVariable)
    )
    assert(
      LocalQueryStack.preflight(env(Map(LocalQueryStack.anthropicKeyVariable -> ""))) ==
        Left("invalid-configuration:" + LocalQueryStack.anthropicKeyVariable)
    )
    assert(
      LocalQueryStack.preflight(env(Map(LocalQueryStack.anthropicKeyVariable -> "   "))).isLeft
    )
    assert(refusal(env(Map(LocalQueryStack.portVariable -> "70000")))._1 == Left(2))
    assert(
      LocalQueryStack.preflight(env(Map(LocalQueryStack.hostVariable -> "127.0.0.1"))).isRight
    )
    // The main refuses before it reads the export: no export-refused code, exit 2.
    val errors = Vector.newBuilder[String]
    val bad = LocalQueryStackMain.run(
      Seq("--export-dir", "/nonexistent-local-export"),
      env(Map(LocalQueryStack.hostVariable -> "0.0.0.0")),
      quiet,
      errors += _
    )
    assert(
      bad.isLeft && bad.left.toOption.contains(2) && !errors.result().exists(_.contains("export"))
    )
    val none = LocalQueryStackMain.run(Seq.empty, env(), quiet, _ => ())
    assert(none.left.toOption.contains(2))
    val unknown = LocalQueryStackMain.run(Seq("--nope"), env(), quiet, _ => ())
    assert(unknown.left.toOption.contains(2))
    val missing = Vector.newBuilder[String]
    val refused = LocalQueryStackMain.run(
      Seq("--export-dir", "/nonexistent-local-export"),
      env(),
      quiet,
      missing += _
    )
    assert(refused.left.toOption.contains(3))
    assert(
      missing.result() == Vector("local-export-refused:export-directory-missing:export-directory")
    )
    val list = Files.createTempFile("include", ".txt")
    try {
      val dir = Files.createTempDirectory("export")
      Files.writeString(list, "not-an-id\n")
      val badList = Vector.newBuilder[String]
      val result = LocalQueryStackMain.run(
        Seq("--export-dir", dir.toString, "--include-list", list.toString),
        env(),
        quiet,
        badList += _
      )
      assert(result.left.toOption.contains(3))
      assert(badList.result() == Vector("include-list-refused:include-list-invalid-id"))
      val unreadable = Vector.newBuilder[String]
      val r2 = LocalQueryStackMain.run(
        Seq("--export-dir", dir.toString, "--include-list", dir.resolve("absent.txt").toString),
        env(),
        quiet,
        unreadable += _
      )
      assert(r2.left.toOption.contains(3))
      assert(unreadable.result() == Vector("include-list-refused:include-list-unreadable"))
      Files.delete(dir)
    } finally Files.deleteIfExists(list)
  }

  test("the ready line names the port and the export provenance for an include-ids artifact") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val list = IncludeList.parse((fixture.hub + "\n").getBytes("UTF-8")).toOption.get
    val stores = fixture.stores(RuntimeArtifactScope.IncludeIds(list))
    assert(stores.provenance.artifactScope == "include-ids:" + list.normalizedSha256)
    val providers = new ScriptedProviders
    val stack = start(stores, providers, Map(LocalQueryStack.anthropicKeyVariable -> canary))
    try {
      val line = LocalQueryStackMain.readyLine(stores, stack)
      assert(line.startsWith("local-query-stack ready port=" + stack.port + " "))
      assert(line.contains("runId=" + fixture.runId))
      assert(line.contains("artifactScope=include-ids:" + list.normalizedSha256))
      assert(line.contains("artifactPointerSha256=" + stores.artifactPointer.sha256))
      assert(line.contains("retrieval=graph") && line.contains("llm=anthropic"))
      assert(
        !line.contains(canary) && !line.contains(apiKey) && !line.contains(Auth.sha256(apiKey))
      )
      // The bounded artifact answers the same direct-coauthor question with verified claims.
      val (status, body) = ask(stack, question, "local-include")
      assert(status == 200 && body("claims").arr.forall(_("verificationStatus").str == "VERIFIED"))
    } finally stack.close()
  }

  test("the model key never reaches output, logs, responses, metrics or the audit store") {
    val fixture = new LocalExportFixture(coauthors = 3, worksPerEdge = 2)
    val out = new ByteArrayOutputStream
    val err = new ByteArrayOutputStream
    val savedOut = System.out
    val savedErr = System.err
    val root = org.slf4j.LoggerFactory
      .getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)
      .asInstanceOf[LogbackLogger]
    val events = new ListAppender[ILoggingEvent]
    events.start(); root.addAppender(events)
    System.setOut(new PrintStream(out, true)); System.setErr(new PrintStream(err, true))
    var seen = Vector.empty[String]
    var audit = ""
    try {
      val scripted = new ScriptedProviders
      val stores = fixture.stores()
      val stack = LocalQueryStack
        .start(
          stores,
          env(Map(LocalQueryStack.anthropicKeyVariable -> canary)),
          scripted,
          s => System.err.println(s)
        )
        .toOption
        .get
      try {
        val (status, body) = ask(stack, question, "local-canary")
        assert(status == 200)
        val queryId = body("queryId").str
        seen ++= Vector(
          body.render(),
          get(stack, "/v1/explain/" + queryId)._2,
          get(stack, "/v1/graph/nodes/" + fixture.hub)._2,
          get(stack, "/metrics")._2,
          Http.get(stack.graphPort, "/metrics", auth)._2,
          Http.get(stack.semanticPort, "/metrics", auth)._2,
          LocalQueryStackMain.readyLine(stores, stack)
        )
        audit = StorageResult.value(stack.factory.audits.get(queryId)).toString
        assert(audit.contains(queryId))
        // The queried requests the scripted model saw never contain the key either.
        seen ++= scripted.llm.get.requests.asScala.toVector.map(r => r.userData + r.systemPrompt)
      } finally stack.close()
      // The real provider seam, built with the canary and never called: construction is silent.
      val real = LocalQueryStack
        .start(
          fixture.stores(),
          env(Map(LocalQueryStack.anthropicKeyVariable -> canary)),
          new RagProviderClients(),
          s => System.err.println(s)
        )
        .toOption
        .get
      real.close()
    } finally {
      System.setOut(savedOut); System.setErr(savedErr); root.detachAppender(events)
    }
    val logged = events.list.asScala.toVector.map(e => e.getFormattedMessage + e.getLoggerName)
    val all = seen ++ logged ++ Vector(out.toString, err.toString, audit)
    assert(all.forall(!_.contains(canary)), "the canary key appeared in an observable output")
    assert(all.forall(!_.contains(apiKey)))
  }

  test("preflight validates the retrieval mode, deadlines and the region pin before any load") {
    val mode = LocalQueryStack.retrievalModeVariable
    assert(
      LocalQueryStack.preflight(env()).toOption.get.runtime.retrievalMode == RetrievalMode.Graph
    )
    assert(
      LocalQueryStack.preflight(env(Map(mode -> "fused"))).toOption.get.runtime.retrievalMode ==
        RetrievalMode.Fused
    )
    for (bad <- Seq("vector", "nonsense"))
      assert(
        LocalQueryStack.preflight(env(Map(mode -> bad))) ==
          Left("invalid-aws-configuration:" + mode)
      )
    val planner = "SCHOLARCHAIN_RUNTIME_PLANNER_DEADLINE_MS"
    assert(
      LocalQueryStack.preflight(env(Map(planner -> "0"))) ==
        Left("invalid-aws-configuration:" + planner)
    )
    // A raised planner or synthesis deadline without the runtime synchronous budget is refused.
    assert(
      LocalQueryStack.preflight(
        env(Map(planner -> "15000", "SCHOLARCHAIN_RUNTIME_SYNTHESIS_DEADLINE_MS" -> "30000"))
      ) ==
        Left("runtime-config-invalid")
    )
    assert(LocalQueryStack.preflight(env(Map("SCHOLARCHAIN_MAX_RESULT_BYTES" -> "x"))).isLeft)
    // The raised profile is accepted and reported as it will run.
    val raised = env(
      Map(
        planner -> "15000",
        "SCHOLARCHAIN_RUNTIME_SYNTHESIS_DEADLINE_MS" -> "30000",
        "SCHOLARCHAIN_RUNTIME_SYNCHRONOUS_DEADLINE_MS" -> "60000",
        "SCHOLARCHAIN_SYNCHRONOUS_DEADLINE_MS" -> "70000",
        "SCHOLARCHAIN_WORKFLOW_TIMEOUT_MS" -> "70000"
      )
    )
    assert(
      LocalQueryStack.preflight(raised).toOption.get.deadlines ==
        "planner:15000,synthesis:30000,runtimeSync:60000,serviceSync:70000,workflow:70000"
    )
    // A caller's region pin cannot break the local placeholder region.
    assert(
      LocalQueryStack.preflight(env(Map("SCHOLARCHAIN_APPLICATION_REGION" -> "us-east-2"))).isRight
    )
    val stack = start(
      new LocalExportFixture(2, 1).stores(),
      new ScriptedProviders,
      Map("SCHOLARCHAIN_APPLICATION_REGION" -> "us-east-2")
    )
    try assert(Http.get(stack.port, "/readyz")._1 == 200)
    finally stack.close()
    // The ready line carries the effective deadlines and the (non-secret) model id.
    val stores = new LocalExportFixture(2, 1).stores()
    val ready = start(stores, new ScriptedProviders, raised)
    try {
      val line = LocalQueryStackMain.readyLine(stores, ready)
      assert(line.contains("model=" + ready.settings.modelId))
      assert(
        line.contains(
          "deadlinesMs=planner:15000,synthesis:30000,runtimeSync:60000,serviceSync:70000,workflow:70000"
        )
      )
    } finally ready.close()
  }

  test("the provider client is closed with the stack") {
    final class ClosingProviders extends ProviderClients {
      val closed = new AtomicInteger
      def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient] =
        Right(new ScriptedAnswerLlm(runtime) with AutoCloseable {
          def close(): Unit = closed.incrementAndGet()
        })
      def voyage(apiKey: Secret, model: EmbeddingModel, purpose: EmbeddingPurpose) =
        Left("unused")
    }
    val providers = new ClosingProviders
    val stack = start(
      new LocalExportFixture(2, 1).stores(),
      providers,
      Map(LocalQueryStack.anthropicKeyVariable -> canary)
    )
    assert(providers.closed.get == 0)
    stack.close()
    assert(providers.closed.get == 1)
  }

  test("the local stack classes reference no AWS SDK service client") {
    val names = Seq(
      "LocalPortFactory",
      "LocalPortFactory$",
      "MissingKeyLlm$",
      "UnservedEmbeddingClient",
      "LocalQueryStack$",
      "LocalQueryStack",
      "RunningLocalStack",
      "LocalQueryStackMain$",
      "LocalQueryStackMain"
    )
    val base = "/edu/uic/cs441/scholarchain/services/"
    val found = names.flatMap { n =>
      Option(getClass.getResourceAsStream(base + n + ".class")).map { in =>
        try (n, new String(in.readAllBytes(), "ISO-8859-1"))
        finally in.close()
      }
    }
    assert(found.size >= 5, "the class files were located")
    assert(found.forall((_, text) => !text.contains("software/amazon/awssdk")))
    assert(found.forall((_, text) => !text.contains("AwsSdkPortFactory")))
  }

  test("a 25-row direct-coauthor answer: observed size and outcome against the 131072-byte bound") {
    // Measurement through the real workflow with the scripted model, not a tuned pass. Each row is
    // one export: a hub with 25 coauthors and `works` joint works per edge.
    val rows = Seq(1, 2, 3, 4, 5, 6, 7, 8, 12, 18, 19, 20, 40).map { works =>
      val fixture = new LocalExportFixture(coauthors = 25, worksPerEdge = works)
      val stack = start(
        fixture.stores(),
        new ScriptedProviders,
        Map(LocalQueryStack.anthropicKeyVariable -> canary)
      )
      try {
        val (status, body) = ask(stack, question, "local-size-" + works)
        val size = body.render().getBytes("UTF-8").length
        val claims = if (status == 200) body("claims").arr.size else -1
        val summary =
          if (status == 200) body("answer")("summary").str.take(40) else body("error").str
        val reason =
          if (claims == 0)
            " reason=" + ujson
              .read(get(stack, "/v1/explain/" + body("queryId").str)._2)("reason")
              .render()
          else ""
        info(s"works=$works status=$status claims=$claims bytes=$size summary=$summary$reason")
        (works, status, claims, size)
      } finally stack.close()
    }
    // The bound is never exceeded by a returned answer, and no size here reached the 502.
    assert(rows.forall((_, status, _, size) => status != 200 || size <= 131072))
    // One claim per coauthor edge plus the hub's own (26) until the evidence no longer fits the
    // context budget, after which the workflow abstains before synthesis (a small 200 body).
    assert(rows.head._3 == 26 && rows.exists(_._3 == 0))
  }

  test("RESULT_TOO_LARGE is returned after the model was called when the bound is exceeded") {
    val fixture = new LocalExportFixture(coauthors = 25, worksPerEdge = 1)
    val providers = new ScriptedProviders
    // The same 25-row answer is about 70 KB; a 40,000-byte bound must refuse it whole.
    val stack = start(
      fixture.stores(),
      providers,
      Map(
        LocalQueryStack.anthropicKeyVariable -> canary,
        "SCHOLARCHAIN_MAX_RESULT_BYTES" -> "40000"
      )
    )
    try {
      val (status, body) = ask(stack, question, "local-too-large")
      assert(status == 502 && body("error").str == "RESULT_TOO_LARGE" && !body("retryable").bool)
      val sent = providers.llm.get.requests.asScala.map(_.toolName).toVector
      assert(sent.contains("submit_answer"), "the synthesis call was made before the refusal")
    } finally stack.close()
  }
}
