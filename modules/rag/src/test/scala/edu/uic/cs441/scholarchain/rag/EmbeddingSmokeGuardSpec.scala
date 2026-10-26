package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.write

/** Synthetic planning/reporting and refused execution only. No approved run or provider call. */
class EmbeddingSmokeGuardSpec extends AnyFunSuite {
  private val model = EmbeddingModel("configured-titan-fixture", "fixture-v1", 256)
  private val tables = DynamoTables(
    "fixture-runs",
    "fixture-links",
    "fixture-sessions",
    "fixture-evidence",
    "fixture-artifacts",
    "fixture-metrics",
    "fixture-idempotency"
  )
  private val live = LiveEmbeddingConfig(
    "fixture-env",
    "fixture-region",
    "fixture-profile",
    model,
    "fixture-text",
    "rag",
    "fixture-vectors",
    tables,
    EmbeddingContracts.indexes,
    "cosine",
    10,
    2,
    2,
    20,
    5.0,
    .01,
    .01,
    .10
  )
  private val renderer = new DocumentRenderer(
    RenderingConfig("fixture-template", ChunkPolicy(1000, 0))
  )
  private val documents = EmbeddingContracts.indexes.toVector.sortBy(_._1).flatMap { (kind, _) =>
    renderer
      .render(
        RenderInput(
          kind,
          "synthetic-" + kind,
          "synthetic-window",
          "synthetic-source",
          Vector(
            SourceField(
              "title",
              "Synthetic " + kind,
              SummarySourceRef("synthetic-source", kind, "title")
            )
          )
        )
      )
      .fold(fail(_), identity)
  }
  private val manifest = EmbeddingManifest(
    documents.map(d => EmbeddingManifests.item(d, model, live.ingest))
  )
  private val queries = manifest.items.zipWithIndex.map { (item, index) =>
    LiveSmokeQuery(
      "synthetic-query-" + index,
      item.indexName,
      "Synthetic query " + index,
      Vector(item.vectorKey),
      1
    )
  }
  private val config = LiveEmbeddingSmokeConfig(live, queries, 4, 20, 10, 1, 20, .001, .001, 5.0)
  private val ct = write(config); private val mt = write(manifest)
  private val gate = "Synthetic gate for pure tests; no actual cloud approval."
  private def approval = LiveEmbeddingApproval(
    true,
    live.environment,
    "synthetic-smoke",
    StableIds.sha256Hex(ct),
    StableIds.sha256Hex(mt),
    "synthetic-gate",
    StableIds.sha256Hex(gate),
    10,
    2,
    20,
    5.0,
    true,
    true,
    2000,
    operation = "query-smoke",
    queryRequestCap = 20,
    queryEmbeddingCallCap = 10,
    queryObjectReadCap = 20
  )
  private def plan(
      a: LiveEmbeddingApproval = approval,
      c: String = ct,
      m: String = mt,
      g: String = gate
  ) =
    LiveEmbeddingSmokeMain.preflight(c, m, write(a), g, "synthetic-smoke", 1000)

  test("smoke pure preflight binds full config, manifest, gate, operation and bounded calls/cost") {
    val p = plan().fold(fail(_), identity)
    assert(p.queryRequests == 20 && p.queryEmbeddingRequests == 10 && p.objectReadBound == 20)
    assert(p.assumedUpperBoundUsd == BigDecimal(".24"))
    assert(plan(approval.copy(operation = "ingest")) == Left("smoke-approval-required"))
    assert(plan(c = ct + " ") == Left("smoke-approval-content-mismatch"))
    assert(plan(m = mt + " ") == Left("smoke-approval-content-mismatch"))
    assert(plan(g = gate + " ") == Left("smoke-approval-content-mismatch"))
    assert(
      plan(approval.copy(queryRequestCap = 19)) == Left("invalid-smoke-config-or-approval-caps")
    )
    assert(
      plan(approval.copy(queryEmbeddingCallCap = 9)) == Left(
        "invalid-smoke-config-or-approval-caps"
      )
    )
    assert(
      plan(approval.copy(queryObjectReadCap = 19)) == Left("invalid-smoke-config-or-approval-caps")
    )
    assert(
      LiveEmbeddingIngestMain.preflight(
        write(live),
        mt,
        write(approval.copy(configSha256 = StableIds.sha256Hex(write(live)))),
        gate,
        "synthetic-smoke",
        1000
      ) == Left("live-approval-required")
    )
  }
  test(
    "smoke planning requires all five indexes, approved expected keys and bounded samples/topK"
  ) {
    def check(c: LiveEmbeddingSmokeConfig) = {
      val text = write(c)
      plan(approval.copy(configSha256 = StableIds.sha256Hex(text)), c = text)
    }
    assert(
      check(config.copy(queries = queries.take(4))) == Left("invalid-smoke-config-or-approval-caps")
    )
    assert(
      check(
        config.copy(queries =
          queries.updated(0, queries.head.copy(expectedVectorKeys = Vector("unknown-key")))
        )
      ) ==
        Left("invalid-smoke-config-or-approval-caps")
    )
    assert(check(config.copy(samplesPerQuery = 5)) == Left("smoke-request-or-assumed-cost-bound"))
    assert(check(config.copy(maxTopK = 101)) == Left("invalid-smoke-config-or-approval-caps"))
    assert(
      check(
        config.copy(live = live.copy(nonFilterableKeys = Vector("textS3Uri", "embeddingModel")))
      ) ==
        Left("invalid-smoke-config-or-approval-caps")
    )
    assert(
      check(config.copy(assumedMaxDollarsPerQuery = 1.0)) == Left(
        "smoke-request-or-assumed-cost-bound"
      )
    )
  }
  test(
    "pure report has hand-derived nearest-rank latency, exact per-index counts and verified pointers"
  ) {
    val p = plan().fold(fail(_), identity)
    val samples = queries.flatMap(q =>
      Vector(1000000L, 2000000L, 4000000L, 9000000L).map(n =>
        LiveSmokeSample(q.queryId, q.indexName, n, true, 1)
      )
    )
    val report = LiveEmbeddingSmokeMain.report(p, samples, "synthetic-smoke", "c", "m", "a")
    assert(report("model") == upickle.default.writeJs(model) && report("sampleCount").num == 20)
    assert(report("allSamplesPresent").bool && report("allNeighborsMatched").bool)
    assert(report("verifiedPointers").num == 20 && !report("billingGuarantee").bool)
    queries.foreach { q =>
      val summary = report("perIndex")(q.indexName)
      assert(
        summary("samples").num == 4 && summary("p50Millis").num == 2 && summary(
          "p95Millis"
        ).num == 9
      )
      assert(summary("neighborMatched").num == 4 && summary("verifiedPointers").num == 4)
    }
    val incomplete =
      LiveEmbeddingSmokeMain.report(p, samples.drop(1), "synthetic-smoke", "c", "m", "a")
    assert(!incomplete("allSamplesPresent").bool)
  }
  test(
    "approved text pointer scope rejects wrong buckets, traversal and URI decorations before reads"
  ) {
    assert(
      LiveEmbeddingSmokeMain.pointerKey("s3://fixture-text/rag/versions/v/document.json", live) ==
        Right("rag/versions/v/document.json")
    )
    Vector(
      "s3://other-text/rag/versions/v/document.json",
      "s3://fixture-text/other/versions/v/document.json",
      "s3://fixture-text/rag/versions/../document.json",
      "s3://fixture-text/rag/versions/%2e%2e/document.json",
      "s3://fixture-text/rag/versions/v/document.json?query=x",
      "s3://fixture-text/rag/versions/v/document.json#fragment",
      "s3://user@fixture-text/rag/versions/v/document.json"
    ).foreach { uri =>
      assert(LiveEmbeddingSmokeMain.pointerKey(uri, live).isLeft, uri)
    }
  }
  test("disabled or ingest-only smoke approval refuses before credentials, gate read and factory") {
    val root = Files.createTempDirectory("embedding-smoke-refusal-")
    val cp = root.resolve("config.json"); val mp = root.resolve("manifest.json");
    val ap = root.resolve("approval.json")
    val rp = root.resolve("report.json")
    Files.writeString(cp, ct, UTF_8); Files.writeString(mp, mt, UTF_8)
    var constructed = 0
    val args = Seq(
      "--config",
      cp.toString,
      "--manifest",
      mp.toString,
      "--approval",
      ap.toString,
      "--report",
      rp.toString,
      "--run-id",
      "synthetic-smoke"
    )
    def run() = LiveEmbeddingSmokeMain.run(
      args,
      _ => { constructed += 1; throw new IllegalStateException("must-not-construct") },
      1000
    )
    Files.writeString(
      ap,
      write(
        approval.copy(
          executionApproved = false,
          phase14GateReference = root.resolve("absent.md").toString
        )
      ),
      UTF_8
    )
    assert(run() == Left("smoke-approval-required"))
    Files.writeString(
      ap,
      write(
        approval
          .copy(operation = "ingest", phase14GateReference = root.resolve("absent.md").toString)
      ),
      UTF_8
    )
    assert(run() == Left("smoke-approval-required"))
    assert(constructed == 0 && !Files.exists(rp))
  }
}
