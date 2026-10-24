package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.write
import java.nio.charset.StandardCharsets.UTF_8

class Embedding8BRepairSpec extends AnyFunSuite {
  private val lineage = SparkLineage(
    "synthetic-hadoop",
    "synthetic-snapshot",
    "synthetic-er",
    "policy-v1",
    "hash",
    Vector.empty,
    Vector.empty
  )
  private val context =
    SparkRecordContext("synthetic-schema", "synthetic-run", Some("synthetic-window"), lineage)
  private val model = EmbeddingModel("amazon.titan-embed-text-v2:0", "fixture-v1", 256)
  private val config = LocalEmbeddingConfig(model, "synthetic-text", "rag", "template-v1", 1000, 0)
  private def node(id: String, kind: GraphNodeClass, label: String, table: String, count: Long) = {
    val provenance = Provenance(
      "synthetic-schema",
      SourceType.OpenAlex,
      id,
      None,
      "synthetic-snapshot",
      None,
      None,
      context.runId,
      Vector("Synthetic fixture only.")
    )
    EmbeddingSourceNode(
      GraphNode(id, "synthetic-schema", kind, label, Vector.empty, provenance),
      table,
      count,
      "synthetic-window",
      Vector(
        SummarySourceRef(table, id, "label"),
        SummarySourceRef("run-metadata.json", table, "rowCount")
      )
    )
  }
  private val batch = EmbeddingSourceBatch(
    context,
    Vector.empty,
    Vector(
      node("synthetic-topic", GraphNodeClass.Topic, "Synthetic optics", "nodes/type=topic", 17),
      node(
        "synthetic-institution",
        GraphNodeClass.Institution,
        "Synthetic campus",
        "nodes/type=institution",
        23
      )
    ),
    "{}",
    40,
    Map("nodes/type=topic" -> 17L, "nodes/type=institution" -> 23L),
    Map.empty
  )
  private val tables = DynamoTables(
    "synthetic-runs",
    "synthetic-links",
    "synthetic-sessions",
    "synthetic-evidence",
    "synthetic-artifacts",
    "synthetic-metrics",
    "synthetic-idempotency"
  )
  private val live = LiveEmbeddingConfig(
    "synthetic-env",
    "synthetic-region",
    "synthetic-profile",
    model,
    config.textBucket,
    config.textPrefix,
    "synthetic-vectors",
    tables,
    EmbeddingContracts.indexes,
    "cosine",
    10,
    2,
    2,
    20,
    5.0,
    .01,
    .01,
    .10
  )

  test(
    "actual topic and institution source branch renders exact source fields, table totals, filters and fifth index"
  ) {
    val documents = EmbeddingIngestMain.renderSource(batch, config).fold(fail(_), identity)
    assert(documents.size == 2)
    documents.foreach { document =>
      val source = batch.nodes.find(_.node.nodeId == document.entityId).get
      val kind = source.node.nodeClass
      val expected =
        "Topic and institution summary\nlabel: " + source.node.label + "\nnodeClass: " + kind.wire +
          "\ntableTotalNodes: " + source.tableRowCount
      assert(document.text.getBytes(UTF_8).toVector == expected.getBytes(UTF_8).toVector)
      assert(
        document.sourceReferences.toSet == source.sourceReferences.toSet +
          SummarySourceRef(source.logicalDataset, source.node.nodeId, "nodeClass")
      )
      assert(
        !document.text.contains("perNodeCount") && !document.text.contains("topicInstitutionCount")
      )
      val identityName = if (kind == GraphNodeClass.Topic) "topicId" else "institutionId"
      assert(
        document.identityFields == Map(
          identityName -> document.entityId,
          "sourceDataset" -> "OPENALEX"
        )
      )
      val item = EmbeddingManifests.item(document, model, config.ingest)
      assert(
        item.indexName == "topic-institution-summary-v1" && EmbeddingValidation
          .workItem(item)
          .isEmpty
      )
    }
  }
  test(
    "render-only real model manifest is accepted by pure live preflight without embedding or state"
  ) {
    val manifest = EmbeddingManifestMain.render(batch, config).fold(fail(_), identity)
    assert(manifest.items.size == 2 && manifest.items.forall(_.embeddingModel == model))
    val ct = write(live); val mt = write(manifest);
    val gate = "Synthetic pure guard gate; not actual approval."
    val approval = LiveEmbeddingApproval(
      true,
      live.environment,
      "synthetic-ingest",
      StableIds.sha256Hex(ct),
      StableIds.sha256Hex(mt),
      "synthetic-gate",
      StableIds.sha256Hex(gate),
      10,
      2,
      20,
      5.0,
      true,
      true,
      2000
    )
    val plan =
      LiveEmbeddingIngestMain.preflight(ct, mt, write(approval), gate, "synthetic-ingest", 1000)
    assert(plan.isRight && plan.toOption.get.maxEmbeddingRequests == 4)
    assert(EmbeddingManifestMain.run(Seq.empty) == Left("invalid-render-arguments"))
  }
  test("pure live report contains configured model, per-index counts and all rejection evidence") {
    val manifest = EmbeddingManifestMain.render(batch, config).fold(fail(_), identity)
    val approval = LiveEmbeddingApproval(
      false,
      live.environment,
      "synthetic",
      "c",
      "m",
      "g",
      "h",
      10,
      2,
      20,
      5.0,
      false,
      false,
      2000
    )
    val plan = LiveEmbeddingPlan(live, manifest, approval, 4, BigDecimal(".16"))
    val result = EmbeddingIngestReport(
      1,
      0,
      0,
      1,
      1,
      Map("topic-institution-summary-v1" -> 1),
      3,
      1000000,
      Vector(VectorReject("synthetic-reject", "embedding-provider-rejected")),
      Some("s3://synthetic-text/rejected/versions/v/report.json")
    )
    val report = LiveEmbeddingIngestMain.report(plan, result, "synthetic", "c", "m", "a")
    assert(report("model") == upickle.default.writeJs(model))
    assert(
      report("embeddingModelId").str == model.modelId && report(
        "embeddingModelVersion"
      ).str == model.version
    )
    assert(
      report("dimension").num == 256 && report("perIndex")("topic-institution-summary-v1").num == 1
    )
    assert(report("rejections")(0)("key").str == "synthetic-reject")
    assert(report("rejections")(0)("reason").str == "embedding-provider-rejected")
    assert(
      report("rejectedReportUri").str == result.rejectedReportUri.get && !report(
        "billingGuarantee"
      ).bool
    )
  }
}
