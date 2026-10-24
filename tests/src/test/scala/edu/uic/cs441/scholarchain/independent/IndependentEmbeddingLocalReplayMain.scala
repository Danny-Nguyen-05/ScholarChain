package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}

/** Standalone local acceptance against an actual completed producer export. Input is supplied by
  * the operator (G1 producer harness or retained real-data export), never a hand-made summary
  * batch.
  */
object IndependentEmbeddingLocalReplayMain {
  def main(args: Array[String]): Unit = {
    require(
      args.length == 2,
      "completed Phase6 export and new acceptance-output directory required"
    )
    val source = Path.of(args(0)).toAbsolutePath.normalize()
    val output = Path.of(args(1)).toAbsolutePath.normalize()
    require(!Files.exists(output), "output must be new; refusing overwrite")
    Files.createDirectories(output)
    val config = LocalEmbeddingConfig(
      EmbeddingModel("local-independent-hashed-bag-of-words", "v1", 256),
      "synthetic-local-text",
      "graph",
      "independent-local-v1",
      10000,
      0,
      maxSummaries = 12,
      maxTopicNodes = 3,
      maxInstitutionNodes = 1,
      maxScannedRows = 200000
    )
    val configPath = output.resolve("local-config.json")
    Files.writeString(configPath, upickle.default.write(config), UTF_8)
    def execute(label: String, stateName: String): ujson.Value = {
      val flags = Seq(
        "--export",
        source.toString,
        "--work-manifest",
        source.resolve("load-manifests/s3vectors.json").toString,
        "--config",
        configPath.toString,
        "--state",
        output.resolve(stateName).toString,
        "--report",
        output.resolve(label + "-report.json").toString,
        "--manifest-output",
        output.resolve(label + "-manifest.json").toString,
        "--run-id",
        "independent-" + label
      )
      EmbeddingIngestMain.run(flags).fold(code => throw new IllegalStateException(code), identity)
    }
    val first = execute("first", "state-a.json")
    val replay = execute("replay", "state-a.json")
    val fresh = execute("fresh", "state-b.json")
    require(first("mode").str == "deterministic-fake", "local result must identify the fake")
    val expectedContextNodes = first("sourceRunId").str match {
      case "run:55555555-5555-4555-8555-555555555555" =>
        0 // Actual G1 fixture has no topic/institution input.
      case "run:f02acf56-4bea-4009-adaf-b11d5afceb49" =>
        4 // Retained real export has exactly three topics and one institution.
      case other =>
        throw new IllegalArgumentException(
          "no independent literal source expectations for " + other
        )
    }
    val expectedDocuments = 12 + expectedContextNodes
    require(
      first("selectedDocuments").num == expectedDocuments && first(
        "selectedSourceSummaries"
      ).num == 12,
      "bounded source selection must yield twelve actual summaries plus literal expected context nodes"
    )
    require(
      first("selectedContextNodes").num == expectedContextNodes,
      "actual source topic/institution selection"
    )
    val expectedTypes = Set("researcher-profile", "community", "collaboration-path", "paper") ++
      (if (expectedContextNodes > 0) Set("topic-institution-summary") else Set.empty[String])
    require(
      first("documentTypes").obj.keySet.toSet == expectedTypes,
      "all available source document types must be ingested"
    )
    require(
      first("counters")("written").num == expectedDocuments && first("counters")(
        "unchanged"
      ).num == 0 && first("counters")("rejected").num == 0,
      "first ingestion counters"
    )
    require(
      replay("counters")("written").num == 0 && replay("counters")(
        "unchanged"
      ).num == expectedDocuments && replay("counters")("embeddingCalls").num == 0 && replay(
        "counters"
      )("rejected").num == 0,
      "persistent replay must skip every item without embedding"
    )
    require(
      first("counters") == fresh("counters"),
      "fresh-state runs must have byte-equivalent counter values"
    )
    require(
      first("embeddingManifestSha256") == replay("embeddingManifestSha256") && first(
        "embeddingManifestSha256"
      ) == fresh("embeddingManifestSha256"),
      "rendered manifests must be deterministic"
    )
    val manifest = upickle.default.read[EmbeddingManifest](
      Files.readString(output.resolve("first-manifest.json"), UTF_8)
    )
    val reopened = StorageResult
      .value(LocalEmbeddingState.open(output.resolve("state-a.json"), config.ingest))
      .get
    manifest.items.foreach { item =>
      val vectors =
        StorageResult.value(reopened.vectors.get(item.indexName, Vector(item.vectorKey))).get
      require(
        vectors.size == 1 && vectors.head.textHash == item.textHash,
        "persisted vector identity/hash"
      )
      val stored = StorageResult
        .value(reopened.objects.get(item.textS3Uri.stripPrefix("s3://synthetic-local-text/")))
        .get
      val hit = VectorHit(item.vectorKey, 0.0, vectors.head.metadata)
      require(
        SemanticContexts.fromStoredObject(hit, stored).isRight,
        "persisted vector pointer and hash must resolve"
      )
    }
    val qualifications = Files.readString(Path.of(first("sourceQualificationsPath").str), UTF_8)
    require(
      StableIds.sha256Hex(qualifications) == first("sourceQualificationsSha256").str,
      "exact retained qualifications hash"
    )
    require(
      qualifications.contains("approximate P90") && qualifications.contains(
        "Community convergence"
      ),
      "upstream qualifications remain explicit"
    )
    val acceptance = ujson.Obj(
      "sourceExport" -> source.toString,
      "sourceRunId" -> first("sourceRunId"),
      "selectedActualSummaries" -> 12,
      "selectedActualContextNodes" -> expectedContextNodes,
      "firstWritten" -> expectedDocuments,
      "replayUnchanged" -> expectedDocuments,
      "replayEmbeddingCalls" -> 0,
      "freshCountersIdentical" -> true,
      "manifestHashesIdentical" -> true,
      "allPersistedPointersVerified" -> true,
      "verifiedPointerCount" -> expectedDocuments,
      "allAvailableSourceDocumentTypesIngested" -> true,
      "sourceQualificationsHashVerified" -> true,
      "mode" -> "deterministic-fake"
    )
    Files.writeString(output.resolve("acceptance.json"), acceptance.render() + "\n", UTF_8)
    println(acceptance.render())
  }
}
