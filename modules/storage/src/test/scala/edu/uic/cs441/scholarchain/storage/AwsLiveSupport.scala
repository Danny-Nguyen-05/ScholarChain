package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.{Files, Path, StandardCopyOption}
import java.nio.charset.StandardCharsets.UTF_8
import java.net.URI
import upickle.default.{ReadWriter, read, write}
import scala.collection.mutable

/** Test-only policy. No environment, file, credential or client access occurs on initialization. */
private[storage] final case class AwsLiveSettings(
    environment: String,
    region: String,
    profile: String,
    readerProfile: String,
    loaderProfile: String,
    cleanupProfile: String,
    bucket: String,
    tables: DynamoTables,
    vectorBucket: String,
    vectorIndex: String,
    dimension: Int,
    metric: String,
    neptuneEndpoint: String,
    neptuneRoleArn: String,
    fixturePrefix: String,
    manifestDirectory: Path,
    cleanupAuthorized: Boolean,
    gateReference: String,
    budgetUsd: Double
)
private[storage] object AwsLiveSettings {
  val allowedDimensions: Set[Int] = Set(256, 512, 1024)
  def enabled(environment: Map[String, String]): Boolean = environment
    .get("SCHOLARCHAIN_AWS_ITEST")
    .contains("1") && environment.get("AWS_PROFILE").exists(_.trim.nonEmpty)
  def load(environment: Map[String, String]): AwsLiveSettings = {
    require(enabled(environment), "live integration requires explicit opt-in and profile")
    val configured = environment
      .get("SCHOLARCHAIN_AWS_ITEST_CONFIG")
      .filter(_.trim.nonEmpty)
      .getOrElse(throw new IllegalArgumentException("explicit live config required"))
    val path = Path.of(configured); require(path.isAbsolute, "live config path must be absolute")
    require(
      Files.isRegularFile(path) && Files.size(path) <= 64 * 1024,
      "live config is missing or oversized"
    )
    parse(ujson.read(Files.readString(path, UTF_8)), environment("AWS_PROFILE").trim)
  }
  def parse(json: ujson.Value, profile: String): AwsLiveSettings = {
    require(profile.trim.nonEmpty, "profile required")
    require(
      json("schemaVersion").str == "scholarchain.aws-integration.v1",
      "unsupported live config"
    )
    val environment = json("environment").str
    require(
      environment.nonEmpty && json("approvedEnvironment").str == environment,
      "approved environment mismatch"
    )
    val gate = json("phase14cGateReference").str
    require(
      gate.nonEmpty && json("executionApproved").bool && json("pricingValidated").bool && json(
        "budgetValidated"
      ).bool,
      "Phase 14C execution/pricing/budget gate required"
    )
    val budget = json("incrementalBudgetUsd").num
    require(
      budget.isFinite && budget > 0 && budget <= 5.0,
      "incremental budget must be validated and at most USD 5"
    )
    val endpoint = URI.create(json("neptuneEndpoint").str)
    require(
      endpoint.getScheme == "https" && endpoint.getHost != null && endpoint.getUserInfo == null,
      "HTTPS Neptune endpoint required"
    )
    val tables = read[DynamoTables](json("tables"))
    val names = Vector(
      tables.runLedger,
      tables.entityLinks,
      tables.querySessions,
      tables.evidence,
      tables.artifacts,
      tables.metrics
    )
    require(
      names.forall(_.nonEmpty) && names.distinct.size == 6 && tables.idempotencyIndex.nonEmpty,
      "explicit distinct provisioned tables required"
    )
    val dimension = json("dimension").num.toInt
    // Titan V2 produces only these widths and the provisioned indexes are 256. A different value
    // can never match the live index, so reject it before any credential is resolved.
    require(
      json("dimension").num == dimension && AwsLiveSettings.allowedDimensions(dimension),
      "invalid vector dimension"
    )
    val metric = json("metric").str;
    require(Set("cosine", "euclidean")(metric), "invalid vector metric")
    val index = json("vectorIndex").str;
    require(VectorIndexes.names(index), "unknown course vector index")
    val prefix = json("fixturePrefix").str
    require(
      prefix.nonEmpty && !prefix
        .startsWith("/") && prefix.split('/').forall(s => s.nonEmpty && s != "." && s != ".."),
      "invalid fixture prefix"
    )
    val directory = Path.of(json("manifestDirectory").str);
    require(directory.isAbsolute, "absolute manifest directory required")
    val strings = Vector(
      "region",
      "readerProfile",
      "loaderProfile",
      "cleanupProfile",
      "bucket",
      "vectorBucket",
      "neptuneRoleArn"
    )
    require(
      strings.forall(k => json(k).str.trim.nonEmpty),
      "all resource and role-profile fields required"
    )
    AwsLiveSettings(
      environment,
      json("region").str,
      profile,
      json("readerProfile").str,
      json("loaderProfile").str,
      json("cleanupProfile").str,
      json("bucket").str,
      tables,
      json("vectorBucket").str,
      index,
      dimension,
      metric,
      endpoint.toString,
      json("neptuneRoleArn").str,
      prefix,
      directory,
      json("cleanupAuthorized").bool,
      gate,
      budget
    )
  }
}
private[storage] final case class OwnedLiveItem(
    kind: String,
    resource: String,
    key: String,
    sortKey: String = "",
    expectedHash: String = "",
    versionId: String = "",
    state: String = "planned"
) derives ReadWriter

/** Journal intentions BEFORE each mutation. Only confirmed owned data may be auto-cleaned. */
private[storage] final class LiveRunManifest(
    directory: Path,
    val runId: String,
    settings: AwsLiveSettings
) {
  Files.createDirectories(directory)
  val path: Path = directory.resolve("aws-integration-" + runId.stripPrefix("run:") + ".json")
  private val items = mutable.LinkedHashMap.empty[(String, String, String, String), OwnedLiveItem]
  private var outcome = "started"
  private def id(item: OwnedLiveItem) = (item.kind, item.resource, item.key, item.sortKey)
  private def save(): Unit = {
    val json = ujson.Obj(
      "schemaVersion" -> "scholarchain.aws-integration-owned.v1",
      "runId" -> runId,
      "environment" -> settings.environment,
      "phase14cGateReference" -> settings.gateReference,
      "incrementalBudgetUsd" -> settings.budgetUsd,
      "cleanupAuthorized" -> settings.cleanupAuthorized,
      "outcome" -> outcome,
      "items" -> ujson.Arr.from(
        items.values.map(i =>
          ujson.Obj(
            "kind" -> i.kind,
            "resource" -> i.resource,
            "key" -> i.key,
            "sortKey" -> i.sortKey,
            "expectedHash" -> i.expectedHash,
            "versionId" -> i.versionId,
            "state" -> i.state
          )
        )
      )
    )
    val temp = path.resolveSibling(path.getFileName.toString + ".tmp")
    Files.writeString(temp, json.render() + "\n", UTF_8)
    Files.move(temp, path, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE)
  }
  def plan(item: OwnedLiveItem): Unit = {
    val key = id(item); if (!items.contains(key)) { items(key) = item; save() }
  }
  def record(item: OwnedLiveItem): Unit = {
    require(items.contains(id(item)), "mutation must have a journaled intention");
    items(id(item)) = item; save()
  }
  def all: Vector[OwnedLiveItem] = items.values.toVector
  def finish(state: String): Unit = { outcome = state; save() }
}
private[storage] final case class LiveGraphFixture(
    runId: String,
    nodeIds: Vector[String],
    edgeId: String,
    nodesCsv: String,
    edgesCsv: String
) {
  val window = "all-years"
  val fingerprint: String = StableIds.sha256Hex(nodesCsv + "\n" + edgesCsv)
  def handle(): ValidatedNeptuneExport = {
    val root = Files.createTempDirectory("live-graph-fixture-")
    val scratch = root.resolve("validated");
    Files.createDirectories(scratch.resolve("enriched-nodes"))
    Files.createDirectories(root.resolve("neptune-opencypher-csv/data/coauthor-edges"));
    Files.createDirectories(root.resolve("edges/type=coauthored_with_support"))
    Files.writeString(scratch.resolve("enriched-nodes/part-0.csv"), nodesCsv, UTF_8)
    Files.writeString(
      root.resolve("neptune-opencypher-csv/data/coauthor-edges/part-0.csv"),
      edgesCsv,
      UTF_8
    )
    val supportSchema = org.apache.parquet.schema.MessageTypeParser.parseMessageType(
      "message support { required binary edgeId (UTF8); required binary workId (UTF8); optional int32 year; }"
    )
    val conf = new org.apache.hadoop.conf.Configuration(false);
    conf.set("fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem")
    val writer = org.apache.parquet.hadoop.example.ExampleParquetWriter
      .builder(
        new org.apache.hadoop.fs.Path(
          root.resolve("edges/type=coauthored_with_support/part-0.parquet").toUri
        )
      )
      .withConf(conf)
      .withType(supportSchema)
      .build()
    try
      writer.write(
        new org.apache.parquet.example.data.simple.SimpleGroupFactory(supportSchema)
          .newGroup()
          .append("edgeId", edgeId)
          .append("workId", nodeIds(2))
      )
    finally writer.close()
    new ValidatedNeptuneExport(
      root,
      scratch,
      runId,
      fingerprint,
      3,
      1,
      1,
      Vector("neptune-opencypher-csv/data/coauthor-edges"),
      "edges/type=coauthored_with_support"
    )
  }
}
private[storage] object LiveGraphFixture {
  private def cell(text: String) = "\"" + text.replace("\"", "\"\"") + "\""
  def create(runId: String): LiveGraphFixture = {
    require(runId.matches("run:[0-9a-f-]{36}"), "unique synthetic run ID required")
    val researchers = Vector("a", "b")
      .map(s => "researcher:dblp:" + StableIds.sha256Hex("synthetic-live:" + runId + ":" + s))
      .sorted
    val nodes = researchers :+ ("work:dblp:synthetic/live/" + runId.stripPrefix("run:"))
    val edge = StableIds
      .sparkCoauthorEdgeId(
        researchers(0),
        researchers(1),
        SparkWindow("all-years", None, None, None),
        "synthetic-live-v1"
      )
      .toOption
      .get
    val provenance = Provenance(
      SchemaVersions.domain,
      SourceType.ScholarChain,
      "synthetic-live-integration",
      None,
      "synthetic-live-fixture",
      None,
      None,
      runId,
      Vector(
        "Synthetic live integration fixture; not an observed researcher, collaboration or scientific result."
      )
    )
    val header =
      ":ID,:LABEL,label:String,schemaVersion:String,propertiesJson:String,provenanceJson:String,liveIntegrationRun:String\r\n"
    val rows = nodes.zipWithIndex
      .map((id, n) =>
        Vector(
          id,
          if (n < 2) "RESEARCHER" else "WORK",
          s"Synthetic integration $n",
          SchemaVersions.domain,
          "[]",
          CoreJson.compact(provenance),
          runId
        ).map(cell).mkString(",")
      )
      .mkString("\r\n")
    val edges =
      ":ID,:START_ID,:END_ID,:TYPE,windowId:String,liveIntegrationRun:String,jointPublicationCount:Long,firstCollaborationYear:Int,lastCollaborationYear:Int,windowStartYear:Int,windowEndYear:Int,evidenceTable:String,evidenceEdgeId:String\r\n" + Vector(
        edge,
        nodes(0),
        nodes(1),
        "COAUTHORED_WITH",
        "all-years",
        runId,
        "1"
      ).map(cell).mkString(",") + ",,,,," + Vector("edges/type=coauthored_with_support", edge)
        .map(cell)
        .mkString(",") + "\r\n"
    LiveGraphFixture(runId, nodes, edge, header + rows + "\r\n", edges)
  }
}
