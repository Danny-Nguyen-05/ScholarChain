package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.mapreduce.TaskAttemptID
import org.apache.hadoop.mapreduce.lib.input.FileSplit
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat
import org.apache.hadoop.mapreduce.task.TaskAttemptContextImpl
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

class HadoopPrepReviewSpec extends AnyFunSuite {
  try org.apache.log4j.Logger.getRootLogger.setLevel(org.apache.log4j.Level.WARN)
  catch { case _: Throwable => () }

  private val runId = StableIds
    .newRunId(java.util.UUID.fromString("12121212-1212-4212-8212-121212121212"))
    .toOption
    .get
  private val retrieval = Map(
    SourceType.Dblp -> "2026-10-05",
    SourceType.OpenAlex -> "2026-10-05",
    SourceType.Crossref -> "2026-10-05",
    SourceType.Orcid -> "2026-10-05"
  )
  private val snapshots = Map(
    SourceType.Dblp -> "dblp-review",
    SourceType.OpenAlex -> "openalex-review",
    SourceType.Crossref -> "crossref-review",
    SourceType.Orcid -> "orcid-review"
  )

  test("bibliographic candidates do not require a shared DOI") {
    val dir = Files.createTempDirectory("review-block")
    val dblp = dir.resolve("works.xml")
    Files.writeString(
      dblp,
      """<?xml version="1.0"?><dblp>
        |<inproceedings key="conf/review/One"><author>Ada Lovelace</author><title>Shared Paper</title><year>2020</year></inproceedings>
        |<inproceedings key="conf/review/Two"><author>Ada Lovelace</author><title>Shared Paper</title><year>2020</year></inproceedings>
        |</dblp>""".stripMargin
    )
    val result = runPipeline(
      dir,
      dblp,
      empty(dir, "oa.jsonl"),
      empty(dir, "cr.jsonl"),
      empty(dir, "orcid.jsonl")
    )
    val lines = LogicalRecords.lines(result.directory.resolve("export"))
    val candidates = lines.flatMap(line => CoreJson.parse[MatchCandidate](line).toOption)
    assert(candidates.exists { candidate =>
      candidate.featurePolicyVersion == PreparationFeatures.policyV2 &&
      candidate.blockKey.startsWith("title-year:") &&
      candidate.features.exists(item =>
        item.name == PreparationFeatures.exactSharedIdentifier && item.value == 0.0
      ) &&
      candidate.features.exists(item =>
        item.name == PreparationFeatures.titleEqual && item.value == 1.0
      )
    })
    assert(!lines.exists(_.contains("\"outcome\"")))
    assert(Files.walk(result.directory.resolve("export")).iterator().asScala.exists { path =>
      path.toString.contains("/author-mention/")
    })
    val mentions = lines.flatMap(line => CoreJson.parse[AuthorMention](line).toOption)
    assert(mentions.exists(_.sourceRecordId == "conf/review/One"))
  }

  test("ampersand entities, comments, and CDATA stay inside one record") {
    val works = dblpWorks(
      """<?xml version="1.0"?><dblp>
        |<article key="journals/review/Self"/>
        |<inproceedings key="conf/review/Amp"><author>Ada Lovelace</author><title>A &amp; B</title><year>2020</year><!-- </inproceedings> --><note><![CDATA[</inproceedings>]]></note></inproceedings>
        |<inproceedings key="conf/review/Num"><author>Ada Lovelace</author><title>A &#38; B</title><year>2020</year></inproceedings>
        |<mystery key="conf/review/Nope"></mystery>
        |</dblp>""".stripMargin
    )
    assert(works.map(_.sourceRecordId).toSet == Set("conf/review/Amp", "conf/review/Num"))
    assert(works.forall(_.normalizedTitle.contains("&")))
    assert(works.forall(!_.normalizedTitle.contains("amp")))
  }

  test("a truncated record is rejected and is not accepted") {
    val lines = dblpLines(
      """<?xml version="1.0"?><dblp>
        |<inproceedings key="conf/review/Cut"><author>Ada Lovelace</author><title>Cut</title>
        |</dblp>""".stripMargin
    )
    assert(lines.exists(_.contains("MALFORMED_RECORD")))
    assert(!lines.exists(_.contains("conf/review/Cut")))
  }

  test("one observation can repeat an institution without a duplicate-observation reject") {
    val dir = Files.createTempDirectory("review-repeat")
    val openAlex = dir.resolve("oa.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"W2741800001","display_name":"Shared Lab","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"},"institutions":[{"display_name":"Analytical Engine","ror":"https://ror.org/02catss52"}]},{"author":{"display_name":"Charles Babbage"},"institutions":[{"display_name":"Analytical Engine","ror":"https://ror.org/02catss52"}]}]}"""
    )
    val result =
      runPipeline(dir, emptyXml(dir), openAlex, empty(dir, "cr.jsonl"), empty(dir, "orcid.jsonl"))
    val lines = LogicalRecords.lines(result.directory.resolve("export"))
    assert(!lines.exists(_.contains("DUPLICATE_IDENTICAL_OBSERVATION")))
    assert(lines.exists(_.contains("W2741800001")))
  }

  test("the launch cap accepts the same prefix for one split and for many splits") {
    val lines = (1 to 3).map(i =>
      s"""{"id":"W274180000$i","display_name":"Paper $i","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"}}]}"""
    )
    val one = acceptedOpenAlex(lines, splitBytes = None)
    val many = acceptedOpenAlex(lines, splitBytes = Some(1L))
    assert(one == many)
    assert(one.contains("W2741800001"))
    assert(!one.contains("W2741800002"))
    assert(one.contains("maxLocalSampleRecords"))
  }

  test("an oversize JSON line is rejected before it is kept as a string") {
    val dir = Files.createTempDirectory("review-oversize")
    val line = """{"id":"W-oversize-line-exceeds-limit"}"""
    assert(line.getBytes(StandardCharsets.UTF_8).length > 16)
    val openAlex = dir.resolve("oa.jsonl")
    Files.writeString(openAlex, line + "\n")
    val out = dir.resolve("out")
    val conf = PrepJobs.configuration(config(dir, 16), runId, snapshots)
    val job =
      PrepJobs.normalize(
        conf,
        openAlex.toString,
        empty(dir, "cr.jsonl").toString,
        empty(dir, "orcid.jsonl").toString,
        out
      )
    PrepJobs.run("J02", job)
    val text = partText(out)
    assert(text.contains("OVERSIZE_RECORD"))
    val works = text.split('\n').flatMap(Lines.unpack).collect {
      case (kind, _) if kind == Kinds.Work => kind
    }
    assert(works.isEmpty)
  }

  test("cluster mode does not set the local framework") {
    val dir = Files.createTempDirectory("review-cluster")
    val conf = PrepJobs.configuration(
      config(dir, 1048576).copy(executionMode = HadoopExecutionMode.Cluster),
      runId,
      snapshots
    )
    assert(conf.get("mapreduce.framework.name") == "yarn")
    assert(conf.get("mapreduce.framework.name") != "local")
  }

  test("a one-slash file URI round-trips to the real directory") {
    val dir = Files.createTempDirectory("review-file-uri")
    val marker = dir.resolve("marker.txt")
    Files.writeString(marker, "ok")
    val oneSlash = "file:" + dir.toAbsolutePath.normalize.toString
    assert(!oneSlash.contains("://"))
    val resolved = FsPaths.local(FsPaths.file(oneSlash))
    assert(Files.isSameFile(resolved, dir))
    assert(Files.isSameFile(resolved.resolve("marker.txt"), marker))
    val relative = FsPaths.local(FsPaths.file("datasets/samples/dblp/linked-records.xml"))
    assert(Files.isRegularFile(relative))
    assert(relative.isAbsolute)
  }

  test("export comparison reads both trees and does not treat a missing export as empty") {
    val left = fileLocation(writeExport("review-digest-left", "{\"workId\":\"left\"}\n"))
    val right = fileLocation(writeExport("review-digest-right", "{\"workId\":\"right\"}\n"))
    val same = fileLocation(writeExport("review-digest-same", "{\"workId\":\"left\"}\n"))
    val missingA = fileLocation(Files.createTempDirectory("review-digest-missing-a"))
    val missingB = fileLocation(Files.createTempDirectory("review-digest-missing-b"))
    assert(HadoopPrepMain.logicalRecordsEqual(left, runId, same, runId))
    assert(!HadoopPrepMain.logicalRecordsEqual(left, runId, right, runId))
    assert(HadoopPrepMain.exportDigest(missingA, runId).isEmpty)
    assert(!HadoopPrepMain.logicalRecordsEqual(missingA, runId, missingB, runId))
    assert(!HadoopPrepMain.logicalRecordsEqual(missingA, runId, left, runId))
    assert(!HadoopPrepMain.logicalRecordsEqual(left, runId, missingB, runId))
  }

  test("duplicate export lines do not cancel and opposite orders stay equal") {
    val lineA = "{\"workId\":\"A\"}\n"
    val lineB = "{\"workId\":\"B\"}\n"
    val aa = fileLocation(writeExport("review-digest-aa", lineA + lineA))
    val bb = fileLocation(writeExport("review-digest-bb", lineB + lineB))
    val ab = fileLocation(writeExport("review-digest-ab", lineA + lineB))
    val ba = fileLocation(writeExport("review-digest-ba", lineB + lineA))
    val once = fileLocation(writeExport("review-digest-once", lineA))
    assert(!HadoopPrepMain.logicalRecordsEqual(aa, runId, bb, runId))
    assert(HadoopPrepMain.logicalRecordsEqual(ab, runId, ba, runId))
    assert(!HadoopPrepMain.logicalRecordsEqual(aa, runId, once, runId))
  }

  test("an s3 output root stays a Hadoop path outside the working directory") {
    val path = FsPaths.runPath(
      "s3://phase4-bucket/out",
      "run:12121212-1212-4212-8212-121212121212"
    )
    assert(path.toString.startsWith("s3://phase4-bucket/out/"))
    assert(!path.toString.contains(Path.of("").toAbsolutePath.toString))
    assert(FsPaths.isRemote("s3://phase4-bucket/out"))
  }

  test("an s3 output root is not refused before a filesystem implementation is required") {
    val resolved = HadoopPrepPipeline.resolveOutput("s3://phase4-bucket/out", runId)
    assert(resolved.isRight)
    val remote = resolved.toOption.get
    assert(remote.toString.startsWith("s3://phase4-bucket/out/"))
    assert(!remote.toString.contains(Path.of("").toAbsolutePath.toString))
    val ran = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config(Files.createTempDirectory("review-s3"), 1048576)
          .copy(outputRoot = "s3://phase4-bucket/out"),
        "unused-dblp.xml",
        "unused-openalex.jsonl",
        "unused-crossref.jsonl",
        "unused-orcid.jsonl",
        snapshots,
        runId,
        retrievalDates = retrieval
      )
    )
    assert(ran.isLeft)
    val message = ran.left.toOption.get
    assert(!message.contains("refusing to create a local directory"))
    assert(message.contains("s3://phase4-bucket/out"))
    assert(!Files.exists(Path.of("s3:")))
    assert(!Files.exists(Path.of("s3:/phase4-bucket")))
  }

  test("a finished remote output is Right and an identical remote identity is reused") {
    val forbidden = Seq(
      "remote output was written through Hadoop FileSystem; no local directory was created",
      "reused remote output has no local directory"
    )
    FsIO.withSettings(
      "fs.s3.impl" -> classOf[MemoryS3FileSystem].getName,
      "fs.s3.impl.disable.cache" -> "true"
    ) {
      MemoryS3FileSystem.clear()
      val outputRoot = "s3://phase4-bucket/out"
      val cfg =
        config(Files.createTempDirectory("review-remote"), 1048576).copy(outputRoot = outputRoot)
      val request = HadoopPrepPipeline.Request(
        cfg,
        "datasets/samples/dblp/linked-records.xml",
        "datasets/samples/openalex/works.jsonl",
        "datasets/samples/crossref/works.jsonl",
        "datasets/samples/orcid/records.jsonl",
        Map.empty,
        runId
      )
      val conf = FsIO.configuration()
      val directory = HadoopPrepPipeline.resolveOutput(outputRoot, runId).toOption.get
      val bound = Seq(
        SourceType.Dblp -> request.dblp,
        SourceType.OpenAlex -> request.openAlex,
        SourceType.Crossref -> request.crossref,
        SourceType.Orcid -> request.orcid
      ).map { case (source, path) =>
        source -> Acquisition
          .bind(source, path, request.snapshots, request.retrievalDates, conf)
          .toOption
          .get
      }.toMap
      FsIO.writeUtf8(
        new org.apache.hadoop.fs.Path(directory, "run-manifest.json"),
        CoreJson.pretty(HadoopPrepPipeline.buildManifest(request, bound)),
        conf
      )
      FsIO.writeUtf8(
        new org.apache.hadoop.fs.Path(directory, "counter-summary.json"),
        """{"inputRecords":1}""",
        conf
      )
      FsIO.writeUtf8(
        new org.apache.hadoop.fs.Path(
          directory,
          "export/snapshot=dblp-2026-10-03/run=remote/work/part-r-00000"
        ),
        "{\"workId\":\"work:openalex:W1\"}\n",
        conf
      )
      val partitions = OutputGate.listPartitions(new org.apache.hadoop.fs.Path(directory, "export"))
      assert(partitions.nonEmpty, partitions.mkString(","))
      OutputGate.write(directory, HadoopPrepPipeline.outputIdentity(runId, cfg, bound, partitions))
      val written =
        HadoopPrepPipeline.completeResult(
          directory,
          runId,
          reused = false,
          Map("inputRecords" -> 1L)
        )
      val finished = Right(written)
      assert(finished.isRight)
      assert(!written.reused)
      assert(written.outputLocation.startsWith("s3://phase4-bucket/out/"))
      assert(written.directory.toString.startsWith("s3://phase4-bucket/out/"))
      assert(written.representative.exists(_.contains("work:openalex:W1")))
      assert(!Files.exists(Path.of("s3:")))
      assert(!Files.exists(Path.of("s3:/phase4-bucket")))
      val again = HadoopPrepPipeline.execute(request)
      assert(again.isRight, again.left.toOption.getOrElse(""))
      val reused = again.toOption.get
      assert(reused.reused)
      assert(reused.outputLocation == written.outputLocation)
      assert(!forbidden.exists(again.left.toOption.getOrElse("").contains))
      assert(!forbidden.exists(written.outputLocation.contains))
      MemoryS3FileSystem.clear()
    }
  }

  test("a bad OpenAlex institution id is rejected while the valid ROR affiliation is kept") {
    val records = openAlex(
      """{"id":"W2741800001","display_name":"Shared Lab","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"},"institutions":[{"display_name":"Analytical Engine","ror":"https://ror.org/02catss52","id":"not-an-institution"}]}]}"""
    )
    assert(rejected(records, "not-an-institution"))
    val institutions = records.collect { case EmittedRecord.InstitutionRec(value) => value }
    assert(institutions.exists(_.institutionId == "institution:ror:02catss52"))
  }

  test("a venue id that fails to parse is an invalid-identifier reject") {
    val records = openAlex(
      """{"id":"W2741800001","display_name":"Shared Lab","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"}}],"primary_location":{"source":{"id":"not-a-venue","display_name":"Proceedings"}}}"""
    )
    assert(rejected(records, "not-a-venue"))
    assert(!records.exists(_.isInstanceOf[EmittedRecord.VenueRec]))
  }

  test("a topic id that fails to parse is an invalid-identifier reject") {
    val records = openAlex(
      """{"id":"W2741800001","display_name":"Shared Lab","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"}}],"topics":[{"id":"not-a-topic","display_name":"Logic"}]}"""
    )
    assert(rejected(records, "not-a-topic"))
    assert(!records.exists(_.isInstanceOf[EmittedRecord.TopicRec]))
  }

  test("a graph edge that fails validation is a schema-failure reject") {
    val provenance = ProvenanceFactory(
      SourceType.OpenAlex,
      "W2741800001",
      Some("https://openalex.org/W2741800001"),
      "openalex-review",
      runId,
      retrievalDate = Some("2026-10-05")
    )
    val graph = GraphEdge(
      "edge:not-stable",
      SchemaVersions.domain,
      "not-a-mention",
      GraphEdgeType.Authored,
      "not-a-work",
      PrepLimits.FeaturePolicy,
      GraphSourceEvidence.Work("not-a-work"),
      Vector.empty,
      None,
      provenance
    )
    val written = scala.collection.mutable.ArrayBuffer.empty[(String, String)]
    ExportReducer.writeCheckedGraph(
      graph,
      "openalex-review",
      runId,
      (kind, json, _, _) => written += ((kind, json))
    )
    assert(written.exists { case (kind, json) =>
      kind == Kinds.Reject && json.contains("SCHEMA_FAILURE")
    })
    assert(!written.exists(_._1 == Kinds.GraphEdge))
  }

  test("sample cutoffs follow the qualified URI when two files share a basename") {
    val conf = new Configuration()
    val openAlex = new org.apache.hadoop.fs.Path("/tmp/scholarchain-openalex/works.jsonl")
    val crossref = new org.apache.hadoop.fs.Path("/tmp/scholarchain-crossref/works.jsonl")
    val fs = openAlex.getFileSystem(conf)
    conf.setInt(ConfKeys.SampleCount, 2)
    conf.set(ConfKeys.samplePath(0), fs.makeQualified(openAlex).toString)
    conf.setLong(ConfKeys.sampleCutoff(0), 11L)
    conf.set(ConfKeys.samplePath(1), fs.makeQualified(crossref).toString)
    conf.setLong(ConfKeys.sampleCutoff(1), 29L)
    assert(SampleBound.cutoff(conf, openAlex) == 11L)
    assert(SampleBound.cutoff(conf, crossref) == 29L)
  }

  test("Crossref keeps an affiliation name and an abstract reference") {
    val json =
      """{"message":{"DOI":"10.1000/review.aff","title":["Affiliation Abstract"],"author":[{"given":"Ada","family":"Lovelace","affiliation":[{"name":"Analytical Engine"}]}],"abstract":"A short abstract."}}"""
    val records = JsonSources.parseLine(
      SourceType.Crossref,
      json,
      runId,
      "crossref-review",
      "crossref@0",
      100000,
      Some("2026-10-05")
    )
    val work = records.collect { case EmittedRecord.Work(value) => value }.head
    val affiliations =
      records.collect { case EmittedRecord.Affiliation(value) => value }
    val texts = records.collect { case EmittedRecord.TextDoc(value) => value }
    assert(affiliations.exists { item =>
      item.organizationName.contains("Analytical Engine") && item.institutionId.isEmpty
    })
    assert(texts.exists(_.documentType == EmittedTextDocument.abstractDocumentType))
    assert(work.abstractTextRef == texts.headOption.map(_.textId))
  }

  test("a malformed DOI is an invalid-identifier reject") {
    val records = JsonSources.parseLine(
      SourceType.Crossref,
      """{"message":{"DOI":"not-a-doi","title":["Broken"]}}""",
      runId,
      "crossref-review",
      "crossref@1",
      100000,
      Some("2026-10-05")
    )
    val reasons = records.collect { case EmittedRecord.Rejected(value) => value.reasonCode }
    assert(reasons.contains(RejectReasonCode.InvalidIdentifier))
  }

  test("intermediate compression still feeds the next job") {
    val dir = Files.createTempDirectory("review-gzip")
    val input = dir.resolve("one.xml")
    Files.writeString(
      input,
      """<?xml version="1.0"?><dblp><inproceedings key="conf/review/Zip"><author>Ada Lovelace</author><title>Compressed</title><year>2020</year></inproceedings></dblp>"""
    )
    val conf = PrepJobs.configuration(
      config(dir, 1048576).copy(compressionCodec = "gzip", intermediateCompressionEnabled = true),
      runId,
      snapshots
    )
    val extracted = dir.resolve("j01")
    PrepJobs.run("J01", PrepJobs.dblp(conf, input.toString, extracted, None))
    assert(Files.list(extracted).iterator().asScala.exists(_.getFileName.toString.endsWith(".gz")))
    val indexed = dir.resolve("j03")
    PrepJobs.run("J03", PrepJobs.index(conf, Seq(extracted), indexed))
    assert(partText(indexed).contains("conf/review/Zip"))
  }

  test("committed samples keep acquisition snapshot ids and retrieval dates") {
    val conf = new Configuration()
    val expected = Seq(
      SourceType.Dblp -> ("datasets/samples/dblp/linked-records.xml", "dblp-2026-10-03"),
      SourceType.OpenAlex -> ("datasets/samples/openalex/works.jsonl", "openalex-rest-2026-10-05"),
      SourceType.Crossref -> ("datasets/samples/crossref/works.jsonl", "crossref-rest-2026-10-05"),
      SourceType.Orcid -> ("datasets/samples/orcid/records.jsonl", "orcid-public-api-2026-10-05")
    )
    expected.foreach { case (source, (relative, snapshot)) =>
      val bound = Acquisition.bind(source, relative, Map.empty, Map.empty, conf)
      assert(bound.isRight, bound.left.toOption.getOrElse(""))
      val (foundSnapshot, foundDate, hash) = bound.toOption.get
      assert(foundSnapshot == snapshot)
      assert(foundDate == "2026-10-05")
      assert(hash.matches("[0-9a-f]{64}"))
    }
    val temp = Files.createTempFile("review-override", ".jsonl")
    val missing = Acquisition.bind(
      SourceType.OpenAlex,
      temp.toString,
      Map(SourceType.OpenAlex -> "openalex-rest-2026-10-05"),
      Map.empty,
      conf
    )
    assert(missing.isLeft)
  }

  test("an invalid limit fails before a job launch") {
    val dir = Files.createTempDirectory("review-limit")
    val bad = config(dir, 0)
    val result = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        bad,
        emptyXml(dir).toString,
        empty(dir, "oa.jsonl").toString,
        empty(dir, "cr.jsonl").toString,
        empty(dir, "orcid.jsonl").toString,
        snapshots,
        runId,
        retrievalDates = retrieval
      )
    )
    assert(result.isLeft)
    assert(result.left.exists(_.contains("maxRecordBytes")))
  }

  private def acceptedOpenAlex(lines: Seq[String], splitBytes: Option[Long]): String = {
    val dir = Files.createTempDirectory("review-cap")
    val openAlex = dir.resolve("oa.jsonl")
    Files.writeString(openAlex, lines.mkString("\n") + "\n")
    val out = dir.resolve("out")
    val conf = PrepJobs.configuration(config(dir, 1048576, sample = 1), runId, snapshots)
    val job =
      PrepJobs.normalize(
        conf,
        openAlex.toString,
        empty(dir, "cr.jsonl").toString,
        empty(dir, "orcid.jsonl").toString,
        out
      )
    splitBytes.foreach(size => FileInputFormat.setMaxInputSplitSize(job, size))
    PrepJobs.run("J02", job)
    partText(out)
  }

  private def dblpWorks(xml: String): Vector[WorkRecord] =
    dblpLines(xml)
      .flatMap(line => Lines.unpack(line).toVector)
      .collect {
        case (kind, json) if kind == Kinds.Work =>
          CoreJson.parse[WorkRecord](json).toOption
      }
      .flatten

  private def dblpLines(xml: String): Vector[String] = {
    val dir = Files.createTempDirectory("review-xml")
    val input = dir.resolve("in.xml")
    Files.writeString(input, xml)
    val out = dir.resolve("out")
    val conf = PrepJobs.configuration(config(dir, 1048576), runId, snapshots)
    PrepJobs.run("J01", PrepJobs.dblp(conf, input.toString, out, None))
    partText(out).split('\n').toVector.filter(_.nonEmpty)
  }

  test("expanded DBLP JSON under the intermediate cap is exported when the source cap is 1024") {
    val title = "T" * 400
    val article =
      """<inproceedings key="conf/review/Cap"><author>Ada</author><title>""" +
        title + """</title><year>2020</year></inproceedings>"""
    assert(article.getBytes(StandardCharsets.UTF_8).length < 1024)
    val dir = Files.createTempDirectory("review-source-cap")
    val dblp = dir.resolve("works.xml")
    Files.writeString(dblp, s"""<?xml version="1.0"?><dblp>$article</dblp>""")
    val result = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config(dir.resolve("root"), 1024),
        dblp.toString,
        empty(dir, "oa.jsonl").toString,
        empty(dir, "cr.jsonl").toString,
        empty(dir, "orcid.jsonl").toString,
        snapshots,
        freshRun("14141414-1414-4414-8414-141414141414"),
        retrievalDates = retrieval
      )
    )
    assert(result.isRight, result.left.toOption.getOrElse(""))
    val lines = LogicalRecords.lines(result.toOption.get.directory.resolve("export"))
    val workJson = lines.find { line =>
      CoreJson
        .parse[WorkRecord](line)
        .toOption
        .exists(_.sourceRecordId == "conf/review/Cap")
    }
    assert(workJson.nonEmpty, lines.mkString("\n"))
    val json = workJson.get
    assert(json.getBytes(StandardCharsets.UTF_8).length > 1024)
    assert(json.contains(title))
  }

  test("a line over the intermediate cap becomes an oversize reject in the export") {
    val dir = Files.createTempDirectory("review-intermediate-cap")
    val input = dir.resolve("j01")
    Files.createDirectories(input)
    val padding = "x" * ((1024 * 1024) + 64)
    Files.writeString(input.resolve("part-m-00000"), s"work\t$padding\n")
    val conf = PrepJobs.configuration(
      config(dir.resolve("root"), 1024),
      freshRun("15151515-1515-4515-8515-151515151515"),
      snapshots
    )
    assert(conf.getLong(ConfKeys.MaxIntermediateBytes, 0L) == IntermediateBytes.Floor)
    val indexed = dir.resolve("j03")
    PrepJobs.run("J03", PrepJobs.index(conf, Seq(input), indexed))
    val joined = dir.resolve("j04")
    PrepJobs.run("J04", PrepJobs.join(conf, Seq(indexed), joined))
    val exported = dir.resolve("export")
    PrepJobs.run("J09", PrepJobs.exportJob(conf, Seq(joined), exported))
    val lines = LogicalRecords.lines(exported)
    assert(lines.exists(_.contains("OVERSIZE_RECORD")), lines.mkString("\n"))
  }

  test("a 2500-byte intermediate line is kept when the source cap is 1024") {
    val dir = Files.createTempDirectory("review-line-cap")
    val path = dir.resolve("line.txt")
    val body = "y" * 2500
    Files.writeString(path, body + "\n")
    val conf = new Configuration()
    conf.setLong(ConfKeys.MaxRecordBytes, 1024L)
    conf.setLong(ConfKeys.BoundedLineBytes, IntermediateBytes.Floor)
    val reader = new BoundedLineRecordReader
    reader.initialize(
      new FileSplit(new org.apache.hadoop.fs.Path(path.toUri), 0, Files.size(path), Array.empty),
      new TaskAttemptContextImpl(conf, new TaskAttemptID())
    )
    try {
      assert(reader.nextKeyValue())
      assert(reader.getCurrentValue.toString == body)
    } finally reader.close()
  }

  test("OpenAlex institution keeps the native id beside a preferred ROR") {
    val records = openAlex(
      """{"id":"W2741800001","display_name":"Shared Lab","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"},"institutions":[{"display_name":"University of Louisiana at Lafayette","ror":"https://ror.org/01x8rc503","id":"https://openalex.org/I79516672"}]}]}"""
    )
    val institutions = records.collect { case EmittedRecord.InstitutionRec(value) => value }
    val institution = institutions.find(_.institutionId == "institution:ror:01x8rc503")
    assert(institution.nonEmpty, records.map(_.json).mkString("\n"))
    val observed = institution.get.observedSourceIds
    assert(observed.exists { id =>
      id.namespace == IdentifierNamespace.OpenAlexInstitution.wire && id.value == "I79516672"
    })
    val rows = DerivedRecords.indexRows(
      EmittedRecord.InstitutionRec(institution.get),
      Digests.sha256Text(institution.get.institutionId)
    )
    val indexed = rows.find(_.entry.namespace == IdentifierNamespace.OpenAlexInstitution)
    assert(indexed.nonEmpty, rows.map(_.entry.normalizedValue).mkString(","))
    assert(indexed.get.entry.normalizedValue == "I79516672")
    assert(indexed.get.entry.preferredWorkId.isEmpty)
    assert(DomainValidation.check(indexed.get.entry).isRight)
    assert(CoreJson.compact(institution.get).contains("I79516672"))
    val malformedOnly = openAlex(
      """{"id":"W2741800002","display_name":"No ROR","publication_year":2020,"authorships":[{"author":{"display_name":"Ada Lovelace"},"institutions":[{"display_name":"Unknown","id":"not-an-institution"}]}]}"""
    )
    assert(rejected(malformedOnly, "not-an-institution"))
    assert(!malformedOnly.exists(_.isInstanceOf[EmittedRecord.InstitutionRec]))
  }

  test("ORCID activity keeps every external id and relationship") {
    val records = JsonSources.parseLine(
      SourceType.Orcid,
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"},"activities-summary":{"works":{"group":[{"work-summary":[{"path":"/0000-0002-4414-6920/work/1","put-code":1,"title":{"title":{"value":"Kept"}},"external-ids":{"external-id":[{"external-id-type":"doi","external-id-value":"10.1000/kept.doi","external-id-relationship":"self"},{"external-id-type":"other-id","external-id-value":"24870415","external-id-relationship":"self"},{"external-id-type":"other-id","external-id-value":"7279939"},{"external-id-type":"isbn","external-id-value":"9781800412781","external-id-relationship":"part-of"},{"external-id-type":"issn","external-id-value":"2192-6255","external-id-relationship":"part-of"}]}}]}]}}}""",
      runId,
      "orcid-review",
      "orcid@0",
      1000000L,
      Some("2026-10-05")
    )
    val activities = records.collect { case EmittedRecord.Activity(value) => value }
    assert(activities.size == 1, records.map(_.json).mkString("\n"))
    val activity = activities.head
    assert(activity.observedDoi.contains("10.1000/kept.doi"))
    assert(activity.observedWorkId.contains("work:doi:10.1000/kept.doi"))
    val refs = activity.workReferences
    assert(refs.exists(ref => ref.externalIdType == "other-id" && ref.value == "24870415"))
    assert(refs.exists(ref => ref.externalIdType == "other-id" && ref.value == "7279939"))
    assert(refs.exists(ref => ref.value == "9781800412781" && ref.relationship.contains("part-of")))
    assert(refs.exists(ref => ref.externalIdType == "issn" && ref.relationship.contains("part-of")))
    assert(!records.exists(_.isInstanceOf[EmittedRecord.Work]))
    val sample = Path.of("datasets/samples/orcid/records.jsonl")
    if (Files.isRegularFile(sample)) {
      val parsed = JsonSources.parseLine(
        SourceType.Orcid,
        Files.readString(sample).linesIterator.find(_.nonEmpty).get,
        runId,
        "orcid-public-api-2026-10-05",
        "orcid@sample",
        1048576L,
        Some("2026-10-05")
      )
      val kept =
        parsed.collect { case EmittedRecord.Activity(value) => value }.flatMap(_.workReferences)
      assert(kept.exists(_.value == "24870415"))
      assert(kept.exists(_.value == "7279939"))
      assert(kept.exists(_.relationship.contains("part-of")))
    }
  }

  test("a truncated export part is not reused and the damaged bytes stay") {
    val dir = Files.createTempDirectory("review-damaged-reuse")
    val dblp = dir.resolve("works.xml")
    Files.writeString(
      dblp,
      """<?xml version="1.0"?><dblp><inproceedings key="conf/review/Reuse"><author>Ada</author><title>Reuse</title><year>2020</year></inproceedings></dblp>"""
    )
    val request = HadoopPrepPipeline.Request(
      config(dir.resolve("root"), 1048576),
      dblp.toString,
      empty(dir, "oa.jsonl").toString,
      empty(dir, "cr.jsonl").toString,
      empty(dir, "orcid.jsonl").toString,
      snapshots,
      freshRun("16161616-1616-4616-8616-161616161616"),
      retrievalDates = retrieval
    )
    val first = HadoopPrepPipeline.execute(request)
    assert(first.isRight, first.left.toOption.getOrElse(""))
    assert(!first.toOption.get.reused)
    val exportDir = first.toOption.get.directory.resolve("export")
    val walk = Files.walk(exportDir)
    val part =
      try
        walk
          .iterator()
          .asScala
          .find { path =>
            val name = path.getFileName.toString
            Files.isRegularFile(path) && name.startsWith("part") && Files.size(path) > 0
          }
          .getOrElse(fail(s"no export part under $exportDir"))
      finally walk.close()
    Files.write(part, Array.emptyByteArray)
    assert(Files.size(part) == 0L)
    val second = HadoopPrepPipeline.execute(request)
    assert(!second.exists(_.reused), s"reused damaged export: $second")
    assert(Files.size(part) == 0L)
  }

  test("Request.hadoopConf filesystem settings reach driver validation") {
    val conf = new Configuration()
    conf.set("fs.s3.impl", classOf[MemoryS3FileSystem].getName)
    conf.set("fs.s3.impl.disable.cache", "true")
    val request = HadoopPrepPipeline.Request(
      config(Files.createTempDirectory("review-caller-fs"), 1048576)
        .copy(outputRoot = "s3://phase4-bucket/out"),
      "missing-dblp.xml",
      "missing-openalex.jsonl",
      "missing-crossref.jsonl",
      "missing-orcid.jsonl",
      snapshots,
      freshRun("17171717-1717-4717-8717-171717171717"),
      retrievalDates = retrieval,
      hadoopConf = conf
    )
    val result = HadoopPrepPipeline.execute(request)
    assert(result.isLeft)
    val message = result.left.toOption.get
    assert(!message.contains("requires a Hadoop FileSystem implementation"), message)
    assert(message.contains("missing input"))
  }

  private def freshRun(uuid: String): String =
    StableIds.newRunId(java.util.UUID.fromString(uuid)).toOption.get

  private def runPipeline(
      dir: Path,
      dblp: Path,
      openAlex: Path,
      crossref: Path,
      orcid: Path
  ): HadoopPrepPipeline.Result = {
    val result = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config(dir.resolve("root"), 1048576),
        dblp.toString,
        openAlex.toString,
        crossref.toString,
        orcid.toString,
        snapshots,
        runId,
        retrievalDates = retrieval
      )
    )
    assert(result.isRight, result.left.toOption.getOrElse(""))
    result.toOption.get
  }

  private def config(root: Path, bytes: Long, sample: Int = 100): HadoopPrepConfig =
    HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      bytes,
      1048576,
      1,
      32,
      128,
      16,
      sample,
      root.toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )

  private def openAlex(json: String): Vector[EmittedRecord] =
    JsonSources.parseLine(
      SourceType.OpenAlex,
      json,
      runId,
      "openalex-review",
      "openalex@0",
      100000,
      Some("2026-10-05")
    )

  private def rejected(records: Vector[EmittedRecord], raw: String): Boolean =
    records.collect { case EmittedRecord.Rejected(value) => value }.exists { item =>
      item.reasonCode == RejectReasonCode.InvalidIdentifier &&
      item.diagnosticExcerpt.exists(_.contains(raw))
    }

  private def fileLocation(dir: Path): String = "file:" + dir.toAbsolutePath.normalize.toString

  private def writeExport(prefix: String, body: String): Path = {
    val root = Files.createTempDirectory(prefix)
    val exportDir = root.resolve("export")
    Files.createDirectories(exportDir)
    Files.writeString(exportDir.resolve("part.json"), body)
    root
  }

  private def empty(dir: Path, name: String): Path = {
    val path = dir.resolve(name)
    if (!Files.exists(path)) Files.writeString(path, "")
    path
  }

  private def emptyXml(dir: Path): Path = {
    val path = dir.resolve("empty.xml")
    if (!Files.exists(path)) Files.writeString(path, "<?xml version=\"1.0\"?><dblp></dblp>")
    path
  }

  private def partText(dir: Path): String =
    Files
      .list(dir)
      .iterator()
      .asScala
      .filter { path =>
        val name = path.getFileName.toString
        !name.startsWith("_") && !name.startsWith(".")
      }
      .map { path =>
        val name = path.getFileName.toString
        if (name.endsWith(".gz")) {
          val in = new java.util.zip.GZIPInputStream(Files.newInputStream(path))
          try new String(in.readAllBytes(), StandardCharsets.UTF_8)
          finally in.close()
        } else Files.readString(path)
      }
      .mkString("\n")
}

/** In-memory `s3` filesystem so a remote result can be read without AWS. */
final class MemoryS3FileSystem extends org.apache.hadoop.fs.FileSystem {
  import org.apache.hadoop.fs.{
    FSDataInputStream,
    FSDataOutputStream,
    FileStatus,
    Path => HPath,
    PositionedReadable,
    Seekable
  }
  import org.apache.hadoop.fs.permission.FsPermission
  import org.apache.hadoop.util.Progressable

  private var uri = java.net.URI.create("s3://phase4-bucket/")
  private var cwd = new HPath("s3://phase4-bucket/")

  override def getScheme: String = "s3"
  override def initialize(name: java.net.URI, conf: org.apache.hadoop.conf.Configuration): Unit = {
    super.initialize(name, conf)
    val host = Option(name.getHost).getOrElse("phase4-bucket")
    uri = java.net.URI.create(s"s3://$host/")
  }
  override def getUri: java.net.URI = uri
  override def open(path: HPath, bufferSize: Int): FSDataInputStream = {
    val bytes = MemoryS3FileSystem.file(MemoryS3FileSystem.key(path))
    if (bytes == null) throw new java.io.FileNotFoundException(path.toString)
    new FSDataInputStream(new MemoryBytes(bytes))
  }
  override def create(
      path: HPath,
      permission: FsPermission,
      overwrite: Boolean,
      bufferSize: Int,
      replication: Short,
      blockSize: Long,
      progress: Progressable
  ): FSDataOutputStream = {
    val key = MemoryS3FileSystem.key(path)
    if (!overwrite && MemoryS3FileSystem.files.containsKey(key))
      throw new java.io.IOException(s"exists $key")
    MemoryS3FileSystem.addParents(key)
    val buffer = new java.io.ByteArrayOutputStream
    new FSDataOutputStream(
      new java.io.FilterOutputStream(buffer) {
        override def close(): Unit = {
          MemoryS3FileSystem.files.put(key, buffer.toByteArray)
          super.close()
        }
      },
      new org.apache.hadoop.fs.FileSystem.Statistics(getScheme)
    )
  }
  override def append(path: HPath, bufferSize: Int, progress: Progressable): FSDataOutputStream =
    throw new UnsupportedOperationException(path.toString)
  override def rename(src: HPath, dst: HPath): Boolean = false
  override def delete(path: HPath, recursive: Boolean): Boolean = {
    val key = MemoryS3FileSystem.key(path)
    MemoryS3FileSystem.files.remove(key)
    MemoryS3FileSystem.dirs.remove(key)
    true
  }
  override def listStatus(path: HPath): Array[FileStatus] = {
    val key = MemoryS3FileSystem.key(path)
    if (MemoryS3FileSystem.files.containsKey(key)) Array(status(key, directory = false))
    else if (MemoryS3FileSystem.isDirectory(key))
      MemoryS3FileSystem
        .children(key)
        .map { child =>
          val childKey = s"$key/$child"
          status(childKey, directory = !MemoryS3FileSystem.files.containsKey(childKey))
        }
        .toArray
    else throw new java.io.FileNotFoundException(path.toString)
  }
  override def setWorkingDirectory(path: HPath): Unit = cwd = path
  override def getWorkingDirectory: HPath = cwd
  override def mkdirs(path: HPath, permission: FsPermission): Boolean = {
    MemoryS3FileSystem.addParents(MemoryS3FileSystem.key(path) + "/file")
    true
  }
  override def getFileStatus(path: HPath): FileStatus = {
    val key = MemoryS3FileSystem.key(path)
    if (MemoryS3FileSystem.files.containsKey(key)) status(key, directory = false)
    else if (MemoryS3FileSystem.isDirectory(key)) status(key, directory = true)
    else throw new java.io.FileNotFoundException(path.toString)
  }

  private def status(key: String, directory: Boolean): FileStatus = {
    val length = if (directory) 0L else MemoryS3FileSystem.files.get(key).length.toLong
    new FileStatus(length, directory, 1, 1024, 0L, new HPath(key))
  }
}

private final class MemoryBytes(bytes: Array[Byte])
    extends java.io.InputStream
    with org.apache.hadoop.fs.Seekable
    with org.apache.hadoop.fs.PositionedReadable {
  private var pos = 0
  override def read(): Int =
    if (pos >= bytes.length) -1
    else { val value = bytes(pos) & 0xff; pos += 1; value }
  override def read(buffer: Array[Byte], offset: Int, length: Int): Int =
    if (pos >= bytes.length) -1
    else {
      val count = math.min(length, bytes.length - pos)
      System.arraycopy(bytes, pos, buffer, offset, count)
      pos += count
      count
    }
  override def seek(target: Long): Unit = pos = target.toInt
  override def getPos: Long = pos.toLong
  override def seekToNewSource(targetPos: Long): Boolean = false
  override def read(position: Long, buffer: Array[Byte], offset: Int, length: Int): Int = {
    val start = position.toInt
    if (start >= bytes.length) -1
    else {
      val count = math.min(length, bytes.length - start)
      System.arraycopy(bytes, start, buffer, offset, count)
      count
    }
  }
  override def readFully(position: Long, buffer: Array[Byte], offset: Int, length: Int): Unit = {
    val count = read(position, buffer, offset, length)
    if (count < length) throw new java.io.EOFException()
  }
  override def readFully(position: Long, buffer: Array[Byte]): Unit =
    readFully(position, buffer, 0, buffer.length)
}

object MemoryS3FileSystem {
  val files = new java.util.concurrent.ConcurrentHashMap[String, Array[Byte]]
  val dirs = new java.util.concurrent.ConcurrentHashMap[String, java.lang.Boolean]
  def clear(): Unit = { files.clear(); dirs.clear() }
  def key(path: org.apache.hadoop.fs.Path): String = {
    val uri = path.toUri
    val host = Option(uri.getHost).orElse(Option(uri.getAuthority)).getOrElse("phase4-bucket")
    val raw = Option(uri.getPath).getOrElse("/")
    val collapsed = raw.split("/").filter(_.nonEmpty).mkString("/")
    s"s3://$host/$collapsed"
  }
  def addParents(fileKey: String): Unit = {
    val parts = fileKey.stripPrefix("s3://").split("/").filter(_.nonEmpty)
    var index = 1
    while (index < parts.length) {
      dirs.put("s3://" + parts.take(index).mkString("/"), java.lang.Boolean.TRUE)
      index += 1
    }
  }
  def file(key: String): Array[Byte] = files.get(key)
  def isDirectory(key: String): Boolean =
    dirs.containsKey(key) ||
      files.keySet.asScala.exists(_.startsWith(key + "/")) ||
      dirs.keySet.asScala.exists(_.startsWith(key + "/"))
  def children(dirKey: String): Vector[String] = {
    val prefix = dirKey + "/"
    val names = scala.collection.mutable.LinkedHashSet.empty[String]
    (files.keySet.asScala ++ dirs.keySet.asScala).foreach { key =>
      if (key.startsWith(prefix)) {
        val name = key.drop(prefix.length).takeWhile(_ != '/')
        if (name.nonEmpty) names += name
      }
    }
    names.toVector
  }
}
