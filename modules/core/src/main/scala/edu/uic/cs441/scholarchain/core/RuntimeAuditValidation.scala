package edu.uic.cs441.scholarchain.core

/** Validates the durable execution envelope, not the truth of attempted claims. Rejected and
  * malformed claim proposals must remain observable in the audit instead of being discarded.
  */
object RuntimeAuditValidation {
  val schemaVersion: String = "scholarchain.runtime-audit.v1"
  val outcomes: Set[String] = Set("ANSWERED", "ABSTAINED", "UNSUPPORTED", "FAILED", "EVIDENCE_ONLY")

  def check(value: RuntimeAuditEnvelope): Vector[String] = {
    val basic = Vector(
      Option.when(value.schemaVersion != schemaVersion)("unsupported-runtime-audit-schema"),
      Option
        .when(value.queryId.trim.isEmpty || value.traceId.trim.isEmpty)("blank-runtime-audit-key"),
      Option.when(!outcomes(value.outcome))("unsupported-runtime-audit-outcome"),
      Option.when(value.reason.exists(_.trim.isEmpty))("blank-runtime-audit-reason"),
      Option.when(value.latencyMillis < 0)("invalid-runtime-audit-latency"),
      Option.when(!value.answerHash.matches("[0-9a-f]{64}"))("invalid-runtime-audit-answer-hash"),
      Option.when(value.stageFailures.exists(f => f.stage.trim.isEmpty || f.reason.trim.isEmpty))(
        "invalid-runtime-audit-stage-failure"
      ),
      Option.when(Set("ANSWERED", "EVIDENCE_ONLY")(value.outcome) && value.record.isEmpty)(
        "runtime-audit-record-required"
      ),
      Option.when(
        (value.outcome == "EVIDENCE_ONLY" && !value.evidenceOnly) ||
          (value.outcome == "ANSWERED" && value.evidenceOnly)
      )("runtime-audit-evidence-only-mismatch")
    ).flatten
    basic ++ value.modelUsage.flatMap(usage) ++ value.record.toVector.flatMap { record =>
      Vector(
        Option.when(
          record.queryId != value.queryId || record.traceId != value.traceId ||
            record.answerHash != value.answerHash
        )("runtime-audit-record-mismatch"),
        Option.when(DomainValidation.check(record.plan).isLeft)("invalid-runtime-audit-plan"),
        Option.when(record.latencyMillis < 0)("invalid-runtime-audit-record-latency"),
        Option.when(
          record.resolvedResearcherIds.distinct != record.resolvedResearcherIds ||
            record.resolvedResearcherIds.exists(StableIds.parseResearcherId(_).isLeft)
        )(
          "invalid-runtime-audit-resolved-identities"
        ),
        Option.when(
          record.evidenceIds.distinct != record.evidenceIds ||
            record.evidenceIds.exists(StableIds.parseEvidenceId(_).isLeft)
        )(
          "invalid-runtime-audit-evidence-identities"
        ),
        Option.when(
          record.graphRunIds.distinct != record.graphRunIds ||
            record.graphRunIds.exists(StableIds.parseRunId(_).isLeft) ||
            record.metricVersions.distinct != record.metricVersions ||
            record.metricVersions.exists(_.trim.isEmpty)
        )("invalid-runtime-audit-source-versions")
      ).flatten ++ record.modelUsage.flatMap(usage)
    }
  }

  private def usage(value: RuntimeModelUsage): Vector[String] = Vector(
    Option.when(
      Vector(value.modelId, value.modelVersion, value.promptVersion, value.schemaVersion)
        .exists(_.trim.isEmpty) || value.region.exists(_.trim.isEmpty)
    )("invalid-runtime-audit-model-version"),
    Option.when(value.inputTokens.exists(_ < 0) || value.outputTokens.exists(_ < 0))(
      "invalid-runtime-audit-token-count"
    )
  ).flatten
}
