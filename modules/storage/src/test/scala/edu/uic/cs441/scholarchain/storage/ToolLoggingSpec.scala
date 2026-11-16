package edu.uic.cs441.scholarchain.storage

import ch.qos.logback.classic.{Level, LoggerContext}
import ch.qos.logback.classic.joran.JoranConfigurator
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.classic.util.ContextInitializer
import ch.qos.logback.core.read.ListAppender
import ch.qos.logback.core.joran.util.ConfigurationWatchListUtil
import com.sun.net.httpserver.{HttpExchange, HttpServer}
import java.io.ByteArrayOutputStream
import java.net.{InetSocketAddress, URI}
import java.nio.charset.StandardCharsets.{US_ASCII, UTF_8}
import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import org.slf4j.LoggerFactory
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import software.amazon.awssdk.auth.credentials.{AwsSessionCredentials, StaticCredentialsProvider}
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.profiles.ProfileFile
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import SubsetFixture.*

/** P38 (Session 1 finding N5): the storage tools must not log AWS SDK or HTTP wire lines, and so
  * never print the Authorization or X-Amz-Security-Token header, when they run. The tool here is
  * RuntimeArtifactMain with --execute-aws, driving a real SDK S3Client against a local fake S3 with
  * synthetic session credentials. Nothing leaves 127.0.0.1 and no profile file is read.
  */
class ToolLoggingSpec extends AnyFunSuite {
  private val accessKey = "AKIDSYNTHETICP38"
  private val secretKey = "synthetic-p38-secret-key"
  private val sessionToken = "synthetic-p38-session-token-0123456789"
  private val wireLoggers =
    Vector("org.apache.http", "org.apache.hc", "software.amazon.awssdk", "io.netty")
  private val leakMarkers =
    Vector(sessionToken, secretKey, "authorization", "x-amz-security-token", "aws4-hmac-sha256")

  /** Minimal path-style S3: PUT stores, HEAD answers from the store, anything else is 404. */
  private final class FakeS3 extends AutoCloseable {
    private val stored = mutable.Map.empty[String, (Array[Byte], String, Map[String, String])]
    val requests = new java.util.concurrent.atomic.AtomicInteger
    private val server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0)
    server.createContext("/", (x: HttpExchange) => handle(x))
    server.start()
    val endpoint: URI = URI.create(s"http://127.0.0.1:${server.getAddress.getPort}")

    private def handle(x: HttpExchange): Unit =
      try {
        requests.incrementAndGet()
        val raw = x.getRequestBody.readAllBytes()
        val path = x.getRequestURI.getPath
        val headers = x.getRequestHeaders
        (x.getRequestMethod, stored.synchronized(stored.get(path))) match {
          case ("PUT", None) =>
            val meta = headers.asScala.collect {
              case (k, v) if k.toLowerCase.startsWith("x-amz-meta-") => k.toLowerCase -> v.get(0)
            }.toMap
            val body =
              if (headers.containsKey("x-amz-decoded-content-length")) decodeChunks(raw) else raw
            stored.synchronized(stored(path) = (body, headers.getFirst("Content-Type"), meta))
            x.getResponseHeaders.add("ETag", "\"synthetic-etag\"")
            x.sendResponseHeaders(200, -1)
          case ("HEAD", Some((body, contentType, meta))) =>
            meta.foreach((k, v) => x.getResponseHeaders.add(k, v))
            x.getResponseHeaders.add("Content-Type", contentType)
            x.getResponseHeaders.add("Content-Length", body.length.toString)
            x.getResponseHeaders.add("ETag", "\"synthetic-etag\"")
            x.sendResponseHeaders(200, -1)
          case _ => x.sendResponseHeaders(404, -1)
        }
      } finally x.close()

    /** aws-chunked body: `<hex size>[;extensions]\r\n<data>\r\n` repeated until size 0. */
    private def decodeChunks(raw: Array[Byte]): Array[Byte] = {
      val out = new ByteArrayOutputStream
      var pos = 0
      var done = false
      while (!done) {
        var end = pos
        while (raw(end) != '\r') end += 1
        val size =
          Integer.parseInt(new String(raw, pos, end - pos, US_ASCII).takeWhile(_ != ';'), 16)
        pos = end + 2
        if (size == 0) done = true
        else { out.write(raw, pos, size); pos += size + 2 }
      }
      out.toByteArray
    }

    def client(): S3Client = {
      val noProfile = ProfileFile
        .builder()
        .content(new java.io.ByteArrayInputStream(Array.emptyByteArray))
        .`type`(ProfileFile.Type.CONFIGURATION)
        .build()
      S3Client
        .builder()
        .region(Region.US_EAST_2)
        .endpointOverride(endpoint)
        .forcePathStyle(true)
        .credentialsProvider(
          StaticCredentialsProvider.create(
            AwsSessionCredentials.create(accessKey, secretKey, sessionToken)
          )
        )
        .overrideConfiguration(
          ClientOverrideConfiguration.builder().defaultProfileFile(noProfile).build()
        )
        .build()
    }
    def close(): Unit = server.stop(0)
  }

  /** Runs the tool's upload path against the fake and returns its exit code and output lines. */
  private def runTool(fake: FakeS3): (Int, Vector[String]) = {
    val root: Path = Files.createTempDirectory("tool-logging-")
    try {
      val source = Files.createDirectories(root.resolve("export/load-manifests")).getParent
      Files.writeString(
        source.resolve("load-manifests/s3.json"),
        upickle.default.write(manifests()),
        UTF_8
      )
      val include = root.resolve("include.txt")
      Files.writeString(include, s"$e\n", UTF_8)
      val deps = RuntimeArtifactMain.Deps(
        reader = _ => new Reader(SubsetFixture.source),
        objects = (_, _, bucket) => {
          val client = fake.client()
          val tables = DynamoTables("r", "l", "s", "e", "a", "m", "i")
          (new S3ObjectStore(client, StorageConfig(bucket, tables)), client)
        }
      )
      val args = Vector(
        "--source",
        source.toString,
        "--include-ids",
        include.toString,
        "--out-dir",
        root.resolve("out").toString,
        "--run-prefix",
        "run-p38-logging",
        "--execute-aws",
        "--profile",
        "synthetic",
        "--bucket",
        "synthetic-bucket",
        "--region",
        "us-east-2"
      )
      val lines = mutable.Buffer.empty[String]
      val code = RuntimeArtifactMain.run(args, lines += _, deps)
      (code, lines.toVector)
    } finally
      Files.walk(root).sorted(java.util.Comparator.reverseOrder()).forEach(p => Files.delete(p))
  }

  private def context: LoggerContext =
    LoggerFactory.getILoggerFactory.asInstanceOf[LoggerContext]

  /** Captures every event the root logger accepts while `body` runs. */
  private def capture[A](ctx: LoggerContext)(body: => A): (A, Vector[ILoggingEvent]) = {
    val root = ctx.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)
    val appender = new ListAppender[ILoggingEvent]
    appender.setContext(ctx)
    appender.start()
    root.addAppender(appender)
    try {
      val result = body
      // At DEBUG, SDK and fake-server threads can still be logging; `AppenderBase.doAppend` holds
      // the appender's monitor, so copy under it (an unguarded copy threw
      // ConcurrentModificationException in the lane G run, storage-test-1.log).
      (result, appender.synchronized(appender.list.asScala.toVector))
    } finally { root.detachAppender(appender); appender.stop() }
  }

  private def text(event: ILoggingEvent): String =
    (event.getLoggerName + " " + event.getFormattedMessage + " " +
      Option(event.getThrowableProxy).map(_.getMessage).getOrElse("")).toLowerCase

  private def isWireName(name: String): Boolean =
    wireLoggers.exists(n => name == n || name.startsWith(n + "."))
  private def isWire(event: ILoggingEvent): Boolean = isWireName(event.getLoggerName)

  /** Runs `body` with `logback.configurationFile` set to `value`, then restores the property and
    * re-runs logback's own start-up configuration so later suites see the logging they started
    * with.
    */
  private def withConfigurationProperty[A](value: Option[String])(body: => A): A = {
    val previous = Option(System.getProperty(ToolLogging.property))
    value match {
      case Some(v) => System.setProperty(ToolLogging.property, v)
      case None    => System.clearProperty(ToolLogging.property)
    }
    try body
    finally {
      previous match {
        case Some(v) => System.setProperty(ToolLogging.property, v)
        case None    => System.clearProperty(ToolLogging.property)
      }
      val ctx = context
      ctx.reset()
      new ContextInitializer(ctx).autoConfig()
    }
  }

  private def levelsOf(ctx: LoggerContext): Map[String, Level] =
    (Vector(
      org.slf4j.Logger.ROOT_LOGGER_NAME,
      "edu.uic.cs441.scholarchain.storage",
      "org.apache.http.wire",
      "org.apache.http.headers",
      "org.apache.hc.client5.http.wire",
      "software.amazon.awssdk.request",
      "software.amazon.awssdk.http.auth.aws.internal.signer",
      "io.netty.handler.logging.LoggingHandler"
    ) ++ wireLoggers).map(n => n -> ctx.getLogger(n).getEffectiveLevel).toMap

  private def assertToolLevels(levels: Map[String, Level]): Unit = {
    assert(levels(org.slf4j.Logger.ROOT_LOGGER_NAME) == Level.INFO, levels)
    assert(levels("edu.uic.cs441.scholarchain.storage") == Level.INFO, levels)
    levels.filter((n, _) => isWireName(n)).foreach((n, l) => assert(l == Level.WARN, s"$n is $l"))
  }

  test("both packaged configurations set root INFO and every wire, header and signer logger WARN") {
    for (name <- Vector(ToolLogging.resource, "logback-test.xml")) {
      val url = Option(getClass.getClassLoader.getResource(name)).getOrElse(fail(s"no $name"))
      val ctx = new LoggerContext
      val configurator = new JoranConfigurator
      configurator.setContext(ctx)
      configurator.doConfigure(url)
      assertToolLevels(levelsOf(ctx))
      ctx.stop()
    }
  }

  test("install selects the packaged configuration and keeps an operator's explicit choice") {
    withConfigurationProperty(None) {
      assert(ToolLogging.install() == ToolLogging.resource)
      assert(System.getProperty(ToolLogging.property) == ToolLogging.resource)
    }
    withConfigurationProperty(Some("/operator/chosen-logback.xml")) {
      assert(ToolLogging.install() == "/operator/chosen-logback.xml")
      assert(System.getProperty(ToolLogging.property) == "/operator/chosen-logback.xml")
    }
    withConfigurationProperty(Some("  ")) {
      assert(ToolLogging.install() == ToolLogging.resource)
    }
  }

  test("both tool mains install the packaged configuration before doing any work") {
    withConfigurationProperty(None) {
      RuntimeArtifactMain.main(Array("--help"))
      assert(System.getProperty(ToolLogging.property) == ToolLogging.resource)
    }
    withConfigurationProperty(None) {
      // An unknown flag is refused before any client is built; main reports it by throwing.
      intercept[IllegalStateException](StorageLoadMain.main(Array("--p38-unknown-flag")))
      assert(System.getProperty(ToolLogging.property) == ToolLogging.resource)
    }
  }

  test("a tool run against fakes logs no DEBUG wire line and no credential header or token") {
    withConfigurationProperty(None) {
      ToolLogging.install()
      // The same start-up configuration logback performs in a fresh tool JVM.
      val ctx = context
      ctx.reset()
      new ContextInitializer(ctx).autoConfig()
      // Logback read the packaged tool file, not the test class path's logback-test.xml.
      val source = ConfigurationWatchListUtil.getMainWatchURL(ctx)
      assert(source != null && source.toString.endsWith("/" + ToolLogging.resource), source)
      assertToolLevels(levelsOf(ctx))
      val fake = new FakeS3
      try {
        val ((code, lines), events) = capture(ctx)(runTool(fake))
        assert(code == 0, lines.mkString("\n"))
        assert(lines.exists(_.startsWith("UPLOAD: written s3://synthetic-bucket/")), lines)
        assert(fake.requests.get() >= 2, "the SDK must actually call the fake (PUT and HEAD)")
        assert(!events.exists(_.getLevel.toInt < Level.INFO.toInt), events.map(text))
        assert(!events.exists(isWire), events.map(text))
        val leaks = for (ev <- events; m <- leakMarkers if text(ev).contains(m)) yield m
        assert(leaks.isEmpty, events.map(text))
        assert(!lines.exists(l => leakMarkers.exists(m => l.toLowerCase.contains(m))), lines)
      } finally fake.close()
    }
  }

  test("control: under logback's unconfigured DEBUG default the same run does leak") {
    withConfigurationProperty(None) {
      val ctx = context
      ctx.reset()
      ctx.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME).setLevel(Level.DEBUG)
      val fake = new FakeS3
      try {
        val ((code, _), events) = capture(ctx)(runTool(fake))
        assert(code == 0)
        assert(events.exists(ev => isWire(ev) && ev.getLevel == Level.DEBUG))
        val texts = events.map(text)
        assert(
          texts.exists(t => t.contains(sessionToken) || t.contains("x-amz-security-token")),
          "the detector must see the token-bearing lines the packaged configuration suppresses"
        )
      } finally fake.close()
    }
  }
}
