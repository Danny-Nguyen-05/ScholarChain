package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import org.apache.hadoop.conf.Configuration
import org.apache.parquet.hadoop.ParquetReader
import org.apache.parquet.hadoop.example.GroupReadSupport
import org.apache.parquet.example.data.Group
import org.apache.parquet.schema.{GroupType, Type, PrimitiveType}
import scala.jdk.CollectionConverters.*
import StorageResult.*

trait CloseableRowIterator extends Iterator[ujson.Obj] with AutoCloseable

/** Reader boundary allows producer fixtures without linking storage to Spark. A row retains every
  * exported column except physical run_id. Partition window is restored from the directory path.
  */
trait ManifestRowReader {
  def open(manifest: LoadManifest): StorageResult[CloseableRowIterator]
  def qualifications(runId: String): StorageResult[String]
}

/** Reads local completed Phase 6 exports only. Remote copying belongs to the explicit composition
  * layer; this adapter never creates a Spark session or calls a cloud provider.
  */
final class LocalParquetManifestReader(root: Path, maxMetadataBytes: Long = 4 * 1024 * 1024)
    extends ManifestRowReader {
  private val base = root.toRealPath()
  private def metadata(name: String): String = {
    val p = base.resolve(name).toRealPath();
    require(p.startsWith(base) && Files.size(p) <= maxMetadataBytes)
    Files.readString(p, UTF_8)
  }
  private def verified(run: String): ujson.Value = {
    val runJson = metadata("run-manifest.json"); val metaJson = metadata("run-metadata.json")
    require(
      metadata("_SCHOLARCHAIN_SPARK_COMPLETE") == StableIds.sha256Hex(
        runJson + "\n" + metaJson
      ) + "\n"
    )
    val m = ujson.read(metaJson)
    require(m("runId").str == run && ujson.read(runJson)("runId").str == run)
    m
  }
  def qualifications(run: String): StorageResult[String] = try {
    val meta = verified(run)
    Found(
      ujson
        .Obj(
          "runMetadata" -> meta,
          "runManifest" -> ujson.read(metadata("run-manifest.json")),
          "counters" -> ujson.read(metadata("counters.json")),
          "interpretation" -> "Community convergence and iteration counts are retained from exported rows; path-length estimates remain seeded-source estimates and approximate P90. No convergence or exact quantile is inferred."
        )
        .render()
    )
  } catch { case _: Exception => Rejected("incomplete-or-corrupt-source-run") }
  def open(m: LoadManifest): StorageResult[CloseableRowIterator] = try {
    val meta = verified(m.context.runId)
    require(m.format == "parquet" && m.paths.nonEmpty)
    require(
      m.context.lineage.hadoopRunId == meta(
        "hadoopRunId"
      ).str && m.context.lineage.entityResolutionRunId == meta(
        "entityResolutionRunId"
      ).str && m.context.lineage.entityResolutionPolicyVersion == meta(
        "entityResolutionPolicyVersion"
      ).str && m.context.lineage.entityResolutionPolicyHash == meta(
        "entityResolutionPolicyHash"
      ).str
    )
    val table = meta("tables").arr.find(_("dataset").str == m.logicalDataset).get
    require(
      ManifestMetadata.rowCount(table("rowCount")).contains(m.rowCount) && table(
        "contentHash"
      ).str == m.sortedRowsSha256
    )
    require(m.paths == Vector(table("path").str))
    // Files.walk streams directories. Sorting file names is unnecessary because table hashes are
    // canonicalized separately; no graph-sized file inventory is retained in driver memory.
    val paths = m.paths.iterator
    val hadoop = new Configuration(false)
    hadoop.set("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
    Found(new CloseableRowIterator {
      private var walk: java.util.stream.Stream[Path] = null
      private var files: Iterator[Path] = Iterator.empty
      private var reader: ParquetReader[Group] = null
      private var currentPath: Path = null
      private var nextRow: Option[ujson.Obj] = None
      private var closed = false
      private def openFile(): Boolean = {
        while (!files.hasNext && paths.hasNext) {
          if (walk != null) walk.close()
          val p = base.resolve(paths.next()).normalize().toRealPath()
          require(p.startsWith(base))
          walk = Files.walk(p)
          files = walk
            .iterator()
            .asScala
            .filter(p => Files.isRegularFile(p) && p.toString.endsWith(".parquet"))
        }
        if (!files.hasNext) false
        else {
          currentPath = files.next().toRealPath(); require(currentPath.startsWith(base))
          reader = ParquetReader
            .builder[Group](new GroupReadSupport, new org.apache.hadoop.fs.Path(currentPath.toUri))
            .withConf(hadoop)
            .build()
          true
        }
      }
      private def advance(): Unit = {
        while (!closed && nextRow.isEmpty) {
          if (reader == null && !openFile()) close()
          if (!closed) {
            val g = reader.read()
            if (g == null) { reader.close(); reader = null }
            else {
              val row = ParquetJson.group(g, g.getType)
              row.obj.remove("run_id")
              if (m.partitionColumns.contains("window") && !row.obj.contains("window")) {
                val window = base
                  .relativize(currentPath)
                  .iterator()
                  .asScala
                  .map(_.toString)
                  .find(_.startsWith("window="))
                  .map(_.stripPrefix("window="))
                  .get
                row("window") = java.net.URLDecoder.decode(window, UTF_8)
              }
              nextRow = Some(row)
            }
          }
        }
      }
      def hasNext: Boolean = { if (nextRow.isEmpty) advance(); nextRow.nonEmpty }
      def next(): ujson.Obj = {
        if (!hasNext) throw new NoSuchElementException("manifest row"); val r = nextRow.get;
        nextRow = None; r
      }
      def close(): Unit = {
        closed = true; if (reader != null) { reader.close(); reader = null };
        if (walk != null) { walk.close(); walk = null }
      }
    })
  } catch { case _: Exception => Rejected("invalid-manifest-source") }
}

/** Phase6Export inserts Scala Long counts into ujson, whose wire representation is a decimal JSON
  * String. Parse that exact representation without floating-point conversion or truncation.
  */
private[storage] object ManifestMetadata {
  def rowCount(value: ujson.Value): Option[Long] = value match {
    case ujson.Str(text) if text.nonEmpty && text.forall(c => c >= '0' && c <= '9') =>
      text.toLongOption.filter(_ >= 0)
    case _ => None
  }
}

private[storage] object ParquetJson {
  def group(g: Group, t: GroupType): ujson.Obj = {
    val result = ujson.Obj()
    t.getFields.asScala.zipWithIndex.foreach { case (field, i) =>
      val count = g.getFieldRepetitionCount(i)
      result(field.getName) =
        if (count == 0) ujson.Null
        else if (field.getRepetition == Type.Repetition.REPEATED)
          ujson.Arr.from((0 until count).map(n => value(g, field, i, n)))
        else value(g, field, i, 0)
    }
    result
  }
  private def value(g: Group, t: Type, i: Int, n: Int): ujson.Value = {
    if (t.isPrimitive) t.asPrimitiveType().getPrimitiveTypeName match {
      case PrimitiveType.PrimitiveTypeName.BINARY |
          PrimitiveType.PrimitiveTypeName.FIXED_LEN_BYTE_ARRAY =>
        ujson.Str(g.getBinary(i, n).toStringUsingUTF8)
      case PrimitiveType.PrimitiveTypeName.INT32 => ujson.Num(g.getInteger(i, n))
      case PrimitiveType.PrimitiveTypeName.INT64 =>
        val value = g.getLong(i, n)
        if (value < -9007199254740991L || value > 9007199254740991L)
          throw SourceRejected("integer-outside-exact-json-range")
        ujson.Num(value.toDouble)
      case PrimitiveType.PrimitiveTypeName.FLOAT   => ujson.Num(g.getFloat(i, n).toDouble)
      case PrimitiveType.PrimitiveTypeName.DOUBLE  => ujson.Num(g.getDouble(i, n))
      case PrimitiveType.PrimitiveTypeName.BOOLEAN => ujson.Bool(g.getBoolean(i, n))
      case _ => throw new IllegalArgumentException("unsupported parquet primitive")
    }
    else {
      val child = g.getGroup(i, n); val typ = t.asGroupType()
      val logical = Option(t.getLogicalTypeAnnotation).map(_.toString).getOrElse("")
      if (logical == "LIST" || Option(t.getOriginalType).exists(_.toString == "LIST")) {
        val repeated = typ.getType(0)
        val values = (0 until child.getFieldRepetitionCount(0)).map { j =>
          if (repeated.isPrimitive) value(child, repeated, 0, j)
          else {
            val wrapper = child.getGroup(0, j)
            if (wrapper.getFieldRepetitionCount(0) == 0) ujson.Null
            else value(wrapper, repeated.asGroupType().getType(0), 0, 0)
          }
        }
        ujson.Arr.from(values)
      } else group(child, typ)
    }
  }
}
final case class CacheLoaderConfig(
    sortChunkRows: Int = 1000,
    maxRowBytes: Int = 1024 * 1024,
    maxAffiliations: Int = 100,
    scratchDirectory: Option[Path] = None
) {
  require(sortChunkRows > 0 && maxRowBytes > 0 && maxAffiliations > 0)
}
final case class CacheLoadReport(
    written: Long,
    unchanged: Long,
    rejected: Long,
    validatedRows: Long
)
