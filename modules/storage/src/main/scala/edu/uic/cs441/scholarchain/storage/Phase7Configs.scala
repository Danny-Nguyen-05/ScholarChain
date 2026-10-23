package edu.uic.cs441.scholarchain.storage

import java.nio.file.Path
import upickle.default.ReadWriter

final case class ExportValidationConfig(
    maxMetadataBytes: Long = 4 * 1024 * 1024,
    maxCsvCellChars: Int = 1024 * 1024,
    sortChunkRows: Int = 1000,
    maxAffiliations: Int = 100,
    maxEnrichedCsvBytes: Int = 8 * 1024 * 1024,
    scratchDirectory: Option[Path] = None
) {
  require(
    maxMetadataBytes > 0 && maxCsvCellChars > 0 && sortChunkRows > 0 && maxEnrichedCsvBytes > 1024
  )
}
final case class NeptuneLoaderConfig(
    bucket: String,
    graphPrefix: String,
    region: String,
    iamRoleArn: String,
    pollIntervalMillis: Long = 1000,
    timeoutMillis: Long = 300000,
    maxPolls: Int = 300,
    maxUploadBytes: Int = 16 * 1024 * 1024,
    requestTimeoutMillis: Long = 30000,
    retry: RetryConfig = RetryConfig()
) {
  require(Vector(bucket, graphPrefix, region, iamRoleArn).forall(_.nonEmpty))
  require(
    pollIntervalMillis >= 0 && timeoutMillis > 0 && maxPolls > 0 && maxUploadBytes > 0 && requestTimeoutMillis > 0
  )
}
final case class GraphReaderConfig(
    maxDepth: Int = 6,
    maxLimit: Int = 100,
    maxCursorOffset: Int = 10000,
    requestTimeoutMillis: Long = 5000,
    retry: RetryConfig = RetryConfig(),
    allowedEdgeTypes: Set[String] = Set(
      "AUTHORED",
      "COAUTHORED_WITH",
      "PUBLISHED_IN",
      "AFFILIATED_WITH",
      "HAS_TOPIC",
      "RESOLVES_TO",
      "DERIVED_FROM",
      "SUPPORTED_BY"
    )
) {
  require(
    maxDepth > 0 && maxDepth <= 12 && maxLimit > 0 && maxCursorOffset >= 0 && requestTimeoutMillis > 0
  )
}
final case class VectorAdapterConfig(
    bucket: String,
    dimension: Int,
    metric: String,
    putBatchSize: Int = 500,
    getBatchSize: Int = 100,
    maxTopK: Int = 10000,
    maxQueryPages: Int = 100,
    maxMetadataBytes: Int = 40 * 1024,
    maxFilterableBytes: Int = 2 * 1024,
    maxMetadataKeys: Int = 50,
    nonFilterableKeys: Set[String] = Set("textS3Uri"),
    maxRequestBytes: Int = 20 * 1024 * 1024,
    requestTimeoutMillis: Long = 10000,
    retry: RetryConfig = RetryConfig()
) {
  require(
    bucket.nonEmpty && dimension >= 1 && dimension <= 4096 && Set("cosine", "euclidean")(metric)
  )
  require(putBatchSize > 0 && putBatchSize <= 500 && getBatchSize > 0 && getBatchSize <= 100)
  require(
    maxTopK > 0 && maxTopK <= 10000 && maxQueryPages > 0 && maxMetadataBytes > 0 && maxMetadataBytes <= 40 * 1024
  )
  require(
    maxFilterableBytes > 0 && maxFilterableBytes <= 2 * 1024 && maxMetadataKeys > 0 && maxMetadataKeys <= 50
  )
  require(
    nonFilterableKeys.size <= 10 && maxRequestBytes > 0 && maxRequestBytes <= 20 * 1024 * 1024 && requestTimeoutMillis > 0
  )
}
object VectorIndexes {
  val names: Set[String] = Set(
    "researcher-profile-v1",
    "collaboration-community-v1",
    "paper-abstract-v1",
    "collaboration-path-v1",
    "topic-institution-summary-v1"
  )
  def key(
      documentType: String,
      entityId: String,
      windowId: String,
      modelVersion: String
  ): String = {
    require(Vector(documentType, entityId, windowId, modelVersion).forall(_.nonEmpty))
    StorageKeys.composite(documentType, entityId, windowId, modelVersion)
  }
}
final case class SourceRunPointer(runId: String, key: String, sha256: String) derives ReadWriter
