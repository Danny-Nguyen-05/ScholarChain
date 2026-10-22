package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.MessageDigest
import java.util.UUID
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.*
import scala.jdk.CollectionConverters.*
import scala.util.Try

/** Full local/cluster Spark jobs 1–11 entry point. Inputs are files, never a live service. */
object Phase6Main {
  private val marker = "_SCHOLARCHAIN_SPARK_COMPLETE"

  /** Class bytes bind semantics even when developers forget a manual version bump. */
  def codeFingerprint: String = {
    val digest = MessageDigest.getInstance("SHA-256")
    Vector(classOf[Phase6CResult], classOf[SparkAnalyticsConfig]).foreach { klass =>
      val source = Path.of(klass.getProtectionDomain.getCodeSource.getLocation.toURI)
      if (Files.isDirectory(source)) {
        val walk = Files.walk(source)
        try
          walk
            .iterator()
            .asScala
            .filter(p => Files.isRegularFile(p) && p.toString.endsWith(".class"))
            .toVector
            .sortBy(p => source.relativize(p).toString)
            .foreach { p =>
              digest.update(source.relativize(p).toString.getBytes(UTF_8)); digest.update(0.toByte);
              digest.update(Files.readAllBytes(p))
            }
        finally walk.close()
      } else digest.update(Files.readAllBytes(source))
    }
    digest.digest().map(b => f"${b & 255}%02x").mkString
  }
  private def completion(root: Path): String = StableIds.sha256Hex(
    Files.readString(root.resolve("run-manifest.json"), UTF_8) + "\n" + Files.readString(
      root.resolve("run-metadata.json"),
      UTF_8
    )
  ) + "\n"
  def requireReusable(root: Path, expected: ujson.Obj): Unit = {
    require(
      Files.isRegularFile(root.resolve(marker)),
      "existing Spark output incomplete; refusing overwrite"
    )
    require(
      Files.readString(root.resolve(marker), UTF_8) == completion(root),
      "existing Spark output completion hash mismatch"
    )
    val old = ujson.read(Files.readString(root.resolve("run-metadata.json"), UTF_8))
    Vector(
      "runId",
      "codeVersion",
      "hadoopManifestHash",
      "entityResolutionManifestHash",
      "logicalConfigFingerprint"
    ).foreach { k =>
      require(
        old.obj.get(k).contains(expected(k)),
        s"existing output belongs to a different run: $k"
      )
    }
  }
  def failIfHardIntegrity(
      root: Path,
      integrity: org.apache.spark.sql.DataFrame,
      counters: org.apache.spark.sql.DataFrame
  ): Unit = {
    if (BoundedActions.exists(integrity.filter(col("hardFailure")))) {
      Files.createDirectories(root)
      integrity
        .withColumn("run_id", col("context.runId"))
        .write
        .mode("errorifexists")
        .partitionBy("run_id")
        .parquet(root.resolve("integrity/violations").toString)
      Files.writeString(
        root.resolve("counters.json"),
        ujson.Arr
          .from(BoundedActions.capped(counters.orderBy("name"), 10000).map(r => ujson.read(r.json)))
          .render() + "\n",
        UTF_8
      )
      throw new IllegalStateException(
        "hard graph invariant failed; details persisted in integrity/violations"
      )
    }
  }
  def run(configPath: Path): Either[String, String] = Try {
    val config = SparkAnalyticsConfigLoader
      .load(configPath)
      .fold(e => throw new IllegalArgumentException(e.toString), identity)
    val eventDir =
      Path.of(config.outputRoot).resolve(".event-logs").resolve(UUID.randomUUID().toString)
    Files.createDirectories(eventDir)
    val builder = SparkSession
      .builder()
      .appName("ScholarChain jobs 1–11")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.maxPlanStringLength", "65536")
      .config("spark.ui.retainedTasks", "100")
      .config("spark.sql.shuffle.partitions", config.shufflePartitions)
      .config(
        "spark.sql.warehouse.dir",
        Path.of(config.checkpointDirectory).resolve("warehouse").toString
      )
      .config("spark.eventLog.enabled", "true")
      .config("spark.eventLog.compress", "false")
      .config("spark.eventLog.dir", eventDir.toUri.toString)
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
    if (sys.props.get("spark.master").isEmpty && sys.env.get("SPARK_MASTER").isEmpty)
      builder.master("local[2]")
    val spark = builder.getOrCreate();
    spark.sparkContext.setCheckpointDir(config.checkpointDirectory)
    var output: Option[Path] = None
    var failureContext: Option[SparkRecordContext] = None
    try {
      val verified = Phase6CReaders.load(
        spark,
        Path.of(config.hadoopRunRoot),
        Path.of(config.entityResolutionRunRoot)
      )
      val code = codeFingerprint
      val runId = StableIds
        .sparkAnalyticsRunId(
          verified.hadoopRunId,
          verified.hadoopManifestHash,
          verified.erRunId,
          verified.erManifestHash,
          verified.lineage.entityResolutionPolicyVersion,
          verified.lineage.entityResolutionPolicyHash,
          config.logicalFingerprint,
          code
        )
        .toOption
        .get
      val root = Path.of(config.outputRoot).resolve(runId)
      failureContext =
        Some(SparkRecordContext(SchemaVersions.sparkAnalytics, runId, None, verified.lineage))
      val metadata = ujson.Obj(
        "runId" -> runId,
        "codeVersion" -> code,
        "hadoopRunId" -> verified.hadoopRunId,
        "hadoopManifestHash" -> verified.hadoopManifestHash,
        "entityResolutionRunId" -> verified.erRunId,
        "entityResolutionManifestHash" -> verified.erManifestHash,
        "entityResolutionPolicyVersion" -> verified.lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> verified.lineage.entityResolutionPolicyHash,
        "logicalConfigFingerprint" -> config.logicalFingerprint,
        "identityPolicyVersion" -> config.identityPolicyVersion,
        "representativePolicyVersion" -> config.representativePolicyVersion,
        "graphPolicyVersion" -> config.graphPolicyVersion,
        "physicalConfigFingerprint" -> config.fingerprint,
        "windows" -> ujson.read(CoreJson.compact(config.windows)),
        "seed" -> config.samplingSeed,
        "sparkVersion" -> spark.version,
        "javaVersion" -> System.getProperty("java.version")
      )
      if (Files.exists(root)) {
        requireReusable(root, metadata); s"Reused completed output $root; runId=$runId"
      } else {
        Files.createDirectories(root); output = Some(root)
        Files.createDirectories(root.resolve("plans"))
        Phase6Plans.start(root.resolve("plans"))
        // Disable early throwing only to retain actual hard-violation rows before enforcing the gate.
        val canonical = Phase6CJobs.build(
          spark,
          config.copy(failOnHardInvariant = false),
          verified.input,
          verified.lineage,
          runId
        )
        val integrity = Phase6Export.contextIntegrity(canonical, verified.lineage, runId)
        if (config.failOnHardInvariant) failIfHardIntegrity(root, integrity, canonical.counters)
        // All canonical result tables are checkpointed; release raw JSON/ER reader caches.
        spark.catalog.clearCache()
        val analytics = Phase6DEJobs.build(spark, config, canonical, verified.lineage, runId)
        spark.catalog.clearCache()
        val fg = Phase6FGJobs.build(spark, config, canonical, analytics, verified.lineage, runId)
        Phase6Export.publish(
          spark,
          config,
          canonical,
          analytics,
          fg,
          verified.rejectedLines,
          verified.lineage,
          runId,
          metadata,
          root
        )
        Phase6Report.write(spark, root)
        val provenance = Provenance(
          SchemaVersions.domain,
          SourceType.ScholarChain,
          "spark-jobs1-11",
          None,
          verified.lineage.hadoopSnapshot,
          None,
          None,
          runId,
          Vector(
            "LPA is synchronous and may oscillate, including every two-person component",
            "path lengths are seeded-source estimates; no all-pairs computation"
          )
        )
        val snapshots = CoreJson
          .parse[RunManifest](
            Files.readString(Path.of(config.hadoopRunRoot).resolve("run-manifest.json"), UTF_8)
          )
          .toOption
          .get
          .datasetSnapshots
        val manifest = RunManifest(
          runId,
          SchemaVersions.domain,
          "spark-analytics",
          snapshots,
          config.configSchemaVersion,
          config.fingerprint,
          provenance
        )
        DomainValidation
          .check(manifest)
          .fold(e => throw new IllegalArgumentException(e.toString), identity)
        Files.writeString(
          root.resolve("run-manifest.json"),
          CoreJson.compact(manifest) + "\n",
          UTF_8
        )
        Files.writeString(root.resolve("run-metadata.json"), metadata.render() + "\n", UTF_8)
        spark.stop()
        Files.writeString(
          root.resolve("event-log-summary.json"),
          Phase6EventLog.summarize(eventDir).render() + "\n",
          UTF_8
        )
        Files.writeString(root.resolve(marker), completion(root), UTF_8)
        s"Completed Spark jobs 1–11; root=$root; runId=$runId"
      }
    } catch {
      case error: Throwable =>
        output.foreach { root =>
          val context = failureContext.get
          val failure = IntegrityViolation(
            context,
            "job-hard-failure",
            None,
            Option(error.getMessage).getOrElse(error.getClass.getName),
            true,
            Vector.empty
          )
          val stack = new java.io.StringWriter()
          error.printStackTrace(new java.io.PrintWriter(stack))
          Files.createDirectories(root.resolve("integrity"))
          Files.writeString(
            root.resolve("integrity/failure-stacktrace.txt"),
            stack.toString,
            UTF_8
          );
          Files.writeString(
            root.resolve("integrity/failure.json"),
            CoreJson.compact(failure) + "\n",
            UTF_8
          )
          if (!Files.exists(root.resolve("counters.json")))
            Files.writeString(
              root.resolve("counters.json"),
              CoreJson.compact(
                Vector(SparkCounter(context, "hardInvariantFailures", 1L, Some(failure.detail)))
              ) + "\n",
              UTF_8
            )
        }
        throw error
    } finally {
      Phase6Plans.stop(); if (!spark.sparkContext.isStopped) spark.stop()
      output.foreach(root =>
        if (!Files.exists(root.resolve("event-log-summary.json")))
          Files.writeString(
            root.resolve("event-log-summary.json"),
            Phase6EventLog.summarize(eventDir).render() + "\n",
            UTF_8
          )
      )
    }
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getName))
  def main(args: Array[String]): Unit = {
    require(args.length == 1, "usage: Phase6Main <spark-config.json>");
    run(Path.of(args(0))) match {
      case Right(result) => println(result)
      case Left(error)   => System.err.println(error); sys.exit(1)
    }
  }
}
