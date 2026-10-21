package edu.uic.cs441.scholarchain.entityresolution

import java.nio.charset.StandardCharsets.UTF_8
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{write, writeJs}

/** Synthetic provider output only; no credentials or network operations. */
class ProviderResponseDiagnosticSpec extends AnyFunSuite {
  private val source = ResolutionConfig.example
  private val config = StrictJson
    .parse[LiveProviderConfig](ResourceText.read("adjudication/openai-live.example.v1.json"))
    .toOption
    .get
  private val a = ErTestData.work("conf/response-diagnostic/A")
  private val b = ErTestData.work("conf/response-diagnostic/B")
  private val input = ErTestData.input(a, b)
  private val candidate = ErTestData.comparison(a, b, input)
  private val request = OpenAIResponses
    .request(
      candidate,
      input,
      ResolutionPolicy.example,
      source,
      config,
      FeatureExtractor.extract(candidate, input, ResolutionPolicy.example),
      input.evidence
    )
    .toOption
    .get
  private val answer = AdjudicationResponse(
    Adjudication.responseSchema,
    request.requestHash,
    request.pairId,
    request.sourceId,
    request.targetId,
    request.inputEvidenceHash,
    request.policyHash,
    "abstain",
    Vector("INSUFFICIENT_EVIDENCE"),
    Vector.empty,
    "Synthetic ambiguous evidence.",
    0.5,
    Vector.empty
  )
  private def envelope(text: String): ProviderHttpResponse = ProviderHttpResponse(
    200,
    ujson
      .Obj(
        "id" -> "resp_synthetic_diagnostic",
        "model" -> config.model,
        "status" -> "completed",
        "output" -> ujson.Arr(
          ujson.Obj(
            "type" -> "message",
            "role" -> "assistant",
            "content" -> ujson.Arr(ujson.Obj("type" -> "output_text", "text" -> text))
          )
        ),
        "usage" -> ujson.Obj(
          "input_tokens" -> 10,
          "output_tokens" -> 5,
          "total_tokens" -> 15,
          "input_tokens_details" -> ujson.Obj("cached_tokens" -> 0),
          "output_tokens_details" -> ujson.Obj("reasoning_tokens" -> 0)
        )
      )
      .render(),
    None
  )

  test("strict validation reports a closed identity category with bounded identity booleans") {
    val text = write(answer.copy(requestHash = "f" * 64))
    val http = envelope(text)
    assert(
      OpenAIResponses.parseResponse(http, request, config) == Left(
        "PROVIDER_ADJUDICATION_IDENTITY_MISMATCH"
      )
    )
    val diagnostic = OpenAIResponses.responseDiagnostic(http, request, config)
    assert(diagnostic.validationCode == "PROVIDER_ADJUDICATION_IDENTITY_MISMATCH")
    assert(diagnostic.identityMatches("requestHash") == false)
    assert(diagnostic.identityMatches.filterNot(_._1 == "requestHash").values.forall(identity))
    assert(diagnostic.responseBytes == http.body.getBytes(UTF_8).length)
    assert(diagnostic.outputTextBytes.contains(text.getBytes(UTF_8).length))
    assert(diagnostic.responseSha256.matches("[a-f0-9]{64}"))
    assert(diagnostic.outputTextSha256.exists(_.matches("[a-f0-9]{64}")))
    assert(diagnostic.reasonCodesCount.contains(1))
    assert(diagnostic.rationaleCharacters.contains(answer.rationale.length))
  }
  test("untrusted model text and provider errors never appear in diagnostics") {
    val marker = "synthetic-DO-NOT-LOG-provider-content"
    val invalid = envelope("{\"private\":\"" + marker + "\"}")
    val diagnostic = OpenAIResponses.responseDiagnostic(invalid, request, config)
    assert(diagnostic.validationCode == "PROVIDER_ADJUDICATION_SCHEMA_OR_FORMAT")
    assert(!write(diagnostic).contains(marker))
    val refused =
      OpenAIResponses.responseDiagnostic(ProviderHttpResponse(401, marker, None), request, config)
    assert(refused.validationCode == "PROVIDER_HTTP_401")
    assert(refused.outputTextSha256.isEmpty && refused.identityMatches.isEmpty)
    assert(!write(refused).contains(marker))
    assert(Adjudication.safeResponseFailureCode(marker) == "SCHEMA_OR_FORMAT")
  }
  test("specific field and reason failures stay rejected and produce finite categories") {
    val cases = Vector(
      answer.copy(reasonCodes = Vector("SUPPORTED_SAME_IDENTITY")) -> "REASON_OUTCOME_MISMATCH",
      answer.copy(rationale =
        "x" * (config.responseLimits.maxRationaleCharacters + 1)
      ) -> "RATIONALE_INVALID",
      answer.copy(evidenceRefs = Vector("fabricated")) -> "EVIDENCE_REFS_INVALID"
    )
    cases.foreach { (response, code) =>
      val http = envelope(write(response))
      assert(
        OpenAIResponses.parseResponse(http, request, config) == Left(
          "PROVIDER_ADJUDICATION_" + code
        )
      )
      assert(
        OpenAIResponses
          .responseDiagnostic(http, request, config)
          .validationCode == "PROVIDER_ADJUDICATION_" + code
      )
    }
  }
  test("historical trace without diagnostic metadata remains readable") {
    val trace = LiveAttemptTrace(
      request.pairId,
      "ADJUDICATION_FAILED",
      1,
      false,
      request,
      None,
      Some("PROVIDER_ADJUDICATION_INVALID")
    )
    val json = writeJs(trace)
    json.obj.remove("diagnostic")
    assert(StrictJson.parse[LiveAttemptTrace](json.render()).contains(trace))
  }
}
