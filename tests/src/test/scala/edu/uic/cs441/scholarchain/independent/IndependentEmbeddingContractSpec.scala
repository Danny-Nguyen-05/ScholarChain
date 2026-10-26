package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write}

/** All records below are synthetic contract fixtures, not observed researchers or findings. */
class IndependentEmbeddingContractSpec extends AnyFunSuite {
  private val model = EmbeddingModel("m", "v", 2)
  private val text = "hello"
  private val hash = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
  private val document = EmbeddingDocument(
    StableIds
      .chunkOrProfileId("synthetic-person", "template-v1", "researcher-profile", Some(0), text)
      .toOption
      .get,
    "researcher-profile",
    "synthetic-person",
    "2020-2026",
    "synthetic-run",
    "template-v1",
    text,
    Vector(SummarySourceRef("synthetic-source", "row-1", "title")),
    "generated-summary",
    chunkPolicyVersion = "synthetic-policy-v1",
    chunkOrdinal = 0
  )
  private def item = EmbeddingWorkItem(
    EmbeddingContracts.vectorKey(document, model),
    "researcher-profile-v1",
    document,
    "s3://synthetic-text/graph/profile.json",
    hash,
    model
  )

  test("UTF-8 content identity and model framing have independent fixed expectations") {
    assert(EmbeddingContracts.textHash(text) == hash)
    assert(model.tag == "1:m1:v1:2")
    assert(EmbeddingModel("a", "bc", 2).tag != EmbeddingModel("ab", "c", 2).tag)
    assert(model.tag != model.copy(version = "v2").tag)
    assert(model.tag != model.copy(dimension = 3).tag)
  }

  test("stable slot keys have seven explicit UTF-8 frames and exclude content and source run") {
    val slot = document.copy(
      entityId = "e",
      windowId = "w",
      templateVersion = "t",
      chunkPolicyVersion = "p",
      chunkOrdinal = 0
    )
    assert(
      EmbeddingContracts.vectorKey(slot, model) == "18:researcher-profile1:e1:w1:t1:p1:09:1:m1:v1:2"
    )
    val changedText = "changed content"
    val changed = slot.copy(
      documentId = StableIds
        .chunkOrProfileId("e", "t", "researcher-profile", Some(0), changedText)
        .toOption
        .get,
      text = changedText,
      runId = "new-source-run"
    )
    assert(changed.documentId != slot.documentId)
    assert(
      EmbeddingContracts.vectorKey(changed, model) == EmbeddingContracts.vectorKey(slot, model)
    )
    assert(
      EmbeddingContracts
        .vectorKey(slot.copy(entityId = "é"), model)
        .startsWith("18:researcher-profile2:é")
    )
    Vector(
      slot.copy(templateVersion = "t2"),
      slot.copy(chunkPolicyVersion = "p2"),
      slot.copy(chunkOrdinal = 1)
    ).foreach { other =>
      assert(
        EmbeddingContracts.vectorKey(other, model) != EmbeddingContracts.vectorKey(slot, model)
      )
    }
    assert(
      EmbeddingContracts.vectorKey(slot, model.copy(version = "v2")) != EmbeddingContracts
        .vectorKey(slot, model)
    )
  }

  test("legacy decoding retains defaults but incomplete slot identity is rejected") {
    val legacy = upickle.default.writeJs(document).obj
    legacy.remove("chunkPolicyVersion")
    legacy.remove("chunkOrdinal")
    val decoded = read[EmbeddingDocument](ujson.Obj.from(legacy))
    assert(decoded.chunkPolicyVersion == "" && decoded.chunkOrdinal == -1)
    assert(EmbeddingValidation.document(decoded).contains("invalid-chunk-policy-version"))
    assert(EmbeddingValidation.document(decoded).contains("invalid-chunk-ordinal"))
  }

  test("wire work records preserve source and reject hash, index and model-key substitutions") {
    assert(EmbeddingValidation.workItem(item).isEmpty)
    assert(read[EmbeddingWorkItem](write(item)) == item)
    assert(
      EmbeddingValidation.workItem(item.copy(textHash = "0" * 64)).contains("text-hash-mismatch")
    )
    assert(
      EmbeddingValidation
        .workItem(item.copy(indexName = "paper-abstract-v1"))
        .contains("document-index-mismatch")
    )
    assert(
      EmbeddingValidation.workItem(item.copy(embeddingModel = model.copy(version = "v2"))).nonEmpty
    )
    assert(
      EmbeddingValidation
        .workItem(item.copy(textS3Uri = "https://synthetic-text/graph/profile.json"))
        .contains("invalid-text-s3-uri")
    )
  }

  test("semantic results cannot acquire authority for exact graph facts or metrics") {
    val context = SemanticContext(
      Vector(
        SemanticContextItem(
          item.vectorKey,
          0.75,
          "researcher-profile",
          item.textS3Uri,
          "hello",
          hash
        )
      )
    )
    assert(EmbeddingValidation.context(context).isEmpty)
    assert(read[SemanticContext](write(context)) == context)
    Vector(
      context.copy(exactMetricsAllowed = true),
      context.copy(graphClaimsAllowed = true),
      context.copy(usage = "verified-evidence")
    ).foreach(c =>
      assert(EmbeddingValidation.context(c).contains("semantic-context-is-not-evidence"))
    )
    assert(
      EmbeddingValidation
        .context(context.copy(items = context.items.map(_.copy(score = Double.NaN))))
        .nonEmpty
    )
  }

  test(
    "compact vector metadata excludes source text and rejects arbitrary or oversized identity fields"
  ) {
    val metadata = EmbeddingVectorMetadata(
      document.documentType,
      document.entityId,
      document.windowId,
      document.runId,
      item.textS3Uri,
      hash,
      model,
      document.templateVersion,
      document.documentId,
      identityFields = Map("researcherId" -> "synthetic-person"),
      chunkPolicyVersion = document.chunkPolicyVersion,
      chunkOrdinal = document.chunkOrdinal
    )
    assert(EmbeddingValidation.metadata(metadata).isEmpty)
    assert(metadata.compact("embeddingModelId") == "m")
    assert(metadata.compact("embeddingModelVersion") == "v")
    assert(metadata.compact("dimension") == "2")
    assert(metadata.compact("textHash") == hash)
    assert(!metadata.compact.contains("text") && !metadata.compact.contains("sourceReferences"))
    assert(!metadata.compact.contains("excerpt"))
    val arbitrary = metadata.copy(identityFields = Map("text" -> ("private payload " * 100)))
    assert(EmbeddingValidation.metadata(arbitrary).contains("invalid-identity-metadata"))
    assert(!arbitrary.compact.contains("text"))
    assert(
      EmbeddingValidation
        .metadata(metadata.copy(identityFields = Map("researcherId" -> ("x" * 257))))
        .nonEmpty
    )
  }

  test("vector results require finite dimensions and sanitized typed failure codes") {
    assert(EmbeddingValidation.result(EmbeddingSuccess(Vector(1f, 0f), model, 1)).isEmpty)
    assert(EmbeddingValidation.result(EmbeddingSuccess(Vector(1f), model, 1)).nonEmpty)
    assert(EmbeddingValidation.result(EmbeddingSuccess(Vector(Float.NaN, 0f), model, 1)).nonEmpty)
    assert(
      EmbeddingValidation.result(EmbeddingFailure("provider-throttled", true, model, 2)).isEmpty
    )
    assert(
      EmbeddingValidation
        .result(EmbeddingFailure("request contained sensitive body", false, model, 1))
        .nonEmpty
    )
  }
}
