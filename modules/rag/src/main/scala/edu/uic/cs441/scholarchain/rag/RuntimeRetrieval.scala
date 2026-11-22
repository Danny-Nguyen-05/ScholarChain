package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

final case class RetrievalInput(plan: QueryPlan, candidates: Vector[ResearcherCandidate])
final case class RetrievalOutput(
    stage: String,
    items: Vector[EvidenceItem],
    rankingScope: Option[String] = None,
    truncated: Boolean = false
)
enum RetrievalResult {
  case Ready(output: RetrievalOutput)
  case Missing(stage: String, reason: String)
  case Unsupported(stage: String, reason: String)
  case Failed(stage: String, reason: String)
}
final case class StageFailure(stage: String, reason: String)

private[rag] final case class RetrievalProblem(kind: String, code: String)
    extends RuntimeException(code)

/** Port errors have closed public codes; provider messages and retrieved text never become errors.
  */
private[rag] object RuntimeRead {
  def value[A](result: StorageResult[A]): A = result match {
    case StorageResult.Found(v)      => v
    case StorageResult.Written(v)    => v
    case StorageResult.Unchanged(v)  => v
    case StorageResult.Retried(_, r) => value(r)
    case StorageResult.Missing => throw RetrievalProblem("missing", "required-evidence-missing")
    case StorageResult.Rejected(c)
        if Set(
          "unsupported-runtime-window",
          "unsupported-filter",
          "filtered-metric-not-stored",
          "authoritative-associations-incomplete",
          "unsupported-filtered-metric-scope",
          "unsupported-authoritative-filter-metadata",
          "unsupported-runtime-metric"
        )(c) =>
      throw RetrievalProblem("unsupported", "stored-population-or-window-unavailable")
    case StorageResult.Rejected(_) => throw RetrievalProblem("failed", "storage-read-rejected")
  }
  def stage(name: String, input: RetrievalInput)(body: => RetrievalOutput): RetrievalResult = {
    val result =
      try RetrievalResult.Ready(body)
      catch {
        case RetrievalProblem("missing", c)     => RetrievalResult.Missing(name, c)
        case RetrievalProblem("unsupported", c) => RetrievalResult.Unsupported(name, c)
        case RetrievalProblem(_, c)             => RetrievalResult.Failed(name, c)
        case _: InterruptedException =>
          Thread.currentThread().interrupt(); RetrievalResult.Failed(name, "stage-interrupted")
        case NonFatal(_) => RetrievalResult.Failed(name, "invalid-or-unavailable-evidence")
      }
    val outcome = result match {
      case RetrievalResult.Ready(_)          => "ready"
      case RetrievalResult.Missing(_, _)     => "missing"
      case RetrievalResult.Unsupported(_, _) => "unsupported"
      case RetrievalResult.Failed(_, _)      => "failed"
    }
    RuntimeStageLog.outcome(
      name,
      input.plan.planId,
      input.plan.provenance.runId,
      outcome,
      Some(input.plan.planId)
    )
    result
  }
  def check(test: Boolean, code: String): Unit =
    if (!test) throw RetrievalProblem("failed", code)
  def window(input: RetrievalInput, config: RuntimeConfig): String = {
    val ids = input.plan.runtime.toVector.flatMap(_.windowIds)
    if (ids.isEmpty || !ids.forall(config.windowIds.contains))
      throw RetrievalProblem("unsupported", "window-not-stored")
    ids.head
  }
  final case class Metric(
      record: ResearcherMetricRecord,
      detail: ResearcherMetricsDetail,
      qualifications: ujson.Value
  )
  def metric(store: ResearcherMetricStore, id: String, window: String): Metric = {
    val r = value(store.get(id, window))
    val d = upickle.default.read[ResearcherMetricsDetail](r.payloadJson)
    check(
      r.researcherId == id && r.windowId == window && d.researcherId == id &&
        d.context.windowId
          .contains(window) && d.context.runId == r.runId && d.policyVersion == r.metricVersion &&
        SparkAnalyticsValidation.check(d).isRight,
      "metric-source-mismatch"
    )
    Metric(r, d, ujson.read(r.qualificationsJson))
  }
  def filters(plan: QueryPlan): RuntimePopulationFilter = RuntimePopulationFilter(
    plan.topicFilters,
    plan.institutionFilters,
    plan.venueFilters
  )
}

private[rag] object RuntimeEvidenceItems {
  def number(field: String, n: Long): RuntimeClaimValue =
    RuntimeClaimValue(field, number = Some(n.toString))
  def decimal(field: String, n: Double): RuntimeClaimValue =
    RuntimeClaimValue(field, number = Some(java.lang.Double.toString(n)))
  def text(field: String, s: String): RuntimeClaimValue = RuntimeClaimValue(field, text = Some(s))
  def ids(field: String, xs: Vector[String]): RuntimeClaimValue =
    RuntimeClaimValue(field, ids = Some(xs.distinct))
  def flag(field: String, b: Boolean): RuntimeClaimValue = RuntimeClaimValue(field, flag = Some(b))
  def ref(table: String, key: String, field: String = "*"): SummarySourceRef =
    SummarySourceRef(table, key, field)

  def make(
      input: RetrievalInput,
      kind: String,
      subjects: Vector[String],
      windows: Vector[String],
      run: String,
      values: Vector[RuntimeClaimValue],
      refs: Vector[SummarySourceRef],
      metricVersion: Option[String] = None,
      converged: Option[Boolean] = None,
      iterations: Option[Int] = None,
      approximate: Boolean = false,
      evidenceType: EvidenceType = EvidenceType.ResearcherProfile,
      graphPath: Option[Vector[String]] = None,
      metricLocator: Option[MetricEvidenceLocator] = None,
      edgeLocator: Option[String] = None,
      descriptive: Boolean = false,
      excerpt: Option[String] = None,
      sourceUri: Option[String] = None,
      sourceContext: Option[SparkRecordContext] = None,
      sourceProvenance: Option[Provenance] = None
  ): EvidenceItem = {
    val runtime = RuntimeEvidence(
      subjects.distinct,
      windows.distinct,
      metricVersion,
      run,
      text("kind", kind) +: values,
      refs.distinct,
      converged,
      iterations,
      approximate,
      descriptive,
      sourceContext = sourceContext
    )
    val provenance = sourceProvenance.getOrElse(
      Provenance(
        SchemaVersions.domain,
        SourceType.ScholarChain,
        StorageKeys
          .composite(kind, refs.map(r => s"${r.table}:${r.rowKey}:${r.field}").mkString("|")),
        sourceUri,
        sourceContext.map(_.lineage.hadoopSnapshot).getOrElse(run),
        None,
        None,
        run,
        Vector("Derived from stored source records; request provenance is retained separately.")
      )
    )
    val item = EvidenceItem(
      "profile:" + ("0" * 64),
      SchemaVersions.domain,
      evidenceType,
      None,
      sourceUri.getOrElse(s"artifact:$run:$kind"),
      None,
      graphPath,
      metricLocator,
      edgeLocator,
      1.0,
      excerpt,
      provenance,
      Some(runtime)
    )
    // The shared helper binds the complete immutable payload, run/window and source references.
    RuntimeEvidenceIds.bind(item).toOption.get
  }
  def metric(
      input: RetrievalInput,
      m: ResearcherMetricsDetail,
      config: RuntimeConfig,
      values: Vector[RuntimeClaimValue],
      kind: String = "metrics",
      membership: Option[CommunityMembership] = None
  ): EvidenceItem = {
    val window = config.windows.find(_.windowId == m.context.windowId.get).get
    make(
      input,
      kind,
      Vector(m.researcherId),
      Vector(window.windowId),
      m.context.runId,
      values,
      Vector(ref("metrics/type=researcher_collaboration", m.researcherId)),
      Some(m.policyVersion),
      membership.map(_.converged),
      membership.map(_.iterations),
      evidenceType = EvidenceType.Metric,
      metricLocator = Some(
        MetricEvidenceLocator(
          m.researcherId,
          input.plan.rankingMetric.getOrElse(CollaborationMetric.DistinctCoauthorCount),
          window.legacyWindow.startYear,
          window.legacyWindow.endYear,
          m.policyVersion
        )
      ),
      sourceContext = Some(m.context)
    )
  }
  def metricValues(m: ResearcherMetricsDetail): Vector[RuntimeClaimValue] = Vector(
    number("publicationCount", m.publicationCount),
    number("distinctCoauthorCount", m.distinctCoauthorCount),
    number("totalCoauthorOccurrences", m.totalCoauthorOccurrences),
    decimal("averageCoauthorsPerPaper", m.averageCoauthorsPerPaper),
    number("maximumCoauthorsOnOnePaper", m.maximumCoauthorsOnOnePaper),
    ids("maxTeamWorkIds", m.maxTeamWorkIds),
    number("maxTeamWorkTieCount", m.maxTeamWorkTieCount),
    number("weightedDegree", m.weightedDegree),
    text("componentId", m.componentId)
  ) ++ m.communityId.map(text("communityId", _)) ++ m.coreness.map(x =>
    number("coreness", x.toLong)
  )
  def edge(input: RetrievalInput, record: RuntimeEdgeRecord): EvidenceItem = {
    val e = record.edge
    RuntimeRead.check(
      SparkAnalyticsValidation
        .check(e)
        .isRight && record.support.size.toLong == e.jointPublicationCount &&
        record.support
          .map(_.workId)
          .distinct
          .size == record.support.size && record.support.forall(s =>
          SparkAnalyticsValidation
            .check(s)
            .isRight && s.edgeId == e.edgeId && s.context.runId == e.context.runId && s.context.windowId == e.context.windowId
        ),
      "edge-support-mismatch"
    )
    val values = Vector(
      text("researcherA", e.researcherA),
      text("researcherB", e.researcherB),
      number("jointPublicationCount", e.jointPublicationCount),
      ids("workIds", record.support.map(_.workId).sorted)
    ) ++
      record.support
        .sortBy(_.workId)
        .map(s =>
          s.year
            .map(y => number(s"year:${s.workId}", y.toLong))
            .getOrElse(text(s"year:${s.workId}", "unknown"))
        )
    make(
      input,
      "edge",
      Vector(e.researcherA, e.researcherB),
      e.context.windowId.toVector,
      e.context.runId,
      values,
      Vector(ref("edges/type=coauthored_with", e.edgeId)) ++ record.support.map(s =>
        ref("edges/type=coauthored_with_support", StorageKeys.support(s.edgeId, s.workId))
      ),
      Some(e.policyVersion),
      evidenceType = EvidenceType.CoauthorEdge,
      edgeLocator = Some(e.edgeId),
      sourceContext = Some(e.context)
    )
  }
}

/** Explicit JSON data encoding prevents retrieved delimiters from acquiring instruction positions.
  * UTF-8 bytes are a conservative tokenizer-independent upper bound (one byte per token). The
  * prompt context omits duplicated storage provenance; immutable evidence retains it in full.
  */
object EvidenceContext {
  private def view(item: EvidenceItem): ujson.Value = {
    val r = item.runtime.get
    val isEdge = r.values.exists(v => v.field == "kind" && v.text.contains("edge"))
    val result = ujson.Obj(
      "evidenceId" -> item.evidenceId,
      "type" -> item.evidenceType.wire,
      "subjects" -> ujson.Arr.from(
        if (
          r.values
            .exists(v => v.field == "kind" && v.text.contains("edge")) || item.graphPath.isDefined
        )
          Vector.empty
        else r.subjectIds
      ),
      "windows" -> ujson.Arr.from(r.windowIds),
      "runId" -> r.runId,
      "values" -> ujson.Obj.from(
        // Per-work detail of an edge (work ids and one year per work) is omitted from the model
        // view: the edge row keeps its joint publication count, the stored evidence keeps every
        // work, and a claim over those fields is still verified against the stored item.
        r.values
          .filterNot(v => isEdge && (v.field == "workIds" || v.field.startsWith("year:")))
          .map(v =>
            v.field -> v.number
              .map(ujson.Str(_))
              .orElse(v.text.map(ujson.Str(_)))
              .orElse(v.ids.map(xs => ujson.Arr.from(xs)))
              .orElse(v.flag.map(ujson.Bool(_)))
              .get
          )
      ),
      "approximate" -> r.approximate,
      "descriptive" -> r.descriptive,
      "excerpt" -> item.text.map(ujson.Str(_)).getOrElse(ujson.Null)
    )
    r.metricVersion.foreach(v => result("metricVersion") = v)
    r.converged.foreach(v => result("converged") = v)
    r.iterations.foreach(v => result("iterations") = v)
    if (result("subjects").arr.isEmpty) result.obj.remove("subjects")
    if (item.text.isEmpty) result.obj.remove("excerpt")
    result
  }
  def render(items: Vector[EvidenceItem]): String = render(items, Vector.empty)
  def render(items: Vector[EvidenceItem], candidates: Vector[ResearcherCandidate]): String = {
    val runs = (items.flatMap(_.runtime.map(_.runId)) ++ candidates.flatMap(_.runIds)).distinct
    val windows = items.flatMap(_.runtime.toVector.flatMap(_.windowIds)).distinct
    val versions = items.flatMap(_.runtime.flatMap(_.metricVersion)).distinct
    val compactItems = items.map { item =>
      val data = view(item).obj
      val runtime = item.runtime.get
      data.remove("runId"); data.remove("windows"); data.remove("metricVersion")
      data("run") = ujson.Num(runs.indexOf(runtime.runId))
      data("windows") = ujson.Arr.from(runtime.windowIds.map(w => ujson.Num(windows.indexOf(w))))
      runtime.metricVersion.foreach(v => data("metricVersion") = ujson.Num(versions.indexOf(v)))
      if (!runtime.approximate) data.remove("approximate")
      // Deterministic types are the default; descriptive excerpts remain explicitly labeled true.
      if (!runtime.descriptive) data.remove("descriptive")
      ujson.Obj.from(data)
    }
    // Model view only: source IDs and evidence references are provenance, not claim material. The
    // persisted bundle and the audit keep every resolved candidate in full; only the identifier,
    // name, run and confidence reach the model, which keeps two-researcher path questions in budget.
    val identities = candidates.map { candidate =>
      val value = ujson.Obj(
        "researcherId" -> candidate.researcherId,
        "displayName" -> candidate.displayName,
        "runs" -> ujson.Arr.from(candidate.runIds.map(r => ujson.Num(runs.indexOf(r)))),
        "confidence" -> candidate.confidence.map(ujson.Num(_)).getOrElse(ujson.Null)
      )
      candidate.provenanceSummary
        .filter(_.truncated)
        .foreach(s => value("provenanceSummary") = upickle.default.writeJs(s))
      value
    }
    val json = ujson
      .Obj(
        "runIds" -> ujson.Arr.from(runs),
        "windowIds" -> ujson.Arr.from(windows),
        "metricVersions" -> ujson.Arr.from(versions),
        "identities" -> ujson.Arr.from(identities),
        "items" -> ujson.Arr.from(compactItems)
      )
      .render()
    "<untrusted_evidence_json>\n" + json
      .replace("<", "\\u003c")
      .replace(">", "\\u003e") + "\n</untrusted_evidence_json>"
  }
  def render(bundle: EvidenceBundle): String =
    render(bundle.items, bundle.runtime.toVector.flatMap(_.resolvedCandidates))
  def tokenUpperBound(items: Vector[EvidenceItem]): Int = tokenUpperBound(items, Vector.empty)
  def tokenUpperBound(items: Vector[EvidenceItem], candidates: Vector[ResearcherCandidate]): Int =
    render(items, candidates).getBytes(UTF_8).length
}

/** Stored display names for researcher ids that answer text will show. The source is the stored
  * graph node label only, so a model can never introduce or change an identity.
  */
private[rag] object RuntimeNames {
  private val researcherPrefix = "researcher:"
  def isResearcherId(id: String): Boolean = id.startsWith(researcherPrefix)

  /** Subjects first, then ids-typed values, in evidence order and without duplicates. Edge items
    * are included (a repeated-collaboration ranking renders their endpoints); the caller's cap
    * keeps the lookup bounded, and the main item's ids come first so they win under the cap.
    */
  def renderedResearcherIds(bundle: EvidenceBundle): Vector[String] =
    bundle.items
      .flatMap(_.runtime)
      .filterNot(_.descriptive)
      .flatMap(r => r.subjectIds ++ r.values.flatMap(_.ids.toVector.flatten))
      .filter(isResearcherId)
      .distinct

  /** Control and format characters (bidi marks, zero-width characters) are removed, whitespace is
    * collapsed. A label that mimics rendering syntax (an id prefix or the path arrow) is refused so
    * a stored name cannot forge ids or extra path steps in answer text.
    */
  def clean(label: String): Option[String] = {
    val text = label
      .replaceAll("[\\p{Cf}]", "")
      .replaceAll("[\\p{Cc}\\s]+", " ")
      .trim
    Option.when(
      text.nonEmpty && text.length <= 200 && !text
        .toLowerCase(java.util.Locale.ROOT)
        .contains(researcherPrefix) && !text.contains("→")
    )(text)
  }

  /** A failed lookup (missing, rejected, thrown) is simply no name. */
  def read(graph: GraphReader, id: String): Option[String] =
    try
      StorageResult.value(graph.node(id)).filter(n => n.nodeId == id).flatMap(n => clean(n.label))
    catch { case scala.util.control.NonFatal(_) => None }
}
