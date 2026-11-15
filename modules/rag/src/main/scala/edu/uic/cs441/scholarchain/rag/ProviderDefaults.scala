package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.EmbeddingModel

/** Plan rule 6.7: no hardcoded endpoint, threshold or model id without a configuration entry and a
  * short rationale. Every provider value below is only a DEFAULT: runtime configuration (the
  * runtime config model id, the Live config model, and the settings case classes) overrides it.
  * Each provider has exactly one defaults object and no other file holds these literals.
  */
object AnthropicDefaults {
  // claude-haiku-5-5: instructor-approved primary, plan Update 2026-11-09.
  val ModelId: String = "claude-haiku-5-5"
  // Anthropic Messages API endpoint, platform documentation 2026-11-09.
  val BaseUri: String = "https://api.anthropic.com"
  // 2023-06-01: the stable Messages API version header value.
  val Version: String = "2023-06-01"
  // 100,000: Anthropic price tier boundary, pricing page 2026-11-09 (higher tier above it).
  val PromptTokenLimit: Long = 100000L
  // 1.3: the Haiku 5.5 tokenizer produces about 30% more tokens than Haiku 4.5, API reference.
  val MaxTokensFactor: Double = 1.3
  // 3: deliberately high estimate, English is nearer 4 bytes per token before the 30% growth.
  val BytesPerEstimatedToken: Int = 3
}

/** Anthropic endpoint and limits. Defaults come from [[AnthropicDefaults]]. */
final case class AnthropicSettings(
    baseUri: String = AnthropicDefaults.BaseUri,
    anthropicVersion: String = AnthropicDefaults.Version,
    promptTokenLimit: Long = AnthropicDefaults.PromptTokenLimit,
    maxTokensFactor: Double = AnthropicDefaults.MaxTokensFactor,
    bytesPerEstimatedToken: Int = AnthropicDefaults.BytesPerEstimatedToken
) {
  require(anthropicVersion.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}"), "invalid-anthropic-version")
  require(promptTokenLimit > 0, "invalid-anthropic-prompt-limit")
  require(maxTokensFactor.isFinite && maxTokensFactor >= 1.0, "invalid-anthropic-token-factor")
  require(bytesPerEstimatedToken >= 1, "invalid-anthropic-bytes-per-token")
}

object VoyageDefaults {
  // voyage-4-lite: instructor-approved primary embedder, plan Update 2026-11-09.
  val ModelId: String = "voyage-4-lite"
  // 256: supported output_dimension, matches the existing S3 Vectors index dimension.
  val Dimension: Int = 256
  // Dimensions Voyage documents for voyage-4-lite, docs 2026-11-09.
  val SupportedDimensions: Set[Int] = Set(256, 512, 1024, 2048)
  // Voyage embeddings endpoint, docs 2026-11-09.
  val BaseUri: String = "https://api.voyageai.com"
  // 1,000 texts per request: Voyage request limit, docs 2026-11-09.
  val MaxTextsPerRequest: Int = 1000
  // 1,000,000 tokens per request: Voyage request limit, docs 2026-11-09.
  val MaxTokensPerRequest: Int = 1000000
  // 32,000 tokens per text: voyage-4-lite context length, docs 2026-11-09.
  val MaxInputTokens: Int = 32000
  // 32 MiB: above any 1,000 x 2,048-dimension JSON response, bounds memory use.
  val MaxResponseBytes: Int = 32 * 1024 * 1024
  // USD 0.02 per 1M tokens: voyage-4-lite price, docs 2026-11-09 (first 200M tokens free, but the
  // counter still prices every token).
  val UsdPerMillionTokens: BigDecimal = BigDecimal("0.02")
  // USD 0.30: embedding cap, plan Update 2026-11-09 and repair round 3 work order.
  val CapUsd: BigDecimal = BigDecimal("0.30")
  // 3 attempts, 25-1000 ms backoff, 30 s timeout: same bounded policy as the Bedrock client.
  val MaxAttempts: Int = 3
  val BaseDelayMillis: Long = 25L
  val MaxDelayMillis: Long = 1000L
  val RequestTimeoutMillis: Long = 30000L

  /** Default stored-vector identity: model id, version tag equal to the id, default dimension. */
  val Model: EmbeddingModel = EmbeddingModel(ModelId, ModelId, Dimension)
}

object BedrockDefaults {
  // USD 0.02 per 1M tokens: Titan Text Embeddings V2 list price (USD 0.00002 per 1,000 tokens).
  val EmbeddingUsdPerMillionTokens: BigDecimal = BigDecimal("0.02")
  // USD 0.30: embedding cap, same plan cap for either embedding provider.
  val EmbeddingCapUsd: BigDecimal = BigDecimal("0.30")
}
