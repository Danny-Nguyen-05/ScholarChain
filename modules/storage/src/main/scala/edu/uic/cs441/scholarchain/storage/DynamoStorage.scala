package edu.uic.cs441.scholarchain.storage

import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.*
import scala.jdk.CollectionConverters.*
import StorageResult.*

private[storage] final class DynamoRows(client: DynamoDbClient, config: StorageConfig)
    extends StorageRows {
  private val retry = new StorageRetry(config.retry)
  private val schemas = Map(
    config.tables.runLedger -> ("runId", "stageKey"),
    config.tables.entityLinks -> ("entityType#normalizedKey", "policyVersion#sourceId"),
    config.tables.querySessions -> ("queryId", "itemType"),
    config.tables.evidence -> ("evidenceId", "part"),
    config.tables.artifacts -> ("artifactId", "version"),
    config.tables.metrics -> ("researcherId", "windowId")
  )
  require(schemas.size == 6, "storage tables must be distinct")
  private def string(s: String) = AttributeValue.builder().s(s).build()
  private def key(table: String, k: RowKey): java.util.Map[String, AttributeValue] = {
    val (p, s) = schemas(table); Map(p -> string(k.pk), s -> string(k.sk)).asJava
  }
  private def item(table: String, row: StorageRow): java.util.Map[String, AttributeValue] = {
    val attrs = row.attributes.map { case (k, v) =>
      k -> (if (k == "expiresAt") AttributeValue.builder().n(v).build() else string(v))
    }
    (key(table, row.key).asScala.toMap ++ attrs + ("payload" -> string(row.payload))).asJava
  }
  private def valid(table: String, row: StorageRow): Boolean = {
    val (p, s) = schemas(table)
    row.key.pk
      .getBytes(java.nio.charset.StandardCharsets.UTF_8)
      .length <= 2048 && row.key.pk.nonEmpty && row.key.sk
      .getBytes(java.nio.charset.StandardCharsets.UTF_8)
      .length <= 1024 && row.key.sk.nonEmpty &&
    (row.payload
      .getBytes(java.nio.charset.StandardCharsets.UTF_8)
      .length + row.key.pk.getBytes(java.nio.charset.StandardCharsets.UTF_8).length + row.key.sk
      .getBytes(java.nio.charset.StandardCharsets.UTF_8)
      .length + p.length + s.length + "payload".length + row.attributes.iterator
      .map((k, v) => k.length + v.getBytes(java.nio.charset.StandardCharsets.UTF_8).length)
      .sum <= config.maxDynamoItemBytes)
  }
  private def decode(
      table: String,
      raw: java.util.Map[String, AttributeValue]
  ): StorageResult[StorageRow] = try {
    val (p, s) = schemas(table)
    val k = RowKey(raw.get(p).s(), raw.get(s).s())
    val payload = raw.get("payload").s()
    if (k.pk == null || k.sk == null || payload == null) Rejected("corrupt-row")
    else
      Found(
        StorageRow(
          k,
          payload,
          raw.asScala.iterator
            .filterNot((name, _) => Set(p, s, "payload")(name))
            .map((name, v) => name -> Option(v.s()).getOrElse(v.n()))
            .toMap
        )
      )
  } catch { case _: Exception => Rejected("corrupt-row") }
  private def decodeAll(
      table: String,
      items: Vector[java.util.Map[String, AttributeValue]]
  ): StorageResult[Vector[StorageRow]] = {
    val decoded = items.map(decode(table, _))
    decoded
      .collectFirst { case Rejected(c) => c }
      .map(Rejected(_))
      .getOrElse(Found(decoded.flatMap(StorageResult.value)))
  }
  private def names(table: String, c: RowCondition): java.util.Map[String, String] = c match {
    case RowCondition.Absent => Map("#pk" -> schemas(table)._1, "#sk" -> schemas(table)._2).asJava
    case RowCondition.PayloadEquals(_) => Map("#payload" -> "payload").asJava
  }
  private def condition(c: RowCondition): String = c match {
    case RowCondition.Absent           => "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
    case RowCondition.PayloadEquals(_) => "#payload = :expected"
  }
  def read(table: String, k: RowKey): StorageResult[StorageRow] = retry {
    val r = client.getItem(
      GetItemRequest.builder().tableName(table).key(key(table, k)).consistentRead(true).build()
    )
    if (!r.hasItem || r.item().isEmpty) Missing else decode(table, r.item())
  }
  def query(table: String, pk: String, descending: Boolean): StorageResult[Vector[StorageRow]] =
    queryInternal(table, pk, descending, None)
  def index(table: String, index: String, k: String): StorageResult[Vector[StorageRow]] =
    queryInternal(table, k, false, Some(index))
  private def queryInternal(
      table: String,
      pk: String,
      descending: Boolean,
      index: Option[String]
  ): StorageResult[Vector[StorageRow]] = retry {
    val p = index.map(_ => "idempotencyKey").getOrElse(schemas(table)._1)
    val result = Vector.newBuilder[java.util.Map[String, AttributeValue]]
    var cursor: java.util.Map[String, AttributeValue] = Map.empty[String, AttributeValue].asJava
    var pages = 0
    var done = false
    while (!done && pages < config.maxQueryPages) {
      val b = QueryRequest
        .builder()
        .tableName(table)
        .keyConditionExpression("#pk = :pk")
        .expressionAttributeNames(Map("#pk" -> p).asJava)
        .expressionAttributeValues(Map(":pk" -> string(pk)).asJava)
        .scanIndexForward(!descending)
        .limit(config.queryPageSize)
        .consistentRead(index.isEmpty)
      index.foreach(b.indexName)
      if (!cursor.isEmpty) b.exclusiveStartKey(cursor)
      val response = client.query(b.build())
      result ++= response.items().asScala
      cursor = response.lastEvaluatedKey(); pages += 1; done = cursor.isEmpty
    }
    if (!done) Rejected("query-page-limit") else decodeAll(table, result.result())
  }
  def write(table: String, row: StorageRow, c: RowCondition): StorageResult[StorageRow] = {
    if (!valid(table, row)) return Rejected("invalid-or-oversized-item")
    retry {
      val b = PutItemRequest
        .builder()
        .tableName(table)
        .item(item(table, row))
        .conditionExpression(condition(c))
        .expressionAttributeNames(names(table, c))
      c match {
        case RowCondition.PayloadEquals(p) =>
          b.expressionAttributeValues(Map(":expected" -> string(p)).asJava)
        case _ => ()
      }
      try { client.putItem(b.build()); Written(row) }
      catch { case _: ConditionalCheckFailedException => Rejected("conditional-conflict") }
    }
  }
  def transact(table: String, writes: Vector[RowWrite]): StorageResult[Unit] = {
    if (
      writes.isEmpty || writes.size > 100 || writes
        .map(_.row.key)
        .distinct
        .size != writes.size || !writes.forall(w => valid(table, w.row))
    ) return Rejected("invalid-transaction")
    val puts = writes.map { w =>
      val b = Put
        .builder()
        .tableName(table)
        .item(item(table, w.row))
        .conditionExpression(condition(w.condition))
        .expressionAttributeNames(names(table, w.condition))
      w.condition match {
        case RowCondition.PayloadEquals(p) =>
          b.expressionAttributeValues(Map(":expected" -> string(p)).asJava)
        case _ => ()
      }
      TransactWriteItem.builder().put(b.build()).build()
    }
    retry {
      try {
        client.transactWriteItems(
          TransactWriteItemsRequest.builder().transactItems(puts.asJava).build()
        ); Written(())
      } catch {
        case e: TransactionCanceledException =>
          val codes = e.cancellationReasons().asScala.map(_.code()).filter(_ != "None")
          if (codes.nonEmpty && codes.forall(_ == "ConditionalCheckFailed"))
            Rejected("conditional-conflict")
          else Rejected("transaction-canceled")
      }
    }
  }
  def batch(table: String, keys: Vector[RowKey]): StorageResult[Vector[StorageRow]] = {
    val result = Vector.newBuilder[StorageRow]; var retried = 0
    for (chunk <- keys.distinct.grouped(config.batchGetSize)) {
      var pending = chunk.toVector
      var attempt = 0
      while (pending.nonEmpty && attempt < config.retry.maxAttempts) {
        val attrs = KeysAndAttributes
          .builder()
          .keys(pending.map(k => key(table, k)).asJava)
          .consistentRead(true)
          .build()
        val responseResult = retry {
          val r = client.batchGetItem(
            BatchGetItemRequest.builder().requestItems(Map(table -> attrs).asJava).build()
          )
          Found(r)
        }
        val response = StorageResult.value(responseResult) match {
          case Some(r) => r;
          case None    => return RowCodec.map(responseResult)(_ => Rejected("batch-unavailable"))
        }
        responseResult match { case Retried(n, _) => retried += n; case _ => () }
        decodeAll(
          table,
          Option(response.responses().get(table)).toVector.flatMap(_.asScala)
        ) match {
          case Found(rs)   => result ++= rs
          case Rejected(c) => return Rejected(c)
          case _           => return Rejected("batch-decode-failed")
        }
        val unprocessed =
          Option(response.unprocessedKeys().get(table)).toVector.flatMap(_.keys().asScala)
        pending = unprocessed.map { k =>
          val (p, s) = schemas(table); RowKey(k.get(p).s(), k.get(s).s())
        }.toVector
        attempt += 1
        if (pending.nonEmpty && attempt < config.retry.maxAttempts) {
          retried += 1
          val cap = math.min(
            config.retry.maxDelayMillis.toDouble,
            config.retry.baseDelayMillis * math.pow(2, attempt - 1)
          )
          try Thread.sleep((scala.util.Random.nextDouble() * cap).toLong)
          catch {
            case _: InterruptedException =>
              Thread.currentThread().interrupt(); return Rejected("interrupted")
          }
        }
      }
      if (pending.nonEmpty) return Retried(retried, Rejected("unprocessed-keys-exhausted"))
    }
    val output = Found(result.result()); if (retried > 0) Retried(retried, output) else output
  }
}
final class DynamoRunLedger(client: DynamoDbClient, config: StorageConfig)
    extends RowRunLedger(new DynamoRows(client, config), config.tables.runLedger)
final class DynamoEntityLinkCache(client: DynamoDbClient, config: StorageConfig)
    extends RowEntityLinks(new DynamoRows(client, config), config.tables.entityLinks)
final class DynamoQuerySessionStore(
    client: DynamoDbClient,
    config: StorageConfig,
    now: () => Long = () => java.time.Instant.now().getEpochSecond
) extends RowSessions(
      new DynamoRows(client, config),
      config.tables.querySessions,
      config.tables.idempotencyIndex,
      config.disposableSessionTtlSeconds,
      now
    )
final class DynamoEvidenceBundleStore(
    client: DynamoDbClient,
    config: StorageConfig,
    objects: ObjectStore
) extends RowEvidence(
      new DynamoRows(client, config),
      config.tables.evidence,
      objects,
      config.maxInlineEvidenceBytes
    )
final class DynamoArtifactRegistry(client: DynamoDbClient, config: StorageConfig)
    extends RowArtifacts(new DynamoRows(client, config), config.tables.artifacts)
final class DynamoResearcherMetricStore(client: DynamoDbClient, config: StorageConfig)
    extends RowMetrics(new DynamoRows(client, config), config.tables.metrics)
