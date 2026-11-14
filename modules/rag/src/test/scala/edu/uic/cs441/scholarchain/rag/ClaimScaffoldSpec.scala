package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import scala.util.chaining.*

/** The scaffold is derived from ClaimContract, the verifier's own field contract. These tests run a
  * fake model that copies every scaffold claim verbatim through the real synthesis agent and the
  * real verifier, so any drift between the two fails here.
  */
class ClaimScaffoldSpec extends AnyFunSuite {
  import Runtime9BG1Fixture.*
  import RuntimeEvidenceItems.{flag, ids, number, text}

  private val cfg = config
  private def ready(r: RetrievalResult): RetrievalOutput = r match {
    case RetrievalResult.Ready(o) => o
    case other                    => fail(s"Expected retrieval evidence, got $other")
  }
  private def metricAgent = new CollaborationMetricsAgent(metricStore(), artifacts(), cfg)
  private def pathAgent = new PathFinderAgent(graph(), metricStore(), artifacts(), cfg)
  private def communityAgent = new CommunityAnalystAgent(graph(), metricStore(), artifacts(), cfg)
  private def estimateAgent = {
    val original = StorageResult.value(metricStore().get(id("A"), "all-years")).get
    val estimate = PathLengthEstimate(context, component("A"), "sampled-bfs", 2, 7L, 2.1, 4.0, 12L)
    val qualifications = ujson.read(original.qualificationsJson)
    qualifications("pathLengthEstimate") = upickle.default.writeJs(estimate)
    val store = new InMemoryResearcherMetricStore
    assert(
      StorageResult.successful(
        store.put(original.copy(qualificationsJson = qualifications.render()))
      )
    )
    new CollaborationMetricsAgent(store, artifacts(), cfg)
  }
  private def assets = {
    val root = Iterator
      .iterate(Path.of("").toAbsolutePath)(_.getParent)
      .takeWhile(_ != null)
      .map(_.resolve("prompts"))
      .find(Files.isDirectory(_))
      .get
    RuntimePromptAssets.fromDirectory(root, cfg).toOption.get
  }
  private def build(i: RetrievalInput, outputs: RetrievalOutput*): EvidenceBundle =
    new EvidenceBuilderAgent(new InMemoryIndexedEvidenceBundleStore, cfg)
      .build("query:scaffold", i, outputs.toVector) match {
      case EvidenceBuildResult.Persisted(b) => b
      case other                            => fail(other.toString)
    }

  private def output(body: ujson.Obj): LlmResult = LlmResult.Output(
    body.render(),
    LlmUsage(None, None),
    cfg.model.modelId,
    cfg.model.modelVersion
  )

  /** Fake model over its own input scaffold. `select` (default) mirrors the prompt: ids only, empty
    * claims. Otherwise it copies every scaffold claim verbatim (the backward-compatible shape).
    */
  private final class EchoModel(interpretation: String = "", select: Boolean = true)
      extends LlmClient {
    var requests = Vector.empty[StructuredLlmRequest]
    def complete(request: StructuredLlmRequest): LlmResult = {
      requests :+= request
      val scaffold = ujson.read(request.userData)("claimScaffold")
      val idsOf = ujson.Arr.from(scaffold.arr.map(_("claimId")))
      output(
        ujson.Obj(
          "schemaVersion" -> cfg.synthesisSchemaVersion,
          "claims" -> (if (select) ujson.Arr() else scaffold),
          "selectedClaimIds" -> (if (select) idsOf else ujson.Arr()),
          "narrativeClaimIds" -> idsOf,
          "interpretation" -> interpretation,
          "uncertainty" -> "Echo model."
        )
      )
    }
  }

  /** Fake model whose answer is built from the request scaffold by `f`. */
  private final class ScriptedModel(f: ujson.Arr => ujson.Obj) extends LlmClient {
    def complete(request: StructuredLlmRequest): LlmResult =
      output(f(ujson.read(request.userData)("claimScaffold").arr.pipe(ujson.Arr.from(_))))
  }
  private def scaffoldOf(plan: QueryPlan, bundle: EvidenceBundle) =
    ClaimScaffold.build(plan, bundle, cfg.retrieval.contextTokenBudget)

  /** Echo every scaffold claim, then require each one to be VERIFIED by the real verifier. */
  private def assertAllVerified(
      plan: QueryPlan,
      bundle: EvidenceBundle,
      expectedClaims: Int = -1,
      interpretation: String = ""
  ): VerifiedAnswer = {
    val expectedScaffold = scaffoldOf(plan, bundle)
    assert(expectedScaffold.nonEmpty, "scaffold must not be empty")
    if (expectedClaims >= 0) assert(expectedScaffold.size == expectedClaims)
    val verifiedBySelection = verifyWith(plan, bundle, new EchoModel(interpretation, true))
    // The verbatim-copy shape stays accepted and yields the same verified claims.
    val verifiedByCopy = verifyWith(plan, bundle, new EchoModel(interpretation, false))
    assert(
      verifiedByCopy.answer.claims.map(_.claimId) ==
        verifiedBySelection.answer.claims.map(_.claimId)
    )
    assert(verifiedBySelection.answer.claims.map(_.claimId) == expectedScaffold.map(_.claimId))
    verifiedBySelection
  }

  private def verifyWith(plan: QueryPlan, bundle: EvidenceBundle, model: LlmClient) = {
    val expected = scaffoldOf(plan, bundle)
    val proposal = new AnswerSynthesisAgent(model, cfg, assets).synthesize(plan, bundle) match {
      case SynthesisResult.Proposed(p) => p
      case other                       => fail(other.toString)
    }
    assert(proposal.claims.map(_.claimId) == expected.map(_.claimId))
    assert(proposal.narrativeClaimIds == expected.map(_.claimId))
    assert(proposal.ignoredSelectedIds == 0)
    val verified = new ClaimVerificationAgent(cfg).verify(plan, bundle, proposal)
    val bad = verified.verification.claims.filter(_.verdict != ClaimVerdict.Verified)
    assert(bad.isEmpty, bad.toString)
    assert(verified.answer.claims.size == expected.size)
    assert(verified.verification.overallStatus == VerificationStatus.Verified)
    verified
  }

  test(
    "direct coauthors: the 2-coauthor scaffold carries exact template, subjects, window, fields"
  ) {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val claims = scaffoldOf(i.plan, bundle)
    assert(claims.size == 3, claims.toString)
    val direct = claims.head
    assert(direct.claim.claimType == RuntimeClaimType.Path)
    assert(direct.claim.templateId == "path-v1")
    assert(direct.claim.subjectIds == Vector(id("A")))
    assert(direct.claim.windowIds == Vector("all-years"))
    assert(direct.evidenceIds == Vector(bundle.items.head.evidenceId))
    val values = direct.claim.values.map(v => v.field -> v).toMap
    assert(values("coauthorIds").ids.get.toSet == Set(id("B"), id("C")))
    assert(values("returnedCount").number.contains("2"))
    assert(values("truncated").flag.contains(false))
    assert(!values.contains("kind"))
    val edges = claims.tail
    assert(edges.forall(_.claim.claimType == RuntimeClaimType.Path))
    assert(
      edges.map(_.claim.values.find(_.field == "jointPublicationCount").get.number.get).toSet ==
        Set("3", "1")
    )
    assertAllVerified(i.plan, bundle, 3)
  }

  test("the model input carries the scaffold and stays inside the request bound") {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val model = new EchoModel
    new AnswerSynthesisAgent(model, cfg, assets).synthesize(i.plan, bundle)
    val request = model.requests.head
    val data = ujson.read(request.userData)
    assert(data("claimScaffold").arr.size == 3)
    val scaffoldBytes = data("claimScaffold").render().getBytes(UTF_8).length
    assert(scaffoldBytes <= cfg.retrieval.contextTokenBudget)
    val total = Vector(request.userData, request.systemPrompt, request.schemaJson)
      .map(_.getBytes(UTF_8).length)
      .sum
    assert(total <= cfg.effectiveByteLimits.requestBytes)
  }

  test("path found, disconnected and no-path-within-limit scaffold claims verify") {
    val found = input(QueryOperation.ShortestPath, "A", "G")
    assertAllVerified(found.plan, build(found, ready(pathAgent.run(found))))
    val disconnected = input(QueryOperation.ShortestPath, "A", "H")
    assertAllVerified(
      disconnected.plan,
      build(disconnected, ready(pathAgent.run(disconnected))),
      1
    )
    val bounded = input(QueryOperation.ShortestPath, "A", "G")
    val limited = bounded.copy(plan = bounded.plan.copy(maxPathDepth = 2))
    assertAllVerified(limited.plan, build(limited, ready(pathAgent.run(limited))), 1)
  }

  test("metric, total-author conversion, distance estimate and ranking scaffold claims verify") {
    val component = input(QueryOperation.ComponentLookup, "A")
    val metrics =
      assertAllVerified(component.plan, build(component, ready(metricAgent.run(component))))
    assert(metrics.answer.claims.head.runtime.get.claimType == RuntimeClaimType.Metric)
    val team = input(QueryOperation.MaximumTeamSize, "A")
    val plain = scaffoldOf(team.plan, build(team, ready(metricAgent.run(team))))
    assert(!plain.flatMap(_.claim.values).exists(v => ClaimContract.conversionFields(v.field)))
    val converted =
      team.copy(plan =
        team.plan.copy(runtime = team.plan.runtime.map(_.copy(authorCountConversion = true)))
      )
    val withConversion = build(converted, ready(metricAgent.run(converted)))
    assert(
      scaffoldOf(converted.plan, withConversion)
        .flatMap(_.claim.values)
        .exists(_.field == "maximumTotalAuthors")
    )
    assertAllVerified(converted.plan, withConversion)
    val estimate = ready(estimateAgent.run(component))
    val estimated = assertAllVerified(component.plan, build(component, estimate), 2)
    assert(
      estimated.answer.claims.exists(
        _.runtime.get.values.exists(v => v.field == "approximate" && v.flag.contains(true))
      )
    )
    val ranking = input(QueryOperation.ResearcherRanking)
    val rankingPlan = ranking.plan.copy(graphLimit = 2)
    val rankingInput = ranking.copy(plan = rankingPlan)
    val ranked =
      assertAllVerified(rankingPlan, build(rankingInput, ready(metricAgent.run(rankingInput))))
    assert(ranked.answer.claims.forall(_.runtime.get.claimType == RuntimeClaimType.Ranking))
  }

  test("community, bridge and bridge ranking scaffold claims verify with qualifications") {
    val comparison = input(QueryOperation.CommunityComparison, "C", "D")
    val bundle = build(comparison, ready(communityAgent.run(comparison)))
    val answer = assertAllVerified(comparison.plan, bundle)
    val types = answer.answer.claims.map(_.runtime.get.claimType).toSet
    assert(types == Set(RuntimeClaimType.Community, RuntimeClaimType.Bridge))
    assert(
      answer.answer.claims.exists(
        _.runtime.get.values.exists(v => v.field == "converged" && v.flag.contains(false))
      )
    )
    val ranking = input(QueryOperation.BridgeRanking)
    val rankingInput = ranking.copy(plan = ranking.plan.copy(graphLimit = 2))
    assertAllVerified(
      rankingInput.plan,
      build(rankingInput, ready(communityAgent.run(rankingInput)))
    )
  }

  /** Temporal, identity and publication items have no retrieval agent in the offline fixtures, so
    * representative items are built through the production item constructor.
    */
  test("temporal, identity and publication evidence items yield verifying scaffold claims") {
    val windows = Vector("through-2009", "all-years")
    val base = input(QueryOperation.TemporalComparison, "A")
    val plan = base.plan.copy(runtime =
      base.plan.runtime.map(_.copy(windowIds = windows.take(1), comparisonWindowIds = windows))
    )
    val request = base.copy(plan = plan)
    val temporal = RuntimeEvidenceItems.make(
      request,
      "temporal",
      Vector(id("A")),
      windows,
      Runtime9BG1Fixture.run,
      Vector(
        flag("fromPresent", true),
        number("deltaDistinctCoauthors", 2),
        text("previousCommunityId", community("A")),
        flag("converged:all-years", false),
        number("iterations:all-years", 3)
      ),
      Vector(RuntimeEvidenceItems.ref("metrics/type=temporal_changes", id("A"))),
      converged = Some(false),
      iterations = Some(3),
      sourceContext = Some(context.copy(windowId = Some("all-years")))
    )
    val identity = RuntimeEvidenceItems.make(
      request,
      "identity",
      Vector(id("A")),
      Vector("all-years"),
      Runtime9BG1Fixture.run,
      Vector(text("displayName", "A"), ids("sourceIds", Vector("synthetic:A"))),
      Vector(RuntimeEvidenceItems.ref("nodes/type=researcher", id("A"))),
      sourceContext = Some(context)
    )
    val publication = RuntimeEvidenceItems.make(
      request,
      "publication",
      Vector(id("A")),
      Vector("all-years"),
      Runtime9BG1Fixture.run,
      Vector(text("title", "Synthetic paper"), number("year", 2015)),
      Vector(RuntimeEvidenceItems.ref("nodes/type=work", id("A"))),
      sourceContext = Some(context)
    )
    val bundle =
      build(request, RetrievalOutput("community", Vector(temporal, identity, publication)))
    // Plan windows are requested for every item; identity/publication use the first window only.
    val widened =
      plan.copy(runtime = plan.runtime.map(_.copy(windowIds = Vector("all-years", "through-2009"))))
    val answer = assertAllVerified(widened, bundle, 3)
    assert(
      answer.answer.claims.map(_.runtime.get.claimType).toSet ==
        Set(RuntimeClaimType.Temporal, RuntimeClaimType.Identity, RuntimeClaimType.Publication)
    )
  }

  test("an empty interpretation is accepted and no interpretation-rejected is produced") {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val answer = assertAllVerified(i.plan, bundle, interpretation = "")
    assert(answer.interpretationAccepted)
    assert(!answer.answer.summary.contains("Interpretation"))
  }

  test("scaffold is empty in vector mode, for unrequested windows and for descriptive evidence") {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val vector =
      bundle.copy(runtime = bundle.runtime.map(_.copy(retrievalMode = RetrievalMode.Vector)))
    assert(ClaimScaffold.build(i.plan, vector, 4096).isEmpty)
    val unrequested =
      i.plan.copy(runtime = i.plan.runtime.map(_.copy(windowIds = Vector("through-2009"))))
    assert(ClaimScaffold.build(unrequested, bundle, 4096).isEmpty)
    val descriptive = bundle.copy(items =
      bundle.items.map(x => x.copy(runtime = x.runtime.map(_.copy(descriptive = true))))
    )
    assert(ClaimScaffold.build(i.plan, descriptive, 4096).isEmpty)
  }

  test("scaffold bytes are bounded by whole claims and by the remaining request room") {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val full = scaffoldOf(i.plan, bundle)
    assert(full.size == 3)
    val one = ClaimScaffold.bytes(full.take(1))
    val limited = ClaimScaffold.build(i.plan, bundle, one + 1)
    assert(limited.size == 1 && limited.head == full.head)
    assert(ClaimScaffold.bytes(limited) <= one + 1)
    assert(ClaimScaffold.build(i.plan, bundle, 10).isEmpty)
    // Shrink the request limit so only the fixed input fits: the call still proceeds, scaffold empty.
    val fixed = {
      val m = new EchoModel
      new AnswerSynthesisAgent(m, cfg, assets).synthesize(i.plan, bundle)
      val r = m.requests.head
      val data = ujson.read(r.userData); data.obj.remove("claimScaffold")
      data.render().getBytes(UTF_8).length + r.systemPrompt.getBytes(UTF_8).length +
        r.schemaJson.getBytes(UTF_8).length
    }
    val tight = cfg.copy(byteLimits = Some(cfg.effectiveByteLimits.copy(requestBytes = fixed + 80)))
    val m = new EchoModel
    val result = new AnswerSynthesisAgent(m, tight, assets).synthesize(i.plan, bundle)
    assert(result.isInstanceOf[SynthesisResult.Proposed], result.toString)
    assert(ujson.read(m.requests.head.userData)("claimScaffold").arr.isEmpty)
  }

  test("a model that ignores the scaffold with an invented claim type is still rejected") {
    val i = input(QueryOperation.DirectCoauthors, "A")
    val bundle = build(i, ready(pathAgent.run(i)))
    val good = scaffoldOf(i.plan, bundle).head
    val wrong = AnswerClaim(
      "claim:wrong",
      SchemaVersions.domain,
      "x",
      good.evidenceIds,
      VerificationStatus.Unverified,
      None,
      i.plan.provenance,
      Some(good.claim.copy(claimType = RuntimeClaimType.Identity, templateId = "identity-v1"))
    )
    val result = new ClaimVerificationAgent(cfg)
      .verify(i.plan, bundle, SynthesisProposal(Vector(wrong), Vector("claim:wrong"), "", "u"))
    assert(result.verification.claims.head.verdict != ClaimVerdict.Verified)
  }

  private def coauthorCase = {
    val i = input(QueryOperation.DirectCoauthors, "A")
    (i, build(i, ready(pathAgent.run(i))))
  }
  private def answer(claims: ujson.Value, selected: Seq[String], narrative: Seq[String]) =
    ujson.Obj(
      "schemaVersion" -> cfg.synthesisSchemaVersion,
      "claims" -> claims,
      "selectedClaimIds" -> ujson.Arr.from(selected),
      "narrativeClaimIds" -> ujson.Arr.from(narrative),
      "interpretation" -> "",
      "uncertainty" -> "u"
    )
  private def propose(plan: QueryPlan, bundle: EvidenceBundle, model: LlmClient) =
    new AnswerSynthesisAgent(model, cfg, assets).synthesize(plan, bundle) match {
      case SynthesisResult.Proposed(p) => p
      case other                       => fail(other.toString)
    }

  test("the model input lists the three scaffold ids it is asked to select") {
    val (i, bundle) = coauthorCase
    val model = new EchoModel
    val p = propose(i.plan, bundle, model)
    assert(p.claims.size == 3 && p.narrativeClaimIds.size == 3)
    val sent = ujson.read(model.requests.head.userData)("claimScaffold").arr.map(_("claimId").str)
    assert(sent.toVector == p.claims.map(_.claimId))
    assert(model.requests.head.systemPrompt.contains("selectedClaimIds"))
  }

  test("unknown selected ids are ignored and counted; nothing is verified for them") {
    val (i, bundle) = coauthorCase
    val model = new ScriptedModel(s => {
      val first = s.arr.head("claimId").str
      answer(
        ujson.Arr(),
        Seq(first, "claim:invented:9", "claim:path:99"),
        Seq(first, "claim:invented:9")
      )
    })
    val p = propose(i.plan, bundle, model)
    assert(p.claims.size == 1 && p.ignoredSelectedIds == 2)
    assert(p.narrativeClaimIds == p.claims.map(_.claimId))
    val verified = new ClaimVerificationAgent(cfg).verify(i.plan, bundle, p)
    assert(verified.verification.claims.map(_.verdict) == Vector(ClaimVerdict.Verified))
    assert(!verified.verification.claims.exists(_.claimId.contains("invented")))
    val none = new ScriptedModel(_ => answer(ujson.Arr(), Seq("claim:invented:9"), Seq.empty))
    val q = propose(i.plan, bundle, none)
    assert(q.claims.isEmpty && q.narrativeClaimIds.isEmpty && q.ignoredSelectedIds == 1)
  }

  test("a claim both copied and selected is de-duplicated and the scaffold version wins") {
    val (i, bundle) = coauthorCase
    val expected = scaffoldOf(i.plan, bundle)
    val model = new ScriptedModel(s => {
      val head = s.arr.head
      // The copied claim is tampered; the scaffold claim of the same id must replace it.
      val copy = ujson.read(head.render())
      copy("values").arr.head("number") = "999"
      val ids = s.arr.map(_("claimId").str).toSeq
      answer(ujson.Arr(copy), ids.take(2), Seq.empty)
    })
    val p = propose(i.plan, bundle, model)
    assert(p.claims.map(_.claimId) == expected.take(2).map(_.claimId))
    assert(p.claims.map(_.runtime.get) == expected.take(2).map(_.claim))
    assert(p.narrativeClaimIds == p.claims.map(_.claimId))
    val verified = new ClaimVerificationAgent(cfg).verify(i.plan, bundle, p)
    assert(verified.verification.claims.forall(_.verdict == ClaimVerdict.Verified))
  }

  test("a tampered copy that is not selected still reaches the verifier and is rejected") {
    val (i, bundle) = coauthorCase
    val model = new ScriptedModel(s => {
      val copy = ujson.read(s.arr.head.render())
      copy("values").arr.foreach { v =>
        if (v("field").str == "returnedCount") v("number") = "999"
      }
      answer(ujson.Arr(copy), Seq.empty, Seq(copy("claimId").str))
    })
    val p = propose(i.plan, bundle, model)
    val verified = new ClaimVerificationAgent(cfg).verify(i.plan, bundle, p)
    assert(verified.verification.claims.head.verdict != ClaimVerdict.Verified)
  }

  test("synthesis schema accepts selectedClaimIds and still rejects unknown properties") {
    val schema = assets.synthesisSchema
    val ok = answer(ujson.Arr(), Seq("claim:path:1"), Seq("claim:path:1"))
    assert(RuntimeJsonSchema.validate(schema, ok).isRight)
    val legacy = ujson.read(ok.render()); legacy.obj.remove("selectedClaimIds")
    assert(RuntimeJsonSchema.validate(schema, legacy).isRight)
    val extra = ujson.read(ok.render()); extra("verdict") = "VERIFIED"
    assert(RuntimeJsonSchema.validate(schema, extra).isLeft)
    val badType = ujson.read(ok.render()); badType("selectedClaimIds") = ujson.Arr(1)
    assert(RuntimeJsonSchema.validate(schema, badType).isLeft)
    val dup = answer(ujson.Arr(), Seq("a", "a"), Seq.empty)
    assert(RuntimeJsonSchema.validate(schema, dup).isLeft)
    val long = answer(ujson.Arr(), Seq("x" * 129), Seq.empty)
    assert(RuntimeJsonSchema.validate(schema, long).isLeft)
  }
}
