package edu.uic.cs441.scholarchain.core

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.ReadWriter

/** Entirely synthetic wire examples; IDs and claims are not observations about real researchers. */
object EmbeddingExamples {
  val model: EmbeddingModel = EmbeddingModel("fixture.embedding", "v1", 3)
  val entity: String = "researcher:dblp:" + "b" * 64
  def contentId(text: String, ordinal: Int = 0): String = StableIds
    .chunkOrProfileId(entity, "fixture-id-source-v1", "researcher-profile", Some(ordinal), text)
    .toOption
    .get
  val document: EmbeddingDocument = EmbeddingDocument(
    contentId("Fixture A has 3 works."),
    "researcher-profile",
    "researcher:dblp:" + "b" * 64,
    "all-years",
    "run:00112233-4455-4677-8899-aabbccddeeff",
    "fixture-template-v1",
    "Fixture A has 3 works.",
    Vector(SummarySourceRef("fixture/researcher_metrics", "fixture-A", "publicationCount")),
    "generated-summary",
    identityFields = Map("sourceDataset" -> "synthetic-fixture"),
    chunkPolicyVersion = "fixture-chunk-policy-v1",
    chunkOrdinal = 0
  )
  val hash: String = "d23025bf3ac41e3d69947fe4aa5bd6318fe202cb7664cac26464143a85926552"
  val workItem: EmbeddingWorkItem = EmbeddingWorkItem(
    EmbeddingContracts.vectorKey(document, model),
    "researcher-profile-v1",
    document,
    "s3://fixture-text/graph/rag/fixture-A.json",
    hash,
    model
  )
  val metadata: EmbeddingVectorMetadata = EmbeddingVectorMetadata(
    document.documentType,
    document.entityId,
    document.windowId,
    document.runId,
    workItem.textS3Uri,
    hash,
    model,
    document.templateVersion,
    document.documentId,
    identityFields = document.identityFields,
    chunkPolicyVersion = document.chunkPolicyVersion,
    chunkOrdinal = document.chunkOrdinal
  )
  val context: SemanticContext = SemanticContext(
    Vector(
      SemanticContextItem(
        workItem.vectorKey,
        0.75,
        document.documentType,
        workItem.textS3Uri,
        "Fixture A",
        hash
      )
    )
  )
}

class EmbeddingContractSpec extends AnyFunSuite {
  import EmbeddingExamples.*
  private def wire[A: ReadWriter](name: String, value: A): Unit = {
    val source = scala.io.Source.fromURL(getClass.getResource(s"/wire/embedding-$name.json"))
    val text =
      try source.mkString
      finally source.close()
    assert(CoreJson.parse[A](text).contains(value))
    assert(ujson.read(CoreJson.pretty(value)) == ujson.read(text))
  }
  test("document, manifest item, compact metadata and context have frozen additive wire examples") {
    wire("document", document)
    wire("work-item", workItem)
    wire("metadata", metadata)
    wire("context", context)
    assert(EmbeddingValidation.document(document).isEmpty)
    assert(EmbeddingValidation.workItem(workItem).isEmpty)
    assert(EmbeddingValidation.metadata(metadata).isEmpty)
    assert(EmbeddingValidation.context(context).isEmpty)
  }
  test("text hash is over exact UTF-8 bytes, not whitespace-normalized text") {
    assert(EmbeddingContracts.textHash(document.text) == hash)
    assert(
      EmbeddingContracts.textHash(
        "abc"
      ) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert(EmbeddingContracts.textHash(document.text + "\n") != hash)
    assert(
      EmbeddingValidation
        .workItem(workItem.copy(textHash = "0" * 64))
        .contains("text-hash-mismatch")
    )
  }
  test(
    "model ID, model version and dimension all change vector identity without delimiter collisions"
  ) {
    assert(model.tag == "17:fixture.embedding2:v11:3")
    assert(EmbeddingModel("a:b", "c", 3).tag != EmbeddingModel("a", "b:c", 3).tag)
    Vector(model.copy(modelId = "another"), model.copy(version = "v2"), model.copy(dimension = 4))
      .foreach { next =>
        val item = workItem.copy(embeddingModel = next)
        assert(EmbeddingValidation.workItem(item).contains("vector-key-model-or-document-mismatch"))
        assert(EmbeddingContracts.vectorKey(document, next) != workItem.vectorKey)
      }
    assert(
      EmbeddingContracts.vectorKey(document.copy(chunkOrdinal = 1), model) != workItem.vectorKey
    )
  }
  test("stable vector slots exclude text, content ID and source run but include every slot field") {
    val changedText = "Fixture A has 4 works."
    val changed = document.copy(text = changedText, documentId = contentId(changedText))
    assert(changed.documentId != document.documentId)
    assert(EmbeddingContracts.vectorKey(changed, model) == workItem.vectorKey)
    assert(
      EmbeddingContracts.vectorKey(
        document.copy(runId = "run:11112233-4455-4677-8899-aabbccddeeff"),
        model
      ) == workItem.vectorKey
    )
    val moved = Vector(
      document.copy(documentType = "paper"),
      document.copy(entityId = "researcher:dblp:" + "c" * 64),
      document.copy(windowId = "2010-2019"),
      document.copy(templateVersion = "fixture-template-v2"),
      document.copy(chunkPolicyVersion = "fixture-chunk-policy-v2"),
      document.copy(documentId = contentId(document.text, 1), chunkOrdinal = 1)
    )
    moved.foreach(next => assert(EmbeddingContracts.vectorKey(next, model) != workItem.vectorKey))
  }
  test(
    "documents and vector metadata reject unspecified or invalid stable slot versions and ordinals"
  ) {
    Vector("", "bad policy", "bad\npolicy", "x" * 257).foreach { version =>
      assert(
        EmbeddingValidation
          .document(document.copy(chunkPolicyVersion = version))
          .contains("invalid-chunk-policy-version")
      )
      assert(
        EmbeddingValidation
          .metadata(metadata.copy(chunkPolicyVersion = version))
          .contains("invalid-chunk-policy-version")
      )
      assert(
        EmbeddingValidation
          .document(document.copy(templateVersion = version))
          .contains("invalid-template-version")
      )
      assert(
        EmbeddingValidation
          .metadata(metadata.copy(templateVersion = version))
          .contains("invalid-template-version")
      )
    }
    assert(
      EmbeddingValidation
        .document(document.copy(chunkOrdinal = -1))
        .contains("invalid-chunk-ordinal")
    )
    assert(
      EmbeddingValidation
        .metadata(metadata.copy(chunkOrdinal = -1))
        .contains("invalid-chunk-ordinal")
    )
    val noSlot = ujson.read(CoreJson.compact(document))
    noSlot.obj.remove("chunkPolicyVersion")
    noSlot.obj.remove("chunkOrdinal")
    val decoded = CoreJson.parse[EmbeddingDocument](noSlot.render()).toOption.get
    assert(EmbeddingValidation.document(decoded).contains("invalid-chunk-policy-version"))
    assert(EmbeddingValidation.document(decoded).contains("invalid-chunk-ordinal"))
    assert(metadata.compact("chunkPolicyVersion") == "fixture-chunk-policy-v1")
    assert(metadata.compact("chunkOrdinal") == "0")
  }
  test(
    "work manifest rejects wrong type/index, unsupported schema, malformed pointers and missing provenance"
  ) {
    assert(
      EmbeddingValidation
        .workItem(workItem.copy(indexName = "paper-abstract-v1"))
        .contains("document-index-mismatch")
    )
    assert(
      EmbeddingValidation
        .workItem(workItem.copy(schemaVersion = "future"))
        .contains("unsupported-embedding-schema")
    )
    Vector(
      "s3vectors://bucket/index/key",
      "s3://bucket",
      "s3://bucket/key?token=x",
      "https://example.test/text"
    ).foreach { uri =>
      assert(
        EmbeddingValidation.workItem(workItem.copy(textS3Uri = uri)).contains("invalid-text-s3-uri")
      )
    }
    assert(
      EmbeddingValidation
        .document(document.copy(sourceReferences = Vector.empty))
        .contains("missing-source-reference")
    )
    assert(
      EmbeddingValidation
        .document(document.copy(documentId = "not-a-chunk"))
        .contains("invalid-document-id")
    )
  }
  test("abstract and fallback choices are explicit and limited to paper documents") {
    val paper = document.copy(documentType = "paper", documentId = "chunk:" + "a" * 64)
    assert(EmbeddingValidation.document(paper.copy(textSelection = "permitted-abstract")).isEmpty)
    assert(
      EmbeddingValidation.document(paper.copy(textSelection = "paper-summary-fallback")).isEmpty
    )
    assert(
      EmbeddingValidation
        .document(document.copy(textSelection = "permitted-abstract"))
        .contains("invalid-text-selection-for-type")
    )
    assert(
      EmbeddingValidation
        .document(paper.copy(textSelection = "invented-abstract"))
        .contains("invalid-text-selection")
    )
  }
  test(
    "metadata keeps model/dimension and pointer but cannot carry full text or arbitrary filter fields"
  ) {
    val compact = metadata.compact
    assert(compact("embeddingModel") == model.tag)
    assert(compact("embeddingModelId") == "fixture.embedding")
    assert(compact("embeddingModelVersion") == "v1")
    assert(compact("dimension") == "3")
    assert(compact("sourceDataset") == "synthetic-fixture")
    assert(compact("textS3Uri") == workItem.textS3Uri)
    assert(!compact.values.exists(_ == document.text))
    val invalid = metadata.copy(identityFields = Map("text" -> document.text))
    assert(EmbeddingValidation.metadata(invalid).contains("invalid-identity-metadata"))
    assert(!invalid.compact.contains("text"))
    assert(
      EmbeddingValidation
        .metadata(metadata.copy(identityFields = Map("topicId" -> "x" * 257)))
        .contains("invalid-identity-metadata")
    )
  }
  test(
    "typed embedding outcomes preserve model and attempt information and reject bad dimensions"
  ) {
    val success: EmbeddingResult = EmbeddingSuccess(Vector(1f, 0f, 0f), model, 2)
    val failure: EmbeddingResult = EmbeddingFailure("throttled", true, model, 3)
    assert(CoreJson.parse[EmbeddingResult](CoreJson.compact(success)).contains(success))
    assert(CoreJson.parse[EmbeddingResult](CoreJson.compact(failure)).contains(failure))
    assert(EmbeddingValidation.result(success).isEmpty)
    assert(EmbeddingValidation.result(failure).isEmpty)
    assert(EmbeddingValidation.result(EmbeddingFailure("input-too-large", false, model, 0)).isEmpty)
    assert(
      EmbeddingValidation
        .result(EmbeddingSuccess(Vector(1f), model, 1))
        .contains("embedding-dimension-or-value-mismatch")
    )
    assert(
      EmbeddingValidation.result(EmbeddingSuccess(Vector(Float.NaN, 0f, 0f), model, 1)).nonEmpty
    )
    assert(
      EmbeddingValidation
        .result(EmbeddingFailure("provider payload with secrets", false, model, 1))
        .contains("invalid-embedding-failure-code")
    )
  }
  test(
    "semantic context serializes descriptive label and cannot authorize exact metrics or graph claims"
  ) {
    val json = ujson.read(CoreJson.compact(context))
    assert(json("usage").str == EmbeddingContracts.descriptiveOnly)
    assert(!json("exactMetricsAllowed").bool && !json("graphClaimsAllowed").bool)
    assert(
      EmbeddingValidation
        .context(context.copy(exactMetricsAllowed = true))
        .contains("semantic-context-is-not-evidence")
    )
    assert(
      EmbeddingValidation
        .context(context.copy(graphClaimsAllowed = true))
        .contains("semantic-context-is-not-evidence")
    )
    assert(
      EmbeddingValidation
        .context(context.copy(usage = "authoritative"))
        .contains("semantic-context-is-not-evidence")
    )
    assert(
      EmbeddingValidation
        .context(context, maxExcerptChars = 4)
        .contains("invalid-semantic-context-item")
    )
    assert(
      EmbeddingValidation
        .context(context.copy(items = context.items.map(_.copy(score = Double.NaN))))
        .nonEmpty
    )
  }

  test("semantic excerpt limits count supplementary Unicode characters as single codepoints") {
    val atBoundary = context.copy(items = context.items.map(_.copy(excerpt = "A😀B")))
    val overBoundary = context.copy(items = context.items.map(_.copy(excerpt = "A😀BC")))
    assert(EmbeddingValidation.context(atBoundary, maxExcerptChars = 3).isEmpty)
    assert(
      EmbeddingValidation
        .context(overBoundary, maxExcerptChars = 3)
        .contains("invalid-semantic-context-item")
    )
  }
}
