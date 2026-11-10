package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files
import upickle.default.{read, write, writeJs}

/** Provider-aware live ingest and query configuration: Voyage `voyage-4-lite` at 256 dimensions
  * with the same values for ingest and query smoke, Titan kept selectable, vector consistency and
  * the USD 0.30 embedding token cap. Pure preflight and refusal branches; the fake ports throw if
  * any storage or embedding method is used, and no network or credential provider is created.
  */
class LiveEmbeddingProviderSpec extends AnyFunSuite {
  private val voyage = VoyageEmbeddingClient.Model
  private val titan =
    EmbeddingModel("amazon.titan-embed-text-v2:0", "amazon.titan-embed-text-v2:0", 256)
  private val tables = DynamoTables(
    "fixture-runs",
    "fixture-links",
    "fixture-sessions",
    "fixture-evidence",
    "fixture-artifacts",
    "fixture-metrics",
    "fixture-idempotency"
  )
  private val gate = "Synthetic gate text for provider tests; not an actual approval."
  private val renderer =
    new DocumentRenderer(RenderingConfig("fixture-template", ChunkPolicy(1000, 0)))

  private def live(
      model: EmbeddingModel,
      provider: String = "",
      assumedPrice: Double = 0.02,
      embeddingCap: Double = 0.30
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
    5,
    2,
    2,
    10,
    0.30,
    1e-9,
    1e-9,
    0.0,
    assumedUsdPerMillionEmbeddingTokens = assumedPrice,
    embeddingProvider = provider,
    embeddingCapUsd = embeddingCap
  )
  private val kinds = EmbeddingContracts.indexes.keys.toVector.sorted
  private def items(config: LiveEmbeddingConfig) = kinds.map { kind =>
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
  private def manifestFor(config: LiveEmbeddingConfig) = write(
    EmbeddingManifest(items(config).toVector)
  )
  private def preflight(config: LiveEmbeddingConfig) = {
    val text = write(config)
    val manifest = manifestFor(config)
    val approval = LiveEmbeddingApproval(
      true,
      "fixture-env",
      "provider-run",
      StableIds.sha256Hex(text),
      StableIds.sha256Hex(manifest),
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
    LiveEmbeddingIngestMain.preflight(text, manifest, write(approval), gate, "provider-run", 1000)
  }

  test("the 14C values: voyage-4-lite, version tag voyage-4-lite, dimension 256, same for both") {
    assert(voyage == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    val config = live(voyage)
    assert(config.provider == Right(EmbeddingProvider.Voyage))
    val ingest = config.voyage(EmbeddingInputType.Document)
    val query = config.voyage(EmbeddingInputType.Query)
    assert(
      ingest.inputType == EmbeddingInputType.Document && query.inputType == EmbeddingInputType.Query
    )
    assert(ingest.copy(inputType = EmbeddingInputType.Query) == query)
    assert(preflight(config).isRight)
  }

  test("provider is inferred from the model when empty and explicit when set") {
    assert(live(voyage).provider == Right(EmbeddingProvider.Voyage))
    assert(live(titan).provider == Right(EmbeddingProvider.Bedrock))
    assert(live(voyage, "voyage").provider == Right(EmbeddingProvider.Voyage))
    assert(live(titan, "bedrock").provider == Right(EmbeddingProvider.Bedrock))
    assert(live(voyage, "openai").provider == Left("invalid-embedding-provider"))
  }

  test("titan stays selectable: a bedrock config preflights, with or without the explicit name") {
    assert(preflight(live(titan, "bedrock")).isRight)
    assert(preflight(live(titan)).isRight)
  }

  test("a provider that does not own the model is refused with a typed code at preflight") {
    assert(preflight(live(titan, "voyage")) == Left("embedding-provider-model-mismatch"))
    assert(preflight(live(voyage, "bedrock")) == Left("embedding-provider-model-mismatch"))
    assert(preflight(live(voyage, "nonsense")) == Left("invalid-embedding-provider"))
  }

  test("a configured non-default voyage model preflights and reaches the client config") {
    val other = EmbeddingModel("voyage-configured-x", "v9", 512)
    val config = live(other, "voyage")
    assert(preflight(config).isRight)
    val client = config.voyage(EmbeddingInputType.Document)
    assert(client.model == other && client.inputType == EmbeddingInputType.Document)
    assert(config.voyage(EmbeddingInputType.Query).model == other)
  }

  test("the configured price drives the bound; the default is the VoyageDefaults price") {
    assert(live(voyage).assumedUsdPerMillionEmbeddingTokens == 0.02)
    assert(
      live(voyage).assumedUsdPerMillionEmbeddingTokens ==
        VoyageDefaults.UsdPerMillionTokens.toDouble
    )
    assert(live(voyage).embeddingCapUsd == VoyageDefaults.CapUsd.toDouble)
    // 1,202 tokens: a lower configured price is accepted, 250 USD per million crosses the 0.30 cap.
    assert(preflight(live(voyage, assumedPrice = 0.01)).isRight)
    assert(preflight(live(voyage, assumedPrice = 0.05)).isRight)
    assert(
      preflight(live(voyage, assumedPrice = 250.0)) == Left("live-assumed-cost-or-request-bound")
    )
  }

  test("the embedding cap is token-based: 601 bytes x 2 attempts = 1,202 tokens at USD 0.02/M") {
    // 1,202 tokens cost USD 0.00002404: a cap of 0.00002 refuses, 0.00003 accepts.
    assert(
      preflight(live(voyage, embeddingCap = 0.00002)) ==
        Left("live-assumed-cost-or-request-bound")
    )
    assert(preflight(live(voyage, embeddingCap = 0.00003)).isRight)
    assert(live(voyage).embeddingCapUsd == 0.30)
    assert(LiveEmbeddingIngestMain.embeddingCapExceeded(BigInt(15000000), live(voyage)) == false)
    assert(LiveEmbeddingIngestMain.embeddingCapExceeded(BigInt(15000001), live(voyage)))
    intercept[IllegalArgumentException](live(voyage, embeddingCap = 0.0))
  }

  test("reports name the provider; configs written before this field read as inferred") {
    val config = live(voyage)
    val plan = preflight(config).fold(fail(_), identity)
    val report = LiveEmbeddingIngestMain.report(
      plan,
      EmbeddingIngestReport(0, 0, 0, 0, 0, Map.empty, 0, 0L, Vector.empty, None),
      "provider-run",
      "c",
      "m",
      "a"
    )
    assert(report("embeddingProvider").str == "voyage")
    assert(report("embeddingModelId").str == "voyage-4-lite")
    assert(report("embeddingModelVersion").str == "voyage-4-lite")
    assert(report("dimension").num == 256)
    val old = writeJs(live(titan))
    old.obj.remove("embeddingProvider")
    old.obj.remove("embeddingCapUsd")
    val reread = read[LiveEmbeddingConfig](old.render())
    assert(reread.embeddingProvider.isEmpty && reread.embeddingCapUsd == 0.30)
    assert(reread.provider == Right(EmbeddingProvider.Bedrock))
  }

  private final class FailingPorts(embedderModel: EmbeddingModel) extends LiveEmbeddingPorts {
    def objects: ObjectStore = throw new IllegalStateException("unused")
    def vectors: VectorStore = throw new IllegalStateException("unused")
    def registry: ArtifactRegistry = throw new IllegalStateException("unused")
    def ledger: RunLedger = throw new IllegalStateException("unused")
    val embedder: EmbeddingClient = new DeterministicHashedEmbeddingClient(embedderModel)
    def indexesReady(): StorageResult[Unit] = throw new IllegalStateException("unused")
    var closed = false
    def close(): Unit = closed = true
  }

  test("consistency: ingest embedder must match the stored provider, model, version, dimension") {
    val config = live(voyage)
    val same = new DeterministicHashedEmbeddingClient(voyage)
    assert(LiveEmbeddingIngestMain.consistency(config, same) == Right(()))
    assert(
      LiveEmbeddingIngestMain.consistency(config, new DeterministicHashedEmbeddingClient(titan)) ==
        Left("vector-consistency-provider-mismatch")
    )
    assert(
      LiveEmbeddingIngestMain.consistency(
        config,
        new DeterministicHashedEmbeddingClient(voyage.copy(dimension = 512))
      ) == Left("vector-consistency-dimension-mismatch")
    )
    assert(
      LiveEmbeddingIngestMain.consistency(
        config,
        new DeterministicHashedEmbeddingClient(voyage.copy(version = "voyage-4-lite-b"))
      ) == Left("vector-consistency-version-mismatch")
    )
    assert(
      LiveEmbeddingIngestMain.consistency(live(titan), same) ==
        Left("vector-consistency-provider-mismatch")
    )
  }

  test("run refuses a mismatched embedder with the typed code before any port is used") {
    val config = live(voyage)
    val root = Files.createTempDirectory("provider-consistency-")
    val text = write(config)
    val manifest = manifestFor(config)
    val gp = root.resolve("gate.md")
    Files.writeString(gp, gate, UTF_8)
    val approval = LiveEmbeddingApproval(
      true,
      "fixture-env",
      "provider-run",
      StableIds.sha256Hex(text),
      StableIds.sha256Hex(manifest),
      gp.toString,
      StableIds.sha256Hex(gate),
      5,
      2,
      10,
      0.30,
      true,
      true,
      2000
    )
    Files.writeString(root.resolve("config.json"), text, UTF_8)
    Files.writeString(root.resolve("manifest.json"), manifest, UTF_8)
    Files.writeString(root.resolve("approval.json"), write(approval), UTF_8)
    val ports = new FailingPorts(titan)
    val rp = root.resolve("report.json")
    val result = LiveEmbeddingIngestMain.run(
      Seq(
        "--config",
        root.resolve("config.json").toString,
        "--manifest",
        root.resolve("manifest.json").toString,
        "--approval",
        root.resolve("approval.json").toString,
        "--report",
        rp.toString,
        "--run-id",
        "provider-run"
      ),
      _ => ports,
      1000
    )
    assert(result == Left("vector-consistency-provider-mismatch"))
    assert(ports.closed && !Files.exists(rp))
  }

  // ----- The embedder construction path shared by LiveEmbeddingIngestMain and LiveEmbeddingSmokeMain
  // (both awsPorts call LiveEmbeddingIngestMain.embeddingClientFor). The Bedrock SDK client is an
  // inert proxy that fails any invocation; nothing here reaches AWS, Voyage or the network.

  private val inertBedrock: software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient =
    java.lang.reflect.Proxy
      .newProxyInstance(
        getClass.getClassLoader,
        Array(classOf[software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient]),
        (_, method, _) =>
          if (method.getName == "toString") "inert-bedrock"
          else throw new IllegalStateException("no-call")
      )
      .asInstanceOf[software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient]

  test(
    "awsPorts path: a Titan config with no Voyage key builds a Bedrock client, ingest and query"
  ) {
    Vector(EmbeddingInputType.Document, EmbeddingInputType.Query).foreach { input =>
      var built = 0
      val result = LiveEmbeddingIngestMain.embeddingClientFor(
        live(titan, "bedrock"),
        input,
        None,
        () => { built += 1; inertBedrock }
      )
      val client = result.fold(fail(_), identity)
      assert(client.isInstanceOf[BedrockEmbeddingClient] && client.model == titan)
      assert(client.provider == EmbeddingProvider.Bedrock && built == 1)
    }
    // The provider can also be inferred from the Titan model id.
    assert(
      LiveEmbeddingIngestMain
        .embeddingClientFor(live(titan), EmbeddingInputType.Query, None, () => inertBedrock)
        .toOption
        .exists(_.isInstanceOf[BedrockEmbeddingClient])
    )
  }

  test(
    "awsPorts path: a Voyage config builds a Voyage client and never builds the Bedrock client"
  ) {
    val dim2048 = voyage.copy(dimension = 2048) // a Voyage size the Bedrock config rejects
    Vector(voyage, dim2048).foreach { model =>
      Vector(EmbeddingInputType.Document, EmbeddingInputType.Query).foreach { input =>
        val result = LiveEmbeddingIngestMain.embeddingClientFor(
          live(model),
          input,
          Some("synthetic-placeholder-key"),
          () => throw new IllegalStateException("bedrock-must-not-be-built")
        )
        val client = result.fold(fail(_), identity)
        assert(client.isInstanceOf[VoyageEmbeddingClient] && client.model == model)
        assert(client.provider == EmbeddingProvider.Voyage)
      }
    }
  }

  test("awsPorts path: Voyage without a key is a closed code and the Bedrock client is untouched") {
    val result = LiveEmbeddingIngestMain.embeddingClientFor(
      live(voyage),
      EmbeddingInputType.Query,
      None,
      () => throw new IllegalStateException("bedrock-must-not-be-built")
    )
    assert(result.left.toOption.contains("voyage-api-key-missing"))
    assert(
      LiveEmbeddingIngestMain
        .embeddingClientFor(
          live(voyage, "nonsense"),
          EmbeddingInputType.Query,
          None,
          () => inertBedrock
        )
        .left
        .toOption
        .contains("invalid-embedding-provider")
    )
  }
}
