package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.scalatest.funsuite.AnyFunSuite

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*

/** Synthetic end-to-end evidence retention regressions for phase-04/review.md:657. */
class IndependentPhase4EvidenceSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  try org.apache.log4j.Logger.getRootLogger.setLevel(org.apache.log4j.Level.WARN)
  catch { case _: Throwable => () }

  private val keptOpenAlexId = "W9100000801"
  private val conflictOpenAlexId = "W9100000802"
  private val malformedOpenAlexId = "W9100000803"
  private val topDoi = "https://doi.org/10.1000/evidence.preferred"
  private val secondaryDoi = "10.1000/evidence.secondary"
  private val malformedSecondaryDoi = "not-a-secondary-doi"
  private val dblpKey = "conf/indep-evidence/Links"
  private val dblpLinks = Vector(
    NamedText("ee", "https://publisher.example/paper?x=1&y=2"),
    NamedText("ee", "https://repository.example/paper"),
    NamedText("ee", "https://doi.org/10.1000/evidence.dblp"),
    NamedText("ee", "https://arxiv.org/abs/2101.00001"),
    NamedText("url", "https://dblp.example/first"),
    NamedText("url", "https://dblp.example/second")
  )

  // Read-only assertions share one fresh run, avoiding four identical nine-job executions.
  private lazy val evidenceExport: Vector[String] = {
    val dir = phase4RunDir("independent-retained-source-evidence")
    val dblp = dir.resolve("dblp.xml")
    val linkTags = dblpLinks.map { link =>
      s"<${link.name}>${link.value.replace("&", "&amp;")}</${link.name}>"
    }.mkString
    Files.writeString(
      dblp,
      dblpDocument(
        s"""<article key="$dblpKey"><author>Ada</author><title>Linked publication</title>$linkTags</article>"""
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    val lines = Vector(
      openAlexLine(keptOpenAlexId, topDoi, secondaryDoi),
      openAlexLine(conflictOpenAlexId, "10.1000/evidence.conflict", "10.1000/evidence.left"),
      openAlexLine(conflictOpenAlexId, "10.1000/evidence.conflict", "10.1000/evidence.right"),
      openAlexLine(malformedOpenAlexId, "10.1000/evidence.valid", malformedSecondaryDoi)
    )
    Files.writeString(openAlex, lines.mkString("", "\n", "\n"))
    val crossref = emptyFile(dir, "crossref.jsonl")
    val orcid = emptyFile(dir, "orcid.jsonl")
    val result =
      runFreshPipeline(dir.resolve("output"), dblp, openAlex, crossref, orcid, 16, 32, 128)
    exportLines(result.directory)
  }

  test("final OpenAlex work retains both declared DOI fields separately from preferred DOI") {
    val work = works(evidenceExport)
      .find(_.sourceRecordId == keptOpenAlexId)
      .getOrElse(
        fail(s"accepted OpenAlex work $keptOpenAlexId missing")
      )
    assert(work.source == SourceType.OpenAlex)
    assert(work.doi.contains("10.1000/evidence.preferred"))
    assert(
      work.observedIdentifiers == Vector(
        ObservedIdentifier("openalex.doi", topDoi, IdentifierInterpretation.SourceObservation),
        ObservedIdentifier(
          "openalex.ids.doi",
          secondaryDoi,
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    assert(work.provenance.datasetSnapshot == independentSnapshots(SourceType.OpenAlex))
  }

  test("changing only ids.doi is a conflicting observation rather than an identical duplicate") {
    val rejected = rejects(evidenceExport)
    val conflicts = rejected.filter(_.reasonCode == RejectReasonCode.ConflictingObservation)
    assert(conflicts.size == 2, rejected.map(CoreJson.compact(_)).mkString("\n"))
    assert(conflicts.forall(_.source.contains(SourceType.OpenAlex)))
    assert(conflicts.forall(_.datasetSnapshot.contains(independentSnapshots(SourceType.OpenAlex))))
    assert(conflicts.forall(_.sourceLocator.contains(conflictOpenAlexId)))
    assert(!rejected.exists(_.reasonCode == RejectReasonCode.DuplicateIdenticalObservation))
    assert(!works(evidenceExport).exists(_.sourceRecordId == conflictOpenAlexId))
  }

  test("valid top-level DOI does not hide a malformed secondary ids.doi") {
    val invalid = rejects(evidenceExport).filter(_.reasonCode == RejectReasonCode.InvalidIdentifier)
    assert(invalid.size == 1, rejects(evidenceExport).map(CoreJson.compact(_)).mkString("\n"))
    assert(invalid.head.source.contains(SourceType.OpenAlex))
    assert(invalid.head.datasetSnapshot.contains(independentSnapshots(SourceType.OpenAlex)))
    assert(invalid.head.diagnosticExcerpt.exists(_.contains(malformedSecondaryDoi)))
    assert(!works(evidenceExport).exists(_.sourceRecordId == malformedOpenAlexId))
  }

  test("all DBLP electronic-edition and URL links survive final export with decoded values") {
    val work = works(evidenceExport)
      .find(_.sourceRecordId == dblpKey)
      .getOrElse(
        fail(s"accepted DBLP work $dblpKey missing")
      )
    assert(work.sourceLinks == dblpLinks)
    assert(work.externalUrl.contains("https://dblp.example/first"))
    assert(work.doi.contains("10.1000/evidence.dblp"))
    assert(work.arxivId.nonEmpty)
    assert(work.provenance.sourceRecordId == dblpKey)
    assert(work.provenance.datasetSnapshot == independentSnapshots(SourceType.Dblp))
  }

  test(
    "valid DBLP expansion overflow retains source snapshot and qualified distinct file locators"
  ) {
    val dir = phase4RunDir("independent-overflow-lineage")
    val maxRecordBytes = 1048576L
    val title = "A" * 600000
    val keys = (1 to 4).map(index => s"conf/indep-evidence/Overflow$index").toVector
    val articles = keys.map { key =>
      s"""<article key="$key"><title>$title</title></article>"""
    }
    articles.foreach { xml =>
      assert(xml.getBytes(StandardCharsets.UTF_8).length < maxRecordBytes)
      val parsed = DblpRecords.parse(
        xml,
        DblpXml.Header(Map.empty, None),
        runId,
        independentSnapshots(SourceType.Dblp),
        "independent-valid-overflow",
        maxRecordBytes,
        maxRecordBytes
      )
      assert(!parsed.exists { case EmittedRecord.Rejected(_) => true; case _ => false })
      val work = parsed.collect { case EmittedRecord.Work(value) => value }.head
      assert(CoreJson.compact(work).getBytes(StandardCharsets.UTF_8).length > maxRecordBytes)
    }
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(dblp, dblpDocument(articles.mkString("\n")))
    val openAlex = emptyFile(dir, "openalex.jsonl")
    val crossref = emptyFile(dir, "crossref.jsonl")
    val orcid = emptyFile(dir, "orcid.jsonl")
    val base = pipelineRequest(
      dir.resolve("output"),
      dblp,
      openAlex,
      crossref,
      orcid,
      16,
      32,
      128,
      freshRunId()
    )
    val request = base.copy(config =
      base.config.copy(
        reducerCount = 4,
        maxRecordBytes = maxRecordBytes,
        maxXmlEntityExpansion = maxRecordBytes
      )
    )
    val executed = HadoopPrepPipeline.execute(request)
    assert(executed.isRight, executed.left.toOption.getOrElse(""))
    val result = executed.toOption.get
    assert(!result.reused)
    val j01 = result.directory.resolve("intermediate/j01")
    val walk = Files.walk(j01)
    val nonemptyParts =
      try
        walk
          .iterator()
          .asScala
          .filter { path =>
            Files.isRegularFile(path) && path.getFileName.toString.startsWith("part-") && Files
              .size(path) > 0
          }
          .toVector
      finally walk.close()
    assert(nonemptyParts.size >= 2, "fixture must exercise multiple intermediate files")
    val exported = exportLines(result.directory)
    assert(
      works(exported).isEmpty,
      "oversized normalized observations must not be emitted as works"
    )
    val rejected = rejects(exported).filter(_.reasonCode == RejectReasonCode.OversizeRecord)
    assert(rejected.nonEmpty, "valid source expansion overflow was silently lost")
    assert(
      rejected.forall(_.source.contains(SourceType.Dblp)),
      rejected.map(CoreJson.compact(_)).mkString("\n")
    )
    assert(rejected.forall(_.datasetSnapshot.contains(independentSnapshots(SourceType.Dblp))))
    keys.foreach { key =>
      assert(rejected.exists(_.sourceLocator.contains(key)), s"missing overflow lineage for $key")
    }
    assert(
      rejected.forall(reject =>
        reject.sourceLocator.contains("file:") &&
          reject.sourceLocator.contains("/intermediate/") && reject.sourceLocator.contains("part-")
      )
    )
    val qualifiedParts = nonemptyParts.map(path => FsPaths.file(path.toString).toString)
    assert(
      rejected.forall(reject => qualifiedParts.exists(reject.sourceLocator.contains)),
      "overflow locator does not identify its qualified containing intermediate file"
    )
    assert(
      qualifiedParts.count(part => rejected.exists(_.sourceLocator.contains(part))) >= 2,
      "overflow locators must distinguish at least two containing files"
    )
    assert(
      rejected.map(_.sourceLocator).distinct.size >= keys.size,
      "overflow locators collide across distinct source observations"
    )
    assert(rejected.forall(_.sourceLocator.length <= RejectRecord.maxSourceLocatorLength))
    assert(
      rejected.forall(
        _.diagnosticExcerpt.forall(_.length <= RejectRecord.maxDiagnosticExcerptLength)
      )
    )
    val secondRequest = request.copy(runId = freshRunId())
    val secondExecution = HadoopPrepPipeline.execute(secondRequest)
    assert(secondExecution.isRight, secondExecution.left.toOption.getOrElse(""))
    val second = secondExecution.toOption.get
    assert(!second.reused)
    assert(result.runId != second.runId)
    assert(
      LogicalRecords.equivalent(
        result.directory.resolve("export"),
        second.directory.resolve("export"),
        result.runId,
        second.runId
      ),
      "equivalent valid source expansions differ solely because processing runs have different IDs"
    )

    // Perturb exported source evidence, without another job execution or editing retained runs.
    val secondLines = exportLines(second.directory)
    val firstExample = rejected.head
    val firstNormalized = LogicalRecords.normalize(CoreJson.compact(firstExample), result.runId)
    val secondExample = rejects(secondLines)
      .find { reject =>
        LogicalRecords.normalize(CoreJson.compact(reject), second.runId) == firstNormalized
      }
      .getOrElse(fail("second fresh run lacks a matching overflow observation"))
    val exampleKey = keys.find(firstExample.sourceLocator.contains).get
    val firstNativeUuid = firstExample.copy(sourceLocator =
      firstExample.sourceLocator.replace(
        exampleKey,
        s"conf/source-uuid/${result.runId.stripPrefix("run:")}"
      )
    )
    val secondNativeUuid = secondExample.copy(sourceLocator =
      secondExample.sourceLocator.replace(
        exampleKey,
        s"conf/source-uuid/${second.runId.stripPrefix("run:")}"
      )
    )
    assert(
      LogicalRecords.normalize(CoreJson.compact(firstNativeUuid), result.runId) !=
        LogicalRecords.normalize(CoreJson.compact(secondNativeUuid), second.runId),
      "a UUID supplied as a native source identifier must remain evidence"
    )
    val changes: Vector[(String, RejectRecord => RejectRecord)] = Vector(
      "source" -> (reject => reject.copy(source = Some(SourceType.OpenAlex))),
      "snapshot" -> (reject =>
        reject.copy(datasetSnapshot = Some(s"source-snapshot-${second.runId.stripPrefix("run:")}"))
      ),
      "native-record" -> (reject =>
        reject.copy(sourceLocator =
          reject.sourceLocator
            .replace("conf/indep-evidence/Overflow", "conf/indep-evidence/Changed")
        )
      )
    )
    changes.foreach { case (label, change) =>
      val changedDirectory = dir.resolve(s"changed-$label")
      Files.createDirectories(changedDirectory)
      val changedLines = secondLines.map { line =>
        CoreJson.parse[RejectRecord](line) match {
          case Right(reject) => CoreJson.compact(change(reject))
          case Left(_)       => line
        }
      }
      assert(changedLines != secondLines, s"$label perturbation must change source evidence")
      Files.writeString(
        changedDirectory.resolve("records.jsonl"),
        changedLines.mkString("", "\n", "\n")
      )
      assert(
        !LogicalRecords.equivalent(
          result.directory.resolve("export"),
          changedDirectory,
          result.runId,
          second.runId
        ),
        s"logical comparison erased a real $label evidence difference"
      )
    }
  }

  private def openAlexLine(id: String, doi: String, secondary: String): String =
    ujson.write(
      ujson.Obj(
        "id" -> id,
        "title" -> "Observed DOI evidence",
        "type" -> "article",
        "doi" -> doi,
        "ids" -> ujson.Obj("doi" -> secondary)
      )
    )

  private def emptyFile(dir: Path, name: String): Path = {
    val path = dir.resolve(name)
    Files.writeString(path, "")
    path
  }
}
