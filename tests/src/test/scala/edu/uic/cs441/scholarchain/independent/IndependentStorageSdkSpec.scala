package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.core.ResponseInputStream
import software.amazon.awssdk.http.AbortableInputStream
import software.amazon.awssdk.core.sync.RequestBody
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.*
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.*

import java.io.ByteArrayInputStream
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.nio.charset.StandardCharsets.UTF_8
import scala.collection.mutable
import scala.jdk.CollectionConverters.*

/** SDK interfaces are dynamic stubs. Unexpected calls fail the test; no client can reach a network.
  */
class IndependentStorageSdkSpec extends AnyFunSuite {
  import IndependentStorageFixtures.*
  import StorageResult.*

  private val config = StorageConfig(
    "synthetic-unit-bucket",
    DynamoTables(
      "synthetic-runs",
      "synthetic-links",
      "synthetic-sessions",
      "synthetic-evidence",
      "synthetic-artifacts",
      "synthetic-metrics",
      "synthetic-idempotency-index"
    ),
    RetryConfig(maxAttempts = 2, baseDelayMillis = 0, maxDelayMillis = 0)
  )

  private def stub[A](
      kind: Class[A]
  )(handler: PartialFunction[(String, Vector[AnyRef]), AnyRef]): A = {
    val proxy = Proxy.newProxyInstance(
      kind.getClassLoader,
      Array(kind),
      new InvocationHandler {
        def invoke(self: AnyRef, method: Method, args: Array[AnyRef]): AnyRef = {
          val call = method.getName -> Option(args).map(_.toVector).getOrElse(Vector.empty)
          if (handler.isDefinedAt(call)) handler(call)
          else throw new AssertionError(s"Unexpected SDK call: ${method.getName}")
        }
      }
    )
    kind.cast(proxy)
  }

  private def stream(
      response: GetObjectResponse,
      bytes: Array[Byte]
  ): ResponseInputStream[GetObjectResponse] =
    new ResponseInputStream(response, AbortableInputStream.create(new ByteArrayInputStream(bytes)))

  private def rejected(result: StorageResult[?]): Boolean = result match {
    case Rejected(_) => true
    case _           => false
  }

  test("S3 read checks SHA-256 against bytes and rejects missing or malformed hash metadata") {
    val body = "abc".getBytes(UTF_8)
    val wrongOrMissing =
      Vector(Map.empty[String, String], Map("sha256" -> "invalid"), Map("sha256" -> "0" * 64))
    wrongOrMissing.foreach { metadata =>
      val client = stub(classOf[S3Client]) {
        case ("headObject", Vector(request: HeadObjectRequest)) =>
          assert(request.bucket() == config.bucket)
          assert(request.key() == "synthetic/versions/001/object")
          HeadObjectResponse
            .builder()
            .contentLength(3L)
            .contentType("text/plain")
            .metadata(metadata.asJava)
            .build()
        case ("getObject", Vector(request: GetObjectRequest)) =>
          assert(request.bucket() == config.bucket)
          assert(request.key() == "synthetic/versions/001/object")
          stream(
            GetObjectResponse
              .builder()
              .contentLength(3L)
              .contentType("text/plain")
              .metadata(metadata.asJava)
              .build(),
            body
          )
      }
      assert(rejected(new S3ObjectStore(client, config).get("synthetic/versions/001/object")))
    }
  }

  test("S3 valid read preserves caller metadata and missing objects return Missing") {
    val hash = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    val client = stub(classOf[S3Client]) {
      case ("headObject", Vector(request: HeadObjectRequest)) if request.key().endsWith("object") =>
        HeadObjectResponse
          .builder()
          .contentLength(3L)
          .contentType("text/plain")
          .metadata(Map("sha256" -> hash, "run-id" -> runId).asJava)
          .build()
      case ("headObject", Vector(_: HeadObjectRequest)) =>
        throw NoSuchKeyException.builder().statusCode(404).build()
      case ("getObject", Vector(request: GetObjectRequest)) if request.key().endsWith("object") =>
        stream(
          GetObjectResponse
            .builder()
            .contentLength(3L)
            .contentType("text/plain")
            .metadata(Map("sha256" -> hash, "run-id" -> runId).asJava)
            .build(),
          "abc".getBytes(UTF_8)
        )
      case ("getObject", Vector(_: GetObjectRequest)) =>
        throw NoSuchKeyException.builder().statusCode(404).build()
    }
    val store = new S3ObjectStore(client, config)
    val objectValue = StorageResult.value(store.get("synthetic/versions/001/object")).get
    assert(objectValue.bytes == "abc".getBytes(UTF_8).toVector)
    assert(objectValue.head.sha256 == hash)
    assert(objectValue.head.metadata("run-id") == runId)
    assert(store.get("synthetic/versions/001/missing") == Missing)
  }

  test("S3 writes bind versioned key, SHA metadata and atomic create condition") {
    val requests = mutable.Buffer.empty[PutObjectRequest]
    val client = stub(classOf[S3Client]) {
      case ("putObject", Vector(request: PutObjectRequest, body: RequestBody)) =>
        requests += request
        val stream = body.contentStreamProvider().newStream()
        try assert(new String(stream.readAllBytes(), UTF_8) == "abc")
        finally stream.close()
        PutObjectResponse.builder().build()
    }
    val store = new S3ObjectStore(client, config)
    assert(
      store
        .put(
          "synthetic/versions/001/object",
          "abc".getBytes(UTF_8).toVector,
          "text/plain",
          Map("run-id" -> runId)
        )
        .isInstanceOf[Written[?]]
    )
    assert(requests.size == 1)
    val request = requests.head
    assert(request.bucket() == config.bucket)
    assert(request.key() == "synthetic/versions/001/object")
    assert(request.ifNoneMatch() == "*")
    assert(
      request
        .metadata()
        .get("sha256") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert(request.metadata().get("run-id") == runId)
  }

  test("S3 bounds a stream whose body exceeds its advertised content length and closes it") {
    val hash = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    var bytesRead = 0
    var closed = false
    val body = new ByteArrayInputStream(Array.fill[Byte](100)(1.toByte)) {
      override def read(target: Array[Byte], offset: Int, length: Int): Int = {
        val n = super.read(target, offset, length)
        if (n > 0) bytesRead += n
        n
      }
      override def close(): Unit = { closed = true; super.close() }
    }
    val client = stub(classOf[S3Client]) {
      case ("headObject", Vector(_: HeadObjectRequest)) =>
        HeadObjectResponse
          .builder()
          .contentLength(3L)
          .contentType("text/plain")
          .metadata(Map("sha256" -> hash).asJava)
          .build()
      case ("getObject", Vector(_: GetObjectRequest)) =>
        new ResponseInputStream(
          GetObjectResponse
            .builder()
            .contentLength(3L)
            .contentType("text/plain")
            .metadata(Map("sha256" -> hash).asJava)
            .build(),
          AbortableInputStream.create(body)
        )
    }
    assert(
      rejected(
        new S3ObjectStore(client, config.copy(maxObjectBytes = 4))
          .get("synthetic/versions/001/object")
      )
    )
    assert(bytesRead == 5)
    assert(closed)
  }

  test("S3 retries a transient SDK failure within the configured bound without real sleeping") {
    var attempts = 0
    val client = stub(classOf[S3Client]) { case ("headObject", Vector(_: HeadObjectRequest)) =>
      attempts += 1
      if (attempts == 1)
        throw S3Exception.builder().statusCode(503).message("synthetic-error").build()
      HeadObjectResponse
        .builder()
        .contentLength(3L)
        .contentType("text/plain")
        .metadata(
          Map("sha256" -> "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad").asJava
        )
        .build()
    }
    val result = new S3ObjectStore(client, config).head("synthetic/versions/001/object")
    assert(result.isInstanceOf[Retried[?]])
    assert(StorageResult.successful(result))
    assert(attempts == 2)
  }

  test("Dynamo immutable writes use conditional create and read the original on conflict") {
    var saved: Map[String, AttributeValue] = Map.empty
    val puts = mutable.Buffer.empty[PutItemRequest]
    val client = stub(classOf[DynamoDbClient]) {
      case ("putItem", Vector(request: PutItemRequest)) =>
        puts += request
        if (saved.nonEmpty) throw ConditionalCheckFailedException.builder().build()
        saved = request.item().asScala.toMap
        PutItemResponse.builder().build()
      case ("getItem", Vector(request: GetItemRequest)) =>
        assert(request.consistentRead())
        GetItemResponse.builder().item(saved.asJava).build()
    }
    val registry: ArtifactRegistry = new DynamoArtifactRegistry(client, config)
    assert(
      registry
        .register("synthetic-artifact", "0001", "synthetic://one", "a" * 64)
        .isInstanceOf[Written[?]]
    )
    assert(
      registry
        .register("synthetic-artifact", "0001", "synthetic://one", "a" * 64)
        .isInstanceOf[Unchanged[?]]
    )
    assert(rejected(registry.register("synthetic-artifact", "0001", "synthetic://one", "b" * 64)))
    assert(puts.size == 3)
    puts.foreach { request =>
      assert(request.tableName() == config.tables.artifacts)
      assert(
        request.conditionExpression() == "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
      )
      assert(
        request.expressionAttributeNames().asScala.toMap == Map(
          "#pk" -> "artifactId",
          "#sk" -> "version"
        )
      )
      assert(!request.item().containsKey("expiresAt"))
    }
    assert(saved("artifactId").s() == "synthetic-artifact")
    assert(saved("version").s() == "0001")
    assert(StorageResult.value(registry.get("synthetic-artifact", "0001")).get.hash == "a" * 64)
  }

  test("Dynamo point reads reject unknown envelope schema and corrupt payload") {
    val examples = Vector(
      "{broken",
      """{"schemaVersion":"unknown.v99","record":{}}""",
      """{"schemaVersion":"scholarchain.storage.v1","record":{"artifactId":17}}"""
    )
    examples.foreach { payload =>
      val client = stub(classOf[DynamoDbClient]) { case ("getItem", Vector(_: GetItemRequest)) =>
        GetItemResponse
          .builder()
          .item(
            Map(
              "artifactId" -> AttributeValue.builder().s("synthetic-artifact").build(),
              "version" -> AttributeValue.builder().s("0001").build(),
              "payload" -> AttributeValue.builder().s(payload).build()
            ).asJava
          )
          .build()
      }
      assert(rejected(new DynamoArtifactRegistry(client, config).get("synthetic-artifact", "0001")))
    }
  }

  test("Dynamo idempotency lookup uses configured GSI and the raw key as a parameter") {
    val requests = mutable.Buffer.empty[QueryRequest]
    val userKey = "synthetic' OR 1=1 --"
    val client = stub(classOf[DynamoDbClient]) { case ("query", Vector(request: QueryRequest)) =>
      requests += request
      QueryResponse
        .builder()
        .items(java.util.Collections.emptyList[java.util.Map[String, AttributeValue]]())
        .build()
    }
    val sessions: QuerySessionStore = new DynamoQuerySessionStore(client, config)
    assert(sessions.lookupByIdempotencyKey(userKey) == Missing)
    assert(requests.size == 1)
    val request = requests.head
    assert(request.tableName() == config.tables.querySessions)
    assert(request.indexName() == config.tables.idempotencyIndex)
    assert(!request.keyConditionExpression().contains(userKey))
    assert(request.expressionAttributeValues().values().asScala.exists(_.s() == userKey))
    assert(!request.consistentRead())
  }

  test(
    "Dynamo query creation atomically reserves idempotency and limits TTL to configured sessions"
  ) {
    Vector(None, Some(60L)).foreach { ttl =>
      val requests = mutable.Buffer.empty[TransactWriteItemsRequest]
      val client = stub(classOf[DynamoDbClient]) {
        case ("transactWriteItems", Vector(request: TransactWriteItemsRequest)) =>
          requests += request
          TransactWriteItemsResponse.builder().build()
      }
      val sessions = new DynamoQuerySessionStore(
        client,
        config.copy(disposableSessionTtlSeconds = ttl),
        () => 1000L
      )
      val result = sessions.createIfAbsent("synthetic-query", "synthetic-idempotency")
      assert(result.isInstanceOf[Written[?]])
      assert(requests.size == 1)
      val items = requests.head.transactItems().asScala.toVector.map(_.put())
      assert(items.size == 2)
      assert(items.forall(_.tableName() == config.tables.querySessions))
      assert(items.map(_.item().get("itemType").s()).toSet == Set("SESSION", "RESERVATION"))
      items.foreach { put =>
        assert(
          put.conditionExpression() == "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
        )
        assert(
          put.expressionAttributeNames().asScala.toMap == Map(
            "#pk" -> "queryId",
            "#sk" -> "itemType"
          )
        )
        ttl match {
          case None    => assert(!put.item().containsKey("expiresAt"))
          case Some(_) => assert(put.item().get("expiresAt").n() == "1060")
        }
      }
      val session = items.find(_.item().get("itemType").s() == "SESSION").get
      assert(session.item().get("idempotencyKey").s() == "synthetic-idempotency")
    }
  }

  test("Dynamo batch point reads split 101 unique keys into calls of 100 and 1") {
    val calls = mutable.Buffer.empty[BatchGetItemRequest]
    val client = stub(classOf[DynamoDbClient]) {
      case ("batchGetItem", Vector(request: BatchGetItemRequest)) =>
        calls += request
        BatchGetItemResponse.builder().build()
    }
    val store: ResearcherMetricStore = new DynamoResearcherMetricStore(client, config)
    val keys = (1 to 101).toVector.map(i => (s"synthetic-researcher-$i", "all-years"))
    assert(store.batchGet(keys ++ keys.take(1)) == Found(Vector.empty))
    assert(
      calls.map(_.requestItems().get(config.tables.metrics).keys().size()).toVector == Vector(
        100,
        1
      )
    )
    val observed = calls.toVector.flatMap { request =>
      val attributes = request.requestItems().get(config.tables.metrics)
      assert(attributes.consistentRead())
      attributes.keys().asScala.map(k => k.get("researcherId").s() -> k.get("windowId").s())
    }
    assert(observed.toSet == keys.toSet)
    assert(observed.size == 101)
  }

  test(
    "Dynamo unprocessed keys retry to the configured bound and return a typed exhausted result"
  ) {
    var count = 0
    val client = stub(classOf[DynamoDbClient]) {
      case ("batchGetItem", Vector(request: BatchGetItemRequest)) =>
        count += 1
        BatchGetItemResponse.builder().unprocessedKeys(request.requestItems()).build()
    }
    val store = new DynamoResearcherMetricStore(client, config)
    assert(
      store.batchGet(Vector(researcherId -> "all-years")) == Retried(
        1,
        Rejected("unprocessed-keys-exhausted")
      )
    )
    assert(count == 2)
  }
}
