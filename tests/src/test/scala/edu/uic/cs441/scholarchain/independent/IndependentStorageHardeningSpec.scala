package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.{StorageConfig as AdapterConfig, *}
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.*

import scala.collection.mutable
import scala.jdk.CollectionConverters.*

/** Independent wire checks exercise public adapters, never package-private codecs. */
class IndependentStorageHardeningSpec extends AnyFunSuite {
  import IndependentStorage7BSupport.*
  import IndependentStorageFixtures.*
  import StorageResult.*

  private val config = AdapterConfig(
    "synthetic-hardening",
    DynamoTables("runs", "links", "sessions", "evidence", "artifacts", "metrics", "idempotency"),
    retry = RetryConfig(2, 0, 0)
  )
  private val keys = Map(
    "runs" -> ("runId", "stageKey"),
    "links" -> ("entityType#normalizedKey", "policyVersion#sourceId"),
    "sessions" -> ("queryId", "itemType"),
    "evidence" -> ("evidenceId", "part"),
    "artifacts" -> ("artifactId", "version"),
    "metrics" -> ("researcherId", "windowId")
  )

  private final class WireStore {
    val rows = mutable.Map.empty[(String, String, String), Map[String, AttributeValue]]
    def address(
        table: String,
        item: java.util.Map[String, AttributeValue]
    ): (String, String, String) = {
      val (pk, sk) = keys(table)
      (table, item.get(pk).s(), item.get(sk).s())
    }
    private def save(table: String, item: java.util.Map[String, AttributeValue]): Unit =
      rows(address(table, item)) = item.asScala.toMap
    val client: DynamoDbClient = stub(classOf[DynamoDbClient]) {
      case ("putItem", Vector(request: PutItemRequest)) =>
        save(request.tableName(), request.item())
        PutItemResponse.builder().build()
      case ("transactWriteItems", Vector(request: TransactWriteItemsRequest)) =>
        request.transactItems().asScala.foreach(t => save(t.put().tableName(), t.put().item()))
        TransactWriteItemsResponse.builder().build()
      case ("getItem", Vector(request: GetItemRequest)) =>
        GetItemResponse
          .builder()
          .item(rows.getOrElse(address(request.tableName(), request.key()), Map.empty).asJava)
          .build()
      case ("query", Vector(request: QueryRequest)) =>
        val pk = request.expressionAttributeValues().get(":pk").s()
        val selected = rows.iterator.collect {
          case ((table, partition, _), item) if table == request.tableName() && partition == pk =>
            item.asJava
        }.toVector
        QueryResponse.builder().items(selected.asJava).build()
    }
    def assertEnvelopes(): Unit = rows.values.foreach { row =>
      val json = ujson.read(row("payload").s())
      assert(json("schemaVersion") == ujson.Str("scholarchain.storage.v1"))
      assert(json("record").isInstanceOf[ujson.Obj])
    }
  }

  test(
    "entity link wire round trip retains candidate confidence, affiliations and source evidence"
  ) {
    val wire = new WireStore()
    val cache = new DynamoEntityLinkCache(wire.client, config)
    val expected = EntityLink(
      "name",
      "synthetic α",
      policyVersion,
      "source:synthetic",
      researcherId,
      "Synthetic α",
      Vector("institution:synthetic"),
      Some(0.75),
      runId,
      Vector("edge:synthetic")
    )
    assert(cache.putLink(expected) == Written(expected))
    assert(cache.lookupByNormalizedName("Synthetic α") == Found(Vector(expected)))
    wire.assertEnvelopes()
  }

  test("query session wire round trip preserves revision, raw payload and explicit TTL") {
    val wire = new WireStore()
    val sessions = new DynamoQuerySessionStore(
      wire.client,
      config.copy(disposableSessionTtlSeconds = Some(60)),
      () => 1000L
    )
    val created = sessions.createIfAbsent("query:synthetic", "idem:synthetic")
    assert(
      created == Written(
        QuerySession("query:synthetic", "idem:synthetic", "created", 0, "{}", Some(1060))
      )
    )
    val expected = QuerySession(
      "query:synthetic",
      "idem:synthetic",
      "complete",
      1,
      "{\"text\":\"α\\r\\nline\"}",
      Some(1060)
    )
    assert(sessions.update(expected, 0) == Written(expected))
    assert(sessions.get(expected.queryId) == Found(expected))
    wire.assertEnvelopes()
  }

  test(
    "artifact and metric envelopes retain immutable version hashes and exact qualified payloads"
  ) {
    val wire = new WireStore()
    val artifacts = new DynamoArtifactRegistry(wire.client, config)
    val artifact =
      ArtifactRecord("artifact:synthetic", "v0001", "s3://synthetic/versions/v0001/text", "a" * 64)
    assert(
      artifacts.register(
        artifact.artifactId,
        artifact.version,
        artifact.uri,
        artifact.hash
      ) == Written(artifact)
    )
    assert(artifacts.get(artifact.artifactId, artifact.version) == Found(artifact))
    val metrics = new DynamoResearcherMetricStore(wire.client, config)
    val record = ResearcherMetricRecord(
      researcherId,
      "all-years",
      policyVersion,
      runId,
      CoreJson.compact(IndependentStorageFixtures.metrics),
      """{"converged":false,"P90":"approximate"}"""
    )
    assert(metrics.put(record) == Written(record))
    assert(metrics.get(researcherId, "all-years") == Found(record))
    wire.assertEnvelopes()
  }

  test("run ledger wire round trip retains stage failures and recovered retry history") {
    val wire = new WireStore()
    val ledger = new DynamoRunLedger(wire.client, config)
    assert(ledger.startRun(runId) == Written(RunRecord(runId, "running", Vector.empty)))
    assert(ledger.recordStage(runId, "load") == Written(RunStage("load", "running", 0, None)))
    val failed = RunStage("load", "failed", 1, Some("synthetic-throttle"))
    assert(ledger.recordFailure(runId, "load", 1, "synthetic-throttle") == Written(failed))
    assert(ledger.recordStage(runId, "load") == Written(RunStage("load", "running", 1, None)))
    assert(ledger.completeStage(runId, "load") == Written(RunStage("load", "complete", 1, None)))
    assert(StorageResult.successful(ledger.completeRun(runId)))
    val actual = StorageResult.value(ledger.getRun(runId)).get
    assert(actual.state == "complete" && actual.revision == 5)
    assert(actual.stages == Vector(RunStage("load", "complete", 1, None)))
    assert(actual.failures == Vector(failed))
    wire.assertEnvelopes()
  }

  private def bundle(text: String): EvidenceBundle = {
    val item = EvidenceItem(
      "chunk:" + "f" * 64,
      SchemaVersions.domain,
      EvidenceType.WorkMetadata,
      Some("work:dblp:independent/synthetic/storage"),
      "synthetic://evidence",
      None,
      None,
      score = 0.0,
      text = Some(text),
      provenance = provenance
    )
    EvidenceBundle(
      "bundle:synthetic-hardening",
      SchemaVersions.domain,
      "query:synthetic",
      Vector(item),
      Vector(researcherId),
      Vector.empty,
      None,
      "Synthetic evidence only.",
      provenance
    )
  }

  test("inline evidence wire envelope round trips source text and validates its digest") {
    val wire = new WireStore()
    val objects = new InMemoryObjectStore()
    val store = new DynamoEvidenceBundleStore(wire.client, config, objects)
    val expected = bundle("Synthetic α\r\ntext\t\"quoted\" \\ source")
    assert(store.put(expected) == Written(expected))
    assert(store.get(expected.bundleId) == Found(expected))
    assert(objects.writeOrder.isEmpty)
    val raw = wire.rows.values.head.apply("payload").s()
    val pointer = ujson.read(raw)("record")
    assert(pointer("inlineJson").str == CoreJson.compact(expected))
    assert(pointer("objectKey") == ujson.Null)
    wire.assertEnvelopes()
  }

  test(
    "large evidence stores one immutable object and a hash-bound pointer instead of inline text"
  ) {
    val wire = new WireStore()
    val objects = new InMemoryObjectStore()
    val store =
      new DynamoEvidenceBundleStore(wire.client, config.copy(maxInlineEvidenceBytes = 1), objects)
    val expected = bundle("Synthetic α\r\nlarge source")
    assert(store.put(expected) == Written(expected))
    assert(store.get(expected.bundleId) == Found(expected))
    assert(objects.writeOrder.size == 1)
    val pointer = ujson.read(wire.rows.values.head.apply("payload").s())("record")
    assert(pointer("inlineJson") == ujson.Null)
    assert(pointer("objectKey").str == objects.writeOrder.head)
    val bytes = StorageResult.value(objects.get(pointer("objectKey").str)).get
    assert(pointer("sha256").str == bytes.head.sha256)
    wire.assertEnvelopes()
  }

  test(
    "all six Dynamo tables reject unsupported envelope versions, corrupt JSON and missing payload metadata"
  ) {
    val lookups: Vector[(String, DynamoDbClient => StorageResult[?])] = Vector(
      "runs" -> (c => new DynamoRunLedger(c, config).getRun(runId)),
      "links" -> (c => new DynamoEntityLinkCache(c, config).lookupByNormalizedName("synthetic")),
      "sessions" -> (c => new DynamoQuerySessionStore(c, config).get("synthetic")),
      "evidence" -> (c =>
        new DynamoEvidenceBundleStore(c, config, new InMemoryObjectStore()).get("synthetic")
      ),
      "artifacts" -> (c => new DynamoArtifactRegistry(c, config).get("synthetic", "v1")),
      "metrics" -> (c => new DynamoResearcherMetricStore(c, config).get(researcherId, "all-years"))
    )
    val payloads = Vector(
      Some("""{"schemaVersion":"unsupported.v99","record":{}}"""),
      Some("{corrupt"),
      Some("""{"schemaVersion":"scholarchain.storage.v1","record":{}}"""),
      None
    )
    lookups.foreach { (table, fetch) =>
      payloads.foreach { payload =>
        val (pk, sk) = keys(table)
        val item = Map(
          pk -> AttributeValue.builder().s("synthetic").build(),
          sk -> AttributeValue.builder().s("synthetic").build()
        ) ++ payload.map(p => "payload" -> AttributeValue.builder().s(p).build())
        val sdk = stub(classOf[DynamoDbClient]) {
          case ("getItem", Vector(_: GetItemRequest)) =>
            GetItemResponse.builder().item(item.asJava).build()
          case ("query", Vector(_: QueryRequest)) =>
            QueryResponse.builder().items(Vector(item.asJava).asJava).build()
        }
        val result = fetch(sdk)
        assert(!StorageResult.successful(result), s"table=$table payload=$payload result=$result")
      }
    }
  }

  test("metric and entity adapters reject malformed required metadata before issuing a write") {
    val sdk = stub(classOf[DynamoDbClient])(PartialFunction.empty)
    val metricStore = new DynamoResearcherMetricStore(sdk, config)
    val record = ResearcherMetricRecord(researcherId, "all-years", policyVersion, runId, "{}", "{}")
    Vector(
      record.copy(runId = ""),
      record.copy(windowId = ""),
      record.copy(payloadJson = "{broken"),
      record.copy(qualificationsJson = "{broken")
    ).foreach(r => assert(!StorageResult.successful(metricStore.put(r))))
    val links = new DynamoEntityLinkCache(sdk, config)
    val link = EntityLink(
      "name",
      "synthetic",
      policyVersion,
      "synthetic",
      researcherId,
      "Synthetic",
      Vector.empty,
      None,
      runId,
      Vector.empty
    )
    Vector(
      link.copy(normalizedKey = ""),
      link.copy(sourceId = ""),
      link.copy(confidence = Some(Double.NaN)),
      link.copy(confidence = Some(1.1))
    ).foreach(r => assert(!StorageResult.successful(links.putLink(r))))
  }
}
