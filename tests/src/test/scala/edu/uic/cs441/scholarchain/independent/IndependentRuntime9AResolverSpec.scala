package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

/** Independent synthetic cache observations; suffixes identify distinct source people. */
class IndependentRuntime9AResolverSpec extends AnyFunSuite {
  import IndependentRuntime9AFixture.*
  import IndependentStorageFixtures.{researcherId, secondResearcherId, runId}
  private def link(
      name: String,
      id: String,
      source: String,
      display: String,
      confidence: Option[Double] = None
  ): EntityLink = EntityLink(
    "name",
    TextNorm.personName(name),
    "independent-runtime-policy",
    source,
    id,
    display,
    Vector("institution:synthetic"),
    confidence,
    runId,
    Vector("source-backed-synthetic-observation")
  )

  test("multiple observations of one canonical identity remain one candidate with all sources") {
    val cache = new InMemoryEntityLinkCache
    assert(
      StorageResult.successful(
        cache.putLink(link("Ada Example", researcherId, "source-a", "Ada Example"))
      )
    )
    assert(
      StorageResult.successful(
        cache.putLink(link("Ada Example", researcherId, "source-b", "Ada Example"))
      )
    )
    new ResearcherResolverAgent(cache, config).resolve(plan(Vector("Ada Example"))) match {
      case ResolverResult.Resolved(Vector(candidate)) =>
        assert(candidate.researcherId == researcherId)
        assert(candidate.sourceIds == Vector("source-a", "source-b"))
        assert(candidate.affiliations == Vector("institution:synthetic"))
        assert(candidate.confidence.isEmpty)
        assert(candidate.runIds == Vector(runId))
      case other => fail(s"Expected one canonical candidate, got $other")
    }
  }

  test("common name abstains with both identities even when one confidence is higher") {
    val cache = new InMemoryEntityLinkCache
    cache.putLink(link("Wei Wang", researcherId, "source-a", "Wei Wang 0001", Some(0.99)))
    cache.putLink(link("Wei Wang", secondResearcherId, "source-b", "Wei Wang 0002", Some(0.51)))
    new ResearcherResolverAgent(cache, config).resolve(plan(Vector("Wei Wang"))) match {
      case ResolverResult.Ambiguous(name, candidates, totalCandidateCount, truncated) =>
        assert(name == "Wei Wang")
        assert(totalCandidateCount == 2 && !truncated)
        assert(candidates.map(_.researcherId).toSet == Set(researcherId, secondResearcherId))
        assert(candidates.flatMap(_.confidence).toSet == Set(0.99, 0.51))
      case other => fail(s"Expected ambiguity rather than score selection, got $other")
    }
  }

  test(
    "exact homonym suffix resolves its identity while the published base alias stays ambiguous"
  ) {
    val cache = new InMemoryEntityLinkCache
    Vector(("Name 0001", researcherId, "source-a"), ("Name 0002", secondResearcherId, "source-b"))
      .foreach { (display, id, source) =>
        cache.putLink(link(display, id, source, display))
        cache.putLink(link("Name", id, source, display))
      }
    assert(
      new ResearcherResolverAgent(cache, config)
        .resolve(plan(Vector("Name")))
        .isInstanceOf[ResolverResult.Ambiguous]
    )
    Vector("Name 0001" -> researcherId, "Name 0002" -> secondResearcherId).foreach { (name, id) =>
      new ResearcherResolverAgent(cache, config).resolve(plan(Vector(name))) match {
        case ResolverResult.Resolved(Vector(candidate)) => assert(candidate.researcherId == id)
        case other => fail(s"Suffix $name must not collapse: $other")
      }
    }
  }

  test("missing name returns NotFound without generating an identity or confidence") {
    assert(
      new ResearcherResolverAgent(new InMemoryEntityLinkCache, config)
        .resolve(plan(Vector("Nobody Present"))) ==
        ResolverResult.NotFound("Nobody Present")
    )
  }

  test("cache failures stay typed failures instead of being misreported as not found") {
    val failed = new EntityLinkCache {
      def putLink(value: EntityLink): StorageResult[EntityLink] = StorageResult.Rejected("disabled")
      def lookupByNormalizedName(name: String): StorageResult[Vector[EntityLink]] =
        StorageResult.Rejected("offline-fault")
      def lookupByExternalId(namespace: String, id: String): StorageResult[Vector[EntityLink]] =
        StorageResult.Rejected("disabled")
    }
    assert(
      new ResearcherResolverAgent(failed, config).resolve(plan(Vector("Ada Example"))) ==
        ResolverResult.Failed("resolver-cache-unavailable")
    )
  }

  test("a ranking question without named researchers needs no invented resolution") {
    assert(
      new ResearcherResolverAgent(new InMemoryEntityLinkCache, config)
        .resolve(plan(Vector.empty)) ==
        ResolverResult.Resolved(Vector.empty)
    )
  }
}
