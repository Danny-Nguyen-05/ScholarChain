package edu.uic.cs441.scholarchain.storage

import StorageResult.*

private[storage] object NeptuneLoadStates {
  val pending: Set[String] = Set("LOAD_NOT_STARTED", "LOAD_IN_QUEUE", "LOAD_IN_PROGRESS")
  def sanitized(state: String): String =
    if (state.matches("[A-Z0-9_]{1,80}")) state else "UNKNOWN_" + ExportFiles.hash(state).take(12)
  def failureCode(state: String): String =
    "neptune-load-" + sanitized(state).toLowerCase(java.util.Locale.ROOT)
}
private[storage] final case class NeptuneJobAttempt(
    version: String,
    loadId: Option[String],
    recovery: Boolean
)

/** Append-only job attempts and terminal markers. A timeout does not mark a provider job final. */
private[storage] final class NeptuneJobAttempts(
    registry: ArtifactRegistry,
    runId: String,
    fingerprint: String
) {
  private val jobs = "neptune-job:" + runId + ":" + fingerprint
  private val failures = "neptune-failed:" + runId + ":" + fingerprint
  private val prefix = "attempt-"
  private def fresh(previous: Option[String]): StorageResult[NeptuneJobAttempt] = {
    val number = previous match {
      case None | Some("legacy") => Some(1L)
      case Some(v) if v.matches("attempt-[0-9]{20}") =>
        v.stripPrefix(prefix).toLongOption.filter(_ < Long.MaxValue).map(_ + 1)
      case _ => None
    }
    number
      .map(n => Found(NeptuneJobAttempt(prefix + f"$n%020d", None, previous.nonEmpty)))
      .getOrElse(Rejected("invalid-loader-attempt-version"))
  }
  private def active(record: ArtifactRecord, version: String): StorageResult[NeptuneJobAttempt] = {
    if (record.hash != fingerprint || record.uri.isEmpty)
      return Rejected("loader-job-binding-conflict")
    registry.get(failures, version) match {
      case Missing => Found(NeptuneJobAttempt(version, Some(record.uri), false))
      case result if StorageResult.successful(result) => fresh(Some(version))
      case _ => Rejected("loader-failure-registry-unavailable")
    }
  }
  def select(): StorageResult[NeptuneJobAttempt] = registry.latest(jobs) match {
    case Missing =>
      registry.get("neptune-job:" + runId, fingerprint) match {
        case Missing                          => fresh(None)
        case r if StorageResult.successful(r) => active(StorageResult.value(r).get, "legacy")
        case _                                => Rejected("loader-job-registry-unavailable")
      }
    case r if StorageResult.successful(r) =>
      val record = StorageResult.value(r).get; active(record, record.version)
    case _ => Rejected("loader-job-registry-unavailable")
  }
  def recordJob(attempt: NeptuneJobAttempt, loadId: String): StorageResult[ArtifactRecord] =
    registry.register(jobs, attempt.version, loadId, fingerprint)
  def recordFailure(attempt: NeptuneJobAttempt, state: String): StorageResult[ArtifactRecord] =
    registry.register(failures, attempt.version, NeptuneLoadStates.sanitized(state), fingerprint)
}
