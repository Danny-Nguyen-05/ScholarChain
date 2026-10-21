package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite

/** Independently authored synthetic fixtures test shared 5A contracts only. These are neither
  * matching results nor human labels, and do not establish dataset or model accuracy.
  */
class IndependentResolutionContractSpec extends AnyFunSuite {
  private val schema = ResolutionContracts.schemaVersion
  private val run = "run:11111111-1111-4111-8111-111111111111"
  private val digest = "a" * 64
  private val doi = "10.5555/independent-resolution"
  private val workId = s"work:doi:$doi"
  private val orcidA = "0000-0002-1825-0097"
  private val orcidC = "0000-0001-5109-3700"
  private val fixtureNote = "Synthetic independent contract fixture; identity remains unconfirmed."

  private def provenance(source: SourceType, native: String, snapshot: String): Provenance =
    Provenance(
      SchemaVersions.domain,
      source,
      native,
      None,
      snapshot,
      Some("2026-10-15"),
      None,
      run,
      Vector(fixtureNote)
    )

  private def work(
      source: SourceType,
      native: String,
      snapshot: String = "independent-snapshot-a",
      withAuthor: Boolean = true
  ): WorkRecord = {
    val p = provenance(source, native, snapshot)
    val name = "Alex Example"
    val authors =
      if (withAuthor)
        Vector(
          AuthorMention(
            StableIds.mentionId(source, native, 1),
            SchemaVersions.domain,
            source,
            native,
            1,
            name,
            TextNorm.personName(name),
            None,
            None,
            MentionIdentityStatus.NameOnlyUnconfirmed,
            None,
            fixtureNote,
            p
          )
        )
      else Vector.empty
    WorkRecord(
      SchemaVersions.domain,
      workId,
      source,
      native,
      None,
      "Synthetic distributed storage study",
      TextNorm.title("Synthetic distributed storage study"),
      Some(2021),
      None,
      Some(doi),
      None,
      None,
      None,
      authors,
      None,
      p
    )
  }

  private val dblp = work(SourceType.Dblp, "conf/independent/A")
  private val openAlex = work(SourceType.OpenAlex, "W700000001")

  private def ref(p: Provenance): ResolutionObservationRef =
    ResolutionObservationRef(p.source, p.sourceRecordId, p.datasetSnapshot)
  private def endpoint(w: WorkRecord): ResolutionEndpoint =
    ResolutionEndpoint.Work(ref(w.provenance), w.workId)
  private def mention(w: WorkRecord): ResolutionEndpoint =
    ResolutionEndpoint.Mention(ref(w.provenance), w.authors.head.mentionId)
  private def pair(a: ResolutionEndpoint, b: ResolutionEndpoint): ResolutionPair =
    ResolutionIds.pair(ResolutionIds.entityType(a), a, b).toOption.get
  private def context(
      works: Vector[WorkRecord] = Vector(dblp, openAlex),
      profiles: Vector[OrcidProfileRecord] = Vector.empty,
      activities: Vector[OrcidActivityRecord] = Vector.empty
  ): ResolutionValidationContext = {
    val result = ResolutionValidationContext.create(works, profiles, activities)
    assert(result.isRight, result.toString)
    result.toOption.get
  }

  private def assertMissingBinding(
      result: Either[Vector[DomainViolation], ResolutionPair]
  ): Unit = {
    assert(result.isLeft)
    assert(result.left.toOption.get.exists(_.message.contains("missing source observation")))
  }

  test("same DOI observations stay distinct and cannot satisfy a missing native key or snapshot") {
    val ctx = context()
    val original = pair(endpoint(dblp), endpoint(openAlex))
    assert(dblp.workId == openAlex.workId)
    assert(ResolutionValidation.check(original, ctx).isRight)
    assert(ResolutionIds.endpointId(original.left) != ResolutionIds.endpointId(original.right))

    val absentNative = openAlex.copy(
      sourceRecordId = "W700000002",
      provenance = openAlex.provenance.copy(sourceRecordId = "W700000002")
    )
    assertMissingBinding(
      ResolutionValidation.check(pair(endpoint(dblp), endpoint(absentNative)), ctx)
    )
    val absentSnapshot =
      openAlex.copy(provenance = openAlex.provenance.copy(datasetSnapshot = "not-loaded"))
    assertMissingBinding(
      ResolutionValidation.check(pair(endpoint(dblp), endpoint(absentSnapshot)), ctx)
    )
  }

  test("snapshot-free mention IDs cannot borrow authors from another snapshot or parent work") {
    val later =
      work(SourceType.Dblp, dblp.sourceRecordId, "independent-snapshot-b", withAuthor = false)
    val ctx = context(Vector(dblp, later, openAlex))
    val original = pair(mention(dblp), mention(openAlex))
    assert(ResolutionValidation.check(original, ctx).isRight)

    val reusedId = ResolutionEndpoint.Mention(ref(later.provenance), dblp.authors.head.mentionId)
    assertMissingBinding(ResolutionValidation.check(pair(reusedId, mention(openAlex)), ctx))
    val nonexistentOrdinal = ResolutionEndpoint.Mention(
      ref(dblp.provenance),
      StableIds.mentionId(dblp.source, dblp.sourceRecordId, 2)
    )
    assertMissingBinding(
      ResolutionValidation.check(pair(nonexistentOrdinal, mention(openAlex)), ctx)
    )
    val wrongParent =
      ResolutionEndpoint.Mention(ref(openAlex.provenance), dblp.authors.head.mentionId)
    assert(ResolutionIds.pair(ResolutionEntityType.Researcher, wrongParent, mention(dblp)).isLeft)
  }

  test(
    "an actual ORCID work activity without DOI is eligible but supplies no publication authors"
  ) {
    def activity(kind: OrcidActivityKind, code: Int): OrcidActivityRecord = {
      val native = s"/$orcidA/${kind.wire}/$code"
      OrcidActivityRecord(
        SchemaVersions.domain,
        orcidA,
        kind,
        native,
        Some("Synthetic source activity"),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        fixtureNote,
        provenance(SourceType.Orcid, native, "independent-orcid")
      )
    }
    val publication = activity(OrcidActivityKind.Work, 1)
    val employment = activity(OrcidActivityKind.Employment, 2)
    val ctx = context(activities = Vector(publication, employment))
    val workActivity = ResolutionEndpoint.OrcidWorkActivity(ref(publication.provenance), None)
    assert(ResolutionValidation.check(pair(workActivity, endpoint(dblp)), ctx).isRight)
    val nonwork = ResolutionEndpoint.OrcidWorkActivity(ref(employment.provenance), None)
    assert(ResolutionIds.pair(ResolutionEntityType.Work, nonwork, endpoint(dblp)).isLeft)

    // A valid work-activity observation is still not a full WorkRecord.
    val manufacturedWork = ResolutionEndpoint.Work(ref(publication.provenance), workId)
    assertMissingBinding(ResolutionValidation.check(pair(manufacturedWork, endpoint(dblp)), ctx))
    val missingActivity = ResolutionEndpoint.OrcidWorkActivity(
      ref(publication.provenance).copy(sourceRecordId = s"/$orcidA/work/3"),
      None
    )
    assertMissingBinding(ResolutionValidation.check(pair(missingActivity, endpoint(dblp)), ctx))
  }

  test(
    "pair deduplication preserves changed snapshot identity even when all bibliographic IDs match"
  ) {
    val later = work(SourceType.OpenAlex, openAlex.sourceRecordId, "independent-snapshot-b")
    val ctx = context(Vector(dblp, openAlex, later))
    val original = pair(endpoint(dblp), endpoint(openAlex))
    val reversed = pair(endpoint(openAlex), endpoint(dblp))
    val changed = pair(endpoint(dblp), endpoint(later))
    assert(original == reversed)
    assert(original.pairId != changed.pairId)
    assert(Vector(original, reversed, changed).map(_.pairId).distinct.size == 2)
    assert(ResolutionValidation.check(changed, ctx).isRight)
  }

  private def identify(d: ResolutionDecision): ResolutionDecision =
    d.copy(decisionId = ResolutionIds.decisionId(d))

  private def audit(outcome: MatchOutcome): ResolutionDecision = {
    val p = pair(endpoint(dblp), endpoint(openAlex))
    identify(
      ResolutionDecision(
        schema,
        "",
        p,
        MatchDecision(
          SchemaVersions.domain,
          ResolutionIds.endpointId(p.left),
          ResolutionIds.endpointId(p.right),
          Vector.empty,
          outcome,
          0.31,
          Vector("SYNTHETIC_CONTRACT"),
          "independent-policy-v1",
          run,
          fixtureNote,
          provenance(SourceType.ScholarChain, p.pairId, "independent-derived")
        ),
        Vector.empty,
        "independent-features-v1",
        Vector.empty,
        ResolutionDecisionPath.Scored,
        ResolutionConfidenceSemantics.UncalibratedScore,
        None,
        digest,
        digest,
        digest,
        Vector("synthetic:source"),
        "2026-10-15T16:00:00Z",
        None
      )
    )
  }

  test(
    "only accepted audits authorize links and timestamp changes must renew the decision identity"
  ) {
    val ctx = context()
    MatchOutcome.values.foreach { outcome =>
      val d = audit(outcome)
      assert(ResolutionValidation.check(d, ctx).isRight)
      val link = ResolutionAcceptedLink(
        schema,
        d.pair,
        d.decisionId,
        d.decision.policyVersion,
        d.policyHash,
        run,
        d.decision.provenance
      )
      assert(ResolutionValidation.check(link, d, ctx).isRight == (outcome == MatchOutcome.Accepted))
    }
    val d = audit(MatchOutcome.Accepted)
    val later = d.copy(decidedAtUtc = "2026-10-15T16:01:00Z")
    assert(ResolutionValidation.check(later, ctx).isLeft)
    assert(ResolutionValidation.check(identify(later), ctx).isRight)
    val localTime = identify(d.copy(decidedAtUtc = "2026-10-15T11:00:00"))
    assert(ResolutionValidation.check(localTime, ctx).isLeft)
  }

  test("LLM reported confidence is required independently of the system score and UTC audit") {
    val metadata = ResolutionAdjudication(
      digest,
      "synthetic-prompt-v1",
      digest,
      "synthetic-response-v1",
      "synthetic-fake",
      "synthetic-model",
      None,
      digest,
      digest,
      ResolutionAdjudicationMode.Fake,
      false,
      0.91,
      Vector("synthetic:source"),
      ResolutionPreAdjudication(Some(0.31), MatchOutcome.Unresolved, ResolutionDecisionPath.Scored)
    )
    val d = identify(
      audit(MatchOutcome.Unresolved).copy(
        decisionPath = ResolutionDecisionPath.LlmAdjudicated,
        adjudication = Some(metadata)
      )
    )
    assert(ResolutionValidation.check(d, context()).isRight)
    val decoded = CoreJson.parse[ResolutionDecision](CoreJson.compact(d)).toOption.get
    assert(decoded.decision.confidence == 0.31)
    assert(decoded.adjudication.get.reportedConfidence == 0.91)
    assert(decoded.confidenceSemantics == ResolutionConfidenceSemantics.UncalibratedScore)
    val missing = ujson.read(CoreJson.compact(d))
    missing("adjudication").obj.remove("reportedConfidence")
    assert(CoreJson.parse[ResolutionDecision](missing.render()).isLeft)
    val outOfRange = identify(d.copy(adjudication = Some(metadata.copy(reportedConfidence = 1.01))))
    assert(ResolutionValidation.check(outOfRange, context()).isLeft)
    Vector(
      ResolutionDecisionPath.Scored,
      ResolutionDecisionPath.ExactIdentifier,
      ResolutionDecisionPath.HardConflict
    ).foreach { path =>
      val outcome =
        if (path == ResolutionDecisionPath.HardConflict) MatchOutcome.Conflict
        else MatchOutcome.Unresolved
      val hiddenLlm = identify(
        d.copy(
          decisionPath = path,
          decision = d.decision.copy(decision = outcome)
        )
      )
      assert(ResolutionValidation.check(hiddenLlm, context()).isLeft)
    }
    Vector(MatchOutcome.Unresolved, MatchOutcome.Accepted, MatchOutcome.Rejected).foreach {
      outcome =>
        val finalLlm = identify(d.copy(decision = d.decision.copy(decision = outcome)))
        assert(ResolutionValidation.check(finalLlm, context()).isRight)
    }
    val modelConflict =
      identify(d.copy(decision = d.decision.copy(decision = MatchOutcome.Conflict)))
    assert(ResolutionValidation.check(modelConflict, context()).isLeft)
  }

  private def profile(orcid: String): OrcidProfileRecord = OrcidProfileRecord(
    SchemaVersions.domain,
    orcid,
    Some("Synthetic profile"),
    Vector.empty,
    Vector(ObservedIdentifier("orcid", orcid, IdentifierInterpretation.ValidatedExternal)),
    fixtureNote,
    provenance(SourceType.Orcid, orcid, "independent-orcid")
  )

  test("A-B and B-C admissibility cannot erase conflicting authoritative ORCIDs in A-B-C") {
    val pa = profile(orcidA)
    val pc = profile(orcidC)
    val a = ResolutionEndpoint.OrcidProfile(ref(pa.provenance), orcidA)
    val b = mention(dblp) // Explicitly covered despite having no authoritative identifier.
    val c = ResolutionEndpoint.OrcidProfile(ref(pc.provenance), orcidC)
    val ctx = context(profiles = Vector(pa, pc))
    val bundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Researcher,
      "independent-policy-v1",
      digest,
      Vector(a, b, c),
      Vector.empty,
      Vector(
        ResolutionIdentifierAssertion(
          a,
          ResolutionAuthorityNamespace.Orcid,
          orcidA,
          Vector("synthetic:profile-a")
        ),
        ResolutionIdentifierAssertion(
          c,
          ResolutionAuthorityNamespace.Orcid,
          orcidC,
          Vector("synthetic:profile-c")
        )
      )
    )
    def check(
        members: Vector[ResolutionEndpoint],
        constraints: ResolutionGroupingConstraints = bundle
    ) =
      ResolutionValidation.checkComponent(
        members,
        constraints,
        ctx,
        maxMembers = 3,
        maxConstraints = 10
      )

    assert(check(Vector(a, b)).isRight)
    assert(check(Vector(b, c)).isRight)
    assert(check(Vector(a, b, c)).isLeft)
    assert(check(Vector(a, b), bundle.copy(coveredEndpoints = Vector(a, c))).isLeft)
    val cannotLink = bundle.copy(
      cannotLinks =
        Vector(ResolutionCannotLink(pair(a, c), "SYNTHETIC_CONFLICT", Vector("synthetic:source")))
    )
    assert(check(Vector(a, b), cannotLink).isRight)
    assert(check(Vector(b, c), cannotLink).isRight)
    assert(check(Vector(a, b, c), cannotLink).isLeft)
  }

  private def researcherAuthorityBundle
      : (ResolutionGroupingConstraints, ResolutionValidationContext) = {
    val pa = profile(orcidA)
    val pc = profile(orcidC)
    val a = ResolutionEndpoint.OrcidProfile(ref(pa.provenance), orcidA)
    val c = ResolutionEndpoint.OrcidProfile(ref(pc.provenance), orcidC)
    val bundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Researcher,
      "independent-policy-v1",
      digest,
      Vector(a, mention(dblp), c),
      Vector.empty,
      Vector(
        ResolutionIdentifierAssertion(
          a,
          ResolutionAuthorityNamespace.Orcid,
          orcidA,
          Vector("synthetic:profile-a")
        ),
        ResolutionIdentifierAssertion(
          c,
          ResolutionAuthorityNamespace.Orcid,
          orcidC,
          Vector("synthetic:profile-c")
        )
      )
    )
    (bundle, context(profiles = Vector(pa, pc)))
  }

  private def validAuthorityJson(json: ujson.Value, ctx: ResolutionValidationContext): Boolean =
    CoreJson.parse[ResolutionGroupingConstraints](json.render()) match {
      case Left(_)       => false
      case Right(bundle) => ResolutionValidation.check(bundle, ctx).isRight
    }

  test(
    "B1 namespace aliases cannot split conflicting ORCID assertions across a transitive component"
  ) {
    val (bundle, ctx) = researcherAuthorityBundle
    val json = ujson.read(CoreJson.compact(bundle))
    json("authoritativeIdentifiers")(1)("namespace") = ujson.Str("ORCID")
    val result = CoreJson.parse[ResolutionGroupingConstraints](json.render()) match {
      case Left(_) => true
      case Right(decoded) =>
        ResolutionValidation.checkComponent(decoded.coveredEndpoints, decoded, ctx, 3, 10).isLeft
    }
    assert(result, "ORCID namespace casing must not bypass the canonical orcid conflict")
  }

  test("B1 authoritative namespaces are closed and entity typed at the serialized boundary") {
    val (bundle, ctx) = researcherAuthorityBundle
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    Vector(
      "ORCID",
      "Orcid",
      "researcher:orcid",
      "unknown-authority",
      "openalex",
      "openalex-author",
      "openalex-work",
      "dblp",
      "semantic-scholar",
      "repository-url"
    ).foreach { namespace =>
      val json = ujson.read(CoreJson.compact(bundle))
      json("authoritativeIdentifiers")(0)("namespace") = ujson.Str(namespace)
      assert(!validAuthorityJson(json, ctx), s"unsupported namespace accepted: $namespace")
    }
    val researcherDoi = ujson.read(CoreJson.compact(bundle))
    researcherDoi("authoritativeIdentifiers")(0)("namespace") = ujson.Str("doi")
    researcherDoi("authoritativeIdentifiers")(0)("value") = ujson.Str(doi)
    assert(
      !validAuthorityJson(researcherDoi, ctx),
      "DOI cannot be authoritative researcher identity"
    )

    val workBundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Work,
      "independent-policy-v1",
      digest,
      Vector(endpoint(dblp)),
      Vector.empty,
      Vector(
        ResolutionIdentifierAssertion(
          endpoint(dblp),
          ResolutionAuthorityNamespace.Orcid,
          orcidA,
          Vector("synthetic:source")
        )
      )
    )
    assert(
      ResolutionValidation.check(workBundle, context()).isLeft,
      "ORCID cannot be authoritative work identity"
    )
  }

  test("B1 authoritative values reject noncanonical ORCID and DOI spellings before grouping") {
    val (bundle, ctx) = researcherAuthorityBundle
    Vector(s"https://orcid.org/$orcidA", s" $orcidA", "0000-0002-1825-0098").foreach { value =>
      val json = ujson.read(CoreJson.compact(bundle))
      json("authoritativeIdentifiers")(0)("value") = ujson.Str(value)
      assert(!validAuthorityJson(json, ctx), s"noncanonical or invalid ORCID accepted: $value")
    }
    val workBundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Work,
      "independent-policy-v1",
      digest,
      Vector(endpoint(dblp)),
      Vector.empty,
      Vector(
        ResolutionIdentifierAssertion(
          endpoint(dblp),
          ResolutionAuthorityNamespace.Doi,
          doi,
          Vector("synthetic:source")
        )
      )
    )
    assert(ResolutionValidation.check(workBundle, context()).isRight)
    Vector(
      s"https://doi.org/$doi",
      "DOI:10.5555/INDEPENDENT-RESOLUTION",
      "10.5555/INDEPENDENT-RESOLUTION",
      "not-a-doi"
    ).foreach { value =>
      val json = ujson.read(CoreJson.compact(workBundle))
      json("authoritativeIdentifiers")(0)("value") = ujson.Str(value)
      assert(!validAuthorityJson(json, context()), s"noncanonical or invalid DOI accepted: $value")
    }
  }

  test("B1 arXiv authority accepts canonical base tokens and rejects versions or URI spellings") {
    val observed = dblp.copy(arxivId = Some("2101.00001v2"))
    val ctx = context(Vector(observed))
    val bundle = ResolutionGroupingConstraints(
      schema,
      ResolutionEntityType.Work,
      "independent-policy-v1",
      digest,
      Vector(endpoint(dblp)),
      Vector.empty,
      Vector(
        ResolutionIdentifierAssertion(
          endpoint(dblp),
          ResolutionAuthorityNamespace.Arxiv,
          "2101.00001",
          Vector("synthetic:source")
        ),
        ResolutionIdentifierAssertion(
          endpoint(observed),
          ResolutionAuthorityNamespace.Doi,
          doi,
          Vector("synthetic:source")
        )
      )
    )
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    val canonical = ujson.read(CoreJson.compact(bundle))
    assert(canonical("authoritativeIdentifiers")(0)("namespace").str == "arxiv")
    assert(validAuthorityJson(canonical, ctx))
    Vector("2101.00001v1", "arXiv:2101.00001", "https://arxiv.org/abs/2101.00001", " 2101.00001")
      .foreach { value =>
        val json = ujson.read(CoreJson.compact(bundle))
        json("authoritativeIdentifiers")(0)("value") = ujson.Str(value)
        assert(
          !validAuthorityJson(json, ctx),
          s"noncanonical arXiv authority accepted: $value"
        )
      }
  }

  test("B2 a canonical ORCID assertion must be grounded in its own profile observation") {
    val (bundle, ctx) = researcherAuthorityBundle
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    assert(ResolutionValidation.checkComponent(bundle.coveredEndpoints, bundle, ctx, 3, 10).isLeft)
    val misattributed = bundle.copy(authoritativeIdentifiers = bundle.authoritativeIdentifiers.map {
      assertion => assertion.copy(value = orcidC)
    })
    assert(
      ResolutionValidation.check(misattributed, ctx).isLeft,
      "a profile for ORCID A cannot assert ORCID C"
    )
    assert(
      ResolutionValidation
        .checkComponent(
          misattributed.coveredEndpoints,
          misattributed,
          ctx,
          3,
          10
        )
        .isLeft,
      "misattributed assertions must not suppress the source ORCID conflict"
    )
  }

  test("B2 work authority cannot invent an absent identifier or substitute a contradictory DOI") {
    def bundle(
        namespace: ResolutionAuthorityNamespace,
        value: String
    ): ResolutionGroupingConstraints =
      ResolutionGroupingConstraints(
        schema,
        ResolutionEntityType.Work,
        "independent-policy-v1",
        digest,
        Vector(endpoint(dblp)),
        Vector.empty,
        Vector(
          ResolutionIdentifierAssertion(
            endpoint(dblp),
            namespace,
            value,
            Vector("synthetic:source")
          )
        )
      )
    assert(
      ResolutionValidation.check(bundle(ResolutionAuthorityNamespace.Doi, doi), context()).isRight
    )
    assert(
      ResolutionValidation
        .check(
          bundle(ResolutionAuthorityNamespace.Doi, "10.5555/not-observed"),
          context()
        )
        .isLeft,
      "canonical syntax alone cannot ground a contradictory DOI"
    )
    assert(
      ResolutionValidation
        .check(
          bundle(ResolutionAuthorityNamespace.Arxiv, "2101.00001"),
          context()
        )
        .isLeft,
      "a work with no arXiv evidence cannot assert an arXiv identifier"
    )
  }

  test("N10 covered profiles cannot omit their own ORCIDs to evade a component conflict") {
    val (bundle, ctx) = researcherAuthorityBundle
    val omitted = bundle.copy(authoritativeIdentifiers = Vector.empty)
    assert(
      ResolutionValidation
        .checkComponent(
          omitted.coveredEndpoints,
          omitted,
          ctx,
          3,
          10
        )
        .isLeft,
      "coverage alone cannot erase both profiles' known authoritative ORCIDs"
    )
  }

  private def authorityBundle(
      entityType: ResolutionEntityType,
      endpoint: ResolutionEndpoint,
      facts: Vector[(ResolutionAuthorityNamespace, String)]
  ): ResolutionGroupingConstraints = ResolutionGroupingConstraints(
    schema,
    entityType,
    "independent-policy-v1",
    digest,
    Vector(endpoint),
    Vector.empty,
    facts.map { case (namespace, value) =>
      ResolutionIdentifierAssertion(endpoint, namespace, value, Vector("synthetic:source"))
    }
  )

  test("B2 mention grounding uses the selected member and accepts its raw ORCID URL") {
    val identified = dblp.authors.head.copy(
      observedOrcid = Some(s"https://orcid.org/$orcidA"),
      identityStatus = MentionIdentityStatus.ExternalIdentifierObserved
    )
    val observed = dblp.copy(authors = Vector(identified))
    val ep = mention(observed)
    val ctx = context(Vector(observed))
    val bundle = authorityBundle(
      ResolutionEntityType.Researcher,
      ep,
      Vector(ResolutionAuthorityNamespace.Orcid -> orcidA)
    )
    assert(ResolutionValidation.check(bundle, ctx).isRight)
    assert(
      ResolutionValidation.check(bundle.copy(authoritativeIdentifiers = Vector.empty), ctx).isLeft
    )
    val nameOnly = authorityBundle(
      ResolutionEntityType.Researcher,
      mention(openAlex),
      Vector(ResolutionAuthorityNamespace.Orcid -> orcidA)
    )
    assert(
      ResolutionValidation.check(nameOnly, context()).isLeft,
      "a same-named author on a different parent cannot borrow this member's ORCID"
    )
  }

  test("B2 all recognized work observations must be retained even when DOI values contradict") {
    val other = "10.5555/second-observed"
    val observed = openAlex.copy(observedIdentifiers =
      Vector(
        ObservedIdentifier(
          "openalex.doi",
          s"https://doi.org/${doi.toUpperCase(java.util.Locale.ROOT)}",
          IdentifierInterpretation.SourceObservation
        ),
        ObservedIdentifier(
          "openalex.ids.doi",
          s"https://doi.org/$other",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    val ctx = context(Vector(observed))
    val full = authorityBundle(
      ResolutionEntityType.Work,
      endpoint(observed),
      Vector(
        ResolutionAuthorityNamespace.Doi -> doi,
        ResolutionAuthorityNamespace.Doi -> other
      )
    )
    assert(ResolutionValidation.check(full, ctx).isRight)
    assert(ResolutionValidation.checkComponent(full.coveredEndpoints, full, ctx, 1, 10).isLeft)
    assert(
      ResolutionValidation
        .check(full.copy(authoritativeIdentifiers = full.authoritativeIdentifiers.take(1)), ctx)
        .isLeft,
      "preferred DOI cannot hide a contradictory declared DOI"
    )

    val nativeDoi =
      work(SourceType.Crossref, s"https://doi.org/${doi.toUpperCase(java.util.Locale.ROOT)}")
    val nativeCtx = context(Vector(nativeDoi))
    val nativeBundle = authorityBundle(
      ResolutionEntityType.Work,
      endpoint(nativeDoi),
      Vector(ResolutionAuthorityNamespace.Doi -> doi)
    )
    assert(ResolutionValidation.check(nativeBundle, nativeCtx).isRight)
  }

  test(
    "B2 ORCID work references ground self identifiers while related works remain weak evidence"
  ) {
    val native = s"/$orcidA/work/41"
    val activity = OrcidActivityRecord(
      SchemaVersions.domain,
      orcidA,
      OrcidActivityKind.Work,
      native,
      Some("Synthetic work"),
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      None,
      fixtureNote,
      provenance(SourceType.Orcid, native, "independent-orcid"),
      Vector(
        OrcidWorkReference(
          "doi",
          s"https://doi.org/${doi.toUpperCase(java.util.Locale.ROOT)}",
          Some("self")
        ),
        OrcidWorkReference("arxiv", "2101.00001v3", Some("self")),
        OrcidWorkReference("doi", "10.5555/related-only", Some("part-of"))
      )
    )
    val ep = ResolutionEndpoint.OrcidWorkActivity(ref(activity.provenance), None)
    val ctx = context(activities = Vector(activity))
    val full = authorityBundle(
      ResolutionEntityType.Work,
      ep,
      Vector(
        ResolutionAuthorityNamespace.Doi -> doi,
        ResolutionAuthorityNamespace.Arxiv -> "2101.00001"
      )
    )
    assert(ResolutionValidation.check(full, ctx).isRight)
    assert(
      ResolutionValidation
        .check(full.copy(authoritativeIdentifiers = full.authoritativeIdentifiers.take(1)), ctx)
        .isLeft
    )
    val related = full.copy(authoritativeIdentifiers =
      full.authoritativeIdentifiers :+
        ResolutionIdentifierAssertion(
          ep,
          ResolutionAuthorityNamespace.Doi,
          "10.5555/related-only",
          Vector("synthetic:source")
        )
    )
    assert(
      ResolutionValidation.check(related, ctx).isLeft,
      "a part-of DOI does not identify the ORCID work itself"
    )
  }
}
