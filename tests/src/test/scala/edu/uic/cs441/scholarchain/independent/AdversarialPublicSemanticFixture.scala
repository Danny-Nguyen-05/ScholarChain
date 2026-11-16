package edu.uic.cs441.scholarchain.independent

import com.sun.net.httpserver.{HttpExchange, HttpServer}
import edu.uic.cs441.scholarchain.core.RuntimeConfig
import edu.uic.cs441.scholarchain.services.*
import java.io.{ByteArrayInputStream, ByteArrayOutputStream, OutputStream, PrintStream}
import java.net.{InetSocketAddress, URI}
import java.net.http.{HttpClient, HttpRequest, HttpResponse}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.MessageDigest
import java.time.Duration
import java.util.concurrent.{ConcurrentLinkedQueue, Executors}
import java.util.concurrent.atomic.AtomicInteger
import org.apache.logging.log4j.{Level, LogManager}
import org.apache.logging.log4j.core.{LogEvent, LoggerContext}
import org.apache.logging.log4j.core.appender.AbstractAppender
import org.apache.logging.log4j.core.config.{LoggerConfig, Property}
import org.apache.logging.log4j.core.layout.PatternLayout
import scala.jdk.CollectionConverters.*

/** Black-box fixture for the public `POST /v1/semantic/retrieve` route (P40-T). Everything here is
  * derived from the published contract (modules/services/README.md "Public semantic retrieval" and
  * the OpenAPI path), not from the route's implementation. All credentials are synthetic
  * placeholders, every service runs in `offline-synthetic` mode, and the only downstream is a local
  * stub HTTP server. No AWS, Anthropic or Voyage endpoint is contacted: the injected AWS port
  * factory refuses every call and counts it.
  */
private[independent] object AdversarialPublicSemanticFixture {
  val apiKey = "synthetic-p40t-public-api-key"
  val internalToken = "synthetic-p40t-internal-token"
  val Route = "/v1/semantic/retrieve"
  val InternalRoute = "/internal/v1/semantic/retrieve"
  val Trace = "trace-p40t-independent"

  /** Distinctive alphanumeric token placed in every question (and in stub bodies); it must never
    * appear in a log line, `/metrics` body, error body or response header.
    */
  val Sentinel = "zq7f3aP40Tqx"

  def sha256Hex(value: String): String =
    MessageDigest
      .getInstance("SHA-256")
      .digest(value.getBytes(UTF_8))
      .map(b => f"${b & 0xff}%02x")
      .mkString

  def baseEnv(extra: (String, String)*): Map[String, String] = Map(
    "SCHOLARCHAIN_API_KEY_SHA256" -> sha256Hex(apiKey),
    "SCHOLARCHAIN_INTERNAL_TOKEN_SHA256" -> sha256Hex(internalToken),
    "SCHOLARCHAIN_SERVICE_MODE" -> "offline-synthetic",
    "SCHOLARCHAIN_HTTP_HOST" -> "127.0.0.1",
    "SCHOLARCHAIN_HTTP_PORT" -> "0"
  ) ++ extra

  /** Query-api in offline-synthetic mode forwarding graph and semantic calls to `stub`. */
  def remoteEnv(stub: StubSemantic, extra: (String, String)*): Map[String, String] =
    baseEnv(
      "SCHOLARCHAIN_GRAPH_BASE_URI" -> stub.base,
      "SCHOLARCHAIN_SEMANTIC_BASE_URI" -> stub.base,
      "SCHOLARCHAIN_INTERNAL_TOKEN" -> internalToken,
      "SCHOLARCHAIN_DOWNSTREAM_MAX_ATTEMPTS" -> "1",
      "SCHOLARCHAIN_DOWNSTREAM_TIMEOUT_MS" -> "1000"
    ) ++ extra

  /** Offline mode must never construct an AWS port; any call is counted and refused. */
  final class RefusingAwsFactory extends AwsPortFactory {
    val calls = new AtomicInteger
    def graph(config: GraphRoleConfig): Either[String, GraphPorts] = refuse
    def semantic(config: SemanticRoleConfig): Either[String, SemanticPorts] = refuse
    def query(config: QueryRoleConfig, runtime: RuntimeConfig): Either[String, QueryPorts] =
      refuse
    def worker(config: WorkerRoleConfig): Either[String, WorkerPorts] = refuse
    private def refuse[A]: Either[String, A] = { calls.incrementAndGet(); Left("p40t-no-aws") }
  }

  def launch(role: String, env: Map[String, String]): Either[Int, RunningService] = {
    val factory = new RefusingAwsFactory
    val result = ServiceBootstrap.launch(role, env, factory)
    assert(factory.calls.get == 0, "offline-synthetic launch touched the AWS port factory")
    result
  }

  def withService[A](role: String, env: Map[String, String])(check: Int => A): A =
    launch(role, env) match {
      case Left(code) => throw new AssertionError(s"$role refused to start with exit $code")
      case Right(service) =>
        try check(service.port)
        finally service.close()
    }

  private val client = HttpClient
    .newBuilder()
    .version(HttpClient.Version.HTTP_1_1)
    .connectTimeout(Duration.ofSeconds(3))
    .build()

  def call(
      port: Int,
      path: String = Route,
      body: Option[String] = None,
      method: String = "POST",
      auth: Seq[String] = Seq("Bearer " + apiKey),
      headers: Seq[(String, String)] = Seq("Content-Type" -> "application/json"),
      chunked: Boolean = false,
      trace: String = Trace
  ): HttpResponse[String] = {
    val builder = HttpRequest
      .newBuilder(URI.create(s"http://127.0.0.1:$port$path"))
      .timeout(Duration.ofSeconds(15))
      .header("X-Trace-Id", trace)
    auth.foreach(value => builder.header("Authorization", value))
    headers.foreach((name, value) => builder.header(name, value))
    val publisher = body match {
      case None => HttpRequest.BodyPublishers.noBody()
      case Some(text) if chunked =>
        val bytes = text.getBytes(UTF_8)
        HttpRequest.BodyPublishers.ofInputStream(() => new ByteArrayInputStream(bytes))
      case Some(text) => HttpRequest.BodyPublishers.ofString(text, UTF_8)
    }
    builder.method(method, publisher)
    client.send(builder.build(), HttpResponse.BodyHandlers.ofString(UTF_8))
  }

  def post(port: Int, body: String, auth: Seq[String] = Seq("Bearer " + apiKey)) =
    call(port, body = Some(body), auth = auth)

  def get(port: Int, path: String, auth: Seq[String] = Seq("Bearer " + apiKey)) =
    call(port, path, method = "GET", auth = auth, headers = Seq.empty)

  def question(text: String, topK: Option[Int] = None): String = {
    val obj = ujson.Obj("question" -> text)
    topK.foreach(k => obj("topK") = k)
    obj.render()
  }

  /** Inserts JSON whitespace after the opening brace so the body is exactly `bytes` UTF-8 bytes. */
  def padTo(json: String, bytes: Int): String = {
    val size = json.getBytes(UTF_8).length
    require(json.startsWith("{") && size <= bytes, s"cannot pad $size to $bytes")
    "{" + " " * (bytes - size) + json.drop(1)
  }

  def header(response: HttpResponse[String], name: String): Option[String] = {
    val value = response.headers().firstValue(name)
    if (value.isPresent) Some(value.get) else None
  }

  /** Prometheus text: the value of the series with exactly these labels (any label order). */
  def metric(
      text: String,
      name: String,
      labels: Map[String, String] = Map.empty
  ): Option[Double] = {
    val line = raw"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{([^}]*)\})?\s+(\S+)$$".r
    val pair = raw"""([a-zA-Z_][a-zA-Z0-9_]*)="((?:[^"\\]|\\.)*)"""".r
    text.linesIterator
      .filterNot(_.startsWith("#"))
      .collect {
        case line(n, l, v) if n == name =>
          val parsed = Option(l).toVector
            .flatMap(pair.findAllMatchIn(_))
            .map(m => m.group(1) -> m.group(2))
            .toMap
          (parsed, v.toDouble)
      }
      .collectFirst { case (parsed, v) if parsed == labels => v }
  }

  def metricsText(port: Int): String = {
    val response = get(port, "/metrics")
    assert(response.statusCode() == 200, s"/metrics returned ${response.statusCode()}")
    response.body()
  }

  def routeCount(text: String, status: Int, route: String = Route): Double =
    metric(text, "api_route_requests_total", Map("route" -> route, "status" -> status.toString))
      .getOrElse(0.0)

  /** A local stand-in for semantic-service (and graph-service readiness). It records every call to
    * the internal semantic route and answers with the currently configured reply.
    */
  final class StubSemantic extends AutoCloseable {
    final case class Received(
        path: String,
        query: Option[String],
        headers: Map[String, Vector[String]],
        body: String
    ) { def json: ujson.Value = ujson.read(body) }
    final case class Reply(status: Int, body: String, delayMs: Long = 0)

    val received = new ConcurrentLinkedQueue[Received]
    @volatile var reply: Reply = Reply(200, StubSemantic.goodBody)
    private val server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    server.setExecutor(Executors.newCachedThreadPool())
    server.createContext(
      "/",
      (exchange: HttpExchange) => {
        val path = exchange.getRequestURI.getRawPath
        val body = new String(exchange.getRequestBody.readAllBytes(), UTF_8)
        val current =
          if (path == InternalRoute) {
            val headers = exchange.getRequestHeaders.asScala.toMap.map((k, v) =>
              k.toLowerCase -> v.asScala.toVector
            )
            received.add(Received(path, Option(exchange.getRequestURI.getRawQuery), headers, body))
            reply
          } else Reply(200, """{"status":"ready"}""")
        if (current.delayMs > 0) Thread.sleep(current.delayMs)
        val bytes = current.body.getBytes(UTF_8)
        exchange.getResponseHeaders.add("Content-Type", "application/json")
        try {
          exchange.sendResponseHeaders(current.status, if (bytes.isEmpty) -1 else bytes.length)
          if (bytes.nonEmpty) exchange.getResponseBody.write(bytes)
        } catch { case _: java.io.IOException => () }
        exchange.close()
      }
    )
    server.start()
    val port: Int = server.getAddress.getPort
    val base: String = s"http://127.0.0.1:$port"
    def calls: Int = received.size
    def last: Received = received.asScala.last
    private val closed = new java.util.concurrent.atomic.AtomicBoolean(false)
    def close(): Unit = if (closed.compareAndSet(false, true)) server.stop(0)
  }
  object StubSemantic {
    val goodBody: String =
      """{"hits":[{"key":"synthetic-p40t-hit-1","distance":0.125,"metadata":{"source":"synthetic-p40t"}}],"model":{"modelId":"synthetic-p40t-model","version":"v1","dimension":8}}"""
  }

  def withStub[A](check: StubSemantic => A): A = {
    val stub = new StubSemantic
    try check(stub)
    finally stub.close()
  }

  private final class Tee(first: OutputStream, second: OutputStream) extends OutputStream {
    override def write(b: Int): Unit = synchronized { first.write(b); second.write(b) }
    override def write(b: Array[Byte], off: Int, len: Int): Unit = synchronized {
      first.write(b, off, len); second.write(b, off, len)
    }
    override def flush(): Unit = synchronized { first.flush(); second.flush() }
  }

  /** Application loggers captured at every level; all other loggers at the shipped root level. */
  val applicationLoggers = Vector("scholarchain", "edu.uic.cs441.scholarchain")

  /** Runs `body` with log4j events and stdout/stderr captured. The capture mirrors the shipped
    * configuration (modules/services/src/main/resources/logback.xml: root INFO) for third-party
    * loggers and is stricter for application loggers (all levels). The console appender keeps its
    * previous threshold, so the build output is not flooded.
    */
  def capturing[A](body: => A): (A, String) = {
    val events = new ConcurrentLinkedQueue[String]
    val context = LogManager.getContext(false).asInstanceOf[LoggerContext]
    val root = context.getConfiguration.getRootLogger
    val priorLevel = root.getLevel
    val prior = root.getAppenders.asScala.toVector
    val appender = new AbstractAppender(
      "p40t-capture",
      null,
      PatternLayout.createDefaultLayout(),
      false,
      Array.empty[Property]
    ) {
      def append(event: LogEvent): Unit = {
        val thrown = Option(event.getThrown).map(t => t.toString + t.getStackTrace.mkString(" "))
        events.add(
          s"${event.getLevel} ${event.getLoggerName} ${event.getMessage.getFormattedMessage} " +
            s"${event.getContextData} ${thrown.getOrElse("")}"
        )
        ()
      }
    }
    appender.start()
    prior.foreach((name, _) => root.removeAppender(name))
    prior.foreach((_, a) => root.addAppender(a, priorLevel, null))
    root.addAppender(appender, Level.ALL, null)
    root.setLevel(Level.INFO)
    val config = context.getConfiguration
    val added = applicationLoggers.filterNot(config.getLoggers.containsKey)
    added.foreach(name => config.addLogger(name, new LoggerConfig(name, Level.ALL, true)))
    context.updateLoggers()
    val streams = new ByteArrayOutputStream
    val (out0, err0) = (System.out, System.err)
    val out = new PrintStream(new Tee(out0, streams), true, UTF_8)
    val err = new PrintStream(new Tee(err0, streams), true, UTF_8)
    System.setOut(out); System.setErr(err)
    try {
      val result = Console.withOut(out)(Console.withErr(err)(body))
      out.flush(); err.flush()
      (result, events.asScala.mkString("\n") + "\n" + streams.toString(UTF_8))
    } finally {
      System.setOut(out0); System.setErr(err0)
      added.foreach(config.removeLogger)
      root.removeAppender("p40t-capture")
      prior.foreach((name, _) => root.removeAppender(name))
      prior.foreach((_, a) => root.addAppender(a, null, null))
      root.setLevel(priorLevel)
      context.updateLoggers()
      appender.stop()
    }
  }
}
