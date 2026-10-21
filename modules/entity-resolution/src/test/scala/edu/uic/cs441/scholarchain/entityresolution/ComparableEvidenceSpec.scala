package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Files
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write

class ComparableEvidenceSpec extends AnyFunSuite {
  import ErTestData.*
  private def compare(
      a: WorkRecord,
      b: WorkRecord,
      affiliations: Vector[MentionAffiliation] = Vector.empty,
      researcher: Boolean = false
  ): (ResolutionInput, DerivedPair) = {
    val in = ResolutionInput
      .create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty, affiliations)
      .fold(e => fail(e), identity)
    val left =
      if (researcher)
        ResolutionEndpoint.Mention(ResolutionInput.ref(a.provenance), a.authors.head.mentionId)
      else endpoint(a)
    val right =
      if (researcher)
        ResolutionEndpoint.Mention(ResolutionInput.ref(b.provenance), b.authors.head.mentionId)
      else endpoint(b)
    val pair = ResolutionIds.pair(ResolutionIds.entityType(left), left, right).toOption.get
    in -> DerivedPair(pair, Vector.empty, (in.refs(left) ++ in.refs(right)).distinct.sorted)
  }
  private def aff(
      w: WorkRecord,
      ror: Option[String] = None,
      name: Option[String] = None
  ): MentionAffiliation =
    MentionAffiliation(
      SchemaVersions.domain,
      w.authors.head.mentionId,
      w.source,
      w.sourceRecordId,
      w.provenance.datasetSnapshot,
      name,
      ror,
      None,
      ror.flatMap(v => StableIds.institutionIdFromRor(v).toOption),
      "Synthetic organization evidence",
      w.provenance
    )

  test("incomparable venues are unavailable and do not dilute an otherwise unit score") {
    val a = work("conf/test/VenueLeft").copy(venueId = Some("venue:dblp-booktitle:sigmod"))
    val b = work("conf/test/VenueRight").copy(venueId = Some("venue:openalex:S123"))
    val (in, candidate) = compare(a, b)
    val classified = ResolutionEngine.classify(candidate, in, ResolutionPolicy.example).toOption.get
    val feature = classified.features.find(_.name == "venue").get
    assert(
      feature.value.isEmpty && feature.missingReason.contains(
        "UNAVAILABLE_INCOMPARABLE_VENUE_NAMESPACES"
      )
    )
    assert(classified.score.contains(1.0) && classified.outcome == MatchOutcome.Accepted)
    val same = b.copy(venueId = a.venueId); val (sameInput, samePair) = compare(a, same)
    assert(
      FeatureExtractor
        .extract(samePair, sameInput, ResolutionPolicy.example)
        .find(_.name == "venue")
        .get
        .value
        .contains(1.0)
    )
    val different = b.copy(venueId = Some("venue:dblp-booktitle:icde"));
    val (differentInput, differentPair) = compare(a, different)
    assert(
      FeatureExtractor
        .extract(differentPair, differentInput, ResolutionPolicy.example)
        .find(_.name == "venue")
        .get
        .value
        .contains(0.0)
    )
  }
  test("affiliations compare namespace partitions and use the minimum of comparable similarities") {
    val a = work("conf/test/AffLeft"); val b = work("conf/test/AffRight")
    def feature(values: Vector[MentionAffiliation]): ResolutionFeature = {
      val (in, pair) = compare(a, b, values, true);
      FeatureExtractor.extract(pair, in, ResolutionPolicy.example).find(_.name == "affiliation").get
    }
    val ror = aff(a, Some("03yrm5c26"))
    assert(
      feature(Vector(ror, aff(b, name = Some("Systems Lab")))).missingReason
        .contains("UNAVAILABLE_INCOMPARABLE_AFFILIATION_NAMESPACES")
    )
    assert(feature(Vector(ror, aff(b, Some("03yrm5c26"), Some("Systems Lab")))).value.contains(1.0))
    assert(
      feature(
        Vector(
          aff(a, Some("03yrm5c26"), Some("Left Lab")),
          aff(b, Some("03yrm5c26"), Some("Right Lab"))
        )
      ).value.contains(0.0)
    )
    val enrichment = EnrichmentLink(
      SchemaVersions.domain,
      b.source,
      b.sourceRecordId,
      b.provenance.datasetSnapshot,
      Some(b.workId),
      Some(b.authors.head.mentionId),
      EnrichmentTargetKind.Institution,
      "institution:ror:03yrm5c26",
      Some("03yrm5c26"),
      None,
      None,
      "Synthetic institution observation",
      ErTestData.run,
      b.provenance
    )
    val in = ResolutionInput
      .create(
        Vector(a, b),
        Vector.empty,
        Vector.empty,
        Vector.empty,
        Vector(ror),
        Vector(enrichment)
      )
      .fold(e => fail(e), identity)
    val left =
      ResolutionEndpoint.Mention(ResolutionInput.ref(a.provenance), a.authors.head.mentionId);
    val right =
      ResolutionEndpoint.Mention(ResolutionInput.ref(b.provenance), b.authors.head.mentionId)
    val pair = DerivedPair(
      ResolutionIds.pair(ResolutionEntityType.Researcher, left, right).toOption.get,
      Vector.empty,
      Vector.empty
    )
    assert(
      FeatureExtractor
        .extract(pair, in, ResolutionPolicy.example)
        .find(_.name == "affiliation")
        .get
        .value
        .contains(1.0)
    )
  }
  test("feature semantics are versioned and punctuation-only names remain missing") {
    val policy = ResolutionPolicy.example
    assert(
      policy.featurePolicyVersion == "er-features-v2" && policy.policyVersion == "er-offline-uncalibrated-v2"
    )
    assert(!policy.work.bibliographicEnabled)
    assert(
      ResolutionPolicy.parse(write(policy.copy(featurePolicyVersion = "er-features-v1"))).isLeft
    )
    assert(policy.fingerprint != policy.copy(featurePolicyVersion = "er-features-v1").fingerprint)
    val (in, pair) = compare(
      work("conf/test/NameEmpty", names = Vector("---")),
      work("conf/test/NameFull"),
      researcher = true
    )
    val feature = FeatureExtractor.extract(pair, in, policy).find(_.name == "name").get
    assert(feature.value.isEmpty && feature.missingReason.contains("EMPTY_NORMALIZED_NAME"))
  }
  test("input output and cache paths must be physically disjoint before IO") {
    val root = Files.createTempDirectory("er-isolation-owner-").toRealPath()
    val input = root.resolve("input"); Files.createDirectory(input)
    assert(
      PathIsolation.validate(input, root.resolve("output"), Some(root.resolve("cache"))).isRight
    )
    assert(PathIsolation.validate(input, input.resolve("output"), None).isLeft)
    assert(
      PathIsolation.validate(input, root.resolve("output"), Some(input.resolve("cache"))).isLeft
    )
    assert(
      PathIsolation
        .validate(input, root.resolve("output"), Some(root.resolve("output/cache")))
        .isLeft
    )
    val a = work("conf/test/PathsA"); val b = work("conf/test/PathsB")
    val in = ResolutionInput
      .assemble(
        Vector(a, b),
        Vector.empty,
        Vector.empty,
        Vector.empty,
        Vector.empty,
        Vector.empty,
        Vector.empty,
        None,
        Some(input)
      )
      .fold(e => fail(e), identity)
    assert(
      ResolutionEngine
        .resolve(
          in,
          CandidatePopulation(Vector.empty, Vector.empty, Vector.empty),
          ResolutionPolicy.example,
          ResolutionConfig.example,
          "disabled",
          Some(input.resolve("cache")),
          ErTestData.run,
          instant
        )
        .isLeft
    )
    val result = ResolutionEngine
      .resolve(
        in,
        CandidatePopulation(Vector.empty, Vector.empty, Vector.empty),
        ResolutionPolicy.example,
        ResolutionConfig.example,
        "disabled",
        None,
        ErTestData.run,
        instant
      )
      .fold(e => fail(e), identity)
    assert(
      LinkExporter
        .writeNew(
          input.resolve("output"),
          result,
          in,
          ResolutionPolicy.example,
          ResolutionConfig.example
        )
        .isLeft
    )
    assert(!Files.exists(input.resolve("cache")) && !Files.exists(input.resolve("output")))
  }
  test("publication catalog preserves raw links and shares core authoritative canonical values") {
    val observed = work("conf/test/Catalog").copy(sourceLinks =
      Vector(
        NamedText("ee", "https://doi.org/10.5555/catalog%2F?literal"),
        NamedText("ee", "https://arxiv.org/abs/2301.01234v2")
      )
    )
    val in = ResolutionInput
      .create(Vector(observed), Vector.empty, Vector.empty, Vector.empty)
      .fold(e => fail(e), identity)
    val catalog = FeatureExtractor.identifiers(endpoint(observed), in)
    val facts = catalog.filter(_.authority).flatMap(i => i.normalized.map(i.namespace -> _)).toSet
    assert(facts == in.authority(endpoint(observed)).map((ns, value) => ns.wire -> value))
    assert(catalog.forall(_.role == "sourceLinks.ee"))
    assert(catalog.find(_.namespace == "doi").get.raw == observed.sourceLinks.head.value)
    assert(catalog.find(_.namespace == "arxiv").get.normalized.contains("2301.01234"))
    val versionSuffix = work("conf/test/DoiVersion", doi = Some("10.5555/paper-v2"))
    val versionInput = ResolutionInput
      .create(Vector(versionSuffix), Vector.empty, Vector.empty, Vector.empty)
      .fold(e => fail(e), identity)
    assert(
      FeatureExtractor
        .identifiers(endpoint(versionSuffix), versionInput)
        .exists(i =>
          i.namespace == "doi" && i.authority && i.normalized.contains("10.5555/paper-v2")
        )
    )
  }
}
