package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.collection.mutable
import scala.util.control.NonFatal
import upickle.default.{ReadWriter, read}
import StorageResult.*

/** A refused local load. `code` is a closed, value-free reason; `part` names the export part that
  * was being read (for example `manifests`, `table:edges/type=coauthored_with`, `cache`,
  * `runtime-artifact`). `detail` carries only names and counts, never file contents.
  */
final case class LocalExportError(code: String, part: String, detail: String = "")

object LocalExportError {
  val exportDirectoryMissing = "export-directory-missing"
  val sourceRunIncomplete = "incomplete-or-corrupt-source-run"
  val invalidManifests = "invalid-source-manifests"
  val missingTable = "missing-source-table"
  val exportTooLarge = "export-exceeds-limits"
  val rowCountMismatch = "row-count-mismatch"
  val contentHashMismatch = "source-content-hash-mismatch"
  val rowTooLarge = "source-row-too-large"
  val invalidRow = "invalid-source-row"
  val runMismatch = "row-run-mismatch"
  val duplicateKey = "duplicate-source-key"
  val missingEndpoint = "missing-edge-endpoint"
  val invalidExport = "invalid-export"
}

/** Application bounds for the local load. The defaults hold the Phase 15 size-S export (about 1.0
  * million source rows). Nothing is silently truncated: an export above a bound is refused.
  *
  * @param maxRows
  *   upper bound on the summed manifest row counts of every table the loader reads
  * @param maxRowBytes
  *   upper bound on one row's UTF-8 JSON size
  * @param maxMetadataBytes
  *   upper bound on each metadata file
  * @param subsetArtifact
  *   caps of the bounded runtime artifact built for an include-ids scope
  */
final case class LocalExportLimits(
    maxRows: Long = 2000000L,
    maxRowBytes: Int = 1024 * 1024,
    maxMetadataBytes: Int = 4 * 1024 * 1024,
    subsetArtifact: RuntimeArtifactConfig = RuntimeArtifactConfig()
) {
  require(maxRows > 0 && maxRowBytes > 0 && maxMetadataBytes > 0)
}

/** Which rows the runtime artifact answers about. */
sealed trait RuntimeArtifactScope
object RuntimeArtifactScope {

  /** Every researcher and relation of the export, served from typed in-memory rows (default). */
  case object WholeExport extends RuntimeArtifactScope

  /** The deterministic bounded subset of `RuntimeArtifactSubset`, serialized as the same immutable
    * snapshot the AWS runtime reads, inside the subset caps of `LocalExportLimits.subsetArtifact`.
    */
  final case class IncludeIds(list: IncludeList) extends RuntimeArtifactScope
}

/** @param verifySourceHashes
  *   recompute every loaded table's logical content hash and compare it with its manifest
  * @param validateNeptuneCsv
  *   also run `NeptuneExportValidator` over the sidecar CSV (hashes all ~450 MB, needs scratch
  *   disk)
  * @param scratchDirectory
  *   parent of the temporary scratch the cache loader and the CSV validator use
  * @param progress
  *   receives one short line per load phase
  */
final case class LocalExportOptions(
    limits: LocalExportLimits = LocalExportLimits(),
    artifactScope: RuntimeArtifactScope = RuntimeArtifactScope.WholeExport,
    verifySourceHashes: Boolean = true,
    validateNeptuneCsv: Boolean = false,
    scratchDirectory: Option[Path] = None,
    progress: String => Unit = _ => ()
)

final case class LocalExportTableProvenance(
    dataset: String,
    rowCount: Long,
    sortedRowsSha256: String,
    hashVerified: Boolean
)
final case class LocalNeptuneCsvProvenance(
    fingerprint: String,
    nodes: Long,
    edges: Long,
    supports: Long
)

/** Where every served value came from. */
final case class LocalExportProvenance(
    runId: String,
    exportRoot: Option[String],
    hadoopRunId: String,
    entityResolutionRunId: String,
    entityResolutionPolicyVersion: String,
    entityResolutionPolicyHash: String,
    fileSha256: Map[String, String],
    tables: Vector[LocalExportTableProvenance],
    artifactScope: String,
    artifactPointer: RuntimeArtifactPointer,
    neptuneCsv: Option[LocalNeptuneCsvProvenance]
)

final case class LocalExportCounts(
    nodesByClass: Map[String, Long],
    edgesByType: Map[String, Long],
    coauthorEdgesByWindow: Map[String, Long],
    coauthorSupportRows: Long,
    metricRows: Long,
    communityMembershipRows: Long,
    bridgeRows: Long,
    temporalChangeRows: Long,
    communitySummaryRows: Long,
    sourceRowsRead: Long,
    cacheWritten: Long,
    cacheRejected: Long
)

/** The in-memory stores a local (offline) query stack needs, built from one completed Phase 6 Spark
  * export. Nothing here calls a provider.
  *
  *   - `graphReader` answers the reads of `LiveGraphSnapshot` and `GraphReader` like Neptune would.
  *   - `metrics` and `entityLinks` are filled by the same `Phase6CacheLoader` that fills DynamoDB.
  *   - `runtimeArtifacts` answers rank, community, bridge, temporal, edge-support and researcher
  *     context reads; `artifactPointer` identifies what it serves.
  *   - `objects` holds the immutable source-run qualifications the metric rows point to (and, for
  *     an include-ids scope, the artifact snapshot); `artifactRegistry` registers them.
  *
  * Path evidence and semantic summaries are not read by the runtime workflow as tables and are not
  * loaded; semantic retrieval needs query embeddings and is out of scope here.
  */
final class LocalExportStores private[storage] (
    val graphReader: LocalGraphReader,
    val metrics: ResearcherMetricStore,
    val entityLinks: EntityLinkCache,
    val objects: ObjectStore,
    val artifactRegistry: ArtifactRegistry,
    val runtimeArtifacts: RuntimeArtifactStore,
    val provenance: LocalExportProvenance,
    val counts: LocalExportCounts,
    val loadMillis: Long
) {
  def artifactPointer: RuntimeArtifactPointer = provenance.artifactPointer
  def runId: String = provenance.runId

  /** Fresh, empty in-memory ports for the query-time state. They are not derived from the export.
    */
  def newQuerySessionStore(): QuerySessionStore = new InMemoryQuerySessionStore()
  def newEvidenceStore(): EvidenceBundleStore = new fakes.InMemoryIndexedEvidenceBundleStore()
  def newAuditStore(): RuntimeAuditStore = new fakes.InMemoryRuntimeAuditStore()
}

object LocalExportStores {

  def load(
      exportDir: Path,
      limits: LocalExportLimits
  ): Either[LocalExportError, LocalExportStores] =
    load(exportDir, LocalExportOptions(limits = limits))

  /** Reads `exportDir` (a completed Phase 6 Spark export root) and builds the stores. Every refusal
    * is a typed value and leaves nothing partially usable.
    */
  def load(
      exportDir: Path,
      options: LocalExportOptions = LocalExportOptions()
  ): Either[LocalExportError, LocalExportStores] =
    try {
      if (!Files.isDirectory(exportDir))
        Left(LocalExportError(LocalExportError.exportDirectoryMissing, "export-directory"))
      else {
        val root = exportDir.toRealPath()
        def text(name: String): Option[String] = {
          val p = root.resolve(name)
          if (Files.isRegularFile(p) && Files.size(p) <= options.limits.maxMetadataBytes)
            Some(Files.readString(p, UTF_8))
          else None
        }
        val files = Vector(
          "run-manifest.json",
          "run-metadata.json",
          "_SCHOLARCHAIN_SPARK_COMPLETE",
          "load-manifests/s3.json"
        ).flatMap(n => text(n).map(t => n -> StorageKeys.sha256(t.getBytes(UTF_8).toVector)))
        text("load-manifests/s3.json") match {
          case None =>
            Left(LocalExportError(LocalExportError.invalidManifests, "manifests", "s3.json"))
          case Some(json) =>
            val manifests =
              try read[Vector[LoadManifest]](json)
              catch {
                case NonFatal(_) =>
                  return Left(
                    LocalExportError(LocalExportError.invalidManifests, "manifests", "s3.json")
                  )
              }
            new Loader(
              manifests,
              new LocalParquetManifestReader(root, options.limits.maxMetadataBytes),
              Some(root),
              files.toMap,
              options
            ).run()
        }
      }
    } catch {
      case NonFatal(_) => Left(LocalExportError(LocalExportError.invalidExport, "export-directory"))
    }

  /** Reader-injected construction for producer fixtures; applies the same checks. */
  def load(
      manifests: Vector[LoadManifest],
      reader: ManifestRowReader,
      options: LocalExportOptions
  ): Either[LocalExportError, LocalExportStores] =
    new Loader(manifests, reader, None, Map.empty, options).run()

  private final class Refused(val error: LocalExportError)
      extends RuntimeException(error.code + " @ " + error.part)

  private val nodeTables = Vector(
    "nodes/type=researcher",
    "nodes/type=work",
    "nodes/type=author_mention",
    "nodes/type=venue",
    "nodes/type=institution",
    "nodes/type=topic"
  )
  private val graphEdgeTables = Vector(
    "edges/type=authored",
    "edges/type=published_in",
    "edges/type=has_topic",
    "edges/type=affiliated_with",
    "edges/type=resolves_to"
  )
  private val coauthorTable = "edges/type=coauthored_with"
  private val supportTable = "edges/type=coauthored_with_support"
  private val metricsTable = "metrics/type=researcher_collaboration"
  private val bridgesTable = "metrics/type=bridges"
  private val communitiesTable = "metrics/type=communities"
  private val summariesTable = "metrics/type=community_summaries"
  private val temporalTable = "metrics/type=temporal_changes"
  private val cacheOnlyTables = Set("metrics/type=kcore", "metrics/type=path_length_estimate")
  private val coauthorEvidenceTable = supportTable

  private final class Loader(
      manifests: Vector[LoadManifest],
      reader: ManifestRowReader,
      root: Option[Path],
      fileHashes: Map[String, String],
      options: LocalExportOptions
  ) {
    private val limits = options.limits
    private var part = "manifests"
    private def refuse(code: String, detail: String = ""): Nothing =
      throw new Refused(LocalExportError(code, part, detail))
    private def checked[A](r: StorageResult[A]): A = StorageResult.value(r).getOrElse {
      r match {
        case Rejected(c) => refuse(c)
        case _           => refuse(LocalExportError.invalidExport, "source-unavailable")
      }
    }
    private val interned = mutable.HashMap.empty[String, String]
    private def i(s: String): String = interned.getOrElseUpdate(s, s)

    def run(): Either[LocalExportError, LocalExportStores] = {
      val started = System.nanoTime()
      try Right(build(started))
      catch {
        case r: Refused        => Left(r.error)
        case SourceRejected(c) => Left(LocalExportError(c, part))
        case _: OutOfMemoryError =>
          Left(LocalExportError("out-of-memory", part, "raise the JVM heap or use an include list"))
        case NonFatal(e) =>
          Left(LocalExportError(LocalExportError.invalidExport, part, e.getClass.getSimpleName))
      }
    }

    private def build(started: Long): LocalExportStores = {
      options.progress("selecting source tables")
      if (
        manifests.isEmpty || manifests.map(_.logicalDataset).distinct.size != manifests.size ||
        manifests.map(_.context).distinct.size != 1
      ) refuse(LocalExportError.invalidManifests, "tables must be unique with one run context")
      val byName = manifests.map(m => m.logicalDataset -> m).toMap
      val context = manifests.head.context
      val run = context.runId
      val required = Phase6RuntimeArtifacts.required.toVector.sorted
      required.foreach(n => if (!byName.contains(n)) refuse(LocalExportError.missingTable, n))
      val needed =
        required ++ (nodeTables ++ graphEdgeTables).filter(n =>
          byName.contains(n) && !required.contains(n)
        )
      val optionalPresent = cacheOnlyTables.toVector.filter(byName.contains)
      val loaded = needed.map(byName)
      loaded.foreach { m =>
        if (
          SparkAnalyticsValidation.check(m).isLeft || m.targetStore != "s3" || m.format != "parquet"
        ) refuse(LocalExportError.invalidManifests, m.logicalDataset)
      }
      val totalRows = (loaded.map(_.rowCount) ++ optionalPresent.map(byName(_).rowCount)).sum
      if (totalRows > limits.maxRows)
        refuse(LocalExportError.exportTooLarge, s"$totalRows rows, limit ${limits.maxRows}")
      val windows = loaded.map(_.windows).distinct
      if (windows.size != 1) refuse(LocalExportError.invalidManifests, "window mismatch")
      val windowSet = windows.head.toSet
      part = "run-verification"
      val qualifications = checked(reader.qualifications(run))

      val objects = new InMemoryObjectStore(
        math.max(16 * 1024 * 1024, limits.subsetArtifact.maxBytes)
      )
      val registry = new InMemoryArtifactRegistry
      val links = new InMemoryEntityLinkCache
      val metrics = new InMemoryResearcherMetricStore
      def loadCache(): CacheLoadReport = {
        part = "cache"
        options.progress("loading entity-link and metric caches")
        val report = new Phase6CacheLoader(
          links,
          metrics,
          reader,
          CacheLoaderConfig(
            maxRowBytes = limits.maxRowBytes,
            scratchDirectory = options.scratchDirectory
          ),
          objects,
          registry
        ).load(manifests) match {
          case Written(r)   => r
          case Unchanged(r) => r
          case Rejected(c)  => refuse(c)
          case _            => refuse(LocalExportError.invalidExport, "cache")
        }
        if (report.rejected > 0) refuse("cache-write-rejected")
        report
      }

      // Optional bounded subset artifact: built from its own streaming pass, then dropped.
      val subset: Option[(RuntimeArtifactPointer, RuntimeArtifactStore)] =
        options.artifactScope match {
          case RuntimeArtifactScope.WholeExport => None
          case RuntimeArtifactScope.IncludeIds(list) =>
            part = "runtime-artifact"
            options.progress("building the bounded include-ids runtime artifact")
            val outcome = RuntimeArtifactSubset.build(
              manifests,
              reader,
              list,
              limits.subsetArtifact,
              maxSourceRows = limits.maxRows
            )
            outcome.result match {
              case Left(refusal) => refuse(refusal.code, refusal.detail)
              case Right(artifact) =>
                val key =
                  StorageKeys.versioned("local-runtime-artifact", artifact.sha256, "snapshot.json")
                checked(objects.put(key, artifact.bytes.toVector, "application/json", Map.empty))
                val pointer = RuntimeArtifactPointer(key, artifact.sha256, run)
                Some(
                  pointer -> new ObjectStoreRuntimeArtifactStore(
                    objects,
                    pointer,
                    limits.subsetArtifact
                  )
                )
            }
        }

      // ---- typed tables ----
      val tableProvenance = Vector.newBuilder[LocalExportTableProvenance]
      var sourceRows = 0L
      val contexts = mutable.HashMap.empty[Option[String], SparkRecordContext]
      val contextJson = mutable.HashMap.empty[String, String]
      def scan(m: LoadManifest)(f: ujson.Obj => Unit): Unit = {
        part = "table:" + m.logicalDataset
        options.progress("reading " + m.logicalDataset)
        val rows = checked(reader.open(m))
        val canonical =
          if (options.verifySourceHashes) mutable.ArrayBuffer.empty[String] else null
        var count = 0L
        try
          while (rows.hasNext) {
            val row = rows.next()
            count += 1
            if (count > m.rowCount) refuse(LocalExportError.rowCountMismatch, m.logicalDataset)
            val json =
              if (canonical != null) Phase6RuntimeArtifacts.canonicalRow(row) else row.render()
            if (json.getBytes(UTF_8).length > limits.maxRowBytes)
              refuse(LocalExportError.rowTooLarge, m.logicalDataset)
            if (canonical != null) canonical += json
            f(row)
          }
        finally rows.close()
        if (count != m.rowCount) refuse(LocalExportError.rowCountMismatch, m.logicalDataset)
        if (
          canonical != null &&
          Phase6RuntimeArtifacts.hashCanonical(canonical.toSeq) != m.sortedRowsSha256
        ) refuse(LocalExportError.contentHashMismatch, m.logicalDataset)
        sourceRows += count
        tableProvenance += LocalExportTableProvenance(
          m.logicalDataset,
          m.rowCount,
          m.sortedRowsSha256,
          options.verifySourceHashes
        )
      }
      def validRow(ok: Boolean, table: String): Unit =
        if (!ok) refuse(LocalExportError.invalidRow, table)
      def sparkContext(c: SparkRecordContext, table: String): SparkRecordContext = {
        validRow(
          c.runId == run && c.lineage == context.lineage && c.windowId.forall(windowSet),
          table
        )
        contexts.getOrElseUpdate(c.windowId, c)
      }
      val seen = mutable.HashMap.empty[String, mutable.HashSet[String]]
      def unique(table: String, key: String): Unit =
        if (!seen.getOrElseUpdate(table, mutable.HashSet.empty).add(key))
          refuse(LocalExportError.duplicateKey, table)

      val nodes = mutable.HashMap.empty[String, (String, String)]
      val researcherIds = mutable.HashSet.empty[String]
      nodeTables.filter(byName.contains).foreach { name =>
        scan(byName(name)) { row =>
          val node = read[GraphNode](row)
          validRow(
            DomainValidation.check(node).isRight && node.provenance.runId == run &&
              node.nodeClass.wire.toLowerCase == name.stripPrefix("nodes/type="),
            name
          )
          if (nodes.contains(node.nodeId)) refuse(LocalExportError.duplicateKey, name)
          nodes(i(node.nodeId)) = (node.nodeClass.wire, row.render())
          if (name == "nodes/type=researcher") researcherIds += i(node.nodeId)
        }
      }

      val edges = Vector.newBuilder[LocalEdge]
      val edgeIds = mutable.HashSet.empty[String]
      val associations =
        mutable.HashMap.empty[String, Vector[AssociationRef]].withDefaultValue(Vector.empty)
      def serialized(v: ujson.Value): Option[String] =
        if (v == ujson.Null) None else Some(v.render())
      graphEdgeTables.filter(byName.contains).foreach { name =>
        val refs = Vector.newBuilder[AssociationRef]
        scan(byName(name)) { row =>
          val edge = read[GraphEdge](row)
          validRow(
            DomainValidation.check(edge).isRight && edge.provenance.runId == run &&
              edge.edgeType.wire.toLowerCase == name.stripPrefix("edges/type="),
            name
          )
          if (!nodes.contains(edge.fromId) || !nodes.contains(edge.toId))
            refuse(LocalExportError.missingEndpoint, name)
          if (!edgeIds.add(edge.edgeId)) refuse(LocalExportError.duplicateKey, name)
          // A null or absent cell is an absent property, as the CSV loader would store it.
          def cell(column: String, property: String): Option[(String, String)] =
            row.obj.get(column).flatMap(serialized).map(property -> _)
          val props = Vector(
            Some("schemaVersion" -> i(edge.schemaVersion)),
            Some("policyVersion" -> i(edge.policyVersion)),
            cell("sourceEvidence", "sourceEvidenceJson"),
            cell("properties", "propertiesJson"),
            cell("provenance", "provenanceJson"),
            cell("context", "contextJson").map((k, v) => k -> contextJson.getOrElseUpdate(v, v))
          ).flatten.toMap
          edges += new LocalEdge(
            i(edge.edgeId),
            i(edge.fromId),
            i(edge.toId),
            edge.edgeType.wire,
            "",
            () => props
          )
          refs += AssociationRef(i(edge.edgeId), i(edge.fromId), i(edge.toId))
        }
        associations(name) = refs.result()
      }

      val coauthored = Vector.newBuilder[SparkCoauthorEdge]
      scan(byName(coauthorTable)) { row =>
        val raw = read[SparkCoauthorEdge](row)
        validRow(SparkAnalyticsValidation.check(raw).isRight, coauthorTable)
        val window =
          raw.context.windowId.getOrElse(refuse(LocalExportError.invalidRow, coauthorTable))
        val edge = raw.copy(
          context = sparkContext(raw.context, coauthorTable),
          edgeId = i(raw.edgeId),
          researcherA = i(raw.researcherA),
          researcherB = i(raw.researcherB)
        )
        if (!researcherIds(edge.researcherA) || !researcherIds(edge.researcherB))
          refuse(LocalExportError.missingEndpoint, coauthorTable)
        if (!edgeIds.add(edge.edgeId)) refuse(LocalExportError.duplicateKey, coauthorTable)
        val ctx = row("context").render()
        val sharedCtx = contextJson.getOrElseUpdate(ctx, ctx)
        coauthored += edge
        edges += new LocalEdge(
          edge.edgeId,
          edge.researcherA,
          edge.researcherB,
          "COAUTHORED_WITH",
          i(window),
          () =>
            Vector(
              Some("policyVersion" -> edge.policyVersion),
              Some("jointPublicationCount" -> edge.jointPublicationCount.toString),
              edge.firstCollaborationYear.map("firstCollaborationYear" -> _.toString),
              edge.lastCollaborationYear.map("lastCollaborationYear" -> _.toString),
              edge.windowStartYear.map("windowStartYear" -> _.toString),
              edge.windowEndYear.map("windowEndYear" -> _.toString),
              Some("windowId" -> window),
              Some(
                "representativeWorkIdsJson" ->
                  ujson.Arr.from(edge.representativeWorkIds.map(ujson.Str(_))).render()
              ),
              Some("evidenceTable" -> coauthorEvidenceTable),
              Some("evidenceEdgeId" -> edge.edgeId),
              Some("contextJson" -> sharedCtx)
            ).flatten.toMap
        )
      }
      val supports = Vector.newBuilder[CoauthorEdgeSupport]
      scan(byName(supportTable)) { row =>
        val raw = read[CoauthorEdgeSupport](row)
        validRow(SparkAnalyticsValidation.check(raw).isRight, supportTable)
        supports += raw.copy(
          context = sparkContext(raw.context, supportTable),
          edgeId = i(raw.edgeId),
          workId = i(raw.workId)
        )
      }
      def typed[A: ReadWriter](
          name: String,
          check: A => Boolean,
          key: A => String,
          context: A => SparkRecordContext,
          rewrite: (A, SparkRecordContext) => A
      ): Vector[A] = {
        val out = Vector.newBuilder[A]
        scan(byName(name)) { row =>
          val raw = read[A](row)
          validRow(check(raw), name)
          unique(name, key(raw))
          out += rewrite(raw, sparkContext(context(raw), name))
        }
        out.result()
      }
      val metricRows = typed[ResearcherMetricsDetail](
        metricsTable,
        SparkAnalyticsValidation.check(_).isRight,
        m => m.researcherId + "\u0000" + m.context.windowId.get,
        _.context,
        (m, c) =>
          m.copy(
            context = c,
            researcherId = i(m.researcherId),
            componentId = i(m.componentId),
            communityId = m.communityId.map(i)
          )
      )
      val bridgeRows = typed[ResearcherBridgeMetrics](
        bridgesTable,
        SparkAnalyticsValidation.check(_).isRight,
        m => m.researcherId + "\u0000" + m.context.windowId.get,
        _.context,
        (m, c) => m.copy(context = c, researcherId = i(m.researcherId))
      )
      val membershipRows = typed[CommunityMembership](
        communitiesTable,
        SparkAnalyticsValidation.check(_).isRight,
        m => m.researcherId + "\u0000" + m.context.windowId.get,
        _.context,
        (m, c) =>
          m.copy(context = c, researcherId = i(m.researcherId), communityId = i(m.communityId))
      )
      val summaryRows = typed[CommunitySummary](
        summariesTable,
        SparkAnalyticsValidation.check(_).isRight,
        m => m.communityId + "\u0000" + m.context.windowId.get,
        _.context,
        (m, c) => m.copy(context = c, communityId = i(m.communityId))
      )
      val changeRows = typed[TemporalChange](
        temporalTable,
        SparkAnalyticsValidation.check(_).isRight,
        m => m.researcherId + "\u0000" + m.fromWindowId + "\u0000" + m.toWindowId,
        _.context,
        (m, c) => m.copy(context = c, researcherId = i(m.researcherId))
      )
      part = "graph"
      options.progress("indexing the graph")
      val coauthorRows = coauthored.result()
      val supportRows = supports.result()
      val rows = RuntimeArtifactRows(
        windowSet,
        loaded.map(_.logicalDataset).toSet,
        researcherIds.toSet,
        metricRows,
        bridgeRows,
        membershipRows,
        summaryRows,
        changeRows,
        coauthorRows,
        supportRows,
        associations("edges/type=authored"),
        associations("edges/type=has_topic"),
        associations("edges/type=published_in"),
        associations("edges/type=affiliated_with")
      )
      part = "runtime-artifact"
      try RuntimeArtifactData.crossCheck(rows)
      catch { case SourceRejected(c) => refuse(c) }
      val membershipOrder = windows.head.zipWithIndex.toMap
      val memberships = membershipRows
        .groupBy(_.researcherId)
        .view
        .mapValues(_.sortBy(m => membershipOrder(m.context.windowId.get)))
        .toMap
      part = "graph"
      val graph = new LocalGraphReader(nodes.toMap, edges.result(), memberships)
      // Counts agree with the manifests or nothing is served.
      def expect(name: String, actual: Long): Unit =
        if (byName.get(name).exists(_.rowCount != actual))
          refuse(LocalExportError.rowCountMismatch, name)
      nodeTables.foreach(n =>
        expect(n, graph.nodeCountsByClass.getOrElse(n.stripPrefix("nodes/type=").toUpperCase, 0L))
      )
      graphEdgeTables.foreach(n =>
        expect(
          n,
          graph.edgeCountsByType.getOrElse(n.stripPrefix("edges/type=").toUpperCase, 0L)
        )
      )
      expect(coauthorTable, graph.edgeCountsByType.getOrElse("COAUTHORED_WITH", 0L))
      val cacheReport = loadCache()

      val (pointer, store) = subset.getOrElse {
        val key = StorageKeys.versioned("local-runtime-artifact", run.replace(':', '-'), "whole")
        val sha = StableIds.sha256Hex(
          "scholarchain.local-whole-runtime-artifact.v1\n" + loaded
            .sortBy(_.logicalDataset)
            .map(m => s"${m.logicalDataset}:${m.rowCount}:${m.sortedRowsSha256}")
            .mkString("\n")
        )
        val p = RuntimeArtifactPointer(key, sha, run)
        p -> (new RuntimeArtifactData(rows, p, RuntimeArtifactConfig()): RuntimeArtifactStore)
      }

      val csv: Option[LocalNeptuneCsvProvenance] =
        if (!options.validateNeptuneCsv) None
        else {
          part = "neptune-csv"
          options.progress("validating the Neptune CSV sidecar")
          val rootPath = root.getOrElse(refuse(LocalExportError.invalidExport, "no export root"))
          val validator = new NeptuneExportValidator(
            ExportValidationConfig(
              maxMetadataBytes = limits.maxMetadataBytes,
              scratchDirectory = options.scratchDirectory
            )
          )
          val validated = checked(
            validator.validate(GraphLoadManifest(run, rootPath.toString, "opencypher"))
          )
          try {
            val nodeCount = graph.nodeCountsByClass.values.sum
            val edgeCount = graph.edgeCountsByType.values.sum
            if (
              validated.nodeCount != nodeCount || validated.edgeCount != edgeCount ||
              validated.supportCount != supportRows.size.toLong
            ) refuse(LocalExportError.rowCountMismatch, "neptune-csv")
            Some(
              LocalNeptuneCsvProvenance(
                validated.fingerprint,
                validated.nodeCount,
                validated.edgeCount,
                validated.supportCount
              )
            )
          } finally validated.close()
        }

      val counts = LocalExportCounts(
        graph.nodeCountsByClass,
        graph.edgeCountsByType,
        graph.coauthorEdgeCountsByWindow,
        supportRows.size.toLong,
        metricRows.size.toLong,
        membershipRows.size.toLong,
        bridgeRows.size.toLong,
        changeRows.size.toLong,
        summaryRows.size.toLong,
        sourceRows,
        cacheReport.written + cacheReport.unchanged,
        cacheReport.rejected
      )
      val provenance = LocalExportProvenance(
        run,
        root.map(_.toString),
        context.lineage.hadoopRunId,
        context.lineage.entityResolutionRunId,
        context.lineage.entityResolutionPolicyVersion,
        context.lineage.entityResolutionPolicyHash,
        fileHashes ++ Map(
          "qualifications" -> StorageKeys.sha256(qualifications.getBytes(UTF_8).toVector)
        ),
        tableProvenance.result(),
        options.artifactScope match {
          case RuntimeArtifactScope.WholeExport      => "whole-export"
          case RuntimeArtifactScope.IncludeIds(list) => "include-ids:" + list.normalizedSha256
        },
        pointer,
        csv
      )
      options.progress("done")
      new LocalExportStores(
        graph,
        metrics,
        links,
        objects,
        registry,
        store,
        provenance,
        counts,
        (System.nanoTime() - started) / 1000000L
      )
    }
  }
}
