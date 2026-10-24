package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*

/** Values and locators are supplied by validated producer rows, never calculated by this renderer.
  */
final case class SourceField(name: String, value: String, reference: SummarySourceRef)
final case class RenderInput(
    documentType: String,
    entityId: String,
    windowId: String,
    runId: String,
    fields: Vector[SourceField],
    identityFields: Map[String, String] = Map.empty
)
final case class PermittedAbstract(
    text: String,
    reference: SummarySourceRef,
    permissionReference: SummarySourceRef
)

/** Limits and overlap count Unicode code points, not UTF-16 units. Prefer the last whitespace
  * boundary within the limit, retain that whitespace, and overlap exact code points. A boundary
  * must advance beyond the overlap. Thus every iteration makes progress without losing source text.
  */
final case class ChunkPolicy(maxCharacters: Int, overlapCharacters: Int, maxChunks: Int = 1000) {
  require(maxCharacters > 0 && overlapCharacters >= 0 && overlapCharacters < maxCharacters)
  require(maxChunks > 0)
  def chunks(text: String): Either[String, Vector[String]] = {
    val points = text.codePoints().toArray
    if (text.trim.isEmpty) Left("empty-document-text")
    else {
      val out = Vector.newBuilder[String]
      var start = 0
      var count = 0
      while (start < points.length && count < maxChunks) {
        val hardEnd = math.min(start + maxCharacters, points.length)
        var end = hardEnd
        if (hardEnd < points.length) {
          var boundary = hardEnd
          while (
            boundary > start + overlapCharacters + 1 &&
            !Character.isWhitespace(points(boundary - 1))
          ) boundary -= 1
          if (boundary > start + overlapCharacters + 1) end = boundary
        }
        out += new String(points, start, end - start)
        count += 1
        start = if (end == points.length) end else end - overlapCharacters
      }
      if (start < points.length) Left("chunk-count-limit") else Right(out.result())
    }
  }
}
final case class RenderingConfig(
    templateVersion: String,
    chunkPolicy: ChunkPolicy,
    maxDocumentCharacters: Int = 1000000
) {
  require(templateVersion.trim.nonEmpty && maxDocumentCharacters > 0)
}

final class DocumentRenderer(config: RenderingConfig) {
  private val headers = Map(
    "researcher-profile" -> "Researcher profile",
    "community" -> "Collaboration community",
    "collaboration-path" -> "Collaboration path",
    "paper" -> "Paper summary",
    "topic-institution-summary" -> "Topic and institution summary"
  )
  private def validRef(r: SummarySourceRef): Boolean =
    Vector(r.table, r.rowKey, r.field).forall(_.trim.nonEmpty)
  private def sortedRefs(refs: Vector[SummarySourceRef]): Vector[SummarySourceRef] =
    refs.distinct.sortBy(r => (r.table, r.rowKey, r.field))
  private def chunkPolicyVersion: String =
    Vector(
      "codepoint-whitespace-v1",
      config.chunkPolicy.maxCharacters.toString,
      config.chunkPolicy.overlapCharacters.toString,
      config.chunkPolicy.maxChunks.toString
    )
      .map(value => s"${value.length}:$value")
      .mkString
  private def version(windowId: String): String =
    Vector(
      config.templateVersion,
      windowId,
      "codepoint-whitespace-v1",
      config.chunkPolicy.maxCharacters.toString,
      config.chunkPolicy.overlapCharacters.toString,
      config.chunkPolicy.maxChunks.toString
    )
      .map(value => s"${value.length}:$value")
      .mkString

  def render(
      input: RenderInput,
      abstractText: Option[PermittedAbstract] = None
  ): Either[String, Vector[EmbeddingDocument]] = {
    if (!headers.contains(input.documentType)) Left("invalid-document-type")
    else if (Vector(input.entityId, input.windowId, input.runId).exists(_.trim.isEmpty))
      Left("missing-document-identity")
    else if (
      input.fields.isEmpty || input.fields.exists(f =>
        !f.name.matches("[a-z][A-Za-z0-9_-]*") || f.value.trim.isEmpty || !validRef(f.reference)
      ) ||
      input.fields.map(_.name).distinct.size != input.fields.size
    )
      Left("invalid-source-fields")
    else if (abstractText.nonEmpty && input.documentType != "paper") Left("abstract-for-non-paper")
    else {
      val permitted = abstractText.filter(_.text.trim.nonEmpty)
      if (permitted.exists(a => !validRef(a.reference) || !validRef(a.permissionReference)))
        Left("abstract-permission-reference-required")
      else {
        val heading = if (permitted.nonEmpty) "Paper abstract" else headers(input.documentType)
        val fields = input.fields.sortBy(_.name).map(f => s"${f.name}: ${f.value}")
        val text =
          (Vector(heading) ++ fields ++ permitted.map(a => s"abstract: ${a.text}")).mkString("\n")
        val selection =
          if (permitted.nonEmpty) "permitted-abstract"
          else if (input.documentType == "paper") "paper-summary-fallback"
          else "generated-summary"
        val refs = input.fields.map(_.reference) ++ permitted.toVector.flatMap(a =>
          Vector(a.reference, a.permissionReference)
        )
        documents(input, text, refs, selection)
      }
    }
  }

  /** Phase 6 already rendered and qualified four summary types. Preserve its exact text and
    * original locators rather than recomputing facts. An actual window is mandatory. This adapter
    * adds no generated heading or label. An explicit permitted paper abstract composes the exact
    * summary prefix, one LF and exact abstract text while retaining both permission and text refs.
    */
  def fromSummary(
      summary: SemanticSummary,
      abstractText: Option[PermittedAbstract] = None,
      identityFields: Map[String, String] = Map.empty
  ): Either[String, Vector[EmbeddingDocument]] = summary.context.windowId match {
    case None => Left("missing-summary-window")
    case Some(window) =>
      if (summary.sourceReferences.isEmpty || summary.sourceReferences.exists(r => !validRef(r)))
        Left("missing-source-reference")
      else if (abstractText.nonEmpty && summary.summaryType != "paper")
        Left("abstract-for-non-paper")
      else {
        val permitted = abstractText.filter(_.text.trim.nonEmpty)
        if (permitted.exists(a => !validRef(a.reference) || !validRef(a.permissionReference)))
          Left("abstract-permission-reference-required")
        else {
          val input = RenderInput(
            summary.summaryType,
            summary.entityId,
            window,
            summary.context.runId,
            Vector.empty,
            identityFields
          )
          val selection =
            if (permitted.nonEmpty) "permitted-abstract"
            else if (summary.summaryType == "paper") "paper-summary-fallback"
            else "generated-summary"
          val text = permitted.fold(summary.text)(a => summary.text + "\n" + a.text)
          val refs = summary.sourceReferences ++ permitted.toVector.flatMap(a =>
            Vector(a.reference, a.permissionReference)
          )
          documents(input, text, refs, selection)
        }
      }
  }

  private def documents(
      input: RenderInput,
      text: String,
      refs: Vector[SummarySourceRef],
      selection: String
  ): Either[String, Vector[EmbeddingDocument]] = {
    if (text.codePointCount(0, text.length) > config.maxDocumentCharacters)
      Left("document-character-limit")
    else
      config.chunkPolicy.chunks(text).flatMap { chunks =>
        val out = chunks.zipWithIndex.map { (chunk, ordinal) =>
          StableIds
            .chunkOrProfileId(
              input.entityId,
              version(input.windowId),
              input.documentType,
              Some(ordinal),
              chunk
            )
            .left
            .map(_ => "invalid-document-identity")
            .map { id =>
              EmbeddingDocument(
                id,
                input.documentType,
                input.entityId,
                input.windowId,
                input.runId,
                config.templateVersion,
                chunk,
                sortedRefs(refs),
                selection,
                identityFields = input.identityFields,
                chunkPolicyVersion = chunkPolicyVersion,
                chunkOrdinal = ordinal,
                chunkCount = chunks.size,
                wholeTextHash = EmbeddingContracts.textHash(text)
              )
            }
        }
        out.collectFirst { case Left(code) => code } match {
          case Some(code) => Left(code)
          case None =>
            val docs = out.collect { case Right(doc) => doc }
            if (docs.exists(d => EmbeddingValidation.document(d).nonEmpty))
              Left("invalid-rendered-document")
            else Right(docs)
        }
      }
  }
}
