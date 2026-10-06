package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Environment-specific settings. No field has a compiled-in bucket, endpoint, account id,
  * threshold, model id, graph window, or bridge parameter. Callers must load a file and environment
  * through [[ConfigLoader]].
  */
final case class ScholarChainConfig(
    configSchemaVersion: String,
    application: ApplicationConfig,
    storage: StorageConfig,
    neptune: NeptuneConfig,
    s3Vectors: S3VectorsConfig,
    entityResolution: EntityResolutionConfig,
    graph: GraphConfig,
    retrieval: RetrievalConfig,
    models: ModelsConfig,
    operations: OperationsConfig
) derives ReadWriter {
  def canonicalJson: String = CoreJson.compact(this)

  def fingerprint: String = StableIds.sha256Hex(canonicalJson)
}

final case class ApplicationConfig(
    environment: String,
    region: String,
    awsAccountId: Option[String]
) derives ReadWriter

final case class StorageConfig(
    rawBucket: String,
    curatedBucket: String,
    graphBucket: String,
    ragBucket: String
) derives ReadWriter

final case class NeptuneConfig(
    endpoint: String,
    port: Int,
    queryTimeoutMs: Int
) derives ReadWriter

final case class S3VectorsConfig(
    vectorBucket: String,
    indexes: VectorIndexConfig
) derives ReadWriter

final case class VectorIndexConfig(
    researchers: String,
    communities: String,
    abstracts: String,
    paths: String,
    topicInstitutions: String
) derives ReadWriter

final case class EntityResolutionConfig(
    policyVersion: String,
    acceptThreshold: Double,
    rejectThreshold: Double,
    llmBandMin: Double,
    llmBandMax: Double
) derives ReadWriter

final case class GraphConfig(
    windowStartYear: Int,
    windowEndYear: Int,
    bridgeAlgorithm: String,
    bridgeParameters: Vector[NamedText]
) derives ReadWriter

final case class RetrievalConfig(
    graphLimit: Int,
    vectorLimit: Int,
    contextTokenBudget: Int,
    fusionPolicyVersion: String,
    maxPathDepth: Int
) derives ReadWriter

final case class ModelsConfig(
    embeddingModel: String,
    synthesisModel: String,
    verificationModel: String
) derives ReadWriter

final case class OperationsConfig(
    synchronousDeadlineMs: Int,
    maxWorkflowRetries: Int,
    maxConcurrentLlmCalls: Int
) derives ReadWriter

final case class ConfigError(messages: Vector[String]) {
  def text: String = messages.mkString("; ")
}
