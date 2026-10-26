package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.apache.spark.sql.SparkSession
import org.scalatest.funsuite.AnyFunSuite

/** Actual Phase6 public producer/export -> bounded ObjectStore artifact -> runtime port. Temporary
  * synthetic direct inputs do not claim acquired datasets or Hadoop/ER execution.
  */
class IndependentRuntime9AArtifactPipelineSpec extends AnyFunSuite {
  test(
    "computed G1 source artifacts preserve exact metrics, edge support and iteration qualifications"
  ) {
    IndependentStorage7BSupport.temporary("independent-runtime-9a-artifact-") { root =>
      val source = root.resolve("computed-g1")
      try {
        IndependentEmbeddingG1ExportMain.main(Array(source.toString))
        val objects = new InMemoryObjectStore
        val published = Phase6RuntimeArtifacts.materialize(
          source,
          objects,
          "runtime/versions/independent-g1/snapshot.json"
        )
        assert(
          StorageResult.successful(published),
          s"Actual producer materialization failed: $published"
        )
        val pointer = StorageResult.value(published).get
        assert(pointer.sourceRunId == IndependentPhase6G1.sparkRunId)
        val store = new ObjectStoreRuntimeArtifactStore(objects, pointer)
        val page = StorageResult
          .value(
            store.rank(
              "all-years",
              RuntimeRankingMetric.DistinctCoauthorCount,
              RuntimePopulationFilter(),
              10
            )
          )
          .get
        assert(page.populationCount == 10 && page.matchedCount == 10 && !page.truncated)
        val byId = page.items.map(entry => entry.metric.researcherId -> entry.metric).toMap
        val a = IndependentPhase6G1.researcherId("A")
        val b = IndependentPhase6G1.researcherId("B")
        val h = IndependentPhase6G1.researcherId("H")
        // A occurs on w1,w2,w9; literal support counts are 2,1,1 coauthors.
        assert(byId(a).publicationCount == 3)
        assert(byId(a).distinctCoauthorCount == 2)
        assert(byId(a).totalCoauthorOccurrences == 4)
        assert(byId(a).weightedDegree == 4)
        assert(byId(a).maximumCoauthorsOnOnePaper == 2)
        assert(byId(a).averageCoauthorsPerPaper == 4.0 / 3.0)
        assert(
          page.items.take(3).map(_.metric.researcherId).toSet ==
            Set("C", "D", "F").map(IndependentPhase6G1.researcherId)
        )
        val top = StorageResult
          .value(
            store.rank(
              "all-years",
              RuntimeRankingMetric.DistinctCoauthorCount,
              RuntimePopulationFilter(),
              2
            )
          )
          .get
        assert(top.items.size == 2 && top.truncated && top.matchedCount == 10)
        val edgeId = StableIds
          .sparkCoauthorEdgeId(
            a,
            b,
            IndependentPhase6G1.windows.head,
            IndependentPhase6G1.graphPolicy
          )
          .toOption
          .get
        val support = StorageResult.value(store.edgeSupport(edgeId, "all-years")).get
        assert(support.edge.jointPublicationCount == 3)
        assert(
          support.support.map(_.workId).toSet ==
            Set("w1", "w2", "w9").map(IndependentPhase6G1.canonicalWorkId)
        )
        assert(support.support.flatMap(_.year).toSet == Set(2015, 2016))
        val bridge = StorageResult.value(store.bridgeMetrics(h, "all-years")).get
        assert(!bridge.membership.converged && bridge.membership.iterations == 3)
        assert(bridge.distinctCoauthorCount == 1)
        val summary = StorageResult
          .value(store.communitySummary(bridge.membership.communityId, "all-years"))
          .get
        assert(!summary.converged && summary.iterations == 3)
        assert(
          store.rank(
            "all-years",
            RuntimeRankingMetric.DistinctCoauthorCount,
            RuntimePopulationFilter(topicIds = Vector("distributed-systems")),
            10
          ) ==
            StorageResult.Rejected("unsupported-authoritative-filter-metadata")
        )
        assert(
          store.rank(
            "unknown-window",
            RuntimeRankingMetric.DistinctCoauthorCount,
            RuntimePopulationFilter(),
            10
          ) == StorageResult.Rejected("unsupported-runtime-window")
        )
        assert(
          store.rank(
            "all-years",
            RuntimeRankingMetric.DistinctCoauthorCount,
            RuntimePopulationFilter(metricScope = "publication-subgraph"),
            10
          ) ==
            StorageResult.Rejected("unsupported-filtered-metric-scope")
        )
        val change = StorageResult.value(store.temporalChange(a, "2015-2017", "2018-2021")).get
        assert(change.change.fromPresent && !change.change.toPresent)
        assert(change.change.deltaDistinctCoauthors.isEmpty)
        assert(change.fromMembership.nonEmpty && change.toMembership.isEmpty)
        val tampered = new ObjectStoreRuntimeArtifactStore(objects, pointer.copy(sha256 = "0" * 64))
        assert(
          tampered.rank(
            "all-years",
            RuntimeRankingMetric.DistinctCoauthorCount,
            RuntimePopulationFilter(),
            10
          ) == StorageResult.Rejected("runtime-artifact-content-mismatch")
        )
        assert(
          Phase6RuntimeArtifacts
            .materialize(
              source,
              new InMemoryObjectStore,
              "runtime/versions/too-small/snapshot.json",
              RuntimeArtifactConfig(maxRows = 1)
            )
            .isInstanceOf[StorageResult.Rejected[?]]
        )
      } finally {
        SparkSession.clearActiveSession()
        SparkSession.clearDefaultSession()
      }
    }
  }
}
