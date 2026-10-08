package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{FileSystem, Path => HPath}
import org.apache.hadoop.io.{LongWritable, Text}
import org.apache.hadoop.io.compress.CompressionCodecFactory
import org.apache.hadoop.mapreduce.lib.input.FileSplit
import org.apache.hadoop.mapreduce.{InputSplit, JobContext, RecordReader, TaskAttemptContext}

import java.io.InputStream
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import java.security.MessageDigest

/** Hadoop paths for local files and `s3`, `s3a`, `s3n`, and `hdfs` inputs. Those URIs stay
  * `org.apache.hadoop.fs.Path` values. They are not resolved with `java.nio.file.Path`. A local
  * relative path is resolved from the process working directory.
  */
object FsPaths {
  def isRemote(spec: String): Boolean = {
    val lower = spec.trim.toLowerCase(java.util.Locale.ROOT)
    lower.startsWith("s3://") || lower.startsWith("s3a://") || lower.startsWith("s3n://") ||
    lower.startsWith("hdfs://")
  }

  def file(spec: String): HPath = {
    val trimmed = spec.trim
    if (isRemote(trimmed) || trimmed.contains("://") || isFileUri(trimmed)) new HPath(trimmed)
    else new HPath(Path.of(trimmed).toAbsolutePath.normalize.toUri)
  }

  /** `file:/absolute/path` has a scheme and one slash. It is not a relative path named `file:`. */
  private def isFileUri(spec: String): Boolean =
    spec.toLowerCase(java.util.Locale.ROOT).startsWith("file:")

  def child(parent: HPath, name: String): HPath = new HPath(parent, name)

  def runPath(outputRoot: String, runId: String): HPath = {
    val root = outputRoot.trim
    val directory = HadoopPrepPipeline.directoryName(runId)
    if (isRemote(root)) {
      val base = if (root.endsWith("/")) root.dropRight(1) else root
      new HPath(s"$base/$directory")
    } else new HPath(Path.of(root).toAbsolutePath.normalize.resolve(directory).toUri)
  }

  def local(path: HPath): Path = Path.of(path.toUri)
}

object FsIO {
  private val overlays = new ThreadLocal[java.util.Map[String, String]]

  /** Fresh configuration plus the thread-local test overlay. */
  def configuration(): Configuration = configuration(new Configuration())

  /** Copies `base`, including `fs.*` and `-D` settings and its class loader, then applies the
    * thread-local test overlay. Production driver calls pass the request configuration here.
    */
  def configuration(base: Configuration): Configuration = {
    val conf = new Configuration(base)
    val loader = base.getClassLoader
    if (loader != null) conf.setClassLoader(loader)
    val extra = overlays.get()
    if (extra != null)
      extra.forEach((key, value) => conf.set(key, value))
    conf
  }

  /** Test hook for a Hadoop `FileSystem` implementation. Production calls leave this empty. */
  def withSettings[T](settings: (String, String)*)(body: => T): T = {
    val map = new java.util.HashMap[String, String]
    settings.foreach { case (key, value) => map.put(key, value) }
    overlays.set(map)
    try body
    finally overlays.remove()
  }

  def filesystem(path: HPath, conf: Configuration): FileSystem = path.getFileSystem(conf)

  def isFile(path: HPath, conf: Configuration): Boolean =
    try {
      val fs = filesystem(path, conf)
      fs.isFile(path)
    } catch { case _: Exception => false }

  def exists(path: HPath, conf: Configuration): Boolean =
    try filesystem(path, conf).exists(path)
    catch { case _: Exception => false }

  def mkdirs(path: HPath, conf: Configuration): Unit = {
    filesystem(path, conf).mkdirs(path)
    ()
  }

  def writeUtf8(path: HPath, text: String, conf: Configuration): Unit = {
    val fs = filesystem(path, conf)
    val parent = path.getParent
    if (parent != null) fs.mkdirs(parent)
    val out = fs.create(path, true)
    try out.write(text.getBytes(StandardCharsets.UTF_8))
    finally out.close()
  }

  def readUtf8(path: HPath, conf: Configuration): String = {
    val in = filesystem(path, conf).open(path)
    try new String(in.readAllBytes(), StandardCharsets.UTF_8)
    finally in.close()
  }

  def length(path: HPath, conf: Configuration): Long =
    filesystem(path, conf).getFileStatus(path).getLen

  def sha256(path: HPath, conf: Configuration): String = {
    val digest = MessageDigest.getInstance("SHA-256")
    val buffer = new Array[Byte](8192)
    val in = filesystem(path, conf).open(path)
    try {
      var n = in.read(buffer)
      while (n >= 0) {
        if (n > 0) digest.update(buffer, 0, n)
        n = in.read(buffer)
      }
    } finally in.close()
    digest.digest().map(byte => f"${byte & 0xff}%02x").mkString
  }

  def listFiles(dir: HPath, conf: Configuration): Vector[HPath] = {
    val fs = filesystem(dir, conf)
    if (!fs.exists(dir)) Vector.empty
    else {
      val out = scala.collection.mutable.ArrayBuffer.empty[HPath]
      def walk(path: HPath): Unit = {
        val statuses = fs.listStatus(path)
        statuses.foreach { status =>
          if (status.isDirectory) walk(status.getPath)
          else out += status.getPath
        }
      }
      if (fs.getFileStatus(dir).isDirectory) walk(dir) else out += dir
      out.toVector
    }
  }
}

/** Authoritative acquisition metadata from `datasets/acquisition-index.v1.json`. */
object Acquisition {
  final case class SourceMeta(
      snapshotId: String,
      retrievalDate: String,
      committedSample: String,
      sha256: String
  )

  val fileName = "datasets/acquisition-index.v1.json"

  def findIndex(start: Path = Path.of("").toAbsolutePath): Option[Path] = {
    var cursor: Path = start
    var found: Option[Path] = None
    while (cursor != null && found.isEmpty) {
      val candidate = cursor.resolve(fileName)
      if (Files.isRegularFile(candidate)) found = Some(candidate)
      cursor = cursor.getParent
    }
    found
  }

  def load(path: Path): Either[String, Map[SourceType, SourceMeta]] =
    try {
      val root = ujson.read(Files.readString(path)).obj
      def one(name: String, source: SourceType): Either[String, (SourceType, SourceMeta)] = {
        root.get(name).flatMap(_.objOpt) match {
          case None => Left(s"acquisition index missing $name")
          case Some(obj) =>
            def text(field: String): Either[String, String] =
              obj.value.get(field).collect {
                case ujson.Str(value) if value.trim.nonEmpty => value
              } match {
                case Some(value) => Right(value)
                case None        => Left(s"acquisition index $name.$field is missing")
              }
            for {
              snapshot <- text("snapshotId")
              retrieval <- text("retrievalDate")
              sample <- text("committedSample")
              hash <- text("sha256")
            } yield source -> SourceMeta(snapshot, retrieval, sample, hash)
        }
      }
      for {
        dblp <- one("dblp", SourceType.Dblp)
        openAlex <- one("openalex", SourceType.OpenAlex)
        crossref <- one("crossref", SourceType.Crossref)
        orcid <- one("orcid", SourceType.Orcid)
      } yield Map(dblp, openAlex, crossref, orcid)
    } catch {
      case error: Exception =>
        Left(s"acquisition index unreadable: ${Option(error.getMessage).getOrElse(error.toString)}")
    }

  def committedFile(index: Path, meta: SourceMeta): Path =
    index.getParent.resolve(meta.committedSample).toAbsolutePath.normalize

  /** Sample paths take snapshot id, retrieval date, and checksum from the index. Any other path
    * needs an explicit snapshot id and retrieval date. A sample label is not applied silently.
    */
  def bind(
      source: SourceType,
      input: String,
      snapshots: Map[SourceType, String],
      retrievalDates: Map[SourceType, String],
      conf: Configuration
  ): Either[String, (String, String, String)] = {
    val hadoopPath = FsPaths.file(input)
    if (!FsIO.isFile(hadoopPath, conf)) Left(s"missing input $hadoopPath")
    else {
      val streamed = FsIO.sha256(hadoopPath, conf)
      localFile(hadoopPath) match {
        case None =>
          explicit(source, input, snapshots, retrievalDates, streamed)
        case Some(absolute) =>
          findIndex(absolute).orElse(findIndex()) match {
            case None =>
              explicit(source, input, snapshots, retrievalDates, streamed)
            case Some(indexPath) =>
              load(indexPath) match {
                case Left(message) => Left(message)
                case Right(index) =>
                  index.get(source) match {
                    case Some(meta) if sameFile(absolute, committedFile(indexPath, meta)) =>
                      if (streamed != meta.sha256)
                        Left(
                          s"${source.wire} checksum does not match the acquisition index for ${meta.snapshotId}"
                        )
                      else Right((meta.snapshotId, meta.retrievalDate, streamed))
                    case _ =>
                      explicit(source, input, snapshots, retrievalDates, streamed)
                  }
              }
          }
      }
    }
  }

  /** `file` URIs can be compared with the committed sample. Remote schemes stay Hadoop paths. */
  private def localFile(path: HPath): Option[Path] = {
    val scheme = Option(path.toUri.getScheme).map(_.toLowerCase(java.util.Locale.ROOT))
    scheme match {
      case None | Some("file") =>
        try Some(Path.of(path.toUri).toAbsolutePath.normalize)
        catch { case _: Exception => None }
      case _ => None
    }
  }

  private def explicit(
      source: SourceType,
      input: String,
      snapshots: Map[SourceType, String],
      retrievalDates: Map[SourceType, String],
      checksum: String
  ): Either[String, (String, String, String)] =
    (
      snapshots.get(source).filter(_.trim.nonEmpty),
      retrievalDates.get(source).filter(_.trim.nonEmpty)
    ) match {
      case (Some(snapshot), Some(retrieval)) => Right((snapshot, retrieval, checksum))
      case _ =>
        Left(
          s"input $input is not the committed ${source.wire} sample; pass an explicit snapshot id and retrieval date"
        )
    }

  private def sameFile(left: Path, right: Path): Boolean =
    try Files.isSameFile(left, right)
    catch { case _: Exception => false }
}

object SampleBound {
  def install(conf: Configuration, inputs: Seq[HPath]): Unit = {
    if (conf.getBoolean(ConfKeys.SampleReady, false)) return
    var remaining = conf.getInt(ConfKeys.MaxSample, Int.MaxValue)
    inputs.zipWithIndex.foreach { case (path, index) =>
      val qualified = path.getFileSystem(conf).makeQualified(path)
      val (cutoff, accepted) =
        if (remaining <= 0) (0L, 0)
        else scan(qualified, remaining, conf)
      conf.set(ConfKeys.samplePath(index), qualified.toString)
      conf.setLong(ConfKeys.sampleCutoff(index), cutoff)
      remaining -= accepted
    }
    conf.setInt(ConfKeys.SampleCount, inputs.size)
    conf.setBoolean(ConfKeys.SampleReady, true)
  }

  /** Cutoff lookup uses the qualified URI. A shared basename such as `works.jsonl` is not a match.
    */
  def cutoff(conf: Configuration, path: HPath): Long = {
    val count = conf.getInt(ConfKeys.SampleCount, 0)
    if (count == 0) Long.MaxValue
    else {
      val qualified =
        try path.getFileSystem(conf).makeQualified(path).toString
        catch { case _: Exception => path.toString }
      var index = 0
      var found = Long.MaxValue
      while (index < count) {
        val configured = conf.get(ConfKeys.samplePath(index), "")
        if (configured == qualified)
          found = conf.getLong(ConfKeys.sampleCutoff(index), Long.MaxValue)
        index += 1
      }
      found
    }
  }

  private def scan(path: HPath, limit: Int, conf: Configuration): (Long, Int) = {
    val name = path.getName.toLowerCase(java.util.Locale.ROOT)
    if (name.endsWith(".xml") || name.endsWith(".xml.gz")) scanXml(path, limit, conf)
    else scanLines(path, limit, conf)
  }

  private def scanLines(path: HPath, limit: Int, conf: Configuration): (Long, Int) = {
    val in = open(path, conf)
    try {
      var pos = 0L
      var lineStart = 0L
      var empty = true
      var count = 0
      var byte = in.read()
      while (byte >= 0 && count < limit) {
        if (byte == '\n') {
          if (!empty) count += 1
          lineStart = pos + 1
          empty = true
        } else if (byte != '\r') empty = false
        pos += 1
        byte = in.read()
      }
      if (!empty && byte < 0) count += 1
      val cutoff = if (count >= limit && byte >= 0) lineStart else Long.MaxValue
      (cutoff, math.min(count, limit))
    } finally in.close()
  }

  private def scanXml(path: HPath, limit: Int, conf: Configuration): (Long, Int) = {
    val in = open(path, conf)
    try {
      val prepared = DblpPieces.headerAndBody(in, 65536)
      val stream = new PosStream(prepared._2)
      val cutoff = DblpSplitReader.offsetAfter(stream, limit)
      val accepted = if (cutoff == Long.MaxValue) countXml(path, conf) else limit
      (cutoff, accepted)
    } finally in.close()
  }

  private def countXml(path: HPath, conf: Configuration): Int = {
    val in = open(path, conf)
    try {
      val prepared = DblpPieces.headerAndBody(in, 65536)
      val stream = new PosStream(prepared._2)
      var seen = 0
      var open = DblpSplitReader.nextOpen(stream, Long.MaxValue)
      while (open.nonEmpty) {
        DblpSplitReader.readElement(stream, open.get, 0L)
        seen += 1
        open = DblpSplitReader.nextOpen(stream, Long.MaxValue)
      }
      seen
    } finally in.close()
  }

  private def open(path: HPath, conf: Configuration): InputStream = {
    val fs = path.getFileSystem(conf)
    val raw = fs.open(path)
    val codec = new CompressionCodecFactory(conf).getCodec(path)
    if (codec == null) raw else codec.createInputStream(raw)
  }
}

/** Line reader that enforces a byte cap before allocating the line as a `String`. J01 and J02 keep
  * the source `maxRecordBytes` cap. J03–J09 set [[ConfKeys.BoundedLineBytes]] to the intermediate
  * cap. Excess bytes are drained to the next newline. The value is a short diagnostic, not the
  * original line.
  */
final class BoundedLineInputFormat
    extends org.apache.hadoop.mapreduce.lib.input.FileInputFormat[LongWritable, Text] {
  override def createRecordReader(
      split: InputSplit,
      context: TaskAttemptContext
  ): RecordReader[LongWritable, Text] = new BoundedLineRecordReader

  override protected def isSplitable(context: JobContext, filename: HPath): Boolean = {
    val codec = new CompressionCodecFactory(context.getConfiguration).getCodec(filename)
    codec == null
  }
}

final class BoundedLineRecordReader extends RecordReader[LongWritable, Text] {
  private val key = new LongWritable
  private val value = new Text
  private var in: InputStream = _
  private var start = 0L
  private var end = Long.MaxValue
  private var pos = 0L
  private var maxBytes = Int.MaxValue
  private var compressed = false
  private var opened = false
  private var qualifiedPath = ""
  private var processingRun = ""

  override def initialize(split: InputSplit, context: TaskAttemptContext): Unit = {
    val fileSplit = split.asInstanceOf[FileSplit]
    val conf = context.getConfiguration
    processingRun = Option(conf.get(ConfKeys.RunId)).getOrElse("")
    val bounded = conf.getLong(ConfKeys.BoundedLineBytes, -1L)
    val configured =
      if (bounded > 0) bounded
      else conf.getLong(ConfKeys.MaxRecordBytes, Int.MaxValue.toLong)
    maxBytes = math.min(math.max(configured, 1L), Int.MaxValue.toLong).toInt
    val path = fileSplit.getPath
    val fs = path.getFileSystem(conf)
    qualifiedPath = fs.makeQualified(path).toString
    val codec = new CompressionCodecFactory(conf).getCodec(path)
    val raw = fs.open(path)
    if (codec != null) {
      compressed = true
      in = codec.createInputStream(raw)
      start = 0L
      end = Long.MaxValue
      pos = 0L
    } else {
      start = fileSplit.getStart
      end = start + fileSplit.getLength
      if (start > 0) raw.seek(start)
      in = raw
      pos = start
      if (start > 0 && !lineBoundary(fs, path, start)) {
        var byte = readRaw()
        while (byte >= 0 && byte != '\n') byte = readRaw()
      }
    }
    opened = true
  }

  override def nextKeyValue(): Boolean = {
    if (!compressed && pos >= end) return false
    val lineStart = pos
    val body = new java.io.ByteArrayOutputStream
    val excerpt = new java.io.ByteArrayOutputStream
    val prefix = new java.io.ByteArrayOutputStream
    var prefixFinished = false
    var total = 0L
    var overflow = false
    var byte = readRaw()
    if (byte < 0) return false
    while (byte >= 0 && byte != '\n') {
      total += 1
      if (total > maxBytes.toLong) overflow = true
      if (excerpt.size() < 180) excerpt.write(byte)
      if (!prefixFinished) {
        if (byte == '\t') prefixFinished = true
        else if (prefix.size() < Lineage.MaxPrefixBytes) prefix.write(byte)
      }
      if (!overflow) body.write(byte)
      byte = readRaw()
    }
    key.set(lineStart)
    if (overflow) {
      val preview = new String(excerpt.toByteArray, StandardCharsets.UTF_8).replace('\n', ' ')
      val lineage =
        if (prefixFinished) Lineage.prefix(new String(prefix.toByteArray, StandardCharsets.UTF_8))
        else None
      val locator = Lineage.overflowLocator(qualifiedPath, lineStart, lineage, processingRun)
      value.set(OverflowLines.encode(total, preview, lineage, locator))
    } else value.set(body.toByteArray)
    true
  }

  private def readRaw(): Int = {
    val byte = in.read()
    if (byte >= 0) pos += 1
    byte
  }

  private def readByte(): Int = readRaw()

  private def lineBoundary(fs: FileSystem, path: HPath, start: Long): Boolean =
    if (start <= 0) true
    else {
      val probe = fs.open(path)
      try {
        probe.seek(start - 1)
        val previous = probe.read()
        previous == '\n' || previous == '\r'
      } finally probe.close()
    }

  override def getCurrentKey: LongWritable = key
  override def getCurrentValue: Text = value
  override def getProgress: Float =
    if (end <= start) 1f else math.min(1f, (pos - start).toFloat / (end - start).toFloat)
  override def close(): Unit =
    if (in != null) in.close()
}
