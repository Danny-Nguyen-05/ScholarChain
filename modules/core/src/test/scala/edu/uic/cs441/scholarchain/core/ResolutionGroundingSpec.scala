package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite

/** Synthetic source-consistency cases: no matcher or human annotation is invoked. */
class ResolutionGroundingSpec extends AnyFunSuite {
  import ResolutionContractFixtures.*
  import ResolutionAuthorityNamespace.*

  private def assertion(
      e: ResolutionEndpoint,
      ns: ResolutionAuthorityNamespace,
      value: String
  ): ResolutionIdentifierAssertion =
    ResolutionIdentifierAssertion(e, ns, value, Vector("synthetic:grounding"))
  private def constraints(
      members: Vector[ResolutionEndpoint],
      ids: Vector[ResolutionIdentifierAssertion]
  ): ResolutionGroupingConstraints =
    ResolutionGroupingConstraints(
      schema,
      ResolutionIds.entityType(members.head),
      "synthetic-grounding-v1",
      hash,
      members,
      Vector.empty,
      ids
    )
  private def check(
      members: Vector[ResolutionEndpoint],
      ids: Vector[ResolutionIdentifierAssertion],
      ctx: ResolutionValidationContext
  ): Boolean =
    ResolutionValidation.checkComponent(members, constraints(members, ids), ctx, 10, 50).isRight
  private def workContext(work: WorkRecord): ResolutionValidationContext =
    ResolutionValidationContext.create(Vector(work), Vector.empty, Vector.empty).toOption.get

  test("profile assertions bind their own ORCID and covered profiles cannot omit known IDs") {
    val other = "0000-0002-1825-0097"
    val otherProfile = profile.copy(
      orcid = other,
      externalIds =
        Vector(ObservedIdentifier("orcid", other, IdentifierInterpretation.ValidatedExternal)),
      provenance = profile.provenance.copy(sourceRecordId = other)
    )
    val otherEndpoint = ResolutionEndpoint.OrcidProfile(ref(otherProfile.provenance), other)
    val middle =
      ResolutionEndpoint.Mention(ref(Fixtures.work.provenance), Fixtures.berkeleyMentionId)
    val ctx = ResolutionValidationContext
      .create(Vector(Fixtures.work), Vector(profile, otherProfile), Vector.empty)
      .toOption
      .get
    val members = Vector(profileEndpoint, middle, otherEndpoint)
    val genuine = Vector(
      assertion(profileEndpoint, Orcid, profile.orcid),
      assertion(otherEndpoint, Orcid, other)
    )
    assert(ResolutionValidation.check(constraints(members, genuine), ctx).isRight)
    assert(!check(members, genuine, ctx))
    val forged =
      Vector(assertion(profileEndpoint, Orcid, other), assertion(otherEndpoint, Orcid, other))
    assert(ResolutionValidation.check(constraints(members, forged), ctx).isLeft)
    assert(!check(members, forged, ctx))
    assert(!check(members, Vector.empty, ctx))
  }

  test(
    "mention authority uses only the actual member observed ORCID, including raw resolver spelling"
  ) {
    val otherMention =
      ResolutionEndpoint.Mention(ref(Fixtures.work.provenance), Fixtures.berkeleyMentionId)
    assert(
      !check(
        Vector(otherMention),
        Vector(assertion(otherMention, Orcid, Fixtures.riceOrcid)),
        context
      )
    )
    assert(!check(Vector(mentionEndpoint), Vector.empty, context))
    val raw = Fixtures.work.copy(authors = Fixtures.work.authors.map { m =>
      if (m.mentionId == Fixtures.riceMentionId)
        m.copy(observedOrcid = Some("https://orcid.org/" + Fixtures.riceOrcid))
      else m
    })
    assert(
      check(
        Vector(mentionEndpoint),
        Vector(assertion(mentionEndpoint, Orcid, Fixtures.riceOrcid)),
        workContext(raw)
      )
    )
  }

  test(
    "work assertions require actual DOI or arxiv facts and Crossref native DOI survives absent optional field"
  ) {
    assert(
      !check(Vector(workEndpoint), Vector(assertion(workEndpoint, Arxiv, "2301.01234")), context)
    )
    assert(
      !check(Vector(workEndpoint), Vector(assertion(workEndpoint, Doi, "10.9999/absent")), context)
    )
    assert(!check(Vector(workEndpoint), Vector.empty, context))
    val native = Fixtures.work.copy(
      workId = StableIds.workIdFromDblpKey(Fixtures.dblpKey).toOption.get,
      doi = None,
      externalUrl = None,
      authors = Vector.empty,
      provenance = Fixtures.work.provenance.copy(sourceUri = None)
    )
    val nativeEndpoint = ResolutionEndpoint.Work(ref(native.provenance), native.workId)
    assert(check(Vector(nativeEndpoint), Vector.empty, workContext(native)))
    assert(
      !check(
        Vector(nativeEndpoint),
        Vector(assertion(nativeEndpoint, Doi, Fixtures.doi)),
        workContext(native)
      )
    )
    val noOptionalDoi = crossref.copy(doi = None)
    assert(
      check(
        Vector(crossrefEndpoint),
        Vector(assertion(crossrefEndpoint, Doi, Fixtures.doi)),
        workContext(noOptionalDoi)
      )
    )
  }

  test(
    "recognized raw work fields ground canonical facts and preserve contradictory same-namespace evidence"
  ) {
    val raw = Fixtures.work.copy(observedIdentifiers =
      Vector(
        ObservedIdentifier(
          "DOI",
          "https://doi.org/" + Fixtures.doi,
          IdentifierInterpretation.SourceObservation
        ),
        ObservedIdentifier(
          "arxiv",
          "https://arxiv.org/abs/2301.01234v2",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    val ids = Vector(
      assertion(workEndpoint, Doi, Fixtures.doi),
      assertion(workEndpoint, Arxiv, "2301.01234")
    )
    assert(check(Vector(workEndpoint), ids, workContext(raw)))
    assert(!check(Vector(workEndpoint), ids.take(1), workContext(raw)))
    val contradictory = raw.copy(observedIdentifiers =
      raw.observedIdentifiers :+
        ObservedIdentifier(
          "doi",
          "10.9999/CONTRADICTORY",
          IdentifierInterpretation.SourceObservation
        )
    )
    val ctx = workContext(contradictory)
    assert(ResolutionValidation.check(constraints(Vector(workEndpoint), ids), ctx).isLeft)
    val allFacts = ids :+ assertion(workEndpoint, Doi, "10.9999/contradictory")
    assert(ResolutionValidation.check(constraints(Vector(workEndpoint), allFacts), ctx).isRight)
    assert(!check(Vector(workEndpoint), allFacts, ctx))
    val malformed = raw.copy(observedIdentifiers =
      Vector(ObservedIdentifier("doi", "malformed", IdentifierInterpretation.SourceObservation))
    )
    assert(!check(Vector(workEndpoint), ids.take(1), workContext(malformed)))
  }

  test(
    "OpenAlex declared DOI field roles ground all retained raw values without consulting arbitrary links"
  ) {
    val openAlex = Fixtures
      .sourceWork(SourceType.OpenAlex, "W123", 2013, "article")
      .copy(
        observedIdentifiers = Vector(
          ObservedIdentifier(
            "openalex.ids.doi",
            "https://doi.org/" + Fixtures.doi,
            IdentifierInterpretation.SourceObservation
          )
        ),
        sourceLinks = Vector(NamedText("unrelated", "https://doi.org/10.9999/unrelated"))
      )
    val endpoint = ResolutionEndpoint.Work(ref(openAlex.provenance), openAlex.workId)
    assert(
      check(Vector(endpoint), Vector(assertion(endpoint, Doi, Fixtures.doi)), workContext(openAlex))
    )
    assert(
      !check(
        Vector(endpoint),
        Vector(assertion(endpoint, Doi, "10.9999/unrelated")),
        workContext(openAlex)
      )
    )
  }

  test("work activities ground own self references and fail related-only preferred DOI metadata") {
    def ctx(a: OrcidActivityRecord): ResolutionValidationContext =
      ResolutionValidationContext.create(Vector.empty, Vector.empty, Vector(a)).toOption.get
    val raw = activity.copy(workReferences =
      Vector(
        OrcidWorkReference("DOI", "https://doi.org/" + Fixtures.doi, Some("self")),
        OrcidWorkReference("arxiv", "2301.01234v3", Some("SELF")),
        OrcidWorkReference("doi", "10.9999/related", Some("part-of"))
      )
    )
    val ids = Vector(
      assertion(activityEndpoint, Doi, Fixtures.doi),
      assertion(activityEndpoint, Arxiv, "2301.01234")
    )
    assert(check(Vector(activityEndpoint), ids, ctx(raw)))
    assert(!check(Vector(activityEndpoint), ids.take(1), ctx(raw)))
    assert(
      !check(
        Vector(activityEndpoint),
        ids :+ assertion(activityEndpoint, Doi, "10.9999/related"),
        ctx(raw)
      )
    )
    Vector(Some("part-of"), None).foreach { relationship =>
      val relatedOnly = activity.copy(workReferences =
        Vector(OrcidWorkReference("doi", Fixtures.doi, relationship))
      )
      assert(
        !check(
          Vector(activityEndpoint),
          Vector(assertion(activityEndpoint, Doi, Fixtures.doi)),
          ctx(relatedOnly)
        )
      )
    }
    val absent = activity.copy(observedDoi = None, observedWorkId = None)
    val absentEndpoint = ResolutionEndpoint.OrcidWorkActivity(ref(absent.provenance), None)
    assert(check(Vector(absentEndpoint), Vector.empty, ctx(absent)))
    assert(
      !check(
        Vector(absentEndpoint),
        Vector(assertion(absentEndpoint, Doi, Fixtures.doi)),
        ctx(absent)
      )
    )
    val malformed =
      activity.copy(workReferences = Vector(OrcidWorkReference("arxiv", "malformed", Some("self"))))
    assert(!check(Vector(activityEndpoint), ids.take(1), ctx(malformed)))
  }

  test(
    "grounding preserves snapshot binding and rejects endpoint mismatch before looking up facts"
  ) {
    val wrong = ResolutionEndpoint.Work(
      ref(Fixtures.work.provenance).copy(datasetSnapshot = "absent"),
      Fixtures.workId
    )
    assert(!check(Vector(wrong), Vector(assertion(wrong, Doi, Fixtures.doi)), context))
    val spoof = ResolutionEndpoint.OrcidProfile(ref(profile.provenance), "0000-0002-1825-0097")
    assert(!check(Vector(spoof), Vector(assertion(spoof, Orcid, Fixtures.riceOrcid)), context))
  }
}
