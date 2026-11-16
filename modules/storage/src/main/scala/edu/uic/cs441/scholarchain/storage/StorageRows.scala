package edu.uic.cs441.scholarchain.storage

import upickle.default.{ReadWriter, read, write}
import scala.collection.mutable
import StorageResult.*
import java.nio.charset.StandardCharsets.UTF_8

private[storage] final case class RowKey(pk: String, sk: String)
private[storage] final case class StorageRow(
    key: RowKey,
    payload: String,
    attributes: Map[String, String] = Map.empty
)
private[storage] enum RowCondition {
  case Absent
  case PayloadEquals(payload: String)
}
private[storage] final case class RowWrite(row: StorageRow, condition: RowCondition)
private[storage] trait StorageRows {
  def read(table: String, key: RowKey): StorageResult[StorageRow]
  def query(
      table: String,
      pk: String,
      descending: Boolean = false
  ): StorageResult[Vector[StorageRow]]
  def index(table: String, index: String, key: String): StorageResult[Vector[StorageRow]]
  def write(table: String, row: StorageRow, condition: RowCondition): StorageResult[StorageRow]
  def transact(table: String, writes: Vector[RowWrite]): StorageResult[Unit]
  def batch(table: String, keys: Vector[RowKey]): StorageResult[Vector[StorageRow]]
}
private[storage] final class MemoryRows extends StorageRows {
  private val rows = mutable.Map.empty[(String, RowKey), StorageRow]
  def read(table: String, key: RowKey): StorageResult[StorageRow] = synchronized {
    rows.get(table -> key).map(Found(_)).getOrElse(Missing)
  }
  def query(table: String, pk: String, descending: Boolean): StorageResult[Vector[StorageRow]] =
    synchronized {
      val result = rows.iterator
        .collect { case ((t, k), v) if t == table && k.pk == pk => v }
        .toVector
        .sortBy(_.key.sk)
      Found(if (descending) result.reverse else result)
    }
  def index(table: String, index: String, key: String): StorageResult[Vector[StorageRow]] =
    synchronized {
      Found(rows.iterator.collect {
        case ((t, _), v) if t == table && v.attributes.get("idempotencyKey").contains(key) => v
      }.toVector)
    }
  private def allowed(table: String, w: RowWrite): Boolean = w.condition match {
    case RowCondition.Absent           => !rows.contains(table -> w.row.key)
    case RowCondition.PayloadEquals(p) => rows.get(table -> w.row.key).exists(_.payload == p)
  }
  def write(table: String, row: StorageRow, condition: RowCondition): StorageResult[StorageRow] =
    synchronized {
      if (allowed(table, RowWrite(row, condition))) { rows(table -> row.key) = row; Written(row) }
      else Rejected("conditional-conflict")
    }
  def transact(table: String, writes: Vector[RowWrite]): StorageResult[Unit] = synchronized {
    if (writes.map(_.row.key).distinct.size != writes.size) Rejected("duplicate-transaction-key")
    else if (writes.forall(allowed(table, _))) {
      writes.foreach(w => rows(table -> w.row.key) = w.row); Written(())
    } else Rejected("conditional-conflict")
  }
  def batch(table: String, keys: Vector[RowKey]): StorageResult[Vector[StorageRow]] = synchronized {
    Found(keys.distinct.flatMap(k => rows.get(table -> k)))
  }
}
private[storage] object RowCodec {
  val schema = "scholarchain.storage.v1"
  def encode[A: ReadWriter](a: A): String =
    ujson.Obj("schemaVersion" -> schema, "record" -> ujson.read(write(a))).render()
  def decode[A: ReadWriter](s: String): StorageResult[A] = try {
    val json = ujson.read(s)
    if (json("schemaVersion").str != schema) Rejected("unsupported-schema-version")
    else Found(read[A](json("record")))
  } catch { case _: Exception => Rejected("corrupt-row") }
  def map[A, B](result: StorageResult[A])(f: A => StorageResult[B]): StorageResult[B] =
    result match {
      case Found(a)      => f(a)
      case Written(a)    => f(a)
      case Unchanged(a)  => f(a)
      case Retried(n, r) => Retried(n, map(r)(f))
      case Missing       => Missing
      case Rejected(c)   => Rejected(c)
    }
}
private[storage] class TypedRows[A: ReadWriter](val rows: StorageRows, val table: String) {
  import RowCodec.*
  def get(key: RowKey): StorageResult[A] = map(rows.read(table, key))(r => decode[A](r.payload))
  def put(key: RowKey, value: A, attrs: Map[String, String] = Map.empty): StorageResult[A] = {
    val row = StorageRow(key, encode(value), attrs)
    rows.write(table, row, RowCondition.Absent) match {
      case Written(_)             => Written(value)
      case Retried(n, Written(_)) => Retried(n, Written(value))
      case Rejected("conditional-conflict") =>
        map(get(key)) { old =>
          if (encode(old) == row.payload) Unchanged(old) else Rejected("immutable-conflict")
        }
      case r => map(r)(_ => Rejected("write-failed"))
    }
  }
  def all(pk: String, descending: Boolean = false): StorageResult[Vector[A]] =
    map(rows.query(table, pk, descending))(decodeAll)
  def decodeAll(rs: Vector[StorageRow]): StorageResult[Vector[A]] = {
    val values = rs.map(r => decode[A](r.payload))
    values.collectFirst { case Rejected(c) => c } match {
      case Some(c) => Rejected(c)
      case None    => Found(values.flatMap(StorageResult.value))
    }
  }
}
private[storage] class RowEntityLinks(rows: StorageRows, table: String) extends EntityLinkCache {
  private val typed = new TypedRows[EntityLink](rows, table)
  def putLink(link: EntityLink): StorageResult[EntityLink] = {
    if (
      link.normalizedKey.isEmpty || link.researcherId.isEmpty || link.policyVersion.isEmpty || link.sourceId.isEmpty || link.runId.isEmpty || link.confidence
        .exists(c => !c.isFinite || c < 0 || c > 1)
    ) Rejected("invalid-entity-link")
    else
      typed.put(
        RowKey(
          StorageKeys.composite(link.entityType, link.normalizedKey),
          StorageKeys.composite(link.policyVersion, link.sourceId)
        ),
        link
      )
  }
  def lookupByNormalizedName(name: String): StorageResult[Vector[EntityLink]] = typed.all(
    StorageKeys.composite("name", edu.uic.cs441.scholarchain.core.TextNorm.personName(name))
  )
  def lookupByExternalId(namespace: String, id: String): StorageResult[Vector[EntityLink]] =
    typed.all(StorageKeys.composite(s"external:$namespace", id))
}
private[storage] class RowArtifacts(rows: StorageRows, table: String) extends ArtifactRegistry {
  private val typed = new TypedRows[ArtifactRecord](rows, table)
  def register(
      id: String,
      version: String,
      uri: String,
      hash: String
  ): StorageResult[ArtifactRecord] = {
    if (id.isEmpty || version.isEmpty || uri.isEmpty || !hash.matches("[0-9a-f]{64}"))
      Rejected("invalid-artifact")
    else typed.put(RowKey(id, version), ArtifactRecord(id, version, uri, hash))
  }
  def get(id: String, version: String): StorageResult[ArtifactRecord] =
    typed.get(RowKey(id, version))
  def latest(id: String): StorageResult[ArtifactRecord] =
    RowCodec.map(typed.all(id, true))(_.headOption.map(Found(_)).getOrElse(Missing))
}
private[storage] class RowMetrics(rows: StorageRows, table: String) extends ResearcherMetricStore {
  private val typed = new TypedRows[ResearcherMetricRecord](rows, table)
  def put(r: ResearcherMetricRecord): StorageResult[ResearcherMetricRecord] = {
    val valid =
      try { ujson.read(r.payloadJson); ujson.read(r.qualificationsJson); true }
      catch { case _: Exception => false }
    if (
      r.researcherId.isEmpty || r.windowId.isEmpty || r.metricVersion.isEmpty || r.runId.isEmpty || !valid
    ) Rejected("invalid-metric")
    else typed.put(RowKey(r.researcherId, r.windowId), r)
  }
  def get(id: String, window: String): StorageResult[ResearcherMetricRecord] =
    typed.get(RowKey(id, window))
  def batchGet(keys: Vector[(String, String)]): StorageResult[Vector[ResearcherMetricRecord]] =
    RowCodec.map(rows.batch(table, keys.map((p, s) => RowKey(p, s))))(typed.decodeAll)
}
private[storage] class RowSessions(
    rows: StorageRows,
    table: String,
    indexName: String,
    ttl: Option[Long],
    now: () => Long
) extends QuerySessionStore {
  private val typed = new TypedRows[QuerySession](rows, table)
  private def key(q: String) = RowKey(q, "SESSION")
  private def reservation(i: String) =
    RowKey("IDEMPOTENCY#" + StorageKeys.sha256(i.getBytes(UTF_8).toVector), "RESERVATION")
  def get(id: String): StorageResult[QuerySession] = typed.get(key(id))
  def lookupByIdempotencyKey(i: String): StorageResult[QuerySession] =
    RowCodec.map(rows.index(table, indexName, i)) { rs =>
      val sessions = rs.filter(_.key.sk == "SESSION")
      if (sessions.size > 1) Rejected("duplicate-idempotency-key")
      else sessions.headOption.map(r => RowCodec.decode[QuerySession](r.payload)).getOrElse(Missing)
    }
  def createIfAbsent(id: String, i: String): StorageResult[QuerySession] = {
    if (id.isEmpty || id.startsWith("IDEMPOTENCY#") || i.isEmpty)
      return Rejected("invalid-session-key")
    val session = QuerySession(id, i, "created", 0, "{}", ttl.map(t => now() + t))
    val attrs = Map("idempotencyKey" -> i) ++ session.expiresAtEpochSeconds.map(t =>
      "expiresAt" -> t.toString
    )
    val writes = Vector(
      RowWrite(StorageRow(key(id), RowCodec.encode(session), attrs), RowCondition.Absent),
      RowWrite(
        StorageRow(
          reservation(i),
          RowCodec.encode(session),
          session.expiresAtEpochSeconds
            .map(t => Map("expiresAt" -> t.toString))
            .getOrElse(Map.empty)
        ),
        RowCondition.Absent
      )
    )
    rows.transact(table, writes) match {
      case Written(_)             => Written(session)
      case Retried(n, Written(_)) => Retried(n, Written(session))
      case Rejected("conditional-conflict") =>
        rows.read(table, reservation(i)) match {
          case Missing => Rejected("query-id-conflict")
          case reserved =>
            RowCodec.map(reserved) { r =>
              RowCodec.map(RowCodec.decode[QuerySession](r.payload)) { original =>
                // Reservation is authoritative; GSI may lag. Return current state by primary key.
                if (original.queryId != id) Rejected("idempotency-key-conflict")
                else RowCodec.map(get(original.queryId))(Unchanged(_))
              }
            }
        }
      case r => RowCodec.map(r)(_ => Rejected("session-create-failed"))
    }
  }
  def update(s: QuerySession, expectedRevision: Long): StorageResult[QuerySession] =
    RowCodec.map(get(s.queryId)) { old =>
      if (
        s.idempotencyKey != old.idempotencyKey || s.expiresAtEpochSeconds != old.expiresAtEpochSeconds || s.revision != expectedRevision + 1 || old.revision != expectedRevision
      ) Rejected("revision-conflict")
      else {
        val attrs = Map("idempotencyKey" -> s.idempotencyKey) ++ s.expiresAtEpochSeconds.map(t =>
          "expiresAt" -> t.toString
        )
        RowCodec.map(
          rows.write(
            table,
            StorageRow(key(s.queryId), RowCodec.encode(s), attrs),
            RowCondition.PayloadEquals(RowCodec.encode(old))
          )
        )(_ => Written(s))
      }
    }
}
private[storage] class RowRunLedger(rows: StorageRows, table: String) extends RunLedger {
  private val roots = new TypedRows[RunRecord](rows, table)
  private val stages = new TypedRows[RunStage](rows, table)
  private def rootKey(id: String) = RowKey(id, "RUN")
  private def stageKey(id: String, stage: String) = RowKey(id, "STAGE#" + stage)
  def startRun(id: String): StorageResult[RunRecord] = {
    if (id.isEmpty) Rejected("invalid-run-id")
    else
      roots.put(rootKey(id), RunRecord(id, "running", Vector.empty)) match {
        case Rejected("immutable-conflict") => RowCodec.map(getRun(id))(Unchanged(_))
        case r                              => r
      }
  }
  def getRun(id: String): StorageResult[RunRecord] = RowCodec.map(roots.get(rootKey(id))) { r =>
    RowCodec.map(rows.query(table, id)) { all =>
      val stageRows = all.filter(_.key.sk.startsWith("STAGE#"))
      RowCodec.map(stages.decodeAll(stageRows)) { ss =>
        RowCodec.map(stages.decodeAll(all.filter(_.key.sk.startsWith("FAILURE#")))) { failures =>
          Found(r.copy(stages = ss, failures = failures))
        }
      }
    }
  }
  // `known` is the stage row the caller has already read (recordStage, completeStage): reading it
  // again costs one more DynamoDB GetItem per transition and decides nothing new, because the
  // transaction below is conditioned on that exact stage payload (or its absence) and on the root.
  private def transition(
      id: String,
      stage: String,
      next: RunStage,
      known: Option[StorageResult[RunStage]] = None
  ): StorageResult[RunStage] = {
    if (stage.isEmpty || next.retryCount < 0) return Rejected("invalid-stage")
    RowCodec.map(roots.get(rootKey(id))) { root =>
      if (root.state != "running") Rejected("run-not-running")
      else {
        val current = known.getOrElse(stages.get(stageKey(id, stage)))
        val condition = current match {
          case Missing if next.state == "running" && next.retryCount == 0 =>
            Some(RowCondition.Absent)
          case Found(old) if old == next => return Unchanged(next)
          case Found(old)
              if old.state == "failed" && next.state == "running" && next.retryCount == old.retryCount =>
            Some(RowCondition.PayloadEquals(RowCodec.encode(old)))
          case Found(old)
              if old.state == "running" && next.state == "complete" && next.retryCount == old.retryCount =>
            Some(RowCondition.PayloadEquals(RowCodec.encode(old)))
          case Found(old)
              if old.state == "running" && next.state == "failed" && next.retryCount == old.retryCount + 1 =>
            Some(RowCondition.PayloadEquals(RowCodec.encode(old)))
          case _ => None
        }
        condition match {
          case None => Rejected("invalid-stage-transition")
          case Some(c) =>
            val ws = Vector(
              RowWrite(
                StorageRow(rootKey(id), RowCodec.encode(root.copy(revision = root.revision + 1))),
                RowCondition.PayloadEquals(RowCodec.encode(root))
              ),
              RowWrite(StorageRow(stageKey(id, stage), RowCodec.encode(next)), c)
            ) ++ (if (next.state == "failed")
                    Vector(
                      RowWrite(
                        StorageRow(
                          RowKey(
                            id,
                            "FAILURE#" + StorageKeys.composite(stage, next.retryCount.toString)
                          ),
                          RowCodec.encode(next)
                        ),
                        RowCondition.Absent
                      )
                    )
                  else Vector.empty)
            RowCodec.map(rows.transact(table, ws))(_ => Written(next))
        }
      }
    }
  }
  def recordStage(id: String, stage: String): StorageResult[RunStage] = {
    val current = stages.get(stageKey(id, stage))
    val retries = StorageResult.value(current).map(_.retryCount).getOrElse(0)
    transition(id, stage, RunStage(stage, "running", retries, None), Some(current))
  }
  def recordFailure(
      id: String,
      stage: String,
      retryCount: Int,
      reason: String
  ): StorageResult[RunStage] = {
    if (!reason.matches("[A-Za-z0-9._-]{1,128}")) Rejected("invalid-reason-code")
    else transition(id, stage, RunStage(stage, "failed", retryCount, Some(reason)))
  }
  def completeStage(id: String, stage: String): StorageResult[RunStage] = {
    val current = stages.get(stageKey(id, stage))
    val retries = StorageResult.value(current).map(_.retryCount).getOrElse(0)
    transition(id, stage, RunStage(stage, "complete", retries, None), Some(current))
  }
  def completeRun(id: String): StorageResult[RunRecord] = RowCodec.map(roots.get(rootKey(id))) {
    root =>
      if (root.state == "complete") Unchanged(root)
      else
        RowCodec.map(getRun(id)) { current =>
          if (current.stages.exists(_.state != "complete")) Rejected("incomplete-stage")
          else {
            val next = root.copy(state = "complete", revision = root.revision + 1)
            RowCodec.map(
              rows.write(
                table,
                StorageRow(rootKey(id), RowCodec.encode(next)),
                RowCondition.PayloadEquals(RowCodec.encode(root))
              )
            )(_ => Written(next))
          }
        }
  }
}
