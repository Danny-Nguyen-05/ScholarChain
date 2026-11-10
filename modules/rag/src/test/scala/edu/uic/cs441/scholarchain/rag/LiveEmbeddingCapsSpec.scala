package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.write

/** Phase 14 gap fixes: N15 (a query-smoke approval carries only query-sized caps) and the
  * token-derived embedding spend bound that refuses before any client or Titan call. Synthetic
  * fixtures and pure preflight only; no provider, credential or AWS client is created.
  */
class LiveEmbeddingCapsSpec extends AnyFunSuite {
  private val model = EmbeddingModel("amazon.titan-embed-text-v2:0", "fixture-v1", 256)
  private val tables = DynamoTables(
    "fixture-runs",
    "fixture-links",
    "fixture-sessions",
    "fixture-evidence",
    "fixture-artifacts",
    "fixture-metrics",
    "fixture-idempotency"
  )
  private val gate = "Synthetic gate text for pure cap tests; not an actual approval."
  private val renderer = new DocumentRenderer(
    RenderingConfig("fixture-template", ChunkPolicy(1000, 0))
  )

  /** Rendered text is "<heading>\ntitle: " + 92 x's, i.e. heading bytes + 8 + 92. */
  private def item(live: LiveEmbeddingConfig, kind: String, entity: String) = {
    val document = renderer
      .render(
        RenderInput(
          kind,
          entity,
          "w",
          "r",
          Vector(
            SourceField("title", "x" * 92, SummarySourceRef("synthetic-source", entity, "title"))
          )
        )
      )
      .fold(fail(_), identity)
      .head
    EmbeddingManifests.item(document, model, live.ingest)
  }
  private val kinds = EmbeddingContracts.indexes.keys.toVector.sorted
  // Hand-derived UTF-8 bytes per kind: heading + "\ntitle: " (8) + 92.
  private val headingBytes = Map(
    "researcher-profile" -> 18,
    "community" -> 23,
    "collaboration-path" -> 18,
    "paper" -> 13,
    "topic-institution-summary" -> 29
  )

  private def liveConfig(
      maxVectors: Int = 1000,
      attempts: Int = 2,
      calls: Long = 10,
      cap: Double = 0.10,
      perAttempt: Double = .0002,
      storage: Double = .0001,
      overhead: Double = .05
  ) = LiveEmbeddingConfig(
    "fixture-env",
    "us-east-2",
    "fixture-profile",
    model,
    "fixture-text",
    "embedding-text",
    "fixture-vectors",
    tables,
    EmbeddingContracts.indexes,
    "cosine",
    maxVectors,
    2,
    attempts,
    calls,
    cap,
    perAttempt,
    storage,
    overhead
  )

  private def ingestApproval(
      configText: String,
      manifestText: String,
      vectors: Int,
      calls: Long,
      dollars: Double
  ) = LiveEmbeddingApproval(
    true,
    "fixture-env",
    "caps-run",
    StableIds.sha256Hex(configText),
    StableIds.sha256Hex(manifestText),
    "phase14-gate-fixture",
    StableIds.sha256Hex(gate),
    vectors,
    2,
    calls,
    dollars,
    true,
    true,
    2000
  )

  // ----- N15: query-smoke approval is query-sized, independent of a large ingest manifest -----

  private val smokeLive = liveConfig()
  private val bigItems =
    kinds.map(k => item(smokeLive, k, "first-" + k)) ++
      (1 to 200).map(i => item(smokeLive, "paper", "extra-paper-" + i))
  private val bigManifestText = write(EmbeddingManifest(bigItems.toVector))
  private def smokeQueries(text: String = "Synthetic query") = kinds.map { kind =>
    val first = bigItems
      .find(i => i.document.documentType == kind && i.document.entityId == "first-" + kind)
      .get
    LiveSmokeQuery("q-" + kind, first.indexName, text, Vector(first.vectorKey), 1)
  }
  private def smokeConfig(
      live: LiveEmbeddingConfig = smokeLive,
      queries: Vector[LiveSmokeQuery] = smokeQueries(),
      requests: Long = 5,
      embeddings: Long = 10,
      reads: Long = 5,
      cap: Double = 0.10
  ) = LiveEmbeddingSmokeConfig(live, queries, 1, requests, embeddings, 1, reads, .0001, .0001, cap)
  private def smokeApproval(c: LiveEmbeddingSmokeConfig, m: String = bigManifestText) =
    LiveEmbeddingApproval(
      true,
      "fixture-env",
      "caps-run",
      StableIds.sha256Hex(write(c)),
      StableIds.sha256Hex(m),
      "phase14-gate-fixture",
      StableIds.sha256Hex(gate),
      0,
      0,
      0,
      0.10,
      true,
      true,
      2000,
      operation = "query-smoke",
      queryRequestCap = 5,
      queryEmbeddingCallCap = 10,
      queryObjectReadCap = 5
    )
  private def smoke(c: LiveEmbeddingSmokeConfig, a: LiveEmbeddingApproval) =
    LiveEmbeddingSmokeMain.preflight(write(c), bigManifestText, write(a), gate, "caps-run", 1000)

  test("N15: large ingest manifest with a small query-only approval is accepted") {
    assert(bigItems.size == 205)
    val c = smokeConfig()
    val a = smokeApproval(c)
    // The approval carries zero ingest vector/concurrency/embedding-call caps.
    assert(a.vectorCap == 0 && a.concurrencyCap == 0 && a.embeddingCallCap == 0)
    val plan = smoke(c, a).fold(fail(_), identity)
    // 5 queries x 1 sample; 5 queries x 2 attempts; 5 queries x topK 1 x 1 sample.
    assert(
      plan.queryRequests == 5 && plan.queryEmbeddingRequests == 10 && plan.objectReadBound == 5
    )
    assert(plan.manifest.items.size == 205)
    // Dollars: 10 x 0.0002 + 5 x 0.0001 + 5 x 0.0001 + 0.05 = 0.053 (< smoke cap 0.10). Tokens for
    // the query texts: 5 x 15 bytes x 2 attempts = 150, i.e. 150 x 0.02 / 1e6 = 0.000003 USD,
    // far below the per-attempt bound 0.002, so the per-attempt bound dominates.
    assert(plan.queryEmbeddingTokenBound == BigInt(150))
    assert(plan.assumedUpperBoundUsd == BigDecimal("0.053"))
  }

  test("N15: the same manifest and an ingest-sized caps profile is refused for ingest") {
    // Ingest would need 205 x 2 = 410 embedding calls against a call cap of 10, so the ingest
    // preflight refuses, while the smoke above never required those caps.
    val ingestConfigText = write(smokeLive)
    val approval = ingestApproval(ingestConfigText, bigManifestText, 1000, 10, 0.10)
    assert(
      LiveEmbeddingIngestMain.preflight(
        ingestConfigText,
        bigManifestText,
        write(approval),
        gate,
        "caps-run",
        1000
      ) == Left("live-assumed-cost-or-request-bound")
    )
  }

  test("N15: query caps, smoke dollar cap, identity and expiry remain enforced") {
    val c = smokeConfig()
    val a = smokeApproval(c)
    assert(smoke(c, a.copy(queryRequestCap = 4)) == Left("invalid-smoke-config-or-approval-caps"))
    assert(
      smoke(c, a.copy(queryEmbeddingCallCap = 9)) == Left("invalid-smoke-config-or-approval-caps")
    )
    assert(
      smoke(c, a.copy(queryObjectReadCap = 4)) == Left("invalid-smoke-config-or-approval-caps")
    )
    // Smoke dollar cap above the approved dollar cap.
    assert(smoke(c, a.copy(dollarCapUsd = 0.09)) == Left("invalid-smoke-config-or-approval-caps"))
    // Negative ingest fields are never a valid grant.
    assert(smoke(c, a.copy(vectorCap = -1)) == Left("invalid-smoke-config-or-approval-caps"))
    assert(smoke(c, a.copy(runId = "other")) == Left("smoke-approval-identity-or-expiry"))
    assert(
      smoke(c, a.copy(expiresAtEpochSeconds = 1000)) == Left("smoke-approval-identity-or-expiry")
    )
    assert(
      smoke(c, a.copy(environment = "other-env")) == Left("invalid-smoke-config-or-approval-caps")
    )
    // Config bounds below the computed workload: 10 query embeddings > 9.
    val tight = smokeConfig(embeddings = 9)
    assert(smoke(tight, smokeApproval(tight)) == Left("smoke-request-or-assumed-cost-bound"))
    // 0.053 assumed upper bound > 0.05 smoke cap.
    val cheap = smokeConfig(cap = 0.05)
    assert(
      smoke(cheap, smokeApproval(cheap).copy(dollarCapUsd = 0.05)) ==
        Left("smoke-request-or-assumed-cost-bound")
    )
  }

  test("N15: a smoke still refuses an invalid or partial manifest and a wrong expected key") {
    val c = smokeConfig()
    val partial = write(EmbeddingManifest(bigItems.toVector.drop(1).take(3)))
    assert(
      LiveEmbeddingSmokeMain
        .preflight(
          write(c),
          partial,
          write(smokeApproval(c, partial)),
          gate,
          "caps-run",
          1000
        )
        .isLeft
    )
    val wrongKey = smokeConfig(queries =
      smokeQueries().updated(0, smokeQueries().head.copy(expectedVectorKeys = Vector("absent")))
    )
    assert(
      smoke(wrongKey, smokeApproval(wrongKey)) == Left("invalid-smoke-config-or-approval-caps")
    )
  }

  test("smoke embedding spend is also bounded by query-text tokens at the configured rate") {
    // 5 queries x 8000 ASCII bytes x 2 attempts = 80,000 tokens. At 20 USD per million tokens that
    // is 1.6 USD, over the 0.10 cap, although the per-attempt bound is only 10 x 0.0002 = 0.002.
    val pricey = liveConfig().copy(assumedUsdPerMillionEmbeddingTokens = 20.0)
    val c = smokeConfig(live = pricey, queries = smokeQueries("a" * 8000))
    val plan = smoke(c, smokeApproval(c))
    assert(plan == Left("smoke-request-or-assumed-cost-bound"))
    // At the default 0.02 per million the same text costs 80,000 x 0.02 / 1e6 = 0.0016 <
    // 0.002 per-attempt bound, so the total stays 0.053.
    val ok = smokeConfig(queries = smokeQueries("a" * 8000))
    val accepted = smoke(ok, smokeApproval(ok)).fold(fail(_), identity)
    assert(accepted.queryEmbeddingTokenBound == BigInt(80000))
    assert(accepted.assumedUpperBoundUsd == BigDecimal("0.053"))
  }

  // ----- Embedding spend bound (Titan USD 0.30 at USD 0.02 per million tokens) -----

  private val titanLive = liveConfig(
    maxVectors = 5,
    attempts = 2,
    calls = 10,
    cap = 0.30,
    perAttempt = 1e-9,
    storage = 1e-9,
    overhead = 0.0
  )
  private val titanItems = kinds.map(k => item(titanLive, k, "e-" + k))
  private val titanManifest = write(EmbeddingManifest(titanItems.toVector))

  private def ingest(config: LiveEmbeddingConfig) = {
    val text = write(config)
    val approval = ingestApproval(text, titanManifest, 5, 10, 0.30)
    LiveEmbeddingIngestMain.preflight(text, titanManifest, write(approval), gate, "caps-run", 1000)
  }

  test("token bound is hand-derived: 601 bytes per pass, 1202 tokens over 2 attempts") {
    assert(titanItems.map(_.document.text.getBytes(UTF_8).length).sum == 601)
    assert(kinds.map(headingBytes(_) + 100).sum == 601)
    val plan = ingest(titanLive).fold(fail(_), identity)
    assert(plan.plannedEmbeddingTokens == BigInt(1202))
    // 1202 x 0.02 / 1e6 = 0.00002404 dominates 10 x 1e-9 = 1e-8; plus storage 5e-9.
    assert(plan.assumedUpperBoundUsd == BigDecimal("0.000024045"))
  }

  test("minBytesPerEmbeddingToken rounds each item up: 59+62+59+57+65 = 302 per pass") {
    val plan = ingest(titanLive.copy(minBytesPerEmbeddingToken = 2)).fold(fail(_), identity)
    // Items are 118, 123, 118, 113, 129 bytes -> ceil(n/2) = 59, 62, 59, 57, 65 -> 302 x 2.
    assert(plan.plannedEmbeddingTokens == BigInt(604))
  }

  test("the default price is USD 0.02 per million tokens: 15,000,000 tokens is exactly USD 0.30") {
    assert(titanLive.assumedUsdPerMillionEmbeddingTokens == 0.02)
    assert(LiveEmbeddingIngestMain.tokenUsd(BigInt(15000000), titanLive) == BigDecimal("0.30"))
    assert(LiveEmbeddingIngestMain.tokenUsd(BigInt(15000001), titanLive) > BigDecimal("0.30"))
    assert(LiveEmbeddingIngestMain.tokenUsd(BigInt(14999999), titanLive) < BigDecimal("0.30"))
  }

  test("ingest refuses when the token estimate crosses the USD 0.30 cap, accepts just below") {
    // 1202 tokens: 249.5 USD/M gives 0.299899 (+5e-9) <= 0.30 accepted; 250 USD/M gives 0.3005.
    assert(ingest(titanLive.copy(assumedUsdPerMillionEmbeddingTokens = 249.5)).isRight)
    assert(
      ingest(titanLive.copy(assumedUsdPerMillionEmbeddingTokens = 250.0)) ==
        Left("live-assumed-cost-or-request-bound")
    )
  }

  test("run refuses on the token bound before the factory, any client or the report is touched") {
    val root = Files.createTempDirectory("embedding-token-bound-")
    val config = titanLive.copy(assumedUsdPerMillionEmbeddingTokens = 250.0)
    val cp = root.resolve("config.json"); val mp = root.resolve("manifest.json")
    val ap = root.resolve("approval.json"); val gp = root.resolve("gate.md")
    val rp = root.resolve("report.json")
    val configText = write(config)
    Files.writeString(cp, configText, UTF_8)
    Files.writeString(mp, titanManifest, UTF_8)
    Files.writeString(gp, gate, UTF_8)
    Files.writeString(
      ap,
      write(
        ingestApproval(configText, titanManifest, 5, 10, 0.30)
          .copy(phase14GateReference = gp.toString)
      ),
      UTF_8
    )
    var constructed = 0
    val result = LiveEmbeddingIngestMain.run(
      Seq(
        "--config",
        cp.toString,
        "--manifest",
        mp.toString,
        "--approval",
        ap.toString,
        "--report",
        rp.toString,
        "--run-id",
        "caps-run"
      ),
      _ => { constructed += 1; throw new IllegalStateException("must-not-construct") },
      1000
    )
    assert(result == Left("live-assumed-cost-or-request-bound"))
    assert(constructed == 0 && !Files.exists(rp))
  }

  test("config validation rejects a non-positive price and an out-of-range bytes-per-token") {
    intercept[IllegalArgumentException](titanLive.copy(assumedUsdPerMillionEmbeddingTokens = 0.0))
    intercept[IllegalArgumentException](titanLive.copy(minBytesPerEmbeddingToken = 0))
    intercept[IllegalArgumentException](titanLive.copy(minBytesPerEmbeddingToken = 5))
  }
}
