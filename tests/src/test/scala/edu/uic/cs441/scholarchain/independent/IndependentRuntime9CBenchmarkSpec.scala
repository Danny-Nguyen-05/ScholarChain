package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import org.scalatest.funsuite.AnyFunSuite

/** Literal expectations independent of the benchmark implementation's own expected-value fields. */
class IndependentRuntime9CBenchmarkSpec extends AnyFunSuite {
  private val expected = Vector(
    ("ranking", "ANSWERED", Some("distinctCoauthorCount" -> "3")),
    ("team", "ANSWERED", Some("maximumCoauthorsOnOnePaper" -> "2")),
    ("direct", "ANSWERED", Some("returnedCount" -> "2")),
    ("path", "ANSWERED", Some("hopCount" -> "4")),
    ("component", "ANSWERED", Some("publicationCount" -> "3")),
    ("community", "ANSWERED", Some("size" -> "3")),
    ("bridge", "ANSWERED", Some("crossCommunityDegree" -> "1")),
    ("temporal", "ANSWERED", Some("deltaDistinctCoauthors" -> "1")),
    ("topic", "ANSWERED", Some("distinctCoauthorCount" -> "2")),
    ("ambiguous", "ABSTAINED", None),
    ("unsupported", "UNSUPPORTED", None),
    ("injection", "UNSUPPORTED", None),
    ("institution", "ANSWERED", Some("distinctCoauthorCount" -> "2")),
    ("venue", "ANSWERED", Some("distinctCoauthorCount" -> "2")),
    ("disconnected", "ANSWERED", Some("pathStatus" -> "Disconnected"))
  )
  private def execute(question: String): ujson.Value = RuntimeWorkflowMain
    .execute(Vector("--question", question))
    .fold(reason => fail(reason), ujson.read(_))

  test("versioned benchmark covers all required operation classes and explicit enrichment cases") {
    val source = RuntimeBenchmark.load()
    assert(source("schemaVersion").str == "scholarchain.runtime-benchmark.v1")
    assert(source("fixture").str.toLowerCase.contains("synthetic"))
    val ids = source("cases").arr.map(_("id").str).toVector
    assert(ids.distinct == ids)
    assert(expected.map(_._1).forall(ids.contains))
    assert(source("limitations").arr.exists(_.str.toLowerCase.contains("offline")))
  }

  expected.foreach { (id, outcome, field) =>
    test(s"offline benchmark $id has its hand-derived outcome and checked stored value") {
      val entry = RuntimeBenchmark.questionCases.find(_("id").str == id).get
      val result = execute(entry("question").str)
      assert(result("audit")("outcome").str == outcome)
      if (outcome == "ANSWERED") {
        val answer = upickle.default.read[AnswerResponse](result("answer"))
        assert(DomainValidation.check(answer).isRight)
        assert(
          answer.claims.nonEmpty && answer.claims.forall(
            _.verificationStatus == VerificationStatus.Verified
          )
        )
        field.foreach { (name, value) =>
          assert(
            answer.claims.exists(
              _.runtime.exists(
                _.values.exists(v =>
                  v.field == name && (v.number.contains(value) || v.text.contains(value))
                )
              )
            )
          )
        }
        assert(result("audit")("answerHash").str == StableIds.sha256Hex(CoreJson.compact(answer)))
        def researcher(name: String): String =
          StableIds.researcherIdFromDblpName("module-g1-v1", name).toOption.get
        val typed = answer.claims.flatMap(_.runtime)
        if (id == "component")
          assert(
            typed.exists(
              _.values.exists(v =>
                v.field == "componentId" &&
                  v.text.contains("component:" + StableIds.sha256Hex("ag"))
              )
            )
          )
        if (id == "path")
          assert(
            typed.exists(
              _.values.exists(v =>
                v.field == "orderedResearcherIds" &&
                  v.ids.contains(Vector("A", "C", "D", "F", "G").map(researcher))
              )
            )
          )
        if (id == "direct")
          assert(
            typed.exists(
              _.values.exists(v =>
                v.field == "coauthorIds" &&
                  v.ids.exists(_.toSet == Set(researcher("B"), researcher("C")))
              )
            )
          )
        if (id == "community") {
          assert(
            typed.exists(t =>
              t.subjectIds == Vector(researcher("C")) &&
                t.values.exists(v => v.field == "size" && v.number.contains("3"))
            )
          )
          assert(
            typed.exists(t =>
              t.subjectIds == Vector(researcher("D")) &&
                t.values.exists(v => v.field == "size" && v.number.contains("4"))
            )
          )
          assert(answer.summary.toLowerCase.contains("iteration-limited"))
        }
        if (Set("ranking", "team", "topic", "institution", "venue", "bridge")(id)) {
          assert(answer.summary.toLowerCase.contains("scope"))
          assert(answer.summary.toLowerCase.contains("truncat"))
        }

      } else {
        assert(!result.obj.contains("answer") || result("answer")("claims").arr.isEmpty)
        if (id == "ambiguous") {
          val candidates = result("candidates").arr.toVector.map(value =>
            upickle.default.read[ResearcherCandidate](value)
          )
          val expectedCandidates = Set("Name 0001", "Name 0002").map { name =>
            StableIds.researcherIdFromDblpName("module-g1-v1", name).toOption.get -> name
          }
          assert(candidates.size == 2)
          assert(candidates.map(c => c.researcherId -> c.displayName).toSet == expectedCandidates)
          val audit = upickle.default.read[RuntimeAuditEnvelope](result("audit"))
          assert(audit.record.forall(_.resolvedResearcherIds.isEmpty))
          assert(!audit.modelUsage.exists(_.promptVersion.startsWith("synthesis")))
        }
      }
    }
  }
  test("fake-backed CLI supports evidence-only JSON without proposing answer claims") {
    val question =
      RuntimeBenchmark.questionCases.find(_("id").str == "component").get("question").str
    val result = RuntimeWorkflowMain
      .execute(Vector("--question", question, "--evidence-only"))
      .fold(reason => fail(reason), ujson.read(_))
    assert(result.obj.contains("evidence"))
    assert(!result.obj.contains("answer"))
    assert(result("audit")("outcome").str == "EVIDENCE_ONLY")
    val audit = upickle.default.read[RuntimeAuditEnvelope](result("audit"))
    assert(audit.evidenceOnly)
    assert(audit.record.get.attemptedClaims.isEmpty)
    assert(!audit.modelUsage.exists(_.promptVersion.startsWith("synthesis")))
  }
  test("CLI refuses live flags and incomplete arguments instead of constructing provider clients") {
    assert(RuntimeWorkflowMain.execute(Vector("--live")).isLeft)
    assert(RuntimeWorkflowMain.execute(Vector("--question")).isLeft)
    assert(RuntimeWorkflowMain.execute(Vector("--question", "")).isLeft)
    assert(RuntimeWorkflowMain.execute(Vector("--question", "x", "--region", "us-east-2")).isLeft)
  }
}
