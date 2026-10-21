package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

/** Independent provider-wire fixtures use no network, API keys or live model. */
class IndependentOpenAIResponsesSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*

  test(
    "live wire request fixes selected model disables storage and tools and uses a strict supported schema"
  ) {
    val r = request()
    val rendered = OpenAIResponses.renderRequest(r, config)
    assert(rendered.isRight, rendered.toString)
    val wire = ujson.read(rendered.toOption.get)
    assert(wire("model").str == "gpt-6-luna")
    assert(wire("store") == ujson.Bool(false))
    assert(wire("max_output_tokens").num == config.budget.maxOutputTokensPerCall)
    assert(!wire.obj.contains("tools") || wire("tools").arr.isEmpty)
    val format = wire("text")("format")
    assert(format("type").str == "json_schema" && format("strict") == ujson.Bool(true))
    val schema = format("schema")
    def allKeys(v: ujson.Value): Set[String] = v match {
      case o: ujson.Obj => o.obj.keySet.toSet ++ o.obj.values.flatMap(allKeys)
      case a: ujson.Arr => a.arr.flatMap(allKeys).toSet
      case _            => Set.empty
    }
    assert(
      allKeys(schema).intersect(Set("allOf", "if", "then", "else", "const", "uniqueItems")).isEmpty
    )
    assert(schema("additionalProperties") == ujson.Bool(false))
    assert(schema("required").arr.map(_.str).toSet == schema("properties").obj.keySet.toSet)
    assert(!rendered.toOption.get.contains("Authorization"))
  }

  test(
    "completed provider envelope binds typed response and preserves measured reasoning and cached usage"
  ) {
    val r = request()
    val parsed = OpenAIResponses.parseResponse(http(envelope(r)), r, config)
    assert(parsed.isRight, parsed.toString)
    val result = parsed.toOption.get
    assert(result.response == response(r))
    assert(
      result.usage.inputTokens == 120 && result.usage.outputTokens == 40 && result.usage.totalTokens == 160
    )
    assert(result.usage.reasoningTokens == 10 && result.usage.cachedInputTokens == 20)
    assert(
      result.responseId == "resp_synthetic_independent" && result.resolvedModel == "gpt-6-luna"
    )
  }

  test(
    "refusal incomplete malformed and missing usage envelopes cannot become decisive responses"
  ) {
    val r = request()
    val original = envelope(r)
    val refusal = changed(original)(_("output")(0)("content") =
      ujson.Arr(ujson.Obj("type" -> "refusal", "refusal" -> "Synthetic refusal"))
    )
    val incomplete = changed(original)(_("status") = "incomplete")
    val missingUsage = changed(original)(_.obj.remove("usage"))
    val missingText = changed(original)(_("output") = ujson.Arr())
    Vector(refusal, incomplete, missingUsage, missingText).foreach(v =>
      assert(OpenAIResponses.parseResponse(http(v), r, config).isLeft)
    )
    assert(
      OpenAIResponses.parseResponse(ProviderHttpResponse(200, "{malformed", None), r, config).isLeft
    )
  }

  test(
    "provider usage must be integral nonnegative consistent and bounded by its parent counters"
  ) {
    val r = request()
    Vector(
      changed(envelope(r))(_("usage")("input_tokens") = -1),
      changed(envelope(r))(_("usage")("output_tokens") = 2.5),
      changed(envelope(r))(_("usage")("total_tokens") = 999),
      changed(envelope(r))(_("usage")("input_tokens_details")("cached_tokens") = 121),
      changed(envelope(r))(_("usage")("output_tokens_details")("reasoning_tokens") = 41)
    ).foreach(v => assert(OpenAIResponses.parseResponse(http(v), r, config).isLeft))
  }

  test(
    "strict adjudication validation rejects wrong identity citations extra fields and contradictory reasons through live envelopes"
  ) {
    val r = request()
    val invalid = Vector(
      response(r).copy(pairId = "resolution-pair:" + "0" * 64),
      response(r).copy(evidenceRefs = Vector("er-evidence:invented")),
      response(r).copy(reasonCodes = Vector("INSUFFICIENT_EVIDENCE")),
      response(r).copy(fieldRefs = Vector(r.evidence.head.ref + "#/absentField"))
    )
    invalid.foreach(a =>
      assert(OpenAIResponses.parseResponse(http(envelope(r, Some(a))), r, config).isLeft)
    )
    val extra = ujson.read(write(response(r))); extra("tools") = ujson.Arr("browse")
    val wrapped = changed(envelope(r))(_("output")(0)("content")(0)("text") = extra.render())
    assert(OpenAIResponses.parseResponse(http(wrapped), r, config).isLeft)
  }

  test(
    "HTTP errors and oversized response bodies fail without reflecting sensitive provider body text"
  ) {
    val r = request()
    val sentinel = "synthetic-secret-sentinel-DO-NOT-LOG"
    Vector(400, 401, 403, 429, 500, 503).foreach { status =>
      val parsed = OpenAIResponses.parseResponse(
        ProviderHttpResponse(status, sentinel, Some("req_safe")),
        r,
        config
      )
      assert(parsed.isLeft && !parsed.toString.contains(sentinel))
    }
    assert(
      OpenAIResponses
        .parseResponse(
          ProviderHttpResponse(200, "x" * (config.budget.maxResponseBytes + 1), None),
          r,
          config
        )
        .isLeft
    )
  }
  test("live request identity settings and wire byte bound reject mutations before transport") {
    val r = request()
    Vector(
      r.copy(requestHash = "0" * 64),
      r.copy(mode = "fake"),
      r.copy(model = "another-model"),
      r.copy(promptHash = "0" * 64),
      r.copy(generationSettings = r.generationSettings.updated("store", "true"))
    ).foreach { invalid =>
      assert(OpenAIResponses.renderRequest(invalid, config).isLeft)
    }
    val tiny = config.copy(budget = config.budget.copy(maxRequestBytes = 100))
    val tinyRequest = request(tiny)
    assert(OpenAIResponses.renderRequest(tinyRequest, tiny).isLeft)
  }

  test("local response limits remain enforced independently of the provider wire schema subset") {
    val r = request()
    val long =
      response(r).copy(rationale = "x" * (config.responseLimits.maxRationaleCharacters + 1))
    val wrongBounds =
      config.copy(responseLimits = config.responseLimits.copy(maxRationaleCharacters = 1))
    assert(OpenAIResponses.parseResponse(http(envelope(r, Some(long))), r, config).isLeft)
    val mismatch = intercept[IllegalArgumentException] { request(wrongBounds) }
    assert(mismatch.getMessage.contains("response limits"))
  }

  test("unselected model and unavailable price assumptions are refused rather than falling back") {
    assert(LiveProviderConfig.validate(config.copy(model = "another-model")).isLeft)
    assert(
      LiveProviderConfig
        .validate(config.copy(rateCard = config.rateCard.copy(inputMicrousdPerMillionTokens = 0)))
        .isLeft
    )
    val r = request()
    val wrongModel = changed(envelope(r))(_("model") = "another-model")
    assert(OpenAIResponses.parseResponse(http(wrongModel), r, config).isLeft)
  }

}
