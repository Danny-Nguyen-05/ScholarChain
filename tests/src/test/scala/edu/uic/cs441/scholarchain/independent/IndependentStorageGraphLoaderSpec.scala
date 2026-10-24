package edu.uic.cs441.scholarchain.independent

import com.univocity.parsers.csv.{CsvParser, CsvParserSettings}
import edu.uic.cs441.scholarchain.storage.*
import org.apache.spark.sql.SparkSession
import org.scalatest.BeforeAndAfterAll
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.*

import java.io.StringReader
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path, StandardCopyOption}
import scala.collection.mutable
import scala.jdk.CollectionConverters.*

class IndependentStorageGraphLoaderSpec extends AnyFunSuite with BeforeAndAfterAll {
  import IndependentStorage7BSupport.*
  import IndependentStorageFixtures.*
  import IndependentStorageGraphFixture.{expectedEdges, expectedNodes}
  import StorageResult.*

  private var root: Path = _
  private var exportRoot: Path = _
  private var missingEndpointExport: Path = _
  private var missingSupportExport: Path = _
  private val config = NeptuneLoaderConfig(
    "synthetic-unit-graph",
    "graph",
    "us-east-1",
    "arn:aws:iam::000000000000:role/synthetic-loader",
    pollIntervalMillis = 0,
    timeoutMillis = 100,
    maxPolls = 3,
    retry = RetryConfig(2, 0, 0)
  )

  private final class RecordingLedger extends RunLedger {
    private val delegate = new InMemoryRunLedger()
    val started = mutable.Buffer.empty[String]
    def startRun(id: String): StorageResult[RunRecord] = { started += id; delegate.startRun(id) }
    def recordStage(id: String, stage: String): StorageResult[RunStage] =
      delegate.recordStage(id, stage)
    def recordFailure(
        id: String,
        stage: String,
        retryCount: Int,
        reason: String
    ): StorageResult[RunStage] =
      delegate.recordFailure(id, stage, retryCount, reason)
    def completeStage(id: String, stage: String): StorageResult[RunStage] =
      delegate.completeStage(id, stage)
    def completeRun(id: String): StorageResult[RunRecord] = delegate.completeRun(id)
    def getRun(id: String): StorageResult[RunRecord] = delegate.getRun(id)
  }

  override protected def beforeAll(): Unit = {
    super.beforeAll()
    root = Files.createTempDirectory("independent-storage-graph-")
    val spark = SparkSession
      .builder()
      .master("local[2]")
      .appName("Independent storage graph loader fixture")
      .config("spark.ui.enabled", "false")
      .config("spark.sql.shuffle.partitions", "2")
      .config("spark.sql.session.timeZone", "UTC")
      .config("spark.sql.jsonGenerator.ignoreNullFields", "false")
      .config("spark.sql.warehouse.dir", root.resolve("warehouse").toString)
      .getOrCreate()
    try {
      exportRoot = IndependentStorageGraphFixture.publish(spark, root.resolve("export"))
      missingEndpointExport = IndependentStorageGraphFixture.publish(
        spark,
        root.resolve("missing-endpoint"),
        missingEndpoint = true
      )
      missingSupportExport = IndependentStorageGraphFixture.publish(
        spark,
        root.resolve("missing-support"),
        missingSupport = true
      )
    } finally spark.stop()
  }

  test(
    "hash-bound authoritative edges with a missing endpoint or supporting work are rejected before upload"
  ) {
    Vector(
      missingEndpointExport -> "missing-edge-endpoint",
      missingSupportExport -> "coauthor-support-count-mismatch"
    ).foreach { (source, reason) =>
      val client = stub(classOf[NeptunedataClient])(PartialFunction.empty)
      val objects = new InMemoryObjectStore()
      val result = new NeptuneGraphLoader(
        client,
        objects,
        new InMemoryRunLedger(),
        new InMemoryArtifactRegistry(),
        config,
        new NeptuneExportValidator()
      )
        .submitBulkLoad(GraphLoadManifest(runId, source.toString, "opencypher"))
      assert(result == Rejected(reason), result.toString)
      assert(objects.writeOrder.isEmpty)
    }
  }

  override protected def afterAll(): Unit = {
    try
      if (root != null) {
        val walk = Files.walk(root)
        try
          walk
            .sorted(java.util.Comparator.reverseOrder[Path]())
            .iterator()
            .asScala
            .foreach(Files.deleteIfExists)
        finally walk.close()
      }
    finally super.afterAll()
  }

  private def copyExport(target: Path): Path = {
    val walk = Files.walk(exportRoot)
    try
      walk.iterator().asScala.foreach { original =>
        val destination = target.resolve(exportRoot.relativize(original))
        if (Files.isDirectory(original)) Files.createDirectories(destination)
        else Files.copy(original, destination, StandardCopyOption.REPLACE_EXISTING)
      }
    finally walk.close()
    target
  }

  private def completed = GetLoaderJobStatusResponse
    .builder()
    .status("200 OK")
    .payload(document(ujson.Obj("overallStatus" -> ujson.Obj("status" -> "LOAD_COMPLETED"))))
    .build()

  private def parseCsv(text: String): Vector[Map[String, String]] = {
    val settings = new CsvParserSettings()
    settings.setHeaderExtractionEnabled(true)
    settings.getFormat.setLineSeparator("\r\n")
    settings.setNormalizeLineEndingsWithinQuotes(false)
    new CsvParser(settings)
      .parseAllRecords(new StringReader(text))
      .asScala
      .toVector
      .map(_.toFieldMap().asScala.toMap)
  }

  private def configFile(): Path = {
    val path = root.resolve("synthetic-storage-load.json")
    val tables = DynamoTables(
      "synthetic-runs",
      "synthetic-links",
      "synthetic-sessions",
      "synthetic-evidence",
      "synthetic-artifacts",
      "synthetic-metrics",
      "synthetic-idempotency"
    )
    val json = ujson.Obj(
      "schemaVersion" -> "scholarchain.storage-load.v1",
      "environment" -> "synthetic-approved",
      "approvedEnvironment" -> "synthetic-approved",
      "region" -> "us-east-1",
      "bucket" -> "synthetic-unit-graph",
      "graphPrefix" -> "graph",
      "tables" -> ujson.read(upickle.default.write(tables)),
      "neptune" -> ujson.Obj(
        "iamRoleArn" -> config.iamRoleArn,
        "endpoint" -> "https://synthetic.invalid:8182"
      )
    )
    Files.writeString(path, json.render(), UTF_8)
    path
  }

  test("storage CLI defaults to a validated dry-run with hand-derived expected counts") {
    val output = mutable.Buffer.empty[String]
    val result = StorageLoadMain.run(
      Vector("--manifest", exportRoot.toString, "--config", configFile().toString),
      output += _
    )
    assert(result == 0, output.mkString("\n"))
    assert(
      output.exists(line =>
        line.contains("mode=dry-run") && line.contains("nodes=3 edges=1 support=1")
      )
    )
    assert(output.exists(_.startsWith("PLAN:")))
    assert(!output.exists(_.startsWith("COMPLETE:")))
  }

  test("storage CLI executes the same complete source locally through fake ports") {
    val output = mutable.Buffer.empty[String]
    val result = StorageLoadMain.run(
      Vector(
        "--manifest",
        exportRoot.toString,
        "--config",
        configFile().toString,
        "--execute-fake"
      ),
      output += _
    )
    assert(result == 0, output.mkString("\n"))
    assert(output.exists(_.contains("mode=fake")))
    assert(
      output.exists(line =>
        line.contains("COMPLETE:") && line.contains("cacheWritten=2") &&
          line.contains("graphState=LOAD_COMPLETED")
      )
    )
  }

  test("storage CLI refuses real execution without profile or matching approved environment") {
    val basic = Vector("--manifest", exportRoot.toString, "--config", configFile().toString)
    val refused = Vector(
      basic ++ Vector("--execute-aws", "--environment", "synthetic-approved"),
      basic ++ Vector(
        "--execute-aws",
        "--environment",
        "unapproved",
        "--profile",
        "synthetic-profile"
      ),
      basic ++ Vector("--profile", "synthetic-profile"),
      basic ++ Vector("--execute-fake", "--execute-aws")
    )
    refused.foreach { arguments =>
      val output = mutable.Buffer.empty[String]
      assert(StorageLoadMain.run(arguments, output += _) == 2)
      assert(output.exists(_.startsWith("REFUSED:")))
      assert(!output.exists(_.contains("mode=aws")))
    }
  }

  test(
    "validated bulk load preserves exact Spark-shaped IDs both ways and unchanged reload submits nothing"
  ) {
    val starts = mutable.Buffer.empty[StartLoaderJobRequest]
    val client = stub(classOf[NeptunedataClient]) {
      case ("startLoaderJob", Vector(request: StartLoaderJobRequest)) =>
        starts += request
        StartLoaderJobResponse
          .builder()
          .status("200 OK")
          .payload(Map("loadId" -> "synthetic-load-1").asJava)
          .build()
      case ("getLoaderJobStatus", Vector(_: GetLoaderJobStatusRequest)) => completed
    }
    val objects = new InMemoryObjectStore()
    val ledger = new RecordingLedger()
    val loader = new NeptuneGraphLoader(
      client,
      objects,
      ledger,
      new InMemoryArtifactRegistry(),
      config,
      new NeptuneExportValidator(),
      _ => (),
      () => 0L
    )
    val manifest = GraphLoadManifest(runId, exportRoot.toString, "opencypher")
    val first = loader.submitBulkLoad(manifest)
    assert(StorageResult.successful(first), first.toString)
    assert(starts.size == 1)
    assert(starts.head.formatAsString() == "opencypher")
    assert(starts.head.userProvidedEdgeIds())
    assert(starts.head.iamRoleArn() == config.iamRoleArn)
    assert(starts.head.source().startsWith("s3://synthetic-unit-graph/graph/versions/"))
    assert(starts.head.source().endsWith("/neptune-opencypher-csv/data/"))
    val csv = objects.writeOrder.filter(_.endsWith(".csv")).toVector.map { key =>
      key -> parseCsv(new String(StorageResult.value(objects.get(key)).get.bytes.toArray, UTF_8))
    }
    val nodes = csv.filter(_._1.contains("/nodes/")).flatMap(_._2).map(_(":ID")).toSet
    val edges = csv.filterNot(_._1.contains("/nodes/")).flatMap(_._2).map(_(":ID")).toSet
    assert(nodes.diff(expectedNodes).isEmpty && expectedNodes.diff(nodes).isEmpty)
    assert(edges.diff(expectedEdges).isEmpty && expectedEdges.diff(edges).isEmpty)
    val coauthor = csv.flatMap(_._2).find(_.get(":TYPE").contains("COAUTHORED_WITH")).get
    assert(coauthor(":START_ID") == researcherId && coauthor(":END_ID") == secondResearcherId)
    assert(
      coauthor("firstCollaborationYear:Int") == null && coauthor(
        "lastCollaborationYear:Int"
      ) == null
    )
    assert(coauthor("evidenceEdgeId:String") == IndependentStorageGraphFixture.edge)
    val uploads = objects.writeOrder.toVector
    assert(loader.submitBulkLoad(manifest).isInstanceOf[Unchanged[?]])
    assert(starts.size == 1 && objects.writeOrder.toVector == uploads)
  }

  test("sidecar logical hash tampering is rejected before uploads or loader submission") {
    temporary("independent-sidecar-tamper-") { target =>
      val copied = copyExport(target)
      val sidecar = copied.resolve("load-manifests/neptune-opencypher-csv.json")
      val json = ujson.read(Files.readString(sidecar, UTF_8))
      json("datasets")(0)("contentHash") = "0" * 64
      Files.writeString(sidecar, json.render(), UTF_8)
      val client = stub(classOf[NeptunedataClient])(PartialFunction.empty)
      val objects = new InMemoryObjectStore()
      val result = new NeptuneGraphLoader(
        client,
        objects,
        new InMemoryRunLedger(),
        new InMemoryArtifactRegistry(),
        config,
        new NeptuneExportValidator()
      )
        .submitBulkLoad(GraphLoadManifest(runId, copied.toString, "opencypher"))
      assert(!StorageResult.successful(result))
      assert(objects.writeOrder.isEmpty)
    }
  }

  test("bounded loader polling records timeout failure in the run ledger") {
    var polls = 0
    val client = stub(classOf[NeptunedataClient]) {
      case ("startLoaderJob", Vector(_: StartLoaderJobRequest)) =>
        StartLoaderJobResponse
          .builder()
          .status("200 OK")
          .payload(Map("loadId" -> "synthetic-pending").asJava)
          .build()
      case ("getLoaderJobStatus", Vector(_: GetLoaderJobStatusRequest)) =>
        polls += 1
        GetLoaderJobStatusResponse
          .builder()
          .status("200 OK")
          .payload(
            document(ujson.Obj("overallStatus" -> ujson.Obj("status" -> "LOAD_IN_PROGRESS")))
          )
          .build()
    }
    val ledger = new RecordingLedger()
    val result = new NeptuneGraphLoader(
      client,
      new InMemoryObjectStore(),
      ledger,
      new InMemoryArtifactRegistry(),
      config,
      new NeptuneExportValidator(),
      _ => (),
      () => 0L
    )
      .submitBulkLoad(GraphLoadManifest(runId, exportRoot.toString, "opencypher"))
    assert(!StorageResult.successful(result))
    assert(polls == 3)
    assert(ledger.started.size == 1)
    val run = StorageResult.value(ledger.getRun(ledger.started.head)).get
    assert(run.failures.exists(_.detail.exists(_.contains("timeout"))))
    assert(run.stages.exists(_.state == "failed"))
  }

  private def statusResponse(state: String): GetLoaderJobStatusResponse =
    GetLoaderJobStatusResponse
      .builder()
      .status("200 OK")
      .payload(document(ujson.Obj("overallStatus" -> ujson.Obj("status" -> state))))
      .build()

  private final class RecoveryFixture(states: Vector[String]) {
    val submissions = mutable.Buffer.empty[StartLoaderJobRequest]
    val polledIds = mutable.Buffer.empty[String]
    val objects = new InMemoryObjectStore()
    val ledger = new RecordingLedger()
    private val registry = new InMemoryArtifactRegistry()
    private val remaining = mutable.Queue.from(states)
    private val client = stub(classOf[NeptunedataClient]) {
      case ("startLoaderJob", Vector(request: StartLoaderJobRequest)) =>
        submissions += request
        StartLoaderJobResponse
          .builder()
          .status("200 OK")
          .payload(Map("loadId" -> s"synthetic-recovery-${submissions.size}").asJava)
          .build()
      case ("getLoaderJobStatus", Vector(request: GetLoaderJobStatusRequest)) =>
        polledIds += request.loadId()
        assert(remaining.nonEmpty, "loader polled after the specified state sequence ended")
        statusResponse(remaining.dequeue())
    }
    private val manifest = GraphLoadManifest(runId, exportRoot.toString, "opencypher")
    // A fresh adapter per call models a resumed invocation; only durable ports retain state.
    def invoke(): StorageResult[GraphLoadStatus] = new NeptuneGraphLoader(
      client,
      objects,
      ledger,
      registry,
      config,
      new NeptuneExportValidator(),
      _ => (),
      () => 0L
    ).submitBulkLoad(manifest)
    def currentRun: RunRecord = {
      assert(ledger.started.nonEmpty)
      assert(ledger.started.distinct.size == 1)
      StorageResult.value(ledger.getRun(ledger.started.head)).get
    }
  }

  test("LOAD_FAILED stops after one poll and a resumed invocation submits exactly one new job") {
    val fixture = new RecoveryFixture(Vector("LOAD_FAILED", "LOAD_COMPLETED"))
    val first = fixture.invoke()
    assert(!StorageResult.successful(first), first.toString)
    assert(fixture.submissions.size == 1 && fixture.polledIds == Vector("synthetic-recovery-1"))
    val failed = fixture.currentRun
    assert(failed.failures.size == 1 && failed.failures.head.retryCount == 1)
    assert(failed.failures.head.detail.contains("neptune-load-load_failed"))
    assert(!failed.failures.head.detail.exists(_.contains("timeout")))
    val resumed = fixture.invoke()
    assert(
      StorageResult
        .value(resumed)
        .contains(GraphLoadStatus("synthetic-recovery-2", "LOAD_COMPLETED")),
      resumed.toString
    )
    assert(fixture.submissions.size == 2)
    assert(fixture.submissions.head.modeAsString() == "AUTO")
    assert(fixture.submissions.last.modeAsString() == "NEW")
    assert(fixture.polledIds.toVector == Vector("synthetic-recovery-1", "synthetic-recovery-2"))
    val completedRun = fixture.currentRun
    assert(completedRun.state == "complete")
    assert(completedRun.failures == failed.failures)
    assert(completedRun.stages.find(_.stageKey == "bulk-load").exists(_.retryCount == 1))
    val uploads = fixture.objects.writeOrder.toVector
    assert(fixture.invoke().isInstanceOf[Unchanged[?]])
    assert(fixture.submissions.size == 2 && fixture.polledIds.size == 2)
    assert(fixture.objects.writeOrder.toVector == uploads)
  }

  test(
    "LOAD_COMMITTED_W_WRITE_CONFLICTS is final immediately and a resumed invocation can recover"
  ) {
    val fixture = new RecoveryFixture(Vector("LOAD_COMMITTED_W_WRITE_CONFLICTS", "LOAD_COMPLETED"))
    val first = fixture.invoke()
    assert(!StorageResult.successful(first), first.toString)
    assert(fixture.submissions.size == 1 && fixture.polledIds.size == 1)
    val failure = fixture.currentRun.failures.head
    assert(failure.retryCount == 1)
    assert(failure.detail.contains("neptune-load-load_committed_w_write_conflicts"))
    assert(!failure.detail.exists(_.contains("timeout")))
    assert(StorageResult.successful(fixture.invoke()))
    assert(fixture.submissions.size == 2)
    assert(fixture.submissions.last.modeAsString() == "NEW")
    assert(fixture.currentRun.state == "complete")
    assert(fixture.currentRun.failures == Vector(failure))
  }

  test("deadlock and unknown Neptune states are classified immediately instead of timing out") {
    Vector("LOAD_DATA_DEADLOCK", "LOAD_UNRECOGNIZED_SYNTHETIC_STATE").foreach { state =>
      val fixture = new RecoveryFixture(Vector(state))
      val result = fixture.invoke()
      assert(!StorageResult.successful(result), result.toString)
      assert(fixture.submissions.size == 1 && fixture.polledIds.size == 1)
      val failure = fixture.currentRun.failures.head
      assert(failure.detail.contains("neptune-load-" + state.toLowerCase(java.util.Locale.ROOT)))
      assert(!failure.detail.exists(_.contains("timeout")))
      assert(fixture.currentRun.stages.exists(_.state == "failed"))
    }
  }

  test(
    "timeout recovery polls the existing pending job without resubmission and retains prior failure"
  ) {
    val fixture = new RecoveryFixture(Vector.fill(3)("LOAD_IN_PROGRESS") :+ "LOAD_COMPLETED")
    val first = fixture.invoke()
    assert(!StorageResult.successful(first), first.toString)
    assert(fixture.submissions.size == 1 && fixture.polledIds.size == 3)
    val failure = fixture.currentRun.failures.head
    assert(failure.detail.exists(_.contains("timeout")) && failure.retryCount == 1)
    assert(
      StorageResult
        .value(fixture.invoke())
        .contains(GraphLoadStatus("synthetic-recovery-1", "LOAD_COMPLETED"))
    )
    assert(fixture.submissions.size == 1)
    assert(fixture.polledIds.toVector == Vector.fill(4)("synthetic-recovery-1"))
    assert(fixture.currentRun.state == "complete")
    assert(fixture.currentRun.failures == Vector(failure))
  }
}
