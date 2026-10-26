package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8

class EmbeddingRetrievalSpec extends AnyFunSuite {
  test(
    "six committed known queries retrieve their fixed neighbor and every hit resolves to hashed ordinary text"
  ) {
    val source = scala.io.Source.fromResource("embedding-smoke.json")
    val fixture =
      try ujson.read(source.mkString)
      finally source.close()
    val model = EmbeddingModel("local-hashed-bow", "fixture-v1", 256)
    val embedder = new DeterministicHashedEmbeddingClient(model)
    val renderer =
      new DocumentRenderer(RenderingConfig("fixture-template-v1", ChunkPolicy(1000, 0)))
    val documents = fixture("documents").arr.toVector.flatMap { row =>
      val entity = row("entityId").str
      renderer
        .render(
          RenderInput(
            row("documentType").str,
            entity,
            "synthetic-window",
            "synthetic-source-run",
            Vector(
              SourceField(
                "description",
                row("text").str,
                SummarySourceRef("synthetic-smoke-fixture", entity, "text")
              )
            )
          )
        )
        .fold(fail(_), identity)
    }
    val config = EmbeddingIngestConfig("synthetic-text", "rag", model.dimension)
    val objects = new InMemoryObjectStore
    val vectors = new InMemoryVectorStore
    EmbeddingContracts.indexes.values.toSet.foreach(index =>
      vectors.ensureIndex(index, model.dimension, "cosine")
    )
    val items = documents.map(doc => EmbeddingManifests.item(doc, model, config))
    val runner = new EmbeddingManifestRunner(
      config,
      objects,
      vectors,
      new InMemoryArtifactRegistry,
      new InMemoryRunLedger,
      embedder,
      logEvent = _ => ()
    )
    val report =
      StorageResult.value(runner.run(EmbeddingManifest(items), "synthetic-smoke-ingest")).get
    assert(report.written == 12 && report.rejected == 0 && report.vectorKeyTextConflict == 0)
    val queries = fixture("queries").arr.toVector
    assert(
      queries.map(_("caseId").str).toSet == Set(
        "researcher",
        "community",
        "path",
        "paper",
        "topic",
        "institution"
      )
    )
    queries.foreach { query =>
      val embedding = embedder.embed(Seq(query("query").str)).head.asInstanceOf[EmbeddingSuccess]
      val index = EmbeddingContracts.indexes(query("documentType").str)
      val hits = StorageResult
        .value(vectors.query(index, embedding.values, query("topK").num.toInt, Map.empty))
        .get
      assert(
        hits.exists(_.metadata("entityId") == query("expectedEntityId").str),
        query("caseId").str
      )
      assert(hits.nonEmpty)
      hits.foreach { hit =>
        val uri = hit.metadata("textS3Uri")
        assert(uri.startsWith("s3://synthetic-text/"))
        val stored = StorageResult.value(objects.get(uri.stripPrefix("s3://synthetic-text/"))).get
        val envelope = ujson.read(new String(stored.bytes.toArray, UTF_8))
        val text = envelope("document")("text").str
        assert(envelope("textHash").str == StableIds.sha256Hex(text))
        assert(hit.metadata("textHash") == StableIds.sha256Hex(text))
        val item = SemanticContexts.fromStoredObject(hit, stored).fold(fail(_), identity)
        assert(item.vectorKey == hit.key && item.textS3Uri == uri && item.excerpt.nonEmpty)
        val context = SemanticContext(Vector(item))
        assert(EmbeddingValidation.context(context).isEmpty)
        assert(
          context.usage == EmbeddingContracts.descriptiveOnly && !context.exactMetricsAllowed && !context.graphClaimsAllowed
        )
        assert(EmbeddingValidation.context(context.copy(exactMetricsAllowed = true)).nonEmpty)
        assert(EmbeddingValidation.context(context.copy(graphClaimsAllowed = true)).nonEmpty)
      }
    }
  }
  test("renderer supplies whole text binding and actual group cardinality for every chunk") {
    val text = "Paper summary\npapers: 7\ntitle: Synthetic graph"
    val refs = Vector(
      SummarySourceRef("synthetic-counts", "fixture", "publicationCount"),
      SummarySourceRef("synthetic-works", "fixture", "title")
    )
    val documents = new DocumentRenderer(RenderingConfig("fixture-v1", ChunkPolicy(16, 2)))
      .render(
        RenderInput(
          "paper",
          "synthetic-work",
          "synthetic-window",
          "synthetic-run",
          Vector(
            SourceField("papers", "7", refs(0)),
            SourceField("title", "Synthetic graph", refs(1))
          )
        )
      )
      .fold(fail(_), identity)
    assert(documents.size > 1)
    assert(
      documents.forall(doc =>
        doc.chunkCount == documents.size && doc.wholeTextHash == StableIds.sha256Hex(text)
      )
    )
    assert(documents.map(_.chunkOrdinal) == documents.indices.toVector)
    val model = EmbeddingModel("local-hashed-bow", "fixture-v1", 256)
    assert(documents.map(d => EmbeddingContracts.groupKey(d, model)).distinct.size == 1)
    assert(
      documents.map(d => EmbeddingContracts.vectorKey(d, model)).distinct.size == documents.size
    )
    assert(documents.forall(doc => EmbeddingValidation.document(doc).isEmpty))
  }
  test("local CLI rejects missing or live-mode arguments before source or state access") {
    assert(EmbeddingIngestMain.run(Seq.empty) == Left("invalid-local-arguments"))
    assert(EmbeddingIngestMain.run(Seq("--execute-aws", "true")) == Left("invalid-local-arguments"))
  }
}
