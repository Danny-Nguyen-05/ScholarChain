package edu.uic.cs441.scholarchain.storage

import edu.uic.cs441.scholarchain.core.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8
import java.util.concurrent.{Callable, CyclicBarrier, Executors, TimeUnit}
import StorageResult.*

/** Literal terminal audit observations exercise the real adapter with offline storage ports. */
class RuntimeAuditStorageSpec extends AnyFunSuite {
  private val config = RuntimeAuditStoreConfig("synthetic-runtime-audit")
  private def envelope(queryId: String = "query:synthetic-audit"): RuntimeAuditEnvelope =
    RuntimeAuditEnvelope(
      queryId,
      "trace:synthetic",
      "Unsupported synthetic question",
      "UNSUPPORTED",
      Some("unsupported-query"),
      None,
      Vector.empty,
      12L,
      "a" * 64
    )
  private def primary(queryId: String): String = "RUNTIME_AUDIT#" +
    StableIds.sha256Hex(StorageKeys.composite(config.prefix, queryId))

  private class ObjectProxy(val delegate: ObjectStore) extends ObjectStore {
    def put(
        k: String,
        b: Vector[Byte],
        t: String,
        m: Map[String, String]
    ): StorageResult[ObjectHead] =
      delegate.put(k, b, t, m)
    def get(k: String): StorageResult[StoredObject] = delegate.get(k)
    def head(k: String): StorageResult[ObjectHead] = delegate.head(k)
  }
  private class SessionProxy(val delegate: QuerySessionStore) extends QuerySessionStore {
    def createIfAbsent(q: String, i: String): StorageResult[QuerySession] =
      delegate.createIfAbsent(q, i)
    def get(q: String): StorageResult[QuerySession] = delegate.get(q)
    def lookupByIdempotencyKey(i: String): StorageResult[QuerySession] =
      delegate.lookupByIdempotencyKey(i)
    def update(s: QuerySession, expected: Long): StorageResult[QuerySession] =
      delegate.update(s, expected)
  }

  test(
    "terminal audit writes reads and identical replay use immutable content with a small pointer"
  ) {
    val objects = new InMemoryObjectStore
    val sessions = new InMemoryQuerySessionStore
    val store = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    val audit = envelope()
    assert(store.get(audit.queryId) == Missing)
    assert(store.put(audit) == Written(audit))
    assert(store.get(audit.queryId) == Found(audit))
    assert(store.put(audit) == Unchanged(audit))
    assert(objects.writeOrder.size == 1)
    val session = StorageResult.value(sessions.get(primary(audit.queryId))).get
    val pointer = upickle.default.read[RuntimeAuditPointer](session.payload)
    assert(session.queryId != audit.queryId && session.expiresAtEpochSeconds.isEmpty)
    assert(session.revision == 1 && session.state == "runtime-audit-complete")
    assert(pointer.queryId == audit.queryId)
    assert(pointer.sha256 == StorageKeys.sha256(CoreJson.compact(audit).getBytes(UTF_8).toVector))
    assert(pointer.size == CoreJson.compact(audit).getBytes(UTF_8).length.toLong)
    assert(session.payload.getBytes(UTF_8).length <= config.maxPointerBytes)
    assert(
      ujson.read(session.payload).obj.keySet ==
        Set("schemaVersion", "queryId", "objectKey", "sha256", "size")
    )
    assert(!session.payload.contains(audit.question))
  }

  test("audit namespace preserves an existing application query session") {
    val sessions = new InMemoryQuerySessionStore
    val audit = envelope()
    val original =
      StorageResult.value(sessions.createIfAbsent(audit.queryId, "client-idempotency")).get
    val store = new ObjectStoreRuntimeAuditStore(new InMemoryObjectStore, sessions, config)
    assert(store.put(audit) == Written(audit))
    assert(sessions.get(audit.queryId) == Found(original))
    assert(sessions.lookupByIdempotencyKey("client-idempotency") == Found(original))
  }

  test("a changed terminal record cannot overwrite the first audit for a query") {
    val objects = new InMemoryObjectStore
    val store = new ObjectStoreRuntimeAuditStore(objects, new InMemoryQuerySessionStore, config)
    val first = envelope()
    assert(store.put(first) == Written(first))
    assert(
      store.put(first.copy(reason = Some("different-terminal-observation"))) ==
        Rejected("audit-query-content-conflict")
    )
    assert(store.get(first.queryId) == Found(first))
    assert(objects.writeOrder.size == 1)
  }

  test("invalid envelopes and byte bounds refuse before object publication") {
    val objects = new InMemoryObjectStore
    val sessions = new InMemoryQuerySessionStore
    val store = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    assert(store.put(envelope().copy(answerHash = "bad")) == Rejected("invalid-audit-envelope"))
    assert(store.put(envelope().copy(outcome = "ANSWERED")) == Rejected("invalid-audit-envelope"))
    assert(
      new ObjectStoreRuntimeAuditStore(objects, sessions, config.copy(maxAuditBytes = 8))
        .put(envelope()) == Rejected("audit-envelope-byte-bound")
    )
    assert(
      new ObjectStoreRuntimeAuditStore(objects, sessions, config.copy(maxPointerBytes = 8))
        .put(envelope()) == Rejected("audit-pointer-byte-bound")
    )
    assert(objects.writeOrder.isEmpty)
  }

  test("rejected fabricated claim proposals survive exact audit storage and lookup") {
    val run = "run:00112233-4455-4677-8899-aabbccddeeff"
    val provenance = Provenance(
      SchemaVersions.domain,
      SourceType.ScholarChain,
      "synthetic-runtime-audit",
      None,
      "synthetic-snapshot",
      None,
      None,
      run,
      Vector("Synthetic fixture")
    )
    val plan = QueryPlan(
      "plan:" + "a" * 64,
      SchemaVersions.domain,
      "Synthetic question",
      Vector(QueryOperation.ComponentLookup),
      YearWindow(1000, 9999),
      Vector.empty,
      Vector.empty,
      Vector.empty,
      None,
      25,
      10,
      6,
      provenance
    )
    val bad = AnswerClaim(
      "",
      SchemaVersions.domain,
      "Unverified fabricated proposal",
      Vector("invented-id"),
      VerificationStatus.Unverified,
      None,
      provenance,
      Some(
        TypedAnswerClaim(
          RuntimeClaimType.Metric,
          Vector("invented-researcher"),
          Vector(RuntimeClaimValue("count", number = Some("not-a-number"))),
          Vector("all-years"),
          "fabricated-template"
        )
      )
    )
    assert(DomainValidation.check(bad).isLeft)
    val audit = envelope().copy(
      outcome = "ABSTAINED",
      record = Some(
        AuditRecord(
          envelope().queryId,
          envelope().traceId,
          plan,
          Vector.empty,
          Vector.empty,
          Vector.empty,
          Vector.empty,
          Vector.empty,
          12L,
          Vector(bad),
          VerificationResult(
            Vector(
              ClaimVerificationResult("", ClaimVerdict.Unsupported, Vector("fabricated-claim"))
            ),
            Vector(bad),
            abstained = true
          ),
          envelope().answerHash
        )
      )
    )
    val store = new ObjectStoreRuntimeAuditStore(
      new InMemoryObjectStore,
      new InMemoryQuerySessionStore,
      config
    )
    assert(RuntimeAuditValidation.check(audit).isEmpty)
    assert(store.put(audit) == Written(audit))
    assert(
      StorageResult.value(store.get(audit.queryId)).get.record.get.attemptedClaims == Vector(bad)
    )
    assert(
      StorageResult
        .value(store.get(audit.queryId))
        .get
        .record
        .get
        .verification
        .rejectedClaims == Vector(bad)
    )
  }

  test("object write failure is typed and never publishes a terminal session pointer") {
    val sessions = new InMemoryQuerySessionStore
    val objects = new ObjectProxy(new InMemoryObjectStore) {
      override def put(k: String, b: Vector[Byte], t: String, m: Map[String, String]) =
        Rejected("injected-object-failure")
    }
    val store = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    assert(store.put(envelope()) == Rejected("audit-object-write-failed"))
    assert(sessions.get(primary(envelope().queryId)) == Missing)
  }

  test("failed pointer publication leaves a retryable object and pending session") {
    val objects = new InMemoryObjectStore
    val underlying = new InMemoryQuerySessionStore
    var fail = true
    val sessions = new SessionProxy(underlying) {
      override def update(s: QuerySession, expected: Long): StorageResult[QuerySession] =
        if (fail) Rejected("injected-update-failure") else super.update(s, expected)
    }
    val store = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    assert(store.put(envelope()) == Rejected("audit-session-write-failed"))
    assert(store.get(envelope().queryId) == Missing && objects.writeOrder.size == 1)
    fail = false
    assert(store.put(envelope()) == Written(envelope()))
    assert(store.get(envelope().queryId) == Found(envelope()))
    assert(objects.writeOrder.size == 1)
  }

  test("lost successful pointer-write response is recognized by authoritative lookup") {
    val sessions = new SessionProxy(new InMemoryQuerySessionStore) {
      override def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        super.update(s, expected)
        Rejected("injected-lost-reply")
      }
    }
    val store = new ObjectStoreRuntimeAuditStore(new InMemoryObjectStore, sessions, config)
    assert(store.put(envelope()) == Unchanged(envelope()))
    assert(store.get(envelope().queryId) == Found(envelope()))
  }

  test("session creation failure is typed and retrying reuses the existing immutable object") {
    val objects = new InMemoryObjectStore
    var fail = true
    val sessions = new SessionProxy(new InMemoryQuerySessionStore) {
      override def createIfAbsent(q: String, i: String): StorageResult[QuerySession] =
        if (fail) Rejected("injected-create-failure") else super.createIfAbsent(q, i)
    }
    val store = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    assert(store.put(envelope()) == Rejected("audit-session-create-failed"))
    fail = false
    assert(store.put(envelope()) == Written(envelope()))
    assert(objects.writeOrder.size == 1)
  }

  test("corrupt or missing stored objects cannot be returned through a valid pointer") {
    val underlying = new InMemoryObjectStore
    var corrupt = false
    var missing = false
    val objects = new ObjectProxy(underlying) {
      override def get(k: String): StorageResult[StoredObject] =
        if (missing) Missing
        else
          super.get(k) match {
            case Found(value) if corrupt => Found(value.copy(bytes = value.bytes :+ 0.toByte))
            case other                   => other
          }
    }
    val store = new ObjectStoreRuntimeAuditStore(objects, new InMemoryQuerySessionStore, config)
    assert(store.put(envelope()) == Written(envelope()))
    corrupt = true
    assert(store.get(envelope().queryId) == Rejected("audit-object-integrity-mismatch"))
    corrupt = false; missing = true
    assert(store.get(envelope().queryId) == Rejected("audit-object-missing"))
  }

  test("pointer query and key tampering fail closed") {
    val underlying = new InMemoryQuerySessionStore
    var change: QuerySession => QuerySession = identity
    val sessions = new SessionProxy(underlying) {
      override def get(q: String): StorageResult[QuerySession] = super.get(q) match {
        case Found(value) => Found(change(value))
        case other        => other
      }
    }
    val store = new ObjectStoreRuntimeAuditStore(new InMemoryObjectStore, sessions, config)
    assert(store.put(envelope()) == Written(envelope()))
    change = session =>
      session.copy(payload =
        upickle.default.write(
          upickle.default.read[RuntimeAuditPointer](session.payload).copy(queryId = "query:another")
        )
      )
    assert(store.get(envelope().queryId) == Rejected("audit-pointer-query-mismatch"))
    change = session =>
      session.copy(payload =
        upickle.default.write(
          upickle.default
            .read[RuntimeAuditPointer](session.payload)
            .copy(objectKey = "other/versions/v1/wrong.json")
        )
      )
    assert(store.get(envelope().queryId) == Rejected("invalid-audit-pointer"))
  }

  test("TTL-bearing sessions and foreign reserved rows are never reused") {
    val expiring = new ObjectStoreRuntimeAuditStore(
      new InMemoryObjectStore,
      new InMemoryQuerySessionStore(Some(60L)),
      config
    )
    assert(expiring.put(envelope()) == Rejected("audit-session-ownership-mismatch"))
    val sessions = new InMemoryQuerySessionStore
    assert(
      StorageResult.successful(
        sessions.createIfAbsent(primary(envelope().queryId), "unrelated-owner")
      )
    )
    val store = new ObjectStoreRuntimeAuditStore(new InMemoryObjectStore, sessions, config)
    assert(store.put(envelope()) == Rejected("audit-existing-record-unavailable"))
    assert(
      StorageResult
        .value(sessions.get(primary(envelope().queryId)))
        .get
        .idempotencyKey == "unrelated-owner"
    )
  }

  test("two adapters racing different records publish only one immutable winner") {
    val underlying = new InMemoryQuerySessionStore
    val barrier = new CyclicBarrier(2)
    val sessions = new SessionProxy(underlying) {
      override def update(s: QuerySession, expected: Long): StorageResult[QuerySession] = {
        barrier.await(5, TimeUnit.SECONDS)
        super.update(s, expected)
      }
    }
    val objects = new InMemoryObjectStore
    val first = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    val second = new ObjectStoreRuntimeAuditStore(objects, sessions, config)
    val other = envelope().copy(reason = Some("another-synthetic-outcome"))
    val pool = Executors.newFixedThreadPool(2)
    try {
      val a = pool.submit(new Callable[StorageResult[RuntimeAuditEnvelope]] {
        def call() = first.put(envelope())
      })
      val b = pool.submit(new Callable[StorageResult[RuntimeAuditEnvelope]] {
        def call() = second.put(other)
      })
      val results = Vector(a.get(10, TimeUnit.SECONDS), b.get(10, TimeUnit.SECONDS))
      assert(results.count(StorageResult.successful) == 1)
      assert(results.count(_ == Rejected("audit-query-content-conflict")) == 1)
      assert(
        StorageResult
          .value(first.get(envelope().queryId))
          .exists(v => v == envelope() || v == other)
      )
    } finally pool.shutdownNow()
  }

  test("matching in-memory fake exposes the same durable-audit lookup and conflict contract") {
    val store = new edu.uic.cs441.scholarchain.storage.fakes.InMemoryRuntimeAuditStore
    assert(store.put(envelope()) == Written(envelope()))
    assert(store.get(envelope().queryId) == Found(envelope()))
    assert(store.put(envelope()) == Unchanged(envelope()))
    assert(
      store.put(envelope().copy(question = "changed")) == Rejected("audit-query-content-conflict")
    )
  }
}
