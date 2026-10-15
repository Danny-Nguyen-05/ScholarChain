package edu.uic.cs441.scholarchain.core

/** Source truth only; does not resolve identities. Mentions must belong to a validated work. */
final class ResolutionValidationContext private (
    private val works: Map[ResolutionObservationRef, WorkRecord],
    private val profiles: Map[ResolutionObservationRef, OrcidProfileRecord],
    private val activities: Map[ResolutionObservationRef, OrcidActivityRecord]
) {

  /** All supported hard facts on this exact observation. This is source consistency, not a matching
    * policy: unknown identifiers remain observations, and recognized malformed facts fail instead
    * of vanishing. No evidence is borrowed from another member or source key.
    */
  private[core] def groundedAuthority(
      endpoint: ResolutionEndpoint
  ): Either[Vector[DomainViolation], Set[(ResolutionAuthorityNamespace, String)]] = {
    val bindingErrors = ResolutionValidation.checkEndpointStructure(endpoint) ++ check(endpoint)
    if (bindingErrors.nonEmpty) Left(bindingErrors)
    else {
      import ResolutionAuthorityNamespace.*
      def token(raw: String): String = raw.trim.toLowerCase(java.util.Locale.ROOT)
      def role(raw: String): Option[ResolutionAuthorityNamespace] = token(raw) match {
        case "doi" | "openalex.doi" | "openalex.ids.doi" => Some(Doi)
        case "arxiv"                                     => Some(Arxiv)
        case _                                           => None
      }
      def normalize(
          namespace: ResolutionAuthorityNamespace,
          raw: String
      ): Either[DomainViolation, String] = namespace match {
        case Doi   => StableIds.normalizeIndexedIdentifier(IdentifierNamespace.Doi, raw)
        case Orcid => StableIds.normalizeIndexedIdentifier(IdentifierNamespace.Orcid, raw)
        case Arxiv =>
          val parsed = StableIds
            .normalizeIndexedIdentifier(IdentifierNamespace.Arxiv, raw)
            .orElse(
              StableIds
                .arxivFromSourceUri(Some(raw))
                .toRight(
                  DomainViolation(
                    ViolationCode.MalformedId,
                    "malformed declared arXiv authority evidence"
                  )
                )
            )
          parsed.map(_.replaceFirst("v[0-9]+$", ""))
      }
      val ref = ResolutionIds.observation(endpoint)
      val (rawFacts, relationshipErrors)
          : (Vector[(ResolutionAuthorityNamespace, String)], Vector[DomainViolation]) =
        endpoint match {
          case ResolutionEndpoint.Work(_, _) =>
            val work = works(ref)
            val preferred = work.doi.toVector.map(Doi -> _) ++ work.arxivId.toVector.map(Arxiv -> _)
            val crossref =
              if (work.source == SourceType.Crossref) Vector(Doi -> work.sourceRecordId)
              else Vector.empty
            val declared =
              work.observedIdentifiers.flatMap(id => role(id.namespace).map(_ -> id.value))
            (preferred ++ crossref ++ declared, Vector.empty)
          case ResolutionEndpoint.Mention(_, id) =>
            (
              works(ref).authors.find(_.mentionId == id).get.observedOrcid.toVector.map(Orcid -> _),
              Vector.empty
            )
          case ResolutionEndpoint.OrcidProfile(_, _) =>
            (Vector(Orcid -> profiles(ref).orcid), Vector.empty)
          case ResolutionEndpoint.OrcidWorkActivity(_, _) =>
            val activity = activities(ref)
            // Activity identifiers have only explicit DOI/arxiv type roles, unlike work field roles.
            val references = activity.workReferences.flatMap { r =>
              val namespace = token(r.externalIdType) match {
                case "doi"   => Some(Doi)
                case "arxiv" => Some(Arxiv)
                case _       => None
              }
              namespace.map(ns => (ns, r.value, r.relationship.exists(token(_) == "self")))
            }
            val matchingPreferred = activity.observedDoi.toVector.flatMap { preferred =>
              references.filter { case (ns, raw, _) =>
                ns == Doi && normalize(Doi, raw) == normalize(Doi, preferred)
              }
            }
            val errors =
              if (matchingPreferred.nonEmpty && !matchingPreferred.exists(_._3))
                Vector(
                  DomainViolation(
                    ViolationCode.InconsistentRecord,
                    "preferred activity DOI is retained only as a related/unknown relationship reference"
                  )
                )
              else Vector.empty
            val selfFacts = references.collect { case (ns, raw, true) => ns -> raw }
            (activity.observedDoi.toVector.map(Doi -> _) ++ selfFacts, errors)
        }
      val normalized = rawFacts.map { case (ns, raw) => normalize(ns, raw).map(ns -> _) }
      val errors = relationshipErrors ++ normalized.flatMap(_.left.toOption)
      if (errors.nonEmpty) Left(errors.distinct)
      else Right(normalized.flatMap(_.toOption).toSet)
    }
  }

  private[core] def check(endpoint: ResolutionEndpoint): Vector[DomainViolation] = {
    val ref = ResolutionIds.observation(endpoint)
    val bound = endpoint match {
      case ResolutionEndpoint.Work(_, id) => works.get(ref).exists(_.workId == id)
      case ResolutionEndpoint.Mention(_, id) =>
        works.get(ref).exists(_.authors.exists(_.mentionId == id))
      case ResolutionEndpoint.OrcidProfile(_, orcid) => profiles.get(ref).exists(_.orcid == orcid)
      case ResolutionEndpoint.OrcidWorkActivity(_, workId) =>
        activities
          .get(ref)
          .exists(a => a.activityKind == OrcidActivityKind.Work && a.observedWorkId == workId)
    }
    if (bound) Vector.empty
    else
      Vector(
        DomainViolation(
          ViolationCode.InconsistentRecord,
          s"missing source observation or mismatched endpoint binding: ${ResolutionIds.endpointId(endpoint)}"
        )
      )
  }
}

object ResolutionValidationContext {
  def create(
      works: Vector[WorkRecord],
      profiles: Vector[OrcidProfileRecord],
      activities: Vector[OrcidActivityRecord]
  ): Either[Vector[DomainViolation], ResolutionValidationContext] = {
    def ref(p: Provenance): ResolutionObservationRef =
      ResolutionObservationRef(p.source, p.sourceRecordId, p.datasetSnapshot)
    val errors = works.flatMap(w => DomainValidation.check(w).left.toOption.toVector.flatten) ++
      profiles.flatMap(p => DomainValidation.check(p).left.toOption.toVector.flatten) ++
      activities.flatMap(a => DomainValidation.check(a).left.toOption.toVector.flatten)
    val keyed: Vector[(ResolutionObservationRef, Any)] =
      works.map(w => ref(w.provenance) -> w) ++
        profiles.map(p => ref(p.provenance) -> p) ++
        activities.map(a => ref(a.provenance) -> a)
    val collisions = keyed.groupBy(_._1).toVector.collect {
      case (key, values) if values.map(_._2).distinct.size > 1 =>
        DomainViolation(ViolationCode.InconsistentRecord, s"conflicting source observation: $key")
    }
    val allErrors = (errors ++ collisions).distinct.sortBy(e => (e.code.toString, e.message))
    if (allErrors.nonEmpty) Left(allErrors)
    else
      Right(
        new ResolutionValidationContext(
          works.map(w => ref(w.provenance) -> w).toMap,
          profiles.map(p => ref(p.provenance) -> p).toMap,
          activities.map(a => ref(a.provenance) -> a).toMap
        )
      )
  }
}
