package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite

/** External 5B blocker regressions, independently specified before production repairs. */
class IndependentResolutionRepairSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  private def input(
      works: Vector[WorkRecord],
      affiliations: Vector[MentionAffiliation] = Vector.empty
  ) = {
    val result =
      ResolutionInput.create(works, Vector.empty, Vector.empty, Vector.empty, affiliations)
    assert(result.isRight, result.toString)
    result.toOption.get
  }
  private def comparison(a: ResolutionEndpoint, b: ResolutionEndpoint, in: ResolutionInput) =
    DerivedPair(pair(a, b), Vector.empty, (in.refs(a) ++ in.refs(b)).distinct.sorted)
  private def extracted(
      a: WorkRecord,
      b: WorkRecord,
      affiliations: Vector[MentionAffiliation] = Vector.empty,
      researcher: Boolean = false
  ) = {
    val in = input(Vector(a, b), affiliations)
    val (left, right) = if (researcher) (mention(a), mention(b)) else (endpoint(a), endpoint(b))
    FeatureExtractor
      .extract(comparison(left, right, in), in, ResolutionPolicy.example)
      .map(f => f.name -> f)
      .toMap
  }

  test("B1 accepted literal DOI resolver tokens remain exact source-bound publication facts") {
    val raw = Vector(
      "10.5555/a%2Fb",
      "10.5555/a?b",
      "10.5555/(SICI)1097-4571(199912)50:14<1258::AID-ASI2>3.0.CO;2-X"
    )
    raw.zipWithIndex.foreach { case (token, i) =>
      val canonical = StableIds.normalizeDoi(token).toOption.get
      val observed = work(s"conf/independent/Literal$i", doi = Some(canonical))
        .copy(sourceLinks = Vector(NamedText("ee", "https://doi.org/" + token)))
      assert(DomainValidation.check(observed).isRight)
      val in = input(Vector(observed))
      val facts = in.context.groundedAuthority(endpoint(observed)).toOption.get
      assert(facts == Set(ResolutionAuthorityNamespace.Doi -> canonical))
    }
    val canonical = StableIds.normalizeDoi("10.5555/a%2Fb").toOption.get
    val conflicted = work("conf/independent/LiteralConflict", doi = Some(canonical)).copy(
      sourceLinks = Vector(
        NamedText("ee", "https://doi.org/10.5555/a%2Fb"),
        NamedText("ee", "https://doi.org/10.5555/other?literal")
      )
    )
    val peer = work("conf/independent/LiteralPeer", doi = Some(canonical))
    val in = input(Vector(conflicted, peer))
    val decision = ResolutionEngine
      .classify(comparison(endpoint(conflicted), endpoint(peer), in), in, ResolutionPolicy.example)
      .toOption
      .get
    assert(decision.outcome == MatchOutcome.Conflict)
  }

  test(
    "B2 incomparable venue namespaces are unavailable while same namespace comparisons remain binary"
  ) {
    val a = work("conf/independent/VenueA").copy(venueId = Some("venue:dblp-booktitle:sigmod"))
    val b = work("W700000090", source = SourceType.OpenAlex)
      .copy(venueId = Some("venue:openalex:S700000090"))
    val absent = extracted(a, b)("venue")
    assert(absent.value.isEmpty)
    assert(absent.missingReason.contains("UNAVAILABLE_INCOMPARABLE_VENUE_NAMESPACES"))
    val same = work("conf/independent/VenueSame").copy(venueId = a.venueId)
    val different =
      work("conf/independent/VenueDifferent").copy(venueId = Some("venue:dblp-booktitle:icde"))
    assert(extracted(a, same)("venue").value.contains(1.0))
    assert(extracted(a, different)("venue").value.contains(0.0))
  }

  test("B2 affiliation representations compare only common namespaces without unrelated dilution") {
    val a = work("conf/independent/AffiliationLeft")
    val b = work("conf/independent/AffiliationRight")
    def aff(
        w: WorkRecord,
        ror: Option[String] = None,
        ringgold: Option[String] = None,
        name: Option[String] = None
    ) =
      MentionAffiliation(
        SchemaVersions.domain,
        w.authors.head.mentionId,
        w.source,
        w.sourceRecordId,
        w.provenance.datasetSnapshot,
        name,
        ror,
        ringgold,
        ror.map(r => "institution:ror:" + r).orElse(ringgold.map(r => "institution:ringgold:" + r)),
        IndependentResolutionFixtures.note,
        w.provenance
      )
    val ror = aff(a, ror = Some("03yrm5c26"))
    val name = aff(b, name = Some("Independent Systems Lab"))
    val incomparable = extracted(a, b, Vector(ror, name), researcher = true)("affiliation")
    assert(incomparable.value.isEmpty)
    assert(incomparable.missingReason.contains("UNAVAILABLE_INCOMPARABLE_AFFILIATION_NAMESPACES"))
    assert(
      extracted(a, b, Vector(ror, aff(b, ringgold = Some("12345"))), researcher = true)(
        "affiliation"
      ).value.isEmpty
    )
    val sameWithExtraName = aff(b, ror = Some("03yrm5c26"), name = Some("Independent Systems Lab"))
    assert(
      extracted(a, b, Vector(ror, sameWithExtraName), researcher = true)("affiliation").value
        .contains(1.0)
    )
    assert(
      extracted(a, b, Vector(ror, aff(b, ror = Some("01an7q238"))), researcher = true)(
        "affiliation"
      ).value.contains(0.0)
    )
  }

  test("B2 hand-calculated available-feature weighted score excludes incomparable venue evidence") {
    val a =
      work("conf/independent/WeightedVenueA").copy(venueId = Some("venue:dblp-booktitle:sigmod"))
    val b = work("W700000091", source = SourceType.OpenAlex)
      .copy(venueId = Some("venue:openalex:S700000091"))
    val in = input(Vector(a, b))
    val base = ResolutionPolicy.example
    val policy = base.copy(work = base.work.copy(bibliographicEnabled = false))
    val decision =
      ResolutionEngine.classify(comparison(endpoint(a), endpoint(b), in), in, policy).toOption.get
    // Title=1, authors=1, year=1. Incomparable venue is absent: (.5+.3+.1)/(.5+.3+.1)=1.
    assert(decision.score.contains(1.0))
    assert(
      decision.outcome == MatchOutcome.Accepted && decision.path == ResolutionDecisionPath.Scored
    )
  }

  test("N5 identifier catalog represents every grounded DBLP publication link authority") {
    val observed = work("conf/independent/CatalogLinks").copy(sourceLinks =
      Vector(
        NamedText("ee", "https://doi.org/10.5555/catalog-literal%2F"),
        NamedText("ee", "https://doi.org/10.5555/catalog-second?literal"),
        NamedText("ee", "https://arxiv.org/abs/2301.01234v2")
      )
    )
    val in = input(Vector(observed))
    val ep = endpoint(observed)
    val catalog = FeatureExtractor.identifiers(ep, in)
    val facts = in.authority(ep).map((ns, value) => ns.wire -> value)
    val catalogFacts = catalog
      .filter(_.authority)
      .flatMap(i => i.normalized.map(n => i.namespace -> n.replaceFirst("v[0-9]+$", "")))
      .toSet
    assert(facts.subsetOf(catalogFacts))
    facts.foreach { case (namespace, value) =>
      assert(
        catalog.exists(i =>
          i.namespace == namespace && i.authority && i.normalized.exists(
            _.replaceFirst("v[0-9]+$", "") == value
          )
            && i.evidenceRefs.nonEmpty && i.role.contains("sourceLinks.ee")
        )
      )
    }
  }

  test("N6 names empty after normalization remain missing rather than numeric disagreement") {
    val a = work("conf/independent/EmptyNameA", names = Vector("---"))
    val b = work("conf/independent/EmptyNameB", names = Vector("Alex Example"))
    val feature = extracted(a, b, researcher = true)("name")
    assert(feature.value.isEmpty && feature.missingReason.contains("EMPTY_NORMALIZED_NAME"))
  }
}
