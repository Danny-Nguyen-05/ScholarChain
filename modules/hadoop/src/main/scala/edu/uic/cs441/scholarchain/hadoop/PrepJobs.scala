package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{Path => HPath}
import org.apache.hadoop.io.compress.CompressionCodec
import org.apache.hadoop.io.{LongWritable, NullWritable, Text}
import org.apache.hadoop.mapreduce.{Job, Mapper, Reducer}
import org.apache.hadoop.mapreduce.lib.input.{FileInputFormat, MultipleInputs}
import org.apache.hadoop.mapreduce.lib.output.{FileOutputFormat, MultipleOutputs, TextOutputFormat}

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.jdk.CollectionConverters.*

object PrepJobs {
  def configuration(
      config: HadoopPrepConfig,
      runId: String,
      snapshots: Map[SourceType, String],
      parent: Configuration = new Configuration()
  ): Configuration = {
    require(
      snapshots.values.forall(Lineage.snapshotFits),
      s"dataset snapshot exceeds bounded lineage metadata limit ${Lineage.MaxSnapshotBytes} UTF-8 bytes"
    )
    val conf = new Configuration(parent)
    val loader = parent.getClassLoader
    if (loader != null) conf.setClassLoader(loader)
    config.executionMode match {
      case HadoopExecutionMode.Local =>
        conf.set("mapreduce.framework.name", "local")
        conf.set("mapreduce.jobtracker.address", "local")
      case HadoopExecutionMode.Cluster =>
        conf.set("mapreduce.framework.name", "yarn")
        conf.unset("mapreduce.jobtracker.address")
    }
    conf.set(ConfKeys.ExecutionMode, config.executionMode.wire)
    conf.setBoolean("mapreduce.job.ubertask.enable", false)
    conf.setInt("mapreduce.job.reduces", config.reducerCount)
    conf.set(ConfKeys.RunId, runId)
    conf.setLong(ConfKeys.MaxRecordBytes, config.maxRecordBytes)
    conf.setLong(ConfKeys.MaxIntermediateBytes, IntermediateBytes.cap(config.maxRecordBytes))
    conf.setLong(ConfKeys.MaxXmlEntityExpansion, config.maxXmlEntityExpansion)
    conf.setInt(ConfKeys.MaxBlock, config.maxCandidateBlockSize)
    conf.setInt(ConfKeys.MaxPairs, config.maxCandidatePairsPerBlock)
    conf.setInt(ConfKeys.MaxTeam, config.maxAuthorTeamSize)
    conf.setInt(ConfKeys.MaxSample, config.maxLocalSampleRecords)
    conf.set(ConfKeys.SnapshotDblp, snapshots(SourceType.Dblp))
    conf.set(ConfKeys.SnapshotOpenAlex, snapshots(SourceType.OpenAlex))
    conf.set(ConfKeys.SnapshotCrossref, snapshots(SourceType.Crossref))
    conf.set(ConfKeys.SnapshotOrcid, snapshots(SourceType.Orcid))
    conf.setBoolean(ConfKeys.IntermediateCompression, config.intermediateCompressionEnabled)
    conf.set(ConfKeys.CompressionCodec, config.compressionCodec)
    conf.setBoolean("mapreduce.map.output.compress", false)
    if (config.intermediateCompressionEnabled) codecClass(config.compressionCodec)
    conf
  }

  def codecClass(name: String): Class[? <: CompressionCodec] = {
    val mapped = name match {
      case "gzip" | "GzipCodec"         => "org.apache.hadoop.io.compress.GzipCodec"
      case "default" | "DefaultCodec"   => "org.apache.hadoop.io.compress.DefaultCodec"
      case "bzip2" | "BZip2Codec"       => "org.apache.hadoop.io.compress.BZip2Codec"
      case other if other.contains('.') => other
      case other                        => "org.apache.hadoop.io.compress." + other
    }
    Class.forName(mapped).asInstanceOf[Class[? <: CompressionCodec]]
  }

  private def compressIntermediate(job: Job): Unit = {
    val conf = job.getConfiguration
    if (conf.getBoolean(ConfKeys.IntermediateCompression, false)) {
      FileOutputFormat.setCompressOutput(job, true)
      FileOutputFormat.setOutputCompressorClass(
        job,
        codecClass(conf.get(ConfKeys.CompressionCodec))
      )
    }
  }

  def run(name: String, job: Job): Unit =
    if (!job.waitForCompletion(true))
      throw new IllegalStateException(s"$name failed")

  private def hadoopPath(path: Path): HPath = new HPath(path.toUri)

  def dblp(conf: Configuration, input: String, output: Path, splitMax: Option[Long]): Job =
    dblp(conf, input, hadoopPath(output), splitMax)

  def dblp(conf: Configuration, input: String, output: HPath, splitMax: Option[Long]): Job = {
    val job = newJob(conf, "J01-DblpExtract")
    job.setJarByClass(classOf[DblpExtractMapper])
    job.setMapperClass(classOf[DblpExtractMapper])
    job.setReducerClass(classOf[PassReducer])
    job.setMapOutputKeyClass(classOf[Text])
    job.setMapOutputValueClass(classOf[Text])
    job.setOutputKeyClass(classOf[Text])
    job.setOutputValueClass(classOf[Text])
    job.setInputFormatClass(classOf[DblpXmlInputFormat])
    job.setNumReduceTasks(conf.getInt("mapreduce.job.reduces", 1))
    val inputPath = FsPaths.file(input)
    if (!job.getConfiguration.getBoolean(ConfKeys.SampleReady, false))
      SampleBound.install(job.getConfiguration, Seq(inputPath))
    FileInputFormat.addInputPath(job, inputPath)
    splitMax.foreach(size => FileInputFormat.setMaxInputSplitSize(job, size))
    FileOutputFormat.setOutputPath(job, output)
    compressIntermediate(job)
    job
  }

  def normalize(
      conf: Configuration,
      openAlex: String,
      crossref: String,
      orcid: String,
      output: Path
  ): Job =
    normalize(conf, openAlex, crossref, orcid, hadoopPath(output))

  def normalize(
      conf: Configuration,
      openAlex: String,
      crossref: String,
      orcid: String,
      output: HPath
  ): Job = {
    val job = newJob(conf, "J02-SourceNormalize")
    job.setJarByClass(classOf[OpenAlexMapper])
    val inputs = Seq(openAlex, crossref, orcid).map(FsPaths.file)
    if (!job.getConfiguration.getBoolean(ConfKeys.SampleReady, false))
      SampleBound.install(job.getConfiguration, inputs)
    MultipleInputs.addInputPath(
      job,
      inputs(0),
      classOf[BoundedLineInputFormat],
      classOf[OpenAlexMapper]
    )
    MultipleInputs.addInputPath(
      job,
      inputs(1),
      classOf[BoundedLineInputFormat],
      classOf[CrossrefMapper]
    )
    MultipleInputs.addInputPath(
      job,
      inputs(2),
      classOf[BoundedLineInputFormat],
      classOf[OrcidMapper]
    )
    job.setReducerClass(classOf[PassReducer])
    job.setMapOutputKeyClass(classOf[Text])
    job.setMapOutputValueClass(classOf[Text])
    job.setOutputKeyClass(classOf[Text])
    job.setOutputValueClass(classOf[Text])
    job.setNumReduceTasks(conf.getInt("mapreduce.job.reduces", 1))
    FileOutputFormat.setOutputPath(job, output)
    compressIntermediate(job)
    job
  }

  def index(conf: Configuration, inputs: Seq[Path], output: Path): Job =
    index(conf, inputs.map(hadoopPath), hadoopPath(output))

  def index(conf: Configuration, inputs: Seq[HPath], output: HPath): Job =
    keyed(
      conf,
      "J03-ExactIdentifierIndex",
      classOf[IndexMapper],
      classOf[PassReducer],
      inputs,
      output
    )

  def join(conf: Configuration, inputs: Seq[Path], output: Path): Job =
    join(conf, inputs.map(hadoopPath), hadoopPath(output))

  def join(conf: Configuration, inputs: Seq[HPath], output: HPath): Job =
    keyed(
      conf,
      "J04-ExactIdentifierJoin",
      classOf[JoinMapper],
      classOf[JoinReducer],
      inputs,
      output
    )

  def block(conf: Configuration, input: Path, output: Path): Job =
    block(conf, hadoopPath(input), hadoopPath(output))

  def block(conf: Configuration, input: HPath, output: HPath): Job =
    keyed(conf, "J05-BlockingKey", classOf[BlockMapper], classOf[BlockReducer], Seq(input), output)

  def candidates(conf: Configuration, input: Path, output: Path): Job =
    candidates(conf, hadoopPath(input), hadoopPath(output))

  def candidates(conf: Configuration, input: HPath, output: HPath): Job =
    keyed(
      conf,
      "J06-CandidateJoin",
      classOf[CandidateMapper],
      classOf[CandidateReducer],
      Seq(input),
      output
    )

  def teams(conf: Configuration, inputs: Seq[Path], output: Path): Job =
    teams(conf, inputs.map(hadoopPath), hadoopPath(output))

  def teams(conf: Configuration, inputs: Seq[HPath], output: HPath): Job =
    keyed(conf, "J07-PublicationTeam", classOf[TeamMapper], classOf[PassReducer], inputs, output)

  def pairExpansion(conf: Configuration, inputs: Seq[Path], output: Path): Job =
    pairExpansion(conf, inputs.map(hadoopPath), hadoopPath(output))

  def pairExpansion(conf: Configuration, inputs: Seq[HPath], output: HPath): Job =
    keyed(
      conf,
      "J08-CoauthorPairExpansion",
      classOf[PairMapper],
      classOf[PassReducer],
      inputs,
      output
    )

  def exportJob(conf: Configuration, inputs: Seq[Path], output: Path): Job =
    exportJob(conf, inputs.map(hadoopPath), hadoopPath(output))

  def exportJob(conf: Configuration, inputs: Seq[HPath], output: HPath): Job = {
    val job = newJob(conf, "J09-GraphCandidateExport")
    job.setJarByClass(classOf[ExportMapper])
    job.setMapperClass(classOf[ExportMapper])
    job.setReducerClass(classOf[ExportReducer])
    job.setMapOutputKeyClass(classOf[Text])
    job.setMapOutputValueClass(classOf[Text])
    job.setOutputKeyClass(classOf[Text])
    job.setOutputValueClass(classOf[NullWritable])
    job.setNumReduceTasks(conf.getInt("mapreduce.job.reduces", 1))
    job.setInputFormatClass(classOf[BoundedLineInputFormat])
    useIntermediateCap(job)
    inputs.foreach(path => FileInputFormat.addInputPath(job, path))
    FileOutputFormat.setOutputPath(job, output)
    FileOutputFormat.setCompressOutput(job, false)
    job.getConfiguration.set("mapreduce.output.textoutputformat.separator", "")
    MultipleOutputs.addNamedOutput(
      job,
      "json",
      classOf[TextOutputFormat[Text, NullWritable]],
      classOf[Text],
      classOf[NullWritable]
    )
    job
  }

  private def keyed(
      conf: Configuration,
      name: String,
      mapper: Class[? <: Mapper[?, ?, ?, ?]],
      reducer: Class[? <: Reducer[?, ?, ?, ?]],
      inputs: Seq[HPath],
      output: HPath
  ): Job = {
    val job = newJob(conf, name)
    job.setJarByClass(mapper)
    job.setMapperClass(mapper)
    job.setReducerClass(reducer)
    job.setMapOutputKeyClass(classOf[Text])
    job.setMapOutputValueClass(classOf[Text])
    job.setOutputKeyClass(classOf[Text])
    job.setOutputValueClass(classOf[Text])
    job.setInputFormatClass(classOf[BoundedLineInputFormat])
    useIntermediateCap(job)
    job.setNumReduceTasks(conf.getInt("mapreduce.job.reduces", 1))
    inputs.foreach(path => FileInputFormat.addInputPath(job, path))
    FileOutputFormat.setOutputPath(job, output)
    if (name != "J09-GraphCandidateExport") compressIntermediate(job)
    job
  }

  /** `Job.getInstance` copies properties and drops the caller's class loader. `fs.*`
    * implementations set only on that loader must stay visible to the job.
    */
  private def newJob(conf: Configuration, name: String): Job = {
    val job = Job.getInstance(conf, name)
    val loader = conf.getClassLoader
    if (loader != null) job.getConfiguration.setClassLoader(loader)
    job
  }

  /** J03–J09 read domain JSON, which is larger than the source record. The cap stays in this
    * module: at least 1 MiB, at most 16 MiB, and at least the source cap.
    */
  private def useIntermediateCap(job: Job): Unit = {
    val conf = job.getConfiguration
    val cap = conf.getLong(
      ConfKeys.MaxIntermediateBytes,
      IntermediateBytes.cap(conf.getLong(ConfKeys.MaxRecordBytes, IntermediateBytes.Floor))
    )
    conf.setLong(ConfKeys.BoundedLineBytes, cap)
  }

  def counters(job: Job): Map[String, Long] = {
    val group = job.getCounters.findCounter(PrepCounters.Group, PrepCounters.Input)
    val _ = group
    val found = job.getCounters.getGroup(PrepCounters.Group)
    PrepCounters.All.map { name =>
      val value = if (found == null) 0L else found.findCounter(name).getValue
      name -> value
    }.toMap
  }
}

final class PassReducer extends Reducer[Text, Text, Text, Text] {
  override def reduce(
      key: Text,
      values: java.lang.Iterable[Text],
      context: Reducer[Text, Text, Text, Text]#Context
  ): Unit = {
    val copy = new Text
    values.forEach { value =>
      copy.set(value)
      context.write(key, copy)
    }
  }
}

final class DblpExtractMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J01")
    val sink = TaskSink.from(context, TaskSink.runId(context))
    val snapshot = context.getConfiguration.get(ConfKeys.SnapshotDblp)
    sink.count(PrepCounters.Input, 1)
    val cutoff = SplitCutoff(context)
    if (key.get >= cutoff) {
      sink.reject(
        Some(SourceType.Dblp),
        key.toString,
        Some(snapshot),
        PreparationStage.Parse,
        RejectReasonCode.OversizeRecord,
        "maxLocalSampleRecords"
      )
      return
    }
    val text = value.toString
    val splitAt = text.indexOf('\n')
    if (splitAt < 0) {
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.Parse,
        RejectReasonCode.MalformedRecord,
        text
      )
      return
    }
    val meta = ujson.read(text.substring(0, splitAt)).obj
    val xml = text.substring(splitAt + 1)
    val unsafe = meta.get("unsafe").collect { case ujson.Str(text) => text }
    val oversize = meta.get("oversize").contains(ujson.True)
    val unterminated = meta.get("unterminated").contains(ujson.True)
    val malformed = meta.get("malformed").contains(ujson.True)
    if (unterminated || malformed) {
      sink.reject(
        Some(SourceType.Dblp),
        key.toString,
        Some(snapshot),
        PreparationStage.Parse,
        RejectReasonCode.MalformedRecord,
        if (unterminated) "unterminated record" else "malformed closing tag"
      )
      return
    }
    if (oversize) {
      sink.reject(
        Some(SourceType.Dblp),
        key.toString,
        Some(snapshot),
        PreparationStage.Parse,
        RejectReasonCode.OversizeRecord,
        xml
      )
      return
    }
    if (unsafe.nonEmpty) {
      sink.reject(
        Some(SourceType.Dblp),
        key.toString,
        Some(snapshot),
        PreparationStage.Parse,
        RejectReasonCode.UnsafeEntity,
        unsafe.get
      )
      return
    }
    val entityMap =
      meta.get("entities").flatMap(_.objOpt).getOrElse(Map.empty[String, ujson.Value])
    val entities = entityMap.collect { case (name, ujson.Str(body)) => name -> body }.toMap
    val limits = TaskSink.limits(context)
    DblpRecords
      .parse(
        xml,
        DblpXml.Header(entities, None),
        sink.runId,
        snapshot,
        s"dblp@$key",
        limits.maxRecordBytes,
        limits.maxXmlEntityExpansion,
        Option(context.getConfiguration.get(ConfKeys.RetrievalDblp)).filter(_.nonEmpty)
      )
      .foreach(record => sink.emit(record, key.toString))
  }
}

private object SplitCutoff {
  def apply(context: org.apache.hadoop.mapreduce.MapContext[?, ?, ?, ?]): Long = {
    val path = filePath(context.getInputSplit)
    if (path == null) Long.MaxValue else SampleBound.cutoff(context.getConfiguration, path)
  }

  private def filePath(split: org.apache.hadoop.mapreduce.InputSplit): HPath =
    split match {
      case file: org.apache.hadoop.mapreduce.lib.input.FileSplit => file.getPath
      case other =>
        try {
          val method = other.getClass.getDeclaredMethod("getInputSplit")
          method.setAccessible(true)
          method.invoke(other) match {
            case file: org.apache.hadoop.mapreduce.lib.input.FileSplit => file.getPath
            case _                                                     => null
          }
        } catch { case _: Exception => null }
    }
}

final class OpenAlexMapper
    extends SourceMapper(SourceType.OpenAlex, ConfKeys.SnapshotOpenAlex, "J02")
final class CrossrefMapper
    extends SourceMapper(SourceType.Crossref, ConfKeys.SnapshotCrossref, "J02")
final class OrcidMapper extends SourceMapper(SourceType.Orcid, ConfKeys.SnapshotOrcid, "J02")

class SourceMapper(source: SourceType, snapshotKey: String, jobName: String)
    extends Mapper[LongWritable, Text, Text, Text] {
  private val retrievalKey = source match {
    case SourceType.OpenAlex => ConfKeys.RetrievalOpenAlex
    case SourceType.Crossref => ConfKeys.RetrievalCrossref
    case SourceType.Orcid    => ConfKeys.RetrievalOrcid
    case _                   => ConfKeys.RetrievalDblp
  }

  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, jobName)
    val line = value.toString
    if (line.trim.isEmpty) return
    val sink = TaskSink.from(context, TaskSink.runId(context))
    sink.count(PrepCounters.Input, 1)
    val snapshot = context.getConfiguration.get(snapshotKey)
    // Decimal file offset only. A shared `reject` key is reordered by the shuffle when the
    // split count changes, so the offset also sorts the part line.
    val locator = s"${source.wire}@${key.get}"
    if (line.startsWith("\u0000OVERSIZE")) {
      sink.reject(
        Some(source),
        locator,
        Some(snapshot),
        PreparationStage.Normalize,
        RejectReasonCode.OversizeRecord,
        line.drop(1).take(180),
        locator
      )
      return
    }
    if (key.get >= SplitCutoff(context)) {
      sink.reject(
        Some(source),
        locator,
        Some(snapshot),
        PreparationStage.Normalize,
        RejectReasonCode.OversizeRecord,
        "maxLocalSampleRecords",
        locator
      )
      return
    }
    val limits = TaskSink.limits(context)
    JsonSources
      .parseLine(
        source,
        line,
        sink.runId,
        snapshot,
        locator,
        limits.maxRecordBytes,
        Option(context.getConfiguration.get(retrievalKey)).filter(_.nonEmpty)
      )
      .foreach(record => sink.emit(record, s"${source.wire}:${key.get}"))
  }
}

final class IndexMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J03")
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.emit(context, line, PreparationStage.IdentifierIndex, key.toString)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    Lines.tag(line).foreach { case (kind, instance, json) =>
      decodePrimary(kind, json).foreach { record =>
        sink.count(PrepCounters.Input, 1)
        val payload = Digests.sha256Text(json)
        val rows = DerivedRecords.indexRows(record, payload)
        if (
          record.isInstanceOf[EmittedRecord.Work] && rows.forall(row =>
            DerivedRecords.exactKey(row.entry.namespace, row.entry.normalizedValue).isEmpty
          )
        )
          sink.count(PrepCounters.MissingKey, 1)
        rows.foreach { row =>
          DomainValidation.check(row.entry) match {
            case Right(_) =>
              sink.emit(EmittedRecord.Indexed(row), instance)
            case Left(errors) =>
              sink.reject(
                Some(row.entry.source),
                row.entry.sourceRecordId,
                Some(row.entry.datasetSnapshot),
                PreparationStage.IdentifierIndex,
                RejectReasonCode.InvalidIdentifier,
                errors.map(_.message).mkString("; ")
              )
          }
        }
      }
    }
  }

  private def decodePrimary(kind: String, json: String): Option[EmittedRecord] =
    kind match {
      case Kinds.Work => CoreJson.parse[WorkRecord](json).toOption.map(EmittedRecord.Work.apply)
      case Kinds.Profile =>
        CoreJson.parse[OrcidProfileRecord](json).toOption.map(EmittedRecord.Profile.apply)
      case Kinds.Activity =>
        CoreJson.parse[OrcidActivityRecord](json).toOption.map(EmittedRecord.Activity.apply)
      case Kinds.Institution =>
        CoreJson.parse[Institution](json).toOption.map(EmittedRecord.InstitutionRec.apply)
      case _ => None
    }
}

final class JoinMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.defer(context, line, PreparationStage.IdentifierIndex, key.toString)
      return
    }
    Lines.tag(line).foreach { case (kind, instance, json) =>
      if (kind == Kinds.Bibliography) ()
      else if (kind == Kinds.Index) {
        val parsed = CoreJson.parse[IndexRow](json)
        parsed.foreach { row =>
          val group =
            s"${row.entry.source.wire}\u0001${row.entry.sourceRecordId}\u0001${row.entry.datasetSnapshot}"
          context.write(keyFrom(group), new Text(s"idx\t$instance\t$json"))
        }
        if (parsed.isLeft)
          context.getCounter(PrepCounters.Group, PrepCounters.MissingKey).increment(1)
      } else {
        val group =
          observationGroup(json).getOrElse("line\u0001" + Digests.sha256Text(kind + "\n" + json))
        context.write(keyFrom(group), new Text(s"rec\t$instance\t$kind\t$json"))
      }
    }
  }

  private def observationGroup(json: String): Option[String] =
    try {
      val obj = ujson.read(json).objOpt.map(_.value)
      val prov = obj.flatMap(_.get("provenance")).flatMap(_.objOpt).map(_.value)
      val source = prov.flatMap(_.get("source")).collect { case ujson.Str(text) => text }
      val recordId = prov.flatMap(_.get("sourceRecordId")).collect { case ujson.Str(text) => text }
      val snapshot = prov
        .flatMap(_.get("datasetSnapshot"))
        .collect { case ujson.Str(text) => text }
        .orElse(obj.flatMap(_.get("datasetSnapshot")).collect { case ujson.Str(text) => text })
      source.zip(recordId).zip(snapshot).map { case ((src, id), snap) =>
        s"$src\u0001$id\u0001$snap"
      }
    } catch { case _: Throwable => None }

  private def keyFrom(group: String): Text = new Text(group)
}

final class JoinReducer extends Reducer[Text, Text, Text, Text] {
  override def reduce(
      key: Text,
      values: java.lang.Iterable[Text],
      context: Reducer[Text, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J04")
    if (key.toString == OverflowLines.PassKey) {
      OverflowLines.release(context, values)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    val limit = math.max(256, context.getConfiguration.getInt(ConfKeys.MaxTeam, 1) * 16)
    val stored = ArrayBuffer.empty[String]
    val iter = values.iterator
    var extra = 0
    while (iter.hasNext) {
      val text = iter.next().toString
      if (stored.size < limit) stored += text else extra += 1
    }
    sink.count(PrepCounters.Input, (stored.size + extra).toLong)
    if (extra > 0)
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.IdentifierIndex,
        RejectReasonCode.OversizeRecord,
        "observation group"
      )
    else JoinReducer.decide(stored.toVector, sink, context)
  }
}

object JoinReducer {
  private val Primary = Set(Kinds.Work, Kinds.Profile, Kinds.Activity)

  /** Compare complete input observations. One observation that repeats an institution is not a
    * duplicate. Two copies of one side and none of the other do not count as agreement.
    */
  def decide(
      lines: Vector[String],
      sink: TaskSink,
      context: Reducer[Text, Text, Text, Text]#Context
  ): Unit = {
    val records = mutable.LinkedHashMap.empty[String, ArrayBuffer[(String, String)]]
    val indexes = mutable.LinkedHashMap.empty[String, ArrayBuffer[IndexRow]]
    lines.foreach { line =>
      if (line.startsWith("idx\t")) {
        val parts = line.split("\t", 3)
        if (parts.length == 3)
          CoreJson.parse[IndexRow](parts(2)).foreach { row =>
            indexes.getOrElseUpdate(parts(1), ArrayBuffer.empty) += row
          }
      } else if (line.startsWith("rec\t")) {
        val parts = line.split("\t", 4)
        if (parts.length == 4)
          records.getOrElseUpdate(parts(1), ArrayBuffer.empty) += (parts(2) -> parts(3))
      }
    }
    val instances = (records.keys ++ indexes.keys).toVector.distinct.sorted
    val hashes = instances.map { instance =>
      val body = records
        .getOrElse(instance, ArrayBuffer.empty)
        .map { case (kind, json) =>
          kind + "\n" + json
        }
        .sorted
      Digests.sha256Text(body.mkString("\n"))
    }
    val selfConflict = instances.exists { instance =>
      val primary = records.getOrElse(instance, ArrayBuffer.empty).filter { case (kind, _) =>
        Primary.contains(kind)
      }
      primary.map(_._2).distinct.size > 1
    }
    val conflict = selfConflict || hashes.distinct.size > 1
    if (instances.isEmpty) ()
    else if (conflict)
      instances.foreach { instance =>
        val located = conflictReject(records.getOrElse(instance, ArrayBuffer.empty).toSeq)
        sink.reject(
          located.map(_._1).getOrElse(None),
          located.map(_._2).getOrElse(instance),
          located.flatMap(_._3),
          PreparationStage.IdentifierIndex,
          RejectReasonCode.ConflictingObservation,
          "conflicting payload"
        )
      }
    else {
      val kept = instances.head
      val keptRecords = records.getOrElse(kept, ArrayBuffer.empty)
      keptRecords.foreach { case (kind, json) =>
        context.write(new Text(Lineage.key(kind, Lineage.fromJson(json))), new Text(json))
      }
      indexes
        .getOrElse(kept, ArrayBuffer.empty)
        .distinctBy(row => (row.entry.namespace, row.entry.normalizedValue))
        .foreach(row => sink.emit(EmittedRecord.Indexed(row)))
      DerivedRecords
        .bibliography(keptRecords.toSeq, indexes.getOrElse(kept, ArrayBuffer.empty).toSeq)
        .foreach { profile =>
          val json = CoreJson.compact(profile)
          context.write(
            new Text(Lineage.key(Kinds.Bibliography, Lineage.fromJson(json))),
            new Text(json)
          )
        }
      instances.tail.foreach { instance =>
        val located = conflictReject(records.getOrElse(instance, ArrayBuffer.empty).toSeq)
        sink.reject(
          located.map(_._1).getOrElse(None),
          located.map(_._2).getOrElse(instance),
          located.flatMap(_._3),
          PreparationStage.IdentifierIndex,
          RejectReasonCode.DuplicateIdenticalObservation,
          "identical observation"
        )
      }
    }
  }

  def conflictReject(
      records: Seq[(String, String)]
  ): Option[(Option[SourceType], String, Option[String])] =
    records.headOption.flatMap { case (_, json) =>
      try {
        val prov =
          ujson.read(json).objOpt.flatMap(_.value.get("provenance")).flatMap(_.objOpt).map(_.value)
        val source = prov.flatMap(_.get("source")).collect { case ujson.Str(text) => text }
        val locator = prov.flatMap(_.get("sourceRecordId")).collect { case ujson.Str(text) => text }
        val snapshot =
          prov.flatMap(_.get("datasetSnapshot")).collect { case ujson.Str(text) => text }
        locator.map { id =>
          val parsed = source.flatMap(wire => SourceType.values.find(_.wire == wire))
          (parsed, id, snapshot)
        }
      } catch { case _: Throwable => None }
    }
}

final class BlockMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.defer(context, line, PreparationStage.Block, key.toString)
      return
    }
    Lines.unpack(line).foreach { case (kind, json) =>
      if (kind == Kinds.Bibliography)
        CoreJson.parse[Bibliography](json).foreach { profile =>
          val keys = DerivedRecords.blockKeys(profile)
          if (keys.forall(_.startsWith("fallback:")))
            context.getCounter(PrepCounters.Group, PrepCounters.MissingKey).increment(1)
          keys.foreach { blockKey =>
            val member = DerivedRecords.member(profile, blockKey)
            context.write(new Text(blockKey), new Text(CoreJson.compact(member)))
          }
        }
    }
  }
}

final class BlockReducer extends Reducer[Text, Text, Text, Text] {
  private val considered = mutable.Map.empty[String, Long]

  override def reduce(
      key: Text,
      values: java.lang.Iterable[Text],
      context: Reducer[Text, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J05")
    if (key.toString == OverflowLines.PassKey) {
      OverflowLines.release(context, values)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    val maxBlock = context.getConfiguration.getInt(ConfKeys.MaxBlock, 1)
    val maxPairs = context.getConfiguration.getInt(ConfKeys.MaxPairs, 1)
    val kept = mutable.LinkedHashMap.empty[(SourceType, String, String), BlockMember]
    val iter = values.iterator
    var overflow = false
    var seen = 0
    while (iter.hasNext) {
      seen += 1
      CoreJson.parse[BlockMember](iter.next().toString).foreach { member =>
        val identity = (member.source, member.sourceRecordId, member.datasetSnapshot)
        if (!kept.contains(identity)) {
          if (kept.size >= maxBlock) overflow = true
          else kept.update(identity, member)
        }
      }
    }
    sink.count(PrepCounters.Input, seen.toLong)
    val size = if (overflow) maxBlock.toLong + 1 else kept.size.toLong
    val pairs =
      try if (overflow) Long.MaxValue else PrepLimits.pairCount(kept.size)
      catch { case _: ArithmeticException => Long.MaxValue }
    considered.update("largestBlock", math.max(considered.getOrElse("largestBlock", 0L), size))
    considered.update(
      "largestBlockPairs",
      math.max(
        considered.getOrElse("largestBlockPairs", 0L),
        if (pairs == Long.MaxValue) 0L else pairs
      )
    )
    if (overflow)
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.Block,
        RejectReasonCode.OversizeBlock,
        s"block exceeds $maxBlock"
      )
    else if (pairs > maxPairs.toLong)
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.Block,
        RejectReasonCode.OversizeCandidatePairs,
        s"block pairs $pairs exceed $maxPairs"
      )
    else
      kept.values.toVector
        .sortBy(member => (member.source.wire, member.sourceRecordId, member.datasetSnapshot))
        .foreach(member => sink.emit(EmittedRecord.Member(member)))
  }

  override def cleanup(context: Reducer[Text, Text, Text, Text]#Context): Unit = {
    val dir = context.getConfiguration.get(ConfKeys.StatsDir)
    if (dir != null)
      StatsFiles.write(
        dir,
        "j05-" + context.getTaskAttemptID.toString,
        considered.toMap,
        context.getConfiguration
      )
  }
}

final class CandidateMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.defer(context, line, PreparationStage.MatchCandidate, key.toString)
      return
    }
    Lines.unpack(line).foreach { case (kind, json) =>
      if (kind == Kinds.BlockMember)
        CoreJson.parse[BlockMember](json).foreach { member =>
          context.write(new Text(member.blockKey), new Text(json))
        }
    }
  }
}

final class CandidateReducer extends Reducer[Text, Text, Text, Text] {
  override def reduce(
      key: Text,
      values: java.lang.Iterable[Text],
      context: Reducer[Text, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J06")
    if (key.toString == OverflowLines.PassKey) {
      OverflowLines.release(context, values)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    if (key.toString.startsWith("fallback:")) {
      val iter = values.iterator
      while (iter.hasNext) iter.next()
      return
    }
    val maxBlock = context.getConfiguration.getInt(ConfKeys.MaxBlock, 1)
    val maxPairs = context.getConfiguration.getInt(ConfKeys.MaxPairs, 1)
    val kept = mutable.LinkedHashMap.empty[(SourceType, String, String), BlockMember]
    val iter = values.iterator
    var overflow = false
    while (iter.hasNext) {
      CoreJson.parse[BlockMember](iter.next().toString).foreach { member =>
        val identity = (member.source, member.sourceRecordId, member.datasetSnapshot)
        if (!kept.contains(identity)) {
          if (kept.size >= maxBlock) overflow = true
          else kept.update(identity, member)
        }
      }
    }
    val pairs =
      try if (overflow) Long.MaxValue else PrepLimits.pairCount(kept.size)
      catch { case _: ArithmeticException => Long.MaxValue }
    if (overflow)
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.MatchCandidate,
        RejectReasonCode.OversizeBlock,
        s"block exceeds $maxBlock"
      )
    else if (pairs > maxPairs.toLong)
      sink.reject(
        None,
        key.toString,
        None,
        PreparationStage.MatchCandidate,
        RejectReasonCode.OversizeCandidatePairs,
        s"block pairs $pairs exceed $maxPairs"
      )
    else {
      val members = kept.values.toVector.sortBy(member =>
        StableIds.candidateObservationOrderKey(
          CandidateObservation(
            member.source,
            member.sourceRecordId,
            member.datasetSnapshot,
            member.workId
          )
        )
      )
      var i = 0
      while (i < members.size) {
        var j = i + 1
        while (j < members.size) {
          DerivedRecords.candidate(members(i), members(j), members.size, sink.runId) match {
            case Right(value) =>
              DomainValidation.check(value) match {
                case Right(valid) => sink.emit(EmittedRecord.Candidate(valid))
                case Left(errors) =>
                  sink.reject(
                    Some(SourceType.ScholarChain),
                    key.toString,
                    Some(PrepLimits.DerivedSnapshot),
                    PreparationStage.MatchCandidate,
                    RejectReasonCode.SchemaFailure,
                    errors.map(_.message).mkString("; ")
                  )
              }
            case Left(_) =>
              sink.count(PrepCounters.MissingKey, 1)
          }
          j += 1
        }
        i += 1
      }
    }
  }
}

final class TeamMapper extends Mapper[LongWritable, Text, Text, Text] {
  private val largest = mutable.Map.empty[String, Long]

  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J07")
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.emit(context, line, PreparationStage.PublicationTeam, key.toString)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    Lines.unpack(line).foreach { case (kind, json) =>
      if (kind == Kinds.Work)
        CoreJson.parse[WorkRecord](json).foreach { work =>
          sink.count(PrepCounters.Input, 1)
          val size = work.authors.size
          largest.update("largestTeam", math.max(largest.getOrElse("largestTeam", 0L), size.toLong))
          val maxTeam = context.getConfiguration.getInt(ConfKeys.MaxTeam, 1)
          DerivedRecords.teams(work, maxTeam, work.sourceRecordId).foreach(sink.emit)
        }
    }
  }

  override def cleanup(context: Mapper[LongWritable, Text, Text, Text]#Context): Unit = {
    val dir = context.getConfiguration.get(ConfKeys.StatsDir)
    if (dir != null)
      StatsFiles.write(
        dir,
        "j07-" + context.getTaskAttemptID.toString,
        largest.toMap,
        context.getConfiguration
      )
  }
}

final class PairMapper extends Mapper[LongWritable, Text, Text, Text] {
  private val largest = mutable.Map.empty[String, Long]

  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J08")
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      OverflowLines.emit(context, line, PreparationStage.CoauthorPair, key.toString)
      return
    }
    val sink = TaskSink.from(context, TaskSink.runId(context))
    Lines.unpack(line).foreach { case (kind, json) =>
      if (kind == Kinds.Work)
        CoreJson.parse[WorkRecord](json).foreach { work =>
          sink.count(PrepCounters.Input, 1)
          val count =
            try PrepLimits.pairCount(work.authors.size)
            catch { case _: ArithmeticException => Long.MaxValue }
          largest.update(
            "largestPairExpansion",
            math.max(largest.getOrElse("largestPairExpansion", 0L), count)
          )
          val maxPairs = context.getConfiguration.getInt(ConfKeys.MaxPairs, 1)
          val maxTeam = context.getConfiguration.getInt(ConfKeys.MaxTeam, 1)
          DerivedRecords.pairs(work, maxPairs, maxTeam, work.sourceRecordId).foreach(sink.emit)
        }
    }
  }

  override def cleanup(context: Mapper[LongWritable, Text, Text, Text]#Context): Unit = {
    val dir = context.getConfiguration.get(ConfKeys.StatsDir)
    if (dir != null)
      StatsFiles.write(
        dir,
        "j08-" + context.getTaskAttemptID.toString,
        largest.toMap,
        context.getConfiguration
      )
  }
}

final class ExportMapper extends Mapper[LongWritable, Text, Text, Text] {
  override def map(
      key: LongWritable,
      value: Text,
      context: Mapper[LongWritable, Text, Text, Text]#Context
  ): Unit = {
    TaskSink.guard(context, "J09")
    val line = value.toString
    if (OverflowLines.isMarker(line)) {
      val reject = OverflowLines.record(
        line,
        TaskSink.runId(context),
        PreparationStage.Export,
        key.toString
      )
      val packed = Lines.pack(Kinds.Reject, CoreJson.compact(reject))
      context.write(
        new Text("out\t" + reject.datasetSnapshot.getOrElse(PrepLimits.DerivedSnapshot)),
        new Text(packed)
      )
      return
    }
    Lines.unpack(line).foreach { case (kind, json) =>
      if (kind != Kinds.BlockMember && kind != Kinds.Bibliography) {
        val path = context.getInputSplit match {
          case split: org.apache.hadoop.mapreduce.lib.input.FileSplit => split.getPath.toString
          case _                                                      => ""
        }
        val exportIndex = kind == Kinds.Index && path.contains("/j04/")
        if (kind != Kinds.Index || exportIndex)
          context.write(new Text("out\t" + snapshotOf(kind, json)), new Text(line))
        textRef(kind, json).foreach { ref =>
          context.write(new Text("ref\t" + ref), new Text("need"))
        }
        if (kind == Kinds.Text)
          CoreJson.parse[EmittedTextDocument](json).foreach { doc =>
            context.write(new Text("ref\t" + doc.textId), new Text("have"))
          }
      }
    }
  }

  private def snapshotOf(kind: String, json: String): String =
    kind match {
      case Kinds.Work =>
        CoreJson
          .parse[WorkRecord](json)
          .map(_.provenance.datasetSnapshot)
          .getOrElse(PrepLimits.DerivedSnapshot)
      case Kinds.Reject =>
        CoreJson
          .parse[RejectRecord](json)
          .map(_.datasetSnapshot.getOrElse(PrepLimits.DerivedSnapshot))
          .getOrElse(PrepLimits.DerivedSnapshot)
      case Kinds.MatchCandidate => PrepLimits.DerivedSnapshot
      case Kinds.Index =>
        CoreJson
          .parse[IndexRow](json)
          .map(_.entry.datasetSnapshot)
          .getOrElse(PrepLimits.DerivedSnapshot)
      case _ =>
        try {
          val parsed = ujson.read(json)
          parsed.objOpt
            .flatMap(_.value.get("datasetSnapshot"))
            .flatMap {
              case ujson.Str(text) => Some(text)
              case _               => None
            }
            .orElse(parsed.objOpt.flatMap(_.value.get("provenance")).flatMap(_.objOpt).flatMap {
              prov =>
                prov.value.get("datasetSnapshot").collect { case ujson.Str(text) => text }
            })
            .getOrElse(PrepLimits.DerivedSnapshot)
        } catch {
          case _: ujson.ParseException => PrepLimits.DerivedSnapshot
        }
    }

  private def textRef(kind: String, json: String): Option[String] =
    if (kind != Kinds.Work) None
    else CoreJson.parse[WorkRecord](json).toOption.flatMap(_.abstractTextRef)
}

object ExportReducer {

  /** A failed graph check is a schema reject. A successful edge is the only graph line. */
  def writeCheckedGraph(
      graph: GraphEdge,
      snapshot: String,
      runId: String,
      writeJson: (String, String, String, String) => Unit
  ): Unit =
    DomainValidation.check(graph) match {
      case Right(valid) =>
        writeJson(Kinds.GraphEdge, CoreJson.compact(valid), snapshot, runId)
      case Left(errors) =>
        val reject = Rejects.record(
          Some(graph.provenance.source),
          graph.provenance.sourceRecordId,
          Some(snapshot),
          runId,
          PreparationStage.Export,
          RejectReasonCode.SchemaFailure,
          errors.map(_.message).mkString("; ")
        )
        writeJson(Kinds.Reject, CoreJson.compact(reject), snapshot, runId)
    }
}

final class ExportReducer extends Reducer[Text, Text, Text, NullWritable] {
  private var outputs: MultipleOutputs[Text, NullWritable] = _

  override def setup(context: Reducer[Text, Text, Text, NullWritable]#Context): Unit =
    outputs = new MultipleOutputs(context)

  override def reduce(
      key: Text,
      values: java.lang.Iterable[Text],
      context: Reducer[Text, Text, Text, NullWritable]#Context
  ): Unit = {
    val text = key.toString
    if (text.startsWith("ref\t")) {
      val flags = values.asScala.map(_.toString).toSet
      if (flags.contains("need") && !flags.contains("have")) {
        val sinkRun = TaskSink.runId(context)
        val sink = new TaskSink(
          (kind, json) =>
            writeJson(
              kind.takeWhile(_ != Lineage.Separator),
              json,
              PrepLimits.DerivedSnapshot,
              sinkRun
            ),
          (name, n) => context.getCounter(PrepCounters.Group, name).increment(n),
          sinkRun
        )
        sink.reject(
          None,
          text.drop(4),
          Some(PrepLimits.DerivedSnapshot),
          PreparationStage.Export,
          RejectReasonCode.SchemaFailure,
          "abstractTextRef does not resolve to an emitted text document"
        )
      }
    } else if (text.startsWith("out\t")) {
      val snapshot = text.drop(4)
      val runId = TaskSink.runId(context)
      values.forEach { value =>
        Lines.unpack(value.toString).foreach { case (kind, json) =>
          if (kind == Kinds.Index)
            CoreJson.parse[IndexRow](json).foreach { row =>
              writeJson(kind, CoreJson.compact(row.entry), row.entry.datasetSnapshot, runId)
            }
          else writeJson(kind, json, snapshot, runId)
          if (kind == Kinds.Work)
            CoreJson.parse[WorkRecord](json).foreach { work =>
              work.authors.foreach { mention =>
                writeJson(Kinds.AuthorMention, CoreJson.compact(mention), snapshot, runId)
              }
              DerivedRecords.edges(work).foreach { graph =>
                ExportReducer.writeCheckedGraph(graph, snapshot, runId, writeJson)
              }
            }
          if (kind == Kinds.Enrichment)
            CoreJson.parse[EnrichmentLink](json).foreach { link =>
              DerivedRecords.topicEdge(link).foreach { graph =>
                ExportReducer.writeCheckedGraph(graph, snapshot, runId, writeJson)
              }
            }
          if (kind == Kinds.GraphEdge)
            context.getCounter(PrepCounters.Group, PrepCounters.Accepted).increment(1)
        }
      }
    }
  }

  private def writeJson(kind: String, json: String, snapshot: String, runId: String): Unit = {
    val uuid = runId.stripPrefix("run:")
    outputs.write(
      "json",
      new Text(json),
      NullWritable.get(),
      s"snapshot=$snapshot/run=$uuid/$kind/part"
    )
  }

  override def cleanup(context: Reducer[Text, Text, Text, NullWritable]#Context): Unit =
    if (outputs != null) outputs.close()
}

object ExportCheck {
  def unresolved(dir: Path): Vector[String] = {
    val works = ArrayBuffer.empty[WorkRecord]
    val docs = ArrayBuffer.empty[EmittedTextDocument]
    if (Files.exists(dir)) {
      val walk = Files.walk(dir)
      try {
        walk.forEach { path =>
          val name = path.getFileName.toString
          if (
            Files.isRegularFile(path) && !name.startsWith("_") && !name.startsWith(".") &&
            !name.endsWith(".crc")
          ) {
            Files.readAllLines(path).forEach { line =>
              if (line.startsWith("{")) {
                if (path.toString.contains("/work/") || path.toString.contains("/works/"))
                  CoreJson.parse[WorkRecord](line).foreach(works += _)
                if (path.toString.contains("/text/"))
                  CoreJson.parse[EmittedTextDocument](line).foreach(docs += _)
              }
            }
          }
        }
      } finally walk.close()
    }
    TextRefs.unresolved(works.toVector, docs.toVector)
  }
}
