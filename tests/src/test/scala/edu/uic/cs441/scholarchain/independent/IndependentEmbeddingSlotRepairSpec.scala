package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import scala.collection.mutable
import java.nio.charset.StandardCharsets.UTF_8

/** F1/N1 repair acceptance: synthetic data passed through actual renderer and ingestion ports. */
class IndependentEmbeddingSlotRepairSpec extends AnyFunSuite {
  import StorageResult.*
  private val model = EmbeddingModel("synthetic-repair-model", "v1", 2)
  private val config = EmbeddingIngestConfig("synthetic-text", "graph", 2)
  private val renderer = new DocumentRenderer(RenderingConfig("template-v1", ChunkPolicy(10000, 0)))
  private val reference = SummarySourceRef("synthetic-counts", "row-1", "publicationCount")
  private def input(count: String, run: String = "source-run") = RenderInput(
    "researcher-profile",
    "synthetic-person",
    "2020-2026",
    run,
    Vector(SourceField("papers", count, reference)),
    Map("researcherId" -> "synthetic-person")
  )
  private def documents(result: Either[String, Vector[EmbeddingDocument]]) =
    result.fold(fail(_), identity)
  private def value[A](result: StorageResult[A]): A =
    StorageResult.value(result).getOrElse(fail(result.toString))
  private final class RecordingObjects extends ObjectStore {
    val delegate = new InMemoryObjectStore()
    val putKeys = mutable.Buffer.empty[String]
    def put(
        key: String,
        bytes: Vector[Byte],
        contentType: String,
        metadata: Map[String, String]
    ): StorageResult[ObjectHead] = {
      putKeys += key
      delegate.put(key, bytes, contentType, metadata)
    }
    def get(key: String): StorageResult[StoredObject] = delegate.get(key)
    def head(key: String): StorageResult[ObjectHead] = delegate.head(key)
  }
  private final class RecordingVectors extends VectorStore {
    val delegate = new InMemoryVectorStore()
    val batches = mutable.Buffer.empty[Vector[VectorDocument]]
    def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String] =
      delegate.ensureIndex(name, dimension, metric)
    def putBatch(
        index: String,
        documents: Vector[VectorDocument]
    ): StorageResult[VectorBatchResult] = {
      batches += documents
      delegate.putBatch(index, documents)
    }
    def query(
        index: String,
        vector: Vector[Float],
        topK: Int,
        filter: Map[String, String]
    ): StorageResult[Vector[VectorHit]] = delegate.query(index, vector, topK, filter)
    def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
      delegate.get(index, keys)
  }
  private final class Fixture {
    val objects = new RecordingObjects()
    val vectors = new RecordingVectors()
    val registry = new InMemoryArtifactRegistry()
    val ledger = new InMemoryRunLedger()
    val embedded = mutable.Buffer.empty[(EmbeddingModel, String)]
    assert(StorageResult.successful(vectors.ensureIndex("researcher-profile-v1", 2, "cosine")))
    def run(
        documents: Vector[EmbeddingDocument],
        execution: String,
        selectedModel: EmbeddingModel = model
    ): EmbeddingIngestReport = {
      val client = new EmbeddingClient {
        val model = selectedModel
        def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
          embedded += model -> text
          EmbeddingSuccess(Vector(1f, 0f), model, 1)
        }
      }
      val runner = new EmbeddingManifestRunner(config, objects, vectors, registry, ledger, client)
      value(
        runner.run(
          EmbeddingManifest(documents.map(EmbeddingManifests.item(_, selectedModel, config))),
          execution
        )
      )
    }
  }

  test(
    "real rendered content changes keep the stable slot and conflict before any new embedding or data writes"
  ) {
    val f = new Fixture()
    val original = documents(renderer.render(input("7")))
    val changed = documents(renderer.render(input("8", "new-source-run")))
    assert(original.head.text == "Researcher profile\npapers: 7")
    assert(changed.head.text == "Researcher profile\npapers: 8")
    assert(original.head.documentId != changed.head.documentId)
    assert(StableIds.parseChunkOrProfileId(original.head.documentId).isRight)
    assert(StableIds.parseChunkOrProfileId(changed.head.documentId).isRight)
    val firstItem = EmbeddingManifests.item(original.head, model, config)
    val changedItem = EmbeddingManifests.item(changed.head, model, config)
    assert(firstItem.vectorKey == changedItem.vectorKey)
    assert(
      firstItem.textHash != changedItem.textHash && firstItem.textS3Uri != changedItem.textS3Uri
    )
    assert(f.run(original, "first-execution").written == 1)
    val oldObjectPuts = f.objects.putKeys.toVector
    val oldVectorPuts = f.vectors.batches.size
    val oldEmbeddings = f.embedded.toVector
    val conflict = f.run(changed, "changed-execution")
    assert(
      (
        conflict.written,
        conflict.unchanged,
        conflict.vectorKeyTextConflict,
        conflict.rejected,
        conflict.embeddingCalls
      ) == (0, 0, 1, 1, 0)
    )
    assert(
      conflict.rejections == Vector(VectorReject(firstItem.vectorKey, "vectorKeyTextConflict"))
    )
    assert(f.embedded.toVector == oldEmbeddings)
    assert(f.vectors.batches.size == oldVectorPuts)
    val newObjectPuts = f.objects.putKeys.drop(oldObjectPuts.size).toVector
    assert(newObjectPuts.size == 1 && newObjectPuts.head.startsWith("graph/rejected/versions/"))
    assert(!newObjectPuts.exists(_.contains("/prepared/")))
    val stored = value(f.vectors.get(firstItem.indexName, Vector(firstItem.vectorKey)))
    assert(stored.size == 1 && stored.head.textHash == firstItem.textHash)
    val replayObjects = f.objects.putKeys.size
    val replay = f.run(original, "unchanged-execution")
    assert(
      (replay.written, replay.unchanged, replay.rejected, replay.embeddingCalls) == (0, 1, 0, 0)
    )
    assert(f.embedded.toVector == oldEmbeddings && f.vectors.batches.size == oldVectorPuts)
    assert(f.objects.putKeys.size == replayObjects)
  }

  test(
    "a new model occupies a distinct slot while actual separate chunks retain separate ordinal keys"
  ) {
    val f = new Fixture()
    val document = documents(renderer.render(input("7")))
    assert(f.run(document, "model-one").written == 1)
    val nextModel = model.copy(version = "v2")
    val originalKey = EmbeddingManifests.item(document.head, model, config).vectorKey
    val newKey = EmbeddingManifests.item(document.head, nextModel, config).vectorKey
    assert(newKey != originalKey)
    assert(f.run(document, "model-two", nextModel).written == 1)
    assert(f.embedded.map(_._1).toVector == Vector(model, nextModel))
    assert(value(f.vectors.get("researcher-profile-v1", Vector(originalKey, newKey))).size == 2)
    val chunks = documents(
      new DocumentRenderer(RenderingConfig("template-v1", ChunkPolicy(6, 0)))
        .fromSummary(summary("abcdefghijkl"))
    )
    assert(chunks.map(_.text) == Vector("abcdef", "ghijkl"))
    assert(chunks.map(_.chunkOrdinal) == Vector(0, 1))
    val chunkItems = chunks.map(EmbeddingManifests.item(_, model, config))
    assert(chunkItems.map(_.vectorKey).distinct.size == 2)
    val separate = new Fixture()
    val first = separate.run(chunks, "chunks-one")
    assert((first.written, first.rejected, first.embeddingCalls) == (2, 0, 2))
    val replay = separate.run(chunks, "chunks-two")
    assert((replay.written, replay.unchanged, replay.embeddingCalls) == (0, 2, 0))
  }

  private val lineage = SparkLineage(
    "synthetic-hadoop",
    "synthetic-snapshot",
    "synthetic-er",
    "er-v1",
    "a" * 64,
    Vector.empty,
    Vector.empty
  )
  private def summary(text: String, kind: String = "researcher-profile") = SemanticSummary(
    SparkRecordContext(
      "scholarchain.spark-analytics.v1",
      "summary-source-run",
      Some("2020-2026"),
      lineage
    ),
    "synthetic-summary",
    kind,
    "synthetic-summary-entity",
    "summary-policy-v1",
    text,
    Vector(reference),
    Vector.empty
  )

  test(
    "summary adapter preserves exact source bytes and caller filters through actual ingestion metadata"
  ) {
    val text = "  Non-converged community\r\nApproximate P90: 7.5\n"
    val source = summary(text)
    val filters = Map(
      "researcherId" -> "synthetic-person",
      "communityId" -> "synthetic-community",
      "topicId" -> "synthetic-topic",
      "institutionId" -> "synthetic-institution",
      "sourceDataset" -> "synthetic-source"
    )
    val adapted = documents(renderer.fromSummary(source, identityFields = filters))
    assert(
      adapted.size == 1 && adapted.head.text.getBytes(UTF_8).toVector == text
        .getBytes(UTF_8)
        .toVector
    )
    assert(adapted.head.sourceReferences == source.sourceReferences)
    assert(adapted.head.identityFields == filters && adapted.head.runId == source.context.runId)
    val f = new Fixture()
    assert(f.run(adapted, "summary-metadata").written == 1)
    val item = EmbeddingManifests.item(adapted.head, model, config)
    val stored = value(f.vectors.get(item.indexName, Vector(item.vectorKey))).head
    filters.foreach { (name, expected) => assert(stored.metadata(name) == expected) }
    assert(stored.metadata("chunkPolicyVersion") == adapted.head.chunkPolicyVersion)
    assert(stored.metadata("chunkOrdinal") == "0")
    val body = ujson.read(
      new String(
        value(f.objects.get(item.textS3Uri.stripPrefix("s3://synthetic-text/"))).bytes.toArray,
        UTF_8
      )
    )
    assert(body("document")("text").str == text)
    assert(
      renderer.fromSummary(source, identityFields = Map("fullText" -> "not-an-identity")).isLeft
    )
    assert(renderer.fromSummary(source, identityFields = Map("researcherId" -> ("x" * 257))).isLeft)
  }

  test(
    "paper summary adapter uses exact source text for absent or blank abstracts and exact permitted composition"
  ) {
    val text = "Original paper summary\r\nQualified source facts.  "
    val source = summary(text, "paper")
    val abstractRef = SummarySourceRef("synthetic-abstracts", "row-1", "text")
    val permissionRef = SummarySourceRef("synthetic-permissions", "row-1", "permission")
    val absent = documents(renderer.fromSummary(source)).head
    val blank = documents(
      renderer.fromSummary(source, Some(PermittedAbstract(" \t\n", abstractRef, permissionRef)))
    ).head
    assert(absent.text == text && blank.text == text)
    assert(
      absent.textSelection == "paper-summary-fallback" && blank.textSelection == "paper-summary-fallback"
    )
    assert(
      absent.sourceReferences == source.sourceReferences && blank.sourceReferences == source.sourceReferences
    )
    assert(absent.documentId == blank.documentId)
    val abstractText = "Permitted abstract\r\nExact bytes. "
    val permitted = documents(
      renderer.fromSummary(
        source,
        Some(PermittedAbstract(abstractText, abstractRef, permissionRef))
      )
    ).head
    assert(permitted.text == text + "\n" + abstractText)
    assert(permitted.textSelection == "permitted-abstract")
    assert(permitted.sourceReferences.toSet == Set(reference, abstractRef, permissionRef))
    assert(!permitted.text.startsWith("Paper abstract\n"))
  }
}
