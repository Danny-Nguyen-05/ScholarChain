package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import upickle.default.{ReadWriter, read, write}
import scala.util.control.NonFatal

/** Explicit local configuration. The fake model ID must describe the fake, not claim Titan output.
  * Bounds govern selected rows and local ingestion; no SDK client or credentials exist here.
  */
final case class LocalEmbeddingConfig(
    model: EmbeddingModel,
    textBucket: String,
    textPrefix: String,
    templateVersion: String,
    chunkMaxCharacters: Int,
    chunkOverlapCharacters: Int,
    schemaVersion: String = "scholarchain.embedding-local.v1",
    chunkMaxCount: Int = 1000,
    maxDocumentCharacters: Int = 1000000,
    maxSummaries: Int = 100,
    maxTopicNodes: Int = 10,
    maxInstitutionNodes: Int = 10,
    maxScannedRows: Long = 200000,
    maxManifestItems: Int = 10000,
    maxManifestBytes: Int = 16 * 1024 * 1024,
    maxTextBytes: Int = 1024 * 1024,
    batchSize: Int = 100
) derives ReadWriter {
  require(schemaVersion == "scholarchain.embedding-local.v1")
  require(EmbeddingValidation.model(model).isEmpty)
  def rendering: RenderingConfig = RenderingConfig(
    templateVersion,
    ChunkPolicy(chunkMaxCharacters, chunkOverlapCharacters, chunkMaxCount),
    maxDocumentCharacters
  )
  def ingest: EmbeddingIngestConfig = EmbeddingIngestConfig(
    textBucket,
    textPrefix,
    model.dimension,
    maxManifestItems = maxManifestItems,
    maxManifestBytes = maxManifestBytes,
    maxTextBytes = maxTextBytes,
    batchSize = batchSize
  )
  def selection: EmbeddingSourceSelection =
    EmbeddingSourceSelection(maxSummaries, maxTopicNodes, maxInstitutionNodes, maxScannedRows)
}

/** Local-only executable. It reads an actual completed Phase 6 export and its declared work
  * manifest, renders bounded source-backed documents, then persists fake ports for process replay.
  */
object EmbeddingIngestMain {
  private val requiredFlags = Set(
    "--export",
    "--work-manifest",
    "--config",
    "--state",
    "--report",
    "--manifest-output",
    "--run-id"
  )
  private def canonical(value: ujson.Value): ujson.Value = value match {
    case o: ujson.Obj =>
      ujson.Obj.from(o.obj.toVector.sortBy(_._1).map((k, v) => k -> canonical(v)))
    case a: ujson.Arr => ujson.Arr.from(a.arr.map(canonical))
    case other        => other
  }
  private def output(path: Path, content: String): Unit = {
    Option(path.toAbsolutePath.getParent).foreach(Files.createDirectories(_))
    Files.writeString(path, content, UTF_8)
  }
  private def value[A](result: StorageResult[A]): Either[String, A] = result match {
    case StorageResult.Rejected(code) => Left(code)
    case other => StorageResult.value(other).toRight("local-port-unavailable")
  }
  private def parse(args: Seq[String]): Either[String, Map[String, String]] = {
    if (args.size != requiredFlags.size * 2 || args.grouped(2).exists(_.size != 2))
      Left("invalid-local-arguments")
    else {
      val pairs = args.grouped(2).map(p => p(0) -> p(1)).toVector
      if (
        pairs.map(_._1).toSet != requiredFlags || pairs.map(_._1).distinct.size != pairs.size ||
        pairs.exists(_._2.trim.isEmpty)
      ) Left("invalid-local-arguments")
      else Right(pairs.toMap)
    }
  }
  def renderSource(
      batch: EmbeddingSourceBatch,
      config: LocalEmbeddingConfig
  ): Either[String, Vector[EmbeddingDocument]] = {
    val renderer = new DocumentRenderer(config.rendering)
    val summaries = batch.summaries.map(summary =>
      renderer.fromSummary(
        summary,
        identityFields = batch.identityFieldsBySummaryId.getOrElse(summary.summaryId, Map.empty)
      )
    )
    val nodes = batch.nodes.map { source =>
      val node = source.node
      val identityName = node.nodeClass match {
        case GraphNodeClass.Topic       => "topicId"
        case GraphNodeClass.Institution => "institutionId"
        case _                          => ""
      }
      if (identityName.isEmpty) Left("unsupported-context-node")
      else {
        val refs = source.sourceReferences
        if (refs.isEmpty) Left("missing-context-node-reference")
        else {
          val labelRef = refs.find(_.field == "label").getOrElse(refs.head)
          val countRef = refs.find(_.field == "rowCount").getOrElse(refs.last)
          val input = RenderInput(
            "topic-institution-summary",
            node.nodeId,
            source.windowId,
            batch.context.runId,
            Vector(
              SourceField("label", node.label, labelRef),
              SourceField(
                "nodeClass",
                node.nodeClass.wire,
                SummarySourceRef(source.logicalDataset, node.nodeId, "nodeClass")
              ),
              SourceField("tableTotalNodes", source.tableRowCount.toString, countRef)
            ),
            Map(identityName -> node.nodeId, "sourceDataset" -> node.provenance.source.wire)
          )
          renderer
            .render(input)
            .map(
              _.map(doc =>
                doc.copy(sourceReferences =
                  (doc.sourceReferences ++ refs).distinct.sortBy(r => (r.table, r.rowKey, r.field))
                )
              )
            )
        }
      }
    }
    val results = summaries ++ nodes
    results.collectFirst { case Left(code) => code } match {
      case Some(code) => Left(code)
      case None       => Right(results.collect { case Right(documents) => documents }.flatten)
    }
  }
  def run(args: Seq[String]): Either[String, ujson.Value] = try {
    for {
      flags <- parse(args)
      configPath = Path.of(flags("--config"))
      _ <- Either.cond(Files.size(configPath) <= 65536, (), "local-config-too-large")
      config = read[LocalEmbeddingConfig](Files.readString(configPath, UTF_8))
      // Force every configured bound to validate before data/state work.
      ingest = config.ingest
      selection = config.selection
      _ = config.rendering
      batch <- value(
        Phase6EmbeddingSource.load(
          Path.of(flags("--export")),
          selection,
          Some(Path.of(flags("--work-manifest")))
        )
      )
      documents <- renderSource(batch, config)
      _ <- Either.cond(
        documents.nonEmpty && documents.size <= config.maxManifestItems,
        (),
        "local-document-count-bound"
      )
      manifest = EmbeddingManifest(
        documents.map(document => EmbeddingManifests.item(document, config.model, ingest))
      )
      manifestJson = canonical(upickle.default.writeJs(manifest)).render()
      _ <- Either.cond(
        manifestJson.getBytes(UTF_8).length <= config.maxManifestBytes,
        (),
        "manifest-byte-limit"
      )
      state <- value(LocalEmbeddingState.open(Path.of(flags("--state")), ingest))
      _ <- EmbeddingContracts.indexes.values.toVector.distinct.sorted
        .foldLeft[Either[String, Unit]](Right(())) { (result, index) =>
          result.flatMap(_ =>
            value(state.vectors.ensureIndex(index, config.model.dimension, "cosine")).map(_ => ())
          )
        }
      report <- {
        val result = new EmbeddingManifestRunner(
          ingest,
          state.objects,
          state.vectors,
          state.registry,
          state.ledger,
          new DeterministicHashedEmbeddingClient(config.model)
        ).run(manifest, flags("--run-id"))
        value(state.save(Path.of(flags("--state")))).flatMap(_ => value(result))
      }
      outputReport <- {
        val reportPath = Path.of(flags("--report"))
        val qualificationPath =
          reportPath.resolveSibling(reportPath.getFileName.toString + ".source-qualifications.json")
        output(Path.of(flags("--manifest-output")), manifestJson)
        output(qualificationPath, batch.qualificationsJson)
        val counters = ujson.Obj(
          "written" -> report.written,
          "unchanged" -> report.unchanged,
          "conflicts" -> report.vectorKeyTextConflict,
          "rejected" -> report.rejected,
          "retried" -> report.retried,
          "embeddingCalls" -> report.embeddingCalls,
          "perIndex" -> ujson.Obj.from(
            report.perIndex.toVector.sortBy(_._1).map((k, v) => k -> ujson.Num(v))
          )
        )
        val json = canonical(
          ujson.Obj(
            "schemaVersion" -> "scholarchain.embedding-local-report.v1",
            "mode" -> "deterministic-fake",
            "runId" -> flags("--run-id"),
            "sourceRunId" -> batch.context.runId,
            "exportRoot" -> Path.of(flags("--export")).toAbsolutePath.toString,
            "workManifestSha256" -> StableIds.sha256Hex(
              Files.readString(Path.of(flags("--work-manifest")), UTF_8)
            ),
            "model" -> upickle.default.writeJs(config.model),
            "selectedDocuments" -> documents.size,
            "selectedSourceSummaries" -> batch.summaries.size,
            "selectedContextNodes" -> batch.nodes.size,
            "documentTypes" -> ujson.Obj.from(
              documents
                .groupMapReduce(_.documentType)(_ => 1)(_ + _)
                .toVector
                .sortBy(_._1)
                .map((k, v) => k -> ujson.Num(v))
            ),
            "sourceTableCounts" -> ujson.Obj.from(
              batch.tableCounts.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v.toString))
            ),
            "scannedRows" -> batch.scannedRows.toString,
            "sourceQualificationsPath" -> qualificationPath.toAbsolutePath.toString,
            "sourceQualificationsSha256" -> StableIds.sha256Hex(batch.qualificationsJson),
            "embeddingManifestSha256" -> StableIds.sha256Hex(manifestJson),
            "counters" -> counters,
            "vectorsPerSecond" -> report.vectorsPerSecond,
            "elapsedNanos" -> report.elapsedNanos.toString,
            "statePath" -> Path.of(flags("--state")).toAbsolutePath.toString,
            "rejections" -> ujson.Arr.from(
              report.rejections.map(r => ujson.Obj("key" -> r.key, "reason" -> r.reason))
            )
          )
        )
        output(reportPath, json.render())
        if (report.rejected > 0 || report.vectorKeyTextConflict > 0)
          Left("local-ingestion-rejected-items")
        else Right(json)
      }
    } yield outputReport
  } catch { case NonFatal(_) => Left("invalid-local-input-or-state") }
  def main(args: Array[String]): Unit = run(args.toSeq) match {
    case Right(report) => println(report.render())
    case Left(code)    => throw new IllegalArgumentException(code)
  }
}
