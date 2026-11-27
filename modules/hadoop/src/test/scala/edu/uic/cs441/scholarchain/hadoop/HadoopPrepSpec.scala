package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import java.util.zip.GZIPOutputStream
import scala.jdk.CollectionConverters.*

class HadoopPrepSpec extends AnyFunSuite {
  try org.apache.log4j.Logger.getRootLogger.setLevel(org.apache.log4j.Level.WARN)
  catch { case _: Throwable => () }

  private val fixtureRetrieval = Map(
    SourceType.Dblp -> "2026-10-05",
    SourceType.OpenAlex -> "2026-10-05",
    SourceType.Crossref -> "2026-10-05",
    SourceType.Orcid -> "2026-10-05"
  )

  private val runId = StableIds
    .newRunId(java.util.UUID.fromString("11111111-1111-4111-8111-111111111111"))
    .toOption
    .get

  test("pair arithmetic is overflow-safe and ordered mention ids keep their ordinals") {
    assert(PrepLimits.pairCount(0) == 0L)
    assert(PrepLimits.pairCount(1) == 0L)
    assert(PrepLimits.pairCount(2) == 1L)
    assert(PrepLimits.pairCount(3) == 3L)
    assert(PrepLimits.pairCount(16) == 120L)
    val wide = PrepLimits.pairCount(Int.MaxValue)
    assert(wide == Int.MaxValue.toLong * (Int.MaxValue.toLong - 1) / 2)
    val second = mention("series/sapere/BerkeleyR13", 2, "Ann")
    val tenth = mention("series/sapere/BerkeleyR13", 10, "Ann")
    val (left, right) = DerivedRecords.orderedPair(tenth, second)
    assert(left.mentionId.compareTo(right.mentionId) < 0)
    assert(left.ordinal == 10)
    assert(right.ordinal == 2)
  }

  test("DBLP preserves markup, unicode, repeated names, and optional year") {
    val xml = record(
      "series/sapere/Markup1",
      """<author>Ann Lee</author><author>Ann Lee</author><author>北 京</author>""",
      "<title>Machine <i>Mentality</i> 机器学习?</title><year>2011</year><booktitle>PT-AI</booktitle>"
    )
    val parsed = DblpRecords.parse(
      xml,
      DblpXml.Header(Map.empty, None),
      runId,
      "dblp-test",
      "markup",
      100000,
      100000
    )
    val work = parsed.collect { case EmittedRecord.Work(value) => value }.head
    assert(work.title == "Machine <i>Mentality</i> 机器学习?")
    assert(work.authors.map(_.nameText) == Vector("Ann Lee", "Ann Lee", "北 京"))
    assert(work.authors.map(_.ordinal) == Vector(1, 2, 3))
    assert(work.authors.map(_.mentionId).distinct.size == 3)
    val noYear =
      record("series/sapere/NoYear1", "<author>Ada</author>", "<title>Optional year</title>")
    val optional = DblpRecords.parse(
      noYear,
      DblpXml.Header(Map.empty, None),
      runId,
      "dblp-test",
      "noyear",
      100000,
      100000
    )
    assert(optional.collect { case EmittedRecord.Work(value) => value }.head.year.isEmpty)
  }

  test("missing title, unsupported element, malformed identifier, and unsafe entities reject") {
    val missing = record("series/sapere/NoTitle1", "<author>Ada</author>", "<pages>1-2</pages>")
    assert(reason(missing) == RejectReasonCode.MissingRequiredField)
    val unsupported = "<www key=\"homepages/x\"><author>Ada</author><title>Home</title></www>"
    assert(reason(unsupported) == RejectReasonCode.UnsupportedRecordType)
    val badOrcid = record(
      "series/sapere/BadOrcid1",
      """<author orcid="not-an-orcid">Ada</author>""",
      "<title>Bad id</title>"
    )
    assert(reason(badOrcid) == RejectReasonCode.InvalidIdentifier)
    val unsafe = DblpRecords.parse(
      record("series/sapere/Safe1", "<author>Ada</author>", "<title>T</title>"),
      DblpXml.Header(Map.empty, Some("external entity")),
      runId,
      "dblp-test",
      "unsafe",
      100000,
      100000
    )
    assert(
      unsafe
        .collect { case EmittedRecord.Rejected(value) => value.reasonCode }
        .contains(RejectReasonCode.UnsafeEntity)
    )
    val bomb = DblpXml.expand("start &b; end", Map("a" -> "xxxx", "b" -> "&a;&a;&a;&a;&a;"), 10)
    assert(bomb == Left(RejectReasonCode.OversizeXmlEntityExpansion))
    val evil = DblpXml.header("<!DOCTYPE dblp SYSTEM \"http://evil.example/x.dtd\">")
    assert(evil.unsafe.nonEmpty)
    val emptySubset = DblpXml.header("<!DOCTYPE dblp []>")
    assert(emptySubset.unsafe.isEmpty)
    assert(emptySubset.entities.isEmpty)
    val dated = DblpXml.header("<!DOCTYPE dblp SYSTEM \"dblp-2023-06-28.dtd\">")
    val plain = DblpXml.header("<!DOCTYPE dblp SYSTEM \"dblp.dtd\">")
    assert(dated.unsafe.isEmpty)
    assert(plain.unsafe.isEmpty)
    assert(dated.entities("eacute") == "\u00e9")
    assert(!dated.entities.contains("amp"))
    val overridden = DblpXml.header(
      "<!DOCTYPE dblp SYSTEM \"dblp.dtd\" [<!ENTITY eacute \"XYZ\">]>"
    )
    assert(overridden.unsafe.isEmpty)
    assert(overridden.entities("eacute") == "XYZ")
    assert(
      DblpXml
        .header("<!DOCTYPE dblp SYSTEM \"dblp.dtd\" [<!ENTITY ext SYSTEM \"secret\">]>")
        .unsafe
        .nonEmpty
    )
    assert(
      DblpXml.header("<!DOCTYPE dblp SYSTEM \"https://evil.example/dblp.dtd\">").unsafe.nonEmpty
    )
    assert(DblpXml.header("<!DOCTYPE dblp SYSTEM \"file:///etc/passwd\">").unsafe.nonEmpty)
    assert(DblpXml.header("<!DOCTYPE dblp SYSTEM \"/etc/passwd\">").unsafe.nonEmpty)
    assert(DblpXml.header("<!DOCTYPE dblp SYSTEM \"../secret.dtd\">").unsafe.nonEmpty)
    assert(DblpXml.header("<!DOCTYPE dblp SYSTEM \"dblp.dtd/../../x\">").unsafe.nonEmpty)
    assert(DblpXml.header("<!DOCTYPE dblp SYSTEM \"dblp-2023-6-28.dtd\">").unsafe.nonEmpty)
    val accented = DblpRecords.parse(
      record("conf/review/Eacute1", "<author>Ada</author>", "<title>Caf&eacute;</title>"),
      dated,
      runId,
      "dblp-test",
      "eacute",
      100000,
      100000
    )
    val accentedWork = accented.collect { case EmittedRecord.Work(value) => value }
    assert(accentedWork.size == 1, accented.map(_.json).mkString("\n"))
    assert(accentedWork.head.title == "Caf\u00e9")
    assert(!accented.exists {
      case EmittedRecord.Rejected(value) => value.reasonCode == RejectReasonCode.UnsafeEntity
      case _                             => false
    })
  }

  test("-libjars is parsed into tmpjars and kept on the job configuration") {
    val file = Files.createTempFile("scholarchain-libjars", ".jar")
    Files.write(file, Array[Byte](1, 2, 3))
    val launch = HadoopPrepMain.parseLaunch(Array("-libjars", file.toString, "--once"))
    assert(launch.args.toSeq == Seq("--once"))
    val tmpjars = launch.configuration.get("tmpjars")
    assert(tmpjars != null, "tmpjars was dropped")
    assert(
      tmpjars.contains(file.toString) || tmpjars.contains(file.toRealPath().toString),
      tmpjars
    )
    val parent = new org.apache.hadoop.conf.Configuration(false)
    parent.set("tmpjars", file.toString)
    val snapshots = HadoopPrepPipeline.DefaultSnapshots
    val local = PrepJobs.configuration(
      prepConfig(file.getParent, 16, 32, 128),
      runId,
      snapshots,
      parent
    )
    assert(local.get("tmpjars") == file.toString)
    assert(local.get("mapreduce.framework.name") == "local")
    val cluster = PrepJobs.configuration(
      prepConfig(file.getParent, 16, 32, 128).copy(executionMode = HadoopExecutionMode.Cluster),
      runId,
      snapshots,
      parent
    )
    assert(cluster.get("tmpjars") == file.toString)
    assert(cluster.get("mapreduce.framework.name") == "yarn")
    val bare = PrepJobs.configuration(
      prepConfig(file.getParent, 16, 32, 128),
      runId,
      snapshots
    )
    assert(bare.get("mapreduce.framework.name") == "local")
  }

  test("remote config URIs are rejected before a local path is opened") {
    val message = HadoopPrepMain.requireLocalConfig("s3://bucket/prep.json")
    assert(message.isLeft)
    assert(message.swap.toOption.get.contains("local regular file"))
    assert(HadoopPrepMain.requireLocalConfig("s3a://bucket/prep.json").isLeft)
    assert(HadoopPrepMain.requireLocalConfig("s3n://bucket/prep.json").isLeft)
    assert(HadoopPrepMain.requireLocalConfig("hdfs://namenode/prep.json").isLeft)
    assert(HadoopPrepMain.requireLocalConfig(HadoopPrepMain.DefaultConfigPath).isRight)
  }

  test("comments and CDATA do not create titles or authors") {
    val header = DblpXml.header("<!DOCTYPE dblp []>")
    val commented =
      """<article key="conf/review/Comment1">
        |  <!-- <title>Fake</title><author>Fake Author</author> -->
        |  <title>Real</title><author>Real Author</author>
        |</article>""".stripMargin
    val cdata =
      """<article key="conf/review/Cdata1">
        |  <![CDATA[<title>Fake</title><author>Fake Author</author>]]>
        |  <title>Real</title><author>Real Author</author>
        |</article>""".stripMargin
    def parsed(xml: String, locator: String) =
      DblpRecords.parse(xml, header, runId, "dblp-test", locator, 100000, 100000)
    Seq(commented -> "comment", cdata -> "cdata").foreach { case (xml, locator) =>
      val records = parsed(xml, locator)
      val works = records.collect { case EmittedRecord.Work(value) => value }
      assert(works.size == 1, records.map(_.json).mkString("\n"))
      assert(works.head.title == "Real")
      assert(works.head.authors.map(_.nameText) == Vector("Real Author"))
      assert(!records.map(_.json).mkString("\n").contains("Fake"))
    }
    assert(
      DblpXml.children("<title>A<![CDATA[ B <author>No</author>]]>C</title>", "title") ==
        Vector("A B <author>No</author>C")
    )
    assert(
      DblpXml.children(
        """<title>A<!-- <title>Fake</title> -->B</title>""",
        "title"
      ) == Vector("AB")
    )
  }

  test("oversize nested XML drains without retaining every tag name") {
    val nested = 10000
    val xml = "<i>" * nested + "</i>" * nested
    val stream =
      new PosStream(new java.io.ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8)))
    assert(stream.read() == '<'.toInt)
    assert(stream.read() == 'i'.toInt)
    val element = DblpSplitReader.readElement(stream, "i", 64L)
    assert(element.oversize)
    assert(!element.unterminated)
    assert(element.storedNameHighWater <= DblpSplitReader.MaxStoredNestingDepth)
    assert(element.storedNameHighWater >= 1)
    assert(element.xml.getBytes(StandardCharsets.UTF_8).length <= 256)

    val deep = "<i>" * 80 + "</i>" * 80
    val deepStream =
      new PosStream(new java.io.ByteArrayInputStream(deep.getBytes(StandardCharsets.UTF_8)))
    assert(deepStream.read() == '<'.toInt)
    assert(deepStream.read() == 'i'.toInt)
    val capped = DblpSplitReader.readElement(deepStream, "i", 1000000L)
    assert(capped.oversize)
    assert(!capped.unterminated)
    assert(capped.storedNameHighWater <= DblpSplitReader.MaxStoredNestingDepth)
    assert(capped.xml.getBytes(StandardCharsets.UTF_8).length <= 256)

    val longName = "n" * 4000
    val body = "><" + longName + ">x</" + longName + "></article>"
    val named = DblpSplitReader.readElement(
      new PosStream(new java.io.ByteArrayInputStream(body.getBytes(StandardCharsets.UTF_8))),
      "article",
      1000000L
    )
    assert(named.oversize)
    assert(!named.unterminated)
    assert(named.xml.getBytes(StandardCharsets.UTF_8).length <= 256)
    assert(!named.xml.contains(longName))
  }

  test("split edges and gzip keep complete records") {
    val body = (1 to 3)
      .map { n =>
        record(
          s"conf/split/Paper$n",
          s"<author>Author $n</author>",
          s"<title>Split <i>title</i> $n</title><year>2020</year>"
        )
      }
      .mkString("\n")
    val xml = s"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE dblp []>
<dblp>
$body
</dblp>
"""
    val dir = Files.createTempDirectory("dblp-split")
    val plain = dir.resolve("records.xml")
    Files.writeString(plain, xml)
    val gzip = dir.resolve("records.xml.gz")
    val out = new GZIPOutputStream(Files.newOutputStream(gzip))
    out.write(xml.getBytes(StandardCharsets.UTF_8))
    out.close()
    val plainWorks = runDblp(plain, dir.resolve("plain"), Some(80L))
    assert(
      plainWorks.map(_.title).sorted == Vector(
        "Split <i>title</i> 1",
        "Split <i>title</i> 2",
        "Split <i>title</i> 3"
      )
    )
    val gzipWorks = runDblp(gzip, dir.resolve("gzip"), None)
    assert(gzipWorks.map(_.sourceRecordId).sorted == plainWorks.map(_.sourceRecordId).sorted)
  }

  test("duplicate, conflict, shared DOI, ORCID activity, teams, and text refs") {
    val dir = Files.createTempDirectory("prep-pipeline")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?>
<!DOCTYPE dblp []>
<dblp>
${record(
          "conf/team/Solo1",
          "<author>Only One</author>",
          "<title>Solo paper</title><year>2020</year>"
        )}
${record(
          "conf/team/Pair1",
          "<author>Ann Lee</author><author>Bea Kim</author>",
          "<title>Two authors</title><year>2021</year>"
        )}
${record(
          "conf/team/Trio1",
          "<author>Ann Lee</author><author>Ann Lee</author><author>北 京</author>",
          "<title>Repeated <i>names</i></title><year>2022</year><ee>https://doi.org/10.1000/shared.doi</ee><booktitle>PT-AI</booktitle>"
        )}
</dblp>
"""
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      Vector(
        openAlexWork("W2741948091", "10.1000/shared.doi", "Shared title", Some(abstractIndex)),
        openAlexWork("W2741948091", "10.1000/shared.doi", "Shared title", Some(abstractIndex)),
        openAlexWork("W2741948092", "10.1000/conflict.doi", "First title", None),
        openAlexWork("W2741948092", "10.1000/conflict.doi", "Other title", None)
      ).mkString("\n") + "\n{"
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      crossrefWork(
        "10.1000/shared.doi",
        "Shared title"
      ) + "\n" + """{"message":{"DOI":"10.1000/notitle"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, orcidRecord)
    val output = dir.resolve("out")
    val result = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        prepConfig(output, team = 16, block = 32, pairs = 128),
        dblp.toString,
        openAlex.toString,
        crossref.toString,
        orcid.toString,
        Map(
          SourceType.Dblp -> "dblp-test",
          SourceType.OpenAlex -> "openalex-test",
          SourceType.Crossref -> "crossref-test",
          SourceType.Orcid -> "orcid-test"
        ),
        runId,
        retrievalDates = fixtureRetrieval
      )
    )
    assert(result.isRight, result.left.toOption.getOrElse(""))
    val run = result.toOption.get
    val lines = LogicalRecords.lines(run.directory.resolve("export"))
    assert(lines.exists(_.contains("DUPLICATE_IDENTICAL_OBSERVATION")))
    assert(lines.exists(_.contains("CONFLICTING_OBSERVATION")))
    assert(lines.exists(_.contains("MISSING_REQUIRED_FIELD")))
    assert(lines.exists(_.contains("MALFORMED_RECORD")))
    val candidates = lines
      .filter(_.contains("\"candidateId\""))
      .flatMap(line => CoreJson.parse[MatchCandidate](line).toOption)
    assert(candidates.exists { candidate =>
      val sources = Set(candidate.left.source, candidate.right.source)
      sources == Set(SourceType.Dblp, SourceType.Crossref)
    })
    assert(!lines.exists(_.contains("RESOLVES_TO")))
    assert(!lines.exists(_.contains("COAUTHORED_WITH")))
    assert(!lines.exists(_.contains("\"decision\"")))
    val teams = lines
      .filter(line => line.contains("\"teamSize\"") && line.contains("\"memberMentionIds\""))
      .flatMap(CoreJson.parse[PublicationTeam](_).toOption)
    assert(teams.map(_.teamSize).toSet.intersect(Set(1, 2, 3)).size == 3)
    val profiles = lines.flatMap(line => CoreJson.parse[OrcidProfileRecord](line).toOption)
    assert(profiles.nonEmpty)
    val activities = lines.flatMap(line => CoreJson.parse[OrcidActivityRecord](line).toOption)
    assert(activities.exists(_.activityKind == OrcidActivityKind.Work))
    assert(activities.exists(_.ror.nonEmpty))
    assert(activities.exists(_.ringgold.nonEmpty))
    assert(activities.forall(_.activityKind != OrcidActivityKind.Work || activities.nonEmpty))
    val works = lines
      .flatMap(line => CoreJson.parse[WorkRecord](line).toOption)
      .filter(_.source != SourceType.Orcid)
    assert(works.forall(_.source != SourceType.Orcid))
    val docs = lines.flatMap(line => CoreJson.parse[EmittedTextDocument](line).toOption)
    assert(TextRefs.unresolved(works, docs).isEmpty)
    assert(docs.exists(_.textId.startsWith("chunk:")))
    assert(run.largestTeam >= 3)
    assert(run.largestBlock >= 2)
    assert(run.counters(PrepCounters.EmittedPair) >= 1)
  }

  test("block and team limits reject the whole group") {
    val dir = Files.createTempDirectory("prep-limits")
    val dblp = dir.resolve("dblp.xml")
    val authors = (1 to 4).map(n => s"<author>Person $n</author>").mkString
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?><!DOCTYPE dblp []><dblp>
${record(
          "conf/limits/Big1",
          authors,
          "<title>Big team</title><year>2020</year><ee>https://doi.org/10.1000/limits.doi</ee>"
        )}
</dblp>"""
    )
    val shared = (1 to 3).map { n =>
      val source = if (n == 1) "openalex" else if (n == 2) "crossref" else "dblp-json"
      s"""{"id":"https://openalex.org/W300000000$n","title":"Limits $n","doi":"https://doi.org/10.1000/block.doi","authorships":[{"raw_author_name":"A$n","author":{"display_name":"A$n"}}]}"""
    }
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(openAlex, shared.mkString("\n"))
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(crossref, crossrefWork("10.1000/block.doi", "Block"))
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val oversizeTeam = HadoopPrepPipeline.execute(
      request(
        dir.resolve("team-out"),
        dblp,
        openAlex,
        crossref,
        orcid,
        team = 3,
        block = 32,
        pairs = 128,
        "22222222-2222-4222-8222-222222222222"
      )
    )
    assert(oversizeTeam.isRight)
    val teamLines = LogicalRecords.lines(oversizeTeam.toOption.get.directory.resolve("export"))
    assert(teamLines.exists(_.contains("OVERSIZE_TEAM")))
    assert(!teamLines.flatMap(CoreJson.parse[PublicationTeam](_).toOption).exists(_.teamSize == 4))
    // J08 accounts for the same team: one pair-step counter and one COAUTHOR_PAIR reject, no pairs.
    val teamResult = oversizeTeam.toOption.get
    assert(teamResult.counters(PrepCounters.OversizeTeam) == 1L)
    assert(teamResult.counters(PrepCounters.OversizeTeamPairStep) == 1L)
    val pairStepRejects = teamLines
      .flatMap(CoreJson.parse[RejectRecord](_).toOption)
      .filter(_.stage == PreparationStage.CoauthorPair)
    assert(pairStepRejects.size == 1)
    assert(pairStepRejects.head.reasonCode == RejectReasonCode.OversizeTeam)
    assert(pairStepRejects.head.diagnosticExcerpt.exists(_.contains("team 4 exceeds 3")))
    assert(teamLines.flatMap(CoreJson.parse[CoauthorPairCandidate](_).toOption).isEmpty)
    val oversizeBlock = HadoopPrepPipeline.execute(
      request(
        dir.resolve("block-out"),
        dblp,
        openAlex,
        crossref,
        orcid,
        team = 16,
        block = 2,
        pairs = 100,
        "33333333-3333-4333-8333-333333333333"
      )
    )
    assert(oversizeBlock.isRight)
    val blockLines = LogicalRecords.lines(oversizeBlock.toOption.get.directory.resolve("export"))
    assert(blockLines.exists(_.contains("OVERSIZE_BLOCK")))
    val oversizePairs = HadoopPrepPipeline.execute(
      request(
        dir.resolve("pair-out"),
        dblp,
        openAlex,
        crossref,
        orcid,
        team = 16,
        block = 32,
        pairs = 2,
        "44444444-4444-4444-8444-444444444444"
      )
    )
    assert(oversizePairs.isRight)
    val pairLines = LogicalRecords.lines(oversizePairs.toOption.get.directory.resolve("export"))
    assert(pairLines.exists(_.contains("OVERSIZE_CANDIDATE_PAIRS")))
    assert(oversizePairs.toOption.get.largestPairExpansion >= 6)
  }

  test("failed run leaves no completion marker and a matching marker can be reused") {
    val dir = Files.createTempDirectory("prep-reuse")
    val dirty = dir.resolve("dirty")
    Files.createDirectories(dirty)
    Files.writeString(dirty.resolve("partial.txt"), "partial")
    val checksums = Map(SourceType.Dblp.wire -> "abc")
    val snapshots = Map(SourceType.Dblp.wire -> "dblp-test")
    val retrievals = Map(SourceType.Dblp.wire -> "2026-10-05")
    val partition =
      s"snapshot=dblp-test/run=${runId.stripPrefix("run:")}/work"
    def identity(fingerprint: String, parts: Vector[String]) =
      OutputIdentity(runId, fingerprint, checksums, snapshots, retrievals, parts)
    val claim = OutputGate.claim(dirty, identity("f" * 64, Vector.empty))
    assert(claim.isInstanceOf[OutputGate.Refuse])
    assert(Files.readString(dirty.resolve("partial.txt")) == "partial")
    val fresh = dir.resolve("fresh")
    assert(OutputGate.claim(fresh, identity("a" * 64, Vector.empty)) == OutputGate.Proceed)
    Files.writeString(fresh.resolve("partial.txt"), "partial")
    assert(
      OutputGate.claim(fresh, identity("a" * 64, Vector.empty)).isInstanceOf[OutputGate.Refuse]
    )
    val exportDir = fresh.resolve("export").resolve(partition)
    Files.createDirectories(exportDir)
    Files.writeString(exportDir.resolve("part-m-00000"), "{}\n")
    val manifest = RunManifest(
      runId,
      SchemaVersions.domain,
      "hadoop-prep",
      Vector(DatasetSnapshotRef(SourceType.Dblp, "dblp-test", Some("2026-10-05"))),
      SchemaVersions.hadoopPrep,
      "a" * 64,
      ProvenanceFactory(SourceType.ScholarChain, runId, None, PrepLimits.DerivedSnapshot, runId)
    )
    Files.writeString(fresh.resolve("run-manifest.json"), CoreJson.pretty(manifest))
    OutputGate.write(fresh, identity("a" * 64, Vector(partition)))
    assert(OutputGate.claim(fresh, identity("a" * 64, Vector.empty)) == OutputGate.Reuse)
    val changed =
      identity("a" * 64, Vector.empty).copy(snapshots = Map(SourceType.Dblp.wire -> "dblp-other"))
    assert(OutputGate.claim(fresh, changed).isInstanceOf[OutputGate.Refuse])
    Files.delete(exportDir.resolve("part-m-00000"))
    assert(
      OutputGate.claim(fresh, identity("a" * 64, Vector.empty)).isInstanceOf[OutputGate.Refuse]
    )
    val inputs = sampleInputs(dir)
    val output = dir.resolve("runs")
    val config = prepConfig(output, 16, 32, 128)
    val firstId = "55555555-5555-4555-8555-555555555555"
    val first = HadoopPrepPipeline.execute(fullRequest(config, inputs, firstId))
    assert(first.isRight)
    val failed = HadoopPrepPipeline.execute(
      fullRequest(config, inputs, "66666666-6666-4666-8666-666666666666").copy(failJob =
        Some("J01")
      )
    )
    assert(failed.isLeft)
    val failedDir =
      output.resolve(HadoopPrepPipeline.directoryName("run:66666666-6666-4666-8666-666666666666"))
    assert(!Files.exists(failedDir.resolve(OutputGate.MarkerName)))
    val again = HadoopPrepPipeline.execute(fullRequest(config, inputs, firstId))
    assert(again.toOption.exists(_.reused))
  }

  test("provenance mismatch is rejected and a dangling text ref does not resolve") {
    val work = DblpRecords
      .parse(
        record(
          "series/sapere/Prov1",
          "<author>Ada</author>",
          "<title>Provenance</title><year>2020</year>"
        ),
        DblpXml.Header(Map.empty, None),
        runId,
        "dblp-test",
        "prov",
        100000,
        100000
      )
      .collect { case EmittedRecord.Work(value) => value }
      .head
    val mismatched = work.provenance.copy(sourceRecordId = "other")
    assert(
      DerivedRecords
        .provenanceGate(mismatched, work.provenance)
        .contains(RejectReasonCode.ProvenanceMismatch)
    )
    val doc = EmittedTextDocument(
      "chunk:" + ("ab" * 32),
      SchemaVersions.domain,
      EmittedTextDocument.abstractDocumentType,
      work.workId,
      work.provenance.datasetSnapshot,
      Some(0),
      "not the hashed text",
      work.provenance
    )
    assert(
      TextRefs.unresolved(Seq(work.copy(abstractTextRef = Some(doc.textId))), Seq(doc)).nonEmpty
    )
  }

  test("UTF-8 title bytes survive the DBLP record reader") {
    val dir = Files.createTempDirectory("dblp-utf8")
    val title = "机器学习"
    val xml = s"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE dblp []>
<dblp>
${record("conf/utf/Learn1", "<author>Ada</author>", s"<title>$title</title><year>2020</year>")}
</dblp>
"""
    val input = dir.resolve("records.xml")
    Files.write(input, xml.getBytes(StandardCharsets.UTF_8))
    val works = runDblp(input, dir.resolve("out"), None)
    assert(works.map(_.title) == Vector(title))
  }

  test("identical payloads survive once and conflicting payloads are not exported") {
    val dir = Files.createTempDirectory("prep-dedupe")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?><!DOCTYPE dblp []><dblp>
${record("conf/dedupe/One1", "<author>Ada</author>", "<title>Local</title><year>2020</year>")}
</dblp>"""
    )
    val same = openAlexWork("W2741948091", "10.1000/same.doi", "Same title", None)
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      Vector(
        same,
        same,
        openAlexWork("W2741948092", "10.1000/only-left.doi", "Left title", None),
        openAlexWork("W2741948092", "10.1000/only-right.doi", "Right title", None)
      ).mkString("\n")
    )
    Files.writeString(dir.resolve("crossref.jsonl"), crossrefWork("10.1000/other.doi", "Other"))
    Files.writeString(
      dir.resolve("orcid.jsonl"),
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}"""
    )
    val ran = HadoopPrepPipeline.execute(
      request(
        dir.resolve("out"),
        dblp,
        openAlex,
        dir.resolve("crossref.jsonl"),
        dir.resolve("orcid.jsonl"),
        16,
        32,
        128,
        "77777777-7777-4777-8777-777777777777"
      )
    )
    assert(ran.isRight, ran.left.toOption.getOrElse(""))
    val lines = LogicalRecords.lines(ran.toOption.get.directory.resolve("export"))
    val works = lines.flatMap(line => CoreJson.parse[WorkRecord](line).toOption)
    assert(works.count(_.sourceRecordId == "W2741948091") == 1)
    assert(!works.exists(_.sourceRecordId == "W2741948092"))
    assert(!lines.exists(_.contains("only-left")))
    assert(!lines.exists(_.contains("only-right")))
    assert(!lines.exists(_.contains("Left title")))
    assert(!lines.exists(_.contains("Right title")))
    assert(lines.exists(_.contains("DUPLICATE_IDENTICAL_OBSERVATION")))
    assert(lines.exists(_.contains("CONFLICTING_OBSERVATION")))
  }

  test("largestPairExpansion counts coauthor teams and not block pairs") {
    val dir = Files.createTempDirectory("prep-pairs")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?><!DOCTYPE dblp []><dblp>
${record("conf/pairs/Solo1", "<author>Ada</author>", "<title>Solo</title><year>2020</year>")}
</dblp>"""
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      (1 to 4)
        .map(n => openAlexWork(s"W300000000$n", "10.1000/block.doi", s"Block $n", None))
        .mkString("\n")
    )
    Files.writeString(dir.resolve("crossref.jsonl"), crossrefWork("10.1000/other.doi", "Other"))
    Files.writeString(
      dir.resolve("orcid.jsonl"),
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}"""
    )
    val ran = HadoopPrepPipeline.execute(
      request(
        dir.resolve("out"),
        dblp,
        openAlex,
        dir.resolve("crossref.jsonl"),
        dir.resolve("orcid.jsonl"),
        16,
        32,
        128,
        "88888888-8888-4888-8888-888888888888"
      )
    )
    assert(ran.isRight, ran.left.toOption.getOrElse(""))
    val value = ran.toOption.get
    assert(value.largestBlock >= 4)
    assert(value.largestPairExpansion == 0)
  }

  test("one institution-bearing work exports the work and the institution") {
    val lines = runObservation(
      Vector(institutionWork("W2741948091", "10.1000/inst.doi", "Held", "T12090", "Language")),
      "99999991-9999-4999-8999-999999999991"
    )
    val works = lines.flatMap(line => CoreJson.parse[WorkRecord](line).toOption)
    val institutions = lines.flatMap(line => CoreJson.parse[Institution](line).toOption)
    assert(works.count(_.sourceRecordId == "W2741948091") == 1)
    assert(institutions.exists(_.institutionId == "institution:ror:02catss52"))
    assert(!lines.exists(_.contains("CONFLICTING_OBSERVATION")))
  }

  test("two identical institution-bearing observations export one work and one institution") {
    val line = institutionWork("W2741948091", "10.1000/inst.doi", "Held", "T12090", "Language")
    val lines = runObservation(Vector(line, line), "99999992-9999-4999-8999-999999999992")
    val works = lines.flatMap(line => CoreJson.parse[WorkRecord](line).toOption)
    val institutions = lines.flatMap(line => CoreJson.parse[Institution](line).toOption)
    assert(works.count(_.sourceRecordId == "W2741948091") == 1)
    assert(institutions.count(_.institutionId == "institution:ror:02catss52") == 1)
    assert(lines.exists(_.contains("DUPLICATE_IDENTICAL_OBSERVATION")))
  }

  test("different topics on the same observation key are a conflict and not an edge") {
    val lines = runObservation(
      Vector(
        institutionWork("W2741948091", "10.1000/inst.doi", "Held", "T12091", "OnlyLeftTopic"),
        institutionWork("W2741948091", "10.1000/inst.doi", "Held", "T12092", "OnlyRightTopic")
      ),
      "99999993-9999-4999-8999-999999999993"
    )
    val works = lines.flatMap(line => CoreJson.parse[WorkRecord](line).toOption)
    assert(!works.exists(_.sourceRecordId == "W2741948091"))
    assert(lines.exists(_.contains("CONFLICTING_OBSERVATION")))
    assert(!lines.exists(_.contains("HAS_TOPIC")))
    assert(!lines.exists(_.contains("OnlyLeftTopic")))
    assert(!lines.exists(_.contains("OnlyRightTopic")))
  }

  test("s3 output root is not created as a local directory") {
    val dir = Files.createTempDirectory("s3-root")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(dblp, "<dblp></dblp>")
    val empty = dir.resolve("empty.jsonl")
    Files.writeString(empty, "")
    val localRoot = dir.resolve("local-out")
    val overridden = HadoopPrepMain.withOutputRoot(
      prepConfig(localRoot, 16, 32, 128),
      Array("--output-root", "s3://phase4-bucket/out")
    )
    assert(overridden.outputRoot == "s3://phase4-bucket/out")
    val ran = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        overridden,
        dblp.toString,
        empty.toString,
        empty.toString,
        empty.toString,
        HadoopPrepPipeline.DefaultSnapshots,
        runId
      )
    )
    assert(ran.isLeft)
    assert(ran.left.exists(message => message.contains("s3://phase4-bucket/out")))
    assert(!Files.exists(Path.of("s3:")))
    assert(!Files.exists(Path.of("s3:/phase4-bucket")))
    assert(!Files.exists(localRoot))
    val top = Files.list(Path.of("").toAbsolutePath).iterator().asScala.map(_.getFileName.toString)
    assert(!top.exists(_.contains("s3:")))
  }

  private def reason(xml: String): RejectReasonCode =
    DblpRecords
      .parse(xml, DblpXml.Header(Map.empty, None), runId, "dblp-test", "case", 100000, 100000)
      .collect { case EmittedRecord.Rejected(value) => value.reasonCode }
      .head

  private def record(key: String, authors: String, rest: String): String =
    s"""<inproceedings key="$key">$authors$rest</inproceedings>"""

  private def mention(key: String, ordinal: Int, name: String): AuthorMention = {
    val provenance = ProvenanceFactory(SourceType.Dblp, key, None, "dblp-test", runId)
    AuthorMention(
      StableIds.mentionId(SourceType.Dblp, key, ordinal),
      SchemaVersions.domain,
      SourceType.Dblp,
      key,
      ordinal,
      name,
      TextNorm.personName(name),
      None,
      None,
      MentionIdentityStatus.NameOnlyUnconfirmed,
      None,
      "fixture",
      provenance
    )
  }

  private def runDblp(input: Path, output: Path, split: Option[Long]): Vector[WorkRecord] = {
    val conf = PrepJobs.configuration(
      prepConfig(output.getParent, 16, 32, 128),
      runId,
      HadoopPrepPipeline.DefaultSnapshots
    )
    val job = PrepJobs.dblp(conf, input.toString, output, split)
    PrepJobs.run("J01", job)
    Files
      .list(output)
      .iterator()
      .asScala
      .filter(_.getFileName.toString.startsWith("part"))
      .flatMap { path =>
        Files.readAllLines(path).asScala.flatMap { line =>
          Lines.unpack(line).toVector.flatMap { case (kind, json) =>
            if (kind == Kinds.Work) CoreJson.parse[WorkRecord](json).toOption else None
          }
        }
      }
      .toVector
  }

  private def prepConfig(root: Path, team: Int, block: Int, pairs: Int): HadoopPrepConfig =
    HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      block,
      pairs,
      team,
      100,
      root.toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )

  private def request(
      root: Path,
      dblp: Path,
      openAlex: Path,
      crossref: Path,
      orcid: Path,
      team: Int,
      block: Int,
      pairs: Int,
      uuid: String
  ): HadoopPrepPipeline.Request =
    HadoopPrepPipeline.Request(
      prepConfig(root, team, block, pairs),
      dblp.toString,
      openAlex.toString,
      crossref.toString,
      orcid.toString,
      Map(
        SourceType.Dblp -> "dblp-test",
        SourceType.OpenAlex -> "openalex-test",
        SourceType.Crossref -> "crossref-test",
        SourceType.Orcid -> "orcid-test"
      ),
      StableIds.newRunId(java.util.UUID.fromString(uuid)).toOption.get,
      retrievalDates = fixtureRetrieval
    )

  private def sampleInputs(dir: Path): (Path, Path, Path, Path) = {
    val dblp = dir.resolve("one.xml")
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?><!DOCTYPE dblp []><dblp>${record(
          "conf/reuse/One1",
          "<author>Ada</author>",
          "<title>Reuse</title>"
        )}</dblp>"""
    )
    val openAlex = dir.resolve("one-open.jsonl")
    Files.writeString(openAlex, openAlexWork("W2741948093", "10.1000/reuse.doi", "Reuse", None))
    val crossref = dir.resolve("one-cross.jsonl")
    Files.writeString(crossref, crossrefWork("10.1000/reuse.doi", "Reuse"))
    val orcid = dir.resolve("one-orcid.jsonl")
    Files.writeString(
      orcid,
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"},"person":{"name":{"credit-name":{"value":"Ada Lovelace"}}}}"""
    )
    (dblp, openAlex, crossref, orcid)
  }

  private def fullRequest(
      config: HadoopPrepConfig,
      inputs: (Path, Path, Path, Path),
      uuid: String
  ) =
    HadoopPrepPipeline.Request(
      config,
      inputs._1.toString,
      inputs._2.toString,
      inputs._3.toString,
      inputs._4.toString,
      HadoopPrepPipeline.DefaultSnapshots,
      StableIds.newRunId(java.util.UUID.fromString(uuid)).toOption.get,
      retrievalDates = fixtureRetrieval
    )

  private def institutionWork(
      id: String,
      doi: String,
      title: String,
      topicId: String,
      topicName: String
  ): String =
    s"""{"id":"https://openalex.org/$id","doi":"https://doi.org/$doi","title":"$title","publication_year":2020,"type":"article","authorships":[{"raw_author_name":"Ada Lovelace","author":{"id":"https://openalex.org/A5048491430","display_name":"Ada Lovelace"},"institutions":[{"id":"https://openalex.org/I4210144935","display_name":"Analytical Engine","ror":"https://ror.org/02catss52"}]}],"primary_location":{"source":{"id":"https://openalex.org/S4210195904","display_name":"PT AI","issn_l":"2192-6255"}},"topics":[{"id":"https://openalex.org/$topicId","display_name":"$topicName","score":0.5}]}"""

  private def runObservation(openAlexLines: Vector[String], uuid: String): Vector[String] = {
    val dir = Files.createTempDirectory("prep-observation")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      s"""<?xml version="1.0"?><!DOCTYPE dblp []><dblp>
${record("conf/obs/Solo1", "<author>Ada</author>", "<title>Local</title><year>2020</year>")}
</dblp>"""
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(openAlex, openAlexLines.mkString("\n"))
    Files.writeString(dir.resolve("crossref.jsonl"), crossrefWork("10.1000/other.doi", "Other"))
    Files.writeString(
      dir.resolve("orcid.jsonl"),
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}"""
    )
    val ran = HadoopPrepPipeline.execute(
      request(
        dir.resolve("out"),
        dblp,
        openAlex,
        dir.resolve("crossref.jsonl"),
        dir.resolve("orcid.jsonl"),
        16,
        32,
        128,
        uuid
      )
    )
    assert(ran.isRight, ran.left.toOption.getOrElse(""))
    LogicalRecords.lines(ran.toOption.get.directory.resolve("export"))
  }

  private def openAlexWork(
      id: String,
      doi: String,
      title: String,
      abstractIndex: Option[String]
  ): String = {
    val abstractField =
      abstractIndex.map(value => s""","abstract_inverted_index":$value""").getOrElse("")
    s"""{"id":"https://openalex.org/$id","doi":"https://doi.org/$doi","title":"$title","publication_year":2020,"type":"article","authorships":[{"raw_author_name":"Ada Lovelace","author":{"id":"https://openalex.org/A5048491430","display_name":"Ada Lovelace"}}],"primary_location":{"source":{"id":"https://openalex.org/S4210195904","display_name":"PT AI","issn_l":"2192-6255"}},"topics":[{"id":"https://openalex.org/T12090","display_name":"Language","score":0.5}]$abstractField}"""
  }

  private def abstractIndex: String = """{"machine":[0],"mentality":[1]}"""

  private def crossrefWork(doi: String, title: String): String =
    s"""{"message":{"DOI":"$doi","type":"journal-article","title":["$title"],"author":[{"given":"Ada","family":"Lovelace"}],"issued":{"date-parts":[[2020]]},"ISSN":["2192-6255"],"container-title":["PT AI"]}}"""

  private val orcidRecord: String =
    """{"orcid-identifier":{"path":"0000-0002-4414-6920"},"person":{"name":{"credit-name":{"value":"Ada Lovelace"},"given-names":{"value":"Ada"},"family-name":{"value":"Lovelace"}},"other-names":{"other-name":[{"content":"A. Lovelace"}]},"biography":{"content":"Analyst and programmer."},"external-identifiers":{"external-identifier":[]}},"activities-summary":{"employments":{"affiliation-group":[{"summaries":[{"employment-summary":{"path":"/0000-0002-4414-6920/employment/1","put-code":1,"role-title":"Analyst","start-date":{"year":{"value":"1843"}},"organization":{"name":"Analytical Engine","disambiguated-organization":{"disambiguated-organization-identifier":"https://ror.org/02catss52","disambiguation-source":"ROR"}}}}]}]},"distinctions":{"affiliation-group":[{"summaries":[{"distinction-summary":{"path":"/0000-0002-4414-6920/distinction/3","put-code":3,"role-title":"Fellow","start-date":{"year":{"value":"1843"}},"organization":{"name":"Royal Society","disambiguated-organization":{"disambiguated-organization-identifier":"385488","disambiguation-source":"RINGGOLD"}}}}]}]},"works":{"group":[{"work-summary":[{"path":"/0000-0002-4414-6920/work/2","put-code":2,"title":{"title":{"value":"Notes"}},"publication-date":{"year":{"value":"1843"}},"external-ids":{"external-id":[{"external-id-type":"doi","external-id-value":"10.1000/shared.doi"}]}}]}]}}}"""
}
