package edu.uic.cs441.scholarchain.core

/** Immutable source observations, created only after full WorkRecord validation. No global
  * registration, URI fallback, or last-writer-wins behavior. A snapshot is part of observation
  * identity; runId records lineage and can change when an observation is reused downstream.
  */
final class WorkValidationContext private (
    private val works: Map[(SourceType, String, String), WorkRecord]
) {
  private[core] def lookup(provenance: Provenance): Option[WorkRecord] =
    works.get((provenance.source, provenance.sourceRecordId, provenance.datasetSnapshot))
}

object WorkValidationContext {
  def create(
      records: Vector[WorkRecord]
  ): Either[Vector[DomainViolation], WorkValidationContext] = {
    val errors =
      records.flatMap(work => DomainValidation.check(work).left.toOption.toVector.flatten)
    val grouped =
      records.groupBy(work => (work.source, work.sourceRecordId, work.provenance.datasetSnapshot))
    val collisions = grouped.toVector
      .sortBy { case ((source, id, snapshot), _) =>
        (source.wire, id, snapshot)
      }
      .collect {
        case ((source, id, snapshot), observations) if observations.distinct.size > 1 =>
          DomainViolation(
            ViolationCode.InconsistentRecord,
            s"conflicting work observations for ${source.wire}, $id, $snapshot"
          )
      }
    if (errors.nonEmpty || collisions.nonEmpty)
      Left((errors ++ collisions).distinct.sortBy(e => (e.code.toString, e.message)))
    else Right(new WorkValidationContext(grouped.map { case (key, values) => key -> values.head }))
  }
}
