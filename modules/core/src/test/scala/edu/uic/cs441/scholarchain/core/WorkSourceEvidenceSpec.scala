package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite

class WorkSourceEvidenceSpec extends AnyFunSuite {
  test("declared identifier roles and repeated links round trip separately from preferred DOI") {
    val base = Fixtures.sourceWork(SourceType.OpenAlex, "W2741800001", 2020, "article")
    val observed = base.copy(
      observedIdentifiers = Vector(
        ObservedIdentifier(
          "openalex.doi",
          "https://doi.org/" + Fixtures.doi,
          IdentifierInterpretation.SourceObservation
        ),
        ObservedIdentifier(
          "openalex.ids.doi",
          "10.1000/secondary",
          IdentifierInterpretation.SourceObservation
        )
      ),
      sourceLinks =
        Vector(NamedText("ee", "https://example.test/a"), NamedText("ee", "https://example.test/a"))
    )
    assert(DomainValidation.check(observed).isRight)
    assert(CoreJson.parse[WorkRecord](CoreJson.compact(observed)) == Right(observed))
    assert(observed.doi == base.doi)
    assert(
      DomainValidation
        .check(
          observed
            .copy(observedIdentifiers = observed.observedIdentifiers.map(_.copy(value = "bad DOI")))
        )
        .isLeft
    )
    assert(DomainValidation.check(observed.copy(sourceLinks = Vector(NamedText("ee", " ")))).isLeft)
    assert(
      DomainValidation
        .check(
          observed.copy(observedIdentifiers =
            observed.observedIdentifiers
              .map(_.copy(interpretation = IdentifierInterpretation.ValidatedExternal))
          )
        )
        .isLeft
    )
  }

  test("older work JSON without additive evidence fields reads with empty defaults") {
    val old = ujson.read(CoreJson.compact(Fixtures.work)).obj
    old.remove("observedIdentifiers")
    old.remove("sourceLinks")
    assert(CoreJson.parse[WorkRecord](ujson.write(old)) == Right(Fixtures.work))
  }
}
