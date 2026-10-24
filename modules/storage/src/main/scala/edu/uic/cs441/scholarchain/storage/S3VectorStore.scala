package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.*
import software.amazon.awssdk.core.document.Document
import software.amazon.awssdk.awscore.AwsRequestOverrideConfiguration
import java.time.Duration
import java.nio.charset.StandardCharsets.UTF_8
import scala.jdk.CollectionConverters.*
import StorageResult.*

final class S3VectorStore(
    client: S3VectorsClient,
    registry: ArtifactRegistry,
    config: VectorAdapterConfig,
    rejectedObjects: ObjectStore
) extends VectorStore {
  private val retry = new StorageRetry(config.retry)
  private val required = Set("documentType", "textS3Uri", "textHash", "embeddingModel", "runId")
  private def timeout = AwsRequestOverrideConfiguration
    .builder()
    .apiCallTimeout(Duration.ofMillis(config.requestTimeoutMillis))
    .build()
  private def data(v: Vector[Float]) = VectorData.builder().float32(v.map(Float.box).asJava).build()
  private def document(metadata: Map[String, String]): Document =
    Document.fromMap(metadata.map((k, v) => k -> Document.fromString(v)).asJava)
  private def metadata(d: Document): Map[String, String] =
    d.asMap().asScala.map((k, v) => k -> v.asString()).toMap
  private def payload(d: VectorDocument): String = ujson
    .Obj(
      "key" -> d.key,
      "values" -> ujson.Arr.from(d.values.map(v => ujson.Num(v.toDouble))),
      "metadata" -> ujson.Obj
        .from(d.metadata.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v))),
      "textHash" -> d.textHash
    )
    .render()
  private def hash(s: String) = StorageKeys.sha256(s.getBytes(UTF_8).toVector)
  // Conservative JSON upper bound: a finite float32 needs fewer than 32 encoded characters.
  private def wireBytes(d: VectorDocument): Int = ujson.Obj
    .from(d.metadata.map((k, v) => k -> ujson.Str(v)))
    .render()
    .getBytes(UTF_8)
    .length + ujson.Str(d.key).render().getBytes(UTF_8).length + d.values.size * 32 + 256
  private def reason(d: VectorDocument): Option[String] = {
    val metaBytes =
      ujson.Obj.from(d.metadata.map((k, v) => k -> ujson.Str(v))).render().getBytes(UTF_8).length
    val filterBytes = ujson.Obj
      .from(
        d.metadata.filterNot((k, _) => config.nonFilterableKeys(k)).map((k, v) => k -> ujson.Str(v))
      )
      .render()
      .getBytes(UTF_8)
      .length
    if (d.key.isEmpty || d.key.getBytes(UTF_8).length > 1024) Some("invalid-vector-key")
    else if (
      d.values.size != config.dimension || d.values
        .exists(v => !v.isFinite) || (config.metric == "cosine" && d.values.forall(_ == 0f))
    ) Some("invalid-vector-data")
    else if (
      !required.subsetOf(d.metadata.keySet) || !(d.metadata.contains("researcherId") || d.metadata
        .contains("communityId") || d.metadata.contains("entityId"))
    ) Some("missing-vector-metadata")
    else if (
      !d.textHash.matches("[0-9a-f]{64}") || d
        .metadata("textHash") != d.textHash || !d.metadata("textS3Uri").startsWith("s3://")
    ) Some("invalid-vector-metadata")
    else if (d.metadata.keys.exists(_.isEmpty) || d.metadata.values.exists(_.isEmpty))
      Some("invalid-vector-metadata")
    else if (
      d.metadata.size > config.maxMetadataKeys || metaBytes > config.maxMetadataBytes || filterBytes > config.maxFilterableBytes
    ) Some("metadata-limit")
    else if (d.metadata.keys.exists(k => Set("text", "abstract", "content", "fullText")(k)))
      Some("long-text-in-metadata")
    else if (wireBytes(d) + 1024 > config.maxRequestBytes)
      Some("request-size-limit")
    else None
  }
  def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String] = {
    if (!VectorIndexes.names(name) || dimension != config.dimension || metric != config.metric)
      return Rejected("invalid-index")
    retry {
      try {
        val existing = client
          .getIndex(
            GetIndexRequest
              .builder()
              .vectorBucketName(config.bucket)
              .indexName(name)
              .overrideConfiguration(timeout)
              .build()
          )
          .index()
        if (
          existing.dimension() != dimension || existing
            .distanceMetricAsString() != metric || existing
            .dataTypeAsString() != "float32" || existing
            .metadataConfiguration()
            .nonFilterableMetadataKeys()
            .asScala
            .toSet != config.nonFilterableKeys
        ) Rejected("index-conflict")
        else Unchanged(name)
      } catch {
        case _: NotFoundException =>
          client.createIndex(
            CreateIndexRequest
              .builder()
              .vectorBucketName(config.bucket)
              .indexName(name)
              .dimension(dimension)
              .distanceMetric(metric)
              .dataType("float32")
              .metadataConfiguration(
                MetadataConfiguration
                  .builder()
                  .nonFilterableMetadataKeys(config.nonFilterableKeys.toVector.sorted.asJava)
                  .build()
              )
              .overrideConfiguration(timeout)
              .build()
          )
          Written(name)
      }
    }
  }
  def putBatch(
      index: String,
      documents: Vector[VectorDocument]
  ): StorageResult[VectorBatchResult] = {
    if (!VectorIndexes.names(index)) return Rejected("invalid-index")
    var written = 0; var unchanged = 0; var retries = 0
    val rejected = Vector.newBuilder[VectorReject];
    val pending = scala.collection.mutable.ArrayBuffer.empty[VectorDocument]
    val seen = scala.collection.mutable.Map.empty[String, String]
    def reject(d: VectorDocument, r: String): Unit = rejected += VectorReject(d.key, r)
    documents.foreach { d =>
      reason(d) match {
        case Some(code) => reject(d, code)
        case None =>
          val artifact = "vector:" + StorageKeys.composite(index, d.key)
          val uri = "s3vectors://" + config.bucket + "/" + index + "/" + java.net.URLEncoder
            .encode(d.key, UTF_8)
          val fingerprint = hash(payload(d))
          if (seen.get(d.key).exists(_ != fingerprint)) reject(d, "vector-payload-conflict")
          else if (seen.contains(d.key)) unchanged += 1
          else {
            seen(d.key) = fingerprint
            val binding = registry.register(artifact, "text", uri, d.textHash)
            if (!StorageResult.successful(binding)) reject(d, "text-hash-conflict")
            else {
              val reservation = registry.register(artifact, "payload", uri, fingerprint)
              if (!StorageResult.successful(reservation)) reject(d, "vector-payload-conflict")
              else
                registry.get(artifact, "complete") match {
                  case Found(record) if record.hash == fingerprint =>
                    unchanged += 1
                  case Unchanged(record) if record.hash == fingerprint =>
                    unchanged += 1
                  case Missing => pending += d
                  case _       => reject(d, "vector-registry-unavailable")
                }
            }
          }
      }
    }
    var batch = Vector.empty[VectorDocument]; var bytes = 1024
    def flush(): Unit = if (batch.nonEmpty) {
      val current = batch
      val result = retry {
        val vectors = current.map(d =>
          PutInputVector
            .builder()
            .key(d.key)
            .data(data(d.values))
            .metadata(document(d.metadata))
            .build()
        )
        client.putVectors(
          PutVectorsRequest
            .builder()
            .vectorBucketName(config.bucket)
            .indexName(index)
            .vectors(vectors.asJava)
            .overrideConfiguration(timeout)
            .build()
        ); Written(())
      }
      result match { case Retried(n, _) => retries += n; case _ => () }
      if (StorageResult.successful(result)) current.foreach { d =>
        val artifact = "vector:" + StorageKeys.composite(index, d.key);
        val fingerprint = hash(payload(d));
        val uri = "s3vectors://" + config.bucket + "/" + index + "/" + java.net.URLEncoder
          .encode(d.key, UTF_8)
        val done = registry.register(artifact, "complete", uri, fingerprint)
        if (StorageResult.successful(done)) written += 1
        else reject(d, "completion-registry-failed")
      }
      else
        current.foreach(d =>
          reject(
            d,
            result match {
              case Rejected(c) => c; case Retried(_, Rejected(c)) => c;
              case _           => "vector-write-failed"
            }
          )
        )
      batch = Vector.empty; bytes = 1024
    }
    pending.foreach { d =>
      val size = wireBytes(d);
      if (batch.size >= config.putBatchSize || bytes + size > config.maxRequestBytes) flush();
      batch = batch :+ d; bytes += size
    }; flush()
    val report = VectorBatchResult(written, unchanged, rejected.result())
    if (report.rejected.nonEmpty) {
      val json = ujson
        .Obj(
          "index" -> index,
          "written" -> written,
          "unchanged" -> unchanged,
          "rejected" -> ujson.Arr
            .from(report.rejected.map(r => ujson.Obj("key" -> r.key, "reason" -> r.reason)))
        )
        .render()
      val digest = hash(json)
      val saved = rejectedObjects.put(
        StorageKeys.versioned("vector-rejects", digest, "report.json"),
        json.getBytes(UTF_8).toVector,
        "application/json",
        Map.empty
      )
      if (!StorageResult.successful(saved)) return Rejected("reject-report-write-failed")
    }
    val result = if (written > 0) Written(report) else Unchanged(report)
    if (retries > 0) Retried(retries, result) else result
  }
  def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] = {
    if (!VectorIndexes.names(index)) return Rejected("invalid-index")
    val out = Vector.newBuilder[VectorDocument]
    for (batch <- keys.distinct.grouped(config.getBatchSize)) {
      val result = retry {
        val r = client.getVectors(
          GetVectorsRequest
            .builder()
            .vectorBucketName(config.bucket)
            .indexName(index)
            .keys(batch.asJava)
            .returnData(true)
            .returnMetadata(true)
            .overrideConfiguration(timeout)
            .build()
        )
        try
          Found(
            r.vectors()
              .asScala
              .toVector
              .map(v => {
                val m = metadata(v.metadata());
                VectorDocument(
                  v.key(),
                  v.data().float32().asScala.map(_.floatValue()).toVector,
                  m,
                  m("textHash")
                )
              })
          )
        catch { case _: Exception => Rejected("malformed-vector-response") }
      }
      StorageResult.value(result) match { case Some(v) => out ++= v; case None => return result }
    }
    Found(out.result())
  }
  def query(
      index: String,
      vector: Vector[Float],
      topK: Int,
      filter: Map[String, String]
  ): StorageResult[Vector[VectorHit]] = {
    if (
      !VectorIndexes.names(
        index
      ) || topK < 1 || topK > config.maxTopK || vector.size != config.dimension || vector.exists(
        v => !v.isFinite
      ) || filter.keys.exists(config.nonFilterableKeys)
    ) return Rejected("invalid-vector-query")
    val filters = filter.toVector
      .sortBy(_._1)
      .map((k, v) =>
        Document.fromMap(
          Map(k -> Document.fromMap(Map("$eq" -> Document.fromString(v)).asJava)).asJava
        )
      )
    val expression =
      if (filters.size == 1) filters.head
      else Document.fromMap(Map("$and" -> Document.fromList(filters.asJava)).asJava)
    var token: Option[String] = None; val seen = scala.collection.mutable.Set.empty[String];
    val out = Vector.newBuilder[VectorHit]; var count = 0; var pages = 0
    var firstPage = true
    while (firstPage || token.nonEmpty && pages < config.maxQueryPages) {
      firstPage = false
      val result = retry {
        val b = QueryVectorsRequest
          .builder()
          .vectorBucketName(config.bucket)
          .indexName(index)
          .queryVector(data(vector))
          .topK(topK)
          .returnMetadata(true)
          .returnDistance(true)
          .overrideConfiguration(timeout)
        if (filter.nonEmpty) b.filter(expression); token.foreach(b.nextToken)
        val r = client.queryVectors(b.build()); Found(r)
      }
      val response = StorageResult.value(result) match {
        case Some(r) => r;
        case None    => return RowCodec.map(result)(_ => Rejected("vector-query-failed"))
      }
      try
        response.vectors().asScala.foreach { v =>
          if (!seen.add(v.key())) return Rejected("duplicate-vector-result")
          out += VectorHit(v.key(), v.distance().doubleValue(), metadata(v.metadata())); count += 1
        }
      catch { case _: Exception => return Rejected("malformed-vector-response") }
      if (count > topK) return Rejected("vector-response-limit")
      token = Option(response.nextToken()).filter(_.nonEmpty); pages += 1
    }
    if (token.nonEmpty) Rejected("vector-query-page-limit") else Found(out.result())
  }
}
