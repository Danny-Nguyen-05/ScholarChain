package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.*
import software.amazon.awssdk.core.sync.RequestBody
import software.amazon.awssdk.awscore.exception.AwsServiceException
import software.amazon.awssdk.core.exception.SdkClientException
import scala.jdk.CollectionConverters.*
import StorageResult.*

private[storage] final class StorageRetry(
    config: RetryConfig,
    sleep: Long => Unit = ms => Thread.sleep(ms),
    random: () => Double = () => scala.util.Random.nextDouble()
) {
  def apply[A](body: => StorageResult[A]): StorageResult[A] = {
    var attempt = 1
    while (true) {
      try { val r = body; return if (attempt > 1) Retried(attempt - 1, r) else r }
      catch {
        case e: AwsServiceException
            if e.statusCode() == 429 || e.statusCode() == 409 || e.statusCode() >= 500 =>
          if (attempt >= config.maxAttempts)
            return Retried(attempt - 1, Rejected("retry-exhausted"))
          val delay = math.min(
            config.maxDelayMillis.toDouble,
            config.baseDelayMillis.toDouble * math.pow(2, attempt - 1)
          )
          try sleep((random() * delay).toLong)
          catch {
            case _: InterruptedException =>
              Thread.currentThread().interrupt(); return Rejected("interrupted")
          }
          attempt += 1
        case _: AwsServiceException => return Rejected("provider-rejected")
        case _: SdkClientException | _: java.io.IOException =>
          if (attempt >= config.maxAttempts)
            return Retried(attempt - 1, Rejected("transport-retry-exhausted"))
          val delay = math.min(
            config.maxDelayMillis.toDouble,
            config.baseDelayMillis.toDouble * math.pow(2, attempt - 1)
          )
          try sleep((random() * delay).toLong)
          catch {
            case _: InterruptedException =>
              Thread.currentThread().interrupt(); return Rejected("interrupted")
          }
          attempt += 1
      }
    }
    Rejected("unreachable")
  }
}
final class S3ObjectStore(client: S3Client, config: StorageConfig) extends ObjectStore {
  private val retry = new StorageRetry(config.retry)
  private def checkHead(
      key: String,
      hash: Option[String],
      size: Long,
      contentType: String,
      meta: Map[String, String]
  ): StorageResult[ObjectHead] = {
    if (!hash.exists(_.matches("[0-9a-f]{64}"))) Rejected("missing-or-malformed-content-hash")
    else if (size < 0 || size > config.maxObjectBytes || contentType == null || contentType.isEmpty)
      Rejected("invalid-object-head")
    else Found(ObjectHead(key, hash.get, size, contentType, meta))
  }
  def head(key: String): StorageResult[ObjectHead] = retry {
    try {
      val r = client.headObject(HeadObjectRequest.builder().bucket(config.bucket).key(key).build())
      val meta = r.metadata().asScala.toMap
      checkHead(key, meta.get("sha256"), r.contentLength(), r.contentType(), meta)
    } catch { case e: S3Exception if e.statusCode() == 404 => Missing }
  }
  def get(key: String): StorageResult[StoredObject] = retry {
    // Reject over-large heads first, then independently cap the streamed response. An outside
    // overwrite between HEAD and GET cannot cause unbounded allocation or pass hash comparison.
    RowCodec.map(head(key)) { h =>
      val response =
        client.getObject(GetObjectRequest.builder().bucket(config.bucket).key(key).build())
      val bytes =
        try response.readNBytes(config.maxObjectBytes + 1).toVector
        finally response.close()
      val meta = response.response().metadata().asScala.toMap
      RowCodec.map(
        checkHead(
          key,
          meta.get("sha256"),
          response.response().contentLength(),
          response.response().contentType(),
          meta
        )
      ) { actual =>
        if (
          bytes.size > config.maxObjectBytes || bytes.size != actual.size || StorageKeys.sha256(
            bytes
          ) != actual.sha256 || actual != h
        ) Rejected("content-hash-mismatch")
        else Found(StoredObject(actual, bytes))
      }
    }
  }
  def put(
      key: String,
      bytes: Vector[Byte],
      contentType: String,
      metadata: Map[String, String]
  ): StorageResult[ObjectHead] = {
    ObjectRules.validate(key, bytes, contentType, metadata, config.maxObjectBytes) match {
      case Some(code) => Rejected(code)
      case None =>
        val hash = StorageKeys.sha256(bytes)
        val meta = metadata + ("sha256" -> hash)
        val expected = ObjectHead(key, hash, bytes.size.toLong, contentType, meta)
        retry {
          try {
            client.putObject(
              PutObjectRequest
                .builder()
                .bucket(config.bucket)
                .key(key)
                .contentType(contentType)
                .metadata(meta.asJava)
                .ifNoneMatch("*")
                .build(),
              RequestBody.fromBytes(bytes.toArray)
            )
            Written(expected)
          } catch {
            case e: S3Exception if e.statusCode() == 412 =>
              RowCodec.map(get(key)) { old =>
                if (old.head == expected && old.bytes == bytes) Unchanged(old.head)
                else Rejected("immutable-conflict")
              }
          }
        }
    }
  }
}
