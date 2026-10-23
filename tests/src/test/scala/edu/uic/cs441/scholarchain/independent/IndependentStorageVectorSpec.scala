package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.*

import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import java.nio.charset.StandardCharsets.UTF_8

class IndependentStorageVectorSpec extends AnyFunSuite {
  import IndependentStorage7BSupport.*
  import IndependentStorageFixtures.runId
  import StorageResult.*

  private val index = "researcher-profile-v1"
  private val config =
    VectorAdapterConfig("synthetic-unit-vectors", 2, "cosine", retry = RetryConfig(2, 0, 0))

  private def doc(ordinal: Int): VectorDocument = {
    val entity = "researcher:dblp:" + f"$ordinal%064x"
    VectorDocument(
      VectorIndexes.key("researcher-profile", entity, "2020-2026", "synthetic-model-v1"),
      Vector(1f, 0f),
      Map(
        "researcherId" -> entity,
        "documentType" -> "researcher-profile",
        "windowStartYear" -> "2020",
        "windowEndYear" -> "2026",
        "sourceDataset" -> "independent-synthetic",
        "textS3Uri" -> "s3://synthetic-unit-text/versions/v1/text",
        "textHash" -> ("a" * 64),
        "embeddingModel" -> "synthetic-model-v1",
        "runId" -> runId
      ),
      "a" * 64
    )
  }

  private val indexResponse = GetIndexResponse
    .builder()
    .index(
      Index
        .builder()
        .vectorBucketName(config.bucket)
        .indexName(index)
        .dimension(2)
        .distanceMetric("cosine")
        .dataType("float32")
        .metadataConfiguration(
          MetadataConfiguration
            .builder()
            .nonFilterableMetadataKeys(Vector("textS3Uri").asJava)
            .build()
        )
        .build()
    )
    .build()

  private def client(extra: PartialFunction[(String, Vector[AnyRef]), AnyRef]): S3VectorsClient =
    stub(classOf[S3VectorsClient])(extra.orElse {
      case ("getIndex", Vector(request: GetIndexRequest)) =>
        assert(request.vectorBucketName() == config.bucket)
        assert(request.indexName() == index)
        indexResponse
    })

  private def store(
      client: S3VectorsClient,
      reports: ObjectStore = new InMemoryObjectStore()
  ): S3VectorStore = {
    val result = new S3VectorStore(client, new InMemoryArtifactRegistry(), config, reports)
    assert(StorageResult.successful(result.ensureIndex(index, 2, "cosine")))
    result
  }

  test(
    "missing configured vector index is created with dimension, metric and nonfilterable text pointer"
  ) {
    val requests = mutable.Buffer.empty[CreateIndexRequest]
    val sdk = client {
      case ("getIndex", Vector(_: GetIndexRequest)) =>
        throw NotFoundException.builder().statusCode(404).build()
      case ("createIndex", Vector(request: CreateIndexRequest)) =>
        requests += request
        CreateIndexResponse.builder().build()
    }
    val vectors =
      new S3VectorStore(sdk, new InMemoryArtifactRegistry(), config, new InMemoryObjectStore())
    assert(vectors.ensureIndex(index, 2, "cosine") == Written(index))
    assert(requests.size == 1)
    assert(requests.head.dimension() == 2 && requests.head.distanceMetricAsString() == "cosine")
    assert(requests.head.dataTypeAsString() == "float32")
    assert(
      requests.head.metadataConfiguration().nonFilterableMetadataKeys().asScala.toSet == Set(
        "textS3Uri"
      )
    )
    assert(!StorageResult.successful(vectors.ensureIndex(index, 3, "cosine")))
    assert(!StorageResult.successful(vectors.ensureIndex("unconfigured-index", 2, "cosine")))
    assert(requests.size == 1)
  }

  test("vector writes split 501 valid documents at the documented 500-vector boundary") {
    val requests = mutable.Buffer.empty[PutVectorsRequest]
    val vectors = store(client { case ("putVectors", Vector(request: PutVectorsRequest)) =>
      requests += request
      PutVectorsResponse.builder().build()
    })
    val documents = (1 to 501).toVector.map(doc)
    val report = StorageResult.value(vectors.putBatch(index, documents)).get
    assert(report == VectorBatchResult(501, 0, Vector.empty))
    assert(requests.map(_.vectors().size()).toVector == Vector(500, 1))
    assert(requests.forall(r => r.vectorBucketName() == config.bucket && r.indexName() == index))
    assert(
      requests.toVector.flatMap(_.vectors().asScala.map(_.key())).toSet == documents
        .map(_.key)
        .toSet
    )
    assert(
      requests.head
        .vectors()
        .get(0)
        .data()
        .float32()
        .asScala
        .map(_.floatValue())
        .toVector == Vector(1f, 0f)
    )
  }

  test(
    "same key and text is unchanged while a changed text hash is rejected before provider write"
  ) {
    var puts = 0
    val vectors = store(client { case ("putVectors", Vector(_: PutVectorsRequest)) =>
      puts += 1
      PutVectorsResponse.builder().build()
    })
    val value = doc(1)
    assert(
      StorageResult.value(vectors.putBatch(index, Vector(value))).get == VectorBatchResult(
        1,
        0,
        Vector.empty
      )
    )
    assert(
      StorageResult.value(vectors.putBatch(index, Vector(value))).get == VectorBatchResult(
        0,
        1,
        Vector.empty
      )
    )
    val conflict =
      value.copy(textHash = "b" * 64, metadata = value.metadata.updated("textHash", "b" * 64))
    val report = StorageResult.value(vectors.putBatch(index, Vector(conflict))).get
    assert(report.written == 0 && report.unchanged == 0)
    assert(report.rejected.map(_.key) == Vector(value.key))
    assert(report.rejected.head.reason == "text-hash-conflict")
    assert(puts == 1)
  }

  test(
    "oversized metadata, missing required metadata and invalid vectors are counted without SDK writes"
  ) {
    val vectors = store(client(PartialFunction.empty))
    val value = doc(1)
    val invalid = Vector(
      value.copy(
        key = "oversize-total",
        metadata = value.metadata.updated("textS3Uri", "s3://" + "x" * (40 * 1024 + 1))
      ),
      value.copy(
        key = "oversize-filterable",
        metadata = value.metadata.updated("sourceDataset", "x" * (2 * 1024 + 1))
      ),
      value.copy(key = "missing-metadata", metadata = value.metadata - "textHash"),
      value.copy(key = "wrong-dimension", values = Vector(1f)),
      value.copy(key = "nonfinite-vector", values = Vector(Float.NaN, 0f))
    )
    val report = StorageResult.value(vectors.putBatch(index, invalid)).get
    assert(report.written == 0 && report.unchanged == 0)
    assert(report.rejected.map(_.key).toSet == invalid.map(_.key).toSet)
    assert(report.rejected.forall(_.reason.nonEmpty))
  }

  test("transient throttling retries once then succeeds with the same batch and bounded attempts") {
    val attempts = mutable.Buffer.empty[PutVectorsRequest]
    val vectors = store(client { case ("putVectors", Vector(request: PutVectorsRequest)) =>
      attempts += request
      if (attempts.size == 1) throw S3VectorsException.builder().statusCode(429).build()
      PutVectorsResponse.builder().build()
    })
    val result = vectors.putBatch(index, Vector(doc(2)))
    assert(StorageResult.value(result).exists(_.written == 1))
    assert(attempts.size == 2)
    assert(attempts.head.vectors() == attempts.last.vectors())
    assert(result.isInstanceOf[Retried[?]])
  }

  test("retry exhaustion and permanent provider failures produce rejected-vector reports") {
    Vector(503 -> 2, 400 -> 1).foreach { (status, expectedAttempts) =>
      var attempts = 0
      val reports = new InMemoryObjectStore()
      val vectors = store(
        client { case ("putVectors", Vector(_: PutVectorsRequest)) =>
          attempts += 1
          throw S3VectorsException
            .builder()
            .statusCode(status)
            .message("synthetic-sensitive-payload")
            .build()
        },
        reports
      )
      val result = vectors.putBatch(index, Vector(doc(status)))
      val report = StorageResult.value(result).get
      assert(report.written == 0 && report.unchanged == 0 && report.rejected.size == 1)
      assert(report.rejected.head.key == doc(status).key)
      assert(!report.rejected.head.reason.contains("synthetic-sensitive-payload"))
      assert(attempts == expectedAttempts)
      assert(reports.writeOrder.size == 1)
      val saved = StorageResult.value(reports.get(reports.writeOrder.head)).get
      val json = ujson.read(new String(saved.bytes.toArray, UTF_8))
      assert(json("rejected").arr.size == 1)
      assert(json("rejected")(0)("key").str == doc(status).key)
      assert(!new String(saved.bytes.toArray, UTF_8).contains("synthetic-sensitive-payload"))
    }
  }

  test("vector query binds metadata filters and enforces configured top-K and dimensions") {
    val requests = mutable.Buffer.empty[QueryVectorsRequest]
    val value = doc(1)
    val vectors = store(client { case ("queryVectors", Vector(request: QueryVectorsRequest)) =>
      requests += request
      QueryVectorsResponse
        .builder()
        .vectors(
          QueryOutputVector
            .builder()
            .key(value.key)
            .distance(0.25f)
            .metadata(
              document(ujson.Obj.from(value.metadata.map((key, text) => key -> ujson.Str(text))))
            )
            .build()
        )
        .build()
    })
    val filter = Map("sourceDataset" -> "synthetic' OR true --")
    val hits = StorageResult.value(vectors.query(index, Vector(1f, 0f), 3, filter)).get
    assert(hits.map(_.key) == Vector(value.key) && hits.head.distance == 0.25)
    assert(requests.size == 1)
    assert(requests.head.topK() == 3)
    assert(requests.head.filter().toString.contains("synthetic' OR true --"))
    assert(!StorageResult.successful(vectors.query(index, Vector(1f, 0f), 10001, filter)))
    assert(!StorageResult.successful(vectors.query(index, Vector(1f), 3, filter)))
    assert(requests.size == 1)
  }

  test("vector get splits 101 keys into 100 and 1 without synthesizing missing records") {
    val calls = mutable.Buffer.empty[GetVectorsRequest]
    val vectors = store(client { case ("getVectors", Vector(request: GetVectorsRequest)) =>
      calls += request
      GetVectorsResponse.builder().build()
    })
    assert(
      StorageResult
        .value(vectors.get(index, (1 to 101).toVector.map(i => s"synthetic-$i")))
        .contains(Vector.empty)
    )
    assert(calls.map(_.keys().size()).toVector == Vector(100, 1))
  }

  test("vector query follows a 100-result page token and returns the remaining hit for top-K 101") {
    val calls = mutable.Buffer.empty[QueryVectorsRequest]
    val documents = (1 to 101).toVector.map(doc)
    def hits(values: Vector[VectorDocument]): Vector[QueryOutputVector] = values.map { value =>
      QueryOutputVector
        .builder()
        .key(value.key)
        .distance(0.25f)
        .metadata(
          document(ujson.Obj.from(value.metadata.map((key, text) => key -> ujson.Str(text))))
        )
        .build()
    }
    val vectors = store(client { case ("queryVectors", Vector(request: QueryVectorsRequest)) =>
      calls += request
      if (calls.size == 1)
        QueryVectorsResponse
          .builder()
          .vectors(hits(documents.take(100)).asJava)
          .nextToken("synthetic-next-page")
          .build()
      else QueryVectorsResponse.builder().vectors(hits(documents.drop(100)).asJava).build()
    })
    val result = StorageResult
      .value(
        vectors.query(index, Vector(1f, 0f), 101, Map("sourceDataset" -> "independent-synthetic"))
      )
      .get
    assert(result.map(_.key) == documents.map(_.key))
    assert(result.size == 101)
    assert(calls.size == 2)
    assert(calls.head.nextToken() == null && calls.last.nextToken() == "synthetic-next-page")
    assert(calls.forall(_.topK() == 101))
    assert(calls.head.queryVector() == calls.last.queryVector())
    assert(calls.head.filter() == calls.last.filter())
  }

  test("vector query stops with a typed rejection when the configured page budget is exhausted") {
    var calls = 0
    val sdk = client { case ("queryVectors", Vector(_: QueryVectorsRequest)) =>
      calls += 1
      val value = doc(calls)
      QueryVectorsResponse
        .builder()
        .vectors(
          QueryOutputVector
            .builder()
            .key(value.key)
            .distance(0.25f)
            .metadata(
              document(ujson.Obj.from(value.metadata.map((key, text) => key -> ujson.Str(text))))
            )
            .build()
        )
        .nextToken(s"synthetic-page-$calls")
        .build()
    }
    val vectors = new S3VectorStore(
      sdk,
      new InMemoryArtifactRegistry(),
      config.copy(maxQueryPages = 2),
      new InMemoryObjectStore()
    )
    assert(StorageResult.successful(vectors.ensureIndex(index, 2, "cosine")))
    assert(
      vectors.query(index, Vector(1f, 0f), 101, Map.empty) == Rejected("vector-query-page-limit")
    )
    assert(calls == 2)
  }
}
