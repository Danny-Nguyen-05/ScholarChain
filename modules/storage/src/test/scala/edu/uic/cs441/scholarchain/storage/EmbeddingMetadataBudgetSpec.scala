package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite

/** Phase 8 finding R3: the S3 Vectors metadata budget is enforced before any embedding call. */
class EmbeddingMetadataBudgetSpec extends AnyFunSuite {
  private val model = EmbeddingModel("fixture-embedding", "v1", 2)
  private class CountingEmbed extends EmbeddingClient {
    val model = EmbeddingMetadataBudgetSpec.this.model
    var calls = 0
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      calls += texts.size; texts.map(_ => EmbeddingSuccess(Vector(1f, 0f), model, 1))
    }
  }
  private def doc(dataset: String): EmbeddingDocument = {
    val id = StableIds.chunkOrProfileId("e", "v1", "paper", Some(0), "text").toOption.get
    EmbeddingDocument(
      id,
      "paper",
      "e",
      "w",
      "r",
      "t-v1",
      "text",
      Vector(SummarySourceRef("works", "w1", "title")),
      "paper-summary-fallback",
      identityFields = Map("sourceDataset" -> dataset),
      chunkPolicyVersion = "p-v1",
      chunkOrdinal = 0
    )
  }
  private def runWith(config: EmbeddingIngestConfig, d: EmbeddingDocument) = {
    val objects = new InMemoryObjectStore
    val vectors = new InMemoryVectorStore
    vectors.ensureIndex("paper-abstract-v1", 2, "cosine")
    val embed = new CountingEmbed
    val runner = new EmbeddingManifestRunner(
      config,
      objects,
      vectors,
      new InMemoryArtifactRegistry,
      new InMemoryRunLedger,
      embed
    )
    val item = EmbeddingManifests.item(d, model, config)
    val report = StorageResult.value(runner.run(EmbeddingManifest(Vector(item)), "budget-run")).get
    (report, embed, objects, item)
  }
  private def filterable(config: EmbeddingIngestConfig, d: EmbeddingDocument): Int = {
    val item = EmbeddingManifests.item(d, model, config)
    val m = EmbeddingVectorMetadata(
      d.documentType,
      d.entityId,
      d.windowId,
      d.runId,
      item.textS3Uri,
      item.textHash,
      item.embeddingModel,
      d.templateVersion,
      d.documentId,
      identityFields = d.identityFields,
      chunkPolicyVersion = d.chunkPolicyVersion,
      chunkOrdinal = d.chunkOrdinal
    ).compact
    VectorMetadataBudget.filterableBytes(m, config.nonFilterableKeys)
  }

  // Hand-derived: {"a":"bb"} is 2 braces + 3 + 1 + 4 = 10 bytes.
  test("budget arithmetic is exact: limit passes, limit-1 fails, non-filterable keys excluded") {
    val m = Map("a" -> "bb")
    assert(VectorMetadataBudget.totalBytes(m) == 10)
    assert(!VectorMetadataBudget.exceeds(m, 50, 40960, 10, Set.empty))
    assert(VectorMetadataBudget.exceeds(m, 50, 40960, 9, Set.empty))
    val withUri = m + ("u" -> ("x" * 100))
    assert(VectorMetadataBudget.filterableBytes(withUri, Set("u")) == 10)
    assert(!VectorMetadataBudget.exceeds(withUri, 50, 40960, 10, Set("u")))
    assert(VectorMetadataBudget.exceeds(withUri, 50, 40960, 10, Set.empty))
    assert(VectorMetadataBudget.exceeds(m + ("b" -> "c"), 1, 40960, 2048, Set.empty))
    assert(VectorMetadataBudget.exceeds(withUri, 50, 100, 2048, Set("u")))
  }
  test("ingest config refuses limits above the S3 Vectors service caps") {
    intercept[IllegalArgumentException](
      EmbeddingIngestConfig("b", "p", 2, maxFilterableBytes = 2049)
    )
    intercept[IllegalArgumentException](EmbeddingIngestConfig("b", "p", 2, maxMetadataKeys = 51))
    intercept[IllegalArgumentException](
      EmbeddingIngestConfig("b", "p", 2, maxMetadataBytes = 40 * 1024 + 1)
    )
  }
  test("oversized filterable metadata is refused before the embedder is invoked") {
    // The fixed keys alone take roughly 650 bytes, so a 500-byte filterable budget refuses any
    // document; the core contract already caps each identity value, so the budget is the guard.
    val config = EmbeddingIngestConfig("fixture-text", "rag", 2, maxFilterableBytes = 500)
    val (report, embed, objects, item) = runWith(config, doc("d" * 20))
    assert(filterable(config, doc("d" * 20)) > 500)
    assert(embed.calls == 0 && report.embeddingCalls == 0)
    assert(report.written == 0 && report.rejected == 1)
    assert(
      report.rejections.map(r => r.key -> r.reason) == Vector(item.vectorKey -> "metadata-limit")
    )
    assert(!objects.writeOrder.exists(_.contains("/prepared/")))
  }
  test(
    "filterable boundary: exactly the limit is embedded, one byte more is refused with 0 calls"
  ) {
    val base = EmbeddingIngestConfig("fixture-text", "rag", 2)
    val atLimit = filterable(base, doc("d" * 20))
    val config = base.copy(maxFilterableBytes = atLimit)
    val (ok, okEmbed, _, _) = runWith(config, doc("d" * 20))
    assert(ok.written == 1 && ok.rejected == 0 && okEmbed.calls == 1)
    val (bad, badEmbed, _, _) = runWith(config, doc("d" * 21))
    assert(filterable(config, doc("d" * 21)) == atLimit + 1)
    assert(bad.written == 0 && bad.rejected == 1 && badEmbed.calls == 0)
    assert(bad.rejections.map(_.reason) == Vector("metadata-limit"))
  }
  test("non-filterable keys do not count toward the filterable budget") {
    val noUri = EmbeddingIngestConfig("fixture-text", "p" * 200, 2)
    val limit = filterable(noUri, doc("d" * 20))
    val config = noUri.copy(maxFilterableBytes = limit)
    // textS3Uri (>200 bytes here) is non-filterable, so the document sits exactly at the limit.
    val (ok, embed, _, _) = runWith(config, doc("d" * 20))
    assert(ok.written == 1 && embed.calls == 1)
    // The same document is refused once textS3Uri is treated as filterable.
    val strict = config.copy(nonFilterableKeys = Set.empty)
    val (bad, badEmbed, _, _) = runWith(strict, doc("d" * 20))
    assert(bad.rejected == 1 && badEmbed.calls == 0)
  }
}
