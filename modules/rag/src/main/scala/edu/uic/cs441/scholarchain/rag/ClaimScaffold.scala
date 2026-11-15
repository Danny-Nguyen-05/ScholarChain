package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8

/** One exact claim the deterministic verifier accepts for the cited evidence item. */
private[rag] final case class ScaffoldClaim(
    claimId: String,
    claim: TypedAnswerClaim,
    evidenceIds: Vector[String]
)

/** Model-visible scaffold of verifiable claims. Every id, type, template, window and typed value is
  * computed from the stored evidence through [[ClaimContract]], the same functions the verifier
  * applies, so a model that copies a scaffold claim verbatim is verified. The scaffold never
  * carries descriptive (vector) evidence and is empty in vector retrieval mode, because the
  * verifier rejects deterministic claims there. Its size is bounded by the evidence items already
  * admitted to the bundle and, in addition, by an explicit byte budget; whole claims are dropped
  * (never truncated) when they do not fit.
  */
private[rag] object ClaimScaffold {
  import ClaimContract.*

  /** The one claim type the verifier accepts for each deterministic evidence kind. */
  def claimType(item: EvidenceItem): Option[RuntimeClaimType] = kind(item) match {
    case "metrics" | "distance-estimate"      => Some(RuntimeClaimType.Metric)
    case "ranking"                            => Some(RuntimeClaimType.Ranking)
    case "path" | "direct-coauthors" | "edge" => Some(RuntimeClaimType.Path)
    case "community"                          => Some(RuntimeClaimType.Community)
    case "bridge"                             => Some(RuntimeClaimType.Bridge)
    case "temporal"                           => Some(RuntimeClaimType.Temporal)
    case "identity"                           => Some(RuntimeClaimType.Identity)
    case "publication"                        => Some(RuntimeClaimType.Publication)
    case _                                    => None
  }

  private val qualifications = Vector("converged", "iterations", "approximate")

  /** Values for one item, restricted to fields `allowed` accepts with the stored `expected` value.
    */
  private def values(
      plan: QueryPlan,
      item: EvidenceItem,
      typ: RuntimeClaimType
  ): Vector[RuntimeClaimValue] = {
    val r = item.runtime.get
    val conversion = plan.runtime.exists(_.authorCountConversion)
    val candidates = (r.values.map(_.field) ++ qualifications).distinct
      .filter(f => f != "kind" && (conversion || !conversionFields(f)))
      .flatMap(f => expected(item, f))
    def probe(vs: Vector[RuntimeClaimValue]) =
      TypedAnswerClaim(typ, r.subjectIds, vs, r.windowIds, templateId(typ))
    // `allowed` depends on the other values for community qualification; iterate to a fixed point.
    var current = candidates
    var stable = false
    while (!stable) {
      val next = current.filter(v => allowed(probe(current), item, v.field))
      stable = next.size == current.size
      current = next
    }
    current
  }

  private def json(c: ScaffoldClaim): ujson.Obj = ujson.Obj(
    "claimId" -> c.claimId,
    "claimType" -> c.claim.claimType.wire,
    "subjectIds" -> ujson.Arr.from(c.claim.subjectIds),
    "values" -> ujson.Arr.from(c.claim.values.map { v =>
      ujson.Obj(
        "field" -> v.field,
        "number" -> v.number.map(ujson.Str(_)).getOrElse(ujson.Null),
        "text" -> v.text.map(ujson.Str(_)).getOrElse(ujson.Null),
        "ids" -> v.ids.map(xs => ujson.Arr.from(xs): ujson.Value).getOrElse(ujson.Null),
        "flag" -> v.flag.map(ujson.Bool(_): ujson.Value).getOrElse(ujson.Null)
      )
    }),
    "evidenceIds" -> ujson.Arr.from(c.evidenceIds),
    "windowIds" -> ujson.Arr.from(c.claim.windowIds),
    "templateId" -> c.claim.templateId
  )

  def toJson(claims: Vector[ScaffoldClaim]): ujson.Value = ujson.Arr.from(claims.map(json))
  def bytes(claims: Vector[ScaffoldClaim]): Int = toJson(claims).render().getBytes(UTF_8).length

  /** Claims in bundle order, dropping whole claims that would exceed `maxBytes` in total. */
  def build(plan: QueryPlan, bundle: EvidenceBundle, maxBytes: Int): Vector[ScaffoldClaim] = {
    val usable =
      DomainValidation.check(bundle).isRight &&
        !bundle.runtime.exists(_.retrievalMode == RetrievalMode.Vector)
    if (!usable) return Vector.empty
    val byId = bundle.items.map(i => i.evidenceId -> i).toMap
    val windows = requestedWindows(plan)
    val all = bundle.items
      .filter(i => i.runtime.exists(r => !r.descriptive && r.windowIds.forall(windows)))
      .flatMap { item =>
        claimType(item).flatMap { typ =>
          val vs = values(plan, item, typ)
          val r = item.runtime.get
          val foundPath = kind(item) == "path" &&
            r.values.exists(v => v.field == "pathStatus" && v.text.contains("Found"))
          Option.when(vs.nonEmpty && (!foundPath || pathComplete(item, byId)))(
            (
              kind(item),
              TypedAnswerClaim(typ, r.subjectIds, vs, r.windowIds, templateId(typ)),
              item.evidenceId
            )
          )
        }
      }
    var used = 2 // enclosing brackets
    all.zipWithIndex.flatMap { case ((k, typed, evidenceId), index) =>
      val claim = ScaffoldClaim(s"claim:$k:${index + 1}", typed, Vector(evidenceId))
      val size = json(claim).render().getBytes(UTF_8).length + 1
      Option.when(used + size <= maxBytes) { used += size; claim }
    }
  }
}
