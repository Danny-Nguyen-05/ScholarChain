package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import scala.collection.mutable
import StorageResult.*

/** One stored edge of the local graph. `window` is the windowId of a COAUTHORED_WITH edge and the
  * empty string for every other type, whose rows carry no `windowId` property. Properties are the
  * text-rendered edge properties exactly as the Neptune loader would store them. They are built on
  * first use for coauthor edges so that the 228k coauthor rows do not each hold a property map.
  */
private[storage] final class LocalEdge(
    val edgeId: String,
    val from: String,
    val to: String,
    val edgeType: String,
    val window: String,
    build: () => Map[String, String]
) {
  lazy val properties: Map[String, String] = build()
}

/** An indexed, immutable, in-memory counterpart of `NeptuneGraphReader`. It answers the same
  * bounded reads with the same ordering and bounds: the window constrains COAUTHORED_WITH only,
  * stored endpoints are returned as written, order is edge ID within the outgoing then incoming
  * phase, shortest paths use only COAUTHORED_WITH edges of the requested window and return the
  * paths of the minimal length in node-ID order. Nothing is inferred; a node is parsed and checked
  * from its stored row on each read.
  *
  * @param nodes
  *   node ID to (node class wire name, stored node row as JSON)
  * @param memberships
  *   stored community membership rows by researcher, in manifest window order
  */
final class LocalGraphReader private[storage] (
    nodes: Map[String, (String, String)],
    edges: Vector[LocalEdge],
    memberships: Map[String, Vector[CommunityMembership]],
    config: GraphReaderConfig = GraphReaderConfig()
) extends DirectedGraphReader {
  private val byId: Ordering[LocalEdge] = Ordering.by(_.edgeId)
  private val outgoing: Map[String, Vector[LocalEdge]] =
    edges.groupBy(_.from).view.mapValues(_.sorted(byId)).toMap
  private val incoming: Map[String, Vector[LocalEdge]] =
    edges.groupBy(_.to).view.mapValues(_.sorted(byId)).toMap

  /** window -> node -> (neighbor, edge ID) sorted by neighbor then edge ID. */
  private val coauthorAdjacency: Map[String, Map[String, Vector[(String, String)]]] =
    edges
      .filter(_.edgeType == "COAUTHORED_WITH")
      .groupBy(_.window)
      .view
      .mapValues { es =>
        es.flatMap(e =>
          if (e.from == e.to) Vector(e.from -> (e.to, e.edgeId))
          else Vector(e.from -> (e.to, e.edgeId), e.to -> (e.from, e.edgeId))
        ).groupMap(_._1)(_._2)
          .view
          .mapValues(_.sorted)
          .toMap
      }
      .toMap
  private val membershipByWindow: Map[String, Map[String, String]] =
    memberships.toVector
      .flatMap((id, ms) => ms.map(m => (m.context.windowId.get, id, m.communityId)))
      .groupBy(_._1)
      .view
      .mapValues(_.map(t => t._2 -> t._3).toMap)
      .toMap
  private val membersByCommunity: Map[(String, String), Vector[String]] =
    membershipByWindow.toVector
      .flatMap((w, m) => m.toVector.map((id, c) => (w, c) -> id))
      .groupMap(_._1)(_._2)
      .view
      .mapValues(_.sorted)
      .toMap
  private val qualificationsJson: Map[String, String] = memberships.view
    .mapValues(ms => ujson.Arr.from(ms.map(m => ujson.read(CoreJson.compact(m)))).render())
    .toMap

  /** Stored node counts by node class wire name (for example RESEARCHER). */
  val nodeCountsByClass: Map[String, Long] =
    nodes.values.groupBy(_._1).view.mapValues(_.size.toLong).toMap

  /** Stored edge counts by edge type wire name. COAUTHORED_WITH counts every window. */
  val edgeCountsByType: Map[String, Long] =
    edges.groupBy(_.edgeType).view.mapValues(_.size.toLong).toMap

  /** Stored COAUTHORED_WITH edge counts per windowId. */
  val coauthorEdgeCountsByWindow: Map[String, Long] =
    edges
      .filter(_.edgeType == "COAUTHORED_WITH")
      .groupBy(_.window)
      .view
      .mapValues(_.size.toLong)
      .toMap

  private def validLimit(n: Int) = n > 0 && n <= config.maxLimit
  private def typesFor(requested: Set[String]) =
    if (requested.isEmpty) config.allowedEdgeTypes else requested
  private def visible(e: LocalEdge, types: Set[String], window: String) =
    types(e.edgeType) && (e.edgeType != "COAUTHORED_WITH" || e.window == window)
  private def directed(e: LocalEdge) =
    DirectedGraphEdge(e.from, e.to, e.edgeId, e.edgeType, e.properties)

  def node(id: String): StorageResult[GraphNode] = nodes.get(id) match {
    case None => Missing
    case Some((_, json)) =>
      CoreJson.parse[GraphNode](json) match {
        case Right(n) if DomainValidation.check(n).isRight => Found(n)
        case _                                             => Rejected("malformed-graph-node")
      }
  }

  def directedEdges(
      id: String,
      window: String,
      direction: EdgeDirection,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[DirectedEdgePage] =
    if (!validLimit(limit) || !edgeTypes.subsetOf(config.allowedEdgeTypes))
      Rejected("invalid-bound")
    else {
      val types = typesFor(edgeTypes)
      DirectedEdgePaging.page(direction, limit, cursor, config.maxCursorOffset) {
        (phase, offset, n) =>
          val source = phase match {
            case DirectedEdgePaging.Phase.Out => outgoing.getOrElse(id, Vector.empty)
            case DirectedEdgePaging.Phase.In  => incoming.getOrElse(id, Vector.empty)
            case DirectedEdgePaging.Phase.InWithoutSelfLoops =>
              incoming.getOrElse(id, Vector.empty).filter(_.from != id)
          }
          Found(
            source.iterator
              .filter(visible(_, types, window))
              .slice(offset, offset + n)
              .map(directed)
              .toVector
          )
      }
    }

  private def qualificationsOf(researcher: String): Map[String, String] =
    qualificationsJson.get(researcher).map("communityQualificationsJson" -> _).toMap

  private def adjacent(
      id: String,
      window: String,
      types: Set[String]
  ): Vector[GraphNeighbor] = {
    val out = outgoing.getOrElse(id, Vector.empty).map(e => (e, e.to))
    val in = incoming.getOrElse(id, Vector.empty).filter(_.from != id).map(e => (e, e.from))
    (out ++ in)
      .filter((e, _) => visible(e, types, window))
      .map((e, other) =>
        GraphNeighbor(other, e.edgeId, e.edgeType, e.properties ++ qualificationsOf(other))
      )
      .sortBy(n => (n.nodeId, n.edgeId))
  }

  def neighbors(
      id: String,
      window: String,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[GraphPage] = {
    val offset = cursor.map(_.toIntOption.filter(_ >= 0)).getOrElse(Some(0))
    if (
      !validLimit(limit) || offset.isEmpty || offset.get > config.maxCursorOffset ||
      !edgeTypes.subsetOf(config.allowedEdgeTypes)
    ) Rejected("invalid-bound")
    else {
      val all = adjacent(id, window, typesFor(edgeTypes))
      val page = all.slice(offset.get, offset.get + limit)
      Found(
        GraphPage(
          page,
          Option.when(all.size > offset.get + limit)((offset.get + limit).toString)
        )
      )
    }
  }

  def directCoauthors(id: String, window: String, limit: Int): StorageResult[GraphPage] =
    neighbors(id, window, Set("COAUTHORED_WITH"), limit, None)

  def shortestPaths(
      a: String,
      b: String,
      maxDepth: Int,
      window: String,
      limit: Int
  ): StorageResult[Vector[GraphPath]] =
    if (maxDepth < 1 || maxDepth > config.maxDepth || !validLimit(limit)) Rejected("invalid-bound")
    else if (a == b) Found(Vector.empty)
    else {
      val adj = coauthorAdjacency.getOrElse(window, Map.empty)
      val none = Vector.empty[(String, String)]
      val dist = mutable.HashMap(a -> 0)
      val levels = mutable.ArrayBuffer(Vector(a))
      var depth = 0
      while (!dist.contains(b) && depth < maxDepth && levels(depth).nonEmpty) {
        depth += 1
        val next = mutable.LinkedHashSet.empty[String]
        for (n <- levels(depth - 1); (m, _) <- adj.getOrElse(n, none) if !dist.contains(m)) {
          dist(m) = depth; next += m
        }
        levels += next.toVector
      }
      if (!dist.contains(b)) Found(Vector.empty)
      else {
        // Keep only nodes that lie on some shortest path, then walk them in node-ID order.
        val length = dist(b)
        val onPath = Array.fill(length + 1)(mutable.HashSet.empty[String])
        onPath(length) += b
        for (level <- length - 1 to 0 by -1)
          levels(level).foreach { n =>
            if (adj.getOrElse(n, none).exists((m, _) => onPath(level + 1)(m))) onPath(level) += n
          }
        val found = Vector.newBuilder[GraphPath]
        var count = 0
        def walk(node: String, level: Int, nodeIds: Vector[String], edgeIds: Vector[String]): Unit =
          if (count < limit)
            if (level == length) { found += GraphPath(nodeIds, edgeIds); count += 1 }
            else
              adj
                .getOrElse(node, none)
                .foreach((m, edge) =>
                  if (dist.get(m).contains(level + 1) && onPath(level + 1)(m))
                    walk(m, level + 1, nodeIds :+ m, edgeIds :+ edge)
                )
        walk(a, 0, Vector(a), Vector.empty)
        Found(found.result())
      }
    }

  def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]] =
    if (!validLimit(limit)) Rejected("invalid-bound")
    else Found(membersByCommunity.getOrElse((window, communityId), Vector.empty).take(limit))

  def crossCommunityEdges(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[GraphPage] =
    if (!validLimit(limit)) Rejected("invalid-bound")
    else {
      val members = membersByCommunity.getOrElse((window, communityId), Vector.empty)
      val inWindow = membershipByWindow.getOrElse(window, Map.empty)
      val rows = members.flatMap { a =>
        val incident = outgoing.getOrElse(a, Vector.empty).map(e => (e, e.to)) ++
          incoming.getOrElse(a, Vector.empty).filter(_.from != a).map(e => (e, e.from))
        incident.collect {
          case (e, b)
              if e.edgeType == "COAUTHORED_WITH" && e.window == window &&
                inWindow.get(b).exists(_ != communityId) =>
            GraphNeighbor(b, e.edgeId, e.edgeType, e.properties ++ qualificationsOf(a))
        }
      }
      Found(GraphPage(rows.sortBy(_.edgeId).take(limit), None))
    }
}
