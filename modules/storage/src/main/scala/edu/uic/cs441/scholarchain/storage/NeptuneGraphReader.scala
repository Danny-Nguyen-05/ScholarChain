package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.ExecuteOpenCypherQueryRequest
import software.amazon.awssdk.awscore.AwsRequestOverrideConfiguration
import software.amazon.awssdk.auth.credentials.AwsCredentialsProvider
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.awscore.retry.AwsRetryStrategy
import software.amazon.awssdk.regions.Region
import java.net.URI
import java.time.Duration
import java.util.concurrent.atomic.AtomicBoolean
import StorageResult.*

object CommunityLookup {
  def membership(window: String, community: String): String =
    "|" + StableIds.sha256Hex(StorageKeys.composite(window, community)) + "|"
  def window(window: String): String = "|" + StableIds.sha256Hex(window) + "|"
}

/** Runtime-facing constructor accepts no loader, mutation callback or arbitrary query text. The
  * `connect` factory builds and owns a read-only SDK client; `close` releases it. A reader built
  * from an injected client never closes that client.
  */
final class NeptuneGraphReader private (
    client: NeptunedataClient,
    config: GraphReaderConfig,
    ownsClient: Boolean
) extends DirectedGraphReader
    with AutoCloseable {
  def this(client: NeptunedataClient, config: GraphReaderConfig) = this(client, config, false)
  private val closed = new AtomicBoolean(false)
  def close(): Unit = if (ownsClient && closed.compareAndSet(false, true)) client.close()
  private val retry = new StorageRetry(config.retry)
  private val neighborQuery =
    "MATCH (a)-[r]-(b) WHERE id(a) = $id AND type(r) IN $types AND (type(r) <> 'COAUTHORED_WITH' OR r.windowId = $window) RETURN id(b) AS nodeId, id(r) AS edgeId, type(r) AS edgeType, properties(r) AS properties, b.communityQualificationsJson AS communityQualificationsJson ORDER BY nodeId, edgeId SKIP $offset LIMIT $limit"
  private val outQuery =
    "MATCH (a)-[r]->(b) WHERE id(a) = $id AND type(r) IN $types AND (type(r) <> 'COAUTHORED_WITH' OR r.windowId = $window) RETURN id(a) AS fromId, id(b) AS toId, id(r) AS edgeId, type(r) AS edgeType, properties(r) AS properties ORDER BY edgeId SKIP $offset LIMIT $limit"
  private val inQuery =
    "MATCH (b)-[r]->(a) WHERE id(a) = $id AND type(r) IN $types AND (type(r) <> 'COAUTHORED_WITH' OR r.windowId = $window) RETURN id(b) AS fromId, id(a) AS toId, id(r) AS edgeId, type(r) AS edgeType, properties(r) AS properties ORDER BY edgeId SKIP $offset LIMIT $limit"
  private val inWithoutSelfLoopsQuery =
    "MATCH (b)-[r]->(a) WHERE id(a) = $id AND id(b) <> id(a) AND type(r) IN $types AND (type(r) <> 'COAUTHORED_WITH' OR r.windowId = $window) RETURN id(b) AS fromId, id(a) AS toId, id(r) AS edgeId, type(r) AS edgeType, properties(r) AS properties ORDER BY edgeId SKIP $offset LIMIT $limit"
  private def execute(query: String, params: ujson.Obj): StorageResult[Vector[AwsJson]] =
    retry {
      try {
        val request = ExecuteOpenCypherQueryRequest
          .builder()
          .openCypherQuery(
            s"USING QUERY:TIMEOUTMILLISECONDS ${config.requestTimeoutMillis} " + query
          )
          .parameters(params.render())
          .overrideConfiguration(
            AwsRequestOverrideConfiguration
              .builder()
              .apiCallTimeout(Duration.ofMillis(config.requestTimeoutMillis + 1000))
              .build()
          )
          .build()
        val response = client.executeOpenCypherQuery(request)
        val json = AwsDocumentJson.value(response.results())
        val requested = params.obj.get("limit").map(_.num.toInt).getOrElse(1)
        if (json.arr.size > math.min(config.maxLimit + 1, requested))
          Rejected("graph-response-limit")
        else Found(json.arr.toVector)
      } catch {
        case _: ujson.Value.InvalidData | _: ujson.ParseException | _: IllegalArgumentException =>
          Rejected("malformed-graph-response")
      }
    }
  private def validLimit(n: Int) = n > 0 && n <= config.maxLimit
  private def textProperties(json: AwsJson): Map[String, String] = json.obj.iterator
    .map((k, v) => k -> (v match { case AwsJson.StringValue(s) => s; case v => v.render }))
    .toMap
  private def decodeNeighbor(r: AwsJson): GraphNeighbor = {
    val props =
      r.obj
        .get("properties")
        .filter(_ != AwsJson.NullValue)
        .map(textProperties)
        .getOrElse(Map.empty)
    val qualifications = r.obj
      .get("communityQualificationsJson")
      .filter(_ != AwsJson.NullValue)
      .map(v => "communityQualificationsJson" -> v.str)
    GraphNeighbor(r("nodeId").str, r("edgeId").str, r("edgeType").str, props ++ qualifications)
  }
  private def decoded[A](body: => StorageResult[A]): StorageResult[A] = try body
  catch { case _: Exception => Rejected("malformed-graph-response") }
  def node(id: String): StorageResult[GraphNode] = decoded {
    RowCodec.map(
      execute(
        "MATCH (n) WHERE id(n) = $id RETURN id(n) AS nodeId, labels(n) AS labels, properties(n) AS properties LIMIT 1",
        ujson.Obj("id" -> id)
      )
    ) { rows =>
      rows.headOption match {
        case None => Missing
        case Some(r) =>
          val p = r("properties")
          val json = ujson.Obj(
            "nodeId" -> r("nodeId").str,
            "schemaVersion" -> p("schemaVersion").str,
            "nodeClass" -> r("labels")(0).str,
            "label" -> p("label").str,
            "properties" -> ujson.read(p("propertiesJson").str),
            "provenance" -> ujson.read(p("provenanceJson").str)
          )
          CoreJson.parse[GraphNode](json.render()) match {
            case Right(n) if DomainValidation.check(n).isRight => Found(n);
            case _                                             => Rejected("malformed-graph-node")
          }
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
    val offset = cursor.map(_.toIntOption.filter(_ >= 0)).getOrElse(Some(0))
    if (
      !validLimit(limit) || offset.isEmpty || offset.get > config.maxCursorOffset || !edgeTypes
        .subsetOf(config.allowedEdgeTypes)
    ) Rejected("invalid-bound")
    else {
      val types = if (edgeTypes.isEmpty) config.allowedEdgeTypes else edgeTypes
      RowCodec.map(
        execute(
          neighborQuery,
          ujson.Obj(
            "id" -> id,
            "window" -> window,
            "types" -> ujson.Arr.from(types.toVector.sorted),
            "offset" -> offset.get,
            "limit" -> (limit + 1)
          )
        )
      ) { rows =>
        val page = rows.take(limit).map(decodeNeighbor)
        Found(GraphPage(page, if (rows.size > limit) Some((offset.get + limit).toString) else None))
      }
    }
  }
  def directedEdges(
      id: String,
      window: String,
      direction: EdgeDirection,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[DirectedEdgePage] = decoded {
    if (!validLimit(limit) || !edgeTypes.subsetOf(config.allowedEdgeTypes))
      Rejected("invalid-bound")
    else {
      val types = if (edgeTypes.isEmpty) config.allowedEdgeTypes else edgeTypes
      DirectedEdgePaging.page(direction, limit, cursor, config.maxCursorOffset) {
        (phase, offset, fetchLimit) =>
          val query = phase match {
            case DirectedEdgePaging.Phase.Out                => outQuery
            case DirectedEdgePaging.Phase.In                 => inQuery
            case DirectedEdgePaging.Phase.InWithoutSelfLoops => inWithoutSelfLoopsQuery
          }
          RowCodec.map(
            execute(
              query,
              ujson.Obj(
                "id" -> id,
                "window" -> window,
                "types" -> ujson.Arr.from(types.toVector.sorted),
                "offset" -> offset,
                "limit" -> fetchLimit
              )
            )
          ) { rows =>
            val edges = rows.map(decodeDirected)
            // A row whose stored endpoints do not touch the requested node on the requested
            // side is a malformed response, never an edge to attribute.
            val consistent = edges.forall(e =>
              if (phase == DirectedEdgePaging.Phase.Out) e.fromId == id else e.toId == id
            )
            if (consistent) Found(edges) else Rejected("malformed-graph-response")
          }
      }
    }
  }
  private def decodeDirected(r: AwsJson): DirectedGraphEdge = DirectedGraphEdge(
    r("fromId").str,
    r("toId").str,
    r("edgeId").str,
    r("edgeType").str,
    r.obj
      .get("properties")
      .filter(_ != AwsJson.NullValue)
      .map(textProperties)
      .getOrElse(Map.empty)
  )
  def directCoauthors(id: String, window: String, limit: Int): StorageResult[GraphPage] =
    neighbors(id, window, Set("COAUTHORED_WITH"), limit, None)
  def shortestPaths(
      a: String,
      b: String,
      maxDepth: Int,
      window: String,
      limit: Int
  ): StorageResult[Vector[GraphPath]] = decoded {
    if (maxDepth < 1 || maxDepth > config.maxDepth || !validLimit(limit)) Rejected("invalid-bound")
    else {
      // Depth is selected from a finite configured allowlist; identifiers/window/limit are params.
      val templates = (1 to config.maxDepth).map { depth =>
        depth -> ("MATCH p=(a)-[:COAUTHORED_WITH*1.." + depth + "]-(b) WHERE id(a) = $a AND id(b) = $b AND all(r IN relationships(p) WHERE r.windowId = $window) RETURN [n IN nodes(p) | id(n)] AS nodeIds, [r IN relationships(p) | id(r)] AS edgeIds ORDER BY length(p), nodeIds LIMIT $limit")
      }.toMap
      RowCodec.map(
        execute(
          templates(maxDepth),
          ujson.Obj("a" -> a, "b" -> b, "window" -> window, "limit" -> limit)
        )
      ) { rows =>
        val paths = rows.map(r =>
          GraphPath(r("nodeIds").arr.map(_.str).toVector, r("edgeIds").arr.map(_.str).toVector)
        )
        Found(
          paths.headOption
            .map(p => paths.takeWhile(_.edgeIds.size == p.edgeIds.size))
            .getOrElse(Vector.empty)
        )
      }
    }
  }
  def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]] = decoded {
    if (!validLimit(limit)) Rejected("invalid-bound")
    else
      RowCodec.map(
        execute(
          "MATCH (n:RESEARCHER) WHERE n.communityMembershipKeys CONTAINS $membership RETURN id(n) AS nodeId ORDER BY nodeId LIMIT $limit",
          ujson.Obj(
            "membership" -> CommunityLookup.membership(window, communityId),
            "limit" -> limit
          )
        )
      )(rows => Found(rows.map(_("nodeId").str)))
  }
  def crossCommunityEdges(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[GraphPage] = decoded {
    if (!validLimit(limit)) Rejected("invalid-bound")
    else
      RowCodec.map(
        execute(
          "MATCH (a:RESEARCHER)-[r:COAUTHORED_WITH]-(b:RESEARCHER) WHERE a.communityMembershipKeys CONTAINS $membership AND b.communityWindowKeys CONTAINS $windowKey AND NOT b.communityMembershipKeys CONTAINS $membership AND r.windowId = $window RETURN id(b) AS nodeId, id(r) AS edgeId, type(r) AS edgeType, properties(r) AS properties, a.communityQualificationsJson AS communityQualificationsJson ORDER BY edgeId LIMIT $limit",
          ujson.Obj(
            "membership" -> CommunityLookup.membership(window, communityId),
            "windowKey" -> CommunityLookup.window(window),
            "window" -> window,
            "limit" -> limit
          )
        )
      )(rows => Found(GraphPage(rows.map(decodeNeighbor), None)))
  }
}

object NeptuneGraphReader {

  /** Closed refusal codes of `connect`. */
  val invalidEndpoint = "invalid-neptune-endpoint"
  val invalidRegion = "invalid-neptune-region"
  private val regionPattern = "[a-z]{2}(-[a-z]+)+-[0-9]+".r

  /** Test seam: a reader that owns (and therefore closes) an already built client. */
  private[storage] def owning(client: NeptunedataClient, config: GraphReaderConfig) =
    new NeptuneGraphReader(client, config, true)

  /** An https URI with a host and an explicit port, nothing else. */
  def validEndpoint(endpoint: URI): Boolean =
    endpoint != null && "https".equals(endpoint.getScheme) && endpoint.getHost != null &&
      endpoint.getHost.nonEmpty && endpoint.getPort >= 1 && endpoint.getPort <= 65535 &&
      endpoint.getUserInfo == null && endpoint.getRawQuery == null &&
      endpoint.getRawFragment == null &&
      Option(endpoint.getRawPath).forall(p => p.isEmpty || p == "/")

  /** Builds the read-only reader and its owned client. No network call is made: credentials are
    * resolved lazily by the SDK on the first query. SDK retries are disabled because the reader
    * owns the bounded `config.retry` policy; the SDK call timeouts follow the configured query
    * timeout plus the one-second margin already used per request. Refusals are closed codes.
    */
  def connect(
      endpoint: URI,
      region: String,
      credentials: AwsCredentialsProvider,
      config: GraphReaderConfig
  ): Either[String, NeptuneGraphReader] =
    if (!validEndpoint(endpoint)) Left(invalidEndpoint)
    else if (region == null || !regionPattern.matches(region)) Left(invalidRegion)
    else if (credentials == null) Left("missing-credentials")
    else {
      val timeout = Duration.ofMillis(config.requestTimeoutMillis + 1000)
      val client = NeptunedataClient
        .builder()
        .region(Region.of(region))
        .credentialsProvider(credentials)
        .endpointOverride(endpoint)
        .overrideConfiguration(
          ClientOverrideConfiguration
            .builder()
            .retryStrategy(AwsRetryStrategy.doNotRetry())
            .apiCallTimeout(timeout)
            .apiCallAttemptTimeout(timeout)
            .build()
        )
        .build()
      Right(new NeptuneGraphReader(client, config, true))
    }
}
