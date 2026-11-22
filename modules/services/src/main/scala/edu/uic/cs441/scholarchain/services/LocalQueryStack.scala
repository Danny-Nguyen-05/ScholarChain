package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.RuntimeConfig
import edu.uic.cs441.scholarchain.storage.{
  IncludeList,
  LocalExportError,
  LocalExportOptions,
  LocalExportStores,
  RuntimeArtifactScope
}
import java.net.URI
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.file.{Files, Path}
import java.security.SecureRandom
import java.time.Duration
import scala.util.control.NonFatal

/** Three started roles (semantic-service, graph-service, query-api) of one local query stack, all
  * bound to loopback in this JVM. `port` is the query-api port; the peer roles listen on ephemeral
  * loopback ports known only to the query role. Closing stops the query role first.
  */
final class RunningLocalStack private[services] (
    val port: Int,
    val graphPort: Int,
    val semanticPort: Int,
    val retrievalMode: String,
    val settings: LocalSettings,
    val llmConfigured: Boolean,
    val factory: LocalPortFactory,
    roles: Vector[RunningService]
) extends AutoCloseable {
  def close(): Unit = roles.reverse.foreach(r =>
    try r.close()
    catch { case NonFatal(_) => () }
  )
}

/** The effective, non-secret runtime values the stack runs with (parsed once, before any load). */
final case class LocalSettings(runtime: RuntimeConfig, service: ServiceConfig) {
  def modelId: String = runtime.model.modelId
  def deadlines: String =
    "planner:" + runtime.deadlines.plannerMs + ",synthesis:" + runtime.deadlines.synthesisMs +
      ",runtimeSync:" + runtime.operations.synchronousDeadlineMs +
      ",serviceSync:" + service.synchronousDeadlineMs + ",workflow:" + service.workflowTimeoutMs
}

/** Composition of a local, offline query stack over a loaded Phase 6 export. It starts the same
  * three roles as aws mode, through the same `ServiceBootstrap.launch`, with `LocalPortFactory` as
  * the port factory, so the workflow, routes, authentication, jobs and evidence reads are the real
  * ones. Nothing here creates an AWS SDK client; the AWS-shaped configuration values the shared
  * config reader insists on are fixed local placeholders (`local-unused-*`, never used).
  *
  * Secrets: the public API key arrives only as its SHA-256 (`SCHOLARCHAIN_API_KEY_SHA256`); the
  * internal token is random per run and exists only in memory; the Anthropic key
  * (`SCHOLARCHAIN_ANTHROPIC_API_KEY`) goes only to the provider seam. No value is printed.
  */
object LocalQueryStack {
  val apiKeyHashVariable = "SCHOLARCHAIN_API_KEY_SHA256"
  val anthropicKeyVariable = "SCHOLARCHAIN_ANTHROPIC_API_KEY"
  val hostVariable = "SCHOLARCHAIN_HTTP_HOST"
  val portVariable = "SCHOLARCHAIN_HTTP_PORT"
  val retrievalModeVariable = "SCHOLARCHAIN_RUNTIME_RETRIEVAL_MODE"

  /** The one accepted host. The peer URIs and the readiness probe are built for IPv4 loopback, and
    * no name is resolved to decide (`localhost` may resolve to `::1`).
    */
  val loopbackHosts: Set[String] = Set("127.0.0.1")

  private val region = "us-local-1"
  private val reserved = Set(
    "SCHOLARCHAIN_APPLICATION_REGION",
    anthropicKeyVariable,
    "SCHOLARCHAIN_VOYAGE_API_KEY",
    "SCHOLARCHAIN_INTERNAL_TOKEN",
    "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256"
  )

  /** Checks that need no export. Run before the (slow) load so a bad launch fails at once. It
    * validates the host, key hash, key shape, port and, by parsing the same configuration the roles
    * will parse (with placeholder token, ports and run), the retrieval mode, every deadline and
    * every service knob. A refusal names only a variable or a closed code.
    */
  def preflight(env: Map[String, String]): Either[String, LocalSettings] = {
    val host = env.getOrElse(hostVariable, "127.0.0.1")
    val hash = env.getOrElse(apiKeyHashVariable, "")
    if (!loopbackHosts(host)) Left("non-loopback-host-refused:" + hostVariable)
    else if (!hash.matches("[0-9a-f]{64}") || hash == Auth.sha256(""))
      Left("missing-or-invalid-configuration:" + apiKeyHashVariable)
    else if (!anthropicKey(env).isRight) Left("invalid-configuration:" + anthropicKeyVariable)
    else
      env.get(portVariable) match {
        case Some(p) if !p.matches("[0-9]{1,5}") || p.toInt > 65535 =>
          Left("invalid-configuration:" + portVariable)
        case _ => settings(env)
      }
  }

  private def settings(env: Map[String, String]): Either[String, LocalSettings] =
    try {
      val token = "preflight-placeholder-token"
      val query = sharedEnv(env, Auth.sha256(token)) ++ queryEnv(token, "run:preflight", 1, 1, env)
      for {
        service <- ServiceConfig.fromEnvironment(query)
        _ <- RateLimitSettings.fromEnvironment(query)
        _ <- EmbeddingCacheSettings.fromEnvironment(query)
        role <- AwsServiceConfig.fromEnvironment("query-api", query, service)
        runtime <- AwsComposition.runtimeConfig(role.asInstanceOf[QueryRoleConfig])
      } yield {
        BootstrapConfig.graph(query); BootstrapConfig.worker(query)
        LocalSettings(runtime, service)
      }
    } catch { case NonFatal(_) => Left("invalid-configuration:SCHOLARCHAIN_*") }

  private def effectiveMode(env: Map[String, String]): String =
    env.getOrElse(retrievalModeVariable, "graph")

  /** The environment every role parses: user knobs (never secrets or the region pin), then the
    * fixed local values, which win.
    */
  private def sharedEnv(
      env: Map[String, String],
      internalTokenSha256: String
  ): Map[String, String] =
    env.filter((k, _) => k.startsWith("SCHOLARCHAIN_") && !reserved(k)) ++ Map(
      "SCHOLARCHAIN_SERVICE_MODE" -> "aws",
      apiKeyHashVariable -> env(apiKeyHashVariable),
      "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> internalTokenSha256,
      hostVariable -> env.getOrElse(hostVariable, "127.0.0.1"),
      "AWS_REGION" -> region,
      "SCHOLARCHAIN_DYNAMODB_TABLE_RUN_LEDGER" -> "local-unused-run-ledger",
      "SCHOLARCHAIN_DYNAMODB_TABLE_ENTITY_LINK_CACHE" -> "local-unused-entity-links",
      "SCHOLARCHAIN_DYNAMODB_TABLE_QUERY_SESSION" -> "local-unused-query-session",
      "SCHOLARCHAIN_DYNAMODB_TABLE_EVIDENCE_BUNDLE" -> "local-unused-evidence-bundle",
      "SCHOLARCHAIN_DYNAMODB_TABLE_ARTIFACT_REGISTRY" -> "local-unused-artifact-registry",
      "SCHOLARCHAIN_DYNAMODB_TABLE_RESEARCHER_METRIC_CACHE" -> "local-unused-metric-cache",
      "SCHOLARCHAIN_DYNAMODB_QUERY_SESSION_INDEX" -> "local-unused-idempotency-index",
      "SCHOLARCHAIN_EMBEDDING_PROVIDER" -> "bedrock",
      "SCHOLARCHAIN_MODELS_EMBEDDING_MODEL" -> "amazon.titan-embed-text-v2:0",
      "SCHOLARCHAIN_EMBEDDING_MODEL_VERSION" -> "local-semantic-not-served",
      "SCHOLARCHAIN_EMBEDDING_DIMENSION" -> "256"
    )

  private def queryEnv(
      token: String,
      run: String,
      graphPort: Int,
      semanticPort: Int,
      env: Map[String, String]
  ): Map[String, String] = Map(
    "SCHOLARCHAIN_STORAGE_RAG_BUCKET" -> "local-unused-rag",
    "SCHOLARCHAIN_GRAPH_BASE_URI" -> s"http://127.0.0.1:$graphPort",
    "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> s"http://127.0.0.1:$semanticPort",
    "SCHOLARCHAIN_INTERNAL_TOKEN" -> token,
    // The shared config reader insists on a key for the Anthropic provider. This placeholder never
    // reaches a client: the factory ignores the configured key.
    anthropicKeyVariable -> "local-placeholder-unused",
    "SCHOLARCHAIN_RUNTIME_DATASET_SNAPSHOT" -> ("local-export:" + run),
    retrievalModeVariable -> effectiveMode(env)
  )

  private def anthropicKey(env: Map[String, String]): Either[String, Option[Secret]] =
    env.get(anthropicKeyVariable).map(_.trim) match {
      // Unset means no key (queries answer 503). A variable that is set but blank is a mistake
      // (for example a failed no-echo read) and is refused rather than starting without a model.
      case None => Right(None)
      case Some(v) if v.length >= 8 && v.length <= 512 && v.forall(c => c > ' ' && c < '\u007f') =>
        Right(Some(new Secret(v)))
      case Some(_) => Left("invalid-configuration:" + anthropicKeyVariable)
    }

  private def randomHex(bytes: Int): String = {
    val b = new Array[Byte](bytes); new SecureRandom().nextBytes(b)
    b.map(x => f"${x & 255}%02x").mkString
  }

  /** Starts the three roles over `stores`. Returns the stack once the query role's own `/readyz`
    * answers 200 (it checks both peers), or a refusal code after closing what was started.
    * `providers` is the seam for the Anthropic client; the default builds the real one.
    */
  def start(
      stores: LocalExportStores,
      env: Map[String, String],
      providers: ProviderClients = new RagProviderClients(),
      err: String => Unit = s => System.err.println(s)
  ): Either[Int, RunningLocalStack] = {
    def refuse(code: String): Left[Int, RunningLocalStack] = { err(code); Left(2) }
    preflight(env) match {
      case Left(code) => refuse(code)
      case Right(effective) =>
        val key = anthropicKey(env).toOption.flatten
        val token = randomHex(32)
        val mode = effectiveMode(env)
        val factory = new LocalPortFactory(stores, key, providers)
        val shared = sharedEnv(env, Auth.sha256(token))
        val started = Vector.newBuilder[RunningService]
        def abort(code: String): Left[Int, RunningLocalStack] = {
          started
            .result()
            .reverse
            .foreach(r =>
              try r.close()
              catch { case NonFatal(_) => () }
            )
          refuse(code)
        }
        def launch(role: String, extra: Map[String, String]): Either[Int, RunningService] =
          try ServiceBootstrap.launch(role, shared ++ extra, factory)
          catch { case NonFatal(_) => err("invalid-local-composition"); Left(2) }
        val run = stores.runId
        val semantic = launch(
          "semantic-service",
          Map(
            portVariable -> "0",
            "SCHOLARCHAIN_STORAGE_RAG_BUCKET" -> "local-unused-rag",
            "SCHOLARCHAIN_S3_VECTORS_VECTOR_BUCKET" -> "local-unused-vectors",
            "SCHOLARCHAIN_SEMANTIC_INDEX" -> "researcher-profile-v1"
          )
        )
        semantic match {
          case Left(_) => Left(2)
          case Right(semanticRole) =>
            started += semanticRole
            val graph = launch(
              "graph-service",
              Map(
                portVariable -> "0",
                "SCHOLARCHAIN_STORAGE_GRAPH_BUCKET" -> "local-unused-graph",
                "SCHOLARCHAIN_NEPTUNE_ENDPOINT" -> "https://local-unused.invalid:8182",
                "SCHOLARCHAIN_GRAPH_CURSOR_KEY" -> randomHex(16),
                "SCHOLARCHAIN_GRAPH_SNAPSHOT_ID" -> ("local-" + run)
              )
            )
            graph match {
              case Left(_) => abort("local-stack-start-failed:graph-service")
              case Right(graphRole) =>
                started += graphRole
                val query = launch(
                  "query-api",
                  queryEnv(token, run, graphRole.port, semanticRole.port, env)
                )
                query match {
                  case Left(_) => abort("local-stack-start-failed:query-api")
                  case Right(queryRole) =>
                    started += queryRole
                    val stack = new RunningLocalStack(
                      queryRole.port,
                      graphRole.port,
                      semanticRole.port,
                      mode,
                      effective,
                      factory.llmConfigured,
                      factory,
                      started.result()
                    )
                    if (awaitReady(queryRole.port)) Right(stack)
                    else {
                      stack.close(); refuse("local-stack-not-ready")
                    }
                }
            }
        }
    }
  }

  private def awaitReady(port: Int, timeoutMs: Long = 15000): Boolean = {
    val client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build()
    val request = HttpRequest
      .newBuilder(URI.create(s"http://127.0.0.1:$port/readyz"))
      .timeout(Duration.ofSeconds(5))
      .GET()
      .build()
    val end = System.nanoTime() + timeoutMs * 1000000L
    var ok = false
    while (!ok && System.nanoTime() < end) {
      ok =
        try client.send(request, HttpResponse.BodyHandlers.discarding()).statusCode() == 200
        catch { case NonFatal(_) => false }
      if (!ok) Thread.sleep(100)
    }
    ok
  }
}

/** Launcher for the local query stack. Loads one Phase 6 export (path from `--export-dir` or
  * `SCHOLARCHAIN_LOCAL_EXPORT_DIR`; there is no default), starts the three roles bound to loopback,
  * and prints one ready line naming the port, retrieval mode, model status and export provenance.
  * It prints no environment value.
  */
object LocalQueryStackMain {
  val exportDirVariable = "SCHOLARCHAIN_LOCAL_EXPORT_DIR"
  val includeListVariable = "SCHOLARCHAIN_LOCAL_INCLUDE_LIST"
  val usage =
    "usage: LocalQueryStackMain [--export-dir DIR] [--include-list FILE] [--port N] [--scratch-dir DIR] [--no-verify]"

  private final case class Args(
      exportDir: Option[String],
      includeList: Option[String],
      port: Option[String],
      scratch: Option[String],
      verify: Boolean
  )
  private def parse(args: Seq[String]): Option[Args] = {
    var out = Args(None, None, None, None, true)
    var rest = args.toList
    while (rest.nonEmpty) rest match {
      case "--export-dir" :: v :: tail   => out = out.copy(exportDir = Some(v)); rest = tail
      case "--include-list" :: v :: tail => out = out.copy(includeList = Some(v)); rest = tail
      case "--port" :: v :: tail         => out = out.copy(port = Some(v)); rest = tail
      case "--scratch-dir" :: v :: tail  => out = out.copy(scratch = Some(v)); rest = tail
      case "--no-verify" :: tail         => out = out.copy(verify = false); rest = tail
      case _                             => return None
    }
    Some(out)
  }

  /** The one ready line: port, retrieval mode, model status and export provenance. No value of the
    * environment appears in it.
    */
  def readyLine(stores: LocalExportStores, stack: RunningLocalStack): String =
    "local-query-stack ready port=" + stack.port +
      " retrieval=" + stack.retrievalMode +
      " model=" + stack.settings.modelId +
      " deadlinesMs=" + stack.settings.deadlines +
      " llm=" + (if (stack.llmConfigured) "anthropic" else "unconfigured") +
      " runId=" + stores.runId +
      " artifactScope=" + stores.provenance.artifactScope +
      " artifactPointerSha256=" + stores.artifactPointer.sha256 +
      " hashesVerified=" + stores.provenance.tables.forall(_.hashVerified) +
      " loadMillis=" + stores.loadMillis

  /** Runs the launch and returns the started stack or an exit code. Exit 2 is a configuration
    * refusal, 3 a refused export. Messages carry only closed codes, names and counts.
    */
  def run(
      args: Seq[String],
      env: Map[String, String],
      out: String => Unit = s => println(s),
      err: String => Unit = s => System.err.println(s),
      providers: ProviderClients = new RagProviderClients()
  ): Either[Int, RunningLocalStack] = parse(args) match {
    case None => err(usage); Left(2)
    case Some(a) =>
      val effective = a.port.fold(env)(p => env.updated(LocalQueryStack.portVariable, p))
      LocalQueryStack.preflight(effective) match {
        case Left(code) => err(code); Left(2)
        case Right(_) =>
          a.exportDir.orElse(env.get(exportDirVariable)).filter(_.trim.nonEmpty) match {
            case None      => err("missing-configuration:" + exportDirVariable); Left(2)
            case Some(dir) =>
              // With an include list the runtime artifact is the bounded subset (as deployed on
              // AWS); without one it is the whole export.
              val scope: Either[String, RuntimeArtifactScope] =
                a.includeList.orElse(env.get(includeListVariable)).filter(_.trim.nonEmpty) match {
                  case None => Right(RuntimeArtifactScope.WholeExport)
                  case Some(file) =>
                    try
                      IncludeList
                        .parse(Files.readAllBytes(Path.of(file)))
                        .map(RuntimeArtifactScope.IncludeIds(_))
                    catch { case NonFatal(_) => Left("include-list-unreadable") }
                }
              val options = LocalExportOptions(
                artifactScope = scope.getOrElse(RuntimeArtifactScope.WholeExport),
                verifySourceHashes = a.verify,
                scratchDirectory = a.scratch.map(Path.of(_)),
                progress = line => out("local-query-stack " + line)
              )
              if (scope.isLeft) {
                err("include-list-refused:" + scope.left.getOrElse("")); Left(3)
              } else
                LocalExportStores.load(Path.of(dir), options) match {
                  case Left(LocalExportError(code, part, _)) =>
                    err("local-export-refused:" + code + ":" + part); Left(3)
                  case Right(stores) =>
                    LocalQueryStack.start(stores, effective, providers, err).map { stack =>
                      out(readyLine(stores, stack))
                      stack
                    }
                }
          }
      }
  }

  def main(args: Array[String]): Unit = run(args.toSeq, sys.env) match {
    case Left(code) => System.exit(code)
    case Right(stack) =>
      Runtime.getRuntime.addShutdownHook(new Thread(() => stack.close()))
      new java.util.concurrent.CountDownLatch(1).await()
  }
}
