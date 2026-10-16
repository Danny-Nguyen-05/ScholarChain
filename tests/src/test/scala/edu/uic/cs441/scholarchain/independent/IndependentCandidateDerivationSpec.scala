package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8

class IndependentCandidateDerivationSpec extends AnyFunSuite {
  import IndependentResolutionFixtures.*
  private def input(works: Vector[WorkRecord], candidates: Vector[MatchCandidate] = Vector.empty) =
    ResolutionInput.create(works, Vector.empty, Vector.empty, candidates).toOption.get

  test("multiple preparation blocks produce one unordered work comparison retaining every block") {
    val a = work("conf/independent/BlockA")
    val b = work("conf/independent/BlockB")
    val candidates = Vector(
      candidate(a, b, "name:alex example"),
      candidate(b, a, "title-year:distributed storage transactions:2020")
    )
    val population =
      CandidateBuilder.build(input(Vector(a, b), candidates), ResolutionConfig.example).toOption.get
    val works = population.pairs.filter(_.pair.entityType == ResolutionEntityType.Work)
    assert(works.size == 1)
    assert(
      works.head.contributingCandidates.map(_.candidateId).toSet == candidates
        .map(_.candidateId)
        .toSet
    )
    assert(
      works.head.contributingCandidates.map(_.blockKey).toSet == candidates.map(_.blockKey).toSet
    )
    assert(population.pairs.map(_.pair.pairId).distinct.size == population.pairs.size)
  }

  test("cross-publication researcher candidates exist without a matching work candidate") {
    val a = work("conf/independent/CrossA", title = "Consensus protocols")
    val b = work("conf/independent/CrossB", title = "Streaming joins", year = Some(2024))
    assert(a.workId != b.workId)
    val population =
      CandidateBuilder.build(input(Vector(a, b)), ResolutionConfig.example).toOption.get
    assert(population.pairs.exists(p => p.pair == pair(mention(a), mention(b))))
    assert(population.pairs.forall(_.pair.entityType == ResolutionEntityType.Researcher))
  }

  test("common-name giant blocks are skipped rather than expanded to all pairs") {
    val works = (1 to 20).map(i => work(s"conf/independent/Common$i")).toVector
    val base = ResolutionConfig.example
    val config =
      base.copy(blocking = base.blocking.copy(maxMembersPerBlock = 3, maxPairsPerBlock = 3))
    val population = CandidateBuilder.build(input(works), config).toOption.get
    assert(population.pairs.isEmpty)
    assert(population.diagnostics.exists(d => d.code == "DERIVED_OVERSIZE_BLOCK" && d.count > 0))
  }

  test("per-mention and whole-run limits bound cross-publication candidate expansion") {
    val works = (1 to 6).map(i => work(s"conf/independent/Capped$i")).toVector
    val base = ResolutionConfig.example
    val config = base.copy(blocking =
      base.blocking.copy(maxPairsPerRun = 2, maxCrossPublicationPairsPerMention = 1)
    )
    val population = CandidateBuilder.build(input(works), config).toOption.get
    assert(population.pairs.size <= 2)
    val endpoints = population.pairs.flatMap(p => Vector(p.pair.left, p.pair.right))
    assert(endpoints.groupBy(ResolutionIds.endpointId).values.forall(_.size <= 1))
    assert(
      population.diagnostics.exists(d =>
        Set("RUN_PAIR_BOUND", "MENTION_PAIR_BOUND").contains(d.code)
      )
    )
    val retainedRefs = population.pairs.flatMap(_.evidenceRefs).toSet
    assert(
      population.derivedEvidence.forall(e => retainedRefs(e.ref)),
      "skipped expansion must not retain unused derived evidence beyond the pair budget"
    )
  }

  test("aggregate multiblock evidence cannot evade the pair byte bound") {
    val a = work("conf/independent/BytesA")
    val b = work("conf/independent/BytesB")
    val candidates = (1 to 8).map(i => candidate(a, b, s"name:independent block $i")).toVector
    val in = input(Vector(a, b), candidates)
    val one = Vector(
      in.refs(endpoint(a)).head,
      in.refs(endpoint(b)).head,
      ResolutionInput.evidenceFor("match-candidate", upickle.default.writeJs(candidates.head))
    )
    val initialBytes = one.map(r => in.evidence(r).payload.render().getBytes(UTF_8).length).sum
    val base = ResolutionConfig.example
    val config =
      base.copy(blocking = base.blocking.copy(maxEvidenceBytesPerPair = initialBytes + 10))
    val built = CandidateBuilder.build(in, config)
    if (built.isRight) {
      val population = built.toOption.get
      val evidence = in.evidence ++ population.derivedEvidence.map(e => e.ref -> e)
      population.pairs.foreach { p =>
        val bytes = p.evidenceRefs.map(r => evidence(r).payload.render().getBytes(UTF_8).length).sum
        assert(
          bytes <= config.blocking.maxEvidenceBytesPerPair,
          s"pair carried $bytes bytes despite bound"
        )
      }
      assert(population.diagnostics.exists(_.code.contains("EVIDENCE_BYTE_BOUND")))
    }
  }

  test("cross-entity profile work and nonwork activities have explicit distinct-pair diagnostics") {
    val a = work("conf/independent/Unsupported", names = Vector.empty)
    val p = profile(orcidA, None)
    val employment = activity(OrcidActivityKind.Employment, 1)
    val d1 = activity(OrcidActivityKind.Distinction, 2)
    val d2 = activity(OrcidActivityKind.Distinction, 3)
    def obs(prov: Provenance, workId: Option[String] = None) =
      CandidateObservation(prov.source, prov.sourceRecordId, prov.datasetSnapshot, workId)
    val workObs = obs(a.provenance, Some(a.workId))
    val candidates = Vector(
      candidateObservations(obs(p.provenance), workObs, "name:unsupported a"),
      candidateObservations(obs(p.provenance), workObs, "initial:unsupported a"),
      candidateObservations(obs(employment.provenance), workObs, "name:unsupported b"),
      candidateObservations(obs(d1.provenance), obs(d2.provenance), "name:unsupported c")
    )
    val in = ResolutionInput
      .create(Vector(a), Vector(p), Vector(employment, d1, d2), candidates)
      .toOption
      .get
    val population = CandidateBuilder.build(in, ResolutionConfig.example).toOption.get
    val diagnostics = population.diagnostics.map(d => d.code -> d.count).toMap
    assert(population.pairs.isEmpty)
    assert(diagnostics("UNSUPPORTED_CROSS_ENTITY_PROFILE_WORK") == 2)
    assert(diagnostics("UNSUPPORTED_DISTINCT_CROSS_ENTITY_PAIR") == 1)
    assert(diagnostics("UNSUPPORTED_NONWORK_ORCID_ACTIVITY") == 2)
    assert(diagnostics("UNSUPPORTED_DISTINCT_NONWORK_PAIR") == 2)
    assert(
      in.endpoints.forall {
        case ResolutionEndpoint.Mention(_, _)           => false
        case ResolutionEndpoint.OrcidWorkActivity(_, _) => false
        case _                                          => true
      },
      "activities cannot fabricate mentions or publication teams"
    )
  }
}
