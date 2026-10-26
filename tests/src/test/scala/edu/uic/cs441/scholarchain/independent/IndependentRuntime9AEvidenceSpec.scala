package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite

/** Exercises public item lookup and its independent content binding, without database clients. */
class IndependentRuntime9AEvidenceSpec extends AnyFunSuite {
  import IndependentStorageFixtures.*
  import StorageResult.*
  private def bundle(id: String = "bundle:independent-runtime"): EvidenceBundle = {
    val item = EvidenceItem(
      "chunk:" + "f" * 64,
      SchemaVersions.domain,
      EvidenceType.WorkMetadata,
      Some("work:dblp:independent/synthetic/storage"),
      "synthetic://runtime-evidence",
      None,
      None,
      score = 0.0,
      text = Some("Synthetic source-backed title."),
      provenance = provenance
    )
    EvidenceBundle(
      id,
      SchemaVersions.domain,
      "query:independent-runtime",
      Vector(item),
      Vector(researcherId),
      Vector.empty,
      None,
      "Synthetic evidence only.",
      provenance
    )
  }

  test(
    "an evidence item ID resolves through its bundle, including an identical item shared by bundles"
  ) {
    val store = new IndexedEvidenceBundleStore(
      new InMemoryEvidenceBundleStore,
      new InMemoryObjectStore,
      "independent-evidence-index"
    )
    val first = bundle()
    assert(store.getItem(first.items.head.evidenceId) == Missing)
    assert(StorageResult.successful(store.put(first)))
    assert(store.getItem(first.items.head.evidenceId) == Found(first.items.head))
    assert(StorageResult.successful(store.put(first)))
    val second = first.copy(bundleId = "bundle:another-runtime", queryId = "query:another-runtime")
    assert(StorageResult.successful(store.put(second)))
    assert(store.getItem(first.items.head.evidenceId) == Found(first.items.head))
  }

  test("the same evidence item ID cannot be rebound to changed text in another bundle") {
    val store = new IndexedEvidenceBundleStore(
      new InMemoryEvidenceBundleStore,
      new InMemoryObjectStore,
      "independent-evidence-conflict"
    )
    val first = bundle()
    assert(StorageResult.successful(store.put(first)))
    val changed = first.copy(
      bundleId = "bundle:conflicting",
      items = first.items.map(_.copy(text = Some("Invented replacement.")))
    )
    assert(store.put(changed) == Rejected("evidence-item-id-conflict"))
    assert(store.getItem(first.items.head.evidenceId) == Found(first.items.head))
  }

  test("corrupt pointer bytes are rejected before any item can be returned") {
    val underlying = new InMemoryObjectStore
    var corrupt = false
    val objects = new ObjectStore {
      def put(
          k: String,
          b: Vector[Byte],
          t: String,
          m: Map[String, String]
      ): StorageResult[ObjectHead] = underlying.put(k, b, t, m)
      def head(k: String): StorageResult[ObjectHead] = underlying.head(k)
      def get(k: String): StorageResult[StoredObject] = underlying.get(k) match {
        case Found(value) if corrupt => Found(value.copy(bytes = value.bytes :+ 0.toByte))
        case value                   => value
      }
    }
    val store = new IndexedEvidenceBundleStore(
      new InMemoryEvidenceBundleStore,
      objects,
      "independent-evidence-corrupt"
    )
    val first = bundle()
    assert(StorageResult.successful(store.put(first)))
    corrupt = true
    assert(store.getItem(first.items.head.evidenceId) == Rejected("corrupt-evidence-item-pointer"))
  }

  test("indexed fake exposes the same item-ID lookup contract") {
    val store = new edu.uic.cs441.scholarchain.storage.fakes.InMemoryIndexedEvidenceBundleStore()
    val first = bundle()
    assert(StorageResult.successful(store.put(first)))
    assert(store.getItem(first.items.head.evidenceId) == Found(first.items.head))
  }
}
