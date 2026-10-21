package edu.uic.cs441.scholarchain.entityresolution

import edu.uic.cs441.scholarchain.core.*
import java.nio.file.Files
import java.util.concurrent.atomic.AtomicInteger
import org.scalatest.funsuite.AnyFunSuite
import upickle.default.{write, writeJs}

private object ErTestData {
  val run = "run:11111111-1111-4111-8111-111111111111"
  val instant = "2026-10-16T12:00:00Z"
  def work(
      key: String,
      title: String = "Atomic log storage",
      doi: Option[String] = None,
      names: Vector[String] = Vector("Nora Test"),
      year: Option[Int] = Some(2021)
  ): WorkRecord = {
    val p = Provenance(
      SchemaVersions.domain,
      SourceType.Dblp,
      key,
      None,
      "er-synthetic-v1",
      Some("2026-10-16"),
      None,
      run,
      Vector("synthetic owner fixture")
    )
    val authors = names.zipWithIndex.map((n, i) =>
      AuthorMention(
        StableIds.mentionId(SourceType.Dblp, key, i + 1),
        SchemaVersions.domain,
        SourceType.Dblp,
        key,
        i + 1,
        n,
        TextNorm.personName(n),
        None,
        None,
        MentionIdentityStatus.NameOnlyUnconfirmed,
        None,
        "unconfirmed synthetic",
        p
      )
    )
    WorkRecord(
      SchemaVersions.domain,
      StableIds.authoritativeWorkId(doi, None, StableIds.workIdFromDblpKey(key)).toOption.get,
      SourceType.Dblp,
      key,
      None,
      title,
      TextNorm.title(title),
      year,
      None,
      doi,
      None,
      None,
      None,
      authors,
      None,
      p
    )
  }
  def endpoint(w: WorkRecord): ResolutionEndpoint =
    ResolutionEndpoint.Work(ResolutionInput.ref(w.provenance), w.workId)
  def candidate(
      a: WorkRecord,
      b: WorkRecord,
      key: String = "title-year:synthetic"
  ): MatchCandidate = {
    val oa = CandidateObservation(
      a.source,
      a.sourceRecordId,
      a.provenance.datasetSnapshot,
      Some(a.workId)
    );
    val ob =
      CandidateObservation(b.source, b.sourceRecordId, b.provenance.datasetSnapshot, Some(b.workId))
    val (l, r) = StableIds.canonicalCandidateObservations(oa, ob).toOption.get
    val id = StableIds.matchCandidateId(l, r, key).toOption.get
    MatchCandidate(
      id,
      SchemaVersions.domain,
      key,
      l,
      r,
      Vector(NamedNumber(PreparationFeatures.yearAbsDelta, -1)),
      PreparationFeatures.policyV2,
      run,
      "blocking only",
      Provenance(
        SchemaVersions.domain,
        SourceType.ScholarChain,
        id,
        None,
        "hadoop-prep",
        None,
        None,
        run,
        Vector.empty
      )
    )
  }
  def input(a: WorkRecord, b: WorkRecord): ResolutionInput = ResolutionInput
    .create(Vector(a, b), Vector.empty, Vector.empty, Vector(candidate(a, b)))
    .fold(e => throw new IllegalArgumentException(e), identity)
  def comparison(a: WorkRecord, b: WorkRecord, in: ResolutionInput): DerivedPair = DerivedPair(
    ResolutionIds.pair(ResolutionEntityType.Work, endpoint(a), endpoint(b)).toOption.get,
    Vector.empty,
    (in.refs(endpoint(a)) ++ in.refs(endpoint(b))).distinct.sorted
  )
}

class OfflineResolutionSpec extends AnyFunSuite {
  import ErTestData.*
  test("runtime resources are strict uncalibrated configs; duplicate/unknown keys fail") {
    val p = ResolutionPolicy.example; val c = ResolutionConfig.example
    assert(p.policyVersion.contains("uncalibrated")); assert(c.adjudication.maxSpendUsd == 0)
    val obj = writeJs(p); obj.obj("unknown") = ujson.Num(1)
    assert(ResolutionPolicy.parse(obj.render()).isLeft)
    assert(
      ResolutionConfig.parse(write(c).replaceFirst("\\{", "{\"schemaVersion\":\"ignored\",")).isLeft
    )
    assert(
      ResolutionPolicy
        .validate(p.copy(work = p.work.copy(llmBandMin = p.work.rejectThreshold)))
        .isLeft
    )
  }
  test(
    "normalization keeps raw accents separate and respects initials surname and repository escapes"
  ) {
    assert(Normalization.text("<b>José</b>  Garcia") == "josé garcia")
    assert(Normalization.folded("José García") == "jose garcia")
    assert(Normalization.initialsCompatible("Jim Smith", "John Smythe").contains(0))
    assert(Normalization.initialsCompatible("Smith, J.", "John Smith").contains(1))
    assert(
      IdentifierRules
        .normalize("repository-url", "https://EXAMPLE.org/a%2Fb?q=x%26y")
        .toOption
        .get == "https://example.org/a%2Fb?q=x%26y"
    )
    assert(
      IdentifierRules.normalize(
        "repository-url",
        "https://example.org/a/b?q=x&y"
      ) != IdentifierRules.normalize("repository-url", "https://example.org/a%2Fb?q=x%26y")
    )
  }
  test("hard conflict dominates exact DOI and bibliographic similarity") {
    val a = work("conf/test/A", doi = Some("10.1000/a"));
    val b = work("conf/test/B", doi = Some("10.1000/a")).copy(observedIdentifiers =
      Vector(ObservedIdentifier("doi", "10.1000/b", IdentifierInterpretation.SourceObservation))
    )
    val in = input(a, b);
    val result =
      ResolutionEngine.classify(comparison(a, b, in), in, ResolutionPolicy.example).toOption.get
    assert(result.outcome == MatchOutcome.Conflict);
    assert(result.path == ResolutionDecisionPath.HardConflict)
  }
  test("same publication copies cannot supply independent researcher coauthor support") {
    val a = work("conf/test/A", doi = Some("10.1000/a"), names = Vector("Nora Test", "Sam Other"));
    val b = work("conf/test/B", doi = Some("10.1000/a"), names = Vector("Nora Test", "Sam Other"))
    val in = input(a, b);
    val pair = ResolutionIds
      .pair(
        ResolutionEntityType.Researcher,
        ResolutionEndpoint.Mention(ResolutionInput.ref(a.provenance), a.authors.head.mentionId),
        ResolutionEndpoint.Mention(ResolutionInput.ref(b.provenance), b.authors.head.mentionId)
      )
      .toOption
      .get
    val result = ResolutionEngine
      .classify(DerivedPair(pair, Vector.empty, Vector.empty), in, ResolutionPolicy.example)
      .toOption
      .get
    assert(result.features.find(_.name == "coauthorOverlap").get.value.isEmpty)
    assert(result.outcome == MatchOutcome.Unresolved)
  }
  test("missing year remains unavailable and does not consume preparation sentinel") {
    val a = work("conf/test/A", year = None); val b = work("conf/test/B", year = None)
    val in = input(a, b);
    val result =
      ResolutionEngine.classify(comparison(a, b, in), in, ResolutionPolicy.example).toOption.get
    assert(result.features.find(_.name == "yearCompatibility").get.value.isEmpty)
    assert(result.features.find(_.name == "citationNeighborhood").get.value.isEmpty)
    assert(result.outcome == MatchOutcome.Unresolved)
  }
  test("oversize blocks and aggregate multiblock evidence are explicit diagnostics") {
    val a = work("conf/test/A"); val b = work("conf/test/B"); val in = input(a, b)
    val config = ResolutionConfig.example.copy(blocking =
      ResolutionConfig.example.blocking.copy(maxMembersPerBlock = 1)
    )
    val result = CandidateBuilder.build(in, config).toOption.get
    assert(result.pairs.isEmpty);
    assert(result.diagnostics.exists(_.code == "PREP_OVERSIZE_BLOCK_ROWS"))
    val rows = (1 to 5).map(i => candidate(a, b, "venue:test" + i)).toVector
    val mult = ResolutionInput.create(Vector(a, b), Vector.empty, Vector.empty, rows).toOption.get
    val pair = CandidateBuilder
      .build(input(a, b), ResolutionConfig.example)
      .toOption
      .get
      .pairs
      .find(_.pair.entityType == ResolutionEntityType.Work)
      .get
    val size = pair.evidenceRefs
      .map(r =>
        in.evidence(r).payload.render().getBytes(java.nio.charset.StandardCharsets.UTF_8).length
      )
      .sum
    val bounded = CandidateBuilder
      .build(
        mult,
        ResolutionConfig.example.copy(blocking =
          ResolutionConfig.example.blocking.copy(maxEvidenceBytesPerPair = size + 10)
        )
      )
      .toOption
      .get
    assert(!bounded.pairs.exists(_.pair.entityType == ResolutionEntityType.Work));
    assert(bounded.diagnostics.exists(_.code == "PAIR_AGGREGATE_EVIDENCE_BYTE_BOUND"))
  }
  test("field citations must point to present supplied input fields; unknown JSON is rejected") {
    val a = work("conf/test/A"); val b = work("conf/test/B"); val in = input(a, b);
    val p = ResolutionPolicy.example; val c = ResolutionConfig.example
    val pair = comparison(a, b, in);
    val req = Adjudication
      .request(pair, in, p, c, FeatureExtractor.extract(pair, in, p), in.evidence)
      .toOption
      .get
    val ref = in.refs(endpoint(a)).head
    val response = AdjudicationResponse(
      Adjudication.responseSchema,
      req.requestHash,
      req.pairId,
      req.sourceId,
      req.targetId,
      req.inputEvidenceHash,
      req.policyHash,
      "accept",
      Vector("SUPPORTED_SAME_IDENTITY"),
      Vector(ref),
      "Synthetic schema fixture",
      0.8,
      Vector(ref + "#/title")
    )
    assert(Adjudication.validateResponse(write(response), req, c).isRight)
    assert(
      Adjudication
        .validateResponse(write(response.copy(fieldRefs = Vector(ref + "#/fabricated"))), req, c)
        .isLeft
    )
    assert(
      Adjudication
        .validateResponse(write(response.copy(fieldRefs = Vector(ref + "#/doi"))), req, c)
        .isLeft
    )
    val bad = writeJs(response); bad.obj("invented") = ujson.Str("data")
    assert(Adjudication.validateResponse(bad.render(), req, c).isLeft)
  }
  test("disabled run is source bound, exports complete constraints and refuses overwrite") {
    val a = work("conf/test/A", doi = Some("10.1000/a"));
    val b = work("conf/test/B", doi = Some("10.1000/a")); val in = input(a, b);
    val c = ResolutionConfig.example; val p = ResolutionPolicy.example
    val population = CandidateBuilder.build(in, c).toOption.get
    val run = ResolutionEngine
      .resolve(in, population, p, c, "disabled", None, ErTestData.run, instant)
      .fold(e => fail(e), identity)
    assert(run.fakeCalls == 0); assert(run.links.size == 1)
    val parent = Files.createTempDirectory("er-owner-export-").toRealPath();
    val output = parent.resolve("new")
    val manifest = LinkExporter.writeNew(output, run, in, p, c).fold(e => fail(e), identity)
    assert(manifest.constraints.size == 2); assert(manifest.liveCalls == 0)
    assert(LinkExporter.verify(output, c).contains(manifest))
    assert(LinkExporter.writeNew(output, run, in, p, c).isLeft)
    Files.writeString(output.resolve("work/grouping-constraints.json"), "corrupt")
    assert(LinkExporter.verify(output, c).isLeft)
  }
  test("a fake adapter ignoring interruption fuses further calls instead of overlapping retries") {
    val a = work("conf/test/A"); val b = work("conf/test/B"); val in = input(a, b);
    val p = ResolutionPolicy.example; val base = ResolutionConfig.example;
    val c = base.copy(adjudication = base.adjudication.copy(timeoutMs = 5, maxRetries = 1))
    val req = Adjudication
      .request(
        comparison(a, b, in),
        in,
        p,
        c,
        FeatureExtractor.extract(comparison(a, b, in), in, p),
        in.evidence
      )
      .toOption
      .get
    val counter = new AtomicInteger(0)
    val fake = new AdjudicationAdapter {
      val provider = c.adjudication.provider; val model = c.adjudication.model;
      val modelVersion = c.adjudication.modelVersion
      def respond(r: AdjudicationRequest): String = {
        counter.incrementAndGet(); val end = System.nanoTime() + 150000000L;
        while (System.nanoTime() < end) {
          try Thread.sleep(5)
          catch { case _: InterruptedException => () }
        }; "{}"
      }
    }
    val adjudicator = new OfflineAdjudicator(c, fake, None)
    assert(adjudicator.adjudicate(req).status == "ADAPTER_NOT_TERMINATED")
    assert(adjudicator.adjudicate(req).status == "ADAPTER_NOT_TERMINATED")
    assert(counter.get() == 1)
    Thread.sleep(
      180
    ) // Let the deliberately uncooperative synthetic adapter finish before the gate exits.
  }
  test("CLI help is honest and invalid options fail before creating output") {
    assert(
      Phase5Main
        .run(Array("--help"))
        .toOption
        .get
        .contains("live adapters and network calls do not exist")
    )
    assert(Phase5Main.run(Array("resolve", "--gold", "forbidden")).isLeft)
  }
  test("strict JSON refuses primitive coercions and fractional integral configuration") {
    val config = writeJs(ResolutionConfig.example)
    config("input")("maxInputRecords") = ujson.Str("100")
    assert(ResolutionConfig.parse(config.render()).isLeft)
    val fractional = writeJs(ResolutionConfig.example)
    fractional("input")("maxInputRecords") = ujson.Num(2.5)
    assert(ResolutionConfig.parse(fractional.render()).isLeft)
  }
  test("a valid identifier-index row cannot cite a missing source observation") {
    val a = work("conf/test/IndexA")
    val native = "conf/test/Missing"
    val index = IdentifierIndexEntry(
      SchemaVersions.domain,
      IdentifierNamespace.Doi,
      "10.1000/missing",
      Some("work:doi:10.1000/missing"),
      SourceType.Dblp,
      native,
      a.provenance.datasetSnapshot,
      ErTestData.run,
      a.provenance.copy(sourceRecordId = native)
    )
    assert(DomainValidation.check(index).isRight)
    val evidence = ResolutionInput.record("index", writeJs(index), "synthetic-index:1")
    val result = ResolutionInput.assemble(
      Vector(a),
      Vector.empty,
      Vector.empty,
      Vector.empty,
      Vector.empty,
      Vector.empty,
      Vector(evidence),
      None
    )
    assert(result.left.toOption.exists(_.contains("missing source observation")))
  }
  test("a work abstract reference requires the actual matching text observation") {
    val a = work("conf/test/AbstractA")
    val text = "Synthetic source abstract"
    val id = StableIds
      .chunkOrProfileId(
        a.workId,
        a.provenance.datasetSnapshot,
        EmittedTextDocument.abstractDocumentType,
        None,
        text
      )
      .toOption
      .get
    val withAbstract = a.copy(abstractTextRef = Some(id))
    assert(DomainValidation.check(withAbstract).isRight)
    assert(
      ResolutionInput
        .create(Vector(withAbstract), Vector.empty, Vector.empty, Vector.empty)
        .left
        .toOption
        .exists(_.contains("abstractTextRef"))
    )
    val document = EmittedTextDocument(
      id,
      SchemaVersions.domain,
      EmittedTextDocument.abstractDocumentType,
      a.workId,
      a.provenance.datasetSnapshot,
      None,
      text,
      a.provenance
    )
    val evidence = ResolutionInput.record("text", writeJs(document), "synthetic-text:1")
    assert(
      ResolutionInput
        .assemble(
          Vector(withAbstract),
          Vector.empty,
          Vector.empty,
          Vector.empty,
          Vector.empty,
          Vector.empty,
          Vector(evidence),
          None
        )
        .isRight
    )
  }
  test(
    "ORCID work activity candidates may omit carried workId while present identifiers must bind"
  ) {
    val w = work("conf/test/ActivityWork", doi = Some("10.1000/activity"))
    val orcid = "0000-0002-1825-0097"
    val native = orcid + "/work/123"
    val activity = OrcidActivityRecord(
      SchemaVersions.domain,
      orcid,
      OrcidActivityKind.Work,
      native,
      Some(w.title),
      None,
      w.year,
      None,
      None,
      None,
      None,
      w.doi,
      Some(w.workId),
      "Synthetic source activity; no author list",
      w.provenance.copy(source = SourceType.Orcid, sourceRecordId = native),
      Vector(OrcidWorkReference("doi", w.doi.get, Some("self")))
    )
    def candidateWith(carried: Option[String]): MatchCandidate = {
      val oa = CandidateObservation(
        w.source,
        w.sourceRecordId,
        w.provenance.datasetSnapshot,
        Some(w.workId)
      )
      val ob =
        CandidateObservation(SourceType.Orcid, native, activity.provenance.datasetSnapshot, carried)
      val (left, right) = StableIds.canonicalCandidateObservations(oa, ob).toOption.get
      val key = "exact:doi:" + w.doi.get
      val id = StableIds.matchCandidateId(left, right, key).toOption.get
      MatchCandidate(
        id,
        SchemaVersions.domain,
        key,
        left,
        right,
        Vector.empty,
        PreparationFeatures.policyV2,
        ErTestData.run,
        "Synthetic blocking evidence",
        w.provenance.copy(
          source = SourceType.ScholarChain,
          sourceRecordId = id,
          datasetSnapshot = "hadoop-prep"
        )
      )
    }
    assert(DomainValidation.check(activity).isRight)
    val input =
      ResolutionInput.create(Vector(w), Vector.empty, Vector(activity), Vector(candidateWith(None)))
    assert(input.isRight, input.toString)
    val pairs = CandidateBuilder.build(input.toOption.get, ResolutionConfig.example).toOption.get
    assert(pairs.pairs.size == 1 && pairs.pairs.head.pair.entityType == ResolutionEntityType.Work)
    assert(
      FeatureExtractor
        .extract(pairs.pairs.head, input.toOption.get, ResolutionPolicy.example)
        .find(_.name == "authorOverlap")
        .get
        .value
        .isEmpty
    )
    assert(
      ResolutionInput
        .create(
          Vector(w),
          Vector.empty,
          Vector(activity),
          Vector(candidateWith(Some("work:doi:10.1000/wrong")))
        )
        .isLeft
    )
    assert(
      ResolutionInput
        .create(Vector(w), Vector.empty, Vector(activity), Vector(candidateWith(Some(w.workId))))
        .isRight
    )
  }

}
