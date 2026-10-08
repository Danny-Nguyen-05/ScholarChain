package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*

import java.nio.file.{Files, Path}
import java.util.UUID
import scala.jdk.CollectionConverters.*

object IndependentTestSupport {
  val runId: String =
    StableIds
      .newRunId(UUID.fromString("a1a1a1a1-a1a1-41a1-81a1-a1a1a1a1a1a1"))
      .toOption
      .get

  val independentSnapshots: Map[SourceType, String] = Map(
    SourceType.Dblp -> "dblp-independent",
    SourceType.OpenAlex -> "openalex-independent",
    SourceType.Crossref -> "crossref-independent",
    SourceType.Orcid -> "orcid-independent"
  )

  val independentRetrievalDates: Map[SourceType, String] = Map(
    SourceType.Dblp -> "2026-10-05",
    SourceType.OpenAlex -> "2026-10-05",
    SourceType.Crossref -> "2026-10-05",
    SourceType.Orcid -> "2026-10-05"
  )

  def repoRoot: Path = {
    val here = Path.of(".").toAbsolutePath.normalize
    if (Files.isDirectory(here.resolve("datasets"))) here
    else here.getParent
  }

  def sample(subpath: String): Path = repoRoot.resolve(subpath)

  def freshRunId(): String =
    StableIds.newRunId(UUID.randomUUID()).toOption.get

  def phase4RunDir(label: String): Path = {
    val dir = Path.of("target/phase4-runs").resolve(s"$label-${UUID.randomUUID()}")
    Files.createDirectories(dir)
    dir
  }

  def prepConfig(outputRoot: Path, team: Int, block: Int, pairs: Int): HadoopPrepConfig =
    HadoopPrepConfig(
      SchemaVersions.hadoopPrep,
      1048576,
      1048576,
      1,
      block,
      pairs,
      team,
      100,
      outputRoot.toString,
      "none",
      false,
      HadoopExecutionMode.Local
    )

  def pipelineRequest(
      outputRoot: Path,
      dblp: Path,
      openAlex: Path,
      crossref: Path,
      orcid: Path,
      team: Int,
      block: Int,
      pairs: Int,
      runId: String,
      splitMax: Option[Long] = None,
      failJob: Option[String] = None
  ): HadoopPrepPipeline.Request =
    HadoopPrepPipeline.Request(
      prepConfig(outputRoot, team, block, pairs),
      dblp.toString,
      openAlex.toString,
      crossref.toString,
      orcid.toString,
      independentSnapshots,
      runId,
      splitMax,
      failJob,
      independentRetrievalDates
    )

  def exportHasAuthorMention(runDirectory: Path): Boolean =
    Files.walk(runDirectory.resolve("export")).iterator().asScala.exists { path =>
      path.toString.replace('\\', '/').contains("/author-mention/")
    }

  def runFreshPipeline(
      outputRoot: Path,
      dblp: Path,
      openAlex: Path,
      crossref: Path,
      orcid: Path,
      team: Int,
      block: Int,
      pairs: Int,
      runId: String = freshRunId(),
      splitMax: Option[Long] = None,
      failJob: Option[String] = None
  ): HadoopPrepPipeline.Result = {
    val result = HadoopPrepPipeline.execute(
      pipelineRequest(
        outputRoot,
        dblp,
        openAlex,
        crossref,
        orcid,
        team,
        block,
        pairs,
        runId,
        splitMax,
        failJob
      )
    )
    assert(result.isRight, result.left.getOrElse(""))
    val value = result.toOption.get
    assert(!value.reused, s"expected fresh pipeline execution for $runId")
    assert(exportHasAuthorMention(value.directory), "export missing author-mention partition")
    value
  }

  def dblpRecord(key: String, authors: String, rest: String): String =
    s"""<inproceedings key="$key">$authors$rest</inproceedings>"""

  def dblpDocument(body: String, doctype: String = "<!DOCTYPE dblp []>"): String =
    s"""<?xml version="1.0" encoding="UTF-8"?>
$doctype
<dblp>
$body
</dblp>
"""

  def parseDblp(
      xml: String,
      header: DblpXml.Header = DblpXml.Header(Map.empty, None),
      locator: String = "loc"
  ): Vector[EmittedRecord] =
    DblpRecords.parse(xml, header, runId, "dblp-independent", locator, 100000, 100000)

  def jsonLine(
      source: SourceType,
      line: String,
      locator: String = "json:1"
  ): Vector[EmittedRecord] =
    JsonSources.parseLine(source, line, runId, "snapshot-independent", locator, 100000)

  def exportLines(runDir: Path): Vector[String] =
    LogicalRecords.lines(runDir.resolve("export"))

  def works(lines: Vector[String]): Vector[WorkRecord] =
    lines.flatMap(line => CoreJson.parse[WorkRecord](line).toOption)

  def candidates(lines: Vector[String]): Vector[MatchCandidate] =
    lines.flatMap(line => CoreJson.parse[MatchCandidate](line).toOption)

  def rejects(lines: Vector[String]): Vector[RejectRecord] =
    lines.flatMap(line => CoreJson.parse[RejectRecord](line).toOption)

  def textDocs(lines: Vector[String]): Vector[EmittedTextDocument] =
    lines.flatMap(line => CoreJson.parse[EmittedTextDocument](line).toOption)

  def institutions(lines: Vector[String]): Vector[Institution] =
    lines.flatMap(line => CoreJson.parse[Institution](line).toOption)

  def graphEdges(lines: Vector[String]): Vector[GraphEdge] =
    lines.flatMap(line => CoreJson.parse[GraphEdge](line).toOption)

  def roundTrip[T: upickle.default.ReadWriter](value: T): T =
    CoreJson.parse[T](CoreJson.compact(value)).toOption.get
}
