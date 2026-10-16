package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.writeJs

class IndependentResolutionPolicySpec extends AnyFunSuite {
  test(
    "runtime policy and config reject unknown fields recursively and simultaneous legacy knobs"
  ) {
    val policy = writeJs(ResolutionPolicy.example)
    policy("work")("acceptThreshhold") = ujson.Num(0.9)
    assert(ResolutionPolicy.parse(policy.render()).isLeft)
    val config = writeJs(ResolutionConfig.example)
    config("entityResolution") = ujson.Obj("acceptThreshold" -> 0.95)
    assert(ResolutionConfig.parse(config.render()).isLeft)
    val nested = writeJs(ResolutionConfig.example)
    nested("adjudication")("hiddenProviderModel") = ujson.Str("live-model")
    assert(ResolutionConfig.parse(nested.render()).isLeft)
  }

  test("threshold gap and entire uncertain band are validated before processing") {
    val base = ResolutionPolicy.example
    Vector(
      base.work.copy(rejectThreshold = base.work.acceptThreshold),
      base.work.copy(llmBandMin = base.work.rejectThreshold),
      base.work.copy(llmBandMax = base.work.acceptThreshold),
      base.work.copy(llmBandMin = 0.85, llmBandMax = 0.65),
      base.work.copy(acceptThreshold = Double.NaN),
      base.work.copy(weights = base.work.weights.updated("title", -1.0))
    ).foreach(w => assert(ResolutionPolicy.validate(base.copy(work = w)).isLeft))
    assert(ResolutionPolicy.validate(base).isRight)
  }

  test("duplicate raw JSON keys cannot silently override policy or generation settings") {
    val base = writeJs(ResolutionPolicy.example).render()
    val duplicateWeights = base.replaceFirst("\"weights\":\\{", "\"weights\":{\"title\":0.123,")
    assert(duplicateWeights != base)
    assert(ResolutionPolicy.parse(duplicateWeights).isLeft)
    val config = writeJs(ResolutionConfig.example).render()
    val duplicateSchema = config.replaceFirst("\\{", "{\"schemaVersion\":\"wrong-first-value\",")
    assert(ResolutionConfig.parse(duplicateSchema).isLeft)
  }

  test("policy refuses to count correlated name or bibliography features as independent groups") {
    val base = ResolutionPolicy.example
    val researcher = base.researcher.copy(featureGroups =
      base.researcher.featureGroups.updated("initials", "independent-initials")
    )
    assert(ResolutionPolicy.validate(base.copy(researcher = researcher)).isLeft)
    val work =
      base.work.copy(featureGroups = base.work.featureGroups.updated("venue", "independent-venue"))
    assert(ResolutionPolicy.validate(base.copy(work = work)).isLeft)
  }

  test("policy fingerprint ignores object key order but changes with every effective setting") {
    val base = ResolutionPolicy.example
    def reverse(value: ujson.Value): ujson.Value = value match {
      case o: ujson.Obj => ujson.Obj.from(o.value.toVector.reverse.map((k, v) => k -> reverse(v)))
      case a: ujson.Arr => ujson.Arr.from(a.value.map(reverse))
      case other        => other
    }
    val reordered = ResolutionPolicy.parse(reverse(writeJs(base)).render()).toOption.get
    assert(base.fingerprint == reordered.fingerprint)
    assert(base.fingerprint != base.copy(policyVersion = "independent-policy-new").fingerprint)
    assert(
      base.fingerprint != base
        .copy(sourceReliability = base.sourceReliability.updated("DBLP", 0.8))
        .fingerprint
    )
    val config = ResolutionConfig.example
    assert(
      config.fingerprint != config
        .copy(blocking = config.blocking.copy(maxPairsPerRun = config.blocking.maxPairsPerRun + 1))
        .fingerprint
    )
  }

  test("offline configuration rejects live provider and unbounded or monetary execution") {
    val base = ResolutionConfig.example
    Vector(
      base.adjudication.copy(provider = "live-provider"),
      base.adjudication.copy(maxSpendUsd = 1.0),
      base.adjudication.copy(maxRetries = 100),
      base.adjudication.copy(maxConcurrentCalls = 2),
      base.adjudication.copy(timeoutMs = 0),
      base.adjudication.copy(maxResponseBytes = 0)
    ).foreach(a => assert(ResolutionConfig.validate(base.copy(adjudication = a)).isLeft))
  }
}
