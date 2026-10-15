package edu.uic.cs441.scholarchain.core

import upickle.default.ReadWriter

/** Additive Phase 5 contracts. Existing domain records and stable-id formulas are unchanged. */
object ResolutionContracts {
  val schemaVersion: String = "scholarchain.resolution.v1"
}

final case class ResolutionObservationRef(
    source: SourceType,
    sourceRecordId: String,
    datasetSnapshot: String
) derives ReadWriter

enum ResolutionEntityType derives ReadWriter {
  case Work, Researcher
}

/** Activities never supply an author list. Only an actual ORCID work activity is a work endpoint.
  */
enum ResolutionEndpoint derives ReadWriter {
  case Work(observation: ResolutionObservationRef, workId: String)
  case Mention(observation: ResolutionObservationRef, mentionId: String)
  case OrcidProfile(observation: ResolutionObservationRef, orcid: String)
  case OrcidWorkActivity(observation: ResolutionObservationRef, observedWorkId: Option[String])
}

final case class ResolutionPair(
    schemaVersion: String,
    pairId: String,
    entityType: ResolutionEntityType,
    left: ResolutionEndpoint,
    right: ResolutionEndpoint
) derives ReadWriter

final case class CandidateBlockRef(candidateId: String, blockKey: String) derives ReadWriter

/** Missing is explicit; no numeric sentinel denotes unavailable evidence. Formulas live in ER. */
final case class ResolutionFeature(
    name: String,
    value: Option[Double],
    missingReason: Option[String],
    evidenceRefs: Vector[String]
) derives ReadWriter

enum ResolutionDecisionPath derives ReadWriter {
  case ExactIdentifier, DeterministicBibliographic, Scored, LlmAdjudicated, HardConflict
}

enum ResolutionConfidenceSemantics derives ReadWriter {
  case Unavailable, UncalibratedScore, CalibratedProbability
}

enum ResolutionAdjudicationMode derives ReadWriter {
  case Fake, Live
}

final case class ResolutionPreAdjudication(
    score: Option[Double],
    outcome: MatchOutcome,
    decisionPath: ResolutionDecisionPath
) derives ReadWriter

/** Reported confidence is the model's assertion, never a calibrated system probability. */
final case class ResolutionAdjudication(
    requestHash: String,
    promptVersion: String,
    promptHash: String,
    responseSchemaVersion: String,
    provider: String,
    model: String,
    modelVersion: Option[String],
    generationSettingsHash: String,
    cacheKey: String,
    mode: ResolutionAdjudicationMode,
    cacheHit: Boolean,
    reportedConfidence: Double,
    evidenceRefs: Vector[String],
    preAdjudication: ResolutionPreAdjudication
) derives ReadWriter

final case class ResolutionDecision(
    schemaVersion: String,
    decisionId: String,
    pair: ResolutionPair,
    decision: MatchDecision,
    contributingCandidates: Vector[CandidateBlockRef],
    featurePolicyVersion: String,
    featureEvidence: Vector[ResolutionFeature],
    decisionPath: ResolutionDecisionPath,
    confidenceSemantics: ResolutionConfidenceSemantics,
    scoreUnavailableReason: Option[String],
    policyHash: String,
    configHash: String,
    inputEvidenceHash: String,
    evidenceRefs: Vector[String],
    decidedAtUtc: String,
    adjudication: Option[ResolutionAdjudication]
) derives ReadWriter

/** Pairwise acceptance only. Consumers must apply the complete constraint bundle before grouping.
  */
final case class ResolutionAcceptedLink(
    schemaVersion: String,
    pair: ResolutionPair,
    decisionId: String,
    policyVersion: String,
    policyHash: String,
    runId: String,
    provenance: Provenance
) derives ReadWriter

final case class ResolutionCannotLink(
    pair: ResolutionPair,
    reasonCode: String,
    evidenceRefs: Vector[String]
) derives ReadWriter

/** Closed hard-conflict namespaces, narrower than identifiers used for observation lookup. Native
  * source keys and author disambiguation hypotheses cannot assert hard identity conflicts.
  */
enum ResolutionAuthorityNamespace(
    val wire: String,
    val entityType: ResolutionEntityType,
    private val indexedNamespace: IdentifierNamespace
) {
  case Doi
      extends ResolutionAuthorityNamespace(
        "doi",
        ResolutionEntityType.Work,
        IdentifierNamespace.Doi
      )
  case Arxiv
      extends ResolutionAuthorityNamespace(
        "arxiv",
        ResolutionEntityType.Work,
        IdentifierNamespace.Arxiv
      )
  case Orcid
      extends ResolutionAuthorityNamespace(
        "orcid",
        ResolutionEntityType.Researcher,
        IdentifierNamespace.Orcid
      )

  /** Ingestion must normalize before constructing assertions. Group validation never silently
    * repairs spellings. Versioned arXiv observations remain evidence until version semantics are
    * defined by a later matching policy; they are not hard-conflict assertions in this contract.
    */
  def acceptsCanonicalValue(value: String): Boolean =
    StableIds.normalizeIndexedIdentifier(indexedNamespace, value).contains(value) &&
      (this != ResolutionAuthorityNamespace.Arxiv || !value.matches(".*v[0-9]+$"))
}

object ResolutionAuthorityNamespace {
  given ReadWriter[ResolutionAuthorityNamespace] =
    EnumCodecs.wire(ResolutionAuthorityNamespace.values, _.wire)
}

/** ER supplies canonical authoritative identifiers under its versioned authority policy. */
final case class ResolutionIdentifierAssertion(
    endpoint: ResolutionEndpoint,
    namespace: ResolutionAuthorityNamespace,
    value: String,
    evidenceRefs: Vector[String]
) derives ReadWriter

/** coveredEndpoints explicitly includes endpoints with no authoritative identifier. Omission is
  * unknown coverage, never permission to group. This is a complete run-level bundle, not a
  * pair-local subset.
  */
final case class ResolutionGroupingConstraints(
    schemaVersion: String,
    entityType: ResolutionEntityType,
    policyVersion: String,
    policyHash: String,
    coveredEndpoints: Vector[ResolutionEndpoint],
    cannotLinks: Vector[ResolutionCannotLink],
    authoritativeIdentifiers: Vector[ResolutionIdentifierAssertion]
) derives ReadWriter

/** New identifiers hash compact JSON arrays (UTF-8 SHA-256); no old StableIds formula changes. */
object ResolutionIds {
  def observation(endpoint: ResolutionEndpoint): ResolutionObservationRef = endpoint match {
    case ResolutionEndpoint.Work(ref, _)              => ref
    case ResolutionEndpoint.Mention(ref, _)           => ref
    case ResolutionEndpoint.OrcidProfile(ref, _)      => ref
    case ResolutionEndpoint.OrcidWorkActivity(ref, _) => ref
  }

  def entityType(endpoint: ResolutionEndpoint): ResolutionEntityType = endpoint match {
    case ResolutionEndpoint.Work(_, _) | ResolutionEndpoint.OrcidWorkActivity(_, _) =>
      ResolutionEntityType.Work
    case _ => ResolutionEntityType.Researcher
  }

  /** Carried work/orcid bindings are checked against source context, not hashed as identity. */
  def endpointKey(endpoint: ResolutionEndpoint): String = {
    val ref = observation(endpoint)
    val (kind, member) = endpoint match {
      case ResolutionEndpoint.Work(_, _)              => ("work", "")
      case ResolutionEndpoint.Mention(_, mentionId)   => ("mention", mentionId)
      case ResolutionEndpoint.OrcidProfile(_, _)      => ("orcid-profile", "")
      case ResolutionEndpoint.OrcidWorkActivity(_, _) => ("orcid-work-activity", "")
    }
    ujson.Arr(kind, ref.source.wire, ref.sourceRecordId, ref.datasetSnapshot, member).render()
  }

  def endpointId(endpoint: ResolutionEndpoint): String =
    "resolution-endpoint:" + StableIds.sha256Hex(endpointKey(endpoint))

  def pair(
      entityType: ResolutionEntityType,
      first: ResolutionEndpoint,
      second: ResolutionEndpoint
  ): Either[Vector[DomainViolation], ResolutionPair] = {
    val errors = ResolutionValidation.checkEndpointStructure(first) ++
      ResolutionValidation.checkEndpointStructure(second)
    if (errors.nonEmpty) Left(errors)
    else if (entityType != this.entityType(first) || entityType != this.entityType(second))
      Left(Vector(DomainViolation(ViolationCode.InconsistentRecord, "pair entity type mismatch")))
    else if (endpointKey(first) == endpointKey(second))
      Left(Vector(DomainViolation(ViolationCode.InvalidPairOrder, "self observation pair")))
    else {
      val (left, right) =
        if (endpointKey(first).compareTo(endpointKey(second)) < 0) (first, second)
        else (second, first)
      val hashInput = ujson
        .Arr(
          ResolutionContracts.schemaVersion,
          entityType.toString,
          ujson.read(endpointKey(left)),
          ujson.read(endpointKey(right))
        )
        .render()
      Right(
        ResolutionPair(
          ResolutionContracts.schemaVersion,
          "resolution-pair:" + StableIds.sha256Hex(hashInput),
          entityType,
          left,
          right
        )
      )
    }
  }

  /** Includes all audit fields including time/run. Blank only the derived id to avoid recursion. */
  def decisionId(value: ResolutionDecision): String =
    "resolution-decision:" + StableIds.sha256Hex(CoreJson.compact(value.copy(decisionId = "")))
}
