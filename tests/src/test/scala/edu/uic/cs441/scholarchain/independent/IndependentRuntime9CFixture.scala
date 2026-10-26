package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*
import edu.uic.cs441.scholarchain.storage.*

/** Synthetic, hand-stated facts; expected values never come from the verifier under test. */
private[independent] object IndependentRuntime9CFixture {
  val config = IndependentRuntime9BFixture.config.copy(evidenceOnly = false)
  val runId = IndependentRuntime9BFixture.runId
  val provenance = IndependentRuntime9BFixture.provenance
  val a = IndependentRuntime9BFixture.id("A")
  val b = IndependentRuntime9BFixture.id("B")
  val g = IndependentRuntime9BFixture.id("G")
  val component = IndependentRuntime9BFixture.component("A")
  val community = IndependentRuntime9BFixture.community("A")
  val work = IndependentPhase6G1.canonicalWorkId("w1")
  val candidate = IndependentRuntime9BFixture.candidates("A").head.copy(displayName = "Ada Example")
  val plan = IndependentRuntime9BFixture
    .plan(QueryOperation.ComponentLookup, Vector("A"))
    .copy(
      question = "Show stored collaboration metrics for A",
      runtime = Some(
        RuntimeQueryOptions(
          researcherNames = Vector("A"),
          windowIds = Vector("all-years"),
          retrievalMode = RetrievalMode.Graph,
          evidenceOnly = false
        )
      )
    )
  def assets: RuntimePromptAssets = RuntimePromptAssets
    .fromDirectory(
      IndependentRuntime9AFixture.root.resolve("prompts"),
      config
    )
    .toOption
    .get
  def n(field: String, value: String): RuntimeClaimValue =
    RuntimeClaimValue(field, number = Some(value))
  def t(field: String, value: String): RuntimeClaimValue =
    RuntimeClaimValue(field, text = Some(value))
  def f(field: String, value: Boolean): RuntimeClaimValue =
    RuntimeClaimValue(field, flag = Some(value))
  def ids(field: String, value: Vector[String]): RuntimeClaimValue =
    RuntimeClaimValue(field, ids = Some(value))

  def evidence(
      kind: String,
      values: Vector[RuntimeClaimValue],
      subjects: Vector[String] = Vector(a),
      windows: Vector[String] = Vector("all-years"),
      approximate: Boolean = false,
      descriptive: Boolean = false,
      converged: Option[Boolean] = None,
      iterations: Option[Int] = None,
      evidenceType: EvidenceType = EvidenceType.ResearcherProfile,
      excerpt: Option[String] = None,
      path: Option[Vector[String]] = None,
      locator: Option[MetricEvidenceLocator] = None
  ): EvidenceItem = RuntimeEvidenceIds
    .bind(
      EvidenceItem(
        "profile:" + ("0" * 64),
        SchemaVersions.domain,
        evidenceType,
        None,
        "synthetic://independent-9c/" + kind,
        None,
        path,
        locator,
        None,
        1.0,
        excerpt,
        provenance,
        Some(
          RuntimeEvidence(
            subjects,
            windows,
            Option.when(!descriptive)(IndependentRuntime9BFixture.policy),
            runId,
            t("kind", kind) +: values,
            Vector(SummarySourceRef("synthetic-independent-9c", subjects.mkString("|"), "*")),
            converged,
            iterations,
            approximate,
            descriptive
          )
        )
      )
    )
    .toOption
    .get

  val metric = evidence(
    "metrics",
    Vector(
      n("publicationCount", "3"),
      n("distinctCoauthorCount", "2"),
      n("totalCoauthorOccurrences", "4"),
      n("weightedDegree", "4"),
      n("averageCoauthorsPerPaper", "1.3333333333333333"),
      n("maximumCoauthorsOnOnePaper", "2"),
      n("coreness", "2"),
      t("componentId", component),
      t("communityId", community),
      ids("maxTeamWorkIds", Vector(work))
    ),
    evidenceType = EvidenceType.Metric,
    locator = Some(
      MetricEvidenceLocator(
        a,
        CollaborationMetric.DistinctCoauthorCount,
        1000,
        9999,
        IndependentRuntime9BFixture.policy
      )
    ),
    converged = Some(false),
    iterations = Some(3)
  )

  val communityItem = evidence(
    "community",
    Vector(
      t("communityId", community),
      n("size", "3"),
      t("communityQualification", "iteration-limited")
    ),
    converged = Some(false),
    iterations = Some(3)
  )
  val bridgeItem = evidence(
    "bridge",
    Vector(
      t("communityId", community),
      n("crossCommunityDegree", "1"),
      n("crossCommunityWeight", "1"),
      n("communitiesConnected", "1"),
      n("participationCoefficient", "0.4444444444444444"),
      n("distinctCoauthorCount", "3"),
      t("communityQualification", "iteration-limited")
    ),
    converged = Some(false),
    iterations = Some(3)
  )
  val estimate = evidence(
    "distance-estimate",
    Vector(
      t("componentId", component),
      n("effectiveDiameterP90", "4.0"),
      t("distanceMethod", "sampled-bfs"),
      f("distanceP90Approximate", true),
      n("sampleSourceCount", "2"),
      n("reachedPairCount", "7"),
      n("meanDistance", "2.1"),
      n("seed", "12")
    ),
    subjects = Vector(component),
    approximate = true
  )
  val publication = evidence(
    "publication",
    Vector(
      t("title", "Independent G1 w1"),
      t("workId", work),
      n("year", "2015")
    ),
    subjects = Vector(work),
    evidenceType = EvidenceType.WorkMetadata
  )
  val semantic = evidence(
    "semantic",
    Vector(t("usage", "descriptive-only")),
    descriptive = true,
    evidenceType = EvidenceType.TextChunk,
    excerpt = Some("Untrusted descriptive context, not graph support.")
  )

  def bundle(
      items: Vector[EvidenceItem] = Vector(metric),
      mode: RetrievalMode = RetrievalMode.Graph,
      candidates: Vector[ResearcherCandidate] = Vector(candidate)
  ): EvidenceBundle = EvidenceBundle(
    "bundle:independent-9c",
    SchemaVersions.domain,
    "query:independent-9c",
    items,
    candidates.map(_.researcherId),
    items.filter(_.evidenceType == EvidenceType.Metric).map(_.evidenceId),
    None,
    "Synthetic independent fixture with explicit source qualifications.",
    provenance,
    Some(
      RuntimeBundleContext(
        items.filterNot(_.runtime.get.descriptive).map(_.evidenceId),
        items.filter(_.runtime.get.descriptive).map(_.evidenceId),
        items.filterNot(_.runtime.get.descriptive).map(_.runtime.get.runId).distinct,
        items.flatMap(_.runtime.get.metricVersion).distinct,
        mode,
        None,
        false,
        candidates
      )
    )
  )

  def claim(
      fields: Vector[RuntimeClaimValue] = Vector(n("publicationCount", "3")),
      evidenceIds: Vector[String] = Vector(metric.evidenceId),
      claimType: RuntimeClaimType = RuntimeClaimType.Metric,
      subjects: Vector[String] = Vector(a),
      windows: Vector[String] = Vector("all-years"),
      claimId: String = "claim-exact",
      template: Option[String] = None,
      prose: String = "An untrusted proposal sentence."
  ): AnswerClaim = AnswerClaim(
    claimId,
    SchemaVersions.domain,
    prose,
    evidenceIds,
    VerificationStatus.Unverified,
    None,
    provenance,
    Some(
      TypedAnswerClaim(
        claimType,
        subjects,
        fields,
        windows,
        template.getOrElse(claimType.wire.toLowerCase(java.util.Locale.ROOT) + "-v1")
      )
    )
  )
  def proposal(
      claims: Vector[AnswerClaim],
      interpretation: String = "",
      narrative: Option[Vector[String]] = None
  ): SynthesisProposal = SynthesisProposal(
    claims,
    narrative.getOrElse(claims.map(_.claimId)),
    interpretation,
    "Synthetic fixture only."
  )
  def output(
      claims: Vector[AnswerClaim],
      interpretation: String = "",
      narrative: Option[Vector[String]] = None
  ): String = ujson
    .Obj(
      "schemaVersion" -> config.synthesisSchemaVersion,
      "claims" -> ujson.Arr.from(claims.map { claim =>
        val typed = claim.runtime.get
        ujson.Obj(
          "claimId" -> claim.claimId,
          "claimType" -> typed.claimType.wire,
          "subjectIds" -> ujson.Arr.from(typed.subjectIds),
          "values" -> ujson.Arr.from(
            typed.values.map(v =>
              ujson.Obj(
                "field" -> v.field,
                "number" -> v.number.map(ujson.Str(_)).getOrElse(ujson.Null),
                "text" -> v.text.map(ujson.Str(_)).getOrElse(ujson.Null),
                "ids" -> v.ids.map(xs => ujson.Arr.from(xs)).getOrElse(ujson.Null),
                "flag" -> v.flag.map(ujson.Bool(_)).getOrElse(ujson.Null)
              )
            )
          ),
          "evidenceIds" -> ujson.Arr.from(claim.evidenceIds),
          "windowIds" -> ujson.Arr.from(typed.windowIds),
          "templateId" -> typed.templateId
        )
      }),
      "narrativeClaimIds" -> ujson.Arr.from(narrative.getOrElse(claims.map(_.claimId))),
      "interpretation" -> interpretation,
      "uncertainty" -> "Synthetic fixture only."
    )
    .render()
  def model(json: String): LlmResult = LlmResult.Output(
    json,
    LlmUsage(Some(11), Some(7)),
    config.model.modelId,
    config.model.modelVersion
  )
}
