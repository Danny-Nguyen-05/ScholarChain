package edu.uic.cs441.scholarchain.storage

import java.nio.file.{Files, Path}
import org.scalatest.funsuite.AnyFunSuite
import StorageResult.*

/** Opt-in: loads a real completed Phase 6 export. Set `SCHOLARCHAIN_LOCAL_EXPORT_DIR` to the Spark
  * export root of the size-S run (`.../p6/size-S/run:ba7402d1-.../spark`); without it every test is
  * canceled. It reads local files only. The expected counts are those of that run.
  */
class LocalExportRealExportSpec extends AnyFunSuite {
  private val dir: Option[Path] =
    sys.env.get("SCHOLARCHAIN_LOCAL_EXPORT_DIR").map(Path.of(_)).filter(Files.isDirectory(_))

  test("the Phase 15 size-S export loads with the exported counts") {
    assume(dir.nonEmpty, "SCHOLARCHAIN_LOCAL_EXPORT_DIR is not set to an export directory")
    val s =
      LocalExportStores.load(dir.get, LocalExportLimits()).fold(e => fail(e.toString), identity)
    info(s"loadMillis=${s.loadMillis}")
    assert(s.runId == "run:ba7402d1-959a-4277-8c6e-e92878a38afa")
    assert(
      s.counts.nodesByClass == Map(
        "RESEARCHER" -> 21819L,
        "WORK" -> 10578L,
        "AUTHOR_MENTION" -> 45591L,
        "VENUE" -> 112L,
        "INSTITUTION" -> 1L,
        "TOPIC" -> 3L
      )
    )
    assert(
      s.counts.edgesByType == Map(
        "AUTHORED" -> 44083L,
        "PUBLISHED_IN" -> 10579L,
        "RESOLVES_TO" -> 45587L,
        "HAS_TOPIC" -> 3L,
        "COAUTHORED_WITH" -> 228715L
      )
    )
    assert(
      s.counts.coauthorEdgesByWindow == Map(
        "all-years" -> 81181L,
        "since-2015" -> 62785L,
        "2020-2026" -> 45020L,
        "2015-2019" -> 19326L,
        "2010-2014" -> 11795L,
        "through-2009" -> 8608L
      )
    )
    assert(s.counts.coauthorSupportRows == 269753L && s.counts.cacheRejected == 0L)
    assert(s.provenance.tables.forall(_.hashVerified))
    val page = StorageResult
      .value(
        s.runtimeArtifacts.rank(
          "all-years",
          edu.uic.cs441.scholarchain.core.RuntimeRankingMetric.DistinctCoauthorCount,
          edu.uic.cs441.scholarchain.core.RuntimePopulationFilter(),
          5
        )
      )
      .get
    // The ranked population is the researchers that have a metric row in the window.
    info(s"all-years population=${page.populationCount}")
    assert(page.populationCount > 0L && page.populationCount <= 21819L && page.items.size == 5)
    val top = page.items.head.metric.researcherId
    assert(s.graphReader.node(top).isInstanceOf[Found[?]])
    assert(s.metrics.get(top, "all-years").isInstanceOf[Found[?]])
    assert(
      StorageResult
        .value(
          s.graphReader.directedEdges(top, "all-years", EdgeDirection.Both, Set.empty, 100, None)
        )
        .exists(_.items.nonEmpty)
    )
  }
}
