package edu.uic.cs441.scholarchain.core

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import upickle.default.ReadWriter
import scala.util.control.NonFatal

final case class RuntimeModelConfig(
    modelId: String,
    modelVersion: String,
    region: String,
    temperature: Double
) derives ReadWriter

/** legacyWindow is an explicitly configured compatibility projection, never evidence of the actual
  * bounds. Runtime readers use windowId and optional bounds, including all-years.
  */
final case class RuntimeWindow(
    windowId: String,
    startYear: Option[Int],
    endYear: Option[Int],
    legacyWindow: YearWindow
) derives ReadWriter

/** Identity and provenance bounds are separate from graph-result limits. Defaults retain
  * compatibility with the original runtime-config JSON; operators can tune each bound in config.
  */
final case class RuntimeResolverConfig(
    maxDistinctCandidates: Int = 25,
    maxSourceIdsPerCandidate: Int = 16,
    maxEvidenceRefsPerCandidate: Int = 32,
    maxAffiliationsPerCandidate: Int = 16,
    maxRunIdsPerCandidate: Int = 8
) derives ReadWriter

final case class RuntimeStageDeadlines(
    plannerMs: Long,
    resolverMs: Long,
    metricsMs: Long,
    pathMs: Long,
    communityMs: Long,
    semanticMs: Long,
    evidenceMs: Long,
    synthesisMs: Long,
    verificationMs: Long,
    auditMs: Long
) derives ReadWriter {
  def all: Vector[Long] = Vector(
    plannerMs,
    resolverMs,
    metricsMs,
    pathMs,
    communityMs,
    semanticMs,
    evidenceMs,
    synthesisMs,
    verificationMs,
    auditMs
  )
  def criticalPathMillis: BigInt = BigInt(plannerMs) + resolverMs +
    Vector(
      metricsMs,
      pathMs,
      communityMs,
      semanticMs
    ).max + evidenceMs + synthesisMs + verificationMs + auditMs
}
final case class RuntimeConfig(
    schemaVersion: String,
    model: RuntimeModelConfig,
    plannerPromptVersion: String,
    plannerSchemaVersion: String,
    synthesisPromptVersion: String,
    synthesisSchemaVersion: String,
    retrieval: RetrievalConfig,
    operations: OperationsConfig,
    deadlines: RuntimeStageDeadlines,
    malformedRetries: Int,
    maxInputBytes: Int,
    maxOutputTokens: Int,
    retrievalMode: RetrievalMode,
    evidenceOnly: Boolean,
    windows: Vector[RuntimeWindow],
    defaultWindowId: String,
    defaultRankingMeasure: String,
    resolver: RuntimeResolverConfig = RuntimeResolverConfig()
) derives ReadWriter {
  def windowIds: Vector[String] = windows.map(_.windowId)
}
object RuntimeConfigValidation {
  val schemaVersion = "scholarchain.runtime-config.v1"
  def check(config: RuntimeConfig): Vector[String] = {
    val text = Vector(
      config.model.modelId,
      config.model.modelVersion,
      config.model.region,
      config.plannerPromptVersion,
      config.plannerSchemaVersion,
      config.synthesisPromptVersion,
      config.synthesisSchemaVersion,
      config.retrieval.fusionPolicyVersion,
      config.defaultRankingMeasure
    )
    Vector(
      Option.when(config.schemaVersion != schemaVersion)("unsupported-runtime-config-schema"),
      Option.when(text.exists(_.trim.isEmpty))("blank-runtime-config-value"),
      Option.when(
        !config.model.temperature.isFinite || config.model.temperature < 0 || config.model.temperature > 1
      )("invalid-model-temperature"),
      Option.when(
        config.deadlines.all.exists(_ <= 0) || config.operations.synchronousDeadlineMs <= 0 ||
          config.deadlines.criticalPathMillis > config.operations.synchronousDeadlineMs
      )("runtime-deadline-budget-exceeded"),
      Option.when(
        config.retrieval.graphLimit <= 0 || config.retrieval.vectorLimit <= 0 || config.retrieval.contextTokenBudget <= 0 ||
          config.retrieval.maxPathDepth <= 0
      )("invalid-runtime-retrieval-bound"),
      Option.when(
        config.operations.maxConcurrentLlmCalls <= 0 || config.operations.maxWorkflowRetries < 0
      )("invalid-runtime-operation-bound"),
      Option.when(
        Vector(
          config.resolver.maxDistinctCandidates,
          config.resolver.maxSourceIdsPerCandidate,
          config.resolver.maxEvidenceRefsPerCandidate,
          config.resolver.maxAffiliationsPerCandidate,
          config.resolver.maxRunIdsPerCandidate
        ).exists(_ <= 0)
      )("invalid-runtime-resolver-bound"),
      Option.when(
        config.malformedRetries < 0 || config.malformedRetries > 1 || config.maxInputBytes <= 0 || config.maxOutputTokens <= 0
      )("invalid-runtime-model-bound"),
      Option.when(
        config.windows.isEmpty || config.windowIds.distinct != config.windowIds || !config.windowIds
          .contains(config.defaultWindowId)
      )("invalid-runtime-window-catalog"),
      Option.when(config.windows.exists { w =>
        !w.windowId.matches("[a-z0-9][a-z0-9._-]*") ||
        w.startYear.exists(y => y < 1000 || y > 9999) || w.endYear.exists(y =>
          y < 1000 || y > 9999
        ) ||
        (for (a <- w.startYear; b <- w.endYear) yield a > b).getOrElse(false) ||
        w.legacyWindow.startYear < 1000 || w.legacyWindow.endYear > 9999 || w.legacyWindow.startYear > w.legacyWindow.endYear
      })("invalid-runtime-window-definition"),
      Option.when(!RuntimeRankingMetric.values.exists(_.wire == config.defaultRankingMeasure))(
        "unsupported-default-ranking-measure"
      )
    ).flatten
  }
}
object RuntimeConfigLoader {

  /** File content only; never reads credentials, .env, JVM properties or remote configuration. */
  def fromJson(json: String): Either[Vector[String], RuntimeConfig] =
    try {
      val config = upickle.default.read[RuntimeConfig](json)
      val errors = RuntimeConfigValidation.check(config)
      if (errors.isEmpty) Right(config) else Left(errors)
    } catch { case NonFatal(_) => Left(Vector("malformed-runtime-config")) }
  def load(path: Path): Either[Vector[String], RuntimeConfig] =
    try fromJson(Files.readString(path, UTF_8))
    catch { case NonFatal(_) => Left(Vector("runtime-config-unavailable")) }
}
