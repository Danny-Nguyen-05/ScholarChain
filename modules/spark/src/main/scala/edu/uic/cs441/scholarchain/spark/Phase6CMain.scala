package edu.uic.cs441.scholarchain.spark

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardCopyOption}
import java.util.UUID
import java.util.concurrent.atomic.AtomicLong
import org.apache.spark.Success
import org.apache.spark.scheduler.{SparkListener, SparkListenerStageCompleted, SparkListenerTaskEnd}
import org.apache.spark.sql.{DataFrame, SparkSession}
import org.apache.spark.sql.execution.ExplainMode
import org.apache.spark.sql.functions.*
import scala.util.Try
import scala.jdk.CollectionConverters.*

/** Local jobs 1–2 entry point. The completed output is never overwritten. */
object Phase6CMain {
  private[spark] val codeVersion = "spark-phase6c-jobs1-2-v2"

  private[spark] def publishTable(table: DataFrame, runId: String): DataFrame = {
    val withRun =
      if (table.columns.contains("runId")) table else table.withColumn("runId", lit(runId))
    if (withRun.columns.contains("schemaVersion")) withRun
    else withRun.withColumn("schemaVersion", lit(SchemaVersions.sparkAnalytics))
  }

  private[spark] def publishRejects(
      rejected: DataFrame,
      runId: String,
      lineage: SparkLineage
  ): DataFrame = publishTable(rejected, runId)
    .withColumn("hadoopRunId", lit(lineage.hadoopRunId))
    .withColumn("hadoopSnapshot", lit(lineage.hadoopSnapshot))
    .withColumn("entityResolutionRunId", lit(lineage.entityResolutionRunId))
    .withColumn(
      "entityResolutionPolicyVersion",
      lit(lineage.entityResolutionPolicyVersion)
    )
    .withColumn("entityResolutionPolicyHash", lit(lineage.entityResolutionPolicyHash))

  /** Small task-event aggregate; no event or row payloads are retained on the driver. */
  private class TaskEventSummary extends SparkListener {
    val completedStages = new AtomicLong()
    val successfulTasks = new AtomicLong()
    val failedTasks = new AtomicLong()
    val executorRunTimeMs = new AtomicLong()
    val shuffleReadBytes = new AtomicLong()
    val shuffleWriteBytes = new AtomicLong()
    val memorySpilledBytes = new AtomicLong()
    val diskSpilledBytes = new AtomicLong()

    override def onStageCompleted(event: SparkListenerStageCompleted): Unit =
      completedStages.incrementAndGet()

    override def onTaskEnd(event: SparkListenerTaskEnd): Unit = {
      if (event.reason == Success) successfulTasks.incrementAndGet()
      else failedTasks.incrementAndGet()
      Option(event.taskMetrics).foreach { metrics =>
        executorRunTimeMs.addAndGet(metrics.executorRunTime)
        shuffleReadBytes.addAndGet(metrics.shuffleReadMetrics.totalBytesRead)
        shuffleWriteBytes.addAndGet(metrics.shuffleWriteMetrics.bytesWritten)
        memorySpilledBytes.addAndGet(metrics.memoryBytesSpilled)
        diskSpilledBytes.addAndGet(metrics.diskBytesSpilled)
      }
    }

    def json: ujson.Value = ujson.Obj(
      "source" -> "SparkListener task and stage events; local Spark event file disabled",
      "completedStages" -> ujson.Num(completedStages.get().toDouble),
      "successfulTasks" -> ujson.Num(successfulTasks.get().toDouble),
      "failedTasks" -> ujson.Num(failedTasks.get().toDouble),
      "executorRunTimeMs" -> ujson.Num(executorRunTimeMs.get().toDouble),
      "shuffleReadBytes" -> ujson.Num(shuffleReadBytes.get().toDouble),
      "shuffleWriteBytes" -> ujson.Num(shuffleWriteBytes.get().toDouble),
      "memorySpilledBytes" -> ujson.Num(memorySpilledBytes.get().toDouble),
      "diskSpilledBytes" -> ujson.Num(diskSpilledBytes.get().toDouble)
    )
  }

  private[spark] def requireReusable(root: Path, expected: ujson.Obj): Unit = {
    require(
      Files.isRegularFile(root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE")),
      "existing Spark output is incomplete; refusing overwrite"
    )
    val oldText = Files.readString(root.resolve("run-manifest.json"), UTF_8)
    val old = ujson.read(oldText)
    val marker = Files.readString(root.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"), UTF_8)
    require(
      marker == StableIds.sha256Hex(oldText) + "\n",
      "existing Spark output completion hash mismatch"
    )
    val identityKeys = Vector(
      "schemaVersion",
      "runId",
      "codeVersion",
      "hadoopRunId",
      "hadoopManifestHash",
      "entityResolutionRunId",
      "entityResolutionManifestHash",
      "entityResolutionPolicyVersion",
      "entityResolutionPolicyHash",
      "logicalConfigFingerprint"
    )
    require(
      identityKeys.forall(key => old.obj.get(key).contains(expected(key))),
      "existing Spark output belongs to a different run/config"
    )
  }

  def run(configPath: Path): Either[String, String] = Try {
    val config = SparkAnalyticsConfigLoader
      .load(configPath)
      .fold(e => throw new IllegalArgumentException(e.toString), identity)
    val builder = SparkSession
      .builder()
      .appName("ScholarChain Phase 6C")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.ui.retainedExecutions", "4")
      .config("spark.ui.retainedJobs", "10")
      .config("spark.ui.retainedStages", "10")
      .config("spark.ui.retainedTasks", "100")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.shuffle.partitions", config.shufflePartitions)
      .config(
        "spark.sql.warehouse.dir",
        Path
          .of(config.checkpointDirectory)
          .resolve("warehouse")
          .toString
      )
    if (sys.props.get("spark.master").isEmpty && sys.env.get("SPARK_MASTER").isEmpty)
      builder.master("local[2]")
    val spark = builder.getOrCreate()
    spark.sparkContext.setCheckpointDir(config.checkpointDirectory)
    val eventSummary = new TaskEventSummary()
    spark.sparkContext.addSparkListener(eventSummary)
    try {
      val verified = Phase6CReaders.load(
        spark,
        Path.of(config.hadoopRunRoot),
        Path.of(config.entityResolutionRunRoot)
      )
      val runId = StableIds
        .sparkAnalyticsRunId(
          verified.hadoopRunId,
          verified.hadoopManifestHash,
          verified.erRunId,
          verified.erManifestHash,
          verified.lineage.entityResolutionPolicyVersion,
          verified.lineage.entityResolutionPolicyHash,
          config.logicalFingerprint,
          codeVersion
        )
        .fold(e => throw new IllegalArgumentException(e.toString), identity)
      val root = Path.of(config.outputRoot).resolve(runId)
      val expected = ujson.Obj(
        "schemaVersion" -> SchemaVersions.sparkAnalytics,
        "runId" -> runId,
        "codeVersion" -> codeVersion,
        "hadoopRunId" -> verified.hadoopRunId,
        "hadoopManifestHash" -> verified.hadoopManifestHash,
        "entityResolutionRunId" -> verified.erRunId,
        "entityResolutionManifestHash" -> verified.erManifestHash,
        "entityResolutionPolicyVersion" -> verified.lineage.entityResolutionPolicyVersion,
        "entityResolutionPolicyHash" -> verified.lineage.entityResolutionPolicyHash,
        "logicalConfigFingerprint" -> config.logicalFingerprint,
        "physicalConfigFingerprint" -> config.fingerprint,
        "windows" -> ujson.Arr.from(config.windows.map(w => ujson.Str(w.windowId))),
        "seed" -> ujson.Num(config.samplingSeed.toDouble),
        "sparkVersion" -> spark.version,
        "javaVersion" -> System.getProperty("java.version")
      )
      if (Files.exists(root)) {
        requireReusable(root, expected)
        s"Reused completed 6C output $root; runId=$runId"
      } else {
        val result = Phase6CJobs.build(spark, config, verified.input, verified.lineage, runId)
        val publishedRejects = publishRejects(verified.rejectedLines, runId, verified.lineage)
        val rejectedCount = BoundedActions.count(publishedRejects)
        val rejectedCounter = result.counters
          .limit(1)
          .withColumn("name", lit("malformedJsonLines"))
          .withColumn("value", lit(rejectedCount))
          .withColumn("detail", lit("retained under input_rejects"))
        Files.createDirectories(root.getParent)
        val partial =
          root.resolveSibling("." + root.getFileName.toString + ".partial-" + UUID.randomUUID())
        Files.createDirectory(partial)
        val tables = Vector(
          "nodes/researcher" -> result.researchers,
          "nodes/author_mention" -> result.mentions,
          "nodes/work" -> result.works,
          "nodes/graph" -> result.graphNodes,
          "edges/graph" -> result.graphEdges,
          "intermediate/canonical_works" -> result.canonicalWorks,
          "intermediate/memberships" -> result.memberships,
          "edges/coauthored_with" -> result.edges,
          "edges/coauthored_with_support" -> result.support,
          "integrity" -> result.integrity,
          "input_rejects" -> publishedRejects,
          "counters" -> result.counters.unionByName(rejectedCounter)
        ).map { case (name, table) => name -> publishTable(table, runId) }
        val counts = ujson.Obj()
        try {
          val plans = partial.resolve("plans")
          Files.createDirectory(plans)
          tables.foreach { case (name, table) =>
            val count = BoundedActions.count(table)
            counts(name) = ujson.Num(count.toDouble)
            Files.writeString(
              plans.resolve(name.replace('/', '_') + ".txt"),
              table.queryExecution.explainString(ExplainMode.fromString("formatted")) + "\n",
              UTF_8
            )
            table.write.mode("errorifexists").parquet(partial.resolve(name).toString)
          }
          expected("inputRejectCount") = ujson.Num(rejectedCount.toDouble)
          expected("tableCounts") = counts
          Files.writeString(
            partial.resolve("event-log-summary.json"),
            eventSummary.json.render(indent = 2) + "\n",
            UTF_8
          )
          val manifest = expected.render(indent = 2) + "\n"
          Files.writeString(partial.resolve("run-manifest.json"), manifest, UTF_8)
          Files.writeString(
            partial.resolve("_SCHOLARCHAIN_SPARK_COMPLETE"),
            StableIds.sha256Hex(manifest) + "\n",
            UTF_8
          )
          Files.move(partial, root, StandardCopyOption.ATOMIC_MOVE)
          s"Completed 6C jobs 1–2 at $root; runId=$runId; counts=${counts.render()}"
        } catch {
          case error: Throwable =>
            val walk = Files.walk(partial)
            try walk.iterator().asScala.toVector.reverse.foreach(Files.deleteIfExists(_))
            finally walk.close()
            throw error
        }
      }
    } finally spark.stop()
  }.toEither.left.map(e => Option(e.getMessage).getOrElse(e.getClass.getSimpleName))

  def main(args: Array[String]): Unit = {
    if (args.length != 1) {
      System.err.println("Usage: Phase6CMain SPARK_CONFIG_JSON")
      sys.exit(2)
    }
    run(Path.of(args(0))) match {
      case Right(message) => println(message)
      case Left(error)    => System.err.println("Phase 6C failed: " + error); sys.exit(2)
    }
  }
}
