package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8

/** Refusal-only tests: injected factory fails if any client boundary is reached. */
class IndependentEmbedding8BGuardSpec extends AnyFunSuite {
  test("missing disabled or content-mismatched live approval never constructs service ports") {
    IndependentStorage7BSupport.temporary("independent-live-refusal-") { root =>
      var constructions = 0
      val factory: LiveEmbeddingConfig => LiveEmbeddingPorts = _ => {
        constructions += 1
        throw new AssertionError("refusal must precede every credential/client boundary")
      }
      val config = root.resolve("config.json")
      val manifest = root.resolve("manifest.json")
      val approvalFile = root.resolve("approval.json")
      val gate = root.resolve("fixture-gate.txt")
      val report = root.resolve("must-not-exist.json")
      Files.writeString(config, "{}", UTF_8)
      Files.writeString(manifest, "{}", UTF_8)
      Files.writeString(gate, "SYNTHETIC NON-APPROVAL GATE FIXTURE", UTF_8)
      def args = Seq(
        "--config",
        config.toString,
        "--manifest",
        manifest.toString,
        "--approval",
        approvalFile.toString,
        "--report",
        report.toString,
        "--run-id",
        "synthetic-run"
      )
      assert(LiveEmbeddingIngestMain.run(args, factory, 1L).isLeft)
      val disabled = LiveEmbeddingApproval(
        false,
        "synthetic",
        "synthetic-run",
        "0" * 64,
        "0" * 64,
        gate.toString,
        "0" * 64,
        1,
        1,
        1,
        1.0,
        false,
        false,
        100L
      )
      Files.writeString(approvalFile, upickle.default.write(disabled), UTF_8)
      assert(LiveEmbeddingIngestMain.run(args, factory, 1L) == Left("live-approval-required"))
      val mismatched =
        disabled.copy(executionApproved = true, pricingValidated = true, budgetValidated = true)
      Files.writeString(approvalFile, upickle.default.write(mismatched), UTF_8)
      assert(
        LiveEmbeddingIngestMain.run(args, factory, 1L) == Left("live-approval-content-mismatch")
      )
      assert(constructions == 0 && !Files.exists(report))
    }
  }

  test("the local CLI refuses a live flag before accessing any state or provider") {
    assert(EmbeddingIngestMain.run(Seq("--execute-aws", "true")) == Left("invalid-local-arguments"))
    assert(
      LiveEmbeddingIngestMain.run(
        Seq("--execute-aws", "true"),
        _ => throw new AssertionError("no client construction"),
        1L
      ) == Left("invalid-live-arguments")
    )
  }
  test(
    "query smoke rejects missing disabled and wrong-operation grants before constructing ports"
  ) {
    IndependentStorage7BSupport.temporary("independent-smoke-refusal-") { root =>
      var constructions = 0
      val factory: LiveEmbeddingSmokeConfig => LiveEmbeddingSmokePorts = _ => {
        constructions += 1
        throw new AssertionError("query refusal must precede every client boundary")
      }
      val model = EmbeddingModel("synthetic-query-shape", "v1", 256)
      val live = LiveEmbeddingConfig(
        "synthetic",
        "us-east-2",
        "unused-profile",
        model,
        "synthetic-text",
        "graph",
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
        5,
        1,
        1,
        5,
        1.0,
        0.001,
        0.001,
        0.0
      )
      val renderer =
        new DocumentRenderer(RenderingConfig("synthetic-template", ChunkPolicy(1000, 0)))
      val items = EmbeddingContracts.documentTypes.toVector.sorted.map { kind =>
        val document = renderer
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
          .toOption
          .get
          .head
        EmbeddingManifests.item(document, model, live.ingest)
      }
      val queries = items.zipWithIndex.map { (item, ordinal) =>
        LiveSmokeQuery(
          "synthetic-query-" + ordinal,
          item.indexName,
          "Synthetic query",
          Vector(item.vectorKey),
          1
        )
      }
      val smoke = LiveEmbeddingSmokeConfig(live, queries, 1, 5, 5, 1, 5, 0.001, 0.001, 1.0)
      val configText = upickle.default.write(smoke)
      val manifestText = upickle.default.write(EmbeddingManifest(items))
      val gateText = "SYNTHETIC PURE REFUSAL FIXTURE; NOT AN ACTUAL HUMAN APPROVAL."
      val configFile = root.resolve("config.json")
      val manifestFile = root.resolve("manifest.json")
      val gateFile = root.resolve("fixture-gate.txt")
      val approvalFile = root.resolve("grant.json")
      val reportFile = root.resolve("must-not-exist.json")
      Files.writeString(configFile, configText, UTF_8)
      Files.writeString(manifestFile, manifestText, UTF_8)
      Files.writeString(gateFile, gateText, UTF_8)
      val grant = LiveEmbeddingApproval(
        true,
        "synthetic",
        "synthetic-query-run",
        StableIds.sha256Hex(configText),
        StableIds.sha256Hex(manifestText),
        gateFile.toString,
        StableIds.sha256Hex(gateText),
        5,
        1,
        5,
        1.0,
        true,
        true,
        2000L,
        operation = "query-smoke",
        queryRequestCap = 5,
        queryEmbeddingCallCap = 5,
        queryObjectReadCap = 5
      )
      // Only the pure parser/planner sees a valid synthetic grant; the execution entry point never does.
      assert(
        LiveEmbeddingSmokeMain
          .preflight(
            configText,
            manifestText,
            upickle.default.write(grant),
            gateText,
            "synthetic-query-run",
            1000L
          )
          .isRight
      )
      val args = Seq(
        "--config",
        configFile.toString,
        "--manifest",
        manifestFile.toString,
        "--approval",
        approvalFile.toString,
        "--report",
        reportFile.toString,
        "--run-id",
        "synthetic-query-run"
      )
      assert(LiveEmbeddingSmokeMain.run(args, factory, 1000L).isLeft)
      Files.writeString(
        approvalFile,
        upickle.default.write(grant.copy(executionApproved = false)),
        UTF_8
      )
      assert(LiveEmbeddingSmokeMain.run(args, factory, 1000L) == Left("smoke-approval-required"))
      Files.writeString(
        approvalFile,
        upickle.default.write(grant.copy(operation = "ingest")),
        UTF_8
      )
      assert(LiveEmbeddingSmokeMain.run(args, factory, 1000L) == Left("smoke-approval-required"))
      assert(constructions == 0 && !Files.exists(reportFile))
    }
  }

}
