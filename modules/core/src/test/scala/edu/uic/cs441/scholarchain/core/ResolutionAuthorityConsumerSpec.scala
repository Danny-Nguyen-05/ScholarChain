package edu.uic.cs441.scholarchain.resolutionconsumer

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite

/** The external package verifies that module consumers can reuse source truth without copying it.
  */
class ResolutionAuthorityConsumerSpec extends AnyFunSuite {
  import ResolutionContractFixtures.*
  import ResolutionAuthorityNamespace.*

  private def workContext(work: WorkRecord): ResolutionValidationContext =
    ResolutionValidationContext.create(Vector(work), Vector.empty, Vector.empty).toOption.get

  test("consumers receive source-bound facts for all endpoint kinds and explicit true absence") {
    assert(context.groundedAuthority(workEndpoint) == Right(Set(Doi -> Fixtures.doi)))
    assert(context.groundedAuthority(crossrefEndpoint) == Right(Set(Doi -> Fixtures.doi)))
    assert(context.groundedAuthority(mentionEndpoint) == Right(Set(Orcid -> Fixtures.riceOrcid)))
    assert(context.groundedAuthority(profileEndpoint) == Right(Set(Orcid -> profile.orcid)))
    assert(context.groundedAuthority(activityEndpoint) == Right(Set(Doi -> Fixtures.doi)))
    val noIdMention =
      ResolutionEndpoint.Mention(ref(Fixtures.work.provenance), Fixtures.berkeleyMentionId)
    assert(context.groundedAuthority(noIdMention) == Right(Set.empty))
  }

  test("consumers cannot borrow facts from another source observation or endpoint binding") {
    val absent = ResolutionEndpoint.Work(
      ref(Fixtures.work.provenance).copy(datasetSnapshot = "absent"),
      Fixtures.workId
    )
    val wrongWork = ResolutionEndpoint.Work(
      ref(Fixtures.work.provenance),
      StableIds.workIdFromDoi("10.9999/absent").toOption.get
    )
    val wrongProfile =
      ResolutionEndpoint.OrcidProfile(ref(profile.provenance), "0000-0002-1825-0097")
    Vector(absent, wrongWork, wrongProfile).foreach { endpoint =>
      assert(context.groundedAuthority(endpoint).isLeft)
    }
  }

  test("consumers receive all contradictory canonical facts without promoting arbitrary links") {
    val raw = Fixtures.work.copy(
      observedIdentifiers = Vector(
        ObservedIdentifier(
          "DOI",
          "https://doi.org/10.9999/CONTRADICTORY",
          IdentifierInterpretation.SourceObservation
        ),
        ObservedIdentifier(
          "arxiv",
          "https://arxiv.org/abs/2301.01234v2",
          IdentifierInterpretation.SourceObservation
        )
      ),
      sourceLinks = Vector(NamedText("unrelated", "https://doi.org/10.9999/unrelated"))
    )
    assert(
      workContext(raw).groundedAuthority(workEndpoint) ==
        Right(Set(Doi -> Fixtures.doi, Doi -> "10.9999/contradictory", Arxiv -> "2301.01234"))
    )
  }

  test(
    "consumers fail closed on malformed own facts and preferred DOI backed only by related evidence"
  ) {
    val malformed = Fixtures.work.copy(observedIdentifiers =
      Vector(ObservedIdentifier("doi", "malformed", IdentifierInterpretation.SourceObservation))
    )
    assert(workContext(malformed).groundedAuthority(workEndpoint).isLeft)
    val related = activity.copy(workReferences =
      Vector(OrcidWorkReference("doi", Fixtures.doi, Some("part-of")))
    )
    val ctx = ResolutionValidationContext
      .create(Vector.empty, Vector.empty, Vector(related))
      .toOption
      .get
    assert(ctx.groundedAuthority(activityEndpoint).isLeft)
  }

  test("DBLP electronic-publication resolver disagreements remain complete hard constraints") {
    val observed = Fixtures.work.copy(sourceLinks =
      Vector(
        NamedText("ee", "https://dx.doi.org/10.9999/CONTRADICTORY"),
        NamedText("ee", "https://doi.org/" + Fixtures.doi)
      )
    )
    val ctx = workContext(observed)
    val facts = Set(Doi -> Fixtures.doi, Doi -> "10.9999/contradictory")
    assert(ctx.groundedAuthority(workEndpoint) == Right(facts))
    val ids = facts.toVector.map { case (namespace, value) =>
      ResolutionIdentifierAssertion(workEndpoint, namespace, value, Vector("synthetic:ee"))
    }
    val bundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Work,
      "synthetic-ee-v1",
      hash,
      Vector(workEndpoint),
      Vector.empty,
      ids
    )
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    assert(
      ResolutionValidation
        .check(bundle.copy(authoritativeIdentifiers = ids.filter(_.value == Fixtures.doi)), ctx)
        .isLeft
    )
    assert(ResolutionValidation.checkComponent(Vector(workEndpoint), bundle, ctx, 10, 20).isLeft)
  }

  test(
    "only DBLP ee direct publication resolvers ground IDs and arxiv versions retain their base"
  ) {
    val observed = Fixtures.work.copy(sourceLinks =
      Vector(
        NamedText("ee", "https://arxiv.org/pdf/2301.01234v2.pdf"),
        NamedText("url", "https://doi.org/10.9999/table-of-contents"),
        NamedText("unrelated", "https://doi.org/10.9999/other-role"),
        NamedText("ee", "https://doi.org.evil.test/10.9999/lookalike"),
        NamedText("ee", "https://arxiv.org/help/2301.01234"),
        NamedText("ee", "https://publisher.test/paper?doi=10.9999/query")
      )
    )
    assert(
      workContext(observed).groundedAuthority(workEndpoint) == Right(
        Set(Doi -> Fixtures.doi, Arxiv -> "2301.01234")
      )
    )
    val nonDblp =
      crossref.copy(sourceLinks = Vector(NamedText("ee", "https://doi.org/10.9999/foreign-role")))
    assert(
      workContext(nonDblp).groundedAuthority(crossrefEndpoint) == Right(Set(Doi -> Fixtures.doi))
    )
  }

  test("recognized DBLP ee resolvers fail closed on malformed or ambiguous URL syntax") {
    Vector(
      "https://doi.org",
      "https://doi.org/malformed",
      "https://doi.org/10.9999/has space",
      "https://reader@doi.org/10.9999/value",
      "https://doi.org:443/10.9999/value",
      "https://arxiv.org/abs/malformed",
      "https://arxiv.org/abs/2301.01234?version=2"
    ).foreach { raw =>
      val observed = Fixtures.work.copy(sourceLinks = Vector(NamedText("ee", raw)))
      assert(workContext(observed).groundedAuthority(workEndpoint).isLeft, raw)
    }
  }

  test("DBLP DOI resolver facts use the same literal suffix semantics as preferred fields") {
    Vector(
      "https://doi.org/10.9999/encoded%2FValue",
      "https://dx.doi.org/10.9999/Value?different=10.9999/Other",
      "https://doi.org/10.9999/Value#Other",
      "https://doi.org/10.9999/(SICI)1099-1234(1999)1:2<3::AID-EXAMPLE>3.0.CO;2-X"
    ).foreach { raw =>
      val canonical = StableIds.normalizeDoi(raw).toOption.get
      val observed = Fixtures.work.copy(
        workId = StableIds.workIdFromDoi(canonical).toOption.get,
        doi = Some(canonical),
        externalUrl = Some(raw),
        authors = Vector.empty,
        provenance = Fixtures.work.provenance.copy(sourceUri = Some(raw)),
        sourceLinks = Vector(NamedText("ee", raw))
      )
      val endpoint = ResolutionEndpoint.Work(ref(observed.provenance), observed.workId)
      val ctx = workContext(observed)
      assert(ctx.groundedAuthority(endpoint) == Right(Set(Doi -> canonical)), raw)
      assert(
        ctx.groundedElectronicPublicationFacts(endpoint) ==
          Right(Vector((NamedText("ee", raw), Doi, canonical))),
        raw
      )
    }
  }

  test("literal DOI resolver differences cannot be erased by URL decoding or suffix stripping") {
    val raw = Vector(
      "https://doi.org/10.9999/value%2Fpart",
      "https://doi.org/10.9999/value/part",
      "https://doi.org/10.9999/value?part=1",
      "https://doi.org/10.9999/value"
    )
    val observed = Fixtures.work.copy(sourceLinks = raw.map(NamedText("ee", _)))
    val ctx = workContext(observed)
    val canonical = raw.map(StableIds.normalizeDoi(_).toOption.get)
    val facts = canonical.map(Doi -> _).toSet + (Doi -> Fixtures.doi)
    assert(ctx.groundedAuthority(workEndpoint) == Right(facts))
    val bundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Work,
      "synthetic-literal-doi-v1",
      hash,
      Vector(workEndpoint),
      Vector.empty,
      facts.toVector.map { case (namespace, value) =>
        ResolutionIdentifierAssertion(
          workEndpoint,
          namespace,
          value,
          Vector("synthetic:literal-doi")
        )
      }
    )
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    assert(ResolutionValidation.checkComponent(Vector(workEndpoint), bundle, ctx, 10, 20).isLeft)
    assert(
      ResolutionValidation
        .check(bundle.copy(authoritativeIdentifiers = bundle.authoritativeIdentifiers.take(1)), ctx)
        .isLeft
    )
  }

  test(
    "publication fact catalogs preserve raw roles and endpoint binding without promoting links"
  ) {
    val raw = "https://arxiv.org/pdf/2301.01234v2.pdf"
    val observed = Fixtures.work.copy(sourceLinks =
      Vector(
        NamedText("ee", raw),
        NamedText("ee", raw),
        NamedText("url", "https://doi.org/10.9999/contents"),
        NamedText("ee", "https://doi.org.evil.test/10.9999/lookalike")
      )
    )
    val ctx = workContext(observed)
    assert(
      ctx.groundedElectronicPublicationFacts(workEndpoint) ==
        Right(Vector.fill(2)((NamedText("ee", raw), Arxiv, "2301.01234")))
    )
    assert(context.groundedElectronicPublicationFacts(profileEndpoint) == Right(Vector.empty))
    assert(context.groundedElectronicPublicationFacts(crossrefEndpoint) == Right(Vector.empty))
    val absent = ResolutionEndpoint.Work(
      ref(observed.provenance).copy(datasetSnapshot = "absent"),
      observed.workId
    )
    assert(ctx.groundedElectronicPublicationFacts(absent).isLeft)
    val malformed =
      observed.copy(sourceLinks = Vector(NamedText("ee", "https://doi.org/malformed")))
    assert(workContext(malformed).groundedElectronicPublicationFacts(workEndpoint).isLeft)
  }
}
