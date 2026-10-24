package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.{StoredObject, StorageKeys, VectorHit}
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

/** Only descriptive excerpts leave this boundary. Graph edges, paths, counts and bridge metrics
  * require graph/metric-store evidence even when a source document happens to mention them.
  */
object SemanticContexts {
  def fromVerifiedText(
      hit: VectorHit,
      document: EmbeddingDocument,
      maxExcerptCharacters: Int = 512
  ): Either[String, SemanticContextItem] = {
    val metadata = hit.metadata
    val expectedHash = EmbeddingContracts.textHash(document.text)
    val keyMatches =
      try {
        val model = EmbeddingModel(
          metadata("embeddingModelId"),
          metadata("embeddingModelVersion"),
          metadata("dimension").toInt
        )
        EmbeddingValidation
          .model(model)
          .isEmpty && metadata.get("embeddingModel").contains(model.tag) &&
        hit.key == EmbeddingContracts.vectorKey(document, model)
      } catch { case NonFatal(_) => false }
    val matches = keyMatches && metadata.get("textHash").contains(expectedHash) &&
      metadata.get("documentId").contains(document.documentId) &&
      metadata.get("templateVersion").contains(document.templateVersion) &&
      metadata.get("chunkPolicyVersion").contains(document.chunkPolicyVersion) &&
      metadata.get("chunkOrdinal").contains(document.chunkOrdinal.toString) &&
      metadata.get("documentType").contains(document.documentType) &&
      metadata.get("entityId").contains(document.entityId) &&
      metadata.get("windowId").contains(document.windowId) &&
      metadata.get("runId").contains(document.runId)
    if (EmbeddingValidation.document(document).nonEmpty || !matches)
      Left("semantic-document-mismatch")
    else if (!hit.distance.isFinite || maxExcerptCharacters <= 0) Left("invalid-semantic-context")
    else {
      val points = document.text.codePoints().toArray
      val excerpt = new String(points, 0, math.min(points.length, maxExcerptCharacters))
      val item = SemanticContextItem(
        hit.key,
        -hit.distance,
        document.documentType,
        metadata.getOrElse("textS3Uri", ""),
        excerpt,
        expectedHash
      )
      val context = SemanticContext(Vector(item))
      if (EmbeddingValidation.context(context, maxExcerptCharacters).nonEmpty)
        Left("invalid-semantic-context")
      else Right(item)
    }
  }

  /** Verify ordinary-S3 bytes and canonical document envelope before excerpting. The caller
    * resolves the hit's URI through an ObjectStore; this helper performs no I/O or cloud calls.
    */
  def fromStoredObject(
      hit: VectorHit,
      stored: StoredObject,
      maxExcerptCharacters: Int = 512
  ): Either[String, SemanticContextItem] = {
    val pointerMatches =
      try {
        val uri = java.net.URI.create(hit.metadata.getOrElse("textS3Uri", ""))
        uri.getScheme == "s3" && Option(uri.getHost).exists(_.nonEmpty) &&
        Option(uri.getRawPath).exists(_.stripPrefix("/") == stored.head.key) &&
        uri.getRawQuery == null && uri.getRawFragment == null
      } catch { case NonFatal(_) => false }
    if (
      !pointerMatches || stored.head.sha256 != StorageKeys.sha256(stored.bytes) ||
      stored.head.size != stored.bytes.size.toLong
    ) Left("semantic-object-mismatch")
    else
      try {
        val envelope = ujson.read(new String(stored.bytes.toArray, UTF_8))
        val document = upickle.default.read[EmbeddingDocument](envelope("document"))
        if (envelope("textHash").str != EmbeddingContracts.textHash(document.text))
          Left("semantic-text-hash-mismatch")
        else fromVerifiedText(hit, document, maxExcerptCharacters)
      } catch { case NonFatal(_) => Left("semantic-invalid-object") }
  }
}
