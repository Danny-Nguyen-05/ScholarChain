package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*

/** Independently transcribed G1 from phase6.md Section 8. All records are synthetic. The expected
  * table is literal fixture data, not calculated from the teams under test.
  */
private[independent] object IndependentPhase6G1 {
  val hadoopRunId = "run:33333333-3333-4333-8333-333333333333"
  val erRunId = "run:44444444-4444-4444-8444-444444444444"
  val sparkRunId = "run:55555555-5555-4555-8555-555555555555"
  val snapshot = "independent-6c-g1-synthetic"
  val identityPolicy = "independent-g1-identity-v1"
  val graphPolicy = "independent-g1-graph-v1"
  val representativePolicy = "independent-g1-representative-v1"
  val erPolicy = "independent-g1-er-v1"
  val erPolicyHash = "a" * 64
  val note = "Synthetic independent G1 test observation; not a real publication or identity."

  final case class Paper(label: String, year: Option[Int], team: Vector[String])
  val papers: Vector[Paper] = Vector(
    Paper("w1", Some(2015), Vector("A", "B", "C")),
    Paper("w2", Some(2016), Vector("A", "B")),
    Paper("w9", Some(2016), Vector("A", "A", "B")),
    Paper("w3", Some(2017), Vector("C", "D")),
    Paper("w4", Some(2018), Vector("D", "E", "F")),
    Paper("w5", Some(2019), Vector("E", "F")),
    Paper("w6", Some(2020), Vector("F", "G")),
    Paper("w7", Some(2020), Vector("H", "I")),
    Paper("w8", Some(2021), Vector("J"))
  )

  val windows: Vector[SparkWindow] = Vector(
    SparkWindow("all-years", None, None, None),
    SparkWindow("2015-2017", Some(2015), Some(2017), Some(0)),
    SparkWindow("2018-2021", Some(2018), Some(2021), Some(1))
  )

  /** The work lists are ordered newest first, then by stable work ID for same-year ties. */
  final case class ExpectedEdge(
      windowId: String,
      left: String,
      right: String,
      weight: Long,
      first: Int,
      last: Int,
      supportingWorks: Set[String]
  )
  val expectedEdges: Vector[ExpectedEdge] = Vector(
    ExpectedEdge("all-years", "A", "B", 3, 2015, 2016, Set("w1", "w2", "w9")),
    ExpectedEdge("all-years", "A", "C", 1, 2015, 2015, Set("w1")),
    ExpectedEdge("all-years", "B", "C", 1, 2015, 2015, Set("w1")),
    ExpectedEdge("all-years", "C", "D", 1, 2017, 2017, Set("w3")),
    ExpectedEdge("all-years", "D", "E", 1, 2018, 2018, Set("w4")),
    ExpectedEdge("all-years", "D", "F", 1, 2018, 2018, Set("w4")),
    ExpectedEdge("all-years", "E", "F", 2, 2018, 2019, Set("w4", "w5")),
    ExpectedEdge("all-years", "F", "G", 1, 2020, 2020, Set("w6")),
    ExpectedEdge("all-years", "H", "I", 1, 2020, 2020, Set("w7")),
    ExpectedEdge("2015-2017", "A", "B", 3, 2015, 2016, Set("w1", "w2", "w9")),
    ExpectedEdge("2015-2017", "A", "C", 1, 2015, 2015, Set("w1")),
    ExpectedEdge("2015-2017", "B", "C", 1, 2015, 2015, Set("w1")),
    ExpectedEdge("2015-2017", "C", "D", 1, 2017, 2017, Set("w3")),
    ExpectedEdge("2018-2021", "D", "E", 1, 2018, 2018, Set("w4")),
    ExpectedEdge("2018-2021", "D", "F", 1, 2018, 2018, Set("w4")),
    ExpectedEdge("2018-2021", "E", "F", 2, 2018, 2019, Set("w4", "w5")),
    ExpectedEdge("2018-2021", "F", "G", 1, 2020, 2020, Set("w6")),
    ExpectedEdge("2018-2021", "H", "I", 1, 2020, 2020, Set("w7"))
  )

  val dblpWorks: Vector[WorkRecord] = papers.map(p => work(p.label, p.year, p.team))
  val crossrefW1: WorkRecord =
    work("w1-crossref", Some(2015), Vector("A", "B", "C"), SourceType.Crossref)
  val allWorks: Vector[WorkRecord] = dblpWorks :+ crossrefW1

  def researcherId(name: String): String =
    StableIds.researcherIdFromDblpName(identityPolicy, name).toOption.get

  def workId(label: String): String = dblpWorks
    .find(_.sourceRecordId == s"conf/independent-g1/$label")
    .map(_.workId)
    .get

  /** The accepted w1 work link chooses the Crossref DOI ID by representative authority. */
  def canonicalWorkId(label: String): String =
    if (label == "w1") crossrefW1.workId else workId(label)

  def provenance(source: SourceType, sourceRecordId: String): Provenance =
    Provenance(
      SchemaVersions.domain,
      source,
      sourceRecordId,
      None,
      snapshot,
      Some("2026-10-21"),
      None,
      hadoopRunId,
      Vector(note)
    )

  def work(
      label: String,
      year: Option[Int],
      team: Vector[String],
      source: SourceType = SourceType.Dblp
  ): WorkRecord = {
    val native = source match {
      case SourceType.Dblp     => s"conf/independent-g1/$label"
      case SourceType.Crossref => "10.5555/independent-g1-w1"
      case SourceType.OpenAlex => "https://openalex.org/W9200000001"
      case _ =>
        throw new IllegalArgumentException("fixture supports DBLP, Crossref and OpenAlex works")
    }
    val id = source match {
      case SourceType.Dblp     => StableIds.workIdFromDblpKey(native).toOption.get
      case SourceType.Crossref => StableIds.workIdFromDoi(native).toOption.get
      case SourceType.OpenAlex => StableIds.workIdFromOpenAlex(native).toOption.get
      case _                   => throw new IllegalArgumentException("unsupported fixture source")
    }
    val p = provenance(source, native)
    val authors = team.zipWithIndex.map { case (name, index) =>
      AuthorMention(
        StableIds.mentionId(source, native, index + 1),
        SchemaVersions.domain,
        source,
        native,
        index + 1,
        name,
        TextNorm.personName(name),
        None,
        None,
        MentionIdentityStatus.NameOnlyUnconfirmed,
        None,
        note,
        p
      )
    }
    val title = s"Independent G1 $label"
    WorkRecord(
      SchemaVersions.domain,
      id,
      source,
      native,
      None,
      title,
      TextNorm.title(title),
      year,
      None,
      if (source == SourceType.Crossref) Some(native) else None,
      None,
      None,
      None,
      authors,
      None,
      p
    )
  }

  def teams: Vector[PublicationTeam] = allWorks.map(w =>
    PublicationTeam(
      SchemaVersions.domain,
      w.workId,
      w.authors.map(_.mentionId),
      w.authors.size,
      note,
      w.provenance
    )
  )

  def pairs: Vector[CoauthorPairCandidate] = allWorks.flatMap { w =>
    for {
      left <- w.authors.indices
      right <- (left + 1) until w.authors.size
    } yield CoauthorPairCandidate(
      SchemaVersions.domain,
      w.workId,
      w.doi,
      w.arxivId,
      w.authors(left).mentionId,
      w.authors(right).mentionId,
      left + 1,
      right + 1,
      w.year,
      note,
      w.provenance
    )
  }
}
