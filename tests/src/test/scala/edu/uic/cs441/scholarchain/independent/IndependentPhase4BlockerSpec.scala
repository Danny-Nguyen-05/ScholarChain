package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.mapreduce.TaskAttemptID
import org.apache.hadoop.mapreduce.lib.input.FileSplit
import org.apache.hadoop.mapreduce.task.TaskAttemptContextImpl
import org.scalatest.funsuite.AnyFunSuite

import java.net.URLClassLoader
import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Independent coverage for the six Hadoop and domain blockers in phase-04/review.md. */
class IndependentPhase4BlockerSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  try org.apache.log4j.Logger.getRootLogger.setLevel(org.apache.log4j.Level.WARN)
  catch { case _: Throwable => () }

  private val sampleDblpKeys = Vector(
    "series/sapere/BerkeleyR13",
    "series/sapere/NasutoB13",
    "series/sapere/SchiaffonatiV13"
  )
  private val memoryS3Impl = "edu.uic.cs441.scholarchain.hadoop.MemoryS3FileSystem"
  private val filesystemGap = "requires a Hadoop FileSystem implementation"
  private val inproceedings = "(?s)<inproceedings\\b.*?</inproceedings>".r

  test(
    "DBLP works under a 1024-byte source cap stay in the export or are explicit OVERSIZE_RECORD rejects"
  ) {
    val dblp = sample("datasets/samples/dblp/linked-records.xml")
    assume(Files.isRegularFile(dblp), s"missing sample $dblp")
    val raw = inproceedings.findAllIn(Files.readString(dblp)).toVector
    assert(raw.size == sampleDblpKeys.size, s"expected ${sampleDblpKeys.size} articles")
    raw.foreach { article =>
      val bytes = article.getBytes(StandardCharsets.UTF_8).length
      assert(bytes < 1024, s"raw DBLP article is $bytes bytes")
    }
    val request = committedRequest("source-cap", maxRecordBytes = 1024L)
    val result = HadoopPrepPipeline.execute(request)
    assert(result.isRight, result.left.toOption.getOrElse(""))
    val value = result.toOption.get
    assert(!value.reused)
    val lines = exportLines(value.directory)
    val oversize = rejects(lines).count(_.reasonCode == RejectReasonCode.OversizeRecord)
    sampleDblpKeys.foreach { key =>
      val present = works(lines).exists { work =>
        work.source == SourceType.Dblp && work.sourceRecordId == key
      }
      assert(
        present || oversizeMentions(lines, key),
        s"$key absent from export with $oversize OVERSIZE_RECORD rejects"
      )
    }
  }

  test("FileSplit starting inside a comment does not emit the fake article") {
    val xml =
      """<dblp><!-- padding
        |<article key="conf/review/Fake"><title>Fake</title></article>
        |--><article key="conf/review/Real"><title>Real</title></article></dblp>""".stripMargin
    assertLexicalSplit("comment-split", xml, "<!--")
  }

  test("FileSplit starting inside CDATA does not emit the fake article") {
    val xml =
      """<dblp><![CDATA[ padding
        |<article key="conf/review/Fake"><title>Fake</title></article>
        |]]><article key="conf/review/Real"><title>Real</title></article></dblp>""".stripMargin
    assertLexicalSplit("cdata-split", xml, "<![CDATA[")
  }

  test("committed OpenAlex and ORCID samples keep native identifiers on success records") {
    val openAlex = sample("datasets/samples/openalex/works.jsonl")
    val orcid = sample("datasets/samples/orcid/records.jsonl")
    assume(Files.isRegularFile(openAlex) && Files.isRegularFile(orcid), "missing samples")
    val openAlexText = Files.readString(openAlex)
    val orcidText = Files.readString(orcid)
    assert(openAlexText.contains("I79516672"))
    assert(orcidText.contains("24870415"))
    assert(orcidText.contains("7279939"))
    assert(orcidText.contains("part-of"))
    val result =
      HadoopPrepPipeline.execute(committedRequest("retained-ids", maxRecordBytes = 1048576L))
    assert(result.isRight, result.left.toOption.getOrElse(""))
    val value = result.toOption.get
    assert(!value.reused)
    val success = successLines(exportLines(value.directory))
    val rendered = success.mkString("\n")
    assert(rendered.contains("I79516672"), "I79516672 missing from success export")
    assert(rendered.contains("24870415"), "24870415 missing from success export")
    assert(rendered.contains("7279939"), "7279939 missing from success export")
    assert(rendered.contains("part-of"), "part-of missing from success export")
    val observed = success.flatMap(line => CoreJson.parse[Institution](line).toOption)
    assert(
      observed.exists(_.observedSourceIds.exists(_.value.contains("I79516672"))),
      "I79516672 is not an observedSourceIds value"
    )
    val references = success
      .flatMap(line => CoreJson.parse[OrcidActivityRecord](line).toOption)
      .flatMap(_.workReferences)
    assert(references.exists(_.value == "24870415"), "24870415 is not a workReferences value")
    assert(references.exists(_.value == "7279939"), "7279939 is not a workReferences value")
    assert(
      references.exists(_.relationship.contains("part-of")),
      "part-of is not a workReferences relationship"
    )
  }

  test(
    "self-closing author rejects with missing required field and does not emit Ada at ordinal 1"
  ) {
    val header = DblpXml.header("<!DOCTYPE dblp []>")
    assert(header.unsafe.isEmpty)
    val xml =
      """<article key="conf/review/A"><author/><author>Ada</author><title>T</title></article>"""
    val records = DblpRecords.parse(
      xml,
      header,
      freshRunId(),
      "dblp-independent",
      "self-closing-author",
      100000L,
      100000L
    )
    val rejected = records.collect { case EmittedRecord.Rejected(record) => record }
    val rendered = records.map(_.json).mkString("\n")
    assert(
      rejected.exists(_.reasonCode == RejectReasonCode.MissingRequiredField),
      rendered
    )
    val adaAtOne = records.collect { case EmittedRecord.Work(work) => work }.exists { work =>
      work.authors.exists(author => author.nameText == "Ada" && author.ordinal == 1)
    }
    assert(!adaAtOne, rendered)
    assert(
      records.forall { case EmittedRecord.Rejected(_) => true; case _ => false },
      rendered
    )
  }

  test("truncated export part is not a successful reuse of the identical request") {
    val dir = phase4RunDir("damaged-reuse")
    val (dblp, openAlex, crossref, orcid) = writeCorpus(dir)
    val out = dir.resolve("output")
    val runId = freshRunId()
    val request = pipelineRequest(out, dblp, openAlex, crossref, orcid, 16, 32, 128, runId)
    val first = HadoopPrepPipeline.execute(request)
    assert(first.isRight, first.left.toOption.getOrElse(""))
    assert(first.toOption.exists(result => !result.reused))
    val directory = first.toOption.get.directory
    assert(Files.isRegularFile(directory.resolve(OutputGate.MarkerName)))
    val part = nonemptyExportPart(directory)
    val before = Files.size(part)
    assert(before > 0)
    Files.write(part, Array.emptyByteArray)
    assert(Files.size(part) == 0L)
    val second = HadoopPrepPipeline.execute(request)
    assert(second.forall(result => !result.reused), s"reused damaged export: $second")
  }

  test("Request hadoopConf fs.s3.impl is used by filesystem validation") {
    val dir = phase4RunDir("caller-fs")
    val (dblp, openAlex, crossref, orcid) = writeCorpus(dir)
    val loader = memoryS3Loader()
    val previous = Thread.currentThread.getContextClassLoader
    Thread.currentThread.setContextClassLoader(loader)
    try {
      val impl = loader.loadClass(memoryS3Impl)
      val conf = new Configuration()
      conf.setClassLoader(loader)
      conf.set("fs.s3.impl", impl.getName)
      conf.set("fs.s3.impl.disable.cache", "true")
      val local = pipelineRequest(
        dir.resolve("unused-local"),
        dblp,
        openAlex,
        crossref,
        orcid,
        16,
        32,
        128,
        freshRunId()
      )
      val request = local.copy(
        config = local.config.copy(outputRoot = "s3://phase4-bucket/out"),
        hadoopConf = conf
      )
      assert(request.hadoopConf.get("fs.s3.impl") == impl.getName)
      val message =
        try
          HadoopPrepPipeline.execute(request) match {
            case Left(error) => error
            case Right(_)    => ""
          }
        catch {
          case error: Exception =>
            Option(error.getMessage).getOrElse(error.toString)
        }
      assert(!message.contains(filesystemGap), message)
    } finally {
      Thread.currentThread.setContextClassLoader(previous)
      loader.close()
    }
  }

  private def committedRequest(label: String, maxRecordBytes: Long): HadoopPrepPipeline.Request = {
    val configPath = sample("modules/core/src/main/resources/scholarchain.hadoop-prep.v1.json")
    val loaded = HadoopPrepConfigLoader.load(configPath).toOption.get
    val config = loaded.copy(
      outputRoot = phase4RunDir(label).toString,
      executionMode = HadoopExecutionMode.Local,
      maxRecordBytes = maxRecordBytes
    )
    HadoopPrepPipeline.Request(
      config,
      sample("datasets/samples/dblp/linked-records.xml").toString,
      sample("datasets/samples/openalex/works.jsonl").toString,
      sample("datasets/samples/crossref/works.jsonl").toString,
      sample("datasets/samples/orcid/records.jsonl").toString,
      HadoopPrepPipeline.DefaultSnapshots,
      freshRunId(),
      retrievalDates = HadoopPrepPipeline.DefaultRetrievalDates
    )
  }

  private def assertLexicalSplit(label: String, xml: String, opener: String): Unit = {
    val bytes = xml.getBytes(StandardCharsets.UTF_8)
    assert(bytes.length == xml.length, "fixture must stay ASCII so split offsets match chars")
    val opened = xml.indexOf(opener)
    val fakeAt = xml.indexOf("<article key=\"conf/review/Fake\">")
    val start = opened + opener.length
    assert(opened >= 0 && start < fakeAt)
    val dir = phase4RunDir(label)
    val path = dir.resolve("input.xml")
    Files.write(path, bytes)
    val size = Files.size(path)
    val splitKeys = publicationKeys(readDblpSplit(path, start.toLong, size - start))
    val wholeKeys = publicationKeys(readDblpSplit(path, 0L, size))
    assert(!splitKeys.contains("conf/review/Fake"), splitKeys.mkString(","))
    assert(!wholeKeys.contains("conf/review/Fake"), wholeKeys.mkString(","))
    assert(wholeKeys.contains("conf/review/Real"), wholeKeys.mkString(","))
  }

  private def readDblpSplit(path: Path, start: Long, length: Long): Vector[String] = {
    val conf = new Configuration()
    conf.setLong(ConfKeys.MaxRecordBytes, 1048576L)
    val split = new FileSplit(FsPaths.file(path.toString), start, length, Array.empty[String])
    val context = new TaskAttemptContextImpl(conf, new TaskAttemptID())
    val reader = new DblpXmlRecordReader
    try {
      reader.initialize(split, context)
      val found = Vector.newBuilder[String]
      while (reader.nextKeyValue()) found += reader.getCurrentValue.toString
      found.result()
    } finally reader.close()
  }

  private def publicationKeys(encoded: Vector[String]): Vector[String] =
    encoded.flatMap { text =>
      val newline = text.indexOf('\n')
      val body = if (newline < 0) text else text.substring(newline + 1)
      val name = DblpXml.rootName(body).getOrElse("")
      if (!DblpXml.RecordNames.contains(name)) None
      else DblpXml.attr(body, "key")
    }

  private def successLines(lines: Vector[String]): Vector[String] =
    lines.filter(line => CoreJson.parse[RejectRecord](line).isLeft)

  private def oversizeMentions(lines: Vector[String], key: String): Boolean =
    rejects(lines).exists { reject =>
      reject.reasonCode == RejectReasonCode.OversizeRecord &&
      (reject.sourceLocator.contains(key) ||
        reject.diagnosticExcerpt.exists(_.contains(key)) ||
        CoreJson.compact(reject).contains(key))
    }

  private def nonemptyExportPart(directory: Path): Path = {
    val exportDir = directory.resolve("export")
    val walk = Files.walk(exportDir)
    try
      walk
        .iterator()
        .asScala
        .filter(path => Files.isRegularFile(path))
        .find { path =>
          val name = path.getFileName.toString
          name.startsWith("part") && !name.startsWith("_") && !name.startsWith(".") &&
          !name.endsWith(".crc") && Files.size(path) > 0
        }
        .getOrElse(fail(s"no nonempty export part under $exportDir"))
    finally walk.close()
  }

  private def writeCorpus(dir: Path): (Path, Path, Path, Path) = {
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-blockers/S1",
          "<author>Ada</author>",
          "<title>Stub</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9100000301","title":"Stub","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.blocker","title":["Stub"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    (dblp, openAlex, crossref, orcid)
  }

  private def memoryS3Loader(): URLClassLoader = {
    val target = repoRoot.resolve("modules/hadoop/target")
    val relative = "edu/uic/cs441/scholarchain/hadoop/MemoryS3FileSystem.class"
    val found =
      if (!Files.isDirectory(target)) None
      else {
        val walk = Files.walk(target, 4)
        try
          walk.iterator().asScala.collectFirst {
            case path
                if Files.isDirectory(path) && path.getFileName.toString == "test-classes" &&
                  Files.isRegularFile(path.resolve(relative)) =>
              path
          }
        finally walk.close()
      }
    val classes = found.getOrElse(fail(s"$memoryS3Impl is not compiled under $target"))
    new URLClassLoader(Array(classes.toUri.toURL), Thread.currentThread.getContextClassLoader)
  }
}
