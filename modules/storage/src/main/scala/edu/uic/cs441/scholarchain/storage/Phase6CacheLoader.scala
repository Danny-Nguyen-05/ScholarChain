package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path, StandardOpenOption}
import java.nio.charset.StandardCharsets.UTF_8
import java.io.BufferedReader
import java.security.MessageDigest
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import StorageResult.*

private[storage] final case class SourceRejected(code: String) extends RuntimeException(code)

/** Disk-spooled, bounded-memory validation precedes every cache write. The producer's Merkle hash
  * is verified, not confused with the hash of physical Parquet bytes. No dataset collect exists.
  */
final class Phase6CacheLoader(
    entityLinks: EntityLinkCache,
    metrics: ResearcherMetricStore,
    reader: ManifestRowReader,
    config: CacheLoaderConfig = CacheLoaderConfig()
) {
  private val method = "sha256-fixed-256-shard-sorted-row-json-merkle-v1"
  private def reject(c: String): Nothing = throw SourceRejected(c)
  // Spark's Jackson generator retains Double's integral .0, negative zero and exponent
  // representation. ujson's ordinary renderer erases those type distinctions. These are the
  // only Double fields in the selected Phase6 tables; nested field order follows Parquet schema.
  private val doubleFields = Set("averageCoauthorsPerPaper", "meanDistance", "effectiveDiameterP90")
  private def render(value: ujson.Value, field: Option[String] = None): String = value match {
    case obj: ujson.Obj =>
      obj.obj.iterator
        .map((k, v) => ujson.Str(k).render() + ":" + render(v, Some(k)))
        .mkString("{", ",", "}")
    case arr: ujson.Arr => arr.arr.iterator.map(v => render(v, None)).mkString("[", ",", "]")
    case n: ujson.Num if field.exists(doubleFields) => java.lang.Double.toString(n.num)
    case other                                      => other.render()
  }
  private def canonical(row: ujson.Obj): String = render(
    ujson.Obj.from(row.obj.toVector.filterNot(_._1 == "run_id").sortBy(_._1))
  )
  private def digest(s: String) = StorageKeys.sha256(s.getBytes(UTF_8).toVector)
  private def lines(path: Path)(f: String => Unit): Unit = {
    if (Files.exists(path)) {
      val br = Files.newBufferedReader(path, UTF_8);
      try { var l = br.readLine(); while (l != null) { f(l); l = br.readLine() } }
      finally br.close()
    }
  }
  private def append(path: Path, s: String): Unit =
    Files.writeString(path, s + "\n", UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND)
  private def checked[A](r: StorageResult[A]): A = StorageResult
    .value(r)
    .getOrElse(r match { case Rejected(c) => reject(c); case _ => reject("source-unavailable") })
  // Spark UTF8 binary ordering is code-point order, unlike UTF-16 String.compareTo on astral text.
  private def compare(a: String, b: String): Int = {
    val x = a.getBytes(UTF_8); val y = b.getBytes(UTF_8)
    var i = 0;
    while (i < math.min(x.length, y.length)) {
      val d = (x(i) & 255) - (y(i) & 255); if (d != 0) return d; i += 1
    }; x.length - y.length
  }
  private def shardHash(path: Path, scratch: Path): String = {
    val chunk = mutable.ArrayBuffer.empty[String]
    var chunkId = 0
    def flush(): Unit = if (chunk.nonEmpty) {
      val p = scratch.resolve("chunk-" + chunkId); chunkId += 1
      Files.write(p, chunk.sortWith((a, b) => compare(a, b) < 0).asJava, UTF_8)
      chunk.clear()
    }
    lines(path) { l =>
      chunk += l; if (chunk.size >= config.sortChunkRows) flush()
    }; flush()
    // Open at most 64 merge inputs at a time, even for very large shards.
    def merge(inputs: Vector[Path], out: Option[Path]): String = {
      val readers = inputs.map(p => Files.newBufferedReader(p, UTF_8))
      val queue =
        new java.util.PriorityQueue[(String, Int)](new java.util.Comparator[(String, Int)] {
          def compare(a: (String, Int), b: (String, Int)): Int =
            Phase6CacheLoader.this.compare(a._1, b._1)
        })
      val md = MessageDigest.getInstance("SHA-256")
      val writer = out.map(p => Files.newBufferedWriter(p, UTF_8))
      try {
        readers.zipWithIndex.foreach((r, i) => Option(r.readLine()).foreach(l => queue.add(l -> i)))
        var first = true
        while (!queue.isEmpty) {
          val (l, i) = queue.remove()
          if (!first) md.update('\n'.toByte); md.update(l.getBytes(UTF_8)); first = false
          writer.foreach(w => { w.write(l); w.newLine() })
          Option(readers(i).readLine()).foreach(n => queue.add(n -> i))
        }
        md.digest().map(b => f"${b & 255}%02x").mkString
      } finally { readers.foreach(_.close()); writer.foreach(_.close()) }
    }
    var count = chunkId
    var round = -1
    def part(r: Int, i: Int): Path =
      if (r < 0) scratch.resolve("chunk-" + i) else scratch.resolve(s"merge-$r-$i")
    while (count > 64) {
      val nextCount = (count + 63) / 64
      var batch = 0
      while (batch < nextCount) {
        val inputs =
          (batch * 64 until math.min(count, (batch + 1) * 64)).map(i => part(round, i)).toVector
        merge(inputs, Some(part(round + 1, batch))); inputs.foreach(Files.delete); batch += 1
      }
      count = nextCount; round += 1
    }
    val inputs = (0 until count).map(i => part(round, i)).toVector
    val result = merge(inputs, None); inputs.foreach(Files.delete); result
  }

  private def stage(m: LoadManifest, scratch: Path): Path = {
    if (
      SparkAnalyticsValidation
        .check(m)
        .isLeft || m.context.schemaVersion != SchemaVersions.sparkAnalytics || m.format != "parquet"
    ) reject("invalid-load-manifest")
    val dir = scratch.resolve(digest(m.logicalDataset)); Files.createDirectory(dir)
    val spool = dir.resolve("rows.jsonl")
    val counts = mutable.Map.empty[String, Long].withDefaultValue(0L)
    val it = checked(reader.open(m))
    var count = 0L
    try
      while (it.hasNext) {
        val row = it.next()
        val json = canonical(row)
        if (json.getBytes(UTF_8).length > config.maxRowBytes) reject("source-row-too-large")
        val run = row.obj
          .get("context")
          .flatMap(_.obj.get("runId"))
          .orElse(row.obj.get("provenance").flatMap(_.obj.get("runId")))
          .map(_.str)
        if (!run.contains(m.context.runId)) reject("row-run-mismatch")
        val shard = digest(json).take(2)
        append(spool, json); append(dir.resolve("shard-" + shard), json)
        counts(shard) += 1; count += 1
        if (count > m.rowCount) reject("manifest-row-count-mismatch")
      }
    finally it.close()
    if (count != m.rowCount) reject("manifest-row-count-mismatch")
    val shardLines = counts.toVector.sortBy(_._1).map { case (s, n) =>
      s"$s:$n:${shardHash(dir.resolve("shard-" + s), dir)}"
    }
    if (digest(method + "\n" + shardLines.mkString("\n")) != m.sortedRowsSha256)
      reject("manifest-content-hash-mismatch")
    spool
  }
  def load(manifests: Vector[LoadManifest]): StorageResult[CacheLoadReport] = {
    var scratch: Path = null
    try {
      if (
        manifests.map(_.logicalDataset).distinct.size != manifests.size || manifests
          .map(_.context.runId)
          .distinct
          .size > 1
      ) reject("conflicting-manifests")
      if (manifests.isEmpty) return Unchanged(CacheLoadReport(0, 0, 0, 0))
      val run = manifests.head.context.runId
      val qualifications = checked(reader.qualifications(run))
      ujson.read(qualifications)
      scratch = config.scratchDirectory
        .map(p => Files.createTempDirectory(p, "storage-cache-"))
        .getOrElse(Files.createTempDirectory("storage-cache-"))
      val relevant = Set(
        "nodes/type=researcher",
        "nodes/type=author_mention",
        "nodes/type=institution",
        "edges/type=resolves_to",
        "edges/type=affiliated_with",
        "metrics/type=researcher_collaboration",
        "metrics/type=kcore",
        "metrics/type=communities",
        "metrics/type=path_length_estimate"
      )
      val selected = manifests.filter(m => relevant(m.logicalDataset))
      val staged = selected.map(m => m.logicalDataset -> stage(m, scratch)).toMap
      val index = scratch.resolve("index"); Files.createDirectory(index)
      def file(kind: String, key: String): Path = index.resolve(kind + "-" + digest(key))
      def store(kind: String, key: String, row: ujson.Obj): Unit = {
        val p = file(kind, key); val text = canonical(row)
        if (Files.exists(p) && Files.readString(p, UTF_8) != text)
          reject("conflicting-duplicate-" + kind)
        Files.writeString(p, text, UTF_8)
      }
      def lookup(kind: String, key: String): Option[ujson.Obj] = {
        val p = file(kind, key);
        if (Files.exists(p)) Some(ujson.read(Files.readString(p, UTF_8)).asInstanceOf[ujson.Obj])
        else None
      }
      def each(name: String)(f: ujson.Obj => Unit): Unit =
        staged.get(name).foreach(p => lines(p)(l => f(ujson.read(l).asInstanceOf[ujson.Obj])))
      val policy = manifests.head.context.lineage.entityResolutionPolicyVersion
      each("nodes/type=researcher") { row =>
        val node = CoreJson
          .parse[GraphNode](row.render())
          .toOption
          .getOrElse(reject("invalid-researcher-node"));
        if (DomainValidation.check(node).isLeft || node.nodeClass.wire != "RESEARCHER")
          reject("invalid-researcher-node"); store("researcher", node.nodeId, row)
      }
      each("nodes/type=author_mention") { row => store("mention", row("nodeId").str, row) }
      each("nodes/type=institution") { row => store("institution", row("nodeId").str, row) }
      each("edges/type=resolves_to") { row =>
        val from = row("fromId").str; val to = row("toId").str
        if (lookup("researcher", to).isEmpty || lookup("mention", from).isEmpty)
          reject("missing-resolution-endpoint")
        store("resolution", from, ujson.Obj("researcherId" -> to, "edgeId" -> row("edgeId")))
      }
      def canonicalResearcher(id: String): String = if (lookup("researcher", id).isDefined) id
      else
        lookup("resolution", id)
          .map(_("researcherId").str)
          .getOrElse(reject("missing-affiliation-researcher"))
      each("edges/type=affiliated_with") { row =>
        val id = canonicalResearcher(row("fromId").str)
        val institution = row("toId").str
        if (lookup("institution", institution).isEmpty) reject("missing-affiliation-institution")
        append(file("affiliations", id), institution)
      }
      def affiliations(id: String): Vector[String] = {
        val out = mutable.Set.empty[String]
        lines(file("affiliations", id)) { s =>
          out += s; if (out.size > config.maxAffiliations) reject("too-many-affiliations")
        }
        out.toVector.sorted
      }
      // Validate all duplicate metric copies before writing either copy to a cache.
      Vector("metrics/type=researcher_collaboration", "metrics/type=kcore").foreach { name =>
        each(name) { row =>
          val detail = CoreJson
            .parse[ResearcherMetricsDetail](row.render())
            .toOption
            .getOrElse(reject("invalid-researcher-metric"))
          if (SparkAnalyticsValidation.check(detail).isLeft) reject("invalid-researcher-metric")
          val key = StorageKeys.composite(
            detail.researcherId,
            detail.context.windowId.getOrElse(reject("missing-window"))
          )
          // Physical partition columns differ only by dataset path, not row semantics.
          store("metric", key, ujson.read(CoreJson.compact(detail)).asInstanceOf[ujson.Obj])
        }
      }
      each("metrics/type=communities") { row =>
        val c = CoreJson
          .parse[CommunityMembership](row.render())
          .toOption
          .getOrElse(reject("invalid-community-membership"))
        if (SparkAnalyticsValidation.check(c).isLeft) reject("invalid-community-membership")
        store(
          "community",
          StorageKeys
            .composite(c.researcherId, c.context.windowId.getOrElse(reject("missing-window"))),
          ujson.read(CoreJson.compact(c)).asInstanceOf[ujson.Obj]
        )
      }
      each("metrics/type=path_length_estimate") { row =>
        val e = CoreJson
          .parse[PathLengthEstimate](row.render())
          .toOption
          .getOrElse(reject("invalid-path-estimate"))
        if (SparkAnalyticsValidation.check(e).isLeft) reject("invalid-path-estimate")
        store(
          "estimate",
          StorageKeys
            .composite(e.componentId, e.context.windowId.getOrElse(reject("missing-window"))),
          ujson.read(CoreJson.compact(e)).asInstanceOf[ujson.Obj]
        )
      }
      var written = 0L; var unchanged = 0L; var rejected = 0L
      def count(r: StorageResult[?]): Unit = r match {
        case Written(_)    => written += 1
        case Unchanged(_)  => unchanged += 1
        case Retried(_, v) => count(v)
        case _             => rejected += 1
      }
      def link(row: ujson.Obj, sourceId: String, evidence: Vector[String]): Unit = {
        val id = row("nodeId").str; val display = row("label").str
        val candidate = EntityLink(
          "name",
          TextNorm.personName(display),
          policy,
          sourceId,
          id,
          display,
          affiliations(id),
          None,
          run,
          evidence
        )
        count(entityLinks.putLink(candidate))
        row("properties").arr.foreach { p =>
          val name = p("name").str
          if (name == "orcid" || name.startsWith("orcid."))
            count(
              entityLinks.putLink(
                candidate.copy(entityType = "external:orcid", normalizedKey = p("value").str)
              )
            )
        }
      }
      each("nodes/type=researcher") { row =>
        link(row, row("nodeId").str, Vector("nodes/type=researcher", row("nodeId").str))
      }
      each("edges/type=resolves_to") { edge =>
        val mention = lookup("mention", edge("fromId").str).get
        val researcher = lookup("researcher", edge("toId").str).get
        val alias = ujson.read(researcher.render()).asInstanceOf[ujson.Obj]
        alias("label") = mention("label")
        // Only exported applied resolution edges authorize a canonical alias. Raw Phase 5
        // accepted pairs which grouping rejected or left ambiguous are deliberately not loaded.
        link(alias, edge("fromId").str, Vector("edges/type=resolves_to", edge("edgeId").str))
      }
      val metricDirectory = Files.list(index)
      try
        metricDirectory
          .iterator()
          .asScala
          .filter(_.getFileName.toString.startsWith("metric-"))
          .foreach { p =>
            val detail = upickle.default.read[ResearcherMetricsDetail](Files.readString(p, UTF_8));
            val window = detail.context.windowId.get
            val q = ujson.Obj(
              "sourceRun" -> ujson.read(qualifications),
              "communityMembership" -> lookup(
                "community",
                StorageKeys.composite(detail.researcherId, window)
              ).getOrElse(ujson.Null),
              "communityQualification" -> (if (
                                             lookup(
                                               "community",
                                               StorageKeys.composite(detail.researcherId, window)
                                             ).isDefined
                                           ) "observed-source-row"
                                           else "unknown-not-exported"),
              "pathLengthEstimate" -> lookup(
                "estimate",
                StorageKeys.composite(detail.componentId, window)
              ).getOrElse(ujson.Null)
            )
            count(
              metrics.put(
                ResearcherMetricRecord(
                  detail.researcherId,
                  window,
                  detail.policyVersion,
                  run,
                  CoreJson.compact(detail),
                  q.render()
                )
              )
            )
          }
      finally metricDirectory.close()
      val report = CacheLoadReport(written, unchanged, rejected, selected.map(_.rowCount).sum)
      if (rejected > 0) Rejected("cache-write-rejected")
      else if (written == 0) Unchanged(report)
      else Written(report)
    } catch {
      case SourceRejected(c) => Rejected(c)
      case _: Exception      => Rejected("malformed-source-data")
    } finally {
      if (scratch != null) {
        val walk = Files.walk(scratch)
        try
          walk
            .sorted(java.util.Comparator.reverseOrder[Path]())
            .iterator()
            .asScala
            .foreach(Files.deleteIfExists)
        finally walk.close()
      }
    }
  }
}
