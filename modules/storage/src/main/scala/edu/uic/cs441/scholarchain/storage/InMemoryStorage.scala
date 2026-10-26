package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import StorageResult.*
import scala.collection.mutable

/** Main-source fakes are usable from downstream module tests without a test-to-test dependency. */
final class InMemoryObjectStore(maxObjectBytes: Int = 16 * 1024 * 1024) extends ObjectStore {
  private val objects = mutable.Map.empty[String, StoredObject]
  val writeOrder: mutable.Buffer[String] = mutable.Buffer.empty
  def put(
      key: String,
      bytes: Vector[Byte],
      contentType: String,
      metadata: Map[String, String]
  ): StorageResult[ObjectHead] = synchronized {
    ObjectRules.validate(key, bytes, contentType, metadata, maxObjectBytes) match {
      case Some(code) => Rejected(code)
      case None =>
        val h = ObjectHead(
          key,
          StorageKeys.sha256(bytes),
          bytes.size.toLong,
          contentType,
          metadata + ("sha256" -> StorageKeys.sha256(bytes))
        )
        objects.get(key) match {
          case Some(old) if old.head == h && old.bytes == bytes => Unchanged(old.head)
          case Some(_)                                          => Rejected("immutable-conflict")
          case None => objects(key) = StoredObject(h, bytes); writeOrder += key; Written(h)
        }
    }
  }
  def get(key: String): StorageResult[StoredObject] = synchronized {
    objects.get(key).map(Found(_)).getOrElse(Missing)
  }
  def head(key: String): StorageResult[ObjectHead] = RowCodec.map(get(key))(o => Found(o.head))
}
private[storage] object ObjectRules {
  def validate(
      key: String,
      bytes: Vector[Byte],
      contentType: String,
      metadata: Map[String, String],
      max: Int
  ): Option[String] = {
    if (!key.contains("/versions/") || key.startsWith("/") || key.split('/').contains(".."))
      Some("unversioned-key")
    else if (bytes.size > max) Some("object-too-large")
    else if (
      contentType.isEmpty || metadata.keys.exists(k => k != k.toLowerCase(java.util.Locale.ROOT))
    ) Some("invalid-metadata")
    else if (metadata.get("sha256").exists(_ != StorageKeys.sha256(bytes))) Some("hash-mismatch")
    else if (
      metadata.iterator
        .map((k, v) =>
          k.getBytes(java.nio.charset.StandardCharsets.UTF_8)
            .length + v.getBytes(java.nio.charset.StandardCharsets.UTF_8).length
        )
        .sum + 70 > 2048
    ) Some("metadata-too-large")
    else None
  }
}

/** Stops on first failed upload. Manifest is never published before all payloads are durable. */
final class RunObjectPublisher(store: ObjectStore) {
  def publish(
      objects: Vector[ObjectUpload],
      manifest: ObjectUpload
  ): StorageResult[Vector[ObjectHead]] = {
    if (objects.exists(_.key == manifest.key) || objects.map(_.key).distinct.size != objects.size)
      return Rejected("duplicate-object-key")
    val outputs = Vector.newBuilder[ObjectHead]
    var written = false
    for (o <- objects :+ manifest) {
      val r = store.put(o.key, o.bytes, o.contentType, o.metadata)
      if (!StorageResult.successful(r)) return r match {
        case Rejected(c) => Rejected(c); case _ => Rejected("object-upload-failed")
      }
      r match {
        case Written(_) => written = true; case Retried(_, Written(_)) => written = true;
        case _          => ()
      }
      outputs += StorageResult.value(r).get
    }
    if (written) Written(outputs.result()) else Unchanged(outputs.result())
  }
}
final class InMemoryRunLedger extends RowRunLedger(new MemoryRows, "runs")
final class InMemoryEntityLinkCache extends RowEntityLinks(new MemoryRows, "links")
final class InMemoryQuerySessionStore(
    ttlSeconds: Option[Long] = None,
    now: () => Long = () => java.time.Instant.now().getEpochSecond
) extends RowSessions(new MemoryRows, "sessions", "by-idempotency", ttlSeconds, now)
final class InMemoryArtifactRegistry extends RowArtifacts(new MemoryRows, "artifacts")
final class InMemoryResearcherMetricStore extends RowMetrics(new MemoryRows, "metrics")
final class InMemoryEvidenceBundleStore
    extends RowEvidence(new MemoryRows, "evidence", new InMemoryObjectStore, 256 * 1024)

final case class FakeGraphEdge(
    from: String,
    to: String,
    edgeId: String,
    edgeType: String,
    window: String,
    properties: Map[String, String] = Map.empty
)
final class InMemoryGraphReader(
    nodes: Vector[GraphNode] = Vector.empty,
    edges: Vector[FakeGraphEdge] = Vector.empty,
    communities: Map[(String, String), Vector[String]] = Map.empty,
    maxDepth: Int = 6,
    maxLimit: Int = 100
) extends GraphReader {
  private def limitValid(limit: Int) = limit > 0 && limit <= maxLimit
  def node(id: String): StorageResult[GraphNode] =
    nodes.find(_.nodeId == id).map(Found(_)).getOrElse(Missing)
  private def adjacent(id: String, window: String, types: Set[String]): Vector[GraphNeighbor] =
    edges
      .filter(e =>
        e.window == window && (e.from == id || e.to == id) && (types.isEmpty || types(e.edgeType))
      )
      .map(e =>
        GraphNeighbor(if (e.from == id) e.to else e.from, e.edgeId, e.edgeType, e.properties)
      )
      .sortBy(e => (e.nodeId, e.edgeId))
  def neighbors(
      id: String,
      window: String,
      types: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[GraphPage] = {
    val offset =
      try cursor.map(_.toInt).getOrElse(0)
      catch { case _: NumberFormatException => -1 }
    if (!limitValid(limit) || offset < 0) Rejected("invalid-bound")
    else {
      val all = adjacent(id, window, types); val page = all.slice(offset, offset + limit);
      Found(
        GraphPage(page, if (offset + limit < all.size) Some((offset + limit).toString) else None)
      )
    }
  }
  def directCoauthors(id: String, window: String, limit: Int): StorageResult[GraphPage] =
    neighbors(id, window, Set("COAUTHORED_WITH"), limit, None)
  def shortestPaths(
      a: String,
      b: String,
      depth: Int,
      window: String,
      limit: Int
  ): StorageResult[Vector[GraphPath]] = {
    if (depth < 1 || depth > maxDepth || !limitValid(limit)) Rejected("invalid-bound")
    else {
      var frontier = Vector(GraphPath(Vector(a), Vector.empty));
      var found = Vector.empty[GraphPath]; var d = 0
      while (frontier.nonEmpty && found.isEmpty && d <= depth) {
        found = frontier.filter(_.nodeIds.last == b).take(limit)
        if (found.isEmpty && d < depth)
          frontier = frontier.flatMap(p =>
            adjacent(p.nodeIds.last, window, Set("COAUTHORED_WITH"))
              .filterNot(n => p.nodeIds.contains(n.nodeId))
              .map(n => GraphPath(p.nodeIds :+ n.nodeId, p.edgeIds :+ n.edgeId))
          )
        else frontier = Vector.empty
        d += 1
      }
      Found(found)
    }
  }
  def communityMembers(id: String, window: String, limit: Int): StorageResult[Vector[String]] = if (
    !limitValid(limit)
  ) Rejected("invalid-bound")
  else Found(communities.getOrElse(id -> window, Vector.empty).sorted.take(limit))
  def crossCommunityEdges(id: String, window: String, limit: Int): StorageResult[GraphPage] = {
    if (!limitValid(limit)) Rejected("invalid-bound")
    else {
      val members = communities.getOrElse(id -> window, Vector.empty).toSet
      val all = members.toVector.sorted
        .flatMap(m => adjacent(m, window, Set("COAUTHORED_WITH")))
        .filterNot(n => members(n.nodeId))
        .distinct
      Found(GraphPage(all.take(limit), None))
    }
  }
}
final class InMemoryVectorStore extends VectorStore {
  private val indexes = mutable.Map.empty[String, (Int, String)]
  private val documents = mutable.Map.empty[(String, String), VectorDocument]
  def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String] =
    synchronized {
      if (name.isEmpty || dimension < 1 || dimension > 4096 || !Set("cosine", "euclidean")(metric))
        Rejected("invalid-index")
      else
        indexes.get(name) match {
          case Some(v) if v == (dimension -> metric) => Unchanged(name)
          case Some(_)                               => Rejected("index-conflict")
          case None => indexes(name) = dimension -> metric; Written(name)
        }
    }
  def putBatch(index: String, docs: Vector[VectorDocument]): StorageResult[VectorBatchResult] =
    synchronized {
      if (!indexes.contains(index)) return Rejected("missing-index")
      var written = 0; var unchanged = 0; val rejected = Vector.newBuilder[VectorReject]
      docs.foreach { d =>
        if (
          d.key.isEmpty || d.values.size != indexes(index)._1 || d.values
            .exists(v => !v.isFinite) || !d.textHash.matches("[0-9a-f]{64}")
        ) rejected += VectorReject(d.key, "invalid-vector")
        else
          documents.get(index -> d.key) match {
            case Some(old) if old.textHash != d.textHash =>
              rejected += VectorReject(d.key, "text-hash-conflict")
            case Some(old) if old == d => unchanged += 1
            case Some(_)               => rejected += VectorReject(d.key, "immutable-conflict")
            case None                  => documents(index -> d.key) = d; written += 1
          }
      }
      val result = VectorBatchResult(written, unchanged, rejected.result());
      if (written > 0) Written(result) else Unchanged(result)
    }
  def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]] =
    synchronized {
      if (!indexes.contains(index)) Rejected("missing-index")
      else Found(keys.distinct.flatMap(k => documents.get(index -> k)))
    }
  def query(
      index: String,
      v: Vector[Float],
      topK: Int,
      filter: Map[String, String]
  ): StorageResult[Vector[VectorHit]] = synchronized {
    if (!indexes.contains(index)) Rejected("missing-index")
    else if (v.size != indexes(index)._1 || v.exists(x => !x.isFinite) || topK < 1 || topK > 10000)
      Rejected("invalid-bound")
    else {
      val metric = indexes(index)._2
      val hits = documents.iterator
        .collect {
          case ((i, _), d)
              if i == index && filter.forall((k, value) => d.metadata.get(k).contains(value)) =>
            val distance =
              if (metric == "euclidean")
                math.sqrt(v.zip(d.values).map((a, b) => math.pow(a.toDouble - b, 2)).sum)
              else {
                val denominator = math.sqrt(v.map(x => x.toDouble * x).sum) * math.sqrt(
                  d.values.map(x => x.toDouble * x).sum
                )
                if (denominator == 0) 1.0
                else 1.0 - v.zip(d.values).map((a, b) => a.toDouble * b).sum / denominator
              }
            VectorHit(d.key, distance, d.metadata)
        }
        .toVector
        .sortBy(h => (h.distance, h.key))
        .take(topK)
      Found(hits)
    }
  }
}
