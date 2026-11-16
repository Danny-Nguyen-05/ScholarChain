package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.util.concurrent.ThreadLocalRandom
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*
import software.amazon.awssdk.services.dynamodb.DynamoDbClient
import software.amazon.awssdk.services.dynamodb.model.*
import IngestThroughputFixture.*

/** Session 2 plan P26 (b), lane G: per-item call profile, latency-injected throughput, concurrency
  * safety, resume and caps of the storage `EmbeddingManifestRunner` in the live composition (see
  * `IngestThroughputFixture` for the fakes and the provenance of every injected latency).
  */
class IngestThroughputSpec extends AnyFunSuite {
  private val base = EmbeddingIngestConfig("fixture-text", "rag", 2)
  private def ok(r: StorageResult[EmbeddingIngestReport]): EmbeddingIngestReport =
    StorageResult.value(r).getOrElse(fail(s"run failed: $r"))
  private def texts(m: EmbeddingManifest) = m.items.map(_.document.text)
  private def jitter: CallMeter =
    new CallMeter(_ => ThreadLocalRandom.current().nextLong(0L, 300000L))
  private def run(stores: Stores, id: String): RunRecord =
    StorageResult.value(stores.ledger.getRun(id)).get

  test("ingestConcurrency: default 1, accepted 1..16, refused outside with a typed message") {
    assert(base.ingestConcurrency == 1)
    assert(EmbeddingIngestConfig.MaxIngestConcurrency == 16)
    Seq(1, 8, 16).foreach(n => assert(base.copy(ingestConcurrency = n).ingestConcurrency == n))
    Seq(0, -1, 17, Int.MaxValue).foreach { n =>
      val e = intercept[IllegalArgumentException](base.copy(ingestConcurrency = n))
      assert(e.getMessage.contains("invalid-ingest-concurrency"))
    }
  }

  test("call profile: AWS API calls per fresh and per unchanged item; concurrency adds none") {
    val n = 40
    def profile(workers: Int): (Map[String, Long], Map[String, Long], LookaheadEmbedder) = {
      val config = base.copy(ingestConcurrency = workers)
      val stores = new Stores(new CallMeter)
      val manifest = IngestThroughputFixture.manifest(n, config, oneIndex = true)
      val embedder = new LookaheadEmbedder(model, texts(manifest), 100, stores.meter)
      val first = ok(stores.runner(config, embedder).run(manifest, "profile-1"))
      assert(first.written == n && first.rejected == 0)
      val fresh = stores.meter.snapshot
      val second = ok(stores.runner(config, embedder).run(manifest, "profile-2"))
      assert(second.unchanged == n && second.written == 0 && second.embeddingCalls == 0)
      val replay = stores.meter.snapshot
        .map((k, v) => k -> (v - fresh.getOrElse(k, 0L)))
        .filter(_._2 > 0)
      (fresh, replay, embedder)
    }
    val (fresh, replay, _) = profile(1)
    info(s"FRESH run of $n items, one index, batchSize ${base.batchSize}, one worker:")
    fresh.toVector.sortBy(_._1).foreach { (k, v) =>
      info(f"$k%-34s total=$v%5d perItem=${v.toDouble / n}%.3f")
    }
    info(s"REPLAY (all unchanged) run of the same $n items:")
    replay.toVector.sortBy(_._1).foreach { (k, v) =>
      info(f"$k%-34s total=$v%5d perItem=${v.toDouble / n}%.3f")
    }
    // Per fresh item: ledger 3 + 3 (recordStage, completeStage), registry 6 reads and 7
    // conditional writes, 2 S3 puts (text, prepared vector); per run: startRun, getRun,
    // completeRun; per batch: one PutVectors and one embedding request.
    assert(
      fresh == Map(
        "ddb.ledger.GetItem" -> (4L * n + 3),
        "ddb.ledger.TransactWriteItems" -> 2L * n,
        "ddb.ledger.PutItem" -> 2L,
        "ddb.ledger.Query" -> 2L,
        "ddb.registry.GetItem" -> 6L * n,
        "ddb.registry.PutItem" -> 7L * n,
        "s3.PutObject" -> 2L * n,
        "s3vectors.PutVectors" -> 1L,
        "voyage.embed" -> 1L
      )
    )
    assert(
      replay == Map(
        "ddb.ledger.GetItem" -> (4L * n + 3),
        "ddb.ledger.TransactWriteItems" -> 2L * n,
        "ddb.ledger.PutItem" -> 2L,
        "ddb.ledger.Query" -> 2L,
        "ddb.registry.GetItem" -> 4L * n,
        "ddb.registry.PutItem" -> 1L * n
      )
    )
    // Eight workers make exactly the same storage calls. Only the embedding request count may
    // grow (texts that reach the lookahead out of manifest order start their own request); every
    // text is still requested once.
    val (fresh8, replay8, embedder8) = profile(8)
    assert(fresh8 - "voyage.embed" == fresh - "voyage.embed" && replay8 == replay)
    assert(embedder8.perText.size == n && embedder8.perText.values.asScala.forall(_.get == 1))
    info(s"eight workers: voyage.embed requests=${fresh8("voyage.embed")} for $n texts")
  }

  test("latency-injected throughput: one worker vs bounded concurrency (scale 1/20)") {
    val scale = 20L
    // 100 items per index and 50 per batch: every vector batch fills during the run, as it does
    // at 10,000 items with batchSize 100, so the end-of-run flush does not dominate.
    val n = 400
    val target = IngestLatency.StorageCallNanos / scale
    val calibrationStart = System.nanoTime()
    (1 to 200).foreach(_ => CallMeter.pause(target))
    info(
      f"pause calibration: target=${target / 1e6}%.3fms observed=${(System.nanoTime() - calibrationStart) / 200 / 1e6}%.3fms"
    )
    def measure(workers: Int): Double = {
      val config = base.copy(batchSize = 50, ingestConcurrency = workers)
      val stores = new Stores(new CallMeter(scaledDelay(scale)))
      val manifest = IngestThroughputFixture.manifest(n, config)
      val embedder =
        new LookaheadEmbedder(model, texts(manifest), config.batchSize, stores.meter)
      val report = ok(stores.runner(config, embedder).run(manifest, s"latency-$workers"))
      assert(report.written == n && report.rejected == 0)
      val liveSeconds = report.elapsedNanos.toDouble * scale / 1e9
      val liveVps = n / liveSeconds
      info(
        f"workers=$workers n=$n scaledElapsed=${report.elapsedNanos / 1e9}%.2fs liveEquivalent=$liveSeconds%.1fs " +
          f"liveVectorsPerSecond=$liveVps%.3f projected10000=${10000 / liveVps / 60}%.1fmin " +
          s"embeddingRequests=${stores.meter.snapshot.getOrElse("voyage.embed", 0L)}"
      )
      liveVps
    }
    val one = measure(1)
    val four = measure(4)
    val eight = measure(8)
    // Ledger-bound ceiling: 6 serialized ledger calls per item.
    info(
      f"ledger-bound ceiling at L=${IngestLatency.StorageCallNanos / 1e6}%.1fms: " +
        f"${1e9 / (6.0 * IngestLatency.StorageCallNanos)}%.3f vectors/s"
    )
    assert(eight >= 2.0 * one, s"eight workers $eight vs one worker $one vectors/s")
    assert(four >= 1.5 * one, s"four workers $four vs one worker $one vectors/s")
  }

  test("concurrency safety: no double write, consistent ledger, each text embedded once") {
    val n = 300
    val config = base.copy(batchSize = 25, ingestConcurrency = 8)
    val stores = new Stores(jitter)
    val manifest = IngestThroughputFixture.manifest(n, config)
    val embedder = new FixedEmbedder(model)
    val report = ok(stores.runner(config, embedder).run(manifest, "safety-1"))
    assert(report.written == n && report.unchanged == 0 && report.rejected == 0)
    assert(report.embeddingCalls == n && report.retried == 0)
    assert(report.perIndex.values.toSet == Set(n / types.size) && report.perIndex.size == 4)
    val keys = stores.putKeys
    assert(keys.size == n && keys.distinct.size == n)
    assert(keys.toSet == manifest.items.map(_.vectorKey).toSet)
    assert(stores.puts.asScala.forall(p => p.vectors.nonEmpty && p.vectors.size <= 25))
    assert(embedder.perText.size == n && embedder.perText.values.asScala.forall(_.get == 1))
    val writes = stores.objects.underlying.writeOrder.toVector
    assert(writes.size == 2 * n && writes.distinct.size == writes.size)
    val record = run(stores, "safety-1")
    assert(record.state == "complete" && record.failures.isEmpty)
    assert(record.stages.size == n && record.stages.forall(s => s.state == "complete"))
    assert(record.stages.forall(_.retryCount == 0))
    // Every transition bumped the root revision exactly once: none was lost or conflicted.
    assert(record.revision == 2L * n + 1)
    assert(manifest.items.forall(stores.runnerComplete))

    val replay = ok(stores.runner(config, embedder).run(manifest, "safety-2"))
    assert(replay.unchanged == n && replay.written == 0 && replay.embeddingCalls == 0)
    assert(stores.putKeys.size == n)
  }

  test("deterministic per-item results: one worker and eight workers give the same report") {
    val config = base.copy(maxTextBytes = 200, batchSize = 7)
    val valid = IngestThroughputFixture.manifest(120, config).items
    val long = EmbeddingManifests.item(doc(900, "paper", "x" * 300), model, config)
    val clashA = EmbeddingManifests.item(doc(901, "community", "first wording"), model, config)
    val clashB = EmbeddingManifests.item(doc(901, "community", "second wording"), model, config)
    val manifest = EmbeddingManifest(
      valid.take(60) ++ Vector(long, clashA, valid(6)) ++ valid.drop(60) ++
        Vector(clashB, valid(5), valid(6))
    )
    def once(workers: Int) = {
      val stores = new Stores(if (workers == 1) new CallMeter else jitter)
      val embedder = new FixedEmbedder(model, _.contains("number 17 "))
      val r = ok(
        stores.runner(config.copy(ingestConcurrency = workers), embedder).run(manifest, "same")
      )
      val puts = stores.puts.asScala.toVector.flatMap(_.vectors).toMap
      (r.copy(elapsedNanos = 0), puts)
    }
    val (sequential, sequentialPuts) = once(1)
    val (concurrent, concurrentPuts) = once(8)
    val (again, againPuts) = once(8)
    info(
      s"written=${sequential.written} unchanged=${sequential.unchanged} rejected=${sequential.rejected} " +
        s"reasons=${sequential.rejections.map(_.reason).distinct}"
    )
    // Repeated copies of an item fail their group binding (a chunk ordinal twice), the clashing
    // pair conflicts, one text is too long and one embedding fails: 2 + 3 + 2 + 1 + 1.
    assert(sequential.rejected == 9 && sequential.unchanged == 0 && sequential.written == 117)
    assert(sequential.vectorKeyTextConflict == 2)
    assert(sequential.rejections.count(_.reason == "incomplete-embedding-group") == 5)
    assert(sequential.rejections.exists(_.reason == "text-byte-limit"))
    assert(sequential.rejections.exists(_.reason == "embedding-provider-unavailable"))
    assert(concurrent == sequential && again == sequential)
    assert(concurrentPuts == sequentialPuts && againPuts == sequentialPuts)
  }

  test("resume after a crash mid-run under concurrency: no re-embedding, no double write") {
    val n = 300
    val config = base.copy(batchSize = 25, ingestConcurrency = 8)
    val stores = new Stores(jitter)
    val manifest = IngestThroughputFixture.manifest(n, config)
    val embedder = new FixedEmbedder(model)
    val crashing = new CrashingRegistry(stores.registry, after = 30)
    val crash = intercept[IllegalStateException] {
      stores.runner(config, embedder, crashing).run(manifest, "crash-1")
    }
    assert(crash.getMessage == "simulated-crash")
    val completeAfterCrash = manifest.items.count(stores.runnerComplete)
    val putAfterCrash = stores.putKeys.size
    val embeddedBeforeResume = embedder.perText.size
    info(s"after the crash: runner-complete=$completeAfterCrash vector keys written=$putAfterCrash")
    assert(completeAfterCrash < n && run(stores, "crash-1").state == "running")

    val resumed = ok(stores.runner(config, embedder).run(manifest, "crash-2"))
    assert(resumed.rejected == 0 && resumed.written + resumed.unchanged == n)
    assert(resumed.written == n - putAfterCrash)
    assert(manifest.items.forall(stores.runnerComplete))
    // Each text was embedded once over both runs; each vector key was written once.
    assert(embedder.perText.size == n && embedder.perText.values.asScala.forall(_.get == 1))
    assert(resumed.embeddingCalls == n - embeddedBeforeResume)
    val keys = stores.putKeys
    assert(keys.size == n && keys.distinct.size == n)
    val record = run(stores, "crash-2")
    assert(record.state == "complete" && record.stages.forall(_.state == "complete"))
  }

  test("resume after a provider failure mid-run: only the rejected items are embedded again") {
    val n = 300
    val config = base.copy(batchSize = 25, ingestConcurrency = 8)
    val stores = new Stores(jitter)
    val manifest = IngestThroughputFixture.manifest(n, config)
    val failing =
      new LookaheadEmbedder(model, texts(manifest), 50, stores.meter, failAfter = 2)
    val first = ok(stores.runner(config, failing).run(manifest, "provider-1"))
    info(s"run 1: written=${first.written} rejected=${first.rejected}")
    assert(first.written > 0 && first.rejected > 0 && first.written + first.rejected == n)
    assert(first.rejections.forall(_.reason == "embedding-provider-unavailable"))
    assert(first.rejectedReportUri.nonEmpty && run(stores, "provider-1").state == "running")
    val doneFirst = manifest.items.filter(stores.runnerComplete).map(_.document.text).toSet
    assert(doneFirst.size == first.written)

    val healthy = new FixedEmbedder(model)
    val second = ok(stores.runner(config, healthy).run(manifest, "provider-2"))
    assert(second.rejected == 0 && second.written == first.rejected)
    assert(second.unchanged == first.written)
    assert(healthy.perText.keySet.asScala.toSet == texts(manifest).toSet -- doneFirst)
    assert(healthy.perText.values.asScala.forall(_.get == 1))
    val keys = stores.putKeys
    assert(keys.size == n && keys.distinct.size == n)
    assert(run(stores, "provider-2").state == "complete")
  }

  test("caps hold under concurrency: manifest item limit and a client-side embedding cap") {
    val limited = base.copy(maxManifestItems = 10, ingestConcurrency = 8)
    val stores = new Stores(new CallMeter)
    val embedder = new FixedEmbedder(model)
    val over = IngestThroughputFixture.manifest(11, limited)
    assert(
      stores.runner(limited, embedder).run(over, "cap-items") == StorageResult.Rejected(
        "manifest-item-limit"
      )
    )
    assert(stores.meter.snapshot.isEmpty && embedder.perText.isEmpty)

    def capped(workers: Int) = {
      val config = base.copy(batchSize = 25, ingestConcurrency = workers)
      val s = new Stores(jitter)
      val e = new CappedEmbedder(model, 37)
      val r = ok(s.runner(config, e).run(IngestThroughputFixture.manifest(300, config), "cap"))
      (r, e, s)
    }
    Seq(1, 8).foreach { workers =>
      val (r, e, s) = capped(workers)
      assert(e.asked.get == 300, s"workers=$workers: each item asks the embedder once")
      assert(r.written == 37 && r.embeddingCalls == 37 && r.rejected == 263)
      assert(r.rejections.forall(_.reason == "embedding-call-cap"))
      assert(s.putKeys.size == 37 && s.putKeys.distinct.size == 37)
    }
  }

  test("run ledger paging: a 10,000-stage run exceeds the default query bound (100 x 100 rows)") {
    val runId = "run-paging"
    def client(stages: Int): DynamoDbClient = {
      def s(v: String) = AttributeValue.builder().s(v).build()
      def row(sk: String, payload: String) =
        Map("runId" -> s(runId), "stageKey" -> s(sk), "payload" -> s(payload)).asJava
      val root = row("RUN", RowCodec.encode(RunRecord(runId, "running", Vector.empty)))
      val rows = root +: (0 until stages).toVector.map { k =>
        val stage = f"embedding-$k%05d"
        row("STAGE#" + stage, RowCodec.encode(RunStage(stage, "complete", 0, None)))
      }
      Proxy
        .newProxyInstance(
          getClass.getClassLoader,
          Array(classOf[DynamoDbClient]),
          new InvocationHandler {
            def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef =
              method.getName match {
                case "getItem" => GetItemResponse.builder().item(root).build()
                case "putItem" => PutItemResponse.builder().build()
                case "query" =>
                  val q = args.head.asInstanceOf[QueryRequest]
                  val from =
                    if (!q.hasExclusiveStartKey || q.exclusiveStartKey.isEmpty) 0
                    else
                      rows.indexWhere(
                        _.get("stageKey").s == q.exclusiveStartKey.get("stageKey").s
                      ) + 1
                  val page = rows.slice(from, from + q.limit)
                  val b = QueryResponse.builder().items(page.asJava)
                  if (from + page.size < rows.size)
                    b.lastEvaluatedKey(
                      Map("runId" -> s(runId), "stageKey" -> page.last.get("stageKey")).asJava
                    )
                  b.build()
                case "serviceName" => "dynamodb"
                case "close"       => null
                case "hashCode"    => Int.box(System.identityHashCode(proxy))
                case "equals"      => Boolean.box(false)
                case "toString"    => "fake-dynamodb"
                case other         => throw new UnsupportedOperationException(other)
              }
          }
        )
        .asInstanceOf[DynamoDbClient]
    }
    val tables =
      DynamoTables("runs", "links", "sessions", "evidence", "artifacts", "metrics", "gsi")
    val defaults = edu.uic.cs441.scholarchain.storage.StorageConfig("bucket", tables)
    assert(defaults.queryPageSize == 100 && defaults.maxQueryPages == 100)
    // 9,999 stages + the run row = 100 full pages: within the bound.
    assert(
      StorageResult
        .value(new DynamoRunLedger(client(9999), defaults).getRun(runId))
        .get
        .stages
        .size == 9999
    )
    // 10,000 stages + the run row: the 101st page is refused, so completeRun cannot succeed.
    val atTenThousand = new DynamoRunLedger(client(10000), defaults)
    assert(atTenThousand.getRun(runId) == StorageResult.Rejected("query-page-limit"))
    assert(!StorageResult.successful(atTenThousand.completeRun(runId)))
    // The fix is configuration only: 1,000 rows per page (a stage row is about 200 bytes, far
    // below DynamoDB's 1 MB page) bounds a run at 100,000 rows.
    val wider = new DynamoRunLedger(client(10000), defaults.copy(queryPageSize = 1000))
    assert(StorageResult.value(wider.getRun(runId)).get.stages.size == 10000)
    assert(StorageResult.successful(wider.completeRun(runId)))
  }
}
