package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*

object FeatureExtractor {
  val names: Vector[String] = ResolutionPolicy.featureNames.toVector.sorted
  def identifiers(
      endpoint: ResolutionEndpoint,
      input: ResolutionInput
  ): Vector[IdentifierEvidence] = {
    val ref = ResolutionIds.observation(endpoint); val refs = input.refs(endpoint)
    val publicationFacts = input.context
      .groundedElectronicPublicationFacts(endpoint)
      .fold(
        errors => throw new IllegalArgumentException(errors.map(_.message).mkString("; ")),
        identity
      )
    val publicationLinks = publicationFacts.map(_._1).toSet
    val raw: Vector[(String, String, String)] = endpoint match {
      case ResolutionEndpoint.Work(_, _) =>
        val w = input.workByRef(ref)
        w.doi.toVector.map(v => ("doi", v, "preferred.doi")) ++ w.arxivId.toVector.map(v =>
          ("arxiv", v, "preferred.arxiv")
        ) ++
          w.observedIdentifiers.flatMap(id =>
            IdentifierRules.role(id.namespace).map(ns => (ns, id.value, id.namespace))
          ) ++
          w.sourceLinks
            .filterNot(publicationLinks)
            .map(l =>
              ("repository-url", l.value, "sourceLinks." + l.name)
            ) ++ w.externalUrl.toVector.map(v => ("repository-url", v, "externalUrl")) ++
          (if (w.source == SourceType.OpenAlex)
             Vector(("openalex-work", w.sourceRecordId, "native-record"))
           else if (w.source == SourceType.Crossref)
             Vector(("doi", w.sourceRecordId, "native-record"))
           else Vector.empty)
      case ResolutionEndpoint.Mention(_, _) =>
        val m = input.mention(endpoint).get;
        m.observedOrcid.toVector.map(v =>
          ("orcid", v, "observedOrcid")
        ) ++ m.observedOpenAlexAuthorId.toVector.map(v =>
          ("openalex-author", v, "observedOpenAlexAuthorId")
        )
      case ResolutionEndpoint.OrcidProfile(_, _) =>
        val p = input.profileByRef(ref);
        Vector(("orcid", p.orcid, "profile.orcid")) ++ p.externalIds.flatMap(id =>
          IdentifierRules
            .role(id.namespace)
            .map(ns => (ns, id.value, "profile.externalIds." + id.namespace))
        )
      case ResolutionEndpoint.OrcidWorkActivity(_, _) =>
        val a = input.activityByRef(ref);
        a.observedDoi.toVector.map(v => ("doi", v, "observedDoi")) ++ a.workReferences.flatMap(id =>
          IdentifierRules
            .role(id.externalIdType)
            .map(ns => (ns, id.value, "workReferences." + id.relationship.getOrElse("unknown")))
        )
    }
    val ordinary = raw.map { case (ns, value, role) =>
      val n = IdentifierRules.normalize(ns, value);
      IdentifierEvidence(
        ns,
        value,
        n.toOption,
        Normalization.version,
        role,
        Set("doi", "arxiv", "orcid")(ns) && (!role.startsWith("workReferences.") || role
          .stripPrefix("workReferences.")
          .trim
          .equalsIgnoreCase("self")) && n.toOption.exists(v =>
          input
            .authority(endpoint)
            .exists((a, x) =>
              a.wire == ns && x == (if (ns == "arxiv") v.replaceFirst("v[0-9]+$", "") else v)
            )
        ),
        refs,
        n.left.toOption
      )
    }
    ordinary ++ publicationFacts.map { case (link, namespace, canonical) =>
      IdentifierEvidence(
        namespace.wire,
        link.value,
        Some(canonical),
        Normalization.version,
        "sourceLinks." + link.name,
        true,
        refs,
        None
      )
    }
  }
  def extract(
      candidate: DerivedPair,
      input: ResolutionInput,
      policy: ResolutionPolicy
  ): Vector[ResolutionFeature] = {
    val pair = candidate.pair; val a = pair.left; val b = pair.right;
    val refs = (input.refs(a) ++ input.refs(b)).distinct.sorted
    val wa = input.parentWork(a); val wb = input.parentWork(b)
    def title(e: ResolutionEndpoint): Option[String] = input
      .parentWork(e)
      .map(_.title)
      .orElse(input.activityByRef.get(ResolutionIds.observation(e)).flatMap(_.title))
    def year(e: ResolutionEndpoint): Option[Int] = input
      .parentWork(e)
      .flatMap(_.year)
      .orElse(input.activityByRef.get(ResolutionIds.observation(e)).flatMap(_.publicationYear))
    def name(e: ResolutionEndpoint): Option[String] = input
      .mention(e)
      .map(_.nameText)
      .orElse(input.profileByRef.get(ResolutionIds.observation(e)).flatMap(_.displayName))
    def similarity(x: Option[String], y: Option[String]): Option[Double] = for (
      xx <- x; yy <- y; s <- Normalization.similarity(xx, yy)
    ) yield s
    def authorNames(w: Option[WorkRecord]): Set[String] = w.toVector
      .flatMap(_.authors)
      .map(m => Normalization.nameTokens(m.nameText).sorted.mkString(" "))
      .filter(_.nonEmpty)
      .toSet
    def coauthors(e: ResolutionEndpoint): Set[String] = input
      .parentWork(e)
      .toVector
      .flatMap(_.authors)
      .filterNot(m => input.mention(e).exists(_.mentionId == m.mentionId))
      .map(m => Normalization.nameTokens(m.nameText).sorted.mkString(" "))
      .filter(_.nonEmpty)
      .toSet
    val samePublication = (for (x <- wa; y <- wb)
      yield x.workId == y.workId).contains(true) || (for (x <- wa; y <- wb) yield {
      val ex = ResolutionEndpoint.Work(ResolutionInput.ref(x.provenance), x.workId);
      val ey = ResolutionEndpoint.Work(ResolutionInput.ref(y.provenance), y.workId)
      input.authority(ex).intersect(input.authority(ey)).nonEmpty
    }).contains(true)
    // IDs only compare inside their declared namespace. Organization names remain a separate,
    // weak namespace; absence of an external-ID crosswalk is unavailable, not disagreement.
    def affiliations(e: ResolutionEndpoint): Map[String, Set[String]] = {
      val found = input.mention(e).toVector.flatMap { m =>
        val ref = ResolutionIds.observation(e)
        val declared = input.affiliations
          .filter(a => a.mentionId == m.mentionId && ResolutionInput.ref(a.provenance) == ref)
          .flatMap { a =>
            a.ror.toVector
              .flatMap(v => StableIds.institutionIdFromRor(v).toOption.map("ror" -> _)) ++
              a.ringgold.toVector.flatMap(v =>
                StableIds.institutionIdFromRinggold(v).toOption.map("ringgold" -> _)
              ) ++
              a.organizationName.toVector
                .map(Normalization.folded)
                .filter(_.nonEmpty)
                .map("name" -> _)
          }
        val enriched = input.enrichments
          .filter(a =>
            a.mentionId.contains(m.mentionId) && ResolutionInput
              .ref(a.provenance) == ref && a.targetKind == EnrichmentTargetKind.Institution
          )
          .map { a =>
            val parts = a.targetId.split(":", 3)
            parts(1) -> a.targetId
          }
        declared ++ enriched
      }
      found.groupBy(_._1).view.mapValues(_.map(_._2).toSet).toMap
    }
    val affiliationA = affiliations(a); val affiliationB = affiliations(b)
    val comparableAffiliations = affiliationA.keySet.intersect(affiliationB.keySet)
    val affiliationSimilarity =
      if (comparableAffiliations.isEmpty) None
      else
        Some(
          comparableAffiliations.toVector
            .flatMap(ns => Normalization.jaccard(affiliationA(ns), affiliationB(ns)))
            .min
        )
    val venueA = wa.flatMap(_.venueId); val venueB = wb.flatMap(_.venueId)
    def venueNamespace(id: String): String = id.substring(0, id.lastIndexOf(':'))
    val incomparableVenues =
      (for (x <- venueA; y <- venueB) yield venueNamespace(x) != venueNamespace(y)).contains(true)
    val venueSimilarity =
      for (x <- venueA; y <- venueB if venueNamespace(x) == venueNamespace(y))
        yield if (x == y) 1.0 else 0.0
    val emptyNormalizedName =
      Vector(name(a), name(b)).exists(_.exists(raw => Normalization.nameTokens(raw).isEmpty))
    val ia = identifiers(a, input).flatMap(i => i.normalized.map(i.namespace -> _)).toSet
    val ib = identifiers(b, input).flatMap(i => i.normalized.map(i.namespace -> _)).toSet
    val researcher = pair.entityType == ResolutionEntityType.Researcher
    val values: Map[String, Option[Double]] = Map(
      "title" -> (if (!researcher) similarity(title(a), title(b)) else None),
      "name" -> (if (researcher) (for (
                   x <- name(a); y <- name(b);
                   similarity <- Normalization
                     .jaccard(Normalization.nameTokens(x).toSet, Normalization.nameTokens(y).toSet)
                 ) yield similarity)
                 else None),
      "initials" -> (if (researcher) (for (
                       x <- name(a); y <- name(b); s <- Normalization.initialsCompatible(x, y)
                     ) yield s)
                     else None),
      "authorOverlap" -> (if (!researcher) Normalization.jaccard(authorNames(wa), authorNames(wb))
                          else None),
      "coauthorOverlap" -> (if (researcher && !samePublication)
                              Normalization.jaccard(coauthors(a), coauthors(b))
                            else None),
      "authorOrder" -> (if (researcher)
                          (for (x <- input.mention(a); y <- input.mention(b))
                            yield 1.0 / (1.0 + math.abs(x.ordinal.toLong - y.ordinal.toLong)))
                        else None),
      "affiliation" -> (if (researcher) affiliationSimilarity else None),
      "yearCompatibility" -> (for (x <- year(a); y <- year(b))
        yield math.max(
          0.0,
          1.0 - math
            .abs(x.toLong - y.toLong)
            .toDouble / policy.forEntity(pair.entityType).yearToleranceYears
        )),
      "venue" -> venueSimilarity,
      "identifier" -> (if (ia.map(_._1).intersect(ib.map(_._1)).isEmpty) None
                       else Some(if (ia.intersect(ib).nonEmpty) 1.0 else 0.0)),
      "citationNeighborhood" -> None,
      "sourceReliability" -> Some(
        math.min(
          policy.sourceReliability(ResolutionIds.observation(a).source.wire),
          policy.sourceReliability(ResolutionIds.observation(b).source.wire)
        )
      )
    )
    names.map(n =>
      ResolutionFeature(
        n,
        values(n),
        if (values(n).isDefined) None
        else
          Some(
            if (n == "citationNeighborhood") "NOT_EXPORTED_BY_PREPARATION"
            else if (n == "venue" && incomparableVenues) "UNAVAILABLE_INCOMPARABLE_VENUE_NAMESPACES"
            else if (
              n == "affiliation" && researcher && affiliationA.nonEmpty && affiliationB.nonEmpty && comparableAffiliations.isEmpty
            ) "UNAVAILABLE_INCOMPARABLE_AFFILIATION_NAMESPACES"
            else if (n == "name" && researcher && emptyNormalizedName) "EMPTY_NORMALIZED_NAME"
            else "NOT_APPLICABLE_OR_SOURCE_EVIDENCE_MISSING"
          ),
        if (values(n).isDefined) refs else Vector.empty
      )
    )
  }
}
