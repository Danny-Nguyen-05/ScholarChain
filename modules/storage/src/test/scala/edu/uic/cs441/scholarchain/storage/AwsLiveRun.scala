package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.auth.credentials.ProfileCredentialsProvider
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.core.client.config.ClientOverrideConfiguration
import software.amazon.awssdk.core.retry.RetryPolicy
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.{HeadObjectRequest, DeleteObjectRequest}
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.{
  AttributeValue,
  GetItemRequest,
  DeleteItemRequest,
  QueryRequest
}
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.{
  GetIndexRequest,
  GetVectorsRequest,
  DeleteVectorsRequest
}
import software.amazon.awssdk.services.neptunedata.NeptunedataClient
import software.amazon.awssdk.services.neptunedata.model.{
  ExecuteOpenCypherQueryRequest,
  GetLoaderJobStatusRequest
}
import java.time.Duration
import java.net.URI
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.Files
import scala.jdk.CollectionConverters.*
import StorageResult.*

/** Not a Suite or initializer. Only the explicitly tagged test body invokes execute. */
private[storage] object AwsLiveRun {
  private def need(condition: Boolean): Unit =
    require(condition, "live integration assertion failed")
  private def found[A](result: StorageResult[A]): A = StorageResult
    .value(result)
    .getOrElse(throw new IllegalStateException("live storage operation rejected"))
  private def scalar(value: String) = AttributeValue.builder().s(value).build()
  private def key(pkName: String, skName: String, item: OwnedLiveItem) =
    Map(pkName -> scalar(item.key), skName -> scalar(item.sortKey)).asJava
  def execute(settings: AwsLiveSettings): Unit = {
    // Bounds: one unique run, three graph nodes/one edge, one vector, <=90 loader polls over90s.
    val runId = "run:" + java.util.UUID.randomUUID().toString
    val fixture = LiveGraphFixture.create(runId)
    val journal = new LiveRunManifest(settings.manifestDirectory, runId, settings)
    journal.finish("guarded-start")
    val closed = scala.collection.mutable.ArrayBuffer.empty[AutoCloseable]
    var completed = false
    var localRoot: Option[java.nio.file.Path] = None
    try {
      def credentials(profile: String): ProfileCredentialsProvider = {
        val value = ProfileCredentialsProvider.builder().profileName(profile).build();
        closed += value; value
      }
      val policy = ClientOverrideConfiguration
        .builder()
        .retryPolicy(RetryPolicy.none())
        .apiCallTimeout(Duration.ofSeconds(10))
        .apiCallAttemptTimeout(Duration.ofSeconds(10))
        .build()
      val primary = credentials(settings.profile);
      val readerCredentials = credentials(settings.readerProfile);
      val loaderCredentials = credentials(settings.loaderProfile)
      val region = Region.of(settings.region)
      val s3 = S3Client
        .builder()
        .region(region)
        .credentialsProvider(primary)
        .overrideConfiguration(policy)
        .build(); closed += s3
      val dynamo = DynamoDbClient
        .builder()
        .region(region)
        .credentialsProvider(primary)
        .overrideConfiguration(policy)
        .build(); closed += dynamo
      val vectors = S3VectorsClient
        .builder()
        .region(region)
        .credentialsProvider(primary)
        .overrideConfiguration(policy)
        .build(); closed += vectors
      val graphLoaderClient = NeptunedataClient
        .builder()
        .region(region)
        .credentialsProvider(loaderCredentials)
        .endpointOverride(URI.create(settings.neptuneEndpoint))
        .overrideConfiguration(policy)
        .build(); closed += graphLoaderClient
      val graphReaderClient = NeptunedataClient
        .builder()
        .region(region)
        .credentialsProvider(readerCredentials)
        .endpointOverride(URI.create(settings.neptuneEndpoint))
        .overrideConfiguration(policy)
        .build(); closed += graphReaderClient
      val retry = RetryConfig(1, 0, 0)
      val storage =
        StorageConfig(settings.bucket, settings.tables, retry = retry, maxObjectBytes = 64 * 1024)
      val delegateObjects = new S3ObjectStore(s3, storage)
      val objects = new ObjectStore {
        def put(
            k: String,
            bytes: Vector[Byte],
            contentType: String,
            metadata: Map[String, String]
        ): StorageResult[ObjectHead] = {
          val planned =
            OwnedLiveItem("s3", settings.bucket, k, expectedHash = StorageKeys.sha256(bytes));
          journal.plan(planned)
          val result =
            delegateObjects.put(k, bytes, contentType, metadata + ("live-itest-run" -> runId))
          if (StorageResult.successful(result)) {
            val head =
              s3.headObject(HeadObjectRequest.builder().bucket(settings.bucket).key(k).build())
            need(head.metadata().get("live-itest-run") == runId)
            journal.record(
              planned.copy(versionId = Option(head.versionId()).getOrElse(""), state = "created")
            )
          }
          result
        }
        def get(k: String) = delegateObjects.get(k)
        def head(k: String) = delegateObjects.head(k)
      }
      val delegateRegistry = new DynamoArtifactRegistry(dynamo, storage)
      val registry = new ArtifactRegistry {
        def register(
            id: String,
            version: String,
            uri: String,
            hash: String
        ): StorageResult[ArtifactRecord] = {
          need(id.contains(runId))
          val planned = OwnedLiveItem(
            "dynamodb-artifact",
            settings.tables.artifacts,
            id,
            version,
            StorageKeys.sha256(
              RowCodec.encode(ArtifactRecord(id, version, uri, hash)).getBytes(UTF_8).toVector
            )
          )
          val alreadyOwned = journal.all.exists(item =>
            item.kind == planned.kind && item.key == id && item.sortKey == version && item.state == "created"
          )
          if (!alreadyOwned) need(delegateRegistry.get(id, version) == Missing)
          journal.plan(planned)
          val result = delegateRegistry.register(id, version, uri, hash)
          if (StorageResult.successful(result)) journal.record(planned.copy(state = "created"))
          result
        }
        def get(id: String, version: String) = delegateRegistry.get(id, version)
        def latest(id: String) = delegateRegistry.latest(id)
      }
      // S3 adapter round trip, exact hash and immutable-key conflict.
      val objectKey =
        StorageKeys.versioned(settings.fixturePrefix, runId.stripPrefix("run:"), "roundtrip.txt")
      val body = "Synthetic AWS integration text\r\n\t\"quoted\"\\path Ελληνικά 中文 😀"
        .getBytes(UTF_8)
        .toVector
      found(objects.put(objectKey, body, "text/plain", Map.empty))
      need(found(objects.get(objectKey)).bytes == body)
      need(found(objects.head(objectKey)).sha256 == StorageKeys.sha256(body))
      // Dynamo immutable conditional create succeeds once, same payload is unchanged, changed hash rejects.
      val artifactId = "live:" + runId + ":conditional"
      need(
        registry
          .register(
            artifactId,
            "0001",
            "s3://" + settings.bucket + "/" + objectKey,
            StorageKeys.sha256(body)
          )
          .isInstanceOf[Written[?]]
      )
      need(
        registry
          .register(
            artifactId,
            "0001",
            "s3://" + settings.bucket + "/" + objectKey,
            StorageKeys.sha256(body)
          )
          .isInstanceOf[Unchanged[?]]
      )
      // Conflicting probe uses the underlying adapter so the journal retains the created hash.
      need(
        delegateRegistry.register(
          artifactId,
          "0001",
          "s3://" + settings.bucket + "/" + objectKey,
          "0" * 64
        ) == Rejected("immutable-conflict")
      )
      // Indexes are provisioned by Terraform; this suite never calls ensureIndex or CreateIndex.
      val existing = vectors
        .getIndex(
          GetIndexRequest
            .builder()
            .vectorBucketName(settings.vectorBucket)
            .indexName(settings.vectorIndex)
            .build()
        )
        .index()
      need(
        existing.dimension() == settings.dimension && existing
          .distanceMetricAsString() == settings.metric && existing.dataTypeAsString() == "float32"
      )
      val nonFilterable = existing.metadataConfiguration().nonFilterableMetadataKeys().asScala.toSet
      val vectorConfig = VectorAdapterConfig(
        settings.vectorBucket,
        settings.dimension,
        settings.metric,
        putBatchSize = 1,
        getBatchSize = 1,
        maxTopK = 1,
        maxQueryPages = 1,
        nonFilterableKeys = nonFilterable,
        retry = retry
      )
      val vectorStore = new S3VectorStore(vectors, registry, vectorConfig, objects)
      val vectorKey =
        VectorIndexes.key("researcher-profile", runId, "all-years", "synthetic-live-v1")
      val plannedVector = OwnedLiveItem(
        "vector",
        settings.vectorBucket,
        vectorKey,
        settings.vectorIndex,
        expectedHash = StorageKeys.sha256(body)
      )
      journal.plan(plannedVector)
      need(
        vectors
          .getVectors(
            GetVectorsRequest
              .builder()
              .vectorBucketName(settings.vectorBucket)
              .indexName(settings.vectorIndex)
              .keys(vectorKey)
              .returnMetadata(true)
              .build()
          )
          .vectors()
          .isEmpty
      )
      val vector = Vector.tabulate(settings.dimension)(n => if (n == 0) 1.0f else 0.0f)
      val metadata = Map(
        "researcherId" -> fixture.nodeIds.head,
        "documentType" -> "researcher-profile",
        "textS3Uri" -> ("s3://" + settings.bucket + "/" + objectKey),
        "textHash" -> StorageKeys.sha256(body),
        "embeddingModel" -> "synthetic-live-v1",
        "runId" -> runId
      )
      val put = found(
        vectorStore.putBatch(
          settings.vectorIndex,
          Vector(VectorDocument(vectorKey, vector, metadata, StorageKeys.sha256(body)))
        )
      )
      need(put.written == 1 && put.rejected.isEmpty)
      journal.record(plannedVector.copy(state = "created"))
      var vectorVisible = false; var tries = 0
      while (!vectorVisible && tries < 10) {
        val hits = found(vectorStore.query(settings.vectorIndex, vector, 1, Map("runId" -> runId)))
        vectorVisible = hits.exists(_.key == vectorKey); tries += 1
        if (!vectorVisible && tries < 10) Thread.sleep(500)
      }
      need(vectorVisible)
      // Synthetic test-only validated handle exercises the real loader, ledger, registry and reader.
      // Full Parquet/sidecar validation is covered by the offline producer/independent suites.
      val graphReader =
        new NeptuneGraphReader(graphReaderClient, GraphReaderConfig(maxLimit = 2, retry = retry))
      fixture.nodeIds.foreach(id => need(graphReader.node(id) == Missing))
      fixture.nodeIds.foreach(id =>
        journal.plan(
          OwnedLiveItem("neptune-node", settings.neptuneEndpoint, id, expectedHash = runId)
        )
      )
      journal.plan(
        OwnedLiveItem(
          "neptune-edge",
          settings.neptuneEndpoint,
          fixture.edgeId,
          expectedHash = runId
        )
      )
      val handle = fixture.handle(); localRoot = Some(handle.root)
      val run = "neptune:" + runId + ":" + fixture.fingerprint
      val ledger = new DynamoRunLedger(dynamo, storage)
      need(ledger.getRun(run) == Missing)
      Vector("RUN", "STAGE#bulk-load", "FAILURE#" + StorageKeys.composite("bulk-load", "1"))
        .foreach(sk =>
          journal.plan(OwnedLiveItem("dynamodb-run", settings.tables.runLedger, run, sk))
        )
      val graphLoader = new NeptuneGraphLoader(
        graphLoaderClient,
        objects,
        ledger,
        registry,
        NeptuneLoaderConfig(
          settings.bucket,
          settings.fixturePrefix,
          settings.region,
          settings.neptuneRoleArn,
          pollIntervalMillis = 1000,
          timeoutMillis = 90000,
          maxPolls = 90,
          maxUploadBytes = 64 * 1024,
          requestTimeoutMillis = 10000,
          retry = retry
        ),
        new NeptuneExportValidator()
      )
      val loaded = found(graphLoader.loadValidated(handle)); need(loaded.state == "LOAD_COMPLETED")
      fixture.nodeIds.foreach { id =>
        need(found(graphReader.node(id)).nodeId == id);
        journal.record(
          OwnedLiveItem(
            "neptune-node",
            settings.neptuneEndpoint,
            id,
            expectedHash = runId,
            state = "created"
          )
        )
      }
      need(
        found(graphReader.directCoauthors(fixture.nodeIds.head, "all-years", 2)).items.exists(n =>
          n.edgeId == fixture.edgeId && n.nodeId == fixture.nodeIds(1)
        )
      )
      journal.record(
        OwnedLiveItem(
          "neptune-edge",
          settings.neptuneEndpoint,
          fixture.edgeId,
          expectedHash = runId,
          state = "created"
        )
      )
      completed = true
      journal.finish("passed-retained")
      // Snapshot all bounded run rows for conditional owned-data cleanup, including any failure history.
      snapshotLedger(dynamo, settings, run, journal)
      if (settings.cleanupAuthorized) {
        val cleanupCredentials = credentials(settings.cleanupProfile)
        val cleanupClient = NeptunedataClient
          .builder()
          .region(region)
          .credentialsProvider(cleanupCredentials)
          .endpointOverride(URI.create(settings.neptuneEndpoint))
          .overrideConfiguration(policy)
          .build(); closed += cleanupClient
        try {
          cleanup(
            settings,
            s3,
            dynamo,
            vectors,
            cleanupClient,
            graphReaderClient,
            graphReader,
            runId,
            journal
          );
          journal.finish("passed-cleaned")
        } catch {
          case e: Exception => journal.finish("passed-cleanup-incomplete-reconcile"); throw e
        }
      }
    } finally {
      if (!completed) journal.finish("failed-retained-reconcile-planned-items-before-cleanup")
      localRoot.foreach(p => if (Files.exists(p)) ExportFiles.deleteTree(p))
      closed.reverseIterator.foreach(c =>
        try c.close()
        catch { case _: Exception => () }
      )
    }
  }
  private def snapshotLedger(
      client: DynamoDbClient,
      settings: AwsLiveSettings,
      run: String,
      journal: LiveRunManifest
  ): Unit = {
    val rows = client.query(
      QueryRequest
        .builder()
        .tableName(settings.tables.runLedger)
        .keyConditionExpression("#pk = :run")
        .expressionAttributeNames(Map("#pk" -> "runId").asJava)
        .expressionAttributeValues(Map(":run" -> scalar(run)).asJava)
        .consistentRead(true)
        .limit(10)
        .build()
    )
    need(rows.lastEvaluatedKey().isEmpty && rows.items().size() <= 10)
    rows.items().asScala.foreach { row =>
      need(row.get("runId").s() == run)
      val item = OwnedLiveItem(
        "dynamodb-run",
        settings.tables.runLedger,
        run,
        row.get("stageKey").s(),
        StorageKeys.sha256(row.get("payload").s().getBytes(UTF_8).toVector),
        state = "created"
      )
      journal.plan(item.copy(state = "planned")); journal.record(item)
    }
  }
  private def cleanup(
      settings: AwsLiveSettings,
      s3: S3Client,
      dynamo: DynamoDbClient,
      vectors: S3VectorsClient,
      graph: NeptunedataClient,
      graphReadClient: NeptunedataClient,
      graphReader: GraphReader,
      runId: String,
      journal: LiveRunManifest
  ): Unit = {
    need(settings.cleanupAuthorized)
    AwsLiveGraphCleanup.clean(graph, graphReadClient, graphReader, runId, journal)
    journal.all.filter(_.state == "created").foreach { item =>
      item.kind match {
        case "vector" =>
          val response = vectors.getVectors(
            GetVectorsRequest
              .builder()
              .vectorBucketName(item.resource)
              .indexName(item.sortKey)
              .keys(item.key)
              .returnMetadata(true)
              .build()
          )
          need(
            response.vectors().size() == 1 && response
              .vectors()
              .get(0)
              .metadata()
              .asMap()
              .get("runId")
              .asString() == runId && response
              .vectors()
              .get(0)
              .metadata()
              .asMap()
              .get("textHash")
              .asString() == item.expectedHash
          )
          vectors.deleteVectors(
            DeleteVectorsRequest
              .builder()
              .vectorBucketName(item.resource)
              .indexName(item.sortKey)
              .keys(item.key)
              .build()
          )
        case "dynamodb-artifact" | "dynamodb-run" =>
          val (pk, sk) =
            if (item.kind == "dynamodb-run") ("runId", "stageKey") else ("artifactId", "version")
          val row = dynamo
            .getItem(
              GetItemRequest
                .builder()
                .tableName(item.resource)
                .key(key(pk, sk, item))
                .consistentRead(true)
                .build()
            )
            .item()
          need(!row.isEmpty)
          val payload = row.get("payload").s();
          need(StorageKeys.sha256(payload.getBytes(UTF_8).toVector) == item.expectedHash)
          dynamo.deleteItem(
            DeleteItemRequest
              .builder()
              .tableName(item.resource)
              .key(key(pk, sk, item))
              .conditionExpression("#payload = :expected")
              .expressionAttributeNames(Map("#payload" -> "payload").asJava)
              .expressionAttributeValues(Map(":expected" -> scalar(payload)).asJava)
              .build()
          )
        case "s3" =>
          val builder = HeadObjectRequest.builder().bucket(item.resource).key(item.key);
          if (item.versionId.nonEmpty) builder.versionId(item.versionId)
          val head = s3.headObject(builder.build());
          need(
            head
              .metadata()
              .get("live-itest-run") == runId && head.metadata().get("sha256") == item.expectedHash
          )
          val deletion = DeleteObjectRequest.builder().bucket(item.resource).key(item.key);
          if (item.versionId.nonEmpty) deletion.versionId(item.versionId)
          s3.deleteObject(deletion.build())
        case _ => throw new IllegalArgumentException("unknown owned-data kind")
      }
      journal.record(item.copy(state = "cleaned"))
    }
  }
}
