package edu.uic.cs441.scholarchain.independent

import edu.uic.cs441.scholarchain.core.*
import edu.uic.cs441.scholarchain.hadoop.*
import org.scalatest.funsuite.AnyFunSuite

import java.nio.file.{Files, Path}

class IndependentHadoopPipelineSpec extends AnyFunSuite {
  import IndependentTestSupport.*

  test("pipeline duplicate identical and conflicting openalex observations surface in export") {
    val dir = phase4RunDir("dup-conflict")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/D1",
          "<author>Ada</author>",
          "<title>Stub</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    val dupLine =
      """{"id":"https://openalex.org/W9100000001","title":"Dup","doi":"https://doi.org/10.1000/indep.pipe.dup","type":"article","publication_year":2020}"""
    val conflict1 =
      """{"id":"https://openalex.org/W9100000002","title":"First","doi":"https://doi.org/10.1000/indep.pipe.conf","type":"article","publication_year":2020}"""
    val conflict2 =
      """{"id":"https://openalex.org/W9100000002","title":"Second","doi":"https://doi.org/10.1000/indep.pipe.conf","type":"article","publication_year":2020}"""
    Files.writeString(openAlex, s"$dupLine\n$dupLine\n$conflict1\n$conflict2\n")
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.pipe.dup","title":["Dup"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val lines = exportLines(result.directory)
    assert(rejects(lines).exists(_.reasonCode == RejectReasonCode.DuplicateIdenticalObservation))
    assert(rejects(lines).exists(_.reasonCode == RejectReasonCode.ConflictingObservation))
  }

  test("pipeline shared doi across dblp and crossref keeps lineage in match candidate sides") {
    val dir = phase4RunDir("shared-doi")
    val sharedDoi = "10.1000/indep.lineage"
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/L1",
          "<author>Ada</author>",
          s"<title>Lineage A</title><year>2020</year><ee>https://doi.org/$sharedDoi</ee>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9100000100","title":"Other","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      s"""{"message":{"DOI":"$sharedDoi","title":["Lineage B"],"type":"journal-article","author":[{"given":"Ada","family":"Lovelace"}],"issued":{"date-parts":[[2020]]}}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val lines = exportLines(result.directory)
    val matched = candidates(lines).find { c =>
      c.left.source != c.right.source && c.blockKey.contains("doi")
    }
    assert(matched.nonEmpty)
    val candidate = matched.get
    assert(candidate.left.sourceRecordId != candidate.right.sourceRecordId)
    assert(
      Set(candidate.left.source, candidate.right.source) == Set(
        SourceType.Dblp,
        SourceType.Crossref
      )
    )
    val dblpWorks = works(lines).filter(_.source == SourceType.Dblp)
    val crossWorks = works(lines).filter(_.source == SourceType.Crossref)
    assert(dblpWorks.size == 1 && crossWorks.size == 1)
    assert(dblpWorks.head.workId == crossWorks.head.workId)
  }

  test("pipeline orcid activity keeps ror and ringgold distinct and work doi is not authorship") {
    val dir = phase4RunDir("orcid-activity")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/O1",
          "<author>Ada</author>",
          "<title>Dblp stub</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9100000200","title":"Stub","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.orcid.stub","title":["Stub"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(
      orcid,
      """{"orcid-identifier":{"path":"0000-0002-4414-6920"},"activities-summary":{"employments":{"affiliation-group":[{"summaries":[{"employment-summary":{"path":"/0000-0002-4414-6920/employment/1","put-code":1,"organization":{"name":"Lab","disambiguated-organization":{"disambiguated-organization-identifier":"https://ror.org/02catss52","disambiguation-source":"ROR"}}}}]}]},"distinctions":{"affiliation-group":[{"summaries":[{"distinction-summary":{"path":"/0000-0002-4414-6920/distinction/2","put-code":2,"organization":{"name":"Society","disambiguated-organization":{"disambiguated-organization-identifier":"385488","disambiguation-source":"RINGGOLD"}}}}]}]},"works":{"group":[{"work-summary":[{"path":"/0000-0002-4414-6920/work/3","put-code":3,"title":{"title":{"value":"Orcid work"}},"external-ids":{"external-id":[{"external-id-type":"doi","external-id-value":"10.1000/indep.orcid.workdoi"}]}}]}]}}}"""
    )
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val lines = exportLines(result.directory)
    val activities = lines.flatMap(line => CoreJson.parse[OrcidActivityRecord](line).toOption)
    val employment = activities.find(_.activityKind == OrcidActivityKind.Employment).get
    val distinction = activities.find(_.activityKind == OrcidActivityKind.Distinction).get
    val workActivity = activities.find(_.activityKind == OrcidActivityKind.Work).get
    assert(employment.ror.nonEmpty && employment.ringgold.isEmpty)
    assert(distinction.ringgold.nonEmpty && distinction.ror.isEmpty)
    assert(workActivity.observedDoi.contains("10.1000/indep.orcid.workdoi"))
    assert(!works(lines).exists(_.source == SourceType.Orcid))
    val authorships = lines.flatMap(line => CoreJson.parse[AuthorshipRecord](line).toOption)
    assert(
      authorships.forall(a =>
        works(lines).exists(w => w.workId == a.workId && w.source != SourceType.Orcid)
      )
    )
    assert(
      !candidates(lines).exists(c =>
        c.left.source == SourceType.Orcid || c.right.source == SourceType.Orcid
      )
    )
  }

  test("pipeline block size below at and above maxCandidateBlockSize three") {
    val dir = phase4RunDir("block-limits")
    val doi = "10.1000/indep.block"
    val crossrefLine =
      s"""{"message":{"DOI":"$doi","title":["Block CR"],"type":"journal-article","author":[{"given":"A","family":"One"}],"issued":{"date-parts":[[2020]]}}}"""
    val orcidLine = """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}"""
    val openAlexStub =
      """{"id":"https://openalex.org/W9200999999","title":"Unrelated","type":"article","publication_year":2020}"""
    val openAlex1 =
      s"""{"id":"https://openalex.org/W9200000001","title":"Block OA1","doi":"https://doi.org/$doi","type":"article","publication_year":2020}"""
    val dblp1 = dblpRecord(
      "conf/indep-block/B1",
      "<author>A1</author>",
      s"<title>Block one</title><year>2020</year><ee>https://doi.org/$doi</ee>"
    )
    val dblp2 = dblpRecord(
      "conf/indep-block/B2",
      "<author>A2</author>",
      s"<title>Block two</title><year>2020</year><ee>https://doi.org/$doi</ee>"
    )
    def run(suffix: String, dblpBody: String, openAlexBody: String): Vector[String] = {
      val dblp = dir.resolve(s"dblp-$suffix.xml")
      Files.writeString(dblp, dblpDocument(dblpBody))
      val openAlex = dir.resolve(s"openalex-$suffix.jsonl")
      Files.writeString(openAlex, openAlexBody)
      val crossref = dir.resolve(s"crossref-$suffix.jsonl")
      Files.writeString(crossref, crossrefLine)
      val orcid = dir.resolve(s"orcid-$suffix.jsonl")
      Files.writeString(orcid, orcidLine)
      val out = dir.resolve(s"output-$suffix")
      val result =
        runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, block = 3, pairs = 128)
      exportLines(result.directory)
    }

    val below = run("below", dblp1, openAlexStub)
    assert(candidates(below).nonEmpty)
    assert(!rejects(below).exists(_.reasonCode == RejectReasonCode.OversizeBlock))

    val atLimit = run("at", dblp1 + dblp2, openAlexStub)
    assert(candidates(atLimit).nonEmpty)
    assert(!rejects(atLimit).exists(_.reasonCode == RejectReasonCode.OversizeBlock))

    val above = run("above", dblp1 + dblp2, openAlexStub + "\n" + openAlex1)
    assert(rejects(above).exists(_.reasonCode == RejectReasonCode.OversizeBlock))
    assert(!candidates(above).exists(_.blockKey == s"exact:doi:$doi"))
  }

  test("pipeline abstractTextRef resolves to emitted chunk document") {
    val dir = phase4RunDir("abstract-ref")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/A1",
          "<author>Ada</author>",
          "<title>Dblp only</title><year>2020</year>"
        )
      )
    )
    val abstractIndex = """{"machine":[0],"learning":[1],"works":[2]}"""
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      s"""{"id":"https://openalex.org/W9300000001","title":"Abstract paper","doi":"https://doi.org/10.1000/indep.abstract","type":"article","publication_year":2020,"authorships":[{"raw_author_name":"Ada","author":{"display_name":"Ada"}}],"abstract_inverted_index":$abstractIndex}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.stub","title":["Stub"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val lines = exportLines(result.directory)
    val oaWorks = works(lines).filter(_.source == SourceType.OpenAlex)
    assert(oaWorks.exists(_.abstractTextRef.nonEmpty))
    val docs = textDocs(lines)
    assert(TextRefs.unresolved(oaWorks, docs).isEmpty)
    assert(docs.exists(_.textId.startsWith("chunk:")))
  }

  test("pipeline json round trip preserves emitted MatchCandidate and WorkRecord") {
    val dir = phase4RunDir("round-trip")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/R1",
          "<author>Ada</author>",
          "<title>Round trip</title><year>2020</year><ee>https://doi.org/10.1000/indep.round</ee>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9400000001","title":"Round trip","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.round","title":["Round trip"],"type":"journal-article","author":[{"given":"Ada","family":"Lovelace"}],"issued":{"date-parts":[[2020]]}}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val lines = exportLines(result.directory)
    val work = works(lines).find(_.source == SourceType.Dblp).get
    val candidate = candidates(lines).head
    assert(roundTrip(work) == work)
    assert(roundTrip(candidate) == candidate)
  }

  test("OutputGate refuses occupied output and failed pipeline run skips completion marker") {
    val dir = phase4RunDir("output-gate")
    val dirty = dir.resolve("dirty-output")
    Files.createDirectories(dirty)
    Files.writeString(dirty.resolve("stray.txt"), "keep")
    val probeIdentity = OutputIdentity(
      freshRunId(),
      "c" * 64,
      Map("dblp" -> ("a" * 64), "openalex" -> ("b" * 64)),
      Map("dblp" -> "dblp-independent", "openalex" -> "openalex-independent"),
      Map("dblp" -> "2026-10-05", "openalex" -> "2026-10-05"),
      Vector.empty
    )
    assert(OutputGate.claim(dirty, probeIdentity).isInstanceOf[OutputGate.Refuse])

    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/F1",
          "<author>Ada</author>",
          "<title>Fail run</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9500000001","title":"Fail","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.fail","title":["Fail"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("pipeline-output")
    runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    val failedRunId = freshRunId()
    val failed = HadoopPrepPipeline.execute(
      pipelineRequest(
        out,
        dblp,
        openAlex,
        crossref,
        orcid,
        16,
        32,
        128,
        failedRunId,
        failJob = Some("J02")
      )
    )
    assert(failed.isLeft)
    val failedDir = out.resolve(HadoopPrepPipeline.directoryName(failedRunId))
    assert(!Files.exists(failedDir.resolve(OutputGate.MarkerName)))
  }

  test("pipeline identical second request reuses completed output") {
    val dir = phase4RunDir("reuse")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-pipe/Reuse1",
          "<author>Ada</author>",
          "<title>Reuse</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(
      openAlex,
      """{"id":"https://openalex.org/W9500000002","title":"Reuse","type":"article","publication_year":2020}"""
    )
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.reuse","title":["Reuse"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val runId = freshRunId()
    val request = pipelineRequest(out, dblp, openAlex, crossref, orcid, 16, 32, 128, runId)
    val first = HadoopPrepPipeline.execute(request)
    assert(first.isRight)
    assert(first.toOption.exists(r => !r.reused))
    assert(exportHasAuthorMention(first.toOption.get.directory))
    val second = HadoopPrepPipeline.execute(request)
    assert(second.isRight)
    assert(second.toOption.exists(_.reused))
  }

  test(
    "pipeline institution-bearing openalex observation exports one work and one institution without conflict"
  ) {
    val openAlexId = "W9600000001"
    val line = institutionOpenAlexWork(
      openAlexId,
      "10.1000/indep.inst.ror",
      "Institution held work",
      "T96000001",
      "Independent institution topic"
    )
    val lines = runOpenAlexObservation(line)
    val openAlexWorks = works(lines).filter(_.source == SourceType.OpenAlex)
    val exportedInstitutions = institutions(lines)
    assert(openAlexWorks.count(_.sourceRecordId == openAlexId) == 1)
    assert(exportedInstitutions.count(_.institutionId == "institution:ror:02catss52") == 1)
    assert(!rejects(lines).exists(_.reasonCode == RejectReasonCode.ConflictingObservation))
    assert(!lines.exists(_.contains("CONFLICTING_OBSERVATION")))
  }

  test(
    "pipeline differing topics on the same openalex observation key conflict and emit no HasTopic edge"
  ) {
    val openAlexId = "W9600000002"
    val sharedDoi = "10.1000/indep.topic.conflict"
    val title = "Same work different topics"
    val left =
      institutionOpenAlexWork(openAlexId, sharedDoi, title, "T96000011", "IndepTopicLeft")
    val right =
      institutionOpenAlexWork(openAlexId, sharedDoi, title, "T96000012", "IndepTopicRight")
    val lines = runOpenAlexObservation(s"$left\n$right")
    assert(rejects(lines).exists(_.reasonCode == RejectReasonCode.ConflictingObservation))
    assert(!works(lines).exists(_.sourceRecordId == openAlexId))
    assert(!graphEdges(lines).exists(_.edgeType == GraphEdgeType.HasTopic))
    assert(!lines.exists(_.contains("HAS_TOPIC")))
    assert(!lines.exists(_.contains("IndepTopicLeft")))
    assert(!lines.exists(_.contains("IndepTopicRight")))
  }

  test("LocalJobRunner sample replay export is logically equivalent across two run ids") {
    val configPath = sample("modules/core/src/main/resources/scholarchain.hadoop-prep.v1.json")
    val loaded = HadoopPrepConfigLoader.load(configPath).toOption.get
    val outRoot = phase4RunDir("sample-replay")
    val config =
      loaded.copy(outputRoot = outRoot.toString, executionMode = HadoopExecutionMode.Local)
    val dblp = sample("datasets/samples/dblp/linked-records.xml")
    val openAlex = sample("datasets/samples/openalex/works.jsonl")
    val crossref = sample("datasets/samples/crossref/works.jsonl")
    val orcid = sample("datasets/samples/orcid/records.jsonl")
    assume(Files.isRegularFile(dblp), s"missing sample $dblp")
    val firstRunId = freshRunId()
    val secondRunId = freshRunId()
    val first = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config,
        dblp.toString,
        openAlex.toString,
        crossref.toString,
        orcid.toString,
        HadoopPrepPipeline.DefaultSnapshots,
        firstRunId,
        retrievalDates = HadoopPrepPipeline.DefaultRetrievalDates
      )
    )
    val second = HadoopPrepPipeline.execute(
      HadoopPrepPipeline.Request(
        config,
        dblp.toString,
        openAlex.toString,
        crossref.toString,
        orcid.toString,
        HadoopPrepPipeline.DefaultSnapshots,
        secondRunId,
        retrievalDates = HadoopPrepPipeline.DefaultRetrievalDates
      )
    )
    assert(first.isRight && second.isRight)
    assert(first.toOption.exists(r => !r.reused))
    assert(second.toOption.exists(r => !r.reused))
    assert(exportHasAuthorMention(first.toOption.get.directory))
    assert(exportHasAuthorMention(second.toOption.get.directory))
    val same = LogicalRecords.equivalent(
      first.toOption.get.directory.resolve("export"),
      second.toOption.get.directory.resolve("export"),
      first.toOption.get.runId,
      second.toOption.get.runId
    )
    assert(same)
  }

  private def institutionOpenAlexWork(
      id: String,
      doi: String,
      title: String,
      topicId: String,
      topicName: String
  ): String =
    s"""{"id":"https://openalex.org/$id","doi":"https://doi.org/$doi","title":"$title","publication_year":2020,"type":"article","authorships":[{"raw_author_name":"Ada Lovelace","author":{"id":"https://openalex.org/A5048491430","display_name":"Ada Lovelace"},"institutions":[{"id":"https://openalex.org/I4210144935","display_name":"Analytical Engine","ror":"https://ror.org/02catss52"}]}],"primary_location":{"source":{"id":"https://openalex.org/S4210195904","display_name":"PT AI","issn_l":"2192-6255"}},"topics":[{"id":"https://openalex.org/$topicId","display_name":"$topicName","score":0.5}]}"""

  private def runOpenAlexObservation(openAlexBody: String): Vector[String] = {
    val dir = phase4RunDir("openalex-obs")
    val dblp = dir.resolve("dblp.xml")
    Files.writeString(
      dblp,
      dblpDocument(
        dblpRecord(
          "conf/indep-join/Stub1",
          "<author>Ada</author>",
          "<title>Local stub</title><year>2020</year>"
        )
      )
    )
    val openAlex = dir.resolve("openalex.jsonl")
    Files.writeString(openAlex, openAlexBody)
    val crossref = dir.resolve("crossref.jsonl")
    Files.writeString(
      crossref,
      """{"message":{"DOI":"10.1000/indep.join.stub","title":["Stub"],"type":"journal-article"}}"""
    )
    val orcid = dir.resolve("orcid.jsonl")
    Files.writeString(orcid, """{"orcid-identifier":{"path":"0000-0002-4414-6920"}}""")
    val out = dir.resolve("output")
    val result = runFreshPipeline(out, dblp, openAlex, crossref, orcid, 16, 32, 128)
    exportLines(result.directory)
  }
}
