package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.scalatest.concurrent.TimeLimits
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.time.{Seconds, Span}

import java.io.InputStream
import java.nio.charset.StandardCharsets

class IndependentDblpXmlAdversarialSpec extends AnyFunSuite with TimeLimits {
  import IndependentTestSupport.*

  private val emptySubset = "<!DOCTYPE dblp []>"
  private val approvedDatedDtd = """<!DOCTYPE dblp SYSTEM "dblp-2023-06-28.dtd">"""
  private val approvedPlainDtd = """<!DOCTYPE dblp SYSTEM "dblp.dtd">"""
  private val remoteDtd = """<!DOCTYPE dblp SYSTEM "http://evil.example/x.dtd">"""
  private val traversalDtd = """<!DOCTYPE dblp SYSTEM "../secret.dtd">"""

  test("a comment is not title or author metadata") {
    val header = DblpXml.header(emptySubset)
    assert(header.unsafe.isEmpty)
    val xml =
      """<article key="conf/review/Comment1">
        |  <!-- <title>Fake</title><author>Fake Author</author> -->
        |  <title>Real</title><author>Real Author</author>
        |</article>""".stripMargin
    assertRealPublication(parse(xml, header, "comment"))
  }

  test("tag-shaped CDATA is not a title or author element") {
    val header = DblpXml.header(emptySubset)
    assert(header.unsafe.isEmpty)
    val xml =
      """<article key="conf/review/Cdata1">
        |  <![CDATA[<title>Fake</title><author>Fake Author</author>]]>
        |  <title>Real</title><author>Real Author</author>
        |</article>""".stripMargin
    assertRealPublication(parse(xml, header, "cdata"))
  }

  test("an approved local DTD basename is not UNSAFE_ENTITY") {
    assert(DblpXml.header(approvedDatedDtd).unsafe.isEmpty)
    assert(DblpXml.header(approvedPlainDtd).unsafe.isEmpty)
    assert(DblpXml.header(remoteDtd).unsafe.isDefined)
    assert(DblpXml.header(traversalDtd).unsafe.isDefined)

    val header = DblpXml.header(approvedDatedDtd)
    val xml = """<article key="conf/review/Eacute1"><title>Caf&eacute;</title></article>"""
    val records = parse(xml, header, "eacute")
    val rejected = records.collect { case EmittedRecord.Rejected(record) => record }
    val detail = rejectDetail(rejected)
    assert(!rejected.exists(_.reasonCode == RejectReasonCode.UnsafeEntity), detail)
    if (rejected.nonEmpty) fail(s"parse rejected: $detail")
    val works = records.collect { case EmittedRecord.Work(work) => work }
    assert(works.size == 1, works.map(_.title).mkString(" | "))
    assert(works.head.title.contains("\u00e9"), s"title=${works.head.title}")
  }

  test("oversize nested XML drains under a byte bound") {
    val maxBytes = 64L
    val prefixAllowance = 512L
    val nested = 10000
    failAfter(Span(2, Seconds)) {
      val stream = new PosStream(new NestedElementStream(nested))
      val element = DblpSplitReader.readElement(stream, "article", maxBytes)
      assert(element.oversize)
      val storedBytes = element.xml.getBytes(StandardCharsets.UTF_8).length.toLong
      val bound = maxBytes + prefixAllowance
      assert(storedBytes <= bound, s"stored xml was $storedBytes bytes; bound is $bound")
      var leftover = 0
      var next = stream.read()
      while (next >= 0 && leftover < 8) {
        leftover += 1
        next = stream.read()
      }
      assert(next < 0, s"nested element was not drained; leftover=$leftover pos=${stream.pos}")
    }
  }

  private def parse(
      xml: String,
      header: DblpXml.Header,
      locator: String
  ): Vector[EmittedRecord] =
    DblpRecords.parse(
      xml,
      header,
      runId,
      "dblp-independent",
      locator,
      100000L,
      100000L,
      None
    )

  private def assertRealPublication(records: Vector[EmittedRecord]): Unit = {
    val rejected = records.collect { case EmittedRecord.Rejected(record) => record }
    val detail = rejectDetail(rejected)
    if (detail.nonEmpty) fail(s"parse rejected: $detail")
    val rendered = records.map(_.json).mkString("\n")
    val fakeAt = rendered.indexOf("Fake")
    val shown =
      rendered.slice(math.max(0, fakeAt), math.min(rendered.length, math.max(fakeAt, 0) + 120))
    assert(fakeAt < 0, shown)
    val works = records.collect { case EmittedRecord.Work(work) => work }
    val titles = works.map(_.title)
    val authors = works.flatMap(_.authors).map(_.nameText)
    assert(!titles.exists(text => text == "Fake" || text == "Fake Author"), titles.mkString(", "))
    assert(
      !authors.exists(text => text == "Fake" || text == "Fake Author"),
      authors.mkString(", ")
    )
    assert(titles == Vector("Real"), titles.mkString(", "))
    assert(authors == Vector("Real Author"), authors.mkString(" | "))
    assert(rendered.contains("Real"))
    assert(rendered.contains("Real Author"))
  }

  private def rejectDetail(rejected: Vector[RejectRecord]): String =
    rejected
      .map { record =>
        val excerpt = record.diagnosticExcerpt.getOrElse("")
        s"${record.reasonCode.wire} $excerpt".trim
      }
      .mkString("; ")

  /** Bytes that follow an article's opening name. readElement writes that name itself. */
  private final class NestedElementStream(count: Int) extends InputStream {
    private val open = "<i>".getBytes(StandardCharsets.UTF_8)
    private val close = "</i>".getBytes(StandardCharsets.UTF_8)
    private val end = "</article>".getBytes(StandardCharsets.UTF_8)
    private val readBudget = 200000
    private var reads = 0
    private var phase = 0
    private var index = 0
    private var cursor = 0

    override def read(): Int = {
      reads += 1
      if (reads > readBudget)
        throw new java.io.IOException(s"nested element exceeded read budget $readBudget")
      phase match {
        case 0 =>
          phase = 1
          '>'
        case 1 =>
          val value = open(cursor) & 0xff
          advance(open.length, 2)
          value
        case 2 =>
          val value = close(cursor) & 0xff
          advance(close.length, 3)
          value
        case 3 =>
          val value = end(cursor) & 0xff
          cursor += 1
          if (cursor >= end.length) phase = 4
          value
        case _ => -1
      }
    }

    private def advance(length: Int, nextPhase: Int): Unit = {
      cursor += 1
      if (cursor == length) {
        cursor = 0
        index += 1
        if (index == count) {
          index = 0
          phase = nextPhase
        }
      }
    }
  }
}
