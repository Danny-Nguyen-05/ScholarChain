package edu.uic.cs441.scholarchain.core

import java.net.URI
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.ReadWriter

/** Additive Phase 8 contracts. No credentials, providers or storage dependencies live here. */
object EmbeddingContracts {
  val schemaVersion: String = "scholarchain.embedding.v1"
  val documentTypes: Set[String] = Set(
    "researcher-profile",
    "community",
    "collaboration-path",
    "paper",
    "topic-institution-summary"
  )
  val textSelections: Set[String] =
    Set("generated-summary", "permitted-abstract", "paper-summary-fallback")
  val indexes: Map[String, String] = Map(
    "researcher-profile" -> "researcher-profile-v1",
    "community" -> "collaboration-community-v1",
    "collaboration-path" -> "collaboration-path-v1",
    "paper" -> "paper-abstract-v1",
    "topic-institution-summary" -> "topic-institution-summary-v1"
  )
  val identityFieldNames: Set[String] =
    Set("researcherId", "communityId", "topicId", "institutionId", "sourceDataset")

  /** Stable slot identity excludes content and source run. Changed content in an occupied slot must
    * reach the ingestion conflict guard rather than silently creating another vector.
    */
  def vectorKey(document: EmbeddingDocument, model: EmbeddingModel): String =
    frame(
      document.documentType,
      document.entityId,
      document.windowId,
      document.templateVersion,
      document.chunkPolicyVersion,
      document.chunkOrdinal.toString,
      model.tag
    )

  /** Entity-group identity omits the ordinal so a binding can cover every chunk atomically. Count
    * and whole-text hash are binding values, never part of this identity.
    */
  def groupKey(document: EmbeddingDocument, model: EmbeddingModel): String =
    frame(
      document.documentType,
      document.entityId,
      document.windowId,
      document.templateVersion,
      document.chunkPolicyVersion,
      model.tag
    )

  /** Legacy single-chunk documents can establish their complete-text hash from their own text.
    * Validation rejects this fallback for a multi-chunk document or a nonzero ordinal.
    */
  def wholeTextHash(document: EmbeddingDocument): String =
    if (document.wholeTextHash.nonEmpty) document.wholeTextHash else textHash(document.text)
  val descriptiveOnly: String =
    "descriptive-context-only; exact metrics and graph claims require graph/metric evidence"
  def textHash(text: String): String = StableIds.sha256Hex(text)
  private[core] def frame(parts: String*): String =
    parts.map(p => s"${p.getBytes(UTF_8).length}:$p").mkString
}

/** Model version and output dimension are part of identity, not inferred from provider defaults. */
final case class EmbeddingModel(modelId: String, version: String, dimension: Int)
    derives ReadWriter {
  def tag: String = EmbeddingContracts.frame(modelId, version, dimension.toString)
}

/** Source references retain the original exported row and field locators. Text selection records
  * whether a paper used permitted abstract text or its deterministic metadata fallback.
  */
@upickle.implicits.serializeDefaults(true)
final case class EmbeddingDocument(
    documentId: String,
    documentType: String,
    entityId: String,
    windowId: String,
    runId: String,
    templateVersion: String,
    text: String,
    sourceReferences: Vector[SummarySourceRef],
    textSelection: String,
    schemaVersion: String = EmbeddingContracts.schemaVersion,
    identityFields: Map[String, String] = Map.empty,
    chunkPolicyVersion: String = "",
    chunkOrdinal: Int = -1,
    chunkCount: Int = 1,
    wholeTextHash: String = ""
) derives ReadWriter

/** Manifest and queue payload. Hash is over the exact document text encoded as UTF-8. The URI
  * points to ordinary S3 JSON containing that text, never to a vector bucket.
  */
@upickle.implicits.serializeDefaults(true)
final case class EmbeddingWorkItem(
    vectorKey: String,
    indexName: String,
    document: EmbeddingDocument,
    textS3Uri: String,
    textHash: String,
    embeddingModel: EmbeddingModel,
    schemaVersion: String = EmbeddingContracts.schemaVersion
) derives ReadWriter

/** Closed metadata shape excludes text, excerpts and source-reference arrays. Service-specific
  * byte/filterability limits remain the adapter's responsibility.
  */
@upickle.implicits.serializeDefaults(true)
final case class EmbeddingVectorMetadata(
    documentType: String,
    entityId: String,
    windowId: String,
    runId: String,
    textS3Uri: String,
    textHash: String,
    embeddingModel: EmbeddingModel,
    templateVersion: String,
    documentId: String,
    schemaVersion: String = EmbeddingContracts.schemaVersion,
    identityFields: Map[String, String] = Map.empty,
    chunkPolicyVersion: String = "",
    chunkOrdinal: Int = -1
) derives ReadWriter {
  def compact: Map[String, String] = Map(
    "schemaVersion" -> schemaVersion,
    "documentType" -> documentType,
    "entityId" -> entityId,
    "windowId" -> windowId,
    "runId" -> runId,
    "textS3Uri" -> textS3Uri,
    "textHash" -> textHash,
    "embeddingModel" -> embeddingModel.tag,
    "embeddingModelId" -> embeddingModel.modelId,
    "embeddingModelVersion" -> embeddingModel.version,
    "dimension" -> embeddingModel.dimension.toString,
    "templateVersion" -> templateVersion,
    "documentId" -> documentId,
    "chunkPolicyVersion" -> chunkPolicyVersion,
    "chunkOrdinal" -> chunkOrdinal.toString
  ) ++ identityFields.filter((key, _) => EmbeddingContracts.identityFieldNames(key))
}

/** Results preserve input ordering and cardinality. Attempts count provider attempts for one text;
  * a preflight rejection has zero attempts. Failure codes contain no provider payloads.
  */
sealed trait EmbeddingResult derives ReadWriter {
  def model: EmbeddingModel
  def attempts: Int
}
final case class EmbeddingSuccess(values: Vector[Float], model: EmbeddingModel, attempts: Int)
    extends EmbeddingResult derives ReadWriter
final case class EmbeddingFailure(
    code: String,
    retryable: Boolean,
    model: EmbeddingModel,
    attempts: Int
) extends EmbeddingResult derives ReadWriter
trait EmbeddingClient {
  def model: EmbeddingModel
  def embed(texts: Seq[String]): Seq[EmbeddingResult]
}

/** A similarity score is a retrieval ranking signal, never a graph edge or exact metric. */
final case class SemanticContextItem(
    vectorKey: String,
    score: Double,
    documentType: String,
    textS3Uri: String,
    excerpt: String,
    textHash: String
) derives ReadWriter
@upickle.implicits.serializeDefaults(true)
final case class SemanticContext(
    items: Vector[SemanticContextItem],
    usage: String = EmbeddingContracts.descriptiveOnly,
    exactMetricsAllowed: Boolean = false,
    graphClaimsAllowed: Boolean = false,
    schemaVersion: String = EmbeddingContracts.schemaVersion
) derives ReadWriter

/** Structural validation only: these checks cannot establish source existence, permission to use an
  * abstract, or factual correctness. Owners resolve references against actual producer exports.
  */
object EmbeddingValidation {
  private def nonblank(value: String): Boolean = value.trim.nonEmpty
  private def identities(value: Map[String, String]): Boolean =
    value.forall((key, item) =>
      EmbeddingContracts
        .identityFieldNames(key) && nonblank(item) && item.getBytes(UTF_8).length <= 256
    )
  private def slotVersion(value: String): Boolean =
    nonblank(value) && value.getBytes(UTF_8).length <= 256 &&
      !value.exists(ch => ch.isWhitespace || ch.isControl)
  private def sha(value: String): Boolean = value.matches("[0-9a-f]{64}")
  private def s3(value: String): Boolean = try {
    val uri = URI.create(value)
    uri.getScheme == "s3" && Option(uri.getHost).exists(nonblank) &&
    Option(uri.getRawPath).exists(p => p.startsWith("/") && p.length > 1) &&
    uri.getRawQuery == null && uri.getRawFragment == null && uri.getUserInfo == null && uri.getPort == -1
  } catch { case _: IllegalArgumentException => false }
  private def errors(checks: (Boolean, String)*): Vector[String] =
    checks.collect { case (false, code) => code }.toVector
  def model(value: EmbeddingModel): Vector[String] = errors(
    (nonblank(value.modelId) && nonblank(value.version), "invalid-embedding-model"),
    (value.dimension >= 1 && value.dimension <= 4096, "invalid-embedding-dimension")
  )
  def document(value: EmbeddingDocument): Vector[String] = errors(
    (value.schemaVersion == EmbeddingContracts.schemaVersion, "unsupported-embedding-schema"),
    (StableIds.parseChunkOrProfileId(value.documentId).isRight, "invalid-document-id"),
    (EmbeddingContracts.documentTypes(value.documentType), "invalid-document-type"),
    (
      Vector(value.entityId, value.windowId, value.runId, value.templateVersion).forall(nonblank),
      "missing-document-identity"
    ),
    (slotVersion(value.templateVersion), "invalid-template-version"),
    (slotVersion(value.chunkPolicyVersion), "invalid-chunk-policy-version"),
    (value.chunkOrdinal >= 0, "invalid-chunk-ordinal"),
    (value.chunkCount >= 1 && value.chunkOrdinal < value.chunkCount, "invalid-chunk-count"),
    (
      (value.wholeTextHash.isEmpty && value.chunkCount == 1 && value.chunkOrdinal == 0) ||
        sha(value.wholeTextHash),
      "invalid-whole-text-hash"
    ),
    (
      value.chunkCount != 1 || value.wholeTextHash.isEmpty ||
        value.wholeTextHash == EmbeddingContracts.textHash(value.text),
      "whole-text-hash-mismatch"
    ),
    (nonblank(value.text), "empty-document-text"),
    (
      value.sourceReferences.nonEmpty && value.sourceReferences.forall(r =>
        Vector(r.table, r.rowKey, r.field).forall(nonblank)
      ),
      "missing-source-reference"
    ),
    (identities(value.identityFields), "invalid-identity-metadata"),
    (EmbeddingContracts.textSelections(value.textSelection), "invalid-text-selection"),
    (
      value.documentType == "paper" || value.textSelection == "generated-summary",
      "invalid-text-selection-for-type"
    )
  )
  def workItem(value: EmbeddingWorkItem): Vector[String] =
    document(value.document) ++ model(value.embeddingModel) ++ errors(
      (value.schemaVersion == EmbeddingContracts.schemaVersion, "unsupported-embedding-schema"),
      (
        nonblank(value.vectorKey) && value.vectorKey.getBytes(UTF_8).length <= 1024,
        "invalid-vector-key"
      ),
      (
        value.vectorKey == EmbeddingContracts.vectorKey(value.document, value.embeddingModel),
        "vector-key-model-or-document-mismatch"
      ),
      (
        EmbeddingContracts.indexes.get(value.document.documentType).contains(value.indexName),
        "document-index-mismatch"
      ),
      (s3(value.textS3Uri), "invalid-text-s3-uri"),
      (
        sha(value.textHash) && value.textHash == EmbeddingContracts.textHash(value.document.text),
        "text-hash-mismatch"
      )
    )
  def metadata(value: EmbeddingVectorMetadata): Vector[String] =
    model(value.embeddingModel) ++ errors(
      (value.schemaVersion == EmbeddingContracts.schemaVersion, "unsupported-embedding-schema"),
      (EmbeddingContracts.documentTypes(value.documentType), "invalid-document-type"),
      (
        Vector(value.entityId, value.windowId, value.runId, value.templateVersion).forall(nonblank),
        "missing-document-identity"
      ),
      (slotVersion(value.templateVersion), "invalid-template-version"),
      (slotVersion(value.chunkPolicyVersion), "invalid-chunk-policy-version"),
      (value.chunkOrdinal >= 0, "invalid-chunk-ordinal"),
      (StableIds.parseChunkOrProfileId(value.documentId).isRight, "invalid-document-id"),
      (s3(value.textS3Uri), "invalid-text-s3-uri"),
      (sha(value.textHash), "invalid-text-hash"),
      (identities(value.identityFields), "invalid-identity-metadata")
    )
  def result(value: EmbeddingResult): Vector[String] = model(value.model) ++ (value match {
    case EmbeddingSuccess(values, model, attempts) =>
      errors(
        (attempts >= 1, "invalid-embedding-attempts"),
        (
          values.size == model.dimension && values.forall(_.isFinite),
          "embedding-dimension-or-value-mismatch"
        )
      )
    case EmbeddingFailure(code, _, _, attempts) =>
      errors(
        (code.matches("[a-z][a-z0-9-]*"), "invalid-embedding-failure-code"),
        (attempts >= 0, "invalid-embedding-attempts")
      )
  })
  def context(value: SemanticContext, maxExcerptChars: Int = 512): Vector[String] = errors(
    (value.schemaVersion == EmbeddingContracts.schemaVersion, "unsupported-embedding-schema"),
    (
      value.usage == EmbeddingContracts.descriptiveOnly && !value.exactMetricsAllowed && !value.graphClaimsAllowed,
      "semantic-context-is-not-evidence"
    ),
    (maxExcerptChars > 0, "invalid-excerpt-limit"),
    (
      value.items.forall(i =>
        nonblank(i.vectorKey) && i.score.isFinite && EmbeddingContracts.documentTypes(
          i.documentType
        ) && s3(i.textS3Uri) && sha(i.textHash) && nonblank(
          i.excerpt
        ) && i.excerpt.codePointCount(0, i.excerpt.length) <= maxExcerptChars
      ),
      "invalid-semantic-context-item"
    )
  )
}
