package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.apache.spark.sql.SparkSession
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Discovered by the ordinary independentTests/test gate. All producer/state/output artifacts are
  * temporary; no pre-existing target tree, real export, credentials or provider is required.
  */
class IndependentEmbedding8BPipelineSpec extends AnyFunSuite {
  test(
    "computed G1 export survives local CLI disk replay and fresh-state determinism with bounded source verification"
  ) {
    IndependentStorage7BSupport.temporary("independent-8b-pipeline-") { root =>
      val source = root.resolve("computed-g1")
      val output = root.resolve("local-acceptance")
      try {
        IndependentEmbeddingG1ExportMain.main(Array(source.toString))
        assert(Files.isRegularFile(source.resolve("_SCHOLARCHAIN_SPARK_COMPLETE")))
        val producer = ujson.read(Files.readString(source.resolve("g1-acceptance.json"), UTF_8))
        assert(producer("canonicalResearchers").num == 10)
        assert(producer("canonicalWorks").num == 9)
        assert(producer("windowedEdges").num == 18)
        assert(producer("publishedTables").num == 28)
        assert(producer("allExactEdgeExpectationsMatched").bool)
        IndependentEmbeddingLocalReplayMain.main(Array(source.toString, output.toString))
        val first = ujson.read(Files.readString(output.resolve("first-report.json"), UTF_8))
        val replay = ujson.read(Files.readString(output.resolve("replay-report.json"), UTF_8))
        val fresh = ujson.read(Files.readString(output.resolve("fresh-report.json"), UTF_8))
        assert(first("counters")("written").num == 12 && first("counters")("unchanged").num == 0)
        assert(first("counters")("rejected").num == 0 && first("counters")("conflicts").num == 0)
        assert(replay("counters")("written").num == 0 && replay("counters")("unchanged").num == 12)
        assert(
          replay("counters")("embeddingCalls").num == 0 && replay("counters")("rejected").num == 0
        )
        assert(first("counters") == fresh("counters"))
        assert(first("embeddingManifestSha256") == fresh("embeddingManifestSha256"))
        assert(first("embeddingManifestSha256") == replay("embeddingManifestSha256"))
        val acceptance = ujson.read(Files.readString(output.resolve("acceptance.json"), UTF_8))
        assert(
          acceptance("verifiedPointerCount").num == 12 && acceptance(
            "allPersistedPointersVerified"
          ).bool
        )
        assert(acceptance("sourceQualificationsHashVerified").bool)
        // Independent read of every stored envelope confirms that the disk-backed path was used.
        val config = upickle.default.read[LocalEmbeddingConfig](
          Files.readString(output.resolve("local-config.json"), UTF_8)
        )
        val state = StorageResult
          .value(LocalEmbeddingState.open(output.resolve("state-a.json"), config.ingest))
          .get
        val manifest = upickle.default.read[EmbeddingManifest](
          Files.readString(output.resolve("first-manifest.json"), UTF_8)
        )
        assert(manifest.items.size == 12)
        manifest.items.foreach { item =>
          val vector =
            StorageResult.value(state.vectors.get(item.indexName, Vector(item.vectorKey))).get.head
          val key = item.textS3Uri.stripPrefix("s3://synthetic-local-text/")
          val stored = StorageResult.value(state.objects.get(key)).get
          assert(stored.head.sha256 == StorageKeys.sha256(stored.bytes))
          val body = ujson.read(new String(stored.bytes.toArray, UTF_8))
          assert(body("textHash").str == StableIds.sha256Hex(body("document")("text").str))
          assert(
            SemanticContexts
              .fromStoredObject(VectorHit(item.vectorKey, 0.0, vector.metadata), stored)
              .isRight
          )
        }
        val qualifications =
          Files.readString(output.resolve("first-report.json.source-qualifications.json"), UTF_8)
        assert(StableIds.sha256Hex(qualifications) == first("sourceQualificationsSha256").str)
        verifyRenderOnlyLiveManifest(source, root.resolve("render-only"), config)
        val work = Some(source.resolve("load-manifests/s3vectors.json"))
        assert(
          Phase6EmbeddingSource.load(
            source,
            EmbeddingSourceSelection(maxScannedRows = 1),
            work
          ) == StorageResult.Rejected("embedding-source-scan-limit")
        )
        val selection =
          EmbeddingSourceSelection(maxSummaries = 4, maxTopicNodes = 0, maxInstitutionNodes = 0)
        val batch = StorageResult.value(Phase6EmbeddingSource.load(source, selection, work)).get
        val repeated = StorageResult.value(Phase6EmbeddingSource.load(source, selection, work)).get
        assert(batch.summaries.size == 4)
        assert(
          batch.summaries.map(_.summaryType) == Vector(
            "collaboration-path",
            "community",
            "paper",
            "researcher-profile"
          )
        )
        assert(
          batch.summaries.groupMapReduce(_.summaryType)(_ => 1)(_ + _) == Map(
            "collaboration-path" -> 1,
            "community" -> 1,
            "paper" -> 1,
            "researcher-profile" -> 1
          )
        )
        assert(batch.summaries.map(_.summaryId) == repeated.summaries.map(_.summaryId))
        val rendered = EmbeddingIngestMain.renderSource(batch, config).toOption.get
        val repeatedRendered = EmbeddingIngestMain.renderSource(repeated, config).toOption.get
        val keys = rendered.map(EmbeddingContracts.vectorKey(_, config.model))
        assert(keys == repeatedRendered.map(EmbeddingContracts.vectorKey(_, config.model)))
        assert(keys.size == 4 && keys.distinct.size == 4)
      } finally {
        SparkSession.getActiveSession.foreach(_.stop())
        SparkSession.getDefaultSession.foreach(_.stop())
        SparkSession.clearActiveSession()
        SparkSession.clearDefaultSession()
      }
    }
  }
  private def verifyRenderOnlyLiveManifest(
      source: Path,
      output: Path,
      local: LocalEmbeddingConfig
  ): Unit = {
    Files.createDirectories(output)
    val realModel = EmbeddingModel("amazon.titan-embed-text-v2:0", "configured-version-v1", 256)
    val rendering = local.copy(model = realModel)
    val configFile = output.resolve("render-config.json")
    val manifestFile = output.resolve("real-model-manifest.json")
    val reportFile = output.resolve("render-report.json")
    Files.writeString(configFile, upickle.default.write(rendering), UTF_8)
    val result = EmbeddingManifestMain
      .run(
        Seq(
          "--export",
          source.toString,
          "--work-manifest",
          source.resolve("load-manifests/s3vectors.json").toString,
          "--config",
          configFile.toString,
          "--manifest-output",
          manifestFile.toString,
          "--report",
          reportFile.toString
        )
      )
      .fold(fail(_), identity)
    assert(
      result("mode").str == "render-only" && result("embeddingCalls").num == 0 && !result(
        "stateWritten"
      ).bool
    )
    assert(
      result("selectedDocuments").num == 12 && result("model") == upickle.default.writeJs(realModel)
    )
    val manifestText = Files.readString(manifestFile, UTF_8)
    val manifest = upickle.default.read[EmbeddingManifest](manifestText)
    assert(manifest.items.size == 12 && manifest.items.forall(_.embeddingModel == realModel))
    assert(manifest.items.forall(EmbeddingValidation.workItem(_).isEmpty))
    val entries = Files.walk(output)
    val files =
      try
        entries
          .iterator()
          .asScala
          .filter(Files.isRegularFile(_))
          .map(output.relativize(_).toString)
          .toVector
      finally entries.close()
    assert(
      !files.exists(name =>
        name.contains("state") || name.contains("prepared") || name.contains("vector")
      )
    )
    assert(!Files.exists(output.resolve("state-a.json")))
    val live = LiveEmbeddingConfig(
      "synthetic-preflight-only",
      "us-east-2",
      "unused-profile",
      realModel,
      rendering.textBucket,
      rendering.textPrefix,
      "synthetic-vectors",
      DynamoTables(
        "synthetic-runs",
        "synthetic-links",
        "synthetic-sessions",
        "synthetic-evidence",
        "synthetic-artifacts",
        "synthetic-metrics",
        "synthetic-idempotency"
      ),
      EmbeddingContracts.indexes,
      "cosine",
      12,
      1,
      2,
      24,
      1.0,
      0.001,
      0.001,
      0.01
    )
    val liveText = upickle.default.write(live)
    val gateText = "SYNTHETIC PURE PREFLIGHT FIXTURE. This is not an actual human approval."
    val approval = LiveEmbeddingApproval(
      true,
      live.environment,
      "synthetic-pure-run",
      StableIds.sha256Hex(liveText),
      StableIds.sha256Hex(manifestText),
      "unused-synthetic-gate",
      StableIds.sha256Hex(gateText),
      12,
      1,
      24,
      1.0,
      true,
      true,
      2000L
    )
    val approvalText = upickle.default.write(approval)
    val plan = LiveEmbeddingIngestMain
      .preflight(liveText, manifestText, approvalText, gateText, "synthetic-pure-run", 1000L)
      .fold(fail(_), identity)
    assert(plan.manifest == manifest && plan.maxEmbeddingRequests == 24)
    // Report construction is pure; this result is a hypothetical serialization fixture, never an execution claim.
    val hypothetical = EmbeddingIngestReport(
      11,
      0,
      0,
      1,
      2,
      Map("researcher-profile-v1" -> 11),
      14,
      1000000000L,
      Vector(VectorReject("synthetic-rejected-key", "embedding-provider-rejected")),
      Some("s3://synthetic-text/rejected/report.json")
    )
    val report = LiveEmbeddingIngestMain.report(
      plan,
      hypothetical,
      "synthetic-pure-run",
      StableIds.sha256Hex(liveText),
      StableIds.sha256Hex(manifestText),
      StableIds.sha256Hex(approvalText)
    )
    assert(report("model") == upickle.default.writeJs(realModel))
    assert(report("perIndex")("researcher-profile-v1").num == 11)
    assert(report("rejections")(0)("key").str == "synthetic-rejected-key")
    assert(report("rejections")(0)("reason").str == "embedding-provider-rejected")
    assert(report("rejectedReportUri").str == "s3://synthetic-text/rejected/report.json")
    assert(!report("billingGuarantee").bool)
  }

}
