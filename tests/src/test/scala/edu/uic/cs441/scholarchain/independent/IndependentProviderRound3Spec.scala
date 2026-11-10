package edu.uic.cs441.scholarchain.independent

import com.sun.net.httpserver.HttpServer
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import org.scalatest.funsuite.AnyFunSuite
import java.net.{InetAddress, InetSocketAddress}
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.concurrent.{ConcurrentLinkedQueue, Executors}
import scala.jdk.CollectionConverters.*

/** Repair round 3 (Anthropic API for synthesis, Voyage AI for embeddings), written independently by
  * the test-engineer from the work order contract in docs/agent-runs/phase-14/prompt.md, through
  * the public API of modules/rag only. Fake HTTP only: every request goes to an in-process server
  * on 127.0.0.1; the keys are sentinels; no network host, AWS or provider is contacted.
  *
  * Hand-derived expectations: max_tokens = ceil(2048 x 1.3) = 2663 (2048 x 1.3 = 2662.4); the
  * embedding cap USD 0.30 at USD 0.02 per 1M tokens is 0.30 / 0.02 x 1,000,000 = 15,000,000 tokens;
  * 2,500 texts go out as requests of 1,000, 1,000 and 500.
  */
class IndependentProviderRound3Spec extends AnyFunSuite {
  // Sentinels are built from pieces so that no key-shaped literal exists in the repository.
  private val anthropicSentinel = "sk-" + "ant-" + "SENTINEL" + "x9Qz" * 8
  private val voyageSentinel = "pa-" + "SENTINEL" + "k7Lm" * 10

  private val root: Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .find(p => Files.isDirectory(p.resolve("prompts/runtime")))
    .get
  private val baseConfig: RuntimeConfig = RuntimeConfigLoader
    .load(root.resolve("modules/core/src/main/resources/scholarchain.runtime-config.v1.json"))
    .toOption
    .get
  private def configWith(temperature: Double): RuntimeConfig =
    baseConfig.copy(model =
      baseConfig.model.copy(
        modelId = "claude-haiku-5-5",
        modelVersion = "synthetic-v1",
        temperature = temperature
      )
    )
  private val config = configWith(0.0)

  private final case class Seen(
      method: String,
      path: String,
      headers: Map[String, String],
      body: String
  ) {
    def json: ujson.Obj = ujson.read(body).obj
  }
  private final case class Reply(status: Int, body: String)
  private final class Stub(respond: Seen => Reply) {
    private val server =
      HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress, 0), 0)
    private val log = new ConcurrentLinkedQueue[Seen]()
    server.setExecutor(Executors.newCachedThreadPool())
    server.createContext(
      "/",
      exchange =>
        try {
          val headers = exchange.getRequestHeaders.entrySet.asScala
            .map(e => e.getKey.toLowerCase -> e.getValue.get(0))
            .toMap
          val seen = Seen(
            exchange.getRequestMethod,
            exchange.getRequestURI.toString,
            headers,
            new String(exchange.getRequestBody.readAllBytes(), UTF_8)
          )
          log.add(seen)
          val reply = respond(seen)
          exchange.getResponseHeaders.add("content-type", "application/json")
          val bytes = reply.body.getBytes(UTF_8)
          exchange.sendResponseHeaders(
            reply.status,
            if (bytes.isEmpty) -1L else bytes.length.toLong
          )
          if (bytes.nonEmpty) exchange.getResponseBody.write(bytes)
        } catch { case _: java.io.IOException => () }
        finally exchange.close()
    )
    server.start()
    val baseUri: String = s"http://127.0.0.1:${server.getAddress.getPort}"
    def seen: Vector[Seen] = log.asScala.toVector
    def stop(): Unit = server.stop(0)
  }
  private def withStub[A](respond: Seen => Reply)(f: Stub => A): A = {
    val stub = new Stub(respond)
    try f(stub)
    finally stub.stop()
  }

  // ---------------------------------------------------------------- Anthropic Messages API
  private val toolName = "submit_plan"
  private val schemaJson =
    """{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:fixture","title":"Plan","type":"object",
      |"properties":{"a":{"type":"string"}},"required":["a"],"additionalProperties":false}""".stripMargin
  private def request = StructuredLlmRequest(
    toolName,
    "system fixture",
    """{"q":"fixture"}""",
    schemaJson,
    "planner-v1",
    "plan.v1",
    5000L
  )
  private def toolUse(name: String = toolName) = ujson.Obj(
    "type" -> "tool_use",
    "id" -> "toolu_1",
    "name" -> name,
    "input" -> ujson.Obj("a" -> "b")
  )
  private def message(
      blocks: Seq[ujson.Value] = Seq(toolUse()),
      stop: String = "tool_use",
      model: String = "claude-haiku-5-5"
  ): String =
    ujson
      .Obj(
        "id" -> "msg_1",
        "type" -> "message",
        "role" -> "assistant",
        "model" -> model,
        "content" -> ujson.Arr.from(blocks),
        "stop_reason" -> stop,
        "usage" -> ujson.Obj("input_tokens" -> 12, "output_tokens" -> 7)
      )
      .render()
  private def anthropic(stub: Stub, c: RuntimeConfig = config) =
    new AnthropicMessagesLlmClient(
      AnthropicApiKey.fromValue(anthropicSentinel).toOption.get,
      c,
      AnthropicSettings(baseUri = stub.baseUri)
    )

  test(
    "the request never carries temperature, top_p, top_k, strict or a prefill, even when the runtime config says so"
  ) {
    for (temperature <- Seq(0.0, 0.7)) {
      withStub(_ => Reply(200, message())) { stub =>
        assert(
          anthropic(stub, configWith(temperature)).complete(request).isInstanceOf[LlmResult.Output],
          s"temperature $temperature"
        )
        val body = stub.seen.head.json
        for (
          forbidden <- Seq(
            "temperature",
            "top_p",
            "top_k",
            "strict",
            "prefill",
            "stop_sequences",
            "thinking"
          )
        )
          assert(!body.value.contains(forbidden), s"$forbidden at temperature $temperature")
        val messages = body("messages").arr
        assert(
          messages.size == 1 && messages.head("role").str == "user",
          "no assistant prefill: a single user message"
        )
        assert(
          !stub.seen.head.body.contains("\"strict\""),
          "strict appears nowhere, not even inside the tool"
        )
      }
    }
  }

  test(
    "the tool is forced by name, the schema loses $schema, $id and title, and max_tokens is ceil(2048 x 1.3) = 2663"
  ) {
    withStub(_ => Reply(200, message())) { stub =>
      anthropic(stub).complete(request)
      val seen = stub.seen
      assert(seen.size == 1)
      val body = seen.head.json
      assert(body("tool_choice") == ujson.Obj("type" -> "tool", "name" -> toolName))
      assert(body("tools").arr.size == 1 && body("tools")(0)("name").str == toolName)
      val inputSchema = body("tools")(0)("input_schema").obj
      for (removed <- Seq("$schema", "$id", "title"))
        assert(!inputSchema.value.contains(removed), removed)
      assert(inputSchema("type").str == "object" && inputSchema("required") == ujson.Arr("a"))
      assert(baseConfig.maxOutputTokens == 2048)
      assert(body("max_tokens").num == 2663.0)
      assert(body("model").str == "claude-haiku-5-5")
    }
  }

  test(
    "the key travels only in the x-api-key header of a POST to /v1/messages, never in the body or the URL"
  ) {
    withStub(_ => Reply(200, message())) { stub =>
      anthropic(stub).complete(request)
      val seen = stub.seen.head
      assert(seen.method == "POST" && seen.path == "/v1/messages")
      assert(seen.headers("x-api-key") == anthropicSentinel)
      assert(seen.headers("anthropic-version") == "2023-06-01")
      assert(!seen.body.contains(anthropicSentinel) && !seen.path.contains(anthropicSentinel))
      assert(!seen.headers.contains("authorization"))
    }
  }

  test(
    "stop_reason refusal is a typed failure that is not retried, even when a tool_use block is present"
  ) {
    withStub(_ => Reply(200, message(stop = "refusal"))) { stub =>
      assert(anthropic(stub).complete(request) == LlmResult.Failure("llm-refusal"))
      assert(stub.seen.size == 1, "no retry on a refusal")
    }
    withStub(_ =>
      Reply(
        200,
        message(blocks = Seq(ujson.Obj("type" -> "text", "text" -> "no")), stop = "refusal")
      )
    ) { stub =>
      assert(anthropic(stub).complete(request) == LlmResult.Failure("llm-refusal"))
      assert(stub.seen.size == 1)
    }
  }

  test("provider errors are closed codes and are not retried") {
    for (status <- Seq(400, 401, 429, 500, 529)) {
      withStub(_ => Reply(status, "{}")) { stub =>
        assert(
          anthropic(stub).complete(request) == LlmResult.Failure("llm-provider-rejected"),
          s"status $status"
        )
        assert(stub.seen.size == 1, s"no retry for $status")
      }
    }
  }

  test(
    "content blocks are read by type: thinking and text before the tool_use block do not hide it, text alone is not an answer"
  ) {
    val blocks = Seq(
      ujson.Obj("type" -> "thinking", "thinking" -> "t", "signature" -> "s"),
      ujson.Obj("type" -> "text", "text" -> "hello"),
      toolUse()
    )
    withStub(_ => Reply(200, message(blocks = blocks))) { stub =>
      anthropic(stub).complete(request) match {
        case LlmResult.Output(json, usage, modelId, _) =>
          assert(ujson.read(json) == ujson.Obj("a" -> "b"))
          assert(usage == LlmUsage(Some(12L), Some(7L)))
          assert(modelId == "claude-haiku-5-5")
        case other => fail(s"expected output, got $other")
      }
    }
    withStub(_ =>
      Reply(200, message(blocks = Seq(ujson.Obj("type" -> "text", "text" -> "no tool"))))
    ) { stub =>
      assert(anthropic(stub).complete(request).isInstanceOf[LlmResult.Failure])
    }
    withStub(_ => Reply(200, message(blocks = Seq(toolUse("other_tool"))))) { stub =>
      assert(
        anthropic(stub).complete(request).isInstanceOf[LlmResult.Failure],
        "a tool other than the forced one is refused"
      )
    }
    withStub(_ => Reply(200, message(model = "some-other-model"))) { stub =>
      assert(anthropic(stub).complete(request) == LlmResult.Failure("llm-model-mismatch"))
    }
  }

  test("a key echoed back by the provider in an error or success body never reaches a result") {
    val echo: Seen => Reply =
      seen => Reply(401, s"""{"error":"bad key ${seen.headers("x-api-key")}"}""")
    withStub(echo) { stub =>
      val result = anthropic(stub).complete(request)
      assert(result.isInstanceOf[LlmResult.Failure])
      assert(!result.toString.contains("SENTINEL"))
    }
  }

  test(
    "an Anthropic key and a plain-http remote endpoint are refused with closed codes that echo nothing"
  ) {
    val key = AnthropicApiKey.fromValue(anthropicSentinel).toOption.get
    assert(!key.toString.contains("SENTINEL") && key.toString == "AnthropicApiKey(REDACTED)")
    assert(
      AnthropicApiKey.fromValue(anthropicSentinel).toOption.get != key,
      "equality is by identity, so a key cannot be probed by comparison"
    )
    for (
      bad <- Seq("", "has space " + anthropicSentinel, "line\n" + anthropicSentinel, "x" * 513)
    ) {
      val result = AnthropicApiKey.fromValue(bad)
      assert(result == Left("invalid-anthropic-api-key"), "closed code")
      assert(!result.toString.contains("SENTINEL"))
    }
    val remote = SynthesisClients.create(
      SynthesisProvider.Anthropic,
      config,
      Some(anthropicSentinel),
      () => fail("Bedrock must not be touched"),
      AnthropicSettings(baseUri = "http://example.invalid")
    )
    assert(remote == Left("invalid-anthropic-base-uri"))
    val missing = SynthesisClients.create(
      SynthesisProvider.Anthropic,
      config,
      None,
      () => fail("Bedrock must not be touched")
    )
    assert(missing == Left("anthropic-api-key-missing"))
    val created = SynthesisClients.create(
      SynthesisProvider.Anthropic,
      config,
      Some(anthropicSentinel),
      () => fail("Bedrock must not be touched")
    )
    assert(created.isRight && !created.toString.contains("SENTINEL"))
  }

  test(
    "the provider switches default to anthropic and voyage, accept bedrock, and refuse anything else without echoing it"
  ) {
    assert(SynthesisProvider.parse(None) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some("  ")) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some("bedrock")) == Right(SynthesisProvider.Bedrock))
    assert(EmbeddingProvider.parse(None) == Right(EmbeddingProvider.Voyage))
    assert(EmbeddingProvider.parse(Some("bedrock")) == Right(EmbeddingProvider.Bedrock))
    assert(
      SynthesisProvider.parse(Some("openai-" + anthropicSentinel)) == Left(
        "invalid-synthesis-provider"
      )
    )
    assert(
      EmbeddingProvider.parse(Some("voyage ")) == Right(EmbeddingProvider.Voyage),
      "surrounding blanks are trimmed"
    )
    assert(
      EmbeddingProvider.parse(Some("cohere-" + voyageSentinel)) == Left(
        "invalid-embedding-provider"
      )
    )
    assert(
      SynthesisProvider.EnvName == "SCHOLARCHAIN_SYNTHESIS_PROVIDER" && EmbeddingProvider.EnvName == "SCHOLARCHAIN_EMBEDDING_PROVIDER"
    )
    assert(
      SynthesisClients.AnthropicKeyEnvName == "SCHOLARCHAIN_ANTHROPIC_API_KEY" && EmbeddingClientFactory.VoyageKeyEnvName == "SCHOLARCHAIN_VOYAGE_API_KEY"
    )
  }

  // ---------------------------------------------------------------- Voyage embeddings
  private val dim = 256
  private def vectors(
      count: Int,
      size: Int = dim,
      tokens: Long = 10,
      model: String = "voyage-4-lite"
  ): String = {
    val rows = (0 until count).map(i =>
      ujson.Obj(
        "object" -> "embedding",
        "index" -> i,
        "embedding" -> ujson.Arr.from((0 until size).map(_ => ujson.Num(0.25)))
      )
    )
    ujson
      .Obj(
        "object" -> "list",
        "data" -> ujson.Arr.from(rows),
        "model" -> model,
        "usage" -> ujson.Obj("total_tokens" -> ujson.Num(tokens.toDouble))
      )
      .render()
  }
  private def inputsOf(seen: Seen): Int = seen.json("input").arr.size
  private def voyage(
      stub: Stub,
      inputType: EmbeddingInputType,
      counter: EmbeddingSpendCounter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage)
  ) =
    new VoyageEmbeddingClient(
      VoyageApiKey.fromValue(voyageSentinel).toOption.get,
      VoyageEmbeddingConfig(inputType, baseUri = stub.baseUri),
      counter
    )

  test(
    "voyage-4-lite requests carry model, output_dimension 256 and input_type document for ingest and query for queries"
  ) {
    for (
      (inputType, wire) <- Seq(
        EmbeddingInputType.Document -> "document",
        EmbeddingInputType.Query -> "query"
      )
    ) {
      withStub(seen => Reply(200, vectors(inputsOf(seen)))) { stub =>
        val client = voyage(stub, inputType)
        assert(client.model == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
        assert(client.provider == EmbeddingProvider.Voyage)
        val results = client.embed(Seq("alpha", "beta"))
        assert(results.forall {
          case s: EmbeddingSuccess => s.values.size == 256 && s.model == client.model;
          case _                   => false
        })
        val seen = stub.seen.head
        assert(seen.path == "/v1/embeddings" && seen.method == "POST")
        assert(seen.headers("authorization") == "Bearer " + voyageSentinel)
        assert(!seen.body.contains(voyageSentinel))
        val body = seen.json
        assert(
          body("model").str == "voyage-4-lite" && body("output_dimension").num == 256.0 && body(
            "input_type"
          ).str == wire
        )
        assert(body("input").arr.map(_.str) == Seq("alpha", "beta"))
      }
    }
  }

  test("at most 1,000 texts go in one request: 2,500 texts are sent as 1,000 + 1,000 + 500") {
    withStub(seen => Reply(200, vectors(inputsOf(seen), tokens = 1))) { stub =>
      val client = voyage(stub, EmbeddingInputType.Document)
      val results = client.embed((0 until 2500).map(i => s"text $i"))
      assert(results.size == 2500 && results.forall(_.isInstanceOf[EmbeddingSuccess]))
      assert(stub.seen.map(inputsOf) == Vector(1000, 1000, 500))
    }
  }

  test(
    "the embedding cap is 0.30 / 0.02 x 1,000,000 = 15,000,000 tokens, and a request past the cap is refused before it is sent"
  ) {
    val counter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage)
    assert(
      counter.capUsd == BigDecimal("0.30") && counter.usdPerMillionTokens == BigDecimal("0.02")
    )
    assert(counter.capTokens == BigInt(15000000))
    val tiny =
      new EmbeddingSpendCounter(
        BigDecimal("0.000001"),
        BigDecimal("0.02")
      ) // 0.000001 / 0.02 x 1e6 = 50 tokens
    assert(tiny.capTokens == BigInt(50))
    withStub(seen => Reply(200, vectors(inputsOf(seen)))) { stub =>
      val results = voyage(stub, EmbeddingInputType.Document, tiny).embed(Seq("x" * 200))
      assert(results.head match {
        case EmbeddingFailure(code, _, _, _) => code == "embedding-token-cap"; case _ => false
      })
      assert(stub.seen.isEmpty, "nothing is sent once the cap would be passed")
    }
  }

  test(
    "a response whose vectors have the wrong dimension or model is a failure, never a stored vector"
  ) {
    withStub(seen => Reply(200, vectors(inputsOf(seen), size = 1024))) { stub =>
      val results = voyage(stub, EmbeddingInputType.Query).embed(Seq("alpha"))
      assert(results.forall(_.isInstanceOf[EmbeddingFailure]))
    }
    withStub(seen => Reply(200, vectors(inputsOf(seen), model = "voyage-3-large"))) { stub =>
      assert(
        voyage(stub, EmbeddingInputType.Query)
          .embed(Seq("alpha"))
          .forall(_.isInstanceOf[EmbeddingFailure])
      )
    }
  }

  test(
    "a key echoed back in a Voyage error body never reaches a result, and a Voyage key renders redacted"
  ) {
    withStub(seen => Reply(401, s"""{"detail":"bad key ${seen.headers("authorization")}"}""")) {
      stub =>
        val results = voyage(stub, EmbeddingInputType.Query).embed(Seq("alpha"))
        assert(results.forall(_.isInstanceOf[EmbeddingFailure]))
        assert(!results.toString.contains("SENTINEL"))
    }
    val key = VoyageApiKey.fromValue(voyageSentinel).toOption.get
    assert(key.toString == "VoyageApiKey(REDACTED)" && !key.toString.contains("SENTINEL"))
    for (bad <- Seq("", "has space", "line\nbreak", "y" * 513))
      assert(VoyageApiKey.fromValue(bad).isLeft, s"refused: ${bad.length} chars")
    assert(
      !VoyageApiKey.fromValue("has space " + voyageSentinel).toString.contains("SENTINEL"),
      "no echo of the refused value"
    )
    val missing = EmbeddingClientFactory.create(
      EmbeddingProvider.Voyage,
      EmbeddingInputType.Query,
      None,
      () => fail("Bedrock must not be touched"),
      None
    )
    assert(missing.left.toOption.contains("voyage-api-key-missing"))
  }

  // ---------------------------------------------------------------- stored versus query vector identity
  private val voyageModel = EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256)
  private val titanModel = EmbeddingModel("amazon.titan-embed-text-v2:0", "v2", 256)

  test(
    "stored and query vectors must share provider, model, version and dimension; every mismatch is refused with a typed code"
  ) {
    val V = EmbeddingProvider.Voyage
    val B = EmbeddingProvider.Bedrock
    assert(VectorConsistency.check(V, voyageModel, V, voyageModel) == Right(()))
    assert(VectorConsistency.check(B, titanModel, B, titanModel) == Right(()))
    assert(
      VectorConsistency.check(B, titanModel, V, voyageModel) == Left(
        VectorConsistencyError("provider")
      )
    )
    assert(
      VectorConsistency.check(V, voyageModel, B, titanModel) == Left(
        VectorConsistencyError("provider")
      )
    )
    assert(
      VectorConsistency.check(V, voyageModel, V, voyageModel.copy(modelId = "voyage-4")) == Left(
        VectorConsistencyError("model")
      )
    )
    assert(
      VectorConsistency.check(
        V,
        voyageModel,
        V,
        voyageModel.copy(version = "voyage-4-lite-2")
      ) == Left(VectorConsistencyError("version"))
    )
    assert(
      VectorConsistency.check(V, voyageModel, V, voyageModel.copy(dimension = 512)) == Left(
        VectorConsistencyError("dimension")
      )
    )
    assert(VectorConsistencyError("dimension").code == "vector-consistency-dimension-mismatch")
    assert(
      !VectorConsistencyError("provider").code.contains("voyage"),
      "the code names the field, never a value"
    )
  }

  test(
    "a live Voyage query embedder against vectors stored by Titan is refused, and the same embedder against Voyage vectors passes"
  ) {
    withStub(seen => Reply(200, vectors(inputsOf(seen)))) { stub =>
      val client = voyage(stub, EmbeddingInputType.Query)
      assert(
        VectorConsistency.checkClient(EmbeddingProvider.Bedrock, titanModel, client) == Left(
          VectorConsistencyError("provider")
        )
      )
      assert(
        VectorConsistency.checkClient(EmbeddingProvider.Voyage, voyageModel, client) == Right(())
      )
      assert(
        VectorConsistency.checkClient(
          EmbeddingProvider.Voyage,
          voyageModel.copy(dimension = 1024),
          client
        ) == Left(VectorConsistencyError("dimension"))
      )
      assert(stub.seen.isEmpty, "the identity check is local: it makes no call")
    }
  }

  test(
    "a model belongs to its provider by name: a voyage model on the bedrock path and a titan model on the voyage path are refused"
  ) {
    assert(EmbeddingProviders.infer(voyageModel) == EmbeddingProvider.Voyage)
    assert(EmbeddingProviders.infer(titanModel) == EmbeddingProvider.Bedrock)
    assert(!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Bedrock, voyageModel))
    assert(!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Voyage, titanModel))
  }

  test(
    "a Bedrock embedding config that names a Voyage model is refused before any Bedrock client is built"
  ) {
    val result = EmbeddingClientFactory.create(
      EmbeddingProvider.Bedrock,
      EmbeddingInputType.Document,
      None,
      () => fail("Bedrock must not be touched"),
      Some(BedrockEmbeddingConfig(model = voyageModel, region = "us-east-2"))
    )
    assert(result.left.toOption.contains("embedding-provider-model-mismatch"))
  }
}
