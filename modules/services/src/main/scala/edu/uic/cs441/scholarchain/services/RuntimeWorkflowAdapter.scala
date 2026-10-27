package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.*

/** The plan resolver must use the configured planner and corpus windows. Every explicitly requested
  * constraint is checked before retrieval: silently dropping constraints is forbidden. This adapter
  * never constructs a provider client or invents a researcher summary.
  */
final class RuntimeWorkflowAdapter(
    workflow: RuntimeAnswerWorkflow,
    resolvePlan: (QueryRequest, RequestContext) => Either[ApiError, QueryPlan],
    evidenceStore: Option[edu.uic.cs441.scholarchain.storage.EvidenceBundleStore] = None
) extends QueryWorkflow {
  def run(
      request: QueryRequest,
      context: RequestContext,
      stage: String => Unit
  ): Either[ApiError, WorkflowOutput] = {
    stage("PLANNING")
    resolvePlan(request, context).flatMap { plan =>
      if (!matches(request, plan)) Left(ApiError.unsupported)
      else {
        stage("RETRIEVAL")
        workflow.runPlan(plan, context.queryId) match {
          case AnswerWorkflowResult.Completed(answer, audit) =>
            stage("AUDIT")
            val output = request.json.obj.get("output")
            def include(key: String) = output.flatMap(_.obj.get(key)).forall(_.bool)
            val claims = answer.claims.map { claim =>
              val json = upickle.default.writeJs(claim)
              if (!include("includeUncertainty")) json.obj.remove("uncertainty")
              if (!include("includeEvidence")) json.obj.remove("evidenceIds")
              json
            }
            val body =
              ujson.Obj(
                "summary" -> answer.summary,
                "researchers" -> researchers(answer),
                "evidenceBundleId" -> answer.evidenceBundleId
              )
            if (include("includeScores"))
              body("scores") = ujson.Arr.from(
                evidenceStore.toVector
                  .flatMap(s =>
                    edu.uic.cs441.scholarchain.storage.StorageResult
                      .value(s.get(answer.evidenceBundleId))
                  )
                  .flatMap(_.items)
                  .map(item => ujson.Obj("evidenceId" -> item.evidenceId, "score" -> item.score))
              )
            if (include("includeUncertainty")) body("uncertainty") = answer.uncertainty
            if (!include("includeEvidence")) body.obj.remove("evidenceBundleId")
            val abstained = audit.outcome == "ABSTAINED"
            Right(
              WorkflowOutput(
                body,
                claims,
                audit.record
                  .map(r => RuntimeWorkflowAdapter.verificationLabel(r.verification))
                  .getOrElse("UNVERIFIED"),
                abstained
              )
            )
          case AnswerWorkflowResult.Abstained(_, _, candidates) =>
            Right(
              WorkflowOutput(
                ujson.Obj(
                  "summary" -> "Insufficient verified evidence to answer.",
                  "researchers" -> ujson.Arr(),
                  "candidates" -> upickle.default.writeJs(candidates)
                ),
                verificationStatus = "ABSTAINED",
                abstained = true
              )
            )
          case AnswerWorkflowResult.Unsupported(_, _) => Left(ApiError.unsupported)
          case AnswerWorkflowResult.EvidenceOnly(_, _) =>
            Left(
              ApiError(
                422,
                "EVIDENCE_ONLY_PLAN",
                "An answer query requires synthesis and verification."
              )
            )
          case AnswerWorkflowResult.Failed(failure) =>
            if (failure.reason.contains("deadline")) Left(ApiError.timeout.copy(retryable = false))
            else Left(ApiError.downstream.copy(retryable = false))
        }
      }
    }
  }
  private def researchers(answer: AnswerResponse): ujson.Value = {
    val bundle = evidenceStore.flatMap(s =>
      edu.uic.cs441.scholarchain.storage.StorageResult.value(s.get(answer.evidenceBundleId))
    )
    val candidates = bundle.toVector
      .flatMap(_.runtime.toVector.flatMap(_.resolvedCandidates))
      .map(c => c.researcherId -> c)
      .toMap
    val claims = answer.claims
      .filter(c => c.verificationStatus == VerificationStatus.Verified)
      .flatMap(c => c.runtime.map(t => c -> t))
    val ids = claims.flatMap(_._2.subjectIds).distinct
    ujson.Arr.from(ids.map { id =>
      val obj = ujson.Obj("researcherId" -> id)
      candidates.get(id).foreach(c => obj("displayName") = c.displayName)
      val relevant = claims.filter(_._2.subjectIds == Vector(id))
      obj("claimIds") = ujson.Arr.from(relevant.map(_._1.claimId))
      relevant.flatMap(_._2.values).foreach { v =>
        if (
          Set(
            "publicationCount",
            "distinctCoauthorCount",
            "weightedDegree",
            "averageCoauthorsPerPaper",
            "maximumCoauthorsOnOnePaper",
            "componentId",
            "communityId"
          )(v.field)
        ) {
          v.number.foreach(n => obj(v.field) = ujson.Str(n))
          v.text.foreach(t => obj(v.field) = ujson.Str(t))
        }
      }
      obj
    })
  }
  private def matches(request: QueryRequest, plan: QueryPlan): Boolean = {
    val json = request.json
    val constraints = json.obj.get("constraints")
    val analysis = json.obj.get("analysis")
    val retrieval = json.obj.get("retrieval")
    def check(section: Option[ujson.Value], key: String)(f: ujson.Value => Boolean): Boolean =
      section.flatMap(_.obj.get(key)).forall(f)
    def strings(v: ujson.Value) = v.arr.toVector.map(_.str)
    val operations = Map(
      "includeTeamSize" -> Set(QueryOperation.MaximumTeamSize),
      "includeBridgeMetrics" -> Set(QueryOperation.BridgeRanking),
      "includeCommunities" -> Set(QueryOperation.CommunityComparison),
      "includePaths" -> Set(QueryOperation.DirectCoauthors, QueryOperation.ShortestPath)
    )
    check(json.obj.get("output"), "includeScores")(v => !v.bool || evidenceStore.nonEmpty) &&
    plan.question == request.question && !plan.runtime.exists(_.evidenceOnly) &&
    check(constraints, "yearFrom")(_.num.toInt == plan.window.startYear) &&
    check(constraints, "yearTo")(_.num.toInt == plan.window.endYear) &&
    check(constraints, "topics")(strings(_) == plan.topicFilters) &&
    check(constraints, "institutions")(strings(_) == plan.institutionFilters) &&
    check(constraints, "venues")(strings(_) == plan.venueFilters) &&
    check(analysis, "rankingMetric")(v => plan.rankingMetric.exists(_.wire == v.str)) &&
    operations.forall { (key, ops) =>
      check(analysis, key)(v => !v.bool || plan.operations.exists(ops))
    } &&
    check(retrieval, "graphLimit")(_.num.toInt == plan.graphLimit) &&
    check(retrieval, "vectorLimit")(_.num.toInt == plan.vectorLimit) &&
    check(retrieval, "maxPathDepth")(_.num.toInt == plan.maxPathDepth)
  }
}

object RuntimeWorkflowAdapter {
  private[services] def verificationLabel(verification: VerificationResult): String =
    verification.overallStatus match {
      case VerificationStatus.PartiallyVerified => "PARTIAL"
      case other                                => other.wire
    }
}
