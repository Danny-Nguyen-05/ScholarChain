package edu.uic.cs441.scholarchain.core

import java.time.Instant
import scala.util.Try

/** Contract validation only. ER owns scoring, authority extraction, policy loading and evidence IO.
  */
object ResolutionValidation {
  private def error(message: String): DomainViolation =
    DomainViolation(ViolationCode.InconsistentRecord, message)
  private def requireThat(condition: Boolean, message: String): Vector[DomainViolation] =
    if (condition) Vector.empty else Vector(error(message))
  private def checked[A](
      value: A,
      errors: Vector[DomainViolation]
  ): Either[Vector[DomainViolation], A] =
    if (errors.isEmpty) Right(value) else Left(errors.distinct)
  private def nonblank(value: String): Boolean = value.nonEmpty && value == value.trim
  private def hash(value: String): Boolean = value.matches("[0-9a-f]{64}")
  private def refs(values: Vector[String]): Boolean =
    values.distinct == values && values.forall(nonblank)
  private def schema(version: String): Vector[DomainViolation] =
    if (version == ResolutionContracts.schemaVersion) Vector.empty
    else
      Vector(
        DomainViolation(ViolationCode.UnsupportedSchemaVersion, "unsupported resolution schema")
      )
  private def failures[A](value: Either[Vector[DomainViolation], A]): Vector[DomainViolation] =
    value.left.toOption.toVector.flatten

  private[core] def checkEndpointStructure(
      endpoint: ResolutionEndpoint
  ): Vector[DomainViolation] = {
    val ref = ResolutionIds.observation(endpoint)
    val sourceErrors =
      StableIds.parseSourceRecordId(ref.source, ref.sourceRecordId).left.toOption.toVector ++
        StableIds.snapshotId(ref.source, ref.datasetSnapshot).left.toOption.toVector
    val bindingErrors = endpoint match {
      case ResolutionEndpoint.Work(_, id) =>
        StableIds.parseWorkId(id).left.toOption.toVector
      case ResolutionEndpoint.Mention(_, id) =>
        StableIds.parseMentionIdParts(id) match {
          case Left(e) => Vector(e)
          case Right(parts) =>
            requireThat(
              parts.sourceWire.equalsIgnoreCase(
                ref.source.wire
              ) && parts.sourceRecordId == ref.sourceRecordId,
              "mention endpoint must repeat source and parent source record"
            )
        }
      case ResolutionEndpoint.OrcidProfile(_, orcid) =>
        requireThat(
          ref.source == SourceType.Orcid && ref.sourceRecordId.stripPrefix("/") == orcid &&
            StableIds.researcherIdFromValidatedOrcid(orcid).isRight,
          "profile endpoint must reference its bare ORCID source record"
        )
      case ResolutionEndpoint.OrcidWorkActivity(_, workId) =>
        requireThat(
          ref.source == SourceType.Orcid &&
            ref.sourceRecordId.stripPrefix("/").split("/", -1).toVector.lift(1).contains("work"),
          "work activity endpoint requires an ORCID work path"
        ) ++ workId.toVector.flatMap(id => StableIds.parseWorkId(id).left.toOption)
    }
    sourceErrors ++ bindingErrors ++ requireThat(
      ref.source != SourceType.ScholarChain,
      "identity endpoints require original source observations"
    )
  }

  def check(
      value: ResolutionPair,
      context: ResolutionValidationContext
  ): Either[Vector[DomainViolation], ResolutionPair] = {
    val expected = ResolutionIds.pair(value.entityType, value.left, value.right)
    checked(
      value,
      schema(value.schemaVersion) ++ failures(expected) ++
        requireThat(
          expected.contains(value),
          "pair must have canonical endpoints and its computed id"
        ) ++
        context.check(value.left) ++ context.check(value.right)
    )
  }

  def check(
      value: ResolutionDecision,
      context: ResolutionValidationContext
  ): Either[Vector[DomainViolation], ResolutionDecision] = {
    val d = value.decision
    val available = value.featureEvidence.flatMap(f => f.value.map(NamedNumber(f.name, _)))
    val featureErrors = value.featureEvidence.flatMap { f =>
      requireThat(nonblank(f.name), "feature name required") ++
        requireThat(
          f.value.isDefined != f.missingReason.isDefined,
          "feature requires value XOR missing reason"
        ) ++
        requireThat(f.value.forall(_.isFinite), "feature value must be finite") ++
        requireThat(f.missingReason.forall(nonblank), "missing reason cannot be blank") ++
        requireThat(
          refs(f.evidenceRefs) && f.evidenceRefs.forall(value.evidenceRefs.contains),
          "feature evidence must use allowed refs"
        )
    }
    val candidateErrors = value.contributingCandidates.flatMap { c =>
      requireThat(
        c.candidateId.matches("match-candidate:[0-9a-f]{64}"),
        "invalid contributing candidate id"
      ) ++
        requireThat(
          nonblank(c.blockKey) && c.blockKey.length <= 512 && !c.blockKey.exists(ch =>
            ch == '\r' || ch == '\n'
          ),
          "invalid contributing block key"
        )
    }
    val adjudicationErrors = value.adjudication.toVector.flatMap { a =>
      requireThat(
        Vector(a.requestHash, a.promptHash, a.generationSettingsHash, a.cacheKey).forall(hash),
        "adjudication hashes required"
      ) ++
        requireThat(
          Vector(a.promptVersion, a.responseSchemaVersion, a.provider, a.model)
            .forall(nonblank) && a.modelVersion.forall(nonblank),
          "adjudication versions/provider/model required"
        ) ++
        requireThat(
          a.reportedConfidence.isFinite && a.reportedConfidence >= 0 && a.reportedConfidence <= 1,
          "LLM reported confidence must be finite in [0,1]"
        ) ++
        requireThat(
          refs(a.evidenceRefs) && a.evidenceRefs.forall(value.evidenceRefs.contains),
          "adjudication evidence must use allowed refs"
        ) ++ requireThat(
          a.preAdjudication.score.forall(s => s.isFinite && s >= 0 && s <= 1),
          "pre-adjudication score must be finite in [0,1] when present"
        ) ++ requireThat(
          a.preAdjudication.outcome == MatchOutcome.Unresolved &&
            Set(ResolutionDecisionPath.Scored, ResolutionDecisionPath.DeterministicBibliographic)
              .contains(a.preAdjudication.decisionPath),
          "only unresolved scored/bibliographic cases may reach adjudication"
        )
    }
    val timestampValid =
      value.decidedAtUtc.endsWith("Z") && Try(Instant.parse(value.decidedAtUtc)).isSuccess
    checked(
      value,
      schema(value.schemaVersion) ++ failures(check(value.pair, context)) ++
        failures(
          DomainValidation.check(d)
        ) ++ featureErrors ++ candidateErrors ++ adjudicationErrors ++
        requireThat(
          d.sourceId == ResolutionIds.endpointId(value.pair.left) && d.targetId == ResolutionIds
            .endpointId(value.pair.right),
          "decision endpoints must bind snapshot endpoint ids"
        ) ++
        requireThat(
          value.decisionId == ResolutionIds.decisionId(value),
          "decision id must bind all audit fields"
        ) ++
        requireThat(timestampValid, "decision timestamp must be an ISO instant in UTC ending Z") ++
        requireThat(
          Vector(value.policyHash, value.configHash, value.inputEvidenceHash).forall(hash),
          "policy/config/input evidence hashes required"
        ) ++
        requireThat(nonblank(value.featurePolicyVersion), "feature policy version required") ++
        requireThat(
          if (value.confidenceSemantics == ResolutionConfidenceSemantics.Unavailable)
            d.confidence == 0 && value.scoreUnavailableReason.exists(nonblank)
          else value.scoreUnavailableReason.isEmpty,
          "unavailable score requires explicit reason and compatibility confidence zero"
        ) ++
        requireThat(
          value.featureEvidence.map(_.name) == value.featureEvidence.map(_.name).distinct.sorted,
          "feature evidence must be sorted and distinct"
        ) ++
        requireThat(
          d.features == available,
          "legacy decision features must equal available evidence values"
        ) ++
        requireThat(
          refs(value.evidenceRefs) && value.evidenceRefs.nonEmpty,
          "distinct nonempty evidence refs required"
        ) ++
        requireThat(
          value.contributingCandidates.distinct == value.contributingCandidates && value.contributingCandidates
            .map(_.candidateId)
            .distinct
            .size == value.contributingCandidates.size,
          "contributing candidates must be distinct"
        ) ++
        requireThat(
          (value.decisionPath == ResolutionDecisionPath.LlmAdjudicated) == value.adjudication.nonEmpty,
          "LLM decision path and adjudication metadata must occur together"
        ) ++
        requireThat(
          value.decisionPath != ResolutionDecisionPath.LlmAdjudicated || d.decision != MatchOutcome.Conflict,
          "LLM adjudication cannot produce CONFLICT"
        ) ++
        requireThat(
          value.decisionPath != ResolutionDecisionPath.HardConflict || d.decision == MatchOutcome.Conflict,
          "hard conflict path requires CONFLICT"
        ) ++
        requireThat(
          d.provenance.source == SourceType.ScholarChain && d.provenance.sourceRecordId == value.pair.pairId,
          "decision provenance must identify its derived pair"
        )
    )
  }

  /** Full link validation requires the actual accepted audit decision; a naked link proves nothing.
    */
  def check(
      value: ResolutionAcceptedLink,
      audit: ResolutionDecision,
      context: ResolutionValidationContext
  ): Either[Vector[DomainViolation], ResolutionAcceptedLink] =
    checked(
      value,
      schema(value.schemaVersion) ++ failures(check(audit, context)) ++
        failures(DomainValidation.checkProvenance(value.provenance)) ++
        requireThat(
          audit.decision.decision == MatchOutcome.Accepted,
          "link requires ACCEPTED audit"
        ) ++
        requireThat(
          value.pair == audit.pair && value.decisionId == audit.decisionId && value.policyVersion == audit.decision.policyVersion && value.policyHash == audit.policyHash && value.runId == audit.decision.runId && value.provenance == audit.decision.provenance,
          "link must bind accepted audit pair/policy/run/provenance"
        )
    )

  def check(
      value: ResolutionGroupingConstraints,
      context: ResolutionValidationContext
  ): Either[Vector[DomainViolation], ResolutionGroupingConstraints] = {
    val endpointErrors =
      value.coveredEndpoints.flatMap(e => checkEndpointStructure(e) ++ context.check(e))
    val ids = value.coveredEndpoints.map(ResolutionIds.endpointId)
    val constraintErrors = value.cannotLinks.flatMap { c =>
      failures(check(c.pair, context)) ++
        requireThat(
          c.pair.entityType == value.entityType && Vector(c.pair.left, c.pair.right)
            .forall(value.coveredEndpoints.contains),
          "cannot-link endpoints require coverage and entity type"
        ) ++
        requireThat(
          nonblank(c.reasonCode) && c.evidenceRefs.nonEmpty && refs(c.evidenceRefs),
          "cannot-link reason/evidence required"
        )
    }
    val assertionErrors = value.authoritativeIdentifiers.flatMap { a =>
      requireThat(
        value.coveredEndpoints.contains(a.endpoint),
        "identifier assertion endpoint requires coverage"
      ) ++
        requireThat(
          a.namespace.entityType == value.entityType &&
            a.namespace.entityType == ResolutionIds.entityType(a.endpoint),
          "authoritative identifier namespace must match entity type"
        ) ++
        requireThat(
          a.namespace.acceptsCanonicalValue(a.value),
          "authoritative identifier requires canonical value in its supported namespace"
        ) ++
        requireThat(
          a.evidenceRefs.nonEmpty && refs(a.evidenceRefs),
          "authoritative identifier evidence required"
        ) ++ failures(context.groundedAuthority(a.endpoint).flatMap { facts =>
          checked(
            a,
            requireThat(
              facts.contains(a.namespace -> a.value),
              "authoritative assertion must match its endpoint source observation"
            )
          )
        })
    }
    val coverageErrors = value.coveredEndpoints.flatMap { endpoint =>
      failures(context.groundedAuthority(endpoint).flatMap { facts =>
        val supplied = value.authoritativeIdentifiers
          .filter(_.endpoint == endpoint)
          .map(a => a.namespace -> a.value)
          .toSet
        checked(
          endpoint,
          requireThat(
            facts.subsetOf(supplied),
            "covered endpoint requires every supported source authority fact"
          )
        )
      })
    }
    checked(
      value,
      schema(
        value.schemaVersion
      ) ++ endpointErrors ++ constraintErrors ++ assertionErrors ++ coverageErrors ++
        requireThat(
          nonblank(value.policyVersion) && hash(value.policyHash),
          "constraint policy version/hash required"
        ) ++
        requireThat(
          ids.distinct == ids && value.coveredEndpoints.forall(
            ResolutionIds.entityType(_) == value.entityType
          ),
          "constraint coverage must be distinct and typed"
        ) ++
        requireThat(
          value.cannotLinks
            .map(_.pair.pairId)
            .distinct
            .size == value.cannotLinks.size && value.authoritativeIdentifiers.distinct == value.authoritativeIdentifiers,
          "constraints must not contain duplicate assertions/pairs"
        )
    )
  }

  /** Validates one proposed component, without constructing groups or selecting representatives.
    * Limits are explicit caller policy, checked before traversing the supplied bundle.
    */
  def checkComponent(
      members: Vector[ResolutionEndpoint],
      constraints: ResolutionGroupingConstraints,
      context: ResolutionValidationContext,
      maxMembers: Int,
      maxConstraints: Int
  ): Either[Vector[DomainViolation], Vector[ResolutionEndpoint]] = {
    val size =
      constraints.coveredEndpoints.size.toLong + constraints.cannotLinks.size + constraints.authoritativeIdentifiers.size
    if (
      maxMembers <= 0 || maxConstraints <= 0 || members.isEmpty || members.size > maxMembers || size > maxConstraints
    )
      Left(Vector(error("component or constraint bounds invalid/exceeded")))
    else
      check(constraints, context).flatMap { _ =>
        val ids = members.map(ResolutionIds.endpointId)
        val memberSet = members.toSet
        val conflicts =
          constraints.cannotLinks.exists(c => memberSet(c.pair.left) && memberSet(c.pair.right))
        val identifierConflict = constraints.authoritativeIdentifiers
          .filter(a => memberSet(a.endpoint))
          .groupBy(_.namespace)
          .values
          .exists(_.map(_.value).distinct.size > 1)
        checked(
          members,
          requireThat(
            ids.distinct == ids && members.forall(constraints.coveredEndpoints.contains),
            "component members require distinct complete constraint coverage"
          ) ++
            requireThat(!conflicts, "component violates cannot-link constraint") ++
            requireThat(
              !identifierConflict,
              "component has conflicting authoritative identifiers in one namespace"
            )
        )
      }
  }
}
