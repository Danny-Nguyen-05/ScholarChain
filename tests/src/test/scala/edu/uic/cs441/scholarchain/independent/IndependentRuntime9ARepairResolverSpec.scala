package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

/** B2/B3 regressions use canonical-count expectations and the real runtime artifact fake. */
class IndependentRuntime9ARepairResolverSpec extends AnyFunSuite {
  import IndependentRuntime9AFixture.*
  import IndependentStorageFixtures.{researcherId, secondResearcherId, runId}
  private val limits = RuntimeResolverConfig(
    maxDistinctCandidates = 2,
    maxSourceIdsPerCandidate = 3,
    maxEvidenceRefsPerCandidate = 4,
    maxAffiliationsPerCandidate = 2,
    maxRunIdsPerCandidate = 1
  )
  private val boundedConfig =
    config.copy(resolver = limits, retrieval = config.retrieval.copy(graphLimit = 2))
  private def cached(name: String, id: String, source: String, display: String): EntityLink =
    EntityLink(
      "name",
      TextNorm.personName(name),
      "independent-r1-policy",
      source,
      id,
      display,
      Vector.empty,
      None,
      runId,
      Vector("independent-source:" + source)
    )

  test(
    "B2 many raw observations for one canonical identity resolve with bounded disclosed provenance"
  ) {
    val cache = new InMemoryEntityLinkCache
    val otherRun = "run:99887766-5544-4322-8877-aabbccddeeff"
    (0 until 31).foreach { i =>
      val row = cached("Ada Example", researcherId, f"source-$i%02d", "Ada Example").copy(
        affiliations = Vector(f"institution-$i%02d"),
        evidenceRefs = Vector(f"source-evidence-$i%02d", "shared-source-evidence"),
        runId = if (i % 2 == 0) runId else otherRun
      )
      assert(StorageResult.successful(cache.putLink(row)))
    }
    new ResearcherResolverAgent(cache, boundedConfig).resolve(plan(Vector("Ada Example"))) match {
      case ResolverResult.Resolved(Vector(candidate)) =>
        assert(candidate.researcherId == researcherId)
        assert(candidate.sourceIds.size == 3)
        assert(candidate.evidenceRefs.size == 4)
        assert(candidate.affiliations.size == 2)
        assert(candidate.runIds.size == 1)
        assert(candidate.confidence.isEmpty)
        val summary = candidate.provenanceSummary.get
        assert(summary.sourceIdCount == 31)
        assert(summary.evidenceRefCount == 32)
        assert(summary.affiliationCount == 31)
        assert(summary.runIdCount == 2)
        assert(summary.truncated)
      case other => fail(s"Raw row count cannot turn one canonical identity into failure: $other")
    }
  }

  test("B2 too many canonical identities returns a bounded Ambiguous list with exact total") {
    val cache = new InMemoryEntityLinkCache
    val ids = (1 to 5).map(i => "researcher:dblp:" + f"$i%064x").toVector
    ids.zipWithIndex.foreach { (id, index) =>
      assert(
        StorageResult.successful(
          cache.putLink(cached("Wei Wang", id, s"source-$index", s"Wei Wang 000${index + 1}"))
        )
      )
    }
    new ResearcherResolverAgent(cache, boundedConfig).resolve(plan(Vector("Wei Wang"))) match {
      case ResolverResult.Ambiguous(name, candidates, totalCandidateCount, truncated) =>
        assert(name == "Wei Wang")
        assert(totalCandidateCount == 5 && truncated)
        assert(candidates.size == 2)
        assert(candidates.map(_.researcherId) == ids.sorted.take(2))
        assert(
          candidates.forall(c =>
            c.sourceIds.size <= limits.maxSourceIdsPerCandidate &&
              c.evidenceRefs.size <= limits.maxEvidenceRefsPerCandidate
          )
        )
      case other => fail(s"Canonical overflow must retain disclosed ambiguity, got $other")
    }
  }

  private def artifactStore(): RuntimeArtifactStore = {
    val sourceContext = IndependentStorageFixtures.context.copy(windowId = None)
    val first =
      IndependentStorageFixtures.researcher.copy(label = "Name 0001", properties = Vector.empty)
    val second = first.copy(nodeId = secondResearcherId, label = "Name 0002")
    def solo(id: String, window: String) = IndependentStorageFixtures.metrics.copy(
      context = sourceContext.copy(windowId = Some(window)),
      researcherId = id,
      publicationCount = 1,
      distinctCoauthorCount = 0,
      totalCoauthorOccurrences = 0,
      averageCoauthorsPerPaper = 0.0,
      maximumCoauthorsOnOnePaper = 0,
      weightedDegree = 0,
      communityId = None,
      coreness = Some(0)
    )
    def row[A: upickle.default.Writer](value: A): ujson.Obj =
      upickle.default.writeJs(value).obj match {
        case fields => ujson.Obj.from(fields)
      }
    val rows: Map[String, Vector[ujson.Obj]] = Map(
      "nodes/type=researcher" -> Vector(row(first), row(second)),
      "metrics/type=researcher_collaboration" -> Vector(
        row(solo(researcherId, "all-years")),
        row(solo(secondResearcherId, "since-2015"))
      ),
      "metrics/type=communities" -> Vector.empty,
      "metrics/type=community_summaries" -> Vector.empty,
      "metrics/type=bridges" -> Vector.empty,
      "metrics/type=temporal_changes" -> Vector.empty,
      "edges/type=coauthored_with" -> Vector.empty,
      "edges/type=coauthored_with_support" -> Vector.empty
    )
    new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeArtifactStore(
      sourceContext,
      rows,
      Vector("all-years", "since-2015")
    )
  }

  test("B3 known identity absent from a stored window resolves with empty context") {
    val artifacts = artifactStore()
    assert(artifacts.researcherContext(researcherId, "since-2015", 10) == StorageResult.Missing)
    val cache = new InMemoryEntityLinkCache
    assert(
      StorageResult.successful(
        cache.putLink(cached("Name 0001", researcherId, "source-1", "Name 0001"))
      )
    )
    new ResearcherResolverAgent(cache, config, Some(artifacts))
      .resolve(plan(Vector("Name 0001"))) match {
      case ResolverResult.Resolved(Vector(candidate)) =>
        assert(candidate.researcherId == researcherId)
        assert(candidate.coauthorContext.isEmpty)
        assert(candidate.coauthorContextTruncated.isEmpty)
      case other => fail(s"Identity must not depend on publication presence in the window: $other")
    }
  }

  test("B3 an absent homonym remains in ambiguity with the active homonym") {
    val artifacts = artifactStore()
    assert(
      StorageResult.successful(artifacts.researcherContext(secondResearcherId, "since-2015", 10))
    )
    val cache = new InMemoryEntityLinkCache
    cache.putLink(cached("Name", researcherId, "source-1", "Name 0001"))
    cache.putLink(cached("Name", secondResearcherId, "source-2", "Name 0002"))
    new ResearcherResolverAgent(cache, config, Some(artifacts))
      .resolve(plan(Vector("Name"))) match {
      case ResolverResult.Ambiguous(name, candidates, totalCandidateCount, truncated) =>
        assert(name == "Name")
        assert(candidates.map(_.researcherId).toSet == Set(researcherId, secondResearcherId))
        assert(totalCandidateCount == 2 && !truncated)
      case other => fail(s"Absent homonym must remain plausible: $other")
    }
  }

  test("B3 an undeclared window remains rejected by the actual artifact store and resolver") {
    val artifacts = artifactStore()
    assert(
      artifacts.researcherContext(researcherId, "not-stored", 10) ==
        StorageResult.Rejected("unsupported-runtime-window")
    )
    val unknown = plan(Vector("Name 0001")).copy(runtime =
      Some(
        RuntimeQueryOptions(researcherNames = Vector("Name 0001"), windowIds = Vector("not-stored"))
      )
    )
    assert(
      new ResearcherResolverAgent(new InMemoryEntityLinkCache, config, Some(artifacts))
        .resolve(unknown) ==
        ResolverResult.Failed("resolver-window-not-stored")
    )
  }
}
