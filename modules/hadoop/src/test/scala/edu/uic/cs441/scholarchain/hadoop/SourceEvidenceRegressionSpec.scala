package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{Path => HPath}
import org.apache.hadoop.mapreduce.TaskAttemptID
import org.apache.hadoop.mapreduce.lib.input.FileSplit
import org.apache.hadoop.mapreduce.task.TaskAttemptContextImpl
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import java.util.zip.GZIPOutputStream
import scala.jdk.CollectionConverters.*

class SourceEvidenceRegressionSpec extends AnyFunSuite {
  private val runId = "run:71717171-7171-4171-8171-717171717171"

  test("OpenAlex retains both DOI field roles and validates the secondary value") {
    def records(secondary: String) = JsonSources.parseLine(
      SourceType.OpenAlex,
      s"""{"id":"W2741800001","title":"T","doi":"https://doi.org/10.1000/a","ids":{"doi":"$secondary"}}""",
      runId,
      "openalex-test",
      "json@0",
      1048576
    )
    val a = records("10.1000/b").collect { case EmittedRecord.Work(value) => value }.head
    val b = records("10.1000/c").collect { case EmittedRecord.Work(value) => value }.head
    assert(a.doi.contains("10.1000/a") && a.workId == b.workId)
    assert(
      a.observedIdentifiers.map(id => id.namespace -> id.value) == Vector(
        "openalex.doi" -> "https://doi.org/10.1000/a",
        "openalex.ids.doi" -> "10.1000/b"
      )
    )
    assert(
      a.observedIdentifiers.forall(_.interpretation == IdentifierInterpretation.SourceObservation)
    )
    assert(CoreJson.compact(a) != CoreJson.compact(b))
    assert(
      records("malformed-secondary")
        .collect { case EmittedRecord.Rejected(value) =>
          value.reasonCode
        }
        .contains(RejectReasonCode.InvalidIdentifier)
    )
    assert(!records("malformed-secondary").exists(_.isInstanceOf[EmittedRecord.Work]))
  }

  test("DBLP preserves repeated electronic editions and URLs by their declared field") {
    val xml =
      """<article key='conf/review/Links'><title>T</title><author>Ada</author><ee>https://publisher.test/paper?a=1&amp;b=2</ee><url>db/first</url><ee>https://repository.test/paper</ee><ee>https://publisher.test/paper?a=1&amp;b=2</ee><url>https://archive.test/paper</url></article>"""
    val work = DblpRecords
      .parse(xml, DblpXml.Header(Map.empty, None), runId, "dblp-test", "xml@0", 1048576, 1048576)
      .collect { case EmittedRecord.Work(value) => value }
      .head
    assert(work.doi.isEmpty)
    assert(
      work.sourceLinks == Vector(
        NamedText("ee", "https://publisher.test/paper?a=1&b=2"),
        NamedText("ee", "https://repository.test/paper"),
        NamedText("ee", "https://publisher.test/paper?a=1&b=2"),
        NamedText("url", "db/first"),
        NamedText("url", "https://archive.test/paper")
      )
    )
    assert(work.externalUrl.contains("https://dblp.org/db/first"))
  }

  test("overflow lineage survives compressed input and distinct part-file offsets") {
    val directory = Files.createTempDirectory("lineage-envelope")
    val lineage = Lineage(Some(SourceType.Dblp), Some("dblp-ü-test"), "conf/test/Quoted\t\"Ü")
    val raw = Lineage.key("work\u0001dblp:0", Some(lineage)) + "\t" + ("x" * 10000) + "\n"
    assert(Lines.tag(raw.trim).exists { case (kind, instance, _) =>
      kind == Kinds.Work && instance == "dblp:0"
    })
    val first = directory.resolve("part-00000")
    val second = directory.resolve("part-00001.gz")
    Files.writeString(first, raw)
    val zipped = new GZIPOutputStream(Files.newOutputStream(second))
    try zipped.write(raw.getBytes(StandardCharsets.UTF_8))
    finally zipped.close()
    val rejects = Vector(first, second).map { path =>
      val encoded = read(path, 0L, Files.size(path), 256L).head
      OverflowLines.record(encoded, runId, PreparationStage.Export, "fallback")
    }
    assert(rejects.forall(_.source.contains(SourceType.Dblp)))
    assert(rejects.forall(_.datasetSnapshot.contains("dblp-ü-test")))
    assert(rejects.forall(_.sourceLocator.contains("@0#record=")))
    assert(rejects.map(_.sourceLocator).distinct.size == 2)
    assert(
      rejects.forall(
        _.diagnosticExcerpt.exists(_.length <= RejectRecord.maxDiagnosticExcerptLength)
      )
    )
    val bodyOffset = raw.indexOf('\t') + 101
    assert(read(first, bodyOffset.toLong, Files.size(first) - bodyOffset, 256).isEmpty)
  }

  test("valid 600k DBLP title expansion exports rejects with original source lineage") {
    val directory = Files.createTempDirectory("valid-source-expansion")
    val xml = directory.resolve("source.xml")
    val key = "conf/review/Large"
    val title = "x" * 600000
    Files.writeString(xml, s"<dblp><article key='$key'><title>$title</title></article></dblp>")
    assert(Files.size(xml) < 1048576)
    val config = HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      32,
      128,
      16,
      100,
      directory.resolve("root").toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )
    val conf = PrepJobs.configuration(config, runId, HadoopPrepPipeline.DefaultSnapshots)
    val extracted = directory.resolve("j01")
    PrepJobs.run("J01", PrepJobs.dblp(conf, xml.toString, extracted, None))
    val indexed = directory.resolve("j03")
    PrepJobs.run("J03", PrepJobs.index(conf, Seq(extracted), indexed))
    val joined = directory.resolve("j04")
    PrepJobs.run("J04", PrepJobs.join(conf, Seq(extracted, indexed), joined))
    val exported = directory.resolve("export")
    PrepJobs.run("J09", PrepJobs.exportJob(conf, Seq(joined), exported))
    val rejects =
      LogicalRecords.lines(exported).flatMap(line => CoreJson.parse[RejectRecord](line).toOption)
    assert(rejects.nonEmpty)
    assert(rejects.forall(_.reasonCode == RejectReasonCode.OversizeRecord))
    assert(rejects.forall(_.source.contains(SourceType.Dblp)))
    assert(
      rejects.forall(
        _.datasetSnapshot.contains(HadoopPrepPipeline.DefaultSnapshots(SourceType.Dblp))
      )
    )
    assert(rejects.forall(_.sourceLocator.contains(key)))
    assert(rejects.exists(_.sourceLocator.contains("/j01/part")))
    assert(rejects.forall(_.sourceLocator.contains("@")))
  }

  test("snapshot metadata beyond its fixed budget fails before filesystem or job work") {
    assert(Lineage.snapshotFits("ü" * 512))
    assert(!Lineage.snapshotFits("ü" * 513))
    val directory = Files.createTempDirectory("lineage-metadata-limit")
    val config = HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      32,
      128,
      16,
      100,
      directory.resolve("out").toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )
    val snapshots = HadoopPrepPipeline.DefaultSnapshots.updated(SourceType.Dblp, "ü" * 513)
    val result = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config,
        "missing.xml",
        "missing-oa",
        "missing-cr",
        "missing-orcid",
        snapshots,
        runId
      )
    )
    assert(
      result.left.exists(_.contains("dataset snapshot exceeds bounded lineage metadata limit 1024"))
    )
    assert(!Files.exists(directory.resolve("out")))
    intercept[IllegalArgumentException](PrepJobs.configuration(config, runId, snapshots))
  }

  test("missing abstract document exports its reject in the public reject partition") {
    val directory = Files.createTempDirectory("final-export-lineage")
    val records = JsonSources.parseLine(
      SourceType.OpenAlex,
      """{"id":"W2741800001","title":"Missing abstract"}""",
      runId,
      "openalex-test",
      "json@0",
      1048576
    )
    val parsed = records.collect { case EmittedRecord.Work(value) => value }.head
    val ref = StableIds
      .chunkOrProfileId(parsed.workId, "openalex-test", "abstract", Some(0), "unavailable document")
      .toOption
      .get
    val work = parsed.copy(abstractTextRef = Some(ref))
    assert(DomainValidation.check(work).isRight)
    val input = directory.resolve("j04")
    Files.createDirectories(input)
    val lines = Vector.newBuilder[String]
    val sink = new TaskSink((kind, json) => lines += Lines.pack(kind, json), (_, _) => (), runId)
    sink.emit(EmittedRecord.Work(work))
    Files.writeString(input.resolve("part-r-00000"), lines.result().mkString("\n") + "\n")
    val config = HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      32,
      128,
      16,
      100,
      directory.resolve("root").toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )
    val conf = PrepJobs.configuration(config, runId, HadoopPrepPipeline.DefaultSnapshots)
    val exported = directory.resolve("export")
    PrepJobs.run("J09", PrepJobs.exportJob(conf, Seq(input), exported))
    val walked = Files.walk(exported)
    val paths =
      try walked.iterator().asScala.toVector
      finally walked.close()
    assert(paths.forall(path => !path.toString.exists(_.isControl)))
    val rejectFiles = paths.filter(path =>
      Files.isRegularFile(path) && path.toString.contains("/reject/") && !path.getFileName.toString
        .startsWith(".")
    )
    assert(rejectFiles.nonEmpty, paths.mkString("\n"))
    val rejects = rejectFiles
      .flatMap(path => Files.readAllLines(path).asScala)
      .flatMap(line => CoreJson.parse[RejectRecord](line).toOption)
    assert(
      rejects.exists(value =>
        value.reasonCode == RejectReasonCode.SchemaFailure && value.sourceLocator == ref
      )
    )
  }

  test(
    "processing location normalization preserves long roots native identities and unknown lineage"
  ) {
    val otherRun = "run:72727272-7272-4272-8272-727272727272"
    val lineage =
      Some(Lineage(Some(SourceType.Dblp), Some("dblp-test"), "conf/test/" + ("n" * 500)))
    val root = "file:/source/" + runId.stripPrefix("run:") + "/" + ("long-root/" * 100)
    def locate(run: String, part: String = "part-r-00000.gz", fileRoot: String = root) =
      Lineage.overflowLocator(
        fileRoot + "/" + run.stripPrefix("run:") + "/intermediate/j01/" + part,
        42L,
        lineage,
        run
      )
    def reject(
        locator: String,
        run: String,
        source: Option[SourceType] = Some(SourceType.Dblp),
        snapshot: String = "dblp-test"
    ) =
      CoreJson.compact(
        Rejects.record(
          source,
          locator,
          Some(snapshot),
          run,
          PreparationStage.IdentifierIndex,
          RejectReasonCode.OversizeRecord,
          "stable diagnostic"
        )
      )
    val left = locate(runId)
    val right = locate(otherRun)
    assert(left != right && left.length <= RejectRecord.maxSourceLocatorLength)
    assert(left.endsWith("#record=" + Lineage.boundedIdentity(lineage.get.record)))
    assert(Lineage.boundedIdentity(lineage.get.record).contains("#sha256="))
    assert(
      LogicalRecords.normalize(reject(left, runId), runId) == LogicalRecords.normalize(
        reject(right, otherRun),
        otherRun
      )
    )
    assert(
      LogicalRecords.normalize(reject(left, runId), runId) != LogicalRecords.normalize(
        reject(locate(otherRun, "part-r-00001.gz"), otherRun),
        otherRun
      )
    )
    assert(
      LogicalRecords.normalize(reject(left, runId), runId) != LogicalRecords.normalize(
        reject(locate(otherRun, fileRoot = root + "changed"), otherRun),
        otherRun
      )
    )
    assert(
      LogicalRecords.normalize(reject(left, runId), runId) != LogicalRecords.normalize(
        reject(right, otherRun, snapshot = "dblp-other"),
        otherRun
      )
    )
    val unknown = ujson.read(LogicalRecords.normalize(reject(left, runId, None), runId))
    assert(unknown("sourceLocator").str == left)
    val rawSource =
      "file:/source/" + runId.stripPrefix("run:") + "/raw.xml@42#record=conf/test/Native"
    assert(
      ujson
        .read(LogicalRecords.normalize(reject(rawSource, runId), runId))("sourceLocator")
        .str == rawSource
    )
    assert(
      Lineage
        .canonicalProcessingFile(
          root + "/" + runId.stripPrefix("run:") + "/intermediate/j01/part-r-00000.gz",
          runId
        )
        .contains(root + "/RUN/intermediate/j01/part-r-00000.gz")
    )
  }

  test("two fresh valid 600k title overflow pipelines remain logically equivalent") {
    val directory = Files.createTempDirectory("fresh-overflow-equivalence")
    val xml = directory.resolve("source.xml")
    Files.writeString(
      xml,
      "<dblp><article key='conf/review/FreshLarge'><title>" + ("x" * 600000) + "</title></article></dblp>"
    )
    val json = directory.resolve("empty.jsonl")
    Files.writeString(json, "")
    val config = HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      32,
      128,
      16,
      100,
      directory.resolve("output").toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )
    val first = HadoopPrepPipeline.Request(
      config,
      xml.toString,
      json.toString,
      json.toString,
      json.toString,
      HadoopPrepPipeline.DefaultSnapshots,
      runId,
      retrievalDates = HadoopPrepPipeline.DefaultRetrievalDates
    )
    val second = first.copy(runId = "run:73737373-7373-4373-8373-737373737373")
    val a = HadoopPrepPipeline.execute(first)
    val b = HadoopPrepPipeline.execute(second)
    assert(a.isRight, a.left.toOption.getOrElse(""))
    assert(b.isRight, b.left.toOption.getOrElse(""))
    assert(!a.toOption.get.reused && !b.toOption.get.reused)
    val aExport = a.toOption.get.directory.resolve("export")
    val bExport = b.toOption.get.directory.resolve("export")
    assert(LogicalRecords.lines(aExport).exists(_.contains("OVERSIZE_RECORD")))
    assert(LogicalRecords.equivalent(aExport, bExport, first.runId, second.runId))
  }

  test(
    "logical comparison only excludes processing runId fields and retains exact run-shaped source values"
  ) {
    val otherRun = "run:74747474-7474-4474-8474-747474747474"
    def fixture(processingRun: String) = ujson.Obj(
      "runId" -> processingRun,
      "title" -> runId,
      "sourceLocator" -> runId,
      "datasetSnapshot" -> runId,
      "sourceLinks" -> ujson.Arr(ujson.Obj("name" -> "ee", "value" -> runId)),
      "observedIdentifiers" -> ujson.Arr(ujson.Obj("namespace" -> "declared", "value" -> runId)),
      "sourceDetails" -> ujson.Obj("runId" -> runId),
      "provenance" -> ujson.Obj(
        "runId" -> processingRun,
        "sourceRecordId" -> runId,
        "datasetSnapshot" -> runId
      )
    )
    val first = fixture(runId)
    val second = fixture(otherRun)
    val normalized = LogicalRecords.normalize(ujson.write(first), runId)
    assert(normalized == LogicalRecords.normalize(ujson.write(second), otherRun))
    val readBack = ujson.read(normalized)
    assert(readBack("runId").str == "RUN")
    assert(readBack("provenance")("runId").str == "RUN")
    assert(readBack("title").str == runId)
    assert(readBack("sourceLocator").str == runId)
    assert(readBack("datasetSnapshot").str == runId)
    assert(readBack("sourceDetails")("runId").str == runId)
    assert(readBack("sourceLinks")(0)("value").str == runId)
    assert(readBack("observedIdentifiers")(0)("value").str == runId)
    assert(readBack("provenance")("sourceRecordId").str == runId)
    Vector("title", "datasetSnapshot", "sourceLocator").foreach { field =>
      val changed = fixture(otherRun)
      changed(field) = ujson.Str(otherRun)
      assert(normalized != LogicalRecords.normalize(ujson.write(changed), otherRun), field)
    }
    val changedLink = fixture(otherRun)
    changedLink("sourceLinks")(0)("value") = ujson.Str(otherRun)
    assert(normalized != LogicalRecords.normalize(ujson.write(changedLink), otherRun))
    val index = ujson.Obj(
      "payloadHash" -> "payload",
      "entry" -> ujson.Obj("runId" -> runId, "datasetSnapshot" -> runId)
    )
    val normalizedIndex = ujson.read(LogicalRecords.normalize(ujson.write(index), runId))
    assert(normalizedIndex("entry")("runId").str == "RUN")
    assert(normalizedIndex("entry")("datasetSnapshot").str == runId)
  }

  private def read(path: Path, start: Long, length: Long, cap: Long): Vector[String] = {
    val conf = new Configuration()
    conf.setLong(ConfKeys.BoundedLineBytes, cap)
    val reader = new BoundedLineRecordReader
    reader.initialize(
      new FileSplit(new HPath(path.toUri), start, length, Array.empty[String]),
      new TaskAttemptContextImpl(conf, new TaskAttemptID())
    )
    val found = Vector.newBuilder[String]
    try {
      while (reader.nextKeyValue()) found += reader.getCurrentValue.toString
      found.result()
    } finally reader.close()
  }
}
