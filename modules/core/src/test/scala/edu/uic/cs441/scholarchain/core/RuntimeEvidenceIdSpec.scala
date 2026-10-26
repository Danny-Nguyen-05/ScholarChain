package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}

/** Immutable evidence lookup requires distinct IDs for different complete stored observations. */
class RuntimeEvidenceIdSpec extends AnyFunSuite {
  private val payload = RuntimeEvidence(
    Vector(Fixtures.orcidResearcher.researcherId),
    Vector("all-years"),
    Some("stored-policy"),
    Fixtures.evidence.provenance.runId,
    Vector(RuntimeClaimValue("count", number = Some("9007199254740993"))),
    Vector.empty,
    None,
    None,
    approximate = false,
    descriptive = false
  )
  private def enriched(item: EvidenceItem): EvidenceItem = item.copy(runtime = Some(payload))
  private def bound(item: EvidenceItem): EvidenceItem = RuntimeEvidenceIds.bind(item).toOption.get

  test("legacy and unmarked runtime evidence retain their frozen locator-only IDs") {
    Vector(Fixtures.graphPathEvidence, Fixtures.edgeEvidence, Fixtures.metricEvidence).foreach {
      item =>
        assert(DomainValidation.check(item).isRight)
        assert(DomainValidation.check(enriched(item)).isRight)
        val oldJson = ujson.read(write(payload))
        oldJson.obj.remove("contentBindingVersion")
        assert(read[RuntimeEvidence](oldJson.render()).contentBindingVersion.isEmpty)
    }
  }

  test(
    "binding is deterministic and idempotent and retains precise types and actual metric policy"
  ) {
    Vector(Fixtures.graphPathEvidence, Fixtures.edgeEvidence, Fixtures.metricEvidence).foreach {
      item =>
        val first = bound(enriched(item))
        assert(first == bound(enriched(item)))
        assert(first == bound(first))
        assert(first.evidenceType == item.evidenceType)
        assert(first.metricLocator == item.metricLocator)
        assert(first.runtime.get.contentBindingVersion.contains(RuntimeEvidenceIds.version))
        assert(StableIds.parseEvidenceId(first.evidenceId).isRight)
        assert(DomainValidation.check(first).isRight)
    }
  }

  test("the same path across windows source runs and payload values has distinct evidence IDs") {
    val first = bound(enriched(Fixtures.graphPathEvidence))
    val otherRun = "run:12345678-1234-4123-8123-123456789abc"
    val alternatives = Vector(
      first.copy(runtime = Some(first.runtime.get.copy(windowIds = Vector("2020-2026")))),
      first.copy(runtime = Some(first.runtime.get.copy(runId = otherRun))),
      first.copy(runtime =
        Some(
          first.runtime.get.copy(values =
            Vector(RuntimeClaimValue("count", number = Some("9007199254740994")))
          )
        )
      )
    ).map(bound)
    assert((first +: alternatives).map(_.graphPath).distinct.size == 1)
    assert((first +: alternatives).map(_.evidenceId).distinct.size == 4)
    alternatives.foreach(item => assert(DomainValidation.check(item).isRight))
  }

  test("complete item binding includes text score source URI and provenance") {
    val first = bound(enriched(Fixtures.edgeEvidence))
    val alternatives = Vector(
      first.copy(text = Some("Different observation")),
      first.copy(score = 0.75),
      first.copy(sourceUri = "synthetic://different-source"),
      first.copy(provenance =
        first.provenance.copy(uncertaintyNotes = Vector("Different qualification"))
      )
    ).map(bound)
    assert((first +: alternatives).map(_.evidenceId).distinct.size == 5)
    alternatives.foreach(item => assert(DomainValidation.check(item).isRight))
  }

  test("tampering a bound payload without rebinding is rejected") {
    val first = bound(enriched(Fixtures.metricEvidence))
    val changed = first.copy(runtime =
      Some(first.runtime.get.copy(values = Vector(RuntimeClaimValue("count", number = Some("2")))))
    )
    assert(DomainValidation.check(changed).isLeft)
    assert(DomainValidation.check(first.copy(text = Some("Changed"))).isLeft)
    assert(DomainValidation.check(first.copy(score = 0.5)).isLeft)
  }

  test("binding cannot bypass path edge metric locator and exact-value validation") {
    val invalid = Vector(
      enriched(Fixtures.graphPathEvidence.copy(graphPath = None)),
      enriched(Fixtures.edgeEvidence.copy(edgeLocatorId = Some("invented"))),
      enriched(Fixtures.metricEvidence.copy(metricLocator = None)),
      enriched(Fixtures.metricEvidence).copy(runtime =
        Some(payload.copy(values = Vector(RuntimeClaimValue("count", number = Some("NaN")))))
      )
    )
    invalid.map(bound).foreach(item => assert(DomainValidation.check(item).isLeft))
  }

  test("unknown binding versions and missing runtime are rejected") {
    assert(RuntimeEvidenceIds.bind(Fixtures.evidence).isLeft)
    val unknown = enriched(Fixtures.metricEvidence).copy(runtime =
      Some(payload.copy(contentBindingVersion = Some("runtime-evidence-content-unknown")))
    )
    assert(RuntimeEvidenceIds.bind(unknown).isLeft)
    assert(RuntimeEvidenceIds.expectedId(unknown).isLeft)
    assert(DomainValidation.check(unknown).isLeft)
  }

  test("binding supports descriptive profile and chunk evidence using existing ID parsers") {
    val description = payload.copy(
      metricVersion = None,
      values = Vector(RuntimeClaimValue("excerpt", text = Some("Descriptive context"))),
      descriptive = true
    )
    Vector(
      EvidenceType.TextChunk,
      EvidenceType.ResearcherProfile,
      EvidenceType.WorkMetadata,
      EvidenceType.AuthorMention,
      EvidenceType.Institution,
      EvidenceType.Topic,
      EvidenceType.Venue
    )
      .foreach { kind =>
        val item = bound(Fixtures.evidence.copy(evidenceType = kind, runtime = Some(description)))
        assert(StableIds.parseChunkOrProfileId(item.evidenceId).isRight)
        assert(
          item.evidenceId.startsWith(
            if (kind == EvidenceType.ResearcherProfile) "profile:" else "chunk:"
          )
        )
        assert(DomainValidation.check(item).isRight)
      }
  }

  test("serialization round trips preserve binding and large exact decimal values") {
    val item = bound(enriched(Fixtures.metricEvidence))
    val roundTrip = read[EvidenceItem](write(item))
    assert(roundTrip == item)
    assert(roundTrip.runtime.get.values.head.number.contains("9007199254740993"))
    assert(RuntimeEvidenceIds.expectedId(roundTrip).contains(item.evidenceId))
    assert(DomainValidation.check(roundTrip).isRight)
  }
}
