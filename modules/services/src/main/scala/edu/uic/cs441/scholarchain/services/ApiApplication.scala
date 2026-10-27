package edu.uic.cs441.scholarchain.services

import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.LongAdder
import scala.jdk.CollectionConverters.*
import scala.util.control.NonFatal

final class ServiceMetrics {
  private val statuses = new ConcurrentHashMap[Int, LongAdder]()
  private val verification = new ConcurrentHashMap[String, LongAdder]()
  private val buckets = Vector(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 60.0)
  private val latencies = buckets.map(_ => new LongAdder)
  private val requests = new LongAdder; private val nanos = new LongAdder
  private val abstentions = new LongAdder; private val timeouts = new LongAdder
  private val downstreamErrors = new LongAdder
  private val downstreamTimeouts = new LongAdder
  private val breakers = new ConcurrentHashMap[String, () => String]()
  def registerBreaker(name: String, state: () => String): Unit = {
    require(name.matches("[a-zA-Z0-9_]{1,64}")); breakers.put(name, state); ()
  }
  def observe(status: Int, elapsedNanos: Long): Unit = {
    requests.increment(); nanos.add(elapsedNanos)
    statuses.computeIfAbsent(status, _ => new LongAdder).increment()
    val seconds = elapsedNanos.toDouble / 1e9
    buckets.zip(latencies).foreach { (upper, counter) => if (seconds <= upper) counter.increment() }
    if (status == 504) timeouts.increment()
  }
  def downstream(status: Int): Unit = {
    if (status == 504) downstreamTimeouts.increment()
    if (status == 502 || status == 504) downstreamErrors.increment()
  }
  def workflow(status: String, abstained: Boolean): Unit = {
    val label =
      if (Set("VERIFIED", "PARTIAL", "REJECTED", "ABSTAINED", "UNVERIFIED")(status)) status
      else "OTHER"
    verification.computeIfAbsent(label, _ => new LongAdder).increment()
    if (abstained) abstentions.increment()
  }
  def render: String = {
    val lines = Vector(s"api_requests_total ${requests.sum()}") ++
      statuses.asScala.toVector
        .sortBy(_._1)
        .map((s, n) => s"api_status_total{status=\"$s\"} ${n.sum()}") ++
      buckets.zip(latencies).map((b, n) => s"api_latency_seconds_bucket{le=\"$b\"} ${n.sum()}") ++
      Vector(
        s"api_latency_seconds_bucket{le=\"+Inf\"} ${requests.sum()}",
        s"api_latency_seconds_count ${requests.sum()}",
        s"api_latency_seconds_sum ${nanos.sum().toDouble / 1e9}",
        s"api_timeouts_total ${timeouts.sum()}",
        s"api_downstream_errors_total ${downstreamErrors.sum()}",
        s"downstream_timeouts_total ${downstreamTimeouts.sum()}",
        s"workflow_abstentions_total ${abstentions.sum()}"
      ) ++
      verification.asScala.toVector
        .sortBy(_._1)
        .map((s, n) => s"workflow_verification_total{status=\"$s\"} ${n.sum()}") ++
      breakers.asScala.toVector.sortBy(_._1).flatMap { (name, state) =>
        val current = state();
        Vector("CLOSED", "OPEN", "HALF_OPEN").map(s =>
          s"downstream_circuit_state{dependency=\"$name\",state=\"$s\"} ${if (s == current) 1 else 0}"
        )
      }
    lines.mkString("", "\n", "\n")
  }
}

/** Logs are constructed from an allowlist, so arbitrary headers, bodies, URLs, provider errors, or
  * user supplied fields can never enter the log payload.
  */
object SafeLog {
  def request(context: RequestContext, route: String, status: Int, elapsedMs: Long): String =
    ujson
      .Obj(
        "event" -> "http_request",
        "requestId" -> context.requestId,
        "traceId" -> context.traceId,
        "route" -> route,
        "status" -> status,
        "elapsedMs" -> elapsedMs
      )
      .render()
}
final case class HttpReply(status: Int, body: String, headers: Map[String, String])
final class ApiApplication(
    queries: QueryService,
    config: ServiceConfig,
    readiness: () => Boolean = () => true,
    logSink: String => Unit = s => org.slf4j.LoggerFactory.getLogger("scholarchain.http").info(s),
    serviceRole: String = "query-api"
) extends AutoCloseable {
  def requestByteLimit: Int = config.maxRequestBytes
  def requestReadTimeoutMs: Int = config.requestReadTimeoutMs
  private def safeId(value: Option[String], prefix: String): String =
    value.filter(_.matches("[a-zA-Z0-9._:-]{1,128}")).getOrElse(prefix + UUID.randomUUID().toString)
  private def routeLabel(path: String): String = path match {
    case "/healthz" | "/readyz" | "/metrics" | "/v1/query" => path
    case p if p.startsWith("/v1/jobs/")                    => "/v1/jobs/{jobId}"
    case _                                                 => "unmatched"
  }
  def handle(
      method: String,
      path: String,
      headers: Map[String, String],
      body: String,
      transportError: Option[ApiError] = None
  ): HttpReply = {
    val start = System.nanoTime()
    val normalized = headers.map((k, v) => k.toLowerCase(java.util.Locale.ROOT) -> v)
    val context = RequestContext(
      safeId(normalized.get("x-request-id"), "req-"),
      safeId(normalized.get("x-trace-id"), "trace-")
    )
    val responseHeaders = Map(
      "Content-Type" -> "application/json",
      "X-Request-Id" -> context.requestId,
      "X-Trace-Id" -> context.traceId,
      "Cache-Control" -> "no-store"
    )
    val result: Either[ApiError, ApiReply] =
      try {
        val open = method == "GET" && Set("/healthz", "/readyz")(path)
        val hash =
          if (path.startsWith("/internal/")) config.internalTokenSha256 else config.apiKeySha256
        if (!open && !Auth.authorized(normalized.get("authorization"), hash))
          Left(ApiError(401, "UNAUTHORIZED", "Missing or invalid authentication."))
        else if (transportError.nonEmpty) Left(transportError.get)
        else if (method == "GET" && path == "/healthz")
          Right(ApiReply(200, ujson.Obj("status" -> "alive")))
        else if (method == "GET" && path == "/readyz") {
          if (readiness()) Right(ApiReply(200, ujson.Obj("status" -> "ready")))
          else Left(ApiError(503, "NOT_READY", "Dependencies are unavailable.", true))
        } else if (method == "GET" && path == "/metrics")
          Right(ApiReply(200, ujson.Str(queries.metrics.render)))
        else if (serviceRole == "query-api" && method == "POST" && path == "/v1/query") {
          if (
            body.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > config.maxRequestBytes
          ) Left(ApiError.invalid)
          else
            normalized
              .get("idempotency-key")
              .filter(k =>
                k.nonEmpty && k.length <= config.maxIdempotencyKeyChars && !k.exists(_.isControl)
              )
              .toRight(
                ApiError(
                  400,
                  "IDEMPOTENCY_KEY_REQUIRED",
                  "A bounded Idempotency-Key header is required."
                )
              )
              .flatMap { key =>
                QueryRequest.parse(body, config).flatMap(queries.submit(_, key, context))
              }
        } else if (serviceRole == "query-api" && method == "GET" && path.startsWith("/v1/jobs/")) {
          val parts = path.stripPrefix("/v1/jobs/").split("/", -1).toVector
          parts match {
            case Vector(id)           => queries.job(id)
            case Vector(id, "result") => queries.result(id)
            case _ => Left(ApiError(404, "NOT_FOUND", "The requested route was not found."))
          }
        } else Left(ApiError(404, "NOT_FOUND", "The requested route was not found."))
      } catch { case NonFatal(_) => Left(ApiError.internal) }
    val reply = result.fold(e => ApiReply(e.status, e.json(context.traceId)), identity)
    val elapsed = System.nanoTime() - start
    queries.metrics.observe(reply.status, elapsed)
    try logSink(SafeLog.request(context, routeLabel(path), reply.status, elapsed / 1000000L))
    catch { case NonFatal(_) => () }
    if (path == "/metrics" && reply.status == 200)
      HttpReply(
        reply.status,
        reply.body.str,
        responseHeaders.updated("Content-Type", "text/plain; version=0.0.4")
      )
    else HttpReply(reply.status, reply.body.render(), responseHeaders)
  }
  def close(): Unit = queries.close()
}
