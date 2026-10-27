package edu.uic.cs441.scholarchain.services

import java.nio.charset.StandardCharsets.UTF_8
import java.security.MessageDigest
import scala.util.control.NonFatal
import scala.util.boundary

final case class ApiError(status: Int, code: String, message: String, retryable: Boolean = false) {
  def json(traceId: String): ujson.Value = ujson.Obj(
    "error" -> code,
    "message" -> message,
    "traceId" -> traceId,
    "retryable" -> retryable
  )
}
object ApiError {
  val invalid = ApiError(400, "INVALID_REQUEST", "Malformed request or invalid field.")
  val unsupported =
    ApiError(422, "UNSUPPORTED_QUERY", "The requested query constraints are unsupported.")
  val unavailable = ApiError(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable.", true)
  val downstream = ApiError(502, "DOWNSTREAM_FAILURE", "A downstream dependency failed.", true)
  val timeout = ApiError(504, "DOWNSTREAM_TIMEOUT", "A downstream dependency timed out.", true)
  val internal = ApiError(500, "INTERNAL_ERROR", "An internal error occurred.")
}
final case class RequestContext(requestId: String, traceId: String, queryId: String = "") {
  def downstreamHeaders: Map[String, String] =
    Map("X-Request-Id" -> requestId, "X-Trace-Id" -> traceId)
}
final case class QueryRequest(question: String, json: ujson.Value)
final case class WorkflowOutput(
    answer: ujson.Value,
    claims: Vector[ujson.Value] = Vector.empty,
    verificationStatus: String = "VERIFIED",
    abstained: Boolean = false
)
trait QueryWorkflow {
  def run(
      request: QueryRequest,
      context: RequestContext,
      stage: String => Unit
  ): Either[ApiError, WorkflowOutput]
}
final case class ServiceConfig(
    apiKeySha256: String,
    internalTokenSha256: String,
    synchronousDeadlineMs: Long = 15000,
    workflowTimeoutMs: Long = 60000,
    maxWorkflowRetries: Int = 2,
    workerThreads: Int = 4,
    queueCapacity: Int = 64,
    maxRequestBytes: Int = 65536,
    maxResultBytes: Int = 131072,
    maxQuestionChars: Int = 8192,
    maxGraphLimit: Int = 100,
    maxVectorLimit: Int = 50,
    maxPathDepth: Int = 6,
    downstreamTimeoutMs: Long = 5000,
    downstreamMaxAttempts: Int = 3,
    breakerFailureThreshold: Int = 3,
    breakerResetMs: Long = 30000,
    host: String = "127.0.0.1",
    port: Int = 8080,
    sessionCasAttempts: Int = 8,
    maxFilterItems: Int = 100,
    maxFilterChars: Int = 512,
    sessionPollMs: Long = 50,
    maxIdempotencyKeyChars: Int = 256,
    requestReadTimeoutMs: Int = 5000
) {
  require(Vector(apiKeySha256, internalTokenSha256).forall(_.matches("[0-9a-f]{64}")))
  require(apiKeySha256 != internalTokenSha256, "separate-auth-domains-required")
  require(synchronousDeadlineMs > 0 && workflowTimeoutMs >= synchronousDeadlineMs)
  require(maxWorkflowRetries >= 0 && maxWorkflowRetries <= 10)
  require(workerThreads > 0 && queueCapacity > 0 && maxRequestBytes > 0 && maxResultBytes > 0)
  require(maxQuestionChars > 0 && maxGraphLimit > 0 && maxVectorLimit > 0 && maxPathDepth > 0)
  require(
    downstreamTimeoutMs > 0 && downstreamMaxAttempts > 0 && breakerFailureThreshold > 0 && breakerResetMs > 0
  )
  require(
    sessionCasAttempts > 0 && maxFilterItems > 0 && maxFilterChars > 0 && sessionPollMs > 0 && maxIdempotencyKeyChars > 0 && requestReadTimeoutMs > 0
  )
  require(port >= 0 && port <= 65535 && host.nonEmpty)
}
object ServiceConfig {

  /** Secrets Manager injects only hashes; there are deliberately no default credentials. */
  def fromEnvironment(env: Map[String, String]): Either[String, ServiceConfig] = try {
    def required(key: String) = env.getOrElse(key, throw new IllegalArgumentException)
    def int(key: String, default: Int) = env.get(key).map(_.toInt).getOrElse(default)
    def long(key: String, default: Long) = env.get(key).map(_.toLong).getOrElse(default)
    Right(
      ServiceConfig(
        required("SCHOLARCHAIN_API_KEY_SHA256"),
        required("SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"),
        long("SCHOLARCHAIN_SYNCHRONOUS_DEADLINE_MS", 15000),
        long("SCHOLARCHAIN_WORKFLOW_TIMEOUT_MS", 60000),
        int("SCHOLARCHAIN_MAX_WORKFLOW_RETRIES", 2),
        int("SCHOLARCHAIN_WORKER_THREADS", 4),
        int("SCHOLARCHAIN_QUEUE_CAPACITY", 64),
        int("SCHOLARCHAIN_MAX_REQUEST_BYTES", 65536),
        int("SCHOLARCHAIN_MAX_RESULT_BYTES", 131072),
        int("SCHOLARCHAIN_MAX_QUESTION_CHARS", 8192),
        int("SCHOLARCHAIN_MAX_GRAPH_LIMIT", 100),
        int("SCHOLARCHAIN_MAX_VECTOR_LIMIT", 50),
        int("SCHOLARCHAIN_MAX_PATH_DEPTH", 6),
        long("SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS", 5000),
        int("SCHOLARCHAIN_DOWNSTREAM_MAX_ATTEMPTS", 3),
        int("SCHOLARCHAIN_BREAKER_FAILURE_THRESHOLD", 3),
        long("SCHOLARCHAIN_BREAKER_RESET_MS", 30000),
        env.getOrElse("SCHOLARCHAIN_HTTP_HOST", "127.0.0.1"),
        int("SCHOLARCHAIN_HTTP_PORT", 8080),
        int("SCHOLARCHAIN_SESSION_CAS_ATTEMPTS", 8),
        int("SCHOLARCHAIN_MAX_FILTER_ITEMS", 100),
        int("SCHOLARCHAIN_MAX_FILTER_CHARS", 512),
        long("SCHOLARCHAIN_SESSION_POLL_MS", 50),
        int("SCHOLARCHAIN_MAX_IDEMPOTENCY_KEY_CHARS", 256),
        int("SCHOLARCHAIN_REQUEST_READ_TIMEOUT_MS", 5000)
      )
    )
  } catch { case NonFatal(_) => Left("invalid-or-missing-service-configuration") }
}
object Auth {
  def sha256(value: String): String = MessageDigest
    .getInstance("SHA-256")
    .digest(value.getBytes(UTF_8))
    .map(b => f"${b & 255}%02x")
    .mkString
  def authorized(header: Option[String], expectedHash: String): Boolean = {
    val token = header.filter(_.startsWith("Bearer ")).map(_.substring(7)).getOrElse("")
    val actual = sha256(token).getBytes(UTF_8)
    MessageDigest.isEqual(actual, expectedHash.getBytes(UTF_8)) && token.nonEmpty
  }
}
object QueryRequest {
  private def canonical(v: ujson.Value): ujson.Value = v match {
    case o: ujson.Obj =>
      ujson.Obj.from(o.obj.toVector.sortBy(_._1).map((k, x) => k -> canonical(x)))
    case a: ujson.Arr => ujson.Arr.from(a.arr.map(canonical))
    case x            => x
  }
  def fingerprint(request: QueryRequest): String = Auth.sha256(canonical(request.json).render())
  def parse(body: String, config: ServiceConfig): Either[ApiError, QueryRequest] = boundary {
    try {
      val value = ujson.read(body); val obj = value.obj
      if (!obj.keySet.subsetOf(Set("question", "constraints", "analysis", "retrieval", "output")))
        boundary.break(Left(ApiError.unsupported))
      val question = value("question").str
      if (question.trim.isEmpty || question.length > config.maxQuestionChars)
        boundary.break(Left(ApiError.invalid))
      val fields = Map(
        "constraints" -> Set("yearFrom", "yearTo", "topics", "institutions", "venues"),
        "analysis" -> Set(
          "rankingMetric",
          "includeTeamSize",
          "includeBridgeMetrics",
          "includeCommunities",
          "includePaths"
        ),
        "retrieval" -> Set("graphLimit", "vectorLimit", "maxPathDepth"),
        "output" -> Set("includeEvidence", "includeScores", "includeUncertainty")
      )
      for ((name, allowed) <- fields; section <- obj.get(name)) {
        if (!section.obj.keySet.subsetOf(allowed)) boundary.break(Left(ApiError.unsupported))
        section.obj.foreach { (key, v) =>
          if (key.startsWith("include")) v.bool
          else if (Set("topics", "institutions", "venues")(key)) {
            if (
              v.arr.size > config.maxFilterItems || v.arr
                .exists(x => x.str.trim.isEmpty || x.str.length > config.maxFilterChars)
            ) boundary.break(Left(ApiError.invalid))
          } else if (key == "rankingMetric") {
            if (
              !Set(
                "DISTINCT_COAUTHOR_COUNT",
                "PUBLICATION_COUNT",
                "WEIGHTED_DEGREE",
                "MAXIMUM_COAUTHORS_ON_ONE_PAPER",
                "BRIDGE_SCORE",
                "TOTAL_COAUTHOR_OCCURRENCES",
                "AVERAGE_COAUTHORS_PER_PAPER",
                "CORENESS"
              )(v.str)
            ) boundary.break(Left(ApiError.unsupported))
          } else {
            val n = v.num
            if (!n.isWhole || n < 1 || n > Int.MaxValue) boundary.break(Left(ApiError.invalid))
            val max = key match {
              case "graphLimit"   => config.maxGraphLimit
              case "vectorLimit"  => config.maxVectorLimit
              case "maxPathDepth" => config.maxPathDepth
              case _              => 9999
            }
            if (n > max) boundary.break(Left(ApiError.unsupported))
          }
        }
      }
      obj.get("constraints").foreach { c =>
        if (
          c.obj.contains("yearFrom") && c.obj
            .contains("yearTo") && c("yearFrom").num > c("yearTo").num
        ) boundary.break(Left(ApiError.invalid))
      }
      Right(QueryRequest(question, canonical(value)))
    } catch { case b: boundary.Break[?] => throw b; case NonFatal(_) => Left(ApiError.invalid) }
  }
}
