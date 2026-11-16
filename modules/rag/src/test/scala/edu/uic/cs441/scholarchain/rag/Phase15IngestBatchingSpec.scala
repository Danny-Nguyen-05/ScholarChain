package edu.uic.cs441.scholarchain.rag

import ch.qos.logback.classic.{Level, LoggerContext}
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.classic.util.ContextInitializer
import ch.qos.logback.core.joran.util.ConfigurationWatchListUtil
import ch.qos.logback.core.read.ListAppender
import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import org.slf4j.LoggerFactory
import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Path}
import scala.collection.mutable
import scala.jdk.CollectionConverters.*
import upickle.default.write

/** Session-2 plan P26 (b) ingest batching and P38 tool logging for the rag tools. Everything runs
  * in process against in-memory storage fakes and fake embedders; no network, AWS, Voyage or
  * credential provider is used. Throughput figures are local fake measurements only: they say
  * nothing about Voyage, S3, DynamoDB or S3 Vectors latency.
  */
class Phase15IngestBatchingSpec extends AnyFunSuite {
  private val model = VoyageDefaults.Model

  /** Records every underlying call; optional fixed latency per call, failure or exception. */
  private final class RecordingEmbedder(
      latencyMillis: Long = 0,
      failWith: Option[EmbeddingFailure] = None,
      throwOnCall: Int = -1,
      wrongCountOnCall: Int = -1,
      onCall: () => Unit = () => ()
  ) extends EmbeddingClient {
    val model: EmbeddingModel = Phase15IngestBatchingSpec.this.model
    private val inner = new DeterministicHashedEmbeddingClient(model)
    val calls = mutable.ArrayBuffer.empty[Vector[String]]
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      calls += texts.toVector
      onCall()
      if (latencyMillis > 0) Thread.sleep(latencyMillis)
      if (calls.size == throwOnCall) throw new IllegalStateException("synthetic-failure")
      if (calls.size == wrongCountOnCall) inner.embed(texts.drop(1))
      else failWith.fold(inner.embed(texts))(f => texts.map(_ => f))
    }
  }

  private def texts(n: Int) = (0 until n).map(i => s"synthetic manifest text $i").toVector
  private def vector(r: EmbeddingResult) = r match {
    case EmbeddingSuccess(values, _, _) => values
    case other                          => fail(other.toString)
  }

  // ----- LookaheadBatchingEmbeddingClient -----

  test("P26b: in-order single-text requests become batches of batchSize, same vectors") {
    val all = texts(10)
    val fake = new RecordingEmbedder
    val batcher = new LookaheadBatchingEmbeddingClient(fake, all, 4)
    val reference = new DeterministicHashedEmbeddingClient(model)
    all.foreach { t =>
      val got = batcher.embed(Seq(t))
      assert(got.size == 1 && vector(got.head) == vector(reference.embed(Seq(t)).head))
    }
    assert(fake.calls.toVector == Vector(all.slice(0, 4), all.slice(4, 8), all.slice(8, 10)))
    assert(batcher.stats == EmbeddingBatchStats(3, 10, 7, 0, 0, 4))
    assert(batcher.model == model && batcher.provider == EmbeddingProvider.Voyage)
  }

  test("P26b: skipped items are not re-sent; prefetched-but-unused texts are counted") {
    val all = texts(10)
    val fake = new RecordingEmbedder
    val batcher = new LookaheadBatchingEmbeddingClient(fake, all, 4)
    batcher.embed(Seq(all(0))) // sends 0..3
    batcher.embed(Seq(all(5))) // runner skipped 1..4 (complete); sends 5..8, never 4
    assert(fake.calls.toVector == Vector(all.slice(0, 4), all.slice(5, 9)))
    assert(batcher.stats.unusedPrefetched == 6 && batcher.stats.textsSent == 8)
    // Each distinct text reaches the underlying client at most once.
    assert(fake.calls.flatten.distinct.size == fake.calls.flatten.size)
  }

  test("P26b: duplicate manifest texts are sent once; unknown or repeated texts pass through") {
    val all = Vector("a text", "b text", "a text", "c text")
    val fake = new RecordingEmbedder
    val batcher = new LookaheadBatchingEmbeddingClient(fake, all, 10)
    batcher.embed(Seq("a text"))
    assert(fake.calls.toVector == Vector(Vector("a text", "b text", "c text")))
    batcher.embed(Seq("b text"))
    batcher.embed(Seq("a text")) // already returned: goes alone
    batcher.embed(Seq("not in manifest"))
    assert(fake.calls.size == 3 && batcher.stats.passThrough == 2)
    assert(batcher.stats.servedFromBatch == 1)
  }

  test("P26b: a failed request returns the provider's failure for every text it carried") {
    val failure = EmbeddingFailure("embedding-retries-exhausted", true, model, 3)
    val all = texts(3)
    val fake = new RecordingEmbedder(failWith = Some(failure))
    val batcher = new LookaheadBatchingEmbeddingClient(fake, all, 3)
    assert(all.flatMap(t => batcher.embed(Seq(t))) == Vector.fill(3)(failure))
    assert(fake.calls.size == 1)
  }

  test("P26b: a throwing or wrong-count call is a typed failure and keeps nothing") {
    val all = texts(4)
    val thrower = new RecordingEmbedder(throwOnCall = 1)
    val b1 = new LookaheadBatchingEmbeddingClient(thrower, all, 4)
    assert(
      b1.embed(Seq(all(0))) == Seq(EmbeddingFailure("embedding-client-exception", false, model, 0))
    )
    // The other texts were not kept and are batched again on the next request.
    assert(vector(b1.embed(Seq(all(1))).head).nonEmpty)
    assert(thrower.calls.toVector == Vector(all, all.drop(1)))
    val short = new RecordingEmbedder(wrongCountOnCall = 1)
    val b2 = new LookaheadBatchingEmbeddingClient(short, all, 4)
    assert(
      b2.embed(Seq(all(0))) ==
        Seq(EmbeddingFailure("embedding-batch-result-count", false, model, 0))
    )
    assert(b2.stats.unusedPrefetched == 0)
  }

  test("P26b: batch size must be positive and the identity is the wrapped client's") {
    intercept[IllegalArgumentException](
      new LookaheadBatchingEmbeddingClient(new RecordingEmbedder, Vector.empty, 0)
    )
    val titan = EmbeddingModel("amazon.titan-embed-text-v2:0", "amazon.titan-embed-text-v2:0", 256)
    val b = new LookaheadBatchingEmbeddingClient(
      new DeterministicHashedEmbeddingClient(titan),
      Vector.empty,
      1
    )
    assert(b.model == titan && b.provider == EmbeddingProvider.Bedrock)
  }

  // ----- LiveEmbeddingIngestMain.run against in-memory fakes -----

  private val tables =
    DynamoTables("runs", "links", "sessions", "evidence", "artifacts", "metrics", "by-idempotency")
  private val gate = "Synthetic gate text for P26/P38 tests; not an actual approval."
  private val renderer =
    new DocumentRenderer(RenderingConfig("fixture-template", ChunkPolicy(1000, 0)))
  private val kinds = EmbeddingContracts.indexes.keys.toVector.sorted

  private def live(maxVectors: Int, batchSize: Int) = LiveEmbeddingConfig(
    "fixture-env",
    "us-east-2",
    "fixture-profile",
    model,
    "fixture-text",
    "embedding-text",
    "fixture-vectors",
    tables,
    EmbeddingContracts.indexes,
    "cosine",
    maxVectors,
    2,
    2,
    maxVectors * 2L,
    0.30,
    1e-9,
    1e-9,
    0.0,
    maxManifestBytes = 32 * 1024 * 1024,
    batchSize = batchSize
  )

  private def manifest(config: LiveEmbeddingConfig, n: Int): String = write(
    EmbeddingManifest((0 until n).toVector.map { i =>
      val kind = kinds(i % kinds.size)
      val document = renderer
        .render(
          RenderInput(
            kind,
            s"e-$kind-$i",
            "w",
            "r",
            Vector(
              SourceField(
                "title",
                s"Synthetic item $i of the P26 throughput fixture",
                SummarySourceRef("synthetic-source", s"e-$kind-$i", "title")
              )
            )
          )
        )
        .fold(fail(_), identity)
        .head
      EmbeddingManifests.item(document, config.model, config.ingest)
    })
  )

  private final class MemoryPorts(
      val embedder: EmbeddingClient,
      onReady: () => Unit = () => (),
      val ledger: RunLedger = new InMemoryRunLedger
  ) extends LiveEmbeddingPorts {
    val objects: ObjectStore = new InMemoryObjectStore
    val vectors: VectorStore = {
      val v = new InMemoryVectorStore
      EmbeddingContracts.indexes.values.toSet.foreach(i =>
        v.ensureIndex(i, model.dimension, "cosine")
      )
      v
    }
    val registry: ArtifactRegistry = new InMemoryArtifactRegistry
    def indexesReady(): StorageResult[Unit] = { onReady(); StorageResult.Found(()) }
    def close(): Unit = ()
  }

  /** Writes config, manifest, gate and approval files and runs the ingest main. */
  private def ingest(
      config: LiveEmbeddingConfig,
      items: Int,
      ports: LiveEmbeddingPorts,
      runId: String = "p26-run",
      concurrencyCap: Int = 2
  ): Either[String, ujson.Value] = {
    val root = Files.createTempDirectory("p26-ingest-")
    val configText = write(config)
    val manifestText = manifest(config, items)
    val gp = root.resolve("gate.md")
    Files.writeString(gp, gate, UTF_8)
    val approval = LiveEmbeddingApproval(
      true,
      "fixture-env",
      runId,
      StableIds.sha256Hex(configText),
      StableIds.sha256Hex(manifestText),
      gp.toString,
      StableIds.sha256Hex(gate),
      config.maxVectors,
      concurrencyCap,
      config.maxEmbeddingCalls,
      0.30,
      true,
      true,
      2000
    )
    def file(name: String, text: String): String = {
      val p = root.resolve(name); Files.writeString(p, text, UTF_8); p.toString
    }
    LiveEmbeddingIngestMain.run(
      Seq(
        "--config",
        file("config.json", configText),
        "--manifest",
        file("manifest.json", manifestText),
        "--approval",
        file("approval.json", write(approval)),
        "--report",
        root.resolve("report.json").toString,
        "--run-id",
        runId
      ),
      _ => ports,
      1000
    )
  }

  test("P26b: the ingest main batches embeddings by batchSize and reports the counters") {
    val fake = new RecordingEmbedder
    val report = ingest(live(250, 100), 250, new MemoryPorts(fake)).fold(fail(_), identity)
    assert(report("written").num == 250 && report("rejected").num == 0)
    assert(fake.calls.map(_.size).toVector == Vector(100, 100, 50))
    val batch = report("embeddingBatch")
    assert(batch("batchSize").num == 100 && batch("underlyingCalls").str == "3")
    assert(batch("textsSent").str == "250" && batch("servedFromBatch").str == "247")
    assert(batch("unusedPrefetched").str == "0" && batch("passThrough").str == "0")
    // embeddingCalls stays the runner's per-item attempt sum (one attempt per item here).
    assert(report("embeddingCalls").num == 250)
  }

  test("P26b: measured local throughput with a fake embedder, batched versus one text per call") {
    // A fixed 10 ms per underlying call stands in for a provider round trip; storage is in memory.
    val n = 500
    def measure(batchSize: Int): (Double, Int) = {
      val fake = new RecordingEmbedder(latencyMillis = 10)
      val report =
        ingest(live(n, batchSize), n, new MemoryPorts(fake), s"p26-tp-$batchSize")
          .fold(fail(_), identity)
      assert(report("written").num == n && report("rejected").num == 0)
      (report("vectorsPerSecond").num, fake.calls.size)
    }
    val (single, singleCalls) = measure(1)
    val (batched, batchedCalls) = measure(100)
    assert(singleCalls == n && batchedCalls == 5)
    info(f"fake 10 ms/call, $n items: batchSize=1 -> $single%.1f vectors/s ($singleCalls calls)")
    info(
      f"fake 10 ms/call, $n items: batchSize=100 -> $batched%.1f vectors/s ($batchedCalls calls)"
    )
    assert(batched > single)
  }

  test("P26b: 10,000 items flow through the ingest main with a zero-latency fake embedder") {
    val fake = new RecordingEmbedder
    val report =
      ingest(live(10000, 100), 10000, new MemoryPorts(fake), "p26-10k").fold(fail(_), identity)
    assert(report("written").num == 10000 && report("rejected").num == 0)
    assert(fake.calls.size == 100 && report("embeddingBatch")("textsSent").str == "10000")
    info(
      f"zero-latency fake, 10,000 items, batchSize=100: ${report("vectorsPerSecond").num}%.1f vectors/s"
    )
  }

  // ----- Concurrent callers, ingestConcurrency and the run-ledger page capacity -----

  test("P26b: concurrent callers get correct vectors and each text is sent at most once") {
    val all = texts(1000)
    val fake = new RecordingEmbedder
    val batcher = new LookaheadBatchingEmbeddingClient(fake, all, 50)
    val reference = new DeterministicHashedEmbeddingClient(model)
    val pool = java.util.concurrent.Executors.newFixedThreadPool(16)
    try {
      // Roughly ordered, like 16 runner workers: each worker takes every 16th text.
      val futures = (0 until 16).map { w =>
        pool.submit(new java.util.concurrent.Callable[Vector[(String, EmbeddingResult)]] {
          def call(): Vector[(String, EmbeddingResult)] =
            all.indices
              .filter(_ % 16 == w)
              .toVector
              .map(i => all(i) -> batcher.embed(Seq(all(i))).head)
        })
      }
      val results = futures.flatMap(_.get(60, java.util.concurrent.TimeUnit.SECONDS)).toMap
      assert(results.size == 1000)
      all.foreach(t => assert(vector(results(t)) == vector(reference.embed(Seq(t)).head)))
    } finally pool.shutdownNow()
    val sentTexts = fake.calls.synchronized(fake.calls.flatten.toVector)
    assert(sentTexts.size == 1000 && sentTexts.distinct.size == 1000)
    assert(fake.calls.forall(_.size <= 50))
    assert(batcher.stats.textsSent == 1000 && batcher.stats.unusedPrefetched == 0)
  }

  test("P26b: ingestConcurrency is bounded, reaches the storage config and the old key default") {
    val config = live(100, 10).copy(ingestConcurrency = 8)
    assert(config.ingest.ingestConcurrency == 8)
    assert(live(100, 10).copy(ingestConcurrency = 16).ingest.ingestConcurrency == 16)
    intercept[IllegalArgumentException](live(100, 10).copy(ingestConcurrency = 0))
    intercept[IllegalArgumentException](live(100, 10).copy(ingestConcurrency = 17))
    // Round trip, and an existing config without the key reads as 1 (sequential).
    assert(upickle.default.read[LiveEmbeddingConfig](write(config)) == config)
    val old = upickle.default.writeJs(config)
    old.obj.remove("ingestConcurrency")
    assert(upickle.default.read[LiveEmbeddingConfig](old.render()).ingestConcurrency == 1)
  }

  test("P26b: preflight refuses ingestConcurrency above the approval's concurrencyCap") {
    val config = live(20, 10).copy(ingestConcurrency = 8)
    val refused = ingest(config, 20, new MemoryPorts(new RecordingEmbedder), "p26-cap", 4)
    assert(refused == Left("live-approval-ingest-concurrency-cap"))
    val report = ingest(config, 20, new MemoryPorts(new RecordingEmbedder), "p26-cap-ok", 8)
      .fold(fail(_), identity)
    assert(report("ingestConcurrency").num == 8 && report("written").num == 20)
  }

  test("P26b: live storage settings: one SDK attempt, ledger pages hold a 10,000-item run") {
    val settings = live(10000, 100).storageSettings
    assert(settings.retry.maxAttempts == 1 && settings.queryPageSize == 1000)
    assert(settings.bucket == "fixture-text" && settings.tables == tables)
    assert(live(10000, 100).ledgerRowsFit(10000) && live(10000, 100).ledgerRowsFit(99999))
    assert(!live(10000, 100).ledgerRowsFit(100000))
    // The storage default page size (100 x 100 pages) cannot hold the root plus 10,000 stages.
    val defaults = edu.uic.cs441.scholarchain.storage.StorageConfig("fixture-text", tables)
    assert(BigInt(defaults.queryPageSize) * defaults.maxQueryPages < 10001)
  }

  /** In-memory DynamoDB for the run-ledger table only, with real Query paging (Limit,
    * ExclusiveStartKey, LastEvaluatedKey) and the conditions DynamoRows sends (attribute_not_exists
    * and payload equality), so the real DynamoRunLedger runs unchanged against it.
    */
  private final class PagingDynamo {
    private val rows = mutable.Map.empty[String, java.util.TreeMap[String, Map[String, String]]]
    val queries = new java.util.concurrent.atomic.AtomicInteger
    private def attr(s: String) =
      software.amazon.awssdk.services.dynamodb.model.AttributeValue.builder().s(s).build()
    private def toJava(item: Map[String, String]) = item.map((k, v) => k -> attr(v)).asJava
    private def fromJava(
        m: java.util.Map[String, software.amazon.awssdk.services.dynamodb.model.AttributeValue]
    ) =
      m.asScala.map((k, v) => k -> Option(v.s()).getOrElse(v.n())).toMap
    private def existing(item: Map[String, String]) =
      Option(rows.getOrElse(item("runId"), new java.util.TreeMap()).get(item("stageKey")))
    private def holds(item: Map[String, String], condition: String, expected: Option[String]) =
      if (condition.startsWith("attribute_not_exists")) existing(item).isEmpty
      else existing(item).exists(r => expected.contains(r("payload")))
    private def store(item: Map[String, String]): Unit =
      rows.getOrElseUpdate(item("runId"), new java.util.TreeMap()).put(item("stageKey"), item)
    import software.amazon.awssdk.services.dynamodb.model.*
    private def expected(values: java.util.Map[String, AttributeValue]) =
      Option(values).flatMap(v => Option(v.get(":expected"))).map(_.s())
    val client: software.amazon.awssdk.services.dynamodb.DynamoDbClient =
      java.lang.reflect.Proxy
        .newProxyInstance(
          getClass.getClassLoader,
          Array(classOf[software.amazon.awssdk.services.dynamodb.DynamoDbClient]),
          (_, method, args) =>
            synchronized {
              (method.getName, Option(args).flatMap(_.headOption).orNull) match {
                case ("getItem", r: GetItemRequest) =>
                  val k = fromJava(r.key())
                  existing(k).fold(GetItemResponse.builder().build())(i =>
                    GetItemResponse.builder().item(toJava(i)).build()
                  )
                case ("putItem", r: PutItemRequest) =>
                  val item = fromJava(r.item())
                  if (
                    !holds(item, r.conditionExpression(), expected(r.expressionAttributeValues()))
                  )
                    throw ConditionalCheckFailedException.builder().message("condition").build()
                  store(item); PutItemResponse.builder().build()
                case ("transactWriteItems", r: TransactWriteItemsRequest) =>
                  val puts = r.transactItems().asScala.map(_.put()).toVector
                  val items = puts.map(p => fromJava(p.item()))
                  if (
                    !puts
                      .zip(items)
                      .forall((p, i) =>
                        holds(i, p.conditionExpression(), expected(p.expressionAttributeValues()))
                      )
                  )
                    throw TransactionCanceledException
                      .builder()
                      .cancellationReasons(
                        puts
                          .map(_ =>
                            CancellationReason.builder().code("ConditionalCheckFailed").build()
                          )
                          .asJava
                      )
                      .build()
                  items.foreach(store); TransactWriteItemsResponse.builder().build()
                case ("query", r: QueryRequest) =>
                  queries.incrementAndGet()
                  val pk = r.expressionAttributeValues().get(":pk").s()
                  val all = rows.getOrElse(pk, new java.util.TreeMap()).values.asScala.toVector
                  val after = Option(r.exclusiveStartKey())
                    .filterNot(_.isEmpty)
                    .map(k => k.get("stageKey").s())
                  val rest = after.fold(all)(a => all.filter(_("stageKey") > a))
                  val page = rest.take(r.limit())
                  val b = QueryResponse.builder().items(page.map(toJava).asJava)
                  if (rest.size > page.size)
                    b.lastEvaluatedKey(
                      Map("runId" -> attr(pk), "stageKey" -> attr(page.last("stageKey"))).asJava
                    )
                  b.build()
                case ("close", _)       => null
                case ("serviceName", _) => "dynamodb"
                case ("toString", _)    => "paging-dynamo-fake"
                case (other, _)         => throw new UnsupportedOperationException(other)
              }
            }
        )
        .asInstanceOf[software.amazon.awssdk.services.dynamodb.DynamoDbClient]
  }

  test("P26b: a 10,000-item run completes its DynamoDB run ledger with the live storage settings") {
    val config = live(10000, 100).copy(ingestConcurrency = 8)
    val dynamo = new PagingDynamo
    val ledger = new DynamoRunLedger(dynamo.client, config.storageSettings)
    val report = ingest(
      config,
      10000,
      new MemoryPorts(new RecordingEmbedder, ledger = ledger),
      "p26-ledger-10k",
      8
    ).fold(fail(_), identity)
    assert(report("written").num == 10000 && report("rejected").num == 0)
    assert(StorageResult.value(ledger.getRun("p26-ledger-10k")).exists(_.state == "complete"))
    info(
      f"10,000 items, ingestConcurrency 8, paged ledger fake: ${report("vectorsPerSecond").num}%.1f vectors/s"
    )
  }

  test("P26b control: the storage default page size fails the same run at completeRun") {
    val config = live(10000, 100).copy(ingestConcurrency = 8)
    val dynamo = new PagingDynamo
    val ledger = new DynamoRunLedger(
      dynamo.client,
      edu.uic.cs441.scholarchain.storage
        .StorageConfig("fixture-text", tables, retry = RetryConfig(maxAttempts = 1))
    )
    val result = ingest(
      config,
      10000,
      new MemoryPorts(new RecordingEmbedder, ledger = ledger),
      "p26-ledger-default",
      8
    )
    assert(result == Left("run-ledger-completion-failed"))
  }

  // ----- P38: tool logging -----

  private val wireLoggers =
    Vector("org.apache.http", "org.apache.hc", "software.amazon.awssdk", "io.netty")
  private val token = "synthetic-p38-rag-session-token"
  private def isWire(e: ILoggingEvent) =
    wireLoggers.exists(n => e.getLoggerName == n || e.getLoggerName.startsWith(n + "."))

  /** What an SDK client at DEBUG would emit; the fake ports call it during the run. */
  private def emitWireLines(): Unit = {
    LoggerFactory.getLogger("software.amazon.awssdk.request").debug(s"X-Amz-Security-Token: $token")
    LoggerFactory
      .getLogger("org.apache.http.wire")
      .debug(s">> \"Authorization: AWS4-HMAC-SHA256 $token\"")
    LoggerFactory.getLogger("org.apache.hc.client5.http.wire").debug(s"header $token")
    LoggerFactory.getLogger("io.netty.handler.logging.LoggingHandler").debug(s"frame $token")
  }

  private def context = LoggerFactory.getILoggerFactory.asInstanceOf[LoggerContext]

  private def withProperty[A](value: Option[String])(body: => A): A = {
    val previous = Option(System.getProperty(ToolLogging.property))
    value.fold(System.clearProperty(ToolLogging.property))(
      System.setProperty(ToolLogging.property, _)
    )
    try body
    finally {
      previous.fold(System.clearProperty(ToolLogging.property))(
        System.setProperty(ToolLogging.property, _)
      )
      val ctx = context
      ctx.reset()
      new ContextInitializer(ctx).autoConfig()
    }
  }

  private def capture[A](ctx: LoggerContext)(body: => A): (A, Vector[ILoggingEvent]) = {
    val root = ctx.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME)
    val appender = new ListAppender[ILoggingEvent]
    appender.setContext(ctx); appender.start(); root.addAppender(appender)
    try { val r = body; (r, appender.list.asScala.toVector) }
    finally { root.detachAppender(appender); appender.stop() }
  }

  private def runWithWireNoise(): Either[String, ujson.Value] = {
    val fake = new RecordingEmbedder(onCall = () => emitWireLines())
    ingest(live(20, 10), 20, new MemoryPorts(fake, () => emitWireLines()), "p38-run")
  }

  test("P38: the three rag tool mains install the packaged tool logging before any work") {
    Vector[Array[String] => Unit](
      EmbeddingManifestMain.main,
      LiveEmbeddingIngestMain.main,
      LiveEmbeddingSmokeMain.main
    ).foreach { main =>
      withProperty(None) {
        intercept[IllegalArgumentException](main(Array("--p38-unknown-flag")))
        assert(System.getProperty(ToolLogging.property) == ToolLogging.resource)
      }
      withProperty(Some("/operator/chosen.xml")) {
        intercept[IllegalArgumentException](main(Array("--p38-unknown-flag")))
        assert(System.getProperty(ToolLogging.property) == "/operator/chosen.xml")
      }
    }
  }

  test("P38: an ingest run against fakes logs its INFO event and no DEBUG wire line or token") {
    withProperty(None) {
      ToolLogging.install()
      val ctx = context
      ctx.reset()
      new ContextInitializer(ctx).autoConfig()
      val source = ConfigurationWatchListUtil.getMainWatchURL(ctx)
      assert(source != null && source.toString.endsWith("/" + ToolLogging.resource), source)
      val (result, events) = capture(ctx)(runWithWireNoise())
      assert(result.isRight, result)
      assert(
        events.exists(e =>
          e.getLevel == Level.INFO && e.getFormattedMessage.contains("embedding_ingest")
        )
      )
      assert(!events.exists(_.getLevel.toInt < Level.INFO.toInt), events.map(_.getFormattedMessage))
      assert(!events.exists(isWire))
      assert(!events.exists(_.getFormattedMessage.contains(token)))
    }
  }

  test("P38 control: with logback's DEBUG default the same run does emit the wire lines") {
    withProperty(None) {
      val ctx = context
      ctx.reset()
      ctx.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME).setLevel(Level.DEBUG)
      val (result, events) = capture(ctx)(runWithWireNoise())
      assert(result.isRight)
      assert(events.exists(e => isWire(e) && e.getLevel == Level.DEBUG))
      assert(events.exists(_.getFormattedMessage.contains(token)))
    }
  }
}
