package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path, Paths}

/** Independently constructed synthetic observations, never human labels or production samples. */
private[independent] object IndependentResolutionFixtures {
  val runId = "run:22222222-2222-4222-8222-222222222222"
  val instant = "2026-10-16T15:00:00Z"
  val snapshot = "independent-5b-synthetic"
  val orcidA = "0000-0002-1825-0097"
  val orcidB = "0000-0001-5109-3700"
  val note = "Synthetic independent acceptance fixture; no confirmed researcher identity."

  def root: Path = Iterator
    .iterate(Paths.get("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .find(p => Files.exists(p.resolve("build.sbt")))
    .getOrElse(throw new IllegalStateException("repository root unavailable"))

  def provenance(source: SourceType, native: String, snap: String = snapshot): Provenance =
    Provenance(
      SchemaVersions.domain,
      source,
      native,
      None,
      snap,
      Some("2026-10-16"),
      None,
      runId,
      Vector(note)
    )

  def work(
      native: String,
      title: String = "Distributed storage transactions",
      year: Option[Int] = Some(2020),
      names: Vector[String] = Vector("Alex Example"),
      doi: Option[String] = None,
      orcids: Map[Int, String] = Map.empty,
      authorIds: Map[Int, String] = Map.empty,
      source: SourceType = SourceType.Dblp,
      snap: String = snapshot
  ): WorkRecord = {
    val p = provenance(source, native, snap)
    val nativeWorkId = source match {
      case SourceType.Dblp     => StableIds.workIdFromDblpKey(native)
      case SourceType.OpenAlex => StableIds.workIdFromOpenAlex(native)
      case SourceType.Crossref => StableIds.workIdFromDoi(native)
      case _ => throw new IllegalArgumentException("fixture source must carry works")
    }
    val id = StableIds.authoritativeWorkId(doi, None, nativeWorkId).toOption.get
    val mentions = names.zipWithIndex.map { case (name, i) =>
      AuthorMention(
        StableIds.mentionId(source, native, i + 1),
        SchemaVersions.domain,
        source,
        native,
        i + 1,
        name,
        TextNorm.personName(name),
        orcids.get(i + 1),
        authorIds.get(i + 1),
        if (orcids.contains(i + 1) || authorIds.contains(i + 1))
          MentionIdentityStatus.ExternalIdentifierObserved
        else MentionIdentityStatus.NameOnlyUnconfirmed,
        None,
        note,
        p
      )
    }
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
      doi,
      None,
      None,
      None,
      mentions,
      None,
      p
    )
  }

  def ref(p: Provenance): ResolutionObservationRef =
    ResolutionObservationRef(p.source, p.sourceRecordId, p.datasetSnapshot)

  def endpoint(w: WorkRecord): ResolutionEndpoint =
    ResolutionEndpoint.Work(ref(w.provenance), w.workId)
  def mention(w: WorkRecord, index: Int = 0): ResolutionEndpoint =
    ResolutionEndpoint.Mention(ref(w.provenance), w.authors(index).mentionId)

  def pair(a: ResolutionEndpoint, b: ResolutionEndpoint): ResolutionPair =
    ResolutionIds.pair(ResolutionIds.entityType(a), a, b).toOption.get

  def candidate(
      a: WorkRecord,
      b: WorkRecord,
      block: String = "name:alex example"
  ): MatchCandidate = {
    val first =
      CandidateObservation(a.source, a.sourceRecordId, a.provenance.datasetSnapshot, Some(a.workId))
    val second =
      CandidateObservation(b.source, b.sourceRecordId, b.provenance.datasetSnapshot, Some(b.workId))
    candidateObservations(first, second, block)
  }

  def candidateObservations(
      first: CandidateObservation,
      second: CandidateObservation,
      block: String
  ): MatchCandidate = {
    val (left, right) = StableIds.canonicalCandidateObservations(first, second).toOption.get
    val id = StableIds.matchCandidateId(left, right, block).toOption.get
    MatchCandidate(
      id,
      SchemaVersions.domain,
      block,
      left,
      right,
      Vector(NamedNumber(PreparationFeatures.yearAbsDelta, -1.0)),
      PreparationFeatures.policyV2,
      runId,
      note,
      provenance(SourceType.ScholarChain, id, "independent-prep-synthetic")
    )
  }

  def profile(orcid: String, name: Option[String] = Some("Alex Example")): OrcidProfileRecord =
    OrcidProfileRecord(
      SchemaVersions.domain,
      orcid,
      name,
      Vector.empty,
      Vector(ObservedIdentifier("orcid", orcid, IdentifierInterpretation.ValidatedExternal)),
      note,
      provenance(SourceType.Orcid, orcid)
    )

  def activity(kind: OrcidActivityKind, code: Int): OrcidActivityRecord = {
    val native = s"$orcidA/${kind.wire}/$code"
    OrcidActivityRecord(
      SchemaVersions.domain,
      orcidA,
      kind,
      native,
      Some("Synthetic ORCID activity"),
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      note,
      provenance(SourceType.Orcid, native)
    )
  }
}
