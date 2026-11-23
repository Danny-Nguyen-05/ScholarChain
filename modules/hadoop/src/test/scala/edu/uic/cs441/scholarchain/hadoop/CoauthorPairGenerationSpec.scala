package edu.uic.cs441.scholarchain.hadoop

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite

/** Value-asserting cases for coauthor pair generation (J08 helper `DerivedRecords.pairs`), team
  * generation (J07 helper `DerivedRecords.teams`) and the blocking and key functions. Every
  * expectation records what the production code does today.
  */
class CoauthorPairGenerationSpec extends AnyFunSuite {
  private val runId = StableIds
    .newRunId(java.util.UUID.fromString("13131313-1313-4313-8313-131313131313"))
    .toOption
    .get

  private val header = DblpXml.Header(Map.empty, None)

  private def dblpWork(
      key: String,
      names: Seq[String],
      year: Option[Int] = Some(2020),
      title: String = "Pair Fixture"
  ): WorkRecord = {
    val authors = names.map(name => s"<author>$name</author>").mkString
    val yearXml = year.map(y => s"<year>$y</year>").getOrElse("")
    val xml = s"""<inproceedings key="$key">$authors<title>$title</title>$yearXml</inproceedings>"""
    val emitted =
      DblpRecords.parse(xml, header, runId, "dblp-test", "pair-spec", 100000, 100000)
    emitted.collect { case EmittedRecord.Work(value) => value } match {
      case Vector(work) => work
      case other        => fail(s"expected one work, got $other from $emitted")
    }
  }

  private def named(key: String, count: Int): WorkRecord =
    dblpWork(key, (1 to count).map(n => s"Author $n"))

  private def pairsOf(emitted: Vector[EmittedRecord]): Vector[CoauthorPairCandidate] =
    emitted.collect { case EmittedRecord.PairRec(value) => value }

  private def rejectsOf(emitted: Vector[EmittedRecord]): Vector[RejectRecord] =
    emitted.collect { case EmittedRecord.Rejected(value) => value }

  private def mid(key: String, ordinal: Int): String =
    s"mention:dblp:$key#$ordinal"

  private def idPairs(emitted: Vector[EmittedRecord]): Vector[(String, String)] =
    pairsOf(emitted).map(p => (p.leftMentionId, p.rightMentionId))

  // ---------------------------------------------------------------- pair generation

  test("a team of one author generates no pairs and no rejects") {
    val work = named("conf/pair/Solo1", 1)
    assert(work.authors.map(_.mentionId) == Vector(mid("conf/pair/Solo1", 1)))
    val out = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    assert(out == Vector.empty)
  }

  test("a work with no authors generates no pairs") {
    val work = named("conf/pair/Empty1", 1).copy(authors = Vector.empty)
    assert(DerivedRecords.pairs(work, 128, 16, work.sourceRecordId) == Vector.empty)
  }

  test("a team of two authors generates exactly one pair in canonical order") {
    val work = named("conf/pair/Duo1", 2)
    val out = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    assert(out.size == 1)
    val pair = pairsOf(out).head
    assert(pair.leftMentionId == mid("conf/pair/Duo1", 1))
    assert(pair.rightMentionId == mid("conf/pair/Duo1", 2))
    assert(pair.leftOrdinal == 1)
    assert(pair.rightOrdinal == 2)
    assert(pair.workId == "work:dblp:conf/pair/Duo1")
    assert(pair.year == Some(2020))
    assert(pair.doi == None)
    assert(pair.arxivId == None)
    assert(pair.schemaVersion == SchemaVersions.domain)
    assert(pair.uncertainty == "undirected pair from one work; mention order is String.compareTo")
    assert(pair.provenance == work.provenance)
  }

  test("a team of three authors generates exactly three pairs with i<j and no self pairs") {
    val key = "conf/pair/Trio1"
    val work = named(key, 3)
    val out = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    assert(rejectsOf(out) == Vector.empty)
    assert(
      idPairs(out) == Vector(
        (mid(key, 1), mid(key, 2)),
        (mid(key, 1), mid(key, 3)),
        (mid(key, 2), mid(key, 3))
      )
    )
    val ordinals = pairsOf(out).map(p => (p.leftOrdinal, p.rightOrdinal))
    assert(ordinals == Vector((1, 2), (1, 3), (2, 3)))
    assert(pairsOf(out).forall(p => p.leftMentionId != p.rightMentionId))
    assert(pairsOf(out).forall(p => p.leftMentionId.compareTo(p.rightMentionId) < 0))
    assert(idPairs(out).distinct.size == 3)
  }

  test("a team of five authors generates the ten pairs n(n-1)/2 in lexicographic order") {
    val key = "conf/pair/Five1"
    val work = named(key, 5)
    val out = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    val expected = for {
      i <- 1 to 5
      j <- (i + 1) to 5
    } yield (mid(key, i), mid(key, j))
    assert(expected.size == 10)
    assert(PrepLimits.pairCount(5) == 10L)
    assert(idPairs(out) == expected.toVector)
    assert(
      pairsOf(out).map(p => (p.leftOrdinal, p.rightOrdinal)) == Vector(
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (2, 3),
        (2, 4),
        (2, 5),
        (3, 4),
        (3, 5),
        (4, 5)
      )
    )
    assert(idPairs(out).distinct.size == 10)
  }

  test("pair count equals n(n-1)/2 for each team size from 1 to 8") {
    val counts = (1 to 8).map { n =>
      val work = named(s"conf/pair/Size$n", n)
      n -> pairsOf(DerivedRecords.pairs(work, 1000, 16, work.sourceRecordId)).size
    }
    assert(counts == Vector(1 -> 0, 2 -> 1, 3 -> 3, 4 -> 6, 5 -> 10, 6 -> 15, 7 -> 21, 8 -> 28))
  }

  test("canonical order is String.compareTo on mention ids so ordinal 10 sorts before 2") {
    val key = "conf/pair/Ten1"
    val work = named(key, 10)
    val out = pairsOf(DerivedRecords.pairs(work, 1000, 16, work.sourceRecordId))
    assert(out.size == 45)
    val ids = work.authors.map(_.mentionId).sorted
    assert(ids.take(3) == Vector(mid(key, 1), mid(key, 10), mid(key, 2)))
    val first = out.head
    assert((first.leftMentionId, first.rightMentionId) == (mid(key, 1), mid(key, 10)))
    assert((first.leftOrdinal, first.rightOrdinal) == (1, 10))
    val tenTwo = out.find(p => p.leftMentionId == mid(key, 10) && p.rightMentionId == mid(key, 2))
    assert(tenTwo.map(p => (p.leftOrdinal, p.rightOrdinal)) == Some((10, 2)))
    assert(!out.exists(p => p.leftMentionId == mid(key, 2) && p.rightMentionId == mid(key, 10)))
    assert(out.forall(p => p.leftMentionId.compareTo(p.rightMentionId) < 0))
    assert(out.map(p => (p.leftMentionId, p.rightMentionId)).distinct.size == 45)
  }

  test("author order does not change the generated pairs") {
    val key = "conf/pair/Order1"
    val work = named(key, 5)
    val forward = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    val reversed =
      DerivedRecords.pairs(work.copy(authors = work.authors.reverse), 128, 16, work.sourceRecordId)
    val rotated = DerivedRecords.pairs(
      work.copy(authors = work.authors.drop(2) ++ work.authors.take(2)),
      128,
      16,
      work.sourceRecordId
    )
    assert(idPairs(forward).size == 10)
    assert(idPairs(reversed) == idPairs(forward))
    assert(idPairs(rotated) == idPairs(forward))
    assert(forward == reversed)
    assert(forward == rotated)
  }

  test("generation is repeatable for the same input") {
    val work = named("conf/pair/Repeat1", 4)
    val first = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    val second = DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)
    assert(first == second)
    assert(CoreJson.compact(pairsOf(first).head) == CoreJson.compact(pairsOf(second).head))
  }

  test("repeated author names stay distinct mentions and still pair by mention id") {
    val key = "conf/pair/Same1"
    val work = dblpWork(key, Seq("Ann Lee", "Ann Lee", "Ann Lee"))
    assert(work.authors.map(_.normalizedName) == Vector("ann lee", "ann lee", "ann lee"))
    assert(
      idPairs(DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)) == Vector(
        (mid(key, 1), mid(key, 2)),
        (mid(key, 1), mid(key, 3)),
        (mid(key, 2), mid(key, 3))
      )
    )
  }

  test("a pair record carries the work doi and a missing year as None") {
    val key = "conf/pair/NoYear1"
    val work = dblpWork(key, Seq("Ada", "Bea"), year = None)
    val pair = pairsOf(DerivedRecords.pairs(work, 128, 16, work.sourceRecordId)).head
    assert(pair.year == None)
    assert(pair.doi == work.doi)
    assert(pair.leftMentionId == mid(key, 1))
  }

  // ---------------------------------------------------------------- limits

  test("a team exactly at the team-size limit is expanded") {
    val key = "conf/pair/AtLimit1"
    val work = named(key, 4)
    val out = DerivedRecords.pairs(work, 6, 4, work.sourceRecordId)
    assert(rejectsOf(out) == Vector.empty)
    assert(pairsOf(out).size == 6)
  }

  test("a team one above the team-size limit yields nothing from the pair step") {
    val work = named("conf/pair/OverLimit1", 5)
    assert(DerivedRecords.pairs(work, 1000, 4, work.sourceRecordId) == Vector.empty)
  }

  test("the team step rejects a team above the limit and keeps one at the limit") {
    val atLimit = named("conf/pair/TeamAt1", 4)
    val kept = DerivedRecords.teams(atLimit, 4, atLimit.sourceRecordId)
    val teamRecords = kept.collect { case EmittedRecord.TeamRec(value) => value }
    assert(teamRecords.size == 1)
    assert(teamRecords.head.teamSize == 4)
    assert(teamRecords.head.memberMentionIds == atLimit.authors.map(_.mentionId))
    assert(kept.collect { case EmittedRecord.AuthorshipRec(value) =>
      value.position
    } == Vector(1, 2, 3, 4))
    assert(rejectsOf(kept) == Vector.empty)

    val over = named("conf/pair/TeamOver1", 5)
    val rejected = DerivedRecords.teams(over, 4, over.sourceRecordId)
    assert(rejected.size == 1)
    val reject = rejectsOf(rejected).head
    assert(reject.reasonCode == RejectReasonCode.OversizeTeam)
    assert(reject.stage == PreparationStage.PublicationTeam)
    assert(reject.diagnosticExcerpt == Some("team 5 exceeds 4"))
    assert(reject.source == Some(SourceType.Dblp))
    assert(reject.sourceLocator == "conf/pair/TeamOver1")
  }

  test("a team of one is a complete team with one authorship") {
    val work = named("conf/pair/TeamSolo1", 1)
    val out = DerivedRecords.teams(work, 16, work.sourceRecordId)
    val team = out.collect { case EmittedRecord.TeamRec(value) => value }.head
    assert(team.teamSize == 1)
    assert(team.memberMentionIds == Vector(mid("conf/pair/TeamSolo1", 1)))
    assert(out.collect { case EmittedRecord.AuthorshipRec(value) => value.position } == Vector(1))
  }

  test("team members follow ordinal order even when the input authors are reversed") {
    val key = "conf/pair/TeamOrder1"
    val work = named(key, 3)
    val out = DerivedRecords.teams(
      work.copy(authors = work.authors.reverse),
      16,
      work.sourceRecordId
    )
    val team = out.collect { case EmittedRecord.TeamRec(value) => value }.head
    assert(team.memberMentionIds == Vector(mid(key, 1), mid(key, 2), mid(key, 3)))
  }

  test("pair expansion exactly at maxPairs is expanded and one above is rejected as one record") {
    val key = "conf/pair/Cap1"
    val work = named(key, 4)
    assert(PrepLimits.pairCount(4) == 6L)
    val atCap = DerivedRecords.pairs(work, 6, 16, work.sourceRecordId)
    assert(pairsOf(atCap).size == 6)
    assert(rejectsOf(atCap) == Vector.empty)
    val over = DerivedRecords.pairs(work, 5, 16, work.sourceRecordId)
    assert(over.size == 1)
    assert(pairsOf(over) == Vector.empty)
    val reject = rejectsOf(over).head
    assert(reject.reasonCode == RejectReasonCode.OversizeCandidatePairs)
    assert(reject.stage == PreparationStage.CoauthorPair)
    assert(reject.diagnosticExcerpt == Some("pair expansion 6 exceeds 5"))
    assert(reject.sourceLocator == key)
    assert(reject.datasetSnapshot == Some("dblp-test"))
    assert(reject.runId == runId)
  }

  test("maxPairs of zero rejects a two-author team and still allows a one-author team") {
    val two = named("conf/pair/Zero2", 2)
    val rejected = DerivedRecords.pairs(two, 0, 16, two.sourceRecordId)
    assert(rejectsOf(rejected).map(_.reasonCode) == Vector(RejectReasonCode.OversizeCandidatePairs))
    assert(rejectsOf(rejected).head.diagnosticExcerpt == Some("pair expansion 1 exceeds 0"))
    val one = named("conf/pair/Zero1", 1)
    assert(DerivedRecords.pairs(one, 0, 16, one.sourceRecordId) == Vector.empty)
  }

  test("PrepLimits.pairCount gives the exact values for 0 to 6 and 100") {
    assert((0 to 6).map(n => PrepLimits.pairCount(n)) == Vector(0L, 0L, 1L, 3L, 6L, 10L, 15L))
    assert(PrepLimits.pairCount(100) == 4950L)
    assert(PrepLimits.pairCount(-3) == 0L)
  }

  // ---------------------------------------------------------------- key functions

  test("blockKey joins trimmed segments with a colon") {
    assert(DerivedRecords.blockKey("name", "ada lovelace") == Some("name:ada lovelace"))
    assert(DerivedRecords.blockKey("exact", "doi", "10.1000/x") == Some("exact:doi:10.1000/x"))
    assert(DerivedRecords.blockKey("  name  ", "  ada  ") == Some("name:ada"))
    assert(DerivedRecords.blockKey("solo") == Some("solo"))
  }

  test("blockKey keeps an empty trailing segment and keeps case, accents and inner spaces") {
    assert(DerivedRecords.blockKey("name", "") == Some("name:"))
    assert(DerivedRecords.blockKey("name", "José  Álvarez") == Some("name:José  Álvarez"))
    assert(DerivedRecords.blockKey("Name", "ADA") == Some("Name:ADA"))
  }

  test("blockKey replaces embedded line breaks with a space before trimming") {
    assert(DerivedRecords.blockKey("name", "ada\nlovelace") == Some("name:ada lovelace"))
    assert(DerivedRecords.blockKey("name", "ada\r\nlovelace") == Some("name:ada  lovelace"))
    assert(DerivedRecords.blockKey("name", "\nada\n") == Some("name:ada"))
  }

  test("blockKey refuses an empty key and a key longer than 512 characters") {
    assert(DerivedRecords.blockKey() == None)
    assert(DerivedRecords.blockKey("") == None)
    assert(DerivedRecords.blockKey("   ") == None)
    assert(DerivedRecords.blockKey("\n") == None)
    val prefix = "name:"
    val atLimit = "x" * (512 - prefix.length)
    assert(DerivedRecords.blockKey("name", atLimit).map(_.length) == Some(512))
    assert(DerivedRecords.blockKey("name", atLimit + "x") == None)
  }

  test("exactKey is built for work, ORCID and OpenAlex author namespaces and refused otherwise") {
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.Doi, "10.1000/x") == Some("exact:doi:10.1000/x")
    )
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.Arxiv, "2101.00001") ==
        Some("exact:arxiv:2101.00001")
    )
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.Dblp, "conf/a/B1") == Some("exact:dblp:conf/a/B1")
    )
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.OpenAlexWork, "W123") ==
        Some("exact:openalex-work:W123")
    )
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.Orcid, "0000-0002-4414-6920") ==
        Some("exact:orcid:0000-0002-4414-6920")
    )
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.OpenAlexAuthor, "A5048491430") ==
        Some("exact:openalex-author:A5048491430")
    )
    assert(DerivedRecords.exactKey(IdentifierNamespace.Ror, "02catss52") == None)
    assert(DerivedRecords.exactKey(IdentifierNamespace.Ringgold, "385488") == None)
    assert(DerivedRecords.exactKey(IdentifierNamespace.OpenAlexInstitution, "I42") == None)
    // normalisation of the value happens upstream; a blank value only loses its own text here
    assert(DerivedRecords.exactKey(IdentifierNamespace.Doi, "   ") == Some("exact:doi:"))
    assert(
      DerivedRecords.exactKey(IdentifierNamespace.Doi, "  10.1000/x \n") == Some(
        "exact:doi:10.1000/x"
      )
    )
    assert(
      DerivedRecords.exactNamespaces == Set(
        IdentifierNamespace.Doi,
        IdentifierNamespace.Arxiv,
        IdentifierNamespace.Dblp,
        IdentifierNamespace.OpenAlexWork,
        IdentifierNamespace.Orcid,
        IdentifierNamespace.OpenAlexAuthor
      )
    )
  }

  test("initials takes the first character of each space-separated word") {
    assert(DerivedRecords.initials("ada lovelace") == "a l")
    assert(DerivedRecords.initials("ada") == "a")
    assert(DerivedRecords.initials("") == "")
    assert(DerivedRecords.initials("   ") == "")
    assert(DerivedRecords.initials("  ada   king  lovelace ") == "a k l")
    assert(DerivedRecords.initials("Ada Lovelace") == "A L")
    assert(DerivedRecords.initials("élan vital") == "é v")
  }

  private def profile(
      title: String = "",
      year: Option[Int] = None,
      venue: String = "",
      names: Vector[String] = Vector.empty,
      initialsV: Vector[String] = Vector.empty,
      affiliations: Vector[String] = Vector.empty,
      coauthors: Vector[String] = Vector.empty,
      exact: Vector[String] = Vector.empty
  ): Bibliography =
    Bibliography(
      SourceType.Dblp,
      "conf/key/Rec1",
      "dblp-test",
      None,
      title,
      year,
      venue,
      names,
      initialsV,
      affiliations,
      coauthors,
      exact
    )

  test("blockKeys emits every key family sorted and de-duplicated") {
    val bib = profile(
      title = "graph mining",
      year = Some(2020),
      venue = "pt-ai",
      names = Vector("ada lovelace", "bea kim"),
      initialsV = Vector("a l", "b k"),
      affiliations = Vector("analytical engine"),
      coauthors = Vector("ada lovelace", "bea kim"),
      exact = Vector("exact:doi:10.1000/x", "exact:doi:10.1000/x")
    )
    assert(
      DerivedRecords.blockKeys(bib) == Vector(
        "affiliation:analytical engine",
        "coauthor:ada lovelace",
        "coauthor:bea kim",
        "exact:doi:10.1000/x",
        "initial:a l",
        "initial:b k",
        "name:ada lovelace",
        "name:bea kim",
        "title-year:graph mining:2020",
        "venue:pt-ai"
      )
    )
  }

  test("blockKeys uses unknown for a missing year and drops empty title, venue and initials") {
    val bib = profile(
      title = "graph mining",
      year = None,
      venue = "",
      names = Vector("ada"),
      initialsV = Vector("", "a")
    )
    assert(
      DerivedRecords.blockKeys(bib) == Vector(
        "initial:a",
        "name:ada",
        "title-year:graph mining:unknown"
      )
    )
    val noTitle = profile(title = "", year = Some(2020), names = Vector("ada"))
    assert(DerivedRecords.blockKeys(noTitle) == Vector("name:ada"))
  }

  test("blockKeys falls back to the source and record id when no other key exists") {
    assert(DerivedRecords.blockKeys(profile()) == Vector("fallback:DBLP:conf/key/Rec1"))
    val orcid = profile().copy(source = SourceType.Orcid, sourceRecordId = "0000-0002-4414-6920")
    assert(DerivedRecords.blockKeys(orcid) == Vector("fallback:ORCID:0000-0002-4414-6920"))
  }

  test("blockKeys drops a name key that would exceed 512 characters and keeps the rest") {
    val long = "n" * 600
    val bib = profile(names = Vector("ada", long))
    assert(DerivedRecords.blockKeys(bib) == Vector("name:ada"))
    val onlyLong = profile(names = Vector(long))
    assert(DerivedRecords.blockKeys(onlyLong) == Vector("fallback:DBLP:conf/key/Rec1"))
  }

  test("blockKeys re-splits an exact key on colons and rejoins it unchanged") {
    val bib = profile(exact = Vector("exact:doi:10.1000/a:b", "exact:orcid:0000-0002-4414-6920"))
    assert(
      DerivedRecords.blockKeys(bib) == Vector(
        "exact:doi:10.1000/a:b",
        "exact:orcid:0000-0002-4414-6920"
      )
    )
  }

  test("bibliography normalises case and whitespace in author names and builds the keys") {
    val work = dblpWork(
      "conf/key/Norm1",
      Seq("  Ada   LOVELACE ", "Bea Kim"),
      year = Some(2021),
      title = "Graph Mining."
    )
    assert(work.authors.map(_.normalizedName) == Vector("ada lovelace", "bea kim"))
    val bib = DerivedRecords
      .bibliography(Seq(Kinds.Work -> CoreJson.compact(work)), Seq.empty)
      .get
    assert(bib.source == SourceType.Dblp)
    assert(bib.sourceRecordId == "conf/key/Norm1")
    assert(bib.authorNames == Vector("ada lovelace", "bea kim"))
    assert(bib.authorInitials == Vector("a l", "b k"))
    assert(bib.coauthorNames == Vector("ada lovelace", "bea kim"))
    assert(bib.year == Some(2021))
    assert(bib.venue == "")
    assert(bib.exactKeys == Vector.empty)
    val keys = DerivedRecords.blockKeys(bib)
    assert(keys.contains("name:ada lovelace"))
    assert(keys.contains("initial:a l"))
    assert(keys.contains("coauthor:bea kim"))
    assert(keys.contains(s"title-year:${work.normalizedTitle}:2021"))
    assert(keys.size == 7)
    assert(keys == keys.distinct.sorted)
  }

  test("bibliography keeps accents, lowercases them and does not fold them to ASCII") {
    val work = dblpWork("conf/key/Accent1", Seq("José  ÁLVAREZ"), year = None)
    assert(work.authors.map(_.normalizedName) == Vector("josé álvarez"))
    val bib = DerivedRecords
      .bibliography(Seq(Kinds.Work -> CoreJson.compact(work)), Seq.empty)
      .get
    assert(bib.authorNames == Vector("josé álvarez"))
    assert(bib.authorInitials == Vector("j á"))
    assert(bib.coauthorNames == Vector.empty)
    assert(bib.year == None)
    val keys = DerivedRecords.blockKeys(bib)
    assert(keys.contains("name:josé álvarez"))
    assert(keys.contains("initial:j á"))
    assert(keys.contains(s"title-year:${work.normalizedTitle}:unknown"))
    assert(!keys.exists(_.startsWith("coauthor:")))
  }

  test("bibliography is absent when no record carries an anchor") {
    assert(DerivedRecords.bibliography(Seq.empty, Seq.empty) == None)
  }

  test("bibliography exact keys come from index rows, only for exact namespaces, sorted") {
    val work = dblpWork("conf/key/Rows1", Seq("Ada"))
    val rows = DerivedRecords.indexRows(EmittedRecord.Work(work), "hash")
    val bib = DerivedRecords
      .bibliography(Seq(Kinds.Work -> CoreJson.compact(work)), rows)
      .get
    assert(bib.exactKeys == Vector("exact:dblp:conf/key/Rows1"))
    assert(DerivedRecords.blockKeys(bib).head == "exact:dblp:conf/key/Rows1")
  }

  test("member copies the profile fields and the chosen block key") {
    val bib = profile(
      title = "t",
      year = Some(2019),
      venue = "v",
      names = Vector("ada"),
      initialsV = Vector("a"),
      affiliations = Vector("lab"),
      coauthors = Vector("bea")
    )
    val member = DerivedRecords.member(bib, "name:ada")
    assert(
      member == BlockMember(
        "name:ada",
        SourceType.Dblp,
        "conf/key/Rec1",
        "dblp-test",
        None,
        "t",
        Some(2019),
        "v",
        Vector("ada"),
        Vector("a"),
        Vector("lab"),
        Vector("bea")
      )
    )
  }

  test("candidate refuses to pair two members of a fallback block") {
    val left = DerivedRecords.member(profile(), "fallback:DBLP:conf/key/Rec1")
    val right = left.copy(sourceRecordId = "conf/key/Rec2")
    val result = DerivedRecords.candidate(left, right, 2, runId)
    assert(result.isLeft)
    assert(result.left.toOption.get.code == ViolationCode.MalformedId)
    assert(result.left.toOption.get.message == "fallback block does not pair records")
  }

  test("orderedPair puts the smaller mention id first and keeps ties in input order") {
    val a = dblpWork("conf/key/OrdA1", Seq("Ada", "Bea"))
    val Vector(first, second) = a.authors
    assert(DerivedRecords.orderedPair(first, second) == ((first, second)))
    assert(DerivedRecords.orderedPair(second, first) == ((first, second)))
    assert(DerivedRecords.orderedPair(first, first) == ((first, first)))
  }
}
