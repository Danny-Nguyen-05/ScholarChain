package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.StableIds
import java.lang.management.ManagementFactory
import java.net.InetAddress
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardOpenOption}
import java.security.MessageDigest
import java.util.UUID
import java.util.jar.JarFile
import org.apache.spark.{SparkEnv, TaskContext}
import org.apache.spark.api.java.JavaSparkContext
import org.apache.spark.api.java.function.FlatMapFunction
import org.apache.spark.sql.{DataFrame, SparkSession}
import scala.jdk.CollectionConverters.*
import scala.util.Try

/** Additive operational evidence for Phase 12. Never creates cloud resources or changes job IDs. */
object Phase12Readiness {
  private val marker = "_SCHOLARCHAIN_SPARK_COMPLETE"
  private val semanticFields = Vector(
    "runId",
    "codeVersion",
    "hadoopRunId",
    "hadoopManifestHash",
    "entityResolutionRunId",
    "entityResolutionManifestHash",
    "entityResolutionPolicyVersion",
    "entityResolutionPolicyHash",
    "logicalConfigFingerprint",
    "identityPolicyVersion",
    "representativePolicyVersion",
    "graphPolicyVersion",
    "windows",
    "seed",
    "contentHashMethod"
  )
  private[spark] val datasets: Set[String] = Set(
    "nodes/type=researcher",
    "nodes/type=author_mention",
    "nodes/type=work",
    "nodes/type=venue",
    "nodes/type=institution",
    "nodes/type=topic",
    "nodes/type=work_sources",
    "edges/type=authored",
    "edges/type=resolves_to",
    "edges/type=published_in",
    "edges/type=affiliated_with",
    "edges/type=has_topic",
    "edges/type=coauthored_with",
    "edges/type=coauthored_with_support",
    "metrics/type=researcher_collaboration",
    "metrics/type=components",
    "metrics/type=component_summaries",
    "metrics/type=communities",
    "metrics/type=community_summaries",
    "metrics/type=cross_community_edges",
    "metrics/type=bridges",
    "metrics/type=kcore",
    "metrics/type=temporal_changes",
    "metrics/type=path_length_estimate",
    "path-evidence",
    "semantic-summaries",
    "integrity/violations",
    "integrity/rejects"
  )

  private def digest(path: Path): String = {
    val hash = MessageDigest.getInstance("SHA-256")
    val input = Files.newInputStream(path)
    try {
      val buffer = new Array[Byte](65536)
      var n = input.read(buffer)
      while (n >= 0) {
        if (n > 0) hash.update(buffer, 0, n)
        n = input.read(buffer)
      }
      hash.digest().map(b => f"${b & 255}%02x").mkString
    } finally input.close()
  }

  private[spark] def safeDirectory(path: Path): Path = {
    require(path.isAbsolute && path.normalize() == path, "absolute normalized directory required")
    var node: Path = path
    while (node != null) {
      require(!Files.isSymbolicLink(node), "symlink path refused")
      node = node.getParent
    }
    require(Files.isDirectory(path), "existing directory required")
    path
  }

  private[spark] def writeNew(path: Path, value: ujson.Value): Unit = {
    require(path.isAbsolute && path.normalize() == path, "absolute normalized output required")
    safeDirectory(path.getParent)
    require(!Files.exists(path) && !Files.isSymbolicLink(path), "output already exists")
    Files.writeString(
      path,
      value.render(indent = 2) + "\n",
      UTF_8,
      StandardOpenOption.CREATE_NEW,
      StandardOpenOption.WRITE
    )
  }

  private def session(name: String): SparkSession = {
    val builder = SparkSession
      .builder()
      .appName(name)
      .config("spark.ui.enabled", "false")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.task.maxFailures", "1")
    if (!sys.props.get("spark.master").isDefined && !sys.env.get("SPARK_MASTER").isDefined)
      builder.master("local[2]")
    builder.getOrCreate()
  }

  private[spark] def processSnapshot(role: String): ujson.Obj = {
    val classes = Vector(
      ("spark", "org.apache.spark.SparkContext", Some(org.apache.spark.SPARK_VERSION)),
      ("scala-library", "scala.Option", Some(scala.util.Properties.versionNumberString)),
      ("scala-reflect", "scala.reflect.api.Universe", None),
      ("scala3-library", "scala.deriving.Mirror", None)
    )
    val sources = scala.collection.mutable.Map.empty[Path, String]
    val libraries = classes.map { case (component, name, runtimeVersion) =>
      val klass = Class.forName(name, false, Thread.currentThread().getContextClassLoader)
      val location = Path.of(klass.getProtectionDomain.getCodeSource.getLocation.toURI)
      val entry = name.replace('.', '/') + ".class"
      val bytes =
        if (Files.isDirectory(location)) Files.readAllBytes(location.resolve(entry))
        else {
          val jar = new JarFile(location.toFile)
          try {
            val item = jar.getJarEntry(entry)
            require(item != null, "loaded class source entry unavailable")
            val input = jar.getInputStream(item)
            try input.readAllBytes()
            finally input.close()
          } finally jar.close()
        }
      val sourceHash =
        if (Files.isRegularFile(location))
          ujson.Str(sources.getOrElseUpdate(location, digest(location)))
        else ujson.Null
      ujson.Obj(
        "component" -> component,
        "className" -> name,
        "origin" -> location.toString,
        "classSha256" -> MessageDigest
          .getInstance("SHA-256")
          .digest(bytes)
          .map(b => f"${b & 255}%02x")
          .mkString,
        "codeSourceSha256" -> sourceHash,
        "runtimeVersion" -> runtimeVersion.map(ujson.Str(_)).getOrElse(ujson.Null),
        "implementationVersion" -> Option(klass.getPackage.getImplementationVersion)
          .map(ujson.Str(_))
          .getOrElse(ujson.Null)
      )
    }
    ujson.Obj(
      "role" -> role,
      "host" -> InetAddress.getLocalHost.getHostName,
      "pid" -> ProcessHandle.current().pid().toString,
      "jvmStartTime" -> ManagementFactory.getRuntimeMXBean.getStartTime.toString,
      "executorId" -> Option(SparkEnv.get).map(_.executorId).getOrElse("unavailable"),
      "javaVersion" -> System.getProperty("java.version"),
      "libraries" -> ujson.Arr.from(libraries)
    )
  }

  private[spark] def requireExternal(driver: ujson.Value, executor: ujson.Value): Unit = {
    require(
      executor("executorId").str != "driver" && executor("executorId").str != "unavailable",
      "non-driver executor required"
    )
    require(
      driver("host").str != executor("host").str || driver("pid").str != executor("pid").str,
      "executor must run outside driver process"
    )
  }

  def probe(shared: Path, output: Path, requireDistributed: Boolean): ujson.Value = {
    safeDirectory(shared); safeDirectory(output.getParent)
    require(!Files.exists(output) && !Files.isSymbolicLink(output), "output already exists")
    val token = UUID.randomUUID().toString
    val exchange = shared.resolve("phase12-probe-" + token)
    Files.createDirectory(exchange)
    Files.writeString(
      exchange.resolve("driver-token.txt"),
      token,
      UTF_8,
      StandardOpenOption.CREATE_NEW,
      StandardOpenOption.WRITE
    )
    val spark = session("ScholarChain Phase12 runtime and filesystem probe")
    try {
      require(
        spark.sparkContext.hadoopConfiguration.get("fs.defaultFS", "file:///") == "file:///",
        "identical POSIX mount strategy requires fs.defaultFS=file:///"
      )
      val driver = processSnapshot("driver")
      val sharedName = exchange.toString
      val task = new FlatMapFunction[java.util.Iterator[Integer], String] {
        override def call(ignored: java.util.Iterator[Integer]): java.util.Iterator[String] = {
          val directory = Path.of(sharedName)
          safeDirectory(directory)
          require(
            Files.readString(directory.resolve("driver-token.txt"), UTF_8) == token,
            "executor cannot see driver shared token"
          )
          val snapshot = processSnapshot("executor-task")
          val proof = "executor-" + TaskContext.get().taskAttemptId() + ".json"
          snapshot("proofFile") = ujson.Str(proof)
          snapshot("sharedToken") = ujson.Str(token)
          writeNew(directory.resolve(proof), snapshot)
          java.util.Collections.singletonList(snapshot.render()).iterator()
        }
      }
      val reportRows = JavaSparkContext
        .fromSparkContext(spark.sparkContext)
        .parallelize(java.util.Collections.singletonList(Integer.valueOf(1)), 1)
        .mapPartitions(task)
      val reports = BoundedActions.cappedJava(reportRows, 1).map(ujson.read(_))
      require(reports.size == 1, "exactly one task report required")
      reports.foreach { report =>
        require(report("sharedToken").str == token, "shared token mismatch")
        val path = exchange.resolve(report("proofFile").str)
        require(
          ujson.read(Files.readString(path, UTF_8)) == report,
          "driver cannot see executor shared proof"
        )
        if (requireDistributed) requireExternal(driver, report)
      }
      val external = reports.forall { report =>
        Try(requireExternal(driver, report)).isSuccess
      }
      val result = ujson.Obj(
        "schemaVersion" -> "scholarchain.phase12-readiness.v1",
        "stage" -> "probe",
        "driver" -> driver,
        "taskProcesses" -> ujson.Arr.from(reports),
        "sharedAbsoluteDirectory" -> shared.toString,
        "exchangeDirectory" -> exchange.toString,
        "driverToTaskAndBackVerified" -> true,
        "externalExecutorVerified" -> external,
        "distributedRequired" -> requireDistributed,
        "cloudCompatibilityVerified" -> false,
        "componentVersionQualification" -> "Null versions are unknown; match class/source hashes to the resolved build artifact inventory."
      )
      writeNew(output, result); result
    } finally spark.stop()
  }

  private[spark] def completedMetadata(root: Path): ujson.Value = {
    safeDirectory(root)
    def text(name: String): String = {
      val path = root.resolve(name)
      require(
        Files.isRegularFile(path) && !Files.isSymbolicLink(path),
        "completed output file required"
      )
      Files.readString(path, UTF_8)
    }
    val manifest = text("run-manifest.json")
    val metadata = text("run-metadata.json")
    require(
      text(marker) == StableIds.sha256Hex(manifest + "\n" + metadata) + "\n",
      "completion hash mismatch"
    )
    val parsed = ujson.read(metadata)
    require(ujson.read(manifest)("runId") == parsed("runId"), "manifest runId mismatch")
    require(parsed("contentHashMethod").str == Phase6Export.hashMethod, "hash method mismatch")
    parsed
  }

  private[spark] def requireSameSemantics(left: ujson.Value, right: ujson.Value): Unit = {
    semanticFields.foreach { field =>
      require(
        left.obj.contains(field) && right.obj.contains(field) && left(field) == right(field),
        "semantic metadata mismatch: " + field
      )
    }
  }

  private[spark] def tableInventory(metadata: ujson.Value): Map[String, ujson.Value] = {
    val entries = metadata("tables").arr.toVector
    val names = entries.map(_("dataset").str)
    require(
      names.size == names.distinct.size && names.toSet == datasets,
      "exact 28-table inventory required"
    )
    entries.foreach { entry =>
      require(entry("path").str == entry("dataset").str, "noncanonical table path")
      require(entry("rowCount").str.toLong >= 0L, "nonnegative table count required")
      require(entry("contentHash").str.matches("[0-9a-f]{64}"), "table hash required")
    }
    entries.map(row => row("dataset").str -> row).toMap
  }

  private[spark] def compareTable(
      name: String,
      left: DataFrame,
      right: DataFrame,
      expectedLeft: ujson.Value,
      expectedRight: ujson.Value
  ): ujson.Value = {
    require(left.schema == right.schema, "table schema mismatch: " + name)
    val leftCount = BoundedActions.count(left)
    val rightCount = BoundedActions.count(right)
    val leftHash = Phase6Export.logicalTableHash(left)
    val rightHash = Phase6Export.logicalTableHash(right)
    require(
      leftCount == expectedLeft("rowCount").str.toLong &&
        rightCount == expectedRight("rowCount").str.toLong,
      "stored row count mismatch: " + name
    )
    require(
      leftHash == expectedLeft("contentHash").str &&
        rightHash == expectedRight("contentHash").str,
      "stored logical hash mismatch: " + name
    )
    require(leftCount == rightCount && leftHash == rightHash, "logical table mismatch: " + name)
    // The production logical hash excludes only physical run_id. Preserve it in this stronger
    // bounded readiness equality as well; nested context/run IDs are never normalized.
    require(
      !BoundedActions.exists(left.exceptAll(right)) &&
        !BoundedActions.exists(right.exceptAll(left)),
      "full row multiset mismatch: " + name
    )
    ujson.Obj(
      "dataset" -> name,
      "rowCount" -> leftCount.toString,
      "contentHash" -> leftHash,
      "exactSchemaAndRowsMatch" -> true
    )
  }

  def compare(left: Path, right: Path, output: Path): ujson.Value = {
    safeDirectory(output.getParent)
    require(!Files.exists(output) && !Files.isSymbolicLink(output), "output already exists")
    val lm = completedMetadata(left); val rm = completedMetadata(right)
    requireSameSemantics(lm, rm)
    require(
      lm("codeVersion").str == Phase6Main.codeFingerprint,
      "comparison must use the same packaged code as both runs"
    )
    val lt = tableInventory(lm); val rt = tableInventory(rm)
    val spark = session("ScholarChain Phase12 exact same-artifact comparison")
    try {
      val compared = datasets.toVector.sorted.map { name =>
        val lp = left.resolve(name); val rp = right.resolve(name)
        safeDirectory(lp); safeDirectory(rp)
        compareTable(
          name,
          spark.read.parquet(lp.toString),
          spark.read.parquet(rp.toString),
          lt(name),
          rt(name)
        )
      }
      val result = ujson.Obj(
        "schemaVersion" -> "scholarchain.phase12-readiness.v1",
        "stage" -> "compare",
        "runId" -> lm("runId"),
        "codeVersion" -> lm("codeVersion"),
        "hadoopManifestHash" -> lm("hadoopManifestHash"),
        "entityResolutionManifestHash" -> lm("entityResolutionManifestHash"),
        "logicalConfigFingerprint" -> lm("logicalConfigFingerprint"),
        "tables" -> ujson.Arr.from(compared),
        "tablesCompared" -> datasets.size,
        "provenanceNormalization" -> "none",
        "allExactRowsMatch" -> true,
        "cloudCompatibilityVerified" -> false
      )
      writeNew(output, result); result
    } finally spark.stop()
  }

  def run(args: Array[String]): Either[String, ujson.Value] = Try {
    args.toVector match {
      case Vector("probe", shared, output, mode) if Set("local", "distributed")(mode) =>
        probe(Path.of(shared), Path.of(output), mode == "distributed")
      case Vector("compare", left, right, output) =>
        compare(Path.of(left), Path.of(right), Path.of(output))
      case _ =>
        throw new IllegalArgumentException(
          "usage: probe SHARED_ABSOLUTE_DIRECTORY OUTPUT_JSON local|distributed OR compare LEFT_RUN RIGHT_RUN OUTPUT_JSON"
        )
    }
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))

  def main(args: Array[String]): Unit = run(args) match {
    case Right(result) => println(result.render())
    case Left(error)   => System.err.println(error); sys.exit(2)
  }
}
