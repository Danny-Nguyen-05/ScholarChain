package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Path
import java.time.Instant
import scala.util.Try
import upickle.default.ReadWriter

final case class ClassifiedPair(
    outcome: MatchOutcome,
    path: ResolutionDecisionPath,
    score: Option[Double],
    features: Vector[ResolutionFeature],
    reasonCodes: Vector[String],
    supportiveGroups: Vector[String],
    sufficient: Boolean
) derives ReadWriter
final case class DecisionDetail(
    decisionId: String,
    pairId: String,
    rulesFired: Vector[String],
    supportiveGroups: Vector[String],
    identifiers: Vector[IdentifierEvidence],
    adjudication: Option[AdjudicationTrace]
) derives ReadWriter
final case class ResolutionRun(
    runId: String,
    decidedAtUtc: String,
    decisions: Vector[ResolutionDecision],
    links: Vector[ResolutionAcceptedLink],
    constraints: Vector[ResolutionGroupingConstraints],
    details: Vector[DecisionDetail],
    diagnostics: Vector[InputDiagnostic],
    evidence: Vector[EvidenceRecord],
    fakeCalls: Int,
    llmMode: String
) derives ReadWriter

object ResolutionEngine {
  def conflicts(a: ResolutionEndpoint, b: ResolutionEndpoint, input: ResolutionInput): Boolean =
    (input.authority(a) ++ input.authority(b)).groupBy(_._1).values.exists(_.map(_._2).size > 1)

  def classify(
      candidate: DerivedPair,
      input: ResolutionInput,
      policy: ResolutionPolicy
  ): Either[String, ClassifiedPair] = Try {
    ResolutionPolicy.validate(policy).fold(e => throw new IllegalArgumentException(e), identity)
    require(
      ResolutionValidation.check(candidate.pair, input.context).isRight,
      "invalid comparison pair"
    )
    val pair = candidate.pair; val p = policy.forEntity(pair.entityType)
    val features = FeatureExtractor.extract(candidate, input, policy)
    val values = features.flatMap(f => f.value.map(f.name -> _)).toMap
    val available =
      p.weights.toVector.flatMap((name, weight) => values.get(name).map(v => (name, v, weight)))
    val score =
      if (available.isEmpty) None
      else
        Some(
          available.map((_, v, w) => v * w).sum / available.map(_._3).sum * values(
            "sourceReliability"
          )
        )
    require(
      score.forall(s => s.isFinite && s >= 0 && s <= 1),
      "nonfinite/out-of-range weighted score"
    )
    val supportive = available
      .collect { case (n, v, _) if v >= p.supportiveFeatureMin => p.featureGroups(n) }
      .distinct
      .sorted
    val sufficient =
      supportive.size >= p.minimumIndependentGroupsForAccept && p.requiredGroups.forall(
        supportive.contains
      )
    val a = pair.left; val b = pair.right
    val hardConflict = conflicts(a, b, input)
    val shared = input.authority(a).intersect(input.authority(b)).nonEmpty
    val bibliography =
      pair.entityType == ResolutionEntityType.Work && p.bibliographicEnabled && values
        .get("title")
        .exists(_ >= p.bibliographicMinTitle) && values
        .get("authorOverlap")
        .exists(_ >= p.bibliographicMinAuthors) && (for (
        x <- input.parentWork(a).flatMap(_.year); y <- input.parentWork(b).flatMap(_.year)
      ) yield math.abs(x.toLong - y.toLong) <= p.bibliographicMaxYearDistance).contains(true)
    if (hardConflict)
      ClassifiedPair(
        MatchOutcome.Conflict,
        ResolutionDecisionPath.HardConflict,
        None,
        features,
        Vector("AUTHORITATIVE_IDENTIFIER_CONFLICT"),
        supportive,
        false
      )
    else if (shared)
      ClassifiedPair(
        MatchOutcome.Accepted,
        ResolutionDecisionPath.ExactIdentifier,
        None,
        features,
        Vector("EXACT_SUPPORTED_IDENTIFIER"),
        supportive,
        true
      )
    else if (bibliography)
      ClassifiedPair(
        MatchOutcome.Accepted,
        ResolutionDecisionPath.DeterministicBibliographic,
        None,
        features,
        Vector("EXACT_TITLE_COMPLETE_AUTHOR_SET_SAME_YEAR"),
        supportive,
        true
      )
    else
      score match {
        case Some(s) if s <= p.rejectThreshold =>
          ClassifiedPair(
            MatchOutcome.Rejected,
            ResolutionDecisionPath.Scored,
            score,
            features,
            Vector("SCORE_LE_REJECT_THRESHOLD"),
            supportive,
            sufficient
          )
        case Some(s) if s >= p.acceptThreshold && sufficient =>
          ClassifiedPair(
            MatchOutcome.Accepted,
            ResolutionDecisionPath.Scored,
            score,
            features,
            Vector("SCORE_GE_ACCEPT_THRESHOLD_SUFFICIENT_EVIDENCE"),
            supportive,
            true
          )
        case Some(s) if s >= p.acceptThreshold =>
          ClassifiedPair(
            MatchOutcome.Unresolved,
            ResolutionDecisionPath.Scored,
            score,
            features,
            Vector("INSUFFICIENT_INDEPENDENT_EVIDENCE"),
            supportive,
            false
          )
        case Some(_) =>
          ClassifiedPair(
            MatchOutcome.Unresolved,
            ResolutionDecisionPath.Scored,
            score,
            features,
            Vector("SCORE_IN_UNRESOLVED_GAP"),
            supportive,
            sufficient
          )
        case None =>
          ClassifiedPair(
            MatchOutcome.Unresolved,
            ResolutionDecisionPath.Scored,
            None,
            features,
            Vector("NO_AVAILABLE_WEIGHTED_EVIDENCE"),
            supportive,
            false
          )
      }
  }.toEither.left.map(_.getMessage)

  def resolve(
      input: ResolutionInput,
      population: CandidatePopulation,
      policy: ResolutionPolicy,
      config: ResolutionConfig,
      mode: String,
      cache: Option[Path],
      runId: String,
      instant: String,
      adapter: Option[AdjudicationAdapter] = None,
      requestPolicy: Option[RequestEligibilityPolicy] = None
  ): Either[String, ResolutionRun] = Try {
    ResolutionConfig.validate(config).fold(e => throw new IllegalArgumentException(e), identity)
    ResolutionPolicy.validate(policy).fold(e => throw new IllegalArgumentException(e), identity)
    RequestEligibilityPolicy
      .validateBinding(policy, requestPolicy)
      .fold(e => throw new IllegalArgumentException(e), identity)
    input.sourceRootPath.foreach(source =>
      cache.foreach(path =>
        PathIsolation
          .disjoint(source, path)
          .fold(e => throw new IllegalArgumentException(e), identity)
      )
    )
    require(Set("disabled", "fake")(mode), "5B supports only disabled or fake mode")
    require(
      StableIds.parseRunId(runId).isRight && instant.endsWith("Z") && Try(
        Instant.parse(instant)
      ).isSuccess,
      "valid run ID and UTC instant required"
    )
    require(
      population.pairs.size <= config.blocking.maxPairsPerRun && population.pairs
        .map(_.pair.pairId)
        .distinct
        .size == population.pairs.size,
      "duplicate/oversized candidate population"
    )
    val evidence =
      (input.evidence.values.toVector ++ population.derivedEvidence).groupBy(_.ref).map {
        case (k, v) =>
          require(v.map(_.sha256).distinct.size == 1, "conflicting evidence ref"); k -> v.head
      }
    evidence.foreach { case (ref, e) =>
      require(
        ref == ResolutionInput.evidenceFor(e.kind, e.payload) && e.sha256 == StableIds.sha256Hex(
          StrictJson.canonical(e.payload)
        ),
        "evidence content/hash mismatch"
      )
    }
    // All candidates must bind both full source records, not merely claim arbitrary valid refs.
    population.pairs.foreach { c =>
      require(
        c.evidenceRefs.distinct == c.evidenceRefs && c.evidenceRefs.forall(evidence.contains),
        "missing/duplicate candidate evidence"
      )
      require(
        (input.refs(c.pair.left) ++ input.refs(c.pair.right)).forall(c.evidenceRefs.contains),
        "candidate does not cite both source observations"
      )
      require(
        c.evidenceRefs
          .map(r =>
            evidence(r).payload
              .render()
              .getBytes(java.nio.charset.StandardCharsets.UTF_8)
              .length
              .toLong
          )
          .sum <= config.blocking.maxEvidenceBytesPerPair,
        "candidate aggregate evidence exceeds bound"
      )
      c.contributingCandidates.foreach { block =>
        require(
          c.evidenceRefs.exists { r =>
            val e = evidence(r);
            e.kind match {
              case "match-candidate" =>
                val prep = StrictJson.parse[MatchCandidate](e.payload.render()).toOption
                prep.exists { p =>
                  val claimed = Set(
                    ResolutionObservationRef(
                      p.left.source,
                      p.left.sourceRecordId,
                      p.left.datasetSnapshot
                    ),
                    ResolutionObservationRef(
                      p.right.source,
                      p.right.sourceRecordId,
                      p.right.datasetSnapshot
                    )
                  )
                  p.candidateId == block.candidateId && p.blockKey == block.blockKey && c.pair.entityType == ResolutionEntityType.Work && claimed == Set(
                    ResolutionIds.observation(c.pair.left),
                    ResolutionIds.observation(c.pair.right)
                  )
                }
              case "derived-candidate" =>
                e.payload("candidateId").str == block.candidateId && e
                  .payload("blockKey")
                  .str == block.blockKey && e.payload("pair")("pairId").str == c.pair.pairId
              case _ => false
            }
          },
          "candidate block lacks actual matching evidence"
        )
      }
    }
    val adjudicator = new OfflineAdjudicator(
      config,
      adapter.getOrElse(
        new DeterministicFakeAdapter(config.adjudication.model, config.adjudication.modelVersion)
      ),
      cache
    )
    val details = Vector.newBuilder[DecisionDetail]
    val decisions = population.pairs.sortBy(_.pair.pairId).map { candidate =>
      val pair = candidate.pair
      val initial = classify(candidate, input, policy)
        .fold(e => throw new IllegalArgumentException(e), identity)
      val eligible =
        RequestEligibilityPolicy.eligible(initial, pair.entityType, policy, requestPolicy)
      val trace =
        if (eligible && mode == "fake")
          Some(
            Adjudication
              .request(candidate, input, policy, config, initial.features, evidence) match {
              case Left(e) =>
                AdjudicationTrace(pair.pairId, "REQUEST_INVALID", 0, false, None, None, Some(e))
              case Right(request) => adjudicator.adjudicate(request)
            }
          )
        else None
      val response = trace.flatMap(_.response)
      val finalOutcome = response.map(_.outcome) match {
        case Some("accept") if initial.sufficient && !conflicts(pair.left, pair.right, input) =>
          MatchOutcome.Accepted
        case Some("reject") => MatchOutcome.Rejected
        case _              => initial.outcome
      }
      val finalPath = if (response.nonEmpty) ResolutionDecisionPath.LlmAdjudicated else initial.path
      val reasons =
        (initial.reasonCodes ++ (if (response.exists(_.outcome == "accept") && !initial.sufficient)
                                   Vector(RequestEligibilityPolicy.blockedAcceptReason)
                                 else Vector.empty) ++ (if (eligible && mode == "disabled")
                                                          Vector("LLM_DISABLED")
                                                        else Vector.empty) ++ trace.toVector.map(
          _.status
        ) ++ response.toVector.flatMap(_.reasonCodes.map("LLM_" + _))).distinct
      val provenance = Provenance(
        SchemaVersions.domain,
        SourceType.ScholarChain,
        pair.pairId,
        None,
        "entity-resolution",
        None,
        None,
        runId,
        Vector("uncalibrated-policy=" + policy.policyVersion, "llm-mode=" + mode)
      )
      val decision = MatchDecision(
        SchemaVersions.domain,
        ResolutionIds.endpointId(pair.left),
        ResolutionIds.endpointId(pair.right),
        initial.features.flatMap(f => f.value.map(v => NamedNumber(f.name, v))),
        finalOutcome,
        initial.score.getOrElse(0.0),
        reasons,
        policy.policyVersion,
        runId,
        "Structural offline resolution; no evaluated identity accuracy or calibrated probability",
        provenance
      )
      val adjudication =
        for (t <- trace; r <- t.response; req <- t.request)
          yield ResolutionAdjudication(
            req.requestHash,
            req.promptVersion,
            req.promptHash,
            req.responseSchemaVersion,
            req.provider,
            req.model,
            Some(req.modelVersion),
            StrictJson.hash(req.generationSettings),
            AdjudicationCache.key(req),
            ResolutionAdjudicationMode.Fake,
            t.cacheHit,
            r.reportedConfidence,
            r.evidenceRefs,
            ResolutionPreAdjudication(initial.score, initial.outcome, initial.path)
          )
      val raw = ResolutionDecision(
        ResolutionContracts.schemaVersion,
        "",
        pair,
        decision,
        candidate.contributingCandidates,
        policy.featurePolicyVersion,
        initial.features,
        finalPath,
        if (initial.score.isDefined) ResolutionConfidenceSemantics.UncalibratedScore
        else ResolutionConfidenceSemantics.Unavailable,
        if (initial.score.isDefined) None else Some("RULE_PATH_OR_NO_AVAILABLE_WEIGHTED_EVIDENCE"),
        policy.fingerprint,
        config.fingerprint,
        input.inputEvidenceHash,
        candidate.evidenceRefs,
        instant,
        adjudication
      )
      val audit = raw.copy(decisionId = ResolutionIds.decisionId(raw))
      ResolutionValidation
        .check(audit, input.context)
        .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
      details += DecisionDetail(
        audit.decisionId,
        pair.pairId,
        initial.reasonCodes,
        initial.supportiveGroups,
        FeatureExtractor.identifiers(pair.left, input) ++ FeatureExtractor
          .identifiers(pair.right, input),
        trace
      )
      audit
    }
    val constraints = ResolutionEntityType.values.toVector.map { entity =>
      val covered = input.endpoints.filter(ResolutionIds.entityType(_) == entity)
      val assertions = covered.flatMap(e =>
        input
          .authority(e)
          .toVector
          .sortBy((ns, value) => (ns.wire, value))
          .map((ns, value) => ResolutionIdentifierAssertion(e, ns, value, input.refs(e)))
      )
      val cannot = decisions
        .filter(d => d.pair.entityType == entity && d.decision.decision == MatchOutcome.Conflict)
        .map(d => ResolutionCannotLink(d.pair, "AUTHORITATIVE_IDENTIFIER_CONFLICT", d.evidenceRefs))
      val bundle = ResolutionGroupingConstraints(
        ResolutionContracts.schemaVersion,
        entity,
        policy.policyVersion,
        policy.fingerprint,
        covered,
        cannot,
        assertions
      )
      require(
        covered.size.toLong + assertions.size + cannot.size <= config.maxConstraintEntries,
        "complete constraint bundle exceeds run-level bound"
      )
      // Exactly once per complete run-level bundle; no grouping or component traversal here.
      ResolutionValidation
        .check(bundle, input.context)
        .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
    }
    val links = decisions.filter(_.decision.decision == MatchOutcome.Accepted).map { audit =>
      require(!conflicts(audit.pair.left, audit.pair.right, input), "conflict before link export")
      val link = ResolutionAcceptedLink(
        ResolutionContracts.schemaVersion,
        audit.pair,
        audit.decisionId,
        policy.policyVersion,
        policy.fingerprint,
        runId,
        audit.decision.provenance
      )
      ResolutionValidation
        .check(link, audit, input.context)
        .fold(es => throw new IllegalArgumentException(es.map(_.message).mkString("; ")), identity)
    }
    ResolutionRun(
      runId,
      instant,
      decisions,
      links,
      constraints,
      details.result(),
      population.diagnostics,
      evidence.values.toVector.sortBy(_.ref),
      adjudicator.calls,
      mode
    )
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))
}
