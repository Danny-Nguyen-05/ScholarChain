package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import org.scalatest.funsuite.AnyFunSuite

/** Literal positive/negative claim pairs prevent a reject-everything verifier from passing. */
class IndependentRuntime9CVerificationSpec extends AnyFunSuite {
  import IndependentRuntime9CFixture.*
  private def verify(
      claims: Vector[AnswerClaim],
      evidence: EvidenceBundle = bundle(),
      interpretation: String = ""
  ): VerifiedAnswer =
    new ClaimVerificationAgent(config).verify(plan, evidence, proposal(claims, interpretation))
  private def rejected(result: VerifiedAnswer, id: String = "claim-exact"): Unit = {
    assert(
      result.verification.claims
        .find(_.claimId == id)
        .exists(c => c.verdict == ClaimVerdict.Unsupported || c.verdict == ClaimVerdict.Conflicting)
    )
    assert(result.verification.rejectedClaims.exists(_.claimId == id))
    assert(!result.answer.claims.exists(_.claimId == id))
  }

  Vector(
    "publicationCount" -> "3",
    "distinctCoauthorCount" -> "2",
    "totalCoauthorOccurrences" -> "4",
    "weightedDegree" -> "4",
    "averageCoauthorsPerPaper" -> "1.3333333333333333",
    "maximumCoauthorsOnOnePaper" -> "2",
    "coreness" -> "2"
  ).foreach { (field, expected) =>
    test(s"exact $field is verified and rendered without approximate or iteration labels") {
      val result = verify(Vector(claim(Vector(n(field, expected)))))
      assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
      assert(result.answer.claims.size == 1)
      assert(result.answer.summary.contains(expected))
      assert(!result.answer.summary.toLowerCase.contains("approximate"))
      assert(!result.answer.summary.toLowerCase.contains("iteration-limited"))
      assert(result.verification.rejectedClaims.isEmpty)
    }
  }

  test("wrong stored count is rejected and remains available in attempted-claim audit material") {
    rejected(verify(Vector(claim(Vector(n("publicationCount", "999"))))))
  }
  test("a missing evidence ID cannot authorize an otherwise correct count") {
    rejected(verify(Vector(claim(evidenceIds = Vector("evidence:metric:" + ("f" * 64))))))
  }
  test("a fabricated subject cannot borrow another researcher's stored metrics") {
    rejected(
      verify(Vector(claim(subjects = Vector(IndependentRuntime9BFixture.id("Invented Person")))))
    )
  }
  test("a different stored window cannot be silently substituted for the cited all-years value") {
    rejected(verify(Vector(claim(windows = Vector("2015-2017")))))
  }
  test("an unknown field and an unknown template fail closed") {
    rejected(verify(Vector(claim(Vector(n("hIndex", "3"))))))
    rejected(verify(Vector(claim(template = Some("execute-untrusted-text")))))
  }
  test("a claim type cannot recast metric evidence as a publication title") {
    rejected(
      verify(
        Vector(
          claim(
            Vector(t("title", "Independent G1 w1")),
            claimType = RuntimeClaimType.Publication,
            subjects = Vector(work)
          )
        )
      )
    )
  }
  test(
    "factual prose is regenerated from verified fields rather than trusting proposed sentences"
  ) {
    val result = verify(Vector(claim(prose = "Ada Example has 999 publications and is converged.")))
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.contains("3"))
    assert(!result.answer.summary.contains("999"))
    assert(!result.answer.claims.head.text.contains("999"))
    assert(!result.answer.summary.contains("is converged"))
  }
  test("mixed supported and rejected claims retain only verified factual sentences") {
    val good = claim(claimId = "good")
    val bad = claim(Vector(n("distinctCoauthorCount", "999")), claimId = "bad")
    val result = verify(Vector(good, bad))
    assert(result.answer.claims.map(_.claimId) == Vector("good"))
    assert(result.verification.rejectedClaims.map(_.claimId) == Vector("bad"))
    assert(!result.answer.summary.contains("999"))
    assert(result.verification.overallStatus == VerificationStatus.PartiallyVerified)
  }
  test("no accepted claim results in explicit abstention and no unsupported factual text") {
    val result = verify(Vector(claim(Vector(n("publicationCount", "999")))))
    assert(result.verification.abstained)
    assert(result.verification.overallStatus == VerificationStatus.Abstained)
    assert(result.answer.claims.isEmpty)
    assert(!result.answer.summary.contains("999"))
  }
  test(
    "exact integers larger than binary floating-point precision survive verification and rendering"
  ) {
    val large = "9007199254740993"
    val big = RuntimeEvidenceIds
      .bind(
        metric.copy(runtime =
          metric.runtime.map(
            _.copy(values = Vector(t("kind", "metrics"), n("publicationCount", large)))
          )
        )
      )
      .toOption
      .get
    val result = verify(
      Vector(claim(Vector(n("publicationCount", large)), Vector(big.evidenceId))),
      bundle(Vector(big))
    )
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.contains(large))
    assert(!result.answer.summary.contains("9007199254740992"))
  }
  test("untrusted descriptive text cannot authorize a deterministic count in a vector bundle") {
    val vector = bundle(Vector(semantic), RetrievalMode.Vector)
    rejected(verify(Vector(claim(evidenceIds = Vector(semantic.evidenceId))), vector))
  }

  test("a community-size claim retains the stored false convergence flag and iteration count") {
    val c = claim(
      Vector(
        n("size", "3"),
        f("converged", false),
        n("iterations", "3"),
        t("communityQualification", "iteration-limited")
      ),
      Vector(communityItem.evidenceId),
      RuntimeClaimType.Community
    )
    val result = verify(Vector(c), bundle(Vector(communityItem)))
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.toLowerCase.contains("iteration-limited"))
    assert(result.answer.summary.contains("3"))
  }
  test("a false converged claim conflicts with the stored iteration-limited membership") {
    val c = claim(
      Vector(n("size", "3"), f("converged", true), n("iterations", "3")),
      Vector(communityItem.evidenceId),
      RuntimeClaimType.Community
    )
    rejected(verify(Vector(c), bundle(Vector(communityItem))))
  }
  test("approximate component distance remains separate from exact researcher counts") {
    val c = claim(
      Vector(
        n("effectiveDiameterP90", "4.0"),
        f("approximate", true),
        f("distanceP90Approximate", true),
        t("distanceMethod", "sampled-bfs")
      ),
      Vector(estimate.evidenceId),
      RuntimeClaimType.Metric,
      Vector(component),
      template = Some("metric-v1")
    )
    val result = verify(Vector(c), bundle(Vector(estimate)))
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.toLowerCase.contains("approximate"))
    assert(result.answer.summary.contains("4.0"))
    assert(!result.answer.summary.toLowerCase.contains("iteration-limited"))
  }
  test("P90 cannot be claimed as an exact graph distance") {
    val c = claim(
      Vector(n("effectiveDiameterP90", "4.0"), f("approximate", false)),
      Vector(estimate.evidenceId),
      RuntimeClaimType.Metric,
      Vector(component)
    )
    rejected(verify(Vector(c), bundle(Vector(estimate))))
  }
  test("stored distance sampling details are verified field by field") {
    val c = claim(
      Vector(
        n("sampleSourceCount", "2"),
        n("reachedPairCount", "7"),
        n("seed", "12"),
        n("meanDistance", "2.1"),
        f("approximate", true)
      ),
      Vector(estimate.evidenceId),
      RuntimeClaimType.Metric,
      Vector(component)
    )
    val result = verify(Vector(c), bundle(Vector(estimate)))
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    val wrong =
      c.copy(runtime = c.runtime.map(_.copy(values = Vector(n("sampleSourceCount", "999")))))
    rejected(verify(Vector(wrong), bundle(Vector(estimate))))
  }
  test("bridge scores require the exact stored value rather than degree as substitute evidence") {
    val positive = claim(
      Vector(
        n("crossCommunityDegree", "1"),
        n("participationCoefficient", "0.4444444444444444"),
        f("converged", false),
        n("iterations", "3")
      ),
      Vector(bridgeItem.evidenceId),
      RuntimeClaimType.Bridge
    )
    assert(
      verify(
        Vector(positive),
        bundle(Vector(bridgeItem))
      ).verification.claims.head.verdict == ClaimVerdict.Verified
    )
    rejected(
      verify(
        Vector(
          positive.copy(runtime =
            positive.runtime.map(_.copy(values = Vector(n("participationCoefficient", "3"))))
          )
        ),
        bundle(Vector(bridgeItem))
      )
    )
  }
  test("stored publication titles and work IDs are checked without permitting invented titles") {
    val c = claim(
      Vector(t("title", "Independent G1 w1")),
      Vector(publication.evidenceId),
      RuntimeClaimType.Publication,
      Vector(work)
    )
    assert(
      verify(
        Vector(c),
        bundle(Vector(publication))
      ).verification.claims.head.verdict == ClaimVerdict.Verified
    )
    val wrong =
      c.copy(runtime = c.runtime.map(_.copy(values = Vector(t("title", "Invented paper title")))))
    rejected(verify(Vector(wrong), bundle(Vector(publication))))
  }

  Vector(
    "Ada Example has broad collaboration.",
    "There are 3 collaborations.",
    "Use researcher:dblp:123 as proof.",
    "There are three collaborators.",
    "Alice invented the result."
  ).foreach { unsafe =>
    test(s"interpretation with a name number or identifier is rejected: $unsafe") {
      val result = verify(Vector(claim()), interpretation = unsafe)
      assert(!result.interpretationAccepted)
      assert(!result.answer.summary.contains(unsafe))
      assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    }
  }
  test(
    "a known researcher name cannot pass interpretation merely because it is a generic allowed word"
  ) {
    val knownMay = candidate.copy(displayName = "May")
    val result = verify(
      Vector(claim()),
      bundle(candidates = Vector(knownMay)),
      "may reflect collaboration breadth."
    )
    assert(!result.interpretationAccepted)
    assert(!result.answer.summary.contains("may reflect collaboration breadth."))
  }
  test(
    "contradictory cited stored values cannot be resolved by accepting whichever value matches"
  ) {
    val other = RuntimeEvidenceIds
      .bind(
        metric.copy(runtime =
          metric.runtime.map(r =>
            r.copy(
              values =
                r.values.filterNot(_.field == "publicationCount") :+ n("publicationCount", "4")
            )
          )
        )
      )
      .toOption
      .get
    val c = claim(evidenceIds = Vector(metric.evidenceId, other.evidenceId))
    val result = verify(Vector(c), bundle(Vector(metric, other)))
    assert(result.verification.claims.head.verdict == ClaimVerdict.Conflicting)
    assert(result.answer.claims.isEmpty)
  }
  test("a found path cannot be verified from a hop count when its cited hop evidence is absent") {
    val route = Vector(
      a,
      IndependentRuntime9BFixture.id("C"),
      IndependentRuntime9BFixture.id("D"),
      IndependentRuntime9BFixture.id("F"),
      g
    )
    val pathItem = evidence(
      "path",
      Vector(
        t("pathStatus", "Found"),
        ids("orderedResearcherIds", route),
        ids(
          "edgeIds",
          Vector(
            IndependentRuntime9BFixture.edge("A", "C").edgeId,
            IndependentRuntime9BFixture.edge("C", "D").edgeId,
            IndependentRuntime9BFixture.edge("D", "F").edgeId,
            IndependentRuntime9BFixture.edge("F", "G").edgeId
          )
        ),
        ids("hopEvidenceIds", Vector("evidence:edge:" + ("f" * 64))),
        n("hopCount", "4")
      ),
      subjects = route,
      evidenceType = EvidenceType.GraphPath,
      path = Some(route)
    )
    val c =
      claim(Vector(n("hopCount", "4")), Vector(pathItem.evidenceId), RuntimeClaimType.Path, route)
    rejected(verify(Vector(c), bundle(Vector(pathItem), candidates = Vector.empty)))
  }

  test("the literal four-hop G1 path is verified with complete cited hop support") {
    val input = IndependentRuntime9BFixture.input(QueryOperation.ShortestPath, "A", "G")
    val found = new PathFinderAgent(
      new IndependentRuntime9BFixture.Graph,
      IndependentRuntime9BFixture.metricStore(),
      IndependentRuntime9BFixture.artifacts(),
      config
    ).run(input)
    val RetrievalResult.Ready(out) = found: @unchecked
    val pathItem = out.items.find(_.evidenceType == EvidenceType.GraphPath).get
    val route = Vector("A", "C", "D", "F", "G").map(IndependentRuntime9BFixture.id)
    val c = claim(
      Vector(n("hopCount", "4"), ids("orderedResearcherIds", route)),
      out.items.map(_.evidenceId),
      RuntimeClaimType.Path,
      route
    )
    val result = new ClaimVerificationAgent(config).verify(
      input.plan,
      bundle(out.items, candidates = IndependentRuntime9BFixture.candidates("A", "G")),
      proposal(Vector(c))
    )
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.contains("4"))
    val bad = c.copy(runtime = c.runtime.map(_.copy(values = Vector(n("hopCount", "3")))))
    val wrong = new ClaimVerificationAgent(config).verify(
      input.plan,
      bundle(out.items, candidates = IndependentRuntime9BFixture.candidates("A", "G")),
      proposal(Vector(bad))
    )
    rejected(wrong)
  }
  test("total-author conversion is verified only when explicitly requested by the plan") {
    val prepared = RuntimeEvidenceIds
      .bind(
        metric.copy(runtime =
          metric.runtime.map(r =>
            r.copy(
              values = r.values ++ Vector(
                n("maximumTotalAuthors", "3"),
                t("authorCountConversion", "stored maximum coauthors + 1")
              )
            )
          )
        )
      )
      .toOption
      .get
    val c = claim(
      Vector(
        n("maximumTotalAuthors", "3"),
        t("authorCountConversion", "stored maximum coauthors + 1")
      ),
      Vector(prepared.evidenceId)
    )
    rejected(verify(Vector(c), bundle(Vector(prepared))))
    val requested = plan.copy(runtime = plan.runtime.map(_.copy(authorCountConversion = true)))
    val result = new ClaimVerificationAgent(config).verify(
      requested,
      bundle(Vector(prepared)),
      proposal(Vector(c))
    )
    assert(result.verification.claims.head.verdict == ClaimVerdict.Verified)
    assert(result.answer.summary.contains("3"))
    assert(result.answer.summary.contains("coauthors + 1"))
  }
  test("repeated collaboration requires the per-edge joint publication count") {
    val input = IndependentRuntime9BFixture.input(QueryOperation.DirectCoauthors, "A")
    val RetrievalResult.Ready(out) = new PathFinderAgent(
      new IndependentRuntime9BFixture.Graph,
      IndependentRuntime9BFixture.metricStore(),
      IndependentRuntime9BFixture.artifacts(),
      config
    ).run(input): @unchecked
    val edge = out.items
      .find(i =>
        i.evidenceType == EvidenceType.CoauthorEdge &&
          i.runtime.get.subjectIds.toSet == Set(a, b)
      )
      .get
    val c = claim(
      Vector(n("jointPublicationCount", "3")),
      Vector(edge.evidenceId),
      RuntimeClaimType.Path,
      edge.runtime.get.subjectIds
    )
    assert(
      new ClaimVerificationAgent(config)
        .verify(input.plan, bundle(out.items), proposal(Vector(c)))
        .verification
        .claims
        .head
        .verdict == ClaimVerdict.Verified
    )
    val borrowed = c.copy(evidenceIds = Vector(metric.evidenceId))
    rejected(verify(Vector(borrowed)))
  }

}
