package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import scala.util.control.NonFatal

/** Graph snapshot backed by the read-only directed graph port and the stored metric records. Edges
  * keep their stored start and end; an undirected type (see `GraphEdgeType.isUndirected`) is marked
  * so the graph API treats it as incident in every direction. A row with a stored provenance record
  * reports it. A row without one (coauthor edges) reports its stored evidence pointers instead and
  * a null provenance. A row with neither, or with malformed stored provenance, refuses the whole
  * read: nothing is inferred. Node and metric reads are the stored records, byte for byte.
  */
final class LiveGraphSnapshot(
    val snapshotId: String,
    reader: DirectedGraphReader,
    metricStore: ResearcherMetricStore,
    pageSize: Int = 100,
    scanLimit: Int = 10000
) extends GraphSnapshot {
  require(snapshotId.nonEmpty && pageSize > 0 && scanLimit > 0)
  def node(id: String): StorageResult[GraphNode] = reader.node(id)

  /** Fully typed core edges need provenance on every row, which loaded coauthor rows lack. */
  def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] =
    StorageResult.Rejected(LiveGraphSnapshot.coreEdgesUnavailable)
  def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord] =
    metricStore.get(id, window)

  private def failure(result: StorageResult[?]): StorageResult[Nothing] = result match {
    case StorageResult.Missing           => StorageResult.Missing
    case StorageResult.Rejected(code)    => StorageResult.Rejected(code)
    case StorageResult.Retried(_, inner) => failure(inner)
    case _                               => StorageResult.Rejected("edge-read-failed")
  }
  private def json(text: String): Either[String, ujson.Value] =
    try Right(ujson.read(text))
    catch { case NonFatal(_) => Left("malformed-edge-evidence") }
  private def convert(row: DirectedGraphEdge): Either[String, SnapshotEdge] = {
    val undirected = GraphEdgeType.values
      .find(_.wire == row.edgeType)
      .exists(GraphEdgeType.isUndirected)
    def edge(provenance: ujson.Value, evidence: Option[ujson.Value]) =
      SnapshotEdge(row.edgeId, row.edgeType, row.fromId, row.toId, undirected, provenance, evidence)
    row.provenance match {
      case Right(p) =>
        row.properties.get("sourceEvidenceJson") match {
          case None       => Right(edge(upickle.default.writeJs(p), None))
          case Some(text) => json(text).map(e => edge(upickle.default.writeJs(p), Some(e)))
        }
      case Left("edge-provenance-absent") =>
        (row.properties.get("evidenceTable"), row.properties.get("evidenceEdgeId")) match {
          case (Some(table), Some(edgeId)) =>
            val pointer = ujson.Obj(
              "kind" -> "stored-evidence-pointer",
              "evidenceTable" -> table,
              "evidenceEdgeId" -> edgeId
            )
            row.properties.get("windowId").foreach(w => pointer("windowId") = w)
            val works = row.properties.get("representativeWorkIdsJson") match {
              case None       => Right(())
              case Some(text) => json(text).map(v => pointer("representativeWorkIds") = v)
            }
            works.map(_ => edge(ujson.Null, Some(pointer)))
          case _ => Left("edge-provenance-absent")
        }
      case Left(code) => Left(code)
    }
  }

  override def incidentEdges(id: String, window: String): StorageResult[Vector[SnapshotEdge]] =
    incidentEdges(id, window, LiveGraphSnapshot.servedEdgeTypes)

  /** Community reads are the stored reader's own: the live (Neptune) reader answers from the
    * membership keys the loader wrote, and the local export reader from its loaded memberships.
    * Nothing is derived here.
    */
  override def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]] = reader.communityMembers(communityId, window, limit)
  override def crossCommunityEdges(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[GraphPage] = reader.crossCommunityEdges(communityId, window, limit)

  override def incidentEdges(
      id: String,
      window: String,
      edgeTypes: Set[String]
  ): StorageResult[Vector[SnapshotEdge]] = {
    val requested = edgeTypes.intersect(LiveGraphSnapshot.servedEdgeTypes)
    if (requested.isEmpty) return StorageResult.Found(Vector.empty)
    val rows = Vector.newBuilder[DirectedGraphEdge]
    var count = 0
    var cursor: Option[String] = None
    var more = true
    var pages = 0
    while (more) {
      val read = reader.directedEdges(
        id,
        window,
        EdgeDirection.Both,
        requested,
        pageSize,
        cursor
      )
      StorageResult.value(read) match {
        case None => return failure(read)
        case Some(page) =>
          rows ++= page.items
          count += page.items.size
          pages += 1
          cursor = page.cursor
          // One row past the scan limit is enough for the graph API to report its scan cap.
          more = cursor.nonEmpty && count <= scanLimit && pages <= scanLimit / pageSize + 2
      }
    }
    val converted = rows.result().map(convert)
    converted.collectFirst { case Left(code) => code } match {
      case Some(code) => StorageResult.Rejected(code)
      case None       => StorageResult.Found(converted.collect { case Right(e) => e })
    }
  }
}
object LiveGraphSnapshot {

  /** Declares that no immutable snapshot identity is asserted for the live graph. */
  val unpinnedId = "neptune-live-unpinned"
  val coreEdgesUnavailable = "core-edge-projection-unavailable"

  /** The edge types the graph API serves, all inside the reader's allowed set. */
  val servedEdgeTypes: Set[String] =
    Set("COAUTHORED_WITH", "AUTHORED", "HAS_TOPIC", "AFFILIATED_WITH", "PUBLISHED_IN")
}

/** The semantic endpoint role is not served by this process. */
object UnservedSemanticEndpoints extends SemanticEndpoints {
  override def ready(context: RequestContext): Boolean = false
  def retrieve(body: String, context: RequestContext): Either[ApiError, ApiReply] =
    Left(ApiError.unavailable)
  def close(): Unit = ()
}

/** The graph endpoint role is not served by this process. */
object UnservedGraphEndpoints extends GraphEndpoints {
  override def ready(context: RequestContext): Boolean = false
  def node(id: String, context: RequestContext): Either[ApiError, ApiReply] =
    Left(ApiError.unavailable)
  def neighbors(
      id: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = Left(ApiError.unavailable)
  def metrics(id: String, window: String, context: RequestContext): Either[ApiError, ApiReply] =
    Left(ApiError.unavailable)
  def paths(params: Map[String, String], context: RequestContext): Either[ApiError, ApiReply] =
    Left(ApiError.unavailable)
  override def communityMembers(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = Left(ApiError.unavailable)
  override def crossCommunityEdges(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = Left(ApiError.unavailable)
  def close(): Unit = ()
}

/** Evidence and audit routes belong to query-api; other roles hold refusing ports. */
object UnservedEvidenceStore extends EvidenceBundleStore {
  def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle] =
    StorageResult.Rejected("role-does-not-serve-evidence")
  def get(evidenceId: String): StorageResult[EvidenceBundle] =
    StorageResult.Rejected("role-does-not-serve-evidence")
}
object UnservedAuditStore extends RuntimeAuditStore {
  def put(envelope: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope] =
    StorageResult.Rejected("role-does-not-serve-audit")
  def get(queryId: String): StorageResult[RuntimeAuditEnvelope] =
    StorageResult.Rejected("role-does-not-serve-audit")
}

/** Used until a published runtime artifact pointer is configured. Every read is refused; no
  * ranking, community or temporal value is ever supplied from anywhere else.
  */
object UnconfiguredRuntimeArtifacts extends RuntimeArtifactStore {
  val code = "runtime-artifact-pointer-not-configured"
  def rank(
      windowId: String,
      metric: RuntimeRankingMetric,
      filters: RuntimePopulationFilter,
      limit: Int
  ): StorageResult[RuntimeRankingPage] = StorageResult.Rejected(code)
  def communitySummary(communityId: String, windowId: String): StorageResult[CommunitySummary] =
    StorageResult.Rejected(code)
  def bridgeMetrics(researcherId: String, windowId: String): StorageResult[RuntimeBridgeRecord] =
    StorageResult.Rejected(code)
  def temporalChange(
      researcherId: String,
      fromWindowId: String,
      toWindowId: String
  ): StorageResult[RuntimeTemporalRecord] = StorageResult.Rejected(code)
  def edgeSupport(edgeId: String, windowId: String): StorageResult[RuntimeEdgeRecord] =
    StorageResult.Rejected(code)
  def researcherContext(
      researcherId: String,
      windowId: String,
      limit: Int
  ): StorageResult[RuntimeResearcherContext] = StorageResult.Rejected(code)
}

/** The retrieval agents read the graph through the storage port. query-api holds no graph
  * credentials, so this adapter answers each port call from the existing graph-service routes.
  * Community reads use the graph-service community routes; a service that holds no communities
  * answers 422, which is refused rather than approximated.
  */
final class RemoteGraphReader(graph: GraphEndpoints, context: RequestContext) extends GraphReader {
  private val remoteEdgeTypes =
    Set("COAUTHORED_WITH", "AUTHORED", "HAS_TOPIC", "AFFILIATED_WITH", "PUBLISHED_IN")
  private def failure[A](error: ApiError): StorageResult[A] =
    if (error.status == 404) StorageResult.Missing
    else StorageResult.Rejected("remote-graph-failed")
  private def decoded[A](body: => StorageResult[A]): StorageResult[A] =
    try body
    catch { case NonFatal(_) => StorageResult.Rejected("malformed-remote-graph-response") }
  def node(id: String): StorageResult[GraphNode] = decoded {
    graph.node(id, context) match {
      case Left(error) => failure(error)
      case Right(reply) =>
        CoreJson.parse[GraphNode](reply.body("node").render()) match {
          case Right(n) => StorageResult.Found(n)
          case Left(_)  => StorageResult.Rejected("malformed-remote-graph-node")
        }
    }
  }
  def neighbors(
      id: String,
      window: String,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[GraphPage] = decoded {
    if (!edgeTypes.subsetOf(remoteEdgeTypes)) StorageResult.Rejected("unsupported-remote-edge-type")
    else {
      val params =
        Map("direction" -> "both", "depth" -> "1", "limit" -> limit.toString, "window" -> window) ++
          Option.when(edgeTypes.nonEmpty)("edgeTypes" -> edgeTypes.toVector.sorted.mkString(",")) ++
          cursor.map("cursor" -> _)
      graph.neighbors(id, params, context) match {
        case Left(error) => failure(error)
        case Right(reply) =>
          val items = reply.body("items").arr.toVector.map { item =>
            GraphNeighbor(
              item("nodeId").str,
              item("edgeId").str,
              item("edgeType").str,
              Map("fromId" -> item("fromId").str, "toId" -> item("toId").str)
            )
          }
          StorageResult.Found(GraphPage(items, reply.body("cursor").strOpt))
      }
    }
  }
  def directCoauthors(id: String, window: String, limit: Int): StorageResult[GraphPage] =
    neighbors(id, window, Set("COAUTHORED_WITH"), limit, None)

  /** Shortest paths over the graph-service `paths` route. An empty result is returned only for a
    * search that ran to the requested depth and completed: the retrieval agent turns an empty
    * result into a verified "no path within N hops" claim. A search that found nothing but was cut
    * short is therefore a closed refusal, never an empty result or a status claim: `path-search-
    * truncated` when a scan or node cap was hit, `path-depth-clamped` when the service's path
    * ceiling is below the requested depth. The retrieval stage then fails and the answer abstains.
    */
  def shortestPaths(
      a: String,
      b: String,
      maxDepth: Int,
      window: String,
      limit: Int
  ): StorageResult[Vector[GraphPath]] = decoded {
    val params =
      Map("from" -> a, "to" -> b, "maxDepth" -> maxDepth.toString, "window" -> window)
    graph.paths(params, context) match {
      case Left(error) => failure(error)
      case Right(reply) =>
        val found = reply
          .body("paths")
          .arr
          .toVector
          .take(limit)
          .map(p =>
            GraphPath(p("nodeIds").arr.map(_.str).toVector, p("edgeIds").arr.map(_.str).toVector)
          )
        val applied = reply.body.obj.get("maxDepth").flatMap(_.numOpt).map(_.toInt)
        val truncated = reply.body.obj.get("truncated").flatMap(_.boolOpt).contains(true)
        if (found.nonEmpty) StorageResult.Found(found)
        else if (truncated) StorageResult.Rejected("path-search-truncated")
        else if (applied.exists(_ < maxDepth)) StorageResult.Rejected("path-depth-clamped")
        else StorageResult.Found(found)
    }
  }
  private def communityFailure[A](error: ApiError): StorageResult[A] =
    if (error.status == 422) StorageResult.Rejected("remote-graph-operation-unsupported")
    else failure(error)
  private def communityParams(window: String, limit: Int) =
    Map("window" -> window, "limit" -> limit.toString)
  def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]] = decoded {
    graph.communityMembers(communityId, communityParams(window, limit), context) match {
      case Left(error) => communityFailure(error)
      case Right(reply) =>
        StorageResult.Found(reply.body("members").arr.map(_.str).toVector)
    }
  }
  def crossCommunityEdges(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[GraphPage] = decoded {
    graph.crossCommunityEdges(communityId, communityParams(window, limit), context) match {
      case Left(error) => communityFailure(error)
      case Right(reply) =>
        val items = reply.body("items").arr.toVector.map { item =>
          GraphNeighbor(
            item("nodeId").str,
            item("edgeId").str,
            item("edgeType").str,
            item("properties").obj.map((k, v) => k -> v.str).toMap
          )
        }
        // The port has no way to resume a community page, so a truncated page is reported with a
        // marker cursor that only says "more rows exist".
        val more = reply.body.obj.get("truncated").flatMap(_.boolOpt).contains(true)
        StorageResult.Found(GraphPage(items, Option.when(more)("more-available")))
    }
  }
}

/** Vector queries are answered by the semantic-service, which embeds the question itself. The query
  * vector the retrieval agent holds is never sent; only the question, the cap and the filters
  * travel. Hits are the service's actual records.
  */
final class RemoteVectorStore(
    semantic: SemanticEndpoints,
    question: String,
    context: RequestContext
) extends VectorStore {
  private val readOnly = "read-only-runtime"
  def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String] =
    StorageResult.Rejected(readOnly)
  def putBatch(index: String, documents: Vector[VectorDocument]): StorageResult[VectorBatchResult] =
    StorageResult.Rejected(readOnly)
  def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
    StorageResult.Rejected("remote-vector-get-unsupported")
  def query(
      index: String,
      vector: Vector[Float],
      topK: Int,
      filter: Map[String, String]
  ): StorageResult[Vector[VectorHit]] =
    try
      semantic.retrieve(
        ujson
          .Obj(
            "question" -> question,
            "topK" -> topK,
            "filters" -> ujson.Obj.from(filter.map((k, v) => k -> ujson.Str(v)))
          )
          .render(),
        context
      ) match {
        case Left(_) => StorageResult.Rejected("remote-semantic-unavailable")
        case Right(reply) =>
          StorageResult.Found(
            reply
              .body("hits")
              .arr
              .toVector
              .map(h =>
                VectorHit(
                  h("key").str,
                  h("distance").num,
                  h("metadata").obj.toMap.map((k, v) => k -> v.str)
                )
              )
          )
      }
    catch { case NonFatal(_) => StorageResult.Rejected("malformed-remote-semantic-response") }
}

/** Carries the configured embedding model identity for the retrieval agent. The retrieval agent
  * compares stored vector metadata with this model's tag, and its port signature asks for a query
  * vector before it calls the vector port. In query-api that port is [[RemoteVectorStore]], which
  * discards the vector: the real embedding runs in semantic-service. The carried value is a
  * placeholder shape only and never reaches retrieval or the wire.
  */
final class RemoteQueryEmbeddingCarrier(val model: EmbeddingModel) extends EmbeddingClient {
  private val shape: Vector[Float] =
    Vector.fill(model.dimension)(1.0f / math.sqrt(model.dimension).toFloat)
  def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
    if (text.trim.isEmpty) EmbeddingFailure("empty-embedding-text", false, model, 0)
    else EmbeddingSuccess(shape, model, 1)
  }
}
