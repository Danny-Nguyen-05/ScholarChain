package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*

/** The single source of the verifier's per-claim-type field contract. ClaimVerificationAgent
  * enforces it and ClaimScaffold derives the model-visible claims from it, so the two cannot drift
  * apart.
  */
private[rag] object ClaimContract {
  val metricFields = Set(
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
  val bridgeFields = Set(
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
  val communityFields = Set(
    "communityId",
    "size",
    "selectedMemberIds",
    "selectedCrossCommunityEdgeCount",
    "neighborCommunityIds",
    "truncated",
    "communityQualification"
  )
  val pathFields = Set(
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
  val estimateFields = Set(
    "componentId",
    "effectiveDiameterP90",
    "distanceMethod",
    "distanceP90Approximate",
    "sampleSourceCount",
    "seed",
    "meanDistance",
    "reachedPairCount"
  )
  val temporalFields = Set(
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
  val qualificationFields = Set("converged", "iterations", "approximate")
  def kind(item: EvidenceItem): String = item.runtime.toVector
    .flatMap(_.values)
    .find(_.field == "kind")
    .flatMap(_.text)
    .getOrElse("")
  def allowed(typed: TypedAnswerClaim, item: EvidenceItem, field: String): Boolean = {
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
  def expected(item: EvidenceItem, field: String): Option[RuntimeClaimValue] = {
    val r = item.runtime.get
    field match {
      case "approximate" => Some(RuntimeClaimValue(field, flag = Some(r.approximate)))
      case "converged"   => r.converged.map(v => RuntimeClaimValue(field, flag = Some(v)))
      case "iterations" =>
        r.iterations.map(v => RuntimeClaimValue(field, number = Some(v.toString)))
      case _ => r.values.find(_.field == field)
    }
  }
  def same(a: RuntimeClaimValue, b: RuntimeClaimValue): Boolean =
    if (a.field != b.field) false
    else if (a.number.nonEmpty && b.number.nonEmpty)
      try BigDecimal(a.number.get) == BigDecimal(b.number.get)
      catch { case _: NumberFormatException => false }
    else a == b

  def templateId(claimType: RuntimeClaimType): String =
    claimType.wire.toLowerCase(java.util.Locale.ROOT) + "-v1"
  val conversionFields = Set("maximumTotalAuthors", "authorCountConversion")
  def requestedWindows(plan: QueryPlan): Set[String] =
    plan.runtime.toVector.flatMap(o => o.windowIds ++ o.comparisonWindowIds).toSet

  def pathComplete(item: EvidenceItem, byId: Map[String, EvidenceItem]): Boolean = {
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

}
