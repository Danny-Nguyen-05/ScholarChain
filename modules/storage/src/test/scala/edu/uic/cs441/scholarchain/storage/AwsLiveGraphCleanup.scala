package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.ExecuteOpenCypherQueryRequest
import StorageResult.*

/** Test-only cleanup seam. A graph batch is journaled cleaned only after both exact mutation counts
  * and independent read-side absence checks succeed for every owned ID.
  */
private[storage] object AwsLiveGraphCleanup {
  def clean(
      writer: NeptunedataClient,
      readClient: NeptunedataClient,
      reader: GraphReader,
      runId: String,
      journal: LiveRunManifest
  ): Unit = {
    val items =
      journal.all.filter(i => Set("neptune-edge", "neptune-node")(i.kind) && i.state == "created")
    require(items.forall(_.expectedHash == runId), "graph cleanup ownership mismatch")
    val edges = items.filter(_.kind == "neptune-edge").map(_.key)
    val nodes = items.filter(_.kind == "neptune-node").map(_.key)
    require(
      edges.distinct.size == edges.size && nodes.distinct.size == nodes.size,
      "duplicate cleanup ID"
    )
    def remove(ids: Vector[String], query: String): Unit = if (ids.nonEmpty) {
      val response = writer.executeOpenCypherQuery(
        ExecuteOpenCypherQueryRequest
          .builder()
          .openCypherQuery(query)
          .parameters(ujson.Obj("ids" -> ujson.Arr.from(ids), "run" -> runId).render())
          .build()
      )
      val rows = AwsDocumentJson.value(response.results()).arr
      require(rows.size == 1, "graph cleanup count response malformed")
      val count = rows.head("deleted") match {
        case AwsJson.NumberValue(number) => number.longValueExact()
        case _ =>
          throw new IllegalArgumentException("graph cleanup count must be exact numeric value")
      }
      require(count == ids.size.toLong, "graph cleanup matched count differs from owned IDs")
    }
    remove(
      edges,
      "USING QUERY:TIMEOUTMILLISECONDS 5000 MATCH ()-[r]-() WHERE id(r) IN $ids AND r.liveIntegrationRun = $run WITH DISTINCT r DELETE r RETURN count(r) AS deleted"
    )
    remove(
      nodes,
      "USING QUERY:TIMEOUTMILLISECONDS 5000 MATCH (n) WHERE id(n) IN $ids AND n.liveIntegrationRun = $run WITH DISTINCT n DELETE n RETURN count(n) AS deleted"
    )
    edges.foreach { id =>
      val response = readClient.executeOpenCypherQuery(
        ExecuteOpenCypherQueryRequest
          .builder()
          .openCypherQuery(
            "USING QUERY:TIMEOUTMILLISECONDS 5000 MATCH ()-[r]-() WHERE id(r) = $id RETURN DISTINCT id(r) AS edgeId LIMIT 1"
          )
          .parameters(ujson.Obj("id" -> id).render())
          .build()
      )
      require(
        AwsDocumentJson.value(response.results()).arr.isEmpty,
        "graph edge remains after cleanup"
      )
    }
    nodes.foreach(id =>
      require(reader.node(id) == Missing, "graph node absence unverified after cleanup")
    )
    // Deliberately all-or-none journaling: a partially deleted or unreadable batch stays created
    // for operator reconciliation instead of making an unverified successful-cleanup claim.
    items.foreach(item => journal.record(item.copy(state = "cleaned")))
  }
}
