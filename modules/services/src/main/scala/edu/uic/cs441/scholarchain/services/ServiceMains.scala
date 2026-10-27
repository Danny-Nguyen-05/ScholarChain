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
object ServiceBootstrap {

  /** Return an exit code for invalid configuration so packaging tests can check refusal without
    * terminating their test JVM. Production mains apply that exit code via System.exit.
    */
  def start(role: String): Int = try {
    ServiceConfig.fromEnvironment(sys.env) match {
      case Left(code) => System.err.println(code); 2
      case Right(config) =>
        val mode = sys.env.getOrElse("SCHOLARCHAIN_SERVICE_MODE", "unconfigured")
        if (!Set("unconfigured", "offline-synthetic")(mode)) {
          System.err.println("unsupported-service-mode"); return 2
        }
        val validMode = mode == "offline-synthetic"
        val workerConfig = BootstrapConfig.worker(sys.env)
        val composition = new OfflineComposition(config)
        // In explicit offline mode query-api can call independently running graph/semantic
        // artifacts through real HTTP clients. Raw runtime token is required only for those calls.
        val graphUri = sys.env.get("SCHOLARCHAIN_GRAPH_BASE_URI")
        val semanticUri = sys.env.get("SCHOLARCHAIN_SEMANTIC_BASE_URI")
        val configuredRemote = role == "query-api" && (graphUri.nonEmpty || semanticUri.nonEmpty)
        val bundle = if (configuredRemote) {
          if (graphUri.isEmpty || semanticUri.isEmpty) {
            composition.queries.close(); composition.extended.close(); return 2
          }
          val token =
            sys.env.getOrElse("SCHOLARCHAIN_INTERNAL_TOKEN", throw new IllegalArgumentException)
          if (Auth.sha256(token) != config.internalTokenSha256) throw new IllegalArgumentException
          val graph = new RemoteGraphApi(
            new RemoteService(URI.create(graphUri.get), token, config, composition.metrics, "graph")
          )
          val semantic = new RemoteSemanticApi(
            new RemoteService(
              URI.create(semanticUri.get),
              token,
              config,
              composition.metrics,
              "semantic"
            )
          )
          val remoteComposition =
            new OfflineComposition(config, Some(graph), Some(semantic), Some(composition.metrics))
          composition.queries.close(); composition.extended.close()
          remoteComposition
        } else composition
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
          extended = if (validMode) Some(bundle.extended) else None
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
        Runtime.getRuntime.addShutdownHook(new Thread(() => {
          worker.foreach((w, t) => {
            w.close(); t.interrupt(); t.join(config.downstreamTimeoutMs)
          }); server.close()
        }))
        0
    }
  } catch { case NonFatal(_) => System.err.println("invalid-service-configuration"); 2 }
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
