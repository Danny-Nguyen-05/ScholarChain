package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import scala.util.control.NonFatal

trait GraphEndpoints extends AutoCloseable {
  def ready(context: RequestContext): Boolean = true
  def node(id: String, context: RequestContext): Either[ApiError, ApiReply]
  def node(
      id: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    if (params.isEmpty) node(id, context) else Left(ApiError.invalid)
  def neighbors(
      id: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply]
  def metrics(id: String, window: String, context: RequestContext): Either[ApiError, ApiReply]
  def metrics(
      id: String,
      window: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] =
    if (params.keySet.subsetOf(Set("window"))) metrics(id, window, context)
    else Left(ApiError.invalid)
  def paths(params: Map[String, String], context: RequestContext): Either[ApiError, ApiReply]

  /** Stored community members. Implementations that do not serve communities keep the typed
    * refusal; the default is never an approximation.
    */
  def communityMembers(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = Left(ApiError.unsupported)
  def crossCommunityEdges(
      communityId: String,
      params: Map[String, String],
      context: RequestContext
  ): Either[ApiError, ApiReply] = Left(ApiError.unsupported)
}
trait SemanticEndpoints extends AutoCloseable {
  def ready(context: RequestContext): Boolean = true
  def retrieve(body: String, context: RequestContext): Either[ApiError, ApiReply]
}
final case class SemanticApiConfig(
    maxTopK: Int = 50,
    maxQuestionChars: Int = 8192,
    maxBodyBytes: Int = 65536,
    maxFilters: Int = 16,
    timeoutMs: Long = 5000
) {
  require(
    maxTopK > 0 && maxQuestionChars > 0 && maxBodyBytes > 0 && maxFilters > 0 && timeoutMs > 0
  )
}
final class SemanticApi(
    retrieve: (ujson.Value, RequestContext) => Either[ApiError, ujson.Value],
    config: SemanticApiConfig = SemanticApiConfig()
) extends SemanticEndpoints {
  private val deadlineConfig = ServiceConfig(
    Auth.sha256("semantic-boundary-placeholder"),
    Auth.sha256("semantic-boundary-internal-placeholder"),
    downstreamTimeoutMs = config.timeoutMs,
    downstreamMaxAttempts = 1
  )
  private val deadline =
    new DownstreamClient(deadlineConfig, new CircuitBreaker(Int.MaxValue, config.timeoutMs))
  def retrieve(body: String, context: RequestContext): Either[ApiError, ApiReply] = try {
    if (
      body.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > config.maxBodyBytes ||
      !RequestJson.withinDepth(body)
    ) return Left(ApiError.invalid)
    val json = ujson.read(body)
    if (!json.obj.keySet.subsetOf(Set("question", "topK", "filters"))) return Left(ApiError.invalid)
    val question = json("question").str
    val topK = json.obj.get("topK").map(_.num).getOrElse(config.maxTopK.toDouble)
    if (
      question.trim.isEmpty || question.length > config.maxQuestionChars || !topK.isWhole || topK < 1 || topK > config.maxTopK
    ) return Left(ApiError.invalid)
    json.obj.get("filters").foreach { f =>
      if (
        f.obj.size > config.maxFilters || f.obj
          .exists((k, v) => k.isEmpty || v.str.length > config.maxQuestionChars)
      ) throw new IllegalArgumentException
    }
    deadline.call("POST", context)(_ => retrieve(json, context)).map(v => ApiReply(200, v))
  } catch { case NonFatal(_) => Left(ApiError.invalid) }
  def close(): Unit = deadline.close()
}
object SemanticApi {

  /** Existing embedding/vector ports do the work. Query text is never logged. Returned hits are
    * actual backend records; no hit, score, or source evidence is synthesized by the route.
    */
  def fromPorts(
      embedding: EmbeddingClient,
      model: EmbeddingModel,
      vectors: VectorStore,
      index: String,
      config: SemanticApiConfig = SemanticApiConfig()
  ): SemanticApi =
    new SemanticApi(
      (json, _) => {
        val topK = json.obj.get("topK").map(_.num.toInt).getOrElse(config.maxTopK)
        val filters =
          json.obj.get("filters").map(_.obj.toMap.map((k, v) => k -> v.str)).getOrElse(Map.empty)
        embedding.embed(Vector(json("question").str)).head match {
          case EmbeddingSuccess(values, _, _) =>
            PortResult.read(vectors.query(index, values, topK, filters)).map { hits =>
              ujson.Obj(
                "hits" -> ujson.Arr.from(
                  hits.map(h =>
                    ujson.Obj(
                      "key" -> h.key,
                      "distance" -> h.distance,
                      "metadata" -> ujson.Obj.from(h.metadata.map((k, v) => k -> ujson.Str(v)))
                    )
                  )
                ),
                "model" -> upickle.default.writeJs(model)
              )
            }
          case _ => Left(ApiError.downstream)
        }
      },
      config
    )
}
final case class ExtendedApi(
    evidence: EvidenceApi,
    graph: GraphEndpoints,
    semantic: SemanticEndpoints
) extends AutoCloseable {
  def close(): Unit = { graph.close(); semantic.close() }
}
