package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{read, write, writeJs}

/** The live config field `tables.idempotencyIndex` is the QuerySession global secondary index NAME
  * (Terraform default `by-idempotency-key`), never a table name. Offline: pure config parsing and
  * preflight, no storage, embedding or network client is created.
  */
class LiveEmbeddingIdempotencyIndexSpec extends AnyFunSuite {
  private val gsi = "by-idempotency-key"
  private val gate = "Synthetic gate text for idempotency index tests; not an actual approval."
  private val renderer =
    new DocumentRenderer(RenderingConfig("fixture-template", ChunkPolicy(1000, 0)))

  private def tables(index: String) = DynamoTables(
    "fixture-runledger",
    "fixture-entitylinks",
    "fixture-querysessions",
    "fixture-evidence",
    "fixture-artifacts",
    "fixture-metrics",
    index
  )
  private def live(index: String) = LiveEmbeddingConfig(
    "fixture-env",
    "us-east-2",
    "fixture-profile",
    VoyageEmbeddingClient.Model,
    "fixture-text",
    "embedding-text",
    "fixture-vectors",
    tables(index),
    EmbeddingContracts.indexes,
    "cosine",
    5,
    2,
    2,
    10,
    0.30,
    1e-9,
    1e-9,
    0.0
  )
  private def manifest(config: LiveEmbeddingConfig) = write(
    EmbeddingManifest(
      EmbeddingContracts.indexes.keys.toVector.sorted.map { kind =>
        val document = renderer
          .render(
            RenderInput(
              kind,
              "e-" + kind,
              "w",
              "r",
              Vector(
                SourceField(
                  "title",
                  "x" * 92,
                  SummarySourceRef("synthetic-source", "e-" + kind, "title")
                )
              )
            )
          )
          .fold(fail(_), identity)
          .head
        EmbeddingManifests.item(document, config.model, config.ingest)
      }
    )
  )

  /** Preflights a config JSON text whose `tables.idempotencyIndex` is replaced by `index`. */
  private def preflightWithIndex(index: String) = {
    val json = writeJs(live(gsi))
    json("tables")("idempotencyIndex") = index
    val text = json.render()
    val items = manifest(live(gsi))
    val approval = LiveEmbeddingApproval(
      true,
      "fixture-env",
      "idem-run",
      StableIds.sha256Hex(text),
      StableIds.sha256Hex(items),
      "phase14-gate-fixture",
      StableIds.sha256Hex(gate),
      5,
      2,
      10,
      0.30,
      true,
      true,
      2000
    )
    LiveEmbeddingIngestMain.preflight(text, items, write(approval), gate, "idem-run", 1000)
  }

  test("the Terraform GSI name by-idempotency-key is accepted and carried to StorageConfig") {
    val config = live(gsi)
    assert(config.tables.idempotencyIndex == "by-idempotency-key")
    assert(read[LiveEmbeddingConfig](write(config)).tables.idempotencyIndex == gsi)
    val storage = edu.uic.cs441.scholarchain.storage.StorageConfig(config.textBucket, config.tables)
    assert(storage.tables.idempotencyIndex == gsi)
    assert(storage.tables.idempotencyIndex != storage.tables.querySessions)
    assert(preflightWithIndex(gsi).isRight)
  }

  test("a blank, malformed or table-name idempotencyIndex is refused at construction") {
    Vector("", "   ", "ab", "has space", "bad/slash", "x" * 256).foreach { bad =>
      intercept[IllegalArgumentException](live(bad))
    }
    // The six table names are never an index name.
    Vector(
      "fixture-runledger",
      "fixture-entitylinks",
      "fixture-querysessions",
      "fixture-evidence",
      "fixture-artifacts",
      "fixture-metrics"
    ).foreach(table => intercept[IllegalArgumentException](live(table)))
  }

  test("a wrong idempotencyIndex in the config file is refused at preflight with a typed code") {
    val refused = Left("invalid-live-config-manifest-or-approval")
    assert(preflightWithIndex("") == refused)
    assert(preflightWithIndex("fixture-querysessions") == refused)
    assert(preflightWithIndex("fixture runledger") == refused)
    assert(preflightWithIndex("fixture-metrics") == refused)
  }
}
