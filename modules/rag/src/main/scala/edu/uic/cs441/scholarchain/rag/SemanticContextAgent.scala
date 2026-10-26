package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*

/** Verified Phase8 objects supply descriptive data only. No store is created or written here. */
final class SemanticContextAgent(
    vectors: VectorStore,
    objects: ObjectStore,
    embedding: EmbeddingClient,
    index: String,
    config: RuntimeConfig
) {
  import RuntimeEvidenceItems.*
  require(index.trim.nonEmpty && RuntimeConfigValidation.check(config).isEmpty)
  def run(input: RetrievalInput): RetrievalResult = RuntimeRead.stage("semantic", input) {
    val plan = input.plan
    val window = RuntimeRead.window(input, config)
    if (plan.venueFilters.nonEmpty)
      throw RetrievalProblem("unsupported", "semantic-venue-metadata-not-stored")
    if (plan.topicFilters.size > 1 || plan.institutionFilters.size > 1)
      throw RetrievalProblem("unsupported", "semantic-multiple-filter-values-not-supported")
    val filter = Map("windowId" -> window) ++ plan.topicFilters.headOption.map("topicId" -> _) ++
      plan.institutionFilters.headOption.map("institutionId" -> _)
    val result = embedding.embed(Vector(plan.question)).toVector
    val vector = result match {
      case Vector(EmbeddingSuccess(v, model, _))
          if model == embedding.model && v.size == model.dimension && v.forall(_.isFinite) =>
        v
      case _ => throw RetrievalProblem("failed", "query-embedding-unavailable")
    }
    val limit = math.min(plan.vectorLimit, config.retrieval.vectorLimit)
    val hits = RuntimeRead.value(vectors.query(index, vector, limit, filter))
    RuntimeRead.check(
      hits.size <= limit && hits.map(_.key).distinct.size == hits.size &&
        hits.forall(h =>
          h.metadata.get("embeddingModel").contains(embedding.model.tag) && filter.forall(
            (key, value) => h.metadata.get(key).contains(value)
          )
        ),
      "semantic-filter-or-result-mismatch"
    )
    val items = hits.map { hit =>
      val uri = java.net.URI.create(hit.metadata.getOrElse("textS3Uri", ""))
      RuntimeRead.check(
        uri.getScheme == "s3" && Option(uri.getHost)
          .exists(_.nonEmpty) && uri.getRawQuery == null && uri.getRawFragment == null,
        "semantic-object-uri-invalid"
      )
      val stored = RuntimeRead.value(objects.get(uri.getRawPath.stripPrefix("/")))
      val excerpt = SemanticContexts
        .fromStoredObject(hit, stored, config.retrieval.contextTokenBudget)
        .fold(c => throw RetrievalProblem("failed", c), identity)
      val envelope =
        ujson.read(new String(stored.bytes.toArray, java.nio.charset.StandardCharsets.UTF_8))
      val document = upickle.default.read[EmbeddingDocument](envelope("document"))
      RuntimeRead.check(
        document.windowId == window && filter
          .filterNot(_._1 == "windowId")
          .forall((k, v) => document.identityFields.get(k).contains(v)),
        "semantic-document-filter-mismatch"
      )
      make(
        input,
        "semantic",
        Vector(document.entityId),
        Vector(window),
        document.runId,
        Vector(
          text("usage", EmbeddingContracts.descriptiveOnly),
          text("documentType", document.documentType),
          text("vectorKey", hit.key),
          text("textHash", excerpt.textHash)
        ),
        document.sourceReferences,
        evidenceType = EvidenceType.TextChunk,
        descriptive = true,
        excerpt = Some(excerpt.excerpt),
        sourceUri = Some(excerpt.textS3Uri)
      ) match {
        case item => RuntimeEvidenceIds.bind(item.copy(score = excerpt.score)).toOption.get
      }
    }
    if (items.isEmpty) throw RetrievalProblem("missing", "semantic-context-empty")
    RetrievalOutput(
      "semantic",
      items,
      truncated = hits.size == limit || items.exists(
        _.text.exists(s => s.codePointCount(0, s.length) >= config.retrieval.contextTokenBudget)
      )
    )
  }
}
