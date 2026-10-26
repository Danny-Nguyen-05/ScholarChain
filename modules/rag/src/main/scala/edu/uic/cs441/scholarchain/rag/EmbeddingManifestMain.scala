package edu.uic.cs441.scholarchain.rag

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.storage.*
import java.nio.file.{Files, Path}
import java.nio.charset.StandardCharsets.UTF_8
import scala.util.control.NonFatal
import upickle.default.read

/** Render-only handoff: reads completed source and creates real-model-tagged work without
  * constructing an embedder, fake state, credentials or SDK clients.
  */
object EmbeddingManifestMain {
  private val flags =
    Set("--export", "--work-manifest", "--config", "--manifest-output", "--report")
  private def canonical(value: ujson.Value): ujson.Value = value match {
    case o: ujson.Obj =>
      ujson.Obj.from(o.obj.toVector.sortBy(_._1).map((k, v) => k -> canonical(v)))
    case a: ujson.Arr => ujson.Arr.from(a.arr.map(canonical))
    case other        => other
  }
  private def value[A](r: StorageResult[A]): Either[String, A] = r match {
    case StorageResult.Rejected(code) => Left(code)
    case other => StorageResult.value(other).toRight("render-source-unavailable")
  }
  def render(
      batch: EmbeddingSourceBatch,
      config: LocalEmbeddingConfig
  ): Either[String, EmbeddingManifest] =
    EmbeddingIngestMain.renderSource(batch, config).flatMap { documents =>
      if (documents.isEmpty || documents.size > config.maxManifestItems)
        Left("render-document-count-bound")
      else {
        val manifest = EmbeddingManifest(
          documents.map(doc => EmbeddingManifests.item(doc, config.model, config.ingest))
        )
        val serialized = canonical(upickle.default.writeJs(manifest)).render()
        if (serialized.getBytes(UTF_8).length > config.maxManifestBytes) Left("manifest-byte-limit")
        else if (manifest.items.exists(item => EmbeddingValidation.workItem(item).nonEmpty))
          Left("invalid-rendered-manifest")
        else Right(manifest)
      }
    }
  private def output(path: Path, text: String): Unit = {
    Option(path.toAbsolutePath.getParent).foreach(Files.createDirectories(_))
    Files.writeString(path, text, UTF_8)
  }
  def run(args: Seq[String]): Either[String, ujson.Value] = try {
    val pairs = args.grouped(2).toVector
    if (
      pairs.size != flags.size || pairs.exists(_.size != 2) || pairs.map(_.head).toSet != flags ||
      pairs.map(_.head).distinct.size != flags.size || pairs.exists(_.last.trim.isEmpty)
    ) Left("invalid-render-arguments")
    else {
      val input = pairs.map(p => p(0) -> p(1)).toMap
      val cp = Path.of(input("--config"))
      if (Files.size(cp) > 65536) Left("render-config-too-large")
      else {
        val config = read[LocalEmbeddingConfig](Files.readString(cp, UTF_8))
        value(
          Phase6EmbeddingSource.load(
            Path.of(input("--export")),
            config.selection,
            Some(Path.of(input("--work-manifest")))
          )
        ).flatMap { batch =>
          render(batch, config).map { manifest =>
            val manifestJson = canonical(upickle.default.writeJs(manifest)).render()
            val reportPath = Path.of(input("--report"))
            val qualificationPath = reportPath.resolveSibling(
              reportPath.getFileName.toString + ".source-qualifications.json"
            )
            output(Path.of(input("--manifest-output")), manifestJson)
            output(qualificationPath, batch.qualificationsJson)
            val report = canonical(
              ujson.Obj(
                "schemaVersion" -> "scholarchain.embedding-render-report.v1",
                "mode" -> "render-only",
                "embeddingCalls" -> 0,
                "stateWritten" -> false,
                "sourceRunId" -> batch.context.runId,
                "model" -> upickle.default.writeJs(config.model),
                "selectedDocuments" -> manifest.items.size,
                "documentTypes" -> ujson.Obj.from(
                  manifest.items
                    .groupMapReduce(_.document.documentType)(_ => 1)(_ + _)
                    .toVector
                    .sortBy(_._1)
                    .map((k, v) => k -> ujson.Num(v))
                ),
                "sourceTableCounts" -> ujson.Obj.from(
                  batch.tableCounts.toVector.sortBy(_._1).map((k, v) => k -> ujson.Str(v.toString))
                ),
                "scannedRows" -> batch.scannedRows.toString,
                "embeddingManifestSha256" -> StableIds.sha256Hex(manifestJson),
                "workManifestSha256" -> StableIds.sha256Hex(
                  Files.readString(Path.of(input("--work-manifest")), UTF_8)
                ),
                "sourceQualificationsPath" -> qualificationPath.toAbsolutePath.toString,
                "sourceQualificationsSha256" -> StableIds.sha256Hex(batch.qualificationsJson)
              )
            )
            output(reportPath, report.render())
            report
          }
        }
      }
    }
  } catch { case NonFatal(_) => Left("invalid-render-input") }
  def main(args: Array[String]): Unit = run(args.toSeq) match {
    case Right(report) => println(report.render())
    case Left(code)    => throw new IllegalArgumentException(code)
  }
}
