package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite

class IndependentResolutionInputSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*

  private def input(works: Vector[WorkRecord], candidates: Vector[MatchCandidate] = Vector.empty) =
    ResolutionInput.create(works, Vector.empty, Vector.empty, candidates)

  test("same DOI source observations remain distinct while conflicting full lookup keys fail") {
    val doi = Some("10.5555/independent-input")
    val a = work("conf/independent/InputA", doi = doi)
    val b = work("W700000001", doi = doi, source = SourceType.OpenAlex)
    assert(a.workId == b.workId)
    assert(input(Vector(a, b), Vector(candidate(a, b))).isRight)
    val contradictory = a.copy(year = Some(2024))
    assert(input(Vector(a, contradictory)).isLeft)
    assert(input(Vector(a, a)).isRight, "byte-equivalent duplicates may be deduplicated")
  }

  test("candidate lookup binds source native record and snapshot rather than shared work ID") {
    val doi = Some("10.5555/independent-input")
    val a = work("conf/independent/LookupA", doi = doi)
    val b = work("W700000002", doi = doi, source = SourceType.OpenAlex)
    val missingNative = work("W700000003", doi = doi, source = SourceType.OpenAlex)
    assert(input(Vector(a, b), Vector(candidate(a, missingNative))).isLeft)
    val missingSnapshot = b.copy(
      provenance = b.provenance.copy(datasetSnapshot = "not-loaded"),
      authors =
        b.authors.map(m => m.copy(provenance = m.provenance.copy(datasetSnapshot = "not-loaded")))
    )
    assert(input(Vector(a, b), Vector(candidate(a, missingSnapshot))).isLeft)
  }

  test("optional candidate work hints may be absent but supplied hints must match source truth") {
    val doi = "10.5555/independent-optional-hint"
    val observedWork = work("conf/independent/OptionalHint", doi = Some(doi))
    val observedActivity = activity(OrcidActivityKind.Work, 41).copy(
      observedDoi = Some(doi),
      observedWorkId = Some(s"work:doi:$doi"),
      workReferences = Vector(OrcidWorkReference("doi", doi, Some("self")))
    )
    assert(DomainValidation.check(observedActivity).isRight)
    def observation(p: Provenance, hint: Option[String]) =
      CandidateObservation(p.source, p.sourceRecordId, p.datasetSnapshot, hint)
    def loaded(workHint: Option[String], activityHint: Option[String]) = {
      val candidate = candidateObservations(
        observation(observedWork.provenance, workHint),
        observation(observedActivity.provenance, activityHint),
        "exact:doi:" + doi
      )
      ResolutionInput.create(
        Vector(observedWork),
        Vector.empty,
        Vector(observedActivity),
        Vector(candidate)
      )
    }
    assert(loaded(None, None).isRight, "optional hints cannot erase full source observation lookup")
    assert(
      loaded(Some(observedWork.workId), None).isRight,
      "Phase 4 ORCID work candidates legitimately omit an available observed work ID"
    )
    assert(loaded(Some(observedWork.workId), observedActivity.observedWorkId).isRight)
    val wrong = Some("work:doi:10.5555/not-this-observation")
    assert(loaded(wrong, None).isLeft)
    assert(loaded(None, wrong).isLeft)
  }

  test(
    "native source aliases are rejected before two identities can be assigned to one observation"
  ) {
    val canonical = work("W700000004", source = SourceType.OpenAlex)
    val alias = work("https://openalex.org/W700000004", source = SourceType.OpenAlex)
    assert(DomainValidation.check(alias).isRight, "core historically accepts the alias")
    assert(input(Vector(canonical)).isRight)
    assert(
      input(Vector(alias)).isLeft,
      "5B must reject or canonicalize native aliases consistently"
    )
    assert(input(Vector(canonical, alias)).isLeft)
    val profileAlias = profile(orcidA).copy(provenance =
      profile(orcidA).provenance.copy(sourceRecordId = s"/$orcidA")
    )
    assert(
      ResolutionInput.create(Vector.empty, Vector(profileAlias), Vector.empty, Vector.empty).isLeft
    )
  }

  test("nested unknown schema, forged mention binding and invalid candidate IDs fail closed") {
    val a = work("conf/independent/SchemaA")
    val b = work("conf/independent/SchemaB")
    assert(input(Vector(a.copy(schemaVersion = "scholarchain.domain.v99"))).isLeft)
    val forged = a.copy(authors = a.authors.map(_.copy(sourceRecordId = b.sourceRecordId)))
    assert(input(Vector(forged, b)).isLeft)
    val badCandidate = candidate(a, b).copy(candidateId = "candidate:forged")
    assert(input(Vector(a, b), Vector(badCandidate)).isLeft)
  }

  test("affiliation evidence cannot point to a missing member or wrong parent snapshot") {
    val a = work("conf/independent/AffiliationA")
    val affiliation = MentionAffiliation(
      SchemaVersions.domain,
      a.authors.head.mentionId,
      a.source,
      a.sourceRecordId,
      a.provenance.datasetSnapshot,
      Some("Synthetic Distributed Systems Lab"),
      None,
      None,
      None,
      IndependentResolutionFixtures.note,
      a.provenance
    )
    assert(
      ResolutionInput
        .create(
          Vector(a),
          Vector.empty,
          Vector.empty,
          Vector.empty,
          affiliations = Vector(affiliation)
        )
        .isRight
    )
    assert(
      ResolutionInput
        .create(
          Vector(a),
          Vector.empty,
          Vector.empty,
          Vector.empty,
          affiliations =
            Vector(affiliation.copy(mentionId = StableIds.mentionId(a.source, a.sourceRecordId, 2)))
        )
        .isLeft
    )
    val wrong = affiliation.copy(
      datasetSnapshot = "unloaded",
      provenance = affiliation.provenance.copy(datasetSnapshot = "unloaded")
    )
    assert(
      ResolutionInput
        .create(Vector(a), Vector.empty, Vector.empty, Vector.empty, affiliations = Vector(wrong))
        .isLeft
    )
  }
}
