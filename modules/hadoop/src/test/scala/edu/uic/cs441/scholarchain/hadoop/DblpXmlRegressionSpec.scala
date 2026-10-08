package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.apache.hadoop.conf.Configuration
import org.apache.hadoop.fs.{Path => HPath}
import org.apache.hadoop.mapreduce.TaskAttemptID
import org.apache.hadoop.mapreduce.lib.input.FileSplit
import org.apache.hadoop.mapreduce.task.TaskAttemptContextImpl
import org.scalatest.funsuite.AnyFunSuite

import java.io.ByteArrayInputStream
import java.nio.charset.StandardCharsets
import java.nio.file.Files

class DblpXmlRegressionSpec extends AnyFunSuite {
  private val runId = "run:11111111-1111-4111-8111-111111111111"

  private def parse(xml: String, maxExpansion: Long = 100000): Vector[EmittedRecord] =
    DblpRecords.parse(
      xml,
      DblpXml.Header(Map("label" -> "Expanded"), None),
      runId,
      "dblp-test",
      "xml-regression",
      2000000,
      maxExpansion
    )

  private def stream(xml: String): PosStream =
    new PosStream(new ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8)))

  test("opening names are capped before record framing and launch sample scanning") {
    val name = "n" * 100000
    val bad = s"<$name/>"
    val good = "<article key='conf/review/Next'><title>Next</title></article>"
    val xml = s"<dblp>$bad$good</dblp>"
    val in = stream(xml)
    val open = DblpSplitReader.nextOpen(in, Long.MaxValue).get
    assert(open.name.length == DblpSplitReader.MaxStoredTagNameBytes)
    assert(open.nameByteLength == name.length)
    val framed = DblpSplitReader.readElement(in, open, 2000000)
    assert(framed.oversize && !framed.unterminated)
    assert(framed.byteLength == bad.length)
    assert(framed.xml.getBytes(StandardCharsets.UTF_8).length <= 256)
    assert(DblpSplitReader.nextOpen(in, Long.MaxValue).exists(_.name == "article"))
    assert(DblpSplitReader.offsetAfter(stream(xml), 1) == 6L + bad.length)

    val path = Files.createTempFile("dblp-opening-name", ".xml")
    Files.writeString(path, xml)
    val conf = new Configuration()
    conf.setLong(ConfKeys.MaxRecordBytes, 2000000)
    conf.setInt(ConfKeys.MaxSample, 1)
    val input = new HPath(path.toUri)
    SampleBound.install(conf, Seq(input))
    assert(SampleBound.cutoff(conf, input) == 6L + bad.length)
    val reader = new DblpXmlRecordReader
    reader.initialize(
      new FileSplit(input, 0, Files.size(path), Array.empty[String]),
      new TaskAttemptContextImpl(conf, new TaskAttemptID())
    )
    try {
      assert(reader.nextKeyValue())
      val encoded = reader.getCurrentValue.toString.split("\n", 2)
      assert(ujson.read(encoded(0))("oversize").bool)
      assert(ujson.read(encoded(0))("bytes").str.toLong == bad.length)
      assert(encoded(1).getBytes(StandardCharsets.UTF_8).length <= 256)
      assert(reader.nextKeyValue())
      assert(reader.getCurrentValue.toString.contains("conf/review/Next"))
    } finally reader.close()
  }

  test("CDATA title and author references stay literal while active text expands") {
    val xml =
      """<article key="conf/review/Literal"><title>A &amp; <![CDATA[B & C &amp; &label;]]> &label;</title><author><![CDATA[Ada & Bob &amp; &label;]]></author></article>"""
    val records = parse(xml)
    val works = records.collect { case EmittedRecord.Work(value) => value }
    assert(works.size == 1, records.map(_.json).mkString("\n"))
    assert(works.head.title == "A & B & C &amp; &label; Expanded")
    assert(works.head.authors.map(_.nameText) == Vector("Ada & Bob &amp; &label;"))
    assert(
      DblpXml.expandCharacterData("123<![CDATA[456]]>&label;", Map("label" -> "789"), 9) == Right(
        "123456789"
      )
    )
    assert(
      DblpXml.expandCharacterData("123<![CDATA[456]]>&label;", Map("label" -> "789"), 8) == Left(
        RejectReasonCode.OversizeXmlEntityExpansion
      )
    )
    val limited = parse(xml.replace("conf/review/Literal", "conf/r/L"), 12)
    assert(
      limited
        .collect { case EmittedRecord.Rejected(value) => value.reasonCode }
        .contains(RejectReasonCode.OversizeXmlEntityExpansion)
    )
  }

  test("single quoted identifiers and whitespace closing tags retain author evidence") {
    val xml =
      "<article key='conf/review/Quoted'><title>Quoted</title \t><author orcid='0000-0002-4414-6920'>Ada</author \t>\n</article >"
    val records = parse(xml)
    val works = records.collect { case EmittedRecord.Work(value) => value }
    assert(works.size == 1, records.map(_.json).mkString("\n"))
    val work = works.head
    assert(work.sourceRecordId == "conf/review/Quoted")
    assert(work.authors.map(_.nameText) == Vector("Ada"))
    assert(work.authors.head.observedOrcid.contains("0000-0002-4414-6920"))
    assert(work.authors.head.identityStatus == MentionIdentityStatus.ExternalIdentifierObserved)
    assert(
      parse(xml.replace("0000-0002-4414-6920", "invalid-orcid"))
        .collect { case EmittedRecord.Rejected(value) =>
          value.reasonCode
        }
        .contains(RejectReasonCode.InvalidIdentifier)
    )
  }

  test("unmatched mismatched and malformed closing tags reject and preserve the next record") {
    val badBodies = Vector(
      "<title>T</title></bogus>",
      "<title><i>T</title>",
      "<title>T</title extra>",
      "<title>T</title/>",
      "<title>T</ title>",
      "<title>T</>"
    )
    val next = "<article key='conf/review/Next'><title>Next</title></article>"
    badBodies.foreach { body =>
      val bad = s"<article key='conf/review/Bad'>$body</article>"
      val records = parse(bad)
      assert(!records.exists(_.isInstanceOf[EmittedRecord.Work]), bad)
      assert(
        records
          .collect { case EmittedRecord.Rejected(value) => value.reasonCode }
          .contains(RejectReasonCode.MalformedRecord),
        bad
      )
      val in = stream(bad + next)
      val open = DblpSplitReader.nextOpen(in, Long.MaxValue).get
      assert(DblpSplitReader.readElement(in, open, 100000).malformed, bad)
      val after = DblpSplitReader.nextOpen(in, Long.MaxValue).get
      val framed = DblpSplitReader.readElement(in, after, 100000)
      assert(!framed.malformed && framed.xml == next, bad)
    }
  }

  test("a self-closing author is a missing-field reject and does not renumber Ada") {
    val bodies = Vector(
      """<article key="conf/review/A"><author/><author>Ada</author><title>T</title></article>""",
      """<article key="conf/review/A"><author /><author>Ada</author><title>T</title></article>"""
    )
    bodies.foreach { xml =>
      val records = parse(xml)
      val rejected = records.collect { case EmittedRecord.Rejected(value) => value }
      assert(
        rejected.exists(_.reasonCode == RejectReasonCode.MissingRequiredField),
        records.map(_.json).mkString("\n")
      )
      val adaAtOne = records.collect { case EmittedRecord.Work(work) => work }.exists { work =>
        work.authors.exists(author => author.nameText == "Ada" && author.ordinal == 1)
      }
      assert(!adaAtOne, records.map(_.json).mkString("\n"))
      assert(
        !records.exists {
          case EmittedRecord.AuthorshipRec(record) =>
            record.mentionId.contains("#1") && records.exists(_.json.contains("Ada"))
          case _ => false
        }
      )
    }
  }

  test("a FileSplit inside a comment or CDATA does not invent a publication") {
    val comment =
      """<dblp><!-- padding
        |<article key="conf/review/Fake"><title>Fake</title></article>
        |--><article key="conf/review/Real"><title>Real</title></article></dblp>""".stripMargin
    val cdata =
      """<dblp><![CDATA[ padding
        |<article key="conf/review/Fake"><title>Fake</title></article>
        |]]><article key="conf/review/Real"><title>Real</title></article></dblp>""".stripMargin
    val instruction =
      """<dblp><?note <article key="conf/review/Fake"><title>Fake</title></article> ?>
        |<article key="conf/review/Real"><title>Real</title></article></dblp>""".stripMargin
    Vector(comment, cdata, instruction).foreach { xml =>
      assertLexicalUnion(xml)
    }
  }

  private def assertLexicalUnion(xml: String): Unit = {
    val bytes = xml.getBytes(StandardCharsets.UTF_8)
    assert(bytes.length == xml.length)
    val path = Files.createTempFile("dblp-lexical", ".xml")
    Files.write(path, bytes)
    val length = Files.size(path)
    val fakeAt = xml.indexOf("<article key=\"conf/review/Fake\">").toLong
    assert(fakeAt > 0)
    val whole = publicationKeys(readWithInputFormat(path, 0L, length))
    val left = publicationKeys(readWithInputFormat(path, 0L, fakeAt))
    val right = publicationKeys(readWithInputFormat(path, fakeAt, length - fakeAt))
    assert(!whole.contains("conf/review/Fake"), whole.mkString(","))
    assert(whole.contains("conf/review/Real"), whole.mkString(","))
    assert(!right.contains("conf/review/Fake"), right.mkString(","))
    assert(left ++ right == whole, s"left=$left right=$right whole=$whole")
    val inside = xml.indexOf("<title>Real</title>").toLong
    val before = publicationKeys(readWithInputFormat(path, 0L, inside))
    val after = publicationKeys(readWithInputFormat(path, inside, length - inside))
    assert(before ++ after == whole, s"before=$before after=$after whole=$whole")
  }

  private def readWithInputFormat(
      path: java.nio.file.Path,
      start: Long,
      length: Long
  ): Vector[String] = {
    val conf = new Configuration()
    conf.setLong(ConfKeys.MaxRecordBytes, 2000000L)
    val split = new FileSplit(new HPath(path.toUri), start, length, Array.empty[String])
    val context = new TaskAttemptContextImpl(conf, new TaskAttemptID())
    val format = new DblpXmlInputFormat
    val reader = format.createRecordReader(split, context)
    reader.initialize(split, context)
    val found = Vector.newBuilder[String]
    try while (reader.nextKeyValue()) found += reader.getCurrentValue.toString
    finally reader.close()
    found.result()
  }

  private def publicationKeys(encoded: Vector[String]): Vector[String] =
    encoded.flatMap { text =>
      val newline = text.indexOf('\n')
      val body = if (newline < 0) text else text.substring(newline + 1)
      DblpXml.attr(body, "key").toVector
    }
}
