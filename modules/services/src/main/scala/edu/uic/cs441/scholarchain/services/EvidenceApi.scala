package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.core.*

private[services] object PortResult {
  def read[A](r: StorageResult[A]): Either[ApiError, A] = r match {
    case StorageResult.Missing =>
      Left(ApiError(404, "NOT_FOUND", "The requested record was not found."))
    case other => StorageResult.value(other).toRight(ApiError.downstream)
  }
}
final class EvidenceApi(
    store: EvidenceBundleStore,
    audits: RuntimeAuditStore,
    sessions: Option[QuerySessionStore] = None
) {
  def evidence(id: String): Either[ApiError, ApiReply] =
    PortResult.read(store.getItem(id)).map { item =>
      ApiReply(
        200,
        ujson.Obj(
          "evidenceId" -> item.evidenceId,
          "evidenceType" -> item.evidenceType.wire,
          "workId" -> upickle.default.writeJs(item.workId),
          "sourceDataset" -> item.provenance.source.wire,
          "sourceRecordId" -> item.provenance.sourceRecordId,
          "snapshot" -> item.provenance.datasetSnapshot,
          "sourceUri" -> item.sourceUri,
          "text" -> upickle.default.writeJs(item.text),
          "textS3Uri" -> (if (item.sourceUri.startsWith("s3://")) ujson.Str(item.sourceUri)
                          else ujson.Null),
          "graphPath" -> upickle.default.writeJs(item.graphPath),
          "chunkId" -> upickle.default.writeJs(item.chunkId),
          "score" -> item.score,
          "provenance" -> upickle.default.writeJs(item.provenance),
          "supportingContent" -> item.runtime.map(upickle.default.writeJs(_)).getOrElse(ujson.Null)
        )
      )
    }
  def queryEvidence(id: String): Either[ApiError, ApiReply] =
    PortResult.read(audits.get(id)).map { audit =>
      ApiReply(
        200,
        ujson.Obj(
          "queryId" -> id,
          "evidenceIds" -> ujson.Arr.from(audit.record.toVector.flatMap(_.evidenceIds))
        )
      )
    }
  def explain(id: String): Either[ApiError, ApiReply] =
    PortResult.read(audits.get(id)).map { audit =>
      val record = audit.record
      // Only observable, persisted audit fields are projected. Neither attempted model prose nor
      // hidden prompts/reasoning are returned. Missing measurements remain null, never guessed.
      ApiReply(
        200,
        ujson.Obj(
          "queryId" -> audit.queryId,
          "traceId" -> audit.traceId,
          "queryPlan" -> record.map(r => upickle.default.writeJs(r.plan)).getOrElse(ujson.Null),
          "stagesExecuted" -> sessions
            .flatMap(s => StorageResult.value(s.get(id)))
            .flatMap(s =>
              try ujson.read(s.payload).obj.get("observedStages")
              catch { case _: Exception => None }
            )
            .getOrElse(ujson.Null),
          "stageFailures" -> upickle.default.writeJs(audit.stageFailures),
          "promptVersions" -> ujson.Arr.from(audit.modelUsage.map(_.promptVersion).distinct),
          "modelVersions" -> upickle.default.writeJs(audit.modelUsage),
          "evidenceIds" -> ujson.Arr.from(record.toVector.flatMap(_.evidenceIds)),
          "scoreComponents" -> ujson.Arr.from(
            record.toVector
              .flatMap(_.evidenceIds)
              .flatMap(id => StorageResult.value(store.getItem(id)))
              .map(item =>
                ujson.Obj(
                  "evidenceId" -> item.evidenceId,
                  "score" -> item.score,
                  "source" -> "persisted-evidence-item"
                )
              )
          ),
          "counters" -> ujson.Obj(
            "latencyMillis" -> audit.latencyMillis,
            "retries" -> ujson.Null,
            "cacheHits" -> ujson.Null,
            "attemptedClaims" -> record.map(_.attemptedClaims.size).getOrElse(0),
            "verifiedClaims" -> record.toVector
              .flatMap(_.verification.claims)
              .count(_.verdict == ClaimVerdict.Verified),
            "rejectedClaims" -> record.map(_.verification.rejectedClaims.size).getOrElse(0)
          ),
          "verificationStatus" -> record
            .map(r => r.verification.overallStatus.wire)
            .getOrElse(audit.outcome),
          "verification" -> record
            .map(r => upickle.default.writeJs(r.verification.claims))
            .getOrElse(ujson.Arr()),
          "outcome" -> audit.outcome,
          "reason" -> upickle.default.writeJs(audit.reason),
          "metricVersions" -> ujson.Arr.from(record.toVector.flatMap(_.metricVersions)),
          "graphRunIds" -> ujson.Arr.from(record.toVector.flatMap(_.graphRunIds))
        )
      )
    }
}
