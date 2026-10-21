package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Path
import java.time.Instant
import scala.collection.mutable
import scala.util.Try
import upickle.default.ReadWriter

final case class LiveDemoAdmission(
    schemaVersion: String,
    frozenInputHash: String,
    demoInputHash: String,
    demoCandidateHash: String,
    queueHash: String,
    splitHash: String,
    lockedHeldOutAnchorsHash: String,
    admittedPairIds: Vector[String],
    excludedPairIds: Vector[String],
    supplemental: Boolean
) derives ReadWriter
final case class LiveDemoSelection(
    admittedPairs: Vector[DerivedPair],
    eligiblePairs: Vector[DerivedPair],
    diagnostics: Vector[InputDiagnostic],
    admission: LiveDemoAdmission
) derives ReadWriter
final case class LiveDemoRun(
    schemaVersion: String,
    admission: LiveDemoAdmission,
    policyHash: String,
    sourceConfigHash: String,
    liveConfigHash: String,
    promptHash: String,
    responseSchemaHash: String,
    selectedModel: String,
    providerReportedModels: Vector[String],
    eligiblePairs: Int,
    traces: Vector[LiveAttemptTrace],
    decisions: Vector[ResolutionDecision],
    budget: Option[LiveBudgetState],
    limitations: Vector[String],
    links: Vector[ResolutionAcceptedLink],
    constraints: Vector[ResolutionGroupingConstraints]
) derives ReadWriter

/** Filters protected evidence components before any prediction, request, credential or provider
  * access.
  */
object LiveDemo {
  private def value[A](r: Either[String, A]): A =
    r.fold(e => throw new IllegalArgumentException(e), identity)
  private def locked(split: ReviewSplit): Vector[String] = split.groups
    .filter(g => split.partitions.get(g.groupId).contains("held-out"))
    .flatMap(_.anchorHashes)
    .distinct
    .sorted
  private def result(
      input: ResolutionInput,
      population: CandidatePopulation,
      frozen: ResolutionInput,
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      policy: ResolutionPolicy,
      admitted: Vector[DerivedPair],
      supplemental: Boolean,
      requestPolicy: Option[RequestEligibilityPolicy]
  ): LiveDemoSelection = {
    val allowed = admitted.sortBy(_.pair.pairId)
    val ids = allowed.map(_.pair.pairId).toSet
    val rejected = population.pairs.map(_.pair.pairId).filterNot(ids).sorted
    val candidates = allowed.filter(d =>
      RequestEligibilityPolicy.eligible(
        value(ResolutionEngine.classify(d, input, policy)),
        d.pair.entityType,
        policy,
        requestPolicy
      )
    )
    val admission = LiveDemoAdmission(
      "scholarchain.live-demo-admission.v1",
      frozen.inputEvidenceHash,
      input.inputEvidenceHash,
      ReviewQueue.populationHash(population),
      queue.queueHash,
      split.hash,
      StrictJson.hash(locked(split)),
      allowed.map(_.pair.pairId),
      rejected,
      supplemental
    )
    LiveDemoSelection(
      allowed,
      candidates,
      Vector(
        InputDiagnostic("DEVELOPMENT_COMPONENT_CANDIDATES_ADMITTED", allowed.size, Vector.empty),
        InputDiagnostic(
          "HELD_OUT_LINKED_OR_UNASSIGNED_CANDIDATES_EXCLUDED_BEFORE_SCORING",
          rejected.size,
          Vector.empty
        ),
        InputDiagnostic("NATURALLY_ELIGIBLE_DEVELOPMENT_PAIRS", candidates.size, Vector.empty)
      ),
      admission
    )
  }
  def select(
      input: ResolutionInput,
      population: CandidatePopulation,
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      policy: ResolutionPolicy,
      requestPolicy: Option[RequestEligibilityPolicy] = None
  ): Either[String, LiveDemoSelection] = Try {
    value(ReviewQueue.validate(queue, split)); value(ResolutionPolicy.validate(policy))
    value(RequestEligibilityPolicy.validateBinding(policy, requestPolicy))
    require(
      input.inputEvidenceHash == queue.binding.inputEvidenceHash && ReviewQueue.populationHash(
        population
      ) == queue.binding.candidatePopulationHash,
      "development demo population differs from frozen queue"
    )
    val groups = split.groups.flatMap(g => g.endpointIds.map(_ -> g.groupId)).toMap
    val admitted = population.pairs.filter { candidate =>
      val actual = Vector(candidate.pair.left, candidate.pair.right).map(e =>
        groups.get(ResolutionIds.endpointId(e))
      )
      actual.forall(_.nonEmpty) && split.pairGroups
        .get(candidate.pair.pairId)
        .contains(actual.flatten.distinct.sorted) && actual.flatten.forall(g =>
        split.partitions.get(g).contains("development")
      )
    }
    result(
      input,
      population,
      input,
      queue,
      split,
      policy,
      admitted,
      supplemental = false,
      requestPolicy = requestPolicy
    )
  }.toEither.left.map(_.getMessage)
  def selectSupplement(
      input: ResolutionInput,
      population: CandidatePopulation,
      frozenInput: ResolutionInput,
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      policy: ResolutionPolicy,
      requestPolicy: Option[RequestEligibilityPolicy] = None
  ): Either[String, LiveDemoSelection] = Try {
    value(ReviewQueue.validate(queue, split)); value(ResolutionPolicy.validate(policy))
    value(RequestEligibilityPolicy.validateBinding(policy, requestPolicy))
    require(
      frozenInput.inputEvidenceHash == queue.binding.inputEvidenceHash,
      "protected frozen input differs from queue"
    )
    require(
      population.pairs.map(_.pair.pairId).distinct.size == population.pairs.size,
      "duplicate supplemental pairs"
    )
    val endpoints = input.endpoints.distinct.sortBy(ResolutionIds.endpointKey)
    val index = endpoints.zipWithIndex.toMap
    val parent = Array.tabulate(endpoints.size)(identity)
    def root(n: Int): Int = {
      var r = n; while (parent(r) != r) r = parent(r); var x = n;
      while (parent(x) != x) { val next = parent(x); parent(x) = r; x = next }; r
    }
    val hashes = endpoints.map(e => ReviewQueue.leakageAnchors(e, input).map(StableIds.sha256Hex))
    val first = mutable.Map.empty[String, Int]
    hashes.zipWithIndex.foreach((anchors, i) =>
      anchors.foreach(a => first.get(a).fold { first(a) = i } { j => parent(root(i)) = root(j) })
    )
    val forbidden = locked(split).toSet
    val excludedComponents =
      endpoints.indices.filter(i => hashes(i).exists(forbidden)).map(root).toSet
    val admitted = population.pairs.filter { candidate =>
      Vector(candidate.pair.left, candidate.pair.right).forall(e =>
        index.get(e).exists(i => !excludedComponents(root(i)))
      )
    }
    result(
      input,
      population,
      frozenInput,
      queue,
      split,
      policy,
      admitted,
      supplemental = true,
      requestPolicy = requestPolicy
    )
  }.toEither.left.map(_.getMessage)
  def run(
      input: ResolutionInput,
      population: CandidatePopulation,
      frozenInput: ResolutionInput,
      queue: ReviewQueueDocument,
      split: ReviewSplit,
      policy: ResolutionPolicy,
      sourceConfig: ResolutionConfig,
      liveConfig: LiveProviderConfig,
      ledgerPath: Path,
      cache: Option[Path],
      runId: String,
      enabled: Boolean,
      approvalId: String,
      transportFactory: () => OpenAITransport,
      supplemental: Boolean = false,
      requestPolicy: Option[RequestEligibilityPolicy] = None,
      maxPairs: Option[Int] = None
  ): Either[String, LiveDemoRun] = Try {
    value(ResolutionConfig.validate(sourceConfig)); value(LiveProviderConfig.validate(liveConfig))
    require(
      maxPairs.forall(n => n > 0 && n <= liveConfig.budget.maxAttempts),
      "live pair cap must be positive and within the approved attempt limit"
    )
    val selection = value(
      if (supplemental)
        selectSupplement(input, population, frozenInput, queue, split, policy, requestPolicy)
      else select(input, population, queue, split, policy, requestPolicy)
    )
    val evidence = input.evidence ++ population.derivedEvidence.map(e => e.ref -> e)
    val limitations = Vector(
      "Development/demo only; protected held-out components are excluded before scoring.",
      "No human labels are read. This pilot establishes provider execution evidence, not accuracy or final Phase 5 acceptance.",
      "Token reservations use wire UTF-8 bytes plus 4096 framing allowance; observed usage is recorded separately. An observed reservation overrun fuses subsequent calls.",
      "Cost is a conservative standard-tier upper-bound estimate from observed tokens, not a provider invoice. Missing cache-write token details are represented as zero reported writes; input cost still uses the higher cache-write rate.",
      "Unobserved identity leakage remains possible; approved supplemental evidence is separate from the frozen review population.",
      "Accepted links and complete source constraints are limited to this explicitly scoped development demo, not a full matching run; the human queue is unchanged."
    ) ++ maxPairs.toVector.map(n =>
      "Explicit live candidate cap=" + n + "; the full eligible population remains reported separately."
    )
    def output(
        traces: Vector[LiveAttemptTrace],
        decisions: Vector[ResolutionDecision],
        budget: Option[LiveBudgetState]
    ): LiveDemoRun = {
      val links = decisions.filter(_.decision.decision == MatchOutcome.Accepted).map { d =>
        require(
          !ResolutionEngine.conflicts(d.pair.left, d.pair.right, input),
          "conflict before demo link export"
        )
        val link = ResolutionAcceptedLink(
          ResolutionContracts.schemaVersion,
          d.pair,
          d.decisionId,
          policy.policyVersion,
          policy.fingerprint,
          runId,
          d.decision.provenance
        )
        value(
          ResolutionValidation
            .check(link, d, input.context)
            .left
            .map(_.map(_.message).mkString("; "))
        )
      }
      val constraints = ResolutionEntityType.values.toVector.map { entity =>
        val covered = input.endpoints.filter(ResolutionIds.entityType(_) == entity)
        val assertions = covered.flatMap(e =>
          input
            .authority(e)
            .toVector
            .sortBy((ns, v) => (ns.wire, v))
            .map((ns, v) => ResolutionIdentifierAssertion(e, ns, v, input.refs(e)))
        )
        val cannot = decisions
          .filter(d => d.pair.entityType == entity && d.decision.decision == MatchOutcome.Conflict)
          .map(d =>
            ResolutionCannotLink(d.pair, "AUTHORITATIVE_IDENTIFIER_CONFLICT", d.evidenceRefs)
          )
        require(
          covered.size.toLong + assertions.size + cannot.size <= sourceConfig.maxConstraintEntries,
          "demo complete constraints exceed run bound"
        )
        value(
          ResolutionValidation
            .check(
              ResolutionGroupingConstraints(
                ResolutionContracts.schemaVersion,
                entity,
                policy.policyVersion,
                policy.fingerprint,
                covered,
                cannot,
                assertions
              ),
              input.context
            )
            .left
            .map(_.map(_.message).mkString("; "))
        )
      }
      LiveDemoRun(
        "scholarchain.live-demo.v1",
        selection.admission,
        policy.fingerprint,
        sourceConfig.fingerprint,
        liveConfig.fingerprint,
        StableIds.sha256Hex(OpenAIResponses.prompt),
        StableIds.sha256Hex(OpenAIResponses.schemaText),
        liveConfig.model,
        traces.flatMap(_.result.map(_.resolvedModel)).distinct.sorted,
        selection.eligiblePairs.size,
        traces,
        decisions,
        budget,
        limitations,
        links,
        constraints
      )
    }
    if (!enabled || selection.eligiblePairs.isEmpty) output(Vector.empty, Vector.empty, None)
    else {
      value(LiveProviderConfig.validate(liveConfig, requireApproval = true))
      require(
        approvalId == liveConfig.approvalId,
        "explicit live opt-in must match recorded budget approval"
      )
      require(StableIds.parseRunId(runId).isRight, "valid demo run ID required")
      require(
        LiveResponseLimits.from(sourceConfig) == liveConfig.responseLimits,
        "source/live response bounds differ"
      )
      Vector(input, frozenInput).flatMap(_.sourceRootPath).distinct.foreach { root =>
        value(PathIsolation.disjoint(root, ledgerPath));
        cache.foreach(p => value(PathIsolation.disjoint(root, p)))
      }
      val ledger = new LiveBudgetLedger(liveConfig, ledgerPath)
      try {
        lazy val transport = transportFactory()
        val service = new LiveAdjudicator(
          liveConfig,
          new OpenAITransport {
            override def prepare(): Either[String, OpenAITransport] = transport.prepare()
            def post(body: String, timeoutMs: Int, maxResponseBytes: Int): ProviderHttpResponse =
              transport.post(body, timeoutMs, maxResponseBytes)
          },
          ledger,
          cache
        )
        val traces = Vector.newBuilder[LiveAttemptTrace];
        val decisions = Vector.newBuilder[ResolutionDecision]
        selection.eligiblePairs.take(maxPairs.getOrElse(liveConfig.budget.maxAttempts)).foreach {
          candidate =>
            val initial = value(ResolutionEngine.classify(candidate, input, policy))
            require(
              RequestEligibilityPolicy.eligible(
                initial,
                candidate.pair.entityType,
                policy,
                requestPolicy
              ) && !ResolutionEngine
                .conflicts(candidate.pair.left, candidate.pair.right, input),
              "live candidate lost eligibility or gained conflict"
            )
            val request = value(
              OpenAIResponses.request(
                candidate,
                input,
                policy,
                sourceConfig,
                liveConfig,
                initial.features,
                evidence
              )
            )
            val trace = service.adjudicate(request); traces += trace
            val response = trace.result.map(_.response)
            val outcome = response.map(_.outcome) match {
              case Some("accept")
                  if initial.sufficient && !ResolutionEngine
                    .conflicts(candidate.pair.left, candidate.pair.right, input) =>
                MatchOutcome.Accepted
              case Some("reject") => MatchOutcome.Rejected
              case _              => initial.outcome
            }
            val provenance = Provenance(
              SchemaVersions.domain,
              SourceType.ScholarChain,
              candidate.pair.pairId,
              None,
              "entity-resolution-live-demo",
              None,
              None,
              runId,
              Vector(
                "development-demo-only",
                "provider=" + liveConfig.provider,
                "model=" + liveConfig.model
              )
            )
            val decision = MatchDecision(
              SchemaVersions.domain,
              ResolutionIds.endpointId(candidate.pair.left),
              ResolutionIds.endpointId(candidate.pair.right),
              initial.features.flatMap(f => f.value.map(v => NamedNumber(f.name, v))),
              outcome,
              initial.score.getOrElse(0.0),
              (initial.reasonCodes ++ (if (
                                         response
                                           .exists(_.outcome == "accept") && !initial.sufficient
                                       ) Vector(RequestEligibilityPolicy.blockedAcceptReason)
                                       else
                                         Vector.empty) ++ Vector(trace.status) ++ response.toVector
                .flatMap(
                  _.reasonCodes.map("LLM_" + _)
                )).distinct,
              policy.policyVersion,
              runId,
              "Bounded live development demo; no calibrated probability or measured identity accuracy",
              provenance
            )
            val adjudication = response.map(r =>
              ResolutionAdjudication(
                request.requestHash,
                request.promptVersion,
                request.promptHash,
                request.responseSchemaVersion,
                request.provider,
                request.model,
                Some(liveConfig.modelVersion),
                StrictJson.hash(request.generationSettings),
                LiveAdjudicationCache.key(request),
                ResolutionAdjudicationMode.Live,
                trace.cacheHit,
                r.reportedConfidence,
                r.evidenceRefs,
                ResolutionPreAdjudication(initial.score, initial.outcome, initial.path)
              )
            )
            val raw = ResolutionDecision(
              ResolutionContracts.schemaVersion,
              "",
              candidate.pair,
              decision,
              candidate.contributingCandidates,
              policy.featurePolicyVersion,
              initial.features,
              if (response.nonEmpty) ResolutionDecisionPath.LlmAdjudicated else initial.path,
              ResolutionConfidenceSemantics.UncalibratedScore,
              None,
              policy.fingerprint,
              OpenAIResponses.effectiveConfigHash(sourceConfig, liveConfig),
              input.inputEvidenceHash,
              candidate.evidenceRefs,
              Instant.now().toString,
              adjudication
            )
            val audit = raw.copy(decisionId = ResolutionIds.decisionId(raw))
            value(
              ResolutionValidation
                .check(audit, input.context)
                .left
                .map(_.map(_.message).mkString("; "))
            )
            decisions += audit
        }
        output(traces.result(), decisions.result(), Some(ledger.snapshot))
      } finally ledger.close()
    }
  }.toEither.left.map(e =>
    Option(e.getMessage)
      .filter(m => !m.toLowerCase.contains("bearer"))
      .getOrElse("LIVE_DEMO_FAILED")
  )
}
