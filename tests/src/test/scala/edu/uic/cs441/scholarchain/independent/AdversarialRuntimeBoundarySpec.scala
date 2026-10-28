package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.services.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

class AdversarialRuntimeBoundarySpec extends AnyFunSuite {
  import AdversarialRuntimeFixture.*
  import IndependentRuntime9BFixture.{config, input}

  test(
    "duplicate vector result keys reject the whole semantic result before source objects become evidence"
  ) {
    val corpus = new Corpus
    var calls = 0
    val duplicate = new VectorProxy(corpus.vectors) {
      override def query(
          i: String,
          v: Vector[Float],
          k: Int,
          f: Map[String, String]
      ): StorageResult[Vector[VectorHit]] = {
        calls += 1
        val hit = StorageResult.value(super.query(i, v, k, f)).get.head
        StorageResult.Found(Vector(hit, hit))
      }
    }
    val result =
      new SemanticContextAgent(duplicate, corpus.objects, corpus.embeddings, corpus.index, config)
        .run(input(QueryOperation.SemanticExplanation, "A"))
    assert(calls == 1)
    result match {
      case RetrievalResult.Failed("semantic", reason) =>
        assert(reason == "semantic-filter-or-result-mismatch")
      case other => fail(s"Duplicate keys must reject all evidence: $other")
    }
  }

  test(
    "stale model version in a same-dimension vector result is rejected before it can authorize evidence"
  ) {
    val corpus = new Corpus
    var calls = 0
    val stale = new VectorProxy(corpus.vectors) {
      override def query(
          i: String,
          v: Vector[Float],
          k: Int,
          f: Map[String, String]
      ): StorageResult[Vector[VectorHit]] = {
        calls += 1
        val hits = StorageResult.value(super.query(i, v, k, f)).get
        assert(hits.size == 1)
        StorageResult.Found(
          hits.map(h =>
            h.copy(metadata =
              h.metadata
                .updated("embeddingModel", corpus.embeddings.model.copy(version = "stale-v0").tag)
            )
          )
        )
      }
    }
    val result =
      new SemanticContextAgent(stale, corpus.objects, corpus.embeddings, corpus.index, config)
        .run(input(QueryOperation.SemanticExplanation, "A"))
    assert(calls == 1)
    result match {
      case RetrievalResult.Failed("semantic", reason) =>
        assert(reason == "semantic-filter-or-result-mismatch")
      case other => fail(s"A stale model version cannot produce evidence: $other")
    }
  }

  test(
    "each required service credential omission fails configuration before composition without revealing supplied values"
  ) {
    val api = "SCHOLARCHAIN_API_KEY_SHA256"
    val internal = "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"
    val valid = Map(
      api -> Auth.sha256("synthetic-config-api"),
      internal -> Auth.sha256("synthetic-config-internal")
    )
    assert(ServiceConfig.fromEnvironment(valid).isRight)
    for (missing <- Vector(api, internal)) {
      val result = ServiceConfig.fromEnvironment(valid - missing)
      assert(result == Left("invalid-or-missing-service-configuration"))
      assert(!result.toString.contains(valid(api)) && !result.toString.contains(valid(internal)))
    }
    val canary = "synthetic-invalid-config-secret"
    assert(
      ServiceConfig.fromEnvironment(valid.updated(api, canary)) == Left(
        "invalid-or-missing-service-configuration"
      )
    )
  }
}
