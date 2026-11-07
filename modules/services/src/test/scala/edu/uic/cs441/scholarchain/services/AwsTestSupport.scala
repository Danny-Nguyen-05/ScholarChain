package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.{LlmClient, LlmResult, StructuredLlmRequest}
import edu.uic.cs441.scholarchain.storage.*
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.file.{Files, Path}
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import scala.jdk.CollectionConverters.*

/** Scriptable stand-ins for the AWS-backed ports. They never leave the process. A dependency can be
  * made to answer cleanly (absent data), to be refused, or to hang until interrupted.
  */
final class Dependencies {
  private val counters = new ConcurrentHashMap[String, AtomicInteger]()
  @volatile var failing: Set[String] = Set.empty
  @volatile var hanging: Set[String] = Set.empty
  def calls(name: String): Int = Option(counters.get(name)).map(_.get).getOrElse(0)
  def total: Int = counters.values.asScala.map(_.get).sum
  def touch(name: String): StorageResult[Nothing] = {
    counters.computeIfAbsent(name, _ => new AtomicInteger).incrementAndGet()
    if (hanging(name)) {
      try Thread.sleep(60000)
      catch { case _: InterruptedException => () }
      StorageResult.Rejected("hung")
    } else if (failing(name)) StorageResult.Rejected("denied")
    else StorageResult.Missing
  }
}

final class FakeReader(d: Dependencies) extends DirectedGraphReader {
  def node(id: String): StorageResult[GraphNode] = d.touch("neptune")
  def directedEdges(
      id: String,
      window: String,
      direction: EdgeDirection,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[DirectedEdgePage] = {
    d.touch("edges"); StorageResult.Found(DirectedEdgePage(Vector.empty, None))
  }
  def neighbors(
      id: String,
      window: String,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ) =
    StorageResult.Rejected("unused")
  def directCoauthors(id: String, window: String, limit: Int) = StorageResult.Rejected("unused")
  def shortestPaths(a: String, b: String, maxDepth: Int, window: String, limit: Int) =
    StorageResult.Rejected("unused")
  def communityMembers(communityId: String, window: String, limit: Int) =
    StorageResult.Rejected("unused")
  def crossCommunityEdges(communityId: String, window: String, limit: Int) =
    StorageResult.Rejected("unused")
}
final class FakeMetrics(d: Dependencies) extends ResearcherMetricStore {
  def put(record: ResearcherMetricRecord) = StorageResult.Rejected("unused")
  def get(researcherId: String, windowId: String): StorageResult[ResearcherMetricRecord] =
    d.touch("metrics")
  def batchGet(keys: Vector[(String, String)]) = StorageResult.Rejected("unused")
}
final class FakeVectors(d: Dependencies) extends VectorStore {
  def ensureIndex(name: String, dimension: Int, metric: String) = StorageResult.Rejected("unused")
  def putBatch(index: String, documents: Vector[VectorDocument]) = StorageResult.Rejected("unused")
  def query(index: String, vector: Vector[Float], topK: Int, filter: Map[String, String]) =
    StorageResult.Rejected("unused")
  def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
    d.touch("vectors") match {
      case StorageResult.Missing => StorageResult.Found(Vector.empty)
      case other                 => other
    }
}
final class FakeEmbedder(d: Dependencies, val model: EmbeddingModel) extends EmbeddingClient {
  def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
    d.touch("embed")
    texts.map(_ => EmbeddingFailure("fake-embedding-unavailable", false, model, 1))
  }
}
final class FakeSessions(d: Dependencies) extends QuerySessionStore {
  def createIfAbsent(queryId: String, idempotencyKey: String) = StorageResult.Rejected("unused")
  def get(queryId: String): StorageResult[QuerySession] = d.touch("sessions")
  def lookupByIdempotencyKey(key: String) = StorageResult.Rejected("unused")
  def update(session: QuerySession, expectedRevision: Long) = StorageResult.Rejected("unused")
}

/** Session store that really stores sessions, except that the readiness probe key is counted. */
final class FunctionalSessions(d: Dependencies) extends QuerySessionStore {
  private val inner = new InMemoryQuerySessionStore
  def createIfAbsent(queryId: String, idempotencyKey: String) =
    inner.createIfAbsent(queryId, idempotencyKey)
  def get(queryId: String): StorageResult[QuerySession] =
    if (queryId == ReadinessProbes.probeKey) d.touch("sessions") else inner.get(queryId)
  def lookupByIdempotencyKey(key: String) = inner.lookupByIdempotencyKey(key)
  def update(session: QuerySession, expectedRevision: Long) =
    inner.update(session, expectedRevision)
}
final class FakeEvidence(d: Dependencies) extends EvidenceBundleStore {
  def put(bundle: EvidenceBundle) = StorageResult.Rejected("unused")
  def get(evidenceId: String): StorageResult[EvidenceBundle] = d.touch("evidence")
}
final class FakeAudits extends RuntimeAuditStore {
  def put(envelope: RuntimeAuditEnvelope) = StorageResult.Rejected("unused")
  def get(queryId: String) = StorageResult.Rejected("unused")
}
final class FakeLinks(d: Dependencies) extends EntityLinkCache {
  def putLink(link: EntityLink) = StorageResult.Rejected("unused")
  def lookupByNormalizedName(name: String): StorageResult[Vector[EntityLink]] = d.touch("links")
  def lookupByExternalId(namespace: String, id: String) = StorageResult.Rejected("unused")
}
final class FakeObjects extends ObjectStore {
  def put(key: String, bytes: Vector[Byte], contentType: String, metadata: Map[String, String]) =
    StorageResult.Rejected("unused")
  def get(key: String) = StorageResult.Rejected("unused")
  def head(key: String) = StorageResult.Rejected("unused")
}
final class FakeQueue(d: Dependencies) extends EmbeddingWorkQueue {
  def enqueue(items: Vector[EmbeddingWorkItem]) = StorageResult.Rejected("unused")
  def receive(maxItems: Int): StorageResult[Vector[EmbeddingQueueMessage]] =
    StorageResult.Found(Vector.empty)
  def acknowledge(receipt: String) = StorageResult.Rejected("unused")
  def backlog: StorageResult[Long] = d.touch("queue") match {
    case StorageResult.Missing => StorageResult.Found(0L)
    case other                 => other
  }
}
final class FakeRegistry(d: Dependencies) extends ArtifactRegistry {
  def register(artifactId: String, version: String, uri: String, hash: String) =
    StorageResult.Rejected("unused")
  def latest(artifactId: String) = StorageResult.Rejected("unused")
  def get(artifactId: String, version: String): StorageResult[ArtifactRecord] = d.touch("registry")
}
final class FakeLedger(d: Dependencies) extends RunLedger {
  def startRun(runId: String) = StorageResult.Rejected("unused")
  def recordStage(runId: String, stageKey: String) = StorageResult.Rejected("unused")
  def recordFailure(runId: String, stageKey: String, retryCount: Int, reasonCode: String) =
    StorageResult.Rejected("unused")
  def completeStage(runId: String, stageKey: String) = StorageResult.Rejected("unused")
  def completeRun(runId: String) = StorageResult.Rejected("unused")
  def getRun(runId: String): StorageResult[RunRecord] = d.touch("ledger")
}
final class RecordingLlm extends LlmClient {
  val requests = new java.util.concurrent.ConcurrentLinkedQueue[StructuredLlmRequest]()
  def complete(request: StructuredLlmRequest): LlmResult = {
    requests.add(request); LlmResult.Failure("recorded-no-output")
  }
}

/** Produces the fakes above and records which roles were opened and closed. */
final class FakeFactory(val d: Dependencies = new Dependencies) extends AwsPortFactory {
  val opened = new java.util.concurrent.ConcurrentLinkedQueue[String]()
  val closed = new AtomicInteger
  val llm = new RecordingLlm
  val objects = new FakeObjects
  @volatile var refuse: Option[String] = None
  @volatile var explode = false
  @volatile var functionalSessions = false
  private def close(): Unit = { closed.incrementAndGet(); () }
  private def gate[A](role: String)(make: => A): Either[String, A] = {
    if (explode) throw new IllegalStateException("provider-detail-must-not-leak")
    opened.add(role)
    refuse.toLeft(make)
  }
  @volatile var graphProvider: Option[GraphReaderProvider] = None
  private val credentials =
    software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
      .create(software.amazon.awssdk.auth.credentials.AwsBasicCredentials.create("test", "test"))
  def graph(config: GraphRoleConfig) = graphProvider match {
    case None =>
      gate("graph-service")(new GraphPorts(new FakeReader(d), new FakeMetrics(d), () => close()))
    case Some(provider) =>
      // Same seam the real factory uses: the reader comes from the provider and is closed with it.
      gate("graph-service")(()).flatMap { _ =>
        provider
          .open(config.neptuneEndpoint, config.region, credentials, config.neptuneTimeoutMs)
          .map(o => new GraphPorts(o.reader, new FakeMetrics(d), () => { o.close(); close() }))
      }
  }
  def semantic(config: SemanticRoleConfig) = gate("semantic-service")(
    new SemanticPorts(new FakeEmbedder(d, config.embedding), new FakeVectors(d), () => close())
  )
  def query(config: QueryRoleConfig, runtime: RuntimeConfig) = gate("query-api")(
    new QueryPorts(
      if (functionalSessions) new FunctionalSessions(d) else new FakeSessions(d),
      new FakeEvidence(d),
      new FakeAudits,
      new FakeLinks(d),
      new FakeMetrics(d),
      objects,
      UnconfiguredRuntimeArtifacts,
      llm,
      () => close()
    )
  )
  def worker(config: WorkerRoleConfig) = gate("embedding-worker")(
    new WorkerPorts(
      new FakeQueue(d),
      new FakeQueue(d),
      new FakeSessions(d),
      objects,
      new FakeVectors(d),
      new FakeRegistry(d),
      new FakeLedger(d),
      new FakeEmbedder(d, config.embedding),
      () => close()
    )
  )
}

object AwsTestEnv {

  /** Polls until the condition equals the expectation or the bound passes. */
  def settle(expected: Boolean, timeoutMs: Long = 3000)(condition: => Boolean): Boolean = {
    val end = System.nanoTime() + timeoutMs * 1000000L
    var value = condition
    while (value != expected && System.nanoTime() < end) { Thread.sleep(10); value = condition }
    value == expected
  }
  val shortBreaker = Map("SCHOLARCHAIN_BREAKER_RESET_MS" -> "30")
  val apiKey = "synthetic-aws-api-key"
  val internalToken = "synthetic-aws-internal-token"
  val profile = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  val foundation = "anthropic.claude-haiku-4-5-20251001-v1:0"
  val common: Map[String, String] = Map(
    "SCHOLARCHAIN_SERVICE_MODE" -> "aws",
    "SCHOLARCHAIN_API_KEY_SHA256" -> Auth.sha256(apiKey),
    "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> Auth.sha256(internalToken),
    "SCHOLARCHAIN_HTTP_HOST" -> "127.0.0.1",
    "SCHOLARCHAIN_HTTP_PORT" -> "0",
    "AWS_REGION" -> "us-east-2",
    "SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER" -> "sc-RunLedger",
    "SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE" -> "sc-EntityLinkCache",
    "SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION" -> "sc-QuerySession",
    "SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE" -> "sc-EvidenceBundle",
    "SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY" -> "sc-ArtifactRegistry",
    "SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE" -> "sc-ResearcherMetricCache",
    "SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX" -> "by-idempotency-key"
  )
  private val embedding = Map(
    "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL" -> "amazon.titan-embed-text-v2:0",
    "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION" -> "configured-version-v1",
    "SCHOLARCHAIN_EMBEDDING_DIMENSION" -> "256"
  )
  val graph: Map[String, String] = common ++ Map(
    "SCHOLARCHAIN_STORAGE_GRAPH_BUCKET" -> "sc-123456789012-graph",
    "SCHOLARCHAIN_NEPTUNE_ENDPOINT" -> "https://sc-reader.cluster-ro-x.us-east-2.neptune.amazonaws.com:8182",
    "SCHOLARCHAIN_GRAPH_CURSOR_KEY" -> "synthetic-cursor-key-0123456789"
  )
  val semantic: Map[String, String] = common ++ embedding ++ Map(
    "SCHOLARCHAIN_STORAGE_RAG_BUCKET" -> "sc-123456789012-rag",
    "SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET" -> "sc-123456789012-vectors",
    "SCHOLARCHAIN_SEMANTIC_INDEX" -> "researcher-profile-v1"
  )
  val worker: Map[String, String] = semantic ++ Map(
    "SCHOLARCHAIN_SQS_QUEUE_URL" -> "https://sqs.us-east-2.amazonaws.com/123456789012/sc-embedding",
    "SCHOLARCHAIN_SQS_DLQ_URL" -> "https://sqs.us-east-2.amazonaws.com/123456789012/sc-embedding-dlq",
    "SCHOLARCHAIN_EMBEDDING_TEXT_PREFIX" -> "embedding-text"
  )
  def query(graphBase: String, semanticBase: String): Map[String, String] =
    common ++ embedding ++ Map(
      "SCHOLARCHAIN_STORAGE_RAG_BUCKET" -> "sc-123456789012-rag",
      "SCHOLARCHAIN_GRAPH_BASE_URI" -> graphBase,
      "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> semanticBase,
      "SCHOLARCHAIN_INTERNAL_TOKEN" -> internalToken,
      "SCHOLARCHAIN_MODELS_SYNTHESIS_MODEL" -> profile,
      "SCHOLARCHAIN_SYNTHESIS_MODEL_VERSION" -> foundation,
      "SCHOLARCHAIN_PROMPTS_DIR" -> promptsDirectory.toString
    )
  def forRole(role: String): Map[String, String] = role match {
    case "graph-service"    => graph
    case "semantic-service" => semantic
    case "embedding-worker" => worker
    case _ =>
      query("http://graph-service.sc.internal:8080", "http://semantic-service.sc.internal:8080")
  }
  val promptsDirectory: Path = Iterator
    .iterate(Path.of("").toAbsolutePath)(_.getParent)
    .takeWhile(_ != null)
    .map(_.resolve("prompts"))
    .find(Files.isDirectory(_))
    .get
  def service(env: Map[String, String]): ServiceConfig =
    ServiceConfig.fromEnvironment(env).toOption.get
  def parse(role: String, env: Map[String, String]): Either[String, AwsRoleConfig] =
    AwsServiceConfig.fromEnvironment(role, env, service(env))
}

/** Minimal HTTP caller for started test services. */
object Http {
  private val client = HttpClient.newHttpClient()
  def get(port: Int, path: String, headers: Map[String, String] = Map.empty): (Int, String) = {
    val b = HttpRequest.newBuilder(URI.create(s"http://127.0.0.1:$port$path"))
    headers.foreach((k, v) => b.header(k, v))
    val r = client.send(b.GET().build(), HttpResponse.BodyHandlers.ofString())
    (r.statusCode(), r.body())
  }
  def post(port: Int, path: String, body: String, headers: Map[String, String]): (Int, String) = {
    val b = HttpRequest.newBuilder(URI.create(s"http://127.0.0.1:$port$path"))
    headers.foreach((k, v) => b.header(k, v))
    val r = client.send(
      b.POST(HttpRequest.BodyPublishers.ofString(body)).build(),
      HttpResponse.BodyHandlers.ofString()
    )
    (r.statusCode(), r.body())
  }
}
