package edu.uic.cs441.scholarchain.core

/** New runtime evidence binds the complete persisted item, including provenance and runtime
  * payload, while legacy unmarked records retain their original locator-only ID contracts.
  */
object RuntimeEvidenceIds {
  val version: String = "runtime-evidence-content-v1"

  def bind(item: EvidenceItem): Either[DomainViolation, EvidenceItem] = item.runtime match {
    case None => Left(invalid("runtime-content-binding-requires-runtime"))
    case Some(payload) if payload.contentBindingVersion.exists(_ != version) =>
      Left(invalid("unsupported-runtime-evidence-content-binding"))
    case Some(payload) =>
      val marked = item.copy(runtime = Some(payload.copy(contentBindingVersion = Some(version))))
      expectedId(marked).map(id => marked.copy(evidenceId = id))
  }

  def expectedId(item: EvidenceItem): Either[DomainViolation, String] =
    if (!item.runtime.exists(_.contentBindingVersion.contains(version)))
      Left(invalid("unsupported-runtime-evidence-content-binding"))
    else {
      val tree = upickle.default.writeJs(item)
      tree.obj.remove("evidenceId")
      val hash = StableIds.sha256Hex(canonical(tree).render())
      val prefix = item.evidenceType match {
        case EvidenceType.GraphPath         => "evidence:graph-path:"
        case EvidenceType.CoauthorEdge      => "evidence:edge:"
        case EvidenceType.Metric            => "evidence:metric:"
        case EvidenceType.ResearcherProfile => "profile:"
        case _                              => "chunk:"
      }
      Right(prefix + hash)
    }

  private def canonical(value: ujson.Value): ujson.Value = value match {
    case obj: ujson.Obj =>
      ujson.Obj.from(obj.obj.toVector.sortBy(_._1).map { case (key, entry) =>
        key -> canonical(entry)
      })
    case arr: ujson.Arr => ujson.Arr.from(arr.value.map(canonical))
    case other          => other
  }

  private def invalid(message: String): DomainViolation =
    DomainViolation(ViolationCode.InconsistentRecord, message)
}
