package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.util.control.NonFatal
import StorageResult.*

final case class EmbeddingSourceSelection(
    maxSummaries: Int = 100,
    maxTopicNodes: Int = 10,
    maxInstitutionNodes: Int = 10,
    maxScannedRows: Long = 200000,
    maxRowBytes: Int = 1024 * 1024,
    sortChunkRows: Int = 1000,
    maxMetadataBytes: Int = 4 * 1024 * 1024
) {
  require(maxSummaries > 0 && maxTopicNodes >= 0 && maxInstitutionNodes >= 0 && maxScannedRows > 0)
  require(maxRowBytes > 0 && sortChunkRows > 0 && maxMetadataBytes > 0)
}
final case class EmbeddingSourceNode(
    node: GraphNode,
    logicalDataset: String,
    tableRowCount: Long,
    windowId: String,
    sourceReferences: Vector[SummarySourceRef]
)
final case class EmbeddingSourceBatch(
    context: SparkRecordContext,
    summaries: Vector[SemanticSummary],
    nodes: Vector[EmbeddingSourceNode],
    qualificationsJson: String,
    scannedRows: Long,
    tableCounts: Map[String, Long],
    identityFieldsBySummaryId: Map[String, Map[String, String]],
    summaryTypeCounts: Map[String, Long] = Map.empty
)

/** Local completed-export reader. Selection is bounded and stable; selected tables are streamed in
  * full to check producer logical hashes/counts before returning any document to ingestion. The
  * configured scan cap fails closed instead of presenting a partial scan as verification.
  */
object Phase6EmbeddingSource {
  private def rejected(code: String): Nothing = throw SourceRejected(code)
  private def checked[A](result: StorageResult[A]): A = StorageResult.value(result).getOrElse {
    result match {
      case Rejected(code) => rejected(code); case _ => rejected("embedding-source-unavailable")
    }
  }
  def load(
      root: Path,
      selection: EmbeddingSourceSelection = EmbeddingSourceSelection(),
      workManifest: Option[Path] = None
  ): StorageResult[EmbeddingSourceBatch] = {
    var scratch: Path = null
    try {
      val base = root.toRealPath()
      def json(path: Path): String = {
        val real = path.toRealPath()
        if (!real.startsWith(base) || Files.size(real) > selection.maxMetadataBytes)
          rejected("embedding-source-metadata-bound")
        Files.readString(real, UTF_8)
      }
      val declarations = CoreJson
        .parse[Vector[LoadManifest]](json(base.resolve("load-manifests/s3.json")))
        .toOption
        .getOrElse(rejected("invalid-embedding-source-manifest"))
      if (
        declarations.isEmpty || declarations
          .map(_.logicalDataset)
          .distinct
          .size != declarations.size || declarations.map(_.context).distinct.size != 1
      ) rejected("conflicting-embedding-source-manifests")
      val context = declarations.head.context
      val required = Vector("semantic-summaries", "nodes/type=topic", "nodes/type=institution")
      val manifests = required.map(name =>
        declarations
          .find(_.logicalDataset == name)
          .getOrElse(rejected("missing-embedding-source-table"))
      )
      if (
        manifests.exists(m =>
          SparkAnalyticsValidation.check(m).isLeft || m.targetStore != "s3" || m.format != "parquet"
        )
      ) rejected("invalid-embedding-source-manifest")
      val declaredWork = workManifest match {
        case Some(path) =>
          val real = path.toRealPath()
          if (Files.size(real) > selection.maxMetadataBytes)
            rejected("embedding-work-manifest-bound")
          CoreJson
            .parse[Vector[LoadManifest]](Files.readString(real, UTF_8))
            .toOption
            .getOrElse(rejected("invalid-embedding-work-manifest"))
        case None =>
          CoreJson
            .parse[Vector[LoadManifest]](json(base.resolve("load-manifests/s3vectors.json")))
            .toOption
            .getOrElse(rejected("invalid-embedding-work-manifest"))
      }
      val summaryManifest = manifests.head
      if (
        declaredWork.size != 1 || declaredWork.head != summaryManifest
          .copy(targetStore = "s3vectors")
      ) {
        // Store-specific mapping differs; compare the exact immutable source identity instead.
        if (declaredWork.size != 1) rejected("invalid-embedding-work-manifest")
        val work = declaredWork.head
        if (
          work.targetStore != "s3vectors" || work.context != summaryManifest.context || work.logicalDataset != summaryManifest.logicalDataset || work.paths != summaryManifest.paths || work.format != summaryManifest.format || work.rowCount != summaryManifest.rowCount || work.sortedRowsSha256 != summaryManifest.sortedRowsSha256 || work.keyColumns != summaryManifest.keyColumns || work.partitionColumns != summaryManifest.partitionColumns || work.windows != summaryManifest.windows || SparkAnalyticsValidation
            .check(work)
            .isLeft
        ) rejected("embedding-work-source-mismatch")
      }
      if (
        manifests
          .foldLeft(BigInt(0))((sum, m) => sum + BigInt(m.rowCount)) > selection.maxScannedRows
      ) rejected("embedding-source-scan-limit")
      val reader = new LocalParquetManifestReader(base, selection.maxMetadataBytes)
      val qualifications = checked(reader.qualifications(context.runId))
      scratch = Files.createTempDirectory("scholarchain-embedding-source-")
      val summaries = mutable.Map.empty[String, mutable.TreeMap[String, SemanticSummary]]
      val typeCounts = mutable.Map.empty[String, Long].withDefaultValue(0L)
      val nodes = mutable.ArrayBuffer.empty[EmbeddingSourceNode]
      var scanned = 0L
      val counts = mutable.Map.empty[String, Long]
      manifests.zipWithIndex.foreach { (manifest, tableIndex) =>
        val digest =
          new SpillDigest(scratch.resolve("table-" + tableIndex), selection.sortChunkRows)
        val selectedNodes = mutable.TreeMap.empty[String, GraphNode]
        val rows = checked(reader.open(manifest))
        try
          while (rows.hasNext) {
            val row = rows.next()
            if (ExportFiles.canonical(row).getBytes(UTF_8).length > selection.maxRowBytes)
              rejected("embedding-source-row-limit")
            scanned += 1
            if (scanned > selection.maxScannedRows || digest.rowCount >= manifest.rowCount)
              rejected("embedding-source-row-count-mismatch")
            digest.add(row)
            if (manifest.logicalDataset == "semantic-summaries") {
              val summary = CoreJson
                .parse[SemanticSummary](row.render())
                .toOption
                .getOrElse(rejected("invalid-semantic-source-row"))
              if (
                SparkAnalyticsValidation
                  .check(summary)
                  .isLeft || summary.context.runId != context.runId || summary.context.lineage != context.lineage
              ) rejected("semantic-source-provenance-mismatch")
              val key = StorageKeys.composite(
                summary.summaryType,
                summary.entityId,
                summary.context.windowId.getOrElse(""),
                summary.summaryId
              )
              val pool = summaries.getOrElseUpdate(
                summary.summaryType,
                mutable.TreeMap.empty[String, SemanticSummary]
              )
              pool
                .get(key)
                .foreach(old => if (old != summary) rejected("conflicting-summary-source-row"))
              pool(key) = summary
              typeCounts(summary.summaryType) += 1
              if (pool.size > selection.maxSummaries) pool.remove(pool.lastKey)
            } else {
              val node = CoreJson
                .parse[GraphNode](row.render())
                .toOption
                .getOrElse(rejected("invalid-node-source-row"))
              val expected =
                if (manifest.logicalDataset == "nodes/type=topic") GraphNodeClass.Topic
                else GraphNodeClass.Institution
              if (
                DomainValidation
                  .check(node)
                  .isLeft || node.nodeClass != expected || node.provenance.runId != context.runId
              ) rejected("node-source-provenance-mismatch")
              val limit =
                if (expected == GraphNodeClass.Topic) selection.maxTopicNodes
                else selection.maxInstitutionNodes
              if (limit > 0) {
                selectedNodes
                  .get(node.nodeId)
                  .foreach(old => if (old != node) rejected("conflicting-node-source-row"))
                selectedNodes(node.nodeId) = node
                if (selectedNodes.size > limit) selectedNodes.remove(selectedNodes.lastKey)
              }
            }
          }
        finally rows.close()
        if (digest.rowCount != manifest.rowCount || digest.finish() != manifest.sortedRowsSha256)
          rejected("embedding-source-logical-hash-mismatch")
        counts(manifest.logicalDataset) = manifest.rowCount
        selectedNodes.values.foreach { node =>
          nodes += EmbeddingSourceNode(
            node,
            manifest.logicalDataset,
            manifest.rowCount,
            context.windowId.getOrElse("all-years"),
            Vector(
              SummarySourceRef(manifest.logicalDataset, node.nodeId, "label"),
              SummarySourceRef("run-metadata.json", manifest.logicalDataset, "rowCount")
            )
          )
        }
      }
      val pools = summaries.toVector.sortBy(_._1).map(_._2.valuesIterator)
      val selectedRows = mutable.ArrayBuffer.empty[SemanticSummary]
      while (selectedRows.size < selection.maxSummaries && pools.exists(_.hasNext)) {
        pools.foreach(it =>
          if (it.hasNext && selectedRows.size < selection.maxSummaries) selectedRows += it.next()
        )
      }
      val selected = selectedRows.toVector
      val identity = selected.map { summary =>
        val baseFields = summary.summaryType match {
          case "researcher-profile" => Map("researcherId" -> summary.entityId)
          case "community"          => Map("communityId" -> summary.entityId)
          case _                    => Map.empty[String, String]
        }
        // A summary can reference many source datasets; do not guess one from a mixed export.
        summary.summaryId -> baseFields
      }.toMap
      Found(
        EmbeddingSourceBatch(
          context,
          selected,
          nodes.toVector,
          qualifications,
          scanned,
          counts.toMap,
          identity,
          typeCounts.toMap
        )
      )
    } catch {
      case e: SourceRejected => Rejected(e.code)
      case NonFatal(_)       => Rejected("invalid-completed-embedding-source")
    } finally if (scratch != null) ExportFiles.deleteTree(scratch)
  }
}
