package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*

/** Synthetic storage-contract examples; no identity, metric or source observation is real. */
object IndependentStorageFixtures {
  val runId = "run:00112233-4455-4677-8899-aabbccddeeff"
  val researcherId = "researcher:dblp:" + "a" * 64
  val secondResearcherId = "researcher:dblp:" + "b" * 64
  val policyVersion = "independent-storage-synthetic-v1"
  val provenance = Provenance(
    SchemaVersions.domain,
    SourceType.Dblp,
    "independent/synthetic/storage",
    None,
    "independent-synthetic-snapshot",
    None,
    None,
    runId,
    Vector("Synthetic independent test fixture; no observed researcher or source claim.")
  )
  val context = SparkRecordContext(
    SchemaVersions.sparkAnalytics,
    runId,
    Some("all-years"),
    SparkLineage(
      runId,
      provenance.datasetSnapshot,
      runId,
      "synthetic-er-v1",
      "c" * 64,
      Vector("work:dblp:independent/synthetic/storage"),
      Vector.empty
    )
  )
  val researcher = GraphNode(
    researcherId,
    SchemaVersions.domain,
    GraphNodeClass.Researcher,
    "Synthetic Example 0001",
    Vector(NamedText("orcid.0", "0000-0002-1825-0097")),
    provenance
  )

  // Two publications with coauthor counts 2 and 0: total=2, average=1, maximum=2.
  val metrics = ResearcherMetricsDetail(
    context,
    researcherId,
    policyVersion,
    2L,
    2L,
    2L,
    1.0,
    2L,
    Vector("work:dblp:independent/synthetic/storage"),
    1L,
    2L,
    "component:" + "d" * 64,
    None,
    Some(1)
  )

  def manifest(dataset: String, rows: Long, keys: Vector[String]): LoadManifest =
    LoadManifest(
      context.copy(windowId = None),
      "dynamodb",
      dataset,
      Vector("synthetic-export/" + dataset),
      "parquet",
      rows,
      keys,
      Vector("run_id"),
      "e" * 64,
      Vector("all-years"),
      "storage-engineer",
      Vector.empty
    )
}
