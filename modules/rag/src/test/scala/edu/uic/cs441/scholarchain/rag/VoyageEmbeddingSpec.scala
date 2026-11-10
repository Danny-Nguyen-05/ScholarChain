package edu.uic.cs441.scholarchain.rag

import com.sun.net.httpserver.HttpServer
import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.io.{ByteArrayOutputStream, PrintStream}
import java.net.{InetAddress, InetSocketAddress}
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{ConcurrentLinkedQueue, Executors}
import scala.jdk.CollectionConverters.*

/** Fake HTTP only: every request goes to an in-process server on 127.0.0.1 with a synthetic
  * placeholder key. No Voyage host, network or secret is touched.
  */
class VoyageEmbeddingSpec extends AnyFunSuite {
  private val secret = "pa-synthetic-placeholder-key-value"
  private val key = VoyageApiKey.fromValue(secret).toOption.get
  private val dim = VoyageEmbeddingClient.OutputDimension

  private final case class Seen(path: String, headers: Map[String, String], body: String) {
    def json: ujson.Obj = ujson.read(body).obj
    def inputs: Vector[String] = json("input").arr.map(_.str).toVector
  }
  private final case class Reply(status: Int, body: String, delayMs: Long = 0)
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
            exchange.getRequestURI.toString,
            headers,
            new String(exchange.getRequestBody.readAllBytes(), UTF_8)
          )
          log.add(seen)
          val reply = respond(seen)
          if (reply.delayMs > 0) Thread.sleep(reply.delayMs)
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
  private def withStub[A](respond: Seen => Reply)(f: Stub => A): A = {
    val stub = new Stub(respond)
    try f(stub)
    finally stub.stop()
  }

  /** Vector whose first component encodes the position of the text in the request (as a float). */
  private def vector(marker: Int, size: Int = dim): ujson.Arr =
    ujson.Arr.from((0 until size).map(i => ujson.Num(if (i == 0) marker.toDouble else 0.5)))
  private def good(
      count: Int,
      tokens: Long = 10,
      model: String = "voyage-4-lite",
      shuffle: Boolean = false,
      size: Int = dim
  ): String = {
    val rows = (0 until count).map(i =>
      ujson.Obj("object" -> "embedding", "embedding" -> vector(i, size), "index" -> i)
    )
    ujson
      .Obj(
        "object" -> "list",
        "data" -> ujson.Arr.from(if (shuffle) rows.reverse else rows),
        "model" -> model,
        "usage" -> ujson.Obj("total_tokens" -> ujson.Num(tokens.toDouble))
      )
      .render()
  }
  private val echo: Seen => Reply = seen => Reply(200, good(seen.inputs.size))
  private def config(
      inputType: EmbeddingInputType = EmbeddingInputType.Document,
      c: VoyageEmbeddingConfig => VoyageEmbeddingConfig = identity
  )(stub: Stub) = c(VoyageEmbeddingConfig(inputType, baseUri = stub.baseUri))
  private def client(
      stub: Stub,
      inputType: EmbeddingInputType = EmbeddingInputType.Document,
      counter: EmbeddingSpendCounter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage),
      sleeps: scala.collection.mutable.ArrayBuffer[Long] = null,
      tune: VoyageEmbeddingConfig => VoyageEmbeddingConfig = identity
  ) = new VoyageEmbeddingClient(
    key,
    config(inputType, tune)(stub),
    counter,
    ms => if (sleeps != null) sleeps += ms
  )
  private def codes(results: Seq[EmbeddingResult]): Seq[String] = results.map {
    case EmbeddingFailure(code, _, _, _) => code
    case _: EmbeddingSuccess             => "ok"
  }

  test("model identity: voyage-4-lite, version tag voyage-4-lite, dimension 256") {
    assert(VoyageEmbeddingClient.ModelId == "voyage-4-lite")
    assert(VoyageEmbeddingClient.Model == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    withStub(echo)(stub => assert(client(stub).model == VoyageEmbeddingClient.Model))
  }

  test(
    "request shape: URL, bearer auth, model, output_dimension, document input_type, no truncation"
  ) {
    withStub(echo) { stub =>
      val results = client(stub).embed(Seq("alpha", "beta"))
      val call = stub.seen.head
      assert(stub.seen.size == 1 && call.path == "/v1/embeddings")
      assert(call.headers.get("authorization").contains("Bearer " + secret))
      assert(call.headers.get("content-type").contains("application/json"))
      val body = call.json
      assert(body("model").str == "voyage-4-lite")
      assert(body("output_dimension").num == 256)
      assert(body("input_type").str == "document")
      assert(body("truncation") == ujson.Bool(false))
      assert(call.inputs == Vector("alpha", "beta"))
      assert(!call.body.contains(secret))
      results.zipWithIndex.foreach {
        case (EmbeddingSuccess(values, model, attempts), i) =>
          assert(values.size == 256 && values.head == i.toFloat)
          assert(model == VoyageEmbeddingClient.Model && attempts == 1)
        case (other, _) => fail(s"Expected success, got $other")
      }
    }
  }

  test("input_type is query for queries and document for ingest") {
    withStub(echo) { stub =>
      client(stub, EmbeddingInputType.Query).embed(Seq("who collaborates with whom"))
      client(stub, EmbeddingInputType.Document).embed(Seq("a paper abstract"))
      assert(stub.seen.map(_.json("input_type").str) == Vector("query", "document"))
      assert(
        EmbeddingInputType.Query.wire == "query" && EmbeddingInputType.Document.wire == "document"
      )
    }
  }

  test("at most 1,000 texts per request: 2,500 texts become 1,000 + 1,000 + 500, order kept") {
    withStub(echo) { stub =>
      val texts = (0 until 2500).map(i => s"t$i")
      val results = client(stub).embed(texts)
      assert(stub.seen.map(_.inputs.size) == Vector(1000, 1000, 500))
      assert(stub.seen.flatMap(_.inputs) == texts.toVector)
      assert(results.size == 2500 && codes(results).forall(_ == "ok"))
      // Each response numbers positions from 0 within its own request.
      assert(
        results.map { case EmbeddingSuccess(v, _, _) => v.head.toInt; case _ => -1 } ==
          (0 until 2500).map(_ % 1000)
      )
      assert(VoyageEmbeddingClient.MaxTextsPerRequest == 1000)
    }
  }

  test("at most 1,000,000 estimated tokens per request: 31,000-byte texts split 32 + 8") {
    withStub(echo) { stub =>
      val texts = Vector.fill(40)("x" * 31000)
      val results = client(stub).embed(texts)
      assert(stub.seen.map(_.inputs.size) == Vector(32, 8))
      assert(stub.seen.forall(_.inputs.map(_.length.toLong).sum <= 1000000L))
      assert(codes(results).forall(_ == "ok"))
      assert(VoyageEmbeddingClient.MaxTokensPerRequest == 1000000)
    }
  }

  test("per-text bounds are typed failures with no request; other texts still embed in place") {
    withStub(echo) { stub =>
      val results = client(stub).embed(
        Seq("fine", "", "   ", "x" * 32001, "x" * 32000, null)
      )
      assert(
        codes(results) == Seq(
          "ok",
          "empty-document-text",
          "empty-document-text",
          "embedding-input-limit",
          "ok",
          "empty-document-text"
        )
      )
      assert(stub.seen.size == 1 && stub.seen.head.inputs.size == 2)
    }
    withStub(echo) { stub =>
      assert(client(stub).embed(Seq("", "x" * 32001)).forall(_.isInstanceOf[EmbeddingFailure]))
      assert(client(stub).embed(Seq.empty).isEmpty)
      assert(stub.seen.isEmpty)
    }
  }

  test("defaults are held in VoyageDefaults and used when nothing is configured") {
    assert(VoyageDefaults.MaxTextsPerRequest == 1000)
    assert(VoyageDefaults.MaxTokensPerRequest == 1000000)
    assert(VoyageDefaults.MaxInputTokens == 32000)
    assert(VoyageDefaults.UsdPerMillionTokens == BigDecimal("0.02"))
    assert(VoyageDefaults.CapUsd == BigDecimal("0.30"))
    assert(VoyageDefaults.BaseUri == "https://api.voyageai.com")
    val c = VoyageEmbeddingConfig(EmbeddingInputType.Query)
    assert(c.model == VoyageDefaults.Model && c.baseUri == VoyageDefaults.BaseUri)
    assert(c.maxTextsPerRequest == 1000 && c.maxTokensPerRequest == 1000000)
    assert(c.maxInputTokens == 32000 && c.maxResponseBytes == VoyageDefaults.MaxResponseBytes)
  }

  test("a configured model id, version and dimension reach the request and the echo check") {
    val model = EmbeddingModel("voyage-configured-x", "configured-v7", 512)
    withStub(seen => Reply(200, good(seen.inputs.size, model = model.modelId, size = 512))) {
      stub =>
        val c = new VoyageEmbeddingClient(
          key,
          VoyageEmbeddingConfig(EmbeddingInputType.Document, model = model, baseUri = stub.baseUri)
        )
        assert(c.model == model)
        c.embed(Seq("a")) match {
          case Seq(EmbeddingSuccess(values, m, _)) => assert(values.size == 512 && m == model)
          case other                               => fail(s"Expected success, got $other")
        }
        val body = stub.seen.head.json
        assert(body("model").str == "voyage-configured-x" && body("output_dimension").num == 512)
    }
    // The echo is compared with the configured id: the default id echoed back is a mismatch.
    withStub(seen => Reply(200, good(seen.inputs.size, size = 512))) { stub =>
      val c = new VoyageEmbeddingClient(
        key,
        VoyageEmbeddingConfig(EmbeddingInputType.Document, model = model, baseUri = stub.baseUri)
      )
      assert(codes(c.embed(Seq("a"))) == Seq("embedding-model-mismatch"))
    }
  }

  test("configured limits replace the defaults: 2 texts or 300 tokens per request") {
    withStub(echo) { stub =>
      val texts = Vector.fill(5)("x" * 100)
      val byCount = client(stub, tune = _.copy(maxTextsPerRequest = 2)).embed(texts)
      assert(stub.seen.map(_.inputs.size) == Vector(2, 2, 1) && codes(byCount).forall(_ == "ok"))
    }
    withStub(echo) { stub =>
      client(stub, tune = _.copy(maxTokensPerRequest = 300)).embed(Vector.fill(5)("x" * 100))
      assert(stub.seen.map(_.inputs.size) == Vector(3, 2))
    }
    withStub(echo) { stub =>
      val results = client(stub, tune = _.copy(maxInputTokens = 50)).embed(Seq("x" * 51, "x" * 50))
      assert(codes(results) == Seq("embedding-input-limit", "ok"))
    }
  }

  test("config validation: positive limits, voyage family model, supported dimension") {
    Vector[VoyageEmbeddingConfig => VoyageEmbeddingConfig](
      _.copy(maxTextsPerRequest = 0),
      _.copy(maxTokensPerRequest = 0),
      _.copy(maxInputTokens = 0),
      _.copy(maxResponseBytes = 0),
      _.copy(maxAttempts = 0),
      _.copy(requestTimeoutMillis = 0),
      _.copy(model = VoyageDefaults.Model.copy(modelId = "amazon.titan-embed-text-v2:0")),
      _.copy(model = VoyageDefaults.Model.copy(dimension = 100)),
      _.copy(model = VoyageDefaults.Model.copy(dimension = 0))
    ).foreach(change =>
      intercept[IllegalArgumentException](change(VoyageEmbeddingConfig(EmbeddingInputType.Query)))
    )
    // A dimension outside the default list is accepted when configured as supported.
    VoyageEmbeddingConfig(
      EmbeddingInputType.Query,
      model = VoyageDefaults.Model.copy(dimension = 100),
      supportedDimensions = Set(100)
    )
  }

  test("the response is validated: model echo, count, dimension and index set") {
    def one(body: String) = withStub(_ => Reply(200, body)) { stub =>
      client(stub).embed(Seq("a", "b"))
    }
    assert(codes(one(good(2, model = "voyage-4"))) == Seq.fill(2)("embedding-model-mismatch"))
    assert(codes(one(good(1))) == Seq.fill(2)("embedding-dimension-or-value-mismatch"))
    assert(codes(one(good(3))) == Seq.fill(2)("embedding-dimension-or-value-mismatch"))
    val short = ujson.read(good(2))
    short("data")(1)("embedding") = ujson.Arr(1, 2)
    assert(codes(one(short.render())) == Seq.fill(2)("embedding-dimension-or-value-mismatch"))
    val dup = ujson.read(good(2))
    dup("data")(1)("index") = 0
    assert(codes(one(dup.render())) == Seq.fill(2)("embedding-dimension-or-value-mismatch"))
    assert(codes(one("not json")) == Seq.fill(2)("embedding-invalid-response"))
    assert(codes(one("[]")) == Seq.fill(2)("embedding-invalid-response"))
    assert(codes(one("{}")) == Seq.fill(2)("embedding-model-mismatch"))
    // Out-of-order rows are mapped back by index.
    withStub(_ => Reply(200, good(2, shuffle = true))) { stub =>
      val results = client(stub).embed(Seq("a", "b"))
      assert(results.map {
        case EmbeddingSuccess(v, _, _) => v.head.toInt; case _ => -1
      } == Seq(0, 1))
    }
  }

  test("400/401/403 are permanent and not retried; 429 and 5xx retry with backoff") {
    Vector(400, 401, 403, 404, 422).foreach { status =>
      withStub(_ => Reply(status, """{"detail":"fixture"}""")) { stub =>
        val results = client(stub).embed(Seq("a"))
        assert(
          results == Seq(
            EmbeddingFailure("embedding-provider-rejected", false, VoyageEmbeddingClient.Model, 1)
          )
        )
        assert(stub.seen.size == 1, status.toString)
      }
    }
    val sleeps = scala.collection.mutable.ArrayBuffer.empty[Long]
    var calls = 0
    withStub { seen =>
      calls += 1
      if (calls == 1) Reply(429, "{}") else if (calls == 2) Reply(503, "{}") else echo(seen)
    } { stub =>
      val results = client(stub, sleeps = sleeps).embed(Seq("a"))
      results.head match {
        case EmbeddingSuccess(_, _, attempts) => assert(attempts == 3)
        case other                            => fail(s"Expected success, got $other")
      }
      assert(stub.seen.size == 3 && sleeps.toVector == Vector(25L, 50L))
    }
    val counter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage)
    withStub(_ => Reply(500, "{}")) { stub =>
      val results = client(stub, counter = counter, sleeps = sleeps).embed(Seq("a"))
      assert(
        results == Seq(
          EmbeddingFailure("embedding-retries-exhausted", true, VoyageEmbeddingClient.Model, 3)
        )
      )
      assert(stub.seen.size == 3)
      assert(counter.tokensUsed == BigInt(0), "failed requests are not counted")
    }
  }

  test("redirects are not followed and a slow server hits the request timeout") {
    withStub(_ => Reply(302, "")) { stub =>
      val results = client(stub, tune = _.copy(maxAttempts = 1)).embed(Seq("a"))
      assert(
        results == Seq(
          EmbeddingFailure("embedding-provider-rejected", false, VoyageEmbeddingClient.Model, 1)
        )
      )
      assert(stub.seen.size == 1)
    }
    withStub(_ => Reply(200, good(1), delayMs = 3000)) { stub =>
      val started = System.nanoTime()
      val results =
        client(stub, tune = _.copy(maxAttempts = 1, requestTimeoutMillis = 400)).embed(Seq("a"))
      assert((System.nanoTime() - started) / 1000000 < 2500)
      assert(codes(results) == Seq("embedding-retries-exhausted"))
    }
  }

  test("token counter: Voyage USD 0.02 per 1M, USD 0.30 cap is 15,000,000 tokens") {
    val counter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage)
    assert(counter.usdPerMillionTokens == BigDecimal("0.02"))
    assert(counter.capUsd == BigDecimal("0.30") && counter.capTokens == BigInt(15000000))
    withStub(seen => Reply(200, good(seen.inputs.size, tokens = 1234))) { stub =>
      val c = client(stub, counter = counter)
      c.embed(Seq("a", "b"))
      c.embed(Seq("c"))
      assert(counter.tokensUsed == BigInt(2468))
      assert(counter.usdUsed == BigDecimal("0.00004936"))
      assert(c.tokenCounter eq counter)
    }
  }

  test(
    "token counter applies even though the first 200M tokens are free: cap refuses before send"
  ) {
    // Cap USD 0.0001 at USD 0.02 per 1M tokens is 5,000 tokens.
    val counter = new EmbeddingSpendCounter(BigDecimal("0.0001"), BigDecimal("0.02"))
    assert(counter.capTokens == BigInt(5000))
    withStub(seen => Reply(200, good(seen.inputs.size, tokens = 2900))) { stub =>
      val c = client(stub, counter = counter)
      val text = "x" * 3000
      assert(codes(c.embed(Seq(text))) == Seq("ok"))
      assert(counter.tokensUsed == BigInt(2900))
      // 2,900 used + 3,000 estimated > 5,000: refused with no request and no retry.
      assert(codes(c.embed(Seq(text))) == Seq("embedding-token-cap"))
      assert(stub.seen.size == 1)
      assert(counter.tokensUsed == BigInt(2900))
      assert(codes(c.embed(Seq("y" * 2000))) == Seq("ok"))
      assert(stub.seen.size == 2)
    }
  }

  test("a counter constructed with a non-positive cap or price is refused") {
    intercept[IllegalArgumentException](
      new EmbeddingSpendCounter(BigDecimal(0), BigDecimal("0.02"))
    )
    intercept[IllegalArgumentException](new EmbeddingSpendCounter(BigDecimal("0.3"), BigDecimal(0)))
  }

  test("the base URI is validated and plain http is loopback only") {
    new VoyageEmbeddingClient(key, VoyageEmbeddingConfig(EmbeddingInputType.Query))
    Vector(
      "http://example.com",
      "ftp://127.0.0.1",
      "https://user:pw@api.voyageai.com",
      "https://api.voyageai.com/x",
      "https://api.voyageai.com?q=1"
    ).foreach { bad =>
      val e = intercept[IllegalArgumentException](
        new VoyageEmbeddingClient(
          key,
          VoyageEmbeddingConfig(EmbeddingInputType.Query, baseUri = bad)
        )
      )
      assert(e.getMessage.contains("invalid-voyage-base-uri") && !e.getMessage.contains("pw"))
    }
  }

  test("the api key never appears in toString, error messages, results or console output") {
    assert(key.toString == "VoyageApiKey(REDACTED)" && !key.toString.contains(secret))
    Vector("", "has space", "line\nbreak", "x" * 513, null).foreach { bad =>
      assert(VoyageApiKey.fromValue(bad) == Left("invalid-voyage-api-key"))
    }
    val client0 = new VoyageEmbeddingClient(key, VoyageEmbeddingConfig(EmbeddingInputType.Query))
    assert(!client0.toString.contains(secret))
    assert(!client0.model.toString.contains(secret))
    val badUri = intercept[IllegalArgumentException](
      new VoyageEmbeddingClient(
        key,
        VoyageEmbeddingConfig(EmbeddingInputType.Query, baseUri = s"http://$secret@example.com")
      )
    )
    assert(!badUri.getMessage.contains(secret))
    val captured = new ByteArrayOutputStream()
    val sink = new PrintStream(captured, true, "UTF-8")
    val (oldOut, oldErr) = (System.out, System.err)
    val results =
      try {
        System.setOut(sink)
        System.setErr(sink)
        Vector(
          Reply(401, s"""{"detail":"bad key $secret"}"""),
          Reply(200, s"""{"model":"$secret","data":[]}"""),
          Reply(200, s"not json $secret"),
          Reply(500, secret)
        ).flatMap(reply =>
          withStub(_ => reply)(stub => client(stub, tune = _.copy(maxAttempts = 1)).embed(Seq("a")))
        )
      } finally {
        System.setOut(oldOut)
        System.setErr(oldErr)
      }
    results.foreach(r => assert(!r.toString.contains(secret), r.toString))
    assert(results.forall(_.isInstanceOf[EmbeddingFailure]))
    assert(!captured.toString("UTF-8").contains(secret))
  }
}
