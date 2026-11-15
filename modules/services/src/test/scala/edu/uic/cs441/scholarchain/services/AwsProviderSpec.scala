package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.{
  EmbeddingClient,
  EmbeddingFailure,
  EmbeddingModel,
  EmbeddingResult,
  RuntimeConfig
}
import edu.uic.cs441.scholarchain.rag.{
  AnthropicDefaults,
  AnthropicMessagesLlmClient,
  EmbeddingProvider,
  LlmClient,
  LlmResult,
  StructuredLlmRequest,
  SynthesisProvider,
  VoyageDefaults,
  VoyageEmbeddingClient
}
import java.io.{ByteArrayOutputStream, PrintStream}
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.auth.credentials.{
  AwsBasicCredentials,
  AwsCredentialsProvider,
  StaticCredentialsProvider
}
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient

/** Provider selection: Anthropic and Voyage by default, Bedrock when chosen. Everything here is
  * offline; the provider clients are counting stand-ins and no key is a real credential.
  */
class AwsProviderSpec extends AnyFunSuite {
  import AwsTestEnv.*

  private val providerVariables = Set(
    "SCHOLARCHAIN_SYNTHESIS_PROVIDER",
    "SCHOLARCHAIN_EMBEDDING_PROVIDER",
    "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL",
    "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION",
    "SCHOLARCHAIN_EMBEDDING_DIMENSION",
    "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL",
    "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION"
  )
  private val anthropicName = "SCHOLARCHAIN_ANTHROPIC_API_KEY"
  private val voyageName = "SCHOLARCHAIN_VOYAGE_API_KEY"
  private val roles = Vector("query-api", "graph-service", "semantic-service", "embedding-worker")
  private val fast =
    Map("SCHOLARCHAIN_READINESS_CACHE_MS" -> "1", "SCHOLARCHAIN_READINESS_TIMEOUT_MS" -> "500")
  private val keyedRoles = Vector(
    ("query-api", anthropicName),
    ("semantic-service", voyageName),
    ("embedding-worker", voyageName)
  )
  private val bedrockAnthropic = Map(
    "SCHOLARCHAIN_SYNTHESIS_PROVIDER" -> "anthropic",
    "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL" -> "claude-haiku-5-5",
    "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION" -> "claude-haiku-5-5",
    anthropicName -> anthropicKeyValue
  )

  /** The default configuration: no provider variable, no model variable, only the keys. */
  private def defaults(role: String): Map[String, String] = {
    val base = forRole(role) -- providerVariables
    role match {
      case "query-api"                             => base + (anthropicName -> anthropicKeyValue)
      case "semantic-service" | "embedding-worker" => base + (voyageName -> voyageKeyValue)
      case _                                       => base
    }
  }
  private def queryConfig(env: Map[String, String]) =
    parse("query-api", env).toOption.get.asInstanceOf[QueryRoleConfig]
  private def semanticConfig(env: Map[String, String]) =
    parse("semantic-service", env).toOption.get.asInstanceOf[SemanticRoleConfig]
  private def workerConfig(env: Map[String, String]) =
    parse("embedding-worker", env).toOption.get.asInstanceOf[WorkerRoleConfig]

  private def captured[A](body: => A): (A, String) = {
    val original = System.err
    val buffer = new ByteArrayOutputStream
    System.setErr(new PrintStream(buffer, true, UTF_8))
    try { val result = body; (result, buffer.toString(UTF_8)) }
    finally System.setErr(original)
  }

  // ---- configuration --------------------------------------------------------------------

  test("with no provider variable the defaults are Anthropic and Voyage with the contract models") {
    roles.foreach(role => assert(parse(role, defaults(role)).isRight, role))
    val q = queryConfig(defaults("query-api"))
    assert(q.synthesisProvider == SynthesisProvider.Anthropic)
    assert(q.embeddingProvider == EmbeddingProvider.Voyage)
    assert(
      q.synthesisModelId == AnthropicDefaults.ModelId && q.synthesisModelVersion == AnthropicDefaults.ModelId
    )
    assert(q.embedding == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    assert(q.anthropicApiKey.map(_.value).contains(anthropicKeyValue))
    val s = semanticConfig(defaults("semantic-service"))
    assert(s.embeddingProvider == EmbeddingProvider.Voyage)
    assert(s.embedding == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    assert(s.voyageApiKey.map(_.value).contains(voyageKeyValue))
    val w = workerConfig(defaults("embedding-worker"))
    assert(w.embeddingProvider == EmbeddingProvider.Voyage && w.embedding == s.embedding)
    assert(w.voyageApiKey.map(_.value).contains(voyageKeyValue))
  }

  test("explicit provider names equal the defaults and other names are refused by variable") {
    val explicit = defaults("query-api") ++ Map(
      "SCHOLARCHAIN_SYNTHESIS_PROVIDER" -> "anthropic",
      "SCHOLARCHAIN_EMBEDDING_PROVIDER" -> "voyage"
    )
    assert(queryConfig(explicit).synthesisProvider == SynthesisProvider.Anthropic)
    for (
      (role, name) <- Vector(
        ("query-api", "SCHOLARCHAIN_SYNTHESIS_PROVIDER"),
        ("query-api", "SCHOLARCHAIN_EMBEDDING_PROVIDER"),
        ("semantic-service", "SCHOLARCHAIN_EMBEDDING_PROVIDER"),
        ("embedding-worker", "SCHOLARCHAIN_EMBEDDING_PROVIDER")
      );
      value <- Vector("openai", "Anthropic", "VOYAGE", "titan-leaky-value")
    ) {
      val result = parse(role, defaults(role).updated(name, value))
      assert(result == Left("invalid-aws-configuration:" + name), s"$role $name=$value")
    }
  }

  test("a selected provider requires its key by name; an unselected provider needs none") {
    for ((role, name) <- keyedRoles) {
      assert(parse(role, defaults(role) - name) == Left("missing-aws-configuration:" + name))
      assert(
        parse(role, defaults(role).updated(name, "   ")) == Left(
          "missing-aws-configuration:" + name
        )
      )
    }
    // The graph service uses neither provider, and each role reads only its own key.
    assert(parse("graph-service", defaults("graph-service")).isRight)
    assert(parse("query-api", defaults("query-api") - voyageName).isRight)
    assert(parse("semantic-service", defaults("semantic-service") - anthropicName).isRight)
    // Bedrock needs no provider key.
    assert(queryConfig(forRole("query-api")).anthropicApiKey.isEmpty)
    assert(semanticConfig(forRole("semantic-service")).voyageApiKey.isEmpty)
    assert(workerConfig(forRole("embedding-worker")).voyageApiKey.isEmpty)
    // A key is ignored, never read, when its provider is not selected.
    val ignored = queryConfig(forRole("query-api") + (anthropicName -> anthropicKeyValue))
    assert(
      ignored.anthropicApiKey.isEmpty && ignored.synthesisProvider == SynthesisProvider.Bedrock
    )
    val ignoredVoyage = semanticConfig(forRole("semantic-service") + (voyageName -> voyageKeyValue))
    assert(ignoredVoyage.voyageApiKey.isEmpty)
  }

  test("a malformed key is refused by variable name and the value is never echoed") {
    val bad = Vector(
      "short",
      "has a space inside-0123",
      "tab\tinside-0123456789",
      "newline\ninside-0123456",
      "non-ascii-é-0123456789",
      "x" * 513
    )
    for ((role, name) <- keyedRoles; value <- bad) {
      val result = parse(role, defaults(role).updated(name, value))
      assert(result == Left("invalid-aws-configuration:" + name), s"$role $name")
      assert(!result.left.toOption.get.contains(value.trim))
    }
  }

  test("model ids, version tags and the Voyage dimension are configuration with rag defaults") {
    // Unset: the rag-owned defaults apply (rule 6.7 keeps their rationale in rag).
    val q = queryConfig(defaults("query-api"))
    assert(q.synthesisModelId == AnthropicDefaults.ModelId)
    assert(q.synthesisModelVersion == AnthropicDefaults.ModelId)
    assert(q.embedding == VoyageDefaults.Model)
    // Set: any well-formed value is taken as configured, never compared with a constant.
    val configured = defaults("query-api") ++ Map(
      "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL" -> "claude-test-model-9",
      "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION" -> "claude-test-model-9-r2",
      "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL" -> "voyage-test-model",
      "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION" -> "voyage-test-model-r2",
      "SCHOLARCHAIN_EMBEDDING_DIMENSION" -> "512"
    )
    val c = queryConfig(configured)
    assert(c.synthesisModelId == "claude-test-model-9")
    assert(c.synthesisModelVersion == "claude-test-model-9-r2")
    assert(c.embedding == EmbeddingModel("voyage-test-model", "voyage-test-model-r2", 512))
    // Every dimension in the Voyage supported set is accepted for both embedding roles.
    for (
      role <- Vector("semantic-service", "embedding-worker");
      d <- VoyageDefaults.SupportedDimensions
    ) {
      val env = defaults(role).updated("SCHOLARCHAIN_EMBEDDING_DIMENSION", d.toString)
      assert(parse(role, env).isRight, s"$role $d")
    }
    // An unsupported dimension is refused by name, as are malformed ids and non-Voyage families.
    for (
      (role, name, value) <- Vector(
        ("semantic-service", "SCHOLARCHAIN_EMBEDDING_DIMENSION", "300"),
        ("embedding-worker", "SCHOLARCHAIN_EMBEDDING_DIMENSION", "4096"),
        ("query-api", "SCHOLARCHAIN_EMBEDDING_DIMENSION", "0"),
        ("semantic-service", "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0"),
        ("semantic-service", "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", "bad id with space"),
        ("semantic-service", "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION", "bad version"),
        ("query-api", "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL", "bad id with space"),
        ("query-api", "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION", "bad version")
      )
    ) {
      assert(
        parse(role, defaults(role).updated(name, value)) ==
          Left("invalid-aws-configuration:" + name),
        s"$role $name=$value"
      )
    }
  }

  test("Bedrock values keep their previous validation, including the 256/512/1024 dimensions") {
    val q = queryConfig(forRole("query-api"))
    assert(q.synthesisProvider == SynthesisProvider.Bedrock && q.synthesisModelId == profile)
    assert(q.synthesisModelVersion == foundation)
    assert(q.embeddingProvider == EmbeddingProvider.Bedrock)
    val wider = forRole("semantic-service").updated("SCHOLARCHAIN_EMBEDDING_DIMENSION", "512")
    assert(semanticConfig(wider).embedding.dimension == 512)
    val odd = forRole("semantic-service").updated("SCHOLARCHAIN_EMBEDDING_DIMENSION", "300")
    assert(
      parse("semantic-service", odd) == Left(
        "invalid-aws-configuration:SCHOLARCHAIN_EMBEDDING_DIMENSION"
      )
    )
    // Providers are independent: Anthropic synthesis can run with Bedrock embeddings.
    val m = queryConfig(forRole("query-api") ++ bedrockAnthropic)
    assert(m.synthesisProvider == SynthesisProvider.Anthropic)
    assert(m.embeddingProvider == EmbeddingProvider.Bedrock)
    assert(m.embedding.modelId.startsWith("amazon."))
  }

  test("the runtime contract carries the Anthropic model while the packaged temperature stays") {
    val runtime = AwsComposition.runtimeConfig(queryConfig(defaults("query-api"))).toOption.get
    assert(runtime.model.modelId == "claude-haiku-5-5")
    assert(runtime.model.modelVersion == "claude-haiku-5-5")
    // The rag client must omit the temperature for this model; the config value is not changed here.
    assert(runtime.model.temperature == 0.0)
  }

  // ---- key hygiene ----------------------------------------------------------------------

  test("no key value appears in any role configuration rendering") {
    val keys = Vector(anthropicKeyValue, voyageKeyValue)
    val q = queryConfig(defaults("query-api"))
    val s = semanticConfig(defaults("semantic-service"))
    val renderings = Vector(
      q.toString,
      s.toString,
      workerConfig(defaults("embedding-worker")).toString,
      q.anthropicApiKey.get.toString,
      s"${s.voyageApiKey}"
    )
    renderings.foreach(text => keys.foreach(k => assert(!text.contains(k), text)))
    assert(renderings.take(3).forall(_.contains("<redacted>")))
  }

  test("a refusal from the key checks is a closed code even when the value looks like a secret") {
    val leaky = "sk-ant-api03-LEAKY-SECRET-VALUE with space"
    val refused = parse("query-api", defaults("query-api").updated(anthropicName, leaky))
    assert(refused == Left("invalid-aws-configuration:" + anthropicName))
    val (result, err) = captured(
      ServiceBootstrap.launch(
        "semantic-service",
        defaults("semantic-service").updated(voyageName, leaky),
        new FakeFactory
      )
    )
    assert(result.left.toOption.contains(2))
    assert(err.trim == "invalid-aws-configuration:" + voyageName && !err.contains("LEAKY"))
    val (missing, missingErr) = captured(
      ServiceBootstrap.launch("query-api", defaults("query-api") - anthropicName, new FakeFactory)
    )
    assert(missing.left.toOption.contains(2))
    assert(missingErr.trim == "missing-aws-configuration:" + anthropicName)
  }

  // ---- ports ----------------------------------------------------------------------------

  private final class CountingLlm extends LlmClient {
    val calls = new AtomicInteger
    def complete(request: StructuredLlmRequest): LlmResult = {
      calls.incrementAndGet(); LlmResult.Failure("counting-no-output")
    }
  }
  private final class CountingEmbedder(val model: EmbeddingModel) extends EmbeddingClient {
    val calls = new AtomicInteger
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      calls.incrementAndGet(); texts.map(_ => EmbeddingFailure("counting-none", false, model, 1))
    }
  }
  private final class RecordingProviders(
      refuse: Option[String] = None,
      explode: Option[String] = None
  ) extends ProviderClients {
    val llm = new CountingLlm
    val keysSeen = new ConcurrentLinkedQueue[String]()
    val models = new ConcurrentLinkedQueue[EmbeddingModel]()
    val runtimes = new ConcurrentLinkedQueue[RuntimeConfig]()
    val purposes = new ConcurrentLinkedQueue[EmbeddingPurpose]()
    @volatile var embedder: Option[CountingEmbedder] = None
    private def gate[A](key: Secret)(make: => A): Either[String, A] = {
      keysSeen.add(key.value)
      explode.foreach(message => throw new IllegalStateException(message))
      refuse.toLeft(make)
    }
    def anthropic(apiKey: Secret, runtime: RuntimeConfig): Either[String, LlmClient] =
      gate(apiKey) { runtimes.add(runtime); llm }
    def voyage(
        apiKey: Secret,
        model: EmbeddingModel,
        purpose: EmbeddingPurpose
    ): Either[String, EmbeddingClient] =
      gate(apiKey) {
        models.add(model)
        purposes.add(purpose)
        val e = new CountingEmbedder(model)
        embedder = Some(e)
        e
      }
  }
  private final class BedrockCount {
    val built = new AtomicInteger
    val build
        : (Region, AwsCredentialsProvider, ClientOverrideConfiguration) => BedrockRuntimeClient =
      (region, creds, overrides) => {
        built.incrementAndGet()
        AwsSdkPortFactory.defaultBedrock(region, creds, overrides)
      }
  }
  private val creds = () => StaticCredentialsProvider.create(AwsBasicCredentials.create("t", "t"))
  private val unusedGraphReader = new GraphReaderProvider {
    def open(
        endpoint: java.net.URI,
        region: String,
        credentials: AwsCredentialsProvider,
        timeoutMs: Long
    ) = Right(OpenedGraphReader(new FakeReader(new Dependencies), () => ()))
  }
  private def factory(providers: ProviderClients, bedrock: BedrockCount) =
    new AwsSdkPortFactory(creds, unusedGraphReader, providers, bedrock.build)

  test("the Anthropic and Voyage clients are built from the key and no Bedrock client exists") {
    val providers = new RecordingProviders
    val bedrock = new BedrockCount
    val f = factory(providers, bedrock)
    val q = queryConfig(defaults("query-api"))
    val runtime = AwsComposition.runtimeConfig(q).toOption.get
    val queryPorts = f.query(q, runtime).toOption.get
    assert(queryPorts.llm eq providers.llm)
    assert(providers.runtimes.peek() == runtime)
    val semanticPorts = f.semantic(semanticConfig(defaults("semantic-service"))).toOption.get
    assert(semanticPorts.embedding eq providers.embedder.get)
    val workerPorts = f.worker(workerConfig(defaults("embedding-worker"))).toOption.get
    assert(workerPorts.embedder eq providers.embedder.get)
    assert(
      providers.keysSeen.toArray.toVector ==
        Vector(anthropicKeyValue, voyageKeyValue, voyageKeyValue)
    )
    // The semantic service searches with queries; the worker stores documents.
    assert(
      providers.purposes.toArray.toVector == Vector(
        EmbeddingPurpose.Query,
        EmbeddingPurpose.Document
      )
    )
    assert(providers.models.peek() == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    assert(bedrock.built.get == 0, "no Bedrock client is built for the external providers")
    // Building the ports made no paid call.
    assert(providers.llm.calls.get == 0 && providers.embedder.get.calls.get == 0)
    Vector[PortBundle](queryPorts, semanticPorts, workerPorts).foreach(_.close())
  }

  test("Bedrock clients are built only for a selected Bedrock provider") {
    val providers = new RecordingProviders
    val bedrock = new BedrockCount
    val f = factory(providers, bedrock)
    val q = queryConfig(forRole("query-api"))
    val a = f.query(q, AwsComposition.runtimeConfig(q).toOption.get).toOption.get
    assert(bedrock.built.get == 1)
    val b = f.semantic(semanticConfig(forRole("semantic-service"))).toOption.get
    assert(bedrock.built.get == 2)
    val c = f.worker(workerConfig(forRole("embedding-worker"))).toOption.get
    assert(bedrock.built.get == 3)
    assert(providers.keysSeen.isEmpty, "no external client or key is used under Bedrock")
    // Mixed: Anthropic synthesis with Bedrock embeddings builds no synthesis Bedrock client.
    val mq = queryConfig(forRole("query-api") ++ bedrockAnthropic)
    val d = f.query(mq, AwsComposition.runtimeConfig(mq).toOption.get).toOption.get
    assert(bedrock.built.get == 3 && providers.keysSeen.size == 1)
    Vector[PortBundle](a, b, c, d).foreach(_.close())
  }

  test("a provider refusal or exception becomes a closed code and no key is leaked") {
    val refusing = new RecordingProviders(refuse = Some("provider-says-no"))
    val exploding =
      new RecordingProviders(explode = Some("boom " + anthropicKeyValue + " " + voyageKeyValue))
    val q = queryConfig(defaults("query-api"))
    val runtime = AwsComposition.runtimeConfig(q).toOption.get
    val s = semanticConfig(defaults("semantic-service"))
    val w = workerConfig(defaults("embedding-worker"))
    val bedrock = new BedrockCount
    val refused = factory(refusing, bedrock)
    assert(refused.query(q, runtime).left.toOption.contains("provider-says-no"))
    assert(refused.semantic(s).left.toOption.contains("provider-says-no"))
    assert(refused.worker(w).left.toOption.contains("provider-says-no"))
    val f = factory(exploding, bedrock)
    val results =
      Vector(f.query(q, runtime).map(_ => ()), f.semantic(s).map(_ => ()), f.worker(w).map(_ => ()))
    results.foreach(r => assert(r == Left("provider-client-failed"), r))
    assert(bedrock.built.get == 0)
    // The composition and the launcher add nothing either.
    val env = defaults("semantic-service") ++ fast
    val built =
      AwsComposition.build(service(env), parse("semantic-service", env).toOption.get, env, f)
    assert(built.left.toOption.contains("provider-client-failed"))
    val (launched, err) =
      captured(ServiceBootstrap.launch("query-api", defaults("query-api") ++ fast, f))
    assert(launched.left.toOption.contains(2) && err.trim == "provider-client-failed")
    assert(!err.contains(anthropicKeyValue) && !err.contains("boom"))
  }

  test("the unwired double refuses by closed code without any call") {
    val f = new AwsSdkPortFactory(creds, unusedGraphReader, UnwiredProviderClients)
    val q = queryConfig(defaults("query-api"))
    val runtime = AwsComposition.runtimeConfig(q).toOption.get
    val code = Some(UnwiredProviderClients.unavailable)
    assert(f.query(q, runtime).left.toOption == code)
    assert(f.semantic(semanticConfig(defaults("semantic-service"))).left.toOption == code)
    assert(f.worker(workerConfig(defaults("embedding-worker"))).left.toOption == code)
  }

  test("the default factory builds the real rag clients offline and never a Bedrock client") {
    val bedrock = new BedrockCount
    val rag = new RagProviderClients()
    val f = new AwsSdkPortFactory(creds, unusedGraphReader, rag, bedrock.build)
    val q = queryConfig(defaults("query-api"))
    val runtime = AwsComposition.runtimeConfig(q).toOption.get
    val queryPorts = f.query(q, runtime).toOption.get
    assert(queryPorts.llm.isInstanceOf[AnthropicMessagesLlmClient])
    val semanticPorts = f.semantic(semanticConfig(defaults("semantic-service"))).toOption.get
    val workerPorts = f.worker(workerConfig(defaults("embedding-worker"))).toOption.get
    assert(semanticPorts.embedding.isInstanceOf[VoyageEmbeddingClient])
    assert(workerPorts.embedder.isInstanceOf[VoyageEmbeddingClient])
    assert(semanticPorts.embedding.model == EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256))
    assert(bedrock.built.get == 0, "the external providers build no Bedrock client")
    val used = Vector(queryPorts.llm, semanticPorts.embedding, workerPorts.embedder)
    used.foreach { client =>
      assert(
        !client.toString.contains(anthropicKeyValue) && !client.toString.contains(voyageKeyValue)
      )
    }
    Vector[PortBundle](queryPorts, semanticPorts, workerPorts).foreach(_.close())
  }

  test("one process shares one embedding spend counter across every Voyage client it builds") {
    val rag = new RagProviderClients()
    val f = new AwsSdkPortFactory(creds, unusedGraphReader, rag, new BedrockCount().build)
    val a = f.semantic(semanticConfig(defaults("semantic-service"))).toOption.get
    val b = f.worker(workerConfig(defaults("embedding-worker"))).toOption.get
    val clientA = a.embedding.asInstanceOf[VoyageEmbeddingClient]
    val clientB = b.embedder.asInstanceOf[VoyageEmbeddingClient]
    assert(clientA.tokenCounter eq rag.counter)
    assert(clientB.tokenCounter eq rag.counter)
    assert(rag.counter.capUsd == BigDecimal("0.30") && rag.counter.tokensUsed == 0)
    // A second process-level instance owns a different counter.
    assert(new RagProviderClients().counter ne rag.counter)
    Vector[PortBundle](a, b).foreach(_.close())
  }

  test("a non-default configured synthesis and embedding model flows into the built clients") {
    val bedrock = new BedrockCount
    val f = new AwsSdkPortFactory(creds, unusedGraphReader, new RagProviderClients(), bedrock.build)
    val env = Map(
      "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL" -> "claude-test-model-9",
      "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION" -> "claude-test-model-9-r2"
    )
    val q = queryConfig(defaults("query-api") ++ env)
    val runtime = AwsComposition.runtimeConfig(q).toOption.get
    assert(runtime.model.modelId == "claude-test-model-9")
    assert(runtime.model.modelVersion == "claude-test-model-9-r2")
    val queryPorts = f.query(q, runtime).toOption.get
    assert(queryPorts.llm.isInstanceOf[AnthropicMessagesLlmClient])
    val embedded = Map(
      "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL" -> "voyage-test-model",
      "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION" -> "voyage-test-model-r2",
      "SCHOLARCHAIN_EMBEDDING_DIMENSION" -> "512"
    )
    val expected = EmbeddingModel("voyage-test-model", "voyage-test-model-r2", 512)
    val s = f.semantic(semanticConfig(defaults("semantic-service") ++ embedded)).toOption.get
    val w = f.worker(workerConfig(defaults("embedding-worker") ++ embedded)).toOption.get
    assert(s.embedding.model == expected && w.embedder.model == expected)
    assert(s.embedding.isInstanceOf[VoyageEmbeddingClient])
    // The consistency check runs against the configured identity, so these start.
    for ((role, config) <- Vector(("semantic-service", embedded), ("embedding-worker", embedded))) {
      val e = defaults(role) ++ embedded ++ fast
      val built = AwsComposition.build(service(e), parse(role, e).toOption.get, e, f)
      assert(built.isRight, s"$role $built")
      built.toOption.get.close()
    }
    assert(bedrock.built.get == 0)
    Vector[PortBundle](queryPorts, s, w).foreach(_.close())
  }

  test("the rag clients take the configured model and refuse only malformed input, keyless") {
    val rag = new RagProviderClients()
    val other = EmbeddingModel("voyage-test-model", "voyage-test-model", 512)
    val built = rag.voyage(new Secret(voyageKeyValue), other, EmbeddingPurpose.Query)
    assert(built.toOption.exists(_.model == other))
    val unsupported = EmbeddingModel("voyage-test-model", "voyage-test-model", 300)
    val refused = rag.voyage(new Secret(voyageKeyValue), unsupported, EmbeddingPurpose.Query)
    assert(refused == Left("invalid-voyage-embedding-config"))
    val bad = rag.voyage(new Secret("has a space"), VoyageDefaults.Model, EmbeddingPurpose.Query)
    assert(bad.isLeft && !bad.left.toOption.get.contains("space"))
  }

  test("a real anthropic and voyage composition starts offline and is process-only until probed") {
    val bedrock = new BedrockCount
    val f = new AwsSdkPortFactory(creds, unusedGraphReader, new RagProviderClients(), bedrock.build)
    for (role <- Vector("semantic-service", "embedding-worker", "query-api")) {
      val env = defaults(role) ++ fast
      val config = parse(role, env).toOption.get
      val built = AwsComposition.build(service(env), config, env, f)
      assert(built.isRight, s"$role $built")
      assert(
        !built.toString.contains(anthropicKeyValue) && !built.toString.contains(voyageKeyValue)
      )
      built.toOption.get.close()
    }
    assert(bedrock.built.get == 0)
  }

  /** Hands the semantic and worker roles an embedder with a different identity than configured. */
  private final class OtherModelFactory(model: EmbeddingModel) extends AwsPortFactory {
    val inner = new FakeFactory
    def graph(config: GraphRoleConfig) = inner.graph(config)
    def query(config: QueryRoleConfig, runtime: RuntimeConfig) = inner.query(config, runtime)
    def semantic(config: SemanticRoleConfig) = inner.semantic(config).map { p =>
      new SemanticPorts(new FakeEmbedder(inner.d, model), p.vectors, () => p.close())
    }
    def worker(config: WorkerRoleConfig) = inner.worker(config).map { p =>
      new WorkerPorts(
        p.queue,
        p.dlq,
        p.sessions,
        p.objects,
        p.vectors,
        p.registry,
        p.ledger,
        new FakeEmbedder(inner.d, model),
        () => p.close()
      )
    }
  }

  test("a stored versus query provider, model, version or dimension mismatch refuses startup") {
    val voyage = EmbeddingModel("voyage-4-lite", "voyage-4-lite", 256)
    val titan = EmbeddingModel("amazon.titan-embed-text-v2:0", "configured-version-v1", 256)
    val cases = Vector(
      (voyage.copy(dimension = 512), "vector-consistency-dimension-mismatch"),
      (voyage.copy(version = "voyage-4-lite-b"), "vector-consistency-version-mismatch"),
      (voyage.copy(modelId = "voyage-4-lite-b"), "vector-consistency-model-mismatch"),
      (titan, "vector-consistency-provider-mismatch")
    )
    for ((model, code) <- cases; role <- Vector("semantic-service", "embedding-worker")) {
      val factory = new OtherModelFactory(model)
      val env = defaults(role) ++ fast
      val config = parse(role, env).toOption.get
      assert(AwsComposition.build(service(env), config, env, factory) == Left(code), s"$role $code")
      assert(factory.inner.closed.get == 1, "the opened ports are released on refusal")
    }
    // The matching identity starts, and the other provider's configuration is checked the same way.
    val same = new OtherModelFactory(voyage)
    val env = defaults("semantic-service") ++ fast
    val config = parse("semantic-service", env).toOption.get
    assert(AwsComposition.build(service(env), config, env, same).isRight)
    val bedrockEnv = forRole("semantic-service") ++ fast
    val bedrockConfig = parse("semantic-service", bedrockEnv).toOption.get
    val toVoyage = new OtherModelFactory(voyage)
    assert(
      AwsComposition.build(service(bedrockEnv), bedrockConfig, bedrockEnv, toVoyage) ==
        Left("vector-consistency-provider-mismatch")
    )
  }

  test("a Voyage model id cannot be configured under the Bedrock provider") {
    val mixed =
      forRole("semantic-service").updated("SCHOLARCHAIN_MODELS_EMBEDDING_MODEL", "voyage-4-lite")
    assert(
      parse("semantic-service", mixed) ==
        Left("invalid-aws-configuration:SCHOLARCHAIN_MODELS_EMBEDDING_MODEL")
    )
  }

  test("the runtime config used by the client and agents carries the provider's model id") {
    val anthropic = AwsComposition.runtimeConfig(queryConfig(defaults("query-api"))).toOption.get
    assert(anthropic.model.modelId == AnthropicDefaults.ModelId)
    val bedrock = AwsComposition.runtimeConfig(queryConfig(forRole("query-api"))).toOption.get
    assert(bedrock.model.modelId == profile)
  }

  // ---- readiness and health -------------------------------------------------------------

  test("readiness, health and metrics make no provider call and never show a key") {
    val config = service(common)
    def stub(role: String) = ApiServer.start(
      new ApiApplication(
        new QueryService(
          new edu.uic.cs441.scholarchain.storage.InMemoryQuerySessionStore,
          (_, _, _) => Left(ApiError.unavailable),
          config
        ),
        config,
        () => true,
        _ => (),
        role
      ),
      "127.0.0.1",
      0
    )
    val graphServer = stub("graph-service")
    val semanticServer = stub("semantic-service")
    val fake = new FakeFactory
    val env = defaults("query-api") ++ Map(
      "SCHOLARCHAIN_GRAPH_BASE_URI" -> s"http://127.0.0.1:${graphServer.port}",
      "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> s"http://127.0.0.1:${semanticServer.port}",
      voyageName -> voyageKeyValue
    ) ++ fast ++ shortBreaker
    val (started, startErr) = captured(ServiceBootstrap.launch("query-api", env, fake))
    val running = started.toOption.get
    try {
      val auth = Map("Authorization" -> ("Bearer " + apiKey))
      val bodies = Vector(
        Http.get(running.port, "/healthz"),
        Http.get(running.port, "/readyz"),
        Http.get(running.port, "/readyz"),
        Http.get(running.port, "/metrics", auth)
      )
      assert(bodies.map(_._1) == Vector(200, 200, 200, 200))
      bodies.foreach { case (_, body) =>
        assert(!body.contains(anthropicKeyValue) && !body.contains(voyageKeyValue), body)
      }
      assert(fake.llm.requests.isEmpty, "readiness never called the model")
      assert(fake.d.calls("embed") == 0)
      assert(!startErr.contains(anthropicKeyValue))
    } finally { running.close(); graphServer.close(); semanticServer.close() }
    val semanticFake = new FakeFactory
    val semanticEnv = defaults("semantic-service") ++ fast
    val semanticRun =
      ServiceBootstrap.launch("semantic-service", semanticEnv, semanticFake).toOption.get
    try {
      assert(Http.get(semanticRun.port, "/readyz")._1 == 200)
      assert(Http.get(semanticRun.port, "/readyz")._1 == 200)
      val (_, body) = Http.get(semanticRun.port, "/readyz")
      assert(!body.contains(voyageKeyValue))
      assert(semanticFake.d.calls("embed") == 0, "readiness never called the embedder")
    } finally semanticRun.close()
  }

  test("provider selection source never prints, logs or interpolates a key") {
    val relative = "modules/services/src/main/scala/edu/uic/cs441/scholarchain/services"
    val root = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve(relative))
      .find(Files.isDirectory(_))
      .get
    val text = Vector("AwsConfig", "AwsPorts")
      .map(n => Files.readString(root.resolve(n + ".scala"), UTF_8))
      .mkString("\n")
    assert(!text.contains("println") && !text.contains("logger") && !text.contains("System.err"))
    assert("""\$\{?[A-Za-z.]*[Kk]ey""".r.findFirstIn(text).isEmpty, "no key interpolation")
  }
}
