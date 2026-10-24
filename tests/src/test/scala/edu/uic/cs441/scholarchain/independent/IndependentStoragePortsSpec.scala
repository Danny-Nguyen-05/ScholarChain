package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryArtifactRegistry,
  InMemoryEntityLinkCache,
  InMemoryEvidenceBundleStore,
  InMemoryObjectStore,
  InMemoryQuerySessionStore,
  InMemoryResearcherMetricStore,
  InMemoryRunLedger
}
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets.UTF_8

class IndependentStoragePortsSpec extends AnyFunSuite {
  import IndependentStorageFixtures.*
  import StorageResult.*

  private def rejected(result: StorageResult[?]): Boolean = result match {
    case Rejected(_) => true
    case _           => false
  }

  test("versioned immutable objects retain bytes, metadata, and the standard SHA-256 digest") {
    val store: ObjectStore = new InMemoryObjectStore()
    val key = StorageKeys.versioned("synthetic", "v001", "value.txt")
    assert(key == "synthetic/versions/v001/value.txt")
    val bytes = "abc".getBytes(UTF_8).toVector
    val first = store.put(key, bytes, "text/plain", Map("run-id" -> runId))
    assert(first.isInstanceOf[Written[?]])
    val head = StorageResult.value(first).get
    assert(head.sha256 == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    assert(head.size == 3)
    assert(head.metadata("run-id") == runId)
    assert(StorageResult.value(store.get(key)).exists(_.bytes == bytes))
    assert(store.put(key, bytes, "text/plain", Map("run-id" -> runId)).isInstanceOf[Unchanged[?]])
    assert(rejected(store.put(key, "different".getBytes(UTF_8).toVector, "text/plain", Map.empty)))
    assert(StorageResult.value(store.get(key)).exists(_.bytes == bytes))
    assert(store.get("synthetic/versions/v001/missing") == Missing)
    assert(store.exists("synthetic/versions/v001/missing") == Found(false))
  }

  test("support keys keep multiple works and cannot alias through delimiter placement") {
    assert(StorageKeys.support("edge:one", "work:two") == "8:edge:one8:work:two")
    assert(StorageKeys.support("a#b", "c") != StorageKeys.support("a", "b#c"))
    assert(
      StorageKeys.support("same-edge", "first-work") != StorageKeys.support(
        "same-edge",
        "second-work"
      )
    )
    assert(StorageKeys.composite("é", "x") == "2:é1:x")
  }

  test(
    "run publisher writes the manifest last, reports unchanged reload and withholds failed completion"
  ) {
    val store = new InMemoryObjectStore()
    val one =
      ObjectUpload("synthetic/versions/001/one", Vector(1.toByte), "application/octet-stream")
    val two =
      ObjectUpload("synthetic/versions/001/two", Vector(2.toByte), "application/octet-stream")
    val manifest = ObjectUpload(
      "synthetic/versions/001/manifest.json",
      "{}".getBytes(UTF_8).toVector,
      "application/json"
    )
    val publisher = new RunObjectPublisher(store)
    assert(publisher.publish(Vector(one, two), manifest).isInstanceOf[Written[?]])
    assert(store.writeOrder.toVector == Vector(one.key, two.key, manifest.key))
    assert(publisher.publish(Vector(one, two), manifest).isInstanceOf[Unchanged[?]])
    assert(store.writeOrder.toVector == Vector(one.key, two.key, manifest.key))
    val failed = new InMemoryObjectStore()
    assert(
      rejected(
        new RunObjectPublisher(failed).publish(Vector(one, two.copy(key = "unversioned")), manifest)
      )
    )
    assert(failed.head(manifest.key) == Missing)
    assert(failed.writeOrder.toVector == Vector(one.key))
  }

  test("object validation rejects malformed metadata and caller-supplied mismatching hashes") {
    val store: ObjectStore = new InMemoryObjectStore()
    val bytes = Vector(1.toByte)
    val key = "synthetic/versions/001/object"
    assert(rejected(store.put(key, bytes, "text/plain", Map("sha256" -> "0" * 64))))
    assert(rejected(store.put(key, bytes, "text/plain", Map("Run-Id" -> runId))))
    assert(rejected(store.put(key, bytes, "", Map.empty)))
    assert(store.head(key) == Missing)
  }

  test("run ledger rejects stages before start and changes after completion") {
    val ledger: RunLedger = new InMemoryRunLedger()
    assert(!StorageResult.successful(ledger.recordStage(runId, "load")))
    assert(ledger.startRun(runId).isInstanceOf[Written[?]])
    assert(ledger.startRun(runId).isInstanceOf[Unchanged[?]])
    assert(ledger.recordStage(runId, "load").isInstanceOf[Written[?]])
    assert(rejected(ledger.completeRun(runId)))
    assert(rejected(ledger.recordFailure(runId, "load", 2, "synthetic-throttle")))
    assert(ledger.recordFailure(runId, "load", 1, "synthetic-throttle").isInstanceOf[Written[?]])
    assert(!StorageResult.successful(ledger.completeRun(runId)))
    assert(ledger.recordStage(runId, "load").isInstanceOf[Written[?]])
    assert(ledger.recordFailure(runId, "load", 2, "synthetic-throttle").isInstanceOf[Written[?]])
    assert(StorageResult.value(ledger.getRun(runId)).get.stages.exists(_.retryCount == 2))
    assert(ledger.recordStage(runId, "load").isInstanceOf[Written[?]])
    assert(ledger.completeStage(runId, "load").isInstanceOf[Written[?]])
    assert(ledger.completeRun(runId).isInstanceOf[Written[?]])
    assert(rejected(ledger.recordStage(runId, "after-completion")))
    assert(rejected(ledger.recordFailure(runId, "load", 3, "late-failure")))
  }

  test("entity cache retains multiple candidates and rejects conflicting replacement of one key") {
    val cache: EntityLinkCache = new InMemoryEntityLinkCache()
    val link = EntityLink(
      "name",
      "synthetic example",
      policyVersion,
      "source-one",
      researcherId,
      "Synthetic Example",
      Vector("Synthetic institution"),
      None,
      runId,
      Vector("synthetic-evidence")
    )
    val second = link.copy(sourceId = "source-two", researcherId = secondResearcherId)
    assert(cache.putLink(link).isInstanceOf[Written[?]])
    assert(cache.putLink(second).isInstanceOf[Written[?]])
    assert(cache.putLink(link).isInstanceOf[Unchanged[?]])
    assert(rejected(cache.putLink(link.copy(researcherId = secondResearcherId))))
    val found = StorageResult.value(cache.lookupByNormalizedName("synthetic example")).get
    assert(found.map(_.researcherId).toSet == Set(researcherId, secondResearcherId))
    val external = link.copy(entityType = "external:orcid", normalizedKey = "0000-0002-1825-0097")
    assert(cache.putLink(external).isInstanceOf[Written[?]])
    assert(
      StorageResult
        .value(cache.lookupByExternalId("orcid", "0000-0002-1825-0097"))
        .contains(Vector(external))
    )
  }

  test("query idempotency binds one query and optimistic revisions reject a stale writer") {
    val sessions: QuerySessionStore = new InMemoryQuerySessionStore()
    val first =
      StorageResult.value(sessions.createIfAbsent("synthetic-query-1", "synthetic-key")).get
    assert(first.revision == 0L)
    assert(first.expiresAtEpochSeconds.isEmpty)
    assert(sessions.createIfAbsent("synthetic-query-1", "synthetic-key").isInstanceOf[Unchanged[?]])
    assert(rejected(sessions.createIfAbsent("synthetic-query-2", "synthetic-key")))
    val updated = first.copy(state = "completed", revision = 1, payload = "synthetic-result")
    assert(sessions.update(updated, 0).isInstanceOf[Written[?]])
    assert(rejected(sessions.update(updated.copy(payload = "stale"), 0)))
    assert(StorageResult.value(sessions.lookupByIdempotencyKey("synthetic-key")).contains(updated))
  }

  test("artifact hashes and metric payloads are immutable, qualified, and window isolated") {
    val artifacts: ArtifactRegistry = new InMemoryArtifactRegistry()
    assert(
      artifacts
        .register("synthetic-artifact", "0001", "synthetic://one", "a" * 64)
        .isInstanceOf[Written[?]]
    )
    assert(
      artifacts
        .register("synthetic-artifact", "0001", "synthetic://one", "a" * 64)
        .isInstanceOf[Unchanged[?]]
    )
    assert(rejected(artifacts.register("synthetic-artifact", "0001", "synthetic://one", "b" * 64)))
    artifacts.register("synthetic-artifact", "0002", "synthetic://two", "b" * 64)
    assert(StorageResult.value(artifacts.latest("synthetic-artifact")).get.version == "0002")
    val store: ResearcherMetricStore = new InMemoryResearcherMetricStore()
    val qualification = """{"converged":false,"iterations":3,"p90Method":"approximate"}"""
    val record = ResearcherMetricRecord(
      researcherId,
      "all-years",
      policyVersion,
      runId,
      CoreJson.compact(metrics),
      qualification
    )
    assert(store.put(record).isInstanceOf[Written[?]])
    assert(store.put(record).isInstanceOf[Unchanged[?]])
    assert(rejected(store.put(record.copy(payloadJson = "{}"))))
    val laterMetrics = metrics.copy(context = context.copy(windowId = Some("2020-2026")))
    assert(
      store
        .put(record.copy(windowId = "2020-2026", payloadJson = CoreJson.compact(laterMetrics)))
        .isInstanceOf[Written[?]]
    )
    val rows = StorageResult
      .value(store.batchGet(Vector(researcherId -> "all-years", researcherId -> "2020-2026")))
      .get
    assert(rows.size == 2)
    assert(rows.forall(_.qualificationsJson == qualification))
    assert(rows.forall(_.runId == runId))
  }

  test("evidence fake preserves source provenance and refuses schema corruption") {
    val store: EvidenceBundleStore = new InMemoryEvidenceBundleStore()
    val item = EvidenceItem(
      "chunk:" + "f" * 64,
      SchemaVersions.domain,
      EvidenceType.WorkMetadata,
      Some("work:dblp:independent/synthetic/storage"),
      "synthetic://independent-storage",
      None,
      None,
      score = 0.0,
      text = Some("Synthetic evidence fixture."),
      provenance = provenance
    )
    val bundle = EvidenceBundle(
      "bundle:synthetic-storage",
      SchemaVersions.domain,
      "plan:" + "f" * 64,
      Vector(item),
      Vector(researcherId),
      Vector.empty,
      None,
      "Synthetic fixture, no observed evidence.",
      provenance
    )
    assert(store.put(bundle).isInstanceOf[Written[?]])
    assert(store.put(bundle).isInstanceOf[Unchanged[?]])
    assert(StorageResult.value(store.get(bundle.bundleId)).contains(bundle))
    assert(rejected(store.put(bundle.copy(schemaVersion = "unsupported.v99"))))
  }
}
