package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import software.amazon.awssdk.services.bedrockruntime.BedrockRuntimeClient

/** Synthesis provider: `anthropic` (default, Anthropic Messages API, model `claude-haiku-5-5`) or
  * `bedrock` (Converse API, the configured Bedrock model). Selected by the services from env
  * `SCHOLARCHAIN_SYNTHESIS_PROVIDER`.
  */
enum SynthesisProvider(val wire: String) {
  case Anthropic extends SynthesisProvider("anthropic")
  case Bedrock extends SynthesisProvider("bedrock")
}
object SynthesisProvider {
  val EnvName: String = "SCHOLARCHAIN_SYNTHESIS_PROVIDER"
  val Default: SynthesisProvider = Anthropic

  /** None or blank selects the default. An unknown value is a closed code and is never echoed. */
  def parse(raw: Option[String]): Either[String, SynthesisProvider] =
    raw.map(_.trim).filter(_.nonEmpty) match {
      case None              => Right(Default)
      case Some("anthropic") => Right(Anthropic)
      case Some("bedrock")   => Right(Bedrock)
      case Some(_)           => Left("invalid-synthesis-provider")
    }
}

/** Embedding provider: `voyage` (default, model `voyage-4-lite`, dimension 256) or `bedrock` (Titan
  * Text Embeddings V2). Selected by the services from env `SCHOLARCHAIN_EMBEDDING_PROVIDER`.
  */
enum EmbeddingProvider(val wire: String) {
  case Voyage extends EmbeddingProvider("voyage")
  case Bedrock extends EmbeddingProvider("bedrock")
}
object EmbeddingProvider {
  val EnvName: String = "SCHOLARCHAIN_EMBEDDING_PROVIDER"
  val Default: EmbeddingProvider = Voyage
  def parse(raw: Option[String]): Either[String, EmbeddingProvider] =
    raw.map(_.trim).filter(_.nonEmpty) match {
      case None            => Right(Default)
      case Some("voyage")  => Right(Voyage)
      case Some("bedrock") => Right(Bedrock)
      case Some(_)         => Left("invalid-embedding-provider")
    }
}

/** Provider-aware embedding price and cap. The values are the defaults held in [[VoyageDefaults]]
  * and [[BedrockDefaults]]; a caller with configured values passes them to `newCounter`. Voyage
  * gives the first 200M tokens per account free, but the token counter and every bound still price
  * all tokens, so a bound never depends on the free allowance.
  */
object EmbeddingPricing {
  def defaultCapUsd(provider: EmbeddingProvider): BigDecimal = provider match {
    case EmbeddingProvider.Voyage  => VoyageDefaults.CapUsd
    case EmbeddingProvider.Bedrock => BedrockDefaults.EmbeddingCapUsd
  }
  def usdPerMillionTokens(provider: EmbeddingProvider): BigDecimal = provider match {
    case EmbeddingProvider.Voyage  => VoyageDefaults.UsdPerMillionTokens
    case EmbeddingProvider.Bedrock => BedrockDefaults.EmbeddingUsdPerMillionTokens
  }

  /** The embedding cap counted in tokens at the price (defaults: USD 0.30 at USD 0.02 per 1M). */
  def newCounter(
      provider: EmbeddingProvider,
      capUsd: Option[BigDecimal] = None,
      usdPerMillion: Option[BigDecimal] = None
  ): EmbeddingSpendCounter = new EmbeddingSpendCounter(
    capUsd.getOrElse(defaultCapUsd(provider)),
    usdPerMillion.getOrElse(usdPerMillionTokens(provider))
  )
}

/** Which provider and model identity a stored or query vector carries. */
object EmbeddingProviders {

  /** The provider that a model id belongs to: `voyage-*` is Voyage, anything else is Bedrock. */
  def infer(model: EmbeddingModel): EmbeddingProvider =
    if (model.modelId.startsWith("voyage-")) EmbeddingProvider.Voyage
    else EmbeddingProvider.Bedrock

  /** A model belongs to its provider by naming family (`voyage-*` is Voyage, never Bedrock); the
    * exact model id and dimension come from configuration.
    */
  def modelMatchesProvider(provider: EmbeddingProvider, model: EmbeddingModel): Boolean =
    infer(model) == provider
}

/** Typed refusal for a stored versus query vector identity mismatch. `field` is one of `provider`,
  * `model`, `version` or `dimension`; no values are included.
  */
final case class VectorConsistencyError(field: String) {
  def code: String = s"vector-consistency-$field-mismatch"
}

/** Stored and query vectors must share provider, model, version tag and dimension. Changing the
  * embedding model requires a full re-embed and an index rebuild; mixed vectors are refused.
  */
object VectorConsistency {
  def check(
      storedProvider: EmbeddingProvider,
      stored: EmbeddingModel,
      queryProvider: EmbeddingProvider,
      query: EmbeddingModel
  ): Either[VectorConsistencyError, Unit] =
    if (storedProvider != queryProvider) Left(VectorConsistencyError("provider"))
    else if (stored.modelId != query.modelId) Left(VectorConsistencyError("model"))
    else if (stored.version != query.version) Left(VectorConsistencyError("version"))
    else if (stored.dimension != query.dimension) Left(VectorConsistencyError("dimension"))
    else Right(())

  /** An embedder that is not a `ProviderEmbeddingClient` (a test double) has its provider inferred
    * from its model id.
    */
  def checkClient(
      storedProvider: EmbeddingProvider,
      stored: EmbeddingModel,
      client: EmbeddingClient
  ): Either[VectorConsistencyError, Unit] = {
    val queryProvider = client match {
      case p: ProviderEmbeddingClient => p.provider
      case other                      => EmbeddingProviders.infer(other.model)
    }
    check(storedProvider, stored, queryProvider, client.model)
  }
}

/** Raised by composition code and carries only a closed code, never a key or response text. */
private[rag] final class ProviderConfigurationError(val code: String) extends RuntimeException(code)

/** Builds the synthesis client for the selected provider. API keys arrive as arguments (the
  * services read env `SCHOLARCHAIN_ANTHROPIC_API_KEY`); no key is logged, printed or placed in a
  * result or exception. The Bedrock SDK client is a thunk so the Anthropic path never needs AWS.
  */
object SynthesisClients {
  val AnthropicKeyEnvName: String = "SCHOLARCHAIN_ANTHROPIC_API_KEY"

  /** The runtime config the workflow must use: `modelId` is the configured synthesis model id (for
    * example from `SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL`); it replaces the config's id so the client
    * and every agent agree. No id is forced here.
    */
  def runtimeConfigFor(
      provider: SynthesisProvider,
      config: RuntimeConfig,
      modelId: String
  ): RuntimeConfig = config.copy(model = config.model.copy(modelId = modelId))

  /** The config as given: its `model.modelId` is already the configured id. */
  def runtimeConfigFor(provider: SynthesisProvider, config: RuntimeConfig): RuntimeConfig = config

  def create(
      provider: SynthesisProvider,
      config: RuntimeConfig,
      anthropicApiKey: Option[String],
      bedrock: () => BedrockRuntimeClient,
      anthropic: AnthropicSettings = AnthropicSettings()
  ): Either[String, LlmClient] =
    if (RuntimeConfigValidation.check(config).nonEmpty) Left("invalid-runtime-config")
    else
      provider match {
        case SynthesisProvider.Bedrock => Right(new BedrockConverseLlmClient(bedrock(), config))
        case SynthesisProvider.Anthropic =>
          anthropicApiKey.filter(_.nonEmpty) match {
            case None => Left("anthropic-api-key-missing")
            case Some(raw) =>
              AnthropicApiKey
                .fromValue(raw)
                .flatMap(key =>
                  try Right(new AnthropicMessagesLlmClient(key, config, anthropic))
                  catch { case _: IllegalArgumentException => Left("invalid-anthropic-base-uri") }
                )
          }
      }
}

/** Builds the embedding client for the selected provider and purpose. Ingest uses `Document`,
  * queries use `Query` (Voyage `input_type`); Titan has no such distinction. Share one counter
  * between the document and query clients of a run so the embedding token cap is applied once.
  * `voyageConfig` carries the configured model, endpoint and limits (defaults: [[VoyageDefaults]]).
  * Both configs are by-name: only the selected provider's config is ever evaluated, so a Titan
  * model never reaches `VoyageEmbeddingConfig` validation and a Voyage model never reaches
  * `BedrockEmbeddingConfig` validation.
  */
object EmbeddingClientFactory {
  val VoyageKeyEnvName: String = "SCHOLARCHAIN_VOYAGE_API_KEY"
  def create(
      provider: EmbeddingProvider,
      inputType: EmbeddingInputType,
      voyageApiKey: Option[String],
      bedrock: () => BedrockRuntimeClient,
      bedrockConfig: => Option[BedrockEmbeddingConfig],
      counter: EmbeddingSpendCounter = EmbeddingPricing.newCounter(EmbeddingProvider.Voyage),
      voyageConfig: => Option[VoyageEmbeddingConfig] = None
  ): Either[String, ProviderEmbeddingClient] = provider match {
    case EmbeddingProvider.Bedrock =>
      bedrockConfig match {
        case None => Left("bedrock-embedding-config-missing")
        case Some(c) if !EmbeddingProviders.modelMatchesProvider(provider, c.model) =>
          Left("embedding-provider-model-mismatch")
        case Some(c) => Right(new BedrockEmbeddingClient(bedrock(), c))
      }
    case EmbeddingProvider.Voyage =>
      voyageApiKey.filter(_.nonEmpty) match {
        case None => Left("voyage-api-key-missing")
        case Some(raw) =>
          VoyageApiKey
            .fromValue(raw)
            .flatMap(key =>
              try
                Right(
                  new VoyageEmbeddingClient(
                    key,
                    voyageConfig
                      .fold(VoyageEmbeddingConfig(inputType))(_.copy(inputType = inputType)),
                    counter
                  )
                )
              catch {
                case e: IllegalArgumentException =>
                  val code = Option(e.getMessage).map(_.stripPrefix("requirement failed: "))
                  Left(
                    code
                      .filter(_.matches("invalid-voyage-[a-z-]+"))
                      .getOrElse("invalid-voyage-config")
                  )
              }
            )
      }
  }
}
