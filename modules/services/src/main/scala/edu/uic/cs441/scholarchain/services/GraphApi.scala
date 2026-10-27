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
trait GraphSnapshot {
  def snapshotId: String
  def node(id: String): StorageResult[GraphNode]
  def edges(id: String, window: String): StorageResult[Vector[GraphEdge]]
  def metrics(id: String, window: String): StorageResult[ResearcherMetricRecord]
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
    cursorKey: String = java.util.UUID.randomUUID().toString
) {
  require(
    Set("in", "out", "both")(
      defaultDirection
    ) && defaultDepth > 0 && defaultDepth <= maxDepth && maxDepth <= 3
  )
  require(defaultLimit > 0 && defaultLimit <= maxLimit && maxLimit <= 200 && timeoutMs > 0)
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
              else if (error.isEmpty) PortResult.read(snapshot.edges(current, window)) match {
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
                    edges.sortBy(_.edgeId).filter(e => types(e.edgeType.wire)).foreach { edge =>
                      val follow =
                        if (direction == "out" && edge.fromId == current) Some(edge.toId)
                        else if (direction == "in" && edge.toId == current) Some(edge.fromId)
                        else if (direction == "both")
                          Some(if (edge.fromId == current) edge.toId else edge.fromId)
                        else None
                      follow.foreach { target =>
                        if (!seenEdges(edge.edgeId)) {
                          items :+= ujson.Obj(
                            "nodeId" -> target,
                            "edgeId" -> edge.edgeId,
                            "edgeType" -> edge.edgeType.wire,
                            "depth" -> level,
                            "fromId" -> edge.fromId,
                            "toId" -> edge.toId,
                            "provenance" -> upickle.default.writeJs(edge.provenance)
                          )
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
  def paths(params: Map[String, String], context: RequestContext): Either[ApiError, ApiReply] = {
    val started = System.nanoTime()
    val timeout = operationTimeout(params, Set("from", "to", "maxDepth", "window")) match {
      case Left(error)  => return Left(error)
      case Right(value) => value
    }
    val to = params.getOrElse("to", "")
    if (to.isEmpty)
      Left(ApiError.invalid)
    else {
      val from = params.getOrElse("from", "")
      val p = Map(
        "depth" -> params.getOrElse("maxDepth", config.maxDepth.toString),
        "limit" -> config.maxLimit.toString,
        "window" -> params.getOrElse("window", config.defaultWindow),
        "timeoutMs" -> timeout.toString
      )
      neighbors(from, p, context).flatMap { reply =>
        val items = reply.body("items").arr.toVector
        val maxDepth = p("depth").toInt
        var frontier = Vector((Vector(from), Vector.empty[String]));
        var found: Option[(Vector[String], Vector[String])] = None
        var level = 0
        var visited = Set(from)
        while (frontier.nonEmpty && found.isEmpty && level <= maxDepth) {
          if (System.nanoTime() - started >= timeout * 1000000L) return Left(ApiError.graphDeadline)
          found = frontier.find(_._1.last == to)
          if (found.isEmpty && level < maxDepth) frontier = frontier.flatMap { (ns, es) =>
            items.filter(x => x("fromId").str == ns.last || x("toId").str == ns.last).flatMap {
              item =>
                val n = if (item("fromId").str == ns.last) item("toId").str else item("fromId").str
                if (visited(n)) None
                else { visited += n; Some((ns :+ n, es :+ item("edgeId").str)) }
            }
          }
          else frontier = Vector.empty
          level += 1
        }
        val nodes = found.map(_._1).getOrElse(Vector.empty)
        val edgeIds = found.map(_._2).getOrElse(Vector.empty)
        if (reply.body("cursor") != ujson.Null)
          return Left(
            ApiError(422, "PATH_EXPANSION_TRUNCATED", "The bounded path expansion is incomplete.")
          )
        Right(
          ApiReply(
            200,
            ujson.Obj(
              "snapshot" -> snapshot.snapshotId,
              "paths" -> (if (found.nonEmpty)
                            ujson.Arr(
                              ujson.Obj(
                                "nodeIds" -> ujson.Arr.from(nodes),
                                "edgeIds" -> ujson.Arr.from(edgeIds)
                              )
                            )
                          else ujson.Arr())
            )
          )
        )
      }
    }
  }
  def close(): Unit = boundaryClient.close()
}
