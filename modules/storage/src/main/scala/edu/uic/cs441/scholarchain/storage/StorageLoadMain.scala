package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import java.net.URI
import java.time.Duration
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider
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
  def run(args: Vector[String], out: String => Unit = println): Int = {
    var clients = Vector.empty[AutoCloseable]
    try {
      val flags = Set("--execute-fake", "--execute-aws", "--dry-run")
      val values = scala.collection.mutable.Map.empty[String, String];
      val enabled = scala.collection.mutable.Set.empty[String]
      var i = 0
      while (i < args.size) {
        val arg = args(i);
        if (flags(arg)) {
          if (!enabled.add(arg)) throw new IllegalArgumentException("duplicate flag"); i += 1
        } else {
          if (
            !Set("--manifest", "--config", "--environment", "--profile")(
              arg
            ) || i + 1 >= args.size || values.contains(arg)
          ) throw new IllegalArgumentException("invalid arguments"); values(arg) = args(i + 1);
          i += 2
        }
      }
      if (enabled.size > 1) throw new IllegalArgumentException("execution flags conflict")
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
      val loaderConfig = NeptuneLoaderConfig(
        storage.bucket,
        cfg("graphPrefix").str,
        cfg("region").str,
        cfg("neptune")("iamRoleArn").str
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
        val credentials =
          ProfileCredentialsProvider.builder().profileName(values("--profile")).build()
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
        clients = Vector(s3, dynamo, graph, credentials)
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
      val cache = new Phase6CacheLoader(
        links,
        metrics,
        new LocalParquetManifestReader(root),
        sourceObjects = objects,
        sourceRegistry = registry
      ).load(manifests)
      if (!StorageResult.successful(cache)) {
        out("FAILED: cache loading rejected; reason=" + failureCode(cache)); return 1
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
      val result = StorageResult.value(cache).get
      out(
        s"COMPLETE: cacheWritten=${result.written} cacheUnchanged=${result.unchanged} graphState=${StorageResult.value(loaded).get.state}"
      )
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
