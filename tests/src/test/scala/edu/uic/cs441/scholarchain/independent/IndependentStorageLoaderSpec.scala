package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import edu.uic.cs441.scholarchain.storage.fakes.{
  InMemoryEntityLinkCache,
  InMemoryResearcherMetricStore
}
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets.UTF_8

class IndependentStorageLoaderSpec extends AnyFunSuite {
  import IndependentStorageFixtures.*
  import StorageResult.*

  private val qualification =
    """{"converged":false,"iterations":3,"effectiveDiameterP90Method":"approximate"}"""

  // Independently precomputed SHA-256 vectors for the checked-in synthetic JSON, using Python's
  // hashlib and the documented fixed-shard format. No producer or storage hash helper is called.
  private val hashes = Map(
    "researcher" -> "a6d8e0707f0c48e1d2c9bbcd9072b457ce1f18cb36a31864bdd9b62e8cd3e4c7",
    "researcher-invalid" -> "65fcfb3d346787a6c1f50cef3c35bc8b38cc4dd57516b690a1327f5981a687b5",
    "metrics" -> "db15762550d952d1c87ffe0e3d3341ec84cef45b6363e0d63ce1ee0fce50d55d",
    "metrics-conflict" -> "463dc347d9bfeaf7aae40828ee2b3c18a7e32af760473e364c3442cccdcd4aa7"
  )

  private def fixture(name: String): ujson.Obj = {
    val stream = getClass.getResourceAsStream(s"/storage/$name.json")
    require(stream != null)
    try ujson.read(new String(stream.readAllBytes(), UTF_8)).asInstanceOf[ujson.Obj]
    finally stream.close()
  }

  private def source(dataset: String, fixtureName: String): LoadManifest =
    manifest(dataset, 1, Vector(if (dataset.startsWith("nodes/")) "nodeId" else "researcherId"))
      .copy(
        targetStore = if (dataset.startsWith("nodes/")) "s3" else "dynamodb",
        sortedRowsSha256 = hashes(fixtureName)
      )

  private final class SyntheticReader(
      rows: Map[String, String],
      sourceQualification: StorageResult[String] = Found(qualification)
  ) extends ManifestRowReader {
    var opened = 0
    var closed = 0
    def qualifications(sourceRunId: String): StorageResult[String] = {
      assert(sourceRunId == runId)
      sourceQualification
    }
    def open(manifest: LoadManifest): StorageResult[CloseableRowIterator] = {
      opened += 1
      val values = Vector(fixture(rows(manifest.logicalDataset))).iterator
      Found(new CloseableRowIterator {
        private var isClosed = false
        def hasNext: Boolean = values.hasNext
        def next(): ujson.Obj = values.next()
        def close(): Unit = if (!isClosed) { isClosed = true; closed += 1 }
      })
    }
  }

  test(
    "manifest reload loads one canonical metric copy with exact IDs, lineage and qualifications"
  ) {
    val rows = Map(
      "nodes/type=researcher" -> "researcher",
      "metrics/type=researcher_collaboration" -> "metrics",
      "metrics/type=kcore" -> "metrics"
    )
    val reader = new SyntheticReader(rows)
    val links = new InMemoryEntityLinkCache()
    val store = new InMemoryResearcherMetricStore()
    val loader = new Phase6CacheLoader(links, store, reader, CacheLoaderConfig(sortChunkRows = 1))
    val manifests = rows.toVector.sortBy(_._1).map((dataset, name) => source(dataset, name))
    val first = loader.load(manifests)
    assert(first == Written(CacheLoadReport(3, 0, 0, 3)), first.toString)
    val candidates = StorageResult.value(links.lookupByNormalizedName("Synthetic Example 0001")).get
    assert(candidates.map(_.researcherId) == Vector(researcherId))
    assert(candidates.head.confidence.isEmpty)
    assert(candidates.head.runId == runId)
    val external = StorageResult.value(links.lookupByExternalId("orcid", "0000-0002-1825-0097")).get
    assert(external.map(_.researcherId) == Vector(researcherId))
    val record = StorageResult.value(store.get(researcherId, "all-years")).get
    val value = CoreJson.parse[ResearcherMetricsDetail](record.payloadJson).toOption.get
    assert(value.researcherId == researcherId)
    assert(value.publicationCount == 4 && value.totalCoauthorOccurrences == 2)
    assert(value.averageCoauthorsPerPaper == 0.5)
    assert(value.context.lineage == context.lineage)
    assert(record.metricVersion == policyVersion && record.runId == runId)
    assert(ujson.read(record.qualificationsJson)("sourceRun") == ujson.read(qualification))
    assert(loader.load(manifests) == Unchanged(CacheLoadReport(0, 3, 0, 3)))
    assert(reader.opened == 6 && reader.closed == 6)
  }

  test("conflicting collaboration and kcore copies reject before publishing any cache row") {
    val rows = Map(
      "nodes/type=researcher" -> "researcher",
      "metrics/type=researcher_collaboration" -> "metrics",
      "metrics/type=kcore" -> "metrics-conflict"
    )
    val reader = new SyntheticReader(rows)
    val links = new InMemoryEntityLinkCache()
    val store = new InMemoryResearcherMetricStore()
    val result = new Phase6CacheLoader(links, store, reader)
      .load(rows.toVector.map((dataset, name) => source(dataset, name)))
    assert(result == Rejected("conflicting-duplicate-metric"), result.toString)
    assert(store.get(researcherId, "all-years") == Missing)
    assert(links.lookupByNormalizedName("Synthetic Example 0001") == Found(Vector.empty))
    assert(reader.opened == reader.closed)
  }

  test("count and content-hash mismatches reject the manifest and always close its iterator") {
    val dataset = "nodes/type=researcher"
    Vector(
      source(dataset, "researcher").copy(rowCount = 2),
      source(dataset, "researcher").copy(sortedRowsSha256 = "0" * 64)
    ).foreach { bad =>
      val reader = new SyntheticReader(Map(dataset -> "researcher"))
      val links = new InMemoryEntityLinkCache()
      val result =
        new Phase6CacheLoader(links, new InMemoryResearcherMetricStore(), reader).load(Vector(bad))
      assert(!StorageResult.successful(result))
      assert(reader.opened == 1 && reader.closed == 1)
      assert(links.lookupByNormalizedName("Synthetic Example 0001") == Found(Vector.empty))
    }
  }

  test("a hash-valid unsupported researcher schema is rejected before any candidate is cached") {
    val dataset = "nodes/type=researcher"
    val reader = new SyntheticReader(Map(dataset -> "researcher-invalid"))
    val links = new InMemoryEntityLinkCache()
    val result = new Phase6CacheLoader(links, new InMemoryResearcherMetricStore(), reader)
      .load(Vector(source(dataset, "researcher-invalid")))
    assert(result == Rejected("invalid-researcher-node"), result.toString)
    assert(links.lookupByNormalizedName("Synthetic Example 0001") == Found(Vector.empty))
    assert(reader.opened == reader.closed)
  }

  test("missing source qualification metadata and unsupported manifest versions refuse loading") {
    val dataset = "nodes/type=researcher"
    val absent = new SyntheticReader(Map(dataset -> "researcher"), Missing)
    val missingResult = new Phase6CacheLoader(
      new InMemoryEntityLinkCache(),
      new InMemoryResearcherMetricStore(),
      absent
    ).load(Vector(source(dataset, "researcher")))
    assert(missingResult == Rejected("source-unavailable"))
    assert(absent.opened == 0)
    val reader = new SyntheticReader(Map(dataset -> "researcher"))
    val invalid =
      source(dataset, "researcher").copy(context = context.copy(schemaVersion = "unknown.v99"))
    assert(
      new Phase6CacheLoader(
        new InMemoryEntityLinkCache(),
        new InMemoryResearcherMetricStore(),
        reader
      )
        .load(Vector(invalid)) == Rejected("invalid-load-manifest")
    )
    assert(reader.opened == 0)
  }
}
