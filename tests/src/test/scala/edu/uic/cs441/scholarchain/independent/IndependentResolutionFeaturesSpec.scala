package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite

class IndependentResolutionFeaturesSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*

  private def features(
      a: WorkRecord,
      b: WorkRecord,
      left: ResolutionEndpoint,
      right: ResolutionEndpoint
  ) = {
    val in =
      ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, Vector.empty).toOption.get
    val candidate = DerivedPair(
      pair(left, right),
      Vector.empty,
      (in.refs(left) ++ in.refs(right)).distinct.sorted
    )
    FeatureExtractor.extract(candidate, in, ResolutionPolicy.example).map(f => f.name -> f).toMap
  }

  test("author order uses the documented reciprocal distance rather than binary ordinal equality") {
    val a = work("conf/independent/OrderA", names = Vector("First Person", "Alex Example"))
    val b = work(
      "conf/independent/OrderB",
      names = Vector("First Person", "Second Person", "Third Person", "Alex Example")
    )
    val result = features(a, b, mention(a, 1), mention(b, 3))
    // Positions 2 and 4: 1/(1+|2-4|)=1/3.
    assert(result("authorOrder").value.exists(x => math.abs(x - 1.0 / 3.0) < 1e-12))
  }

  test("identical initial letters on unrelated surnames are not positive initials evidence") {
    val a = work("conf/independent/InitialsA", names = Vector("Alex Allen"))
    val b = work("conf/independent/InitialsB", names = Vector("Alice Adams"))
    val result = features(a, b, mention(a), mention(b))
    assert(result("initials").value.contains(0.0))
    val sameSurname = work("conf/independent/InitialsC", names = Vector("A. Allen"))
    assert(
      features(a, sameSurname, mention(a), mention(sameSurname))("initials").value.contains(1.0)
    )
  }

  test("identifiers in disjoint namespaces are unavailable rather than contradictory evidence") {
    val a = work("conf/independent/IdentifierA", doi = Some("10.5555/namespace-only"))
    val original = work("conf/independent/IdentifierB")
    val b = original.copy(arxivId = Some("2301.01234"), workId = "work:arxiv:2301.01234")
    val result = features(a, b, endpoint(a), endpoint(b))
    assert(result("identifier").value.isEmpty)
    assert(result("identifier").missingReason.nonEmpty)
  }

  test(
    "raw names and titles remain source truth while normalized comparison handles Unicode and markup"
  ) {
    val raw = "<i>Ｄistributed</i> Storage — Transactions"
    val a = work("conf/independent/UnicodeA", title = raw)
    val b = work("conf/independent/UnicodeB", title = "Distributed storage transactions")
    val result = features(a, b, endpoint(a), endpoint(b))
    assert(result("title").value.contains(1.0))
    assert(a.title == raw)
    assert(Normalization.nameTokens("García, José") == Vector("garcia", "jose"))
    assert(
      Normalization.nameTokens("Jose Garcia").sorted == Normalization
        .nameTokens("García, José")
        .sorted
    )
  }

  test(
    "copies of one publication do not create independent coauthor context for researcher acceptance"
  ) {
    val names = Vector("Alex Example", "Blair Collaborator")
    val a = work("conf/independent/CopyA", names = names, doi = Some("10.5555/same-publication"))
    val b = work("W700000030", names = names, doi = a.doi, source = SourceType.OpenAlex)
    assert(a.workId == b.workId)
    val result = features(a, b, mention(a), mention(b))
    assert(
      result("coauthorOverlap").value.isEmpty,
      "a duplicated author list cannot masquerade as independent cross-publication context"
    )
  }
}
