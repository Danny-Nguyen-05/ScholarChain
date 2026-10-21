package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.IdentifierRules
import org.scalatest.funsuite.AnyFunSuite

/** Explicit expected tokens come from identifier syntax, independently of matching weights. */
class IndependentIdentifierNormalizationSpec extends AnyFunSuite {
  test("DOI and ORCID spelling normalizes without accepting an invalid checksum") {
    assert(
      IdentifierRules.normalize("doi", "https://doi.org/10.5555/Distributed.Storage") ==
        Right("10.5555/distributed.storage")
    )
    assert(
      IdentifierRules.normalize("doi", "DOI:10.5555/Distributed.Storage") ==
        Right("10.5555/distributed.storage")
    )
    assert(
      IdentifierRules.normalize("orcid", "https://orcid.org/0000-0002-1825-0097") ==
        Right("0000-0002-1825-0097")
    )
    assert(IdentifierRules.normalize("orcid", "0000-0002-1825-0098").isLeft)
    assert(IdentifierRules.normalize("doi", "https://unrelated.example/paper/1").isLeft)
  }

  test("OpenAlex work and author identifiers cannot cross their entity namespace") {
    assert(
      IdentifierRules.normalize("openalex-work", "https://openalex.org/W700000001") ==
        Right("W700000001")
    )
    assert(
      IdentifierRules.normalize("openalex-author", "https://openalex.org/A700000001") ==
        Right("A700000001")
    )
    assert(IdentifierRules.normalize("openalex-work", "A700000001").isLeft)
    assert(IdentifierRules.normalize("openalex-author", "W700000001").isLeft)
  }

  test("arXiv versions remain auditable and arbitrary URL hosts cannot masquerade as arXiv") {
    val base = IdentifierRules.normalize("arxiv", "2301.01234")
    assert(base == Right("2301.01234"))
    assert(IdentifierRules.normalize("arxiv", "https://arxiv.org/abs/2301.01234v2").isRight)
    assert(IdentifierRules.normalize("arxiv", "https://unrelated.example/abs/2301.01234").isLeft)
    assert(IdentifierRules.normalize("arxiv", "2301.01234garbage").isLeft)
  }

  test("repository normalization preserves distinct path case and meaningful query identity") {
    val a = IdentifierRules.normalize("repository-url", "https://github.com/Example/Project")
    val b = IdentifierRules.normalize("repository-url", "https://github.com/Example/project")
    assert(a.isRight && b.isRight)
    assert(a != b, "case-sensitive repository paths must not silently collapse")
    val queryA = IdentifierRules.normalize("repository-url", "https://example.org/repo?id=1")
    val queryB = IdentifierRules.normalize("repository-url", "https://example.org/repo?id=2")
    assert(queryA.isRight && queryB.isRight && queryA != queryB)
    val escaped = IdentifierRules.normalize("repository-url", "https://example.org/a%2Fb")
    val separate = IdentifierRules.normalize("repository-url", "https://example.org/a/b")
    assert(
      escaped.isRight && separate.isRight && escaped != separate,
      "an escaped slash is not a path separator"
    )
    val escapedQuery =
      IdentifierRules.normalize("repository-url", "https://example.org/repo?q=a%26b")
    val separateQuery =
      IdentifierRules.normalize("repository-url", "https://example.org/repo?q=a&b")
    assert(
      escapedQuery.isRight && separateQuery.isRight && escapedQuery != separateQuery,
      "an escaped ampersand is not a query separator"
    )
    assert(IdentifierRules.normalize("repository-url", "javascript:alert(1)").isLeft)
    assert(IdentifierRules.normalize("repository-url", "file:///tmp/repository").isLeft)
  }

  test("Semantic Scholar syntax is covered without introducing a live source") {
    val paper = "a" * 40
    assert(IdentifierRules.normalize("semantic-scholar-work", paper).isRight)
    assert(IdentifierRules.normalize("semantic-scholar-work", "not-an-id").isLeft)
    assert(IdentifierRules.normalize("semantic-scholar-author", "12345") == Right("12345"))
    assert(IdentifierRules.normalize("semantic-scholar-author", paper).isLeft)
    assert(IdentifierRules.normalize("unknown-authority", "anything").isLeft)
  }
}
