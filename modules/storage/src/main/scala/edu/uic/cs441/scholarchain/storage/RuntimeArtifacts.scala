package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.util.control.NonFatal
import upickle.default.{ReadWriter, read}
import StorageResult.*

/** Read-only runtime access to immutable, source-verified Phase 6 records. */
trait RuntimeArtifactStore {
  def rank(
      windowId: String,
      metric: RuntimeRankingMetric,
      filters: RuntimePopulationFilter,
      limit: Int
  ): StorageResult[RuntimeRankingPage]
  def communitySummary(communityId: String, windowId: String): StorageResult[CommunitySummary]
  def bridgeMetrics(researcherId: String, windowId: String): StorageResult[RuntimeBridgeRecord]
  def temporalChange(
      researcherId: String,
      fromWindowId: String,
      toWindowId: String
  ): StorageResult[RuntimeTemporalRecord]
  def edgeSupport(edgeId: String, windowId: String): StorageResult[RuntimeEdgeRecord]
  def researcherContext(
      researcherId: String,
      windowId: String,
      limit: Int
  ): StorageResult[RuntimeResearcherContext]
}

final case class RuntimeArtifactConfig(
    maxRows: Int = 10000,
    maxBytes: Int = 16 * 1024 * 1024,
    maxRowBytes: Int = 1024 * 1024,
    maxMetadataBytes: Int = 4 * 1024 * 1024,
    maxResults: Int = 100
) {
  require(maxRows > 0 && maxBytes > 0 && maxRowBytes > 0 && maxMetadataBytes > 0 && maxResults > 0)
}

final case class RuntimeArtifactPointer(key: String, sha256: String, sourceRunId: String)
    derives ReadWriter

private[storage] final case class RuntimeArtifactTable(
    manifest: LoadManifest,
    rows: Vector[ujson.Value]
) derives ReadWriter

private[storage] final case class RuntimeArtifactSnapshot(
    schemaVersion: String,
    context: SparkRecordContext,
    qualificationsJson: String,
    tables: Vector[RuntimeArtifactTable]
) derives ReadWriter

/** This is deliberately a bounded complete-export snapshot, not an unbounded graph collection.
  * Declared and actual row/byte caps both fail closed. Larger corpora need a separately designed
  * partitioned artifact format. No snapshot is advertised as a complete population after a cap.
  */
object Phase6RuntimeArtifacts {
  private[storage] val version = "scholarchain.runtime-artifacts.v1"
  private[storage] val required = Set(
    "nodes/type=researcher",
    "metrics/type=researcher_collaboration",
    "metrics/type=communities",
    "metrics/type=community_summaries",
    "metrics/type=bridges",
    "metrics/type=temporal_changes",
    "edges/type=coauthored_with",
    "edges/type=coauthored_with_support"
  )
  private[storage] val optional = Set(
    "edges/type=authored",
    "edges/type=published_in",
    "edges/type=has_topic",
    "edges/type=affiliated_with",
    "nodes/type=topic",
    "nodes/type=venue",
    "nodes/type=institution"
  )
  private def reject(code: String): Nothing = throw SourceRejected(code)
  private def checked[A](r: StorageResult[A]): A = StorageResult.value(r).getOrElse {
    r match { case Rejected(c) => reject(c); case _ => reject("runtime-source-unavailable") }
  }

  /** Complete Spark row hashes retain Double .0 and exponent spellings. Top-level columns are
    * lexical; nested fields retain the producer schema's order, exactly as Phase6Export does.
    */
  private val doubles = Set(
    "averageCoauthorsPerPaper",
    "participationCoefficient",
    "deltaAverageCoauthorsPerPaper",
    "deltaParticipationCoefficient",
    "communityJaccardOverlap"
  )
  private def render(value: ujson.Value, field: String = ""): String = value match {
    case o: ujson.Obj =>
      o.obj.iterator
        .map((k, v) => ujson.Str(k).render() + ":" + render(v, k))
        .mkString("{", ",", "}")
    case a: ujson.Arr => a.arr.iterator.map(v => render(v)).mkString("[", ",", "]")
    case n: ujson.Num if doubles(field) => java.lang.Double.toString(n.num)
    case other                          => other.render()
  }
  private[storage] def canonicalRow(row: ujson.Value): String =
    render(ujson.Obj.from(row.obj.toVector.filterNot(_._1 == "run_id").sortBy(_._1)))
  private[storage] def tableHash(rows: Vector[ujson.Value]): String =
    hashCanonical(rows.map(canonicalRow))
  private[storage] def hashCanonical(strings: Seq[String]): String = {
    val shards = strings.groupBy(s => StableIds.sha256Hex(s).take(2)).toVector.sortBy(_._1)
    def utf8Before(a: String, b: String): Boolean = {
      val x = a.getBytes(UTF_8); val y = b.getBytes(UTF_8)
      var i = 0
      while (i < math.min(x.length, y.length) && x(i) == y(i)) i += 1
      if (i == math.min(x.length, y.length)) x.length < y.length
      else (x(i) & 255) < (y(i) & 255)
    }
    StableIds.sha256Hex(
      "sha256-fixed-256-shard-sorted-row-json-merkle-v1\n" + shards
        .map { (shard, values) =>
          s"$shard:${values.size}:${StableIds.sha256Hex(values.sortWith(utf8Before).mkString("\n"))}"
        }
        .mkString("\n")
    )
  }

  /** Shared manifest preconditions for the complete and the bounded-subset producers. */
  private[storage] def selectSourceManifests(
      manifests: Vector[LoadManifest]
  ): Vector[LoadManifest] = {
    if (
      manifests.isEmpty || manifests.map(_.logicalDataset).distinct.size != manifests.size ||
      manifests.map(_.context).distinct.size != 1 ||
      !required.subsetOf(manifests.map(_.logicalDataset).toSet)
    ) reject("invalid-runtime-source-manifests")
    val selected =
      manifests.filter(m => (required ++ optional)(m.logicalDataset)).sortBy(_.logicalDataset)
    if (
      selected.exists(m =>
        SparkAnalyticsValidation.check(m).isLeft || m.targetStore != "s3" || m.format != "parquet"
      )
    ) reject("invalid-runtime-source-manifests")
    selected
  }

  def materialize(
      root: Path,
      objects: ObjectStore,
      key: String,
      config: RuntimeArtifactConfig = RuntimeArtifactConfig()
  ): StorageResult[RuntimeArtifactPointer] = try {
    val base = root.toRealPath()
    val path = base.resolve("load-manifests/s3.json").toRealPath()
    if (!path.startsWith(base) || Files.size(path) > config.maxMetadataBytes)
      Rejected("runtime-source-metadata-bound")
    else {
      val manifests = read[Vector[LoadManifest]](Files.readString(path, UTF_8))
      publish(
        manifests,
        new LocalParquetManifestReader(base, config.maxMetadataBytes),
        objects,
        key,
        config
      )
    }
  } catch { case NonFatal(_) => Rejected("invalid-runtime-source") }

  /** Reader-injected preparation is also used for producer contract fixtures; it never makes a
    * provider call itself. Production uses materialize and its completed local Parquet reader.
    */
  def publish(
      manifests: Vector[LoadManifest],
      reader: ManifestRowReader,
      objects: ObjectStore,
      key: String,
      config: RuntimeArtifactConfig = RuntimeArtifactConfig()
  ): StorageResult[RuntimeArtifactPointer] = try {
    if (!key.contains("/versions/") || key.split('/').contains(".."))
      reject("unversioned-runtime-artifact-key")
    val selected = selectSourceManifests(manifests)
    if (selected.map(m => BigInt(m.rowCount)).sum > config.maxRows)
      reject("runtime-artifact-row-bound")
    val context = selected.head.context
    val qualifications = checked(reader.qualifications(context.runId))
    if (qualifications.getBytes(UTF_8).length > config.maxMetadataBytes)
      reject("runtime-source-metadata-bound")
    val q = ujson.read(qualifications)
    if (
      q("runManifest")("runId").str != context.runId || q("runMetadata")(
        "runId"
      ).str != context.runId
    )
      reject("runtime-source-qualification-mismatch")
    var totalRows = 0
    var totalBytes = 0L
    val tables = selected.map { manifest =>
      val rows = checked(reader.open(manifest))
      val values = Vector.newBuilder[ujson.Value]
      var count = 0
      try
        while (rows.hasNext) {
          val row = rows.next()
          val size = row.render().getBytes(UTF_8).length
          totalRows += 1; count += 1; totalBytes += size
          if (
            size > config.maxRowBytes || totalRows > config.maxRows || totalBytes > config.maxBytes
          )
            reject("runtime-artifact-content-bound")
          if (count > manifest.rowCount) reject("runtime-source-row-count-mismatch")
          values += row
        }
      finally rows.close()
      val result = values.result()
      if (count != manifest.rowCount || tableHash(result) != manifest.sortedRowsSha256)
        reject("runtime-source-logical-hash-mismatch")
      RuntimeArtifactTable(manifest, result)
    }
    val snapshot = RuntimeArtifactSnapshot(version, context, qualifications, tables)
    RuntimeArtifactData.validate(snapshot, config)
    val bytes = CoreJson.compact(snapshot).getBytes(UTF_8).toVector
    if (bytes.size > config.maxBytes) reject("runtime-artifact-byte-bound")
    val pointer = RuntimeArtifactPointer(key, StorageKeys.sha256(bytes), context.runId)
    objects.put(key, bytes, "application/json", Map.empty) match {
      case r if StorageResult.successful(r) =>
        if (r.isInstanceOf[Unchanged[?]]) Unchanged(pointer) else Written(pointer)
      case Rejected(c) => Rejected(c)
      case _           => Rejected("runtime-artifact-publish-failed")
    }
  } catch {
    case SourceRejected(c) => Rejected(c)
    case NonFatal(_)       => Rejected("invalid-runtime-source")
  }
}

/** Slim, provenance-free view of one stored association edge. The runtime artifact reads only these
  * three fields from authored, has_topic, published_in and affiliated_with rows.
  */
private[storage] final case class AssociationRef(edgeId: String, fromId: String, toId: String)

/** The typed rows behind the runtime artifact. A snapshot is decoded into this shape, and the local
  * export loader, which never serializes a snapshot, builds it directly. Both feed the one query
  * implementation below.
  */
private[storage] final case class RuntimeArtifactRows(
    windows: Set[String],
    presentTables: Set[String],
    researcherIds: Set[String],
    metrics: Vector[ResearcherMetricsDetail],
    bridges: Vector[ResearcherBridgeMetrics],
    memberships: Vector[CommunityMembership],
    summaries: Vector[CommunitySummary],
    changes: Vector[TemporalChange],
    edges: Vector[SparkCoauthorEdge],
    supports: Vector[CoauthorEdgeSupport],
    authored: Vector[AssociationRef],
    hasTopic: Vector[AssociationRef],
    publishedIn: Vector[AssociationRef],
    affiliatedWith: Vector[AssociationRef]
)

private[storage] object RuntimeArtifactRows {
  def fromSnapshot(snapshot: RuntimeArtifactSnapshot): RuntimeArtifactRows = {
    val tables = snapshot.tables.map(t => t.manifest.logicalDataset -> t.rows).toMap
    def rows[A: ReadWriter](name: String): Vector[A] =
      tables.getOrElse(name, Vector.empty).map(v => read[A](v))
    def refs(name: String): Vector[AssociationRef] =
      rows[GraphEdge](name).map(e => AssociationRef(e.edgeId, e.fromId, e.toId))
    RuntimeArtifactRows(
      snapshot.tables.head.manifest.windows.toSet,
      tables.keySet,
      rows[GraphNode]("nodes/type=researcher").map(_.nodeId).toSet,
      rows[ResearcherMetricsDetail]("metrics/type=researcher_collaboration"),
      rows[ResearcherBridgeMetrics]("metrics/type=bridges"),
      rows[CommunityMembership]("metrics/type=communities"),
      rows[CommunitySummary]("metrics/type=community_summaries"),
      rows[TemporalChange]("metrics/type=temporal_changes"),
      rows[SparkCoauthorEdge]("edges/type=coauthored_with"),
      rows[CoauthorEdgeSupport]("edges/type=coauthored_with_support"),
      refs("edges/type=authored"),
      refs("edges/type=has_topic"),
      refs("edges/type=published_in"),
      refs("edges/type=affiliated_with")
    )
  }
}

private[storage] final class RuntimeArtifactData(
    val data: RuntimeArtifactRows,
    val pointer: RuntimeArtifactPointer,
    config: RuntimeArtifactConfig
) extends RuntimeArtifactStore {
  private val metrics = data.metrics
  private val bridges = data.bridges
  private val memberships = data.memberships
  private val summaries = data.summaries
  private val changes = data.changes
  private val edges = data.edges
  private val supports = data.supports
  private val storedWindows = data.windows
  private val researcherIds = data.researcherIds
  private val metricsByResearcherWindow =
    metrics.map(m => (m.researcherId, m.context.windowId.get) -> m).toMap
  private val metricsByWindow = metrics.groupBy(_.context.windowId.get)
  private val bridgesByResearcherWindow =
    bridges.map(b => (b.researcherId, b.context.windowId.get) -> b).toMap
  private val membershipsByResearcherWindow =
    memberships.map(m => (m.researcherId, m.context.windowId.get) -> m).toMap
  private val summariesByCommunityWindow =
    summaries.map(s => (s.communityId, s.context.windowId.get) -> s).toMap
  private val changesByResearcherWindows =
    changes.map(c => (c.researcherId, c.fromWindowId, c.toWindowId) -> c).toMap
  private val edgesByIdWindow = edges.map(e => (e.edgeId, e.context.windowId.get) -> e).toMap
  private val supportsByEdgeWindow = supports.groupBy(s => (s.edgeId, s.context.windowId.get))
  private val edgesByResearcherWindow = edges
    .flatMap { e =>
      Vector(
        (e.researcherA, e.context.windowId.get) -> e,
        (e.researcherB, e.context.windowId.get) -> e
      )
    }
    .groupMap(_._1)(_._2)
  // Index source relations without materializing the potentially quadratic researcher/work/topic
  // join. Each query traverses only the researcher's authored works and those subjects' relations.
  private val authoredByResearcher = data.authored.groupBy(_.fromId)
  private val associationTableNames =
    Vector("edges/type=has_topic", "edges/type=published_in", "edges/type=affiliated_with")
  private val associationsByTableSubject = Map(
    "edges/type=has_topic" -> data.hasTopic.groupBy(_.fromId),
    "edges/type=published_in" -> data.publishedIn.groupBy(_.fromId),
    "edges/type=affiliated_with" -> data.affiliatedWith.groupBy(_.fromId)
  )
  private def sourceAssociations(id: String, dataset: String): Vector[AssociationRef] = {
    val bySubject = associationsByTableSubject(dataset)
    if (dataset == "edges/type=affiliated_with") bySubject.getOrElse(id, Vector.empty)
    else
      authoredByResearcher
        .getOrElse(id, Vector.empty)
        .map(_.toId)
        .distinct
        .sorted
        .flatMap(work => bySubject.getOrElse(work, Vector.empty))
  }
  private def member(id: String, w: String): Option[CommunityMembership] =
    membershipsByResearcherWindow.get((id, w))
  private def association(id: String, field: String): Option[Vector[String]] = {
    val dataset = field match {
      case "topic" => "edges/type=has_topic"
      case "venue" => "edges/type=published_in"
      case _       => "edges/type=affiliated_with"
    }
    if (!data.presentTables(dataset)) None
    else {
      val found = sourceAssociations(id, dataset).map(_.toId).distinct.sorted
      // No association row is missing evidence, not proof of a known empty association set.
      if (found.isEmpty) None else Some(found)
    }
  }
  private def numeric(metric: RuntimeRankingMetric, m: ResearcherMetricsDetail): Option[String] = {
    val b = bridgesByResearcherWindow.get((m.researcherId, m.context.windowId.get))
    metric match {
      case RuntimeRankingMetric.PublicationCount      => Some(m.publicationCount.toString)
      case RuntimeRankingMetric.DistinctCoauthorCount => Some(m.distinctCoauthorCount.toString)
      case RuntimeRankingMetric.TotalCoauthorOccurrences =>
        Some(m.totalCoauthorOccurrences.toString)
      case RuntimeRankingMetric.AverageCoauthorsPerPaper =>
        Some(java.lang.Double.toString(m.averageCoauthorsPerPaper))
      case RuntimeRankingMetric.MaximumCoauthorsOnOnePaper =>
        Some(m.maximumCoauthorsOnOnePaper.toString)
      case RuntimeRankingMetric.WeightedDegree       => Some(m.weightedDegree.toString)
      case RuntimeRankingMetric.Coreness             => m.coreness.map(_.toString)
      case RuntimeRankingMetric.CrossCommunityDegree => b.map(_.crossCommunityDegree.toString)
      case RuntimeRankingMetric.CrossCommunityWeight => b.map(_.crossCommunityWeight.toString)
      case RuntimeRankingMetric.CommunitiesConnected => b.map(_.communitiesConnected.toString)
      case RuntimeRankingMetric.ParticipationCoefficient =>
        b.map(x => java.lang.Double.toString(x.participationCoefficient))
    }
  }

  def rank(
      w: String,
      metric: RuntimeRankingMetric,
      filters: RuntimePopulationFilter,
      limit: Int
  ): StorageResult[RuntimeRankingPage] = {
    if (limit <= 0 || limit > config.maxResults) return Rejected("runtime-result-bound")
    if (filters.metricScope != "population") return Rejected("unsupported-filtered-metric-scope")
    val population = metricsByWindow.getOrElse(w, Vector.empty)
    if (!storedWindows(w))
      return Rejected("unsupported-runtime-window")
    val requested = Vector(
      "topic" -> filters.topicIds,
      "institution" -> filters.institutionIds,
      "venue" -> filters.venueIds
    ).filter(_._2.nonEmpty)
    if (
      requested
        .exists((field, _) => population.exists(m => association(m.researcherId, field).isEmpty))
    )
      return Rejected("unsupported-authoritative-filter-metadata")
    val matched = population.filter(m =>
      requested.forall((field, ids) =>
        association(m.researcherId, field).exists(v => ids.exists(v.contains))
      )
    )
    if (matched.exists(m => numeric(metric, m).isEmpty))
      return Rejected("unsupported-runtime-metric")
    val bridgeMetric = Set(
      RuntimeRankingMetric.CrossCommunityDegree,
      RuntimeRankingMetric.CrossCommunityWeight,
      RuntimeRankingMetric.CommunitiesConnected,
      RuntimeRankingMetric.ParticipationCoefficient
    )(metric)
    if (bridgeMetric && matched.exists(m => member(m.researcherId, w).isEmpty))
      return Rejected("missing-runtime-community-qualification")
    // At most limit selected entries remain in the selection buffer, after authoritative filters.
    var selected = Vector.empty[RuntimeRankingEntry]
    matched.foreach { m =>
      val entry = RuntimeRankingEntry(
        m,
        bridgesByResearcherWindow.get((m.researcherId, w)),
        member(m.researcherId, w),
        numeric(metric, m).get
      )
      selected = (selected :+ entry)
        .sortWith { (a, b) =>
          val compare = BigDecimal(a.rankingValue).compare(BigDecimal(b.rankingValue))
          if (compare == 0) a.metric.researcherId < b.metric.researcherId else compare > 0
        }
        .take(limit)
    }
    Found(
      RuntimeRankingPage(
        w,
        metric,
        filters,
        selected,
        population.size.toLong,
        matched.size.toLong,
        matched.size > limit,
        pointer.sourceRunId,
        pointer.sha256
      )
    )
  }
  def communitySummary(id: String, w: String): StorageResult[CommunitySummary] =
    summariesByCommunityWindow
      .get((id, w))
      .map(Found(_))
      .getOrElse(Missing)
  def bridgeMetrics(id: String, w: String): StorageResult[RuntimeBridgeRecord] = {
    val value = for {
      b <- bridgesByResearcherWindow.get((id, w))
      m <- member(id, w)
      d <- metricsByResearcherWindow.get((id, w))
    } yield RuntimeBridgeRecord(b, m, d.distinctCoauthorCount)
    value.map(Found(_)).getOrElse(Missing)
  }
  def temporalChange(id: String, from: String, to: String): StorageResult[RuntimeTemporalRecord] =
    changesByResearcherWindows
      .get((id, from, to))
      .map(c => Found(RuntimeTemporalRecord(c, member(id, from), member(id, to))))
      .getOrElse(Missing)
  def edgeSupport(id: String, w: String): StorageResult[RuntimeEdgeRecord] =
    edgesByIdWindow
      .get((id, w))
      .map(e => Found(RuntimeEdgeRecord(e, supportsByEdgeWindow.getOrElse((id, w), Vector.empty))))
      .getOrElse(Missing)
  def researcherContext(
      id: String,
      w: String,
      limit: Int
  ): StorageResult[RuntimeResearcherContext] = {
    if (limit <= 0 || limit > config.maxResults) return Rejected("runtime-result-bound")
    if (!storedWindows(w)) return Rejected("unsupported-runtime-window")
    if (!researcherIds(id) || !metricsByResearcherWindow.contains((id, w))) return Missing
    val localEdges = edgesByResearcherWindow.getOrElse((id, w), Vector.empty)
    val coauthors = localEdges
      .map(e => if (e.researcherA == id) e.researcherB else e.researcherA)
      .distinct
      .sorted
    val selectedCoauthors = coauthors.take(limit).toSet
    val coauthorRefs = localEdges
      .filter(e =>
        (e.researcherA == id && selectedCoauthors(e.researcherB)) ||
          (e.researcherB == id && selectedCoauthors(e.researcherA))
      )
      .sortBy(_.edgeId)
      .map(e =>
        SummarySourceRef(
          "edges/type=coauthored_with",
          e.edgeId,
          if (e.researcherA == id) "researcherB" else "researcherA"
        )
      )
    val authored = authoredByResearcher.getOrElse(id, Vector.empty)
    val associationRefs =
      associationTableNames
        .flatMap(name =>
          sourceAssociations(id, name)
            .map(e => SummarySourceRef(name, e.edgeId, "toId"))
        )
    Found(
      RuntimeResearcherContext(
        id,
        w,
        association(id, "topic"),
        association(id, "institution"),
        association(id, "venue"),
        coauthors.take(limit),
        coauthors.size > limit,
        Vector(SummarySourceRef("nodes/type=researcher", id, "nodeId")) ++ coauthorRefs ++
          authored.map(e =>
            SummarySourceRef("edges/type=authored", e.edgeId, "toId")
          ) ++ associationRefs,
        pointer.sourceRunId
      )
    )
  }
}

private[storage] object RuntimeArtifactData {
  private def reject(code: String): Nothing = throw SourceRejected(code)
  def validate(s: RuntimeArtifactSnapshot, config: RuntimeArtifactConfig): Unit = {
    validated(s, config); ()
  }

  /** Same checks as `validate`; also returns the decoded typed rows. */
  def validated(s: RuntimeArtifactSnapshot, config: RuntimeArtifactConfig): RuntimeArtifactRows = {
    if (
      s.schemaVersion != Phase6RuntimeArtifacts.version || s.tables
        .map(_.manifest.logicalDataset)
        .distinct
        .size != s.tables.size ||
      !Phase6RuntimeArtifacts.required.subsetOf(s.tables.map(_.manifest.logicalDataset).toSet) ||
      s.tables.map(t => BigInt(t.rows.size)).sum > config.maxRows
    )
      reject("invalid-runtime-artifact")
    val run = s.context.runId
    val qualifications = ujson.read(s.qualificationsJson)
    if (
      s.qualificationsJson.getBytes(UTF_8).length > config.maxMetadataBytes ||
      qualifications("runManifest")("runId").str != run || qualifications("runMetadata")(
        "runId"
      ).str != run
    )
      reject("runtime-source-qualification-mismatch")
    if (s.tables.map(_.manifest.windows).distinct.size != 1)
      reject("runtime-artifact-window-mismatch")
    s.tables.foreach { table =>
      val m = table.manifest
      if (
        m.context != s.context || m.rowCount != table.rows.size || SparkAnalyticsValidation
          .check(m)
          .isLeft || m.targetStore != "s3" || m.format != "parquet" ||
        Phase6RuntimeArtifacts.tableHash(table.rows) != m.sortedRowsSha256
      ) reject("runtime-artifact-table-mismatch")
      table.rows.foreach { row =>
        if (row.render().getBytes(UTF_8).length > config.maxRowBytes)
          reject("runtime-artifact-row-byte-bound")
        def spark[A: ReadWriter](
            check: A => Either[ConfigError, A],
            context: A => SparkRecordContext
        ): Unit = {
          val value = read[A](row)
          val c = context(value)
          if (
            check(value).isLeft || c.runId != run || c.lineage != s.context.lineage || !c.windowId
              .exists(m.windows.contains)
          )
            reject("runtime-artifact-row-provenance-mismatch")
        }
        m.logicalDataset match {
          case "metrics/type=researcher_collaboration" =>
            spark[ResearcherMetricsDetail](SparkAnalyticsValidation.check, _.context)
          case "metrics/type=bridges" =>
            spark[ResearcherBridgeMetrics](SparkAnalyticsValidation.check, _.context)
          case "metrics/type=communities" =>
            spark[CommunityMembership](SparkAnalyticsValidation.check, _.context)
          case "metrics/type=community_summaries" =>
            spark[CommunitySummary](SparkAnalyticsValidation.check, _.context)
          case "metrics/type=temporal_changes" =>
            spark[TemporalChange](SparkAnalyticsValidation.check, _.context)
          case "edges/type=coauthored_with" =>
            spark[SparkCoauthorEdge](SparkAnalyticsValidation.check, _.context)
          case "edges/type=coauthored_with_support" =>
            spark[CoauthorEdgeSupport](SparkAnalyticsValidation.check, _.context)
          case name if name.startsWith("nodes/") =>
            val value = read[GraphNode](row)
            if (
              DomainValidation.check(value).isLeft || value.provenance.runId != run ||
              value.nodeClass.toString.toLowerCase != name.stripPrefix("nodes/type=")
            ) reject("runtime-artifact-node-mismatch")
          case name if name.startsWith("edges/") =>
            val value = read[GraphEdge](row)
            if (
              DomainValidation.check(value).isLeft || value.provenance.runId != run ||
              value.edgeType.wire.toLowerCase != name.stripPrefix("edges/type=")
            ) reject("runtime-artifact-edge-mismatch")
          case _ => reject("unsupported-runtime-artifact-table")
        }
      }
      val keys = table.rows.map(row =>
        m.keyColumns
          .map(k => row.obj.get(k).map(_.render()).getOrElse("null"))
          .mkString("\u0000") + "\u0000" + row.obj
          .get("context")
          .flatMap(_.obj.get("windowId"))
          .map(_.render())
          .getOrElse("")
      )
      if (keys.distinct.size != keys.size) reject("runtime-artifact-duplicate-source-key")
    }
    val rows = RuntimeArtifactRows.fromSnapshot(s)
    crossCheck(rows)
    rows
  }

  /** Relations between tables, shared by the snapshot path and the local export loader. */
  def crossCheck(rows: RuntimeArtifactRows): Unit = {
    val nodes = rows.researcherIds
    val metrics = rows.metrics
    val memberships = rows.memberships
    val edges = rows.edges
    val supports = rows.supports
    val metricsByKey = metrics.map(m => (m.researcherId, m.context.windowId) -> m).toMap
    val membershipsByKey = memberships.map(m => (m.researcherId, m.context.windowId) -> m).toMap
    val edgeKeys = edges.map(e => (e.edgeId, e.context.windowId)).toSet
    val supportsByEdge = supports.groupBy(s => (s.edgeId, s.context.windowId))
    if (
      metrics.exists(m => !nodes(m.researcherId)) || memberships
        .exists(m => !nodes(m.researcherId)) ||
      edges.exists(e => !nodes(e.researcherA) || !nodes(e.researcherB))
    ) reject("runtime-artifact-missing-researcher")
    rows.bridges.foreach { b =>
      val metric = metricsByKey.get((b.researcherId, b.context.windowId))
      val membership = membershipsByKey.get((b.researcherId, b.context.windowId))
      if (
        metric.isEmpty || membership.isEmpty || b.crossCommunityDegree > metric.get.distinctCoauthorCount ||
        b.crossCommunityWeight > metric.get.weightedDegree || metric.get.communityId != Some(
          membership.get.communityId
        )
      )
        reject("runtime-artifact-bridge-binding-mismatch")
    }
    supports.foreach { support =>
      if (!edgeKeys((support.edgeId, support.context.windowId)))
        reject("runtime-artifact-orphan-support")
    }
    edges.foreach { edge =>
      val support = supportsByEdge.getOrElse((edge.edgeId, edge.context.windowId), Vector.empty)
      val workIds = support.map(_.workId).toSet
      if (
        support.size.toLong != edge.jointPublicationCount ||
        !edge.representativeWorkIds.forall(workIds)
      )
        reject("runtime-artifact-edge-support-mismatch")
    }
  }
}

/** This reader uses ObjectStore reads only. The immutable SHA-bound snapshot is validated and
  * indexed once per instance after a successful load. Failed loads are never cached, so missing
  * objects, transient failures and initially corrupt responses can be retried without replacing the
  * adapter. Concurrent cold calls share one synchronized load; warm calls use immutable data.
  */
final class ObjectStoreRuntimeArtifactStore(
    objects: ObjectStore,
    pointer: RuntimeArtifactPointer,
    config: RuntimeArtifactConfig = RuntimeArtifactConfig()
) extends RuntimeArtifactStore {
  private var cachedData: Option[RuntimeArtifactData] = None

  private def load(): StorageResult[RuntimeArtifactData] = try {
    if (!pointer.key.contains("/versions/") || !pointer.sha256.matches("[0-9a-f]{64}"))
      Rejected("invalid-runtime-artifact-pointer")
    else
      RowCodec.map(objects.get(pointer.key)) { stored =>
        if (
          stored.head.key != pointer.key || stored.bytes.size > config.maxBytes || stored.head.size != stored.bytes.size ||
          stored.head.sha256 != pointer.sha256 || StorageKeys.sha256(stored.bytes) != pointer.sha256
        )
          Rejected("runtime-artifact-content-mismatch")
        else {
          val snapshot = read[RuntimeArtifactSnapshot](new String(stored.bytes.toArray, UTF_8))
          val rows = RuntimeArtifactData.validated(snapshot, config)
          if (snapshot.context.runId != pointer.sourceRunId)
            Rejected("runtime-artifact-run-mismatch")
          else Found(new RuntimeArtifactData(rows, pointer, config))
        }
      }
  } catch {
    case SourceRejected(c) => Rejected(c)
    case NonFatal(_)       => Rejected("invalid-runtime-artifact")
  }
  private def verifiedData(): StorageResult[RuntimeArtifactData] = synchronized {
    cachedData match {
      case Some(data) => Found(data)
      case None =>
        val result = load()
        StorageResult.value(result).foreach(data => cachedData = Some(data))
        result
    }
  }
  private def withData[A](f: RuntimeArtifactStore => StorageResult[A]): StorageResult[A] =
    RowCodec.map(verifiedData())(f)
  def rank(
      w: String,
      m: RuntimeRankingMetric,
      f: RuntimePopulationFilter,
      l: Int
  ): StorageResult[RuntimeRankingPage] = withData(_.rank(w, m, f, l))
  def communitySummary(id: String, w: String): StorageResult[CommunitySummary] = withData(
    _.communitySummary(id, w)
  )
  def bridgeMetrics(id: String, w: String): StorageResult[RuntimeBridgeRecord] = withData(
    _.bridgeMetrics(id, w)
  )
  def temporalChange(id: String, from: String, to: String): StorageResult[RuntimeTemporalRecord] =
    withData(_.temporalChange(id, from, to))
  def edgeSupport(id: String, w: String): StorageResult[RuntimeEdgeRecord] = withData(
    _.edgeSupport(id, w)
  )
  def researcherContext(id: String, w: String, l: Int): StorageResult[RuntimeResearcherContext] =
    withData(_.researcherContext(id, w, l))
}
