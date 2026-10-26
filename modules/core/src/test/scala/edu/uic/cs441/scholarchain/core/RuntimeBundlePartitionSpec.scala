package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}

/** Hand-derived trust partitions: descriptive retrieval cannot authorize stored numeric facts. */
class RuntimeBundlePartitionSpec extends AnyFunSuite {
  private def payload(descriptive: Boolean): RuntimeEvidence = RuntimeEvidence(
    Vector(Fixtures.orcidResearcher.researcherId),
    Vector("all-years"),
    None,
    Fixtures.evidence.provenance.runId,
    Vector(RuntimeClaimValue("excerpt", text = Some("A descriptive source excerpt."))),
    Vector.empty,
    None,
    None,
    approximate = false,
    descriptive = descriptive
  )
  private val semantic = Fixtures.evidence.copy(
    evidenceType = EvidenceType.TextChunk,
    runtime = Some(payload(descriptive = true))
  )
  private val deterministic = Fixtures.metricEvidence.copy(
    runtime = Some(
      payload(descriptive = false).copy(
        metricVersion = Some("stored-policy"),
        values = Vector(RuntimeClaimValue("publicationCount", number = Some("7")))
      )
    )
  )
  private def bundle(
      items: Vector[EvidenceItem],
      mode: RetrievalMode = RetrievalMode.Vector,
      deterministicIds: Vector[String] = Vector.empty
  ): EvidenceBundle = Fixtures.bundle.copy(
    items = items,
    runtime = Some(
      RuntimeBundleContext(
        deterministicIds,
        items.map(_.evidenceId).filterNot(deterministicIds.contains),
        Vector(Fixtures.evidence.provenance.runId),
        Vector.empty,
        mode,
        None,
        truncated = false
      )
    )
  )

  test("frozen legacy bundles remain valid without runtime classification") {
    assert(Fixtures.bundle.runtime.isEmpty)
    assert(DomainValidation.check(Fixtures.bundle).isRight)
  }

  test("runtime bundles reject unclassified legacy items instead of trusting partition IDs") {
    assert(DomainValidation.check(bundle(Vector(Fixtures.evidence))).isLeft)
  }

  test("vector bundles accept descriptive text chunks and researcher profiles with provenance") {
    assert(DomainValidation.check(bundle(Vector(semantic))).isRight)
    val profile = semantic.copy(evidenceType = EvidenceType.ResearcherProfile)
    assert(DomainValidation.check(bundle(Vector(profile))).isRight)
  }

  test("the reported non-descriptive metric masquerading as semantic is rejected") {
    val candidate = bundle(Vector(deterministic))
    assert(candidate.runtime.get.deterministicEvidenceIds.isEmpty)
    assert(candidate.runtime.get.semanticEvidenceIds == Vector(deterministic.evidenceId))
    assert(DomainValidation.check(candidate).isLeft)
  }

  test("marking graph and metric evidence descriptive cannot make its type semantic") {
    Vector(
      Fixtures.metricEvidence,
      Fixtures.edgeEvidence,
      Fixtures.graphPathEvidence,
      Fixtures.evidence
    ).foreach { item =>
      val candidate = item.copy(runtime = Some(payload(descriptive = true)))
      assert(DomainValidation.check(bundle(Vector(candidate))).isLeft, item.evidenceType.wire)
    }
  }

  test("semantic text and profile payloads require descriptive=true") {
    Vector(EvidenceType.TextChunk, EvidenceType.ResearcherProfile).foreach { kind =>
      val candidate =
        semantic.copy(evidenceType = kind, runtime = Some(payload(descriptive = false)))
      assert(DomainValidation.check(bundle(Vector(candidate))).isLeft)
    }
  }

  test("semantic payload cannot carry typed numeric, flag or ID facts") {
    Vector(
      RuntimeClaimValue("publicationCount", number = Some("7")),
      RuntimeClaimValue("connected", flag = Some(true)),
      RuntimeClaimValue("path", ids = Some(Vector(Fixtures.orcidResearcher.researcherId)))
    ).foreach { value =>
      val candidate = semantic.copy(runtime =
        Some(
          payload(descriptive = true)
            .copy(values = Vector(value))
        )
      )
      assert(DomainValidation.check(bundle(Vector(candidate))).isLeft)
    }
  }

  test("semantic payload cannot carry deterministic metric or convergence qualifications") {
    val base = payload(descriptive = true)
    Vector(
      base.copy(metricVersion = Some("stored-policy")),
      base.copy(converged = Some(false), iterations = Some(20)),
      base.copy(approximate = true)
    ).foreach { value =>
      assert(DomainValidation.check(bundle(Vector(semantic.copy(runtime = Some(value))))).isLeft)
    }
  }

  test("semantic types cannot conceal deterministic graph, edge or metric locators") {
    val examples = Vector(
      semantic.copy(graphPath = Fixtures.graphPathEvidence.graphPath),
      semantic.copy(edgeLocatorId = Fixtures.edgeEvidence.edgeLocatorId),
      semantic.copy(metricLocator = Fixtures.metricEvidence.metricLocator)
    )
    examples.foreach { item => assert(DomainValidation.check(bundle(Vector(item))).isLeft) }
  }

  test("fused partitions accept stored metrics and descriptive context together") {
    val candidate =
      bundle(Vector(deterministic, semantic), RetrievalMode.Fused, Vector(deterministic.evidenceId))
    assert(DomainValidation.check(candidate).isRight)
    val vectorCandidate = candidate.copy(runtime =
      Some(candidate.runtime.get.copy(retrievalMode = RetrievalMode.Vector))
    )
    assert(DomainValidation.check(vectorCandidate).isLeft)
  }

  test("deterministic partitions reject descriptive items and text chunks with a false label") {
    Vector(semantic, semantic.copy(runtime = Some(payload(descriptive = false)))).foreach { item =>
      val candidate = bundle(Vector(item), RetrievalMode.Fused, Vector(item.evidenceId))
      assert(DomainValidation.check(candidate).isLeft)
    }
  }

  private val resolved = ResearcherCandidate(
    Fixtures.orcidResearcher.researcherId,
    "Name 0001",
    Vector("source:synthetic-name"),
    Vector("Synthetic institution"),
    Some(0.8),
    Vector.empty,
    Vector("source-row:synthetic-name"),
    Vector(Fixtures.evidence.provenance.runId)
  )

  test("old runtime bundle JSON defaults omitted resolved candidates to empty") {
    val context = bundle(Vector(semantic)).runtime.get
    val oldJson = ujson.read(write(context))
    oldJson.obj.remove("resolvedCandidates")
    assert(read[RuntimeBundleContext](oldJson.render()).resolvedCandidates.isEmpty)
  }

  test("resolved candidate identities and per-candidate confidence survive bundle serialization") {
    val original = bundle(Vector(semantic))
    val withIdentity = original.copy(runtime =
      Some(original.runtime.get.copy(resolvedCandidates = Vector(resolved)))
    )
    assert(DomainValidation.check(withIdentity).isRight)
    val roundTrip = read[EvidenceBundle](write(withIdentity))
    assert(roundTrip.runtime.get.resolvedCandidates == Vector(resolved))
    assert(roundTrip.runtime.get.resolvedCandidates.head.displayName == "Name 0001")
    assert(roundTrip.runtime.get.resolvedCandidates.head.confidence.contains(0.8))
  }

  test("bundle validation rejects malformed resolved identity provenance and confidence") {
    val original = bundle(Vector(semantic))
    val invalid = Vector(
      resolved.copy(researcherId = "invented"),
      resolved.copy(displayName = " "),
      resolved.copy(sourceIds = Vector.empty),
      resolved.copy(sourceIds = Vector("")),
      resolved.copy(sourceIds = Vector("duplicate", "duplicate")),
      resolved.copy(evidenceRefs = Vector("")),
      resolved.copy(runIds = Vector("invented")),
      resolved.copy(runIds = Vector.empty),
      resolved.copy(confidence = Some(Double.NaN)),
      resolved.copy(confidence = Some(1.01)),
      resolved.copy(coauthorContext = Vector("invented")),
      resolved.copy(provenanceSummary =
        Some(ResearcherCandidateProvenanceSummary(0, 1, 1, 1, truncated = false))
      )
    )
    invalid.foreach { value =>
      val candidate =
        original.copy(runtime = Some(original.runtime.get.copy(resolvedCandidates = Vector(value))))
      assert(DomainValidation.check(candidate).isLeft)
    }
    val duplicate = original.copy(runtime =
      Some(original.runtime.get.copy(resolvedCandidates = Vector(resolved, resolved)))
    )
    assert(DomainValidation.check(duplicate).isLeft)
  }
}
