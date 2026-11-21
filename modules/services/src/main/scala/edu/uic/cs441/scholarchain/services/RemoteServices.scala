package edu.uic.cs441.scholarchain.services

import java.net.{URI, URLEncoder}
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.time.Duration
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal

/** Endpoint/token values are runtime injection inputs, never logged or included in public errors.
  */
final class RemoteService(
    baseUri: URI,
    internalToken: String,
    config: ServiceConfig,
    metrics: ServiceMetrics,
    dependencyName: String
) extends AutoCloseable {
  require(
    Set("http", "https")(
      baseUri.getScheme
    ) && baseUri.getHost != null && baseUri.getUserInfo == null && internalToken.nonEmpty
  )
  // Ceil with BigInt keeps even very large configured transport durations overflow-safe.
  private val graphWorkBudgetMs = if (dependencyName == "graph") {
    val reserve =
      ((BigInt(config.downstreamTimeoutMs) * config.graphDeadlineReservePercent + 99) / 100).toLong
    val work = config.downstreamTimeoutMs - reserve
    require(work > 0, "graph-transport-must-leave-positive-work-and-response-budgets")
    work
  } else config.downstreamTimeoutMs
  private val http =
    HttpClient.newBuilder().connectTimeout(Duration.ofMillis(config.downstreamTimeoutMs)).build()
  private val boundary = new DownstreamClient(
    config,
    new CircuitBreaker(config.breakerFailureThreshold, config.breakerResetMs),
    metrics,
    dependencyName
  )
  def call(
      method: String,
      path: String,
      params: Map[String, String],
      body: Option[String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = {
    val effectiveParams = graphParameters(method, path, params) match {
      case Left(error)  => return Left(error)
      case Right(value) => value
    }
    val query =
      if (effectiveParams.isEmpty) ""
      else
        effectiveParams.toVector
          .sortBy(_._1)
          .map((k, v) => RemoteService.segment(k) + "=" + RemoteService.segment(v))
          .mkString("?", "&", "")
    boundary.call(method, context) { correlation =>
      try {
        val builder = HttpRequest
          .newBuilder(URI.create(baseUri.toString.stripSuffix("/") + path + query))
          .timeout(Duration.ofMillis(config.downstreamTimeoutMs))
          .header("Authorization", "Bearer " + internalToken)
          .header("Content-Type", "application/json")
        correlation.foreach((k, v) => builder.header(k, v))
        val request = builder
          .method(
            method,
            body
              .map(HttpRequest.BodyPublishers.ofString(_))
              .getOrElse(HttpRequest.BodyPublishers.noBody())
          )
          .build()
        val response = http.send(request, HttpResponse.BodyHandlers.ofInputStream())
        val in = response.body()
        val bytes =
          try in.readNBytes(config.maxResultBytes + 1)
          finally in.close()
        if (bytes.length > config.maxResultBytes)
          Left(
            ApiError(
              502,
              "DOWNSTREAM_RESULT_TOO_LARGE",
              "Downstream result exceeds the configured bound."
            )
          )
        else if (response.statusCode() >= 200 && response.statusCode() < 300)
          Right(ApiReply(response.statusCode(), ujson.read(new String(bytes, UTF_8))))
        else {
          val status = response.statusCode()
          val safe = Map(
            400 -> ApiError.invalid,
            401 -> ApiError(
              502,
              "DOWNSTREAM_AUTH_FAILURE",
              "A downstream service rejected authentication."
            ),
            404 -> ApiError(404, "NOT_FOUND", "The requested record was not found."),
            409 -> ApiError(409, "DOWNSTREAM_CONFLICT", "A downstream state conflict occurred."),
            422 -> ApiError.unsupported,
            429 -> ApiError(429, "THROTTLED", "A downstream service is throttled.", true),
            503 -> ApiError.unavailable,
            504 -> ApiError.timeout
          )
          // Only a fully typed, allowlisted graph-operation deadline is request-specific.
          // Every other status/body retains the existing dependency-failure classification.
          Left(
            graphRequestDeadline(method, path, status, bytes).getOrElse(
              safe.getOrElse(status, ApiError.downstream)
            )
          )
        }
      } catch {
        case _: java.net.http.HttpTimeoutException => Left(ApiError.timeout)
        case _: InterruptedException =>
          Thread.currentThread().interrupt(); Left(ApiError.unavailable)
        case NonFatal(_) => Left(ApiError.downstream)
      }
    }
  }
  private def graphOperation(method: String, path: String): Boolean =
    dependencyName == "graph" && method == "GET" &&
      path.matches(
        "/internal/v1/graph/(?:nodes/[^/]+(?:/neighbors)?|metrics/[^/]+|paths|communities/[^/]+/(?:members|cross-edges))"
      )
  private def graphParameters(
      method: String,
      path: String,
      params: Map[String, String]
  ): Either[ApiError, Map[String, String]] = {
    if (!graphOperation(method, path)) Right(params)
    else
      try {
        val requested =
          params.get("timeoutMs").map(_.toLong).getOrElse(config.graphRequestTimeoutMs)
        if (requested <= 0 || requested > config.graphRequestTimeoutMs) Left(ApiError.invalid)
        else Right(params.updated("timeoutMs", math.min(requested, graphWorkBudgetMs).toString))
      } catch { case NonFatal(_) => Left(ApiError.invalid) }
  }
  private def graphRequestDeadline(
      method: String,
      path: String,
      status: Int,
      bytes: Array[Byte]
  ): Option[ApiError] = {
    if (!graphOperation(method, path) || status != 504) None
    else
      try {
        val json = ujson.read(new String(bytes, UTF_8))
        val typed = json.obj.keySet == Set("error", "message", "traceId", "retryable") &&
          json("error").strOpt.contains(ApiError.graphDeadline.code) &&
          json("message").strOpt.isDefined &&
          json("traceId").strOpt.exists(_.matches("[a-zA-Z0-9._:-]{1,128}")) &&
          json("retryable").boolOpt.contains(false)
        // The body was already byte-bounded. Its arbitrary message and remote trace are never
        // forwarded: public dispatch supplies the caller's trace and a fixed safe message.
        Option.when(typed)(ApiError.graphDeadline)
      } catch { case NonFatal(_) => None }
  }
  def close(): Unit = boundary.close()
}
object RemoteService {
  def segment(value: String): String = URLEncoder.encode(value, UTF_8).replace("+", "%20")
}
final class RemoteGraphApi(remote: RemoteService) extends GraphEndpoints {
  override def ready(context: RequestContext): Boolean =
    remote.call("GET", "/readyz", Map.empty, None, context).exists(_.status == 200)
  def node(id: String, c: RequestContext): Either[ApiError, ApiReply] = node(id, Map.empty, c)
  override def node(
      id: String,
      params: Map[String, String],
      c: RequestContext
  ): Either[ApiError, ApiReply] =
    remote.call("GET", "/internal/v1/graph/nodes/" + RemoteService.segment(id), params, None, c)
  def neighbors(id: String, p: Map[String, String], c: RequestContext) = remote.call(
    "GET",
    "/internal/v1/graph/nodes/" + RemoteService.segment(id) + "/neighbors",
    p,
    None,
    c
  )
  def metrics(id: String, window: String, c: RequestContext): Either[ApiError, ApiReply] =
    metrics(id, window, Map.empty, c)
  override def metrics(
      id: String,
      window: String,
      params: Map[String, String],
      c: RequestContext
  ): Either[ApiError, ApiReply] = remote.call(
    "GET",
    "/internal/v1/graph/metrics/" + RemoteService.segment(id),
    params.updated("window", window),
    None,
    c
  )
  def paths(p: Map[String, String], c: RequestContext) =
    remote.call("GET", "/internal/v1/graph/paths", p, None, c)
  override def communityMembers(
      id: String,
      p: Map[String, String],
      c: RequestContext
  ): Either[ApiError, ApiReply] = remote.call(
    "GET",
    "/internal/v1/graph/communities/" + RemoteService.segment(id) + "/members",
    p,
    None,
    c
  )
  override def crossCommunityEdges(
      id: String,
      p: Map[String, String],
      c: RequestContext
  ): Either[ApiError, ApiReply] = remote.call(
    "GET",
    "/internal/v1/graph/communities/" + RemoteService.segment(id) + "/cross-edges",
    p,
    None,
    c
  )
  def close(): Unit = remote.close()
}
final class RemoteSemanticApi(remote: RemoteService) extends SemanticEndpoints {
  override def ready(context: RequestContext): Boolean =
    remote.call("GET", "/readyz", Map.empty, None, context).exists(_.status == 200)
  def retrieve(body: String, c: RequestContext) =
    remote.call("POST", "/internal/v1/semantic/retrieve", Map.empty, Some(body), c)
  def close(): Unit = remote.close()
}
