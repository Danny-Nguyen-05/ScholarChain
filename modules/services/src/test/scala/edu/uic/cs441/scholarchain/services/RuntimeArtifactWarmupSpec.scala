package edu.uic.cs441.scholarchain.services

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.{CountDownLatch, TimeUnit}
import java.util.concurrent.ConcurrentLinkedQueue
import org.scalatest.funsuite.AnyFunSuite
import scala.jdk.CollectionConverters.*

class RuntimeArtifactWarmupSpec extends AnyFunSuite {

  /** Mirrors the real store: the first successful load is cached, a failed load is not. */
  private class CachingStore(failuresBeforeSuccess: Int, failure: StorageResult[Nothing])
      extends RuntimeArtifactStore {
    val loads = new AtomicInteger
    @volatile private var loaded = false
    private def data[A](): Option[StorageResult[A]] = synchronized {
      if (loaded) None
      else if (loads.incrementAndGet() <= failuresBeforeSuccess) Some(failure)
      else { loaded = true; None }
    }
    def rank(w: String, m: RuntimeRankingMetric, f: RuntimePopulationFilter, l: Int) =
      data[RuntimeRankingPage]().getOrElse(StorageResult.Missing)
    def communitySummary(id: String, w: String) =
      data[CommunitySummary]().getOrElse(StorageResult.Missing)
    def bridgeMetrics(id: String, w: String) =
      data[RuntimeBridgeRecord]().getOrElse(StorageResult.Missing)
    def temporalChange(id: String, from: String, to: String) =
      data[RuntimeTemporalRecord]().getOrElse(StorageResult.Missing)
    def edgeSupport(id: String, w: String) =
      data[RuntimeEdgeRecord]().getOrElse(StorageResult.Missing)
    def researcherContext(id: String, w: String, limit: Int) =
      data[RuntimeResearcherContext]().getOrElse(StorageResult.Rejected("runtime-result-bound"))
  }

  private final class Recorder {
    val lines = new ConcurrentLinkedQueue[String]
    val sleeps = new ConcurrentLinkedQueue[Long]
    val log: String => Unit = lines.add(_)
    val sleep: Long => Unit = sleeps.add(_)
  }

  test("a successful warm-up loads once and later calls are served without another load") {
    val store = new CachingStore(0, StorageResult.Rejected("unused"))
    val r = new Recorder
    assert(RuntimeArtifactWarmup.run(store, 3, 5000L, r.sleep, log = r.log))
    assert(store.loads.get == 1)
    assert(store.edgeSupport("edge", "all-years") == StorageResult.Missing)
    assert(
      store.rank(
        "all-years",
        RuntimeRankingMetric.DistinctCoauthorCount,
        RuntimePopulationFilter(),
        1
      ) == StorageResult.Missing
    )
    assert(store.loads.get == 1)
    assert(r.sleeps.isEmpty)
    assert(r.lines.asScala.toVector.size == 1)
    assert(r.lines.peek.contains("attempt=1/3") && r.lines.peek.contains("outcome=loaded"))
  }

  test("a failing load is retried up to three times, never throws, and later calls still retry") {
    val store =
      new CachingStore(Int.MaxValue, StorageResult.Rejected("runtime-artifact-content-mismatch"))
    val r = new Recorder
    assert(!RuntimeArtifactWarmup.run(store, 3, 5000L, r.sleep, log = r.log))
    assert(store.loads.get == 3)
    assert(r.sleeps.asScala.toVector == Vector(5000L, 5000L))
    val lines = r.lines.asScala.toVector
    assert(lines.size == 3)
    assert(lines.forall(_.contains("outcome=runtime-artifact-content-mismatch")))
    assert(lines.forall(_.contains("elapsedMs=")))
    // The failure was not cached: an on-demand read still reaches the loader.
    store.edgeSupport("edge", "all-years")
    assert(store.loads.get == 4)
  }

  test("warm-up stops at the first success after earlier failures") {
    val store = new CachingStore(2, StorageResult.Rejected("invalid-runtime-artifact"))
    val r = new Recorder
    assert(RuntimeArtifactWarmup.run(store, 3, 5000L, r.sleep, log = r.log))
    assert(store.loads.get == 3)
    assert(r.sleeps.size == 2)
    val lines = r.lines.asScala.toVector
    assert(lines.take(2).forall(_.contains("outcome=invalid-runtime-artifact")))
    assert(lines(2).contains("outcome=loaded"))
  }

  test("an absent object is a failed load, not a loaded snapshot") {
    val store = new CachingStore(Int.MaxValue, StorageResult.Missing)
    val r = new Recorder
    assert(!RuntimeArtifactWarmup.run(store, 2, 1L, r.sleep, log = r.log))
    assert(r.lines.asScala.forall(_.contains("outcome=runtime-artifact-missing")))
  }

  test("a throwing store and a throwing logger never escape the warm-up") {
    val throwing = new CachingStore(0, StorageResult.Rejected("x")) {
      override def researcherContext(id: String, w: String, limit: Int) =
        throw new IllegalStateException("secret-bucket-name")
    }
    val lines = new ConcurrentLinkedQueue[String]
    assert(!RuntimeArtifactWarmup.run(throwing, 3, 1L, _ => (), log = lines.add(_)))
    assert(lines.size == 3)
    assert(
      lines.asScala.forall(l => l.contains("outcome=warmup-exception") && !l.contains("secret"))
    )
    assert(
      !RuntimeArtifactWarmup.run(
        throwing,
        2,
        1L,
        _ => (),
        log = _ => throw new RuntimeException("log")
      )
    )
  }

  test("an unconfigured store is skipped and no thread is started") {
    val r = new Recorder
    assert(!RuntimeArtifactWarmup.run(UnconfiguredRuntimeArtifacts, 3, 1L, r.sleep, log = r.log))
    assert(RuntimeArtifactWarmup.start(UnconfiguredRuntimeArtifacts, 3, 1L, r.sleep, r.log).isEmpty)
    assert(r.lines.isEmpty && r.sleeps.isEmpty)
  }

  test("the warm-up thread is a named daemon that does the work off the calling thread") {
    val store = new CachingStore(0, StorageResult.Rejected("unused"))
    val done = new CountDownLatch(1)
    val callerName = Thread.currentThread().getName
    val ranOn = new java.util.concurrent.atomic.AtomicReference[String]()
    val thread = RuntimeArtifactWarmup
      .start(
        store,
        3,
        1L,
        _ => (),
        s => { ranOn.set(Thread.currentThread().getName); done.countDown() }
      )
      .get
    assert(thread.isDaemon)
    assert(thread.getName == "runtime-artifact-warm")
    assert(done.await(5, TimeUnit.SECONDS))
    thread.join(5000)
    assert(ranOn.get == "runtime-artifact-warm" && ranOn.get != callerName)
    assert(store.loads.get == 1)
  }

  test("start does not block while the load is hanging") {
    val release = new CountDownLatch(1)
    val hanging = new CachingStore(0, StorageResult.Rejected("x")) {
      override def researcherContext(id: String, w: String, limit: Int) = {
        try release.await(30, TimeUnit.SECONDS)
        catch { case _: InterruptedException => () }
        StorageResult.Rejected("runtime-result-bound")
      }
    }
    val began = System.nanoTime()
    val thread = RuntimeArtifactWarmup.start(hanging, 3, 1L, _ => (), _ => ()).get
    assert((System.nanoTime() - began) / 1000000L < 2000L)
    assert(thread.isAlive)
    release.countDown()
    thread.join(5000)
    assert(!thread.isAlive)
  }

  test("the real object-store adapter reports a failed load and retries the GET on later calls") {
    val gets = new AtomicInteger
    val objects = new ObjectStore {
      def put(k: String, b: Vector[Byte], c: String, m: Map[String, String]) =
        StorageResult.Rejected("unused")
      def head(k: String) = StorageResult.Rejected("unused")
      def get(k: String): StorageResult[StoredObject] = {
        gets.incrementAndGet(); StorageResult.Missing
      }
    }
    val store = new ObjectStoreRuntimeArtifactStore(
      objects,
      RuntimeArtifactPointer("runtime/versions/v1/a.json", "a" * 64, "run:fixture")
    )
    val r = new Recorder
    assert(RuntimeArtifactWarmup.outcome(store) == "runtime-artifact-missing")
    assert(!RuntimeArtifactWarmup.run(store, 3, 1L, r.sleep, log = r.log))
    assert(gets.get == 4)
    store.edgeSupport("edge", "all-years")
    assert(gets.get == 5)
    val badPointer = new ObjectStoreRuntimeArtifactStore(
      objects,
      RuntimeArtifactPointer("no-version-segment", "a" * 64, "run:fixture")
    )
    assert(RuntimeArtifactWarmup.outcome(badPointer) == "invalid-runtime-artifact-pointer")
  }

  test("the AWS query composition starts the warm-up only for a configured artifact pointer") {
    import AwsTestEnv.*
    val started = new java.util.concurrent.CopyOnWriteArrayList[RuntimeArtifactStore]
    val creds = () =>
      software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
        .create(software.amazon.awssdk.auth.credentials.AwsBasicCredentials.create("t", "t"))
    val factory = new AwsSdkPortFactory(
      credentials = creds,
      artifactWarmup = store => { started.add(store); () }
    )
    def queryPorts(env: Map[String, String]) = {
      val q = parse("query-api", env).toOption.get.asInstanceOf[QueryRoleConfig]
      factory.query(q, AwsComposition.runtimeConfig(q).toOption.get).toOption.get
    }
    val unconfigured = queryPorts(forRole("query-api"))
    assert(started.isEmpty)
    assert(unconfigured.artifacts eq UnconfiguredRuntimeArtifacts)
    unconfigured.close()
    val configured = queryPorts(
      forRole("query-api") ++ Map(
        "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY" -> "runtime/versions/v1/artifacts.json",
        "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256" -> ("b" * 64),
        "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID" -> "run:fixture"
      )
    )
    assert(started.size == 1 && (started.get(0) eq configured.artifacts))
    configured.close()
  }

  test("a warm-up hook that throws cannot fail the query composition") {
    import AwsTestEnv.*
    val creds = () =>
      software.amazon.awssdk.auth.credentials.StaticCredentialsProvider
        .create(software.amazon.awssdk.auth.credentials.AwsBasicCredentials.create("t", "t"))
    val factory = new AwsSdkPortFactory(
      credentials = creds,
      artifactWarmup = _ => throw new IllegalStateException("hook")
    )
    val env = forRole("query-api") ++ Map(
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_KEY" -> "runtime/versions/v1/artifacts.json",
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SHA256" -> ("b" * 64),
      "SCHOLARCHAIN_RUNTIME_ARTIFACT_SOURCE_RUN_ID" -> "run:fixture"
    )
    val q = parse("query-api", env).toOption.get.asInstanceOf[QueryRoleConfig]
    val ports = factory.query(q, AwsComposition.runtimeConfig(q).toOption.get)
    assert(ports.isRight)
    ports.toOption.get.close()
  }
}
