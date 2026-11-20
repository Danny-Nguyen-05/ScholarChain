package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.io.{ByteArrayOutputStream, PrintStream}
import java.util.concurrent.{ConcurrentLinkedQueue, CountDownLatch, Executors, TimeUnit}
import java.util.concurrent.atomic.{AtomicBoolean, AtomicReference}
import scala.jdk.CollectionConverters.*

/** P40 query-embedding cache. Every underlying client is an in-memory counting fake; no network,
  * AWS or provider call is made. Expected call lists and counters are derived by hand in each test.
  */
class CachingEmbeddingClientSpec extends AnyFunSuite {
  private val voyageModel = EmbeddingModel("voyage-4-lite", "voyage-4-lite", 4)
  private val titanModel = EmbeddingModel("amazon.titan-embed-text-v2:0", "v2", 4)

  /** A distinct, finite 4-value vector per text, attempts 1. */
  private def vectorFor(text: String): Vector[Float] =
    Vector.tabulate(4)(i => (math.abs(text.hashCode % 997) + i * 1000).toFloat)
  private def expected(text: String, model: EmbeddingModel = voyageModel): EmbeddingSuccess =
    EmbeddingSuccess(vectorFor(text), model, 1)

  /** Thread-safe counting fake. `respond` decides the reply for each underlying call. */
  private final class CountingEmbedder(val model: EmbeddingModel) extends EmbeddingClient {
    val calls = new ConcurrentLinkedQueue[Vector[String]]()
    val respond = new AtomicReference[Vector[String] => Seq[EmbeddingResult]](batch =>
      batch.map(text => EmbeddingSuccess(vectorFor(text), model, 1))
    )
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = {
      val batch = texts.toVector
      calls.add(batch)
      respond.get()(batch)
    }
    def callList: Vector[Vector[String]] = calls.asScala.toVector
    def textsSent: Int = calls.asScala.map(_.size).sum
  }

  private final class ProviderFake(val model: EmbeddingModel, val provider: EmbeddingProvider)
      extends ProviderEmbeddingClient {
    def embed(texts: Seq[String]): Seq[EmbeddingResult] =
      texts.map(text => EmbeddingSuccess(vectorFor(text), model, 1))
  }

  test("one underlying call per distinct text across repeated calls") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 16)
    assert(cache.embed(Vector("a")) == Vector(expected("a")))
    assert(cache.embed(Vector("a")) == Vector(expected("a")))
    assert(cache.embed(Vector("b")) == Vector(expected("b")))
    assert(cache.embed(Vector("a")) == Vector(expected("a")))
    assert(cache.embed(Vector("b")) == Vector(expected("b")))
    assert(fake.callList == Vector(Vector("a"), Vector("b")))
    assert(cache.stats == EmbeddingCacheStats(hits = 3, misses = 2, evictions = 0, size = 2, 16))
  }

  test("an empty call and an all-hit call make no underlying call") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 4)
    assert(cache.embed(Vector.empty) == Vector.empty)
    assert(fake.callList.isEmpty)
    cache.embed(Vector("a", "b"))
    assert(
      cache.embed(Vector("b", "a", "b")) == Vector(expected("b"), expected("a"), expected("b"))
    )
    assert(fake.callList == Vector(Vector("a", "b")))
    assert(cache.stats == EmbeddingCacheStats(3, 2, 0, 2, 4))
  }

  test("duplicates within one call are sent once and all positions answered") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 16)
    val out = cache.embed(Vector("a", "b", "a", "a", "b"))
    assert(out == Vector("a", "b", "a", "a", "b").map(expected(_)))
    assert(fake.callList == Vector(Vector("a", "b")))
    // two distinct misses; the three repeated positions are hits
    assert(cache.stats == EmbeddingCacheStats(3, 2, 0, 2, 16))
    assert(cache.embed(Vector("b", "a")) == Vector(expected("b"), expected("a")))
    assert(fake.callList.size == 1)
    assert(cache.stats == EmbeddingCacheStats(5, 2, 0, 2, 16))
  }

  test("mixed hits and misses keep input order; only distinct misses are sent, in order") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 16)
    cache.embed(Vector("b"))
    val out = cache.embed(Vector("c", "b", "a", "c", "d"))
    assert(out == Vector(expected("c"), expected("b"), expected("a"), expected("c"), expected("d")))
    assert(fake.callList == Vector(Vector("b"), Vector("c", "a", "d")))
    // hits: cached b (1) + repeated c (1); misses: b, then c, a, d
    assert(cache.stats == EmbeddingCacheStats(2, 4, 0, 4, 16))
  }

  test("exact text is the key: case and whitespace variants are distinct entries") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 16)
    cache.embed(Vector("Who", "who", "who "))
    assert(fake.callList == Vector(Vector("Who", "who", "who ")))
    assert(cache.stats.size == 3)
  }

  test("LRU eviction order and exact eviction count at capacity 2") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 2)
    cache.embed(Vector("a")) // miss: [a]
    cache.embed(Vector("b")) // miss: [a, b]
    cache.embed(Vector("a")) // hit:  [b, a]
    cache.embed(Vector("c")) // miss, evict b: [a, c]
    cache.embed(Vector("a")) // hit:  [c, a]
    cache.embed(Vector("b")) // miss, evict c: [a, b]
    cache.embed(Vector("c")) // miss, evict a: [b, c]
    assert(fake.callList == Vector("a", "b", "c", "b", "c").map(Vector(_)))
    assert(cache.stats == EmbeddingCacheStats(2, 5, 3, 2, 2))
    assert(cache.embed(Vector("b", "c")) == Vector(expected("b"), expected("c"))) // both hits
    assert(fake.callList.size == 5)
    assert(cache.embed(Vector("a")) == Vector(expected("a"))) // miss, evict b: [c, a]
    assert(fake.callList.last == Vector("a"))
    assert(cache.stats == EmbeddingCacheStats(4, 6, 4, 2, 2))
  }

  test("one call with more distinct misses than capacity returns all and keeps the newest") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 2)
    assert(cache.embed(Vector("x", "y", "z")) == Vector("x", "y", "z").map(expected(_)))
    assert(cache.stats == EmbeddingCacheStats(0, 3, 1, 2, 2))
    cache.embed(Vector("y", "z"))
    assert(fake.callList.size == 1)
    cache.embed(Vector("x"))
    assert(fake.callList == Vector(Vector("x", "y", "z"), Vector("x")))
    assert(cache.stats == EmbeddingCacheStats(2, 4, 2, 2, 2))
  }

  test("a thrown failure propagates unchanged, is not cached, and is retried next time") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 4)
    val boom = new RuntimeException("embedding-provider-down")
    fake.respond.set(_ => throw boom)
    val thrown = intercept[RuntimeException](cache.embed(Vector("a", "a")))
    assert(thrown eq boom)
    // one distinct text was sent; the repeated position is not counted as a hit on failure
    assert(cache.stats == EmbeddingCacheStats(0, 1, 0, 0, 4))
    fake.respond.set(batch => batch.map(text => EmbeddingSuccess(vectorFor(text), voyageModel, 1)))
    assert(cache.embed(Vector("a")) == Vector(expected("a")))
    assert(fake.callList == Vector(Vector("a"), Vector("a")))
    assert(cache.stats == EmbeddingCacheStats(0, 2, 0, 1, 4))
  }

  test("EmbeddingFailure values are returned, never cached; successes beside them are cached") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 4)
    val failure = EmbeddingFailure("embedding-retries-exhausted", true, voyageModel, 3)
    fake.respond.set(batch =>
      batch.map(text =>
        if (text == "bad") failure else EmbeddingSuccess(vectorFor(text), voyageModel, 1)
      )
    )
    assert(cache.embed(Vector("bad", "ok", "bad")) == Vector(failure, expected("ok"), failure))
    assert(cache.stats == EmbeddingCacheStats(1, 2, 0, 1, 4))
    cache.embed(Vector("ok"))
    cache.embed(Vector("bad"))
    assert(fake.callList == Vector(Vector("bad", "ok"), Vector("bad")))
    assert(cache.stats == EmbeddingCacheStats(2, 3, 0, 1, 4))
  }

  test("a short or long underlying result throws a closed code and caches nothing") {
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 4)
    fake.respond.set(batch =>
      batch.take(1).map(t => EmbeddingSuccess(vectorFor(t), voyageModel, 1))
    )
    val short = intercept[IllegalStateException](cache.embed(Vector("a", "b")))
    assert(short.getMessage == CachingEmbeddingClient.ResultCountMismatch)
    assert(cache.stats.size == 0)
    fake.respond.set(batch =>
      (batch :+ "extra").map(t => EmbeddingSuccess(vectorFor(t), voyageModel, 1))
    )
    val long = intercept[IllegalStateException](cache.embed(Vector("a")))
    assert(long.getMessage == CachingEmbeddingClient.ResultCountMismatch)
    fake.respond.set(batch => batch.map(_ => null))
    val nulls = intercept[IllegalStateException](cache.embed(Vector("a")))
    assert(nulls.getMessage == CachingEmbeddingClient.NullResult)
    assert(cache.stats == EmbeddingCacheStats(0, 4, 0, 0, 4))
    fake.respond.set(batch => batch.map(text => EmbeddingSuccess(vectorFor(text), voyageModel, 1)))
    assert(cache.embed(Vector("a", "b")) == Vector(expected("a"), expected("b")))
    // short, long and null-element calls, then the retry; nothing was cached before it
    assert(
      fake.callList == Vector(Vector("a", "b"), Vector("a"), Vector("a"), Vector("a", "b"))
    )
    assert(cache.stats == EmbeddingCacheStats(0, 6, 0, 2, 4))
  }

  test("a malformed success is returned unchanged and nothing from that response is cached") {
    val wrongDimension = EmbeddingSuccess(Vector(1f, 2f), voyageModel, 1)
    val wrongModel = EmbeddingSuccess(vectorFor("a"), titanModel, 1)
    val nonFinite = EmbeddingSuccess(Vector(1f, Float.NaN, 0f, 0f), voyageModel, 1)
    Vector(wrongDimension, wrongModel, nonFinite).foreach { bad =>
      val fake = new CountingEmbedder(voyageModel)
      val cache = new CachingEmbeddingClient(fake, 4)
      fake.respond.set(batch =>
        batch.map(text =>
          if (text == "a") bad else EmbeddingSuccess(vectorFor(text), voyageModel, 1)
        )
      )
      assert(cache.embed(Vector("a", "b")) == Vector(bad, expected("b")))
      assert(cache.stats == EmbeddingCacheStats(0, 2, 0, 0, 4))
      cache.embed(Vector("b"))
      assert(fake.callList == Vector(Vector("a", "b"), Vector("b")))
    }
  }

  test("null texts pass through to the underlying client and are never cached") {
    val fake = new CountingEmbedder(voyageModel)
    val failure = EmbeddingFailure("empty-document-text", false, voyageModel, 0)
    fake.respond.set(batch =>
      batch.map(text =>
        if (text == null) failure else EmbeddingSuccess(vectorFor(text), voyageModel, 1)
      )
    )
    val cache = new CachingEmbeddingClient(fake, 4)
    assert(cache.embed(Vector(null, "a", null)) == Vector(failure, expected("a"), failure))
    assert(fake.callList == Vector(Vector(null, "a")))
    cache.embed(Vector(null))
    assert(fake.callList.size == 2)
    assert(cache.stats.size == 1)
  }

  test("model identity and provider pass through, so VectorConsistency.checkClient is unchanged") {
    val plain = new CountingEmbedder(voyageModel)
    val cachedPlain = new CachingEmbeddingClient(plain, 4)
    assert(cachedPlain.model eq plain.model)
    assert(cachedPlain.provider == EmbeddingProvider.Voyage)

    val titan = new ProviderFake(titanModel, EmbeddingProvider.Bedrock)
    val cachedTitan = new CachingEmbeddingClient(titan, 4)
    assert(cachedTitan.model == titanModel && cachedTitan.provider == EmbeddingProvider.Bedrock)

    val key = VoyageApiKey.fromValue("synthetic-placeholder-not-a-key").toOption.get
    val voyageConfig = VoyageEmbeddingConfig(EmbeddingInputType.Query)
    val voyage = new VoyageEmbeddingClient(key, voyageConfig) // constructed only; never called
    val cachedVoyage = new CachingEmbeddingClient(voyage)
    assert(cachedVoyage.model == voyage.model && cachedVoyage.provider == voyage.provider)

    val stores = Vector(
      EmbeddingProvider.Voyage -> voyageModel,
      EmbeddingProvider.Voyage -> VoyageDefaults.Model,
      EmbeddingProvider.Bedrock -> titanModel,
      EmbeddingProvider.Bedrock -> voyageModel,
      EmbeddingProvider.Voyage -> voyageModel.copy(dimension = 8)
    )
    Vector[(EmbeddingClient, EmbeddingClient)](
      plain -> cachedPlain,
      titan -> cachedTitan,
      voyage -> cachedVoyage
    ).foreach { (raw, cached) =>
      stores.foreach { (provider, stored) =>
        assert(
          VectorConsistency.checkClient(provider, stored, cached) ==
            VectorConsistency.checkClient(provider, stored, raw)
        )
      }
    }
    assert(
      VectorConsistency.checkClient(EmbeddingProvider.Voyage, voyageModel, cachedPlain).isRight
    )
    assert(
      VectorConsistency.checkClient(EmbeddingProvider.Bedrock, voyageModel, cachedPlain) ==
        Left(VectorConsistencyError("provider"))
    )
  }

  test("maxEntries must be positive; the default is 1,024") {
    val fake = new CountingEmbedder(voyageModel)
    Vector(0, -1, Int.MinValue).foreach { size =>
      val error = intercept[IllegalArgumentException](new CachingEmbeddingClient(fake, size))
      assert(error.getMessage.contains("invalid-embedding-cache-size"))
    }
    assert(CachingEmbeddingClient.DefaultMaxEntries == 1024)
    assert(new CachingEmbeddingClient(fake).stats == EmbeddingCacheStats(0, 0, 0, 0, 1024))
    assert(new CachingEmbeddingClient(fake, 1).capacity == 1)
  }

  test("keys, stats, toString, errors and console output never contain the question text") {
    val sentinel = "SENTINEL-QUESTION-q7zx who collaborates with Ada Lovelace?"
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 4)
    val captured = new ByteArrayOutputStream()
    val (out, err) = (System.out, System.err)
    val sink = new PrintStream(captured, true, "UTF-8")
    System.setOut(sink); System.setErr(sink)
    val errorMessage =
      try {
        Console.withOut(sink)(Console.withErr(sink) {
          cache.embed(Vector(sentinel, sentinel))
          cache.embed(Vector(sentinel))
          fake.respond.set(_ => Vector.empty)
          intercept[IllegalStateException](cache.embed(Vector(sentinel + "?"))).getMessage
        })
      } finally { System.setOut(out); System.setErr(err) }
    assert(errorMessage == CachingEmbeddingClient.ResultCountMismatch)
    val rendered = Vector(
      cache.toString,
      cache.stats.toString,
      captured.toString("UTF-8"),
      errorMessage
    ) ++ cache.keyFingerprints
    rendered.foreach(text => assert(!text.contains("SENTINEL"), "clear text leaked"))
    assert(cache.keyFingerprints.size == 1)
    assert(cache.keyFingerprints.head.contains(StableIds.sha256Hex(sentinel)))
    assert(cache.stats == EmbeddingCacheStats(2, 2, 0, 1, 4))
    assert(
      cache.toString ==
        "CachingEmbeddingClient(provider=voyage, model=voyage-4-lite, capacity=4, size=1, " +
        "hits=2, misses=2, evictions=0)"
    )
  }

  private def runThreads(threads: Int)(work: Int => Unit): Unit = {
    val pool = Executors.newFixedThreadPool(threads)
    val start = new CountDownLatch(1)
    val failures = new ConcurrentLinkedQueue[Throwable]()
    try {
      (0 until threads).foreach { t =>
        pool.submit(new Runnable {
          def run(): Unit =
            try { start.await(); work(t) }
            catch { case e: Throwable => failures.add(e) }
        })
      }
      start.countDown()
      pool.shutdown()
      assert(pool.awaitTermination(60, TimeUnit.SECONDS), "threads did not finish")
    } finally pool.shutdownNow()
    assert(failures.isEmpty, failures.asScala.headOption.map(_.toString).getOrElse(""))
  }

  test("concurrent calls over a fixed text set: correct results, bounded size and calls") {
    val texts = Vector.tabulate(40)(i => s"question-$i")
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 64)
    val threads = 16
    val rounds = 200
    runThreads(threads) { t =>
      (0 until rounds).foreach { i =>
        val batch = Vector(texts((t * 7 + i) % 40), texts((t + i * 3) % 40), texts(i % 40))
        val out = cache.embed(batch)
        if (out != batch.map(expected(_))) throw new AssertionError("wrong result")
      }
    }
    val stats = cache.stats
    val inputs = threads.toLong * rounds * 3
    assert(stats.size == 40 && stats.evictions == 0)
    assert(stats.hits + stats.misses == inputs)
    assert(fake.textsSent.toLong == stats.misses)
    // every text missed at least once; without eviction a thread misses each text at most once
    assert(stats.misses >= 40 && stats.misses <= threads.toLong * 40)
    assert(fake.callList.forall(batch => batch.distinct == batch))
    val before = fake.callList.size
    assert(cache.embed(texts) == texts.map(expected(_)))
    assert(fake.callList.size == before)
  }

  test("concurrent calls at a small capacity never exceed it and counters stay monotonic") {
    val texts = Vector.tabulate(40)(i => s"question-$i")
    val fake = new CountingEmbedder(voyageModel)
    val cache = new CachingEmbeddingClient(fake, 8)
    val done = new AtomicBoolean(false)
    val violations = new ConcurrentLinkedQueue[String]()
    val reader = new Thread(() => {
      var last = cache.stats
      while (!done.get()) {
        val now = cache.stats
        if (now.size > 8) violations.add("size")
        if (now.hits < last.hits || now.misses < last.misses || now.evictions < last.evictions)
          violations.add("monotonic")
        last = now
      }
    })
    reader.start()
    val threads = 12
    val rounds = 150
    try
      runThreads(threads) { t =>
        (0 until rounds).foreach { i =>
          val batch = Vector(texts((t * 5 + i) % 40), texts((i * 11) % 40))
          if (cache.embed(batch) != batch.map(expected(_))) throw new AssertionError("wrong")
        }
      }
    finally { done.set(true); reader.join() }
    assert(violations.isEmpty, violations.asScala.toVector.distinct.mkString(","))
    val stats = cache.stats
    assert(stats.size == 8)
    assert(stats.hits + stats.misses == threads.toLong * rounds * 2)
    assert(fake.textsSent.toLong == stats.misses)
    // each insert of a new key grows the map or evicts once; a racing duplicate insert replaces
    assert(stats.evictions > 0 && stats.evictions + stats.size <= stats.misses)
  }
}
