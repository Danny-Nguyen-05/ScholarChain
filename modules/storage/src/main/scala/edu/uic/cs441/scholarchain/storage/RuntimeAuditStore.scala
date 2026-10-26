package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal
import upickle.default.ReadWriter
import StorageResult.*

/** Terminal audit publication is required before an answer can be returned. */
trait RuntimeAuditStore {
  def put(envelope: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope]
  def get(queryId: String): StorageResult[RuntimeAuditEnvelope]
}

/** The one-MiB envelope bound accommodates rejected proposals and provenance without putting those
  * payloads in DynamoDB. The small pointer has a separate sixteen-KiB application bound. Both are
  * configurable memory/storage bounds rather than provider limits.
  */
final case class RuntimeAuditStoreConfig(
    prefix: String,
    maxAuditBytes: Int = 1024 * 1024,
    maxPointerBytes: Int = 16384
) {
  require(prefix.trim.nonEmpty && !prefix.startsWith("/") && !prefix.split('/').contains(".."))
  require(maxAuditBytes > 0 && maxPointerBytes > 0)
}

private[storage] final case class RuntimeAuditPointer(
    schemaVersion: String,
    queryId: String,
    objectKey: String,
    sha256: String,
    size: Long
) derives ReadWriter

/** An immutable ordinary-object payload is published before a conditional pointer in the existing
  * query-session table. Reserved, hashed primary and idempotency keys do not overwrite application
  * query sessions. An interrupted pointer write may leave an orphan object; retrying the identical
  * envelope repairs publication. There is no cross-store transaction and no new table or GSI.
  * Inject a session adapter with TTL disabled: an audit pointer must not expire.
  */
final class ObjectStoreRuntimeAuditStore(
    objects: ObjectStore,
    sessions: QuerySessionStore,
    config: RuntimeAuditStoreConfig
) extends RuntimeAuditStore {
  private val pointerVersion = "scholarchain.runtime-audit-pointer.v1"
  private val readyState = "runtime-audit-complete"
  private def identity(queryId: String): String =
    StableIds.sha256Hex(StorageKeys.composite(config.prefix, queryId))
  private def sessionKey(queryId: String): String = "RUNTIME_AUDIT#" + identity(queryId)
  private def idempotencyKey(queryId: String): String = "runtime-audit-v1:" + identity(queryId)
  private def objectKey(hash: String): String =
    StorageKeys.versioned(config.prefix, "runtime-audit-v1", hash + ".json")

  private def guarded(
      body: => StorageResult[RuntimeAuditEnvelope]
  ): StorageResult[RuntimeAuditEnvelope] =
    try body
    catch {
      case _: InterruptedException =>
        Thread.currentThread().interrupt(); Rejected("audit-interrupted")
      case NonFatal(_) => Rejected("audit-storage-failure")
    }

  private def owned(session: QuerySession, queryId: String): Boolean =
    session.queryId == sessionKey(queryId) && session.idempotencyKey == idempotencyKey(queryId) &&
      session.expiresAtEpochSeconds.isEmpty

  private def pending(session: QuerySession): Boolean =
    session.revision == 0 && session.state == "created" && session.payload == "{}"

  private def readObject(pointer: RuntimeAuditPointer): StorageResult[RuntimeAuditEnvelope] = {
    if (
      pointer.schemaVersion != pointerVersion || !pointer.sha256.matches("[0-9a-f]{64}") ||
      pointer.objectKey != objectKey(
        pointer.sha256
      ) || pointer.size <= 0 || pointer.size > config.maxAuditBytes
    )
      return Rejected("invalid-audit-pointer")
    objects.get(pointer.objectKey) match {
      case Missing => Rejected("audit-object-missing")
      case result =>
        StorageResult.value(result) match {
          case Some(stored) =>
            if (
              stored.head.key != pointer.objectKey || stored.head.size != pointer.size ||
              stored.bytes.size.toLong != pointer.size || stored.head.sha256 != pointer.sha256 ||
              StorageKeys.sha256(stored.bytes) != pointer.sha256
            )
              Rejected("audit-object-integrity-mismatch")
            else {
              val envelope =
                upickle.default.read[RuntimeAuditEnvelope](new String(stored.bytes.toArray, UTF_8))
              if (
                envelope.queryId != pointer.queryId || RuntimeAuditValidation
                  .check(envelope)
                  .nonEmpty
              )
                Rejected("audit-object-envelope-mismatch")
              else Found(envelope)
            }
          case None => Rejected("audit-object-read-failed")
        }
    }
  }

  private def readSession(
      session: QuerySession,
      queryId: String
  ): StorageResult[RuntimeAuditEnvelope] = {
    if (!owned(session, queryId)) Rejected("audit-session-ownership-mismatch")
    else if (pending(session)) Missing
    else if (
      session.state != readyState || session.revision < 1 ||
      session.payload.getBytes(UTF_8).length > config.maxPointerBytes
    )
      Rejected("invalid-audit-session")
    else {
      val pointer = upickle.default.read[RuntimeAuditPointer](session.payload)
      if (pointer.queryId != queryId) Rejected("audit-pointer-query-mismatch")
      else readObject(pointer)
    }
  }

  def get(queryId: String): StorageResult[RuntimeAuditEnvelope] = guarded {
    if (queryId.trim.isEmpty) Rejected("invalid-audit-query-id")
    else
      sessions.get(sessionKey(queryId)) match {
        case Missing => Missing
        case result =>
          StorageResult.value(result) match {
            case Some(session) => readSession(session, queryId)
            case None          => Rejected("audit-session-read-failed")
          }
      }
  }

  def put(envelope: RuntimeAuditEnvelope): StorageResult[RuntimeAuditEnvelope] = synchronized {
    guarded {
      if (RuntimeAuditValidation.check(envelope).nonEmpty) return Rejected("invalid-audit-envelope")
      val bytes = CoreJson.compact(envelope).getBytes(UTF_8).toVector
      if (bytes.size > config.maxAuditBytes) return Rejected("audit-envelope-byte-bound")
      val hash = StorageKeys.sha256(bytes)
      val pointer = RuntimeAuditPointer(
        pointerVersion,
        envelope.queryId,
        objectKey(hash),
        hash,
        bytes.size.toLong
      )
      val pointerJson = CoreJson.compact(pointer)
      if (pointerJson.getBytes(UTF_8).length > config.maxPointerBytes)
        return Rejected("audit-pointer-byte-bound")
      get(envelope.queryId) match {
        case Found(old) if old == envelope => return Unchanged(envelope)
        case Found(_)                      => return Rejected("audit-query-content-conflict")
        case Missing                       => ()
        case _                             => return Rejected("audit-existing-record-unavailable")
      }
      val uploaded = objects.put(pointer.objectKey, bytes, "application/json", Map.empty)
      if (!StorageResult.successful(uploaded)) return Rejected("audit-object-write-failed")
      if (!StorageResult.value(readObject(pointer)).contains(envelope))
        return Rejected("audit-object-write-verification-failed")
      val created =
        sessions.createIfAbsent(sessionKey(envelope.queryId), idempotencyKey(envelope.queryId))
      val session =
        StorageResult.value(created).getOrElse(return Rejected("audit-session-create-failed"))
      if (!owned(session, envelope.queryId)) return Rejected("audit-session-ownership-mismatch")
      if (!pending(session)) {
        return readSession(session, envelope.queryId) match {
          case Found(old) if old == envelope => Unchanged(envelope)
          case Found(_)                      => Rejected("audit-query-content-conflict")
          case _                             => Rejected("audit-session-publication-conflict")
        }
      }
      val saved = sessions.update(
        session.copy(state = readyState, revision = session.revision + 1, payload = pointerJson),
        session.revision
      )
      if (
        StorageResult
          .successful(saved) && StorageResult.value(get(envelope.queryId)).contains(envelope)
      )
        Written(envelope)
      else
        get(envelope.queryId) match {
          case Found(old) if old == envelope => Unchanged(envelope)
          case Found(_)                      => Rejected("audit-query-content-conflict")
          case _                             => Rejected("audit-session-write-failed")
        }
    }
  }
}
