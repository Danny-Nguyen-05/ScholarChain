package edu.uic.cs441.scholarchain.core

import java.nio.charset.StandardCharsets
import java.nio.file.{Files, Path}

import org.scalatest.funsuite.AnyFunSuite
import upickle.default.ReadWriter

import scala.io.Source

/** Phase 4 additive contracts. Pair-order expectations describe the accepted coauthor-pair rule. */
class Phase4ContractSpec extends AnyFunSuite {
  private val blockKey = "doi:" + Fixtures.doi
  private val abstractText =
    "Synthetic abstract fixture for the text-reference contract. Not source evidence."

  private val crossrefObservation = CandidateObservation(
    SourceType.Crossref,
    Fixtures.doi,
    "crossref-2026-10-03",
    Some(Fixtures.workId)
  )
  private val dblpObservation = CandidateObservation(
    SourceType.Dblp,
    Fixtures.dblpKey,
    "dblp-2026-10-03",
    Some(Fixtures.workId)
  )

  test("match candidate id is invariant when the two observations are swapped") {
    val forward = StableIds.matchCandidateId(dblpObservation, crossrefObservation, blockKey)
    val backward = StableIds.matchCandidateId(crossrefObservation, dblpObservation, blockKey)
    assert(forward == backward)
    assert(forward.isRight)
    val expected = "match-candidate:" + StableIds.sha256Hex(
      Seq(
        blockKey,
        crossrefObservation.source.wire,
        crossrefObservation.sourceRecordId,
        crossrefObservation.datasetSnapshot,
        crossrefObservation.workId.get,
        dblpObservation.source.wire,
        dblpObservation.sourceRecordId,
        dblpObservation.datasetSnapshot,
        dblpObservation.workId.get
      ).mkString("\n")
    )
    assert(forward == Right(expected))
    assert(
      StableIds
        .candidateObservationOrderKey(crossrefObservation)
        .compareTo(StableIds.candidateObservationOrderKey(dblpObservation)) < 0
    )
    val identical = StableIds.matchCandidateId(dblpObservation, dblpObservation, blockKey)
    assert(identical.left.exists(_.message.contains("identical observations")))
    val conflict = dblpObservation.copy(
      workId = StableIds.workIdFromDblpKey(Fixtures.dblpKey).toOption
    )
    val conflicting =
      StableIds.matchCandidateId(dblpObservation, conflict, blockKey)
    assert(conflicting.left.exists(_.message.contains("conflicting work ids")))
  }

  test("match candidate round-trips and is not a match decision") {
    val candidate = matchCandidate
    val checked = roundTrip(candidate)(DomainValidation.check)
    val json = CoreJson.compact(checked)
    assert(!json.contains("\"decision\""))
    assert(!json.contains("\"confidence\""))
    assert(json.contains("\"features\""))
    assert(checked.schemaVersion == SchemaVersions.domain)
    val swapped = checked.copy(left = checked.right, right = checked.left)
    assert(DomainValidation.check(swapped).isLeft)
    assert(
      StableIds.matchCandidateId(swapped.left, swapped.right, blockKey) == Right(
        checked.candidateId
      )
    )
    val decided = checked.copy(features = Vector(NamedNumber("ACCEPTED", 1.0)))
    assert(
      DomainValidation
        .check(decided)
        .left
        .exists(_.exists(_.code == ViolationCode.UnconfirmedIdentity))
    )
  }

  test("prep-features-v2 names stay inside the closed catalog and v1 records stay valid") {
    val expected = Vector(
      "block_size",
      "exact_shared_identifier",
      "same_work_id",
      "shared_affiliation_name_count",
      "shared_author_initial_count",
      "shared_author_name_count",
      "shared_coauthor_name_count",
      "title_equal",
      "venue_equal",
      "year_abs_delta",
      "year_equal"
    )
    assert(PreparationFeatures.policyV1 == "prep-features-v1")
    assert(PreparationFeatures.policyV2 == "prep-features-v2")
    assert(PreparationFeatures.names == expected)
    assert(PreparationFeatures.names == PreparationFeatures.names.sorted)
    assert(PreparationFeatures.names.distinct == PreparationFeatures.names)
    assert(PreparationFeatures.nameSet == expected.toSet)
    val catalog = candidateWith(PreparationFeatures.policyV2, v2Features)
    val checked = roundTrip(catalog)(DomainValidation.check)
    assert(checked.features.map(_.name) == expected)
    assert(checked.features.find(_.name == "year_abs_delta").exists(_.value == -1.0))
    assert(!CoreJson.compact(checked).contains("\"decision\""))
    val selection = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber(PreparationFeatures.blockSize, 4.0))
    )
    assert(DomainValidation.check(selection).isRight)
    assert(DomainValidation.check(matchCandidate).isRight)
    val outside = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("shared-doi", 1.0), NamedNumber("title-equality", 1.0))
    )
    assert(DomainValidation.check(outside).isLeft)
    val unsorted = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("year_equal", 1.0), NamedNumber("block_size", 2.0))
    )
    assert(DomainValidation.check(unsorted).isLeft)
    val duplicate = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("block_size", 1.0), NamedNumber("block_size", 2.0))
    )
    assert(DomainValidation.check(duplicate).isLeft)
    val nan = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("block_size", Double.NaN))
    )
    assert(DomainValidation.check(nan).isLeft)
    val infinite = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("block_size", Double.PositiveInfinity))
    )
    assert(DomainValidation.check(infinite).isLeft)
    val decided = candidateWith(
      PreparationFeatures.policyV2,
      Vector(NamedNumber("ACCEPTED", 1.0))
    )
    assert(
      DomainValidation
        .check(decided)
        .left
        .exists(_.exists(_.code == ViolationCode.UnconfirmedIdentity))
    )
  }

  test("block-key grammars stay inside the existing stable id rules") {
    assert(
      PreparationFeatures.blockKeyGrammars == Vector(
        "exact:{namespace}:{value}",
        "name:{normalized}",
        "initial:{normalized}",
        "title-year:{normalizedTitle}:{year-or-unknown}",
        "venue:{normalized}",
        "affiliation:{normalized}",
        "coauthor:{normalized}",
        "fallback:{sourceWire}:{sourceRecordId}"
      )
    )
    val keys = Vector(
      s"exact:doi:${Fixtures.doi}",
      "name:claiborne rice",
      "initial:c rice",
      "title-year:machine mentality:2011",
      "title-year:machine mentality:unknown",
      "venue:pt-ai",
      "affiliation:university of louisiana at lafayette",
      "coauthor:istvan s n berkeley",
      s"fallback:${SourceType.Dblp.wire}:${Fixtures.dblpKey}",
      blockKey
    )
    keys.foreach { key =>
      assert(key == key.trim && key.length <= 512)
      assert(!key.exists(ch => ch == '\n' || ch == '\r'))
      assert(StableIds.matchCandidateId(dblpObservation, crossrefObservation, key).isRight)
    }
    val broken = s"fallback:${SourceType.Dblp.wire}:has\nline"
    assert(StableIds.matchCandidateId(dblpObservation, crossrefObservation, broken).isLeft)
    val oversize = "fallback:DBLP:" + ("a" * 512)
    assert(oversize.length > 512)
    assert(StableIds.matchCandidateId(dblpObservation, crossrefObservation, oversize).isLeft)
  }

  test("reject records round-trip for every closed reason and do not invent a source") {
    val wires = RejectReasonCode.values.map(_.wire).toSet
    assert(wires.contains("MALFORMED_RECORD"))
    assert(wires.contains("UNSUPPORTED_RECORD_TYPE"))
    assert(wires.contains("INVALID_IDENTIFIER"))
    assert(wires.contains("MISSING_REQUIRED_FIELD"))
    assert(wires.contains("OVERSIZE_RECORD"))
    assert(wires.contains("OVERSIZE_XML_ENTITY_EXPANSION"))
    assert(wires.contains("UNSAFE_ENTITY"))
    assert(wires.contains("OVERSIZE_BLOCK"))
    assert(wires.contains("OVERSIZE_CANDIDATE_PAIRS"))
    assert(wires.contains("OVERSIZE_TEAM"))
    assert(wires.contains("SCHEMA_FAILURE"))
    assert(wires.contains("CONFLICTING_OBSERVATION"))
    assert(wires.contains("DUPLICATE_IDENTICAL_OBSERVATION"))
    assert(wires.contains("PROVENANCE_MISMATCH"))
    assert(
      RejectReasonCode.DuplicateIdenticalObservation != RejectReasonCode.ConflictingObservation
    )
    RejectReasonCode.values.foreach { reason =>
      val record = reject(reason)
      val checked = roundTrip(record)(DomainValidation.check)
      assert(checked.source.isEmpty)
      assert(checked.reasonCode == reason)
    }
    val hashed = reject(RejectReasonCode.MalformedRecord).copy(
      diagnosticExcerpt = None,
      diagnosticHash = Some(StableIds.sha256Hex("byte-level parse failure"))
    )
    assert(DomainValidation.check(hashed).isRight)
    val missingDiagnostic = hashed.copy(diagnosticHash = None)
    assert(DomainValidation.check(missingDiagnostic).isLeft)
    val oversize = reject(RejectReasonCode.OversizeRecord).copy(
      diagnosticExcerpt = Some("x" * (RejectRecord.maxDiagnosticExcerptLength + 1))
    )
    assert(DomainValidation.check(oversize).isLeft)
    val bounded = reject(RejectReasonCode.OversizeRecord).copy(
      diagnosticExcerpt = Some("y" * RejectRecord.maxDiagnosticExcerptLength)
    )
    assert(DomainValidation.check(bounded).isRight)
    val unknownReason = CoreJson
      .compact(reject(RejectReasonCode.SchemaFailure))
      .replace("SCHEMA_FAILURE", "NOT_A_REASON")
    assert(CoreJson.parse[RejectRecord](unknownReason).isLeft)
  }

  test("identifier index keeps one row per observation and refuses invented work ids") {
    val dblpDoi = indexEntry(
      SourceType.Dblp,
      Fixtures.dblpKey,
      "dblp-2026-10-03",
      IdentifierNamespace.Doi,
      "https://doi.org/" + Fixtures.doi
    )
    val crossrefDoi = indexEntry(
      SourceType.Crossref,
      Fixtures.doi,
      "crossref-2026-10-03",
      IdentifierNamespace.Doi,
      Fixtures.doi
    )
    roundTrip(dblpDoi)(DomainValidation.check)
    roundTrip(crossrefDoi)(DomainValidation.check)
    assert(dblpDoi.normalizedValue == crossrefDoi.normalizedValue)
    assert(dblpDoi.preferredWorkId == Some(Fixtures.workId))
    assert(dblpDoi != crossrefDoi)
    assert(DomainValidation.check(dblpDoi.copy(preferredWorkId = None)).isLeft)
    val orcid = indexEntry(
      SourceType.Orcid,
      Fixtures.riceOrcid,
      "unknown",
      IdentifierNamespace.Orcid,
      "https://orcid.org/" + Fixtures.riceOrcid
    )
    val checkedOrcid = roundTrip(orcid)(DomainValidation.check)
    assert(checkedOrcid.preferredWorkId.isEmpty)
    assert(checkedOrcid.normalizedValue == Fixtures.riceOrcid)
    assert(DomainValidation.check(orcid.copy(preferredWorkId = Some(Fixtures.workId))).isLeft)
    val malformed = StableIds.identifierPreferredWorkId(IdentifierNamespace.Doi, "not-a-doi")
    assert(malformed.isLeft)
    assert(!malformed.swap.toOption.get.message.contains("work:"))
    assert(
      StableIds.identifierPreferredWorkId(
        IdentifierNamespace.OpenAlexAuthor,
        "https://openalex.org/A5101955953"
      ) == Right(None)
    )
    assert(
      DomainValidation
        .check(dblpDoi.copy(normalizedValue = "NOT-A-DOI", preferredWorkId = None))
        .isLeft
    )
  }

  test("emitted abstract text is the abstractTextRef target") {
    val document = emittedAbstract
    roundTrip(document)(DomainValidation.check)
    assert(document.textId.startsWith("chunk:"))
    val cited = Fixtures.work.copy(abstractTextRef = Some(document.textId))
    assert(DomainValidation.check(cited).isRight)
    val raw = Fixtures.work.copy(abstractTextRef = Some(abstractText))
    assert(DomainValidation.check(raw).isLeft)
    assert(DomainValidation.check(document.copy(textId = "chunk:" + ("a" * 64))).isLeft)
  }

  test("ORCID profile and activity stay distinct from works, merges, and institution ids") {
    roundTrip(orcidProfile)(DomainValidation.check)
    val employment = orcidEmployment
    roundTrip(employment)(DomainValidation.check)
    assert(employment.ror.isEmpty)
    assert(employment.ringgold.contains("4365"))
    assert(employment.institutionId.contains(Fixtures.ringgoldInstitutionId))
    val swappedNamespace = employment.copy(ror = Some("4365"), ringgold = None)
    assert(DomainValidation.check(swappedNamespace).isLeft)
    val dual = employment.copy(
      ror = Some("https://ror.org/01x8rc503"),
      institutionId = Some(Fixtures.openAlexInstitutionId),
      uncertainty = "Synthetic dual-id fixture. ROR and Ringgold stay in separate fields."
    )
    assert(DomainValidation.check(dual).isRight)
    val collapsed = dual.copy(institutionId = Some("institution:openalex:I79516672"))
    assert(DomainValidation.check(collapsed).isLeft)
    val workRef = orcidWorkReference
    val checkedWork = roundTrip(workRef)(DomainValidation.check)
    assert(workRef.observedDoi.contains(Fixtures.doi))
    assert(workRef.observedWorkId.contains(Fixtures.workId))
    assert(
      checkedWork.workReferences == Vector(
        OrcidWorkReference("other-id", "24870415", Some("self"))
      )
    )
    assert(DomainValidation.check(workRef.copy(observedWorkId = None)).isLeft)
    assert(DomainValidation.check(employment.copy(observedDoi = Some(Fixtures.doi))).isLeft)
  }

  test("OpenAlex institution ids and ORCID work references stay source observations") {
    assert(IdentifierNamespace.OpenAlexInstitution.wire == "openalex-institution")
    assert(!IdentifierNamespace.workNamespaces.contains(IdentifierNamespace.OpenAlexInstitution))
    assert(!IdentifierNamespace.authorizesWorkId(IdentifierNamespace.OpenAlexInstitution))
    assert(
      CoreJson.compact(IdentifierNamespace.OpenAlexInstitution) == "\"openalex-institution\""
    )
    assert(
      CoreJson.parse[IdentifierNamespace]("\"openalex-institution\"") == Right(
        IdentifierNamespace.OpenAlexInstitution
      )
    )
    assert(
      StableIds.normalizeIndexedIdentifier(
        IdentifierNamespace.OpenAlexInstitution,
        "https://openalex.org/I79516672"
      ) == Right("I79516672")
    )
    assert(
      StableIds.normalizeIndexedIdentifier(
        IdentifierNamespace.OpenAlexInstitution,
        "I79516672"
      ) == Right("I79516672")
    )
    assert(
      StableIds
        .normalizeIndexedIdentifier(IdentifierNamespace.OpenAlexInstitution, "not-an-institution")
        .isLeft
    )
    assert(
      StableIds.identifierPreferredWorkId(
        IdentifierNamespace.OpenAlexInstitution,
        "https://openalex.org/I79516672"
      ) == Right(None)
    )
    assert(
      StableIds
        .identifierPreferredWorkId(IdentifierNamespace.OpenAlexInstitution, "not-an-institution")
        .isLeft
    )
    val indexed = indexEntry(
      SourceType.OpenAlex,
      "https://openalex.org/I79516672",
      "unknown",
      IdentifierNamespace.OpenAlexInstitution,
      "https://openalex.org/I79516672"
    )
    val checkedIndex = roundTrip(indexed)(DomainValidation.check)
    assert(checkedIndex.normalizedValue == "I79516672")
    assert(checkedIndex.preferredWorkId.isEmpty)
    assert(DomainValidation.check(indexed.copy(preferredWorkId = Some(Fixtures.workId))).isLeft)

    val reference = OrcidWorkReference("other-id", "24870415", Some("self"))
    val activity = orcidWorkReference.copy(workReferences = Vector(reference))
    val checkedActivity = roundTrip(activity)(DomainValidation.check)
    assert(checkedActivity.observedDoi.contains(Fixtures.doi))
    assert(checkedActivity.observedWorkId.contains(Fixtures.workId))
    assert(checkedActivity.workReferences == Vector(reference))
    assert(DomainValidation.check(reference).isRight)
    assert(DomainValidation.check(reference.copy(relationship = None)).isRight)
    assert(DomainValidation.check(reference.copy(externalIdType = "")).isLeft)
    assert(DomainValidation.check(reference.copy(value = " ")).isLeft)
    assert(DomainValidation.check(reference.copy(relationship = Some(""))).isLeft)
    assert(DomainValidation.check(reference.copy(relationship = Some(" self"))).isLeft)
    val missingReferences = ujson.read(CoreJson.compact(checkedActivity))
    missingReferences.obj.remove("workReferences")
    val legacyActivity = CoreJson.parse[OrcidActivityRecord](ujson.write(missingReferences))
    assert(legacyActivity.exists(_.workReferences.isEmpty))
    assert(legacyActivity.exists(_.observedDoi.contains(Fixtures.doi)))

    val institution = Fixtures.openAlexInstitution
    val checkedInstitution = roundTrip(institution)(DomainValidation.check)
    assert(checkedInstitution.institutionId == Fixtures.openAlexInstitutionId)
    assert(checkedInstitution.institutionId.startsWith("institution:ror:"))
    assert(checkedInstitution.ror.contains("https://ror.org/01x8rc503"))
    assert(
      checkedInstitution.observedSourceIds == Vector(
        ObservedIdentifier(
          "openalex-institution",
          "https://openalex.org/I79516672",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    assert(
      StableIds.identifierPreferredWorkId(
        IdentifierNamespace.OpenAlexInstitution,
        checkedInstitution.observedSourceIds.head.value
      ) == Right(None)
    )
    val unknownNamespace = institution.copy(
      observedSourceIds = Vector(
        ObservedIdentifier(
          "not-a-namespace",
          "I79516672",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    assert(DomainValidation.check(unknownNamespace).isLeft)
    val blankValue = institution.copy(
      observedSourceIds = Vector(
        ObservedIdentifier(
          "openalex-institution",
          " ",
          IdentifierInterpretation.SourceObservation
        )
      )
    )
    assert(DomainValidation.check(blankValue).isLeft)
    val missingObservations = ujson.read(CoreJson.compact(checkedInstitution))
    missingObservations.obj.remove("observedSourceIds")
    val legacyInstitution = CoreJson.parse[Institution](ujson.write(missingObservations))
    assert(legacyInstitution.exists(_.observedSourceIds.isEmpty))
    assert(legacyInstitution.exists(_.institutionId == Fixtures.openAlexInstitutionId))
  }

  test("enrichment links attach venue, institution, and topic evidence without a decision") {
    roundTrip(institutionLink)(DomainValidation.check)
    roundTrip(topicLink)(DomainValidation.check)
    val venue = institutionLink.copy(
      mentionId = None,
      targetKind = EnrichmentTargetKind.Venue,
      targetId = Fixtures.venueId,
      ror = None,
      uncertainty = "Venue observed on the work. Not an identity decision."
    )
    roundTrip(venue)(DomainValidation.check)
    assert(DomainValidation.check(venue.copy(ror = Some("https://ror.org/01x8rc503"))).isLeft)
    assert(DomainValidation.check(institutionLink.copy(workId = None, mentionId = None)).isLeft)
  }

  test("mention affiliation keeps a name without inventing an institution id") {
    val named = mentionAffiliation
    val checked = roundTrip(named)(DomainValidation.check)
    val json = CoreJson.compact(checked)
    assert(fieldOrder(json) == mentionAffiliationFields)
    assert(json.contains("\"organizationName\""))
    assert(!json.contains("\"targetId\""))
    assert(!json.contains("\"decision\""))
    assert(checked.institutionId.isEmpty)
    assert(checked.ror.isEmpty)
    assert(checked.ringgold.isEmpty)
    val mentionFields = fieldOrder(CoreJson.compact(Fixtures.riceMention))
    assert(mentionFields == fieldOrder(resourceText("/wire/author-mention.json")))
    assert(!mentionFields.contains("organizationName"))
    assert(!mentionFields.contains("affiliation"))
    val withRor = named.copy(
      organizationName = None,
      ror = Some("https://ror.org/01x8rc503"),
      institutionId = Some(Fixtures.openAlexInstitutionId)
    )
    roundTrip(withRor)(DomainValidation.check)
    val withRinggold = named.copy(
      organizationName = None,
      ringgold = Some("4365"),
      institutionId = Some(Fixtures.ringgoldInstitutionId)
    )
    roundTrip(withRinggold)(DomainValidation.check)
    assert(DomainValidation.check(named.copy(organizationName = Some(""))).isLeft)
    assert(DomainValidation.check(named.copy(organizationName = Some("   "))).isLeft)
    assert(DomainValidation.check(named.copy(organizationName = Some("institution"))).isLeft)
    assert(DomainValidation.check(named.copy(organizationName = Some(" institution "))).isLeft)
    val invented = named.copy(institutionId = Some("institution:openalex:I79516672"))
    assert(DomainValidation.check(invented).isLeft)
    assert(DomainValidation.check(withRor.copy(institutionId = None)).isLeft)
    assert(DomainValidation.check(named.copy(organizationName = None)).isLeft)
    val otherMention = StableIds.mentionId(SourceType.Crossref, Fixtures.doi, 1)
    assert(DomainValidation.check(named.copy(mentionId = otherMention)).isLeft)
  }

  test("config v1 still loads and fingerprints independently of hadoop prep") {
    val jsonUrl = getClass.getResource("/scholarchain.config.v1.json")
    val confUrl = getClass.getResource("/scholarchain.config.v1.conf")
    val jsonBytes = Files.readAllBytes(Path.of(jsonUrl.toURI))
    val confBytes = Files.readAllBytes(Path.of(confUrl.toURI))
    assert(jsonBytes sameElements confBytes)
    val jsonText = new String(jsonBytes, StandardCharsets.UTF_8)
    val loaded = ConfigLoader.loadText(jsonText, Map.empty).toOption.get
    val fromConf =
      ConfigLoader.loadText(new String(confBytes, StandardCharsets.UTF_8), Map.empty).toOption.get
    assert(loaded == fromConf)
    assert(loaded.configSchemaVersion == SchemaVersions.config)
    assert(loaded.fingerprint == fromConf.fingerprint)
    assert(loaded.fingerprint == StableIds.sha256Hex(loaded.canonicalJson))
    assert(loaded.fingerprint.matches("[0-9a-f]{64}"))
    assert(loaded.canonicalJson.contains("scholarchain.config.v1"))
    assert(loaded.canonicalJson.contains("local-dev-raw"))
    assert(!loaded.canonicalJson.contains("hadoop-prep"))
    assert(!loaded.canonicalJson.contains("maxRecordBytes"))
    assert(!loaded.canonicalJson.contains("s3://"))
    val changed = loaded.copy(application = loaded.application.copy(environment = "mutated"))
    assert(changed.fingerprint != loaded.fingerprint)
    assert(ConfigLoader.loadText(hadoopExample, Map.empty).isLeft)
  }

  test("hadoop prep config rejects missing limits and non-positive limits") {
    val example = hadoopExample
    assert(!example.contains("s3://"))
    assert(!example.contains("s3a://"))
    assert(!example.contains("amazonaws.com"))
    val loaded = HadoopPrepConfigLoader.loadText(example).toOption.get
    assert(loaded.outputRoot == "target/phase4-runs")
    assert(loaded.compressionCodec == "none")
    assert(!loaded.intermediateCompressionEnabled)
    assert(loaded.executionMode == HadoopExecutionMode.Local)
    assert(example.contains("\"executionMode\": \"local\""))
    assert(loaded.configSchemaVersion == SchemaVersions.hadoopPrep)
    assert(HadoopPrepConfigLoader.validate(loaded) == Right(loaded))
    val parsed = CoreJson.parse[HadoopPrepConfig](CoreJson.compact(loaded))
    assert(parsed == Right(loaded))
    assert(HadoopPrepConfigLoader.loadText(CoreJson.compact(loaded)) == Right(loaded))
    val removedLimit = ujson.read(example)
    removedLimit.obj.remove("maxRecordBytes")
    assert(HadoopPrepConfigLoader.loadText(removedLimit.render()).isLeft)
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"reducerCount\": 1", "\"reducerCount\": 0"))
        .isLeft
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"maxAuthorTeamSize\": 16", "\"maxAuthorTeamSize\": -1"))
        .isLeft
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"maxRecordBytes\": 1048576", "\"maxRecordBytes\": 1.5"))
        .isLeft
    )
    val enabled = example
      .replace("\"compressionCodec\": \"none\"", "\"compressionCodec\": \"gzip\"")
      .replace(
        "\"intermediateCompressionEnabled\": false",
        "\"intermediateCompressionEnabled\": true"
      )
    assert(HadoopPrepConfigLoader.loadText(enabled).isRight)
    assert(
      HadoopPrepConfigLoader
        .loadText(
          example.replace("\"compressionCodec\": \"none\"", "\"compressionCodec\": \"gzip\"")
        )
        .isLeft
    )
    assert(HadoopPrepConfigLoader.validate(loaded.copy(maxLocalSampleRecords = 0)).isLeft)
    assert(HadoopPrepConfigLoader.loadText("{}").isLeft)
    val removedMode = ujson.read(example)
    removedMode.obj.remove("executionMode")
    val missingMode = HadoopPrepConfigLoader.loadText(removedMode.render())
    assert(missingMode.isLeft)
    assert(missingMode.left.exists(_.text.contains("missing executionMode")))
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"executionMode\": \"local\"", "\"executionMode\": \"cluster\""))
        .toOption
        .map(_.executionMode)
        .contains(HadoopExecutionMode.Cluster)
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"executionMode\": \"local\"", "\"executionMode\": \"emr\""))
        .isLeft
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("\"executionMode\": \"local\"", "\"executionMode\": true"))
        .isLeft
    )
  }

  test("run manifest may name the hadoop prep schema that ConfigLoader rejects") {
    val fingerprint = "ab" * 32
    val prepManifest = Fixtures.manifest.copy(
      configSchemaVersion = SchemaVersions.hadoopPrep,
      configFingerprint = fingerprint
    )
    assert(fingerprint.matches("[0-9a-f]{64}"))
    assert(DomainValidation.check(prepManifest).isRight)
    assert(DomainValidation.check(Fixtures.manifest).isRight)
    assert(
      SchemaVersions.supportedManifestConfig == Set(
        SchemaVersions.config,
        SchemaVersions.hadoopPrep,
        SchemaVersions.sparkAnalyticsConfig
      )
    )
    assert(SchemaVersions.supportedConfig == Set(SchemaVersions.config))
    val asApplication = resourceText("/scholarchain.config.v1.json")
      .replace(SchemaVersions.config, SchemaVersions.hadoopPrep)
    assert(
      ConfigLoader
        .loadText(asApplication, Map.empty)
        .left
        .exists(_.text.contains("unsupported config schema"))
    )
    assert(ConfigLoader.loadText(hadoopExample, Map.empty).isLeft)
  }

  test("caller-supplied s3 output root loads and the sample stays local") {
    val example = hadoopExample
    val loaded = HadoopPrepConfigLoader.loadText(example).toOption.get
    assert(loaded.outputRoot == "target/phase4-runs")
    assert(!example.contains("s3://"))
    assert(!example.contains("s3a://"))
    assert(!example.contains("s3n://"))
    val supplied = "s3://phase4-bucket/out"
    val withRoot = HadoopPrepConfigLoader.loadText(example.replace("target/phase4-runs", supplied))
    assert(withRoot.toOption.map(_.outputRoot).contains(supplied))
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("target/phase4-runs", "s3a://phase4-bucket/out"))
        .isRight
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("target/phase4-runs", "s3n://phase4-bucket/out"))
        .isRight
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("target/phase4-runs", "s3://phase4-bucket"))
        .isLeft
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("target/phase4-runs", "https://bucket.amazonaws.com/out"))
        .isLeft
    )
    assert(
      HadoopPrepConfigLoader.loadText(example.replace("target/phase4-runs", "amazonaws.com")).isLeft
    )
    assert(
      HadoopPrepConfigLoader
        .loadText(example.replace("target/phase4-runs", "s3.us-east-1.amazonaws.com"))
        .isLeft
    )
    assert(HadoopPrepConfigLoader.validate(loaded.copy(outputRoot = " ")).isLeft)
    assert(HadoopPrepConfigLoader.validate(loaded.copy(outputRoot = "target/a\nb")).isLeft)
    assert(HadoopPrepConfigLoader.validate(loaded.copy(outputRoot = "${OUTPUT_ROOT}")).isLeft)
  }

  test("coauthor pair endpoint field order and ordinal movement are unchanged") {
    val expected = Vector(
      "schemaVersion",
      "workId",
      "doi",
      "arxivId",
      "leftMentionId",
      "rightMentionId",
      "leftOrdinal",
      "rightOrdinal",
      "year",
      "uncertainty",
      "provenance"
    )
    assert(fieldOrder(CoreJson.compact(Fixtures.pair)) == expected)
    val frozen = resourceText("/wire/coauthor-pair-candidate.json")
    assert(fieldOrder(frozen) == expected)
    assert(Fixtures.pair.leftMentionId.compareTo(Fixtures.pair.rightMentionId) < 0)
    val leftParts = StableIds.parseMentionIdParts(Fixtures.pair.leftMentionId).toOption.get
    val rightParts = StableIds.parseMentionIdParts(Fixtures.pair.rightMentionId).toOption.get
    assert(leftParts.ordinal == Fixtures.pair.leftOrdinal)
    assert(rightParts.ordinal == Fixtures.pair.rightOrdinal)
    val lesserString = StableIds.mentionId(SourceType.Dblp, Fixtures.dblpKey, 10)
    val greaterString = StableIds.mentionId(SourceType.Dblp, Fixtures.dblpKey, 2)
    assert(lesserString.compareTo(greaterString) < 0)
    val structural = Fixtures.pair.copy(
      leftMentionId = lesserString,
      rightMentionId = greaterString,
      leftOrdinal = 10,
      rightOrdinal = 2
    )
    assert(DomainValidation.checkStructure(structural).isRight)
    val ordinalsLeftBehind = structural.copy(leftOrdinal = 2, rightOrdinal = 10)
    assert(DomainValidation.checkStructure(ordinalsLeftBehind).isLeft)
    val reversedIds = structural.copy(
      leftMentionId = greaterString,
      rightMentionId = lesserString,
      leftOrdinal = 2,
      rightOrdinal = 10
    )
    assert(DomainValidation.checkStructure(reversedIds).isLeft)
    assert(DomainValidation.check(Fixtures.pair, Fixtures.work).isRight)
  }

  private val mentionAffiliationFields: Vector[String] = Vector(
    "schemaVersion",
    "mentionId",
    "source",
    "sourceRecordId",
    "datasetSnapshot",
    "organizationName",
    "ror",
    "ringgold",
    "institutionId",
    "uncertainty",
    "provenance"
  )

  private def candidateWith(policy: String, features: Vector[NamedNumber]): MatchCandidate =
    matchCandidate.copy(featurePolicyVersion = policy, features = features)

  private def v2Features: Vector[NamedNumber] =
    PreparationFeatures.names.map { name =>
      val value =
        if (name == PreparationFeatures.yearAbsDelta) -1.0
        else if (
          name == PreparationFeatures.exactSharedIdentifier ||
          name == PreparationFeatures.sameWorkId
        ) 1.0
        else 0.0
      NamedNumber(name, value)
    }

  private def mentionAffiliation: MentionAffiliation =
    MentionAffiliation(
      schemaVersion = SchemaVersions.domain,
      mentionId = Fixtures.riceMentionId,
      source = SourceType.Dblp,
      sourceRecordId = Fixtures.dblpKey,
      datasetSnapshot = Fixtures.dblpProvenance.datasetSnapshot,
      organizationName = Some("University of Louisiana at Lafayette"),
      ror = None,
      ringgold = None,
      institutionId = None,
      uncertainty = "Publisher affiliation name. No ROR or Ringgold, so no institution id.",
      provenance = Fixtures.dblpProvenance
    )

  private def matchCandidate: MatchCandidate = {
    val candidateId =
      StableIds.matchCandidateId(dblpObservation, crossrefObservation, blockKey).toOption.get
    MatchCandidate(
      candidateId = candidateId,
      schemaVersion = SchemaVersions.domain,
      blockKey = blockKey,
      left = crossrefObservation,
      right = dblpObservation,
      features = Vector(
        NamedNumber("shared-doi", 1.0),
        NamedNumber("title-equality", 1.0)
      ),
      featurePolicyVersion = "prep-features-v1",
      runId = Fixtures.runId,
      uncertainty = "Deterministic block features are not an accept or reject decision.",
      provenance = Fixtures.provenance(
        SourceType.ScholarChain,
        candidateId,
        "phase4-local",
        None,
        None,
        Vector("Block features are not an identity decision.")
      )
    )
  }

  private def reject(reason: RejectReasonCode): RejectRecord =
    RejectRecord(
      schemaVersion = SchemaVersions.domain,
      source = None,
      sourceLocator = "datasets/samples/dblp/linked-records.xml#byte:0",
      datasetSnapshot = None,
      runId = Fixtures.runId,
      stage = PreparationStage.Parse,
      reasonCode = reason,
      diagnosticExcerpt = Some(reason.wire),
      diagnosticHash = None
    )

  private def indexEntry(
      source: SourceType,
      sourceRecordId: String,
      snapshot: String,
      namespace: IdentifierNamespace,
      raw: String
  ): IdentifierIndexEntry = {
    val normalized = StableIds.normalizeIndexedIdentifier(namespace, raw).toOption.get
    val preferred = StableIds.identifierPreferredWorkId(namespace, raw).toOption.get
    IdentifierIndexEntry(
      schemaVersion = SchemaVersions.domain,
      namespace = namespace,
      normalizedValue = normalized,
      preferredWorkId = preferred,
      source = source,
      sourceRecordId = sourceRecordId,
      datasetSnapshot = snapshot,
      runId = Fixtures.runId,
      provenance = Fixtures.provenance(
        source,
        sourceRecordId,
        snapshot,
        None,
        None,
        Vector("One identifier observation. Not collapsed with another source.")
      )
    )
  }

  private def emittedAbstract: EmittedTextDocument = {
    val textId = StableIds
      .chunkOrProfileId(
        Fixtures.workId,
        Fixtures.dblpProvenance.datasetSnapshot,
        EmittedTextDocument.abstractDocumentType,
        None,
        abstractText
      )
      .toOption
      .get
    EmittedTextDocument(
      textId = textId,
      schemaVersion = SchemaVersions.domain,
      documentType = EmittedTextDocument.abstractDocumentType,
      entityId = Fixtures.workId,
      sourceVersion = Fixtures.dblpProvenance.datasetSnapshot,
      ordinal = None,
      text = abstractText,
      provenance = Fixtures.dblpProvenance
    )
  }

  private def orcidProfile: OrcidProfileRecord =
    OrcidProfileRecord(
      schemaVersion = SchemaVersions.domain,
      orcid = Fixtures.riceOrcid,
      displayName = Some("Charles Claiborne Rice"),
      otherNames = Vector("Clai Rice"),
      externalIds = Vector(
        ObservedIdentifier(
          "orcid",
          Fixtures.riceOrcid,
          IdentifierInterpretation.ValidatedExternal
        ),
        ObservedIdentifier(
          "scopus",
          "55497628100",
          IdentifierInterpretation.SourceObservation
        )
      ),
      uncertainty =
        "Public ORCID person record. Not a merge with the dblp author string Claiborne Rice.",
      provenance = Fixtures.orcidResearcher.provenance
    )

  private def orcidEmployment: OrcidActivityRecord = {
    val path = s"/${Fixtures.riceOrcid}/employment/19198978"
    OrcidActivityRecord(
      schemaVersion = SchemaVersions.domain,
      orcid = Fixtures.riceOrcid,
      activityKind = OrcidActivityKind.Employment,
      sourceRecordId = path,
      title = Some("Associate Professor"),
      startYear = Some(2010),
      publicationYear = None,
      organizationName = Some("University of Louisiana at Lafayette"),
      ror = None,
      ringgold = Some("4365"),
      institutionId = Some(Fixtures.ringgoldInstitutionId),
      observedDoi = None,
      observedWorkId = None,
      uncertainty =
        "Ringgold 4365 is the ORCID organization id on this employment. No ROR is present.",
      provenance = Fixtures.provenance(
        SourceType.Orcid,
        path,
        "unknown",
        None,
        Some("https://info.orcid.org/public-data-file-use-policy/"),
        Vector("Bulk public-data-file version is unknown.")
      )
    )
  }

  private def orcidWorkReference: OrcidActivityRecord = {
    val path = s"/${Fixtures.riceOrcid}/work/128060282"
    OrcidActivityRecord(
      schemaVersion = SchemaVersions.domain,
      orcid = Fixtures.riceOrcid,
      activityKind = OrcidActivityKind.Work,
      sourceRecordId = path,
      title = Some("Machine Mentality?"),
      startYear = None,
      publicationYear = Some(2013),
      organizationName = None,
      ror = None,
      ringgold = None,
      institutionId = None,
      observedDoi = Some(Fixtures.doi),
      observedWorkId = Some(Fixtures.workId),
      uncertainty =
        "ORCID publication year is 2013. The DOI link is not authorship proof or a merge.",
      provenance = Fixtures.provenance(
        SourceType.Orcid,
        path,
        "unknown",
        Some("https://doi.org/10.1007/978-3-642-31674-6_1"),
        Some("https://info.orcid.org/public-data-file-use-policy/"),
        Vector("The DOI is an ORCID external id on this work summary, not an authorship proof.")
      ),
      workReferences = Vector(OrcidWorkReference("other-id", "24870415", Some("self")))
    )
  }

  private def institutionLink: EnrichmentLink =
    EnrichmentLink(
      schemaVersion = SchemaVersions.domain,
      source = SourceType.Dblp,
      sourceRecordId = Fixtures.dblpKey,
      datasetSnapshot = Fixtures.dblpProvenance.datasetSnapshot,
      workId = Some(Fixtures.workId),
      mentionId = Some(Fixtures.riceMentionId),
      targetKind = EnrichmentTargetKind.Institution,
      targetId = Fixtures.openAlexInstitutionId,
      ror = Some("https://ror.org/01x8rc503"),
      ringgold = None,
      score = None,
      uncertainty = "ROR observed beside an unresolved mention. Not a resolved affiliation.",
      runId = Fixtures.runId,
      provenance = Fixtures.dblpProvenance
    )

  private def topicLink: EnrichmentLink =
    EnrichmentLink(
      schemaVersion = SchemaVersions.domain,
      source = SourceType.Dblp,
      sourceRecordId = Fixtures.dblpKey,
      datasetSnapshot = Fixtures.dblpProvenance.datasetSnapshot,
      workId = Some(Fixtures.workId),
      mentionId = None,
      targetKind = EnrichmentTargetKind.Topic,
      targetId = Fixtures.topicId,
      ror = None,
      ringgold = None,
      score = Some(1.0),
      uncertainty = "Synthetic contract score, not an OpenAlex score. Not an identity decision.",
      runId = Fixtures.runId,
      provenance = Fixtures.dblpProvenance
    )

  private def hadoopExample: String = resourceText("/scholarchain.hadoop-prep.v1.json")

  private def resourceText(name: String): String = {
    val stream = getClass.getResourceAsStream(name)
    val text = Source.fromInputStream(stream, "UTF-8").mkString
    stream.close()
    text
  }

  private def fieldOrder(json: String): Vector[String] =
    ujson.read(json).obj.keys.toVector

  private def roundTrip[T: ReadWriter](
      value: T
  )(validate: T => Either[Vector[DomainViolation], T]): T = {
    val checked = validate(value)
    assert(checked.isRight, checked.left.toOption.map(_.mkString(" | ")).getOrElse(""))
    val parsed = CoreJson.parseAndValidate(CoreJson.compact(value))(validate)
    assert(parsed.isRight, parsed.left.toOption.map(_.mkString(" | ")).getOrElse(""))
    assert(parsed.toOption.get == value)
    parsed.toOption.get
  }
}
