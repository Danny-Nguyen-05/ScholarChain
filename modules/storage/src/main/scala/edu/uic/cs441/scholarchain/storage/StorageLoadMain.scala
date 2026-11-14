package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import java.net.URI
import java.time.Duration
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import software.amazon.awssdk.auth.credentials.{
  AwsCredentialsProvider,
  AwsSessionCredentials,
  ProfileCredentialsProvider
}
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.{
  StartLoaderJobResponse,
  GetLoaderJobStatusResponse
}
import scala.jdk.CollectionConverters.*
import StorageResult.*

/** Explicit composition boundary. No credential provider/client is constructed before the real
  * execution gate. Default dry-run validates and reports a plan; execute-fake traverses the ports.
  */
object StorageLoadMain {
  private def fakeNeptune: NeptunedataClient = Proxy
    .newProxyInstance(
      classOf[NeptunedataClient].getClassLoader,
      Array(classOf[NeptunedataClient]),
      new InvocationHandler {
        def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef = method.getName match {
          case "startLoaderJob" =>
            StartLoaderJobResponse
              .builder()
              .status("200 OK")
              .payload(Map("loadId" -> "local-fake-load").asJava)
              .build()
          case "getLoaderJobStatus" =>
            GetLoaderJobStatusResponse
              .builder()
              .status("200 OK")
              .payload(
                Document.fromMap(
                  Map(
                    "overallStatus" -> Document.fromMap(
                      Map("status" -> Document.fromString("LOAD_COMPLETED")).asJava
                    )
                  ).asJava
                )
              )
              .build()
          case "close" => null
          case _ => throw new UnsupportedOperationException("unsupported fake Neptune operation")
        }
      }
    )
    .asInstanceOf[NeptunedataClient]
  private def failureCode(result: StorageResult[?]): String = result match {
    case Rejected(code) if code.matches("[A-Za-z0-9._-]{1,128}") => code
    case Retried(_, nested)                                      => failureCode(nested)
    case _                                                       => "operation-rejected"
  }
  private val defaultLoader = NeptuneLoaderConfig("b", "g", "r", "a")

  /** Optional loader poll budget. A lone timeout derives the poll count at the default interval,
    * and a lone poll count derives the timeout, never going below the unchanged defaults. Bounds:
    * timeout 1..14400 seconds, polls 1..20000.
    */
  private[storage] def loaderBudget(
      timeoutSeconds: Option[String],
      maxPolls: Option[String]
  ): Either[String, Option[(Long, Int)]] = {
    val interval = math.max(1L, defaultLoader.pollIntervalMillis)
    val timeout = timeoutSeconds.map(_.toLongOption.filter(n => n >= 1 && n <= 14400L))
    val polls = maxPolls.map(_.toIntOption.filter(n => n >= 1 && n <= 20000))
    if (timeout.contains(None)) Left("--load-timeout-seconds must be an integer from 1 to 14400.")
    else if (polls.contains(None)) Left("--load-max-polls must be an integer from 1 to 20000.")
    else
      (timeout.flatten, polls.flatten) match {
        case (None, None)       => Right(None)
        case (Some(t), Some(p)) => Right(Some((t * 1000L, p)))
        case (Some(t), None) =>
          val ms = t * 1000L
          Right(
            Some(
              (ms, math.max(defaultLoader.maxPolls.toLong, (ms + interval - 1) / interval).toInt)
            )
          )
        case (None, Some(p)) =>
          Right(Some((math.max(defaultLoader.timeoutMillis, p.toLong * interval), p)))
      }
  }

  /** Resolves the named profile through the Java SDK only. It makes no AWS API call and prints
    * neither the access key nor any secret. For caller identity use `aws sts get-caller-identity`.
    */
  private def checkCredentials(
      profile: String,
      out: String => Unit,
      credentialsFor: String => AwsCredentialsProvider
  ): Int = {
    val provider = credentialsFor(profile)
    try {
      val credentials = provider.resolveCredentials()
      val session = credentials.isInstanceOf[AwsSessionCredentials]
      val expires = Option(credentials.expirationTime().orElse(null)).map(_.toString)
      out(
        s"CREDENTIALS-RESOLVED: profile=$profile sessionToken=$session expiresAt=${expires.getOrElse("unknown")}"
      )
      0
    } catch {
      case e: Exception =>
        out(s"CREDENTIALS-FAILED: profile=$profile reason=${e.getClass.getSimpleName}"); 1
    } finally
      provider match {
        case c: AutoCloseable =>
          try c.close()
          catch { case _: Exception => () }
        case _ => ()
      }
  }

  def run(
      args: Vector[String],
      out: String => Unit = println,
      credentialsFor: String => AwsCredentialsProvider = p =>
        ProfileCredentialsProvider.builder().profileName(p).build()
  ): Int = {
    var clients = Vector.empty[AutoCloseable]
    try {
      val flags = Set("--execute-fake", "--execute-aws", "--dry-run")
      val values = scala.collection.mutable.Map.empty[String, String];
      val enabled = scala.collection.mutable.Set.empty[String]
      var checkOnly = false
      var graphOnly = false
      var i = 0
      while (i < args.size) {
        val arg = args(i);
        if (arg == "--check-credentials") {
          if (checkOnly) throw new IllegalArgumentException("duplicate flag"); checkOnly = true;
          i += 1
        } else if (arg == "--graph-only") {
          if (graphOnly) throw new IllegalArgumentException("duplicate flag"); graphOnly = true;
          i += 1
        } else if (flags(arg)) {
          if (!enabled.add(arg)) throw new IllegalArgumentException("duplicate flag"); i += 1
        } else {
          if (
            !Set(
              "--manifest",
              "--config",
              "--environment",
              "--profile",
              "--load-timeout-seconds",
              "--load-max-polls"
            )(
              arg
            ) || i + 1 >= args.size || values.contains(arg)
          ) throw new IllegalArgumentException("invalid arguments"); values(arg) = args(i + 1);
          i += 2
        }
      }
      if (checkOnly) {
        if (
          graphOnly || enabled.nonEmpty || values.keySet != Set("--profile") || values(
            "--profile"
          ).isEmpty
        ) {
          out("REFUSED: --check-credentials accepts only --profile."); return 2
        }
        return checkCredentials(values("--profile"), out, credentialsFor)
      }
      if (enabled.size > 1) throw new IllegalArgumentException("execution flags conflict")
      val budget =
        loaderBudget(values.get("--load-timeout-seconds"), values.get("--load-max-polls")) match {
          case Right(b)      => b
          case Left(message) => out("REFUSED: " + message); return 2
        }
      val manifestPath = Path
        .of(values.getOrElse("--manifest", throw new IllegalArgumentException("manifest required")))
        .toRealPath()
      val root =
        if (Files.isDirectory(manifestPath)) manifestPath else manifestPath.getParent.getParent
      val configPath = Path
        .of(values.getOrElse("--config", throw new IllegalArgumentException("config required")))
        .toRealPath()
      if (Files.size(configPath) > 1024 * 1024)
        throw new IllegalArgumentException("configuration too large")
      val cfg = ujson.read(Files.readString(configPath, UTF_8))
      if (cfg("schemaVersion").str != "scholarchain.storage-load.v1")
        throw new IllegalArgumentException("unsupported config")
      val real = enabled("--execute-aws"); val fake = enabled("--execute-fake")
      if (real) {
        val environment = values.getOrElse("--environment", "")
        val approved =
          cfg.obj.get("approvedEnvironment").filter(_ != ujson.Null).map(_.str).getOrElse("")
        if (
          environment.isEmpty || approved != environment || cfg(
            "environment"
          ).str != environment || values.getOrElse("--profile", "").isEmpty
        ) {
          out(
            "REFUSED: real AWS requires explicit execution, profile and matching approved environment."
          ); return 2
        }
      } else if (values.contains("--environment") || values.contains("--profile")) {
        out("REFUSED: environment/profile options require explicit AWS execution."); return 2
      }
      if (!real && !fake && budget.nonEmpty) {
        out("REFUSED: loader timeout options require --execute-aws or --execute-fake."); return 2
      }
      val rawManifest = root.resolve("load-manifests/s3.json")
      if (Files.size(rawManifest) > 4 * 1024 * 1024)
        throw new IllegalArgumentException("source manifest too large")
      val manifests = CoreJson
        .parse[Vector[LoadManifest]](Files.readString(rawManifest, UTF_8))
        .toOption
        .getOrElse(throw new IllegalArgumentException("invalid load manifest"))
      val runId = manifests.headOption
        .map(_.context.runId)
        .getOrElse(throw new IllegalArgumentException("empty source manifest"))
      val validator = new NeptuneExportValidator()
      val graphManifest = GraphLoadManifest(runId, root.toString, "opencypher")
      val validation = validator.validate(graphManifest)
      val counts = StorageResult.value(validation) match {
        case Some(validated) =>
          try
            s"nodes=${validated.nodeCount} edges=${validated.edgeCount} support=${validated.supportCount}"
          finally validated.close()
        case None => out("FAILED: graph export validation rejected."); return 1
      }
      out(s"runId=$runId mode=${if (real) "aws" else if (fake) "fake" else "dry-run"} $counts")
      if (!real && !fake && graphOnly) {
        out("PLAN: graph-only; cache step skipped (caches must already be loaded for this run)")
        out(
          "PLAN: upload validated graph/support and submit and poll Neptune through ports. No AWS calls or external store writes performed."
        ); return 0
      }
      if (!real && !fake) {
        val plan = new Phase6CacheLoader(
          new InMemoryEntityLinkCache,
          new InMemoryResearcherMetricStore,
          new LocalParquetManifestReader(root),
          sourceObjects = new InMemoryObjectStore,
          sourceRegistry = new InMemoryArtifactRegistry
        ).load(manifests)
        if (!StorageResult.successful(plan)) {
          out("FAILED: cache source validation rejected; reason=" + failureCode(plan)); return 1
        }
        out(
          s"PLAN: cacheWrites=${StorageResult.value(plan).get.written} cacheUnchanged=${StorageResult.value(plan).get.unchanged}"
        )
        out(
          "PLAN: upload validated graph/support and source qualifications; load entity/metric caches; submit and poll Neptune through ports. No AWS calls or external store writes performed."
        ); return 0
      }
      val tables = upickle.default.read[DynamoTables](cfg("tables"))
      val storage = edu.uic.cs441.scholarchain.storage.StorageConfig(cfg("bucket").str, tables)
      val baseLoaderConfig = NeptuneLoaderConfig(
        storage.bucket,
        cfg("graphPrefix").str,
        cfg("region").str,
        cfg("neptune")("iamRoleArn").str
      )
      val loaderConfig = budget
        .map((timeout, polls) => baseLoaderConfig.copy(timeoutMillis = timeout, maxPolls = polls))
        .getOrElse(baseLoaderConfig)
      budget.foreach((timeout, polls) =>
        out(s"loader: timeoutMillis=$timeout maxPolls=$polls (override)")
      )
      val (objects, links, metrics, ledger, registry, neptune): (
          ObjectStore,
          EntityLinkCache,
          ResearcherMetricStore,
          RunLedger,
          ArtifactRegistry,
          NeptunedataClient
      ) = if (fake) {
        (
          new InMemoryObjectStore,
          new InMemoryEntityLinkCache,
          new InMemoryResearcherMetricStore,
          new InMemoryRunLedger,
          new InMemoryArtifactRegistry,
          fakeNeptune
        )
      } else {
        val credentials = credentialsFor(values("--profile"))
        val overrideConfig = ClientOverrideConfiguration
          .builder()
          .apiCallTimeout(Duration.ofMillis(loaderConfig.requestTimeoutMillis))
          .apiCallAttemptTimeout(Duration.ofMillis(loaderConfig.requestTimeoutMillis))
          .build()
        val region = Region.of(cfg("region").str)
        val s3 = S3Client
          .builder()
          .region(region)
          .credentialsProvider(credentials)
          .overrideConfiguration(overrideConfig)
          .build()
        val dynamo = DynamoDbClient
          .builder()
          .region(region)
          .credentialsProvider(credentials)
          .overrideConfiguration(overrideConfig)
          .build()
        val graph = NeptunedataClient
          .builder()
          .region(region)
          .credentialsProvider(credentials)
          .endpointOverride(URI.create(cfg("neptune")("endpoint").str))
          .overrideConfiguration(overrideConfig)
          .build()
        clients = Vector(s3, dynamo, graph) ++ (credentials match {
          case c: AutoCloseable => Vector(c)
          case _                => Vector.empty
        })
        val objects = new S3ObjectStore(s3, storage)
        (
          objects,
          new DynamoEntityLinkCache(dynamo, storage),
          new DynamoResearcherMetricStore(dynamo, storage),
          new DynamoRunLedger(dynamo, storage),
          new DynamoArtifactRegistry(dynamo, storage),
          graph
        )
      }
      val cache =
        if (graphOnly) None
        else {
          val loadedCache = new Phase6CacheLoader(
            links,
            metrics,
            new LocalParquetManifestReader(root),
            sourceObjects = objects,
            sourceRegistry = registry
          ).load(manifests)
          if (!StorageResult.successful(loadedCache)) {
            out("FAILED: cache loading rejected; reason=" + failureCode(loadedCache)); return 1
          }
          Some(loadedCache)
        }
      val graph = new NeptuneGraphLoader(
        neptune,
        objects,
        ledger,
        registry,
        loaderConfig,
        validator,
        sleep = (if (fake) (_: Long) => () else (ms: Long) => Thread.sleep(ms))
      )
      val loaded = graph.submitBulkLoad(graphManifest)
      if (!StorageResult.successful(loaded)) {
        out("FAILED: graph loading rejected; reason=" + failureCode(loaded)); return 1
      }
      val graphState = StorageResult.value(loaded).get.state
      cache match {
        case None => out(s"COMPLETE: cacheSkipped=true graphState=$graphState")
        case Some(c) =>
          val result = StorageResult.value(c).get
          out(
            s"COMPLETE: cacheWritten=${result.written} cacheUnchanged=${result.unchanged} graphState=$graphState"
          )
      }
      0
    } catch {
      case _: Exception => out("REFUSED: invalid arguments, configuration or source data."); 2
    } finally
      clients.reverse.foreach(c =>
        try c.close()
        catch { case _: Exception => () }
      )
  }
  def main(args: Array[String]): Unit = {
    val result = run(args.toVector);
    if (result != 0)
      throw new IllegalStateException("StorageLoadMain failed with exit code " + result)
  }
}
