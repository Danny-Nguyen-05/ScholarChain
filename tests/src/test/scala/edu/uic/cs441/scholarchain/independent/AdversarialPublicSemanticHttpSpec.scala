package edu.uic.cs441.scholarchain.independent

import java.net.http.HttpResponse
import java.util.Base64
import java.util.concurrent.{CountDownLatch, Executors, TimeUnit}
import java.nio.charset.StandardCharsets.UTF_8
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable

/** P40-T: independent, hand-derived black-box tests of `POST /v1/semantic/retrieve` over real HTTP.
  * Expected values come from the published contract (modules/services/README.md "Public semantic
  * retrieval", the OpenAPI path `/v1/semantic/retrieve` and the user's accepted P40 defaults),
  * never from the implementation. Offline only: query-api, graph-service and semantic-service run
  * in `offline-synthetic` mode; downstream failures come from a local stub. Where the contract is
  * silent, the test only checks safety (no 5xx, no limit smuggling, no leak) and reports what it
  * observed through `info`.
  */
class AdversarialPublicSemanticHttpSpec extends AnyFunSuite {
  import AdversarialPublicSemanticFixture.*

  private val jobPath = "/v1/jobs/job-" + "0" * 64
  private def sq(i: Int): String = s"Synthetic $Sentinel question number $i about graphs"

  // Booleans are computed first so a failure never prints the observed text itself.
  private def assertClean(observed: String, where: String): Unit = {
    val question = observed.contains(Sentinel)
    val key = observed.contains(apiKey)
    val token = observed.contains(internalToken)
    assert(!question, s"question sentinel escaped into $where")
    assert(!key, s"raw API key escaped into $where")
    assert(!token, s"raw internal token escaped into $where")
  }

  private def assertLogsClean(logs: String): Unit = {
    val observed = logs.contains(Route)
    assert(observed, "log capture must observe the route's own request log line")
    assertClean(logs, "captured logs")
  }

  private def typedError(
      r: HttpResponse[String],
      status: Int,
      codes: Set[String],
      retryable: Option[Boolean] = None
  ): ujson.Value = {
    assert(r.statusCode() == status, s"expected $status, got ${r.statusCode()}")
    val json = ujson.read(r.body())
    assert(Set("error", "message", "traceId", "retryable").subsetOf(json.obj.keySet), r.body())
    assert(codes.isEmpty || codes(json("error").str), s"error code ${json("error").str}")
    assert(json("message").str.nonEmpty)
    assert(json("traceId").str == Trace && header(r, "X-Trace-Id").contains(Trace))
    retryable.foreach(flag => assert(json("retryable").bool == flag, r.body()))
    assertClean(r.body() + r.headers().map().toString, "an error reply")
    assert(!r.body().contains("Exception") && !r.body().contains("java."), r.body())
    assert(!r.body().contains("127.0.0.1:"), "an internal URL escaped into an error body")
    json
  }

  private def badRequest(r: HttpResponse[String]): Unit =
    typedError(r, 400, Set("INVALID_REQUEST"), Some(false))

  private def unauthorized(r: HttpResponse[String]): Unit =
    typedError(r, 401, Set("UNAUTHORIZED"), Some(false))

  /** The published reply: exactly hits[{key, distance, metadata}] and model{modelId, version,
    * dimension}.
    */
  private def projected(r: HttpResponse[String]): ujson.Value = {
    assert(r.statusCode() == 200, s"expected 200, got ${r.statusCode()}: ${r.body().take(300)}")
    val json = ujson.read(r.body())
    assert(json.obj.keySet == Set("hits", "model"), r.body())
    json("hits").arr.foreach { hit =>
      assert(hit.obj.keySet == Set("key", "distance", "metadata"), hit.render())
      hit("key").str; hit("distance").num
      hit("metadata").obj.values.foreach(_.str)
    }
    val model = json("model")
    assert(model.obj.keySet == Set("modelId", "version", "dimension"), model.render())
    model("modelId").str; model("version").str
    assert(model("dimension").num == math.rint(model("dimension").num))
    assert(header(r, "X-Trace-Id").contains(Trace))
    json
  }

  test(
    "deeply nested JSON inside the 8 KiB bound is a typed 400, never a 500 or a stack trace in the logs"
  ) {
    // Each body is at most 8,192 UTF-8 bytes, so only the JSON shape rule can reject it. This test
    // runs first so the server is as cold as possible: a recursion-depth failure shows up on an
    // unwarmed JIT (larger interpreted frames) and can disappear once the code is compiled.
    val deep = Vector(
      "array depth 4096" -> ("[" * 4096 + "]" * 4096),
      "array depth 4000" -> ("[" * 4000 + "]" * 4000),
      "object depth 1300" -> ("{\"a\":" * 1300 + "1" + "}" * 1300),
      "filter value depth 3900" ->
        (s"""{"question":"${sq(29)}","filters":{"f":""" + "[" * 3900 + "]" * 3900 + "}}"),
      "topK depth 3900" -> (s"""{"question":"${sq(29)}","topK":""" + "[" * 3900 + "]" * 3900 + "}")
    )
    deep.foreach((name, b) => require(b.getBytes(UTF_8).length <= 8192, name))
    val replies = mutable.LinkedHashMap.empty[String, HttpResponse[String]]
    var logs = ""
    withStub { stub =>
      withService("query-api", remoteEnv(stub)) { port =>
        logs = capturing {
          for ((name, content) <- deep) replies(name) = post(port, content)
          projected(post(port, question(sq(28))))
        }._2
        assert(stub.calls == 1, "a nested body reached semantic-service")
        assert(get(port, "/healthz").statusCode() == 200)
        // For the report only: shallower nesting, and the same body on pre-existing routes.
        for (depth <- Vector(100, 500, 1000, 2000, 3000))
          info(
            s"array depth $depth: public route ${post(port, "[" * depth + "]" * depth).statusCode()}"
          )
        val deepArray = "[" * 4000 + "]" * 4000
        val query = call(
          port,
          "/v1/query",
          Some(deepArray),
          headers = Seq("Content-Type" -> "application/json", "Idempotency-Key" -> "p40t-deep")
        )
        info(s"array depth 4000 on pre-existing POST /v1/query: ${query.statusCode()}")
        val internal =
          call(port, InternalRoute, Some(deepArray), auth = Seq("Bearer " + internalToken))
        info(
          s"array depth 4000 on query-api internal route (internal token): ${internal.statusCode()}"
        )
      }
    }
    for ((name, reply) <- replies) {
      val code = scala.util.Try(ujson.read(reply.body())("error").str).getOrElse("<untyped body>")
      info(s"$name: public route ${reply.statusCode()} $code")
    }
    for ((name, reply) <- replies) withClue(name) {
      assert(reply.statusCode() == 400, "expected typed 400 INVALID_REQUEST")
      badRequest(reply)
    }
    val overflow = logs.contains("StackOverflowError")
    val trace = logs.contains("\tat ")
    assert(!overflow, "a StackOverflowError reached the logs")
    assert(!trace, "a stack trace reached the logs")
    assertLogsClean(logs)
  }

  test(
    "offline query-api serves the route with exactly the published reply shape; other roles and unconfigured mode return 404"
  ) {
    val (_, logs) = capturing {
      withService("query-api", baseEnv()) { port =>
        val reply = projected(post(port, question(sq(1), Some(3))))
        assert(reply("hits").arr.size <= 3)
        assertClean(metricsText(port), "/metrics")
      }
      withService("semantic-service", baseEnv()) { port =>
        assert(post(port, question(sq(2))).statusCode() == 404)
        val direct = call(
          port,
          InternalRoute,
          Some(question(sq(3))),
          auth = Seq("Bearer " + internalToken)
        )
        assert(direct.statusCode() == 200, direct.body())
        unauthorized(call(port, InternalRoute, Some(question(sq(4)))))
      }
      withService("graph-service", baseEnv()) { port =>
        assert(post(port, question(sq(5))).statusCode() == 404)
      }
      withService("query-api", baseEnv("SCHOLARCHAIN_SERVICE_MODE" -> "unconfigured")) { port =>
        assert(post(port, question(sq(6))).statusCode() == 404)
      }
    }
    assertLogsClean(logs)
  }

  test(
    "authentication: only the public API key opens the route, exactly as on other /v1 routes, and it never opens the internal route"
  ) {
    val basic = Base64.getEncoder.encodeToString(s"user:$apiKey".getBytes(UTF_8))
    val mustReject: Vector[(String, Seq[String], Seq[(String, String)])] = Vector(
      ("missing header", Seq.empty, Seq.empty),
      ("empty bearer", Seq("Bearer "), Seq.empty),
      ("scheme only", Seq("Bearer"), Seq.empty),
      ("internal token", Seq("Bearer " + internalToken), Seq.empty),
      ("basic scheme", Seq("Basic " + basic), Seq.empty),
      ("key without scheme", Seq(apiKey), Seq.empty),
      ("token scheme", Seq("Token " + apiKey), Seq.empty),
      ("upper-case key", Seq("Bearer " + apiKey.toUpperCase), Seq.empty),
      ("key plus suffix", Seq("Bearer " + apiKey + "x"), Seq.empty),
      ("key prefix", Seq("Bearer " + apiKey.dropRight(1)), Seq.empty),
      ("presented key hash", Seq("Bearer " + sha256Hex(apiKey)), Seq.empty),
      ("presented token hash", Seq("Bearer " + sha256Hex(internalToken)), Seq.empty),
      ("X-Api-Key header", Seq.empty, Seq("X-Api-Key" -> apiKey)),
      ("key in cookie", Seq.empty, Seq("Cookie" -> s"api_key=$apiKey"))
    )
    val consistent: Vector[(String, Seq[String], Seq[(String, String)])] = Vector(
      ("lower-case scheme", Seq("bearer " + apiKey), Seq.empty),
      ("upper-case scheme", Seq("BEARER " + apiKey), Seq.empty),
      ("double space", Seq("Bearer  " + apiKey), Seq.empty),
      ("trailing space", Seq("Bearer " + apiKey + " "), Seq.empty),
      ("internal then key", Seq("Bearer " + internalToken, "Bearer " + apiKey), Seq.empty),
      ("key then internal", Seq("Bearer " + apiKey, "Bearer " + internalToken), Seq.empty)
    )
    val (_, logs) = capturing {
      withStub { stub =>
        withService("query-api", remoteEnv(stub)) { port =>
          for ((name, auth, extra) <- mustReject) {
            val headers = ("Content-Type" -> "application/json") +: extra
            withClue(name) {
              unauthorized(
                call(port, body = Some(question(sq(10))), auth = auth, headers = headers)
              )
              unauthorized(call(port, jobPath, method = "GET", auth = auth, headers = extra))
            }
          }
          assert(stub.calls == 0, "a rejected credential reached semantic-service")
          unauthorized(
            call(port, Route + "?api_key=" + apiKey, Some(question(sq(11))), auth = Seq.empty)
          )
          assert(stub.calls == 0)
          var forwarded = 0
          for ((name, auth, extra) <- consistent) withClue(name) {
            val public = call(port, body = Some(question(sq(12))), auth = auth)
            val other = call(port, jobPath, method = "GET", auth = auth, headers = extra)
            assert(
              (public.statusCode() == 401) == (other.statusCode() == 401),
              s"$name: public ${public.statusCode()} but /v1/jobs ${other.statusCode()}"
            )
            if (public.statusCode() == 401) unauthorized(public)
            else { projected(public); forwarded += 1 }
            info(s"auth variant '$name': public route ${public.statusCode()}")
          }
          assert(stub.calls == forwarded)
          // Header names are case-insensitive in HTTP; the canonical key still works.
          projected(
            call(
              port,
              body = Some(question(sq(13))),
              auth = Seq.empty,
              headers =
                Seq("Content-Type" -> "application/json", "authorization" -> s"Bearer $apiKey")
            )
          )
          // The API key never opens the internal route on query-api; the internal token does,
          // with the internal route's own (wider) topK limit.
          val before = stub.calls
          unauthorized(call(port, InternalRoute, Some(question(sq(14), Some(50)))))
          assert(stub.calls == before)
          val internal = call(
            port,
            InternalRoute,
            Some(question(sq(15), Some(50))),
            auth = Seq("Bearer " + internalToken)
          )
          assert(internal.statusCode() == 200, internal.body())
          assert(stub.last.json("topK").num == 50)
          badRequest(post(port, question(sq(16), Some(50))))
          assertClean(metricsText(port), "/metrics")
        }
      }
    }
    assertLogsClean(logs)
  }

  test(
    "public limits are exact at their boundaries, rejected bodies never reach semantic-service, and accepted ones are forwarded unchanged"
  ) {
    val emoji = "😀" // one code point, two UTF-16 units, four UTF-8 bytes
    val e1000 = emoji * 1000
    def filters(n: Int, value: String = "v"): ujson.Obj =
      ujson.Obj.from((1 to n).map(i => s"f$i" -> ujson.Str(value)))
    def body(fields: (String, ujson.Value)*): String = ujson.Obj.from(fields).render()
    val q = ujson.Str(sq(20))
    val wideButSmall = body("question" -> e1000, "filters" -> ujson.Obj("f" -> e1000))
    require(wideButSmall.length < 8192 && wideButSmall.getBytes(UTF_8).length < 8192)

    // (body, expected forwarded question, topK, filters)
    val accepted: Vector[(String, String, String, Int, Option[ujson.Value])] = Vector(
      ("topK 1", body("question" -> q, "topK" -> 1), sq(20), 1, None),
      ("topK 20", body("question" -> q, "topK" -> 20), sq(20), 20, None),
      ("default topK", body("question" -> q), sq(20), 20, None),
      (
        "1000 ASCII",
        body("question" -> ("a" * 990 + Sentinel.take(10))),
        "a" * 990 + Sentinel.take(10),
        20,
        None
      ),
      ("1000 two-byte", body("question" -> "é" * 1000), "é" * 1000, 20, None),
      ("1000 emoji", body("question" -> e1000), e1000, 20, None),
      ("padded question", body("question" -> s"  ${sq(21)}  "), s"  ${sq(21)}  ", 20, None),
      (
        "16 filters",
        body("question" -> q, "filters" -> filters(16)),
        sq(20),
        20,
        Some(filters(16))
      ),
      (
        "1000 code-point filter value",
        body("question" -> q, "filters" -> ujson.Obj("f" -> e1000)),
        sq(20),
        20,
        Some(ujson.Obj("f" -> e1000))
      ),
      ("8192 bytes", padTo(body("question" -> q), 8192), sq(20), 20, None),
      ("8192 multi-byte bytes", padTo(wideButSmall, 8192), e1000, 20, Some(ujson.Obj("f" -> e1000)))
    )

    val rejected: Vector[(String, String)] = Vector(
      "topK 21" -> body("question" -> q, "topK" -> 21),
      "topK 0" -> body("question" -> q, "topK" -> 0),
      "topK -1" -> body("question" -> q, "topK" -> -1),
      "topK -0" -> s"""{"question":"${sq(20)}","topK":-0}""",
      "topK huge" -> s"""{"question":"${sq(20)}","topK":99999999999999999999}""",
      "topK 1e400" -> s"""{"question":"${sq(20)}","topK":1e400}""",
      "topK string" -> body("question" -> q, "topK" -> "5"),
      "topK fraction" -> body("question" -> q, "topK" -> 5.5),
      "topK just above 20" -> s"""{"question":"${sq(20)}","topK":20.000001}""",
      "topK boolean" -> body("question" -> q, "topK" -> true),
      "topK array" -> body("question" -> q, "topK" -> ujson.Arr(5)),
      "empty question" -> body("question" -> ""),
      "blank question" -> body("question" -> "   "),
      "control whitespace" -> body("question" -> "\t\n\r "),
      "1001 ASCII" -> body("question" -> ("a" * 991 + Sentinel.take(10))),
      "1001 emoji" -> body("question" -> (e1000 + emoji)),
      "numeric question" -> body("question" -> 123),
      "null question" -> body("question" -> ujson.Null),
      "array question" -> body("question" -> ujson.Arr(sq(20))),
      "missing question" -> body("topK" -> 3),
      "17 filters" -> body("question" -> q, "filters" -> filters(17)),
      "empty filter key" -> body("question" -> q, "filters" -> ujson.Obj("" -> "v")),
      "1001 filter value" -> body("question" -> q, "filters" -> ujson.Obj("f" -> (e1000 + emoji))),
      "numeric filter value" -> body("question" -> q, "filters" -> ujson.Obj("f" -> 1)),
      "nested filter value" -> body("question" -> q, "filters" -> ujson.Obj("f" -> ujson.Obj())),
      "filters array" -> body("question" -> q, "filters" -> ujson.Arr("f")),
      "filters string" -> body("question" -> q, "filters" -> "f=v"),
      "unknown field" -> body("question" -> q, "includeVectors" -> true),
      "model field" -> body("question" -> q, "model" -> "other-model"),
      "hits field" -> body("question" -> q, "hits" -> ujson.Arr()),
      "case-variant field" -> body("Question" -> q),
      "lower-case topk" -> body("question" -> q, "topk" -> 50),
      "8193 bytes" -> padTo(body("question" -> q), 8193),
      "8193 multi-byte bytes" -> padTo(wideButSmall, 8193),
      "form encoded" -> s"question=$Sentinel",
      "empty body" -> "",
      "truncated" -> s"""{"question":"${sq(20)}"""",
      "JSON null" -> "null",
      "JSON array" -> s"""["${sq(20)}"]""",
      "JSON string" -> s""""${sq(20)}"""",
      "JSON number" -> "42",
      "trailing garbage" -> (body("question" -> q) + s" {$Sentinel}")
    )

    val (_, logs) = capturing {
      withStub { stub =>
        withService("query-api", remoteEnv(stub)) { port =>
          var ok = 0
          var bad = 0
          for ((name, content, fq, k, f) <- accepted) withClue(name) {
            val before = stub.calls
            val reply = projected(post(port, content))
            ok += 1
            assert(stub.calls == before + 1, "one accepted request is forwarded exactly once")
            val sent = stub.last.json
            assert(sent.obj.keySet.subsetOf(Set("question", "topK", "filters")), sent.render())
            assert(sent("question").str == fq)
            assert(sent("topK").num == k)
            f match {
              case Some(expected) => assert(sent("filters") == expected)
              case None =>
                assert(sent.obj.get("filters").forall(_.obj.isEmpty), sent.render())
            }
            assert(reply("hits").arr.map(_("key").str) == Vector("synthetic-p40t-hit-1"))
          }
          val callsBefore = stub.calls
          for ((name, content) <- rejected) withClue(name) {
            badRequest(post(port, content)); bad += 1
          }
          // No query string is accepted, even one that only repeats body fields.
          for (path <- Vector(Route + "?topK=50", Route + "?question=" + Sentinel))
            withClue(path) { badRequest(call(port, path, Some(question(sq(22))))); bad += 1 }
          assert(stub.calls == callsBefore, "a rejected body reached semantic-service")
          // An empty query component carries no parameter; recorded only.
          val emptyQuery = call(port, Route + "?", Some(question(sq(22))))
          if (emptyQuery.statusCode() == 200) { projected(emptyQuery); ok += 1 }
          else { badRequest(emptyQuery); bad += 1 }
          info(s"empty query component '$Route?': ${emptyQuery.statusCode()}")
          assert(get(port, "/healthz").statusCode() == 200)

          // Contract-silent inputs: the reply must be 200 or a typed 4xx, never 5xx, and an accepted
          // reply must forward a value inside the public limits.
          val silent: Vector[(String, String, ujson.Value => Boolean)] = Vector(
            ("topK 5.0", s"""{"question":"${sq(23)}","topK":5.0}""", _("topK").num == 5),
            ("topK 1e1", s"""{"question":"${sq(23)}","topK":1e1}""", _("topK").num == 10),
            ("topK null", s"""{"question":"${sq(23)}","topK":null}""", _("topK").num == 20),
            ("filters null", s"""{"question":"${sq(23)}","filters":null}""", _ => true),
            ("filters empty", s"""{"question":"${sq(23)}","filters":{}}""", _ => true),
            (
              "duplicate topK low-high",
              s"""{"question":"${sq(23)}","topK":5,"topK":50}""",
              _("topK").num == 5
            ),
            (
              "duplicate topK high-low",
              s"""{"question":"${sq(23)}","topK":50,"topK":5}""",
              _("topK").num == 5
            ),
            (
              "duplicate question short-long",
              s"""{"question":"${sq(23)}","question":"${"b" * 1001}"}""",
              j => j("question").str.codePointCount(0, j("question").str.length) <= 1000
            ),
            (
              "duplicate question long-short",
              s"""{"question":"${"b" * 1001}","question":"${sq(23)}"}""",
              j => j("question").str.codePointCount(0, j("question").str.length) <= 1000
            ),
            ("lone surrogate", s"""{"question":"a\\ud800 ${sq(23)}"}""", _ => true)
          )
          for ((name, content, check) <- silent) withClue(name) {
            val before = stub.calls
            val reply = post(port, content)
            if (reply.statusCode() == 200) {
              projected(reply); ok += 1
              assert(stub.calls == before + 1)
              val sent = stub.last.json
              assert(sent("topK").num >= 1 && sent("topK").num <= 20, sent.render())
              assert(check(sent), sent.render())
            } else {
              typedError(reply, 400, Set("INVALID_REQUEST"), Some(false)); bad += 1
              assert(stub.calls == before)
            }
            info(s"contract-silent input '$name': ${reply.statusCode()}")
          }
          for (
            (name, headers) <- Vector(
              "text/plain" -> Seq("Content-Type" -> "text/plain"),
              "no content type" -> Seq.empty,
              "form content type" -> Seq("Content-Type" -> "application/x-www-form-urlencoded")
            )
          ) withClue(name) {
            val reply = call(port, body = Some(question(sq(24))), headers = headers)
            if (reply.statusCode() == 200) { projected(reply); ok += 1 }
            else {
              assert(Set(400, 415)(reply.statusCode()), reply.body())
              typedError(reply, reply.statusCode(), Set.empty, Some(false))
              if (reply.statusCode() == 400) bad += 1
            }
            info(s"content type '$name': ${reply.statusCode()}")
          }
          // Other methods never run the route.
          for (method <- Vector("GET", "PUT", "DELETE", "PATCH")) withClue(method) {
            val before = stub.calls
            val reply = call(port, method = method, body = Some(question(sq(25))))
            assert(reply.statusCode() >= 400 && reply.statusCode() < 500, reply.body())
            assert(stub.calls == before)
          }
          // A question-bearing unknown path is labelled, not echoed, in metrics.
          assert(post(port, question(sq(26))).statusCode() == 200); ok += 1
          call(port, s"/v1/semantic/$Sentinel", Some(question(sq(27))))
          val text = metricsText(port)
          assertClean(text, "/metrics")
          assert(routeCount(text, 200) == ok, text)
          assert(routeCount(text, 400) == bad, text)
        }
      }
    }
    assertLogsClean(logs)
  }

  test("the 8 KiB body bound cannot be bypassed with chunked transfer or an oversize stream") {
    val (_, logs) = capturing {
      withStub { stub =>
        withService("query-api", remoteEnv(stub)) { port =>
          val small = call(port, body = Some(question(sq(30))), chunked = true)
          assert(small.statusCode() < 500, small.body())
          info(s"chunked 8,192-byte-or-less valid body: ${small.statusCode()}")
          val callsAfterSmall = stub.calls
          val over = call(port, body = Some(padTo(question(sq(31)), 8193)), chunked = true)
          assert(over.statusCode() >= 400 && over.statusCode() < 500, over.body())
          assert(over.statusCode() != 200)
          val huge = post(port, padTo(question(sq(32)), 70000))
          assert(huge.statusCode() >= 400 && huge.statusCode() < 500, huge.body().take(200))
          val hugeChunked = call(port, body = Some(padTo(question(sq(33)), 70000)), chunked = true)
          assert(hugeChunked.statusCode() >= 400 && hugeChunked.statusCode() < 500)
          for (r <- Vector(over, huge, hugeChunked)) assertClean(r.body(), "a body-limit reply")
          assert(stub.calls == callsAfterSmall, "an oversize body reached semantic-service")
          assert(get(port, "/healthz").statusCode() == 200)
          projected(post(port, question(sq(34))))
        }
      }
    }
    assertLogsClean(logs)
  }

  /** Warms the JVM's HTTP path on a separate process-local server so timed windows are short. */
  private def warmUp(): Unit = withService("query-api", baseEnv()) { port =>
    for (i <- 1 to 30) post(port, question(sq(900 + i % 3)))
    metricsText(port)
  }

  test(
    "rate limit over real HTTP with a tiny burst: exact admissions, typed retryable 429 with Retry-After, ordering, other routes and metrics"
  ) {
    warmUp()
    val rateEnv = baseEnv(
      "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND" -> "1",
      "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST" -> "3"
    )
    val (_, logs) = capturing {
      withService("query-api", rateEnv) { port =>
        val good = question(sq(40), Some(2))
        // 401s come before the limiter and consume nothing.
        for (_ <- 1 to 5) unauthorized(post(port, good, auth = Seq("Bearer " + internalToken)))
        val t0 = System.nanoTime()
        val firstThree = (1 to 3).map(_ => post(port, good))
        val afterAdmitted = metricsText(port)
        val throttled = (1 to 5).map(_ => post(port, good))
        // While the bucket is empty: the limiter runs before validation, after authentication.
        val invalidWhileEmpty = Vector(
          post(port, question(sq(41), Some(21))),
          post(port, "not json " + Sentinel),
          call(port, Route + "?topK=50", Some(good))
        )
        val wrongKeyWhileEmpty = post(port, good, auth = Seq("Bearer " + internalToken))
        val spoofed = call(
          port,
          body = Some(good),
          headers = Seq("Content-Type" -> "application/json", "X-Forwarded-For" -> "203.0.113.9")
        )
        val variants = Vector(
          Route + "/",
          "/V1/semantic/retrieve",
          "/v1//semantic/retrieve",
          "/v1/semantic/./retrieve",
          "/v1/semantic/retrieve%2F",
          "/v1/semantic/RETRIEVE"
        ).map(path => path -> call(port, path, Some(good)))
        val afterThrottled = metricsText(port)
        val window = (System.nanoTime() - t0) / 1000000
        assert(
          window < 1000,
          s"the exhausted-bucket window took $window ms; at 1 token/s the counts are only exact under 1 s"
        )

        firstThree.foreach(projected)
        val throttledAll = throttled ++ invalidWhileEmpty :+ spoofed
        val retryAfter = throttledAll.map { r =>
          typedError(r, 429, Set("RATE_LIMITED"), Some(true))
          val value =
            header(r, "Retry-After").getOrElse(fail("429 RATE_LIMITED without Retry-After"))
          assert(value.matches("[0-9]+"), s"Retry-After must be whole seconds: $value")
          value.toInt
        }
        assert(retryAfter.forall(s => s >= 1 && s <= 2), retryAfter)
        unauthorized(wrongKeyWhileEmpty)
        for ((path, r) <- variants) withClue(path) {
          assert(r.statusCode() != 200, s"$path bypassed the empty bucket")
          assert(r.statusCode() < 500, r.body())
          info(s"path variant '$path' with an empty bucket: ${r.statusCode()}")
        }
        val variant429 = variants.count(_._2.statusCode() == 429)
        // 429s never reach the embedder.
        for (m <- Vector("embedding_cache_hits_total", "embedding_cache_misses_total"))
          assert(metric(afterAdmitted, m) == metric(afterThrottled, m), m)

        // After Retry-After seconds a request is admitted again.
        Thread.sleep(retryAfter.last * 1000L + 100)
        projected(post(port, good))

        // Other routes are not behind the semantic limiter.
        val others = Vector(
          get(port, "/healthz"),
          get(port, "/metrics"),
          get(port, jobPath),
          call(port, InternalRoute, Some(good), auth = Seq("Bearer " + internalToken))
        )
        others.foreach(r => assert(r.statusCode() != 429, r.body()))
        assert(others.take(2).forall(_.statusCode() == 200))
        assert(others(2).statusCode() == 404)
        val query = call(
          port,
          "/v1/query",
          Some(
            """{"question":"Synthetic fixture: publication count for A","output":{"includeScores":false}}"""
          ),
          headers =
            Seq("Content-Type" -> "application/json", "Idempotency-Key" -> "p40t-rate-query")
        )
        assert(Set(200, 202)(query.statusCode()), query.body())

        val text = metricsText(port)
        val n429 = throttledAll.size + variant429
        assert(metric(text, "api_rate_limited_total").contains(n429.toDouble), text)
        assert(routeCount(text, 429) == n429, text)
        assert(routeCount(text, 200) == 4, "three burst admissions and one after Retry-After")
        assert(routeCount(text, 401) == 6, text)
        assert(metric(text, "embedding_cache_misses_total").exists(_ >= 1))
        assertClean(text, "/metrics")
      }
    }
    assertLogsClean(logs)
  }

  test(
    "a concurrent burst over real HTTP admits exactly the configured burst and counts every 429"
  ) {
    warmUp()
    val env = baseEnv(
      "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND" -> "1",
      "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST" -> "5"
    )
    val (_, logs) = capturing {
      withService("query-api", env) { port =>
        val pool = Executors.newFixedThreadPool(16)
        val gate = new CountDownLatch(1)
        try {
          val started = System.nanoTime()
          val futures = (1 to 40).map { i =>
            pool.submit(() => {
              gate.await()
              post(port, question(sq(50 + i % 4))).statusCode()
            })
          }
          gate.countDown()
          val statuses = futures.map(_.get(20, TimeUnit.SECONDS))
          val elapsed = (System.nanoTime() - started) / 1000000
          assert(elapsed < 1000, s"burst took $elapsed ms; exact only under 1 s at 1 token/s")
          assert(statuses.count(_ == 200) == 5, statuses)
          assert(statuses.count(_ == 429) == 35, statuses)
          val text = metricsText(port)
          assert(metric(text, "api_rate_limited_total").contains(35.0))
          assert(routeCount(text, 200) == 5 && routeCount(text, 429) == 35)
        } finally pool.shutdownNow()
      }
    }
    assertLogsClean(logs)
  }

  test(
    "default limits without an override admit a full burst of 100 and never exceed burst plus 50 per second"
  ) {
    val (_, logs) = capturing {
      withService("query-api", baseEnv()) { port =>
        val started = System.nanoTime()
        val first = (1 to 100).map(i => post(port, question(sq(60 + i % 5))).statusCode())
        assert(first.forall(_ == 200), first)
        val pool = Executors.newFixedThreadPool(16)
        try {
          val more = (1 to 400).map(i =>
            pool.submit(() => post(port, question(sq(60 + i % 5))).statusCode())
          )
          val statuses = more.map(_.get(30, TimeUnit.SECONDS))
          val elapsedSeconds = (System.nanoTime() - started) / 1e9
          val admitted = 100 + statuses.count(_ == 200)
          val bound = 100 + math.ceil(50 * elapsedSeconds).toInt + 1
          assert(admitted <= bound, s"admitted $admitted in $elapsedSeconds s; bound $bound")
          assert(statuses.forall(s => s == 200 || s == 429), statuses)
          val n429 = statuses.count(_ == 429)
          val text = metricsText(port)
          assert(metric(text, "api_rate_limited_total").contains(n429.toDouble))
          assert(routeCount(text, 200) == admitted && routeCount(text, 429) == n429)
          info(s"default limits: $admitted admitted, $n429 throttled in $elapsedSeconds s")
        } finally pool.shutdownNow()
      }
    }
    assertLogsClean(logs)
  }

  test(
    "invalid rate-limit and cache-size values refuse startup with exit 2 naming only the variable"
  ) {
    val bad = Vector("0", "-1", "p40tbadvalue", "99999999999999999999999")
    val cases =
      (for {
        name <- Vector(
          "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_PER_SECOND",
          "SCHOLARCHAIN_SEMANTIC_RATE_LIMIT_BURST"
        )
        value <- bad
      } yield ("query-api", name, value)) ++
        bad.map(v => ("semantic-service", "SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES", v))
    for ((role, name, value) <- cases) withClue(s"$role $name=$value") {
      val (result, output) = capturing(launch(role, baseEnv(name -> value)))
      result match {
        case Right(service) => service.close(); fail("an invalid value was accepted")
        case Left(code)     => assert(code == 2)
      }
      assert(output.contains("invalid-service-configuration:" + name), output)
      assert(!output.contains("p40tbadvalue") && !output.contains("99999999999999999999999"))
    }
  }

  test(
    "the reply drops every extra downstream field, including one carrying the question, and the forwarded call uses only the internal token"
  ) {
    val wide =
      s"""{"hits":[{"key":"synthetic-p40t-hit-1","distance":0.125,"metadata":{"source":"synthetic-p40t"},"vector":[0.1,0.2],"text":"$Sentinel echoed question","score":0.9},{"key":"synthetic-p40t-hit-2","distance":0.5,"metadata":{},"question":"$Sentinel"}],"model":{"modelId":"synthetic-p40t-model","version":"v1","dimension":8,"endpoint":"http://internal.invalid/$Sentinel","inputType":"query"},"question":"$Sentinel","debug":{"internalUrl":"http://internal.invalid"},"usage":{"tokens":7},"cache":"miss"}"""
    val (_, logs) = capturing {
      withStub { stub =>
        stub.reply = stub.Reply(200, wide)
        withService("query-api", remoteEnv(stub)) { port =>
          val reply = call(
            port,
            body = Some(question(sq(70), Some(2))),
            headers = Seq(
              "Content-Type" -> "application/json",
              "X-Request-Id" -> "request-p40t-projection",
              "X-Private-Canary" -> "p40t-private-header-canary"
            )
          )
          val json = projected(reply)
          assert(
            json == ujson.read(
              """{"hits":[{"key":"synthetic-p40t-hit-1","distance":0.125,"metadata":{"source":"synthetic-p40t"}},{"key":"synthetic-p40t-hit-2","distance":0.5,"metadata":{}}],"model":{"modelId":"synthetic-p40t-model","version":"v1","dimension":8}}"""
            )
          )
          assertClean(reply.body() + reply.headers().map().toString, "the public reply")
          assert(!reply.body().contains("internal.invalid"))
          assert(stub.calls == 1)
          val sent = stub.last
          assert(sent.headers.get("authorization").contains(Vector("Bearer " + internalToken)))
          assert(!sent.headers.values.flatten.exists(_.contains(apiKey)), "API key forwarded")
          assert(!sent.headers.contains("x-private-canary"), "client header forwarded")
          assert(sent.headers.get("x-trace-id").contains(Vector(Trace)))
          assert(sent.query.isEmpty)
          assert(sent.json == ujson.read(s"""{"question":"${sq(70)}","topK":2}"""), sent.body)
          assertClean(metricsText(port), "/metrics")
        }
      }
    }
    assertLogsClean(logs)
  }

  test(
    "a downstream reply with more hits than the forwarded topK is passed through projected, never widened in fields"
  ) {
    // Contract note: the OpenAPI describes hits as "At most the forwarded topK hits, as returned
    // by the vector store". Whether the public route must also truncate a misbehaving downstream is
    // not stated, so this test records the count and checks only the field projection.
    val five = (1 to 5)
      .map(i =>
        s"""{"key":"synthetic-p40t-hit-$i","distance":0.$i,"metadata":{},"text":"$Sentinel"}"""
      )
      .mkString("[", ",", "]")
    withStub { stub =>
      stub.reply =
        stub.Reply(200, s"""{"hits":$five,"model":{"modelId":"m","version":"v1","dimension":8}}""")
      withService("query-api", remoteEnv(stub)) { port =>
        val reply = post(port, question(sq(75), Some(2)))
        info(s"downstream returned 5 hits for topK 2; public status ${reply.statusCode()}")
        if (reply.statusCode() == 200) {
          val keys = projected(reply)("hits").arr.map(_("key").str).toVector
          info(s"public reply carried ${keys.size} hits for topK 2")
          assert(keys == (1 to keys.size).map(i => s"synthetic-p40t-hit-$i").toVector)
          assertClean(reply.body(), "the public reply")
        } else typedError(reply, 502, Set.empty)
      }
    }
  }

  test(
    "downstream failures map to typed errors without leaking the downstream body, URL or question"
  ) {
    val scenarios: Vector[(String, Option[(Int, String, Long)], Int, Set[String])] = Vector(
      (
        "503",
        Some((503, s"""{"error":"$Sentinel down"}""", 0L)),
        503,
        Set("SERVICE_UNAVAILABLE", "CIRCUIT_OPEN")
      ),
      ("504", Some((504, s"""{"error":"$Sentinel slow"}""", 0L)), 504, Set("DOWNSTREAM_TIMEOUT")),
      (
        "transport timeout",
        Some((200, StubSemantic.goodBody, 2500L)),
        504,
        Set("DOWNSTREAM_TIMEOUT")
      ),
      ("downstream 429", Some((429, s"""{"error":"$Sentinel busy"}""", 0L)), 429, Set("THROTTLED")),
      ("non-JSON 200", Some((200, s"<html>$Sentinel</html>", 0L)), 502, Set.empty),
      ("array 200", Some((200, s"""["$Sentinel"]""", 0L)), 502, Set.empty),
      (
        "hits not array",
        Some(
          (200, s"""{"hits":"$Sentinel","model":{"modelId":"m","version":"v","dimension":8}}""", 0L)
        ),
        502,
        Set.empty
      ),
      (
        "hit without distance",
        Some(
          (
            200,
            s"""{"hits":[{"key":"$Sentinel","metadata":{}}],"model":{"modelId":"m","version":"v","dimension":8}}""",
            0L
          )
        ),
        502,
        Set.empty
      ),
      ("downstream 401", Some((401, s"""{"error":"$Sentinel"}""", 0L)), 502, Set.empty),
      ("connection refused", None, 502, Set("DOWNSTREAM_FAILURE", "CIRCUIT_OPEN"))
    )
    val (_, logs) = capturing {
      for ((name, reply, status, codes) <- scenarios) withClue(name) {
        withStub { stub =>
          reply.foreach((s, b, d) => stub.reply = stub.Reply(s, b, d))
          val env = remoteEnv(stub, "SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS" -> "800")
          if (reply.isEmpty) stub.close()
          withService("query-api", env) { port =>
            val started = System.nanoTime()
            val r = post(port, question(sq(80)))
            val ms = (System.nanoTime() - started) / 1000000
            val acceptable =
              if (name == "connection refused") Set(502, 503) else Set(status)
            assert(acceptable(r.statusCode()), s"$name -> ${r.statusCode()} ${r.body()}")
            typedError(r, r.statusCode(), codes)
            if (name == "downstream 429")
              assert(header(r, "Retry-After").isEmpty, "THROTTLED carries no Retry-After")
            if (name == "transport timeout") assert(ms < 2400, s"timeout reply took $ms ms")
            if (reply.nonEmpty)
              assert(stub.calls == 1, s"attempts configured to 1, saw ${stub.calls}")
            val text = metricsText(port)
            assert(metric(text, "api_rate_limited_total").forall(_ == 0.0), text)
            assertClean(text, "/metrics")
            info(s"downstream $name: ${r.statusCode()} ${ujson.read(r.body())("error").str}")
          }
        }
      }
    }
    assertLogsClean(logs)
  }

  test(
    "in-process cache: N distinct questions repeated M times give exactly N embed misses on /metrics"
  ) {
    val (_, logs) = capturing {
      withService("query-api", baseEnv()) { port =>
        val start = metricsText(port)
        assert(metric(start, "embedding_cache_misses_total").contains(0.0), start)
        assert(metric(start, "embedding_cache_capacity").contains(1024.0), start)
        val n = 7
        val m = 5
        for (_ <- 1 to m; i <- 1 to n) projected(post(port, question(sq(100 + i))))
        // Other topK and filter values do not change the embedded text.
        projected(post(port, question(sq(101), Some(1))))
        projected(
          post(port, ujson.Obj("question" -> sq(102), "filters" -> ujson.Obj("f" -> "v")).render())
        )
        // Rejected and unauthenticated requests never reach the embedder.
        badRequest(post(port, question(sq(999), Some(21))))
        unauthorized(post(port, question(sq(998)), auth = Seq.empty))
        val text = metricsText(port)
        assert(metric(text, "embedding_cache_misses_total").contains(n.toDouble), text)
        assert(
          metric(text, "embedding_cache_hits_total").contains((n * (m - 1) + 2).toDouble),
          text
        )
        assert(metric(text, "embedding_cache_size").contains(n.toDouble), text)
        assert(metric(text, "embedding_cache_evictions_total").contains(0.0), text)
        assertClean(text, "/metrics")
      }
      // LRU with two entries: q1 miss, q2 miss, q1 hit, q3 miss (evicts q2), q1 hit, q2 miss
      // (evicts q3).
      withService("query-api", baseEnv("SCHOLARCHAIN_EMBEDDING_CACHE_MAX_ENTRIES" -> "2")) { port =>
        for (i <- Vector(1, 2, 1, 3, 1, 2)) projected(post(port, question(sq(200 + i))))
        val text = metricsText(port)
        assert(metric(text, "embedding_cache_misses_total").contains(4.0), text)
        assert(metric(text, "embedding_cache_hits_total").contains(2.0), text)
        assert(metric(text, "embedding_cache_evictions_total").contains(2.0), text)
        assert(metric(text, "embedding_cache_size").contains(2.0), text)
        assert(metric(text, "embedding_cache_capacity").contains(2.0), text)
      }
    }
    assertLogsClean(logs)
  }

  test(
    "two-process topology: query-api forwards to a real offline semantic-service whose cache misses equal the distinct questions"
  ) {
    val (_, logs) = capturing {
      withService("graph-service", baseEnv()) { graphPort =>
        withService("semantic-service", baseEnv()) { semanticPort =>
          val env = baseEnv(
            "SCHOLARCHAIN_GRAPH_BASE_URI" -> s"http://127.0.0.1:$graphPort",
            "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> s"http://127.0.0.1:$semanticPort",
            "SCHOLARCHAIN_INTERNAL_TOKEN" -> internalToken
          )
          withService("query-api", env) { port =>
            val n = 4
            val m = 3
            for (_ <- 1 to m; i <- 1 to n) projected(post(port, question(sq(300 + i), Some(5))))
            val semantic = metricsText(semanticPort)
            assert(metric(semantic, "embedding_cache_misses_total").contains(n.toDouble), semantic)
            assert(
              metric(semantic, "embedding_cache_hits_total").contains((n * (m - 1)).toDouble),
              semantic
            )
            val query = metricsText(port)
            assert(metric(query, "embedding_cache_misses_total").forall(_ == 0.0), query)
            assert(routeCount(query, 200) == n * m)
            assertClean(semantic + query, "/metrics")
          }
        }
      }
    }
    assertLogsClean(logs)
  }
}
