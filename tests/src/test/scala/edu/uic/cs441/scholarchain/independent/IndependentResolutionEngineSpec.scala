package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite

class IndependentResolutionEngineSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*

  private def source(
      works: Vector[WorkRecord],
      profiles: Vector[OrcidProfileRecord] = Vector.empty
  ) =
    ResolutionInput.create(works, profiles, Vector.empty, Vector.empty).toOption.get

  private def derived(
      a: ResolutionEndpoint,
      b: ResolutionEndpoint,
      input: ResolutionInput
  ): DerivedPair =
    DerivedPair(pair(a, b), Vector.empty, (input.refs(a) ++ input.refs(b)).distinct.sorted)

  private def classify(
      a: WorkRecord,
      b: WorkRecord,
      policy: ResolutionPolicy = ResolutionPolicy.example
  ) = {
    val in = source(Vector(a, b))
    ResolutionEngine.classify(derived(endpoint(a), endpoint(b), in), in, policy).toOption.get
  }

  test("a conflicting declared DOI wins over equal preferred DOI and equal work ID") {
    val doi = Some("10.5555/shared-but-conflicted")
    val a = work("conf/independent/ConflictA", doi = doi)
    val b = work("W700000010", doi = doi, source = SourceType.OpenAlex).copy(
      observedIdentifiers = Vector(
        ObservedIdentifier(
          "openalex.ids.doi",
          "https://doi.org/10.5555/other-observed",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    assert(a.workId == b.workId)
    val result = classify(a, b)
    assert(result.outcome == MatchOutcome.Conflict)
    assert(result.path == ResolutionDecisionPath.HardConflict)
  }

  test(
    "different direct ORCIDs cannot merge through equal name and shared OpenAlex author hypothesis"
  ) {
    val oa = Map(1 -> "A700000001")
    val a = work("conf/independent/OrcidA", orcids = Map(1 -> orcidA), authorIds = oa)
    val b = work("conf/independent/OrcidB", orcids = Map(1 -> orcidB), authorIds = oa)
    val in = source(Vector(a, b))
    val result = ResolutionEngine
      .classify(derived(mention(a), mention(b), in), in, ResolutionPolicy.example)
      .toOption
      .get
    assert(result.outcome == MatchOutcome.Conflict)
    assert(result.path == ResolutionDecisionPath.HardConflict)
  }

  test(
    "matching direct identifiers use exact path without treating work equality as author equality"
  ) {
    val doi = Some("10.5555/exact-independent")
    val a = work("conf/independent/ExactA", doi = doi)
    val b = work("conf/independent/ExactB", doi = doi)
    val exact = classify(a, b)
    assert(exact.outcome == MatchOutcome.Accepted)
    assert(exact.path == ResolutionDecisionPath.ExactIdentifier)
    val in = source(Vector(a, b))
    val names = ResolutionEngine
      .classify(derived(mention(a), mention(b), in), in, ResolutionPolicy.example)
      .toOption
      .get
    assert(
      names.outcome != MatchOutcome.Accepted,
      "same paper, name and ordinal are correlated context, not confirmed researcher identity"
    )
    val identifiedA = a.copy(authors =
      a.authors.map(
        _.copy(
          observedOrcid = Some(orcidA),
          identityStatus = MentionIdentityStatus.ExternalIdentifierObserved
        )
      )
    )
    val p = profile(orcidA)
    val researcherInput = source(Vector(identifiedA), Vector(p))
    val researcher = ResolutionEngine
      .classify(
        derived(
          mention(identifiedA),
          ResolutionEndpoint.OrcidProfile(ref(p.provenance), orcidA),
          researcherInput
        ),
        researcherInput,
        ResolutionPolicy.example
      )
      .toOption
      .get
    assert(
      researcher.outcome == MatchOutcome.Accepted && researcher.path == ResolutionDecisionPath.ExactIdentifier
    )
  }

  test("hand-computed 2/3 weighted score obeys inclusive accept and reject threshold boundaries") {
    // Title token intersection={alpha}, union={alpha,beta,gamma}: 1/3.
    // Same year: 1. Equal weights and neutral reliability => (1/3+1)/2 = 2/3.
    val a = work("conf/independent/ScoreA", title = "alpha beta", names = Vector.empty)
    val b = work("conf/independent/ScoreB", title = "alpha gamma", names = Vector.empty)
    val base = ResolutionPolicy.example
    val workPolicy = base.work.copy(
      weights = Map("title" -> 1.0, "yearCompatibility" -> 1.0),
      featureGroups = Map("title" -> "bibliography", "yearCompatibility" -> "chronology"),
      requiredGroups = Vector("bibliography", "chronology"),
      minimumIndependentGroupsForAccept = 2,
      supportiveFeatureMin = 0.3,
      bibliographicEnabled = false,
      rejectThreshold = 0.2,
      acceptThreshold = 2.0 / 3.0,
      llmBandMin = 0.3,
      llmBandMax = 0.6
    )
    val acceptPolicy = base.copy(work = workPolicy)
    assert(ResolutionPolicy.validate(acceptPolicy).isRight)
    val accepted = classify(a, b, acceptPolicy)
    assert(accepted.score.exists(x => math.abs(x - 2.0 / 3.0) < 1e-12))
    assert(
      accepted.outcome == MatchOutcome.Accepted && accepted.path == ResolutionDecisionPath.Scored
    )
    val rejected = classify(
      a,
      b,
      base.copy(work =
        workPolicy.copy(
          rejectThreshold = 2.0 / 3.0,
          acceptThreshold = 0.95,
          llmBandMin = 0.7,
          llmBandMax = 0.8
        )
      )
    )
    assert(rejected.outcome == MatchOutcome.Rejected)
    val unresolved = classify(
      a,
      b,
      base.copy(work =
        workPolicy.copy(
          rejectThreshold = 0.5,
          acceptThreshold = 0.9,
          llmBandMin = 0.6,
          llmBandMax = 0.8
        )
      )
    )
    assert(unresolved.outcome == MatchOutcome.Unresolved)
    val lessReliable = classify(
      a,
      b,
      acceptPolicy.copy(sourceReliability = acceptPolicy.sourceReliability.updated("DBLP", 0.6))
    )
    assert(
      lessReliable.score.exists(x => math.abs(x - 0.4) < 1e-12),
      "2/3 weighted evidence times the configured 0.6 reliability is 0.4"
    )
  }

  test("missing evidence stays unavailable rather than zero, perfect similarity or prep sentinel") {
    val a = work("conf/independent/MissingA", year = None, names = Vector.empty)
    val b = work("conf/independent/MissingB", year = None, names = Vector.empty)
    val result = classify(a, b)
    val features = result.features.map(f => f.name -> f).toMap
    Vector("authorOverlap", "yearCompatibility", "venue", "citationNeighborhood").foreach { name =>
      assert(features(name).value.isEmpty, s"$name must remain missing")
      assert(features(name).missingReason.nonEmpty)
    }
    assert(result.outcome != MatchOutcome.Accepted)
    assert(result.features.flatMap(_.value).forall(n => n.isFinite && n >= 0 && n <= 1))
    val base = ResolutionPolicy.example
    val noAvailablePolicy = base.copy(work =
      base.work.copy(
        weights = Map("authorOverlap" -> 1.0, "yearCompatibility" -> 1.0),
        featureGroups = Map("authorOverlap" -> "authorship", "yearCompatibility" -> "chronology"),
        requiredGroups = Vector("authorship", "chronology"),
        minimumIndependentGroupsForAccept = 2,
        bibliographicEnabled = false
      )
    )
    val absent = classify(a, b, noAvailablePolicy)
    assert(absent.score.isEmpty && absent.outcome == MatchOutcome.Unresolved)
  }

  test("bibliographic path requires authors and year evidence independently of exact title") {
    val a =
      work("conf/independent/BibliographicA", names = Vector("Alex Example", "Blair Researcher"))
    val b = work("conf/independent/BibliographicB", names = a.authors.map(_.nameText))
    val base = ResolutionPolicy.example
    assert(
      !base.work.bibliographicEnabled,
      "uncalibrated runtime policy disables the exact bibliographic shortcut"
    )
    val enabled = base.copy(work = base.work.copy(bibliographicEnabled = true))
    val result = classify(a, b, enabled)
    assert(result.path == ResolutionDecisionPath.DeterministicBibliographic)
    assert(result.outcome == MatchOutcome.Accepted)
    val noYear = b.copy(year = None)
    assert(classify(a, noYear, enabled).path != ResolutionDecisionPath.DeterministicBibliographic)
    val noAuthors = b.copy(authors = Vector.empty)
    assert(
      classify(a, noAuthors, enabled).path != ResolutionDecisionPath.DeterministicBibliographic
    )
  }

  test("recognized DBLP publication links retain conflicting DOI and arXiv source facts") {
    val common = Some("10.5555/link-preferred")
    val a = work("conf/independent/LinkA", doi = common).copy(sourceLinks =
      Vector(
        NamedText("ee", "https://doi.org/10.5555/link-other"),
        NamedText("ee", "https://arxiv.org/abs/2301.01234v2")
      )
    )
    val b = work("conf/independent/LinkB", doi = common)
    val input = source(Vector(a, b))
    val facts = input.context.groundedAuthority(endpoint(a)).toOption.get
    assert(
      facts == Set(
        ResolutionAuthorityNamespace.Doi -> common.get,
        ResolutionAuthorityNamespace.Doi -> "10.5555/link-other",
        ResolutionAuthorityNamespace.Arxiv -> "2301.01234"
      )
    )
    assert(classify(a, b).outcome == MatchOutcome.Conflict)
    val candidate = derived(endpoint(a), endpoint(b), input)
    val run = ResolutionEngine
      .resolve(
        input,
        CandidatePopulation(Vector(candidate), Vector.empty, Vector.empty),
        ResolutionPolicy.example,
        ResolutionConfig.example,
        "disabled",
        None,
        runId,
        instant
      )
      .toOption
      .get
    val bundle = run.constraints.find(_.entityType == ResolutionEntityType.Work).get
    assert(
      bundle.authoritativeIdentifiers
        .filter(_.endpoint == endpoint(a))
        .map(i => i.namespace -> i.value)
        .toSet == facts
    )
  }

  test(
    "backlinks and arbitrary hosts stay weak while malformed recognized publication resolvers fail"
  ) {
    val original = work("conf/independent/WeakLink")
    val weak = original.copy(sourceLinks =
      Vector(
        NamedText("url", "https://doi.org/10.5555/backlink"),
        NamedText("ee", "https://unrelated.example/abs/2301.01234")
      )
    )
    val input = source(Vector(weak))
    assert(input.context.groundedAuthority(endpoint(weak)).contains(Set.empty))
    val malformedArxiv = original.copy(sourceLinks =
      Vector(NamedText("ee", "https://arxiv.org/abs/2301.01234?other=2301.99999"))
    )
    assert(
      ResolutionInput
        .create(Vector(malformedArxiv), Vector.empty, Vector.empty, Vector.empty)
        .isLeft
    )
  }
}
