package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.charset.StandardCharsets.UTF_8

/** Session-2 plan P26 (a): the render path and the manifest limits hold about 10,000 items.
  *
  * The synthetic summaries copy the shape of the Phase 6 producer (`Phase6FGJobs.semanticSummaries`
  * in modules/spark): the same four summary types, the same text templates, the same source
  * reference tables and fields (6, 4, 3 and 2 references per type), and identifiers built with the
  * same `StableIds` functions. They are not real data: the numbers, names and titles are invented,
  * so the byte figures below are an estimate of the real manifest, not a measurement of it. The
  * human's render-only run on the real export is the authoritative check.
  */
class Phase15VectorScaleSpec extends AnyFunSuite {
  private val model = VoyageDefaults.Model
  // Realistic bucket-name length; the account-ID part is built at run time (no ID literal).
  private val syntheticBucket = "scholarchain-course-rag-" + "0" * 12 + "-us-east-2"
  private val policy = "phase6-graph-v1"
  private val window = "all-years"
  private val runId = "run-20261117-stage-a-s"
  private val lineage = SparkLineage(
    "hadoop-prep-run-20261117-s",
    "snapshot-20261117-s",
    "er-run-20261117-s",
    "phase5-er-policy-v1",
    "a" * 64,
    Vector.empty,
    Vector.empty
  )
  private val context = SparkRecordContext("scholarchain.phase6.v1", runId, Some(window), lineage)

  private def hex(kind: String, n: Int) = StableIds.sha256Hex(kind + "\n" + n)
  private def ref(table: String, key: String, field: String) =
    SummarySourceRef(table, s"$window/$key", field)

  /** One summary in the Phase 6 producer's shape. `titleChars` sets the paper title length. */
  private def summary(kind: String, n: Int, titleChars: Int): SemanticSummary = {
    val (entity, text, refs) = kind match {
      case "researcher-profile" =>
        val id = s"researcher:dblp:${hex("researcher", n)}"
        val fields = Vector(
          "publicationCount",
          "distinctCoauthorCount",
          "totalCoauthorOccurrences",
          "averageCoauthorsPerPaper",
          "maximumCoauthorsOnOnePaper",
          "weightedDegree"
        )
        (
          id,
          s"Publication count: ${n % 97 + 1}. Distinct coauthors: ${n % 53 + 2}. Coauthor " +
            s"occurrences: ${n % 211 + 3}. Average coauthors per paper: ${41.0 / 12}. " +
            s"Maximum coauthors on one paper: ${n % 17 + 2}. Weighted degree: ${n % 389 + 5}.",
          fields.map(f => ref("metrics/type=researcher_collaboration", id, f))
        )
      case "community" =>
        val id = s"community:${hex("community", n)}"
        (
          id,
          s"Community size: ${n % 640 + 2}. Label propagation iterations: ${n % 9 + 1}. " +
            s"Changed labels in final iteration: 0. Converged: true.",
          Vector("size", "iterations", "finalChangedCount", "converged")
            .map(f => ref("metrics/type=community_summaries", id, f))
        )
      case "collaboration-path" =>
        val id = s"path-evidence:${hex("path", n)}"
        (
          id,
          s"Selected collaboration path status: found. Hop count: ${n % 4 + 1}. " +
            "Maximum search hops: 4.",
          Vector("status", "hopCount", "maxHops").map(f => ref("path-evidence", id, f))
        )
      case _ =>
        val id = f"work:doi:10.1145/${3_000_000 + n}%d.${n % 9000 + 1000}%d"
        val title = ("Scalable temporal collaboration graph analysis " * 20).take(titleChars)
        (
          id,
          s"Paper title: $title. Publication year: ${2000 + n % 24}.",
          Vector(
            SummarySourceRef("nodes/type=work_sources", id, "title"),
            SummarySourceRef("nodes/type=work_sources", id, "year")
          )
        )
    }
    val summaryId =
      StableIds
        .sparkSemanticSummaryId(entity, policy, window, kind, text)
        .fold(e => fail(e.toString), identity)
    SemanticSummary(context, summaryId, kind, entity, policy, text, refs, Vector.empty)
  }

  private def node(nodeClass: GraphNodeClass, n: Int): EmbeddingSourceNode = {
    val (id, dataset) =
      if (nodeClass == GraphNodeClass.Topic) (s"topic:openalex:T${10000 + n}", "nodes/type=topic")
      else (s"institution:ror:0${hex("ror", n).take(8)}", "nodes/type=institution")
    EmbeddingSourceNode(
      GraphNode(
        id,
        SchemaVersions.domain,
        nodeClass,
        s"Synthetic ${nodeClass.wire} label $n",
        Vector.empty,
        Provenance(
          SchemaVersions.domain,
          SourceType.OpenAlex,
          s"synthetic-$n",
          None,
          "snapshot-20261117-s",
          None,
          None,
          runId,
          Vector.empty
        )
      ),
      dataset,
      4L,
      window,
      Vector(
        SummarySourceRef(dataset, id, "label"),
        SummarySourceRef("run-metadata.json", dataset, "rowCount")
      )
    )
  }

  private val kinds = Vector("collaboration-path", "community", "paper", "researcher-profile")

  /** `perType` summaries of each of the four types (round robin, like the selection), plus 2 topic
    * and 2 institution nodes, as in Session 1 (4 nodes in total).
    */
  private def batch(perType: Int, titleChars: Int = 90): EmbeddingSourceBatch = {
    val summaries =
      (0 until perType).flatMap(n => kinds.map(k => summary(k, n, titleChars))).toVector
    val identities = summaries.map { s =>
      s.summaryId -> (s.summaryType match {
        case "researcher-profile" => Map("researcherId" -> s.entityId)
        case "community"          => Map("communityId" -> s.entityId)
        case _                    => Map.empty[String, String]
      })
    }.toMap
    EmbeddingSourceBatch(
      context,
      summaries,
      Vector(
        node(GraphNodeClass.Topic, 1),
        node(GraphNodeClass.Topic, 2),
        node(GraphNodeClass.Institution, 1),
        node(GraphNodeClass.Institution, 2)
      ),
      "{}",
      summaries.size.toLong + 4,
      Map("semantic-summaries" -> summaries.size.toLong),
      identities
    )
  }

  /** The 14C render-config template values (phase-08 template, Session 1 template version), with
    * the P26 selection caps. The bucket name has a realistic length.
    */
  private val manifestBytes32MiB = 32 * 1024 * 1024
  private def config(maxSummaries: Int, maxManifestBytes: Int = manifestBytes32MiB) =
    LocalEmbeddingConfig(
      model,
      syntheticBucket,
      "graph/rag",
      "phase14c-v1",
      1000,
      100,
      maxSummaries = maxSummaries,
      maxTopicNodes = 10,
      maxInstitutionNodes = 10,
      maxScannedRows = 200000,
      maxManifestItems = 10000,
      maxManifestBytes = maxManifestBytes
    )

  private def liveConfig(maxManifestBytes: Int) = LiveEmbeddingConfig(
    "fixture-env",
    "us-east-2",
    "fixture-profile",
    model,
    syntheticBucket,
    "graph/rag",
    "fixture-vectors",
    DynamoTables("runs", "links", "sessions", "evidence", "artifacts", "metrics", "by-idempotency"),
    EmbeddingContracts.indexes,
    "cosine",
    10000,
    2,
    2,
    20000,
    0.25,
    0.00001,
    0.000001,
    0.02,
    maxManifestBytes = maxManifestBytes
  )

  private def bytes(manifest: EmbeddingManifest) =
    upickle.default.write(manifest).getBytes(UTF_8).length.toLong

  test("P26a: 9,996 summaries plus 4 nodes render to exactly 10,000 items within every limit") {
    val manifest = EmbeddingManifestMain.render(batch(2499), config(9996)).fold(fail(_), identity)
    assert(manifest.items.size == 10000)
    val perType = manifest.items.groupMapReduce(_.document.documentType)(_ => 1)(_ + _)
    assert(
      perType == Map(
        "collaboration-path" -> 2499,
        "community" -> 2499,
        "paper" -> 2499,
        "researcher-profile" -> 2499,
        "topic-institution-summary" -> 4
      )
    )
    // One chunk per summary at the template's 1,000-character chunk limit.
    assert(manifest.items.forall(_.document.chunkCount == 1))
    val total = bytes(manifest)
    val perItem = manifest.items.groupMapReduce(_.document.documentType)(i =>
      upickle.default.write(i).getBytes(UTF_8).length.toLong
    )(_ + _)
    val textBytes = manifest.items.map(_.document.text.getBytes(UTF_8).length.toLong)
    info(s"manifestBytes=$total limit=$manifestBytes32MiB averageItemBytes=${total / 10000}")
    perItem.toVector.sorted.foreach((k, v) =>
      info(s"type=$k items=${perType(k)} averageItemBytes=${v / perType(k)}")
    )
    info(s"textBytes total=${textBytes.sum} max=${textBytes.max} average=${textBytes.sum / 10000}")
    // About 20.5 MB: above the 16 MiB default, within the 32 MiB the human sets for P26.
    assert(total > 16L * 1024 * 1024 && total <= manifestBytes32MiB)
    // The render report's size evidence states the same figures.
    val evidence =
      EmbeddingManifestMain.sizeEvidence(manifest, upickle.default.write(manifest), config(9996))
    assert(evidence("manifestBytes").str == total.toString)
    assert(evidence("maxManifestBytes").str == manifestBytes32MiB.toString)
    assert(evidence("maxManifestItems").str == "10000")
    assert(evidence("textBytesTotal").str == textBytes.sum.toString)
    assert(evidence("textBytesMax").str == textBytes.max.toString)
    // The live config accepts 32 MiB (ceiling 64 MiB), and its parser takes the 10,000 items.
    val live = liveConfig(manifestBytes32MiB)
    assert(
      StorageResult
        .value(EmbeddingManifests.parse(upickle.default.write(manifest), live.ingest))
        .exists(_.items.size == 10000)
    )
  }

  test("P26a: the 16 MiB default refuses the 10,000-item manifest with the typed byte code") {
    assert(
      EmbeddingManifestMain.render(batch(2499), config(9996, 16 * 1024 * 1024)) ==
        Left("manifest-byte-limit")
    )
  }

  test("P26a: live maxManifestBytes accepts up to the 64 MiB ceiling and refuses above it") {
    assert(LiveEmbeddingConfig.MaxManifestBytesCeiling == 64 * 1024 * 1024)
    assert(liveConfig(64 * 1024 * 1024).maxManifestBytes == 64 * 1024 * 1024)
    intercept[IllegalArgumentException](liveConfig(64 * 1024 * 1024 + 1))
    // An absent key keeps the 16 MiB default.
    val old = upickle.default.writeJs(liveConfig(manifestBytes32MiB))
    old.obj.remove("maxManifestBytes")
    assert(upickle.default.read[LiveEmbeddingConfig](old.render()).maxManifestBytes == 16777216)
  }

  test("P26a: one item past maxManifestItems is refused with the typed code, not truncated") {
    // 2,500 per type = 10,000 summaries + 4 nodes = 10,004 items > 10,000.
    assert(
      EmbeddingManifestMain.render(batch(2500), config(10000)) == Left(
        "render-document-count-bound"
      )
    )
  }

  test("P26a: worst-case 900-character paper titles still render one chunk per paper") {
    val manifest =
      EmbeddingManifestMain
        .render(batch(250, titleChars = 900), config(1000))
        .fold(fail(_), identity)
    val papers = manifest.items.filter(_.document.documentType == "paper")
    assert(papers.size == 250 && papers.forall(_.document.chunkCount == 1))
    val paperBytes = papers.map(i => upickle.default.write(i).getBytes(UTF_8).length.toLong)
    info(
      s"worst-case paper item bytes average=${paperBytes.sum / papers.size} max=${paperBytes.max}"
    )
  }
}
