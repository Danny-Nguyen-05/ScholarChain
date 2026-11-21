package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.charset.StandardCharsets.UTF_8
import java.util.Base64
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import scala.util.boundary
import scala.util.control.NonFatal

/** Directed immutable snapshot supplied by composition. The older GraphReader neighbor port has
  * neither direction nor snapshot identity and cannot satisfy this stronger public contract.
  */
/** One stored edge as the graph API reports it. `undirected` marks a type whose stored endpoint
  * order is only canonical, so every direction filter treats it as incident. `evidence` carries
  * stored evidence pointers for edges whose row has no provenance record; it is never inferred.
  */
final case class SnapshotEdge(
    edgeId: String,
    edgeType: String,
    fromId: String,
    toId: String,
    undirected: Boolean,
    provenance: ujson.Value,
    evidence: Option[ujson.Value] = None
)
trait GraphSnapshot {
  def snapshotId: String
  def node(id: String): StorageResult[GraphNode]
  def edges(id: String, window: String): StorageResult[Vector[GraphEdge]]

  /** Edges incident to a node. The default projects the fully typed core edges unchanged. */
  def incidentEdges(id: String, window: String): StorageResult[Vector[SnapshotEdge]] =
    edges(id, window) match {
      case StorageResult.Missing => StorageResult.Missing
      case result =>
        StorageResult.value(result) match {
          case Some(found) =>
            StorageResult.Found(
              found.map(e =>
                SnapshotEdge(
                  e.edgeId,
                  e.edgeType.wire,
                  e.fromId,
                  e.toId,
                  false,
                  upickle.default.writeJs(e.provenance)
                )
              )
            )
          case None => StorageResult.Rejected("edge-read-failed")
        }
    }

  /** Edges incident to a node, restricted to the given stored edge types. The default filters the
    * unrestricted read; an adapter may push the filter to its store to scan less.
    */
  def incidentEdges(
      id: String,
      window: String,
      edgeTypes: Set[String]
  ): StorageResult[Vector[SnapshotEdge]] = incidentEdges(id, window) match {
    case StorageResult.Found(found) => StorageResult.Found(found.filter(e => edgeTypes(e.edgeType)))
    case other                      => other
  }
  def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord]

  /** Stored members of one community in a window. A snapshot that holds no community membership
    * refuses with [[GraphSnapshot.communityUnsupported]]; nothing is inferred.
    */
  def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]] = StorageResult.Rejected(GraphSnapshot.communityUnsupported)

  /** Stored coauthor edges leaving one community in a window (one row per edge, the far endpoint as
    * `nodeId`). Same refusal as [[communityMembers]] when the snapshot holds no communities.
    */
  def crossCommunityEdges(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[GraphPage] = StorageResult.Rejected(GraphSnapshot.communityUnsupported)
}
object GraphSnapshot {
  val communityUnsupported = "community-read-unsupported"
}
final class InMemoryGraphSnapshot(
    val snapshotId: String,
    nodes: Vector[GraphNode],
    edges: Vector[GraphEdge],
    metricStore: ResearcherMetricStore = new InMemoryResearcherMetricStore
) extends GraphSnapshot {
  require(snapshotId.nonEmpty && nodes.map(_.nodeId).distinct.size == nodes.size)
  def node(id: String): StorageResult[GraphNode] =
    nodes.find(_.nodeId == id).map(StorageResult.Found(_)).getOrElse(StorageResult.Missing)
  def edges(id: String, window: String): StorageResult[Vector[GraphEdge]] =
    StorageResult.Found(
      edges
        .filter(e => e.fromId == id || e.toId == id)
        .filter(e => e.properties.find(_.name == "windowId").forall(_.value == window))
    )
  def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord] =
    metricStore.get(id, window)
}
final case class GraphApiConfig(
    defaultDirection: String = "both",
    defaultDepth: Int = 1,
    maxDepth: Int = 3,
    defaultLimit: Int = 50,
    maxLimit: Int = 200,
    timeoutMs: Long = 5000,
    defaultWindow: String = "all-years",
    maxScannedEdges: Int = 10000,
    maxVisitedNodes: Int = 2000,
    maxCursorChars: Int = 4096,
    cursorKey: String = java.util.UUID.randomUUID().toString,
    maxPathDepth: Int = 6
) {
  require(
    Set("in", "out", "both")(
      defaultDirection
    ) && defaultDepth > 0 && defaultDepth <= maxDepth && maxDepth <= 3
  )
  require(defaultLimit > 0 && defaultLimit <= maxLimit && maxLimit <= 200 && timeoutMs > 0)
  // Shortest-path search is a level-by-level search bounded by the scan and node caps, so its hop
  // ceiling is separate from (and at least) the neighbour-expansion depth ceiling above.
  require(maxPathDepth >= maxDepth && maxPathDepth <= 16)
  require(
    defaultWindow.nonEmpty && maxScannedEdges > 0 && maxVisitedNodes > 0 && maxCursorChars > 0 && cursorKey.nonEmpty
  )
}
final class GraphApi(snapshot: GraphSnapshot, val config: GraphApiConfig = GraphApiConfig())
    extends GraphEndpoints {
  private val edgeTypes =
    Set("COAUTHORED_WITH", "AUTHORED", "HAS_TOPIC", "AFFILIATED_WITH", "PUBLISHED_IN")
  private val boundaryConfig = ServiceConfig(
    Auth.sha256("graph-boundary-placeholder"),
    Auth.sha256("graph-boundary-internal-placeholder"),
    downstreamTimeoutMs = config.timeoutMs,
    downstreamMaxAttempts = 1
  )
  private val boundaryClient =
    new DownstreamClient(boundaryConfig, new CircuitBreaker(Int.MaxValue, config.timeoutMs))
  private def timed[A](context: RequestContext, timeout: Long)(
      body: => Either[ApiError, A]
  ): Either[ApiError, A] = {
    // One call wraps the complete expansion so slow node/edge adapters cannot extend the aggregate deadline.
    boundaryClient.callWithin("GET", context, timeout)(_ => body).left.map { error =>
      // This boundary encloses local graph work only. An expiry here is the request's graph
      // execution budget, not the remote HTTP client's transport timeout.
      if (error == ApiError.timeout) ApiError.graphDeadline else error
    }
  }
  private def operationTimeout(
      params: Map[String, String],
      allowed: Set[String]
  ): Either[ApiError, Long] = try {
    if (!params.keySet.subsetOf(allowed + "timeoutMs")) Left(ApiError.invalid)
    else {
      val timeout = params.get("timeoutMs").map(_.toLong).getOrElse(config.timeoutMs)
      if (timeout <= 0 || timeout > config.timeoutMs) Left(ApiError.invalid) else Right(timeout)
    }
  } catch { case NonFatal(_) => Left(ApiError.invalid) }
  private def signature(value: String): String = {
    val mac = Mac.getInstance("HmacSHA256")
    mac.init(new SecretKeySpec(config.cursorKey.getBytes(UTF_8), "HmacSHA256"))
    Base64.getUrlEncoder.withoutPadding().encodeToString(mac.doFinal(value.getBytes(UTF_8)))
  }
  private def encode(offset: Int, binding: String): String = {
    val p = ujson.Obj("offset" -> offset, "binding" -> binding).render()
    Base64.getUrlEncoder.withoutPadding().encodeToString(p.getBytes(UTF_8)) + "." + signature(p)
  }
  private def decode(cursor: String, binding: String): Either[ApiError, Int] = try {
    if (cursor.length > config.maxCursorChars) return Left(ApiError.invalid)
    val parts = cursor.split("\\.", -1)
    if (parts.length != 2) return Left(ApiError.invalid)
    val p = new String(Base64.getUrlDecoder.decode(parts(0)), UTF_8)
    if (
      !java.security.MessageDigest.isEqual(signature(p).getBytes(UTF_8), parts(1).getBytes(UTF_8))
    ) return Left(ApiError.invalid)
    val value = ujson.read(p)
    if (value("binding").str != binding || !value("offset").num.isWhole || value("offset").num < 0)
      Left(ApiError.invalid)
    else Right(value("offset").num.toInt)
  } catch { case NonFatal(_) => Left(ApiError.invalid) }
  def node(id: String, context: RequestContext): Either[ApiError, ApiReply] =
    node(id, Map.empty, context)
  override def node(
      id: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    operationTimeout(params, Set.empty).flatMap { timeout =>
      timed(context, timeout) {
        PortResult
          .read(snapshot.node(id))
          .map(n =>
            ApiReply(
              200,
              ujson.Obj(
                "nodeId" -> n.nodeId,
                "snapshot" -> snapshot.snapshotId,
                "node" -> upickle.default.writeJs(n)
              )
            )
          )
      }
    }
  def neighbors(
      id: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = boundary {
    try {
      if (
        !params.keySet.subsetOf(
          Set("direction", "depth", "limit", "edgeTypes", "window", "timeoutMs", "cursor")
        )
      ) boundary.break(Left(ApiError.invalid))
      val direction = params.getOrElse("direction", config.defaultDirection)
      val depth = params.get("depth").map(_.toInt).getOrElse(config.defaultDepth)
      val limit = params.get("limit").map(_.toInt).getOrElse(config.defaultLimit)
      val timeout = params.get("timeoutMs").map(_.toLong).getOrElse(config.timeoutMs)
      val window = params.getOrElse("window", config.defaultWindow)
      val types = params.get("edgeTypes").map(_.split(",", -1).toSet).getOrElse(edgeTypes)
      if (
        !Set("in", "out", "both")(
          direction
        ) || depth < 1 || depth > config.maxDepth || limit < 1 || limit > config.maxLimit || timeout < 1 || timeout > config.timeoutMs || window.isEmpty || !types
          .subsetOf(edgeTypes) || types.isEmpty
      ) boundary.break(Left(ApiError.invalid))
      val binding = Auth.sha256(
        ujson
          .Arr(
            id,
            snapshot.snapshotId,
            direction,
            depth,
            limit,
            window,
            ujson.Arr.from(types.toVector.sorted),
            timeout
          )
          .render()
      )
      val offset = params
        .get("cursor")
        .map(decode(_, binding))
        .getOrElse(Right(0))
        .fold(e => boundary.break(Left(e)), identity)
      timed(context, timeout) {
        PortResult.read(snapshot.node(id)).flatMap { _ =>
          val expires = System.nanoTime() + timeout * 1000000L
          var frontier = Vector(id); var visited = Set(id); var scanned = 0; var level = 0
          var items = Vector.empty[ujson.Value]; var seenEdges = Set.empty[String]
          var error: Option[ApiError] = None
          while (frontier.nonEmpty && level < depth && error.isEmpty) {
            level += 1; var next = Vector.empty[String]
            frontier.sorted.foreach { current =>
              if (System.nanoTime() >= expires) error = Some(ApiError.timeout)
              else if (error.isEmpty)
                PortResult.read(snapshot.incidentEdges(current, window)) match {
                  case Left(e) => error = Some(e)
                  case Right(edges) =>
                    scanned += edges.size
                    if (scanned > config.maxScannedEdges)
                      error = Some(
                        ApiError(
                          422,
                          "GRAPH_SCAN_CAP",
                          "Graph exploration exceeds the configured scan cap."
                        )
                      )
                    else
                      edges.sortBy(_.edgeId).filter(e => types(e.edgeType)).foreach { edge =>
                        val touches = edge.fromId == current || edge.toId == current
                        val follow =
                          if (edge.undirected && touches)
                            Some(if (edge.fromId == current) edge.toId else edge.fromId)
                          else if (direction == "out" && edge.fromId == current) Some(edge.toId)
                          else if (direction == "in" && edge.toId == current) Some(edge.fromId)
                          else if (direction == "both")
                            Some(if (edge.fromId == current) edge.toId else edge.fromId)
                          else None
                        follow.foreach { target =>
                          if (!seenEdges(edge.edgeId)) {
                            val item = ujson.Obj(
                              "nodeId" -> target,
                              "edgeId" -> edge.edgeId,
                              "edgeType" -> edge.edgeType,
                              "depth" -> level,
                              "fromId" -> edge.fromId,
                              "toId" -> edge.toId,
                              "provenance" -> edge.provenance
                            )
                            edge.evidence.foreach(e => item("evidence") = e)
                            items :+= item
                            seenEdges += edge.edgeId
                          }
                          if (!visited(target)) { visited += target; next :+= target }
                        }
                      }
                }
              if (visited.size > config.maxVisitedNodes)
                error = Some(
                  ApiError(
                    422,
                    "GRAPH_NODE_CAP",
                    "Graph exploration exceeds the configured node cap."
                  )
                )
            }
            frontier = next.distinct
          }
          if (System.nanoTime() >= expires) error = Some(ApiError.timeout)
          error.map(Left(_)).getOrElse {
            if (offset > items.size) Left(ApiError.invalid)
            else
              Right(
                ApiReply(
                  200,
                  ujson.Obj(
                    "nodeId" -> id,
                    "snapshot" -> snapshot.snapshotId,
                    "direction" -> direction,
                    "depth" -> depth,
                    "items" -> ujson.Arr.from(items.slice(offset, offset + limit)),
                    "cursor" -> (if (offset + limit < items.size)
                                   ujson.Str(encode(offset + limit, binding))
                                 else ujson.Null)
                  )
                )
              )
          }
        }
      }
    } catch { case b: boundary.Break[?] => throw b; case NonFatal(_) => Left(ApiError.invalid) }
  }
  def metrics(id: String, window: String, context: RequestContext): Either[ApiError, ApiReply] =
    metrics(id, window, Map.empty, context)
  override def metrics(
      id: String,
      window: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    operationTimeout(params, Set("window")).flatMap { timeout =>
      timed(context, timeout) {
        PortResult
          .read(snapshot.metrics(id, window))
          .map(m =>
            ApiReply(
              200,
              ujson.Obj(
                "researcherId" -> id,
                "window" -> window,
                "record" -> ujson.read(m.payloadJson),
                "qualifications" -> ujson.read(m.qualificationsJson),
                "metricVersion" -> m.metricVersion,
                "runId" -> m.runId
              )
            )
          )
      }
    }

  /** Shortest coauthor path by level-by-level BFS that stops at the first level containing `to`.
    * Only `COAUTHORED_WITH` edges are walked, in either stored direction, as the storage
    * `GraphReader.shortestPaths` contract and the runtime path verifier require. Frontier nodes and
    * their edges are visited in sorted order, so the single returned path is deterministic.
    *
    * A requested `maxDepth` above `config.maxPathDepth` is clamped to it (never rejected); the
    * reply states the applied depth and whether it was clamped. When the scan or node cap is hit
    * before `to` is reached the reply is a 200 with no path and `truncated: true`, so an empty
    * result is never presented as proof that no path exists. Deadline and snapshot failures stay
    * typed errors.
    */
  def paths(params: Map[String, String], context: RequestContext): Either[ApiError, ApiReply] =
    boundary {
      try {
        val timeout = operationTimeout(params, Set("from", "to", "maxDepth", "window")) match {
          case Left(error)  => boundary.break(Left(error))
          case Right(value) => value
        }
        val to = params.getOrElse("to", "")
        val from = params.getOrElse("from", "")
        val window = params.getOrElse("window", config.defaultWindow)
        val requested = params.get("maxDepth").map(_.toInt).getOrElse(config.maxPathDepth)
        if (to.isEmpty || window.isEmpty || requested < 1) boundary.break(Left(ApiError.invalid))
        val applied = math.min(requested, config.maxPathDepth)
        timed(context, timeout) {
          PortResult
            .read(snapshot.node(from))
            .flatMap { _ =>
              // A missing target is a 404 up front rather than a search that runs to the caps.
              PortResult.read(snapshot.node(to))
            }
            .flatMap { _ =>
              val expires = System.nanoTime() + timeout * 1000000L
              val coauthor = "COAUTHORED_WITH"
              val parent = scala.collection.mutable.HashMap.empty[String, (String, String)]
              val visited = scala.collection.mutable.HashSet(from)
              var frontier = Vector(from)
              var level = 0
              var scanned = 0
              var found = from == to
              var truncation = Option.empty[String]
              var error = Option.empty[ApiError]
              while (
                !found && frontier.nonEmpty && level < applied && error.isEmpty && truncation.isEmpty
              ) {
                level += 1
                val next = Vector.newBuilder[String]
                frontier.sorted.foreach { current =>
                  if (!found && error.isEmpty && truncation.isEmpty) {
                    if (System.nanoTime() >= expires) error = Some(ApiError.timeout)
                    else
                      PortResult.read(
                        snapshot.incidentEdges(current, window, Set(coauthor))
                      ) match {
                        case Left(e) => error = Some(e)
                        case Right(edges) =>
                          scanned += edges.size
                          if (scanned > config.maxScannedEdges) truncation = Some("scan-cap")
                          else
                            edges.sortBy(_.edgeId).filter(_.edgeType == coauthor).foreach { edge =>
                              val target = if (edge.fromId == current) edge.toId else edge.fromId
                              if (!found && visited.add(target)) {
                                parent(target) = (current, edge.edgeId)
                                next += target
                                if (target == to) found = true
                              }
                            }
                          if (!found && visited.size > config.maxVisitedNodes)
                            truncation = Some("node-cap")
                      }
                  }
                }
                frontier = next.result()
              }
              if (System.nanoTime() >= expires) error = Some(ApiError.timeout)
              error.map(Left(_)).getOrElse {
                val route =
                  if (!found) Vector.empty[(String, Option[String])]
                  else {
                    var current = to
                    var walked = Vector((to, Option.empty[String]))
                    while (current != from) {
                      val (before, edgeId) = parent(current)
                      walked = (before, Some(edgeId)) +: walked
                      current = before
                    }
                    walked
                  }
                // Each entry holds a node and the edge that leaves it toward `to` (none for the last).
                val nodeIds = route.map(_._1)
                val edgeIds = route.flatMap(_._2)
                Right(
                  ApiReply(
                    200,
                    ujson.Obj(
                      "snapshot" -> snapshot.snapshotId,
                      "paths" -> (if (found)
                                    ujson.Arr(
                                      ujson.Obj(
                                        "nodeIds" -> ujson.Arr.from(nodeIds),
                                        "edgeIds" -> ujson.Arr.from(edgeIds)
                                      )
                                    )
                                  else ujson.Arr()),
                      "maxDepth" -> applied,
                      "clamped" -> (requested > applied),
                      "truncated" -> truncation.nonEmpty,
                      "truncationReason" -> truncation.map(ujson.Str(_)).getOrElse(ujson.Null)
                    )
                  )
                )
              }
            }
        }
      } catch { case b: boundary.Break[?] => throw b; case NonFatal(_) => Left(ApiError.invalid) }
    }

  private def communityParams(
      params: Map[String, String]
  ): Either[ApiError, (String, Int, Long)] = try {
    val window = params.getOrElse("window", config.defaultWindow)
    val limit = params.get("limit").map(_.toInt).getOrElse(config.defaultLimit)
    operationTimeout(params, Set("window", "limit")).flatMap { timeout =>
      if (window.isEmpty || limit < 1 || limit > config.maxLimit) Left(ApiError.invalid)
      else Right((window, limit, timeout))
    }
  } catch { case NonFatal(_) => Left(ApiError.invalid) }
  private def communityRead[A](result: StorageResult[A]): Either[ApiError, A] = result match {
    case StorageResult.Rejected(GraphSnapshot.communityUnsupported) =>
      Left(
        ApiError(
          422,
          "COMMUNITY_UNSUPPORTED",
          "This graph snapshot holds no stored community membership."
        )
      )
    case other => PortResult.read(other)
  }

  /** Stored members of a community, at most `limit` (default and maximum as for neighbours). */
  override def communityMembers(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    if (communityId.isEmpty) Left(ApiError.invalid)
    else
      communityParams(params).flatMap { (window, limit, timeout) =>
        timed(context, timeout) {
          communityRead(snapshot.communityMembers(communityId, window, limit)).flatMap { members =>
            if (members.size > limit) Left(ApiError.downstream)
            else
              Right(
                ApiReply(
                  200,
                  ujson.Obj(
                    "snapshot" -> snapshot.snapshotId,
                    "communityId" -> communityId,
                    "window" -> window,
                    "members" -> ujson.Arr.from(members)
                  )
                )
              )
          }
        }
      }

  /** Stored coauthor edges that leave a community, at most `limit`. `truncated` is true when the
    * store reports more rows than were returned.
    */
  override def crossCommunityEdges(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    if (communityId.isEmpty) Left(ApiError.invalid)
    else
      communityParams(params).flatMap { (window, limit, timeout) =>
        timed(context, timeout) {
          communityRead(snapshot.crossCommunityEdges(communityId, window, limit)).flatMap { page =>
            if (page.items.size > limit) Left(ApiError.downstream)
            else
              Right(
                ApiReply(
                  200,
                  ujson.Obj(
                    "snapshot" -> snapshot.snapshotId,
                    "communityId" -> communityId,
                    "window" -> window,
                    "items" -> ujson.Arr.from(page.items.map { n =>
                      ujson.Obj(
                        "nodeId" -> n.nodeId,
                        "edgeId" -> n.edgeId,
                        "edgeType" -> n.edgeType,
                        "properties" -> ujson.Obj.from(
                          n.properties.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v))
                        )
                      )
                    }),
                    "truncated" -> page.cursor.nonEmpty
                  )
                )
              )
          }
        }
      }
  def close(): Unit = boundaryClient.close()
}
