package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import org.scalatest.funsuite.AnyFunSuite

/** Hand-derived expectations use synthetic source fields, never claimed real-data facts. */
class IndependentEmbeddingRenderingSpec extends AnyFunSuite {
  private val papers = SummarySourceRef("synthetic-counts", "row-1", "paperCount")
  private val title = SummarySourceRef("synthetic-titles", "row-1", "title")
  private val fields =
    Vector(SourceField("title", "Synthetic title", title), SourceField("papers", "7", papers))
  private val renderer = new DocumentRenderer(RenderingConfig("template-v1", ChunkPolicy(10000, 0)))
  private def input(kind: String) =
    RenderInput(kind, "synthetic-entity", "2020-2026", "synthetic-run", fields)
  private def documents(result: Either[String, Vector[EmbeddingDocument]]) =
    result.fold(fail(_), identity)

  test(
    "five document templates render exact supplied fields deterministically and retain provenance"
  ) {
    val headers = Vector(
      "researcher-profile" -> "Researcher profile",
      "community" -> "Collaboration community",
      "collaboration-path" -> "Collaboration path",
      "paper" -> "Paper summary",
      "topic-institution-summary" -> "Topic and institution summary"
    )
    headers.foreach { (kind, header) =>
      val rendered = documents(renderer.render(input(kind)))
      assert(rendered.size == 1)
      val document = rendered.head
      assert(document.text == header + "\npapers: 7\ntitle: Synthetic title")
      assert(document.templateVersion == "template-v1")
      assert(document.sourceReferences.toSet == Set(papers, title))
      assert(document.runId == "synthetic-run" && document.windowId == "2020-2026")
      assert(documents(renderer.render(input(kind).copy(fields = fields.reverse))) == rendered)
      assert(EmbeddingValidation.document(document).isEmpty)
    }
  }

  test(
    "paper fallback and permitted abstract record different explicit selections with permission provenance"
  ) {
    val fallback = documents(renderer.render(input("paper"))).head
    assert(fallback.textSelection == "paper-summary-fallback")
    assert(fallback.text == "Paper summary\npapers: 7\ntitle: Synthetic title")
    val abstractRef = SummarySourceRef("synthetic-permitted-text", "row-1", "text")
    val permissionRef = SummarySourceRef("synthetic-license", "row-1", "permission")
    val permitted = PermittedAbstract("Synthetic abstract text.", abstractRef, permissionRef)
    val abstractDocument = documents(renderer.render(input("paper"), Some(permitted))).head
    assert(abstractDocument.textSelection == "permitted-abstract")
    assert(
      abstractDocument.text == "Paper abstract\npapers: 7\ntitle: Synthetic title\nabstract: Synthetic abstract text."
    )
    assert(
      abstractDocument.sourceReferences.toSet == Set(papers, title, abstractRef, permissionRef)
    )
    assert(abstractDocument.documentId != fallback.documentId)
  }

  test("chunking follows a fixed boundary/overlap expectation and rejects invalid limits") {
    assert(ChunkPolicy(6, 2).chunks("abcdefghij") == Right(Vector("abcdef", "efghij")))
    assert(ChunkPolicy(6, 2).chunks("abcdef") == Right(Vector("abcdef")))
    assert(ChunkPolicy(6, 2).chunks("").isLeft)
    assert(ChunkPolicy(6, 2, maxChunks = 1).chunks("abcdefghij").isLeft)
    intercept[IllegalArgumentException](ChunkPolicy(6, 6))
  }

  test(
    "deterministic fake returns stable finite model-versioned results and typed empty-input failure"
  ) {
    val model = EmbeddingModel("synthetic-hashed", "v1", 32)
    val client = new DeterministicHashedEmbeddingClient(model)
    val first = client.embed(Seq("synthetic graph context", ""))
    val repeated = client.embed(Seq("synthetic graph context", ""))
    assert(first == repeated && first.size == 2)
    val vector = first.head.asInstanceOf[EmbeddingSuccess]
    assert(vector.model == model && vector.attempts == 1)
    assert(vector.values.size == 32 && vector.values.forall(_.isFinite))
    assert(vector.values.exists(_ != 0f))
    assert(first(1).isInstanceOf[EmbeddingFailure])
    assert(first.forall(_.model == model))
  }
}
