package edu.uic.cs441.scholarchain.rag

import com.sun.net.httpserver.HttpServer
import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.io.{ByteArrayOutputStream, PrintStream}
import java.net.{InetAddress, InetSocketAddress}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{ConcurrentLinkedQueue, Executors}
import scala.jdk.CollectionConverters.*

/** Loopback-only tests: every request goes to an in-process server bound to 127.0.0.1. The key is a
  * synthetic placeholder and no provider or network host is contacted.
  */
class AnthropicLlmSpec extends AnyFunSuite {
  private def resource(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    try new String(stream.readAllBytes(), UTF_8)
    finally stream.close()
  }
  private val baseConfig =
    RuntimeConfigLoader.fromJson(resource("/scholarchain.runtime-config.v1.json")).toOption.get
  private val config =
    baseConfig.copy(model =
      baseConfig.model.copy(
        modelId = AnthropicMessagesLlmClient.ModelId,
        modelVersion = "synthetic-v1",
        temperature = 0.0
      )
    )
  private val secret = "sk-synthetic-placeholder-key-value"
  private val key = AnthropicApiKey.fromValue(secret).toOption.get
  private val toolName = "submit_query_plan"
  private val schemaJson =
    """{"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"fixture.id",
      |"title":"top level title","type":"object",
      |"properties":{"a":{"type":"string","title":"nested title"}},
      |"required":["a"],"additionalProperties":false}""".stripMargin
  private def request(timeout: Long = 5000L) = StructuredLlmRequest(
    toolName,
    "system prompt fixture",
    "{\"question\":\"fixture\"}",
    schemaJson,
    "planner-v1",
    "scholarchain.runtime.planner.v1",
    timeout
  )

  private final case class Seen(
      method: String,
      path: String,
      headers: Map[String, String],
      body: String
  )
  private final case class Reply(
      status: Int,
      body: String,
      delayMs: Long = 0,
      headers: Map[String, String] = Map.empty
  )
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
          if (reply.delayMs > 0) Thread.sleep(reply.delayMs)
          reply.headers.foreach((k, v) => exchange.getResponseHeaders.add(k, v))
          exchange.getResponseHeaders.add("content-type", "application/json")
          val bytes = reply.body.getBytes(UTF_8)
          exchange.sendResponseHeaders(
            reply.status,
            if (bytes.isEmpty) -1L else bytes.length.toLong
          )
          if (bytes.nonEmpty) exchange.getResponseBody.write(bytes)
        } catch { case _: java.io.IOException | _: InterruptedException => () }
        finally exchange.close()
    )
    server.start()
    val baseUri: String = s"http://127.0.0.1:${server.getAddress.getPort}"
    def seen: Vector[Seen] = log.asScala.toVector
    def stop(): Unit = server.stop(0)
  }
  private def withStub[A](reply: Reply)(f: Stub => A): A = withStub(_ => reply)(f)
  private def withStub[A](respond: Seen => Reply)(f: Stub => A): A = {
    val stub = new Stub(respond)
    try f(stub)
    finally stub.stop()
  }
  private def client(
      stub: Stub,
      c: RuntimeConfig = config,
      settings: AnthropicSettings = AnthropicSettings()
  ) = new AnthropicMessagesLlmClient(key, c, settings.copy(baseUri = stub.baseUri))
  private def at(uri: String) = AnthropicSettings(baseUri = uri)

  private def input = ujson.Obj("schemaVersion" -> "scholarchain.runtime.planner.v1", "n" -> 3)
  private def toolBlock(name: String = toolName, in: ujson.Value = input) =
    ujson.Obj("type" -> "tool_use", "id" -> "toolu_fixture", "name" -> name, "input" -> in)
  private def message(
      blocks: Vector[ujson.Value] = Vector(toolBlock()),
      stop: String = "tool_use",
      model: String = config.model.modelId
  ): ujson.Obj = ujson.Obj(
    "id" -> "msg_fixture",
    "type" -> "message",
    "role" -> "assistant",
    "model" -> model,
    "content" -> ujson.Arr.from(blocks),
    "stop_reason" -> stop,
    "usage" -> ujson.Obj("input_tokens" -> 12, "output_tokens" -> 15)
  )
  private def ok(m: ujson.Obj = message()) = Reply(200, m.render())
  private def codeOf(result: LlmResult): String = result match {
    case LlmResult.Failure(code) => code
    case other                   => fail(s"Expected failure, got $other")
  }

  test("request shape: URL, headers, body fields, forced tool, trimmed schema, no strict") {
    withStub(ok()) { stub =>
      val result = client(stub).complete(request())
      val seen = stub.seen
      assert(seen.size == 1)
      val call = seen.head
      assert(call.method == "POST" && call.path == "/v1/messages")
      assert(call.headers.get("x-api-key").contains(secret))
      assert(call.headers.get("anthropic-version").contains("2023-06-01"))
      assert(call.headers.get("content-type").contains("application/json"))
      val body = ujson.read(call.body)
      assert(body("model").str == config.model.modelId)
      assert(body("model").str == "claude-haiku-5-5")
      assert(body("max_tokens").num == math.ceil(config.maxOutputTokens * 1.3))
      assert(body("system").str == "system prompt fixture")
      assert(
        body("messages") == ujson.Arr(
          ujson.Obj("role" -> "user", "content" -> "{\"question\":\"fixture\"}")
        )
      )
      assert(body("tool_choice") == ujson.Obj("type" -> "tool", "name" -> toolName))
      assert(body("tools").arr.size == 1 && body("tools")(0)("name").str == toolName)
      val schema = body("tools")(0)("input_schema").obj
      assert(!schema.contains("$schema") && !schema.contains("$id") && !schema.contains("title"))
      assert(schema("type").str == "object" && schema("required") == ujson.Arr("a"))
      assert(schema("additionalProperties") == ujson.Bool(false))
      assert(schema("properties")("a")("title").str == "nested title")
      assert(!call.body.contains("strict"))
      assert(!call.body.contains(secret))
      result match {
        case LlmResult.Output(json, usage, model, version) =>
          assert(ujson.read(json) == input)
          assert(usage == LlmUsage(Some(12), Some(15)))
          assert(model == config.model.modelId && version == config.model.modelVersion)
        case other => fail(s"Expected output, got $other")
      }
    }
  }

  test("anthropic-version is configurable and the base URI is validated without echo") {
    withStub(ok()) { stub =>
      new AnthropicMessagesLlmClient(
        key,
        config,
        AnthropicSettings(baseUri = stub.baseUri + "/", anthropicVersion = "2099-01-01")
      ).complete(request())
      assert(stub.seen.head.headers.get("anthropic-version").contains("2099-01-01"))
      assert(stub.seen.head.path == "/v1/messages")
    }
    new AnthropicMessagesLlmClient(key, config)
    Vector(
      "http://example.com",
      "ftp://127.0.0.1",
      "https://user:pw@api.anthropic.com",
      "https://api.anthropic.com/x",
      "https://api.anthropic.com?q=1"
    ).foreach { bad =>
      val e = intercept[IllegalArgumentException](
        new AnthropicMessagesLlmClient(key, config, at(bad))
      )
      assert(e.getMessage.contains("invalid-anthropic-base-uri") && !e.getMessage.contains("pw"))
    }
    intercept[IllegalArgumentException](AnthropicSettings(anthropicVersion = "latest"))
  }

  test("api key value object is redacted and rejects unsafe values with a closed code") {
    assert(key.toString == "AnthropicApiKey(REDACTED)" && !key.toString.contains(secret))
    Vector("", "has space", "line\nbreak", "tab\tchar", "x" * 513).foreach { bad =>
      assert(AnthropicApiKey.fromValue(bad) == Left("invalid-anthropic-api-key"))
    }
    assert(AnthropicApiKey.fromValue(null) == Left("invalid-anthropic-api-key"))
  }

  test("accepts exact safe numbers and rejects unsafe, inexact and non-finite ones") {
    val marker = "\"__NUMBER__\""
    def withNumber(token: String): Reply = Reply(
      200,
      message(Vector(toolBlock(in = ujson.Obj("count" -> "__NUMBER__"))))
        .render()
        .replace(marker, token)
    )
    Vector("12", "0.5", "-7", "1e2", (BigInt(2).pow(53) - 1).toString).foreach { token =>
      withStub(withNumber(token)) { stub =>
        assert(client(stub).complete(request()).isInstanceOf[LlmResult.Output], token)
      }
    }
    Vector((BigInt(2).pow(53) + 1).toString, "1e400", ("7" * 30)).foreach { token =>
      withStub(withNumber(token)) { stub =>
        assert(codeOf(client(stub).complete(request())) == "llm-invalid-tool-output", token)
      }
    }
  }

  test("refuses non-tool, wrong-tool, multi-block, truncated and non-object outputs") {
    val text = ujson.Obj("type" -> "text", "text" -> "{\"looks\":\"like json\"}")
    val cases = Vector(
      "text only" -> message(Vector(text)),
      "wrong tool" -> message(Vector(toolBlock("wrong_tool"))),
      "two blocks" -> message(Vector(toolBlock(), toolBlock())),
      "no blocks" -> message(Vector.empty),
      "max_tokens" -> message(stop = "max_tokens"),
      "end_turn" -> message(stop = "end_turn"),
      "array input" -> message(Vector(toolBlock(in = ujson.Arr(1))))
    )
    cases.foreach { (label, m) =>
      withStub(ok(m)) { stub =>
        assert(codeOf(client(stub).complete(request())) == "llm-invalid-tool-output", label)
      }
    }
    withStub(Reply(200, "[1,2]")) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-invalid-tool-output")
    }
  }

  test("response model must equal the configured model id") {
    Vector("other-model", "").foreach { other =>
      withStub(ok(message(model = other))) { stub =>
        assert(codeOf(client(stub).complete(request())) == "llm-model-mismatch")
      }
    }
    val noModel = message()
    noModel.value.remove("model")
    withStub(ok(noModel)) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-model-mismatch")
    }
  }

  test("depth bound refuses deeply nested output") {
    val deep = "[" * 100 + "]" * 100
    val raw = message(Vector(toolBlock(in = ujson.Obj("v" -> "__DEEP__"))))
      .render()
      .replace("\"__DEEP__\"", deep)
    withStub(Reply(200, raw)) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-invalid-tool-output")
    }
  }

  test("output bound: oversized envelope and oversized tool input are both refused") {
    val limit = config.effectiveByteLimits.outputBytes
    val hugeEnvelope = message(Vector(toolBlock(in = ujson.Obj("v" -> ("x" * (limit * 3))))))
    withStub(ok(hugeEnvelope)) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-output-bound")
    }
    val bigInput = message(Vector(toolBlock(in = ujson.Obj("v" -> ("x" * (limit + 100))))))
    withStub(ok(bigInput)) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-output-bound")
    }
    val nearLimit = message(Vector(toolBlock(in = ujson.Obj("v" -> ("x" * (limit - 100))))))
    withStub(ok(nearLimit)) { stub =>
      assert(client(stub).complete(request()).isInstanceOf[LlmResult.Output])
    }
  }

  test("HTTP errors map to provider-rejected, are not retried and do not follow redirects") {
    Vector(400, 401, 403, 404, 429, 500, 503, 529, 204, 201).foreach { status =>
      withStub(Reply(status, if (status == 204) "" else "{\"error\":\"fixture\"}")) { stub =>
        val result = client(stub).complete(request())
        assert(result == LlmResult.Failure("llm-provider-rejected"), status.toString)
        assert(stub.seen.size == 1, s"no retry for $status")
      }
    }
    withStub(Reply(302, "", headers = Map("location" -> "http://127.0.0.1:1/elsewhere"))) { stub =>
      assert(client(stub).complete(request()) == LlmResult.Failure("llm-provider-rejected"))
      assert(stub.seen.size == 1)
    }
  }

  test("malformed or non-UTF-8 success bodies are a client-or-response failure") {
    withStub(Reply(200, "not json at all")) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-client-or-response-failure")
    }
    withStub(Reply(200, "")) { stub =>
      assert(codeOf(client(stub).complete(request())) == "llm-client-or-response-failure")
    }
  }

  test("slow server hits the per-call deadline and connection refusal is a closed failure") {
    withStub(Reply(200, message().render(), delayMs = 3000)) { stub =>
      val started = System.nanoTime()
      val result = client(stub).complete(request(timeout = 400))
      val elapsedMs = (System.nanoTime() - started) / 1000000
      assert(result == LlmResult.Failure("llm-client-or-response-failure"))
      assert(elapsedMs < 2500, s"deadline not honoured: $elapsedMs ms")
      assert(stub.seen.size == 1)
    }
    val closed = new Stub(_ => Reply(200, ""))
    val base = closed.baseUri
    closed.stop()
    val refused = new AnthropicMessagesLlmClient(key, config, at(base)).complete(request())
    assert(refused == LlmResult.Failure("llm-client-or-response-failure"))
  }

  test("invalid inputs are refused before any request is sent") {
    withStub(ok()) { stub =>
      val c = client(stub)
      Vector(
        request(timeout = 0),
        request().copy(toolName = " "),
        request().copy(systemPrompt = " "),
        request().copy(userData = ""),
        request().copy(userData = "x" * (config.effectiveByteLimits.requestBytes + 1))
      ).foreach(r => assert(codeOf(c.complete(r)) == "llm-input-bound"))
      assert(stub.seen.isEmpty)
    }
  }

  // ----- claude-haiku-5-5 rules -----

  private val samplingFields = Vector("temperature", "top_p", "top_k")

  test("rule: temperature, top_p and top_k are never sent, even when the config has a value") {
    Vector(0.0, 0.7, 1.0).foreach { temperature =>
      val c = config.copy(model = config.model.copy(temperature = temperature))
      withStub(ok()) { stub =>
        assert(client(stub, c).complete(request()).isInstanceOf[LlmResult.Output])
        val body = ujson.read(stub.seen.head.body).obj
        samplingFields.foreach(f => assert(!body.contains(f), s"$f present at $temperature"))
        samplingFields.foreach(f => assert(!stub.seen.head.body.contains(f)))
      }
    }
  }

  test("rule: forced tool_choice names the requested tool and no thinking or auto choice is sent") {
    withStub(ok()) { stub =>
      client(stub).complete(request())
      val body = ujson.read(stub.seen.head.body).obj
      assert(body("tool_choice") == ujson.Obj("type" -> "tool", "name" -> toolName))
      assert(!body.contains("thinking") && !stub.seen.head.body.contains("\"auto\""))
    }
  }

  test("rule: no prefill, exactly one user message and no assistant turn") {
    withStub(ok()) { stub =>
      client(stub).complete(request())
      val messages = ujson.read(stub.seen.head.body)("messages").arr
      assert(messages.size == 1 && messages.head("role").str == "user")
      assert(!stub.seen.head.body.contains("\"assistant\""))
    }
  }

  test("rule: content blocks are read by type, not position; thinking and text are ignored") {
    val text = ujson.Obj("type" -> "text", "text" -> "{\"looks\":\"like json\"}")
    val thinking = ujson.Obj("type" -> "thinking", "thinking" -> "x", "signature" -> "s")
    val redacted = ujson.Obj("type" -> "redacted_thinking", "data" -> "x")
    Vector(
      "tool first" -> Vector(toolBlock(), text),
      "text first" -> Vector(text, toolBlock()),
      "thinking first" -> Vector(thinking, toolBlock()),
      "redacted thinking and text" -> Vector(redacted, text, toolBlock())
    ).foreach { (label, blocks) =>
      withStub(ok(message(blocks))) { stub =>
        client(stub).complete(request()) match {
          case LlmResult.Output(json, _, _, _) => assert(ujson.read(json) == input, label)
          case other                           => fail(s"$label: $other")
        }
      }
    }
    // The tool input is the only output: text is never parsed as a substitute for it.
    Vector(
      "text only" -> Vector(text),
      "thinking only" -> Vector(thinking),
      "unknown block type" -> Vector(ujson.Obj("type" -> "server_tool_use"), toolBlock()),
      "block without type" -> Vector(ujson.Obj("name" -> toolName), toolBlock()),
      "non-object block" -> Vector(ujson.Str("x"), toolBlock()),
      "two tool blocks" -> Vector(text, toolBlock(), toolBlock())
    ).foreach { (label, blocks) =>
      withStub(ok(message(blocks))) { stub =>
        assert(codeOf(client(stub).complete(request())) == "llm-invalid-tool-output", label)
      }
    }
  }

  test("rule: stop_reason refusal is a typed, non-retried error") {
    assert(AnthropicMessagesLlmClient.RefusalCode == "llm-refusal")
    withStub(ok(message(Vector.empty, stop = "refusal"))) { stub =>
      assert(client(stub).complete(request()) == LlmResult.Failure("llm-refusal"))
      assert(stub.seen.size == 1)
    }
    // A refusal that still carries a tool block is a refusal, not an output.
    withStub(ok(message(Vector(toolBlock()), stop = "refusal"))) { stub =>
      assert(client(stub).complete(request()) == LlmResult.Failure("llm-refusal"))
      assert(stub.seen.size == 1)
    }
  }

  test("rule: max_tokens is the configured budget times the configured factor (default 1.3)") {
    assert(AnthropicDefaults.MaxTokensFactor == 1.3)
    assert(AnthropicSettings().maxTokensFactor == AnthropicDefaults.MaxTokensFactor)
    Vector(1, 10, 1000, 4096).foreach { budget =>
      val expected = math.ceil(budget * 1.3).toInt
      assert(AnthropicMessagesLlmClient.maxTokensFor(budget, 1.3) == expected)
      assert(AnthropicMessagesLlmClient.maxTokensFor(budget, 1.3) >= budget)
    }
    assert(AnthropicMessagesLlmClient.maxTokensFor(1000, 1.3) == 1300)
    val c = config.copy(maxOutputTokens = 1000)
    withStub(ok()) { stub =>
      client(stub, c).complete(request())
      assert(ujson.read(stub.seen.head.body)("max_tokens").num == 1300)
    }
    // A configured factor replaces the default.
    withStub(ok()) { stub =>
      client(stub, c, AnthropicSettings(maxTokensFactor = 2.0)).complete(request())
      assert(ujson.read(stub.seen.head.body)("max_tokens").num == 2000)
    }
    intercept[IllegalArgumentException](AnthropicSettings(maxTokensFactor = 0.5))
  }

  test("rule: top-level $schema, $id and title are stripped, nested names stay, strict is unset") {
    withStub(ok()) { stub =>
      client(stub).complete(request())
      val schema = ujson.read(stub.seen.head.body)("tools")(0)("input_schema").obj
      Vector("$schema", "$id", "title").foreach(k => assert(!schema.contains(k), k))
      assert(schema("properties")("a")("title").str == "nested title")
      assert(!stub.seen.head.body.contains("strict"))
    }
  }

  test("model id: the default is claude-haiku-5-5 and is used when nothing else is configured") {
    assert(AnthropicDefaults.ModelId == "claude-haiku-5-5")
    assert(AnthropicMessagesLlmClient.ModelId == AnthropicDefaults.ModelId)
    assert(config.model.modelId == "claude-haiku-5-5")
    withStub(ok()) { stub =>
      client(stub).complete(request())
      assert(ujson.read(stub.seen.head.body)("model").str == "claude-haiku-5-5")
    }
  }

  test("model id: a configured non-default id reaches the request body and the echo check") {
    val other = "claude-configured-model-x"
    val c = config.copy(model = config.model.copy(modelId = other))
    withStub(ok(message(model = other))) { stub =>
      client(stub, c).complete(request()) match {
        case LlmResult.Output(_, _, id, _) => assert(id == other)
        case failure                       => fail(s"Expected output, got $failure")
      }
      assert(ujson.read(stub.seen.head.body)("model").str == other)
    }
    // The echo is compared with the configured id, so the old default is now a mismatch.
    withStub(ok(message(model = AnthropicDefaults.ModelId))) { stub =>
      assert(codeOf(client(stub, c).complete(request())) == "llm-model-mismatch")
    }
    // The Haiku 5.5 request rules still apply to the configured model.
    withStub(ok(message(model = other))) { stub =>
      client(stub, c).complete(request())
      val body = ujson.read(stub.seen.head.body).obj
      Vector("temperature", "top_p", "top_k", "strict").foreach(k => assert(!body.contains(k)))
      assert(body("tool_choice") == ujson.Obj("type" -> "tool", "name" -> toolName))
    }
  }

  test("rule: a prompt estimated at or above 100,000 tokens is refused before any call") {
    assert(AnthropicDefaults.PromptTokenLimit == 100000L)
    assert(AnthropicDefaults.BytesPerEstimatedToken == 3)
    assert(AnthropicSettings().promptTokenLimit == 100000L)
    val big = baseConfig.copy(
      model = config.model,
      byteLimits = Some(RuntimeByteLimits(1000000, 1000000, 1000000, 1000000, 1000000))
    )
    // estimate = (system + data + schema bytes + 2) / 3, so the data length for an exact estimate
    // follows from the fixed bytes of the other two parts.
    val fixedBytes = (request().systemPrompt + request().schemaJson).getBytes(UTF_8).length
    def withEstimate(tokens: Long): StructuredLlmRequest = {
      val data = "d" * (tokens * 3 - 2 - fixedBytes).toInt
      val r = request().copy(userData = data)
      assert(AnthropicMessagesLlmClient.estimatePromptTokens(r, 3) == tokens)
      r
    }
    val atLimit = withEstimate(100000L)
    val below = withEstimate(99999L)
    withStub(ok()) { stub =>
      val c = client(stub, big)
      assert(c.complete(atLimit) == LlmResult.Failure("llm-prompt-too-large"))
      assert(stub.seen.isEmpty, "refused before any call")
      val over = atLimit.copy(userData = atLimit.userData + "d" * 30)
      assert(c.complete(over) == LlmResult.Failure("llm-prompt-too-large"))
      assert(stub.seen.isEmpty)
      assert(c.complete(below).isInstanceOf[LlmResult.Output])
      assert(stub.seen.size == 1)
    }
    // A configured limit replaces the default: `below` is refused at a limit of 99,999.
    withStub(ok()) { stub =>
      val c = client(stub, big, AnthropicSettings(promptTokenLimit = 99999L))
      assert(c.complete(below) == LlmResult.Failure("llm-prompt-too-large"))
      assert(stub.seen.isEmpty)
    }
  }

  test("the api key never appears in results, exception text, or console output") {
    val echoed = Reply(
      401,
      s"""{"error":{"message":"bad key $secret"}}""",
      headers = Map("x-echo-key" -> secret)
    )
    val captured = new ByteArrayOutputStream()
    val sink = new PrintStream(captured, true, "UTF-8")
    val (oldOut, oldErr) = (System.out, System.err)
    val results =
      try {
        System.setOut(sink)
        System.setErr(sink)
        val replies = Vector(
          echoed,
          Reply(200, s"""{"model":"$secret","content":[]}"""),
          Reply(200, message().render().replace("fixture", secret)),
          Reply(200, s"not json $secret")
        )
        replies.map(r => withStub(r)(stub => client(stub).complete(request())))
      } finally {
        System.setOut(oldOut)
        System.setErr(oldErr)
      }
    results.foreach(r => assert(!r.toString.contains(secret), r.toString))
    assert(!captured.toString("UTF-8").contains(secret))
    results.take(2).foreach(r => assert(r.isInstanceOf[LlmResult.Failure]))
    val badUri = intercept[IllegalArgumentException](
      new AnthropicMessagesLlmClient(key, config, at(s"http://$secret@example.com"))
    )
    assert(!badUri.getMessage.contains(secret))
  }
}
