package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.Normalization
import edu.uic.cs441.scholarchain.hadoop.*
import org.scalatest.funsuite.AnyFunSuite

import java.io.ByteArrayInputStream
import java.nio.charset.StandardCharsets.UTF_8

/** Synthetic inputs only; literal oracles follow the public identity and preparation contracts. */
class AdversarialDataPlaneSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  test("NFC and NFD share DBLP researcher identity while original author evidence survives") {
    val composed = "José Núñez"
    val decomposed = "Jose\u0301 Nu\u0301n\u0303ez"
    val xml = dblpRecord(
      "conf/adversarial/unicode",
      s"<author>$composed</author><author>$decomposed</author>",
      "<title>Unicode</title>"
    )
    val work = parseDblp(xml).collect { case EmittedRecord.Work(w) => w }.head
    assert(work.authors.map(_.nameText) == Vector(composed, decomposed))
    assert(work.authors.map(_.mentionId).distinct.size == 2)
    val firstId = StableIds.researcherIdFromDblpName("dblp-exact-v1", composed).toOption.get
    val secondId = StableIds.researcherIdFromDblpName("dblp-exact-v1", decomposed).toOption.get
    assert(firstId == secondId)
    assert(Normalization.text(composed) == "josé núñez")
    assert(Normalization.text(decomposed) == "josé núñez")
  }

  test("Latin Cyrillic confusables and DBLP homonym suffixes stay distinct identities") {
    // The second spelling begins with Cyrillic U+0410, not Latin U+0041.
    val names = Vector("Alex Li", "\u0410lex Li", "Alex Li 0001", "Alex Li 0002")
    val ids =
      names.map(name => StableIds.researcherIdFromDblpName("dblp-exact-v1", name).toOption.get)
    assert(ids.distinct.size == 4)
    assert(
      names.map(Normalization.text) == Vector(
        "alex li",
        "\u0430lex li",
        "alex li 0001",
        "alex li 0002"
      )
    )
  }

  test("64 repeated common-name mentions yield exactly 2016 distinct ordinal pairs") {
    val work = parseDblp(
      dblpRecord(
        "conf/adversarial/team64",
        Vector.fill(64)("<author>Wei Wang</author>").mkString,
        "<title>Synthetic large team</title><year>2020</year>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    val records = DerivedRecords.pairs(work, maxPairs = 2016, maxTeam = 64, "synthetic-team64")
    val pairs = records.collect { case EmittedRecord.PairRec(p) => p }
    assert(records.size == 2016 && pairs.size == 2016)
    val ordinalPairs = pairs.map(p => Set(p.leftOrdinal, p.rightOrdinal))
    assert(ordinalPairs.distinct.size == 2016)
    assert(ordinalPairs.forall(_.size == 2))
    assert(ordinalPairs.flatten.toSet == (1 to 64).toSet)
    assert((1 to 64).forall(i => ordinalPairs.count(_.contains(i)) == 63))
    assert(
      pairs.forall(p =>
        p.leftMentionId < p.rightMentionId && p.workId == work.workId && p.provenance == work.provenance
      )
    )
  }

  test("64-author expansion one pair over budget rejects atomically without partial pairs") {
    val work = parseDblp(
      dblpRecord(
        "conf/adversarial/pair-budget",
        (1 to 64).map(i => s"<author>Synthetic Person $i</author>").mkString,
        "<title>Budget</title>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    val records = DerivedRecords.pairs(work, maxPairs = 2015, maxTeam = 64, "synthetic-budget")
    assert(records.size == 1)
    assert(records.collect { case EmittedRecord.Rejected(r) =>
      r.reasonCode
    } == Vector(RejectReasonCode.OversizeCandidatePairs))
  }

  test("reordered repeated names retain source ordinals without asserting researcher equality") {
    def work(key: String, names: Vector[String]) = parseDblp(
      dblpRecord(
        key,
        names.map(n => s"<author>$n</author>").mkString,
        "<title>Order evidence</title>"
      )
    ).collect { case EmittedRecord.Work(w) => w }.head
    val first = work("conf/adversarial/order1", Vector("Wei Wang", "Alex Li 0001", "Wei Wang"))
    val second = work("conf/adversarial/order2", Vector("Alex Li 0001", "Wei Wang", "Wei Wang"))
    assert(
      first.authors.map(m => (m.nameText, m.ordinal)) == Vector(
        "Wei Wang" -> 1,
        "Alex Li 0001" -> 2,
        "Wei Wang" -> 3
      )
    )
    assert(
      second.authors.map(m => (m.nameText, m.ordinal)) == Vector(
        "Alex Li 0001" -> 1,
        "Wei Wang" -> 2,
        "Wei Wang" -> 3
      )
    )
    val authorships =
      DerivedRecords.teams(first, 3, "order").collect { case EmittedRecord.AuthorshipRec(a) => a }
    assert(authorships.size == 3 && authorships.forall(_.resolvedResearcherId.isEmpty))
    assert(
      first.authors.map(_.mentionId).toSet.intersect(second.authors.map(_.mentionId).toSet).isEmpty
    )
  }

  test(
    "a truncated final Unicode record is marked unterminated without losing its complete predecessor"
  ) {
    val complete =
      dblpRecord("conf/adversarial/complete", "<author>北 京</author>", "<title>Complete</title>")
    val partial = "<inproceedings key=\"conf/adversarial/truncated\"><author>José</author><title>未完"
    val bytes = (complete + partial).getBytes(UTF_8)
    val stream = new PosStream(new ByteArrayInputStream(bytes))
    val first = DblpSplitReader.nextOpen(stream, bytes.length).get
    val good = DblpSplitReader.readElement(stream, first.name, 100000L)
    assert(!good.unterminated && !good.oversize)
    assert(parseDblp(good.xml).collect { case EmittedRecord.Work(w) =>
      w.title
    } == Vector("Complete"))
    val last = DblpSplitReader.nextOpen(stream, bytes.length).get
    val broken = DblpSplitReader.readElement(stream, last.name, 100000L)
    assert(broken.unterminated && !broken.oversize)
    assert(DblpSplitReader.nextOpen(stream, bytes.length).isEmpty)
  }

  test(
    "multiline Unicode titles preserve source markup and normalize whitespace deterministically"
  ) {
    val title = "Line one\n<i>北 京</i>\nLine three."
    val records = parseDblp(
      dblpRecord("conf/adversarial/multiline", "<author>José</author>", s"<title>$title</title>")
    )
    val works = records.collect { case EmittedRecord.Work(w) => w }
    assert(works.size == 1)
    assert(works.head.title == title)
    assert(works.head.normalizedTitle == "line one <i>北 京</i> line three")
    assert(works.head.authors.map(_.nameText) == Vector("José"))
  }

  test("bare publication metadata never invents topics institutions abstract or profile identity") {
    val records = jsonLine(
      SourceType.OpenAlex,
      """{"id":"https://openalex.org/W99941101","title":"Synthetic sparse work","type":"article","authorships":[{"author":{"display_name":"Wei Wang"}}]}"""
    )
    val works = records.collect { case EmittedRecord.Work(w) => w }
    assert(works.size == 1)
    assert(works.head.abstractTextRef.isEmpty)
    assert(works.head.authors.map(_.nameText) == Vector("Wei Wang"))
    assert(!records.exists {
      case EmittedRecord.InstitutionRec(_) | EmittedRecord.TopicRec(_) | EmittedRecord.Profile(_) |
          EmittedRecord.TextDoc(_) =>
        true
      case _ => false
    })
    assert(
      works.head.authors.forall(m => m.observedOrcid.isEmpty && m.observedOpenAlexAuthorId.isEmpty)
    )
  }
}
