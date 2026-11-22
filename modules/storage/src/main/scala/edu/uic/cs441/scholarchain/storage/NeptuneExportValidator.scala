package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*
import StorageResult.*

final class ValidatedNeptuneExport private[storage] (
    val root: Path,
    private[storage] val scratch: Path,
    val runId: String,
    val fingerprint: String,
    val nodeCount: Long,
    val edgeCount: Long,
    val supportCount: Long,
    private val datasets: Vector[String],
    private val supportPath: String
) extends AutoCloseable {
  val loaderRelativePrefix = "neptune-opencypher-csv/data"

  /** Original node CSV is replaced by the checked, enriched projection with identical IDs. */
  def foreachObject(f: (Path, String) => Unit): Unit = {
    val enriched = Files.list(scratch.resolve("enriched-nodes"))
    try
      enriched
        .iterator()
        .asScala
        .foreach(p => f(p, loaderRelativePrefix + "/nodes/" + p.getFileName.toString))
    finally enriched.close()
    datasets.filterNot(_.endsWith("/nodes")).foreach { relative =>
      val walk = Files.walk(root.resolve(relative))
      try
        walk
          .iterator()
          .asScala
          .filter(Files.isRegularFile(_))
          .foreach(p => {
            val real = p.toRealPath();
            if (!real.startsWith(root)) throw SourceRejected("source-file-outside-root");
            f(real, root.relativize(p).toString.replace('\\', '/'))
          })
      finally walk.close()
    }
    val support = Files.walk(root.resolve(supportPath))
    try
      support
        .iterator()
        .asScala
        .filter(p => Files.isRegularFile(p) && p.toString.endsWith(".parquet"))
        .foreach(p => {
          val real = p.toRealPath();
          if (!real.startsWith(root)) throw SourceRejected("source-file-outside-root");
          f(real, root.relativize(p).toString.replace('\\', '/'))
        })
    finally support.close()
  }
  def close(): Unit = ExportFiles.deleteTree(scratch)
}

/** Checks the completed producer inputs, every CSV logical hash, exact projection/ID parity and
  * supporting works before the loader can upload a single byte or submit any SDK mutation.
  */
final class NeptuneExportValidator(config: ExportValidationConfig = ExportValidationConfig()) {
  import ExportFiles.*
  private def fail(c: String): Nothing = throw SourceRejected(c)
  private def value[A](r: StorageResult[A]): A = StorageResult
    .value(r)
    .getOrElse(r match { case Rejected(c) => fail(c); case _ => fail("source-unavailable") })
  private def csvCell(s: String): String = if (
    s.isEmpty || s.exists(c => c == ',' || c == '"' || c == '\r' || c == '\n')
  ) "\"" + s.replace("\"", "\"\"") + "\""
  else s
  def validate(manifest: GraphLoadManifest): StorageResult[ValidatedNeptuneExport] = {
    var scratch: Path = null
    try {
      if (manifest.format != "opencypher" || manifest.nodeIds.nonEmpty || manifest.edgeIds.nonEmpty)
        fail("invalid-neptune-manifest")
      val supplied = Path.of(manifest.uri).toRealPath()
      val root = if (Files.isDirectory(supplied)) supplied else supplied.getParent.getParent
      def metadata(relative: String): String = {
        val p = root.resolve(relative).toRealPath();
        if (!p.startsWith(root) || Files.size(p) > config.maxMetadataBytes) {
          fail("source-metadata-limit")
        }
        Files.readString(p, UTF_8)
      }
      val sidecar = ujson.read(metadata("load-manifests/neptune-opencypher-csv.json"))
      if (
        sidecar("schemaVersion").str != "scholarchain.neptune-opencypher-export.v1" || sidecar(
          "runId"
        ).str != manifest.runId || sidecar("format").str != "opencypher" || !sidecar(
          "userProvidedEdgeIds"
        ).bool || sidecar("loaderPrefix").str != "neptune-opencypher-csv/data" || sidecar(
          "contentHashMethod"
        ).str != "sha256-fixed-256-shard-sorted-row-json-merkle-v1"
      ) fail("invalid-neptune-sidecar")
      val sources = CoreJson
        .parse[Vector[LoadManifest]](metadata("load-manifests/s3.json"))
        .toOption
        .getOrElse(fail("invalid-source-manifests"))
      val sourceMap = sources.map(m => m.logicalDataset -> m).toMap
      if (sourceMap.size != sources.size || sources.exists(_.context.runId != manifest.runId))
        fail("conflicting-source-manifests")
      val supportPath = "edges/type=coauthored_with_support"
      if (
        sidecar("supportTable")("path").str != supportPath || sidecar("supportTable")(
          "keyColumns"
        ).arr.map(_.str).toVector != Vector("edgeId", "workId")
      ) fail("invalid-support-mapping")
      val declared = sidecar("sourceTables").arr.toVector
      val expectedSources = sources.filter(m =>
        (m.logicalDataset.startsWith(
          "nodes/"
        ) && m.logicalDataset != "nodes/type=work_sources") || m.logicalDataset.startsWith("edges/")
      )
      if (
        declared.map(_("path").str).toSet != expectedSources
          .map(_.logicalDataset)
          .toSet || declared.map(_("path").str).distinct.size != declared.size
      ) fail("source-table-set-mismatch")
      declared.foreach { t =>
        val m = sourceMap(t("path").str);
        if (
          !ManifestMetadata.rowCount(t("rowCount")).contains(m.rowCount) || t(
            "contentHash"
          ).str != m.sortedRowsSha256 || t("keyColumns").arr.map(_.str).toVector != m.keyColumns
        ) fail("source-table-binding-mismatch")
      }
      val reader = new LocalParquetManifestReader(root, config.maxMetadataBytes)
      value(reader.qualifications(manifest.runId))
      scratch = config.scratchDirectory
        .map(p => Files.createTempDirectory(p, "neptune-validate-"))
        .getOrElse(Files.createTempDirectory("neptune-validate-"))
      val index = scratch.resolve("index"); Files.createDirectory(index)
      def indexFile(kind: String, id: String) = index.resolve(kind + "-" + hash(id))
      def put(kind: String, id: String, json: String): Unit = {
        val p = indexFile(kind, id); if (Files.exists(p)) fail("duplicate-" + kind + "-id");
        Files.writeString(p, json, UTF_8)
      }
      def get(kind: String, id: String): Option[ujson.Obj] = {
        val p = indexFile(kind, id);
        if (Files.exists(p)) Some(ujson.read(Files.readString(p, UTF_8)).asInstanceOf[ujson.Obj])
        else None
      }
      def serialized(v: ujson.Value): ujson.Value =
        if (v == ujson.Null) ujson.Null else ujson.Str(v.render())
      def expectedNode(row: ujson.Obj) = ujson.Obj(
        ":ID" -> row("nodeId"),
        ":LABEL" -> row("nodeClass"),
        "label:String" -> row("label"),
        "schemaVersion:String" -> row("schemaVersion"),
        "propertiesJson:String" -> serialized(row("properties")),
        "provenanceJson:String" -> serialized(row("provenance")),
        "contextJson:String" -> serialized(row("context"))
      )
      // One shared definition of the edge projection (also used by the local loader).
      def expectedGraph(row: ujson.Obj) = GraphProjection.toObj(GraphProjection.graphEdge(row))
      def expectedCoauthor(row: ujson.Obj) =
        GraphProjection.toObj(GraphProjection.coauthorFromRow(row))
      var nodes = 0L; var edges = 0L; var supports = 0L
      def source(m: LoadManifest)(f: ujson.Obj => Unit): Unit = {
        val digest =
          new SpillDigest(scratch.resolve("hash-" + hash(m.logicalDataset)), config.sortChunkRows)
        val rows = value(reader.open(m));
        try while (rows.hasNext) { val row = rows.next(); digest.add(row); f(row) }
        finally rows.close()
        if (digest.rowCount != m.rowCount || digest.finish() != m.sortedRowsSha256)
          fail("source-content-hash-mismatch")
      }
      expectedSources
        .filter(_.logicalDataset.startsWith("nodes/"))
        .foreach(m =>
          source(m) { row =>
            val id = row("nodeId").str; put("node", id, canonical(expectedNode(row))); nodes += 1
          }
        )
      expectedSources
        .filter(m => m.logicalDataset.startsWith("edges/") && m.logicalDataset != supportPath)
        .foreach(m =>
          source(m) { row =>
            val projected =
              if (m.logicalDataset == "edges/type=coauthored_with") expectedCoauthor(row)
              else expectedGraph(row)
            if (
              get("node", projected(":START_ID").str).isEmpty || get(
                "node",
                projected(":END_ID").str
              ).isEmpty
            ) fail("missing-edge-endpoint")
            put("edge", row("edgeId").str, canonical(projected)); edges += 1
          }
        )
      source(sourceMap.getOrElse(supportPath, fail("missing-support-table"))) { row =>
        val edge = get("edge", row("edgeId").str).getOrElse(fail("orphan-coauthor-support"))
        val work = get("node", row("workId").str).getOrElse(fail("missing-support-work"))
        if (edge(":TYPE").str != "COAUTHORED_WITH" || work(":LABEL").str != "WORK")
          fail("invalid-support-endpoint")
        put("support", StorageKeys.support(row("edgeId").str, row("workId").str), canonical(row));
        supports += 1
        append(indexFile("support-count", row("edgeId").str), "1")
      }
      val communityManifest = sourceMap.get("metrics/type=communities")
      communityManifest.foreach(m =>
        source(m) { row =>
          val c = CoreJson
            .parse[CommunityMembership](row.render())
            .toOption
            .getOrElse(fail("invalid-community-membership"))
          if (SparkAnalyticsValidation.check(c).isLeft || get("node", c.researcherId).isEmpty)
            fail("invalid-community-membership")
          val p = indexFile("memberships", c.researcherId)
          val prior =
            if (Files.exists(p)) ujson.read(Files.readString(p, UTF_8)).arr.toVector
            else Vector.empty
          if (
            prior.size >= config.maxAffiliations || prior
              .exists(_("context")("windowId") == row("context")("windowId"))
          ) fail("duplicate-or-excess-community-window")
          Files.writeString(
            p,
            ujson.Arr.from(prior :+ ujson.read(CoreJson.compact(c))).render(),
            UTF_8
          )
        }
      )
      val datasets = sidecar("datasets").arr.toVector
      val required = Vector(
        "neptune-opencypher-csv/data/nodes",
        "neptune-opencypher-csv/data/graph-edges",
        "neptune-opencypher-csv/data/coauthor-edges"
      )
      if (datasets.map(_("path").str).toSet != required.toSet || datasets.size != 3)
        fail("invalid-csv-datasets")
      val enrichedDirectory = scratch.resolve("enriched-nodes");
      Files.createDirectory(enrichedDirectory)
      var nodeOutput: java.io.BufferedWriter = null; var nodePart = 0; var nodeBytes = 0L;
      var nodeHeader = ""
      def openNodePart(): Unit = {
        if (nodeOutput != null) nodeOutput.close();
        nodeOutput =
          Files.newBufferedWriter(enrichedDirectory.resolve(s"part-$nodePart.csv"), UTF_8);
        nodePart += 1; nodeOutput.write(nodeHeader); nodeBytes = nodeHeader.getBytes(UTF_8).length
      }
      def writeNode(line: String): Unit = {
        val bytes = line.getBytes(UTF_8).length;
        if (bytes + nodeHeader.getBytes(UTF_8).length > config.maxEnrichedCsvBytes)
          fail("enriched-node-row-limit");
        if (nodeOutput == null || nodeBytes + bytes > config.maxEnrichedCsvBytes) openNodePart();
        nodeOutput.write(line); nodeBytes += bytes
      }
      var writtenHeader = false; var csvNodes = 0L; var csvEdges = 0L
      try
        datasets.foreach { dataset =>
          val relative = dataset("path").str; val directory = root.resolve(relative).toRealPath();
          if (!directory.startsWith(root)) fail("invalid-csv-path")
          val headers = dataset("columns").arr.map(_.str).toVector
          if (headers.distinct.size != headers.size) fail("duplicate-csv-header")
          val digest =
            new SpillDigest(scratch.resolve("csvhash-" + hash(relative)), config.sortChunkRows)
          val files = Files.walk(directory)
          try
            files.iterator().asScala.filter(Files.isRegularFile(_)).foreach { path =>
              val realFile = path.toRealPath();
              if (!realFile.startsWith(root)) fail("source-file-outside-root")
              if (!path.toString.endsWith(".csv")) fail("non-csv-loader-file")
              val csv =
                new CsvRecords(Files.newBufferedReader(realFile, UTF_8), config.maxCsvCellChars)
              try {
                if (!csv.next().exists(_.map(_.text) == headers)) fail("csv-header-mismatch")
                var next = csv.next()
                while (next.nonEmpty) {
                  val cells = next.get; if (cells.size != headers.size) fail("csv-column-count")
                  val row = ujson.Obj.from(headers.zip(cells).map { case (h, c) =>
                    val v =
                      if (c.text.isEmpty && !c.quoted) ujson.Null
                      else if (h.endsWith(":Long") || h.endsWith(":Int")) {
                        val n = c.text.toLongOption.getOrElse(fail("invalid-csv-integer"));
                        if (
                          n < -9007199254740991L || n > 9007199254740991L || (h
                            .endsWith(":Int") && (n < Int.MinValue || n > Int.MaxValue))
                        ) fail("csv-integer-range"); ujson.Num(n.toDouble)
                      } else ujson.Str(c.text)
                    h -> v
                  })
                  digest.add(row)
                  val kind = if (relative.endsWith("/nodes")) "node" else "edge";
                  val id = row(":ID").str
                  val expected = get(kind, id).getOrElse(fail("csv-id-not-in-source"))
                  if (canonical(row) != canonical(expected)) fail("csv-projection-mismatch")
                  put("csv-" + kind, id, "{}")
                  if (kind == "node") {
                    csvNodes += 1
                    if (!writtenHeader) {
                      nodeHeader = (headers ++ Vector(
                        "communityMembershipKeys:String",
                        "communityWindowKeys:String",
                        "communityQualificationsJson:String"
                      )).map(csvCell).mkString(",") + "\r\n"; writtenHeader = true
                    }
                    val p = indexFile("memberships", id);
                    val memberships =
                      if (Files.exists(p)) ujson.read(Files.readString(p, UTF_8)).arr.toVector
                      else Vector.empty
                    val tokens = memberships
                      .map(c =>
                        CommunityLookup
                          .membership(c("context")("windowId").str, c("communityId").str)
                      )
                      .sorted
                      .mkString
                    val windows = memberships
                      .map(c => CommunityLookup.window(c("context")("windowId").str))
                      .sorted
                      .mkString
                    val values = cells
                      .map(c => if (c.text.isEmpty && !c.quoted) "" else csvCell(c.text)) ++ Vector(
                      csvCell(tokens),
                      csvCell(windows),
                      csvCell(ujson.Arr.from(memberships).render())
                    )
                    writeNode(values.mkString(",") + "\r\n")
                  } else {
                    csvEdges += 1
                    if (row(":TYPE").str == "COAUTHORED_WITH") {
                      val p = indexFile("support-count", id); var count = 0L
                      if (Files.exists(p)) {
                        val lines = Files.lines(p, UTF_8);
                        try count = lines.count()
                        finally lines.close()
                      }
                      if (count <= 0 || count.toDouble != row("jointPublicationCount:Long").num)
                        fail("coauthor-support-count-mismatch")
                    }
                  }
                  next = csv.next()
                }
              } finally csv.close()
            }
          finally files.close()
          if (
            !ManifestMetadata.rowCount(dataset("rowCount")).contains(digest.rowCount) || dataset(
              "contentHash"
            ).str != digest.finish()
          ) fail("csv-content-hash-mismatch")
        }
      finally if (nodeOutput != null) nodeOutput.close()
      if (csvNodes != nodes || csvEdges != edges) fail("csv-id-parity-mismatch")
      if (!writtenHeader) {
        val header =
          datasets.find(_("path").str.endsWith("/nodes")).get("columns").arr.map(_.str).toVector;
        Files.writeString(
          enrichedDirectory.resolve("part-0.csv"),
          (header ++ Vector(
            "communityMembershipKeys:String",
            "communityWindowKeys:String",
            "communityQualificationsJson:String"
          )).map(csvCell).mkString(",") + "\r\n",
          UTF_8
        )
      }
      val fingerprint = hash(
        sidecar.render() + "\n" + communityManifest
          .map(_.sortedRowsSha256)
          .getOrElse("no-community-memberships")
      )
      Found(
        new ValidatedNeptuneExport(
          root,
          scratch,
          manifest.runId,
          fingerprint,
          nodes,
          edges,
          supports,
          required,
          supportPath
        )
      )
    } catch {
      case SourceRejected(c) => if (scratch != null) deleteTree(scratch); Rejected(c);
      case _: Exception =>
        if (scratch != null) deleteTree(scratch); Rejected("invalid-neptune-export")
    }
  }
}
