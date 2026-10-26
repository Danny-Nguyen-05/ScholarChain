package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*

final case class VerifiedAnswer(
    answer: AnswerResponse,
    verification: VerificationResult,
    interpretationAccepted: Boolean
)

/** Pure exact-field verification. Similarity, fluent prose and model status are never evidence. */
final class ClaimVerificationAgent(config: RuntimeConfig) {
  require(RuntimeConfigValidation.check(config).isEmpty)
  private val metricFields = Set(
    "publicationCount",
    "distinctCoauthorCount",
    "totalCoauthorOccurrences",
    "averageCoauthorsPerPaper",
    "maximumCoauthorsOnOnePaper",
    "maxTeamWorkIds",
    "maxTeamWorkTieCount",
    "weightedDegree",
    "componentId",
    "communityId",
    "coreness",
    "maximumTotalAuthors",
    "authorCountConversion"
  )
  private val bridgeFields = Set(
    "crossCommunityDegree",
    "crossCommunityWeight",
    "communitiesConnected",
    "participationCoefficient",
    "distinctCoauthorCount",
    "communityId",
    "communityQualification",
    "rank",
    "rankingValue",
    "rankingMeasure",
    "sourceRankingScope"
  )
  private val communityFields = Set(
    "communityId",
    "size",
    "selectedMemberIds",
    "selectedCrossCommunityEdgeCount",
    "neighborCommunityIds",
    "truncated",
    "communityQualification"
  )
  private val pathFields = Set(
    "pathStatus",
    "orderedResearcherIds",
    "edgeIds",
    "hopEvidenceIds",
    "hopCount",
    "maxHops",
    "sourceComponentId",
    "targetComponentId",
    "coauthorIds",
    "returnedCount",
    "truncated",
    "researcherA",
    "researcherB",
    "jointPublicationCount",
    "workIds"
  )
  private val estimateFields = Set(
    "componentId",
    "effectiveDiameterP90",
    "distanceMethod",
    "distanceP90Approximate",
    "sampleSourceCount",
    "seed",
    "meanDistance",
    "reachedPairCount"
  )
  private val temporalFields = Set(
    "fromPresent",
    "toPresent",
    "enteredLargestComponent",
    "leftLargestComponent",
    "deltaDistinctCoauthors",
    "deltaAverageCoauthorsPerPaper",
    "deltaMaximumCoauthorsOnOnePaper",
    "deltaComponentSize",
    "deltaCrossCommunityDegree",
    "deltaCrossCommunityWeight",
    "deltaCommunitiesConnected",
    "deltaParticipationCoefficient",
    "communityJaccardOverlap",
    "previousCommunityId",
    "currentCommunityId"
  )
  private val qualificationFields = Set("converged", "iterations", "approximate")
  private def kind(item: EvidenceItem): String = item.runtime.toVector
    .flatMap(_.values)
    .find(_.field == "kind")
    .flatMap(_.text)
    .getOrElse("")
  private def allowed(typed: TypedAnswerClaim, item: EvidenceItem, field: String): Boolean = {
    val k = kind(item)
    val communityQualification =
      Set(RuntimeClaimType.Community, RuntimeClaimType.Bridge, RuntimeClaimType.Temporal)(
        typed.claimType
      ) ||
        typed.values.exists(v => Set("communityId", "communityJaccardOverlap")(v.field))
    if (field == "approximate") return k == "distance-estimate"
    if (field == "converged" || field == "iterations") return communityQualification
    typed.claimType match {
      case RuntimeClaimType.Metric =>
        (Set("metrics", "ranking")(k) && metricFields(
          field
        )) || (k == "distance-estimate" && estimateFields(field))
      case RuntimeClaimType.Ranking =>
        Set("ranking", "bridge")(k) &&
        (metricFields ++ bridgeFields ++ Set(
          "rank",
          "rankingValue",
          "rankingMetric",
          "sourceRankingScope"
        ))(field)
      case RuntimeClaimType.Path =>
        Set("path", "direct-coauthors", "edge")(k) &&
        (pathFields(field) || field.startsWith("year:"))
      case RuntimeClaimType.Community => k == "community" && communityFields(field)
      case RuntimeClaimType.Bridge    => k == "bridge" && bridgeFields(field)
      case RuntimeClaimType.Temporal =>
        k == "temporal" &&
        (temporalFields(field) || field.startsWith("converged:") || field.startsWith("iterations:"))
      case RuntimeClaimType.Identity =>
        k == "identity" && Set("displayName", "sourceIds", "confidence")(field)
      case RuntimeClaimType.Publication =>
        k == "publication" && Set("title", "year", "workId")(field)
      case RuntimeClaimType.Semantic =>
        item.runtime.exists(_.descriptive) && Set("documentType", "usage")(field)
    }
  }
  private def expected(item: EvidenceItem, field: String): Option[RuntimeClaimValue] = {
    val r = item.runtime.get
    field match {
      case "approximate" => Some(RuntimeClaimValue(field, flag = Some(r.approximate)))
      case "converged"   => r.converged.map(v => RuntimeClaimValue(field, flag = Some(v)))
      case "iterations" =>
        r.iterations.map(v => RuntimeClaimValue(field, number = Some(v.toString)))
      case _ => r.values.find(_.field == field)
    }
  }
  private def same(a: RuntimeClaimValue, b: RuntimeClaimValue): Boolean =
    if (a.field != b.field) false
    else if (a.number.nonEmpty && b.number.nonEmpty)
      try BigDecimal(a.number.get) == BigDecimal(b.number.get)
      catch { case _: NumberFormatException => false }
    else a == b

  def verify(
      plan: QueryPlan,
      bundle: EvidenceBundle,
      proposal: SynthesisProposal
  ): VerifiedAnswer = {
    val validBundle = DomainValidation.check(bundle).isRight
    val byId = bundle.items.map(i => i.evidenceId -> i).toMap
    val duplicates =
      proposal.claims.groupBy(_.claimId).collect { case (id, xs) if xs.size > 1 => id }.toSet
    val outcomes = proposal.claims.map { claim =>
      var reasons = Vector.empty[String]
      if (!validBundle) reasons :+= "invalid-evidence-bundle"
      if (duplicates(claim.claimId)) reasons :+= "duplicate-claim-id"
      if (
        claim.evidenceIds.isEmpty || claim.evidenceIds.distinct != claim.evidenceIds || !claim.evidenceIds
          .forall(byId.contains)
      )
        reasons :+= "missing-or-duplicate-evidence-id"
      val cited = claim.evidenceIds.flatMap(byId.get)
      val typed = claim.runtime
      if (typed.isEmpty || typed.exists(t => RuntimeContractValidation.claim(t).nonEmpty))
        reasons :+= "invalid-typed-claim"
      var matched = 0
      var conflicting = false
      typed.foreach { t =>
        val expectedTemplate = t.claimType.wire.toLowerCase(java.util.Locale.ROOT) + "-v1"
        if (t.templateId != expectedTemplate) reasons :+= "unsupported-claim-template"
        val source =
          if (!validBundle) Vector.empty
          else
            cited.filter(i =>
              i.runtime.exists(r =>
                r.subjectIds.toSet == t.subjectIds.toSet &&
                  r.windowIds == t.windowIds && (t.claimType == RuntimeClaimType.Semantic || !r.descriptive)
              )
            )
        if (source.isEmpty) reasons :+= "subject-window-or-trust-mismatch"
        if (
          t.claimType == RuntimeClaimType.Path && source.exists(i =>
            kind(i) == "path" &&
              i.runtime.get.values.exists(v => v.field == "pathStatus" && v.text.contains("Found"))
          )
        ) {
          if (!source.filter(kind(_) == "path").forall(pathComplete(_, byId)))
            reasons :+= "incomplete-path-evidence"
        }
        val requestedWindows =
          plan.runtime.toVector.flatMap(o => o.windowIds ++ o.comparisonWindowIds).toSet
        if (!t.windowIds.forall(requestedWindows)) reasons :+= "window-not-requested"
        if (
          t.values.exists(v => Set("maximumTotalAuthors", "authorCountConversion")(v.field)) &&
          !plan.runtime.exists(_.authorCountConversion)
        ) reasons :+= "author-conversion-not-requested"
        if (
          bundle.runtime.exists(
            _.retrievalMode == RetrievalMode.Vector
          ) && t.claimType != RuntimeClaimType.Semantic
        )
          reasons :+= "vector-mode-deterministic-claim"
        for (v <- t.values) {
          val candidates = source.filter(allowed(t, _, v.field)).flatMap(expected(_, v.field))
          if (candidates.exists(same(v, _)) && !candidates.exists(x => !same(v, x))) matched += 1
          else {
            if (candidates.nonEmpty) conflicting = true
            reasons :+= (if (candidates.nonEmpty) "value-conflicts-with-evidence"
                         else "unsupported-claim-field")
          }
        }
        if (t.claimType == RuntimeClaimType.Identity) {
          val resolved = bundle.runtime.toVector.flatMap(_.resolvedCandidates)
          val deterministicNames = source.filterNot(_.runtime.get.descriptive)
          if (
            !t.subjectIds.forall(id =>
              resolved.exists(_.researcherId == id) || deterministicNames
                .exists(_.runtime.get.subjectIds.contains(id))
            )
          )
            reasons :+= "identity-not-resolved"
        }
      }
      val verdict =
        if (reasons.isEmpty) ClaimVerdict.Verified
        else if (conflicting) ClaimVerdict.Conflicting
        else if (matched > 0 && reasons.forall(_ == "unsupported-claim-field"))
          ClaimVerdict.PartiallySupported
        else ClaimVerdict.Unsupported
      ClaimVerificationResult(claim.claimId, verdict, reasons.distinct)
    }
    val verifiedIds = outcomes.filter(_.verdict == ClaimVerdict.Verified).map(_.claimId).toSet
    val accepted = proposal.claims.filter(c => verifiedIds(c.claimId)).map { c =>
      val text = render(c.runtime.get, c.evidenceIds.flatMap(byId.get), bundle)
      c.copy(
        text = text,
        verificationStatus = VerificationStatus.Verified,
        uncertainty = Some("Verified against the cited stored evidence.")
      )
    }
    val rejected = proposal.claims.filterNot(c => verifiedIds(c.claimId))
    val verification = VerificationResult(outcomes, rejected, accepted.isEmpty)
    val ordered = proposal.narrativeClaimIds.flatMap(id => accepted.find(_.claimId == id))
    val included = ordered ++ accepted.filterNot(c => ordered.exists(_.claimId == c.claimId))
    val knownNames = bundle.runtime.toVector.flatMap(_.resolvedCandidates).map(_.displayName) ++
      bundle.items
        .filterNot(_.runtime.exists(_.descriptive))
        .flatMap(_.runtime.toVector.flatMap(_.values))
        .filter(_.field == "displayName")
        .flatMap(_.text)
    val interpretationOk =
      InterpretationGuard.accept(proposal.interpretation) && !knownNames.exists(name =>
        ("(?i)\\b" + java.util.regex.Pattern.quote(name) + "\\b").r
          .findFirstIn(proposal.interpretation)
          .nonEmpty
      )
    val facts =
      if (included.isEmpty) "No verified answer is available from the supplied evidence."
      else included.map(_.text).mkString(" ")
    val interpretation =
      if (interpretationOk && proposal.interpretation.trim.nonEmpty)
        " Interpretation: " + proposal.interpretation.trim
      else ""
    val response = AnswerResponse(
      SchemaVersions.domain,
      "answer:" + StableIds.sha256Hex(bundle.queryId + "|" + facts + interpretation),
      plan.planId,
      plan.provenance.runId,
      facts + interpretation,
      accepted,
      bundle.bundleId,
      if (rejected.nonEmpty) "Some proposed claims were rejected by deterministic verification."
      else if (accepted.isEmpty) "Essential verified claims are unavailable."
      else "Source qualifications and evidence bounds apply.",
      plan.provenance
    )
    VerifiedAnswer(response, verification, interpretationOk)
  }

  private def pathComplete(item: EvidenceItem, byId: Map[String, EvidenceItem]): Boolean = {
    val fields = item.runtime.get.values.map(v => v.field -> v).toMap
    val nodes = fields.get("orderedResearcherIds").flatMap(_.ids).getOrElse(Vector.empty)
    val edges = fields.get("edgeIds").flatMap(_.ids).getOrElse(Vector.empty)
    val refs = fields.get("hopEvidenceIds").flatMap(_.ids).getOrElse(Vector.empty)
    val count = fields.get("hopCount").flatMap(_.number).flatMap(_.toIntOption)
    item.graphPath.contains(nodes) && nodes.nonEmpty && edges.size == nodes.size - 1 &&
    count.contains(edges.size) && refs.size == edges.size && refs.zipWithIndex.forall {
      (id, index) =>
        byId.get(id).exists { hop =>
          val r = hop.runtime
          hop.evidenceType == EvidenceType.CoauthorEdge && hop.edgeLocatorId
            .contains(edges(index)) &&
          r.exists(v =>
            !v.descriptive && v.windowIds == item.runtime.get.windowIds &&
              v.runId == item.runtime.get.runId && v.subjectIds.toSet == Set(
                nodes(index),
                nodes(index + 1)
              ) &&
              v.values.exists(x => x.field == "workIds" && x.ids.exists(_.nonEmpty))
          )
        }
    }
  }

  private def render(
      t: TypedAnswerClaim,
      cited: Vector[EvidenceItem],
      bundle: EvidenceBundle
  ): String = {
    val names = bundle.runtime.toVector
      .flatMap(_.resolvedCandidates)
      .map(c => c.researcherId -> c.displayName)
      .toMap
    val subject = t.subjectIds.map(id => names.getOrElse(id, id)).mkString(", ")
    def display(v: RuntimeClaimValue): String = v.number
      .orElse(v.text)
      .orElse(v.flag.map(_.toString))
      .orElse(v.ids.map(_.mkString(" → ")))
      .get
    val labels = Map(
      "publicationCount" -> "publications",
      "distinctCoauthorCount" -> "distinct coauthors (collaboration breadth)",
      "totalCoauthorOccurrences" -> "coauthor occurrences (collaboration intensity)",
      "weightedDegree" -> "weighted degree (equal to coauthor occurrences)",
      "averageCoauthorsPerPaper" -> "average coauthors per paper",
      "maximumCoauthorsOnOnePaper" -> "maximum coauthors on one paper",
      "maximumTotalAuthors" -> "maximum total authors (stored coauthors + 1)",
      "hopCount" -> "collaboration hops",
      "pathStatus" -> "path result",
      "size" -> "community size",
      "crossCommunityDegree" -> "cross-community degree",
      "participationCoefficient" -> "participation coefficient",
      "communitiesConnected" -> "communities connected",
      "jointPublicationCount" -> "joint publications on this collaboration edge",
      "effectiveDiameterP90" -> "approximate distance P90",
      "coreness" -> "coreness",
      "deltaDistinctCoauthors" -> "change in distinct coauthors"
    )
    val fields = t.values
      .filterNot(v => qualificationFields(v.field))
      .map(v =>
        s"${labels.getOrElse(v.field, v.field.replaceAll("([a-z])([A-Z])", "$1 $2").toLowerCase(java.util.Locale.ROOT))}: ${display(v)}"
      )
      .mkString(", ")
    val communityFieldsPresent =
      Set(RuntimeClaimType.Community, RuntimeClaimType.Bridge)(t.claimType) ||
        t.values.exists(v =>
          Set(
            "communityId",
            "communityJaccardOverlap",
            "previousCommunityId",
            "currentCommunityId",
            "deltaCrossCommunityDegree",
            "deltaCrossCommunityWeight",
            "deltaCommunitiesConnected",
            "deltaParticipationCoefficient"
          )(v.field)
        )
    val communities =
      if (communityFieldsPresent) cited.flatMap(_.runtime).filter(_.converged.isDefined)
      else Vector.empty
    val qualification =
      if (communities.exists(_.converged.contains(false)))
        " Community-derived fields are iteration-limited (iterations=" + communities
          .flatMap(_.iterations)
          .max + ")."
      else ""
    val approximate =
      if (
        cited.exists(i => kind(i) == "distance-estimate") && t.values
          .exists(v => estimateFields(v.field))
      )
        " Distance estimates are approximate."
      else ""
    if (t.claimType == RuntimeClaimType.Semantic)
      "Descriptive semantic context is available; it does not establish graph facts."
    else {
      val scope =
        if (t.claimType == RuntimeClaimType.Ranking || t.claimType == RuntimeClaimType.Bridge)
          bundle.runtime
            .flatMap(_.rankingScope)
            .map(value => " Ranking scope: " + value)
            .getOrElse("")
        else ""
      s"$subject: $fields (window=${t.windowIds.mkString(",")})." + qualification + approximate + scope
    }
  }
}

/** A deliberately narrow language for optional interpretation avoids heuristically guessing names.
  * Unknown words fail closed, including unseen researcher names and identifiers.
  */
object InterpretationGuard {
  private val words = Set(
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "between",
    "breadth",
    "bridge",
    "bridges",
    "broad",
    "broader",
    "by",
    "can",
    "collaboration",
    "collaborations",
    "communities",
    "community",
    "connect",
    "connected",
    "connection",
    "connections",
    "connectivity",
    "context",
    "degree",
    "dense",
    "descriptive",
    "different",
    "diverse",
    "differ",
    "evidence",
    "for",
    "from",
    "high",
    "higher",
    "importance",
    "in",
    "intensity",
    "is",
    "it",
    "limited",
    "may",
    "network",
    "networks",
    "of",
    "or",
    "participation",
    "patterns",
    "reflect",
    "reflects",
    "repeated",
    "research",
    "role",
    "roles",
    "separate",
    "shows",
    "structural",
    "structure",
    "suggest",
    "suggests",
    "support",
    "team",
    "teams",
    "than",
    "that",
    "the",
    "their",
    "these",
    "this",
    "through",
    "ties",
    "to",
    "together",
    "uncertain",
    "uncertainty",
    "with",
    "within"
  )
  def accept(text: String): Boolean = text.trim.isEmpty ||
    (text == text.toLowerCase(java.util.Locale.ROOT) && text.matches("[a-z ,.?!;:'()\\-]+") &&
      "[a-z]+".r.findAllIn(text).forall(words))
}
