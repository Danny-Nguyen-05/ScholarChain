package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient
import java.nio.charset.StandardCharsets.UTF_8

/** Provider switches and vector consistency. No client is called: the Bedrock SDK client is an
  * inert proxy that fails any invocation, and no HTTP server is started.
  */
class ProviderSelectionSpec extends AnyFunSuite {
  private val secret = "sk-synthetic-placeholder-key-two"
  private def resource(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    try new String(stream.readAllBytes(), UTF_8)
    finally stream.close()
  }
  private val baseConfig =
    RuntimeConfigLoader.fromJson(resource("/scholarchain.runtime-config.v1.json")).toOption.get
  private val haikuConfig = SynthesisClients.runtimeConfigFor(
    SynthesisProvider.Anthropic,
    baseConfig,
    AnthropicDefaults.ModelId
  )
  private def inertBedrock: BedrockRuntimeClient =
    java.lang.reflect.Proxy
      .newProxyInstance(
        getClass.getClassLoader,
        Array(classOf[BedrockRuntimeClient]),
        (_, method, _) =>
          if (method.getName == "toString") "inert-bedrock"
          else throw new IllegalStateException("no-call")
      )
      .asInstanceOf[BedrockRuntimeClient]
  private val bedrockThunkMustNotRun: () => BedrockRuntimeClient =
    () => throw new IllegalStateException("bedrock-must-not-be-built")

  test("synthesis provider defaults to anthropic and parses both names") {
    assert(SynthesisProvider.EnvName == "SCHOLARCHAIN_SYNTHESIS_PROVIDER")
    assert(SynthesisProvider.parse(None) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some("")) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some("  ")) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some("anthropic")) == Right(SynthesisProvider.Anthropic))
    assert(SynthesisProvider.parse(Some(" bedrock ")) == Right(SynthesisProvider.Bedrock))
    assert(
      SynthesisProvider.Anthropic.wire == "anthropic" && SynthesisProvider.Bedrock.wire == "bedrock"
    )
  }

  test("embedding provider defaults to voyage and parses both names") {
    assert(EmbeddingProvider.EnvName == "SCHOLARCHAIN_EMBEDDING_PROVIDER")
    assert(EmbeddingProvider.parse(None) == Right(EmbeddingProvider.Voyage))
    assert(EmbeddingProvider.parse(Some("")) == Right(EmbeddingProvider.Voyage))
    assert(EmbeddingProvider.parse(Some("voyage")) == Right(EmbeddingProvider.Voyage))
    assert(EmbeddingProvider.parse(Some("bedrock")) == Right(EmbeddingProvider.Bedrock))
  }

  test("an unknown provider name is a closed code that does not echo the value") {
    assert(SynthesisProvider.parse(Some("openai")) == Left("invalid-synthesis-provider"))
    assert(SynthesisProvider.parse(Some("Anthropic")) == Left("invalid-synthesis-provider"))
    assert(EmbeddingProvider.parse(Some(secret)) == Left("invalid-embedding-provider"))
    assert(EmbeddingProvider.parse(Some("titan")) == Left("invalid-embedding-provider"))
  }

  test("runtimeConfigFor takes the configured model id; it forces no constant") {
    assert(baseConfig.model.modelId != "claude-haiku-5-5")
    assert(haikuConfig.model.modelId == "claude-haiku-5-5")
    assert(haikuConfig.model.modelVersion == baseConfig.model.modelVersion)
    val other = SynthesisClients
      .runtimeConfigFor(SynthesisProvider.Anthropic, baseConfig, "claude-configured-y")
    assert(other.model.modelId == "claude-configured-y")
    val bedrock = SynthesisClients
      .runtimeConfigFor(SynthesisProvider.Bedrock, baseConfig, "configured-bedrock-model")
    assert(bedrock.model.modelId == "configured-bedrock-model")
    // Without a model id the config is returned as configured.
    assert(SynthesisClients.runtimeConfigFor(SynthesisProvider.Anthropic, baseConfig) == baseConfig)
  }

  test("anthropic synthesis accepts any configured model id and settings override defaults") {
    val other = haikuConfig.copy(model = haikuConfig.model.copy(modelId = "claude-configured-y"))
    Vector(haikuConfig, other, baseConfig).foreach { c =>
      assert(
        SynthesisClients
          .create(SynthesisProvider.Anthropic, c, Some(secret), bedrockThunkMustNotRun)
          .toOption
          .exists(_.isInstanceOf[AnthropicMessagesLlmClient])
      )
    }
    assert(
      SynthesisClients
        .create(
          SynthesisProvider.Anthropic,
          haikuConfig,
          Some(secret),
          bedrockThunkMustNotRun,
          AnthropicSettings(baseUri = "https://proxy.example.test")
        )
        .isRight
    )
  }

  test("anthropic synthesis builds an Anthropic client without touching Bedrock") {
    val built = SynthesisClients
      .create(SynthesisProvider.Anthropic, haikuConfig, Some(secret), bedrockThunkMustNotRun)
    assert(built.toOption.exists(_.isInstanceOf[AnthropicMessagesLlmClient]))
    assert(SynthesisClients.AnthropicKeyEnvName == "SCHOLARCHAIN_ANTHROPIC_API_KEY")
  }

  test("anthropic synthesis refuses a missing, blank or unsafe key with closed codes, no echo") {
    def create(key: Option[String]) = SynthesisClients
      .create(SynthesisProvider.Anthropic, haikuConfig, key, bedrockThunkMustNotRun)
    assert(create(None) == Left("anthropic-api-key-missing"))
    assert(create(Some("")) == Left("anthropic-api-key-missing"))
    assert(create(Some("has space " + secret)) == Left("invalid-anthropic-api-key"))
    assert(create(Some("has space " + secret)).left.exists(!_.contains(secret)))
    assert(
      SynthesisClients.create(
        SynthesisProvider.Anthropic,
        haikuConfig,
        Some(secret),
        bedrockThunkMustNotRun,
        AnthropicSettings(baseUri = "http://example.com")
      ) == Left("invalid-anthropic-base-uri")
    )
  }

  test("bedrock synthesis builds the Converse client and needs no Anthropic key") {
    val built =
      SynthesisClients.create(SynthesisProvider.Bedrock, baseConfig, None, () => inertBedrock)
    assert(built.toOption.exists(_.isInstanceOf[BedrockConverseLlmClient]))
  }

  test("synthesis refuses an invalid runtime config before building any client") {
    val bad = baseConfig.copy(model = baseConfig.model.copy(temperature = 5.0))
    assert(
      SynthesisClients.create(SynthesisProvider.Bedrock, bad, None, bedrockThunkMustNotRun) ==
        Left("invalid-runtime-config")
    )
  }

  private val titan =
    EmbeddingModel("amazon.titan-embed-text-v2:0", "amazon.titan-embed-text-v2:0", 256)
  private val bedrockConfig = BedrockEmbeddingConfig(titan, "us-east-2")

  test("voyage embeddings build document and query clients with the default model, no Bedrock") {
    val doc = EmbeddingClientFactory.create(
      EmbeddingProvider.Voyage,
      EmbeddingInputType.Document,
      Some(secret),
      bedrockThunkMustNotRun,
      None
    )
    val query = EmbeddingClientFactory.create(
      EmbeddingProvider.Voyage,
      EmbeddingInputType.Query,
      Some(secret),
      bedrockThunkMustNotRun,
      None
    )
    Vector(doc, query).foreach { built =>
      val client = built.fold(fail(_), identity)
      assert(client.isInstanceOf[VoyageEmbeddingClient])
      assert(client.provider == EmbeddingProvider.Voyage)
      assert(client.model == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    }
    assert(EmbeddingClientFactory.VoyageKeyEnvName == "SCHOLARCHAIN_VOYAGE_API_KEY")
  }

  test("voyage embeddings refuse a missing or unsafe key with closed codes, no echo") {
    def create(key: Option[String]) = EmbeddingClientFactory.create(
      EmbeddingProvider.Voyage,
      EmbeddingInputType.Query,
      key,
      bedrockThunkMustNotRun,
      None
    )
    assert(create(None).left.toOption == Some("voyage-api-key-missing"))
    assert(create(Some("")).left.toOption == Some("voyage-api-key-missing"))
    assert(create(Some("bad key " + secret)).left.toOption == Some("invalid-voyage-api-key"))
  }

  test("bedrock embeddings stay selectable with Titan V2 and need no Voyage key") {
    val built = EmbeddingClientFactory.create(
      EmbeddingProvider.Bedrock,
      EmbeddingInputType.Document,
      None,
      () => inertBedrock,
      Some(bedrockConfig)
    )
    val client = built.fold(fail(_), identity)
    assert(client.isInstanceOf[BedrockEmbeddingClient])
    assert(client.provider == EmbeddingProvider.Bedrock && client.model == titan)
    assert(
      EmbeddingClientFactory
        .create(EmbeddingProvider.Bedrock, EmbeddingInputType.Query, None, () => inertBedrock, None)
        .left
        .toOption == Some("bedrock-embedding-config-missing")
    )
    val voyageUnderBedrock = BedrockEmbeddingConfig(VoyageEmbeddingClient.Model, "us-east-2")
    assert(
      EmbeddingClientFactory
        .create(
          EmbeddingProvider.Bedrock,
          EmbeddingInputType.Query,
          None,
          () => inertBedrock,
          Some(voyageUnderBedrock)
        )
        .left
        .toOption == Some("embedding-provider-model-mismatch")
    )
  }

  test("provider pricing: both list USD 0.02 per million, cap USD 0.30 is 15,000,000 tokens") {
    assert(EmbeddingPricing.usdPerMillionTokens(EmbeddingProvider.Voyage) == BigDecimal("0.02"))
    assert(EmbeddingPricing.usdPerMillionTokens(EmbeddingProvider.Bedrock) == BigDecimal("0.02"))
    assert(EmbeddingPricing.defaultCapUsd(EmbeddingProvider.Voyage) == BigDecimal("0.30"))
    assert(EmbeddingPricing.defaultCapUsd(EmbeddingProvider.Bedrock) == BigDecimal("0.30"))
    // Configured values replace the defaults: USD 1 at USD 0.5 per million is 2,000,000 tokens.
    val configured = EmbeddingPricing.newCounter(
      EmbeddingProvider.Voyage,
      Some(BigDecimal("1")),
      Some(BigDecimal("0.5"))
    )
    assert(configured.capTokens == BigInt(2000000))
    Vector(EmbeddingProvider.Voyage, EmbeddingProvider.Bedrock).foreach { p =>
      assert(EmbeddingPricing.newCounter(p).capTokens == BigInt(15000000))
    }
  }

  test("provider-model family: voyage-* is Voyage, anything else is Bedrock; ids are configured") {
    val voyageOther = EmbeddingModel("voyage-configured-x", "v9", 512)
    assert(EmbeddingProviders.infer(VoyageEmbeddingClient.Model) == EmbeddingProvider.Voyage)
    assert(EmbeddingProviders.infer(titan) == EmbeddingProvider.Bedrock)
    assert(EmbeddingProviders.infer(voyageOther) == EmbeddingProvider.Voyage)
    assert(
      EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Voyage, VoyageEmbeddingClient.Model)
    )
    assert(EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Voyage, voyageOther))
    assert(!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Voyage, titan))
    assert(EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Bedrock, titan))
    assert(
      !EmbeddingProviders.modelMatchesProvider(
        EmbeddingProvider.Bedrock,
        VoyageEmbeddingClient.Model
      )
    )
    assert(!EmbeddingProviders.modelMatchesProvider(EmbeddingProvider.Bedrock, voyageOther))
  }

  test("the factory passes a configured Voyage model, endpoint and limits to the client") {
    val model = EmbeddingModel("voyage-configured-x", "v9", 512)
    val built = EmbeddingClientFactory
      .create(
        EmbeddingProvider.Voyage,
        EmbeddingInputType.Query,
        Some(secret),
        bedrockThunkMustNotRun,
        None,
        voyageConfig = Some(VoyageEmbeddingConfig(EmbeddingInputType.Document, model = model))
      )
      .fold(fail(_), identity)
    assert(built.model == model)
    // The purpose argument wins over the template's input type, so one config serves both.
    assert(
      EmbeddingClientFactory
        .create(
          EmbeddingProvider.Voyage,
          EmbeddingInputType.Query,
          Some(secret),
          bedrockThunkMustNotRun,
          None,
          voyageConfig =
            Some(VoyageEmbeddingConfig(EmbeddingInputType.Document, baseUri = "http://example.com"))
        )
        .left
        .toOption == Some("invalid-voyage-base-uri")
    )
  }

  test("vector consistency refuses a provider, model, version or dimension mismatch, typed") {
    val v = EmbeddingProvider.Voyage
    val m = VoyageEmbeddingClient.Model
    assert(VectorConsistency.check(v, m, v, m) == Right(()))
    assert(
      VectorConsistency.check(v, m, EmbeddingProvider.Bedrock, m) == Left(
        VectorConsistencyError("provider")
      )
    )
    assert(
      VectorConsistency.check(v, m, v, m.copy(modelId = "voyage-4")) == Left(
        VectorConsistencyError("model")
      )
    )
    assert(
      VectorConsistency.check(v, m, v, m.copy(version = "voyage-4-lite-v2")) == Left(
        VectorConsistencyError("version")
      )
    )
    assert(
      VectorConsistency.check(v, m, v, m.copy(dimension = 1024)) == Left(
        VectorConsistencyError("dimension")
      )
    )
    assert(VectorConsistencyError("dimension").code == "vector-consistency-dimension-mismatch")
    assert(VectorConsistencyError("provider").code == "vector-consistency-provider-mismatch")
  }

  test("vector consistency on a client: stored Titan vectors versus a Voyage query client") {
    val voyage = new VoyageEmbeddingClient(
      VoyageApiKey.fromValue(secret).toOption.get,
      VoyageEmbeddingConfig(EmbeddingInputType.Query)
    )
    assert(
      VectorConsistency.checkClient(
        EmbeddingProvider.Voyage,
        VoyageEmbeddingClient.Model,
        voyage
      ) == Right(())
    )
    assert(
      VectorConsistency.checkClient(EmbeddingProvider.Bedrock, titan, voyage) ==
        Left(VectorConsistencyError("provider"))
    )
    // A test double that is not a provider client has its provider inferred from the model id.
    val hashed = new DeterministicHashedEmbeddingClient(EmbeddingModel("offline-fixture", "v1", 8))
    assert(
      VectorConsistency.checkClient(EmbeddingProvider.Bedrock, hashed.model, hashed) == Right(())
    )
    assert(
      VectorConsistency.checkClient(
        EmbeddingProvider.Bedrock,
        hashed.model.copy(dimension = 16),
        hashed
      ) ==
        Left(VectorConsistencyError("dimension"))
    )
  }
}
