package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.Files
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.write

/** Only pure preflight and refused execution are exercised. No approved execution path or AWS
  * factory is invoked by this suite, even when a synthetic pure preflight plan is accepted.
  */
class LiveEmbeddingGuardSpec extends AnyFunSuite {
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
  private val config = LiveEmbeddingConfig(
    "fixture-environment",
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
    3,
    30,
    5.0,
    0.01,
    0.01,
    0.10
  )
  private val document =
    new DocumentRenderer(RenderingConfig("fixture-template", ChunkPolicy(1000, 0)))
      .render(
        RenderInput(
          "paper",
          "synthetic-work",
          "synthetic-window",
          "synthetic-source",
          Vector(
            SourceField(
              "title",
              "Synthetic paper",
              SummarySourceRef("synthetic-works", "synthetic-work", "title")
            )
          )
        )
      )
      .toOption
      .get
      .head
  private val manifest = EmbeddingManifest(
    Vector(EmbeddingManifests.item(document, model, config.ingest))
  )
  private val configText = write(config)
  private val manifestText = write(manifest)
  private val gateText = "Synthetic gate text for pure guard tests; no actual execution approval."
  private val now = 1000L
  private def approval = LiveEmbeddingApproval(
    true,
    config.environment,
    "synthetic-live-run",
    StableIds.sha256Hex(configText),
    StableIds.sha256Hex(manifestText),
    "synthetic-gate-reference",
    StableIds.sha256Hex(gateText),
    10,
    2,
    30,
    5.0,
    true,
    true,
    2000
  )
  private def check(
      a: LiveEmbeddingApproval = approval,
      c: String = configText,
      m: String = manifestText,
      g: String = gateText
  ) = LiveEmbeddingIngestMain.preflight(c, m, write(a), g, "synthetic-live-run", now)

  test(
    "pure preflight binds exact content, run, expiry, caps and conservative configured estimate"
  ) {
    val plan = check().toOption.get
    assert(plan.manifest.items.size == 1 && plan.maxEmbeddingRequests == 3)
    assert(plan.assumedUpperBoundUsd == BigDecimal("0.14"))
    assert(check(approval.copy(executionApproved = false)) == Left("live-approval-required"))
    assert(check(approval.copy(pricingValidated = false)) == Left("live-approval-required"))
    assert(check(approval.copy(budgetValidated = false)) == Left("live-approval-required"))
    assert(
      check(approval.copy(runId = "different-run")) == Left("live-approval-identity-or-expiry")
    )
    assert(
      check(approval.copy(expiresAtEpochSeconds = now)) == Left("live-approval-identity-or-expiry")
    )
    assert(check(c = configText + " ") == Left("live-approval-content-mismatch"))
    assert(check(m = manifestText + " ") == Left("live-approval-content-mismatch"))
    assert(check(g = gateText + " ") == Left("live-approval-content-mismatch"))
  }
  test("vector, concurrency, request and price approval limits refuse before clients") {
    assert(check(approval.copy(vectorCap = 9)) == Left("live-approval-cap-mismatch"))
    assert(check(approval.copy(concurrencyCap = 1)) == Left("live-approval-cap-mismatch"))
    assert(check(approval.copy(embeddingCallCap = 29)) == Left("live-approval-cap-mismatch"))
    assert(check(approval.copy(dollarCapUsd = 4.99)) == Left("live-approval-cap-mismatch"))
    val expensive = write(config.copy(assumedMaxDollarsPerEmbeddingAttempt = 2.0))
    assert(
      check(approval.copy(configSha256 = StableIds.sha256Hex(expensive)), c = expensive) ==
        Left("live-assumed-cost-or-request-bound")
    )
    val requestBound = write(config.copy(maxEmbeddingCalls = 2))
    assert(
      check(approval.copy(configSha256 = StableIds.sha256Hex(requestBound)), c = requestBound) ==
        Left("live-assumed-cost-or-request-bound")
    )
  }
  test("partial or inconsistent chunk groups refuse with bounded work even at an IntMax count") {
    val partialDocument = document.copy(chunkCount = Int.MaxValue)
    val partial = write(
      EmbeddingManifest(Vector(EmbeddingManifests.item(partialDocument, model, config.ingest)))
    )
    assert(
      check(approval.copy(manifestSha256 = StableIds.sha256Hex(partial)), m = partial) ==
        Left("live-manifest-invalid-or-partial-group")
    )
    val changedPointer = manifest.copy(items =
      manifest.items.map(_.copy(textS3Uri = "s3://wrong-bucket/rag/versions/x/doc.json"))
    )
    val changedText = write(changedPointer)
    assert(
      check(approval.copy(manifestSha256 = StableIds.sha256Hex(changedText)), m = changedText) ==
        Left("live-manifest-invalid-or-partial-group")
    )
  }
  test("disabled approval refuses executable run before credential/client factory or gate reads") {
    val directory = Files.createTempDirectory("embedding-live-refusal-")
    val cp = directory.resolve("config.json")
    val mp = directory.resolve("manifest.json")
    val ap = directory.resolve("approval.json")
    val rp = directory.resolve("report.json")
    Files.writeString(cp, configText, UTF_8)
    Files.writeString(mp, manifestText, UTF_8)
    Files.writeString(
      ap,
      write(
        approval.copy(
          executionApproved = false,
          phase14GateReference = directory.resolve("absent-gate.md").toString
        )
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
        "synthetic-live-run"
      ),
      _ => { constructed += 1; throw new IllegalStateException("must-not-construct") },
      now
    )
    assert(result == Left("live-approval-required") && constructed == 0 && !Files.exists(rp))
    assert(
      LiveEmbeddingIngestMain.run(
        Seq.empty,
        _ => { constructed += 1; throw new IllegalStateException },
        now
      ) ==
        Left("invalid-live-arguments")
    )
    assert(constructed == 0)
  }
}
