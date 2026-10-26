package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import scala.io.Source
import upickle.default.{read, write}

/** Synthetic records exercise compatibility and exact fields, never real researcher claims. */
class RuntimeContractSpec extends AnyFunSuite {
  private def resource(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    assert(stream != null, s"missing resource $name")
    val source = Source.fromInputStream(stream, "UTF-8")
    try source.mkString
    finally source.close()
  }
  private def config =
    RuntimeConfigLoader.fromJson(resource("/scholarchain.runtime-config.v1.json")).toOption.get
  private val typed = TypedAnswerClaim(
    RuntimeClaimType.Metric,
    Vector(Fixtures.orcidResearcher.researcherId),
    Vector(RuntimeClaimValue("distinctCoauthorCount", number = Some("9007199254740993"))),
    Vector("since-2015"),
    "metric-v1"
  )

  test("frozen runtime-related v1 wire records parse without optional runtime fields") {
    assert(read[QueryPlan](resource("/wire/query-plan.json")).runtime.isEmpty)
    assert(read[EvidenceItem](resource("/wire/evidence-item.json")).runtime.isEmpty)
    assert(read[EvidenceBundle](resource("/wire/evidence-bundle.json")).runtime.isEmpty)
    assert(read[AnswerClaim](resource("/wire/answer-claim.json")).runtime.isEmpty)
  }
  test("optional query payload converts without changing the legacy plan or researcher spelling") {
    val old = read[QueryPlan](resource("/wire/query-plan.json"))
    val options = read[RuntimeQueryOptions](resource("/wire/runtime-query-options.json"))
    val enriched = old.copy(runtime = Some(options))
    assert(read[QueryPlan](write(enriched)) == enriched)
    assert(enriched.copy(runtime = None) == old)
    assert(enriched.runtime.get.researcherNames == Vector("Name 0001"))
    assert(DomainValidation.check(enriched).isRight)
  }
  test(
    "typed claims preserve exact integers beyond binary floating point and legacy claim fields"
  ) {
    val old = read[AnswerClaim](resource("/wire/answer-claim.json"))
    val enriched = old.copy(runtime = Some(typed))
    assert(read[AnswerClaim](write(enriched)) == enriched)
    assert(enriched.copy(runtime = None) == old)
    assert(enriched.runtime.get.values.head.number.contains("9007199254740993"))
    assert(DomainValidation.check(enriched).isRight)
    val wire = read[TypedAnswerClaim](resource("/wire/runtime-typed-claim.json"))
    assert(wire.values.head.number == typed.values.head.number)
  }
  test("new per-claim verdicts map explicitly while overall abstention remains ABSTAINED") {
    assert(ClaimVerdict.Verified.verificationStatus == VerificationStatus.Verified)
    assert(
      ClaimVerdict.PartiallySupported.verificationStatus == VerificationStatus.PartiallyVerified
    )
    assert(ClaimVerdict.Unsupported.verificationStatus == VerificationStatus.Rejected)
    assert(ClaimVerdict.Conflicting.verificationStatus == VerificationStatus.Rejected)
    val rejected = ClaimVerificationResult("bad", ClaimVerdict.Conflicting, Vector("wrong-count"))
    assert(
      VerificationResult(
        Vector(rejected),
        Vector(Fixtures.claim),
        abstained = false
      ).overallStatus == VerificationStatus.Rejected
    )
    assert(
      VerificationResult(
        Vector(rejected),
        Vector(Fixtures.claim),
        abstained = true
      ).overallStatus == VerificationStatus.Abstained
    )
    assert(write(ClaimVerdict.PartiallySupported) == "\"PARTIALLY_SUPPORTED\"")
  }
  test(
    "mixed claim verdicts remain partially verified and rejected attempted claims survive audit serialization"
  ) {
    val verification = VerificationResult(
      Vector(
        ClaimVerificationResult("ok", ClaimVerdict.Verified, Vector.empty),
        ClaimVerificationResult("bad", ClaimVerdict.Unsupported, Vector("unknown-evidence"))
      ),
      Vector(Fixtures.claim),
      false
    )
    assert(verification.overallStatus == VerificationStatus.PartiallyVerified)
    val audit = AuditRecord(
      "q",
      "trace",
      Fixtures.plan,
      Vector.empty,
      Vector(Fixtures.evidence.evidenceId),
      Vector("metric-policy"),
      Vector(Fixtures.plan.provenance.runId),
      Vector.empty,
      12,
      Vector(Fixtures.claim),
      verification,
      "a" * 64
    )
    assert(read[AuditRecord](write(audit)).attemptedClaims == Vector(Fixtures.claim))
    assert(read[AuditRecord](write(audit)).verification.rejectedClaims == Vector(Fixtures.claim))
  }
  test("domain validation rejects malformed optional payload rather than ignoring it") {
    val old = read[AnswerClaim](resource("/wire/answer-claim.json"))
    assert(
      DomainValidation
        .check(
          old.copy(runtime =
            Some(typed.copy(values = Vector(RuntimeClaimValue("count", number = Some("NaN")))))
          )
        )
        .isLeft
    )
    assert(
      DomainValidation
        .check(
          old.copy(runtime =
            Some(
              typed.copy(values =
                Vector(RuntimeClaimValue("count", number = Some("4"), text = Some("four")))
              )
            )
          )
        )
        .isLeft
    )
    assert(
      DomainValidation
        .check(Fixtures.plan.copy(runtime = Some(RuntimeQueryOptions(windowIds = Vector("")))))
        .isLeft
    )
  }
  test("evidence qualifiers retain iteration-limited and approximate source observations") {
    val evidence = RuntimeEvidence(
      Vector(Fixtures.orcidResearcher.researcherId),
      Vector("all-years"),
      Some("policy"),
      Fixtures.evidence.provenance.runId,
      Vector(RuntimeClaimValue("distanceP90", number = Some("4.2"))),
      Vector.empty,
      Some(false),
      Some(20),
      approximate = true,
      descriptive = false
    )
    val item = Fixtures.evidence.copy(runtime = Some(evidence))
    assert(read[EvidenceItem](write(item)).runtime.get.converged.contains(false))
    assert(DomainValidation.check(item).isRight)
    assert(
      DomainValidation.check(item.copy(runtime = Some(evidence.copy(iterations = None)))).isLeft
    )
  }
  test("vector-only evidence partition cannot carry deterministic evidence") {
    val context = RuntimeBundleContext(
      Vector(Fixtures.evidence.evidenceId),
      Vector.empty,
      Vector(Fixtures.evidence.provenance.runId),
      Vector("policy"),
      RetrievalMode.Vector,
      None,
      false
    )
    assert(DomainValidation.check(Fixtures.bundle.copy(runtime = Some(context))).isLeft)
    assert(
      DomainValidation
        .check(
          Fixtures.bundle.copy(
            items = Fixtures.bundle.items.map(
              _.copy(runtime =
                Some(
                  RuntimeEvidence(
                    Vector.empty,
                    Vector("all-years"),
                    None,
                    Fixtures.evidence.provenance.runId,
                    Vector(RuntimeClaimValue("title", text = Some("Stored title"))),
                    Vector.empty,
                    None,
                    None,
                    approximate = false,
                    descriptive = false
                  )
                )
              )
            ),
            runtime = Some(
              context.copy(
                retrievalMode = RetrievalMode.Fused,
                deterministicEvidenceIds = Fixtures.bundle.items.map(_.evidenceId)
              )
            )
          )
        )
        .isRight
    )
  }
  test("runtime configuration loads explicit model region and bounded deadlines") {
    val c = config
    assert(c.model.region == "us-east-2")
    assert(c.model.modelId == "local-placeholder-converse-model")
    assert(c.malformedRetries == 1)
    assert(c.deadlines.criticalPathMillis == BigInt(22000))
    assert(c.windows.find(_.windowId == "all-years").get.startYear.isEmpty)
    assert(RuntimeConfigValidation.check(c).isEmpty)
  }
  test("runtime configuration rejects total deadline overflow even if each individual stage fits") {
    val c = config
    assert(
      RuntimeConfigValidation
        .check(c.copy(deadlines = c.deadlines.copy(plannerMs = 29000)))
        .contains("runtime-deadline-budget-exceeded")
    )
    assert(
      RuntimeConfigValidation
        .check(c.copy(deadlines = c.deadlines.copy(plannerMs = Long.MaxValue)))
        .contains("runtime-deadline-budget-exceeded")
    )
    assert(
      RuntimeConfigValidation
        .check(c.copy(malformedRetries = 2))
        .contains("invalid-runtime-model-bound")
    )
  }
  test(
    "runtime configuration rejects unsupported modes, missing versions, unknown defaults and malformed windows"
  ) {
    assert(
      RuntimeConfigLoader
        .fromJson(
          resource("/scholarchain.runtime-config.v1.json").replace("\"fused\"", "\"invented\"")
        )
        .isLeft
    )
    assert(
      RuntimeConfigValidation
        .check(config.copy(model = config.model.copy(modelVersion = "")))
        .contains("blank-runtime-config-value")
    )
    assert(
      RuntimeConfigValidation
        .check(config.copy(defaultWindowId = "missing"))
        .contains("invalid-runtime-window-catalog")
    )
    assert(
      RuntimeConfigValidation
        .check(
          config.copy(windows =
            Vector(RuntimeWindow("bad", Some(2020), Some(2010), YearWindow(2020, 2010)))
          )
        )
        .contains("invalid-runtime-window-definition")
    )
  }
  test("researcher candidates preserve absent confidence and distinct DBLP suffixes") {
    val first = ResearcherCandidate(
      Fixtures.orcidResearcher.researcherId,
      "Name 0001",
      Vector("source-1"),
      Vector.empty,
      None,
      Vector.empty,
      Vector("source-row"),
      Vector(Fixtures.evidence.provenance.runId)
    )
    val second = first.copy(displayName = "Name 0002", sourceIds = Vector("source-2"))
    assert(read[ResearcherCandidate](write(first)).confidence.isEmpty)
    assert(read[ResearcherCandidate](write(first)).coauthorContextTruncated.isEmpty)
    val bounded = first.copy(coauthorContextTruncated = Some(true))
    assert(read[ResearcherCandidate](write(bounded)).coauthorContextTruncated.contains(true))
    val oldJson = ujson.read(write(bounded)).obj
    oldJson.remove("coauthorContextTruncated")
    assert(
      read[ResearcherCandidate](ujson.Obj.from(oldJson).render()).coauthorContextTruncated.isEmpty
    )
    assert(first.displayName != second.displayName)
  }
  test(
    "resolver configuration remains compatible and its identity cap is independent of graph results"
  ) {
    val old = ujson.read(resource("/scholarchain.runtime-config.v1.json"))
    old.obj.remove("resolver")
    val legacy = RuntimeConfigLoader.fromJson(old.render()).toOption.get
    assert(legacy.resolver == RuntimeResolverConfig(25, 16, 32, 16, 8))
    val c = legacy.copy(retrieval = legacy.retrieval.copy(graphLimit = 1))
    assert(c.resolver.maxDistinctCandidates == 25)
    assert(RuntimeConfigValidation.check(c).isEmpty)
    val configured = c.copy(resolver = RuntimeResolverConfig(3, 4, 5, 2, 1))
    assert(read[RuntimeConfig](write(configured)).resolver == RuntimeResolverConfig(3, 4, 5, 2, 1))
  }
  test("resolver configuration rejects every nonpositive candidate or provenance bound") {
    val invalid = Vector(
      RuntimeResolverConfig(maxDistinctCandidates = 0),
      RuntimeResolverConfig(maxSourceIdsPerCandidate = -1),
      RuntimeResolverConfig(maxEvidenceRefsPerCandidate = 0),
      RuntimeResolverConfig(maxAffiliationsPerCandidate = -1),
      RuntimeResolverConfig(maxRunIdsPerCandidate = 0)
    )
    invalid.foreach { bounds =>
      assert(
        RuntimeConfigValidation
          .check(config.copy(resolver = bounds))
          .contains("invalid-runtime-resolver-bound")
      )
    }
  }
  test(
    "candidate provenance counts disclose clipped distinct lists and remain optional for legacy JSON"
  ) {
    val candidate = ResearcherCandidate(
      Fixtures.orcidResearcher.researcherId,
      "Name 0001",
      Vector("source-1", "source-2"),
      Vector("affiliation-1"),
      None,
      Vector.empty,
      Vector("cache-evidence-1", "context-evidence-1"),
      Vector(Fixtures.evidence.provenance.runId),
      provenanceSummary = Some(ResearcherCandidateProvenanceSummary(40, 75, 1, 3, truncated = true))
    )
    assert(RuntimeContractValidation.candidate(candidate).isEmpty)
    assert(read[ResearcherCandidate](write(candidate)) == candidate)
    assert(candidate.provenanceSummary.get.sourceIdCount == 40)
    assert(candidate.provenanceSummary.get.evidenceRefCount == 75)
    val old = ujson.read(write(candidate))
    old.obj.remove("provenanceSummary")
    assert(read[ResearcherCandidate](old.render()).provenanceSummary.isEmpty)
    val complete = candidate.copy(provenanceSummary =
      Some(ResearcherCandidateProvenanceSummary(2, 2, 1, 1, truncated = false))
    )
    assert(RuntimeContractValidation.candidate(complete).isEmpty)
  }
  test("candidate provenance validation rejects hidden truncation and impossible source totals") {
    val candidate = ResearcherCandidate(
      Fixtures.orcidResearcher.researcherId,
      "Name 0001",
      Vector("source-1"),
      Vector.empty,
      None,
      Vector.empty,
      Vector("evidence-1"),
      Vector.empty,
      provenanceSummary = Some(ResearcherCandidateProvenanceSummary(2, 1, 0, 0, truncated = false))
    )
    assert(
      RuntimeContractValidation
        .candidate(candidate)
        .contains("invalid-candidate-provenance-truncation")
    )
    val impossible = candidate.copy(provenanceSummary =
      Some(ResearcherCandidateProvenanceSummary(0, 1, 0, 0, truncated = false))
    )
    assert(
      RuntimeContractValidation.candidate(impossible).contains("invalid-candidate-provenance-count")
    )
    val negative = candidate.copy(provenanceSummary =
      Some(ResearcherCandidateProvenanceSummary(1, 1, -1, 0, truncated = false))
    )
    assert(
      RuntimeContractValidation.candidate(negative).contains("invalid-candidate-provenance-count")
    )
  }
}
