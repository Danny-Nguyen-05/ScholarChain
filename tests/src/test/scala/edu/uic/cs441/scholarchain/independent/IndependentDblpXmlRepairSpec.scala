package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.mapreduce.{Job, TaskAttemptID}
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat
import org.apache.hadoop.mapreduce.task.TaskAttemptContextImpl
import org.scalatest.concurrent.TimeLimits
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.time.{Seconds, Span}

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Synthetic regressions for the four XML findings in phase-04/review.md, October 7. */
class IndependentDblpXmlRepairSpec extends AnyFunSuite with TimeLimits {
  import IndependentTestSupport.*

  try org.apache.log4j.Logger.getRootLogger.setLevel(org.apache.log4j.Level.WARN)
  catch { case _: Throwable => () }

  private val goodArticle =
    """<article key="conf/independent/After"><title>After</title><author>Ada</author></article>"""
  private val oversizedNameBytes = 262144
  private val prefix = "<dblp>\n<"
  private val openerEnd = "/>\n"

  test("nextOpen retains a bounded opening name before any record byte limit applies") {
    val input = oversizedOpener("next-open")
    val raw = Files.newInputStream(input)
    try {
      failAfter(Span(10, Seconds)) {
        val stream = new PosStream(raw)
        val open = DblpSplitReader.nextOpen(stream, Long.MaxValue).get
        assert(open.at == prefix.length - 1L)
        assert(
          open.name
            .getBytes(StandardCharsets.UTF_8)
            .length <= DblpSplitReader.MaxStoredTagNameBytes,
          s"opening name retained ${open.name.length} characters"
        )
        assert(stream.pos >= prefix.length + oversizedNameBytes)
        assert(open.nameByteLength == oversizedNameBytes.toLong)
      }
    } finally raw.close()
  }

  test("actual InputFormat drains an oversized opening name and retains the following work") {
    val input = oversizedOpener("input-format")
    val conf = new Configuration()
    conf.setLong(ConfKeys.MaxRecordBytes, 4096L)
    val envelopes = readInput(input, conf)
    assert(envelopes.size == 2)
    val (meta, diagnostic) = envelopes.head
    assert(meta("oversize").bool)
    assert(!meta("unterminated").bool)
    assert(meta("bytes").str.toLong >= oversizedNameBytes)
    assert(diagnostic.getBytes(StandardCharsets.UTF_8).length <= 256)
    assert(envelopes(1)._2 == goodArticle)
    assert(accepted(envelopes(1)._2).sourceRecordId == "conf/independent/After")
  }

  test("launch sample scanning counts and drains the oversized opener under a bounded cutoff") {
    val input = oversizedOpener("sample-scan")
    val conf = new Configuration()
    conf.setInt(ConfKeys.MaxSample, 1)
    failAfter(Span(10, Seconds)) {
      SampleBound.install(conf, Seq(FsPaths.file(input.toString)))
    }
    val expectedNextStart = prefix.length.toLong + oversizedNameBytes + openerEnd.length
    assert(SampleBound.cutoff(conf, FsPaths.file(input.toString)) == expectedNextStart)
    assert(conf.getBoolean(ConfKeys.SampleReady, false))
  }

  test("title and author CDATA preserve bare ampersands literally") {
    val work = accepted(
      """<article key="conf/independent/CdataBare"><title><![CDATA[A & B]]></title><author><![CDATA[Ada & Bob]]></author></article>"""
    )
    assert(work.title == "A & B")
    assert(work.authors.map(_.nameText) == Vector("Ada & Bob"))
  }

  test("entity-shaped CDATA stays literal while adjacent active XML references expand") {
    val header = DblpXml.header("""<!DOCTYPE dblp [<!ENTITY trade "MARK">]>""")
    val xml =
      """<article key="conf/independent/CdataEntities"><title>Active &amp; <![CDATA[Literal &amp; &#38; &trade; &unknown;]]> &trade;</title><author><![CDATA[Ada &amp; &#38; &trade; &unknown;]]></author></article>"""
    val work = accepted(xml, header)
    assert(work.title == "Active & Literal &amp; &#38; &trade; &unknown; MARK")
    assert(work.authors.map(_.nameText) == Vector("Ada &amp; &#38; &trade; &unknown;"))
  }

  test("combined active and CDATA character data still obeys the expansion byte limit") {
    val xml =
      """<article key="conf/i/C"><title>12345678<![CDATA[abcdefghijkl]]></title></article>"""
    val records = DblpRecords.parse(
      xml,
      DblpXml.Header(Map.empty, None),
      runId,
      "dblp-independent",
      "cdata-limit",
      100000L,
      16L
    )
    assertOnlyReject(records, RejectReasonCode.OversizeXmlEntityExpansion)
  }

  test("single quoted publication key and ORCID retain supplied author evidence") {
    val xml =
      """<article key='conf/independent/SingleQuote'><title>Quoted</title><author orcid='0000-0002-4414-6920'>Ada</author></article>"""
    val records = parseDblp(xml)
    assertNoReject(records)
    val work = records.collect { case EmittedRecord.Work(value) => value }.head
    assert(work.sourceRecordId == "conf/independent/SingleQuote")
    assert(work.authors.map(_.nameText) == Vector("Ada"))
    assert(work.authors.size == 1)
    assert(work.authors.head.observedOrcid.contains("0000-0002-4414-6920"))
  }

  test("closing tag whitespace preserves valid title and author text") {
    val xml =
      """<article key="conf/independent/ClosingWhitespace"><title>Whitespace</title \t><author orcid="0000-0002-4414-6920">Ada</author \t\n></article >"""
        .replace("\\t", "\t")
        .replace("\\n", "\n")
    val work = accepted(xml)
    assert(work.title == "Whitespace")
    assert(work.authors.map(_.nameText) == Vector("Ada"))
  }

  private val malformedBodies = Vector(
    "unmatched" -> "<title>T</title></bogus>",
    "mismatched" -> "<title>T</author></title>",
    "crossed" -> "<title><i>T</title></i>",
    "closing attributes" -> "<title>T</title bad='value'>",
    "closing extra name" -> "<title>T</title bogus>",
    "closing slash" -> "<title>T</title/>",
    "closing doubled slash" -> "<title>T</title//>",
    "empty closing name" -> "<title>T</></title>"
  )

  malformedBodies.foreach { case (label, body) =>
    test(s"direct extraction explicitly rejects $label closing tags") {
      val xml = s"""<article key="conf/independent/BadClosing">$body</article>"""
      assertOnlyReject(parseDblp(xml), RejectReasonCode.MalformedRecord)
    }
  }

  test("LocalJobRunner emits explicit rejects for oversized openers and malformed closing tags") {
    val input = oversizedOpener("reject-job")
    val malformedFiles = malformedBodies.zipWithIndex.map { case ((_, body), index) =>
      val xml = s"""<article key="conf/independent/BadClosing$index">$body</article>"""
      Files.writeString(input.getParent.resolve(s"malformed-$index.xml"), dblpDocument(xml))
    }
    val out = phase4RunDir("independent-xml-reject-output").resolve("job-output")
    val config = prepConfig(out, 100, 100, 100).copy(maxRecordBytes = 4096L)
    val conf = PrepJobs.configuration(config, runId, independentSnapshots)
    SampleBound.install(conf, (input +: malformedFiles).map(path => FsPaths.file(path.toString)))
    PrepJobs.run(
      "independent-xml-repairs",
      PrepJobs.dblp(conf, input.getParent.toString, out, None)
    )
    val walk = Files.walk(out)
    val payloads =
      try {
        walk
          .iterator()
          .asScala
          .filter(path => path.getFileName.toString.startsWith("part-"))
          .flatMap(path => Files.readString(path).split('\n').iterator.flatMap(Lines.unpack))
          .map(_._2)
          .toVector
      } finally walk.close()
    val rejected = payloads.flatMap(json => CoreJson.parse[RejectRecord](json).toOption)
    assert(rejected.count(_.reasonCode == RejectReasonCode.OversizeRecord) == 1)
    assert(rejected.count(_.reasonCode == RejectReasonCode.MalformedRecord) == malformedBodies.size)
    assert(works(payloads).map(_.sourceRecordId) == Vector("conf/independent/After"))
    assert(rejected.forall(_.diagnosticExcerpt.forall(_.length <= 256)))
  }

  private def oversizedOpener(label: String): Path = {
    val input = phase4RunDir(s"independent-xml-$label").resolve("oversized.xml")
    val out = Files.newOutputStream(input)
    try {
      out.write(prefix.getBytes(StandardCharsets.UTF_8))
      val block = Array.fill[Byte](4096)('a'.toByte)
      var remaining = oversizedNameBytes
      while (remaining > 0) {
        val n = math.min(remaining, block.length)
        out.write(block, 0, n)
        remaining -= n
      }
      out.write(
        (openerEnd + goodArticle + "\n</dblp>\n")
          .getBytes(StandardCharsets.UTF_8)
      )
    } finally out.close()
    input
  }

  private def readInput(input: Path, conf: Configuration): Vector[(ujson.Value, String)] = {
    val job = Job.getInstance(conf)
    FileInputFormat.addInputPath(job, FsPaths.file(input.toString))
    val format = new DblpXmlInputFormat
    format.getSplits(job).asScala.toVector.flatMap { split =>
      val context = new TaskAttemptContextImpl(job.getConfiguration, new TaskAttemptID())
      val reader = format.createRecordReader(split, context)
      reader.initialize(split, context)
      try {
        val records = Vector.newBuilder[(ujson.Value, String)]
        while (reader.nextKeyValue()) {
          val text = reader.getCurrentValue.toString
          val newline = text.indexOf('\n')
          records += ujson.read(text.substring(0, newline)) -> text.substring(newline + 1)
        }
        records.result()
      } finally reader.close()
    }
  }

  private def accepted(
      xml: String,
      header: DblpXml.Header = DblpXml.Header(Map.empty, None)
  ): WorkRecord = {
    val records = parseDblp(xml, header)
    assertNoReject(records)
    val found = records.collect { case EmittedRecord.Work(work) => work }
    assert(found.size == 1)
    found.head
  }

  private def assertNoReject(records: Vector[EmittedRecord]): Unit = {
    val rejected = records.collect { case EmittedRecord.Rejected(record) => record }
    assert(rejected.isEmpty, rejected.map(CoreJson.compact(_)).mkString("\n"))
  }

  private def assertOnlyReject(records: Vector[EmittedRecord], reason: RejectReasonCode): Unit = {
    val rejected = records.collect { case EmittedRecord.Rejected(record) => record }
    assert(rejected.map(_.reasonCode) == Vector(reason), records.map(_.json).mkString("\n"))
    assert(records.forall { case EmittedRecord.Rejected(_) => true; case _ => false })
  }
}
