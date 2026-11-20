package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite

/** P3 and P4 of the Session 1 query failures. Direct-coauthor and shortest-path answers abstained
  * with `essential-evidence-context-budget` because the model context carried every candidate's
  * full provenance and every per-work edge row against a 4096-byte budget. These tests run the real
  * retrieval agents, evidence builder, synthesis agent and verifier on production-shaped IDs.
  */
class CoauthorScaleSpec extends AnyFunSuite {
  private def assets(cfg: RuntimeConfig) = {
    val root = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .get
    RuntimePromptAssets.fromDirectory(root, cfg).toOption.get
  }

  /** Selects every claim of the request scaffold, as the prompt asks a model to do. */
  private final class SelectAll(cfg: RuntimeConfig) extends LlmClient {
    var requests = Vector.empty[StructuredLlmRequest]
    def complete(request: StructuredLlmRequest): LlmResult = {
      requests :+= request
      val ids = ujson.Arr.from(ujson.read(request.userData)("claimScaffold").arr.map(_("claimId")))
      LlmResult.Output(
        ujson
          .Obj(
            "schemaVersion" -> cfg.synthesisSchemaVersion,
            "claims" -> ujson.Arr(),
            "selectedClaimIds" -> ids,
            "narrativeClaimIds" -> ids,
            "interpretation" -> "",
            "uncertainty" -> "Echo model."
          )
          .render(),
        LlmUsage(None, None),
        cfg.model.modelId,
        cfg.model.modelVersion
      )
    }
  }

  private def cfgWith(
      limit: Int,
      budget: Int = Runtime9BG1Fixture.config.retrieval.contextTokenBudget
  ) = {
    val base = Runtime9BG1Fixture.config
    base.copy(retrieval = base.retrieval.copy(graphLimit = limit, contextTokenBudget = budget))
  }

  private def retrieve(
      fx: CoauthorScaleFixture,
      plan: QueryPlan,
      names: Seq[String],
      cfg: RuntimeConfig
  ): (RetrievalInput, RetrievalResult) = {
    val input = RetrievalInput(plan, fx.candidates(names*))
    (input, new PathFinderAgent(fx.graph(), fx.metricStore(), fx.artifacts(), cfg).run(input))
  }
  private def build(
      input: RetrievalInput,
      result: RetrievalResult,
      cfg: RuntimeConfig
  ): EvidenceBuildResult = result match {
    case RetrievalResult.Ready(o) =>
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, cfg)
        .build("query:scale", input, Vector(o))
    case other => fail(s"retrieval failed: $other")
  }
  private def bundleOf(r: EvidenceBuildResult): EvidenceBundle = r match {
    case EvidenceBuildResult.Persisted(b) => b
    case other                            => fail(s"evidence build failed: $other")
  }

  /** Full chain; returns the bundle, the verified answer and the model request. */
  private def answer(
      fx: CoauthorScaleFixture,
      op: QueryOperation,
      window: String,
      limit: Int,
      names: String*
  ) = {
    val cfg = cfgWith(limit)
    val plan = fx.plan(op, window, limit, names*)
    val (input, result) = retrieve(fx, plan, names, cfg)
    val bundle = bundleOf(build(input, result, cfg))
    val model = new SelectAll(cfg)
    val proposal =
      new AnswerSynthesisAgent(model, cfg, assets(cfg)).synthesize(plan, bundle) match {
        case SynthesisResult.Proposed(p) => p
        case other                       => fail(s"synthesis failed: $other")
      }
    val verified = new ClaimVerificationAgent(cfg).verify(plan, bundle, proposal)
    (bundle, verified, model.requests.head)
  }

  private def assertAllVerified(v: VerifiedAnswer): Unit = {
    val bad = v.verification.claims.filter(_.verdict != ClaimVerdict.Verified)
    assert(bad.isEmpty, bad.toString)
    assert(v.answer.claims.nonEmpty)
    assert(v.verification.overallStatus == VerificationStatus.Verified)
  }
  private def claimValue(v: VerifiedAnswer, field: String): Option[RuntimeClaimValue] =
    v.answer.claims.flatMap(_.runtime.toVector.flatMap(_.values)).find(_.field == field)

  test("P4 reproduction: a one-hop path with 18 joint works and production-sized identities") {
    // Session 1 shape (Hugues Fauconnier / Carole Delporte-Gallet): 23-ref identities, 18 joint works.
    val fx = new CoauthorScaleFixture(3, i => if (i == 0) 18 else 1)
    val cfg = cfgWith(25)
    val plan = fx.plan(QueryOperation.ShortestPath, "all-years", 25, fx.hubName, fx.coauthorName(1))
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName, fx.coauthorName(1)), cfg)
    assert(cfg.retrieval.contextTokenBudget == 4096)
    val built = build(input, result, cfg)
    assert(built.isInstanceOf[EvidenceBuildResult.Persisted], built.toString)
    val (bundle, verified, _) =
      answer(fx, QueryOperation.ShortestPath, "all-years", 25, fx.hubName, fx.coauthorName(1))
    assert(bundle.items.count(_.evidenceType == EvidenceType.CoauthorEdge) == 1)
    assertAllVerified(verified)
    assert(claimValue(verified, "hopCount").flatMap(_.number).contains("1"))
  }

  test("P4 reproduction: a two-hop path between researchers of different hub rows is answered") {
    val fx = new CoauthorScaleFixture(6)
    val (bundle, verified, _) = answer(
      fx,
      QueryOperation.ShortestPath,
      "all-years",
      25,
      fx.coauthorName(1),
      fx.coauthorName(4)
    )
    assert(bundle.items.count(_.evidenceType == EvidenceType.CoauthorEdge) == 2)
    assertAllVerified(verified)
  }

  test("the rendered identity omits provenance lists that stay in the persisted bundle") {
    val fx = new CoauthorScaleFixture(3)
    val plan = fx.plan(QueryOperation.ShortestPath, "all-years", 25, fx.hubName, fx.coauthorName(1))
    val cfg = cfgWith(25)
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName, fx.coauthorName(1)), cfg)
    val bundle = bundleOf(build(input, result, cfg))
    val rendered = ujson.read(
      EvidenceContext
        .render(bundle)
        .stripPrefix("<untrusted_evidence_json>\n")
        .stripSuffix("\n</untrusted_evidence_json>")
    )
    val identity = rendered("identities").arr.head
    assert(identity("researcherId").str == fx.hub)
    assert(identity("displayName").str == fx.hubName)
    assert(!identity.obj.contains("sourceIds") && !identity.obj.contains("evidenceRefs"))
    val kept = bundle.runtime.get.resolvedCandidates.head
    assert(kept.sourceIds.size == 5 && kept.evidenceRefs.size == 23)
  }

  test("the full identity JSON of two production-sized candidates exceeds the pre-fix budget") {
    // The pre-fix render emitted these fields for every candidate; two Session 1 sized identities
    // (5 source ids, 23 references) alone are larger than contextTokenBudget = 4096.
    val fx = new CoauthorScaleFixture(3)
    val full = ujson.Arr.from(fx.candidates(fx.hubName, fx.coauthorName(1)).map { c =>
      ujson.Obj(
        "researcherId" -> c.researcherId,
        "displayName" -> c.displayName,
        "sourceIds" -> ujson.Arr.from(c.sourceIds),
        "evidenceRefs" -> ujson.Arr.from(c.evidenceRefs),
        "runs" -> ujson.Arr(0),
        "confidence" -> ujson.Null
      )
    })
    assert(full.render().getBytes(UTF_8).length > 4096)
  }

  test("a truncated provenance summary stays in the model view; the provenance lists do not") {
    val fx = new CoauthorScaleFixture(3)
    val cfg = cfgWith(25)
    val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
    val input = RetrievalInput(plan, Vector(fx.truncatedCandidate(fx.hub, fx.hubName)))
    val result = new PathFinderAgent(fx.graph(), fx.metricStore(), fx.artifacts(), cfg).run(input)
    val bundle = bundleOf(build(input, result, cfg))
    val identity = ujson
      .read(
        EvidenceContext
          .render(bundle)
          .stripPrefix("<untrusted_evidence_json>\n")
          .stripSuffix("\n</untrusted_evidence_json>")
      )("identities")
      .arr
      .head
    assert(!identity.obj.contains("sourceIds") && !identity.obj.contains("evidenceRefs"))
    assert(identity("provenanceSummary")("truncated").bool)
    assert(identity("provenanceSummary")("sourceIdCount").num == 40)
    val kept = bundle.runtime.get.resolvedCandidates.head
    assert(kept.sourceIds.size == 16 && kept.provenanceSummary.exists(_.truncated))
  }

  test("a stored total that disagrees with the returned page fails the stage") {
    // (rows in the graph, metric distinct count, page limit): the page exceeds the total, an
    // untruncated page differs from the total, and a truncated page exceeds the total.
    for ((rows, metric, limit) <- Seq((25, 22, 40), (25, 30, 40), (35, 20, 25))) {
      val fx = new CoauthorScaleFixture(rows, hubMetricDistinct = Some(metric))
      val cfg = cfgWith(limit)
      val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", limit, fx.hubName)
      val (_, result) = retrieve(fx, plan, Seq(fx.hubName), cfg)
      assert(
        result == RetrievalResult.Failed("path", "coauthor-count-mismatch"),
        s"rows=$rows metric=$metric limit=$limit: $result"
      )
    }
    // Agreement is accepted, truncated or not.
    for ((rows, limit) <- Seq((22, 40), (35, 25))) {
      val fx = new CoauthorScaleFixture(rows)
      val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", limit, fx.hubName)
      val (_, result) = retrieve(fx, plan, Seq(fx.hubName), cfgWith(limit))
      assert(result.isInstanceOf[RetrievalResult.Ready], result.toString)
    }
  }

  private def semanticItem(fx: CoauthorScaleFixture, text: String): EvidenceItem =
    RuntimeEvidenceIds
      .bind(
        EvidenceItem(
          "chunk:" + "0" * 64,
          SchemaVersions.domain,
          EvidenceType.TextChunk,
          None,
          "s3://synthetic-scale/context.json",
          None,
          None,
          score = 0.0,
          text = Some(text),
          provenance = fx.provenance,
          runtime = Some(
            RuntimeEvidence(
              Vector(fx.hub),
              Vector("all-years"),
              None,
              fx.run,
              Vector(RuntimeClaimValue("kind", text = Some("semantic"))),
              Vector(SummarySourceRef("synthetic-scale", "context", "text")),
              None,
              None,
              approximate = false,
              descriptive = true
            )
          )
        )
      )
      .toOption
      .get

  test("fused mode: descriptive text cannot use the room scaled for deterministic list rows") {
    val fx = new CoauthorScaleFixture(22)
    val cfg = cfgWith(25)
    val graphPlan = fx.plan(QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
    val plan =
      graphPlan.copy(runtime = graphPlan.runtime.map(_.copy(retrievalMode = RetrievalMode.Fused)))
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName), cfg)
    val rows = result match {
      case RetrievalResult.Ready(o) => o
      case other                    => fail(other.toString)
    }
    val semantic = RetrievalOutput(
      "semantic",
      Vector(semanticItem(fx, "descriptive " * 5000)),
      truncated = true
    )
    val bundle = bundleOf(
      new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, cfg)
        .build("query:fused", input, Vector(semantic, rows))
    )
    val deterministic = bundle.items.filterNot(_.runtime.get.descriptive)
    val descriptive = bundle.items.filter(_.runtime.get.descriptive)
    val base = cfg.retrieval.contextTokenBudget
    val detBytes = EvidenceContext.tokenUpperBound(deterministic, input.candidates)
    val totalBytes = EvidenceContext.render(bundle).getBytes(UTF_8).length
    // The list-operation ceiling is far above deterministic bytes plus the base budget, so the
    // descriptive cap, not the ceiling, is what bounds the excerpt.
    assert(detBytes + base < ContextBudget.forPlan(plan, cfg))
    assert(deterministic.size == 23 && descriptive.size == 1)
    assert(descriptive.head.text.exists(t => t.nonEmpty && t.length < 60000))
    assert(totalBytes <= detBytes + base, s"total=$totalBytes det=$detBytes base=$base")
    assert(bundle.runtime.get.truncated)
  }

  for {
    n <- Seq(22, 35)
    window <- Seq("all-years", "2015-2019")
  } test(s"P3: direct coauthors of a researcher with $n coauthors, window $window, verify") {
    val fx = new CoauthorScaleFixture(n)
    // `answer` copies the shared config and sets its graph limit to this value, so every coauthor
    // is returned in one page; the deployed core graphLimit (25) is not changed by this test.
    val limit = 40
    val (bundle, verified, request) =
      answer(fx, QueryOperation.DirectCoauthors, window, limit, fx.hubName)
    assertAllVerified(verified)
    val expected = fx.degree(fx.hub, window)
    assert(expected > 0)
    val direct = bundle.items.find(i => ClaimContract.kind(i) == "direct-coauthors").get
    val values = direct.runtime.get.values.map(v => v.field -> v).toMap
    assert(values("returnedCount").number.contains(expected.toString))
    assert(values("distinctCoauthorCount").number.contains(expected.toString))
    assert(values("truncated").flag.contains(false))
    assert(claimValue(verified, "returnedCount").flatMap(_.number).contains(expected.toString))
    // every coauthor edge row is in the bundle and in the verified answer
    assert(bundle.items.count(_.evidenceType == EvidenceType.CoauthorEdge) == expected)
    assert(verified.answer.claims.size == expected + 1)
    val total = Vector(request.userData, request.systemPrompt, request.schemaJson)
      .map(_.getBytes(UTF_8).length)
      .sum
    assert(total <= Runtime9BG1Fixture.config.effectiveByteLimits.requestBytes)
  }

  test("P3: 35 coauthors at the default graph limit 25 verify 'showing 25 of 35'") {
    val fx = new CoauthorScaleFixture(35)
    assert(Runtime9BG1Fixture.config.retrieval.graphLimit == 25)
    val (bundle, verified, _) =
      answer(fx, QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
    assertAllVerified(verified)
    val direct = bundle.items.find(i => ClaimContract.kind(i) == "direct-coauthors").get
    val values = direct.runtime.get.values.map(v => v.field -> v).toMap
    assert(values("returnedCount").number.contains("25"))
    assert(values("distinctCoauthorCount").number.contains("35"))
    assert(values("truncated").flag.contains(true))
    assert(claimValue(verified, "distinctCoauthorCount").flatMap(_.number).contains("35"))
    assert(claimValue(verified, "truncated").flatMap(_.flag).contains(true))
    assert(bundle.runtime.get.truncated)
  }

  test(
    "an incorrect total cannot be claimed: the verifier rejects a tampered distinctCoauthorCount"
  ) {
    val fx = new CoauthorScaleFixture(35)
    val cfg = cfgWith(25)
    val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName), cfg)
    val bundle = bundleOf(build(input, result, cfg))
    val direct = bundle.items.find(i => ClaimContract.kind(i) == "direct-coauthors").get
    val claim = AnswerClaim(
      "claim:tampered",
      SchemaVersions.domain,
      "x",
      Vector(direct.evidenceId),
      VerificationStatus.Unverified,
      None,
      plan.provenance,
      Some(
        TypedAnswerClaim(
          RuntimeClaimType.Path,
          direct.runtime.get.subjectIds,
          Vector(RuntimeClaimValue("distinctCoauthorCount", number = Some("25"))),
          direct.runtime.get.windowIds,
          "path-v1"
        )
      )
    )
    val v = new ClaimVerificationAgent(cfg)
      .verify(plan, bundle, SynthesisProposal(Vector(claim), Vector("claim:tampered"), "", "u"))
    assert(v.answer.claims.isEmpty)
    assert(v.verification.claims.head.verdict == ClaimVerdict.Conflicting)
  }

  test(
    "an absurdly small configured budget still abstains cleanly for direct coauthors and paths"
  ) {
    val fx = new CoauthorScaleFixture(22)
    for (budget <- Seq(1, 30)) {
      val cfg = cfgWith(25, budget)
      val direct = fx.plan(QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
      val (i1, r1) = retrieve(fx, direct, Seq(fx.hubName), cfg)
      assert(
        build(i1, r1, cfg) == EvidenceBuildResult.Missing("essential-evidence-context-budget")
      )
      val path =
        fx.plan(QueryOperation.ShortestPath, "all-years", 25, fx.hubName, fx.coauthorName(1))
      val (i2, r2) = retrieve(fx, path, Seq(fx.hubName, fx.coauthorName(1)), cfg)
      assert(
        build(i2, r2, cfg) == EvidenceBuildResult.Missing("essential-evidence-context-budget")
      )
    }
  }

  test("an absurd page size is refused with a closed abstention, never a partial bundle") {
    // 100 coauthors with 40 joint works each: the per-operation ceiling and the persisted-bundle
    // byte bound both apply; whichever trips first must be a Missing, not a Failed or a truncation.
    val fx = new CoauthorScaleFixture(100, _ => 40)
    val cfg = cfgWith(100)
    val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", 100, fx.hubName)
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName), cfg)
    val store = new InMemoryIndexedEvidenceBundleStore
    val built = result match {
      case RetrievalResult.Ready(o) =>
        new EvidenceBuilderAgent(store, cfg).build("query:absurd", input, Vector(o))
      case other => fail(other.toString)
    }
    built match {
      case EvidenceBuildResult.Missing(reason) =>
        assert(
          Set("essential-evidence-context-budget", "evidence-bundle-byte-budget")(reason),
          reason
        )
      case other => fail(s"expected a Missing abstention, got $other")
    }
  }

  test("scaffold edge claims drop per-work detail before any whole claim is dropped") {
    val fx = new CoauthorScaleFixture(22)
    val cfg = cfgWith(25)
    val plan = fx.plan(QueryOperation.DirectCoauthors, "all-years", 25, fx.hubName)
    val (input, result) = retrieve(fx, plan, Seq(fx.hubName), cfg)
    val bundle = bundleOf(build(input, result, cfg))
    val full = ClaimScaffold.build(plan, bundle, Int.MaxValue)
    val fullBytes = ClaimScaffold.bytes(full)
    val compact = ClaimScaffold.build(plan, bundle, fullBytes - 1)
    assert(compact.size == full.size)
    assert(ClaimScaffold.bytes(compact) < fullBytes)
    val edgeFields = compact.filter(_.claimId.startsWith("claim:edge:")).flatMap(_.claim.values)
    assert(edgeFields.nonEmpty)
    assert(!edgeFields.exists(v => v.field == "workIds" || v.field.startsWith("year:")))
    assert(edgeFields.exists(_.field == "jointPublicationCount"))
    // A tighter bound still drops whole claims, never part of one.
    val tight = ClaimScaffold.build(plan, bundle, ClaimScaffold.bytes(compact) / 2)
    assert(tight.nonEmpty && tight.size < compact.size)
    assert(tight == compact.take(tight.size))
  }

  test("the per-operation ceiling never lets the context exceed the request bound") {
    val cfg = cfgWith(25)
    val plan =
      new CoauthorScaleFixture(1).plan(QueryOperation.DirectCoauthors, "all-years", 25, "x")
    val ceiling = ContextBudget.forPlan(plan, cfg)
    assert(ceiling > cfg.retrieval.contextTokenBudget)
    assert(ceiling * 3 <= cfg.effectiveByteLimits.requestBytes)
    assert(
      ContextBudget.persistedBundleBytes(plan, cfg) > cfg.effectiveByteLimits.persistedBundleBytes
    )
    val other = plan.copy(operations = Vector(QueryOperation.ComponentLookup))
    assert(
      ContextBudget.persistedBundleBytes(other, cfg) == cfg.effectiveByteLimits.persistedBundleBytes
    )
    assert(ContextBudget.forPlan(other, cfg) == cfg.retrieval.contextTokenBudget)
  }

  test("L2: the synthesis agent refuses retired or mismatched synthesis labels") {
    val cfg = Runtime9BG1Fixture.config
    val ok = assets(cfg)
    new AnswerSynthesisAgent(new SelectAll(cfg), cfg, ok)
    assert(cfg.synthesisPromptVersion == SynthesisAssetVersions.promptVersion)
    val retired = cfg.copy(synthesisPromptVersion = "synthesis-v1")
    intercept[IllegalArgumentException](
      new AnswerSynthesisAgent(new SelectAll(retired), retired, ok)
    )
    val mismatched = cfg.copy(synthesisSchemaVersion = "scholarchain.runtime.synthesis.v9")
    intercept[IllegalArgumentException](
      new AnswerSynthesisAgent(new SelectAll(mismatched), mismatched, ok)
    )
  }
}
