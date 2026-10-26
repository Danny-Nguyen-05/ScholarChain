package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}
import scala.io.Source

class Runtime9CContractSpec extends AnyFunSuite {
  private def config: RuntimeConfig = {
    val source = Source.fromInputStream(
      getClass.getResourceAsStream("/scholarchain.runtime-config.v1.json"),
      "UTF-8"
    )
    try RuntimeConfigLoader.fromJson(source.mkString).toOption.get
    finally source.close()
  }
  private val payload = RuntimeEvidence(
    Vector(Fixtures.orcidResearcher.researcherId),
    Vector("all-years"),
    Some("stored-policy"),
    Fixtures.runId,
    Vector(RuntimeClaimValue("publicationCount", number = Some("3"))),
    Vector.empty,
    None,
    None,
    approximate = false,
    descriptive = false
  )
  private val hash = "b" * 64
  private def record: AuditRecord = AuditRecord(
    "query:9c",
    "trace:9c",
    Fixtures.plan,
    Vector(Fixtures.orcidResearcher.researcherId),
    Vector(Fixtures.metricEvidence.evidenceId),
    Vector("stored-policy"),
    Vector(Fixtures.runId),
    Vector.empty,
    12L,
    Vector.empty,
    VerificationResult(Vector.empty, Vector.empty, abstained = false),
    hash
  )
  private def envelope: RuntimeAuditEnvelope = RuntimeAuditEnvelope(
    "query:9c",
    "trace:9c",
    Fixtures.plan.question,
    "ANSWERED",
    None,
    Some(record),
    Vector.empty,
    12L,
    hash
  )

  test("omitted byte limits preserve each legacy maxInputBytes surface") {
    val old = ujson.read(write(config))
    old.obj.remove("byteLimits")
    old("maxInputBytes") = 1234
    val parsed = RuntimeConfigLoader.fromJson(old.render()).toOption.get
    assert(parsed.byteLimits.isEmpty)
    assert(parsed.effectiveByteLimits == RuntimeByteLimits(1234, 1234, 1234, 1234, 1234))
  }

  test("explicit independent limits round trip without changing token and deadline budgets") {
    val c = config
    assert(c.effectiveByteLimits == RuntimeByteLimits(16384, 16384, 65536, 32768, 65536))
    val independent = c.copy(byteLimits = Some(RuntimeByteLimits(10, 20, 30, 40, 50)))
    assert(
      read[RuntimeConfig](write(independent)).effectiveByteLimits == RuntimeByteLimits(10, 20, 30,
        40, 50)
    )
    assert(c.retrieval.contextTokenBudget == 4096)
    assert(c.operations.synchronousDeadlineMs == 30000)
    assert(c.deadlines.criticalPathMillis == BigInt(22000))
  }

  test("each independent byte surface rejects zero or negative bounds") {
    val limits = Vector(
      RuntimeByteLimits(0, 2, 3, 4, 5),
      RuntimeByteLimits(1, -2, 3, 4, 5),
      RuntimeByteLimits(1, 2, 0, 4, 5),
      RuntimeByteLimits(1, 2, 3, -4, 5),
      RuntimeByteLimits(1, 2, 3, 4, 0)
    )
    limits.foreach { limit =>
      assert(
        RuntimeConfigValidation
          .check(config.copy(byteLimits = Some(limit)))
          .contains("invalid-runtime-byte-bound")
      )
    }
  }

  test("legacy runtime evidence omits source context and old model usage omits region") {
    val old = ujson.read(write(payload)); old.obj.remove("sourceContext")
    assert(read[RuntimeEvidence](old.render()).sourceContext.isEmpty)
    val usage =
      ujson.read(write(RuntimeModelUsage("model", "version", "prompt", "schema", None, None)))
    usage.obj.remove("region")
    assert(read[RuntimeModelUsage](usage.render()).region.isEmpty)
  }

  test("stored Spark context round trips and binds the evidence ID") {
    val enriched = Fixtures.metricEvidence.copy(runtime =
      Some(payload.copy(sourceContext = Some(SparkAnalyticsExamples.ctx)))
    )
    val bound = RuntimeEvidenceIds.bind(enriched).toOption.get
    assert(DomainValidation.check(bound).isRight)
    assert(
      read[EvidenceItem](write(bound)).runtime.get.sourceContext
        .contains(SparkAnalyticsExamples.ctx)
    )
    val changed = bound.copy(runtime =
      bound.runtime.map(p =>
        p.copy(sourceContext =
          p.sourceContext.map(c =>
            c.copy(lineage = c.lineage.copy(hadoopSnapshot = "other-stored-snapshot"))
          )
        )
      )
    )
    assert(DomainValidation.check(changed).isLeft)
    assert(RuntimeEvidenceIds.bind(changed).toOption.get.evidenceId != bound.evidenceId)
  }

  test("source contexts reject run window and lineage mismatches") {
    val source = SparkAnalyticsExamples.ctx
    Vector(
      source.copy(runId = "run:99999999-9999-4999-8999-999999999999"),
      source.copy(windowId = Some("2020-2026")),
      source.copy(lineage = source.lineage.copy(entityResolutionPolicyHash = "invalid"))
    ).foreach { context =>
      assert(
        RuntimeContractValidation.evidence(payload.copy(sourceContext = Some(context))).nonEmpty
      )
    }
  }

  test("runtime deterministic profiles reject excerpt text while legacy bundles remain readable") {
    val item =
      Fixtures.evidence.copy(evidenceType = EvidenceType.ResearcherProfile, runtime = Some(payload))
    val context = RuntimeBundleContext(
      Vector(item.evidenceId),
      Vector.empty,
      Vector(Fixtures.runId),
      Vector("stored-policy"),
      RetrievalMode.Graph,
      None,
      false
    )
    assert(DomainValidation.check(Fixtures.bundle).isRight)
    val bundle = Fixtures.bundle.copy(items = Vector(item), runtime = Some(context))
    assert(DomainValidation.check(bundle).isLeft)
    assert(DomainValidation.check(bundle.copy(items = Vector(item.copy(text = None)))).isRight)
  }

  test("audit envelope records pre-plan rejection without fabricating a plan") {
    val rejected = envelope.copy(
      outcome = "UNSUPPORTED",
      reason = Some("unsupported-query"),
      record = None,
      stageFailures = Vector(RuntimeAuditFailure("planner", "unsupported-query"))
    )
    assert(RuntimeAuditValidation.check(rejected).isEmpty)
    assert(read[RuntimeAuditEnvelope](write(rejected)).record.isEmpty)
    assert(read[RuntimeAuditEnvelope](write(envelope)) == envelope)
  }

  test("audit rejects missing answered records mismatched keys hashes and inconsistent modes") {
    Vector(
      envelope.copy(record = None),
      envelope.copy(queryId = "other"),
      envelope.copy(answerHash = "a" * 64),
      envelope.copy(outcome = "unknown"),
      envelope.copy(latencyMillis = -1),
      envelope.copy(evidenceOnly = true),
      envelope.copy(outcome = "EVIDENCE_ONLY", evidenceOnly = false)
    ).foreach { value =>
      assert(RuntimeAuditValidation.check(value).nonEmpty)
    }
    assert(
      RuntimeAuditValidation
        .check(envelope.copy(outcome = "EVIDENCE_ONLY", evidenceOnly = true))
        .isEmpty
    )
  }

  test("audit retains malformed rejected claim proposals and ABSTAINED status") {
    val attempted =
      Fixtures.claim.copy(claimId = "fabricated-proposal", evidenceIds = Vector("invented"))
    assert(DomainValidation.check(attempted).isLeft)
    val verification = VerificationResult(
      Vector(
        ClaimVerificationResult(
          attempted.claimId,
          ClaimVerdict.Unsupported,
          Vector("missing-evidence")
        )
      ),
      Vector(attempted),
      abstained = true
    )
    val value = envelope.copy(
      outcome = "ABSTAINED",
      reason = Some("unsupported-claims"),
      record = Some(record.copy(attemptedClaims = Vector(attempted), verification = verification))
    )
    assert(RuntimeAuditValidation.check(value).isEmpty)
    assert(read[RuntimeAuditEnvelope](write(value)).record.get.attemptedClaims == Vector(attempted))
    assert(value.record.get.verification.overallStatus == VerificationStatus.Abstained)
  }

  test("audit validates model region and token counts without requiring legacy region") {
    val usage = RuntimeModelUsage(
      "model",
      "version",
      "prompt",
      "schema",
      Some(4L),
      Some(2L),
      Some("us-east-2")
    )
    assert(RuntimeAuditValidation.check(envelope.copy(modelUsage = Vector(usage))).isEmpty)
    assert(
      RuntimeAuditValidation
        .check(envelope.copy(modelUsage = Vector(usage.copy(region = None))))
        .isEmpty
    )
    assert(
      RuntimeAuditValidation
        .check(envelope.copy(modelUsage = Vector(usage.copy(region = Some("")))))
        .nonEmpty
    )
    assert(
      RuntimeAuditValidation
        .check(envelope.copy(modelUsage = Vector(usage.copy(inputTokens = Some(-1L)))))
        .nonEmpty
    )
  }
}
