package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.scalatest.funsuite.AnyFunSuite

import java.io.ByteArrayInputStream
import java.nio.charset.StandardCharsets

class IndependentDblpJsonSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  test("DblpSplitReader split edge keeps the record that starts before the boundary") {
    val body = (1 to 2)
      .map { n =>
        dblpRecord(
          s"conf/indep-edge/P$n",
          s"<author>Edge Author $n</author>",
          s"<title>Edge title $n</title><year>2024</year>"
        )
      }
      .mkString("\n")
    val xml = dblpDocument(body)
    val bytes = xml.getBytes(StandardCharsets.UTF_8)
    val p2Start = xml.indexOf("""<inproceedings key="conf/indep-edge/P2"""")
    assert(p2Start > 0)
    val splitAt = xml.indexOf("conf/indep-edge/P2").toLong
    assert(splitAt > p2Start)

    def readRecords(stream: PosStream, end: Long): Vector[String] = {
      val out = Vector.newBuilder[String]
      var open = DblpSplitReader.nextOpen(stream, end)
      while (open.nonEmpty) {
        val name = open.get.name
        val element = DblpSplitReader.readElement(stream, name, 100000L)
        assert(!element.oversize)
        assert(!element.unterminated)
        out += element.xml
        open = DblpSplitReader.nextOpen(stream, end)
      }
      out.result()
    }

    def skipBytes(stream: PosStream, count: Long): Unit = {
      var left = count
      while (left > 0) {
        assert(stream.read() >= 0)
        left -= 1
      }
    }

    val firstEnd = splitAt + 5L
    val firstRecords = readRecords(new PosStream(new ByteArrayInputStream(bytes)), firstEnd)
    val p2FromFirst = firstRecords.find(_.contains("conf/indep-edge/P2")).get
    assert(p2FromFirst.contains("Edge title 2"))
    val p2Work = parseDblp(p2FromFirst).collect { case EmittedRecord.Work(w) => w }.head
    assert(p2Work.title == "Edge title 2")

    val second = new PosStream(new ByteArrayInputStream(bytes))
    skipBytes(second, splitAt)
    assert(second.pos == splitAt)
    val secondRecords = readRecords(second, bytes.length.toLong)
    assert(!secondRecords.exists(_.contains("conf/indep-edge/P1")))
  }

  test("DblpXml local entity declaration expands inline markup before parse") {
    val prefix =
      """<?xml version="1.0"?><!DOCTYPE dblp [<!ENTITY trade "™">]><dblp>"""
    val header = DblpXml.header(prefix)
    assert(header.unsafe.isEmpty)
    assert(header.entities.contains("trade"))
    val xml = dblpRecord(
      "conf/indep-entity/E1",
      "<author>Ada</author>",
      "<title>Markup <sub>v</sub> &trade;</title><year>2020</year>"
    )
    val expanded = DblpXml.expand(xml, header.entities, 1000).toOption.get
    assert(expanded.contains("™"))
    val work = parseDblp(expanded, header, "entity").collect { case EmittedRecord.Work(w) =>
      w
    }.head
    assert(work.title.contains("™"))
    assert(work.title.contains("<sub>"))
  }

  test("DblpRecords rejects malformed token and external SYSTEM entity declaration") {
    val broken = dblpRecord(
      "conf/indep-bad/B1",
      "<author>Ada</author>",
      "<title>Unclosed &entity</title>"
    )
    assert(DblpXml.expand(broken, Map.empty, 1000) == Left(RejectReasonCode.MalformedRecord))

    val externalEntityHeader = DblpXml.header(
      """<?xml version="1.0"?><!DOCTYPE dblp [<!ENTITY ext SYSTEM "file:///etc/passwd">]>"""
    )
    assert(externalEntityHeader.unsafe.contains("external entity"))
    val unsafeParse = parseDblp(
      dblpRecord("conf/indep-bad/S1", "<author>Ada</author>", "<title>Safe title</title>"),
      externalEntityHeader,
      "unsafe"
    )
    assert(
      unsafeParse
        .collect { case EmittedRecord.Rejected(r) => r.reasonCode }
        .contains(
          RejectReasonCode.UnsafeEntity
        )
    )
  }

  test("DblpRecords preserves unicode in author and title fields") {
    val xml = dblpRecord(
      "conf/indep-unicode/U1",
      """<author>北 京</author><author>Åse Øresund</author>""",
      "<title>Café <i>naïve</i> 机器学习</title><year>2019</year>"
    )
    val work = parseDblp(xml).collect { case EmittedRecord.Work(w) => w }.head
    assert(work.title == "Café <i>naïve</i> 机器学习")
    assert(work.authors.map(_.nameText) == Vector("北 京", "Åse Øresund"))
  }

  test("JsonSources accepts missing optional publication_year but rejects invalid required doi") {
    val optionalYear =
      """{"id":"https://openalex.org/W9000000001","title":"No year field","type":"article"}"""
    val optional = jsonLine(SourceType.OpenAlex, optionalYear)
    assert(optional.exists { case EmittedRecord.Work(_) => true; case _ => false })
    assert(optional.collect { case EmittedRecord.Work(w) => w }.head.year.isEmpty)

    val badDoi =
      """{"id":"https://openalex.org/W9000000002","title":"Bad DOI","doi":"not-a-doi","type":"article"}"""
    val invalid = jsonLine(SourceType.OpenAlex, badDoi)
    assert(
      invalid
        .collect { case EmittedRecord.Rejected(r) => r.reasonCode }
        .contains(
          RejectReasonCode.InvalidIdentifier
        )
    )

    val missingTitle = """{"message":{"DOI":"10.1000/indep.missing.title"}}"""
    assert(
      jsonLine(SourceType.Crossref, missingTitle)
        .collect { case EmittedRecord.Rejected(r) =>
          r.reasonCode
        }
        .contains(RejectReasonCode.MissingRequiredField)
    )
  }

  test(
    "JsonSources identical openalex payloads share payload hash and conflicting titles diverge"
  ) {
    val line =
      """{"id":"https://openalex.org/W9000000010","title":"Same","doi":"https://doi.org/10.1000/indep.dup","type":"article"}"""
    val first = jsonLine(SourceType.OpenAlex, line, "dup:1")
    val second = jsonLine(SourceType.OpenAlex, line, "dup:2")
    assert(first.exists { case EmittedRecord.Work(_) => true; case _ => false })
    val leftHash = DerivedRecords.indexRows(first.head, "hash-a").head.payloadHash
    val rightHash = DerivedRecords.indexRows(second.head, "hash-a").head.payloadHash
    assert(leftHash == rightHash)

    val conflictA =
      """{"id":"https://openalex.org/W9000000011","title":"Alpha","doi":"https://doi.org/10.1000/indep.conf","type":"article"}"""
    val conflictB =
      """{"id":"https://openalex.org/W9000000011","title":"Beta","doi":"https://doi.org/10.1000/indep.conf","type":"article"}"""
    val hashA = DerivedRecords.indexRows(jsonLine(SourceType.OpenAlex, conflictA).head, "ha").head
    val hashB = DerivedRecords.indexRows(jsonLine(SourceType.OpenAlex, conflictB).head, "hb").head
    assert(hashA.entry.sourceRecordId == hashB.entry.sourceRecordId)
    assert(hashA.payloadHash != hashB.payloadHash)
  }

  test("PrepLimits pairCount stays overflow-safe at Int.MaxValue team size") {
    val wide = PrepLimits.pairCount(Int.MaxValue)
    assert(wide == Int.MaxValue.toLong * (Int.MaxValue.toLong - 1) / 2)
    val work = parseDblp(
      dblpRecord(
        "conf/indep-pairs/P4",
        (1 to 4).map(n => s"<author>Author $n</author>").mkString,
        "<title>Four authors</title><year>2020</year>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    val rejected = DerivedRecords.pairs(work, maxPairs = 5, maxTeam = 16, "pairs")
    assert(
      rejected
        .collect { case EmittedRecord.Rejected(r) => r.reasonCode }
        .contains(
          RejectReasonCode.OversizeCandidatePairs
        )
    )
  }

  test("DerivedRecords provenance mismatch rejects derived publication team emission") {
    val work = parseDblp(
      dblpRecord(
        "conf/indep-prov/P1",
        "<author>Ada</author>",
        "<title>Provenance gate</title><year>2020</year>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    val team = DerivedRecords
      .teams(work, maxTeam = 16, "team")
      .collect { case EmittedRecord.TeamRec(t) =>
        t
      }
      .head
    val tampered = team.copy(provenance = team.provenance.copy(sourceRecordId = "other-key"))
    assert(
      DerivedRecords
        .provenanceGate(tampered.provenance, work.provenance)
        .contains(RejectReasonCode.ProvenanceMismatch)
    )
  }

  test("DerivedRecords publication teams cover size one two three repeat and oversize rejection") {
    val solo = teamSize("conf/indep-team/S1", "<author>Solo</author>")
    val pair = teamSize(
      "conf/indep-team/P1",
      "<author>Ann</author><author>Bea</author>"
    )
    val trio = teamSize(
      "conf/indep-team/T1",
      "<author>Ann</author><author>Ann</author><author>北</author>"
    )
    assert(solo == 1 && pair == 2 && trio == 3)
    val big = parseDblp(
      dblpRecord(
        "conf/indep-team/B1",
        (1 to 5).map(n => s"<author>Person $n</author>").mkString,
        "<title>Too many</title><year>2020</year>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    assert(
      DerivedRecords
        .teams(big, maxTeam = 4, "big")
        .collect { case EmittedRecord.Rejected(r) =>
          r.reasonCode
        }
        .contains(RejectReasonCode.OversizeTeam)
    )
  }

  private def teamSize(key: String, authors: String): Int =
    DerivedRecords
      .teams(
        parseDblp(
          dblpRecord(key, authors, "<title>Team size</title><year>2020</year>")
        ).collect { case EmittedRecord.Work(w) => w }.head,
        maxTeam = 16,
        "team"
      )
      .collect { case EmittedRecord.TeamRec(t) => t.teamSize }
      .head
}
