package edu.uic.cs441.scholarchain.storage

import StorageResult.*
import scala.collection.mutable

/** Fake loader performs deterministic ID validation, no network or query synthesis. */
final class InMemoryGraphLoader extends GraphLoader {
  private val loads = mutable.Map.empty[String, (GraphLoadManifest, GraphLoadStatus)]
  def submitBulkLoad(m: GraphLoadManifest): StorageResult[GraphLoadStatus] = synchronized {
    if (
      m.runId.isEmpty || m.nodeIds.distinct.size != m.nodeIds.size || m.edgeIds.distinct.size != m.edgeIds.size
    ) Rejected("invalid-graph-manifest")
    else
      loads.get(m.runId) match {
        case Some((old, s)) if old == m => Unchanged(s)
        case Some(_)                    => Rejected("immutable-conflict")
        case None =>
          val s = GraphLoadStatus(m.runId, "complete"); loads(m.runId) = m -> s; Written(s)
      }
  }
  def status(id: String): StorageResult[GraphLoadStatus] = synchronized {
    loads.get(id).map(p => Found(p._2)).getOrElse(Missing)
  }
}
