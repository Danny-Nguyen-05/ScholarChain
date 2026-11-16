package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.lang.reflect.{InvocationHandler, Method, Proxy}
import java.util.concurrent.{ConcurrentHashMap, ConcurrentLinkedQueue}
import java.util.concurrent.atomic.{AtomicInteger, LongAdder}
import java.util.concurrent.locks.LockSupport
import scala.jdk.CollectionConverters.*
import software.amazon.awssdk.services.s3vectors.S3VectorsClient
import software.amazon.awssdk.services.s3vectors.model.{PutVectorsRequest, PutVectorsResponse}

/** Session 2 plan P26 (b), lane G: offline fakes for the live ingest composition of
  * `LiveEmbeddingIngestMain.awsPorts` (rag): `DynamoRunLedger` and `DynamoArtifactRegistry` are
  * `RowRunLedger` / `RowArtifacts` over DynamoDB rows, the vector store is the real `S3VectorStore`
  * sharing that registry, and the text store is S3. Here the rows are `MemoryRows`, the S3 Vectors
  * client is a proxy, and every port call that is one AWS API call is counted and, optionally,
  * delayed by a fixed per-call latency.
  *
  * Latency provenance (labelled):
  *   - `S3VectorsPutNanos` 141 ms: MEASURED proxy, the Session 1 S3 Vectors query p50 from the
  *     operator laptop to us-east-2 (docs/agent-runs/phase-14/evidence/14b/session-1/14c-load/
  *     query-smoke.log, five samples 132-187 ms). No put latency was recorded.
  *   - `StorageCallNanos` 54.4 ms per DynamoDB or S3 call: DERIVED from the Session 1 ingest
  *     (ingest-2.log: 95 written + 9 unchanged in 154.52 s, 95 single-text Voyage calls). With the
  *     pre-change call profile measured by `IngestThroughputSpec` (21 DynamoDB + 2 S3 calls per
  *     fresh item, 13 DynamoDB calls per unchanged item, 5 vector puts): 154.52 s = 95 x 23 L + 9 x
  *     13 L + 95 x 0.30 s + 5 x 0.141 s, so L = 54.4 ms. The 0.30 s single-text Voyage latency is
  *     an ASSUMPTION (not measured); at 0.20 s or 0.50 s, L is 58.5 or 46.1 ms.
  *   - `VoyageBatchNanos` 2.0 s per 100-text Voyage request: ASSUMPTION (not measured).
  */
object IngestLatency {
  val StorageCallNanos: Long = 54400000L
  val S3VectorsPutNanos: Long = 141000000L
  val VoyageBatchNanos: Long = 2000000000L
}

/** Counts calls by name; `delay` maps a call name to its injected latency (already scaled). */
final class CallMeter(delay: String => Long = _ => 0L) {
  private val counts = new ConcurrentHashMap[String, LongAdder]()
  def apply[A](name: String)(body: => A): A = {
    counts.computeIfAbsent(name, _ => new LongAdder).increment()
    CallMeter.pause(delay(name))
    body
  }
  def snapshot: Map[String, Long] = counts.asScala.view.mapValues(_.sum()).toMap
  def total(prefix: String): Long = snapshot.collect {
    case (k, v) if k.startsWith(prefix) => v
  }.sum
}
object CallMeter {
  // Parking alone overshoots by up to about 1 ms on macOS (timer slack), which at 1/20 scale is a
  // large share of a 2.72 ms call; park until 1 ms is left, then spin to the deadline.
  def pause(nanos: Long): Unit = if (nanos > 0) {
    val deadline = System.nanoTime() + nanos
    var left = nanos
    while (left > 1000000L) {
      LockSupport.parkNanos(left - 1000000L); left = deadline - System.nanoTime()
    }
    while (System.nanoTime() < deadline) Thread.onSpinWait()
  }
}

/** One table of DynamoDB rows: each method is one DynamoDB API call. */
final class MeteredRows(underlying: StorageRows, meter: CallMeter, table: String)
    extends StorageRows {
  def read(t: String, key: RowKey) = meter(s"ddb.$table.GetItem")(underlying.read(t, key))
  def query(t: String, pk: String, descending: Boolean) =
    meter(s"ddb.$table.Query")(underlying.query(t, pk, descending))
  def index(t: String, i: String, key: String) =
    meter(s"ddb.$table.QueryIndex")(underlying.index(t, i, key))
  def write(t: String, row: StorageRow, c: RowCondition) =
    meter(s"ddb.$table.PutItem")(underlying.write(t, row, c))
  def transact(t: String, writes: Vector[RowWrite]) =
    meter(s"ddb.$table.TransactWriteItems")(underlying.transact(t, writes))
  def batch(t: String, keys: Vector[RowKey]) =
    meter(s"ddb.$table.BatchGetItem")(underlying.batch(t, keys))
}

/** S3 text store: `S3ObjectStore.put` is one PutObject on a fresh key; `get` is Head + Get. */
final class MeteredObjects(meter: CallMeter) extends ObjectStore {
  val underlying = new InMemoryObjectStore
  def put(key: String, bytes: Vector[Byte], contentType: String, metadata: Map[String, String]) =
    meter("s3.PutObject")(underlying.put(key, bytes, contentType, metadata))
  def get(key: String) = meter("s3.HeadObject")(meter("s3.GetObject")(underlying.get(key)))
  def head(key: String) = meter("s3.HeadObject")(underlying.head(key))
}

/** Emulates rag's `LookaheadBatchingEmbeddingClient` over a provider: one provider request carries
  * the requested text and the next `batch - 1` not-yet-sent manifest texts. Serialized by one lock,
  * like the rag decorator. `failAfter` makes every provider request after that many fail.
  */
final class LookaheadEmbedder(
    val model: EmbeddingModel,
    manifestTexts: Vector[String],
    batch: Int,
    meter: CallMeter,
    failAfter: Int = Int.MaxValue
) extends EmbeddingClient {
  private val fetched = scala.collection.mutable.HashSet.empty[String]
  val requests = new AtomicInteger
  val perText = new ConcurrentHashMap[String, AtomicInteger]()
  def vector(text: String): Vector[Float] =
    Vector(1f, (math.abs(text.hashCode) % 997).toFloat / 997f + 0.001f)
  def embed(texts: Seq[String]): Seq[EmbeddingResult] = synchronized {
    texts.map { text =>
      perText.computeIfAbsent(text, _ => new AtomicInteger).incrementAndGet()
      if (fetched.remove(text)) EmbeddingSuccess(vector(text), model, 1)
      else if (requests.get() >= failAfter) {
        requests.incrementAndGet()
        meter("voyage.embed")(EmbeddingFailure("embedding-provider-unavailable", true, model, 1))
      } else
        meter("voyage.embed") {
          requests.incrementAndGet()
          val start = math.max(0, manifestTexts.indexOf(text))
          manifestTexts.drop(start + 1).take(batch - 1).foreach(fetched += _)
          EmbeddingSuccess(vector(text), model, 1)
        }
    }
  }
}

object IngestThroughputFixture {
  val model: EmbeddingModel = EmbeddingModel("fixture-embedding", "v1", 2)
  val types: Vector[String] =
    Vector("paper", "researcher-profile", "community", "collaboration-path")

  def doc(n: Int, documentType: String, text: String): EmbeddingDocument = {
    val entity = f"fixture-entity-$n%05d"
    val id = StableIds.chunkOrProfileId(entity, "v1", documentType, Some(0), text).toOption.get
    EmbeddingDocument(
      id,
      documentType,
      entity,
      "fixture-window",
      "fixture-source-run",
      "fixture-template-v1",
      text,
      Vector(SummarySourceRef("works", s"fixture-work-$n", "title")),
      if (documentType == "paper") "paper-summary-fallback" else "generated-summary",
      identityFields = Map("sourceDataset" -> "synthetic-fixture"),
      chunkPolicyVersion = "fixture-chunk-policy-v1",
      chunkOrdinal = 0
    )
  }

  def manifest(count: Int, config: EmbeddingIngestConfig, oneIndex: Boolean = false) =
    EmbeddingManifest((0 until count).toVector.map { n =>
      val t = if (oneIndex) "paper" else types(n % types.size)
      EmbeddingManifests.item(doc(n, t, s"synthetic summary number $n for $t"), model, config)
    })

  /** One S3 Vectors PutVectors call as observed by the fake: index, then (key, values) per vector.
    */
  final case class PutCall(index: String, vectors: Vector[(String, Vector[Float])])

  def vectorsClient(meter: CallMeter, log: ConcurrentLinkedQueue[PutCall]): S3VectorsClient = Proxy
    .newProxyInstance(
      getClass.getClassLoader,
      Array(classOf[S3VectorsClient]),
      new InvocationHandler {
        def invoke(proxy: Any, method: Method, args: Array[AnyRef]): AnyRef =
          method.getName match {
            case "putVectors"
                if args != null && args.headOption.exists(_.isInstanceOf[PutVectorsRequest]) =>
              val request = args.head.asInstanceOf[PutVectorsRequest]
              meter("s3vectors.PutVectors") {
                log.add(
                  PutCall(
                    request.indexName(),
                    request
                      .vectors()
                      .asScala
                      .toVector
                      .map(v => v.key() -> v.data().float32().asScala.map(_.floatValue).toVector)
                  )
                )
                PutVectorsResponse.builder().build()
              }
            case "serviceName" => "s3vectors"
            case "close"       => null
            case "toString"    => "fake-s3vectors"
            case "hashCode"    => Int.box(System.identityHashCode(proxy))
            case "equals"      => Boolean.box(false)
            case other         => throw new UnsupportedOperationException(other)
          }
      }
    )
    .asInstanceOf[S3VectorsClient]

  /** Stores of one simulated account; they survive across runs (resume) of the same fixture. */
  final class Stores(val meter: CallMeter) {
    val ledgerRows = new MemoryRows
    val registryRows = new MemoryRows
    val ledger = new RowRunLedger(new MeteredRows(ledgerRows, meter, "ledger"), "runs")
    val registry = new RowArtifacts(new MeteredRows(registryRows, meter, "registry"), "artifacts")
    val objects = new MeteredObjects(meter)
    val puts = new ConcurrentLinkedQueue[PutCall]()
    def putKeys: Vector[String] = puts.asScala.toVector.flatMap(_.vectors.map(_._1))
    def vectors(config: EmbeddingIngestConfig) = new S3VectorStore(
      vectorsClient(meter, puts),
      registry,
      VectorAdapterConfig(
        "fixture-vectors",
        config.dimension,
        config.metric,
        putBatchSize = config.batchSize,
        retry = RetryConfig(maxAttempts = 1)
      ),
      objects
    )
    def runner(
        config: EmbeddingIngestConfig,
        embedder: EmbeddingClient,
        registryPort: ArtifactRegistry = registry
    ) =
      new EmbeddingManifestRunner(config, objects, vectors(config), registryPort, ledger, embedder)
    def runnerComplete(i: EmbeddingWorkItem): Boolean = StorageResult
      .value(
        registry.get("embedding:" + StorageKeys.composite(i.indexName, i.vectorKey), "complete")
      )
      .exists(_.hash == i.textHash)
  }

  /** Stateless, thread-safe: one provider attempt per text; `fails` texts get a typed failure. */
  final class FixedEmbedder(val model: EmbeddingModel, fails: String => Boolean = _ => false)
      extends EmbeddingClient {
    val perText = new ConcurrentHashMap[String, AtomicInteger]()
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
      perText.computeIfAbsent(text, _ => new AtomicInteger).incrementAndGet()
      if (fails(text)) EmbeddingFailure("embedding-provider-unavailable", true, model, 1)
      else
        EmbeddingSuccess(
          Vector(1f, (math.abs(text.hashCode) % 997).toFloat / 997f + 0.001f),
          model,
          1
        )
    }
  }

  /** Models a client-side request cap (rag's call/token caps): at most `cap` texts are sent; any
    * later request is refused before the provider with zero attempts.
    */
  final class CappedEmbedder(val model: EmbeddingModel, cap: Int) extends EmbeddingClient {
    val granted = new AtomicInteger
    val asked = new AtomicInteger
    def embed(texts: Seq[String]): Seq[EmbeddingResult] = texts.map { text =>
      asked.incrementAndGet()
      if (granted.incrementAndGet() <= cap) EmbeddingSuccess(Vector(1f, 0.5f), model, 1)
      else EmbeddingFailure("embedding-call-cap", false, model, 0)
    }
  }

  /** The runner's registry, which throws (a simulated process crash) on the `after`-th runner
    * completion record, after the vector write of that batch.
    */
  final class CrashingRegistry(underlying: ArtifactRegistry, after: Int) extends ArtifactRegistry {
    private val completions = new AtomicInteger
    def register(id: String, version: String, uri: String, hash: String) = {
      if (
        id.startsWith("embedding:") && version == "complete" && completions
          .incrementAndGet() >= after
      ) throw new IllegalStateException("simulated-crash")
      underlying.register(id, version, uri, hash)
    }
    def latest(id: String) = underlying.latest(id)
    def get(id: String, version: String) = underlying.get(id, version)
  }

  /** Latency profile at `1/scale` of the live values above. */
  def scaledDelay(scale: Long): String => Long = name =>
    if (name.startsWith("ddb.") || name.startsWith("s3.")) IngestLatency.StorageCallNanos / scale
    else if (name.startsWith("s3vectors.")) IngestLatency.S3VectorsPutNanos / scale
    else if (name.startsWith("voyage.")) IngestLatency.VoyageBatchNanos / scale
    else 0L
}
