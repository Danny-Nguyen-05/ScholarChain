package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import StorageResult.*

class EmbeddingGroupStateSpec extends AnyFunSuite {
  private val model = EmbeddingModel("fixture-local", "v1", 2)
  private val config = EmbeddingIngestConfig("fixture-bucket", "graph", 2)
  private def group(parts: Vector[String]): Vector[EmbeddingWorkItem] = {
    val whole = StableIds.sha256Hex(parts.mkString)
    parts.zipWithIndex.map { (text, ordinal) =>
      val id = StableIds
        .chunkOrProfileId("fixture-entity", "fixture-template", "paper", Some(ordinal), text)
        .toOption
        .get
      val doc = EmbeddingDocument(
        id,
        "paper",
        "fixture-entity",
        "all-years",
        "fixture-source-run",
        "fixture-template",
        text,
        Vector(SummarySourceRef("fixture-table", "fixture-row", "text")),
        "paper-summary-fallback",
        chunkPolicyVersion = "fixture-policy",
        chunkOrdinal = ordinal,
        chunkCount = parts.size,
        wholeTextHash = whole
      )
      EmbeddingManifests.item(doc, model, config)
    }
  }
  private class Embed extends EmbeddingClient {
    val model = EmbeddingGroupStateSpec.this.model
    var calls = 0
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      calls += texts.size; texts.map(_ => EmbeddingSuccess(Vector(1f, 0f), model, 1))
    }
  }
  private def fixture() = {
    val objects = new InMemoryObjectStore
    val vectors = new InMemoryVectorStore; vectors.ensureIndex("paper-abstract-v1", 2, "cosine")
    val registry = new InMemoryArtifactRegistry
    val ledger = new InMemoryRunLedger
    val embed = new Embed
    val runner = new EmbeddingManifestRunner(config, objects, vectors, registry, ledger, embed)
    (objects, vectors, registry, ledger, embed, runner)
  }
  test("shrinking a complete bound group rejects even its unchanged prefix before payload writes") {
    val (objects, vectors, _, _, embed, runner) = fixture()
    val original = group(Vector("prefix", "suffix"))
    assert(
      StorageResult.value(runner.run(EmbeddingManifest(original), "original")).get.written == 2
    )
    val writes = objects.writeOrder.toVector
    val report =
      StorageResult.value(runner.run(EmbeddingManifest(group(Vector("prefix"))), "shrink")).get
    assert(
      report.written == 0 && report.unchanged == 0 && report.vectorKeyTextConflict == 1 && report.embeddingCalls == 0
    )
    assert(embed.calls == 2)
    assert(
      objects.writeOrder.toVector.drop(writes.size).size == 1 && objects.writeOrder.last.startsWith(
        "graph/rejected/versions/"
      )
    )
    assert(
      StorageResult.value(vectors.get("paper-abstract-v1", original.map(_.vectorKey))).get.size == 2
    )
  }
  test("growing a bound group rejects all new members before any embedding or new vector") {
    val (objects, vectors, _, _, embed, runner) = fixture()
    val original = group(Vector("original"))
    assert(
      StorageResult.value(runner.run(EmbeddingManifest(original), "original")).get.written == 1
    )
    val changed = group(Vector("changed-prefix", "new-tail"))
    val writes = objects.writeOrder.toVector
    val report = StorageResult.value(runner.run(EmbeddingManifest(changed), "grow")).get
    assert(
      report.written == 0 && report.rejected == 2 && report.vectorKeyTextConflict == 2 && report.embeddingCalls == 0
    )
    assert(embed.calls == 1 && objects.writeOrder.toVector.drop(writes.size).size == 1)
    assert(objects.writeOrder.last.startsWith("graph/rejected/versions/"))
    assert(
      StorageResult.value(vectors.get("paper-abstract-v1", changed.map(_.vectorKey))).get.size == 1
    )
  }
  test("incomplete and config-invalid groups reject all members before payload writes") {
    val (objects, _, _, _, embed, runner) = fixture()
    val items = group(Vector("first", "second"))
    val missing = StorageResult.value(runner.run(EmbeddingManifest(items.take(1)), "missing")).get
    assert(missing.rejected == 1 && missing.rejections.head.reason == "incomplete-embedding-group")
    val invalid =
      items.updated(1, items(1).copy(textS3Uri = "s3://another-bucket/graph/versions/v/text.json"))
    val rejected = StorageResult.value(runner.run(EmbeddingManifest(invalid), "wrong-pointer")).get
    assert(
      rejected.rejected == 2 && rejected.rejections.forall(
        _.reason == "text-pointer-outside-config"
      )
    )
    assert(
      embed.calls == 0 && objects.writeOrder.size == 2 && objects.writeOrder.forall(
        _.startsWith("graph/rejected/versions/")
      )
    )
  }
  test("legacy individual bindings cannot silently bootstrap a group binding") {
    val (objects, _, registry, _, embed, runner) = fixture()
    val item = group(Vector("original")).head
    val artifact = "embedding:" + StorageKeys.composite(item.indexName, item.vectorKey)
    registry.register(artifact, "binding", item.textS3Uri, item.textHash)
    val report = StorageResult.value(runner.run(EmbeddingManifest(Vector(item)), "legacy")).get
    assert(
      report.rejected == 1 && report.rejections.head.reason == "group-binding-missing" && report.embeddingCalls == 0
    )
    assert(
      registry.get(
        "embedding-group:" + EmbeddingContracts.groupKey(item.document, model),
        "v1"
      ) == Missing
    )
    assert(
      embed.calls == 0 && objects.writeOrder.size == 1 && objects.writeOrder.head.startsWith(
        "graph/rejected/versions/"
      )
    )
  }
  test(
    "local fake state survives save/open with a true unchanged replay and rejects corrupt or changed config state"
  ) {
    val root = Files.createTempDirectory("embedding-state-test-")
    try {
      val path = root.resolve("state.json")
      val first = StorageResult.value(LocalEmbeddingState.open(path, config)).get
      first.vectors.ensureIndex("paper-abstract-v1", 2, "cosine")
      val embed = new Embed
      val items = group(Vector("first", "second"))
      val runner = new EmbeddingManifestRunner(
        config,
        first.objects,
        first.vectors,
        first.registry,
        first.ledger,
        embed
      )
      assert(
        StorageResult.value(runner.run(EmbeddingManifest(items), "before-save")).get.written == 2
      )
      assert(StorageResult.successful(first.save(path)))
      val reopened = StorageResult.value(LocalEmbeddingState.open(path, config)).get
      val replayRunner = new EmbeddingManifestRunner(
        config,
        reopened.objects,
        reopened.vectors,
        reopened.registry,
        reopened.ledger,
        embed
      )
      val report = StorageResult.value(replayRunner.run(EmbeddingManifest(items), "after-open")).get
      assert(
        report.unchanged == 2 && report.written == 0 && report.embeddingCalls == 0 && embed.calls == 2
      )
      assert(StorageResult.value(reopened.ledger.getRun("before-save")).get.state == "complete")
      assert(StorageResult.successful(reopened.save(path)))
      assert(
        LocalEmbeddingState.open(path, config.copy(dimension = 3)) == Rejected(
          "invalid-local-embedding-state"
        )
      )
      val corrupted = ujson.read(Files.readString(path, UTF_8));
      corrupted("payload")("config")("dimension") = 3
      Files.writeString(path, corrupted.render(), UTF_8)
      assert(LocalEmbeddingState.open(path, config) == Rejected("local-state-hash-mismatch"))
    } finally ExportFiles.deleteTree(root)
  }
  test(
    "completed source adapter verifies empty table hashes and rejects malformed completion and mismatched work manifests"
  ) {
    val root = Files.createTempDirectory("embedding-source-test-")
    try {
      val run = "run:00000000-0000-4000-8000-000000000001"
      val lineage = SparkLineage(
        run,
        "fixture-snapshot",
        run,
        "fixture-er",
        "a" * 64,
        Vector.empty,
        Vector.empty
      )
      val context = SparkRecordContext(SchemaVersions.sparkAnalytics, run, None, lineage)
      val names = Vector("semantic-summaries", "nodes/type=topic", "nodes/type=institution")
      val emptyHash = StableIds.sha256Hex("sha256-fixed-256-shard-sorted-row-json-merkle-v1\n")
      val manifests = names.map(name =>
        LoadManifest(
          context,
          "s3",
          name,
          Vector(name),
          "parquet",
          0,
          Vector(if (name == "semantic-summaries") "summaryId" else "nodeId"),
          Vector.empty,
          emptyHash,
          Vector("all-years"),
          "storage-engineer",
          Vector.empty
        )
      )
      names.foreach(name => Files.createDirectories(root.resolve(name)))
      Files.createDirectories(root.resolve("load-manifests"))
      Files.writeString(
        root.resolve("load-manifests/s3.json"),
        upickle.default.write(manifests),
        UTF_8
      )
      Files.writeString(
        root.resolve("load-manifests/s3vectors.json"),
        upickle.default.write(Vector(manifests.head.copy(targetStore = "s3vectors"))),
        UTF_8
      )
      val manifest = ujson.Obj("runId" -> run).render() + "\n"
      val metadata = ujson
        .Obj(
          "runId" -> run,
          "hadoopRunId" -> run,
          "entityResolutionRunId" -> run,
          "entityResolutionPolicyVersion" -> lineage.entityResolutionPolicyVersion,
          "entityResolutionPolicyHash" -> lineage.entityResolutionPolicyHash,
          "tables" -> ujson.Arr.from(
            names.map(name =>
              ujson.Obj(
                "dataset" -> name,
                "path" -> name,
                "rowCount" -> 0L,
                "contentHash" -> emptyHash
              )
            )
          )
        )
        .render() + "\n"
      Files.writeString(root.resolve("run-manifest.json"), manifest, UTF_8)
      Files.writeString(root.resolve("run-metadata.json"), metadata, UTF_8)
      Files.writeString(root.resolve("counters.json"), "[]", UTF_8)
      Files.writeString(
        root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
        StableIds.sha256Hex(manifest + "\n" + metadata) + "\n",
        UTF_8
      )
      val result = StorageResult.value(Phase6EmbeddingSource.load(root)).get
      assert(
        result.summaries.isEmpty && result.nodes.isEmpty && result.scannedRows == 0 && result.tableCounts == names
          .map(_ -> 0L)
          .toMap
      )
      Files.writeString(
        root.resolve("load-manifests/s3vectors.json"),
        upickle.default.write(
          Vector(manifests.head.copy(targetStore = "s3vectors", sortedRowsSha256 = "b" * 64))
        ),
        UTF_8
      )
      assert(Phase6EmbeddingSource.load(root) == Rejected("embedding-work-source-mismatch"))
      Files.writeString(
        root.resolve("load-manifests/s3vectors.json"),
        upickle.default.write(Vector(manifests.head.copy(targetStore = "s3vectors"))),
        UTF_8
      )
      Files.writeString(root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), "invalid", UTF_8)
      assert(Phase6EmbeddingSource.load(root) == Rejected("incomplete-or-corrupt-source-run"))
    } finally ExportFiles.deleteTree(root)
  }
}
