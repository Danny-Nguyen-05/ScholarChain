package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import upickle.default.ReadWriter
import java.nio.charset.StandardCharsets.UTF_8

/** Expected conflicts and unavailable/corrupt data are values. Provider error messages are never
  * returned (they may contain endpoint, credential or request data).
  */
enum StorageResult[+A] {
  case Written(value: A)
  case Unchanged(value: A)
  case Found(value: A)
  case Missing
  case Rejected(code: String)
  case Retried(attempts: Int, result: StorageResult[A])
}
object StorageResult {
  def value[A](r: StorageResult[A]): Option[A] = r match {
    case Written(v)    => Some(v)
    case Unchanged(v)  => Some(v)
    case Found(v)      => Some(v)
    case Retried(_, v) => value(v)
    case _             => None
  }
  def successful(r: StorageResult[?]): Boolean = r match {
    case Written(_) | Unchanged(_) | Found(_) => true
    case Retried(_, v)                        => successful(v)
    case _                                    => false
  }
}
final case class ObjectHead(
    key: String,
    sha256: String,
    size: Long,
    contentType: String,
    metadata: Map[String, String]
)
final case class StoredObject(head: ObjectHead, bytes: Vector[Byte])
final case class ObjectUpload(
    key: String,
    bytes: Vector[Byte],
    contentType: String,
    metadata: Map[String, String] = Map.empty
)
trait ObjectStore {
  def put(
      key: String,
      bytes: Vector[Byte],
      contentType: String,
      metadata: Map[String, String]
  ): StorageResult[ObjectHead]
  def get(key: String): StorageResult[StoredObject]
  def head(key: String): StorageResult[ObjectHead]
  def exists(key: String): StorageResult[Boolean] = head(key) match {
    case StorageResult.Missing            => StorageResult.Found(false)
    case r if StorageResult.successful(r) => StorageResult.Found(true)
    case StorageResult.Rejected(c)        => StorageResult.Rejected(c)
    case _                                => StorageResult.Rejected("object-unavailable")
  }
}
object StorageKeys {
  def versioned(prefix: String, version: String, name: String): String = {
    require(Vector(prefix, version, name).forall(v => v.nonEmpty && !v.split('/').contains("..")))
    s"$prefix/versions/$version/$name"
  }
  // Length framing is collision safe even when IDs contain delimiters. Spark IDs remain untouched.
  def composite(parts: String*): String = parts.map(p => s"${p.getBytes(UTF_8).length}:$p").mkString
  def support(edgeId: String, workId: String): String = composite(edgeId, workId)
  def sha256(bytes: Vector[Byte]): String = java.security.MessageDigest
    .getInstance("SHA-256")
    .digest(bytes.toArray)
    .map(b => f"${b & 255}%02x")
    .mkString
}
final case class RunStage(stageKey: String, state: String, retryCount: Int, detail: Option[String])
    derives ReadWriter
final case class RunRecord(
    runId: String,
    state: String,
    stages: Vector[RunStage],
    revision: Long = 0,
    failures: Vector[RunStage] = Vector.empty
) derives ReadWriter
trait RunLedger {
  def startRun(runId: String): StorageResult[RunRecord]
  def recordStage(runId: String, stageKey: String): StorageResult[RunStage]
  def recordFailure(
      runId: String,
      stageKey: String,
      retryCount: Int,
      reasonCode: String
  ): StorageResult[RunStage]
  def completeStage(runId: String, stageKey: String): StorageResult[RunStage]
  def completeRun(runId: String): StorageResult[RunRecord]
  def getRun(runId: String): StorageResult[RunRecord]
}
final case class EntityLink(
    entityType: String,
    normalizedKey: String,
    policyVersion: String,
    sourceId: String,
    researcherId: String,
    displayName: String,
    affiliations: Vector[String],
    confidence: Option[Double],
    runId: String,
    evidenceRefs: Vector[String]
) derives ReadWriter
trait EntityLinkCache {
  def putLink(link: EntityLink): StorageResult[EntityLink]
  def lookupByNormalizedName(name: String): StorageResult[Vector[EntityLink]]
  def lookupByExternalId(namespace: String, id: String): StorageResult[Vector[EntityLink]]
}
final case class QuerySession(
    queryId: String,
    idempotencyKey: String,
    state: String,
    revision: Long,
    payload: String,
    expiresAtEpochSeconds: Option[Long]
) derives ReadWriter
trait QuerySessionStore {
  def createIfAbsent(queryId: String, idempotencyKey: String): StorageResult[QuerySession]
  def get(queryId: String): StorageResult[QuerySession]
  def lookupByIdempotencyKey(key: String): StorageResult[QuerySession]
  def update(session: QuerySession, expectedRevision: Long): StorageResult[QuerySession]
}
trait EvidenceBundleStore {
  def put(bundle: EvidenceBundle): StorageResult[EvidenceBundle]
  def get(evidenceId: String): StorageResult[EvidenceBundle]

  /** Existing bundle-only adapters remain source compatible. Runtime composition uses
    * IndexedEvidenceBundleStore to resolve item IDs without changing frozen ID formats.
    */
  def getItem(evidenceId: String): StorageResult[EvidenceItem] =
    StorageResult.Rejected("evidence-item-index-required")
}
final case class ArtifactRecord(artifactId: String, version: String, uri: String, hash: String)
    derives ReadWriter
trait ArtifactRegistry {
  def register(
      artifactId: String,
      version: String,
      uri: String,
      hash: String
  ): StorageResult[ArtifactRecord]

  /** Versions are lexically ordered; callers use sortable version tags (e.g. zero-padded versions).
    */
  def latest(artifactId: String): StorageResult[ArtifactRecord]
  def get(artifactId: String, version: String): StorageResult[ArtifactRecord]
}

/** Payload and qualifications are retained byte-for-byte as canonical JSON, including iteration
  * caps, non-convergence and approximate statistics. No derived metric is recalculated here.
  */
final case class ResearcherMetricRecord(
    researcherId: String,
    windowId: String,
    metricVersion: String,
    runId: String,
    payloadJson: String,
    qualificationsJson: String
) derives ReadWriter
trait ResearcherMetricStore {
  def put(record: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord]
  def get(researcherId: String, windowId: String): StorageResult[ResearcherMetricRecord]
  def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]]
}
final case class GraphLoadManifest(
    runId: String,
    uri: String,
    format: String,
    nodeIds: Vector[String] = Vector.empty,
    edgeIds: Vector[String] = Vector.empty
)
final case class GraphLoadStatus(loadId: String, state: String)
trait GraphLoader {
  def submitBulkLoad(manifest: GraphLoadManifest): StorageResult[GraphLoadStatus]
  def status(loadId: String): StorageResult[GraphLoadStatus]
}
final case class GraphNeighbor(
    nodeId: String,
    edgeId: String,
    edgeType: String,
    properties: Map[String, String]
)
final case class GraphPage(items: Vector[GraphNeighbor], cursor: Option[String])
final case class GraphPath(
    nodeIds: Vector[String] = Vector.empty,
    edgeIds: Vector[String] = Vector.empty
)
trait GraphReader {
  def node(id: String): StorageResult[GraphNode]
  def neighbors(
      id: String,
      window: String,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[GraphPage]
  def directCoauthors(id: String, window: String, limit: Int): StorageResult[GraphPage]
  def shortestPaths(
      a: String,
      b: String,
      maxDepth: Int,
      window: String,
      limit: Int
  ): StorageResult[Vector[GraphPath]]
  def communityMembers(
      communityId: String,
      window: String,
      limit: Int
  ): StorageResult[Vector[String]]
  def crossCommunityEdges(communityId: String, window: String, limit: Int): StorageResult[GraphPage]
}

/** Direction relative to the requested node: `Out` returns edges whose stored start is the node,
  * `In` edges whose stored end is the node, `Both` the union (a self-loop appears once).
  */
enum EdgeDirection(val wire: String) {
  case Out extends EdgeDirection("out")
  case In extends EdgeDirection("in")
  case Both extends EdgeDirection("both")
}
object EdgeDirection {
  def fromWire(value: String): Option[EdgeDirection] = values.find(_.wire == value)
}

/** One stored edge with its stored start/end. `properties` are exactly the edge properties the
  * loader wrote (text-rendered, exact decimals retained), including provenance and evidence
  * pointers (`provenanceJson`, `sourceEvidenceJson`, `policyVersion` for graph edges;
  * `evidenceTable`/`evidenceEdgeId` for coauthor edges, whose rows carry no `provenanceJson`).
  * Stored start/end of an undirected type (COAUTHORED_WITH) is a canonical order, not a claim of
  * direction; the caller applies `GraphEdgeType.isUndirected`.
  */
final case class DirectedGraphEdge(
    fromId: String,
    toId: String,
    edgeId: String,
    edgeType: String,
    properties: Map[String, String]
) {

  /** The stored provenance, never inferred: Left when the row carries none or it is malformed. */
  def provenance: Either[String, Provenance] =
    properties.get("provenanceJson") match {
      case None => Left("edge-provenance-absent")
      case Some(json) =>
        CoreJson.parse[Provenance](json).left.map(_ => "malformed-edge-provenance")
    }
}
final case class DirectedEdgePage(items: Vector[DirectedGraphEdge], cursor: Option[String])

/** Additive capability: stored edge endpoints with provenance. Existing `GraphReader` callers are
  * unaffected. Order is stable: for `Both`, outgoing edges by edge ID, then incoming by edge ID.
  * Empty `edgeTypes` means the reader's allowed set; `window` constrains COAUTHORED_WITH only. The
  * cursor is opaque and valid only for the same node, window, direction and edge types.
  */
trait DirectedGraphReader extends GraphReader {
  def directedEdges(
      id: String,
      window: String,
      direction: EdgeDirection,
      edgeTypes: Set[String],
      limit: Int,
      cursor: Option[String]
  ): StorageResult[DirectedEdgePage]
}

/** Paging shared by the Neptune reader and the fakes; only the bounded fetch differs. */
private[storage] object DirectedEdgePaging {
  enum Phase { case Out, In, InWithoutSelfLoops }
  import StorageResult.*
  private def offset(text: String, max: Int): Option[Int] =
    text.toIntOption.filter(n => n >= 0 && n <= max)
  def page(direction: EdgeDirection, limit: Int, cursor: Option[String], maxOffset: Int)(
      fetch: (Phase, Int, Int) => StorageResult[Vector[DirectedGraphEdge]]
  ): StorageResult[DirectedEdgePage] = {
    def single(phase: Phase, off: Int, prefix: String) =
      RowCodec.map(fetch(phase, off, limit + 1)) { rows =>
        Found(
          DirectedEdgePage(
            rows.take(limit),
            Option.when(rows.size > limit)(prefix + (off + limit).toString)
          )
        )
      }
    direction match {
      case EdgeDirection.Out =>
        cursor.map(offset(_, maxOffset)).getOrElse(Some(0)) match {
          case Some(off) => single(Phase.Out, off, "")
          case None      => Rejected("invalid-bound")
        }
      case EdgeDirection.In =>
        cursor.map(offset(_, maxOffset)).getOrElse(Some(0)) match {
          case Some(off) => single(Phase.In, off, "")
          case None      => Rejected("invalid-bound")
        }
      case EdgeDirection.Both =>
        val parsed: Option[(Boolean, Int)] = cursor match {
          case None                          => Some((true, 0))
          case Some(c) if c.startsWith("o:") => offset(c.drop(2), maxOffset).map(true -> _)
          case Some(c) if c.startsWith("i:") => offset(c.drop(2), maxOffset).map(false -> _)
          case _                             => None
        }
        parsed match {
          case None               => Rejected("invalid-bound")
          case Some((false, off)) => single(Phase.InWithoutSelfLoops, off, "i:")
          case Some((true, off)) =>
            RowCodec.map(fetch(Phase.Out, off, limit + 1)) { outRows =>
              if (outRows.size > limit)
                Found(DirectedEdgePage(outRows.take(limit), Some("o:" + (off + limit))))
              else {
                val remaining = limit - outRows.size
                RowCodec.map(fetch(Phase.InWithoutSelfLoops, 0, remaining + 1)) { inRows =>
                  Found(
                    DirectedEdgePage(
                      outRows ++ inRows.take(remaining),
                      Option.when(inRows.size > remaining)("i:" + remaining)
                    )
                  )
                }
              }
            }
        }
    }
  }
}
final case class VectorDocument(
    key: String,
    values: Vector[Float],
    metadata: Map[String, String],
    textHash: String
)
final case class VectorHit(key: String, distance: Double, metadata: Map[String, String])
final case class VectorReject(key: String, reason: String)
final case class VectorBatchResult(written: Int, unchanged: Int, rejected: Vector[VectorReject])
trait VectorStore {
  def ensureIndex(name: String, dimension: Int, metric: String): StorageResult[String]
  def putBatch(index: String, documents: Vector[VectorDocument]): StorageResult[VectorBatchResult]
  def query(
      index: String,
      vector: Vector[Float],
      topK: Int,
      filter: Map[String, String]
  ): StorageResult[Vector[VectorHit]]
  def get(index: String, keys: Vector[String]): StorageResult[Vector[VectorDocument]]
}
final case class RetryConfig(
    maxAttempts: Int = 3,
    baseDelayMillis: Long = 10,
    maxDelayMillis: Long = 1000
) {
  require(maxAttempts >= 1 && baseDelayMillis >= 0 && maxDelayMillis >= baseDelayMillis)
}
final case class DynamoTables(
    runLedger: String,
    entityLinks: String,
    querySessions: String,
    evidence: String,
    artifacts: String,
    metrics: String,
    idempotencyIndex: String
) derives ReadWriter
final case class StorageConfig(
    bucket: String,
    tables: DynamoTables,
    retry: RetryConfig = RetryConfig(),
    maxObjectBytes: Int = 16 * 1024 * 1024,
    maxInlineEvidenceBytes: Int = 256 * 1024,
    maxDynamoItemBytes: Int = 380 * 1024,
    batchGetSize: Int = 100,
    queryPageSize: Int = 100,
    maxQueryPages: Int = 100,
    disposableSessionTtlSeconds: Option[Long] = None
) {
  require(bucket.nonEmpty && maxObjectBytes > 0 && maxInlineEvidenceBytes > 0)
  require(maxDynamoItemBytes > 0 && maxDynamoItemBytes <= 400 * 1024)
  require(batchGetSize > 0 && batchGetSize <= 100 && queryPageSize > 0 && maxQueryPages > 0)
  require(disposableSessionTtlSeconds.forall(_ > 0))
}
