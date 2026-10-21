package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.entityresolution.*
import org.scalatest.funsuite.AnyFunSuite
import java.nio.file.Files

class IndependentResolutionPrepBridgeRepairSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  test(
    "B1 completed Hadoop exports with literal DOI resolver suffixes remain loadable and resolvable"
  ) {
    val dir = phase4RunDir("phase5b-doi-literal-repair").toAbsolutePath.normalize
    val raw = Vector(
      "10.5555/a%2Fb",
      "10.5555/a?b",
      "10.5555/(SICI)1097-4571(199912)50:14<1258::AID-ASI2>3.0.CO;2-X"
    )
    def xml(raw: String): String =
      raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    val records = raw.zipWithIndex
      .map { case (doi, i) =>
        dblpRecord(
          s"conf/independent/LiteralBridge$i",
          "<author>Alex Example</author>",
          s"<title>Literal resolver publication $i</title><year>2020</year><booktitle>Independent Systems</booktitle><ee>https://doi.org/${xml(doi)}</ee>"
        )
      }
      .mkString("\n")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(dblp, dblpDocument(records))
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9100000901","title":"Unrelated distributed database paper","type":"article","publication_year":2021,"authorships":[{"author":{"id":"https://openalex.org/A9100000901","display_name":"Blair Independent"}}]}""" + "\n"
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.5555/unrelated-bridge","title":["Unrelated distributed database paper"],"type":"journal-article","author":[{"given":"Blair","family":"Independent"}],"issued":{"date-parts":[[2021]]}}}""" + "\n"
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""" + "\n")
    val completed =
      runFreshPipeline(dir.resolve("output"), dblp, openAlex, crossref, orcid, 16, 32, 128)
    val hadoopWorks = works(exportLines(completed.directory))
    val expected = raw.map(d => StableIds.normalizeDoi(d).toOption.get).toSet
    assert(
      hadoopWorks.filter(_.source == SourceType.Dblp).flatMap(_.doi).toSet == expected,
      "the accepted Hadoop preparation contract must first retain all three literal DOI tokens"
    )
    val loaded = InputLoader.load(completed.directory, ResolutionConfig.example)
    assert(loaded.isRight, loaded.toString)
    val input = loaded.toOption.get
    val population = CandidateBuilder.build(input, ResolutionConfig.example).toOption.get
    val resolved = ResolutionEngine.resolve(
      input,
      population,
      ResolutionPolicy.example,
      ResolutionConfig.example,
      "disabled",
      None,
      IndependentResolutionFixtures.runId,
      IndependentResolutionFixtures.instant
    )
    assert(resolved.isRight, resolved.toString)
    val run = resolved.toOption.get
    assert(run.fakeCalls == 0)
    val constraints = run.constraints.find(_.entityType == ResolutionEntityType.Work).get
    assert(
      expected.subsetOf(
        constraints.authoritativeIdentifiers
          .filter(_.namespace == ResolutionAuthorityNamespace.Doi)
          .map(_.value)
          .toSet
      )
    )
    assert(
      run.decisions.exists { d =>
        val sources = Set(
          ResolutionIds.observation(d.pair.left).source,
          ResolutionIds.observation(d.pair.right).source
        )
        sources == Set(SourceType.OpenAlex, SourceType.Crossref)
      },
      "unrelated valid source comparisons still resolve instead of aborting the entire run"
    )
    run.constraints.foreach(c => assert(ResolutionValidation.check(c, input.context).isRight))
  }
}
