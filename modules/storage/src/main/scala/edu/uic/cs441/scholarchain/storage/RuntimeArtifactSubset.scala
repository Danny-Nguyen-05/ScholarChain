package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.util.control.NonFatal
import StorageResult.*

/** Validated list of entity IDs that the bounded runtime artifact must answer about. One stable ID
  * per line; blank lines and lines starting with '#' are ignored. Researchers use the `researcher:`
  * prefix; a `work:` ID stands for all of its authors.
  */
final case class IncludeList(fileSha256: String, ids: Vector[String], duplicateLines: Int) {
  def researchers: Vector[String] = ids.filter(_.startsWith("researcher:"))
  def works: Vector[String] = ids.filter(_.startsWith("work:"))
  def normalizedSha256: String = StableIds.sha256Hex(ids.mkString("\n"))
}

object IncludeList {
  val maxIds = 2000
  val maxBytes = 1024 * 1024
  private val shape = "(researcher|work):[^\\s]{1,500}".r

  def parse(bytes: Array[Byte]): Either[String, IncludeList] =
    if (bytes.length > maxBytes) Left("include-list-too-large")
    else {
      val lines = new String(bytes, UTF_8).linesIterator
        .map(_.trim)
        .filter(l => l.nonEmpty && !l.startsWith("#"))
        .toVector
      val unique = lines.distinct.sorted
      if (lines.exists(l => !shape.matches(l))) Left("include-list-invalid-id")
      else if (unique.isEmpty) Left("include-list-empty")
      else if (unique.size > maxIds) Left("include-list-too-many-ids")
      else
        Right(IncludeList(StorageKeys.sha256(bytes.toVector), unique, lines.size - unique.size))
    }
}

final case class SubsetRefusal(code: String, detail: String)
final case class SubsetArtifact(bytes: Array[Byte], sha256: String, runId: String)

/** `result` is Right only when an artifact was produced. `report` is always returned. */
final case class SubsetOutcome(result: Either[SubsetRefusal, SubsetArtifact], report: ujson.Obj)

/** Builds a deterministic bounded runtime artifact from a completed, hash-verified Phase 6 export
  * that is far larger than the artifact caps. The caps are the ordinary [[RuntimeArtifactConfig]]
  * limits; they are never raised. Source tables are read through the ordinary manifest reader and
  * verified against their sorted-row hashes before any row is selected.
  */
object RuntimeArtifactSubset {
  val ruleId = "scholarchain.runtime-subset.v1"
  def ruleText(degreeWindow: String): String =
    "1) Include list (required): every researcher ID listed, and every author of each listed work " +
      "ID, is included with its complete closure; a listed ID that is unknown, whose closure alone " +
      "exceeds the caps, or whose union with the other listed IDs exceeds the caps refuses the " +
      "whole run (nothing is written). " +
      s"2) Fill: remaining researchers ordered by distinctCoauthorCount in window '$degreeWindow' " +
      "descending, ties by stable researcher ID ascending, are added one at a time with their " +
      "complete closure; the fill stops at the first researcher whose additional rows would " +
      "exceed the row cap, the byte cap (estimate includes framing) or the per-row cap. " +
      "3) Closure of a researcher: its node; its rows in researcher_collaboration, communities, " +
      "bridges and temporal_changes for all windows; the summaries of its communities; every " +
      "coauthored_with edge incident to it with all its support rows and both endpoint nodes; " +
      "its authored edges and, for each authored work, the has_topic and published_in edges; " +
      "its affiliated_with edges; and the topic, venue and institution nodes those edges " +
      "reference. A closure is added whole or not at all (no half entities). Rows already present " +
      "through another closure are counted once. 4) Rows are sorted by their key and serialized " +
      "canonically, so the same inputs produce the same bytes."

  private final class Refused(val code: String, val detail: String)
      extends RuntimeException(code + ": " + detail)

  private final class SrcRow(
      val ord: Int,
      val table: String,
      val sortKey: String,
      val json: String,
      val x: String,
      val y: String,
      val z: String
  ) {
    val bytes: Int = json.getBytes(UTF_8).length
    def cost: Long = bytes.toLong + 1L
  }

  private val researcherNodes = "nodes/type=researcher"
  private val metricsTable = "metrics/type=researcher_collaboration"
  private val communitiesTable = "metrics/type=communities"
  private val summariesTable = "metrics/type=community_summaries"
  private val bridgesTable = "metrics/type=bridges"
  private val temporalTable = "metrics/type=temporal_changes"
  private val edgesTable = "edges/type=coauthored_with"
  private val supportsTable = "edges/type=coauthored_with_support"
  private val authoredTable = "edges/type=authored"
  private val hasTopicTable = "edges/type=has_topic"
  private val publishedInTable = "edges/type=published_in"
  private val affiliatedTable = "edges/type=affiliated_with"
  private val perResearcherTables = Vector(
    metricsTable,
    communitiesTable,
    bridgesTable,
    temporalTable,
    authoredTable,
    affiliatedTable
  )
  private val workAssociationTables = Vector(hasTopicTable, publishedInTable)
  private val otherNodeTables =
    Set("nodes/type=topic", "nodes/type=venue", "nodes/type=institution")

  private type Multi = mutable.HashMap[String, mutable.ArrayBuffer[SrcRow]]
  private def multi(): Multi = mutable.HashMap.empty
  private def put(m: Multi, key: String, row: SrcRow): Unit =
    m.getOrElseUpdate(key, mutable.ArrayBuffer.empty) += row
  private def get(m: Multi, key: String): Iterable[SrcRow] = m.getOrElse(key, Nil)

  private final class Index(degreeWindow: String) {
    val all = mutable.ArrayBuffer.empty[SrcRow]
    val researcherNode = mutable.HashMap.empty[String, SrcRow]
    val otherNode = mutable.HashMap.empty[String, SrcRow]
    val perResearcher: Map[String, Multi] = perResearcherTables.map(_ -> multi()).toMap
    val edgesByResearcher: Multi = multi()
    val supportsByEdge: Multi = multi()
    val summariesByCommunity: Multi = multi()
    val assocByWork: Map[String, Multi] = workAssociationTables.map(_ -> multi()).toMap
    val authorsOfWork = mutable.HashMap.empty[String, mutable.ArrayBuffer[String]]
    val degrees = mutable.HashMap.empty[String, Long]

    private def str(row: ujson.Obj, name: String): String = row.obj(name).str
    private def window(row: ujson.Obj): Option[ujson.Value] =
      row.obj.get("context").flatMap(_.obj.get("windowId"))
    private def windowText(row: ujson.Obj): String = window(row).map(_.render()).getOrElse("")

    def add(m: LoadManifest, row: ujson.Obj): Unit = {
      val sortKey = m.keyColumns
        .map(k => row.obj.get(k).map(_.render()).getOrElse("null"))
        .mkString("\u0000") + "\u0000" + windowText(row)
      def make(x: String = "", y: String = "", z: String = ""): SrcRow = {
        val r = new SrcRow(all.size, m.logicalDataset, sortKey, row.render(), x, y, z)
        all += r
        r
      }
      m.logicalDataset match {
        case `researcherNodes`       => researcherNode(str(row, "nodeId")) = make()
        case n if otherNodeTables(n) => otherNode(str(row, "nodeId")) = make()
        case `metricsTable` =>
          val id = str(row, "researcherId")
          put(perResearcher(metricsTable), id, make())
          if (window(row).contains(ujson.Str(degreeWindow)))
            degrees(id) = row.obj("distinctCoauthorCount").num.toLong
        case `communitiesTable` =>
          put(
            perResearcher(communitiesTable),
            str(row, "researcherId"),
            make(x = str(row, "communityId"))
          )
        case `bridgesTable` | `temporalTable` =>
          put(perResearcher(m.logicalDataset), str(row, "researcherId"), make())
        case `summariesTable` => put(summariesByCommunity, str(row, "communityId"), make())
        case `edgesTable` =>
          val a = str(row, "researcherA"); val b = str(row, "researcherB")
          val r = make(a, b, str(row, "edgeId") + "\u0000" + windowText(row))
          put(edgesByResearcher, a, r)
          if (b != a) put(edgesByResearcher, b, r)
        case `supportsTable` =>
          put(supportsByEdge, str(row, "edgeId") + "\u0000" + windowText(row), make())
        case `authoredTable` =>
          val from = str(row, "fromId"); val to = str(row, "toId")
          put(perResearcher(authoredTable), from, make(x = to))
          authorsOfWork.getOrElseUpdate(to, mutable.ArrayBuffer.empty) += from
        case `hasTopicTable` | `publishedInTable` =>
          put(assocByWork(m.logicalDataset), str(row, "fromId"), make(x = str(row, "toId")))
        case `affiliatedTable` =>
          put(perResearcher(affiliatedTable), str(row, "fromId"), make(x = str(row, "toId")))
        case other => throw new Refused("unsupported-runtime-artifact-table", other)
      }
    }

    private def node(id: String, what: String): SrcRow = researcherNode.getOrElse(
      id,
      throw new Refused("source-researcher-node-missing", s"$what $id has no researcher node")
    )

    /** The complete set of source rows needed to answer about one researcher. */
    def closure(researcher: String): Vector[SrcRow] = {
      val rows = mutable.LinkedHashMap.empty[Int, SrcRow]
      def add(r: SrcRow): Unit = rows.getOrElseUpdate(r.ord, r)
      add(node(researcher, "researcher"))
      Vector(metricsTable, communitiesTable, bridgesTable, temporalTable).foreach { t =>
        get(perResearcher(t), researcher).foreach(add)
      }
      get(perResearcher(communitiesTable), researcher)
        .map(_.x)
        .toVector
        .distinct
        .foreach(c => get(summariesByCommunity, c).foreach(add))
      get(edgesByResearcher, researcher).foreach { e =>
        add(e)
        get(supportsByEdge, e.z).foreach(add)
        add(node(e.x, "coauthor")); add(node(e.y, "coauthor"))
      }
      val authored = get(perResearcher(authoredTable), researcher)
      authored.foreach(add)
      authored.map(_.x).toVector.distinct.foreach { work =>
        workAssociationTables.foreach { t =>
          get(assocByWork(t), work).foreach { a =>
            add(a); otherNode.get(a.x).foreach(add)
          }
        }
      }
      get(perResearcher(affiliatedTable), researcher).foreach { a =>
        add(a); otherNode.get(a.x).foreach(add)
      }
      rows.values.toVector
    }
  }

  private def checked[A](r: StorageResult[A]): A = StorageResult.value(r).getOrElse {
    r match {
      case Rejected(c) => throw SourceRejected(c)
      case _           => throw SourceRejected("runtime-source-unavailable")
    }
  }

  private def subsetManifest(
      m: LoadManifest,
      rows: Vector[ujson.Value],
      includeSha: String
  ): LoadManifest =
    m.copy(
      rowCount = rows.size.toLong,
      sortedRowsSha256 = Phase6RuntimeArtifacts.tableHash(rows),
      targetMapping = m.targetMapping ++ Vector(
        NamedText("subset.rule", ruleId),
        NamedText("subset.sourceRowCount", m.rowCount.toString),
        NamedText("subset.sourceSortedRowsSha256", m.sortedRowsSha256),
        NamedText("subset.includeListSha256", includeSha)
      )
    )

  def build(
      manifests: Vector[LoadManifest],
      reader: ManifestRowReader,
      include: IncludeList,
      config: RuntimeArtifactConfig = RuntimeArtifactConfig(),
      degreeWindow: String = "all-years",
      maxSourceRows: Long = 3000000L
  ): SubsetOutcome = {
    val report = ujson.Obj(
      "schema" -> "scholarchain.runtime-subset-report.v1",
      "rule" -> ruleId,
      "ruleText" -> ruleText(degreeWindow),
      "degreeMetric" -> "distinctCoauthorCount",
      "degreeWindow" -> degreeWindow,
      "caps" -> ujson.Obj(
        "maxRows" -> config.maxRows,
        "maxBytes" -> config.maxBytes,
        "maxRowBytes" -> config.maxRowBytes
      ),
      "includeList" -> ujson.Obj(
        "fileSha256" -> include.fileSha256,
        "normalizedSha256" -> include.normalizedSha256,
        "ids" -> include.ids.size,
        "researchers" -> include.researchers.size,
        "works" -> include.works.size,
        "duplicateLines" -> include.duplicateLines
      )
    )
    def refuse(code: String, detail: String): SubsetOutcome = {
      report("status") = "refused"
      report("refusal") = ujson.Obj("code" -> code, "detail" -> detail)
      SubsetOutcome(Left(SubsetRefusal(code, detail)), report)
    }
    try {
      val sources = Phase6RuntimeArtifacts.selectSourceManifests(manifests)
      val context = sources.head.context
      val sourceRows = sources.map(_.rowCount).sum
      report("sourceRunId") = context.runId
      report("source") = ujson.Obj(
        "totalRows" -> sourceRows.toDouble,
        "tables" -> ujson.Arr.from(
          sources.map(m =>
            ujson.Obj(
              "table" -> m.logicalDataset,
              "rows" -> m.rowCount.toDouble,
              "sortedRowsSha256" -> m.sortedRowsSha256
            )
          )
        )
      )
      if (sourceRows > maxSourceRows)
        throw new Refused(
          "source-too-large-for-subset-reader",
          s"source rows $sourceRows exceed the reader bound $maxSourceRows"
        )
      val qualifications = checked(reader.qualifications(context.runId))
      if (qualifications.getBytes(UTF_8).length > config.maxMetadataBytes)
        throw SourceRejected("runtime-source-metadata-bound")
      val q = ujson.read(qualifications)
      if (
        q("runManifest")("runId").str != context.runId ||
        q("runMetadata")("runId").str != context.runId
      ) throw SourceRejected("runtime-source-qualification-mismatch")

      // One streaming pass per table: verify the complete logical hash and build the index.
      val index = new Index(degreeWindow)
      sources.foreach { m =>
        val rows = checked(reader.open(m))
        val canonical = Vector.newBuilder[String]
        var count = 0L
        try
          while (rows.hasNext) {
            val row = rows.next()
            count += 1
            if (count > m.rowCount) throw SourceRejected("runtime-source-row-count-mismatch")
            canonical += Phase6RuntimeArtifacts.canonicalRow(row)
            index.add(m, row)
          }
        finally rows.close()
        if (
          count != m.rowCount ||
          Phase6RuntimeArtifacts.hashCanonical(canonical.result()) != m.sortedRowsSha256
        ) throw SourceRejected("runtime-source-logical-hash-mismatch")
      }

      // Byte budget: the snapshot framing with empty tables, plus slack for longer counts, plus
      // every row's bytes and one separator. The real size is re-measured and re-checked below.
      val baseline = CoreJson
        .compact(
          RuntimeArtifactSnapshot(
            Phase6RuntimeArtifacts.version,
            context,
            qualifications,
            sources.map(m =>
              RuntimeArtifactTable(
                subsetManifest(m, Vector.empty, include.normalizedSha256),
                Vector.empty
              )
            )
          )
        )
        .getBytes(UTF_8)
        .length
        .toLong + sources.size * 8L
      val selected = mutable.HashSet.empty[Int]
      var usedRows = 0L
      var usedBytes = baseline
      def fresh(rows: Seq[SrcRow]): Vector[SrcRow] =
        rows.distinctBy(_.ord).filterNot(r => selected(r.ord)).toVector
      def capReasons(add: Vector[SrcRow]): Vector[String] = Vector(
        Option.when(usedRows + add.size > config.maxRows)("row-cap"),
        Option.when(usedBytes + add.map(_.cost).sum > config.maxBytes)("byte-cap"),
        Option.when(add.exists(_.bytes > config.maxRowBytes))("row-byte-cap")
      ).flatten
      def commit(add: Vector[SrcRow]): Unit = {
        add.foreach(r => selected += r.ord)
        usedRows += add.size
        usedBytes += add.map(_.cost).sum
      }

      // Include list: works become their authors. Each entry alone must fit, then their union.
      val closures = mutable.HashMap.empty[String, Vector[SrcRow]]
      def closureOf(r: String): Vector[SrcRow] = closures.getOrElseUpdate(r, index.closure(r))
      val worksReport = Vector.newBuilder[ujson.Value]
      val entries: Vector[(String, Vector[String])] = include.ids.map { id =>
        if (id.startsWith("researcher:")) {
          if (!index.researcherNode.contains(id))
            throw new Refused("include-id-not-found", s"researcher $id is not a source node")
          id -> Vector(id)
        } else {
          val authors =
            index.authorsOfWork.get(id).map(_.distinct.sorted.toVector).getOrElse(Vector())
          if (authors.isEmpty)
            throw new Refused(
              "include-id-not-found",
              s"work $id has no authored edge in the source"
            )
          worksReport += ujson.Obj("workId" -> id, "authors" -> ujson.Arr.from(authors))
          id -> authors
        }
      }
      entries.foreach { (id, researchers) =>
        val alone = fresh(researchers.flatMap(closureOf))
        val reasons = capReasons(alone)
        if (reasons.nonEmpty)
          throw new Refused(
            "include-entity-alone-exceeds-cap",
            s"$id needs ${alone.size} rows and about ${baseline + alone.map(_.cost).sum} bytes " +
              s"alone; caps ${config.maxRows} rows and ${config.maxBytes} bytes; " +
              s"reasons ${reasons.mkString(",")}"
          )
      }
      val reasonOf = mutable.LinkedHashMap.empty[String, Set[String]]
      entries.foreach { (id, researchers) =>
        val add = fresh(researchers.flatMap(closureOf))
        val reasons = capReasons(add)
        if (reasons.nonEmpty)
          throw new Refused(
            "include-list-exceeds-cap",
            s"adding $id (${add.size} new rows) to $usedRows rows exceeds the caps; " +
              s"reasons ${reasons.mkString(",")}"
          )
        commit(add)
        researchers.foreach { r =>
          reasonOf(r) = reasonOf.getOrElse(r, Set.empty) + (
            if (id.startsWith("researcher:")) "include-list" else s"work-author:$id"
          )
        }
      }
      val listed = reasonOf.toVector.map { (id, reasons) =>
        val label =
          if (reasons("include-list")) "include-list" else reasons.toVector.sorted.mkString(",")
        (id, label, closureOf(id).size, 0)
      }

      // Deterministic fill: highest degree first, ties by ID, whole closures only.
      val order = index.degrees.toVector
        .filter((id, _) => index.researcherNode.contains(id) && !reasonOf.contains(id))
        .sortBy((id, degree) => (-degree, id))
      val filled = Vector.newBuilder[(String, String, Int, Int)]
      var filledCount = 0
      var stoppedAt: Option[ujson.Value] = None
      val candidates = order.iterator
      while (stoppedAt.isEmpty && candidates.hasNext) {
        val (id, degree) = candidates.next()
        val full = index.closure(id)
        val add = fresh(full)
        val reasons = capReasons(add)
        if (reasons.nonEmpty)
          stoppedAt = Some(
            ujson.Obj(
              "id" -> id,
              "degree" -> degree.toDouble,
              "reasons" -> ujson.Arr.from(reasons),
              "neededNewRows" -> add.size,
              "wouldBeTotalRows" -> (usedRows + add.size).toDouble,
              "wouldBeEstimatedBytes" -> (usedBytes + add.map(_.cost).sum).toDouble,
              "droppedBecause" -> "closure does not fit the remaining caps; no partial entity"
            )
          )
        else {
          commit(add)
          filled += ((id, "degree-fill", full.size, add.size))
          filledCount += 1
        }
      }

      // Assemble the sorted tables with recomputed manifests.
      val chosen = selected.toVector.map(index.all(_)).groupBy(_.table)
      val tables = sources.map { m =>
        val rows = chosen
          .getOrElse(m.logicalDataset, Vector.empty)
          .sortBy(r => (r.sortKey, r.json))
          .map(r => ujson.read(r.json))
        RuntimeArtifactTable(subsetManifest(m, rows, include.normalizedSha256), rows)
      }
      val snapshot =
        RuntimeArtifactSnapshot(Phase6RuntimeArtifacts.version, context, qualifications, tables)
      RuntimeArtifactData.validate(snapshot, config)
      val bytes = CoreJson.compact(snapshot).getBytes(UTF_8)
      if (bytes.length > config.maxBytes) throw SourceRejected("runtime-artifact-byte-bound")
      val sha = StorageKeys.sha256(bytes.toVector)

      // Self-check through the real reader: the bytes must load and answer a ranking.
      val selfStore = new InMemoryObjectStore(config.maxBytes)
      val selfKey = "subset-self-check/versions/" + sha + "/snapshot.json"
      if (
        !StorageResult.successful(
          selfStore.put(selfKey, bytes.toVector, "application/json", Map.empty)
        )
      ) throw new Refused("self-check-failed", "in-memory put rejected")
      new ObjectStoreRuntimeArtifactStore(
        selfStore,
        RuntimeArtifactPointer(selfKey, sha, context.runId),
        config
      ).rank(
        degreeWindow,
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(),
        1
      ) match {
        case Found(_) => ()
        case other    => throw new Refused("self-check-failed", other.toString)
      }

      report("status") = "written"
      report("selected") = ujson.Obj(
        "totalRows" -> tables.map(_.rows.size).sum,
        "artifactBytes" -> bytes.length,
        "estimatedBytesBound" -> usedBytes.toDouble,
        "artifactSha256" -> sha,
        "tables" -> ujson.Arr.from(
          tables.map(t =>
            ujson.Obj(
              "table" -> t.manifest.logicalDataset,
              "rows" -> t.rows.size,
              "sortedRowsSha256" -> t.manifest.sortedRowsSha256
            )
          )
        )
      )
      val reportedEntities = listed ++ filled.result()
      report("entities") = ujson.Obj(
        "includedResearchers" -> reportedEntities.size,
        "fromIncludeList" -> listed.size,
        "fromDegreeFill" -> filledCount,
        "included" -> ujson.Arr.from(reportedEntities.map { (id, reason, closureRows, added) =>
          ujson.Obj(
            "id" -> id,
            "reason" -> reason,
            "degree" -> index.degrees.get(id).map(d => ujson.Num(d.toDouble)).getOrElse(ujson.Null),
            "closureRows" -> closureRows,
            "newRowsWhenFilled" -> (if (reason == "degree-fill") ujson.Num(added) else ujson.Null)
          )
        }),
        "includeListWorks" -> ujson.Arr.from(worksReport.result()),
        "fillStoppedAt" -> stoppedAt.getOrElse(ujson.Null),
        "fillStopReason" -> (if (stoppedAt.isDefined) "cap" else "candidates-exhausted"),
        "candidatesNotReached" -> (order.size - filledCount - stoppedAt.size),
        "dropped" -> ("Researchers that are not listed are not entities of the artifact. They " +
          "appear at most as endpoint nodes of included researchers' edges.")
      )
      SubsetOutcome(Right(SubsetArtifact(bytes, sha, context.runId)), report)
    } catch {
      case r: Refused        => refuse(r.code, r.detail)
      case SourceRejected(c) => refuse(c, "")
      case NonFatal(e)       => refuse("invalid-runtime-source", e.getClass.getSimpleName)
    }
  }
}
