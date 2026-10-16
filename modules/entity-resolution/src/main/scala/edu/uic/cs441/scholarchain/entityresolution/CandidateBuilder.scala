package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.util.Try
import upickle.default.{ReadWriter, writeJs}

final case class DerivedPair(
    pair: ResolutionPair,
    contributingCandidates: Vector[CandidateBlockRef],
    evidenceRefs: Vector[String]
) derives ReadWriter
final case class CandidatePopulation(
    pairs: Vector[DerivedPair],
    diagnostics: Vector[InputDiagnostic],
    derivedEvidence: Vector[EvidenceRecord]
) derives ReadWriter

object CandidateBuilder {
  def build(input: ResolutionInput, config: ResolutionConfig): Either[String, CandidatePopulation] =
    Try {
      ResolutionConfig.validate(config).fold(e => throw new IllegalArgumentException(e), identity)
      val bounds = config.blocking
      val pairs = mutable.Map.empty[String, DerivedPair]
      val diagnostics = mutable.Map.empty[String, Long].withDefaultValue(0L)
      val derived = mutable.Map.empty[String, EvidenceRecord]
      val perMention = mutable.Map.empty[String, Int].withDefaultValue(0)
      val oversizePairs = mutable.Set.empty[String]
      var attempted = 0L
      def diagnostic(code: String, count: Long = 1): Unit = diagnostics(code) += count
      def add(
          a: ResolutionEndpoint,
          b: ResolutionEndpoint,
          refs: Vector[CandidateBlockRef],
          evidence: Vector[String]
      ): Unit = {
        ResolutionIds.pair(ResolutionIds.entityType(a), a, b) match {
          case Left(_) => diagnostic("SELF_OR_INCOMPATIBLE_PAIR")
          case Right(pair) =>
            if (oversizePairs(pair.pairId)) diagnostic("PAIR_ALREADY_OVERSIZE")
            else if (pairs.contains(pair.pairId)) {
              val old = pairs(pair.pairId)
              val mergedRefs = (old.evidenceRefs ++ evidence).distinct.sorted
              val available = input.evidence ++ derived
              if (
                mergedRefs
                  .map(r => available(r).payload.render().getBytes(UTF_8).length.toLong)
                  .sum > bounds.maxEvidenceBytesPerPair
              ) {
                pairs.remove(pair.pairId); oversizePairs += pair.pairId;
                diagnostic("PAIR_AGGREGATE_EVIDENCE_BYTE_BOUND")
              } else
                pairs(pair.pairId) = old.copy(
                  contributingCandidates = (old.contributingCandidates ++ refs).distinct.sortBy(c =>
                    (c.candidateId, c.blockKey)
                  ),
                  evidenceRefs = mergedRefs
                )
            } else if (pairs.size >= bounds.maxPairsPerRun) diagnostic("RUN_PAIR_BOUND")
            else {
              val keys = Vector(a, b).collect { case e @ ResolutionEndpoint.Mention(_, _) =>
                ResolutionIds.endpointId(e)
              }
              val cross = ResolutionIds.observation(a) != ResolutionIds.observation(b)
              if (
                cross && keys
                  .exists(k => perMention(k) >= bounds.maxCrossPublicationPairsPerMention)
              ) diagnostic("MENTION_PAIR_BOUND")
              else {
                val sourceRefs = (input.refs(a) ++ input.refs(b) ++ evidence).distinct.sorted
                val available = input.evidence ++ derived
                val bytes = sourceRefs
                  .map(r => available(r).payload.render().getBytes(UTF_8).length.toLong)
                  .sum
                if (bytes > bounds.maxEvidenceBytesPerPair) diagnostic("PAIR_EVIDENCE_BYTE_BOUND")
                else {
                  pairs(pair.pairId) = DerivedPair(
                    pair,
                    refs.distinct.sortBy(c => (c.candidateId, c.blockKey)),
                    sourceRefs
                  )
                  if (cross) keys.foreach(k => perMention(k) += 1)
                }
              }
            }
        }
      }
      def endpoint(o: CandidateObservation): Option[ResolutionEndpoint] = {
        val ref = ResolutionObservationRef(o.source, o.sourceRecordId, o.datasetSnapshot)
        input.workByRef
          .get(ref)
          .map(w => ResolutionEndpoint.Work(ref, w.workId))
          .orElse(
            input.profileByRef.get(ref).map(p => ResolutionEndpoint.OrcidProfile(ref, p.orcid))
          )
          .orElse(
            input.activityByRef
              .get(ref)
              .filter(_.activityKind == OrcidActivityKind.Work)
              .map(a => ResolutionEndpoint.OrcidWorkActivity(ref, a.observedWorkId))
          )
      }
      input.candidates.groupBy(_.blockKey).toVector.sortBy(_._1).foreach { case (_, rows) =>
        val members = rows.flatMap(c => Vector(c.left, c.right)).distinct.size
        if (
          members > bounds.maxMembersPerBlock || rows
            .map(c => (c.left, c.right))
            .distinct
            .size > bounds.maxPairsPerBlock
        ) diagnostic("PREP_OVERSIZE_BLOCK_ROWS", rows.size)
        else if (attempted + rows.size > bounds.maxPairAttempts)
          diagnostic("PAIR_ATTEMPT_BOUND", rows.size)
        else
          rows.sortBy(_.candidateId).foreach { c =>
            attempted += 1
            val ea = endpoint(c.left); val eb = endpoint(c.right)
            (ea, eb) match {
              case (Some(a), Some(b))
                  if ResolutionIds.entityType(a) == ResolutionIds.entityType(b) =>
                add(
                  a,
                  b,
                  Vector(CandidateBlockRef(c.candidateId, c.blockKey)),
                  Vector(ResolutionInput.evidenceFor("match-candidate", writeJs(c)))
                )
              case (Some(_), Some(_)) => diagnostic("UNSUPPORTED_CROSS_ENTITY_PROFILE_WORK")
              case _                  => diagnostic("UNSUPPORTED_NONWORK_ORCID_ACTIVITY")
            }
          }
      }
      // Emit pair-level skip counts separately from row counts, so multiblock duplication is visible.
      val unsupported = input.candidates
        .groupBy(c =>
          Vector(c.left, c.right)
            .map(o => ujson.Arr(o.source.wire, o.sourceRecordId, o.datasetSnapshot).render())
            .sorted
            .mkString("\n")
        )
        .values
      unsupported.foreach { rows =>
        val c = rows.head;
        (endpoint(c.left), endpoint(c.right)) match {
          case (Some(a), Some(b)) if ResolutionIds.entityType(a) != ResolutionIds.entityType(b) =>
            diagnostic("UNSUPPORTED_DISTINCT_CROSS_ENTITY_PAIR")
          case (None, _) | (_, None) => diagnostic("UNSUPPORTED_DISTINCT_NONWORK_PAIR")
          case _                     => ()
        }
      }
      val memberships = mutable.ArrayBuffer.empty[(String, ResolutionEndpoint)]
      def block(key: String, e: ResolutionEndpoint): Unit = {
        require(memberships.size < bounds.maxBlockMemberships, "block membership bound exceeded")
        memberships += key -> e
      }
      input.endpoints
        .filter(ResolutionIds.entityType(_) == ResolutionEntityType.Researcher)
        .foreach { e =>
          val names = e match {
            case ResolutionEndpoint.Mention(_, _) => input.mention(e).toVector.map(_.nameText)
            case ResolutionEndpoint.OrcidProfile(ref, _) =>
              input.profileByRef(ref).displayName.toVector ++ input.profileByRef(ref).otherNames
            case _ => Vector.empty
          }
          names
            .flatMap(n => Normalization.nameVariants(n).toVector)
            .filter(_.nonEmpty)
            .distinct
            .sorted
            .foreach(n => block("er-name:" + StableIds.sha256Hex(n), e))
          names
            .map(Normalization.nameTokens)
            .filter(_.nonEmpty)
            .map(t => t.last + ":" + t.head.head)
            .distinct
            .sorted
            .foreach(n => block("er-initial:" + StableIds.sha256Hex(n), e))
          input.authority(e).foreach { case (ns, value) =>
            block("er-id:" + ns.wire + ":" + value, e)
          }
          input
            .mention(e)
            .flatMap(_.observedOpenAlexAuthorId)
            .foreach(id => block("er-openalex-author:" + id, e))
        }
      memberships.toVector.groupBy(_._1).toVector.sortBy(_._1).foreach { case (key, items) =>
        val members = items.map(_._2).distinct.sortBy(ResolutionIds.endpointKey)
        val possible = members.size.toLong * (members.size - 1) / 2
        if (members.size > bounds.maxMembersPerBlock || possible > bounds.maxPairsPerBlock)
          diagnostic("DERIVED_OVERSIZE_BLOCK", possible)
        else if (attempted + possible > bounds.maxPairAttempts)
          diagnostic("PAIR_ATTEMPT_BOUND", possible)
        else if (pairs.size >= bounds.maxPairsPerRun) diagnostic("RUN_PAIR_BOUND", possible)
        else
          for (i <- members.indices; j <- (i + 1) until members.size) {
            attempted += 1
            val a = members(i); val b = members(j)
            if (ResolutionIds.observation(a) != ResolutionIds.observation(b)) {
              val pair = ResolutionIds.pair(ResolutionEntityType.Researcher, a, b).toOption.get
              val candidateId = "match-candidate:" + StableIds.sha256Hex(
                ujson.Arr("er-derived-candidate-v1", key, pair.pairId).render()
              )
              val payload = ujson.Obj(
                "schemaVersion" -> "scholarchain.er-derived-candidate.v1",
                "candidateId" -> candidateId,
                "blockKey" -> key,
                "pair" -> writeJs(pair)
              )
              val ev =
                ResolutionInput.record("derived-candidate", payload, "derived-by-er-blocking-v1")
              derived(ev.ref) = ev
              add(a, b, Vector(CandidateBlockRef(candidateId, key)), Vector(ev.ref))
            }
          }
      }
      val used = pairs.valuesIterator.flatMap(_.evidenceRefs).toSet
      CandidatePopulation(
        pairs.values.toVector.sortBy(_.pair.pairId),
        diagnostics.toVector.sortBy(_._1).map((k, n) => InputDiagnostic(k, n, Vector.empty)),
        derived.valuesIterator.filter(e => used(e.ref)).toVector.sortBy(_.ref)
      )
    }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
}
