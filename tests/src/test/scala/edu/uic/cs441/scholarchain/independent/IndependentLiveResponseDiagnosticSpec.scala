package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.StableIds
import edu.uic.cs441.scholarchain.entityresolution.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}

/** No HTTP or credentials: these deliberately invalid model outputs are synthetic fixtures. */
class IndependentLiveResponseDiagnosticSpec extends AnyFunSuite {
  import IndependentLiveFixtures.*
  private val sentinel = "synthetic-private-value-DO-NOT-REFLECT"

  private def invalidCases(r: AdjudicationRequest): Vector[(String, AdjudicationResponse)] = {
    val original = response(r)
    Vector(
      "IDENTITY_MISMATCH" -> original.copy(pairId = sentinel),
      "OUTCOME_INVALID" -> original.copy(outcome = sentinel),
      "REASON_CODES_INVALID" -> original.copy(reasonCodes = Vector(sentinel)),
      "REASON_OUTCOME_MISMATCH" -> original.copy(reasonCodes = Vector("INSUFFICIENT_EVIDENCE")),
      "EVIDENCE_REFS_INVALID" -> original.copy(evidenceRefs = Vector(sentinel)),
      "EVIDENCE_REQUIRED" -> original.copy(evidenceRefs = Vector.empty),
      "FIELDS_REQUIRED" -> original.copy(fieldRefs = Vector.empty),
      "FIELD_CITATION_FORMAT" -> original.copy(fieldRefs = Vector(sentinel)),
      "POINTER_ESCAPE_INVALID" -> original.copy(fieldRefs =
        Vector(r.evidence.head.ref + "#/bad~3")
      ),
      "FIELD_NOT_FOUND" -> original.copy(fieldRefs = Vector(r.evidence.head.ref + "#/" + sentinel)),
      "ARRAY_INDEX_RANGE" -> original.copy(fieldRefs =
        Vector(r.evidence.head.ref + "#/authors/99999")
      ),
      "POINTER_SCALAR" -> original.copy(fieldRefs =
        Vector(r.evidence.head.ref + "#/title/missing")
      ),
      "RATIONALE_INVALID" -> original.copy(rationale = sentinel + "\u0000"),
      "CONFIDENCE_INVALID" -> original.copy(reportedConfidence = 1.1)
    )
  }

  test(
    "inner validation failures have distinct finite codes without echoing provider-controlled values"
  ) {
    val r = request()
    invalidCases(r).foreach { case (category, answer) =>
      val parsed = OpenAIResponses.parseResponse(http(envelope(r, Some(answer))), r, config)
      assert(parsed == Left("PROVIDER_ADJUDICATION_" + category), s"$category: $parsed")
      assert(!parsed.toString.contains(sentinel))
    }
    assert(Adjudication.safeResponseFailureCode(sentinel) == "SCHEMA_OR_FORMAT")
    assert(Adjudication.safeResponseFailureCode("PROVIDER_" + sentinel) == "SCHEMA_OR_FORMAT")
  }

  test("schema or malformed JSON stays rejected without surfacing raw parse exceptions") {
    val r = request()
    val extra = ujson.read(write(response(r)))
    extra(sentinel) = ujson.Str(sentinel)
    val bodies = Vector(extra.render(), "{" + sentinel, "{\"schemaVersion\":\"" + sentinel + "\"}")
    bodies.foreach { text =>
      val wrapped = changed(envelope(r))(_("output")(0)("content")(0)("text") = text)
      val parsed = OpenAIResponses.parseResponse(http(wrapped), r, config)
      assert(parsed == Left("PROVIDER_ADJUDICATION_SCHEMA_OR_FORMAT"), parsed.toString)
      assert(!parsed.toString.contains(sentinel))
    }
  }

  test(
    "diagnostics retain only hashes counts allowlisted outcome and fixed identity comparison keys"
  ) {
    val r = request()
    val answer =
      response(r).copy(pairId = sentinel, rationale = sentinel, fieldRefs = Vector(sentinel))
    val wrapped = http(envelope(r, Some(answer)))
    val diagnostic = OpenAIResponses.responseDiagnostic(wrapped, r, config)
    assert(diagnostic.validationCode == "PROVIDER_ADJUDICATION_IDENTITY_MISMATCH")
    assert(diagnostic.responseBytes == wrapped.body.getBytes(UTF_8).length)
    assert(diagnostic.responseSha256 == StableIds.sha256Hex(wrapped.body))
    val text = ujson.read(wrapped.body)("output")(0)("content")(0)("text").str
    assert(diagnostic.outputTextBytes.contains(text.getBytes(UTF_8).length))
    assert(diagnostic.outputTextSha256.contains(StableIds.sha256Hex(text)))
    assert(
      diagnostic.identityMatches.keySet == Set(
        "schemaVersion",
        "requestHash",
        "pairId",
        "sourceId",
        "targetId",
        "inputEvidenceHash",
        "policyHash"
      )
    )
    assert(!diagnostic.identityMatches("pairId"))
    assert(diagnostic.identityMatches.filterNot(_._1 == "pairId").values.forall(identity))
    assert(diagnostic.outcome.contains("accept"))
    assert(diagnostic.evidenceRefCount.contains(answer.evidenceRefs.size))
    assert(diagnostic.fieldRefCount.contains(1) && diagnostic.reasonCodesCount.contains(1))
    assert(diagnostic.rationaleCharacters.contains(sentinel.length))
    assert(!write(diagnostic).contains(sentinel))
    val badOutcome = http(envelope(r, Some(answer.copy(outcome = sentinel))))
    assert(OpenAIResponses.responseDiagnostic(badOutcome, r, config).outcome.isEmpty)
  }

  test("HTTP errors malformed envelopes and oversized bodies never expose model output fields") {
    val r = request()
    val wrapped = http(envelope(r, Some(response(r).copy(rationale = sentinel))), 401)
    val malformed = ProviderHttpResponse(200, "{" + sentinel, None)
    val oversized =
      ProviderHttpResponse(200, sentinel + ("x" * config.budget.maxResponseBytes), None)
    Vector(wrapped, malformed, oversized).foreach { body =>
      val diagnostic = OpenAIResponses.responseDiagnostic(body, r, config)
      assert(diagnostic.identityMatches.isEmpty && diagnostic.outcome.isEmpty)
      assert(diagnostic.outputTextBytes.isEmpty && diagnostic.outputTextSha256.isEmpty)
      assert(diagnostic.evidenceRefCount.isEmpty && diagnostic.fieldRefCount.isEmpty)
      assert(diagnostic.rationaleCharacters.isEmpty)
      assert(!write(diagnostic).contains(sentinel))
    }
  }

  test(
    "failed adjudication remains charged and diagnosable; corrected output uses the same ledger"
  ) {
    val cfg = config
    val l = ledger(cfg)
    val calls = new AtomicInteger(0)
    val transport = new OpenAITransport {
      def post(body: String, timeout: Int, maxBytes: Int): ProviderHttpResponse = {
        val r = read[AdjudicationRequest](ujson.read(body)("input").str)
        val answer =
          if (calls.incrementAndGet() == 1) response(r).copy(pairId = sentinel) else response(r)
        http(envelope(r, Some(answer)))
      }
    }
    val cache =
      Files.createTempDirectory("scholarchain-independent-response-diagnostics-").toRealPath()
    try {
      val runner = new LiveAdjudicator(cfg, transport, l, Some(cache))
      val failed = runner.adjudicate(request(cfg))
      assert(failed.status == "ADJUDICATION_FAILED" && failed.result.isEmpty)
      assert(failed.error.contains("PROVIDER_ADJUDICATION_IDENTITY_MISMATCH"))
      assert(
        failed.diagnostic.exists(_.validationCode == "PROVIDER_ADJUDICATION_IDENTITY_MISMATCH")
      )
      assert(!write(failed).contains(sentinel))
      assert(l.snapshot.attempts == 1 && !l.snapshot.fused && l.snapshot.unknownUsageAttempts == 0)
      assert(l.snapshot.observedInputTokens == 120 && l.snapshot.observedOutputTokens == 40)
      val valid = runner.adjudicate(request(cfg))
      assert(valid.status == "VALIDATED_LIVE" && valid.result.nonEmpty && valid.diagnostic.isEmpty)
      assert(calls.get() == 2 && l.snapshot.attempts == 2 && !l.snapshot.fused)
      assert(l.snapshot.observedInputTokens == 240 && l.snapshot.observedOutputTokens == 80)
      val replay = runner.adjudicate(request(cfg))
      assert(replay.status == "CACHE_HIT" && replay.result == valid.result)
      assert(calls.get() == 2 && l.snapshot.attempts == 2)
      assert(cfg.fingerprint == config.fingerprint)
    } finally l.close()
  }
}
