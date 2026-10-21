package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite

/** Synthetic hard-authority contract cases, never source identity decisions or human labels. */
class ResolutionAuthoritySpec extends AnyFunSuite {
  import ResolutionContractFixtures.*

  private def bundle(
      entityType: ResolutionEntityType,
      endpoints: Vector[ResolutionEndpoint],
      assertions: Vector[ResolutionIdentifierAssertion]
  ): ResolutionGroupingConstraints =
    ResolutionGroupingConstraints(
      schema,
      entityType,
      "synthetic-authority-v1",
      hash,
      endpoints,
      Vector.empty,
      assertions
    )

  private def assertion(
      endpoint: ResolutionEndpoint,
      namespace: ResolutionAuthorityNamespace,
      value: String
  ): ResolutionIdentifierAssertion =
    ResolutionIdentifierAssertion(endpoint, namespace, value, Vector("synthetic:authority"))

  test("authority codec admits only explicit lowercase DOI arxiv and ORCID namespace wires") {
    val expected = Vector(
      ResolutionAuthorityNamespace.Doi -> "doi",
      ResolutionAuthorityNamespace.Arxiv -> "arxiv",
      ResolutionAuthorityNamespace.Orcid -> "orcid"
    )
    assert(ResolutionAuthorityNamespace.values.toVector == expected.map(_._1))
    expected.foreach { case (namespace, wire) =>
      assert(CoreJson.compact(namespace) == s"\"$wire\"")
      assert(CoreJson.parse[ResolutionAuthorityNamespace](s"\"$wire\"").contains(namespace))
    }
    Vector(
      "DOI",
      "ORCID",
      "Orcid",
      "orcid ",
      "doi-id",
      "openalex",
      "openalex-author",
      "openalex-work",
      "dblp",
      "Scopus Author ID",
      "semantic-scholar",
      "repository-url"
    ).foreach { wire =>
      assert(CoreJson.parse[ResolutionAuthorityNamespace](ujson.Str(wire).render()).isLeft)
    }
  }

  test(
    "canonical authority values validate and noncanonical representations fail before grouping"
  ) {
    val workMembers = Vector(workEndpoint, crossrefEndpoint)
    val canonicalDoi = bundle(
      ResolutionEntityType.Work,
      workMembers,
      workMembers.map(assertion(_, ResolutionAuthorityNamespace.Doi, Fixtures.doi))
    )
    assert(ResolutionValidation.checkComponent(workMembers, canonicalDoi, context, 3, 20).isRight)
    val arxivContext = ResolutionValidationContext
      .create(
        Vector(
          Fixtures.work.copy(arxivId = Some("2301.01234v2")),
          crossref.copy(arxivId = Some("2301.01234"))
        ),
        Vector.empty,
        Vector.empty
      )
      .toOption
      .get
    val canonicalArxiv = canonicalDoi.copy(authoritativeIdentifiers =
      canonicalDoi.authoritativeIdentifiers ++
        workMembers.map(assertion(_, ResolutionAuthorityNamespace.Arxiv, "2301.01234"))
    )
    assert(
      ResolutionValidation.checkComponent(workMembers, canonicalArxiv, arxivContext, 3, 20).isRight
    )
    val canonicalOrcid = bundle(
      ResolutionEntityType.Researcher,
      Vector(mentionEndpoint, profileEndpoint),
      Vector(mentionEndpoint, profileEndpoint).map(
        assertion(_, ResolutionAuthorityNamespace.Orcid, Fixtures.riceOrcid)
      )
    )
    assert(
      ResolutionValidation
        .checkComponent(canonicalOrcid.coveredEndpoints, canonicalOrcid, context, 3, 20)
        .isRight
    )

    Vector(
      "https://doi.org/" + Fixtures.doi,
      "DOI:" + Fixtures.doi,
      "10.1234/CASE",
      " " + Fixtures.doi,
      "invalid-doi"
    ).foreach { value =>
      val bad = canonicalDoi.copy(authoritativeIdentifiers =
        Vector(assertion(workEndpoint, ResolutionAuthorityNamespace.Doi, value))
      )
      assert(ResolutionValidation.check(bad, context).isLeft)
      assert(ResolutionValidation.checkComponent(workMembers, bad, context, 3, 20).isLeft)
    }
    Vector(
      "https://orcid.org/" + Fixtures.riceOrcid,
      "orcid:" + Fixtures.riceOrcid,
      " " + Fixtures.riceOrcid,
      "0000-0002-4414-6921",
      "not-an-orcid"
    ).foreach { value =>
      val bad = canonicalOrcid.copy(authoritativeIdentifiers =
        Vector(assertion(mentionEndpoint, ResolutionAuthorityNamespace.Orcid, value))
      )
      assert(ResolutionValidation.checkComponent(bad.coveredEndpoints, bad, context, 3, 20).isLeft)
    }
    Vector("arXiv:2301.01234", "2301.01234v1", "2301.01234v2", "malformed").foreach { value =>
      val bad = canonicalArxiv.copy(authoritativeIdentifiers =
        Vector(assertion(workEndpoint, ResolutionAuthorityNamespace.Arxiv, value))
      )
      assert(ResolutionValidation.checkComponent(workMembers, bad, context, 3, 20).isLeft)
    }
  }

  test("authority namespaces cannot cross work and researcher entity meaning") {
    val work = bundle(
      ResolutionEntityType.Work,
      Vector(workEndpoint),
      Vector(assertion(workEndpoint, ResolutionAuthorityNamespace.Orcid, Fixtures.riceOrcid))
    )
    assert(ResolutionValidation.check(work, context).isLeft)
    Vector(
      ResolutionAuthorityNamespace.Doi -> Fixtures.doi,
      ResolutionAuthorityNamespace.Arxiv -> "2301.01234"
    ).foreach { case (namespace, value) =>
      val researcher = bundle(
        ResolutionEntityType.Researcher,
        Vector(mentionEndpoint),
        Vector(assertion(mentionEndpoint, namespace, value))
      )
      assert(ResolutionValidation.check(researcher, context).isLeft)
    }
  }

  test(
    "canonical conflicting ORCIDs block A-B-C while aliases and noncanonical values fail closed"
  ) {
    val otherMention =
      ResolutionEndpoint.Mention(ref(Fixtures.work.provenance), Fixtures.berkeleyMentionId)
    val otherOrcid = "0000-0002-1825-0097"
    val otherProfile = profile.copy(
      orcid = otherOrcid,
      externalIds =
        Vector(ObservedIdentifier("orcid", otherOrcid, IdentifierInterpretation.ValidatedExternal)),
      provenance = profile.provenance.copy(sourceRecordId = otherOrcid)
    )
    val otherEndpoint = ResolutionEndpoint.OrcidProfile(ref(otherProfile.provenance), otherOrcid)
    val boundContext = ResolutionValidationContext
      .create(Vector(Fixtures.work), Vector(otherProfile), Vector.empty)
      .toOption
      .get
    val members = Vector(mentionEndpoint, otherMention, otherEndpoint)
    val constraints = bundle(
      ResolutionEntityType.Researcher,
      members,
      Vector(
        assertion(mentionEndpoint, ResolutionAuthorityNamespace.Orcid, Fixtures.riceOrcid),
        assertion(otherEndpoint, ResolutionAuthorityNamespace.Orcid, otherOrcid)
      )
    )
    assert(
      ResolutionValidation.checkComponent(members.take(2), constraints, boundContext, 3, 20).isRight
    )
    assert(
      ResolutionValidation.checkComponent(members.drop(1), constraints, boundContext, 3, 20).isRight
    )
    assert(ResolutionValidation.check(constraints, boundContext).isRight)
    assert(ResolutionValidation.checkComponent(members, constraints, boundContext, 3, 20).isLeft)
    val json = ujson.read(CoreJson.compact(constraints))
    json("authoritativeIdentifiers")(1)("namespace") = "ORCID"
    assert(CoreJson.parse[ResolutionGroupingConstraints](json.render()).isLeft)
    json("authoritativeIdentifiers")(1)("namespace") = "orcid"
    json("authoritativeIdentifiers")(1)("value") = "https://orcid.org/0000-0002-1825-0097"
    assert(
      CoreJson
        .parseAndValidate[ResolutionGroupingConstraints](json.render())(c =>
          ResolutionValidation.checkComponent(members, c, boundContext, 3, 20).map(_ => c)
        )
        .isLeft
    )
  }
}
