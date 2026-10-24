package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files

/** Expected neighbors are literal independent expectations for a committed synthetic corpus. */
class IndependentEmbedding8BSmokeSpec extends AnyFunSuite {
  private val expected = Map(
    "researcher" -> "synthetic-researcher-graph",
    "community" -> "synthetic-community-database",
    "path" -> "synthetic-path-algebra",
    "paper" -> "synthetic-paper-genome",
    "topic" -> "synthetic-topic-optics",
    "institution" -> "synthetic-institution-ocean"
  )
  private def value[A](result: StorageResult[A]): A =
    StorageResult.value(result).getOrElse(fail(result.toString))
  private val fixture = ujson.read(
    Files.readString(
      IndependentTestSupport.repoRoot.resolve(
        "modules/rag/src/test/resources/embedding-smoke.json"
      ),
      UTF_8
    )
  )
  private val model = EmbeddingModel("synthetic-independent-lexical", "v1", 256)
  private val embedder = new DeterministicHashedEmbeddingClient(model)
  private val ingest = EmbeddingIngestConfig("synthetic-smoke-text", "graph", 256)
  private val renderer = new DocumentRenderer(RenderingConfig("smoke-v1", ChunkPolicy(1000, 0)))
  private val objects = new InMemoryObjectStore()
  private val vectors = new InMemoryVectorStore()
  EmbeddingContracts.indexes.values.toVector.distinct.foreach(index =>
    assert(StorageResult.successful(vectors.ensureIndex(index, 256, "cosine")))
  )
  private val documents = fixture("documents").arr.toVector.flatMap { row =>
    renderer
      .render(
        RenderInput(
          row("documentType").str,
          row("entityId").str,
          "synthetic-window",
          "synthetic-smoke-run",
          Vector(
            SourceField(
              "description",
              row("text").str,
              SummarySourceRef("synthetic-smoke", row("entityId").str, "text")
            )
          )
        )
      )
      .fold(fail(_), identity)
  }
  private val report = value(
    new EmbeddingManifestRunner(
      ingest,
      objects,
      vectors,
      new InMemoryArtifactRegistry(),
      new InMemoryRunLedger(),
      embedder
    )
      .run(
        EmbeddingManifest(documents.map(EmbeddingManifests.item(_, model, ingest))),
        "independent-smoke"
      )
  )
  private def query(text: String): Vector[Float] =
    embedder.embed(Seq(text)).head.asInstanceOf[EmbeddingSuccess].values

  test(
    "six committed known queries return literal expected neighbors with competing same-type documents"
  ) {
    assert(report.written == 12 && report.rejected == 0)
    assert(
      fixture("queries").arr
        .map(q => q("caseId").str -> q("expectedEntityId").str)
        .toMap == expected
    )
    fixture("queries").arr.foreach { q =>
      val index = EmbeddingContracts.indexes(q("documentType").str)
      val hits = value(vectors.query(index, query(q("query").str), 1, Map.empty))
      assert(hits.size == 1 && hits.head.metadata("entityId") == expected(q("caseId").str))
      val stored = value(
        objects.get(hits.head.metadata("textS3Uri").stripPrefix("s3://synthetic-smoke-text/"))
      )
      assert(SemanticContexts.fromStoredObject(hits.head, stored).isRight)
    }
  }

  test(
    "every corpus vector follows its pointer to exact text and verified hash with descriptive-only authority"
  ) {
    val allHits = EmbeddingContracts.indexes.values.toVector.distinct.flatMap(index =>
      value(vectors.query(index, query("synthetic smoke"), 100, Map.empty))
    )
    assert(allHits.size == 12 && allHits.map(_.key).distinct.size == 12)
    val items = allHits.map { hit =>
      val pointer = hit.metadata("textS3Uri")
      assert(pointer.startsWith("s3://synthetic-smoke-text/graph/"))
      val stored = value(objects.get(pointer.stripPrefix("s3://synthetic-smoke-text/")))
      val body = ujson.read(new String(stored.bytes.toArray, UTF_8))
      val document = upickle.default.read[EmbeddingDocument](body("document"))
      assert(hit.metadata("textHash") == StableIds.sha256Hex(document.text))
      assert(body("textHash").str == hit.metadata("textHash"))
      assert(stored.head.sha256 == StorageKeys.sha256(stored.bytes))
      val item = SemanticContexts.fromStoredObject(hit, stored).fold(fail(_), identity)
      assert(
        item.vectorKey == hit.key && item.textS3Uri == pointer && item.textHash == hit.metadata(
          "textHash"
        )
      )
      assert(
        SemanticContexts
          .fromStoredObject(hit.copy(metadata = hit.metadata.updated("textHash", "0" * 64)), stored)
          .isLeft
      )
      item
    }
    val context = SemanticContext(items)
    assert(!context.exactMetricsAllowed && !context.graphClaimsAllowed)
    assert(context.usage == EmbeddingContracts.descriptiveOnly)
    assert(EmbeddingValidation.context(context).isEmpty)
    assert(EmbeddingValidation.context(context.copy(exactMetricsAllowed = true)).nonEmpty)
    assert(EmbeddingValidation.context(context.copy(graphClaimsAllowed = true)).nonEmpty)
  }
}
