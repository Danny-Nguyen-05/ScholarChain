package edu.uic.cs441.scholarchain.services

import java.net.URI
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.rag.DeterministicHashedEmbeddingClient
import edu.uic.cs441.scholarchain.storage.*
import scala.util.control.NonFatal

object BootstrapConfig {
  def graph(env: Map[String, String]): GraphApiConfig = {
    def int(k: String, d: Int) = env.get("SCHOLARCHAIN_GRAPH_" + k).map(_.toInt).getOrElse(d)
    GraphApiConfig(
      defaultDirection = env.getOrElse("SCHOLARCHAIN_GRAPH_DIRECTION", "both"),
      defaultDepth = int("DEFAULT_DEPTH", 1),
      maxDepth = int("MAX_DEPTH", 3),
      defaultLimit = int("DEFAULT_LIMIT", 50),
      maxLimit = int("MAX_LIMIT", 200),
      timeoutMs = int("TIMEOUT_MS", 5000).toLong,
      defaultWindow = env.getOrElse("SCHOLARCHAIN_GRAPH_DEFAULT_WINDOW", "all-years"),
      maxScannedEdges = int("MAX_SCANNED_EDGES", 10000),
      maxVisitedNodes = int("MAX_VISITED_NODES", 2000),
      maxCursorChars = int("MAX_CURSOR_CHARS", 4096),
      cursorKey =
        env.getOrElse("SCHOLARCHAIN_GRAPH_CURSOR_KEY", java.util.UUID.randomUUID().toString)
    )
  }
  def worker(env: Map[String, String]): WorkerConfig = WorkerConfig(
    env.get("SCHOLARCHAIN_WORKER_MAX_ATTEMPTS").map(_.toInt).getOrElse(3),
    env.get("SCHOLARCHAIN_WORKER_BATCH_SIZE").map(_.toInt).getOrElse(1),
    env.get("SCHOLARCHAIN_WORKER_POLL_MS").map(_.toLong).getOrElse(1000L)
  )
}

/** A started role. close() stops the worker thread, the HTTP server and then owned resources. */
final class RunningService private[services] (
    server: ApiServer.RunningServer,
    worker: Option[(EmbeddingWorker, Thread)],
    timeoutMs: Long,
    owned: Vector[AutoCloseable]
) extends AutoCloseable {
  def port: Int = server.port
  def close(): Unit = {
    worker.foreach((w, t) => {
      w.close(); t.interrupt(); t.join(timeoutMs)
    })
    server.close()
    owned.foreach(c =>
      try c.close()
      catch { case NonFatal(_) => () }
    )
  }
}
object ServiceBootstrap {
  val modes: Set[String] = Set("unconfigured", "offline-synthetic", "aws")

  /** Return an exit code for invalid configuration so packaging tests can check refusal without
    * terminating their test JVM. Production mains apply that exit code via System.exit.
    */
  def start(role: String): Int =
    launch(role, sys.env, new AwsSdkPortFactory(providers = new RagProviderClients())) match {
      case Left(code) => code
      case Right(running) =>
        Runtime.getRuntime.addShutdownHook(new Thread(() => running.close()))
        0
    }

  /** Starts a role from an explicit environment and, in aws mode, an injected port factory. Exit
    * code 2 is the single refusal path; messages name at most an environment variable, never a
    * value, a provider message or a stack trace.
    */
  def launch(
      role: String,
      env: Map[String, String],
      factory: AwsPortFactory
  ): Either[Int, RunningService] = try {
    ServiceConfig.fromEnvironment(env) match {
      case Left(code) => System.err.println(code); Left(2)
      case Right(config) =>
        val mode = env.getOrElse("SCHOLARCHAIN_SERVICE_MODE", "unconfigured")
        if (!modes(mode)) {
          System.err.println("unsupported-service-mode"); return Left(2)
        }
        RateLimitSettings.fromEnvironment(env) match {
          case Left(code)  => System.err.println(code); Left(2)
          case Right(rate) =>
            // One limiter per process: the public semantic route's per-key token buckets.
            val route = new PublicSemanticRoute(
              PublicSemanticLimits(),
              new TokenBucketRateLimiter(rate)
            )
            if (mode == "aws") launchAws(role, env, config, factory, route)
            else launchLocal(role, env, config, mode == "offline-synthetic", route)
        }
    }
  } catch { case NonFatal(_) => System.err.println("invalid-service-configuration"); Left(2) }

  private def launchAws(
      role: String,
      env: Map[String, String],
      config: ServiceConfig,
      factory: AwsPortFactory,
      route: PublicSemanticRoute
  ): Either[Int, RunningService] = {
    val refusal = (code: String) => { System.err.println(code); Left(2) }
    AwsServiceConfig.fromEnvironment(role, env, config) match {
      case Left(code) => refusal(code)
      case Right(aws) =>
        AwsComposition.build(config, aws, env, factory) match {
          case Left(code) => refusal(code)
          case Right(composition) =>
            val app = new ApiApplication(
              composition.queries,
              config,
              readiness = () => composition.ready,
              serviceRole = role,
              extended = composition.extended,
              semanticRoute = route
            )
            val server = ApiServer.start(app, config.host, config.port, config.maxRequestBytes)
            val worker = composition.worker.map { w =>
              val thread = ServiceThreads.daemon("embedding-worker").newThread(() => w.run());
              thread.start(); (w, thread)
            }
            Right(
              new RunningService(server, worker, config.downstreamTimeoutMs, Vector(composition))
            )
        }
    }
  }

  private def launchLocal(
      role: String,
      env: Map[String, String],
      config: ServiceConfig,
      validMode: Boolean,
      route: PublicSemanticRoute
  ): Either[Int, RunningService] = {
    val workerConfig = BootstrapConfig.worker(env)
    val cacheEntries = EmbeddingCacheSettings.fromEnvironment(env) match {
      case Left(code)  => System.err.println(code); return Left(2)
      case Right(size) => size
    }
    // In explicit offline mode query-api can call independently running graph/semantic
    // artifacts through real HTTP clients. Raw runtime token is required only for those calls.
    // The remote decision is made before any composition is built, so no discarded composition
    // registers an embedding cache on the shared metrics.
    val graphUri = env.get("SCHOLARCHAIN_GRAPH_BASE_URI")
    val semanticUri = env.get("SCHOLARCHAIN_SEMANTIC_BASE_URI")
    val configuredRemote = role == "query-api" && (graphUri.nonEmpty || semanticUri.nonEmpty)
    val metrics = new ServiceMetrics
    val bundle = if (configuredRemote) {
      if (graphUri.isEmpty || semanticUri.isEmpty) return Left(2)
      val token =
        env.getOrElse("SCHOLARCHAIN_INTERNAL_TOKEN", throw new IllegalArgumentException)
      if (Auth.sha256(token) != config.internalTokenSha256) throw new IllegalArgumentException
      val graph = new RemoteGraphApi(
        new RemoteService(URI.create(graphUri.get), token, config, metrics, "graph")
      )
      val semantic = new RemoteSemanticApi(
        new RemoteService(URI.create(semanticUri.get), token, config, metrics, "semantic")
      )
      new OfflineComposition(config, Some(graph), Some(semantic), Some(metrics), cacheEntries)
    } else new OfflineComposition(config, None, None, Some(metrics), cacheEntries)
    val workflow =
      if (validMode) bundle.workflow
      else
        new QueryWorkflow {
          def run(
              r: QueryRequest,
              c: RequestContext,
              s: String => Unit
          ): Either[ApiError, WorkflowOutput] = Left(ApiError.unavailable)
        }
    val queries =
      if (validMode) bundle.queries
      else new QueryService(bundle.sessions, workflow, config, bundle.metrics)
    val app = new ApiApplication(
      queries,
      config,
      readiness = () => validMode && bundle.ready,
      serviceRole = role,
      extended = if (validMode) Some(bundle.extended) else None,
      semanticRoute = route
    )
    val server = ApiServer.start(app, config.host, config.port, config.maxRequestBytes)
    val worker = if (role == "embedding-worker" && validMode) {
      val embedder = new DeterministicHashedEmbeddingClient(
        EmbeddingModel("synthetic-offline-services", "v1", 8)
      )
      val vectors = new InMemoryVectorStore
      val runner = new EmbeddingManifestRunner(
        EmbeddingIngestConfig("synthetic-offline", "text", 8),
        new InMemoryObjectStore,
        vectors,
        new InMemoryArtifactRegistry,
        new InMemoryRunLedger,
        embedder
      )
      val w = new EmbeddingWorker(
        new InMemoryEmbeddingWorkQueue,
        new InMemoryEmbeddingWorkQueue,
        new InMemoryQuerySessionStore,
        new ManifestEmbeddingProcessor(runner),
        workerConfig
      )
      val thread = ServiceThreads.daemon("embedding-worker").newThread(() => w.run());
      thread.start(); Some((w, thread))
    } else None
    Right(new RunningService(server, worker, config.downstreamTimeoutMs, Vector.empty))
  }
  def main(role: String): Unit = { val exit = start(role); if (exit != 0) System.exit(exit) }
}
object QueryApiMain { def main(args: Array[String]): Unit = ServiceBootstrap.main("query-api") }
object GraphServiceMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.main("graph-service")
}
object SemanticServiceMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.main("semantic-service")
}
object EmbeddingWorkerMain {
  def main(args: Array[String]): Unit = ServiceBootstrap.main("embedding-worker")
}
